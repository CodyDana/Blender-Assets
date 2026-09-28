#!/usr/bin/env python
"""Re-import the SHIPPED FBX in a fresh Blender and count what is really in the file.

The build reports the triangle counts of the objects that were in its scene.  This reads
the bytes that left, which is a different claim, and the Unreal gate requires the two to
agree before it will look at the engine's numbers at all.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python WorkFiles/paperbomb/UnrealCheck/blender_fbx_counts.py
"""
import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealCheck"
FBX = PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.fbx"
OUT = HERE / "blender_fbx_counts.json"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX), automatic_bone_orientation=True)

    nodes = {}
    for obj in bpy.data.objects:
        entry = {"type": obj.type,
                 "parent": obj.parent.name if obj.parent else None,
                 "location_m": [round(v, 8) for v in obj.location],
                 "scale": [round(v, 8) for v in obj.scale]}
        if obj.type == "MESH":
            mesh = obj.data
            mesh.calc_loop_triangles()
            co = np.empty(len(mesh.vertices) * 3, np.float64)
            mesh.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3) * 1000.0
            bm = bmesh.new()
            bm.from_mesh(mesh)
            try:
                edge_use = {}
                for face in bm.faces:
                    for edge in face.edges:
                        edge_use[edge.index] = edge_use.get(edge.index, 0) + 1
                hist = {}
                for v in edge_use.values():
                    hist[str(v)] = hist.get(str(v), 0) + 1
            finally:
                bm.free()
            entry.update({
                "triangles": len(mesh.loop_triangles),
                "polygons": len(mesh.polygons),
                "vertices": len(mesh.vertices),
                "uv_layers": [layer.name for layer in mesh.uv_layers],
                "materials": [m.name if m else None for m in mesh.materials],
                "extents_mm": {"min": [round(float(x), 4) for x in co.min(axis=0)],
                               "max": [round(float(x), 4) for x in co.max(axis=0)],
                               "size": [round(float(x), 4) for x in np.ptp(co, axis=0)]},
                "edge_use_histogram": hist,
            })
            if mesh.uv_layers:
                uv = np.empty(len(mesh.loops) * 2, np.float64)
                mesh.uv_layers[0].data.foreach_get("uv", uv)
                uv = uv.reshape(-1, 2)
                entry["uv0_range"] = [round(float(uv.min()), 6), round(float(uv.max()), 6)]
        nodes[obj.name] = entry

    report = {
        "fbx": str(FBX), "sha256": sha256(FBX), "bytes": FBX.stat().st_size,
        "blender": bpy.app.version_string,
        "objects": len(bpy.data.objects),
        "nodes": nodes,
        "note": ("the FBX importer re-creates the LodGroup's children as plain objects; "
                 "SOCKET_ nodes are absent by design (export_fbx drops them from a "
                 "LodGroup file and writes the .sockets.json sidecar instead)"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("[fbx_counts] ->", OUT)
    for name, entry in sorted(nodes.items()):
        if entry["type"] == "MESH":
            print(f"  {name:32s} {entry['triangles']:5d} tris  {entry['vertices']:5d} verts  "
                  f"uv {entry.get('uv0_range')}")
        else:
            print(f"  {name:32s} {entry['type']}")


main()
