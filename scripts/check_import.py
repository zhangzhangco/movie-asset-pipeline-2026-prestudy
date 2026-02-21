import sys
import bpy

def test_import(file_path):
    # clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    try:
        if file_path.lower().endswith('.ply'):
            # In Blender 3.x, use import_mesh.ply instead of wm.ply_import
            if hasattr(bpy.ops.import_mesh, 'ply'):
                bpy.ops.import_mesh.ply(filepath=file_path)
            else:
                bpy.ops.wm.ply_import(filepath=file_path)
                
            # Find the imported object (usually the active one or the only mesh)
            obj = bpy.context.active_object
            if not obj and bpy.data.objects:
                obj = bpy.data.objects[0]

            if not obj or obj.type != 'MESH':
                print("import check failed: no valid mesh found.")
                return False

            if len(obj.data.vertices) == 0:
                print("import check failed: 0 vertices.")
                return False

            print(f"import check success! vertices count: {len(obj.data.vertices)}")
            return True

        elif file_path.lower().endswith('.glb') or file_path.lower().endswith('.gltf'):
            # Clear objects first
            for obj in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
            
            bpy.ops.import_scene.gltf(filepath=file_path)
            
            # Check if any meshes were imported
            has_mesh = False
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    if len(obj.data.vertices) > 0:
                        has_mesh = True
                        break
            
            if has_mesh:
                print("import check success! valid gltf mesh found.")
                return True
            else:
                print("import check failed: no valid geometry in gltf.")
                return False

        else:
            print("unsupported file format for testing.")
            return False

    except Exception as e:
        print(f"import check failed with exception: {str(e)}")
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
