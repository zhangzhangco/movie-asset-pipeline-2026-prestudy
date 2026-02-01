
# 电影级 3D 资产生成与渲染：技术路线总结

**版本日期**: 2026-01-30
**作者**: Zhangxin (via Antigravity)

## 1. 项目背景与目标
本项目旨在探索利用生成式 AI 技术，将**单张电影画幅**（SDR/HDR 图像）快速转换为**高质量 3D 资产**。我们将这一流程应用于电影预演（Previz）、资产库填充及 2.5D 场景重建，旨在替代传统耗时的人工建模或多视角扫描流程。

核心目标是建立一条**"Image-to-3D"**的自动化管线：
> **输入图像 (EXR/PNG)**  -->  **生成模型 (AI)**  -->  **3D 资产 (3DGS/Mesh)**  -->  **实时渲染 (NVIDIA)**

---

## 2. 技术路线全景 (The Big Picture)

我们将整个技术栈分为三个层级：生成层、表示层、渲染层。

### 2.1 生成层 (Generative Layer)
这是 AI "无中生有" 的核心。我们并行验证了两条前沿技术路线：

| 技术方案 | **Microsoft TRELLIS** (当前主力) | **Apple ml-sharp** (对照组) |
| :--- | :--- | :--- |
| **核心原理** | **Structured Latents (结构化潜空间)**。<br>先生成 3D 骨架(Sparse)，再解码纹理和几何。 | **Feed-forward 3DGS**。<br>直接从图像回归高斯球参数。 |
| **特点** | **几何质量高**，拓扑结构清晰，支持多种输出 (Mesh/NeRF/3DGS)。 | **速度极快** (秒级)，点云非常稠密，覆盖率高。 |
| **产物特征** | 经过压缩优化的 3DGS，体积小 (~16MB)，结构紧凑。 | 原始稠密点云，体积大 (~64MB)，细节多但杂乱。 |
| **部署难度** | **极高** (涉及 spconv, flash-attn, transform 等复杂依赖)。 | 中等 (依赖特定 checkpoint)。 |

### 2.2 表示层 (Representation Layer)
我们要用什么格式来存储 3D 资产？目前业界标准正在从传统的 Mesh (网格) 向 **3D Gaussian Splatting (3DGS)** 转移。
*   我们选择 **.ply 格式的 3DGS** 作为核心交付标准。
*   **优势**: 渲染速度极快，能够完美表达电影画面的复杂光影和半透明材质（如烟雾、毛发），这是传统 Mesh 难以做到的。

### 2.3 渲染层 (Rendering Layer)
生成了 .ply 文件后，如何高质量地看它？
*   **Python Native (gsplat)**: 我们集成了 NVIDIA 的 **gsplat** 库。这是一个基于 CUDA 的可微光栅化器，能在 Python 中直接实现 1000fps+ 的渲染。
*   **Web Viewer**: 对于非开发人员，我们使用标准的 WebGL Viewer (如 Polycam / Luma)，这要求我们输出标准的 PLY 格式。

---

## 3. 已完成工作详解 (Executed Milestones)

我们通过一系列工程攻坚，打通了上述所有环节：

### Phase A: TRELLIS 本地化部署 (最困难的一环)
*   **依赖地狱**: 解决了 `spconv` (稀疏卷积库) 在 PyTorch 2.4 + CUDA 12.1 下的崩溃问题 (`SPCONV_ALGO=native`)。
*   **代码修补**: 发现 TRELLIS 依赖的 `utils3d` 库与现有环境冲突，我们**手动重写了核心数学模块** (使用 `scipy` 替换)，移除了对 `utils3d` 的依赖。
*   **成果**: 编写了 `run_trellis_local.py`，成功生成了 `07956.ply` 和 `12322.ply`。

### Phase B: ml-sharp 对照组验证
*   **快速验证**: 部署了 Apple 的 ml-sharp 模型，用于生成对比样本。
*   **对比**: 确认 ml-sharp 生成的文件 (64MB) 远大于 TRELLIS (16MB)，证明 TRELLIS 的结构化压缩更有效。

### Phase C: 高性能渲染集成 (NVIDIA gsplat)
这是我们的**杀手锏**。为了在 Python 中看清楚生成的模型，我们：
1.  **独立环境**: 搭建了 `nvidia_opt` 环境，从源码编译了 `gsplat v1.5.3`。
2.  **渲染脚本**: 开发了 `run_gsplat_render.py`。
3.  **工程优化**:
    *   **尺度修复**: 解决了 AI 生成模型尺度极小 (mm级别) 导致的不可见问题，实现了 **World Scale (10x)** 自动放大。
    *   **画质增强**: 发现原始模型缺乏光照，我们利用法线信息实现了 **合成光照 (Synthetic Lighting)**，并增加了 Gamma 校正，将渲染分辨率提升至 **1024p**。

---

## 4. 技术模块关系图 (The Relationship)

```mermaid
graph TD
    Input[单张电影图像 Input] --> TRELLIS[Microsoft TRELLIS]
    Input --> SHARP[Apple ml-sharp]
    
    subgraph Generative_Core [生成核心]
        TRELLIS -->|解码| Latents[Structured Latents]
        Latents -->|转换| PLY1[Trellis 3DGS (.ply)]
        SHARP -->|直接预测| PLY2[Sharp 3DGS (.ply)]
    end
    
    subgraph Optimization [优化与后处理]
        PLY1 --> Scale[World Scaling (x10)]
        PLY1 --> RescaleScript[export_rescaled_ply.py]
    end
    
    subgraph Rendering [渲染与应用]
        Scale --> gsplat[NVIDIA gsplat]
        RescaleScript --> WebViewer[Web/External Viewers]
        gsplat -->|光栅化| Video[1024p MP4 视频]
        gsplat -->|可微渲染| Refinement[未来: 纹理精修]
    end
```

## 5. 总结
目前，您已经拥有了一套 **完整的、本地化的、基于 AI 的 3D 资产生产线**。
您不需要关心底层的数学公式，只需要运行我们封装好的脚本 (`run_trellis_local.py` 和 `run_gsplat_render.py`)，即可完成从 **"一张照片"** 到 **"高质量 3D 视频"** 的全过程。
