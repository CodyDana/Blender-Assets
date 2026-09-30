"""Pine needle ROSETTE units, hand-shaped in code (numpy only). Pines v2, owner-approved method, step 1.

The sheet's pad close-ups (pad from the side, pad from above) show every pad as a dome of SEPARATE rosettes: a
radial burst of 2-needle fascicles at the end of a short shoot, 8-15 cm across, needles 7-12 cm, straight and
rigid, pale yellow-green fascicle bases (the sheaths show as yellow specks among the needles) and a short pale
candle in the centre. From the side a rosette is an upright brush (a cone opening upward); from above a star.

One unit, local frame: the shoot runs along +Z and ENDS at the origin (the twig tube of the trunk mesh ends there).
  * fascicles on a 137.5 degree spiral along the last ``shoot_len`` of the shoot, denser toward the tip;
  * each fascicle = 2 needles welded at ONE base vertex inside the sheath (no coincident vertices, study P39);
  * each needle = a 2-triangle strip: full width to 70 % of its length, then a single tapered tip triangle.
    Straight (a rigid needle), a 1-4 degree kink at most;
  * polar angle from the shoot axis: the top fascicles stand near the axis (inner cone), the lowest splay out to
    the outer cone angle, so the burst is a cone about ``1.2 x needle length`` across;
  * a 5-sided candle (pale bud) on the tip.

UV0: every needle (and the candle) gets its own cell of the needle texture (vegetation/foliage.py CELLS_U x
CELLS_V); within a cell v runs base -> tip, so the texture's pale sheath band sits at every needle's base and the
tip colour at its tip. The candle samples the pale bud band. Units are ``foliage.Tuft`` objects, instanced by
``foliage.instance``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from foliage import Tuft

GOLDEN = np.deg2rad(137.5)


@dataclass
class RosetteSpec:
    name: str
    n_fasc: int                         # fascicles (2 needles each)
    needle_len: Tuple[float, float]     # metres, per needle uniform in range
    cone: Tuple[float, float]           # polar angle (deg) of the top fascicle .. the lowest fascicle
    shoot_len: float = 0.035            # fascicle zone along the shoot (m)
    width: float = 0.0030               # needle width at the base (m); mean width half this (P43, recorded)
    candle_len: float = 0.018           # 1.5-2 cm pale bud (study 3.1)
    twig_r: float = 0.0035              # shoot radius where the fascicles leave it
    tilt: float = 0.0                   # asymmetric lean of the burst (deg), gives a less perfect star
    seed: int = 0


# The library (task: 4-6 units). Across the set: 8-15 cm across, needles 7-12 cm, fascicle counts from a sparse
# young shoot to the dense brushes of the pad close-ups, one flatter star (seen on the pad tops) and one tall
# upright brush (seen on the pad rims from the side).
LIBRARY: List[RosetteSpec] = [
    # v2 r6 close-up look: the sheet's rosettes are dense round pom-poms (70-100 needles, the lowest out to near
    # horizontal); 7-9.5 cm needles keep them 8-15 cm across (P90) with the wider cone
    RosetteSpec("RosetteA_Standard", 42, (0.070, 0.092), (14.0, 64.0), seed=11),
    RosetteSpec("RosetteB_Dense", 50, (0.072, 0.093), (12.0, 62.0), shoot_len=0.040, seed=23),
    RosetteSpec("RosetteC_Young", 30, (0.070, 0.086), (10.0, 56.0), shoot_len=0.028, candle_len=0.022, seed=37),
    RosetteSpec("RosetteD_Star", 44, (0.070, 0.086), (24.0, 65.0), shoot_len=0.030, tilt=6.0, seed=41),
    RosetteSpec("RosetteE_Brush", 42, (0.078, 0.096), (8.0, 52.0), shoot_len=0.040, seed=53),
]


def make_rosette(rs: RosetteSpec) -> Tuft:
    rng = np.random.default_rng(rs.seed)
    verts, tris, uvs, cells, kinds, along = [], [], [], [], [], []

    def add(p, k, a):
        verts.append(np.asarray(p, dtype=np.float64))
        kinds.append(k)
        along.append(a)
        return len(verts) - 1

    tilt_ax = rng.uniform(0, 2 * np.pi)
    tilt = np.deg2rad(rs.tilt)
    Rt = _axis_rot(np.array([np.cos(tilt_ax), np.sin(tilt_ax), 0.0]), tilt)
    cell = 0
    for f in range(rs.n_fasc):
        t = (f + 0.5) / rs.n_fasc                       # 0 low on the shoot .. 1 at the tip
        z = -rs.shoot_len * (1.0 - t) ** 1.15            # denser toward the tip
        phi = f * GOLDEN + rng.normal(0, 0.18)
        radial = np.array([np.cos(phi), np.sin(phi), 0.0])
        b = np.array([0.0, 0.0, z]) + radial * rs.twig_r * 0.95
        bi = add(b, 0, t)
        # polar angle: inner cone at the tip, outer cone low on the shoot (+ jitter); a few strays
        th = rs.cone[1] + (rs.cone[0] - rs.cone[1]) * t ** 0.85 + rng.normal(0, 5.0)
        if rng.random() < 0.06:
            th += rng.uniform(8, 18)
        alpha = np.deg2rad(np.clip(th, 3.0, 95.0))
        for side in (-1, 1):
            az = phi + side * np.deg2rad(rng.uniform(4, 11))
            d = np.array([np.sin(alpha) * np.cos(az), np.sin(alpha) * np.sin(az), np.cos(alpha)])
            d = Rt @ d
            L = rng.uniform(*rs.needle_len)
            ref = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.95 else np.array([1.0, 0.0, 0.0])
            w1 = np.cross(d, ref)
            w1 /= np.linalg.norm(w1)
            w2 = np.cross(d, w1)
            tw = rng.uniform(0, np.pi)
            wv = (np.cos(tw) * w1 + np.sin(tw) * w2) * rs.width * rng.uniform(0.85, 1.1)
            # a rigid needle: straight, a 1-4 degree kink at most; ONE tapering triangle (v2 r6: the 3-triangle strip
            # cost 3x the triangles for no visible gain at 1-3 mm; the budget goes into denser rosettes instead)
            kink = np.deg2rad(rng.uniform(1.0, 4.0))
            d2 = d * np.cos(kink) - np.array([0.0, 0.0, 1.0]) * np.sin(kink)
            d2 /= np.linalg.norm(d2)
            b2 = b + wv + d * 0.0025                     # second base corner (>= 0.05 mm from anything, P39)
            tip = b + d * (0.70 * L) + d2 * (0.30 * L) + 0.5 * wv
            i_b2 = add(b2, 1, t)
            i_t = add(tip, 2, t)
            tris.append((bi, i_b2, i_t))
            uvs.append(((0.18, 0.02), (0.82, 0.02), (0.5, 0.98)))
            cells.append(cell)
            cell += 1
    # candle: a 5-sided pale cone on the tip, its base ring above every fascicle base
    cr = 0.0036
    ring = [add((cr * np.cos(a), cr * np.sin(a), 0.003), 3, 1.0) for a in np.linspace(0, 2 * np.pi, 5, endpoint=False)]
    apex = add((rng.normal(0, 0.0015), rng.normal(0, 0.0015), 0.003 + rs.candle_len), 3, 1.0)
    for i in range(5):
        tris.append((ring[i], ring[(i + 1) % 5], apex))
        u0 = 0.02 + 0.196 * i
        uvs.append(((u0, 0.004), (u0 + 0.17, 0.004), (u0 + 0.085, 0.055)))
        cells.append(cell)
    cell += 1
    return Tuft(np.array(verts), np.array(tris, dtype=np.int64), np.array(uvs, dtype=np.float64),
                np.array(cells, dtype=np.int64), cell, np.array(kinds), np.array(along))


def _axis_rot(axis, ang):
    axis = axis / np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K


def library(scale_len: float = 1.0) -> List[Tuft]:
    """The rosette library as Tufts (``scale_len`` scales needle lengths, e.g. per tree)."""
    out = []
    for rs in LIBRARY:
        r2 = RosetteSpec(**{**rs.__dict__, "needle_len": (rs.needle_len[0] * scale_len, rs.needle_len[1] * scale_len)})
        out.append(make_rosette(r2))
    return out


def measure(tf: Tuft) -> Dict:
    """Unit stats: across (max horizontal diameter of the needle tips), height, needle lengths, tris."""
    V = tf.V
    tips = V[tf.kind == 2]
    base_kind0 = V[tf.kind == 0]
    across = 2.0 * float(np.sqrt((tips[:, 0] ** 2 + tips[:, 1] ** 2)).max())
    across_p90 = 2.0 * float(np.percentile(np.sqrt(tips[:, 0] ** 2 + tips[:, 1] ** 2), 90))
    # needle length: tip to its fascicle base (the base vertex precedes its needles)
    lens = []
    last_base = None
    for i, k in enumerate(tf.kind):
        if k == 0:
            last_base = V[i]
        elif k == 2 and last_base is not None:
            lens.append(float(np.linalg.norm(V[i] - last_base)))
    return {"tris": int(len(tf.T)), "needles": int((tf.kind == 2).sum()), "fascicles": int(len(base_kind0)),
            "across_cm": round(100 * across, 1), "across_p90_cm": round(100 * across_p90, 1),
            "height_cm": round(100 * float(V[:, 2].max() - V[:, 2].min()), 1),
            "needle_len_cm": [round(100 * min(lens), 1), round(100 * max(lens), 1)]}
