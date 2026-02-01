# 专家评审意见：关于“电影数字资产导入管线 V1.1”的合规性分析
# (Expert Review: Compliance Analysis for National Film Digital Asset Platform)

**评审对象**: 电影级数字资产导入管线设计方案 V1.1
**评审视角**: 国家电影数字资产平台 (National Film Digital Asset Platform) 架构专家
**日期**: 2026-01-30

---

## 1. 总体评价 (General Assessment)

该方案设计思路清晰，技术选型（DUSt3R, TRELLIS, 3DGS）处于 2026 年国际前沿水平。V1.1 版本提出的“混合管线”和“智能处理中心”概念，不仅解决了生产效率问题，还通过“顺便”生成的元数据和代理资产，极大提升了资产的可用性。

**结论**: 从**技术先进性**和**生产实用性**角度，该方案是非常合理的，完全可以作为“国家平台”的**核心生产节点 (Production Node)**。

**但是**，作为“国家级平台”的基础设施，目前的 V1.1 版本在**互操作性 (Interoperability)**、**长期保存 (Preservation)** 和 **版权治理 (Governance)** 三个维度上还存在显著缺口。

---

## 2. 关键缺口与改进建议 (Critical Gaps & Recommendations)

### 2.1 格式标准缺口：从 PLY 到 OpenUSD
*   **现状**: 交付物核心是 `.ply` (3DGS) 和 `metadata.json`。
*   **问题**: `.ply` 只是渲染数据，不是资产交换标准。国家平台要求资产必须具备跨软件、跨引擎的通用性。单纯的 PLY 文件丢失了场景层级关系，且无法被非 3DGS 引擎优雅降级处理。
*   **专家建议**: **必须引入 OpenUSD (.usdez / .usd)**。
    *   不应只交付 `model.ply`。
    *   应交付一个 `asset.usd`，在其中引用 `model.ply` 作为渲染表达，同时引用 `model_proxy.fbx` 作为视窗表达。
    *   **架构调整**: 在 `Library` 阶段增加 `USP Packager` 步骤。

### 2.2 标识符体系缺口：从 Local ID 到 EIDR/DOI
*   **现状**: 使用 `prop_20260130_ae3f` (时间戳+哈希) 作为 ID。
*   **问题**: 这是“孤岛 ID”。国家平台需要跨库检索，资产可能在不同制作公司间流转。
*   **专家建议**: **严格遵循 GB/T 36369 国家标准**。
    *   **国标落地**: 首选支持 **GB/T 36369-2018 (电影数字对象标识符)**，这是建设国家级平台的法理基础。
    *   **国际兼容**: 兼容 **ISO 26324 (DOI System)** 标准，确保资产具备全球唯一性与解析能力。
    *   **架构调整**: 元数据 Schema 中必须强制保留 `gbt_36369_id` (e.g., `10.5000/film.asset...`) 字段。

### 2.3 版权与确权：AI 生成的“出生证明”
*   **现状**: 虽然有 `author` 字段，但缺乏防篡改机制。
*   **问题**: 生成式 AI 资产的版权归属在 2026 年依然敏感。国家平台需要明确区分“人类创作”与“AI 生成”，并追踪“源素材版权”。
*   **专家建议**: **C2PA 数字水印与谱系追踪**。
    *   记录 `lineage` (谱系)：由哪张 Input 图片生成？该 Input 图片的版权方是谁？
    *   建议在生成的纹理或元数据中嵌入隐形水印，通过 `source_tech: TRELLIS` 明确标记为 AI 生成物 (AIGC)，符合国家对 AI 内容标识的法规要求。

### 2.4 数据长期保存 (Long-term Preservation)
*   **现状**: 保存了 `model.ply`。
*   **问题**: 3DGS 技术迭代极快 (2023-2026 已经换了 5 代)。今天的 `.ply` 可能 5 年后就无法高效渲染。
*   **专家建议**: **双重归档策略**。
    *   不仅保存“渲染态” (PLY)，必须永久保存“源头态” (Input Image + Mask + Camera Parameters)。
    *   只要源头在，5 年后可以用更新的算法 (e.g., 4D-GS) 重新“烘焙”资产。

---

## 3. 修正后的架构建议 (Revised Architecture)

建议在 V1.2 中，在 `02_Library` 阶段之前增设一层 **"Packager (封装层)"**：

```mermaid
graph LR
    Input[生产侧数据] --> Packager[📦 USD 封装器]
    
    subgraph USD_Package [Asset.usd]
        Meta[元数据\n(Rights, Lineage)]
        Payload[Payload\n(High-Res PLY)]
        Proxy[Proxy\n(Low-Res Mesh)]
    end
    
    Packager --> USD_Package
```

**总结**：设计非常出色，只需补齐 **USD 封装** 和 **版权元数据** 两块拼图，即可从“工作室级工具”跃升为“国家基础设施级方案”。

---

## 4. 2026-01-30 现场评测反馈 (Live Audit Findings)

### 4.1 模型可用性评估 (Model Usability)
*   **DUSt3R (Naver)**: 
    *   **几何表现**: 单图模式下点云过于稀疏，细节丢失严重，被称为“看不清”。
    *   **改进**: 采用 `Tiled Inference` (1024x1024 分块) 后，点云密度提升至 300万点+，几何轮廓清晰可见，但仍残留噪点。
    *   **定位**: 适合作为**空间参考 (Layout/Geometry)**，不适合直接作为渲染资产。
*   **ml-sharp (Apple)**:
    *   **视觉表现**: 生成的 3DGS 视觉连贯性极佳，通过 Video Preview 确认无闪烁。
    *   **定位**: 确认为**虚拟拍摄背景 (Backplate)** 的首选方案。
*   **TRELLIS (Microsoft)**:
    *   **定位**: 确认仅用于 **“道具级 (Hero Asset)”** 生成，严禁用于场景重建。

### 4.2 修正策略 (Correction Strategy)
*   **分治法**: 放弃“单一大一统模型”幻想。
    *   **背景**: 走 ml-sharp 通道 -> 烘焙为环境球/背景板。
    *   **前景**: 走 TRELLIS 通道 -> 生成 Mesh/GS 道具。
    *   **融合**: 利用 DUSt3R 提供的深度与法线信息进行合成时的遮挡关系处理 (Z-Compositing)。
