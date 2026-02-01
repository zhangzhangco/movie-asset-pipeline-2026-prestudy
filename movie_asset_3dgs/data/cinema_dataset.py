from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar

import torch
import torch.nn.functional as F

from nerfstudio.data.datasets.base_dataset import InputDataset

from .cinema_utils import load_exr_image


def _is_exr(path: Path) -> bool:
    return path.suffix.lower() == ".exr"


def _rescale_image(image: torch.Tensor, scale_factor: float) -> torch.Tensor:
    """Rescale (H, W, C) tensor by scale_factor using bilinear filtering."""
    if scale_factor == 1.0:
        return image
    if scale_factor <= 0:
        raise ValueError(f"scale_factor must be > 0, got {scale_factor}")
    chw = image.permute(2, 0, 1).unsqueeze(0)  # 1,C,H,W
    chw = F.interpolate(chw, scale_factor=scale_factor, mode="bilinear", align_corners=False)
    return chw.squeeze(0).permute(1, 2, 0)


class CinemaDataset(InputDataset):
    """InputDataset variant that loads `.exr` images with OpenEXR (linear float)."""

    def get_image_float32(self, image_idx: int) -> torch.Tensor:
        image_filename = self._dataparser_outputs.image_filenames[image_idx]
        if not _is_exr(image_filename):
            return super().get_image_float32(image_idx)
        image = load_exr_image(image_filename)
        return _rescale_image(image, self.scale_factor)

    def get_image_uint8(self, image_idx: int) -> torch.Tensor:
        image_filename = self._dataparser_outputs.image_filenames[image_idx]
        if not _is_exr(image_filename):
            return super().get_image_uint8(image_idx)
        image = self.get_image_float32(image_idx)
        return (image.clamp(0.0, 1.0) * 255.0 + 0.5).to(torch.uint8)

    def get_numpy_image(self, image_idx: int):
        image_filename = self._dataparser_outputs.image_filenames[image_idx]
        if not _is_exr(image_filename):
            return super().get_numpy_image(image_idx)
        return self.get_image_uint8(image_idx).cpu().numpy()


_T = TypeVar("_T")


def install_exr_loader_patch() -> None:
    """Patch Nerfstudio's InputDataset to support `.exr` without changing datamanagers.

    Nerfstudio instantiates `InputDataset` (or subclasses) inside its DataManagers.
    Dataparser outputs alone cannot change the image IO path; dataset methods do.

    This patch is intentionally conditional: it only takes effect for `.exr` paths.
    """

    if getattr(InputDataset, "_movie_asset_3dgs_exr_patched", False):
        return

    orig_get_image_float32: Callable[[InputDataset, int], torch.Tensor] = InputDataset.get_image_float32
    orig_get_image_uint8: Callable[[InputDataset, int], torch.Tensor] = InputDataset.get_image_uint8
    orig_get_numpy_image = InputDataset.get_numpy_image

    def patched_get_image_float32(self: InputDataset, image_idx: int) -> torch.Tensor:
        image_filename = self._dataparser_outputs.image_filenames[image_idx]
        if not _is_exr(image_filename):
            return orig_get_image_float32(self, image_idx)
        image = load_exr_image(image_filename)
        return _rescale_image(image, self.scale_factor)

    def patched_get_image_uint8(self: InputDataset, image_idx: int) -> torch.Tensor:
        image_filename = self._dataparser_outputs.image_filenames[image_idx]
        if not _is_exr(image_filename):
            return orig_get_image_uint8(self, image_idx)
        image = patched_get_image_float32(self, image_idx)
        return (image.clamp(0.0, 1.0) * 255.0 + 0.5).to(torch.uint8)

    def patched_get_numpy_image(self: InputDataset, image_idx: int):
        image_filename = self._dataparser_outputs.image_filenames[image_idx]
        if not _is_exr(image_filename):
            return orig_get_numpy_image(self, image_idx)
        return patched_get_image_uint8(self, image_idx).cpu().numpy()

    InputDataset.get_image_float32 = patched_get_image_float32  # type: ignore[method-assign]
    InputDataset.get_image_uint8 = patched_get_image_uint8  # type: ignore[method-assign]
    InputDataset.get_numpy_image = patched_get_numpy_image  # type: ignore[method-assign]
    InputDataset._movie_asset_3dgs_exr_patched = True  # type: ignore[attr-defined]

