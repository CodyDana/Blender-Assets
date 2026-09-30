"""Tree silhouette measurement from a reference panel or an orthographic render (PIL + numpy only).

TREE_BUILDING_STUDY.md section 6.2. No bpy, no scipy: runs under the system Python 3.12 and under Blender's Python.

Masks (study 6.2 step 2):
    background = median of a corner patch; foreground = colour distance > 45;
    foliage = fg & G > R+4 & G > B+4; wood = fg & R > B+8 & not foliage; the scale figure = neutral grey.
Everything below the panel's ``base_y`` (the mound / rock / ground band) is cut before measuring.

Metrics per panel (all in metres through ``px_per_m``): height (base to apex), crown width, crown base, lean
(apex x - base x), foliage centroid offset, pad count (components after a closing at half resolution, >= 2 % of
the foliage area), tiers (peaks of the per-row width profile) and row fill (foliage px / sum of per-row spans).
``iou`` aligns two masks by trunk base with heights matched.
"""
from __future__ import annotations

import json
import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    from PIL import Image
except ImportError:  # Blender's Python has no PIL: callers pass arrays instead
    Image = None


# ----------------------------------------------------------------------------- io

def load_rgb(path: str) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32)


def crop(arr: np.ndarray, box: Sequence[int]) -> np.ndarray:
    x0, y0, x1, y1 = box
    return arr[y0:y1, x0:x1]


# ----------------------------------------------------------------------------- masks

def background_colour(arr: np.ndarray, patch: int = 12) -> np.ndarray:
    corners = [arr[:patch, :patch], arr[:patch, -patch:]]
    return np.median(np.concatenate([c.reshape(-1, 3) for c in corners]), axis=0)


def masks(arr: np.ndarray, base_y: Optional[int] = None, bg: Optional[np.ndarray] = None,
          dist: float = 45.0) -> Dict[str, np.ndarray]:
    """Return fg / foliage / wood / figure boolean masks of an RGB float array (0-255)."""
    if bg is None:
        bg = background_colour(arr)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    fg = np.linalg.norm(arr - bg[None, None, :], axis=-1) > dist
    # Hue split (deviation from the study's G>R+4 rule, which labels the sheet's dark olive needles as wood):
    # needles sit at hue 55-200 deg, bark at 0-50 deg. Low-saturation pixels are neutral (rock, figure).
    hue, sat, _val = hsv(arr)
    neutral = sat < 0.10
    foliage = fg & ~neutral & (hue >= 52.0) & (hue <= 200.0)
    wood = fg & ~foliage & ~(neutral & (np.maximum(np.maximum(r, g), b) > 90))
    figure = fg & neutral & ~foliage & ~wood
    if base_y is not None:
        for m in (fg, foliage, wood):
            m[base_y:, :] = False
    return {"fg": fg, "foliage": foliage, "wood": wood, "figure": figure}


def hsv(arr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Hue in degrees, saturation 0-1, value 0-255 of an RGB float array (0-255)."""
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    d = np.maximum(mx - mn, 1e-6)
    h = np.where(mx == r, ((g - b) / d) % 6.0, np.where(mx == g, (b - r) / d + 2.0, (r - g) / d + 4.0)) * 60.0
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    return h, s, mx


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    out = mask.copy()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy > radius * radius:
                continue
            out |= np.roll(np.roll(mask, dy, 0), dx, 1)
    return out


def erode(mask: np.ndarray, radius: int) -> np.ndarray:
    return ~dilate(~mask, radius)


def closing(mask: np.ndarray, radius: int) -> np.ndarray:
    return erode(dilate(mask, radius), radius)


def components(mask: np.ndarray) -> Tuple[np.ndarray, int]:
    """4-connected labelling by run-length union-find (pure numpy + python, fast enough for panels)."""
    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    parent = [0]

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    prev_runs: List[Tuple[int, int, int]] = []
    for y in range(h):
        row = mask[y]
        if not row.any():
            prev_runs = []
            continue
        d = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
        starts = np.nonzero(d == 1)[0]
        ends = np.nonzero(d == -1)[0]
        runs = []
        j = 0
        for s, e in zip(starts, ends):
            lab = 0
            while j < len(prev_runs) and prev_runs[j][1] <= s:
                j += 1
            k = j
            while k < len(prev_runs) and prev_runs[k][0] < e:
                pl = prev_runs[k][2]
                if lab == 0:
                    lab = find(pl)
                else:
                    a, b = find(lab), find(pl)
                    if a != b:
                        parent[max(a, b)] = min(a, b)
                        lab = min(a, b)
                k += 1
            if lab == 0:
                parent.append(len(parent))
                lab = len(parent) - 1
            labels[y, s:e] = lab
            runs.append((s, e, lab))
        prev_runs = runs
    roots = np.array([find(i) for i in range(len(parent))], dtype=np.int32)
    labels = roots[labels]
    uniq = np.unique(labels[labels > 0])
    remap = np.zeros(roots.max() + 1, dtype=np.int32)
    remap[uniq] = np.arange(1, len(uniq) + 1)
    return remap[labels], len(uniq)


# ----------------------------------------------------------------------------- metrics

def row_profile(mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per row: leftmost x, rightmost x, pixel count (-1 where empty)."""
    h, w = mask.shape
    any_row = mask.any(1)
    left = np.where(any_row, mask.argmax(1), -1)
    right = np.where(any_row, w - 1 - mask[:, ::-1].argmax(1), -1)
    count = mask.sum(1)
    return left, right, count


def pad_components(foliage: np.ndarray, radius: int = 5, min_frac: float = 0.02, half: bool = True) -> List[Dict]:
    m = foliage[::2, ::2] if half else foliage
    m = closing(m, max(1, radius // (2 if half else 1)) if half else radius)
    lab, n = components(m)
    total = max(1, int(m.sum()))
    out = []
    s = 2 if half else 1
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(ys) < min_frac * total:
            continue
        out.append({"cx": float(xs.mean() * s), "cy": float(ys.mean() * s), "x0": int(xs.min() * s),
                    "x1": int(xs.max() * s), "y0": int(ys.min() * s), "y1": int(ys.max() * s),
                    "area_px": int(len(ys) * s * s)})
    return sorted(out, key=lambda c: c["cy"])


def tiers(foliage: np.ndarray, smooth: int = 7, min_prom: float = 0.15) -> int:
    _, _, count = row_profile(foliage)
    k = np.ones(smooth) / smooth
    c = np.convolve(count.astype(float), k, mode="same")
    if c.max() <= 0:
        return 0
    c = c / c.max()
    peaks = 0
    last_min = 1.0
    rising = False
    for i in range(1, len(c) - 1):
        if c[i] >= c[i - 1] and c[i] > c[i + 1]:
            if c[i] - last_min >= min_prom:
                peaks += 1
                last_min = c[i]
        last_min = min(last_min, c[i])
    return peaks


def metrics(fol: np.ndarray, wood: np.ndarray, base_xy: Tuple[float, float], px_per_m: float,
            pad_radius: int = 5) -> Dict:
    tree = fol | wood
    ys, xs = np.nonzero(tree)
    if len(ys) == 0:
        return {}
    bx, by = base_xy
    top = ys.min()
    apex_x = float(xs[ys == top].mean())
    fys, fxs = np.nonzero(fol)
    left, right, count = row_profile(fol)
    spans = np.where(left >= 0, right - left + 1, 0)
    row_fill = float(count.sum() / max(1, spans.sum()))
    pads = pad_components(fol, pad_radius)
    crown_base = float((by - fys.max()) / px_per_m) if len(fys) else 0.0
    sizes = np.array([p["area_px"] for p in pads], dtype=float)
    lmass = float(fol[:, : int(round(bx))].sum())
    rmass = float(fol[:, int(round(bx)):].sum())
    return {
        "height_m": round(float((by - top) / px_per_m), 3),
        "crown_w_m": round(float((fxs.max() - fxs.min() + 1) / px_per_m), 3) if len(fxs) else 0.0,
        "crown_x0_m": round(float((fxs.min() - bx) / px_per_m), 3) if len(fxs) else 0.0,
        "crown_x1_m": round(float((fxs.max() - bx) / px_per_m), 3) if len(fxs) else 0.0,
        "crown_base_m": round(crown_base, 3),
        "lean_m": round(float((apex_x - bx) / px_per_m), 3),
        "foliage_centroid_dx_m": round(float((fxs.mean() - bx) / px_per_m), 3) if len(fxs) else 0.0,
        "pads_auto": len(pads),
        "tiers": tiers(fol),
        "row_fill": round(row_fill, 3),
        "pad_size_cv": round(float(sizes.std() / sizes.mean()), 3) if len(sizes) > 1 else 0.0,
        "lr_mass_ratio": round(lmass / max(1.0, rmass), 3),
        "foliage_px": int(fol.sum()), "wood_px": int(wood.sum()),
    }


# ----------------------------------------------------------------------------- comparison

def normalise(mask: np.ndarray, base_xy: Tuple[float, float], out_h: int = 400, out_w: int = 1000,
              base_row: int = 380) -> np.ndarray:
    """Resample a tree mask so its height (base to apex) spans a fixed number of rows, base at a fixed point."""
    ys, xs = np.nonzero(mask)
    bx, by = base_xy
    top = ys.min()
    height = max(1.0, by - top)
    scale = (base_row - 20) / height
    oy, ox = np.mgrid[0:out_h, 0:out_w].astype(np.float32)
    sy = (oy - base_row) / scale + by
    sx = (ox - out_w / 2) / scale + bx
    iy = np.round(sy).astype(int)
    ix = np.round(sx).astype(int)
    ok = (iy >= 0) & (iy < mask.shape[0]) & (ix >= 0) & (ix < mask.shape[1])
    out = np.zeros((out_h, out_w), dtype=bool)
    out[ok] = mask[iy[ok], ix[ok]]
    return out


def iou(a: np.ndarray, a_base: Tuple[float, float], b: np.ndarray, b_base: Tuple[float, float]) -> Dict:
    na = normalise(a, a_base)
    nb = normalise(b, b_base)
    inter = float((na & nb).sum())
    union = float((na | nb).sum())
    la, ra, _ = row_profile(na)
    lb, rb, _ = row_profile(nb)
    both = (la >= 0) & (lb >= 0)
    wa = (ra - la + 1)[both].astype(float)
    wb = (rb - lb + 1)[both].astype(float)
    werr = float(np.mean(np.abs(wa - wb) / np.maximum(wa, 1))) if both.any() else 1.0
    return {"iou": round(inter / max(1.0, union), 3), "width_err": round(werr, 3),
            "xor_px": int((na ^ nb).sum())}


def save_mask_png(path: str, masks_rgb: Dict[str, np.ndarray]) -> None:
    fol = masks_rgb.get("foliage")
    h, w = fol.shape
    img = np.full((h, w, 3), 200, np.uint8)
    img[masks_rgb["wood"]] = (120, 70, 30)
    img[fol] = (30, 120, 30)
    Image.fromarray(img).save(path)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--box", type=int, nargs=4, required=True)
    ap.add_argument("--base", type=float, nargs=2, required=True, help="trunk base x y inside the box")
    ap.add_argument("--pxm", type=float, required=True)
    a = ap.parse_args()
    arr = crop(load_rgb(a.image), a.box)
    m = masks(arr, int(a.base[1]))
    print(json.dumps(metrics(m["foliage"], m["wood"], tuple(a.base), a.pxm), indent=1))
