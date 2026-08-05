# -*- coding: utf-8 -*-
"""道具/建筑/环境生成器：蛋/奶/饲料/工具/出货箱/围栏/农舍/鸡舍/牛棚/水井/石头"""
import numpy as np
import trimesh
import gen_lib as gl


# ---------------- 道具 ----------------
def gen_egg(seed=1):
    """鸡蛋：椭球"""
    egg = gl.mesh(gl.C("cream"), radius=0.035, sections=8, geom="sphere")
    egg.apply_scale([0.8, 1.1, 0.8])
    egg.apply_translation([0, 0.035, 0])
    return [("egg", egg)]


def gen_milk(seed=1):
    """牛奶瓶：瓶体 + 盖"""
    bottle = gl.mesh(gl.C("cream"), radius=0.04, height=0.14, sections=8, geom="cylinder")
    bottle.apply_translation([0, 0.07, 0])
    cap = gl.mesh(gl.C("blueberry"), radius=0.045, height=0.03, sections=8, geom="cylinder")
    cap.apply_translation([0, 0.16, 0])
    return [("bottle", bottle), ("cap", cap)]


def gen_feed(seed=1):
    """饲料/干草捆"""
    hay = gl.mesh(gl.jitter(gl.C("wheat"), 0.04, seed and np.random.default_rng(seed)),
                  radius=0.16, height=0.3, sections=8, geom="cylinder")
    hay.apply_translation([0, 0.15, 0])
    hay.apply_scale([1.0, 1.0, 0.8])
    return [("hay", hay)]


def gen_basket(seed=1):
    """篮子：编织篮"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("wood"), 0.03, rng)
    base = gl.mesh(c, radius=0.12, height=0.1, sections=10, geom="cylinder")
    base.apply_translation([0, 0.05, 0])
    rim = gl.mesh(c, radius=0.13, height=0.02, sections=10, geom="cylinder")
    rim.apply_translation([0, 0.11, 0])
    return [("base", base), ("rim", rim)]


def gen_hoe(seed=1):
    """锄头：木柄 + 金属头"""
    rng = gl.rng_from_seed(seed)
    handle = gl.mesh(gl.jitter(gl.C("wood"), 0.03, rng), radius=0.015, height=0.7, sections=6, geom="cylinder")
    handle.apply_translation([0, 0.35, 0])
    blade = gl.mesh(gl.C("stone"), extents=(0.16, 0.05, 0.02), geom="box")
    blade.apply_translation([0, 0.72, 0])
    return [("handle", handle), ("blade", blade)]


def gen_watering_can(seed=1):
    """水壶"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("blueberry"), 0.03, rng)
    body = gl.mesh(c, radius=0.08, height=0.16, sections=10, geom="cylinder")
    body.apply_translation([0, 0.08, 0])
    spout = gl.mesh(c, extents=(0.04, 0.04, 0.15), geom="box")
    spout.apply_translation([0, 0.16, 0.12])
    handle = gl.mesh(c, extents=(0.03, 0.12, 0.03), geom="box")
    handle.apply_translation([0, 0.14, -0.09])
    return [("body", body), ("spout", spout), ("handle", handle)]


def gen_fishing_rod(seed=1):
    """鱼竿：细杆 + 线轴"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("wood"), 0.03, rng)
    rod = gl.mesh(c, radius=0.012, height=1.2, sections=6, geom="cylinder")
    rod.apply_translation([0, 0.6, 0])
    reel = gl.mesh(gl.C("stone"), radius=0.04, height=0.02, sections=8, geom="cylinder")
    reel.apply_translation([0, 0.35, 0.01])
    return [("rod", rod), ("reel", reel)]


def gen_scythe(seed=1):
    """镰刀：木柄 + 弯刃（简化）"""
    rng = gl.rng_from_seed(seed)
    handle = gl.mesh(gl.jitter(gl.C("wood"), 0.03, rng), radius=0.015, height=0.5, sections=6, geom="cylinder")
    handle.apply_translation([0, 0.25, 0])
    blade = gl.mesh(gl.C("stone"), extents=(0.04, 0.18, 0.02), geom="box")
    blade.apply_translation([0, 0.55, 0])
    blade.apply_transform(trimesh.transformations.rotation_matrix(np.radians(30), [1, 0, 0], [0, 0, 0]))
    return [("handle", handle), ("blade", blade)]


def gen_shipping_box(seed=1):
    """出货箱：木箱 + 盖子"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("wood"), 0.03, rng)
    box = gl.mesh(c, extents=(0.5, 0.35, 0.5), geom="box")
    box.apply_translation([0, 0.175, 0])
    lid = gl.mesh(gl.jitter(gl.C("wood_dark"), 0.03, rng), extents=(0.54, 0.05, 0.54), geom="box")
    lid.apply_translation([0, 0.375, 0])
    return [("box", box), ("lid", lid)]


def gen_fence_segment(seed=1):
    """围栏直段：2 横杆 + 3 立柱"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("wood"), 0.03, rng)
    parts = []
    for i in range(3):
        post = gl.mesh(c, radius=0.03, height=0.9, sections=6, geom="cylinder")
        post.apply_translation([-0.45 + i * 0.45, 0.45, 0])
        parts.append((f"post{i}", post))
    for y in (0.25, 0.6):
        rail = gl.mesh(c, extents=(1.0, 0.05, 0.05), geom="box")
        rail.apply_translation([0, y, 0])
        parts.append((f"rail_{int(y*100)}", rail))
    return parts


# ---------------- 建筑（v2 精细版：瓦顶/门框窗框/烟囱/地基/室内地板/可开关门） ----------------

def _wall_with_openings(wall_c, length, height, thickness, openings, y_base=0.0):
    """带开口的墙体（开口用黑色块模拟镂空感，视觉通透）"""
    parts = []
    wall = gl.mesh(wall_c, extents=(length, height, thickness), geom="box")
    wall.apply_translation([0, height / 2 + y_base, 0])
    parts.append(("wall", wall))
    for i, (cx, cy, w, h) in enumerate(openings):
        hole = gl.mesh(gl.C("black"), extents=(w + 0.02, h + 0.02, thickness + 0.03), geom="box")
        hole.apply_translation([cx, cy + y_base, 0])
        parts.append((f"opening{i}", hole))
    return parts


def _make_door(width=0.5, height=0.9, thickness=0.04, color="wood_dark", handle_side=1):
    """
    可开关门组：门板+把手，铰链轴在 x=0（门左缘），运行时绕 Y 轴旋转即开合。
    门板锚点=铰链位置（底部中心），命名 door_panel / door_handle 供运行时识别。
    """
    rng = np.random.default_rng(1)
    parts = []
    panel = gl.mesh(gl.jitter(gl.C(color), 0.02, rng), extents=(width, height, thickness), geom="box")
    panel.apply_translation([width / 2, height / 2, 0])  # 左缘贴铰链
    parts.append(("door_panel", panel))
    handle = gl.mesh(gl.C("gold"), radius=0.015, height=0.06, sections=6, geom="cylinder")
    handle.apply_translation([width * handle_side, height * 0.5, thickness / 2 + 0.012])
    parts.append(("door_handle", handle))
    return parts


def gen_farmhouse(seed=1):
    """农舍 v2：地基+墙体+门框窗框+玻璃+瓦顶+烟囱+室内地板+可开关门"""
    rng = gl.rng_from_seed(seed)
    wall_c = gl.jitter(gl.C("cream"), 0.02, rng)
    roof_c = gl.jitter(gl.C("roof"), 0.03, rng)
    wood_c = gl.jitter(gl.C("wood"), 0.03, rng)
    wood_dark_c = gl.jitter(gl.C("wood_dark"), 0.03, rng)
    stone_c = gl.jitter(gl.C("stone"), 0.03, rng)

    W, D, H = 2.6, 2.0, 1.5
    wall_t = 0.1
    parts = []
    # 地基（石基）
    foundation = gl.mesh(stone_c, extents=(W + 0.3, 0.12, D + 0.3), geom="box")
    foundation.apply_translation([0, 0.06, 0])
    parts.append(("foundation", foundation))
    # 前墙（门洞 + 2 窗）
    front = _wall_with_openings(wall_c, W, H, wall_t, [(0, 0.42, 0.5, 0.85), (-0.8, 0.85, 0.35, 0.35), (0.8, 0.85, 0.35, 0.35)], y_base=wall_t)
    for name, m in front:
        m.apply_translation([0, 0, D / 2])
        parts.append((name, m))
    # 后墙（2 窗）
    back = _wall_with_openings(wall_c, W, H, wall_t, [(-0.6, 0.85, 0.3, 0.3), (0.6, 0.85, 0.3, 0.3)], y_base=wall_t)
    for name, m in back:
        m.apply_translation([0, 0, -D / 2])
        parts.append((name, m))
    # 左右墙（各 1 窗）
    for sx, rot in ((1, 90), (-1, -90)):
        side = _wall_with_openings(wall_c, D, H, wall_t, [(0, 0.85, 0.35, 0.35)], y_base=wall_t)
        for name, m in side:
            m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
            m.apply_translation([sx * W / 2, 0, 0])
            parts.append((name, m))
    # 门框（立柱+楣）+ 窗框 + 玻璃
    for sx in (-0.28, 0.28):
        jamb = gl.mesh(wood_dark_c, extents=(0.05, 0.85, 0.06), geom="box")
        jamb.apply_translation([sx, wall_t + 0.42, D / 2])
        parts.append((f"jamb_{'l' if sx<0 else 'r'}", jamb))
    lintel = gl.mesh(wood_dark_c, extents=(0.6, 0.06, 0.06), geom="box")
    lintel.apply_translation([0, wall_t + 0.87, D / 2])
    parts.append(("lintel", lintel))
    for wx, wy in ((-0.8, 0.85), (0.8, 0.85)):
        frame = gl.mesh(wood_c, extents=(0.4, 0.4, 0.05), geom="box")
        frame.apply_translation([wx, wall_t + wy, D / 2])
        parts.append((f"frame_{wx}", frame))
        glass = gl.mesh(gl.C("sky"), extents=(0.3, 0.3, 0.02), geom="box")
        glass.apply_translation([wx, wall_t + wy, D / 2])
        parts.append((f"glass_{wx}", glass))
    # 可开关门（铰链左缘，门洞中心 x=0 → 左缘 x=-0.25）
    door_parts = _make_door(width=0.5, height=0.85, thickness=0.04, color="wood_dark")
    for name, m in door_parts:
        m.apply_translation([-0.25, wall_t, D / 2])
        parts.append((name, m))
    # 室内地板
    floor = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(W - 0.05, 0.04, D - 0.05), geom="box")
    floor.apply_translation([0, wall_t, 0])
    parts.append(("floor", floor))
    # 屋顶（双坡 + 屋脊 + 瓦楞条）
    for sx in (-1, 1):
        slope = gl.mesh(roof_c, extents=(W + 0.4, 0.08, 1.35), geom="box")
        slope.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-28 * sx), [1, 0, 0], [0, 0, 0]))
        slope.apply_translation([0, H + wall_t + 0.3, sx * (D / 2 - 0.35)])
        parts.append((f"roof_{sx}", slope))
    ridge = gl.mesh(roof_c, extents=(W + 0.45, 0.1, 0.1), geom="box")
    ridge.apply_translation([0, H + wall_t + 0.42, 0])
    parts.append(("ridge", ridge))
    for i, zoff in enumerate((-0.55, 0.0, 0.55)):
        tile = gl.mesh(gl.jitter(gl.C("roof"), 0.04, rng), extents=(W + 0.35, 0.03, 0.9), geom="box")
        tile.apply_transform(trimesh.transformations.rotation_matrix(np.radians(28), [1, 0, 0], [0, 0, 0]))
        tile.apply_translation([0, H + wall_t + 0.05, zoff])
        parts.append((f"tile{i}", tile))
    # 烟囱 + 盖
    chimney = gl.mesh(stone_c, extents=(0.22, 0.6, 0.22), geom="box")
    chimney.apply_translation([0.75, H + wall_t + 0.45, -0.55])
    parts.append(("chimney", chimney))
    cap = gl.mesh(gl.C("stone"), extents=(0.3, 0.06, 0.3), geom="box")
    cap.apply_translation([0.75, H + wall_t + 0.78, -0.55])
    parts.append(("chimney_cap", cap))
    # 屋檐横梁
    for zs in (D / 2, -D / 2):
        beam = gl.mesh(wood_dark_c, extents=(W + 0.4, 0.06, 0.06), geom="box")
        beam.apply_translation([0, H + wall_t - 0.05, zs])
        parts.append((f"eave_{zs}", beam))
    return parts


def gen_coop(seed=1):
    """鸡舍 v2：地基+墙体+瓦顶+门+室内地板"""
    rng = gl.rng_from_seed(seed)
    wall_c = gl.jitter(gl.C("wood"), 0.03, rng)
    roof_c = gl.jitter(gl.C("roof"), 0.03, rng)
    wood_dark_c = gl.jitter(gl.C("wood_dark"), 0.03, rng)
    W, D, H = 1.7, 1.4, 1.0
    wall_t = 0.08
    parts = []
    foundation = gl.mesh(gl.C("stone"), extents=(W + 0.2, 0.1, D + 0.2), geom="box")
    foundation.apply_translation([0, 0.05, 0])
    parts.append(("foundation", foundation))
    front = _wall_with_openings(wall_c, W, H, wall_t, [(0, 0.32, 0.4, 0.6)], y_base=wall_t)
    for name, m in front:
        m.apply_translation([0, 0, D / 2])
        parts.append((name, m))
    back = _wall_with_openings(wall_c, W, H, wall_t, [], y_base=wall_t)
    for name, m in back:
        m.apply_translation([0, 0, -D / 2])
        parts.append((name, m))
    for sx, rot in ((1, 90), (-1, -90)):
        side = _wall_with_openings(wall_c, D, H, wall_t, [], y_base=wall_t)
        for name, m in side:
            m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
            m.apply_translation([sx * W / 2, 0, 0])
            parts.append((name, m))
    door_parts = _make_door(width=0.4, height=0.6, thickness=0.03, color="wood_dark")
    for name, m in door_parts:
        m.apply_translation([-0.2, wall_t, D / 2])
        parts.append((name, m))
    floor = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(W - 0.04, 0.04, D - 0.04), geom="box")
    floor.apply_translation([0, wall_t, 0])
    parts.append(("floor", floor))
    for sx in (-1, 1):
        slope = gl.mesh(roof_c, extents=(W + 0.3, 0.07, 0.85), geom="box")
        slope.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-30 * sx), [1, 0, 0], [0, 0, 0]))
        slope.apply_translation([0, H + wall_t + 0.25, sx * (D / 2 - 0.3)])
        parts.append((f"roof_{sx}", slope))
    ridge = gl.mesh(roof_c, extents=(W + 0.35, 0.08, 0.08), geom="box")
    ridge.apply_translation([0, H + wall_t + 0.35, 0])
    parts.append(("ridge", ridge))
    chimney = gl.mesh(gl.C("stone"), extents=(0.12, 0.3, 0.12), geom="box")
    chimney.apply_translation([0.5, H + wall_t + 0.3, -0.35])
    parts.append(("chimney", chimney))
    return parts


def gen_barn(seed=1):
    """牛棚 v2：地基+墙体+双开门+瓦顶+侧窗+室内地板"""
    rng = gl.rng_from_seed(seed)
    wall_c = gl.jitter(gl.C("roof"), 0.03, rng)
    roof_c = gl.jitter(gl.C("wood_dark"), 0.03, rng)
    wood_c = gl.jitter(gl.C("wood"), 0.03, rng)
    W, D, H = 2.4, 2.0, 1.4
    wall_t = 0.1
    parts = []
    foundation = gl.mesh(gl.C("stone"), extents=(W + 0.25, 0.12, D + 0.25), geom="box")
    foundation.apply_translation([0, 0.06, 0])
    parts.append(("foundation", foundation))
    front = _wall_with_openings(wall_c, W, H, wall_t, [(0, 0.55, 0.9, 1.0)], y_base=wall_t)
    for name, m in front:
        m.apply_translation([0, 0, D / 2])
        parts.append((name, m))
    back = _wall_with_openings(wall_c, W, H, wall_t, [], y_base=wall_t)
    for name, m in back:
        m.apply_translation([0, 0, -D / 2])
        parts.append((name, m))
    for sx, rot in ((1, 90), (-1, -90)):
        side = _wall_with_openings(wall_c, D, H, wall_t, [], y_base=wall_t)
        for name, m in side:
            m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rot), [0, 1, 0], [0, 0, 0]))
            m.apply_translation([sx * W / 2, 0, 0])
            parts.append((name, m))
    # 双开门（左右两扇，各带把手）
    for sx, hs in ((-1, 1), (1, -1)):
        door_parts = _make_door(width=0.45, height=1.0, thickness=0.05, color="wood", handle_side=hs)
        for name, m in door_parts:
            m.apply_translation([sx * 0.225, wall_t, D / 2])
            parts.append((f"door_{'l' if sx<0 else 'r'}_{name}", m))
    floor = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), extents=(W - 0.05, 0.04, D - 0.05), geom="box")
    floor.apply_translation([0, wall_t, 0])
    parts.append(("floor", floor))
    for sx in (-1, 1):
        slope = gl.mesh(roof_c, extents=(W + 0.4, 0.08, 1.3), geom="box")
        slope.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-30 * sx), [1, 0, 0], [0, 0, 0]))
        slope.apply_translation([0, H + wall_t + 0.3, sx * (D / 2 - 0.35)])
        parts.append((f"roof_{sx}", slope))
    ridge = gl.mesh(roof_c, extents=(W + 0.45, 0.1, 0.1), geom="box")
    ridge.apply_translation([0, H + wall_t + 0.42, 0])
    parts.append(("ridge", ridge))
    for sx in (-1, 1):
        glass = gl.mesh(gl.C("sky"), extents=(0.4, 0.3, 0.03), geom="box")
        glass.apply_translation([sx * W / 2, wall_t + 0.7, 0.2])
        parts.append((f"glass_{sx}", glass))
    return parts


def gen_well(seed=1):
    """水井 v2：石壁双圈+装饰环+木顶+提桶"""
    rng = gl.rng_from_seed(seed)
    stone_c = gl.jitter(gl.C("stone"), 0.03, rng)
    wood_c = gl.jitter(gl.C("wood"), 0.03, rng)
    parts = []
    for i, (r, h) in enumerate(((0.28, 0.18), (0.24, 0.18))):
        wall = gl.mesh(stone_c, radius=r, height=h, sections=12, geom="cylinder")
        wall.apply_translation([0, 0.1 + i * 0.18, 0])
        parts.append((f"wall{i}", wall))
    inner = gl.mesh(gl.C("black"), radius=0.14, height=0.4, sections=8, geom="cylinder")
    inner.apply_translation([0, 0.2, 0])
    parts.append(("inner", inner))
    for i in range(6):
        ang = i * np.pi / 3
        ring = gl.mesh(gl.C("stone"), extents=(0.5, 0.04, 0.08), geom="box")
        ring.apply_transform(trimesh.transformations.rotation_matrix(ang, [0, 1, 0], [0, 0, 0]))
        ring.apply_translation([0, 0.28, 0])
        parts.append((f"ring{i}", ring))
    for side in (-1, 1):
        post = gl.mesh(wood_c, radius=0.035, height=0.75, sections=6, geom="cylinder")
        post.apply_translation([0.22 * side, 0.55, 0])
        parts.append((f"post{side}", post))
    crossbar = gl.mesh(wood_c, extents=(0.55, 0.06, 0.06), geom="box")
    crossbar.apply_translation([0, 0.95, 0])
    parts.append(("crossbar", crossbar))
    bucket = gl.mesh(gl.jitter(gl.C("wood"), 0.02, rng), radius=0.06, height=0.09, sections=8, geom="cylinder")
    bucket.apply_translation([0, 0.62, 0.08])
    parts.append(("bucket", bucket))
    rope = gl.mesh(gl.C("cream"), radius=0.006, height=0.2, sections=4, geom="cylinder")
    rope.apply_translation([0, 0.83, 0.08])
    parts.append(("rope", rope))
    return parts


# ---------------- 家具（室内布局用） ----------------
def gen_furn_bed(seed=1):
    """床：床头板+床架+床垫+枕头"""
    rng = gl.rng_from_seed(seed)
    wood_c = gl.jitter(gl.C("wood"), 0.03, rng)
    parts = []
    frame = gl.mesh(wood_c, extents=(0.9, 0.25, 1.9), geom="box")
    frame.apply_translation([0, 0.125, 0])
    parts.append(("frame", frame))
    headboard = gl.mesh(wood_c, extents=(0.9, 0.55, 0.08), geom="box")
    headboard.apply_translation([0, 0.4, -0.91])
    parts.append(("headboard", headboard))
    mattress = gl.mesh(gl.jitter(gl.C("cream"), 0.02, rng), extents=(0.85, 0.12, 1.85), geom="box")
    mattress.apply_translation([0, 0.31, 0])
    parts.append(("mattress", mattress))
    pillow = gl.mesh(gl.C("white"), extents=(0.55, 0.07, 0.3), geom="box")
    pillow.apply_translation([0, 0.41, -0.55])
    parts.append(("pillow", pillow))
    blanket = gl.mesh(gl.jitter(gl.C("blueberry"), 0.03, rng), extents=(0.86, 0.05, 1.2), geom="box")
    blanket.apply_translation([0, 0.4, 0.28])
    parts.append(("blanket", blanket))
    return parts


def gen_furn_table(seed=1):
    """木桌：桌面+4腿"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("wood"), 0.03, rng)
    parts = []
    top = gl.mesh(c, extents=(1.2, 0.06, 0.7), geom="box")
    top.apply_translation([0, 0.72, 0])
    parts.append(("top", top))
    for sx in (-0.5, 0.5):
        for sz in (-0.28, 0.28):
            leg = gl.mesh(c, radius=0.03, height=0.7, sections=6, geom="cylinder")
            leg.apply_translation([sx, 0.35, sz])
            parts.append((f"leg_{sx}_{sz}", leg))
    return parts


def gen_furn_chair(seed=1):
    """椅子：坐面+靠背+4腿"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("wood"), 0.03, rng)
    parts = []
    seat = gl.mesh(c, extents=(0.45, 0.05, 0.45), geom="box")
    seat.apply_translation([0, 0.45, 0])
    parts.append(("seat", seat))
    back = gl.mesh(c, extents=(0.45, 0.5, 0.05), geom="box")
    back.apply_translation([0, 0.72, -0.2])
    parts.append(("back", back))
    for sx in (-0.18, 0.18):
        for sz in (-0.18, 0.18):
            leg = gl.mesh(c, radius=0.02, height=0.45, sections=6, geom="cylinder")
            leg.apply_translation([sx, 0.225, sz])
            parts.append((f"leg_{sx}_{sz}", leg))
    return parts


def gen_furn_cabinet(seed=1):
    """储物柜：柜体+双门+把手"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("wood"), 0.03, rng)
    parts = []
    body = gl.mesh(c, extents=(0.9, 1.4, 0.5), geom="box")
    body.apply_translation([0, 0.7, 0])
    parts.append(("body", body))
    for sx in (-0.2, 0.2):
        door = gl.mesh(gl.jitter(gl.C("wood_dark"), 0.02, rng), extents=(0.4, 1.3, 0.03), geom="box")
        door.apply_translation([sx, 0.7, 0.27])
        parts.append((f"door_{sx}", door))
        handle = gl.mesh(gl.C("gold"), radius=0.01, height=0.08, sections=6, geom="cylinder")
        handle.apply_translation([sx + 0.16 * (-1 if sx > 0 else 1), 0.7, 0.29])
        parts.append((f"handle_{sx}", handle))
    return parts


def gen_furn_stove(seed=1):
    """炉灶：炉体+灶台+烟管"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("stone"), 0.03, rng)
    dark = gl.jitter(gl.C("black"), 0.02, rng)
    parts = []
    body = gl.mesh(c, extents=(0.8, 0.85, 0.6), geom="box")
    body.apply_translation([0, 0.425, 0])
    parts.append(("body", body))
    top = gl.mesh(dark, extents=(0.85, 0.06, 0.65), geom="box")
    top.apply_translation([0, 0.88, 0])
    parts.append(("top", top))
    for sx in (-0.25, 0.25):
        burner = gl.mesh(gl.C("tomato"), radius=0.09, height=0.02, sections=8, geom="cylinder")
        burner.apply_translation([sx, 0.92, 0])
        parts.append((f"burner_{sx}", burner))
    pipe = gl.mesh(dark, radius=0.06, height=0.5, sections=8, geom="cylinder")
    pipe.apply_translation([0.25, 1.32, 0])
    parts.append(("pipe", pipe))
    return parts


def gen_furn_bookshelf(seed=1):
    """书架：架体+3隔板+彩色书"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("wood_dark"), 0.03, rng)
    parts = []
    body = gl.mesh(c, extents=(1.0, 1.4, 0.3), geom="box")
    body.apply_translation([0, 0.7, 0])
    parts.append(("body", body))
    for i in range(3):
        shelf = gl.mesh(c, extents=(0.94, 0.04, 0.26), geom="box")
        shelf.apply_translation([0, 0.35 + i * 0.45, 0])
        parts.append((f"shelf{i}", shelf))
    book_colors = ["tomato", "blueberry", "egg_yolk", "grass", "pink", "sky"]
    for row in range(3):
        for i in range(5):
            book = gl.mesh(gl.C(book_colors[(row + i) % len(book_colors)]),
                           extents=(0.05, 0.3, 0.15), geom="box")
            book.apply_translation([-0.35 + i * 0.16, 0.2 + row * 0.45, 0.03])
            parts.append((f"book_{row}_{i}", book))
    return parts


def gen_furn_lamp(seed=1):
    """台灯：底座+柱+灯罩"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("egg_yolk"), 0.03, rng)
    dark = gl.jitter(gl.C("wood_dark"), 0.03, rng)
    parts = []
    base = gl.mesh(dark, radius=0.1, height=0.04, sections=10, geom="cylinder")
    base.apply_translation([0, 0.02, 0])
    parts.append(("base", base))
    pole = gl.mesh(dark, radius=0.015, height=0.5, sections=6, geom="cylinder")
    pole.apply_translation([0, 0.29, 0])
    parts.append(("pole", pole))
    shade = gl.mesh(c, radius=0.12, height=0.1, sections=10, geom="cone")
    shade.apply_translation([0, 0.55, 0])
    parts.append(("shade", shade))
    return parts


def gen_furn_rug(seed=1):
    """地毯：扁圆柱"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("tomato"), 0.04, rng)
    rug = gl.mesh(c, radius=0.7, height=0.02, sections=14, geom="cylinder")
    rug.apply_translation([0, 0.01, 0])
    return [("rug", rug)]


def gen_furn_sofa(seed=1):
    """沙发：底座+靠背+扶手"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("blueberry"), 0.03, rng)
    parts = []
    base = gl.mesh(c, extents=(1.6, 0.4, 0.7), geom="box")
    base.apply_translation([0, 0.2, 0])
    parts.append(("base", base))
    back = gl.mesh(c, extents=(1.6, 0.5, 0.15), geom="box")
    back.apply_translation([0, 0.55, -0.28])
    parts.append(("back", back))
    for sx in (-0.72, 0.72):
        arm = gl.mesh(c, extents=(0.15, 0.5, 0.7), geom="box")
        arm.apply_translation([sx, 0.25, 0])
        parts.append((f"arm_{sx}", arm))
    cushion = gl.mesh(gl.jitter(gl.C("cream"), 0.02, rng), extents=(1.4, 0.15, 0.5), geom="box")
    cushion.apply_translation([0, 0.48, 0.03])
    parts.append(("cushion", cushion))
    return parts


def gen_furn_workbench(seed=1):
    """工作台：台面+柜体+抽屉"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("wood"), 0.03, rng)
    dark = gl.jitter(gl.C("wood_dark"), 0.03, rng)
    parts = []
    top = gl.mesh(c, extents=(1.3, 0.08, 0.7), geom="box")
    top.apply_translation([0, 0.82, 0])
    parts.append(("top", top))
    body = gl.mesh(dark, extents=(1.1, 0.7, 0.6), geom="box")
    body.apply_translation([0, 0.35, 0])
    parts.append(("body", body))
    for i, sx in enumerate((-0.4, 0.0, 0.4)):
        drawer = gl.mesh(c, extents=(0.3, 0.12, 0.5), geom="box")
        drawer.apply_translation([sx, 0.55, 0])
        handle = gl.mesh(gl.C("gold"), radius=0.008, height=0.1, sections=4, geom="cylinder")
        handle.apply_translation([sx, 0.55, 0.31])
        parts.append((f"drawer{i}", drawer))
        parts.append((f"handle{i}", handle))
    return parts


# ---------------- 环境 ----------------
def gen_rock(seed=1):
    """石头：低模凸包（用 icosphere 挤压模拟）"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("stone"), 0.04, rng)
    rock = gl.mesh(c, radius=0.25, sections=5, geom="sphere")
    rock.apply_scale([rng.uniform(0.8, 1.3), rng.uniform(0.6, 0.9), rng.uniform(0.8, 1.3)])
    rock.apply_translation([0, 0.15, 0])
    return [("rock", rock)]


def gen_grass_tuft(seed=1):
    """草丛：3 簇草叶"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("grass"), 0.06, rng)
    parts = []
    for i in range(3):
        tuft = gl.mesh(c, extents=(0.03, 0.18, 0.03), geom="box")
        tuft.apply_translation([-0.04 + i * 0.04, 0.09, 0])
        tuft.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-15 + i * 15), [0, 0, 1], [0, 0, 0]))
        parts.append((f"tuft{i}", tuft))
    return parts


def gen_terrain_tile(seed=1):
    """草地地形块：1m 薄板 + 草色"""
    rng = gl.rng_from_seed(seed)
    c = gl.jitter(gl.C("grass"), 0.04, rng)
    tile = gl.mesh(c, extents=(1.0, 0.1, 1.0), geom="box")
    tile.apply_translation([0, 0.05, 0])
    return [("tile", tile)]
