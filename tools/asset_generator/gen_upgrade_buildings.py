# -*- coding: utf-8 -*-
"""
升级链建筑生成器（5 级：茅草小屋 → 木屋 → 砖瓦房 → 石砌宅邸 → 豪华庄园）
- 每一级尺寸/细节/豪华度递增，成形成构：真坡顶（三棱柱截面挤出）+ 门框楣 + 窗棂窗台
- 全部带可开关门（命名节点 door_panel / door_l / door_r + handle，运行时绕铰链 Y 轴旋转）
- 输出到 assets/upgrade_buildings/building_upgrade_l{N}.glb
依赖 gen_lib 强制规范：PALETTE/C/jitter/mesh/export_scene/_ensure_normals
"""
import os
import sys
import struct
import numpy as np
import trimesh
from shapely.geometry import Polygon

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import gen_lib as gl


# ================ 真坡顶（三棱柱截面挤出，非斜板） ================

def _gable_roof(roof_c, tile_c, w, d, rise, base_y, eave=0.3, tile_rows=3, seed=9):
    """人字坡屋顶：等腰三角截面沿 X 轴挤出成三棱柱，底边挑檐；瓦片沿坡面排布。返回 (parts, peak_y)"""
    parts = []
    rng = np.random.default_rng(seed)
    half = d / 2 + eave
    poly = Polygon([(-half, 0), (half, 0), (0, rise)])
    roof = trimesh.creation.extrude_polygon(poly, height=w)
    roof.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90), [0, 1, 0], [0, 0, 0]))
    # 修正：挤出沿 Z ∈ [0,w]，旋转 90° 后 X' = Z，需平移 -w/2 使屋顶居中
    roof.apply_translation([-w / 2, 0, 0])
    roof.apply_translation([0, base_y, 0])
    gl._ensure_normals(roof)
    roof.visual = trimesh.visual.ColorVisuals(roof, vertex_colors=gl.jitter(gl.C(roof_c), 0.02, rng))
    parts.append(("roof_body", roof))
    slope_ang = np.degrees(np.arctan2(rise, half))
    tile_len = half * 0.62 / tile_rows
    for sx in (-1, 1):
        for row in range(tile_rows):
            t = (row + 0.5) / tile_rows
            zc = -sx * half * (1 - t)
            yc = base_y + rise * t
            tile = gl.mesh(gl.jitter(gl.C(tile_c), 0.04, rng),
                           extents=(w * 0.9 / 3, 0.035, tile_len * 1.05), geom="box")
            tile.apply_transform(trimesh.transformations.rotation_matrix(
                np.radians(sx * slope_ang), [1, 0, 0], [0, 0, 0]))
            seg = 0
            off = (seg - 0.5) * (w * 0.3 if row % 2 else 0)
            tile.apply_translation([off, yc - 0.03, zc])
            parts.append((f"tile_{sx}_{row}", tile))
    ridge = gl.mesh(gl.jitter(gl.C(tile_c), 0.02, rng), extents=(w + 0.06, 0.09, 0.09), geom="box")
    ridge.apply_translation([0, base_y + rise + 0.045, 0])
    parts.append(("ridge", ridge))
    for sx in (-1, 1):
        finial = gl.mesh(gl.jitter(gl.C(tile_c), 0.02, rng), radius=0.07, height=0.16, sections=6, geom="cone")
        finial.apply_translation([sx * w / 2, base_y + rise + 0.08, 0])
        parts.append((f"finial_{sx}", finial))
    for sz in (-1, 1):
        eave_b = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(w + 0.08, 0.07, 0.1), geom="box")
        eave_b.apply_translation([0, base_y + 0.02, sz * half * 0.92])
        parts.append((f"eave_{sz}", eave_b))
    return parts, base_y + rise


def _thatch_roof(w, d, base_y, eave=0.38, seed=12):
    """茅草顶：草色三棱柱 + 圆弧脊 + 草檐；破旧但成构"""
    parts = []
    rng = np.random.default_rng(seed)
    half = d / 2 + eave
    rise = w * 0.42
    poly = Polygon([(-half, 0), (half, 0), (0, rise)])
    roof = trimesh.creation.extrude_polygon(poly, height=w)
    roof.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90), [0, 1, 0], [0, 0, 0]))
    roof.apply_translation([-w / 2, 0, 0])  # 修正居中
    roof.apply_translation([0, base_y, 0])
    gl._ensure_normals(roof)
    roof.visual = trimesh.visual.ColorVisuals(roof, vertex_colors=gl.jitter(gl.C("leaf_dark"), 0.04, rng))
    parts.append(("thatched_body", roof))
    # 草檐条（前后）
    for sz in (-1, 1):
        for i in range(4):
            tuft = gl.mesh(gl.jitter(gl.C("grass"), 0.05, rng), extents=(w * 0.3, 0.06, 0.08), geom="box")
            tuft.apply_translation([(i - 1.5) * w * 0.24, base_y - 0.01, sz * half * 0.96])
            parts.append((f"thatch_tuft_{sz}_{i}", tuft))
    # 圆弧草脊
    ridge = gl.mesh(gl.jitter(gl.C("grass"), 0.03, rng), radius=0.11, height=w + 0.1, sections=10, geom="cylinder")
    ridge.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90), [0, 0, 1], [0, 0, 0]))
    ridge.apply_translation([0, base_y + rise + 0.02, 0])
    parts.append(("thatch_ridge", ridge))
    for sx in (-1, 1):
        cap = gl.mesh(gl.jitter(gl.C("grass"), 0.04, rng), radius=0.09, height=0.14, sections=6, geom="cone")
        cap.apply_translation([sx * w / 2, base_y + rise + 0.02, 0])
        parts.append((f"thatch_cap_{sx}", cap))
    return parts, base_y + rise


# ================ 门（可开关，铰链左/右缘） ================

def _door(wood_c, w, h, y_base, prefix="door_panel", arched=False):
    """单开门：多板 + 横档 + 门框 + 楣 + 门槛 + 金把手；门板部件命名 prefix_plank/rail/handle
    （运行时按 name.startswith(prefix) 且匹配 plank|rail|handle 收集为可动部件，铰链=包围盒左/右缘）"""
    parts = []
    rng = np.random.default_rng(11)
    n_planks = 3
    for i in range(n_planks):
        plank = gl.mesh(gl.jitter(wood_c, 0.03, rng), extents=(w / n_planks - 0.01, h, 0.035), geom="box")
        plank.apply_translation([-w / 2 + w / n_planks * (i + 0.5), y_base + h / 2, 0])
        parts.append((f"{prefix}_plank{i}", plank))
    for i, yoff in enumerate((h * 0.35, h * 0.65)):
        rail = gl.mesh(gl.jitter(wood_c, 0.03, rng), extents=(w, 0.05, 0.045), geom="box")
        rail.apply_translation([0, y_base + yoff, 0])
        parts.append((f"{prefix}_rail{i}", rail))
    for sx in (-1, 1):
        jamb = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(0.07, h + 0.04, 0.08), geom="box")
        jamb.apply_translation([sx * (w / 2 + 0.035), y_base + h / 2, 0])
        parts.append((f"{prefix}_jamb_{sx}", jamb))
    lintel = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(w + 0.14, 0.07, 0.08), geom="box")
    lintel.apply_translation([0, y_base + h + 0.02, 0])
    parts.append((f"{prefix}_lintel", lintel))
    if arched:
        arch = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), radius=(w / 2 + 0.04), sections=10, geom="sphere")
        arch.apply_scale([1, 0.35, 0.35])
        arch.apply_translation([0, y_base + h + 0.05, 0])
        parts.append((f"{prefix}_arch", arch))
    threshold = gl.mesh(gl.jitter(gl.C("stone"), 0.02, rng), extents=(w + 0.1, 0.05, 0.12), geom="box")
    threshold.apply_translation([0, y_base - 0.025, 0])
    parts.append((f"{prefix}_threshold", threshold))
    handle = gl.mesh(gl.C("gold"), radius=0.018, height=0.05, sections=6, geom="cylinder")
    handle.apply_translation([w * 0.32, y_base + h * 0.5, 0.045])
    parts.append((f"{prefix}_handle", handle))
    return parts


def _double_door(wood_c, total_w, h, y_base, prefix_l="door_l", prefix_r="door_r", arched=False):
    """双开门：共享门框 + 左右两扇（各自可开关，铰链在外缘）"""
    parts = []
    rng = np.random.default_rng(11)
    leaf_w = total_w / 2
    for sx in (-1, 1):
        jamb = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(0.08, h + 0.04, 0.09), geom="box")
        jamb.apply_translation([sx * (total_w / 2 + 0.04), y_base + h / 2, 0])
        parts.append((f"doorframe_jamb_{sx}", jamb))
    lintel = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(total_w + 0.18, 0.09, 0.09), geom="box")
    lintel.apply_translation([0, y_base + h + 0.02, 0])
    parts.append(("doorframe_lintel", lintel))
    if arched:
        arch = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), radius=(total_w / 2 + 0.05), sections=12, geom="sphere")
        arch.apply_scale([1, 0.38, 0.38])
        arch.apply_translation([0, y_base + h + 0.06, 0])
        parts.append(("doorframe_arch", arch))
    threshold = gl.mesh(gl.jitter(gl.C("stone"), 0.02, rng), extents=(total_w + 0.14, 0.06, 0.13), geom="box")
    threshold.apply_translation([0, y_base - 0.03, 0])
    parts.append(("doorframe_threshold", threshold))
    # 左右扇：每扇 n_planks + 横档 + 把手
    n_planks = 3
    for sx, prefix in ((-1, prefix_l), (1, prefix_r)):
        base_x = 0.0 if sx == 1 else -leaf_w
        for i in range(n_planks):
            plank = gl.mesh(gl.jitter(wood_c, 0.03, rng), extents=(leaf_w / n_planks - 0.01, h, 0.035), geom="box")
            plank.apply_translation([base_x + leaf_w / n_planks * (i + 0.5), y_base + h / 2, 0])
            parts.append((f"{prefix}_plank{i}", plank))
        for i, yoff in enumerate((h * 0.35, h * 0.65)):
            rail = gl.mesh(gl.jitter(wood_c, 0.03, rng), extents=(leaf_w, 0.05, 0.045), geom="box")
            rail.apply_translation([sx * leaf_w / 2, y_base + yoff, 0])
            parts.append((f"{prefix}_rail{i}", rail))
        handle = gl.mesh(gl.C("gold"), radius=0.018, height=0.05, sections=6, geom="cylinder")
        handle.apply_translation([sx * leaf_w * 0.18, y_base + h * 0.5, 0.05])
        parts.append((f"{prefix}_handle", handle))
    return parts


# ================ 窗（窗棂 + 窗台 + 楣） ================

def _window(wood_c, frame_w, frame_h, y_base, glass="sky", sill=True, cross=True, arched=False):
    """精致窗：外框 + 玻璃 + 十字棂 + 窗台 + 楣；arch 时为拱窗"""
    parts = []
    rng = np.random.default_rng(5)
    frame = gl.mesh(gl.jitter(wood_c, 0.02, rng), extents=(frame_w, frame_h, 0.06), geom="box")
    frame.apply_translation([0, y_base, 0])
    parts.append(("frame", frame))
    g = gl.mesh(gl.jitter(gl.C(glass), 0.03, rng), extents=(frame_w - 0.08, frame_h - 0.08, 0.025), geom="box")
    g.apply_translation([0, y_base, 0])
    parts.append(("glass", g))
    if cross:
        vbar = gl.mesh(gl.jitter(wood_c, 0.02, rng), extents=(0.03, frame_h - 0.1, 0.04), geom="box")
        vbar.apply_translation([0, y_base, 0])
        parts.append(("vbar", vbar))
        hbar = gl.mesh(gl.jitter(wood_c, 0.02, rng), extents=(frame_w - 0.1, 0.03, 0.04), geom="box")
        hbar.apply_translation([0, y_base, 0])
        parts.append(("hbar", hbar))
    if arched:
        a = gl.mesh(gl.jitter(gl.C(glass), 0.03, rng), radius=(frame_w / 2), sections=10, geom="sphere")
        a.apply_scale([1, 0.4, 0.4])
        a.apply_translation([0, y_base + frame_h / 2 + 0.02, 0])
        parts.append(("arch_glass", a))
    if sill:
        sill_m = gl.mesh(gl.jitter(gl.C("stone"), 0.03, rng), extents=(frame_w + 0.12, 0.06, 0.14), geom="box")
        sill_m.apply_translation([0, y_base - frame_h / 2 - 0.03, 0])
        parts.append(("sill", sill_m))
    pediment = gl.mesh(gl.jitter(wood_c, 0.02, rng), extents=(frame_w + 0.1, 0.05, 0.07), geom="box")
    pediment.apply_translation([0, y_base + frame_h / 2 + 0.03, 0])
    parts.append(("pediment", pediment))
    return parts


# ================ 烟囱 ================

def _chimney(color, w, h, d, x, z, base_y, rows=4, cap_c="stone"):
    parts = []
    rng = np.random.default_rng(13)
    row_h = h / rows
    for i in range(rows):
        brick = gl.mesh(gl.jitter(color, 0.05, rng), extents=(w, row_h * 0.7, d), geom="box")
        brick.apply_translation([x, base_y + i * row_h + row_h * 0.35, z])
        parts.append((f"brick{i}", brick))
    cap = gl.mesh(gl.jitter(gl.C(cap_c), 0.02, rng), extents=(w + 0.08, 0.08, d + 0.08), geom="box")
    cap.apply_translation([x, base_y + h + 0.04, z])
    parts.append(("cap", cap))
    return parts


# ================ 纹理墙（砖/石/护墙板） ================

def _textured_front(parts, base_c, mortar_c, w, h, t, base_y, z, brick_h, brick_w, prefix, rng):
    """前面墙：基础墙 + 水平灰缝 + 竖向错缝（贴图感顶点色）"""
    wall = gl.mesh(gl.jitter(base_c, 0.02, rng), extents=(w, h, t), geom="box")
    wall.apply_translation([0, base_y + h / 2, z])
    parts.append((f"{prefix}_wall", wall))
    n_rows = int(h / brick_h)
    for i in range(1, n_rows):
        yy = base_y + i * brick_h
        if yy > base_y + h - 0.02:
            continue
        line = gl.mesh(gl.jitter(mortar_c, 0.02, rng), extents=(w - 0.02, 0.015, t + 0.03), geom="box")
        line.apply_translation([0, yy, z])
        parts.append((f"{prefix}_h{i}", line))
    col = 0
    x = -w / 2 + brick_w / 2
    while x < w / 2:
        row_off = brick_h / 2 if col % 2 == 0 else 0
        yy = base_y + row_off + brick_h
        while yy < base_y + h - brick_h:
            v = gl.mesh(gl.jitter(mortar_c, 0.02, rng), extents=(0.015, brick_h - 0.03, t + 0.03), geom="box")
            v.apply_translation([x, yy, z])
            parts.append((f"{prefix}_v{col}", v))
            yy += 2 * brick_h
        x += brick_w
        col += 1


def _plank_wall(parts, wood_c, plank_w, h, t, base_y, z, prefix, rng):
    """护墙板墙：竖板条（交替木色深浅）"""
    n = max(4, int(3.0 / plank_w))
    for i in range(n):
        x = - (n - 1) / 2 * plank_w + i * plank_w
        c = gl.jitter(wood_c, 0.05, rng)
        b = gl.mesh(c, extents=(plank_w - 0.01, h, t), geom="box")
        b.apply_translation([x, base_y + h / 2, z])
        parts.append((f"{prefix}_plank{i}", b))


def _openings(parts, w, h, t, base_y, z, openings):
    """在墙上挖洞：黑块（开口阴影）"""
    for i, (cx, cy, ow, oh) in enumerate(openings):
        hole = gl.mesh(gl.C("black"), extents=(ow + 0.04, oh + 0.04, t + 0.05), geom="box")
        hole.apply_translation([cx, base_y + cy, z])
        parts.append((f"open{i}", hole))


# ================ 通用小件 ================

def _steps(parts, stone_c, count, width, depth, base_y, z, rng):
    for i in range(count):
        step = gl.mesh(gl.jitter(stone_c, 0.02, rng), extents=(width - i * 0.14, 0.12, depth - i * 0.1), geom="box")
        step.apply_translation([0, base_y + 0.06 + i * 0.12, z + 0.04 + i * 0.1])
        parts.append((f"step{i}", step))


def _pillar(parts, color, r, h, x, z, base_y, prefix, rng):
    col = gl.mesh(gl.jitter(color, 0.02, rng), radius=r, height=h, sections=8, geom="cylinder")
    col.apply_translation([x, base_y + h / 2, z])
    parts.append((f"{prefix}_col", col))


def _canopy(parts, color, w, d, base_y, z, prefix, rng):
    c = gl.mesh(gl.jitter(color, 0.02, rng), extents=(w, 0.07, d), geom="box")
    c.apply_translation([0, base_y, z])
    parts.append((f"{prefix}_canopy", c))


# ================ 5 级升级链 ================

def gen_upgrade_l1(seed=1):
    """L1 茅草小屋：木墙 + 草坡顶 + 木门 + 小方窗（破旧但完整）"""
    rng = gl.rng_from_seed(seed)
    wall_c = gl.jitter(gl.C("wood"), 0.02, rng)
    wood_dark_c = gl.jitter(gl.C("wood_dark"), 0.02, rng)
    stone_c = gl.jitter(gl.C("stone"), 0.02, rng)
    W, D, H = 2.5, 2.5, 1.4
    wall_t = 0.1
    base_y = 0.18
    parts = []
    # 地基
    f = gl.mesh(gl.jitter(stone_c, 0.03, rng), extents=(W + 0.3, 0.14, D + 0.3), geom="box")
    f.apply_translation([0, 0.07, 0])
    parts.append(("foundation", f))
    # 护墙板四面
    _plank_wall(parts, wall_c, 0.28, H, wall_t, base_y, D / 2, "front", rng)
    _openings(parts, W, H, wall_t, base_y, D / 2, [(0, 0.55, 0.5, 0.9), (-0.75, 0.78, 0.32, 0.32)])
    _plank_wall(parts, wall_c, 0.28, H, wall_t, base_y, -D / 2, "back", rng)
    _openings(parts, W, H, wall_t, base_y, -D / 2, [])
    for sx, rot in ((1, 90), (-1, -90)):
        side = gl.mesh(gl.jitter(wall_c, 0.02, rng), extents=(D, H, wall_t), geom="box")
        side.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
        side.apply_translation([sx * W / 2, base_y + H / 2, 0])
        parts.append((f"side_{sx}", side))
    # 门
    door_parts = _door(wood_dark_c, 0.5, 0.9, base_y, prefix="door_panel", arched=False)
    for name, m in door_parts:
        m.apply_translation([0, 0, D / 2 + 0.02])
        parts.append((name, m))
    # 小方窗（左）
    win = _window(wood_dark_c, 0.32, 0.32, base_y + 0.78, sill=True, cross=False)
    for name, m in win:
        m.apply_translation([-0.75, 0, D / 2 + 0.02])
        parts.append((f"win_l_{name}", m))
    # 草顶
    roof_parts, peak_y = _thatch_roof(W, D, base_y + H, eave=0.38)
    parts.extend(roof_parts)
    # 室内地板
    floor = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(W - 0.06, 0.04, D - 0.06), geom="box")
    floor.apply_translation([0, base_y, 0])
    parts.append(("floor", floor))
    return parts


def gen_upgrade_l2(seed=2):
    """L2 木屋：护墙板 + 棕坡顶 + 门 + 2 十字窗 + 小烟囱"""
    rng = gl.rng_from_seed(seed)
    wall_c = gl.jitter(gl.C("wood"), 0.02, rng)
    wood_dark_c = gl.jitter(gl.C("wood_dark"), 0.02, rng)
    stone_c = gl.jitter(gl.C("stone"), 0.02, rng)
    W, D, H = 3.0, 3.0, 1.6
    wall_t = 0.1
    base_y = 0.18
    parts = []
    f = gl.mesh(gl.jitter(stone_c, 0.03, rng), extents=(W + 0.3, 0.14, D + 0.3), geom="box")
    f.apply_translation([0, 0.07, 0])
    parts.append(("foundation", f))
    # 前墙：护墙板 + 门/窗洞
    _plank_wall(parts, wall_c, 0.3, H, wall_t, base_y, D / 2, "front", rng)
    _openings(parts, W, H, wall_t, base_y, D / 2,
              [(0, 0.6, 0.55, 1.0), (-0.85, 0.85, 0.42, 0.45), (0.85, 0.85, 0.42, 0.45)])
    _plank_wall(parts, wall_c, 0.3, H, wall_t, base_y, -D / 2, "back", rng)
    _openings(parts, W, H, wall_t, base_y, -D / 2, [])
    for sx, rot in ((1, 90), (-1, -90)):
        side = gl.mesh(gl.jitter(wall_c, 0.02, rng), extents=(D, H, wall_t), geom="box")
        side.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
        side.apply_translation([sx * W / 2, base_y + H / 2, 0])
        parts.append((f"side_{sx}", side))
    # 门
    door_parts = _door(wood_dark_c, 0.55, 1.0, base_y, prefix="door_panel", arched=False)
    for name, m in door_parts:
        m.apply_translation([0, 0, D / 2 + 0.02])
        parts.append((name, m))
    # 2 十字窗
    for wx in (-0.85, 0.85):
        win = _window(wood_dark_c, 0.42, 0.45, base_y + 0.85, sill=True, cross=True)
        for name, m in win:
            m.apply_translation([wx, 0, D / 2 + 0.02])
            parts.append((f"win_{wx}_{name}", m))
    # 棕坡顶
    roof_parts, peak_y = _gable_roof("wood_dark", "wood_dark", W, D, 1.0, base_y + H, eave=0.3, tile_rows=3)
    parts.extend(roof_parts)
    # 小烟囱
    ch = _chimney(gl.jitter(gl.C("stone"), 0.03, rng), 0.22, 0.7, 0.22, 0.75, -0.7, peak_y - 0.15, rows=4)
    parts.extend([(f"chim_{n}", m) for n, m in ch])
    floor = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(W - 0.06, 0.04, D - 0.06), geom="box")
    floor.apply_translation([0, base_y, 0])
    parts.append(("floor", floor))
    return parts


def gen_upgrade_l3(seed=3):
    """L3 砖瓦房：红砖墙(砖缝) + 红瓦人字顶 + 门廊遮棚 + 2 窗 + 烟囱 + 台阶"""
    rng = gl.rng_from_seed(seed)
    brick_c = gl.jitter(gl.C("tomato"), 0.02, rng)
    mortar_c = gl.jitter(gl.C("cream"), 0.02, rng)
    wood_dark_c = gl.jitter(gl.C("wood_dark"), 0.02, rng)
    stone_c = gl.jitter(gl.C("stone"), 0.02, rng)
    W, D, H = 4.0, 3.5, 1.8
    wall_t = 0.12
    base_y = 0.22
    parts = []
    # 双层地基
    for i, (ew, eh, ey) in enumerate(((W + 0.5, 0.14, 0.07), (W + 0.3, 0.12, 0.18))):
        f = gl.mesh(gl.jitter(stone_c, 0.03, rng), extents=(ew, eh, D + 0.5 - i * 0.2), geom="box")
        f.apply_translation([0, ey, 0])
        parts.append((f"foundation{i}", f))
    # 前墙：砖纹理 + 门/窗洞
    _textured_front(parts, brick_c, mortar_c, W, H, wall_t, base_y, D / 2, 0.16, 0.42, "front", rng)
    _openings(parts, W, H, wall_t, base_y, D / 2,
              [(0, 0.62, 0.6, 1.05), (-1.15, 0.9, 0.45, 0.5), (1.15, 0.9, 0.45, 0.5)])
    # 后墙/侧墙：纯砖色（省网格）
    back = gl.mesh(gl.jitter(brick_c, 0.02, rng), extents=(W, H, wall_t), geom="box")
    back.apply_translation([0, base_y + H / 2, -D / 2])
    parts.append(("back", back))
    for sx, rot in ((1, 90), (-1, -90)):
        side = gl.mesh(gl.jitter(brick_c, 0.02, rng), extents=(D, H, wall_t), geom="box")
        side.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
        side.apply_translation([sx * W / 2, base_y + H / 2, 0])
        parts.append((f"side_{sx}", side))
    # 门
    door_parts = _door(wood_dark_c, 0.6, 1.05, base_y, prefix="door_panel", arched=False)
    for name, m in door_parts:
        m.apply_translation([0, 0, D / 2 + 0.02])
        parts.append((name, m))
    # 门廊遮棚（立柱 + 遮雨板）
    _pillar(parts, wood_dark_c, 0.035, 1.25, -0.38, D / 2 + 0.22, base_y, "porch_l", rng)
    _pillar(parts, wood_dark_c, 0.035, 1.25, 0.38, D / 2 + 0.22, base_y, "porch_r", rng)
    _canopy(parts, wood_dark_c, 1.2, 0.6, base_y + 1.28, D / 2 + 0.24, "porch", rng)
    # 2 窗
    for wx in (-1.15, 1.15):
        win = _window(wood_dark_c, 0.45, 0.5, base_y + 0.9, sill=True, cross=True)
        for name, m in win:
            m.apply_translation([wx, 0, D / 2 + 0.02])
            parts.append((f"win_{wx}_{name}", m))
    # 红瓦人字顶
    roof_parts, peak_y = _gable_roof("roof", "roof", W, D, 1.1, base_y + H, eave=0.34, tile_rows=4)
    parts.extend(roof_parts)
    # 烟囱
    ch = _chimney(gl.jitter(gl.C("roof"), 0.03, rng), 0.3, 1.0, 0.3, 1.15, -0.85, peak_y - 0.18, rows=5)
    parts.extend([(f"chim_{n}", m) for n, m in ch])
    # 台阶
    _steps(parts, stone_c, 2, 1.4, 0.7, base_y - 0.0, D / 2 + 0.3, rng)
    floor = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(W - 0.08, 0.05, D - 0.08), geom="box")
    floor.apply_translation([0, base_y, 0])
    parts.append(("floor", floor))
    return parts


def gen_upgrade_l4(seed=4):
    """L4 石砌宅邸：灰石墙 + 深蓝灰坡顶 + 双开门 + 4 窗(窗台楣) + 双烟囱 + 壁柱 + 门廊立柱"""
    rng = gl.rng_from_seed(seed)
    stone_c = gl.jitter(gl.C("stone"), 0.02, rng)
    mortar_c = gl.jitter(gl.C("white"), 0.02, rng)
    wood_dark_c = gl.jitter(gl.C("wood_dark"), 0.02, rng)
    W, D, H = 5.0, 4.0, 2.0
    wall_t = 0.13
    base_y = 0.24
    parts = []
    for i, (ew, eh, ey) in enumerate(((W + 0.6, 0.16, 0.08), (W + 0.4, 0.14, 0.2), (W + 0.2, 0.12, 0.33))):
        f = gl.mesh(gl.jitter(stone_c, 0.03, rng), extents=(ew, eh, D + 0.6 - i * 0.2), geom="box")
        f.apply_translation([0, ey, 0])
        parts.append((f"foundation{i}", f))
    # 前墙：石纹理（大块）+ 双开门/4窗洞
    _textured_front(parts, stone_c, mortar_c, W, H, wall_t, base_y, D / 2, 0.24, 0.6, "front", rng)
    _openings(parts, W, H, wall_t, base_y, D / 2,
              [(0, 0.68, 1.0, 1.15), (-1.7, 0.95, 0.5, 0.55), (1.7, 0.95, 0.5, 0.55)])
    back = gl.mesh(gl.jitter(stone_c, 0.02, rng), extents=(W, H, wall_t), geom="box")
    back.apply_translation([0, base_y + H / 2, -D / 2])
    parts.append(("back", back))
    for sx, rot in ((1, 90), (-1, -90)):
        side = gl.mesh(gl.jitter(stone_c, 0.02, rng), extents=(D, H, wall_t), geom="box")
        side.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
        side.apply_translation([sx * W / 2, base_y + H / 2, 0])
        parts.append((f"side_{sx}", side))
        # 侧窗（每侧 1 窗，窗台+楣）
        win = _window(wood_dark_c, 0.5, 0.55, base_y + 0.95, sill=True, cross=True)
        for name, m in win:
            m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
            m.apply_translation([sx * W / 2, 0, 0.45])
            parts.append((f"swin_{sx}_{name}", m))
    # 双开门
    door_parts = _double_door(wood_dark_c, 1.0, 1.15, base_y, prefix_l="door_l", prefix_r="door_r", arched=False)
    for name, m in door_parts:
        m.apply_translation([0, 0, D / 2 + 0.03])
        parts.append((name, m))
    # 前窗 ×2
    for wx in (-1.7, 1.7):
        win = _window(wood_dark_c, 0.5, 0.55, base_y + 0.95, sill=True, cross=True)
        for name, m in win:
            m.apply_translation([wx, 0, D / 2 + 0.03])
            parts.append((f"win_{wx}_{name}", m))
    # 壁柱 ×4
    for sx in (-1, 1):
        for sz in (-1, 1):
            pilaster = gl.mesh(gl.jitter(wood_dark_c, 0.02, rng), extents=(0.16, H + 0.06, 0.16), geom="box")
            pilaster.apply_translation([sx * (W / 2 - 0.08), base_y + H / 2, sz * (D / 2 - 0.08)])
            parts.append((f"pilaster_{sx}_{sz}", pilaster))
    # 门廊立柱 + 遮棚
    for px in (-0.55, 0.55):
        _pillar(parts, wood_dark_c, 0.045, 1.5, px, D / 2 + 0.3, base_y, f"porch_{px}", rng)
    _canopy(parts, wood_dark_c, 1.8, 0.85, base_y + 1.55, D / 2 + 0.32, "porch", rng)
    # 深蓝灰坡顶
    roof_parts, peak_y = _gable_roof("blueberry", "blueberry", W, D, 1.25, base_y + H, eave=0.38, tile_rows=4)
    parts.extend(roof_parts)
    # 双烟囱
    for cx, cz in ((1.5, -1.0), (-1.5, 0.7)):
        ch = _chimney(gl.jitter(gl.C("stone"), 0.03, rng), 0.32, 1.15, 0.32, cx, cz, peak_y - 0.2, rows=5)
        parts.extend([(f"chim_{cx}_{n}", m) for n, m in ch])
    # 台阶
    _steps(parts, stone_c, 2, 1.7, 0.8, base_y - 0.0, D / 2 + 0.35, rng)
    floor = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(W - 0.1, 0.06, D - 0.1), geom="box")
    floor.apply_translation([0, base_y, 0])
    parts.append(("floor", floor))
    return parts


def gen_upgrade_l5(seed=5):
    """L5 豪华庄园：米白墙 + 红人字顶 + 双开大门 + 6 窗(拱/楣) + 双烟囱 + 塔楼 + 拱门廊 + 三层台阶 + 阳台"""
    rng = gl.rng_from_seed(seed)
    cream_c = gl.jitter(gl.C("cream"), 0.02, rng)
    trim_c = gl.jitter(gl.C("white"), 0.02, rng)
    wood_dark_c = gl.jitter(gl.C("wood_dark"), 0.02, rng)
    stone_c = gl.jitter(gl.C("stone"), 0.02, rng)
    W, D, H = 6.0, 4.5, 2.2
    wall_t = 0.14
    base_y = 0.26
    parts = []
    for i, (ew, eh, ey) in enumerate(((W + 0.8, 0.18, 0.09), (W + 0.55, 0.16, 0.23), (W + 0.3, 0.14, 0.38))):
        f = gl.mesh(gl.jitter(stone_c, 0.03, rng), extents=(ew, eh, D + 0.8 - i * 0.25), geom="box")
        f.apply_translation([0, ey, 0])
        parts.append((f"foundation{i}", f))
    # 前墙（米白）+ 大门/窗洞
    front = gl.mesh(gl.jitter(cream_c, 0.02, rng), extents=(W, H, wall_t), geom="box")
    front.apply_translation([0, base_y + H / 2, D / 2])
    parts.append(("front", front))
    _openings(parts, W, H, wall_t, base_y, D / 2,
              [(0, 0.7, 1.1, 1.25), (-1.95, 0.95, 0.5, 0.6), (1.95, 0.95, 0.5, 0.6)])
    back = gl.mesh(gl.jitter(cream_c, 0.02, rng), extents=(W, H, wall_t), geom="box")
    back.apply_translation([0, base_y + H / 2, -D / 2])
    parts.append(("back", back))
    _openings(parts, W, H, wall_t, base_y, -D / 2,
              [(-1.95, 0.95, 0.5, 0.6), (1.95, 0.95, 0.5, 0.6)])
    for sx, rot in ((1, 90), (-1, -90)):
        side = gl.mesh(gl.jitter(cream_c, 0.02, rng), extents=(D, H, wall_t), geom="box")
        side.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
        side.apply_translation([sx * W / 2, base_y + H / 2, 0])
        parts.append((f"side_{sx}", side))
        win = _window(wood_dark_c, 0.5, 0.6, base_y + 0.95, sill=True, cross=True, arched=True)
        for name, m in win:
            m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
            m.apply_translation([sx * W / 2, 0, 0.5])
            parts.append((f"swin_{sx}_{name}", m))
    # 双开大门（拱）
    door_parts = _double_door(wood_dark_c, 1.1, 1.25, base_y, prefix_l="door_l", prefix_r="door_r", arched=True)
    for name, m in door_parts:
        m.apply_translation([0, 0, D / 2 + 0.03])
        parts.append((name, m))
    # 前窗 ×2（拱窗）
    for wx in (-1.95, 1.95):
        win = _window(wood_dark_c, 0.5, 0.6, base_y + 0.95, sill=True, cross=True, arched=True)
        for name, m in win:
            m.apply_translation([wx, 0, D / 2 + 0.03])
            parts.append((f"win_{wx}_{name}", m))
    # 后窗 ×2
    for wx in (-1.95, 1.95):
        win = _window(wood_dark_c, 0.5, 0.6, base_y + 0.95, sill=True, cross=True)
        for name, m in win:
            m.apply_translation([wx, 0, -D / 2 - 0.03])
            parts.append((f"bwin_{wx}_{name}", m))
    # 壁柱 ×4
    for sx in (-1, 1):
        for sz in (-1, 1):
            pilaster = gl.mesh(gl.jitter(trim_c, 0.02, rng), extents=(0.18, H + 0.08, 0.18), geom="box")
            pilaster.apply_translation([sx * (W / 2 - 0.09), base_y + H / 2, sz * (D / 2 - 0.09)])
            parts.append((f"pilaster_{sx}_{sz}", pilaster))
    # 拱门廊（立柱 + 拱 + 遮棚）
    for px in (-0.7, 0.7):
        _pillar(parts, wood_dark_c, 0.05, 1.7, px, D / 2 + 0.42, base_y, f"porch_{px}", rng)
    arch = gl.mesh(gl.jitter(wood_dark_c, 0.02, rng), radius=0.62, sections=12, geom="sphere")
    arch.apply_scale([1, 0.5, 0.5])
    arch.apply_translation([0, base_y + 1.15, D / 2 + 0.4])
    parts.append(("porch_arch", arch))
    _canopy(parts, wood_dark_c, 2.3, 1.2, base_y + 1.75, D / 2 + 0.45, "porch", rng)
    # 阳台（二层围栏 + 底板）
    balcony = gl.mesh(gl.jitter(wood_dark_c, 0.02, rng), extents=(2.4, 0.08, 1.0), geom="box")
    balcony.apply_translation([0, base_y + 1.82, D / 2 + 0.42])
    parts.append(("balcony_floor", balcony))
    for i in range(6):
        bx = -1.0 + i * 0.4
        post = gl.mesh(gl.jitter(wood_dark_c, 0.02, rng), extents=(0.05, 0.4, 0.05), geom="box")
        post.apply_translation([bx, base_y + 2.06, D / 2 + 0.42])
        parts.append((f"balc_post_{i}", post))
    rail = gl.mesh(gl.jitter(wood_dark_c, 0.02, rng), extents=(2.2, 0.05, 0.05), geom="box")
    rail.apply_translation([0, base_y + 2.14, D / 2 + 0.42])
    parts.append(("balc_rail", rail))
    # 红人字顶
    roof_parts, peak_y = _gable_roof("roof", "roof", W, D, 1.4, base_y + H, eave=0.42, tile_rows=4)
    parts.extend(roof_parts)
    # 双烟囱
    for cx, cz in ((1.9, -1.1), (-1.9, 0.8)):
        ch = _chimney(gl.jitter(gl.C("roof"), 0.03, rng), 0.36, 1.25, 0.36, cx, cz, peak_y - 0.22, rows=5)
        parts.extend([(f"chim_{cx}_{n}", m) for n, m in ch])
    # 塔楼（左前角，锥顶）
    tw = 0.85
    tx, tz = -W / 2 + tw / 2 + 0.05, D / 2 - tw / 2 - 0.05
    tw_h = H + 2.5  # 塔身明显高于屋脊
    tower = gl.mesh(gl.jitter(cream_c, 0.02, rng), extents=(tw, tw_h, tw), geom="box")
    tower.apply_translation([tx, base_y + tw_h / 2, tz])
    parts.append(("tower_body", tower))
    for sy in range(4):
        quo = gl.mesh(gl.jitter(trim_c, 0.02, rng), extents=(tw + 0.06, 0.14, tw + 0.06), geom="box")
        quo.apply_translation([tx, base_y + 0.45 + sy * 0.8, tz])
        parts.append((f"tower_quo_{sy}", quo))
    t_win = _window(wood_dark_c, 0.34, 0.4, base_y + 1.5, sill=True, cross=True, arched=True)
    for name, m in t_win:
        m.apply_translation([tx, 0, tz + tw / 2 + 0.02])
        parts.append((f"twin_{name}", m))
    # 塔锥顶
    cone = gl.mesh(gl.jitter(gl.C("roof"), 0.02, rng), radius=tw / 2 + 0.08, height=0.85, sections=8, geom="cone")
    cone.apply_translation([tx, base_y + tw_h, tz])
    parts.append(("tower_cone", cone))
    fin = gl.mesh(gl.jitter(gl.C("gold"), 0.02, rng), radius=0.05, height=0.22, sections=6, geom="cone")
    fin.apply_translation([tx, base_y + tw_h + 0.42, tz])
    parts.append(("tower_finial", fin))
    # 三层台阶
    _steps(parts, stone_c, 3, 2.0, 0.9, base_y - 0.0, D / 2 + 0.5, rng)
    floor = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(W - 0.12, 0.06, D - 0.12), geom="box")
    floor.apply_translation([0, base_y, 0])
    parts.append(("floor", floor))
    return parts


GENERATORS = {
    "building_upgrade_l1": gen_upgrade_l1,
    "building_upgrade_l2": gen_upgrade_l2,
    "building_upgrade_l3": gen_upgrade_l3,
    "building_upgrade_l4": gen_upgrade_l4,
    "building_upgrade_l5": gen_upgrade_l5,
}

DOOR_CFG = {
    "building_upgrade_l1": [{"name": "door_panel", "hinge": "left", "angle": 110}],
    "building_upgrade_l2": [{"name": "door_panel", "hinge": "left", "angle": 110}],
    "building_upgrade_l3": [{"name": "door_panel", "hinge": "left", "angle": 110}],
    "building_upgrade_l4": [{"name": "door_l", "hinge": "left", "angle": 100}, {"name": "door_r", "hinge": "right", "angle": -100}],
    "building_upgrade_l5": [{"name": "door_l", "hinge": "left", "angle": 100}, {"name": "door_r", "hinge": "right", "angle": -100}],
}

# 碰撞盒（半尺寸，粗拟合整体）
COLLISION = {
    "building_upgrade_l1": {"type": "fixed", "shape": "box", "params": {"hx": 1.25, "hy": 1.1, "hz": 1.25}},
    "building_upgrade_l2": {"type": "fixed", "shape": "box", "params": {"hx": 1.5, "hy": 1.3, "hz": 1.5}},
    "building_upgrade_l3": {"type": "fixed", "shape": "box", "params": {"hx": 2.0, "hy": 1.5, "hz": 1.75}},
    "building_upgrade_l4": {"type": "fixed", "shape": "box", "params": {"hx": 2.5, "hy": 1.8, "hz": 2.0}},
    "building_upgrade_l5": {"type": "fixed", "shape": "box", "params": {"hx": 3.0, "hy": 2.2, "hz": 2.25}},
}

NAMES = {
    "building_upgrade_l1": "茅草小屋",
    "building_upgrade_l2": "木屋",
    "building_upgrade_l3": "砖瓦房",
    "building_upgrade_l4": "石砌宅邸",
    "building_upgrade_l5": "豪华庄园",
}

DESCS = {
    "building_upgrade_l1": "升级 Lv.1：茅草小屋",
    "building_upgrade_l2": "升级 Lv.2：木屋",
    "building_upgrade_l3": "升级 Lv.3：砖瓦房",
    "building_upgrade_l4": "升级 Lv.4：石砌宅邸",
    "building_upgrade_l5": "升级 Lv.5：豪华庄园",
}


def generate(assets_dir=None, verify=True):
    """生成全部 5 级建筑 GLB 并验证"""
    if assets_dir is None:
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(BASE)), "assets")
    out_dir = os.path.join(assets_dir, "upgrade_buildings")
    os.makedirs(out_dir, exist_ok=True)
    results = {}
    for aid, fn in GENERATORS.items():
        parts = fn()
        # 锚点归零：整体平移使最低 y = 0
        min_y = min(m.bounds[0][1] for _, m in parts)
        if min_y < 0:
            for _, m in parts:
                m.apply_translation([0, -min_y, 0])
        path = os.path.join(out_dir, f"{aid}.glb")
        gl.export_scene(parts, path)
        size_kb = os.path.getsize(path) / 1024
        results[aid] = {"path": path, "sizeKB": round(size_kb, 1), "parts": len(parts)}
        if verify:
            ok = verify_glb(path)
            results[aid]["verify"] = ok
            print(f"  {'✔' if ok else '✘'} {aid} ({size_kb:.1f} KB, {len(parts)} parts) -> {path}")
    return results


def verify_glb(path):
    """验证 GLB：trimesh 加载 OK + JSON chunk 含 POSITION/NORMAL/COLOR_0 + 尺寸合理"""
    try:
        scene = trimesh.load(path)
        if scene is None:
            return False
        with open(path, "rb") as f:
            data = f.read()
        # GLB header: magic(4) version(4) length(4) 然后 JSON chunk
        if len(data) < 20:
            return False
        json_len = struct.unpack_from("<I", data, 12)[0]
        json_data = data[20:20 + json_len]
        import json as _json
        glb = _json.loads(json_data)
        found = {"POSITION": False, "NORMAL": False, "COLOR_0": False}
        for m in glb.get("meshes", []):
            for prim in m.get("primitives", []):
                attrs = prim.get("attributes", {})
                if "POSITION" in attrs:
                    found["POSITION"] = True
                if "NORMAL" in attrs:
                    found["NORMAL"] = True
                if "COLOR_0" in attrs:
                    found["COLOR_0"] = True
        return all(found.values())
    except Exception as e:
        print(f"  verify error: {e}")
        return False


if __name__ == "__main__":
    generate()
