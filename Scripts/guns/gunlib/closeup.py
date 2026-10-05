"""Close-up panels of a gun reference sheet: masks, edge traces, cameras solved against the model, part crops and
edge comparisons (plain Python: numpy + scipy + Pillow).

Why (AR-01 detail pass, 2026-10-04): small parts derived from the side outlines cannot show their 3D shape, and a
blind judge picked our renders on exactly those parts. Each detailed part is now built from its OWN close-up: the
close-up's camera is solved against the current model, the part's outlines and internal edges are traced in the
close-up, and our render at that camera is compared with the reference crop at identical framing. Close-ups are not
to scale: scale / position come from the spec and the side views; shape, proportions within the part and details come
from the close-up.

Conventions
- Panel pixels: (u, v) = (column, row) at pixel centres, v down; a panel box is (x0, y0, x1, y1) inclusive in sheet px.
- Frame M (mm), the spec's measurement frame. Cameras:
    OrthoCam   rows (right, up, forward) in M, a centre point c0 imaged at (u0, v0), scale s px / mm (weak perspective;
               the close-ups are stylised and a free pinhole runs away on them)
    PerspCam   camsolve.Camera (OpenCV axes: x right, y down, z forward) for panels with strong perspective
  Both give project(P) -> (N, 2) px, depth(P) and view_dirs(P) (unit vectors from the eye toward P).
- Camera JSON (written by to_json, read by gunlib/render_job.py): {"type": "ORTHO" | "PERSP", "panel_px": [W, H], ...}
  ORTHO keeps rifle_render.ortho_from_json's keys (R_rows_right_up_fwd_M, image_centre_point_M, ortho_width_mm);
  PERSP keeps camsolve's (R_rows_cam_axes_in_M, centre_M_mm, f_px, cx, cy).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from scipy.optimize import least_squares, minimize

from . import camsolve as CS
from . import compare as C


# ================================================================================================ reference image
def load_rgb(path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB")).astype(float)


def crop(rgb, box) -> np.ndarray:
    x0, y0, x1, y1 = box
    return rgb[y0:y1 + 1, x0:x1 + 1].copy()


def _poly_terms(H, W, deg):
    yy, xx = np.mgrid[0:H, 0:W]
    xn = xx / max(W - 1, 1) * 2 - 1
    yn = yy / max(H - 1, 1) * 2 - 1
    return np.stack([(xn ** i * yn ** j).ravel() for i in range(deg + 1) for j in range(deg + 1 - i)], 1)


def fit_background(P, deg=3, iters=5, exclude=None):
    """Robust polynomial fit of the neutral studio backdrop. Returns (luminance model, residual sd, backdrop pixel
    mask, per-channel RGB backdrop image)."""
    L, S = P.mean(2), P.max(2) - P.min(2)
    H, W = L.shape
    A = _poly_terms(H, W, deg)
    ok = ((S < 6) & (L > 90)).ravel()
    if exclude is not None:
        ok &= ~exclude.ravel()
    c, sd = None, 0.0
    for _ in range(iters):
        c, *_ = np.linalg.lstsq(A[ok], L.ravel()[ok], rcond=None)
        r = L.ravel() - A @ c
        sd = float(np.std(r[ok]))
        ok = ok & (np.abs(r) < max(2.5 * sd, 4.0))
    rgb = np.zeros_like(P)
    for k in range(3):
        ck, *_ = np.linalg.lstsq(A[ok], P[:, :, k].ravel()[ok], rcond=None)
        rgb[:, :, k] = (A @ ck).reshape(H, W)
    return (A @ c).reshape(H, W), sd, ok.reshape(H, W), rgb


def soft_field(P, bg, dl=30.0, ds=24.0, db=24.0):
    """Foreground strength in [0, 1] (0.5 = edge): luminance drop dl below the backdrop, chroma ds, or a highlight db
    above it. Steel is dark and neutral, wood chromatic, the backdrop neutral grey."""
    L, S = P.mean(2), P.max(2) - P.min(2)
    f = np.maximum(np.maximum((bg - L) / dl, S / ds), (L - bg) / db) * 0.5
    return np.clip(f, 0.0, 1.0)


def drop_small(m, min_obj):
    lab, n = ndi.label(m)
    if not n:
        return m
    sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = np.zeros(n + 1, bool)
    keep[1:] = sizes >= min_obj
    return keep[lab]


def largest_component(m):
    lab, n = ndi.label(m)
    if n == 0:
        return m
    sizes = ndi.sum(m, lab, range(1, n + 1))
    return lab == (1 + int(np.argmax(sizes)))


def ref_mask(P, dl=30.0, min_obj=60, largest=False, border=2, fill=True, db=12.0, ds=20.0):
    """Foreground mask of a close-up panel (the item against the studio backdrop). Lit steel can come within a few
    levels of the backdrop, so highlights count from db = 12 above the fitted backdrop (its residual sd is ~2)."""
    bg, _, _, _ = fit_background(P)
    F = soft_field(P, bg, dl, ds, db)
    if border:
        F[:border, :] = F[-border:, :] = 0
        F[:, :border] = F[:, -border:] = 0
    m = F > 0.5
    m = largest_component(m) if largest else drop_small(m, min_obj)
    return ndi.binary_fill_holes(m) if fill else m


def marching_squares(F, level=0.5):
    """Sub-pixel iso-contours of F at level -> closed rings (N, 2) of (u, v) px; outer rings have positive
    signed_area (computed in u, -v), holes negative. (Same algorithm as the trace tools' refimg.py.)"""
    F = np.pad(F.astype(float), 1, constant_values=level - 1.0)
    H, W = F.shape
    B = F > level

    def interp(p, q):
        (y0, x0), (y1, x1) = p, q
        a, b = F[y0, x0], F[y1, x1]
        t = 0.5 if a == b else (level - a) / (b - a)
        return (x0 + t * (x1 - x0) - 1.0, y0 + t * (y1 - y0) - 1.0)

    nxt, pts = {}, {}
    table = {1: [('B', 'L')], 2: [('R', 'B')], 3: [('R', 'L')], 4: [('T', 'R')], 6: [('T', 'B')], 7: [('T', 'L')],
             8: [('L', 'T')], 9: [('B', 'T')], 11: [('R', 'T')], 12: [('L', 'R')], 13: [('B', 'R')], 14: [('L', 'B')]}
    for i in range(H - 1):
        code = B[i, :-1] * 8 + B[i, 1:] * 4 + B[i + 1, 1:] * 2 + B[i + 1, :-1] * 1
        for j in np.nonzero((code != 0) & (code != 15))[0]:
            c = int(code[j])
            E = {'T': ('h', i, j), 'R': ('v', i, j + 1), 'B': ('h', i + 1, j), 'L': ('v', i, j)}
            ept = {'T': ((i, j), (i, j + 1)), 'R': ((i, j + 1), (i + 1, j + 1)),
                   'B': ((i + 1, j), (i + 1, j + 1)), 'L': ((i, j), (i + 1, j))}
            if c in (5, 10):
                centre = F[i:i + 2, j:j + 2].mean() > level
                if c == 5:
                    segs = [('T', 'R'), ('B', 'L')] if not centre else [('T', 'L'), ('B', 'R')]
                else:
                    segs = [('L', 'T'), ('R', 'B')] if not centre else [('R', 'T'), ('L', 'B')]
            else:
                segs = table[c]
            for a, b in segs:
                nxt[E[a]] = E[b]
                for k in (a, b):
                    if E[k] not in pts:
                        pts[E[k]] = interp(*ept[k])
    polys, seen = [], set()
    for start in list(nxt.keys()):
        if start in seen:
            continue
        ring, e = [], start
        while e not in seen and e in nxt:
            seen.add(e)
            ring.append(pts[e])
            e = nxt[e]
        if len(ring) >= 3:
            polys.append(np.array(ring))
    return polys


def signed_area(P):
    x, y = P[:, 0], -P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def dp_simplify(P, tol):
    """Douglas-Peucker on a closed ring."""
    n = len(P)
    if n < 5:
        return P
    i1 = int(np.argmax(np.hypot(*(P - P[0]).T)))
    keep = np.zeros(n + 1, bool)
    Q = np.vstack([P, P[:1]])
    keep[[0, i1, n]] = True
    stack = [(0, i1), (i1, n)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        A, Bp = Q[a], Q[b]
        ab = Bp - A
        nn = np.hypot(*ab)
        seg = Q[a + 1:b]
        d = np.hypot(*(seg - A).T) if nn == 0 else np.abs(ab[0] * (seg[:, 1] - A[1]) - ab[1] * (seg[:, 0] - A[0])) / nn
        k = int(np.argmax(d))
        if d[k] > tol:
            m = a + 1 + k
            keep[m] = True
            stack += [(a, m), (m, b)]
    return Q[:-1][keep[:-1]]


# ================================================================================================ edges
def canny(L, sigma=1.4, hi_pct=88.0, lo_ratio=0.45, mask=None, min_len=6):
    """Canny edges (scipy only): Gaussian smoothing, Sobel gradient, non-maximum suppression along the quantised
    gradient direction, hysteresis with thresholds taken as percentiles of the gradient inside `mask`, and short
    fragments (< min_len px) dropped. Returns (edges bool, gradient magnitude)."""
    Ls = ndi.gaussian_filter(np.asarray(L, float), sigma)
    gx = ndi.sobel(Ls, axis=1)
    gy = ndi.sobel(Ls, axis=0)
    mag = np.hypot(gx, gy)
    ang = (np.degrees(np.arctan2(gy, gx)) + 180.0) % 180.0
    q = np.zeros_like(ang, int)
    q[(ang >= 22.5) & (ang < 67.5)] = 1
    q[(ang >= 67.5) & (ang < 112.5)] = 2
    q[(ang >= 112.5) & (ang < 157.5)] = 3
    P = np.pad(mag, 1)
    H, W = mag.shape
    c = P[1:-1, 1:-1]
    nb = {0: ((0, 1), (0, -1)), 1: ((1, 1), (-1, -1)), 2: ((1, 0), (-1, 0)), 3: ((1, -1), (-1, 1))}
    nms = np.zeros_like(mag)
    for k, ((dy1, dx1), (dy2, dx2)) in nb.items():
        a = P[1 + dy1:H + 1 + dy1, 1 + dx1:W + 1 + dx1]
        b = P[1 + dy2:H + 1 + dy2, 1 + dx2:W + 1 + dx2]
        sel = (q == k) & (c >= a) & (c >= b)
        nms[sel] = c[sel]
    vals = nms[(nms > 0) & (mask if mask is not None else True)]
    if vals.size == 0:
        return np.zeros_like(mag, bool), mag
    hi = np.percentile(vals, hi_pct)
    lo = lo_ratio * hi
    weak = nms > lo
    lab, n = ndi.label(weak, structure=np.ones((3, 3)))
    if n == 0:
        return np.zeros_like(mag, bool), mag
    strong = np.zeros(n + 1, bool)
    strong[np.unique(lab[nms > hi])] = True
    sizes = ndi.sum(weak, lab, range(n + 1))
    strong &= sizes >= min_len
    strong[0] = False
    e = strong[lab]
    if mask is not None:
        e &= mask
    return e, mag


def edge_metrics(ref_e, our_e, roi=None, tol_px=2.0) -> Dict[str, float]:
    """Edge agreement inside roi: precision (our edges within tol of a reference edge), recall (reference edges within
    tol of ours), F, and the symmetric chamfer distance P50 / P95 (px)."""
    if roi is None:
        roi = np.ones_like(ref_e, bool)
    r, o = ref_e & roi, our_e & roi
    if r.sum() == 0 or o.sum() == 0:
        return {"precision": 0.0, "recall": 0.0, "f": 0.0, "chamfer_p50_px": None, "chamfer_p95_px": None,
                "ref_edge_px": int(r.sum()), "our_edge_px": int(o.sum())}
    dr = ndi.distance_transform_edt(~r)
    do = ndi.distance_transform_edt(~o)
    prec = float((dr[o] <= tol_px).mean())
    rec = float((do[r] <= tol_px).mean())
    f = 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)
    d = np.r_[dr[o], do[r]]
    return {"precision": round(prec, 4), "recall": round(rec, 4), "f": round(f, 4),
            "chamfer_p50_px": round(float(np.percentile(d, 50)), 2), "chamfer_p95_px": round(float(np.percentile(d, 95)), 2),
            "ref_edge_px": int(r.sum()), "our_edge_px": int(o.sum())}


def trace_panel(P, dl=30.0, largest=False, sigma=1.4, hi_pct=88.0, simplify_px=0.35):
    """Close-up trace: foreground mask, outline rings (sub-pixel, simplified) and internal edges (Canny inside the
    mask, the outline band excluded so internal edges are not the silhouette again)."""
    m = ref_mask(P, dl=dl, largest=largest)
    bg, _, _, _ = fit_background(P)
    F = soft_field(P, bg, dl, 20.0, 12.0)
    F = np.where(m, np.maximum(F, 0.51), np.where(ndi.binary_dilation(m, iterations=2), np.minimum(F, 0.49), 0.0))
    rings = [dp_simplify(r, simplify_px) for r in marching_squares(F, 0.5) if abs(signed_area(r)) >= 6.0]
    inner = ndi.binary_erosion(m, iterations=2)
    e, mag = canny(P.mean(2), sigma, hi_pct, mask=inner)
    return {"mask": m, "edges": e, "rings": rings}


def save_trace(P, tr, png, js, scale=3, meta=None):
    """Trace image (panel greyed, outline blue, internal edges orange) + JSON (rings in panel px, edge pixel list)."""
    H, W = tr["mask"].shape
    g = P.mean(2)
    base = np.stack([g, g, g], 2) * 0.5 + 255 * 0.5
    im = Image.fromarray(base.astype(np.uint8)).resize((W * scale, H * scale), Image.LANCZOS)
    A = np.asarray(im).copy()
    e = np.asarray(Image.fromarray(tr["edges"].astype(np.uint8) * 255).resize((W * scale, H * scale), Image.NEAREST)) > 127
    A[e] = (235, 120, 20)
    im = Image.fromarray(A)
    d = ImageDraw.Draw(im)
    for r in tr["rings"]:
        pts = [((x + 0.5) * scale, (y + 0.5) * scale) for x, y in r]
        d.line(pts + pts[:1], fill=(30, 80, 255), width=2)
    im.save(png)
    ys, xs = np.nonzero(tr["edges"])
    out = {"panel_px": [W, H], "rings_px": [np.round(r, 2).tolist() for r in tr["rings"]],
           "ring_signed_area_px": [round(signed_area(r), 1) for r in tr["rings"]],
           "edge_px_uv": np.c_[xs, ys].tolist(), "note": "(u, v) panel pixel centres; outer rings positive area"}
    if meta:
        out.update(meta)
    Path(js).write_text(json.dumps(out))


# ================================================================================================ cameras
def view_R(from_dir, up=(0.0, 0.0, 1.0), roll_deg=0.0):
    """Camera rows (right, up, forward) in M for a camera placed along from_dir (from the target toward the eye)."""
    f = -np.asarray(from_dir, float)
    f /= np.linalg.norm(f)
    r = np.cross(f, up)
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    a = math.radians(roll_deg)
    r, u = r * math.cos(a) + u * math.sin(a), -r * math.sin(a) + u * math.cos(a)
    return np.vstack([r, u, f])


def rot_deg(R0, R1) -> float:
    c = (np.trace(R0 @ R1.T) - 1) / 2
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


class OrthoCam:
    type = "ORTHO"

    def __init__(self, R, c0, s, u0, v0, W, H):
        self.R = np.asarray(R, float)
        self.c0 = np.asarray(c0, float)
        self.s, self.u0, self.v0 = float(s), float(u0), float(v0)
        self.W, self.H = int(W), int(H)

    def project(self, P):
        X = (np.asarray(P, float) - self.c0) @ self.R.T
        return np.c_[self.s * X[:, 0] + self.u0, -self.s * X[:, 1] + self.v0]

    def depth(self, P):
        return (np.asarray(P, float) - self.c0) @ self.R[2]

    def view_dirs(self, P):
        return np.repeat(self.R[2][None, :], len(P), 0)

    def px_per_mm_at(self, P=None):
        return self.s

    def centre_point(self):
        xc = (self.W / 2.0 - 0.5 - self.u0) / self.s
        yc = -(self.H / 2.0 - 0.5 - self.v0) / self.s
        return self.c0 + xc * self.R[0] + yc * self.R[1]

    def to_json(self):
        return {"type": "ORTHO", "R_rows_right_up_fwd_M": self.R.tolist(), "image_centre_point_M": self.centre_point().tolist(),
                "px_per_mm": self.s, "ortho_width_mm": self.W / self.s, "panel_px": [self.W, self.H],
                "c0_M": self.c0.tolist(), "c0_px": [self.u0, self.v0]}

    @staticmethod
    def from_json(d):
        W, H = d["panel_px"]
        R = np.array(d["R_rows_right_up_fwd_M"], float)
        c = np.array(d["image_centre_point_M"], float)
        return OrthoCam(R, c, d["px_per_mm"], W / 2.0 - 0.5, H / 2.0 - 0.5, W, H)


class PerspCam(CS.Camera):
    type = "PERSP"

    def __init__(self, rvec, centre, f, cx, cy, W, H):
        super().__init__(rvec, centre, f, cx, cy)
        self.W, self.H = int(W), int(H)

    def view_dirs(self, P):
        d = np.asarray(P, float) - self.C
        return d / np.linalg.norm(d, axis=1, keepdims=True)

    def px_per_mm_at(self, P):
        return self.f / float(np.mean(self.depth(np.atleast_2d(P))))

    def to_json(self):
        d = self.to_dict()
        d.update({"type": "PERSP", "panel_px": [self.W, self.H]})
        return d

    @staticmethod
    def from_json(d):
        W, H = d["panel_px"]
        return PerspCam(d["rvec"], d["centre_M_mm"], d["f_px"], d["cx"], d["cy"], W, H)


def cam_from_json(d):
    return OrthoCam.from_json(d) if d["type"] == "ORTHO" else PerspCam.from_json(d)


def visible_tris(cam, V, T, margin_px=4.0, cull_back=True):
    """Triangles that can show in the panel: front-facing (closed solids; Blender exports outward winding) and
    overlapping the frame."""
    T = np.asarray(T)
    P2 = cam.project(V)
    W, H = cam.W, cam.H
    tp = P2[T]
    lo, hi = tp.min(1), tp.max(1)
    keep = (hi[:, 0] >= -margin_px) & (lo[:, 0] <= W + margin_px) & (hi[:, 1] >= -margin_px) & (lo[:, 1] <= H + margin_px)
    if isinstance(cam, PerspCam):
        keep &= (cam.depth(V)[T] > 1.0).all(1)
    if cull_back:
        a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        n = np.cross(b - a, c - a)
        ff = np.einsum("ij,ij->i", n, cam.view_dirs((a + b + c) / 3.0)) < 0
        keep &= ff
    return T[keep]


def raster(cam, V, T, ss=2):
    return C.raster_tris(cam.project(V), T, (cam.H, cam.W), ss=ss)


def _soft_iou(cov, tgt, roi=None):
    inter, uni = np.minimum(cov, tgt), np.maximum(cov, tgt)
    if roi is not None:
        inter, uni = inter[roi], uni[roi]
    return float(inter.sum() / max(uni.sum(), 1e-9))


def _ortho_maker(R0, c0, W, H):
    def make(q):
        R = R0 @ CS.rodrigues(q[:3])
        return OrthoCam(R, c0, math.exp(q[3]), q[4], q[5], W, H)
    return make


def _persp_maker(R0cv, W, H):
    """q = rotation delta (3), eye centre (3), log f; principal point at the panel centre."""
    def make(q):
        R = R0cv @ CS.rodrigues(q[:3])
        return PerspCam(CS.mat_to_rvec(R), q[3:6], math.exp(q[6]), W / 2.0 - 0.5, H / 2.0 - 0.5, W, H)
    return make


def solve_camera(cfg, W, H, V=None, T=None, ref=None, roi=None, init=None, iters=400, ss=2, log=None):
    """Solve a close-up camera.

    cfg keys: model "ortho" | "persp"; from_dir, up, roll_deg (the view set by eye: the prior); bound_deg (rotation
    freedom about the prior); landmarks [(label, (u, v), (X, Y, Z)), ...] (optional); dist_mm (persp prior eye
    distance); lam_lm (landmark weight in the silhouette refine, default 1.0).
    Steps: (1) least squares on the landmarks with the rotation tied to the prior; with fewer than 3 landmarks the
    model's projected box is fitted to the reference mask's box instead; (2) Nelder-Mead on the soft IoU between the
    rasterised model (front-facing in-frame triangles of V, T) and the reference mask (inside roi when given), plus
    the landmark residual and the rotation prior. init: a camera to start (2) from (per-part refinement).
    Returns (camera, report)."""
    model = cfg.get("model", "ortho")
    R0 = view_R(cfg["from_dir"], cfg.get("up", (0, 0, 1)), cfg.get("roll_deg", 0.0))
    bound = math.radians(cfg.get("bound_deg", 6.0))
    lms = cfg.get("landmarks", []) or []
    p2 = np.array([l[1] for l in lms], float).reshape(-1, 2)
    p3 = np.array([l[2] for l in lms], float).reshape(-1, 3)
    lam = float(cfg.get("lam_lm", 1.0))
    prior_w = float(cfg.get("prior_w", 8.0))      # px-equivalent weight of one bound_deg of rotation off the prior
    diag = math.hypot(W, H)
    rep = {"model": model}

    if model == "ortho":
        c0 = p3.mean(0) if len(p3) >= 3 else np.asarray(V, float).mean(0)
        make = _ortho_maker(R0, c0, W, H)
        if init is not None:
            q0 = np.r_[CS.mat_to_rvec(R0.T @ init.R), math.log(init.s), init.project(c0[None])[0]]
        elif len(p3) >= 3:
            X = (p3 - c0) @ R0.T
            s0 = np.linalg.norm(p2 - p2.mean(0), axis=1).sum() / max(np.linalg.norm(X[:, :2], axis=1).sum(), 1e-6)

            def res(q):
                cam = make(q)
                return np.r_[(cam.project(p3) - p2).ravel(), q[:3] / bound * prior_w]
            r = least_squares(res, np.r_[0, 0, 0, math.log(s0), p2.mean(0)])
            q0 = r.x
        else:
            q0 = _box_init(make, np.r_[0, 0, 0, 0.0, W / 2, H / 2], V, ref, W, H)
        steps = np.r_[[bound / 3] * 3, 0.03, 3.0, 3.0]
    else:
        dist = float(cfg.get("dist_mm", 1500.0))
        target = p3.mean(0) if len(p3) >= 3 else np.asarray(V, float).mean(0)
        R0cv = np.vstack([R0[0], -R0[1], R0[2]])
        make = _persp_maker(R0cv, W, H)
        if init is not None:
            q0 = np.r_[CS.mat_to_rvec(R0cv.T @ init.R), init.C, math.log(init.f)]
        else:
            eye0 = target - R0[2] * dist
            if len(p3) >= 4:
                Xo = (p3 - target) @ R0.T
                s0 = np.linalg.norm(p2 - p2.mean(0), axis=1).sum() / max(np.linalg.norm(Xo[:, :2], axis=1).sum(), 1e-6)
            else:
                s0 = 2.0
            qa = np.r_[0, 0, 0, eye0, math.log(s0 * dist)]
            if len(p3) >= 4:
                def res(q):
                    cam = make(q)
                    dd = np.linalg.norm(q[3:6] - target)
                    return np.r_[(cam.project(p3) - p2).ravel(), q[:3] / bound * prior_w, prior_w * 2.0 * math.log(dd / dist)]
                qa = least_squares(res, qa).x
            else:
                qa = _box_init(make, qa, V, ref, W, H, persp=True)
            q0 = qa
        steps = np.r_[[bound / 3] * 3, 15.0, 15.0, 15.0, 0.03]

    def lm_rms(cam):
        if not len(p3):
            return 0.0
        return float(np.sqrt(np.mean(np.sum((cam.project(p3) - p2) ** 2, 1))))

    cam = make(q0)
    rep["landmark_rms_px_ls"] = round(lm_rms(cam), 2)
    if V is not None and ref is not None and iters > 0:
        tgt = ref.astype(float)
        Tv = visible_tris(make(q0), V, T, margin_px=0.25 * diag)

        persp = model != "ortho"

        def cost(q):
            c = make(q)
            dev = np.linalg.norm(q[:3]) / bound
            T_ = visible_tris(c, V, Tv) if persp else Tv          # drops triangles behind / at the eye
            cov = C.raster_tris(c.project(V), T_, (H, W), ss=ss)
            return (1.0 - _soft_iou(cov, tgt, roi)) + lam * lm_rms(c) / diag + 0.02 * max(dev - 1.0, 0.0) ** 2

        n = len(q0)
        best = None
        x = q0.copy()
        for scale in (1.0, 0.35):
            sim = np.vstack([x] + [x + np.eye(n)[i] * steps[i] * scale for i in range(n)])
            best = minimize(cost, x, method="Nelder-Mead",
                            options={"maxiter": iters, "xatol": 1e-4, "fatol": 1e-6, "adaptive": True, "initial_simplex": sim})
            x = best.x
        cam = make(x)
        rep["refine_cost"] = round(float(best.fun), 5)
    if V is not None and ref is not None:
        Tv = visible_tris(cam, V, T)
        cov = C.raster_tris(cam.project(V), Tv, (H, W), ss=ss)
        rep["iou_in_frame"] = round(C.iou(cov > 0.5, ref), 4)
        if roi is not None:
            rep["iou_in_roi"] = round(C.iou(cov > 0.5, ref, roi), 4)
    rep["landmark_rms_px"] = round(lm_rms(cam), 2)
    if len(p3):
        err = np.linalg.norm(cam.project(p3) - p2, axis=1)
        rep["landmark_err_px"] = {l[0]: round(float(e), 2) for l, e in zip(lms, err)}
    rep["rotation_from_prior_deg"] = round(rot_deg(R0, cam.R if model == "ortho" else np.vstack([cam.R[0], -cam.R[1], cam.R[2]])), 2)
    if model == "ortho":
        rep["px_per_mm"] = round(cam.s, 4)
    else:
        rep["f_px"] = round(cam.f, 1)
        rep["eye_distance_mm"] = round(float(np.linalg.norm(cam.C - (p3.mean(0) if len(p3) else np.mean(V, 0)))), 1)
    return cam, rep


def _box_init(make, q, V, ref, W, H, persp=False):
    """Scale / shift so the model's projected box matches the reference mask's box (no landmarks)."""
    ys, xs = np.nonzero(ref)
    rb = np.array([xs.min(), ys.min(), xs.max(), ys.max()], float)
    q = np.array(q, float)
    for _ in range(4):
        cam = make(q)
        P2 = cam.project(V)
        mb = np.r_[P2.min(0), P2.max(0)]
        k = max(rb[3] - rb[1], rb[2] - rb[0]) / max(mb[3] - mb[1], mb[2] - mb[0])
        if persp:
            q[6] += math.log(k)
            cam = make(q)
            P2 = cam.project(V)
            mb = np.r_[P2.min(0), P2.max(0)]
            d = 0.5 * (rb[:2] + rb[2:]) - 0.5 * (mb[:2] + mb[2:])
            # move the eye sideways: px -> mm at the model's depth
            ppm = cam.f / float(np.mean(cam.depth(V)))
            Rcv = cam.R
            q[3:6] -= (d[0] * Rcv[0] + d[1] * Rcv[1]) / ppm
        else:
            q[3] += math.log(k)
            cam = make(q)
            P2 = cam.project(V)
            mb = np.r_[P2.min(0), P2.max(0)]
            q[4:6] += 0.5 * (rb[:2] + rb[2:]) - 0.5 * (mb[:2] + mb[2:])
    return q


def part_window(cam, Vp, margin=0.15, min_px=48, square_ish=True) -> Tuple[int, int, int, int]:
    """Panel px window (x0, y0, x1, y1 exclusive) round the projection of a part's vertices, clipped to the panel."""
    P2 = cam.project(Vp)
    W, H = cam.W, cam.H
    inside = (P2[:, 0] > -W) & (P2[:, 0] < 2 * W) & (P2[:, 1] > -H) & (P2[:, 1] < 2 * H)
    P2 = P2[inside] if inside.any() else P2
    lo, hi = P2.min(0), P2.max(0)
    w, h = hi - lo
    pad = margin * max(w, h, 1.0)
    lo, hi = lo - pad, hi + pad
    if square_ish:
        cx, cy = 0.5 * (lo + hi)
        side = max(hi - lo)
        w2 = max(hi[0] - lo[0], 0.6 * side)
        h2 = max(hi[1] - lo[1], 0.6 * side)
        lo, hi = np.array([cx - w2 / 2, cy - h2 / 2]), np.array([cx + w2 / 2, cy + h2 / 2])
    for k, n in ((0, W), (1, H)):
        if hi[k] - lo[k] < min_px:
            c = 0.5 * (hi[k] + lo[k])
            lo[k], hi[k] = c - min_px / 2, c + min_px / 2
    x0, y0 = int(max(math.floor(lo[0]), 0)), int(max(math.floor(lo[1]), 0))
    x1, y1 = int(min(math.ceil(hi[0]), W)), int(min(math.ceil(hi[1]), H))
    return x0, y0, x1, y1


# ================================================================================================ images
def composite_on(bg_rgb, rgba_ss, ss):
    """Our transparent render (H*ss, W*ss, 4) over the panel's fitted backdrop (H, W, 3) -> uint8 RGB at ss res."""
    H, W = bg_rgb.shape[:2]
    bg = np.asarray(Image.fromarray(np.clip(bg_rgb, 0, 255).astype(np.uint8)).resize((W * ss, H * ss), Image.BILINEAR)).astype(float)
    a = rgba_ss[:, :, 3:4].astype(float) / 255.0
    rgb = rgba_ss[:, :, :3].astype(float)
    return np.clip(rgb * a + bg * (1 - a), 0, 255).astype(np.uint8)


def upscale(P, ss):
    H, W = P.shape[:2]
    return np.asarray(Image.fromarray(np.clip(P, 0, 255).astype(np.uint8)).resize((W * ss, H * ss), Image.LANCZOS))


def downscale(A, ss):
    H, W = A.shape[0] // ss, A.shape[1] // ss
    return np.asarray(Image.fromarray(A).resize((W, H), Image.BOX)).astype(float)


def _font(sz):
    for f in ("arial.ttf", "DejaVuSans.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def pair_image(left, right, path, captions=("reference", "ours"), height=640, title=None):
    """Side-by-side at identical framing (both crops are the same panel window) with captions."""
    ims = []
    for a in (left, right):
        im = Image.fromarray(np.asarray(a, np.uint8))
        k = height / im.height
        ims.append(im.resize((max(1, int(round(im.width * k))), height), Image.LANCZOS))
    gap, top = 12, 34 if title else 26
    W = sum(i.width for i in ims) + gap
    out = Image.new("RGB", (W, height + top), (255, 255, 255))
    d = ImageDraw.Draw(out)
    x = 0
    f = _font(16)
    for im, cap in zip(ims, captions):
        out.paste(im, (x, top))
        d.text((x + 4, top - 22), cap, fill=(20, 20, 20), font=f)
        x += im.width + gap
    if title:
        d.text((4, 2), title, fill=(90, 90, 90), font=_font(13))
    out.save(path)


def edge_overlay(ref_rgb, ref_e, our_e, path, sil_ref=None, sil_our=None):
    """Reference crop greyed; reference edges blue, ours red, both (within 1 px) purple; silhouettes as thin lines
    (reference cyan, ours orange) when given."""
    g = np.asarray(ref_rgb, float).mean(2)
    A = (np.stack([g, g, g], 2) * 0.45 + 255 * 0.55).astype(np.uint8)
    rd = ndi.binary_dilation(ref_e, iterations=1)
    od = ndi.binary_dilation(our_e, iterations=1)
    A[ref_e] = (40, 90, 255)
    A[our_e] = (230, 40, 40)
    A[(ref_e & od) | (our_e & rd)] = (170, 40, 200)
    if sil_ref is not None:
        A[C.boundary(sil_ref)] = (0, 190, 210)
    if sil_our is not None:
        A[C.boundary(sil_our)] = (255, 150, 0)
    Image.fromarray(A).save(path)


def grid_zoom(P, path, scale=3, step=10, label_every=50, box_origin=(0, 0)):
    """Gridded zoom of a panel for reading landmark pixels by eye (labels in panel px)."""
    H, W = P.shape[:2]
    im = Image.fromarray(np.clip(P, 0, 255).astype(np.uint8)).resize((W * scale, H * scale), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    f = _font(11)
    for x in range(0, W, step):
        col = (255, 60, 60) if x % label_every == 0 else (255, 255, 255)
        d.line([((x + 0.5) * scale, 0), ((x + 0.5) * scale, H * scale)], fill=col, width=1)
        if x % label_every == 0:
            d.text(((x + 0.5) * scale + 2, 2), str(x), fill=(255, 255, 0), font=f)
    for y in range(0, H, step):
        col = (255, 60, 60) if y % label_every == 0 else (255, 255, 255)
        d.line([(0, (y + 0.5) * scale), (W * scale, (y + 0.5) * scale)], fill=col, width=1)
        if y % label_every == 0:
            d.text((2, (y + 0.5) * scale + 2), str(y), fill=(255, 255, 0), font=f)
    im.save(path)


def solve_overlay(P, cam, V, T, ref, path, landmarks=(), roi_box=None, scale=2):
    """Camera check image: reference outline blue, our silhouette red, landmarks (reference green, ours red)."""
    Tv = visible_tris(cam, V, T)
    ours = C.raster_tris(cam.project(V), Tv, ref.shape, ss=2) > 0.5
    im = C.overlay(P, ours, ref, None, scale=scale).convert("RGB")
    d = ImageDraw.Draw(im)
    for lab, uv, X in landmarks:
        a = (np.asarray(uv) + 0.5) * scale
        b = (cam.project(np.asarray(X, float)[None])[0] + 0.5) * scale
        d.ellipse([a[0] - 4, a[1] - 4, a[0] + 4, a[1] + 4], outline=(0, 200, 0), width=2)
        d.line([tuple(a), tuple(b)], fill=(0, 160, 0), width=1)
        d.ellipse([b[0] - 3, b[1] - 3, b[0] + 3, b[1] + 3], outline=(230, 0, 0), width=2)
    if roi_box is not None:
        x0, y0, x1, y1 = roi_box
        d.rectangle([x0 * scale, y0 * scale, x1 * scale, y1 * scale], outline=(255, 200, 0), width=2)
    im.save(path)
