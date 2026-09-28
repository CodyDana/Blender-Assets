# Debug overlays: full-image overlay of contours + fitted primitives, junction mosaic, tip mosaic.
import sys, os, pickle
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from util import *
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a = np.load(os.path.join(OUT, "roppo_rgb.npy"))
Hh, Ww, _ = a.shape
FN = pickle.load(open(os.path.join(OUT, "final.pkl"), "rb"))
RAW, COR = FN["RAW"], FN["COR"]
cz = np.load(os.path.join(OUT, "contours.npz")); outer_raw, hole_raw = cz["outer"], cz["hole"]
outer_cor, hole_cor = FN["outer_cor"], FN["hole_cor"]
BN = pickle.load(open(os.path.join(OUT, "bevel_notch.pkl"), "rb"))

SS = 2  # supersample for the full overlay
base = np.repeat(np.repeat(a * 0.85, SS, 0), SS, 1)


def plot_pts(img, P, col, ss, rad=0):
    H, W, _ = img.shape
    for x, y in P:
        xi, yi = int(round(x * ss + (ss - 1) / 2)), int(round(y * ss + (ss - 1) / 2))
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                if 0 <= yi + dy < H and 0 <= xi + dx < W:
                    img[yi + dy, xi + dx] = col


def line_pts(c, d, t0, t1, step=0.25):
    t = np.arange(t0, t1, step)
    return c[None] + t[:, None] * d[None]


def circle_pts(cx, cy, r, step_deg=0.1):
    th = np.radians(np.arange(0, 360, step_deg))
    return np.c_[cx + r * np.cos(th), cy - r * np.sin(th)]


def draw_all(img, ss):
    R = COR
    hb, ho, tc = R["hub"], R["hole"], R["tip_circle"]
    plot_pts(img, circle_pts(hb["cx"], hb["cy"], hb["r"]), [1, 1, 0], ss)
    plot_pts(img, circle_pts(ho["cx"], ho["cy"], ho["r"]), [0, 1, 0], ss)
    plot_pts(img, circle_pts(tc["cx"], tc["cy"], tc["r"], 0.05), [1, 0.5, 0], ss)
    plot_pts(img, outer_raw, [0.3, 0.3, 1], ss)
    plot_pts(img, hole_raw, [0.3, 0.3, 1], ss)
    plot_pts(img, outer_cor, [1, 0, 1], ss)
    plot_pts(img, hole_cor, [1, 0, 1], ss)
    for p in R["pts"]:
        for s in ("A", "B"):
            e = p[s]
            t0 = np.dot(e["root"] - e["cen"], e["dir"]) - 20; t1 = np.dot(p["apex"] - e["cen"], e["dir"])
            plot_pts(img, line_pts(e["cen"], e["dir"], t0, t1), [0, 1, 1], ss)
            plot_pts(img, [e["root"]], [0, 0.4, 1], ss, rad=2)
        plot_pts(img, [p["apex"]], [1, 0, 0], ss, rad=2)
        CH = R["CH"]
        tip = CH + p["obs_tip_rho_est"] * p["axis"]
        plot_pts(img, [tip], [1, 1, 1], ss, rad=2)
    plot_pts(img, [R["CH"]], [1, 1, 0], ss, rad=3)
    plot_pts(img, [(ho["cx"], ho["cy"])], [0, 1, 0], ss, rad=3)


full = base.copy(); draw_all(full, SS)
# downsample to 1x-ish size for viewing (keep 2x file too)
write_png(os.path.join(OUT, "roppo_overlay_2x.png"), full)
small = full.reshape(Hh, SS, Ww, SS, 3).max(axis=(1, 3)) * 0 + full[::SS, ::SS]
write_png(os.path.join(OUT, "roppo_overlay.png"), small)

# junction mosaic (crop 64x64 source px at 5x)
SC = 5; HALF = 32
tiles = []
for i, p in enumerate(COR["pts"]):
    for s in ("A", "B"):
        rt = p[s]["root"]
        x0, y0 = int(rt[0]) - HALF, int(rt[1]) - HALF
        crop = a[max(y0, 0):y0 + 2 * HALF, max(x0, 0):x0 + 2 * HALF]
        big = np.repeat(np.repeat(crop, SC, 0), SC, 1).copy()
        def pl(P, col, rad=0):
            P = np.asarray(P, float) - [x0, y0]
            m = (P[:, 0] >= 0) & (P[:, 0] < 2 * HALF) & (P[:, 1] >= 0) & (P[:, 1] < 2 * HALF)
            plot_pts(big, P[m], col, SC, rad)
        hb = COR["hub"]
        pl(circle_pts(hb["cx"], hb["cy"], hb["r"], 0.02), [1, 1, 0])
        e = p[s]; pl(line_pts(e["cen"], e["dir"], np.dot(rt - e["cen"], e["dir"]) - 40, np.dot(rt - e["cen"], e["dir"]) + 60, 0.1), [0, 1, 1])
        pl(outer_raw, [0.3, 0.3, 1], 1)
        pl(outer_cor, [1, 0, 1], 1)
        j = [q for q in BN["junctions"] if q["point"] == i and q["side"] == s][0]
        if j["min_dev"] < -1.5: pl([j["min_at"]], [1, 0, 0], 3)
        big[:3] = 1; big[:, :3] = 1
        tiles.append(big)
rows = [np.concatenate(tiles[k:k + 4], 1) for k in range(0, 12, 4)]
write_png(os.path.join(OUT, "roppo_junctions_mosaic.png"), np.concatenate(rows, 0))

# tip mosaic (crop 80x80 at 4x)
SC = 4; HALF = 40; tiles = []
for i, p in enumerate(COR["pts"]):
    t = COR["CH"] + p["obs_tip_rho_est"] * p["axis"]
    x0, y0 = int(t[0]) - HALF, int(t[1]) - HALF
    crop = np.zeros((2 * HALF, 2 * HALF, 3)) + 0.5
    ys, xs = slice(max(y0, 0), min(y0 + 2 * HALF, Hh)), slice(max(x0, 0), min(x0 + 2 * HALF, Ww))
    crop[ys.start - y0:ys.stop - y0, xs.start - x0:xs.stop - x0] = a[ys, xs]
    big = np.repeat(np.repeat(crop, SC, 0), SC, 1).copy()
    def pl(P, col, rad=0):
        P = np.asarray(P, float) - [x0, y0]
        m = (P[:, 0] >= 0) & (P[:, 0] < 2 * HALF) & (P[:, 1] >= 0) & (P[:, 1] < 2 * HALF)
        plot_pts(big, P[m], col, SC, rad)
    for s in ("A", "B"):
        e = p[s]; pl(line_pts(e["cen"], e["dir"], np.dot(t - e["cen"], e["dir"]) - 80, np.dot(p["apex"] - e["cen"], e["dir"]), 0.1), [0, 1, 1])
    pl(outer_raw, [0.3, 0.3, 1], 0)
    pl(outer_cor, [1, 0, 1], 0)
    pl([p["apex"]], [1, 0, 0], 2)
    big[:3] = 1; big[:, :3] = 1
    tiles.append(big)
write_png(os.path.join(OUT, "roppo_tips_mosaic.png"), np.concatenate([np.concatenate(tiles[:3], 1), np.concatenate(tiles[3:], 1)], 0))
print("written")
