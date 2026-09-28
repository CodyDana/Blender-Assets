"""Shared helpers for UnrealCheck6 (runs inside the UE 5.8.2 pythonscript commandlet).

Maintenance-pass verification of the rebuilt pack (library 3.2). Adapted from the verifier's
UnrealCheck5 (uc5_common.py), with three changes:
  * it runs in the shuriken-only WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject
    (legacy FBX importer) into /Game/ShurikenCheck6/Verify, not in the JinMuWon-named UnrealTest project;
  * the expected LOD screen sizes are the pack's 1.0 / 0.10 / 0.035, read from the sidecar and
    cross-checked against the build report and against the pack constant;
  * pass 1 records the SHA-256 of the exact FBX and sidecar it imported, so the evidence is tied to
    those bytes (attach_engine_check.py compares them with the build report's export_sha256).

Expectations are the SPEC figures (study 2.1/2.2/2.3 + study 4), not only the build report, so a report
that drifted from the spec cannot pass itself.

Parameterized per form (senban build, library 3.3): FORM_SPECS holds each form's study size and its
expected LOD screen sizes, computed here from the study figures - the pack's 1.0 / 0.10 / 0.035 for a
~50 mm star, scaled by bounding radius / 50 mm for a form of another size (study 4, amended
2026-09-17), which is what the build must have written into the sidecar.  A new form adds one entry.
"""
import math
import hashlib
import json
import os
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck6"
DEST = "/Game/ShurikenCheck6/Verify"
FORM = os.environ.get("SHURIKEN_FORM", "eight_point")
REPORT = json.loads((PROJ / "WorkFiles" / "shuriken" / f"{FORM}_report.json").read_text(encoding="utf-8"))
MESH = REPORT["asset"]
FBX = PROJ / "Exports" / "Shuriken" / f"{MESH}.fbx"
SIDECAR = PROJ / "Exports" / "Shuriken" / f"{MESH}.sockets.json"
ASSET = f"{DEST}/{MESH}"

PACK_SCREEN_SIZES = [1.0, 0.1, 0.035]               # for a star of tip radius ~50 mm


def _scaled_screen_sizes(radius_mm, reference_mm=50.0):
    return [1.0] + [round(s * radius_mm / reference_mm, 4) for s in PACK_SCREEN_SIZES[1:]]


_SENBAN_SIDE_MM = 76.2                                # study 2.3: the [17] pair, a 76.2 mm square
FORM_SPECS = {
    "eight_point": {"size_cm": [10.0, 10.0, 0.25],    # study 2.2: 100 mm, 2.5 mm
                    "screen_sizes": PACK_SCREEN_SIZES,
                    "lod_bands": [(1200, 2500), (500, 900), (120, 250)]},
    "four_point": {"size_cm": [9.7, 9.7, 0.3],        # study 2.1: 97 mm, 3.0 mm
                   "screen_sizes": PACK_SCREEN_SIZES,
                   "lod_bands": [(1200, 2500), (500, 900), (120, 250)]},
    "square_plate": {"size_cm": [round(_SENBAN_SIDE_MM * math.sqrt(2.0) / 10.0, 6)] * 2 + [0.19],   # 107.763 mm, 1.9 mm
                     "screen_sizes": _scaled_screen_sizes(_SENBAN_SIDE_MM / math.sqrt(2.0)),   # corner radius 53.88 mm
                     "lod_bands": [(1200, 2500), (500, 900), (0, 250)]},   # plate: no floor at LOD2
}
SPEC = FORM_SPECS[FORM]
LOD_BANDS = SPEC["lod_bands"]
BLENDER_LOD_TRIANGLES = REPORT["lod_triangles"]
BLENDER_FBX_COUNTS = json.loads((HERE / "blender_fbx_counts.json").read_text(encoding="utf-8"))["forms"][FORM]
FBX_LOD_TRIANGLES = [BLENDER_FBX_COUNTS["nodes"][f"{MESH}_LOD{i}"]["triangles"] for i in range(3)]
SIDECAR_PAYLOAD = json.loads(SIDECAR.read_text(encoding="utf-8"))
EXPECTED_SCREEN_SIZES = SIDECAR_PAYLOAD.get("lod_screen_sizes")
EXPECTED_SOCKETS = {r["socket"]: r for r in SIDECAR_PAYLOAD["sockets"]}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def vec(v, nd=4):
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


def inspect(mesh):
    """Everything the gates need, read from a loaded StaticMesh."""
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
                "generate_lightmap_u_vs", "src_lightmap_index", "dst_lightmap_index", "min_lightmap_resolution",
                "recompute_normals", "recompute_tangents", "use_mikk_t_space", "remove_degenerates")}
        builds.append(safe(read))
    info["lod_build_settings"] = builds
    info["light_map_coordinate_index"] = safe(lambda: int(mesh.get_editor_property("light_map_coordinate_index")))
    info["light_map_resolution"] = safe(lambda: int(mesh.get_editor_property("light_map_resolution")))
    info["nanite_enabled"] = safe(lambda: bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")))
    body = mesh.get_editor_property("body_setup")
    agg = body.get_editor_property("agg_geom")
    info["convex_hulls"] = len(agg.get_editor_property("convex_elems"))
    info["other_collision_elems"] = {k: safe(lambda k=k: len(agg.get_editor_property(k)), default=-1)
                                     for k in ("box_elems", "sphere_elems", "sphyl_elems", "tapered_capsule_elems")}
    info["collision_trace_flag"] = str(body.get_editor_property("collision_trace_flag"))
    b = mesh.get_bounding_box()
    info["bounds_min_cm"] = vec(b.min)
    info["bounds_max_cm"] = vec(b.max)
    info["size_cm"] = [round(b.max.x - b.min.x, 4), round(b.max.y - b.min.y, 4), round(b.max.z - b.min.z, 4)]
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
        info["socket_array"].append({
            "name": str(s.get_editor_property("socket_name")),
            "outer": s.get_outer().get_path_name() if s.get_outer() else None,
            "relative_location": vec(s.get_editor_property("relative_location")),
            "relative_rotation": [round(s.get_editor_property("relative_rotation").roll, 4),
                                  round(s.get_editor_property("relative_rotation").pitch, 4),
                                  round(s.get_editor_property("relative_rotation").yaw, 4)],
            "relative_scale": vec(s.get_editor_property("relative_scale")),
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


def gates(info):
    """Gates 1-6 (gate 7, the zero Warning/Error log lines, is added by attach_engine_check.py)."""
    n = info["num_lods"]
    tri_delta = [a - b for a, b in zip(info["lod_triangles"], BLENDER_LOD_TRIANGLES)]
    size_ok = all(abs(a - e) < 1e-3 for a, e in zip(info["size_cm"], SPEC["size_cm"]))
    sockets_ok = (len(info["sockets"]) == 2 and len(info["socket_array"]) == 2)
    socket_detail = {}
    for s in info["sockets"]:
        exp = EXPECTED_SOCKETS.get(s["name"])
        ok = (exp is not None
              and all(abs(a - e) < 1e-3 for a, e in zip(s["location_cm"], exp["location_cm"]))
              and abs(s["rpy"][2] - exp["rotation_deg"]["yaw"]) < 1e-3
              and abs(s["rpy"][0]) < 1e-3 and abs(s["rpy"][1]) < 1e-3
              and s["scale"] == [1.0, 1.0, 1.0])
        socket_detail[s["name"]] = ok
        sockets_ok = sockets_ok and ok
    sockets_ok = sockets_ok and set(socket_detail) == {"Grip", "Trail"}
    raw_ok = all(r["relative_scale"] == [1.0, 1.0, 1.0] and (r["outer"] or "").startswith(ASSET)
                 for r in info["socket_array"])
    lm_builds = [b for b in info["lod_build_settings"] if isinstance(b, dict) and "error" not in b]
    lightmap_ok = (info["light_map_coordinate_index"] == 1
                   and all(isinstance(c, int) and c >= 1 for c in info["lod_source_uv_channels"])
                   and len(lm_builds) == n
                   and all(b["generate_lightmap_u_vs"] and b["src_lightmap_index"] == 0
                           and b["dst_lightmap_index"] == 1 for b in lm_builds))
    auto_ss = info.get("auto_compute_lod_screen_size")
    screen = info["lod_screen_sizes"]
    screen_ok = (isinstance(screen, list) and len(screen) == 3
                 and all(abs(a - e) < 1e-6 for a, e in zip(screen, EXPECTED_SCREEN_SIZES))
                 and EXPECTED_SCREEN_SIZES == REPORT["lod_screen_sizes"] == SPEC["screen_sizes"]
                 and auto_ss is not True)
    out = {
        "1_lod_count_and_triangles_delta_0": n == 3 and tri_delta == [0, 0, 0]
        and BLENDER_LOD_TRIANGLES == FBX_LOD_TRIANGLES,
        "2_exactly_one_convex_hull": info["convex_hulls"] == 1
        and all(v == 0 for k, v in info["other_collision_elems"].items() if k != "tapered_capsule_elems")
        and info["other_collision_elems"].get("tapered_capsule_elems", 0) in (0, -1),
        "3_grip_trail_scale_1_sane_cm": sockets_ok and raw_ok,
        "4_bounds_cm": size_ok,
        "5_screen_sizes_from_sidecar": screen_ok,
        "6_lightmap_coordinate_index_1": lightmap_ok,
    }
    detail = {"triangle_delta": tri_delta, "blender_report_lod_triangles": BLENDER_LOD_TRIANGLES,
              "blender_fbx_reimport_lod_triangles": FBX_LOD_TRIANGLES, "expected_size_cm": SPEC["size_cm"],
              "socket_detail": socket_detail, "raw_socket_array_scale_1_and_outered_to_asset": raw_ok,
              "expected_screen_sizes": EXPECTED_SCREEN_SIZES, "report_screen_sizes": REPORT["lod_screen_sizes"],
              "spec_screen_sizes": SPEC["screen_sizes"],
              "lod_bands_ok": [lo <= t <= hi for t, (lo, hi) in zip(info["lod_triangles"], LOD_BANDS)]}
    return out, detail
