"""DojoLab SHOWCASE step (pythonscript commandlet, -nullrhi): import KIT 1, KIT 2 ground, the four prop kits and the
drum-less grey-box pavilion into /Game/DojoKit/<Kit>/{Meshes,Textures} (the grey-box meshes are dj_import.py's).

Meshes: the legacy FBX importer (Interchange.FeatureFlags.Import.FBX 0) with the armory's proven FbxImportUI: no auto
collision, one convex hull per UCX, imported normals, vertex colours replaced from the FBX (kit 1 'Col', ground 'Wear' /
'Blend' / 'Col', training 'Wear'), no materials / textures, lightmap UVs off (AllowStaticLighting False), **Import Mesh
LODs ON** (kit 1, taiko, training, stone and modern ship LodGroups), **Nanite per layout_showcase.json** (kit 1's own
flags; props over 2k triangles; ground and grey-box off), Nanite fallback at full detail (fallback_target
RELATIVE_ERROR + relative error 0; round 2: with the default AUTO target the error value is ignored). After import the `<name>.sockets.json` sidecar is applied
(pipeline.ue_import_sockets: the sockets a LodGroup FBX loses and the LOD screen sizes 1.0 / 0.5 / 0.25).
Textures: BC sRGB TC_Default; ORM and _M masks linear TC_Masks; N linear TC_Normalmap, no green flip (DirectX maps).
Idempotent: an asset whose source sha256 (+ Nanite flag) matches the manifest is skipped (DJ_FORCE_IMPORT=1 forces);
a changed mesh is deleted and imported fresh (a reimport keeps stale slot names).
Result: WorkFiles/dojo/build/unreal/showcase/import.json (dj_sc_verify.py is the authoritative check).
"""
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\Scripts")
import unreal  # noqa: E402
import dj_sc_common as S  # noqa: E402
from pipeline.ue_import_sockets import apply_sidecar  # noqa: E402

EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MANIFEST = S.SC_OUT / "import_manifest.json"
FORCE = os.environ.get("DJ_FORCE_IMPORT", "0") == "1"
try:
    SMS = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
except Exception:  # noqa: BLE001
    SMS = None
SMS = SMS or unreal.new_object(unreal.StaticMeshEditorSubsystem)   # None in a commandlet: new_object works (pipeline)
TEX_INTENT = {
    "BC": {"srgb": True, "compression_settings": unreal.TextureCompressionSettings.TC_DEFAULT},
    "ORM": {"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_MASKS},
    "M": {"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_MASKS},
    "N": {"srgb": False, "compression_settings": unreal.TextureCompressionSettings.TC_NORMALMAP,
          "flip_green_channel": False},
}


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


def main():
    t0 = time.time()
    unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    L = S.load()
    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "force": FORCE, "textures": {}, "meshes": {}}
    # ---- textures first (the masters take their defaults from them)
    for name, t in sorted(L["textures"].items()):
        path = f"{t['ue_dir']}/{name}"
        e = {"png": t["png"], "kind": t["kind"]}
        try:
            h = sha(t["png"])
            if not FORCE and man.get(path) == h and EAL.does_asset_exist(path):
                e["skipped"] = True
                tex = unreal.load_asset(path)
            else:
                run_task(t["png"], t["ue_dir"], name)
                tex = unreal.load_asset(path)
                for k, v in TEX_INTENT[t["kind"]].items():
                    tex.set_editor_property(k, v)
                e["saved"] = bool(EAL.save_loaded_asset(tex, False))
                if e["saved"]:
                    man[path] = h
            e["size"] = [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())]
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["textures"][name] = e
    C_ = S.C
    C_.write_json(MANIFEST, man)
    # ---- meshes (every piece that is not one of the grey-box meshes dj_import.py owns)
    for piece, p in sorted(L["pieces"].items()):
        if p["kit"] == "greybox":
            continue
        path = f"{p['ue_dir']}/{piece}"
        e = {"fbx": p["fbx"], "nanite_wanted": bool(p["nanite"]), "lods_blender": p["lods"]}
        try:
            h = sha(p["fbx"], f"nanite={int(bool(p['nanite']))}")
            if not FORCE and man.get(path) == h and EAL.does_asset_exist(path):
                e["skipped"] = True
            else:
                if EAL.does_asset_exist(path):
                    e["deleted_before_import"] = bool(EAL.delete_asset(path))
                e["imported"] = run_task(p["fbx"], p["ue_dir"], piece, unreal.FbxFactory(), mesh_options(p["nanite"]))
                mesh = unreal.load_asset(path)
                if not isinstance(mesh, unreal.StaticMesh):
                    raise RuntimeError(f"{path} is not a StaticMesh after import")
                if p.get("sidecar"):
                    sc = apply_sidecar(p["sidecar"], path, save=False)
                    e["sidecar"] = {"sockets": len(sc.get("applied", [])), "lod_screen_sizes": sc.get("lod_screen_sizes")}
                e["saved"] = bool(EAL.save_loaded_asset(mesh, False))
                if e["saved"]:
                    man[path] = h
            mesh = unreal.load_asset(path)
            if p["nanite"]:
                # the Nanite FALLBACK mesh (LOD0 render data: bounds, triangle counts, non-Nanite paths) at full detail.
                # Round 2 (2026-09-28): the error / percent values alone do nothing while fallback_target is AUTO (the
                # default): UE 5.8 then decimates the fallback, and the bounds grew 0.5-27.6 cm (38 / 38 meshes). The
                # target must be RELATIVE_ERROR (with error 0) for them to apply. Checked on every run, also on meshes
                # the manifest skips, so an existing project is repaired and every future import keeps it.
                ns = mesh.get_editor_property("nanite_settings")
                want_t = unreal.NaniteFallbackTarget.RELATIVE_ERROR
                if (ns.get_editor_property("fallback_target") != want_t
                        or float(ns.get_editor_property("fallback_relative_error")) != 0.0
                        or float(ns.get_editor_property("fallback_percent_triangles")) != 1.0):
                    ns.set_editor_property("fallback_target", want_t)
                    ns.set_editor_property("fallback_relative_error", 0.0)
                    ns.set_editor_property("fallback_percent_triangles", 1.0)
                    SMS.set_nanite_settings(mesh, ns, True)
                    e["fallback_set_full"] = bool(EAL.save_loaded_asset(mesh, False))
                ns = mesh.get_editor_property("nanite_settings")
                e["fallback_target"] = str(ns.get_editor_property("fallback_target")).split(".")[-1].split(":")[0]
                e["fallback_relative_error"] = float(ns.get_editor_property("fallback_relative_error"))
                e["fallback_full"] = (ns.get_editor_property("fallback_target") == want_t
                                      and e["fallback_relative_error"] == 0.0)
                bb = mesh.get_bounding_box()
                e["bbox_after_cm"] = [[round(bb.min.x, 3), round(bb.min.y, 3), round(bb.min.z, 3)],
                                      [round(bb.max.x, 3), round(bb.max.y, 3), round(bb.max.z, 3)]]
            agg = mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
            e["convex"] = len(agg.get_editor_property("convex_elems"))
            e["lods"] = int(mesh.get_num_lods())
            e["nanite"] = bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))
            e["slots"] = [str(s.get_editor_property("material_slot_name")) for s in mesh.get_editor_property("static_materials")]
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["meshes"][piece] = e
        C_.write_json(MANIFEST, man)
    # ---- round 3: distance-field build fixes (showcase/look_r3.py DF_FIX), also on grey-box meshes; idempotent
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "showcase"))
    import look_r3
    rep["df_fix"] = {}
    for piece, (scale, two) in look_r3.DF_FIX.items():
        e = {}
        try:
            mesh = unreal.load_asset(S.mesh_path(L, piece))
            bs = SMS.get_lod_build_settings(mesh, 0)
            if (abs(float(bs.get_editor_property("distance_field_resolution_scale")) - scale) > 1e-6
                    or bool(bs.get_editor_property("generate_distance_field_as_if_two_sided")) != two):
                bs.set_editor_property("distance_field_resolution_scale", float(scale))
                bs.set_editor_property("generate_distance_field_as_if_two_sided", bool(two))
                SMS.set_lod_build_settings(mesh, 0, bs)
                e["saved"] = bool(EAL.save_loaded_asset(mesh, False))
            bs = SMS.get_lod_build_settings(mesh, 0)
            e["df_resolution_scale"] = float(bs.get_editor_property("distance_field_resolution_scale"))
            e["two_sided"] = bool(bs.get_editor_property("generate_distance_field_as_if_two_sided"))
            e["ok"] = abs(e["df_resolution_scale"] - scale) < 1e-6 and e["two_sided"] == two
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()[-1500:]
        rep["df_fix"][piece] = e
    rep["n_textures"] = len(rep["textures"])
    rep["n_meshes"] = len(rep["meshes"])
    rep["errors"] = [k for k, v in list(rep["textures"].items()) + list(rep["meshes"].items())
                     + list(rep["df_fix"].items()) if v.get("error")]
    rep["nanite_mismatch"] = [k for k, v in rep["meshes"].items() if "nanite" in v and v["nanite"] != v["nanite_wanted"]]
    rep["nanite_fallback_not_full"] = [k for k, v in rep["meshes"].items() if v.get("nanite") and not v.get("fallback_full")]
    rep["passed"] = not rep["errors"] and not rep["nanite_mismatch"] and not rep["nanite_fallback_not_full"]
    rep["sec"] = round(time.time() - t0, 1)
    S.write_json(S.SC_OUT / "import.json", rep)
    unreal.log(f"DJ_STEP_DONE sc_import passed={rep['passed']} meshes={rep['n_meshes']} textures={rep['n_textures']} "
               f"errors={len(rep['errors'])}")


main()
