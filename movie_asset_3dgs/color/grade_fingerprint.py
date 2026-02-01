"""
调色指纹模块
Author: zhangxin
功能: 从多帧 EXR 统计中生成 "调色指纹" (Grade Fingerprint)
"""

import json
import numpy as np
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from pathlib import Path

from movie_asset_3dgs.color.color_stats import ColorStats, analyze_exr


@dataclass
class GradeFingerprint:
    """
    调色指纹：基于多帧统计的风格特征向量
    可用于：风格对比、风格迁移、QC 检测
    """
    # 源信息
    source_name: str
    num_frames: int
    
    # 亮度特征 (跨帧平均)
    avg_luma_mean: float
    avg_luma_std: float
    avg_luma_p1: float   # 1% percentile (shadow level)
    avg_luma_p50: float  # median
    avg_luma_p99: float  # 99% percentile (highlight level)
    
    # 色彩平衡 (跨帧平均)
    avg_channel_means: tuple  # (R, G, B) 平均值
    color_balance_ratio: tuple  # (R/G, B/G) 相对于绿通道的比值
    
    # 饱和度特征
    avg_saturation_mean: float
    avg_saturation_std: float
    
    # 动态范围
    avg_dynamic_range_stops: float
    
    def to_vector(self) -> np.ndarray:
        """将指纹转换为数值向量，用于相似度计算"""
        return np.array([
            self.avg_luma_mean,
            self.avg_luma_std,
            self.avg_luma_p1,
            self.avg_luma_p50,
            self.avg_luma_p99,
            self.avg_channel_means[0],
            self.avg_channel_means[1],
            self.avg_channel_means[2],
            self.color_balance_ratio[0],
            self.color_balance_ratio[1],
            self.avg_saturation_mean,
            self.avg_saturation_std,
            self.avg_dynamic_range_stops,
        ])
    
    def to_json(self) -> str:
        """导出为 JSON 字符串"""
        return json.dumps(asdict(self), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "GradeFingerprint":
        """从 JSON 加载"""
        data = json.loads(json_str)
        # Convert lists back to tuples
        data['avg_channel_means'] = tuple(data['avg_channel_means'])
        data['color_balance_ratio'] = tuple(data['color_balance_ratio'])
        return cls(**data)


def compute_fingerprint(stats_list: List[ColorStats], source_name: str = "unknown") -> GradeFingerprint:
    """
    从多帧的 ColorStats 列表计算调色指纹
    
    Args:
        stats_list: 多帧的 ColorStats
        source_name: 素材名称
        
    Returns:
        GradeFingerprint
    """
    n = len(stats_list)
    if n == 0:
        raise ValueError("stats_list is empty")
    
    # 聚合亮度
    luma_means = [s.luma_mean for s in stats_list]
    luma_stds = [s.luma_std for s in stats_list]
    luma_p1s = [s.luma_percentiles[1] for s in stats_list]
    luma_p50s = [s.luma_percentiles[50] for s in stats_list]
    luma_p99s = [s.luma_percentiles[99] for s in stats_list]
    
    # 聚合通道
    r_means = [s.channel_means[0] for s in stats_list]
    g_means = [s.channel_means[1] for s in stats_list]
    b_means = [s.channel_means[2] for s in stats_list]
    
    avg_r = np.mean(r_means)
    avg_g = np.mean(g_means)
    avg_b = np.mean(b_means)
    
    # 色彩平衡比 (相对于 G)
    if avg_g > 1e-6:
        r_g_ratio = avg_r / avg_g
        b_g_ratio = avg_b / avg_g
    else:
        r_g_ratio = 1.0
        b_g_ratio = 1.0
    
    # 聚合饱和度
    sat_means = [s.saturation_mean for s in stats_list]
    sat_stds = [s.saturation_std for s in stats_list]
    
    # 聚合动态范围
    dr_stops = [s.dynamic_range_stops for s in stats_list]
    
    return GradeFingerprint(
        source_name=source_name,
        num_frames=n,
        avg_luma_mean=float(np.mean(luma_means)),
        avg_luma_std=float(np.mean(luma_stds)),
        avg_luma_p1=float(np.mean(luma_p1s)),
        avg_luma_p50=float(np.mean(luma_p50s)),
        avg_luma_p99=float(np.mean(luma_p99s)),
        avg_channel_means=(avg_r, avg_g, avg_b),
        color_balance_ratio=(r_g_ratio, b_g_ratio),
        avg_saturation_mean=float(np.mean(sat_means)),
        avg_saturation_std=float(np.mean(sat_stds)),
        avg_dynamic_range_stops=float(np.mean(dr_stops)),
    )


def fingerprint_similarity(fp1: GradeFingerprint, fp2: GradeFingerprint) -> float:
    """
    计算两个调色指纹之间的相似度 (余弦相似度)
    
    Returns:
        float: [0, 1] 范围，1 表示完全相似
    """
    v1 = fp1.to_vector()
    v2 = fp2.to_vector()
    
    # Cosine similarity
    dot = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 < 1e-9 or norm2 < 1e-9:
        return 0.0
    
    return float(dot / (norm1 * norm2))


def print_fingerprint(fp: GradeFingerprint) -> None:
    """打印调色指纹报告"""
    print(f"\n=== Grade Fingerprint: {fp.source_name} ===")
    print(f"Frames Analyzed: {fp.num_frames}")
    print(f"\nLuma Profile:")
    print(f"  Mean / Std: {fp.avg_luma_mean:.4f} / {fp.avg_luma_std:.4f}")
    print(f"  Shadows (1%): {fp.avg_luma_p1:.4f}")
    print(f"  Midtones (50%): {fp.avg_luma_p50:.4f}")
    print(f"  Highlights (99%): {fp.avg_luma_p99:.4f}")
    print(f"\nColor Balance:")
    print(f"  Channel Means (R/G/B): {fp.avg_channel_means[0]:.4f} / {fp.avg_channel_means[1]:.4f} / {fp.avg_channel_means[2]:.4f}")
    print(f"  R/G Ratio: {fp.color_balance_ratio[0]:.4f}")
    print(f"  B/G Ratio: {fp.color_balance_ratio[1]:.4f}")
    print(f"\nSaturation: Mean {fp.avg_saturation_mean:.4f}, Std {fp.avg_saturation_std:.4f}")
    print(f"Dynamic Range: {fp.avg_dynamic_range_stops:.2f} stops")
