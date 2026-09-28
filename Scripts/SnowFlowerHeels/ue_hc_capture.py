"""Heels Unreal check, step 5: worn test in a FRESH offscreen editor (run_ue_heels.ps1 -Mode editor). Saves NOTHING.

A transient blank level: white floor, studio lights, BP_MH_PlayerFemale spawned (her asset untouched), her Body's anim class
switched ON THE INSTANCE to /Game/HeelsCheck/<RUN>/ABP_HeelsTest_<Clip> (clip -> CR_HeelPose), and the imported
SK_SnowFlowerHeels on a SkeletalMeshActor attached to her Body as a Leader Pose follower. Driven by a Slate post-tick
generator so every pose and capture gets real engine frames.

Per pose (clip, time, HeelAlpha) it waits for the pose to settle, dumps component-space transforms of every body bone
(plus the follower's foot/ball to prove Leader Pose), and captures the listed cameras (SceneCapture2D, FINAL_COLOR_LDR).
Then: real-time walk and run playback (AnimTime advanced by the world delta each tick, so the pelvis smoothing behaves as
in game) with the heel/leg bones dumped every tick, and an LOD sweep (camera distance -> predicted LOD of body and heels).
Writes WorkFiles/SnowFlowerHeels/ue/capture_<RUN>.json and Renders/SnowFlowerHeels/ue_<RUN>/*.png.
"""
import json
import math
import os
import time
import traceback

import unreal as ue

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
UEW = ROOT + "/WorkFiles/SnowFlowerHeels/ue"
RUN = json.load(open(UEW + "/run.json", encoding="utf-8"))["run"]
DEST = "/Game/HeelsCheck/" + RUN
SHOTS = ROOT + "/Renders/SnowFlowerHeels/ue_" + RUN
os.makedirs(SHOTS, exist_ok=True)
BP = "/Game/MetaHumans/MH_PlayerFemale/BP_MH_PlayerFemale.BP_MH_PlayerFemale_C"
# HC_MESH=shipped: the FBX exactly as shipped (imports with root bone scale 100 -> drawn 100x small as a follower);
# HC_MESH=fix: the TEST centimetre re-export (fixtest/SK_SnowFlowerHeels_cm), same geometry/weights/LODs/materials
MESH_KIND = os.environ.get("HC_MESH", "fix")
MESH = DEST + ("/SK_SnowFlowerHeels" if MESH_KIND == "shipped" else "/fixtest/SK_SnowFlowerHeels_cm")
LEN = {"Idle": 10.0, "Walk": 4.0, "Run": 2.5}
EAS = ue.get_editor_subsystem(ue.EditorActorSubsystem)
RTS = ue.RelativeTransformSpace.RTS_COMPONENT
REP = {"run": RUN, "status": "starting", "errors": [], "notes": [], "poses": [], "continuous": {}, "lod_sweep": [],
       "captures": []}
T0 = time.time()
SKIN_BONES = json.load(open(UEW + "/skin_data.json", encoding="utf-8"))["body"]["bones_used"] + [
    "calf_l", "calf_r", "thigh_l", "thigh_r", "root"]


def log(msg):
    REP["notes"].append("%.1fs %s" % (time.time() - T0, msg))
    ue.log("[HC_CAPTURE] " + msg)
    save()


def save():
    with open("%s/capture_%s%s.json" % (UEW, RUN, "" if MESH_KIND == "fix" else "_shipped"), "w", encoding="utf-8") as fh:
        json.dump(REP, fh, indent=0, default=str)


def world():
    return ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()


def tf_list(t):
    q = t.rotation
    return [round(t.translation.x, 5), round(t.translation.y, 5), round(t.translation.z, 5),
            round(q.x, 7), round(q.y, 7), round(q.z, 7), round(q.w, 7)]


def setup():
    ue.EditorLoadingAndSavingUtils.new_blank_map(False)
    w = world()
    REP["skm_methods"] = [m for m in dir(ue.SkeletalMeshComponent) if any(k in m for k in ("tick", "refresh", "update", "anim"))]
    for fn, args in (("editor_set_viewport_realtime", (True,)),):
        for holder in (ue.get_editor_subsystem(ue.LevelEditorSubsystem), ue.EditorLevelLibrary):
            if hasattr(holder, fn):
                try:
                    getattr(holder, fn)(*args)
                    REP["viewport_realtime"] = str(holder)
                    break
                except Exception as exc:  # noqa: BLE001
                    REP["viewport_realtime_err"] = str(exc)[:200]
    # floor
    floor = EAS.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(0, 0, 0), ue.Rotator())
    smc = floor.static_mesh_component
    smc.set_static_mesh(ue.load_asset("/Engine/BasicShapes/Plane"))
    floor.set_actor_scale3d(ue.Vector(40, 40, 1))
    base = ue.load_asset("/Engine/BasicShapes/BasicShapeMaterial")
    mid = smc.create_dynamic_material_instance(0, base)
    try:
        mid.set_vector_parameter_value("Color", ue.LinearColor(0.82, 0.82, 0.82, 1))
    except Exception as exc:  # noqa: BLE001
        log("floor color: %s" % exc)
    # lights (roll, pitch, yaw positional)
    for pitch, yaw, inten, shadows in ((-40.0, -140.0, 4.0, True), (-20.0, 60.0, 1.6, False), (-55.0, 170.0, 1.2, False),
                                       (-10.0, -40.0, 0.8, False)):
        lt = EAS.spawn_actor_from_class(ue.DirectionalLight, ue.Vector(0, 0, 300), ue.Rotator(0, pitch, yaw))
        lt.light_component.set_intensity(inten)
        lt.light_component.set_cast_shadows(shadows)
    sky = EAS.spawn_actor_from_class(ue.SkyLight, ue.Vector(0, 0, 300), ue.Rotator())
    slc = sky.light_component
    slc.set_mobility(ue.ComponentMobility.MOVABLE)
    for cube in ("/Engine/MapTemplates/Sky/SunsetAmbientCubemap", "/Engine/MapTemplates/Sky/DaylightAmbientCubemap",
                 "/Engine/EngineResources/GrayDefaultCube"):
        tex = ue.load_asset(cube) if ue.EditorAssetLibrary.does_asset_exist(cube) else None
        if tex:
            try:
                slc.set_editor_property("source_type", ue.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
                slc.set_cubemap(tex)
                log("sky cubemap %s" % cube)
                break
            except Exception as exc:  # noqa: BLE001
                log("sky cubemap %s: %s" % (cube, exc))
    slc.set_intensity(1.0)
    slc.recapture_sky()
    # her
    cls = ue.load_class(None, BP)
    her = EAS.spawn_actor_from_class(cls, ue.Vector(0, 0, 0), ue.Rotator())
    comps = her.get_components_by_class(ue.SkeletalMeshComponent)
    body = [c for c in comps if c.get_name().startswith("Body")][0]
    REP["her_components"] = [c.get_name() for c in comps]
    REP["body_world"] = tf_list(body.get_world_transform())
    body.set_update_animation_in_editor(True)
    # heels: follower
    heels_actor = EAS.spawn_actor_from_class(ue.SkeletalMeshActor, ue.Vector(0, 0, 0), ue.Rotator())
    hc = heels_actor.skeletal_mesh_component
    mesh = ue.load_asset(MESH)
    if hasattr(hc, "set_skinned_asset_and_update"):
        hc.set_skinned_asset_and_update(mesh)
    else:
        hc.set_skeletal_mesh(mesh)
    heels_actor.set_actor_location_and_rotation(ue.Vector(0, 0, 0), ue.Rotator(), False, False)
    ok = heels_actor.attach_to_component(body, "None", ue.AttachmentRule.SNAP_TO_TARGET, ue.AttachmentRule.SNAP_TO_TARGET,
                                         ue.AttachmentRule.SNAP_TO_TARGET, False)
    if FOLLOW == "leader":
        hc.set_leader_pose_component(body, True)
    else:
        hc.set_animation_mode(ue.AnimationMode.ANIMATION_BLUEPRINT)
        hc.set_anim_instance_class(ue.load_class(None, DEST + "/ABP_HeelsFollow_CopyPose.ABP_HeelsFollow_CopyPose_C"))
    hc.set_visibility(True, True)
    REP["follow_mode"] = FOLLOW
    REP["mesh_kind"] = MESH_KIND
    REP["mesh"] = MESH
    REP["heels_attach"] = {"ok": ok, "parent": str(heels_actor.get_attach_parent_actor()),
                           "world": tf_list(hc.get_world_transform())}
    try:
        REP["heels_sync_attach_parent_lod"] = str(hc.get_editor_property("sync_attach_parent_lod"))
    except Exception as exc:  # noqa: BLE001
        REP["heels_sync_attach_parent_lod"] = "ERR %s" % str(exc)[:100]
    if os.environ.get("HC_DEBUG_STANDALONE", "0") == "1":
        # debug: the same mesh with NO leader pose, standing 60 cm to her left, and a cube for scale
        dbg = EAS.spawn_actor_from_class(ue.SkeletalMeshActor, ue.Vector(60, 0, 10), ue.Rotator())
        dbg.skeletal_mesh_component.set_skinned_asset_and_update(mesh)
        dbg.set_actor_label("HC_DEBUG_STANDALONE")
        dbg_b = EAS.spawn_actor_from_class(ue.SkeletalMeshActor, ue.Vector(0, -90, 0), ue.Rotator())
        dbg_b.skeletal_mesh_component.set_skinned_asset_and_update(mesh)
        dbg_b.set_actor_label("HC_DEBUG_LEADER_ONLY")
        cube = EAS.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(-60, 0, 10), ue.Rotator())
        cube.static_mesh_component.set_static_mesh(ue.load_asset("/Engine/BasicShapes/Cube"))
        cube.set_actor_scale3d(ue.Vector(0.2, 0.2, 0.2))
    # capture
    cap_actor = EAS.spawn_actor_from_class(ue.SceneCapture2D, ue.Vector(0, 0, 0), ue.Rotator())
    cap = cap_actor.get_component_by_class(ue.SceneCaptureComponent2D)
    cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    cap.set_editor_property("capture_every_frame", False)
    cap.set_editor_property("always_persist_rendering_state", True)
    pp = cap.get_editor_property("post_process_settings")
    for k, v in [("override_auto_exposure_method", True), ("auto_exposure_method", ue.AutoExposureMethod.AEM_MANUAL),
                 ("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.3),
                 ("override_auto_exposure_apply_physical_camera_exposure", True),
                 ("auto_exposure_apply_physical_camera_exposure", False)]:
        pp.set_editor_property(k, v)
    cap.set_editor_property("post_process_settings", pp)
    return {"world": w, "her": her, "body": body, "heels": hc, "cap_actor": cap_actor, "cap": cap, "mesh": mesh}


def ref_pose_cs(body):
    mesh = body.get_skinned_asset() if hasattr(body, "get_skinned_asset") else body.skeletal_mesh
    comp = ue.new_object(ue.SkeletalMeshComponent)
    comp.set_skinned_asset_and_update(mesh)
    local, parent = {}, {}
    for i in range(comp.get_num_bones()):
        n = str(comp.get_bone_name(i))
        local[n] = comp.get_ref_pose_transform(i)
        p = str(comp.get_parent_bone(n))
        parent[n] = None if p in ("None", "") else p
    cache = {}

    def cs(n):
        if n not in cache:
            cache[n] = local[n] if parent[n] is None else local[n].multiply(cs(parent[n]))
        return cache[n]
    return {n: tf_list(cs(n)) for n in local}


def bones_now(body, names=None):
    names = names or [str(body.get_bone_name(i)) for i in range(body.get_num_bones())]
    return {n: tf_list(body.get_socket_transform(n, RTS)) for n in names}


def set_vars(body, t, alpha):
    inst = body.get_anim_instance()
    inst.set_editor_property("AnimTime", float(t))
    inst.set_editor_property("HeelAlpha", float(alpha))


def pump(body):
    """The editor world does not tick skeletal animation by itself here: evaluate it explicitly."""
    for fn, args in (("tick_animation", (1.0 / 30.0, False)), ("refresh_bone_transforms", ()), ("tick_pose", (1.0 / 30.0, False))):
        if hasattr(body, fn):
            try:
                getattr(body, fn)(*args)
                REP.setdefault("pump_ok", set()).add(fn) if isinstance(REP.get("pump_ok"), set) else REP.__setitem__("pump_ok", {fn})
            except Exception as exc:  # noqa: BLE001
                REP.setdefault("pump_err", {})[fn] = str(exc)[:200]


LOCAL_FWD = json.load(open(UEW + "/build_cr.json", encoding="utf-8"))["local_forward_in_foot"]


def foot_frame(ctx, s):
    """Centre of her shoe s (between ankle and ball, 7 cm up), its horizontal forward and outward directions."""
    body = ctx["body"]
    f = body.get_socket_transform("foot_" + s, RTS)
    b = body.get_socket_transform("ball_" + s, RTS)
    fw = f.rotation.rotate_vector(ue.Vector(*LOCAL_FWD[s]))
    fw = ue.Vector(fw.x, fw.y, 0.0)
    fw = fw * (1.0 / max(fw.length(), 1e-6))
    out = ue.Vector(fw.y, -fw.x, 0.0) if s == "r" else ue.Vector(-fw.y, fw.x, 0.0)
    c = (f.translation + b.translation) * 0.5
    return ue.Vector(c.x, c.y, 7.0), fw, out


def dyn_cam(ctx, cam):
    c, fw, out = foot_frame(ctx, "r")
    if cam == "close_ref_R":
        a, e, d = math.radians(48), math.radians(22), 75.0
        dirv = fw * math.cos(a) + out * math.sin(a)
        return (c + dirv * (d * math.cos(e)) + ue.Vector(0, 0, d * math.sin(e)), c, 26)
    if cam == "close_side_R":
        return (c + out * 85.0 + ue.Vector(0, 0, 3), c + ue.Vector(0, 0, 1), 26)
    if cam == "close_heel_ground_R":
        tip = c - fw * 11.0
        tip = ue.Vector(tip.x, tip.y, 2.0)
        return (tip + out * 45.0 - fw * 25.0 + ue.Vector(0, 0, 1.5), tip, 24)
    if cam == "close_back_R":
        return (c - fw * 75.0 + ue.Vector(0, 0, 11), c - fw * 5.0 + ue.Vector(0, 0, 3), 30)
    cl, _, _ = foot_frame(ctx, "l")
    mid = (c + cl) * 0.5
    mid = ue.Vector(mid.x, mid.y, 9.0)
    return (mid + ue.Vector(70, 95, 29), mid, 36)


def aim(ctx, loc, target, fov, w, h, cam=None):
    if cam in ("close_ref_R", "close_side_R", "close_heel_ground_R", "close_back_R", "feet_front34"):
        loc, target, fov = dyn_cam(ctx, cam)
    loc = loc if isinstance(loc, ue.Vector) else ue.Vector(*loc)
    target = target if isinstance(target, ue.Vector) else ue.Vector(*target)
    ctx["cap_actor"].set_actor_location_and_rotation(loc, ue.MathLibrary.find_look_at_rotation(loc, target), False, False)
    ctx["cap"].set_editor_property("fov_angle", fov)
    key = (w, h)
    if ctx.get("rt_key") != key:
        rt = ue.RenderingLibrary.create_render_target2d(ctx["world"], w, h, ue.TextureRenderTargetFormat.RTF_RGBA8)
        rt.set_editor_property("target_gamma", 2.2)
        ctx["cap"].set_editor_property("texture_target", rt)
        ctx["rt"], ctx["rt_key"] = rt, key


# right foot (UE -X) outer side; reference camera: 48 deg from the toe direction on the outer side, 22 deg elevation
def ref_cam(center, dist, az_deg, el_deg, toe=(-0.1713, 0.9852), outer=(-0.9852, -0.1713)):
    a, e = math.radians(az_deg), math.radians(el_deg)
    d = [math.cos(a) * toe[0] + math.sin(a) * outer[0], math.cos(a) * toe[1] + math.sin(a) * outer[1]]
    return ((center[0] + d[0] * dist * math.cos(e), center[1] + d[1] * dist * math.cos(e), center[2] + dist * math.sin(e)), center)


R_SHOE = (-15.5, 4.0, 7.0)
CAMS = {
    "front": ((0, 330, 92), (0, 0, 88), 32, 1000, 1400),
    "side": ((340, 0, 92), (0, 0, 88), 32, 1000, 1400),
    "threequarter": ((235, 235, 110), (0, 0, 88), 32, 1000, 1400),
    "back": ((0, -330, 92), (0, 0, 88), 32, 1000, 1400),
    "feet_front34": ((70, 95, 38), (0, 3, 9), 36, 1400, 1050),
    "close_ref_R": ref_cam(R_SHOE, 75, 48, 22) + (26, 1400, 1050),
    "close_side_R": ((-85, 2, 10), (-15, 2, 8), 26, 1400, 1050),
    "close_heel_ground_R": ((-55, -40, 3.5), (-15, -3, 2), 24, 1400, 1050),
    "close_back_R": ((-20, -75, 18), (-15, -3, 10), 30, 1400, 1050),
    "walk_side": ((360, 20, 90), (0, 20, 85), 34, 1000, 1400),
    "walk_feet": ((170, 20, 22), (0, 20, 14), 42, 1400, 1050),
    "walk_feet_R": ((-170, 20, 22), (0, 20, 14), 42, 1400, 1050),
}
POSES = [("Idle", 0.0, 1.0, ["front", "side", "threequarter", "back", "feet_front34", "close_ref_R", "close_side_R",
                             "close_heel_ground_R", "close_back_R"]),
         ("Idle", 0.0, 0.0, ["side", "feet_front34", "close_side_R"]),
         ("Idle", 5.0, 1.0, ["close_side_R"])]
POSES += [("Walk", round(k * 0.25, 3), 1.0, ["walk_side", "walk_feet"] if k % 2 == 0 else ["walk_feet"]) for k in range(8)]
POSES += [("Walk", 0.5, 0.0, ["walk_feet"])]
POSES += [("Run", round(k * 0.1, 3), 1.0, ["walk_side", "walk_feet"] if k % 2 == 0 else ["walk_feet"]) for k in range(8)]
POSES += [("Walk", 0.5, 1.0, ["close_side_R", "close_back_R"]), ("Run", 0.1, 1.0, ["close_side_R", "close_back_R"]),
          ("Run", 0.3, 1.0, ["close_side_R", "close_back_R"]), ("Walk", 0.25, 1.0, ["close_side_R", "close_heel_ground_R"])]
POSES += [("Walk", round(k * 0.125, 3), 1.0, []) for k in range(32)]      # measurement only: one 4 s loop at 8 fps
POSES += [("Run", round(k * 0.0625, 4), 1.0, []) for k in range(40)]      # 2.5 s loop at 16 fps
POSES += [("Walk", round(k * 0.125, 3), 0.0, []) for k in range(32)]      # barefoot baselines
POSES += [("Run", round(k * 0.0625, 4), 0.0, []) for k in range(40)]


QUICK = os.environ.get("HC_QUICK", "0") == "1"
FOLLOW = os.environ.get("HC_FOLLOW", "leader")
CAMS["debug_wide"] = ((0, 200, 60), (0, -30, 15), 70, 1400, 1050)
if QUICK:
    POSES = [("Idle", 0.0, 1.0, ["feet_front34", "close_ref_R", "side"])]


def enter_pie(ctx):
    """Simulate-in-editor: the editor world never ticked her animation (measured), a PIE world does."""
    les = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    les.editor_play_simulate()
    for _ in range(600):
        yield 1
        gw = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world()
        if gw is not None:
            break
    yield 60
    gw = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world()
    if gw is None:
        raise RuntimeError("no PIE world")
    her = ue.GameplayStatics.get_all_actors_of_class(gw, ue.load_class(None, BP))[0]
    body = [c for c in her.get_components_by_class(ue.SkeletalMeshComponent) if c.get_name().startswith("Body")][0]
    heels_actor = [a for a in ue.GameplayStatics.get_all_actors_of_class(gw, ue.SkeletalMeshActor)
                   if a.get_attach_parent_actor() is not None][0]
    hc = heels_actor.skeletal_mesh_component
    if FOLLOW == "leader":
        hc.set_leader_pose_component(body, True)
    for a in ue.GameplayStatics.get_all_actors_of_class(gw, ue.SkeletalMeshActor):
        if a.get_actor_label() == "HC_DEBUG_LEADER_ONLY":
            a.skeletal_mesh_component.set_leader_pose_component(body, True)
            REP["debug_leader_only"] = "leader pose set, not attached, actor at y=-90"
    try:
        REP["follower_leader_prop"] = str(hc.get_editor_property("leader_pose_component"))
    except Exception as exc:  # noqa: BLE001
        REP["follower_leader_prop"] = "ERR %s" % str(exc)[:100]
    cap_actor = ue.GameplayStatics.get_all_actors_of_class(gw, ue.SceneCapture2D)[0]
    cap = cap_actor.get_component_by_class(ue.SceneCaptureComponent2D)
    for c in her.get_components_by_class(ue.ActorComponent):
        if "LODSync" in c.get_class().get_name():
            c.set_component_tick_enabled(False)
            REP["lodsync_disabled"] = c.get_name()
    for c in list(her.get_components_by_class(ue.SkeletalMeshComponent)) + [hc]:
        c.set_forced_lod(1)
    REP["pie_tick_options"] = {c.get_name(): str(c.get_editor_property("visibility_based_anim_tick_option"))
                               for c in list(her.get_components_by_class(ue.SkeletalMeshComponent)) + [hc]}
    if os.environ.get("HC_FLATN", "0") == "1":
        # diagnostic: the same test materials with the baked normal map swapped for a flat one
        flat = ue.load_asset("/Engine/EngineMaterials/FlatNormal")
        for i in range(3):
            mid = hc.create_dynamic_material_instance(i, hc.get_material(i))
            mid.set_texture_parameter_value("Normal", flat)
        REP["flat_normal_diagnostic"] = True
    ctx.update({"world": gw, "her": her, "body": body, "heels": hc, "cap_actor": cap_actor, "cap": cap, "rt_key": None})
    REP["pie"] = {"world": str(gw.get_name()), "heels_parent": str(heels_actor.get_attach_parent_actor()),
                  "body_anim_class": str(body.get_anim_instance().get_class().get_name()) if body.get_anim_instance() else None}
    log("entered simulate: %s" % REP["pie"])


def keep_rendered(ctx, n):
    """Her body only ticks its pose while it is rendered (VisibilityBasedAnimTickOption; changing that property on the
    PIE component killed its anim instance), so every waiting tick renders the capture view."""
    for _ in range(n):
        try:
            ctx["cap"].capture_scene()
        except Exception:  # noqa: BLE001
            pass
        yield 1


def program(ctx):
    yield from enter_pie(ctx)
    body, heels = ctx["body"], ctx["heels"]
    REP["ref_pose_cs"] = ref_pose_cs(body)
    REP["bone_names"] = [str(body.get_bone_name(i)) for i in range(body.get_num_bones())]
    cls = {c: ue.load_class(None, "%s/ABP_HeelsTest_%s.ABP_HeelsTest_%s_C" % (DEST, c, c)) for c in LEN}
    REP["abp_classes"] = {c: str(v) for c, v in cls.items()}
    body.set_forced_lod(1)
    heels.set_forced_lod(1)
    current = None
    first = True
    for i, (clip, t, alpha, cams) in enumerate(POSES):
        if clip != current:
            body.set_anim_instance_class(cls[clip])
            current = clip
            yield 5
            for _ in range(120):
                if body.get_anim_instance() is not None:
                    break
                yield 1
        set_vars(body, t, alpha)
        if not cams:
            aim(ctx, *CAMS["walk_feet"])
        yield from keep_rendered(ctx, 40 if first else (24 if cams else 12))
        if first:
            ue.AutomationLibrary.finish_loading_before_screenshot()
            yield 60
            ue.AutomationLibrary.finish_loading_before_screenshot()
            yield 30
            first = False
        inst = body.get_anim_instance()
        if i == 0:
            o, e = heels.get_owner().get_actor_bounds(False)
            REP["heels_debug"] = {"world": tf_list(heels.get_world_transform()), "visible": heels.is_visible(),
                                  "bounds_origin": [o.x, o.y, o.z], "bounds_extent": [e.x, e.y, e.z],
                                  "asset": str(heels.get_skinned_asset().get_path_name() if hasattr(heels, "get_skinned_asset") else "")}
        rec = {"i": i, "clip": clip, "t": t, "alpha": alpha,
               "abp_vars": [inst.get_editor_property("AnimTime"), inst.get_editor_property("HeelAlpha")],
               "anim_class": str(inst.get_class().get_name()),
               "bones": bones_now(body),
               "follower_foot": {s: tf_list(heels.get_socket_transform("foot_" + s, RTS)) for s in ("l", "r")},
               "follower_ball": {s: tf_list(heels.get_socket_transform("ball_" + s, RTS)) for s in ("l", "r")}}
        REP["poses"].append(rec)
        for cam in cams:
            loc, tgt, fov, w, h = CAMS[cam]
            aim(ctx, loc, tgt, fov, w, h, cam)
            for _ in range(10):
                ctx["cap"].capture_scene()
                yield 1
            name = "%s_%s%s%s_t%05.3f_a%d_%s.png" % (RUN, "" if MESH_KIND == "fix" else "SHIPPED_",
                                                    "FLATN_" if os.environ.get("HC_FLATN", "0") == "1" else "", clip, t, int(alpha), cam)
            ue.RenderingLibrary.export_render_target(ctx["world"], ctx["rt"], SHOTS, name)
            REP["captures"].append(name)
        if i % 10 == 0:
            log("pose %d/%d %s t=%.3f a=%.0f" % (i + 1, len(POSES), clip, t, alpha))
    # real-time playback (pelvis smoothing as in game)
    for clip, dur in ((() if QUICK else (("Walk", 8.0), ("Run", 5.0)))):
        body.set_anim_instance_class(cls[clip])
        aim(ctx, *CAMS["walk_feet"])
        yield from keep_rendered(ctx, 5)
        set_vars(body, 0.0, 1.0)
        yield from keep_rendered(ctx, 20)
        rows, tsum = [], 0.0
        while tsum < dur:
            dt = ue.GameplayStatics.get_world_delta_seconds(ctx["world"])
            tsum += max(dt, 1e-4)
            set_vars(body, tsum % LEN[clip], 1.0)
            yield from keep_rendered(ctx, 1)
            rows.append({"t": tsum, "dt": dt, "bones": bones_now(body, SKIN_BONES + ["pelvis"])})
        REP["continuous"][clip] = rows
        log("continuous %s: %d ticks" % (clip, len(rows)))
    # every heels LOD rendered on her (forced; in game the heels follow her body's LOD through sync_attach_parent_lod)
    body.set_anim_instance_class(cls["Idle"])
    set_vars(body, 0.0, 1.0)
    yield 20
    for lod in (1, 2, 3):
        for c in ctx["her"].get_components_by_class(ue.SkeletalMeshComponent):
            c.set_forced_lod(lod)
        heels.set_forced_lod(lod)
        yield 6
        for cam in ("feet_front34", "close_side_R"):
            loc, tgt, fov, w, h = CAMS[cam]
            aim(ctx, loc, tgt, fov, w, h, cam)
            for _ in range(10):
                ctx["cap"].capture_scene()
                yield 1
            name = "%s_%sLOD%d_%s.png" % (RUN, "" if MESH_KIND == "fix" else "SHIPPED_", lod - 1, cam)
            ue.RenderingLibrary.export_render_target(ctx["world"], ctx["rt"], SHOTS, name)
            REP["captures"].append(name)
    # LOD sweep (standing, forced LOD cleared, her LODSync back on, the level viewport camera placed with the capture)
    body.set_anim_instance_class(cls["Idle"])
    set_vars(body, 0.0, 1.0)
    for c in ctx["her"].get_components_by_class(ue.ActorComponent):
        if "LODSync" in c.get_class().get_name():
            c.set_component_tick_enabled(True)
    for c in ctx["her"].get_components_by_class(ue.SkeletalMeshComponent):
        c.set_forced_lod(0)
    heels.set_forced_lod(0)
    ues = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    yield 10
    for dist in ((150, 800) if QUICK else (150, 300, 500, 800, 1200, 2000, 3500, 6000)):
        aim(ctx, (0, dist, 60), (0, 0, 60), 50, 640, 480)
        try:
            loc = ue.Vector(0, dist, 60)
            ues.set_level_viewport_camera_info(loc, ue.MathLibrary.find_look_at_rotation(loc, ue.Vector(0, 0, 60)))
        except Exception as exc:  # noqa: BLE001
            REP["viewport_cam_err"] = str(exc)[:200]
        for _ in range(8):
            ctx["cap"].capture_scene()
            yield 1
        row = {"distance_cm": dist}
        for label, comp in (("body", body), ("heels", heels)):
            for fn in ("get_predicted_lod_level", "get_forced_lod"):
                try:
                    row["%s_%s" % (label, fn)] = getattr(comp, fn)()
                except Exception as exc:  # noqa: BLE001
                    row["%s_%s" % (label, fn)] = "ERR %s" % str(exc)[:80]
        REP["lod_sweep"].append(row)
        if dist in (150, 800, 3500):
            name = "%s_%slod_%05dcm.png" % (RUN, "" if MESH_KIND == "fix" else "SHIPPED_", dist)
            ue.RenderingLibrary.export_render_target(ctx["world"], ctx["rt"], SHOTS, name)
            REP["captures"].append(name)
    REP["status"] = "done"


STATE = {"gen": None, "wait": 0, "done": False, "handle": None, "ticks": 0}


def finish():
    STATE["done"] = True
    try:
        ue.get_editor_subsystem(ue.LevelEditorSubsystem).editor_request_end_play()
    except Exception:  # noqa: BLE001
        pass
    try:
        ue.unregister_slate_post_tick_callback(STATE["handle"])
    except Exception:  # noqa: BLE001
        pass
    REP["elapsed_s"] = time.time() - T0
    save()
    ue.SystemLibrary.quit_editor()


def tick(_dt):
    if STATE["done"] or STATE.get("busy"):
        return
    STATE["ticks"] += 1
    if STATE["wait"] > 0:
        STATE["wait"] -= 1
        return
    STATE["busy"] = True
    try:
        STATE["wait"] = next(STATE["gen"]) or 0
    except StopIteration:
        log("program finished")
        finish()
    except Exception:  # noqa: BLE001
        REP["errors"].append(traceback.format_exc())
        REP["status"] = "failed"
        finish()
    finally:
        STATE["busy"] = False


try:
    CTX = setup()
    log("setup done")
    STATE["gen"] = program(CTX)
    STATE["handle"] = ue.register_slate_post_tick_callback(tick)
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
except Exception:  # noqa: BLE001
    REP["errors"].append(traceback.format_exc())
    REP["status"] = "failed_setup"
    save()
    ue.SystemLibrary.quit_editor()
