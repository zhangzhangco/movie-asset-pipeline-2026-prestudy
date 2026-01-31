# Setup: SAM 3D Objects (facebookresearch/sam-3d-objects)

This project integrates SAM 3D Objects as an optional prop 3D generation backend.

Repo is vendored at:
- `modules/sam-3d-objects`

## 1) Create conda env

Follow upstream instructions (recommended):
- `modules/sam-3d-objects/doc/setup.md` (raw: https://raw.githubusercontent.com/facebookresearch/sam-3d-objects/main/doc/setup.md)

Expected env name used by `pipeline_runner.py`:
- `sam3d-objects`

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
