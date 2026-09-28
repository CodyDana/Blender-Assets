# -*- coding: utf-8 -*-
"""Probe 3 - colour separation thresholds + locate our build's front UV island."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import lib_metro as L

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"
BCP = r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png"

def colour_report(name, rgb):
    r, g, b = rgb[...,0], rgb[...,1], rgb[...,2]
    lu = L.lum(rgb); rg = r - g; rb = r - b
    print(f"\n--- {name}: n={rgb.shape[0]*rgb.shape[1]} ---")
    for q in (0,1,5,10,20,30,40,50,60,70,80,90,95,99,100):
        print(f"  p{q:3d}  lum={np.percentile(lu,q):.3f}  R-G={np.percentile(rg,q):+.3f}  R-B={np.percentile(rb,q):+.3f}  R={np.percentile(r,q):.3f}")
    # candidate classes
    red = (rg > 0.14) & (r > 0.28)
    blk = (lu < 0.42) & (rg <= 0.14)
    pap = ~(red | blk)
    print(f"  RED  frac={red.mean()*100:.2f}%  mean rgb={np.round(rgb[red].mean(0),4).tolist() if red.any() else None}")
    print(f"  BLK  frac={blk.mean()*100:.2f}%  mean rgb={np.round(rgb[blk].mean(0),4).tolist() if blk.any() else None}")
    print(f"  PAP  frac={pap.mean()*100:.2f}%  mean rgb={np.round(rgb[pap].mean(0),4).tolist()}")
    # dark red vs black ambiguity
    dark = lu < 0.42
    print(f"  dark(lum<.42) frac={dark.mean()*100:.2f}%, of which R-G>0.14: {(dark & (rg>0.14)).sum()/max(dark.sum(),1)*100:.1f}%")

a1 = L.load_stored(os.path.join(REF, "paperbomb_guide.png"))
colour_report("V1 tag interior", a1[70:1440, 210:815, :3])
a2 = L.load_stored(os.path.join(REF, "paperbomb_guide_v2_real_glyphs.png"))
colour_report("V2 tag interior", a2[14:648, 16:288, :3])

bc = L.load_stored(BCP)
rgb = bc[..., :3]
lu = L.lum(rgb)
print("\n=== BC 2048 island scan ===")
print("col means of lum, every 64px:", np.round(lu[:, ::64].mean(axis=0), 3).tolist())
print("row means of lum, every 64px:", np.round(lu[::64, :].mean(axis=1), 3).tolist())
# background brown?
print("bc[0,0]", np.round(rgb[0,0],4).tolist(), " bc[1024,1024]", np.round(rgb[1024,1024],4).tolist())
for thr in (0.66, 0.68, 0.70, 0.72):
    m = lu > thr
    m = L.open_(m, 2)
    lab, comps = L.label_components(m)
    print(f" thr {thr}: top comps " + "; ".join(
        f"n={c['n']} x[{c['x0']},{c['x1']}] y[{c['y0']},{c['y1']}]" for c in comps[:4]))
colour_report("BC left-half interior", rgb[100:1950, 60:900])
