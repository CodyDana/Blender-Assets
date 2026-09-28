"""Hole: separate the BORE boundary (edge of the bright aperture) from the outer
edge of the dark rim ring (where the flat plate face begins)."""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rio

IMG = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Roppo.JPG"
SDIR = np.array([np.cos(np.radians(305.0)), np.sin(np.radians(305.0))])
rgb = rio.load_rgb(IMG)
H, W, _ = rgb.shape
L = rio.lum(rgb)
Lb = rio.blur(L, 0.8)

cx, cy = 630.7, 527.0
step = 0.2
for it in range(6):
    rows = []
    for a in np.arange(0, 360, 0.5):
        th = np.radians(a)
        ux, uy = np.cos(th), np.sin(th)
        rr = np.arange(90, 175, step)
        v = rio.sample(Lb, cx + ux * rr, cy + uy * rr)
        # disc level: median 25..12 px inside the current radius estimate
        rest = 135.0
        disc = np.median(v[(rr > rest - 30) & (rr < rest - 15)])
        # ring floor: minimum within +-12 px of the estimate, outside the disc
        seg = (rr > rest - 6) & (rr < rest + 16)
        floor = float(np.min(v[seg]))
        mid = 0.5 * (disc + floor)
        j = np.flatnonzero((rr > rest - 20) & (v < mid))
        if not len(j):
            continue
        j0 = j[0]
        v0, v1 = v[j0 - 1], v[j0]
        rb = rr[j0 - 1] + (mid - v0) / (v1 - v0) * step
        rows.append((a, rb, float(np.array([ux, uy]) @ SDIR), disc, floor))
    pts = np.array(rows)
    m = pts[:, 2] > -0.15
    x = cx + np.cos(np.radians(pts[m, 0])) * pts[m, 1]
    y = cy + np.sin(np.radians(pts[m, 0])) * pts[m, 1]
    keep = np.ones(len(x), bool)
    for _ in range(4):
        ncx, ncy, nr, rms = rio.fit_circle(x[keep], y[keep])
        d = np.hypot(x - ncx, y - ncy) - nr
        keep = np.abs(d) < max(1.5, 3 * rms)
    if abs(ncx - cx) < 0.02 and abs(ncy - cy) < 0.02:
        cx, cy = ncx, ncy
        break
    cx, cy = ncx, ncy

out = {}
xs = cx + np.cos(np.radians(pts[:, 0])) * pts[:, 1]
ys = cy + np.sin(np.radians(pts[:, 0])) * pts[:, 1]
for tag, m in (("litneutral", pts[:, 2] > -0.15), ("lit", pts[:, 2] > 0.35),
               ("all", np.ones(len(pts), bool))):
    x, y = xs[m], ys[m]
    keep = np.ones(len(x), bool)
    for _ in range(4):
        a_, b_, r_, rms_ = rio.fit_circle(x[keep], y[keep])
        d = np.hypot(x - a_, y - b_) - r_
        keep = np.abs(d) < max(1.5, 3 * rms_)
    out[tag] = dict(cx=a_, cy=b_, r=r_, rms=rms_, n=int(m.sum()), nkeep=int(keep.sum()))
m = pts[:, 2] > -0.15
out['ellipse_litneutral'] = rio.fit_ellipse(xs[m], ys[m])
BORE = out['litneutral']
bc = np.array([BORE['cx'], BORE['cy']])
sect = {}
for a0 in range(0, 360, 30):
    mm = (pts[:, 0] >= a0) & (pts[:, 0] < a0 + 30)
    d = np.hypot(xs[mm] - bc[0], ys[mm] - bc[1]) - BORE['r']
    sect[a0] = [round(float(np.median(d)), 2), round(float(np.median(pts[mm, 2])), 2)]
out['sector_resid'] = sect
# chord diameters through directions perpendicular to the shadow (unbiased by centre)
ch = []
for a in np.arange(0, 180, 0.5):
    u = np.array([np.cos(np.radians(a)), np.sin(np.radians(a))])
    if abs(u @ SDIR) > 0.25:
        continue
    r1 = pts[np.argmin(np.abs(pts[:, 0] - a)), 1]
    r2 = pts[np.argmin(np.abs(pts[:, 0] - (a + 180)))][1]
    ch.append(r1 + r2)
out['neutral_chord_mean'] = float(np.mean(ch))
out['neutral_chord_sd'] = float(np.std(ch))
out['n_neutral_chords'] = len(ch)

# how far out does the dark rim ring go? (outer boundary = where the flat face starts)
ring = []
for a in np.arange(0, 360, 1.0):
    th = np.radians(a)
    ux, uy = np.cos(th), np.sin(th)
    rr = np.arange(120, 175, step)
    v = rio.sample(Lb, cx + ux * rr, cy + uy * rr)
    floor = float(np.min(v[(rr > 133) & (rr < 150)]))
    plate = float(np.median(v[(rr > 158) & (rr < 172)]))
    if plate - floor < 0.03:
        continue
    lev = floor + 0.5 * (plate - floor)
    j = np.flatnonzero((rr > 136) & (v > lev))
    if not len(j):
        continue
    j0 = j[0]
    v0, v1 = v[j0 - 1], v[j0]
    ro = rr[j0 - 1] + (lev - v0) / (v1 - v0) * step
    ring.append((a, ro, float(np.array([ux, uy]) @ SDIR), plate - floor))
ring = np.array(ring)
m = ring[:, 2] > -0.15
xr = cx + np.cos(np.radians(ring[m, 0])) * ring[m, 1]
yr = cy + np.sin(np.radians(ring[m, 0])) * ring[m, 1]
a_, b_, r_, rms_ = rio.fit_circle(xr, yr)
out['ring_outer'] = dict(cx=a_, cy=b_, r=r_, rms=rms_, n=int(m.sum()))
out['ring_width_median'] = float(np.median(ring[m, 1] - np.interp(ring[m, 0], pts[:, 0], pts[:, 1])))
json.dump(out, open(os.path.join(HERE, "bore.json"), "w"), indent=1)
np.save(os.path.join(HERE, "bore_pts.npy"), pts)
print("BORE", BORE)
print("lit", out['lit'], "all", out['all'])
print("ellipse", {k: round(v, 4) for k, v in out['ellipse_litneutral'].items()})
print("neutral chord", out['neutral_chord_mean'], "+-", out['neutral_chord_sd'], out['n_neutral_chords'])
print("sector", sect)
print("ring outer", out['ring_outer'], "width", out['ring_width_median'])
