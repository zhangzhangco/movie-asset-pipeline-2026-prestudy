
# 1. Create environment
conda create -n nvidia_opt python=3.10 -y

# 2. Activate (Note: in script using run_command we need to source activate)
source /home/zhangxin/miniconda3/bin/activate nvidia_opt

# 3. Install PyTorch 2.4.0 with CUDA 12.1
pip install torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cu121

# 4. Install build dependencies
pip install ninja setuptools wheel

# 5. Install gsplat from source
# We use the generic installer which should detect CUDA
pip install git+https://github.com/nerfstudio-project/gsplat.git

# 6. Install other utils
pip install imageio numpy plyfile scipy
