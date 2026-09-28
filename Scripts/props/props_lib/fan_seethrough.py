#!/usr/bin/env python
"""props_lib.fan_seethrough - round 3: does daylight get through the fan around the leaf's inner edge?

A ray test on the POSED mesh (numpy positions, mathutils BVH): target points fill an annulus in the fan plane around
the leaf's inner edge (r_in - 3 mm .. r_in + 4 mm, every 0.1 mm radially and every ~0.1 mm along the arc, at least 2
degrees inside both guards), and from every target a ray is cast along each VIEW direction from far outside the fan.
A ray that hits nothing went through the fan: a see-through sample.  The views are the ones the reviews used:
front and back (orthographic), rim-oblique (a camera outside the rim looking in and down at the front, at several
elevations), rear-oblique (the same from behind), pivot-oblique (a camera over the pivot looking out) and two
tangential obliques.  Directions are set per target from its own radial direction, so every pleat is seen the same way.

``count(Q, T, spec, s)`` -> {view: holes}; one sample stands for ~0.01 mm^2 of the fan plane.  Used by build_fan.py
(gate G5) and by WorkFiles/fan/seethrough_compare.py.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

import numpy as np

from .fan_spec import D2R, FAN, FanSpec

VIEWS: Dict[str, Tuple[str, float]] = {
    "front": ("front", 90.0), "back": ("back", 90.0),
    "rim_oblique_20": ("rim", 20.0), "rim_oblique_25": ("rim", 25.0), "rim_oblique_30": ("rim", 30.0), "rim_oblique_45": ("rim", 45.0),
    "rim_oblique_60": ("rim", 60.0),
    "rear_oblique_30": ("rear", 30.0), "rear_oblique_45": ("rear", 45.0),
    "pivot_oblique_30": ("pivot", 30.0), "pivot_oblique_45": ("pivot", 45.0),
    "pivot_rear_oblique_30": ("pivot_rear", 30.0),
    "side_oblique_45_plus": ("side+", 45.0), "side_oblique_45_minus": ("side-", 45.0),
}


def targets(spec: FanSpec, s: float, dr: float = 0.1, r_lo: float = -3.0, r_hi: float = 4.0, margin_deg: float = 2.0):
    lo = spec.leaf_line_deg(0, s) + margin_deg
    hi = spec.leaf_line_deg(spec.n_sticks - 1, s) - margin_deg
    rs = np.arange(spec.r_in + r_lo, spec.r_in + r_hi + 1e-9, dr)
    dphi = dr / spec.r_in / D2R
    phis = np.arange(lo, hi, dphi)
    R, PH = np.meshgrid(rs, phis, indexing="ij")
    return R.ravel(), PH.ravel()


def direction(kind: str, elev: float, phi_deg: np.ndarray) -> np.ndarray:
    """unit direction of travel (camera -> scene) per target."""
    ph = np.asarray(phi_deg) * D2R
    ur = np.stack([np.cos(ph), np.sin(ph), np.zeros_like(ph)], 1)
    ut = np.stack([-np.sin(ph), np.cos(ph), np.zeros_like(ph)], 1)
    z = np.array([0.0, 0.0, 1.0])
    ce, se = math.cos(elev * D2R), math.sin(elev * D2R)
    if kind == "front":
        cam = np.tile(z, (len(ph), 1))
    elif kind == "back":
        cam = np.tile(-z, (len(ph), 1))
    elif kind == "rim":
        cam = ce * ur + se * z
    elif kind == "rear":
        cam = ce * ur - se * z
    elif kind == "pivot":
        cam = -ce * ur + se * z
    elif kind == "pivot_rear":
        cam = -ce * ur - se * z
    elif kind == "side+":
        cam = ce * ut + se * z
    elif kind == "side-":
        cam = -ce * ut + se * z
    else:
        raise KeyError(kind)
    d = -cam
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def count(Q: np.ndarray, T: np.ndarray, spec: FanSpec = FAN, s: float = 1.0, views: Sequence[str] = tuple(VIEWS),
          dr: float = 0.1, far: float = 600.0, keep: int = 0) -> Dict[str, object]:
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromPolygons([tuple(p) for p in np.asarray(Q, np.float64)], [tuple(int(v) for v in t) for t in T],
                                all_triangles=True, epsilon=0.0)
    R, PH = targets(spec, s, dr)
    P = np.stack([R * np.cos(PH * D2R), R * np.sin(PH * D2R), np.zeros_like(R)], 1)
    out: Dict[str, object] = {"samples_per_view": int(len(R)), "sample_mm2": round(dr * dr, 4)}
    where: Dict[str, List[Tuple[float, float]]] = {}
    for name in views:
        kind, elev = VIEWS[name]
        D = direction(kind, elev, PH)
        O = P - far * D
        holes = 0
        rows = []
        for k in range(len(P)):
            hit = tree.ray_cast(Vector(O[k]), Vector(D[k]), 2 * far)
            if hit[0] is None:
                holes += 1
                if keep and len(rows) < keep:
                    rows.append((round(float(R[k] - spec.r_in), 2), round(float(PH[k]), 3)))
        out[name] = holes
        if keep:
            where[name] = rows
    out["total"] = int(sum(v for k, v in out.items() if k in VIEWS))
    if keep:
        out["examples_dr_phi"] = where
    return out


def count_reference(Q: np.ndarray, T: np.ndarray, spec: FanSpec = FAN, sub: int = 4) -> Dict[str, object]:
    """fan2's reference camera (REFERENCE_SPEC 1, props_lib.fan_refview): every pixel of the band 120 - 165 px round
    the rivet, sub x sub rays each; a ray that hits nothing and crosses the fan plane inside the fan (70 - 95 mm from
    the rivet, 2 deg inside both leaf ends) is a see-through ray.  Q: the OPEN pose, mm, build frame."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from . import fan_refview as RV
    M = RV.placement(spec)
    W = (np.asarray(Q, np.float64) * 0.001) @ M[:3, :3].T + M[:3, 3]
    tree = BVHTree.FromPolygons([tuple(p) for p in W], [tuple(int(v) for v in t) for t in T], all_triangles=True)
    C = RV.camera_matrix(spec)
    Minv = np.linalg.inv(M)
    f_px = RV.LENS_MM / RV.SENSOR_MM * RV.RES[0]
    w, h = RV.RES
    cx, cy = RV.RIVET_PX
    lo, hi = spec.leaf_line_deg(0, 1.0) + 2.0, spec.leaf_line_deg(spec.n_sticks - 1, 1.0) - 2.0
    o = Minv[:3, :3] @ C[:3, 3] + Minv[:3, 3]
    n = miss = 0
    offs = [(k + 0.5) / sub for k in range(sub)]
    for y in range(int(cy - 170), int(cy + 20)):
        for x in range(int(cx - 170), int(cx + 170)):
            if not (120.0 <= math.hypot(x - cx, y - cy) <= 165.0):
                continue
            for sx in offs:
                for sy in offs:
                    d = C[:3, :3] @ np.array([(x + sx - w / 2) / f_px, -(y + sy - h / 2) / f_px, -1.0])
                    d /= np.linalg.norm(d)
                    n += 1
                    if tree.ray_cast(Vector(C[:3, 3]), Vector(d), 10.0)[0] is None:
                        db = Minv[:3, :3] @ d
                        t = -o[2] / db[2]
                        q = (o + t * db) * 1000.0
                        if lo < math.degrees(math.atan2(q[1], q[0])) < hi and 70.0 < math.hypot(q[0], q[1]) < 95.0:
                            miss += 1
    return {"rays": n, "see_through_rays": miss}


__all__ = ["count", "count_reference", "VIEWS", "targets", "direction"]
