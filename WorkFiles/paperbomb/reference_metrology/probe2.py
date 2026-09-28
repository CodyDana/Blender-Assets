# -*- coding: utf-8 -*-
"""Probe 2 - tag outline, rotation/keystone detection, corner clips."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import lib_metro as L

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"
SCRATCH = r"C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/70fec35b-8f87-4dbe-ba33-6e5ba8c5d846/scratchpad"


def tag_mask(a):
    rgb = a[..., :3]
    lu = L.lum(rgb); st = L.sat(rgb)
    # paper is cream: lower luminance than the white bg AND/OR saturated
    m = (lu < 0.965) | (st > 0.045)
    m = L.close_(m, 2)
    m = L.open_(m, 2)
    lab, comps = L.label_components(m)
    big = comps[0]
    m = (lab == big['label'])
    # fill holes: flood background from border on ~m
    inv = ~m
    lab2, comps2 = L.label_components(inv)
    bgl = None
    for c in comps2:
        if c['x0'] == 0 and c['y0'] == 0:
            bgl = c['label']; break
    if bgl is None:
        bgl = comps2[0]['label']
    filled = ~(lab2 == bgl)
    return filled, big


def edge_profiles(m):
    h, w = m.shape
    left = np.full(h, -1.0); right = np.full(h, -1.0)
    top = np.full(w, -1.0); bot = np.full(w, -1.0)
    for y in range(h):
        xs = np.nonzero(m[y])[0]
        if len(xs) > 8:
            left[y] = xs[0]; right[y] = xs[-1]
    for x in range(w):
        ys = np.nonzero(m[:, x])[0]
        if len(ys) > 8:
            top[x] = ys[0]; bot[x] = ys[-1]
    return left, right, top, bot


def report(name, path):
    print(f"\n########## {name} ##########")
    a = L.load_stored(path)
    h, w = a.shape[:2]
    m, big = tag_mask(a)
    ys, xs = np.nonzero(m)
    print(f"image {w}x{h}; mask n={m.sum()} bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}]")
    left, right, top, bot = edge_profiles(m)
    valid = left >= 0
    yv = np.nonzero(valid)[0]
    y0, y1 = yv[0], yv[-1]
    H0 = y1 - y0 + 1
    # sample the straight middle 60% of each side edge to fit lines
    lo = y0 + int(0.20 * H0); hi = y0 + int(0.80 * H0)
    yy = np.arange(lo, hi + 1, dtype=np.float64)
    aL, bL, rL, resL = L.fit_line(left[lo:hi + 1].astype(np.float64), yy)
    aR, bR, rR, resR = L.fit_line(right[lo:hi + 1].astype(np.float64), yy)
    print(f"LEFT  edge x = {aL:+.6f}*y + {bL:.3f}  rms={rL:.3f}px  (slope deg from vertical {np.degrees(np.arctan(aL)):+.4f})")
    print(f"RIGHT edge x = {aR:+.6f}*y + {bR:.3f}  rms={rR:.3f}px  (slope deg from vertical {np.degrees(np.arctan(aR)):+.4f})")
    print(f"  edge residual range L: {resL.min():+.2f}..{resL.max():+.2f}  R: {resR.min():+.2f}..{resR.max():+.2f}")
    xv = np.nonzero(top >= 0)[0]
    x0, x1 = xv[0], xv[-1]
    W0 = x1 - x0 + 1
    xlo = x0 + int(0.25 * W0); xhi = x0 + int(0.75 * W0)
    xx = np.arange(xlo, xhi + 1, dtype=np.float64)
    aT, bT, rT, resT = L.fit_line(top[xlo:xhi + 1].astype(np.float64), xx)
    aB, bB, rB, resB = L.fit_line(bot[xlo:xhi + 1].astype(np.float64), xx)
    print(f"TOP    edge y = {aT:+.6f}*x + {bT:.3f}  rms={rT:.3f}px  (deg from horizontal {np.degrees(np.arctan(aT)):+.4f})")
    print(f"BOTTOM edge y = {aB:+.6f}*x + {bB:.3f}  rms={rB:.3f}px  (deg from horizontal {np.degrees(np.arctan(aB)):+.4f})")
    print(f"  edge residual range T: {resT.min():+.2f}..{resT.max():+.2f}  B: {resB.min():+.2f}..{resB.max():+.2f}")

    # virtual corners = intersections of the 4 edge lines
    def isect(av, bv, ah, bh):
        # x = av*y+bv ; y = ah*x+bh
        y = (ah * bv + bh) / (1 - ah * av)
        x = av * y + bv
        return x, y
    TL = isect(aL, bL, aT, bT); TR = isect(aR, bR, aT, bT)
    BL = isect(aL, bL, aB, bB); BR = isect(aR, bR, aB, bB)
    print(f"virtual corners TL={TL[0]:.2f},{TL[1]:.2f}  TR={TR[0]:.2f},{TR[1]:.2f}  BL={BL[0]:.2f},{BL[1]:.2f}  BR={BR[0]:.2f},{BR[1]:.2f}")
    wt = np.hypot(TR[0]-TL[0], TR[1]-TL[1]); wb = np.hypot(BR[0]-BL[0], BR[1]-BL[1])
    hl = np.hypot(BL[0]-TL[0], BL[1]-TL[1]); hr = np.hypot(BR[0]-TR[0], BR[1]-TR[1])
    print(f"edge lengths top={wt:.2f} bottom={wb:.2f} (delta {wb-wt:+.2f}, {100*(wb-wt)/wt:+.2f}%)")
    print(f"edge lengths left={hl:.2f} right={hr:.2f} (delta {hr-hl:+.2f}, {100*(hr-hl)/hl:+.2f}%)")
    print(f"aspect W/H using mean = {((wt+wb)/2)/((hl+hr)/2):.5f}")

    # corner clip chords: walk the edge profiles to find where they depart the fit line
    print("corner clip analysis (departure of measured edge from fitted line, px):")
    for lbl, prof, fit, rng in (
            ("left/top", left, lambda y: aL*y+bL, range(y0, y0+int(0.25*H0))),
            ("left/bot", left, lambda y: aL*y+bL, range(y1, y1-int(0.25*H0), -1)),
            ("right/top", right, lambda y: aR*y+bR, range(y0, y0+int(0.25*H0))),
            ("right/bot", right, lambda y: aR*y+bR, range(y1, y1-int(0.25*H0), -1))):
        dep = None
        for y in rng:
            if prof[y] < 0:
                continue
            sgn = 1 if 'left' in lbl else -1
            if sgn*(prof[y] - fit(y)) < 1.0:
                dep = y; break
        print(f"  {lbl}: clip ends at y={dep} (inset {abs(dep-(y0 if 'top' in lbl else y1))} px along edge)")
    return dict(a=a, m=m, TL=TL, TR=TR, BL=BL, BR=BR,
                left=left, right=right, top=top, bot=bot,
                aL=aL,bL=bL,aR=aR,bR=bR,aT=aT,bT=bT,aB=aB,bB=bB)


res = {}
res['V1'] = report("V1", os.path.join(REF, "paperbomb_guide.png"))
res['V2'] = report("V2", os.path.join(REF, "paperbomb_guide_v2_real_glyphs.png"))

# quick look at our build's base colour - downsample for eyeballing (DEBUG only)
bc = L.load_stored(r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png")
print("\nBC shape", bc.shape)
small = bc[::4, ::4, :3]
L.save_debug_png(small, os.path.join(SCRATCH, "bc_view_DEBUG.png"))
print("wrote scratch view")
