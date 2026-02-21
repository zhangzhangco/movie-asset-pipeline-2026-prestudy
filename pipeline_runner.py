"""
Movie Assetization Pipeline 主编排脚本
Author: zhangxin
功能：负责跨 Conda 环境调度场景生成、几何重建、资产提取、标准封装和报告生成。
输入：2D 电影静帧或视频路径。
输出：规范化的 3D 资产及其元数据清单。
依赖：Nerfstudio, 3DGS, DUSt3R, TRELLIS 等多环境依赖。
"""
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


def _write_error_log(asset_dir, message):
    os.makedirs(asset_dir, exist_ok=True)
    log_path = os.path.join(asset_dir, "error.log")
    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write(message.strip() + "\n")
    return log_path


def _collect_existing(base_dir, rel_paths):
    outputs = []
    for rel_path in rel_paths:
        abs_path = os.path.join(base_dir, rel_path)
        if os.path.exists(abs_path):
            outputs.append(abs_path)
    return outputs

def _load_failure_metadata(asset_dir):
    failure_path = os.path.join(asset_dir, "failure.json")
    if not os.path.exists(failure_path):
        return None, None

    try:
        with open(failure_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return failure_path, None

    log_path = payload.get("log_path")
    if log_path and not os.path.isabs(log_path):
        log_path = os.path.join(asset_dir, log_path)
    return failure_path, log_path


def _collect_run_log_paths(run_result):
    if run_result is None:
        return []
    paths = []
    if run_result.stdout_log:
        paths.append(run_result.stdout_log)
    if run_result.stderr_log:
        paths.append(run_result.stderr_log)
    return paths


def _validate_required_outputs(asset_type, asset_dir):
    if asset_type == "human":
        mesh_ok = any(
            os.path.exists(os.path.join(asset_dir, candidate))
            for candidate in ("mesh.glb", "mesh.obj", "splat.ply")
        )
        required = ["params.json", "preview.png"]
        missing = []
        if not mesh_ok:
            missing.append("mesh.glb|mesh.obj|splat.ply")
        for rel_path in required:
            if not os.path.exists(os.path.join(asset_dir, rel_path)):
                missing.append(rel_path)
        outputs = _collect_existing(asset_dir, ["mesh.glb", "mesh.obj", "params.json", "preview.png", "splat.ply"])
        return len(missing) == 0, missing, outputs

    if asset_type == "prop":
        mesh_ok = any(
            os.path.exists(os.path.join(asset_dir, candidate))
            for candidate in ("mesh.glb", "mesh.obj", "splat.ply")
        )
        missing = []
        if not mesh_ok:
            missing.append("mesh.glb|mesh.obj|splat.ply")
        if not os.path.exists(os.path.join(asset_dir, "preview.png")):
            missing.append("preview.png")
        outputs = _collect_existing(asset_dir, ["mesh.glb", "mesh.obj", "splat.ply", "preview.png"])
        return len(missing) == 0, missing, outputs

    if asset_type == "scene":
        required = [
            "scene_visual/scene.ply",
            "views/view_01.png",
            "views/view_02.png",
            "views/view_03.png",
        ]
        missing = [rel_path for rel_path in required if not os.path.exists(os.path.join(asset_dir, rel_path))]
        outputs = _collect_existing(asset_dir, required)
        return len(missing) == 0, missing, outputs

    return True, [], []


def _select_primary_output(asset_dir):
    for candidate in ("mesh.glb", "mesh.obj", "splat.ply"):
        candidate_path = os.path.join(asset_dir, candidate)
        if os.path.exists(candidate_path):
            return candidate_path
    return None


def _parse_import_check_result(stdout_text):
    lines = [line.strip() for line in (stdout_text or "").splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and "import_ok" in payload:
            return payload
    return {"import_ok": False, "error": "invalid_or_missing_import_check_json"}


def _run_glb_import_check(glb_path):
    blender_cmd = shutil.which("blender")
    if not blender_cmd:
        return {"import_ok": False, "error": "blender_not_found"}

    try:
        completed = subprocess.run(
            [blender_cmd, "-b", "-P", SCRIPTS["check_import"], "--", glb_path],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as exc:
        return {"import_ok": False, "error": str(exc)}

    result = _parse_import_check_result(completed.stdout)
    result["returncode"] = completed.returncode
    if completed.returncode != 0 and "error" not in result:
        result["error"] = completed.stderr.strip()[:500] if completed.stderr else "blender_import_check_failed"
    return result


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
    logs_root = os.path.join(output_dir, "logs")

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
    scene_run_logs = []
    if not args.skip_scene:
        scene_result = runner.run("Scene Generation (ml-sharp)", "scene_gen",
                                  ["--input-path", input_path, "--output-path", os.path.join(output_dir, "scene_visual")],
                                  ENVS["sharp"],
                                  extra_env={"PYTHONPATH": "modules/ml-sharp/src"},
                                  log_dir=logs_root,
                                  step_id="scene_gen",
                                  asset_id="scene_001")
        scene_run_logs.extend(_collect_run_log_paths(scene_result))
    else:
        print("⏭️ Skipping Scene Generation")

    # 2. Geometry
    if not args.skip_geometry and not args.skip_scene:  # Added condition based on CLI arg semantics
        geometry_result = runner.run("Geometry Reconstruction (DUSt3R)", "geometry",
                                     ["--input", input_path, "--output", os.path.join(output_dir, "dust3r")],
                                     ENVS["dust3r"],
                                     extra_env={"PYTHONPATH": "modules/dust3r"},
                                     log_dir=logs_root,
                                     step_id="geometry",
                                     asset_id="scene_001")
        scene_run_logs.extend(_collect_run_log_paths(geometry_result))
    else:
        print("⏭️ Skipping Geometry")

    # 3. Lighting
    scene_visual_dir = os.path.join(output_dir, "scene_visual")
    potential_plys = glob.glob(os.path.join(scene_visual_dir, "**", "*.ply"), recursive=True)
    potential_ply = potential_plys[0] if potential_plys else None

    lighting_json = os.path.join(output_dir, "lighting_probe.json")
    if potential_ply:
        lighting_result = runner.run("Lighting Estimation", "lighting",
                                     ["--input", potential_ply, "--output", lighting_json],
                                     ENVS["base"],
                                     log_dir=logs_root,
                                     step_id="lighting",
                                     asset_id="scene_001")
        scene_run_logs.extend(_collect_run_log_paths(lighting_result))
    else:
        print(f"⚠️ No scene PLY found for lighting, using default.")
        with open(lighting_json, 'w') as f:
            json.dump({"ambient_light": {"r": 1.0, "g": 1.0, "b": 1.0}}, f)

    # Scene required-file validation (recorded as dedicated manifest asset)
    scene_asset_dir = output_dir
    manifest.record_asset_start(
        asset_id="scene_001",
        asset_type="scene",
        backend_selected="ml-sharp",
        signals={},
        parameters_snapshot={
            "cli": {
                "skip_scene": args.skip_scene,
                "skip_geometry": args.skip_geometry,
                "asset_gen_backend": args.asset_gen_backend,
                "asset_type": args.asset_type,
                "roi_hint": args.roi_hint,
                "disable_skin_rejection": args.disable_skin_rejection,
            },
            "backend": {
                "scene_gen": {"env": "sharp"},
                "geometry": {"env": "dust3r"},
                "lighting": {"env": "base"},
            },
            "model": {"tag": None, "seed": None},
        },
    )
    manifest.append_asset_run_logs("scene_001", scene_run_logs)
    scene_ok, scene_missing, scene_outputs = _validate_required_outputs("scene", scene_asset_dir)
    if scene_ok:
        manifest.record_asset_success("scene_001", outputs=scene_outputs, run_log_paths=scene_run_logs)
    else:
        scene_log = _write_error_log(scene_asset_dir, f"Missing required scene outputs: {', '.join(scene_missing)}")
        manifest.record_asset_failure(
            asset_id="scene_001",
            error_type="OutputValidationError",
            message=f"Missing required scene outputs: {', '.join(scene_missing)}",
            log_path=scene_log,
            outputs=scene_outputs,
        )

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

    harvest_result = runner.run(
        "Asset Extraction & Relighting",
        "harvest",
        harvest_args,
        ENVS["base"],
        log_dir=logs_root,
        step_id="harvest",
        asset_id="scene_001",
    )
    manifest.append_asset_run_logs("scene_001", _collect_run_log_paths(harvest_result))

    # 5. Iterating Asset Manifest and Routing
    prop_dir = os.path.join(output_dir, "props")
    harvest_manifest_path = os.path.join(prop_dir, "harvest_manifest.json")

    asset_counters = {"prop": 0, "human": 0}

    if os.path.exists(harvest_manifest_path):
        with open(harvest_manifest_path, 'r') as f:
            harvest_manifest = json.load(f)

        print(f"🧩 Found {len(harvest_manifest)} props in manifest.")

        for item in harvest_manifest:
            asset_id = item['id']
            relit_file = item['path']  # Absolute path from harvester
            signals = item.get('signals', {})

            asset_type, backend_selected, signals_incomplete = select_asset_type_and_backend(
                signals=signals,
                forced_asset_type=args.asset_type,
                forced_backend=args.asset_gen_backend,
            )
            if asset_type not in {"prop", "human"}:
                asset_type = "prop"

            asset_counters[asset_type] += 1
            unified_asset_dir = os.path.join(output_dir, "assets", f"{asset_type}_{asset_counters[asset_type]:03d}")
            os.makedirs(unified_asset_dir, exist_ok=True)

            print(f"   Processing Asset ID: {asset_id} | Type: {asset_type} | Backend: {backend_selected}")

            parameters_snapshot = {
                "cli": {
                    "asset_gen_backend": args.asset_gen_backend,
                    "asset_type": args.asset_type,
                    "skip_scene": args.skip_scene,
                    "skip_geometry": args.skip_geometry,
                    "roi_hint": args.roi_hint,
                    "disable_skin_rejection": args.disable_skin_rejection,
                },
                "backend": {
                    "selected": backend_selected,
                    "signals_incomplete": args.asset_type == "prop" and signals_incomplete,
                    "asset_output_dir": unified_asset_dir,
                },
                "model": {
                    "tag": "hf" if backend_selected == "sam3d_objects" else None,
                    "seed": 1 if backend_selected == "trellis2" else (42 if backend_selected == "sam3d_objects" else None),
                },
                "source_image": relit_file,
            }
            manifest.record_asset_start(
                asset_id=asset_id,
                asset_type=asset_type,
                backend_selected=backend_selected,
                signals=signals,
                parameters_snapshot=parameters_snapshot,
            )

            # Run 3D Gen backend
            success = False
            run_log_paths = []
            try:
                if backend_selected == "trellis2":
                    run_result = runner.run(
                        f"Hero Asset Gen ({asset_id})",
                        "trellis2",
                        ["--input", relit_file, "--output", unified_asset_dir],
                        ENVS["trellis2"],
                        extra_env={"PYTHONPATH": "modules/TRELLIS.2", "ATTN_BACKEND": "naive"},
                        log_dir=logs_root,
                        step_id="asset_gen",
                        asset_id=asset_id,
                    )
                elif backend_selected == "sam3d_objects":
                    run_result = runner.run(
                        f"Hero Asset Gen ({asset_id})",
                        "sam3d_objects",
                        ["--input", relit_file, "--output", unified_asset_dir],
                        ENVS["sam3d_objects"],
                        extra_env={"PYTHONPATH": "modules/sam-3d-objects"},
                        log_dir=logs_root,
                        step_id="asset_gen",
                        asset_id=asset_id,
                    )
                elif backend_selected == "sam3d_body":
                    run_result = runner.run(
                        f"Hero Asset Gen ({asset_id})",
                        "sam3d_body",
                        ["--image", relit_file, "--output_dir", unified_asset_dir],
                        ENVS["base"],
                        log_dir=logs_root,
                        step_id="asset_gen",
                        asset_id=asset_id,
                    )
                else:
                    print(f"❌ Unknown asset_gen_backend: {backend_selected}")
                    run_result = None
                success = bool(run_result and run_result.success)
                run_log_paths = _collect_run_log_paths(run_result)
                manifest.append_asset_run_logs(asset_id, run_log_paths)
            except Exception as e:
                print(f"❌ Exception in backend {backend_selected}: {e}")

            outputs = [relit_file]
            if not success:
                failure_json, failure_log = _load_failure_metadata(unified_asset_dir)
                if failure_json:
                    outputs.append(failure_json)
                outputs.extend(_collect_existing(unified_asset_dir, ["mesh.glb", "mesh.obj", "splat.ply", "preview.png", "params.json", "failure.json"]))
                error_log = failure_log or _write_error_log(unified_asset_dir, f"{backend_selected} failed to run for asset {asset_id}")
                manifest.record_asset_failure(
                    asset_id=asset_id,
                    error_type="BackendExecutionError",
                    message=f"{backend_selected} failed to run",
                    log_path=error_log,
                    outputs=outputs,
                )
                continue

            # Validate required files immediately after backend completion
            valid, missing, generated_outputs = _validate_required_outputs(asset_type, unified_asset_dir)
            outputs.extend(generated_outputs)
            if asset_type == "human" and not valid:
                error_log = _write_error_log(
                    unified_asset_dir,
                    f"Human required deliverables validation failed for {asset_id}. Missing: {', '.join(missing)}",
                )
                outputs.extend(_collect_existing(unified_asset_dir, ["failure.json"]))
                manifest.record_asset_failure(
                    asset_id=asset_id,
                    error_type="OutputValidationError",
                    message=f"Human required deliverables missing: {', '.join(missing)}",
                    log_path=error_log,
                    outputs=outputs,
                )
                continue

            if not valid:
                error_log = _write_error_log(
                    unified_asset_dir,
                    f"Asset validation failed for {asset_id}. Missing: {', '.join(missing)}",
                )
                outputs.extend(_collect_existing(unified_asset_dir, ["failure.json"]))
                manifest.record_asset_failure(
                    asset_id=asset_id,
                    error_type="OutputValidationError",
                    message=f"Missing required outputs: {', '.join(missing)}",
                    log_path=error_log,
                    outputs=outputs,
                )
                continue

            # Optional packaging for splat/ply based outputs
            splat_path = os.path.join(unified_asset_dir, "splat.ply")
            if os.path.exists(splat_path):
                pkg_success = runner.run(
                    f"Standardization ({asset_id})", "package",
                    ["--input", splat_path, "--id", asset_id],
                    ENVS["base"],
                    log_dir=logs_root,
                    step_id="package",
                    asset_id=asset_id,
                )
                manifest.append_asset_run_logs(asset_id, _collect_run_log_paths(pkg_success))
                if not pkg_success.success:
                    error_log = _write_error_log(unified_asset_dir, "Standardization failed")
                    manifest.record_asset_failure(
                        asset_id=asset_id,
                        error_type="PackagingError",
                        message="Standardization failed",
                        log_path=error_log,
                        outputs=outputs,
                    )
                    continue

            primary_output = _select_primary_output(unified_asset_dir)
            import_check = {}
            if primary_output and primary_output.endswith("mesh.glb"):
                print(f"   Testing GLB Import Compatibility for {asset_id}...")
                import_result = _run_glb_import_check(primary_output)
                import_check = {
                    "import_ok": bool(import_result.get("import_ok")),
                    "stats": import_result.get("stats", {}),
                }
                if import_result.get("error"):
                    import_check["error"] = import_result["error"]
                if import_result.get("returncode") is not None:
                    import_check["returncode"] = import_result["returncode"]
                if import_check["import_ok"]:
                    print("   ✅ Import Validation Passed.")
                else:
                    print(f"   ❌ Import Validation Failed: {import_check.get('error', 'unknown_error')}")
            else:
                import_check = {
                    "skipped": True,
                    "reason": "glb_missing_degraded_to_ply",
                }
                if primary_output:
                    import_check["selected_output"] = os.path.basename(primary_output)
                print(f"   ⚠️ GLB missing; skipped Blender import check for {asset_id}.")

            manifest.update_asset_fields(asset_id, {"import_check": import_check})

            manifest.record_asset_success(
                asset_id=asset_id,
                outputs=outputs,
                run_log_paths=manifest.get_asset_run_logs(asset_id),
            )
    else:
        print("❌ No harvest manifest found. Skipping Generation.")

    # 6. Report
    manifest.save()
    report_result = runner.run(
        "Report Generation", "report",
        ["--output_root", output_dir, "--input_image", input_path],
        ENVS["base"],
        log_dir=logs_root,
        step_id="report",
        asset_id="scene_001",
    )
    manifest.append_asset_run_logs("scene_001", _collect_run_log_paths(report_result))

    print(f"\n🔗 Report available at: {os.path.join(output_dir, 'report.html')}")


if __name__ == "__main__":
    main()
