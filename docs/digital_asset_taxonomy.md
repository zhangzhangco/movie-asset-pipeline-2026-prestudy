# 国家电影数字资产平台：AI 赋能的资产化管线标准 (v2.1)
# (National Movie Digital Asset Platform: AI-Empowered Ingestion Standards)

**文件密级**: 内部预研 (Pre-Study)
**适用范围**: Phase 8 原型开发、学术论文撰写
**最后更新**: 2026-01-31

---

## 1. 战略定位与核心理念 (Strategic Vision)

### 1.1 核心使命
本平台不仅仅是一个存储模型的文件库，而是 **国家文化数字化的基础设施 (National Cultural Digital Infrastructure)**。
我们的使命是：**将非结构化的电影影像资源，转化为结构化、可溯源、可计算的国家级数字资产。**

### 1.2 为什么必须“提前拆解入库”？ (Why Pre-ingestion?)
针对“On-demand（按需生成）”的质疑，我们确立了建设国家级平台的三个不可替代的战略支柱：

1.  **资产确权与溯源 (Provenance is Sovereignty)**
    *   AI 生成具有概率性，而国家资产需要确定性。
    *   只有通过“入库”确权，赋予 DOIB (数字对象唯一标识符)，才能将“像素”转化为法律意义上的“资产”，防止数字资产的流失与滥用。
2.  **结构化检索 (Decomposition is Indexing)**
    *   未拆解的电影只是数据沼泽。
    *   通过 AI 预先提取语义与结构，构建知识图谱，才能实现“检索明代建筑”、“检索秦朝服饰”的各类复杂查询。
3.  **工业标准统一 (Interoperability)**
    *   为了赋能游戏、文旅等下游产业，必须将异构数据清洗为统一的工业标准 (USD/GB-T)。这需要集中的算力与治理，而非分散的临时转换。

---

## 2. 资产化管线分层架构 (Pipeline Taxonomy)

我们将传统的“模型分类”升级为 **“智能摄取管线” (Intelligent Ingestion Pipeline)** 的四个流水线层级：

### Level 1: 源数据采集层 (Source Ingestion Layer)
> **"The Raw Material"**
*   **定义**: 电影数字母版 (DCP) 或胶片扫描件的原始数据摄入。
*   **输入**: EXR Sequence, Log Footage.
*   **关键动作**: 
    *   镜头切分 (Shot Segmentation).
    *   元数据显示 (Metadata Ingres): 提取片名、年代、场次信息。

### Level 2: 智能解构层 (Intelligent Decomposition Layer)
> **"The AI Engine"** —— *本项目的核心技术攻关点*
*   **定义**: 利用多模态 AI 模型，将扁平的画面拆解为独立的资产元素。
*   **四大拆解模组**:
    1.  **视觉拆解 (Visual)**: 前景 (Mesh/NeRF) 与 背景 (3DGS) 的分离。
    2.  **动态拆解 (Dynamic)**: 识别可动结构（如车轮、门轴），推断关节 (Articulation)。
    3.  **物理拆解 (Physical)**: 估算材质属性 (Roughness/Metalness) 和 去光照 (Delighting)。
    4.  **逻辑拆解 (Logical)**: 语义识别 (Tagging)，如“汉代”、“青铜器”。

### Level 3: 标准化封装层 (Standardization Layer)
> **"The Digital Ledger"**
*   **定义**: 将拆解出的碎片封装为符合国家标准的通用格式。
*   **核心格式**: **USD (Universal Scene Description)** + **GB/T 36369 元数据**。
*   **产物**:
    *   `Asset Card`: 资产身份证（含 DOIB、版权方、来源时间码）。
    *   `Asset Payload`: 物理数据包（几何、贴图、骨骼）。

### Level 4: 跨界服务层 (Service & Application Layer)
> **"The Value Outlet"**
*   **定义**: 面向全社会的资产分发接口。
*   **主要场景**:
    *   **游戏开发**: 为《黑神话》等国产 3A 提供高精度的历史文物资产。
    *   **沉浸文旅**: 博物馆虚拟展厅的快速构建。
    *   **AI 训练**: 为下一代国产 AIGC 模型提供高质量的 3D 语义数据集 (Sovereign AI Infrastructure)。

---

## 3. 下一步原型规划 (Phase 8 Prototype)

### 实验代号: `Intelligent Dynamic Ingestion`
*   **目标**: 演示一段电影画面的全自动入库过程。
*   **特征**: 
    *   **动静分离**: 能够把一辆马车从背景中“抠”出来，并且车轮是“活”的。
    *   **自动建档**: 屏幕右侧实时滚动显示 AI 识别出的资产信息（年代、材质、DOIB）。

---

## 4. 技术实现规范 (Technical Implementation Specifications)
*本章节恢复了 v1.0 中定义的具体文件格式标准，用于指导工程实现。*

### 4.1 几何与视觉标准 (Geometry & Visuals)
*   **前景道具 (Hero Props)**:
    *   Format: `.ply` (Processed 3DGS), `.obj/.glb` (Meshed).
    *   Process: Background Removal -> In-painting -> Meshing.
*   **环境背景 (Backplate)**:
    *   Format: `.ply` (3DGS Raw).
    *   Resolution: 2K~4K equivalent.
*   **空间布局 (Layout)**:
    *   Format: Point Cloud (`.ply`).
    *   Metric: Metric Scale (True World Size).

### 4.2 物理与外观标准 (LookDev & Physics)
*   **PBR 材质**:
    *   Maps: Albedo, Normal, Roughness, Metalness.
    *   Workflow: Metal/Roughness.
*   **光照探针 (Lighting Probe)**:
    *   Format: `.json` (SH Coefficients / RGB Ambient).
    *   Source: Inverse rendering from 3DGS.

### 4.3 动态与行为标准 (Dynamics & Behavior)
*   **骨骼/关节 (Rigging)**:
    *   Target: `UsdSkel` compliant hierarchy.
    *   Phase 8 Demo: 简单的 `xformOp` 旋转关节 (Revolute Joint).
*   **交互逻辑**:
    *   Metadata: `articulation_type` (e.g., "door_hinge", "wheel_axle").

### 4.4 封装标准 (Packaging)
*   **USD 组合结构**:
    *   `asset.usd`: 根文件，引用各层。
        *   `geo.usd`: 网格/GS数据。
        *   `mtl.usd`: 材质绑定。
        *   `rig.usd`: 骨骼与物理约束。
*   **元数据**:
    *   Standard: GB/T 36369-2018 (Digital Object Identifier).
    *   Fields: Title, Creator, CreationDate, Rights, SourceTimeCode.
