import os
import argparse
import subprocess
import sys
import glob
import shutil
import json

from src.core.runner_utils import StepRunner, ManifestManager

# Configuration: Conda Environment Paths
CONDA_ROOT = "/home/zhangxin/miniconda3"
ENVS = {
    "sharp": f"{CONDA_ROOT}/envs/sharp/bin/python",
    "dust3r": f"{CONDA_ROOT}/envs/dust3r/bin/python",
    "trellis2": f"{CONDA_ROOT}/envs/trellis2/bin/python",
    # Meta SAM 3D Objects (see modules/sam-3d-objects/doc/setup.md)
    "sam3d_objects": f"{CONDA_ROOT}/envs/sam3d-objects/bin/python",
    "base": sys.executable,
}

# Define Script Paths (Absolute)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = {
    "scene_gen": os.path.join(PROJECT_ROOT, "src/steps/scene_gen/run_sharp.py"),
    "geometry": os.path.join(PROJECT_ROOT, "src/steps/geometry/run_dust3r_tiled.py"),
    "lighting": os.path.join(PROJECT_ROOT, "src/steps/lighting/estimate_lighting.py"),
    "harvest": os.path.join(PROJECT_ROOT, "src/steps/assets/harvest_hero_assets.py"),
    "trellis2": os.path.join(PROJECT_ROOT, "src/steps/assets/run_trellis2_local.py"),
    "sam3d_objects": os.path.join(PROJECT_ROOT, "src/steps/assets/run_sam3d_objects_local.py"),
    "sam3d_body": os.path.join(PROJECT_ROOT, "src/steps/assets/run_sam3d_body_local.py"),
    "package": os.path.join(PROJECT_ROOT, "src/steps/export/package_asset_gbt.py"),
    "report": os.path.join(PROJECT_ROOT, "src/steps/report/generate_report.py"),
    "check_import": os.path.join(PROJECT_ROOT, "scripts/check_import.py"),
}


def _signals_incomplete(signals, required_keys):
    """Return True when any required signal is missing."""
    return any(signals.get(key) is None for key in required_keys)


def select_asset_type_and_backend(signals, forced_asset_type, forced_backend):
    """Select asset type and backend with forced-route priority and rule-table fallback."""
    signals = signals or {}

    # 1) 强制资产类型优先
    if forced_asset_type != "auto":
        asset_type = forced_asset_type
    else:
        # 2) 自动路由规则表（严格顺序）
        has_person = bool(signals.get("has_person", False))
        has_mask = bool(signals.get("has_mask", False))
        num_instances = signals.get("num_instances", 1)
        area_ratio = signals.get("area_ratio", 0)
        bg_score = signals.get("bg_score")

        if has_person:
            asset_type = "human"
        elif has_mask or num_instances > 1 or area_ratio <= 0.5:
            asset_type = "prop"
        elif num_instances == 1 and area_ratio > 0.5 and bg_score == "low":
            asset_type = "prop"
        else:
            asset_type = "scene"

    # backend 选择
    signals_incomplete = False
    if forced_backend != "auto":
        backend_selected = forced_backend
    elif asset_type == "human":
        backend_selected = "sam3d_body"
    elif asset_type == "scene":
        backend_selected = "trellis2"
    else:
        prop_required = ["has_mask", "num_instances", "area_ratio", "bg_score"]
        signals_incomplete = _signals_incomplete(signals, prop_required)
        if forced_asset_type == "prop" and signals_incomplete:
            backend_selected = "trellis2"
        elif signals.get("num_instances", 1) > 1 or signals.get("area_ratio", 0) <= 0.5:
            backend_selected = "sam3d_objects"
        else:
            backend_selected = "trellis2"

    return asset_type, backend_selected, signals_incomplete

def main():
    parser = argparse.ArgumentParser(description="Movie Asset Hybrid Pipeline Orchestrator")
    parser.add_argument("--input", required=True, help="Path to input image")
    parser.add_argument("--output_root", default="outputs/pipeline_demo", help="Root output directory")
    parser.add_argument("--skip_scene", action="store_true", help="Skip expensive scene generation")
    parser.add_argument(
        "--asset_gen_backend",
        choices=["trellis2", "sam3d_objects", "sam3d_body", "auto"],
        default="auto",
        help="3D asset generation backend for props (default: auto)",
    )
    parser.add_argument(
        "--asset_type",
        choices=["prop", "human", "scene", "auto"],
        default="auto",
        help="Override asset type classification",
    )
    parser.add_argument("--skip_geometry", action="store_true", help="Skip DUSt3R geometry reconstruction")
    parser.add_argument("--roi_hint", type=str, default=None, help="Hint bounding box for prop extraction, format 'x,y,w,h'")
    parser.add_argument("--disable_skin_rejection", action="store_true", help="Disable the skin color rejection mechanism")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f"Error: Input file {input_path} not found.")
        return

    session_id = os.path.splitext(os.path.basename(input_path))[0]
    output_dir = os.path.join(args.output_root, session_id)
    os.makedirs(output_dir, exist_ok=True)
    
    # 0. Initialize Global Manifest & Step Runner
    runner = StepRunner(SCRIPTS)
    manifest = ManifestManager(
        path=os.path.join(output_dir, "manifest.json"),
        session_id=session_id,
        input_path=input_path,
        sys_argv=sys.argv
    )
            
    print(f"🎬 Starting Pipeline for Asset: {session_id}")
    print(f"📂 Output Directory: {output_dir}")

    # 1. Scene Gen
    if not args.skip_scene:
        runner.run("Scene Generation (ml-sharp)", "scene_gen", 
                   ["--input-path", input_path, "--output-path", os.path.join(output_dir, "scene_visual")],
                   ENVS["sharp"], 
                   extra_env={"PYTHONPATH": "modules/ml-sharp/src"})
    else:
        print("⏭️ Skipping Scene Generation")

    # 2. Geometry
    if not args.skip_geometry and not args.skip_scene: # Added condition based on CLI arg semantics
        runner.run("Geometry Reconstruction (DUSt3R)", "geometry",
                   ["--input", input_path, "--output", os.path.join(output_dir, "dust3r")],
                   ENVS["dust3r"],
                   extra_env={"PYTHONPATH": "modules/dust3r"})
    else:
        print("⏭️ Skipping Geometry")

    # 3. Lighting
    scene_visual_dir = os.path.join(output_dir, "scene_visual")
    potential_plys = glob.glob(os.path.join(scene_visual_dir, "**", "*.ply"), recursive=True)
    potential_ply = potential_plys[0] if potential_plys else None
    
    lighting_json = os.path.join(output_dir, "lighting_probe.json")
    if potential_ply:
        runner.run("Lighting Estimation", "lighting",
                   ["--input", potential_ply, "--output", lighting_json],
                   ENVS["base"])
    else:
        print(f"⚠️ No scene PLY found for lighting, using default.")
        with open(lighting_json, 'w') as f:
            json.dump({"ambient_light": {"r":1.0, "g":1.0, "b":1.0}}, f)

    # 4. Harvesting
    harvest_args = [
        "--input", input_path,
        "--output_dir", os.path.join(output_dir, "props"),
        "--lighting_probe", lighting_json
    ]
    if args.roi_hint:
        harvest_args.extend(["--roi_hint", args.roi_hint])
    if args.disable_skin_rejection:
        harvest_args.append("--disable_skin_rejection")

    runner.run("Asset Extraction & Relighting", "harvest", harvest_args, ENVS["base"])

    # 5. Iterating Asset Manifest and Routing
    prop_dir = os.path.join(output_dir, "props")
    harvest_manifest_path = os.path.join(prop_dir, "harvest_manifest.json")
    
    if os.path.exists(harvest_manifest_path):
        with open(harvest_manifest_path, 'r') as f:
            harvest_manifest = json.load(f)
            
        print(f"🧩 Found {len(harvest_manifest)} props in manifest.")
        
        for item in harvest_manifest:
            asset_id = item['id']
            relit_file = item['path'] # Absolute path from harvester
            signals = item.get('signals', {})
            
            asset_type, backend_selected, signals_incomplete = select_asset_type_and_backend(
                signals=signals,
                forced_asset_type=args.asset_type,
                forced_backend=args.asset_gen_backend,
            )
                    
            print(f"   Processing Asset ID: {asset_id} | Type: {asset_type} | Backend: {backend_selected}")
            
            parameters_snapshot = {
                "asset_gen_backend": args.asset_gen_backend,
                "asset_type": args.asset_type,
                "skip_scene": args.skip_scene,
                "skip_geometry": args.skip_geometry,
                "roi_hint": args.roi_hint,
                "disable_skin_rejection": args.disable_skin_rejection,
                "source_image": relit_file,
                "signals_incomplete": args.asset_type == "prop" and signals_incomplete,
            }
            manifest.record_asset_start(
                asset_id=asset_id,
                asset_type=asset_type,
                backend_selected=backend_selected,
                signals=signals,
                parameters_snapshot=parameters_snapshot,
            )
            
            # Run 3D Gen backend
            props_3d_dir = os.path.join(output_dir, "props_3d")
            success = False
            try:
                if backend_selected == "trellis2":
                    success = runner.run(
                        f"Hero Asset Gen ({asset_id})",
                        "trellis2",
                        ["--input", relit_file, "--output", props_3d_dir],
                        ENVS["trellis2"],
                        extra_env={"PYTHONPATH": "modules/TRELLIS.2", "ATTN_BACKEND": "naive"},
                    )
                elif backend_selected == "sam3d_objects":
                    success = runner.run(
                        f"Hero Asset Gen ({asset_id})",
                        "sam3d_objects",
                        ["--input", relit_file, "--output", props_3d_dir],
                        ENVS["sam3d_objects"],
                        extra_env={"PYTHONPATH": "modules/sam-3d-objects"},
                    )
                elif backend_selected == "sam3d_body":
                    success = runner.run(
                        f"Hero Asset Gen ({asset_id})",
                        "sam3d_body",
                        ["--image", relit_file, "--output_dir", props_3d_dir],
                        ENVS["base"]
                    )
                else:
                    print(f"❌ Unknown asset_gen_backend: {backend_selected}")
            except Exception as e:
                print(f"❌ Exception in backend {backend_selected}: {e}")

            if not success:
                manifest.record_asset_failure(
                    asset_id=asset_id,
                    error_type="BackendExecutionError",
                    message=f"{backend_selected} failed to run",
                    log_path=None,
                    outputs=[relit_file],
                )
                continue
                
            # Run Export
            ply_name = os.path.splitext(os.path.basename(relit_file))[0] + ".ply"
            ply_path = os.path.join(props_3d_dir, ply_name)
            
            run_log_paths = []
            outputs = [relit_file]
            if os.path.exists(ply_path):
                outputs.append(ply_path)

                pkg_success = runner.run(
                    f"Standardization ({asset_id})", "package",
                    ["--input", ply_path, "--id", asset_id],
                    ENVS["base"]
                )

                # Check Import (Blender Headless)
                blender_cmd = shutil.which("blender")
                if blender_cmd:
                    print(f"   Testing DCC Compatibility for {asset_id}...")
                    try:
                        subprocess.run(
                            [blender_cmd, "-b", "-P", SCRIPTS["check_import"], "--", ply_path],
                            check=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        print(f"   ✅ Import Validation Passed.")
                    except subprocess.CalledProcessError as e:
                        print(f"   ❌ Import Validation Failed: {e.stderr.decode('utf-8')[:200]}")
                else:
                    print(f"   ⚠️ Blender not found in PATH, skipping import validation.")

                if pkg_success:
                    manifest.record_asset_success(
                        asset_id=asset_id,
                        outputs=outputs,
                        run_log_paths=run_log_paths,
                    )
                else:
                    manifest.record_asset_failure(
                        asset_id=asset_id,
                        error_type="PackagingError",
                        message="Standardization failed",
                        log_path=None,
                        outputs=outputs,
                    )
            else:
                if backend_selected != "sam3d_body":
                    manifest.record_asset_failure(
                        asset_id=asset_id,
                        error_type="OutputMissingError",
                        message=f"Expected 3D model not found at {ply_path}",
                        log_path=None,
                        outputs=outputs,
                    )
                else:
                    manifest.record_asset_success(
                        asset_id=asset_id,
                        outputs=outputs,
                        run_log_paths=run_log_paths,
                    )
    else:
        print("❌ No harvest manifest found. Skipping Generation.")
        
    # 6. Report
    manifest.save()
    runner.run(
        "Report Generation", "report",
        ["--output_root", output_dir, "--input_image", input_path],
        ENVS["base"]
    )
             
    print(f"\n🔗 Report available at: {os.path.join(output_dir, 'report.html')}")

if __name__ == "__main__":
    main()
