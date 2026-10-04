"""INDEPENDENT pass C (a THIRD fresh UnrealEditor-Cmd with a real RHI, -RenderOffscreen): load what pass A saved
(nothing imported, nothing saved), and
  1. ListTextures into the log (the engine's BUILT pixel format + NumMips per texture) and in-memory sizes;
  2. attach the katana to the saya's Holster socket at an arbitrary saya world transform (as in pass B), then
     scene-depth captures of the saya alone and the katana alone from the same ortho cameras (+Y, -Y, +X, -X) in the
     SAYA's local frame, for the render-based containment test done offline (kvD_depth.py);
  3. beauty captures with the shipped BC/ORM/N through plain preview materials assigned on the COMPONENTS only:
     sheathed pair + a drawn katana beside it, mouth and kurikata close-ups, and forced LOD0/1/2 strips.
Adapted copy of WorkFiles/SnowFlower/v4/UnrealVerify_Final/ivc_render.py.
"""
import json, sys, time, traceback
sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\katana\UnrealVerify_Final")
import unreal  # noqa: E402
import kv_common as C  # noqa: E402

DEST = C.dest()
RDIR = C.HERE / "renders"
RDIR.mkdir(parents=True, exist_ok=True)
OUT = C.HERE / "kvC_render.json"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
ML = unreal.MathLibrary
res = {"dest": DEST, "t0": time.time(), "hashes_before": C.all_hashes()}
safe = C.safe


def dump():
    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


spawned = []
try:
    kat = unreal.load_asset(f"{DEST}/SM_Katana")
    saya = unreal.load_asset(f"{DEST}/SM_Katana_Saya")
    for m in (kat, saya):  # force the async static-mesh build before any component uses the mesh
        m.get_bounding_box(); m.get_num_triangles(0)
    MEL = unreal.MaterialEditingLibrary
    mats = {}
    for a in ("Steel", "Grip", "Saya"):
        m = unreal.load_asset(f"{DEST}/Materials/M_KV_{a}")
        MEL.recompile_material(m)
        mats[a] = m
    for cmd in ("Editor.AsyncTextureCompilation 0", "r.TextureStreaming 0"):
        unreal.SystemLibrary.execute_console_command(None, cmd)
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

    tex = {}
    for p in unreal.EditorAssetLibrary.list_assets(DEST + "/Textures", recursive=False, include_folder=False):
        t = unreal.load_asset(str(p).split(".")[0])
        safe(lambda: t.set_editor_property("never_stream", True))  # in memory only, never saved
        safe(lambda: t.update_resource())
        tex[t.get_name()] = {"memory_bytes": safe(lambda: int(t.blueprint_get_memory_size())),
                             "size": [int(t.blueprint_get_size_x()), int(t.blueprint_get_size_y())]}
    res["textures_runtime"] = tex
    unreal.log("KV_LISTTEXTURES_BEGIN")
    unreal.SystemLibrary.execute_console_command(w, "ListTextures")
    unreal.log("KV_LISTTEXTURES_END")
    dump()

    for travel, lux in (((0.35, -0.55, -0.75), 6.0), ((-0.6, 0.5, 0.4), 2.5), ((0.1, 0.8, -0.2), 2.0)):
        la = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 100), ML.make_rot_from_x(unreal.Vector(*travel)))
        lc = la.get_editor_property("directional_light_component")
        lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        lc.set_editor_property("intensity", lux)
        safe(lambda: lc.set_editor_property("atmosphere_sun_light", False))
        spawned.append(la)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 300), unreal.Rotator())
    sc = sky.get_editor_property("light_component")
    safe(lambda: sc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE))
    safe(lambda: sc.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP))
    safe(lambda: sc.set_editor_property("cubemap", unreal.load_asset("/Engine/MapTemplates/Sky/DaylightAmbientCubemap")))
    safe(lambda: sc.set_editor_property("intensity", 1.0))
    safe(lambda: sc.recapture_sky())
    spawned.append(sky)

    def mesh_actor(mesh, loc=(0, 0, 0), rot=None, lod=0):
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), rot or unreal.Rotator())
        c = a.get_editor_property("static_mesh_component")
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_static_mesh(mesh)
        c.set_forced_lod_model(lod + 1)
        spawned.append(a)
        return a, c

    # the saya at an arbitrary world transform; every capture is placed in the saya's local frame
    srot = unreal.Rotator(); srot.roll, srot.pitch, srot.yaw = 17.0, -23.0, 41.0
    a_sh, c_sh = mesh_actor(saya, (123.4, -56.7, 89.0), srot)
    a_sw, c_sw = mesh_actor(kat, (50, 50, 50))
    ok = c_sw.attach_to_component(c_sh, "Holster", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                                  unreal.AttachmentRule.SNAP_TO_TARGET, False)
    W_sh = c_sh.get_world_transform()
    res["attach_ok"] = bool(ok)
    res["katana_in_saya_origin_cm"] = (lambda v: [v.x, v.y, v.z])(W_sh.inverse_transform_location(c_sw.get_world_location()))
    # a drawn katana beside the saya (saya-local +X 14 cm), for the look renders
    a_dr, c_dr = mesh_actor(kat)
    a_dr.set_actor_transform(ML.compose_transforms(unreal.Transform(unreal.Vector(14.0, 0, -13.83), unreal.Rotator(), unreal.Vector(1, 1, 1)), W_sh), False, False)

    def L(p):  # saya-local -> world
        return W_sh.transform_location(unreal.Vector(*p))

    def D(d):
        return W_sh.transform_direction(unreal.Vector(*d))

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
                     ("override_auto_exposure_bias", True), ("auto_exposure_bias", 2.0),
                     ("override_auto_exposure_apply_physical_camera_exposure", True), ("auto_exposure_apply_physical_camera_exposure", False),
                     ("override_motion_blur_amount", True), ("motion_blur_amount", 0.0),
                     ("override_bloom_intensity", True), ("bloom_intensity", 0.0),
                     ("override_vignette_intensity", True), ("vignette_intensity", 0.0)):
            safe(lambda k=k, v=v: pp.set_editor_property(k, v))
        cc.set_editor_property("post_process_settings", pp)
        cc.set_editor_property("post_process_blend_weight", 1.0)
        return cam, cc, rt

    def aim(cam, cc, loc, fwd, up, ortho_w=None, fov=None):
        cam.set_actor_location_and_rotation(L(loc), ML.make_rot_from_xz(D(fwd), D(up)), False, False)
        if ortho_w is not None:
            cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
            cc.set_editor_property("ortho_width", float(ortho_w))
            safe(lambda: cc.set_editor_property("auto_calculate_ortho_planes", False))
        else:
            cc.set_editor_property("projection_type", unreal.CameraProjectionMode.PERSPECTIVE)
            cc.set_editor_property("fov_angle", float(fov))

    ALLC = {"saya": c_sh, "katana": c_sw, "drawn": c_dr}

    def show_only(names):
        for n, c in ALLC.items():
            c.set_visibility(n in names, False)

    # a mid-grey backdrop card behind each beauty view (the lacquer is near-black: without it the saya vanishes)
    pm = unreal.load_asset("/Engine/BasicShapes/Plane")
    res["backdrop_mesh_loaded"] = pm is not None
    pm.get_bounding_box()
    bd, bdc = mesh_actor(pm)
    bdc.set_forced_lod_model(0)
    # transient unlit grey card material (created in memory, never saved)
    bdm = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_KV_Backdrop_Transient", f"{DEST}/Transient", unreal.Material, unreal.MaterialFactoryNew())
    bdm.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    safe(lambda: bdm.set_editor_property("two_sided", True))
    _c = MEL.create_material_expression(bdm, unreal.MaterialExpressionConstant3Vector, -300, 0)
    _c.set_editor_property("constant", unreal.LinearColor(0.16, 0.16, 0.17, 1.0))
    MEL.connect_material_property(_c, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(bdm)
    res["backdrop_material_stats"] = safe(lambda: str(MEL.get_statistics(bdm)))  # forces the shader map to finish
    res["backdrop_material_loaded"] = bdm is not None
    res["backdrop_set_material"] = safe(lambda: bdc.set_material(0, bdm))
    res["backdrop_bounds"] = []
    ALLC["backdrop"] = bdc

    def dress():
        for c in (c_sw, c_dr):
            for i, s in enumerate(kat.get_editor_property("static_materials")):
                c.set_material(i, mats["Grip"] if "Grip" in str(s.material_slot_name) else mats["Steel"])
        for i in range(len(saya.get_editor_property("static_materials"))):
            c_sh.set_material(i, mats["Saya"])

    shots = []
    # ---- depth captures: tall ortho strips covering saya-local z -10 .. 66 at 0.05 cm/px
    DW, DH = 300, 1520
    ZC, OW = 28.0, 15.0
    fmt32 = getattr(unreal.TextureRenderTargetFormat, "RTF_RGBA32F", unreal.TextureRenderTargetFormat.RTF_RGBA16F)
    dcam, dcc, drt = camera(DW, DH, fmt32, unreal.SceneCaptureSource.SCS_SCENE_DEPTH)
    DVIEWS = {"py": ((3.5, 25, ZC), (0, -1, 0)), "ny": ((3.5, -25, ZC), (0, 1, 0)),
              "px": ((30, 0, ZC), (-1, 0, 0)), "nx": ((-25, 0, ZC), (1, 0, 0))}
    for vn, (loc, fwd) in DVIEWS.items():
        aim(dcam, dcc, loc, fwd, (0, 0, 1), ortho_w=OW)
        for who in ("saya", "katana"):
            show_only([who])
            for _ in range(2):
                dcc.capture_scene()
            name = f"depth_{vn}_{who}"
            RL.export_render_target(w, drt, str(RDIR), name + ".exr")
            shots.append({"name": name, "view": vn, "loc": loc, "fwd": fwd, "ortho_w": OW, "px": [DW, DH], "zc": ZC})
    res["depth_shots"] = shots
    dump()

    # ---- beauty (component-only preview materials)
    dress()
    bcam, bcc, brt = camera(1600, 1600, unreal.TextureRenderTargetFormat.RTF_RGBA8, unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    BVIEWS = {
        "beauty_side_pair": dict(loc=(7, -120, 14), fwd=(0, 1, 0), up=(0, 0, 1), ortho_w=105.0, show=["saya", "katana", "drawn"]),
        "beauty_persp34": dict(loc=(-60, -95, -20), fwd=(0.5, 0.84, 0.2), up=(0, 0, 1), fov=55.0, show=["saya", "katana", "drawn"]),
        "beauty_mouth_close": dict(loc=(-11, -22, -24), fwd=(0.42, 0.82, 0.38), up=(0, 0, 1), fov=40.0, show=["saya", "katana"]),
        "beauty_kurikata_close": dict(loc=(-4, 22, -10), fwd=(0.2, -0.95, 0.25), up=(0, 0, 1), fov=40.0, show=["saya", "katana"]),
        "beauty_kojiri_close": dict(loc=(-6, -24, 70), fwd=(0.38, 0.9, -0.15), up=(0, 0, 1), fov=40.0, show=["saya", "katana"]),
    }

    def place_backdrop(v):
        import math as _m
        f = v["fwd"]; nrm = _m.sqrt(sum(x * x for x in f)); f = [x / nrm for x in f]
        dist = 150.0 if v.get("ortho_w") or v.get("fov", 0) > 50 else 45.0
        c = [v["loc"][i] + f[i] * dist for i in range(3)]
        bd.set_actor_location_and_rotation(L(c), ML.make_rot_from_z(D([-x for x in f])), False, False)
        bd.set_actor_scale3d(unreal.Vector(6, 6, 1))
        res["backdrop_bounds"].append(safe(lambda: [v3x for v3x in [(lambda q: [q.x, q.y, q.z])(x) for x in bd.get_actor_bounds(False)]]))

    # debug: the backdrop alone, side-pair view, and a sphere-free check of the card's render state
    v = BVIEWS["beauty_side_pair"]
    show_only(["backdrop"])
    place_backdrop(v)
    aim(bcam, bcc, v["loc"], v["fwd"], v["up"], ortho_w=v.get("ortho_w"), fov=v.get("fov"))
    for _ in range(6):
        bcc.capture_scene()
    RL.export_render_target(w, brt, str(RDIR), "debug_backdrop_only.png")
    res["debug_backdrop_render_state"] = safe(lambda: [bdc.is_visible(), str(bdc.get_material(0).get_name())])

    for lod in (0, 1, 2):
        for c in ALLC.values():
            c.set_forced_lod_model(lod + 1)
        views = BVIEWS if lod == 0 else {k: v for k, v in BVIEWS.items() if k in ("beauty_side_pair", "beauty_mouth_close")}
        for name, v in views.items():
            show_only(v["show"] + ["backdrop"])
            place_backdrop(v)
            bdc.set_forced_lod_model(0)
            aim(bcam, bcc, v["loc"], v["fwd"], v["up"], ortho_w=v.get("ortho_w"), fov=v.get("fov"))
            for _ in range(6):
                bcc.capture_scene()
            fn = f"{name}_LOD{lod}"
            RL.export_render_target(w, brt, str(RDIR), fn + ".png")
            shots.append({"name": fn, "lod": lod, **{k: v[k] for k in v if k != "show"}})
            dump()
    res["shots"] = shots
    res["status"] = "ok"
except Exception:  # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
finally:
    for a in spawned:
        safe(lambda a=a: EAS.destroy_actor(a))
res["hashes_after"] = C.all_hashes()
res["exports_unchanged"] = res["hashes_after"] == res["hashes_before"]
res["seconds"] = round(time.time() - res["t0"], 1)
dump()
unreal.log("KV_PASS_C_DONE status=" + res["status"])
