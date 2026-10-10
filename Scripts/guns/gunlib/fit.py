"""Motion-clearance sweep (gate B3, GUN_BUILDING_STUDY 7.2) and static contact checks (G5) - inside Blender.

For each moving group (the parts on one bone), the group's evaluated triangles are moved along their motion (a
translation along an axis or a rotation about a pivot axis) in steps no larger than the study's rule:
translation <= min(half the row's lower clearance bound, 1 mm); rotation <= min(1 deg, c_min / r_max). At every step
the moved triangles are tested for intersections against every other part (exact triangle-triangle overlap through
mathutils BVH trees). The clearance (minimum distance between the moving group and anything else) is measured on
dense surface samples both ways (moving samples -> fixed surface, nearby fixed samples -> moving surface) at every
clearance step (every step for rotations, every 1 mm for long slides) plus rest and both extremes.
"""
from __future__ import annotations

import math
import time
from typing import Dict, List, Sequence

import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from . import bl


def geom(objs) -> Dict[str, tuple]:
    out = {}
    for o in objs:
        V, T = bl.tris_np(o)          # metres*1000 = mm in frame B (offset 0)
        out[o.name] = (V, T)
    return out


def tree(V_mm, T):
    return BVHTree.FromPolygons([tuple(v) for v in V_mm], [tuple(int(i) for i in t) for t in T], all_triangles=True,
                                epsilon=0.0)


def rot_matrix(pivot, axis, deg):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    th = math.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    R = np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = np.asarray(pivot, float) - R @ np.asarray(pivot, float)
    return M


def trans_matrix(axis, d):
    M = np.eye(4)
    M[:3, 3] = np.asarray(axis, float) / np.linalg.norm(axis) * d
    return M


def apply(M, V):
    return V @ M[:3, :3].T + M[:3, 3]


def nearest_dist(points, t: BVHTree, cap):
    best = cap
    arg = None
    for i, p in enumerate(points):
        h = t.find_nearest(Vector(p), best)
        if h[0] is not None and h[3] < best:
            best = h[3]
            arg = i
    return best, arg


def _axis_radius(P, pivot, axis):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    d = np.asarray(P, float) - np.asarray(pivot, float)
    return np.linalg.norm(d - np.outer(d @ a, a), axis=1)


def _proof(points, need, t: BVHTree):
    """Radius-aware coarse-step proof (gunlib 0.2.1): every point must lie at least its own need (r x step / 2: how far
    it travels off the swept chord between two steps) from the other surface. Returns (failures, worst margin)."""
    fails, worst = 0, None
    cap = float(need.max()) if len(need) else 0.0
    for p, nd in zip(points, need):
        h = t.find_nearest(Vector(p), cap)
        if h[0] is not None and h[3] < nd:
            fails += 1
            m = h[3] - nd
            worst = m if worst is None else min(worst, m)
    return fails, worst


def sweep(moving: Dict[str, tuple], fixed: Dict[str, tuple], motion, values: Sequence[float],
          clearance_every: int = 1, cap_mm: float = 3.0, sample_mm: float = 0.5, proof=None):
    """motion(v) -> 4x4 matrix (mm, frame B). Returns per-step records and a summary.
    ``proof`` (gunlib 0.2.1, rotations): {"pivot", "axis", "step_deg", "skip": v -> bool}: at every step not skipped,
    every moving sample stands >= r x step / 2 from the fixed surfaces and every nearby fixed sample >= its own
    r x step / 2 from the moving surface (r = distance from the rotation axis), so nothing can cross between steps;
    records proof_fails / proof_margin per step."""
    # fixed union tree with part ids per triangle
    FV, FT, Fid, names = [], [], [], []
    n = 0
    for k, (nm, (V, T)) in enumerate(fixed.items()):
        FV.append(V)
        FT.append(T + n)
        Fid.append(np.full(len(T), k))
        names.append(nm)
        n += len(V)
    FV = np.vstack(FV)
    FT = np.vstack(FT)
    Fid = np.concatenate(Fid)
    ftree = tree(FV, FT)
    MV = np.vstack([v for v, _ in moving.values()])
    MT, off = [], 0
    for v, t in moving.values():
        MT.append(t + off)
        off += len(v)
    MT = np.vstack(MT)
    msamp = bl.surface_samples(MV, MT, sample_mm)
    # fixed samples inside the swept bbox (+cap)
    lo, hi = MV.min(0), MV.max(0)
    for v in (values[0], values[-1], values[len(values) // 2]):
        Q = apply(motion(v), MV)
        lo, hi = np.minimum(lo, Q.min(0)), np.maximum(hi, Q.max(0))
    lo -= cap_mm
    hi += cap_mm
    tri_lo = FV[FT].min(axis=1)
    tri_hi = FV[FT].max(axis=1)
    near = np.all((tri_hi >= lo) & (tri_lo <= hi), axis=1)
    fs = bl.surface_samples(FV, FT[near], sample_mm)
    fs = fs[np.all((fs >= lo) & (fs <= hi), axis=1)]
    recs = []
    t0 = time.time()
    if proof:
        k = math.radians(float(proof["step_deg"])) / 2.0
        need_m = _axis_radius(msamp, proof["pivot"], proof["axis"]) * k + 1e-4
        need_f = _axis_radius(fs, proof["pivot"], proof["axis"]) * k + 1e-4
    for i, v in enumerate(values):
        M = motion(v)
        Q = apply(M, MV)
        mt = tree(Q, MT)
        pairs = ftree.overlap(mt)
        hit_parts = sorted({names[Fid[a]] for a, _ in pairs})
        rec = {"value": float(v), "intersections": len(pairs), "hit_parts": hit_parts}
        if proof and not proof["skip"](v) and not pairs:
            f1, w1 = _proof(apply(M, msamp), need_m, ftree)
            f2, w2 = _proof(fs, need_f, mt)
            rec["proof_fails"] = f1 + f2
            ws = [w for w in (w1, w2) if w is not None]
            rec["proof_margin"] = round(min(ws), 4) if ws else None
        last = i == len(values) - 1
        if i % clearance_every == 0 or last or i == 0:
            d1, a1 = nearest_dist(apply(M, msamp), ftree, cap_mm)
            d2, a2 = nearest_dist(fs, mt, cap_mm)
            d = min(d1, d2)
            who = None
            if d1 <= d2 and a1 is not None:
                h = ftree.find_nearest(Vector(apply(M, msamp[a1:a1 + 1])[0]), cap_mm)
                who = names[Fid[h[2]]] if h[2] is not None else None
            elif a2 is not None:
                h = ftree.find_nearest(Vector(fs[a2]), 1e-3)
                who = names[Fid[h[2]]] if h[2] is not None else None
            rec["clearance_mm"] = round(float(d), 4)
            rec["nearest_part"] = who
        recs.append(rec)
    cl = [r["clearance_mm"] for r in recs if "clearance_mm" in r]
    worst = min((r for r in recs if "clearance_mm" in r), key=lambda r: r["clearance_mm"])
    summ = {"steps": len(values), "range": [float(values[0]), float(values[-1])],
            "step": float(values[1] - values[0]) if len(values) > 1 else 0.0,
            "intersecting_steps": int(sum(1 for r in recs if r["intersections"])),
            "max_intersections": int(max(r["intersections"] for r in recs)),
            "parts_hit": sorted({p for r in recs for p in r["hit_parts"]}),
            "min_clearance_mm": float(min(cl)), "min_at": worst["value"], "min_with": worst.get("nearest_part"),
            "rest_clearance_mm": recs[0].get("clearance_mm"), "rest_nearest": recs[0].get("nearest_part"),
            "end_clearance_mm": recs[-1].get("clearance_mm"), "end_nearest": recs[-1].get("nearest_part"),
            "seconds": round(time.time() - t0, 1), "moving_samples": int(len(msamp)), "fixed_samples": int(len(fs))}
    return recs, summ


def pair_intersections(geoms: Dict[str, tuple]) -> List[dict]:
    """Every pair of parts at rest: triangle-triangle intersections (G5: 0 at LOD0)."""
    names = list(geoms)
    trees = {n: tree(*geoms[n]) for n in names}
    boxes = {n: (geoms[n][0].min(0), geoms[n][0].max(0)) for n in names}
    out = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            (la, ha), (lb, hb) = boxes[a], boxes[b]
            if np.any(ha < lb - 0.01) or np.any(hb < la - 0.01):
                continue
            pairs = trees[a].overlap(trees[b])
            if pairs:
                out.append({"a": a, "b": b, "intersecting_triangle_pairs": len(pairs)})
    return out


def min_gaps(geoms: Dict[str, tuple], pairs: Sequence[tuple], sample_mm=0.5, cap_mm=0.5):
    """Minimum distance between named part pairs (surface samples both ways)."""
    out = []
    for a, b in pairs:
        if a not in geoms or b not in geoms:
            continue
        ta, tb = tree(*geoms[a]), tree(*geoms[b])
        sa = bl.surface_samples(*geoms[a], sample_mm)
        sb = bl.surface_samples(*geoms[b], sample_mm)
        lo = np.maximum(geoms[a][0].min(0), geoms[b][0].min(0)) - cap_mm
        hi = np.minimum(geoms[a][0].max(0), geoms[b][0].max(0)) + cap_mm
        sa = sa[np.all((sa >= lo) & (sa <= hi), axis=1)]
        sb = sb[np.all((sb >= lo) & (sb <= hi), axis=1)]
        d1, _ = nearest_dist(sa, tb, cap_mm)
        d2, _ = nearest_dist(sb, ta, cap_mm)
        out.append({"a": a, "b": b, "min_gap_mm": round(float(min(d1, d2)), 4)})
    return out
