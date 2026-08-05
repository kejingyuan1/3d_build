# -*- coding: utf-8 -*-
"""
季节与生长阶段生成器：
① 番茄/南瓜三阶段补齐（seed→seedling→mature，与小麦/胡萝卜风格一致）
② 季节皮肤（春/夏/秋/冬）：树（oak/apple ×4）、草地 ×4、耕地 ×4
输出：assets/plants/（植物/树/耕地）+ assets/props/（草地）
依赖 gen_lib 强制规范：PALETTE/C/jitter/mesh/export_scene/_ensure_normals
"""
import os
import sys
import shutil
import struct
import json as _json
import numpy as np
import trimesh

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import gen_lib as gl

# ================ 季节色板（亮色卡通风） ================
SEASON_COLORS = {
    "spring": {"leaf": (0x7E, 0xC8, 0x50), "leaf2": (0x8F, 0xD4, 0x5E), "flower": (0xF4, 0xA9, 0xA9), "flower2": (0xF8, 0xDC, 0xE0)},
    "summer": {"leaf": (0x3E, 0x8E, 0x41), "leaf2": (0x4C, 0x9A, 0x4E)},
    "autumn": {"leaf": (0xE8, 0xA3, 0x3D), "leaf2": (0xD9, 0x6A, 0x2B), "leaf3": (0xF0, 0xC4, 0x2E)},
    "winter": {"snow": (0xE8, 0xF2, 0xF8), "snow2": (0xC8, 0xDC, 0xE8), "branch": (0x7A, 0x5B, 0x3A)},
}


def _j(c, amt=0.03, rng=None):
    return gl.jitter(c, amt, rng)


def _sphere(color, radius, subdiv=1, scale=None):
    """低模球体（icosphere 低细分，避免默认 642 顶点导致体积过大）"""
    m = trimesh.creation.icosphere(subdivisions=subdiv, radius=radius)
    gl._ensure_normals(m)
    m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=color)
    if scale is not None:
        m.apply_scale(scale)
    return m


def _vcyl(color, radius, height, sections=8, rng=None):
    """竖直圆柱（Y 轴向上）：trimesh cylinder 默认沿 Z，需绕 X 转 -90° 竖立（Z→+Y）"""
    c = gl.mesh(color, radius=radius, height=height, sections=sections, geom="cylinder")
    c.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0], [0, 0, 0]))
    return c


def _rot_y(ang_deg):
    return trimesh.transformations.rotation_matrix(np.radians(ang_deg), [0, 1, 0], [0, 0, 0])


def _rot_z(ang_deg):
    return trimesh.transformations.rotation_matrix(np.radians(ang_deg), [0, 0, 1], [0, 0, 0])


# ================ 通用：小土包 + 种子点 ================

def _seed_patch(soil_c, seed_c, seed=1, size=0.08):
    """小土包 + 种子点（种子阶段通用，2KB 级）"""
    rng = gl.rng_from_seed(seed)
    parts = []
    mound = _sphere(_j(soil_c, 0.05, rng), radius=size * 0.5, subdiv=1, scale=[1.0, 0.45, 1.0])
    mound.apply_translation([0, size * 0.06, 0])
    parts.append(("mound", mound))
    dot = _sphere(_j(seed_c, 0.04, rng), radius=size * 0.1, subdiv=1, scale=[1.0, 0.6, 1.0])
    dot.apply_translation([0, size * 0.12, 0])
    parts.append(("seed_dot", dot))
    return parts


# ================ ① 番茄三阶段 ================

def gen_tomato_seed(seed=1):
    return _seed_patch(gl.C("soil"), gl.C("tomato"), seed=seed, size=0.08)


def gen_tomato_seedling(seed=2):
    """番茄苗：茎 + 2-3 片嫩叶"""
    rng = gl.rng_from_seed(seed)
    green = gl.jitter(gl.C("grass"), 0.05, rng)
    green2 = gl.jitter(gl.C("leaf_light"), 0.05, rng)
    parts = []
    h = 0.18
    stem = _vcyl(green, radius=0.012, height=h, sections=6)
    stem.apply_translation([0, h / 2, 0])
    parts.append(("stem", stem))
    for i in range(3):
        leaf = gl.mesh(green2 if i % 2 else green, extents=(0.05, 0.1, 0.015), geom="box")
        leaf.apply_translation([0, h * (0.5 + 0.15 * i), 0])
        leaf.apply_transform(trimesh.transformations.rotation_matrix(np.radians(45 * (i + 1)), [0, 1, 0], [0, 0, 0]))
        leaf.apply_transform(trimesh.transformations.rotation_matrix(np.radians(18 * (1 if i % 2 else -1)), [0, 0, 1], [0, 0, 0]))
        parts.append((f"leaf{i}", leaf))
    return parts


# mature 直接复制现有 plant_tomato.glb（已是成熟态：矮株+绿叶+红果）

# ================ ① 南瓜三阶段 ================

def gen_pumpkin_seed(seed=3):
    return _seed_patch(gl.C("soil"), gl.C("pumpkin"), seed=seed, size=0.09)


def gen_pumpkin_seedling(seed=4):
    """南瓜苗：藤蔓小苗 + 卷须"""
    rng = gl.rng_from_seed(seed)
    green = gl.jitter(gl.C("leaf_dark"), 0.05, rng)
    parts = []
    h = 0.16
    stem = _vcyl(green, radius=0.012, height=h, sections=6)
    stem.apply_translation([0, h / 2, 0])
    parts.append(("stem", stem))
    for i in range(3):
        leaf = gl.mesh(_j(gl.C("grass"), 0.05, rng), extents=(0.06, 0.08, 0.015), geom="box")
        leaf.apply_translation([0, h * (0.45 + 0.12 * i), 0])
        leaf.apply_transform(trimesh.transformations.rotation_matrix(np.radians(60 * i + 30), [0, 1, 0], [0, 0, 0]))
        leaf.apply_transform(trimesh.transformations.rotation_matrix(np.radians(22), [0, 0, 1], [0, 0, 0]))
        parts.append((f"leaf{i}", leaf))
    # 卷须（细长弯条，竖立后倾斜）
    tendril = _vcyl(green, radius=0.006, height=0.12, sections=5)
    tendril.apply_transform(trimesh.transformations.rotation_matrix(np.radians(50), [0, 0, 1], [0, 0, 0]))
    tendril.apply_translation([0.03, h + 0.06, 0.02])
    parts.append(("tendril", tendril))
    return parts


# mature 直接复制现有 plant_pumpkin.glb（已是成熟态：藤蔓+大橙南瓜）

# ================ ② 季节树（oak/apple ×4） ================

def _bare_tree(trunk_c, trunk_h, trunk_r, branch_c, rng, snow=False):
    """冬季光秃树：竖直树干 + 数根斜枝（Y-up）+ 可选积雪"""
    parts = []
    trunk = _vcyl(trunk_c, radius=trunk_r, height=trunk_h, sections=8)
    trunk.apply_translation([0, trunk_h / 2, 0])
    parts.append(("trunk", trunk))
    for i in range(5):
        ang = i * 2 * np.pi / 5 + rng.uniform(-0.3, 0.3)
        tilt = 50 + rng.uniform(-8, 8)
        br_len = rng.uniform(0.32, 0.5)
        br = _vcyl(branch_c, radius=0.022, height=br_len, sections=6)
        br.apply_transform(trimesh.transformations.rotation_matrix(np.radians(tilt), [0, 0, 1], [0, 0, 0]))
        br.apply_transform(trimesh.transformations.rotation_matrix(ang, [0, 1, 0], [0, 0, 0]))
        br.apply_translation([0, trunk_h - 0.06, 0])
        parts.append((f"branch{i}", br))
        if snow:
            # 枝尖位置：竖立枝绕 Z 倾斜再绕 Y 旋转
            tip = np.array([0, br_len * 0.82, 0.0])
            tip = trimesh.transformations.rotation_matrix(np.radians(tilt), [0, 0, 1], [0, 0, 0])[:3, :3] @ tip
            tip = trimesh.transformations.rotation_matrix(ang, [0, 1, 0], [0, 0, 0])[:3, :3] @ tip
            sn = _sphere(_j(SEASON_COLORS["winter"]["snow"], 0.03, rng), radius=0.045, subdiv=1, scale=[1.0, 0.7, 1.0])
            sn.apply_translation([tip[0], trunk_h - 0.06 + tip[1] + 0.02, tip[2]])
            parts.append((f"snow{i}", sn))
    # 主冠雪
    cap = _sphere(_j(SEASON_COLORS["winter"]["snow2"], 0.03, rng), radius=0.1, subdiv=1, scale=[1.2, 0.5, 1.2])
    cap.apply_translation([0, trunk_h + 0.06, 0])
    parts.append(("snow_cap", cap))
    return parts


def _season_tree(kind, season, seed=10):
    """季节树：树干 + 树冠球簇 + 季节装饰（芽/花/果/雪）"""
    rng = gl.rng_from_seed(seed)
    trunk_c = gl.jitter(gl.C("wood"), 0.05, rng)
    trunk_h = 0.9
    trunk_r = 0.07
    crown_r = 0.42
    sc = SEASON_COLORS[season]

    if season == "winter":
        return _bare_tree(trunk_c, trunk_h, trunk_r, sc["branch"], rng, snow=True)

    if season == "spring":
        if kind == "oak":
            main_c = _j(sc["leaf"], 0.05, rng)
            sub_cs = [_j(sc["leaf"], 0.05, rng), _j(sc["leaf2"], 0.05, rng), _j(sc["leaf"], 0.05, rng)]
        else:  # apple 满冠粉白花
            main_c = _j(sc["flower2"], 0.05, rng)
            sub_cs = [_j(sc["flower"], 0.06, rng), _j(sc["flower2"], 0.05, rng), _j(sc["flower"], 0.06, rng)]
    elif season == "summer":
        main_c = _j(sc["leaf"], 0.05, rng)
        sub_cs = [_j(sc["leaf2"], 0.05, rng), _j(sc["leaf"], 0.05, rng), _j(sc["leaf2"], 0.05, rng)]
    else:  # autumn 橙黄红
        pal = [sc["leaf"], sc["leaf2"], sc["leaf3"]]
        main_c = _j(pal[0], 0.05, rng)
        sub_cs = [_j(pal[i % 3], 0.06, rng) for i in range(3)]

    parts = []
    trunk = _vcyl(trunk_c, radius=trunk_r, height=trunk_h, sections=8)
    trunk.apply_translation([0, trunk_h / 2, 0])
    parts.append(("trunk", trunk))
    main = _sphere(main_c, radius=crown_r, subdiv=2)
    main.apply_translation([0, trunk_h + crown_r * 0.7, 0])
    parts.append(("crown_main", main))
    for i in range(3):
        ang = i * 2 * np.pi / 3 + rng.uniform(-0.25, 0.25)
        sub = _sphere(sub_cs[i], radius=crown_r * 0.55, subdiv=2)
        sub.apply_translation([
            crown_r * 0.75 * np.cos(ang),
            trunk_h + crown_r * (0.35 + (i % 2) * 0.3),
            crown_r * 0.75 * np.sin(ang),
        ])
        parts.append((f"crown_sub{i}", sub))

    # ---- 季节装饰 ----
    if season == "spring" and kind == "oak":
        # 浅粉芽点
        for i in range(6):
            ang = i * np.pi / 3
            bud = _sphere(_j(sc["flower"], 0.05, rng), radius=0.025, subdiv=1)
            bud.apply_translation([crown_r * 0.55 * np.cos(ang), trunk_h + crown_r * 0.9, crown_r * 0.55 * np.sin(ang)])
            parts.append((f"bud{i}", bud))
    elif season == "spring" and kind == "apple":
        # 花
        for i in range(8):
            ang = i * np.pi / 4
            fl = _sphere(_j(sc["flower"], 0.04, rng), radius=0.03, subdiv=1)
            fl.apply_translation([crown_r * 0.6 * np.cos(ang), trunk_h + crown_r * (0.75 + 0.12 * (i % 2)), crown_r * 0.6 * np.sin(ang)])
            parts.append((f"flower{i}", fl))
    elif season == "summer" and kind == "apple":
        # 绿/青果
        for i in range(4):
            ang = i * np.pi / 2 + 0.4
            fruit = _sphere(_j(gl.C("grass"), 0.05, rng), radius=0.04, subdiv=1)
            fruit.apply_translation([crown_r * 0.55 * np.cos(ang), trunk_h + crown_r * 0.55, crown_r * 0.55 * np.sin(ang)])
            parts.append((f"fruit{i}", fruit))
    elif season == "autumn" and kind == "apple":
        # 红果
        for i in range(4):
            ang = i * np.pi / 2 + 0.4
            fruit = _sphere(_j(gl.C("tomato"), 0.05, rng), radius=0.04, subdiv=1)
            fruit.apply_translation([crown_r * 0.55 * np.cos(ang), trunk_h + crown_r * 0.55, crown_r * 0.55 * np.sin(ang)])
            parts.append((f"fruit{i}", fruit))
    return parts


# ================ ② 季节草地 ================

def gen_grass_season(season, seed=20):
    """草地 1m 薄板，按季节变色"""
    rng = gl.rng_from_seed(seed)
    sc = SEASON_COLORS[season]
    if season == "summer":
        c = gl.jitter(gl.C("grass"), 0.04, rng)
    elif season == "spring":
        c = _j(sc["leaf"], 0.04, rng)
    elif season == "autumn":
        c = _j(sc["leaf3"], 0.04, rng)
    else:  # winter 雪地
        c = _j(sc["snow"], 0.03, rng)
    tile = gl.mesh(c, extents=(1.0, 0.1, 1.0), geom="box")
    tile.apply_translation([0, 0.05, 0])
    parts = [("tile", tile)]
    if season == "spring":
        for i in range(5):
            tuft = gl.mesh(_j(sc["leaf"], 0.05, rng), extents=(0.03, 0.08, 0.03), geom="box")
            tuft.apply_translation([-0.3 + i * 0.15, 0.12, 0.1])
            parts.append((f"tuft{i}", tuft))
    elif season == "autumn":
        for i in range(4):
            leaf = gl.mesh(_j(sc["leaf2"], 0.05, rng), extents=(0.05, 0.015, 0.05), geom="box")
            leaf.apply_translation([-0.3 + i * 0.2, 0.055, 0.15])
            parts.append((f"leaf{i}", leaf))
    elif season == "winter":
        for i in range(5):
            drift = gl.mesh(_j(sc["snow2"], 0.03, rng), extents=(0.2, 0.06, 0.2), geom="box")
            drift.apply_translation([-0.35 + i * 0.18, 0.08, 0.0])
            parts.append((f"drift{i}", drift))
    return parts


# ================ ② 季节耕地 ================

def gen_tilled_soil_season(season, seed=30):
    """耕地 1m 薄板 + 犁沟，按季节变色（秋=干裂、冬=覆雪）"""
    rng = gl.rng_from_seed(seed)
    sc = SEASON_COLORS[season]
    parts = []
    if season == "winter":
        base_c = _j(sc["snow"], 0.03, rng)
        ridge_c = _j(sc["snow2"], 0.03, rng)
    elif season == "autumn":
        base_c = gl.jitter(gl.C("soil"), 0.06, rng)
        ridge_c = _j(gl.C("soil"), 0.06, rng)
    elif season == "spring":
        base_c = _j(gl.C("soil"), 0.04, rng)
        ridge_c = _j(sc["leaf"], 0.04, rng)
    else:
        base_c = gl.jitter(gl.C("soil"), 0.04, rng)
        ridge_c = gl.jitter(gl.C("soil"), 0.03, rng)
    base = gl.mesh(base_c, extents=(1.0, 0.05, 1.0), geom="box")
    base.apply_translation([0, 0.025, 0])
    parts.append(("soil_base", base))
    for i in range(3):
        ridge = gl.mesh(_j(ridge_c, 0.04, rng), extents=(0.14, 0.04, 0.9), geom="box")
        ridge.apply_translation([-0.3 + i * 0.3, 0.06, 0])
        parts.append((f"ridge{i}", ridge))
    if season == "autumn":
        # 干裂缝
        for i in range(4):
            crack = gl.mesh(_j(gl.C("wood_dark"), 0.03, rng), extents=(0.02, 0.012, 0.12), geom="box")
            crack.apply_translation([-0.35 + i * 0.25, 0.035, 0.1])
            crack.apply_transform(trimesh.transformations.rotation_matrix(np.radians(20 * (i % 2 - 0.5)), [0, 1, 0], [0, 0, 0]))
            parts.append((f"crack{i}", crack))
    elif season == "winter":
        # 积雪垄
        for i in range(3):
            cap = gl.mesh(_j(sc["snow"], 0.03, rng), extents=(0.16, 0.05, 0.92), geom="box")
            cap.apply_translation([-0.3 + i * 0.3, 0.09, 0])
            parts.append((f"cap{i}", cap))
    elif season == "spring":
        # 嫩芽
        for i in range(3):
            sprout = gl.mesh(_j(sc["leaf"], 0.05, rng), extents=(0.03, 0.07, 0.03), geom="box")
            sprout.apply_translation([-0.3 + i * 0.3, 0.095, 0.0])
            parts.append((f"sprout{i}", sprout))
    return parts


# ================ 注册表（生成函数 + 复制源） ================

GENERATORS = {
    "plant_tomato_seed": gen_tomato_seed,
    "plant_tomato_seedling": gen_tomato_seedling,
    "plant_pumpkin_seed": gen_pumpkin_seed,
    "plant_pumpkin_seedling": gen_pumpkin_seedling,
    "plant_tree_oak_spring": lambda: _season_tree("oak", "spring", 101),
    "plant_tree_oak_summer": lambda: _season_tree("oak", "summer", 102),
    "plant_tree_oak_autumn": lambda: _season_tree("oak", "autumn", 103),
    "plant_tree_oak_winter": lambda: _season_tree("oak", "winter", 104),
    "plant_tree_apple_spring": lambda: _season_tree("apple", "spring", 201),
    "plant_tree_apple_summer": lambda: _season_tree("apple", "summer", 202),
    "plant_tree_apple_autumn": lambda: _season_tree("apple", "autumn", 203),
    "plant_tree_apple_winter": lambda: _season_tree("apple", "winter", 204),
    "terrain_grass_spring": lambda: gen_grass_season("spring", 301),
    "terrain_grass_summer": lambda: gen_grass_season("summer", 302),
    "terrain_grass_autumn": lambda: gen_grass_season("autumn", 303),
    "terrain_grass_winter": lambda: gen_grass_season("winter", 304),
    "plant_tilled_soil_spring": lambda: gen_tilled_soil_season("spring", 401),
    "plant_tilled_soil_summer": lambda: gen_tilled_soil_season("summer", 402),
    "plant_tilled_soil_autumn": lambda: gen_tilled_soil_season("autumn", 403),
    "plant_tilled_soil_winter": lambda: gen_tilled_soil_season("winter", 404),
}

# 直接复制现有成熟资产的（避免重复生成）
COPIES = {
    "plant_tomato_mature": ("plants/plant_tomato.glb", "plants/plant_tomato_mature.glb"),
    "plant_pumpkin_mature": ("plants/plant_pumpkin.glb", "plants/plant_pumpkin_mature.glb"),
}

# 输出子目录
SUBDIR = {
    "terrain_grass_spring": "props", "terrain_grass_summer": "props",
    "terrain_grass_autumn": "props", "terrain_grass_winter": "props",
}

# 碰撞（seed/seedling = none，成熟/树 = 与现有一致，草地/耕地 = 薄板）
COLLISION = {
    "plant_tomato_seed": {"type": "none"},
    "plant_tomato_seedling": {"type": "none"},
    "plant_tomato_mature": {"type": "fixed", "shape": "cylinder", "params": {"r": 0.12, "h": 0.3}},
    "plant_pumpkin_seed": {"type": "none"},
    "plant_pumpkin_seedling": {"type": "none"},
    "plant_pumpkin_mature": {"type": "fixed", "shape": "sphere", "params": {"r": 0.22}},
    "plant_tree_oak_spring": {"type": "fixed", "shape": "cylinder", "params": {"r": 0.08, "h": 1.0}},
    "plant_tree_oak_summer": {"type": "fixed", "shape": "cylinder", "params": {"r": 0.08, "h": 1.0}},
    "plant_tree_oak_autumn": {"type": "fixed", "shape": "cylinder", "params": {"r": 0.08, "h": 1.0}},
    "plant_tree_oak_winter": {"type": "fixed", "shape": "cylinder", "params": {"r": 0.08, "h": 1.0}},
    "plant_tree_apple_spring": {"type": "fixed", "shape": "cylinder", "params": {"r": 0.08, "h": 1.0}},
    "plant_tree_apple_summer": {"type": "fixed", "shape": "cylinder", "params": {"r": 0.08, "h": 1.0}},
    "plant_tree_apple_autumn": {"type": "fixed", "shape": "cylinder", "params": {"r": 0.08, "h": 1.0}},
    "plant_tree_apple_winter": {"type": "fixed", "shape": "cylinder", "params": {"r": 0.08, "h": 1.0}},
    "terrain_grass_spring": {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 0.05, "hz": 0.5}},
    "terrain_grass_summer": {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 0.05, "hz": 0.5}},
    "terrain_grass_autumn": {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 0.05, "hz": 0.5}},
    "terrain_grass_winter": {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 0.05, "hz": 0.5}},
    "plant_tilled_soil_spring": {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 0.03, "hz": 0.5}},
    "plant_tilled_soil_summer": {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 0.03, "hz": 0.5}},
    "plant_tilled_soil_autumn": {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 0.03, "hz": 0.5}},
    "plant_tilled_soil_winter": {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 0.03, "hz": 0.5}},
}

NAMES = {
    "plant_tomato_seed": "番茄-种子", "plant_tomato_seedling": "番茄-幼苗", "plant_tomato_mature": "番茄-成熟",
    "plant_pumpkin_seed": "南瓜-种子", "plant_pumpkin_seedling": "南瓜-幼苗", "plant_pumpkin_mature": "南瓜-成熟",
    "plant_tree_oak_spring": "橡树-春", "plant_tree_oak_summer": "橡树-夏", "plant_tree_oak_autumn": "橡树-秋", "plant_tree_oak_winter": "橡树-冬",
    "plant_tree_apple_spring": "苹果树-春", "plant_tree_apple_summer": "苹果树-夏", "plant_tree_apple_autumn": "苹果树-秋", "plant_tree_apple_winter": "苹果树-冬",
    "terrain_grass_spring": "草地-春", "terrain_grass_summer": "草地-夏", "terrain_grass_autumn": "草地-秋", "terrain_grass_winter": "草地-冬",
    "plant_tilled_soil_spring": "耕地-春", "plant_tilled_soil_summer": "耕地-夏", "plant_tilled_soil_autumn": "耕地-秋", "plant_tilled_soil_winter": "耕地-冬",
}

DESCS = {
    "plant_tomato_seed": "番茄生长阶段 1/3", "plant_tomato_seedling": "番茄生长阶段 2/3", "plant_tomato_mature": "番茄生长阶段 3/3",
    "plant_pumpkin_seed": "南瓜生长阶段 1/3", "plant_pumpkin_seedling": "南瓜生长阶段 2/3", "plant_pumpkin_mature": "南瓜生长阶段 3/3",
    "plant_tree_oak_spring": "橡树季节皮肤-春", "plant_tree_oak_summer": "橡树季节皮肤-夏", "plant_tree_oak_autumn": "橡树季节皮肤-秋", "plant_tree_oak_winter": "橡树季节皮肤-冬",
    "plant_tree_apple_spring": "苹果树季节皮肤-春", "plant_tree_apple_summer": "苹果树季节皮肤-夏", "plant_tree_apple_autumn": "苹果树季节皮肤-秋", "plant_tree_apple_winter": "苹果树季节皮肤-冬",
    "terrain_grass_spring": "草地季节皮肤-春", "terrain_grass_summer": "草地季节皮肤-夏", "terrain_grass_autumn": "草地季节皮肤-秋", "terrain_grass_winter": "草地季节皮肤-冬",
    "plant_tilled_soil_spring": "耕地季节皮肤-春", "plant_tilled_soil_summer": "耕地季节皮肤-夏", "plant_tilled_soil_autumn": "耕地季节皮肤-秋(干裂)", "plant_tilled_soil_winter": "耕地季节皮肤-冬(覆雪)",
}

# designId 系列：PLA-S01..18（植物/树/耕地），TER-S01..04（草地）
DESIGN_IDS = {}
_plant_ids = [
    "plant_tomato_seed", "plant_tomato_seedling", "plant_tomato_mature",
    "plant_pumpkin_seed", "plant_pumpkin_seedling", "plant_pumpkin_mature",
    "plant_tree_oak_spring", "plant_tree_oak_summer", "plant_tree_oak_autumn", "plant_tree_oak_winter",
    "plant_tree_apple_spring", "plant_tree_apple_summer", "plant_tree_apple_autumn", "plant_tree_apple_winter",
    "plant_tilled_soil_spring", "plant_tilled_soil_summer", "plant_tilled_soil_autumn", "plant_tilled_soil_winter",
]
for i, aid in enumerate(_plant_ids):
    DESIGN_IDS[aid] = f"PLA-S{i+1:02d}"
DESIGN_IDS.update({
    "terrain_grass_spring": "TER-S01", "terrain_grass_summer": "TER-S02",
    "terrain_grass_autumn": "TER-S03", "terrain_grass_winter": "TER-S04",
})


def all_ids():
    return list(GENERATORS.keys()) + list(COPIES.keys())


def generate(assets_dir=None, verify=True):
    """生成全部 22 个 GLB（20 生成 + 2 复制）并验证"""
    if assets_dir is None:
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(BASE)), "assets")
    os.makedirs(os.path.join(assets_dir, "plants"), exist_ok=True)
    os.makedirs(os.path.join(assets_dir, "props"), exist_ok=True)
    results = {}
    for aid, fn in GENERATORS.items():
        parts = fn()
        # 锚点归零：整体平移使最低 y = 0（无论正负都校正）
        min_y = min(m.bounds[0][1] for _, m in parts)
        if abs(min_y) > 1e-6:
            for _, m in parts:
                m.apply_translation([0, -min_y, 0])
        sub = SUBDIR.get(aid, "plants")
        path = os.path.join(assets_dir, sub, f"{aid}.glb")
        gl.export_scene(parts, path)
        size_kb = os.path.getsize(path) / 1024
        results[aid] = {"path": path, "sizeKB": round(size_kb, 1), "parts": len(parts)}
        if verify:
            ok = verify_glb(path)
            results[aid]["verify"] = ok
    # 复制成熟资产（并归零锚点，保证 GLB 锚点=底部中心）
    for aid, (src_rel, dst_rel) in COPIES.items():
        src = os.path.join(assets_dir, src_rel)
        dst = os.path.join(assets_dir, dst_rel)
        if os.path.exists(src):
            scene = trimesh.load(src)
            if hasattr(scene, 'geometry') and scene.geometry:
                min_y = min(g.bounds[0][1] for g in scene.geometry.values())
                if abs(min_y) > 1e-6:
                    for g in scene.geometry.values():
                        g.apply_translation([0, -min_y, 0])
                scene.export(dst)
            else:
                shutil.copy2(src, dst)
            size_kb = os.path.getsize(dst) / 1024
            results[aid] = {"path": dst, "sizeKB": round(size_kb, 1), "parts": "copy", "verify": verify_glb(dst)}
        else:
            results[aid] = {"error": f"source missing: {src}"}
    return results


def verify_glb(path):
    """验证 GLB：trimesh 加载 OK + JSON chunk 含 POSITION/NORMAL/COLOR_0"""
    try:
        scene = trimesh.load(path)
        if scene is None:
            return False
        with open(path, "rb") as f:
            data = f.read()
        if len(data) < 20:
            return False
        json_len = struct.unpack_from("<I", data, 12)[0]
        glb = _json.loads(data[20:20 + json_len].decode("utf-8"))
        found = {"POSITION": False, "NORMAL": False, "COLOR_0": False}
        for m in glb.get("meshes", []):
            for prim in m.get("primitives", []):
                attrs = prim.get("attributes", {})
                for k in found:
                    if k in attrs:
                        found[k] = True
        return all(found.values())
    except Exception as e:
        print(f"  verify error: {e}")
        return False


if __name__ == "__main__":
    res = generate()
    for aid, r in res.items():
        if "error" in r:
            print(f"  ✘ {aid}: {r['error']}")
        else:
            print(f"  {'✔' if r.get('verify') else '✘'} {aid} ({r['sizeKB']:.1f} KB)")
