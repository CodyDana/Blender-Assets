"""PASS A (fresh process, -nullrhi): import the SHIPPED bytes exactly as the README tells a buyer.

Legacy FBX importer, Import Mesh LODs ON, Auto Generate Collision OFF, One Convex Hull Per UCX ON, Generate Lightmap
UVs OFF, Import Normals, Import Materials OFF.  Then Scripts/pipeline/ue_import_sockets.py (UNCHANGED) with each
sidecar.  Nothing is "fixed" after import: whatever the importer leaves is what the read-back gates.
Textures: import with Unreal's defaults, record them, then apply the README's flags and save.
Verifier-only materials (never shipped) are created for the render pass.
"""
import json
import os
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\flashbang\UnrealVerify_claude")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "Scripts"))
import unreal  # noqa: E402
import uv_common as C  # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402

OUT = HERE / "passA.json"
rep = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "hashes_before": C.all_hashes(),
       "meshes": {}, "textures": {}, "materials": {}}


def fbx_options():
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
    sm.set_editor_property("generate_lightmap_u_vs", False)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    if os.environ.get("UV_README_LITERAL") != "1":
        # ASSET_GUIDELINES 6.5 static-mesh import side (the README omits these; the README-literal run failed)
        sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
        sm.set_editor_property("convert_scene", True)
        sm.set_editor_property("convert_scene_unit", True)
        sm.set_editor_property("force_front_x_axis", False)
        sm.set_editor_property("import_uniform_scale", 1.0)
    return ui


def save_all_under(path):
    return bool(unreal.EditorAssetLibrary.save_directory(path, only_if_is_dirty=False, recursive=True))


try:
    rep["already_exists"] = bool(unreal.EditorAssetLibrary.does_directory_exist(C.DEST)) and bool(
        unreal.EditorAssetLibrary.list_assets(C.DEST, recursive=True))
    if rep["already_exists"]:
        raise RuntimeError("content path already has assets: use a NEW path")
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    for name in C.MESHES:
        r = {}
        try:
            fbx = C.EXP / f"{name}.fbx"
            r["fbx_sha256"] = C.sha256(fbx)
            task = unreal.AssetImportTask()
            task.set_editor_property("filename", str(fbx))
            task.set_editor_property("destination_path", C.DEST)
            task.set_editor_property("destination_name", name)
            task.set_editor_property("automated", True)
            task.set_editor_property("replace_existing", True)
            task.set_editor_property("save", False)
            task.set_editor_property("factory", unreal.FbxFactory())
            task.set_editor_property("options", fbx_options())
            unreal.log(f"UV_IMPORT_BEGIN {name}")
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            unreal.log(f"UV_IMPORT_END {name}")
            r["imported_object_paths"] = [str(p) for p in task.get_editor_property("imported_object_paths")]
            mesh = unreal.load_asset(f"{C.DEST}/{name}")
            r["is_static_mesh"] = isinstance(mesh, unreal.StaticMesh)
            if isinstance(mesh, unreal.StaticMesh):
                r["as_imported"] = {k: v for k, v in C.inspect_mesh(mesh).items()
                                    if k in ("num_lods", "lod_triangles", "lod_screen_sizes", "light_map_coordinate_index",
                                             "convex_hulls", "sockets", "static_materials", "num_uv_channels",
                                             "nanite_enabled", "lod_build_settings")}
                unreal.log(f"UV_SIDECAR_BEGIN {name}")
                r["sidecar_result"] = C.safe(lambda: apply_sidecar(str(C.EXP / f"{name}.sockets.json"),
                                                                    f"{C.DEST}/{name}"))
                unreal.log(f"UV_SIDECAR_END {name}")
                r["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False))
        except Exception:  # noqa: BLE001
            r["error"] = traceback.format_exc()
        rep["meshes"][name] = r

    for tname, (png, want) in C.TEXTURES.items():
        r = {"png": str(png), "sha256": C.sha256(png)}
        try:
            task = unreal.AssetImportTask()
            task.set_editor_property("filename", str(png))
            task.set_editor_property("destination_path", C.TEXDEST)
            task.set_editor_property("destination_name", tname)
            task.set_editor_property("automated", True)
            task.set_editor_property("replace_existing", True)
            task.set_editor_property("save", False)
            unreal.log(f"UV_TEX_BEGIN {tname}")
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            unreal.log(f"UV_TEX_END {tname}")
            tex = unreal.load_asset(f"{C.TEXDEST}/{tname}")
            r["as_imported_defaults"] = C.inspect_texture(tex)
            for k, v in want.items():
                tex.set_editor_property(k, v)
            r["applied"] = {k: str(v) for k, v in want.items()}
            r["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(tex, only_if_is_dirty=False))
        except Exception:  # noqa: BLE001
            r["error"] = traceback.format_exc()
        rep["textures"][tname] = r

    # ---------------- verifier-only materials (for pass C renders and the mip probe) ----------------
    AT = unreal.AssetToolsHelpers.get_asset_tools()
    MEL = unreal.MaterialEditingLibrary
    T = {n: unreal.load_asset(f"{C.TEXDEST}/{n}") for n in C.TEXTURES}

    def new_mat(name):
        return AT.create_asset(name, C.MATDEST, unreal.Material, unreal.MaterialFactoryNew())

    def sample(mat, tex, stype, x, y):
        e = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSample, x, y)
        e.set_editor_property("texture", tex)
        e.set_editor_property("sampler_type", stype)
        return e

    ST = unreal.MaterialSamplerType
    MP = unreal.MaterialProperty
    try:
        m = new_mat("M_UV_Look")
        bc = sample(m, T["T_Flashbang_BC"], ST.SAMPLERTYPE_COLOR, -500, -200)
        orm = sample(m, T["T_Flashbang_ORM"], ST.SAMPLERTYPE_MASKS, -500, 50)
        nn = sample(m, T["T_Flashbang_N"], ST.SAMPLERTYPE_NORMAL, -500, 300)
        ok = [MEL.connect_material_property(bc, "RGB", MP.MP_BASE_COLOR),
              MEL.connect_material_property(orm, "R", MP.MP_AMBIENT_OCCLUSION),
              MEL.connect_material_property(orm, "G", MP.MP_ROUGHNESS),
              MEL.connect_material_property(orm, "B", MP.MP_METALLIC),
              MEL.connect_material_property(nn, "RGB", MP.MP_NORMAL)]
        MEL.recompile_material(m)
        rep["materials"]["M_UV_Look"] = {"connected": ok}
        # flat grey debug (shape only) and a no-normal-map variant (to isolate the normal map)
        g = new_mat("M_UV_Grey")
        c = MEL.create_material_expression(g, unreal.MaterialExpressionConstant3Vector, -300, 0)
        c.set_editor_property("constant", unreal.LinearColor(0.35, 0.35, 0.35, 1.0))
        r_ = MEL.create_material_expression(g, unreal.MaterialExpressionConstant, -300, 200)
        r_.set_editor_property("r", 0.55)
        rep["materials"]["M_UV_Grey"] = {"connected": [MEL.connect_material_property(c, "", MP.MP_BASE_COLOR),
                                                       MEL.connect_material_property(r_, "", MP.MP_ROUGHNESS)]}
        MEL.recompile_material(g)
        # mip probes: unlit, emissive = texture sampled at a fixed mip level
        probes = {"T_Flashbang_BC": ST.SAMPLERTYPE_COLOR, "T_Flashbang_ORM": ST.SAMPLERTYPE_MASKS,
                  "T_Flashbang_N": ST.SAMPLERTYPE_NORMAL, "T_Flashbang_Paint_Detail": ST.SAMPLERTYPE_GRAYSCALE,
                  "T_Flashbang_Paint_Detail16": ST.SAMPLERTYPE_LINEAR_GRAYSCALE}
        for tname, stype in probes.items():
            for mip in (3, 11):
                mn = f"M_UV_Mip_{tname.replace('T_Flashbang_', '')}_{mip}"
                pm = new_mat(mn)
                pm.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
                s = sample(pm, T[tname], stype, -400, 0)
                s.set_editor_property("mip_value_mode", unreal.TextureMipValueMode.TMVM_MIP_LEVEL)
                s.set_editor_property("const_mip_value", mip)
                okc = MEL.connect_material_property(s, "RGB", MP.MP_EMISSIVE_COLOR)
                MEL.recompile_material(pm)
                rep["materials"][mn] = {"connected": okc}
    except Exception:  # noqa: BLE001
        rep["materials_error"] = traceback.format_exc()
    rep["save_directory"] = save_all_under(C.DEST)
    rep["assets"] = [str(p) for p in unreal.EditorAssetLibrary.list_assets(C.DEST, recursive=True)]
except Exception:  # noqa: BLE001
    rep["error"] = traceback.format_exc()
rep["hashes_after"] = C.all_hashes()
rep["shipped_bytes_unchanged"] = rep["hashes_before"] == rep["hashes_after"]
OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
unreal.log("UV_PASSA_DONE")
