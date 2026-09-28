import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pbmetro as P, pbtag as T, pbelem as E
S1=(r"C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/"
    r"70fec35b-8f87-4dbe-ba33-6e5ba8c5d846/scratchpad/snap/T_PaperBomb_BC.snap.png")
S2=S1.replace("snap.png","snap2.png")
for lab,p in (("22:12 snapshot",S1),("22:31 export",S2)):
    tg=T.Tag(p,'atlas','left',lab)
    H,W=tg.black.shape
    ys,xs=np.mgrid[0:H,0:W]; xmm=xs/W*70.0; ymm=ys/H*156.0
    ring=E.fit_ring(tg,tg.red,(5.4,38.0,64.6,114.0))
    rh=ring['radial_hist']
    el=ring['ellipse']
    # centre glyph = black inside ring ellipse
    import math
    thr=math.radians(el['major_axis_deg']); sa,sb=el['semi_major_px'],el['semi_minor_px']
    cs=E.comps(tg.black, max(30,int(0.000012*W*H)),1)
    sel=[]
    for c in cs:
        dx,dy=c['cx']-ring['cx'],c['cy']-ring['cy']
        u=dx*math.cos(thr)+dy*math.sin(thr); v=-dx*math.sin(thr)+dy*math.cos(thr)
        if (u/sa)**2+(v/sb)**2<=1.0: sel.append(c)
    m=E.union([c['mask'] for c in sel],(H,W))
    x0,y0,x1,y1=E.bbox_of(m); b=tg.box(x0,y0,x1,y1)
    print(f"{lab}: card {tg.W}x{tg.H}px | ring c=({tg.mmx(ring['cx']):.2f},{tg.mmy(ring['cy']):.2f}) "
          f"modes={rh['n_radial_modes']} fwhm={rh['fwhm_rho']} | bao {b['w_mm']:.2f}x{b['h_mm']:.2f} "
          f"w/h={b['w_over_h']:.3f} ncomp={len(sel)} inkfloor={tg.seg['ink_floor_luma_p005_stored']:.3f} "
          f"blackcov={tg.seg['black_coverage']:.4f} redcov={tg.seg['red_coverage']:.4f}")
