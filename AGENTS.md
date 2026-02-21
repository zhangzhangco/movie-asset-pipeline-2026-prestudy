# AGENTS.md - AI Coding Agent Guidelines

Guidelines for AI agents working on this Python 3D pipeline project. Based on actual codebase analysis.

## Project Structure (from code)

```
preStudy/
├── pipeline_runner.py          # Main entry point
├── setup.py                    # Package setup (minimal)
├── setup.cfg                   # Package metadata
├── src/
│   ├── core/
│   │   └── runner_utils.py    # StepRunner, ManifestManager
│   └── steps/                 # Pipeline stages
│       ├── scene_gen/         # ml-sharp
│       ├── geometry/          # DUSt3R
│       ├── assets/            # TRELLIS.2, SAM3D
│       ├── lighting/          # Light estimation
│       ├── export/            # GB/T packaging
│       └── report/            # HTML reports
├── movie_asset_3dgs/          # Core library
│   └── data/
│       └── cinema_utils.py    # EXR loading
└── tests/
    └── test_cinema_utils.py   # Test examples
```

## Commands (from actual code)

### Installation
```bash
pip install -e .
```

### Run Pipeline
```bash
# Basic (from pipeline_runner.py:37-57)
python pipeline_runner.py --input /path/to/image.png

# Options
python pipeline_runner.py --input image.png \
    --output_root outputs/custom \
    --skip_scene \
    --skip_geometry \
    --asset_gen_backend trellis2 \
    --roi_hint 100,100,500,500 \
    --disable_skin_rejection
```

### Testing
```bash
# Run all tests
pytest tests/

# Single test (from test_cinema_utils.py:7)
pytest tests/test_cinema_utils.py::test_load_exr_image_real_file -v -s
```

### Individual Steps
```bash
# From pipeline_runner.py SCRIPTS dict (line 24-35)
python src/steps/scene_gen/run_sharp.py --input-path <img> --output-path <dir>
python src/steps/geometry/run_dust3r_tiled.py --input <img> --output <dir>
python src/steps/lighting/estimate_lighting.py --input <ply> --output <json>
python src/steps/assets/harvest_hero_assets.py --input <img> --output_dir <dir>
python src/steps/assets/run_trellis2_local.py --input <img> --output <dir>
python src/steps/export/package_asset_gbt.py --input <ply> --id <asset_id>
```

## Code Style (from actual files)

### Imports (cinema_utils.py:2-6, package_asset_gbt.py:2-6)
```python
# Standard library
import os
import json
import argparse
from pathlib import Path

# Third-party
import numpy as np
import torch
from plyfile import PlyData

# Local
from movie_asset_3dgs.data.cinema_utils import load_exr_image
```

### Naming (observed patterns)
- Functions: `snake_case` (load_exr_image, estimate_lighting_from_gs, harvest_prop_grabcut)
- Variables: `snake_case` (input_path, ply_path, output_dir)
- Constants: `UPPER_SNAKE_CASE` (CONDA_ROOT, PROJECT_ROOT, ENVS)
- Classes: `PascalCase` (StepRunner, ManifestManager)

### Type Hints (cinema_utils.py:8, 71)
```python
def load_exr_image(path: Path) -> torch.Tensor:
    """Loads an EXR image into a PyTorch tensor."""
    ...

def gamma_correct(linear_tensor: torch.Tensor, gamma: float = 2.2) -> torch.Tensor:
    """Apply simple gamma correction for visualization."""
    ...
```

### Docstrings (harvest_hero_assets.py:12-15, package_asset_gbt.py:9-14)
```python
def harvest_prop_grabcut(image_path, output_dir, rect_ratio=0.6, roi_hint=None):
    """
    Simulate automated harvesting using GrabCut.
    In production, this would be replaced by Segment Anything Model (SAM2).
    """

def generate_gbt_id(asset_type, year=2026, sequence=1):
    """
    Generate GB/T 36369 compliant Cinema Digital Object Identifier.
    Format: prefix/CN.FILM.ASSET.YYYY.SEQUENCE
    """
```

### Error Handling (runner_utils.py:42-47, cinema_utils.py:19-25)
```python
# runner_utils.py
try:
    subprocess.check_call(full_cmd, env=env)
except subprocess.CalledProcessError as e:
    print(f"❌ Step '{name}' failed with exit code {e.returncode}")
    return False

# cinema_utils.py
if not path.exists():
    raise FileNotFoundError(f"EXR file not found: {path}")
```

### File Paths (pipeline_runner.py:59-66, test_cinema_utils.py:10)
```python
# pipeline_runner.py - os.path style
input_path = os.path.abspath(args.input)
output_dir = os.path.join(args.output_root, session_id)
os.makedirs(output_dir, exist_ok=True)

# test_cinema_utils.py - pathlib style
exr_path = Path(__file__).resolve().parent.parent / "assets" / "sample_test.exr"
if not exr_path.exists():
    pytest.skip(f"Sample EXR not found at {exr_path}")
```

### JSON (runner_utils.py:79-80, package_asset_gbt.py:95-96)
```python
with open(output_json, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, indent=4, ensure_ascii=False)
```

### Logging (runner_utils.py:20-21,40, harvest_hero_assets.py:36,46)
```python
print(f"🚀 PIPELINE STEP: {name}")
print(f"✅ Step '{name}' completed in {elapsed:.2f}s")
print(f"❌ Step '{name}' failed with exit code {e.returncode}")
print(f"🎯 使用用户提供的 ROI Hint: {rect}")
print(f"👀 Detected {len(faces)} faces. Calculating Group ROI...")
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

```python
ENVS = {
    "sharp": f"{CONDA_ROOT}/envs/sharp/bin/python",
    "dust3r": f"{CONDA_ROOT}/envs/dust3r/bin/python",
    "trellis2": f"{CONDA_ROOT}/envs/trellis2/bin/python",
    "sam3d_objects": f"{CONDA_ROOT}/envs/sam3d-objects/bin/python",
    "base": sys.executable,
}
```

## Common Pitfalls & Best Practices

1. **GPU Memory**: Always assume limited VRAM; implement tiling/chunking for large images
2. **File Existence**: Check before reading; use `os.path.exists()` or `Path.exists()`
3. **Tensor Clamping**: Clamp EXR/HDR values to [0, 1] for 3DGS stability
4. **Mask Validation**: Filter small contours (< 5% image area) to avoid noise
5. **ID Generation**: Use timestamp + UUID for unique asset IDs: `prop_20260221_a3f2`
6. **Checksum**: Always compute MD5 for asset integrity (GB/T requirement)
7. **Multi-view Support**: Check if input is directory vs single file; handle both cases
8. **ROI Handling**: Support both automatic face detection and manual ROI hints
9. **Chinese Support**: Always use `encoding='utf-8'` and `ensure_ascii=False` for JSON

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
