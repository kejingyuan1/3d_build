"""混元 3D 鸭子组装：身体 GLB + 脚 GLB ×2（左右脚）→ 分离式 GLB
节点树：world { body, foot_l, foot_r }
走路：foot_l/foot_r 交替摆动；低头：body 前倾
"""
import sys, struct, json
import numpy as np
import trimesh


def load_glb_mesh(path):
    """加载 GLB，返回合并 mesh（保留材质贴图视觉：用顶点色近似）"""
    m = trimesh.load(path, force='mesh')
    # 保留顶点色（混元 PBR 模型的 baseColorTexture 无法直接烘焙，用材质 base color 近似）
    return m


def main(body_path, foot_path, out_path):
    body = load_glb_mesh(body_path)
    foot = load_glb_mesh(foot_path)

    # 尺寸归一化：身体高度 → 1m，脚高度 → 0.35m（鸭子腿长比例）
    body_h = body.bounds[1][1] - body.bounds[0][1]
    body.apply_scale(1.0 / body_h)  # 身体高 = 1m
    foot_h = foot.bounds[1][1] - foot.bounds[0][1]
    foot.apply_scale(0.35 / foot_h)  # 脚高 = 0.35m

    # 脚锚点归零（底部）
    for m in [body, foot]:
        m.apply_translation([0, -m.bounds[0][1], 0])

    # 组装：
    # body 在原点（脚底贴地 0，身体 0~1m）
    # foot_l/foot_r 放在身体下方（身体底部 y=0），左右间距 ±0.2
    foot_l = foot.copy()
    foot_r = foot.copy()
    foot_l.apply_translation([-0.20, 0, 0.05])   # 左
    foot_r.apply_translation([0.20, 0, 0.05])    # 右
    body.apply_translation([0, 0.0, 0.0])        # 身体底部贴地

    # 组装节点结构：world { body, foot_l, foot_r }
    # 用 trimesh 场景再导出为带节点的 GLB 太复杂，直接手写 GLB：
    # 3 个 mesh 独立 accessor
    meshes = [body, foot_l, foot_r]
    names = ["body", "foot_l", "foot_r"]

    bin_parts = []
    cur = 0
    view_info = []
    for m in meshes:
        pos = np.ascontiguousarray(m.vertices, dtype=np.float32)
        nrm = np.ascontiguousarray(m.vertex_normals, dtype=np.float32)
        if hasattr(m.visual, 'vertex_colors') and m.visual.vertex_colors is not None and len(m.visual.vertex_colors) == len(m.vertices):
            col = np.ascontiguousarray(m.visual.vertex_colors[:, :3].astype(np.float32) / 255.0)
        else:
            col = np.ascontiguousarray(np.full((len(m.vertices), 3), 0.9, dtype=np.float32))
        idx = np.ascontiguousarray(m.faces.astype(np.uint32).flatten())
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
    for i, m in enumerate(meshes):
        p_off, p_len, _ = view_info[i * 4 + 0]
        n_off, n_len, _ = view_info[i * 4 + 1]
        c_off, c_len, _ = view_info[i * 4 + 2]
        ix_off, ix_len, _ = view_info[i * 4 + 3]
        pos = np.ascontiguousarray(m.vertices, dtype=np.float32)
        nrm = np.ascontiguousarray(m.vertex_normals, dtype=np.float32)
        idx = np.ascontiguousarray(m.faces.astype(np.uint32).flatten())
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
            {"bufferView": acc + 2, "componentType": 5126, "count": len(m.vertices), "type": "VEC3"},
            {"bufferView": acc + 3, "componentType": 5125, "count": len(idx), "type": "SCALAR"},
        ])
        mesh_prims.append({
            "attributes": {"POSITION": acc, "NORMAL": acc + 1, "COLOR_0": acc + 2},
            "indices": acc + 3, "mode": 4,
        })
        acc += 4

    gltf = {
        "asset": {"version": "2.0", "generator": "hy3_assemble v1"},
        "scene": 0,
        "scenes": [{"name": "Scene", "nodes": [0]}],
        "nodes": [
            {"name": "world", "children": [1, 2, 3]},
            {"name": "body", "mesh": 0},
            {"name": "foot_l", "mesh": 1},
            {"name": "foot_r", "mesh": 2},
        ],
        "meshes": [{"name": names[i], "primitives": [mesh_prims[i]]} for i in range(3)],
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
    print(f'[OK] 组装完成 → {out_path} ({len(bin_data)/1024/1024:.1f} MB)')
    print(f'  body: {body.bounds.tolist()}')
    print(f'  foot_l: {foot_l.bounds.tolist()}')
    print(f'  foot_r: {foot_r.bounds.tolist()}')


if __name__ == '__main__':
    main('hy3_duck_body.glb', 'hy3_duck_foot.glb', 'assets/animals/animal_duck_white.glb')