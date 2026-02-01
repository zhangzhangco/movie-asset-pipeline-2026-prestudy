
from huggingface_hub import snapshot_download
import os

os.makedirs("models", exist_ok=True)
print("Downloading TRELLIS model to models/TRELLIS-image-large...")
snapshot_download(repo_id="microsoft/TRELLIS-image-large", local_dir="models/TRELLIS-image-large")
print("Download complete.")
