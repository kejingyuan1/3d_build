# 资产生产管线（Asset Pipeline）

> 项目：农场牧场网页游戏
> 文档角色：engineering-lead（程基岩）
> 状态：v0.1 首批交付
> 关联文档：《技术架构文档》(technical-architecture.md)、《美术圣经与资产规格》(art-director 产出)、《全量资产清单》(design-strategist 产出)

---

## 0. 本文档目标

定义"一份资产从生产到上线"的全流程标准，让以下三类来源的资产在运行时表现一致：
1. **程序化生成器**（植物/鱼/简单动物）— 离线批量产出；
2. **CC0 开源资产库**（第三方模型）— 导入、清洗、优化；
3. **手调例外资产**（特殊结构物/占位碰撞体）— 少量人工建模。

所有资产最终统一进入 `assets/manifest.json` 注册表，供运行时懒加载。

---

## 1. GLB 资产标准

### 1.1 坐标系与单位（硬性标准，违反即打回）

| 项 | 标准 | 说明 |
|---|---|---|
| 单位 | **1 单位 = 1 米** | 与 Rapier 物理世界一致，物理参数可直接换算 |
| 轴向上 | **Y 轴向上** | Three.js/Rapier 默认 |
| 前向 | **Z 轴为角色前向**（+Z 朝前） | 动物/角色 facing 约定；植物无朝向要求可忽略 |
| 锚点 | **脚底中心 = 原点 (0,0,0)** | 建筑/道具/动物：脚底中心；植物：根部中心；地面接触点落在原点，放置时直接 `position = (x, 0, z)` 即可贴地 |
| 比例 | 资产在 GLB 内保持真实尺寸，**禁止**在场景中靠 `scale` 修正 | 保证物理碰撞体参数与视觉一致 |

### 1.2 命名规范（snake_case）

| 对象 | 规范 | 示例 |
|---|---|---|
| 资产 ID | `<category>_<name>[_variant]` | `plant_carrot_leafy`、`animal_chicken_brown`、`building_barn_01` |
| GLB 文件名 | `<asset_id>[_lod<level>].glb` | `plant_carrot_leafy.glb`、`building_barn_01_lod2.glb` |
| 内部 Mesh 名 | `mesh_<part>[_lod<level>]` | `mesh_trunk_lod0`、`mesh_leaves_lod1` |
| 内部材质名 | `mat_<material_name>` | `mat_wood_light`、`mat_leaf_green` |
| 占位碰撞体（例外） | `_collider_<shape>_<index>` | `_collider_cuboid_00`、`_collider_cylinder_01` |
| 元数据文件 | `<asset_id>.json` | `plant_carrot_leafy.json` |

### 1.3 GLB 内部结构要求

- **Mesh**：每个 LOD 一个文件或同文件内多个 mesh 节点；mesh 命名必须带 `_lod<level>` 后缀，便于自动识别 LOD 层级。
- **材质**：使用 PBR（`baseColor` + 可选 `roughness/metallic` 图）；卡通风格主要靠颜色与轻微 AO，不做复杂 PBR 参数。
- **纹理**：材质引用的贴图以**外部引用打包进 GLB**（glTF 内嵌）或同目录引用均可，最终管线统一烘焙内嵌；贴图尺寸符合 §4 预算。
- **动画**（动物/机械）：GLB 内可含骨骼动画（走/吃/摇尾巴），命名 `anim_<name>`；运行时用 Three.js `AnimationMixer` 播放。程序化生成的简单动物优先用**顶点动画/参数化摆动**替代骨骼，减少资产体积。
- **禁止**：GLB 内嵌自定义扩展承载碰撞信息（决策见 technical-architecture §3.2）；禁止超大未压缩纹理；禁止在 GLB 里放灯光/相机节点（运行时场景统一打光）。

---

## 2. 程序化生成器架构

### 2.1 生成器类型与职责

| 生成器 | 产出示例 | 输入参数（对齐 art 侧参数规范） | 输出 |
|---|---|---|---|
| `plant_generator` | 蔬菜（胡萝卜/番茄/玉米）、果树、灌木、花 | 种子、品种、尺寸(scale)、成熟度(stage)、色板(variant)、细节密度 | GLB × LOD + metadata JSON |
| `fish_generator` | 池塘/溪流观赏鱼 | 种子、体长、配色、鳍型、游动动画类型 | GLB + metadata JSON（含骨骼或顶点动画参数） |
| `animal_generator` | 鸡、牛、羊（低面卡通） | 种子、体型、毛色/花色、姿态（站/走/卧）、是否幼崽 | GLB × LOD + metadata JSON + 动画参数 |

所有生成器共享统一输出接口：
```
generate(config: GenConfig) -> { glb: Buffer, metadata: AssetMetadata }
```

### 2.2 输入参数规范

- **种子（seed）**：整数，同一 seed + 同一 config 必须产出**完全一致**的资产（确定性），用于批量复现与回归测试。
- **参数空间**：由 art 侧《美术圣经与资产规格》定义（尺寸/色板/风格阈值），工程侧只消费参数，不自行发明风格参数。
- **成熟度（growth stage）**：农场玩法需要"幼苗 → 成长 → 成熟"多阶段，建议每个阶段单独生成小面数变体（而非运行时变形），减少运行时开销。

### 2.3 输出

1. **GLB 文件**：LOD0 完整、LOD1/LOD2 由减面管线生成（或生成器直接出多级）。
2. **metadata JSON**（与 manifest 合并或引用）：
```json
{
  "assetId": "plant_carrot_leafy",
  "category": "plant",
  "genSeed": 20260805,
  "genConfig": { "stage": "mature", "scale": 1.0, "variant": "leafy" },
  "lodLevels": [0, 1, 2],
  "collision": { "type": "cylinder+ball", "params": { "trunkR": 0.03, "trunkH": 0.1, "crownR": 0.22 } },
  "animations": [],
  "textureBudgetMB": 0.5
}
```

### 2.4 批量生成流程（含随机种子）

```
[1] 定义批次（BatchSpec）：资产类别 × 参数空间采样点数 × 全局种子
        ↓
[2] 按 seed 派生每个实例的参数（确定性伪随机：seed 哈希 → 参数采样）
        ↓
[3] 逐实例：生成器 → GLB + metadata
        ↓
[4] 减面/优化管线 → LOD1/LOD2
        ↓
[5] 自动验收（§5）→ 通过则入库
        ↓
[6] 汇总写 assets/manifest.json（含 hash）
        ↓
[7] 冒烟预览（离线渲染器/截图）人工抽查
```

### 2.5 工具栈建议：Blender Python API（推荐）vs 运行时 Three.js 程序化构建

**推荐：离线 Blender Python API 批量生成。**

| 维度 | Blender Python API（离线，推荐） | Three.js 运行时构建 |
|---|---|---|
| 预览 | 可在 Blender 视口/EEVEE 直接预览最终观感 | 需在游戏内临时查看，无灯光/材质所见即所得 |
| 烘焙 | 可烘焙 AO/法线/顶点色，LOD 减面工具成熟 | 无烘焙能力 |
| 资产体积 | 产出静态 GLB，运行时零构建开销 | 每次加载都要跑生成逻辑，CPU 开销 + 启动延迟 |
| 物理代理 | 可直接建碰撞代理对象一并导出 | 需额外写碰撞逻辑 |
| 迭代速度 | 改脚本重跑即可；参数化清晰 | 迭代快但每次都要进游戏验证 |
| 适用场景 | **正式资产生产** | 原型验证、动态变体（如颜色随机） |

**决策记录 ADR-A1：离线 Blender 生成**
- 上下文：资产量大、需 LOD、需与物理碰撞代理一致、Web 端加载要快。
- 备选：A) 离线 Blender Python；B) 运行时 Three.js 构建；C) 混合（离线为主，个别动态变体运行时）。
- 决定：采用 A，运行时保留"简单参数化变体"能力（如染色、缩放）但不做几何生成。
- 后果：需要维护 Blender Python 脚本与依赖（如 `bpy` + 减面插件）；换来的是运行时零生成开销与高质量可预览资产。

---

## 3. CC0 资产导入管线

适用：从开源 CC0 资产库（如 Poly Haven、Kenney、Quaternius、Google Poly 存档、Sketchfab CC0）导入的第三方模型。

### 3.1 工具链

| 工具 | 用途 |
|---|---|
| gltf-transform | GLB 优化：DRACO/meshopt 压缩、纹理 KTX2/Basis 转换、顶点重排、mipmap 生成 |
| Blender（含 decimate/重拓扑插件） | 减面、重拓扑、单位/朝向/锚点修复、碰撞代理建模 |
| 内部脚本（Python/Node） | 自动验收、命名批处理、manifest 写入 |

### 3.2 导入步骤（标准流程）

```
[0] 许可核验：确认 CC0（或明确可商用免署名），记录来源与 URL → 资产元数据字段
[1] 下载原始文件（.blend/.fbx/.obj/.gltf 均可）
[2] Blender 清洗：
    - 单位换算 → 1 单位 = 1 米
    - 旋转 → Y 轴向上、Z 轴前向
    - 锚点 → 脚底中心/根部中心
    - 重命名 → snake_case（§1.2）
    - 删除隐藏对象、清空材质冗余、合并同一 LOD 的 mesh
[3] 减面 / 重拓扑：达目标面数（§4.1），LOD0 保细节，LOD1/LOD2 递减排面
[4] 碰撞代理：按类别规则生成简化碰撞体（或放置 `_collider_*` 占位对象）
[5] 导出 GLB（内嵌纹理）
[6] gltf-transform 优化：压缩 mesh + 纹理 KTX2/Basis
[7] 自动验收（§5）→ 通过则入库
[8] 写入 manifest.json（含 hash、来源、许可记录）
[9] 人工视觉抽查（风格/缩放/朝向）
```

### 3.3 验证检查点（导入必查）

| 检查点 | 标准 | 失败处理 |
|---|---|---|
| 尺寸 | 与 art 规格表一致（如"鸡=0.4m 高"） | 打回修正 scale |
| 朝向 | Y 轴向上、Z 前向、锚点脚底中心 | 打回修正旋转/原点 |
| 碰撞体 | manifest `collision` 字段非空且与类别规则一致 | 打回补碰撞代理 |
| 面数 | ≤ 对应类别 LOD0 预算 | 打回减面 |
| 纹理 | KTX2 压缩、尺寸 ≤ 预算 | 打回压缩 |
| 命名 | snake_case、mesh/mat 前缀规范 | 打回重命名 |
| 可解析 | GLB 能被 gltf-transform / three 加载器无错解析 | 打回修复 |

---

## 4. 资产注册表 assets/manifest.json

### 4.1 结构设计

```jsonc
{
  "schemaVersion": 1,
  "generatedAt": "2026-08-05T00:00:00Z",
  "assetRoot": "assets",
  "assets": [
    {
      "assetId": "plant_carrot_leafy",
      "designId": "AST-PL-042",            // 关联 design/asset-manifest.md 的资产条目（全组唯一 ID）
      "path": "plants/plant_carrot_leafy.glb",
      "category": "plant",                 // plant | animal | fish | building | deco | terrain | pickup
      "materialMode": "toon",              // toon | standard；toon → MeshToonMaterial + gradientMap（见 technical-architecture §4.3）
      "lodLevels": [                       // 按优先级从近到远
        { "level": 0, "path": "plants/plant_carrot_leafy_lod0.glb", "screenSize": 0.25 },
        { "level": 1, "path": "plants/plant_carrot_leafy_lod1.glb", "screenSize": 0.1 },
        { "level": 2, "path": "plants/plant_carrot_leafy_lod2.glb", "screenSize": 0.04 }
      ],
      "collision": {                       // 碰撞配置唯一来源（见 technical-architecture §3.2）
        "type": "cylinder+ball",
        "params": { "trunkR": 0.03, "trunkH": 0.1, "crownR": 0.22 }
      },
      "animations": ["anim_sway"],
      "textureBudgetMB": 0.5,
      "loadPriority": 2,                   // 0=启动必载 1=近场预取 2=懒加载 3=后台慢载
      "source": { "kind": "procedural", "seed": 20260805 },
      "hash": "a1b2c3d4"
    }
  ]
}
```

### 4.2 加载策略

- **loadPriority 语义**：
  - `0` 启动必载（UI、核心地形、常用建筑）；
  - `1` 进入场景后预取（当前区块/常见植物）；
  - `2` 懒加载（用到才拉，如远区装饰）；
  - `3` 后台慢载（几乎用不到的稀有变体）。
- **缓存**：文件名带 hash → CDN 长缓存 + 本地 `Cache Storage`/IndexedDB；再次启动只比对 manifest 差异。
- **运行时按注册表懒加载**：游戏逻辑只按 `assetId` 请求，Loader 负责查表、加载、缓存、实例化；业务代码不感知路径。

### 4.3 版本管理

- manifest 变更（新增/删除/替换资产）→ 生成新 manifest，`generatedAt` 更新，hash 变化。
- `designId` 为跨文档唯一键：与 design/asset-manifest.md 的资产条目一一对应；清单侧改品类/优先级时同步改这里，工程侧以 `designId` 做需求追溯（对应技术架构的"GDD 需求 ID 可追溯"原则）。
- 客户端增量拉取；旧 hash 资产文件可留缓存，不强制清理。
- CI 自动校验：manifest 中每个 `path` 必须存在、hash 与文件实际 hash 一致、`collision` 字段满足类别规则（写进验收脚本）。

---

## 5. 验收标准

### 5.1 自动检查（脚本，进管线必跑）

| 编号 | 检查项 | 判定 |
|---|---|---|
| A1 | GLB 可解析（gltf-transform 读通、three GLTFLoader 无错） | 通过/失败 |
| A2 | 单位=1米、Y 轴向上、Z 前向、锚点=脚底中心 | 通过/失败 |
| A3 | 命名规范：资产 ID / 文件名 / mesh / mat 全 snake_case | 通过/失败 |
| A4 | LOD 文件存在且面数递减（LOD0 > LOD1 > LOD2） | 通过/失败 |
| A5 | 单资产面数 ≤ 类别预算（§4.1） | 通过/失败 |
| A6 | 纹理已 KTX2/Basis 压缩、尺寸 ≤ 预算 | 通过/失败 |
| A7 | manifest `collision` 字段非空、形状参数合法（正数、范围校验） | 通过/失败 |
| A8 | 文件 hash 与 manifest 一致 | 通过/失败 |
| A9 | 程序化资产：同 seed 重生成结果 hash 一致（确定性回归） | 通过/失败 |
| A10 | 许可记录完整（CC0 来源 URL，程序化资产标 `procedural`） | 通过/失败 |

### 5.2 手动检查（人工抽查，进库前抽 10% + 关键资产 100%）

| 编号 | 检查项 | 判定 |
|---|---|---|
| M1 | 视觉观感符合美术圣经风格（卡通 Stylized） | 通过/打回 |
| M2 | 缩放/比例在场景中自然（与参照物对比） | 通过/打回 |
| M3 | 朝向正确（动物 face +Z、植物无歧义） | 通过/打回 |
| M4 | 碰撞体与视觉贴合（不悬空、不穿模、可正常拾取/阻挡） | 通过/打回 |
| M5 | 运行时加载无警告（missing texture、名冲突） | 通过/打回 |

### 5.3 通过标准

- 自动检查 **全部 A1–A10 通过** → 可入库；
- 手动抽查通过 → 可进入下一批/上线；
- 任一失败 → 打回对应环节（生成器脚本 / Blender 清洗 / 减面 / 碰撞代理），修复后重跑 A 系列，不跳过。

---

## 6. 与第二批的衔接

- 本管线产出物（GLB + manifest + metadata）是第二批"场景搭建 / 玩法实现"的输入。
- 运行时碰撞体构建、LOD 切换、懒加载逻辑依赖 manifest 字段，字段变更需同步更新 technical-architecture §3 与 §4。
- 新资产类别（如武器/道具/建筑变体）先在 manifest 定义 `category`，再补充生成器或导入模板。

---

*本文档随第一批交付。后续随 art 侧参数规范与设计清单落地后迭代。*
