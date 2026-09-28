# -*- coding: utf-8 -*-
"""Extract every kanji target from V2 as a soft ink-coverage map (V2 px).
Output: targets.npz + targets.json + view/targets_*.png"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fid_common as C
import fid_core as F

S6 = json.load(open(os.path.join(C.MET, "rg_s6_columns.json"), encoding="utf-8"))
S3 = json.load(open(os.path.join(C.MET, "rg_s3_geometry.json"), encoding="utf-8"))
S8 = json.load(open(os.path.join(C.MET, "rg_s8_seals.json"), encoding="utf-8"))

a = C.load_v2()
H, W = a.shape[:2]
k, r, inks = F.unmix(a)
print("inks", inks)
PP = C.PPMM


def a2mm2(n):
    return n / (PP * PP)


def zone(x0f, x1f, y0f, y1f):
    z = np.zeros((H, W), bool)
    z[int(C.YT + y0f * C.HPX):int(C.YT + y1f * C.HPX), int(C.XL + x0f * C.WPX):int(C.XL + x1f * C.WPX)] = True
    return z


fl = C.XL + S3['rules']['L']['inset_px']
fr = C.XR - 1 - S3['rules']['R']['inset_px']
rule_band = np.zeros((H, W), bool)
for cen_ in (fl, fr):
    x = int(round(cen_)); rule_band[:, max(0, x - 2):x + 3] = True

CDEF = dict(
    col_TL_hidonjutsu=((.04, .28, .015, .36), "火遁術"),
    col_TR_bakuenjin=((.70, .96, .015, .36), "爆炎陣"),
    col_BR_shoujin=((.70, .96, .625, .83), "焼尽"),
    col_BC_shungou=((.36, .64, .68, .93), "瞬業"),
)
black = k >= .5
targets = {}
meta = {}
# exclusion masks: the centre 爆 (full-card component analysis) and the flame emblem
_lab, _comps = F.label(black)
_zc = zone(.05, .95, .30, .66)
foreign = np.zeros((H, W), bool)
for c in _comps:
    ccx = (c['cx'] - C.XL) / C.WPX; ccy = (c['cy'] - C.YT) / C.HPX
    if c['n'] > 100 and .30 < ccy < .66 and .1 < ccx < .9:      # centre 爆 bodies
        foreign |= _lab == c['label']
    if .28 < ccx < .72 and .09 < ccy < .29 and c['n'] > 10:     # flame emblem
        foreign |= _lab == c['label']
foreign = F.dilate(foreign, 2)
for nm, (zf, chars) in CDEF.items():
    zm = zone(*zf)
    m = black & zm & ~rule_band & ~foreign
    lab, comps = F.label(F.dilate(m, 1))
    keep = np.zeros((H, W), bool)
    for c in comps:
        if a2mm2(int((m & (lab == c['label'])).sum())) > 2.0:
            keep |= m & (lab == c['label'])
    care = F.dilate(keep, 2) & zm & ~rule_band
    col = S6['columns'][nm]
    for gi, g in enumerate(col['glyphs']):
        # glyph rows: rg_s6 boxes (mm -> px). x window: column zone.
        _, y0 = C.mm2px(0, g['y0_mm']); _, y1 = C.mm2px(0, g['y1_mm'])
        y0 = int(round(y0)); y1 = int(round(y1))
        band = np.zeros((H, W), bool); band[y0:y1, :] = True
        T = np.where(care & band, k, 0.0)
        ys, xs = np.nonzero(T >= .5)
        key = "%s_%d" % (nm, gi)
        wx0 = max(int(C.XL + zf[0] * C.WPX), xs.min() - 10); wx1 = min(int(C.XL + zf[1] * C.WPX), xs.max() + 11)
        wy0 = y0 - 8; wy1 = y1 + 8
        targets[key] = T[wy0:wy1, wx0:wx1]
        meta[key] = dict(char=chars[gi], kind="column", ink="black", win=[int(wy0), int(wy1), int(wx0), int(wx1)],
                         band=[int(y0), int(y1)], bbox_px=[int(xs.min()), int(xs.max() + 1), int(ys.min()), int(ys.max() + 1)],
                         area_px=float(T.sum()), em_mm=g['em_mm'])
        print(key, chars[gi], meta[key]['win'], meta[key]['bbox_px'])

# ------------------------------------------------ centre 爆 (inside the red ring)
zc = zone(.05, .95, .30, .66)
m = black & zc
lab, comps = F.label(F.dilate(m, 1))
keep = np.zeros((H, W), bool)
for c in comps:
    if a2mm2(int((m & (lab == c['label'])).sum())) > 15.0:
        keep |= m & (lab == c['label'])
care = F.dilate(keep, 2) & zc
T = np.where(care, k, 0.0)
ys, xs = np.nonzero(T >= .5)
wy0, wy1, wx0, wx1 = ys.min() - 10, ys.max() + 11, xs.min() - 10, xs.max() + 11
targets["centre_baku"] = T[wy0:wy1, wx0:wx1]
meta["centre_baku"] = dict(char="爆", kind="centre", ink="black", win=[int(wy0), int(wy1), int(wx0), int(wx1)],
                           band=[int(wy0), int(wy1)], bbox_px=[int(xs.min()), int(xs.max() + 1), int(ys.min()), int(ys.max() + 1)],
                           area_px=float(T.sum()))
print("centre", meta["centre_baku"])

# ------------------------------------------------ small seal 火道 (red on paper)
sb = S8['seal_small']['outer_box_mm']
x0p, y0p = C.mm2px(sb[0], sb[2]); x1p, y1p = C.mm2px(sb[1], sb[3])
zs = np.zeros((H, W), bool); zs[int(y0p) - 1:int(y1p) + 2, int(x0p) - 1:int(x1p) + 2] = True
red = (r >= .5) & zs
lab, comps = F.label(red)
frame = comps[0]
print("seal comps", [(c['n'], c['x0'], c['x1'], c['y0'], c['y1']) for c in comps[:8]])
txt = np.zeros((H, W), bool)
for c in comps[1:]:
    if c['n'] >= 3 and c['x0'] > frame['x0'] + 1 and c['x1'] < frame['x1'] - 1 and c['y0'] > frame['y0'] + 1 and c['y1'] < frame['y1'] - 1:
        txt |= lab == c['label']
care = F.dilate(txt, 1) & ~F.dilate(lab == frame['label'], 0)
T = np.where(care, r, 0.0)
ys, xs = np.nonzero(T >= .5)
# split into 火 (top) and 道 (bottom) at the emptiest row between them
rows = (T >= .5).sum(1)
ymid = int((ys.min() + ys.max()) / 2)
cut = ys.min() + 4 + int(np.argmin(rows[ys.min() + 4:ys.max() - 4]))
for key, ch, ya, yb in (("seal_hi", "火", ys.min(), cut), ("seal_michi", "道", cut, ys.max() + 1)):
    band = np.zeros((H, W), bool); band[ya:yb] = True
    Tg = np.where(band, T, 0.0)
    yy, xx = np.nonzero(Tg >= .5)
    wy0, wy1, wx0, wx1 = ya - 4, yb + 4, xs.min() - 4, xs.max() + 5
    targets[key] = Tg[wy0:wy1, wx0:wx1]
    meta[key] = dict(char=ch, kind="seal", ink="red", win=[int(wy0), int(wy1), int(wx0), int(wx1)], band=[int(ya), int(yb)],
                     bbox_px=[int(xx.min()), int(xx.max() + 1), int(yy.min()), int(yy.max() + 1)], area_px=float(Tg.sum()))
    print(key, meta[key])

np.savez_compressed(os.path.join(C.HERE, "targets.npz"), **targets)
json.dump(dict(source=C.V2, source_sha256=C.sha256(C.V2), inks=inks, ppmm=PP, targets=meta),
          open(os.path.join(C.HERE, "targets.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
os.makedirs(os.path.join(C.HERE, "view"), exist_ok=True)
for key, T in targets.items():
    C.save_png(1 - T, os.path.join(C.HERE, "view", "target_%s.png" % key), scale=6 if key != "centre_baku" else 3)
print("done")
