"""Development aid: the closest approach between part A (optionally posed) and part B, frame M (mm): the 8 closest
sample points of A with their distances. Inside Blender:
    blender -b SMG01.blend --factory-startup --python smg_near_probe.py -- a b [--move dx,dy,dz]
            [--rot px,py,pz,ax,ay,az,deg] [--cap 1.0]"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smg_common import GRIP  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from gunlib import fit as F, bl  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
a, b = argv[0], argv[1]
cap = float(argv[argv.index("--cap") + 1]) if "--cap" in argv else 1.0
G = F.geom([bpy.data.objects[a], bpy.data.objects[b]])
Va, Ta = G[a]
M = np.eye(4)
if "--move" in argv:
    M[:3, 3] = [float(v) for v in argv[argv.index("--move") + 1].split(",")]
if "--rot" in argv:
    v = [float(x) for x in argv[argv.index("--rot") + 1].split(",")]
    M = F.rot_matrix(np.array(v[:3]) - GRIP, v[3:6], v[6]) @ M
Va = F.apply(M, Va)
tb = F.tree(*G[b])
S = bl.surface_samples(Va, Ta, 0.2)
res = []
for p in S:
    h = tb.find_nearest(Vector(p), cap)
    if h[0] is not None:
        res.append((h[3], *(np.array(p) + GRIP), *(np.array(h[0]) + GRIP)))
res.sort()
print("NEAR", a, b, len(res))
for r in res[:8]:
    print("   d %.3f  A %s  B %s" % (r[0], np.round(r[1:4], 2), np.round(r[4:7], 2)))
