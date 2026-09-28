"""INDEPENDENT pass B (a SECOND fresh commandlet, real RHI, offscreen): load what pass A saved; measure; dump the
engine's own bone transforms (reference, raw clip, runtime component) for offline comparison against Blender;
render the posed fan. Nothing is imported or saved."""
import json, math, os, time, traceback
from pathlib import Path
import unreal

OUT = Path(os.environ["IV_OUT"])
DEST = os.environ["IV_DEST"]
SUB = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
AL = unreal.AnimationLibrary
RL = unreal.RenderingLibrary
ML = unreal.MathLibrary
RTS = unreal.RelativeTransformSpace.RTS_COMPONENT
res = {"dest": DEST, "t0": time.time()}


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa
        return {"error": f"{type(e).__name__}: {e}"[:300]}


def T(t):
    q = t.rotation
    return [t.translation.x, t.translation.y, t.translation.z, q.x, q.y, q.z, q.w, t.scale3d.x, t.scale3d.y, t.scale3d.z]


def v3(v):
    return [v.x, v.y, v.z]


def dump():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ivB.json").write_text(json.dumps(res, default=str), encoding="utf-8")


def ref_pose(mesh):
    c = unreal.new_object(unreal.SkeletalMeshComponent)
    c.set_skinned_asset_and_update(mesh)
    names, local, par = [], {}, {}
    for i in range(c.get_num_bones()):
        n = str(c.get_bone_name(i))
        names.append(n)
        local[n] = c.get_ref_pose_transform(i)
        p = str(c.get_parent_bone(n))
        par[n] = None if p in ("None", "") else p
    return names, local, par


def compose(local, par):
    w = {}

    def r(n):
        if n not in w:
            w[n] = local[n] if par[n] is None else ML.compose_transforms(local[n], r(par[n]))
        return w[n]
    for n in local:
        r(n)
    return w


try:
    mesh = unreal.load_asset(f"{DEST}/SK_Fan")
    tmesh = unreal.load_asset(f"{DEST}/SK_Fan_Tassel")
    skel = mesh.get_editor_property("skeleton")
    names, local, par = ref_pose(mesh)
    comp = compose(local, par)
    res["skeleton"] = {"asset": skel.get_path_name(), "mesh_bones": len(names), "order": names, "parents": par,
                       "ref_local": {n: T(local[n]) for n in names}, "ref_comp": {n: T(comp[n]) for n in names}}
    res["skeleton"]["skeleton_asset_bones"] = safe(lambda: len(unreal.AnimPoseExtensions.get_bone_names(skel.get_reference_pose())))
    tn, tl, tp = ref_pose(tmesh)
    res["tassel_skeleton"] = {"asset": tmesh.get_editor_property("skeleton").get_path_name(), "bones": tn, "parents": tp,
                              "ref_comp": {n: T(v) for n, v in compose(tl, tp).items()},
                              "shares_fan_skeleton": tmesh.get_editor_property("skeleton") == skel}
    # ---------------------------------------------------------------- sockets
    socks = {}
    for i in range(mesh.num_sockets()):
        s = mesh.get_socket_by_index(i)
        nm = str(s.get_editor_property("socket_name"))
        bone = str(s.get_editor_property("bone_name"))
        rel = unreal.Transform()
        rel.translation = s.get_editor_property("relative_location")
        rel.rotation = s.get_editor_property("relative_rotation").quaternion()
        rel.scale3d = s.get_editor_property("relative_scale")
        socks[nm] = {"bone": bone, "relative": T(rel), "component": T(ML.compose_transforms(rel, comp[bone]))}
    res["sockets"] = socks
    # ---------------------------------------------------------------- LODs, sections, slots, triangles
    lods = []
    for L in range(SUB.get_lod_count(mesh)):
        ns = SUB.get_num_sections(mesh, L)
        lods.append({"lod": L, "verts": SUB.get_num_verts(mesh, L), "sections": ns,
                     "section_slots": [SUB.get_lod_material_slot(mesh, L, s) for s in range(ns)]})
    res["lods"] = lods
    tl_ = []
    for L in range(SUB.get_lod_count(tmesh)):
        ns = SUB.get_num_sections(tmesh, L)
        tl_.append({"lod": L, "verts": SUB.get_num_verts(tmesh, L), "sections": ns})
    res["tassel_lods"] = tl_
    ls = mesh.get_editor_property("lod_settings")
    res["lod_settings"] = safe(lambda: {"asset": ls.get_path_name(), "screen_sizes": [
        g.get_editor_property("screen_size").get_editor_property("default") for g in ls.get_editor_property("lod_groups")]})
    res["tassel_lod_settings"] = str(tmesh.get_editor_property("lod_settings"))
    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    def tags(path):
        ad = ar.get_asset_by_object_path(path)
        out = {}
        for k in ("Triangles", "Vertices", "Bones", "Sockets", "LODs", "NumTriangles", "NumVertices", "MaterialSlots", "PhysicsAsset"):
            v = safe(lambda: ad.get_tag_value(k))
            out[k] = str(v)
        return out
    res["registry_tags"] = {"SK_Fan": tags(f"{DEST}/SK_Fan.SK_Fan"), "SK_Fan_Tassel": tags(f"{DEST}/SK_Fan_Tassel.SK_Fan_Tassel")}
    res["mesh_api_probe"] = [x for x in dir(mesh) if any(k in x.lower() for k in ("descr", "triang", "lod", "section"))]
    tri = {}
    for L in range(SUB.get_lod_count(mesh)):
        def md():
            d = mesh.get_mesh_description(L)
            return {"triangles": d.get_triangle_count(), "vertices": d.get_vertex_count(), "polygons": d.get_polygon_count()}
        tri[L] = safe(md)
    res["mesh_description"] = tri
    # ---------------------------------------------------------------- materials
    res["slots"] = [{"slot": str(s.get_editor_property("material_slot_name")),
                     "material": (s.get_editor_property("material_interface").get_path_name()
                                  if s.get_editor_property("material_interface") else None)}
                    for s in mesh.get_editor_property("materials")]
    res["tassel_slots"] = [str(s.get_editor_property("material_slot_name")) for s in tmesh.get_editor_property("materials")]
    masters = {}
    for p in ("/Game/NinjaPack/Materials/M_Fabric_Master", "/Game/NinjaPack/Materials/M_Steel_Master"):
        m = unreal.load_asset(p)
        masters[p] = None if m is None else {"used_with_skeletal_mesh": bool(m.get_editor_property("used_with_skeletal_mesh")),
                                             "automatically_set_usage_in_editor": safe(lambda: bool(m.get_editor_property("automatically_set_usage_in_editor")))}
    res["pack_masters"] = masters
    # ---------------------------------------------------------------- textures
    tex = {}
    for p in unreal.EditorAssetLibrary.list_assets(DEST + "/Textures", recursive=False, include_folder=False):
        t = unreal.load_asset(str(p))
        d = {}
        for k in ("srgb", "compression_settings", "mip_gen_settings", "lod_group", "flip_green_channel",
                  "compression_no_alpha", "address_x", "address_y", "power_of_two_mode", "never_stream", "max_texture_size",
                  "lossy_compression_amount", "compression_quality"):
            d[k] = str(safe(lambda: t.get_editor_property(k)))
        d["size"] = [t.blueprint_get_size_x(), t.blueprint_get_size_y()]
        tex[t.get_name()] = d
    res["textures"] = tex
    dump()
    # ---------------------------------------------------------------- physics
    def phys(m):
        pa = m.get_editor_property("physics_asset")
        if pa is None:
            return None
        out = {"asset": pa.get_path_name(), "bodies": {}, "constraints": []}
        for i in range(96):
            bs = unreal.find_object(pa, f"SkeletalBodySetup_{i}")
            if bs is None:
                continue
            g = bs.get_editor_property("agg_geom")
            bi = bs.get_editor_property("default_instance")
            el = []
            for kind, key in (("box", "box_elems"), ("capsule", "sphyl_elems"), ("sphere", "sphere_elems"), ("convex", "convex_elems")):
                for e in g.get_editor_property(key):
                    r = {"shape": kind}
                    for k in ("center", "rotation", "x", "y", "z", "radius", "length", "collision_enabled", "contribute_to_mass"):
                        v = safe(lambda: e.get_editor_property(k))
                        r[k] = v3(v) if isinstance(v, unreal.Vector) else ([v.pitch, v.yaw, v.roll] if isinstance(v, unreal.Rotator) else str(v) if not isinstance(v, (int, float)) else v)
                    el.append(r)
            out["bodies"][str(bs.get_editor_property("bone_name"))] = {
                "elements": el, "physics_type": str(bs.get_editor_property("physics_type")),
                "consider_for_bounds": bool(bs.get_editor_property("consider_for_bounds")),
                "collision": str(bi.get_editor_property("collision_enabled")),
                "override_mass": bool(bi.get_editor_property("override_mass")),
                "mass_kg": bi.get_editor_property("mass_in_kg_override"),
                "simulate": bool(bi.get_editor_property("simulate_physics")),
                "collision_profile": str(safe(lambda: bi.get_editor_property("collision_profile_name")))}
        for i in range(32):
            c = unreal.find_object(pa, f"PhysicsConstraintTemplate_{i}")
            if c is None:
                continue
            ci = safe(lambda: c.get_editor_property("default_instance"))
            rec = {"name": c.get_name()}
            if not isinstance(ci, dict):
                rec["bone1"] = str(safe(lambda: ci.get_editor_property("constraint_bone1")))
                rec["bone2"] = str(safe(lambda: ci.get_editor_property("constraint_bone2")))
            else:
                rec["instance_error"] = ci
                rec["props"] = [x for x in dir(c) if not x.startswith("_")][:60]
            out["constraints"].append(rec)
        out["constraints_api"] = safe(lambda: [str(x) for x in pa.get_constraints(True)])
        return out
    res["physics"] = {"fan": phys(mesh), "tassel": phys(tmesh)}
    # ---------------------------------------------------------------- bounds (asset)
    def bsb(b):
        return {"origin": v3(b.origin), "extent": v3(b.box_extent), "radius": b.sphere_radius}
    res["asset_bounds"] = {"bounds": safe(lambda: bsb(mesh.get_bounds())), "imported": safe(lambda: bsb(mesh.get_imported_bounds())),
                           "pos_ext": safe(lambda: v3(mesh.get_editor_property("positive_bounds_extension"))),
                           "neg_ext": safe(lambda: v3(mesh.get_editor_property("negative_bounds_extension")))}
    dump()
    # ---------------------------------------------------------------- animations: metadata + RAW poses
    anims = {}
    for base in ("A_Fan_OpenClose", "A_Fan_Openness", "A_Fan_OpenPose"):
        for nm in (base, base + "_Default"):
            seq = unreal.load_asset(f"{DEST}/{nm}")
            rec = {"skeleton_ok": seq.get_editor_property("skeleton") == skel,
                   "num_frames": AL.get_num_frames(seq), "num_keys": safe(lambda: AL.get_num_keys(seq)),
                   "play_length": seq.get_play_length(), "sequence_length": safe(lambda: AL.get_sequence_length(seq)),
                   "compression": safe(lambda: AL.get_bone_compression_settings(seq).get_path_name()),
                   "rate_scale": safe(lambda: AL.get_rate_scale(seq)),
                   "time_of_frame1": safe(lambda: AL.get_time_at_frame(seq, 1))}
            for k in ("loop", "enable_root_motion", "interpolation", "import_file_framerate", "import_resample_framerate",
                      "target_frame_rate", "retarget_source", "additive_anim_type", "compressed_data_size"):
                rec[k] = str(safe(lambda: seq.get_editor_property(k)))
            rec["sampling_rate"] = str(safe(lambda: seq.get_sampling_frame_rate()))
            if nm == base:
                n = AL.get_num_keys(seq) if isinstance(AL.get_num_keys(seq), int) else AL.get_num_frames(seq) + 1
                length = seq.get_play_length()
                steps = int(round(length * 60))
                times = [k / 60.0 for k in range(steps + 1)] + [(k + 0.5) / 60.0 for k in range(steps)]
                raw = {}
                for t in times:
                    poses = AL.get_bone_poses_for_time(seq, names, t, False)
                    cs = compose({n_: p for n_, p in zip(names, poses)}, par)
                    raw[f"{t:.5f}"] = {b: T(cs[b])[:7] for b in names}
                rec["raw"] = raw
            anims[nm] = rec
    res["anims"] = {k: {kk: vv for kk, vv in v.items() if kk != "raw"} for k, v in anims.items()}
    (OUT / "ivB_raw.json").write_text(json.dumps({k: v.get("raw") for k, v in anims.items() if "raw" in v}), encoding="utf-8")
    dump()
    # ---------------------------------------------------------------- RUNTIME poses (compressed clip, component)
    def posed(seq, t, lod=0, mats=None):
        a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
        c = a.get_editor_property("skeletal_mesh_component")
        c.set_skinned_asset_and_update(mesh)
        safe(lambda: c.set_forced_lod(lod + 1))
        if seq is not None:
            c.override_animation_data(seq, False, False, float(t), 0.0)
        if mats:
            for i, m in enumerate(mats):
                c.set_material(i, m)
        return a, c

    runtime = {}
    for nm in ("A_Fan_OpenClose", "A_Fan_OpenClose_Default", "A_Fan_Openness", "A_Fan_Openness_Default", "A_Fan_OpenPose", "A_Fan_OpenPose_Default"):
        seq = unreal.load_asset(f"{DEST}/{nm}")
        L = seq.get_play_length()
        steps = int(round(L * 60))
        ts = sorted(set([k / 60.0 for k in range(0, steps + 1, 2)] + [steps / 60.0] + [(k + 0.5) / 60.0 for k in range(1, steps, 7)]))
        out = {}
        for t in ts:
            a, c = posed(seq, t)
            out[f"{t:.5f}"] = {b: T(c.get_socket_transform(b, RTS))[:7] for b in names}
            EAS.destroy_actor(a)
        runtime[nm] = out
    (OUT / "ivB_runtime.json").write_text(json.dumps(runtime), encoding="utf-8")
    res["runtime_samples"] = {k: len(v) for k, v in runtime.items()}
    dump()
    # ---------------------------------------------------------------- posed component bounds
    op = unreal.load_asset(f"{DEST}/A_Fan_Openness")
    bnd = {}
    for f in (0, 1, 3, 9, 15, 30, 45, 60):
        a, c = posed(op, f / 60.0)
        o, e, r = unreal.SystemLibrary.get_component_bounds(c)
        bnd[str(f)] = {"origin": v3(o), "extent": v3(e)}
        # without a physics asset the component falls back to the mesh bounds
        safe(lambda: c.set_physics_asset(None, True))
        o2, e2, r2 = unreal.SystemLibrary.get_component_bounds(c)
        bnd[str(f)]["no_physics_origin"] = v3(o2)
        bnd[str(f)]["no_physics_extent"] = v3(e2)
        EAS.destroy_actor(a)
    res["posed_bounds"] = bnd
    dump()
    # ---------------------------------------------------------------- renders
    rdir = OUT / "renders"
    rdir.mkdir(parents=True, exist_ok=True)
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    MEL = unreal.MaterialEditingLibrary
    mats = {}
    for p in unreal.EditorAssetLibrary.list_assets(DEST + "/Materials", recursive=False, include_folder=False):
        m = unreal.load_asset(str(p))
        MEL.recompile_material(m)
        mats[m.get_name()] = m
    dbg = [mats["M_IV_Dbg_Leaf"], mats["M_IV_Dbg_Sticks"], mats["M_IV_Dbg_Rivet"]]
    spawned = []
    try:
        for travel, lux in (((0.3, 0.5, -1.0), 5.0), ((-0.5, -0.4, 0.6), 2.5), ((0.0, 0.0, 1.0), 1.5)):
            la = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 100), ML.make_rot_from_x(unreal.Vector(*travel)))
            lc = la.get_editor_property("directional_light_component")
            lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
            lc.set_editor_property("intensity", lux)
            safe(lambda: lc.set_editor_property("atmosphere_sun_light", False))
            spawned.append(la)
        px = 768

        def camera(fmt, src):
            cam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 100), unreal.Rotator())
            spawned.append(cam)
            cc = cam.get_editor_property("capture_component2d")
            rt = RL.create_render_target2d(w, px, px, fmt)
            cc.set_editor_property("texture_target", rt)
            cc.set_editor_property("capture_source", src)
            cc.set_editor_property("capture_every_frame", False)
            cc.set_editor_property("capture_on_movement", False)
            safe(lambda: cc.set_editor_property("always_persist_rendering_state", True))
            pp = cc.get_editor_property("post_process_settings")
            for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                         ("override_auto_exposure_bias", True), ("auto_exposure_bias", 1.0),
                         ("override_auto_exposure_apply_physical_camera_exposure", True), ("auto_exposure_apply_physical_camera_exposure", False),
                         ("override_motion_blur_amount", True), ("motion_blur_amount", 0.0),
                         ("override_bloom_intensity", True), ("bloom_intensity", 0.0),
                         ("override_vignette_intensity", True), ("vignette_intensity", 0.0)):
                safe(lambda: pp.set_editor_property(k, v))
            cc.set_editor_property("post_process_settings", pp)
            cc.set_editor_property("post_process_blend_weight", 1.0)
            return cam, cc, rt
        ldr_cam, ldr, ldr_rt = camera(unreal.TextureRenderTargetFormat.RTF_RGBA8, unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        hdr_cam, hdr, hdr_rt = camera(unreal.TextureRenderTargetFormat.RTF_RGBA16F, unreal.SceneCaptureSource.SCS_SCENE_COLOR_HDR)

        def aim(view):
            kind, loc, fwd, up, width = view
            rot = ML.make_rot_from_xz(unreal.Vector(*fwd), unreal.Vector(*up))
            for cam, cc in ((ldr_cam, ldr), (hdr_cam, hdr)):
                cam.set_actor_location_and_rotation(unreal.Vector(*loc), rot, False, False)
                if kind == "ortho":
                    cc.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
                    cc.set_editor_property("ortho_width", float(width))
                    safe(lambda: cc.set_editor_property("auto_calculate_ortho_planes", False))
                else:
                    cc.set_editor_property("projection_type", unreal.CameraProjectionMode.PERSPECTIVE)
                    cc.set_editor_property("fov_angle", float(width))

        VIEWS = {
            "front": ("ortho", (0.35, -8.5, 80.0), (0, 0, -1), (0, -1, 0), 42.0),
            "back": ("ortho", (0.35, -8.5, -80.0), (0, 0, 1), (0, -1, 0), 42.0),
            "rimF": ("persp", (0.0, -40.0, 16.0), (0.0, 0.83, -0.42), (0, 0, 1), 42.0),
            "rimB": ("persp", (0.0, -40.0, -16.0), (0.0, 0.83, 0.42), (0, 0, 1), 42.0),
            "tip": ("ortho", (60.0, 0.0, 0.0), (-1, 0, 0), (0, 0, 1), 5.0),
            "side": ("ortho", (9.5, -60.0, 0.0), (0, 1, 0), (0, 0, 1), 24.0),
            "above": ("ortho", (9.5, 0.0, 60.0), (0, 0, -1), (1, 0, 0), 24.0),
        }
        shots = []

        def shoot(seq, t, view, name, mat_list, hdr_too=True, tassel=True):
            a, c = posed(seq, t, 0, mat_list)
            acts = [a]
            info = {"name": name, "view": view, "t": t}
            if tassel:
                ta = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator())
                tc = ta.get_editor_property("skeletal_mesh_component")
                tc.set_skinned_asset_and_update(tmesh)
                if mat_list is dbg:
                    tc.set_material(0, mats["M_IV_Dbg_Tassel"])
                tc.attach_to_component(c, "Tassel", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                                       unreal.AttachmentRule.KEEP_WORLD, False)
                info["tassel_err_cm"] = math.dist(v3(tc.get_world_location()), v3(c.get_socket_location("Tassel")))
                info["tassel_bones_world"] = {b: v3(tc.get_socket_location(b)) for b in tn}
                acts.append(ta)
            aim(VIEWS[view])
            for _ in range(3):
                ldr.capture_scene()
            RL.export_render_target(w, ldr_rt, str(rdir), name + ".png")
            if hdr_too:
                for _ in range(2):
                    hdr.capture_scene()
                RL.export_render_target(w, hdr_rt, str(rdir), name + "_hdr.exr")
            for x in acts:
                EAS.destroy_actor(x)
            shots.append(info)

        for f in (0, 1, 3, 9, 30, 45, 60):
            for view in ("front", "back", "rimF", "rimB"):
                shoot(op, f / 60.0, view, f"fold_f{f:02d}_{view}", dbg)
        for f in (0, 1, 3):
            for view in ("tip", "side", "above"):
                shoot(op, f / 60.0, view, f"closed_f{f:02d}_{view}", dbg, tassel=False)
        oc = unreal.load_asset(f"{DEST}/A_Fan_OpenClose")
        for t in (0.25, 0.65, 1.1):
            shoot(oc, t, "front", f"openclose_{t:.2f}_front", dbg)
        pose = unreal.load_asset(f"{DEST}/A_Fan_OpenPose")
        look = [mats["M_IV_Tint_Leaf"], mats["M_IV_Tint_Sticks"], mats["M_IV_BC_Rivet"]]
        for view in ("front", "back", "rimF"):
            shoot(pose, 0.0, view, f"look_open_{view}", look)
        # ACL default clip at a mid opening, for a visual crack check
        opd = unreal.load_asset(f"{DEST}/A_Fan_Openness_Default")
        for f in (9, 30, 60):
            shoot(opd, f / 60.0, "rimF", f"acl_f{f:02d}_rimF", dbg)
        res["shots"] = shots
    finally:
        for a in spawned:
            safe(lambda: EAS.destroy_actor(a))
    res["status"] = "ok"
except Exception:  # noqa
    res["status"] = "error"
    res["error"] = traceback.format_exc()
res["seconds"] = round(time.time() - res["t0"], 1)
dump()
unreal.log("IV_PASS_B_DONE status=" + res["status"])
