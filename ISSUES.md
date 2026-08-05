# 已知问题与决策记录（ISSUES）

本仓库成年动物 3D 资产重建过程中累积的**未解决问题**与**未来路线选择**。记录时间：2026-08-06 01:14（北京时间）。

---

## 1. 已发现问题（Known Issues）

### 1.1 眼睛/毛簇附体未根治（用户截图确认，2026-08-06 01:14）

**症状**：5 只顶点蒙皮版（_sk）的卡通风眼睛和鸭子的头顶黑毛簇**仍漂浮在身体外面**（不对齐头部 mesh）。

**已尝试的方案**（均未根治）：
1. attach 到 head bone + 头区几何定位 → 失败（head bone 与 head mesh 不重合）
2. attach 到 root bone + world 坐标从渲染头中心算 → 仍异常（根因是更深的坐标变换问题）

**根因（猜测）**：
- 程序化生成的骨骼（root + neck + head + 4 腿）使用 `setFromObject(skinnedMesh).getCenter()` 算 head bone 位置时，渲染顶点位置受 skin 权重影响与"绑骨时的初值"不一致
- 任何 attach 方案都受 skin 计算时序影响——可能要在 `skinnedMesh.skeleton.update()` 后再 `updateMatrixWorld(true)` 才能拿到真实 worldPosition

**已知数值**（修复前实测）：
- 牛：headBone z=1.008 vs 渲染头中心 z=1.216（差 21cm）
- 鸭：headBone z=0.146 vs 头中心 z=0.183（差 3.7cm）

**兜底方案（未实施）**：
- 把眼睛/毛簇**作为 skinnedMesh 的子 mesh**（共享 skin 绑定）——眼睛顶点直接 skin 到 head bone，自动跟 head mesh 顶点变形
- 需要实现"生成 sub-mesh 的 skin 绑定"

**用户决策（2026-08-06 01:14）**：暂停眼睛迭代，正视问题，记录到 ISSUES，后续路线由用户拍板。

### 1.2 官方 Quaternius glTF 未验证（2026-08-05 23:44）

**症状**：仓库自带 Quaternius animated GLB（`farm_Cow_animated.glb` 等）实测发现：
- skin 权重**全部正常**（修正了之前的 API 误判——`skinWeight.getX(i*4+b)` 对 itemSize=4 是错读，正确是 `getComponent(i,b)`）
- 但有 **100 倍 node scale + 骨骼 bind 双倍缩放**——可通过 `apply_rootjoint_trs.py` 程序化修复
- **未在沙箱联网重下官方 glTF 验证**——之前说"沙箱无外网"是 node fetch 受限，但 curl + Chrome UA + Referer 可通（poly.pizza 链路已验证）

**当前状态**：用了 poly.pizza 镜像的卡通模型（也是 CC0，但风格不同）作为替代。仓库 Quaternius animated 版仍是潜在最优源。

### 1.3 写实方案废弃（用户 2026-08-05 22:30 转向卡通）

**背景**：MAXDESIGN 半写实鸡（`animal_chicken_brown_cc0.glb`，4.16MB）经历了大量 GPU/材质/动画 bug 后用户决定**放弃写实、转卡通**（体积、风格统一性都更好）。

**遗留资产**：`animal_chicken_brown_cc0.glb`（及 chicken_r 系列）仍在 staging 但不是最终方向。

### 1.4 KTX2 + Draco 压缩实验未对卡通资产实操

**状态**：`eng-lead-compress` worker 在用户转向卡通后任务失去意义，仍可能跑完但产物针对写实鸡。卡通资产体积已很小（50-160KB），压缩收益低，**未对卡通资产做 KTX2/Draco 压缩实验**。

### 1.5 猪真骨骼路径待修（2026-08-06 00:23）

**状态**：poly.pizza 的 `poly_pig.glb` 有真骨骼 + 2 动画（Idle + Jump），但有"100 倍 scale + IBM rebake bug"，需要修复 rebake 流程后才能产出可用版本。当前动物清单中**猪未完成**。

### 1.6 荷斯坦牛未做（2026-08-05 23:30）

**状态**：8 只成年动物清单里，**棕牛已做（_sk）、荷斯坦牛未做**（棕牛 mesh 重涂黑白花即可，但批量阶段未触发）。

### 1.7 仓库 `assets/animals/` 原版程序化资产未替换（2026-08-05）

**状态**：用户要求"重新建模"程序化生成的低质量成年动物（脚身脱节问题）。当前 **staging 下有新版**（_sk / _b），但**正式路径** `assets/animals/animal_*.glb` 和 `assets/lifecycle/lifecycle_duck_adult.glb` / `lifecycle_goose_adult.glb` **仍是旧的程序化版本**（未被替换）。这意味着游戏运行时仍加载老资产。

**待办**：批量收尾时执行**同名覆盖**：
- `assets/animals/animal_chicken_brown.glb` ← `staging/animal_chicken_brown_sk.glb`
- `assets/animals/animal_chicken_white.glb` ← `staging/animal_chicken_white_b.glb`（白鸡目前只有程序骨骼版）
- `assets/animals/animal_cow_brown.glb` ← `staging/animal_cow_brown_sk.glb`
- `assets/animals/animal_cow_holstein.glb` ← 待重涂棕牛（荷斯坦牛黑白花）
- `assets/animals/animal_pig.glb` ← 待 rebake 修复后的 poly_pig
- `assets/animals/animal_sheep.glb` ← `staging/animal_sheep_sk.glb`（+shorn 变体运行时切换）
- `assets/lifecycle/lifecycle_duck_adult.glb` ← `staging/lifecycle_duck_adult_sk.glb`
- `assets/lifecycle/lifecycle_goose_adult.glb` ← `staging/lifecycle_goose_adult_sk.glb`

### 1.8 manifest.json 碰撞体未更新（spec §2.x 要求 capsule 加大）

**状态**：spec §2.1-2.8 要求新尺寸对应的碰撞体（如牛 r0.45/h0.65、鸡 r0.16/h0.22）。当前 manifest 仍是旧程序化版本的碰撞体参数。

### 1.9 preview.html toon 环境桥接未做（spec §5.1 C1-C8）

**状态**：spec 提到写实动物需要场景桥接（IBL + rim + ACES），但用户已转卡通，卡通与环境天然统一，**桥接需求降低**。但 toon 环境本身无 IBL，preview.html 仍是老版本，未来若用 Three.js MeshToonMaterial + IBL 桥接需评估。

---

## 2. 后续路线选项（用户拍板）

**问题已正视，不再无限制迭代眼睛附体**。下一步用户可拍板：

### 路线 A · 继续死磕眼睛附体（兜底方案）

- **做什么**：实施眼睛作为 skinnedMesh 子 mesh 的兜底方案（皮肤权重绑定到 head bone，自动跟 head mesh 顶点变形）
- **工作量**：1-2 天（实现 sub-mesh skin 绑定 + 重新跑 5 只蒙皮版）
- **效果保证**：高（数学上必然贴头）
- **风险**：可能发现新的技术卡点

### 路线 B · 接受当前瑕疵，进入批量收尾

- **做什么**：眼睛轻微漂浮作为已知限制被接受，立即开始：
  1. 修猪 poly.pig rebake bug → 产出真骨骼猪
  2. 重涂荷斯坦牛（棕牛 mesh 黑白花）
  3. 8 只同名覆盖到正式路径
  4. 更新 manifest.json 碰撞体
  5. 更新 preview.html（卡通版）
- **工作量**：1-2 天
- **游戏可用性**：高（除了眼睛小瑕疵，整体卡通风格统一、体积小、风格一致）

### 路线 C · 回退到写实方向

- **做什么**：废弃卡通路线，回到 MAXDESIGN 半写实 + KTX2 压缩
- **工作量**：2-3 天（修写实鸡 GPU 残留 bug + 8 只写实批量 + 压缩管线）
- **风险**：与卡通环境（建筑/植物）撕裂；体积仍是卡通几倍

### 路线 D · 暂停动物重建，做其他工作

- **做什么**：动物先放一边，做 spec 中其他 P1 项（场景桥接、manifest、碰撞体、preview.html 升级）
- **不影响**：当前 staging 的卡通资产随时可启用

### 路线 E · 沉淀工具链为 skill

- **做什么**：把 `build_skinned_animal.mjs` + `apply_rootjoint_trs.py` + `verify_render_vertex.mjs` + `fix_eyes_root.mjs` 等工具沉淀为可复用 skill，方便后续项目
- **适合时机**：项目告一段落后

---

## 3. 决策历史（Decision Log）

| 时间 | 决策 | 原因 |
|------|------|------|
| 2026-08-05 20:30 | 写实 vs 卡通 → **卡通** | 体积小 6-50 倍、风格与仓库统一 |
| 2026-08-05 20:50 | CC0 vs 程序化 → **CC0 程序化骨骼** | 用户要求"精致卡通"非"toon 低模" |
| 2026-08-05 21:30 | 拆件 vs 整模 → **顶点蒙皮** | 撕裂问题根因是刚体挂载，须共享顶点 |
| 2026-08-06 00:18 | 蒙皮版 vs 写实版 → **蒙皮版** | 用户确认蒙皮撕裂解决 |
| 2026-08-06 00:45 | 加眼睛 → 通过但**附体有问题** | 用户反馈缺乏生机，附体未根治 |
| 2026-08-06 01:07 | 眼睛 fix 后**仍漂浮** | 渲染时位置不对，attach 机制有问题 |
| 2026-08-06 01:14 | 暂停迭代，**正视问题 + 路线选择** | 用户明确指令 |

---

## 4. 当前 staging 资产清单（2026-08-06 01:14）

### 5 只顶点蒙皮卡通版（最新主资产）

| 文件 | 体积 | 高度 | 备注 |
|------|------|------|------|
| `animal_chicken_brown_sk.glb` | 85KB | 0.500m | 鸡（5 材质 + 顶点色 + 眼睛） |
| `animal_cow_brown_sk.glb` | 157KB | 1.500m | 牛（暖棕身/深褐腿/眼睛 + **眼睛可能漂浮**） |
| `lifecycle_duck_adult_sk.glb` | 84KB | 0.350m | 鸭（黑顶/白身/黄脚/橙喙 + 眼睛 + 毛簇） |
| `lifecycle_goose_adult_sk.glb` | 75KB | 0.650m | 鹅（暖白/橙蹼 + 眼睛） |
| `animal_sheep_sk.glb` | 121KB | 0.750m | 羊（暖白/棕褐脸腿 + 眼睛） |

### 5 只程序骨骼版（对比用，保留作 fallback）

| 文件 | 体积 | 高度 | 备注 |
|------|------|------|------|
| `animal_chicken_brown_b.glb` | 43KB | 0.500m | 早期程序骨骼 |
| `animal_chicken_white_b.glb` | 43KB | 0.500m | 白鸡（无 _sk 版本） |
| `animal_cow_brown_b.glb` | 57KB | 1.500m | 牛程序骨骼（对比） |
| `animal_sheep_b.glb` | 129KB | 0.780m | 羊剪毛前 |
| `animal_sheep_shorn_b.glb` | 47KB | 0.650m | 羊剪毛后（双形态方案） |
| `animal_pig_b.glb` | 187KB | — | 猪（程序骨骼版本） |
| `lifecycle_goose_adult_b.glb` | 117KB | 0.650m | 鹅程序骨骼（对比） |

### 历史写实方案资产（保留作历史）

| 文件 | 体积 | 备注 |
|------|------|------|
| `animal_chicken_brown_cc0.glb` | 4.16MB | MAXDESIGN 半写实 + 完整骨骼（**最终未采用**） |
| `animal_chicken_brown_r.glb` / `_r_game.glb` / `_r_hi.glb` / `_r_game_multimesh.glb` | 40-180KB | 多模态生成样本变体（**废弃**） |
| `cc0_compress_test/` | — | 写实鸡压缩实验目录（**废弃**） |

### 工具（可复用 production tools）

- `tools/build_skinned_animal.mjs` — **主管线**：静态 GLB → 合并子网格 → 对齐 → 启发式骨骼 → 反距离² 蒙皮权重 → 顶点色刷色 → 脚底自校正 → 加眼睛 → 加毛簇（鸭子）
- `tools/fix_eyes_root.mjs` — 眼睛/毛簇改挂 root bone + 世界坐标（root cause 修复）
- `tools/build_cc0_chicken.mjs` — CC0 鸡（blujay）程序化骨骼管线（早期版本，未直接用）
- `tools/apply_rootjoint_trs.py` — 写实 GLB 的 rootJoint TRS 应用
- `tools/align_glb_py.py` / `tools/align_cc0_glb.mjs` — GLB 对齐工具
- `tools/verify_render_vertex.mjs` — **关键验证工具**：模拟 GPU 顶点位置（applyBoneTransform + matrixWorld），发现 6mm 事件、head bone 错位
- `tools/probe_parts.py` / `tools/load_glb_check.mjs` — GLB 探查
- `tools/gen_clips.mjs` / `tools/finalize_cc0.py` — 动画生成/落盘
- `tools/decimate_glb.mjs` / `tools/resize_textures.py` / `tools/cleanup_glb.py` — 减面/纹理/清理

### 文档与 demo

- `docs/art/animal-rebuild-spec.md` — 8 只动物逐只规格（含 GLB 规范、贴图、蒙皮、动画、命名）
- `preview_cartoon_batch.html` — **主 demo 页**：6 格对比 + 牛/鹅新旧切换 + 羊剪毛两态
- `preview_chicken_cc0.html` — 写实鸡 demo（最终未采用路线）
- `preview_chicken_anim.html` / `preview_chicken_b.html` — 程序骨骼鸡 demo（历史）

### CC0 源（留底）

- `assets/_cc0_src/chicken_blujay_raw.glb` (34KB, CC0) — 早期 blujay 鸡
- `assets/_cc0_src/chicken_maxdesign_raw.glb` (4MB, CC-BY MAXDESIGN-3D) — 半写实鸡（最终未采用）
- `assets/_cc0_src/poly_dl/` — poly.pizza 下载的 6 个卡通动物模型（cow/duck/goose/pig/chicken/sheep, CC-BY 各模型作者）

---

**记录人**：主理人（编排者）
**决策待用户**：见 §2 路线选项