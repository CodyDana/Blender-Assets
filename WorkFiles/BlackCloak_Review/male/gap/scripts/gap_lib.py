
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
