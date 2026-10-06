"""AR-01 G5 at LOD2 and LOD3 (headless Blender; GUN_BUILDING_STUDY 7.2 G5 + finding R5: 0 intersections at LOD0-LOD1,
'< 1 px at LOD2-3'):

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_g5_lods.py

For every intersecting part pair of a coarse LOD (exact triangle-triangle overlap, gunlib.fit), the penetration depth:
the deepest surface sample (0.5 mm spacing) of either part inside the other closed part (nearest-surface normal test),
converted to pixels at that LOD's switch-in distance (gates/game_lod_sizes.json: d = 1.778 r / s at 2560 x 1440, 90 deg
horizontal FOV; 1280 / d(mm) px per mm). Gate: every pair's depth < 1 px. Writes scratch/game/g5_lods.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SCRATCH  # noqa: E402

import numpy as np  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from gunlib import fit as F  # noqa: E402
from gunlib import bl  # noqa: E402

OUT = SCRATCH / "game" / "g5_lods.json"


def _parity(t, p, d, cap=2000.0):
    n, o = 0, Vector(p)
    for _ in range(64):
        h = t.ray_cast(o, d, cap)
        if h[0] is None:
            break
        n += 1
        o = h[0] + d * 1e-4
    return n % 2 == 1


DIRS = [Vector((0.31, 0.53, 0.79)).normalized(), Vector((-0.62, 0.21, -0.75)).normalized(),
        Vector((0.12, -0.91, 0.40)).normalized()]


def depth_inside(samples, V, T, cap=30.0):
    """Deepest sample inside the closed mesh (V, T) (mm): inside by ray parity (2 of 3 rays odd; the nearest-face
    normal test calls points beyond an edge 'inside'), depth = distance to the nearest surface."""
    t = F.tree(V, T)
    lo, hi = V.min(0), V.max(0)
    best = 0.0
    for p in samples:
        if np.any(p < lo) or np.any(p > hi):
            continue
        h = t.find_nearest(Vector(p), cap)
        if h[0] is None or h[3] <= best:
            continue
        if sum(_parity(t, p, d) for d in DIRS) >= 2:
            best = h[3]
    return best


def main():
    sz = json.loads((ROOT / "WorkFiles" / "guns" / "rifle" / "gates" / "game_lod_sizes.json").read_text())
    r_m = sz["bounds_radius_m"]
    sizes = sz["SM_AR01"]
    out = {"rule": "GUN_BUILDING_STUDY 7.2 G5 (R5): intersections allowed at LOD2-3 only below 1 px at the LOD's "
                   "switch-in distance", "lods": {}}
    ok_all = True
    for lv in (2, 3):
        objs = [o for o in bpy.data.collections[f"AR01_LOD{lv}"].objects if o.type == "MESH"]
        G = F.geom(objs)
        d_mm = 1.778 * r_m / sizes[lv] * 1000.0
        px_per_mm = 1280.0 / d_mm
        rows = []
        for r in F.pair_intersections(G):
            a, b = r["a"], r["b"]
            Va, Ta = G[a]
            Vb, Tb = G[b]
            lo = np.maximum(Va.min(0), Vb.min(0)) - 1.0
            hi = np.minimum(Va.max(0), Vb.max(0)) + 1.0
            sa = bl.surface_samples(Va, Ta, 0.5)
            sb = bl.surface_samples(Vb, Tb, 0.5)
            sa = sa[np.all((sa >= lo) & (sa <= hi), axis=1)]
            sb = sb[np.all((sb >= lo) & (sb <= hi), axis=1)]
            dep = max(depth_inside(sa, Vb, Tb), depth_inside(sb, Va, Ta))
            rows.append({"a": a, "b": b, "triangle_pairs": r["intersecting_triangle_pairs"],
                         "depth_mm": round(dep, 3), "depth_px": round(dep * px_per_mm, 3)})
        worst = max([x["depth_px"] for x in rows] or [0.0])
        ok = worst < 1.0
        ok_all &= ok
        out["lods"][f"LOD{lv}"] = {"switch_in_screen_size": sizes[lv], "distance_m": round(d_mm / 1000.0, 3),
                                   "px_per_mm": round(px_per_mm, 4), "intersecting_pairs": len(rows),
                                   "worst_depth_px": worst, "pass": ok,
                                   "pairs": sorted(rows, key=lambda x: -x["depth_px"])}
        print("[G5-lods] LOD%d pairs %d worst %.3f px at %.2f m %s" % (lv, len(rows), worst, d_mm / 1000.0,
                                                                         "PASS" if ok else "FAIL"), flush=True)
    out["pass"] = ok_all
    OUT.write_text(json.dumps(out, indent=1))
    print("[G5-lods] DONE")


main()
