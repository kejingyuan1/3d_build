# -*- coding: utf-8 -*-
"""简单动物生成器：鸡/牛/羊/猪（低模卡通，Q 版比例）"""
import numpy as np
import trimesh
import gen_lib as gl


def gen_chicken(seed=1, color="white"):
    """鸡：圆身 + 头 + 冠 + 喙 + 短腿"""
    rng = gl.rng_from_seed(seed)
    if color == "white":
        body_c = gl.jitter(gl.C("cream"), 0.03, rng)
    else:
        body_c = gl.jitter(gl.C("wood"), 0.05, rng)
    comb_c = gl.C("tomato")
    beak_c = gl.C("beak")
    leg_c = gl.jitter(gl.C("egg_yolk"), 0.05, rng)

    parts = []
    body_r = 0.14
    body = gl.mesh(body_c, radius=body_r, sections=10, geom="sphere")
    body.apply_scale([1.1, 0.9, 1.2])
    body.apply_translation([0, 0.22, 0])
    parts.append(("body", body))
    head_r = 0.09
    head = gl.mesh(body_c, radius=head_r, sections=8, geom="sphere")
    head.apply_translation([0, 0.42, 0.1])
    parts.append(("head", head))
    comb = gl.mesh(comb_c, extents=(0.04, 0.04, 0.06), geom="box")
    comb.apply_translation([0, 0.5, 0.12])
    parts.append(("comb", comb))
    beak = gl.mesh(beak_c, extents=(0.03, 0.02, 0.05), geom="box")
    beak.apply_translation([0, 0.41, 0.19])
    parts.append(("beak", beak))
    # 眼睛
    for side in (-1, 1):
        eye = gl.mesh(gl.C("black"), radius=0.012, sections=6, geom="sphere")
        eye.apply_translation([0.05 * side, 0.44, 0.14])
        parts.append((f"eye{side}", eye))
    # 腿
    for side in (-1, 1):
        leg = gl.mesh(leg_c, radius=0.015, height=0.1, sections=6, geom="cylinder")
        leg.apply_translation([0.06 * side, 0.05, 0])
        parts.append((f"leg{side}", leg))
    # 尾
    tail = gl.mesh(body_c, extents=(0.06, 0.1, 0.04), geom="box")
    tail.apply_translation([0, 0.28, -0.16])
    tail.apply_transform(trimesh.transformations.rotation_matrix(np.radians(30), [1, 0, 0], [0, 0, 0]))
    parts.append(("tail", tail))
    return parts


def gen_cow(seed=1, color="holstein"):
    """牛：Q 版圆身 + 头 + 角 + 短腿"""
    rng = gl.rng_from_seed(seed)
    if color == "holstein":
        body_c = gl.jitter(gl.C("white"), 0.02, rng)
        patch_c = gl.C("black")
    else:
        body_c = gl.jitter(gl.C("wood"), 0.05, rng)
        patch_c = gl.jitter(gl.C("cream"), 0.03, rng)
    parts = []
    body_r = 0.32
    body = gl.mesh(body_c, radius=body_r, sections=12, geom="sphere")
    body.apply_scale([1.4, 0.85, 1.1])
    body.apply_translation([0, 0.5, 0])
    parts.append(("body", body))
    # 斑点（荷斯坦）
    if color == "holstein":
        for i in range(3):
            patch = gl.mesh(patch_c, radius=0.08, sections=6, geom="sphere")
            patch.apply_scale([1.2, 0.6, 1.0])
            patch.apply_translation([0.22 * (-1) ** i, 0.58 + 0.06 * i, 0.05])
            parts.append((f"patch{i}", patch))
    # 头
    head_r = 0.15
    head = gl.mesh(body_c, radius=head_r, sections=10, geom="sphere")
    head.apply_translation([0, 0.72, 0.34])
    parts.append(("head", head))
    snout = gl.mesh(patch_c if color == "holstein" else gl.jitter(gl.C("cream"), 0.03, rng),
                    extents=(0.1, 0.08, 0.06), geom="box")
    snout.apply_translation([0, 0.66, 0.5])
    parts.append(("snout", snout))
    # 角
    for side in (-1, 1):
        horn = gl.mesh(gl.C("egg_yolk"), radius=0.02, height=0.08, sections=6, geom="cone")
        horn.apply_translation([0.09 * side, 0.92, 0.28])
        parts.append((f"horn{side}", horn))
    # 眼睛
    for side in (-1, 1):
        eye = gl.mesh(gl.C("black"), radius=0.018, sections=6, geom="sphere")
        eye.apply_translation([0.07 * side, 0.76, 0.4])
        parts.append((f"eye{side}", eye))
    # 腿 x4
    for side in (-1, 1):
        for fb in (-1, 1):
            leg = gl.mesh(gl.jitter(gl.C("cream"), 0.03, rng), radius=0.045, height=0.28, sections=8, geom="cylinder")
            leg.apply_translation([0.22 * side, 0.14, 0.16 * fb])
            parts.append((f"leg{side}_{fb}", leg))
    # 尾巴
    tail = gl.mesh(body_c, radius=0.02, height=0.22, sections=6, geom="cylinder")
    tail.apply_translation([0, 0.62, -0.34])
    tail.apply_transform(trimesh.transformations.rotation_matrix(np.radians(40), [1, 0, 0], [0, 0, 0]))
    parts.append(("tail", tail))
    # 铃铛
    bell = gl.mesh(gl.C("gold"), radius=0.035, sections=6, geom="sphere")
    bell.apply_translation([0, 0.55, 0.48])
    parts.append(("bell", bell))
    return parts


def gen_sheep(seed=1):
    """羊：蓬松卷毛身 + 黑脸"""
    rng = gl.rng_from_seed(seed)
    wool_c = gl.jitter(gl.C("cream"), 0.03, rng)
    face_c = gl.C("black")
    parts = []
    body = gl.mesh(wool_c, radius=0.24, sections=12, geom="sphere")
    body.apply_scale([1.5, 0.9, 1.15])
    body.apply_translation([0, 0.42, 0])
    parts.append(("body", body))
    # 卷毛簇
    for i in range(5):
        tuft = gl.mesh(wool_c, radius=0.09, sections=6, geom="sphere")
        tuft.apply_translation([0.28 * np.cos(i * 2 * np.pi / 5), 0.55, 0.2 * np.sin(i * 2 * np.pi / 5)])
        parts.append((f"tuft{i}", tuft))
    head = gl.mesh(face_c, radius=0.09, sections=8, geom="sphere")
    head.apply_translation([0, 0.58, 0.3])
    parts.append(("head", head))
    for side in (-1, 1):
        ear = gl.mesh(face_c, extents=(0.05, 0.03, 0.04), geom="box")
        ear.apply_translation([0.07 * side, 0.66, 0.28])
        parts.append((f"ear{side}", ear))
    for side in (-1, 1):
        leg = gl.mesh(gl.C("black"), radius=0.03, height=0.2, sections=6, geom="cylinder")
        leg.apply_translation([0.15 * side, 0.1, 0.12])
        parts.append((f"leg{side}", leg))
    return parts


def gen_pig(seed=1):
    """猪：粉身 + 大鼻 + 卷尾"""
    rng = gl.rng_from_seed(seed)
    pink_c = gl.jitter(gl.C("pink"), 0.04, rng)
    parts = []
    body = gl.mesh(pink_c, radius=0.22, sections=12, geom="sphere")
    body.apply_scale([1.4, 0.85, 1.1])
    body.apply_translation([0, 0.32, 0])
    parts.append(("body", body))
    head = gl.mesh(pink_c, radius=0.13, sections=10, geom="sphere")
    head.apply_translation([0, 0.4, 0.26])
    parts.append(("head", head))
    snout = gl.mesh(gl.jitter(gl.C("pink"), 0.02, rng), extents=(0.12, 0.08, 0.06), geom="box")
    snout.apply_translation([0, 0.36, 0.4])
    parts.append(("snout", snout))
    for side in (-1, 1):
        ear = gl.mesh(pink_c, extents=(0.08, 0.05, 0.03), geom="box")
        ear.apply_translation([0.09 * side, 0.55, 0.24])
        ear.apply_transform(trimesh.transformations.rotation_matrix(np.radians(25 * side), [0, 0, 1], [0, 0, 0]))
        parts.append((f"ear{side}", ear))
    for side in (-1, 1):
        leg = gl.mesh(pink_c, radius=0.035, height=0.18, sections=6, geom="cylinder")
        leg.apply_translation([0.14 * side, 0.09, 0.12])
        parts.append((f"leg{side}", leg))
    # 卷尾
    tail = gl.mesh(pink_c, radius=0.02, height=0.06, sections=6, geom="cylinder")
    tail.apply_translation([0, 0.45, -0.24])
    parts.append(("tail", tail))
    return parts
