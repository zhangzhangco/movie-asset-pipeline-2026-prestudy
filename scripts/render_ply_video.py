
import open3d as o3d
import numpy as np
import os
import sys
import argparse
import cv2

def render_point_cloud_video(ply_path, output_video_path, num_frames=120):
    print(f"Loading point cloud from {ply_path}...")
    pcd = o3d.io.read_point_cloud(ply_path)
    
    if not pcd.has_points():
        print("Error: Point cloud is empty.")
        return

    # Center the point cloud
    center = pcd.get_center()
    pcd.translate(-center)

    vis = o3d.visualization.Visualizer()
    vis.create_window(visible=False, width=1280, height=720)
    vis.add_geometry(pcd)

    render_option = vis.get_render_option()
    render_option.point_size = 2.0
    render_option.background_color = np.asarray([0.05, 0.05, 0.05]) # Dark background

    view_control = vis.get_view_control()
    
    # Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, 30.0, (1280, 720))

    print(f"Rendering {num_frames} frames to {output_video_path}...")
    for i in range(num_frames):
        # Rotate camera
        view_control.rotate(10.0, 0.0) # Horizontal rotation
        vis.poll_events()
        vis.update_renderer()
        
        # Capture frame
        image = vis.capture_screen_float_buffer(False)
        image = (np.asarray(image) * 255).astype(np.uint8)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        out.write(image)
        if i % 10 == 0:
            print(f"Progress: {i}/{num_frames}")

    out.release()
    vis.destroy_window()
    print("Video rendering complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to .ply file")
    parser.add_argument("--output", required=True, help="Path to output .mp4")
    parser.add_argument("--frames", type=int, default=120, help="Number of frames")
    args = parser.parse_args()

    render_point_cloud_video(args.input, args.output, args.frames)
