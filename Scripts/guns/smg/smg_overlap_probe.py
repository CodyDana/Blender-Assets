"""Development aid: where two parts' triangles overlap (frame M, mm), optionally with the first part posed.
Inside Blender:  blender -b SMG01.blend --factory-startup --python smg_overlap_probe.py -- a b [--move dx,dy,dz]
                 [--rot px,py,pz,ax,ay,az,deg]"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smg_common import GRIP  # noqa: E402
import bpy  # noqa: E402
from gunlib import fit as F  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
a, b = argv[0], argv[1]
G = F.geom([bpy.data.objects[a], bpy.data.objects[b]])
Va, Ta = G[a]
M = np.eye(4)
if "--move" in argv:
    M = F.trans_matrix((1, 0, 0), 0.0)
    M[:3, 3] = [float(v) for v in argv[argv.index("--move") + 1].split(",")]
if "--rot" in argv:
    v = [float(x) for x in argv[argv.index("--rot") + 1].split(",")]
    M = F.rot_matrix(np.array(v[:3]) - GRIP, v[3:6], v[6]) @ M
Va = F.apply(M, Va)
ta, tb = F.tree(Va, Ta), F.tree(*G[b])
pairs = ta.overlap(tb)
print("OVERLAP", a, b, len(pairs))
C = np.array([Va[Ta[i]].mean(0) for i, _ in pairs]) + GRIP if pairs else np.zeros((0, 3))
if len(C):
    print("  bbox M", C.min(0).round(2), C.max(0).round(2))
    for c in C[:: max(1, len(C) // 12)][:12]:
        print("   ", c.round(2))
