"""Renderer-configuration check of the pack materials (final pass). Runs in ONE of:
    the validation project (deferred, Substrate off: the reference), or a THROWAWAY copy under
    WorkFiles/materials/final/compat/NPCompat_<tag>/ with r.Substrate=True or r.ForwardShading=True in its own ini.
Nothing is saved: test MICs live in /Game/_Scratch_Compat and are deleted (absence checked on disk).

For every buyer-facing instance: the permutation compiles (get_statistics blocks until the shaders exist; the log is
grepped for 'Failed to compile'). Then, for the five recolourable parts (default + white FFFFFF + red FF0000 child MICs):
  base   SCS_BASE_COLOR orthographic UV-plane capture at 512 px (skipped under forward shading: no GBuffer)
  lit    SCS_FINAL_COLOR_HDR of the same plane under one directional light (fixed intensity, manual exposure)
EXRs in final/compat/out_<tag>/; the analysis (compat_analyse.py) compares each configuration with the deferred one.
"""
from __future__ import annotations

import json
import os
import time
import traceback
from pathlib import Path

import unreal

TAG = os.environ.get("NP_COMPAT_TAG", "deferred")
PROJECT = Path("C:/Users/Cody/Desktop/Blender_Projects")
OUT = PROJECT / f"WorkFiles/materials/final/compat/out_{TAG}"
SCRATCH = "/Game/_Scratch_Compat"
MI = "/Game/NinjaPack/MaterialInstances/"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
LEAVES = ["MI_Shuriken_FourPoint_Steel", "MI_Shuriken_EightPoint_Steel", "MI_Shuriken_SquarePlate_Steel",
          "MI_Shuriken_SixPoint_Steel", "MI_Shuriken_Spike_Steel", "MI_Shuriken_HookedCross_Steel",
          "MI_Kunai_Plain_Steel", "MI_Kunai_Plain_Wrap", "MI_SmokeBomb_Cloth", "MI_BlackHat_Straw", "MI_BlackHat_Cloth",
          "MI_PaperBomb_Tag"]
PARTS = {"Kunai_Wrap": ("MI_Kunai_Plain_Wrap", "Colour"), "SmokeBomb_Cloth": ("MI_SmokeBomb_Cloth", "Colour"),
         "BlackHat_Straw": ("MI_BlackHat_Straw", "Colour"), "BlackHat_Cloth": ("MI_BlackHat_Cloth", "Colour"),
         "PaperBomb": ("MI_PaperBomb_Tag", "Paper Colour"), "FourPoint_Steel": ("MI_Shuriken_FourPoint_Steel", None)}
COLOURS = {"default": None, "FFFFFF": [1.0, 1.0, 1.0, 1.0], "FF0000": [1.0, 0.0, 0.0, 1.0]}
PX = 512


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    r = unreal.Rotator()
    r.pitch, r.yaw, r.roll = float(pitch), float(yaw), float(roll)
    return r


def capture(w, mat, x0, source, name, lit=False):
    actors = []
    try:
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x0, 0.0, 0.0), rot())
        actors.append(a)
        smc = a.get_editor_property("static_mesh_component")
        smc.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
        smc.set_material(0, mat)
        a.set_actor_scale3d(unreal.Vector(PX / 100.0, PX / 100.0, 1.0))
        if lit:
            lt = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(x0, 0, 500), rot(pitch=-50.0, yaw=30.0))
            lt.get_editor_property("directional_light_component").set_editor_property("intensity", 3.0)
            actors.append(lt)
        cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(x0, 0.0, 1000.0), rot(pitch=-90.0))
        actors.append(cap)
        cc = cap.get_editor_property("capture_component2d")
        rt = RL.create_render_target2d(w, PX, PX, unreal.TextureRenderTargetFormat.RTF_RGBA16F)
        cc.set_editor_property("texture_target", rt)
        cc.set_editor_property("capture_source", source)
        cc.set_editor_property("capture_every_frame", False)
        cc.set_editor_property("capture_on_movement", False)
        cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
        cc.set_editor_property("ortho_width", float(PX))
        if lit:
            pp = cc.get_editor_property("post_process_settings")
            pp.set_editor_property("override_auto_exposure_method", True)
            pp.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
            pp.set_editor_property("override_auto_exposure_bias", True)
            pp.set_editor_property("auto_exposure_bias", 0.0)
            pp.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
            pp.set_editor_property("auto_exposure_apply_physical_camera_exposure", False)
            cc.set_editor_property("post_process_settings", pp)
        for _ in range(3):
            cc.capture_scene()
        OUT.mkdir(parents=True, exist_ok=True)
        RL.export_render_target(w, rt, str(OUT), name + ".exr")
        return str(OUT / (name + ".exr"))
    finally:
        for x in actors:
            try:
                EAS.destroy_actor(x)
            except Exception:  # noqa: BLE001
                pass


def main():
    t0 = time.time()
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    cvars = {}
    for cv in ("r.Substrate", "r.ForwardShading", "r.Mobile.ForwardShading"):
        try:
            cvars[cv] = unreal.SystemLibrary.get_console_variable_int_value(cv)
        except Exception as exc:  # noqa: BLE001
            cvars[cv] = repr(exc)
    forward = cvars.get("r.ForwardShading") == 1
    rep = {"tag": TAG, "cvars": cvars, "stats": {}, "captures": {}}
    if EAL.does_directory_exist(SCRATCH):
        raise SystemExit(f"{SCRATCH} exists: refusing")
    try:
        for leaf in LEAVES:
            try:
                st = MEL.get_statistics(unreal.load_asset(MI + leaf))
                rep["stats"][leaf] = {"ps": int(st.get_editor_property("num_pixel_shader_instructions")),
                                      "samplers": int(st.get_editor_property("num_samplers"))}
            except Exception:  # noqa: BLE001
                rep["stats"][leaf] = {"error": traceback.format_exc()[-800:]}
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        i = 0
        for part, (inst, param) in PARTS.items():
            for cname, col in COLOURS.items():
                if col is not None and param is None:
                    continue
                i += 1
                name = f"{part}__{cname}"
                rec = {}
                try:
                    mat = unreal.load_asset(MI + inst)
                    if col is not None:
                        mic = tools.create_asset(f"CMP_{name}", SCRATCH, unreal.MaterialInstanceConstant,
                                                 unreal.MaterialInstanceConstantFactoryNew())
                        MEL.set_material_instance_parent(mic, mat)
                        MEL.set_material_instance_vector_parameter_value(mic, param, unreal.LinearColor(*col))
                        MEL.update_material_instance(mic)
                        mat = mic
                    MEL.get_statistics(mat)
                    if not forward:
                        rec["base"] = capture(w, mat, 20000.0 * i, unreal.SceneCaptureSource.SCS_BASE_COLOR, name + "__base")
                    rec["lit"] = capture(w, mat, 20000.0 * i + 10000.0, unreal.SceneCaptureSource.SCS_FINAL_COLOR_HDR,
                                         name + "__lit", lit=True)
                except Exception:  # noqa: BLE001
                    rec["error"] = traceback.format_exc()[-1200:]
                rep["captures"][name] = rec
                unreal.log(f"NP_COMPAT_JOB {name} {'ERR' if 'error' in rec else 'ok'}")
    finally:
        try:
            rep["scratch_deleted"] = bool(EAL.delete_directory(SCRATCH)) if EAL.does_directory_exist(SCRATCH) else None
        except Exception:  # noqa: BLE001
            rep["scratch_deleted"] = traceback.format_exc()[-400:]
        content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
        rep["scratch_on_disk_after"] = (content / "_Scratch_Compat").exists()
        rep["seconds"] = round(time.time() - t0, 1)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "compat_capture.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
        unreal.log(f"NP_COMPAT_DONE tag={TAG} errors={sum(1 for c in rep['captures'].values() if 'error' in c)} "
                   f"sec={rep['seconds']}")


main()
