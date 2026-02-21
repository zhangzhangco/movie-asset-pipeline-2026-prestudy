# Movie Assetization Pipeline (Pre-Study 2026) - Project Context

本项目是一个实验性的**混合3D生成管线 (Hybrid 3D Pipeline)**，旨在将2D电影素材自动化转换为高保真、符合工业标准的 3D 数字资产。项目整合了多个前沿 AI 模型（3DGS, TRELLIS, DUSt3R 等），并严格遵循 GB/T 36369 电影数字资产标准。

## 🚀 项目概述 (Project Overview)

- **核心目标**: 实现从电影静帧/视频到 3D 资产的端到端自动化转换。
- **技术栈**: 
    - **编程语言**: Python 3.10+ (C++/CUDA 扩展)
    - **深度学习**: PyTorch, Nerfstudio
    - **3D 技术**: 3D Gaussian Splatting (3DGS), DUSt3R (几何重建), TRELLIS (Image-to-3D), SAM 3D Objects (分割驱动生成)
    - **色彩管理**: OpenEXR, ACES/Linear Workflow
- **架构模式**: 模块化脚本驱动，通过 `pipeline_runner.py` 进行跨 Conda 环境的编排。

## 🏗️ 核心架构 (Architecture)

项目采用“分而治之”的策略，将管线拆分为多个独立步骤：

1.  **场景生成 (`src/steps/scene_gen/`)**: 利用 `ml-sharp` 扩展背景。
2.  **几何重建 (`src/steps/geometry/`)**: 利用 `DUSt3R` 恢复空间几何。
3.  **资产提取 (`src/steps/assets/`)**:
    - `harvest_hero_assets.py`: 使用 GrabCut/SAM 提取主体道具。
    - `run_trellis_local.py` / `run_sam3d_objects_local.py`: 3D 生成后端。
4.  **光照估计 (`src/steps/lighting/`)**: 提取环境光照探针。
5.  **规范化封装 (`src/steps/export/`)**: 按照 GB/T 36369 进行元数据和资产封装。
6.  **可视化报告 (`src/steps/report/`)**: 生成 HTML 质量审核报告。

## 🛠️ 构建与运行 (Building & Running)

### 环境设置
项目依赖多个 Conda 环境以隔离不同模型的不兼容依赖：
- `sharp`: 用于 `ml-sharp`
- `dust3r`: 用于 `DUSt3R`
- `trellis`: 用于 `TRELLIS`
- `sam3d-objects`: 用于 `SAM 3D Objects`
- `base`: 基础环境，运行主编排器

### 安装
```bash
# 1. 安装 nerfstudio 插件包
pip install -e .

# 2. 运行脚本安装子环境
bash scripts/setup_dust3r.sh
# 其他脚本见 scripts/ 目录
```

### 运行管线
```bash
# 标准运行（使用 TRELLIS 后端）
python pipeline_runner.py --input /path/to/image.png

# 跳过耗时的场景生成步骤
python pipeline_runner.py --input /path/to/image.png --skip_scene

# 使用 SAM3D 后端并指定 ROI
python pipeline_runner.py --input /path/to/image.png --asset_gen_backend sam3d_objects --roi_hint 100,100,500,500
```

### 测试
```bash
pytest tests/
```

## 📝 开发约定 (Development Conventions)

- **作者标注**: 所有生成代码的 `Author` 请标注为 **zhangxin**。
- **编码规范**: 
    - 严格遵循 `AGENTS.md` 中的详细指南。
    - 使用 Python 类型提示 (Type Hints)。
    - 路径处理优先使用 `pathlib`。
    - JSON 输出必须使用 `ensure_ascii=False` 以支持中文元数据。
- **命名规范**: 
    - 函数/变量: `snake_case`
    - 类: `PascalCase`
    - 常量: `UPPER_SNAKE_CASE`
- **元数据标准**: 资产标识符需符合 `10.5000.1/CN.FILM.ASSET.YYYY.NNNN` 格式。

## 📂 关键目录说明 (Directory Overview)

- `pipeline_runner.py`: 主入口，负责跨环境调度。
- `src/steps/`: 各原子化管线步骤的源码。
- `movie_asset_3dgs/`: 核心库，包含 EXR 加载、色彩管理等通用工具。
- `docs/`: 包含 GB/T 标准说明、技术愿景和实验报告。
- `outputs/`: 默认输出目录，按 Session ID 组织。
- `modules/`: 外部模型仓库挂载点（已被 gitignore）。

---
*此文件由 Gemini CLI 生成，作为后续交互的上下文参考。*
