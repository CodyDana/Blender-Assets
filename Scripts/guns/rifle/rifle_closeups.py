"""Cameras for the sheet close-ups c1 (RECEIVER AND SELECTOR, right) and c3 (FRONT SIGHT AND MUZZLE) - plain Python.

The close-ups are perspective views "not to scale" (spec sheet_panels): each camera is solved from landmarks read
off a 3x gridded zoom (scratch/q34/g_c1.png, g_c3.png), then lightly refined on the panel's in-frame silhouette.
The cameras feed rifle_render.py --set crops (our render at the panel's size and framing) and the reference crops
are the panels themselves.

    py -3 -B Scripts/guns/rifle/rifle_closeups.py --npz WorkFiles/guns/rifle/scratch/form_tris.npz
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import SHEET, SCRATCH, REVIEW, WORK  # noqa: E402
from gunlib import compare as C  # noqa: E402
from gunlib import camsolve as CS  # noqa: E402

sys.path.insert(0, str(WORK / "tools"))
import refimg as R  # noqa: E402

PANELS = {
    "c1": {"box": (9, 629, 298, 991), "name": "receiver",
           "yaw_bounds": (3.5, 4.5), "pitch_bounds": (5.5, 6.5), "init_cam": (330.0, -900.0, -10.0), "init_target": (300.0, 0.0, -40.0), "f0": 1700.0,
           "landmarks": [
               ("selector boss centre", (87.0, 111.0), (282.8, -25.9, -7.8)),
               ("rivet (260, -4)", (43.0, 106.0), (260.0, -21.8, -4.0)),
               ("rivet (250, -25)", (30.0, 146.0), (250.0, -21.8, -25.0)),
               ("rivet (313, -25)", (143.0, 141.0), (313.0, -21.8, -25.0)),
               ("trigger tip", (165.0, 200.0), (328.0, -3.0, -57.8)),
               ("guard front-bottom corner", (207.0, 207.0), (350.5, -5.0, -63.5)),
               ("mag catch pin", (226.0, 183.0), (362.0, -5.6, -50.0)),
               ("grip toe", (62.0, 340.0), (262.0, -14.0, -132.5)),
               ("port rear-bottom corner", (150.0, 80.0), (338.0, -20.75, 3.0)),
           ]},
    "c3": {"box": (590, 629, 856, 991), "name": "frontsight",
           "yaw_bounds": (24.5, 25.5), "pitch_bounds": (9.5, 10.5), "init_cam": (1100.0, -650.0, 200.0), "init_target": (830.0, 0.0, 10.0), "f0": 2200.0,
           "landmarks": [
               # framing landmarks only (this stylised close-up draws the brake closer to the block than the side
               # view does): ear top centre, lug bottom centre, brake bottom lip
               ("ear top centre", (140.0, 37.0), (825.6, -10.7, 49.4)),
               ("lug bottom centre", (126.0, 222.0), (821.5, -5.0, -15.8)),
               ("brake bottom lip front", (245.0, 210.0), (880.0, -4.0, -9.0)),
           ]},
}


def panel(box):
    a = np.asarray(Image.open(SHEET).convert("RGB")).astype(float)
    x0, y0, x1, y1 = box
    return a[y0:y1 + 1, x0:x1 + 1]


def mask(P):
    L = P.mean(2)
    S = P.max(2) - P.min(2)
    bg, sd = R.fit_background(L, S)
    F = R.soft_field(L, S, bg, dl=30.0)
    F[:2, :] = F[-2:, :] = 0
    F[:, :2] = F[:, -2:] = 0
    m = F > 0.5
    m = R.drop_small(m, 60)
    return ndi.binary_fill_holes(m)


def rot_ypr(yaw, pitch, roll):
    """Camera rows (right, up, forward) in frame M for a view from the right side (-Y) turned by yaw (about Z,
    + = toward the muzzle side), pitch (+ = looking down) and roll (deg)."""
    import math
    y, p, r = (math.radians(v) for v in (yaw, pitch, roll))
    fwd = np.array([0.0, 1.0, 0.0])
    right = np.array([1.0, 0.0, 0.0])
    up = np.array([0.0, 0.0, 1.0])
    Rz = np.array([[math.cos(y), -math.sin(y), 0], [math.sin(y), math.cos(y), 0], [0, 0, 1]])
    fwd, right, up = Rz @ fwd, Rz @ right, Rz @ up
    def rot(v, k, a):
        k = k / np.linalg.norm(k)
        return v * math.cos(a) + np.cross(k, v) * math.sin(a) + k * (k @ v) * (1 - math.cos(a))
    fwd, up = rot(fwd, right, -p), rot(up, right, -p)
    right, up = rot(right, fwd, r), rot(up, fwd, r)
    return np.vstack([right, up, fwd])


def weak_fit(p2, p3, W, H, ybounds=(-45, 60), pbounds=(-30, 40)):
    """Weak-perspective (orthographic + scale) camera from landmarks: yaw/pitch/roll, scale, image shift."""
    from scipy.optimize import least_squares

    def proj(q, P):
        Rm = rot_ypr(q[0], q[1], q[2])
        X = P @ Rm.T
        return np.c_[q[3] * X[:, 0] + q[4], -q[3] * X[:, 1] + q[5]]

    best = None
    for yaw0 in np.linspace(ybounds[0] + 0.5, ybounds[1] - 0.5, 4):
        for pitch0 in (pbounds[0] + 0.5, 0.5 * (pbounds[0] + pbounds[1])):
            q0 = np.array([yaw0, pitch0, 0.0, 2.0, W / 2, H / 2])
            P0 = p3 - p3.mean(0)
            r = least_squares(lambda q: (proj(q, P0) - p2).ravel(), q0,
                              bounds=([ybounds[0], pbounds[0], -1, 0.3, -5000, -5000], [ybounds[1], pbounds[1], 1, 20, 5000, 5000]))
            if best is None or r.cost < best[0].cost:
                best = (r, p3.mean(0))
    r, c0 = best
    err = np.linalg.norm((lambda q: np.c_[q[3] * ((p3 - c0) @ rot_ypr(*q[:3]).T)[:, 0] + q[4],
                                          -q[3] * ((p3 - c0) @ rot_ypr(*q[:3]).T)[:, 1] + q[5]])(r.x) - p2, axis=1)
    return r.x, c0, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    a = ap.parse_args()
    D = np.load(a.npz)
    V, T = D["V"], D["T"]
    out = {}
    for k, d in PANELS.items():
        P = panel(d["box"])
        ref = mask(P)
        H, W = ref.shape
        p2 = np.array([l[1] for l in d["landmarks"]])
        p3 = np.array([l[2] for l in d["landmarks"]])
        # the close-ups are "not to scale" stylised views: a full pinhole solve runs away to infinity and a free
        # weak-perspective fit turns yaw into anisotropic scale. The view angles are therefore set by eye from the
        # panel (c1: 4 deg toward the muzzle, 6 deg down; c3: 25 deg / 10 deg) and only scale, shift and roll are fitted
        q, c0, err = weak_fit(p2, p3, W, H, d['yaw_bounds'], d['pitch_bounds'])
        Rm = rot_ypr(*q[:3])
        X = (V - c0) @ Rm.T
        P2 = np.c_[q[3] * X[:, 0] + q[4], -q[3] * X[:, 1] + q[5]]
        ou = C.raster_tris(P2, T, ref.shape) > 0.5
        # image centre -> frame M point on the camera's mid plane
        xc = (W / 2.0 - 0.5 - q[4]) / q[3]
        yc = -(H / 2.0 - 0.5 - q[5]) / q[3]
        centre = c0 + xc * Rm[0] + yc * Rm[1]
        cam = {"type": "ORTHO", "R_rows_right_up_fwd_M": Rm.tolist(), "image_centre_point_M": centre.tolist(),
               "px_per_mm": float(q[3]), "ortho_width_mm": float(W / q[3]), "yaw_pitch_roll_deg": [float(v) for v in q[:3]],
               "panel_px": [W, H]}
        (SCRATCH / "q34" / f"camera_{k}.json").write_text(json.dumps(cam, indent=1))
        out[k] = {"model": "weak perspective", "landmark_rms_px": round(float(np.sqrt(np.mean(err ** 2))), 2),
                  "landmark_err_px": {l[0]: round(float(e), 2) for l, e in zip(d["landmarks"], err)},
                  "iou_in_frame": round(C.iou(ou, ref), 4), "yaw_pitch_roll_deg": [round(float(v), 2) for v in q[:3]],
                  "px_per_mm": round(float(q[3]), 3), "panel_px": [W, H]}
        (REVIEW / "early").mkdir(parents=True, exist_ok=True)
        C.overlay(P, ou, ref, REVIEW / "early" / f"{d['name']}_solve_overlay.png", scale=2)
        Image.fromarray(P.astype(np.uint8)).resize((W * 3, H * 3), Image.LANCZOS).save(
            REVIEW / "early" / f"ref_{d['name']}.png")
    (SCRATCH / "closeup_cameras.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
