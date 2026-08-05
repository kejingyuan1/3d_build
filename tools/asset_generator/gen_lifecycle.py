# -*- coding: utf-8 -*-
"""
养殖生命周期生成器：蛋 → 幼年 → 成熟 三阶段模型
- 家禽：鸭（蛋/幼/成）、鹅（蛋/幼/成）、鸡（幼 + 褐壳蛋）
- 家畜：牛犊、羊羔、猪仔（幼年，成年已有）
输出到 assets/lifecycle/lifecycle_<animal>_<stage>.glb
依赖 gen_lib 强制规范：PALETTE/C/jitter/mesh/export_scene/_ensure_normals
尺寸真实：蛋 0.06-0.12m、幼年 0.3-0.5m、成年鸭/鹅 0.6-0.9m、牛犊 0.8m、羊羔 0.5m、猪仔 0.4m
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


# ================ 颜色（PALETTE 亮色 + 蛋壳/绒毛专用亮色） ================
# 蛋壳 / 绒毛专用（保持卡通风亮色）
EGG_CYAN = (0xC9, 0xE8, 0xD8)      # 鸭蛋：浅青绿
EGG_GOOSE = (0xF7, 0xF6, 0xF0)     # 鹅蛋：米白
EGG_BROWN = (0xC9, 0xA2, 0x6B)     # 褐壳蛋
FLUFF_YELLOW = (0xFF, 0xD9, 0x66)  # 幼黄（比 egg_yolk 更嫩）
FLUFF_CREAM = (0xF5, 0xEF, 0xE0)   # 浅黄绒毛
BODY_DUCK = (0xEE, 0xEE, 0xEE)     # 成年鸭：白灰身
BODY_GOOSE = (0xF3, 0xF0, 0xEA)    # 成年鹅：米白身


def _j(color, amt=0.03, rng=None):
    return gl.jitter(color, amt, rng)


# ================ 蛋（椭球 + 底部微尖） ================

def _egg(color, r, seed=1):
    """蛋：椭球 + 底部微尖（小锥），锚点底部中心"""
    rng = gl.rng_from_seed(seed)
    body = gl.mesh(_j(color, 0.02, rng), radius=r, sections=10, geom="sphere")
    body.apply_scale([0.75, 1.05, 0.75])
    # 使底部落在 y=0：椭球中心在 y = r*1.05*0.7（近似），先放底部到 0 再处理
    body.apply_translation([0, r * 0.62, 0])
    tip = gl.mesh(_j(color, 0.02, rng), radius=r * 0.30, height=r * 0.55, sections=8, geom="cone")
    tip.apply_translation([0, -r * 0.02, 0])
    return [("egg_body", body), ("egg_tip", tip)]


# ================ 通用幼年（Q 版圆胖） ================

def _baby_base(body_c, body_r, head_r, body_y, head_y, head_z, rng):
    """Q 版幼崽基座：圆胖身 + 头"""
    parts = []
    body = gl.mesh(_j(body_c, 0.03, rng), radius=body_r, sections=10, geom="sphere")
    body.apply_scale([1.15, 0.95, 1.15])
    body.apply_translation([0, body_y, 0])
    parts.append(("body", body))
    head = gl.mesh(_j(body_c, 0.03, rng), radius=head_r, sections=8, geom="sphere")
    head.apply_translation([0, head_y, head_z])
    parts.append(("head", head))
    return parts


def _eyes(parts, y, z, x_off=0.05, r=0.012, color=None):
    for side in (-1, 1):
        e = gl.mesh(color or gl.C("black"), radius=r, sections=6, geom="sphere")
        e.apply_translation([x_off * side, y, z])
        parts.append((f"eye{side}", e))


def _legs(parts, color, r, h, x_off, y, z_off, rng):
    for side in (-1, 1):
        leg = gl.mesh(_j(color, 0.04, rng), radius=r, height=h, sections=6, geom="cylinder")
        leg.apply_translation([x_off * side, y, z_off])
        parts.append((f"leg{side}", leg))


# ================ 鸭 ================

def gen_duck_egg(seed=1):
    return _egg(EGG_CYAN, 0.055, seed)


def gen_duck_baby(seed=2):
    """小鸭：黄色圆胖、短扁橙嘴、黑眼、小翅膀"""
    rng = gl.rng_from_seed(seed)
    parts = _baby_base(FLUFF_YELLOW, 0.15, 0.10, 0.16, 0.32, 0.05, rng)
    # 绒毛层次（身上小绒球）
    for i in range(4):
        tuft = gl.mesh(_j(FLUFF_YELLOW, 0.04, rng), radius=0.045, sections=6, geom="sphere")
        tuft.apply_translation([0.1 * np.cos(i * np.pi / 2), 0.24 + 0.03 * (i % 2), 0.1 * np.sin(i * np.pi / 2)])
        parts.append((f"tuft{i}", tuft))
    # 扁嘴（橙）
    beak = gl.mesh(_j(gl.C("beak"), 0.02, rng), extents=(0.08, 0.028, 0.04), geom="box")
    beak.apply_translation([0, 0.30, 0.14])
    parts.append(("beak", beak))
    _eyes(parts, 0.33, 0.12, x_off=0.045, r=0.011)
    # 小翅膀
    for side in (-1, 1):
        wing = gl.mesh(_j(FLUFF_YELLOW, 0.04, rng), extents=(0.06, 0.04, 0.12), geom="box")
        wing.apply_translation([0.14 * side, 0.20, 0.0])
        parts.append((f"wing{side}", wing))
    # 小脚（橙）
    _legs(parts, gl.C("beak"), 0.012, 0.06, 0.05, 0.03, 0.0, rng)
    return parts


def gen_duck_adult(seed=3):
    """成年鸭：白灰身、橙色长扁嘴、蹼足、翅膀、短尾"""
    rng = gl.rng_from_seed(seed)
    parts = []
    body = gl.mesh(_j(BODY_DUCK, 0.02, rng), radius=0.21, sections=12, geom="sphere")
    body.apply_scale([1.2, 0.85, 1.2])
    body.apply_translation([0, 0.30, 0])
    parts.append(("body", body))
    # 颈 + 头
    neck = gl.mesh(_j(BODY_DUCK, 0.02, rng), radius=0.055, height=0.16, sections=8, geom="cylinder")
    neck.apply_translation([0, 0.48, 0.05])
    parts.append(("neck", neck))
    head = gl.mesh(_j(BODY_DUCK, 0.02, rng), radius=0.095, sections=8, geom="sphere")
    head.apply_translation([0, 0.60, 0.10])
    parts.append(("head", head))
    # 长扁嘴（橙）
    beak = gl.mesh(_j(gl.C("beak"), 0.02, rng), extents=(0.12, 0.032, 0.05), geom="box")
    beak.apply_translation([0, 0.58, 0.22])
    parts.append(("beak", beak))
    _eyes(parts, 0.62, 0.17, x_off=0.045, r=0.013)
    # 翅膀
    for side in (-1, 1):
        wing = gl.mesh(_j(BODY_DUCK, 0.03, rng), extents=(0.09, 0.06, 0.26), geom="box")
        wing.apply_translation([0.19 * side, 0.33, 0.0])
        parts.append((f"wing{side}", wing))
    # 短尾（翘起）
    tail = gl.mesh(_j(BODY_DUCK, 0.03, rng), extents=(0.08, 0.09, 0.06), geom="box")
    tail.apply_translation([0, 0.38, -0.22])
    tail.apply_transform(trimesh.transformations.rotation_matrix(np.radians(30), [1, 0, 0], [0, 0, 0]))
    parts.append(("tail", tail))
    # 蹼足（橙扁）
    for side in (-1, 1):
        foot = gl.mesh(_j(gl.C("beak"), 0.03, rng), extents=(0.09, 0.03, 0.15), geom="box")
        foot.apply_translation([0.08 * side, 0.015, 0.02])
        parts.append((f"foot{side}", foot))
    return parts


# ================ 鹅 ================

def gen_goose_egg(seed=4):
    return _egg(EGG_GOOSE, 0.065, seed)


def gen_goose_baby(seed=5):
    """小鹅：圆胖、浅黄/浅灰绒毛、短嘴、黑眼"""
    rng = gl.rng_from_seed(seed)
    body_c = FLUFF_CREAM
    parts = _baby_base(body_c, 0.16, 0.105, 0.17, 0.34, 0.06, rng)
    for i in range(4):
        tuft = gl.mesh(_j(body_c, 0.04, rng), radius=0.05, sections=6, geom="sphere")
        tuft.apply_translation([0.1 * np.cos(i * np.pi / 2), 0.25 + 0.03 * (i % 2), 0.1 * np.sin(i * np.pi / 2)])
        parts.append((f"tuft{i}", tuft))
    beak = gl.mesh(_j(gl.C("beak"), 0.02, rng), extents=(0.075, 0.026, 0.04), geom="box")
    beak.apply_translation([0, 0.32, 0.15])
    parts.append(("beak", beak))
    _eyes(parts, 0.35, 0.13, x_off=0.05, r=0.011)
    for side in (-1, 1):
        wing = gl.mesh(_j(body_c, 0.04, rng), extents=(0.06, 0.04, 0.12), geom="box")
        wing.apply_translation([0.15 * side, 0.21, 0.0])
        parts.append((f"wing{side}", wing))
    _legs(parts, gl.C("beak"), 0.013, 0.07, 0.05, 0.03, 0.0, rng)
    return parts


def gen_goose_adult(seed=6):
    """成年鹅：长颈、白/浅灰身、橙嘴 + 橙蹼足、翅膀"""
    rng = gl.rng_from_seed(seed)
    parts = []
    body = gl.mesh(_j(BODY_GOOSE, 0.02, rng), radius=0.24, sections=12, geom="sphere")
    body.apply_scale([1.25, 0.8, 1.25])
    body.apply_translation([0, 0.34, 0])
    parts.append(("body", body))
    # 长颈（鹅的标志）
    neck = gl.mesh(_j(BODY_GOOSE, 0.02, rng), radius=0.05, height=0.34, sections=8, geom="cylinder")
    neck.apply_translation([0, 0.62, 0.08])
    neck.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-10), [1, 0, 0], [0, 0, 0]))
    parts.append(("neck", neck))
    head = gl.mesh(_j(BODY_GOOSE, 0.02, rng), radius=0.085, sections=8, geom="sphere")
    head.apply_translation([0, 0.80, 0.14])
    parts.append(("head", head))
    beak = gl.mesh(_j(gl.C("beak"), 0.02, rng), extents=(0.10, 0.03, 0.045), geom="box")
    beak.apply_translation([0, 0.78, 0.24])
    parts.append(("beak", beak))
    _eyes(parts, 0.82, 0.20, x_off=0.04, r=0.012)
    # 翅膀
    for side in (-1, 1):
        wing = gl.mesh(_j(BODY_GOOSE, 0.03, rng), extents=(0.10, 0.07, 0.30), geom="box")
        wing.apply_translation([0.22 * side, 0.36, 0.0])
        parts.append((f"wing{side}", wing))
    # 短尾
    tail = gl.mesh(_j(BODY_GOOSE, 0.03, rng), extents=(0.09, 0.10, 0.07), geom="box")
    tail.apply_translation([0, 0.42, -0.24])
    tail.apply_transform(trimesh.transformations.rotation_matrix(np.radians(25), [1, 0, 0], [0, 0, 0]))
    parts.append(("tail", tail))
    # 蹼足
    for side in (-1, 1):
        foot = gl.mesh(_j(gl.C("beak"), 0.03, rng), extents=(0.10, 0.035, 0.17), geom="box")
        foot.apply_translation([0.09 * side, 0.018, 0.02])
        parts.append((f"foot{side}", foot))
    return parts


# ================ 鸡（幼年 + 褐壳蛋） ================

def gen_chicken_baby(seed=7):
    """小鸡：黄色绒毛球（多层绒毛层次）+ 橙小嘴 + 黑眼"""
    rng = gl.rng_from_seed(seed)
    parts = []
    body = gl.mesh(_j(FLUFF_YELLOW, 0.03, rng), radius=0.13, sections=10, geom="sphere")
    body.apply_scale([1.1, 1.0, 1.1])
    body.apply_translation([0, 0.14, 0])
    parts.append(("body", body))
    # 绒毛层次：身上 + 头顶 + 两肋的小绒球
    for i in range(5):
        a = i * 2 * np.pi / 5
        tuft = gl.mesh(_j(FLUFF_YELLOW, 0.05, rng), radius=0.05, sections=6, geom="sphere")
        tuft.apply_translation([0.13 * np.cos(a), 0.15 + 0.04 * (i % 2), 0.11 * np.sin(a)])
        parts.append((f"tuft{i}", tuft))
    head = gl.mesh(_j(FLUFF_YELLOW, 0.03, rng), radius=0.09, sections=8, geom="sphere")
    head.apply_translation([0, 0.30, 0.05])
    parts.append(("head", head))
    head_tuft = gl.mesh(_j(FLUFF_YELLOW, 0.05, rng), radius=0.04, sections=6, geom="sphere")
    head_tuft.apply_translation([0, 0.39, 0.05])
    parts.append(("head_tuft", head_tuft))
    beak = gl.mesh(_j(gl.C("beak"), 0.02, rng), extents=(0.045, 0.022, 0.035), geom="box")
    beak.apply_translation([0, 0.29, 0.14])
    parts.append(("beak", beak))
    _eyes(parts, 0.32, 0.11, x_off=0.04, r=0.011)
    for side in (-1, 1):
        wing = gl.mesh(_j(FLUFF_YELLOW, 0.05, rng), extents=(0.05, 0.035, 0.10), geom="box")
        wing.apply_translation([0.12 * side, 0.16, 0.0])
        parts.append((f"wing{side}", wing))
    _legs(parts, gl.C("beak"), 0.011, 0.05, 0.04, 0.025, 0.0, rng)
    return parts


def gen_chicken_egg_brown(seed=8):
    return _egg(EGG_BROWN, 0.042, seed)


# ================ 家畜幼年 ================

def gen_cow_calf(seed=9):
    """牛犊：小体型、白底黑斑、短腿、大圆眼、小角苞"""
    rng = gl.rng_from_seed(seed)
    parts = []
    body_c = gl.jitter(gl.C("white"), 0.02, rng)
    body = gl.mesh(body_c, radius=0.22, sections=12, geom="sphere")
    body.apply_scale([1.35, 0.8, 1.05])
    body.apply_translation([0, 0.32, 0])
    parts.append(("body", body))
    # 黑斑
    for i in range(3):
        patch = gl.mesh(gl.C("black"), radius=0.06, sections=6, geom="sphere")
        patch.apply_scale([1.2, 0.6, 1.0])
        patch.apply_translation([0.16 * (-1) ** i, 0.38 + 0.05 * i, 0.04])
        parts.append((f"patch{i}", patch))
    # 头
    head = gl.mesh(body_c, radius=0.11, sections=8, geom="sphere")
    head.apply_translation([0, 0.48, 0.24])
    parts.append(("head", head))
    snout = gl.mesh(gl.jitter(gl.C("cream"), 0.03, rng), extents=(0.07, 0.06, 0.05), geom="box")
    snout.apply_translation([0, 0.43, 0.35])
    parts.append(("snout", snout))
    # 小角苞（无角或小角苞）
    for side in (-1, 1):
        bud = gl.mesh(gl.jitter(gl.C("egg_yolk"), 0.03, rng), radius=0.016, height=0.035, sections=6, geom="cone")
        bud.apply_translation([0.065 * side, 0.60, 0.20])
        parts.append((f"horn_bud{side}", bud))
    # 大圆眼
    _eyes(parts, 0.50, 0.29, x_off=0.05, r=0.016)
    # 短腿
    for side in (-1, 1):
        for fb in (-1, 1):
            leg = gl.mesh(gl.jitter(gl.C("cream"), 0.03, rng), radius=0.032, height=0.15, sections=6, geom="cylinder")
            leg.apply_translation([0.15 * side, 0.075, 0.12 * fb])
            parts.append((f"leg{side}_{fb}", leg))
    # 尾巴
    tail = gl.mesh(body_c, radius=0.016, height=0.14, sections=6, geom="cylinder")
    tail.apply_translation([0, 0.40, -0.23])
    tail.apply_transform(trimesh.transformations.rotation_matrix(np.radians(40), [1, 0, 0], [0, 0, 0]))
    parts.append(("tail", tail))
    # 小铃铛
    bell = gl.mesh(gl.C("gold"), radius=0.028, sections=6, geom="sphere")
    bell.apply_translation([0, 0.38, 0.34])
    parts.append(("bell", bell))
    return parts


def gen_sheep_lamb(seed=10):
    """羊羔：小体型、白色卷毛（多小球）、黑/灰脸、短腿"""
    rng = gl.rng_from_seed(seed)
    wool_c = gl.jitter(gl.C("cream"), 0.03, rng)
    face_c = gl.C("black")
    parts = []
    body = gl.mesh(wool_c, radius=0.16, sections=10, geom="sphere")
    body.apply_scale([1.4, 0.85, 1.1])
    body.apply_translation([0, 0.26, 0])
    parts.append(("body", body))
    # 卷毛簇（多小球）
    for i in range(6):
        tuft = gl.mesh(wool_c, radius=0.07, sections=6, geom="sphere")
        a = i * 2 * np.pi / 6
        tuft.apply_translation([0.19 * np.cos(a), 0.33, 0.14 * np.sin(a)])
        parts.append((f"tuft{i}", tuft))
    # 黑/灰脸
    head = gl.mesh(face_c, radius=0.075, sections=8, geom="sphere")
    head.apply_translation([0, 0.38, 0.20])
    parts.append(("head", head))
    for side in (-1, 1):
        ear = gl.mesh(face_c, extents=(0.04, 0.025, 0.03), geom="box")
        ear.apply_translation([0.06 * side, 0.44, 0.18])
        parts.append((f"ear{side}", ear))
    # 眼睛（黑脸上用小白点）
    for side in (-1, 1):
        eye = gl.mesh(gl.C("white"), radius=0.012, sections=6, geom="sphere")
        eye.apply_translation([0.035 * side, 0.40, 0.27])
        parts.append((f"eye{side}", eye))
    # 短腿
    for side in (-1, 1):
        for fb in (-1, 1):
            leg = gl.mesh(face_c, radius=0.022, height=0.11, sections=6, geom="cylinder")
            leg.apply_translation([0.10 * side, 0.055, 0.10 * fb])
            parts.append((f"leg{side}_{fb}", leg))
    return parts


def gen_pig_piglet(seed=11):
    """猪仔：小体型、粉嫩、圆鼻、大耳朵、小卷尾"""
    rng = gl.rng_from_seed(seed)
    pink_c = gl.jitter(gl.C("pink"), 0.04, rng)
    parts = []
    body = gl.mesh(pink_c, radius=0.15, sections=10, geom="sphere")
    body.apply_scale([1.35, 0.82, 1.05])
    body.apply_translation([0, 0.21, 0])
    parts.append(("body", body))
    head = gl.mesh(pink_c, radius=0.09, sections=8, geom="sphere")
    head.apply_translation([0, 0.27, 0.17])
    parts.append(("head", head))
    # 圆鼻
    snout = gl.mesh(_j(gl.C("pink"), 0.03, rng), extents=(0.08, 0.055, 0.045), geom="box")
    snout.apply_translation([0, 0.24, 0.27])
    parts.append(("snout", snout))
    for side in (-1, 1):
        nostril = gl.mesh(gl.C("black"), radius=0.008, sections=6, geom="sphere")
        nostril.apply_translation([0.018 * side, 0.245, 0.30])
        parts.append((f"nostril{side}", nostril))
    # 大耳朵
    for side in (-1, 1):
        ear = gl.mesh(pink_c, extents=(0.06, 0.04, 0.025), geom="box")
        ear.apply_translation([0.07 * side, 0.36, 0.15])
        ear.apply_transform(trimesh.transformations.rotation_matrix(np.radians(25 * side), [0, 0, 1], [0, 0, 0]))
        parts.append((f"ear{side}", ear))
    # 眼睛
    _eyes(parts, 0.30, 0.22, x_off=0.045, r=0.011)
    # 短腿
    for side in (-1, 1):
        for fb in (-1, 1):
            leg = gl.mesh(pink_c, radius=0.024, height=0.10, sections=6, geom="cylinder")
            leg.apply_translation([0.10 * side, 0.05, 0.09 * fb])
            parts.append((f"leg{side}_{fb}", leg))
    # 小卷尾（一小段翘起）
    tail = gl.mesh(pink_c, radius=0.016, height=0.05, sections=6, geom="cylinder")
    tail.apply_translation([0, 0.30, -0.16])
    tail.apply_transform(trimesh.transformations.rotation_matrix(np.radians(60), [1, 0, 0], [0, 0, 0]))
    parts.append(("tail", tail))
    return parts


# ================ 注册表 ================

GENERATORS = {
    "lifecycle_duck_egg": gen_duck_egg,
    "lifecycle_duck_baby": gen_duck_baby,
    "lifecycle_duck_adult": gen_duck_adult,
    "lifecycle_goose_egg": gen_goose_egg,
    "lifecycle_goose_baby": gen_goose_baby,
    "lifecycle_goose_adult": gen_goose_adult,
    "lifecycle_chicken_baby": gen_chicken_baby,
    "lifecycle_chicken_egg_brown": gen_chicken_egg_brown,
    "lifecycle_cow_calf": gen_cow_calf,
    "lifecycle_sheep_lamb": gen_sheep_lamb,
    "lifecycle_pig_piglet": gen_pig_piglet,
}

# 碰撞（sphere 半径 ≈ 体型，已按 SCALE 折算）
COLLISION = {
    "lifecycle_duck_egg": {"type": "dynamic", "shape": "sphere", "params": {"r": 0.05}},
    "lifecycle_duck_baby": {"type": "dynamic", "shape": "sphere", "params": {"r": 0.18}},
    "lifecycle_duck_adult": {"type": "dynamic", "shape": "sphere", "params": {"r": 0.30}},
    "lifecycle_goose_egg": {"type": "dynamic", "shape": "sphere", "params": {"r": 0.055}},
    "lifecycle_goose_baby": {"type": "dynamic", "shape": "sphere", "params": {"r": 0.20}},
    "lifecycle_goose_adult": {"type": "dynamic", "shape": "sphere", "params": {"r": 0.36}},
    "lifecycle_chicken_baby": {"type": "dynamic", "shape": "sphere", "params": {"r": 0.16}},
    "lifecycle_chicken_egg_brown": {"type": "dynamic", "shape": "sphere", "params": {"r": 0.04}},
    "lifecycle_cow_calf": {"type": "dynamic", "shape": "sphere", "params": {"r": 0.42}},
    "lifecycle_sheep_lamb": {"type": "dynamic", "shape": "sphere", "params": {"r": 0.31}},
    "lifecycle_pig_piglet": {"type": "dynamic", "shape": "sphere", "params": {"r": 0.23}},
}

# 每资产整体缩放：把基础尺寸校正到目标规格（锚点=底部中心，绕原点缩放不破坏锚点）
# 目标：蛋 0.06-0.12m、幼年 0.3-0.5m、成年鸭/鹅 0.6-0.9m、牛犊 0.8m、羊羔 0.5m、猪仔 0.4m
SCALE = {
    "lifecycle_duck_egg": 1.0,          # 0.116m ✓
    "lifecycle_duck_baby": 1.0,         # 0.402m ✓
    "lifecycle_duck_adult": 1.0,        # 0.695m ✓
    "lifecycle_goose_egg": 0.85,        # 0.137 → 0.116m ✓
    "lifecycle_goose_baby": 1.0,        # 0.427m ✓
    "lifecycle_goose_adult": 1.0,       # 0.884m ✓
    "lifecycle_chicken_baby": 1.0,      # 0.420m ✓
    "lifecycle_chicken_egg_brown": 1.0, # 0.088m ✓
    "lifecycle_cow_calf": 1.40,         # 0.567 → 0.79m ✓
    "lifecycle_sheep_lamb": 1.20,       # 0.419 → 0.50m ✓
    "lifecycle_pig_piglet": 1.10,       # 0.357 → 0.39m ✓
}

NAMES = {
    "lifecycle_duck_egg": "鸭蛋",
    "lifecycle_duck_baby": "小鸭（幼年）",
    "lifecycle_duck_adult": "成年鸭",
    "lifecycle_goose_egg": "鹅蛋",
    "lifecycle_goose_baby": "小鹅（幼年）",
    "lifecycle_goose_adult": "成年鹅",
    "lifecycle_chicken_baby": "小鸡（幼年）",
    "lifecycle_chicken_egg_brown": "褐壳鸡蛋",
    "lifecycle_cow_calf": "牛犊（幼年）",
    "lifecycle_sheep_lamb": "羊羔（幼年）",
    "lifecycle_pig_piglet": "猪仔（幼年）",
}

DESCS = {
    "lifecycle_duck_egg": "养殖生命周期：鸭蛋",
    "lifecycle_duck_baby": "养殖生命周期：小鸭（幼年）",
    "lifecycle_duck_adult": "养殖生命周期：成年鸭",
    "lifecycle_goose_egg": "养殖生命周期：鹅蛋",
    "lifecycle_goose_baby": "养殖生命周期：小鹅（幼年）",
    "lifecycle_goose_adult": "养殖生命周期：成年鹅",
    "lifecycle_chicken_baby": "养殖生命周期：小鸡（幼年）",
    "lifecycle_chicken_egg_brown": "养殖生命周期：褐壳鸡蛋",
    "lifecycle_cow_calf": "养殖生命周期：牛犊（幼年）",
    "lifecycle_sheep_lamb": "养殖生命周期：羊羔（幼年）",
    "lifecycle_pig_piglet": "养殖生命周期：猪仔（幼年）",
}


def generate(assets_dir=None, verify=True):
    """生成全部 11 个生命周期 GLB 并验证"""
    if assets_dir is None:
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(BASE)), "assets")
    out_dir = os.path.join(assets_dir, "lifecycle")
    os.makedirs(out_dir, exist_ok=True)
    results = {}
    for aid, fn in GENERATORS.items():
        parts = fn()
        s = SCALE.get(aid, 1.0)
        if s != 1.0:
            for _, m in parts:
                m.apply_scale(s)
        # 锚点归零：整体平移使最低 y = 0（无论正负都校正到 0）
        min_y = min(m.bounds[0][1] for _, m in parts)
        if abs(min_y) > 1e-6:
            for _, m in parts:
                m.apply_translation([0, -min_y, 0])
        path = os.path.join(out_dir, f"{aid}.glb")
        gl.export_scene(parts, path)
        size_kb = os.path.getsize(path) / 1024
        results[aid] = {"path": path, "sizeKB": round(size_kb, 1), "parts": len(parts)}
        if verify:
            ok = verify_glb(path)
            results[aid]["verify"] = ok
            print(f"  {'✔' if ok else '✘'} {aid} ({size_kb:.1f} KB, {len(parts)} parts)")
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
    generate()
