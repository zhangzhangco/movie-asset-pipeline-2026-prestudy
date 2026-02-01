
import numpy as np
import torch
import OpenEXR
import Imath
from pathlib import Path

def load_exr_image(path: Path) -> torch.Tensor:
    """
    Loads an EXR image into a PyTorch tensor (Float32).
    
    Args:
        path: Path to the .exr file.
        
    Returns:
        torch.Tensor: Shape (H, W, C) where C is 3 (RGB) or 4 (RGBA).
                      Values are linear, clamped to [0, 1].
    """
    if not path.exists():
        raise FileNotFoundError(f"EXR file not found: {path}")

    try:
        exr = OpenEXR.InputFile(str(path))
    except Exception as e:
        raise RuntimeError(f"Failed to open EXR file {path}: {e}")

    header = exr.header()
    # Check available channels
    all_channels = header['channels'].keys()
    
    # Simple logic: prefer RGBA, then RGB.
    # Note: EXR channels can be named variously (e.g., 'R', 'G', 'B', 'A' or 'Layer.R' etc.)
    # We implement a basic finder for 'R', 'G', 'B', 'A'.
    has_alpha = 'A' in all_channels
    channel_names = ['R', 'G', 'B', 'A'] if has_alpha else ['R', 'G', 'B']
    
    # Ensure requested channels exist
    for c in channel_names:
        if c not in all_channels:
             # Fallback/Error handling could be more robust here for complex multi-layer EXRs
             raise ValueError(f"Channel '{c}' missing in EXR. Available: {list(all_channels)}")

    data_window = header["dataWindow"]
    width = data_window.max.x - data_window.min.x + 1
    height = data_window.max.y - data_window.min.y + 1

    # Request float32 for consistent output; HALF channels are upcast by OpenEXR.
    pixel_type = Imath.PixelType(Imath.PixelType.FLOAT)
    channel_arrays = []
    
    for name in channel_names:
        raw = exr.channel(name, pixel_type)
        # Using frombuffer for fast zero-copy loading if possible
        channel = np.frombuffer(raw, dtype=np.float32).reshape(height, width)
        channel_arrays.append(channel)

    # Stack to (H, W, C)
    image = np.stack(channel_arrays, axis=-1)
    
    # Convert to Tensor
    tensor = torch.from_numpy(image).to(dtype=torch.float32)
    
    # Clamp to [0, 1] as 3DGS usually expects normalized colors. 
    # NOTE: High Dynamic Range values > 1.0 are clipped here. 
    # If we want true HDR training, we should NOT clamp, but 3DGS Spherical Harmonics 
    # and rasterizer usually output roughly [0,1].
    # For now, we clip to ensure stability.
    return torch.clamp(tensor, 0.0, 1.0)


def gamma_correct(linear_tensor: torch.Tensor, gamma: float = 2.2) -> torch.Tensor:
    """Apply simple gamma correction for visualization."""
    if gamma <= 0:
        raise ValueError("Gamma must be positive.")
    # Pow is safe since we clamped to >= 0
    return torch.clamp(linear_tensor, 0.0, 1.0).pow(1.0 / gamma)
