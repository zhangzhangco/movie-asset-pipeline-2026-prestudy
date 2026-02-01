
import os
import sys
import torch
import argparse
import copy
import numpy as np
from PIL import Image

# Add dust3r to path
current_dir = os.getcwd()
dust3r_path = os.path.join(current_dir, 'modules/dust3r')
sys.path.append(dust3r_path)

try:
    from dust3r.model import AsymmetricCroCo3DStereo
    from dust3r.inference import inference
    from dust3r.image_pairs import make_pairs
    from dust3r.utils.image import load_images
    from dust3r.cloud_opt import global_aligner, GlobalAlignerMode
    from dust3r.demo import get_3D_model_from_scene
except ImportError:
    print("❌ ERROR: Could not import dust3r.")
    sys.exit(1)

def run_dust3r_tiled(input_path, output_dir, tile_size=1024, overlap=256, device='cuda'):
    # 1. Load Weights
    weights_path = os.path.join(current_dir, 'modules/dust3r/checkpoints/DUSt3R_ViTLarge_BaseDecoder_512_dpt.pth')
    print(f"🚀 Loading weights: {weights_path}")
    model = AsymmetricCroCo3DStereo.from_pretrained(weights_path).to(device)

    # 2. Tiling Logic
    print(f"🖼️ Tiling image for high-res reconstruction...")
    img = Image.open(input_path).convert('RGB')
    W, H = img.size
    
    temp_tiles_dir = os.path.join(output_dir, "temp_tiles")
    os.makedirs(temp_tiles_dir, exist_ok=True)
    
    tile_paths = []
    # 沿水平方向切分（针对宽屏电影场景）
    stride = tile_size - overlap
    for x in range(0, W - tile_size + 1, stride):
        box = (x, 0, x + tile_size, min(H, tile_size))
        tile = img.crop(box)
        tile_path = os.path.join(temp_tiles_dir, f"tile_{x}.png")
        tile.save(tile_path)
        tile_paths.append(tile_path)
    
    # 补上最后的一块
    if W % stride != 0:
        box = (W - tile_size, 0, W, min(H, tile_size))
        tile = img.crop(box)
        tile_path = os.path.join(temp_tiles_dir, f"tile_end.png")
        tile.save(tile_path)
        tile_paths.append(tile_path)

    print(f"✅ Generated {len(tile_paths)} tiles. Running multi-view inference...")

    # 3. Multi-View Inference
    imgs = load_images(tile_paths, size=tile_size)
    # 使用 complete 图连接所有邻近分片
    pairs = make_pairs(imgs, scene_graph='complete', symmetrize=True)
    
    print(f"🧠 Inference (this may take a while)...")
    output = inference(pairs, model, device, batch_size=1)

    # 4. Global Optimization (关键步骤)
    print("🧩 Global Alignment & Refinement...")
    # 模式切换为 PointCloudOptimizer，这会迭代优化所有分片间的相对位置和深度
    scene = global_aligner(output, device=device, mode=GlobalAlignerMode.PointCloudOptimizer)
    
    # 进行 100 次迭代优化以精细化场景结构
    loss = scene.compute_global_alignment(init='mst', niter=100, schedule='linear', lr=0.01)
    
    # 5. Export
    os.makedirs(output_dir, exist_ok=True)
    # min_conf_thr=1.0 配合 clean_depth=True 获得最干净的大规模场景
    outfile = get_3D_model_from_scene(output_dir, False, scene, min_conf_thr=1.0, as_pointcloud=True, clean_depth=True)
    
    print(f"✨ ULTRA-HIGH-RES Scene saved to {outfile}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--tilesize', type=int, default=1024)
    args = parser.parse_args()
    
    run_dust3r_tiled(args.input, args.output, tile_size=args.tilesize)
