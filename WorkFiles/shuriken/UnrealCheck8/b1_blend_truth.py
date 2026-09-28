"""UnrealCheck8 (independent import verifier) - Blender-side truth, read from the pack .blend AND the shipped FBX.

Run headless, never saves anything:
  blender.exe -b Assets/Shuriken.blend --factory-startup --python-exit-code 3 --python b1_blend_truth.py

Per form: evaluated triangle / vertex counts of every <mesh>_LODn object in the .blend, the UCX hull
(name keyed to the render NODE, vertex / triangle counts), the SOCKET_ Empties converted with
pipeline.helpers.ue_socket_transform (compared later with the sidecar), UV layers; then the SAME numbers
from a factory-startup re-import of the shipped FBX (a second, independent reading of the exact bytes).
Writes blend_truth.json next to this file.
"""
import hashlib
import json
import sys
from pathlib import Path

import bpy

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck8"
sys.path.insert(0, str(PROJ / "Scripts"))
from pipeline import helpers  # noqa: E402

FORMS = {"four_point": "SM_Shuriken_FourPoint", "eight_point": "SM_Shuriken_EightPoint",
         "square_plate": "SM_Shuriken_SquarePlate", "six_point": "SM_Shuriken_SixPoint",
         "spike": "SM_Shuriken_Spike"}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def counts(ob, depsgraph):
    ev = ob.evaluated_get(depsgraph)
    me = ev.to_mesh()
    try:
        me.calc_loop_triangles()
        return {"triangles": len(me.loop_triangles), "vertices": len(me.vertices), "polygons": len(me.polygons),
                "uv_layers": [uv.name for uv in me.uv_layers]}
    finally:
        ev.to_mesh_clear()


def world_dims_cm(ob):
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return [round((max(p[i] for p in pts) - min(p[i] for p in pts)) * 100.0, 5) for i in range(3)]


def read_scene(mesh):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    rec = {"lods": {}, "hulls": {}, "sockets": {}, "lod_group": None}
    for i in range(8):
        ob = bpy.data.objects.get(f"{mesh}_LOD{i}")
        if ob is None or ob.type != "MESH":
            break
        c = counts(ob, depsgraph)
        c["dimensions_cm"] = world_dims_cm(ob)
        c["parent"] = ob.parent.name if ob.parent else None
        c["parent_fbx_type"] = (ob.parent.get("fbx_type") if ob.parent else None)
        c["material_slots"] = len(ob.material_slots)
        rec["lods"][f"LOD{i}"] = c
    rec["lod_triangles"] = [v["triangles"] for v in rec["lods"].values()]
    for ob in bpy.data.objects:
        if ob.name.startswith("UCX_") and mesh in ob.name and ob.type == "MESH":
            c = counts(ob, depsgraph)
            c["dimensions_cm"] = world_dims_cm(ob)
            c["parent"] = ob.parent.name if ob.parent else None
            c["keyed_to_render_node"] = ob.name == f"UCX_{mesh}_LOD0_00" or ob.name.startswith(f"UCX_{mesh}_LOD0_")
            rec["hulls"][ob.name] = c
        if ob.name.startswith("SOCKET_") and mesh in ob.name:
            t = helpers.ue_socket_transform(ob.matrix_local)
            rec["sockets"][ob.name] = {"type": ob.type, "parent": ob.parent.name if ob.parent else None,
                                       "ue": t}
    return rec


def main():
    out = {"blend": bpy.data.filepath, "blend_sha256": sha256(bpy.data.filepath), "blender": bpy.app.version_string,
           "forms": {}}
    for form, mesh in FORMS.items():
        out["forms"][form] = {"mesh": mesh, "blend": read_scene(mesh)}
    # second reading: the shipped FBX bytes, re-imported into an empty factory scene
    for form, mesh in FORMS.items():
        fbx = PROJ / "Exports" / "Shuriken" / f"{mesh}.fbx"
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(fbx))
        rec = read_scene(mesh)
        rec["fbx_sha256"] = sha256(fbx)
        rec["nodes"] = sorted(o.name for o in bpy.data.objects)
        rec["socket_nodes_in_fbx"] = [o.name for o in bpy.data.objects if o.name.startswith("SOCKET_")]
        out["forms"][form]["fbx"] = rec
    (HERE / "blend_truth.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("UC8_BLEND_TRUTH_DONE")


main()
