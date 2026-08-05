# -*- coding: utf-8 -*-
"""鱼类生成器：鲤鱼/鲈鱼/鳟鱼/罗非鱼/鲶鱼/草鱼（低模，程序化摆动无需骨骼）"""
import numpy as np
import trimesh
import gen_lib as gl


def _body_profile(ratio, length):
    """按长宽比生成鱼身（用 ellipsoid 拉伸近似卡通鱼形）"""
    body_r = length / ratio  # 体高半径
    return body_r, length / 2  # 半径, 半长


def gen_fish(seed=1, kind="carp"):
    """通用鱼生成器：身体椭球 + 尾鳍 + 背鳍 + 眼睛"""
    rng = gl.rng_from_seed(seed)
    length = rng.uniform(0.4, 0.6)
    ratio = rng.uniform(2.5, 3.5)
    body_r, half_l = _body_profile(ratio, length)

    if kind == "carp":
        base_c = gl.jitter(gl.C("gold"), 0.06, rng)
    elif kind == "bass":
        base_c = gl.jitter(gl.C("grass"), 0.06, rng)
    elif kind == "trout":
        base_c = gl.jitter(gl.C("blueberry"), 0.06, rng)
    elif kind == "tilapia":
        base_c = gl.jitter(gl.C("stone"), 0.06, rng)
    elif kind == "catfish":
        base_c = gl.jitter(gl.C("wood_dark"), 0.06, rng)
    else:  # grass carp
        base_c = gl.jitter(gl.C("leaf_light"), 0.06, rng)
    belly_c = tuple(min(255, int(v * 1.15)) for v in base_c[:3]) + (255,)
    fin_c = gl.jitter(gl.C("ink"), 0.1, rng)
    eye_c = gl.C("black")

    parts = []
    # 身体：沿 Z 轴拉伸的椭球
    body = gl.mesh(base_c, radius=body_r, sections=10, geom="sphere")
    body.apply_scale([0.75, 0.85, 1.0])  # 侧扁
    body.apply_translation([0, 0, 0])
    parts.append(("body", body))
    # 肚皮：下半部浅色（简单用下方小椭球叠加）
    # 尾鳍（三角形，向后 -Z）
    tail = gl.mesh(fin_c, extents=(0.12, 0.22, 0.03), geom="box")
    tail.apply_translation([0, 0.05, -half_l - 0.02])
    tail.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-10), [1, 0, 0], [0, 0, 0]))
    parts.append(("tail", tail))
    # 背鳍
    dorsal = gl.mesh(fin_c, extents=(0.04, 0.12, 0.2), geom="box")
    dorsal.apply_translation([0, body_r * 0.95, -0.05])
    parts.append(("dorsal", dorsal))
    # 眼睛（在 +Z 前向）
    for side in (-1, 1):
        eye = gl.mesh(eye_c, radius=0.025, sections=6, geom="sphere")
        eye.apply_translation([body_r * 0.55 * side, body_r * 0.25, half_l * 0.85])
        parts.append((f"eye{side}", eye))
    return parts


# 各品种 = 通用生成 + 不同调色/细节
def gen_carp(seed=1):    return gen_fish(seed, "carp")
def gen_bass(seed=1):    return gen_fish(seed, "bass")
def gen_trout(seed=1):   return gen_fish(seed, "trout")
def gen_tilapia(seed=1): return gen_fish(seed, "tilapia")
def gen_catfish(seed=1): return gen_fish(seed, "catfish")
def gen_grass_carp(seed=1): return gen_fish(seed, "grass_carp")
