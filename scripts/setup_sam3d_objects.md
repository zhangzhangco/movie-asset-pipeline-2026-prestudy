# Setup: SAM 3D Objects (facebookresearch/sam-3d-objects)

This project integrates SAM 3D Objects as an optional prop 3D generation backend.

Repo is vendored at:
- `modules/sam-3d-objects`

## 1) Create conda env

Follow upstream instructions (recommended):
- `modules/sam-3d-objects/doc/setup.md` (raw: https://raw.githubusercontent.com/facebookresearch/sam-3d-objects/main/doc/setup.md)

Expected env name used by `pipeline_runner.py`:
- `sam3d-objects`

**⚠️ 环境配置核心要点 (CRITICAL Requirements):**
- Python 3.11.0
- PyTorch 2.5.1 + CUDA 12.1
- Kaolin 0.17.0 (必须与 PyTorch/CUDA 版本对应匹配)
- PyTorch3D 0.7.8
- `utils3d == 0.0.2` (**致命陷阱**: 必须来自 MoGe 依赖包的 0.0.2 版本，**绝对不要**安装 PyPI 上其他同名包或 GitHub 的 v1.6)
- 硬件要求：至少需要 32GB+ 显存的 GPU (推荐 RTX A6000 48GB 等级别)



## 2) Download checkpoints (HuggingFace gated)

Upstream requires access to:
- https://huggingface.co/facebook/sam-3d-objects

Once approved:

```bash
cd modules/sam-3d-objects
pip install 'huggingface-hub[cli]<1.0'
hf auth login

TAG=hf
hf download \
  --repo-type model \
  --local-dir checkpoints/${TAG}-download \
  --max-workers 1 \
  facebook/sam-3d-objects
mv checkpoints/${TAG}-download/checkpoints checkpoints/${TAG}
rm -rf checkpoints/${TAG}-download
```

This should create:
- `modules/sam-3d-objects/checkpoints/hf/pipeline.yaml`

## 3) Run just the step

```bash
/home/zhangxin/miniconda3/envs/sam3d-objects/bin/python \
  src/steps/assets/run_sam3d_objects_local.py \
  --input <path/to/rgba_or_rgb.png> \
  --output outputs/sam3d_objects_test
```

## 4) Run full pipeline with SAM3D

```bash
python pipeline_runner.py --input <image.png> --asset_gen_backend sam3d_objects
```

Notes:
- If your prop crops are RGBA, the alpha channel is used as the object mask.
- If crops are RGB, the current integration uses a full-foreground mask (works best when the crop is already tight).
