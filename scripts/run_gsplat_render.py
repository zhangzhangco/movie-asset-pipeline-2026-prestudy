
import os
import torch
import numpy as np
from plyfile import PlyData
import imageio
from gsplat import rasterization
import math
import argparse
import sys

# Environment Guard
try:
    import gsplat
except ImportError:
    print("❌ ERROR: Please run this script in the 'nvidia_opt' conda environment.")
    print("   Run: conda activate nvidia_opt")
    import sys
    sys.exit(1)

def load_ply(path, device='cuda'):
    print(f"Loading PLY from {path}...")
    plydata = PlyData.read(path)
    
    xyz = np.stack((np.asarray(plydata.elements[0]["x"]),
                    np.asarray(plydata.elements[0]["y"]),
                    np.asarray(plydata.elements[0]["z"])),  axis=1)
    
    opacities = np.asarray(plydata.elements[0]["opacity"])
    
    scale_names = [p.name for p in plydata.elements[0].properties if p.name.startswith("scale_")]
    scale_names = sorted(scale_names, key = lambda x: int(x.split('_')[-1]))
    scales = np.zeros((xyz.shape[0], len(scale_names)))
    for idx, attr_name in enumerate(scale_names):
        scales[:, idx] = np.asarray(plydata.elements[0][attr_name])
        
    rot_names = [p.name for p in plydata.elements[0].properties if p.name.startswith("rot")]
    rot_names = sorted(rot_names, key = lambda x: int(x.split('_')[-1]))
    rots = np.zeros((xyz.shape[0], len(rot_names)))
    for idx, attr_name in enumerate(rot_names):
        rots[:, idx] = np.asarray(plydata.elements[0][attr_name])
        
    # SH / Color
    # 3DGS usually stores f_dc_0, f_dc_1, f_dc_2
    features_dc = np.zeros((xyz.shape[0], 3))
    features_dc[:, 0] = np.asarray(plydata.elements[0]["f_dc_0"])
    features_dc[:, 1] = np.asarray(plydata.elements[0]["f_dc_1"])
    features_dc[:, 2] = np.asarray(plydata.elements[0]["f_dc_2"])
    
    # Extra SH
    extra_f_names = [p.name for p in plydata.elements[0].properties if p.name.startswith("f_rest_")]
    # TRELLIS might only output DC (degree 0) or more.
    if len(extra_f_names) > 0:
        # Load extra... for now ignore or just load DC if we want simple render
        pass
        
    # Convert to Tensor and Activate
    means = torch.tensor(xyz, dtype=torch.float32, device=device)
    # TRELLIS saves inverse_sigmoid(opacity), so we apply sigmoid
    opacities = torch.sigmoid(torch.tensor(opacities, dtype=torch.float32, device=device))
    # TRELLIS saves log(scale), so we apply exp
    scales = torch.exp(torch.tensor(scales, dtype=torch.float32, device=device))
    # Quats are usually normalized, but gsplat expects normalized
    quats = torch.tensor(rots, dtype=torch.float32, device=device)
    quats = torch.nn.functional.normalize(quats, dim=-1)
    
    # Load Normals for Lighting
    has_normals = "nx" in [p.name for p in plydata.elements[0].properties]
    if has_normals:
        normals = np.stack((np.asarray(plydata.elements[0]["nx"]),
                            np.asarray(plydata.elements[0]["ny"]),
                            np.asarray(plydata.elements[0]["nz"])), axis=1)
        normals = torch.tensor(normals, dtype=torch.float32, device=device)
        normals = torch.nn.functional.normalize(normals, dim=-1)
    else:
        normals = None
    
    # SH
    # gsplat rasterization expects 'colors' or 'shs'
    # colors: [N, 3] usually assuming SH_0 conversion or just RGB
    # But usually 'colors' argument expects RGB in 0-1 range.
    # SH to RGB: 0.5 + SH * 0.282...
    # TRELLIS outputs RAW SH.
    shs = torch.tensor(features_dc, dtype=torch.float32, device=device).unsqueeze(1) # [N, 1, 3] for degree 0?
    # Actually gsplat might expect [N, K, 3] where K is (deg+1)^2
    
    return means, quats, scales, opacities, shs, normals

def get_look_at(eye, target, up):
    z_axis = eye - target
    z_axis = z_axis / torch.norm(z_axis)
    
    x_axis = torch.cross(up, z_axis)
    x_axis = x_axis / torch.norm(x_axis)
    
    y_axis = torch.cross(z_axis, x_axis)
    
    # View Matrix (World to Camera)
    # R^T * (P - eye)
    # Construct 4x4
    view_mat = torch.eye(4, device=eye.device)
    view_mat[:3, 0] = x_axis
    view_mat[:3, 1] = y_axis
    view_mat[:3, 2] = z_axis
    view_mat[:3, 3] = eye
    
    # However, gsplat/opengl usually expects:
    # Right, Up, Back
    # This construction is typical LookAt.
    # But we need verify if gsplat expects World-to-Camera or Camera-to-World.
    # rasterization(..., viewmats) doc says "World-to-Camera".
    # So we need inverse of the above (Camera-to-World matrix).
    # Wait, the above IS Camera-to-World (Pose), placing camera at 'eye'.
    # So we need to invert it.
    
    c2w = view_mat
    w2c = torch.inverse(c2w)
    return w2c

def render_scene(ply_path, output_mp4, width=1024, height=1024): # Increased Res
    device = 'cuda'
    # Updated unpack
    means, quats, scales, opacities, shs, normals = load_ply(ply_path, device)
    
    frames = []
    n_frames = 60
    
    # Debug Stats
    print(f"Stats:")
    print(f"  Means: {means.mean(0)}")
    print(f"  Scales (mean): {scales.mean(0)}")
    print(f"  Opacities (mean): {opacities.mean()}")
    
    # SH / Color conversion check
    # RGB = 0.5 + 0.28209 * SH
    rgbs = 0.5 + 0.28209479177387814 * shs.squeeze(1)
    rgbs = torch.clamp(rgbs, 0.0, 1.0)
    print(f"  RGBs (mean): {rgbs.mean(0)}")
    
    # Scale inflation for visibility checking
    # FIX: "Flickering" was caused by just inflating scales (blobs overlapping).
    # Correct approach: Scale the entire world (means AND scales).
    world_scale = 10.0
    means = means * world_scale
    scales = scales * world_scale
    print(f"  Applied World Scale {world_scale}x")

    # Base Color (SH DC)
    # RGB = 0.5 + 0.28209 * SH
    rgbs = 0.5 + 0.28209479177387814 * shs.squeeze(1)
    rgbs = torch.clamp(rgbs, 0.0, 1.0)
    
    # Apply Synthetic Lighting if Normals exist
    if normals is not None:
        print("  Applying Synthetic Lighting (Directional)...")
        # Simple Directional Light from top-right-front
        light_dir = torch.tensor([0.5, 1.0, 0.5], device=device)
        light_dir = torch.nn.functional.normalize(light_dir, dim=0)
        
        # Lambertian
        # N dot L
        diffuse = torch.sum(normals * light_dir, dim=1, keepdim=True)
        diffuse = torch.clamp(diffuse, 0.0, 1.0)
        
        # Ambient
        ambient = 0.4
        intensity = ambient + 0.6 * diffuse
        
        # Modulate
        rgbs = rgbs * intensity
        print("  Lighting applied.")
    
    background = torch.tensor([0.0, 0.0, 0.0], dtype=torch.float32, device=device) # Black BG for contrast
    # Model bounds approx +/- 2.75 (after 10x scale). 
    # Radius 2.5 was inside. Radius 8.0 was empty (too far/clipped?).
    # Try 4.5.
    radius = 3.0 # Closer to observed visibility range
    elevation = 1.0 
    n_frames = 120 # Smoother
    
    # Assume object is at 0,0,0 and scaled to unit box approximately
    # TRELLIS normalization might vary.
    
    print("Rendering...")
    for i in range(n_frames):
        angle = 2 * math.pi * i / n_frames
        eye_x = radius * math.cos(angle)
        eye_z = radius * math.sin(angle)
        eye = torch.tensor([eye_x, elevation, eye_z], dtype=torch.float32, device=device)
        target = torch.tensor([0, 0, 0], dtype=torch.float32, device=device)
        up = torch.tensor([0, 1, 0], dtype=torch.float32, device=device)
        
        viewmat = get_look_at(eye, target, up) # [4, 4]
        
        # Projection Matrix (K)
        fov_x = math.pi / 3.0
        # gsplat expects K matrix (3x3) usually?
        # rasterization(..., K=...)
        # K = [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]
        fx = width / (2 * math.tan(fov_x / 2))
        fy = fx
        cx = width / 2
        cy = height / 2
        K = torch.tensor([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=torch.float32, device=device)
        
        # Render
        # gsplat 1.0+: rasterization returns (color, alpha, info)
        # Note: shs shape handling. If we pass shs, we might need degree.
        # If shs is [N, 1, 3], degree=0.
        
        # We need to flatten SHs to [N, 3] if degree 0?
        # Or gsplat handles raw colors.
        # Let's convert SH to RGB manually to be safe if we are unsure about gsplat SH handling.
        # RGB = 0.5 + 0.28209 * SH
        # rgbs = 0.5 + 0.28209479177387814 * shs.squeeze(1)
        # rgbs = torch.clamp(rgbs, 0, 1) # Optional clamp
        
        # Call rasterization
        # colors: [N, D] or [N, 3]
        render_colors, render_alphas, info = rasterization(
            means=means,
            quats=quats,
            scales=scales,
            opacities=opacities,
            colors=rgbs,
            viewmats=viewmat.unsqueeze(0), # [1, 4, 4]
            Ks=K.unsqueeze(0),             # [1, 3, 3]
            width=width,
            height=height
        )
        
        # render_colors: [1, H, W, 3]
        # render_alphas: [1, H, W, 1]
        
        # Manual Composite with Black Background
        bg = torch.zeros_like(render_colors)
        final_color = render_colors + bg * (1.0 - render_alphas)
        
        # Gamma Correction
        final_color = torch.pow(final_color, 1.0/2.2)
        
        img = final_color[0].detach().cpu().numpy()
        img = np.clip(img * 255, 0, 255).astype(np.uint8)
        frames.append(img)
        
    imageio.mimsave(output_mp4, frames, fps=30)
    print(f"Saved video to {output_mp4}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    args = parser.parse_args()
    
    render_scene(args.input, args.output)
