"""
Author: zhangxin
Description: 从视频素材中提取高质关键帧，用于 3D 重建管线的输入。
"""
import cv2
import os
import argparse

def extract_frames(video_path, output_dir, interval=30):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return

    count = 0
    saved_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if count % interval == 0:
            frame_name = os.path.join(output_dir, f"frame_{saved_count:04d}.png")
            cv2.imwrite(frame_name, frame)
            saved_count += 1
            print(f"Saved: {frame_name}")
        
        count += 1
    
    cap.release()
    print(f"Done. Extracted {saved_count} frames.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract frames from video")
    parser.add_argument("--video", required=True, help="Path to video file")
    parser.add_argument("--output", required=True, help="Path to output directory")
    parser.add_argument("--interval", type=int, default=30, help="Frame interval for sampling")
    
    args = parser.parse_args()
    extract_frames(args.video, args.output, args.interval)
