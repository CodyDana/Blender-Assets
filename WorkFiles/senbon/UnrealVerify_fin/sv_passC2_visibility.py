"""PASS C2 (a FOURTH fresh process, REAL RHI, offscreen; nothing imported or saved): distance visibility / flicker.

1920x1080 frames, 90 deg horizontal FOV (the pack's LOD-switch convention), the mesh at the origin, camera on -Y.
For each mesh (needle, heavy, and the pack's SM_Shuriken_Spike as the control) and each distance:
  * LOD identification: engine-picked LOD vs forced LOD0/1/2 (unlit mask, raw scene colour);
  * 8 sub-pixel camera jitters x 2 orientations (along X; tilted 20 deg in the screen plane), each captured as
    (a) SCS_SCENE_COLOR_HDR = the raw raster before any anti-aliasing (the worst single frame), and
    (b) SCS_FINAL_COLOR_LDR = what the capture shows after its post chain (no persisted history).
    The mean of the 8 raw frames stands in for temporal accumulation (TSR/TAA integrate sub-pixel jitter).
Plus grey (non-metal) form frames at LOD0/1/2 for a shape read that the dark-environment steel cannot give.
Frames go to renders_mask/ (scratch) and renders/; sv_analyse.py reduces them.
"""
import json
import math
import sys
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\senbon\UnrealVerify_fin")
sys.path.insert(0, str(HERE))
import unreal  # noqa: E402
import sv_common as C  # noqa: E402

OUT = HERE / "passC2.json"
MDIR = HERE / "renders_mask"
MDIR.mkdir(exist_ok=True)
RDIR = HERE / "renders"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
ML = unreal.MathLibrary
MEL = unreal.MaterialEditingLibrary
SCS = unreal.SceneCaptureSource
res = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "t0": time.time(),
       "hashes_before": C.all_hashes(), "frames": [], "grey_shots": []}
SPIKE = "/Game/NinjaPack/Meshes/SM_Shuriken_Spike"
W, H, FOV = 1920, 1080, 90.0
DISTS = (0.5, 0.86, 0.92, 2.45, 2.63, 3.9, 4.1, 5.0)   # FINALISE: + the needle LOD2 switch at 3.985 m
JIT = [((3 * k % 8) / 8.0, k / 8.0) for k in range(8)]   # (dx, dy) in pixels


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:300]}


def dump():
    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


spawned = []
try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    mask = unreal.load_asset(f"{C.MATDEST}/M_SV_Mask")
    MEL.recompile_material(mask)
    MEL.get_statistics(mask)
    # transient grey default-lit material (never saved)
    grey = unreal.new_object(unreal.Material, name="SV_Grey_Transient")
    c3 = MEL.create_material_expression(grey, unreal.MaterialExpressionConstant3Vector, -300, 0)
    c3.set_editor_property("constant", unreal.LinearColor(0.45, 0.45, 0.45, 1.0))
    rr = MEL.create_material_expression(grey, unreal.MaterialExpressionConstant, -300, 200)
    rr.set_editor_property("r", 0.5)
    MEL.connect_material_property(c3, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(rr, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(grey)
    MEL.get_statistics(grey)
    meshes = {"needle": unreal.load_asset(f"{C.DEST}/SM_Senbon_Needle"),
              "heavy": unreal.load_asset(f"{C.DEST}/SM_Senbon_Heavy"),
              "spike": unreal.load_asset(SPIKE)}
    res["loaded"] = {k: v is not None for k, v in meshes.items()}
    res["spike_screen_sizes"] = safe(lambda: [float(v) for v in C.sme().get_lod_screen_sizes(meshes["spike"])])
    res["spike_bounds_radius_cm"] = safe(lambda: float(meshes["spike"].get_bounds().sphere_radius))

    cam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0), unreal.Rotator())
    spawned.append(cam)
    cc = cam.get_editor_property("capture_component2d")
    rt = RL.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    cc.set_editor_property("texture_target", rt)
    cc.set_editor_property("capture_every_frame", False)
    cc.set_editor_property("capture_on_movement", False)
    cc.set_editor_property("fov_angle", FOV)
    for prop, val in (("override_custom_near_clipping_plane", True), ("custom_near_clipping_plane", 1.0)):
        safe(lambda prop=prop, val=val: cc.set_editor_property(prop, val))
    pp = cc.get_editor_property("post_process_settings")
    for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                 ("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.0),
                 ("override_auto_exposure_apply_physical_camera_exposure", True),
                 ("auto_exposure_apply_physical_camera_exposure", False),
                 ("override_motion_blur_amount", True), ("motion_blur_amount", 0.0),
                 ("override_bloom_intensity", True), ("bloom_intensity", 0.0),
                 ("override_vignette_intensity", True), ("vignette_intensity", 0.0)):
        safe(lambda k=k, v=v: pp.set_editor_property(k, v))
    cc.set_editor_property("post_process_settings", pp)
    cc.set_editor_property("post_process_blend_weight", 1.0)
    res["capture_settings"] = {k: str(safe(lambda k=k: cc.get_editor_property(k))) for k in
                               ("always_persist_rendering_state", "lod_distance_factor", "fov_angle")}

    def snap(fname, source, loc):
        cc.set_editor_property("capture_source", source)
        cam.set_actor_location_and_rotation(unreal.Vector(*loc), unreal.Rotator(roll=0.0, pitch=0.0, yaw=90.0),
                                            False, False)
        cc.capture_scene()
        RL.export_render_target(world, rt, str(MDIR), fname)
        return fname

    for key, mesh in meshes.items():
        if mesh is None:
            continue
        nmat = len(mesh.get_editor_property("static_materials"))
        for orient, pitch in (("h", 0.0), ("diag", 20.0)):
            a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0),
                                           unreal.Rotator(roll=0.0, pitch=pitch, yaw=0.0))
            comp = a.get_editor_property("static_mesh_component")
            comp.set_mobility(unreal.ComponentMobility.MOVABLE)
            comp.set_static_mesh(mesh)
            for i in range(nmat):
                comp.set_material(i, mask)
            for dm in DISTS:
                d = dm * 100.0
                px = 2.0 * d * math.tan(math.radians(FOV / 2)) / W     # cm per pixel
                rec = {"mesh": key, "orient": orient, "distance_m": dm, "px_cm": px, "raw": [], "ldr": [], "lod": {}}
                if orient == "h":
                    for forced in (None, 0, 1, 2):
                        comp.set_forced_lod_model(0 if forced is None else forced + 1)
                        tag = "auto" if forced is None else f"LOD{forced}"
                        rec["lod"][tag] = snap(f"{key}_{orient}_{dm:.2f}_lod_{tag}.png", SCS.SCS_SCENE_COLOR_HDR,
                                               (0.0, -d, 0.0))
                    comp.set_forced_lod_model(0)
                for j, (dx, dy) in enumerate(JIT):
                    # camera right = -X when looking along +Y: shifting the camera by +dx px along -X moves the image
                    loc = (-dx * px, -d, dy * px)
                    rec["raw"].append(snap(f"{key}_{orient}_{dm:.2f}_j{j}_raw.png", SCS.SCS_SCENE_COLOR_HDR, loc))
                    rec["ldr"].append(snap(f"{key}_{orient}_{dm:.2f}_j{j}_ldr.png", SCS.SCS_FINAL_COLOR_LDR, loc))
                res["frames"].append(rec)
            EAS.destroy_actor(a)
            dump()

    # ---------------- grey form frames (lit) ----------------
    for travel, lux in (((-0.55, 0.45, -0.70), 6.0), ((0.6, 0.3, -0.4), 2.0), ((0.2, -0.9, 0.35), 2.5)):
        la = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 300),
                                        ML.make_rot_from_x(unreal.Vector(*travel)))
        lc = la.get_editor_property("directional_light_component")
        lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        lc.set_editor_property("intensity", lux)
        spawned.append(la)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 300), unreal.Rotator())
    sc = sky.get_editor_property("light_component")
    safe(lambda: sc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE))
    safe(lambda: sc.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP))
    safe(lambda: sc.set_editor_property("cubemap", unreal.load_asset("/Engine/MapTemplates/Sky/DaylightAmbientCubemap")))
    safe(lambda: sc.set_editor_property("intensity", 1.5))
    safe(lambda: sc.recapture_sky())
    spawned.append(sky)
    gcam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0), unreal.Rotator())
    spawned.append(gcam)
    gcc = gcam.get_editor_property("capture_component2d")
    grt = RL.create_render_target2d(world, 2048, 512, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    gcc.set_editor_property("texture_target", grt)
    gcc.set_editor_property("capture_source", SCS.SCS_FINAL_COLOR_LDR)
    gcc.set_editor_property("capture_every_frame", False)
    safe(lambda: gcc.set_editor_property("always_persist_rendering_state", True))
    for prop, val in (("override_custom_near_clipping_plane", True), ("custom_near_clipping_plane", 0.2)):
        safe(lambda prop=prop, val=val: gcc.set_editor_property(prop, val))
    gcc.set_editor_property("post_process_settings", pp)
    gcc.set_editor_property("post_process_blend_weight", 1.0)
    views = []
    for key in ("needle", "heavy"):
        L = 13.0 if key == "needle" else 17.0
        cx = 0.0 if key == "needle" else -0.8697
        tipx = 6.5 if key == "needle" else 7.6303
        fov_side = math.degrees(2 * math.atan(L * 1.06 / 2 / 60.0))
        for lod in (0, 1, 2):
            views.append((f"grey_{key}_side_LOD{lod}", key, lod, (cx, -60.0, 0.0), (cx, 0.0, 0.0), fov_side))
            views.append((f"grey_{key}_tip_LOD{lod}", key, lod, (tipx - 0.9, -4.0, 0.8), (tipx - 0.9, 0.0, 0.0), 22.0))
        views.append((f"grey_{key}_end_LOD0", key, 0, (tipx + 6.0, -0.6, 0.6), (tipx, 0.0, 0.0), 6.0))
    views.append(("grey_heavy_wrap_LOD0", "heavy", 0, (-6.4, -8.0, 2.0), (-6.4, 0.0, 0.0), 40.0))
    for name, key, lod, loc, tgt, fov in views:
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
        comp = a.get_editor_property("static_mesh_component")
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)
        comp.set_static_mesh(meshes[key])
        for i in range(len(meshes[key].get_editor_property("static_materials"))):
            comp.set_material(i, grey)
        comp.set_forced_lod_model(lod + 1)
        gcam.set_actor_location_and_rotation(unreal.Vector(*loc),
                                             ML.find_look_at_rotation(unreal.Vector(*loc), unreal.Vector(*tgt)),
                                             False, False)
        gcc.set_editor_property("fov_angle", float(fov))
        for _ in range(8):
            gcc.capture_scene()
        RL.export_render_target(world, grt, str(RDIR), name + ".png")
        res["grey_shots"].append({"name": name, "lod": lod, "exists": (RDIR / (name + ".png")).exists()})
        EAS.destroy_actor(a)
    res["status"] = "ok"
except Exception:  # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
finally:
    for a in spawned:
        safe(lambda a=a: EAS.destroy_actor(a))
res["hashes_after"] = C.all_hashes()
res["shipped_bytes_unchanged"] = res["hashes_before"] == res["hashes_after"]
res["seconds"] = round(time.time() - res["t0"], 1)
dump()
unreal.log("SV_PASSC2_DONE status=" + str(res.get("status")))
