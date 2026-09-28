# -*- coding: utf-8 -*-
"""Comparison sheet: per target one row
   reference (4x) | best brush font (MasaFont / Yuji Boku) | overlay | best overall font | overlay
Overlay colours: black = both, red = reference only, blue = font only.
usage: blender -b --factory-startup --python fid_sheet3.py -- out.png runs3/g*.json"""
import os, sys, json, math, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fid_common as C
import fid_core as F

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
R = []
for pat in argv[1:]:
    for p in sorted(glob.glob(os.path.join(C.HERE, pat))):
        R += json.load(open(p, encoding="utf-8"))
R = [r for r in R if 'soft_iou' in r and r['font_id'] != 'template']
TG = np.load(os.path.join(C.HERE, "targets.npz"))
TM = json.load(open(os.path.join(C.HERE, "targets.json"), encoding="utf-8"))['targets']
FONTS = json.load(open(os.path.join(C.HERE, "fonts.json"), encoding="utf-8"))
LBL = "C:/Windows/Fonts/arial.ttf"
_lc = {}


def label(txt, h=18):
    """Rasterise ASCII text with arial outlines -> coverage (h px tall)."""
    parts = []
    for ch in txt:
        if ch == ' ':
            parts.append(np.zeros((h, int(h * .3)))); continue
        if ch not in _lc:
            _lc[ch] = F.glyph_polys(LBL, ch)
        P = _lc[ch]
        if not P:
            parts.append(np.zeros((h, int(h * .3)))); continue
        fb = F.poly_bbox(P)
        s = h * 0.72
        w = max(2, int(math.ceil((fb[1] - fb[0]) * s)) + 2)
        Q = [np.stack([(q[:, 0] - fb[0]) * s + 1, (q[:, 1] + 0.78) * s + h * .08], 1) for q in P]
        parts.append(F.raster(Q, h, w, ss=3))
    return np.concatenate(parts, 1) if parts else np.zeros((h, 4))


def render_font(r, key, f=4):
    T = TG[key]; H, W = T.shape
    polys = F.glyph_polys(r['path'] if 'path' in r else FONTS[int(r['font_id'])]['path'], r['char'])
    fb = F.poly_bbox(polys); c0 = ((fb[0] + fb[1]) / 2, (fb[2] + fb[3]) / 2)
    w = (None if os.environ.get("FID_RAW") else r.get("weighted")) or dict(params=r["params"], offset_px=0.0)
    p = w['params']; d = w['offset_px']
    return F.raster(F.xform(polys, [p[0] + math.log(f), p[1] + math.log(f), p[2], p[3] * f, p[4] * f], c0), H * f, W * f, ss=2, weight=int(round(d * 2 * f)))


def score(r):
    return ((None if os.environ.get("FID_RAW") else r.get("weighted")) or r)["soft_iou"]


def overlay(T, M):
    t = T >= .5; m = M >= .5
    im = np.ones(T.shape + (3,))
    im[t & ~m] = [.9, .1, .1]; im[m & ~t] = [.15, .3, .95]; im[t & m] = [0, 0, 0]
    return im


def gray(A):
    return np.repeat((1 - np.clip(A, 0, 1))[..., None], 3, 2)


rows = []
order = [k for k in TM if k.startswith('col_')] + ['centre_baku', 'seal_hi', 'seal_michi']
CELL = 240
for key in order:
    rs = [r for r in R if r['target'] == key]
    brush = max([r for r in rs if int(r['font_id']) in (0, 1)], key=score)
    best = max(rs, key=score)
    f = 4 if key != 'centre_baku' else 1
    T4 = F.upsample_bilinear(TG[key], f)
    Mb = render_font(brush, key, f); Mo = render_font(best, key, f)
    panels = [gray(T4), gray(Mb), overlay(T4, Mb), gray(Mo), overlay(T4, Mo)]
    caps = ["ref %s" % key.replace('col_', ''), "%s %.2f" % (brush['font'][:14], score(brush)), "overlay",
            "%s %.2f" % (best['font'][:14], score(best)), "overlay"]
    cells = []
    for pnl, cap in zip(panels, caps):
        h, w = pnl.shape[:2]
        s = min(CELL / h, CELL / w)
        yi = np.clip(((np.arange(int(h * s)) + .5) / s).astype(int), 0, h - 1)
        xi = np.clip(((np.arange(int(w * s)) + .5) / s).astype(int), 0, w - 1)
        pz = pnl[yi][:, xi]
        c = np.ones((CELL + 24, CELL + 10, 3))
        oy = (CELL - pz.shape[0]) // 2; ox = (CELL - pz.shape[1]) // 2 + 5
        c[oy:oy + pz.shape[0], ox:ox + pz.shape[1]] = pz
        L = label(cap, 18)[:, :CELL + 6]
        c[CELL + 3:CELL + 21, 2:2 + L.shape[1]] *= (1 - L[..., None])
        cells.append(c)
    row = np.concatenate(cells, 1)
    rows.append(row); rows.append(np.full((4, row.shape[1], 3), .75))
    print(key, brush['font'], score(brush), best['font'], score(best))
sheet = np.concatenate(rows, 0)
hdr = np.ones((40, sheet.shape[1], 3))
L = label("reference | best brush font (MasaFont/Yuji Boku) | overlay | best font overall | overlay    black=both  red=reference only  blue=font only   (score = soft IoU)", 20)
hdr[10:30, 6:6 + min(L.shape[1], sheet.shape[1] - 12)] *= (1 - L[..., None][:, :sheet.shape[1] - 12])
C.save_png(np.concatenate([hdr, sheet], 0), os.path.join(C.HERE, OUT))
print("saved", OUT, sheet.shape)
