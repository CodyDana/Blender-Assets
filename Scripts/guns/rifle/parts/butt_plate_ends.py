"""Butt-plate detail round 2b: the plate's END shapes compared at the WIDTH scale (plain Python, no Blender).

    py -3 -B Scripts/guns/rifle/parts/butt_plate_ends.py [--fit]

Why: c7 draws the plate at aspect 0.22 (width / height); the spec (TOP flush cap, 36.9) gives ~0.34 (proposal BP-5).
Rounds 1-2 matched c7's half-width profile in the UNIT BOX (height and width both normalised). At our wider plate that
makes each end's arch 1/1.5 as tall relative to the width as c7 draws it: the judge reads our heel as "flat-topped"
and our toe as "blunt", where c7 shows a semicircular heel arch and a long tapered toe.
The ends are compared here in the frame a viewer reads them in: distance from the tip and half-width both as fractions
of the plate's WIDTH. 'end IoU' = IoU of the two end regions (0 .. END_D widths from the tip) in that frame.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from rifle_common import SCRATCH, REVIEW  # noqa: E402

WIP = SCRATCH / "detail" / "butt_plate_wip"
OUT = REVIEW / "detail" / "butt_plate"
END_D = 0.9          # end region compared: 0 .. 0.9 widths from the tip


def ref_halfwidth(ss=4):
    """c7 plate trace -> (d_top, f_top), (d_bot, f_bot): distance from each tip and half-width, both in widths
    (width = the widest row), sub-pixel rows from a softened 4x upsample."""
    m = np.load(WIP / "plate_mask_c7.npy")
    F = ndi.zoom(ndi.gaussian_filter(m.astype(float), 0.7), ss, order=1)
    ys = np.nonzero((F >= 0.5).any(1))[0]
    rows = []
    for y in range(ys.min(), ys.max() + 1):
        on = np.nonzero(F[y] >= 0.5)[0]
        if len(on):
            rows.append((y, on.max() - on.min() + 1))
    rows = np.array(rows, float)
    W = ndi.gaussian_filter1d(rows[:, 1], 2 * ss).max()
    y0, y1 = rows[0, 0] - 0.5, rows[-1, 0] + 0.5
    d_top = (rows[:, 0] - y0) / W
    d_bot = (y1 - rows[:, 0]) / W
    f = rows[:, 1] / W / 2.0
    return (d_top, f), (d_bot[::-1], f[::-1]), (y1 - y0) / W


def our_halfwidth(n=4000):
    """butt_plate_section() -> the same two end curves (in widths) and the aspect height / width."""
    from parts import butt_plate as BP
    Q = BP.butt_plate_section()
    zt, zb = Q[:, 1].max(), Q[:, 1].min()
    z = np.linspace(zt, zb, n)
    hw = np.array([BP._section_halfwidth(Q, zz) for zz in z])
    W = 2 * hw.max()
    d_top = (zt - z) / W
    d_bot = (z - zb) / W
    return (d_top, hw / W), (d_bot[::-1], (hw / W)[::-1]), (zt - zb) / W


def end_iou(a, b, dmax=END_D, n=600):
    """IoU of the two symmetric end regions {|y| <= f(d), 0 <= d <= dmax} (area by 1D integration)."""
    d = np.linspace(0, dmax, n)
    fa = np.interp(d, a[0], a[1], right=a[1][-1])
    fb = np.interp(d, b[0], b[1], right=b[1][-1])
    return float(np.minimum(fa, fb).sum() / np.maximum(fa, fb).sum()), float(np.max(np.abs(fa - fb)))


def report():
    rt, rb, ra = ref_halfwidth()
    ot, ob, oa = our_halfwidth()
    it, mt = end_iou(rt, ot)
    ib, mb = end_iou(rb, ob)
    st = [0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    rep = {"aspect_h_over_w": {"c7": round(ra, 3), "ours": round(oa, 3)},
           "heel_end_iou_width_frame": round(it, 4), "heel_max_abs_diff": round(mt, 3),
           "toe_end_iou_width_frame": round(ib, 4), "toe_max_abs_diff": round(mb, 3),
           "heel (d, c7, ours)": [(s, round(float(np.interp(s, *rt)), 3), round(float(np.interp(s, *ot)), 3)) for s in st],
           "toe (d, c7, ours)": [(s, round(float(np.interp(s, *rb)), 3), round(float(np.interp(s, *ob)), 3)) for s in st]}
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="r2b")
    a = ap.parse_args()
    rep = report()
    (OUT / f"{a.tag}_ends.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
