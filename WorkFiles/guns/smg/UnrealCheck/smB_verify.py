"""SMG01 W5, pass B (a SECOND fresh UnrealEditor-Cmd, -nullrhi): load what pass A saved and read everything back.
Nothing is imported or saved. Writes smB_verify.json (+ smB_geometry.json, smB_poses.json and Unreal's own FBX
exports in roundtrip/ for the Blender fit / hull / UV1 checks):

- SK_SMG01: skeleton (names, parents, reference pose local + component), sockets (bone, relative, component, outer,
  scale), LOD count / vertices / sections / slots, LOD screen sizes (LOD settings asset), registry triangle tag,
  bounds and bounds extensions, physics asset (bodies, shapes, mass), materials;
- U2 procedural (engine pose maths): 'bolt' -6.79 cm (the sidecar's full travel) along its own X (bone space) and
  'selector' to SAFE / AUTO (Blender -63.4 / +45 deg about Y = Unreal pitch +63.4 / -45) about its own Y; the
  component-space motion is read back;
- the eight clips: frames, length, rate, compression, notifies (name, trigger time, track), and every bone's
  component-space transform at every frame (and half frames) from the RAW data and the COMPRESSED data
  (AnimPoseExtensions, evaluation type Raw / Compressed);
- SM_SMG01 / SM_SMG01_Mag: LODs, triangles, vertices, sections, screen sizes, lightmap settings and index, UV channels,
  hulls, sockets vs sidecar, slots, Nanite, bounds; per-LOD source geometry (positions + triangles);
- the magazine attached to the Mag socket of SK_SMG01 and of SM_SMG01 (SnapToTarget) with the gun at an arbitrary world
  transform: the magazine -> gun-component affine map measured in-engine (U6 / M9 at rest);
- texture flags; Unreal's own FBX exports of SK_SMG01 (LODs) and both statics (LODs + collision).
"""
import json, sys, time, traceback
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import sm_common as C  # noqa: E402

DEST = C.dest()
OUT = C.HERE / "smB_verify.json"
GEO = C.HERE / "smB_geometry.json"
POSES = C.HERE / "smB_poses.json"
RT = C.HERE / "roundtrip"
RT.mkdir(exist_ok=True)
SUB = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
AL = unreal.AnimationLibrary
ML = unreal.MathLibrary
RTS = unreal.RelativeTransformSpace.RTS_COMPONENT
SC = C.sidecar_sk()
safe = C.safe
res = {"dest": DEST, "t0": time.time(), "engine": unreal.SystemLibrary.get_engine_version(), "hashes_before": C.all_hashes()}


def dump():
    res["seconds"] = round(time.time() - res["t0"], 1)
    C.write(OUT, res)


def v3(v, nd=6):
    return [round(v.x, nd), round(v.y, nd), round(v.z, nd)]


def T(t):
    q = t.rotation
    return [t.translation.x, t.translation.y, t.translation.z, q.x, q.y, q.z, q.w, t.scale3d.x, t.scale3d.y, t.scale3d.z]


def smsub():
    s = None
    try:
        s = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        s = None
    return s if s is not None else unreal.new_object(unreal.StaticMeshEditorSubsystem)


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


def phys(m):
    pa = m.get_editor_property("physics_asset")
    if pa is None:
        return None
    out = {"asset": pa.get_path_name(), "bodies": {}}
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
                    v = safe(lambda k=k: e.get_editor_property(k))
                    r[k] = v3(v) if isinstance(v, unreal.Vector) else ([v.roll, v.pitch, v.yaw] if isinstance(v, unreal.Rotator)
                                                                       else (v if isinstance(v, (int, float)) else str(v)))
                el.append(r)
        out["bodies"][str(bs.get_editor_property("bone_name"))] = {
            "elements": el, "physics_type": str(bs.get_editor_property("physics_type")),
            "consider_for_bounds": bool(bs.get_editor_property("consider_for_bounds")),
            "collision": str(bi.get_editor_property("collision_enabled")),
            "override_mass": bool(bi.get_editor_property("override_mass")),
            "mass_kg": bi.get_editor_property("mass_in_kg_override"),
            "simulate": bool(bi.get_editor_property("simulate_physics"))}
    out["constraints"] = safe(lambda: [str(x) for x in pa.get_constraints(True)])
    return out


def mk_id(cls, i):
    try:
        return cls(i)
    except Exception:  # noqa: BLE001
        pass
    o = cls()
    for f in ("id_value", "value"):
        try:
            o.set_editor_property(f, i)
            return o
        except Exception:  # noqa: BLE001
            pass
    raise RuntimeError(f"cannot build {cls.__name__}")


def id_int(o):
    for f in ("id_value", "value"):
        try:
            return int(o.get_editor_property(f))
        except Exception:  # noqa: BLE001
            pass
    return int(str(o).split()[-1].strip(">)"))


def geometry(mesh):
    lods = []
    for lod in range(mesh.get_num_lods()):
        d = mesh.get_static_mesh_description(lod)
        P = []
        for i in range(d.get_vertex_count()):
            p = d.get_vertex_position(mk_id(unreal.VertexID, i))
            P.append([p.x, p.y, p.z])
        Tr = []
        for t in range(d.get_triangle_count()):
            vs = d.get_triangle_vertices(mk_id(unreal.TriangleID, t))
            Tr.append([id_int(v) for v in vs])
        lods.append({"positions": P, "triangles": Tr})
    return lods


def inspect_static(mesh, sidecar):
    s = smsub()
    r = {"path": mesh.get_path_name()}
    n = mesh.get_num_lods()
    r["num_lods"] = n
    r["lod_triangles"] = [mesh.get_num_triangles(i) for i in range(n)]
    r["lod_vertices_render"] = [mesh.get_num_vertices(i) for i in range(n)]
    r["lod_sections"] = [mesh.get_num_sections(i) for i in range(n)]
    r["lod_screen_sizes"] = safe(lambda: [round(float(v), 6) for v in s.get_lod_screen_sizes(mesh)])
    r["auto_compute_lod_screen_size"] = safe(lambda: bool(mesh.get_editor_property("auto_compute_lod_screen_size")))
    r["uv_channels_per_lod"] = [safe(lambda i=i: int(s.get_num_uv_channels(mesh, i))) for i in range(n)]

    def bs(i):
        b = s.get_lod_build_settings(mesh, i)
        return {k: b.get_editor_property(k) for k in ("generate_lightmap_u_vs", "src_lightmap_index", "dst_lightmap_index",
                                                        "min_lightmap_resolution", "recompute_normals", "recompute_tangents",
                                                        "use_mikk_t_space", "remove_degenerates", "use_full_precision_u_vs")}
    r["lod_build_settings"] = [safe(lambda i=i: bs(i)) for i in range(n)]
    r["light_map_coordinate_index"] = safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index")))
    r["light_map_resolution"] = safe(lambda: int(mesh.get_editor_property("light_map_resolution")))
    r["nanite"] = safe(lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")))
    body = mesh.get_editor_property("body_setup")
    agg = body.get_editor_property("agg_geom")
    r["convex_elems"] = len(agg.get_editor_property("convex_elems"))
    r["convex_vertex_counts"] = safe(lambda: [len(e.get_editor_property("vertex_data")) for e in agg.get_editor_property("convex_elems")])
    r["box_sphere_sphyl"] = [len(agg.get_editor_property(k)) for k in ("box_elems", "sphere_elems", "sphyl_elems")]
    r["collision_trace_flag"] = safe(lambda: str(body.get_editor_property("collision_trace_flag")))
    box = mesh.get_bounding_box()
    r["bbox_min_cm"] = v3(box.min)
    r["bbox_max_cm"] = v3(box.max)
    b = mesh.get_bounds()
    r["bounds"] = {"origin": v3(b.origin), "extent": v3(b.box_extent), "radius": round(float(b.sphere_radius), 6)}
    r["material_slots"] = [{"slot": str(m.material_slot_name), "imported": str(m.get_editor_property("imported_material_slot_name")),
                            "material": (m.material_interface.get_path_name() if m.material_interface else None)}
                           for m in mesh.get_editor_property("static_materials")]
    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    socks = {}
    for nm in comp.get_all_socket_names():
        nm = str(nm)
        t = comp.get_socket_transform(nm, RTS)
        e = t.rotation.rotator()
        so = mesh.find_socket(nm)
        socks[nm] = {"location_cm": v3(t.translation, 7), "rotator_rpy": [round(e.roll, 6), round(e.pitch, 6), round(e.yaw, 6)],
                     "quat_xyzw": [t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w],
                     "component_scale": v3(t.scale3d), "relative_scale": v3(so.get_editor_property("relative_scale")) if so else None,
                     "outer": so.get_outer().get_path_name() if so else None}
    r["sockets"] = socks
    sc = json.loads(Path(sidecar).read_text(encoding="utf-8"))
    cmp = {}
    for rec in sc["sockets"]:
        got = socks.get(rec["socket"])
        if got is None:
            cmp[rec["socket"]] = "MISSING"
            continue
        dl = max(abs(a - b) for a, b in zip(got["location_cm"], rec["location_cm"]))
        rd = rec["rotation_deg"]
        dr = max(abs(a - b) for a, b in zip(got["rotator_rpy"], [rd["roll"], rd["pitch"], rd["yaw"]]))
        cmp[rec["socket"]] = {"max_loc_err_cm": dl, "max_rot_err_deg": dr,
                              "scale1": got["relative_scale"] == [1.0, 1.0, 1.0] and got["component_scale"] == [1.0, 1.0, 1.0],
                              "outer_is_asset": (got["outer"] or "").startswith(mesh.get_path_name().split(".")[0])}
    r["sidecar_compare"] = cmp
    r["sidecar_extra_sockets"] = sorted(set(socks) - {x["socket"] for x in sc["sockets"]})
    r["sidecar_lod_screen_sizes"] = sc.get("lod_screen_sizes")
    return r


def export(obj, out, exporter, lods=True, collision=True):
    o = unreal.FbxExportOption()
    o.set_editor_property("collision", collision)
    o.set_editor_property("level_of_detail", lods)
    o.set_editor_property("ascii", False)
    o.set_editor_property("force_front_x_axis", False)
    t = unreal.AssetExportTask()
    t.set_editor_property("object", obj)
    t.set_editor_property("filename", str(out))
    t.set_editor_property("automated", True)
    t.set_editor_property("prompt", False)
    t.set_editor_property("replace_identical", True)
    t.set_editor_property("exporter", exporter)
    t.set_editor_property("options", o)
    return {"ok": bool(unreal.Exporter.run_asset_export_task(t)), "file": str(out), "bytes": Path(out).stat().st_size if Path(out).exists() else 0}


def attach(gun_mesh, mag_mesh, skeletal):
    rot = unreal.Rotator()
    rot.roll, rot.pitch, rot.yaw = 17.0, -23.0, 41.0
    loc = unreal.Vector(123.4, -56.7, 89.0)
    cls = unreal.SkeletalMeshActor if skeletal else unreal.StaticMeshActor
    a_g = EAS.spawn_actor_from_class(cls, loc, rot)
    a_m = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(-500, 300, 20), unreal.Rotator(11, 22, 33))
    r = {}
    try:
        if skeletal:
            c_g = a_g.get_editor_property("skeletal_mesh_component")
            c_g.set_skinned_asset_and_update(gun_mesh)
        else:
            c_g = a_g.get_editor_property("static_mesh_component")
            c_g.set_mobility(unreal.ComponentMobility.MOVABLE)
            c_g.set_static_mesh(gun_mesh)
        c_m = a_m.get_editor_property("static_mesh_component")
        c_m.set_mobility(unreal.ComponentMobility.MOVABLE)
        c_m.set_static_mesh(mag_mesh)
        a_g.set_actor_location_and_rotation(loc, rot, False, False)
        r["attach_returned"] = bool(c_m.attach_to_component(c_g, "Mag", unreal.AttachmentRule.SNAP_TO_TARGET,
                                                            unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET, False))
        r["attach_socket"] = str(c_m.get_attach_socket_name())
        Wg = c_g.get_world_transform()
        Wm = c_m.get_world_transform()
        basis = {}
        for key, p in (("o", (0, 0, 0)), ("x", (1, 0, 0)), ("y", (0, 1, 0)), ("z", (0, 0, 1))):
            w = Wm.transform_location(unreal.Vector(*p))
            basis[key] = [float(v) for v in v3(Wg.inverse_transform_location(w), 9)]
        r["mag_to_gun_basis"] = basis
        rel = ML.make_relative_transform(Wm, Wg)
        r["relative_transform"] = T(rel)
        r["relative_to_socket"] = safe(lambda: T(c_m.get_relative_transform()))
        r["mag_world_scale"] = v3(Wm.scale3d)
        st = c_g.get_socket_transform("Mag", RTS)
        r["gun_socket_Mag"] = T(st)
        for sn in ("MagInsertStart",):
            r[f"gun_socket_{sn}"] = T(c_g.get_socket_transform(sn, RTS))
    finally:
        EAS.destroy_actor(a_m)
        EAS.destroy_actor(a_g)
    return r


def poseable_u2(mesh):
    """U2: the engine's pose maths (AnimPose, the same local -> component evaluation a Transform Modify Bone node feeds):
    'bolt' offset by the full travel along its own -X and 'selector' turned to SAFE / AUTO about its own Y, in bone (local) space;
    the component-space motion is read back. (A PoseableMeshComponent needs a registered component, which a
    commandlet cannot tick.)"""
    APE = unreal.AnimPoseExtensions
    skel = mesh.get_editor_property("skeleton")
    out = {}

    def drive(bone, delta):
        pose = APE.get_reference_pose(skel)
        ref_c = APE.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
        ref_l = APE.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.LOCAL)
        new_l = ML.compose_transforms(delta, ref_l)
        r = APE.set_bone_pose(pose, new_l, bone, unreal.AnimPoseSpaces.LOCAL)
        if isinstance(r, unreal.AnimPose):
            pose = r
        got = APE.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
        return {"commanded_local_delta": T(delta), "ref_component": T(ref_c), "got_component": T(got),
                "ref_local": T(ref_l)}
    tb = unreal.Transform()
    tab = C.abp_tables()["SMG01"]
    tb.translation = unreal.Vector(-tab["bolt_cm"], 0.0, 0.0)
    out["bolt_back_full"] = drive("bolt", tb)
    out["bolt_back_full"]["commanded_cm"] = -tab["bolt_cm"]
    for name, deg in (("SAFE", tab["selector_deg"][0]), ("AUTO", tab["selector_deg"][2])):
        ts = unreal.Transform()
        r = unreal.Rotator()
        r.pitch = -deg            # Blender +deg about Y = Unreal pitch -deg
        ts.rotation = r.quaternion()
        out[f"selector_{name}"] = drive("selector", ts)
        out[f"selector_{name}"]["blender_deg"] = deg
    return out


def clip_poses(seq, names, fps):
    nf = AL.get_num_frames(seq)
    rec = {"num_frames": nf, "num_keys": safe(lambda: AL.get_num_keys(seq)), "play_length": seq.get_play_length(),
           "compression": safe(lambda: AL.get_bone_compression_settings(seq).get_path_name()),
           "skeleton": seq.get_editor_property("skeleton").get_path_name(),
           "rate_scale": safe(lambda: AL.get_rate_scale(seq)), "time_of_frame1": safe(lambda: AL.get_time_at_frame(seq, 1))}
    for k in ("loop", "enable_root_motion", "interpolation", "additive_anim_type"):
        rec[k] = str(safe(lambda k=k: seq.get_editor_property(k)))
    # notifies
    evs = []
    for e in AL.get_animation_notify_events(seq):
        evs.append({"name": str(e.get_editor_property("notify_name")),
                    "notify": (e.get_editor_property("notify").get_class().get_name() if e.get_editor_property("notify") else None),
                    "time": safe(lambda e=e: float(AL.get_anim_notify_event_trigger_time(e))),
                    "track_index": safe(lambda e=e: int(e.get_editor_property("track_index")))})
    rec["notifies"] = evs
    rec["notify_tracks"] = safe(lambda: [str(x) for x in AL.get_animation_notify_track_names(seq)])
    # poses: raw and compressed, component space, every frame and half frame
    L = seq.get_play_length()
    steps = int(round(L * fps))
    times = sorted(set([k / fps for k in range(steps + 1)] + [(k + 0.5) / fps for k in range(steps)]))
    poses = {}
    for kind in ("RAW", "COMPRESSED"):
        o = unreal.AnimPoseEvaluationOptions()
        safe(lambda: o.set_editor_property("evaluation_type", getattr(unreal.AnimDataEvalType, kind)))
        safe(lambda: o.set_editor_property("should_retarget", False))
        safe(lambda: o.set_editor_property("extract_root_motion", False))
        per = {}
        for t in times:
            p = unreal.AnimPoseExtensions.get_anim_pose_at_time(seq, t, o)
            per[f"{t:.6f}"] = {b: T(unreal.AnimPoseExtensions.get_bone_pose(p, b, unreal.AnimPoseSpaces.WORLD))[:7] for b in names}
        poses[kind] = per
    rec["eval_options_props"] = [x for x in dir(unreal.AnimPoseEvaluationOptions) if not x.startswith("_") and x.islower()][:40]
    return rec, poses


try:
    sk = unreal.load_asset(f"{DEST}/SK_SMG01")
    sm = unreal.load_asset(f"{DEST}/SM_SMG01")
    mag = unreal.load_asset(f"{DEST}/SM_SMG01_Mag")
    res["loaded"] = {"SK_SMG01": isinstance(sk, unreal.SkeletalMesh), "SM_SMG01": isinstance(sm, unreal.StaticMesh),
                     "SM_SMG01_Mag": isinstance(mag, unreal.StaticMesh)}
    res["sha_now_equals_start"] = C.all_hashes() == json.loads((C.HERE / "SHA256_at_start.json").read_text())
    for m in (sm, mag):
        m.get_bounding_box(); m.get_num_triangles(0)
    # ------------------------------------------------------------------ skeleton + sockets
    skel = sk.get_editor_property("skeleton")
    names, local, par = ref_pose(sk)
    comp = compose(local, par)
    res["skeleton"] = {"asset": skel.get_path_name(), "mesh_bones": len(names), "order": names, "parents": par,
                       "ref_local": {n: T(local[n]) for n in names}, "ref_comp": {n: T(comp[n]) for n in names},
                       "skeleton_asset_bones": safe(lambda: len(unreal.AnimPoseExtensions.get_bone_names(skel.get_reference_pose())))}
    socks = {}
    for i in range(sk.num_sockets()):
        s = sk.get_socket_by_index(i)
        nm = str(s.get_editor_property("socket_name"))
        bone = str(s.get_editor_property("bone_name"))
        rel = unreal.Transform()
        rel.translation = s.get_editor_property("relative_location")
        rel.rotation = s.get_editor_property("relative_rotation").quaternion()
        rel.scale3d = s.get_editor_property("relative_scale")
        socks[nm] = {"bone": bone, "relative": T(rel), "component": T(ML.compose_transforms(rel, comp[bone])),
                     "outer": s.get_outer().get_path_name()}
    res["sk_sockets"] = socks
    # ------------------------------------------------------------------ LODs, sections, slots, bounds, physics
    res["sk_lods"] = [{"lod": L, "verts": SUB.get_num_verts(sk, L), "sections": SUB.get_num_sections(sk, L),
                       "section_slots": [SUB.get_lod_material_slot(sk, L, s) for s in range(SUB.get_num_sections(sk, L))]}
                      for L in range(SUB.get_lod_count(sk))]
    ls = sk.get_editor_property("lod_settings")
    res["sk_lod_settings"] = safe(lambda: {"asset": ls.get_path_name(), "screen_sizes": [
        g.get_editor_property("screen_size").get_editor_property("default") for g in ls.get_editor_property("lod_groups")]})
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    ad = ar.get_asset_by_object_path(f"{DEST}/SK_SMG01.SK_SMG01")
    res["sk_registry_tags"] = {k: str(safe(lambda k=k: ad.get_tag_value(k))) for k in ("Triangles", "Vertices", "Bones", "LODs")}
    res["sk_slots"] = [{"slot": str(s.get_editor_property("material_slot_name")),
                        "material": (s.get_editor_property("material_interface").get_path_name()
                                     if s.get_editor_property("material_interface") else None)}
                       for s in sk.get_editor_property("materials")]

    def bsb(b):
        return {"origin": v3(b.origin), "extent": v3(b.box_extent), "radius": b.sphere_radius}
    res["sk_bounds"] = {"bounds": safe(lambda: bsb(sk.get_bounds())), "imported": safe(lambda: bsb(sk.get_imported_bounds())),
                        "pos_ext": safe(lambda: v3(sk.get_editor_property("positive_bounds_extension"))),
                        "neg_ext": safe(lambda: v3(sk.get_editor_property("negative_bounds_extension")))}
    res["sk_physics"] = safe(lambda: phys(sk))
    res["sk_nanite"] = safe(lambda: str(sk.get_editor_property("nanite_settings")))
    dump()
    # ------------------------------------------------------------------ U2 procedural
    res["U2"] = safe(lambda: poseable_u2(sk))
    dump()
    # ------------------------------------------------------------------ clips
    clips, allposes = {}, {}
    for a in SC["animations"]:
        nm = a["file"][:-4]
        seq = unreal.load_asset(f"{DEST}/{nm}")
        rec, poses = clip_poses(seq, names, float(a["fps"]))
        clips[nm] = rec
        allposes[nm] = poses
    res["clips"] = clips
    POSES.write_text(json.dumps({"names": names, "ref_comp": res["skeleton"]["ref_comp"], "clips": allposes}), encoding="utf-8")
    dump()
    # ------------------------------------------------------------------ statics
    res["SM_SMG01"] = inspect_static(sm, C.EXP / "SM_SMG01.sockets.json")
    res["SM_SMG01_Mag"] = inspect_static(mag, C.EXP / "SM_SMG01_Mag.sockets.json")
    dump()
    # ------------------------------------------------------------------ magazine at Mag (rest)
    # the SK attach needs a render-state skinned component: pass C (real RHI) measures it
    res["attach_SM"] = safe(lambda: attach(sm, mag, False))
    dump()
    # ------------------------------------------------------------------ textures
    tex = {}
    for p in unreal.EditorAssetLibrary.list_assets(DEST + "/Textures", recursive=False, include_folder=False):
        t = unreal.load_asset(str(p).split(".")[0])
        d = {"class": type(t).__name__}
        for k in ("srgb", "compression_settings", "flip_green_channel", "lod_group", "mip_gen_settings", "never_stream",
                  "virtual_texture_streaming", "power_of_two_mode", "max_texture_size", "lod_bias", "compression_no_alpha"):
            d[k] = safe(lambda k=k: str(t.get_editor_property(k)))
        d["size"] = safe(lambda: [int(t.blueprint_get_size_x()), int(t.blueprint_get_size_y())])
        tex[t.get_name()] = d
    res["textures"] = tex
    dump()
    # ------------------------------------------------------------------ Unreal's own FBX exports
    res["roundtrip"] = {
        # SK_SMG01: exported in pass C (the skeletal exporter needs a render-state component)
        "SM_SMG01": safe(lambda: export(sm, RT / "ue_SM_SMG01.fbx", unreal.StaticMeshExporterFBX(), True, True)),
        "SM_SMG01_Mag": safe(lambda: export(mag, RT / "ue_SM_SMG01_Mag.fbx", unreal.StaticMeshExporterFBX(), True, True)),
    }
    dump()
    t1 = time.time()
    geo = {"SM_SMG01": safe(lambda: geometry(sm)), "SM_SMG01_Mag": safe(lambda: geometry(mag))}
    res["geometry_seconds"] = round(time.time() - t1, 1)
    GEO.write_text(json.dumps(geo), encoding="utf-8")
    res["geometry_counts"] = {k: ([{"v": len(l["positions"]), "t": len(l["triangles"])} for l in g] if isinstance(g, list) else g)
                              for k, g in geo.items()}
    res["status"] = "ok"
except Exception:  # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
res["hashes_after"] = C.all_hashes()
res["exports_unchanged"] = res["hashes_after"] == res["hashes_before"]
dump()
unreal.log("SM_PASS_B_DONE status=" + res["status"])
