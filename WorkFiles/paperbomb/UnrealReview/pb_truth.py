"""Independent Blender truth pass for the PaperBomb Unreal review.

Re-imports the EXACT shipped Exports/PaperBomb/SM_PaperBomb.fbx into an empty
factory-startup scene and records, per node: triangle/vertex counts, UV layers,
bounds in cm, materials.  Also records LOD0 and hull vertex positions in Unreal
cm (the legacy importer's documented conversion: Blender metres (x,y,z) ->
Unreal cm (100x, -100y, 100z)) so the round trip can be compared later, and the
UV0 span of every LOD.

Nothing is written to the project except this script's JSON under
WorkFiles/paperbomb/UnrealReview/.

Run:
  blender.exe -b --factory-startup --python-exit-code 3 --python pb_truth.py
"""
import hashlib
import json
from pathlib import Path

import bpy

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealReview"
FBX = PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.fbx"
SIDECAR = PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.sockets.json"
OUT = HERE / "pb_fbx_truth.json"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)


def main():
    clear()
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    out = {"blender": bpy.app.version_string, "fbx": str(FBX), "fbx_sha256": sha256(FBX),
           "sidecar_sha256": sha256(SIDECAR), "nodes": {}}
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        entry = {"type": ob.type, "parent": ob.parent.name if ob.parent else None}
        if ob.type == "MESH":
            me = ob.data
            me.calc_loop_triangles()
            ws = [ob.matrix_world @ v.co for v in me.vertices]
            entry.update({
                "materials": [m.name if m else None for m in me.materials],
                "triangles": len(me.loop_triangles),
                "polygons": len(me.polygons),
                "non_tri_polygons": sum(1 for p in me.polygons if len(p.vertices) != 3),
                "vertices": len(me.vertices),
                "uv_layers": [uv.name for uv in me.uv_layers],
                "size_cm": [round((max(c[i] for c in ws) - min(c[i] for c in ws)) * 100.0, 5)
                            for i in range(3)] if ws else None,
                "min_cm": [round(min(c[i] for c in ws) * 100.0, 5) for i in range(3)] if ws else None,
                "max_cm": [round(max(c[i] for c in ws) * 100.0, 5) for i in range(3)] if ws else None,
            })
            # Unreal cm in Unreal's frame (the legacy FBX importer's change of basis)
            entry["verts_ue_cm"] = [[round(100.0 * c.x, 6), round(-100.0 * c.y, 6), round(100.0 * c.z, 6)]
                                    for c in ws]
            entry["polys_ue_cm"] = [[[round(100.0 * (ob.matrix_world @ me.vertices[i].co).x, 6),
                                      round(-100.0 * (ob.matrix_world @ me.vertices[i].co).y, 6),
                                      round(100.0 * (ob.matrix_world @ me.vertices[i].co).z, 6)]
                                     for i in p.vertices] for p in me.polygons]
            if me.uv_layers:
                uv = me.uv_layers[0].data
                us = [d.uv[0] for d in uv]
                vs = [d.uv[1] for d in uv]
                entry["uv0_range"] = [round(min(us), 6), round(max(us), 6),
                                      round(min(vs), 6), round(max(vs), 6)]
                # UV0 per loop, keyed by loop index, for the cross-LOD identity check
                entry["uv0_loops"] = [[round(d.uv[0], 7), round(d.uv[1], 7)] for d in uv]
        else:
            entry["custom_props"] = {k: str(ob[k]) for k in ob.keys() if not k.startswith("_")}
            entry["location_cm"] = [round(100.0 * ob.matrix_world.translation.x, 6),
                                    round(-100.0 * ob.matrix_world.translation.y, 6),
                                    round(100.0 * ob.matrix_world.translation.z, 6)]
        out["nodes"][ob.name] = entry
    # whole-scene render-mesh bounds (the LOD0 node only; Unreal's bounds come from LOD0)
    out["materials_in_file"] = sorted(m.name for m in bpy.data.materials)
    out["images_in_file"] = sorted(i.name for i in bpy.data.images)
    HERE.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("PB_TRUTH_DONE " + str(OUT))
    for name, e in out["nodes"].items():
        if e["type"] == "MESH":
            print("  %-34s tris=%-6d verts=%-6d uv=%s size_cm=%s" % (
                name, e["triangles"], e["vertices"], e["uv_layers"], e["size_cm"]))
        else:
            print("  %-34s type=%s loc_cm=%s" % (name, e["type"], e.get("location_cm")))


main()
