import bpy, numpy as np, math, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outline import full_polygon

D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/"
SRC = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Manjiken.JPG"
B = np.load(D + "contour/mask_final.npy").astype(bool)
A = np.unpackbits(np.load(D + "radial/mask.npy"))[: B.size].reshape(B.shape).astype(bool)
H, W = B.shape
CEN = np.array([1305.2, 1317.9]); SPAN = 2842.8; ROT = -0.47

def place(poly, cen=CEN, span=SPAN, rot=ROT):
    p = poly / (2.0 * np.hypot(poly[:, 0], poly[:, 1]).max())
    a = math.radians(rot); R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    p = p @ R.T * span
    return np.stack([cen[0] + p[:, 0], cen[1] - p[:, 1]], 1)

def rasterise(pts):
    """even-odd scanline fill"""
    m = np.zeros((H, W), bool)
    P = np.vstack([pts, pts[:1]])
    y0 = max(int(P[:, 1].min()), 0); y1 = min(int(P[:, 1].max()) + 1, H)
    x0s, y0s = P[:-1, 0], P[:-1, 1]; x1s, y1s = P[1:, 0], P[1:, 1]
    for y in range(y0, y1):
        yc = y + 0.5
        hit = ((y0s <= yc) & (y1s > yc)) | ((y1s <= yc) & (y0s > yc))
        if not hit.any(): continue
        t = (yc - y0s[hit]) / (y1s[hit] - y0s[hit])
        xs = np.sort(x0s[hit] + t * (x1s[hit] - x0s[hit]))
        for i in range(0, len(xs) - 1, 2):
            a2, b2 = int(math.ceil(xs[i] - 0.5)), int(math.floor(xs[i + 1] - 0.5))
            if b2 >= a2: m[y, max(a2, 0):min(b2 + 1, W)] = True
    return m

rec = place(full_polygon("reconciled"))
spec = place(full_polygon("spec"))
Mrec = rasterise(rec); Mspec = rasterise(spec)
res = {}
for nm, M in (("A", A), ("B", B)):
    for pn, PM in (("reconciled", Mrec), ("spec", Mspec)):
        i = (M & PM).sum(); u = (M | PM).sum()
        res["%s_vs_%s" % (pn, nm)] = dict(IoU=float(i / u), area_poly=int(PM.sum()), area_mask=int(M.sum()),
                                          only_mask=int((M & ~PM).sum()), only_poly=int((PM & ~M).sum()))
        print("%-11s vs mask %s : IoU %.4f  poly %d  mask %d  mask-only %d  poly-only %d"
              % (pn, nm, i / u, PM.sum(), M.sum(), (M & ~PM).sum(), (PM & ~M).sum()))

# signed perpendicular distance from polygon vertices to the mask boundary, along the polygon normal
def boundary_offsets(pts, M, step=0.25, rng=60):
    segs = np.roll(pts, -1, 0) - pts
    nrm = np.stack([segs[:, 1], -segs[:, 0]], 1)
    nrm /= (np.hypot(nrm[:, 0], nrm[:, 1])[:, None] + 1e-9)
    # ensure the normal points outward (away from CEN)
    out = pts - CEN
    flip = np.sign((nrm * out).sum(1))[:, None]; nrm = nrm * np.where(flip == 0, 1, flip)
    t = np.arange(-rng, rng, step)
    xs = pts[:, 0][:, None] + nrm[:, 0][:, None] * t[None, :]
    ys = pts[:, 1][:, None] + nrm[:, 1][:, None] * t[None, :]
    ins = M[np.clip(np.round(ys).astype(int), 0, H - 1), np.clip(np.round(xs).astype(int), 0, W - 1)]
    ok = ins.any(1) & (~ins).any(1)
    idx = ins.shape[1] - 1 - np.argmax(ins[:, ::-1], 1)
    d = np.where(ok, t[idx], np.nan)
    return d

for nm, M in (("A", A), ("B", B)):
    d = boundary_offsets(rec, M)
    dd = d[~np.isnan(d)]
    print("reconciled boundary vs mask %s: n=%d  mean %+.2f px  median %+.2f  rms %.2f  |d|<5px %.1f%%  p05 %+.1f p95 %+.1f"
          % (nm, len(dd), dd.mean(), np.median(dd), np.sqrt((dd ** 2).mean()),
             100 * (np.abs(dd) < 5).mean(), np.percentile(dd, 5), np.percentile(dd, 95)))
    res["boundary_vs_%s" % nm] = dict(mean=float(dd.mean()), median=float(np.median(dd)),
                                      rms=float(np.sqrt((dd ** 2).mean())),
                                      frac_within_5px=float((np.abs(dd) < 5).mean()))
json.dump(res, open(D + "reconcile/validate.json", "w"), indent=1)

