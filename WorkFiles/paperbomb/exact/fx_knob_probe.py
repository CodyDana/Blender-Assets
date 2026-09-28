# final pass: the top-left knob's black layer, reference vs photographed BC (m3 method)
import sys; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/m3")
from m3_lib import *
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
bcnpy = argv[0] if argv else OUT + "m3_photo_bc.npy"
r = np.load(OUT + "m3_photo_ref.npy"); b = np.load(bcnpy)
H, W = r.shape[:2]; yy, xx = np.mgrid[0:H, 0:W]
card = (xx > 16) & (xx < 286) & (yy > 14) & (yy < 646)
def em(L):
    return (np.median(L[card & (L[..., 0] > 80) & (np.abs(L[..., 1]) < 15)], 0),
            np.median(L[card & (L[..., 0] < 25)], 0), np.median(L[card & (L[..., 1] > 45)], 0))
def soft(L, e):
    p, k, rd = e
    kb = np.clip((p[0]-L[..., 0])/(p[0]-k[0]), 0, 1)
    return np.where(L[..., 1] > (p[1]+rd[1])/2, 0.0, kb)
Lr, Lb = lab(r), lab(b)
kr, kb = soft(Lr, em(Lr)), soft(Lb, em(Lb))
y0, y1, x0, x1 = 26, 58, 22, 53
mr, mb = kr[y0:y1, x0:x1] >= 0.5, kb[y0:y1, x0:x1] >= 0.5
print("black IoU %.3f  n_ref %d n_ours %d" % ((mr & mb).sum() / max(1, (mr | mb).sum()), mr.sum(), mb.sum()))
for nm, a, L in (("ref", kr, Lr), ("ours", kb, Lb)):
    print(nm, "black soft x10 (rows y%d.., cols x%d..)" % (y0, x0))
    for yy_ in range(y0, y1):
        print("  %3d " % yy_ + "".join(("%d" % min(9, int(a[yy_, xx_] * 10))) if a[yy_, xx_] > 0.05 else "." for xx_ in range(x0, x1)))
