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
            asset_name = os.path.basename(relit_file)
            signals = item.get('signals', {})
            
            # --- Routing Logic ---
            asset_type = args.asset_type
            if asset_type == "auto":
                if signals.get('has_person'):
                    asset_type = "human"
                elif signals.get('area_ratio', 0) > 0.8:
                    asset_type = "scene"
                else:
                    asset_type = "prop"
                    
            backend = args.asset_gen_backend
            if backend == "auto":
                if asset_type == "prop":
                    backend = "trellis2" if signals.get('num_instances', 1) == 1 else "sam3d_objects"
                elif asset_type == "human":
                    backend = "sam3d_body"
                else:
                    backend = "trellis2"
                    
            print(f"   Processing Asset ID: {asset_id} | Type: {asset_type} | Backend: {backend}")
            
            # Record in global manifest
            asset_record = {
                "asset_id": asset_id,
                "asset_type": asset_type,
                "backend": backend,
                "status": "processing",
                "signals": signals,
                "artifacts": {
                    "source_image": relit_file
                }
            }
            manifest.add_asset(asset_record)
            
            # Run 3D Gen backend
            props_3d_dir = os.path.join(output_dir, "props_3d")
            success = False
            try:
                if backend == "trellis2":
                    success = runner.run(
                        f"Hero Asset Gen ({asset_id})",
                        "trellis2",
                        ["--input", relit_file, "--output", props_3d_dir],
                        ENVS["trellis2"],
                        extra_env={"PYTHONPATH": "modules/TRELLIS.2", "ATTN_BACKEND": "naive"},
                    )
                elif backend == "sam3d_objects":
                    success = runner.run(
                        f"Hero Asset Gen ({asset_id})",
                        "sam3d_objects",
                        ["--input", relit_file, "--output", props_3d_dir],
                        ENVS["sam3d_objects"],
                        extra_env={"PYTHONPATH": "modules/sam-3d-objects"},
                    )
                elif backend == "sam3d_body":
                    success = runner.run(
                        f"Hero Asset Gen ({asset_id})",
                        "sam3d_body",
                        ["--image", relit_file, "--output_dir", props_3d_dir],
                        ENVS["base"]
                    )
                else:
                    print(f"❌ Unknown asset_gen_backend: {backend}")
            except Exception as e:
                print(f"❌ Exception in backend {backend}: {e}")

            if not success:
                asset_record["status"] = "failed"
                asset_record["error"] = {"type": "BackendExecutionError", "message": f"{backend} failed to run"}
                manifest.save()
                continue
                
            # Run Export
            ply_name = os.path.splitext(os.path.basename(relit_file))[0] + ".ply"
            ply_path = os.path.join(props_3d_dir, ply_name)
            
            if os.path.exists(ply_path):
                asset_record["artifacts"]["raw_model"] = ply_path
                
                pkg_success = runner.run(
                    f"Standardization ({asset_id})", "package",
                    ["--input", ply_path, "--id", asset_id],
                    ENVS["base"]
                )
                         
                if pkg_success:
                    asset_record["status"] = "success"
                else:
                    asset_record["status"] = "failed"
                    asset_record["error"] = {"type": "PackagingError", "message": "Standardization failed"}
            
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
                        asset_record["import_valid"] = True
                        print(f"   ✅ Import Validation Passed.")
                    except subprocess.CalledProcessError as e:
                        asset_record["import_valid"] = False
                        print(f"   ❌ Import Validation Failed: {e.stderr.decode('utf-8')[:200]}")
                else:
                    print(f"   ⚠️ Blender not found in PATH, skipping import validation.")
                    asset_record["import_valid"] = "N/A"
            else:
                 if backend != "sam3d_body":
                     asset_record["status"] = "failed"
                     asset_record["error"] = {"type": "OutputMissingError", "message": f"Expected 3D model not found at {ply_path}"}
                 else:
                     asset_record["status"] = "success"

            manifest.save()
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
