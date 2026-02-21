
import numpy as np
import cv2
import os
from plyfile import PlyData
import time

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def project_ply_to_video_v3(ply_path, output_path, width=1280, height=720, num_frames=120):
    print(f"Reading PLY from {ply_path}...")
    plydata = PlyData.read(ply_path)
    
    # Extract positions
    x = np.array(plydata['vertex']['x'])
    y = np.array(plydata['vertex']['y'])
    z = np.array(plydata['vertex']['z'])
    points = np.stack([x, y, z], axis=-1)
    
    # Extract colors (DC components)
    f_dc_0 = np.array(plydata['vertex']['f_dc_0'])
    f_dc_1 = np.array(plydata['vertex']['f_dc_1'])
    f_dc_2 = np.array(plydata['vertex']['f_dc_2'])
    
    # SHARP/3DGS color normalization (SH DC approx)
    SH_C0 = 0.28209479177387814
    r = (0.5 + SH_C0 * f_dc_0)
    g = (0.5 + SH_C0 * f_dc_1)
    b = (0.5 + SH_C0 * f_dc_2)
    colors = np.stack([b, g, r], axis=-1) # BGR
    colors = np.clip(colors, 0, 1) * 255
    
    # Extract opacity
    try:
        opacity = sigmoid(np.array(plydata['vertex']['opacity']))
    except:
        opacity = np.ones(len(x))

    # Center and scale for visualization
    center = points.mean(axis=0)
    points -= center
    dist = np.linalg.norm(points, axis=1)
    scale = np.percentile(dist, 95) # Use 95th percentile to avoid outliers
    points /= (scale * 1.2)
    
    # Video setup
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(output_path, fourcc, 30, (width, height))
    
    # Use a slightly higher resolution for supersampling/splatting effect
    render_scale = 1.5
    rw, rh = int(width * render_scale), int(height * render_scale)
    
    print(f"Processing {len(points)} points with Soft-Splatting simulation...")
    for f in range(num_frames):
        start_time = time.time()
        angle = 2 * np.pi * f / num_frames
        
        # Camera rotation (Orbit)
        # We also add a slight pitch to see more structure
        pitch = 0.3 
        R_y = np.array([
            [np.cos(angle), 0, np.sin(angle)],
            [0, 1, 0],
            [-np.sin(angle), 0, np.cos(angle)]
        ])
        R_x = np.array([
            [1, 0, 0],
            [0, np.cos(pitch), -np.sin(pitch)],
            [0, np.sin(pitch), np.cos(pitch)]
        ])
        R = R_x @ R_y
        
        proj_points = points @ R.T
        
        # Perspective projection
        z_depth = proj_points[:, 2] + 2.5
        mask = z_depth > 0.5
        
        # Z-Sorting for back-to-front rendering (Alpha blending simulation)
        # Even with one-pass additive, sorting helps depth feel
        indices = np.argsort(-z_depth[mask])
        
        m_points = proj_points[mask][indices]
        m_colors = colors[mask][indices]
        m_opacity = opacity[mask][indices]
        m_z = z_depth[mask][indices]
        
        # Project to pixels
        px = (m_points[:, 0] / m_z * 1.5 * rw / 2 + rw / 2).astype(int)
        py = (m_points[:, 1] / m_z * 1.5 * rh / 2 + rh / 2).astype(int)
        
        # Valid bounds
        valid = (px >= 0) & (px < rw) & (py >= 0) & (py < rh)
        px, py = px[valid], py[valid]
        c = m_colors[valid]
        o = m_opacity[valid]
        
        # Create accumulators for Soft-Splat
        # Instead of individual dots, we use a single high-res pass + blur
        canvas = np.zeros((rh, rw, 3), dtype=np.float32)
        
        # Draw points
        # Optimization: We can't easily do alpha blend in loop, so we map the strongest points
        # To simulate 3DGS, we want overlapping points to brighten and blur
        # Simple additive hack for demo:
        # np.add.at is slow for 1M. We'll just use assignment; the Z-sort deals with occlusion.
        canvas[py, px] = c * o[:, None]
        
        # Apply Soft-Gaussian Splatting effect via Blur
        # 3GS essentially "smears" points.
        canvas = cv2.GaussianBlur(canvas, (3, 3), 0)
        
        # Downsample to final resolution (Antialiasing)
        frame = cv2.resize(canvas, (width, height), interpolation=cv2.INTER_AREA)
        frame = np.clip(frame, 0, 255).astype(np.uint8)
        
        # Add a subtle vignette for "premium" feel
        video.write(frame)
        
        if f % 30 == 0:
            elapsed = time.time() - start_time
            print(f"Frame {f}/{num_frames} ({elapsed:.2f}s)")
            
    video.release()
    print(f"Fidelity video saved to {output_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python project_3d_to_video.py <input.ply> <output.mp4>")
    else:
        project_ply_to_video_v3(sys.argv[1], sys.argv[2])
