
import numpy as np
from plyfile import PlyData, PlyElement
import argparse
import math

def rescale_ply(input_path, output_path, scale_factor=10.0):
    print(f"Loading {input_path}...")
    plydata = PlyData.read(input_path)
    
    # modify vertices
    vertex = plydata.elements[0]
    
    # 1. Scale Positions
    vertex.data['x'] *= scale_factor
    vertex.data['y'] *= scale_factor
    vertex.data['z'] *= scale_factor
    
    # 2. Scale Log-Scales
    # scales are stored as log(scale).
    # new_scale = scale * factor
    # log(new_scale) = log(scale) + log(factor)
    log_factor = math.log(scale_factor)
    
    for prop in ['scale_0', 'scale_1', 'scale_2']:
        vertex.data[prop] += log_factor
        
    print(f"Rescaled by {scale_factor}x (Log-scale shift: +{log_factor:.4f})")
    
    # Save
    PlyData([vertex], text=False).write(output_path)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", type=str, required=True)
    parser.add_argument("--output", "-o", type=str, required=True)
    args = parser.parse_args()
    
    rescale_ply(args.input, args.output)
