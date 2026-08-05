# -*- coding: utf-8 -*-
"""
程序化 3D 资产生成器核心库
农场牧场网页游戏 · Three.js + Rapier
规范: 1单位=1米 / Y-up / +Z前向 / 锚点=脚底中心 / 卡通低模 / 顶点色
"""
import trimesh
import numpy as np

# ---------------- 调色板（美术圣经 §2） ----------------
PALETTE = {
    "grass":     (0x6B, 0xAF, 0x4E),  # 牧场绿
    "soil":      (0x8D, 0x6E, 0x63),  # 沃土棕
    "sky":       (0x7E, 0xC8, 0xE3),  # 天空蓝
    "wheat":     (0xF2, 0xC1, 0x4E),  # 麦穗黄
    "cream":     (0xF5, 0xEF, 0xE0),  # 奶油白
    "stone":     (0x9E, 0x9E, 0x9E),  # 石炭灰
    "tomato":    (0xE4, 0x57, 0x2E),  # 番茄红
    "blueberry": (0x4A, 0x6F, 0xA5),  # 蓝莓蓝
    "egg_yolk":  (0xFF, 0xD1, 0x66),  # 鸡蛋黄
    "ink":       (0x2F, 0x3E, 0x2E),  # 深墨绿
    "orange":    (0xE8, 0x9C, 0x3C),  # 橙
    "carrot":    (0xE8, 0x6A, 0x2C),  # 胡萝卜橙
    "pumpkin":   (0xD9, 0x6E, 0x3B),  # 南瓜橙
    "leaf_dark": (0x4C, 0x8A, 0x3A),  # 深叶绿
    "leaf_light":(0x8C, 0xC6, 0x5C),  # 浅叶绿
    "water":     (0x5B, 0xB4, 0xE4),  # 水体蓝
    "wood":      (0xA0, 0x7B, 0x4F),  # 原木棕
    "wood_dark": (0x7A, 0x5B, 0x3A),  # 深木棕
    "roof":      (0xC8, 0x4B, 0x3A),  # 屋顶红
    "pink":      (0xF4, 0xA9, 0xA9),  # 腮红/粉
    "white":     (0xF8, 0xF6, 0xF0),  # 白
    "black":     (0x3A, 0x3A, 0x3A),  # 黑(眼部)
    "gold":      (0xF0, 0xC4, 0x2E),  # 金
    "beak":      (0xE0, 0xA8, 0x3A),  # 喙黄
}


def C(name, alpha=255):
    """取调色板颜色为 RGBA 元组"""
    r, g, b = PALETTE[name]
    return (r, g, b, alpha)


def hex_to_rgb(h):
    return ((h >> 16) & 0xFF, (h >> 8) & 0xFF, h & 0xFF)


def jitter(color, amount=0.06, rng=None):
    """对颜色做轻微随机扰动（保证程序化变体风格统一但有个体差异）"""
    if rng is None:
        rng = np.random.default_rng()
    r, g, b = color[:3]
    d = lambda v: max(0, min(255, int(v * (1 + rng.uniform(-amount, amount)))))
    return (d(r), d(g), d(b), color[3] if len(color) > 3 else 255)


def _ensure_normals(m):
    """确保 mesh 有正确朝外的法线（Three.js 光照需要，否则全黑）"""
    if not m.visual.kind or m.visual.kind == 'none':
        pass
    try:
        m.fix_normals()
    except Exception:
        pass
    try:
        m.update_faces(m.valid_faces)
    except Exception:
        pass
    # 触发顶点法线缓存计算（trimesh 惰性计算 vertex_normals）
    if hasattr(m, 'vertex_normals') and len(m.vertex_normals) == 0:
        m.vertex_normals  # 触发
    return m


def mesh(color, *args, **kwargs):
    """创建带颜色的基础几何体"""
    m = kwargs.pop("geom", "box")
    if m == "box":
        obj = trimesh.creation.box(*args, **kwargs)
    elif m == "cylinder":
        obj = trimesh.creation.cylinder(*args, **kwargs)
    elif m == "capsule":
        obj = trimesh.creation.capsule(*args, **kwargs)
    elif m == "sphere":
        obj = trimesh.creation.icosphere(*args, **kwargs)
    elif m == "cone":
        obj = trimesh.creation.cone(*args, **kwargs)
    else:
        raise ValueError(f"unknown geom: {m}")
    _ensure_normals(obj)
    obj.visual = trimesh.visual.ColorVisuals(obj, vertex_colors=color)
    return obj


def export_scene(meshes, path):
    """
    导出 GLB。meshes: list of (name, trimesh.Trimesh)
    要求每个 mesh 已摆放在世界坐标（锚点=脚底中心落在 Y=0）
    """
    scene = trimesh.Scene()
    for name, m in meshes:
        # 导出前强制计算法线（trimesh 默认不写 NORMAL 属性，Three.js 会黑）
        _ensure_normals(m)
        scene.add_geometry(m, node_name=name, geom_name=name)
    scene.export(path)
    return path


def subdivide_smooth(m, iterations=1):
    return m.subdivide_smooth(iterations) if hasattr(m, "subdivide_smooth") else m


def concat(meshes):
    """合并多个 mesh 为一个（用于 LOD 简化）"""
    return trimesh.util.concatenate(meshes) if meshes else None


def rng_from_seed(seed):
    return np.random.default_rng(seed)
