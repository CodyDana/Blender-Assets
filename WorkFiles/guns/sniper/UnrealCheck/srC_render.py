"""SR01 W5, pass C (a THIRD fresh UnrealEditor-Cmd, real RHI, -RenderOffscreen): load what pass A saved (nothing
imported, nothing saved) and
  1. ListTextures into the log (built pixel format + mip count per texture);
  2. Unreal's own FBX export of SK_SR01 with its LODs (roundtrip/ue_SK_SR01.fbx; the skeletal exporter needs a
     render-state component, so it runs here);
  3. RUNTIME poses: a SkeletalMeshComponent plays each clip (override_animation_data, the compressed data) at every
     frame; every bone's component transform and the Mag socket are read back (U9 compression error, U5 posed bounds,
     U6 the magazine along the reload path); the magazine attached to the SK component's Mag socket with the gun at
     an arbitrary world transform (U6 at rest);
  4. U4: First Person rendering: FP / WSR components on a lit ground with Virtual Shadow Maps: ground-shadow pixels
     cast by each, ForcedLodModel and predicted LODs at distance;
  5. U4 scope pair on the SK: SM_Att_Scope_LongRange attached at Rail_Top (+2 slots) read back in the SK frame;
  6. beauty captures with the scope (3/4, sides, deployed bipod 3/4 + side + front, bolt open), the scope view (camera
     at EyePoint looking down Sight at a 10 m board, the bore line's 10 m point marked; the reticle is drawn by srF), the
     LOD strip and the twin, with the shipped maps through plain check materials.
"""
import json, math, sys, time, traceback
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import sr_common as C  # noqa: E402

DEST = C.dest()
OUT = C.HERE / "srC_render.json"
POSES = C.HERE / "srC_runtime.json"
RDIR = C.HERE / "renders"
RDIR.mkdir(exist_ok=True)
RT = C.HERE / "roundtrip"
RT.mkdir(exist_ok=True)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RL = unreal.RenderingLibrary
ML = unreal.MathLibrary
MEL = unreal.MaterialEditingLibrary
RTS = unreal.RelativeTransformSpace.RTS_COMPONENT
SC = C.sidecar_sk()
safe = C.safe
res = {"dest": DEST, "t0": time.time(), "hashes_before": C.all_hashes()}
spawned = []


def dump():
    res["seconds"] = round(time.time() - res["t0"], 1)
    C.write(OUT, res)


def v3(v, nd=6):
    return [round(v.x, nd), round(v.y, nd), round(v.z, nd)]


def T(t):
    q = t.rotation
    return [t.translation.x, t.translation.y, t.translation.z, q.x, q.y, q.z, q.w, t.scale3d.x, t.scale3d.y, t.scale3d.z]


def force_lod(c, v):
    """ForcedLodModel (0 = auto, n = LOD n-1) on a skinned or a static component."""
    if hasattr(c, "set_forced_lod"):
        c.set_forced_lod(v)
    else:
        c.set_forced_lod_model(v)


def cvar(cmd):
    unreal.SystemLibrary.execute_console_command(None, cmd)


U2B_CASES = [("rest", {}), ("bolt_1", {"Bolt01": 1.0}), ("bolt_05", {"Bolt01": 0.5}), ("boltrot_1", {"BoltRot01": 1.0}),
             ("bolt_open_back", {"BoltRot01": 1.0, "Bolt01": 1.0}), ("trigger_1", {"Trigger01": 1.0}),
             ("trigger_05", {"Trigger01": 0.5}), ("selector_SAFE", {"SelectorIndex": 0}), ("selector_AUTO", {"SelectorIndex": 2}),
             ("release_1", {"Release01": 1.0}), ("riser_1", {"Riser01": 1.0})]


def set_var(inst, name, value):
    """A Blueprint member variable on the anim instance (instance-editable): the Python name, else the authored name."""
    errs = []
    for key in (name, name.lower(), "".join("_" + ch.lower() if ch.isupper() and i else ch.lower() for i, ch in enumerate(name))):
        try:
            inst.set_editor_property(key, value)
            return key
        except Exception as exc:  # noqa: BLE001
            errs.append(f"{key}: {exc}"[:160])
    raise RuntimeError(f"cannot set {name}: {errs}")


def u2b(mesh_names):
    """U2b: ABP_Gun_LongGun (authored on SK_AR01_Skeleton) on SK_SR01 (Compatible Skeletons) and on SK_AR01; normalized
    inputs, each gun's angle table from its sidecar (sr_common.abp_tables). Per case the anim instance is ticked and the
    pose evaluated in this editor world; every bone and socket is read in component space. Also the guns' own reference
    poses for the comparison: each gun's Fire clip, Reload clip (release), and the sniper's Selector / CheekRiser /
    BoltCycle clips (detents, riser, bolt rotation + travel)."""
    cls = unreal.EditorAssetLibrary.load_blueprint_class(f"{DEST}/{C.ABP_NAME}")
    ar_sk = unreal.load_asset(f"{C.AR_DEST}/SK_AR01")
    tables = C.abp_tables()
    out = {"abp_class": cls.get_path_name() if cls else None, "tables": tables, "guns": {}}
    for gun, mesh, socks in (("SR01", sk, [s_["name"] for s_ in SC["sockets"]]),
                             ("AR01", ar_sk, [s_["name"] for s_ in C.sidecar_ar()["sockets"]])):
        g = {"mesh": mesh.get_path_name(), "skeleton": mesh.get_editor_property("skeleton").get_path_name()}
        # Python cannot tick a component in an editor world: SetAnimInstanceClass -> InitAnim(true) creates the instance
        # from the class defaults and evaluates it once (TickAnimation(0) + RefreshBoneTransforms). So each case writes
        # the inputs into the generated class's DEFAULT object (in memory only; this pass saves nothing) and evaluates on
        # a fresh actor.
        cdo = unreal.get_default_object(cls)
        t = tables[gun]
        keys = {k: set_var(cdo, k, float(v)) for k, v in (("BoltTravelCm", t["bolt_cm"]), ("BoltRotateDeg", t["bolt_rot_deg"]),
                                                          ("TriggerMaxDeg", t["trigger_deg"]), ("ReleaseMaxDeg", t["release_deg"]),
                                                          ("RiserMaxCm", t["riser_cm"]))}
        keys["SelectorDetentsDeg"] = set_var(cdo, "SelectorDetentsDeg", [float(x) for x in t["selector_deg"]])
        g["keys"] = keys
        cases = {}

        def fresh():
            a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
            c = a.get_editor_property("skeletal_mesh_component")
            c.set_skinned_asset_and_update(mesh)
            return a, c
        a, c = fresh()
        bones = [str(c.get_bone_name(i)) for i in range(c.get_num_bones())]
        g["bones"] = bones
        g["socket_named_bones"] = sorted(b for b in bones if b.lower() in {x.lower() for x in socks})

        def read(c):
            return {"bones": {b: T(c.get_socket_transform(b, RTS))[:7] for b in bones},
                    "sockets": {sn: T(c.get_socket_transform(sn, RTS))[:7] for sn in socks}}
        g["bind"] = read(c)
        EAS.destroy_actor(a)
        for nm_, inputs in U2B_CASES:
            vals = {"Bolt01": 0.0, "BoltRot01": 0.0, "Trigger01": 0.0, "Release01": 0.0, "Riser01": 0.0, "SelectorIndex": 1}
            vals.update(inputs)
            for k, v in vals.items():
                keys[k] = set_var(cdo, k, int(v) if k == "SelectorIndex" else float(v))
            a, c = fresh()
            try:
                c.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
                c.set_anim_instance_class(cls)
                inst = c.get_anim_instance()
                rec = read(c)
                rec["inputs"] = vals
                rec["anim_instance"] = inst.get_class().get_path_name() if inst else None
                rec["instance_values"] = {k: str(safe(lambda k=k: inst.get_editor_property(keys[k]))) for k in vals} if inst else None
                cases[nm_] = rec
            finally:
                EAS.destroy_actor(a)
        g["cases"] = cases
        # the gun's own clips (single-node runtime, the same fresh-actor sampling as the runtime poses)
        ref = {}
        clips = {"SR01": ("A_SR01_Fire", "A_SR01_Reload", "A_SR01_Selector", "A_SR01_CheekRiser", "A_SR01_BoltCycle"),
                 "AR01": ("A_AR01_Fire", "A_AR01_Reload", "A_AR01_Selector")}[gun]
        folder = DEST if gun == "SR01" else C.AR_DEST
        for cn in clips:
            seq = unreal.load_asset(f"{folder}/{cn}")
            fps = 60.0 if cn.endswith("_Fire") else 30.0
            n = int(round(seq.get_play_length() * fps))
            fr = {}
            for f in range(n + 1):
                b = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
                cc = b.get_editor_property("skeletal_mesh_component")
                cc.set_skinned_asset_and_update(mesh)
                cc.override_animation_data(seq, False, False, f / fps, 0.0)
                fr[str(f)] = {"bones": {bn: T(cc.get_socket_transform(bn, RTS))[:7] for bn in g["bones"]},
                              "sockets": {sn: T(cc.get_socket_transform(sn, RTS))[:7] for sn in socks}}
                EAS.destroy_actor(b)
            ref[cn] = {"fps": fps, "frames": fr}
        g["clip_reference"] = ref
        out["guns"][gun] = g
    return out


try:
    sk = unreal.load_asset(f"{DEST}/SK_SR01")
    sm = unreal.load_asset(f"{DEST}/SM_SR01")
    mag = unreal.load_asset(f"{DEST}/SM_SR01_Mag")
    for m in (sm, mag):
        m.get_bounding_box(); m.get_num_triangles(0)
    mats = {}
    for s in ("Metal", "Chassis", "Mag", "Scope_Body", "Scope_Lens"):
        m = unreal.load_asset(f"{DEST}/Materials/M_GC_SR01_{s}")
        MEL.recompile_material(m)
        mats[s] = m
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for cmd in ("Editor.AsyncTextureCompilation 0", "r.Shadow.Virtual.Enable 1", "r.TextureStreaming 0"):
        cvar(cmd)
    res["cvars"] = {k: safe(lambda k=k: unreal.SystemLibrary.get_console_variable_int_value(k))
                    for k in ("r.Shadow.Virtual.Enable", "r.TextureStreaming", "r.AllowStaticLighting")}
    # ------------------------------------------------------------------ 1. textures
    tex = {}
    for p in unreal.EditorAssetLibrary.list_assets(DEST + "/Textures", recursive=False, include_folder=False):
        t = unreal.load_asset(str(p).split(".")[0])
        safe(lambda: t.set_editor_property("never_stream", True))   # in memory only, never saved
        safe(lambda: t.update_resource())
        tex[t.get_name()] = {"memory_bytes": safe(lambda: int(t.blueprint_get_memory_size())),
                             "built_size": safe(lambda: [t.blueprint_get_built_texture_size().x, t.blueprint_get_built_texture_size().y]) if hasattr(t, "blueprint_get_built_texture_size") else None,
                             "size": [int(t.blueprint_get_size_x()), int(t.blueprint_get_size_y())]}
    res["textures_runtime"] = tex
    unreal.log("SM_LISTTEXTURES_BEGIN")
    unreal.SystemLibrary.execute_console_command(w, "ListTextures")
    unreal.log("SM_LISTTEXTURES_END")
    dump()
    # ------------------------------------------------------------------ 2. SK roundtrip
    o = unreal.FbxExportOption()
    o.set_editor_property("collision", False)
    o.set_editor_property("level_of_detail", True)
    o.set_editor_property("ascii", False)
    o.set_editor_property("force_front_x_axis", False)
    t_ = unreal.AssetExportTask()
    t_.set_editor_property("object", sk)
    t_.set_editor_property("filename", str(RT / "ue_SK_SR01.fbx"))
    t_.set_editor_property("automated", True)
    t_.set_editor_property("prompt", False)
    t_.set_editor_property("replace_identical", True)
    t_.set_editor_property("exporter", unreal.SkeletalMeshExporterFBX())
    t_.set_editor_property("options", o)
    res["roundtrip_SK"] = safe(lambda: {"ok": bool(unreal.Exporter.run_asset_export_task(t_)),
                                        "bytes": (RT / "ue_SK_SR01.fbx").stat().st_size if (RT / "ue_SK_SR01.fbx").exists() else 0})
    dump()
    # ------------------------------------------------------------------ 3. runtime poses + magazine on the Mag socket
    rot = unreal.Rotator()
    rot.roll, rot.pitch, rot.yaw = 17.0, -23.0, 41.0
    gloc = unreal.Vector(123.4, -56.7, 89.0)
    a_g = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, gloc, rot)
    spawned.append(a_g)
    c_g = a_g.get_editor_property("skeletal_mesh_component")
    c_g.set_skinned_asset_and_update(sk)
    a_g.set_actor_location_and_rotation(gloc, rot, False, False)
    a_m = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(-500, 300, 20), unreal.Rotator(11, 22, 33))
    spawned.append(a_m)
    c_m = a_m.get_editor_property("static_mesh_component")
    c_m.set_mobility(unreal.ComponentMobility.MOVABLE)
    c_m.set_static_mesh(mag)
    res["mag_attach_returned"] = bool(c_m.attach_to_component(c_g, "Mag", unreal.AttachmentRule.SNAP_TO_TARGET,
                                                              unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET, False))
    names = [str(c_g.get_bone_name(i)) for i in range(c_g.get_num_bones())]
    SOCKS = [s_["name"] for s_ in SC["sockets"]]
    res["socket_named_bones"] = sorted(b for b in names if b.lower() in {x.lower() for x in SOCKS})

    def mag_in_gun():
        Wg = c_g.get_world_transform()
        Wm = c_m.get_world_transform()
        basis = {}
        for key, p in (("o", (0, 0, 0)), ("x", (1, 0, 0)), ("y", (0, 1, 0)), ("z", (0, 0, 1))):
            basis[key] = [float(v) for v in v3(Wg.inverse_transform_location(Wm.transform_location(unreal.Vector(*p))), 9)]
        return basis
    res["attach_SK_rest"] = {"mag_to_gun_basis": mag_in_gun(), "socket_Mag": T(c_g.get_socket_transform("Mag", RTS)),
                             "socket_MagInsertStart": T(c_g.get_socket_transform("MagInsertStart", RTS)),
                             "relative_to_socket": safe(lambda: T(c_m.get_relative_transform())),
                             "mag_world_scale": v3(c_m.get_world_transform().scale3d)}
    runtime = {}

    def bone_tf(c, b):
        # bone names share case-insensitive FNames with sockets (trigger / Trigger ...): ask for the BONE
        r = safe(lambda: c.get_bone_transform(b, RTS))
        if isinstance(r, dict):
            idx = c.get_bone_index(b)
            r = c.get_bone_transform(idx) if idx >= 0 else unreal.Transform()
        return T(r)[:7]

    def posed(seq, tt):
        """A fresh actor per sample (the fan harness's method): the clip at time tt, the magazine on Mag."""
        a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, gloc, rot)
        c = a.get_editor_property("skeletal_mesh_component")
        c.set_skinned_asset_and_update(sk)
        c.override_animation_data(seq, False, False, tt, 0.0)
        a.set_actor_location_and_rotation(gloc, rot, False, False)
        am = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(-500, 300, 20), unreal.Rotator(11, 22, 33))
        cm = am.get_editor_property("static_mesh_component")
        cm.set_mobility(unreal.ComponentMobility.MOVABLE)
        cm.set_static_mesh(mag)
        cm.attach_to_component(c, "Mag", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                               unreal.AttachmentRule.SNAP_TO_TARGET, False)
        Wg = c.get_world_transform()
        Wm = cm.get_world_transform()
        basis = {}
        for key, p in (("o", (0, 0, 0)), ("x", (1, 0, 0)), ("y", (0, 1, 0)), ("z", (0, 0, 1))):
            basis[key] = [float(v) for v in v3(Wg.inverse_transform_location(Wm.transform_location(unreal.Vector(*p))), 9)]
        out = {"bones": {b: bone_tf(c, b) for b in names}, "Mag_socket": T(c.get_socket_transform("Mag", RTS))[:7],
               "sockets": {sn: T(c.get_socket_transform(sn, RTS))[:7] for sn in SOCKS},
               "mag_attached": basis}
        EAS.destroy_actor(am)
        EAS.destroy_actor(a)
        return out
    for a in SC["animations"]:
        nm = a["file"][:-4]
        seq = unreal.load_asset(f"{DEST}/{nm}")
        fps = float(a["fps"])
        n = int(round(seq.get_play_length() * fps))
        runtime[nm] = {"fps": fps, "frames": {str(f): posed(seq, f / fps) for f in range(n + 1)}}
    runtime["_bind"] = {"bones": {b: bone_tf(c_g, b) for b in names},
                        "sockets": {sn: T(c_g.get_socket_transform(sn, RTS))[:7] for sn in SOCKS}}
    POSES.write_text(json.dumps({"names": names, "clips": runtime}), encoding="utf-8")
    res["runtime_clips"] = {k: len(v["frames"]) for k, v in runtime.items() if k != "_bind"}
    dump()
    # ------------------------------------------------------------------ U2b: ONE ABP drives both guns
    res["U2b"] = safe(lambda: u2b(names))
    dump()
    # ------------------------------------------------------------------ cameras, light, backdrop
    for x in (a_g, a_m):
        EAS.destroy_actor(x)
        spawned.remove(x)

    def light(travel, lux, shadows=True):
        la = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 300), ML.make_rot_from_x(unreal.Vector(*travel)))
        lc = la.get_editor_property("directional_light_component")
        lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        lc.set_editor_property("intensity", lux)
        lc.set_editor_property("cast_shadows", shadows)
        safe(lambda: lc.set_editor_property("atmosphere_sun_light", False))
        spawned.append(la)
        return la

    def camera(px_w, px_h):
        cam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 100), unreal.Rotator())
        spawned.append(cam)
        cc = cam.get_editor_property("capture_component2d")
        rt = RL.create_render_target2d(w, px_w, px_h, unreal.TextureRenderTargetFormat.RTF_RGBA8)
        cc.set_editor_property("texture_target", rt)
        cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        cc.set_editor_property("capture_every_frame", False)
        cc.set_editor_property("capture_on_movement", False)
        # a 1 cm near plane (the engine's 10 cm default cuts the receiver open at the 25 cm ADS eye)
        safe(lambda: cc.set_editor_property("override_custom_near_clipping_plane", True))
        safe(lambda: cc.set_editor_property("custom_near_clipping_plane", 1.0))
        safe(lambda: cc.set_editor_property("always_persist_rendering_state", True))
        pp = cc.get_editor_property("post_process_settings")
        for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                     ("override_auto_exposure_bias", True), ("auto_exposure_bias", 1.5),
                     ("override_auto_exposure_apply_physical_camera_exposure", True), ("auto_exposure_apply_physical_camera_exposure", False),
                     ("override_motion_blur_amount", True), ("motion_blur_amount", 0.0),
                     ("override_bloom_intensity", True), ("bloom_intensity", 0.0),
                     ("override_vignette_intensity", True), ("vignette_intensity", 0.0)):
            safe(lambda k=k, v=v: pp.set_editor_property(k, v))
        cc.set_editor_property("post_process_settings", pp)
        cc.set_editor_property("post_process_blend_weight", 1.0)
        return cam, cc, rt

    def aim(cam, cc, loc, fwd, up=(0, 0, 1), fov=None, ortho_w=None):
        cam.set_actor_location_and_rotation(unreal.Vector(*loc), ML.make_rot_from_xz(unreal.Vector(*fwd), unreal.Vector(*up)), False, False)
        if ortho_w is not None:
            cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
            cc.set_editor_property("ortho_width", float(ortho_w))
            safe(lambda: cc.set_editor_property("auto_calculate_ortho_planes", False))
        else:
            cc.set_editor_property("projection_type", unreal.CameraProjectionMode.PERSPECTIVE)
            cc.set_editor_property("fov_angle", float(fov or 40.0))

    def shoot(cc, rt, name, n=6):
        for _ in range(n):
            cc.capture_scene()
        RL.export_render_target(w, rt, str(RDIR), name + ".png")
        return name

    def sk_actor(loc=(0, 0, 0), rot_=None):
        a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(*loc), rot_ or unreal.Rotator())
        spawned.append(a)
        c = a.get_editor_property("skeletal_mesh_component")
        c.set_skinned_asset_and_update(sk)
        c.set_material(0, mats["Metal"])
        c.set_material(1, mats["Chassis"])
        return a, c

    def st_actor(mesh, loc=(0, 0, 0), rot_=None, matlist=None):
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), rot_ or unreal.Rotator())
        spawned.append(a)
        c = a.get_editor_property("static_mesh_component")
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_static_mesh(mesh)
        for i, m in enumerate(matlist or []):
            c.set_material(i, m)
        return a, c

    # an unlit backdrop (transient material, never saved) and a lit ground (engine plane + default material)
    bdm = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_GC_Backdrop_Transient", f"{DEST}/Transient", unreal.Material, unreal.MaterialFactoryNew())
    bdm.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    safe(lambda: bdm.set_editor_property("two_sided", True))
    _c = MEL.create_material_expression(bdm, unreal.MaterialExpressionConstant3Vector, -300, 0)
    _c.set_editor_property("constant", unreal.LinearColor(0.18, 0.18, 0.19, 1.0))
    MEL.connect_material_property(_c, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(bdm)
    gm = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_GC_Ground_Transient", f"{DEST}/Transient", unreal.Material, unreal.MaterialFactoryNew())
    _g = MEL.create_material_expression(gm, unreal.MaterialExpressionConstant3Vector, -300, 0)
    _g.set_editor_property("constant", unreal.LinearColor(0.5, 0.5, 0.5, 1.0))
    MEL.connect_material_property(_g, "", unreal.MaterialProperty.MP_BASE_COLOR)
    _r = MEL.create_material_expression(gm, unreal.MaterialExpressionConstant, -300, 200)
    _r.set_editor_property("r", 0.9)
    MEL.connect_material_property(_r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(gm)
    res["material_stats"] = safe(lambda: [str(MEL.get_statistics(bdm)), str(MEL.get_statistics(gm))])
    # engine materials (cooked shader maps; materials made in this process may still be compiling at capture time)
    eng = unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial")
    res["engine_material"] = eng.get_path_name() if eng else None
    # measured: engine / transient materials render black in this commandlet (their shader maps are not ready at
    # capture time); the check materials compiled in pass A render, so the ground uses the walnut check material
    gm = mats["Chassis"]
    plane = unreal.load_asset("/Engine/BasicShapes/Cube")   # a flat cube: lit from any side
    plane.get_bounding_box(); plane.get_num_triangles(0)   # finishes the async build (else it renders nothing)
    # ------------------------------------------------------------------ 4. U4 First Person rendering on a lit ground
    u4 = {"note": "FirstPersonPrimitiveType per component; VSM on; light from the side so a cast shadow lands beside the gun"}
    SCOPE = unreal.load_asset(f"{DEST}/{C.SCOPE}")
    SCOPE.get_bounding_box(); SCOPE.get_num_triangles(0)
    OFF = C.scope_offset_cm()

    def scope_on(c, fp_type=None, forced=None, cast=True):
        sa, scc = st_actor(SCOPE, (0, 0, 0), None, [mats["Scope_Body"], mats["Scope_Lens"]])
        scc.attach_to_component(c, "Rail_Top", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                                unreal.AttachmentRule.SNAP_TO_TARGET, False)
        scc.set_relative_location(unreal.Vector(OFF, 0.0, 0.0), False, False)
        scc.set_cast_shadow(cast)
        if fp_type is not None:
            safe(lambda: scc.set_first_person_primitive_type(fp_type))
        if forced is not None:
            force_lod(scc, forced)
        return sa, scc

    sun = light((0.0, 0.55, -0.835), 6.0, True)
    sky = light((0.3, -0.4, 0.86), 0.6, False)
    ga, gc = st_actor(plane, (25.0, 0.0, -26.0), None, [gm])
    ga.set_actor_scale3d(unreal.Vector(1.9, 1.4, 0.02))
    ucam, ucc, urt = camera(900, 700)
    aim(ucam, ucc, (25.0, -10.0, 150.0), (0.0, 0.07, -1.0), up=(1, 0, 0), fov=50.0)
    FPT = unreal.FirstPersonPrimitiveType
    u4["shots"] = {}
    u4["shots"]["ground_only"] = shoot(ucc, urt, "u4_ground_only")

    def scenario(name, fp_type, cast=True, forced=None):
        a, c = sk_actor()
        c.set_cast_shadow(cast)
        safe(lambda: c.set_first_person_primitive_type(fp_type))
        if forced is not None:
            force_lod(c, forced)
        ma, mc = st_actor(mag, (0, 0, 0), None, [mats["Mag"]])
        mc.attach_to_component(c, "Mag", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                               unreal.AttachmentRule.SNAP_TO_TARGET, False)
        mc.set_cast_shadow(cast)
        safe(lambda: mc.set_first_person_primitive_type(fp_type))
        if forced is not None:
            force_lod(mc, forced)
        sa, scc = scope_on(c, fp_type, None if forced is None else min(forced, 3), cast)
        info = {"fp_type": str(safe(lambda: c.get_editor_property("first_person_primitive_type"))),
                "mag_fp_type": str(safe(lambda: mc.get_editor_property("first_person_primitive_type"))),
                "scope_fp_type": str(safe(lambda: scc.get_editor_property("first_person_primitive_type"))),
                "forced_lod_model": safe(lambda: int(c.get_editor_property("forced_lod_model"))),
                "scope_forced_lod_model": safe(lambda: int(scc.get_editor_property("forced_lod_model"))),
                "cast_shadow": bool(c.get_editor_property("cast_shadow"))}
        info["file"] = shoot(ucc, urt, name)
        info["predicted_lod_after_capture"] = safe(lambda: int(c.get_predicted_lod_level()))
        for x in (sa, ma, a):
            EAS.destroy_actor(x)
            spawned.remove(x)
        return info
    u4["shots"]["tp_noshadow_mask"] = scenario("u4_tp_noshadow", FPT.WORLD_SPACE_REPRESENTATION, cast=False)
    u4["shots"]["tp"] = scenario("u4_tp", FPT.WORLD_SPACE_REPRESENTATION)
    u4["shots"]["none"] = scenario("u4_none", FPT.NONE)
    u4["shots"]["fp"] = scenario("u4_fp", FPT.FIRST_PERSON, forced=1)
    # ForcedLodModel: right side, 120 cm, perspective, the capture's LOD distance factor x 60 (every auto-LOD component
    # falls to its last LOD), references at forced LOD0 / LOD3, then the auto TP component and the FP component
    aim(ucam, ucc, (25.0, 120.0, 5.0), (0.0, -1.0, 0.0), fov=55.0)
    u4["lod_view"] = "right side, 120 cm, 55 deg"
    u4["lod_distance_factor_set"] = safe(lambda: ucc.set_editor_property("lod_distance_factor", 60.0))
    u4["lod_ref0"] = scenario("u4_lod_ref0", FPT.WORLD_SPACE_REPRESENTATION, forced=1)
    u4["lod_ref3"] = scenario("u4_lod_ref3", FPT.WORLD_SPACE_REPRESENTATION, forced=4)
    u4["lod_tp_auto"] = scenario("u4_lod_tp_auto", FPT.WORLD_SPACE_REPRESENTATION)
    u4["lod_fp_forced"] = scenario("u4_lod_fp_forced", FPT.FIRST_PERSON, forced=1)
    safe(lambda: ucc.set_editor_property("lod_distance_factor", 1.0))
    res["U4"] = u4
    for x in (sun, sky, ga):
        EAS.destroy_actor(x)
        spawned.remove(x)
    dump()
    # ------------------------------------------------------------------ 5. U4 scope pair on the SK (gun at an arbitrary transform)
    srot = unreal.Rotator()
    srot.roll, srot.pitch, srot.yaw = 21.0, -8.0, 133.0
    sloc = unreal.Vector(77.0, -88.0, 99.0)
    a, c = sk_actor()
    a.set_actor_location_and_rotation(sloc, srot, False, False)
    sa, scc = scope_on(c)
    Wg = c.get_world_transform()
    sp = {"attach_socket": str(scc.get_attach_socket_name()), "relative_to_parent": T(scc.get_relative_transform()),
          "scope_world_scale": v3(scc.get_world_transform().scale3d),
          "gun_socket_Rail_Top": T(c.get_socket_transform("Rail_Top", RTS)), "gun_socket_Muzzle": T(c.get_socket_transform("Muzzle", RTS)),
          "gun_socket_MuzzleSeat": T(c.get_socket_transform("MuzzleSeat", RTS)), "scope_sockets_in_gun": {}}
    for sn in ("Mount", "Sight", "EyePoint", "Lens_Front", "CenterOfMass"):
        wst = scc.get_socket_transform(sn, unreal.RelativeTransformSpace.RTS_WORLD)
        sp["scope_sockets_in_gun"][sn] = T(ML.make_relative_transform(wst, Wg))
    res["U4_scope_on_SK"] = sp
    for x in (sa, a):
        EAS.destroy_actor(x)
        spawned.remove(x)
    dump()
    # ------------------------------------------------------------------ 6. look captures
    light((0.35, 0.55, -0.75), 6.0)
    light((-0.6, -0.5, 0.4), 2.0)
    light((0.1, -0.8, -0.2), 2.0)
    cam, cc, rtt = camera(1600, 1000)
    shots = []
    G = {}

    def pose(clip=None, frame=0, fps=30.0):
        """a FRESH gun (SK + magazine + scope) per pose: a second override_animation_data on one component did not
        re-pose it (measured: the bipod stayed folded after the bolt pose); the runtime sampling uses fresh actors too."""
        for k_ in ("sa", "ma", "a"):
            if k_ in G:
                EAS.destroy_actor(G[k_])
                spawned.remove(G[k_])
        a_, c_ = sk_actor()
        if clip:
            c_.override_animation_data(unreal.load_asset(f"{DEST}/{clip}"), False, False, frame / fps, 0.0)
        ma_, mc_ = st_actor(mag, (0, 0, 0), None, [mats["Mag"]])
        mc_.attach_to_component(c_, "Mag", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                                unreal.AttachmentRule.SNAP_TO_TARGET, False)
        sa_, scc_ = scope_on(c_)
        G.update(a=a_, ma=ma_, sa=sa_)
        return a_, c_, ma_, mc_, sa_, scc_
    a, c, ma, mc, sa, scc = pose()
    views = {
        "look_hero34": dict(loc=(-75.0, 160.0, 75.0), fwd=(0.50, -1.0, -0.42), fov=45.0),   # W5: pulled back (stock was cut)
        "look_right_side": dict(loc=(25.0, 200.0, 2.0), fwd=(0, -1, 0), ortho_w=125.0),
        "look_left_side": dict(loc=(25.0, -200.0, 2.0), fwd=(0, 1, 0), ortho_w=125.0),
        "look_receiver_right_close": dict(loc=(12.0, 40.0, 14.0), fwd=(0.05, -1.0, -0.15), fov=45.0),
    }
    for nm_, v in views.items():
        aim(cam, cc, v["loc"], v["fwd"], fov=v.get("fov"), ortho_w=v.get("ortho_w"))
        shots.append(shoot(cc, rtt, nm_))
    # the bolt open and back (A_SR01_BoltCycle frame 15: rotated -60, slid 88 mm), right side close-up of the port
    a, c, ma, mc, sa, scc = pose("A_SR01_BoltCycle", 15)
    res["bolt_open_back_handle_cm"] = v3(c.get_socket_transform("BoltHandle", RTS).translation)
    v = dict(loc=(10.0, 45.0, 16.0), fwd=(0.0, -1.0, -0.2), fov=45.0)
    aim(cam, cc, v["loc"], v["fwd"], fov=v["fov"])
    shots.append(shoot(cc, rtt, "look_bolt_open_port"))
    # the bipod deployed (A_SR01_BipodDeploy's last frame: legs +90 with the 12 deg splay, extensions 38 mm)
    a, c, ma, mc, sa, scc = pose("A_SR01_BipodDeploy", 36)
    res["deployed_feet_cm"] = {k: v3(c.get_socket_transform(k, RTS).translation) for k in ("BipodFoot_L", "BipodFoot_R")}
    for nm_, v in (("look_deployed_hero34", dict(loc=(140.0, 120.0, 40.0), fwd=(-0.75, -1.0, -0.35), fov=45.0)),
                   ("look_deployed_right", dict(loc=(25.0, 200.0, -8.0), fwd=(0, -1, 0), ortho_w=125.0)),
                   ("look_deployed_front", dict(loc=(220.0, 0.0, -5.0), fwd=(-1, 0, 0), ortho_w=60.0))):
        aim(cam, cc, v["loc"], v["fwd"], fov=v.get("fov"), ortho_w=v.get("ortho_w"))
        shots.append(shoot(cc, rtt, nm_))
    a, c, ma, mc, sa, scc = pose()
    # the scope view: the camera at EyePoint looking down Sight (+X), the scope itself hidden from this capture, a board
    # 10 m down range and a 1.5 cm marker where the BORE line (Muzzle socket +X) meets the board's plane
    st_ep = scc.get_socket_transform("EyePoint", unreal.RelativeTransformSpace.RTS_WORLD)
    st_si = scc.get_socket_transform("Sight", unreal.RelativeTransformSpace.RTS_WORLD)
    mz = c.get_socket_transform("Muzzle", unreal.RelativeTransformSpace.RTS_WORLD)
    fx = st_si.transform_direction(unreal.Vector(1, 0, 0))
    up = st_si.transform_direction(unreal.Vector(0, 0, 1))
    side = st_si.transform_direction(unreal.Vector(0, 1, 0))
    eye = st_ep.translation
    RANGE = 1000.0
    board_c = eye + fx * RANGE
    bo, boc = st_actor(plane, (board_c.x + fx.x * 1.5, board_c.y + fx.y * 1.5, board_c.z + fx.z * 1.5),
                       ML.make_rot_from_z(unreal.Vector(-fx.x, -fx.y, -fx.z)), [eng or mats["Chassis"]])   # plain board (the atlas read as noise)
    bo.set_actor_scale3d(unreal.Vector(1.2, 1.2, 0.02))
    mfx = mz.transform_direction(unreal.Vector(1, 0, 0))
    tb = (board_c - mz.translation).dot(fx) / max(mfx.dot(fx), 1e-9)
    bore_pt = mz.translation + mfx * tb
    mk_, mkc = st_actor(plane, (bore_pt.x, bore_pt.y, bore_pt.z), None, [mats["Scope_Lens"]])
    mk_.set_actor_scale3d(unreal.Vector(0.015, 0.015, 0.015))
    FOV = 6.0
    res["scope_view_hidden_set"] = safe(lambda: cc.set_editor_property("hidden_actors", [sa]))
    aim(cam, cc, (eye.x, eye.y, eye.z), (fx.x, fx.y, fx.z), up=(up.x, up.y, up.z), fov=FOV)
    shots.append(shoot(cc, rtt, "look_scope_view"))
    safe(lambda: cc.set_editor_property("hidden_actors", []))
    res["scope_view"] = {"eye_world": v3(eye), "sight_dir": v3(fx), "sight_up": v3(up), "range_cm": RANGE, "fov_deg": FOV,
                         "px": [1600, 1000], "bore_point_world": v3(bore_pt),
                         "bore_drop_below_sight_line_cm": float((board_c - bore_pt).dot(up)),
                         "bore_lateral_cm": float((bore_pt - board_c).dot(side)),
                         "muzzle_dir": v3(mfx), "muzzle_dir_dot_sight_dir": float(mfx.dot(fx))}
    for x in (bo, mk_):
        EAS.destroy_actor(x)
        spawned.remove(x)
    # LOD strip: forced LOD0..3, right side (the scope has 3 LODs)
    for lod in range(4):
        force_lod(c, lod + 1)
        force_lod(mc, lod + 1)
        force_lod(scc, min(lod, 2) + 1)
        v = views["look_right_side"]
        aim(cam, cc, v["loc"], v["fwd"], ortho_w=v["ortho_w"])
        shots.append(shoot(cc, rtt, f"look_lod{lod}_right"))
    force_lod(c, 0)
    force_lod(mc, 0)
    force_lod(scc, 0)
    # the static twin, for the same right view
    for x in (sa, ma, a):
        EAS.destroy_actor(x)
        spawned.remove(x)
    ta, tc = st_actor(sm, (0, 0, 0), None, [mats["Metal"], mats["Chassis"], mats["Mag"]])
    v = views["look_right_side"]
    aim(cam, cc, v["loc"], v["fwd"], ortho_w=v["ortho_w"])
    shots.append(shoot(cc, rtt, "look_twin_right"))
    res["shots"] = shots
    res["status"] = "ok"
except Exception:  # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
finally:
    for a_ in spawned:
        safe(lambda a_=a_: EAS.destroy_actor(a_))
res["hashes_after"] = C.all_hashes()
res["exports_unchanged"] = res["hashes_after"] == res["hashes_before"]
dump()
unreal.log("SR_PASS_C_DONE status=" + res["status"])
