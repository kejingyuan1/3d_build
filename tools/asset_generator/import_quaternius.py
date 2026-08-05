# -*- coding: utf-8 -*-
"""
Quaternius OBJ+MTL 资产 → 带纹理的 GLB 转换器
- trimesh 加载 OBJ（保留 UV 坐标）
- 嵌入选定纹理 PNG 到 GLB
- 用 pygltflib 构造 PBR 材质 + baseColorTexture
- 输出符合项目标准：1单位=1米、Y-up、锚点脚底中心、NORMAL+POSITION+TEXCOORD_0
"""
import os, sys, glob, struct, base64
import numpy as np
import trimesh
from pygltflib import (
    GLTF2, Asset, Scene, Node, Mesh, Primitive, Buffer, BufferView,
    Accessor, Image, Texture, Material, PbrMetallicRoughness, Sampler, TextureInfo
)
from PIL import Image as PILImage

# === 路径配置 ===
SRC_BASE = 'assets/quaternius/Textured Models/Finished Textured Buildings/OBJ'
TEX_DIR  = 'assets/quaternius/Textured Models/Textures'
OUT_BASE = 'assets/quaternius_glb'
os.makedirs(OUT_BASE, exist_ok=True)

# 建筑 → 纹理配色（按建筑类型/编号分配，体现差异化，全部用亮色调色板）
BUILDING_TEX = {
    '1Story': 'Light', '1Story_GableRoof': 'Light2', '1Story_RoundRoof': 'Green',
    '1Story_Sign': 'Light',
    '2Story': 'Red', '2Story_2': 'Blue', '2Story_Balcony': 'Yellow',
    '2Story_Center': 'Light2', '2Story_Columns': 'Light', '2Story_Double': 'Red',
    '2Story_GableRoof': 'Blue', '2Story_RoundRoof': 'Light', '2Story_Sidehouse': 'Light2',
    '2Story_Sign': 'Light', '2Story_Slim': 'Light2', '2Story_Stairs': 'Light',
    '2Story_Wide': 'Light2', '2Story_Wide_2Doors': 'Light',
    '3Story_Balcony': 'Light2', '3Story_Slim': 'Light', '3Story_Small': 'Light2',
    '4Story': 'Light', '4Story_Center': 'Light2', '4Story_Wide_2Doors': 'Light',
    '4Story_Wide_2Doors_Roof': 'Light2',
    '6Story_Stack': 'Light2',
}

def load_png_as_bytes(path):
    with open(path, 'rb') as f:
        return f.read()

def obj_to_glb(obj_path, tex_path, out_path):
    """trimesh 加载 OBJ（保留 Scene 多个 mesh），pygltflib 构建带纹理的 GLB"""
    # 1. 加载 OBJ —— 不 force='mesh'，保留原始 Scene 多个 mesh（楼身/屋顶/烟囱/窗户独立）
    scene = trimesh.load(obj_path, process=False)
    if isinstance(scene, trimesh.Scene):
        # 合并所有几何为单个 Trimesh，但每顶点数据要拼接正确
        # trimesh 的 dump() 可以 flatten scene
        geoms = []
        for g in scene.geometry.values():
            if isinstance(g, trimesh.Trimesh):
                geoms.append(g)
        if not geoms:
            raise RuntimeError(f'{obj_path}: 场景无 Trimesh 几何')
        m = trimesh.util.concatenate(geoms)
    else:
        m = scene

    if m.visual.kind != 'texture':
        raise RuntimeError(f'{obj_path}: 没有 UV 纹理')

    verts = np.asarray(m.vertices, dtype=np.float32)
    # 锚点脚底中心
    verts[:, 1] -= verts[:, 1].min()
    # 关键：fix_normals 会改变 m.vertices / m.faces（为每个面复制独立顶点以保证法线独立）
    m.fix_normals()
    # 必须在 fix_normals 之后重新读 verts/idx/uv
    verts = np.asarray(m.vertices, dtype=np.float32)
    norms = np.asarray(m.vertex_normals, dtype=np.float32)
    uvs = np.asarray(m.visual.uv, dtype=np.float32)
    if m.faces.max() < 65536:
        idx = np.asarray(m.faces, dtype=np.uint16)
        idx_type = 5123
    else:
        idx = np.asarray(m.faces, dtype=np.uint32)
        idx_type = 5125

    # 2. 加载贴图
    img_bytes = load_png_as_bytes(tex_path)

    # 3. 拼接 buffer
    vert_stride = 12 + 12 + 8
    vbuf = np.zeros(len(verts) * vert_stride, dtype=np.uint8)
    vbuf_view = vbuf.view(dtype=np.float32).reshape(len(verts), 8)
    vbuf_view[:, 0:3] = verts
    vbuf_view[:, 3:6] = norms
    vbuf_view[:, 6:8] = uvs
    ibuf = idx.tobytes()
    tbuf = img_bytes

    def pad4(b):
        rem = len(b) % 4
        return b + b'\x00' * (4 - rem) if rem else b
    vbuf_p = pad4(vbuf.tobytes())
    ibuf_p = pad4(ibuf)
    tbuf_p = pad4(tbuf)

    # 4. 构造 GLTF2
    g = GLTF2(
        asset=Asset(version='2.0', generator='import_quaternius'),
        scenes=[Scene(nodes=[0])],
        scene=0,
        nodes=[Node(mesh=0)],
        buffers=[Buffer(byteLength=len(vbuf_p) + len(ibuf_p) + len(tbuf_p))],
    )
    vbv_off = 0
    ibv_off = vbv_off + len(vbuf_p)
    tbv_off = ibv_off + len(ibuf_p)
    # 注意：bufferView 字节偏移要对齐到 componentType 大小（GLB 规范）
    # POSITION/NORMAL/UV 都是 float32 → 4 字节对齐；indices 按 idx_type
    g.bufferViews = [
        BufferView(buffer=0, byteOffset=vbv_off, byteLength=len(vbuf_p), byteStride=32, target=34962),
        BufferView(buffer=0, byteOffset=ibv_off, byteLength=len(ibuf_p), target=34963),
        BufferView(buffer=0, byteOffset=tbv_off, byteLength=len(tbuf_p)),
    ]
    g.images = [Image(bufferView=2, mimeType='image/png')]
    # 关键：wrapS/wrapT = 10497 (REPEAT)，这样 UV 超出 [0,1] 也能正确采样
    g.samplers = [Sampler(wrapS=10497, wrapT=10497, magFilter=9728, minFilter=9986)]
    g.textures = [Texture(sampler=0, source=0)]
    g.materials = [Material(
        name='Texture',
        pbrMetallicRoughness=PbrMetallicRoughness(
            baseColorTexture=TextureInfo(index=0, texCoord=0),
            metallicFactor=0.0,
            roughnessFactor=1.0,
        ),
        doubleSided=True,
    )]

    max_pos = verts.max(axis=0).tolist()
    min_pos = verts.min(axis=0).tolist()
    g.accessors = [
        Accessor(bufferView=0, byteOffset=0,  componentType=5126, count=len(verts), type='VEC3', max=max_pos, min=min_pos),
        Accessor(bufferView=0, byteOffset=12, componentType=5126, count=len(verts), type='VEC3', max=[1,1,1], min=[-1,-1,-1]),
        Accessor(bufferView=0, byteOffset=24, componentType=5126, count=len(verts), type='VEC2', max=[uvs.max(axis=0).tolist()], min=[uvs.min(axis=0).tolist()]),
        Accessor(bufferView=1, byteOffset=0, componentType=idx_type, count=int(idx.size), type='SCALAR', max=[int(idx.max())], min=[int(idx.min())]),
    ]
    g.meshes = [Mesh(primitives=[Primitive(
        attributes={'POSITION': 0, 'NORMAL': 1, 'TEXCOORD_0': 2},
        indices=3, material=0, mode=4,
    )])]

    g.set_binary_blob(vbuf_p + ibuf_p + tbuf_p)
    g.save(out_path)
    return len(vbuf_p) + len(ibuf_p) + len(tbuf_p)

# === 批量转换 ===
results = []
ok = 0
fail = 0
for name, tex_name in BUILDING_TEX.items():
    obj_path = os.path.join(SRC_BASE, f'{name}.obj')
    tex_path = os.path.join(TEX_DIR, f'Texture_{tex_name}.png')
    out_path = os.path.join(OUT_BASE, f'building_quaternius_{name}.glb')
    if not os.path.exists(obj_path):
        print(f'  ✗ {name}: OBJ 不存在')
        fail += 1
        continue
    if not os.path.exists(tex_path):
        print(f'  ✗ {name}: 贴图 {tex_name} 不存在')
        fail += 1
        continue
    try:
        size = obj_to_glb(obj_path, tex_path, out_path)
        print(f'  ✓ {name:30s} → {tex_name:10s} {size/1024:.1f} KB')
        results.append((name, tex_name, out_path, size))
        ok += 1
    except Exception as e:
        print(f'  ✗ {name}: {e}')
        fail += 1

print(f'\n转换完成: {ok} 成功 / {fail} 失败')
