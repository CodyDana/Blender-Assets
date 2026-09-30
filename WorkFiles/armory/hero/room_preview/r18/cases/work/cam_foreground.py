"""Ray-cast a camera's frame (1600x900 aspect, 80 x 45 rays) against the assembled room and list what fills it:
per piece, the share of rays whose FIRST hit it is, and its nearest hit distance. Floor/ceiling/walls grouped.
Run: blender -b <blend> --python cam_foreground.py -- <layout.json> <camera name> [loc x,y,z look x,y,z lens]"""
import json, sys, math
from pathlib import Path
from collections import defaultdict
import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
lay = json.loads(Path(a[0]).read_text())
cam = next(c for c in lay["cameras"] if c["name"] == a[1])
if len(a) > 2:
    v = [float(t) for t in a[2].split(",")]
    cam = dict(cam, loc=v[0:3], look_at=v[3:6], lens_mm=v[6])
loc, look = Vector(cam["loc"]), Vector(cam["look_at"])
q = (look - loc).to_track_quat("-Z", "Y")
fx = 36.0 / cam["lens_mm"] / 2; fy = fx * 900 / 1600
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene
NX, NY = 80, 45
stat = defaultdict(lambda: [0, 1e9, 0])   # rays, nearest, rays in the lower third
for j in range(NY):
    for i in range(NX):
        u = (2 * (i + 0.5) / NX - 1) * fx; w = (1 - 2 * (j + 0.5) / NY) * fy
        d = q @ Vector((u, w, -1)).normalized()
        hit, p, n, idx, ob, m = sc.ray_cast(dg, loc, d)
        name = ob.name.split("__")[0] if hit else "(sky)"
        if any(k in name for k in ("Floor_Plank", "Ceiling", "WallLower", "WallUpper", "Rib", "Beam")):
            name = "(floor/ceiling/wall: " + name.split("_")[2] + ")"
        s = stat[name]; s[0] += 1
        if hit: s[1] = min(s[1], (p - loc).length)
        if j >= 2 * NY // 3: s[2] += 1
rows = sorted(stat.items(), key=lambda kv: -kv[1][0])
print("CAMERA", json.dumps(cam))
for k, (n, near, low) in rows[:22]:
    print(f"FG {k:45s} frame {100 * n / (NX * NY):5.1f} %  lower third {100 * low / (NX * NY / 3):5.1f} %  nearest {near:5.2f} m")
