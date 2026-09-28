"""Resolve the tip-angle disagreement: measure the apparent tip angle as a
function of the line-fit window, and compare with the closed form implied by a
circular-arc side of the reconciled sagitta."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from rc_common import fit_line_tls, line_intersect, OUT

d = np.load(os.path.join(OUT, 'reconcile', 'edge_points.npz'))
J = json.load(open(os.path.join(OUT, 'reconcile', 'rc_measure2.json')))
cx, cy = J['c4']['centre']; rot = np.radians(J['c4']['rot_deg'])
side = J['c4']['side_px']; s = J['c4']['sagitta_px']; Rd = J['c4']['diag_px'] / 2

# model corners
corners = {}
for k, name in enumerate(('BR', 'BL', 'TL', 'TR')):
    pass
ang = {'TL': 225, 'TR': 315, 'BR': 45, 'BL': 135}
C = {n: np.array([cx + Rd * np.cos(rot + np.radians(a)),
                  cy + Rd * np.sin(rot + np.radians(a))]) for n, a in ang.items()}
print("model corners:", {n: (round(p[0], 2), round(p[1], 2)) for n, p in C.items()})

R = side * side / (8 * s) + s / 2
print(f"arc radius R = {R:.1f} px  (R/c = {R/side:.3f})")
apex_tangent = 90.0 - 4 * np.degrees(np.arctan(2 * s / side))
print(f"apex tangent tip angle = {apex_tangent:.2f} deg")

SIDES = {'bottom': ('BL', 'BR'), 'top': ('TL', 'TR'),
         'left': ('TL', 'BL'), 'right': ('TR', 'BR')}
PT = {'bottom': d['bottom'], 'top': d['top'], 'left': d['left']}

print("\nwindow   measured tip angle per corner (deg)          mean   arc-model")
for (lo, hi) in ((10, 40), (15, 60), (20, 100), (40, 160)):
    vals = []
    for cn in ('TL', 'BL', 'BR', 'TR'):
        dirs = []
        for sname, (a, b) in SIDES.items():
            if cn not in (a, b) or sname not in PT:
                continue
            P = PT[sname]
            r = np.hypot(P[:, 0] - C[cn][0], P[:, 1] - C[cn][1])
            sel = P[(r >= lo) & (r <= hi)]
            if len(sel) < 6:
                continue
            _, dd, _ = fit_line_tls(sel)
            v = dd if np.dot(dd, sel.mean(0) - C[cn]) > 0 else -dd
            dirs.append(v)
        if len(dirs) == 2:
            a_ = np.degrees(np.arccos(np.clip(np.dot(dirs[0], dirs[1]), -1, 1)))
            vals.append((cn, a_))
    model = apex_tangent + 2 * np.degrees((lo + hi) / 2.0 / R)
    txt = "  ".join(f"{cn}:{v:5.2f}" for cn, v in vals)
    mean = np.mean([v for _, v in vals]) if vals else float('nan')
    print(f"{lo:3d}-{hi:3d}  {txt:44s}  {mean:6.2f}   {model:6.2f}")

# tip sharpness: how far the real boundary sits from the model corner
print("\ntip sharpness: distance from the model corner to the nearest measured")
print("boundary point on each adjacent side (should be ~0 for a sharp corner)")
for cn in ('TL', 'BL', 'BR'):
    ds = []
    for sname in PT:
        P = PT[sname]
        r = np.hypot(P[:, 0] - C[cn][0], P[:, 1] - C[cn][1])
        if r.min() < 40:
            ds.append(r.min())
    print(f"  {cn}: closest measured boundary point {min(ds):.2f} px from the model corner"
          if ds else f"  {cn}: n/a")
