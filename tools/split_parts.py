#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_parts.py — 纯 Python 聚类拆件：单 mesh → 语义部件多 mesh（A' 方案）

输入：单 mesh GLB（文生 3D 产物，如 animal_chicken_brown_r_game.glb）
输出：多 mesh GLB，部件节点命名对齐 spec §3.4：
      mesh_body / mesh_head / mesh_beak / mesh_leg_L / mesh_leg_R / mesh_tail

方法：
  1. 连通分量提取（union-find over triangles）
  2. 语义归组（启发式，基于包围盒空间先验）：
       - leg: 分量完全低于 y_thresh（默认 0.09），按质心 x 分左右
       - beak: 头区里 z 全在最前端（z>0.19）的小独立分量（若与头焊接则并入 head）
       - head: cy>head_thresh 且 z>0 的头部/冠区
       - tail: cz < tail_thresh 的后侧分量
       - body: 其余
  3. 重建 buffer/accessor/mesh/node，单材质沿用，落盘

用法:
  python tools/split_parts.py INPUT.glb OUTPUT.glb [--leg-y 0.09] [--head-cy 0.36] [--tail-z -0.12]

可选参数用于调聚类边界（供失败形态调参）。
"""
import argparse
import sys
import pygltflib
import numpy as np
from pygltflib import (
    GLTF2, Buffer, BufferView, Accessor, Mesh, Primitive, Node, Scene, Asset,
    Image as GLTFImage, Texture, Sampler,
)

PART_ORDER = ['body', 'head', 'beak', 'leg_L', 'leg_R', 'tail']


def read_attr(gltf, bin_data, aidx, comps):
    a = gltf.accessors[aidx]
    bv = gltf.bufferViews[a.bufferView]
    stride = bv.byteStride
    if stride is None or stride == comps * 4:
        off = (bv.byteOffset or 0) + (a.byteOffset or 0)
        return np.frombuffer(bin_data, dtype=np.float32, count=a.count * comps,
                             offset=off).reshape(-1, comps).copy()
    # interleaved: 从 bufferView 起点读整块，再按 accessor.byteOffset 取属性列
    row = stride // 4
    base_off = (bv.byteOffset or 0)
    total = a.count * row
    arr = np.frombuffer(bin_data, dtype=np.float32, count=total, offset=base_off)
    arr = arr.reshape(a.count, row)
    start = (a.byteOffset or 0) // 4
    return arr[:, start:start + comps].copy()


def read_idx(gltf, bin_data, aidx):
    a = gltf.accessors[aidx]
    bv = gltf.bufferViews[a.bufferView]
    off = (bv.byteOffset or 0) + (a.byteOffset or 0)
    comp = a.componentType
    fmt = {5121: 'u1', 5123: 'u2', 5125: 'u4'}[comp]
    return np.frombuffer(bin_data, dtype=np.dtype(fmt), count=a.count, offset=off).copy()


def connected_components(pos, idx):
    n = len(pos)
    parent = np.arange(n)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    tris = idx.reshape(-1, 3)
    for t in tris:
        union(int(t[0]), int(t[1]))
        union(int(t[0]), int(t[2]))
    comps = {}
    for i in range(n):
        r = find(i)
        comps.setdefault(r, []).append(i)
    return list(comps.values())


def classify_component(vlist, pos, leg_y, head_cy, tail_z):
    """Return (part_name, meta) for a component's vertex list."""
    v = pos[vlist]
    mn, mx = v.min(0), v.max(0)
    cy = (mn[1] + mx[1]) / 2
    cz = (mn[2] + mx[2]) / 2
    cx = (mn[0] + mx[0]) / 2
    if mx[1] < leg_y:
        # 腿/脚区
        return ('leg_L' if cx < 0 else 'leg_R'), (mn, mx)
    if cy > head_cy and cz > 0.0:
        # 头区：若为独立小分量且 z 全在最前端 → beak
        if len(vlist) < 300 and mn[2] > 0.19:
            return 'beak', (mn, mx)
        return 'head', (mn, mx)
    if cz < tail_z:
        return 'tail', (mn, mx)
    if cy > head_cy:
        # 高但 z<=0（头后侧/冠后）→ head
        return 'head', (mn, mx)
    return 'body', (mn, mx)


def build_new_glb(parts, pos, normal, uv, idx, tri_map, material, gltf_in=None, bin_data=None):
    """parts: {part_name: [old_vertex_indices...]}. Rebuild multi-mesh GLB.
    若 gltf_in/bin_data 提供，则把原 textures/images/samplers 一并拷入（贴图数据追加到新 buffer），
    避免 material 悬空 texture 引用导致 GLTFLoader 解析失败。"""
    # 每部件：收集三角形（三个顶点都在该部件内），重建索引
    gltf = GLTF2()
    gltf.asset = Asset(version='2.0', generator='split_parts.py')
    gltf.materials = [material] if material is not None else []
    buffer_parts = bytearray()
    accessors = []
    buffer_views = []
    meshes = []
    nodes = []
    scene_nodes = []

    def align(ba, size):
        pad = (size - (len(ba) % size)) % size
        ba.extend(b'\x00' * pad)

    for part in PART_ORDER:
        vlist = parts.get(part)
        if not vlist:
            continue
        old_verts = np.array(sorted(set(vlist)), dtype=np.int64)
        remap = {int(v): i for i, v in enumerate(old_verts)}
        # 三角形：三个顶点都在 old_verts 里（部件内完整）
        tris = idx.reshape(-1, 3)
        mask = np.all(np.isin(tris, old_verts), axis=1)
        part_tris = tris[mask]
        if len(part_tris) == 0:
            continue
        new_idx = np.array([[remap[int(a)], remap[int(b)], remap[int(c)]]
                            for a, b, c in part_tris], dtype=np.uint32).reshape(-1)
        new_pos = pos[old_verts]
        new_nrm = normal[old_verts] if normal is not None else None
        new_uv = uv[old_verts] if uv is not None else None

        # ---- 写入 buffer ----
        # indices (u32, 4-align)
        align(buffer_parts, 4)
        idx_off = len(buffer_parts)
        buffer_parts.extend(new_idx.tobytes())
        idx_len = len(new_idx) * 4

        # position (vec3 f32, 12-align)
        align(buffer_parts, 4)
        pos_off = len(buffer_parts)
        buffer_parts.extend(new_pos.astype(np.float32).tobytes())
        pos_len = len(new_pos) * 12

        nrm_off = uv_off = nrm_len = uv_len = 0
        if new_nrm is not None:
            align(buffer_parts, 4)
            nrm_off = len(buffer_parts)
            buffer_parts.extend(new_nrm.astype(np.float32).tobytes())
            nrm_len = len(new_nrm) * 12
        if new_uv is not None:
            align(buffer_parts, 4)
            uv_off = len(buffer_parts)
            buffer_parts.extend(new_uv.astype(np.float32).tobytes())
            uv_len = len(new_uv) * 8

        # ---- bufferViews / accessors ----
        bvi = BufferView(buffer=0, byteOffset=idx_off, byteLength=idx_len,
                         target=34963)  # ELEMENT_ARRAY_BUFFER
        buffer_views.append(bvi)
        bvp = BufferView(buffer=0, byteOffset=pos_off, byteLength=pos_len,
                         target=34962)  # ARRAY_BUFFER
        buffer_views.append(bvp)
        acc_idx = len(accessors)
        accessors.append(Accessor(bufferView=len(buffer_views) - 2, componentType=5125,
                                  count=len(new_idx), type='SCALAR', min=[int(new_idx.min())],
                                  max=[int(new_idx.max())]))
        acc_pos = len(accessors)
        accessors.append(Accessor(bufferView=len(buffer_views) - 1, componentType=5126,
                                  count=len(new_pos), type='VEC3',
                                  min=[float(new_pos[:, 0].min()), float(new_pos[:, 1].min()), float(new_pos[:, 2].min())],
                                  max=[float(new_pos[:, 0].max()), float(new_pos[:, 1].max()), float(new_pos[:, 2].max())]))
        acc_nrm = acc_uv = None
        if new_nrm is not None:
            buffer_views.append(BufferView(buffer=0, byteOffset=nrm_off, byteLength=nrm_len, target=34962))
            acc_nrm = len(accessors)
            accessors.append(Accessor(bufferView=len(buffer_views) - 1, componentType=5126,
                                      count=len(new_nrm), type='VEC3'))
        if new_uv is not None:
            buffer_views.append(BufferView(buffer=0, byteOffset=uv_off, byteLength=uv_len, target=34962))
            acc_uv = len(accessors)
            accessors.append(Accessor(bufferView=len(buffer_views) - 1, componentType=5126,
                                      count=len(new_uv), type='VEC2'))

        # ---- prim / mesh / node ----
        attributes = {'POSITION': acc_pos}
        if acc_nrm is not None:
            attributes['NORMAL'] = acc_nrm
        if acc_uv is not None:
            attributes['TEXCOORD_0'] = acc_uv
        prim = Primitive(attributes=attributes, indices=acc_idx, material=0 if material is not None else None)
        mesh = Mesh(primitives=[prim], name=f'mesh_{part}')
        meshes.append(mesh)
        node = Node(mesh=len(meshes) - 1, name=f'mesh_{part}')
        nodes.append(node)
        scene_nodes.append(len(nodes) - 1)
        print(f'  [part] {part}: verts={len(new_pos)} tris={len(part_tris)} '
              f'bbox_y=[{new_pos[:,1].min():.3f},{new_pos[:,1].max():.3f}] '
              f'bbox_z=[{new_pos[:,2].min():.3f},{new_pos[:,2].max():.3f}] '
              f'bbox_x=[{new_pos[:,0].min():.3f},{new_pos[:,0].max():.3f}]')

    gltf.buffers = [Buffer(byteLength=len(buffer_parts))]
    gltf.bufferViews = buffer_views
    gltf.accessors = accessors
    gltf.meshes = meshes
    gltf.nodes = nodes
    gltf.scenes = [Scene(nodes=scene_nodes)]
    gltf.scene = 0

    # ---- 拷入原 textures/images/samplers（贴图数据追加到 buffer 尾部） ----
    if gltf_in is not None and bin_data is not None and gltf_in.images:
        img_list = []
        for img in gltf_in.images:
            if img.bufferView is not None:
                old_bv = gltf_in.bufferViews[img.bufferView]
                old_off = (old_bv.byteOffset or 0)
                old_len = old_bv.byteLength
                img_bytes = bytes(bin_data[old_off:old_off + old_len])
                align(buffer_parts, 4)
                new_off = len(buffer_parts)
                buffer_parts.extend(img_bytes)
                bv_img = BufferView(buffer=0, byteOffset=new_off, byteLength=len(img_bytes))
                buffer_views.append(bv_img)
                img_list.append(GLTFImage(name=img.name, bufferView=len(buffer_views) - 1,
                                          mimeType=img.mimeType or 'image/png'))
            else:
                img_list.append(GLTFImage(name=img.name, uri=img.uri, mimeType=img.mimeType))
        if gltf_in.samplers:
            gltf.samplers = list(gltf_in.samplers)
        gltf.images = img_list
        gltf.textures = [Texture(source=t.source, sampler=t.sampler, name=t.name)
                         for t in gltf_in.textures] if gltf_in.textures else []
        gltf.buffers[0].byteLength = len(buffer_parts)

    gltf.set_binary_blob(bytes(buffer_parts))
    return gltf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('output', nargs='?')
    ap.add_argument('--leg-y', type=float, default=0.09)
    ap.add_argument('--head-cy', type=float, default=0.36)
    ap.add_argument('--tail-z', type=float, default=-0.12)
    args = ap.parse_args()

    gltf_in = GLTF2.load(args.input)
    bin_data = gltf_in.binary_blob() or b''

    # 取第一个 mesh prim
    mesh0 = gltf_in.meshes[0]
    prim0 = mesh0.primitives[0]
    pos = read_attr(gltf_in, bin_data, getattr(prim0.attributes, 'POSITION'), 3)
    nrm_acc = getattr(prim0.attributes, 'NORMAL', None)
    uv_acc = getattr(prim0.attributes, 'TEXCOORD_0', None)
    normal = read_attr(gltf_in, bin_data, nrm_acc, 3) if nrm_acc is not None else None
    uv = read_attr(gltf_in, bin_data, uv_acc, 2) if uv_acc is not None else None
    idx = read_idx(gltf_in, bin_data, prim0.indices)
    mat = gltf_in.materials[prim0.material] if (prim0.material is not None and gltf_in.materials) else None

    comps = connected_components(pos, idx)
    print(f'[split] {args.input}: verts={len(pos)} tris={len(idx)//3} components={len(comps)}')

    parts = {p: [] for p in PART_ORDER}
    stats = {}
    for vlist in comps:
        part, (mn, mx) = classify_component(vlist, pos, args.leg_y, args.head_cy, args.tail_z)
        parts[part].extend(vlist)
        stats[part] = stats.get(part, 0) + 1
    print('[assign] components per part:', stats)

    out_gltf = build_new_glb(parts, pos, normal, uv, idx, None, mat, gltf_in=gltf_in, bin_data=bin_data)
    out = args.output or (args.input.rsplit('.glb', 1)[0] + '_multimesh.glb')
    out_gltf.save(out)
    print(f'[write] {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
