# -*- coding: utf-8 -*-
"""Discrimination control for the font-ID test (answers: what IoU does the SAME design reach
at the reference's resolution, and what does a DIFFERENT design reach?).
For each source font A and each column target: synthesise a target = A's glyph placed in the
reference glyph's box at V2 resolution, degraded like the reference (sub-pixel shift, smooth
elastic warp ~0.7 px, 0.6 px gaussian blur, stroke-weight +0.25 px).  Then fit every test
font B with the SAME fitter used on the real reference (5-DOF + stroke-weight allowance).
usage: blender -b --factory-startup --python fid_control.py -- out.json
Deterministic (seed 20260926)."""
import os, sys, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fid_common as C
import fid_core as F

OUT = sys.argv[sys.argv.index("--") + 1]
TG = np.load(os.path.join(C.HERE, "targets.npz"))
TM = json.load(open(os.path.join(C.HERE, "targets.json"), encoding="utf-8"))['targets']
FONTS = json.load(open(os.path.join(C.HERE, "fonts.json"), encoding="utf-8"))
SRC = [0, 1, 5]            # MasaFont Bold, Yuji Boku, GenEiGothic Heavy
TEST = [0, 1, 5, 30, 2]    # + Noto Sans TC Black, AR FangXinShu
KEYS = [k for k in TM if k.startswith('col_')]
rng = np.random.default_rng(20260926)


def tbbox(T):
    ys, xs = np.nonzero(T >= .5)
    return xs.min(), xs.max() + 1, ys.min(), ys.max() + 1


def blur(A, s):
    r = int(math.ceil(3 * s)); x = np.arange(-r, r + 1); k = np.exp(-x * x / (2 * s * s)); k /= k.sum()
    A = np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode='edge'), k, 'valid'), 0, A)
    return np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode='edge'), k, 'valid'), 1, A)


def warp_polys(polys, amp, H, W):
    # smooth displacement field: sum of 3 low-frequency sinusoids per axis
    ph = rng.uniform(0, 2 * math.pi, (2, 3)); fq = rng.uniform(.04, .09, (2, 3, 2))
    out = []
    for P in polys:
        d = []
        for a in range(2):
            s = sum(np.sin(fq[a, i, 0] * P[:, 0] + fq[a, i, 1] * P[:, 1] + ph[a, i]) for i in range(3)) / math.sqrt(3)
            d.append(amp * s)
        out.append(P + np.stack(d, 1))
    return out


def fit(render, fb, T, SS):
    x0, x1, y0, y1 = tbbox(T)
    fw, fh = fb[1] - fb[0], fb[3] - fb[2]
    sx, sy = (x1 - x0) / fw, (y1 - y0) / fh
    tx, ty = (x0 + x1) / 2, (y0 + y1) / 2

    def cost(p, d=0.0):
        if abs(p[2]) > 12 or abs(p[0] - p[1]) > .5:
            return 2.0
        return 1.0 - F.soft_iou(render(p, d), T)
    best = None
    for p0 in ([math.log(sx), math.log(sy), 0, tx, ty], [math.log(math.sqrt(sx * sy))] * 2 + [0, tx, ty]):
        p, v = F.nelder_mead(cost, p0, [.06, .06, 2.0, 1.5, 1.5], iters=220)
        for _ in range(2):
            p, v = F.nelder_mead(cost, p, [.03, .03, 1.0, .75, .75], iters=160)
        if best is None or v < best[1]:
            best = (p, v)
    p, v = best
    bw = (0.0, p, v)
    for i in range(-2, 11):
        d = i / SS
        if d == 0:
            continue
        q, vq = F.nelder_mead(lambda q: cost(q, d), bw[1], [.03, .03, 1.0, .75, .75], iters=120)
        if vq < bw[2]:
            bw = (d, q, vq)
    d, q, _ = bw
    M = render(q, d)
    return dict(soft_iou=F.soft_iou(M, T), bin_iou=F.bin_iou(M, T), offset_px=d,
                soft_iou_noweight=1 - v), M


res = []
G = {}
for fid in set(SRC + TEST):
    G[fid] = {k: F.glyph_polys(FONTS[fid]['path'], TM[k]['char']) for k in KEYS}
for a in SRC:
    for k in KEYS:
        Tref = TG[k]; H, W = Tref.shape
        pa = G[a][k]; fb = F.poly_bbox(pa); c0 = ((fb[0] + fb[1]) / 2, (fb[2] + fb[3]) / 2)
        x0, x1, y0, y1 = tbbox(Tref)
        s = min((x1 - x0) / (fb[1] - fb[0]), (y1 - y0) / (fb[3] - fb[2]))
        p = [math.log(s), math.log(s), 0.0, (x0 + x1) / 2 + rng.uniform(-.5, .5), (y0 + y1) / 2 + rng.uniform(-.5, .5)]
        placed = warp_polys(F.xform(pa, p, c0), 0.7, H, W)
        T = F.raster(placed, H, W, ss=4, weight=1)
        T = np.clip(blur(T, 0.6), 0, 1)
        for b in TEST:
            pb = G[b][k]; fbb = F.poly_bbox(pb); cb = ((fbb[0] + fbb[1]) / 2, (fbb[2] + fbb[3]) / 2)
            render = lambda q, d=0.0, pb=pb, cb=cb, H=H, W=W: F.raster(F.xform(pb, q, cb), H, W, ss=4, weight=int(round(d * 4)))
            m, M = fit(render, fbb, T, 4)
            rec = dict(src=FONTS[a]['name'], src_id=a, test=FONTS[b]['name'], test_id=b, target=k, char=TM[k]['char'], same=(a == b), **m)
            res.append(rec)
            print("%-18s <- %-22s %-22s %s soft %.3f (noW %.3f) bin %.3f" % (FONTS[a]['name'][:18], FONTS[b]['name'][:22], k, TM[k]['char'], m['soft_iou'], m['soft_iou_noweight'], m['bin_iou']))
        json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
same = [r['soft_iou'] for r in res if r['same']]
diff = [r['soft_iou'] for r in res if not r['same']]
print("SAME design: n=%d mean %.3f min %.3f | DIFFERENT: n=%d mean %.3f max %.3f" % (len(same), np.mean(same), np.min(same), len(diff), np.mean(diff), np.max(diff)))
