#!/bin/bash
# CUDA 12.2 安装脚本
# 只安装 Toolkit，不动驱动

set -e

echo "🚀 开始安装 CUDA Toolkit 12.2..."

# 检查是否有 root 权限
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 sudo 运行此脚本"
    exit 1
fi

# 检查安装包是否存在
if [ ! -f /tmp/cuda_12.2.0_installer.run ]; then
    echo "❌ 安装包不存在: /tmp/cuda_12.2.0_installer.run"
    exit 1
fi

# 运行安装器（交互模式，只装 toolkit）
echo "📦 运行 CUDA 安装器..."
sh /tmp/cuda_12.2.0_installer.run --toolkit

echo ""
echo "✅ CUDA Toolkit 12.2 安装完成"
echo ""
echo "🔧 请运行以下命令设置环境变量："
echo ""
echo "export CUDA_HOME=/usr/local/cuda-12.2"
echo "export PATH=\$CUDA_HOME/bin:\$PATH"
echo "export LD_LIBRARY_PATH=\$CUDA_HOME/lib64:\$LD_LIBRARY_PATH"
echo ""
echo "或者将以上内容添加到 ~/.bashrc 中"
