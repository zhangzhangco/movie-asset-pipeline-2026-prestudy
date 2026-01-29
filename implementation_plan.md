# 实施计划 (Implementation Plan)

## 5. 预期交付物形态 (Deliverables)
1.  **Repo**: `movie-asset-3dgs`
2.  **CLI Tool**: `asset-convert --input <folder> --quality cinema --output <file.ply>`
3.  **Viewer Config**: 指引文档，说明如何使用官方 `SIBGRAT` 或 UE5 插件加载资产进行验收。
[!IMPORTANT]
> **A6000 Environment Setup**: Users need to confirm that `nvidia-smi` and `nvcc -V` run correctly in the current environment to ensure the CUDA11.8/12.1 foundation.

## Proposed Changes

### 1. 代码仓库结构设计 (Repository Structure)
我们遵循 Modern Python Project 规范，同时兼容 C++/CUDA 扩展。

```
movie-asset-3dgs/
├── assets/                 # 存放测试用例 (Sample Data)
├── configs/                # 配置文件 (YAML/Hydra)
│   └── cinema_4k.yaml      # 电影级超高参数配置
├── src/
│   ├── app/                # CLI 与 API 入口
│   ├── core/               # 核心算法
│   │   ├── gaussian_model.py # 3DGS 数据结构封装
│   │   ├── densification.py  # 剪枝与分裂逻辑
│   │   └── scheduler.py      # [NEW] 渐进式训练调度器
│   ├── data/               # 数据加载与色彩管理
│   │   ├── image_loader.py # 支持 EXR/OpenCV 读取
│   │   └── ocio_utils.py   # ACES/Linear 转换
│   ├── diff_gaussian_rasterization/ # CUDA 扩展 (Submodule)
│   ├── pipelines/          # 转换管线 (SfM -> Train -> Export)
│   └── metrics/            # 质量评测模块
│       ├── psnr_ssim.py
│       └── lpips_loss.py
├── scripts/                # 实用脚本
│   ├── run_convert.sh      # 一键转换
│   └── benchmarking.py     # 跑分脚本
└── tests/                  # 单元测试
```

### 2. 核心模块与接口 (Core Modules)

#### [NEW] `src/pipelines/converter.py`
**功能**：串联 Colmap 与 3DGS 训练。
*   `def run_pipeline(source_path, output_path, config)`: 主入口。
*   **Color Mgmt**: 确保输入图片（如 `.exr`）被正确转换为 Linear RGB 空间进行训练。
*   实现自动根据显存 (VRAM) 调整 batch_size 的逻辑。

#### [NEW] `src/core/scheduler.py`
**功能**：管理 Progressive Resolution。
*   `class TrainingScheduler`: 控制 1K -> 4K 的迭代步数与分辨率切换条件。
*   `check_rollback()`: 如果指标恶化，自动回滚权重。

#### [NEW] `src/metrics/evaluator.py`
**功能**：计算各项质量指标。
*   `class QualityAuditor`:
    *   `calculate_signal_metrics(gt_image, render_image)` -> {PSNR, SSIM}
    *   `calculate_perceptual_metrics(gt_image, render_image)` -> {LPIPS}
    *   `generate_report(json_path)`: 输出 Markdown/JSON 格式的质检报告。

### 3. 开发里程碑 (Milestones)

#### Phase 1: 基础设施验证 (Infrastructure)
*   [ ] 初始化 Git 仓库，引入 `diff-gaussian-rasterization` 子模块。
*   [ ] 编写 `requirements.txt` 并验证 A6000 上的编译环境。
*   [ ] 跑通官方 Demo (Garden/Bicycle) 以验证 CUDA Kernel 正常工作。

#### Phase 2: 管线封装与色彩管理 (Pipeline & Color)
*   [ ] 编写 `pipelines/converter.py`，实现“一键脚本”从图片文件夹到 `.ply` 文件的输出。
*   [ ] **[Critical]** 实现 `OpenEXR` 读取与 `OCIO` 配置加载，确保全流程 Linear Workflow。
*   [ ] 集成 `metrics` 模块，在训练结束后自动输出 PSNR/SSIM 报告。

#### Phase 3: 电影级特性优化 (Cinema Features)
*   [ ] 实现 `4k_tiling` 逻辑，支持显存受限情况下的高分辨率训练。
*   [ ] 引入 Alpha Mask Loss，优化绿幕素材的边缘质量。

## Verification Plan

### Automated Tests
*   **Unit Tests**: 使用 `pytest` 测试各个 Metric 函数的计算正确性。
*   **Integration Tests**:
    *   命令：`bash scripts/run_integration_test.sh`
    *   逻辑：使用一个极小的数据集（<10张图片），运行完整的 SfM -> 3DGS -> Render 流程，断言生成的 `.ply` 文件存在且大小合理。

### Manual Verification
*   **Visual Inspection**: 使用 SIBR_viewers (官方查看器) 打开生成的 `.ply` 文件，人工确认质量。

