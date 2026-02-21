
import os
import argparse
import sys

# --- GLOBAL STABILITY FIX ---
# Enforce 'naive' attention backend to prevent SIGFPE (Floating Point Exception)
# on certain GPUs/Drivers when processing sparse voxels.
# This must be set BEFORE importing trellis2.
if "ATTN_BACKEND" not in os.environ:
    print("🛡️  Safety: Enforcing ATTN_BACKEND='naive' for stability.")
    os.environ["ATTN_BACKEND"] = "naive"
# ----------------------------

import torch
import imageio
from PIL import Image
from trellis2.pipelines import Trellis2ImageTo3DPipeline
from trellis2.utils import render_utils

# Environment Guard
try:
    import flex_gemm
except ImportError:
    print("❌ ERROR: Please run this script in the 'trellis2' conda environment.")
    print("   Run: conda activate trellis2")
    sys.exit(1)

def run_trellis_local(image_path, output_dir, seed=1):
    os.makedirs(output_dir, exist_ok=True)
    
    model_path = "models/TRELLIS.2-4B"
    if os.path.exists(model_path):
        print(f"Loading pipeline from local path: {model_path}...")
        pipeline = Trellis2ImageTo3DPipeline.from_pretrained(model_path)
    else:
        print(f"Loading pipeline 'microsoft/TRELLIS.2-4B' from HF...")
        pipeline = Trellis2ImageTo3DPipeline.from_pretrained("microsoft/TRELLIS.2-4B")
    pipeline.cuda()
    
    print(f"Processing {image_path}...")
    image = Image.open(image_path)
    
    # Run pipeline
    print("DEBUG: Starting pipeline.run()...")
    outputs = pipeline.run(
        image,
        seed=seed,
        # sparse_structure_sampler_params={"steps": 12, "cfg_strength": 7.5},
        # slat_sampler_params={"steps": 12, "cfg_strength": 3},
    )
    print("DEBUG: pipeline.run() completed. Extracting outputs...")
    
    stem = os.path.splitext(os.path.basename(image_path))[0]
    
    # 1. Save 3D Gaussian (.ply)
    ply_path = os.path.join(output_dir, f"{stem}.ply")
    print(f"Saving Gaussian Splat to {ply_path}")
    outputs['gaussian'][0].save_ply(ply_path)
    
    # 2. Save GLB (.glb) - Disabled due to utils3d incompatibility
    # glb_path = os.path.join(output_dir, f"{stem}.glb")
    # print(f"Saving GLB to {glb_path}")
    # glb = postprocessing_utils.to_glb(
    #     outputs['gaussian'][0],
    #     outputs['mesh'][0],
    #     simplify=0.95,
    #     texture_size=1024,
    # )
    # glb.export(glb_path)
    
    # 3. Render Video (Optional but good for verification) - Disabled due to utils3d incompatibility
    # video_path = os.path.join(output_dir, f"{stem}_gs.mp4")
    # print(f"Rendering video to {video_path}")
    # video = render_utils.render_video(outputs['gaussian'][0])['color']
    # imageio.mimsave(video_path, video, fps=30)
    
    print("Done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", type=str, required=True, help="Input image path")
    parser.add_argument("--output", "-o", type=str, default="outputs/trellis_local", help="Output directory")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    
    run_trellis_local(args.input, args.output, args.seed)
