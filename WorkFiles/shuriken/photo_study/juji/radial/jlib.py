"""Shared helpers for the Juji radial-profile study (run inside Blender's Python)."""
import numpy as np
import bpy

PHOTO = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Juji.JPG"
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial"


def load_image(path=PHOTO):
    """Return float32 array (H, W, 3), row 0 = TOP of the image, raw stored (sRGB) values 0..1."""
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    arr = px.reshape(h, w, 4)[::-1, :, :3].copy()
    bpy.data.images.remove(img)
    return arr


def save_png(path, arr):
    """arr: (H, W) or (H, W, 3) float 0..1 or bool, row 0 = top. Writes an 8-bit PNG."""
    a = np.asarray(arr)
    if a.dtype == bool:
        a = a.astype(np.float32)
    a = a.astype(np.float32)
    if a.ndim == 2:
        a = np.repeat(a[:, :, None], 3, axis=2)
    h, w = a.shape[:2]
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(a, 0, 1)
    rgba = rgba[::-1].ravel()
    img = bpy.data.images.new("tmp_out", w, h, alpha=True)
    img.pixels.foreach_set(rgba)
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


# ---------- small morphology / labelling toolkit (numpy only) ----------

def _disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return (x * x + y * y) <= r * r + 0.25


def dilate(m, r):
    """Binary dilation with a disk of radius r (shift-OR, exact for disk)."""
    m = m.astype(bool)
    out = np.zeros_like(m)
    k = _disk(r)
    H, W = m.shape
    pad = np.pad(m, r)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if k[dy + r, dx + r]:
                out |= pad[r + dy:r + dy + H, r + dx:r + dx + W]
    return out


def erode(m, r):
    return ~dilate(~m.astype(bool), r)


def opening(m, r):
    return dilate(erode(m, r), r)


def closing(m, r):
    return erode(dilate(m, r), r)


def label(m):
    """4-connected component labelling via union-find on runs (pure numpy + python loops over rows)."""
    m = m.astype(bool)
    H, W = m.shape
    lab = np.zeros((H, W), dtype=np.int32)
    parent = [0]

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    prev_runs = []
    nxt = 1
    for y in range(H):
        row = m[y]
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        starts = np.nonzero(d == 1)[0]
        ends = np.nonzero(d == -1)[0]
        runs = []
        j = 0
        for s, e in zip(starts, ends):
            lbl = 0
            # overlapping runs in previous row (4-connectivity: column overlap)
            while j < len(prev_runs) and prev_runs[j][1] <= s:
                j += 1
            k = j
            while k < len(prev_runs) and prev_runs[k][0] < e:
                pl = find(prev_runs[k][2])
                if lbl == 0:
                    lbl = pl
                elif pl != lbl:
                    a, b = sorted((lbl, pl))
                    parent[b] = a
                    lbl = a
                k += 1
            if lbl == 0:
                parent.append(nxt)
                lbl = nxt
                nxt += 1
            runs.append((s, e, lbl))
            lab[y, s:e] = lbl
        prev_runs = runs
    # resolve
    roots = np.array([find(i) for i in range(len(parent))], dtype=np.int32)
    lab = roots[lab]
    uniq, inv = np.unique(lab, return_inverse=True)
    lab = inv.reshape(H, W).astype(np.int32)
    if uniq[0] != 0:
        lab += 1
    return lab, lab.max()


def largest_component(m):
    lab, n = label(m)
    if n == 0:
        return m.astype(bool)
    counts = np.bincount(lab.ravel())
    counts[0] = 0
    return lab == np.argmax(counts)


def fill_holes(m):
    """Fill enclosed background regions. Returns (filled, holes_mask)."""
    bg = ~m.astype(bool)
    lab, n = label(bg)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist())
    border.discard(0)
    outside = np.isin(lab, list(border))
    holes = bg & ~outside
    return m.astype(bool) | holes, holes


def boundary(m):
    m = m.astype(bool)
    return m & ~erode(m, 1)


def gblur(img, s):
    """Separable Gaussian blur (edge-replicated), works on (H,W) or (H,W,C)."""
    img = np.asarray(img, dtype=np.float32)
    r = max(1, int(3 * s + 0.5))
    x = np.arange(-r, r + 1)
    k = np.exp(-0.5 * (x / s) ** 2)
    k /= k.sum()
    pad = [(r, r), (0, 0)] + [(0, 0)] * (img.ndim - 2)
    p = np.pad(img, pad, mode='edge')
    out = np.zeros_like(img)
    for i, kv in enumerate(k):
        out += kv * p[i:i + img.shape[0]]
    pad = [(0, 0), (r, r)] + [(0, 0)] * (img.ndim - 2)
    p = np.pad(out, pad, mode='edge')
    out2 = np.zeros_like(img)
    for i, kv in enumerate(k):
        out2 += kv * p[:, i:i + img.shape[1]]
    return out2


def bilinear(img, x, y):
    """Sample img (H,W) or (H,W,C) at float pixel coords x (col), y (row); out-of-range -> clamped."""
    H, W = img.shape[:2]
    x = np.clip(np.asarray(x, dtype=np.float64), 0, W - 1.001)
    y = np.clip(np.asarray(y, dtype=np.float64), 0, H - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    if img.ndim == 3:
        fx = fx[..., None]; fy = fy[..., None]
    v00 = img[y0, x0]; v01 = img[y0, x0 + 1]; v10 = img[y0 + 1, x0]; v11 = img[y0 + 1, x0 + 1]
    return (v00 * (1 - fx) * (1 - fy) + v01 * fx * (1 - fy) + v10 * (1 - fx) * fy + v11 * fx * fy)
