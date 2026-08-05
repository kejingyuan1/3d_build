# -*- coding: utf-8 -*-
"""
更新养殖生命周期注册表：assets/manifest.json + preview.html（内嵌 manifest + LAYOUT）
用法: python update_lifecycle_manifest.py
"""
import os
import sys
import json
import re
import struct

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
sys.path.insert(0, BASE)

import gen_lifecycle as g

ASSETS = os.path.join(ROOT, "assets")
MANIFEST_PATH = os.path.join(ASSETS, "manifest.json")
PREVIEW_PATH = os.path.join(ROOT, "preview.html")

IDS = list(g.GENERATORS.keys())  # 11 个


def read_glb_size_kb(aid):
    path = os.path.join(ASSETS, "lifecycle", f"{aid}.glb")
    return round(os.path.getsize(path) / 1024, 1)


def build_entry(aid, preview=False):
    sub = "lifecycle"
    rel = f"{sub}/{aid}.glb"
    path = f"assets/{rel}" if preview else rel
    n = list(g.GENERATORS.keys()).index(aid) + 1
    entry = {
        "assetId": aid,
        "designId": f"LC-{n:02d}",
        "path": path,
        "category": "animal",
        "priority": "P0",
        "name": g.NAMES[aid],
        "desc": g.DESCS[aid],
        "source": "procedural",
    }
    if not preview:
        entry["collision"] = g.COLLISION[aid]
        entry["animations"] = []
        entry["lodLevels"] = [{"level": 0, "path": rel}]
        entry["sizeKB"] = read_glb_size_kb(aid)
        entry["loadPriority"] = 0
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

    # ---- 1. 内嵌 manifest：解析 JSON，插入 11 条，回写 ----
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

    # ---- 2. LAYOUT：z=10 行，x 从 -8 到 8 排开（蛋摆小：位置错开、按序号递增）----
    # 11 个资产，x = -8 + i*1.6（i=0..10）：-8,-6.4,-4.8,-3.2,-1.6,0,1.6,3.2,4.8,6.4,8
    lines = []
    for i, aid in enumerate(IDS):
        x = round(-8 + i * 1.6, 1)
        rot = 0
        lines.append(f"  [{x}, 10, {rot}, '{aid}', 'animal'],")
    block = "\n  // 养殖生命周期（蛋→幼年→成熟，z=10 行）\n" + "\n".join(lines) + "\n"
    # 在 LAYOUT 数组结束 `];` 前插入；锚点取 "// 农舍室内家具" 前的 `];`
    anchor = "\n];\n\n// 农舍室内家具"
    if anchor in html:
        html = html.replace(anchor, "\n" + block.rstrip("\n") + "\n];\n\n// 农舍室内家具", 1)
    else:
        raise RuntimeError("preview.html 未找到 LAYOUT 闭合锚点")

    open(PREVIEW_PATH, "w", encoding="utf-8").write(html)
    print(f"preview.html: 内嵌 manifest 新增 {added} 条 + LAYOUT 新增 {len(IDS)} 个")


if __name__ == "__main__":
    update_manifest()
    update_preview()
    print("完成")
