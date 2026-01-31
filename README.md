# Movie Assetization Pipeline (Pre-Study 2026)

This repository implements the **Hybrid 3D Generative Pipeline** for movie asset production. It orchestrates multiple state-of-the-art models (ml-sharp, DUSt3R, TRELLIS) into a unified, robust workflow for generating 3D assets from 2D movie stills.

## 🌟 Key Features

*   **End-to-End Orchestration**: A single command runs Scene Gen + Geometry + Asset Harvesting + 3D Gen (TRELLIS default; SAM3D Objects optional).
*   **Robustness**: Handles complex scenes, multiple objects, and GPU instability (e.g. spconv/A6000 crash fixes).
*   **Standards Compliant**: Outputs assets with GB/T 36369 metadata.
*   **Visual Reporting**: Automatically generates HTML delivery reports.
*   **Modular Architecture**: Steps are decoupled into independent scripts in `src/steps/`.

## 🚀 Quick Start

### 1. Prerequisites
*   **OS**: Linux (Ubuntu 22.04+ recommended)
*   **GPU**: NVIDIA RTX A6000 or equivalent (24GB+ VRAM required)
*   **Conda**: Installed and initialized.

### 2. Usage

**Run the Full Pipeline**:

```bash
# This script manages all sub-processes and environments automatically
python pipeline_runner.py --input /path/to/your/image.png
```

**Options**:
*   `--output_root`: Custom output directory (default: `outputs/pipeline_demo`).
*   `--skip_scene`: Skip the time-consuming ml-sharp scene generation step.
*   `--asset_gen_backend`: Choose prop 3D generation backend: `trellis` (default) or `sam3d_objects`.

### 3. Output Structure

Outputs are organized by Session ID in `outputs/pipeline_demo/<image_name>/`:

*   **`report.html`**: **Start here!** A visual summary of all generated assets.
*   `scene_visual/`: 3DGS Background (.ply).
*   `dust3r/`: Geometric Point Cloud (.ply).
*   `props/`: Extracted 2D crops & Relit check images.
*   `props_3d/`: Final 3D Assets (.ply) and Metadata (.json).

## 🏗️ Architecture

The project follows a **Micro-Step Orchestration** pattern:

*   **`pipeline_runner.py`**: The conductor. It reads the `harvest_manifest.json` and dispatches jobs.
*   **`src/steps/`**: Atomic capabilities.
    *   `scene_gen/`: ml-sharp Logic.
    *   `geometry/`: DUSt3R Logic.
    *   `assets/`: TRELLIS & Harvesting Logic.
    *   `lighting/`: Probe Extraction.
    *   `export/`: GB/T Wrapper.

## 🔭 Strategic Vision

We believe digital assets must evolve from static files to intelligent agents. See our **Evolution Model**:
👉 [**docs/vision_asset_evolution.md**](docs/vision_asset_evolution.md)

*   **Stage 1 (Current)**: Static Assets (Renderable).
*   **Stage 2 (Next)**: Dynamic Assets (Driveable/Rigged).
*   **Stage 3 (Future)**: Interactive Assets (Autonomous Agents).

## 🛠️ Maintenance & Troubleshooting

*   **Environment Setup**: See `scripts/setup_*.sh` for creating necessary conda environments.
*   **TRELLIS Crash**: If `SLAT Sampler` crashes, ensure you are using `spconv-cu118` (see `scripts/download_trellis.py` for hints).
*   **Input Handling**: If automatic harvesting fails to pick up objects, check `src/steps/assets/harvest_hero_assets.py` to adjust ROI thresholds.

---
**Status**: [Phase 7 Complete] Ready for Pilot Production.
**Author**: Zhang Xin
**Date**: Jan 2026
