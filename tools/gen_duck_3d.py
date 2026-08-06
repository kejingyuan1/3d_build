"""3D 鸭子建模 + HY3 贴图映射（真半写实）
- 程序化 3D 几何：capsule 身体 / 椭球头+嘴+眼+毛簇 / 圆柱腿 / 3 趾脚
- HY3 贴图作为 baseColorTexture（不烘焙到 vertex color，保留原图细节）
- 4 mesh 独立：body / neck_group(head+beak+eyes+tuft) / foot_l / foot_r
- 走路/低头动画：neck_group.rotation.x 低头，body 走路
"""
import os, sys, struct, json
import numpy as np
import trimesh


def _color_vertex(m, color):
    c = np.tile(list(color) + [255], (len(m.vertices), 1)).astype(np.uint8)
    m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=c)
    return m


# ================ 部件（程序化 3D 几何） ================

def build_body():
    """白身体：capsule（前后圆头流线型），HY3 贴图 UV 用圆柱展开"""
    # capsule = cylinder + 2 半球
    radius = 0.16
    length = 0.25  # 圆柱段长
    cyl = trimesh.creation.cylinder(radius=radius, height=length, sections=24)
    cyl.apply_translation([0, 0, 0])
    # 半球（前后各一）
    s1 = trimesh.creation.uv_sphere(radius=radius, count=[24, 12])
    s1.apply_translation([0, 0, length / 2])
    s2 = trimesh.creation.uv_sphere(radius=radius, count=[24, 12])
    s2.apply_translation([0, 0, -length / 2])
    s2.apply_scale([1, 1, -1])  # 翻转
    body = trimesh.util.concatenate([cyl, s1, s2])
    body.apply_translation([0, 0.20, 0])
    _color_vertex(body, (0xF8, 0xF8, 0xF5))  # 白兜底
    return body


def build_neck_group():
    """脖子+头+嘴+眼+毛簇（一个 group mesh）"""
    parts = []
    # 脖子（短圆柱）
    neck = trimesh.creation.cylinder(radius=0.055, height=0.08, sections=16)
    neck.apply_translation([0, 0.0, 0.05])
    _color_vertex(neck, (0xF5, 0xF5, 0xF0))
    parts.append(neck)
    # 头（椭球）
    head = trimesh.creation.uv_sphere(radius=0.095, count=[24, 12])
    head.apply_scale([1.0, 0.95, 1.15])
    head.apply_translation([0, 0.06, 0.10])
    _color_vertex(head, (0xF5, 0xF5, 0xF0))
    parts.append(head)
    # 嘴（上嘴：扁圆锥，黄色）
    beak_up = trimesh.creation.cone(radius=0.045, height=0.06, sections=16)
    beak_up.apply_scale([1.6, 0.5, 2.0])  # 扁嘴
    beak_up.apply_translation([0, 0.07, 0.21])  # 头部前方下方
    _color_vertex(beak_up, (0xFF, 0xC8, 0x4A))
    parts.append(beak_up)
    # 嘴（下嘴：小一圈）
    beak_lo = trimesh.creation.cone(radius=0.035, height=0.04, sections=16)
    beak_lo.apply_scale([1.5, 0.45, 1.8])
    beak_lo.apply_translation([0, 0.045, 0.19])
    _color_vertex(beak_lo, (0xFF, 0xC8, 0x4A))
    parts.append(beak_lo)
    # 眼睛（左右小球）
    for side in (-1, 1):
        eye = trimesh.creation.uv_sphere(radius=0.012, count=[8, 6])
        eye.apply_translation([0.055 * side, 0.10, 0.18])
        _color_vertex(eye, (0x08, 0x08, 0x08))
        parts.append(eye)
    # 头顶黑毛簇（5 根短锥）
    tuft_pos = [
        (0, 0.165, 0.08), (-0.025, 0.16, 0.075), (0.025, 0.16, 0.075),
        (-0.012, 0.155, 0.10), (0.012, 0.155, 0.10),
    ]
    for tx, ty, tz in tuft_pos:
        tuft = trimesh.creation.cone(radius=0.014, height=0.045, sections=6)
        tuft.apply_translation([tx, ty, tz])
        # 微后倾
        R = trimesh.transformations.rotation_matrix(np.radians(-15), [1, 0, 0])
        tuft.apply_transform(R)
        _color_vertex(tuft, (0x08, 0x08, 0x08))
        parts.append(tuft)
    ng = trimesh.util.concatenate(parts)
    ng.apply_translation([0, 0.32, 0.08])  # 整体抬到脖子顶
    return ng


def build_foot():
    """腿（白色圆柱）+ 脚掌（黄色 box，3 趾）"""
    parts = []
    # 腿
    leg = trimesh.creation.cylinder(radius=0.025, height=0.20, sections=12)
    leg.apply_translation([0, -0.10, 0])
    _color_vertex(leg, (0xF5, 0xF5, 0xF0))
    parts.append(leg)
    # 脚掌（黄色扁 box）
    foot = trimesh.creation.box(extents=[0.10, 0.025, 0.13])
    foot.apply_translation([0, -0.215, 0.06])
    _color_vertex(foot, (0xFF, 0xC8, 0x4A))
    parts.append(foot)
    # 3 趾（前向，0° 中央，±25°）
    for ang in (-25, 0, 25):
        toe = trimesh.creation.box(extents=[0.03, 0.018, 0.08])
        toe.apply_translation([0, -0.218, 0.10])
        if ang != 0:
            R = trimesh.transformations.rotation_matrix(np.radians(ang), [0, 1, 0])
            toe.apply_transform(R)
        _color_vertex(toe, (0xFF, 0xC8, 0x4A))
        parts.append(toe)
    # 2 蹼（连接趾）
    for ang in (-12, 12):
        web = trimesh.creation.box(extents=[0.08, 0.013, 0.03])
        web.apply_translation([0, -0.215, 0.085])
        if ang != 0:
            R = trimesh.transformations.rotation_matrix(np.radians(ang), [0, 1, 0])
            web.apply_transform(R)
        _color_vertex(web, (0xFF, 0xC8, 0x4A))
        parts.append(web)
    return trimesh.util.concatenate(parts)


# ================ 球面/胶囊 UV ================
def sphere_uv_from_verts(verts):
    """球面 UV：u=atan2(z,x)/2π+0.5，v=acos(y/r)/π，u 偏移 0.5 让图中心对正面"""
    r = np.linalg.norm(verts, axis=1) + 1e-9
    u = (np.arctan2(verts[:, 2], verts[:, 0]) / (2 * np.pi) + 0.5) % 1.0
    v = np.arccos(np.clip(verts[:, 1] / r, -1, 1)) / np.pi
    u = (u + 0.5) % 1.0
    return np.column_stack([u, v]).astype(np.float32)

def capsule_uv_from_verts(verts, length, radius):
    """胶囊 UV：圆柱段用 (u=atan2(z,x)/2π+0.5, v=z/length+0.5)，半球用球面 UV"""
    r = np.linalg.norm(verts, axis=1)
    # 区分：圆柱段 |z| < length/2，球面 |z| >= length/2 - radius
    is_cyl = (np.abs(verts[:, 2]) < length / 2) & (r > 0.001)
    # 圆柱
    u_cyl = (np.arctan2(verts[:, 2], verts[:, 0]) / (2 * np.pi) + 0.5) % 1.0
    v_cyl = verts[:, 2] / length + 0.5
    # 半球
    u_sph = (np.arctan2(verts[:, 2], verts[:, 0]) / (2 * np.pi) + 0.5) % 1.0
    v_sph = np.arccos(np.clip(verts[:, 1] / (r + 1e-9), -1, 1)) / np.pi
    u = np.where(is_cyl, u_cyl, u_sph)
    v = np.where(is_cyl, v_cyl, v_sph)
    u = (u + 0.5) % 1.0
    return np.column_stack([u, v]).astype(np.float32)


# ================ GLB 导出（带 UV） ================
def export_duck_glb(meshes, uvs, out_path):
    bin_parts = []
    cur = 0
    view_info = []
    for i in range(4):
        m, uv = meshes[i], uvs[i]
        pos = np.ascontiguousarray(m.vertices, dtype=np.float32)
        nrm = np.ascontiguousarray(m.vertex_normals, dtype=np.float32)
        # 顶点色保留（兜底白色）
        if hasattr(m.visual, 'vertex_colors') and m.visual.vertex_colors is not None and len(m.visual.vertex_colors) == len(m.vertices):
            col = np.ascontiguousarray(m.visual.vertex_colors[:, :3].astype(np.float32) / 255.0)
        else:
            col = np.ascontiguousarray(np.full((len(m.vertices), 3), 0.96, dtype=np.float32))
        uv_arr = np.ascontiguousarray(uv, dtype=np.float32)
        idx = np.ascontiguousarray(m.faces.astype(np.uint32).flatten())
        for b, target in [(pos.tobytes(), 34962), (nrm.tobytes(), 34962),
                          (col.tobytes(), 34962), (uv_arr.tobytes(), 34962),
                          (idx.tobytes(), 34963)]:
            pad = (-cur) % 4
            if pad:
                bin_parts.append(b'\x00' * pad)
                cur += pad
            bin_parts.append(b)
            view_info.append((cur, len(b), target))
            cur += len(b)
    bin_data = b''.join(bin_parts)

    buffer_views = []
    accessors = []
    mesh_prims = []
    acc = 0
    for i in range(4):
        m, uv = meshes[i], uvs[i]
        p_off, p_len, _ = view_info[i * 5 + 0]
        n_off, n_len, _ = view_info[i * 5 + 1]
        c_off, c_len, _ = view_info[i * 5 + 2]
        u_off, u_len, _ = view_info[i * 5 + 3]
        ix_off, ix_len, _ = view_info[i * 5 + 4]
        pos = np.ascontiguousarray(m.vertices, dtype=np.float32)
        uv_arr = np.ascontiguousarray(uv, dtype=np.float32)
        idx = np.ascontiguousarray(m.faces.astype(np.uint32).flatten())
        buffer_views.extend([
            {"buffer": 0, "byteOffset": p_off, "byteLength": p_len, "target": 34962},
            {"buffer": 0, "byteOffset": n_off, "byteLength": n_len, "target": 34962},
            {"buffer": 0, "byteOffset": c_off, "byteLength": c_len, "target": 34962},
            {"buffer": 0, "byteOffset": u_off, "byteLength": u_len, "target": 34962},
            {"buffer": 0, "byteOffset": ix_off, "byteLength": ix_len, "target": 34963},
        ])
        accessors.extend([
            {"bufferView": acc, "componentType": 5126, "count": len(pos), "type": "VEC3",
             "min": pos.min(0).tolist(), "max": pos.max(0).tolist()},
            {"bufferView": acc + 1, "componentType": 5126, "count": len(m.vertex_normals), "type": "VEC3"},
            {"bufferView": acc + 2, "componentType": 5126, "count": len(m.vertices), "type": "VEC3"},
            {"bufferView": acc + 3, "componentType": 5126, "count": len(uv_arr), "type": "VEC2"},
            {"bufferView": acc + 4, "componentType": 5125, "count": len(idx), "type": "SCALAR"},
        ])
        mesh_prims.append({
            "attributes": {"POSITION": acc, "NORMAL": acc + 1, "COLOR_0": acc + 2, "TEXCOORD_0": acc + 3},
            "indices": acc + 4, "mode": 4,
        })
        acc += 5

    names = ["body", "neck_group", "foot_l", "foot_r"]
    gltf = {
        "asset": {"version": "2.0", "generator": "gen_duck_3d v1 (programmatic + HY3 map)"},
        "scene": 0,
        "scenes": [{"name": "Scene", "nodes": [0]}],
        "nodes": [
            {"name": "world", "children": [1, 2, 3, 4]},
            {"name": "body", "mesh": 0},
            {"name": "neck_group", "mesh": 1},
            {"name": "foot_l", "mesh": 2},
            {"name": "foot_r", "mesh": 3},
        ],
        "meshes": [{"name": names[i], "primitives": [mesh_prims[i]]} for i in range(4)],
        "buffers": [{"byteLength": len(bin_data)}],
        "bufferViews": buffer_views,
        "accessors": accessors,
    }
    json_str = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    pad = (-len(json_str)) % 4
    json_str_padded = json_str + b' ' * pad
    glb = b'glTF' + struct.pack('<II', 2, 12 + 8 + len(json_str_padded) + 8 + len(bin_data))
    glb += struct.pack('<II', len(json_str_padded), 0x4E4F534A) + json_str_padded
    glb += struct.pack('<II', len(bin_data), 0x004E4942) + bin_data
    with open(out_path, 'wb') as f:
        f.write(glb)


def gen_duck_3d(out_path):
    """生成 3D 几何鸭子（含 body/neck_group/foot_l/foot_r）"""
    body = build_body()
    ng = build_neck_group()
    foot_l = build_foot()
    foot_r = build_foot()
    foot_l.apply_translation([-0.07, 0.08, 0.05])
    foot_r.apply_translation([0.07, 0.08, 0.05])
    meshes = [body, ng, foot_l, foot_r]
    # 锚点归 y=0
    all_min_y = min(m.bounds[0][1] for m in meshes)
    if all_min_y < -1e-6:
        for m in meshes:
            m.apply_translation([0, -all_min_y, 0])
    # UV
    uvs = [
        capsule_uv_from_verts(meshes[0].vertices, 0.25, 0.16),  # body
        sphere_uv_from_verts(meshes[1].vertices),                  # neck_group (混合)
        sphere_uv_from_verts(meshes[2].vertices),                  # foot_l
        sphere_uv_from_verts(meshes[3].vertices),                  # foot_r
    ]
    export_duck_glb(meshes, uvs, out_path)


if __name__ == "__main__":
    out = "assets/animals/animal_duck_white.glb"
    gen_duck_3d(out)
    print(f"[OK] 3D 鸭子 → {out} ({os.path.getsize(out)/1024:.1f} KB)")