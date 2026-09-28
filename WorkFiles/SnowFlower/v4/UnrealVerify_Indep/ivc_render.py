"""INDEPENDENT pass C (a THIRD fresh UnrealEditor-Cmd with a real RHI, -RenderOffscreen): load the saved assets,
attach the sword to the sheath's Holster socket in the editor world, and render with the engine:
  - beauty captures (shipped maps through plain preview materials, assigned on the COMPONENTS only)
  - scene-depth captures of the sheath alone and the sword alone from the same ortho cameras (+Y, -Y, +X, -X)
    for a render-based containment test done offline (ivd_depth.py)
Also reads texture memory sizes after the textures are built with a real RHI.  Nothing is saved.
"""
import json, math, os, time, traceback
from pathlib import Path
import unreal

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealVerify_Indep")
RDIR = HERE / "renders"
RDIR.mkdir(parents=True, exist_ok=True)
DEST = os.environ["IV_DEST"]
OUT = HERE / "ivC_render.json"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
ML = unreal.MathLibrary
res = {"dest": DEST, "t0": time.time()}


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:300]}


def dump():
    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


spawned = []
try:
    sword = unreal.load_asset(f"{DEST}/SM_SnowFlower")
    sheath = unreal.load_asset(f"{DEST}/SM_SnowFlower_Sheath")
    for m in (sword, sheath):  # force the async static-mesh build to finish BEFORE any component uses the mesh,
        m.get_bounding_box(); m.get_num_triangles(0)  # otherwise the components never get a render state (no tick in a commandlet)
    MEL = unreal.MaterialEditingLibrary
    mats = {}
    for n in ("M_IV_SF_Steel", "M_IV_SF_Wrap", "M_IV_SF_Sheath"):
        m = unreal.load_asset(f"{DEST}/Materials/{n}")
        MEL.recompile_material(m)
        mats[n] = m
    for cmd in ("Editor.AsyncTextureCompilation 0", "r.TextureStreaming 0"):
        unreal.SystemLibrary.execute_console_command(None, cmd)
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    # textures after a real-RHI build
    tex = {}
    for p in unreal.EditorAssetLibrary.list_assets(DEST + "/Textures", recursive=False, include_folder=False):
        t = unreal.load_asset(str(p).split(".")[0])
        d = {}
        d["memory_bytes"] = safe(lambda: int(t.blueprint_get_memory_size()))
        safe(lambda: t.set_editor_property("never_stream", True))
        safe(lambda: t.update_resource())
        d["memory_bytes_after_update"] = safe(lambda: int(t.blueprint_get_memory_size()))
        d["size"] = [int(t.blueprint_get_size_x()), int(t.blueprint_get_size_y())]
        ad = ar.get_asset_by_object_path(f"{DEST}/Textures/{t.get_name()}.{t.get_name()}")
        d["registry_tags"] = {k: str(safe(lambda k=k: ad.get_tag_value(k))) for k in ("Dimensions", "Format", "HasAlphaChannel", "SRGB", "CompressionSettings", "MipGenSettings", "LODGroup", "NumMips", "ResourceSize")}
        tex[t.get_name()] = d
    res["textures_runtime"] = tex
    dump()

    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for travel, lux in (((0.35, -0.55, -0.75), 6.0), ((-0.6, 0.5, 0.4), 2.5), ((0.1, 0.8, -0.2), 2.0)):
        la = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 100), ML.make_rot_from_x(unreal.Vector(*travel)))
        lc = la.get_editor_property("directional_light_component")
        lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        lc.set_editor_property("intensity", lux)
        safe(lambda: lc.set_editor_property("atmosphere_sun_light", False))
        spawned.append(la)

    def mesh_actor(mesh, loc=(0, 0, 0)):
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), unreal.Rotator())
        c = a.get_editor_property("static_mesh_component")
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_static_mesh(mesh)
        c.set_forced_lod_model(1)  # LOD0 forced for measurement renders
        safe(lambda: c.set_editor_property("forced_lod_model", 1))
        spawned.append(a)
        return a, c

    a_sh, c_sh = mesh_actor(sheath)
    a_sw, c_sw = mesh_actor(sword, (50, 50, 50))
    c_sw.attach_to_component(c_sh, "Holster", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                             unreal.AttachmentRule.SNAP_TO_TARGET, False)
    res["sword_world"] = {"t": [c_sw.get_world_location().x, c_sw.get_world_location().y, c_sw.get_world_location().z],
                          "rpy": (lambda r: [r.roll, r.pitch, r.yaw])(c_sw.get_world_rotation())}
    a_sw2, c_sw2 = mesh_actor(sword, (14.0, 0, -31.6571))  # a drawn copy beside, for the look renders

    def dress(beauty):
        if beauty:
            # look-match verify 2026-09-27: slots are assigned BY NAME (the sword now ships Blade / Fittings / Grip:
            # the Grip reads the Wrap atlas, Blade and Fittings the Steel atlas)
            sw_slots = [str(s.material_slot_name) for s in sword.get_editor_property("static_materials")]
            res["sword_slots_dressed"] = {}
            for i, sn in enumerate(sw_slots):
                m = mats["M_IV_SF_Wrap"] if ("Grip" in sn or "Wrap" in sn) else mats["M_IV_SF_Steel"]
                c_sw.set_material(i, m); c_sw2.set_material(i, m)
                res["sword_slots_dressed"][sn] = m.get_name()
            for i in range(len(sheath.get_editor_property("static_materials"))):
                c_sh.set_material(i, mats["M_IV_SF_Sheath"])

    dress(True)

    def camera(px_w, px_h, fmt, src):
        cam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 100), unreal.Rotator())
        spawned.append(cam)
        cc = cam.get_editor_property("capture_component2d")
        rt = RL.create_render_target2d(w, px_w, px_h, fmt)
        cc.set_editor_property("texture_target", rt)
        cc.set_editor_property("capture_source", src)
        cc.set_editor_property("capture_every_frame", False)
        cc.set_editor_property("capture_on_movement", False)
        safe(lambda: cc.set_editor_property("always_persist_rendering_state", True))
        pp = cc.get_editor_property("post_process_settings")
        for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                     ("override_auto_exposure_bias", True), ("auto_exposure_bias", 2.5),
                     ("override_auto_exposure_apply_physical_camera_exposure", True), ("auto_exposure_apply_physical_camera_exposure", False),
                     ("override_motion_blur_amount", True), ("motion_blur_amount", 0.0),
                     ("override_bloom_intensity", True), ("bloom_intensity", 0.0),
                     ("override_vignette_intensity", True), ("vignette_intensity", 0.0)):
            safe(lambda k=k, v=v: pp.set_editor_property(k, v))
        cc.set_editor_property("post_process_settings", pp)
        cc.set_editor_property("post_process_blend_weight", 1.0)
        return cam, cc, rt

    def aim(cam, cc, loc, fwd, up, ortho_w=None, fov=None):
        cam.set_actor_location_and_rotation(unreal.Vector(*loc), ML.make_rot_from_xz(unreal.Vector(*fwd), unreal.Vector(*up)), False, False)
        if ortho_w is not None:
            cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
            cc.set_editor_property("ortho_width", float(ortho_w))
            safe(lambda: cc.set_editor_property("auto_calculate_ortho_planes", False))
        else:
            cc.set_editor_property("projection_type", unreal.CameraProjectionMode.PERSPECTIVE)
            cc.set_editor_property("fov_angle", float(fov))

    ALLC = {"sheath": c_sh, "sword": c_sw, "sword2": c_sw2}

    def show_only(cc, names):
        for n, c in ALLC.items():
            c.set_visibility(n in names, False)

    shots = []
    # ---- depth captures: tall ortho strips covering z -24 .. 88 (sheath local = world, sheath at identity)
    DW, DH = 320, 2240
    ZC, OW = 32.0, 16.0  # centre z, ortho width (cm) -> vertical 112 cm, 0.05 cm/px
    fmt32 = getattr(unreal.TextureRenderTargetFormat, "RTF_RGBA32F", unreal.TextureRenderTargetFormat.RTF_RGBA16F)
    dcam, dcc, drt = camera(DW, DH, fmt32, unreal.SceneCaptureSource.SCS_SCENE_DEPTH)
    DVIEWS = {"py": ((0, 25, ZC), (0, -1, 0)), "ny": ((0, -25, ZC), (0, 1, 0)),
              "px": ((25, 0, ZC), (-1, 0, 0)), "nx": ((-25, 0, ZC), (1, 0, 0))}
    for vn, (loc, fwd) in DVIEWS.items():
        aim(dcam, dcc, loc, fwd, (0, 0, 1), ortho_w=OW)
        for who in ("sheath", "sword"):
            show_only(dcc, [who])
            for _ in range(2):
                dcc.capture_scene()
            name = f"depth_{vn}_{who}"
            RL.export_render_target(w, drt, str(RDIR), name + ".exr")
            shots.append({"name": name, "view": vn, "loc": loc, "fwd": fwd, "ortho_w": OW, "px": [DW, DH], "zc": ZC})
    res["depth_shots"] = shots
    dump()

    # ---- beauty
    bcam, bcc, brt = camera(1024, 1536, unreal.TextureRenderTargetFormat.RTF_RGBA8, unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    show_only(bcc, ["sheath", "sword", "sword2"])
    BVIEWS = {
        "beauty_front_pair": dict(loc=(7, 90, 22), fwd=(0, -1, 0), up=(0, 0, 1), ortho_w=85.0),
        "beauty_back_pair": dict(loc=(7, -90, 22), fwd=(0, 1, 0), up=(0, 0, 1), ortho_w=85.0),
        "beauty_persp34": dict(loc=(-70, 95, 5), fwd=(0.55, -0.83, 0.12), up=(0, 0, 1), fov=55.0),
        "beauty_mouth_close": dict(loc=(-14, 24, -30), fwd=(0.45, -0.85, 0.28), up=(0, 0, 1), fov=40.0),
        "beauty_chape_close": dict(loc=(-10, 26, 70), fwd=(0.35, -0.9, 0.2), up=(0, 0, 1), fov=40.0),
    }
    for name, v in BVIEWS.items():
        aim(bcam, bcc, v["loc"], v["fwd"], v["up"], ortho_w=v.get("ortho_w"), fov=v.get("fov"))
        for _ in range(4):
            bcc.capture_scene()
        RL.export_render_target(w, brt, str(RDIR), name + ".png")
        shots.append({"name": name, **v})
    res["shots"] = shots
    res["status"] = "ok"
except Exception:  # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
finally:
    for a in spawned:
        safe(lambda a=a: EAS.destroy_actor(a))
res["seconds"] = round(time.time() - res["t0"], 1)
dump()
unreal.log("IV_PASS_C_DONE status=" + res["status"])
