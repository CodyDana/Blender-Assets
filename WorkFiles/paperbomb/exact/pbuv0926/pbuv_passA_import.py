"""PASS A (fresh process 1): import the exact exported bytes into a FRESH content path.

Pipeline importer settings (same as Scripts/unreal/materials/np_meshes.py): legacy FbxFactory,
Interchange FBX off, Import Mesh LODs ON, Import Normals, one convex hull per UCX, no auto collision.
Sidecar applied with Scripts/pipeline/ue_import_sockets.py. Every map imported, incl. Recolour/.
No gates here: gates come from pass B in a second process.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\paperbomb\exact\pbuv0926")
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts")

sys.dont_write_bytecode = True
import unreal                                                    # noqa: E402
import pbuv_common as C                                          # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar             # noqa: E402

OUT = HERE / "pbuv_passA.json"
TC = unreal.TextureCompressionSettings
TMGS = unreal.TextureMipGenSettings


def mesh_options():
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


def import_png(src, dest):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(src))
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("destination_name", src.stem)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", True)
    task.set_editor_property("save", False)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
    return next((t for t in (unreal.load_asset(p) for p in paths) if isinstance(t, unreal.Texture2D)), None), paths


def import_textures(rep):
    res = {}
    jobs = []
    for suffix, intent in C.TEX_INTENT.items():
        want = {"srgb": intent["srgb"], "compression": intent["compression"]}
        if "flip_green" in intent:
            want["flip_green"] = intent["flip_green"]
        jobs.append((C.TEXDIR / f"T_PaperBomb_{suffix}.png", C.TEXDEST, want))
    for stem, intent in C.RECOLOUR_INTENT.items():
        jobs.append((C.RECOLOUR_DIR / f"{stem}.png", C.TEXDEST + "/Recolour", dict(intent)))
    for src, dest, want in jobs:
        tex, paths = import_png(src, dest)
        if tex is None:
            res[src.stem] = {"error": "no Texture2D", "paths": paths}
            continue
        as_imported = C.inspect_texture(tex)
        tex.set_editor_property("srgb", bool(want["srgb"]))
        tex.set_editor_property("compression_settings", getattr(TC, want["compression"]))
        tex.set_editor_property("mip_gen_settings", TMGS.TMGS_FROM_TEXTURE_GROUP)
        if "flip_green" in want:
            tex.set_editor_property("flip_green_channel", bool(want["flip_green"]))
        saved = bool(unreal.EditorAssetLibrary.save_loaded_asset(tex))
        res[src.stem] = {"asset": tex.get_path_name(), "src_sha256": C.sha256(src),
                         "want": want, "saved": saved,
                         "as_imported": as_imported, "after_settings": C.inspect_texture(tex)}
    rep["textures"] = res


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "asset": C.ASSET,
           "fbx_sha256": C.sha256(C.FBX), "sidecar_sha256": C.sha256(C.SIDECAR)}
    try:
        rep["dest_existed_before"] = bool(unreal.EditorAssetLibrary.does_directory_exist(C.DEST))
        rep["dest_assets_before"] = [str(a) for a in unreal.EditorAssetLibrary.list_assets(C.DEST, True, False)] \
            if rep["dest_existed_before"] else []
        unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(C.FBX))
        task.set_editor_property("destination_path", C.DEST)
        task.set_editor_property("destination_name", C.MESH_NAME)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("replace_existing_settings", True)
        task.set_editor_property("save", False)
        task.set_editor_property("factory", unreal.FbxFactory())
        task.set_editor_property("options", mesh_options())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
        rep["imported_object_paths"] = paths
        meshes = [m for m in (unreal.load_asset(p) for p in paths) if isinstance(m, unreal.StaticMesh)]
        rep["imported_static_mesh_count"] = len(meshes)
        if meshes:
            mesh = meshes[0]
            rep["before_sidecar"] = C.inspect_mesh(mesh)
            asset_path = mesh.get_path_name().split(".")[0]
            rep["sidecar_result"] = C.safe(lambda: apply_sidecar(str(C.SIDECAR), asset_path))
            rep["after_sidecar_inprocess"] = C.inspect_mesh(mesh)
            rep["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(mesh))
        import_textures(rep)
    except Exception:
        rep["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    unreal.log("PBUV_PASSA_DONE " + str(OUT))


main()
