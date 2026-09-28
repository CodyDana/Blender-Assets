# -*- coding: utf-8 -*-
"""Register the shipped atlas against the art map by ink-profile correlation."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pbmetro as P

ART = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/art/paperbomb_front_bc.png"
ATL = r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png"

a = P.load_stored(ART)[..., :3]
b = P.load_stored(ATL)[..., :3]
La, Lb = P.luma_stored(a), P.luma_stored(b)
# ink = anything meaningfully darker than paper, in each image's own terms
def inkmask(L):
    p = float(np.percentile(L, 75))
    fl = float(np.percentile(L, 0.5))
    return (L < 0.5 * (p + fl)).astype(np.float64)
ma = inkmask(La)
mb = inkmask(Lb)
mb[:, 930:] = 0.0

def moments(m, axis):
    p = m.sum(axis=axis)
    i = np.arange(len(p), dtype=np.float64)
    s = p.sum()
    mu = float((p * i).sum() / s)
    sd = float(np.sqrt((p * (i - mu) ** 2).sum() / s))
    return p, mu, sd

pax, mux, sdx = moments(ma, 0)
pbx, mubx, sdbx = moments(mb, 0)
pay, muy, sdy = moments(ma, 1)
pby, muby, sdby = moments(mb, 1)
print(f"art  ink x mean={mux:.2f} sd={sdx:.2f}   y mean={muy:.2f} sd={sdy:.2f}")
print(f"atl  ink x mean={mubx:.2f} sd={sdbx:.2f}   y mean={muby:.2f} sd={sdby:.2f}")
sx0 = sdbx / sdx; tx0 = mubx - sx0 * mux
sy0 = sdby / sdy; ty0 = muby - sy0 * muy
print(f"moment affine: sx={sx0:.6f} tx={tx0:.3f}   sy={sy0:.6f} ty={ty0:.3f}")


def refine(pa, pb, s0, t0, srange=0.06, trange=40.0):
    na = len(pa)
    i = np.arange(na, dtype=np.float64)
    pa_ = pa - pa.mean()
    best = (-2, s0, t0)
    for s in np.linspace(s0 - srange, s0 + srange, 121):
        for t in np.linspace(t0 - trange, t0 + trange, 161):
            pos = s * i + t
            k = np.clip(pos.astype(int), 0, len(pb) - 2)
            f = pos - k
            v = pb[k] * (1 - f) + pb[k + 1] * f
            v_ = v - v.mean()
            d = np.sqrt((pa_ ** 2).sum() * (v_ ** 2).sum())
            c = float((pa_ * v_).sum() / d) if d > 0 else -2
            if c > best[0]:
                best = (c, s, t)
    return best

cx, sx, tx = refine(pax, pbx, sx0, tx0)
cy, sy, ty = refine(pay, pby, sy0, ty0)
print(f"refined X corr={cx:.5f} sx={sx:.6f} tx={tx:.3f}")
print(f"refined Y corr={cy:.5f} sy={sy:.6f} ty={ty:.3f}")

ppmm, pad = 12.923, 1.6
x0, y0, w, h = pad * ppmm, pad * ppmm, 70.0 * ppmm, 156.0 * ppmm
print(f"art card rect x0={x0:.2f} y0={y0:.2f} w={w:.2f} h={h:.2f}")
ax0, ay0, aw, ah = x0 * sx + tx, y0 * sy + ty, w * sx, h * sy
print(f"ATLAS card rect x0={ax0:.2f} y0={ay0:.2f} w={aw:.2f} h={ah:.2f}"
      f"  (x1={ax0+aw:.2f} y1={ay0+ah:.2f})  ppmm x={aw/70:.4f} y={ah/156:.4f}")

# sanity: luma across the implied atlas card edges
for x in range(int(ax0) - 8, int(ax0) + 9, 2):
    print(f"   atlas col {x}: luma mean {float(Lb[:, x].mean()):.4f}")
print("   ---")
for x in range(int(ax0 + aw) - 8, int(ax0 + aw) + 9, 2):
    print(f"   atlas col {x}: luma mean {float(Lb[:, x].mean()):.4f}")
