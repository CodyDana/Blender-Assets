
# Element-by-element exact-match measurement of the worn cloak captures vs the reference.
# All coordinates reported in REFERENCE px (417x674 frame). Blender 5.2 Python + numpy.
import sys, os, json, math, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import gap_lib as L
OUT = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/gap/out'
LOG = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/gap/logs'
TH = 115.0
SRC = ['REF', 'BL', 'UE']

def up2(a):
    h, w = a.shape[:2]
    Y, X = np.mgrid[0:h*2, 0:w*2].astype(np.float64)
    return L.bilinear(a, (X+0.5)/2-0.5, (Y+0.5)/2-0.5)

I1 = {s: (np.load(f'{OUT}/ref_1x.npy') if s == 'REF' else np.load(f'{OUT}/aligned_{s}_1x.npy')) for s in SRC}
I2 = {s: (up2(I1['REF']) if s == 'REF' else np.load(f'{OUT}/aligned_{s}_2x.npy')) for s in SRC}
L1 = {s: L.lum(I1[s]) for s in SRC}
L2 = {s: L.lum(I2[s]) for s in SRC}
M1 = {s: L1[s] < TH for s in SRC}
E2 = {s: np.load(f'{OUT}/edge_{s}_2x.npy') for s in SRC}
R = {}

# ---------------- 1. silhouette ----------------
bands = {'collar_0_120': (0, 120), 'shoulders_120_260': (120, 260), 'wings_260_480': (260, 480),
         'lower_480_600': (480, 600), 'hem_600_674': (600, 674)}
sil = {}
bref = L.boundary(M1['REF'])
for s in ['BL', 'UE']:
    d = {'iou': L.iou(M1[s], M1['REF']), 'bands': {}}
    bo = L.boundary(M1[s])
    d_r2o = L.nn_dist(bref, bo); d_o2r = L.nn_dist(bo, bref)
    for bn, (y0, y1) in bands.items():
        a = M1[s][y0:y1]; b = M1['REF'][y0:y1]
        e = {'iou': L.iou(a, b), 'ref_only_px': int((b & ~a).sum()), 'ours_only_px': int((a & ~b).sum())}
        for side, (x0, x1) in {'viewer_left': (0, 208), 'viewer_right': (208, 417)}.items():
            sr = (bref[:, 0] >= y0) & (bref[:, 0] < y1) & (bref[:, 1] >= x0) & (bref[:, 1] < x1)
            so = (bo[:, 0] >= y0) & (bo[:, 0] < y1) & (bo[:, 1] >= x0) & (bo[:, 1] < x1)
            e['contour_'+side] = {
                'ref_to_ours_mean_px': float(d_r2o[sr].mean()) if sr.any() else None,
                'ref_to_ours_p90_px': float(np.percentile(d_r2o[sr], 90)) if sr.any() else None,
                'ref_to_ours_max_px': float(d_r2o[sr].max()) if sr.any() else None,
                'ours_to_ref_mean_px': float(d_o2r[so].mean()) if so.any() else None,
                'ours_to_ref_max_px': float(d_o2r[so].max()) if so.any() else None}
        d['bands'][bn] = e
    d['contour_all'] = {'ref_to_ours_mean': float(d_r2o.mean()), 'ref_to_ours_p90': float(np.percentile(d_r2o, 90)),
                        'ours_to_ref_mean': float(d_o2r.mean()), 'ours_to_ref_p90': float(np.percentile(d_o2r, 90)),
                        'hausdorff': float(max(d_r2o.max(), d_o2r.max()))}
    sil[s] = d
def extents(m, y):
    xs = np.where(m[y])[0]
    return (int(xs[0]), int(xs[-1])) if len(xs) else (None, None)
rows = list(range(20, 661, 20))
sil['row_extents_left_right'] = {s: {y: extents(M1[s], y) for y in rows} for s in SRC}
def bbox(m):
    ys, xs = np.where(m); return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
dims = {}
for s in SRC:
    b = bbox(M1[s]); top = b[1]
    wid = lambda y: (lambda e: (e[1]-e[0]+1) if e[0] is not None else 0)(extents(M1[s], y))
    dims[s] = {'bbox_x0y0x1y1': b, 'height_px': b[3]-b[1]+1, 'width_px': b[2]-b[0]+1,
               'h_over_w': (b[3]-b[1]+1)/(b[2]-b[0]+1),
               'width_at': {f'top+{k}': wid(top+k) for k in (5, 15, 40, 70, 100, 130)},
               'width_at_rows': {y: wid(y) for y in (150, 200, 250, 300, 330, 380, 450, 500, 550, 600, 640)}}
sil['dims'] = dims
filled = {s: L.fill_holes_rows(M1[s]) for s in SRC}
sil['background_inside_outline_px_by_band'] = {s: {bn: int((filled[s][y0:y1] & ~M1[s][y0:y1]).sum()) for bn, (y0, y1) in bands.items()} for s in SRC}
R['silhouette'] = sil

# ---------------- 2. collar ----------------
col = {}
def ridge_peaks(v, thr, sep):
    pk = []
    for i in range(1, len(v)-1):
        if v[i] >= thr and v[i] >= v[i-1] and v[i] >= v[i+1]:
            if pk and i - pk[-1] < sep:
                if v[i] > v[pk[-1]]: pk[-1] = i
            else:
                pk.append(i)
    return pk
def trace(E, x0, y0, dx_total, step):
    """greedy ridge follow in 2x px from (x0,y0) for dx_total columns in direction step (+1/-1)"""
    ys = {x0: y0}; y = y0
    for k in range(1, dx_total+1):
        x = x0 + step*k
        if x < 0 or x >= E.shape[1]: break
        c = [y-1, y, y+1]
        y = max(c, key=lambda yy: E[yy, x] if 0 <= yy < E.shape[0] else -9)
        ys[x] = y
    return ys
for s in SRC:
    m = M1[s]; b = bbox(m); top = b[1]
    w15 = extents(m, top+15)
    cx = (w15[0]+w15[1])/2
    base = None
    for y in range(top+15, top+220):
        e = extents(m, y)
        if e[0] is not None and (e[1]-e[0]+1) > 1.6*(w15[1]-w15[0]+1):
            base = y; break
    d = {'top_y': top, 'centre_x_at_top+15': cx, 'top_opening_width_px(top+5)': dims[s]['width_at']['top+5'],
         'width_top+15': w15[1]-w15[0]+1, 'collar_base_y(width>1.6x)': base,
         'collar_height_px': (base-top) if base else None}
    # wrap folds along the collar centre column (2x edge map, averaged over 5 columns)
    E = E2[s]
    xc2 = int(round(cx*2))
    y_lo, y_hi = (top+6)*2, ((base if base else top+110)+10)*2
    prof = E[y_lo:y_hi, xc2-4:xc2+5].mean(1)
    pk = ridge_peaks(prof, 0.12, 8)
    ys_ref = [ (y_lo+p)/2 for p in pk]
    d['wrap_fold_edges_centre_column'] = {'count': len(pk), 'y_refpx': ys_ref,
        'mean_spacing_px': float(np.diff(ys_ref).mean()) if len(ys_ref) > 1 else None,
        'strength': [float(prof[p]) for p in pk]}
    # trace each fold +-40 ref px
    folds = []
    for p in pk:
        y0 = y_lo + p
        r = trace(E, xc2, y0, 80, +1); l = trace(E, xc2, y0, 80, -1)
        yl = l.get(xc2-80); yr = r.get(xc2+80); ylm = l.get(xc2-40); yrm = r.get(xc2+40)
        if yl is None or yr is None: continue
        ang = math.degrees(math.atan2((yr-yl)/2, 80))   # + = descends toward viewer-right
        sag = (y0 - (yl+yr)/2)/2
        folds.append({'y_centre': y0/2, 'y_at_x-40': yl/2, 'y_at_x-20': ylm/2, 'y_at_x+20': yrm/2, 'y_at_x+40': yr/2,
                      'angle_deg(+ = down to viewer-right)': round(ang, 1), 'sag_px(+ = centre lower)': round(sag, 1),
                      'mean_edge_strength': float(np.mean([E[y, x] for x, y in list(l.items())+list(r.items())]))})
    d['wrap_folds_traced'] = folds
    if folds:
        d['fold_angle_abs_mean_deg'] = float(np.mean([abs(f['angle_deg(+ = down to viewer-right)']) for f in folds]))
        d['fold_angle_mean_deg'] = float(np.mean([f['angle_deg(+ = down to viewer-right)'] for f in folds]))
        d['fold_sag_mean_px'] = float(np.mean([f['sag_px(+ = centre lower)'] for f in folds]))
    # structure-tensor orientation of lum in collar box (1x), left/right halves
    l2 = L.blur2d(L2[s], 3)
    gy, gx = np.gradient(l2)
    for half, (xa, xb) in {'left_half': (cx-45, cx), 'right_half': (cx, cx+45)}.items():
        ya, yb = (top+8)*2, (base if base else top+110)*2
        sl = (slice(int(ya), int(yb)), slice(int(xa*2), int(xb*2)))
        mm = (L2[s][sl] < TH)
        Sxx = (gx[sl]**2)[mm].sum(); Syy = (gy[sl]**2)[mm].sum(); Sxy = (gx[sl]*gy[sl])[mm].sum()
        th = 0.5*math.degrees(math.atan2(2*Sxy, Sxx-Syy))    # gradient direction
        line = th + 90.0                                        # edge-line direction in image coords (y down)
        while line > 90: line -= 180
        while line <= -90: line += 180
        coh = math.sqrt((Sxx-Syy)**2 + 4*Sxy**2)/(Sxx+Syy+1e-9)
        d['orientation_'+half] = {'edge_line_angle_deg(+ = descends to viewer-right)': round(line, 1), 'coherence': round(coh, 3)}
    col[s] = d
R['collar'] = col

# ---------------- 3. clasp ----------------
cl = {}
guess = {'REF': (117, 90), 'BL': (146, 75), 'UE': (117, 85)}
def ring_mean(A, cx, cy, r, n=96):
    t = np.linspace(0, 2*np.pi, n, endpoint=False)
    xs = cx + r*np.cos(t); ys = cy + r*np.sin(t)
    return L.bilinear(A, xs, ys, fill=0.0).mean()
for s in SRC:
    l2 = L.blur2d(L2[s], 3)
    gy, gx = np.gradient(l2); G = np.hypot(gx, gy)
    gxs, gys = guess[s]
    # find centre: maximise summed circle-edge response over two radii bands (inner+outer edge)
    best = None
    for cy in np.arange(gys*2-24, gys*2+25, 1.0):
        for cx in np.arange(gxs*2-24, gxs*2+25, 1.0):
            prof = [ring_mean(G, cx, cy, r, 48) for r in range(8, 34, 2)]
            sc = sorted(prof)[-2:]
            v = sum(sc)
            if best is None or v > best[0]: best = (v, cx, cy)
    _, cx, cy = best
    # refine at 0.25
    for it in range(2):
        cands = [(cx+dx, cy+dy) for dx in np.arange(-1.5, 1.6, 0.25) for dy in np.arange(-1.5, 1.6, 0.25)]
        def f(c):
            prof = [ring_mean(G, c[0], c[1], r, 96) for r in np.arange(8, 34, 1.0)]
            return sum(sorted(prof)[-2:])
        cx, cy = max(cands, key=f)
    rs = np.arange(0, 40, 0.5)
    gprof = np.array([ring_mean(G, cx, cy, r) for r in rs])
    lprof = np.array([ring_mean(l2, cx, cy, r) for r in rs])
    pk = ridge_peaks(gprof, 0.35*gprof[6:].max(), 4)
    pk = [p for p in pk if rs[p] >= 4]
    # choose the two strongest edge radii as inner and outer rim
    top2 = sorted(sorted(pk, key=lambda p: gprof[p])[-2:])
    d = {'centre_refpx': [cx/2, cy/2], 'edge_radii_refpx': [float(rs[p]/2) for p in pk],
         'grad_profile_peaks_strength': [float(gprof[p]) for p in pk]}
    if len(top2) == 2:
        ri, ro = rs[top2[0]]/2, rs[top2[1]]/2
        d.update({'inner_diam_refpx': 2*ri, 'outer_diam_refpx': 2*ro, 'band_thickness_refpx': ro-ri,
                  'inner_over_outer': ri/ro})
    # ring brightness vs inner disc vs surround (sRGB lum)
    d['lum_profile_r0_to_20refpx_step1'] = [round(float(lprof[i]), 1) for i in range(0, 80, 4)]
    # radiating gathered folds: count directional edge peaks on circles of r = 20 and 32 ref px, lower half + right
    for rr in (20, 32):
        t = np.linspace(-np.pi*0.25, np.pi*1.0, 360)   # from up-right, clockwise through right and below to left
        xs = cx + rr*2*np.cos(t); ys = cy + rr*2*np.sin(t)
        # tangential gradient = edges crossing the circle radially
        gxv = L.bilinear(gx, xs, ys, 0.0); gyv = L.bilinear(gy, xs, ys, 0.0)
        tang = np.abs(-np.sin(t)*gxv + np.cos(t)*gyv)
        tang = L.smooth1d(tang, 3)
        inside = L.bilinear(L2[s], xs, ys, 255.0) < TH
        thr = max(2.0, 0.35*np.percentile(tang[inside], 95)) if inside.any() else 99
        p2 = [i for i in ridge_peaks(np.where(inside, tang, 0), thr, 6)]
        d[f'radial_fold_crossings_r{rr}'] = len(p2)
    cl[s] = d
R['clasp'] = cl

# ---------------- 4. traced layer edges (DP) ----------------
def dp_trace(E, guide, xa, xb, w, maxstep=2):
    gx = np.array([p[0] for p in guide], float)*2; gyv = np.array([p[1] for p in guide], float)*2
    xs = np.arange(int(xa*2), int(xb*2)+1)
    gc = np.interp(xs, gx, gyv)
    W = int(w*2)
    n = len(xs); K = 2*W+1
    score = np.full((n, K), -1e9); back = np.zeros((n, K), int)
    def val(i, k):
        y = int(round(gc[i])) - W + k
        return E[y, xs[i]] if 0 <= y < E.shape[0] else -1
    V = np.array([[val(i, k) for k in range(K)] for i in range(n)])
    score[0] = V[0]
    for i in range(1, n):
        for k in range(K):
            lo, hi = max(0, k-maxstep), min(K, k+maxstep+1)
            j = lo + int(np.argmax(score[i-1, lo:hi]))
            score[i, k] = score[i-1, j] + V[i, k]; back[i, k] = j
    k = int(np.argmax(score[-1])); path = [0]*n
    for i in range(n-1, -1, -1):
        path[i] = k; k = back[i, k]
    ys = np.array([int(round(gc[i])) - W + path[i] for i in range(n)])
    st = np.array([V[i, path[i]] for i in range(n)])
    return xs/2.0, ys/2.0, st
edges_def = {
  # name: guide per source (ref px), x-range, band half width
  'mantle_long_diagonal': ({'REF': [(125, 118), (190, 210), (240, 250), (300, 305), (350, 340), (400, 380)],
                            'BL': [(150, 115), (200, 185), (250, 235), (300, 295), (350, 340), (400, 375)],
                            'UE': [(135, 130), (200, 210), (250, 250), (300, 295), (350, 340), (405, 375)]}, 150, 395, 14),
  'upper_overlap_A': ({'REF': [(165, 120), (250, 145), (336, 170)], 'BL': [(165, 110), (250, 140), (345, 172)],
                       'UE': [(165, 125), (250, 150), (345, 175)]}, 180, 330, 10),
  'upper_overlap_B': ({'REF': [(150, 135), (250, 170), (345, 210)], 'BL': [(150, 130), (250, 165), (350, 200)],
                       'UE': [(150, 150), (250, 175), (350, 200)]}, 180, 335, 10),
  'hem_right_diagonal': ({'REF': [(210, 530), (300, 590), (375, 640)], 'BL': [(245, 550), (300, 590), (350, 635)],
                          'UE': [(215, 550), (300, 600), (330, 625)]}, 225, 330, 14),
}
tr = {}
overlay = up2(I1['REF']).copy()
lr = L.lum(overlay); mm = lr < TH
lo, hi = np.percentile(lr[mm], 1), np.percentile(lr[mm], 99.5)
v = np.clip((lr-lo)/(hi-lo), 0, 1)*200
overlay = np.where(mm[..., None], np.stack([v]*3, -1), overlay)
colors = {'REF': (0, 255, 0), 'BL': (40, 120, 255), 'UE': (255, 140, 0)}
for en, (guides, xa, xb, w) in edges_def.items():
    xs10 = np.linspace(xa, xb, 10)
    e = {'sample_x_refpx': [round(float(x), 1) for x in xs10]}
    for s in SRC:
        xs, ys, st = dp_trace(E2[s], guides[s], xa, xb, w)
        y10 = np.interp(xs10, xs, ys)
        e[s] = {'y_at_samples': [round(float(y), 1) for y in y10], 'mean_edge_strength': float(st.mean()),
                'frac_cols_strength_gt_0.1': float((st > 0.1).mean()),
                'fit_slope_deg': float(math.degrees(math.atan(np.polyfit(xs, ys, 1)[0])))}
        for x, y in zip(xs, ys):
            X, Y = int(x*2), int(y*2)
            overlay[max(0, Y-1):Y+1, X:X+1] = colors[s]
    for s in ['BL', 'UE']:
        dlt = np.array(e[s]['y_at_samples']) - np.array(e['REF']['y_at_samples'])
        e[s]['delta_y_vs_ref'] = [round(float(x), 1) for x in dlt]
        e[s]['mean_abs_delta'] = float(np.abs(dlt).mean()); e[s]['max_abs_delta'] = float(np.abs(dlt).max())
    tr[en] = e
L.save(f'{OUT}/traced_edges_overlay_on_ref_2x.png', overlay)
R['traced_edges'] = tr

# ---------------- 5/6. wings ----------------
wg = {}
for s in SRC:
    m = M1[s]
    lefts = [(extents(m, y)[0], y) for y in range(200, 620) if extents(m, y)[0] is not None]
    rights = [(extents(m, y)[1], y) for y in range(200, 620) if extents(m, y)[1] is not None]
    lx = min(lefts); rx = max(rights)
    lx_upper = min([p for p in lefts if p[1] < 450])
    rx_upper = max([p for p in rights if p[1] < 450])
    # layered edges on the left wing: count edge peaks down vertical lines x=35,55,75
    E = E2[s]
    cnt = {}
    for x in (35, 55, 75):
        prof = E[300*2:640*2, x*2-2:x*2+3].mean(1)
        cnt[x] = len(ridge_peaks(prof, 0.12, 10))
    cntr = {}
    for x in (345, 370, 390):
        prof = E[200*2:640*2, x*2-2:x*2+3].mean(1)
        cntr[x] = len(ridge_peaks(prof, 0.12, 10))
    wg[s] = {'left_extreme_xy_y200_620': lx, 'left_extreme_above_y450': lx_upper,
             'right_extreme_xy_y200_620': rx, 'right_extreme_above_y450': rx_upper,
             'left_wing_layer_edges_on_vertical_lines_y300_640': cnt,
             'right_wing_layer_edges_on_vertical_lines_y200_640': cntr,
             'left_boundary_x_at': {y: extents(m, y)[0] for y in (300, 330, 360, 400, 450, 500, 550, 600)},
             'right_boundary_x_at': {y: extents(m, y)[1] for y in (300, 350, 380, 400, 450, 500, 550, 600)}}
R['wings'] = wg

# ---------------- 7. front panels (vertical edges along rows) ----------------
fp = {}
for s in SRC:
    l2 = L.blur2d(L2[s], 5)
    gxr = np.zeros_like(l2); gxr[:, 3:-3] = np.abs(l2[:, 6:] - l2[:, :-6])/(L.blur2d(l2, 15)[:, 3:-3]+4.0)
    m2 = L.blur2d((L2[s] < TH).astype(float), 7) > 0.99
    gxr[~m2] = 0
    d = {}
    for y in (400, 450, 500, 550):
        prof = gxr[y*2-6:y*2+7, 90*2:330*2].mean(0)
        pk = ridge_peaks(prof, 0.18, 10)
        d[y] = {'count': len(pk), 'x_refpx': [round(90+p/2, 1) for p in pk]}
    fp[s] = d
R['front_panels'] = fp

# ---------------- 8. inner opening ----------------
io = {}
for s in SRC:
    m = M1[s]; l = L1[s]
    med = np.median(l[m])
    reg = np.zeros_like(m); reg[330:650, 110:300] = True
    dark = reg & m & (l < 0.45*med)
    ys, xs = np.where(dark)
    io[s] = {'garment_median_lum': float(med), 'dark_px(<0.45*median)_in_x110_300_y330_650': int(dark.sum()),
             'dark_bbox': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None,
             'dark_mean_lum': float(l[dark].mean()) if dark.any() else None,
             'dark_rel_to_median': float(l[dark].mean()/med) if dark.any() else None,
             'col_profile_dark_px_per_20px_x': {int(x): int(dark[:, x:x+20].sum()) for x in range(110, 300, 20)}}
# body visible through (body captures): non-garment, non-background pixels inside the filled outline
for s in ['BLbody', 'UEbody', 'UEsettled']:
    im = np.load(f'{OUT}/aligned_{s}_1x.npy'); l = L.lum(im)
    gm = l < TH
    sat = im.max(-1) - im.min(-1)
    bg = (l > 238) & (sat < 10)
    body = ~gm & ~bg
    fl = L.fill_holes_rows(gm | body)
    rows_body = body & fl
    io['visible_body_'+s] = {bn: int(rows_body[y0:y1, 60:360].sum()) for bn, (y0, y1) in bands.items()}
    io['visible_body_'+s]['iou_vs_ref_garment_mask'] = L.iou(gm, M1['REF'])
R['inner_opening'] = io

# ---------------- 9. hem ----------------
hm = {}
xs10 = [int(round(x)) for x in np.linspace(30, 385, 10)]
for s in SRC:
    m = M1[s]
    low = {}
    for x in range(0, 417):
        ys = np.where(m[:, x])[0]
        low[x] = int(ys[-1]) if len(ys) else None
    prof = np.array([low[x] for x in range(40, 380)], float)
    gaps = {}
    for y in (610, 630, 645, 655):
        row = m[y]; xs_ = np.where(row)[0]
        if len(xs_) == 0: gaps[y] = None; continue
        seg = row[xs_[0]:xs_[-1]+1]
        runs = 0; prev = True; runlens = []; cur = 0
        for v in seg:
            if not v:
                cur += 1
                if prev: runs += 1
            else:
                if cur: runlens.append(cur); cur = 0
            prev = v
        gaps[y] = {'gap_runs': runs, 'gap_px': int((~seg).sum()), 'run_lengths': runlens}
    floor = np.percentile(prof, 95)
    hm[s] = {'hem_lowest_y_at_x': {x: low[x] for x in xs10},
             'hem_profile_std_px_x40_380': float(prof.std()),
             'hem_range_px': float(prof.max()-prof.min()),
             'hem_step_count(|dy|>6 between adjacent columns)': int((np.abs(np.diff(prof)) > 6).sum()),
             'frac_columns_within_4px_of_floor(pooling)': float((prof >= floor-4).mean()),
             'gaps_in_hem_rows': gaps,
             'width_y560': dims[s]['width_at_rows'].get(550), 'width_y640': dims[s]['width_at_rows'].get(640)}
for s in ['BL', 'UE']:
    hm[s]['delta_lowest_y_vs_ref_at_x'] = {x: (hm[s]['hem_lowest_y_at_x'][x] - hm['REF']['hem_lowest_y_at_x'][x])
                                           if hm[s]['hem_lowest_y_at_x'][x] is not None and hm['REF']['hem_lowest_y_at_x'][x] is not None else None for x in xs10}
R['hem'] = hm

# ---------------- 10. edge finish ----------------
ef = {}
for s in SRC:
    m = M1[s]
    out = {}
    for side in ('left', 'right'):
        v = np.array([extents(m, y)[0 if side == 'left' else 1] for y in range(200, 600)], float)
        res = v - L.smooth1d(v, 9)
        out[side+'_contour_hf_rms_px'] = float(np.sqrt((res[5:-5]**2).mean()))
        out[side+'_contour_spikes_gt1px'] = int((np.abs(res[5:-5]) > 1.0).sum())
    low = np.array([np.where(m[:, x])[0][-1] for x in range(40, 380)], float)
    res = low - L.smooth1d(low, 9)
    # exclude big steps (construction) from roughness: clip rows where step > 6
    st = np.abs(np.diff(low, prepend=low[0])) > 6
    ok = ~(st | np.roll(st, 1) | np.roll(st, -1))
    out['hem_contour_hf_rms_px'] = float(np.sqrt((res[ok][5:-5]**2).mean()))
    out['hem_contour_spikes_gt1px'] = int((np.abs(res[ok][5:-5]) > 1.0).sum())
    # rolled edge: vertical profile across the traced mantle edge at 2x
    xs, ys, stv = dp_trace(E2[s], edges_def['mantle_long_diagonal'][0][s], 170, 390, 14)
    widths = []; over = []
    l2 = L2[s]
    for x, y in zip(xs[::6], ys[::6]):
        X = int(x*2); Y = int(y*2)
        p = l2[Y-20:Y+21, X-1:X+2].mean(1)
        above = p[:14].mean(); below = p[-10:].min()
        if above - below < 3: continue
        # 10-90% transition on the falling side between Y-10..Y+10
        seg = p[8:34]
        hi_, lo_ = above, below
        t90 = hi_ - 0.1*(hi_-lo_); t10 = lo_ + 0.1*(hi_-lo_)
        i90 = next((i for i in range(len(seg)) if seg[i] < t90 and all(seg[j] < t90 + 1e-6 for j in range(i, min(i+2, len(seg))))), None)
        i10 = next((i for i in range(len(seg)) if seg[i] <= t10), None)
        if i90 is not None and i10 is not None and i10 >= i90:
            widths.append((i10-i90)/2.0)
        over.append(float((p[10:20].max() - above)/(above+1e-6)))
    out['mantle_edge_transition_10_90_refpx_median'] = float(np.median(widths)) if widths else None
    out['mantle_edge_highlight_overshoot_rel_median'] = float(np.median(over)) if over else None
    out['mantle_edge_samples'] = len(widths)
    ef[s] = out
R['edge_finish'] = ef

# ---------------- 11. fabric ----------------
patches = {'mantle': (225, 195, 40), 'front_panel': (185, 400, 40), 'left_fall': (35, 440, 32), 'right_wing': (320, 450, 32)}
fb = {}
def spectrum(p):
    p = p - L.blur2d(p, 9)
    n = p.shape[0]
    w = np.hanning(n); p = p*np.outer(w, w)
    F = np.abs(np.fft.fftshift(np.fft.fft2(p)))**2
    fy, fx = np.mgrid[-n//2:n//2, -n//2:n//2]/n
    fr = np.hypot(fx, fy)
    out = {}
    tot = F[(fr > 0)].sum()
    for nm, (plo, phi) in {'period_2_3px': (2, 3), 'period_3_5px': (3, 5), 'period_5_10px': (5, 10), 'period_10_20px': (10, 20)}.items():
        sel = (fr <= 1/plo) & (fr > 1/phi)
        out[nm] = float(F[sel].sum()/tot)
    vert = F[(np.abs(fy) > 2*np.abs(fx)) & (fr > 0.05)].sum(); horz = F[(np.abs(fx) > 2*np.abs(fy)) & (fr > 0.05)].sum()
    out['anisotropy_vfreq_over_hfreq'] = float(vert/(horz+1e-9))
    return out
for s in SRC + ['BLtiled']:
    img = I1[s] if s in I1 else np.load(f'{OUT}/aligned_{s}_1x.npy')
    l = L.lum(img)
    d = {}
    for pn, (x, y, n) in patches.items():
        p = l[y:y+n, x:x+n].astype(np.float64)
        inside = float((p < TH).mean())
        hp = p - L.blur2d(p, 9)
        d[pn] = {'inside_frac': inside, 'mean_lum': float(p.mean()), 'hp_std': float(hp[4:-4, 4:-4].std()),
                 'hp_rel': float(hp[4:-4, 4:-4].std()/p.mean()), 'spectrum': spectrum(p)}
    fb[s] = d
R['fabric'] = fb

# ---------------- 12. colour/value ----------------
cv = {}
for s in SRC:
    im = I1[s]; m = M1[s]; l = L1[s]
    rgbm = im[m].mean(0)
    cv[s] = {'lum_p5_p10_p50_p90_p95': [float(np.percentile(l[m], q)) for q in (5, 10, 50, 90, 95)],
             'contrast_(p90-p10)/p50': float((np.percentile(l[m], 90)-np.percentile(l[m], 10))/np.percentile(l[m], 50)),
             'rgb_mean': [float(c) for c in rgbm], 'R_minus_B': float(rgbm[0]-rgbm[2])}
R['colour_value'] = cv
R['align'] = json.load(open(LOG+'/align.json'))
json.dump(R, open(LOG+'/gap_measurements.json', 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
print('WROTE gap_measurements.json')
