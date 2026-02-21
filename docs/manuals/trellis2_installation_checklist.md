# TRELLIS.2 安装执行清单

## ✅ 已完成检查

### GPU 架构验证
```bash
nvidia-smi --query-gpu=name,compute_cap --format=csv
# 结果: NVIDIA RTX A6000, 8.6 (Ampere 架构)
# ✅ 满足 flash-attn 要求（sm80+）
```

### 当前环境状态
```bash
which nvcc              # /usr/bin/nvcc
nvcc -V                 # 11.5.119 (过低)
torch.version.cuda      # 11.8 (不匹配)
CUDA_HOME               # (空)
/usr/local/cuda*        # 不存在
驱动能力上限             # 12.2
```

## 🚧 当前进度：CUDA Toolkit 12.2 安装

### 问题
CUDA 12.2 runfile 安装器遇到执行错误：
```
/tmp/cuda_12.2.0_installer.run: 451: exec: -title: not found
```

### 解决方案选项

#### 选项 1: 使用 apt 包管理器安装（推荐）
```bash
# 添加 NVIDIA CUDA 仓库
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update

# 安装 CUDA Toolkit 12.2
sudo apt-get install -y cuda-toolkit-12-2

# 设置环境变量
export CUDA_HOME=/usr/local/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# 验证
nvcc -V
```

#### 选项 2: 手动解压 runfile 后安装
```bash
# 解压安装包
sh /tmp/cuda_12.2.0_installer.run --extract=/tmp/cuda_12.2_extracted

# 进入解压目录手动安装
cd /tmp/cuda_12.2_extracted
sudo ./cuda-installer --toolkit --toolkitpath=/usr/local/cuda-12.2
```

#### 选项 3: 使用 Docker（最稳妥）
```bash
# 启动 CUDA 12.2 devel 容器
docker run --gpus all -it --rm \
  --name trellis2_build \
  -v /home/zhangxin/2026Projects/preStudy:/workspace \
  nvidia/cuda:12.2.0-devel-ubuntu22.04 bash

# 容器内已有 nvcc 12.2，直接安装 PyTorch 和扩展
```

## 📋 后续步骤（CUDA 安装完成后）

### 1. 设置环境变量（永久生效）
```bash
cat >> ~/.bashrc <<'EOF'
export CUDA_HOME=/usr/local/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
EOF

source ~/.bashrc
hash -r
```

### 2. 验证 nvcc 版本
```bash
which nvcc  # 必须是 /usr/local/cuda-12.2/bin/nvcc
nvcc -V     # 必须显示 12.2
```

### 3. 安装 PyTorch cu121
```bash
conda activate trellis2
pip uninstall -y torch torchvision torchaudio
pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121

# 验证
python -c "import torch; print('PyTorch:', torch.__version__, 'CUDA:', torch.version.cuda)"
# 应该显示: PyTorch: 2.5.1+cu121 CUDA: 12.1
```

### 4. 安装编译工具链
```bash
sudo apt-get update
sudo apt-get install -y build-essential ninja-build cmake git
conda run -n trellis2 pip install -U pip setuptools wheel
```

### 5. 编译 TRELLIS.2 扩展
```bash
cd /home/zhangxin/2026Projects/preStudy/modules/TRELLIS.2
conda activate trellis2

# 确保环境变量正确
which nvcc
nvcc -V
python -c "import torch; print(torch.version.cuda)"

# 逐个安装扩展
bash -lc ". ./setup.sh --flash-attn"
bash -lc ". ./setup.sh --nvdiffrast"
bash -lc ". ./setup.sh --nvdiffrec"
bash -lc ". ./setup.sh --cumesh"
bash -lc ". ./setup.sh --o-voxel"
bash -lc ". ./setup.sh --flexgemm"
```

## ⚠️ 关键注意事项

1. **nvcc 必须压过 /usr/bin/nvcc**
   - 安装完 CUDA 12.2 后，`which nvcc` 必须指向 `/usr/local/cuda-12.2/bin/nvcc`
   - 如果仍然是 `/usr/bin/nvcc`，说明 PATH 顺序不对

2. **编译链约束**
   - nvcc 12.2 ≥ PyTorch cu121 (12.1) ✅
   - 这样才能编译所有 CUDA 扩展

3. **使用 bash -lc 执行编译**
   - `-l` 参数强制加载 ~/.bashrc，确保 CUDA_HOME 等环境变量生效
   - 避免使用 `conda run` 导致环境变量丢失

## 🤔 需要决策

请选择以下方案之一继续：

1. **apt 安装 CUDA 12.2**（推荐，最简单）
2. **手动解压 runfile 安装**（需要额外步骤）
3. **使用 Docker**（最稳妥，环境隔离）

选择后我将继续执行相应步骤。
