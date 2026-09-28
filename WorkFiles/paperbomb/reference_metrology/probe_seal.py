import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pbmetro as P, pbtag as T, pbelem as E
SNAP=(r"C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/"
      r"70fec35b-8f87-4dbe-ba33-6e5ba8c5d846/scratchpad/snap/T_PaperBomb_BC.snap.png")
V1=r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/paperbomb_guide.png"
for path,kind,lab in ((V1,'guide','V1'),(SNAP,'atlas','OURS')):
    tg=T.Tag(path,kind,'left',lab)
    H,W=tg.red.shape
    ys,xs=np.mgrid[0:H,0:W]; xmm=xs/W*70.0; ymm=ys/H*156.0
    for nm,bx in (('BIG',(3.2,108.0,32.0,153.0)),('SMALL',(45.0,112.0,67.0,153.0))):
        win=(xmm>=bx[0])&(xmm<=bx[2])&(ymm>=bx[1])&(ymm<=bx[3])
        cs=E.comps(tg.red&win, max(20,int(0.00002*W*H)), 2)
        print(f"-- {lab} {nm}: {len(cs)} red comps")
        for c in cs[:8]:
            b=tg.box(c['x0'],c['y0'],c['x1'],c['y1'])
            fill=c['area']/max((c['x1']-c['x0'])*(c['y1']-c['y0']),1)
            print(f"   a={c['area']:6d} fill={fill:.3f} x[{b['x0_mm']:.2f}-{b['x1_mm']:.2f}] y[{b['y0_mm']:.2f}-{b['y1_mm']:.2f}] {b['w_mm']:.2f}x{b['h_mm']:.2f}")
