# COPY of WorkFiles/BlackCloak_Review/male/gap/scripts/gap_lib.py (review tool, unchanged below the marker) + BlackCloak_MH_v2 additions at the end.
# ---- original gap_lib.py ----

# Image helpers for the gap measurer. Runs inside Blender 5.2 Python (numpy available).
import bpy, numpy as np, os

def load(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    a = np.empty(w*h*4, dtype=np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[::-1, :, :3] * 255.0   # top-down, sRGB-coded 0..255
    bpy.data.images.remove(img)
    return np.ascontiguousarray(a)

def save(path, rgb):
    rgb = np.clip(np.asarray(rgb, dtype=np.float32), 0, 255)
    if rgb.ndim == 2:
        rgb = np.stack([rgb]*3, -1)
    h, w = rgb.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = rgb / 255.0
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)

def lum(rgb):
    return rgb[..., 0]*0.2126 + rgb[..., 1]*0.7152 + rgb[..., 2]*0.0722

def box_down(a, f):
    h, w = a.shape[:2]
    h2, w2 = h//f, w//f
    a = a[:h2*f, :w2*f]
    if a.ndim == 2:
        return a.reshape(h2, f, w2, f).mean((1, 3))
    return a.reshape(h2, f, w2, f, a.shape[2]).mean((1, 3))

def bilinear(src, xs, ys, fill=255.0):
    h, w = src.shape[:2]
    x0 = np.floor(xs).astype(np.int64); y0 = np.floor(ys).astype(np.int64)
    fx = (xs - x0)[..., None] if src.ndim == 3 else (xs - x0)
    fy = (ys - y0)[..., None] if src.ndim == 3 else (ys - y0)
    valid = (x0 >= 0) & (y0 >= 0) & (x0 < w-1) & (y0 < h-1)
    x0c = np.clip(x0, 0, w-2); y0c = np.clip(y0, 0, h-2)
    a = src[y0c, x0c]; b = src[y0c, x0c+1]; c = src[y0c+1, x0c]; d = src[y0c+1, x0c+1]
    out = (a*(1-fx)+b*fx)*(1-fy) + (c*(1-fx)+d*fx)*fy
    if src.ndim == 3:
        out[~valid] = fill
    else:
        out[~valid] = fill
    return out

def warp_to_ref(src2x, s, tx, ty, out_scale=1, H=674, W=417):
    """src2x: ours at 2x of its own 1x frame. x_ref = s*x_ours1x + tx.
    Returns image in ref frame at out_scale (1 or 2)."""
    Y, X = np.mgrid[0:H*out_scale, 0:W*out_scale].astype(np.float64)
    xr = (X + 0.5)/out_scale; yr = (Y + 0.5)/out_scale
    xo = (xr - tx)/s; yo = (yr - ty)/s          # ours 1x coords (pixel-edge units)
    xs = xo*2 - 0.5; ys = yo*2 - 0.5            # ours 2x pixel-centre index
    return bilinear(src2x, xs, ys)

def iou(a, b):
    i = np.logical_and(a, b).sum(); u = np.logical_or(a, b).sum()
    return float(i)/float(u) if u else 0.0

def boundary(mask):
    m = mask
    e = np.zeros_like(m)
    e[1:-1, 1:-1] = m[1:-1, 1:-1] & ~(m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:])
    return np.argwhere(e)  # (y,x)

def nn_dist(pa, pb, chunk=2000):
    """min distance from each point in pa to the set pb"""
    out = np.empty(len(pa))
    pbf = pb.astype(np.float64)
    for i in range(0, len(pa), chunk):
        d = pa[i:i+chunk, None, :].astype(np.float64) - pbf[None, :, :]
        out[i:i+chunk] = np.sqrt((d**2).sum(-1)).min(1)
    return out

def smooth1d(v, k):
    if k <= 1: return v
    ker = np.ones(k)/k
    pad = k//2
    vp = np.pad(v, pad, mode='edge')
    return np.convolve(vp, ker, mode='valid')[:len(v)]

def blur2d(a, k):
    # separable box blur, odd k
    if k <= 1: return a
    pad = k//2
    ap = np.pad(a, pad, mode='edge')
    c = np.cumsum(np.cumsum(ap, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = a.shape
    s = c[k:k+h, k:k+w] - c[0:h, k:k+w] - c[k:k+h, 0:w] + c[0:h, 0:w]
    return s/(k*k)

def fill_holes_rows(mask):
    """fill background runs fully enclosed left/right in each row (for outline-based metrics)"""
    out = mask.copy()
    for y in range(mask.shape[0]):
        xs = np.where(mask[y])[0]
        if len(xs): out[y, xs[0]:xs[-1]+1] = True
    return out

# ---- BlackCloak_MH_v2 additions ----
def srgb_to_lin01(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4)

def lin_to_srgb01(l):
    l = np.clip(np.asarray(l, dtype=np.float64), 0, 1)
    return np.where(l <= 0.0031308, l*12.92, 1.055*l**(1/2.4)-0.055)

def spectrum(p):
    """gap_measure2 grain spectrum of a square luma patch: band energy fractions by period (px) + anisotropy
    (vertical-frequency energy / horizontal-frequency energy; 1 = isotropic)."""
    p = p - blur2d(p, 9); n = p.shape[0]
    w = np.hanning(n); p = p*np.outer(w, w)
    F = np.abs(np.fft.fftshift(np.fft.fft2(p)))**2
    fy, fx = np.mgrid[-n//2:n//2, -n//2:n//2]/n; fr = np.hypot(fx, fy)
    tot = F[fr > 0].sum(); out = {}
    for nm, (plo, phi) in {'p2_3': (2, 3), 'p3_5': (3, 5), 'p5_10': (5, 10), 'p10_16': (10, 16)}.items():
        out[nm] = float(F[(fr <= 1/plo) & (fr > 1/phi)].sum()/tot)
    v = F[(np.abs(fy) > 2*np.abs(fx)) & (fr > 0.06)].sum(); h = F[(np.abs(fx) > 2*np.abs(fy)) & (fr > 0.06)].sum()
    out['aniso_vfreq_over_hfreq'] = float(v/(h+1e-9))
    # orientation-free anisotropy: ratio of max to min energy over 8 orientation sectors (1 = isotropic)
    ang = np.arctan2(fy, fx) % np.pi; sec = []
    for k in range(8):
        a0, a1 = k*np.pi/8, (k+1)*np.pi/8
        sec.append(F[(ang >= a0) & (ang < a1) & (fr > 0.06)].sum())
    out['aniso_sector_max_over_min'] = float(max(sec)/(min(sec)+1e-9))
    return out

def acf_halfwidth(p):
    """radius (px) where the radially averaged autocorrelation of the high-passed patch first drops below 0.5 = grain blob size"""
    p = p - blur2d(p, 9); p = p - p.mean()
    F = np.fft.fft2(p); A = np.real(np.fft.ifft2(F*np.conj(F))); A = np.fft.fftshift(A)/A.max()
    n = p.shape[0]; yy, xx = np.mgrid[-n//2:n//2, -n//2:n//2]; r = np.hypot(xx, yy)
    for rr in np.arange(0.5, n/2, 0.5):
        v = A[(r >= rr-0.5) & (r < rr+0.5)].mean()
        if v < 0.5: return float(rr)
    return float(n/2)

def best_align(m, refm, s_range=(0.9, 1.1), s_steps=21, t_px=24, t_step=2, fine=True):
    """similarity (scale + translate, no rotation) alignment of mask m (same frame size as refm, same framing
    convention x_ref = s*x + tx) maximising IoU. Returns (iou, s, tx, ty). Scale is about the frame origin."""
    H, W = refm.shape
    ys, xs = np.nonzero(refm); rb = (xs.min(), xs.max(), ys.min(), ys.max())
    ys, xs = np.nonzero(m); sb = (xs.min(), xs.max(), ys.min(), ys.max())
    mf = m.astype(np.float32)
    def sc(s, tx, ty):
        w = warp_to_ref_1x(mf, s, tx, ty, H, W) > 0.5
        return iou(w, refm)
    best = (-1, 1, 0, 0)
    for s in np.linspace(s_range[0], s_range[1], s_steps):
        cx = (rb[0]+rb[1])/2 - s*(sb[0]+sb[1])/2; cy = (rb[2]+rb[3])/2 - s*(sb[2]+sb[3])/2
        for dx in range(-t_px, t_px+1, t_step*2):
            for dy in range(-t_px, t_px+1, t_step*2):
                v = sc(s, cx+dx, cy+dy)
                if v > best[0]: best = (v, s, cx+dx, cy+dy)
    if fine:
        v, s, tx, ty = best
        for st, ss in ((2, 0.005), (1, 0.0025), (0.5, 0.00125)):
            imp = True
            while imp:
                imp = False
                for d in ((ss, 0, 0), (-ss, 0, 0), (0, st, 0), (0, -st, 0), (0, 0, st), (0, 0, -st)):
                    q = (s+d[0], tx+d[1], ty+d[2]); vv = sc(*q)
                    if vv > best[0] + 1e-7: best = (vv,) + q; v, s, tx, ty = best; imp = True
    return best

def warp_to_ref_1x(src, s, tx, ty, H, W, fill=0.0):
    """out(x,y) = src((x-tx)/s, (y-ty)/s): x_ref = s*x_src + tx, pixel-centre convention, bilinear"""
    Y, X = np.mgrid[0:H, 0:W].astype(np.float64)
    xs = (X + 0.5 - tx)/s - 0.5; ys = (Y + 0.5 - ty)/s - 0.5
    return bilinear(src, xs, ys, fill)

def hem_profile(m, x0=20, x1=400):
    low = np.array([np.where(m[:, x])[0][-1] if m[:, x].any() else -1 for x in range(m.shape[1])])
    return low

def hem_jumps(m, x0=20, x1=400, thr=8):
    low = hem_profile(m)[x0:x1].astype(float)
    return int((np.abs(np.diff(low)) >= thr).sum())
