"""
Blender 资产导入校验脚本
Author: zhangxin
功能：在后台启动 Blender 尝试导入生成的 GLB/PLY 资产，检测几何完整性并提取顶点、面数等统计信息。
输入：3D 资产文件路径。
输出：标准输出中的 JSON 校验结果。
依赖：Blender Python API (bpy)。
"""
import sys
import json
import bpy

def _emit_result(import_ok, stats=None, error=None):
    payload = {
        "import_ok": bool(import_ok),
        "stats": stats or {},
    }
    if error:
        payload["error"] = str(error)
    print(json.dumps(payload, ensure_ascii=False))


def _collect_mesh_stats():
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    vertices = sum(len(obj.data.vertices) for obj in mesh_objects)
    faces = sum(len(obj.data.polygons) for obj in mesh_objects)
    material_names = set()
    for obj in mesh_objects:
        for slot in obj.material_slots:
            if slot.material:
                material_names.add(slot.material.name)

    return {
        "mesh_objects": len(mesh_objects),
        "vertices": vertices,
        "faces": faces,
        "materials": len(material_names),
    }


def test_import(file_path):
    # clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    try:
        if file_path.lower().endswith('.glb') or file_path.lower().endswith('.gltf'):
            # Clear objects first
            for obj in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
            
            bpy.ops.import_scene.gltf(filepath=file_path)
            stats = _collect_mesh_stats()

            has_geometry = stats["vertices"] > 0
            _emit_result(import_ok=has_geometry, stats=stats)
            return has_geometry

        else:
            _emit_result(import_ok=False, error="unsupported_file_format")
            return False

    except Exception as e:
        _emit_result(import_ok=False, error=str(e))
        return False

if __name__ == "__main__":
    # Blender arguments can be messy, look for '--' to find script arguments
    argv = sys.argv
    if '--' not in argv:
        print("Usage: blender -b -P check_import.py -- <path_to_3d_file>")
        sys.exit(1)
        
    script_args = argv[argv.index('--') + 1:]
    if not script_args:
        print("Usage: blender -b -P check_import.py -- <path_to_3d_file>")
        sys.exit(1)

    asset_path = script_args[0]
    success = test_import(asset_path)
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
