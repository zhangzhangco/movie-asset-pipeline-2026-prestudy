# 实施计划 (Implementation Plan) - NerfStudio Edition

## Goal Description
基于 **NerfStudio (Splatfacto)** 框架，构建 **movie-asset-3dgs** 插件系统。
通过继承与扩展现有模块，实现电影级素材（EXR/Linear/Alpha）到 3DGS 资产的自动化转换与质量优化。

---

## 进度概览 (Progress Overview)

| 阶段 | 状态 | 说明 |
|------|------|------|
| Phase 1: 基础设施 | ✅ 完成 | NerfStudio 环境 + Splatfacto 验证 |
| Phase 2: 数据加载层 | ✅ 完成 | `cinema` dataparser 插件 (EXR 支持) |
| Phase 3: Alpha Loss 模型 | ⏳ 挂起 | 需带 Alpha 素材 (暂不紧急) |
| Phase 4: 生成式 3D (New) | 🚀 进行中 | 单图转 3DGS (SHARP/TRELLIS) |
| 附加: 色彩分析模块 | ✅ 完成 | fingerprint + style_transfer |
| 附加: 2.5D 深度分层 | ✅ 完成 | 深度图提取 + Parallax Demo |

---

## 已完成模块

### Phase 1: 基础设施迁移 (Infrastructure) ✅
- [x] 安装 NerfStudio (`pip install nerfstudio`)
- [x] 解决 gsplat 编译问题 (GCC-9 + C++17)
- [x] 验证 `ns-train splatfacto` 能跑通官方 Demo (poster)
- [x] 创建插件结构 (`movie_asset_3dgs/`)

### Phase 2: 数据加载层 (Data Layer) ✅
- [x] `cinema_utils.py`: 实现 `load_exr_image` 函数
- [x] `cinema_dataparser.py`: Monkey Patch + 插件注册
- [x] 验证命令: `ns-train splatfacto cinema --data <folder>`

### 附加: 色彩分析模块 (Color Analysis) ✅
- [x] `color_stats.py`: 单帧色彩统计分析
- [x] `grade_fingerprint.py`: 多帧调色指纹生成
- [x] `style_transfer.py`: 风格迁移应用
- [x] `analyze_exr_batch.py`: 批量分析脚本 (支持 ZIP)
- [x] 生成 stem2 调色指纹 (`stem2_fingerprint.json`)

---

## 待完成模块

### Phase 3: 算法模型层 (Model Layer) ⏳
**目标**: 开发 `CinemaSplatfactoModel`，增加 Alpha Loss 监督。
- [ ] 继承 `SplatfactoModel`
- [ ] 在 `get_loss_dict` 中增加 `L_alpha = MSE(pred_alpha, gt_alpha)`
- [ ] 注册插件到 `nerfstudio.method_configs`
- [ ] **前置条件**: 需要带 Alpha 通道的 EXR 测试素材

### 附加: 2.5D 深度分层 (Depth Layering) ⏳
**目标**: 对电影连续帧 (stem2) 进行单目深度估计和分层。
- [ ] 集成 Depth Anything V2 或 MiDaS
- [ ] 实现 `depth_estimator.py`
- [ ] 实现 `layer_decomposition.py` (前景/背景分离)
- [ ] 用途: 虚拟拍摄预演、2.5D 视差效果

### Phase 4: 生成式 3D 资产 (Generative 3D Asset) 🚀
**目标**: 实现"单张电影帧 -> 3DGS/Mesh"的一键生成，无需多视角重建。
- [x] 验证 Apple `ml-sharp` (单图秒级生成)
- [x] 验证 Microsoft `TRELLIS` (高质量结构生成，已完成本地部署)
- [ ] 封装统一接口 `generate_3dgs.py`，支持多后端切换

### Phase 5: 高性能渲染与优化 (Rendering & Optimization) [NVIDIA Path] 🆕
**目标**: 利用 NVIDIA 原生工具链提升资产的渲染质量和实时展示能力。
- [ ] **评估 Instant-NGP**: 利用 `TRELLIS` 的 NeRF 输出进行快速训练和高帧率渲染。
### Phase 6: 场景级重建 (Scene Reconstruction) [DUSt3R] ✅
**目标**: 引入 **DUSt3R** (2026 SOTA) 解决 TRELLIS 无法处理整图场景的问题，实现单目图像的精确 Metric 3D 重建。
- [x] **部署 DUSt3R**: 搭建环境，下载预训练模型 (ViT-L)。
- [x] **原始重建**: 单图 -> 稀疏点云 (`run_dust3r_local.py`)。
- [x] **高精分块重建**: 实现 1024 Tiled Inference (`run_dust3r_tiled.py`)，解决分辨率瓶颈。
- [x] **3DGS 转换**: 实现 KNN 自动缩放插值，将点云转化为 3DGS (`convert_glb_to_gs.py`)。

### Phase 6.1: 场景重建方案分治 (Scene Strategy) 🆕
**结论**: 单目 DUSt3R 几何准确但视觉稀疏，ml-sharp 视觉平滑但几何较弱。
- [x] **ml-sharp 对标**: 验证 ml-sharp 为更优的**“虚拟拍摄背景”**生成器。
- [ ] **融合策略**: DUSt3R 负责空间布局(Layout) + ml-sharp 负责视觉纹理。

### Phase 7: 混合流水线与标准化 (The Standardized Hybrid Pipeline) 🏗️
**目标**: 实现 "Scene + Object" 分治构建，并统一封装入库。
- [x] **GB/T 36369 标准化**: 实现 `package_asset_gbt.py`，生成符合国标元数据的 JSON Sidecar。
- [x] **光影一致性 (Part 1)**: 实现 `estimate_lighting.py`，从场景 3DGS 逆向估算环境光探针。
- [x] **英雄资产自动化 (Hero Asset Auto-Harvest)**:
    - [x] 分割模块: 集成 GrabCut (模拟 SAM) 提取前景 (`harvest_hero_assets.py`)。
    - [ ] 资产生成: 调用 TRELLIS 生成高精道具 (Next Step)。
    - [x] 光影重定向: 利用估算的环境光探针为道具进行重打光 (Relighting)。
- [ ] **管线脚本**: 编写 `run_hybrid_pipeline.py` 串联上述步骤。

---
## 历史记录 (Archived)
### Phase 1-5 (已完成)
- 环境配置、数据解析、TRELLIS 本地化、ml-sharp 对照、gsplat 渲染集成均已完成。
- 关键产出: `run_trellis_local.py`, `run_gsplat_render.py`, `07956_rescaled.ply` (100KB+).

## 代码仓库结构 (Current)

```
movie_asset_3dgs/
├── __init__.py
├── data/
│   ├── __init__.py
│   ├── cinema_dataparser.py   # [完成] EXR 数据加载 + 插件注册
│   └── cinema_utils.py        # [完成] load_exr_image, gamma_correct
├── color/
│   ├── __init__.py
│   ├── color_stats.py         # [完成] 色彩统计分析
│   ├── grade_fingerprint.py   # [完成] 调色指纹
│   └── style_transfer.py      # [完成] 风格迁移
├── models/
│   ├── __init__.py
│   └── cinema_splatfacto.py   # [挂起] Alpha Loss 模型
└── depth/                     # [完成]
    └── depth_estimator.py

scripts/
├── analyze_exr_batch.py       # [完成] 批量 EXR 分析

assets/
├── sample_test.exr            # stem2 单帧样本
├── stem2_preview.png          # PNG 预览
├── stem2_fingerprint.json     # 调色指纹
└── stem2_fingerprint_chart.png # 可视化图表
```

---

## 验证计划 (Verification Plan)

### 已验证
- [x] `ns-train splatfacto cinema --data poster` 训练成功
- [x] EXR 读取功能 (load_exr_image) 单元测试通过
- [x] 色彩分析模块验证通过

### 待验证
- [ ] 完整 EXR → 3DGS 流程 (需多角度 EXR 数据)
- [ ] Alpha Loss 对边缘质量的改善 (需绿幕素材)
- [ ] 深度估计精度验证
