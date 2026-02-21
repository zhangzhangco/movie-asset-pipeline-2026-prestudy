# 2026 电影级数字资产导入管线设计方案
# (Digital Asset Import Pipeline Design 2026)

**版本**: 1.2 (SOP-Aligned)
**作者**: zhangxin
**日期**: 2026-02-05

---

## 1. 设计概述 (Executive Summary)

本方案旨在建立一套集**摄取、路由、生产、管理**于一体的自动化资产处理体系。根据最新的实验验证（2026.02），我们将管线逻辑从单纯的“素材分类”升级为**“交付能级路由” (Delivery-Tier Routing)**。

核心原则：**“按需路由，标准封装”**。利用 AI 感知能力自动分发至**敏捷管线 (Agile)** 或 **沉浸管线 (Immersive)**。

## 2. 目录结构设计 (Directory Structure)

保持一致的**“流式处理”**结构：

```text
/home/zhangxin/2026Projects/preStudy/
├── assets/
│   ├── 00_Inbox/                # [进件区] 挂载原始素材 (EXR/MP4/PNG)
│   ├── 01_Staging/              # [工坊区] 任务执行空间
│   │   ├── Agile_Tasks/         # Pipe A：快速重建任务
│   │   └── Immersive_Tasks/     # Pipe B：3DGS 深度训练任务
│   └── 02_Library/              # [资产库] 最终交付成品 (Read-Only)
│       ├── Environment/         # 大尺度场景/底板 (3DGS)
│       └── Props/               # 独立道具 (Mesh/GS)
```

## 3. 核心工作流 (Core Workflow)

引入 **Dual-Track Branching** 以支持差异化能级生产。

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#4f46e5', 'edgeLabelBackground':'#fef3c7', 'tertiaryColor': '#fffbec'}}}%%
graph TD
    %% Nodes
    Inbox[📂 00_Inbox: 原始素材]
    PreFlight{🛡️ 合规预检\n(ACEScg/16bit)}
    Identify{🤖 策略路由\n(SOP A/B Choice)}
    
    subgraph Staging_Zone [01_Staging: 智能工坊]
        direction TB
        subgraph TrackA [Track A: 敏捷生存 - Pipe A]
            Agile_Spat[DUSt3R 几何对齐] --> Agile_Mesh[TRELLIS 拓扑生成]
        end
        
        subgraph TrackB [Track B: 沉浸优化 - Pipe B]
            Imm_SfM[GLOMAP 相机解算] --> Imm_Train[3DGS 深度训练\n30k Iters]
        end
    end
    
    QC{🔍 交付质检\n(DOIB Check)}
    Library[🏛️ 02_Library: 资产库]

    %% Edges
    Inbox --> PreFlight
    PreFlight -->|OK| Identify
    
    Identify -->|快周转/单图| TrackA
    Identify -->|高保真/视频| TrackB
    
    TrackA --> QC
    TrackB --> QC
    
    QC -->|Pass| Packager[📦 USD/MTS 封装]
    Packager --> Library
```

## 4. 关键组件增强 (Component Enhancements)

### 4.1 动态深度训练 (Immersive Track B)
*   **训练引擎**: Vanilla 3DGS。
*   **优化策略**: 针对 2026.02 提出的“抽帧加密”策略，进件脚本将根据视频时长自动计算最优采样率（目标：Interval 2-5）。
*   **监控**: 集成 Tensorboard 导出，实时跟踪平滑度指标。

### 4.2 智能路由选择 (Strategy Router)
*   **逻辑**: 
    *   单张/少视点图片 -> 默认 Track A。
    *   大于 100 帧的连续序列 -> 建议 Track B。
    *   Hero Prop 语义标签 -> 强制触发 Track A 的 Mesh 拓扑重构。

### 4.3 自动化元数据 (MTS Generation)
*   **DOIB 注入**: 在 `Packager` 阶段，通过调用 `digitial_object_id_api` 获取国家级唯一标识码。
*   **MTS Sidecar**: 记录所有训练超参数（Iterations, Sampling Rate, Learning Rate）。

## 5. 实施进度

*   **P1 (Agile Entry)**: 封装 DUSt3R & TRELLIS (Done)。
*   **P2 (Immersive Refinement)**: 建立基于 GLOMAP 的全自动训练脚本 (Active)。
*   **P3 (Quality Gates)**: 实现基于 ACEScg 的自动化色彩空间转换与质检流程。

---
*设计变更记录*: V1.2 版本将“资产类型驱动”调整为“交付目标驱动”，统一了设计方案与 SOP (V1.1) 的逻辑基准。
