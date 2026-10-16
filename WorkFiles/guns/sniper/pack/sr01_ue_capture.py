"""SR-01 pack-colours gates, Unreal half: UV-plane BASE-COLOUR captures of the SR01 instances (real RHI).
WorkFiles/guns/smg/materials/smg01_ue_capture.py adapted to the sniper: ONE recolourable set (the Chassis, OD paint:
BC 4096 + Detail16 2048, on M_Fabric_Master with Metal From ORM ON) and baked-only steel-master sets (Mag 1024, Metal
2048, Scope Body 2048, Scope Lens 512).

Runs inside UnrealEditor-Cmd (-run=pythonscript, -AllowCommandletRendering -RenderOffscreen, texture streaming off) in
the pack's validation project AFTER run_build.sh built and verified the pack (run_pack_build.sh runs it from the mirror,
with SR01_PACK_DIR = the mirror's Scripts/unreal/materials). Uses the pack's own capture helpers (np_render: _capture,
the UV-probe material, the one-world-unit-per-texel engine Plane, SCS_BASE_COLOR = the GBuffer's 8-bit sRGB base colour).

Jobs (EXR RGBA16F into SR01_CAPTURE_OUT, list in capture_jobs.json):
    chassis_default / mag_default   the SHIPPED instance at the BC's size = mip 0 (chassis: Use Original Baked Colours ON)
    chassis_default_alt / mag_default_alt
                                    the same with its Base Colour Map swapped for a scratch import of the same PNG in
                                    the OTHER compression (shipped BC7 -> BC1 measured beside it, or BC1 -> BC7), so P1's
                                    BC1-vs-BC7 ruling is measured in one run
    chassis_tint_default            a transient MIC child of the shipped chassis with the switch OFF (the buyer's recolour
                                    path) at the default Colour, at the Detail16's size = mip 0
    chassis_<hex>_m0 / _m4          the 13 stress colours on that path at the detail size and 1/16 of it (mip 4)
    metal_default, scope_body_default, scope_lens_default    steel sets (reported)
    uvprobe_<size>                  the probe at each size
Nothing is saved: the MICs/MIDs are transient; the scratch textures go into /Game/_Scratch_SR01, deleted at the end.

    ENV: SR01_PACK_DIR (default <root>/Scripts/unreal/materials), SR01_CAPTURE_OUT (default
         <root>/WorkFiles/guns/sniper/scratch/pack_captures)
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
PACK = Path(os.environ.get("SR01_PACK_DIR") or ROOT / "Scripts/unreal/materials")
sys.path.insert(0, str(PACK))

import unreal  # noqa: E402

import np_build  # noqa: E402
import np_render as nr  # noqa: E402
import np_spec  # noqa: E402

OUT = Path(os.environ.get("SR01_CAPTURE_OUT") or ROOT / "WorkFiles/guns/sniper/scratch/pack_captures")
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
MI = "/Game/NinjaPack/MaterialInstances/"
SCRATCH = "/Game/_Scratch_SR01"
T = "Exports/Guns/SR01/Textures"
STRESS = ["FFFFFF", "FF0000", "0000FF", "F2E8D5", "000000", "808080", "1A1A1A", "3050A0", "2E5E2E", "6B3C27",
          "C2B280", "4B5320", "B08D57"]
SETS = {"chassis": {"inst": "MI_SR01_Chassis", "bc": f"{T}/T_SR01_Chassis_BC.png", "bc_size": 4096, "det_size": 2048}}
BAKED = {"mag": {"inst": "MI_SR01_Mag", "bc": f"{T}/T_SR01_Mag_BC.png", "bc_size": 1024, "gated": True}}
STEEL = {"metal": {"inst": "MI_SR01_Metal", "bc": f"{T}/T_SR01_Metal_BC.png", "bc_size": 2048},
         "scope_body": {"inst": "MI_Att_Scope_LongRange_Body", "bc": f"{T}/T_Att_Scope_LongRange_Scope_Body_BC.png",
                        "bc_size": 2048},
         "scope_lens": {"inst": "MI_Att_Scope_LongRange_Lens", "bc": f"{T}/T_Att_Scope_LongRange_Scope_Lens_BC.png",
                        "bc_size": 512}}
X0 = 20000.0


def s2l(v):
    v = v / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def hexlin(h):
    return [s2l(int(h[i:i + 2], 16)) for i in (0, 2, 4)] + [1.0]


def capture(w, mat, plane_texels, px, name):
    """the engine Plane at one world unit per texel of a plane_texels map, captured orthographically at px x px"""
    actors = []
    try:
        a = nr.EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(X0, 0.0, 0.0), nr.rot())
        actors.append(a)
        smc = a.get_editor_property("static_mesh_component")
        smc.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
        smc.set_material(0, mat)
        a.set_actor_scale3d(unreal.Vector(plane_texels / 100.0, plane_texels / 100.0, 1.0))
        cap, cc, rt = nr._capture(w, px, px, unreal.SceneCaptureSource.SCS_BASE_COLOR,
                                  unreal.TextureRenderTargetFormat.RTF_RGBA16F,
                                  unreal.Vector(X0, 0.0, 1000.0), nr.rot(pitch=-90.0), ortho_width=plane_texels)
        actors.append(cap)
        cc.capture_scene()
        cc.capture_scene()
        return nr._export(w, rt, OUT, name + ".exr")
    finally:
        for a in actors:
            try:
                nr.EAS.destroy_actor(a)
            except Exception:  # noqa: BLE001
                pass


def import_scratch(png: Path, name: str, compression):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(png))
    task.set_editor_property("destination_path", SCRATCH)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = unreal.load_asset(f"{SCRATCH}/{name}")
    tex.set_editor_property("srgb", True)
    tex.set_editor_property("compression_settings", compression)
    tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    return tex


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    w = nr.world()
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "started": time.strftime("%Y-%m-%d %H:%M:%S"),
           "pack_dir": str(PACK), "sets": SETS, "baked": BAKED, "steel": STEEL, "jobs": {}, "errors": [], "params": {},
           "shipped_baked_switch": {}, "tint_switch_after": {}, "shipped_bc_compression": {}, "alt_texture": {}}
    plan = np_spec.resolve()
    jobs = []

    def job(name, mat, plane, px, **meta):
        rec = {"plane_texels": plane, "px": px, **meta}
        try:
            np_build.stats(mat)
            rec["exr"] = capture(w, mat, plane, px, name)
        except Exception:  # noqa: BLE001
            rec["error"] = traceback.format_exc()[-1500:]
            rep["errors"].append(name)
        rep["jobs"][name] = rec
        jobs.append(name)

    def default_and_alt(key, s, shipped):
        job(f"{key}_default", shipped, s["bc_size"], s["bc_size"], kind="default", set=key, reference_png=s["bc"])
        try:
            cur = unreal.load_asset(plan["instances"][s["inst"]]["effective_textures"]["Base Colour Map"])
            comp = cur.get_editor_property("compression_settings")
            rep["shipped_bc_compression"][key] = str(comp)
            is7 = comp == unreal.TextureCompressionSettings.TC_BC7
            alt = unreal.TextureCompressionSettings.TC_DEFAULT if is7 else unreal.TextureCompressionSettings.TC_BC7
            tex = import_scratch(np_spec.PROJECT / s["bc"], Path(s["bc"]).stem + "_ALT", alt)
            mic = unreal.new_object(unreal.MaterialInstanceConstant, name=f"SR01_{key}_ALT")
            MEL.set_material_instance_parent(mic, shipped)
            MEL.set_material_instance_texture_parameter_value(mic, "Base Colour Map", tex)
            MEL.update_material_instance(mic)
            rep["alt_texture"][key] = {"compression": str(tex.get_editor_property("compression_settings")),
                                       "label": "BC1 (TC_DEFAULT)" if is7 else "BC7",
                                       "srgb": bool(tex.get_editor_property("srgb"))}
            job(f"{key}_default_alt", mic, s["bc_size"], s["bc_size"], kind="default_alt", set=key,
                reference_png=s["bc"], label=rep["alt_texture"][key]["label"])
        except Exception:  # noqa: BLE001
            rep["errors"].append(f"{key} alt: " + traceback.format_exc()[-1200:])

    sizes = {2048, 512} | {s["bc_size"] for s in (*SETS.values(), *BAKED.values(), *STEEL.values())} \
        | {s["det_size"] for s in SETS.values()}
    for size in sorted(sizes):
        job(f"uvprobe_{size}", nr.uv_probe_material(size), size, size, kind="probe", gain=nr.PROBE_GAIN)
    for key, s in STEEL.items():
        job(f"{key}_default", unreal.load_asset(MI + s["inst"]), s["bc_size"], s["bc_size"], kind="steel_default",
            set=key, reference_png=s["bc"])
    for key, s in BAKED.items():
        default_and_alt(key, s, unreal.load_asset(MI + s["inst"]))
    for key, s in SETS.items():
        p = plan["instances"][s["inst"]]["effective_params"]
        rep["params"][key] = p
        shipped = unreal.load_asset(MI + s["inst"])
        rep["shipped_baked_switch"][key] = bool(MEL.get_material_instance_static_switch_parameter_value(
            shipped, "Use Original Baked Colours"))
        default_and_alt(key, s, shipped)
        mic = unreal.new_object(unreal.MaterialInstanceConstant, name=f"SR01_{key}_Tint")
        MEL.set_material_instance_parent(mic, shipped)
        MEL.set_material_instance_static_switch_parameter_value(mic, "Use Original Baked Colours", False)
        MEL.update_material_instance(mic)
        rep["tint_switch_after"][key] = bool(
            MEL.get_material_instance_static_switch_parameter_value(mic, "Use Original Baked Colours"))
        d = s["det_size"]
        job(f"{key}_tint_default", mic, d, d, kind="tint_default", set=key, colour=p["Colour"])
        job(f"{key}_tint_default_m4", mic, d, d // 16, kind="tint_m4", set=key, colour=p["Colour"])
        for hx in STRESS:
            col = hexlin(hx)
            mid = unreal.MaterialLibrary.create_dynamic_material_instance(w, mic, f"sr01_{key}_{hx}")
            mid.set_vector_parameter_value("Colour", unreal.LinearColor(*col))
            job(f"{key}_{hx}_m0", mid, d, d, kind="stress", set=key, hex=hx, colour=col)
            job(f"{key}_{hx}_m4", mid, d, d // 16, kind="stress_m4", set=key, hex=hx, colour=col)
    try:
        if EAL.does_directory_exist(SCRATCH):
            EAL.delete_directory(SCRATCH)
        content = np_spec.PROJECT / "WorkFiles/shuriken/UnrealShuriken/Content/_Scratch_SR01"
        rep["scratch_removed"] = {"registry": not EAL.does_directory_exist(SCRATCH),
                                  "disk": not any(content.rglob("*.uasset")) if content.is_dir() else True}
    except Exception:  # noqa: BLE001
        rep["errors"].append("scratch cleanup: " + traceback.format_exc()[-800:])
    rep["order"] = jobs
    rep["passed"] = not rep["errors"]
    (OUT / "capture_jobs.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    unreal.log(f"SR01_CAPTURE_DONE passed={rep['passed']} jobs={len(jobs)} errors={rep['errors']}")


main()
