# -*- coding: utf-8 -*-
"""Font-ID core: V2 ink unmixing, glyph outlines from Blender text objects,
nonzero-winding supersampled rasteriser, 5-DOF fitter, IoU / edge metrics."""
import os, sys, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fid_common as C


# ------------------------------------------------------------------ V2 inks
def unmix(a):
    """Per-pixel least-squares unmixing of V2 into paper + black k + red r."""
    lu = C.luma(a)
    H, W = lu.shape
    inner = np.zeros((H, W), bool)
    inner[int(C.YT) + 12:int(C.YB) - 12, int(C.XL) + 12:int(C.XR) - 12] = True
    rex = a[..., 0] - .5 * (a[..., 1] + a[..., 2])
    P = np.median(a[inner & (lu > np.percentile(lu[inner], 60)) & (rex < .25)], 0)
    K = np.median(a[inner & (lu < np.percentile(lu[inner], 1.5))], 0)
    Rd = np.median(a[inner & (rex > np.percentile(rex[inner], 99.3))], 0)
    A = np.stack([K - P, Rd - P], 1)          # 3x2
    pinv = np.linalg.pinv(A)                   # 2x3
    x = (a - P) @ pinv.T                       # H,W,2
    k = np.clip(x[..., 0], 0, 1)
    r = np.clip(x[..., 1], 0, 1)
    return k, r, dict(paper=P.tolist(), black=K.tolist(), red=Rd.tolist())


# ------------------------------------------------------------ morphology/label
def _sh(m, dy, dx):
    o = np.zeros_like(m)
    h, w = m.shape
    o[max(0, dy):min(h, h + dy), max(0, dx):min(w, w + dx)] = \
        m[max(0, -dy):min(h, h - dy), max(0, -dx):min(w, w - dx)]
    return o


def dilate(m, r=1):
    for _ in range(r):
        acc = m.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                acc |= _sh(m, dy, dx)
        m = acc
    return m


def erode(m, r=1):
    return ~dilate(~m, r)


def label(mask):
    sys.path.insert(0, C.MET)
    import rg_lib as R
    return R.label(mask)


# ------------------------------------------------------------ glyph outlines
_FONTS = {}


def load_font(path):
    import bpy
    if path not in _FONTS:
        _FONTS[path] = bpy.data.fonts.load(path, check_existing=True)
    return _FONTS[path]


def glyph_polys(path, ch, nseg=12):
    """Closed polylines (list of Nx2 arrays, Blender text units at size 1, y DOWN)."""
    import bpy
    f = load_font(path)
    cu = bpy.data.curves.new("fidg", 'FONT')
    cu.body = ch
    cu.font = f
    cu.size = 1.0
    cu.resolution_u = 12
    ob = bpy.data.objects.new("fidg", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    crv = ev.to_curve(dg)
    polys = []
    t = np.linspace(0, 1, nseg, endpoint=False)[:, None]
    for sp in crv.splines:
        if sp.type == 'BEZIER':
            bp = sp.bezier_points
            n = len(bp)
            if n < 2:
                continue
            co = np.array([p.co[:2] for p in bp])
            hl = np.array([p.handle_left[:2] for p in bp])
            hr = np.array([p.handle_right[:2] for p in bp])
            segs = []
            for i in range(n if sp.use_cyclic_u else n - 1):
                j = (i + 1) % n
                p0, p1, p2, p3 = co[i], hr[i], hl[j], co[j]
                pts = ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3
                segs.append(pts)
            P = np.concatenate(segs, 0)
        else:
            P = np.array([p.co[:2] for p in sp.points])
        if len(P) >= 3:
            P = P.copy()
            P[:, 1] *= -1.0
            polys.append(P)
    ev.to_curve_clear()
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    return polys


# ------------------------------------------------------------------ raster
def _cross_dilate(m):
    o = m.copy()
    o[1:] |= m[:-1]; o[:-1] |= m[1:]; o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]
    return o


def _square_dilate(m):
    o = _cross_dilate(m)
    o[1:, 1:] |= m[:-1, :-1]; o[:-1, :-1] |= m[1:, 1:]; o[1:, :-1] |= m[:-1, 1:]; o[:-1, 1:] |= m[1:, :-1]
    return o


def offset_mask(ins, n):
    """Grow (n>0) or shrink (n<0) a supersampled mask by |n| samples (octagonal SE):
    a stroke-weight change of 2*n/ss target pixels."""
    if n == 0:
        return ins
    m = ins if n > 0 else ~ins
    for i in range(abs(n)):
        m = _square_dilate(m) if i % 2 else _cross_dilate(m)
    return m if n > 0 else ~m


def raster(polys, H, W, ss=4, evenodd=False, weight=0):
    """polys in TARGET PIXEL coords (x right, y down, pixel (0,0) spans [0,1)).
    Returns coverage HxW in [0,1] by ss x ss supersampling, nonzero winding.
    weight = outline offset in supersamples (stroke-weight allowance)."""
    Hs, Ws = H * ss, W * ss
    acc = np.zeros((Hs, Ws + 1), np.int32)
    X0 = []; Y0 = []; X1 = []; Y1 = []
    for P in polys:
        Q = P * ss
        X0.append(Q[:, 0]); Y0.append(Q[:, 1])
        X1.append(np.roll(Q[:, 0], -1)); Y1.append(np.roll(Q[:, 1], -1))
    if not X0:
        return np.zeros((H, W))
    x0 = np.concatenate(X0); y0 = np.concatenate(Y0); x1 = np.concatenate(X1); y1 = np.concatenate(Y1)
    d = np.where(y1 > y0, 1, -1)
    ya = np.minimum(y0, y1); yb = np.maximum(y0, y1)
    r0 = np.clip(np.ceil(ya - .5).astype(np.int64), 0, Hs)
    r1 = np.clip(np.ceil(yb - .5).astype(np.int64), 0, Hs)
    cnt = np.maximum(r1 - r0, 0)
    keep = (cnt > 0) & (y1 != y0)
    x0, y0, x1, y1, d, r0, cnt = x0[keep], y0[keep], x1[keep], y1[keep], d[keep], r0[keep], cnt[keep]
    if len(cnt) == 0:
        return np.zeros((H, W))
    idx = np.repeat(np.arange(len(cnt)), cnt)
    off = np.arange(len(idx)) - np.repeat(np.cumsum(cnt) - cnt, cnt)
    rows = r0[idx] + off
    yc = rows + .5
    xi = x0[idx] + (yc - y0[idx]) * (x1[idx] - x0[idx]) / (y1[idx] - y0[idx])
    cols = np.clip(np.ceil(xi - .5).astype(np.int64), 0, Ws)
    np.add.at(acc, (rows, cols), d[idx])
    wind = np.cumsum(acc, 1)[:, :Ws]
    ins = (wind % 2 != 0) if evenodd else (wind != 0)
    if weight:
        ins = offset_mask(ins, int(weight))
    return ins.reshape(H, ss, W, ss).mean((1, 3))


def poly_bbox(polys):
    P = np.concatenate(polys, 0)
    return P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max()


def xform(polys, p, c0):
    """p = (log sx, log sy, theta_deg, tx, ty); c0 = font-space centre."""
    lsx, lsy, th, tx, ty = p
    sx, sy = math.exp(lsx), math.exp(lsy)
    c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
    out = []
    for P in polys:
        u = (P[:, 0] - c0[0]) * sx
        v = (P[:, 1] - c0[1]) * sy
        out.append(np.stack([tx + c * u - s * v, ty + s * u + c * v], 1))
    return out


# -------------------------------------------------------------- template model
def template_sampler(cov, y0, x0):
    """Bilinear sampler of a raster coverage map (a V2 crop) used as a 'font'.
    Template coordinates are V2 pixel coordinates (crop origin y0, x0)."""
    Ht, Wt = cov.shape

    def sample(X, Y):
        X = X - x0 - .5
        Y = Y - y0 - .5
        xi = np.floor(X).astype(int); yi = np.floor(Y).astype(int)
        fx = X - xi; fy = Y - yi

        def g(yy, xx):
            ok = (yy >= 0) & (yy < Ht) & (xx >= 0) & (xx < Wt)
            return np.where(ok, cov[np.clip(yy, 0, Ht - 1), np.clip(xx, 0, Wt - 1)], 0.0)
        return (g(yi, xi) * (1 - fx) * (1 - fy) + g(yi, xi + 1) * fx * (1 - fy)
                + g(yi + 1, xi) * (1 - fx) * fy + g(yi + 1, xi + 1) * fx * fy)
    return sample


def raster_template(sample, p, c0, H, W, ss=4):
    """Inverse-map a template through transform p (template px -> target px)."""
    lsx, lsy, th, tx, ty = p
    sx, sy = math.exp(lsx), math.exp(lsy)
    c, s = math.cos(math.radians(th)), math.sin(math.radians(th))
    ys = (np.arange(H * ss) + .5) / ss
    xs = (np.arange(W * ss) + .5) / ss
    Xg, Yg = np.meshgrid(xs, ys)
    dx = Xg - tx; dy = Yg - ty
    u = (c * dx + s * dy) / sx
    v = (-s * dx + c * dy) / sy
    val = sample(u + c0[0], v + c0[1])
    return val.reshape(H, ss, W, ss).mean((1, 3))


# ------------------------------------------------------------------ metrics
def soft_iou(M, T, D=None):
    if D is not None:
        M = M[D]; T = T[D]
    den = np.maximum(M, T).sum()
    return float(np.minimum(M, T).sum() / den) if den > 0 else 0.0


def bin_iou(M, T, D=None, th=.5):
    m = M >= th; t = T >= th
    if D is not None:
        m = m[D]; t = t[D]
    u = (m | t).sum()
    return float((m & t).sum() / u) if u else 0.0


def upsample_bilinear(A, f):
    H, W = A.shape
    ys = (np.arange(H * f) + .5) / f - .5
    xs = (np.arange(W * f) + .5) / f - .5
    y0 = np.clip(np.floor(ys).astype(int), 0, H - 1); x0 = np.clip(np.floor(xs).astype(int), 0, W - 1)
    y1 = np.clip(y0 + 1, 0, H - 1); x1 = np.clip(x0 + 1, 0, W - 1)
    fy = np.clip(ys - np.floor(ys), 0, 1)[:, None]; fx = np.clip(xs - np.floor(xs), 0, 1)[None, :]
    a = A[y0][:, x0]; b = A[y0][:, x1]; c = A[y1][:, x0]; d = A[y1][:, x1]
    return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy


def boundary_pts(m):
    b = m & ~erode(m, 1)
    ys, xs = np.nonzero(b)
    return np.stack([xs + .5, ys + .5], 1)


def edge_dist(M4, T4, f):
    """Symmetric contour distance between two masks given at f x V2 res. Returns V2 px."""
    a = boundary_pts(M4 >= .5); b = boundary_pts(T4 >= .5)
    if len(a) == 0 or len(b) == 0:
        return dict(mean=None, p95=None, max=None)

    def nn(P, Q):
        out = np.empty(len(P))
        for i in range(0, len(P), 512):
            d = ((P[i:i + 512, None, :] - Q[None, :, :]) ** 2).sum(-1)
            out[i:i + 512] = np.sqrt(d.min(1))
        return out
    da = nn(a, b); db = nn(b, a)
    allv = np.concatenate([da, db]) / f
    return dict(mean=float(allv.mean()), p95=float(np.percentile(allv, 95)), max=float(allv.max()),
                model_to_ref=float(da.mean() / f), ref_to_model=float(db.mean() / f))


# ------------------------------------------------------------------ optimiser
def nelder_mead(fn, x0, step, iters=300, tol=1e-6):
    n = len(x0)
    pts = [np.array(x0, float)]
    for i in range(n):
        q = np.array(x0, float); q[i] += step[i]; pts.append(q)
    vals = [fn(p) for p in pts]
    for it in range(iters):
        o = np.argsort(vals)
        pts = [pts[i] for i in o]; vals = [vals[i] for i in o]
        if abs(vals[-1] - vals[0]) < tol and it > 40:
            break
        cen = np.mean(pts[:-1], 0)
        xr = cen + (cen - pts[-1]); fr = fn(xr)
        if fr < vals[0]:
            xe = cen + 2 * (cen - pts[-1]); fe = fn(xe)
            if fe < fr:
                pts[-1], vals[-1] = xe, fe
            else:
                pts[-1], vals[-1] = xr, fr
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = cen + .5 * (pts[-1] - cen); fc = fn(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                for i in range(1, len(pts)):
                    pts[i] = pts[0] + .5 * (pts[i] - pts[0]); vals[i] = fn(pts[i])
    i = int(np.argmin(vals))
    return pts[i], vals[i]
