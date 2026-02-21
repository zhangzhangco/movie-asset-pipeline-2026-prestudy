# TRELLIS.2 安装问题报告

## 📋 硬约束核对结果（5 条关键命令）

```bash
which nvcc                    # /usr/bin/nvcc
nvcc -V                       # CUDA 11.5.119
python -c "import torch..."   # PyTorch: 2.1.2+cu118, CUDA: 11.8
echo $CUDA_HOME               # (空，未设置)
dpkg -l | grep cuda           # 只有 CUDA 11.5 runtime 库，无完整 Toolkit
ls /usr/local/cuda*           # 不存在
```

### 当前环境信息
```
GPU 驱动: NVIDIA-SMI 535.288.01 (驱动能力上限 CUDA 12.2)
编译器 nvcc: 11.5.119 (通过 Ubuntu 包管理器安装的残缺版本)
conda 环境: trellis2 (Python 3.10)
PyTorch: 2.1.2+cu118 (torch.version.cuda = 11.8)
CUDA Toolkit: 无完整安装（/usr/local/ 下不存在）
```

### 已完成部分
- ✅ TRELLIS.2 代码已克隆到 `modules/TRELLIS.2/`
- ✅ conda 环境 `trellis2` 已创建（Python 3.10）
- ✅ 基础依赖已安装：transformers, gradio, utils3d 等
- ✅ PyTorch 2.1.2+cu118 已安装
- ✅ NumPy 已降级到 1.26.4（修复兼容性问题）

## ❌ 核心问题（关键纠错）

### 问题本质
**不是 PyTorch 版本选择问题，而是"编译期 nvcc(CUDA Toolkit) 版本"与"PyTorch wheel 自带的 CUDA 版本"不一致**

### 关键纠错两点

1. **`nvidia-smi` 显示的 "CUDA Version: 12.2" 只是驱动能力上限**
   - 不是机器上可用于编译的 `nvcc` 版本
   - 真正的编译器版本看 `nvcc -V`，目前是 **11.5**
   - 参考：[Ask Ubuntu - CUDA version mismatch](https://askubuntu.com/questions/1519114/mismatched-versions-between-nvcc-11-5-vs-nvidia-smi-12-2-on-ubuntu)

2. **cu118 对应的是 CUDA 11.8，不是 11.5**
   - 当前 PyTorch 2.1.2+cu118 的 `torch.version.cuda = 11.8`
   - 机器 `nvcc` 版本是 **11.5（更低）**
   - 扩展编译会检查 `nvcc` vs `torch.version.cuda`，不一致就报错
   - 参考：[GitHub - vllm CUDA mismatch issue](https://github.com/vllm-project/vllm/issues/1453)

### 具体失败原因

#### 问题 1: flash-attention 安装失败
```
RuntimeError: FlashAttention is only supported on CUDA 11.7 and above.
```
- **根因**: `nvcc 11.5` 低于最低要求 11.7
- **门槛**: flash-attn 2.7.3 硬性要求 CUDA ≥ 11.7
- 参考：[PyPI - flash-attn](https://pypi.org/project/flash-attn/)

#### 问题 2: nvdiffrast 安装失败
```
RuntimeError: The detected CUDA version (11.5) mismatches the version 
that was used to compile PyTorch (11.8).
```
- **根因**: 典型的 `torch.version.cuda` (11.8) 与 `nvcc` (11.5) 不一致
- **编译期检查**: PyTorch 扩展编译时会强制校验版本匹配
- 参考：[GitHub - vllm CUDA mismatch](https://github.com/vllm-project/vllm/issues/1453)

#### 问题 3: TRELLIS.2 官方要求
- 推荐 CUDA Toolkit **12.4**
- 默认使用 PyTorch 2.6.0 + CUDA 12.4
- 需要编译的扩展：flash-attn, nvdiffrast, nvdiffrec, cumesh, o-voxel, flexgemm
- 参考：[TRELLIS.2 setup.sh](https://github.com/microsoft/TRELLIS.2/blob/main/setup.sh)

## 🔍 技术分析

### 编译链约束规则
**`nvcc` 主版本/小版本 要 ≥ `torch.version.cuda`**（至少同一大版本，且不要比它低）

### CUDA 版本兼容性矩阵
| 组件 | 要求 CUDA 版本 | 当前 nvcc | 当前 PyTorch | 状态 |
|------|---------------|----------|-------------|------|
| flash-attention 2.7.3 | ≥ 11.7 | 11.5 | 11.8 | ❌ nvcc 过低 |
| nvdiffrast | nvcc ≥ torch.cuda | 11.5 | 11.8 | ❌ 11.5 < 11.8 |
| TRELLIS.2 官方推荐 | 12.4 | 11.5 | 11.8 | ❌ 严重不匹配 |
| GPU 驱动能力上限 | - | - | - | ✅ 支持到 12.2 |

### 根本原因
1. **系统没有完整的 CUDA Toolkit**（`/usr/local/cuda*` 不存在）
2. **只有通过 Ubuntu 包管理器安装的 nvcc 11.5**（残缺版本）
3. **nvcc 11.5 < PyTorch cu118 (11.8)**，无法编译任何 CUDA 扩展
4. **驱动虽然支持 12.2，但编译链卡在 11.5**

## 💡 解决方案（按"最少折腾→最贴近官方"排序）

### 路线 1: 安装 CUDA Toolkit 12.2 + PyTorch cu121（推荐，最少折腾）

**为什么选 12.2？**
- 你的驱动 535 显示能力上限是 12.2，走 12.2 最顺
- 不需要升级驱动（12.4 通常需要更高版本驱动，如 550+）
- 让编译链先跑起来，再考虑是否追官方 12.4

**操作步骤**:

1. **安装 CUDA Toolkit 12.2**（含完整 nvcc 编译链）
   ```bash
   # 下载 CUDA 12.2 runfile installer
   wget https://developer.download.nvidia.com/compute/cuda/12.2.0/local_installers/cuda_12.2.0_535.54.03_linux.run
   
   # 安装（只装 toolkit，不装驱动）
   sudo sh cuda_12.2.0_535.54.03_linux.run --toolkit --silent --override
   ```

2. **设置环境变量**（永久生效，写入 ~/.bashrc）
   ```bash
   echo 'export CUDA_HOME=/usr/local/cuda-12.2' >> ~/.bashrc
   echo 'export PATH=$CUDA_HOME/bin:$PATH' >> ~/.bashrc
   echo 'export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
   source ~/.bashrc
   
   # 验证
   nvcc -V  # 应该显示 12.2
   ```

3. **重新安装 PyTorch cu121**（匹配 nvcc 12.2）
   ```bash
   conda activate trellis2
   pip uninstall torch torchvision -y
   pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
   
   # 验证
   python -c "import torch; print('PyTorch:', torch.__version__, 'CUDA:', torch.version.cuda)"
   # 应该显示: PyTorch: 2.5.1+cu121 CUDA: 12.1
   ```

4. **手动安装 TRELLIS.2 扩展**（不用 --new-env，避免脚本强制装 cu124）
   ```bash
   cd /home/zhangxin/2026Projects/preStudy/modules/TRELLIS.2
   
   # 按顺序安装各扩展
   conda run -n trellis2 bash -c '. ./setup.sh --flash-attn'
   conda run -n trellis2 bash -c '. ./setup.sh --nvdiffrast'
   conda run -n trellis2 bash -c '. ./setup.sh --nvdiffrec'
   conda run -n trellis2 bash -c '. ./setup.sh --cumesh'
   conda run -n trellis2 bash -c '. ./setup.sh --o-voxel'
   conda run -n trellis2 bash -c '. ./setup.sh --flexgemm'
   ```

**优点**: 
- 符合你当前驱动能力（535 → 12.2）
- 不需要升级驱动
- 编译链完整，可以编译所有扩展
- 长期稳定

**缺点**: 
- 需要 root 权限安装 CUDA Toolkit
- 可能影响系统其他 CUDA 项目（可通过 CUDA_HOME 切换）

**关键注意事项**:
- 12.4 不只是"装 toolkit"，它和驱动分支的关系要一起算
- 你的驱动 535 对应 CUDA 12.2，直接上 12.4 可能需要 forward-compat 包兜底
- 参考：[NVIDIA CUDA Compatibility](https://docs.nvidia.com/deploy/pdf/CUDA_Compatibility.pdf)

---

### 路线 2: 跟官方默认 CUDA 12.4 全套（需要升级驱动）

**适用场景**: 有 root 权限，且能升级驱动到 550+ 分支

**操作步骤**:

1. **升级 NVIDIA 驱动到 550+ 分支**
   ```bash
   # Ubuntu 示例
   sudo ubuntu-drivers devices
   sudo ubuntu-drivers autoinstall
   # 或手动安装
   sudo apt install nvidia-driver-550
   sudo reboot
   ```

2. **安装 CUDA Toolkit 12.4**
   ```bash
   wget https://developer.download.nvidia.com/compute/cuda/12.4.0/local_installers/cuda_12.4.0_550.54.14_linux.run
   sudo sh cuda_12.4.0_550.54.14_linux.run --tt --silent --override
   
   export CUDA_HOME=/usr/local/cuda-12.4
   export PATH=$CUDA_HOME/bin:$PATH
   export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
   ```

3. **按官方脚本全套安装**
   ```bash
   cd modules/TRELLIS.2
   conda activate trellis2
   pip uninstall torch torchvision -y
   . ./setup.sh --basic --flash-attn --nvdiffrast --nvdiffrec --cumesh --o-voxel --flexgemm
   ```

**优点**: 
- 完全符合官方推荐
- 最新特性支持
- 省后患

**缺点**: 
- 需要升级驱动（可能影响系统稳定性）
- 需要 root 权限
- 折腾程度最高

---

### 路线 3: Docker 容器（环境隔离最强）

**适用场景**: 宿主机不方便改，或需要多版本 CUDA 共存

**关键点**: 必须用 `*-devel` 镜像（包含 nvcc 编译链），不是 runtime 镜像

**操作步骤**:

1. **启动 CUDA 12.2 devel 容器**
   ```bash
   docker run --gpus all -it --rm \
     --name trellis2_build \
     -v /home/zhangxin/2026Projects/preStudy:/workspace \
     nvidia/cuda:12.2.0-devel-ubuntu22.04 bash
   ```

2. **容器内安装 Miniconda + TRELLIS.2**
   ```bash
   # 安装 miniconda
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
   bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda
   export PATH=/opt/conda/bin:$PATH
   
   # 创建环境
   cd /workspace/modules/TRELLIS.2
   conda create -n trellis2 python=3.10 -y
   conda activate trellis2
   
   # 安装 PyTorch cu121
   pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
   
   # 安装扩展
   . ./setup.sh --basic --flash-attn --nvdiffrast --nvdiffrec --cumesh --o-voxel --flexgemm
   ```

3. **保存容器为镜像**（可选）
   ```bash
   # 在宿主机另一个终端
   docker commit trellis2_build trellis2:cu122
   ```

**优点**: 
- 环境完全隔离，不影响宿主机
- 可复现性强
- 可以尝试不同 CUDA 版本（12.2-devel / 12.4-devel）

**缺点**: 
- 需要学习 Docker 基础
- 文件权限管理需要注意（容器内 root vs 宿主机用户）
- 每次运行需要启动容器

**参考**: [NVIDIA CUDA Docker Hub](https://hub.docker.com/r/nvidia/cuda)

---

## 🤔 需要专家决策的问题

### 一句话版决策树

- **能动宿主机（有 root）但不想升级驱动** → **路线 1**（CUDA 12.2 + cu121）
- **能升级驱动** → **路线 2**（官方 cu124 全家桶）
- **宿主机不方便改** → **路线 3**（Docker 12.2-devel）

### 详细决策问题

1. **是否有 root 权限安装 CUDA Toolkit？**
   - ✅ 有 root，不想升级驱动 → **路线 1**（推荐，最少折腾）
   - ✅ 有 root，可以升级驱动 → **路线 2**（最贴近官方）
   - ❌ 没有 root → **路线 3**（Docker，必选）

2. **项目对 TRELLIS.2 的依赖程度？**
   - 核心依赖：必须完整安装，选路线 1/2/3
   - 可选功能：可以先跳过，使用现有的 **TRELLIS 1.0**（已安装在 `trellis` 环境）

3. **是否可以使用 Docker？**
   - ✅ 可以 → **路线 3** 最稳妥（环境隔离）
   - ❌ 不行 → 必须升级宿主机 CUDA（路线 1 或 2）

4. **时间紧急程度？**
   - 🔥 紧急：先用 **TRELLIS 1.0**，后续再升级
   - ⏰ 不紧急：按路线 1/2/3 完整安装

5. **驱动升级风险评估？**
   - 当前驱动 535 对应 CUDA 12.2 能力上限
   - 升级到 550+ 才能稳定支持 CUDA 12.4
   - 如果系统有其他关键应用依赖当前驱动，**不建议升级**（选路线 1 或 3）

## 📝 临时替代方案

在解决 TRELLIS.2 安装问题之前，可以：
1. 使用已安装的 **TRELLIS 1.0**（`conda activate trellis`）
2. 修改 `pipeline_runner.py` 中的 `--asset_gen_backend` 默认值为 `trellis`（而非 `trellis2`）
3. 继续开发和测试其他 pipeline 步骤

## 🔗 参考资料
- TRELLIS.2 官方文档: https://github.com/microsoft/TRELLIS.2
- CUDA Toolkit 下载: https://developer.nvidia.com/cuda-toolkit-archive
- PyTorch CUDA 兼容性: https://pytorch.org/get-started/previous-versions/
