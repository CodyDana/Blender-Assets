"""ArmoryLab step 1 (pythonscript commandlet, -nullrhi): import the kit into /Game/ArmoryKit.

Meshes: every Exports/ArmoryKit/SM_AK*.fbx (SM_AK_ room kit + SM_AKX_ exterior) -> /Game/ArmoryKit/Meshes, legacy FBX importer (Interchange.FeatureFlags.Import.FBX
0), FbxImportUI as the proven SnowFlower v4 pass 1 (Import Mesh LODs ON, no auto collision, one convex hull per UCX, imported
normals, no materials/textures), except Generate Lightmap UVs OFF: the project has AllowStaticLighting False, so lightmap
UVs are unused and the FBX's own UV1 is kept. Nanite stays off: no piece is over the plan's ~2k-triangle threshold
(max 552, layout.json "tris").
Textures: every Exports/ArmoryKit/Textures/T_AK_*_{BC,N,ORM}.png -> /Game/ArmoryKit/Textures with the pack importer's measured
flags: BC sRGB TC_Default; ORM linear TC_Masks; N linear TC_Normalmap, no green flip (the maps are DirectX).

Idempotent: an asset whose source sha256 matches import_manifest.json (written after a good import) is skipped, unless
AK_FORCE_IMPORT=1. Results: WorkFiles/armory/build/unreal/import.json (in-process; ak_verify.py is the authoritative check).
"""
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import ak_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MANIFEST = C.OUT / "import_manifest.json"
FORCE = os.environ.get("AK_FORCE_IMPORT", "0") == "1"

TEX_INTENT = {
    "BC": {"srgb": True, "compression_settings": unreal.TextureCompressionSettings.TC_DEFAULT},
    "ORM": {"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_MASKS,
            "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP},
    "N": {"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_NORMALMAP,
          "flip_green_channel": False},
}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


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
    sm.set_editor_property("generate_lightmap_u_vs", False)
    sm.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    sm.set_editor_property("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    sm.set_editor_property("convert_scene", True)
    sm.set_editor_property("convert_scene_unit", True)
    sm.set_editor_property("force_front_x_axis", False)
    sm.set_editor_property("import_uniform_scale", 1.0)
    try:
        sm.set_editor_property("build_nanite", False)
    except Exception:  # noqa: BLE001
        pass
    return ui


def run_task(filename, dest, name, factory=None, options=None):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(filename))
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("replace_existing_settings", True)
    task.set_editor_property("save", False)
    if factory is not None:
        task.set_editor_property("factory", factory)
    if options is not None:
        task.set_editor_property("options", options)
    AT.import_asset_tasks([task])
    return [str(p) for p in task.get_editor_property("imported_object_paths")]


def mesh_info(mesh):
    info = {"slots": [], "lods": int(mesh.get_num_lods())}
    for s in mesh.get_editor_property("static_materials"):
        info["slots"].append(str(s.get_editor_property("material_slot_name")))
    try:   # the StaticMeshEditorSubsystem is None in a commandlet: read the body setup (SnowFlower v4 pattern)
        agg = mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
        info["convex"] = len(agg.get_editor_property("convex_elems"))
        info["other_simple"] = sum(len(agg.get_editor_property(k)) for k in ("box_elems", "sphere_elems", "sphyl_elems"))
        info["collision_trace"] = str(mesh.get_editor_property("body_setup").get_editor_property("collision_trace_flag"))
    except Exception as exc:  # noqa: BLE001
        info["collision_err"] = str(exc)[:200]
    try:
        info["tris_lod0"] = int(mesh.get_num_triangles(0))
    except Exception:  # noqa: BLE001
        pass
    b = mesh.get_bounding_box()
    info["bbox_cm"] = [[b.min.x, b.min.y, b.min.z], [b.max.x, b.max.y, b.max.z]]
    return info


def main():
    t0 = time.time()
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "force": FORCE, "meshes": {}, "textures": {}}
    for fbx in sorted(C.EXPORTS.glob("SM_AK*.fbx")):
        name = fbx.stem
        path = f"{C.MESH_DEST}/{name}"
        h = sha256(fbx)
        e = {"fbx": str(fbx), "sha256": h}
        try:
            if not FORCE and man.get(path) == h and EAL.does_asset_exist(path):
                e["skipped"] = "unchanged source, asset exists"
            else:
                # look2: a reimport over an existing mesh keeps its OLD material slot names (seen when the glass frames
                # moved from M_AK_Brass to M_AK_Bronze), so a changed source is deleted and imported fresh. The level
                # step respawns every managed actor afterwards.
                if EAL.does_asset_exist(path):
                    e["deleted_before_import"] = bool(EAL.delete_asset(path))
                e["imported"] = run_task(fbx, C.MESH_DEST, name, unreal.FbxFactory(), mesh_options())
            mesh = unreal.load_asset(path)
            if not isinstance(mesh, unreal.StaticMesh):
                raise RuntimeError(f"{path} is not a StaticMesh after import")
            e.update(mesh_info(mesh))
            if "imported" in e:
                e["saved"] = bool(EAL.save_loaded_asset(mesh, False))
                if e["saved"]:
                    man[path] = h
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["meshes"][name] = e
    for png in C.engine_textures():
        name = png.stem
        kind = name.rsplit("_", 1)[1]
        path = f"{C.TEX_DEST}/{name}"
        h = sha256(png)
        e = {"png": str(png), "sha256": h, "kind": kind}
        try:
            if kind not in TEX_INTENT:
                raise RuntimeError(f"no import intent for suffix {kind!r}")
            if not FORCE and man.get(path) == h and EAL.does_asset_exist(path):
                e["skipped"] = "unchanged source, asset exists"
                tex = unreal.load_asset(path)
            else:
                run_task(png, C.TEX_DEST, name)
                tex = unreal.load_asset(path)
                for k, v in TEX_INTENT[kind].items():
                    tex.set_editor_property(k, v)
                e["saved"] = bool(EAL.save_loaded_asset(tex, False))
                if e["saved"]:
                    man[path] = h
            e["flags"] = {k: str(tex.get_editor_property(k)) for k in TEX_INTENT[kind]}
            e["size"] = [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())]
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["textures"][name] = e
    C.write_json(MANIFEST, man)
    rep["n_meshes"] = len(rep["meshes"])
    rep["n_textures"] = len(rep["textures"])
    rep["errors"] = [k for k, v in list(rep["meshes"].items()) + list(rep["textures"].items()) if v.get("error")]
    # look2: remove our own stale meshes (pieces the kit no longer exports), so the level and gates see only the kit
    stems = {f.stem for f in C.EXPORTS.glob("SM_AK*.fbx")}
    rep["stale_deleted"] = []
    for path in sorted(EAL.list_assets(C.MESH_DEST, recursive=False, include_folder=False)):
        base = path.split(".")[0]
        if base.rsplit("/", 1)[-1] not in stems and EAL.delete_asset(base):
            rep["stale_deleted"].append(base)
    # Unreal rebuild: the same for our own textures whose map the kit no longer exports (look2's backdrop, the felt ...)
    tstems = {p.stem for p in C.engine_textures()}
    for path in sorted(EAL.list_assets(C.TEX_DEST, recursive=False, include_folder=False)):
        base = path.split(".")[0]
        if base.rsplit("/", 1)[-1] not in tstems and EAL.delete_asset(base):
            rep["stale_deleted"].append(base)
    rep["passed"] = (rep["n_meshes"] == C.n_meshes() and rep["n_textures"] == C.n_textures()
                     and not rep["errors"])
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "import.json", rep)
    unreal.log(f"AK_STEP_DONE import passed={rep['passed']} meshes={rep['n_meshes']} textures={rep['n_textures']}")


main()
