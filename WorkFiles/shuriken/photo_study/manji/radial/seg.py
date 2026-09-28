"""Stage 1: segment the manji from the scanner background. Writes mask.png, mask.npy, seg.json, seg_overlay*.png."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C

t0 = time.time()
rgb, info = C.load_rgb(C.IMG)
h, w = rgb.shape[:2]
print("INFO", info)
lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)

# --- 1. background from the image border ---------------------------------------------
B = 40
border = np.zeros((h, w), bool)
border[:B] = border[-B:] = True
border[:, :B] = border[:, -B:] = True
c0 = np.median(rgb[border], axis=0)
print("border median rgb", c0, "border lum pct 1/50/99", np.percentile(lum[border], [1, 50, 99]))
D0 = np.linalg.norm(rgb - c0, axis=2)
t_init = C.otsu(D0)
fg0 = D0 > t_init
print("initial otsu on colour distance", t_init, "fg frac", fg0.mean())

# --- 2. smooth spatial background model from background-classified pixels ----------
BS = 64
excl = C.dilate(fg0, 12)
ny, nx = (h + BS - 1) // BS, (w + BS - 1) // BS
grid = np.full((ny, nx, 3), np.nan, np.float32)
for j in range(ny):
    for i in range(nx):
        blk = rgb[j * BS:(j + 1) * BS, i * BS:(i + 1) * BS]
        ok = ~excl[j * BS:(j + 1) * BS, i * BS:(i + 1) * BS]
        if ok.sum() > 0.3 * ok.size:
            grid[j, i] = np.median(blk[ok], axis=0)
valid = ~np.isnan(grid[..., 0])
print("bg grid blocks valid", valid.sum(), "of", valid.size)
g = np.where(valid[..., None], grid, 0)
for it in range(400):  # fill interior blocks by diffusion from valid ones
    p = np.pad(g, ((1, 1), (1, 1), (0, 0)), mode='edge')
    avg = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4
    g = np.where(valid[..., None], grid, avg)
# upsample block centres -> full res
yc = (np.arange(ny) + 0.5) * BS - 0.5
xc = (np.arange(nx) + 0.5) * BS - 0.5
fy = np.clip(np.interp(np.arange(h), yc, np.arange(ny)), 0, ny - 1)
fx = np.clip(np.interp(np.arange(w), xc, np.arange(nx)), 0, nx - 1)
FX, FY = np.meshgrid(fx, fy)
bg = C.bilinear(g, FX, FY).astype(np.float32)
print("bg model lum range", float((bg @ np.array([0.2126, 0.7152, 0.0722])).min()), float((bg @ np.array([0.2126, 0.7152, 0.0722])).max()))
D = np.linalg.norm(rgb - bg, axis=2)
t = C.otsu(D)
raw = D > t
print("refined otsu", t, "fg frac", raw.mean())
# sensitivity: thresholds at 0.75t and 1.25t
sens = {k: float((D > k * t).sum()) for k in (0.75, 1.0, 1.25)}

# --- 3. morphology + largest component ---------------------------------------------
m = C.close_(raw, 2)
m = C.open_(m, 2)
runs, roots, areas, touch = C.label_runs(m, conn8=True)
big = int(np.argmax(areas))
print("components", int((areas > 0).sum()), "largest area", areas[big], "next", np.sort(areas)[-5:])
piece = C.paint((h, w), runs, roots == big)

# --- 4. holes = enclosed background components -------------------------------------
runs_b, roots_b, areas_b, touch_b = C.label_runs(~piece, conn8=False)
comp_ids = np.unique(roots_b)
holes = [(int(c), float(areas_b[c])) for c in comp_ids if not touch_b[c]]
holes.sort(key=lambda a: -a[1])
print("enclosed background components (id, area px):", holes[:10])
filled = piece.copy()
hole_info = []
for cid, a in holes:
    hm = C.paint((h, w), runs_b, roots_b == cid)
    yy, xx = np.nonzero(hm)
    hole_info.append(dict(area_px=a, centroid_xy=[float(xx.mean()), float(yy.mean())],
                          bbox=[int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max())],
                          equiv_diam_px=float(2 * np.sqrt(a / np.pi))))
    filled |= hm

yy, xx = np.nonzero(filled)
cx, cy = float(xx.mean()), float(yy.mean())
area = float(filled.sum())
print("filled area", area, "centroid", cx, cy)

# how far does the raw threshold mask differ from the cleaned mask (boundary sensitivity)
diff = float((raw ^ piece).sum())

np.save(os.path.join(C.OUT, "mask.npy"), np.packbits(filled, axis=None))
C.save_png(filled.astype(np.float32), os.path.join(C.OUT, "mask.png"))

# overlays
ov = rgb * 0.65 + 0.35 * np.where(filled[..., None], np.array([0.1, 0.9, 0.1], np.float32), np.array([0.2, 0.2, 0.9], np.float32)) * 0.6
edge = filled & ~C.erode(filled, 2)
ov[edge] = [1, 0, 0]
cyi, cxi = int(round(cy)), int(round(cx))
ov[cyi - 40:cyi + 41, cxi - 2:cxi + 3] = [1, 1, 0]
ov[cyi - 2:cyi + 3, cxi - 40:cxi + 41] = [1, 1, 0]
C.save_png(ov, os.path.join(C.OUT, "seg_overlay_full.png"))
# half-res version for viewing
C.save_png(ov[::2, ::2], os.path.join(C.OUT, "seg_overlay_half.png"))
# colour-distance map for inspection
C.save_png(np.clip(D / (2 * t), 0, 1)[::2, ::2], os.path.join(C.OUT, "colour_distance_half.png"))

json.dump(dict(image=C.IMG, w=w, h=h, info=info, border_median_rgb=c0.tolist(),
               otsu_initial=t_init, otsu_refined=t, fg_count_vs_threshold_scale=sens,
               raw_vs_clean_xor_px=diff, piece_area_px=float(piece.sum()), filled_area_px=area,
               centroid_xy=[cx, cy], holes=hole_info, n_components=int((areas > 0).sum())),
          open(os.path.join(C.OUT, "seg.json"), "w"), indent=1)
print("done", time.time() - t0)
