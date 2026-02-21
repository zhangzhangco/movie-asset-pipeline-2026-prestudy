#!/usr/bin/env python3
"""Run Meta SAM 3D Objects inference on a single image.

This step is designed to mirror the existing TRELLIS step so it can be plugged into
pipeline_runner.py.

Inputs
- --input: image path (ideally an object crop; if RGBA, alpha is used as mask)
- --output: output directory

Outputs
- <stem>.ply (gaussian splat)

Notes
- Requires the external repo at: modules/sam-3d-objects
- Requires checkpoints downloaded under: modules/sam-3d-objects/checkpoints/<tag>/pipeline.yaml
  (tag default: hf)

Ref:
- https://github.com/facebookresearch/sam-3d-objects
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def _load_rgba_and_mask(image_path: str):
    """Return (rgb_uint8, mask_bool) where mask comes from alpha if present.

    If the input has no alpha channel, default to full-foreground mask.
    """

    img = Image.open(image_path)
    # Keep original mode; convert for numpy handling.
    if img.mode not in {"RGB", "RGBA"}:
        img = img.convert("RGBA")

    arr = np.array(img)

    if arr.ndim != 3 or arr.shape[2] not in {3, 4}:
        raise ValueError(f"Unsupported image shape: {arr.shape} for {image_path}")

    if arr.shape[2] == 4:
        rgb = arr[:, :, :3]
        alpha = arr[:, :, 3]
        mask = alpha > 0
    else:
        rgb = arr
        mask = np.ones((arr.shape[0], arr.shape[1]), dtype=bool)

    return rgb, mask


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="Input image path")
    parser.add_argument(
        "--output",
        "-o",
        default="outputs/sam3d_objects",
        help="Output directory",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--tag",
        type=str,
        default="hf",
        help="Checkpoint tag folder under modules/sam-3d-objects/checkpoints (default: hf)",
    )
    parser.add_argument(
        "--compile",
        action="store_true",
        help="Enable torch.compile in SAM3D pipeline (can be slower to start)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]  # .../preStudy
    sam3d_root = project_root / "modules" / "sam-3d-objects"
    notebook_dir = sam3d_root / "notebook"

    if not sam3d_root.exists():
        raise SystemExit(
            f"SAM3D repo not found at {sam3d_root}. Clone it to modules/sam-3d-objects first."
        )

    # Import their inference helper (they recommend sys.path.append('notebook'))
    sys.path.insert(0, str(notebook_dir))

    # [CRITICAL] 必需的环境变量设置（规避 C++ 扩展编译崩溃与网络验证阻断）
    os.environ["LIDRA_SKIP_INIT"] = "true"
    os.environ["CUDA_HOME"] = os.environ.get("CONDA_PREFIX", "/usr/local/cuda")
    
    # 清除各种代理环境变量防止出现连接问题
    for proxy_var in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]:
        os.environ.pop(proxy_var, None)

    try:
        from inference import Inference  # type: ignore
    except Exception as e:
        raise SystemExit(
            "Failed to import SAM3D Objects inference. "
            "Make sure you are running inside the 'sam3d-objects' conda env and dependencies are installed.\n"
            f"Import error: {e}"
        )

    config_path = sam3d_root / "checkpoints" / args.tag / "pipeline.yaml"
    if not config_path.exists():
        raise SystemExit(
            f"Checkpoint config not found: {config_path}\n"
            "You likely need to download checkpoints first (HuggingFace gated):\n"
            "  cd modules/sam-3d-objects\n"
            "  pip install 'huggingface-hub[cli]<1.0'\n"
            "  hf auth login\n"
            "  TAG=hf\n"
            "  hf download --repo-type model --local-dir checkpoints/${TAG}-download --max-workers 1 facebook/sam-3d-objects\n"
            "  mv checkpoints/${TAG}-download/checkpoints checkpoints/${TAG}\n"
        )

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    input_path = Path(args.input)
    rgb, mask = _load_rgba_and_mask(str(input_path))

    print(f"Loading SAM3D Objects pipeline from: {config_path}")
    inference = Inference(str(config_path), compile=bool(args.compile))

    print(f"Running SAM3D Objects on: {input_path}")
    output = inference(rgb, mask, seed=args.seed)

    # Export gaussian splat
    ply_path = out_dir / "splat.ply"
    if "gs" not in output:
        raise RuntimeError(f"Unexpected output keys: {list(output.keys())}")

    print(f"Saving Gaussian Splat to {ply_path}")
    output["gs"].save_ply(str(ply_path))

    preview_path = out_dir / "preview.png"
    Image.open(input_path).convert("RGB").save(preview_path)

    print("Done!")


if __name__ == "__main__":
    main()
