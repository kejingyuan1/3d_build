# -*- coding: utf-8 -*-
"""
海洋地图 + 矿藏资源生成器（SCALE=20 放大版）
农场牧场网页游戏 · 海洋地图（1 海面 + 16 岛屿）+ 矿藏资源（3 种矿 × 3 档 = 9）
输出：assets/terrain/（terrain_ocean.glb + terrain_island_01..16.glb）+ assets/props/（ore_*.glb）
依赖 gen_lib 强制规范：PALETTE/C/jitter/mesh/export_scene/_ensure_normals + gen_seasons._vcyl 竖直圆柱模式

放大说明（2026 用户反馈：岛上要盖房+养殖+菜地，3-10m 太小）：
- 全局 SCALE=20：所有几何在 1× 生成后统一坐标缩放 ×20（顶点数不变，GLB 体积基本不变）。
  海面 40→800×800m、岛直径 3-10→60-200m（主岛 03 变 200m）、矿藏占地 0.4/1/2→8/20/40m。
- 海面例外：800m 大水面若沿用原 40 格细分太稀，波光斑块会糊；顶面细分 n=40→90（≈8.3k 顶点），
  底面 n=20→45，总顶点 ~10.4k（6000-12000 区间）。波光斑块坐标在 1× 空间定义、随 SCALE 等比放大。
- 锚点不变：岛基座底 min_y=0（海面 y=0），海面顶面 y=0；矿藏同规则。
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


# ================ 色板（海洋/岛屿/矿藏） ================
OCEAN_BASE   = (0x2E, 0x86, 0xC1, 255)   # 实体亮蓝 0x2E86C1
OCEAN_PATCH  = (0x5D, 0xAD, 0xE2, 255)   # 浅蓝波光 0x5DADE2
OCEAN_BORDER = (0x4A, 0x9B, 0xD6, 255)   # 边框稍亮
OCEAN_DEEP   = (0x1F, 0x5E, 0x8F, 255)   # 底面更深蓝

ISLAND_BASE  = (0x4A, 0x3B, 0x2E, 255)   # 水下基座 深棕
ISLAND_BASE_BLUE = (0x2E, 0x4A, 0x5E, 255)  # 水下基座 深蓝（部分岛用）
ISLAND_SAND   = (0xE8, 0xD8, 0xA0, 255)  # 沙滩环 米黄 0xE8D8A0
ISLAND_GRASS  = (0x7E, 0xC8, 0x50, 255)  # 草地顶 绿 0x7EC850
ISLAND_HILL   = (0x8F, 0xD4, 0x5E, 255)  # 山丘 草绿
ISLAND_ROCK   = (0x9A, 0xA3, 0xA8, 255)  # 岩石 灰 0x9AA3A8
PALM_TRUNK    = (0x8D, 0x6E, 0x63, 255)  # 棕榈树干 木棕
PALM_LEAF     = (0x1E, 0x7A, 0x3C, 255)  # 棕榈冠 深绿
HUT_WOOD      = (0xA0, 0x7B, 0x4F, 255)  # 小屋/码头 木色
HUT_ROOF      = (0xC8, 0x4B, 0x3A, 255)  # 屋顶红
DOCK_WOOD     = (0x8D, 0x6E, 0x63, 255)  # 码头木板

# 矿藏：body 主色 / hi 高亮
ORE_COLORS = {
    "copper": {"body": (0xC8, 0x75, 0x3A, 255), "hi": (0xB8, 0x6A, 0x30, 255)},
    "silver": {"body": (0xD8, 0xDC, 0xE0, 255), "hi": (0xC0, 0xC6, 0xCC, 255)},
    "gold":   {"body": (0xFF, 0xD7, 0x00, 255), "hi": (0xE8, 0xC8, 0x4A, 255)},
}
ORE_NAMES = {"copper": "铜矿", "silver": "银矿", "gold": "金矿"}
TIER_NAMES = {"small": "小型", "medium": "中型", "large": "大型"}

# 全局放大系数：1× 几何在 generate() 统一坐标缩放（顶点数不变）
SCALE = 20


# ================ 基础几何 helpers（沿用 gen_seasons 风格） ================

def _j(c, amt=0.04, rng=None):
    return gl.jitter(c, amt, rng)


def _rot_y(ang_deg):
    return trimesh.transformations.rotation_matrix(np.radians(ang_deg), [0, 1, 0], [0, 0, 0])


def _rot_z(ang_deg):
    return trimesh.transformations.rotation_matrix(np.radians(ang_deg), [0, 0, 1], [0, 0, 0])


def _vcyl(color, radius, height, sections=8):
    """竖直圆柱（Y 轴向上）：trimesh cylinder 默认沿 Z，需绕 X 转 -90° 竖立（Z→+Y）"""
    c = gl.mesh(color, radius=radius, height=height, sections=sections, geom="cylinder")
    c.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0], [0, 0, 0]))
    return c


def _sphere(color, radius, subdiv=1, scale=None):
    m = trimesh.creation.icosphere(subdivisions=subdiv, radius=radius)
    gl._ensure_normals(m)
    m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=color)
    if scale is not None:
        m.apply_scale(scale)
    return m


def _frustum(color, r_bot, r_top, height, y0=0.0, sections=16):
    """正体积截锥（Y 向上，底心在 y0，顶在 y0+height）；保证法线朝外"""
    ang = np.linspace(0, 2 * np.pi, sections, endpoint=False)
    bot = np.column_stack([r_bot * np.cos(ang), np.full(sections, y0), r_bot * np.sin(ang)])
    top = np.column_stack([r_top * np.cos(ang), np.full(sections, y0 + height), r_top * np.sin(ang)])
    verts = np.vstack([bot, top, [0, y0, 0], [0, y0 + height, 0]])
    faces = []
    for i in range(sections):
        j = (i + 1) % sections
        # 侧面 quad（两三角）
        faces.append([i, j, sections + j])
        faces.append([i, sections + j, sections + i])
        # 底盖（-Y）与顶盖（+Y），先用简单绕序，下面统一修法线
        faces.append([2 * sections, j, i])
        faces.append([2 * sections + 1, sections + i, sections + j])
    m = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    if m.volume < 0:
        m.invert()
    gl._ensure_normals(m)
    m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=color)
    return m


def _ore_chunk(color, rng, radius=0.1, jit=0.35):
    """不规则多面体矿石：icosphere 细分1 + 顶点径向抖动（非完美球）"""
    m = trimesh.creation.icosphere(subdivisions=1, radius=radius)
    v = m.vertices
    j = 1.0 + rng.uniform(-jit, jit, size=len(v))
    m.vertices = v * j[:, None]
    gl._ensure_normals(m)
    m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=color)
    return m


def _normalize_parts(parts):
    """锚点归零：整体平移使最低 y = 0（岛屿/矿藏用；海洋锚点=顶面另行处理）"""
    min_y = min(m.bounds[0][1] for _, m in parts)
    if abs(min_y) > 1e-6:
        for _, m in parts:
            m.apply_translation([0, -min_y, 0])
    return parts


def _scale_parts(parts, s=SCALE):
    """全局坐标缩放 ×s：顶点数不变，仅坐标放大；统一缩放保持 min_y=0 锚点"""
    if abs(s - 1.0) < 1e-9:
        return parts
    for _, m in parts:
        m.apply_scale(s)
    return parts


# ================ ① 海洋水面（1 个资产） ================

def _ocean_grid(n=40, size=40.0, y=0.0, color_fn=None):
    """构造 y 平面的 n×n 网格，逐顶点着色（用于波光斑块）"""
    xs = np.linspace(-size / 2, size / 2, n + 1)
    zs = np.linspace(-size / 2, size / 2, n + 1)
    verts, cols = [], []
    for z in zs:
        for x in xs:
            verts.append([x, y, z])
            cols.append(color_fn(x, z))
    faces = []
    for i in range(n):
        for j in range(n):
            a = i * (n + 1) + j
            b = (i + 1) * (n + 1) + j
            c = (i + 1) * (n + 1) + (j + 1)
            d = i * (n + 1) + (j + 1)
            faces.append([a, c, b])
            faces.append([a, d, c])
    m = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces), process=False)
    m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=np.array(cols, dtype=np.uint8))
    gl._ensure_normals(m)
    # 强制顶面法线朝 +Y
    if m.face_normals.mean(axis=0)[1] < 0:
        m.invert()
    return m


def _ocean_color_fn(x, z):
    """逐顶点色：亮蓝底 + 2-3 浅蓝波光圆/条 + 边框稍亮"""
    base = np.array(OCEAN_BASE[:3], dtype=float)
    patch = np.array(OCEAN_PATCH[:3], dtype=float)
    border = np.array(OCEAN_BORDER[:3], dtype=float)
    c = base.copy()
    # 波光圆斑 2-3 个
    circles = [((-6.0, 4.0), 5.5), ((7.0, -6.0), 4.5), ((2.0, 9.0), 3.8)]
    for (cx, cz), r in circles:
        d = np.hypot(x - cx, z - cz)
        if d < r:
            f = 1.0 - d / r
            c = c + (patch - c) * f * 0.75
    # 波光斜条 2 条
    strips = [(-0.6, 3.0, 1.6), (0.5, -5.0, 1.4)]
    for a, b0, w in strips:
        d = abs(z - (a * x + b0))
        if d < w:
            f = 1.0 - d / w
            c = c + (patch - c) * f * 0.6
    # 边框稍亮（距边缘 < 1.2m）
    edge = min(abs(x + 20), abs(20 - x), abs(z + 20), abs(20 - z))
    if edge < 1.2:
        f = 1.0 - edge / 1.2
        c = c + (border - c) * f * 0.5
    return np.clip(np.append(c, 255), 0, 255).astype(np.uint8)


def gen_ocean(seed=101):
    """40×40m 海面（1×，generate() 统一 ×20 → 800×800m）：顶面 y=0（锚点），底面 y=-0.1，含波光顶点色
    细分：顶面 n=90（(91)²≈8.3k 顶点）→ 放大后 800m 上波光斑块不糊；底面 n=45"""
    rng = gl.rng_from_seed(seed)
    parts = []
    top = _ocean_grid(n=90, size=40.0, y=0.0, color_fn=_ocean_color_fn)
    parts.append(("ocean_top", top))
    # 底面（更深蓝，法线朝 -Y）
    bottom = _ocean_grid(n=45, size=40.0, y=-0.1,
                         color_fn=lambda x, z: np.array(OCEAN_DEEP, dtype=np.uint8))
    if bottom.face_normals.mean(axis=0)[1] > 0:
        bottom.invert()
    parts.append(("ocean_bottom", bottom))
    # 四侧壁（薄墙封边）
    wall_c = np.array(OCEAN_BASE[:3] + (255,), dtype=np.uint8)
    for i, (dx, dz, ex, ez) in enumerate([
        (-20, 0, 0.05, 40.0), (20, 0, 0.05, 40.0),
        (0, -20, 40.0, 0.05), (0, 20, 40.0, 0.05),
    ]):
        w = gl.mesh(wall_c, extents=(ex, 0.1, ez), geom="box")
        w.apply_translation([dx, -0.05, dz])
        parts.append((f"ocean_wall{i}", w))
    return parts


# ================ ② 岛屿（16 个，预定义参数表） ================
# 字段：r 半径(m, 直径=2r, 1× 范围 3-10m；×SCALE=20 后 60-200m)
#      / beach 沙滩高 / grass 草地厚 / hills 山丘数 / rocks 岩石数 / palms 棕榈数
#      / hut 小屋 / dock 码头 / ry 朝向(deg) / base 基座色
# 所有 1× 尺寸在 generate() 统一 ×SCALE=20（顶点数不变）
ISLAND_TABLE = [
    # 01-08 山丘岛（8 个，从大到小；03 主岛最大直径 10m）
    dict(id=1,  r=4.0,  beach=0.30, grass=0.20, hills=2, rocks=0, palms=0, hut=False, dock=False, ry=15,  base="brown"),
    dict(id=2,  r=3.5,  beach=0.28, grass=0.18, hills=2, rocks=0, palms=0, hut=False, dock=False, ry=45,  base="brown"),
    dict(id=3,  r=5.0,  beach=0.30, grass=0.22, hills=3, rocks=0, palms=0, hut=False, dock=False, ry=0,   base="brown"),
    dict(id=4,  r=3.25, beach=0.26, grass=0.17, hills=1, rocks=0, palms=0, hut=False, dock=False, ry=90,  base="brown"),
    dict(id=5,  r=3.75, beach=0.28, grass=0.18, hills=2, rocks=0, palms=0, hut=False, dock=False, ry=200, base="brown"),
    dict(id=6,  r=3.0,  beach=0.25, grass=0.16, hills=1, rocks=0, palms=0, hut=False, dock=False, ry=120, base="brown"),
    dict(id=7,  r=2.75, beach=0.24, grass=0.15, hills=1, rocks=0, palms=0, hut=False, dock=False, ry=60,  base="brown"),
    dict(id=8,  r=2.5,  beach=0.23, grass=0.15, hills=1, rocks=0, palms=0, hut=False, dock=False, ry=300, base="brown"),
    # 09-12 岩石岛（4 个，直径 4-4.8m）
    dict(id=9,  r=2.4,  beach=0.22, grass=0.14, hills=0, rocks=2, palms=0, hut=False, dock=False, ry=10,  base="blue"),
    dict(id=10, r=2.25, beach=0.21, grass=0.13, hills=0, rocks=3, palms=0, hut=False, dock=False, ry=80,  base="blue"),
    dict(id=11, r=2.1,  beach=0.20, grass=0.13, hills=0, rocks=2, palms=0, hut=False, dock=False, ry=140, base="blue"),
    dict(id=12, r=2.0,  beach=0.20, grass=0.12, hills=0, rocks=3, palms=0, hut=False, dock=False, ry=220, base="blue"),
    # 13-14 棕榈岛（2 个）
    dict(id=13, r=1.9,  beach=0.19, grass=0.12, hills=0, rocks=0, palms=2, hut=False, dock=False, ry=30,  base="blue"),
    dict(id=14, r=1.75, beach=0.18, grass=0.12, hills=0, rocks=0, palms=2, hut=False, dock=False, ry=160, base="blue"),
    # 15-16 小屋/码头岛（2 个）
    dict(id=15, r=1.6,  beach=0.17, grass=0.11, hills=0, rocks=0, palms=0, hut=True,  dock=False, ry=0,   base="blue"),
    dict(id=16, r=1.5,  beach=0.16, grass=0.11, hills=0, rocks=0, palms=0, hut=True,  dock=True,  ry=45,  base="blue"),
]


def _gen_palm(rng, trunk_h=1.2):
    """棕榈树：竖直树干(_vcyl) + 深绿扇形冠（5 片斜叶 + 顶簇），整树 ≤1.7m"""
    parts = []
    trunk = _vcyl(_j(PALM_TRUNK, 0.04, rng), radius=0.05, height=trunk_h, sections=8)
    trunk.apply_translation([0, trunk_h / 2, 0])
    parts.append(("palm_trunk", trunk))
    for i in range(5):
        ang = i * 2 * np.pi / 5 + rng.uniform(-0.2, 0.2)
        leaf = _sphere(_j(PALM_LEAF, 0.05, rng), radius=0.34, subdiv=1, scale=[1.0, 0.16, 0.34])
        # 叶斜向伸出：绕 Y 扇形 + 绕 X 上翘
        leaf.apply_transform(_rot_y(np.degrees(ang)))
        leaf.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-35), [1, 0, 0], [0, 0, 0]))
        leaf.apply_translation([0, trunk_h + 0.22, 0])
        parts.append((f"palm_leaf{i}", leaf))
    cap = _sphere(_j(PALM_LEAF, 0.05, rng), radius=0.12, subdiv=1, scale=[1.0, 0.9, 1.0])
    cap.apply_translation([0, trunk_h + 0.4, 0])
    parts.append(("palm_cap", cap))
    return parts


def _gen_hut(rng, scale=1.0):
    """小屋：木箱身 + 斜顶 + 门"""
    parts = []
    w, d, h = 0.9 * scale, 0.8 * scale, 0.7 * scale
    body = gl.mesh(_j(HUT_WOOD, 0.04, rng), extents=(w, h, d), geom="box")
    body.apply_translation([0, h / 2, 0])
    parts.append(("hut_body", body))
    roof = trimesh.creation.cone(radius=w * 0.72, height=h * 0.5, sections=4)
    roof.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0], [0, 0, 0]))
    gl._ensure_normals(roof)
    roof.visual = trimesh.visual.ColorVisuals(roof, vertex_colors=_j(HUT_ROOF, 0.04, rng))
    roof.apply_translation([0, h, 0])
    parts.append(("hut_roof", roof))
    door = gl.mesh((0x4A, 0x33, 0x22, 255), extents=(0.24 * scale, 0.34 * scale, 0.03), geom="box")
    door.apply_translation([0, 0.2 * scale, d / 2 + 0.015])
    parts.append(("hut_door", door))
    return parts


def _gen_dock(rng, length=1.4):
    """小码头：木板 + 立柱"""
    parts = []
    for i in range(4):
        plank = gl.mesh(_j(DOCK_WOOD, 0.04, rng), extents=(0.7, 0.06, 0.16), geom="box")
        plank.apply_translation([0, 0.08, -length / 2 + i * length / 3])
        parts.append((f"dock_plank{i}", plank))
    for i, (sx, sz) in enumerate([(-0.25, -0.4), (0.25, -0.4), (-0.25, 0.4), (0.25, 0.4)]):
        post = _vcyl(_j(DOCK_WOOD, 0.04, rng), radius=0.035, height=0.3, sections=6)
        post.apply_translation([sx, 0.0, sz])
        parts.append((f"dock_post{i}", post))
    return parts


def gen_island(idx, table=None):
    """自下而上：水下基座(0.3m) → 沙滩环(露出水面) → 草地顶(浅帽) → 可选山丘/岩石/棕榈/小屋码头"""
    if table is None:
        table = ISLAND_TABLE
    p = table[idx - 1]
    rng = gl.rng_from_seed(2000 + idx * 7)
    r, beach_h, grass_h = p["r"], p["beach"], p["grass"]
    base_h = 0.3
    parts = []

    # ① 水下基座（0 → 0.3m）
    base_c = ISLAND_BASE_BLUE if p["base"] == "blue" else ISLAND_BASE
    base = _frustum(_j(base_c, 0.03, rng), r_bot=r * 0.9, r_top=r, height=base_h, y0=0.0, sections=20)
    parts.append(("island_base", base))

    # ② 沙滩环（0.3 → 0.3+beach_h，米黄，露出水面）
    sand = _frustum(_j(ISLAND_SAND, 0.03, rng), r_bot=r, r_top=r * 0.72, height=beach_h, y0=base_h, sections=20)
    parts.append(("island_sand", sand))

    # ③ 草地顶（圆柱台 + 浅穹帽，总厚 grass_h）
    grass_top = base_h + beach_h
    grass_r = r * 0.55
    grass_base = _vcyl(_j(ISLAND_GRASS, 0.03, rng), radius=grass_r, height=grass_h * 0.55, sections=16)
    grass_base.apply_translation([0, grass_top + grass_h * 0.275, 0])
    parts.append(("island_grass_base", grass_base))
    dome_h = grass_h * 0.45
    dome = _sphere(_j(ISLAND_GRASS, 0.03, rng), radius=grass_r, subdiv=2, scale=[1.0, dome_h / (2 * grass_r), 1.0])
    dome.apply_translation([0, grass_top + grass_h * 0.55 + dome_h / 2, 0])
    parts.append(("island_grass_dome", dome))
    # 草地顶面 y（山丘/棕榈/小屋落点基准）
    grass_surface = grass_top + grass_h

    # ④ 山丘（草绿圆丘，高 0.5-1.5m）
    for i in range(p["hills"]):
        h = rng.uniform(0.5, min(1.5, r * 0.32))
        ang = rng.uniform(0, 2 * np.pi)
        dist = rng.uniform(0, grass_r * 0.45)
        hill = _sphere(_j(ISLAND_HILL, 0.04, rng), radius=h * 0.55, subdiv=2, scale=[1.0, 0.95, 1.0])
        hill.apply_translation([dist * np.cos(ang), grass_surface + h * 0.28, dist * np.sin(ang)])
        parts.append((f"hill{i}", hill))

    # ⑤ 岩石（灰，2-3 块）
    for i in range(p["rocks"]):
        rr = rng.uniform(0.14, 0.3)
        ang = rng.uniform(0, 2 * np.pi)
        dist = rng.uniform(r * 0.3, r * 0.68)
        rock = _sphere(_j(ISLAND_ROCK, 0.04, rng), radius=rr, subdiv=1,
                       scale=[rng.uniform(0.8, 1.3), rng.uniform(0.6, 0.9), rng.uniform(0.8, 1.3)])
        rock.apply_translation([dist * np.cos(ang), base_h + beach_h * 0.4, dist * np.sin(ang)])
        parts.append((f"rock{i}", rock))

    # ⑥ 棕榈树
    for i in range(p["palms"]):
        ang = rng.uniform(0, 2 * np.pi)
        dist = rng.uniform(0, grass_r * 0.5)
        trunk_h = rng.uniform(0.9, 1.2)
        palm = _gen_palm(rng, trunk_h=trunk_h)
        for nm, m in palm:
            m.apply_translation([dist * np.cos(ang), grass_surface, dist * np.sin(ang)])
            parts.append((nm, m))

    # ⑦ 小屋 / 码头
    if p["hut"]:
        hut = _gen_hut(rng, scale=0.8)
        for nm, m in hut:
            m.apply_translation([grass_r * 0.25, grass_surface, 0])
            parts.append((nm, m))
    if p["dock"]:
        dock = _gen_dock(rng, length=1.4)
        for nm, m in dock:
            m.apply_transform(_rot_y(p["ry"]))
            m.apply_translation([0, base_h + beach_h * 0.35, r * 0.85])
            parts.append((nm, m))

    # 整体朝向（绕 Y）
    if p["ry"]:
        for _, m in parts:
            m.apply_transform(_rot_y(p["ry"]))
    return _normalize_parts(parts)


# ================ ③ 矿藏资源（3 种矿 × 3 档 = 9） ================

def _gen_ore_scatter(rng, kind, count, r_min, r_max, spread, y0=0.0, stack=0.0):
    """在 spread 半径内撒 count 块不规则矿石，返回 parts（矿体+碎屑）"""
    parts = []
    colors = ORE_COLORS[kind]
    for i in range(count):
        r = rng.uniform(r_min, r_max)
        ang = rng.uniform(0, 2 * np.pi)
        dist = rng.uniform(0, spread)
        col = _j(colors["body"] if rng.random() < 0.7 else colors["hi"], 0.05, rng)
        chunk = _ore_chunk(col, rng, radius=r)
        layer = i // max(1, int(count * 0.4))  # 堆叠分层
        chunk.apply_translation([dist * np.cos(ang), y0 + r * 0.6 + stack * layer, dist * np.sin(ang)])
        parts.append((f"ore{i}", chunk))
    return parts


def _gen_fence_seg(rng, cx, cz, ry=0.0):
    """木围栏一段：2 立柱 + 1 横杆（总宽 ≤0.5m，控制占地）"""
    parts = []
    c = _j((0xA0, 0x7B, 0x4F, 255), 0.04, rng)
    for sx in (-0.12, 0.12):
        post = _vcyl(c, radius=0.02, height=0.3, sections=6)
        post.apply_translation([sx, 0.15, 0])
        parts.append((f"fpost{cx:.2f}{sx}", post))
    rail = gl.mesh(_j((0xA0, 0x7B, 0x4F, 255), 0.04, rng), extents=(0.24, 0.025, 0.025), geom="box")
    rail.apply_translation([0, 0.2, 0])
    parts.append((f"frail{cx:.2f}", rail))
    for _, m in parts:
        m.apply_transform(_rot_y(ry))
        m.apply_translation([cx, 0, cz])
    return parts


def _gen_cart(rng, scale=1.0):
    """小矿石车：木箱 + 2 轮（轮轴沿 Z，可滚动视觉）"""
    parts = []
    body = gl.mesh(_j((0x8D, 0x6E, 0x63, 255), 0.04, rng), extents=(0.4 * scale, 0.22 * scale, 0.3 * scale), geom="box")
    body.apply_translation([0, 0.14 * scale, 0])
    parts.append(("cart_body", body))
    for sx in (-1, 1):
        wheel = gl.mesh((0x3A, 0x3A, 0x3A, 255), radius=0.09 * scale, height=0.05, sections=10, geom="cylinder")
        # 轮轴沿 Z：圆柱默认沿 Z，直接保留（轮面朝 X）
        wheel.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90), [1, 0, 0], [0, 0, 0]))
        wheel.apply_translation([sx * 0.23 * scale, 0.09 * scale, 0])
        parts.append((f"cart_wheel{sx}", wheel))
    return parts


def _gen_mine_arch(rng, width=1.3, height=1.15):
    """矿洞入口：拱形木门框（双柱 + 半圆拱段）+ 洞内暗色"""
    parts = []
    wood_c = _j((0xA0, 0x7B, 0x4F, 255), 0.04, rng)
    # 双柱
    for sx in (-1, 1):
        post = gl.mesh(wood_c, extents=(0.12, height, 0.12), geom="box")
        post.apply_translation([sx * width / 2, height / 2, 0])
        parts.append((f"arch_post{sx}", post))
    # 半圆拱段（7 段）
    r = width / 2
    n = 7
    for i in range(1, n):
        a = np.pi * i / n
        seg = gl.mesh(wood_c, extents=(0.12, 0.12, 0.12), geom="box")
        seg.apply_transform(_rot_z(90 + np.degrees(a)))
        seg.apply_translation([r * np.cos(a), height + r * np.sin(a), 0])
        parts.append((f"arch_seg{i}", seg))
    # 洞内暗色（半圆暗盘）
    dark = gl.mesh((0x2A, 0x2A, 0x28, 255), extents=(width * 0.92, height * 0.9, 0.06), geom="box")
    dark.apply_translation([0, height * 0.5, -0.05])
    parts.append(("arch_dark", dark))
    return parts


def gen_ore_small(kind, seed=301):
    """小型矿脉：3-5 块裸露矿石(0.06-0.12m) + 碎屑，占地 ≤0.4×0.4m，高 ≤0.25m"""
    rng = gl.rng_from_seed(seed)
    parts = []
    # 底座碎石薄片（0.40×0.40）
    base = _sphere(_j((0x8D, 0x6E, 0x63, 255), 0.05, rng), radius=0.20, subdiv=1, scale=[1.0, 0.14, 1.0])
    base.apply_translation([0, 0.015, 0])
    parts.append(("ore_base", base))
    # 3-5 块（高 0.05-0.10，中心贴地，顶部 ≤0.25）
    parts += _gen_ore_scatter(rng, kind, rng.integers(3, 6), 0.05, 0.10, 0.07, y0=0.015, stack=0.02)
    # 碎屑
    for i in range(4):
        r = rng.uniform(0.015, 0.035)
        ang = rng.uniform(0, 2 * np.pi)
        dist = rng.uniform(0.04, 0.16)
        col = _j(ORE_COLORS[kind]["hi"], 0.05, rng)
        debris = _ore_chunk(col, rng, radius=r)
        debris.apply_translation([dist * np.cos(ang), r * 0.5, dist * np.sin(ang)])
        parts.append((f"debris{i}", debris))
    return _normalize_parts(parts)


def gen_ore_medium(kind, seed=311):
    """中型矿堆：7-10 块矿堆 + 2 木支架斜撑 + 2 木围栏 + 小矿车，占地 ≤1.0×1.0m，高 0.6-0.9m"""
    rng = gl.rng_from_seed(seed)
    parts = []
    # 地台 1.0×1.0
    base = gl.mesh(_j((0x8D, 0x6E, 0x63, 255), 0.04, rng), extents=(1.0, 0.05, 1.0), geom="box")
    base.apply_translation([0, 0.025, 0])
    parts.append(("ore_base", base))
    # 矿堆（中心 0.3×0.3m 内，顶部 ≤0.85，控制总高 ≤0.9）
    parts += _gen_ore_scatter(rng, kind, rng.integers(7, 11), 0.09, 0.15, 0.13, y0=0.05, stack=0.08)
    # 2 木支架斜撑（_vcyl 0.8m 棕，斜靠矿堆，整体占地 ≤1.0×1.0m）
    wood_c = _j((0xA0, 0x7B, 0x4F, 255), 0.04, rng)
    for i in range(2):
        ang = i * np.pi + rng.uniform(-0.25, 0.25)
        strut = _vcyl(wood_c, radius=0.03, height=0.8, sections=8)
        strut.apply_transform(_rot_z(16))
        strut.apply_transform(_rot_y(np.degrees(ang)))
        strut.apply_translation([0.34 * np.cos(ang), 0.05, 0.34 * np.sin(ang)])
        parts.append((f"strut{i}", strut))
    # 2 木围栏段（贴地台边缘，整体 ≤1.0×1.0m）
    parts += _gen_fence_seg(rng, -0.36, 0.18, ry=0)
    parts += _gen_fence_seg(rng, 0.36, -0.18, ry=180)
    # 小矿车（可选，本实现包含；靠地台一角）
    cart = _gen_cart(rng, scale=0.6)
    for nm, m in cart:
        m.apply_translation([0.28, 0.05, 0.26])
        parts.append((nm, m))
    return _normalize_parts(parts)


def gen_ore_large(kind, seed=321):
    """大型矿场：矿洞入口 + 大矿堆(15+) + 矿车(带轮) + 木塔架 + 照明灯，占地 2.0×2.0m，高 1.5-2.2m"""
    rng = gl.rng_from_seed(seed)
    parts = []
    # 地台
    base = gl.mesh(_j((0x8D, 0x6E, 0x63, 255), 0.04, rng), extents=(2.0, 0.06, 2.0), geom="box")
    base.apply_translation([0, 0.03, 0])
    parts.append(("ore_base", base))

    # 矿洞入口（靠后）
    arch = _gen_mine_arch(rng, width=1.1, height=1.15)
    for nm, m in arch:
        m.apply_translation([0, 0.06, -0.7])
        parts.append((nm, m))

    # 大矿堆（入口前，15+ 块）
    parts += _gen_ore_scatter(rng, kind, 16, 0.1, 0.22, 0.55, y0=0.06, stack=0.16)

    # 矿车（带轮，入口侧）
    cart = _gen_cart(rng, scale=0.85)
    for nm, m in cart:
        m.apply_translation([0.7, 0.06, 0.35])
        parts.append((nm, m))

    # 木塔架（4 柱 + 平台 + 顶梁）
    tower_c = _j((0xA0, 0x7B, 0x4F, 255), 0.04, rng)
    th = 1.7
    for i, (sx, sz) in enumerate([(-0.45, -0.45), (0.45, -0.45), (-0.45, 0.45), (0.45, 0.45)]):
        post = _vcyl(tower_c, radius=0.045, height=th, sections=8)
        post.apply_translation([sx, 0.06 + th / 2, sz - 0.3])
        parts.append((f"tower_post{i}", post))
    plat = gl.mesh(_j((0x8D, 0x6E, 0x63, 255), 0.04, rng), extents=(1.1, 0.08, 1.1), geom="box")
    plat.apply_translation([0, 0.06 + th, -0.3])
    parts.append(("tower_platform", plat))
    beam = _vcyl(tower_c, radius=0.03, height=1.0, sections=6)
    beam.apply_transform(_rot_z(90))
    beam.apply_translation([0, 0.06 + th + 0.35, -0.3])
    parts.append(("tower_beam", beam))

    # 照明灯（黄点 0xFFE066，2 盏）
    for i, (lx, lz) in enumerate([(-0.85, -0.3), (0.85, -0.3)]):
        lamp_pole = _vcyl((0x5A, 0x4A, 0x38, 255), radius=0.02, height=0.7, sections=6)
        lamp_pole.apply_translation([lx, 0.06 + 0.35, lz])
        parts.append((f"lamp_pole{i}", lamp_pole))
        lamp = _sphere((0xFF, 0xE0, 0x66, 255), radius=0.05, subdiv=1)
        lamp.apply_translation([lx, 0.06 + 0.72, lz])
        parts.append((f"lamp{i}", lamp))

    return _normalize_parts(parts)


# ================ 生成 / 验证 / manifest ================

def all_assets():
    """返回 [(asset_id, 相对路径, 生成函数, category, designId, name, desc, collision)]
    描述/碰撞均按 ×SCALE=20 后的实际世界尺寸标注"""
    items = []
    items.append(("terrain_ocean", "terrain/terrain_ocean.glb", gen_ocean, "terrain", "MAP-01",
                  "海洋水面", "800×800m 海面 + 波光斑块（顶面≈8.3k 顶点）",
                  {"type": "fixed", "shape": "box", "params": {"hx": 20 * SCALE, "hy": 1.0, "hz": 20 * SCALE}}))
    for idx in range(1, 17):
        p = ISLAND_TABLE[idx - 1]
        items.append((f"terrain_island_{idx:02d}", f"terrain/terrain_island_{idx:02d}.glb",
                      lambda i=idx: gen_island(i), "terrain", f"MAP-{idx + 1:02d}",
                      f"岛屿-{idx:02d}", f"岛屿 直径{2 * p['r'] * SCALE:.0f}m 沙滩{p['beach'] * SCALE:.0f}m",
                      {"type": "fixed", "shape": "box",
                       "params": {"hx": p["r"] * SCALE, "hy": 25.0, "hz": p["r"] * SCALE}}))
    ore_ids = []
    for kind in ("copper", "silver", "gold"):
        for tier in ("small", "medium", "large"):
            ore_ids.append((kind, tier))
    for i, (kind, tier) in enumerate(ore_ids, start=1):
        fn = {"small": gen_ore_small, "medium": gen_ore_medium, "large": gen_ore_large}[tier]
        size = {"small": 0.4, "medium": 1.0, "large": 2.0}[tier] * SCALE
        hgt = {"small": 0.25, "medium": 0.9, "large": 2.2}[tier] * SCALE
        items.append((f"ore_{kind}_{tier}", f"props/ore_{kind}_{tier}.glb",
                      lambda k=kind, t=tier: {"small": gen_ore_small, "medium": gen_ore_medium, "large": gen_ore_large}[t](k),
                      "prop", f"ORE-{i:02d}",
                      f"{ORE_NAMES[kind]}-{TIER_NAMES[tier]}", f"{ORE_NAMES[kind]} {TIER_NAMES[tier]}矿藏 {size:.0f}m",
                      {"type": "fixed", "shape": "box", "params": {"hx": size / 2, "hy": hgt / 2, "hz": size / 2}}))
    return items


def verify_glb(path):
    """验证 GLB：trimesh 加载 OK + JSON chunk 含 POSITION/NORMAL/COLOR_0 + min_y=0"""
    try:
        scene = trimesh.load(path)
        if scene is None:
            return False, "load None"
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
        return all(found.values()), found
    except Exception as e:
        return False, str(e)


def bounds_of(path):
    scene = trimesh.load(path)
    geoms = list(scene.geometry.values()) if hasattr(scene, "geometry") and scene.geometry else [scene]
    lo = np.min([g.bounds[0] for g in geoms], axis=0)
    hi = np.max([g.bounds[1] for g in geoms], axis=0)
    return lo, hi


def generate(assets_dir=None, verify=True):
    """生成 26 个 GLB（1 海面 + 16 岛 + 9 矿）并验证；所有几何统一 ×SCALE=20（坐标缩放，顶点数不变）"""
    if assets_dir is None:
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(BASE)), "assets")
    os.makedirs(os.path.join(assets_dir, "terrain"), exist_ok=True)
    os.makedirs(os.path.join(assets_dir, "props"), exist_ok=True)
    results = {}
    for aid, rel, fn, cat, did, name, desc, col in all_assets():
        parts = fn()
        _scale_parts(parts, SCALE)  # ← 全局 ×20（海面细分已在 gen_ocean 内加密度）
        path = os.path.join(assets_dir, rel)
        gl.export_scene(parts, path)
        size_kb = os.path.getsize(path) / 1024
        ok, found = verify_glb(path) if verify else (None, None)
        lo, hi = bounds_of(path)
        results[aid] = {"path": path, "rel": rel, "sizeKB": round(size_kb, 1),
                        "verify": ok, "found": found, "bounds": (lo.tolist(), hi.tolist())}
    return results


# ================ manifest 更新 ================

def _entry_json(aid, rel, did, name, desc, collision, size_kb):
    return {
        "assetId": aid,
        "designId": did,
        "path": rel,
        "category": "terrain" if rel.startswith("terrain") else "prop",
        "priority": "P1",
        "name": name,
        "desc": desc,
        "source": "procedural",
        "collision": collision,
        "animations": [],
        "lodLevels": [{"level": 0, "path": rel}],
        "sizeKB": size_kb,
        "loadPriority": 0,
    }


def update_manifest_json(assets_dir, results):
    """向 assets/manifest.json 写入 26 条（按 assetId upsert，幂等且随几何变化同步）"""
    path = os.path.join(assets_dir, "manifest.json")
    with open(path, encoding="utf-8") as f:
        manifest = _json.load(f)
    by_id = {a["assetId"]: a for a in manifest["assets"]}
    added = 0
    for aid, rel, fn, cat, did, name, desc, col in all_assets():
        entry = _entry_json(aid, rel, did, name, desc, col, results[aid]["sizeKB"])
        if aid in by_id:
            by_id[aid].update(entry)  # 同步几何/尺寸变化
        else:
            manifest["assets"].append(entry)
            added += 1
    with open(path, "w", encoding="utf-8") as f:
        _json.dump(manifest, f, ensure_ascii=False, indent=2)
    return added


def update_preview_html(root, results):
    """用 re 精准替换 preview.html 内嵌 manifest（<script id=manifest-data>）的 assets 数组，不动 LAYOUT"""
    path = os.path.join(root, "preview.html")
    with open(path, encoding="utf-8") as f:
        html = f.read()
    m = _re_search_manifest(html)
    if not m:
        raise RuntimeError("manifest-data script block not found")
    data = _json.loads(m.group(1))
    by_id = {a["assetId"]: a for a in data["assets"]}
    added = 0
    for aid, rel, fn, cat, did, name, desc, col in all_assets():
        entry = {
            "assetId": aid,
            "designId": did,
            "path": "assets/" + rel,
            "category": cat,
            "priority": "P1",
            "name": name,
            "desc": desc,
            "source": "procedural",
        }
        if aid in by_id:
            by_id[aid].update(entry)
        else:
            data["assets"].append(entry)
            added += 1
    new_json = _json.dumps(data, ensure_ascii=False, indent=2)
    html = html[:m.start(1)] + new_json + html[m.end(1):]
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return added


def _re_search_manifest(html):
    import re
    return re.search(r'<script id="manifest-data" type="application/json">(.*?)</script>', html, re.S)


def main():
    root = os.path.dirname(os.path.dirname(BASE))
    assets_dir = os.path.join(root, "assets")
    print("== 生成 26 GLB ==")
    results = generate(assets_dir, verify=True)
    fail = [aid for aid, r in results.items() if not r.get("verify")]
    for aid, r in results.items():
        mark = "OK" if r.get("verify") else "FAIL"
        lo, hi = r["bounds"]
        print(f"  [{mark}] {aid:28s} {r['sizeKB']:7.1f}KB  bounds=({lo[0]:.2f},{lo[1]:.2f},{lo[2]:.2f})~({hi[0]:.2f},{hi[1]:.2f},{hi[2]:.2f})")
    print(f"\n== 验证 ==  {len(results) - len(fail)}/{len(results)} 通过")
    if fail:
        print("  失败:", fail)

    print("\n== 更新 manifest.json ==")
    n1 = update_manifest_json(assets_dir, results)
    print(f"  新增 {n1} 条（按 assetId upsert，已有 26 条同步更新）")
    print("\n== 更新 preview.html 内嵌 manifest ==")
    n2 = update_preview_html(root, results)
    print(f"  新增 {n2} 条（按 assetId upsert，LAYOUT 未动）")
    return results


if __name__ == "__main__":
    main()
