# final pass: the big seal's sparkles and the top-left knob, reference vs BC vs front render at the reference grid
import sys
from pathlib import Path
PROJECT = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(PROJECT / "Scripts")); sys.path.insert(0, str(PROJECT / "Scripts" / "props"))
import bpy, numpy as np
exec(open(str(PROJECT / "WorkFiles/paperbomb/exact/fx_measure.py"), encoding="utf-8").read().split("ref = load(REF)")[0].replace("argv = sys.argv[sys.argv.index(\"--\") + 1:]", "argv=['x']"))
from props_lib import paperbomb_tracedart as TA
argv = sys.argv[sys.argv.index("--") + 1:]
BCP = argv[0] if argv else ROOT + "Exports/PaperBomb/Textures/T_PaperBomb_BC.png"
FRP = argv[1] if len(argv) > 1 else ROOT + "Renders/PaperBomb/paperbomb_front.png"
model = TA.reference_model(); fit = model.L.fit
ref = load(REF); H, W = ref.shape[:2]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
bc = load(BCP)
bcb = sum(np.roll(bc, i, 1) for i in range(-2, 2))/4; bcb = sum(np.roll(bcb, i, 0) for i in range(-2, 2))/4
bcr = bil(bcb, BA[0]*(xx+0.5)+BA[2]-0.5, BA[1]*(yy+0.5)+BA[3]-0.5)
fr = load(FRP)
raw = bil(fr, AFF[0]*(xx+0.5)+AFF[2]-0.5, AFF[1]*(yy+0.5)+AFF[3]-0.5)
roi = (xx > 30) & (xx < 270) & (yy > 30) & (yy < 628)
def psel(a):
    L = lum(a); return roi & (L > np.percentile(L[roi], 40)) & (warmth(a) > 0.05)
g = np.median(ref[psel(ref)], 0)/np.median(raw[psel(raw)], 0); frn = np.clip(raw*g, 0, 1)
for name, c, r in (("spark_TL", (9.6, 126.9), 2.0), ("spark_BR", (20.8, 146.3), 1.8)):
    px, py = fit.mm_to_px(np.array(c[0]), np.array(c[1])); px = float(px); py = float(py)
    rr = r * fit.ppmm
    m = (np.hypot(xx + 0.5 - px, yy + 0.5 - py) < rr)
    print(name, "centre px", round(px, 1), round(py, 1))
    for tag, a in (("ref", ref), ("bc_boxed", bcr), ("front", frn)):
        L = lum(a)[m]; G_ = a[..., 1][m]
        print("  %-9s Lmax %.3f  G p99 %.3f  n(G>0.45) %3d  n(G>0.6) %3d  n(G>0.75) %3d  meanG %.4f" % (
            tag, L.max(), np.percentile(G_, 99), (G_ > 0.45).sum(), (G_ > 0.6).sum(), (G_ > 0.75).sum(), G_.mean()))
    y0, x0 = int(py - rr), int(px - rr)
    for tag, a in (("ref", ref), ("bc_boxed", bcr)):
        print("  ", tag, "G x100 window")
        for row in (a[..., 1][y0:y0 + int(2 * rr) + 1, x0:x0 + int(2 * rr) + 1] * 100).astype(int):
            print("    " + " ".join("%3d" % v for v in row))
