"""G5 at the coarse LODs (headless Blender; GUN_BUILDING_STUDY 7.2 G5 + finding R5: 0 intersections at LOD0-LOD1,
'< 1 px at LOD2-3'). Promoted from the AR-01's rifle_g5_lods.py (gunlib 0.2.0).

    blender -b <gun>.blend --factory-startup --python <shim> -- [--out json] [--sizes json]

For every intersecting part pair of a coarse LOD (exact triangle-triangle overlap, gunlib.fit), the penetration depth:
the deepest surface sample (0.5 mm spacing) of either part inside the other closed part (ray parity), converted to
pixels at that LOD's switch-in distance (game_lod_sizes.json: d = 1.778 r / s at 2560 x 1440, 90 deg horizontal FOV;
1280 / d(mm) px per mm). Gate: every pair's depth < 1 px.

Config ``cfg.g5_lods``: out (default scratch/game/g5_lods.json), sizes (default gates/game_lod_sizes.json), lods
(default [2, 3]), collection (callable(k) or format string; default cfg.lod_collection).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .. import bl
from .. import fit as F
from .. import gateutil as GU


def depth_inside(samples, V, T, cap=30.0):
    """Deepest sample inside the closed mesh (V, T) (mm)."""
    return GU.depth_inside(samples, F.tree(V, T), V.min(0), V.max(0), cap)


def main(cfg, argv=None):
    import bpy
    argv = GU.argv_after_dashes() if argv is None else argv
    C = cfg.g5_lods
    out_path = Path(GU.opt(argv, "--out") or C.get("out") or cfg.scratch / "game" / "g5_lods.json")
    sz = json.loads(Path(GU.opt(argv, "--sizes") or C.get("sizes") or cfg.gates / "game_lod_sizes.json").read_text())
    r_m = sz["bounds_radius_m"]
    sizes = sz[cfg.twin]
    coll = C.get("collection", cfg.lod_collection)
    out = {"rule": "GUN_BUILDING_STUDY 7.2 G5 (R5): intersections allowed at LOD2-3 only below 1 px at the LOD's "
                   "switch-in distance", "lods": {}}
    ok_all = True
    for lv in C.get("lods", (2, 3)):
        name = coll(lv) if callable(coll) else coll.format(k=lv)
        objs = [o for o in bpy.data.collections[name].objects if o.type == "MESH"]
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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1))
    print("[G5-lods] DONE")
    return out
