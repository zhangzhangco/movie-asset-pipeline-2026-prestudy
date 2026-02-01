
import json
import os

model_dir = os.path.abspath("models/TRELLIS-image-large")
json_path = os.path.join(model_dir, "pipeline.json")

if not os.path.exists(json_path):
    print("pipeline.json not found!")
    exit(1)

with open(json_path, 'r') as f:
    data = json.load(f)

print("Patching pipeline.json...")
models = data['args']['models']
changed = False
for key, val in models.items():
    if isinstance(val, str) and val.startswith("ckpts/"):
        # Convert to absolute path
        abs_path = os.path.join(model_dir, val)
        models[key] = abs_path
        print(f"Updated {key} -> {abs_path}")
        changed = True

if changed:
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=4)
    print("Saved patched config.")
else:
    print("No changes needed.")
