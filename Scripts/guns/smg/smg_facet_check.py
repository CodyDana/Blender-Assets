"""SMG01 gate G3o (W4 review fixes): facets on the boundary loops of OPENINGS, not only on revolves (plain Python):

    py -3 -B Scripts/guns/smg/smg_facet_check.py [--npz scratch/form_tris.npz] [--json scratch/facet_check.json]

The W4 craft review found the moulded vents' stadium ends and the charging channel's lock notch polygonal (7 segments
per semicircle, 25.7 deg facets) though every revolve passed G3. This check walks the side faces (planar faces whose
normal is +-Y) of the moulded parts, takes the boundary loops of each coplanar face set, keeps the HOLES (loops wound
against the face normal: the openings and recess mouths), and measures each loop's arcs: a run of >= 2 consecutive
vertices turning the same way by 1-60 deg is an arc; its local radius r = L / (2 sin(theta / 2)) (L the mean of the two
edges' shorter one). Gate: the chord error r (1 - cos(theta / 2)) <= 0.035 mm on every arc (0.43 px at the 3x review
scale, 12.3 px/mm: the AR-01's fastener rule; the W1-W3 vents' 25.7 deg facets on r 3.85 were 0.096 mm, 1.2 px) and
theta <= 7.5 deg (+0.3) where r >= 5 mm (G3's barrel-size rule).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import SCRATCH  # noqa: E402

PARTS = ("upper_receiver", "lower_receiver", "stock_frame", "magazine", "grip_cover", "butt_pad")
G3_DEG, G3_TOL, R_MIN, SAG_MAX = 7.5, 0.3, 5.0, 0.035


def loops_from_edges(edges):
    nxt = {}
    for a, b in edges:
        nxt.setdefault(a, []).append(b)
    used = set()
    out = []
    for a, b in edges:
        if (a, b) in used:
            continue
        loop = [a]
        cur, prev = b, a
        used.add((a, b))
        ok = True
        while cur != a:
            cands = [c for c in nxt.get(cur, []) if (cur, c) not in used]
            if not cands:
                ok = False
                break
            c = cands[0]
            used.add((cur, c))
            loop.append(cur)
            prev, cur = cur, c
            if len(loop) > 100000:
                ok = False
                break
        if ok and len(loop) >= 3:
            out.append(loop)
    return out


def arc_stats(P2):
    """P2 (n, 2) closed loop: (max facet deg over arcs with r >= R_MIN, max sagitta mm over smaller arcs, worst row)."""
    n = len(P2)
    E = np.roll(P2, -1, 0) - P2
    L = np.linalg.norm(E, axis=1)
    keep = L > 1e-6
    P2, E, L = P2[keep], E[keep], L[keep]
    n = len(P2)
    if n < 4:
        return 0.0, 0.0, None
    ang = np.arctan2(E[:, 1], E[:, 0])
    turn = np.degrees((ang - np.roll(ang, 1) + np.pi) % (2 * np.pi) - np.pi)      # at vertex i (edge i-1 -> i)
    Lm = np.minimum(L, np.roll(L, 1))
    arcy = (np.abs(turn) > 1.0) & (np.abs(turn) < 60.0)
    same_prev = arcy & np.roll(arcy, 1) & (np.sign(turn) == np.sign(np.roll(turn, 1)))
    same_next = arcy & np.roll(arcy, -1) & (np.sign(turn) == np.sign(np.roll(turn, -1)))
    inarc = same_prev | same_next
    worst_deg, worst_sag, row = 0.0, 0.0, None
    for i in np.nonzero(inarc)[0]:
        th = math.radians(abs(turn[i]))
        r = Lm[i] / (2.0 * math.sin(th / 2.0))
        sag = r * (1.0 - math.cos(th / 2.0))
        if r >= R_MIN and abs(turn[i]) > worst_deg:
            worst_deg = abs(turn[i])
        if sag > worst_sag:
            worst_sag = sag
            row = {"at": np.round(P2[i], 2).tolist(), "deg": round(float(abs(turn[i])), 2), "r_mm": round(r, 2),
                   "sagitta_mm": round(sag, 4)}
    return worst_deg, worst_sag, row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", default=str(SCRATCH / "form_tris.npz"))
    ap.add_argument("--json", default=str(SCRATCH / "facet_check.json"))
    a = ap.parse_args()
    t = np.load(a.npz)
    V, T, lab, names = t["V"], t["T"], t["lab"], [str(x) for x in t["names"]]
    out = {"rule": __doc__.split("\n\n")[2].strip().replace("\n", " "), "parts": {}}
    ok_all = True
    for pn in PARTS:
        if pn not in names:
            continue
        k = names.index(pn)
        Tk = T[lab == k]
        A, B, C = V[Tk[:, 0]], V[Tk[:, 1]], V[Tk[:, 2]]
        Nn = np.cross(B - A, C - A)
        ar = np.linalg.norm(Nn, axis=1)
        Nn = Nn / np.maximum(ar[:, None], 1e-12)
        side = (np.abs(Nn[:, 1]) > 0.9999) & (ar > 1e-9)
        groups = defaultdict(list)
        for i in np.nonzero(side)[0]:
            groups[(round(float(A[i, 1]), 2), int(np.sign(Nn[i, 1])))].append(i)
        holes = []
        for (yv, sgn), ids in groups.items():
            cnt = defaultdict(int)
            for i in ids:
                a_, b_, c_ = Tk[i]
                for e in ((a_, b_), (b_, c_), (c_, a_)):
                    cnt[e] += 1
            bnd = [e for e in cnt if (e[1], e[0]) not in cnt]
            for lp in loops_from_edges(bnd):
                P2 = V[lp][:, [0, 2]]
                x, z = P2[:, 0], P2[:, 1]
                sa = 0.5 * float(np.dot(x, np.roll(z, -1)) - np.dot(z, np.roll(x, -1)))
                # a CCW loop in (X, Z) seen from +Y is clockwise: for a +Y face the outer boundary has sa < 0
                is_hole = (sa > 0) if sgn > 0 else (sa < 0)
                if not is_hole or abs(sa) < 0.5:
                    continue
                d, sg, row = arc_stats(P2 if sa > 0 else P2[::-1])
                holes.append({"face_Y": yv, "centre_XZ": np.round(P2.mean(0), 1).tolist(), "area_mm2": round(abs(sa), 1),
                              "max_facet_deg_r_ge_5": round(d, 2), "max_sagitta_mm": round(sg, 4),
                              "worst": row})
        bad = [h for h in holes if h["max_facet_deg_r_ge_5"] > G3_DEG + G3_TOL or h["max_sagitta_mm"] > SAG_MAX]
        ok_all &= not bad
        out["parts"][pn] = {"holes": len(holes), "fail": bad,
                            "max_facet_deg": max([h["max_facet_deg_r_ge_5"] for h in holes] or [0.0]),
                            "max_sagitta_mm": max([h["max_sagitta_mm"] for h in holes] or [0.0]),
                            "all": holes}
        print("[G3o] %-16s holes %3d  max facet %.2f deg (r >= 5)  max sagitta %.4f mm  fails %d" % (
            pn, len(holes), out["parts"][pn]["max_facet_deg"], out["parts"][pn]["max_sagitta_mm"], len(bad)))
    out["pass"] = bool(ok_all)
    Path(a.json).write_text(json.dumps(out, indent=1))
    print("[G3o]", "PASS" if ok_all else "FAIL")


if __name__ == "__main__":
    main()
