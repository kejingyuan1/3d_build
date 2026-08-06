"""HY3D 模型程序化绑骨 + 蒙皮（鸭子 2 足版）
- 读 HY3D 单 mesh GLB（POSITION/NORMAL/TEXCOORD_0）
- 按 Y 高度分区：低 Y = 腿区域（分左右），高 Y = 身体
- 创建骨骼：root(身体) → leg_l / leg_r（腿）
- 顶点权重：腿顶点绑对应腿，身体顶点绑 root，过渡带混合
- 输出 GLB：JOINTS_0 + WEIGHTS_0 + skin + animation（walk 腿摆动 / eat 低头）
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

def get_acc(j, bin_data, ai):
    a = j['accessors'][ai]
    bv = j['bufferViews'][a['bufferView']]
    dt = {5126: np.float32, 5125: np.uint32, 5121: np.uint8}[a['componentType']]
    nbytes = bv['byteLength']
    offset = bv.get('byteOffset', 0)
    arr = np.frombuffer(bin_data, dtype=dt, count=nbytes // np.dtype(dt).itemsize, offset=offset)
    dims = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
    n = a['count']
    if dims > 1:
        arr = arr.reshape(n, dims)
    else:
        arr = arr[:n]
    return arr.copy()

def main(in_path, out_path, legs=2):
    j, bin_data = read_glb(in_path)
    # 取 mesh primitive
    prim = j['meshes'][0]['primitives'][0]
    attrs = prim['attributes']
    pos = get_acc(j, bin_data, attrs['POSITION'])
    nrm = get_acc(j, bin_data, attrs['NORMAL'])
    uv = get_acc(j, bin_data, attrs['TEXCOORD_0'])
    idx = get_acc(j, bin_data, prim['indices'])

    nv = len(pos)
    y_min, y_max = pos[:, 1].min(), pos[:, 1].max()
    height = y_max - y_min
    # 腿区域：底部 25% 高度（鸭子站姿，腿短）
    leg_top = y_min + height * 0.25
    # 分区
    body_mask = pos[:, 1] > leg_top
    leg_mask = ~body_mask
    leg_l = leg_mask & (pos[:, 0] < 0)   # 左腿（x<0）
    leg_r = leg_mask & (pos[:, 0] >= 0)  # 右腿

    # 骨骼位置（关节在网格局部坐标）
    root_pos = np.array([0, leg_top, 0], dtype=np.float32)   # 身体/髋部
    leg_l_pos = np.array([pos[leg_l, 0].mean() if leg_l.any() else -0.2, leg_top * 0.5, pos[leg_l, 2].mean() if leg_l.any() else 0], dtype=np.float32)
    leg_r_pos = np.array([pos[leg_r, 0].mean() if leg_r.any() else 0.2, leg_top * 0.5, pos[leg_r, 2].mean() if leg_r.any() else 0], dtype=np.float32)

    joints = [root_pos, leg_l_pos, leg_r_pos]  # index 0,1,2
    n_joints = len(joints)

    # 顶点权重：身体→root，腿→对应腿（过渡带 60%:40%）
    weights = np.zeros((nv, 4), dtype=np.float32)
    joints_idx = np.zeros((nv, 4), dtype=np.uint8)
    weights[:, 0] = 1.0
    for i in range(nv):
        if leg_l[i]:
            joints_idx[i] = [1, 0, 0, 0]
            weights[i] = [1.0, 0.0, 0.0, 0.0]
        elif leg_r[i]:
            joints_idx[i] = [2, 0, 0, 0]
            weights[i] = [1.0, 0.0, 0.0, 0.0]
        # body 保持 root

    # inverse bind matrices（关节位置的逆平移）
    ibm = np.zeros((n_joints, 4, 4), dtype=np.float32)
    for i, jp in enumerate(joints):
        ibm[i] = np.eye(4, dtype=np.float32)
        ibm[i][:3, 3] = -jp

    # 组装 GLB：原数据 + JOINTS_0 + WEIGHTS_0 + skin + animation
    # buffer: pos + nrm + uv + idx + joints + weights + ibm
    pos_b = np.ascontiguousarray(pos, dtype=np.float32).tobytes()
    nrm_b = np.ascontiguousarray(nrm, dtype=np.float32).tobytes()
    uv_b = np.ascontiguousarray(uv, dtype=np.float32).tobytes()
    idx_b = np.ascontiguousarray(idx, dtype=np.uint32).tobytes()
    jt_b = np.ascontiguousarray(joints_idx, dtype=np.uint8).tobytes()
    wt_b = np.ascontiguousarray(weights, dtype=np.float32).tobytes()
    ibm_b = np.ascontiguousarray(ibm, dtype=np.float32).tobytes()

    chunks = [pos_b, nrm_b, uv_b, idx_b, jt_b, wt_b, ibm_b]
    bin_parts, offsets, cur = [], [], 0
    for b in chunks:
        pad = (-cur) % 4
        if pad: bin_parts.append(b'\x00'*pad); cur += pad
        offsets.append(cur)
        bin_parts.append(b)
        cur += len(b)
    bin_data_new = b''.join(bin_parts)

    p_off, n_off, u_off, ix_off, jt_off, wt_off, ibm_off = offsets
    # bufferViews: 0 pos,1 nrm,2 uv,3 idx,4 joints,5 weights,6 ibm
    bvs = [
        {"buffer":0,"byteOffset":p_off,"byteLength":len(pos_b),"target":34962},
        {"buffer":0,"byteOffset":n_off,"byteLength":len(nrm_b),"target":34962},
        {"buffer":0,"byteOffset":u_off,"byteLength":len(uv_b),"target":34962},
        {"buffer":0,"byteOffset":ix_off,"byteLength":len(idx_b),"target":34963},
        {"buffer":0,"byteOffset":jt_off,"byteLength":len(jt_b),"target":34962},
        {"buffer":0,"byteOffset":wt_off,"byteLength":len(wt_b),"target":34962},
        {"buffer":0,"byteOffset":ibm_off,"byteLength":len(ibm_b),"target":0},
    ]
    # accessors: 0 pos,1 nrm,2 uv,3 idx,4 joints,5 weights,6 ibm
    accs = [
        {"bufferView":0,"componentType":5126,"count":nv,"type":"VEC3","min":pos.min(0).tolist(),"max":pos.max(0).tolist()},
        {"bufferView":1,"componentType":5126,"count":nv,"type":"VEC3"},
        {"bufferView":2,"componentType":5126,"count":nv,"type":"VEC2"},
        {"bufferView":3,"componentType":5125,"count":len(idx),"type":"SCALAR"},
        {"bufferView":4,"componentType":5121,"count":nv,"type":"VEC4"},
        {"bufferView":5,"componentType":5126,"count":nv,"type":"VEC4"},
        {"bufferView":6,"componentType":5126,"count":n_joints,"type":"MAT4"},
    ]
    # 节点：0 world, 1 root(关节), 2 leg_l, 3 leg_r, 4 skinned_mesh（mesh + skin 引用，挂在 root 下）
    nodes = [
        {"name":"world","children":[1]},
        {"name":"root","children":[2,3,4]},
        {"name":"leg_l","children":[]},
        {"name":"leg_r","children":[]},
        {"name":"skinned_mesh","mesh":0,"skin":0},  # 关键：同时引用 mesh 和 skin → SkinnedMesh
    ]
    # mesh 引用 skin
    mesh = [{"name":"animal","primitives":[{
        "attributes":{"POSITION":0,"NORMAL":1,"TEXCOORD_0":2,"JOINTS_0":4,"WEIGHTS_0":5},
        "indices":3,"mode":4,
    }]}]
    skins = [{"joints":[1,2,3],"inverseBindMatrices":6,"skeleton":1}]
    # scene: world
    scenes = [{"nodes":[0]}]
    # animation: walk (leg_l/leg_r rotation.x 交替) + eat (root rotation.x)
    # keyframes 0/0.5/1s
    t0, t1, t2 = 0.0, 0.5, 1.0
    def rot_x_channel(node_idx, kf_rots):
        """kf_rots: list of [t, rx]"""
        times = np.array([k[0] for k in kf_rots], dtype=np.float32)
        rots = []
        for t, rx in kf_rots:
            c, s = np.cos(rx/2), np.sin(rx/2)
            rots.append([s, 0, 0, c])  # xyz, w
        rots = np.array(rots, dtype=np.float32)
        return times, rots

    # walk: leg_l swing 0→+0.7→0→-0.7→0, leg_r 反向
    t_w = np.array([0, 0.25, 0.5, 0.75, 1.0], dtype=np.float32)
    leg_l_rot = np.array([[0,0,0,1],[0.34,0,0,0.94],[0,0,0,1],[-0.34,0,0,0.94],[0,0,0,1]], dtype=np.float32)
    leg_r_rot = np.array([[0,0,0,1],[-0.34,0,0,0.94],[0,0,0,1],[0.34,0,0,0.94],[0,0,0,1]], dtype=np.float32)
    root_rot_w = np.tile([[0,0,0,1]], (5,1)).astype(np.float32)

    # eat: root 0→0.7 (低头), 0.5s 后回
    t_e = np.array([0, 0.5, 1.0], dtype=np.float32)
    root_rot_e = np.array([[0,0,0,1],[0.34,0,0,0.94],[0,0,0,1]], dtype=np.float32)

    def pack_kf(times, rots):
        t_b = np.ascontiguousarray(times, dtype=np.float32).tobytes()
        r_b = np.ascontiguousarray(rots, dtype=np.float32).tobytes()
        return t_b, r_b, len(times)

    # 动画 buffer 追加到 bin
    anim_chunks = []  # (bytes, target)
    anim_offsets = []
    cur2 = cur
    for t_b, r_b, _ in [pack_kf(t_w, leg_l_rot), pack_kf(t_w, leg_r_rot), pack_kf(t_w, root_rot_w),
                        pack_kf(t_e, root_rot_e)]:
        pad = (-cur2) % 4
        if pad: anim_chunks.append(b'\x00'*pad); cur2 += pad
        anim_offsets.append(cur2)
        anim_chunks.append(t_b); cur2 += len(t_b)
        anim_offsets.append(cur2)
        anim_chunks.append(r_b); cur2 += len(r_b)
    bin_all = bin_data_new + b''.join(anim_chunks)
    base = len(bin_data_new)

    # 动画 accessor：walk: times(3 accessors) + rot(3)
    acc_anim_start = len(accs)
    walk_t0, walk_t1, walk_t2 = anim_offsets[0], anim_offsets[2], anim_offsets[4]
    walk_r0, walk_r1, walk_r2 = anim_offsets[1], anim_offsets[3], anim_offsets[5]
    eat_t0, eat_r0 = anim_offsets[6], anim_offsets[7]
    n_walk = 5
    anim_accs = [
        {"bufferView": len(bvs)+0, "componentType": 5126, "count": n_walk, "type": "SCALAR",
         "min":[0.0], "max":[1.0]},
        {"bufferView": len(bvs)+1, "componentType": 5126, "count": n_walk, "type": "VEC4"},
        {"bufferView": len(bvs)+2, "componentType": 5126, "count": n_walk, "type": "SCALAR",
         "min":[0.0], "max":[1.0]},
        {"bufferView": len(bvs)+3, "componentType": 5126, "count": n_walk, "type": "VEC4"},
        {"bufferView": len(bvs)+4, "componentType": 5126, "count": n_walk, "type": "SCALAR",
         "min":[0.0], "max":[1.0]},
        {"bufferView": len(bvs)+5, "componentType": 5126, "count": n_walk, "type": "VEC4"},
        {"bufferView": len(bvs)+6, "componentType": 5126, "count": 3, "type": "SCALAR",
         "min":[0.0], "max":[1.0]},
        {"bufferView": len(bvs)+7, "componentType": 5126, "count": 3, "type": "VEC4"},
    ]
    anim_bvs = [
        {"buffer":0,"byteOffset":walk_t0,"byteLength":n_walk*4},
        {"buffer":0,"byteOffset":walk_r0,"byteLength":n_walk*16},
        {"buffer":0,"byteOffset":walk_t1,"byteLength":n_walk*4},
        {"buffer":0,"byteOffset":walk_r1,"byteLength":n_walk*16},
        {"buffer":0,"byteOffset":walk_t2,"byteLength":n_walk*4},
        {"buffer":0,"byteOffset":walk_r2,"byteLength":n_walk*16},
        {"buffer":0,"byteOffset":eat_t0,"byteLength":12},
        {"buffer":0,"byteOffset":eat_r0,"byteLength":48},
    ]
    # channel: leg_l(node2) rotation walk, leg_r(node3) rotation walk, root(node1) rotation eat
    acc_base = acc_anim_start
    anim_walk = {
        "name": "walk",
        "channels": [
            {"sampler":0,"target":{"node":2,"path":"rotation"}},
            {"sampler":1,"target":{"node":3,"path":"rotation"}},
        ],
        "samplers": [
            {"input":acc_base+0,"output":acc_base+1,"interpolation":"LINEAR"},
            {"input":acc_base+2,"output":acc_base+3,"interpolation":"LINEAR"},
        ],
    }
    anim_eat = {
        "name": "eat",
        "channels": [
            {"sampler":0,"target":{"node":1,"path":"rotation"}},
        ],
        "samplers": [
            {"input":acc_base+6,"output":acc_base+7,"interpolation":"LINEAR"},
        ],
    }

    gltf = {
        "asset": {"version":"2.0","generator":"gen_skel_animals v1"},
        "scene": 0,
        "scenes": scenes,
        "nodes": nodes,
        "meshes": mesh,
        "skins": skins,
        "buffers": [{"byteLength": len(bin_all)}],
        "bufferViews": bvs + anim_bvs,
        "accessors": accs + anim_accs,
        "animations": [anim_walk, anim_eat],
    }
    json_str = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    pad = (-len(json_str)) % 4
    json_str_padded = json_str + b' ' * pad
    glb = b'glTF' + struct.pack('<II', 2, 12+8+len(json_str_padded)+8+len(bin_all))
    glb += struct.pack('<II', len(json_str_padded), 0x4E4F534A) + json_str_padded
    glb += struct.pack('<II', len(bin_all), 0x004E4942) + bin_all
    with open(out_path, 'wb') as f:
        f.write(glb)
    print(f'[OK] 绑骨完成 → {out_path}')
    print(f'  顶点={nv} 骨骼={n_joints} 腿区域={leg_mask.sum()} (左{leg_l.sum()}/右{leg_r.sum()})')
    print(f'  animations: walk(腿摆动) + eat(低头)')

if __name__ == '__main__':
    main('hy3_duck_body.glb', 'hy3_duck_skel.glb', legs=2)
