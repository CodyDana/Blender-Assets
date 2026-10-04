# t8: the judge r7 script re-pointed at the t8 renders / files (outputs in t8/judge_style)
# judge r7: tack rows in the photo camera by phase folding (no blob segmentation): pitch from autocorrelation,
# columns folded by pitch phase, the upper row's tacks dark at phase p0 and the lower row's at p0 + 0.5.
import numpy as np, math, json
from PIL import Image
from scipy import ndimage as ndi
T = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/props/taiko/t8/judge_style/'
w = json.load(open(T + '../silhouette_widths.json'))
cx, cy, a, b = w['head_ellipse_ref_px']
out = {}
for nm, f, (Y0, Y1) in (('photo', 'photo.png', (175, 275)), ('ours', 'ours_aligned.png', (175, 275))):
    L = np.asarray(Image.open(T + f).convert('L')).astype(float)
    X0, X1 = 424, 624
    # flatten the band's ellipse curvature: shift each column so the band is straight
    sub = np.zeros((Y1 - Y0, X1 - X0))
    for i, x in enumerate(range(X0, X1)):
        dy = b * (1 - math.sqrt(max(0, 1 - ((x - cx) / a) ** 2)))
        ys = np.arange(Y0, Y1) - dy
        sub[:, i] = ndi.map_coordinates(L, [ys, np.full_like(ys, x)], order=1)
    dark = sub < 70
    dark = ndi.binary_closing(dark, structure=np.ones((3, 3)), iterations=2)   # fill specular dots
    d = dark.astype(float)
    # pitch: autocorrelation of the column darkness (both rows)
    col = d.sum(0) - d.sum(0).mean()
    ac = np.correlate(col, col, 'full')[len(col) - 1:]
    lag = np.argmax(ac[15:60]) + 15
    # refine pitch by parabola
    y0_, y1_, y2_ = ac[lag - 1], ac[lag], ac[lag + 1]
    p = lag + 0.5 * (y0_ - y2_) / (y0_ - 2 * y1_ + y2_)
    # rows: y profile; split by the upper/lower halves around the band's darkness centroid
    yprof = d.sum(1)
    ys = np.arange(Y0, Y1)
    band = ys[yprof > 0.25 * yprof.max()]
    # fold by phase
    nb = 24
    xs = np.arange(X1 - X0)
    ph = ((xs / p) % 1.0 * nb).astype(int)
    fold = np.zeros((Y1 - Y0, nb))
    for k in range(nb):
        fold[:, k] = d[:, ph == k].mean(1)
    # for each phase the vertical centroid of the dark rows above / below the band middle
    mid = band.mean() - Y0
    upc = [(np.arange(Y1 - Y0)[:int(mid)] * fold[:int(mid), k]).sum() / max(fold[:int(mid), k].sum(), 1e-6) for k in range(nb)]
    upm = [fold[:int(mid), k].sum() for k in range(nb)]
    lom = [fold[int(mid):, k].sum() for k in range(nb)]
    ku = int(np.argmax(upm)); kl = int(np.argmax(lom))
    def cent(k, lo, hi):
        c = fold[lo:hi, k]; return (np.arange(lo, hi) * c).sum() / c.sum() + Y0
    yu = cent(ku, 0, int(mid) + 6); yl = cent(kl, int(mid) - 6, Y1 - Y0)
    # tack width: along the row centre line of the upper row, the horizontal dark run lengths
    def runs(row):
        r = d[int(round(row - Y0))]; out_ = []; c = 0
        for v in r:
            if v: c += 1
            else:
                if c: out_.append(c); c = 0
        return out_
    ru = runs(yu); rl = runs(yl)
    # tack height: vertical extent of upper-row tack at its own phase column
    colu = fold[:, ku] > 0.5; coll = fold[:, kl] > 0.5
    hu = colu.sum(); hl = coll.sum()
    # vertical extent of the whole band at the upper tack phase: top of upper tack to bottom of the lower's at opposite phase
    out[nm] = dict(pitch_px=round(float(p), 2), upper_row_y=round(yu, 1), lower_row_y=round(yl, 1), row_spacing_px=round(yl - yu, 2),
                   phase_offset=round(((kl - ku) % nb) / nb, 3),
                   upper_row_dark_runs=ru, lower_row_dark_runs=rl,
                   tack_height_px_upper_lower=[int(hu), int(hl)])
    Image.fromarray((255 - d * 255).astype(np.uint8)).resize(((X1 - X0) * 3, (Y1 - Y0) * 3), Image.NEAREST).save(T + 'tack_fold_%s.png' % nm)
for nm, r in out.items():
    ru = [x for x in r['upper_row_dark_runs'] if x > 8]; rl = [x for x in r['lower_row_dark_runs'] if x > 8]
    # interior runs only (drop first/last partial)
    wu = np.median(ru[1:-1]) if len(ru) > 2 else None; wl = np.median(rl[1:-1]) if len(rl) > 2 else None
    r['tack_width_px_median_upper_lower'] = [wu, wl]
    wd = np.median([x for x in [wu, wl] if x])
    r['spacing_over_width'] = round(r['row_spacing_px'] / wd, 3)
    r['spacing_over_pitch'] = round(r['row_spacing_px'] / r['pitch_px'], 3)
    r['width_over_pitch'] = round(wd / r['pitch_px'], 3)
    print(nm, json.dumps(r))
json.dump(out, open(T + 'tack_fold.json', 'w'), indent=1, default=float)
