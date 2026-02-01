
from pathlib import Path
import torch
import pytest
from movie_asset_3dgs.data.cinema_utils import load_exr_image

def test_load_exr_image_real_file(capsys):
    # Locate the extracted sample EXR relative to this test file
    # tests/../assets/sample_test.exr
    exr_path = Path(__file__).resolve().parent.parent / "assets" / "sample_test.exr"

    if not exr_path.exists():
        pytest.skip(f"Sample EXR not found at {exr_path}")

    tensor = load_exr_image(exr_path)

    # Basic Checks
    assert tensor.dtype == torch.float32
    assert tensor.ndim == 3
    assert tensor.shape[2] in (3, 4), f"Unexpected channels: {tensor.shape[2]}"
    
    # Check for NaNs/Infs
    assert torch.isfinite(tensor).all(), "EXR tensor contains NaNs or Infs"
    
    # Check Range (Should be clamped to [0, 1] by our loader)
    assert tensor.min().item() >= 0.0
    assert tensor.max().item() <= 1.0

    # Print stats to stdout (use -s to see this)
    print(f"\nEXR Loaded: {exr_path.name}")
    print(f"Shape: {tensor.shape}")
    print(f"Stats - Min: {tensor.min().item():.4f}, Max: {tensor.max().item():.4f}, Mean: {tensor.mean().item():.4f}")
