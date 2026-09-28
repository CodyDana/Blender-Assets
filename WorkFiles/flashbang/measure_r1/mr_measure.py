import sys, json, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r1")
from mr_common import *
W = ROOT + "WorkFiles/flashbang/measure_r1/"
R = ref(); O = load_png(W + "mr_row.png")[..., :3] * 255
A = load_png(W + "mr_row_alpha.png")[..., 3] > 0.5
D = 175.31
CX = {"v1": 157.68, "v2": 467.01, "v3": 745.55, "v4": 1103.2}
BOT = {"v1": 720.5, "v2": 716.8, "v3": 717.0, "v4": 717.0}
lumw = np.array([0.2126, 0.7152, 0.0722])
out = {}
def pct(im, m):
    if m.sum() < 30: return None
    lum = im[m] @ lumw; o = np.argsort(lum)
    return [[int(x) for x in im[m][o[int(len(o) * q)]]] for q in (0.1, 0.5, 0.9)]
for v, (x0, y0, x1, y1) in VIEW_BOX.items():
    rs = ref_sil(v); os_ = A.copy()
    box = np.zeros_like(rs); box[y0:y1, x0:x1] = True
    rs &= box; os_ &= box
    r = {}
    r["sil_iou"] = round(float((rs & os_).sum() / (rs | os_).sum()), 3)
    rp = paint_mask(R) & rs; op = paint_mask(O) & os_
    r["paint_iou"] = round(float((rp & op).sum() / max((rp | op).sum(), 1)), 3)
    r["paint_frac_ref_ours"] = [round(float(rp.sum() / rs.sum()), 3), round(float(op.sum() / os_.sum()), 3)]
    # silhouette top row and extents
    def ext(m):
        ys, xs = np.nonzero(m); return [int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())]
    r["bbox_ref_ours_y0y1x0x1"] = [ext(rs), ext(os_)]
    # widths within +-0.72 D of the axis at heights (D units above bottom)
    cx, by = CX[v], BOT[v]
    wd = {}
    for name, h in (("cap", 0.25), ("body", 1.19), ("sleeve", 2.7), ("collar", 3.03), ("housing", 3.40)):
        y = int(round(by - h * D))
        xa, xb = int(cx - 0.72 * D), int(cx + 0.72 * D)
        def w(m):
            row = m[y, xa:xb]; idx = np.nonzero(row)[0]
            return round(float((idx.max() - idx.min() + 1) / D), 3) if len(idx) else 0
        wd[name] = [w(rs), w(os_)]
    r["width_D_ref_ours"] = wd
    # parts beyond the body limbs (ring / lever): rows occupied outside |x-cx| > 0.62 D
    for side, sl in (("right", slice(int(cx + 0.62 * D), x1)), ("left", slice(x0, int(cx - 0.62 * D)))):
        def span(m):
            ys = np.nonzero(m[:, sl].any(1))[0]
            return [round(float((by - ys.max()) / D), 3), round(float((by - ys.min()) / D), 3)] if len(ys) else None
        r[f"outside_{side}_H_range_ref_ours"] = [span(rs), span(os_)]
    # colours by zone (only pixels in both silhouettes)
    both = rs & os_
    zones = {"cap": (0.08, 0.40), "housing": (3.2, 3.6)}
    for z, (h0, h1) in zones.items():
        m = np.zeros_like(both); m[int(by - h1 * D):int(by - h0 * D), int(cx - 0.3 * D):int(cx + 0.3 * D)] = True
        m &= both
        r[f"{z}_p10_p50_p90_ref_ours"] = [pct(R, m), pct(O, m)]
    r["paint_p10_p50_p90_ref_ours"] = [pct(R, rp), pct(O, op)]
    # brass in holes: warm pixels (R-B > 18) not paint within body rows
    def brass(im, sil):
        m = sil.copy(); m[:int(by - 2.45 * D)] = False; m[int(by - 0.6 * D):] = False
        R_, G_, B_ = im[..., 0], im[..., 1], im[..., 2]
        return m & ((R_ - B_) > 14) & ((R_ - G_) > 3)
    rb, ob = brass(R, rs), brass(O, os_)
    r["brass_frac_ref_ours"] = [round(float(rb.sum() / rs.sum()), 4), round(float(ob.sum() / os_.sum()), 4)]
    r["brass_p10_p50_p90_ref_ours"] = [pct(R, rb), pct(O, ob)]
    # bare/chip on body: in body band, within the silhouette, non-paint bright (lum > 85, low sat)
    def chips(im, sil, pm):
        m = sil.copy(); m[:int(by - 2.5 * D)] = False; m[int(by - 0.5 * D):] = False
        m[:, :int(cx - 0.4 * D)] = False; m[:, int(cx + 0.4 * D):] = False
        lum = im @ lumw
        bright = m & ~pm & (lum > 85) & (np.abs(im[..., 0] - im[..., 2]) < 30)
        return round(float(bright.sum() / m.sum()), 4)
    r["bright_bare_frac_body_ref_ours"] = [chips(R, rs, paint_mask(R)), chips(O, os_, paint_mask(O))]
    # hole column profile at the axis: rows where not paint inside body band (ref vs ours), summarised as hole runs
    def holes_on_col(im, xcol):
        col = paint_mask(im)[:, xcol - 3:xcol + 4].mean(1) < 0.2
        col[:int(by - 2.5 * D)] = False; col[int(by - 0.55 * D):] = False
        runs = []; y = 0
        while y < len(col):
            if col[y]:
                s = y
                while y < len(col) and col[y]: y += 1
                if y - s > 15: runs.append([round(float((by - y) / D), 3), round(float((by - s) / D), 3)])
            y += 1
        return runs
    r["hole_runs_H_on_brightest_hole_col_ref_ours"] = None
    # find the column of the most central hole in ref: x within +-0.3D with max non-paint in row B band
    ybB = slice(int(by - 1.75 * D), int(by - 1.30 * D))
    xs = np.arange(int(cx - 0.35 * D), int(cx + 0.35 * D))
    npr = [(~paint_mask(R)[ybB, x] & rs[ybB, x]).mean() for x in xs]
    npo = [(~paint_mask(O)[ybB, x] & os_[ybB, x]).mean() for x in xs]
    xr = int(xs[int(np.argmax(npr))]); xo = int(xs[int(np.argmax(npo))])
    r["central_hole_col_offset_D_ref_ours"] = [round((xr - cx) / D, 3), round((xo - cx) / D, 3)]
    r["hole_runs_H_ref_ours"] = [holes_on_col(R, xr), holes_on_col(O, xo)]
    out[v] = r
    print("MRM", v, json.dumps(r))
json.dump(out, open(W + "mr_measure.json", "w"), indent=1)
