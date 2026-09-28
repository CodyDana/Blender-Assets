import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/m1")
from m1_lib import *
r = load(REF); H, W = r.shape[:2]
Lr = lab(r)
def feat(L):  # darkness + redness feature
    return np.stack([L[..., 0]/100.0, np.clip(L[..., 1], -10, 80)/80.0], -1)
Fr = feat(Lr)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
roi = (xx > 30) & (xx < 270) & (yy > 30) & (yy < 628)
def inkbbox(L, sel):
    ink = ((L[..., 0] < 55) | (L[..., 1] > 30)) & sel
    ys, xs = np.nonzero(ink); return xs.min(), xs.max(), ys.min(), ys.max()
rb = inkbbox(Lr, roi); print("ref ink bbox", rb)

def fit(src, name, sel_src, pre_blur, extra=None):
    Ls = lab(src)
    sb = inkbbox(Ls, sel_src); print(name, "ink bbox", sb)
    sx = (sb[1]-sb[0])/(rb[1]-rb[0]); sy = (sb[3]-sb[2])/(rb[3]-rb[2])
    p = np.array([sx, sy, sb[0]-sx*rb[0], sb[2]-sy*rb[2]], np.float64)
    Fs = feat(lab(box_blur(src, pre_blur(p)))) if True else None
    def warp(p, F=Fs):
        return bilinear(F, p[0]*(xx+0.5)+p[2]-0.5, p[1]*(yy+0.5)+p[3]-0.5)
    def cost(p, sig=0.5):
        w = gauss_blur(warp(p), sig)
        return float(((w-Fr)[roi]**2).mean())
    steps = np.array([0.01, 0.01, 2.0, 2.0])
    c = cost(p)
    for it in range(60):
        improved = False
        for i in range(4):
            for s in (+1, -1):
                q = p.copy(); q[i] += s*steps[i]; cq = cost(q)
                if cq < c: p, c, improved = q, cq, True
        if not improved:
            steps *= 0.5
            if steps[2] < 0.02: break
    best = None
    for sig in np.arange(0, 1.21, 0.1):
        cs = cost(p, sig)
        if best is None or cs < best[1]: best = (sig, cs)
    print(name, "fit", p.tolist(), "cost", c, "best psf sigma", best)
    return p, best[0]

bc = load(BC)
sel_bc = np.zeros(bc.shape[:2], bool); sel_bc[40:2010, 30:880] = True
p_bc, sig_bc = fit(bc, "BC", sel_bc, lambda p: (p[0]+p[1])/2)
fr = load(FRONT)
# exposure-normalise the render on bare paper (linear per-channel gain) to the reference paper
def paper_med(img, sel):
    L = lab(img); m = sel & (L[..., 0] > 60) & (np.abs(L[..., 1]) < 15)
    return np.median(srgb2lin(img[m]), 0)
ref_sel = roi & (Lr[..., 0] > 80)
fsel = np.zeros(fr.shape[:2], bool); fsel[100:800, 670:930] = True
g = paper_med(r, ref_sel)/paper_med(fr, fsel)
print("render exposure gain", g)
lin = srgb2lin(fr)*g
fr = np.clip(np.where(lin <= 0.0031308, lin*12.92, 1.055*np.clip(lin, 1e-9, None)**(1/2.4)-0.055), 0, 1).astype(np.float32)
np.save(OUT+"m1_front_expnorm.npy", fr); json.dump(g.tolist(), open(OUT+"m1_front_gain.json", "w"))
sel_fr = np.zeros(fr.shape[:2], bool); sel_fr[85:815, 660:940] = True
p_fr, sig_fr = fit(fr, "FRONT", sel_fr, lambda p: (p[0]+p[1])/2)
json.dump({"bc": p_bc.tolist(), "bc_sigma": float(sig_bc), "front": p_fr.tolist(), "front_sigma": float(sig_fr)}, open(OUT+"m1_align.json", "w"), indent=1)
