"""Probe 2: prove whether Generate Lightmap UVs really produced a UV1.

StaticMeshEditorSubsystem is None under -run=pythonscript and
EditorStaticMeshLibrary.get_num_uv_channels returns 0 even for a mesh that
demonstrably has UV0, so the channel count is not directly readable
(ASSET_GUIDELINES 6.5: those APIs fail silently). Instead import a matched
CONTROL with generate_lightmap_u_vs=False and compare: lightmap UV packing
splits charts, which splits vertices, so a difference in the rendered vertex
count is positive evidence that the generator ran on this mesh.
"""
import json
import traceback
from pathlib import Path

import unreal

REPORT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck\lightmap_probe.json")
FBX = r"C:\Users\Cody\Desktop\Blender_Projects\Exports\Shuriken\SM_Shuriken_FourPoint.fbx"
SHIPPED = "/Game/ShurikenCheck/SM_Shuriken_FourPoint"


def options(generate_lightmap_uvs):
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
    sm.set_editor_property("generate_lightmap_u_vs", generate_lightmap_uvs)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    sm.set_editor_property("convert_scene", True)
    sm.set_editor_property("convert_scene_unit", True)
    sm.set_editor_property("force_front_x_axis", False)
    sm.set_editor_property("import_uniform_scale", 1.0)
    return ui


def snapshot(mesh):
    n = mesh.get_num_lods()
    return {"asset": mesh.get_path_name(),
            "lod_triangles": [mesh.get_num_triangles(i) for i in range(n)],
            "lod_vertices": [mesh.get_num_vertices(i) for i in range(n)],
            "light_map_coordinate_index": mesh.get_editor_property("light_map_coordinate_index"),
            "light_map_resolution": mesh.get_editor_property("light_map_resolution")}


def main():
    out = {"engine": unreal.SystemLibrary.get_engine_version()}
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        # A: can the subsystem be constructed rather than fetched?
        try:
            sub = unreal.new_object(unreal.StaticMeshEditorSubsystem)
            m = unreal.load_asset(SHIPPED)
            out["new_object_subsystem_uv_channels"] = [sub.get_num_uv_channels(m, i) for i in range(m.get_num_lods())]
        except Exception as exc:  # noqa: BLE001
            out["new_object_subsystem_uv_channels"] = f"UNAVAILABLE {type(exc).__name__}: {exc}"[:300]

        # B: matched control import with the lightmap generator OFF
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", FBX)
        task.set_editor_property("destination_path", "/Game/ShurikenCheck/Control")
        task.set_editor_property("destination_name", "SM_Shuriken_FourPoint_NoLightmapUV")
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("replace_existing_settings", True)
        task.set_editor_property("save", False)
        task.set_editor_property("factory", unreal.FbxFactory())
        task.set_editor_property("options", options(False))
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
        control = [m for m in (unreal.load_asset(p) for p in paths) if isinstance(m, unreal.StaticMesh)]
        out["control_off"] = [snapshot(m) for m in control]
        out["shipped_on"] = snapshot(unreal.load_asset(SHIPPED))
        if control:
            c, s = out["control_off"][0], out["shipped_on"]
            out["vertex_delta_per_lod"] = [a - b for a, b in zip(s["lod_vertices"], c["lod_vertices"])]
            out["lightmap_index_delta"] = [s["light_map_coordinate_index"], c["light_map_coordinate_index"]]
    except Exception:  # noqa: BLE001
        out["error"] = traceback.format_exc()
    REPORT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    unreal.log("SHURIKEN_LMPROBE " + json.dumps(out, default=str)[:4000])


if __name__ == "__main__":
    main()
