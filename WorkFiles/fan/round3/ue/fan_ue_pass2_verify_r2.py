"""PASS 2 (a FRESH commandlet with a real RHI: -AllowCommandletRendering -RenderOffscreen): load what pass 1 saved
and measure it against the build's sidecars - nothing is imported or saved here.

    skeleton    78 bones (root + the build's 77), every parent, every reference-pose head (cm), no bone scale
    sockets     each socket's component transform against the sidecar
    LODs        3 LODs, the LOD settings' screen sizes
    animations  skeleton, frame count, play length at the file's rate
    fold        from the ENGINE's own bone poses (AnimationLibrary.get_bone_poses_for_time) at every key and every
                half key of every animation: each leaf vertex's copies on its two face bones (the crack), and the
                opening angle between the guards against the build's per-frame opening
    physics     the assigned physics asset's bodies against the sidecar (shapes, sizes, type, bounds, mass)
    bounds      a posed SkeletalMeshActor's component bounds hold every leaf corner at every tested opening
    renders     offscreen captures of the posed fan at the fold-sheet openings (tassel attached at its socket)
Results -> pass2.json, renders -> <FAN_OUT>/ue_renders/*.png.
"""
import json
import math
import sys
import time
import traceback

sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\fan\UnrealCheck")
import unreal  # noqa: E402

from fan_ue_common import (DEST, MESH, OUT, PHYS, REPORT, SIDECAR, TASSEL, TPHYS, TSIDECAR, component_space_ref,  # noqa: E402
                           compose_pose, dist, find_bodies, quat, safe, tf, write)

SUB = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
AL = unreal.AnimationLibrary
RL = unreal.RenderingLibrary
res = {"dest": DEST, "checks": {}, "gates": {}}
T0 = time.time()
FOLD_ANGLES = [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 163.2]


def v3(v):
    return [v.x, v.y, v.z]


def qang(a, b):
    d = abs(a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w)
    return math.degrees(2.0 * math.acos(min(1.0, d)))


def yaw_deg(t):
    x = unreal.MathLibrary.transform_direction(t, unreal.Vector(1.0, 0.0, 0.0))
    return math.degrees(math.atan2(x.y, x.x))


def wrap(a):
    return (a + 180.0) % 360.0 - 180.0


try:
    mesh = unreal.load_asset(MESH)
    skel = mesh.get_editor_property("skeleton")
    ref, parent, local = component_space_ref(mesh)
    # ------------------------------------------------------------------ skeleton
    want = ["root"] + list(SIDECAR["bones"])
    rest = SIDECAR["bones_rest"]
    head_err = max(dist(v3(ref[b].translation), rest[b]["head_cm"]) for b in rest)
    parents_bad = [b for b in rest if parent.get(b) != rest[b]["parent"]]
    scale_err = max(max(abs(s - 1.0) for s in v3(ref[b].scale3d)) for b in ref)
    res["checks"]["skeleton"] = {"bones": len(ref), "missing": sorted(set(want) - set(ref)), "extra": sorted(set(ref) - set(want)),
                                 "parents_bad": parents_bad, "max_head_error_cm": head_err, "max_scale_error": scale_err,
                                 "root_local_scale": v3(local["root"].scale3d)}
    res["gates"]["U1_bones_78_hierarchy_ref_pose"] = (len(ref) == 78 and not parents_bad and head_err <= 1e-3
                                                      and not res["checks"]["skeleton"]["missing"])
    res["gates"]["U2_no_bone_scale"] = scale_err <= 1e-4
    # ------------------------------------------------------------------ sockets
    socks = {}
    ok = True
    for s in SIDECAR["sockets"]:
        so = mesh.find_socket(s["name"])
        if so is None:
            socks[s["name"]] = "missing"
            ok = False
            continue
        bone = str(so.get_editor_property("bone_name"))
        rel = unreal.Transform()
        rel.translation = so.get_editor_property("relative_location")
        rel.rotation = so.get_editor_property("relative_rotation").quaternion()
        comp = unreal.MathLibrary.compose_transforms(rel, ref[bone])
        uc = s["unreal_component"]
        de = dist(v3(comp.translation), uc["location_cm"])
        da = qang(comp.rotation, quat(uc["quaternion_xyzw"]))
        sc = v3(so.get_editor_property("relative_scale"))
        socks[s["name"]] = {"bone": bone, "location_error_cm": de, "rotation_error_deg": da, "scale": sc}
        ok = ok and bone == s["bone"] and de <= 1e-3 and da <= 0.01 and max(abs(x - 1) for x in sc) < 1e-6
    res["checks"]["sockets"] = socks
    res["gates"]["U3_sockets"] = ok
    # ------------------------------------------------------------------ LODs
    ls = mesh.get_editor_property("lod_settings")
    sizes = safe(lambda: [g.get_editor_property("screen_size").get_editor_property("default")
                          for g in ls.get_editor_property("lod_groups")], [])
    res["checks"]["lods"] = {"count": SUB.get_lod_count(mesh), "screen_sizes": sizes,
                             "verts": [SUB.get_num_verts(mesh, i) for i in range(SUB.get_lod_count(mesh))]}
    res["gates"]["U4_lods"] = (SUB.get_lod_count(mesh) == 3 and len(sizes) == 3 and
                               all(abs(a - b) < 1e-4 for a, b in zip(sizes, SIDECAR["lod_screen_sizes"])))
    # ------------------------------------------------------------------ animations + fold from the engine's poses
    fc = SIDECAR["fold_check"]
    leaf_bones = sorted(fc["faces"])
    corner_local = {b: [unreal.MathLibrary.inverse_transform_location(ref[b], unreal.Vector(*c)) for c in cs]
                    for b, cs in fc["faces"].items()}
    names = [n for n in ref]
    anims = {}
    fold_ok = True
    worst = {"crack_cm": 0.0}
    posed_corners_at = {}
    for a in SIDECAR["animations"]:
        nm = a["file"][:-4]
        seq = unreal.load_asset(f"{DEST}/{nm}")
        rep_anim = REPORT["animations"][nm]
        fps = a["fps"]
        nfr = AL.get_num_frames(seq)
        length = seq.get_play_length()
        want_len = (a["frames"][1] - a["frames"][0]) / fps
        rec = {"skeleton_ok": seq.get_editor_property("skeleton") == skel, "num_frames": nfr,
               "expected_keys": a["frames"][1] - a["frames"][0] + 1, "play_length_s": length, "expected_s": want_len}
        keys = rep_anim["frames"]
        times = [(k / fps, "key", k) for k in range(keys)] + [((k + 0.5) / fps, "half", k) for k in range(keys - 1)]
        cracks, ang_err = [], []
        for t, kind, k in times:
            poses = AL.get_bone_poses_for_time(seq, names, t, False)
            loc = {n: p for n, p in zip(names, poses)}
            cs = compose_pose(loc, parent)
            P = {b: [unreal.MathLibrary.transform_location(cs[b], c) for c in corner_local[b]] for b in leaf_bones}
            cr = max(math.sqrt((P[f1][c1].x - P[f2][c2].x) ** 2 + (P[f1][c1].y - P[f2][c2].y) ** 2 +
                               (P[f1][c1].z - P[f2][c2].z) ** 2) for f1, c1, f2, c2 in fc["pairs"])
            cracks.append(cr)
            if cr > worst["crack_cm"]:
                worst = {"crack_cm": cr, "anim": nm, "time": t, "kind": kind}
            opening = abs(wrap(yaw_deg(cs["stick_25"]) - yaw_deg(cs["stick_00"])))
            if kind == "key":
                ang_err.append(abs(opening - rep_anim["opening_deg_per_frame"][k]))
            else:
                ang_err.append(-1.0)
            if nm == "A_Fan_Openness" and kind == "key":
                posed_corners_at[round(rep_anim["opening_deg_per_frame"][k], 3)] = [v3(p) for b in leaf_bones for p in P[b]]
        rec.update({"samples": len(times), "max_crack_cm": max(cracks), "max_opening_error_deg": max(ang_err)})
        fold_ok = fold_ok and rec["skeleton_ok"] and max(cracks) <= fc["gate_cm"] and max(ang_err) <= 0.01 and \
            abs(length - want_len) < 1e-4 and nfr in (rec["expected_keys"], rec["expected_keys"] - 1)
        anims[nm] = rec
    res["checks"]["animations"] = anims
    res["checks"]["fold_worst"] = worst
    res["gates"]["U5_animations_play_and_fold_holds"] = fold_ok
    # ------------------------------------------------------------------ physics
    def phys_check(m, path, bodies_spec):
        pa = m.get_editor_property("physics_asset")
        got = find_bodies(pa)
        out = {"asset": pa.get_path_name() if pa else None, "bodies": {}}
        good = pa is not None and pa.get_path_name().split(".")[0] == path
        for b in bodies_spec:
            bone = next((n for n in (b.get("unreal_bone_any_of") or [b["bone"]]) if n in got), None)
            if bone is None:
                out["bodies"][b["bone"]] = "missing"
                good = False
                continue
            bs = got[bone]
            g = bs.get_editor_property("agg_geom")
            boxes = [[e.get_editor_property(k) for k in ("x", "y", "z")] for e in g.get_editor_property("box_elems")]
            sphyls = [[e.get_editor_property("radius"), e.get_editor_property("length")] for e in g.get_editor_property("sphyl_elems")]
            spheres = [e.get_editor_property("radius") for e in g.get_editor_property("sphere_elems")]
            bi = bs.get_editor_property("default_instance")
            rec = {"bone": bone, "boxes_cm": boxes, "capsules_cm": sphyls, "spheres_cm": spheres,
                   "physics_type": str(bs.get_editor_property("physics_type")),
                   "consider_for_bounds": bool(bs.get_editor_property("consider_for_bounds")),
                   "collision": str(bi.get_editor_property("collision_enabled")),
                   "mass_kg": bi.get_editor_property("mass_in_kg_override")}
            want_boxes = [e["size_cm"] for e in b["elements"] if e["shape"] == "box"]
            want_caps = [[e["radius_mm"] * 0.1, e["length_mm"] * 0.1] for e in b["elements"] if e["shape"] == "capsule"]
            shape_ok = len(boxes) == len(want_boxes) and all(max(abs(x - y) for x, y in zip(p, q)) < 1e-3 for p, q in zip(boxes, want_boxes)) \
                and len(sphyls) == len(want_caps) and all(max(abs(x - y) for x, y in zip(p, q)) < 1e-3 for p, q in zip(sphyls, want_caps))
            kin = "KINEMATIC" in rec["physics_type"].upper()
            rec["ok"] = bool(shape_ok and kin == (b["physics_type"] == "Kinematic") and rec["consider_for_bounds"] == b["consider_for_bounds"]
                             and abs(rec["mass_kg"] - b["mass_kg"]) < 1e-6)
            good = good and rec["ok"]
            out["bodies"][b["bone"]] = rec
        out["extra_bodies"] = sorted(set(got) - {r["bone"] for r in out["bodies"].values() if isinstance(r, dict)})
        cons = [unreal.find_object(pa, f"PhysicsConstraintTemplate_{i}") for i in range(16)]
        out["constraints"] = sum(1 for c in cons if c is not None)
        return out, good and not out["extra_bodies"]
    fp, fok = phys_check(mesh, PHYS, SIDECAR["physics_bodies"])
    tmesh = unreal.load_asset(TASSEL)
    tp, tok = phys_check(tmesh, TPHYS, TSIDECAR["physics_bodies"])
    res["checks"]["physics"] = {"fan": fp, "tassel": tp}
    res["gates"]["U6_physics_assets"] = fok and tok and tp["constraints"] == len(TSIDECAR["physics_bodies"]) - 1
    # ------------------------------------------------------------------ world: bounds + renders
    openness = unreal.load_asset(f"{DEST}/A_Fan_Openness")
    op_deg = REPORT["animations"]["A_Fan_Openness"]["opening_deg_per_frame"]
    op_fps = REPORT["animations"]["A_Fan_Openness"]["fps"]

    def time_for(deg):
        deg = min(max(deg, op_deg[0]), op_deg[-1])
        for k in range(len(op_deg) - 1):
            if op_deg[k] <= deg <= op_deg[k + 1]:
                f = 0.0 if op_deg[k + 1] == op_deg[k] else (deg - op_deg[k]) / (op_deg[k + 1] - op_deg[k])
                return (k + f) / op_fps
        return (len(op_deg) - 1) / op_fps

    def posed(anim, t, tassel=True):
        """A FRESH SkeletalMeshActor per pose (MEASURED: a second override_animation_data on the same component
        in a commandlet keeps the first pose), LOD0 forced, the tassel attached at its socket."""
        act = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
        c = act.get_editor_property("skeletal_mesh_component")
        c.set_skinned_asset_and_update(mesh)
        safe(lambda: c.set_forced_lod(1))
        c.override_animation_data(anim, False, False, float(t), 0.0)
        acts = [act]
        info = {"stick_25_yaw": yaw_deg(c.get_socket_transform("stick_25", unreal.RelativeTransformSpace.RTS_COMPONENT)),
                "stick_00_yaw": yaw_deg(c.get_socket_transform("stick_00", unreal.RelativeTransformSpace.RTS_COMPONENT))}
        info["opening_deg"] = abs(wrap(info["stick_25_yaw"] - info["stick_00_yaw"]))
        # the fold from the RUNTIME pose (compressed clip, component evaluation): each leaf vertex's two copies
        cs = {b: c.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_COMPONENT) for b in leaf_bones}
        P = {b: [unreal.MathLibrary.transform_location(cs[b], q) for q in corner_local[b]] for b in leaf_bones}
        info["runtime_crack_cm"] = max(math.sqrt((P[f1][c1].x - P[f2][c2].x) ** 2 + (P[f1][c1].y - P[f2][c2].y) ** 2 +
                                                 (P[f1][c1].z - P[f2][c2].z) ** 2) for f1, c1, f2, c2 in fc["pairs"])
        info["compression"] = safe(lambda: AL.get_bone_compression_settings(anim).get_path_name())
        if tassel:
            ta = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
            tc = ta.get_editor_property("skeletal_mesh_component")
            tc.set_skinned_asset_and_update(tmesh)
            info["attached"] = safe(lambda: (tc.attach_to_component(c, "Tassel", unreal.AttachmentRule.SNAP_TO_TARGET,
                                                                  unreal.AttachmentRule.SNAP_TO_TARGET,
                                                                  unreal.AttachmentRule.KEEP_WORLD, False), True)[1])
            info["tassel_error_cm"] = dist(v3(tc.get_world_location()), v3(c.get_socket_location("Tassel")))
            acts.append(ta)
        return acts, c, info

    def expected_opening(deg):
        return min(max(deg, op_deg[0]), op_deg[-1])

    bounds = {}
    b_ok = True
    for deg in [op_deg[0], 30.0, 90.0, 150.0, op_deg[-1]]:
        t = time_for(deg)
        acts, c, info = posed(openness, t, tassel=False)
        o, e, r = unreal.SystemLibrary.get_component_bounds(c)
        k = min(posed_corners_at, key=lambda d: abs(d - deg))
        pts = posed_corners_at[k]
        outside = max(max(abs(p[i] - [o.x, o.y, o.z][i]) - [e.x, e.y, e.z][i] for i in range(3)) for p in pts)
        bounds[f"{deg:.1f}"] = {"origin": v3(o), "extent": v3(e), "corners_at_deg": k, "worst_corner_outside_cm": outside,
                                "pose_opening_deg": info["opening_deg"]}
        bounds[f"{deg:.1f}"]["runtime_crack_cm"] = info["runtime_crack_cm"]
        b_ok = b_ok and outside <= 0.0 and abs(info["opening_deg"] - expected_opening(deg)) < 0.25
        for x in acts:
            EAS.destroy_actor(x)
    res["checks"]["bounds"] = bounds
    res["gates"]["U7_bounds_hold_the_leaf"] = b_ok
    # renders
    import os
    rdir = OUT / "ue_renders"
    rdir.mkdir(parents=True, exist_ok=True)
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    spawned = []
    try:
        MEL = unreal.MaterialEditingLibrary
        # the check materials' shaders for this RHI (pass 1 ran with -nullrhi): compiled here, never saved
        compiled = []
        for m_ in (mesh, tmesh):
            for slot in m_.get_editor_property("materials"):
                mi = slot.get_editor_property("material_interface")
                if isinstance(mi, unreal.Material):
                    MEL.recompile_material(mi)
                    compiled.append(mi.get_name())
        res["checks"]["render_materials_compiled"] = compiled
        lights = []
        for travel, lux in (((0.25, 0.55, -1.0), 6.0), ((-0.6, -0.3, -0.5), 2.0)):
            d = unreal.Vector(*travel)
            la = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 100),
                                            unreal.MathLibrary.make_rot_from_x(d))
            lc = la.get_editor_property("directional_light_component")
            lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
            lc.set_editor_property("intensity", lux)
            lc.set_editor_property("atmosphere_sun_light", False)
            lights.append(la)
            spawned.append(la)
        cam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0.5, -6.0, 60.0),
                                         unreal.Rotator(roll=0.0, pitch=-90.0, yaw=-90.0))
        spawned.append(cam)
        cc = cam.get_editor_property("capture_component2d")
        px = 768
        rt = RL.create_render_target2d(w, px, px, unreal.TextureRenderTargetFormat.RTF_RGBA8)
        cc.set_editor_property("texture_target", rt)
        cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        cc.set_editor_property("capture_every_frame", False)
        cc.set_editor_property("capture_on_movement", False)
        cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
        cc.set_editor_property("ortho_width", 44.0)
        safe(lambda: cc.set_editor_property("always_persist_rendering_state", True))
        safe(lambda: cc.set_editor_property("auto_calculate_ortho_planes", False))
        pp = cc.get_editor_property("post_process_settings")
        for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                     ("override_auto_exposure_bias", True), ("auto_exposure_bias", 1.0),
                     ("override_auto_exposure_apply_physical_camera_exposure", True),
                     ("auto_exposure_apply_physical_camera_exposure", False),
                     ("override_motion_blur_amount", True), ("motion_blur_amount", 0.0),
                     ("override_bloom_intensity", True), ("bloom_intensity", 0.0),
                     ("override_vignette_intensity", True), ("vignette_intensity", 0.0)):
            safe(lambda: pp.set_editor_property(k, v))
        cc.set_editor_property("post_process_settings", pp)
        cc.set_editor_property("post_process_blend_weight", 1.0)
        # a second, HDR scene-colour capture: its alpha is 0 on geometry, 1 on empty space - the coverage mask
        # (MEASURED: scene depth exports clamped to 1, and a backdrop static mesh spawned in the
        # commandlet world does not render); the sheet composites the shots over a grey ground with it
        dcam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0.5, -6.0, 60.0),
                                          unreal.Rotator(roll=0.0, pitch=-90.0, yaw=-90.0))
        spawned.append(dcam)
        dc = dcam.get_editor_property("capture_component2d")
        drt = RL.create_render_target2d(w, px, px, unreal.TextureRenderTargetFormat.RTF_RGBA16F)
        dc.set_editor_property("texture_target", drt)
        dc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_SCENE_COLOR_HDR)
        dc.set_editor_property("capture_every_frame", False)
        dc.set_editor_property("capture_on_movement", False)
        dc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
        dc.set_editor_property("ortho_width", 44.0)
        safe(lambda: dc.set_editor_property("auto_calculate_ortho_planes", False))
        shots = []
        jobs = [(openness, time_for(max(deg, op_deg[0])), f"ue_fold_{deg:06.2f}.png", {"deg": deg}) for deg in FOLD_ANGLES]
        oc = unreal.load_asset(f"{DEST}/A_Fan_OpenClose")
        jobs += [(oc, 0.25, "ue_openclose_0.25s.png", {"anim": "A_Fan_OpenClose"}),
                 (oc, 0.65, "ue_openclose_hold_0.65s.png", {"anim": "A_Fan_OpenClose"})]
        pose_ok = True
        for anim, t, name, meta in jobs:
            acts, c, info = posed(anim, t)
            try:
                for _ in range(4):
                    cc.capture_scene()
                RL.export_render_target(w, rt, str(rdir), name)
                for _ in range(2):
                    dc.capture_scene()
                RL.export_render_target(w, drt, str(rdir), name[:-4] + "_hdr.png")
            finally:
                for x in acts:
                    EAS.destroy_actor(x)
            rec = dict(meta, time_s=t, file=str(rdir / name), **info)
            if "deg" in meta:
                rec["expected_opening_deg"] = expected_opening(meta["deg"])
                pose_ok = pose_ok and abs(info["opening_deg"] - rec["expected_opening_deg"]) < 0.25
            pose_ok = pose_ok and info.get("attached") is True and info.get("tassel_error_cm", 1) < 1e-3
            shots.append(rec)
        res["checks"]["runtime_fold"] = {"max_crack_cm": max(s_["runtime_crack_cm"] for s_ in shots),
                                         "max_opening_error_deg": max(abs(s_["opening_deg"] - s_["expected_opening_deg"])
                                                                      for s_ in shots if "expected_opening_deg" in s_),
                                         "compression": shots[0].get("compression")}
        res["gates"]["U9_runtime_pose_fold_holds"] = (res["checks"]["runtime_fold"]["max_crack_cm"] <= fc["gate_cm"] and
                                                      res["checks"]["runtime_fold"]["max_opening_error_deg"] <= 0.01)
        res["renders"] = {"camera": {"loc_cm": [0.5, -6.0, 60.0], "ortho_width_cm": 44.0, "px": px,
                                     "view": "front (down the rivet axis, component +Z toward the camera)"},
                          "shots": shots, "exists": [os.path.exists(s["file"]) for s in shots]}
        res["gates"]["U8_renders_written_posed_tassel_on_socket"] = all(res["renders"]["exists"]) and pose_ok
    finally:
        for a in spawned:
            safe(lambda: EAS.destroy_actor(a))
    res["gates"]["_all"] = all(v for k, v in res["gates"].items() if not k.startswith("_"))
    res["status"] = "ok"
except Exception:                                               # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
res["seconds"] = round(time.time() - T0, 1)
write("pass2.json", res)
unreal.log("FAN_PASS2_DONE status=" + res["status"])
