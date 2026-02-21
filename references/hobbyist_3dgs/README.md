# Gaussian Splatting Hobbyist Workflow - Reference Material

这个文件夹包含了视频教程中提到的所有相关资源、脚本和链接。

## 📁 文档与脚本
- **[tutorial.md](./tutorial.md)**: 视频教程的详细中文操作手册。
- **[run_glomap.py](./run_glomap.py)**: 用于自动化运行 COLMAP/GLOMAP 的 Python 脚本。

## 🔗 相关链接与资源

### 核心软件
- **COLMAP**: [https://github.com/colmap/colmap](https://github.com/colmap/colmap)
- **GLOMAP**: [https://github.com/colmap/glomap](https://github.com/colmap/glomap)
- **Brush App**: [https://github.com/ArthurBrussee/brush](https://github.com/ArthurBrussee/brush)

### Blender 插件
- **Photogrammetry Importer**: [https://github.com/SBCV/Blender-Addon-Photogrammetry-Importer](https://github.com/SBCV/Blender-Addon-Photogrammetry-Importer)
- **3DGS Render (KIRI Engine)**: [https://github.com/Kiri-Innovation/3dgs_blender_addon](https://github.com/Kiri-Innovation/3dgs_blender_addon)

### 视频素材
- **Tutorial Footage (by Henry)**: [https://www.pexels.com/video/aerial-footage-of-a-residential-area-near-the-hill-20235213/](https://www.pexels.com/video/aerial-footage-of-a-residential-area-near-the-hill-20235213/)

---

## 🛠️ 快速命令参考

**运行摄影测量重建：**
```bash
# 确保你的图片路径没有空格
python run_glomap.py --image_path /path/to/your/images
```

**如果重建失败（尝试竭尽匹配）：**
```bash
python run_glomap.py --image_path /path/to/your/images --matcher_type exhaustive_matcher
```

---

## 📜 时间轴
- 00:00 简介
- 00:46 视频转帧
- 02:49 安装 COLMAP 与 GLOMAP
- 04:41 计算摄影测量模型
- 05:57 转换模型
- 08:34 创建高斯泼溅
- 10:40 导入 Blender
- 13:10 未来展望...

---
*Note: run_glomap.py 脚本已根据最新版本 colmap/glomap 进行修正（由 @rattt 提供）。*
