"""Do the four sockets actually sit on the paper?

The study puts Fuse at (47.4, 0, +0.075) mm and Cord at (78, 0, 0) mm on a FLAT
card; the shipped sidecar has them 1.39 mm lower, which the build attributes to
the crease step.  This checks the claim against the real LOD0 surface: for each
socket, find the nearest point of the shipped LOD0 mesh and report the distance,
and the local surface Z on the socket's own (x, y) column.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealReview"
FBX = PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.fbx"
SIDECAR = PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.sockets.json"
OUT = HERE / "pbr_socket_surface.json"


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    ob = bpy.data.objects["SM_PaperBomb_LOD0"]
    me = ob.data
    mw = ob.matrix_world
    verts = [(mw @ v.co) * 1000.0 for v in me.vertices]          # mm, Blender frame
    polys = [[i for i in p.vertices] for p in me.polygons]
    tree = BVHTree.FromPolygons([tuple(v) for v in verts], polys, all_triangles=False, epsilon=0.0)

    payload = json.loads(SIDECAR.read_text(encoding="utf-8"))
    rep = {"fbx": str(FBX), "units": "mm, ASSET frame (+X top of tag, +Y left of the printed face, +Z out of print)",
           "sockets": {}}
    for rec in payload["sockets"]:
        # sidecar is Unreal cm in the Unreal frame; Blender frame flips Y
        ux, uy, uz = [10.0 * v for v in rec["location_cm"]]      # mm, Unreal frame
        p = Vector((ux, -uy, uz))                                 # mm, Blender frame
        loc, nrm, idx, dist = tree.find_nearest(p)
        col = [v.z for v in verts if abs(v.x - p.x) < 4.0 and abs(v.y - p.y) < 4.0]
        rep["sockets"][rec["socket"]] = {
            "sidecar_location_unreal_cm": rec["location_cm"],
            "asset_frame_mm": [round(ux, 4), round(uy, 4), round(uz, 4)],
            "distance_to_LOD0_surface_mm": round(float(dist), 4) if dist is not None else None,
            "nearest_surface_point_mm": [round(loc.x, 4), round(-loc.y, 4), round(loc.z, 4)] if loc else None,
            "local_surface_z_mm_within_4mm": [round(min(col), 4), round(max(col), 4)] if col else None,
            "rotation_deg": rec["rotation_deg"],
        }
    half_thickness = 0.075
    rep["gate_all_sockets_within_0_2mm_of_paper"] = all(
        (s["distance_to_LOD0_surface_mm"] or 9.9) <= half_thickness + 0.12 for s in rep["sockets"].values())
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=2))


main()
