#!/usr/bin/env python3
"""
镜头运动检测脚本
Author: zhangxin
功能: 分析帧序列，检测哪些时间区间有足够的相机移动（适合 3DGS 训练）
"""

import cv2
import numpy as np
from pathlib import Path
from collections import defaultdict
import argparse


def compute_optical_flow_magnitude(frame1: np.ndarray, frame2: np.ndarray) -> float:
    """
    计算两帧之间的光流幅度（使用 Farneback 算法）
    返回平均光流幅度（像素/帧）
    """
    # 转灰度
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # 缩小尺寸加快计算
    scale = 0.25
    gray1 = cv2.resize(gray1, None, fx=scale, fy=scale)
    gray2 = cv2.resize(gray2, None, fx=scale, fy=scale)
    
    # 计算光流
    flow = cv2.calcOpticalFlowFarneback(
        gray1, gray2, None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0
    )
    
    # 计算幅度
    magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
    
    # 返回平均幅度（还原到原始尺度）
    return float(np.mean(magnitude)) / scale


def detect_scene_change(frame1: np.ndarray, frame2: np.ndarray, threshold: float = 30.0) -> bool:
    """
    检测镜头切换（通过直方图差异）
    """
    hist1 = cv2.calcHist([frame1], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    hist2 = cv2.calcHist([frame2], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    
    diff = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CHISQR)
    return diff > threshold


def analyze_sequence(image_dir: Path, sample_interval: int = 5, fps: float = 24.0) -> dict:
    """
    分析帧序列，返回各区间的运动统计
    
    Args:
        image_dir: 图像目录
        sample_interval: 采样间隔（每 N 帧分析一次）
        fps: 帧率
        
    Returns:
        dict: 分析结果
    """
    # 获取所有图像文件
    image_files = sorted(image_dir.glob("*.png"))
    if not image_files:
        image_files = sorted(image_dir.glob("*.jpg"))
    
    print(f"Found {len(image_files)} frames")
    
    # 每 sample_interval 帧采样一次
    sampled_files = image_files[::sample_interval]
    print(f"Sampling every {sample_interval} frames -> {len(sampled_files)} samples")
    
    results = []
    scene_changes = []
    prev_frame = None
    prev_idx = 0
    
    for i, img_path in enumerate(sampled_files):
        if i % 100 == 0:
            print(f"  Processing {i}/{len(sampled_files)}...")
        
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue
        
        frame_idx = int(img_path.stem)
        
        if prev_frame is not None:
            # 检测镜头切换
            is_scene_change = detect_scene_change(prev_frame, frame)
            
            if is_scene_change:
                scene_changes.append(frame_idx)
            else:
                # 计算光流
                flow_mag = compute_optical_flow_magnitude(prev_frame, frame)
                
                results.append({
                    'frame_start': prev_idx,
                    'frame_end': frame_idx,
                    'flow_magnitude': flow_mag,
                    'time_start': prev_idx / fps,
                    'time_end': frame_idx / fps,
                })
        
        prev_frame = frame
        prev_idx = frame_idx
    
    return {
        'results': results,
        'scene_changes': scene_changes,
        'total_frames': len(image_files),
        'fps': fps,
    }


def find_good_segments(analysis: dict, 
                       min_flow: float = 2.0, 
                       min_duration: float = 2.0,
                       max_flow: float = 50.0) -> list:
    """
    找出适合 3DGS 的镜头区间
    
    Args:
        min_flow: 最小光流幅度（太小说明相机不动）
        min_duration: 最小持续时间（秒）
        max_flow: 最大光流幅度（太大可能是运动模糊严重）
    """
    results = analysis['results']
    scene_changes = set(analysis['scene_changes'])
    fps = analysis['fps']
    
    # 按帧号排序
    results = sorted(results, key=lambda x: x['frame_start'])
    
    # 找连续的好区间
    good_segments = []
    current_segment = None
    
    for r in results:
        flow = r['flow_magnitude']
        frame = r['frame_start']
        
        # 检查是否在镜头切换点
        is_cut = any(sc in range(r['frame_start'], r['frame_end'] + 1) for sc in scene_changes)
        
        # 判断是否是"好"的帧
        is_good = (min_flow <= flow <= max_flow) and not is_cut
        
        if is_good:
            if current_segment is None:
                current_segment = {
                    'start_frame': frame,
                    'end_frame': r['frame_end'],
                    'start_time': r['time_start'],
                    'end_time': r['time_end'],
                    'avg_flow': flow,
                    'count': 1,
                }
            else:
                current_segment['end_frame'] = r['frame_end']
                current_segment['end_time'] = r['time_end']
                current_segment['avg_flow'] = (current_segment['avg_flow'] * current_segment['count'] + flow) / (current_segment['count'] + 1)
                current_segment['count'] += 1
        else:
            # 保存当前区间（如果足够长）
            if current_segment is not None:
                duration = current_segment['end_time'] - current_segment['start_time']
                if duration >= min_duration:
                    current_segment['duration'] = duration
                    good_segments.append(current_segment)
                current_segment = None
    
    # 保存最后一个区间
    if current_segment is not None:
        duration = current_segment['end_time'] - current_segment['start_time']
        if duration >= min_duration:
            current_segment['duration'] = duration
            good_segments.append(current_segment)
    
    return good_segments


def format_time(seconds: float) -> str:
    """格式化时间为 MM:SS 格式"""
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins:02d}:{secs:05.2f}"


def main():
    parser = argparse.ArgumentParser(description="Detect camera motion segments for 3DGS")
    parser.add_argument("image_dir", type=Path, help="Directory containing frame images")
    parser.add_argument("--interval", type=int, default=10, help="Sampling interval (frames)")
    parser.add_argument("--fps", type=float, default=24.0, help="Frame rate")
    parser.add_argument("--min-flow", type=float, default=2.0, help="Minimum optical flow")
    parser.add_argument("--max-flow", type=float, default=50.0, help="Maximum optical flow")
    parser.add_argument("--min-duration", type=float, default=3.0, help="Minimum segment duration (seconds)")
    args = parser.parse_args()
    
    print(f"Analyzing: {args.image_dir}")
    print(f"Parameters: interval={args.interval}, fps={args.fps}")
    print()
    
    # 分析
    analysis = analyze_sequence(args.image_dir, args.interval, args.fps)
    
    print(f"\nScene changes detected: {len(analysis['scene_changes'])}")
    
    # 找好的区间
    good_segments = find_good_segments(
        analysis,
        min_flow=args.min_flow,
        max_flow=args.max_flow,
        min_duration=args.min_duration,
    )
    
    print(f"\n{'='*60}")
    print(f"GOOD SEGMENTS FOR 3DGS (camera motion detected)")
    print(f"{'='*60}")
    
    if not good_segments:
        print("No suitable segments found!")
    else:
        for i, seg in enumerate(good_segments):
            print(f"\nSegment {i+1}:")
            print(f"  Time: {format_time(seg['start_time'])} - {format_time(seg['end_time'])} ({seg['duration']:.1f}s)")
            print(f"  Frames: {seg['start_frame']} - {seg['end_frame']}")
            print(f"  Avg Motion: {seg['avg_flow']:.2f} px/frame")
    
    print(f"\n{'='*60}")
    print(f"Total good segments: {len(good_segments)}")
    total_duration = sum(s['duration'] for s in good_segments)
    print(f"Total good duration: {total_duration:.1f}s / {analysis['total_frames']/args.fps:.1f}s ({100*total_duration*args.fps/analysis['total_frames']:.1f}%)")


if __name__ == "__main__":
    main()
