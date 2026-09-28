"""Shared helpers for UnrealCheck5 (runs inside the UE 5.8.2 pythonscript commandlet).

Independent verifier for the eight-point pack build, run in the UnrealTest project
(legacy FBX importer, Interchange.FeatureFlags.Import.FBX=0) into /Game/ShurikenCheck5
so the earlier ShurikenCheck/ShurikenCheck2 evidence stays intact. Adapted from
UnrealCheck2/pass1_import.py + pass2_reload.py; adds the lightmap, UV channel, build
settings, Nanite, section and raw socket-array reads that the earlier checks lacked.

Expectations are the SPEC figures (study 2.1/2.2 + study 4), not only the build report,
so a report that drifted from the spec cannot pass itself.
"""
import json
import os
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck5"
DEST = "/Game/ShurikenCheck5/Verify"  # /Game/ShurikenCheck5/SM_Shuriken_EightPoint is an aborted first try (no sidecar)
FORM = os.environ.get("SHURIKEN_FORM", "eight_point")
REPORT = json.loads((PROJ / "WorkFiles" / "shuriken" / f"{FORM}_report.json").read_text(encoding="utf-8"))
MESH = REPORT["asset"]
FBX = PROJ / "Exports" / "Shuriken" / f"{MESH}.fbx"
SIDECAR = PROJ / "Exports" / "Shuriken" / f"{MESH}.sockets.json"
ASSET = f"{DEST}/{MESH}"

# Spec expectations, typed in from the task/study, then cross-checked against the report.
SPEC = {
    "eight_point": {"size_cm": [10.0, 10.0, 0.25], "lod_bands": [(1200, 2500), (500, 900), (120, 250)]},
    "four_point": {"size_cm": [9.7, 9.7, 0.3], "lod_bands": None},
}[FORM]
EXPECTED_SCREEN_SIZES = [1.0, 0.5, 0.25]  # study 4
BLENDER_LOD_TRIANGLES = REPORT["lod_triangles"]
BLENDER_FBX_COUNTS = json.loads((HERE / "blender_fbx_counts.json").read_text(encoding="utf-8"))["forms"][FORM]
FBX_LOD_TRIANGLES = [BLENDER_FBX_COUNTS["nodes"][f"{MESH}_LOD{i}"]["triangles"] for i in range(3)]
SIDECAR_PAYLOAD = json.loads(SIDECAR.read_text(encoding="utf-8"))
EXPECTED_SOCKETS = {r["socket"]: r for r in SIDECAR_PAYLOAD["sockets"]}


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
    # Source (mesh description) UV channels: the generated lightmap channel lives in the built
    # render data, not here, so 1 is expected with Generate Lightmap UVs ON.
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
    # StaticMesh.Sockets is protected from Python in 5.8.2; read each socket object via find_socket.
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
    """The seven requested gates (log gate is added by the runner from the captured log)."""
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
    # LightMapCoordinateIndex survives UStaticMesh::EnforceLightmapRestrictions (clamped to the
    # built render data's UV count - 1) only if every built LOD has a UV1; pass3 exports the
    # render data and counts the channels directly.
    lightmap_ok = (info["light_map_coordinate_index"] == 1
                   and all(isinstance(c, int) and c >= 1 for c in info["lod_source_uv_channels"])
                   and len(lm_builds) == n
                   and all(b["generate_lightmap_u_vs"] and b["src_lightmap_index"] == 0
                           and b["dst_lightmap_index"] == 1 for b in lm_builds))
    auto_ss = info.get("auto_compute_lod_screen_size")
    out = {
        "1_lod_count_and_triangles_delta_0": n == 3 and tri_delta == [0, 0, 0]
        and BLENDER_LOD_TRIANGLES == FBX_LOD_TRIANGLES,
        "2_exactly_one_convex_hull": info["convex_hulls"] == 1
        and all(v == 0 for k, v in info["other_collision_elems"].items() if k != "tapered_capsule_elems")
        and info["other_collision_elems"].get("tapered_capsule_elems", 0) in (0, -1),
        "3_grip_trail_scale_1_sane_cm": sockets_ok and raw_ok,
        "4_bounds_cm": size_ok,
        "5_screen_sizes_from_sidecar": info["lod_screen_sizes"] == EXPECTED_SCREEN_SIZES
        and SIDECAR_PAYLOAD.get("lod_screen_sizes") == EXPECTED_SCREEN_SIZES
        and auto_ss is not True,
        "6_lightmap_coordinate_index_1": lightmap_ok,
    }
    detail = {"triangle_delta": tri_delta, "blender_report_lod_triangles": BLENDER_LOD_TRIANGLES,
              "blender_fbx_reimport_lod_triangles": FBX_LOD_TRIANGLES, "expected_size_cm": SPEC["size_cm"],
              "socket_detail": socket_detail, "raw_socket_array_scale_1_and_outered_to_asset": raw_ok,
              "expected_screen_sizes": EXPECTED_SCREEN_SIZES,
              "sidecar_screen_sizes": SIDECAR_PAYLOAD.get("lod_screen_sizes")}
    if SPEC["lod_bands"]:
        detail["lod_bands_ok"] = [lo <= t <= hi for t, (lo, hi) in zip(info["lod_triangles"], SPEC["lod_bands"])]
    return out, detail
