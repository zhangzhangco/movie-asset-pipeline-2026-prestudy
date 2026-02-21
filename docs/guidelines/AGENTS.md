# AGENTS.md - Coding Guidelines for Movie Asset 3DGS Pipeline

This document provides essential information for AI coding agents working on the Movie Assetization Pipeline project.

## Project Overview

**Type**: Python 3D Graphics/Computer Vision Pipeline  
**Purpose**: Hybrid 3D generative pipeline for converting 2D movie stills into 3D assets  
**Key Technologies**: Python 3.10+, Nerfstudio, PyTorch/CUDA, 3D Gaussian Splatting (3DGS), DUSt3R, TRELLIS, ml-sharp, OpenEXR  
**Standards**: GB/T 36369 compliant metadata for cinema digital assets

## Build, Test & Run Commands

### Installation
```bash
# Install the nerfstudio plugin package
pip install -e .

# Setup individual conda environments (see scripts/setup_*.sh)
# - sharp: ml-sharp scene generation
# - dust3r: DUSt3R geometry reconstruction  
# - trellis: TRELLIS 3D asset generation
# - sam3d_objects: SAM 3D Objects (optional backend)
```

### Running the Pipeline
```bash
# Full pipeline execution
python pipeline_runner.py --input /path/to/image.png

# With options
python pipeline_runner.py --input /path/to/image.png \
    --output_root outputs/custom \
    --skip_scene \
    --asset_gen_backend trellis

# Multi-view mode (pass directory instead of single image)
python pipeline_runner.py --input /path/to/image_sequence/
```

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_cinema_utils.py

# Run with verbose output
pytest tests/ -v -s

# Run single test function
pytest tests/test_cinema_utils.py::test_load_exr_image_real_file
```

### Individual Pipeline Steps
```bash
# Scene generation (ml-sharp)
python src/steps/scene_gen/run_sharp.py --input-path <image> --output-path <dir>

# Geometry reconstruction (DUSt3R)
python src/steps/geometry/run_dust3r_tiled.py --input <image> --output <dir>

# Lighting estimation
python src/steps/lighting/estimate_lighting.py --input <ply> --output <json>

# Asset harvesting
python src/steps/assets/harvest_hero_assets.py --input <image> --output_dir <dir> --lighting_probe <json>

# 3D asset generation (TRELLIS)
python src/steps/assets/run_trellis_local.py --input <image> --output <dir>

# GB/T packaging
python src/steps/export/package_asset_gbt.py --input <ply> --id <asset_id>

# Report generation
python src/steps/report/generate_report.py --output_root <dir> --input_image <image>
```

## Code Style Guidelines

### General Python Style

- **Python Version**: 3.10+ required
- **Indentation**: 4 spaces (no tabs)
- **Line Length**: Aim for 100-120 characters max
- **Encoding**: UTF-8 with `ensure_ascii=False` for JSON output (supports Chinese metadata)

### Imports

```python
# Standard library imports first
import os
import sys
import json
import argparse
from pathlib import Path

# Third-party imports
import numpy as np
import torch
import cv2
from plyfile import PlyData

# Local imports
from movie_asset_3dgs.data.cinema_utils import load_exr_image
```

**Import Order**: Standard library → Third-party → Local modules  
**Style**: Absolute imports preferred; use `from X import Y` for commonly used functions

### Naming Conventions

- **Functions**: `snake_case` (e.g., `harvest_prop_grabcut`, `estimate_lighting_from_gs`)
- **Variables**: `snake_case` (e.g., `input_path`, `lighting_json`, `asset_id`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `CONDA_ROOT`, `PROJECT_ROOT`, `ENVS`)
- **Classes**: `PascalCase` (e.g., `CinemaDataParser`, `DepthEstimator`)
- **Private**: Prefix with `_` (e.g., `_internal_helper`)

### Type Hints

Use type hints for function signatures, especially in library code:

```python
def load_exr_image(path: Path) -> torch.Tensor:
    """Loads an EXR image into a PyTorch tensor."""
    ...

def sh2rgb(sh_coeffs: np.ndarray) -> np.ndarray:
    """Convert spherical harmonics to RGB."""
    ...
```

### Docstrings

Use Google-style docstrings for functions:

```python
def harvest_prop_grabcut(image_path, output_dir, rect_ratio=0.6):
    """
    Simulate automated harvesting using GrabCut.
    In production, this would be replaced by Segment Anything Model (SAM2).
    
    Args:
        image_path: Path to input image
        output_dir: Directory for output assets
        rect_ratio: ROI size ratio (default: 0.6)
        
    Returns:
        List of tuples (output_path, asset_id) for saved assets
    """
```

### Error Handling

- Use specific exceptions: `FileNotFoundError`, `ValueError`, `RuntimeError`
- Provide informative error messages with context
- Use try-except for external operations (file I/O, subprocess calls)

```python
if not os.path.exists(input_path):
    raise FileNotFoundError(f"Input {input_path} not found.")

try:
    subprocess.check_call(full_cmd, env=env)
except subprocess.CalledProcessError as e:
    print(f"❌ Step '{name}' failed with exit code {e.returncode}")
    return False
```

### File Paths

- Use `os.path.join()` for path construction (cross-platform)
- Use `os.path.abspath()` for absolute paths
- Use `Path` from `pathlib` for modern path operations in new code
- Always check file existence before operations

```python
output_dir = os.path.join(args.output_root, session_id)
os.makedirs(output_dir, exist_ok=True)

# Or with pathlib
from pathlib import Path
exr_path = Path(__file__).resolve().parent.parent / "assets" / "sample.exr"
if not exr_path.exists():
    raise FileNotFoundError(f"File not found: {exr_path}")
```

### JSON Handling

- Use `indent=4` for human-readable output
- Use `ensure_ascii=False` for Chinese/Unicode support
- Include metadata comments in JSON structures

```python
metadata = {
    "system_metadata": {
        "doi_name": gbt_id,
        "referent_type": "DigitalAsset"
    }
}

with open(output_json, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, indent=4, ensure_ascii=False)
```

### Logging & Output

- Use emoji prefixes for visual clarity: 🚀 (start), ✅ (success), ❌ (error), ⚠️ (warning), 🔗 (link)
- Print progress messages for long-running operations
- Include timing information for performance tracking

```python
print(f"🚀 PIPELINE STEP: {name}")
print(f"✅ Step '{name}' completed in {elapsed:.2f}s")
print(f"❌ Step '{name}' failed with exit code {e.returncode}")
print(f"⚠️ No scene PLY found for lighting, using default.")
```

## Architecture Patterns

### Modular Pipeline Steps

Each pipeline step is an independent script in `src/steps/`:
- **Input**: Command-line arguments (argparse)
- **Output**: Files + JSON manifests
- **Communication**: Via filesystem (JSON manifests, not in-memory)

### Manifest-Driven Workflow

The pipeline uses JSON manifests to pass data between steps:

```python
# harvest_hero_assets.py outputs harvest_manifest.json
manifest_list.append({
    "id": asset_id,
    "path": final_prop_path,
    "raw_path": prop_path,
    "articulation": articulation_data
})

# pipeline_runner.py reads and iterates
with open(manifest_path, 'r') as f:
    manifest = json.load(f)
for item in manifest:
    asset_id = item['id']
    relit_file = item['path']
    # Process each asset...
```

### Environment Management

Multiple conda environments for different models:
- Use `ENVS` dict in `pipeline_runner.py` to map environment names to Python executables
- Pass `extra_env` dict for PYTHONPATH and other environment variables
- Use `subprocess.check_call()` with custom `env` for isolation

## Common Pitfalls & Best Practices

1. **GPU Memory**: Always assume limited VRAM; implement tiling/chunking for large images
2. **File Existence**: Check before reading; use `os.path.exists()` or `Path.exists()`
3. **Tensor Clamping**: Clamp EXR/HDR values to [0, 1] for 3DGS stability
4. **Mask Validation**: Filter small contours (< 5% image area) to avoid noise
5. **ID Generation**: Use timestamp + UUID for unique asset IDs: `prop_20260221_a3f2`
6. **Checksum**: Always compute MD5 for asset integrity (GB/T requirement)
7. **Multi-view Support**: Check if input is directory vs single file; handle both cases

## Testing Guidelines

- Place test files in `tests/` directory
- Use `pytest` fixtures for setup/teardown
- Use `pytest.skip()` for tests requiring external assets
- Test with real data samples in `assets/` directory
- Use `-s` flag to see print statements during tests

```python
def test_load_exr_image_real_file(capsys):
    exr_path = Path(__file__).resolve().parent.parent / "assets" / "sample_test.exr"
    if not exr_path.exists():
        pytest.skip(f"Sample EXR not found at {exr_path}")
    
    tensor = load_exr_image(exr_path)
    assert tensor.dtype == torch.float32
    assert torch.isfinite(tensor).all()
```

## GB/T 36369 Standards Compliance

When creating or modifying asset metadata:

- **DOI Format**: `10.5000.1/CN.FILM.ASSET.YYYY.NNNN`
- **Required Fields**: `doi_name`, `referent_type`, `referent_identifier` (LocalID + MD5)
- **Technical Metadata**: Format (PLY), standard (3DGS-1.0), file_size, created_at (ISO 8601)
- **Content Metadata**: Tags, description, provenance, structure_data (articulation info)

See `src/steps/export/package_asset_gbt.py` for reference implementation.

## Key Files to Understand

- `pipeline_runner.py` - Main orchestrator, entry point
- `src/steps/assets/harvest_hero_assets.py` - Asset extraction with GrabCut + face detection
- `src/steps/export/package_asset_gbt.py` - GB/T metadata packaging
- `movie_asset_3dgs/data/cinema_utils.py` - EXR loading utilities
- `tests/test_cinema_utils.py` - Example test structure

## Additional Resources

- Project Vision: `docs/vision_asset_evolution.md`
- Technical Architecture: `technical_architecture.md`
- Setup Scripts: `scripts/setup_*.sh`
- Documentation: `docs/` directory
