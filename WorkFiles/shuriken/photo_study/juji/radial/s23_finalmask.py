"""Build the final silhouette mask from the refined outer edges + the junction region of the reference mask,
save mask PNG and an annotated debug overlay; locate the bright blobs inside the silhouette."""
import sys, os, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
names = ["right", "top", "left", "bottom"]
ref = np.load(os.path.join(jlib.OUT, "mask_ref.npy")).astype(bool)
g1 = json.load(open(os.path.join(jlib.OUT, "geom_ws_part1.json")))
c = np.array(g1["centre_candidates_px"]["sym90"])
summ = json.load(open(os.path.join(jlib.OUT, "summary.json")))
jp = json.load(open(os.path.join(jlib.OUT, "junction_panels.json")))
met = json.load(open(os.path.join(jlib.OUT, "metrics_outer.json")))

mask = np.zeros((H, W), bool)
yy, xx = np.mgrid[0:H, 0:W]
rad = np.hypot(xx - c[0], yy - c[1])
mask |= ref & (rad < 150)
for nm in names:
    z = np.load(os.path.join(jlib.OUT, "final_edges_outer_%s.npz" % nm))
    S, tL, tR, origin, u, n = z["S"], z["tL"], z["tR"], z["origin"], z["u"], z["n"]
    Sf = np.arange(S[0], S[-1], 0.25)
    tLf = np.interp(Sf, S, tL); tRf = np.interp(Sf, S, tR)
    for s, a1, b1 in zip(Sf, tLf, tRf):
        t = np.arange(b1, a1 + 0.25, 0.25)
        X = origin[0] + s * u[0] + t * n[0]
        Y = origin[1] + s * u[1] + t * n[1]
        ok = (X >= 0) & (X < W) & (Y >= 0) & (Y < H)
        mask[np.rint(Y[ok]).astype(int), np.rint(X[ok]).astype(int)] = True
mask = jlib.closing(mask, 2)
mask, holes = jlib.fill_holes(mask)
mask = jlib.largest_component(mask)
print("final mask px", mask.sum(), "holes", holes.sum(), "row0 px", mask[0].sum())
np.save(os.path.join(jlib.OUT, "mask_final.npy"), mask)
jlib.save_png(os.path.join(jlib.OUT, "mask_final.png"), mask)

# bright blobs inside
lum_s = jlib.gblur(a.mean(2), 1.5)
warm_s = jlib.gblur((a[:, :, 0] - a[:, :, 2]) / (a.sum(2) + 1e-3), 2.0)
bright = jlib.erode(mask, 3) & (lum_s > 0.36) & (warm_s < 0.06)
lab, nb = jlib.label(bright)
info = []
for k in range(1, nb + 1):
    ys, xs = np.nonzero(lab == k)
    if len(xs) >= 40:
        info.append({"px": int(len(xs)), "centroid": [round(float(xs.mean()), 1), round(float(ys.mean()), 1)],
                     "r_from_centre": round(float(np.hypot(xs.mean() - c[0], ys.mean() - c[1])), 1),
                     "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                     "median_lum": round(float(np.median(a.mean(2)[ys, xs])), 3)})
info.sort(key=lambda d: -d["px"])
print("bright (lid-coloured) blobs inside the silhouette:", json.dumps(info[:6]))
json.dump(info[:10], open(os.path.join(jlib.OUT, "bright_blobs.json"), "w"), indent=1)

# ---- annotated overlay ----
ov = a.copy() * 0.8 + 0.1
bd = jlib.boundary(mask)
ov[jlib.dilate(bd, 1)] = [0, 1, 0]
panel = np.load(os.path.join(jlib.OUT, "panel_mask.npy"))
ov[jlib.boundary(panel)] = [1, 0, 1]


def dot(x, y, col, r=4):
    ov[max(0, int(y) - r):int(y) + r + 1, max(0, int(x) - r):int(x) + r + 1] = col


def line(p0, p1, col):
    d = np.hypot(*(np.array(p1) - np.array(p0)))
    t = np.linspace(0, 1, int(d * 4) + 2)
    for tv in t:
        x = p0[0] + tv * (p1[0] - p0[0]); y = p0[1] + tv * (p1[1] - p0[1])
        if 0 <= int(y) < H and 0 <= int(x) < W:
            ov[int(y), int(x)] = col


dot(c[0], c[1], [1, 1, 0], 5)
for nm in names:
    z = np.load(os.path.join(jlib.OUT, "final_edges_outer_%s.npz" % nm))
    S, tL, tR, origin, u, n = z["S"], z["tL"], z["tR"], z["origin"], z["u"], z["n"]
    wp = summ["width_profile"]["outer"][nm]
    for st, col in ((wp["neck_station_px"], [0.2, 0.8, 1]), (wp["max_station_px"], [1, 0.4, 0])):
        i = int(np.argmin(np.abs(S - st)))
        p0 = origin + st * u + tL[i] * n
        p1 = origin + st * u + tR[i] * n
        line(p0, p1, col)
    t = summ["tips"][nm]
    if not t["clipped"]:
        dot(t["tip_xy"][0], t["tip_xy"][1], [1, 0, 0], 4)
    # axis
    line(origin + 60 * u, origin + (wp["R_tip_px"]) * u, [1, 1, 1])
for nt in jp["notches"]:
    dot(nt["notch_point"][0], nt["notch_point"][1], [0, 0.4, 1], 4)
jlib.save_png(os.path.join(jlib.OUT, "dbg_overlay_final.png"), ov)
print("saved overlay")
