"""Trace pilot stage 2: TRACE element outlines from the reference pixels.
For every element ROI (tp_rois) on a 6x grid:
    region  = ROI polygon  AND  silhouette (reference not background)          -> whole plate outline
    enamel  = region AND enamel field > 0  (blue-shifted or near-black pixels)  -> recessed insets
    silver  = region AND NOT enamel                                             -> raised rims / filigree
Contours = sub-pixel marching squares of the SMOOTHED fields (no hand drawing of any visible edge except where two
silver elements meet inside the silhouette, where the ROI line decides).  Output work/trace.json (ref px)."""
import sys, os, json; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img, tp_geom2d as G, tp_rois as RO
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
seg = np.load(OUT + "/seg.npz")
R0, C0 = int(seg["R0"]), int(seg["C0"])
rgb = seg["rgb"]; lum = seg["lum"]; bg = seg["bg"]
H, W = lum.shape
S = 6
lum_u = tp_img.resize(lum, S, kind='linear')
br_u = tp_img.resize(rgb[..., 2] - rgb[..., 0], S, kind='linear')
sil_u = tp_img.resize((~bg).astype(np.float32), S, kind='linear')
lum_s = G.gauss(lum_u, 0.6 * S / 2)
br_s = G.gauss(br_u, 0.9 * S / 2)
sil_s = G.gauss(sil_u, 0.5 * S / 2)
X, Y = G.grid(R0, R0 + H, C0, C0 + W, S)
ENAMEL = np.maximum(np.minimum((br_s - 0.012) / 0.012, (0.62 - lum_s) / 0.1), (0.16 - lum_s) / 0.05)  # > 0 = enamel / lacquer
FIL = (lum_s - 0.36) / 0.1                                            # filigree silver: > 0
def mirror(poly): return [(2 * RO.AXIS - x, y) for x, y in poly]
elements = []
for roi in RO.ROIS:
    name, kind = roi[0], roi[1]
    if roi[2] == "circle":
        (cx, cy), r = roi[3], roi[4]
        L = [(cx + r*np.cos(t), cy + r*np.sin(t)) for t in np.linspace(0, 2*np.pi, 48, endpoint=False)]
    else:
        L = list(roi[2])
    if kind == "pair":
        polys = [(f"{name}_L", L), (f"{name}_R", mirror(L))]
    else:
        polys = [(name, L + mirror(L)[::-1][1:-1])]
    for ename, poly in polys:
        elements.append((ename, name, np.array(poly, float)))
FILIGREE = {"crestT", "crestB", "sprigU", "sprigL", "lace"}
def loops_of(field, bbox_mask, min_area_px=1.2):
    ys, xs = np.nonzero(bbox_mask)
    if len(ys) == 0: return []
    y0, y1 = max(ys.min() - 3, 0), min(ys.max() + 4, field.shape[0])
    x0, x1 = max(xs.min() - 3, 0), min(xs.max() + 4, field.shape[1])
    f = field[y0:y1, x0:x1]
    out = []
    for lp in G.marching_squares(f, 0.0):
        P = np.c_[C0 + (lp[:, 0] + x0 + 0.5) / S, R0 + (lp[:, 1] + y0 + 0.5) / S]
        A = G.signed_area(P)
        if abs(A) < min_area_px: continue
        P = G.resample_closed(P, 0.25)
        P = G.smooth_closed(P, 2, 0.5)
        out.append({"pts": np.round(P, 3).tolist(), "area": float(A)})
    return out
res = {"source": r"References/SnowFlower/SnowFlower_sheath_reference.png", "grid_upsample": S, "elements": []}
def disk_open(m, r):
    return G.dilate(G.erode(m, r), r)
def disk_close(m, r):
    return G.erode(G.dilate(m, r), r)
def drop_small(m, min_px2, keep_touching=None):
    """remove connected components of m smaller than min_px2 (ref px^2); components touching keep_touching survive."""
    ys, xs = np.nonzero(m)
    if len(ys) == 0: return m
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sub = m[y0:y1, x0:x1]
    lab, n = G.label(sub)
    out = m.copy()
    if n == 0: return out
    cnt = np.bincount(lab.ravel(), minlength=n + 1)
    touch = np.zeros(n + 1, bool)
    if keep_touching is not None:
        touch[np.unique(lab[keep_touching[y0:y1, x0:x1] & (lab > 0)])] = True
    small = (cnt < min_px2 * S * S) & ~touch
    small[0] = False
    out[y0:y1, x0:x1] &= ~small[lab]
    return out
for i, (en, base, poly) in enumerate(elements):
    mine = G.pip(X, Y, poly)                         # the element continues under the ones in front of it
    reg = np.minimum(G.gauss(mine.astype(np.float32), 0.35 * S) - 0.5, sil_s - 0.5)          # > 0 inside
    R_in = reg > 0
    ys, xs = np.nonzero(reg > -0.4)
    y0, y1, x0, x1 = max(ys.min() - 8, 0), ys.max() + 9, max(xs.min() - 8, 0), xs.max() + 9
    win = (slice(y0, y1), slice(x0, x1))
    Rw = R_in[win]
    edge = Rw & ~G.erode(Rw, 2)
    if base in FILIGREE:
        sv = (FIL[win] > 0) & Rw
        sv = drop_small(sv, 1.5)
    else:
        sv = (ENAMEL[win] <= 0) & Rw
        sv = disk_open(sv, int(round(0.7 * S)))          # thin silver specks (reflections in the enamel) go
        sv = drop_small(sv, 14.0, keep_touching=edge)       # silver islands floating in an inset go
        dk = Rw & ~sv
        dk = drop_small(dk, 5.0)                           # enamel pits inside the rims are filled
        sv = Rw & ~dk
    svf = np.full(reg.shape, -1.0, np.float32); svf[win] = G.gauss(sv.astype(np.float32), 0.3 * S) - 0.5
    dkf = np.full(reg.shape, -1.0, np.float32); dkf[win] = G.gauss((Rw & ~sv).astype(np.float32), 0.3 * S) - 0.5
    silver = np.minimum(reg, svf)
    dark = np.minimum(reg, dkf)
    m = reg > -0.2
    e = {"name": en, "kind": base, "roi": poly.tolist(),
         "region": loops_of(reg, m), "silver": loops_of(silver, m), "dark": loops_of(dark, m)}
    print(en, "region", len(e["region"]), "silver", len(e["silver"]), "dark", len(e["dark"]),
          "silver area", round(sum(abs(l["area"]) for l in e["silver"]), 1), "dark area", round(sum(abs(l["area"]) for l in e["dark"]), 1), flush=True)
    res["elements"].append(e)
# silhouette of the whole throat (for the crown width): per row left/right extents of the reference silhouette
sil = ~bg
rows = {}
for r in range(H):
    xs = np.nonzero(sil[r])[0]
    if len(xs): rows[R0 + r] = [C0 + int(xs.min()), C0 + int(xs.max()) + 1]
res["silhouette_rows"] = rows
# sub-pixel silhouette: iso 0.5 crossings of the smoothed silhouette field on every fine row
sub_r, sub_l, sub_rt = [], [], []
for yy in range(sil_s.shape[0]):
    f = sil_s[yy] - 0.5
    idx = np.nonzero(f > 0)[0]
    if len(idx) == 0: continue
    i0, i1 = idx.min(), idx.max()
    xl = i0 - (f[i0] / (f[i0] - f[i0 - 1]) if i0 > 0 else 0.0)
    xr = i1 + (f[i1] / (f[i1] - f[i1 + 1]) if i1 + 1 < len(f) else 0.0)
    sub_r.append(R0 + (yy + 0.5) / S); sub_l.append(C0 + (xl + 0.5) / S); sub_rt.append(C0 + (xr + 0.5) / S)
res["silhouette_sub"] = {"rows": sub_r, "left": sub_l, "right": sub_rt}
json.dump(res, open(OUT + "/trace.json", "w"))
# overlay
big = tp_img.resize(rgb, S, kind='linear') * 0.7 + 0.3
def draw(P, col):
    for x, y in P:
        xi, yi = int((x - C0) * S), int((y - R0) * S)
        if 0 <= xi < big.shape[1] and 0 <= yi < big.shape[0]: big[yi, xi, :3] = col
for e in res["elements"]:
    for l in e["silver"]: draw(l["pts"], [0.9, 0.1, 0.1])
    for l in e["dark"]: draw(l["pts"], [0.1, 0.3, 1.0])
tp_img.save(OUT + "/trace_overlay_x6.png", big)
