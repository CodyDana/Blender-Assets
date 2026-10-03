"""PASS C1 (a THIRD fresh process, REAL RHI, offscreen): load what pass A saved (nothing imported, nothing saved) and
  1. mip probes: every texture drawn at a fixed mip (3 and the LAST mip of a full chain) into a float RT (EXR);
     the last mip of a full chain is 1 texel wide, so its draw must be uniform;
  2. ListTextures (the engine's built pixel format + NumMips per texture) into the log, and in-memory sizes;
  3. lit look frames with the shipped BC/ORM/N (verifier materials): side / three-quarter / tip close-ups at
     LOD0 and LOD1/LOD2 forced, a family frame with the pack's SM_Shuriken_Spike (read-only), and lit frames of
     each needle against a grey backdrop at the LOD switch distances (1920x1080, 90 deg horizontal FOV).
"""
import json
import math
import sys
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\senbon\UnrealVerify")
sys.path.insert(0, str(HERE))
import unreal  # noqa: E402
import sv_common as C  # noqa: E402

OUT = HERE / "passC1.json"
RDIR = HERE / "renders"
RDIR.mkdir(exist_ok=True)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
ML = unreal.MathLibrary
MEL = unreal.MaterialEditingLibrary
res = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "t0": time.time(), "shots": [],
       "hashes_before": C.all_hashes()}
SPIKE = "/Game/NinjaPack/Meshes/SM_Shuriken_Spike"


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:300]}


def dump():
    OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")


spawned = []
try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    M = {n: unreal.load_asset(f"{C.DEST}/{n}") for n in C.MESHES}
    LOOK = {k: unreal.load_asset(f"{C.MATDEST}/M_SV_Look_{k}") for k in ("Needle", "Heavy", "Heavy_Wrap")}
    res["loaded"] = {k: v is not None for k, v in M.items()}
    res["materials_loaded"] = {k: v is not None for k, v in LOOK.items()}
    stats = {}
    for nm, mat in LOOK.items():
        MEL.recompile_material(mat)
        st = MEL.get_statistics(mat)
        stats[nm] = safe(lambda st=st: {"ps": int(st.get_editor_property("num_pixel_shader_instructions")),
                                        "samplers": int(st.get_editor_property("num_samplers"))})
    res["material_stats"] = stats
    spike = unreal.load_asset(SPIKE)
    res["spike_loaded"] = spike is not None

    # ---------------- 1) mip probes ----------------
    probe = {}
    for tname in C.TEXTURES:
        short = tname.replace("T_Senbon_", "")
        last = 10 if "Wrap" in tname else 11
        for mip in (3, last):
            mn = f"M_SV_Mip_{short}_{mip}"
            mat = unreal.load_asset(f"{C.MATDEST}/{mn}")
            MEL.recompile_material(mat)
            MEL.get_statistics(mat)
            rt = RL.create_render_target2d(world, 256, 32, unreal.TextureRenderTargetFormat.RTF_RGBA16F)
            RL.clear_render_target2d(world, rt, unreal.LinearColor(0, 0, 0, 0))
            RL.draw_material_to_render_target(world, rt, mat)
            RL.draw_material_to_render_target(world, rt, mat)
            fname = f"mip_{short}_{mip}.exr"
            RL.export_render_target(world, rt, str(RDIR), fname)
            probe[mn] = {"file": fname, "exists": (RDIR / fname).exists()}
    res["mip_probe"] = probe
    dump()

    # ---------------- 2) textures as the engine built them ----------------
    unreal.log("SV_LISTTEXTURES_BEGIN")
    unreal.SystemLibrary.execute_console_command(world, "ListTextures")
    unreal.log("SV_LISTTEXTURES_END")
    res["tex_memory"] = {n: safe(lambda n=n: int(unreal.load_asset(f"{C.TEXDEST}/{n}").blueprint_get_memory_size()))
                         for n in C.TEXTURES}
    dump()

    # ---------------- 3) lit frames ----------------
    for travel, lux in (((-0.55, 0.45, -0.70), 6.0), ((0.6, 0.3, -0.4), 1.6), ((0.2, -0.9, 0.35), 2.2)):
        la = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 300),
                                        ML.make_rot_from_x(unreal.Vector(*travel)))
        lc = la.get_editor_property("directional_light_component")
        lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        lc.set_editor_property("intensity", lux)
        safe(lambda: lc.set_editor_property("atmosphere_sun_light", False))
        spawned.append(la)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 300), unreal.Rotator())
    sc = sky.get_editor_property("light_component")
    safe(lambda: sc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE))
    safe(lambda: sc.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP))
    cube = unreal.load_asset("/Engine/MapTemplates/Sky/DaylightAmbientCubemap")
    safe(lambda: sc.set_editor_property("cubemap", cube))
    safe(lambda: sc.set_editor_property("intensity", 0.6))
    safe(lambda: sc.recapture_sky())
    spawned.append(sky)

    def make_cam(w, h):
        cam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0), unreal.Rotator())
        cc = cam.get_editor_property("capture_component2d")
        rt = RL.create_render_target2d(world, w, h, unreal.TextureRenderTargetFormat.RTF_RGBA8)
        cc.set_editor_property("texture_target", rt)
        cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        cc.set_editor_property("capture_every_frame", False)
        cc.set_editor_property("capture_on_movement", False)
        safe(lambda: cc.set_editor_property("always_persist_rendering_state", True))
        for prop, val in (("override_custom_near_clipping_plane", True), ("custom_near_clipping_plane", 0.2)):
            safe(lambda prop=prop, val=val: cc.set_editor_property(prop, val))
        pp = cc.get_editor_property("post_process_settings")
        for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                     ("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.5),
                     ("override_auto_exposure_apply_physical_camera_exposure", True),
                     ("auto_exposure_apply_physical_camera_exposure", False),
                     ("override_motion_blur_amount", True), ("motion_blur_amount", 0.0),
                     ("override_bloom_intensity", True), ("bloom_intensity", 0.0),
                     ("override_vignette_intensity", True), ("vignette_intensity", 0.0)):
            safe(lambda k=k, v=v: pp.set_editor_property(k, v))
        cc.set_editor_property("post_process_settings", pp)
        cc.set_editor_property("post_process_blend_weight", 1.0)
        spawned.append(cam)
        return cam, cc, rt

    def place(mesh, mats, lod=None, loc=(0, 0, 0), rot=None):
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), rot or unreal.Rotator())
        c = a.get_editor_property("static_mesh_component")
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_static_mesh(mesh)
        for i, m in enumerate(mats):
            if m is not None:
                c.set_material(i, m)
        c.set_forced_lod_model(0 if lod is None else lod + 1)
        return a, c

    def mats_for(name):
        return [LOOK["Needle"]] if name == "SM_Senbon_Needle" else [LOOK["Heavy"], LOOK["Heavy_Wrap"]]

    def shoot(cam, cc, rt, name, loc, tgt, fov, actors, info=None, n=8):
        rot = ML.find_look_at_rotation(unreal.Vector(*loc), unreal.Vector(*tgt))
        cam.set_actor_location_and_rotation(unreal.Vector(*loc), rot, False, False)
        cc.set_editor_property("fov_angle", float(fov))
        for _ in range(n):
            cc.capture_scene()
        RL.export_render_target(world, rt, str(RDIR), name + ".png")
        rec = {"name": name, "file": name + ".png", "exists": (RDIR / (name + ".png")).exists(),
               "cam": list(loc), "target": list(tgt), "fov": fov}
        rec.update(info or {})
        res["shots"].append(rec)
        for a in actors:
            EAS.destroy_actor(a)
        dump()

    cam, cc, rt = make_cam(2048, 768)
    for name in C.MESHES:
        short = name.replace("SM_Senbon_", "").lower()
        L = 13.0 if short == "needle" else 17.0
        cx = 0.0 if short == "needle" else -0.8697
        # side (camera on -Y looking +Y), fitted to the length; fov for a 2048-wide frame with 8 % margin
        d = 60.0
        fov = math.degrees(2 * math.atan(L * 1.08 / 2 / d))
        for lod in (0, 1, 2):
            a, _ = place(M[name], mats_for(name), lod)
            shoot(cam, cc, rt, f"{short}_side_LOD{lod}", (cx, -d, 0.0), (cx, 0.0, 0.0), fov, [a], {"forced_lod": lod})
        a, _ = place(M[name], mats_for(name), 0)
        shoot(cam, cc, rt, f"{short}_threeq_LOD0", (cx + 25.0, -40.0, 22.0), (cx, 0.0, 0.0), fov * 1.1, [a])
        # tip close-up at LOD0 (tip at +X); and the butt/wrap for the heavy
        tipx = 6.5 if short == "needle" else 7.6303
        a, _ = place(M[name], mats_for(name), 0)
        shoot(cam, cc, rt, f"{short}_tip_close_LOD0", (tipx - 1.2, -6.0, 1.6), (tipx - 1.2, 0.0, 0.0), 30.0, [a])
        if short == "heavy":
            a, _ = place(M[name], mats_for(name), 0)
            shoot(cam, cc, rt, "heavy_wrap_close_LOD0", (-6.4, -9.0, 2.5), (-6.4, 0.0, 0.0), 40.0, [a])
            for lod in (1, 2):
                a, _ = place(M[name], mats_for(name), lod)
                shoot(cam, cc, rt, f"heavy_tip_close_LOD{lod}", (tipx - 1.2, -6.0, 1.6), (tipx - 1.2, 0.0, 0.0), 30.0,
                      [a], {"forced_lod": lod})
    # family: needle, heavy, spike (pack asset, its own materials), stacked in Z
    acts = []
    a, _ = place(M["SM_Senbon_Needle"], mats_for("SM_Senbon_Needle"), 0, loc=(0.0, 0.0, 2.0))
    acts.append(a)
    a, _ = place(M["SM_Senbon_Heavy"], mats_for("SM_Senbon_Heavy"), 0, loc=(0.0, 0.0, 0.0))
    acts.append(a)
    if spike is not None:
        a, _ = place(spike, [], 0, loc=(0.0, 0.0, -2.4))
        acts.append(a)
    shoot(cam, cc, rt, "family_side", (0.0, -75.0, 0.0), (0.0, 0.0, 0.0), 15.0, acts)
    EAS.destroy_actor(cam)
    spawned.remove(cam)

    # lit frames at the switch distances, 1920x1080, 90 deg H-FOV, engine-picked LOD, grey backdrop 40 cm behind
    cam, cc, rt = make_cam(1920, 1080)
    plane = unreal.load_asset("/Engine/BasicShapes/Cube")
    grey = unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial")
    for name in C.MESHES + (["SPIKE"] if spike is not None else []):
        mesh = spike if name == "SPIKE" else M[name]
        short = "spike" if name == "SPIKE" else name.replace("SM_Senbon_", "").lower()
        for dm in (0.5, 0.889, 2.54, 5.0):
            d = dm * 100.0
            a, _ = place(mesh, [] if name == "SPIKE" else mats_for(name), None)
            bd = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 45.0, 0), unreal.Rotator())
            bc = bd.get_editor_property("static_mesh_component")
            bc.set_static_mesh(plane)
            bc.set_material(0, grey)
            bd.set_actor_scale3d(unreal.Vector(20.0, 0.1, 20.0))
            shoot(cam, cc, rt, f"dist_lit_{short}_{dm:.3f}m", (0.0, -d, 0.0), (0.0, 0.0, 0.0), 90.0, [a, bd],
                  {"distance_m": dm, "auto_lod": True}, n=16)
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
unreal.log("SV_PASSC1_DONE status=" + str(res.get("status")))
