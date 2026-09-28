"""Probe 4: does the BUILT render data carry a second UV set?

StaticMeshEditorSubsystem.get_num_uv_channels reads the source MeshDescription
(the FBX's own UV sets), not the built render data, so its answer of 1 does not
by itself mean the lightmap generator failed - UE generates lightmap UVs during
the build, into render data.

Nothing in the Python API exposes the render-data texcoord count, so measure it:
import a matched control with Generate Lightmap UVs OFF, save both, and compare
the saved .uasset sizes. A second UV set on 1966 vertices across 3 LODs is
~2 x 2 bytes x 1966 = ~7.9 KB of extra vertex buffer, which is easy to see.
"""
import json
import traceback
from pathlib import Path

import unreal

REPORT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck\lightmap_render_probe.json")
CONTENT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealTest\Content")
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


def import_one(dest_path, dest_name, lightmap):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", FBX)
    task.set_editor_property("destination_path", dest_path)
    task.set_editor_property("destination_name", dest_name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", True)
    task.set_editor_property("save", True)
    task.set_editor_property("factory", unreal.FbxFactory())
    task.set_editor_property("options", options(lightmap))
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
    meshes = [m for m in (unreal.load_asset(p) for p in paths) if isinstance(m, unreal.StaticMesh)]
    return meshes[0] if meshes else None


def uasset(game_path):
    rel = game_path[len("/Game/"):] + ".uasset"
    return CONTENT / rel


def main():
    out = {"engine": unreal.SystemLibrary.get_engine_version()}
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        variants = {
            "lightmap_on": ("/Game/ShurikenCheck/LMProbe", "SM_LM_On", True),
            "lightmap_off": ("/Game/ShurikenCheck/LMProbe", "SM_LM_Off", False),
        }
        rows = {}
        for key, (path, name, flag) in variants.items():
            mesh = import_one(path, name, flag)
            gp = f"{path}/{name}"
            f = uasset(gp)
            rows[key] = {
                "asset": gp,
                "lod_vertices": [mesh.get_num_vertices(i) for i in range(mesh.get_num_lods())],
                "lod_triangles": [mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())],
                "light_map_coordinate_index": mesh.get_editor_property("light_map_coordinate_index"),
                "uasset_path": str(f),
                "uasset_bytes": f.stat().st_size if f.is_file() else None,
            }
        out["variants"] = rows
        a, b = rows["lightmap_on"], rows["lightmap_off"]
        if a["uasset_bytes"] and b["uasset_bytes"]:
            out["uasset_delta_bytes"] = a["uasset_bytes"] - b["uasset_bytes"]
            verts = sum(a["lod_vertices"])
            out["total_render_vertices"] = verts
            out["expected_extra_bytes_half_precision_uv1"] = verts * 4
            out["verdict"] = ("UV1 present in render data"
                              if out["uasset_delta_bytes"] > verts * 2
                              else "NO extra UV set in render data")
        # the shipped asset, for the record
        s = unreal.load_asset(SHIPPED)
        sf = uasset(SHIPPED)
        out["shipped"] = {"uasset_bytes": sf.stat().st_size if sf.is_file() else None,
                          "light_map_coordinate_index": s.get_editor_property("light_map_coordinate_index"),
                          "note": "shipped also carries 2 sockets, so it is a few hundred bytes larger"}
    except Exception:  # noqa: BLE001
        out["error"] = traceback.format_exc()
    REPORT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    unreal.log("SHURIKEN_LMRENDER " + json.dumps(out, default=str)[:4000])


if __name__ == "__main__":
    main()
