
# Second pass: per-source flat fabric patches, hem slits, fray residue, clasp fold crossings at hand-read centres,
# skin-only visible-body counts. Writes logs/gap_measurements2.json and a patch overlay.
import sys, os, json, math, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import gap_lib as L
OUT = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/gap/out'
LOG = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/gap/logs'
TH = 115.0
SRC = ['REF', 'BL', 'UE', 'BLtiled']
def up2(a):
    h, w = a.shape[:2]
    Y, X = np.mgrid[0:h*2, 0:w*2].astype(np.float64)
    return L.bilinear(a, (X+0.5)/2-0.5, (Y+0.5)/2-0.5)
I1 = {s: (np.load(f'{OUT}/ref_1x.npy') if s == 'REF' else np.load(f'{OUT}/aligned_{s}_1x.npy')) for s in SRC}
L1 = {s: L.lum(I1[s]) for s in SRC}
M1 = {s: L1[s] < TH for s in SRC}
R = {}

# ---- fabric: 4 flattest 32x32 windows per source (low-frequency std smallest), then grain stats ----
def spectrum(p):
    p = p - L.blur2d(p, 9); n = p.shape[0]
    w = np.hanning(n); p = p*np.outer(w, w)
    F = np.abs(np.fft.fftshift(np.fft.fft2(p)))**2
    fy, fx = np.mgrid[-n//2:n//2, -n//2:n//2]/n; fr = np.hypot(fx, fy)
    tot = F[fr > 0].sum(); out = {}
    for nm, (plo, phi) in {'p2_3': (2, 3), 'p3_5': (3, 5), 'p5_10': (5, 10), 'p10_16': (10, 16)}.items():
        out[nm] = float(F[(fr <= 1/plo) & (fr > 1/phi)].sum()/tot)
    v = F[(np.abs(fy) > 2*np.abs(fx)) & (fr > 0.06)].sum(); h = F[(np.abs(fx) > 2*np.abs(fy)) & (fr > 0.06)].sum()
    out['aniso_vfreq_over_hfreq'] = float(v/(h+1e-9))
    return out
N = 32
fab = {}
ov = up2(I1['REF']).copy()
panels_img = []
for s in SRC:
    l = L1[s].astype(np.float64); m = M1[s]
    lf = L.blur2d(l, 9)
    cands = []
    for y in range(100, 620-N, 8):
        for x in range(30, 390-N, 8):
            if not m[y:y+N, x:x+N].all(): continue
            w = lf[y:y+N, x:x+N]
            gy, gx = np.gradient(w)
            cands.append((float(np.hypot(gx, gy).mean() / (w.mean()+1)), x, y))
    cands.sort(); chosen = []
    for c in cands:
        if all(abs(c[1]-q[1]) >= N or abs(c[2]-q[2]) >= N for q in chosen):
            chosen.append(c)
        if len(chosen) == 4: break
    rows = []
    for _, x, y in chosen:
        p = l[y:y+N, x:x+N]; hp = p - L.blur2d(p, 7)
        rows.append({'xy': [x, y], 'mean': float(p.mean()), 'hp_std': float(hp[3:-3, 3:-3].std()),
                     'hp_rel': float(hp[3:-3, 3:-3].std()/p.mean()), 'spec': spectrum(p)})
    agg = {'hp_rel_mean': float(np.mean([r['hp_rel'] for r in rows])), 'hp_std_mean': float(np.mean([r['hp_std'] for r in rows])),
           'mean_lum': float(np.mean([r['mean'] for r in rows]))}
    for k in rows[0]['spec']:
        agg['spec_'+k] = float(np.mean([r['spec'][k] for r in rows]))
    fab[s] = {'patches': rows, 'agg': agg}
    # 64px magnified strip of the first two patches for eyeballing (contrast-normalised per patch)
    for r in rows[:2]:
        x, y = r['xy']; p = l[y:y+N, x:x+N]
        v = np.clip((p - p.mean())/(4*p.std()+1e-6)*0.5+0.5, 0, 1)*255
        panels_img.append(np.repeat(np.repeat(v, 6, 0), 6, 1))
        panels_img.append(np.full((N*6, 6), 255.0))
R['fabric_flat_patches'] = fab
L.save(f'{OUT}/fabric_flat_patches_REF_BL_UE_BLtiled_x6_normalised.png', np.concatenate(panels_img[:-1], 1))

# ---- hem slits: background runs between garment pixels in the same column, rows 520..674 ----
hs = {}
for s in ['REF', 'BL', 'UE']:
    m = M1[s]; cols = 0; px = 0; lens = []
    for x in range(20, 400):
        c = m[520:674, x]
        ys = np.where(c)[0]
        if len(ys) < 2: continue
        seg = c[ys[0]:ys[-1]+1]
        g = (~seg).sum()
        if g >= 3:
            cols += 1; px += int(g)
    # square-cut corners: count columns where the lowest garment y jumps by >= 8 px to the neighbour
    low = np.array([np.where(m[:, x])[0][-1] for x in range(20, 400)])
    jumps = np.where(np.abs(np.diff(low)) >= 8)[0]
    hs[s] = {'columns_with_vertical_slit_ge3px': cols, 'slit_px_total': px,
             'hem_jumps_ge8px': int(len(jumps)), 'jump_x': [int(20+j) for j in jumps]}
R['hem_slits'] = hs

# ---- fray: thin-structure residue (mask minus 3x3 opening) along the outline, per 100 px of outline ----
def erode(m):
    e = m.copy(); e[1:-1, 1:-1] = m[1:-1, 1:-1] & m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:] & m[:-2, :-2] & m[2:, 2:] & m[:-2, 2:] & m[2:, :-2]
    return e
def dilate(m):
    d = m.copy(); d[1:-1, 1:-1] = m[1:-1, 1:-1] | m[:-2, 1:-1] | m[2:, 1:-1] | m[1:-1, :-2] | m[1:-1, 2:] | m[:-2, :-2] | m[2:, 2:] | m[:-2, 2:] | m[2:, :-2]
    return d
fr = {}
for s in ['REF', 'BL', 'UE']:
    # use a softer threshold to catch semi-transparent threads (lum < 200)
    m = L1[s] < 200
    op = dilate(erode(m))
    res = m & ~op
    b = L.boundary(m)
    out = {}
    for nm, (y0, y1, x0, x1) in {'hem_y590_674': (590, 674, 0, 417), 'left_edge_y250_600': (250, 600, 0, 150),
                                 'right_edge_y250_600': (250, 600, 267, 417)}.items():
        rr = int(res[y0:y1, x0:x1].sum())
        bl = int(((b[:, 0] >= y0) & (b[:, 0] < y1) & (b[:, 1] >= x0) & (b[:, 1] < x1)).sum())
        out[nm] = {'thin_residue_px': rr, 'outline_px': bl, 'residue_per_100_outline_px': 100.0*rr/max(bl, 1)}
    # soft-edge alpha: pixels of intermediate lum (115..200) along the outline = semi-transparent fringe
    fringe = (L1[s] >= 115) & (L1[s] < 200)
    out['fringe_px_115_200_total'] = int(fringe[100:674].sum())
    fr[s] = out
R['fray'] = fr

# ---- clasp radial fold crossings at hand-read centres (from 8x crops) ----
cent = {'REF': (117.5, 90.0), 'BL': (145.5, 75.3), 'UE': (111.0, 76.0)}
cl = {}
for s in ['REF', 'BL', 'UE']:
    l2 = L.blur2d(L.lum(up2(I1[s]) if s == 'REF' else np.load(f'{OUT}/aligned_{s}_2x.npy')), 3)
    gy, gx = np.gradient(l2); cx, cy = cent[s][0]*2, cent[s][1]*2
    d = {}
    for rr in (18, 26, 34):
        t = np.linspace(-np.pi*0.2, np.pi*0.95, 400)   # right side, below, to lower-left (where the gathered folds are)
        xs = cx + rr*2*np.cos(t); ys = cy + rr*2*np.sin(t)
        gxv = L.bilinear(gx, xs, ys, 0.0); gyv = L.bilinear(gy, xs, ys, 0.0)
        tang = L.smooth1d(np.abs(-np.sin(t)*gxv + np.cos(t)*gyv), 3)
        inside = L.bilinear(l2, xs, ys, 255.0) < TH
        tang = np.where(inside, tang, 0)
        rel = tang / (L.bilinear(L.blur2d(l2, 15), xs, ys, 1.0) + 4.0)
        thr = 0.06
        pk = []
        for i in range(1, len(rel)-1):
            if rel[i] >= thr and rel[i] >= rel[i-1] and rel[i] >= rel[i+1]:
                if pk and i - pk[-1] < 5:
                    if rel[i] > rel[pk[-1]]: pk[-1] = i
                else: pk.append(i)
        d[f'r{rr}_fold_crossings'] = len(pk)
        d[f'r{rr}_mean_rel_tangential_grad'] = float(rel[inside].mean()) if inside.any() else None
    cl[s] = d
R['clasp_folds_at_manual_centres'] = cl

# ---- visible skin (R-B > 12 and not garment) inside outline, per band ----
bands = {'collar_0_120': (0, 120), 'shoulders_120_260': (120, 260), 'wings_260_480': (260, 480),
         'lower_480_600': (480, 600), 'hem_600_674': (600, 674)}
vs = {}
for s in ['BLbody', 'UEbody', 'UEsettled']:
    im = np.load(f'{OUT}/aligned_{s}_1x.npy'); l = L.lum(im)
    skin = (l >= TH*0.5) & ((im[..., 0] - im[..., 2]) > 12)
    grey_body = (l >= 60) & (l < 236) & ((im[..., 0] - im[..., 2]) <= 12)  # underwear / neutral-skin proxy (BL skin is grey-beige)
    vs[s] = {bn: {'skin_px': int(skin[y0:y1, 40:380].sum()), 'neutral_px': int(grey_body[y0:y1, 40:380].sum())} for bn, (y0, y1) in bands.items()}
R['visible_body'] = vs
json.dump(R, open(LOG+'/gap_measurements2.json', 'w'), indent=1)
print('WROTE')
