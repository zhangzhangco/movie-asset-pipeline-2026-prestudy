
import os
import argparse
import subprocess
import sys
import time
import json
import glob

# Configuration: Conda Environment Paths
CONDA_ROOT = "/home/zhangxin/miniconda3"
ENVS = {
    "sharp": f"{CONDA_ROOT}/envs/sharp/bin/python",
    "dust3r": f"{CONDA_ROOT}/envs/dust3r/bin/python",
    "trellis": f"{CONDA_ROOT}/envs/trellis/bin/python",
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
    "trellis": os.path.join(PROJECT_ROOT, "src/steps/assets/run_trellis_local.py"),
    "sam3d_objects": os.path.join(PROJECT_ROOT, "src/steps/assets/run_sam3d_objects_local.py"),
    "package": os.path.join(PROJECT_ROOT, "src/steps/export/package_asset_gbt.py"),
    "report": os.path.join(PROJECT_ROOT, "src/steps/report/generate_report.py"),
}

def run_step(name, script_key, args, env_python, extra_env=None):
    script_path = SCRIPTS.get(script_key)
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

def main():
    parser = argparse.ArgumentParser(description="Movie Asset Hybrid Pipeline Orchestrator")
    parser.add_argument("--input", required=True, help="Path to input image")
    parser.add_argument("--output_root", default="outputs/pipeline_demo", help="Root output directory")
    parser.add_argument("--skip_scene", action="store_true", help="Skip expensive scene generation")
    parser.add_argument(
        "--asset_gen_backend",
        choices=["trellis", "sam3d_objects"],
        default="trellis",
        help="3D asset generation backend for props (default: trellis)",
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
    
    print(f"🎬 Starting Pipeline for Asset: {session_id}")
    print(f"📂 Output Directory: {output_dir}")

    # 1. Scene Gen
    if not args.skip_scene:
        run_step("Scene Generation (ml-sharp)", "scene_gen", 
                 ["--input-path", input_path, "--output-path", os.path.join(output_dir, "scene_visual")],
                 ENVS["sharp"], 
                 extra_env={"PYTHONPATH": "modules/ml-sharp/src"})
    else:
        print("⏭️ Skipping Scene Generation")

    # 2. Geometry
    if not args.skip_scene:
        run_step("Geometry Reconstruction (DUSt3R)", "geometry",
                 ["--input", input_path, "--output", os.path.join(output_dir, "dust3r")],
                 ENVS["dust3r"],
                 extra_env={"PYTHONPATH": "modules/dust3r"})
    else:
        print("⏭️ Skipping Geometry")

    # 3. Lighting
    # (Assuming ml-sharp produces a ply with same name as input session_id in scene_visual dir)
    # Wait, run_sharp.py output logic might differ. It outputs `scene.ply` or similar?
    # Previous logs showed: "Saving 3DGS to .../scene_visual". Typically it saves as "iteration_x/point_cloud.ply".
    # For now, let's look for ANY ply in scene_visual.
    scene_visual_dir = os.path.join(output_dir, "scene_visual")
    potential_plys = glob.glob(os.path.join(scene_visual_dir, "**", "*.ply"), recursive=True)
    potential_ply = potential_plys[0] if potential_plys else None
    
    lighting_json = os.path.join(output_dir, "lighting_probe.json")
    if potential_ply:
        run_step("Lighting Estimation", "lighting",
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

    run_step("Asset Extraction & Relighting", "harvest",
             harvest_args,
             ENVS["base"])

    # 5. TRELLIS Gen (Iterate over all extracted props in Manifest)
    prop_dir = os.path.join(output_dir, "props")
    manifest_path = os.path.join(prop_dir, "harvest_manifest.json")
    
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            
        print(f"🧩 Found {len(manifest)} props in manifest.")
        
        for item in manifest:
            asset_id = item['id']
            relit_file = item['path'] # Absolute path from harvester
            asset_name = os.path.basename(relit_file)
            
            print(f"   Processing Asset ID: {asset_id}")
            
            # Run 3D Gen backend
            props_3d_dir = os.path.join(output_dir, "props_3d")
            if args.asset_gen_backend == "trellis":
                run_step(
                    f"Hero Asset Gen ({asset_id})",
                    "trellis",
                    ["--input", relit_file, "--output", props_3d_dir],
                    ENVS["trellis"],
                    extra_env={"PYTHONPATH": "modules/TRELLIS", "ATTN_BACKEND": "naive"},
                )
            elif args.asset_gen_backend == "sam3d_objects":
                run_step(
                    f"Hero Asset Gen ({asset_id})",
                    "sam3d_objects",
                    ["--input", relit_file, "--output", props_3d_dir],
                    ENVS["sam3d_objects"],
                    extra_env={"PYTHONPATH": "modules/sam-3d-objects"},
                )
            else:
                raise ValueError(f"Unknown asset_gen_backend: {args.asset_gen_backend}")
            
            # Run Export
            # Output name is derived from input stem logic in the backend script
            ply_name = os.path.splitext(os.path.basename(relit_file))[0] + ".ply"
            ply_path = os.path.join(props_3d_dir, ply_name)
            
            if os.path.exists(ply_path):
                # asset_id already has _relit stripped? Not necessarily.
                # Harvester asset_id: prop_2026...
                # path: prop_2026..._relit.png
                # Let's trust the 'id' from manifest as the canonical ID.
                run_step(f"Standardization ({asset_id})", "package",
                         ["--input", ply_path, "--id", asset_id],
                         ENVS["base"])
    else:
        print("❌ No harvest manifest found. Skipping Generation.")

    # 6. Report
    run_step("Report Generation", "report",
             ["--output_root", output_dir, "--input_image", input_path],
             ENVS["base"])
             
    print(f"\n🔗 Report available at: {os.path.join(output_dir, 'report.html')}")

if __name__ == "__main__":
    main()
