"""INDEPENDENT pass B (a SECOND fresh UnrealEditor-Cmd, -nullrhi): load what pass A saved and read everything back.
Nothing is imported or saved.  Dumps:
  - per-asset LODs, triangles, vertices, sections, screen sizes, lightmap settings, collision, sockets, bounds, slots
  - per-LOD source geometry (positions + triangles, cm, Unreal frame) of both meshes
  - the sword attached to the sheath's Holster socket in the editor world (SNAP_TO_TARGET) with the sheath actor at
    an arbitrary non-identity world transform, and the resulting sword->sheath-local affine map measured in-engine
  - Unreal's own FBX export (collision + LODs) of each loaded asset, for hull checks in Blender
  - texture flags
"""
import hashlib, json, os, time, traceback
from pathlib import Path
import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "SnowFlower" / "v4" / "UnrealVerify_Indep"
EXP = PROJ / "Exports" / "SnowFlower" / "v4"
DEST = os.environ["IV_DEST"]
OUT = HERE / "ivB_verify.json"
GEO = HERE / "ivB_geometry.json"
res = {"dest": DEST, "t0": time.time(), "engine": unreal.SystemLibrary.get_engine_version()}
RTS = unreal.RelativeTransformSpace.RTS_COMPONENT


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:300]}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def v3(v, nd=5):
    return [round(v.x, nd), round(v.y, nd), round(v.z, nd)]


def sub():
    s = None
    try:
        s = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        s = None
    if s is None:
        s = unreal.new_object(unreal.StaticMeshEditorSubsystem)  # get_editor_subsystem is None in a commandlet
    return s


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
        nv = d.get_vertex_count()
        P = []
        for i in range(nv):
            p = d.get_vertex_position(mk_id(unreal.VertexID, i))
            P.append([p.x, p.y, p.z])
        T = []
        for t in range(d.get_triangle_count()):
            vs = d.get_triangle_vertices(mk_id(unreal.TriangleID, t))
            T.append([id_int(v) for v in vs])
        lods.append({"positions": P, "triangles": T})
    return lods


def inspect(mesh, sidecar):
    s = sub()
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
                                                        "recompute_normals", "recompute_tangents", "use_mikk_t_space")}
    r["lod_build_settings"] = [safe(lambda i=i: bs(i)) for i in range(n)]
    r["light_map_coordinate_index"] = safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index")))
    r["light_map_resolution"] = safe(lambda: int(mesh.get_editor_property("light_map_resolution")))
    r["nanite"] = safe(lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")))
    body = mesh.get_editor_property("body_setup")
    agg = body.get_editor_property("agg_geom")
    r["convex_elems"] = len(agg.get_editor_property("convex_elems"))
    r["box_sphere_sphyl"] = [len(agg.get_editor_property(k)) for k in ("box_elems", "sphere_elems", "sphyl_elems")]
    r["collision_trace_flag"] = safe(lambda: str(body.get_editor_property("collision_trace_flag")))
    r["simple_collision_count_subsystem"] = safe(lambda: int(s.get_convex_collision_count(mesh)))
    r["has_simple_collision"] = safe(lambda: bool(s.get_simple_collision_count(mesh)))
    box = mesh.get_bounding_box()
    r["bbox_min_cm"] = v3(box.min)
    r["bbox_max_cm"] = v3(box.max)
    r["size_cm"] = [round(box.max.x - box.min.x, 4), round(box.max.y - box.min.y, 4), round(box.max.z - box.min.z, 4)]
    r["bounds_sphere_radius_cm"] = safe(lambda: round(float(mesh.get_bounds().sphere_radius), 4))
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
        socks[nm] = {"location_cm": v3(t.translation), "rotator_rpy": [round(e.roll, 4), round(e.pitch, 4), round(e.yaw, 4)],
                     "component_scale": v3(t.scale3d),
                     "relative_scale": v3(so.get_editor_property("relative_scale")) if so else None,
                     "relative_rotation": (lambda rr: [round(rr.roll, 4), round(rr.pitch, 4), round(rr.yaw, 4)])(so.get_editor_property("relative_rotation")) if so else None,
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


def export_fbx(mesh, out):
    o = unreal.FbxExportOption()
    o.set_editor_property("collision", True)
    o.set_editor_property("level_of_detail", True)
    o.set_editor_property("ascii", False)
    t = unreal.AssetExportTask()
    t.set_editor_property("object", mesh)
    t.set_editor_property("filename", str(out))
    t.set_editor_property("automated", True)
    t.set_editor_property("prompt", False)
    t.set_editor_property("exporter", unreal.StaticMeshExporterFBX())
    t.set_editor_property("options", o)
    return bool(unreal.Exporter.run_asset_export_task(t))


def tex_info(p):
    t = unreal.load_asset(p)
    d = {"class": type(t).__name__}
    for k in ("srgb", "compression_settings", "flip_green_channel", "lod_group", "mip_gen_settings", "never_stream",
              "virtual_texture_streaming", "power_of_two_mode", "compression_quality", "max_texture_size"):
        d[k] = safe(lambda k=k: str(t.get_editor_property(k)))
    d["size"] = safe(lambda: [int(t.blueprint_get_size_x()), int(t.blueprint_get_size_y())])
    return d


def attach_test(sword, sheath):
    EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    ML = unreal.MathLibrary
    r = {}
    rot = unreal.Rotator()
    rot.roll, rot.pitch, rot.yaw = 17.0, -23.0, 41.0
    loc = unreal.Vector(123.4, -56.7, 89.0)
    a_sh = EAS.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
    a_sw = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(-500, 300, 20), unreal.Rotator())
    try:
        c_sh = a_sh.get_editor_property("static_mesh_component")
        c_sw = a_sw.get_editor_property("static_mesh_component")
        for c, m in ((c_sh, sheath), (c_sw, sword)):
            c.set_mobility(unreal.ComponentMobility.MOVABLE)
            c.set_static_mesh(m)
        a_sh.set_actor_location_and_rotation(loc, rot, False, False)
        ok = c_sw.attach_to_component(c_sh, "Holster", unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
                                      unreal.AttachmentRule.SNAP_TO_TARGET, False)
        r["attach_returned"] = bool(ok)
        r["attach_parent"] = c_sw.get_attach_parent().get_name() if c_sw.get_attach_parent() else None
        r["attach_socket"] = str(c_sw.get_attach_socket_name())
        W_sh = c_sh.get_world_transform()
        W_sw = c_sw.get_world_transform()
        r["sheath_world"] = {"t": v3(W_sh.translation), "rpy": (lambda e: [e.roll, e.pitch, e.yaw])(W_sh.rotation.rotator())}
        r["sword_world_scale"] = v3(W_sw.scale3d, 6)
        # affine map sword-local -> sheath-local, measured through the engine's world transforms
        basis = {}
        for key, p in (("o", (0, 0, 0)), ("x", (1, 0, 0)), ("y", (0, 1, 0)), ("z", (0, 0, 1))):
            w = W_sw.transform_location(unreal.Vector(*p))
            basis[key] = [float(v) for v in v3(W_sh.inverse_transform_location(w), 9)]
        r["sword_to_sheath_basis"] = basis
        rel = ML.make_relative_transform(W_sw, W_sh)
        r["relative_transform"] = {"t": v3(rel.translation, 6), "rpy": (lambda e: [round(e.roll, 6), round(e.pitch, 6), round(e.yaw, 6)])(rel.rotation.rotator()),
                                   "s": v3(rel.scale3d, 6)}
        # the sword's own sockets as they land in sheath-local space
        socks = {}
        for nm in ("Grip", "OffHand", "BladeBase", "BladeTip"):
            w = c_sw.get_socket_location(nm)
            socks[nm] = v3(W_sh.inverse_transform_location(w), 5)
        r["sword_sockets_in_sheath_cm"] = socks
        mt = c_sh.get_socket_transform("Mouth", RTS)
        r["mouth_socket"] = {"t": v3(mt.translation, 5), "z_axis": v3(mt.transform_direction(unreal.Vector(0, 0, 1)), 7),
                             "x_axis": v3(mt.transform_direction(unreal.Vector(1, 0, 0)), 7)}
        ht = c_sh.get_socket_transform("Holster", RTS)
        r["holster_socket"] = {"t": v3(ht.translation, 5), "z_axis": v3(ht.transform_direction(unreal.Vector(0, 0, 1)), 7),
                               "x_axis": v3(ht.transform_direction(unreal.Vector(1, 0, 0)), 7)}
        bm = c_sh.get_socket_transform("BeltMount", RTS)
        r["beltmount_socket"] = {"t": v3(bm.translation, 5)}
        r["world_bounds_sword"] = safe(lambda: [v3(x) for x in a_sw.get_actor_bounds(False)])
        r["world_bounds_sheath"] = safe(lambda: [v3(x) for x in a_sh.get_actor_bounds(False)])
    finally:
        EAS.destroy_actor(a_sw)
        EAS.destroy_actor(a_sh)
    return r


try:
    sword = unreal.load_asset(f"{DEST}/SM_SnowFlower")
    sheath = unreal.load_asset(f"{DEST}/SM_SnowFlower_Sheath")
    res["loaded"] = [isinstance(sword, unreal.StaticMesh), isinstance(sheath, unreal.StaticMesh)]
    res["fbx_sha256_now"] = {n: sha(EXP / f"{n}.fbx") for n in ("SM_SnowFlower", "SM_SnowFlower_Sheath")}
    res["sword"] = inspect(sword, EXP / "SM_SnowFlower.sockets.json")
    res["sheath"] = inspect(sheath, EXP / "SM_SnowFlower_Sheath.sockets.json")
    res["attach"] = safe(lambda: attach_test(sword, sheath))
    res["textures"] = {Path(str(p)).stem.split(".")[0]: tex_info(str(p).split(".")[0])
                       for p in unreal.EditorAssetLibrary.list_assets(DEST + "/Textures", recursive=False, include_folder=False)}
    res["roundtrip_export"] = {
        "sword": safe(lambda: export_fbx(sword, HERE / "ue_roundtrip_sword.fbx")),
        "sheath": safe(lambda: export_fbx(sheath, HERE / "ue_roundtrip_sheath.fbx")),
    }
    t1 = time.time()
    geo = {"sword": safe(lambda: geometry(sword)), "sheath": safe(lambda: geometry(sheath))}
    res["geometry_seconds"] = round(time.time() - t1, 1)
    GEO.write_text(json.dumps(geo), encoding="utf-8")
    res["geometry_counts"] = {k: ([{"v": len(l["positions"]), "t": len(l["triangles"])} for l in g] if isinstance(g, list) else g)
                              for k, g in geo.items()}
    res["status"] = "ok"
except Exception:  # noqa: BLE001
    res["status"] = "error"
    res["error"] = traceback.format_exc()
res["seconds"] = round(time.time() - res["t0"], 1)
OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
unreal.log("IV_PASS_B_DONE status=" + res["status"])
