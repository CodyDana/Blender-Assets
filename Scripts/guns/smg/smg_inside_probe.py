"""Development aid: surface samples of part A that lie inside part B (ray parity), frame M (mm), with their depth.
Inside Blender:  blender -b SMG01.blend --factory-startup --python smg_inside_probe.py -- a b [--rot px,py,pz,ax,ay,az,deg]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smg_common import GRIP  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from gunlib import fit as F, bl, gateutil as GU  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
a, b = argv[0], argv[1]
G = F.geom([bpy.data.objects[a], bpy.data.objects[b]])
Va, Ta = G[a]
if "--rot" in argv:
    v = [float(x) for x in argv[argv.index("--rot") + 1].split(",")]
    Va = F.apply(F.rot_matrix(np.array(v[:3]) - GRIP, v[3:6], v[6]), Va)
if "--move" in argv:
    Va = Va + np.array([float(x) for x in argv[argv.index("--move") + 1].split(",")])
tb = GU.tree(*G[b])
lo, hi = G[b][0].min(0), G[b][0].max(0)
S = bl.surface_samples(Va, Ta, 0.4)
S = S[np.all((S >= lo) & (S <= hi), axis=1)]
dirs = GU._dirs()
ins = []
for p in S:
    if sum(GU.parity(tb, p, d) for d in dirs) >= 2:
        h = tb.find_nearest(Vector(p), 30.0)
        ins.append((*p, h[3] if h[0] is not None else 0.0))
print("INSIDE", a, "in", b, len(ins), "of", len(S))
if ins:
    I = np.array(ins)
    I[:, :3] += GRIP
    print("  bbox M", I[:, :3].min(0).round(2), I[:, :3].max(0).round(2), "max depth", I[:, 3].max().round(3))
    for r in I[np.argsort(-I[:, 3])][:10]:
        print("   ", r.round(2))
