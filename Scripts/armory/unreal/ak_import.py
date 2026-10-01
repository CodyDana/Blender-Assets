"""ArmoryLab step 1 (pythonscript commandlet, -nullrhi): import the kit into /Game/ArmoryKit.

Hero round (2026-09-28): generic over layout.json: every piece in "pieces" (SM_AK_ / SM_AK_H_ / SM_AKX_) and every map a
layout.json material uses (ak_common.engine_textures: T_AK_*, T_AK_H*, T_AKX_*); an FBX or map in the folder that the
layout does not use is not imported (and its old Unreal asset is deleted as stale); one the layout needs but the exports
lack fails the step.
Meshes: every layout.json piece's Exports/ArmoryKit/<piece>.fbx (SM_AK_ room kit + SM_AKX_ exterior) -> /Game/ArmoryKit/Meshes, legacy FBX importer (Interchange.FeatureFlags.Import.FBX
0), FbxImportUI as the proven SnowFlower v4 pass 1 (Import Mesh LODs ON, no auto collision, one convex hull per UCX, imported
normals, no materials/textures), except Generate Lightmap UVs OFF: the project has AllowStaticLighting False, so lightmap
UVs are unused and the FBX's own UV1 is kept. Nanite (2026-10-01, the VSM "Non-Nanite Marking Job Queue overflow"
warning): ON for every mesh whose slots are all opaque / masked, OFF for the case glass pieces (translucent pane), with a
100 % fallback so LOD0 keeps Blender's triangles (ak_nanite.py). It is applied after the import to EVERY layout mesh,
including ones skipped as unchanged, so an existing project converts without a forced reimport.
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
import ak_nanite as N  # noqa: E402

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


def _enum(cls_name, member):
    cls = getattr(unreal, cls_name, None)
    return getattr(cls, member) if cls is not None and hasattr(cls, member) else None


def set_nanite(mesh, want):
    """Nanite on (100 % fallback, always generated) or off; returns the settings changed ({} when already right).
    set_editor_property notifies the mesh (PostEditChange), which rebuilds it synchronously in this commandlet
    (Editor.AsyncStaticMeshCompilation=0)."""
    ns = mesh.get_editor_property("nanite_settings")
    target = {"enabled": bool(want)}
    if want:
        target["fallback_percent_triangles"] = N.FALLBACK_PERCENT
        for k, cls_name, member in (("fallback_target", "NaniteFallbackTarget", "PERCENT_TRIANGLES"),
                                    ("generate_fallback", "NaniteGenerateFallback", "ENABLED")):
            v = _enum(cls_name, member)
            if v is not None:
                target[k] = v
    changed = {}
    for k, v in target.items():
        cur = ns.get_editor_property(k)
        same = abs(float(cur) - float(v)) < 1e-6 if isinstance(v, float) else str(cur) == str(v)
        if not same:
            ns.set_editor_property(k, v)
            changed[k] = [str(cur), str(v)]
    if changed:
        mesh.set_editor_property("nanite_settings", ns)
    return changed


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
    layout = C.load_layout()
    pieces = C.layout_pieces(layout)   # hero round: every piece layout.json lists (generic), not a folder glob
    mats = C.blender_materials(layout)
    rep["fbx_not_in_layout"] = sorted({f.stem for f in C.EXPORTS.glob("SM_AK*.fbx")} - set(pieces))
    for name in pieces:
        fbx = C.EXPORTS / f"{name}.fbx"
        path = f"{C.MESH_DEST}/{name}"
        e = {"fbx": str(fbx)}
        try:
            if not fbx.exists():
                raise FileNotFoundError(f"layout.json lists {name} but {fbx} is missing")
            h = sha256(fbx)
            e["sha256"] = h
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
            e["nanite_want"] = N.want_nanite(e["slots"], mats)
            e["nanite_changed"] = set_nanite(mesh, e["nanite_want"])
            e["nanite"] = bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))
            if e["nanite_changed"]:
                e["tris_lod0_after_nanite"] = int(mesh.get_num_triangles(0))
            if "imported" in e or e["nanite_changed"]:
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
        e = {"png": str(png), "kind": kind}
        try:
            if not png.exists():
                raise FileNotFoundError(f"a layout.json material needs {png.name}, which is not exported")
            h = sha256(png)
            e["sha256"] = h
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
    rep["nanite"] = {"on": sorted(k for k, v in rep["meshes"].items() if v.get("nanite")),
                     "off": sorted(k for k, v in rep["meshes"].items() if not v.get("nanite")),
                     "changed_this_run": sorted(k for k, v in rep["meshes"].items() if v.get("nanite_changed")),
                     "wrong": sorted(k for k, v in rep["meshes"].items()
                                     if "nanite_want" in v and v.get("nanite") != v["nanite_want"])}
    # look2: remove our own stale meshes (pieces the kit no longer exports), so the level and gates see only the kit
    stems = set(pieces)
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
                     and not rep["errors"] and not rep["nanite"]["wrong"])
    rep["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "import.json", rep)
    unreal.log(f"AK_STEP_DONE import passed={rep['passed']} meshes={rep['n_meshes']} textures={rep['n_textures']}")


main()
