"""Male cloak review, Unreal half (2026-09-27). Studio capture of the IN-GAME cloak on the male as the engine draws it.

Runs INSIDE a full offscreen editor (UnrealEditor-Cmd CloakReview.uproject -RenderOffscreen -ExecutePythonScript=this), driven by a
slate post-tick generator so every capture gets real frames (TAA history, VT feedback, sky-light recapture).
Scene is an UNSAVED new level; materials made here are transient; nothing is saved. Assets under /Game/Ninja/Cloak and
/Game/MetaHumans are byte copies of DemoGame_1 (mu_copied_assets.json). Env MU_PASS = A (default) | B (close-ups/cloth, uses mu_passB.json).
"""
import json, math, os, time, traceback
from pathlib import Path
import unreal as ue

OUT = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/unreal")
PASS = os.environ.get("MU_PASS", "A")
SHOTS = OUT / ("shots" if PASS == "A" else "shots_B")
SHOTS.mkdir(parents=True, exist_ok=True)
REP = {"pass": PASS, "engine": ue.SystemLibrary.get_engine_version(), "notes": [], "captures": [], "errors": []}
EAS = ue.get_editor_subsystem(ue.EditorActorSubsystem)
MEL = ue.MaterialEditingLibrary
RL = ue.RenderingLibrary
CLOAK = "/Game/Ninja/Cloak/SKM_BlackCloak_MH"
BODY = "/Game/MetaHumans/MH_PlayerDefault/Body/SKM_MH_PlayerDefault_BodyMesh"
FACE = "/Game/MetaHumans/MH_PlayerDefault/Face/SKM_MH_PlayerDefault_FaceMesh"
W, H = 834, 1348            # reference 417 x 674 at 2x
TAN_V = 0.18                # 100 mm lens on a 36 mm sensor fitted to the frame height (previous review's camfit best focal)
EXPOSURE_BIAS = float(os.environ.get("MU_BIAS", "0.5"))
BACKDROP = 2.5      # unlit backdrop emissive: reads as paper white like the reference sweep (254)
SKY_I = float(os.environ.get("MU_SKY", "1.0"))


def log(*a):
    ue.log("[MU] " + " ".join(str(x) for x in a))


def save():
    (OUT / ("mu_capture_report_%s.json" % PASS)).write_text(json.dumps(REP, indent=1, default=str))


def setp(obj, k, v):
    try:
        obj.set_editor_property(k, v)
        return True
    except Exception as ex:  # noqa: BLE001
        REP["notes"].append("setp %s.%s failed: %s" % (type(obj).__name__, k, ex))
        return False


def getp(obj, k):
    try:
        return obj.get_editor_property(k)
    except Exception as ex:  # noqa: BLE001
        return "ERR %s" % ex


def world():
    return ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()


def V(x, y, z):
    return ue.Vector(float(x), float(y), float(z))


def vl(v):
    return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]


# ------------------------------------------------------------------------------------------------ transient materials
def flat_mat(name, rgb, unlit=False, rough=0.9):
    mat = ue.new_object(ue.Material, name=name)
    if unlit:
        setp(mat, "shading_model", ue.MaterialShadingModel.MSM_UNLIT)
    setp(mat, "two_sided", True)
    e = MEL.create_material_expression(mat, ue.MaterialExpressionConstant3Vector, -400, 0)
    e.set_editor_property("constant", ue.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    MEL.connect_material_property(e, "", ue.MaterialProperty.MP_EMISSIVE_COLOR if unlit else ue.MaterialProperty.MP_BASE_COLOR)
    if not unlit:
        r = MEL.create_material_expression(mat, ue.MaterialExpressionConstant, -400, 200)
        r.set_editor_property("r", rough)
        MEL.connect_material_property(r, "", ue.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    return mat


# ------------------------------------------------------------------------------------------------ asset record
def record_assets(cloak_mesh, body_mesh):
    rec = {}
    slots = []
    for i, s in enumerate(cloak_mesh.get_editor_property("materials")):
        mi = s.get_editor_property("material_interface")
        slots.append({"index": i, "slot": str(s.get_editor_property("material_slot_name")),
                      "material": mi.get_path_name() if mi else None})
    rec["cloak_slots"] = slots
    for k in ("skeleton", "physics_asset", "mesh_clothing_assets", "positive_bounds_extension", "negative_bounds_extension",
              "lod_settings", "shadow_physics_asset"):
        v = getp(cloak_mesh, k)
        rec["cloak_" + k] = [x.get_path_name() for x in v] if isinstance(v, ue.Array) else (v.get_path_name() if hasattr(v, "get_path_name") else str(v))
    try:
        b = cloak_mesh.get_bounds()
        rec["cloak_bounds"] = {"origin": vl(b.origin), "extent": vl(b.box_extent)}
        ib = cloak_mesh.get_imported_bounds()
        rec["cloak_imported_bounds"] = {"origin": vl(ib.origin), "extent": vl(ib.box_extent)}
    except Exception as ex:  # noqa: BLE001
        rec["cloak_bounds_err"] = str(ex)
    try:
        sub = ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem)
        rec["cloak_lods"] = sub.get_lod_count(cloak_mesh)
        rec["cloak_lod0_sections"] = sub.get_num_sections(cloak_mesh, 0)
        rec["cloak_lod0_verts"] = sub.get_num_verts(cloak_mesh, 0)
    except Exception as ex:  # noqa: BLE001
        rec["cloak_lod_err"] = str(ex)
    try:
        info = []
        for c in cloak_mesh.get_editor_property("mesh_clothing_assets"):
            d = {"name": c.get_name(), "class": c.get_class().get_name()}
            for k in ("physics_asset", "cloth_config", "lod_data", "reference_bone_name"):
                v = getp(c, k)
                d[k] = v.get_path_name() if hasattr(v, "get_path_name") else str(v)[:400]
            info.append(d)
        rec["clothing_assets"] = info
    except Exception as ex:  # noqa: BLE001
        rec["clothing_err"] = str(ex)
    mats = {}
    texs = set()
    for s in slots:
        p = s["material"]
        if not p or p in mats:
            continue
        m = ue.load_asset(p)
        d = {"class": m.get_class().get_name()}
        base = m
        if isinstance(m, ue.MaterialInstance):
            par = m.get_editor_property("parent")
            d["parent"] = par.get_path_name() if par else None
            base = m.get_base_material()
            d["base"] = base.get_path_name()
            try:
                d["scalar"] = {str(n): MEL.get_material_instance_scalar_parameter_value(m, n) for n in MEL.get_scalar_parameter_names(m)}
                d["vector"] = {str(n): str(MEL.get_material_instance_vector_parameter_value(m, n)) for n in MEL.get_vector_parameter_names(m)}
                d["texture"] = {}
                for n in MEL.get_texture_parameter_names(m):
                    t = MEL.get_material_instance_texture_parameter_value(m, n)
                    d["texture"][str(n)] = t.get_path_name() if t else None
                d["switch"] = {str(n): MEL.get_material_instance_static_switch_parameter_value(m, n) for n in MEL.get_static_switch_parameter_names(m)}
            except Exception as ex:  # noqa: BLE001
                d["param_err"] = str(ex)
        else:
            try:
                d["scalar"] = {str(n): MEL.get_material_default_scalar_parameter_value(m, n) for n in MEL.get_scalar_parameter_names(m)}
                d["vector"] = {str(n): str(MEL.get_material_default_vector_parameter_value(m, n)) for n in MEL.get_vector_parameter_names(m)}
                d["texture"] = {}
                for n in MEL.get_texture_parameter_names(m):
                    t = MEL.get_material_default_texture_parameter_value(m, n)
                    d["texture"][str(n)] = t.get_path_name() if t else None
                d["switch"] = {str(n): MEL.get_material_default_static_switch_parameter_value(m, n) for n in MEL.get_static_switch_parameter_names(m)}
            except Exception as ex:  # noqa: BLE001
                d["param_err"] = str(ex)
        for k in ("blend_mode", "shading_model", "two_sided", "material_domain", "used_with_skeletal_mesh", "used_with_clothing"):
            d["base_" + k] = str(getp(base, k))
        try:
            used = MEL.get_material_used_textures(m) if hasattr(MEL, 'get_material_used_textures') else MEL.get_used_textures(m)
            d["used_textures"] = [t.get_path_name() for t in used]
            texs.update(d["used_textures"])
        except Exception as ex:  # noqa: BLE001
            d["used_textures_err"] = str(ex)
        try:
            d["base_num_expressions"] = MEL.get_num_material_expressions(base)
        except Exception as ex:  # noqa: BLE001
            d["expr_err"] = str(ex)
        try:
            st = MEL.get_statistics(m)
            d["stats"] = {k: getp(st, k) for k in ("num_pixel_shader_instructions", "num_samplers", "num_vertex_texture_samples",
                                                     "num_pixel_texture_samples", "num_uv_scalars", "num_virtual_texture_samples")}
        except Exception as ex:  # noqa: BLE001
            d["stats_err"] = str(ex)
        mats[p] = d
    rec["materials"] = mats
    tx = {}
    for p in sorted(texs):
        t = ue.load_asset(p)
        d = {}
        for k in ("compression_settings", "srgb", "lod_group", "mip_gen_settings", "address_x", "address_y", "filter",
                  "virtual_texture_streaming", "never_stream", "max_texture_size", "lod_bias", "flip_green_channel",
                  "compression_quality", "adjust_brightness", "adjust_saturation"):
            d[k] = str(getp(t, k))
        try:
            d["size"] = [t.blueprint_get_size_x(), t.blueprint_get_size_y()]
        except Exception as ex:  # noqa: BLE001
            d["size_err"] = str(ex)
        tx[p] = d
    rec["textures"] = tx
    rec["body_physics_asset"] = str(getp(body_mesh, "physics_asset").get_path_name() if body_mesh.get_editor_property("physics_asset") else None)
    REP["assets"] = rec


# ------------------------------------------------------------------------------------------------ scene
def spawn_skel(path, label):
    a = EAS.spawn_actor_from_class(ue.SkeletalMeshActor, V(0, 0, 0), ue.Rotator(0, 0, 0))
    a.set_actor_label(label)
    c = a.skeletal_mesh_component
    c.set_skeletal_mesh_asset(ue.load_asset(path))
    c.set_forced_lod(1)
    setp(c, "disable_post_process_blueprint", True)
    setp(c, "visibility_based_anim_tick_option", ue.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    return a, c


def build():
    w = world()
    for cmd in ("r.TextureStreaming 0", "r.AntiAliasingMethod 2", "r.ScreenPercentage 100", "r.MotionBlurQuality 0",
                "r.VT.MaxUploadsPerFrame 512", "r.SceneCapture.EnableViewExtensions 1"):
        ue.SystemLibrary.execute_console_command(w, cmd)
    S = {}
    cloak_mesh, body_mesh = ue.load_asset(CLOAK), ue.load_asset(BODY)
    assert cloak_mesh and body_mesh, "missing cloak/body"
    record_assets(cloak_mesh, body_mesh)
    save()
    S["body_a"], S["body"] = spawn_skel(BODY, "MU_Body")
    S["face_a"], S["face"] = spawn_skel(FACE, "MU_Face")
    S["cloak_a"], S["cloak"] = spawn_skel(CLOAK, "MU_Cloak")
    # game setup (setup_cloak_mh.py + NinjaVisualBodyComponent.cpp): cloak attached to Body, Leader Pose follower, no anim class,
    # component materials NOT overridden (mesh slot materials render).
    try:
        S["cloak"].set_leader_pose_component(S["body"], True)
        REP["notes"].append("cloak leader pose -> body: ok")
    except Exception as ex:  # noqa: BLE001
        REP["notes"].append("leader pose failed: %s" % ex)
    setp(S["cloak"], "disable_cloth_simulation", True)       # at-rest pass: the cloth section draws its skinned pose
    S["cloak_mats_on_component"] = [m.get_path_name() if m else None for m in S["cloak"].get_materials()]
    REP["cloak_component_materials"] = S["cloak_mats_on_component"]

    # studio: white unlit backdrop sphere (no shadow), white lit floor, key + fill + rim directional, captured sky light
    bd = EAS.spawn_actor_from_class(ue.StaticMeshActor, V(0, 0, 0), ue.Rotator(0, 0, 0))
    bd.set_actor_label("MU_Backdrop")
    bd.static_mesh_component.set_static_mesh(ue.load_asset("/Engine/BasicShapes/Sphere"))
    bd.set_actor_scale3d(V(60, 60, 60))
    bd.static_mesh_component.set_cast_shadow(False)
    bd.static_mesh_component.set_material(0, flat_mat("MU_BackdropMat", (BACKDROP, BACKDROP, BACKDROP), unlit=True))
    fl = EAS.spawn_actor_from_class(ue.StaticMeshActor, V(0, 0, -0.2), ue.Rotator(0, 0, 0))
    fl.set_actor_label("MU_Floor")
    fl.static_mesh_component.set_static_mesh(ue.load_asset("/Engine/BasicShapes/Plane"))
    fl.set_actor_scale3d(V(40, 40, 1))
    fl.static_mesh_component.set_material(0, flat_mat("MU_FloorMat", (0.9, 0.9, 0.9)))
    S["floor"] = fl
    S["lights"] = []
    # forward (the way he faces) from the skeleton: foot -> ball
    body = S["body"]
    f = (body.get_socket_location("ball_l") - body.get_socket_location("foot_l")) +         (body.get_socket_location("ball_r") - body.get_socket_location("foot_r"))
    f.z = 0
    fwd = f.normal()
    # his right (= the viewer's LEFT when facing him = the clasp side in the reference), measured, not assumed
    hr = body.get_socket_location("upperarm_r") - body.get_socket_location("upperarm_l")
    hr.z = 0
    S["his_right"] = hr.normal()
    REP["forward"] = vl(fwd)
    REP["his_right"] = vl(S["his_right"])
    S["fwd"] = fwd
    yaw_f = math.degrees(math.atan2(fwd.y, fwd.x))
    for name, yaw_off, pitch, inten, shadow, angle in (("Key", 150.0, -40.0, 3.0, True, 12.0),
                                                      ("Fill", -150.0, -15.0, 1.2, False, 20.0),
                                                      ("Rim", 20.0, -35.0, 1.0, False, 12.0)):
        # light TRAVEL direction: from the camera side toward him = yaw_f + 180 +/- offset
        rot = ue.Rotator(0.0, pitch, yaw_f + yaw_off)   # (roll, pitch, yaw)
        la = EAS.spawn_actor_from_class(ue.DirectionalLight, V(0, 0, 400), rot)
        la.set_actor_label("MU_" + name)
        lc = la.light_component
        setp(lc, "mobility", ue.ComponentMobility.MOVABLE)
        lc.set_intensity(inten)
        lc.set_cast_shadows(shadow)
        setp(lc, "light_source_angle", angle)
        setp(lc, "atmosphere_sun_light", False)
        S["lights"].append((lc, inten))
    sky = EAS.spawn_actor_from_class(ue.SkyLight, V(0, 0, 300), ue.Rotator(0, 0, 0))
    sky.set_actor_label("MU_Sky")
    sc = sky.light_component
    setp(sc, "mobility", ue.ComponentMobility.MOVABLE)
    setp(sc, "source_type", ue.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    setp(sc, "cubemap", ue.load_asset("/Engine/EngineResources/GrayLightTextureCube"))
    setp(sc, "real_time_capture", False)
    sc.set_intensity(SKY_I)
    S["sky"] = sc
    # calibration spheres (albedo 0.8 / 0.18 / 0.04) 4 m to the side, only seen by the calib camera
    side = S["his_right"] * -1.0
    S["calib"] = []
    for i, alb in enumerate((0.8, 0.18, 0.04)):
        p = side * 400 + side * (i * 60) + V(0, 0, 30)
        a = EAS.spawn_actor_from_class(ue.StaticMeshActor, p, ue.Rotator(0, 0, 0))
        a.static_mesh_component.set_static_mesh(ue.load_asset("/Engine/BasicShapes/Sphere"))
        a.set_actor_scale3d(V(0.5, 0.5, 0.5))
        a.static_mesh_component.set_material(0, flat_mat("MU_Calib_%d" % i, (alb, alb, alb), rough=1.0))
        S["calib"].append(p)
    S["side"] = side

    # capture
    ca = EAS.spawn_actor_from_class(ue.SceneCapture2D, V(0, 500, 100), ue.Rotator(0, 0, 0))
    ca.set_actor_label("MU_Capture")
    cc = ca.get_component_by_class(ue.SceneCaptureComponent2D)
    S["cap_a"], S["cap"] = ca, cc
    setp(cc, "capture_every_frame", False)
    setp(cc, "capture_on_movement", False)
    setp(cc, "always_persist_rendering_state", True)
    setp(cc, "capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    pp = cc.get_editor_property("post_process_settings")
    for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", ue.AutoExposureMethod.AEM_MANUAL),
                 ("override_auto_exposure_bias", True), ("auto_exposure_bias", EXPOSURE_BIAS),
                 ("override_auto_exposure_apply_physical_camera_exposure", True),
                 ("auto_exposure_apply_physical_camera_exposure", False),
                 ("override_dynamic_global_illumination_method", True),
                 ("dynamic_global_illumination_method", ue.DynamicGlobalIlluminationMethod.NONE),
                 ("override_reflection_method", True), ("reflection_method", ue.ReflectionMethod.NONE),
                 ("override_motion_blur_amount", True), ("motion_blur_amount", 0.0),
                 ("override_vignette_intensity", True), ("vignette_intensity", 0.0),
                 ("override_bloom_intensity", True), ("bloom_intensity", 0.0),
                 ("override_local_exposure_highlight_contrast_scale", True), ("local_exposure_highlight_contrast_scale", 1.0),
                 ("override_local_exposure_shadow_contrast_scale", True), ("local_exposure_shadow_contrast_scale", 1.0)):
        setp(pp, k, v)
    cc.set_editor_property("post_process_settings", pp)
    S["rts"] = {}
    # framing from the cloak MESH bounds (a Leader Pose follower reports the leader's bounds, so actor bounds = body bounds)
    b = cloak_mesh.get_bounds()
    S["cb"] = (b.origin, b.box_extent)
    o, e = S["cloak_a"].get_actor_bounds(False)
    REP["cloak_actor_bounds"] = {"origin": vl(o), "extent": vl(e)}
    ob, eb = S["body_a"].get_actor_bounds(False)
    REP["body_actor_bounds"] = {"origin": vl(ob), "extent": vl(eb)}
    return S


def rt(S, w_, h_, fmt=ue.TextureRenderTargetFormat.RTF_RGBA8):
    key = (w_, h_, str(fmt))
    if key not in S["rts"]:
        t = RL.create_render_target2d(world(), w_, h_, fmt)
        setp(t, "target_gamma", 2.2)
        S["rts"][key] = t
    return S["rts"][key]


def aim(S, target, yaw_deg, elev_deg, dist, w_, h_, tan_v=TAN_V):
    """camera orbiting 'target' at yaw_deg from his front (0 = in front of him, + = toward HIS RIGHT = the clasp side)."""
    fwd = S["fwd"]
    a = math.radians(yaw_deg)
    d = fwd * math.cos(a) + S["his_right"] * math.sin(a)
    el = math.radians(elev_deg)
    pos = target + d * (dist * math.cos(el)) + V(0, 0, dist * math.sin(el))
    rot = ue.MathLibrary.find_look_at_rotation(pos, target)
    S["cap_a"].set_actor_location_and_rotation(pos, rot, False, False)
    hfov = math.degrees(2 * math.atan(tan_v * w_ / h_))
    S["cap"].set_editor_property("fov_angle", hfov)
    S["cap"].set_editor_property("texture_target", rt(S, w_, h_))
    return {"cam": vl(pos), "target": vl(target), "yaw": yaw_deg, "elev": elev_deg, "dist": round(dist, 2),
            "hfov": round(hfov, 4), "res": [w_, h_]}


def frame_full(S, yaw=0.0, elev=3.0):
    o, e = S["cb"]
    top, bot = o.z + e.z, max(o.z - e.z, 0.0)
    Hc = top - bot
    frame_h = Hc / (655.0 / 674.0)
    ftop = top + 5.0 / 674.0 * frame_h
    cz = ftop - frame_h / 2
    dist = frame_h / 2 / TAN_V
    return aim(S, V(o.x, o.y, cz), yaw, elev, dist, W, H)


def frame_region(S, cx_frac, cz, frame_h, yaw=0.0, elev=3.0, w_=1200, h_=1200):
    """cx_frac: horizontal offset in cm toward the VIEWER's right (= his left) from the cloak centre, seen from the front."""
    o, e = S["cb"]
    vright = S["his_right"] * -1.0
    tgt = V(o.x, o.y, cz) + vright * cx_frac
    tan_v = 0.18
    dist = frame_h / 2 / tan_v
    return aim(S, tgt, yaw, elev, dist, w_, h_, tan_v)


def vis(S, body, face=None):
    S["body"].set_visibility(body)
    S["face"].set_visibility(body if face is None else face)


def shoot(S, name, meta, n=14):
    """generator: warm n ticks capturing each tick, then export."""
    for _ in range(n):
        S["cap"].capture_scene()
        yield
    S["cap"].capture_scene()
    yield
    RL.export_render_target(world(), S["cap"].get_editor_property("texture_target"), str(SHOTS), name + ".png")
    meta = dict(meta, name=name, file=str(SHOTS / (name + ".png")), t=round(time.time() - T0, 1))
    REP["captures"].append(meta)
    save()
    log("CAPTURED", name)


def set_lights(S, directional):
    for lc, inten in S["lights"]:
        lc.set_intensity(inten if directional else 0.0)


def read_px(S, x, y):
    t = S["cap"].get_editor_property("texture_target")
    c = RL.read_render_target_pixel(world(), t, x, y)
    return (c.r + c.g + c.b) / 3.0


def set_pp(S, **kv):
    pp = S["cap"].get_editor_property("post_process_settings")
    for k, v in kv.items():
        setp(pp, k, v)
    S["cap"].set_editor_property("post_process_settings", pp)


def sky_probe(S, tag):
    """sky light only, mid-grey sphere centre pixel (sRGB 0-255)."""
    set_lights(S, False)
    m = aim(S, S["calib"][1], 0.0, 3.0, 110 / 2 / 0.18 * 1.6, 1200, 600)
    yield from shoot(S, "calib_skylight_only_" + tag, dict(m, directional=False))
    v = read_px(S, 600, 300)
    set_lights(S, True)
    REP.setdefault("sky_probe", []).append({"variant": tag, "grey_sphere_centre_srgb": v})
    log("SKYPROBE", tag, v)
    return v


def dome_lights(S, total):
    """fallback ambient: 26 shadowless soft directional lights over the sphere (no AO)."""
    dirs = []
    for el in (-60, -20, 20, 60):
        for k in range(6):
            dirs.append((el, k * 60 + (30 if el in (-20, 60) else 0)))
    dirs += [(-89, 0), (89, 0)]
    for el, az in dirs:
        la = EAS.spawn_actor_from_class(ue.DirectionalLight, V(0, 0, 500), ue.Rotator(0.0, float(el), float(az)))
        lc = la.light_component
        setp(lc, "mobility", ue.ComponentMobility.MOVABLE)
        lc.set_intensity(total / len(dirs))
        lc.set_cast_shadows(False)
        setp(lc, "light_source_angle", 30.0)
        setp(lc, "atmosphere_sun_light", False)
    REP["notes"].append("ambient fallback: %d shadowless directional lights, total %.2f lux" % (len(dirs), total))


def program():
    S = build()
    save()
    for _ in range(40):
        yield
    ue.AutomationLibrary.finish_loading_before_screenshot()
    S["sky"].recapture_sky()
    for _ in range(40):
        yield
    # --- 1) prove the sky light is captured (sky-light-only grey sphere must not be black); try variants in order
    v = yield from sky_probe(S, "cubemap_graylight")
    if v < 10:
        sc = S["sky"]
        setp(sc, "source_type", ue.SkyLightSourceType.SLS_CAPTURED_SCENE)
        setp(sc, "real_time_capture", True)
        sc.recapture_sky()
        for _ in range(40):
            yield
        v = yield from sky_probe(S, "captured_scene_realtime")
    if v < 10:
        setp(S["sky"], "real_time_capture", False)
        S["sky"].recapture_sky()
        for _ in range(60):
            yield
        v = yield from sky_probe(S, "captured_scene_recapture")
    if v < 10:
        S["sky"].set_intensity(0.0)
        dome_lights(S, 3.0)
        for _ in range(5):
            yield
        v = yield from sky_probe(S, "dome_fallback")
    REP["ambient_final"] = REP["sky_probe"][-1]
    m = aim(S, S["calib"][1], 0.0, 3.0, 110 / 2 / 0.18 * 1.6, 1200, 600)
    yield from shoot(S, "calib_all_lights", dict(m, directional=True))
    REP["calib_all_lights_grey_centre"] = read_px(S, 600, 300)
    o, e = S["cb"]
    top, bot = o.z + e.z, max(o.z - e.z, 0.0)
    Hc = top - bot
    REP["cloak_z_top_bot"] = [round(top, 2), round(bot, 2)]
    if PASS == "A":
        vis(S, False)
        for yaw in (0.0, -10.0, 10.0):
            yield from shoot(S, "front_cloak_only_yaw%+d" % int(yaw), dict(frame_full(S, yaw), body=False))
        vis(S, True)
        yield from shoot(S, "front_with_body", dict(frame_full(S, 0.0), body=True))
        yield from shoot(S, "threequarter_clasp_side_with_body", dict(frame_full(S, 45.0), body=True))
        yield from shoot(S, "threequarter_other_side_with_body", dict(frame_full(S, -45.0), body=True))
        yield from shoot(S, "side_clasp_side_with_body", dict(frame_full(S, 90.0), body=True))
        yield from shoot(S, "back_with_body", dict(frame_full(S, 180.0), body=True))
        vis(S, False)
        yield from shoot(S, "threequarter_clasp_side_cloak_only", dict(frame_full(S, 45.0), body=False))
        yield from shoot(S, "back_cloak_only", dict(frame_full(S, 180.0), body=False))
        # close-ups; the clasp sits ~28 cm to the viewer's LEFT of centre at z ~158 (pass-A2 front shot, pixel 218,215)
        vis(S, True)
        yield from shoot(S, "close_collar_with_body", dict(frame_region(S, 0.0, top - 0.13 * Hc, 0.30 * Hc), body=True))
        vis(S, False)
        yield from shoot(S, "close_collar_clasp_region", dict(frame_region(S, -10.0, top - 0.17 * Hc, 0.36 * Hc), body=False))
        yield from shoot(S, "close_clasp", dict(frame_region(S, -28.0, 157.0, 26.0), body=False))
        yield from shoot(S, "close_hem", dict(frame_region(S, 0.0, bot + 0.14 * Hc, 0.30 * Hc, w_=1400, h_=1000), body=False))
        yield from shoot(S, "close_fabric_chest", dict(frame_region(S, 10.0, top - 0.40 * Hc, 18.0), body=False))
        # diagnostic: +2 EV to read folds / grain in the near-black cloth (NOT the product-shot exposure)
        set_pp(S, auto_exposure_bias=EXPOSURE_BIAS + 2.0)
        yield from shoot(S, "DIAG_front_cloak_only_plus2EV", dict(frame_full(S, 0.0), body=False, exposure_bias=EXPOSURE_BIAS + 2.0))
        yield from shoot(S, "DIAG_close_collar_clasp_plus2EV", dict(frame_region(S, -10.0, top - 0.17 * Hc, 0.36 * Hc), body=False, exposure_bias=EXPOSURE_BIAS + 2.0))
        yield from shoot(S, "DIAG_close_fabric_chest_plus2EV", dict(frame_region(S, 10.0, top - 0.40 * Hc, 18.0), body=False, exposure_bias=EXPOSURE_BIAS + 2.0))
        yield from shoot(S, "DIAG_close_hem_plus2EV", dict(frame_region(S, 0.0, bot + 0.14 * Hc, 0.30 * Hc, w_=1400, h_=1000), body=False, exposure_bias=EXPOSURE_BIAS + 2.0))
        set_pp(S, auto_exposure_bias=EXPOSURE_BIAS)
        # base colour buffer (albedo as the GBuffer sees it), cloak alone, front
        S["cap"].set_editor_property("capture_source", ue.SceneCaptureSource.SCS_BASE_COLOR)
        yield from shoot(S, "front_cloak_only_basecolor", dict(frame_full(S, 0.0), body=False, source="SCS_BASE_COLOR"))
        S["cap"].set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        save()
        # --- cloth: Simulate-In-Editor so components tick (the editor world does not simulate cloth: pass A2 diff = noise)
        vis(S, True)
        setp(S["cloak"], "disable_cloth_simulation", False)
        frame_full(S, 0.0)
        try:
            ue.get_editor_subsystem(ue.LevelEditorSubsystem).editor_play_simulate()
            REP["notes"].append("SIE requested")
        except Exception as ex:  # noqa: BLE001
            REP["notes"].append("SIE failed: %s" % ex)
        gw = None
        t_sim = time.time()
        for i in range(600):
            yield
            if i % 10 == 0:
                try:
                    gw = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world()
                except Exception:  # noqa: BLE001
                    gw = None
                if gw is not None:
                    REP["notes"].append("SIE game world up at tick %d: %s" % (i, gw.get_name()))
                    t_sim = time.time()
                    break
        if gw is not None:
            caps = ue.GameplayStatics.get_all_actors_of_class(gw, ue.SceneCapture2D)
            skels = ue.GameplayStatics.get_all_actors_of_class(gw, ue.SkeletalMeshActor)
            REP["notes"].append("SIE actors: %d captures, %d skeletal" % (len(caps), len(skels)))
            gcap = caps[0].get_component_by_class(ue.SceneCaptureComponent2D) if caps else None
            for a_ in skels:
                smc = a_.skeletal_mesh_component
                ma = smc.get_skeletal_mesh_asset()
                if ma and "BlackCloak" in ma.get_name():
                    REP["notes"].append("SIE cloak: cloth disabled=%s" % getp(smc, "disable_cloth_simulation"))
            if gcap is not None:
                RT_ = rt(S, W, H)
                gcap.set_editor_property("texture_target", RT_)
                for idx, nticks in enumerate((30, 300)):
                    for _ in range(nticks):
                        gcap.capture_scene()
                        yield
                    for _ in range(12):
                        gcap.capture_scene()
                        yield
                    nm = "front_with_body_cloth_SIE_%s" % ("early" if idx == 0 else "settled")
                    RL.export_render_target(gw, RT_, str(SHOTS), nm + ".png")
                    REP["captures"].append({"name": nm, "file": str(SHOTS / (nm + ".png")), "cloth": "Simulate-In-Editor, A-pose, gravity",
                                            "sim_seconds_wall": round(time.time() - t_sim, 1)})
                    save()
                    log("CAPTURED", nm)
            try:
                ue.get_editor_subsystem(ue.LevelEditorSubsystem).editor_request_end_play()
            except Exception as ex:  # noqa: BLE001
                REP["notes"].append("end play: %s" % ex)
            for _ in range(30):
                yield
        else:
            REP["notes"].append("SIE: no game world within 600 ticks; no settled-cloth frame")
    else:
        spec = json.loads((OUT / "mu_passB.json").read_text())
        for s_ in spec["shots"]:
            vis(S, s_.get("body", False))
            m = frame_region(S, s_["dx"], s_["z"], s_["frame_h"], s_.get("yaw", 0.0), s_.get("elev", 3.0), s_.get("w", 1200), s_.get("h", 1200))
            yield from shoot(S, s_["name"], dict(m, body=s_.get("body", False)))
    # textures after everything compiled
    for p_ in list(REP["assets"]["textures"].keys()):
        t_ = ue.load_asset(p_)
        try:
            REP["assets"]["textures"][p_]["size_at_end"] = [t_.blueprint_get_size_x(), t_.blueprint_get_size_y()]
        except Exception as ex:  # noqa: BLE001
            REP["assets"]["textures"][p_]["size_at_end"] = str(ex)
    REP["done"] = True
    save()
    log("MU_DONE")


T0 = time.time()
GEN = program()
STATE = {}


def tick(dt):
    if STATE.get("busy") or STATE.get("finished"):
        STATE["reentered"] = STATE.get("reentered", 0) + 1
        return
    STATE["busy"] = True
    try:
        next(GEN)
    except StopIteration:
        STATE["finished"] = True
        ue.unregister_slate_post_tick_callback(STATE["cb"])
        ue.SystemLibrary.quit_editor()
    except Exception:  # noqa: BLE001
        STATE["finished"] = True
        REP["errors"].append(traceback.format_exc())
        save()
        ue.log_error(traceback.format_exc())
        ue.unregister_slate_post_tick_callback(STATE["cb"])
        ue.SystemLibrary.quit_editor()
    finally:
        STATE["busy"] = False


try:
    ue.get_editor_subsystem(ue.LevelEditorSubsystem).new_level("/Temp/MU_MaleReview")
except Exception as _ex:  # noqa: BLE001
    REP["notes"].append("new_level /Temp failed: %s" % _ex)
    ue.get_editor_subsystem(ue.LevelEditorSubsystem).new_level("/Game/MU_Unsaved/L_MU_MaleReview")
STATE["cb"] = ue.register_slate_post_tick_callback(tick)
try:
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
except Exception:  # noqa: BLE001
    pass
log("MU_REGISTERED pass", PASS)
