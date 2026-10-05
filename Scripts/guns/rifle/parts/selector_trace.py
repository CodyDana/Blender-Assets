"""Selector lever: the c1 close-up trace (RECEIVER AND SELECTOR, RIGHT) and its mapping into the lever's own frame.

Plain Python (numpy only), imported by parts/selector.py (inside Blender) and by parts/selector_dev.py (review loop).

The trace was read off 14x gridded zooms of the c1 panel (panel px, pixel-centre coords, +-0.7 px; the zooms are
written by selector_dev.py zoom). c1 draws the lever in a lower position than the side view and the 3/4 view (its
front end swung down ~14 deg, near the 'auto' detent): the side view (LEFT-labelled panel, true right) and the 3/4
view show it up (safe, the rest pose). So c1 gives the lever's SHAPE (outline, flange step, pivot rings, nose
boss) and the side view gives its scale, pose and position: the trace is mapped into frame M by a similarity
(rotation about the pivot + uniform scale) fitted to the side view's traced lever outline (spec feature
face_outline_M), see fit_to_side().

What c1 shows (the authority for the 3D shape):
  * a flat pressed lever: round rear end around the pivot, straight bottom edge tangent to it, upper edge with a
    short step up ~1/3 along, then a long gently falling upper edge to a rounded nose with a small pressed boss and
    a centre pin; the nose part (tab) is bent outward;
  * every free edge carries a double line: a ~1.2 mm wide edge band (the stamped edge chamfer) inside the outline;
  * a straight crease from just behind the step to the front: the upper strip between the crease and the stepped
    upper edge (the 'flange') sits lower than the main plate, so the crease is a lit step wall (a bright line) and
    the flange is a darker band that ends in a rounded end where the tab starts;
  * on the pivot: a raised ring (washer face) and a domed screw head; the side view shows the head slotted.
"""
from __future__ import annotations

import math

import numpy as np

# ------------------------------------------------------------------------------------------ c1 trace (panel px)
C1_PIVOT_PX = (87.5, 111.5)       # centre of the domed head / rings
C1_END_R_PX = 16.8                # round rear end (outer outline)
C1_RING_R_PX = 11.0               # raised washer ring (outer edge; round 2: re-read 14x zoom, 11.0-11.25)
C1_DOME_R_PX = 7.85               # domed head (round 2: 14x zoom, 15.7 px across; c1 shows no slot)
C1_EDGE_BAND_PX = 2.3             # double line: edge band width
C1_NOSE_BOSS_PX = (231.3, 121.9)  # pressed boss on the nose
C1_NOSE_BOSS_R_PX = 4.5
C1_NOSE_PIN_R_PX = 1.4
C1_BEND_PX = ((211.0, 104.0), (209.0, 131.0))     # tab bend line (top, bottom)

# upper edge, rear to front (outer outline)
C1_UPPER_PX = [(92.0, 94.8), (100.0, 95.6), (110.0, 97.4), (120.0, 99.2), (124.0, 99.4), (127.0, 97.8),
               (130.0, 95.2), (133.0, 93.3), (137.0, 92.4), (141.0, 92.6), (150.0, 94.5), (160.0, 96.8),
               (170.0, 99.0), (180.0, 101.3), (190.0, 103.5), (200.0, 105.7), (207.0, 107.1), (210.6, 107.8),
               (211.5, 108.9), (218.0, 110.74), (224.0, 112.4)]
# detail round 2 (second workflow), re-read at 12x (look_q1_tab.png): the tab's top edge starts a step BELOW the
# lever's outer top line at the bend (c1's notch, 211.5, 108.9) and falls straight to a true semicircle round the pin
# (centre 231.3, 121.9, r 7.4: top 114.5, right 238.7, bottom 129.3); the old nose was 1.5-2 px taller at the end
# and pointed at the lower right
# rounded nose, top to bottom
C1_NOSE_C_PX, C1_NOSE_R_PX = (231.3, 121.9), 7.4
C1_NOSE_PX = [(231.3 + 7.4 * math.cos(a), 121.9 + 7.4 * math.sin(a))
              for a in np.radians(np.linspace(-90.0, 90.0, 11))] + [(227.0, 129.35)]
C1_BOTTOM_Y_PX = 128.0            # straight bottom edge (y at the rear end; rises to 130.0 at the nose)
# crease (lower boundary of the flange), straight; its rear end merges into the upper edge band
C1_CREASE_PX = [(112.0, 102.6), (211.0, 117.6)]
C1_FLANGE_END_R_PX = 4.2          # rounded front end of the flange (where the crease meets the upper edge)


# the selector's c1 camera (rifle_detail.py solve, scratch/detail/cameras/selector__c1.json, 2026-10-05): only its
# rotation and scale are used (the trace is anchored on the pivot), embedded so the build does not read scratch
C1_CAM = {"R_rows_right_up_fwd_M": [[0.9951561108387117, 0.09521157334454228, -0.02447593433612815],
                                    [0.012212579420453258, 0.1273112641885002, 0.9917876259132421],
                                    [-0.0975457224293753, 0.9872824308737509, -0.12553180363457106]],
          "px_per_mm": 1.881209855582364, "c0_M": [301.0375, -14.8625, -45.7],
          "c0_px": [111.84915779104993, 176.38452971049608]}
# similarity c1 -> rest pose in frame M (selector_dev.py fit: best IoU 0.817 against the side view's lever outline):
# the c1 lever is drawn 13.25 deg front-down from the rest (safe) pose and 1/0.91 = 1.10x larger than the side view
C1_TO_REST_DEG = 13.25
C1_TO_SIDE_SCALE = 0.91
PLANE_Y = -24.5


def c1_to_rest(uv, pivot_xz=(282.8, -7.8)):
    """c1 panel px -> rest-pose XZ (mm, frame M) of the lever plate."""
    rel = to_lever_xz(C1_CAM, np.atleast_2d(np.asarray(uv, float)), PLANE_Y, pivot_xz)
    return similarity(rel, C1_TO_REST_DEG, C1_TO_SIDE_SCALE, pivot_xz)


def c1_len(px):
    """A c1 px length -> mm in the rest frame."""
    return px / C1_CAM["px_per_mm"] * C1_TO_SIDE_SCALE


def c1_outline_px(n_arc=40) -> np.ndarray:
    """Closed outer outline of the lever in c1 panel px (image coords, y down), CCW on screen."""
    cx, cy = C1_PIVOT_PX
    r = C1_END_R_PX
    up = np.array(C1_UPPER_PX, float)
    nose = np.array(C1_NOSE_PX, float)
    # bottom edge from the nose back to the rear tangent point
    yb0, yb1 = C1_BOTTOM_Y_PX, nose[-1, 1]
    xb = np.linspace(nose[-1, 0], cx, 8)[1:]
    yb = yb0 + (yb1 - yb0) * (xb - cx) / (nose[-1, 0] - cx)
    bottom = np.c_[xb, yb]
    # rear arc from the bottom tangent (straight down) round the back to the first upper point
    a_top = math.atan2(up[0, 1] - cy, up[0, 0] - cx)          # angle of the first upper point (image coords)
    a0 = math.pi / 2                                           # straight down (y down)
    a1 = a_top + 2 * math.pi if a_top < a0 else a_top
    th = np.linspace(a0, a1, n_arc)[1:-1]
    arc = np.c_[cx + r * np.cos(th), cy + r * np.sin(th)]
    P = np.vstack([up, nose, bottom, arc])
    return P


def unproject_ortho(cam_json, uv, plane_y):
    """Panel px -> frame M points on the plane Y = plane_y for an ORTHO close-up camera (gunlib.closeup JSON)."""
    R = np.array(cam_json["R_rows_right_up_fwd_M"], float)
    s = float(cam_json["px_per_mm"])
    c0 = np.array(cam_json["c0_M"], float)
    u0, v0 = cam_json["c0_px"]
    uv = np.asarray(uv, float)
    a = (uv[:, 0] - u0) / s                 # along R[0]
    b = -(uv[:, 1] - v0) / s                # along R[1]
    # P = c0 + a R0 + b R1 + t R2, with P.y = plane_y
    base = c0 + np.outer(a, R[0]) + np.outer(b, R[1])
    t = (plane_y - base[:, 1]) / R[2][1]
    return base + np.outer(t, R[2])


def to_lever_xz(cam_json, uv, plane_y, pivot_M):
    """c1 px -> XZ (mm) relative to the pivot, in c1's drawn pose and c1's (unscaled) size."""
    P = unproject_ortho(cam_json, uv, plane_y)
    Q = unproject_ortho(cam_json, [C1_PIVOT_PX], plane_y)[0]
    return np.c_[P[:, 0] - Q[0], P[:, 2] - Q[2]]


def similarity(P, deg, k, pivot_xz):
    """Rotate (CCW in XZ, i.e. front end up for positive deg) and scale lever-relative points, then place them at
    the pivot."""
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    P = np.asarray(P, float)
    return k * np.c_[c * P[:, 0] - s * P[:, 1], s * P[:, 0] + c * P[:, 1]] + np.asarray(pivot_xz, float)


def poly_mask(P, x0, z0, res, W, H):
    """Rasterise a closed XZ polygon (mm) onto a grid (res mm / px, origin x0, z0; row j = z0 + (j + 0.5) res)."""
    from PIL import Image, ImageDraw
    P = np.asarray(P, float)
    im = Image.new("L", (W, H), 0)
    ImageDraw.Draw(im).polygon([((x - x0) / res, (z - z0) / res) for x, z in P], fill=255)
    return np.asarray(im) > 127


def iou_xz(A, B, res=0.1):
    lo = np.minimum(A.min(0), B.min(0)) - 1.0
    hi = np.maximum(A.max(0), B.max(0)) + 1.0
    W, H = int((hi[0] - lo[0]) / res) + 1, int((hi[1] - lo[1]) / res) + 1
    ma = poly_mask(A, lo[0], lo[1], res, W, H)
    mb = poly_mask(B, lo[0], lo[1], res, W, H)
    return float((ma & mb).sum() / max(1, (ma | mb).sum()))


def fit_to_side(c1_rel, side_xz, pivot_xz, deg0=14.0, k0=0.94):
    """(deg, k, iou): the rotation about the pivot and the uniform scale that best map the c1 lever outline onto the
    side view's traced lever outline (grid search then local refinement)."""
    best = (-1.0, deg0, k0)
    for d in np.arange(deg0 - 8, deg0 + 8.01, 1.0):
        for k in np.arange(k0 - 0.08, k0 + 0.081, 0.02):
            v = iou_xz(similarity(c1_rel, d, k, pivot_xz), side_xz, 0.2)
            if v > best[0]:
                best = (v, d, k)
    _, d0, kk = best
    for d in np.arange(d0 - 1.0, d0 + 1.01, 0.25):
        for k in np.arange(kk - 0.02, kk + 0.021, 0.005):
            v = iou_xz(similarity(c1_rel, d, k, pivot_xz), side_xz, 0.1)
            if v > best[0]:
                best = (v, d, k)
    return float(best[1]), float(best[2]), float(best[0])
