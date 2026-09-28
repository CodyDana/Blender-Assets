"""Pass 2 (UnrealCheck4, form-parameterised): reload the SAVED asset in a FRESH process and re-read it.

An in-process query cannot tell a persisted socket (or screen size) from a transient one,
so the gate is what a second commandlet sees. Form from SHURIKEN_FORM (default
eight_point); expectations come from WorkFiles/shuriken/<form>_report.json (Blender LOD
counts, measured across/thickness, sidecar socket records). Writes <form>_pass2.json.
"""
import json
import os
import sys
import traceback
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck4"
FORM = os.environ.get("SHURIKEN_FORM", "eight_point")
REPORT = json.loads((PROJ / "WorkFiles" / "shuriken" / f"{FORM}_report.json").read_text(encoding="utf-8"))
MESH = REPORT["asset"]
ASSET = f"/Game/ShurikenCheck4/{MESH}"
BLENDER_LOD_TRIANGLES = REPORT["lod_triangles"]
MEASURED = REPORT["measured"]
EXPECTED_SIZE_CM = [round(MEASURED["across_mm"] / 10.0, 4), round(MEASURED["across_y_mm"] / 10.0, 4),
                    round(MEASURED["thickness_mm"] / 10.0, 4)]
EXPECTED_SOCKETS = {r["socket"]: r for r in REPORT["socket_records"]}
OUT = HERE / f"{FORM}_pass2.json"
sys.path.insert(0, str(PROJ / "Scripts"))
from pipeline.ue_import_sockets import _static_mesh_editor_subsystem  # noqa: E402


def vec(v):
    return [round(v.x, 4), round(v.y, 4), round(v.z, 4)]


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "form": FORM, "asset": ASSET}
    try:
        mesh = unreal.load_asset(ASSET)
        n = mesh.get_num_lods()
        report["num_lods"] = n
        report["lod_triangles"] = [mesh.get_num_triangles(i) for i in range(n)]
        report["lod_vertices"] = [mesh.get_num_vertices(i) for i in range(n)]
        report["blender_lod_triangles"] = BLENDER_LOD_TRIANGLES
        report["triangle_delta"] = [a - b for a, b in zip(report["lod_triangles"], BLENDER_LOD_TRIANGLES)]
        sub = _static_mesh_editor_subsystem()
        report["lod_screen_sizes"] = [round(float(v), 6) for v in sub.get_lod_screen_sizes(mesh)] if sub else None
        report["expected_screen_sizes"] = [1.0, 0.5, 0.25]
        agg = mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
        report["convex_hulls"] = len(agg.get_editor_property("convex_elems"))
        b = mesh.get_bounding_box()
        report["size_cm"] = [round(b.max.x - b.min.x, 4), round(b.max.y - b.min.y, 4),
                             round(b.max.z - b.min.z, 4)]
        report["expected_size_cm"] = EXPECTED_SIZE_CM
        comp = unreal.new_object(unreal.StaticMeshComponent)
        comp.set_static_mesh(mesh)
        report["sockets"] = []
        for name in comp.get_all_socket_names():
            t = comp.get_socket_transform(str(name), unreal.RelativeTransformSpace.RTS_COMPONENT)
            e = t.rotation.euler()
            report["sockets"].append({"name": str(name), "location_cm": vec(t.translation),
                                      "rpy": [round(e.x, 3), round(e.y, 3), round(e.z, 3)],
                                      "scale": vec(t.scale3d)})
        report["expected_sockets"] = {k: {"location_cm": v["location_cm"], "yaw": v["rotation_deg"]["yaw"]}
                                      for k, v in EXPECTED_SOCKETS.items()}
        report["material_slots"] = [str(s.material_slot_name)
                                    for s in mesh.get_editor_property("static_materials")]
        socket_ok = len(report["sockets"]) == len(EXPECTED_SOCKETS) and all(
            s["name"] in EXPECTED_SOCKETS
            and all(abs(a - e) < 1e-3 for a, e in zip(s["location_cm"], EXPECTED_SOCKETS[s["name"]]["location_cm"]))
            and abs(s["rpy"][2] - EXPECTED_SOCKETS[s["name"]]["rotation_deg"]["yaw"]) < 1e-3
            and s["scale"] == [1.0, 1.0, 1.0]
            for s in report["sockets"])
        report["gates"] = {
            "triangle_delta_zero": report["triangle_delta"] == [0] * len(BLENDER_LOD_TRIANGLES)
            and n == len(BLENDER_LOD_TRIANGLES),
            "screen_sizes": report["lod_screen_sizes"] == report["expected_screen_sizes"],
            "one_convex_hull": report["convex_hulls"] == 1,
            "size_cm": all(abs(a - e) < 1e-3 for a, e in zip(report["size_cm"], EXPECTED_SIZE_CM)),
            "sockets_match_sidecar_at_scale_1": socket_ok,
        }
        report["passed"] = all(report["gates"].values())
    except Exception:
        report["error"] = traceback.format_exc()
        report["passed"] = False
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("PASS2_DONE " + str(OUT))


main()
