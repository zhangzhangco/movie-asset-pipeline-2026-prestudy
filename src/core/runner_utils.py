"""
管线运行通用工具库
Author: zhangxin
功能：包含 SHA-256 计算、Git 提交记录提取、Python 运行时信息收集以及 Manifest 清单管理类。
输入：文件路径、资产 ID、运行状态信息。
输出：更新后的 JSON 清单文件及运行环境摘要。
依赖：Python 标准库、PyTorch（可选，用于版本检测）。
"""
import os
import subprocess
import time
import json
import sys
import hashlib
import platform
from dataclasses import dataclass
from configparser import ConfigParser
from importlib import metadata


def _compute_sha256(file_path):
    if not file_path or not os.path.exists(file_path) or not os.path.isfile(file_path):
        return None

    hasher = hashlib.sha256()
    with open(file_path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _get_git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None


def _get_package_version(package_name="movie_asset_3dgs"):
    try:
        return metadata.version(package_name)
    except Exception:
        pass

    setup_cfg_path = os.path.join(os.path.dirname(__file__), "..", "..", "setup.cfg")
    setup_cfg_path = os.path.abspath(setup_cfg_path)
    if not os.path.exists(setup_cfg_path):
        return "unknown"

    parser = ConfigParser()
    parser.read(setup_cfg_path)
    return parser.get("metadata", "version", fallback="unknown")


def _get_runtime_info():
    runtime = {
        "python": platform.python_version(),
        "torch": "not_installed",
        "cuda": "not_available",
    }
    try:
        import torch

        runtime["torch"] = getattr(torch, "__version__", "unknown")
        cuda_version = getattr(torch.version, "cuda", None)
        if cuda_version:
            runtime["cuda"] = cuda_version
    except Exception:
        pass
    return runtime

@dataclass
class StepRunResult:
    success: bool
    returncode: int
    stdout_log: str = None
    stderr_log: str = None
    duration_s: float = 0.0


class StepRunner:
    """Helper class for orchestrating external scripts across different conda environments."""

    def __init__(self, scripts_dict):
        self.scripts = scripts_dict
        
    def run(self, name, script_key, args, env_python, extra_env=None, log_dir=None, step_id=None, asset_id=None):
        script_path = self.scripts.get(script_key)
        if not script_path or not os.path.exists(script_path):
            print(f"⚠️ Script for '{name}' not found at {script_path}, skipping.")
            return StepRunResult(success=False, returncode=-1)
            
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

        stdout_log = None
        stderr_log = None
        stdout_stream = None
        stderr_stream = None
        if log_dir and step_id and asset_id:
            asset_log_dir = os.path.join(log_dir, asset_id)
            os.makedirs(asset_log_dir, exist_ok=True)
            stdout_log = os.path.join(asset_log_dir, f"{step_id}.stdout.log")
            stderr_log = os.path.join(asset_log_dir, f"{step_id}.stderr.log")
            stdout_stream = open(stdout_log, "w", encoding="utf-8")
            stderr_stream = open(stderr_log, "w", encoding="utf-8")

        try:
            completed = subprocess.run(
                full_cmd,
                env=env,
                stdout=stdout_stream,
                stderr=stderr_stream,
                check=False,
            )
            elapsed = time.time() - start_time
            if completed.returncode == 0:
                print(f"✅ Step '{name}' completed in {elapsed:.2f}s")
            else:
                print(f"❌ Step '{name}' failed with exit code {completed.returncode}")
            return StepRunResult(
                success=completed.returncode == 0,
                returncode=completed.returncode,
                stdout_log=stdout_log,
                stderr_log=stderr_log,
                duration_s=elapsed,
            )
        except Exception as e:
            print(f"❌ Step '{name}' failed: {e}")
            return StepRunResult(
                success=False,
                returncode=-1,
                stdout_log=stdout_log,
                stderr_log=stderr_log,
                duration_s=time.time() - start_time,
            )
        finally:
            if stdout_stream:
                stdout_stream.close()
            if stderr_stream:
                stderr_stream.close()


class ManifestManager:
    """Manages reading, writing, and structuring the global JSON manifest."""
    
    def __init__(self, path, session_id, input_path, sys_argv, version="1.3.1"):
        input_files = [input_path]
        sha256_map = {
            file_path: digest
            for file_path in input_files
            if (digest := _compute_sha256(file_path)) is not None
        }

        pipeline_commit = _get_git_commit() or _get_package_version()
        self.path = path
        self.data = {
            "session_id": session_id,
            "inputs": {
                "files": input_files,
                "sha256_map": sha256_map,
            },
            "versions": {
                "pipeline_commit": pipeline_commit,
                "runtime": _get_runtime_info(),
            },
            "reproduce": {
                "command": " ".join(sys_argv),
            },
            "assets": []
        }
        self.save()
    
    def add_asset(self, asset_record):
        """Append an asset record to the manifest."""
        self.data["assets"].append(asset_record)
        self.save()

    def _find_asset(self, asset_id):
        for asset in self.data["assets"]:
            if asset.get("asset_id") == asset_id:
                return asset
        return None

    def record_asset_start(self, asset_id, asset_type, backend_selected, signals, parameters_snapshot):
        asset_record = {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "backend_selected": backend_selected,
            "status": "processing",
            "signals": signals or {},
            "parameters_snapshot": parameters_snapshot or {},
            "outputs": [],
            "error": None,
            "run_log_paths": [],
        }
        existing = self._find_asset(asset_id)
        if existing is None:
            self.data["assets"].append(asset_record)
        else:
            existing.update(asset_record)
        self.save()

    def record_asset_success(self, asset_id, outputs, run_log_paths):
        asset = self._find_asset(asset_id)
        if asset is None:
            raise KeyError(f"Asset '{asset_id}' not found when marking success.")

        asset["status"] = "success"
        asset["outputs"] = outputs or []
        asset["error"] = None
        asset["run_log_paths"] = run_log_paths or []
        self.save()

    def append_asset_run_logs(self, asset_id, run_log_paths):
        asset = self._find_asset(asset_id)
        if asset is None:
            raise KeyError(f"Asset '{asset_id}' not found when appending logs.")

        existing = asset.get("run_log_paths") or []
        for path in run_log_paths or []:
            if path and path not in existing:
                existing.append(path)
        asset["run_log_paths"] = existing
        self.save()

    def get_asset_run_logs(self, asset_id):
        asset = self._find_asset(asset_id)
        if asset is None:
            return []
        return asset.get("run_log_paths") or []

    def record_asset_failure(self, asset_id, error_type, message, log_path, outputs=[]):
        asset = self._find_asset(asset_id)
        if asset is None:
            raise KeyError(f"Asset '{asset_id}' not found when marking failure.")

        asset["status"] = "failed"
        asset["outputs"] = outputs or []
        asset["error"] = {
            "type": error_type,
            "message": message,
            "log_path": log_path,
        }
        existing = asset.get("run_log_paths") or []
        if log_path and log_path not in existing:
            existing.append(log_path)
        asset["run_log_paths"] = existing
        self.save()

    def update_asset_fields(self, asset_id, updates):
        asset = self._find_asset(asset_id)
        if asset is None:
            raise KeyError(f"Asset '{asset_id}' not found when updating fields.")

        asset.update(updates or {})
        self.save()
        
    def get_assets(self):
        """Retrieve the current list of assets."""
        return self.data["assets"]
        
    def save(self):
        """Persist the current state to disk."""
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
