import os
import subprocess
import time
import json
import sys

class StepRunner:
    """Helper class for orchestrating external scripts across different conda environments."""
    
    def __init__(self, scripts_dict):
        self.scripts = scripts_dict
        
    def run(self, name, script_key, args, env_python, extra_env=None):
        script_path = self.scripts.get(script_key)
        if not script_path or not os.path.exists(script_path):
            print(f"⚠️ Script for '{name}' not found at {script_path}, skipping.")
            return False
            
        print(f"\n========================================")
        print(f"🚀 PIPELINE STEP: {name}")
        print(f"========================================")
        
        full_cmd = [env_python, script_path] + args
        cmd_str = " ".join(full_cmd)
        print(f"Executing: {cmd_str}")
        
        # Prepare Environment
        env = os.environ.copy()
        if extra_env:
            for k, v in extra_env.items():
                if k == "PYTHONPATH" and "PYTHONPATH" in env:
                    env[k] = v + os.pathsep + env[k]
                else:
                    env[k] = v
        
        start_time = time.time()
        try:
            subprocess.check_call(full_cmd, env=env)
            elapsed = time.time() - start_time
            print(f"✅ Step '{name}' completed in {elapsed:.2f}s")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Step '{name}' failed with exit code {e.returncode}")
            return False
        except Exception as e:
            print(f"❌ Step '{name}' failed: {e}")
            return False


class ManifestManager:
    """Manages reading, writing, and structuring the global JSON manifest."""
    
    def __init__(self, path, session_id, input_path, sys_argv, version="1.3.1"):
        self.path = path
        self.data = {
            "session_id": session_id,
            "inputs": {
                "image": input_path
            },
            "meta": {
                "pipeline_version": version,
                "command": " ".join(sys_argv)
            },
            "assets": []
        }
        self.save()
    
    def add_asset(self, asset_record):
        """Append an asset record to the manifest."""
        self.data["assets"].append(asset_record)
        self.save()
        
    def get_assets(self):
        """Retrieve the current list of assets."""
        return self.data["assets"]
        
    def save(self):
        """Persist the current state to disk."""
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
