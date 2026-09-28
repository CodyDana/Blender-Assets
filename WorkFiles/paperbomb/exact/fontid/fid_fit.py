# -*- coding: utf-8 -*-
"""Fit every candidate font's glyph to every V2 kanji target.
usage: blender -b --factory-startup --python fid_fit.py -- <out.json> <font_id> [<font_id> ...]
font_id = index into fonts.json (written by fid_fontlist.py), or 'template' for the
centre-爆 -> column-爆 self-consistency ceiling."""
import os, sys, json, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fid_common as C
import fid_core as F

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0]
IDS = argv[1:]
TG = np.load(os.path.join(C.HERE, "targets.npz"))
TM = json.load(open(os.path.join(C.HERE, "targets.json"), encoding="utf-8"))['targets']
FONTS = json.load(open(os.path.join(C.HERE, "fonts.json"), encoding="utf-8"))
ONLY = os.environ.get("FID_ONLY")          # optional comma list of target keys


def tbbox(T):
    ys, xs = np.nonzero(T >= .5)
    return xs.min(), xs.max() + 1, ys.min(), ys.max() + 1


def fit_one(render, fb, T, n_restart=2):
    """render(p) -> coverage at T's shape.  fb = model ink bbox (x0,x1,y0,y1) in model units."""
    x0, x1, y0, y1 = tbbox(T)
    fw, fh = fb[1] - fb[0], fb[3] - fb[2]
    sx, sy = (x1 - x0) / fw, (y1 - y0) / fh
    tx, ty = (x0 + x1) / 2, (y0 + y1) / 2

    def cost(p):
        if abs(p[2]) > 12 or abs(p[0] - p[1]) > .5:
            return 2.0
        return 1.0 - F.soft_iou(render(p), T)
    best = None
    inits = [[math.log(sx), math.log(sy), 0, tx, ty],
             [math.log(math.sqrt(sx * sy))] * 2 + [0, tx, ty]]
    for p0 in inits:
        p, v = F.nelder_mead(cost, p0, [.06, .06, 2.0, 1.5, 1.5], iters=220)
        for _ in range(n_restart):
            p, v = F.nelder_mead(cost, p, [.03, .03, 1.0, .75, .75], iters=160)
        if best is None or v < best[1]:
            best = (p, v)
    return best


def metrics(render4, p, T, render):
    M = render(p)
    f = 4
    M4 = render4(p)
    T4 = F.upsample_bilinear(T, f)
    ed = F.edge_dist(M4, T4, f)
    return dict(soft_iou=F.soft_iou(M, T), bin_iou=F.bin_iou(M, T), edge_mean_px=ed['mean'],
                edge_p95_px=ed['p95'], edge_max_px=ed['max'],
                edge_mean_mm=(ed['mean'] / C.PPMM if ed['mean'] is not None else None),
                edge_p95_mm=(ed['p95'] / C.PPMM if ed['p95'] is not None else None),
                ink_ratio_model_over_ref=float(M.sum() / max(T.sum(), 1e-9)),
                sx_over_sy=math.exp(p[0] - p[1]), rot_deg=float(p[2])), M


results = []
if os.path.exists(OUT):
    results = json.load(open(OUT, encoding="utf-8"))
done = {(r['font_id'], r['target']) for r in results}
PREV = os.path.join(C.HERE, "fitprev"); os.makedirs(PREV, exist_ok=True)
for fid in IDS:
    t0 = time.time()
    if fid == 'template':
        # the centre 爆 used as the "font" for the column 爆 (and vice versa)
        cen = TG['centre_baku']; cm = TM['centre_baku']
        samp = F.template_sampler(cen, 0, 0)
        cb = tbbox(cen)
        c0 = ((cb[0] + cb[1]) / 2, (cb[2] + cb[3]) / 2)
        pairs = [("col_TR_bakuenjin_0", samp, cb, c0, "centre 爆 as template")]
        col = TG['col_TR_bakuenjin_0']
        samp2 = F.template_sampler(col, 0, 0); cb2 = tbbox(col)
        pairs.append(("centre_baku", samp2, cb2, ((cb2[0] + cb2[1]) / 2, (cb2[2] + cb2[3]) / 2), "column 爆 as template"))
        for key, sp, fb, cc, note in pairs:
            T = TG[key]; Hh, Ww = T.shape
            render = lambda p, sp=sp, cc=cc, Hh=Hh, Ww=Ww: F.raster_template(sp, p, cc, Hh, Ww, ss=4)
            render4 = lambda p, sp=sp, cc=cc, Hh=Hh, Ww=Ww: F.raster_template(sp, [p[0] + math.log(4), p[1] + math.log(4), p[2], p[3] * 4, p[4] * 4], cc, Hh * 4, Ww * 4, ss=2)
            (p, v) = fit_one(render, fb, T, n_restart=1)
            m, M = metrics(render4, p, T, render)
            rec = dict(font_id='template', font=note, target=key, char=TM[key]['char'], params=[float(x) for x in p], **m)
            results.append(rec)
            print(key, note, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()}))
            C.save_png(np.stack([1 - T, 1 - np.maximum(T, M), 1 - M], 2), os.path.join(PREV, "tmpl_%s.png" % key), scale=4 if key != 'centre_baku' else 2)
        json.dump(results, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        continue
    fr = FONTS[int(fid)]
    for key in TM:
        if ONLY and key not in ONLY.split(","):
            continue
        ch = TM[key]['char']
        if (int(fid), key) in done:
            continue
        if ch not in fr['covered']:
            results.append(dict(font_id=int(fid), font=fr['name'], target=key, char=ch, missing=True))
            continue
        polys = F.glyph_polys(fr['path'], ch)
        if not polys:
            results.append(dict(font_id=int(fid), font=fr['name'], target=key, char=ch, empty=True)); continue
        fb = F.poly_bbox(polys)
        c0 = ((fb[0] + fb[1]) / 2, (fb[2] + fb[3]) / 2)
        T = TG[key]; Hh, Ww = T.shape
        SS = 2 if key == 'centre_baku' else 4
        render = lambda p, d=0.0: F.raster(F.xform(polys, p, c0), Hh, Ww, ss=SS, weight=int(round(d * SS)))
        render4 = lambda p, d=0.0: F.raster(F.xform(polys, [p[0] + math.log(4), p[1] + math.log(4), p[2], p[3] * 4, p[4] * 4], c0), Hh * 4, Ww * 4, ss=2, weight=int(round(d * 8)))
        ts = time.time()
        (p, v) = fit_one(render, fb, T, n_restart=1 if key == 'centre_baku' else 2)
        m, M = metrics(render4, p, T, render)
        # stroke-weight allowance: offset the outline by d V2-px (both directions), refit
        dstep = 1.0 / SS
        dgrid = [i * dstep for i in range(-2 if SS == 4 else -1, (11 if SS == 4 else 6))]
        if key == 'centre_baku':
            dgrid = [i * 0.5 * (Hh / 60.0) for i in range(-1, 7)]      # centre glyph is ~4x the columns
            dgrid = sorted(set(round(x * SS) / SS for x in dgrid))
        bestw = (0.0, p, v)

        def cost_w(q, d):
            if abs(q[2]) > 12 or abs(q[0] - q[1]) > .5:
                return 2.0
            return 1.0 - F.soft_iou(render(q, d), T)
        for d in dgrid:
            if d == 0:
                continue
            q, vq = F.nelder_mead(lambda q: cost_w(q, d), bestw[1] if abs(d - bestw[0]) <= dstep * 1.01 else p,
                                  [.03, .03, 1.0, .75, .75], iters=120)
            if vq < bestw[2]:
                bestw = (d, q, vq)
        d_w, p_w, _ = bestw
        mw, Mw = metrics(lambda q: render4(q, d_w), p_w, T, lambda q: render(q, d_w))
        rec = dict(font_id=int(fid), font=fr['name'], path=fr['path'], target=key, char=ch,
                   params=[float(x) for x in p], fit_seconds=round(time.time() - ts, 1), **m,
                   weighted=dict(offset_px=d_w, offset_mm=d_w / C.PPMM, params=[float(x) for x in p_w], **mw))
        results.append(rec)
        print("%-3s %-28s %-22s %s soft %.3f bin %.3f edge %.2fpx p95 %.2f aniso %.2f rot %.1f | W d=%.2f soft %.3f bin %.3f edge %.2f/%.2f (%.1fs)" % (
            fid, fr['name'][:28], key, ch, m['soft_iou'], m['bin_iou'], m['edge_mean_px'], m['edge_p95_px'], m['sx_over_sy'], m['rot_deg'],
            d_w, mw['soft_iou'], mw['bin_iou'], mw['edge_mean_px'], mw['edge_p95_px'], time.time() - ts))
        M = Mw
        C.save_png(np.stack([1 - T, 1 - np.maximum(T, M), 1 - M], 2),
                   os.path.join(PREV, "f%02d_%s.png" % (int(fid), key)), scale=4 if key != 'centre_baku' else 2)
        json.dump(results, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("font", fid, "done in %.1fs" % (time.time() - t0))
json.dump(results, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
