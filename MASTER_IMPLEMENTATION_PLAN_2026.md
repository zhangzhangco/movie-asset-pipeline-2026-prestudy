# 电影内容资产化管线（Pre-Study 2026）全景实施计划总纲 (V1.3.1)

**文档状态：防返工终版 (Anti-Rework Final Version)。** 本版本在 V1.3 基础上，对路由兜底、Manifest 字段、命名约定、失败留痕等施工细节进行了最终锁定，是项目 Phase 7+ 阶段唯一的、可直接拆解为工单的执行依据。

---

## 0. 背景与范围
### 0.1 项目背景
国家电影数字资产平台需要将传统“观看型”电影内容转化为“可计算型”数字资产。本 Pre-Study 聚焦于 **Pipeline A：空间资产化管线** 的技术验证，即从 2D 电影素材自动生成可管理的 3D 资产，并形成可审计的工程闭环。

### 0.2 本阶段验证范围
*   **道具（Prop）**：从单帧生成可导入的 mesh 资产。
*   **人物（Human）**：从单帧生成拓扑一致的结构化人体资产。
*   **场景（Scene）**：从单帧生成可渲染的 3D 表示（以 3DGS 为主）。

*预留接口（本轮不作为必过项）：少视图静帧重建、视频序列重建。*

### 0.3 本阶段核心目标（最小闭环）
1.  **端到端闭环**：输入电影帧 → 自动产出资产文件与报告。
2.  **多后端可对比**：同一输入可在不同后端下并排展示结果。
3.  **标准化可交付**：提供可导入的 mesh (GLB/OBJ) 或可预览的 3D 表示 (`.ply`+截图)。
4.  **可追溯可复现**：每个 Session 生成 manifest 与版本/参数快照。

### 0.4 交付形态优先级
*   **优先交付**：Mesh（GLB/OBJ+贴图）+ 可追溯元数据。
*   **允许退化**：当 Mesh 导出不稳定时，允许以 `.ply` + `preview.png` 作为阶段性产物，并记录失败日志。

### 0.5 工程约束与共识
*   **路由必须可观测**：分流基于量化 signals，禁止“凭感觉”。
*   **失败也必须落盘**：任何失败都不得导致 Session 缺失，必须生成 manifest 与 report。
*   **以自家基准集为准**：不以外部论文指标作为验收指标。

---

## 1. 核心目标与工程原则
*   **四得原则**：跑得出、比得了、查得回、导得进。
*   **留痕完整原则**：即便某后端失败，也必须生成 Session 目录、Manifest 和 Report，并在报告中标记失败原因与日志位置。

---

## 2. 路由判定信号与规则

### 2.1 路由判定信号 (Signals)
*   `has_person`, `has_mask`, `area_ratio`, `num_instances`, `bg_score`。

### 2.2 路由规则表（含强制与兜底）
**强制路由**：若用户显式指定 `--asset_type prop|human|scene`，则**强制走指定类型**，仅在该类型内部进行后端选择。

| 目标路由 | 自动触发规则 (若未强制指定) |
| :--- | :--- |
| **Human (SAM 3DB)** | `has_person == true` |
| **复杂 Prop (SAM3D)** | `has_mask==true` \|\| `num_instances>1` \|\| `area_ratio<=0.5` |
| **简单 Prop (TRELLIS)** | `num_instances==1` && `area_ratio>0.5` && `bg_score==low` |
| **场景 (Scene)** | `兜底规则`：若未命中以上任何规则，则默认分配。 |

**兜底策略**:
*   **Scene 兜底**: 在 `--asset_type` 未指定时，若无法匹配 Human/Prop 规则，则默认分配至 `scene`。
*   **Prop 兜底**: 若 `--asset_type prop` 被指定，但判定信号缺失，则默认走 TRELLIS，并在 manifest 标记 `signals_incomplete=true`。

---

## 3. 产出物硬标准 (Deliverables)

### 3.1 Session 内多资产 Manifest Schema
`manifest.json` 必须支持单个 Session 内包含多个资产条目：
```json
{
  "session_id": "string",
  "inputs": {
    "files": ["path/to/image.png"],
    "sha256_map": { "image.png": "sha256_hash_string" }
  },
  "versions": {
    "pipeline_commit": "string",
    "runtime": { "python": "3.10.x", "torch": "2.x.x", "cuda": "11.x" }
  },
  "reproduce": { "command": "python pipeline_runner.py ..." },
  "assets": [
    {
      "asset_id": "person_001",
      "asset_type": "human",
      "status": "success",
      "backend_selected": "sam3d-body",
      "signals": { "has_person": true },
      "outputs": [ "assets/person_001/mesh.glb", "assets/person_001/params.json" ]
    },
    {
      "asset_id": "prop_001",
      "asset_type": "prop",
      "status": "failed",
      "backend_selected": "trellis.2",
      "signals": { "area_ratio": 0.6 },
      "outputs": [],
      "error": { "type": "ExportError", "message": "Mesh has non-manifold edges.", "log_path": "logs/prop_001.log" }
    }
  ]
}
```
**版本采集规则**: `version` 优先使用 `git commit`；否则使用 `pip package==version`。

### 3.2 输出目录强制命名约定
*   `assets/person_<NNN>/` 必含: `mesh.glb` (或 `mesh.obj`), `params.json`, `preview.png`。
*   `assets/prop_<NNN>/` 必含: `mesh.glb` (或 `splat.ply`), `preview.png`。
*   `scene_visual/` 必含: `scene.ply`, `views/view_01.png`, `views/view_02.png`, `views/view_03.png`。

### 3.3 “导得进”自动化验收接口
*   **必做**: 对 `*.glb` 运行 `blender -b -P scripts/check_import.py -- <file>`，输出 `import_ok=true/false` 及统计信息。
*   **可选**: Unity 校验脚本后置。

### 3.4 GB/T 元数据与 Provenance 字段补齐
*   `parameters_snapshot`: 关键参数字典。
*   `run_log_paths`: stdout/stderr 日志文件路径。

### 3.5 SAM 3D Body 失败留痕
若 3DB 失败且无 `params.json`：必须输出 `failure.json` (原因, 日志指针) 与 `preview.png` (输入图+检测框/Mask可视化)。

---

## 4. 施工步骤分解 (Execution Steps)

*   **Step 1: 带标签基准集建设 (Owner: E)**: 挑选图像并编写 `assets/test_dataset/labels.json`。
*   **Step 2: 编排框架与 Manifest 落地 (Owner: A)**: 实现路由判定逻辑与多资产 Manifest 生成。
*   **Step 3-5: 各后端专项集成 (Owners: B, C, D)**: 分别接入 TRELLIS, SAM 3D Body, 场景链路。
*   **Step 6: 报告与验收自动化 (Owner: A)**: 升级报告系统，集成自动化导入检查接口。

---

## 5. 风险与缓解 (Risk & Mitigation)

*   **Risk 1**: SAM 3D Body 模型 Gated 无法下载。
    *   *Mitigation*: 使用 Mock 资产先行跑通打包与报告逻辑。
*   **Risk 2**: 不同模型 Conda 环境冲突。
    *   *Mitigation*: 严格执行环境隔离，通过 `pipeline_runner` 调用不同环境的 Python 解释器。

---
**版本**: V1.3.1 (防返工终版)  
**Author**: zhangxin
