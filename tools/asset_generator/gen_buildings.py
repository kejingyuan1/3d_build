# -*- coding: utf-8 -*-
"""
精细建筑生成器 v4（彻底重做）：
- 屋顶 = 三角截面挤出的真"人字坡"三棱柱（本体就是屋顶形状，绝非 box 拼）
- 瓦片沿坡面方向排布（3-4 排瓦楞，贴坡面）
- 墙体干净成块 + 护墙板 + 壁柱；门/窗精致；烟囱砖纹；地基台阶
"""
import numpy as np
import trimesh
from shapely.geometry import Polygon
import gen_lib as gl


# ================ 核心：真坡顶 ================

def _gable_roof(roof_c, w, d, rise, base_y, eave=0.3, tile_rows=3):
    """
    人字坡屋顶：等腰三角截面沿 X 轴挤出成三棱柱（含两侧山墙 + 两个坡面），
    底边带挑檐(eave)。瓦片沿坡面方向排布。
    返回 (parts, peak_y)
    """
    parts = []
    rng = np.random.default_rng(9)
    half = d / 2 + eave          # 挑檐后的半深
    # --- 截面挤出屋顶本体 ---
    poly = Polygon([(-half, 0), (half, 0), (0, rise)])
    roof = trimesh.creation.extrude_polygon(poly, height=w)
    # 挤出沿 Z（宽度），旋转使宽度沿 X
    roof.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90), [0, 1, 0], [0, 0, 0]))
    # 挤出底边 y=0 正好对齐 base_y
    roof.apply_translation([0, base_y, 0])
    roof.visual = trimesh.visual.ColorVisuals(roof, vertex_colors=gl.jitter(gl.C(roof_c), 0.02, rng))
    parts.append(("roof_body", roof))

    # --- 瓦片：沿坡面方向，每个坡面排 tile_rows 排 ---
    slope_ang = np.degrees(np.arctan2(rise, half))
    tile_len = half * 0.62 / tile_rows  # 每排瓦片沿坡向的长度
    for sx in (-1, 1):  # 两个坡面
        for row in range(tile_rows):
            # 沿坡面从檐口(低)到屋脊(高) 插值
            t = (row + 0.5) / tile_rows
            # 坡面上一点：深度坐标 z，高度 y
            zc = -sx * half * (1 - t)      # 从挑檐端往屋脊走
            yc = base_y + rise * t
            # 瓦片是沿坡向的长条（box 旋转到坡面角）
            tile = gl.mesh(gl.jitter(gl.C("roof"), 0.04, rng),
                           extents=(w * 0.9 / 3, 0.035, tile_len * 1.05), geom="box")
            # 先旋转贴坡面（绕 X 轴旋转坡角，方向随坡面左右翻转）
            tile.apply_transform(trimesh.transformations.rotation_matrix(
                np.radians(sx * slope_ang), [1, 0, 0], [0, 0, 0]))
            # 沿坡向的横向错位（3 段瓦楞 + 隔排错开）
            seg = 0
            off = (seg - 0.5) * (w * 0.3 if row % 2 else 0)
            tile.apply_translation([off, yc - 0.03, zc])
            # 修正：旋转是在原点转的，translation 需考虑旋转后的位置
            parts.append((f"tile_{sx}_{row}", tile))

    # --- 屋脊（横贯屋顶最高处） ---
    ridge = gl.mesh(gl.jitter(gl.C("roof"), 0.02, rng), extents=(w + 0.06, 0.09, 0.09), geom="box")
    ridge.apply_translation([0, base_y + rise + 0.045, 0])
    parts.append(("ridge", ridge))
    # --- 屋脊两端鸱吻 ---
    for sx in (-1, 1):
        finial = gl.mesh(gl.jitter(gl.C("roof"), 0.02, rng), radius=0.07, height=0.16, sections=6, geom="cone")
        finial.apply_translation([sx * w / 2, base_y + rise + 0.08, 0])
        parts.append((f"finial_{sx}", finial))
    # --- 屋檐挑出横梁（前后各一） ---
    for sz in (-1, 1):
        eave_b = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(w + 0.08, 0.07, 0.1), geom="box")
        eave_b.apply_translation([0, base_y + 0.02, sz * half * 0.92])
        parts.append((f"eave_{sz}", eave_b))
    return parts, base_y + rise


# ================ 部件工具 ================

def _window(wood_c, frame_w, frame_h, y_base, glass="sky", sill=True, cross=True):
    """精致窗：外框 + 玻璃 + 十字棂 + 窗台 + 楣"""
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
    if sill:
        sill_m = gl.mesh(gl.jitter(gl.C("stone"), 0.03, rng), extents=(frame_w + 0.12, 0.06, 0.14), geom="box")
        sill_m.apply_translation([0, y_base - frame_h / 2 - 0.03, 0])
        parts.append(("sill", sill_m))
    pediment = gl.mesh(gl.jitter(wood_c, 0.02, rng), extents=(frame_w + 0.1, 0.05, 0.07), geom="box")
    pediment.apply_translation([0, y_base + frame_h / 2 + 0.03, 0])
    parts.append(("pediment", pediment))
    return parts


def _door(wood_c, w, h, y_base, arched=True, prefix="door"):
    """精致门：多板 + 横档 + 门框 + 拱头 + 门槛 + 金把手（铰链在门洞左缘）"""
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


def _chimney(color, w, h, d, x, z, base_y, rows=4):
    """砖纹烟囱"""
    parts = []
    rng = np.random.default_rng(13)
    row_h = h / rows
    for i in range(rows):
        brick = gl.mesh(gl.jitter(color, 0.05, rng), extents=(w, row_h * 0.7, d), geom="box")
        brick.apply_translation([x, base_y + i * row_h + row_h * 0.35, z])
        parts.append((f"brick{i}", brick))
    cap = gl.mesh(gl.jitter(gl.C("stone"), 0.02, rng), extents=(w + 0.08, 0.08, d + 0.08), geom="box")
    cap.apply_translation([x, base_y + h + 0.04, z])
    parts.append(("cap", cap))
    return parts


# ================ 建筑 ================

def gen_farmhouse(seed=1):
    """农舍 v4：真坡顶 + 护墙板 + 壁柱 + 拱门 + 十字窗 + 双烟囱 + 门廊"""
    rng = gl.rng_from_seed(seed)
    wall_c = gl.jitter(gl.C("cream"), 0.02, rng)
    wood_c = gl.jitter(gl.C("wood"), 0.02, rng)
    wood_dark_c = gl.jitter(gl.C("wood_dark"), 0.02, rng)
    stone_c = gl.jitter(gl.C("stone"), 0.02, rng)

    W, D, H = 2.6, 2.2, 1.7
    wall_t = 0.12
    base_y = 0.28   # 墙体底部（地基之上）
    parts = []

    # 地基（双层）
    for i, (ew, eh, ey) in enumerate(((W + 0.5, 0.14, 0.07), (W + 0.3, 0.12, 0.2))):
        f = gl.mesh(gl.jitter(stone_c, 0.03, rng), extents=(ew, eh, D + 0.5 - i * 0.2), geom="box")
        f.apply_translation([0, ey, 0])
        parts.append((f"foundation{i}", f))

    # 墙体四块（干净成块 + 开口黑块）
    front = gl.mesh(gl.jitter(wall_c, 0.02, rng), extents=(W, H, wall_t), geom="box")
    front.apply_translation([0, base_y + H / 2, D / 2])
    parts.append(("front", front))
    for i, (cx, cy, w, h) in enumerate(((0, 0.5, 0.56, 1.0), (-0.85, 0.95, 0.42, 0.5), (0.85, 0.95, 0.42, 0.5))):
        hole = gl.mesh(gl.C("black"), extents=(w + 0.03, h + 0.03, wall_t + 0.05), geom="box")
        hole.apply_translation([cx, base_y + cy, D / 2])
        parts.append((f"front_open{i}", hole))
    back = gl.mesh(gl.jitter(wall_c, 0.02, rng), extents=(W, H, wall_t), geom="box")
    back.apply_translation([0, base_y + H / 2, -D / 2])
    parts.append(("back", back))
    for i, cx in enumerate((-0.7, 0.7)):
        hole = gl.mesh(gl.C("black"), extents=(0.4, 0.45, wall_t + 0.05), geom="box")
        hole.apply_translation([cx, base_y + 0.95, -D / 2])
        parts.append((f"back_open{i}", hole))
    for sx, rot in ((1, 90), (-1, -90)):
        side = gl.mesh(gl.jitter(wall_c, 0.02, rng), extents=(D, H, wall_t), geom="box")
        side.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
        side.apply_translation([sx * W / 2, base_y + H / 2, 0])
        parts.append((f"side_{sx}", side))

    # 护墙板（墙底）
    trim = gl.mesh(gl.jitter(gl.C("wood_dark"), 0.02, rng), extents=(W + 0.02, 0.18, D + 0.02), geom="box")
    trim.apply_translation([0, base_y + 0.09, 0])
    parts.append(("wall_trim", trim))
    # 壁柱 ×4
    for sx in (-1, 1):
        for sz in (-1, 1):
            pilaster = gl.mesh(gl.jitter(wood_dark_c, 0.02, rng), extents=(0.14, H + 0.05, 0.14), geom="box")
            pilaster.apply_translation([sx * (W / 2 - 0.07), base_y + H / 2, sz * (D / 2 - 0.07)])
            parts.append((f"pilaster_{sx}_{sz}", pilaster))

    # 门（拱头，铰链左缘在门洞左）
    door_parts = _door(wood_dark_c, 0.56, 1.0, base_y, arched=True)
    for name, m in door_parts:
        m.apply_translation([0, 0, D / 2 + 0.02])
        parts.append((name, m))

    # 前窗（十字棂 + 花箱）
    for wx, wy in ((-0.85, 0.95), (0.85, 0.95)):
        win = _window(wood_c, 0.42, 0.5, base_y + wy, sill=True, cross=True)
        for name, m in win:
            m.apply_translation([wx, 0, D / 2 + 0.02])
            parts.append((f"win_{wx}_{name}", m))
    # 侧窗
    for sx in (-1, 1):
        win = _window(wood_c, 0.4, 0.45, base_y + 0.95, sill=True, cross=True)
        for name, m in win:
            m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90 * sx), [0, 1, 0], [0, 0, 0]))
            m.apply_translation([sx * W / 2, 0, 0.3])
            parts.append((f"swin_{sx}_{name}", m))

    # 屋顶（真坡顶）
    roof_parts, peak_y = _gable_roof("roof", W, D, 1.05, base_y + H, eave=0.32, tile_rows=3)
    parts.extend(roof_parts)

    # 双烟囱（砖纹）
    for cx, cz in ((0.8, -0.75), (-0.7, 0.5)):
        ch = _chimney(gl.jitter(gl.C("stone"), 0.03, rng), 0.26, 0.9, 0.26, cx, cz, peak_y - 0.15, rows=5)
        parts.extend([(f"chim_{cx}_{n}", m) for n, m in ch])

    # 门廊：立柱 + 遮雨棚 + 台阶
    for sx in (-0.32, 0.32):
        post = gl.mesh(gl.jitter(wood_dark_c, 0.02, rng), radius=0.035, height=1.35, sections=8, geom="cylinder")
        post.apply_translation([sx, base_y + 0.66, D / 2 + 0.14])
        parts.append((f"porch_post_{sx}", post))
    canopy = gl.mesh(gl.jitter(wood_dark_c, 0.02, rng), extents=(0.95, 0.06, 0.5), geom="box")
    canopy.apply_translation([0, base_y + 1.36, D / 2 + 0.16])
    parts.append(("porch_canopy", canopy))
    for i in range(2):
        step = gl.mesh(gl.jitter(stone_c, 0.02, rng), extents=(0.9 - i * 0.15, 0.12, 0.9 - i * 0.15), geom="box")
        step.apply_translation([0, 0.06 + i * 0.12, D / 2 + 0.05 + i * 0.12])
        parts.append((f"step{i}", step))

    # 室内地板
    floor = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(W - 0.06, 0.05, D - 0.06), geom="box")
    floor.apply_translation([0, base_y, 0])
    parts.append(("floor", floor))

    return parts


def gen_coop(seed=1):
    """鸡舍 v4"""
    rng = gl.rng_from_seed(seed)
    wall_c = gl.jitter(gl.C("wood"), 0.02, rng)
    wood_dark_c = gl.jitter(gl.C("wood_dark"), 0.02, rng)
    stone_c = gl.jitter(gl.C("stone"), 0.02, rng)

    W, D, H = 1.8, 1.5, 1.15
    wall_t = 0.1
    base_y = 0.14
    parts = []
    f = gl.mesh(gl.jitter(stone_c, 0.03, rng), extents=(W + 0.3, 0.14, D + 0.3), geom="box")
    f.apply_translation([0, 0.07, 0])
    parts.append(("foundation", f))
    front = gl.mesh(gl.jitter(wall_c, 0.02, rng), extents=(W, H, wall_t), geom="box")
    front.apply_translation([0, base_y + H / 2, D / 2])
    parts.append(("front", front))
    hole = gl.mesh(gl.C("black"), extents=(0.44, 0.66, wall_t + 0.05), geom="box")
    hole.apply_translation([0, base_y + 0.5, D / 2])
    parts.append(("front_open", hole))
    back = gl.mesh(gl.jitter(wall_c, 0.02, rng), extents=(W, H, wall_t), geom="box")
    back.apply_translation([0, base_y + H / 2, -D / 2])
    parts.append(("back", back))
    for sx, rot in ((1, 90), (-1, -90)):
        side = gl.mesh(gl.jitter(wall_c, 0.02, rng), extents=(D, H, wall_t), geom="box")
        side.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
        side.apply_translation([sx * W / 2, base_y + H / 2, 0])
        parts.append((f"side_{sx}", side))
    door_parts = _door(wood_dark_c, 0.44, 0.66, base_y, arched=True)
    for name, m in door_parts:
        m.apply_translation([0, 0, D / 2 + 0.02])
        parts.append((name, m))
    roof_parts, peak_y = _gable_roof("roof", W, D, 0.7, base_y + H, eave=0.24, tile_rows=3)
    parts.extend(roof_parts)
    ch = _chimney(gl.jitter(gl.C("stone"), 0.03, rng), 0.16, 0.55, 0.16, 0.55, -0.5, peak_y - 0.1, rows=3)
    parts.extend([(f"chim_{n}", m) for n, m in ch])
    floor = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(W - 0.04, 0.04, D - 0.04), geom="box")
    floor.apply_translation([0, base_y, 0])
    parts.append(("floor", floor))
    return parts


def gen_barn(seed=1):
    """牛棚 v4：红墙 + 真坡顶 + 双开门 + 侧窗"""
    rng = gl.rng_from_seed(seed)
    wall_c = gl.jitter(gl.C("roof"), 0.02, rng)
    wood_dark_c = gl.jitter(gl.C("wood_dark"), 0.02, rng)
    wood_c = gl.jitter(gl.C("wood"), 0.02, rng)
    stone_c = gl.jitter(gl.C("stone"), 0.02, rng)

    W, D, H = 2.6, 2.2, 1.6
    wall_t = 0.12
    base_y = 0.16
    parts = []
    f = gl.mesh(gl.jitter(stone_c, 0.03, rng), extents=(W + 0.4, 0.16, D + 0.4), geom="box")
    f.apply_translation([0, 0.08, 0])
    parts.append(("foundation", f))
    front = gl.mesh(gl.jitter(wall_c, 0.02, rng), extents=(W, H, wall_t), geom="box")
    front.apply_translation([0, base_y + H / 2, D / 2])
    parts.append(("front", front))
    hole = gl.mesh(gl.C("black"), extents=(1.0, 1.1, wall_t + 0.05), geom="box")
    hole.apply_translation([0, base_y + 0.72, D / 2])
    parts.append(("front_open", hole))
    back = gl.mesh(gl.jitter(wall_c, 0.02, rng), extents=(W, H, wall_t), geom="box")
    back.apply_translation([0, base_y + H / 2, -D / 2])
    parts.append(("back", back))
    for sx, rot in ((1, 90), (-1, -90)):
        side = gl.mesh(gl.jitter(wall_c, 0.02, rng), extents=(D, H, wall_t), geom="box")
        side.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
        side.apply_translation([sx * W / 2, base_y + H / 2, 0])
        parts.append((f"side_{sx}", side))
        hole = gl.mesh(gl.C("black"), extents=(0.4, 0.4, wall_t + 0.05), geom="box")
        hole.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
        hole.apply_translation([sx * W / 2, base_y + 0.75, 0.4])
        parts.append((f"side_open_{sx}", hole))
    # 双开门
    for sx, hs in ((-1, 1), (1, -1)):
        door_parts = _door(wood_dark_c, 0.5, 1.1, base_y, arched=False, prefix=f"bdoor_{sx}")
        for name, m in door_parts:
            m.apply_translation([sx * 0.25, 0, D / 2 + 0.02])
            parts.append((name, m))
    # 侧窗
    for sx in (-1, 1):
        win = _window(wood_c, 0.4, 0.4, base_y + 0.75, sill=True, cross=True)
        for name, m in win:
            m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90 * sx), [0, 1, 0], [0, 0, 0]))
            m.apply_translation([sx * W / 2, 0, 0.4])
            parts.append((f"win_{sx}_{name}", m))
    roof_parts, peak_y = _gable_roof("wood_dark", W, D, 0.95, base_y + H, eave=0.32, tile_rows=3)
    parts.extend(roof_parts)
    ch = _chimney(gl.jitter(gl.C("stone"), 0.03, rng), 0.22, 0.75, 0.22, -0.8, -0.7, peak_y - 0.12, rows=4)
    parts.extend([(f"chim_{n}", m) for n, m in ch])
    floor = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(W - 0.06, 0.05, D - 0.06), geom="box")
    floor.apply_translation([0, base_y, 0])
    parts.append(("floor", floor))
    return parts


def gen_well(seed=1):
    """水井 v4：石壁 + 砖缝 + 木顶 + 滑轮 + 小坡顶 + 提桶"""
    rng = gl.rng_from_seed(seed)
    stone_c = gl.jitter(gl.C("stone"), 0.02, rng)
    wood_c = gl.jitter(gl.C("wood"), 0.02, rng)
    wood_dark_c = gl.jitter(gl.C("wood_dark"), 0.02, rng)
    parts = []
    ring = gl.mesh(gl.jitter(stone_c, 0.02, rng), radius=0.42, height=0.08, sections=14, geom="cylinder")
    ring.apply_translation([0, 0.04, 0])
    parts.append(("ground_ring", ring))
    for i, (r, h, y) in enumerate(((0.32, 0.22, 0.11), (0.28, 0.2, 0.32))):
        wall = gl.mesh(gl.jitter(stone_c, 0.03, rng), radius=r, height=h, sections=12, geom="cylinder")
        wall.apply_translation([0, y, 0])
        parts.append((f"wall{i}", wall))
    for i in range(4):
        band = gl.mesh(gl.jitter(gl.C("cream"), 0.02, rng), radius=0.305, height=0.03, sections=12, geom="cylinder")
        band.apply_translation([0, 0.2 + i * 0.09, 0])
        parts.append((f"band{i}", band))
    inner = gl.mesh(gl.C("black"), radius=0.16, height=0.44, sections=8, geom="cylinder")
    inner.apply_translation([0, 0.22, 0])
    parts.append(("inner", inner))
    for side in (-1, 1):
        post = gl.mesh(wood_c, radius=0.04, height=0.9, sections=8, geom="cylinder")
        post.apply_translation([0.24 * side, 0.55, 0])
        parts.append((f"post{side}", post))
    crossbar = gl.mesh(wood_c, extents=(0.58, 0.07, 0.07), geom="box")
    crossbar.apply_translation([0, 1.05, 0])
    parts.append(("crossbar", crossbar))
    pulley = gl.mesh(gl.jitter(wood_dark_c, 0.02, rng), radius=0.05, height=0.04, sections=10, geom="cylinder")
    pulley.apply_translation([0, 1.02, 0.05])
    parts.append(("pulley", pulley))
    roof_parts, _ = _gable_roof("roof", 0.78, 0.78, 0.35, 1.05, eave=0.16, tile_rows=2)
    parts.extend([(f"roof_{n}", m) for n, m in roof_parts])
    bucket = gl.mesh(gl.jitter(wood_c, 0.02, rng), radius=0.07, height=0.1, sections=8, geom="cylinder")
    bucket.apply_translation([0, 0.72, 0.1])
    parts.append(("bucket", bucket))
    rope = gl.mesh(gl.C("cream"), radius=0.007, height=0.18, sections=4, geom="cylinder")
    rope.apply_translation([0, 0.92, 0.1])
    parts.append(("rope", rope))
    return parts
