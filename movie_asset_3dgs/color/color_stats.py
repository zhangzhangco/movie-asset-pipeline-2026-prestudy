"""
色彩统计分析模块
Author: zhangxin
功能: 从 EXR/Linear 图像中提取色彩统计特征
"""

import torch
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path

from movie_asset_3dgs.data.cinema_utils import load_exr_image


@dataclass
class ColorStats:
    """色彩统计数据结构"""
    # 基础统计
    min_val: float
    max_val: float
    mean_val: float
    std_val: float
    
    # 动态范围 (以 stops 为单位)
    dynamic_range_stops: float
    
    # 通道统计 (R, G, B)
    channel_means: tuple  # (R_mean, G_mean, B_mean)
    channel_stds: tuple   # (R_std, G_std, B_std)
    
    # 亮度统计 (Rec.709 Luma)
    luma_mean: float
    luma_std: float
    luma_percentiles: Dict[int, float]  # {1: val, 50: val, 99: val}
    
    # 色度统计
    saturation_mean: float
    saturation_std: float


def compute_luma_rec709(image: torch.Tensor) -> torch.Tensor:
    """
    计算 Rec.709 亮度（线性空间）
    Args:
        image: (H, W, 3) RGB tensor, linear space
    Returns:
        (H, W) luma tensor
    """
    # Rec.709 coefficients for linear light
    r, g, b = image[..., 0], image[..., 1], image[..., 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return luma


def compute_saturation(image: torch.Tensor) -> torch.Tensor:
    """
    计算饱和度 (Chroma / Luma 的近似)
    Args:
        image: (H, W, 3) RGB tensor
    Returns:
        (H, W) saturation tensor
    """
    luma = compute_luma_rec709(image)
    # 避免除零
    luma_safe = torch.clamp(luma, min=1e-6)
    
    # Chroma = max(R,G,B) - min(R,G,B)
    max_rgb = image.max(dim=-1).values
    min_rgb = image.min(dim=-1).values
    chroma = max_rgb - min_rgb
    
    # Saturation = Chroma / Luma
    saturation = chroma / luma_safe
    return saturation


def analyze_exr(path: Path) -> ColorStats:
    """
    分析单个 EXR 文件的色彩统计
    
    Args:
        path: EXR 文件路径
        
    Returns:
        ColorStats 数据结构
    """
    # 加载 EXR (已经是 linear, [0,1] clamped)
    image = load_exr_image(path)  # (H, W, C)
    
    # 基础统计
    min_val = image.min().item()
    max_val = image.max().item()
    mean_val = image.mean().item()
    std_val = image.std().item()
    
    # 动态范围 (stops = log2(max/min))
    # 注意: 我们的 loader 做了 clamp，所以真实 HDR 范围可能被截断
    # 这里做一个安全计算
    if min_val > 0 and max_val > min_val:
        dynamic_range_stops = np.log2(max_val / min_val)
    else:
        dynamic_range_stops = 0.0
    
    # 通道统计
    channel_means = tuple(image[..., c].mean().item() for c in range(3))
    channel_stds = tuple(image[..., c].std().item() for c in range(3))
    
    # 亮度统计
    luma = compute_luma_rec709(image)
    luma_mean = luma.mean().item()
    luma_std = luma.std().item()
    
    # 亮度百分位
    luma_flat = luma.flatten()
    luma_percentiles = {
        1: torch.quantile(luma_flat, 0.01).item(),
        50: torch.quantile(luma_flat, 0.50).item(),
        99: torch.quantile(luma_flat, 0.99).item(),
    }
    
    # 饱和度统计
    saturation = compute_saturation(image)
    saturation_mean = saturation.mean().item()
    saturation_std = saturation.std().item()
    
    return ColorStats(
        min_val=min_val,
        max_val=max_val,
        mean_val=mean_val,
        std_val=std_val,
        dynamic_range_stops=dynamic_range_stops,
        channel_means=channel_means,
        channel_stds=channel_stds,
        luma_mean=luma_mean,
        luma_std=luma_std,
        luma_percentiles=luma_percentiles,
        saturation_mean=saturation_mean,
        saturation_std=saturation_std,
    )


def print_color_stats(stats: ColorStats, name: str = "EXR") -> None:
    """打印色彩统计报告"""
    print(f"\n=== Color Analysis: {name} ===")
    print(f"Value Range: [{stats.min_val:.4f}, {stats.max_val:.4f}]")
    print(f"Mean / Std: {stats.mean_val:.4f} / {stats.std_val:.4f}")
    print(f"Dynamic Range: {stats.dynamic_range_stops:.2f} stops")
    print(f"\nChannel Means (R/G/B): {stats.channel_means[0]:.4f} / {stats.channel_means[1]:.4f} / {stats.channel_means[2]:.4f}")
    print(f"Channel Stds  (R/G/B): {stats.channel_stds[0]:.4f} / {stats.channel_stds[1]:.4f} / {stats.channel_stds[2]:.4f}")
    print(f"\nLuma Mean / Std: {stats.luma_mean:.4f} / {stats.luma_std:.4f}")
    print(f"Luma Percentiles (1%/50%/99%): {stats.luma_percentiles[1]:.4f} / {stats.luma_percentiles[50]:.4f} / {stats.luma_percentiles[99]:.4f}")
    print(f"\nSaturation Mean / Std: {stats.saturation_mean:.4f} / {stats.saturation_std:.4f}")
