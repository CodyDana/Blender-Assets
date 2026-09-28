import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/m2")
from m2_lib import *
r = load(REF); H, W = r.shape[:2]
Lr = lab(r)
def feat(L):
    return np.stack([L[..., 0]/100.0, np.clip(L[..., 1], -10, 80)/80.0], -1)
Fr = feat(Lr)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
roi = (xx > 30) & (xx < 270) & (yy > 30) & (yy < 628)
def inkbbox(L, sel):
    ink = ((L[..., 0] < 55) | (L[..., 1] > 30)) & sel
    ys, xs = np.nonzero(ink); return xs.min(), xs.max(), ys.min(), ys.max()
rb = inkbbox(Lr, roi); print("ref ink bbox", rb)

def fit(src, name, sel_src, pre_blur):
    Ls = lab(src)
    sb = inkbbox(Ls, sel_src); print(name, "ink bbox", sb)
    sx = (sb[1]-sb[0])/(rb[1]-rb[0]); sy = (sb[3]-sb[2])/(rb[3]-rb[2])
    p = np.array([sx, sy, sb[0]-sx*rb[0], sb[2]-sy*rb[2]], np.float64)
    Fs = feat(lab(box_blur(src, pre_blur(p))))
    def warp(p):
        return bilinear(Fs, p[0]*(xx+0.5)+p[2]-0.5, p[1]*(yy+0.5)+p[3]-0.5)
    def cost(p, sig=0.5):
        w = gauss_blur(warp(p), sig)
        return float(((w-Fr)[roi]**2).mean())
    steps = np.array([0.01, 0.01, 2.0, 2.0])
    c = cost(p)
    for it in range(80):
        improved = False
        for i in range(4):
            for s in (+1, -1):
                q = p.copy(); q[i] += s*steps[i]; cq = cost(q)
                if cq < c: p, c, improved = q, cq, True
        if not improved:
            steps *= 0.5
            if steps[2] < 0.01: break
    best = None
    for sig in np.arange(0, 1.21, 0.1):
        cs = cost(p, sig)
        if best is None or cs < best[1]: best = (sig, cs)
    print(name, "fit", p.tolist(), "cost", c, "best psf sigma", best)
    return p, best[0]

def paper_med(img, sel):
    L = lab(img); m = sel & (L[..., 0] > 60) & (np.abs(L[..., 1]) < 15)
    return np.median(srgb2lin(img[m]), 0)
def gain_apply(img, g):
    lin = srgb2lin(img)*g
    return np.clip(np.where(lin <= 0.0031308, lin*12.92, 1.055*np.clip(lin, 1e-9, None)**(1/2.4)-0.055), 0, 1).astype(np.float32)
ref_sel = roi & (Lr[..., 0] > 80)
out = {}
bc = load(BC)
sel_bc = np.zeros(bc.shape[:2], bool); sel_bc[40:2010, 30:880] = True
p, s = fit(bc, "BC", sel_bc, lambda p: (p[0]+p[1])/2); out["bc"] = p.tolist(); out["bc_sigma"] = float(s)
# scan: RAW, no gain (the builder claims the scan is tone-matched without gain)
sc = load(SCAN)
fsel = np.zeros(sc.shape[:2], bool); fsel[110:790, 670:930] = True
g_scan = paper_med(r, ref_sel)/paper_med(sc, fsel); print("scan gain that would be needed", g_scan)
sel = np.zeros(sc.shape[:2], bool); sel[80:820, 650:950] = True
p, s = fit(sc, "SCAN", sel, lambda p: 1); out["scan"] = p.tolist(); out["scan_sigma"] = float(s); out["scan_gain_needed"] = g_scan.tolist()
np.save(OUT+"m2_scan_raw.npy", sc)
# pack front: exposure-normalised on paper (as in round 1)
fr = load(FRONT)
fsel = np.zeros(fr.shape[:2], bool); fsel[100:800, 670:930] = True
g = paper_med(r, ref_sel)/paper_med(fr, fsel); print("pack front gain", g)
frn = gain_apply(fr, g); np.save(OUT+"m2_front_expnorm.npy", frn)
sel = np.zeros(fr.shape[:2], bool); sel[85:815, 660:940] = True
p, s = fit(frn, "FRONT", sel, lambda p: 1); out["front"] = p.tolist(); out["front_sigma"] = float(s); out["front_gain"] = g.tolist()
json.dump(out, open(OUT+"m2_align.json", "w"), indent=1)
