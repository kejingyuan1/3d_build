"""HY3D 模型绑骨+蒙皮 v2（保留 PBR 颜色）
关键修复：
1. 读 hy3_duck_body.glb（保留 baseColorTexture/PBR 颜色）—— 不重建几何
2. 只添加 skin + JOINTS_0 + WEIGHTS_0 + animations
3. IBM 正确：joints 位置 = 关节在 mesh 局部坐标 → IBM = 平移到 -joint_pos（bind pose 站立不倒）
4. 顶点权重：腿区域→对应腿关节，身体→root
5. 输出新 GLB：原 PBR 完整保留 + 真骨骼动画
"""
import sys, struct, json
import numpy as np


def read_glb(path):
    with open(path, 'rb') as f:
        data = f.read()
    off = 12
    clen, _ = struct.unpack('<II', data[off:off+8])
    j = json.loads(data[off+8:off+8+clen])
    off += 8 + clen
    blen, _ = struct.unpack('<II', data[off:off+8])
    bin_data = data[off+8:off+8+blen]
    return j, bin_data


def get_acc_bytes(j, bin_data, ai):
    """读 accessor 的原始 bytes（不是按 count reshape）"""
    a = j['accessors'][ai]
    bv = j['bufferViews'][a['bufferView']]
    dt = {5126: 4, 5125: 4, 5121: 1, 5123: 2, 5122: 2, 5120: 1, 5124: 1}[a['componentType']]
    nbytes = bv['byteLength']
    offset = bv.get('byteOffset', 0)
    return bin_data[offset:offset+nbytes]


def get_acc_array(j, bin_data, ai):
    a = j['accessors'][ai]
    bv = j['bufferViews'][a['bufferView']]
    dt = {5126: np.float32, 5125: np.uint32, 5121: np.uint8, 5123: np.uint16}[a['componentType']]
    nbytes = bv['byteLength']
    offset = bv.get('byteOffset', 0)
    arr = np.frombuffer(bin_data, dtype=dt, count=nbytes // np.dtype(dt).itemsize, offset=offset)
    dims = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
    if dims > 1:
        arr = arr.reshape(a['count'], dims)
    else:
        arr = arr[:a['count']]
    return arr.copy()


def main(in_path, out_path, legs=2):
    j, bin_data = read_glb(in_path)

    # 1. 提取 primitive 现有数据（POSITION/NORMAL/TEXCOORD_0/indices）
    prim = j['meshes'][0]['primitives'][0]
    attrs = prim['attributes']
    pos = get_acc_array(j, bin_data, attrs['POSITION'])
    nrm = get_acc_array(j, bin_data, attrs['NORMAL'])
    uv = get_acc_array(j, bin_data, attrs['TEXCOORD_0'])
    idx = get_acc_array(j, bin_data, prim['indices'])
    nv = len(pos)
    print(f'原 GLB: {nv} 顶点, material={j.get("materials",[{}])[0].get("name","none")}')

    # 1.5. 提取原 GLB 的 image bytes（关键：保留 PBR 颜色必须把 PNG 复制到新 bin）
    # 原 images[0].bufferView 指向原 bufferView 索引；新 GLB 重组后该索引需指向新位置
    orig_images = j.get('images', [])
    orig_textures = j.get('textures', [])
    orig_samplers = j.get('samplers', [])
    orig_materials = j.get('materials', [])
    image_bytes_list = []
    orig_img_bv_indices = []  # 原 bufferView 索引（用于重新指向）
    for img in orig_images:
        bv_idx = img.get('bufferView')
        if bv_idx is None:
            image_bytes_list.append(b'')
            orig_img_bv_indices.append(None)
            continue
        bv = j['bufferViews'][bv_idx]
        offset = bv.get('byteOffset', 0)
        length = bv['byteLength']
        image_bytes_list.append(bin_data[offset:offset+length])
        orig_img_bv_indices.append(bv_idx)

    # 2. 关节位置（mesh 局部坐标）
    y_min, y_max = pos[:, 1].min(), pos[:, 1].max()
    height = y_max - y_min
    leg_top = y_min + height * 0.30  # 腿根高度（30% 处）
    body_mask = pos[:, 1] > leg_top
    leg_mask = ~body_mask
    leg_l = leg_mask & (pos[:, 0] < 0)
    leg_r = leg_mask & (pos[:, 0] >= 0)
    print(f'腿区域: {leg_mask.sum()} (左{leg_l.sum()}/右{leg_r.sum()}), leg_top={leg_top:.2f}')

    # 关节位置
    if legs == 2:
        root_pos = np.array([0.0, leg_top, 0.0], dtype=np.float32)
        leg_l_pos = np.array([
            pos[leg_l, 0].mean() if leg_l.any() else -0.2,
            leg_top * 0.5,
            pos[leg_l, 2].mean() if leg_l.any() else 0.0
        ], dtype=np.float32)
        leg_r_pos = np.array([
            pos[leg_r, 0].mean() if leg_r.any() else 0.2,
            leg_top * 0.5,
            pos[leg_r, 2].mean() if leg_r.any() else 0.0
        ], dtype=np.float32)
        joints = [root_pos, leg_l_pos, leg_r_pos]
    n_joints = len(joints)

    # 3. 权重（硬权：腿→腿，身体→root）
    weights = np.zeros((nv, 4), dtype=np.float32)
    joints_idx = np.zeros((nv, 4), dtype=np.uint8)
    for i in range(nv):
        if leg_l[i]:
            joints_idx[i] = [1, 0, 0, 0]
            weights[i] = [1.0, 0.0, 0.0, 0.0]
        elif leg_r[i]:
            joints_idx[i] = [2, 0, 0, 0]
            weights[i] = [1.0, 0.0, 0.0, 0.0]
        else:
            joints_idx[i] = [0, 0, 0, 0]
            weights[i] = [1.0, 0.0, 0.0, 0.0]

    # 4. IBM（joints 位置→mesh 局部坐标的平移，bind pose 站立）
    ibm = np.zeros((n_joints, 4, 4), dtype=np.float32)
    for i, jp in enumerate(joints):
        ibm[i] = np.eye(4, dtype=np.float32)
        ibm[i][:3, 3] = -jp  # 平移到 -joint_pos

    # 5. 准备 buffer（按顺序追加：joints_idx → weights → ibm）
    pos_b = np.ascontiguousarray(pos, dtype=np.float32).tobytes()
    nrm_b = np.ascontiguousarray(nrm, dtype=np.float32).tobytes()
    uv_b = np.ascontiguousarray(uv, dtype=np.float32).tobytes()
    idx_b = np.ascontiguousarray(idx, dtype=np.uint32).tobytes()
    jt_b = np.ascontiguousarray(joints_idx, dtype=np.uint8).tobytes()
    wt_b = np.ascontiguousarray(weights, dtype=np.float32).tobytes()
    ibm_b = np.ascontiguousarray(ibm, dtype=np.float32).tobytes()

    # 动画 buffer（walk + eat）
    n_w = 5
    t_w = np.array([0, 0.25, 0.5, 0.75, 1.0], dtype=np.float32)
    # leg_l 0 → 0.7rad → 0 → -0.7rad → 0（quaternion xyzw）
    ql = lambda a: (np.sin(a/2), 0, 0, np.cos(a/2))
    leg_l_rot = np.array([ql(0), ql(0.7), ql(0), ql(-0.7), ql(0)], dtype=np.float32)
    leg_r_rot = np.array([ql(0), ql(-0.7), ql(0), ql(0.7), ql(0)], dtype=np.float32)
    root_rot_w = np.tile([0, 0, 0, 1.0], (n_w, 1)).astype(np.float32)
    n_e = 3
    t_e = np.array([0, 0.5, 1.0], dtype=np.float32)
    root_rot_e = np.array([ql(0), ql(0.7), ql(0)], dtype=np.float32)
    walk_t_b = t_w.tobytes()
    leg_l_r_b = leg_l_rot.tobytes()
    leg_r_r_b = leg_r_rot.tobytes()
    root_rw_b = root_rot_w.tobytes()
    eat_t_b = t_e.tobytes()
    root_re_b = root_rot_e.tobytes()

    # 6. 拼装 buffer（按顺序追加：pos/nrm/uv/idx → joints/weights/ibm → 动画 → 原 image bytes）
    chunks = [pos_b, nrm_b, uv_b, idx_b, jt_b, wt_b, ibm_b,
              walk_t_b, leg_l_r_b, walk_t_b, leg_r_r_b, walk_t_b, root_rw_b,
              eat_t_b, root_re_b]
    # 追加原 image PNG bytes（保留 PBR 颜色！）
    for img_b in image_bytes_list:
        chunks.append(img_b)
    bin_parts = []
    offsets = []
    cur = 0
    for b in chunks:
        pad = (-cur) % 4
        if pad:
            bin_parts.append(b'\x00' * pad)
            cur += pad
        offsets.append(cur)
        bin_parts.append(b)
        cur += len(b)
    bin_all = b''.join(bin_parts)

    # 7. 构造 GLB JSON
    # 原 accessors（pos/nrm/uv/idx）+ 新增 joints/weights/ibm + 动画 accessors
    # 原 accessors 索引 0-3（pos/nrm/uv/idx）保留
    new_accs = list(j['accessors'])
    # 新增 4: JOINTS_0(VEC4 uint8), 5: WEIGHTS_0(VEC4 float)
    new_accs.append({"bufferView": 4, "componentType": 5121, "count": nv, "type": "VEC4"})
    new_accs.append({"bufferView": 5, "componentType": 5126, "count": nv, "type": "VEC4"})
    new_accs.append({"bufferView": 6, "componentType": 5126, "count": n_joints, "type": "MAT4"})

    # 动画 accessors：3 个 walk time + 3 个 walk rot + 1 个 eat time + 1 个 eat rot = 8 个
    walk_t_idx = len(new_accs); new_accs.append({"bufferView": 7, "componentType": 5126, "count": n_w, "type": "SCALAR", "min": [0.0], "max": [1.0]})
    leg_l_r_idx = len(new_accs); new_accs.append({"bufferView": 8, "componentType": 5126, "count": n_w, "type": "VEC4"})
    leg_r_r_idx = len(new_accs); new_accs.append({"bufferView": 10, "componentType": 5126, "count": n_w, "type": "VEC4"})
    root_rw_idx = len(new_accs); new_accs.append({"bufferView": 12, "componentType": 5126, "count": n_w, "type": "VEC4"})
    eat_t_idx = len(new_accs); new_accs.append({"bufferView": 14, "componentType": 5126, "count": n_e, "type": "SCALAR", "min": [0.0], "max": [1.0]})
    root_re_idx = len(new_accs); new_accs.append({"bufferView": 15, "componentType": 5126, "count": n_e, "type": "VEC4"})

    # 8. bufferViews：原 0-3（pos/nrm/uv/idx，跳过 image 的 4）+ 新增（joints/weights/ibm + 动画 + 追加的 image）
    # 原 GLB 有 5 个 bufferView（0-3 几何 + 4 = image），我们跳过原 4（image bytes 走 image_bytes_list 追加路径）
    orig_bv = j['bufferViews']
    skip_orig_indices = set()  # 跳过原 image 的 bufferView
    for img in orig_images:
        if img.get('bufferView') is not None:
            skip_orig_indices.add(img['bufferView'])
    new_bvs = []
    for i, bv in enumerate(orig_bv):
        if i in skip_orig_indices:
            continue  # image 走末尾追加
        new_bvs.append(bv)
    # 新增 4=joints/5=weights/6=ibm
    new_bvs.append({"buffer": 0, "byteOffset": offsets[4], "byteLength": len(jt_b)})
    new_bvs.append({"buffer": 0, "byteOffset": offsets[5], "byteLength": len(wt_b)})
    new_bvs.append({"buffer": 0, "byteOffset": offsets[6], "byteLength": len(ibm_b)})
    # 动画 bufferViews
    for i in range(7, 15):
        b_chunk = chunks[i]
        new_bvs.append({"buffer": 0, "byteOffset": offsets[i], "byteLength": len(b_chunk)})
    # 原 image PNG bytes 的 bufferView（追加在末尾）
    image_bv_indices = []
    for i, img_b in enumerate(image_bytes_list):
        bv_idx = len(new_bvs)
        new_bvs.append({"buffer": 0, "byteOffset": offsets[15 + i], "byteLength": len(img_b)})
        image_bv_indices.append(bv_idx)

    # 9. 修改 primitive 引用 JOINTS_0 + WEIGHTS_0
    new_attrs = dict(attrs)
    new_attrs['JOINTS_0'] = 4
    new_attrs['WEIGHTS_0'] = 5

    # 10. 节点：world, root(关节), leg_l, leg_r, skinned_mesh
    # 关键：joint 节点必须有 translation（与 IBM 中的 joint_pos 一致）—— 否则 bind pose 错位
    nodes = [
        {"name": "world", "children": [1]},
        {"name": "root", "translation": joints[0].tolist(), "children": [2, 3, 4]},
        {"name": "leg_l", "translation": joints[1].tolist(), "children": []},
        {"name": "leg_r", "translation": joints[2].tolist(), "children": []},
        {"name": "skinned_mesh", "mesh": 0, "skin": 0},
    ]

    # 11. mesh（用原 mesh 但更新 attributes）
    new_mesh = [{
        "name": "animal",
        "primitives": [{
            "attributes": new_attrs,
            "indices": prim['indices'],
            "mode": 4,
            "material": prim.get('material', 0),
        }],
    }]

    # 12. skins
    skins = [{"joints": [1, 2, 3], "skeleton": 1, "inverseBindMatrices": 6}]

    # 13. 保留原 buffers（buffer 0，byteLength 设为新总长度）
    new_buffer = [{"byteLength": len(bin_all)}]

    # 14. 保留原 images 和 materials
    # 原 images 是 baseColorTexture，material.pbrMetallicRoughness.baseColorTexture → image index
    # 我们保留原 GLB 的 images 和 materials 引用

    # 15. 构造 animations
    walk_anim = {
        "name": "walk",
        "samplers": [
            {"input": walk_t_idx, "output": leg_l_r_idx, "interpolation": "LINEAR"},
            {"input": walk_t_idx, "output": leg_r_r_idx, "interpolation": "LINEAR"},
        ],
        "channels": [
            {"sampler": 0, "target": {"node": 2, "path": "rotation"}},  # leg_l
            {"sampler": 1, "target": {"node": 3, "path": "rotation"}},  # leg_r
        ],
    }
    eat_anim = {
        "name": "eat",
        "samplers": [
            {"input": eat_t_idx, "output": root_re_idx, "interpolation": "LINEAR"},
        ],
        "channels": [
            {"sampler": 0, "target": {"node": 1, "path": "rotation"}},  # root
        ],
    }

    # 16. 完整 GLB（修正 images[].bufferView 指向新 bufferView 索引 + 保留 materials/textures）
    new_images = []
    for i, img in enumerate(orig_images):
        new_img = dict(img)
        if image_bv_indices[i] is not None:
            new_img['bufferView'] = image_bv_indices[i]  # 指向新追加的 PNG bufferView
        new_images.append(new_img)

    gltf = {
        "asset": j['asset'],
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": nodes,
        "meshes": new_mesh,
        "skins": skins,
        "buffers": new_buffer,
        "bufferViews": new_bvs,
        "accessors": new_accs,
        "animations": [walk_anim, eat_anim],
        # 保留原 materials 和 images（bufferView 已修正）
        "materials": orig_materials,
        "images": new_images,
        "textures": orig_textures,
        "samplers": orig_samplers,
    }
    json_str = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    pad = (-len(json_str)) % 4
    json_str_padded = json_str + b' ' * pad
    glb = b'glTF' + struct.pack('<II', 2, 12 + 8 + len(json_str_padded) + 8 + len(bin_all))
    glb += struct.pack('<II', len(json_str_padded), 0x4E4F534A) + json_str_padded
    glb += struct.pack('<II', len(bin_all), 0x004E4942) + bin_all
    with open(out_path, 'wb') as f:
        f.write(glb)
    print(f'[OK] v2 绑骨（保留 PBR 颜色）→ {out_path}')
    print(f'  顶点={nv}, 骨骼={n_joints}, materials={len(j.get("materials",[]))}, images={len(j.get("images",[]))}')


if __name__ == '__main__':
    main('hy3_duck_body.glb', 'hy3_duck_skel.glb', legs=2)
