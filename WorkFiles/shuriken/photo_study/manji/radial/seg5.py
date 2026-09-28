"""Stage 1 (final): shadow-aware segmentation.

Diagnosis (see crops): the scan has DIRECTIONAL artefacts. Up-facing edges (outward normal -y) carry a
soft shadow: grey ramp -> very dark core -> sharp step up to the metal face. Right-facing edges (+x) carry
a smooth grey ramp ending in a sharp drop at the metal. Left- and down-facing edges are crisp.
A colour-distance threshold (seg.py) swallows the shadow/ramp. We start from that mask and
  1. column scan (top of every run, walking DOWN): if a ramp leads into a dark core that is darker than the
     face below it, move the edge to the half-level crossing of the core->face step;
  2. row scan (right end of every run, walking LEFT): find the sharp ramp->metal drop and move the edge there.
Each of the four edge types of a C4 manji appears twice lit, once shadowed and once ramped, so the
lit copies give an independent check of both corrections (done in measure.py).
Outputs: mask.npy, mask.png, mask_colour.npy, seg5.json, seg5_overlay*.png
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C

t0 = time.time()
rgb, info = C.load_rgb(C.IMG)
h, w = rgb.shape[:2]
lum = (rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)).astype(np.float32)

# ---------- colour-distance mask (as seg.py) ----------
B = 40
border = np.zeros((h, w), bool); border[:B] = border[-B:] = True; border[:, :B] = border[:, -B:] = True
c0 = np.median(rgb[border], axis=0)
D0 = np.linalg.norm(rgb - c0, axis=2)
fg0 = D0 > C.otsu(D0)
BS = 64
excl = C.dilate(fg0, 12)
ny, nx = (h + BS - 1) // BS, (w + BS - 1) // BS
grid = np.full((ny, nx, 3), np.nan, np.float32)
for j in range(ny):
    for i in range(nx):
        ok = ~excl[j * BS:(j + 1) * BS, i * BS:(i + 1) * BS]
        if ok.sum() > 0.3 * ok.size:
            grid[j, i] = np.median(rgb[j * BS:(j + 1) * BS, i * BS:(i + 1) * BS][ok], axis=0)
valid = ~np.isnan(grid[..., 0]); g = np.where(valid[..., None], grid, 0)
for it in range(400):
    p = np.pad(g, ((1, 1), (1, 1), (0, 0)), mode='edge')
    g = np.where(valid[..., None], grid, (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4)
yc = (np.arange(ny) + 0.5) * BS - 0.5; xc = (np.arange(nx) + 0.5) * BS - 0.5
FX, FY = np.meshgrid(np.clip(np.interp(np.arange(w), xc, np.arange(nx)), 0, nx - 1),
                     np.clip(np.interp(np.arange(h), yc, np.arange(ny)), 0, ny - 1))
bg = C.bilinear(g, FX, FY).astype(np.float32)
D = np.linalg.norm(rgb - bg, axis=2)
tcol = C.otsu(D)
cm = C.open_(C.close_(D > tcol, 2), 2)
runs, roots, areas, touch = C.label_runs(cm, True)
cm = C.paint((h, w), runs, roots == int(np.argmax(areas)))
rb, rtb, ab, tb = C.label_runs(~cm, False)
colour_holes = [float(ab[c]) for c in np.unique(rtb) if not tb[c]]
for c in np.unique(rtb):
    if not tb[c]:
        cm |= C.paint((h, w), rb, rtb == c)
print("colour mask area", cm.sum(), "enclosed background components in colour mask:", colour_holes)


def hbox(a, r, axis):
    """1-D box mean along axis (edge padded)."""
    k = 2 * r + 1
    pad = [(0, 0), (0, 0)]; pad[axis] = (r, r)
    P = np.pad(a, pad, mode='edge').astype(np.float64)
    cs = np.cumsum(P, axis=axis)
    cs = np.concatenate([np.zeros_like(np.take(cs, [0], axis=axis)), cs], axis=axis)
    n = a.shape[axis]
    return ((np.take(cs, np.arange(k, k + n), axis=axis) - np.take(cs, np.arange(0, n), axis=axis)) / k).astype(np.float32)


# ---------- 1. column scan for up-facing shadows ----------
Lc = hbox(lum, 3, axis=1)  # average 7 columns, rows untouched
WIN = 75
col_entries = {}  # x -> list of [y0, shift]
for x in range(w):
    col = cm[:, x]
    if not col.any():
        continue
    dcol = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
    starts = np.nonzero(dcol == 1)[0]
    ends = np.nonzero(dcol == -1)[0]
    p = Lc[:, x]
    lst = []
    for y0, y1 in zip(starts, ends):
        shift = 0.0
        L = min(WIN, y1 - y0)
        seg = p[y0:y0 + L]
        # first local minimum after the ramp that is followed by a rise of >0.04 within 8 px
        k = -1
        for i in range(8, L - 6):
            if seg[i] <= seg[i - 1] and seg[i] <= seg[i + 1] and seg[i + 1:i + 9].max() - seg[i] > 0.04:
                k = i
                break
        if k > 0:
            pmin = float(seg[k])
            face = seg[k + 4:k + 12]
            F = float(np.median(face)) if len(face) >= 4 else -1
            ramp_drop = float(seg[:k].max() - pmin)
            if F - pmin > 0.04 and ramp_drop > 0.15:
                half = (pmin + F) / 2
                after = seg[k:k + 12]
                j = np.nonzero(after >= half)[0]
                if len(j):
                    j = int(j[0])
                    if j > 0:
                        a0, a1 = after[j - 1], after[j]
                        ye = y0 + k + j - 1 + ((half - a0) / (a1 - a0) if a1 != a0 else 0.5)
                    else:
                        ye = y0 + k
                    shift = float(ye - y0)
        lst.append([int(y0), shift])
    col_entries[x] = lst


def consensus(entries, R=7, tol=8):
    out = {}
    for x, lst in entries.items():
        res = []
        for y0, sft in lst:
            vals = []
            for xx in range(x - R, x + R + 1):
                for y0b, sb in entries.get(xx, []):
                    if abs(y0b - y0) <= tol:
                        vals.append(sb)
            res.append([y0, float(np.median(vals)) if vals else sft, sft])
        out[x] = res
    return out


colc = consensus(col_entries)
colc = consensus({x: [[a, b] for a, b, c in l] for x, l in colc.items()}, R=20, tol=8)
colc = consensus({x: [[a, b] for a, b, c in l] for x, l in colc.items()}, R=40, tol=8)
m1 = cm.copy()
col_stats = []
for x, lst in colc.items():
    for y0, sm, sraw in lst:
        if sm > 0.5:
            m1[y0:y0 + int(round(sm)), x] = False
            col_stats.append((x, y0, sm, sraw))
col_stats = np.array(col_stats)
print("column scan: columns corrected", len(col_stats), "median shift %.1f px, p95 %.1f, max %.1f" % (
    np.median(col_stats[:, 2]), np.percentile(col_stats[:, 2], 95), col_stats[:, 2].max()))

# ---------- 2. row scan for right-facing ramps ----------
Lr = hbox(lum, 3, axis=0)  # average 7 rows
row_entries = {}
for y in range(h):
    row = m1[y]
    if not row.any():
        continue
    drow = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
    starts = np.nonzero(drow == 1)[0]
    ends = np.nonzero(drow == -1)[0]
    p = Lr[y]
    lst = []
    for x0, x1 in zip(starts, ends):
        xe_last = int(x1 - 1)
        shift = 0.0
        lo = max(x0 + 6, xe_last - 40)
        hi = min(w - 16, xe_last + 3)
        if hi - lo >= 10:
            xs = np.arange(lo, hi)
            dr = (p[xs + 2] - p[xs - 2]) / 4.0
            # candidates: local maxima of the rise, scanned from the background side inward
            for kk in range(len(xs) - 2, 0, -1):
                if not (dr[kk] >= 0.012 and dr[kk] >= dr[kk - 1] and dr[kk] >= dr[kk + 1]):
                    continue
                xk = int(xs[kk])
                right = p[xk + 3:xk + 15]
                left = p[max(xk - 12, 0):xk - 2]
                if len(left) < 5:
                    continue
                R = float(np.median(right)); Lf = float(np.median(left))
                smooth = float(np.std(np.diff(right))) < 0.012
                if R - Lf > 0.06 and smooth and R < 0.62:
                    half = (Lf + R) / 2
                    sg = p[xk - 4:xk + 5]
                    jj = np.nonzero(sg >= half)[0]
                    if len(jj):
                        xcross = xk - 4 + int(jj[0])
                        shift = float(max(0, xe_last + 1 - xcross))
                    break
        lst.append([xe_last, shift])
    row_entries[y] = lst

rowc = consensus(row_entries)
rowc = consensus({y: [[a, b] for a, b, c in l] for y, l in rowc.items()}, R=20, tol=8)
m2 = m1.copy()
row_stats = []
for y, lst in rowc.items():
    for xe_last, sm, sraw in lst:
        if sm > 0.5:
            m2[y, xe_last + 1 - int(round(sm)):xe_last + 1] = False
            row_stats.append((y, xe_last, sm, sraw))
row_stats = np.array(row_stats)
print("row scan: rows corrected", len(row_stats), "median shift %.1f px, p95 %.1f, max %.1f" % (
    np.median(row_stats[:, 2]), np.percentile(row_stats[:, 2], 95), row_stats[:, 2].max()))

# ---------- 3. remove leftover smooth bright ramp blocks (e.g. at the up/right corners) ----------
def box(a, r):
    k = 2 * r + 1
    P = np.pad(a, r, mode='edge').astype(np.float64)
    S = np.zeros((P.shape[0] + 1, P.shape[1] + 1)); S[1:, 1:] = P.cumsum(0).cumsum(1)
    return ((S[k:, k:] - S[:-k, k:] - S[k:, :-k] + S[:-k, :-k]) / (k * k)).astype(np.float32)
E5 = box(np.abs(lum - box(lum, 1)), 2)
l3 = box(lum, 1)
ramp_like = m2 & (E5 < 0.004) & (l3 > 0.38)
edge_band = m2 & ~C.erode(m2, 1)
rr, rro, rar, rto = C.label_runs(ramp_like, True)
removed_blocks = 0
if len(rro):
    comp_touch = np.zeros(len(rar), bool)
    ys_, xs_, xe_ = rr
    for i in range(len(ys_)):
        if edge_band[ys_[i], xs_[i]:xe_[i]].any():
            comp_touch[rro[i]] = True
    sel = comp_touch[rro] & (rar[rro] > 40)
    blk = C.paint((h, w), rr, sel)
    removed_blocks = int(blk.sum())
    m2 &= ~blk
print("ramp blocks removed px", removed_blocks)
final = C.open_(C.close_(m2, 1), 1)
runs, roots, areas, touch = C.label_runs(final, True)
final = C.paint((h, w), runs, roots == int(np.argmax(areas)))
rb, rtb, ab, tb = C.label_runs(~final, False)
final_holes = [float(ab[c]) for c in np.unique(rtb) if not tb[c]]
for c in np.unique(rtb):
    if not tb[c]:
        final |= C.paint((h, w), rb, rtb == c)
print("final area", final.sum(), "colour area", cm.sum(), "ratio %.4f" % (final.sum() / cm.sum()), "holes", final_holes)

np.save(os.path.join(C.OUT, "mask.npy"), np.packbits(final, axis=None))
np.save(os.path.join(C.OUT, "mask_colour.npy"), np.packbits(cm, axis=None))
np.save(os.path.join(C.OUT, "scan_col_stats.npy"), col_stats)
np.save(os.path.join(C.OUT, "scan_row_stats.npy"), row_stats)
C.save_png(final.astype(np.float32), os.path.join(C.OUT, "mask.png"))
ov = rgb.copy()
ov[cm & ~C.erode(cm, 1)] = [1.0, 0.85, 0.0]
ov[final & ~C.erode(final, 1)] = [1, 0, 0]
C.save_png(ov[::2, ::2], os.path.join(C.OUT, "seg5_overlay_half.png"))
json.dump(dict(colour_otsu=float(tcol), colour_area_px=float(cm.sum()), final_area_px=float(final.sum()),
               colour_enclosed_bg_components=colour_holes, final_enclosed_bg_components=final_holes,
               column_scan=dict(n=len(col_stats), median_shift_px=float(np.median(col_stats[:, 2])),
                                p95_shift_px=float(np.percentile(col_stats[:, 2], 95))),
               row_scan=dict(n=len(row_stats), median_shift_px=float(np.median(row_stats[:, 2])),
                             p95_shift_px=float(np.percentile(row_stats[:, 2], 95)))),
          open(os.path.join(C.OUT, "seg5.json"), "w"), indent=1)
print("done", time.time() - t0)
