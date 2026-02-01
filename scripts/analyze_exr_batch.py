#!/usr/bin/env python3
"""
批量 EXR 分析脚本 (支持从 ZIP 中直接读取)
Author: zhangxin
用法: python scripts/analyze_exr_batch.py <zip_path> [--limit N] [--output fingerprint.json]
"""

import argparse
import zipfile
import tempfile
import os
from pathlib import Path
from typing import List

from movie_asset_3dgs.color.color_stats import analyze_exr, ColorStats, print_color_stats
from movie_asset_3dgs.color.grade_fingerprint import compute_fingerprint, print_fingerprint


def list_exr_in_zip(zip_path: Path) -> List[str]:
    """列出 ZIP 中所有 EXR 文件"""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        return [name for name in zf.namelist() if name.lower().endswith('.exr')]


def analyze_exr_from_zip(zip_path: Path, internal_path: str) -> ColorStats:
    """
    从 ZIP 中提取单个 EXR 到临时目录并分析
    """
    with zipfile.ZipFile(zip_path, 'r') as zf:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 提取到临时目录
            extracted_path = zf.extract(internal_path, tmpdir)
            return analyze_exr(Path(extracted_path))


def main():
    parser = argparse.ArgumentParser(description="Analyze EXR files from a ZIP archive")
    parser.add_argument("zip_path", type=Path, help="Path to the ZIP file containing EXRs")
    parser.add_argument("--limit", type=int, default=10, help="Max number of frames to analyze (default: 10)")
    parser.add_argument("--output", type=Path, default=None, help="Output fingerprint JSON file")
    parser.add_argument("--verbose", action="store_true", help="Print stats for each frame")
    args = parser.parse_args()
    
    if not args.zip_path.exists():
        print(f"Error: ZIP file not found: {args.zip_path}")
        return 1
    
    # 列出 EXR 文件
    exr_files = list_exr_in_zip(args.zip_path)
    print(f"Found {len(exr_files)} EXR files in {args.zip_path.name}")
    
    if len(exr_files) == 0:
        print("No EXR files found!")
        return 1
    
    # 排序并取中间段 (避免片头片尾太暗或太亮)
    exr_files.sort()
    start_idx = len(exr_files) // 4  # 从 1/4 处开始
    selected = exr_files[start_idx : start_idx + args.limit]
    
    print(f"Analyzing {len(selected)} frames (from middle section)...")
    
    # 分析每一帧
    stats_list: List[ColorStats] = []
    for i, exr_name in enumerate(selected):
        print(f"  [{i+1}/{len(selected)}] {Path(exr_name).name}", end="")
        try:
            stats = analyze_exr_from_zip(args.zip_path, exr_name)
            stats_list.append(stats)
            print(f" - Luma: {stats.luma_mean:.4f}")
            
            if args.verbose:
                print_color_stats(stats, exr_name)
        except Exception as e:
            print(f" - ERROR: {e}")
    
    if len(stats_list) == 0:
        print("No frames successfully analyzed!")
        return 1
    
    # 生成指纹
    source_name = args.zip_path.stem
    fingerprint = compute_fingerprint(stats_list, source_name)
    print_fingerprint(fingerprint)
    
    # 导出 JSON
    if args.output:
        args.output.write_text(fingerprint.to_json())
        print(f"\nFingerprint saved to: {args.output}")
    
    return 0


if __name__ == "__main__":
    exit(main())
