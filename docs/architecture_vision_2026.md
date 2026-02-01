
# 2026 电影级 3D 资产生成架构愿景 (Architecture Vision 2026)

**版本**: 1.0 (2026-01-30)
**核心理念**: **Hybrid 3D Pipeline (混合 3D 生产线)** —— 结合 "Scene Reconstruction" (场景重建) 与 "Asset Generation" (资产生成)。

---

## 1. 核心挑战与技术变革

在 2026 年的视角下，单张电影图像转 3D 面临两大核心矛盾：
1.  **场景 vs 物体**: 电影画面通常是大场景 (Scene)，而生成式 AI (如 TRELLIS) 训练时假设输入是单个物体 (Object)。强行用 TRELLIS 生成场景会导致空间畸变。
2.  **幻觉 vs 真实**: 电影制作既需要 AI 补全未见视角的细节 (Hallucination)，又严苛要求可见部分与原片绝对一致 (Fidelity)。

### 我们的解决方案：分而治之 (Divide and Conquer)

我们将流水线拆分为三个独立的专业轨道：

| 轨道 | 任务目标 | 核心技术 (SOTA 2026) | 选择理由 |
| :--- | :--- | :--- | :--- |
| **Track A: 场景重建** | 恢复场景的真实空间结构 (Walls, Floor, Layout)，不产生幻觉。 | **DUSt3R** (Metric 3D Reconstruction) | 传统的 SfM 需要多视角，而 DUSt3R 是 2026 年单目/少目重建的霸主，无需相机参数即可输出公制点云。 |
| **Track B: 道具生成** | 从画面中提取关键物体 (Hero Props)，生成高精度、可旋转的独立资产。 | **TRELLIS** (Structured Latents) | 相比 NeRF/SDS，TRELLIS 生成的几何拓扑更干净，支持导出标准 Mesh，适合作为独立资产复用。 |
| **Track C: 语义分割** | 将场景与道具剥离，自动打标。 | **Segment Anything 2 (SAM2)** | 交互式或自动分割的工业标准，能精准处理电影级复杂的遮挡关系。 |

---

## 2. 技术选型综述 (Technical Rationale)

### 2.1 为什么选择 TRELLIS 而非 DreamGaussian?
*   **DreamGaussian (2024)**: 基于 SDS 蒸馏，速度快但纹理模糊，几何只有大概轮廓。
*   **TRELLIS (2026)**: 基于 Structured Latents。它不是在“猜”像素，而是在解码 3D 结构。
*   **结论**: 电影资产要求 **Hard Surface** 级别的几何精度，TRELLIS 是目前的唯一解。

### 3. 应用场景分治 (Task-Specific Allocation)

本管线不再追求单一模型解决所有问题，而是根据电影制作的具体交付需求进行任务分配：

#### 3.1 虚拟拍摄背景重建 (Background Reconstruction)
*   **选用架构**: **ml-sharp**
*   **应用目标**: 生成视觉平滑、光影真实的 3DGS 背景。
*   **优势**: 能够快速复现图像的视觉观感，适合作为虚拟拍摄的远景或立体底座。
*   **状态**: 交付 3DGS 序列或 PLY。

#### 3.2 英雄资产自动化采集 (Hero Asset Harvesting)
*   **选用架构**: **TRELLIS**
*   **应用目标**: 从海量剧照中自动识别出“小玩意”（道具、饰品、武器等），并将其转化为具有精确几何细节的数字资产。
*   **优势**: 高精几何恢复，支持延迟着色 (Slang) 和 PBR 流程。
*   **工作流**: Detection -> Segmentation -> TRELLIS Reconstruction.

#### 3.3 空间骨架与校准 (Spatial Calibration)
*   **选用架构**: **DUSt3R / MASt3R**
*   **应用目标**: 恢复多视角的相机位姿和大规模场景的拓扑结构。
*   **优势**: 对于多图关联和视角对齐具有数学级鲁棒性，不作为视觉输出，而是作为几何校验基准。
*   **状态**: 交付空间布局 (Layout) 和相机标定数据。

### 4. 数据标准化 (GB/T 36369)
所有产物无论来自哪个分枝，最终都通过 `package_asset_gbt.py` 进行封装，进入统一的资产库平台。它通过 "Pointmap Regression" 直接预测每个像素的 3D 坐标。这意味着它能把电影画面的背景“推”到正确的深度平面上，形成类似剧场布景的 2.5D/3D 结构，为前景道具提供正确的空间容器。

### 2.3 为什么坚持 NVIDIA gsplat?
*   **渲染层**: 无论资产来自 A 还是 B，最终都需要统一渲染。
*   **gsplat**: 它是目前 Python 生态中最快、最灵活的可微光栅化器。它让我们可以在 Python 脚本中完成这一步 "Composition" (合成)，而不需要每次都导进 Unreal Engine。

---

## 3.  混合流水线架构 (The Hybrid Pipeline)

```mermaid
graph LR
    Input[单张电影画面] --> Seg{语义分割 (SAM2)}
    
    Seg -->|背景区域| TrackA[Track A: 场景重建]
    Seg -->|前景道具| TrackB[Track B: 资产生成]
    
    subgraph Scene_Layer [场景层]
        TrackA --> DUSt3R[DUSt3R 推理]
        DUSt3R --> ScenePC[场景点云/3DGS]
    end
    
    subgraph Prop_Layer [道具层]
        TrackB --> Inpaint[背景修复] 
        TrackB --> TRELLIS[TRELLIS 生成]
        TRELLIS --> PropGS[道具 3DGS/Mesh]
    end
    
    ScenePC --> Compose[场景组装 (Composition)]
    PropGS --> Compose
    
    Compose --> gsplat[NVIDIA gsplat 渲染]
    gsplat --> Output[最终 3D 镜头]
```

## 4. 后续执行计划

1.  **DUSt3R 集成**: 部署 DUSt3R 环境 (需 Torch 2.x)，验证单图重建能力。
2.  **Pipeline 串联**: 编写 `run_hybrid_pipeline.py`，实现 "分割 -> 重建/生成 -> 拼合" 的自动化流程。
3.  **资产库化**: 批量处理训练集，形成 "Props Library" (道具库) 和 "Scene Library" (场景库)。

---
*本文档基于 2026 年前沿技术综述与项目实战经验总结。*
