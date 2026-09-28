"""Stage 2: background surface model + plate mask at several contrast fractions.

blender -b --factory-startup --python s2_mask.py -- <photo> <outdir>
Classifier: t = projection fraction of (rgb - bg(x,y)) onto (plate - bg(x,y)), 0 = background,
1 = plate colour. Piece if t > T, or (chroma excess > 0.06 and t > 0.25) so the tan/orange
ground-bevel bands stay inside. Nominal T = 0.5; also T = 0.35 / 0.65 / 0.8 for sensitivity
(the upper/right edges carry a soft scanner shadow, the lower/left edges are crisp).
Keeps the largest 4-connected component, fills enclosed specks < 2000 px, records enclosed
background components >= 2000 px as holes.
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imgio

argv = sys.argv[sys.argv.index("--") + 1:]
photo, outdir = argv[0], argv[1]
rgb = imgio.load_rgb(photo).astype(np.float64)
H, W, _ = rgb.shape
lum = rgb.mean(2)
chroma = rgb.max(2) - rgb.min(2)
yy, xx = np.mgrid[0:H, 0:W]
Xf = xx / W; Yf = yy / H


def design(X, Y):
    cols = []
    for i in range(4):
        for j in range(4 - i):
            cols.append((X ** i) * (Y ** j))
    return np.stack(cols, -1)  # cubic surface, 10 terms

Afull = design(Xf, Yf)


def fit_bg(sel):
    A = Afull[sel]
    bg = np.zeros_like(rgb)
    sig = []
    for c in range(3):
        v = rgb[:, :, c][sel]
        w = np.ones(v.shape, bool)
        for it in range(5):
            co, *_ = np.linalg.lstsq(A[w], v[w], rcond=None)
            r = v - A @ co
            s = 1.4826 * np.median(np.abs(r[w]))
            w = np.abs(r) < 3 * max(s, 1e-3)
        bg[:, :, c] = Afull @ co
        sig.append(float(s))
    return bg, sig

# pass 0: crude mask from luminance
crude = lum < 0.5
crude_d = imgio.dilate(crude, 30)
sel = ~crude_d
# subsample for speed
sub = np.zeros((H, W), bool); sub[::3, ::3] = True
bg, sig = fit_bg(sel & sub)
print("bg sigma per channel", np.round(sig, 4), "bg samples", int((sel & sub).sum()))

core = imgio.erode(crude, 6)
plate = np.median(rgb[core], axis=0)
print("plate median rgb", np.round(plate, 3), "lum", round(float(plate.mean()), 3))

dvec = plate[None, None, :] - bg
t = ((rgb - bg) * dvec).sum(2) / (dvec ** 2).sum(2)
bgchroma = bg.max(2) - bg.min(2)
chx = chroma - bgchroma
np.save(os.path.join(outdir, "t.npy"), t.astype(np.float32))
np.save(os.path.join(outdir, "chx.npy"), chx.astype(np.float32))
imgio.save_rgb(os.path.join(outdir, "t_map.png"), np.clip(t, 0, 1))

bgsel = sel & sub
print("t on bg samples pct 50/99/99.9", np.percentile(t[bgsel], [50, 99, 99.9]))
print("chx on bg samples pct 50/99/99.9", np.percentile(chx[bgsel], [50, 99, 99.9]))

results = {}
for T in [0.35, 0.5, 0.65, 0.8]:
    m = (t > T) | ((chx > 0.06) & (t > 0.25))
    m = imgio.opening(m, 1.5)
    lab, sizes = imgio.label(m)
    big = int(np.argmax(sizes))
    piece = lab == big
    # enclosed background components
    blab, bsizes = imgio.label(~piece)
    border_labels = set(np.unique(np.concatenate([blab[0], blab[-1], blab[:, 0], blab[:, -1]])).tolist())
    holes = np.zeros((H, W), bool)
    filled = piece.copy()
    hole_list = []
    for L in range(1, len(bsizes)):
        if L in border_labels:
            continue
        if bsizes[L] < 2000:
            filled |= blab == L
        else:
            holes |= blab == L
            ys, xs = np.nonzero(blab == L)
            hole_list.append({"area_px": int(bsizes[L]), "cx": float(xs.mean()), "cy": float(ys.mean())})
    solid = filled & ~holes          # piece with specks filled, real holes open
    silhouette = filled | holes      # outer silhouette, holes filled
    touches = {"top": bool(silhouette[0].any()), "bottom": bool(silhouette[-1].any()),
               "left": bool(silhouette[:, 0].any()), "right": bool(silhouette[:, -1].any())}
    tag = f"T{int(T * 100):02d}"
    np.save(os.path.join(outdir, f"solid_{tag}.npy"), solid)
    np.save(os.path.join(outdir, f"holes_{tag}.npy"), holes)
    results[tag] = {"piece_px": int(solid.sum()), "silhouette_px": int(silhouette.sum()),
                    "holes": hole_list, "touches_border": touches,
                    "n_components": len(sizes) - 1}
    print(tag, results[tag])
    if T == 0.5:
        imgio.save_rgb(os.path.join(outdir, "mask.png"), solid.astype(np.float32))

json.dump({"plate_rgb": plate.tolist(), "bg_sigma": sig, "masks": results},
          open(os.path.join(outdir, "s2_stats.json"), "w"), indent=1)
