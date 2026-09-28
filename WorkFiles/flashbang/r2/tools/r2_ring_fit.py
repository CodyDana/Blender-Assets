import sys, json, math, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts")
from r2proj import *
from props_lib import flashbang_geom as G
from props_lib.flashbang_spec import FLASHBANG as S
P = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/"
spec = json.load(open(P + "flashbang_spec.json"))
VIEW_BOTTOM = {"v1": 720.5, "v2": 716.8, "v3": 717.0, "v4": 717.0}
D_PX = 175.31; MMPX = D_PX / 44.0
H = W = 1254
yy, xx = np.mgrid[0:H, 0:W]
def poly_mask(poly):
    poly = np.asarray(poly, float); m = np.zeros((H, W), bool)
    x0, y0 = poly.min(0).astype(int); x1, y1 = poly.max(0).astype(int) + 1
    sy, sx = yy[y0:y1, x0:x1] + 0.5, xx[y0:y1, x0:x1] + 0.5
    ins = np.zeros(sx.shape, bool)
    for i in range(len(poly)):
        xa, ya = poly[i]; xb, yb = poly[(i + 1) % len(poly)]
        ins ^= ((ya > sy) != (yb > sy)) & (sx < (xb - xa) * (sy - ya) / (yb - ya + 1e-12) + xa)
    m[y0:y1, x0:x1] = ins
    return m
REFM = {v: poly_mask(spec["outlines"]["silhouettes_ref_px"][v]["polygon_ref_px"]) for v in VIEW_X_PX}
mb, info = G.build_lod(S, 0)
V = np.array(mb.verts)
rng = np.random.default_rng(1)
pts = []
for f in mb.faces:
    if f.part in ("ring",):
        continue
    Q = V[list(f.v)]
    for t in range(len(Q) - 2):
        a, b, c = Q[0], Q[t + 1], Q[t + 2]
        area = 0.5 * np.linalg.norm(np.cross(b - a, c - a))
        n = max(1, int(area / 0.15))
        r1, r2 = rng.random(n), rng.random(n)
        m = r1 + r2 > 1; r1[m], r2[m] = 1 - r1[m], 1 - r2[m]
        pts.append(a + r1[:, None] * (b - a) + r2[:, None] * (c - a))
BODY = np.concatenate(pts)
def ring_pts(top, alpha, tau, R=S.ring_major_r, r=S.ring_wire_d / 2):
    u = np.array([math.cos(math.radians(alpha)), math.sin(math.radians(alpha)), 0.0])
    zz = np.array([0.0, 0.0, 1.0]); ux = np.cross(u, zz)
    w = -math.cos(math.radians(tau)) * zz + math.sin(math.radians(tau)) * ux
    c = np.asarray(top) + R * w
    a = np.linspace(0, 2 * math.pi, 720)[:, None]
    nrm = np.cross(u, w)
    b = np.linspace(0, 2 * math.pi, 12)[None, :]
    d = np.cos(a) * u + np.sin(a) * (-w)                      # (720,3)
    P = c + (R + r * np.cos(b))[..., None] * d[:, None, :] + (r * np.sin(b))[..., None] * nrm
    return P.reshape(-1, 3)
def mask(pts, v, yaw=None):
    xy, _ = project(pts, v, yaw)
    m = np.zeros((H, W), bool)
    xi = np.clip(np.rint(xy[:, 0] - 0.5).astype(int), 0, W - 1); yi = np.clip(np.rint(xy[:, 1] - 0.5).astype(int), 0, H - 1)
    m[yi, xi] = True
    m = m | np.roll(m, 1, 0) | np.roll(m, 1, 1)
    return m
def extents(m, v, Hs):
    out = []
    for Hd in Hs:
        y = int(round(VIEW_BOTTOM[v] - Hd * D_PX))
        x0, x1 = int(VIEW_X_PX[v] - 60 * MMPX), int(VIEW_X_PX[v] + 60 * MMPX)
        row = np.nonzero(m[y, max(0, x0):x1])[0]
        out.append((None, None) if not len(row) else ((max(0, x0) + row.min() - VIEW_X_PX[v]) / MMPX, (max(0, x0) + row.max() + 1 - VIEW_X_PX[v]) / MMPX))
    return out
SIDE = {"v1": 1, "v2": 1, "v3": 1, "v4": 0}          # which extent the ring dominates (0 left, 1 right)
Hs = np.arange(2.70, 3.76, 0.05)
bodym = {v: mask(BODY, v) for v in VIEW_X_PX}
refx = {v: extents(REFM[v], v, Hs) for v in VIEW_X_PX}
def score(top, alpha, tau, verbose=False, yaws=None):
    rp = ring_pts(top, alpha, tau)
    tot = 0.0; per = {}
    for v in VIEW_X_PX:
        yaw = None if yaws is None else yaws[v]
        m = (mask(BODY, v, yaw) if yaw is not None else bodym[v]) | mask(rp, v, yaw)
        ex = extents(m, v, Hs)
        e = []
        for (a, b) in zip(ex, refx[v]):
            if a[0] is None or b[0] is None:
                continue
            e.append(abs(a[SIDE[v]] - b[SIDE[v]]))
        per[v] = round(float(np.mean(e)), 2)
        tot += per[v]
    return tot, per
if __name__ == "__main__":
    px, pz = S.pin_c
    top = (px, S.pin_eye_y(), pz)
    print("current", score(top, 0.0, 30.0))
    best = []
    for alpha in range(-60, 61, 10):
        for tau in range(0, 71, 10):
            s, per = score(top, alpha, tau)
            best.append((s, alpha, tau, per))
    best.sort(key=lambda t: t[0])
    for b in best[:8]:
        print(b)
