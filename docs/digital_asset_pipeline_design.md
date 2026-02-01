# 2026 电影级数字资产导入管线设计方案
# (Digital Asset Import Pipeline Design 2026)

**版本**: 1.1 (Enhanced Draft)
**作者**: zhangxin
**日期**: 2026-01-30

---

## 1. 设计概述 (Executive Summary)

为了支撑 "Hybrid 3D Pipeline" (混合 3D 生产线)，并实现**“电影数字资产智能处理中心”**的愿景，本方案旨在建立一套集**摄取、路由、生产、管理**于一体的自动化管线。

核心理念：**"顺便" (Incidental Intelligence)** —— 在完成基础资产转化的同时，利用已有的 AI 算力自动产出材质、代理、元数据和合规报告。

## 2. 目录结构设计 (Directory Structure)

采用 **"流式处理 + 多维库式管理"** 结构。

```text
/home/zhangxin/2026Projects/preStudy/
├── assets/
│   ├── 00_Inbox/                # [进件区] 拖入原始素材 (EXR/PNG)
│   ├── 01_Staging/              # [工坊区] 流水线正在处理的任务
│   │   ├── <AssetID>_Task/
│   │   │   ├── input.exr
│   │   │   ├── report.json      # [新增] 技术合规性报告
│   │   │   ├── masks/ (SAM2)
│   │   │   ├── dust3r_out/
│   │   │   └── trellis_out/
│   └── 02_Library/              # [资产库] 最终交付成品 (Read-Only)
│       ├── Props/               # 道具库 (Object-Centric)
│       │   └── <Category>/<AssetID>/
│       │       ├── model_high.ply    # 高模 (Render)
│       │       ├── model_proxy.fbx   # [新增] 低模代理 (Anim)
│       │       └── ...
│       ├── Scenes/              # 场景库 (Scene-Centric)
│       ├── Materials/           # [新增] 材质库 (PBR Texture Sets)
│       │   └── <Style>/<MatID>/
│       │       ├── basecolor.png
│       │       ├── normal.png
│       │       ├── roughness.png
│       │       └── material.mtlx     # MaterialX 标准描述
│       └── References/          # [新增] 参考图库 (On-Set Refs)
│           └── <Scene>/<Shot>/
```

## 3. 核心工作流 (Core Workflow)

引入 **Branching DAG** (分支有向无环图) 以支持多类型资产分发。

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#4f46e5', 'edgeLabelBackground':'#fef3c7', 'tertiaryColor': '#fffbec'}}}%%
graph TD
    %% Nodes
    Inbox[📂 00_Inbox: 原始素材]
    PreFlight{🛡️ 技术合规预检}
    ErrorBin[❌ 错误归档]
    
    Identify{🤖 AI 语义路由\n(VLM + SAM2)}
    
    subgraph Staging_Zone [01_Staging: 智能工坊]
        %% Track Definitions
        TrackA[Track A: 场景重建\n(DUSt3R)]
        TrackB[Track B: 道具生成\n(TRELLIS)]
        TrackC[Track C: 材质生成\n(AI PBR Gen)]
        TrackD[Track D: 现场参考\n(OCR/Logging)]
        
        %% Processing
        LOD_Gen[📉 Auto Proxy\n(Decimation)]
        Tag_Gen[🏷️ Semantic Tagging\n(VLM Enrichment)]
    end
    
    Library[🏛️ 02_Library: 智能资产库]

    %% Edges
    Inbox --> PreFlight
    PreFlight -->|合规: ACEScg/16bit| Identify
    PreFlight -->|违规: sRGB/8bit| ErrorBin
    
    Identify -->|物体 Object| TrackB
    Identify -->|场景 Scene| TrackA
    Identify -->|纹理 Texture| TrackC
    Identify -->|参考 Reference| TrackD
    
    TrackA --> LOD_Gen
    TrackB --> LOD_Gen
    
    LOD_Gen --> Tag_Gen
    TrackC --> Tag_Gen
    
    Tag_Gen --> Packager[📦 USD Packaging\n(GB/T 36369 ID)]
    Packager --> Library
```

## 4. 关键组件增强 (Component Enhancements)

### 4.1 技术合规预检 (Pre-flight Check)
*   **位置**: `ingest_asset.py` 的第一步。
*   **功能**: 使用 `OpenImageIO` 检查文件头。
    *   色彩空间: 必须为 Linear (ACEScg/Rec.709-Linear)。
    *   位深: 必须 >= 16-bit Float (EXR) 或 16-bit Int (EXR/PNG for Masks)。
    *   分辨率: 必须 >= 2K。
*   **动作**: 失败则重命名文件 (`_INVALID_COLOR.exr`) 并终止流程。

### 4.2 智能路由与元数据 (Router & Semantic Metadata)
*   **功能**: 集成 VLM (视觉大模型) 进行深度理解。
*   **元数据标准升级**:
```json
{
  "identifiers": {
    "local_id": "prop_20260130_ae3f",
    "gbt_36369_id": "10.5000.1/CN.FILM.ASSET.2026.0001",  // GB/T 36369 电影数字对象标识符
    "iso_26324_doi": "10.xxxxx/xxxx"                       // ISO 26324 兼容
  },
  "type": "PROP",
  "tags": {
    "visual_style": ["Cyberpunk", "Distressed"],
    "material_inference": ["Rusty Metal", "Painted Plastic"],
    "mood": ["Gloomy", "Industrial"]
  },
  "technical_compliance": {
    "input_colorspace": "ACEScg",
    "verified": true
  },
  "files": {
    "high_poly": "model_high.ply",
    "proxy": "model_proxy.fbx"
  }
}
```

### 4.3 自动化 LOD (Auto Proxy)
*   **工具**: `meshlab` 或 `fast-simplification` 算法。
*   **策略**:
    *   **High**: 原始 3DGS 输出 (用于渲染)。
    *   **Proxy**: 转换为 Mesh -> 减面至 5000 面 -> 烘焙简单的 Vertex Color (用于 Maya/Houdini 视窗操作)。

## 5. 实施路线图 (Implementation Roadmap)

*   **Phase 1 (基础架构)**:
    *   实现目录结构与基础 `ingest` 脚本 (含重命名逻辑)。
    *   实现 Track B (Trellis) 的自动触发。
*   **Phase 2 (合规与元数据)**:
    *   集成 `OpenImageIO` 进行 Pre-flight。
    *   定义 `metadata.json` 读写接口。
*   **Phase 3 (扩展能力)**:
    *   集成 VLM 进行语义打标。
    *   开发 LOD 减面脚本。
    *   开发 Texture -> MaterialX 转换节点。

---
*设计变更记录*: V1.1 版本采纳了用户关于 PBR、LOD、语义搜索、合规检查及参考库管理的建议，显著提升了管线的工业化潜力。
