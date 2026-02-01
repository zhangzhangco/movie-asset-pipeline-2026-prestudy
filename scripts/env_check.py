
import sys
import importlib.util
from typing import Tuple, List

try:
    import torch
except ImportError:
    torch = None

def check_torch_cuda() -> Tuple[bool, List[str]]:
    messages = []
    
    if torch is None:
        messages.append("Torch installed: NO")
        return False, messages
    
    messages.append(f"Torch version: {torch.__version__}")
    
    if not torch.cuda.is_available():
        messages.append("CUDA available: NO")
        return False, messages

    messages.append(f"CUDA version: {torch.version.cuda}")
    
    try:
        props = torch.cuda.get_device_properties(0)
        vram_gb = props.total_memory / (1024**3)
        messages.append(f"GPU[0]: {props.name}")
        messages.append(f"GPU VRAM: {vram_gb:.2f} GB")
    except Exception as exc:
        messages.append(f"GPU properties: FAIL ({exc})")
        return False, messages

    return True, messages


def check_diff_gaussian_rasterization() -> Tuple[bool, str]:
    # We first try to import it directly.
    # Note: 'diff_gaussian_rasterization' often needs to be installed via pip install .
    # or available in PYTHONPATH. If it's just a submodule folder but not installed/compiled,
    # this might fail or require sys.path manipulation.
    try:
        # Assuming the user has compiled it or it is in python path
        # If it is in src/diff_gaussian_rasterization, we might need to add src to path
        # But usually gaussian rasterization is installed as a package.
        import diff_gaussian_rasterization
        return True, "diff_gaussian_rasterization import: OK"
    except ImportError as exc:
        return False, f"diff_gaussian_rasterization import: FAIL ({exc})"
    except Exception as exc:
        return False, f"diff_gaussian_rasterization import: FAIL ({exc})"


def main() -> int:
    ok = True
    details: List[str] = []

    # 1. Check Torch & CUDA
    torch_ok, torch_details = check_torch_cuda()
    details.extend(torch_details)
    ok = ok and torch_ok

    # 2. Add 'src' to sys.path just in case, though usually rasterizer is a compiled lib
    sys.path.append('src')
    
    # 3. Check Rasterizer
    dgr_ok, dgr_msg = check_diff_gaussian_rasterization()
    details.append(dgr_msg)
    # Don't fail hard on DGR yet, as user might not have compiled it
    if not dgr_ok:
         ok = False

    print("=== 3DGS Environment Check ===")
    for line in details:
        print(f"- {line}")
    print()
    
    if ok:
        print("RESULT: OK")
        return 0
    else:
        print("RESULT: FAIL (See above)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
