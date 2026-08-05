#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
finalize_cc0.py — 给 CC0 鸡 GLB 加 eat/walk 动画 + 重命名 mesh/mat
用法: python tools/finalize_cc0.py INPUT.glb CLIPS.json OUTPUT.glb
"""
import json
import sys
import numpy as np
import pygltflib
from pygltflib import BufferView, Accessor, Animation, AnimationChannel, AnimationChannelTarget, AnimationSampler


def main():
    input_glb, clips_json, output_glb = sys.argv[1], sys.argv[2], sys.argv[3]
    gltf = pygltflib.GLTF2.load(input_glb)
    blob = bytearray(gltf.binary_blob() or b'')

    # ---- 重命名 mesh / mat ----
    for node in gltf.nodes:
        if node.mesh is not None and (not node.name or node.name.startswith('Object') or node.name == 'CHICKEN_'):
            node.name = 'mesh_body'
    for mat in gltf.materials:
        mat.name = 'mat_base'
    print('[rename] mesh nodes + mat -> mesh_body / mat_base')

    name2idx = {}
    for i, n in enumerate(gltf.nodes):
        if n.name:
            name2idx[n.name] = i

    clips = json.load(open(clips_json, encoding='utf-8'))['clips']

    def align(size):
        pad = (size - (len(blob) % size)) % size
        blob.extend(b'\x00' * pad)

    # 替换旧的 eat/walk（避免重复追加）
    animations = [a for a in (gltf.animations or []) if a.name not in ('eat', 'walk')]
    for clip in clips:
        channels, samplers = [], []
        added = 0
        for track in clip['tracks']:
            node_idx = name2idx.get(track['node'])
            if node_idx is None:
                continue
            times = track['times']
            vals = track['values']
            comps = 4 if track['path'] == 'rotation' else 3
            if not times or not vals or len(vals) % comps != 0:
                continue
            # input accessor
            align(4)
            in_off = len(blob)
            blob.extend(np.asarray(times, dtype=np.float32).tobytes())
            bv_in = BufferView(buffer=0, byteOffset=in_off, byteLength=len(times) * 4)
            gltf.bufferViews.append(bv_in)
            acc_in = Accessor(bufferView=len(gltf.bufferViews) - 1, componentType=5126,
                              count=len(times), type='SCALAR',
                              min=[float(min(times))], max=[float(max(times))])
            gltf.accessors.append(acc_in)
            # output accessor
            align(4)
            out_off = len(blob)
            blob.extend(np.asarray(vals, dtype=np.float32).tobytes())
            bv_out = BufferView(buffer=0, byteOffset=out_off, byteLength=len(vals) * 4)
            gltf.bufferViews.append(bv_out)
            acc_out = Accessor(bufferView=len(gltf.bufferViews) - 1, componentType=5126,
                               count=len(vals) // comps, type='VEC4' if comps == 4 else 'VEC3')
            gltf.accessors.append(acc_out)
            sampler = AnimationSampler(input=len(gltf.accessors) - 2, output=len(gltf.accessors) - 1,
                                       interpolation='LINEAR')
            samplers.append(sampler)
            channel = AnimationChannel(sampler=len(samplers) - 1,
                                       target=AnimationChannelTarget(node=node_idx, path=track['path']))
            channels.append(channel)
            added += 1
        if channels:
            animations.append(Animation(name=clip['name'], channels=channels, samplers=samplers))
            print(f'[anim] {clip["name"]}: duration={clip["duration"]:.2f}s channels={len(channels)}')
        else:
            print(f'[anim] {clip["name"]}: SKIPPED (no matching nodes)')
    gltf.animations = animations

    gltf.buffers[0].byteLength = len(blob)
    gltf.set_binary_blob(bytes(blob))
    gltf.save(output_glb)
    print(f'[write] {output_glb}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
