# -*- coding: utf-8 -*-
"""Probe 4 - rectify, classify, dump clusters so elements can be named."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import lib_metro as L
import lib_tag as T

REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb"
BCP = r"C:/Users/Cody/Desktop/Blender_Projects/Exports/PaperBomb/Textures/T_PaperBomb_BC.png"
DBG = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/reference_metrology/debug"

# --- first: our atlas island edge profile ------------------------------------
bc = L.load_stored(BCP)
lu = L.lum(bc[..., :3])
print("=== OURS: island edge transition profiles (lum, stored) ===")
print(" row y=1000, x=0..40 :", np.round(lu[1000, 0:40], 3).tolist())
print(" row y=1000, x=890..960:", np.round(lu[1000, 890:960], 3).tolist())
print(" col x=460, y=0..40  :", np.round(lu[0:40, 460], 3).tolist())
print(" col x=460, y=2010..2048:", np.round(lu[2010:2048, 460], 3).tolist())
del lu

def run(name, arr, mask):
    q = T.fit_quad(mask)
    print(f"\n########## {name} ##########")
    print(" corners TL=%.2f,%.2f TR=%.2f,%.2f BL=%.2f,%.2f BR=%.2f,%.2f" %
          (q['TL'][0], q['TL'][1], q['TR'][0], q['TR'][1], q['BL'][0], q['BL'][1], q['BR'][0], q['BR'][1]))
    wt = q['TR'][0] - q['TL'][0]; hl = q['BL'][1] - q['TL'][1]
    print(f" W={wt:.2f} H={hl:.2f} aspect={wt/hl:.5f}  rms edges L{q['rmsL']:.3f} R{q['rmsR']:.3f} T{q['rmsT']:.3f} B{q['rmsB']:.3f}")
    rect, Hm = T.rectify(arr, q)
    c = T.classify(rect)
    print(f" thresholds: paper_lum={c['paper_lum']:.3f} ink_lum={c['ink_lum']:.3f} thr_ink={c['thr_ink']:.3f}"
          f" | paper_rex={c['paper_rex']:.3f} red_rex={c['red_rex']:.3f} thr_red={c['thr_red']:.3f}")
    print(f" coverage: red={c['red'].mean()*100:.2f}%  black={c['black'].mean()*100:.2f}%")
    rad = max(1, int(round(1.1 * T.PPMM)))
    for lbl, m in (("BLACK", c['black']), ("RED", c['red'])):
        cl = T.clusters(m, rad, int(0.8 * T.PPMM * T.PPMM))
        print(f" --- {lbl} clusters (dilate r={rad}px): {len(cl)} ---")
        for d in cl[:28]:
            print("   n=%7d  x[%4d,%4d] y[%4d,%4d]  w=%4d h=%4d  c=(%6.1f,%7.1f)  fx[%.3f,%.3f] fy[%.3f,%.3f]"
                  % (d['n'], d['x0'], d['x1'], d['y0'], d['y1'], d['x1']-d['x0']+1, d['y1']-d['y0']+1,
                     d['cx'], d['cy'], d['x0']/T.CW, d['x1']/T.CW, d['y0']/T.CH, d['y1']/T.CH))
    # debug overlay
    ov = rect.copy()
    ov[c['red']] = ov[c['red']] * 0.3 + np.array([0.0, 1.0, 0.0]) * 0.7
    ov[c['black']] = ov[c['black']] * 0.3 + np.array([0.0, 0.4, 1.0]) * 0.7
    L.save_debug_png(ov[::3, ::3], os.path.join(DBG, f"DEBUG_NEVER_SHIP_classes_{name}.png"))
    return rect, c, q

a1 = L.load_stored(os.path.join(REF, "paperbomb_guide.png"))
run("V1", a1, T.tag_mask_ref(a1)); del a1
a2 = L.load_stored(os.path.join(REF, "paperbomb_guide_v2_real_glyphs.png"))
run("V2", a2, T.tag_mask_ref(a2)); del a2
run("OURS", bc, T.tag_mask_ours(bc, 940))
