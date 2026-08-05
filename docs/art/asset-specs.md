# 资产规格规范（Asset Specs）

| 项目 | 农场牧场网页游戏（Farm & Pasture Web Game） |
| --- | --- |
| 引擎 | Three.js + Rapier |
| 风格 | 卡通 Stylized / Low-Poly（见 `docs/art/art-bible.md`） |
| 用途 | 程序化生成器参数依据 + CC0 资产导入统一标准 + 碰撞体必填规格 |
| 版本 | v1.0 |
| 维护 | 林绘澄（art-director） |

> 本文档是**所有 3D 资产**（程序化生成、CC0 导入、手建）的硬性规格。
> 关键点：**碰撞体类型是每个资产条目的必填字段**（Rapier 物理需要），任何资产缺碰撞体规格不得进管线。

---

## 1. 资产规格模板（Asset Spec Template）

每个资产条目（在 `design/asset-manifest.md` 中登记）必须包含以下字段：

```yaml
# 资产条目模板
id: animal_cow_01              # 唯一 ID，见命名规范（与清单 ANI-xxx 对齐）
name: 棕色奶牛
type: animal                 # animal / plant / fish / building / prop / character / terrain / ui
category: livestock          # 子分类（可选）

# --- 几何预算 ---
tris: [1200, 800, 400]       # [LOD0, LOD1, LOD2] 面数预算
lod_count: 3                 # LOD 层级数（1=不设 LOD）
lod_distances: [0, 18, 40]   # LOD 切换距离（米，0=始终显示）

# --- 材质与纹理 ---
texture_size: 512            # 256 / 512 / 1024（见美术圣经 5.2）
texture_channels: [albedo]   # albedo / normal / or / vertex_color
material: toon               # toon（默认）/ standard / vertex_color

# --- 碰撞体（必填！Rapier）---
collision_type: dynamic      # static / dynamic / kinematic
collider: capsule            # box / sphere / capsule / cylinder / convex_hull / trimesh / heightfield
collider_size: [0.5, 1.2, 0.5]  # [半宽x, 半高y, 半深z] 或 [半径, 半高]
collider_offset: [0, 0.6, 0] # 相对锚点的偏移（米）
has_trigger: false           # 是否兼作触发器（检测区域）

# --- 锚点/朝向/缩放 ---
anchor: bottom_center        # bottom_center（默认，Y=0 贴地）
facing: +Z                   # 正面朝向 +Z（glTF/GLB 惯例）
scale_unit: 1m               # 1 单位 = 1 米（硬性）

# --- 动画（仅带骨骼资产）---
animations: [idle, walk, eat] # 动画列表（命名见 design/asset-manifest.md 第 7 章）
skeleton_bones: 12           # 骨骼数（动物按 2.1.1 骨架复用策略，勿超）

# --- 来源 ---
source: procedural           # procedural / cc0_kenney / cc0_quaternius / hand_built
license: N/A                 # CC0 / CC-BY / N/A（程序化）
seed: 20260805               # 程序化生成种子（见第 3 节）

# --- 状态 ---
status: planned              # planned / in_pipeline / done / rejected
```

### 1.1 缩放与坐标统一（硬性）

- **1 单位 = 1 米**，场景坐标系统一。
- **Y 轴向上**，`anchor = bottom_center` 表示资产根部/底面中心落在 `Y=0`（贴地）。
- **正面朝向 +Z**（glTF/GLB 惯例，Three.js 相机默认朝 -Z）；程序化生成与 CC0 导入必须统一旋转到该朝向。
- 禁止在引擎里缩放补偿（引擎内 scale ≠ 1 的资产视为缺陷）。

### 1.2 碰撞体速查（Rapier）

| 字段 | 可选值 | 说明 |
| --- | --- | --- |
| `collision_type` | `static` | 固定不动（地形/建筑/树），Rapier `RigidBodyDesc.fixed()` |
| | `dynamic` | 受重力/力作用（道具、可推动物），`RigidBodyDesc.dynamic()` |
| | `kinematic` | 由代码/动画控制位置（动物待机、鱼游动），`kinematicPositionBased` |
| `collider` | `box` | 三轴半尺寸 `[hx, hy, hz]`，最省性能 |
| | `sphere` | 半径 `[r, 0, 0]`（用 `collider_size[0]`） |
| | `capsule` | 半径+半高 `[r, half_h, 0]`，适合动物/角色 |
| | `cylinder` | 半径+半高 `[r, half_h, 0]`，适合树干/水井 |
| | `convex_hull` | 凸包，贴合石头/不规则静态物，性能中 |
| | `trimesh` | 三角网格碰撞，**仅当 box/sphere/capsule/cylinder/convex 无法近似时**才用（性能贵，尽量避免） |
| | `heightfield` | 高度场，仅大地形使用（1 个即可） |

**规则**：优先 box > sphere > capsule > cylinder > convex_hull > trimesh > heightfield；禁止对精细网格直接用 trimesh collider（移动端灾难）。

---

## 2. 分类型规格表（Category Specs）

### 2.1 动物（Animal）

| 规格项 | 值 |
| --- | --- |
| 基准面数（LOD0） | **鸡/鸭/兔/猫 1.5k · 羊/猪/狗/羊驼 2.5k · 牛/马 3.5-4k**（设计侧建议区间 1.5k-4k，最终以工程预算校准） |
| LOD 层级 | 3（LOD0 / LOD1 50-60% / LOD2 25-30%） |
| 骨骼数 | 见骨架复用策略（2.1.1） |
| 动画列表 | 通用 `idle`/`walk`/`eat`/`hurt`；按需 `run`/`sleep`/`peck`/`swim`/`hop`/`sit`/`bark`（见设计侧第 7 章命名） |
| 碰撞体 | **capsule**（半径≈体宽/2，半高≈身长/2），**`collision_type: dynamic`**（圈养/推动/投喂检测，Rapier `dynamic`；质心低置防翻倒） |
| 缩放 | 牛 1.2m / 羊 0.7m / 鸡 0.4m（肩高） |

#### 2.1.1 骨架复用策略（控成本核心，与设计侧第 7.3 节一致）

| 骨架 | 覆盖动物 | 骨骼数建议 | 换皮差异 |
| --- | --- | --- | --- |
| **4 足大型** | 牛 / 猪 / 羊 / 马 / 羊驼 / 狗 | 14 根 | 换皮 + 缩放 + 角/耳/毛簇差异 |
| **2 足小型** | 鸡 / 鸭 | 10 根 | 换皮 + 喙/翅差异 |
| **4 足小型** | 兔 / 猫 | 12 根 | 换皮 + 耳/尾差异 |
| **鱼（无骨骼）** | 全部鱼类 | — | 程序化正弦摆动 |

> 全套动物仅需 **3 套骨架**，CC0 导入后统一重定向到上述骨架；鱼不建骨骼。

### 2.2 植物（Plant）

| 规格项 | 值 |
| --- | --- |
| 基准面数 | 草 20-60 / 灌木 100-300 / 树 400-900 / 作物单株 300-800（LOD0，设计侧区间 0.3k-0.8k） |
| 生长阶段变体数 | **P0 作物 3 阶段（种子→幼苗→成熟）；P1 起作物 4 阶段**（种子→幼苗→成长→成熟）——见设计侧风险 #2 |
| 纹理 | 顶点色优先（程序化）；树冠/果实可 256 贴图 |
| 碰撞体 | 树干/主茎用 **cylinder**（`collision_type: static`）或 **box**（小作物）；成熟期可加 Static 凸包底座 + **Sensor 收获区**；叶冠/草丛**无碰撞** |
| LOD | 树 3 级；草/灌木/作物 1 级（InstancedMesh 批量） |

### 2.3 鱼类（Fish）

| 规格项 | 值 |
| --- | --- |
| 基准面数 | 200-800 tris（设计侧建议 LOD0≈800） |
| 动画 | `swim`（程序化正弦摆尾，无骨骼）；上钩抖动 |
| 碰撞体 | **capsule**（细长，半径≈身厚/2）；上钩时 **Sensor 挂点**（无物理体）；养殖时 `collision_type: dynamic`（或 kinematic 巡逻） |
| 缩放 | 0.3-0.8m |

### 2.4 建筑（Building）

| 规格项 | 值 |
| --- | --- |
| 基准面数 | 小棚/出货箱 1-1.5k / 畜舍/鸡舍 4-5k / 农舍 6-8k（设计侧区间 5k-8k，农舍可为主角建筑保留 8k） |
| 碰撞体 | **box 组合**（`collision_type: static`）；门洞位置**不设碰撞**（留出入口，门用 Sensor）；水井用 **cylinder**；室内交互点用 Sensor |
| 纹理 | 512（小）/ 1024（主屋） |
| LOD | 2-3 级 |

### 2.5 道具（Prop / Pickup）

| 规格项 | 值 |
| --- | --- |
| 基准面数 | 50-500 tris（设计侧区间 0.1k-0.5k） |
| 碰撞体 | **sphere**（小物：果实/种子/蛋）或 **box**（工具/桶/饲料/奶瓶）或 **capsule**（长杆物）；`collision_type: dynamic`（可拾取/可堆叠/可抛掷） |
| 拾取判定 | 额外加 `has_trigger: true` 的碰撞体作为拾取范围 |
| 工具 | 手持时**无碰撞**；挥动时临时 Sensor 命中检测（锄/镰/斧） |
| 纹理 | 256，顶点色优先 |

---

## 3. 程序化生成参数规范（Procedural Generation Specs）

程序化生成是**默认生产方式**：面数低、无贴图、可无限变体、包体最小。所有参数必须可从 `design/asset-manifest.md` 的条目反查。

### 3.1 参数清单

**植物（Plant）**：

| 参数 | 类型 | 区间/枚举 | 说明 |
| --- | --- | --- | --- |
| `stemHeight` | float | 0.3–2.5m | 茎/干高 |
| `stemRadius` | float | 0.02–0.15m | 茎粗 |
| `leafCount` | int | 3–12 | 叶/枝数 |
| `leafShape` | enum | round / oval / spike | 叶形 |
| `crownShape` | enum | sphere / cone / umbrella | 冠形 |
| `branchLevels` | int | 1–3 | 分支层级 |
| `fruitCount` | int | 0–8 | 果实数 |
| `harvestState` | enum | none / picked / ready | 多次收获作物两态（番茄/草莓）：`ready`=未摘、`picked`=已摘（计时恢复），`none`=一次性收获 |
| `colorTint` | hsl | 见美术圣经 2.3 | 配色区间 |

**鱼类（Fish）**：

| 参数 | 类型 | 区间 | 说明 |
| --- | --- | --- | --- |
| `bodyLength` | float | 0.3–0.8m | 体长 |
| `bodyRatio` | float | 2.5–4.0 | 长宽比（长/高） |
| `finShape` | enum | rounded / forked / triangle | 尾鳍形 |
| `colorBase` | hsl | 鱼类区间 | 基色 |
| `colorBelly` | hsl | 亮于 base 15% | 肚色 |
| `spotPattern` | enum | none / dots / stripes | 斑纹 |

**简单动物（牛/羊/鸡）**：

| 参数 | 类型 | 区间/枚举 | 说明 |
| --- | --- | --- | --- |
| `bodyScale` | float | 0.8–1.2 | 整体体型 |
| `bodyRatio` | float | 1.2–1.6 | 长宽比 |
| `legLength` | float | 0.6–1.0（相对体高） | 腿长 |
| `headRatio` | float | 1:2.5–1:3 | 头身比 |
| `earSize` | float | 0.5–1.5 | 耳/角大小 |
| `furColor` | hsl | 见美术圣经 2.3 皮毛区间 | 毛色 |
| `patchColor` | hsl | 可选 | 斑点色 |

### 3.2 随机种子策略（保证风格统一）

1. **全局种子**：每个场景/世界一个 `globalSeed`（如 `20260805`）。
2. **资产种子派生**：`assetSeed = hash(globalSeed + assetId + assetType)`，确定性哈希（如 xxhash32 / fnv1a）。
   - 同一资产 ID + 同一全局种子 ⇒ **每次加载完全一致**（存档/场景可复现）。
3. **调色板约束**：所有颜色必须从美术圣经 2.3 区间采样；随机数先映射到区间内再使用，**禁止无约束 RGB**。
4. **风格种子分离**：`seedColor` 与 `seedShape` 分开，允许"换色不换形"批量变体。
5. 每个生成资产在 manifest 中记录 `seed` 字段，便于复现与审计。

---

## 4. CC0 资产库接入规范（CC0 Asset Pipeline）

### 4.1 来源白名单（Whitelist）

| 来源 | 授权 | 说明 | 推荐度 |
| --- | --- | --- | --- |
| Kenney.nl | CC0 | 大量低模/极简资产，风格最接近 | ⭐⭐⭐ |
| Quaternius | CC0 | 低模卡通自然/动物包（Ultimate Nature 等） | ⭐⭐⭐ |
| Poly Haven | CC0 | HDRI/材质/模型，偏写实需风格化 | ⭐⭐ |
| Poly Pizza | 多为 CC0/CC-BY | 需逐项核查授权 | ⭐ |
| OpenGameArt | 混合 | **必须逐项确认**授权为 CC0 或 CC-BY | ⭐ |
| Sketchfab | 混合 | 仅接受 CC0 且风格匹配；需下载 GLB | ⭐ |

**授权规则**：
- **CC0**：无署名要求，可直接用于商业项目 ✅。
- **CC-BY**：必须署名（在 CREDITS 文件登记作者+来源+授权）✅（需记录）。
- **CC-BY-SA**：衍生需同协议共享，**不用于本项目** ❌。
- **NC（非商业）类**：一律禁用 ❌。

### 4.2 接入流程（7 步 + 每步检查点）

| 步骤 | 动作 | 检查点（不通过不得进入下一步） |
| --- | --- | --- |
| 1. 下载 | 从白名单下载源文件（优先 GLB/OBJ+FBX） | ✅ 授权类型 CC0/CC-BY；✅ 记录来源 URL + 作者 + 授权类型 |
| 2. 风格统一 | 将配色替换为调色板色、去除写实贴图 | ✅ 主色落在美术圣经调色板；✅ 无写实照片级贴图残留 |
| 3. 重拓扑/减面 | 用减面工具（Blender Decimate / QuadriFlow）降到预算面数 | ✅ tris ≤ 该类型 LOD0 预算（±10%）；✅ 无 N-gon、无反转面 |
| 3.5 骨骼重定向（仅动物） | 将 CC0 骨架重定向到项目 3 套标准骨架（4 足大型/2 足小型/4 足小型），动画 clip 一并重定向 | ✅ 骨骼名称映射表建立；✅ 动画 clip 命名对齐第 7 章；✅ 预览 idle/walk/eat 无穿模、无抖 |
| 4. 材质替换 | 换成 MeshToonMaterial + 统一 shader | ✅ 材质参数符合美术圣经 5.1；✅ 纹理尺寸符合分级 |
| 5. 碰撞体配置 | 按本文档第 1.2 节加 Rapier 碰撞体 | ✅ `collision_type` + `collider` 已填；✅ 碰撞体不穿透/不过大 |
| 6. 命名对齐 | 重命名文件/内部节点 | ✅ 命名符合美术圣经 9.2；✅ 内部节点 `col_*` 标注碰撞体 |
| 7. 导出 GLB | 导出 glTF Binary | ✅ 单位 1m / Y-up / 面朝 +Z；✅ 动画烘焙 30fps；✅ 纹理 2 的幂 |

> **风险控制（设计侧 #1）**：CC0 卡通四足动画较少、重定向可能失真。P0 动物仅牛+鸡，**必须先验证牛的完整动画管线（下载→重定向→预览）再批量生产**，避免 M1 卡点；验证通过后其余动物按骨架复用策略批量换皮。

### 4.3 减面优先级（外部资产）

- 先减**不可见/次要面**（内部面、底下面、贴地不可见面）。
- 保持轮廓剪影不塌陷（卡通风格靠剪影辨识）。
- 减面后必须重新平滑法线，避免凹凸不齐。

---

## 5. 质量检查清单（QA Checklist）

每项资产提交前必须逐条通过（程序化与 CC0 同标准）：

### 几何
- [ ] 面数 ≤ 预算（该类型 LOD0，±10% 容差）
- [ ] LOD 层级数与切换距离符合规格
- [ ] 无 N-gon、无反转面、无孤立顶点/孤立面
- [ ] **无 z-fighting**（无重叠共面；相邻面间距 > 0.001m）
- [ ] 无内部不可见面（可省）

### 碰撞体（必查）
- [ ] `collision_type` 与 `collider` 字段已填且合理（static/dynamic/kinematic + box/sphere/capsule/mesh）
- [ ] 碰撞体大小与网格贴合（误差 < 15% 体积），不穿透地面
- [ ] 门洞/入口处无碰撞阻挡
- [ ] 可交互物有 `has_trigger` 拾取范围

### 材质与纹理
- [ ] 材质为卡通（toon/vertex_color），无写实 PBR 残留
- [ ] 纹理尺寸符合分级且为 2 的幂
- [ ] 颜色落在调色板/随机区间内
- [ ] 纹理通道符合规格（默认仅 albedo / 顶点色）

### 坐标与命名
- [ ] 1 单位 = 1 米，Y-up，锚点 bottom_center 贴地
- [ ] 正面朝向 +Z（glTF/GLB 惯例）
- [ ] 文件名符合 `snake_case` + 类型前缀
- [ ] 内部节点 `col_*` 标注正确

### 动画（如有）
- [ ] 动画列表符合类型要求（动物 idle/walk/eat/hurt；玩家 swing_* / water / cast_rod 等，命名见设计侧第 7 章）
- [ ] 循环动画首尾无缝
- [ ] 动画不含绝对位移（位移由物理/代码驱动）
- [ ] 帧率 30fps
- [ ] 动物骨架复用策略正确（4 足大型 / 2 足小型 / 4 足小型，未重复造骨）

### 性能
- [ ] 同屏 draw call / 实例数 / 纹理 VRAM 在预算内（见美术圣经 9.1）
- [ ] 非必要不使用 mesh collider

### 授权与来源
- [ ] CC0/CC-BY 来源有记录（URL + 作者 + 授权类型 + 署名）
- [ ] 程序化资产已记录 seed 可复现

---

## 附：字段速查表（供 manifest 引用）

| 必填 | 类型字段 | 动画（命名见设计侧第 7 章） | 碰撞体建议 |
| --- | --- | --- | --- |
| `char_farmer_01` | character | idle/walk/run/swing_hoe/water/cast_rod/... | capsule (dynamic) |
| `animal_cow_01` | animal | idle/walk/eat/hurt | capsule (dynamic) |
| `animal_chicken_01` | animal | idle/walk/eat/peck/hurt | capsule (dynamic) |
| `plant_tree_oak_01` | plant | 风摆（顶点/Shader） | cylinder 树干 (static) |
| `fish_salmon_01` | fish | swim（程序化） | capsule (dynamic) + 上钩 Sensor |
| `building_barn_01` | building | 无（粒子可选） | box 组合 (static) |
| `prop_bucket_01` | prop | 无 | box (dynamic) |
| `prop_fruit_01` | prop | 无 | sphere (dynamic) + trigger |

### 动画命名约定（与 design/asset-manifest.md 第 7 章一致）

- 动物通用：`idle` / `walk` / `eat` / `hurt`；按需：`run`、`sleep`、`peck`、`swim`、`hop`、`sit`、`bark`。
- 玩家：`idle` / `walk` / `run` / `swing_hoe` / `swing_scythe` / `swing_axe` / `water` / `cast_rod` / `reel_rod` / `pickup` / `sleep`。
- 建筑/环境：默认无骨骼动画；动效走 Shader（水面、风摆）或粒子（烟雾、水滴）。
- 循环动画必须无缝循环；动画不含绝对位移（位移交给物理/代码）。

### 阶段数约定（与设计侧风险 #2 对齐）

- P0 作物（小麦/胡萝卜）：**3 阶段**（种子→幼苗→成熟）。
- P1 起作物：**4 阶段**（种子→幼苗→成长→成熟）；多年生果树 3 阶段（幼苗→成树→挂果）。
