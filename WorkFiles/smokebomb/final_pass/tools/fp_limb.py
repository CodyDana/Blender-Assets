"""fp_limb BALLJSON a0 a1: who owns the outline between image angles a0..a1 and the radius per 0.25 deg."""
import sys, json, dataclasses
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import smokebomb_ball as SB
spec = dataclasses.replace(SB.BALL, **json.loads(sys.argv[1]))
ball = SB.Ball(spec, log=lambda *a: None).build()
a0, a1 = float(sys.argv[2]), float(sys.argv[3])
nb = int((a1 - a0) / 0.25)
best = np.full(nb, -np.inf); own = np.full(nb, -1)
for st in ball.stretches:
    if not st.exposed.any():
        continue
    Q, u, a = SB._exposed_top_points(ball, st, 1)
    th = np.degrees(np.arctan2(Q[:, 2], Q[:, 0])) % 360
    r = np.hypot(Q[:, 0], Q[:, 2])
    m = (th >= a0) & (th < a1)
    b = ((th[m] - a0) / 0.25).astype(int)
    for bi, rr in zip(b, r[m]):
        if rr > best[bi]:
            best[bi] = rr; own[bi] = st.index
px = 464.07 / spec.outline_mm
prev = None
for i in range(nb):
    k = own[i]
    nm = ball.stretches[k].key if k >= 0 else "-"
    if nm != prev or i % 8 == 0:
        print(f"{a0 + i * 0.25:7.2f} {nm:10s} r={best[i]:.3f} ({(best[i] - spec.outline_mm) * px:+.1f}px)")
    prev = nm
