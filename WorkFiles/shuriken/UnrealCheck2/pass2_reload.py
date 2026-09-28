"""Pass 2: reload the SAVED asset in a FRESH process and re-read it.

An in-process query cannot tell a persisted socket (or screen size) from a transient
one, so the gate is what a second commandlet sees. Scratch only.
"""
import json, sys, traceback
from pathlib import Path
import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
OUT = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck2" / "pass2.json"
ASSET = "/Game/ShurikenCheck2/SM_Shuriken_FourPoint"
sys.path.insert(0, str(PROJ / "Scripts"))
from pipeline.ue_import_sockets import _static_mesh_editor_subsystem  # noqa: E402


def vec(v):
    return [round(v.x, 4), round(v.y, 4), round(v.z, 4)]


def main():
    report = {"engine": unreal.SystemLibrary.get_engine_version(), "asset": ASSET}
    try:
        mesh = unreal.load_asset(ASSET)
        n = mesh.get_num_lods()
        report["num_lods"] = n
        report["lod_triangles"] = [mesh.get_num_triangles(i) for i in range(n)]
        report["lod_vertices"] = [mesh.get_num_vertices(i) for i in range(n)]
        report["blender_lod_triangles"] = [1376, 620, 184]
        report["triangle_delta"] = [a - b for a, b in zip(report["lod_triangles"], [1376, 620, 184])]
        sub = _static_mesh_editor_subsystem()
        report["lod_screen_sizes"] = [round(float(v), 6) for v in sub.get_lod_screen_sizes(mesh)] if sub else None
        report["expected_screen_sizes"] = [1.0, 0.5, 0.25]
        agg = mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
        report["convex_hulls"] = len(agg.get_editor_property("convex_elems"))
        b = mesh.get_bounding_box()
        report["size_cm"] = [round(b.max.x - b.min.x, 4), round(b.max.y - b.min.y, 4),
                             round(b.max.z - b.min.z, 4)]
        comp = unreal.new_object(unreal.StaticMeshComponent)
        comp.set_static_mesh(mesh)
        report["sockets"] = []
        for name in comp.get_all_socket_names():
            t = comp.get_socket_transform(str(name), unreal.RelativeTransformSpace.RTS_COMPONENT)
            e = t.rotation.euler()
            report["sockets"].append({"name": str(name), "location_cm": vec(t.translation),
                                      "rpy": [round(e.x, 3), round(e.y, 3), round(e.z, 3)],
                                      "scale": vec(t.scale3d)})
        report["material_slots"] = [str(s.material_slot_name)
                                    for s in mesh.get_editor_property("static_materials")]
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    unreal.log("PASS2_DONE " + str(OUT))


main()
