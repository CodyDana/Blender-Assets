"""SR01 W4b K1 (headless Blender, fresh process, on EXPORTED bytes): how the chassis-slot edges are finished.

    blender -b --factory-startup --python Scripts/guns/sniper/sr_closeup_edges.py -- --fbx A.fbx[,B.fbx] --out K1.json

For every FBX: the LOD0 mesh's faces on the M_SR01_Chassis slot (chassis, butt, pad plate, riser, grip), welded at
1 um; every manifold edge's dihedral. A machined / moulded round shows as a run of 10-40 deg edges whose shading is
smooth; a raw crease is one edge > 60 deg. Reports the total length (mm) of hard creases (> 60 deg, convex and
concave), of round segments (10-40 deg), and their ratio, plus the fraction of the round segments shaded smooth
(both faces share the vertex normals at the edge, i.e. no split).
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d=None):
    return argv[argv.index(n) + 1] if n in argv else d


def measure(fbx):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx)
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and "LOD" not in o.name.upper().split("_")[-1]
              and not o.name.upper().startswith("UCX")]
    meshes = sorted(meshes, key=lambda o: -len(o.data.polygons))[:1]
    out = {"mesh": meshes[0].name if meshes else None}
    if not meshes:
        return out
    ob = meshes[0]
    slots = [i for i, m in enumerate(ob.data.materials) if m and "Chassis" in m.name]
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    sc = max(ob.matrix_world.to_scale()) * 1000.0           # mesh units -> mm
    split_edges = {e.index for e in bm.edges if not e.smooth}
    keep = [f for f in bm.faces if f.material_index in slots]
    drop = [f for f in bm.faces if f.material_index not in slots]
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6 / max(sc / 1000.0, 1e-9))
    hard = rnd = rnd_smooth = 0.0
    me_norm = None
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        L = e.calc_length() * sc
        a = math.degrees(e.calc_face_angle(0.0))
        if a > 60.0:
            hard += L
        elif 10.0 <= a <= 40.0:
            rnd += L
            if e.smooth:
                rnd_smooth += L
    out.update({"faces_chassis_slot": len(keep), "hard_crease_mm": round(hard, 1), "round_segment_mm": round(rnd, 1),
                "round_to_hard": round(rnd / max(hard, 1e-6), 3),
                "round_smooth_fraction": round(rnd_smooth / max(rnd, 1e-6), 3)})
    bm.free()
    return out


res = {}
for f in arg("--fbx", "").split(","):
    if f:
        res[Path(f).parent.name + "/" + Path(f).name] = measure(f)
        print("[SR01-K1]", f, json.dumps(res[Path(f).parent.name + "/" + Path(f).name]))
Path(arg("--out")).write_text(json.dumps(res, indent=1))
print("[SR01-K1] DONE")
