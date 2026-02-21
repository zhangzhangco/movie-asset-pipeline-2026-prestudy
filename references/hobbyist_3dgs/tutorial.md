# 🎥 Gaussian Splatting 零成本实战教程：从视频到 Blender 三维模型

本文档总结了使用全免费软件进行 **Gaussian Splatting (高斯泼溅)** 建模的完整流程。通过这种方式，你可以利用家庭视频、现成素材或照片集，快速生成具有画意感（Impressionistic）且能捕捉光学细节、空间氛围与表面材质的高质量三维点云。

---

## 🛠️ 工具准备
在开始之前，请确保下载并准备好以下软件/插件：

| 步骤 | 软件/插件 | 功能说明 |
| :--- | :--- | :--- |
| **Step 1** | [Blender](https://www.blender.org/) | 视频抽帧、模型展示与合成渲染 |
| **Step 2** | [COLMAP](https://colmap.github.io/) | 摄影测量（Photogrammetry）基础计算 |
| **Step 3** | [Glow Map](https://github.com/cvg/GlowMap) | 加速摄影测量重建过程 (更高效) |
| **Step 4** | [Python Script (run_glowmap.py)](https://github.com/...) | 用于运行 Glow Map 的自动化脚本 |
| **Step 5** | [Photogrammetry Importer](https://github.com/...) | Blender 插件，用于导入 COLMAP 数据 |
| **Step 6** | [Brush App](https://github.com/...) | 核心工具：生成 Gaussian Splatting 模型 |
| **Step 7** | [Kiri 3DGS Render](https://github.com/...) | Blender 插件，用于实时渲染高斯泼溅点云 |

---

## 📋 详细操作流程

### 第一阶段：视频预处理（抽帧）
1. 打开 **Blender 4.5**，切换至 `Video Editing` 工作区。
2. 将视频素材拖入时间轴，按 `Ctrl + T` 查看总帧数。
3. **优化建议**：如果视频过长（超过 400 帧），建议在 `Output Properties` 中将 `End Frame` 限制在 250 左右。
4. **调整速率**：选中片段按 `Ctrl + R`，拖动右侧关键帧指示器至场景结尾以重新映射时长。
5. **导出设置**：
   - 目标文件夹：新建 `images` 文件夹。
   - 格式：选择 **PNG** (最高质) 或 **JPEG**。
6. 点击 `Render -> Render Animation` 导出所有静态帧。

### 第二阶段：环境配置
1. **下载编译器**：下载 `COLMAP` 和 `Glow Map` 的 Windows CUDA 版本。
2. **设置环境变量**：
   - 搜索并打开系统的“编辑系统环境变量”。
   - 在 `Path` 中分别添加 `COLMAP/bin` 和 `glowmap/bin` 的绝对路径。
   - 这样系统才能在 CMD 中调用这些可执行文件。

### 第三阶段：跑通摄影测量（Glow Map）
1. 在包含 `run_glowmap.py` 的文件夹路径输入 `cmd` 打开命令行。
2. 输入命令：
   ```bash
   python run_glowmap.py --image_path [将你的images文件夹拖入窗口]
   ```
3. 等待计算完成（视频示例中 175 帧约耗时 76 秒）。

### 第四阶段：Blender 场景对齐
1. 安装并重启 Blender。
2. **安装依赖**：在插件偏好设置中，依次点击安装 `setup tools`, `pillow`, `lazrs`, `laspy`, `point_cloud`。
3. **导入模型**：
   - `File -> Import -> COLMAP Model Workspace`。
   - 选择项目下的 `sparse/0` 文件夹进行导入。
4. **对齐与层级**：全选生成的相机和点云，以 `OpenGL Point Cloud` 为父级进行旋转调整。

### 第五阶段：生成 Gaussian Splat (Brush)
1. 打开 **Brush App**。
2. `Directory` 选择项目根目录。
3. 点击 `Start` 开始训练。
   - *提示*：训练过程中可以使用 `WASD` 移动查看实时生成的点云。
4. 达到满意效果（如 10,000 步）后，点击 `Export` 导出 `.ply` 文件。

### 第六阶段：最终渲染与合成
1. 在 Blender 中使用 **Kiri 3DGS Render** 插件导入导出的 `.ply`。
2. 将高斯点云父级关联至之前的排布空物体，实现完美对齐。
3. **合成效果**：
   - 开启 `Render` 模式预览。
   - 支持在场景中添加真实的 3D 物体（如 Cube 或 Suzanne），并开启 `Combine with Native Render` 进行深度混合渲染。

---

## ⚠️ 版本说明
- 大部分步骤支持最新的 **Blender 5** 系列。
- 但 **第四步（导入 PHOTOGRAMMETRY 模型）** 目前在 Blender 5 中可能存在兼容性问题，建议该步骤使用 Blender 4 系列，或者关注插件后续的更新补丁。

---
*Author: zhangxin*
