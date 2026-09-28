import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r2")
from m2_io import *
import json
W = ROOT + "WorkFiles/flashbang/measure_r2/"
R = load(REFP)[..., :3]; np.save(W + "m2_ref_rgb.npy", R.astype(np.float32))
ref = np.zeros((1254, 1254), bool); ref[:745] = np.load(W + "m2_refmask.npy")
def paint(im): 
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    return (np.abs(r - g) <= 10) & ((g - b) >= 8) & (g >= 25)
def holes(im, sil, top, bot):
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    m = sil & ~paint(im) & ((r - b) > 8)
    m[:top] = False; m[bot:] = False
    return m
Rh = holes(R, ref, 270, 615)
Rh2 = Rh.reshape(627, 2, 627, 2).mean((1, 3)) > 0.5
r2 = ref.reshape(627, 2, 627, 2).mean((1, 3)) > 0.5
z = np.load(W + "m2_sweep_tex.npz")
VB = {"v1": (40, 345), "v2": (345, 615), "v3": (615, 950), "v4": (950, 1240)}
res = {}
for v, (x0, x1) in VB.items():
    a, b = x0 // 2, x1 // 2; sc = []
    for k in z.files:
        im = z[k].astype(np.float32); sil = im[..., 3] > 128
        Oh = holes(im[..., :3], sil, 135, 307)
        hi = (Rh2[:, a:b] & Oh[:, a:b]).sum() / max((Rh2[:, a:b] | Oh[:, a:b]).sum(), 1)
        si = (r2[:, a:b] & sil[:, a:b]).sum() / (r2[:, a:b] | sil[:, a:b]).sum()
        sc.append((round(float(hi + si), 3), round(float(hi), 3), round(float(si), 3), int(k)))
    sc.sort(reverse=True); res[v] = sc[:6]; print(v, sc[:6])
save(W + "m2_refholes.png", np.stack([Rh * 255.0] * 3, -1))
