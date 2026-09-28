"""PaperBomb review pass 1: import the EXACT shipped bytes into a FRESH content path.

/Game/PropsCheck/PaperBombReview in ShurikenValidation.uproject.  Legacy FBX
importer, ASSET_GUIDELINES 6.5 options, Import Mesh LODs ON.  The sidecar goes
through Scripts/pipeline/ue_import_sockets.py unchanged.  Then the four maps, with
the flags set by suffix.  Everything is saved here; NOTHING measured in this
process is a gate - pass 2 re-reads it all in a fresh process.
"""
import json
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\paperbomb\UnrealReview")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "Scripts"))

import unreal  # noqa: E402
import pbr_common as C  # noqa: E402
import pbr_textures as T  # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402

OUT = HERE / "pbr_pass1.json"


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
    sm.set_editor_property("import_mesh_lods", True)          # engine rule: Import Mesh LODs ON
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


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "asset": C.ASSET,
              "fbx": str(C.FBX), "fbx_sha256": C.sha256(C.FBX),
              "sidecar": str(C.SIDECAR), "sidecar_sha256": C.sha256(C.SIDECAR),
              "asset_existed_before_import": bool(unreal.EditorAssetLibrary.does_asset_exist(C.ASSET)),
              "import_mesh_lods": True}
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    try:
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(C.FBX))
        task.set_editor_property("destination_path", C.DEST)
        task.set_editor_property("destination_name", C.MESH)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("replace_existing_settings", True)
        task.set_editor_property("save", False)       # one save only: apply_sidecar's
        task.set_editor_property("factory", unreal.FbxFactory())
        task.set_editor_property("options", options())
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
        report["imported_object_paths"] = paths
        meshes = [m for m in (unreal.load_asset(p) for p in paths) if isinstance(m, unreal.StaticMesh)]
        report["imported_static_meshes"] = len(meshes)
        if meshes:
            mesh = meshes[0]
            # StaticMesh.sockets is protected in Python; ask a component instead.
            _c = unreal.new_object(unreal.StaticMeshComponent)
            _c.set_static_mesh(mesh)
            report["after_import_sockets_before_sidecar"] = [str(n) for n in _c.get_all_socket_names()]
            report["after_import_screen_sizes"] = C.safe(
                lambda: [round(float(v), 6) for v in C.subsystem().get_lod_screen_sizes(mesh)])
            asset_path = mesh.get_path_name().split(".")[0]
            report["sidecar_result"] = apply_sidecar(str(C.SIDECAR), asset_path)
            report["after_sidecar_in_process"] = C.inspect(mesh)
            report["saved"] = bool((report["sidecar_result"] or {}).get("saved")) or bool(
                unreal.EditorAssetLibrary.save_loaded_asset(mesh))
    except Exception:
        report["error_mesh"] = traceback.format_exc()

    # ---- textures ----
    report["textures"] = {"dest": C.TEX_DEST, "maps": {}}
    try:
        for stem in C.TEXTURES:
            png = C.TEXDIR / f"{stem}.png"
            entry = {"png": str(png), "sha256": C.sha256(png), "kind": T.kind_of(stem)}
            try:
                paths, texs = T.import_one(png, stem, C.TEX_DEST)
                entry["imported_object_paths"] = paths
                if texs:
                    tex = texs[0]
                    entry["as_imported"] = T.inspect(tex)
                    entry["as_imported_matches_intent"] = T.matches(entry["as_imported"], entry["kind"])
                    entry["applied"] = T.apply_intent(tex)
                    entry["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(tex))
                else:
                    entry["error"] = "no Texture2D produced"
            except Exception:
                entry["error"] = traceback.format_exc()
            report["textures"]["maps"][stem] = entry
    except Exception:
        report["error_textures"] = traceback.format_exc()

    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("PBR_PASS1_DONE " + str(OUT))


main()
