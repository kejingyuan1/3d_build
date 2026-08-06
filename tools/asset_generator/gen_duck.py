# -*- coding: utf-8 -*-
"""
分离式 3D 鸭子生成器（身体 / 脚 / 头分离，代码组装用）
农场牧场网页游戏 · 鸭子造型：身体白色（0xF5F5F0）、头顶一撮黑毛、黄脚丫、黄嘴巴
输出：assets/animals/animal_duck_white.glb（+ animal_duck_brown.glb 棕色变体）
可重跑：py -3.9 tools/asset_generator/gen_duck.py

═══════════════════════════════════════════════════════════════════
节点层级（GLB 场景树，组件装代码时参考 —— 命名必须精确）
═══════════════════════════════════════════════════════════════════
world (根)
├── body        几何=鸭身（椭球 + 尾微翘 + 翅膀扁块）   局部原点=身体中心
├── neck_group  空节点（组）                            局部原点=脖子底（身体连接点）
│   ├── neck    几何=白色短柱（脖子）                   局部原点=脖子底（= neck_group 原点）
│   └── head    几何=圆头 + 黑毛 + 黄嘴                 局部原点=脖子顶连接点（= 脖子顶端）
├── foot_l      几何=左黄脚丫（腿 + 3 趾蹼足）          局部原点=左髋（身体底连接点）
└── foot_r      几何=右黄脚丫                           局部原点=右髋

══ 动画接入点（Three.js 代码）══
- 走路摆脚：foot_l.rotation.x = +摆角；foot_r.rotation.x = -摆角
  （每个 foot 的局部原点 = 髋部，绕自身 X 轴前后摆即摆腿）
- 低头吃食：neck_group.rotation.x = 低头角（绕脖子底 X 轴，脖子+头一起低）
- 左右平移身体：直接移 body 节点即可；foot/head 的局部锚点保证不散架
- 世界摆放：根节点 y 位移使脚底（local y=0 处脚掌）落地面
═══════════════════════════════════════════════════════════════════
"""
import os
import sys
import struct
import json as _json
import numpy as np
import trimesh

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import gen_lib as gl


# ---------------- 鸭子色板 ----------------
DUCK_WHITE = (0xF5, 0xF5, 0xF0, 255)   # 身体白 0xF5F5F0
DUCK_BROWN = (0xA9, 0x74, 0x4F, 255)   # 棕鸭变体 0xA9744F
BEAK_YELLOW = (0xFF, 0xC8, 0x4A, 255)  # 嘴/脚丫黄 0xFFC84A
TUFT_BLACK  = (0x1A, 0x1A, 0x1A, 255)  # 头顶黑毛 0x1A1A1A
EYE_BLACK   = (0x2A, 0x2A, 0x2A, 255)  # 眼睛


def _j(c, amt=0.04, rng=None):
    return gl.jitter(c, amt, rng)


def _rot_x(ang_deg):
    return trimesh.transformations.rotation_matrix(np.radians(ang_deg), [1, 0, 0], [0, 0, 0])


def _rot_x_at(ang_deg, point):
    """绕 X 轴、绕指定支点旋转（黑毛锥绕自身基座微后倾，避免杠杆效应）"""
    return trimesh.transformations.rotation_matrix(np.radians(ang_deg), [1, 0, 0], point)


def _rot_y(ang_deg):
    return trimesh.transformations.rotation_matrix(np.radians(ang_deg), [0, 1, 0], [0, 0, 0])


def _rot_y_at(ang_deg, point):
    """绕 Y 轴、绕指定支点旋转（脚趾/蹼绕脚踝支点扇形展开）"""
    return trimesh.transformations.rotation_matrix(np.radians(ang_deg), [0, 1, 0], point)


def _sphere(color, radius, subdiv=1, scale=None):
    """低模球（icosphere）带顶点色"""
    m = trimesh.creation.icosphere(subdivisions=subdiv, radius=radius)
    gl._ensure_normals(m)
    m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=color)
    if scale is not None:
        m.apply_scale(scale)
    return m


def _vcyl(color, radius, height, sections=8):
    """竖直圆柱（Y 轴向上）：trimesh cylinder 默认沿 Z，绕 X -90° 竖立（Z→+Y）"""
    c = gl.mesh(color, radius=radius, height=height, sections=sections, geom="cylinder")
    c.apply_transform(_rot_x(-90))
    return c


def _vcone(color, radius, height, sections=8):
    """竖直锥（Y 轴向上，基座在局部 y=0，尖端向上）：
    注意 trimesh cone 与 cylinder 不同——cone 基座在 z=0、尖端在 z=height（非居中），
    绕 X -90° 竖立（Z→+Y）后基座即落在 y=0，无需再平移"""
    c = gl.mesh(color, radius=radius, height=height, sections=sections, geom="cone")
    c.apply_transform(_rot_x(-90))
    return c


def _merge(meshes):
    """手动合并多个带顶点色的 mesh 为单个 Trimesh（保留各自顶点色）"""
    if len(meshes) == 1:
        return meshes[0]
    verts, faces, cols, off = [], [], [], 0
    for m in meshes:
        v = np.asarray(m.vertices, dtype=float)
        f = np.asarray(m.faces, dtype=np.int64)
        verts.append(v)
        faces.append(f + off)
        off += len(v)
        cols.append(np.asarray(m.visual.vertex_colors, dtype=np.uint8))
    merged = trimesh.Trimesh(vertices=np.vstack(verts), faces=np.vstack(faces), process=False)
    gl._ensure_normals(merged)
    merged.visual = trimesh.visual.ColorVisuals(merged, vertex_colors=np.vstack(cols))
    return merged


# ================ ① 鸭身（局部原点 = 身体中心） ================

def _build_body(body_c, rng):
    """椭球身 + 尾微翘 + 左右翅膀扁块（都挂在 'body' 节点下，合并为一个几何）"""
    parts = []
    main = _sphere(_j(body_c, 0.02, rng), radius=0.16, subdiv=2, scale=[1.30, 0.88, 1.60])
    # x≈0.208 y≈0.141 z≈0.256（宽 0.42m）
    parts.append(("body_main", main))
    # 尾微翘（锥，指向后上方）
    tail = gl.mesh(_j(body_c, 0.02, rng), radius=0.055, height=0.17, sections=8, geom="cone")
    tail.apply_transform(_rot_x(150))            # +Z → 后上方(0, sin150, cos150)
    tail.apply_translation([0, 0.04, -0.25])
    parts.append(("tail", tail))
    # 翅膀扁块（左右）
    for side in (-1, 1):
        wing = gl.mesh(_j(body_c, 0.02, rng), extents=(0.055, 0.075, 0.19), geom="box")
        wing.apply_translation([0.185 * side, -0.02, 0.02])
        parts.append((f"wing{side}", wing))
    return _merge([m for _, m in parts])


# ================ ② 脖子（局部原点 = 脖子底，挂 neck_group 下） ================

def _build_neck(body_c, rng):
    """白色短柱，从脖子底(y=0)向上到 y=NECK_H"""
    return _vcyl(_j(body_c, 0.02, rng), radius=0.045, height=0.09, sections=10)


# ================ ③ 头（局部原点 = 脖子顶连接点） ================

def _build_head(body_c, rng):
    """圆头 + 黑毛(3 根短锥) + 黄嘴(上嘴+下嘴) + 眼睛；局部原点=脖子顶连接点"""
    parts = []
    # 圆头：中心 (0, 0.075, 0.05)，半径 0.075，头顶到 y≈0.15
    head = _sphere(_j(body_c, 0.02, rng), radius=0.075, subdiv=2, scale=[0.98, 1.0, 1.02])
    head.apply_translation([0, 0.075, 0.05])
    parts.append(("head", head))
    # 头顶黑毛（3 根短锥，绕自身基座微后倾）
    tuft_pos = [(0, 0.146, 0.045), (-0.022, 0.150, 0.040), (0.022, 0.150, 0.040)]
    for i, (tx, ty, tz) in enumerate(tuft_pos):
        tuft = _vcone(_j(TUFT_BLACK, 0.02, rng), radius=0.014, height=0.05, sections=6)
        tuft.apply_transform(_rot_x_at(-12, [0, 0, 0]))   # 绕自身基座微后倾
        tuft.apply_translation([tx, ty, tz])
        parts.append((f"tuft{i}", tuft))
    # 黄嘴：上嘴（扁圆） + 下嘴（扁圆，稍小）
    beak_up = _sphere(_j(BEAK_YELLOW, 0.02, rng), radius=0.038, subdiv=1, scale=[1.0, 0.50, 1.50])
    beak_up.apply_translation([0, 0.100, 0.145])
    parts.append(("beak_up", beak_up))
    beak_lo = _sphere(_j(BEAK_YELLOW, 0.02, rng), radius=0.032, subdiv=1, scale=[1.0, 0.45, 1.30])
    beak_lo.apply_translation([0, 0.062, 0.132])
    parts.append(("beak_lo", beak_lo))
    # 眼睛（左右小黑点）
    for side in (-1, 1):
        eye = _sphere(EYE_BLACK, radius=0.011, subdiv=1)
        eye.apply_translation([0.045 * side, 0.105, 0.115])
        parts.append((f"eye{side}", eye))
    return _merge([m for _, m in parts])


# ================ ④ 脚丫（局部原点 = 髋部；腿向下 + 3 趾蹼足向前） ================

def _build_foot(rng):
    """黄脚丫：腿(髋→地) + 脚踝垫 + 3 趾 + 趾间蹼；局部原点=髋部(0,0,0)"""
    parts = []
    c = _j(BEAK_YELLOW, 0.02, rng)
    # 腿：从髋(y=0)向下 0.22m 到地
    leg = _vcyl(c, radius=0.028, height=0.22, sections=8)
    leg.apply_translation([0, -0.11, 0])
    parts.append(("leg", leg))
    # 脚踝/足垫（扁球）
    heel = _sphere(_j(BEAK_YELLOW, 0.03, rng), radius=0.05, subdiv=1, scale=[1.0, 0.5, 1.1])
    heel.apply_translation([0, -0.205, 0.005])
    parts.append(("heel", heel))
    # 3 趾（绕脚踝支点扇形展开 -28°/0/+28°）
    heel_pivot = [0, -0.21, 0.005]
    for ang in (-28, 0, 28):
        toe = gl.mesh(c, extents=(0.035, 0.02, 0.10), geom="box")
        toe.apply_translation([0, -0.21, 0.055])
        if ang != 0:
            toe.apply_transform(_rot_y_at(ang, heel_pivot))
        parts.append((f"toe{ang}", toe))
    # 趾间蹼（两块薄扁盒，沿相邻趾的角平分线 -14°/+14°）
    for ang in (-14, 14):
        web = gl.mesh(_j(BEAK_YELLOW, 0.03, rng), extents=(0.10, 0.014, 0.035), geom="box")
        web.apply_translation([0, -0.208, 0.045])
        web.apply_transform(_rot_y_at(ang, [0, -0.208, 0.005]))
        parts.append((f"web{ang}", web))
    return _merge([m for _, m in parts])


# ================ 组装（GLB 场景树层级，关键结构） ================

# 世界摆放常量（Y-up，+Z 前向）
BODY_Y    = 0.36          # 身体中心高（身底 0.22 ≈ 髋高）
NECK_BASE = (0.0, 0.47, 0.16)   # 脖子底（body 顶前）
NECK_H    = 0.09          # 脖子高
HIP_Y     = 0.24          # 髋高（腿向下 0.22m → 脚底 y≈0.01）
FOOT_X    = 0.11          # 两脚 X 间距


def gen_duck_scene(color="white", seed=7):
    """生成完整鸭子 GLB 场景（含 body/neck_group/neck/head/foot_l/foot_r 层级）"""
    rng = gl.rng_from_seed(seed)
    body_c = DUCK_WHITE if color == "white" else DUCK_BROWN

    body_mesh = _build_body(body_c, rng)
    neck_mesh = _build_neck(body_c, rng)
    head_mesh = _build_head(body_c, rng)
    foot_mesh = _build_foot(rng)

    scene = trimesh.Scene()
    T = trimesh.transformations.translation_matrix

    # 根 → body（身体几何，局部原点=身体中心）
    scene.add_geometry(body_mesh, node_name="body", geom_name="body",
                       transform=T([0.0, BODY_Y, 0.0]))

    # 根 → neck_group（空组节点，局部原点=脖子底）
    scene.graph.update("neck_group", "world", matrix=T(list(NECK_BASE)))

    # neck_group → neck（脖子几何，局部原点=脖子底 = neck_group 原点，中心再抬 NECK_H/2）
    scene.add_geometry(neck_mesh, node_name="neck", geom_name="neck",
                       parent_node_name="neck_group",
                       transform=T([0.0, NECK_H / 2, 0.0]))

    # neck_group → head（头几何，局部原点=脖子顶连接点 → 偏移 NECK_H 到脖子顶）
    scene.add_geometry(head_mesh, node_name="head", geom_name="head",
                       parent_node_name="neck_group",
                       transform=T([0.0, NECK_H, 0.0]))

    # 根 → foot_l / foot_r（黄脚丫，body 的平级节点，局部原点=髋部）
    scene.add_geometry(foot_mesh, node_name="foot_l", geom_name="foot_l",
                       transform=T([-FOOT_X, HIP_Y, 0.01]))
    scene.add_geometry(foot_mesh, node_name="foot_r", geom_name="foot_r",
                       transform=T([FOOT_X, HIP_Y, 0.01]))
    return scene


def export_duck(path, color="white", seed=7):
    scene = gen_duck_scene(color=color, seed=seed)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scene.export(path)
    return path


# ================ 验证 ================

def verify_duck(path):
    """加载 GLB 并验证：节点名齐全 + 层级正确 + 尺寸合理 + JSON 含 NORMAL/COLOR_0"""
    out = {"path": path, "ok": False, "nodes": [], "errors": []}
    try:
        scene = trimesh.load(path)
        nodes = list(scene.graph.nodes)
        out["nodes"] = nodes
        for n in ("body", "head", "foot_l", "foot_r", "neck_group", "neck"):
            if n not in nodes:
                out["errors"].append(f"missing node: {n}")
        # 层级：neck_group 应为 neck/head 的父节点
        edges = scene.graph.to_edgelist()
        parents = {}
        for a, b, _ in edges:
            parents.setdefault(b, []).append(a)
        if "neck_group" not in parents.get("neck", []) or "neck_group" not in parents.get("head", []):
            out["errors"].append("neck/head 的父节点不是 neck_group")
        # 尺寸（世界坐标：scene.bounds 已计入各节点 transform）
        try:
            bounds = scene.bounds  # (2,3) world AABB
            lo, hi = bounds[0], bounds[1]
        except Exception:
            geoms = list(scene.geometry.values())
            lo = np.min([g.bounds[0] for g in geoms], axis=0)
            hi = np.max([g.bounds[1] for g in geoms], axis=0)
        h = hi[1] - lo[1]
        w = hi[0] - lo[0]
        out["bounds"] = {"lo": lo.tolist(), "hi": hi.tolist(), "height": round(float(h), 3), "width": round(float(w), 3)}
        if not (0.55 < h < 0.9):
            out["errors"].append(f"height {h:.2f} 不在 0.55~0.9m")
        # JSON chunk
        with open(path, "rb") as f:
            data = f.read()
        json_len = struct.unpack_from("<I", data, 12)[0]
        glb = _json.loads(data[20:20 + json_len].decode("utf-8"))
        found = {"POSITION": False, "NORMAL": False, "COLOR_0": False}
        for m in glb.get("meshes", []):
            for prim in m.get("primitives", []):
                attrs = prim.get("attributes", {})
                for k in found:
                    if k in attrs:
                        found[k] = True
        out["attrs"] = found
        if not all(found.values()):
            out["errors"].append(f"attrs missing: {found}")
        out["ok"] = not out["errors"]
        return out
    except Exception as e:
        out["errors"].append(str(e))
        return out


def main():
    root = os.path.dirname(os.path.dirname(BASE))
    assets_dir = os.path.join(root, "assets", "animals")
    variants = [("white", "animal_duck_white.glb"), ("brown", "animal_duck_brown.glb")]
    print("== 生成分离式鸭子 ==")
    results = {}
    for color, fname in variants:
        path = os.path.join(assets_dir, fname)
        export_duck(path, color=color)
        size_kb = os.path.getsize(path) / 1024
        v = verify_duck(path)
        results[color] = {"path": path, "sizeKB": round(size_kb, 1), "verify": v}
        print(f"  [{('OK' if v['ok'] else 'FAIL')}] {fname}  {size_kb:6.1f}KB  bounds={v.get('bounds')}  errors={v['errors']}")
        print(f"       nodes={v['nodes']}")
        print(f"       attrs={v.get('attrs')}")
    return results


if __name__ == "__main__":
    main()
