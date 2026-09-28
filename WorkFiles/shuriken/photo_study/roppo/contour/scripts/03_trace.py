# Moore-neighbour trace of outer and hole contours, Douglas-Peucker simplification (eps 1.5 px).
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from util import *
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = np.load(os.path.join(OUT, "seg.npz"))
piece, hole = d["piece"], d["hole"]
outer = moore_trace(piece)
hc = moore_trace(hole)
# sanity: every traced pixel is a boundary pixel of its region
def is_boundary(m, pts):
    H, W = m.shape
    ok = 0
    for x, y in pts.astype(int):
        nb = m[max(y-1,0):y+2, max(x-1,0):x+2]
        ok += (m[y, x] and (not nb.all() or y in (0, H-1)))
    return ok / len(pts)
print("outer pts", len(outer), "boundary frac", is_boundary(piece, outer))
print("hole pts", len(hc), "boundary frac", is_boundary(hole, hc))
# signed area (shoelace) to report orientation
def area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * (x * np.roll(y, -1) - np.roll(x, -1) * y).sum()
print("outer area", area(outer), "mask px", piece.sum(), "hole area", area(hc), "hole px", hole.sum())
io = douglas_peucker(outer, 1.5)
ih = douglas_peucker(hc, 1.5)
print("DP vertices outer", len(io), "hole", len(ih))
np.savez(os.path.join(OUT, "contours.npz"), outer=outer, hole=hc, dp_outer=io, dp_hole=ih)
v = outer[io]
seg = np.linalg.norm(np.roll(v, -1, 0) - v, axis=1)
for k in range(len(io)):
    if seg[k] > 25:
        print(f"  seg {k}: idx {io[k]} ({v[k][0]:.0f},{v[k][1]:.0f}) -> ({v[(k+1)%len(v)][0]:.0f},{v[(k+1)%len(v)][1]:.0f}) len {seg[k]:.1f}")
