"""
风格迁移模块
Author: zhangxin
功能: 将源图像的调色风格（基于指纹）迁移到目标图像
"""

import torch
import numpy as np
from pathlib import Path
from typing import Optional

from movie_asset_3dgs.color.color_stats import ColorStats, analyze_exr, compute_luma_rec709
from movie_asset_3dgs.color.grade_fingerprint import GradeFingerprint


def match_histogram_1d(source: torch.Tensor, target_mean: float, target_std: float) -> torch.Tensor:
    """
    简单的直方图匹配：将 source 的分布调整到目标的 mean/std
    
    Args:
        source: 1D 或多维 tensor
        target_mean: 目标均值
        target_std: 目标标准差
        
    Returns:
        调整后的 tensor
    """
    src_mean = source.mean()
    src_std = source.std()
    
    if src_std < 1e-6:
        return source
    
    # 标准化后重新缩放
    normalized = (source - src_mean) / src_std
    matched = normalized * target_std + target_mean
    
    return matched


def apply_color_balance(image: torch.Tensor, 
                        target_rg_ratio: float, 
                        target_bg_ratio: float) -> torch.Tensor:
    """
    调整图像的色彩平衡（相对于绿通道）
    
    Args:
        image: (H, W, 3) RGB tensor
        target_rg_ratio: 目标 R/G 比值
        target_bg_ratio: 目标 B/G 比值
        
    Returns:
        调整后的图像
    """
    r, g, b = image[..., 0], image[..., 1], image[..., 2]
    
    # 当前比值
    g_mean = g.mean()
    if g_mean < 1e-6:
        return image
    
    current_r_mean = r.mean()
    current_b_mean = b.mean()
    
    current_rg = current_r_mean / g_mean
    current_bg = current_b_mean / g_mean
    
    # 计算缩放因子
    if current_rg > 1e-6:
        r_scale = target_rg_ratio / current_rg
    else:
        r_scale = 1.0
        
    if current_bg > 1e-6:
        b_scale = target_bg_ratio / current_bg
    else:
        b_scale = 1.0
    
    # 应用缩放
    new_r = r * r_scale
    new_b = b * b_scale
    
    result = torch.stack([new_r, g, new_b], dim=-1)
    return result


def transfer_style(source_image: torch.Tensor, 
                   target_fingerprint: GradeFingerprint,
                   transfer_luma: bool = True,
                   transfer_color: bool = True,
                   transfer_saturation: bool = True) -> torch.Tensor:
    """
    将目标调色指纹的风格迁移到源图像
    
    Args:
        source_image: (H, W, 3) RGB tensor (linear space)
        target_fingerprint: 目标风格的 GradeFingerprint
        transfer_luma: 是否迁移亮度
        transfer_color: 是否迁移色彩平衡
        transfer_saturation: 是否迁移饱和度
        
    Returns:
        风格迁移后的图像
    """
    result = source_image.clone()
    
    # 1. 亮度匹配
    if transfer_luma:
        current_luma = compute_luma_rec709(result)
        
        # 匹配目标的 luma 分布
        matched_luma = match_histogram_1d(
            current_luma, 
            target_fingerprint.avg_luma_mean, 
            target_fingerprint.avg_luma_std
        )
        
        # 按比例调整 RGB（保持色相）
        scale = matched_luma / (current_luma + 1e-6)
        scale = scale.unsqueeze(-1)  # (H, W, 1)
        result = result * scale
    
    # 2. 色彩平衡匹配
    if transfer_color:
        result = apply_color_balance(
            result,
            target_fingerprint.color_balance_ratio[0],  # R/G
            target_fingerprint.color_balance_ratio[1],  # B/G
        )
    
    # 3. 饱和度匹配 (简化处理)
    if transfer_saturation:
        # 计算当前饱和度
        luma = compute_luma_rec709(result).unsqueeze(-1)
        
        # 分离亮度和色度
        chroma = result - luma
        
        # 当前饱和度
        current_sat = chroma.abs().mean()
        target_sat = target_fingerprint.avg_saturation_mean * luma.mean()
        
        if current_sat > 1e-6:
            sat_scale = target_sat / current_sat
            # 限制极端缩放
            sat_scale = max(0.5, min(2.0, sat_scale))
            chroma = chroma * sat_scale
        
        result = luma + chroma
    
    # Clamp 到有效范围
    result = torch.clamp(result, 0.0, 1.0)
    
    return result


def transfer_style_from_file(source_path: Path, 
                             fingerprint_path: Path,
                             output_path: Path) -> None:
    """
    从文件执行风格迁移
    
    Args:
        source_path: 源图像路径 (EXR 或 PNG)
        fingerprint_path: 目标指纹 JSON 路径
        output_path: 输出图像路径
    """
    from movie_asset_3dgs.data.cinema_utils import load_exr_image, gamma_correct
    from PIL import Image
    
    # 加载指纹
    with open(fingerprint_path) as f:
        fp = GradeFingerprint.from_json(f.read())
    
    # 加载源图像
    if source_path.suffix.lower() == '.exr':
        source = load_exr_image(source_path)
    else:
        # 假设是 sRGB PNG/JPG，需要线性化
        img = Image.open(source_path).convert('RGB')
        source = torch.from_numpy(np.array(img)).float() / 255.0
        # sRGB to Linear (approximate)
        source = source ** 2.2
    
    # 执行风格迁移
    result = transfer_style(source, fp)
    
    # 保存结果 (Gamma 校正后保存为 PNG)
    display = gamma_correct(result, gamma=2.2)
    display_np = (display.clamp(0, 1) * 255).numpy().astype(np.uint8)
    img_out = Image.fromarray(display_np)
    img_out.save(output_path)
    print(f"Style transferred image saved to: {output_path}")
