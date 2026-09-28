# -*- coding: utf-8 -*-
"""Find the shipped atlas's front-card UV island by its grain/edge energy."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pbmetro as P
import pbtag as PT

SNAP = (r"C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/"
        r"70fec35b-8f87-4dbe-ba33-6e5ba8c5d846/scratchpad/snap/T_PaperBomb_BC.snap.png")

b = P.load_stored(SNAP)[..., :3]
L = P.luma_stored(b).astype(np.float64)
g = (np.abs(np.diff(L, axis=1, prepend=L[:, :1])) +
     np.abs(np.diff(L, axis=0, prepend=L[:1, :])))
e = PT.box_blur(g, 2)
print("e percentiles:", [round(float(np.percentile(e, p)) * 1000, 3)
                         for p in (1, 5, 10, 25, 50, 75, 90, 99)])
for thr_mult in (0.30, 0.40, 0.50):
    thr = thr_mult * float(np.percentile(e, 50))
    m = e > thr
    m[:, 936:] = False
    m = PT.P.close(m, 4)
    m = PT.P.open_(m, 2)
    lab, n = P.label_cc(m)
    st = [s for s in P.cc_stats(lab, n) if s]
    st.sort(key=lambda s: -s['area'])
    print(f"\nthr={thr*1000:.3f}e-3  n={n}  top areas:",
          [(s['area'], s['x0'], s['y0'], s['x1'], s['y1']) for s in st[:4]])
    if not st:
        continue
    cand = [s for s in st[:6] if s['area'] > 100000]
    cand.sort(key=lambda s: s['cx'])
    pick = cand[0]
    mm = (lab == pick['label'])
    inv = ~mm
    lab2, n2 = P.label_cc(inv)
    edge = set(np.unique(np.concatenate([lab2[0, :], lab2[-1, :], lab2[:, 0], lab2[:, -1]])))
    edge.discard(0)
    mm = ~np.isin(lab2, list(edge))
    rows = np.flatnonzero(mm.any(axis=1)); cols = np.flatnonzero(mm.any(axis=0))
    print("  filled island bbox x", cols[0], cols[-1], "y", rows[0], rows[-1],
          "-> w", cols[-1] - cols[0] + 1, "h", rows[-1] - rows[0] + 1,
          "aspect", round((cols[-1] - cols[0] + 1) / (rows[-1] - rows[0] + 1), 5))
    try:
        d = PT.fit_tag_quad(mm)
        q = d['quad']
        print("  quad tl", [round(v, 2) for v in q['tl']], "tr", [round(v, 2) for v in q['tr']],
              "br", [round(v, 2) for v in q['br']], "bl", [round(v, 2) for v in q['bl']])
        print("  rms", {k: round(v, 3) for k, v in d['side_fit_rms_px'].items()})
        W = 0.5 * (d['width_top_px'] + d['width_bottom_px'])
        Hh = 0.5 * (d['height_left_px'] + d['height_right_px'])
        print(f"  card {W:.2f} x {Hh:.2f} aspect {W/Hh:.5f} (true 0.44872)"
              f" ppmm x={W/70:.4f} y={Hh/156:.4f} aniso={Hh/156/(W/70):.4f}")
        wid = mm.sum(axis=1).astype(float)
        full = float(np.median(wid[int(rows[0] + 0.3 * len(rows)):int(rows[0] + 0.7 * len(rows))]))
        print("  chamfer top ratios:", [round(float(wid[rows[0] + i] / full), 3) for i in range(0, 140, 14)])
        print("  chamfer bot ratios:", [round(float(wid[rows[-1] - i] / full), 3) for i in range(0, 140, 14)])
    except Exception as ex:
        print("  quad fit failed:", ex)
