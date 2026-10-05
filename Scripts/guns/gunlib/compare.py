"""Silhouette comparison against traced sheet panels (plain Python: numpy + scipy + Pillow).

Our geometry arrives as triangles in the gun's frame M (mm, exported by the Blender build as .npz). Each view maps
M to panel pixels exactly as the trace did (side: X along the bore direction u, Z along n; top: X and Y), and the
triangles are rasterised with 4x supersampling into the panel grid, so the comparison has no camera setup error.
Perspective views use a solved pinhole camera (camsolve.py).

Gates: silhouette IoU (identity and after a similarity fit: scale + translation, rotation <= 0.5 deg), contour
distance P95 / max between the two boundaries in panel px, per-part visible-label IoU (painter's order).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.optimize import minimize


# ------------------------------------------------------------------------------------------------ frames
class PanelFrame:
    """Panel px <-> gun mm, the trace's own mapping (trace_reference.Frame)."""

    def __init__(self, s, u, p0, shape):
        self.s = float(s)
        self.u = np.array(u, float) / np.hypot(*u)
        self.n = np.array([self.u[1], -self.u[0]])
        self.p0 = np.array(p0, float)
        self.shape = tuple(shape)          # (H, W)

    def px(self, Q2):
        Q2 = np.asarray(Q2, float)
        return self.p0 + self.s * (Q2[:, :1] * self.u + Q2[:, 1:2] * self.n)

    def mm(self, P):
        d = np.asarray(P, float) - self.p0
        return np.c_[d @ self.u, d @ self.n] / self.s


def signed_area(P):
    x, y = P[:, 0], -P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def rings_mask(rings_px, shape, ss=4):
    outer = [np.asarray(r, float) for r in rings_px if signed_area(np.asarray(r, float)) > 0]
    holes = [np.asarray(r, float) for r in rings_px if signed_area(np.asarray(r, float)) < 0]
    m = poly_cov(outer, shape, ss) > 0.5
    if holes:
        m &= ~(poly_cov(holes, shape, ss) > 0.5)
    return m


def poly_cov(polys, shape, ss=4):
    H, W = shape
    im = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(im)
    for P in polys:
        d.polygon([((x + 0.5) * ss, (y + 0.5) * ss) for x, y in P], fill=255)
    return np.asarray(im.resize((W, H), Image.BOX)).astype(float) / 255.0


def load_trace(trace_dir, view):
    """view in LEFT / RIGHT / TOP. Returns (frame, json). RIGHT has no origin in its json: it is built in its own
    aligned mm frame, so its frame is reconstructed from the ring px/mm pairs (least squares)."""
    j = json.loads((Path(trace_dir) / f"{view}_outline.json").read_text())
    box = j["panel_box_sheet_px"]
    shape = (box[3] - box[1] + 1, box[2] - box[0] + 1)
    if "origin_px" in j:
        fr = PanelFrame(j["px_per_mm"], j["bore_dir_px"], j["origin_px"], shape)
    else:
        P = np.vstack([np.array(r["px"]) for r in j["silhouette"]])
        Q = np.vstack([np.array(r["mm"]) for r in j["silhouette"]])
        # px = p0 + s*(X*u + Z*n), n = (u1, -u0): solve linear in (p0x, p0y, a=s*u0, b=s*u1)
        A = np.zeros((2 * len(P), 4))
        A[0::2] = np.c_[np.ones(len(P)), np.zeros(len(P)), Q[:, 0], Q[:, 1]]
        A[1::2] = np.c_[np.zeros(len(P)), np.ones(len(P)), -Q[:, 1], Q[:, 0]]
        bb = P.reshape(-1)
        x, *_ = np.linalg.lstsq(A, bb, rcond=None)
        s = math.hypot(x[2], x[3])
        fr = PanelFrame(s, (x[2] / s, x[3] / s), (x[0], x[1]), shape)
    return fr, j


def trace_mask(j, key, shape, part=None):
    if part is not None:
        rings = j["parts"][part]
    else:
        rings = j[key]
    return rings_mask([r["px"] for r in rings], shape)


# ------------------------------------------------------------------------------------------------ raster
def raster_tris(P2, T, shape, ss=4, coverage=True):
    """Rasterise triangles given in panel px (pixel-centre coords). Returns coverage in [0, 1] (or the hi-res bool)."""
    H, W = shape
    im = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(im)
    Q = (np.asarray(P2, float) + 0.5) * ss
    for t in T:
        a, b, c = Q[t[0]], Q[t[1]], Q[t[2]]
        d.polygon([(a[0], a[1]), (b[0], b[1]), (c[0], c[1])], fill=255)
    if not coverage:
        return np.asarray(im) > 127
    return np.asarray(im.resize((W, H), Image.BOX)).astype(float) / 255.0


def raster_labels(P2, T, depth, labels, shape, ss=4, nlab=None):
    """Painter's-order label map (far to near by triangle mean depth; larger depth = farther). Returns per-label
    coverage fractions (L, H, W)."""
    H, W = shape
    nlab = int(labels.max()) + 1 if nlab is None else nlab
    im = Image.new("I", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(im)
    Q = (np.asarray(P2, float) + 0.5) * ss
    td = depth[T].mean(axis=1)
    order = np.argsort(-td)
    for i in order:
        t = T[i]
        a, b, c = Q[t[0]], Q[t[1]], Q[t[2]]
        d.polygon([(a[0], a[1]), (b[0], b[1]), (c[0], c[1])], fill=int(labels[i]) + 1)
    L = np.asarray(im, np.int32)
    out = np.zeros((nlab, H, W))
    for k in range(nlab):
        m = (L == k + 1).astype(float)
        out[k] = m.reshape(H, ss, W, ss).mean(axis=(1, 3))
    return out


def side_px(fr: PanelFrame, V):
    return fr.px(np.c_[V[:, 0], V[:, 2]])


def top_px(fr: PanelFrame, V):
    return fr.px(np.c_[V[:, 0], V[:, 1]])


# ------------------------------------------------------------------------------------------------ metrics
def iou(a, b, valid=None):
    if valid is not None:
        a = a & valid
        b = b & valid
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 1.0


def boundary(m):
    return m & ~ndi.binary_erosion(m)


def contour_distance(a, b, valid=None):
    """Symmetric boundary distances (px) between masks a and b: returns dict with p50/p95/max."""
    ba, bb = boundary(a), boundary(b)
    if valid is not None:
        ba &= valid
        bb &= valid
    if not ba.any() or not bb.any():
        return {"p50": None, "p95": None, "max": None, "n": 0}
    da = ndi.distance_transform_edt(~bb)[ba]
    db = ndi.distance_transform_edt(~ba)[bb]
    d = np.r_[da, db]
    return {"p50": float(np.percentile(d, 50)), "p95": float(np.percentile(d, 95)), "max": float(d.max()),
            "n": int(len(d))}


def similarity_fit(project, target, valid=None, max_rot_deg=0.5, max_scale=0.03, max_shift=6.0):
    """Fit (scale, rotation, tx, ty) about the panel centre applied to our projected px to maximise IoU with target.
    ``project()`` returns (P2, T). Returns (params, iou_fit, coverage_fit)."""
    P2, T = project()
    H, W = target.shape
    c = np.array([W / 2.0, H / 2.0])
    tgt = target.astype(float)

    def apply(p):
        s, r, tx, ty = 1 + p[0], math.radians(p[1]), p[2], p[3]
        R = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
        return (P2 - c) @ R.T * s + c + np.array([tx, ty])

    def cost(p):
        if abs(p[1]) > max_rot_deg or abs(p[0]) > max_scale or abs(p[2]) > max_shift or abs(p[3]) > max_shift:
            return 1.0
        cov = raster_tris(apply(p), T, target.shape, ss=2)
        inter = np.minimum(cov, tgt)
        uni = np.maximum(cov, tgt)
        if valid is not None:
            inter, uni = inter[valid], uni[valid]
        return 1.0 - float(inter.sum() / max(uni.sum(), 1e-9))

    best = minimize(cost, np.zeros(4), method="Nelder-Mead",
                    options={"xatol": 1e-4, "fatol": 1e-5, "maxiter": 160, "initial_simplex":
                             np.array([[0, 0, 0, 0], [0.004, 0, 0, 0], [0, 0.2, 0, 0], [0, 0, 0.6, 0], [0, 0, 0, 0.6]])})
    m0 = raster_tris(P2, T, target.shape, ss=4) > 0.5
    i0 = iou(m0, target, valid)
    m = raster_tris(apply(best.x), T, target.shape, ss=4) > 0.5
    i1 = iou(m, target, valid)
    if i0 >= i1:
        return [0.0, 0.0, 0.0, 0.0], i0, m0
    return [float(v) for v in best.x], i1, m


# ------------------------------------------------------------------------------------------------ images
def overlay(panel_rgb, ours, ref, path, scale=3, extra=None):
    """Sheet panel (greyed) with the reference boundary in blue and ours in red; purple where both coincide."""
    g = np.asarray(panel_rgb, float).mean(axis=2)
    base = np.stack([g, g, g], 2) * 0.55 + 255 * 0.45
    im = Image.fromarray(base.astype(np.uint8)).resize((ours.shape[1] * scale, ours.shape[0] * scale), Image.LANCZOS)
    A = np.asarray(im).copy()
    up = lambda m: np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((m.shape[1] * scale, m.shape[0] * scale), Image.BILINEAR)) > 127
    bo = boundary(ndi.binary_dilation(up(ours), iterations=0) if False else up(ours))
    br = boundary(up(ref))
    bo = ndi.binary_dilation(bo, iterations=1)
    br = ndi.binary_dilation(br, iterations=1)
    A[br] = (40, 90, 255)
    A[bo] = (235, 40, 40)
    A[bo & br] = (170, 40, 200)
    if extra is not None:
        for m, col in extra:
            mm = ndi.binary_dilation(boundary(up(m)), iterations=1)
            A[mm] = col
    if path is None:
        return Image.fromarray(A)
    Image.fromarray(A).save(path)


def diff_image(ours, ref, path, scale=3, valid=None):
    """White = both, red = ours only, blue = reference only, black = neither (grey = excluded zone)."""
    H, W = ours.shape
    A = np.zeros((H, W, 3), np.uint8)
    A[ours & ref] = (235, 235, 235)
    A[ours & ~ref] = (230, 50, 50)
    A[~ours & ref] = (50, 110, 255)
    if valid is not None:
        A[~valid] = (A[~valid] * 0.4 + 60).astype(np.uint8)
    Image.fromarray(A).resize((W * scale, H * scale), Image.NEAREST).save(path)


# ------------------------------------------------------------------------------------------------ residual regions
def residual_regions(ours, ref, min_dist=3.0, min_core_px=2):
    """Connected residual regions (8-connected) between two silhouettes whose far part lies more than ``min_dist`` px
    outside the other mask. kind 'ours_only' = our silhouette sticks out, 'ref_only' = the reference does.
    Returns dicts with the region mask, its size, the core size beyond min_dist, the max distance and the bbox."""
    d_out_ref = ndi.distance_transform_edt(~ref)
    d_out_ours = ndi.distance_transform_edt(~ours)
    out = []
    for kind, res, dist in (("ours_only", ours & ~ref, d_out_ref), ("ref_only", ref & ~ours, d_out_ours)):
        lab, n = ndi.label(res, structure=np.ones((3, 3), bool))
        for k in range(1, n + 1):
            m = lab == k
            core = m & (dist > min_dist)
            if core.sum() < min_core_px:
                continue
            ys, xs = np.nonzero(m)
            out.append({"kind": kind, "mask": m, "px": int(m.sum()), "core_px": int(core.sum()),
                        "max_dist_px": round(float(dist[m].max()), 2),
                        "p95_dist_px": round(float(np.percentile(dist[m], 95)), 2),
                        "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]})
    out.sort(key=lambda r: -r["core_px"])
    return out


def best_local_shift(ours, ref, window, max_shift=8):
    """Integer shift of our mask (inside a window x0, y0, x1, y1) that maximises the window IoU. Returns
    (dx, dy, iou_before, iou_after, p95_before, p95_after)."""
    x0, y0, x1, y1 = window
    o = ours[y0:y1, x0:x1]
    r = ref[y0:y1, x0:x1]
    i0 = iou(o, r)
    best = (0, 0, i0)
    for dy in range(-max_shift, max_shift + 1):
        for dx in range(-max_shift, max_shift + 1):
            s = np.roll(np.roll(ours, dy, 0), dx, 1)[y0:y1, x0:x1]
            v = iou(s, r)
            if v > best[2] + 1e-9:
                best = (dx, dy, v)
    s = np.roll(np.roll(ours, best[1], 0), best[0], 1)[y0:y1, x0:x1]
    c0, c1 = contour_distance(o, r), contour_distance(s, r)
    return best[0], best[1], i0, best[2], c0["p95"], c1["p95"]
