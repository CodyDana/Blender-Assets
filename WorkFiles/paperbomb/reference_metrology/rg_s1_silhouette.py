# -*- coding: utf-8 -*-
"""STAGE 1 - the SILHOUETTE of the real-glyph reference. METROLOGY ONLY.

Settles: aspect, the four chamfers, edge straightness, and whether ANY tear,
nick or folded corner exists anywhere on the outline.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rg_lib as R  # noqa: E402

OUT = {}


def tag_mask(a):
    """Tag edge = half-maximum of the PAPER-to-BACKGROUND warmth step.

    NOTE the p99 trap: red ink reaches warmth 0.80 while the paper sits at 0.25,
    so a percentile-99 'hi' puts the threshold above the paper itself and the
    mask collapses onto the ink.  'hi' must be the PAPER level.
    """
    w = R.warmth(a)
    h, wd = w.shape
    corners = np.concatenate([w[:8, :8].ravel(), w[:8, -8:].ravel(),
                              w[-8:, :8].ravel(), w[-8:, -8:].ravel()])
    lo = float(np.median(corners))                       # background
    core = w[int(0.06 * h):int(0.94 * h), int(0.10 * wd):int(0.90 * wd)]
    hi = float(np.median(core[core > lo + 0.05]))        # paper
    res = {}
    for f in (0.25, 0.35, 0.5, 0.65, 0.8):
        m = w > (lo + f * (hi - lo))
        m = R.fill_holes(R.open_(R.close_(m, 2), 2))
        lab, comps = R.label(m)
        m = R.fill_holes(lab == comps[0]['label'])
        ys = np.flatnonzero(m.any(1)); xs = np.flatnonzero(m.any(0))
        res[f] = dict(w=int(xs[-1] - xs[0] + 1), h=int(ys[-1] - ys[0] + 1),
                      x0=int(xs[0]), y0=int(ys[0]))
    m = w > (lo + 0.5 * (hi - lo))
    m = R.fill_holes(R.open_(R.close_(m, 2), 2))
    lab, comps = R.label(m)
    m = R.fill_holes(lab == comps[0]['label'])
    return m, res, lo, hi


def subpixel_edge(a, mask, side, frac=(0.18, 0.82)):
    w = R.warmth(a)
    h, wd = w.shape
    ys = np.flatnonzero(mask.any(1)); xs = np.flatnonzero(mask.any(0))
    y0, y1 = ys[0], ys[-1]; x0, x1 = xs[0], xs[-1]
    vert = side in ('L', 'R')
    if vert:
        lo = int(y0 + frac[0] * (y1 - y0)); hi = int(y0 + frac[1] * (y1 - y0))
    else:
        lo = int(x0 + frac[0] * (x1 - x0)); hi = int(x0 + frac[1] * (x1 - x0))
    T, P = [], []
    for t in range(lo, hi + 1):
        if vert:
            line = w[t]; idx = np.flatnonzero(mask[t])
        else:
            line = w[:, t]; idx = np.flatnonzero(mask[:, t])
        if len(idx) < 8:
            continue
        e = idx[0] if side in ('L', 'T') else idx[-1]
        sgn = +1 if side in ('L', 'T') else -1
        n = len(line)
        ins = [e + sgn * k for k in range(3, 9)]
        outs = [e - sgn * k for k in range(1, 7)]
        ins = [k for k in ins if 0 <= k < n]
        outs = [k for k in outs if 0 <= k < n]
        if len(ins) < 3 or len(outs) < 3:
            continue
        vi = float(np.median(line[ins])); vo = float(np.median(line[outs]))
        if vi - vo < 0.02:
            continue
        tgt = 0.5 * (vi + vo)
        c = None
        for k in range(8, -9, -1):
            k0 = e - sgn * k; k1 = e - sgn * (k - 1)
            if not (0 <= k0 < n and 0 <= k1 < n):
                continue
            v0, v1 = line[k0], line[k1]
            if v0 <= tgt < v1:
                f = 0.0 if v1 == v0 else (tgt - v0) / (v1 - v0)
                c = k0 + f * (k1 - k0)
                break
        if c is None:
            continue
        T.append(float(t)); P.append(float(c) + 0.5)
    return np.array(T), np.array(P)


def main():
    a, info = R.read_stored(R.RG)
    H, W = a.shape[:2]
    OUT['image'] = dict(path=R.RG, width=W, height=H)

    mask, sweep, wlo, whi = tag_mask(a)
    OUT['threshold_sweep'] = {str(k): v for k, v in sweep.items()}
    OUT['warmth_range'] = [round(wlo, 4), round(whi, 4)]

    sides = {}
    for s in ('L', 'R', 'T', 'B'):
        T, P = subpixel_edge(a, mask, s)
        aa, bb, res, keep = R.robust_fit(T, P)
        sides[s] = dict(a=aa, b=bb, n=int(len(T)),
                        rms=float(np.sqrt((res[keep] ** 2).mean())),
                        maxdev=float(np.abs(res[keep]).max()),
                        angle_deg=float(np.degrees(np.arctan(aa))),
                        T=T, P=P, res=res, keep=keep)
    OUT['sides'] = {s: dict(a=round(v['a'], 6), b=round(v['b'], 4), n=v['n'],
                            rms_px=round(v['rms'], 4), maxdev_px=round(v['maxdev'], 4),
                            angle_deg=round(v['angle_deg'], 4)) for s, v in sides.items()}

    def isect_vh(sv, sh):
        av, bv = sides[sv]['a'], sides[sv]['b']
        ah, bh = sides[sh]['a'], sides[sh]['b']
        y = (ah * bv + bh) / (1 - ah * av)
        return (av * y + bv, y)

    TL = isect_vh('L', 'T'); TR = isect_vh('R', 'T')
    BL = isect_vh('L', 'B'); BR = isect_vh('R', 'B')
    Wpx = 0.5 * ((TR[0] - TL[0]) + (BR[0] - BL[0]))
    Hpx = 0.5 * ((BL[1] - TL[1]) + (BR[1] - TR[1]))
    OUT['virtual_corners'] = dict(TL=[round(v, 3) for v in TL], TR=[round(v, 3) for v in TR],
                                  BL=[round(v, 3) for v in BL], BR=[round(v, 3) for v in BR])
    OUT['tag_px'] = dict(w=round(Wpx, 3), h=round(Hpx, 3))
    aspect = Wpx / Hpx
    OUT['aspect'] = round(aspect, 5)
    ppmm = Wpx / R.CARD_W_MM
    OUT['ppmm'] = round(ppmm, 4)
    OUT['card_h_mm_from_aspect'] = round(R.CARD_W_MM / aspect, 3)
    OUT['aspect_sweep'] = {str(k): round(v['w'] / v['h'], 5) for k, v in sweep.items()}

    ys = np.flatnonzero(mask.any(1)); xs = np.flatnonzero(mask.any(0))
    y0i, y1i = int(ys[0]), int(ys[-1]); x0i, x1i = int(xs[0]), int(xs[-1])
    cham = {}
    for name, sv, sh, vsign, hsign in (('TL', 'L', 'T', +1, +1), ('TR', 'R', 'T', -1, +1),
                                       ('BL', 'L', 'B', +1, -1), ('BR', 'R', 'B', -1, -1)):
        pts = []
        band = int(round(0.16 * Hpx))
        ylo, yhi = (y0i, y0i + band) if hsign > 0 else (y1i - band, y1i)
        for y in range(ylo, yhi + 1):
            idx = np.flatnonzero(mask[y])
            if len(idx) < 8:
                continue
            e = idx[0] if sv == 'L' else idx[-1]
            pts.append((float(e) + (0.0 if sv == 'L' else 1.0), float(y)))
        xband = int(round(0.36 * Wpx))
        xlo, xhi = (x0i, x0i + xband) if vsign > 0 else (x1i - xband, x1i)
        for x in range(xlo, xhi + 1):
            idx = np.flatnonzero(mask[:, x])
            if len(idx) < 8:
                continue
            e = idx[0] if sh == 'T' else idx[-1]
            pts.append((float(x), float(e) + (0.0 if sh == 'T' else 1.0)))
        pts = np.array(sorted(set(map(tuple, pts))))
        dv = (pts[:, 0] - (sides[sv]['a'] * pts[:, 1] + sides[sv]['b'])) * vsign
        dh = (pts[:, 1] - (sides[sh]['a'] * pts[:, 0] + sides[sh]['b'])) * hsign
        sel = (dv > 1.2) & (dh > 1.2)
        n = int(sel.sum())
        rec = dict(n_bevel_pts=n)
        if n >= 6:
            bp = pts[sel]
            m, c, res, keep = R.robust_fit(bp[:, 0], bp[:, 1])
            rec['bevel_slope'] = round(float(m), 4)
            rec['bevel_angle_deg'] = round(float(np.degrees(np.arctan(abs(m)))), 3)
            rec['bevel_rms_px'] = round(float(np.sqrt((res[keep] ** 2).mean())), 4)
            rec['bevel_maxdev_px'] = round(float(np.abs(res[keep]).max()), 4)
            av, bv = sides[sv]['a'], sides[sv]['b']
            yv = (m * bv + c) / (1 - m * av); xv = av * yv + bv
            ah, bh = sides[sh]['a'], sides[sh]['b']
            xh = (bh - c) / (m - ah); yh = ah * xh + bh
            vc = {'TL': TL, 'TR': TR, 'BL': BL, 'BR': BR}[name]
            legv = float(np.hypot(xv - vc[0], yv - vc[1]))
            legh = float(np.hypot(xh - vc[0], yh - vc[1]))
            chord = float(np.hypot(xv - xh, yv - yh))
            rec.update(leg_vertical_px=round(legv, 3), leg_horizontal_px=round(legh, 3),
                       chord_px=round(chord, 3),
                       leg_vertical_mm=round(legv / ppmm, 3),
                       leg_horizontal_mm=round(legh / ppmm, 3),
                       chord_mm=round(chord / ppmm, 3),
                       end_on_vertical=[round(xv, 3), round(yv, 3)],
                       end_on_horizontal=[round(xh, 3), round(yh, 3)])
        cham[name] = rec
    OUT['chamfers'] = cham
    print('CHAMFER DIAG')
    print(json.dumps(cham, indent=1))

    P = [cham['TL']['end_on_horizontal'], cham['TR']['end_on_horizontal'],
         cham['TR']['end_on_vertical'], cham['BR']['end_on_vertical'],
         cham['BR']['end_on_horizontal'], cham['BL']['end_on_horizontal'],
         cham['BL']['end_on_vertical'], cham['TL']['end_on_vertical']]
    P = np.array(P, float)
    OUT['octagon_vertices_px'] = [[round(v, 3) for v in p] for p in P]

    bpts = []
    for y in range(y0i, y1i + 1):
        idx = np.flatnonzero(mask[y])
        if len(idx):
            bpts.append((float(idx[0]), float(y), 'L'))
            bpts.append((float(idx[-1]) + 1.0, float(y), 'R'))
    for x in range(x0i, x1i + 1):
        idx = np.flatnonzero(mask[:, x])
        if len(idx):
            bpts.append((float(x), float(idx[0]), 'T'))
            bpts.append((float(x), float(idx[-1]) + 1.0, 'B'))

    n = len(P)
    seg = [(P[i], P[(i + 1) % n]) for i in range(n)]

    def sd_poly(px_, py_):
        best = 1e9
        for (p1, p2) in seg:
            dx = p2[0] - p1[0]; dy = p2[1] - p1[1]
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px_ - p1[0]) * dx + (py_ - p1[1]) * dy) / L2))
            qx = p1[0] + t * dx; qy = p1[1] + t * dy
            d = float(np.hypot(px_ - qx, py_ - qy))
            if d < best:
                best = d
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = P[i]; xj, yj = P[j]
            if ((yi > py_) != (yj > py_)) and (px_ < (xj - xi) * (py_ - yi) / (yj - yi + 1e-12) + xi):
                inside = not inside
            j = i
        return -best if inside else best

    devs = []
    for (bx, by, tag) in bpts:
        devs.append((sd_poly(bx, by), bx, by, tag))
    devs.sort(key=lambda d: d[0])
    dd = np.array([d[0] for d in devs])
    OUT['outline_deviation'] = dict(
        n_points=len(devs),
        rms_px=round(float(np.sqrt((dd ** 2).mean())), 4),
        p01_px=round(float(np.percentile(dd, 1)), 4),
        p99_px=round(float(np.percentile(dd, 99)), 4),
        min_px=round(float(dd.min()), 4), max_px=round(float(dd.max()), 4),
        min_mm=round(float(dd.min()) / ppmm, 4), max_mm=round(float(dd.max()) / ppmm, 4),
        worst_inward=[[round(d[0], 3), round(d[1], 1), round(d[2], 1), d[3]] for d in devs[:12]],
        worst_outward=[[round(d[0], 3), round(d[1], 1), round(d[2], 1), d[3]] for d in devs[-12:]],
    )
    reg = {}
    third = Hpx / 3.0
    checks = (('left_top', lambda x, y: x < TL[0] + 6 and y < TL[1] + third),
              ('left_mid', lambda x, y: x < TL[0] + 6 and TL[1] + third <= y < TL[1] + 2 * third),
              ('left_bot', lambda x, y: x < TL[0] + 6 and y >= TL[1] + 2 * third),
              ('right_top', lambda x, y: x > TR[0] - 6 and y < TL[1] + third),
              ('right_mid', lambda x, y: x > TR[0] - 6 and TL[1] + third <= y < TL[1] + 2 * third),
              ('right_bot', lambda x, y: x > TR[0] - 6 and y >= TL[1] + 2 * third),
              ('top_all', lambda x, y: y < TL[1] + 6),
              ('bottom_all', lambda x, y: y > BL[1] - 6))
    for nm, sel in checks:
        v = [d[0] for d in devs if sel(d[1], d[2])]
        if v:
            v = np.array(v)
            reg[nm] = dict(n=len(v), mean=round(float(v.mean()), 3),
                           min=round(float(v.min()), 3), max=round(float(v.max()), 3),
                           min_mm=round(float(v.min()) / ppmm, 3),
                           max_mm=round(float(v.max()) / ppmm, 3))
    OUT['outline_deviation_regions'] = reg

    def runs_inboard(tagsel, keyidx, thresh_px):
        pts = [(d[1], d[2], d[0]) for d in devs if d[3] == tagsel]
        pts.sort(key=lambda p: p[keyidx])
        cur = 0; tot = 0; runs = []
        for (_, _, dv) in pts:
            if dv < -thresh_px:
                cur += 1; tot += 1
            else:
                if cur:
                    runs.append(cur)
                cur = 0
        if cur:
            runs.append(cur)
        return dict(n_inboard=tot, n_total=len(pts),
                    longest_run_px=max(runs) if runs else 0,
                    longest_run_mm=round((max(runs) if runs else 0) / ppmm, 3),
                    n_runs=len(runs))
    OUT['damage_test'] = {
        'threshold_px': 1.5,
        'threshold_mm': round(1.5 / ppmm, 3),
        'L': runs_inboard('L', 1, 1.5),
        'R': runs_inboard('R', 1, 1.5),
        'T': runs_inboard('T', 0, 1.5),
        'B': runs_inboard('B', 0, 1.5),
    }

    vis = a.copy()
    e = mask ^ R.erode(mask, 1)
    vis[e] = [0.0, 0.85, 0.0]
    R.save_debug(vis, "s1_tagmask", scale=2)
    for name, cxy in (('TL', TL), ('TR', TR), ('BL', BL), ('BR', BR)):
        cx, cy = cxy
        x0 = int(cx - 6) if name in ('TL', 'BL') else int(cx - 40)
        y0 = int(cy - 6) if name in ('TL', 'TR') else int(cy - 40)
        x0 = max(0, min(W - 46, x0)); y0 = max(0, min(H - 46, y0))
        R.save_debug(a[y0:y0 + 46, x0:x0 + 46], "s1_corner_%s" % name, scale=8)

    with open(os.path.join(HERE, "rg_s1_silhouette.json"), "w", encoding="utf-8") as fh:
        json.dump(OUT, fh, indent=1, ensure_ascii=False)
    pr = {k: v for k, v in OUT.items() if k != 'image'}
    print(json.dumps(pr, indent=1))


main()
