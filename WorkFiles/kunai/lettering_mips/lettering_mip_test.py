"""Lettering mask mip test (UE 5.8, real RHI, fresh process). Nothing is saved; the scratch folder is deleted.

1. Import a TEST mask (WorkFiles/kunai/lettering_test/T_Kunai_Lettering_TEST.png, 1536 x 256, never shipped) three ways:
   T_Default  - a fresh import with the factory defaults (what a buyer gets dragging a new PNG in)
   T_Reimport - a copy of the shipped /Game/NinjaPack T_Kunai_Lettering, re-imported with the test PNG over it
                (a buyer replacing the shipped mask) - do its settings survive?
   T_NoMip    - T_Reimport with Mip Gen Settings forced to NoMipmaps (the control: what the main chat feared)
   For each: built size, in-memory size, settings.
2. Two scratch material instances of MI_Kunai_Plain_Wrap with Use Lettering on (T_Reimport / T_NoMip), plus one with
   it off, on SM_Kunai_Plain. Renders: a close-up of the band, and 1 / 2.5 / 5 m at a 90 deg game FOV (1920 x 1088),
   each with 4 sub-pixel camera shifts (shimmer), plus an 8x-narrower-FOV reference of the same view (downsampled 8x
   by the analysis = an anti-aliased ground truth).
"""
import json
import math
import traceback
from pathlib import Path

import unreal

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/kunai/lettering_mips"
FRAMES = OUT / "frames2"
TEST_PNG = ROOT / "WorkFiles/kunai/lettering_test/T_Kunai_Lettering_TEST.png"
SCRATCH = "/Game/Scratch_LetteringMipTest2"
SHIPPED = "/Game/NinjaPack/Textures/Shuriken/T_Kunai_Lettering"
WRAP_MI = "/Game/NinjaPack/MaterialInstances/MI_Kunai_Plain_Wrap"
MESH = "/Game/NinjaPack/Meshes/SM_Kunai_Plain"

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
res = {"steps": [], "textures": {}, "renders": {}}


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    r = unreal.Rotator()
    r.pitch, r.yaw, r.roll = float(pitch), float(yaw), float(roll)
    return r


def tex_info(t):
    d = {}
    for k in ("power_of_two_mode", "mip_gen_settings", "compression_settings", "address_x", "address_y", "srgb", "lod_group"):
        d[k] = str(t.get_editor_property(k))
    s = t.blueprint_get_built_texture_size()
    d["built_size"] = [int(s.x), int(s.y)]
    d["memory_bytes"] = int(t.blueprint_get_memory_size())
    w, h = d["built_size"]
    top = w * h  # G8: one byte per texel
    full, mw, mh, n = 0, w, h, 0
    while True:
        full += mw * mh
        n += 1
        if mw == 1 and mh == 1:
            break
        mw, mh = max(1, mw // 2), max(1, mh // 2)
    d["top_mip_bytes"], d["full_chain_bytes"], d["full_chain_levels"] = top, full, n
    d["memory_over_top_mip"] = round(d["memory_bytes"] / top, 4)
    return d


def import_png(dest_path, dest_name, replace):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(TEST_PNG))
    task.set_editor_property("destination_path", dest_path)
    task.set_editor_property("destination_name", dest_name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", replace)
    task.set_editor_property("save", False)
    AT.import_asset_tasks([task])
    return EAL.load_asset(f"{dest_path}/{dest_name}")


def make_mi(name, mask):
    mi = AT.create_asset(name, SCRATCH, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property("parent", EAL.load_asset(WRAP_MI))
    if mask is not None:
        MEL.set_material_instance_static_switch_parameter_value(mi, "Use Lettering", True)
        MEL.set_material_instance_texture_parameter_value(mi, "Lettering Mask", mask)
        MEL.set_material_instance_vector_parameter_value(mi, "Lettering Colour", unreal.LinearColor(0.62, 0.56, 0.44, 1.0))
    MEL.update_material_instance(mi)
    MEL.get_statistics(mi)            # blocks until this permutation's shaders exist (else it renders the default grid)
    return mi


def capture(w, px_w, px_h, loc, r, fov, name):
    cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, loc, r)
    cc = cap.get_editor_property("capture_component2d")
    rt = RL.create_render_target2d(w, px_w, px_h, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    cc.set_editor_property("texture_target", rt)
    cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    cc.set_editor_property("capture_every_frame", False)
    cc.set_editor_property("capture_on_movement", False)
    cc.set_editor_property("fov_angle", float(fov))
    for prop, val in (("override_custom_near_clipping_plane", True), ("custom_near_clipping_plane", 0.5)):
        try:
            cc.set_editor_property(prop, val)
        except Exception:  # noqa: BLE001
            pass
    pp = cc.get_editor_property("post_process_settings")
    pp.set_editor_property("override_auto_exposure_method", True)
    pp.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
    pp.set_editor_property("override_auto_exposure_bias", True)
    pp.set_editor_property("auto_exposure_bias", 0.0)
    pp.set_editor_property("override_auto_exposure_apply_physical_camera_exposure", True)
    pp.set_editor_property("auto_exposure_apply_physical_camera_exposure", False)
    cc.set_editor_property("post_process_settings", pp)
    cc.set_editor_property("post_process_blend_weight", 1.0)
    for _ in range(3):
        cc.capture_scene()
    FRAMES.mkdir(parents=True, exist_ok=True)
    RL.export_render_target(w, rt, str(FRAMES), name)
    EAS.destroy_actor(cap)
    return str(FRAMES / name)


def main():
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if EAL.does_directory_exist(SCRATCH):
        raise RuntimeError(f"{SCRATCH} already exists - refusing to reuse it")
    res["shipped"] = tex_info(EAL.load_asset(SHIPPED))

    t_def = import_png(SCRATCH, "T_Default", False)
    res["textures"]["T_Default"] = tex_info(t_def)
    EAL.duplicate_asset(SHIPPED, f"{SCRATCH}/T_Reimport")
    t_re = import_png(SCRATCH, "T_Reimport", True)
    res["textures"]["T_Reimport"] = tex_info(t_re)
    EAL.duplicate_asset(f"{SCRATCH}/T_Reimport", f"{SCRATCH}/T_NoMip")
    t_nm = EAL.load_asset(f"{SCRATCH}/T_NoMip")
    t_nm.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    res["textures"]["T_NoMip"] = tex_info(t_nm)
    res["steps"].append("textures")

    mis = {"mip": make_mi("MI_LetTest_Mip", t_re), "nomip": make_mi("MI_LetTest_NoMip", t_nm),
           "blank": make_mi("MI_LetTest_Blank", None)}
    mesh = EAL.load_asset(MESH)
    wrap_slot = next(i for i in range(mesh.get_num_sections(0) + 2)
                     if mesh.get_material(i) and "Wrap" in mesh.get_material(i).get_name())
    res["wrap_slot"] = wrap_slot

    lights = []
    for lrot, lux in ((rot(-40.0, -35.0), 9.0), (rot(-15.0, 140.0), 2.7), (rot(-25.0, 70.0), 6.0)):
        lt = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500), lrot)
        lt.get_editor_property("directional_light_component").set_editor_property("intensity", lux)
        lights.append(lt)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 300), rot())
    slc = sky.get_editor_property("light_component")
    slc.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
    slc.set_editor_property("real_time_capture", True)
    slc.set_editor_property("intensity", 3.0)
    slc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    atmo = EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), rot())
    lights += [sky, atmo]

    actor = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), rot())
    smc = actor.get_editor_property("static_mesh_component")
    smc.set_static_mesh(mesh)

    # band centre: X -90..-18 mm from the shoulder; the pivot sits at x = -19.59 mm (report 14) -> -3.44 cm, on +Z
    c = unreal.Vector(-3.44, 0.0, 1.0)
    res["band_centre_cm"] = [c.x, c.y, c.z]
    el = math.radians(60.0)
    views = [("close", 15.0, 40.0, 1600, 896, False), ("d100", 100.0, 90.0, 1920, 1088, True),
             ("d250", 250.0, 90.0, 1920, 1088, True), ("d500", 500.0, 90.0, 1920, 1088, True)]
    try:
        for vname, d, fov, W, H, jitter in views:
            base = unreal.Vector(c.x, c.y - d * math.cos(el), c.z + d * math.sin(el))
            r = unreal.MathLibrary.find_look_at_rotation(base, c)
            px = 2.0 * d * math.tan(math.radians(fov / 2.0)) / W        # cm per pixel at the band
            rec = {"distance_cm": d, "fov": fov, "size": [W, H], "cm_per_px": px, "band_px_long": 7.2 / px, "frames": {}}
            for key, mi in mis.items():
                smc.set_material(wrap_slot, mi)
                shifts = (0.0, 0.25, 0.5, 0.75) if (jitter and key != "blank") else (0.0,)
                for k, s in enumerate(shifts):
                    loc = unreal.Vector(base.x + s * px, base.y, base.z)
                    rec["frames"][f"{key}_{k}"] = capture(w, W, H, loc, r, fov, f"{vname}_{key}_{k}.png")
                if jitter:
                    rfov = 2.0 * math.degrees(math.atan(math.tan(math.radians(fov / 2.0)) / 8.0))
                    rec["ref_fov"] = rfov
                    rec["frames"][f"{key}_ref"] = capture(w, W, H, base, r, rfov, f"{vname}_{key}_ref.png")
            res["renders"][vname] = rec
        res["steps"].append("renders")
    finally:
        for a in [actor] + lights:
            EAS.destroy_actor(a)


try:
    main()
except Exception:  # noqa: BLE001
    res["error"] = traceback.format_exc()
finally:
    try:
        if EAL.does_directory_exist(SCRATCH):
            res["scratch_deleted"] = bool(EAL.delete_directory(SCRATCH))
        res["scratch_exists_after"] = bool(EAL.does_directory_exist(SCRATCH))
    except Exception:  # noqa: BLE001
        res["cleanup_error"] = traceback.format_exc()
    (OUT / "lettering_mip_test2.json").write_text(json.dumps(res, indent=1))
    print("LETTERING_MIP_TEST_DONE")
