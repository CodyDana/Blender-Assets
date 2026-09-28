"""Pass 1 (UnrealCheck4, form-parameterised): import <mesh>.fbx into ShurikenValidation and apply the sidecar.

Form from the SHURIKEN_FORM environment variable (default eight_point). Mesh name, FBX,
sidecar and the Blender LOD counts are read from WorkFiles/shuriken/<form>_report.json,
so the same script verifies any form the pack builder wrote. Adapted from
UnrealCheck3/pass1_import.py (four-point only, left unchanged). UE 5.8.2, legacy FBX
importer. Writes <form>_pass1.json next to this file.
"""
import json
import os
import sys
import traceback
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck4"
FORM = os.environ.get("SHURIKEN_FORM", "eight_point")
REPORT = json.loads((PROJ / "WorkFiles" / "shuriken" / f"{FORM}_report.json").read_text(encoding="utf-8"))
MESH = REPORT["asset"]
FBX = Path(REPORT["fbx"])
SIDECAR = Path(REPORT["sockets_sidecar"])
BLENDER_LOD_TRIANGLES = REPORT["lod_triangles"]
DEST_PATH, DEST_NAME = "/Game/ShurikenCheck4", MESH
OUT = HERE / f"{FORM}_pass1.json"
sys.path.insert(0, str(PROJ / "Scripts"))
from pipeline.ue_import_sockets import apply_sidecar, _static_mesh_editor_subsystem  # noqa: E402


def options():
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    sm = ui.get_editor_property("static_mesh_import_data")
    sm.set_editor_property("import_mesh_lods", True)
    sm.set_editor_property("auto_generate_collision", False)
    sm.set_editor_property("one_convex_hull_per_ucx", True)
    sm.set_editor_property("combine_meshes", False)
    sm.set_editor_property("generate_lightmap_u_vs", True)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    sm.set_editor_property("convert_scene", True)
    sm.set_editor_property("convert_scene_unit", True)
    sm.set_editor_property("force_front_x_axis", False)
    sm.set_editor_property("import_uniform_scale", 1.0)
    return ui


def vec(v):
    return [round(v.x, 4), round(v.y, 4), round(v.z, 4)]


def inspect(mesh):
    info = {"asset": mesh.get_path_name()}
    n = mesh.get_num_lods()
    info["num_lods"] = n
    info["lod_triangles"] = [mesh.get_num_triangles(i) for i in range(n)]
    info["lod_vertices"] = [mesh.get_num_vertices(i) for i in range(n)]
    sub = _static_mesh_editor_subsystem()
    info["subsystem"] = sub is not None
    if sub is not None:
        try:
            info["lod_screen_sizes"] = [round(float(v), 6) for v in sub.get_lod_screen_sizes(mesh)]
        except Exception as exc:
            info["lod_screen_sizes_error"] = f"{type(exc).__name__}: {exc}"[:160]
    agg = mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
    info["convex_hulls"] = len(agg.get_editor_property("convex_elems"))
    b = mesh.get_bounding_box()
    info["size_cm"] = [round(b.max.x - b.min.x, 4), round(b.max.y - b.min.y, 4), round(b.max.z - b.min.z, 4)]
    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    info["sockets"] = []
    for name in comp.get_all_socket_names():
        t = comp.get_socket_transform(str(name), unreal.RelativeTransformSpace.RTS_COMPONENT)
        e = t.rotation.euler()
        info["sockets"].append({"name": str(name), "location_cm": vec(t.translation),
                                "rpy": [round(e.x, 3), round(e.y, 3), round(e.z, 3)],
                                "scale": vec(t.scale3d)})
    return info


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "form": FORM, "fbx": str(FBX),
              "sidecar": str(SIDECAR), "blender_lod_triangles": BLENDER_LOD_TRIANGLES}
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(FBX))
        task.set_editor_property("destination_path", DEST_PATH)
        task.set_editor_property("destination_name", DEST_NAME)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("replace_existing_settings", True)
        task.set_editor_property("save", True)
        task.set_editor_property("factory", unreal.FbxFactory())
        task.set_editor_property("options", options())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
        report["imported_object_paths"] = paths
        meshes = [m for m in (unreal.load_asset(p) for p in paths) if isinstance(m, unreal.StaticMesh)]
        report["after_import"] = [inspect(m) for m in meshes]
        if meshes:
            asset_path = meshes[0].get_path_name().split(".")[0]
            report["sidecar_result"] = apply_sidecar(str(SIDECAR), asset_path)
            report["after_sidecar"] = inspect(meshes[0])
            report["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(meshes[0]))
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("PASS1_DONE " + str(OUT))


main()
