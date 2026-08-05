#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanup_glb.py — AI 生成 GLB 工程清洗工具（animal-rebuild-spec §6.6 / asset-pipeline §1）

职责（对单个 GLB）：
  1. 报告：mesh 数 / 三角面数 / 材质 / 贴图 / 世界包围盒 / 单位朝向
  2. 规范化变换（烘焙进顶点，节点矩阵置恒等）：
       - 缩放至目标身高（默认 0.5 m，1 单位 = 1 米）
       - Y 轴向上（可选旋转，把指定轴翻到 Y）
       - 前向 +Z（可选绕 Y 旋转）
       - 锚点 = 脚底中心：x/z 居中、y 最小面落 y=0
  3. 重命名 mesh → mesh_* / material → mat_*
  4. 材质规范化为 glTF PBR（pbrMetallicRoughness，metallic=0，缺失 roughness 给 0.9）
  5. 面数检查：报告 tris 是否 <= 预算（默认 10000，可用 --budget 覆盖）

用法：
  python tools/cleanup_glb.py INPUT.glb OUTPUT.glb [--target-height 0.5] [--budget 10000]
      [--up-axis y|z|x] [--face-rotate 0|90|180|270] [--dry-run]

说明：
  - --dry-run 只报告不写文件（用于检查生成物质量）
  - --up-axis 默认 y（生成器通常已 Y-up）；若模型躺倒（身高沿 z/x），
    用 --up-axis z 把 z 翻到 y 上。
  - --face-rotate 绕 Y 轴旋转角度，用于让喙指向 +Z。
  - 不改动顶点色/贴图内容；只规范化结构。
"""
import argparse
import json
import math
import re
import struct
import sys

import numpy as np  # noqa: F401  (pygltflib 依赖 numpy)
import pygltflib
from pygltflib import (
    GLTF2, Buffer, BufferView, Accessor, Mesh, Primitive, Node, Material,
    PbrMetallicRoughness, TextureInfo,
)

MAT_ALIAS = {
    'body': 'plumage_body', 'plumage': 'plumage', 'feather': 'plumage',
    'head': 'plumage_head', 'comb': 'comb', 'wattle': 'comb',
    'beak': 'beak', 'bill': 'beak', 'mouth': 'beak',
    'tail': 'plumage_tail', 'wing': 'plumage_wing', 'leg': 'leg', 'foot': 'leg',
    'feet': 'leg', 'claw': 'leg', 'toe': 'leg', 'eye': 'eye', 'skin': 'skin',
}
MESH_ALIAS = {
    'body': 'body', 'head': 'head', 'comb': 'comb', 'wattle': 'wattle',
    'beak': 'beak', 'bill': 'beak', 'tail': 'tail', 'wing': 'wing',
    'leg': 'leg', 'foot': 'foot', 'feet': 'feet', 'claw': 'claw', 'toe': 'toe',
    'eye': 'eye', 'wattle': 'wattle', 'skin': 'skin', 'ear': 'ear',
}


def snake(name: str) -> str:
    s = re.sub(r'[^0-9a-zA-Z]+', '_', name).strip('_').lower()
    return s or 'part'


def read_accessor_float(gltf: GLTF2, accessor: Accessor, bin_data: bytes):
    """Return float32 array for accessor (assume FLOAT component)."""
    if accessor.componentType != pygltflib.FLOAT:
        raise ValueError(f"accessor componentType {accessor.componentType} not FLOAT")
    buf_view = gltf.bufferViews[accessor.bufferView]
    offset = (buf_view.byteOffset or 0) + (accessor.byteOffset or 0)
    count = accessor.count
    comps = {
        pygltflib.SCALAR: 1, pygltflib.VEC2: 2, pygltflib.VEC3: 3, pygltflib.VEC4: 4,
    }[accessor.type]
    stride = buf_view.byteStride or (comps * 4)
    if stride == comps * 4:
        # tight layout
        arr = np.frombuffer(bin_data, dtype=np.float32, count=count * comps,
                            offset=offset)
        return arr.copy()
    # interleaved/strided: read count rows of stride/4 floats each
    row_floats = stride // 4
    total = count * row_floats
    arr = np.frombuffer(bin_data, dtype=np.float32, count=total, offset=offset)
    out = arr.reshape(count, row_floats)[:, :comps].copy()
    return out.reshape(-1)


def write_accessor_float(gltf: GLTF2, accessor: Accessor, bin_data: bytearray,
                         new_values: np.ndarray):
    """Overwrite float data in place (same length)."""
    buf_view = gltf.bufferViews[accessor.bufferView]
    offset = (buf_view.byteOffset or 0) + (accessor.byteOffset or 0)
    comps = {
        pygltflib.SCALAR: 1, pygltflib.VEC2: 2, pygltflib.VEC3: 3, pygltflib.VEC4: 4,
    }[accessor.type]
    stride = buf_view.byteStride or (comps * 4)
    flat = new_values.reshape(-1).astype(np.float32)
    if len(flat) != accessor.count * comps:
        raise ValueError("length mismatch")
    if stride == comps * 4:
        bin_data[offset:offset + len(flat) * 4] = flat.tobytes()
    else:
        # interleaved: write each vertex at its strided offset
        for i in range(accessor.count):
            p = offset + i * stride
            bin_data[p:p + comps * 4] = flat[i * comps:(i + 1) * comps].tobytes()


def node_world_matrix(gltf: GLTF2, node_idx: int) -> np.ndarray:
    stack = []
    cur = node_idx
    # find root chain by walking parents
    def find_parent(i):
        for p, n in enumerate(gltf.nodes):
            if n.children and i in n.children:
                return p
        return None
    chain = []
    seen = set()
    while cur is not None and cur not in seen:
        chain.append(cur)
        seen.add(cur)
        cur = find_parent(cur)
    chain.reverse()
    M = np.eye(4)
    for i in chain:
        n = gltf.nodes[i]
        if n.matrix is not None:
            m = np.array(n.matrix, dtype=np.float64).reshape(4, 4).T
            M = M @ m
        else:
            T = np.eye(4)
            if n.translation:
                T[:3, 3] = n.translation
            R = np.eye(4)
            if n.rotation:
                q = n.rotation
                x, y, z, w = q
                R[0, 0] = 1 - 2 * (y * y + z * z)
                R[0, 1] = 2 * (x * y - z * w)
                R[0, 2] = 2 * (x * z + y * w)
                R[1, 0] = 2 * (x * y + z * w)
                R[1, 1] = 1 - 2 * (x * x + z * z)
                R[1, 2] = 2 * (y * z - x * w)
                R[2, 0] = 2 * (x * z - y * w)
                R[2, 1] = 2 * (y * z + x * w)
                R[2, 2] = 1 - 2 * (x * x + y * y)
            S = np.eye(4)
            if n.scale:
                S[0, 0], S[1, 1], S[2, 2] = n.scale
            M = M @ (T @ R @ S)
    return M


def analyze(gltf: GLTF2, bin_data: bytes):
    """Compute world bbox and total triangle count."""
    mins = np.full(3, np.inf)
    maxs = np.full(3, -np.inf)
    tri_count = 0
    mesh_stats = []
    for mi, mesh in enumerate(gltf.meshes):
        for pi, prim in enumerate(mesh.primitives):
            if not prim.attributes or getattr(prim.attributes, 'POSITION', None) is None:
                continue
            acc = gltf.accessors[getattr(prim.attributes, 'POSITION')]
            pos = read_accessor_float(gltf, acc, bin_data).reshape(-1, 3)
            # find nodes referencing this mesh
            for ni, node in enumerate(gltf.nodes):
                if node.mesh == mi:
                    M = node_world_matrix(gltf, ni)
                    world = (np.hstack([pos, np.ones((len(pos), 1))]) @ M.T)[:, :3]
                    mins = np.minimum(mins, world.min(axis=0))
                    maxs = np.maximum(maxs, world.max(axis=0))
            if prim.indices is not None:
                idx_acc = gltf.accessors[prim.indices]
                tri_count += idx_acc.count // 3
            elif prim.mode in (None, 4):
                tri_count += acc.count // 3
            elif prim.mode == 5:
                tri_count += acc.count - 2
            else:
                tri_count += acc.count // 3
            mesh_stats.append((mesh.name or f'mesh_{mi}', tri_count, prim.mode))
    return mins, maxs, tri_count, mesh_stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('output', nargs='?')
    ap.add_argument('--target-height', type=float, default=0.5)
    ap.add_argument('--budget', type=int, default=10000)
    ap.add_argument('--up-axis', default='y', choices=['y', 'z', 'x'])
    ap.add_argument('--face-rotate', type=float, default=0.0,
                    help='rotate around Y after up-axis fix (deg), to face +Z')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    gltf = GLTF2.load(args.input)
    bin_data = bytearray(gltf.binary_blob() or b'')

    mins, maxs, tris, mesh_stats = analyze(gltf, bin_data)
    size = maxs - mins
    center = (mins + maxs) / 2
    print(f"[report] input={args.input}")
    print(f"  meshes={len(gltf.meshes)} tris={tris} budget={args.budget} "
          f"({'OK' if tris <= args.budget else 'OVER'})")
    print(f"  bbox min=({mins[0]:.4f},{mins[1]:.4f},{mins[2]:.4f}) "
          f"max=({maxs[0]:.4f},{maxs[1]:.4f},{maxs[2]:.4f})")
    print(f"  size X={size[0]:.4f} Y={size[1]:.4f} Z={size[2]:.4f} "
          f"height={size[1]:.4f} (target {args.target_height})")
    print(f"  mesh stats: {mesh_stats}")
    for i, m in enumerate(gltf.materials or []):
        print(f"  mat[{i}] name={m.name!r} pbr={m.pbrMetallicRoughness is not None}")
        if m.pbrMetallicRoughness:
            pbr = m.pbrMetallicRoughness
            print(f"       baseColorTex={pbr.baseColorTexture is not None} "
                  f"normalTex={m.normalTexture is not None} "
                  f"metalRoughTex={pbr.metallicRoughnessTexture is not None} "
                  f"metallic={pbr.metallicFactor} roughness={pbr.roughnessFactor}")
    if gltf.images:
        for img in gltf.images:
            print(f"  img name={img.name!r} uri={str(img.uri)[:50] if img.uri else None}")

    if args.dry_run:
        print("[dry-run] no write")
        return 0

    # ---- build canonical transform (bake into vertices) ----
    # 1) up-axis fix (only if requested, default none)
    up_rot = np.eye(4)
    if args.up_axis == 'z':
        # rotate -90 around X: z -> y
        a = -math.pi / 2
        c, s = math.cos(a), math.sin(a)
        up_rot = np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]],
                          dtype=np.float64)
    elif args.up_axis == 'x':
        a = math.pi / 2
        c, s = math.cos(a), math.sin(a)
        up_rot = np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]],
                          dtype=np.float64)

    # 2) face rotate (around Y after up fix)
    face_rot = np.eye(4)
    if args.face_rotate:
        a = math.radians(args.face_rotate)
        c, s = math.cos(a), math.sin(a)
        face_rot = np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]],
                            dtype=np.float64)

    world_pre = up_rot @ face_rot  # applied to world coords
    # recompute bbox after world_pre
    pmins = np.full(3, np.inf)
    pmaxs = np.full(3, -np.inf)
    for mi, mesh in enumerate(gltf.meshes):
        for prim in mesh.primitives:
            if not prim.attributes or getattr(prim.attributes, 'POSITION', None) is None:
                continue
            acc = gltf.accessors[getattr(prim.attributes, 'POSITION')]
            pos = read_accessor_float(gltf, acc, bin_data).reshape(-1, 3)
            for ni, node in enumerate(gltf.nodes):
                if node.mesh == mi:
                    M = world_pre @ node_world_matrix(gltf, ni)
                    world = (np.hstack([pos, np.ones((len(pos), 1))]) @ M.T)[:, :3]
                    pmins = np.minimum(pmins, world.min(axis=0))
                    pmaxs = np.maximum(pmaxs, world.max(axis=0))
    psize = pmaxs - pmins
    # 3) scale to target height
    cur_h = psize[1]
    s = args.target_height / cur_h if cur_h > 1e-6 else 1.0
    scale_mat = np.diag([s, s, s, 1.0])
    # 4) anchor: feet center at origin
    # after scale, min y -> 0; x/z centered
    # compute in scaled coords
    sc_min = pmins * s
    sc_max = pmaxs * s
    tx = -(sc_min[0] + sc_max[0]) / 2.0
    tz = -(sc_min[2] + sc_max[2]) / 2.0
    ty = -sc_min[1]
    trans = np.eye(4)
    trans[:3, 3] = [tx, ty, tz]

    final = trans @ scale_mat @ world_pre
    print(f"[transform] up-axis={args.up_axis} face-rotate={args.face_rotate} "
          f"scale={s:.6f} translate=({tx:.4f},{ty:.4f},{tz:.4f})")

    # bake into vertices, reset node transforms
    for mi, mesh in enumerate(gltf.meshes):
        for prim in mesh.primitives:
            if not prim.attributes or getattr(prim.attributes, 'POSITION', None) is None:
                continue
            acc = gltf.accessors[getattr(prim.attributes, 'POSITION')]
            pos = read_accessor_float(gltf, acc, bin_data).reshape(-1, 3)
            for ni, node in enumerate(gltf.nodes):
                if node.mesh == mi:
                    M = final @ node_world_matrix(gltf, ni)
                    world = (np.hstack([pos, np.ones((len(pos), 1))]) @ M.T)[:, :3]
                    write_accessor_float(gltf, acc, bin_data, world)
    for node in gltf.nodes:
        node.matrix = None
        node.translation = None
        node.rotation = None
        node.scale = None

    # ---- rename meshes (保留 L/R 部件语义，供关节动画对位) ----
    def side_of(base: str) -> str:
        if 'left' in base or '_l' in base or base.endswith('_l'):
            return 'L'
        if 'right' in base or '_r' in base or base.endswith('_r'):
            return 'R'
        return ''

    used_mesh = {}
    for mi, mesh in enumerate(gltf.meshes):
        base = snake(mesh.name or f'part_{mi}')
        part = None
        for k, v in MESH_ALIAS.items():
            if k in base:
                part = v
                break
        part = part or 'part'
        side = side_of(base)
        key = part + side
        n = used_mesh.get(key, 0)
        used_mesh[key] = n + 1
        name = f'mesh_{part}' if side == '' else f'mesh_{part}_{side}'
        if n > 0:
            name = f'{name}_{n}'
        mesh.name = name
    print(f"[rename] meshes -> {[m.name for m in gltf.meshes]}")

    # ---- rename materials + normalize PBR ----
    if not gltf.materials:
        gltf.materials = []
    used_mat = {}
    for i, m in enumerate(gltf.materials):
        base = snake(m.name or f'mat_{i}')
        part = None
        for k, v in MAT_ALIAS.items():
            if k in base:
                part = v
                break
        part = part or base or 'default'
        n = used_mat.get(part, 0)
        used_mat[part] = n + 1
        m.name = f'mat_{part}' if n == 0 else f'mat_{part}_{n}'
        if not m.pbrMetallicRoughness:
            m.pbrMetallicRoughness = PbrMetallicRoughness()
        pbr = m.pbrMetallicRoughness
        if pbr.metallicFactor is None:
            pbr.metallicFactor = 0.0
        if pbr.metallicFactor != 0.0:
            pbr.metallicFactor = 0.0  # 鸡无金属部件（spec §1.2）
        if pbr.roughnessFactor is None:
            pbr.roughnessFactor = 0.9
        if pbr.baseColorFactor is None:
            pbr.baseColorFactor = [1, 1, 1, 1]
    print(f"[rename] materials -> {[m.name for m in gltf.materials]}")

    # final report
    fmins, fmaxs, ftris, fstats = analyze(gltf, bin_data)
    fsize = fmaxs - fmins
    print(f"[final] bbox min=({fmins[0]:.4f},{fmins[1]:.4f},{fmins[2]:.4f}) "
          f"max=({fmaxs[0]:.4f},{fmaxs[1]:.4f},{fmaxs[2]:.4f})")
    print(f"[final] size X={fsize[0]:.4f} Y={fsize[1]:.4f} Z={fsize[2]:.4f} "
          f"height={fsize[1]:.4f} tris={ftris} "
          f"({'PASS <= budget' if ftris <= args.budget else 'FAIL > budget'})")
    print(f"[final] feet_y={fmins[1]:.6f} (should be ~0)")

    # serialize
    gltf.set_binary_blob(bytes(bin_data))
    gltf.save(args.output)
    print(f"[write] {args.output}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
