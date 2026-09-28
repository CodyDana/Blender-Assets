"""Characterise the edge transition on each side of each arm (sharp vs soft, black band present?).

For each arm and station, colour profiles are sampled along the perpendicular through the watershed edge
(averaged over a 5-px strip along the arm). With B = median colour 28..40 px outside the edge and
O = median colour 6..14 px inside, f(t) = (c(t)-B).(O-B)/|O-B|^2. Reported: t where f first reaches
0.1/0.5/0.9 coming from outside (t>0 outside, relative to the watershed edge), the 10-90 rise width,
and the minimum luminance in the 20 px inside the edge (a black band shows up as lum < 0.12).
"""
import sys, os, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
ab = jlib.gblur(a, 0.7)
lum = ab.mean(2)
tag = "ws"
names = ["right", "top", "left", "bottom"]
out = {}
for nme in names:
    d = np.load(os.path.join(jlib.OUT, "arm_%s_%s.npz" % (tag, nme)))
    prof, u, n, origin = d["prof"], d["u"], d["n"], d["origin"]
    R = prof[np.isfinite(prof[:, 1]), 0].max()
    rows = []
    for s in np.arange(240, R - 25, 5.0):
        i = int(np.argmin(np.abs(prof[:, 0] - s)))
        for side, te in (("L", prof[i, 1]), ("R", prof[i, 2])):
            if not np.isfinite(te):
                continue
            sgn = 1.0 if side == "L" else -1.0
            tt = np.arange(-24, 44.01, 0.5)           # relative, positive = outward
            acc = np.zeros((len(tt), 3))
            for ds in (-2, -1, 0, 1, 2):
                P = origin[None, :] + (s + ds) * u[None, :] + (te + sgn * tt)[:, None] * n[None, :]
                acc += jlib.bilinear(ab, P[:, 0], P[:, 1])
            col = acc / 5
            B = np.median(col[(tt >= 28) & (tt <= 40)], 0)
            O = np.median(col[(tt >= -14) & (tt <= -6)], 0)
            v = O - B
            den = float(np.dot(v, v))
            if den < 0.03 ** 2:
                continue
            f = (col - B) @ v / den
            # coming from outside inward: first crossing of level
            order = np.argsort(-tt)
            def cross(level):
                ff = f[order]; t2 = tt[order]
                j = np.argmax(ff >= level)
                if ff[j] < level:
                    return np.nan
                if j == 0:
                    return t2[0]
                fa, fb = ff[j - 1], ff[j]
                return t2[j - 1] + (level - fa) / (fb - fa) * (t2[j] - t2[j - 1])
            t10, t50, t90 = cross(0.1), cross(0.5), cross(0.9)
            L = col.mean(1)
            inner = L[(tt >= -20) & (tt <= 2)]
            P0 = origin + s * u + te * n
            # outward normal in image coords (for the shadow-direction model)
            nout = sgn * n
            rows.append(dict(s=float(s), side=side, t10=t10, t50=t50, t90=t90, rise=t10 - t90,
                             minlum_inside=float(inner.min()), contrast=math.sqrt(den),
                             x=float(P0[0]), y=float(P0[1]), nx=float(nout[0]), ny=float(nout[1])))
    out[nme] = rows

json.dump(out, open(os.path.join(jlib.OUT, "edgeprofiles_%s.json" % tag), "w"))
print("arm side  n_out(x,y)     N   rise10-90 med  t50 med  t10 med t90 med  frac(minlum<0.12)  contrast")
for nme in names:
    rows = out[nme]
    for side in ("L", "R"):
        rs = [r for r in rows if r["side"] == side and np.isfinite(r["rise"])]
        if not rs:
            continue
        nx = np.median([r["nx"] for r in rs]); ny = np.median([r["ny"] for r in rs])
        print("%-6s %s   (%5.2f,%5.2f)  %3d   %6.1f        %6.1f  %6.1f  %6.1f   %.2f   %.3f" % (
            nme, side, nx, ny, len(rs), np.median([r["rise"] for r in rs]), np.median([r["t50"] for r in rs]),
            np.median([r["t10"] for r in rs]), np.median([r["t90"] for r in rs]),
            np.mean([r["minlum_inside"] < 0.12 for r in rs]), np.median([r["contrast"] for r in rs])))
# rise vs normal direction: bin by outward-normal angle
allr = [r for nme in names for r in out[nme] if np.isfinite(r["rise"])]
ang = np.array([math.degrees(math.atan2(-r["ny"], r["nx"])) % 360 for r in allr])  # CCW from +x, y up
rise = np.array([r["rise"] for r in allr])
mb = np.array([r["minlum_inside"] < 0.12 for r in allr])
print("\noutward-normal direction (deg, CCW from +x, y up) -> median 10-90 rise (px), black-band fraction, N")
for b0 in range(0, 360, 30):
    sel = (ang >= b0) & (ang < b0 + 30)
    if sel.sum():
        print("%3d-%3d  rise %5.1f   band %.2f   N %d" % (b0, b0 + 30, np.median(rise[sel]), mb[sel].mean(), sel.sum()))
