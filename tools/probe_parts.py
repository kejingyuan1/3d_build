#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_parts.py — 探查多部件 GLB 的部件结构（mesh 名 / 各自 bbox / 连通性 / 铰链建议）
用法: python tools/probe_parts.py INPUT.glb
"""
import collections
import sys
import pygltflib
import numpy as np


def read_accessor(gltf, bin_data, aidx, comps):
    a = gltf.accessors[aidx]
    bv = gltf.bufferViews[a.bufferView]
    off = (bv.byteOffset or 0) + (a.byteOffset or 0)
    stride = bv.byteStride or (comps * 4)
    if stride == comps * 4:
        return np.frombuffer(bin_data, dtype=np.float32, count=a.count * comps,
                             offset=off).reshape(-1, comps).copy()
    row = stride // 4
    total = a.count * row
    arr = np.frombuffer(bin_data, dtype=np.float32, count=total, offset=off)
    return arr.reshape(a.count, row)[:, :comps].copy()


def read_idx(gltf, bin_data, aidx):
    a = gltf.accessors[aidx]
    bv = gltf.bufferViews[a.bufferView]
    off = (bv.byteOffset or 0) + (a.byteOffset or 0)
    comp = a.componentType
    fmt = {5121: 'u1', 5123: 'u2', 5125: 'u4'}[comp]
    return np.frombuffer(bin_data, dtype=np.dtype(fmt), count=a.count, offset=off).copy()


def main(path):
    gltf = pygltflib.GLTF2.load(path)
    bin_data = gltf.binary_blob() or b''
    print(f'=== probe_parts: {path} ===')
    print(f'nodes={len(gltf.nodes or [])} meshes={len(gltf.meshes or [])} '
          f'materials={len(gltf.materials or [])} skins={len(gltf.skins or [])} '
          f'animations={len(gltf.animations or [])}')
    # node hierarchy
    for i, n in enumerate(gltf.nodes or []):
        print(f'  node[{i}] name={n.name!r} mesh={n.mesh} children={n.children} '
              f'skin={n.skin} tr={n.translation} rot={n.rotation} sc={n.scale}')
    # per-mesh info
    for mi, m in enumerate(gltf.meshes or []):
        for pi, pr in enumerate(m.primitives):
            if not pr.attributes or getattr(pr.attributes, 'POSITION', None) is None:
                continue
            pos = read_accessor(gltf, bin_data, getattr(pr.attributes, 'POSITION'), 3)
            idx = read_idx(gltf, bin_data, pr.indices) if pr.indices is not None else None
            tris = len(idx) // 3 if idx is not None else len(pos) // 3
            mn, mx = pos.min(0), pos.max(0)
            # hinge suggestions
            size = mx - mn
            cy = (mn[1] + mx[1]) / 2
            print(f'  mesh[{mi}] name={m.name!r} verts={len(pos)} tris={tris}')
            print(f'      bbox min={mn} max={mx} size={size}')
            print(f'      center=({(mn[0]+mx[0])/2:.3f}, {cy:.3f}, {(mn[2]+mx[2])/2:.3f})')
            # connectivity within this mesh
            if idx is not None:
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
                for t in idx.reshape(-1, 3):
                    union(int(t[0]), int(t[1]))
                    union(int(t[0]), int(t[2]))
                roots = collections.Counter(find(i) for i in range(n))
                print(f'      connected components: {len(roots)}')
    print('[hinge hints] leg=top(bmax.y) head=bottom(bmin.y) beak=side-toward-head')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: python tools/probe_parts.py INPUT.glb')
        sys.exit(1)
    main(sys.argv[1])
