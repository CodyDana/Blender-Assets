"""LANDSCAPE ROUND (world stage), Unreal step 1 (pythonscript commandlet, -nullrhi): import OUR assets of this round into
DojoLab through the showcase pipeline rules (legacy FBX importer, no auto collision, one convex hull per UCX, imported
normals, vertex colours REPLACED, no materials / textures from the FBX, lightmap UVs off, Import Mesh LODs ON, the
<name>.sockets.json sidecar applied to LodGroup pieces):
  stone kit  Exports/DojoKit/StoneKit/SM_DKT_*.fbx (104, f3)  -> /Game/DojoKit/StoneKit/Meshes
             Nanite per kit_catalog.json; STONE_BUILDING_STUDY 5.2: ShapePreservation NONE, KeepPercent 1 / Trim 0,
             FallbackTarget RELATIVE_ERROR 1.0 (explicit: under AUTO the values do nothing)
  pines      Exports/DojoKit/Pines/SM_DKN_*.fbx (v2f)          -> /Game/DojoKit/Pines/Meshes
             TREE_BUILDING_STUDY 4.13 / 5.2: Nanite on; trunk / rock / mound ShapePreservation NONE (lerp UVs on);
             foliage VOXELIZE with bLerpUVs OFF (UV2 carries the PP2 index); fallback RELATIVE_ERROR 1.0
             textures: BC sRGB, N normal map (DirectX, no flip), ORM / M linear masks, SSS linear grayscale,
             PivotPos EXR HDR NoMips Nearest, XVector uncompressed (VectorDisplacementmap) NoMips Nearest
  fx         Exports/DojoKit/FX/SM_DKF_*.fbx + Textures         -> /Game/DojoKit/FX (for the FX stage)
Idempotent: an asset whose source sha256 (+ its settings key) matches the manifest is skipped.
Result: WorkFiles/dojo/build/landscape/world/json/ls_import.json
"""
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts"))
import unreal  # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402

EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
OUTD = ROOT / "WorkFiles" / "dojo" / "build" / "landscape" / "world" / "json"
MANIFEST = OUTD / "ls_import_manifest.json"
FORCE = os.environ.get("DJ_FORCE_IMPORT", "0") == "1"
ONLY = os.environ.get("DJ_LS_ONLY", "")          # "stone,pines,fx" subset
CAT = json.loads((ROOT / "WorkFiles/dojo/build/stonekit/kit_catalog.json").read_text(encoding="utf-8"))
try:
    SMS = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
except Exception:  # noqa: BLE001
    SMS = None
SMS = SMS or unreal.new_object(unreal.StaticMeshEditorSubsystem)
TC = unreal.TextureCompressionSettings
TEX_INTENT = {
    "BC": {"srgb": True, "compression_settings": TC.TC_DEFAULT},
    "ORM": {"srgb": False, "compression_settings": TC.TC_MASKS},
    "M": {"srgb": False, "compression_settings": TC.TC_MASKS},
    "N": {"srgb": False, "compression_settings": TC.TC_NORMALMAP, "flip_green_channel": False},
    "SSS": {"srgb": False, "compression_settings": TC.TC_GRAYSCALE},
    "PIVOT": {"srgb": False, "compression_settings": TC.TC_HDR, "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS,
              "filter": unreal.TextureFilter.TF_NEAREST, "never_stream": True},
    "XVEC": {"srgb": False, "compression_settings": TC.TC_VECTOR_DISPLACEMENTMAP,
             "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS, "filter": unreal.TextureFilter.TF_NEAREST,
             "never_stream": True},
    "SIXWAY": {"srgb": False, "compression_settings": TC.TC_BC7},
}


def tex_kind(name):
    n = name.rsplit(".", 1)[0]
    if n.endswith("_PivotPos"):
        return "PIVOT"
    if n.endswith("_XVector"):
        return "XVEC"
    if "_SixWay" in n:
        return "SIXWAY"
    for suf, k in (("_BC", "BC"), ("_N", "N"), ("_ORM", "ORM"), ("_M", "M"), ("_SSS", "SSS")):
        if n.endswith(suf):
            return k
    raise ValueError(f"no texture kind for {name}")


def sha(p, extra=""):
    return hashlib.sha256(Path(p).read_bytes() + extra.encode()).hexdigest()


def mesh_options(nanite):
    ui = unreal.FbxImportUI()
    for k, v in (("automated_import_should_detect_type", False), ("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH),
                 ("import_as_skeletal", False), ("import_mesh", True), ("import_materials", False),
                 ("import_textures", False), ("import_animations", False)):
        ui.set_editor_property(k, v)
    sm = ui.get_editor_property("static_mesh_import_data")
    for k, v in (("import_mesh_lods", True), ("auto_generate_collision", False), ("one_convex_hull_per_ucx", True),
                 ("combine_meshes", False), ("generate_lightmap_u_vs", False),
                 ("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS),
                 ("normal_generation_method", unreal.FBXNormalGenerationMethod.MIKK_T_SPACE),
                 ("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE),
                 ("convert_scene", True), ("convert_scene_unit", True), ("force_front_x_axis", False),
                 ("import_uniform_scale", 1.0), ("build_nanite", bool(nanite))):
        sm.set_editor_property(k, v)
    return ui


def run_task(filename, dest, name, factory=None, options=None):
    task = unreal.AssetImportTask()
    for k, v in (("filename", str(filename)), ("destination_path", dest), ("destination_name", name), ("automated", True),
                 ("replace_existing", True), ("replace_existing_settings", True), ("save", False)):
        task.set_editor_property(k, v)
    if factory is not None:
        task.set_editor_property("factory", factory)
    if options is not None:
        task.set_editor_property("options", options)
    AT.import_asset_tasks([task])
    return [str(p) for p in task.get_editor_property("imported_object_paths")]


def set_first(obj, names, value):
    for n in names:
        try:
            obj.set_editor_property(n, value)
            return n
        except Exception:  # noqa: BLE001
            continue
    return None


def nanite_settings(mesh, shape, lerp_uvs):
    """STONE 5.2 / TREE 4.13: shape preservation, lerp UVs, keep 100 %, trim 0, fallback RELATIVE_ERROR 1.0."""
    ns = mesh.get_editor_property("nanite_settings")
    rec = {"enabled": bool(ns.get_editor_property("enabled"))}
    enum = unreal.NaniteShapePreservation
    want = {"none": enum.NONE, "voxelize": enum.VOXELIZE}[shape]
    rec["shape_field"] = set_first(ns, ["shape_preservation"], want)
    rec["lerp_field"] = set_first(ns, ["lerp_u_vs", "lerp_uvs", "b_lerp_u_vs"], bool(lerp_uvs))
    for k, v in (("keep_percent_triangles", 1.0), ("trim_relative_error", 0.0),
                 ("fallback_target", unreal.NaniteFallbackTarget.RELATIVE_ERROR), ("fallback_relative_error", 1.0)):
        try:
            ns.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            rec.setdefault("set_errors", []).append(f"{k}: {str(exc)[:100]}")
    SMS.set_nanite_settings(mesh, ns, True)
    ns = mesh.get_editor_property("nanite_settings")
    rec["shape_preservation"] = str(ns.get_editor_property("shape_preservation")).split(".")[-1].split(":")[0]
    if rec["lerp_field"]:
        rec["lerp_uvs"] = bool(ns.get_editor_property(rec["lerp_field"]))
    rec["fallback_target"] = str(ns.get_editor_property("fallback_target")).split(".")[-1].split(":")[0]
    rec["fallback_relative_error"] = float(ns.get_editor_property("fallback_relative_error"))
    return rec


def jobs():
    J = []
    if not ONLY or "stone" in ONLY:
        for name, p in sorted(CAT["pieces"].items()):
            fbx = ROOT / p["fbx"]
            side = fbx.with_suffix(".sockets.json")
            J.append({"set": "stone", "name": name, "fbx": fbx, "dest": "/Game/DojoKit/StoneKit/Meshes",
                      "nanite": bool(p["nanite"]), "shape": "none", "lerp": True,
                      "sidecar": str(side) if side.exists() else None})
    if not ONLY or "pines" in ONLY:
        for fbx in sorted((ROOT / "Exports/DojoKit/Pines").glob("SM_DKN_*.fbx")):
            fol = fbx.stem.endswith("_Foliage")
            J.append({"set": "pines", "name": fbx.stem, "fbx": fbx, "dest": "/Game/DojoKit/Pines/Meshes", "nanite": True,
                      "shape": "voxelize" if fol else "none", "lerp": not fol, "sidecar": None})
    if not ONLY or "fx" in ONLY:
        for fbx in sorted((ROOT / "Exports/DojoKit/FX").glob("SM_DKF_*.fbx")):
            J.append({"set": "fx", "name": fbx.stem, "fbx": fbx, "dest": "/Game/DojoKit/FX/Meshes", "nanite": False,
                      "shape": "none", "lerp": True, "sidecar": None})
    return J


def tex_jobs():
    T = []
    for s, d, dest in (("pines", "Exports/DojoKit/Pines/Textures", "/Game/DojoKit/Pines/Textures"),
                       ("fx", "Exports/DojoKit/FX/Textures", "/Game/DojoKit/FX/Textures")):
        if ONLY and s not in ONLY:
            continue
        for f in sorted((ROOT / d).iterdir()):
            if f.suffix.lower() in (".png", ".exr"):
                T.append({"set": s, "file": f, "name": f.stem, "dest": dest, "kind": tex_kind(f.name)})
    return T


def main():
    t0 = time.time()
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "force": FORCE, "only": ONLY, "textures": {}, "meshes": {}}
    for t in tex_jobs():
        path = f"{t['dest']}/{t['name']}"
        e = {"file": str(t["file"]), "kind": t["kind"]}
        try:
            h = sha(t["file"], t["kind"])
            if not FORCE and man.get(path) == h and EAL.does_asset_exist(path):
                e["skipped"] = True
                tex = unreal.load_asset(path)
            else:
                run_task(t["file"], t["dest"], t["name"])
                tex = unreal.load_asset(path)
                for k, v in TEX_INTENT[t["kind"]].items():
                    tex.set_editor_property(k, v)
                e["saved"] = bool(EAL.save_loaded_asset(tex, False))
                if e["saved"]:
                    man[path] = h
            e["size"] = [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())]
            e["srgb"] = bool(tex.get_editor_property("srgb"))
            e["compression"] = str(tex.get_editor_property("compression_settings")).split(".")[-1].split(":")[0]
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["textures"][path] = e
        OUTD.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8")
    for j in jobs():
        path = f"{j['dest']}/{j['name']}"
        key = f"nanite={int(j['nanite'])} shape={j['shape']} lerp={int(j['lerp'])} fb=RE1"
        e = {"set": j["set"], "fbx": str(j["fbx"]), "want": key}
        try:
            h = sha(j["fbx"], key)
            if not FORCE and man.get(path) == h and EAL.does_asset_exist(path):
                e["skipped"] = True
            else:
                if EAL.does_asset_exist(path):
                    e["deleted_before_import"] = bool(EAL.delete_asset(path))
                e["imported"] = run_task(j["fbx"], j["dest"], j["name"], unreal.FbxFactory(), mesh_options(j["nanite"]))
                mesh = unreal.load_asset(path)
                if not isinstance(mesh, unreal.StaticMesh):
                    raise RuntimeError(f"{path} is not a StaticMesh after import")
                if j["sidecar"]:
                    sc = apply_sidecar(j["sidecar"], path, save=False)
                    e["sidecar"] = {"sockets": len(sc.get("applied", [])), "lod_screen_sizes": sc.get("lod_screen_sizes")}
                if j["nanite"]:
                    e["nanite_settings"] = nanite_settings(mesh, j["shape"], j["lerp"])
                e["saved"] = bool(EAL.save_loaded_asset(mesh, False))
                if e["saved"]:
                    man[path] = h
            mesh = unreal.load_asset(path)
            agg = mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
            e["convex"] = len(agg.get_editor_property("convex_elems"))
            e["lods"] = int(mesh.get_num_lods())
            ns = mesh.get_editor_property("nanite_settings")
            e["nanite"] = bool(ns.get_editor_property("enabled"))
            e["shape_preservation"] = str(ns.get_editor_property("shape_preservation")).split(".")[-1].split(":")[0]
            e["fallback_target"] = str(ns.get_editor_property("fallback_target")).split(".")[-1].split(":")[0]
            e["slots"] = [str(s.get_editor_property("material_slot_name")) for s in mesh.get_editor_property("static_materials")]
            try:
                e["has_vertex_colors"] = bool(SMS.has_vertex_colors(mesh))
            except Exception:  # noqa: BLE001
                e["has_vertex_colors"] = None
            bb = mesh.get_bounding_box()
            e["bbox_cm"] = [[round(bb.min.x, 2), round(bb.min.y, 2), round(bb.min.z, 2)],
                            [round(bb.max.x, 2), round(bb.max.y, 2), round(bb.max.z, 2)]]
            e["ok"] = e["nanite"] == j["nanite"] and (not j["nanite"] or e["shape_preservation"].upper() == j["shape"].upper())
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
            e["ok"] = False
        rep["meshes"][path] = e
        MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8")
    rep["errors"] = [k for k, v in list(rep["textures"].items()) + list(rep["meshes"].items()) if v.get("error")]
    rep["not_ok"] = [k for k, v in rep["meshes"].items() if not v.get("ok")]
    rep["no_vertex_colours"] = [k for k, v in rep["meshes"].items() if v.get("has_vertex_colors") is False]
    rep["n_meshes"], rep["n_textures"] = len(rep["meshes"]), len(rep["textures"])
    rep["passed"] = not rep["errors"] and not rep["not_ok"]
    rep["sec"] = round(time.time() - t0, 1)
    (OUTD / "ls_import.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    unreal.log(f"DJ_STEP_DONE ls_import passed={rep['passed']} meshes={rep['n_meshes']} textures={rep['n_textures']} "
               f"errors={len(rep['errors'])} not_ok={len(rep['not_ok'])}")


main()
