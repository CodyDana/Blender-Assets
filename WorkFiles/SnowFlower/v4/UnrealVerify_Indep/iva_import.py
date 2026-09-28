"""INDEPENDENT pass A (fresh UnrealEditor-Cmd, -nullrhi): import the exact shipped bytes of SM_SnowFlower and
SM_SnowFlower_Sheath into a NEW content path, apply each sidecar with the pipeline helper, import every shipped map
with the kind's intended flags, build three plain preview materials (used only for renders, never assigned to the
mesh assets), and save.  Nothing here is a gate: pass B (a second fresh process) is.
"""
import hashlib, json, os, sys, time, traceback
from pathlib import Path
import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(PROJ / "Scripts"))
from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402

HERE = PROJ / "WorkFiles" / "SnowFlower" / "v4" / "UnrealVerify_Indep"
EXP = PROJ / "Exports" / "SnowFlower" / "v4"
DEST = os.environ["IV_DEST"]
OUT = HERE / "ivA_import.json"
res = {"dest": DEST, "t0": time.time(), "engine": unreal.SystemLibrary.get_engine_version()}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:300]}


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
    sm.set_editor_property("convert_scene", True)
    sm.set_editor_property("convert_scene_unit", True)
    sm.set_editor_property("force_front_x_axis", False)
    sm.set_editor_property("import_uniform_scale", 1.0)
    return ui


def import_mesh(name):
    fbx = EXP / f"{name}.fbx"
    r = {"fbx": str(fbx), "sha256_before": sha(fbx)}
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
        r["sidecar"] = safe(lambda: apply_sidecar(str(EXP / f"{name}.sockets.json"), f"{DEST}/{name}"))
        r["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(mesh))
    r["sha256_after"] = sha(fbx)
    return r


KIND = {
    "BC": dict(srgb=True, compression_settings=unreal.TextureCompressionSettings.TC_DEFAULT),
    "ORM": dict(srgb=False, compression_settings=unreal.TextureCompressionSettings.TC_MASKS),
    "N": dict(srgb=False, compression_settings=unreal.TextureCompressionSettings.TC_NORMALMAP, flip_green_channel=False),
    "Detail": dict(srgb=True, compression_settings=unreal.TextureCompressionSettings.TC_GRAYSCALE),
}


def kind_of(stem):
    for k in ("Detail", "ORM", "BC", "N"):
        if stem.endswith("_" + k):
            return k
    return None


def import_textures():
    out = {}
    tasks = []
    files = sorted((EXP / "Textures").glob("*.png"))
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
        r = {"kind": k, "loaded": tex is not None, "sha256": sha(p)}
        if tex is not None and k:
            for prop, v in KIND[k].items():
                tex.set_editor_property(prop, v)
            tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
            r["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(tex))
        out[p.stem] = r
    return out


def make_material(name, bc, orm, n):
    MEL = unreal.MaterialEditingLibrary
    path = f"{DEST}/Materials"
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, path, unreal.Material, unreal.MaterialFactoryNew())
    def sample(tex_name, stype, y):
        e = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -400, y)
        e.set_editor_property("texture", unreal.load_asset(f"{DEST}/Textures/{tex_name}"))
        e.set_editor_property("sampler_type", stype)
        return e
    e_bc = sample(bc, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -200)
    e_orm = sample(orm, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, 100)
    e_n = sample(n, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, 400)
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
    res["sword"] = import_mesh("SM_SnowFlower")
    res["sheath"] = import_mesh("SM_SnowFlower_Sheath")
    res["textures"] = import_textures()
    res["materials"] = {
        "M_IV_SF_Steel": safe(lambda: make_material("M_IV_SF_Steel", "T_SnowFlower_Steel_BC", "T_SnowFlower_Steel_ORM", "T_SnowFlower_Steel_N")),
        "M_IV_SF_Wrap": safe(lambda: make_material("M_IV_SF_Wrap", "T_SnowFlower_Wrap_BC", "T_SnowFlower_Wrap_ORM", "T_SnowFlower_Wrap_N")),
        "M_IV_SF_Sheath": safe(lambda: make_material("M_IV_SF_Sheath", "T_SnowFlower_Sheath_BC", "T_SnowFlower_Sheath_ORM", "T_SnowFlower_Sheath_N")),
    }
    res["status"] = "ok"
except Exception:  # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
res["seconds"] = round(time.time() - res["t0"], 1)
OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
unreal.log("IV_PASS_A_DONE status=" + res["status"])
