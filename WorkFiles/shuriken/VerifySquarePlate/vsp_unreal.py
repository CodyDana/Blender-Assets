"""Unreal-side helpers for the independent verification (runs inside the UE 5.8 pythonscript commandlet).

Reuses UnrealCheck6's read-only inspector (uc6_common.inspect) and its gate function by PARAMETERIZING it
(form via SHURIKEN_FORM, content path and counts overridden here) instead of copying it, and adds the
verifier's own gates whose expectations come from vsp_config (the study), not from the build.
"""
import json
import math
import os
import sys
from pathlib import Path

import unreal

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\VerifySquarePlate")
UC6 = HERE.parent / "UnrealCheck6"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(UC6))
sys.path.insert(0, str(HERE.parents[2] / "Scripts"))

import vsp_config as V  # noqa: E402

os.environ["SHURIKEN_FORM"] = V.FORM
import uc6_common as C  # noqa: E402  (parameterized below; its module constants are overridden, not edited)

S = V.spec()
BLENDER_FBX = json.loads((HERE / "vsp_blender_fbx.json").read_text(encoding="utf-8"))
BLENDER_BLEND = json.loads((HERE / "vsp_blender_blend.json").read_text(encoding="utf-8"))

# --- parameterize UnrealCheck6 for this verifier: new content path, verifier's own Blender counts
C.DEST = V.DEST
C.ASSET = S["asset"]
C.FBX = S["fbx"]
C.SIDECAR = S["sidecar"]
C.FBX_LOD_TRIANGLES = BLENDER_FBX["lod_triangles"]


def _vertex_positions(mesh, lod):
    """Source vertex positions (Unreal cm, Unreal frame) of one LOD, via the StaticMeshDescription."""
    desc = mesh.get_static_mesh_description(lod)
    out = []
    n = desc.get_vertex_count()

    def make_id(i):
        for field in ("id_value", "value"):
            try:
                vid = unreal.VertexID()
                vid.set_editor_property(field, i)
                return vid
            except Exception:  # noqa: BLE001
                pass
        return unreal.VertexID(i)

    for i in range(n):
        p = desc.get_vertex_position(make_id(i))
        out.append((p.x, p.y, p.z))
    return out


def extra_inspect(mesh):
    """Readings UnrealCheck6 does not take: bounds sphere, build flags, geometry in Unreal's own frame."""
    info = {}
    b = mesh.get_bounds()
    info["bounds_origin_cm"] = C.vec(b.origin, 6)
    info["bounds_box_extent_cm"] = C.vec(b.box_extent, 6)
    info["bounds_sphere_radius_cm"] = round(b.sphere_radius, 6)
    bb = mesh.get_bounding_box()
    info["bounding_box_min_cm_6dp"] = C.vec(bb.min, 6)
    info["bounding_box_max_cm_6dp"] = C.vec(bb.max, 6)
    sub = C.subsystem()
    flags = []
    for i in range(mesh.get_num_lods()):
        def read(i=i):
            bs = sub.get_lod_build_settings(mesh, i)
            return {k: C.safe(lambda k=k: bs.get_editor_property(k)) for k in (
                "use_full_precision_u_vs", "use_high_precision_tangent_basis", "compute_weighted_normals",
                "build_reversed_index_buffer", "use_backwards_compatible_f16_trunc_u_vs")}
        flags.append(C.safe(read))
    info["lod_build_flags"] = flags
    info["lod_screen_sizes_raw"] = C.safe(lambda: [float(v) for v in sub.get_lod_screen_sizes(mesh)])
    info["lod_count_subsystem"] = C.safe(lambda: int(sub.get_lod_count(mesh)))
    info["lightmap_uv_channels_after_build"] = C.safe(lambda: [int(sub.get_num_uv_channels(mesh, i))
                                                            for i in range(mesh.get_num_lods())])
    info["allow_cpu_access"] = C.safe(lambda: bool(mesh.get_editor_property("allow_cpu_access")))
    # geometry in Unreal's frame from the saved source model (no convention assumed)
    geo = {}
    try:
        pts = _vertex_positions(mesh, 0)
        geo["lod0_vertex_count_source"] = len(pts)
        ex = max(pts, key=lambda p: p[0])
        ey = max(pts, key=lambda p: p[1])
        radii = [math.hypot(p[0], p[1]) for p in pts]
        imin = min(range(len(pts)), key=lambda i: radii[i])
        geo.update({
            "max_x_vertex_cm": [round(c, 6) for c in ex], "max_y_vertex_cm": [round(c, 6) for c in ey],
            "corner_radius_cm": round(max(radii), 6),
            "hole_min_radius_cm": round(radii[imin], 6),
            "hole_min_radius_azimuths_deg": sorted({round(math.degrees(math.atan2(pts[i][1], pts[i][0])), 3)
                                                    for i in range(len(pts)) if abs(radii[i] - radii[imin]) < 1e-5}),
            "z_range_cm": [round(min(p[2] for p in pts), 6), round(max(p[2] for p in pts), 6)],
        })
        sockets = {}
        comp = unreal.new_object(unreal.StaticMeshComponent)
        comp.set_static_mesh(mesh)
        for sname in comp.get_all_socket_names():
            s = mesh.find_socket(sname)
            if s is None:
                continue
            name = str(s.get_editor_property("socket_name"))
            loc = s.get_editor_property("relative_location")
            q = (loc.x, loc.y, loc.z)
            az = math.degrees(math.atan2(q[1], q[0])) if math.hypot(q[0], q[1]) > 1e-9 else None
            near = min(pts, key=lambda p: math.dist(p, q))
            ray = [p for p in pts if az is not None and math.hypot(p[0], p[1]) > 1e-6
                   and abs(math.degrees(math.atan2(p[1], p[0])) - az) < 1e-3]
            rot = s.get_editor_property("relative_rotation")
            fwd = unreal.MathLibrary.get_forward_vector(rot)
            up = unreal.MathLibrary.get_up_vector(rot)
            sockets[name] = {
                "location_cm": [round(c, 6) for c in q],
                "radius_cm": round(math.hypot(q[0], q[1]), 6),
                "azimuth_deg": None if az is None else round(az, 4),
                "nearest_lod0_vertex_cm": [round(c, 6) for c in near],
                "nearest_lod0_vertex_distance_cm": round(math.dist(near, q), 6),
                "lod0_max_radius_on_this_azimuth_cm": round(max((math.hypot(p[0], p[1]) for p in ray), default=-1.0), 6),
                "forward_x_axis": [round(fwd.x, 6), round(fwd.y, 6), round(fwd.z, 6)],
                "up_z_axis": [round(up.x, 6), round(up.y, 6), round(up.z, 6)],
            }
        geo["sockets"] = sockets
    except Exception as exc:  # noqa: BLE001
        geo["error"] = f"{type(exc).__name__}: {exc}"[:300]
    info["unreal_frame_geometry"] = geo
    return info


def verifier_gates(info, extra, sidecar):
    """Gates 1-6 with the verifier's own expectations (study-derived), plus agreement with the sidecar/report."""
    t = V.TOL
    blender_tris = BLENDER_FBX["lod_triangles"]
    blend_tris = BLENDER_BLEND["lod_triangles"]
    tri_delta = [a - b for a, b in zip(info["lod_triangles"], blender_tris)]
    g1 = (info["num_lods"] == 3 and len(info["lod_triangles"]) == 3 and tri_delta == [0, 0, 0]
          and blender_tris == blend_tris)

    other = info["other_collision_elems"]
    g2 = (info["convex_hulls"] == 1 and all(other.get(k, 0) == 0 for k in ("box_elems", "sphere_elems", "sphyl_elems"))
          and other.get("tapered_capsule_elems", 0) in (0, -1))

    geo = extra.get("unreal_frame_geometry", {})
    sk = {s["name"]: s for s in info["sockets"]}
    raw = {r["name"]: r for r in info["socket_array"]}
    det = {}
    grip, trail = sk.get("Grip"), sk.get("Trail")
    gs = S["grip"]
    if grip:
        loc = grip["location_cm"]
        r = math.hypot(loc[0], loc[1])
        az = math.degrees(math.atan2(loc[1], loc[0]))
        az_ok = any(abs(az - a) < t["socket_deg"] for a in gs["azimuths_deg"])
        yaw = grip["rpy"][2]
        g_geo = (geo.get("sockets") or {}).get("Grip", {})
        fwd = g_geo.get("forward_x_axis")
        outward = [math.cos(math.radians(az)), math.sin(math.radians(az)), 0.0]
        det["Grip"] = {
            "radius_cm": round(r, 6), "expected_radius_cm": gs["radius_cm"],
            "radius_ok": abs(r - gs["radius_cm"]) < t["socket_cm"],
            "azimuth_deg": round(az, 4), "azimuth_on_a_side_midpoint": az_ok,
            "z_ok": abs(loc[2] - gs["z_cm"]) < t["socket_cm"],
            "x_axis_points_outward": (fwd is not None and all(abs(a - b) < 1e-4 for a, b in zip(fwd, outward))
                                      and abs(yaw - az) < t["socket_deg"]),
            "roll_pitch_zero": abs(grip["rpy"][0]) < t["socket_deg"] and abs(grip["rpy"][1]) < t["socket_deg"],
            "on_rim": (g_geo.get("nearest_lod0_vertex_distance_cm", 1.0) <= S["thickness_mm"] / 20.0 + 1e-6
                       and abs(g_geo.get("lod0_max_radius_on_this_azimuth_cm", -1.0) - r) < t["socket_cm"]),
            "scale_1": grip["scale"] == [1.0, 1.0, 1.0],
        }
    if trail:
        loc = trail["location_cm"]
        t_geo = (geo.get("sockets") or {}).get("Trail", {})
        det["Trail"] = {
            "at_origin": all(abs(a - b) < t["socket_cm"] for a, b in zip(loc, S["trail"]["location_cm"])),
            "z_axis_is_mesh_up": t_geo.get("up_z_axis") is not None and all(
                abs(a - b) < 1e-4 for a, b in zip(t_geo["up_z_axis"], [0.0, 0.0, 1.0])),
            "rpy_zero": all(abs(v) < t["socket_deg"] for v in trail["rpy"]),
            "scale_1": trail["scale"] == [1.0, 1.0, 1.0],
        }
    raw_ok = (set(raw) == {"Grip", "Trail"} and all(
        r["relative_scale"] == [1.0, 1.0, 1.0] and (r["outer"] or "").startswith(S["asset"]) for r in raw.values()))
    side_rec = {r["socket"]: r for r in sidecar["sockets"]}
    agrees_sidecar = all(
        n in side_rec and all(abs(a - b) < t["socket_cm"] for a, b in zip(sk[n]["location_cm"], side_rec[n]["location_cm"]))
        and abs(sk[n]["rpy"][2] - side_rec[n]["rotation_deg"]["yaw"]) < t["socket_deg"] for n in sk)
    g3 = (set(sk) == {"Grip", "Trail"} and len(info["sockets"]) == 2 and raw_ok and agrees_sidecar
          and all(all(v.values()) if isinstance(v, dict) else v for v in (
              {k: x for k, x in det.get("Grip", {}).items() if isinstance(x, bool)},
              {k: x for k, x in det.get("Trail", {}).items() if isinstance(x, bool)})) and "Grip" in det and "Trail" in det)

    size = info["size_cm"]
    bmin, bmax = extra["bounding_box_min_cm_6dp"], extra["bounding_box_max_cm_6dp"]
    size6 = [bmax[i] - bmin[i] for i in range(3)]
    centred = all(abs(bmin[i] + bmax[i]) < 1e-4 for i in range(3))
    corners = (abs(geo.get("max_x_vertex_cm", [0, 1, 0])[1]) < 1e-4 and abs(geo.get("max_y_vertex_cm", [1, 0, 0])[0]) < 1e-4
               and abs(geo.get("corner_radius_cm", 0) - S["bounding_radius_mm"] / 10.0) < t["size_cm"])
    g4 = (all(abs(a - e) < t["size_cm"] for a, e in zip(size6, S["size_cm"])) and centred and corners)

    screen = info["lod_screen_sizes"]
    radius = extra["bounds_sphere_radius_cm"]
    switch = [None] + [round(V.SCREEN_MULTIPLE * radius / s, 2) for s in screen[1:]] if isinstance(screen, list) else None
    g5 = (isinstance(screen, list) and len(screen) == 3
          and all(abs(a - e) < t["screen_size"] for a, e in zip(screen, S["screen_sizes"]))
          and sidecar.get("lod_screen_sizes") == S["screen_sizes"]
          and switch is not None and all(abs(a - b) < t["switch_distance_cm"]
                                          for a, b in zip(switch[1:], S["pack_switch_distance_cm"][1:])))

    builds = [b for b in info["lod_build_settings"] if isinstance(b, dict) and "error" not in b]
    g6 = (info["light_map_coordinate_index"] == 1 and len(builds) == 3
          and all(b["generate_lightmap_u_vs"] and b["src_lightmap_index"] == 0 and b["dst_lightmap_index"] == 1
                  for b in builds))

    gates = {"1_lod_count_and_triangles_delta_0": g1, "2_exactly_one_convex_hull": g2,
             "3_grip_trail_scale_1_sane_cm": g3, "4_bounds_cm_match_spec": g4,
             "5_screen_sizes_applied_from_sidecar": g5, "6_lightmap_coordinate_index_1": g6}
    detail = {"triangle_delta_vs_blender_fbx_reimport": tri_delta, "blender_fbx_reimport_lod_triangles": blender_tris,
              "blender_blend_lod_triangles": blend_tris, "socket_checks": det, "raw_socket_array_ok": raw_ok,
              "sockets_agree_with_sidecar": agrees_sidecar,
              "size_cm_6dp": [round(v, 6) for v in size6], "size_cm_4dp": size, "expected_size_cm": S["size_cm"],
              "bounds_centred_on_origin": centred, "corners_on_axes_and_radius": corners,
              "expected_screen_sizes_from_study": S["screen_sizes"], "sidecar_screen_sizes": sidecar.get("lod_screen_sizes"),
              "unreal_bounds_sphere_radius_cm": radius, "switch_distance_cm": switch,
              "pack_switch_distance_cm": S["pack_switch_distance_cm"]}
    return gates, detail
