"""PASS A - import the shipped bytes into a FRESH content path, exactly as the README says.

Nothing here is a gate.  An in-process read cannot tell a persisted setting from a
transient one, so every conclusion is drawn in pass B, in a second fresh process, off the
saved packages.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\paperbomb\UnrealVerify2")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "Scripts"))

import unreal                                                    # noqa: E402
import v2_common as C                                            # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar             # noqa: E402

OUT = HERE / "passA.json"


def mesh_options():
    """README section 1: LODs ON, Import Normals (not Compute), collision from UCX."""
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


COMPRESSION = {
    "TC_DEFAULT": unreal.TextureCompressionSettings.TC_DEFAULT,
    "TC_NORMALMAP": unreal.TextureCompressionSettings.TC_NORMALMAP,
    "TC_MASKS": unreal.TextureCompressionSettings.TC_MASKS,
}


def import_textures(rep):
    """Import the four maps and apply ONLY what README section 3 tells the buyer to do.

    BC and N are left exactly as Unreal imports them - that is the README's claim and it
    is the claim under test.  ORM and M get sRGB off + Masks, which is the change the
    README asks the buyer to make by hand.
    """
    res = {}
    for suffix, intent in C.TEX_INTENT.items():
        src = C.TEXDIR / f"T_PaperBomb_{suffix}.png"
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(src))
        task.set_editor_property("destination_path", C.TEXDEST)
        task.set_editor_property("destination_name", src.stem)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("replace_existing_settings", True)
        task.set_editor_property("save", False)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
        tex = next((t for t in (unreal.load_asset(p) for p in paths)
                    if isinstance(t, unreal.Texture2D)), None)
        if tex is None:
            res[suffix] = {"error": "no Texture2D", "paths": paths}
            continue
        # what Unreal chose on its own, BEFORE the README's manual step
        as_imported = C.inspect_texture(tex)
        if suffix in ("ORM", "M"):
            tex.set_editor_property("srgb", False)
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        unreal.EditorAssetLibrary.save_loaded_asset(tex)
        res[suffix] = {"asset": tex.get_path_name(), "src_sha256": C.sha256(src),
                       "as_imported_before_readme_step": as_imported,
                       "after_readme_step": C.inspect_texture(tex)}
    rep["textures"] = res


def main():
    rep = {
        "engine": unreal.SystemLibrary.get_engine_version(),
        "dest": C.DEST,
        "asset": C.ASSET,
        "fbx": str(C.FBX),
        "fbx_sha256": C.sha256(C.FBX),
        "sidecar_sha256": C.sha256(C.SIDECAR),
        "readme_sha256": C.sha256(C.README),
        "texture_sha256": {s: C.sha256(C.TEXDIR / f"T_PaperBomb_{s}.png") for s in C.TEX_INTENT},
        "readme_promises": {
            "hashes": C.readme_hashes(),
            "screen_sizes": C.readme_screen_sizes(),
            "triangles": C.readme_triangles(),
            "bounds_cm": C.readme_bounds_cm(),
        },
    }
    try:
        # a genuinely fresh content path
        if unreal.EditorAssetLibrary.does_directory_exist(C.DEST):
            rep["wiped_existing_dest"] = bool(unreal.EditorAssetLibrary.delete_directory(C.DEST))
        rep["asset_existed_before"] = bool(unreal.EditorAssetLibrary.does_asset_exist(C.ASSET))

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
        meshes = [m for m in (unreal.load_asset(p) for p in paths)
                  if isinstance(m, unreal.StaticMesh)]
        rep["imported_static_mesh_count"] = len(meshes)
        if meshes:
            mesh = meshes[0]
            rep["before_sidecar"] = C.inspect_mesh(mesh)
            asset_path = mesh.get_path_name().split(".")[0]
            rep["sidecar_result"] = C.safe(lambda: apply_sidecar(str(C.SIDECAR), asset_path))
            rep["after_sidecar"] = C.inspect_mesh(mesh)
            rep["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(mesh))
        import_textures(rep)
    except Exception:
        rep["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    unreal.log("PBV2_PASSA_DONE " + str(OUT))


main()
