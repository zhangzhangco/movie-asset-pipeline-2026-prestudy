"""
单目深度估计模块
Author: zhangxin
功能: 使用预训练模型 (Depth Anything V2) 从单张图像估计深度图
"""

import torch
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional, Tuple

# 延迟导入，避免启动时加载大模型
_depth_model = None
_depth_processor = None


def _load_depth_model(device: str = "cuda"):
    """
    懒加载 Depth Anything V2 模型
    """
    global _depth_model, _depth_processor
    
    if _depth_model is not None:
        return _depth_model, _depth_processor
    
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation
    
    print("Loading Depth Anything V2 model...")
    model_id = "depth-anything/Depth-Anything-V2-Small-hf"
    
    _depth_processor = AutoImageProcessor.from_pretrained(model_id)
    _depth_model = AutoModelForDepthEstimation.from_pretrained(model_id)
    _depth_model = _depth_model.to(device)
    _depth_model.eval()
    
    print(f"Depth model loaded on {device}")
    return _depth_model, _depth_processor


def estimate_depth(
    image: torch.Tensor | np.ndarray | Image.Image,
    device: str = "cuda",
    normalize: bool = True,
) -> torch.Tensor:
    """
    估计单张图像的深度图
    
    Args:
        image: 输入图像，支持多种格式:
            - torch.Tensor: (H, W, 3) 或 (3, H, W), 范围 [0, 1]
            - np.ndarray: (H, W, 3), 范围 [0, 255] uint8 或 [0, 1] float
            - PIL.Image
        device: 推理设备
        normalize: 是否将输出归一化到 [0, 1]
        
    Returns:
        torch.Tensor: (H, W) 深度图，近处值小，远处值大
    """
    model, processor = _load_depth_model(device)
    
    # 统一转换为 PIL Image
    if isinstance(image, torch.Tensor):
        if image.ndim == 3 and image.shape[0] == 3:
            image = image.permute(1, 2, 0)  # CHW -> HWC
        image_np = (image.cpu().numpy() * 255).astype(np.uint8)
        pil_image = Image.fromarray(image_np)
    elif isinstance(image, np.ndarray):
        if image.dtype == np.float32 or image.dtype == np.float64:
            image = (image * 255).astype(np.uint8)
        pil_image = Image.fromarray(image)
    else:
        pil_image = image
    
    original_size = pil_image.size  # (W, H)
    
    # 预处理
    inputs = processor(images=pil_image, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    # 推理
    with torch.no_grad():
        outputs = model(**inputs)
        predicted_depth = outputs.predicted_depth
    
    # 后处理：调整回原始尺寸
    depth = torch.nn.functional.interpolate(
        predicted_depth.unsqueeze(0),
        size=(original_size[1], original_size[0]),  # (H, W)
        mode="bicubic",
        align_corners=False,
    ).squeeze()
    
    # 归一化
    if normalize:
        depth_min = depth.min()
        depth_max = depth.max()
        if depth_max > depth_min:
            depth = (depth - depth_min) / (depth_max - depth_min)
        else:
            depth = torch.zeros_like(depth)
    
    return depth


def depth_to_colormap(depth: torch.Tensor, colormap: str = "magma") -> np.ndarray:
    """
    将深度图转换为彩色可视化
    
    Args:
        depth: (H, W) 深度图，范围 [0, 1]
        colormap: matplotlib colormap 名称
        
    Returns:
        np.ndarray: (H, W, 3) RGB 图像，uint8
    """
    import matplotlib.pyplot as plt
    
    depth_np = depth.cpu().numpy()
    cmap = plt.get_cmap(colormap)
    colored = cmap(depth_np)[:, :, :3]  # 去掉 alpha
    return (colored * 255).astype(np.uint8)


def create_depth_layers(
    image: torch.Tensor,
    depth: torch.Tensor,
    num_layers: int = 3,
) -> list[Tuple[torch.Tensor, torch.Tensor]]:
    # Ensure both tensors are on the same device (CPU for simplicity)
    image = image.cpu()
    depth = depth.cpu()
    """
    根据深度将图像分割成多个层
    
    Args:
        image: (H, W, 3) RGB 图像
        depth: (H, W) 深度图，范围 [0, 1]
        num_layers: 分层数量
        
    Returns:
        list of (layer_image, layer_mask): 每层的图像和对应的 mask
    """
    layers = []
    thresholds = torch.linspace(0, 1, num_layers + 1)
    
    for i in range(num_layers):
        low = thresholds[i]
        high = thresholds[i + 1]
        
        # 创建该深度范围的 mask
        mask = (depth >= low) & (depth < high)
        mask = mask.float().unsqueeze(-1)  # (H, W, 1)
        
        # 应用 mask 到图像
        layer_image = image * mask
        
        layers.append((layer_image, mask.squeeze(-1)))
    
    return layers


def estimate_depth_from_file(
    input_path: Path,
    output_depth_path: Optional[Path] = None,
    output_colormap_path: Optional[Path] = None,
    device: str = "cuda",
) -> torch.Tensor:
    """
    从文件读取图像并估计深度
    
    Args:
        input_path: 输入图像路径
        output_depth_path: 可选，保存深度图 (numpy .npy)
        output_colormap_path: 可选，保存彩色深度图 (PNG)
        device: 推理设备
        
    Returns:
        深度图 tensor
    """
    # 加载图像
    if input_path.suffix.lower() == '.exr':
        from movie_asset_3dgs.data.cinema_utils import load_exr_image, gamma_correct
        image = load_exr_image(input_path)
        # 需要 gamma 校正后再送入深度模型（模型期望 sRGB 输入）
        image = gamma_correct(image, gamma=2.2)
    else:
        image = Image.open(input_path).convert('RGB')
    
    # 估计深度
    depth = estimate_depth(image, device=device)
    
    # 保存
    if output_depth_path:
        np.save(output_depth_path, depth.cpu().numpy())
        print(f"Depth saved to: {output_depth_path}")
    
    if output_colormap_path:
        colored = depth_to_colormap(depth)
        Image.fromarray(colored).save(output_colormap_path)
        print(f"Colored depth saved to: {output_colormap_path}")
    
    return depth
