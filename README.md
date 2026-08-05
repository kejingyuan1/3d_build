# 3D Build — 农场牧场游戏 3D 资产库

农场牧场网页游戏（Three.js + Rapier）的 3D 资产包。包含 **97+ 项资产**：建筑（含 5 级升级链）、动物（静态 + 动画版）、植物、鱼类、道具、家具，全部带碰撞体配置与门交互支持。

**来源**：CC0（Kenney / Quaternius）+ 程序化生成，商业可自由使用，归详见 `assets/manifest.json`。

---

## 目录结构

```
assets/
├── manifest.json              # 资产注册表（碰撞体/门交互/CC0 归属/优先级）
├── animals/                   # 程序化动物（鸡/牛/羊/猪）
├── buildings/                 # 程序化建筑（农舍/鸡舍/牛棚 + 10 件家具）
├── fish/                      # 程序化鱼类（鲤鱼/鲈鱼/鳟鱼/罗非鱼/鲶鱼/草鱼）
├── plants/                    # 程序化植物（小麦/胡萝卜/番茄/南瓜/树/花）
├── props/                     # 道具（工具/出货箱/围栏/蛋/奶/饲料）
├── kenney/                    # Kenney Modular Buildings（3 小屋 + 2 塔楼 + 2 屋顶 + 门/窗）
├── quaternius_glb/            # Quaternius 26 建筑（带贴图，亮色调色板）
├── quaternius_animals5_glb/   # Quaternius 5 野生动物（静态）
├── quaternius_farm_animals_glb/ # Quaternius 7 农场动物（静态）
├── quaternius_animated/       # ★ 动画版 GLB（12 个，FBX 转骨骼动画）
├── upgrade_buildings/         # ★ 5 级升级链建筑（L1 茅草屋 → L5 豪华庄园，带门）
└── quaternius_trees/          # Quaternius 45 棵树（Birch/Pine/DeadTree 等）
tools/asset_generator/         # 程序化生成器 + FBX→GLB 转换器
preview.html                   # Three.js 3D 预览（点击开门、旋转缩放）
```

---

## 一、快速开始（Three.js）

```html
<script type="importmap">
{ "imports": { "three": "https://unpkg.com/three@0.170.0/build/three.module.js",
               "three/addons/": "https://unpkg.com/three@0.170.0/examples/jsm/" } }
</script>
<script type="module">
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const loader = new GLTFLoader();
const gltf = await loader.loadAsync('assets/buildings/building_farmhouse.glb');
scene.add(gltf.scene);
</script>
```

> **GLB 规范**：1 单位 = 1 米 · Y 轴向上 · 正面朝 +Z · 锚点 = 底部中心。
> **注意**：程序化资产生成时用顶点色（sRGB），Three.js 侧读取首顶点色作为 `baseColor` 即可；带贴图资产（Quaternius）用 `MeshToonMaterial({ map })` 保留贴图。

---

## 二、怎么触发动作（重点）

### 1. 开门关门（5 级升级链 + 农舍/鸡舍/牛棚）

每栋建筑的 GLB 内都有**命名门节点**，manifest 的 `interactions.doors` 记录了铰链配置：

```jsonc
// assets/manifest.json
{
  "assetId": "building_upgrade_l3",
  "interactions": { "doors": [
    { "name": "door_panel", "hinge": "left", "angle": 110 }
  ]}
}
```

**触发代码**（绕 Y 轴旋转门，铰链在门左/右缘）：

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MathUtils } from 'three';

async function makeDoor(buildingAssetId, doorCfg) {
  const gltf = await loader.loadAsync(`assets/upgrade_buildings/${buildingAssetId}.glb`);
  const model = gltf.scene;

  // 1. 找门板节点（单门 door_panel；双开门 door_l / door_r）
  const panel = model.getObjectByName(doorCfg.name);

  // 2. 建铰链 pivot：位置 = 门的左缘（hinge=left）或右缘（hinge=right）
  const pivot = new THREE.Group();
  const box = new THREE.Box3().setFromObject(panel);
  const hingeX = doorCfg.hinge === 'left' ? box.min.x : box.max.x;
  pivot.position.set(hingeX, 0, box.min.z);

  // 3. 把门板挂到 pivot（门板本地坐标归零）
  panel.position.sub(pivot.position);
  pivot.add(panel);
  model.add(pivot);

  // 4. 开门：rotation.y = angle（右铰链取负）
  const dir = doorCfg.hinge === 'right' ? -1 : 1;
  pivot.rotation.y = MathUtils.degToRad(doorCfg.angle) * dir; // 开
  pivot.rotation.y = 0;                                        // 关

  return { model, pivot, open: false, toggle() { this.open = !this.open;
    this.pivot.rotation.y = this.open ? MathUtils.degToRad(doorCfg.angle) * dir : 0; } };
}

// 用法：点击事件里调 toggle
const door = await makeDoor('building_upgrade_l3', { name: 'door_panel', hinge: 'left', angle: 110 });
renderer.domElement.onclick = () => door.toggle();
```

**各建筑门配置速查**：

| 建筑 | 门节点 | 铰链 | 开角 |
|------|--------|------|------|
| building_farmhouse / coop / barn（程序化） | `door` / `bdoor_l`+`bdoor_r` | left / 双开 | 110°/100° |
| building_upgrade_l1 / l2 / l3 | `door_panel` | left | 110° |
| building_upgrade_l4 / l5 | `door_l` + `door_r` | 左+右双开 | 100° |

### 2. 使用动画版 GLB（FBX 转骨骼动画）

`assets/quaternius_animated/` 下 12 个动画资产（牛/马/羊驼/猪/哈巴狗/羊/斑马/鸟/小鸡/鱼/红狐/鲸鱼），每个含 1-6 个动画 clip + 骨骼（skins=1）。**触发播放**：

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { AnimationMixer } from 'three';

const gltf = await loader.loadAsync('assets/quaternius_animated/farm_Cow_animated.glb');
const model = gltf.scene;

// AnimationMixer 驱动所有动画 clip
const mixer = new AnimationMixer(model);
const clips = gltf.animations;            // 例：Cow 有 6 个 clip（Cow_anim0..5）
clips.forEach((clip, i) => console.log(i, clip.name, clip.duration.toFixed(2) + 's'));

// 播放指定动作（如走路/待机/进食，按 clip 名选择）
const action = mixer.clipAction(clips[0]);
action.play();

// 每帧更新
function animate() {
  requestAnimationFrame(animate);
  mixer.update(deltaTime);   // 传入上一帧到现在的秒数
  renderer.render(scene, camera);
}
```

**动画 clip 分布**：Cow/Horse/Zebra 各 6 个（走路/跑/待机等）、Llama/Pig/Pug/Sheep/Whale 各 2 个、bird 3 个、Chick/Fish/Red Fox 各 1 个。播放前先打印 `clips` 确认每个 clip 对应的动作。

### 3. 升级链切换（L1 → L5）

5 级升级链建筑在 `assets/upgrade_buildings/building_upgrade_l{1..5}.glb`。升级 = 卸载旧建筑模型 + 加载下一级 + 开门动画：

```js
async function upgrade(currentLevel, position) {
  // 1. 移除当前级
  scene.remove(currentModel);

  // 2. 加载下一级（L1→L2→...→L5，尺寸递增：2.5m→6m）
  const nextLevel = currentLevel + 1;
  const gltf = await loader.loadAsync(
    `assets/upgrade_buildings/building_upgrade_l${nextLevel}.glb`);
  const model = gltf.scene;
  model.position.copy(position);
  scene.add(model);

  // 3. 开门（按 manifest 的 interactions.doors 配置）
  await openAllDoors(model, `building_upgrade_l${nextLevel}`);

  return { model, level: nextLevel };
}
```

---

## 三、物理碰撞（Rapier）

所有资产在 `manifest.json` 登记碰撞体：

```jsonc
"collision": {
  "type": "fixed" | "dynamic",
  "shape": "box" | "sphere" | "capsule" | "cylinder",
  "params": { "width": 2.2, "height": 3.0, "depth": 2.4 }
}
```

```js
import RAPIER from 'https://unpkg.com/@dimforge/rapier3d-compat/rapier.js';
await RAPIER.init();

// 从 manifest 取碰撞配置 → 建碰撞体
const entry = manifest.assets.find(a => a.assetId === 'building_upgrade_l3');
const c = entry.collision;
const body = world.createRigidBody(RAPIER.RigidBodyDesc[c.type === 'fixed' ? 'fixed' : 'dynamic']());
const collider = world.createCollider(
  RAPIER.ColliderDesc.cuboid(c.params.width/2, c.params.height/2, c.params.depth/2), body);
```

**Filter Group 分层建议**（详见 docs/architecture/technical-architecture.md §2.5）：

| 层 | 与谁碰撞 |
|----|---------|
| 玩家（KinematicCharacterController） | 地形/建筑/动物 |
| 动物（dynamic） | 地形/玩家 Sensor |
| 掉落物（dynamic） | 地形/玩家 |
| 工具命中（sensor） | 可交互物 |
| 交互 Sensor（sensor） | 玩家 |

---

## 四、门交互 + 动画 + 升级链 = 玩法循环示例

```js
// 玩家点击门 → 开门 → 进入建筑 → 内部升级 → 换 L 级建筑 → 开门迎接
```

完整可运行示例见 `preview.html`（点击门开关、下拉筛选分类、5 级升级链 L1-L5 排布展示）。

---

## 五、重新生成资产

```bash
# 程序化资产（动物/植物/鱼/道具/家具/建筑）
python tools/asset_generator/batch_generate.py

# 5 级升级链建筑
python tools/asset_generator/gen_upgrade_buildings.py
python tools/asset_generator/update_upgrade_manifest.py

# Quaternius 建筑（需先解压 zip 到 assets/quaternius/）
python tools/asset_generator/import_quaternius.py

# FBX → 动画 GLB（需要 Node + three）
node tools/asset_generator/fbx_to_glb.js <in.fbx> <out.glb>
```

---

## 六、文档

- `docs/architecture/technical-architecture.md` — Three.js + Rapier 架构、ADR、碰撞分层、性能预算
- `docs/architecture/asset-pipeline.md` — GLB 标准、生成器架构、验收清单
- `docs/art/art-bible.md` — 卡通美术圣经（调色板/Toon/比例/命名）
- `docs/art/asset-specs.md` — 资产规格规范（碰撞必填/CC0 流程/QA）
- `docs/art/animal-rebuild-spec.md` — **成年动物重建规格**（8 只动物逐只规格 + GLB 规范 + 蒙皮/动画 + 命名 + 验收清单）
- `ISSUES.md` — **已知问题 + 后续路线选项**（眼睛附体未根治、批量收尾待办、路线 A/B/C/D/E 决策）

---

## 七、成年动物重建进展（2026-08-06）

**用户决策**：放弃写实（MAXDESIGN 鸡 4.16MB 太重 + 与卡通环境撕裂）→ **卡通 + 顶点蒙皮**方向。体积小 6-50 倍、风格与仓库建筑/植物统一、自带骨骼动画（idle/walk/eat）无撕裂。

### 最新资产（`assets/animals/staging/`，5 只顶点蒙皮版 `_sk`）

| 文件 | 体积 | 高度 | 说明 |
|------|------|------|------|
| `animal_chicken_brown_sk.glb` | 85KB | 0.5m | 鸡（5 材质 + 顶点色 + 眼睛） |
| `animal_cow_brown_sk.glb` | 157KB | 1.5m | 牛（暖棕身/深褐腿 + 眼睛） |
| `lifecycle_duck_adult_sk.glb` | 84KB | 0.35m | 鸭（黑顶/白身/黄脚/橙喙 + 眼睛 + 头顶黑毛簇） |
| `lifecycle_goose_adult_sk.glb` | 75KB | 0.65m | 鹅（暖白/橙蹼 + 眼睛） |
| `animal_sheep_sk.glb` | 121KB | 0.75m | 羊（暖白/棕褐脸腿 + 眼睛） |

另有 `_b` 程序骨骼版（白鸡/棕牛/鹅/羊剪毛两态/猪）作对比兜底，`cc0_compress_test/` 为写实鸡压缩实验（废弃）。

### ⚠️ 已知问题（详见 ISSUES.md）

1. **眼睛/毛簇附体未根治**：head bone 与 head mesh 不重合（牛 z 差 21cm），眼睛/鸭头顶黑毛簇漂浮。已试 attach 到 head bone / root bone 两方案未彻底解决；兜底方案（眼睛作为 skinnedMesh 子 mesh 绑 skin 权重）待实施
2. **正式路径未替换**：`assets/animals/*.glb` 与 `assets/lifecycle/lifecycle_duck_adult.glb` / `lifecycle_goose_adult.glb` 仍是旧程序化版本——批量收尾需**同名覆盖** staging 新资产
3. **猪未完成**：poly_pig.glb（真骨骼 Idle+Jump）rebake bug 待修
4. **荷斯坦牛未做**（棕牛 mesh 重涂黑白花即可）
5. **manifest.json 碰撞体未更新**（spec §2.x capsule 尺寸）
6. **仓库 Quaternius animated GLB 未在联网环境重下验证**（100 倍 node scale 问题可程序化修复）

### 管线工具（`tools/`）

- `build_skinned_animal.mjs` — **主管线**：静态 GLB → 合并子网格 → 对齐 → 启发式骨骼 → 反距离² 蒙皮权重 → 顶点色刷色 → 脚底自校正 → 加眼睛 → 加毛簇
- `fix_eyes_root.mjs` — 眼睛/毛簇挂 root bone + 世界坐标
- `verify_render_vertex.mjs` — **关键验证**：模拟 GPU 顶点位置（applyBoneTransform + matrixWorld）
- 其余：`build_cc0_chicken/cow/goose/sheep.mjs`、`apply_rootjoint_trs.py`、`align_glb_py.py`、`align_cc0_glb.mjs`、`probe_parts.py`、`load_glb_check.mjs`、`gen_clips.mjs`、`finalize_cc0.py`、`decimate_glb.mjs`、`resize_textures.py`、`cleanup_glb.py`、`rebake_quaternius_animal.mjs` 等

### Demo

- `preview_cartoon_batch.html` — **主 demo**：6 格卡通对比 + 牛/鹅新旧切换 + 羊剪毛两态
- `preview_chicken_cc0.html` — 写实鸡 demo（废弃路线）
- `preview_chicken_anim.html` / `preview_chicken_b.html` / `preview_chicken_sample.html` — 历史 demo

### 后续路线建议（用户拍板，详见 ISSUES.md §2）

- **A · 死磕眼睛附体**（眼睛 skin 进 head bone，1-2 天）
- **B · 接受瑕疵批量收尾**（修猪 → 荷斯坦牛 → 8 只覆盖 → manifest → preview.html，1-2 天）⭐ 推荐
- **C · 回退写实**（MAXDESIGN + KTX2 压缩，2-3 天）
- **D · 暂停动物做其他**（场景桥接等 spec P1）
- **E · 沉淀工具为 skill**

---

## License

全部资产 **CC0**（公有领域）：程序化生成（本项目自产）、Kenney Modular Buildings、Quaternius 系列（建筑/动物/树）。
逐项归属见 `assets/manifest.json` 的 `source` / `attribution` / `license` 字段。
**新增外部资产归属**：`assets/_cc0_src/` 下 poly.pizza 卡通动物（CC-BY 各模型作者）、chicken_maxdesign_raw.glb（CC-BY MAXDESIGN-3D）——attribution 需在正式合入 manifest 时补全。
