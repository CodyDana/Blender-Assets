"""FINAL recolour stress captures in UNREAL (offscreen, real RHI) with TEMPORARY test instances (v2 graphs).

Run by fs_ue_run.sh (one UnrealEditor-Cmd, -AllowCommandletRendering -RenderOffscreen, texture streaming off).

For every recolourable part and stress colour a Material Instance Constant is created under the SCRATCH content path
/Game/_Scratch_FinalRecolour (never saved), parented to the SHIPPED buyer-facing MI_<Item>_<Part> (exactly what a buyer
does: duplicate / child the instance and pick a colour), with ONE colour overridden. Each is put on the engine Plane
scaled to one world unit per texel and captured orthographically with SCS_BASE_COLOR (the GBuffer's 8-bit sRGB base
colour) at the texture's own resolution (mip 0) and at 1/16 of it (the GPU then samples mip 4, and the material's own
mip level is 4: the distant view with the v2 mip compensation). EXRs go to final/recolour/ue/. At the end the scratch
folder is deleted and its absence from the registry and the disk is checked. Nothing else is created, modified or saved.
"""
from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

import unreal

PROJECT = Path("C:/Users/Cody/Desktop/Blender_Projects")
OUT = PROJECT / "WorkFiles/materials/final/recolour/ue"
SCRATCH = "/Game/_Scratch_FinalRecolour"
MI = "/Game/NinjaPack/MaterialInstances/"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary


def s2l(v):
    v = v / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def hexlin(h):
    return [s2l(int(h[i:i + 2], 16)) for i in (0, 2, 4)] + [1.0]


FABRIC = {"Kunai_Wrap": ("MI_Kunai_Plain_Wrap", 1024), "SmokeBomb_Cloth": ("MI_SmokeBomb_Cloth", 4096),
          "BlackHat_Straw": ("MI_BlackHat_Straw", 2048), "BlackHat_Cloth": ("MI_BlackHat_Cloth", 2048)}
FAB_COLOURS = ["FFFFFF", "F2E8D5", "FF0000", "0000FF", "808080", "000000", "E7E7E7", "B01010", "1A1A1A"]
PAPER_TESTS = [("Paper Colour", h) for h in ("FFFFFF", "F2E8D5", "FF0000", "0000FF", "808080", "000000", "1A1A1A")] + \
              [("Black Ink Colour", h) for h in ("FFFFFF", "FF0000", "0000FF", "000000")] + \
              [("Red Ink Colour", h) for h in ("FFFFFF", "808080", "0000FF", "F2E8D5", "000000")]


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    r = unreal.Rotator()
    r.pitch, r.yaw, r.roll = float(pitch), float(yaw), float(roll)
    return r


def jobs():
    out = []
    for part, (inst, size) in FABRIC.items():
        out.append({"name": f"{part}__default", "part": part, "inst": inst, "size": size, "param": None, "hex": None})
        for h in FAB_COLOURS:
            out.append({"name": f"{part}__{h}", "part": part, "inst": inst, "size": size, "param": "Colour", "hex": h})
    out.append({"name": "PaperBomb__default", "part": "PaperBomb", "inst": "MI_PaperBomb_Tag", "size": 2048,
                "param": None, "hex": None})
    for param, h in PAPER_TESTS:
        key = param.replace(" Colour", "").replace(" ", "")
        out.append({"name": f"PaperBomb_{key}__{h}", "part": "PaperBomb", "inst": "MI_PaperBomb_Tag", "size": 2048,
                    "param": param, "hex": h})
    return out


def make_mic(job):
    parent = unreal.load_asset(MI + job["inst"])
    if job["param"] is None:
        return parent, None
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mic = tools.create_asset(f"FS_{job['name']}", SCRATCH, unreal.MaterialInstanceConstant,
                             unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mic, parent)
    MEL.set_material_instance_vector_parameter_value(mic, job["param"], unreal.LinearColor(*hexlin(job["hex"])))
    MEL.update_material_instance(mic)
    got = MEL.get_material_instance_vector_parameter_value(mic, job["param"])
    return mic, [got.r, got.g, got.b]


def capture(w, mat, size, px, x0, name):
    actors = []
    try:
        plane = unreal.load_asset("/Engine/BasicShapes/Plane")
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x0, 0.0, 0.0), rot())
        actors.append(a)
        smc = a.get_editor_property("static_mesh_component")
        smc.set_static_mesh(plane)
        smc.set_material(0, mat)
        a.set_actor_scale3d(unreal.Vector(size / 100.0, size / 100.0, 1.0))
        cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(x0, 0.0, 1000.0), rot(pitch=-90.0))
        actors.append(cap)
        cc = cap.get_editor_property("capture_component2d")
        rt = RL.create_render_target2d(w, px, px, unreal.TextureRenderTargetFormat.RTF_RGBA16F)
        cc.set_editor_property("texture_target", rt)
        cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR)
        cc.set_editor_property("capture_every_frame", False)
        cc.set_editor_property("capture_on_movement", False)
        cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
        cc.set_editor_property("ortho_width", float(size))
        cc.capture_scene()
        cc.capture_scene()
        OUT.mkdir(parents=True, exist_ok=True)
        RL.export_render_target(w, rt, str(OUT), name + ".exr")
        return str(OUT / (name + ".exr"))
    finally:
        for a in actors:
            try:
                EAS.destroy_actor(a)
            except Exception:  # noqa: BLE001
                pass


def main():
    t0 = time.time()
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    rep = {"world": w.get_path_name(), "scratch": SCRATCH, "jobs": {}}
    if EAL.does_directory_exist(SCRATCH):
        raise SystemExit(f"{SCRATCH} already exists: refusing to touch it")
    try:
        for i, job in enumerate(jobs()):
            rec = dict(job)
            try:
                mat, got = make_mic(job)
                rec["readback"] = got
                st = MEL.get_statistics(mat)          # blocks until the permutation's shaders exist
                rec["ps_instructions"] = int(st.get_editor_property("num_pixel_shader_instructions"))
                x0 = 20000.0 * (i + 1)
                rec["exr_mip0"] = capture(w, mat, job["size"], job["size"], x0, job["name"] + "__mip0")
                rec["exr_mip4"] = capture(w, mat, job["size"], job["size"] // 16, x0, job["name"] + "__mip4")
            except Exception:  # noqa: BLE001
                rec["error"] = traceback.format_exc()[-1500:]
            rep["jobs"][job["name"]] = rec
            unreal.log(f"FS_JOB {job['name']} {'ERR' if 'error' in rec else 'ok'}")
    finally:
        try:
            deleted = EAL.delete_directory(SCRATCH)
        except Exception:  # noqa: BLE001
            deleted = traceback.format_exc()[-800:]
        disk = PROJECT / "WorkFiles/shuriken/UnrealShuriken/Content/_Scratch_FinalRecolour"
        rep["scratch_deleted"] = deleted
        rep["scratch_exists_in_registry_after"] = bool(EAL.does_directory_exist(SCRATCH))
        rep["scratch_exists_on_disk_after"] = disk.exists()
        rep["seconds"] = round(time.time() - t0, 1)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "fs_ue_capture.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
        unreal.log(f"FS_UE_DONE errors={sum(1 for j in rep['jobs'].values() if 'error' in j)} "
                   f"scratch_on_disk={rep['scratch_exists_on_disk_after']} sec={rep['seconds']}")


main()
