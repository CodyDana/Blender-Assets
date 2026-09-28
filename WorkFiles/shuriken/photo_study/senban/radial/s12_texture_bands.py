"""Is the dark band along the top edge (and inside the hole's bottom edge) steel or a shadow on the
scanner lid? Along-edge texture (high-pass std) and colour (R-B) as a function of depth from the
edge, for all four outer sides and the four hole sides. Lid shadow = smooth + neutral; steel =
textured + warm."""
import sys, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/radial")
import numpy as np
from common import *

R0 = json.load(open(OUT + "senban_radial.json"))
rgb = load_rgb().astype(np.float64)
H, W, _ = rgb.shape
L = rgb.mean(-1)
RB = rgb[..., 0] - rgb[..., 2]


def bilinear(img, x, y):
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def smooth_rows(a, s):
    r = int(3 * s) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2); k /= k.sum()
    p = np.pad(a, ((r, r), (0, 0)), mode='edge')
    o = np.zeros_like(a)
    for i, kv in enumerate(k):
        o += kv * p[i:i + a.shape[0]]
    return o


def band_stats(P0, u, n, s_lo, s_hi, n_lo, n_hi):
    ss = np.arange(s_lo, s_hi, 1.0)
    ns = np.arange(n_lo, n_hi, 1.0)
    X = P0[0] + ss[:, None] * u[0] + ns[None, :] * n[0]
    Y = P0[1] + ss[:, None] * u[1] + ns[None, :] * n[1]
    Lp = bilinear(L, X, Y); Rp = bilinear(RB, X, Y)
    # align rows on the outer edge = first depth where L drops below midpoint of lid and inner level
    return ss, ns, Lp, Rp


out = {}
cx, cy = R0["outer_boundary"]["centre_polygon_centroid"]
corners = [np.array(p) for p in R0["corners_virtual_px"]]
for q, sd in enumerate(R0["sides"]):
    P0 = corners[q]; P1 = corners[(q + 1) % 4]
    ch = P1 - P0; c = np.linalg.norm(ch); u = ch / c
    nrm = np.array([-u[1], u[0]])
    if np.dot(np.array([cx, cy]) - (P0 + P1) / 2, nrm) < 0: nrm = -nrm
    # middle 60% of the side, where the edge is nearly parallel to... use the arc to align
    fcx, fcy = sd["arc_centre_px"]; R = sd["arc_radius_px"]
    rows = []
    for s in np.arange(0.2 * c, 0.8 * c, 1.0):
        # point on chord, go along chord-normal to find arc: parametrize by arc directly
        pass
    # sample along arc-normal lines anchored on the arc with offset
    ang0 = math.atan2(P0[1] - fcy, P0[0] - fcx); ang1 = math.atan2(P1[1] - fcy, P1[0] - fcx)
    da = (ang1 - ang0 + math.pi) % (2 * math.pi) - math.pi
    aa = ang0 + np.linspace(0.2, 0.8, int(0.6 * c)) * da
    depths = np.arange(-15, 40, 0.5)
    rad = R + depths  # inward = away from arc centre (concave side)
    X = fcx + rad[None, :] * np.cos(aa)[:, None]
    Y = fcy + rad[None, :] * np.sin(aa)[:, None]
    Lp = bilinear(L, X, Y); Rp = bilinear(RB, X, Y)
    # per-row edge: steepest L drop in depth -10..10 (first significant)
    g = np.gradient(Lp, axis=1)
    e = np.zeros(len(aa))
    for i in range(len(aa)):
        w = (depths > -12) & (depths < 12)
        idx = np.nonzero(w)[0]
        gi = -g[i, idx]
        thr = 0.5 * gi.max()
        k = int(np.nonzero(gi >= thr)[0][0])
        while k + 1 < len(gi) and gi[k + 1] > gi[k]: k += 1
        e[i] = depths[idx[k]]
    # resample aligned: rel depth
    rel = np.arange(-12, 34, 1.0)
    La = np.array([np.interp(rel + e[i], depths, Lp[i]) for i in range(len(aa))])
    Ra = np.array([np.interp(rel + e[i], depths, Rp[i]) for i in range(len(aa))])
    hp = La - smooth_rows(La, 6.0)
    out["outer_" + sd["name"]] = {
        "rel_depth_px": rel.tolist(),
        "L_mean": La.mean(0).round(3).tolist(),
        "RB_mean": Ra.mean(0).round(3).tolist(),
        "alongedge_hp_std": hp.std(0).round(4).tolist(),
        "edge_offset_from_arc_median": round(float(np.median(e)), 2),
    }

# hole sides: use the hole corners from R0
hc = R0["hole"]["corners_px"]
hcen = np.array(R0["hole"]["centre_from_corners_px"])
for nm, (a, b) in {"top": ("top_left", "top_right"), "bottom": ("bottom_left", "bottom_right"),
                   "left": ("top_left", "bottom_left"), "right": ("top_right", "bottom_right")}.items():
    P0 = np.array(hc[a]); P1 = np.array(hc[b])
    ch = P1 - P0; c = np.linalg.norm(ch); u = ch / c
    nrm = np.array([-u[1], u[0]])
    if np.dot(hcen - (P0 + P1) / 2, nrm) > 0: nrm = -nrm   # outward from hole = into plate
    ss = np.arange(0.2 * c, 0.8 * c, 1.0)
    depths = np.arange(-40, 30, 0.5)     # negative = inside hole
    X = P0[0] + ss[:, None] * u[0] + depths[None, :] * nrm[0]
    Y = P0[1] + ss[:, None] * u[1] + depths[None, :] * nrm[1]
    Lp = bilinear(L, X, Y); Rp = bilinear(RB, X, Y)
    rel = depths
    hp = Lp - smooth_rows(Lp, 6.0)
    out["hole_" + nm] = {"rel_depth_px_from_fitted_line(+ = into plate)": rel[::2].tolist(),
                         "L_mean": Lp.mean(0)[::2].round(3).tolist(), "RB_mean": Rp.mean(0)[::2].round(3).tolist(),
                         "alongedge_hp_std": hp.std(0)[::2].round(4).tolist()}
json.dump(out, open(OUT + "senban_band_texture.json", "w"), indent=0)
for k, v in out.items():
    print("==", k, v.get("edge_offset_from_arc_median", ""))
    rel = v.get("rel_depth_px", v.get("rel_depth_px_from_fitted_line(+ = into plate)"))
    for i in range(len(rel)):
        print("  %6.1f  L=%.3f  RB=%.3f  hp=%.4f" % (rel[i], v["L_mean"][i], v["RB_mean"][i], v["alongedge_hp_std"][i]))
