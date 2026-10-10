"""Hinges (gunlib 0.2.0; GUN_BUILDING_STUDY 3.7 hinge row, SMG_BUILD_PLAN 4.1 / 14 B3): knuckles, the axle or pin,
detent bosses, the latch bolt, the pivot record and the B3 sweep group. Plain Python (numpy).

The real pattern of a folding-stock / leaf hinge: a steel axle (or roll / solid pin) through alternating knuckles of
the two parts (the fixed side's outer knuckles, often with steel bushings in a polymer housing; the moving side's
centre knuckle), each knuckle a tube on the axle with a radial running clearance (hinge row 0.10-0.30 mm per side)
and an axial gap between neighbouring knuckles (same row); the axle's ends finished with a head, a peened or
chamfered end or a retaining clip; detents as a spring plunger or a boss riding a notch. Everything a sweep can
touch is modelled: the knuckles' end faces, the axle, the bores.

Frame: any; every function takes the axis as a point + direction in the gun frame M (mm).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..mesh import Mesh, revolve, tube

HINGE_ROW = (0.10, 0.30)


def axis_frame(p, d):
    d = np.asarray(d, float)
    d = d / np.linalg.norm(d)
    return np.asarray(p, float), d


def knuckle(p, d, t0: float, t1: float, r_out: float, r_bore: float, nseg: int = 32) -> Mesh:
    """A knuckle: a tube on the axis from t0 to t1 (mm along d from p), outer radius r_out, bore r_bore."""
    o, d = axis_frame(p, d)
    return tube(o + d * t0, o + d * t1, r_bore, r_out, nseg)


def knuckle_stack(p, d, spans: Sequence[Tuple[float, float, str]], r_out: float, axle_r: float,
                  radial: float = 0.15, axial: float = 0.15, nseg: int = 32) -> Dict[str, List[Mesh]]:
    """Alternating knuckles on one axis. ``spans`` = [(t0, t1, owner)] along the axis (owners alternate: 'fixed',
    'moving'); every owner's knuckles are shrunk by axial / 2 at each face that meets a neighbour, so neighbours stand
    ``axial`` apart; bores = axle_r + radial. Returns {owner: [tubes]}."""
    lo, hi = HINGE_ROW
    if not (lo <= radial <= hi and lo <= axial <= hi):
        raise ValueError("hinge clearances must sit in the hinge row %s (radial %.3f, axial %.3f)" % (HINGE_ROW, radial,
                                                                                                    axial))
    sp = sorted(spans)
    out: Dict[str, List[Mesh]] = {}
    for i, (t0, t1, owner) in enumerate(sp):
        a = t0 + (axial / 2.0 if i > 0 and abs(sp[i - 1][1] - t0) < axial + 1e-6 else 0.0)
        b = t1 - (axial / 2.0 if i < len(sp) - 1 and abs(sp[i + 1][0] - t1) < axial + 1e-6 else 0.0)
        out.setdefault(owner, []).append(knuckle(p, d, a, b, r_out, axle_r + radial, nseg))
    return out


def pin(p, d, t0: float, t1: float, r: float, chamfer: float = 0.3, head: Optional[Dict] = None,
        nseg: int = 32) -> Mesh:
    """An axle / pin from t0 to t1 along the axis: radius r, both ends chamfered (>= 0.1 mm, UD); ``head`` {'r':
    head radius, 'h': height, 'end': 0 or 1, 'chamfer': c} adds a round head at that end (a shouldered pin)."""
    o, d = axis_frame(p, d)
    c = max(0.1, min(chamfer, 0.45 * r))
    prof = [(t0, 0.0), (t0, r - c), (t0 + c, r), (t1 - c, r), (t1, r - c), (t1, 0.0)]
    if head:
        hr, hh, hc = head["r"], head["h"], max(0.1, min(head.get("chamfer", 0.3), 0.45 * head["h"]))
        if head.get("end", 1) == 1:
            prof = [(t0, 0.0), (t0, r - c), (t0 + c, r), (t1, r), (t1, hr), (t1 + hh - hc, hr), (t1 + hh, hr - hc),
                    (t1 + hh, 0.0)]
        else:
            prof = [(t0 - hh, 0.0), (t0 - hh, hr - hc), (t0 - hh + hc, hr), (t0, hr), (t0, r), (t1 - c, r),
                    (t1, r - c), (t1, 0.0)]
    return revolve(prof, o, d, nseg)


def detent_boss(center, normal, r: float, h: float, nseg: int = 24) -> Mesh:
    """A detent boss / plunger tip: a cylinder of radius r standing h proud along ``normal`` with a 45 deg chamfer of
    min(0.4 r, h / 2) on its end (it rides a notch, so the end is chamfered, never a point)."""
    c = max(0.1, min(0.4 * r, h / 2.0))
    o, nrm = axis_frame(center, normal)
    prof = [(-0.5, 0.0), (-0.5, r), (h - c, r), (h, r - c), (h, 0.0)]
    return revolve(prof, o, nrm, nseg)


def latch_bolt(p, d, t0: float, t1: float, r: float, neck: Tuple[float, float, float], chamfer: float = 0.3,
               nseg: int = 32) -> Mesh:
    """A necked latch bolt (push-button stock latch): radius r from t0 to t1 with a neck (n0, n1, r_neck) where the
    lug passes when the button is pressed; 45 deg shoulders at the neck (the bolt rides over the lug on unfolding)."""
    o, d = axis_frame(p, d)
    n0, n1, rn = neck
    c = max(0.1, min(chamfer, 0.45 * r))
    s = r - rn                                                      # 45 deg shoulder length
    prof = [(t0, 0.0), (t0, r - c), (t0 + c, r), (n0 - s, r), (n0, rn), (n1, rn), (n1 + s, r), (t1 - c, r),
            (t1, r - c), (t1, 0.0)]
    return revolve(prof, o, d, nseg)


def bore_cutter(p, d, t0: float, t1: float, r: float, nseg: int = 32) -> Mesh:
    """A cylinder cutter for a bore (to boolean a host part); run it 1 mm past both faces it opens."""
    o, d = axis_frame(p, d)
    return revolve([(t0, 0.0), (t0, r), (t1, r), (t1, 0.0)], o, d, nseg)


def record(pivot_M, axis, limits_deg: Tuple[float, float], row: str = "hinge", bone: Optional[str] = None,
           detents_deg: Sequence[float] = ()) -> Dict:
    """The joint record a part stores in its gun_part JSON (study 11.2: pivot, axis, limits, row)."""
    return {"type": "hinge", "pivot_M": [round(float(v), 4) for v in pivot_M], "axis": [float(v) for v in axis],
            "limits_deg": list(limits_deg), "row": row, "clearance_mm": list(HINGE_ROW), "bone": bone,
            "detents_deg": list(detents_deg)}


def sweep_group(parts: Sequence[str], pivot_B, axis, limits_deg: Tuple[float, float], row: str = "hinge",
                step: Optional[float] = None, fine: Sequence[Tuple[float, float, float]] = (),
                allowances: Sequence[Dict] = (), coarse_proof: bool = False) -> Dict:
    """A B3 group for gunlib.drivers.b3 (pivot in frame B). ``fine`` windows (a latch zone), ``coarse_proof`` (the
    plan's 0.25 deg stock-fold alternative) and declared ``allowances`` (snap, detents) pass straight through."""
    g = {"parts": list(parts), "kind": "rot", "pivot": np.asarray(pivot_B, float), "axis": list(axis),
         "range": [float(limits_deg[0]), float(limits_deg[1])], "row": row}
    if step is not None:
        g["step"] = float(step)
    if fine:
        g["fine"] = [list(f) for f in fine]
    if allowances:
        g["allowances"] = [dict(a) for a in allowances]
    if coarse_proof:
        g["coarse_proof"] = True
    return g


def fold_step(r_max_mm: float, c_mm: float = 0.10) -> float:
    """The study's rotation step: min(1 deg, c / r_max) (the plan's ~0.023 deg at r 250 mm for the stock fold)."""
    return min(1.0, math.degrees(c_mm / r_max_mm))


def rotate_points(V, pivot, axis, deg) -> np.ndarray:
    """Rotate points about an axis through pivot (numpy; the B3 driver's own motion)."""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    th = math.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    R = np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K
    P = np.asarray(pivot, float)
    return (np.asarray(V, float) - P) @ R.T + P

