"""AR-01 pack-materials gates, Unreal half: UV-plane BASE-COLOUR captures of the AR-01 instances (real RHI).

Runs inside UnrealEditor-Cmd (-run=pythonscript, -AllowCommandletRendering -RenderOffscreen, texture streaming off) in
the pack's validation project AFTER run_build.sh built and verified the pack. Uses the pack's own capture helpers
(np_render: _capture, the UV-probe material, the one-world-unit-per-texel engine Plane, SCS_BASE_COLOR = the GBuffer's
8-bit sRGB base colour) at one place for every job, plus one UV probe per capture size at that place.

Jobs (EXR RGBA16F into WorkFiles/guns/rifle/scratch/pack_captures/, list in capture_jobs.json):
    fur_default          the SHIPPED MI_AR01_Furniture (Use Original Baked Colours ON) at 2048 = mip 0
    fur_default_bc7      the same with its Base Colour Map swapped for a scratch BC7 import of the same PNG
    fur_tint_default     a transient MIC child of MI_AR01_Furniture with the switch OFF (the buyer's recolour path) at
                         the default Colour
    fur_<hex>_m0 / _m4   the 10 stress colours on that path (MaterialInstanceDynamic Colour) at 2048 (mip 0) and 128
                         (the GPU samples mip 4; the material's own mip level is 4: the distant view)
    metal_default        MI_AR01_Metal at 4096, mag_default MI_AR01_Mag at 1024 (steel: BC1 error, reported)
    uvprobe_<size>       the probe at each size
Nothing is saved: the MICs/MIDs are transient; the BC7 texture is imported into /Game/_Scratch_AR01, which is deleted
at the end (its absence from the registry and the disk is recorded).

    ENV: AR01_PACK_DIR (default <root>/Scripts/unreal/materials), AR01_CAPTURE_OUT (default <root>/WorkFiles/guns/rifle/scratch/pack_captures)
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
PACK = Path(os.environ.get("AR01_PACK_DIR") or ROOT / "Scripts/unreal/materials")
sys.path.insert(0, str(PACK))

import unreal  # noqa: E402

import np_build  # noqa: E402
import np_render as nr  # noqa: E402
import np_spec  # noqa: E402

OUT = Path(os.environ.get("AR01_CAPTURE_OUT") or ROOT / "WorkFiles/guns/rifle/scratch/pack_captures")
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
MI = "/Game/NinjaPack/MaterialInstances/"
SCRATCH = "/Game/_Scratch_AR01"
STRESS = ["FFFFFF", "FF0000", "0000FF", "F2E8D5", "000000", "808080", "1A1A1A", "3050A0", "2E5E2E", "6B3C27"]
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


def import_bc7(png: Path):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(png))
    task.set_editor_property("destination_path", SCRATCH)
    task.set_editor_property("destination_name", "T_AR01_Furniture_BC_BC7")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = unreal.load_asset(f"{SCRATCH}/T_AR01_Furniture_BC_BC7")
    tex.set_editor_property("srgb", True)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_BC7)
    tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    return tex


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    w = nr.world()
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "started": time.strftime("%Y-%m-%d %H:%M:%S"),
           "pack_dir": str(PACK), "jobs": {}, "errors": []}
    plan = np_spec.resolve()
    fur = plan["instances"]["MI_AR01_Furniture"]
    rep["furniture_params"] = fur["effective_params"]
    rep["textures"] = {k: v for k, v in fur["effective_textures"].items()}
    shipped = unreal.load_asset(MI + "MI_AR01_Furniture")
    rep["shipped_baked_switch"] = bool(MEL.get_material_instance_static_switch_parameter_value(
        shipped, "Use Original Baked Colours"))
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

    # probes (one per capture size, at the jobs' place)
    for size in (2048, 4096, 1024):
        job(f"uvprobe_{size}", nr.uv_probe_material(size), size, size, kind="probe", gain=nr.PROBE_GAIN)
    # shipped instances
    job("fur_default", shipped, 2048, 2048, kind="fur_default", reference_png=np_spec.png_rel(
        "Exports/Guns/AR01/Textures/T_AR01_Furniture_BC.png"))
    job("metal_default", unreal.load_asset(MI + "MI_AR01_Metal"), 4096, 4096, kind="steel_default",
        reference_png="Exports/Guns/AR01/Textures/T_AR01_Metal_BC.png")
    job("mag_default", unreal.load_asset(MI + "MI_AR01_Mag"), 1024, 1024, kind="steel_default",
        reference_png="Exports/Guns/AR01/Textures/T_AR01_Mag_BC.png")
    # the BC7 variant of the shipped furniture default
    try:
        tex7 = import_bc7(np_spec.PROJECT / "Exports/Guns/AR01/Textures/T_AR01_Furniture_BC.png")
        mic7 = unreal.new_object(unreal.MaterialInstanceConstant, name="AR01_Fur_BC7")
        MEL.set_material_instance_parent(mic7, shipped)
        MEL.set_material_instance_texture_parameter_value(mic7, "Base Colour Map", tex7)
        MEL.update_material_instance(mic7)
        rep["bc7_texture"] = {"compression": str(tex7.get_editor_property("compression_settings")),
                              "srgb": bool(tex7.get_editor_property("srgb"))}
        job("fur_default_bc7", mic7, 2048, 2048, kind="fur_default_bc7",
            reference_png="Exports/Guns/AR01/Textures/T_AR01_Furniture_BC.png")
    except Exception:  # noqa: BLE001
        rep["errors"].append("bc7: " + traceback.format_exc()[-1200:])
    # the buyer's recolour path: switch OFF on a transient child of the shipped instance
    mic = unreal.new_object(unreal.MaterialInstanceConstant, name="AR01_Fur_Tint")
    MEL.set_material_instance_parent(mic, shipped)
    MEL.set_material_instance_static_switch_parameter_value(mic, "Use Original Baked Colours", False)
    MEL.update_material_instance(mic)
    rep["tint_switch_after"] = bool(MEL.get_material_instance_static_switch_parameter_value(mic, "Use Original Baked Colours"))
    job("fur_tint_default", mic, 2048, 2048, kind="fur_tint_default", colour=fur["effective_params"]["Colour"])
    job("fur_tint_default_m4", mic, 2048, 128, kind="fur_tint_m4", colour=fur["effective_params"]["Colour"])
    for hx in STRESS:
        col = hexlin(hx)
        mid = unreal.MaterialLibrary.create_dynamic_material_instance(w, mic, f"ar01_{hx}")
        mid.set_vector_parameter_value("Colour", unreal.LinearColor(*col))
        job(f"fur_{hx}_m0", mid, 2048, 2048, kind="fur_stress", hex=hx, colour=col)
        job(f"fur_{hx}_m4", mid, 2048, 128, kind="fur_stress_m4", hex=hx, colour=col)
    # clean the scratch folder (never saved) and prove it is gone
    try:
        if EAL.does_directory_exist(SCRATCH):
            EAL.delete_directory(SCRATCH)
        content = np_spec.PROJECT / "WorkFiles/shuriken/UnrealShuriken/Content/_Scratch_AR01"
        rep["scratch_removed"] = {"registry": not EAL.does_directory_exist(SCRATCH)
                                  and not EAL.does_asset_exist(f"{SCRATCH}/T_AR01_Furniture_BC_BC7"),
                                  "disk": not any(content.rglob("*.uasset")) if content.is_dir() else True}
    except Exception:  # noqa: BLE001
        rep["errors"].append("scratch cleanup: " + traceback.format_exc()[-800:])
    rep["order"] = jobs
    rep["passed"] = not rep["errors"]
    (OUT / "capture_jobs.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    unreal.log(f"AR01_CAPTURE_DONE passed={rep['passed']} jobs={len(jobs)} errors={rep['errors']}")


main()
