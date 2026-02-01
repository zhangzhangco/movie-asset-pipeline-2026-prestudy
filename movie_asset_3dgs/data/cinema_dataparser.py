
from dataclasses import dataclass, field
from typing import Type

import torch
import numpy as np
from pathlib import Path

from nerfstudio.data.dataparsers.nerfstudio_dataparser import Nerfstudio, NerfstudioDataParserConfig
from nerfstudio.data.datasets.base_dataset import InputDataset
from nerfstudio.plugins.registry_dataparser import DataParserSpecification

from movie_asset_3dgs.data.cinema_utils import load_exr_image

# --- Monkey Patching Logic ---
# Need to patch InputDataset to support EXR loading, as default only supports PIL/OpenCV
# This is "magic" but necessary to avoid rewriting the strict InputDataset class.

_original_get_numpy_image = InputDataset.get_numpy_image
_original_get_image_float32 = InputDataset.get_image_float32

def _is_exr(filepath: str) -> bool:
    return filepath.lower().endswith('.exr')

def patched_get_numpy_image(self: InputDataset, image_idx: int):
    """
    Patched method to handle .exr files in the dataset.
    Returns:
        np.ndarray: float32 array in [0, 1], shape (H, W, C).
                   OR default uint8 array if not EXR.
    """
    filepath = self._dataparser_outputs.image_filenames[image_idx]
    if _is_exr(str(filepath)):
        # Load EXR using our custom loader (which returns Tensor)
        # Convert back to numpy for consistency with InputDataset's internal flow
        # NerfStudio expects get_numpy_image to return the raw data
        tensor = load_exr_image(Path(filepath))
        return tensor.cpu().numpy()
    
    return _original_get_numpy_image(self, image_idx)

def patched_get_image_float32(self: InputDataset, image_idx: int) -> torch.Tensor:
    """
    Override to avoid unnecessary uint8->float32 conversions and Gamma correction for EXR.
    """
    filepath = self._dataparser_outputs.image_filenames[image_idx]
    if _is_exr(str(filepath)):
        # For EXR, we already have linear float32 data.
        # Just return it directly as a tensor.
        # NOTE: We skip standard NerfStudio processing (resizing handled by dataparser usually, but loading here).
        # We assume EXR is already pre-processed or we rely on full resolution.
        # If dynamic resizing is needed, we would need to implement it on the tensor.
        
        # Re-load or cache? InputDataset caches via source.
        # Here we just call get_numpy_image which we patched above.
        image = self.get_numpy_image(image_idx)
        return torch.from_numpy(image).float()
    
    return _original_get_image_float32(self, image_idx)


# Apply the patches only once
if not hasattr(InputDataset, "_movie_asset_3dgs_patched"):
    # We carefully patch only what we need.
    # Note: ns uses get_numpy_image primarily. helper methods consume it.
    InputDataset.get_numpy_image = patched_get_numpy_image
    InputDataset.get_image_float32 = patched_get_image_float32
    InputDataset._movie_asset_3dgs_patched = True


# --- Custom DataParser ---

@dataclass
class CinemaDataParserConfig(NerfstudioDataParserConfig):
    """Cinema DataParser config (extends Nerfstudio)"""
    _target: Type = field(default_factory=lambda: CinemaDataParser)
    # You can add custom fields here if needed, e.g. alpha thresholds
    
@dataclass
class CinemaDataParser(Nerfstudio):
    """Cinema DataParser that supports EXR and Linear Workflow"""
    
    config: CinemaDataParserConfig

    def __init__(self, config: CinemaDataParserConfig):
        super().__init__(config)

    def _get_image_filenames(self, image_dir: Path, filenames: list[str]) -> list[Path]:
        """
        Override to allow .exr extensions if they aren't caught by default.
        But NerfstudioDataParser usually scans for images.
        We just need to ensure the parent class doesn't filter out EXR.
        """
        # The parent implementation scans the directory if filenames is empty.
        # If we rely on colmap/transforms.json, the file paths are in the json.
        # So we just pass through.
        return super()._get_image_filenames(image_dir, filenames)


# Register the plugin entry point config
cinema_dataparser = DataParserSpecification(
    config=CinemaDataParserConfig(),
    description="Cinema EXR DataParser Plugin",
)
