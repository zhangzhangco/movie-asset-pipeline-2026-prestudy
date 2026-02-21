
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

def run_geometry(input_path, output_dir, tile_size=1024, overlap=256, device='cuda'):
    # 1. Load Weights
    weights_path = os.path.join(current_dir, 'modules/dust3r/checkpoints/DUSt3R_ViTLarge_BaseDecoder_512_dpt.pth')
    print(f"🚀 Loading weights: {weights_path}")
    model = AsymmetricCroCo3DStereo.from_pretrained(weights_path).to(device)

    # 2. Input Handling: File vs Directory
    image_paths = []
    is_multi_view = False
    
    if os.path.isdir(input_path):
        print(f"📂 Directory detected: {input_path}. Switching to Multi-View Mode.")
        is_multi_view = True
        for f in sorted(os.listdir(input_path)):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                image_paths.append(os.path.join(input_path, f))
        if not image_paths:
            print(f"❌ ERROR: No images found in {input_path}")
            sys.exit(1)
        print(f"✅ Found {len(image_paths)} images for global alignment.")
    else:
        # Existing Tiling Logic for Single Image
        print(f"🖼️ Single image detected. Tiling for high-res reconstruction...")
        img = Image.open(input_path).convert('RGB')
        W, H = img.size
        
        temp_tiles_dir = os.path.join(output_dir, "temp_tiles")
        os.makedirs(temp_tiles_dir, exist_ok=True)
        
        stride = tile_size - overlap
        for x in range(0, W - tile_size + 1, stride):
            box = (x, 0, x + tile_size, min(H, tile_size))
            tile = img.crop(box)
            tile_path = os.path.join(temp_tiles_dir, f"tile_{x}.png")
            tile.save(tile_path)
            image_paths.append(tile_path)
        
        if W % stride != 0 or not image_paths:
            box = (max(0, W - tile_size), 0, W, min(H, tile_size))
            tile = img.crop(box)
            tile_path = os.path.join(temp_tiles_dir, f"tile_end.png")
            tile.save(tile_path)
            image_paths.append(tile_path)

    # 3. Multi-View Inference
    imgs = load_images(image_paths, size=tile_size)
    # 强制使用 complete 以确保所有视图都参与配对
    scene_graph = 'complete' 
    pairs = make_pairs(imgs, scene_graph=scene_graph, symmetrize=True)
    
    print(f"🧠 Running DUSt3R Inference on {len(image_paths)} views ({len(pairs)} pairs)...")
    output = inference(pairs, model, device, batch_size=1)

    # 4. Global Optimization (核心修复：鲁棒处理多层嵌套输出)
    print("🧩 Global Alignment & Refinement...")
    from dust3r.utils.device import collate_with_cat
    
    def collect_dicts(item):
        """递归搜寻所有包含 DUSt3R 标志性预测的字典"""
        results = []
        if isinstance(item, dict):
            if 'view1' in item and 'pred1' in item:
                results.append(item)
            else:
                for v in item.values():
                    results.extend(collect_dicts(v))
        elif isinstance(item, (list, tuple)):
            for x in item:
                results.extend(collect_dicts(x))
        return results

    all_results = collect_dicts(output)
    if not all_results:
        raise ValueError(f"CRITICAL: No valid inference results found in DUSt3R output! Type: {type(output)}")

    print(f"✅ Collected {len(all_results)} valid inference objects.")
    final_input = collate_with_cat(all_results)
    
    # Debug information for batch size
    if 'view1' in final_input:
        print(f"📊 Inference data batch size: {final_input['view1'].shape[0]} (Should match expected pairs)")

    scene = global_aligner(final_input, device=device, mode=GlobalAlignerMode.PointCloudOptimizer)
    
    # 进行 100 次迭代优化以精细化场景结构
    print("🎯 Optimizing scene graph (100 iterations)...")
    loss = scene.compute_global_alignment(init='mst', niter=100, schedule='linear', lr=0.01)
    
    # 5. Export
    os.makedirs(output_dir, exist_ok=True)
    outfile = get_3D_model_from_scene(output_dir, False, scene, min_conf_thr=1.5 if is_multi_view else 1.0, as_pointcloud=True, clean_depth=True)
    
    print(f"✨ 3D Result saved to {outfile}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--tilesize', type=int, default=1024)
    args = parser.parse_args()
    
    run_geometry(args.input, args.output, tile_size=args.tilesize)
