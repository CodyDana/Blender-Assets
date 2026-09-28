# -*- coding: utf-8 -*-
"""Probe 5 - border-rule scanlines with a hue-ratio classifier + corner zooms."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import lib_metro as L
import lib_tag as T

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"
BCP = r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png"
DBG = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/reference_metrology/debug"


def classify2(rgb):
    lu = L.lum(rgb)
    gb = 0.5 * (rgb[..., 1] + rgb[..., 2])
    ratio = rgb[..., 0] / np.maximum(gb, 0.02)
    paper_lum = float(np.percentile(lu, 60))
    ink_lum = float(np.percentile(lu[lu < np.percentile(lu, 12)], 50))
    thr_ink = 0.5 * (paper_lum + ink_lum)
    red = ratio > 1.55
    ink = (lu < thr_ink) | red
    black = ink & ~red
    return red, black, ink, lu, ratio, thr_ink


def runs(row):
    d = np.diff(row.astype(np.int8))
    s = list(np.nonzero(d == 1)[0] + 1); e = list(np.nonzero(d == -1)[0] + 1)
    if row[0]: s.insert(0, 0)
    if row[-1]: e.append(len(row))
    return list(zip(s, e))


def scan_side(red, side, ylo, yhi, lim=0.14):
    """Report the first up-to-3 red runs from the given side, per row."""
    CWl = red.shape[1]
    lim_px = int(lim * CWl)
    rows = range(int(ylo * red.shape[0]), int(yhi * red.shape[0]), 3)
    seqs = []
    for y in rows:
        if side == 'L':
            r = runs(red[y, :lim_px])
            r = [(a, b) for a, b in r]
        else:
            r = runs(red[y, CWl - lim_px:][::-1])
            r = [(a, b) for a, b in r]
        seqs.append((y, r[:3]))
    # summarise the first run
    for k in range(3):
        cs, ws, cnt = [], [], 0
        for y, r in seqs:
            if len(r) > k:
                a, b = r[k]
                cs.append((a + b) / 2.0); ws.append(b - a); cnt += 1
        if cnt < 5:
            print(f"   run#{k}: present in {cnt}/{len(seqs)} rows - none")
            continue
        cs = np.array(cs); ws = np.array(ws)
        print(f"   run#{k}: present {cnt}/{len(seqs)} rows  centre med={np.median(cs):.2f} "
              f"p10={np.percentile(cs,10):.2f} p90={np.percentile(cs,90):.2f} sd={cs.std():.2f} | "
              f"width med={np.median(ws):.2f} p10={np.percentile(ws,10):.1f} p90={np.percentile(ws,90):.1f} max={ws.max():.0f}")


def scan_tb(red, side, xlo, xhi, lim=0.07):
    CHl = red.shape[0]
    lim_px = int(lim * CHl)
    cols = range(int(xlo * red.shape[1]), int(xhi * red.shape[1]), 3)
    for k in range(3):
        cs, ws, cnt = [], [], 0
        for x in cols:
            col = red[:lim_px, x] if side == 'T' else red[CHl - lim_px:, x][::-1]
            r = runs(col)
            if len(r) > k:
                a, b = r[k]
                cs.append((a + b) / 2.0); ws.append(b - a); cnt += 1
        if cnt < 5:
            print(f"   run#{k}: present in {cnt}/{len(cols)} cols - none")
            continue
        cs = np.array(cs); ws = np.array(ws)
        print(f"   run#{k}: present {cnt}/{len(cols)} cols  centre med={np.median(cs):.2f} "
              f"p10={np.percentile(cs,10):.2f} p90={np.percentile(cs,90):.2f} sd={cs.std():.2f} | "
              f"width med={np.median(ws):.2f} p10={np.percentile(ws,10):.1f} p90={np.percentile(ws,90):.1f} max={ws.max():.0f}")


def go(name, path, ours=False):
    a = L.load_stored(path)
    m = T.tag_mask_ours(a, 940) if ours else T.tag_mask_ref(a)
    q = T.fit_quad(m)
    rect, _ = T.rectify(a, q)
    red, black, ink, lu, ratio, thr_ink = classify2(rect)
    print(f"\n########## {name}  (thr_ink={thr_ink:.3f}) red={red.mean()*100:.2f}% black={black.mean()*100:.2f}% ##########")
    print(" LEFT side scan  y 0.22..0.52:");  scan_side(red, 'L', 0.22, 0.52)
    print(" LEFT side scan  y 0.74..0.95:");  scan_side(red, 'L', 0.74, 0.95)
    print(" RIGHT side scan y 0.22..0.52:");  scan_side(red, 'R', 0.22, 0.52)
    print(" RIGHT side scan y 0.74..0.95:");  scan_side(red, 'R', 0.74, 0.95)
    print(" TOP scan x 0.30..0.70:");         scan_tb(red, 'T', 0.30, 0.70)
    print(" BOTTOM scan x 0.30..0.70:");      scan_tb(red, 'B', 0.30, 0.70)
    # corner zooms (DEBUG)
    s = int(0.22 * T.CW)
    for lbl, sl in (("TL", (slice(0, s), slice(0, s))),
                    ("TR", (slice(0, s), slice(T.CW - s, T.CW))),
                    ("BL", (slice(T.CH - s, T.CH), slice(0, s))),
                    ("BR", (slice(T.CH - s, T.CH), slice(T.CW - s, T.CW)))):
        L.save_debug_png(rect[sl[0], sl[1]], os.path.join(DBG, f"DEBUG_NEVER_SHIP_corner_{name}_{lbl}.png"))
    # centre-bottom strip zoom
    L.save_debug_png(rect[int(0.66*T.CH):, int(0.30*T.CW):int(0.72*T.CW)],
                     os.path.join(DBG, f"DEBUG_NEVER_SHIP_lower_{name}.png"))
    return rect, red, black


go("V1", os.path.join(REF, "paperbomb_guide.png"))
go("V2", os.path.join(REF, "paperbomb_guide_v2_real_glyphs.png"))
go("OURS", BCP, ours=True)
