
import trimesh
import numpy as np
import argparse
# plyfile might need to be installed or use trimesh export?
# Standard 3DGS PLY has custom fields not supported by standard mesh exporters.
# We use plyfile.
import sys
try:
    from plyfile import PlyData, PlyElement
except ImportError:
    print("Please install plyfile: pip install plyfile")
    sys.exit(1)

def convert_glb_to_gs(input_path, output_path):
    print(f"Loading {input_path}...")
    # force='mesh' might lose color if point cloud?
    # trimesh.load handles scene.
    scene = trimesh.load(input_path)
    
    if isinstance(scene, trimesh.Scene):
        # Merge all geometries
        verts_list = []
        colors_list = []
        for g in scene.geometry.values():
            verts_list.append(g.vertices)
            if hasattr(g, 'visual') and hasattr(g.visual, 'vertex_colors'):
                colors_list.append(g.visual.vertex_colors)
            elif hasattr(g, 'colors') and g.colors is not None:
                colors_list.append(g.colors)
            else:
                colors_list.append(np.ones((len(g.vertices), 4)) * 255)
        
        if len(verts_list) == 0:
            print("Empty scene")
            return
            
        verts = np.concatenate(verts_list)
        colors = np.concatenate(colors_list)
    elif hasattr(scene, 'vertices'):
        verts = scene.vertices
        if hasattr(scene, 'visual') and hasattr(scene.visual, 'vertex_colors'):
            colors = scene.visual.vertex_colors
        elif hasattr(scene, 'colors') and scene.colors is not None:
            colors = scene.colors
        else:
            colors = np.ones((len(verts), 4)) * 255
    else:
        print(f"Unknown type: {type(scene)}")
        return

    N = verts.shape[0]
    print(f"Converting {N} points to Gaussians with KNN scaling...")
    
    # 1. Position
    x = verts[:, 0].astype(np.float32)
    y = verts[:, 1].astype(np.float32)
    z = verts[:, 2].astype(np.float32)
    
    # RGB [N, 4] -> [N, 3] Normalized
    if colors.shape[1] == 4:
        rgb = colors[:, :3] / 255.0
    else:
        rgb = colors / 255.0
    sh_dc = (rgb - 0.5) / 0.28209479177387814

    # 2. Scale Heuristic (KNN)
    # Using KDTree for mean distance to 3-nearest neighbors as splat radius
    from scipy.spatial import KDTree
    print("Calculating spatial scales...")
    tree = KDTree(verts)
    dists, _ = tree.query(verts, k=4) # k=4 because k=1 is the point itself
    avg_dist = np.mean(dists[:, 1:], axis=1)
    # scale = log(distance * factor)
    # We want the splats to slightly overlap to form a surface
    scale_val = np.log(avg_dist * 1.5).astype(np.float32)
    scale_0 = scale_val
    scale_1 = scale_val
    scale_2 = scale_val
    
    # 4. Rotation
    rot_0 = np.ones(N, dtype=np.float32)
    rot_1 = np.zeros(N, dtype=np.float32)
    rot_2 = np.zeros(N, dtype=np.float32)
    rot_3 = np.zeros(N, dtype=np.float32)
    
    # 5. Opacity
    opacity = np.full(N, 10.0, dtype=np.float32)
    
    # 6. Normals (Optional, fill 0)
    nx = np.zeros(N, dtype=np.float32)
    ny = np.zeros(N, dtype=np.float32)
    nz = np.zeros(N, dtype=np.float32)
    
    # Construct PLY
    dtype = [('x', 'f4'), ('y', 'f4'), ('z', 'f4'),
             ('nx', 'f4'), ('ny', 'f4'), ('nz', 'f4'),
             ('f_dc_0', 'f4'), ('f_dc_1', 'f4'), ('f_dc_2', 'f4'),
             ('opacity', 'f4'),
             ('scale_0', 'f4'), ('scale_1', 'f4'), ('scale_2', 'f4'),
             ('rot_0', 'f4'), ('rot_1', 'f4'), ('rot_2', 'f4'), ('rot_3', 'f4')]
             
    data = np.zeros(N, dtype=dtype)
    data['x'] = x
    data['y'] = y
    data['z'] = z
    data['nx'] = nx
    data['ny'] = ny
    data['nz'] = nz
    data['f_dc_0'] = sh_dc[:, 0]
    data['f_dc_1'] = sh_dc[:, 1]
    data['f_dc_2'] = sh_dc[:, 2]
    data['opacity'] = opacity
    data['scale_0'] = scale_0
    data['scale_1'] = scale_1
    data['scale_2'] = scale_2
    data['rot_0'] = rot_0
    
    ply_el = PlyElement.describe(data, 'vertex')
    PlyData([ply_el], text=False).write(output_path)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    convert_glb_to_gs(args.input, args.output)
