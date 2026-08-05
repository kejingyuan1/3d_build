# -*- coding: utf-8 -*-
"""
更新升级链建筑注册表：assets/manifest.json + preview.html（内嵌 manifest + LAYOUT）
用法: python update_upgrade_manifest.py
"""
import os
import json
import re
import struct

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))

sys_path = os.path.join(BASE)
import sys
sys.path.insert(0, sys_path)
import gen_upgrade_buildings as g

ASSETS = os.path.join(ROOT, "assets")
MANIFEST_PATH = os.path.join(ASSETS, "manifest.json")
PREVIEW_PATH = os.path.join(ROOT, "preview.html")

IDS = [f"building_upgrade_l{i}" for i in range(1, 6)]


def read_glb_size_kb(aid):
    path = os.path.join(ASSETS, "upgrade_buildings", f"{aid}.glb")
    return round(os.path.getsize(path) / 1024, 1)


def build_entry(aid, preview=False):
    """构建 manifest 条目；preview=True 时 path 带 assets/ 前缀"""
    sub = "upgrade_buildings"
    rel = f"{sub}/{aid}.glb"
    path = f"assets/{rel}" if preview else rel
    entry = {
        "assetId": aid,
        "designId": f"UPG-{aid[-1]}",
        "path": path,
        "category": "building",
        "priority": "P0",
        "name": g.NAMES[aid],
        "desc": g.DESCS[aid],
    }
    if not preview:
        entry["collision"] = g.COLLISION[aid]
        entry["animations"] = []
        entry["lodLevels"] = [{"level": 0, "path": rel}]
        entry["sizeKB"] = read_glb_size_kb(aid)
        entry["loadPriority"] = 0
    entry["interactions"] = {"doors": g.DOOR_CFG[aid]}
    return entry


def update_manifest():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)
    existing = {a["assetId"] for a in manifest["assets"]}
    added = 0
    for aid in IDS:
        if aid in existing:
            print(f"  ~ {aid} 已存在，跳过")
            continue
        manifest["assets"].append(build_entry(aid))
        added += 1
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"manifest.json: 新增 {added} 条 -> {MANIFEST_PATH}")


def update_preview():
    html = open(PREVIEW_PATH, encoding="utf-8").read()

    # ---- 1. 内嵌 manifest：解析 JSON 数组，插入 5 条，回写 ----
    m = re.search(r'<script id="manifest-data"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("preview.html 未找到 manifest-data")
    data = json.loads(m.group(1))
    existing = {a["assetId"] for a in data["assets"]}
    added = 0
    for aid in IDS:
        if aid in existing:
            continue
        data["assets"].append(build_entry(aid, preview=True))
        added += 1
    new_json = json.dumps(data, ensure_ascii=False, indent=2)
    html = re.sub(r'<script id="manifest-data"[^>]*>.*?</script>',
                  lambda mm: mm.group(0)[:mm.group(0).index(">") + 1] + "\n" + new_json + "\n</script>",
                  html, count=1, flags=re.S)

    # ---- 2. LAYOUT：在数组闭合 `];` 前插入 5 个建筑（x=16 列，z -4..-16）----
    layout_lines = []
    for i in range(5):
        z = -4 - i * 3  # -4, -7, -10, -13, -16
        layout_lines.append(f"  [16, {z}, 0, 'building_upgrade_l{i+1}', 'building'],")
    block = "\n  // 升级链建筑（5 级，x=16 列）\n" + "\n".join(layout_lines) + "\n"
    # 在 LAYOUT 数组结束 `];` 前插入；锚点取 "// 农舍室内家具" 前的 `];`
    anchor = "\n];\n\n// 农舍室内家具"
    if anchor in html:
        html = html.replace(anchor, "\n" + block.rstrip("\n") + "\n];\n\n// 农舍室内家具", 1)
    else:
        raise RuntimeError("preview.html 未找到 LAYOUT 闭合锚点")

    open(PREVIEW_PATH, "w", encoding="utf-8").write(html)
    print(f"preview.html: 内嵌 manifest 新增 {added} 条 + LAYOUT 新增 5 个建筑")


if __name__ == "__main__":
    update_manifest()
    update_preview()
    print("完成")
