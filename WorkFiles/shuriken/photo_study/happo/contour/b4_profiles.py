# Method B step 4: per-edge normal profiles relative to the first-pass chord (tip -> notch of Otsu contour)
# saves profiles.npz and prints mean profile per edge
import numpy as np, os, json
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour"
L = np.load(os.path.join(OUT, "Ls.npy")).astype(np.float64)   # sigma 1.2 smoothed luminance
rgb = np.load(os.path.join(OUT, "rgb.npy")).astype(np.float64)
S = np.load(os.path.join(OUT, "S.npy")).astype(np.float64)
info = json.load(open(os.path.join(OUT, "b3_contour_mask_filled.json")))
cx, cy = info["centroid"]
tips = [(t["x"], t["y"]) for t in info["tips"]]
notches = [(n["x"], n["y"]) for n in info["notches"]]
H, W = L.shape

def bil(A, x, y):
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = x - x0; fy = y - y0
    return (A[y0, x0] * (1 - fx) * (1 - fy) + A[y0, x0 + 1] * fx * (1 - fy) + A[y0 + 1, x0] * (1 - fx) * fy + A[y0 + 1, x0 + 1] * fx * fy)

edges = []
# edge k: 2k = tip k -> notch k (notch k lies between tip k and tip k+1), 2k+1 = tip k+1 -> notch k
for k in range(8):
    edges.append(dict(name="T%d-N%d" % (k, k), tip=k, notch=k, A=tips[k], B=notches[k]))
    edges.append(dict(name="T%d-N%d" % ((k + 1) % 8, k), tip=(k + 1) % 8, notch=k, A=tips[(k + 1) % 8], B=notches[k]))

TS = np.arange(-45, 25.01, 0.25)
SS = np.arange(-5, 5.01, 1.0)
allprof = {}
for e in edges:
    A = np.array(e["A"]); B = np.array(e["B"])
    d = B - A; Ln = np.hypot(*d); u = d / Ln
    n = np.array([u[1], -u[0]])
    mid = (A + B) / 2
    if np.dot(mid - np.array([cx, cy]), n) < 0: n = -n     # outward
    e["u"] = u.tolist(); e["n"] = n.tolist(); e["len"] = float(Ln)
    stations = np.arange(0.30, 0.901, 0.01) * Ln
    prof = np.zeros((len(stations), len(TS))); profS = np.zeros_like(prof)
    for i, s in enumerate(stations):
        base = A + u * s
        xs = base[0] + TS[None, :] * n[0] + SS[:, None] * u[0]
        ys = base[1] + TS[None, :] * n[1] + SS[:, None] * u[1]
        prof[i] = bil(L, xs, ys).mean(0)
        profS[i] = bil(S, xs, ys).mean(0)
    allprof[e["name"]] = (stations, prof, profS)
    print("== %s len %.0f n=(%.2f,%.2f)" % (e["name"], Ln, n[0], n[1]))
    for g0 in (5, 30, 55):
        mp = prof[g0:g0 + 6].mean(0)
        row = ["%+d:%.2f" % (t, mp[j]) for j, t in enumerate(TS) if abs(t - round(t)) < 1e-6 and int(round(t)) % 2 == 0]
        print("  @%.0f%%: " % (30 + g0 + 3) + " ".join(row))
np.savez(os.path.join(OUT, "profiles.npz"), TS=TS, **{k + "_st": v[0] for k, v in allprof.items()},
         **{k + "_L": v[1] for k, v in allprof.items()}, **{k + "_S": v[2] for k, v in allprof.items()})
json.dump(edges, open(os.path.join(OUT, "b4_edges.json"), "w"), indent=1)
