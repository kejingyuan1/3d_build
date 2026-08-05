# -*- coding: utf-8 -*-
"""
更新生长阶段 + 季节皮肤注册表：assets/manifest.json + preview.html（仅内嵌 manifest，不动 LAYOUT）
用法: python update_seasons_manifest.py
"""
import os
import sys
import json
import re

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
sys.path.insert(0, BASE)

import gen_seasons as g

ASSETS = os.path.join(ROOT, "assets")
MANIFEST_PATH = os.path.join(ASSETS, "manifest.json")
PREVIEW_PATH = os.path.join(ROOT, "preview.html")

IDS = g.all_ids()  # 22 个


def read_glb_size_kb(aid):
    sub = g.SUBDIR.get(aid, "plants")
    path = os.path.join(ASSETS, sub, f"{aid}.glb")
    return round(os.path.getsize(path) / 1024, 1)


def build_entry(aid, preview=False):
    sub = g.SUBDIR.get(aid, "plants")
    rel = f"{sub}/{aid}.glb"
    path = f"assets/{rel}" if preview else rel
    cat = "terrain" if aid.startswith("terrain_") else "plant"
    entry = {
        "assetId": aid,
        "designId": g.DESIGN_IDS[aid],
        "path": path,
        "category": cat,
        "priority": "P0" if "mature" in aid or "tree" in aid else "P1",
        "name": g.NAMES[aid],
        "desc": g.DESCS[aid],
        "source": "procedural",
    }
    if not preview:
        entry["collision"] = g.COLLISION[aid]
        entry["animations"] = ["sway"] if "tree" in aid else []
        entry["lodLevels"] = [{"level": 0, "path": rel}]
        entry["sizeKB"] = read_glb_size_kb(aid)
        entry["loadPriority"] = 0 if entry["priority"] == "P0" else 1
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
    open(PREVIEW_PATH, "w", encoding="utf-8").write(html)
    print(f"preview.html: 内嵌 manifest 新增 {added} 条（未动 LAYOUT）")


if __name__ == "__main__":
    update_manifest()
    update_preview()
    print("完成")
