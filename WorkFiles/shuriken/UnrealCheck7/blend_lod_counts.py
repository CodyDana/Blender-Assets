"""Blender-side truth for UnrealCheck7, read straight from the pack .blend (not from the FBX).

Opens Assets/Shuriken.blend read-only (headless, factory startup, never saved) and records, per form:
the evaluated triangle count of each LOD object, the UCX hull's vertex/triangle counts and naming
(UCX_<render node>_00), the SOCKET_ Empties with their Blender local locations converted to the sidecar's
Unreal convention (pipeline.helpers.ue_socket_transform), the LOD group, the object dimensions in cm, and the
object custom properties.  The importer verification then compares Unreal's numbers with THESE, not only with
a re-import of the same FBX.  Writes blend_lod_counts.json next to this file.  Run:
  blender.exe -b Assets/Shuriken.blend --factory-startup --python-exit-code 3 --python blend_lod_counts.py
"""
import json
import sys
from pathlib import Path

import bpy

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck7"
sys.path.insert(0, str(PROJ / "Scripts"))
from pipeline import helpers  # noqa: E402

FORMS = {"four_point": "SM_Shuriken_FourPoint", "eight_point": "SM_Shuriken_EightPoint",
         "square_plate": "SM_Shuriken_SquarePlate"}


def tri_count(ob, depsgraph):
    ev = ob.evaluated_get(depsgraph)
    me = ev.to_mesh()
    try:
        me.calc_loop_triangles()
        return len(me.loop_triangles), len(me.vertices), len(me.polygons)
    finally:
        ev.to_mesh_clear()


def main():
    out = {"blend": bpy.data.filepath, "blender": bpy.app.version_string, "forms": {}}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for form, mesh in FORMS.items():
        rec = {"lods": {}, "hulls": {}, "sockets": [], "lod_group": None, "collection": None}
        for coll in bpy.data.collections:
            if any(o.name == f"{mesh}_LOD0" for o in coll.all_objects):
                rec["collection"] = coll.name
        for i in range(8):
            ob = bpy.data.objects.get(f"{mesh}_LOD{i}")
            if ob is None or ob.type != "MESH":
                break
            tris, verts, polys = tri_count(ob, depsgraph)
            rec["lods"][f"LOD{i}"] = {
                "triangles": tris, "vertices": verts, "polygons": polys,
                "modifiers": [m.type for m in ob.modifiers],
                "dimensions_cm": [round(d * 100.0, 5) for d in ob.dimensions],
                "uv_layers": [uv.name for uv in ob.data.uv_layers],
                "material_slots": [s.material.name if s.material else None for s in ob.material_slots],
                "parent": ob.parent.name if ob.parent else None,
                "transform_applied": helpers.transform_is_applied(ob)[0],
                "custom_props": {k: (list(ob[k]) if hasattr(ob[k], "__len__") and not isinstance(ob[k], str) else ob[k])
                                 for k in ob.keys() if not k.startswith("_")},
            }
        rec["lod_triangles"] = [v["triangles"] for v in rec["lods"].values()]
        group = bpy.data.objects.get(f"{mesh}_LodGroup")
        rec["lod_group"] = {"name": group.name, "type": group.type,
                            "children": sorted(c.name for c in group.children)} if group else None
        lod0 = bpy.data.objects.get(f"{mesh}_LOD0")
        if lod0 is not None:
            for child in lod0.children:
                if child.name.startswith("UCX_") and child.type == "MESH":
                    tris, verts, polys = tri_count(child, depsgraph)
                    rec["hulls"][child.name] = {"triangles": tris, "vertices": verts, "polygons": polys,
                                                "keyed_to_render_node": child.name == f"UCX_{lod0.name}_00",
                                                "dimensions_cm": [round(d * 100.0, 5) for d in child.dimensions]}
                elif child.name.startswith("SOCKET_"):
                    s = {"name": child.name, "type": child.type, "is_empty": child.type == "EMPTY",
                         "ue_correction": bool(child.get("ue_socket_correction", False))}
                    try:
                        s["record"] = helpers.socket_record(lod0, child)
                    except Exception as exc:  # noqa: BLE001
                        s["record_error"] = f"{type(exc).__name__}: {exc}"
                    rec["sockets"].append(s)
        out["forms"][form] = rec
    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "blend_lod_counts.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("BLEND_COUNTS_DONE")


main()
