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

---

## License

全部资产 **CC0**（公有领域）：程序化生成（本项目自产）、Kenney Modular Buildings、Quaternius 系列（建筑/动物/树）。
逐项归属见 `assets/manifest.json` 的 `source` / `attribution` / `license` 字段。
