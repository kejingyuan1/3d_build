# -*- coding: utf-8 -*-
"""植物生成器：小麦/胡萝卜/番茄/南瓜/树/花 + 耕地地块"""
import numpy as np
import trimesh
import gen_lib as gl


def gen_wheat(seed=1, stage="mature"):
    """小麦：3阶段（种子->幼苗->成熟）"""
    rng = gl.rng_from_seed(seed)
    color = gl.jitter(gl.C("wheat"), 0.05, rng)
    green = gl.jitter(gl.C("grass"), 0.05, rng)
    parts = []
    if stage == "seed":
        p = gl.mesh(color, extents=(0.08, 0.03, 0.08), geom="box")
        p.apply_translation([0, 0.015, 0])
        parts.append(("seed", p))
    elif stage == "seedling":
        h = 0.25
        stem = gl.mesh(green, radius=0.012, height=h, sections=6, geom="cylinder")
        stem.apply_translation([0, h / 2, 0])
        leaf = gl.mesh(green, extents=(0.05, 0.18, 0.02), geom="box")
        leaf.apply_translation([0.04, 0.15, 0])
        leaf.apply_transform(trimesh.transformations.rotation_matrix(np.radians(15), [0, 0, 1], [0, 0, 0]))
        parts.append(("stem", stem))
        parts.append(("leaf", leaf))
    else:  # mature
        h = 0.7
        stem = gl.mesh(green, radius=0.014, height=h, sections=6, geom="cylinder")
        stem.apply_translation([0, h / 2, 0])
        head = gl.mesh(color, extents=(0.06, 0.22, 0.06), geom="box")
        head.apply_translation([0, h + 0.06, 0])
        leaf = gl.mesh(green, extents=(0.04, 0.3, 0.02), geom="box")
        leaf.apply_translation([0.02, h * 0.6, 0])
        leaf.apply_transform(trimesh.transformations.rotation_matrix(np.radians(20), [0, 0, 1], [0, 0, 0]))
        parts.append(("stem", stem))
        parts.append(("head", head))
        parts.append(("leaf", leaf))
    return parts


def gen_carrot(seed=1, stage="mature"):
    """胡萝卜：地上叶簇 + 地下根（露出顶部）"""
    rng = gl.rng_from_seed(seed)
    orange = gl.jitter(gl.C("carrot"), 0.05, rng)
    green = gl.jitter(gl.C("leaf_light"), 0.05, rng)
    parts = []
    if stage == "seed":
        p = gl.mesh(orange, radius=0.02, height=0.02, sections=6, geom="cylinder")
        p.apply_translation([0, 0.01, 0])
        parts.append(("seed", p))
    elif stage == "seedling":
        h = 0.18
        leaf = gl.mesh(green, extents=(0.12, 0.16, 0.02), geom="box")
        leaf.apply_translation([0, 0.12, 0])
        parts.append(("leaf", leaf))
    else:
        root_r, root_h = 0.04, 0.22
        root = gl.mesh(orange, radius=root_r, height=root_h, sections=8, geom="cylinder")
        root.apply_translation([0, -root_h / 2, 0])
        tip = gl.mesh(orange, radius=0.015, height=0.06, sections=6, geom="cone")
        tip.apply_translation([0, -root_h - 0.02, 0])
        # 叶簇
        for i, ang in enumerate([0, 120, 240]):
            leaf = gl.mesh(green, extents=(0.05, 0.28, 0.015), geom="box")
            leaf.apply_translation([0, 0.1, 0])
            leaf.apply_transform(trimesh.transformations.rotation_matrix(np.radians(ang), [0, 1, 0], [0, 0, 0]))
            leaf.apply_transform(trimesh.transformations.rotation_matrix(np.radians(25 + i * 5), [0, 0, 1], [0, 0, 0]))
            parts.append((f"leaf{i}", leaf))
        parts.append(("root", root))
        parts.append(("tip", tip))
    return parts


def gen_tomato(seed=1, stage="mature"):
    """番茄：矮株 + 红色果实"""
    rng = gl.rng_from_seed(seed)
    green = gl.jitter(gl.C("grass"), 0.05, rng)
    red = gl.jitter(gl.C("tomato"), 0.05, rng)
    parts = []
    if stage == "seed":
        p = gl.mesh(red, radius=0.02, height=0.02, sections=6, geom="cylinder")
        p.apply_translation([0, 0.01, 0])
        parts.append(("seed", p))
    elif stage == "seedling":
        h = 0.2
        stem = gl.mesh(green, radius=0.015, height=h, sections=6, geom="cylinder")
        stem.apply_translation([0, h / 2, 0])
        parts.append(("stem", stem))
    else:
        h = 0.35
        stem = gl.mesh(green, radius=0.02, height=h, sections=6, geom="cylinder")
        stem.apply_translation([0, h / 2, 0])
        bush = gl.mesh(green, radius=0.16, height=0.12, sections=10, geom="sphere")
        bush.apply_translation([0, h + 0.05, 0])
        bush.apply_scale([1.2, 0.7, 1.2])
        for i in range(3):
            fruit = gl.mesh(red, radius=0.05, sections=8, geom="sphere")
            angle = i * 2 * np.pi / 3
            fruit.apply_translation([0.12 * np.cos(angle), h - 0.05 + (i % 2) * 0.06, 0.12 * np.sin(angle)])
            parts.append((f"fruit{i}", fruit))
        parts.append(("stem", stem))
        parts.append(("bush", bush))
    return parts


def gen_pumpkin(seed=1, stage="mature"):
    """南瓜：扁圆橙 + 藤蔓 + 顶柄"""
    rng = gl.rng_from_seed(seed)
    orange = gl.jitter(gl.C("pumpkin"), 0.05, rng)
    green = gl.jitter(gl.C("leaf_dark"), 0.05, rng)
    parts = []
    if stage == "seed":
        p = gl.mesh(orange, radius=0.02, height=0.02, sections=6, geom="cylinder")
        p.apply_translation([0, 0.01, 0])
        parts.append(("seed", p))
    elif stage == "seedling":
        h = 0.2
        stem = gl.mesh(green, radius=0.015, height=h, sections=6, geom="cylinder")
        stem.apply_translation([0, h / 2, 0])
        parts.append(("stem", stem))
    else:
        body = gl.mesh(orange, radius=0.22, sections=12, geom="sphere")
        body.apply_scale([1.0, 0.7, 1.0])
        body.apply_translation([0, 0.15, 0])
        handle = gl.mesh(green, radius=0.03, height=0.1, sections=6, geom="cylinder")
        handle.apply_translation([0, 0.34, 0])
        vine = gl.mesh(green, extents=(0.16, 0.03, 0.03), geom="box")
        vine.apply_translation([0.14, 0.05, 0.05])
        parts.append(("body", body))
        parts.append(("handle", handle))
        parts.append(("vine", vine))
    return parts


def gen_tree(seed=1, kind="oak"):
    """树：树干圆柱 + 树冠球簇（可 2-3 变体）"""
    rng = gl.rng_from_seed(seed)
    trunk_c = gl.jitter(gl.C("wood"), 0.05, rng)
    if kind == "oak":
        crown_c = gl.jitter(gl.C("leaf_dark"), 0.06, rng)
    elif kind == "apple":
        crown_c = gl.jitter(gl.C("leaf_light"), 0.06, rng)
    else:
        crown_c = gl.jitter(gl.C("grass"), 0.06, rng)
    trunk_h = rng.uniform(0.8, 1.2)
    trunk_r = rng.uniform(0.06, 0.09)
    crown_r = rng.uniform(0.35, 0.5)
    parts = []
    trunk = gl.mesh(trunk_c, radius=trunk_r, height=trunk_h, sections=8, geom="cylinder")
    trunk.apply_translation([0, trunk_h / 2, 0])
    parts.append(("trunk", trunk))
    # 树冠：主球 + 3 个副球簇
    main = gl.mesh(crown_c, radius=crown_r, sections=10, geom="sphere")
    main.apply_translation([0, trunk_h + crown_r * 0.7, 0])
    parts.append(("crown_main", main))
    for i in range(3):
        ang = i * 2 * np.pi / 3 + rng.uniform(-0.3, 0.3)
        sub = gl.mesh(crown_c, radius=crown_r * 0.55, sections=8, geom="sphere")
        sub.apply_translation([
            crown_r * 0.75 * np.cos(ang),
            trunk_h + crown_r * (0.35 + (i % 2) * 0.3),
            crown_r * 0.75 * np.sin(ang),
        ])
        parts.append((f"crown_sub{i}", sub))
    if kind == "apple":
        for i in range(4):
            fruit = gl.mesh(gl.C("tomato"), radius=0.035, sections=6, geom="sphere")
            ang = i * np.pi / 2
            fruit.apply_translation([
                crown_r * 0.5 * np.cos(ang),
                trunk_h + crown_r * 0.55,
                crown_r * 0.5 * np.sin(ang),
            ])
            parts.append((f"fruit{i}", fruit))
    return parts


def gen_flower(seed=1, kind="daisy"):
    """花：茎 + 花盘 + 花瓣"""
    rng = gl.rng_from_seed(seed)
    green = gl.jitter(gl.C("grass"), 0.05, rng)
    parts = []
    stem_h = rng.uniform(0.25, 0.4)
    stem = gl.mesh(green, radius=0.008, height=stem_h, sections=6, geom="cylinder")
    stem.apply_translation([0, stem_h / 2, 0])
    parts.append(("stem", stem))
    if kind == "daisy":
        petal_c = gl.jitter(gl.C("cream"), 0.03, rng)
        center_c = gl.jitter(gl.C("egg_yolk"), 0.05, rng)
    else:
        petal_c = gl.jitter(gl.C("pink"), 0.05, rng)
        center_c = gl.jitter(gl.C("tomato"), 0.05, rng)
    for i in range(6):
        ang = i * np.pi / 3
        petal = gl.mesh(petal_c, extents=(0.025, 0.02, 0.06), geom="box")
        petal.apply_translation([0.04 * np.cos(ang), stem_h + 0.02, 0.04 * np.sin(ang)])
        parts.append((f"petal{i}", petal))
    center = gl.mesh(center_c, radius=0.03, sections=8, geom="sphere")
    center.apply_translation([0, stem_h + 0.02, 0])
    parts.append(("center", center))
    return parts


def gen_tilled_soil(seed=1):
    """耕地地块：1m x 1m 薄板 + 犁沟"""
    rng = gl.rng_from_seed(seed)
    soil_c = gl.jitter(gl.C("soil"), 0.04, rng)
    parts = []
    base = gl.mesh(soil_c, extents=(1.0, 0.05, 1.0), geom="box")
    base.apply_translation([0, 0.025, 0])
    parts.append(("soil_base", base))
    for i in range(3):
        ridge = gl.mesh(gl.jitter(gl.C("soil"), 0.03, rng), extents=(0.14, 0.04, 0.9), geom="box")
        ridge.apply_translation([-0.3 + i * 0.3, 0.06, 0])
        parts.append((f"ridge{i}", ridge))
    return parts
