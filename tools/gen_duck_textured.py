"""HY3 文生图贴图版鸭子生成器 v1 + 透明预填充
- 用 HY3 PNG 烘焙到 vertex color
- 预填充 PNG 透明背景为米白色（避免黑色背面）
- 4 mesh 分离节点：world{body, neck_group, foot_l, foot_r}
"""
import os, sys, struct, json
import numpy as np
import trimesh
from PIL import Image


def _sphere(radius, subdiv=3, scale=None):
    m = trimesh.creation.uv_sphere(radius=radius, count=[8*subdiv, 6*subdiv])
    if scale:
        sx, sy, sz = scale
        m.apply_scale([sx, sy, sz])
    return m

def _box(extents):
    return trimesh.creation.box(extents=extents)


def sample_sphere_uv_to_pixel(img, verts):
    """椭球球面 UV 采样贴图像素"""
    arr = np.array(img.convert('RGBA'))
    H, W = arr.shape[:2]
    r = np.linalg.norm(verts, axis=1) + 1e-9
    u = (np.arctan2(verts[:, 2], verts[:, 0]) / (2 * np.pi) + 0.5) % 1.0
    v = np.arccos(np.clip(verts[:, 1] / r, -1, 1)) / np.pi
    px = np.clip((u * (W - 1)).astype(int), 0, W - 1)
    py = np.clip(((1 - v) * (H - 1)).astype(int), 0, H - 1)
    return arr[py, px].astype(np.uint8)


def sample_box_top_to_pixel(img, verts):
    """脚掌：U=V=世界坐标映射"""
    arr = np.array(img.convert('RGBA'))
    H, W = arr.shape[:2]
    u = (verts[:, 0] + 0.05) / 0.1
    v = (verts[:, 2] + 0.05) / 0.1
    u = np.clip(u, 0, 1); v = np.clip(v, 0, 1)
    px = np.clip((u * (W - 1)).astype(int), 0, W - 1)
    py = np.clip(((1 - v) * (H - 1)).astype(int), 0, H - 1)
    return arr[py, px].astype(np.uint8)


def fill_transparent(img, white=(0xF5, 0xF5, 0xF0)):
    """透明背景填充白色"""
    arr = np.array(img.convert('RGBA'))
    if arr.shape[2] == 4:
        mask = arr[..., 3] < 200
        arr[mask, :3] = list(white)
        arr[mask, 3] = 255
    return arr


def build_body(body_img):
    body = _sphere(radius=0.20, subdiv=3, scale=[1.1, 0.95, 1.3])
    body.apply_translation([0, 0.22, 0])
    arr = fill_transparent(body_img)
    cols = sample_sphere_uv_to_pixel(Image.fromarray(arr), body.vertices)
    body.visual = trimesh.visual.ColorVisuals(body, vertex_colors=cols)
    return body

def build_neck_group(body_img):
    neck = _sphere(radius=0.055, subdiv=2, scale=[0.9, 1.2, 0.9])
    neck.apply_translation([0, 0.0, 0.04])
    white = np.tile([0xF5, 0xF5, 0xF0, 0xFF], (len(neck.vertices), 1)).astype(np.uint8)
    neck.visual = trimesh.visual.ColorVisuals(neck, vertex_colors=white)

    head = _sphere(radius=0.095, subdiv=3, scale=[1.0, 1.0, 1.1])
    head.apply_translation([0, 0.04, 0.06])
    arr = fill_transparent(body_img)
    cols = sample_sphere_uv_to_pixel(Image.fromarray(arr), head.vertices)
    head.visual = trimesh.visual.ColorVisuals(head, vertex_colors=cols)

    neck_group = trimesh.util.concatenate([neck, head])
    neck_group.apply_translation([0, 0.32, 0.10])
    return neck_group

def build_foot(foot_img):
    leg = _box(extents=[0.045, 0.22, 0.045])
    leg.apply_translation([0, -0.11, 0])
    leg_c = np.tile([0xF5, 0xF5, 0xF0, 0xFF], (len(leg.vertices), 1)).astype(np.uint8)
    leg.visual = trimesh.visual.ColorVisuals(leg, vertex_colors=leg_c)

    foot = _box(extents=[0.10, 0.025, 0.14])
    foot.apply_translation([0, -0.225, 0.06])
    arr = fill_transparent(foot_img, white=(0xFF, 0xC8, 0x4A))  # 透明区域填黄
    cols = sample_box_top_to_pixel(Image.fromarray(arr), foot.vertices)
    foot.visual = trimesh.visual.ColorVisuals(foot, vertex_colors=cols)

    return trimesh.util.concatenate([leg, foot])


def export_duck_glb(meshes, out_path):
    """手写 GLB：4 个 mesh 各用独立 bufferView/accessor（避免全部共享同一几何）"""
    mesh_data = []
    for m in meshes:
        pos = np.ascontiguousarray(m.vertices, dtype=np.float32)
        nrm = np.ascontiguousarray(m.vertex_normals, dtype=np.float32)
        col = np.ascontiguousarray(m.visual.vertex_colors[:, :3].astype(np.float32) / 255.0)
        idx = np.ascontiguousarray(m.faces.astype(np.uint32).flatten())
        mesh_data.append((pos, nrm, col, idx))

    # 打包 buffer（每 mesh: pos, nrm, col, idx，4 字节对齐）
    bin_parts = []
    cur = 0
    view_info = []  # (byteOffset, byteLength, target)
    for i in range(4):
        pos, nrm, col, idx = mesh_data[i]
        for b, target in [(pos.tobytes(), 34962), (nrm.tobytes(), 34962), (col.tobytes(), 34962), (idx.tobytes(), 34963)]:
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
        p_off, p_len, _ = view_info[i * 4 + 0]
        n_off, n_len, _ = view_info[i * 4 + 1]
        c_off, c_len, _ = view_info[i * 4 + 2]
        ix_off, ix_len, _ = view_info[i * 4 + 3]
        pos, nrm, col, idx = mesh_data[i]
        buffer_views.extend([
            {"buffer": 0, "byteOffset": p_off, "byteLength": p_len, "target": 34962},
            {"buffer": 0, "byteOffset": n_off, "byteLength": n_len, "target": 34962},
            {"buffer": 0, "byteOffset": c_off, "byteLength": c_len, "target": 34962},
            {"buffer": 0, "byteOffset": ix_off, "byteLength": ix_len, "target": 34963},
        ])
        accessors.extend([
            {"bufferView": acc, "componentType": 5126, "count": len(pos), "type": "VEC3",
             "min": pos.min(0).tolist(), "max": pos.max(0).tolist()},
            {"bufferView": acc + 1, "componentType": 5126, "count": len(nrm), "type": "VEC3"},
            {"bufferView": acc + 2, "componentType": 5126, "count": len(col), "type": "VEC3"},
            {"bufferView": acc + 3, "componentType": 5125, "count": len(idx), "type": "SCALAR"},
        ])
        mesh_prims.append({
            "attributes": {"POSITION": acc, "NORMAL": acc + 1, "COLOR_0": acc + 2},
            "indices": acc + 3, "mode": 4,
        })
        acc += 4

    names = ["body", "neck_group", "foot_l", "foot_r"]
    gltf = {
        "asset": {"version": "2.0", "generator": "gen_duck_textured v1+fill"},
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


def gen_duck_with_tex(body_png, foot_png, out_path):
    body_img = Image.open(body_png)
    foot_img = Image.open(foot_png)
    body = build_body(body_img)
    neck_group = build_neck_group(body_img)
    foot_l = build_foot(foot_img)
    foot_r = build_foot(foot_img)
    foot_l.apply_translation([-0.07, 0.08, 0.05])
    foot_r.apply_translation([0.07, 0.08, 0.05])
    meshes = [body, neck_group, foot_l, foot_r]
    # 整体锚点归一化：所有 mesh 平移使 min_y = 0（脚掌贴地，不再半埋）
    all_min_y = min(m.bounds[0][1] for m in meshes)
    if all_min_y < -1e-6:
        for m in meshes:
            m.apply_translation([0, -all_min_y, 0])
    export_duck_glb(meshes, out_path)


if __name__ == "__main__":
    body_png = "generated-images/卡通鸭子身体侧视图贴图_白色羽毛质感_圆润Q版_头顶有一撮黑_2026-08-06T04-15-07.png"
    foot_png = "generated-images/卡通黄色鸭子脚丫特写贴图_黄色鸭子脚丫_三根脚趾带蹼_扁平卡_2026-08-06T04-15-41.png"
    if not os.path.exists(body_png) or not os.path.exists(foot_png):
        print("贴图缺失"); sys.exit(1)
    out = "assets/animals/animal_duck_white.glb"
    gen_duck_with_tex(body_png, foot_png, out)
    print(f"[OK] HY3 贴图版鸭子 → {out} ({os.path.getsize(out)/1024:.1f} KB)")