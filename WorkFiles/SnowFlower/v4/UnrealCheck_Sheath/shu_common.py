"""Shared helpers for SM_SnowFlower_Sheath's Unreal verification (UE 5.8 pythonscript commandlet).

Adapted copy of WorkFiles/SnowFlower/v4/UnrealCheck/sfu_common.py (the sword's harness, left unchanged).

Adapted COPY of WorkFiles/paperbomb/UnrealCheck/uc_common.py (that folder is the paused
paper bomb's and is left alone).  Verifies under a NEW content path in the shuriken-only
validation project, never DemoGame_1.

Everything expected is read from the BUILD's outputs, never typed twice:

    WorkFiles/SnowFlower/v4/sheath_report.json  LOD triangles, screen sizes, bounds,
                                                  sockets, the SHA-256 of the shipped bytes
    Exports/SnowFlower/v4/SM_SnowFlower.sockets.json  the sidecar Unreal applies
    WorkFiles/smokebomb/UnrealCheck/blender_fbx_counts.json
                                                  a SECOND Blender process's re-import of
                                                  the shipped FBX
"""
import hashlib
import itertools
import json
import math
import os
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "SnowFlower" / "v4" / "UnrealCheck_Sheath"
DEST = os.environ.get("SNOWFLOWER_DEST", "/Game/SwordCheck/SnowFlowerSheath")
REPORT = json.loads((PROJ / "WorkFiles" / "SnowFlower" / "v4" / "sheath_report.json").read_text(encoding="utf-8"))
MESH = REPORT["asset"]
FBX = PROJ / "Exports" / "SnowFlower" / "v4" / f"{MESH}.fbx"
SIDECAR = PROJ / "Exports" / "SnowFlower" / "v4" / f"{MESH}.sockets.json"
TEXTURE_DIR = PROJ / "Exports" / "SnowFlower" / "v4" / "Textures"
#: the v4 sword is imported beside the sheath (its own sidecar) for the in-engine Holster gate
SWORD_MESH = "SM_SnowFlower"
SWORD_FBX = PROJ / "Exports" / "SnowFlower" / "v4" / "SM_SnowFlower.fbx"
SWORD_SIDECAR = PROJ / "Exports" / "SnowFlower" / "v4" / "SM_SnowFlower.sockets.json"
SWORD_ASSET = f"{DEST}/{SWORD_MESH}"
ASSET = f"{DEST}/{MESH}"
TEXTURE_DEST = f"{DEST}/Textures"

SIDECAR_PAYLOAD = json.loads(SIDECAR.read_text(encoding="utf-8"))
EXPECTED_SCREEN_SIZES = SIDECAR_PAYLOAD.get("lod_screen_sizes")
EXPECTED_SOCKETS = {r["socket"]: r for r in SIDECAR_PAYLOAD["sockets"]}
BLENDER_LOD_TRIANGLES = REPORT["lod_triangles"]
EXPECTED_SIZE_CM = [v / 10.0 for v in REPORT["size_mm"]]
EXPECTED_RADIUS_CM = REPORT["bounds_radius_mm"] / 10.0
#: three hulls (throat + upper body, body, chape)
EXPECTED_HULLS = len(REPORT["collision"]["hulls"])

_counts_path = HERE / "blender_fbx_counts.json"
FBX_LOD_TRIANGLES = None
if _counts_path.is_file():
    _counts = json.loads(_counts_path.read_text(encoding="utf-8"))
    FBX_LOD_TRIANGLES = [_counts["nodes"][f"{MESH}_LOD{i}"]["triangles"] for i in range(3)]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _angle_close(a, b, tol=1e-2):
    return abs((float(a) - float(b) + 180.0) % 360.0 - 180.0) < tol


def vec(v, nd=4):
    return [round(v.x, nd), round(v.y, nd), round(v.z, nd)]


def safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:                                    # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"[:200]} if default is None else default


def subsystem():
    try:
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:                                           # noqa: BLE001
        sub = None
    if sub is None:
        sub = unreal.new_object(unreal.StaticMeshEditorSubsystem)
    return sub


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
    info["auto_compute_lod_screen_size"] = safe(
        lambda: bool(mesh.get_editor_property("auto_compute_lod_screen_size")))
    builds = []
    for i in range(n):
        def read(i=i):
            bs = sub.get_lod_build_settings(mesh, i)
            return {k: bs.get_editor_property(k) for k in (
                "generate_lightmap_u_vs", "src_lightmap_index", "dst_lightmap_index",
                "recompute_normals", "recompute_tangents", "use_mikk_t_space", "remove_degenerates")}
        builds.append(safe(read))
    info["lod_build_settings"] = builds
    info["light_map_coordinate_index"] = safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index")))
    info["nanite_enabled"] = safe(
        lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")))
    body = mesh.get_editor_property("body_setup")
    agg = body.get_editor_property("agg_geom")
    info["convex_hulls"] = len(agg.get_editor_property("convex_elems"))
    info["other_collision_elems"] = {k: safe(lambda k=k: len(agg.get_editor_property(k)), default=-1)
                                     for k in ("box_elems", "sphere_elems", "sphyl_elems",
                                               "tapered_capsule_elems")}
    try:
        info["convex_hull_vertex_counts"] = [len(e.get_editor_property("vertex_data"))
                                             for e in agg.get_editor_property("convex_elems")]
    except Exception as exc:                                    # noqa: BLE001
        info["convex_hull_vertex_counts"] = f"<{type(exc).__name__}: {exc}>"[:120]
    box = mesh.get_bounding_box()
    info["bounds_min_cm"] = vec(box.min)
    info["bounds_max_cm"] = vec(box.max)
    info["size_cm"] = [round(box.max.x - box.min.x, 4), round(box.max.y - box.min.y, 4),
                       round(box.max.z - box.min.z, 4)]
    info["bounds_sphere_radius_cm"] = safe(lambda: round(float(mesh.get_bounds().sphere_radius), 5))
    info["material_slots"] = [str(s.material_slot_name) for s in mesh.get_editor_property("static_materials")]
    comp = unreal.new_object(unreal.StaticMeshComponent)
    comp.set_static_mesh(mesh)
    sockets, raw = [], []
    for name in comp.get_all_socket_names():
        t = comp.get_socket_transform(str(name), unreal.RelativeTransformSpace.RTS_COMPONENT)
        e = t.rotation.euler()
        sockets.append({"name": str(name), "location_cm": vec(t.translation),
                        "rpy": [round(e.x, 3), round(e.y, 3), round(e.z, 3)], "scale": vec(t.scale3d)})
        s = mesh.find_socket(name)
        raw.append({"name": str(name), "found": s is not None,
                    "outer": (s.get_outer().get_path_name() if (s and s.get_outer()) else None),
                    "relative_scale": vec(s.get_editor_property("relative_scale")) if s else None})
    info["sockets"] = sorted(sockets, key=lambda d: d["name"])
    info["socket_array"] = sorted(raw, key=lambda d: d["name"])
    return info


def lod0_positions_cm(mesh):
    desc = mesh.get_static_mesh_description(0)
    out = []

    def make_id(i):
        for field in ("id_value", "value"):
            try:
                vid = unreal.VertexID()
                vid.set_editor_property(field, i)
                return vid
            except Exception:                               # noqa: BLE001
                pass
        return unreal.VertexID(i)
    for i in range(desc.get_vertex_count()):
        p = desc.get_vertex_position(make_id(i))
        out.append((p.x, p.y, p.z))
    return out


def hull_planes(points):
    """Supporting planes of a convex point set (brute force over triples; 32 points)."""
    planes = []
    pts = [tuple(p) for p in points]
    for a, b, c in itertools.combinations(range(len(pts)), 3):
        A, B, C = pts[a], pts[b], pts[c]
        u = (B[0] - A[0], B[1] - A[1], B[2] - A[2])
        v = (C[0] - A[0], C[1] - A[1], C[2] - A[2])
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        L = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        if L < 1e-9:
            continue
        n = (n[0] / L, n[1] / L, n[2] / L)
        d = n[0] * A[0] + n[1] * A[1] + n[2] * A[2]
        side = [n[0] * p[0] + n[1] * p[1] + n[2] * p[2] - d for p in pts]
        if max(side) <= 1e-6:
            planes.append((n, d))
        elif min(side) >= -1e-6:
            planes.append(((-n[0], -n[1], -n[2]), -d))
    return planes


def gates(info):
    n = info["num_lods"]
    tri_delta = [a - b for a, b in zip(info["lod_triangles"], BLENDER_LOD_TRIANGLES)]
    fbx_agrees = (FBX_LOD_TRIANGLES is None) or (FBX_LOD_TRIANGLES == BLENDER_LOD_TRIANGLES)
    size_ok = all(abs(a - e) < 2e-3 for a, e in zip(info["size_cm"], EXPECTED_SIZE_CM))
    raw_by_name = {r["name"]: r for r in info.get("socket_array", [])}
    socket_detail = {}
    for s in info["sockets"]:
        exp = EXPECTED_SOCKETS.get(s["name"])
        raw = raw_by_name.get(s["name"]) or {}
        socket_detail[s["name"]] = bool(
            exp is not None
            and all(abs(a - e) < 1e-3 for a, e in zip(s["location_cm"], exp["location_cm"]))
            and _angle_close(s["rpy"][2], exp["rotation_deg"]["yaw"])
            and _angle_close(s["rpy"][1], exp["rotation_deg"]["pitch"])
            and _angle_close(s["rpy"][0], exp["rotation_deg"]["roll"])
            and s["scale"] == [1.0, 1.0, 1.0]
            and raw.get("relative_scale") == [1.0, 1.0, 1.0]
            and (raw.get("outer") or "").startswith(ASSET))
    sockets_ok = (set(socket_detail) == set(EXPECTED_SOCKETS) and all(socket_detail.values()))
    builds = [b for b in info["lod_build_settings"] if isinstance(b, dict) and "error" not in b]
    lightmap_ok = (info["light_map_coordinate_index"] == 1 and len(builds) == n
                   and all(b["generate_lightmap_u_vs"] and b["src_lightmap_index"] == 0
                           and b["dst_lightmap_index"] == 1 for b in builds))
    screen = info["lod_screen_sizes"]
    screen_ok = (isinstance(screen, list) and len(screen) == 3
                 and all(abs(a - e) < 1e-6 for a, e in zip(screen, EXPECTED_SCREEN_SIZES))
                 and EXPECTED_SCREEN_SIZES == REPORT["lod_screen_sizes"]
                 and info.get("auto_compute_lod_screen_size") is not True)
    radius = info.get("bounds_sphere_radius_cm")
    radius_ok = isinstance(radius, float) and abs(radius - EXPECTED_RADIUS_CM) <= 0.05
    hulls_ok = (info["convex_hulls"] == EXPECTED_HULLS
                and all(v == 0 for k, v in info["other_collision_elems"].items() if k != "tapered_capsule_elems")
                and info["other_collision_elems"].get("tapered_capsule_elems", 0) in (0, -1))
    out = {
        "1_three_lods_triangles_match_blender_and_the_fbx": n == 3 and tri_delta == [0, 0, 0] and fbx_agrees,
        "2_convex_hull_count_as_shipped": hulls_ok,
        "3_sockets_at_scale_1_outered_to_the_asset": sockets_ok,
        "4_bounds_cm_match_the_measured_mesh": size_ok,
        "5_screen_sizes_applied_from_the_sidecar": screen_ok,
        "5b_bounds_sphere_radius_is_the_one_the_screen_sizes_used": radius_ok,
        "6_lightmap_coordinate_index_1_generated_on_every_lod": lightmap_ok,
        "7_two_material_slots_lacquer_silver": info["material_slots"] == REPORT["material_slots"],
        "8_nanite_off": info.get("nanite_enabled") is False,
    }
    detail = {"triangle_delta": tri_delta, "blender_report_lod_triangles": BLENDER_LOD_TRIANGLES,
              "blender_fbx_reimport_lod_triangles": FBX_LOD_TRIANGLES,
              "expected_size_cm": EXPECTED_SIZE_CM, "socket_detail": socket_detail,
              "expected_screen_sizes": EXPECTED_SCREEN_SIZES,
              "bounds_sphere_radius_cm": radius, "expected_radius_cm": round(EXPECTED_RADIUS_CM, 5),
              "convex_hull_vertex_counts": info.get("convex_hull_vertex_counts")}
    return out, detail
