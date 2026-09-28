"""UnrealCheck9 step 3 (a SECOND, FRESH process): read back the saved mesh and maps. Imports nothing, saves nothing.

Gates computed here (log-line, Blender-truth and round-trip gates are added by summarize.py):
  G1 LOD count 3 (per-LOD triangles compared with Blender in summarize.py)
  G2 exactly one convex hull, no other primitives
  G3 Grip / Trail persisted (outered to the asset), relative scale 1, spec location/yaw
  G4 bounds cm == spec, centred
  G5 LOD screen sizes 1.0 / 0.098 / 0.0343 (render data)
  G6 lightmap coordinate index 1, lightmap UVs generated 0 -> 1 on every LOD
  T  BC sRGB TC_Default; ORM sRGB off TC_Masks; N sRGB off TC_Normalmap flip-green off; 2048; FileMD5 == shipped
Writes s3_readback.json.
"""
import json
import math
import sys
import traceback
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck9_SixPoint")
sys.path.insert(0, str(HERE))

import unreal  # noqa: E402
import u9_common as C  # noqa: E402


def safe(fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"[:240]}


def v3(v, nd=6):
    return [round(float(v.x), nd), round(float(v.y), nd), round(float(v.z), nd)]


def subsystem():
    return C.sm_subsystem()


def registry_import_tag(asset_path):
    """The AssetImportData registry tag: JSON with RelativeFilename / Timestamp / FileMD5 of the imported bytes."""
    ad = safe(lambda: unreal.EditorAssetLibrary.find_asset_data(asset_path))
    if isinstance(ad, dict):
        return ad
    out = {}
    for fn in (lambda: ad.get_tag_value("AssetImportData"),):
        val = safe(fn)
        out["raw"] = val
    raw = out.get("raw")
    if isinstance(raw, (tuple, list)):
        raw = raw[-1]
    if isinstance(raw, str) and raw.strip():
        try:
            out["parsed"] = json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            out["parse_error"] = str(exc)[:160]
    return out


def mesh_info(mesh):
    sub = subsystem()
    n = mesh.get_num_lods()
    info = {"asset": mesh.get_path_name(), "class": mesh.get_class().get_name(), "num_lods": n,
            "lod_triangles": [int(mesh.get_num_triangles(i)) for i in range(n)],
            "lod_vertices": [int(mesh.get_num_vertices(i)) for i in range(n)],
            "lod_sections": [safe(lambda i=i: int(mesh.get_num_sections(i))) for i in range(n)],
            "lod_screen_sizes_render_data": safe(lambda: [float(v) for v in sub.get_lod_screen_sizes(mesh)]),
            "lod_source_uv_channels": [safe(lambda i=i: int(sub.get_num_uv_channels(mesh, i))) for i in range(n)]}
    builds = []
    for i in range(n):
        def rd(i=i):
            bs = sub.get_lod_build_settings(mesh, i)
            out = {}
            for k in ("generate_lightmap_u_vs", "src_lightmap_index", "dst_lightmap_index", "min_lightmap_resolution",
                      "recompute_normals", "recompute_tangents", "use_mikk_t_space", "remove_degenerates",
                      "use_full_precision_u_vs", "build_scale3d"):
                val = safe(lambda k=k: bs.get_editor_property(k))
                out[k] = val if isinstance(val, (bool, int, float, dict)) else str(val)
            return out
        builds.append(safe(rd))
    info["lod_build_settings"] = builds
    for k in ("light_map_coordinate_index", "light_map_resolution", "lod_group", "min_lod", "lod_for_collision"):
        val = safe(lambda k=k: mesh.get_editor_property(k))
        info[k] = val if isinstance(val, (bool, int, float, dict)) else str(val)
    info["nanite_enabled"] = safe(lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")))
    # probe for the auto-compute flag under any exposed name
    info["props_matching_auto_or_screen"] = sorted(n_ for n_ in dir(mesh) if ("auto" in n_.lower() or "screen" in n_.lower()))
    probe = {}
    for name in ("auto_compute_lod_screen_size", "b_auto_compute_lod_screen_size", "bAutoComputeLODScreenSize"):
        probe[name] = str(safe(lambda name=name: mesh.get_editor_property(name)))[:160]
    info["auto_compute_probe"] = probe
    info["is_lod_screen_size_auto_computed"] = safe(lambda: bool(mesh.is_lod_screen_size_auto_computed()))
    body = mesh.get_editor_property("body_setup")
    info["has_body_setup"] = body is not None
    if body is not None:
        agg = body.get_editor_property("agg_geom")
        info["convex_hulls"] = len(agg.get_editor_property("convex_elems"))
        info["other_collision_elems"] = {k: safe(lambda k=k: len(agg.get_editor_property(k)))
                                         for k in ("box_elems", "sphere_elems", "sphyl_elems", "tapered_capsule_elems",
                                                   "level_set_elems", "skinned_level_set_elems")}
        info["collision_trace_flag"] = str(safe(lambda: body.get_editor_property("collision_trace_flag")))
        di = safe(lambda: body.get_editor_property("default_instance"))
        if not isinstance(di, dict):
            info["default_instance_mass"] = {k: str(safe(lambda k=k: di.get_editor_property(k)))[:120]
                                             for k in ("override_mass", "mass_in_kg_override", "mass_scale")}
    bb = mesh.get_bounding_box()
    info["bounds_min_cm"] = v3(bb.min)
    info["bounds_max_cm"] = v3(bb.max)
    info["size_cm"] = [round(bb.max.x - bb.min.x, 6), round(bb.max.y - bb.min.y, 6), round(bb.max.z - bb.min.z, 6)]
    bs = safe(lambda: mesh.get_bounds())
    if not isinstance(bs, dict):
        info["sphere_bounds"] = {"origin": v3(bs.origin), "box_extent": v3(bs.box_extent),
                                 "sphere_radius_cm": round(float(bs.sphere_radius), 6)}
    info["material_slots"] = [{"slot": str(s.material_slot_name),
                               "material": s.material_interface.get_path_name() if s.material_interface else None}
                              for s in mesh.get_editor_property("static_materials")]
    info["socket_objects"] = {}
    for name in ("Grip", "Trail"):
        s = mesh.find_socket(name)
        if s is None:
            info["socket_objects"][name] = {"found": False}
            continue
        r = s.get_editor_property("relative_rotation")
        info["socket_objects"][name] = {
            "found": True, "socket_name": str(s.get_editor_property("socket_name")),
            "outer": s.get_outer().get_path_name() if s.get_outer() else None,
            "relative_location_cm": v3(s.get_editor_property("relative_location")),
            "relative_rotation": {"roll": round(r.roll, 6), "pitch": round(r.pitch, 6), "yaw": round(r.yaw, 6)},
            "relative_scale": v3(s.get_editor_property("relative_scale")),
        }
    info["socket_array_len"] = safe(lambda: len(mesh.get_editor_property("sockets")))
    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    info["component_socket_names"] = sorted(str(n_) for n_ in comp.get_all_socket_names())
    info["component_sockets"] = {}
    for name in info["component_socket_names"]:
        t = comp.get_socket_transform(name, unreal.RelativeTransformSpace.RTS_COMPONENT)
        rot = t.rotation.rotator()
        info["component_sockets"][name] = {"location_cm": v3(t.translation), "scale": v3(t.scale3d),
                                           "rotator": {"roll": round(rot.roll, 6), "pitch": round(rot.pitch, 6),
                                                       "yaw": round(rot.yaw, 6)}}
    info["import_filenames"] = safe(lambda: [str(f) for f in mesh.get_editor_property("asset_import_data").extract_filenames()])
    info["registry_import_tag"] = registry_import_tag(C.ASSET)
    return info


def close(a, b, tol):
    return len(a) == len(b) and all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def mesh_gates(info, side):
    g, d = {}, {}
    g["G1_three_lods"] = info["num_lods"] == 3
    oth = info.get("other_collision_elems", {})
    g["G2_exactly_one_convex_hull"] = info.get("convex_hulls") == 1 and all(
        v == 0 for v in oth.values() if isinstance(v, int))
    sock_ok = info["component_socket_names"] == ["Grip", "Trail"]
    exp = {r["socket"]: r for r in side["sockets"]}
    spec = {"Grip": (C.SPEC_GRIP_CM, C.SPEC_GRIP_YAW), "Trail": ([0.0, 0.0, 0.0], 0.0)}
    sd = {}
    for name, (loc, yaw) in spec.items():
        s = info["socket_objects"].get(name, {})
        cs = info["component_sockets"].get(name, {})
        e = exp.get(name)
        ok = bool(s.get("found")) and e is not None and bool(cs)
        if ok:
            rot = s["relative_rotation"]
            ok = (close(s["relative_location_cm"], loc, 1e-4)
                  and close(s["relative_location_cm"], e["location_cm"], 1e-6)
                  and abs(rot["yaw"] - yaw) < 1e-4 and abs(rot["roll"]) < 1e-4 and abs(rot["pitch"]) < 1e-4
                  and close(s["relative_scale"], [1.0, 1.0, 1.0], 0.0)
                  and (s["outer"] or "").startswith(C.ASSET + ".")
                  and close(cs["scale"], [1.0, 1.0, 1.0], 1e-6)
                  and close(cs["location_cm"], loc, 1e-4)
                  and abs(cs["rotator"]["yaw"] - yaw) < 1e-4)
        sd[name] = ok
        sock_ok = sock_ok and ok
    g["G3_grip_trail_scale_1_spec_cm"] = sock_ok
    d["G3"] = sd
    size_ok = close(info["size_cm"], C.SPEC_SIZE_CM, 5e-4)
    centred = all(abs(a + b) < 1e-4 for a, b in zip(info["bounds_min_cm"], info["bounds_max_cm"]))
    g["G4_bounds_cm_match_spec_centred"] = size_ok and centred
    d["G4"] = {"unreal": info["size_cm"], "spec": [round(x, 6) for x in C.SPEC_SIZE_CM], "centred": centred}
    ss = info["lod_screen_sizes_render_data"]
    g["G5_lod_screen_sizes"] = (isinstance(ss, list) and close(ss, C.SPEC_SCREEN, 1e-6)
                                and close(side["lod_screen_sizes"], C.SPEC_SCREEN, 1e-9)
                                and info.get("is_lod_screen_size_auto_computed") is False)
    d["G5"] = {"unreal": ss, "sidecar": side["lod_screen_sizes"], "spec": C.SPEC_SCREEN}
    bs = info["lod_build_settings"]
    g["G6_lightmap_index_1"] = (info["light_map_coordinate_index"] == 1 and len(bs) == info["num_lods"]
                                and all(isinstance(b, dict) and "error" not in b and b["generate_lightmap_u_vs"] is True
                                        and b["src_lightmap_index"] == 0 and b["dst_lightmap_index"] == 1 for b in bs))
    return g, d


TEX_INTENT = {
    "BC": {"srgb": "True", "compression_settings": "TC_DEFAULT"},
    "ORM": {"srgb": "False", "compression_settings": "TC_MASKS"},
    "N": {"srgb": "False", "compression_settings": "TC_NORMALMAP", "flip_green_channel": "False"},
}


def tex_info(tex):
    info = {"asset": tex.get_path_name(), "class": tex.get_class().get_name()}
    for k in ("srgb", "compression_settings", "flip_green_channel", "lod_group", "compression_no_alpha",
              "mip_gen_settings", "virtual_texture_streaming", "never_stream"):
        val = safe(lambda k=k: tex.get_editor_property(k))
        info[k] = str(val.name) if hasattr(val, "name") and not isinstance(val, (bool, int)) else str(val)
    info["size"] = safe(lambda: [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())])
    info["import_filenames"] = safe(lambda: [str(f) for f in tex.get_editor_property("asset_import_data").extract_filenames()])
    return info


def main():
    rep = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": C.ASSET, "fresh_process": True}
    side = json.loads(C.SIDECAR.read_text(encoding="utf-8"))
    rep["fbx_sha256_now"] = C.sha256(C.FBX)
    rep["fbx_md5_now"] = C.md5(C.FBX)
    rep["sidecar_sha256_now"] = C.sha256(C.SIDECAR)
    try:
        content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
        rep["uasset_on_disk"] = str(content / C.DEST[len("/Game/"):] / f"{C.MESH}.uasset")
        rep["uasset_exists"] = Path(rep["uasset_on_disk"]).exists()
        mesh = unreal.load_asset(C.ASSET)
        rep["mesh"] = mesh_info(mesh)
        rep["gates"], rep["detail"] = mesh_gates(rep["mesh"], side)
        tag = rep["mesh"]["registry_import_tag"].get("parsed")
        rep["mesh_import_md5_matches_shipped"] = (isinstance(tag, list) and len(tag) == 1
                                                  and str(tag[0].get("FileMD5", "")).lower() == rep["fbx_md5_now"])
    except Exception:  # noqa: BLE001
        rep["error"] = traceback.format_exc()
    rep["textures"] = {}
    for kind in ("BC", "ORM", "N"):
        stem = f"T_Shuriken_SixPoint_{kind}"
        shipped = C.TEX_SHIPPED / f"{stem}.png"
        staged = C.TEX_STAGE / f"{stem}.png"
        rec = {"asset": f"{C.TEX_DEST}/{stem}", "shipped_sha256": C.sha256(shipped),
               "staged_sha256": C.sha256(staged), "shipped_md5": C.md5(shipped)}
        try:
            tex = unreal.load_asset(rec["asset"])
            if tex is None:
                rec["ok"] = False
                rec["error"] = "asset not found"
            else:
                rec["info"] = tex_info(tex)
                rec["registry_import_tag"] = registry_import_tag(rec["asset"])
                tag = rec["registry_import_tag"].get("parsed")
                want = TEX_INTENT[kind]
                checks = {}
                for k, v in want.items():
                    got = rec["info"].get(k, "")
                    checks[k] = got == v or got.endswith("." + v) or got.upper() == v.upper()
                checks["size_2048"] = rec["info"].get("size") == [2048, 2048]
                checks["texture2d"] = rec["info"].get("class") == "Texture2D"
                checks["staged_bytes_equal_shipped"] = rec["staged_sha256"] == rec["shipped_sha256"]
                checks["import_md5_equals_shipped"] = (isinstance(tag, list) and len(tag) == 1
                                                       and str(tag[0].get("FileMD5", "")).lower() == rec["shipped_md5"])
                rec["checks"] = checks
                rec["ok"] = all(checks.values())
        except Exception:  # noqa: BLE001
            rec["error"] = traceback.format_exc()
            rec["ok"] = False
        rep["textures"][stem] = rec
    rep["subsystem_route"] = dict(C.SUBSYSTEM_ROUTE)
    C.write(C.HERE / "s3_readback.json", rep)
    unreal.log("U9_S3_DONE")


main()
