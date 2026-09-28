"""QA + summary: r(theta) plot, extrema from r(theta), symmetry, hole check, ratios."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import imglib as L

OUT = os.path.dirname(os.path.abspath(__file__))
res = json.load(open(os.path.join(OUT, "results.json")))
G = json.load(open(os.path.join(OUT, "geom.json")))
th, r = np.load(os.path.join(OUT, "r_theta.npy"))
lum = np.load(os.path.join(OUT, "lum.npy"))
mask = np.load(os.path.join(OUT, "mask_final.npy"))
C = np.array(res["centre_px"])
span = res["span_px"]

# ---- r(theta) extrema ----
per = 450  # 45 deg in 0.1 deg steps
maxima, minima = [], []
for k in range(8):
    lo = int(k * per); hi = int((k + 1) * per)
    seg = np.concatenate([r, r])[lo:hi]
    pass
rr = r.copy()
sm = np.convolve(np.concatenate([rr[-50:], rr, rr[:50]]), np.ones(9) / 9, "same")[50:-50]
for i in range(len(rr)):
    w = sm[[(i + j) % len(rr) for j in range(-120, 121)]]
    if sm[i] == w.max() and (not maxima or (i - maxima[-1]) % len(rr) > 150):
        maxima.append(i)
    if sm[i] == w.min() and (not minima or (i - minima[-1]) % len(rr) > 150):
        minima.append(i)
rmax = np.array([r[i] for i in maxima]); rmin = np.array([r[i] for i in minima])
print("r(theta) maxima: n=%d  r %s  mean %.1f sd %.1f" % (len(maxima), ["%.0f" % v for v in rmax], rmax.mean(), rmax.std()))
print("r(theta) minima: n=%d  r %s  mean %.1f sd %.1f" % (len(minima), ["%.0f" % v for v in rmin], rmin.mean(), rmin.std()))
print("max/min angles: %s | %s" % (["%.1f" % th[i] for i in maxima], ["%.1f" % th[i] for i in minima]))
print("r(theta) actual-outline ratio min/max = %.4f" % (rmin.mean() / rmax.mean()))

# ---- symmetry of r(theta) ----
for k in (1, 2, 4):
    sh = int(k * 45 / 0.1)
    d = r - np.roll(r, sh)
    print("rotation by %2d x 45 deg: rms %.2f px (%.4f of span), max %.1f" % (k, np.sqrt((d ** 2).mean()), np.sqrt((d ** 2).mean()) / span, np.abs(d).max()))
F = np.abs(np.fft.rfft(r - r.mean())) / len(r) * 2
print("harmonic amplitudes (px): " + " ".join("k%d %.1f" % (k, F[k]) for k in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 24, 32)))

# ---- hole check on the metal core ----
core = L.closing(lum < 0.45, 3)
lab, sizes = L.label(core)
big = max(sizes, key=sizes.get)
piece = lab == big
blab, bs = L.label(~piece)
edge_labels = set(np.unique(np.concatenate([blab[0], blab[-1], blab[:, 0], blab[:, -1]]))) - {0}
holes = sorted([v for k, v in bs.items() if k not in edge_labels], reverse=True)
print("enclosed non-metal regions inside the piece (px): %s" % holes[:10])
inner = np.zeros_like(mask)
yy, xx = np.mgrid[0:mask.shape[0], 0:mask.shape[1]]
rad = np.hypot(xx - C[0], yy - C[1])
sel = rad < 0.35 * span / 2
print("centre disc (r < %.0f px): mask coverage %.4f, min lum %.3f, mean lum %.3f" %
      (0.35 * span / 2, mask[sel].mean(), lum[sel].min(), lum[sel].mean()))

# ---- plot r(theta) ----
Wp, Hp = 1440, 480
img = np.ones((Hp, Wp, 3), np.float32)
rmaxp, rminp = 700.0, 250.0
def xy(t, rv):
    return int(t / 360 * (Wp - 1)), int(Hp - 1 - (rv - rminp) / (rmaxp - rminp) * (Hp - 1))
for gl in range(250, 701, 50):
    y = xy(0, gl)[1]
    img[y, :] = 0.85
    if gl % 100 == 0:
        img[y, :] = 0.7
for t in range(0, 361, 45):
    x = xy(t, 0)[0]
    img[:, min(x, Wp - 1)] = 0.85
prev = None
for i in range(len(r)):
    p = xy(th[i], r[i])
    if prev:
        y0, y1 = sorted((prev[1], p[1]))
        img[max(y0, 0):min(y1 + 1, Hp), np.clip(p[0], 0, Wp - 1)] = [0.8, 0.1, 0.1]
    prev = p
for v in res["tips"]:
    x, y = xy(v["theta"], v["r_virtual"])
    img[max(y - 4, 0):y + 5, max(x - 1, 0):x + 2] = [0, 0.4, 1]
for v in res["notches"]:
    x, y = xy(v["theta"], v["r_virtual"])
    img[max(y - 4, 0):y + 5, max(x - 1, 0):x + 2] = [0, 0.6, 0]
L.save_png(os.path.join(OUT, "r_theta_plot.png"), img)
print("wrote r_theta_plot.png (x: theta 0-360 deg, y: r 250-700 px; blue = virtual tip, green = virtual notch)")

# ---- summary ratios ----
tips = res["tips"]; nots = res["notches"]
tr = np.array([v["r_virtual"] for v in tips]); nr = np.array([v["r_virtual"] for v in nots])
ta = np.array([v["angle"] for v in tips]); na = np.array([v["angle"] for v in nots])
print("\n--- ratios to span (%.1f px) ---" % span)
print("tip radius   %.4f +- %.4f" % ((tr / span).mean(), (tr / span).std()))
print("notch radius %.4f +- %.4f   (of span)  ; notch/tip = %.4f +- %.4f" %
      ((nr / span).mean(), (nr / span).std(), (nr / tr.mean()).mean(), (nr / tr.mean()).std()))
print("actual outline: tip %.4f  notch %.4f of span" % (rmax.mean() / span, rmin.mean() / span))
print("tip angle %.2f +- %.2f (range %.1f-%.1f)" % (ta.mean(), ta.std(), ta.min(), ta.max()))
print("notch angle %.2f +- %.2f (range %.1f-%.1f)" % (na.mean(), na.std(), na.min(), na.max()))
sub = [v for v in tips if v["name"] not in ("T_SSW", "T_SSE")]
sa = np.array([v["angle"] for v in sub])
print("tip angle without the two odd points (T_SSW, T_SSE): %.2f +- %.2f" % (sa.mean(), sa.std()))
print("edge straightness: rms %s px" % ["%.2f" % e["rms_px"] for e in res["edges"]])
print("edge sagitta: %s px over fit lengths %s" % (["%+.1f" % e["sagitta_px"] for e in res["edges"]],
                                                   ["%.0f" % e["fit_len_px"] for e in res["edges"]]))
