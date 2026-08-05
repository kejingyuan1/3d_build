#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
align_glb_py.py — 纯 Python 对齐 CC0 带骨骼 GLB（不破坏 skin/动画/纹理）
方法：计算 bind-pose 世界 bbox → 缩放 0.5m / 脚底 y=0 / x,z 居中
      → 新建根 Group 节点(带 scale+translation)挂到 scene 根，原根节点变其子
      → 顶点/骨骼/动画/纹理全部不动（glTF node TRS 不参与动画通道）
用法: python tools/align_glb_py.py INPUT.glb OUTPUT.glb [--target-h 0.5] [--face-rot 0]
"""
import argparse
import math
import sys
import numpy as np
import pygltflib


def read_attr(gltf, bin_data, aidx, comps):
    a = gltf.accessors[aidx]
    bv = gltf.bufferViews[a.bufferView]
    stride = bv.byteStride
    if stride is None or stride == comps * 4:
        off = (bv.byteOffset or 0) + (a.byteOffset or 0)
        return np.frombuffer(bin_data, dtype=np.float32, count=a.count * comps,
                             offset=off).reshape(-1, comps).copy()
    row = stride // 4
    base_off = (bv.byteOffset or 0)
    total = a.count * row
    arr = np.frombuffer(bin_data, dtype=np.float32, count=total, offset=base_off)
    arr = arr.reshape(a.count, row)
    start = (a.byteOffset or 0) // 4
    return arr[:, start:start + comps].copy()


def node_chain(gltf, node_idx):
    """父链（从根到 node）"""
    def find_parent(i):
        for p, n in enumerate(gltf.nodes):
            if n.children and i in n.children:
                return p
        return None
    chain = []
    cur = node_idx
    seen = set()
    while cur is not None and cur not in seen:
        chain.append(cur)
        seen.add(cur)
        cur = find_parent(cur)
    return list(reversed(chain))


def node_matrix(gltf, node_idx):
    M = np.eye(4)
    for i in node_chain(gltf, node_idx):
        n = gltf.nodes[i]
        T = np.eye(4)
        if n.translation:
            T[:3, 3] = n.translation
        R = np.eye(4)
        if n.rotation:
            x, y, z, w = n.rotation
            R[:3, :3] = np.array([
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
            ])
        S = np.eye(4)
        if n.scale:
            S[0, 0], S[1, 1], S[2, 2] = n.scale
        M = M @ T @ R @ S
    return M


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--target-h', type=float, default=0.5)
    ap.add_argument('--face-rot', type=float, default=0.0)
    args = ap.parse_args()

    gltf = pygltflib.GLTF2.load(args.input)
    bin_data = gltf.binary_blob() or b''

    # 计算 bind-pose 世界 bbox（遍历 mesh prim 的 POSITION × mesh 节点世界矩阵）
    mins = np.full(3, np.inf)
    maxs = np.full(3, -np.inf)
    mesh_nodes = []
    for i, n in enumerate(gltf.nodes):
        if n.mesh is not None:
            mesh_nodes.append(i)
    if not mesh_nodes:
        print('[align] no mesh nodes found!')
        return 1
    for mi in mesh_nodes:
        M = node_matrix(gltf, mi)
        for pr in gltf.meshes[gltf.nodes[mi].mesh].primitives:
            if not pr.attributes or getattr(pr.attributes, 'POSITION', None) is None:
                continue
            pos = read_attr(gltf, bin_data, getattr(pr.attributes, 'POSITION'), 3)
            homo = np.hstack([pos, np.ones((len(pos), 1))])
            world = (homo @ M.T)[:, :3]
            mins = np.minimum(mins, world.min(axis=0))
            maxs = np.maximum(maxs, world.max(axis=0))
    size = maxs - mins
    h = size[1]
    print(f'[align] raw bbox min={mins} max={maxs} size={size}')

    scale = args.target_h / h if h > 0 else 1.0
    # 绕 Y 旋转（face-rot）后坐标：x' = x*cos + z*sin; z' = -x*sin + z*cos (绕Y角)
    a = math.radians(args.face_rot)
    c, s = math.cos(a), math.sin(a)
    # 旋转后的 bbox
    corners = np.array([[mins[0], mins[2]], [mins[0], maxs[2]], [maxs[0], mins[2]], [maxs[0], maxs[2]]])
    rot_c = corners @ np.array([[c, -s], [s, c]])
    rmin_x, rmin_z = rot_c[:, 0].min() * scale, rot_c[:, 1].min() * scale
    rmax_x, rmax_z = rot_c[:, 0].max() * scale, rot_c[:, 1].max() * scale
    tx = -(rmin_x + rmax_x) / 2
    tz = -(rmin_z + rmax_z) / 2
    ty = -mins[1] * scale
    print(f'[align] scale={scale:.4f} rotY={args.face_rot} t=({tx:.4f},{ty:.4f},{tz:.4f})')

    # 新建根 Group node：scene.nodes[0] 变为其 child
    root_old = gltf.scenes[gltf.scene or 0].nodes[0]
    rot_node = None
    if args.face_rot != 0:
        rot_node = len(gltf.nodes)
        gltf.nodes.append(pygltflib.Node(
            name='aligned_rot',
            rotation=[0, math.sin(a / 2), 0, math.cos(a / 2)],
            children=[root_old],
        ))
        root_old = rot_node
    align_idx = len(gltf.nodes)
    gltf.nodes.append(pygltflib.Node(
        name='aligned_root',
        scale=[scale, scale, scale],
        translation=[tx, ty, tz],
        children=[root_old],
    ))
    gltf.scenes[gltf.scene or 0].nodes = [align_idx]
    gltf.save(args.output)
    print(f'[write] {args.output} (added root node #{align_idx} aligned_root)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
