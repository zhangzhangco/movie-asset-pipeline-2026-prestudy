
from huggingface_hub import snapshot_download
import os

os.makedirs("models", exist_ok=True)
print("Downloading TRELLIS.2 model to models/TRELLIS.2-4B...")
snapshot_download(repo_id="microsoft/TRELLIS.2-4B", local_dir="models/TRELLIS.2-4B")
print("Download complete.")
