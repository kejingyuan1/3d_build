"""HY3 半写实贴图版鸭子 v5 - 平面 billboard 方案
- 4 mesh 独立但用 PlaneGeometry（不要椭球！）
- HY3 贴图作为完整角色造型（前/背 plane 镜像）
- 走路/低头动画保持（group 旋转）
- 用户看到的是 HY3 半写实皮克斯风完整图，不是抽象椭球
"""
import os, sys, struct, json
import numpy as np
import trimesh


def _plane(size):
    """创建 4 顶点 + 2 三角形的 plane（朝 +Z）。返回 trimesh + UV 数组。"""
    w, h = size
    verts = np.array([
        [-w / 2, 0, -h / 2],   # 0 左下
        [ w / 2, 0, -h / 2],   # 1 右下
        [-w / 2, 0,  h / 2],   # 2 左上
        [ w / 2, 0,  h / 2],   # 3 右上
    ], dtype=np.float32)
    faces = np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32)  # 2 三角面
    uv = np.array([
        [0, 1],   # 0 左下 -> uv (0,1)
        [1, 1],   # 1 右下
        [0, 0],   # 2 左上
        [1, 0],   # 3 右上
    ], dtype=np.float32)
    m = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    return m, uv


def build_body():
    """Body: 大平面贴 HY3 半写实鸭子整图（仅正面 plane）"""
    front, uv = _plane((0.7, 0.55))
    front.apply_translation([0, 0.30, 0])
    return front, uv


def build_neck_group():
    """neck_group: 与 body 相同 plane（z 偏移 0.01 紧贴），用于低头旋转"""
    front, uv = _plane((0.7, 0.55))
    front.apply_translation([0, 0.30, 0.01])
    return front, uv


def build_foot():
    """Foot: 平面贴 HY3 脚贴图"""
    front, uv = _plane((0.18, 0.12))
    front.apply_translation([0, 0.05, 0])
    return front, uv


def export_duck_glb(meshes, uvs, out_path):
    """4 mesh 独立 accessor + POSITION/NORMAL/COLOR_0/TEXCOORD_0"""
    bin_parts = []
    cur = 0
    view_info = []
    for i in range(4):
        m, uv = meshes[i], uvs[i]
        pos = np.ascontiguousarray(m.vertices, dtype=np.float32)
        nrm = np.ascontiguousarray(m.vertex_normals, dtype=np.float32)
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
        p_off, p_len, _ = view_info[i * 5 + 0]
        n_off, n_len, _ = view_info[i * 5 + 1]
        c_off, c_len, _ = view_info[i * 5 + 2]
        u_off, u_len, _ = view_info[i * 5 + 3]
        ix_off, ix_len, _ = view_info[i * 5 + 4]
        pos = np.ascontiguousarray(meshes[i].vertices, dtype=np.float32)
        uv_arr = np.ascontiguousarray(uvs[i], dtype=np.float32)
        idx = np.ascontiguousarray(meshes[i].faces.astype(np.uint32).flatten())
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
            {"bufferView": acc + 1, "componentType": 5126, "count": len(meshes[i].vertex_normals), "type": "VEC3"},
            {"bufferView": acc + 2, "componentType": 5126, "count": len(meshes[i].vertices), "type": "VEC3"},
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
        "asset": {"version": "2.0", "generator": "gen_duck_uv v5 (plane billboard)"},
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


def gen_duck_plane(out_path):
    """生成 v5 plane 版鸭子（HY3 贴图作为完整造型）"""
    body, uv_body = build_body()
    ng, uv_ng = build_neck_group()
    foot_l, uv_fl = build_foot()
    foot_r, uv_fr = build_foot()
    foot_l.apply_translation([-0.18, 0, 0.05])
    foot_r.apply_translation([0.18, 0, 0.05])
    meshes = [body, ng, foot_l, foot_r]
    # 锚点归 y=0
    all_min_y = min(m.bounds[0][1] for m in meshes)
    if all_min_y < -1e-6:
        for m in meshes:
            m.apply_translation([0, -all_min_y, 0])
    uvs = [uv_body, uv_ng, uv_fl, uv_fr]
    export_duck_glb(meshes, uvs, out_path)


if __name__ == "__main__":
    out = "assets/animals/animal_duck_white.glb"
    gen_duck_plane(out)
    print(f"[OK] v5 plane 版 → {out} ({os.path.getsize(out)/1024:.1f} KB)")