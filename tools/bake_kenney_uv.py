"""给 Kenney 鸭子模型烘焙球面 UV，输出带 TEXCOORD_0 的 GLB
- Kenney 模型（纯顶点色）→ 加球面 UV → HY3 贴图可映射
- 保持 11 mesh 节点结构（body/neck/head/beak/eyes/wings/tail/feet）
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

def get_buffer(j, bin_data, accessor_idx):
    a = j['accessors'][accessor_idx]
    bv = j['bufferViews'][a['bufferView']]
    cnt = a['count']
    if a['type'] == 'VEC3':
        arr = np.frombuffer(bin_data, dtype=np.float32, count=cnt*3, offset=bv['byteOffset']).reshape(-1,3).copy()
    elif a['type'] == 'SCALAR':
        arr = np.frombuffer(bin_data, dtype=np.uint32, count=cnt, offset=bv['byteOffset']).copy()
    else:
        raise Exception(f'type {a["type"]}')
    return arr

def sphere_uv(verts, center_y=0.4, radius_scale=0.4):
    """球面 UV：u=atan2(z,x)/2π+0.5，v=acos((y-cy)/r)/π"""
    dy = (verts[:, 1] - center_y) / radius_scale
    dy = np.clip(dy, -1, 1)
    u = (np.arctan2(verts[:, 2], verts[:, 0]) / (2 * np.pi) + 0.5) % 1.0
    v = np.arccos(dy) / np.pi
    # 让 HY3 鸭子图正脸（图中心 u=0.5）对准模型 +Z（u=0.25）→ 偏移
    u = (u + 0.25) % 1.0
    return np.column_stack([u, v]).astype(np.float32)

def write_glb_with_uv(in_path, out_path):
    j, bin_data = read_glb(in_path)
    # 收集所有 mesh 的 POSITION accessor（按 primitive）
    mesh_uv_accessors = []
    new_uvs = []  # (bytes, count)
    for mi, m in enumerate(j['meshes']):
        p = m['primitives'][0]
        pos_acc = p['attributes']['POSITION']
        verts = get_buffer(j, bin_data, pos_acc)
        uv = sphere_uv(verts)
        new_uvs.append((uv.tobytes(), len(uv)))
        mesh_uv_accessors.append(len(j['accessors']))
        # 添加 UV accessor（先占位，稍后统一补 bufferView）
        j['accessors'].append({
            'bufferView': None, 'componentType': 5126, 'count': len(uv), 'type': 'VEC2'
        })
        # primitive 加 TEXCOORD_0
        p['attributes']['TEXCOORD_0'] = mesh_uv_accessors[-1]

    # 组装新 buffer：原 buffer + 各 mesh UV
    old_bin = bin_data
    cur = len(old_bin)
    # 原 buffer 对齐（4 字节）
    cur = (cur + 3) // 4 * 4
    for i, (uvb, cnt) in enumerate(new_uvs):
        pad = (-cur) % 4
        if pad:
            cur += pad
        j['accessors'][mesh_uv_accessors[i]]['bufferView'] = len(j['bufferViews'])
        j['bufferViews'].append({
            'buffer': 0, 'byteOffset': cur, 'byteLength': len(uvb), 'target': 34962
        })
        cur += len(uvb)
    new_bin = old_bin + b'\x00' * (cur - len(old_bin))
    for i, (uvb, cnt) in enumerate(new_uvs):
        new_bin += uvb

    j['buffers'][0]['byteLength'] = len(new_bin)
    json_str = json.dumps(j, separators=(',', ':')).encode('utf-8')
    pad = (-len(json_str)) % 4
    json_str_padded = json_str + b' ' * pad
    glb = b'glTF' + struct.pack('<II', 2, 12 + 8 + len(json_str_padded) + 8 + len(new_bin))
    glb += struct.pack('<II', len(json_str_padded), 0x4E4F534A) + json_str_padded
    glb += struct.pack('<II', len(new_bin), 0x004E4942) + new_bin
    with open(out_path, 'wb') as f:
        f.write(glb)
    return len(j['meshes'])

if __name__ == '__main__':
    n = write_glb_with_uv('assets/lifecycle/lifecycle_duck_adult.glb', 'assets/animals/animal_duck_white.glb')
    print(f'[OK] Kenney 鸭子 + UV → animal_duck_white.glb ({n} mesh)')