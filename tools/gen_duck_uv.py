"""HY3 半写实贴图版鸭子生成器 v4
- 4 mesh 独立 accessor（body/neck_group/foot_l/foot_r）
- 每个 mesh 带 TEXCOORD_0（球面 UV / box UV）
- GLB 保持顶点色兜底；HY3 贴图由 demo_duck.html 用 TextureLoader 加载映射
- UV 对齐：HY3 贴图中心（鸭子脸）→ 椭球 +Z 正面
"""
import os, sys, struct, json
import numpy as np
import trimesh


def _uv_sphere(radius, subdiv=3, scale=None):
    """带 UV 的球体。返回 (mesh, uv_array)。"""
    m = trimesh.creation.uv_sphere(radius=radius, count=[8*subdiv, 6*subdiv])
    if scale:
        sx, sy, sz = scale
        m.apply_scale([sx, sy, sz])
    return m

def sphere_uv_from_verts(verts):
    """标准球面 UV：u=(atan2(z,x)/2π+0.5)%1, v=acos(y/r)/π
    u=0 → +X, u=0.25 → +Z, u=0.5 → -X, u=0.75 → -Z
    偏移 +0.5：让贴图水平中心（u=0.5 即鸭子脸）对准 +Z（椭球正面）"""
    r = np.linalg.norm(verts, axis=1) + 1e-9
    u = (np.arctan2(verts[:, 2], verts[:, 0]) / (2 * np.pi) + 0.5) % 1.0
    v = np.arccos(np.clip(verts[:, 1] / r, -1, 1)) / np.pi
    # 旋转贴图：把 HY3 鸭子图中心（脸）对准椭球 +Z 正面
    u = (u + 0.5) % 1.0
    return np.column_stack([u, v]).astype(np.float32)

def box_uv_from_verts(verts, extents):
    """box 的 UV：顶面（y=max）映射整张贴图，侧面拉伸。
    简化：u=(x+ex/2)/ex, v=(z+ez/2)/ez（顶面），其他面也用同一映射。"""
    ex, ey, ez = extents
    u = (verts[:, 0] + ex / 2) / ex
    v = (verts[:, 2] + ez / 2) / ez
    return np.column_stack([u, v]).astype(np.float32)


# ================ 部件构建（带 UV） ================
def build_body():
    """白身椭球（长轴 Z 前后）：body mesh + UV"""
    m = _uv_sphere(radius=0.20, subdiv=4, scale=[1.1, 0.95, 1.3])
    m.apply_translation([0, 0.22, 0])
    uv = sphere_uv_from_verts(m.vertices)
    return m, uv

def build_neck_group():
    """脖子(圆柱)+头(椭球) 合并为 neck_group + UV"""
    neck = _uv_sphere(radius=0.055, subdiv=3, scale=[0.9, 1.2, 0.9])
    neck.apply_translation([0, 0.0, 0.04])
    head = _uv_sphere(radius=0.10, subdiv=4, scale=[1.0, 1.0, 1.1])
    head.apply_translation([0, 0.04, 0.06])
    ng = trimesh.util.concatenate([neck, head])
    ng.apply_translation([0, 0.32, 0.10])
    uv = sphere_uv_from_verts(ng.vertices)
    return ng, uv

def build_foot():
    """腿(白盒)+脚掌(黄盒) 合并 + UV（脚掌顶面映射脚贴图）"""
    leg = trimesh.creation.box(extents=[0.045, 0.22, 0.045])
    leg.apply_translation([0, -0.11, 0])
    foot = trimesh.creation.box(extents=[0.10, 0.025, 0.14])
    foot.apply_translation([0, -0.225, 0.06])
    ft = trimesh.util.concatenate([leg, foot])
    uv = box_uv_from_verts(ft.vertices, [0.10, 0.25, 0.14])  # 覆盖腿+脚掌范围
    return ft, uv


# ================ GLB 导出（含 TEXCOORD_0） ================
def export_duck_glb(meshes, uvs, out_path):
    """4 mesh 独立 accessor + TEXCOORD_0（VEC2）"""
    bin_parts = []
    cur = 0
    view_info = []  # (byteOffset, byteLength, target)
    for i in range(4):
        m, uv = meshes[i], uvs[i]
        pos = np.ascontiguousarray(m.vertices, dtype=np.float32)
        nrm = np.ascontiguousarray(m.vertex_normals, dtype=np.float32)
        col = np.ascontiguousarray(np.full((len(m.vertices), 3), 0.96, dtype=np.float32))  # 白兜底
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
        nrm = np.ascontiguousarray(m.vertex_normals, dtype=np.float32)
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
            {"bufferView": acc + 1, "componentType": 5126, "count": len(nrm), "type": "VEC3"},
            {"bufferView": acc + 2, "componentType": 5126, "count": len(pos), "type": "VEC3"},
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
        "asset": {"version": "2.0", "generator": "gen_duck_textured v4 (UV)"},
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


def gen_duck_uv(out_path):
    """生成带 TEXCOORD_0 的分离式鸭子"""
    body, uv_body = build_body()
    ng, uv_ng = build_neck_group()
    foot_l, uv_foot = build_foot()
    foot_r, uv_foot2 = build_foot()
    foot_l.apply_translation([-0.07, 0.08, 0.05])
    foot_r.apply_translation([0.07, 0.08, 0.05])
    # 锚点归一化
    meshes = [body, ng, foot_l, foot_r]
    all_min_y = min(m.bounds[0][1] for m in meshes)
    if all_min_y < -1e-6:
        for m in meshes:
            m.apply_translation([0, -all_min_y, 0])
    uvs = [uv_body, uv_ng, uv_foot, uv_foot2]
    export_duck_glb(meshes, uvs, out_path)


if __name__ == "__main__":
    out = "assets/animals/animal_duck_white.glb"
    gen_duck_uv(out)
    print(f"[OK] UV 版鸭子 → {out} ({os.path.getsize(out)/1024:.1f} KB)")