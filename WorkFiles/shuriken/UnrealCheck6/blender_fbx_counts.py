"""Independent Blender-side counts for the UnrealCheck6 import verification.

Re-imports each shipped FBX (Exports/Shuriken) into an empty factory-startup scene and
records, per mesh node: triangle count, vertex count, UV layer names and the bounds in
cm. Also opens nothing else and saves nothing. Writes blender_fbx_counts.json next to
this file. Every form whose FBX exists in Exports/Shuriken is counted (FORMS below, one entry per
pack form). Run:
  blender.exe -b --factory-startup --python-exit-code 3 --python blender_fbx_counts.py
"""
import json
import sys
from pathlib import Path

import bpy

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck6"
# 3.11 (blade section): a run may keep its evidence in its own folder (UC6_OUT); default HERE (unchanged)
import os as _os  # noqa: E402
OUT = Path(_os.environ.get("UC6_OUT") or HERE)
sys.dont_write_bytecode = True   # 3.11: no bytecode caches in the live Scripts tree
FORMS = {"four_point": "SM_Shuriken_FourPoint", "eight_point": "SM_Shuriken_EightPoint",
         "square_plate": "SM_Shuriken_SquarePlate", "six_point": "SM_Shuriken_SixPoint",
         "spike": "SM_Shuriken_Spike", "hooked_cross": "SM_Shuriken_HookedCross", "kunai_plain": "SM_Kunai_Plain"}
FBXS = {form: PROJ / "Exports" / "Shuriken" / f"{mesh}.fbx" for form, mesh in FORMS.items()
        if (PROJ / "Exports" / "Shuriken" / f"{mesh}.fbx").exists()}


def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)


def main():
    out = {"blender": bpy.app.version_string, "forms": {}}
    for form, fbx in FBXS.items():
        clear()
        bpy.ops.import_scene.fbx(filepath=str(fbx))
        rec = {"fbx": str(fbx), "nodes": {}}
        for ob in sorted(bpy.data.objects, key=lambda o: o.name):
            entry = {"type": ob.type, "parent": ob.parent.name if ob.parent else None}
            if ob.type == "MESH":
                me = ob.data
                me.calc_loop_triangles()
                ws = [ob.matrix_world @ v.co for v in me.vertices]
                # the importer applies the FBX unit scale on the object; world coords are metres
                entry.update({
                    "materials": [m.name if m else None for m in me.materials],
                    "triangles": len(me.loop_triangles),
                    "polygons": len(me.polygons),
                    "non_tri_polygons": sum(1 for p in me.polygons if len(p.vertices) != 3),
                    "vertices": len(me.vertices),
                    "uv_layers": [uv.name for uv in me.uv_layers],
                    "size_cm": [round((max(c[i] for c in ws) - min(c[i] for c in ws)) * 100.0, 5)
                                for i in range(3)] if ws else None,
                })
            else:
                entry["custom_props"] = {k: str(ob[k]) for k in ob.keys() if not k.startswith("_")}
            rec["nodes"][ob.name] = entry
        out["forms"][form] = rec
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "blender_fbx_counts.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("BLENDER_COUNTS_DONE")


main()
