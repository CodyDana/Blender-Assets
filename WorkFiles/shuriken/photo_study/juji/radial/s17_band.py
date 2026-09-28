"""Map the near-black band just inside the watershed silhouette: thickness vs position and edge normal.

For every silhouette pixel, step inward along the inward normal (from the gradient of the blurred mask)
and measure the contiguous run of lum < LT starting within 4 px of the edge. Writes an overlay where the
band thickness is colour coded, and prints thickness statistics by outward-normal direction and by region.
"""
import sys, os, math, json
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
lum = jlib.gblur(a.mean(2), 0.8)
m = np.load(os.path.join(jlib.OUT, "mask_final_ws.npy")).astype(bool)
mf = jlib.gblur(m.astype(np.float32), 3.0)
gy, gx = np.gradient(mf)
bd = jlib.boundary(m)
ys, xs = np.nonzero(bd)
LT = float(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else 0.12
c = np.array(json.load(open(os.path.join(jlib.OUT, "geom_ws_part1.json")))["centre_candidates_px"]["sym90"])
rows = []
tt = np.arange(0, 40, 0.5)
for y, x in zip(ys, xs):
    g = np.array([gx[y, x], gy[y, x]])
    nrm = np.linalg.norm(g)
    if nrm < 1e-4:
        continue
    inward = g / nrm            # gradient of mask points inward
    P = np.array([x, y])[None, :] + tt[:, None] * inward[None, :]
    L = jlib.bilinear(lum, P[:, 0], P[:, 1])
    k0 = np.nonzero((tt <= 4) & (L < LT))[0]
    thick = 0.0
    if len(k0):
        k = k0[0]
        while k + 1 < len(tt) and L[k + 1] < LT:
            k += 1
        thick = tt[k] - tt[k0[0]] + 0.5
    outward = -inward
    ang = math.degrees(math.atan2(-outward[1], outward[0])) % 360   # CCW from +x, y up
    rows.append((x, y, ang, thick))
rows = np.array(rows)
np.save(os.path.join(jlib.OUT, "band_map.npy"), rows)
print("LT", LT, "boundary px", len(rows))
print("outward-normal sector (deg, y up): median/p75/max band thickness px, fraction with band>=3px")
for b0 in range(0, 360, 30):
    sel = (rows[:, 2] >= b0) & (rows[:, 2] < b0 + 30)
    t = rows[sel, 3]
    print("%3d-%3d  N %5d  med %4.1f  p75 %4.1f  max %4.1f  frac %.2f" % (b0, b0 + 30, sel.sum(), np.median(t), np.percentile(t, 75), t.max(), (t >= 3).mean()))
# regions: which arm / fillet (by polar angle of the boundary point about the centre) for up-facing normals
pa = (np.degrees(np.arctan2(-(rows[:, 1] - c[1]), rows[:, 0] - c[0]))) % 360
r = np.hypot(rows[:, 0] - c[0], rows[:, 1] - c[1])
print("\nup-facing (normal 45-135) boundary points by polar position:")
up = (rows[:, 2] >= 45) & (rows[:, 2] <= 135)
for lo, hi, name in ((350, 370, "right arm"), (20, 70, "fillet R-T"), (70, 110, "top arm"), (110, 160, "fillet T-L"), (160, 200, "left arm")):
    pp = pa.copy(); pp[pp < 10] += 360 if lo >= 350 else 0
    sel = up & (pp >= lo) & (pp < hi)
    if sel.sum():
        t = rows[sel, 3]
        print("  %-11s N %4d  med %4.1f  p90 %4.1f  frac>=3 %.2f" % (name, sel.sum(), np.median(t), np.percentile(t, 90), (t >= 3).mean()))
# thickness along the right and left arms' upper edges vs x
for name, xr in (("right arm upper edge", range(780, 1340, 40)), ("left arm upper edge", range(60, 600, 40))):
    print(name)
    for x0 in xr:
        sel = up & (rows[:, 0] >= x0) & (rows[:, 0] < x0 + 40) & (np.abs(rows[:, 1] - c[1]) < 120)
        if sel.sum():
            print("   x %4d-%4d  N %3d  band med %4.1f  (y ~%d)" % (x0, x0 + 40, sel.sum(), np.median(rows[sel, 3]), np.median(rows[sel, 1])))
ov = a.copy() * 0.85
for x, y, ang, t in rows:
    col = [0, 1, 0] if t < 3 else ([1, 1, 0] if t < 8 else ([1, 0.5, 0] if t < 14 else [1, 0, 0]))
    ov[int(y), int(x)] = col
jlib.save_png(os.path.join(jlib.OUT, "dbg_band_overlay.png"), ov)
