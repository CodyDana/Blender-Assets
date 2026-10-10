"""Dimension gate for SM_Casing_762x39 (plain numpy): measures a LOD0 vertex cloud against the C.I.P. numbers.

Input: vertices in mm in the case frame (axis = +X, x = 0 at the base plane). Rings are found by their axial position
(|x - target| < 1e-3 mm); a ring's diameter is 2 x its mean vertex radius (the profile vertices ARE the dimension
points). The 24-gon's across-flats diameter (x cos 7.5 deg) is reported as information, not gated.
"""
from __future__ import annotations

import math
from typing import Dict, List

import numpy as np

from casing_spec import CIP, EXTRA

TOL_MM = 0.05
TOL_DEG = 0.1


def _ring(V: np.ndarray, x: float, r_expect: float, tol: float = 1e-3) -> Dict:
    r = np.hypot(V[:, 1], V[:, 2])
    sel = (np.abs(V[:, 0] - x) < tol) & (r > 0.05)
    if not sel.any():
        return {"n": 0}
    rs = r[sel]
    # several rings can share an x (base plane: dimple rim + chamfer; mouth: outer + inner): keep the nearest radius
    groups = {}
    for v in rs:
        key = round(float(v), 3)
        groups.setdefault(key, []).append(float(v))
    best = min(groups, key=lambda k: abs(k - r_expect))
    g = np.array(groups[best])
    return {"n": int(len(g)), "r_mean": float(g.mean()), "r_spread": float(g.max() - g.min())}


def measure(V_mm: np.ndarray, segments: int = 24) -> Dict:
    V = np.asarray(V_mm, float)
    rows: List[Dict] = []

    def dia(name, x, d_expect):
        ring = _ring(V, x, d_expect / 2.0)
        d = 2.0 * ring["r_mean"] if ring.get("n") else float("nan")
        rows.append({"dim": name, "at_mm": x, "expected_mm": d_expect, "measured_mm": round(d, 4),
                     "err_mm": round(d - d_expect, 4), "ring_vertices": ring.get("n", 0),
                     "across_flats_mm_info": round(d * math.cos(math.pi / segments), 4),
                     "pass": bool(ring.get("n", 0) >= segments and abs(d - d_expect) <= TOL_MM)})
        return ring

    def length(name, measured, expect):
        rows.append({"dim": name, "expected_mm": expect, "measured_mm": round(measured, 4),
                     "err_mm": round(measured - expect, 4), "pass": bool(abs(measured - expect) <= TOL_MM)})

    def angle(name, measured, expect):
        rows.append({"dim": name, "expected_deg": round(expect, 4), "measured_deg": round(measured, 4),
                     "err_deg": round(measured - expect, 4), "pass": bool(abs(measured - expect) <= TOL_DEG)})

    rr, rg = CIP["R1"] / 2.0, CIP["E1"] / 2.0
    r_all = np.hypot(V[:, 1], V[:, 2])
    outer = r_all > (EXTRA["neck_inner_d"] / 2.0 + 0.1)
    xs = V[:, 0]
    base_x = float(xs[outer & (r_all > 5.0)].min())                   # base plane (chamfer ring)
    mouth_x = float(xs[outer].max())
    length("L3 case length", mouth_x - base_x, CIP["L3"])
    Vb = V.copy()
    Vb[:, 0] -= base_x
    V = Vb
    dia("R1 rim (lower edge of the rim band)", CIP["f"], CIP["R1"])
    rim_top = _ring(V, CIP["R"] - (rr - rg), rr)
    dia("R1 rim (upper edge of the rim band)", CIP["R"] - (rr - rg), CIP["R1"])
    base_ring = _ring(V, 0.0, rr - CIP["f"])
    length("f base chamfer (radial)", rr - base_ring.get("r_mean", float("nan")), CIP["f"])
    dia("E1 extractor groove (floor start, x = R)", CIP["R"], CIP["E1"])
    dia("E1 extractor groove (floor end, x = R + e)", CIP["R"] + CIP["e"], CIP["E1"])
    # groove floor width e and the rim thickness R come from the ring positions themselves
    xr = np.unique(np.round(V[np.abs(np.hypot(V[:, 1], V[:, 2]) - rg) < 1e-3, 0], 4))
    if len(xr) >= 2:
        length("R base to groove floor", float(xr.min()), CIP["R"])
        length("e groove floor width", float(xr.max() - xr.min()), CIP["e"])
    dia("P1 body at E", CIP["E"], CIP["P1"])
    dia("P2 body at L1", CIP["L1"], CIP["P2"])
    dia("H1 neck at L2", CIP["L2"], CIP["H1"])
    dia("H2 mouth at L3", CIP["L3"], CIP["H2"])
    dia("neck inner (projectile G1 7.92, not C.I.P. case)", CIP["L3"], EXTRA["neck_inner_d"])
    r_p2, r_h = CIP["P2"] / 2.0, CIP["H1"] / 2.0
    angle("alpha shoulder (included)", 2.0 * math.degrees(math.atan2(r_p2 - r_h, CIP["L2"] - CIP["L1"])),
          CIP["alpha_deg"])
    # measured angles from the rings found
    p2 = _ring(V, CIP["L1"], r_p2)
    h1 = _ring(V, CIP["L2"], r_h)
    if p2.get("n") and h1.get("n"):
        rows[-1]["measured_deg"] = round(2.0 * math.degrees(math.atan2(p2["r_mean"] - h1["r_mean"],
                                                                        CIP["L2"] - CIP["L1"])), 4)
        rows[-1]["err_deg"] = round(rows[-1]["measured_deg"] - rows[-1]["expected_deg"], 4)
        rows[-1]["pass"] = abs(rows[-1]["err_deg"]) <= TOL_DEG
    p1 = _ring(V, CIP["E"], rr)
    gf = _ring(V, CIP["R"] + CIP["e"], rg)
    if p1.get("n") and gf.get("n"):
        angle("delta groove front flank (to the axis)",
              math.degrees(math.atan2(p1["r_mean"] - gf["r_mean"], CIP["E"] - CIP["R"] - CIP["e"])), CIP["delta_deg"])
    gs = _ring(V, CIP["R"], rg)
    if rim_top.get("n") and gs.get("n"):
        angle("beta rim front cone", math.degrees(math.atan2(CIP["R"] - (CIP["R"] - (rr - rg)),
                                                             rim_top["r_mean"] - gs["r_mean"])), CIP["beta_deg"])
    return {"tolerance_mm": TOL_MM, "tolerance_deg": TOL_DEG, "base_plane_x_mm": round(base_x, 5),
            "rows": rows, "pass": all(r["pass"] for r in rows)}
