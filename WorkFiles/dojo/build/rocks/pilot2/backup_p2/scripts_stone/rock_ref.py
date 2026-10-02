"""Rock reference tools (STONE_BUILDING_STUDY.md 6.1 step 9, 6.8): silhouettes of rocks drawn on a light studio sheet,
shape measures that run identically on the sheet and on our renders, and value/hue per region. numpy + PIL only
(no bpy, no scipy), so it runs under `py -3` and under Blender's Python.

Silhouette (seed mode, study 6.8 item 2, for rocks >= 60 px on a flat light-grey sheet background):
  background = median of the ROI border; a pixel is rock when it differs from the background by colour distance,
  chroma, or local texture (std in a 5x5 window) beyond thresholds; then close, fill holes, open and keep the
  component(s) touching the ROI's seed box. The ground contact shadow is neutral and smooth, so it fails the chroma
  and texture tests; only its darkest 1-2 px at the contact line pass (the trace error is +-2 px).

Shape measures (scale-free; both masks resampled to the same height first, so pixel effects match):
  aspect w/h, solidity (area / convex-hull area), extent (area / bbox area), straight-run share of the outline
  (Douglas-Peucker at 1.2 % of the bbox diagonal; runs longer than 6 % of the perimeter), corner count (DP turns
  > 35 deg), corner rounding = median fitted radius at those corners / short side (the arris radius of the
  silhouette), top flatness (std of the top profile / height), and IoU after centring (best over +-3 % shifts).
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np

try:                       # PIL is absent from Blender's Python; only outline / measures run there
    from PIL import Image
except ImportError:        # pragma: no cover
    Image = None


# ------------------------------------------------------------------------------------------------ io
def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)


# ------------------------------------------------------------------------------------------------ morphology
def _shift(M, dy, dx):
    O = np.zeros_like(M)
    H, W = M.shape
    ys0, ys1 = max(0, dy), min(H, H + dy)
    xs0, xs1 = max(0, dx), min(W, W + dx)
    O[ys0:ys1, xs0:xs1] = M[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return O


def dilate(M, r=1):
    O = M.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r + r:
                O |= _shift(M, dy, dx)
    return O


def erode(M, r=1):
    return ~dilate(~M, r)


def close(M, r=1):
    return erode(dilate(M, r), r)


def open_(M, r=1):
    return dilate(erode(M, r), r)


def label(M):
    """4-connected components (pure numpy union-find over runs). Returns (labels, n)."""
    H, W = M.shape
    lab = np.zeros((H, W), np.int64)
    parent = [0]

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    nxt = 1
    for y in range(H):
        row = M[y]
        x = 0
        while x < W:
            if not row[x]:
                x += 1
                continue
            x0 = x
            while x < W and row[x]:
                x += 1
            parent.append(nxt)
            lab[y, x0:x] = nxt
            if y > 0:
                above = np.unique(lab[y - 1, x0:x])
                for a in above[above > 0]:
                    ra, rb = find(int(a)), find(nxt)
                    if ra != rb:
                        parent[max(ra, rb)] = min(ra, rb)
            nxt += 1
    roots = np.array([find(i) for i in range(nxt)])
    uniq, inv = np.unique(roots, return_inverse=True)
    lab = inv[lab]
    return lab, len(uniq) - 1


def fill_holes(M):
    lab, n = label(~M)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist())
    holes = ~M & ~np.isin(lab, list(border))
    return M | holes


def local_std(L, r=2):
    acc = np.zeros_like(L)
    acc2 = np.zeros_like(L)
    n = 0
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            s = np.roll(np.roll(L, dy, 0), dx, 1)
            acc += s
            acc2 += s * s
            n += 1
    m = acc / n
    return np.sqrt(np.maximum(acc2 / n - m * m, 0))


# ------------------------------------------------------------------------------------------------ silhouette
def silhouette(img, box, seed=None, t_dist=34.0, t_chroma=14.0, t_std=7.0, close_r=2, open_r=1):
    """Rock mask inside ``box`` (x0, y0, x1, y1) of an RGB float image (0-255). ``seed`` (x0, y0, x1, y1, ROI-local
    or None = the ROI centre third) picks the component(s) to keep. Returns (mask, info)."""
    x0, y0, x1, y1 = box
    sub = img[y0:y1, x0:x1]
    border = np.concatenate([sub[0], sub[-1], sub[:, 0], sub[:, -1]])
    bg = np.median(border, axis=0)
    d = np.sqrt(((sub - bg) ** 2).sum(-1))
    chroma = sub.max(-1) - sub.min(-1)
    L = sub.mean(-1)
    st = local_std(L, 2)
    darker = (bg.mean() - L)
    # neutral, smooth, moderately darker pixels are the ground shadow: they count only when much darker (d is
    # sqrt(3) x the darkening on neutral grey) or textured
    m = (((d > t_dist) & (chroma > 8)) | (darker > 70) | ((chroma > t_chroma) & (darker > 6))
         | ((st > t_std) & (darker > 12) & (chroma > 6)) | ((st > 2 * t_std) & (darker > 10)))
    m = close(m, close_r)
    m = fill_holes(m)
    m = open_(m, open_r)
    # the ground contact shadow leaves thin horizontal strips at the foot: a vertical opening (5 px) removes them
    v = m.copy()
    for k in range(1, 3):
        v &= _shift(m, k, 0) & _shift(m, -k, 0)
    vd = v.copy()
    for k in range(1, 3):
        vd |= _shift(v, k, 0) | _shift(v, -k, 0)
    m = vd
    lab, n = label(m)
    H, W = m.shape
    if seed is None:
        seed = (W // 3, H // 3, 2 * W // 3, 2 * H // 3)
    sx0, sy0, sx1, sy1 = seed
    ids = np.unique(lab[sy0:sy1, sx0:sx1])
    ids = ids[ids > 0]
    if len(ids) == 0:
        raise RuntimeError(f"no rock component in the seed box of ROI {box}")
    sizes = np.bincount(lab.ravel())
    keep = [i for i in ids if sizes[i] > 0.15 * sizes[ids].max()]
    m = np.isin(lab, keep)
    m = fill_holes(m)
    ys, xs = np.nonzero(m)
    info = {"box": list(box), "bg_rgb": [round(float(c), 1) for c in bg], "area_px": int(m.sum()),
            "bbox_px": [int(xs.min() + x0), int(ys.min() + y0), int(xs.max() + x0 + 1), int(ys.max() + y0 + 1)],
            "w_px": int(xs.max() - xs.min() + 1), "h_px": int(ys.max() - ys.min() + 1)}
    return m, info


def crop_to_mask(m, pad=0):
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    out = m[y0:y1, x0:x1]
    if pad:
        out = np.pad(out, pad)
    return out


def resample_h(m, h):
    """Mask cropped to its bbox and resampled to height ``h`` (aspect kept), as bool."""
    c = crop_to_mask(m)
    H, W = c.shape
    w = max(1, int(round(W * h / H)))
    im = Image.fromarray((c * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    return np.asarray(im) > 127


# ------------------------------------------------------------------------------------------------ outline + measures
def outline(m):
    """Ordered outer boundary (Moore neighbour trace) of the largest component, (n, 2) x, y floats."""
    lab, n = label(m)
    if n > 1:
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        m = lab == int(np.argmax(sizes))
    M = np.pad(m, 1)
    H, W = M.shape
    ys, xs = np.nonzero(M)
    i = np.argmin(ys * W + xs)
    p = (int(ys[i]), int(xs[i]))
    # Moore-neighbour tracing, clockwise from West
    off = [(0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1)]
    idx_of = {o: k for k, o in enumerate(off)}
    start = p
    bdir = 0                                   # the backtrack (a background pixel) lies West of the start
    pts = [p]
    second = None
    for _ in range(8 * M.size):
        found = False
        for k in range(1, 9):
            d = (bdir + k) % 8
            q = (p[0] + off[d][0], p[1] + off[d][1])
            if M[q]:
                bp = (p[0] + off[(d - 1) % 8][0], p[1] + off[(d - 1) % 8][1])
                p = q
                bdir = idx_of[(bp[0] - p[0], bp[1] - p[1])]
                found = True
                break
        if not found:
            break
        if second is None:
            second = p
        elif p == second and pts[-1] == start:
            pts.pop()
            break
        pts.append(p)
    P = np.array([[x - 1, y - 1] for y, x in pts], float)
    return P


def _dp(P, eps):
    """Douglas-Peucker on an open polyline -> kept indices."""
    keep = np.zeros(len(P), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(P) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        A, B = P[a], P[b]
        AB = B - A
        L = math.hypot(*AB)
        seg = P[a + 1:b] - A
        if L < 1e-9:
            d = np.hypot(seg[:, 0], seg[:, 1])
        else:
            d = np.abs(seg[:, 0] * AB[1] - seg[:, 1] * AB[0]) / L
        k = int(np.argmax(d))
        if d[k] > eps:
            keep[a + 1 + k] = True
            stack += [(a, a + 1 + k), (a + 1 + k, b)]
    return np.nonzero(keep)[0]


def _circle_fit(Q):
    """Algebraic (Kasa) circle fit -> radius."""
    x, y = Q[:, 0], Q[:, 1]
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x * x + y * y
    c, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = c[0] / 2, c[1] / 2
    r2 = c[2] + cx * cx + cy * cy
    return math.sqrt(max(r2, 0.0))


def convex_hull_area(P):
    pts = sorted(set(map(tuple, np.round(P, 3))))
    if len(pts) < 3:
        return 0.0

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    h = np.array(lo[:-1] + up[:-1])
    x, y = h[:, 0], h[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def shape_measures(m, h=300):
    """Scale-free silhouette measures (module docstring) on ``m`` resampled to height ``h``."""
    r = resample_h(m, h)
    H, W = r.shape
    P = outline(r)
    n = len(P)
    seg = np.hypot(*np.diff(np.vstack([P, P[:1]]), axis=0).T)
    perim = float(seg.sum())
    diag = math.hypot(W, H)
    # Douglas-Peucker on the closed loop (split at the farthest point from the start)
    j = int(np.argmax(np.hypot(*(P - P[0]).T)))
    i1 = _dp(P[:j + 1], 0.012 * diag)
    i2 = _dp(np.vstack([P[j:], P[:1]]), 0.012 * diag) + j
    idx = np.unique(np.concatenate([i1, i2[:-1]])) % n
    idx = np.unique(idx)
    V = P[idx]
    k = len(V)
    seglen = np.hypot(*(np.roll(V, -1, 0) - V).T)
    straight = float(seglen[seglen > 0.06 * perim].sum() / perim)
    # turning angles at DP vertices
    a_in = V - np.roll(V, 1, 0)
    a_out = np.roll(V, -1, 0) - V
    ang = np.degrees(np.abs(np.arctan2(a_in[:, 0] * a_out[:, 1] - a_in[:, 1] * a_out[:, 0],
                                       (a_in * a_out).sum(1))))
    corners = np.nonzero(ang > 35)[0]
    short = min(W, H)
    radii = []
    win = max(4, int(0.035 * perim))
    for c in corners:
        ii = idx[c]
        Q = P[[(ii + t) % n for t in range(-win, win + 1)]]
        radii.append(_circle_fit(Q) / short)
    area = float(r.sum())
    hull = convex_hull_area(P)
    # top profile: highest pixel per column over the middle 70 % of the width
    cols = np.arange(int(0.15 * W), int(0.85 * W))
    top = np.array([np.argmax(r[:, c]) for c in cols], float)
    return {"aspect_w_over_h": round(W / H, 3), "solidity": round(area / max(hull, 1), 3),
            "extent": round(area / (W * H), 3), "straight_run_share": round(straight, 3),
            "dp_vertices": int(k), "corners_gt35deg": int(len(corners)),
            "corner_radius_over_short_median": round(float(np.median(radii)), 3) if radii else None,
            "top_profile_std_over_h": round(float(top.std() / H), 4)}


def iou(a, b, h=300, search=0.03):
    """IoU of two masks after resampling both to height ``h`` and centring their bboxes; best over shifts within
    +-``search`` x h (registration error of hand-free crops)."""
    A = resample_h(a, h)
    B = resample_h(b, h)
    W = max(A.shape[1], B.shape[1]) + 2 * int(search * h) + 4
    Hh = h + 2 * int(search * h) + 4

    def place(M, dx=0, dy=0):
        O = np.zeros((Hh, W), bool)
        y = (Hh - M.shape[0]) // 2 + dy
        x = (W - M.shape[1]) // 2 + dx
        O[y:y + M.shape[0], x:x + M.shape[1]] = M
        return O
    PA = place(A)
    best = 0.0
    s = int(search * h)
    for dy in range(-s, s + 1, max(1, s // 3)):
        for dx in range(-s, s + 1, max(1, s // 3)):
            PB = place(B, dx, dy)
            u = (PA | PB).sum()
            v = (PA & PB).sum() / max(u, 1)
            best = max(best, float(v))
    return round(best, 4)


def save_mask(m, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((m * 255).astype(np.uint8)).save(path)


def overlay(img, box, m, path, scale=3):
    x0, y0, x1, y1 = box
    sub = img[y0:y1, x0:x1].copy()
    edge = m & ~erode(m, 1)
    sub[edge] = [255, 0, 255]
    im = Image.fromarray(sub.astype(np.uint8))
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path)
