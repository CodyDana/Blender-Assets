"""Shared helpers for the independent PaperBomb Unreal review (UE 5.8.2 pythonscript commandlet).

Independent of the build: every expectation comes from the STUDY figures and from
an independent Blender re-import of the exact shipped FBX bytes
(pb_fbx_truth.json), never from the build report.  The build report is loaded only
so the review can say where the two disagree.

Content path /Game/PropsCheck/PaperBombReview, in
WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject.  Never DemoGame_1.
"""
import hashlib
import json
import math
import os
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealReview"
DEST = os.environ.get("PB_DEST", "/Game/PropsCheck/PaperBombReview")
MESH = "SM_PaperBomb"
ASSET = f"{DEST}/{MESH}"
TEX_DEST = f"{DEST}/Textures"
FBX = PROJ / "Exports" / "PaperBomb" / f"{MESH}.fbx"
SIDECAR = PROJ / "Exports" / "PaperBomb" / f"{MESH}.sockets.json"
TEXDIR = PROJ / "Exports" / "PaperBomb" / "Textures"

TRUTH = json.loads((HERE / "pb_fbx_truth.json").read_text(encoding="utf-8"))
SIDECAR_PAYLOAD = json.loads(SIDECAR.read_text(encoding="utf-8"))
EXPECTED_SOCKETS = {r["socket"]: r for r in SIDECAR_PAYLOAD["sockets"]}
SIDECAR_SCREEN_SIZES = SIDECAR_PAYLOAD.get("lod_screen_sizes")

# --- independent expectations -------------------------------------------------
# triangles: from the Blender re-import of the shipped bytes, not from the report
BLENDER_LOD_TRIANGLES = [TRUTH["nodes"][f"{MESH}_LOD{i}"]["triangles"] for i in range(3)]
LOD0_SIZE_CM = TRUTH["nodes"][f"{MESH}_LOD0"]["size_cm"]
HULL_NODE = f"UCX_{MESH}_LOD0_00"
HULL_VERTS_FBX = TRUTH["nodes"][HULL_NODE]["verts_ue_cm"]
LOD0_VERTS_FBX = TRUTH["nodes"][f"{MESH}_LOD0"]["verts_ue_cm"]

# study 3: card 70 x 156 mm, LOD bands, pack LOD rule
STUDY_CARD_MM = (70.0, 156.0)
STUDY_LOD_BANDS = [(1000, 1600), (350, 650), (100, 200)]
PACK_LOD_SCREEN_SIZES = (1.0, 0.10, 0.035)
PACK_LOD_REFERENCE_RADIUS_MM = 50.0
REFERENCE_HFOV_DEG = 90.0
REFERENCE_ASPECT = 16.0 / 9.0
EXPECTED_SOCKET_NAMES = ["Attach", "Cord", "Face", "Fuse"]
EXPECTED_MATERIAL_SLOTS = ["M_PaperBomb"]
TEXTURES = ["T_PaperBomb_BC", "T_PaperBomb_ORM", "T_PaperBomb_N", "T_PaperBomb_M"]


def bounds_radius_mm_from_size(size_cm):
    """Unreal's bounding-sphere radius for a box centred on the pivot, in mm."""
    return 10.0 * math.sqrt(sum((0.5 * s) ** 2 for s in size_cm))


def scaled_lod_screen_sizes(radius_mm):
    f = radius_mm / PACK_LOD_REFERENCE_RADIUS_MM
    return [1.0] + [round(s * f, 4) for s in PACK_LOD_SCREEN_SIZES[1:]]


def screen_size_distance_m(screen_size, radius_m):
    mult = max(1.0, REFERENCE_ASPECT) / math.tan(math.radians(0.5 * REFERENCE_HFOV_DEG))
    return mult * radius_m / screen_size


EXPECTED_BOUNDS_RADIUS_MM = bounds_radius_mm_from_size(LOD0_SIZE_CM)
EXPECTED_SCREEN_SIZES = scaled_lod_screen_sizes(EXPECTED_BOUNDS_RADIUS_MM)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def vec(v, nd=5):
    return [round(v.x, nd), round(v.y, nd), round(v.z, nd)]


def subsystem():
    try:
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001
        sub = None
    if sub is None:
        sub = unreal.new_object(unreal.StaticMeshEditorSubsystem)
    return sub


def safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"[:200]} if default is None else default


def _axes(rot):
    """Socket forward / right / up unit vectors from an Unreal rotator, in the asset frame."""
    p = math.radians(rot.pitch); y = math.radians(rot.yaw); r = math.radians(rot.roll)
    cp, sp, cy, sy, cr, sr = math.cos(p), math.sin(p), math.cos(y), math.sin(y), math.cos(r), math.sin(r)
    fwd = (cp * cy, cp * sy, sp)
    right = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
    up = (-(cr * sp * cy + sr * sy), -(cr * sp * sy - sr * cy), cr * cp)
    rnd = lambda t: [round(v, 4) for v in t]  # noqa: E731
    return {"forward_x_axis": rnd(fwd), "right_y_axis": rnd(right), "up_z_axis": rnd(up)}


def inspect(mesh):
    sub = subsystem()
    info = {"asset": mesh.get_path_name()}
    n = mesh.get_num_lods()
    info["num_lods"] = n
    info["lod_triangles"] = [mesh.get_num_triangles(i) for i in range(n)]
    info["lod_vertices"] = [mesh.get_num_vertices(i) for i in range(n)]
    info["lod_sections"] = [safe(lambda i=i: mesh.get_num_sections(i)) for i in range(n)]
    info["lod_screen_sizes"] = safe(lambda: [round(float(v), 6) for v in sub.get_lod_screen_sizes(mesh)])
    info["lod_source_uv_channels"] = [safe(lambda i=i: int(sub.get_num_uv_channels(mesh, i))) for i in range(n)]
    info["auto_compute_lod_screen_size"] = safe(lambda: bool(mesh.get_editor_property("auto_compute_lod_screen_size")))
    builds = []
    for i in range(n):
        def read(i=i):
            bs = sub.get_lod_build_settings(mesh, i)
            return {k: bs.get_editor_property(k) for k in (
                "generate_lightmap_u_vs", "src_lightmap_index", "dst_lightmap_index",
                "min_lightmap_resolution", "recompute_normals", "recompute_tangents",
                "use_mikk_t_space", "remove_degenerates", "use_full_precision_u_vs")}
        builds.append(safe(read))
    info["lod_build_settings"] = builds
    info["light_map_coordinate_index"] = safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index")))
    info["light_map_resolution"] = safe(lambda: int(mesh.get_editor_property("light_map_resolution")))
    info["nanite_enabled"] = safe(
        lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")))
    body = mesh.get_editor_property("body_setup")
    agg = body.get_editor_property("agg_geom")
    info["convex_hulls"] = len(agg.get_editor_property("convex_elems"))
    info["other_collision_elems"] = {k: safe(lambda k=k: len(agg.get_editor_property(k)), default=-1)
                                     for k in ("box_elems", "sphere_elems", "sphyl_elems", "tapered_capsule_elems")}
    info["collision_trace_flag"] = str(body.get_editor_property("collision_trace_flag"))
    info["collision_complexity_ok"] = "SIMPLE_AND_COMPLEX" in str(body.get_editor_property("collision_trace_flag")) \
        or "DEFAULT" in str(body.get_editor_property("collision_trace_flag"))
    b = mesh.get_bounding_box()
    info["bounds_min_cm"] = vec(b.min)
    info["bounds_max_cm"] = vec(b.max)
    info["size_cm"] = [round(b.max.x - b.min.x, 5), round(b.max.y - b.min.y, 5), round(b.max.z - b.min.z, 5)]
    info["bounds_radius_mm"] = round(bounds_radius_mm_from_size(info["size_cm"]), 4)
    info["material_slots"] = [{"slot": str(s.material_slot_name),
                               "material": s.material_interface.get_path_name() if s.material_interface else None}
                              for s in mesh.get_editor_property("static_materials")]
    info["socket_array"] = []
    comp0 = unreal.new_object(unreal.StaticMeshComponent)
    comp0.set_static_mesh(mesh)
    for sname in comp0.get_all_socket_names():
        s = mesh.find_socket(sname)
        if s is None:
            info["socket_array"].append({"name": str(sname), "find_socket": None})
            continue
        rot = s.get_editor_property("relative_rotation")
        info["socket_array"].append({
            "name": str(s.get_editor_property("socket_name")),
            "outer": s.get_outer().get_path_name() if s.get_outer() else None,
            "relative_location": vec(s.get_editor_property("relative_location")),
            "relative_rotation": [round(rot.roll, 4), round(rot.pitch, 4), round(rot.yaw, 4)],
            "relative_scale": vec(s.get_editor_property("relative_scale")),
            "axes": _axes(rot),
        })
    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    info["sockets"] = []
    for name in comp.get_all_socket_names():
        t = comp.get_socket_transform(str(name), unreal.RelativeTransformSpace.RTS_COMPONENT)
        e = t.rotation.euler()
        info["sockets"].append({"name": str(name), "location_cm": vec(t.translation),
                                "rpy": [round(e.x, 3), round(e.y, 3), round(e.z, 3)],
                                "scale": vec(t.scale3d)})
    return info


def lod_positions_cm(mesh, lod):
    desc = mesh.get_static_mesh_description(lod)
    out = []

    def make_id(i):
        for field in ("id_value", "value"):
            try:
                vid = unreal.VertexID()
                vid.set_editor_property(field, i)
                return vid
            except Exception:  # noqa: BLE001
                pass
        return unreal.VertexID(i)

    for i in range(desc.get_vertex_count()):
        p = desc.get_vertex_position(make_id(i))
        out.append((p.x, p.y, p.z))
    return out


def two_sided_max(a, b):
    def one(src, dst):
        worst = 0.0
        for p in src:
            best = min((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2 for q in dst)
            worst = max(worst, best)
        return math.sqrt(worst)
    return max(one(a, b), one(b, a))


def gates(info, textures=None):
    """Independent gates.  Nothing here reads the build report."""
    n = info["num_lods"]
    tri_delta = [a - b for a, b in zip(info["lod_triangles"], BLENDER_LOD_TRIANGLES)]
    bands_ok = [lo <= t <= hi for t, (lo, hi) in zip(info["lod_triangles"], STUDY_LOD_BANDS)]

    size_ok = all(abs(a - e) < 1e-4 for a, e in zip(info["size_cm"], LOD0_SIZE_CM))
    # study: the card is 70 x 156 mm (the plan; the Z bound is the curl+crease, study estimate 2.6 mm)
    card_ok = (abs(info["size_cm"][0] * 10.0 - STUDY_CARD_MM[1]) < 0.5
               and abs(info["size_cm"][1] * 10.0 - STUDY_CARD_MM[0]) < 0.5)

    sockets_ok = (len(info["sockets"]) == len(EXPECTED_SOCKET_NAMES)
                  and len(info["socket_array"]) == len(EXPECTED_SOCKET_NAMES)
                  and sorted(s["name"] for s in info["sockets"]) == EXPECTED_SOCKET_NAMES)
    socket_detail = {}
    for s in info["sockets"]:
        exp = EXPECTED_SOCKETS.get(s["name"])
        loc_ok = exp is not None and all(abs(a - e) < 1e-3 for a, e in zip(s["location_cm"], exp["location_cm"]))
        # inside the bounding box, with a little slack for a socket that sits on the surface
        inside = all(info["bounds_min_cm"][i] - 0.2 <= s["location_cm"][i] <= info["bounds_max_cm"][i] + 0.2
                     for i in range(3))
        scale_ok = s["scale"] == [1.0, 1.0, 1.0]
        socket_detail[s["name"]] = {"location_matches_sidecar": bool(loc_ok), "scale_1": bool(scale_ok),
                                    "inside_bounds": bool(inside), "location_cm": s["location_cm"]}
        sockets_ok = sockets_ok and loc_ok and scale_ok and inside
    raw_ok = all(r["relative_scale"] == [1.0, 1.0, 1.0] and (r["outer"] or "").startswith(ASSET)
                 for r in info["socket_array"])

    lm_builds = [b for b in info["lod_build_settings"] if isinstance(b, dict) and "error" not in b]
    lightmap_ok = (info["light_map_coordinate_index"] == 1
                   and len(lm_builds) == n
                   and all(b["generate_lightmap_u_vs"] and b["src_lightmap_index"] == 0
                           and b["dst_lightmap_index"] == 1 for b in lm_builds))

    screen = info["lod_screen_sizes"]
    screen_ok = (isinstance(screen, list) and len(screen) == 3
                 and all(abs(a - e) < 1e-6 for a, e in zip(screen, SIDECAR_SCREEN_SIZES))
                 and [round(v, 4) for v in SIDECAR_SCREEN_SIZES] == EXPECTED_SCREEN_SIZES
                 and info["auto_compute_lod_screen_size"] is not True)

    hulls_ok = (info["convex_hulls"] == 1
                and all(v in (0, -1) for v in info["other_collision_elems"].values()))

    slots = [m["slot"] for m in info["material_slots"]]
    slots_ok = slots == EXPECTED_MATERIAL_SLOTS

    out = {
        "1_lod_count_3_and_triangles_match_blender": n == 3 and tri_delta == [0, 0, 0],
        "2_lod_triangles_inside_study_bands": all(bands_ok),
        "3_exactly_one_convex_hull_no_other_primitives": hulls_ok,
        "4_four_sockets_scale_1_sane_cm_outered_to_asset": bool(sockets_ok and raw_ok),
        "5_bounds_cm_match_shipped_fbx_and_study_card": bool(size_ok and card_ok),
        "6_lod_screen_sizes_from_sidecar_and_pack_rule": bool(screen_ok),
        "7_lightmap_coordinate_index_1_generated_on_every_lod": bool(lightmap_ok),
        "8_one_material_slot_named_M_PaperBomb": bool(slots_ok),
        "9_nanite_off": info["nanite_enabled"] is False,
    }
    detail = {
        "triangle_delta_vs_blender": tri_delta,
        "blender_fbx_reimport_lod_triangles": BLENDER_LOD_TRIANGLES,
        "study_lod_bands": STUDY_LOD_BANDS, "lod_bands_ok": bands_ok,
        "expected_size_cm_from_fbx": LOD0_SIZE_CM,
        "expected_screen_sizes_from_pack_rule": EXPECTED_SCREEN_SIZES,
        "sidecar_screen_sizes": SIDECAR_SCREEN_SIZES,
        "expected_bounds_radius_mm": round(EXPECTED_BOUNDS_RADIUS_MM, 4),
        "socket_detail": socket_detail,
        "raw_socket_array_scale_1_and_outered_to_asset": raw_ok,
        "material_slots": slots,
    }
    if textures is not None:
        out["10_every_texture_flag_and_mipgen_correct"] = bool(textures.get("passed"))
        detail["textures"] = textures
    return out, detail
