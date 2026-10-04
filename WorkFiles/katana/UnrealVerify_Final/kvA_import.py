"""INDEPENDENT pass A (fresh UnrealEditor-Cmd, -nullrhi): import the exact shipped bytes of SM_Katana and SM_Katana_Saya
into a NEW content path with the pack's legacy-FBX settings (ASSET_GUIDELINES 6.5 / Exports/Katana/README.md:
Import Mesh LODs ON, Convert Scene ON, Convert Scene Unit ON, Force Front X OFF, uniform scale 1, Import Normals,
Combine OFF, Auto Collision OFF, One Convex Hull per UCX, Generate Lightmap UVs 0->1, no materials/textures),
apply each sidecar with the pipeline helper (Scripts/pipeline/ue_import_sockets.py, read-only), import every shipped
map with the README's flags (BC sRGB TC_Default, ORM linear TC_Masks, N TC_Normalmap Flip Green OFF), build plain
preview materials used ONLY on components in the render pass, and save.  Nothing here is a gate: pass B (a second
fresh process) is.  Adapted copy of WorkFiles/SnowFlower/v4/UnrealVerify_Final/iva_import.py.
"""
import json, sys, time, traceback
sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\katana\UnrealVerify_Final")
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts")
import unreal  # noqa: E402
import kv_common as C  # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402

DEST = C.dest()
OUT = C.HERE / "kvA_import.json"
res = {"dest": DEST, "t0": time.time(), "engine": unreal.SystemLibrary.get_engine_version(), "hashes_before": C.all_hashes()}
safe = C.safe


def fbx_ui():
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
    safe(lambda: sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE))
    sm.set_editor_property("convert_scene", True)
    sm.set_editor_property("convert_scene_unit", True)
    sm.set_editor_property("force_front_x_axis", False)
    sm.set_editor_property("import_uniform_scale", 1.0)
    safe(lambda: sm.set_editor_property("build_nanite", False))
    return ui


def import_mesh(name):
    fbx = C.EXP / f"{name}.fbx"
    r = {"fbx": str(fbx), "sha256_before": C.sha(fbx)}
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(fbx))
    t.set_editor_property("destination_path", DEST)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    t.set_editor_property("factory", unreal.FbxFactory())
    t.set_editor_property("options", fbx_ui())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    r["imported"] = [str(p) for p in t.get_editor_property("imported_object_paths")]
    mesh = unreal.load_asset(f"{DEST}/{name}")
    r["is_static_mesh"] = isinstance(mesh, unreal.StaticMesh)
    if mesh is not None:
        r["in_process_lods"] = mesh.get_num_lods()
        def _socks():
            c = unreal.new_object(unreal.StaticMeshComponent)
            c.set_static_mesh(mesh)
            return [str(n) for n in c.get_all_socket_names()]
        r["in_process_sockets_from_fbx"] = safe(_socks)
        try:
            sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        except Exception:  # noqa: BLE001
            sub = None
        if sub is None:
            sub = unreal.new_object(unreal.StaticMeshEditorSubsystem)
        for i in range(mesh.get_num_lods()):
            bs = sub.get_lod_build_settings(mesh, i)
            bs.set_editor_property("generate_lightmap_u_vs", True)
            bs.set_editor_property("src_lightmap_index", 0)
            bs.set_editor_property("dst_lightmap_index", 1)
            sub.set_lod_build_settings(mesh, i, bs)
        mesh.set_editor_property("light_map_coordinate_index", 1)
        r["sidecar"] = safe(lambda: apply_sidecar(str(C.EXP / f"{name}.sockets.json"), f"{DEST}/{name}"))
        r["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(mesh))
    r["sha256_after"] = C.sha(fbx)
    return r


KIND = {
    "BC": dict(srgb=True, compression_settings=unreal.TextureCompressionSettings.TC_DEFAULT),
    "ORM": dict(srgb=False, compression_settings=unreal.TextureCompressionSettings.TC_MASKS),
    "N": dict(srgb=False, compression_settings=unreal.TextureCompressionSettings.TC_NORMALMAP, flip_green_channel=False),
}


def kind_of(stem):
    for k in ("ORM", "BC", "N"):
        if stem.endswith("_" + k):
            return k
    return None


def import_textures():
    out, tasks = {}, []
    files = sorted((C.EXP / "Textures").glob("*.png"))
    for p in files:
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", str(p))
        t.set_editor_property("destination_path", DEST + "/Textures")
        t.set_editor_property("destination_name", p.stem)
        t.set_editor_property("automated", True)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("save", False)
        tasks.append(t)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for p in files:
        tex = unreal.load_asset(f"{DEST}/Textures/{p.stem}")
        k = kind_of(p.stem)
        r = {"kind": k, "loaded": tex is not None, "sha256": C.sha(p)}
        if tex is not None and k:
            for prop, v in KIND[k].items():
                tex.set_editor_property(prop, v)
            tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
            r["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(tex))
        out[p.stem] = r
    return out


def make_material(name, atlas):
    MEL = unreal.MaterialEditingLibrary
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, f"{DEST}/Materials", unreal.Material,
                                                                  unreal.MaterialFactoryNew())
    def sample(tex_name, stype, y):
        e = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -400, y)
        e.set_editor_property("texture", unreal.load_asset(f"{DEST}/Textures/{tex_name}"))
        e.set_editor_property("sampler_type", stype)
        return e
    e_bc = sample(f"T_Katana_{atlas}_BC", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -200)
    e_orm = sample(f"T_Katana_{atlas}_ORM", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, 100)
    e_n = sample(f"T_Katana_{atlas}_N", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, 400)
    MEL.connect_material_property(e_bc, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(e_orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(e_orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(e_orm, "B", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(e_n, "RGB", unreal.MaterialProperty.MP_NORMAL)
    MEL.recompile_material(mat)
    return bool(unreal.EditorAssetLibrary.save_loaded_asset(mat))


try:
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    res["existed_before"] = bool(unreal.EditorAssetLibrary.does_directory_exist(DEST))
    for n in C.MESHES:
        res[n] = import_mesh(n)
    res["textures"] = import_textures()
    res["materials"] = {f"M_KV_{a}": safe(lambda a=a: make_material(f"M_KV_{a}", a)) for a in ("Steel", "Grip", "Saya")}
    res["status"] = "ok"
except Exception:  # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
res["hashes_after"] = C.all_hashes()
res["exports_unchanged"] = res["hashes_after"] == res["hashes_before"]
res["seconds"] = round(time.time() - res["t0"], 1)
OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
unreal.log("KV_PASS_A_DONE status=" + res["status"])
