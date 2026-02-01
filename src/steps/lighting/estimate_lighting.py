
import numpy as np
from plyfile import PlyData
import argparse
import json
import os

def sh2rgb(sh_coeffs):
    # SH (l=0, m=0) is Ambient DC. 
    # Constant factor for l=0 is 0.28209479177387814
    C0 = 0.28209479177387814
    return sh_coeffs * C0 + 0.5

def estimate_lighting_from_gs(ply_path, output_json):
    print(f"Loading 3DGS from {ply_path}...")
    plydata = PlyData.read(ply_path)
    v = plydata['vertex']
    
    # Extract Opacity to use as weight (sigmoid)
    opacities = 1 / (1 + np.exp(-v['opacity']))
    
    # Extract f_dc (0-th band SH)
    f_dc_0 = v['f_dc_0']
    f_dc_1 = v['f_dc_1']
    f_dc_2 = v['f_dc_2']
    
    # Valid mask (remove transparent junk)
    mask = opacities > 0.5
    
    print(f"Analyzing {np.sum(mask)} valid splats...")
    
    # Weighted Average of DC components
    # This gives us the "Average Color" of the scene
    avg_dc_0 = np.mean(f_dc_0[mask])
    avg_dc_1 = np.mean(f_dc_1[mask])
    avg_dc_2 = np.mean(f_dc_2[mask])
    
    ambient_rgb = sh2rgb(np.array([avg_dc_0, avg_dc_1, avg_dc_2]))
    
    # Normalize to 0-1
    ambient_rgb = np.clip(ambient_rgb, 0, 1)
    
    # Directional analysis (1st band SH) ???
    # Standard 3DGS PLY usually stores f_rest for higher bands.
    # If present, we can estimate dominant direction.
    # f_rest_0..2 (Y, Z, X bases usually) per channel.
    # This is complex because SH is view-dependent.
    # But statistical SH direction can hint at "brightest direction".
    
    # For now, let's just output Ambient Color.
    print(f"Estimated Scene Ambient: RGB{ambient_rgb}")
    
    # Pack result
    light_data = {
        "source_ply": ply_path,
        "ambient_light": {
            "r": float(ambient_rgb[0]),
            "g": float(ambient_rgb[1]),
            "b": float(ambient_rgb[2])
        },
        "intensity": float(np.mean(ambient_rgb)),
        "note": "Derived from 3DGS SH_DC average"
    }
    
    with open(output_json, 'w') as f:
        json.dump(light_data, f, indent=4)
    print(f"Saved lighting estimation to {output_json}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    estimate_lighting_from_gs(args.input, args.output)
