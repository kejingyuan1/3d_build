# -*- coding: utf-8 -*-
"""
批量生成入口：产出全部 GLB 资产 + assets/manifest.json（含碰撞体配置）
用法: python batch_generate.py
"""
import os
import json
import sys
import importlib.util

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))  # 项目根
sys.path.insert(0, BASE)

import gen_lib as gl
import gen_plants as plants
import gen_fish as fish
import gen_animals as animals
import gen_props as props
import gen_buildings as buildings

ASSETS_DIR = os.path.join(ROOT, "assets")
SUBDIRS = {
    "plants": "plants", "animals": "animals", "fish": "fish",
    "buildings": "buildings", "props": "props",
}

# ---------------- 资产注册表（id -> (生成函数, 子目录, 碰撞配置, 元数据)） ----------------
# 碰撞配置遵循工程约定: {type: fixed|dynamic|kinematic, shape: box|sphere|capsule|cylinder, params: {...}}
REGISTRY = []


def register(asset_id, gen_fn, subdir, collision, category, priority, name, desc="", animations=None, extra=None):
    REGISTRY.append({
        "id": asset_id,
        "gen": gen_fn,
        "subdir": subdir,
        "collision": collision,
        "category": category,
        "priority": priority,
        "name": name,
        "desc": desc,
        "animations": animations or [],
        "extra": extra or {},
    })


# ================ 植物 P0/P1 ================
for i, (name, stage) in enumerate([("seed", "seed"), ("seedling", "seedling"), ("mature", "mature")]):
    register(f"plant_wheat_{name}", lambda s=i: plants.gen_wheat(seed=1, stage=["seed","seedling","mature"][s]),
             "plants",
             {"type": "fixed", "shape": "box", "params": {"hx": 0.05, "hy": 0.1, "hz": 0.05}} if stage == "mature" else {"type": "none"},
             "plant", "P0", f"小麦-{stage}", "种植作物，3阶段生长", animations=["sway"] if stage == "mature" else [])
for i, (name, stage) in enumerate([("seed", "seed"), ("seedling", "seedling"), ("mature", "mature")]):
    register(f"plant_carrot_{name}", lambda s=i: plants.gen_carrot(seed=1, stage=["seed","seedling","mature"][s]),
             "plants",
             {"type": "fixed", "shape": "cylinder", "params": {"r": 0.05, "h": 0.25}} if stage == "mature" else {"type": "none"},
             "plant", "P0", f"胡萝卜-{stage}", "种植作物，3阶段生长", animations=["sway"] if stage == "mature" else [])
register("plant_tomato", lambda: plants.gen_tomato(seed=1), "plants",
         {"type": "fixed", "shape": "cylinder", "params": {"r": 0.12, "h": 0.3}}, "plant", "P1", "番茄", "P1作物")
register("plant_pumpkin", lambda: plants.gen_pumpkin(seed=1), "plants",
         {"type": "fixed", "shape": "sphere", "params": {"r": 0.22}}, "plant", "P1", "南瓜", "P1作物")
for kind in ("oak", "apple"):
    register(f"plant_tree_{kind}", lambda k=kind: plants.gen_tree(seed=1, kind=k), "plants",
             {"type": "fixed", "shape": "cylinder", "params": {"r": 0.08, "h": 1.0}}, "plant", "P0" if kind=="oak" else "P1",
             f"{'基础树' if kind=='oak' else '苹果树'}", "装饰+障碍/果树", animations=["sway"])
register("plant_flower_daisy", lambda: plants.gen_flower(seed=1, kind="daisy"), "plants",
         {"type": "none"}, "plant", "P1", "雏菊", "装饰")
register("plant_tilled_soil", lambda: plants.gen_tilled_soil(seed=1), "plants",
         {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 0.03, "hz": 0.5}}, "plant", "P0", "耕地地块", "锄地生成")

# ================ 动物 P0/P1 ================
register("animal_chicken_white", lambda: animals.gen_chicken(seed=1, color="white"), "animals",
         {"type": "dynamic", "shape": "capsule", "params": {"r": 0.15, "half_h": 0.2}}, "animal", "P0", "白鸡",
         "产蛋，投喂", animations=["idle", "walk", "eat", "peck"])
register("animal_chicken_brown", lambda: animals.gen_chicken(seed=2, color="brown"), "animals",
         {"type": "dynamic", "shape": "capsule", "params": {"r": 0.15, "half_h": 0.2}}, "animal", "P0", "棕鸡", "鸡变体",
         animations=["idle", "walk", "eat", "peck"])
register("animal_cow_holstein", lambda: animals.gen_cow(seed=1, color="holstein"), "animals",
         {"type": "dynamic", "shape": "capsule", "params": {"r": 0.35, "half_h": 0.55}}, "animal", "P0", "荷斯坦牛",
         "产奶，投喂", animations=["idle", "walk", "eat"])
register("animal_cow_brown", lambda: animals.gen_cow(seed=2, color="brown"), "animals",
         {"type": "dynamic", "shape": "capsule", "params": {"r": 0.35, "half_h": 0.55}}, "animal", "P1", "棕牛", "牛变体",
         animations=["idle", "walk", "eat"])
register("animal_sheep", lambda: animals.gen_sheep(seed=1), "animals",
         {"type": "dynamic", "shape": "capsule", "params": {"r": 0.25, "half_h": 0.35}}, "animal", "P1", "羊",
         "产羊毛", animations=["idle", "walk", "eat"])
register("animal_pig", lambda: animals.gen_pig(seed=1), "animals",
         {"type": "dynamic", "shape": "capsule", "params": {"r": 0.22, "half_h": 0.3}}, "animal", "P1", "猪",
         "增重出售", animations=["idle", "walk", "eat"])

# ================ 鱼类 P0/P1 ================
fish_specs = {
    "fish_carp": (fish.gen_carp, "鲤鱼", "P0", {"type": "dynamic", "shape": "capsule", "params": {"r": 0.1, "half_h": 0.25}}),
    "fish_bass": (fish.gen_bass, "鲈鱼", "P0", {"type": "dynamic", "shape": "capsule", "params": {"r": 0.09, "half_h": 0.22}}),
    "fish_trout": (fish.gen_trout, "鳟鱼", "P1", {"type": "dynamic", "shape": "capsule", "params": {"r": 0.09, "half_h": 0.22}}),
    "fish_tilapia": (fish.gen_tilapia, "罗非鱼", "P1", {"type": "dynamic", "shape": "capsule", "params": {"r": 0.09, "half_h": 0.2}}),
    "fish_catfish": (fish.gen_catfish, "鲶鱼", "P1", {"type": "dynamic", "shape": "capsule", "params": {"r": 0.11, "half_h": 0.26}}),
    "fish_grass_carp": (fish.gen_grass_carp, "草鱼", "P2", {"type": "dynamic", "shape": "capsule", "params": {"r": 0.1, "half_h": 0.25}}),
}
for fid, (fn, cn, pri, col) in fish_specs.items():
    register(fid, fn, "fish", col, "fish", pri, cn, "垂钓/养殖", animations=["swim"])

# ================ 道具 P0/P1 ================
props_specs = {
    "prop_egg": (props.gen_egg, "鸡蛋", "P0", {"type": "dynamic", "shape": "sphere", "params": {"r": 0.035}}),
    "prop_milk": (props.gen_milk, "牛奶", "P0", {"type": "dynamic", "shape": "cylinder", "params": {"r": 0.05, "h": 0.16}}),
    "prop_feed": (props.gen_feed, "饲料", "P0", {"type": "dynamic", "shape": "cylinder", "params": {"r": 0.16, "h": 0.3}}),
    "prop_basket": (props.gen_basket, "篮子", "P0", {"type": "dynamic", "shape": "cylinder", "params": {"r": 0.13, "h": 0.12}}),
    "prop_hoe": (props.gen_hoe, "锄头", "P0", {"type": "none"}),
    "prop_watering_can": (props.gen_watering_can, "水壶", "P0", {"type": "none"}),
    "prop_fishing_rod": (props.gen_fishing_rod, "鱼竿", "P0", {"type": "none"}),
    "prop_scythe": (props.gen_scythe, "镰刀", "P0", {"type": "none"}),
    "prop_shipping_box": (props.gen_shipping_box, "出货箱", "P0", {"type": "fixed", "shape": "box", "params": {"hx": 0.25, "hy": 0.35, "hz": 0.25}}),
    "prop_fence": (props.gen_fence_segment, "围栏段", "P0", {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 0.45, "hz": 0.05}}),
}
for pid, (fn, cn, pri, col) in props_specs.items():
    register(pid, fn, "props", col, "prop", pri, cn, "")

# ================ 建筑 P0/P1（v3 精细版，带门交互配置） ================
build_specs = {
    "building_farmhouse": (buildings.gen_farmhouse, "农舍", "P0", {"type": "fixed", "shape": "box", "params": {"hx": 1.3, "hy": 0.8, "hz": 1.1}},
                           {"doors": [{"name": "door", "hinge": "left", "angle": 110}]}),
    "building_coop": (buildings.gen_coop, "鸡舍", "P0", {"type": "fixed", "shape": "box", "params": {"hx": 0.9, "hy": 0.6, "hz": 0.75}},
                      {"doors": [{"name": "door", "hinge": "left", "angle": 110}]}),
    "building_barn": (buildings.gen_barn, "牛棚", "P0", {"type": "fixed", "shape": "box", "params": {"hx": 1.3, "hy": 0.8, "hz": 1.1}},
                      {"doors": [{"name": "bdoor_l", "hinge": "left", "angle": 100}, {"name": "bdoor_r", "hinge": "right", "angle": -100}]}),
    "building_well": (buildings.gen_well, "水井", "P1", {"type": "fixed", "shape": "cylinder", "params": {"r": 0.32, "h": 0.4}}, {}),
}
for bid, (fn, cn, pri, col, interact) in build_specs.items():
    register(bid, fn, "buildings", col, "building", pri, cn, "", extra=interact)

# ================ 家具（室内布局） ================
furn_specs = {
    "furn_bed": (props.gen_furn_bed, "床", "P0", {"type": "fixed", "shape": "box", "params": {"hx": 0.45, "hy": 0.25, "hz": 0.95}}),
    "furn_table": (props.gen_furn_table, "木桌", "P0", {"type": "fixed", "shape": "box", "params": {"hx": 0.6, "hy": 0.36, "hz": 0.35}}),
    "furn_chair": (props.gen_furn_chair, "椅子", "P0", {"type": "fixed", "shape": "box", "params": {"hx": 0.22, "hy": 0.45, "hz": 0.22}}),
    "furn_cabinet": (props.gen_furn_cabinet, "储物柜", "P0", {"type": "fixed", "shape": "box", "params": {"hx": 0.45, "hy": 0.7, "hz": 0.25}}),
    "furn_stove": (props.gen_furn_stove, "炉灶", "P0", {"type": "fixed", "shape": "box", "params": {"hx": 0.4, "hy": 0.45, "hz": 0.3}}),
    "furn_bookshelf": (props.gen_furn_bookshelf, "书架", "P0", {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 0.7, "hz": 0.15}}),
    "furn_lamp": (props.gen_furn_lamp, "台灯", "P0", {"type": "fixed", "shape": "cylinder", "params": {"r": 0.12, "h": 0.6}}),
    "furn_rug": (props.gen_furn_rug, "地毯", "P0", {"type": "fixed", "shape": "cylinder", "params": {"r": 0.7, "h": 0.02}}),
    "furn_sofa": (props.gen_furn_sofa, "沙发", "P1", {"type": "fixed", "shape": "box", "params": {"hx": 0.8, "hy": 0.4, "hz": 0.35}}),
    "furn_workbench": (props.gen_furn_workbench, "工作台", "P1", {"type": "fixed", "shape": "box", "params": {"hx": 0.65, "hy": 0.4, "hz": 0.35}}),
}
for fid, (fn, cn, pri, col) in furn_specs.items():
    register(fid, fn, "buildings", col, "furniture", pri, cn, "")

# ================ 环境 P0/P1 ================
register("terrain_grass", lambda: props.gen_terrain_tile(seed=1), "props",
         {"type": "fixed", "shape": "box", "params": {"hx": 0.5, "hy": 0.05, "hz": 0.5}}, "terrain", "P0", "草地地块")
register("terrain_rock", lambda: props.gen_rock(seed=1), "props",
         {"type": "fixed", "shape": "sphere", "params": {"r": 0.25}}, "terrain", "P0", "石头")
register("terrain_grass_tuft", lambda: props.gen_grass_tuft(seed=1), "props",
         {"type": "none"}, "terrain", "P1", "草丛")


def generate_all():
    """生成全部资产 + manifest"""
    manifest = {"schemaVersion": 1, "generatedAt": "2026-08-05T00:00:00Z", "assetRoot": "assets", "assets": []}
    stats = {"P0": 0, "P1": 0, "P2": 0}
    for reg in REGISTRY:
        parts = reg["gen"]()
        if not parts:
            print(f"  !! {reg['id']} 无部件，跳过")
            continue
        rel_dir = SUBDIRS[reg["subdir"]]
        out_dir = os.path.join(ASSETS_DIR, rel_dir)
        os.makedirs(out_dir, exist_ok=True)
        glb_path = os.path.join(out_dir, f"{reg['id']}.glb")
        gl.export_scene(parts, glb_path)
        size_kb = os.path.getsize(glb_path) / 1024
        stats[reg["priority"]] = stats.get(reg["priority"], 0) + 1
        asset_entry = {
            "assetId": reg["id"],
            "designId": reg["extra"].get("designId", reg["id"]),
            "path": f"{rel_dir}/{reg['id']}.glb",
            "category": reg["category"],
            "priority": reg["priority"],
            "name": reg["name"],
            "desc": reg["desc"],
            "collision": reg["collision"],
            "animations": reg["animations"],
            "lodLevels": [{"level": 0, "path": f"{rel_dir}/{reg['id']}.glb"}],
            "sizeKB": round(size_kb, 1),
            "loadPriority": 0 if reg["priority"] == "P0" else (1 if reg["priority"] == "P1" else 2),
        }
        # 附加交互配置（如门的开关）
        if reg["extra"].get("doors"):
            asset_entry["interactions"] = {
                "doors": reg["extra"]["doors"]
            }
        manifest["assets"].append(asset_entry)
        print(f"  ✔ {reg['id']} ({size_kb:.1f} KB)")
    # 写 manifest
    manifest_path = os.path.join(ASSETS_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\n===== 完成 =====")
    print(f"总资产: {len(REGISTRY)} 个 | P0:{stats['P0']} P1:{stats['P1']} P2:{stats['P2']}")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    generate_all()
