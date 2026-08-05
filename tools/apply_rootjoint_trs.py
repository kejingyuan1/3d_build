#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_rootjoint_trs.py — 修复：把 scale/translation 加到真正的骨骼根 _rootJoint (skin.joints[0])
+ 权重归一化 + 材质 OPAQUE
（skinned mesh 蒙皮的世界变换来自 rootJoint，不是 scene 根节点）
用法: python tools/apply_rootjoint_trs.py INPUT.glb OUTPUT.glb --scale 0.0107 --tx -0.1155 --ty 0.250 --tz 0.0337
"""
import argparse
import sys
import numpy as np
import pygltflib


def read_acc(gltf, bin_data, aidx, comps, dtype=np.float32):
    a = gltf.accessors[aidx]
    bv = gltf.bufferViews[a.bufferView]
    off = (bv.byteOffset or 0) + (a.byteOffset or 0)
    return np.frombuffer(bin_data, dtype=dtype, count=a.count * comps, offset=off).copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--scale', type=float, default=0.0107)
    ap.add_argument('--tx', type=float, default=0.0)
    ap.add_argument('--ty', type=float, default=0.0)
    ap.add_argument('--tz', type=float, default=0.0)
    ap.add_argument('--normalize-weights', action='store_true', default=True)
    args = ap.parse_args()

    gltf = pygltflib.GLTF2.load(args.input)
    bin_data = bytearray(gltf.binary_blob() or b'')

    if not gltf.skins:
        print('[error] no skins found!')
        return 1
    skin = gltf.skins[0]
    root_idx = skin.joints[0]
    node = gltf.nodes[root_idx]
    print(f'[before] rootJoint idx={root_idx} name={node.name!r} scale={node.scale} translation={node.translation}')
    node.scale = [args.scale, args.scale, args.scale]
    node.translation = [args.tx, args.ty, args.tz]
    print(f'[after ] rootJoint scale={node.scale} translation={node.translation}')

    # ---- 权重归一化（每顶点 4 权重和为 1；和为 0 时兜底设 [1,0,0,0]） ----
    if args.normalize_weights and skin and gltf.meshes:
        mesh = gltf.meshes[0]
        fixed = 0
        for pr in mesh.primitives:
            wa = getattr(pr.attributes, 'WEIGHTS_0', None)
            ja = getattr(pr.attributes, 'JOINTS_0', None)
            if wa is None or ja is None:
                continue
            acc_w = gltf.accessors[wa]
            acc_j = gltf.accessors[ja]
            # 权重是 VEC4 f32
            n = acc_w.count
            comps_w = 4
            wv = read_acc(gltf, bytes(bin_data), wa, comps_w).reshape(-1, 4)
            # 找到权重 accessor 在 buffer 的 offset，直接改写
            def write_back(acc, data):
                bv = gltf.bufferViews[acc.bufferView]
                off = (bv.byteOffset or 0) + (acc.byteOffset or 0)
                bin_data[off:off + data.nbytes] = data.tobytes()
            sums = wv.sum(axis=1)
            bad = np.abs(sums - 1.0) > 0.01
            fixed += int(bad.sum())
            for i in np.where(bad)[0]:
                if sums[i] > 0.0001:
                    wv[i] = wv[i] / sums[i]
                else:
                    wv[i] = [1.0, 0.0, 0.0, 0.0]
            write_back(acc_w, wv.astype(np.float32))
        print(f'[weights] normalized {fixed} vertices (sum != 1)')

    # ---- 材质强制 OPAQUE（作者 alphaMode=BLEND 会导致透明不可见） ----
    for m in gltf.materials:
        m.alphaMode = 'OPAQUE'
        m.doubleSided = False
        print(f'[mat] {m.name!r} alphaMode -> OPAQUE')

    gltf.buffers[0].byteLength = len(bin_data)
    gltf.set_binary_blob(bytes(bin_data))
    gltf.save(args.output)
    print(f'[write] {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
