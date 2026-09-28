"""PASS C (a THIRD fresh process, REAL RHI, offscreen): load what pass A saved (nothing imported or saved) and
  1. render the assembled mesh with the shipped BC/ORM/N (verifier material, both slots) from 7 views, LOD0/1/2 forced;
  2. render Body + PullRing@Pin + Lever@LeverHinge (identity attach) from the same camera as the assembled mesh, for
     a pixel difference; and the "pin pulled + lever opened (+100 pitch)" state;
  3. mip probe: each texture drawn at a fixed mip (3 and 11) into a float render target (EXR) - mip 11 of a full
     2048 chain is 1x1, so the draw must be uniform; a truncated chain clamps to a larger mip and is not;
  4. ListTextures (engine's built format + mip count per texture) into the log.
"""
import json
import os
import sys
import time
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\flashbang\UnrealVerify_claude")
sys.path.insert(0, str(HERE))
import unreal  # noqa: E402
import uv_common as C  # noqa: E402

OUT = HERE / "passC.json"
RDIR = HERE / "renders"
RDIR.mkdir(exist_ok=True)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
ML = unreal.MathLibrary
res = {"engine": unreal.SystemLibrary.get_engine_version(), "dest": C.DEST, "t0": time.time(), "shots": []}


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
    look = unreal.load_asset(f"{C.MATDEST}/M_UV_Look")
    grey = unreal.load_asset(f"{C.MATDEST}/M_UV_Grey")
    res["loaded"] = {k: v is not None for k, v in M.items()}
    res["materials_loaded"] = {"look": look is not None, "grey": grey is not None}
    MEL = unreal.MaterialEditingLibrary
    stats = {}
    for nm, mat in (("look", look), ("grey", grey)):
        MEL.recompile_material(mat)
        st = MEL.get_statistics(mat)  # blocks until the permutation's shaders exist
        stats[nm] = safe(lambda st=st: {"ps": int(st.get_editor_property("num_pixel_shader_instructions")),
                                        "samplers": int(st.get_editor_property("num_samplers"))})
    res["material_stats"] = stats

    # ---------------- mip probe (before any scene work) ----------------
    probe = {}
    for tex in ("BC", "ORM", "N", "Paint_Detail", "Paint_Detail16"):
        for mip in (3, 11):
            mn = f"M_UV_Mip_{tex}_{mip}"
            mat = unreal.load_asset(f"{C.MATDEST}/{mn}")
            rt = RL.create_render_target2d(world, 256, 256, unreal.TextureRenderTargetFormat.RTF_RGBA16F)
            RL.clear_render_target2d(world, rt, unreal.LinearColor(0, 0, 0, 0))
            RL.draw_material_to_render_target(world, rt, mat)
            RL.draw_material_to_render_target(world, rt, mat)
            fname = f"mip_{tex}_{mip}.exr"
            RL.export_render_target(world, rt, str(RDIR), fname)
            probe[mn] = {"file": fname, "exists": (RDIR / fname).exists()}
    res["mip_probe"] = probe
    dump()

    # ---------------- scene ----------------
    for travel, lux in (((-0.55, -0.45, -0.70), 6.0), ((0.6, 0.3, -0.4), 1.6), ((0.2, -0.9, 0.35), 2.2)):
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
    res["sky_cubemap"] = cube.get_path_name() if cube else None
    safe(lambda: sc.set_editor_property("cubemap", cube))
    safe(lambda: sc.set_editor_property("intensity", 0.5))
    safe(lambda: sc.recapture_sky())
    spawned.append(sky)

    PX = 1024
    cam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0), unreal.Rotator())
    spawned.append(cam)
    cc = cam.get_editor_property("capture_component2d")
    rt = RL.create_render_target2d(world, PX, PX, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    cc.set_editor_property("texture_target", rt)
    cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    cc.set_editor_property("capture_every_frame", False)
    cc.set_editor_property("capture_on_movement", False)
    safe(lambda: cc.set_editor_property("always_persist_rendering_state", True))
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
    cc.set_editor_property("fov_angle", 22.0)

    # camera views: (location, look-at, fov). Grenade: axis Z, 16.6 cm tall, ring on +Y, lever on +X.
    VIEWS = {
        "ring_front": ((0.6, 62.0, 8.8), (0.6, 0.0, 8.3), 22.0),
        "lever_side": ((62.0, 0.0, 8.8), (0.0, 0.0, 8.3), 22.0),
        "three_q": ((40.0, 44.0, 22.0), (0.6, 0.2, 8.3), 22.0),
        "back": ((-0.6, -62.0, 8.8), (0.6, 0.0, 8.3), 22.0),
        "top": ((0.3, 0.0, 70.0), (0.6, 0.0, 8.3), 12.0),
        "base": ((0.3, 0.0, -55.0), (0.3, 0.0, 0.0), 12.0),
        "fuze_close": ((14.0, 18.0, 21.0), (1.0, 0.0, 14.5), 22.0),
        "hole_macro": ((0.0, 24.0, 7.0), (0.0, 0.0, 7.0), 14.0),
    }

    def aim(view):
        loc, tgt, fov = VIEWS[view]
        rot = ML.find_look_at_rotation(unreal.Vector(*loc), unreal.Vector(*tgt))
        cam.set_actor_location_and_rotation(unreal.Vector(*loc), rot, False, False)
        cc.set_editor_property("fov_angle", float(fov))

    def place(mesh, mat, lod=0, loc=(0, 0, 0)):
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), unreal.Rotator())
        c = a.get_editor_property("static_mesh_component")
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_static_mesh(mesh)
        for i in range(len(mesh.get_editor_property("static_materials"))):
            c.set_material(i, mat)
        c.set_forced_lod_model(lod + 1 if lod is not None else 0)
        return a, c

    def shoot(name, view, actors, info=None):
        aim(view)
        for _ in range(4):
            cc.capture_scene()
        RL.export_render_target(world, rt, str(RDIR), name + ".png")
        rec = {"name": name, "view": view, "file": name + ".png", "exists": (RDIR / (name + ".png")).exists()}
        rec.update(info or {})
        res["shots"].append(rec)
        for a in actors:
            EAS.destroy_actor(a)
        dump()

    # 1) assembled, shipped maps, every view at LOD0
    for view in VIEWS:
        a, _ = place(M["SM_Flashbang"], look)
        shoot(f"asm_look_{view}", view, [a])
    # LOD1 / LOD2 forced
    for lod in (1, 2):
        for view in ("three_q", "ring_front"):
            a, _ = place(M["SM_Flashbang"], look, lod)
            shoot(f"asm_look_{view}_LOD{lod}", view, [a], {"forced_lod": lod})
    # shape only
    for view in ("three_q", "fuze_close", "base"):
        a, _ = place(M["SM_Flashbang"], grey)
        shoot(f"asm_grey_{view}", view, [a])

    # 2) Body + parts attached at sockets, identity
    def parts(pulled=False, opened=False, mat=look, lod=0):
        b, bc = place(M["SM_Flashbang_Body"], mat, lod)
        acts = [b]
        out = {}
        for part, sock in (("SM_Flashbang_PullRing", "Pin"), ("SM_Flashbang_Lever", "LeverHinge")):
            p, pc = place(M[part], mat, lod)
            pc.attach_to_component(bc, sock, unreal.AttachmentRule.SNAP_TO_TARGET,
                                   unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.KEEP_WORLD, False)
            if pulled and part == "SM_Flashbang_PullRing":
                trav = C.sidecar("SM_Flashbang")["parts"]["PullRing"]["pin_travel_mm"] / 10.0
                pc.set_relative_location(unreal.Vector(trav, 0, 0), False, False)
            if opened and part == "SM_Flashbang_Lever":
                pc.set_relative_rotation(unreal.Rotator(roll=0.0, pitch=100.0, yaw=0.0), False, False)
            w = pc.get_world_transform()
            out[part] = {"world_t": C.vec(w.translation),
                         "world_rpy": [w.rotation.rotator().roll, w.rotation.rotator().pitch, w.rotation.rotator().yaw]}
            acts.append(p)
        return acts, out

    for view in ("three_q", "ring_front", "lever_side", "fuze_close"):
        acts, out = parts()
        shoot(f"parts_look_{view}", view, acts, {"attach": out})
    for view in ("fuze_close", "three_q"):
        acts, out = parts(mat=grey)
        shoot(f"parts_grey_{view}", view, acts, {"attach": out})
    for view in ("ring_front", "lever_side", "three_q"):
        acts, out = parts(pulled=True, opened=True)
        shoot(f"parts_pulled_open_{view}", view, acts, {"attach": out})

    # 3) textures as the engine built them
    unreal.log("UV_LISTTEXTURES_BEGIN")
    unreal.SystemLibrary.execute_console_command(world, "ListTextures")
    unreal.log("UV_LISTTEXTURES_END")
    res["tex_memory"] = {n: safe(lambda n=n: int(unreal.load_asset(f"{C.TEXDEST}/{n}").blueprint_get_memory_size()))
                         for n in C.TEXTURES}
    res["status"] = "ok"
except Exception:  # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
finally:
    for a in spawned:
        safe(lambda a=a: EAS.destroy_actor(a))
res["seconds"] = round(time.time() - res["t0"], 1)
dump()
unreal.log("UV_PASSC_DONE status=" + str(res.get("status")))
