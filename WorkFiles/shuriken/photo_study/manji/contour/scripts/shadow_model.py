# Averaged edge-normal profiles per long coarse-contour segment -> locate the sharp metal step, fit scanner shadow vector.
import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *
px = np.load(BASE + "/manji_pixels.npy")
L = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
m = np.load(BASE + "/mask_solid.npy")
c = np.load(BASE + "/coarse_contour.npy")
idx = douglas_peucker(c, 6.0)
ts = np.arange(-70, 10.01, 0.5)
def dog(prof, sig=1.2, dt=0.5):
    r = int(4 * sig / dt); k = np.arange(-r, r + 1) * dt
    g = -k * np.exp(-0.5 * (k / sig) ** 2); g /= np.sum(np.abs(g) * np.abs(k))  # derivative kernel, unit slope response
    return np.convolve(prof, g[::-1], mode="same") / dt * 1.0
rows = []
for k in range(len(idx)):
    a, b = idx[k], idx[(k + 1) % len(idx)]
    p, q = c[a], c[b]; ln = np.hypot(*(q - p))
    if ln < 120: continue
    t = (q - p) / ln; n = np.array([t[1], -t[0]]); mid = (p + q) / 2
    if m[int(round(mid[1] + 8 * n[1])), int(round(mid[0] + 8 * n[0]))]: n = -n
    ss = np.linspace(0.2, 0.8, 80)
    prof = np.zeros(len(ts))
    for s in ss:
        base = p + s * (q - p)
        prof += bilinear(L, base[0] + ts * n[0], base[1] + ts * n[1])
    prof /= len(ss)
    g = dog(prof)
    valid = (ts > -66) & (ts < 6)
    ga = np.where(valid, np.abs(g), 0)
    # local maxima
    pk = [i for i in range(1, len(ga) - 1) if ga[i] >= ga[i - 1] and ga[i] >= ga[i + 1] and ga[i] > 0.01]
    pk.sort(key=lambda i: -ga[i])
    ang = float(np.degrees(np.arctan2(n[1], n[0])))
    top = [(float(ts[i]), round(float(g[i]), 3)) for i in pk[:3]]
    rows.append(dict(seg=k, len=float(ln), normal=[float(n[0]), float(n[1])], ang=ang, mid=[float(mid[0]), float(mid[1])], peaks=top))
    print(f"seg {k:3d} len {ln:5.0f} n_ang {ang:7.1f} mid ({mid[0]:5.0f},{mid[1]:5.0f}) peaks(t, dL/dt): {top}")
json.dump(rows, open(BASE + "/shadow_profiles.json", "w"), indent=1)
