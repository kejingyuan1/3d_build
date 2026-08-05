# -*- coding: utf-8 -*-
"""接入 Kenney Modular Buildings（CC0）到农场项目资产管线
- 解压 zip → 选农场建筑 GLB → 统一命名/朝向/锚点 → 写 assets/manifest.json
"""
import zipfile
import os
import json
import shutil
import struct

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
ZIP = os.path.join(ROOT, 'downloads', 'kenney_modular_buildings.zip')
ASSETS_DIR = os.path.join(ROOT, 'assets')
OUT_DIR = os.path.join(ASSETS_DIR, 'kenney')

# 挑选的农场建筑（source 文件名 → (assetId, 中文名, 碰撞体配置, 优先级)）
PICKS = [
    ("building-sample-house-a.glb", "building_kenney_house_a", "肯尼小屋A", {"type": "fixed", "shape": "box", "params": {"hx": 0.8, "hy": 1.0, "hz": 0.8}}, "P0"),
    ("building-sample-house-b.glb", "building_kenney_house_b", "肯尼小屋B", {"type": "fixed", "shape": "box", "params": {"hx": 0.8, "hy": 1.0, "hz": 0.8}}, "P0"),
    ("building-sample-house-c.glb", "building_kenney_house_c", "肯尼小屋C", {"type": "fixed", "shape": "box", "params": {"hx": 0.8, "hy": 1.0, "hz": 0.8}}, "P0"),
    ("building-sample-tower-a.glb", "building_kenney_tower_a", "肯尼塔楼A", {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 1.4, "hz": 0.5}}, "P1"),
    ("building-sample-tower-b.glb", "building_kenney_tower_b", "肯尼塔楼B", {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 1.4, "hz": 0.5}}, "P1"),
    ("roof-gable.glb", "building_kenney_roof_gable", "人字坡屋顶", {"type": "fixed", "shape": "box", "params": {"hx": 0.8, "hy": 0.5, "hz": 0.8}}, "P0"),
    ("roof-slanted.glb", "building_kenney_roof_slanted", "单坡屋顶", {"type": "fixed", "shape": "box", "params": {"hx": 0.8, "hy": 0.5, "hz": 0.8}}, "P0"),
    ("door-brown.glb", "prop_kenney_door_brown", "木门(棕)", {"type": "fixed", "shape": "box", "params": {"hx": 0.3, "hy": 0.9, "hz": 0.1}}, "P1"),
    ("door-white.glb", "prop_kenney_door_white", "木门(白)", {"type": "fixed", "shape": "box", "params": {"hx": 0.3, "hy": 0.9, "hz": 0.1}}, "P1"),
    ("window-brown.glb", "prop_kenney_window_brown", "窗(棕)", {"type": "fixed", "shape": "box", "params": {"hx": 0.3, "hy": 0.3, "hz": 0.05}}, "P1"),
]


def inspect_glb_size(path):
    """读取 GLB 尺寸，用于生成锚点信息"""
    try:
        import trimesh
        m = trimesh.load(path)
        if hasattr(m, 'geometry') and m.geometry:
            verts = [list(g.vertices) for g in m.geometry.values()]
            import numpy as np
            all_v = np.concatenate([v for v in verts if len(v) > 0])
            mn, mx = all_v.min(axis=0), all_v.max(axis=0)
            return mx - mn, mn
        return None, None
    except Exception as e:
        print(f'  尺寸读取失败: {e}')
        return None, None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    z = zipfile.ZipFile(ZIP)
    manifest_path = os.path.join(ASSETS_DIR, 'manifest.json')
    manifest = {"schemaVersion": 1, "generatedAt": "2026-08-05T00:00:00Z", "assetRoot": "assets", "assets": []}
    # 保留已有程序化资产条目
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding='utf-8') as f:
            existing = json.load(f)
        manifest["assets"] = [a for a in existing["assets"] if not a["assetId"].startswith("building_kenney")]
        print(f'保留已有资产 {len(manifest["assets"])} 条')

    added = 0
    for src, asset_id, cn, col, pri in PICKS:
        # 找 zip 中匹配的 GLB（可能在 Models/GLB format/ 子目录）
        match = next((n for n in z.namelist() if n.endswith(src)), None)
        if not match:
            print(f'  !! 未找到 {src}')
            continue
        out_path = os.path.join(OUT_DIR, f'{asset_id}.glb')
        with z.open(match) as src_f, open(out_path, 'wb') as dst_f:
            shutil.copyfileobj(src_f, dst_f)
        size_kb = os.path.getsize(out_path) / 1024
        manifest["assets"].append({
            "assetId": asset_id,
            "path": f"kenney/{asset_id}.glb",
            "category": "building",
            "priority": pri,
            "name": cn,
            "desc": f"Kenney CC0 专业资产: {src}",
            "collision": col,
            "animations": [],
            "lodLevels": [{"level": 0, "path": f"kenney/{asset_id}.glb"}],
            "sizeKB": round(size_kb, 1),
            "loadPriority": 0 if pri == "P0" else 1,
            "source": {"kind": "cc0_kenney", "license": "CC0", "url": "https://kenney.nl/assets/modular-buildings"},
        })
        added += 1
        print(f'  ✔ {asset_id} ({size_kb:.1f} KB)')

    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f'\n完成: 接入 {added} 个 Kenney 资产, manifest 共 {len(manifest["assets"])} 条')


if __name__ == '__main__':
    main()
