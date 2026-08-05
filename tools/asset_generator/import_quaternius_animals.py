# -*- coding: utf-8 -*-
"""Quaternius 5 Animals (无贴图) → GLB：用 MTL Kd 颜色作 baseColor"""
import os, numpy as np, trimesh
from pygltflib import (GLTF2, Asset, Scene, Node, Mesh, Primitive, Buffer, BufferView,
    Accessor, Material, PbrMetallicRoughness)

SRC = 'assets/quaternius_animals5/OBJ'
OUT = 'assets/quaternius_animals5_glb'
os.makedirs(OUT, exist_ok=True)

# 5 个动物的预设 baseColor（参考 Quaternius 网站预览色）
ANIMAL_COLOR = {
    'bird':      [0x9F, 0xB8, 0xC8],  # 浅蓝灰
    'Chick':     [0xFF, 0xC8, 0x4A],  # 小鸡黄
    'Fish':      [0xFF, 0x6B, 0x35],  # 鱼橙红
    'Red Fox':   [0xE6, 0x4A, 0x29],  # 狐狸红
    'Whale':     [0x4A, 0x6B, 0x8A],  # 鲸深蓝
}

def load_mtl_color(name):
    """读 MTL 文件取 Kd 颜色"""
    mtl_path = os.path.join(SRC, f'{name}.mtl')
    if not os.path.exists(mtl_path):
        return [200, 200, 200]
    with open(mtl_path) as f:
        for line in f:
            if line.startswith('Kd'):
                parts = line.split()
                if len(parts) >= 4:
                    return [int(float(parts[1])*255), int(float(parts[2])*255), int(float(parts[3])*255)]
    return [200, 200, 200]

def obj_to_glb(name, base_color, scale=0.05):
    obj_path = os.path.join(SRC, f'{name}.obj')
    scene = trimesh.load(obj_path, process=False)
    if isinstance(scene, trimesh.Scene):
        geoms = [g for g in scene.geometry.values() if isinstance(g, trimesh.Trimesh)]
        m = trimesh.util.concatenate(geoms)
    else:
        m = scene

    verts = np.asarray(m.vertices, dtype=np.float32)
    # 锚点：底部中心（min y 归 0）
    verts[:, 1] -= verts[:, 1].min()
    m.fix_normals()
    # 关键：fix_normals 之后重新读 verts，并先 fix_normals 再 scale
    verts = np.asarray(m.vertices, dtype=np.float32)
    # 锚点 + 缩放（fix_normals 之后应用）
    verts[:, 1] -= verts[:, 1].min()
    verts *= scale
    norms = np.asarray(m.vertex_normals, dtype=np.float32)
    if m.faces.max() < 65536:
        idx = np.asarray(m.faces, dtype=np.uint16)
        idx_type = 5123
    else:
        idx = np.asarray(m.faces, dtype=np.uint32)
        idx_type = 5125

    # 单 baseColor，不嵌入贴图
    vert_stride = 12 + 12  # position + normal
    vbuf = np.zeros(len(verts) * vert_stride, dtype=np.uint8)
    vbuf_view = vbuf.view(dtype=np.float32).reshape(len(verts), 6)
    vbuf_view[:, 0:3] = verts
    vbuf_view[:, 3:6] = norms
    ibuf = idx.tobytes()

    def pad4(b):
        rem = len(b) % 4
        return b + b'\x00' * (4 - rem) if rem else b
    vbuf_p = pad4(vbuf.tobytes())
    ibuf_p = pad4(ibuf)

    # 归一化 baseColor 0-1
    bc = [c/255.0 for c in base_color]
    g = GLTF2(
        asset=Asset(version='2.0', generator='import_quaternius_animals'),
        scenes=[Scene(nodes=[0])], scene=0,
        nodes=[Node(mesh=0)],
        buffers=[Buffer(byteLength=len(vbuf_p) + len(ibuf_p))],
    )
    g.bufferViews = [
        BufferView(buffer=0, byteOffset=0, byteLength=len(vbuf_p), byteStride=24, target=34962),
        BufferView(buffer=0, byteOffset=len(vbuf_p), byteLength=len(ibuf_p), target=34963),
    ]
    g.materials = [Material(
        name=name,
        pbrMetallicRoughness=PbrMetallicRoughness(
            baseColorFactor=bc + [1.0],
            metallicFactor=0.0, roughnessFactor=1.0,
        ),
        doubleSided=True,
    )]
    g.accessors = [
        Accessor(bufferView=0, byteOffset=0,  componentType=5126, count=len(verts), type='VEC3',
                 max=verts.max(axis=0).tolist(), min=verts.min(axis=0).tolist()),
        Accessor(bufferView=0, byteOffset=12, componentType=5126, count=len(verts), type='VEC3',
                 max=[1,1,1], min=[-1,-1,-1]),
        Accessor(bufferView=1, byteOffset=0, componentType=idx_type, count=int(idx.size), type='SCALAR',
                 max=[int(idx.max())], min=[int(idx.min())]),
    ]
    g.meshes = [Mesh(primitives=[Primitive(
        attributes={'POSITION': 0, 'NORMAL': 1}, indices=2, material=0, mode=4,
    )])]
    g.set_binary_blob(vbuf_p + ibuf_p)
    out_path = os.path.join(OUT, f'quaternius_{name}.glb')
    g.save(out_path)
    return os.path.getsize(out_path)

ok = 0
for name in ['bird', 'Chick', 'Fish', 'Red Fox', 'Whale']:
    color = ANIMAL_COLOR.get(name, load_mtl_color(name))
    try:
        size = obj_to_glb(name, color)
        print(f'  ✓ {name:10s} 颜色={color} {size/1024:.1f} KB')
        ok += 1
    except Exception as e:
        print(f'  ✗ {name}: {e}')

print(f'\n转换完成: {ok}/5')
