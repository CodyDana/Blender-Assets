"""3/4 FRONT RIGHT panel: reference mask, camera solve, silhouette gate, magazine-thickness check (plain Python).

    py -3 -B Scripts/guns/rifle/rifle_q34.py --npz <tris.npz> --stage blockout|form [--solve]

--solve   (re)solve the camera: landmarks -> least squares -> silhouette refinement on the rifle WITHOUT the
          magazine region (so the magazine check that follows is independent of the solve); saved to
          scratch/q34/camera.json and reused by later stages and the Blender 3/4 render.
Magazine thickness: with the solved camera, the magazine's visible silhouette is compared (IoU in the magazine zone)
for thickness t in 18..34 mm (Y scaled about the mid-plane); the best t is reported against the spec's 28.0.
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
from rifle_common import ROOT, SHEET, SCRATCH, REVIEW, WORK  # noqa: E402
from gunlib import compare as C  # noqa: E402
from gunlib import camsolve as CS  # noqa: E402

sys.path.insert(0, str(WORK / "tools"))
import refimg as R  # noqa: E402

BOX = (771, 322, 1528, 600)
QDIR = SCRATCH / "q34"
QDIR.mkdir(parents=True, exist_ok=True)

# panel px  <->  frame M (mm). Read off 4x gridded zooms (scratch/q34/g_left.png, g_right.png); +-1.5 px.
LANDMARKS = [
    ("butt top rear corner (near side)", (40.0, 48.0), (2.0, -18.0, -1.0)),
    ("butt bottom rear corner (near side)", (45.0, 137.0), (12.0, -18.0, -108.0)),
    ("grip toe (lowest point)", (190.0, 183.0), (263.5, -12.0, -132.5)),
    ("mag floor plate front corner", (353.0, 221.0), (493.1, -14.0, -138.9)),
    ("mag floor plate rear corner", (312.0, 263.0), (456.2, -14.0, -183.9)),
    ("rear sight notch plate top", (310.0, 23.0), (450.0, 0.0, 48.0)),
    ("front sight near ear top centre", (645.0, 43.0), (825.3, -10.7, 49.4)),
    ("brake bottom lip front", (720.0, 136.0), (880.0, -3.0, -9.0)),
    ("trigger guard bottom", (213.0, 129.0), (312.0, -5.0, -68.0)),
]
MAG_ZONE = [(238, 96), (372, 96), (372, 275), (238, 275)]          # px polygon holding the magazine


def panel():
    a = np.asarray(Image.open(SHEET).convert("RGB")).astype(float)
    return a[BOX[1]:BOX[3] + 1, BOX[0]:BOX[2] + 1]


def ref_mask():
    P = panel()
    L = P.mean(2)
    S = P.max(2) - P.min(2)
    bg, sd = R.fit_background(L, S)
    F = R.soft_field(L, S, bg, dl=30.0)
    # the floor contact shadow under the magazine: demand a much darker pixel there
    Fs = R.soft_field(L, S, bg, dl=75.0)
    zone = np.zeros_like(F, bool)
    zone[248:, 260:370] = True
    F[zone] = Fs[zone]
    F[:3, :] = F[-3:, :] = 0
    F[:, :3] = F[:, -3:] = 0
    m = R.largest_component(F > 0.5)
    m = ndi.binary_fill_holes(m)
    return m, P


def project_np(cam, V):
    return cam.project(V)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    ap.add_argument("--stage", default="blockout")
    ap.add_argument("--solve", action="store_true")
    a = ap.parse_args()
    D = np.load(a.npz)
    V, T, lab, names = D["V"], D["T"], D["lab"], [str(n) for n in D["names"]]
    ref, P = ref_mask()
    H, W = ref.shape
    magzone = C.poly_cov([np.array(MAG_ZONE, float)], ref.shape) > 0
    magk = [i for i, n in enumerate(names) if n.startswith("magazine")]
    selm = np.isin(lab, magk)
    camf = QDIR / ("camera_blockout.json" if a.stage == "blockout" else "camera.json")
    out = {"stage": a.stage}
    if a.solve or not camf.exists():
        p2 = np.array([l[1] for l in LANDMARKS])
        p3 = np.array([l[2] for l in LANDMARKS])
        cam0, err = CS.solve_landmarks(p2, p3, W / 2, H / 2, init_cam=(1400.0, -1500.0, 450.0),
                                       init_target=(440.0, 0.0, -30.0), f0=2000.0)
        out["landmark_rms_px"] = float(np.sqrt(np.mean(err ** 2)))
        out["landmark_err_px"] = {l[0]: round(float(e), 2) for l, e in zip(LANDMARKS, err)}
        valid = ~magzone
        cam, siou = CS.refine_silhouette(cam0, V, T[~selm], ref, valid=valid)
        out["refine_soft_iou_no_mag"] = siou
        camf.write_text(json.dumps(cam.to_dict(), indent=1))
    cd = json.loads(camf.read_text())
    cam = CS.Camera(cd["rvec"], cd["centre_M_mm"], cd["f_px"], cd["cx"], cd["cy"])
    out["camera"] = {"centre_M_mm": [round(v, 1) for v in cam.C], "f_px": round(cam.f, 1),
                     "distance_to_centre_mm": round(float(np.linalg.norm(cam.C - np.array([440, 0, -30]))), 1),
                     "forward_M": [round(v, 4) for v in cam.R[2]]}
    hfov = 2 * np.degrees(np.arctan(W / 2 / cam.f))
    out["camera"]["hfov_deg"] = round(float(hfov), 2)
    # ---- whole silhouette gate (L2 3/4)
    ours = C.raster_tris(cam.project(V), T, ref.shape) > 0.5
    out["iou"] = round(C.iou(ours, ref), 4)
    out["contour_px"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in C.contour_distance(ours, ref).items()}
    nm = ~magzone
    out["iou_without_mag_zone"] = round(C.iou(ours, ref, nm), 4)
    tag = a.stage
    (REVIEW / tag).mkdir(parents=True, exist_ok=True)
    C.overlay(P, ours, ref, REVIEW / tag / "q34_overlay.png")
    C.diff_image(ours, ref, REVIEW / tag / "q34_diff.png")
    # ---- magazine thickness sweep
    sweep = {}
    rest = C.raster_tris(cam.project(V), T[~selm], ref.shape) > 0.5
    Vm = V.copy()
    for t in (18, 20, 22, 24, 26, 28, 30, 32, 34):
        Vm[:, 1] = V[:, 1]
        idx = np.unique(T[selm].ravel())
        Vm[idx, 1] = V[idx, 1] * (t / 28.0)
        om = C.raster_tris(cam.project(Vm), T[selm], ref.shape) > 0.5
        both = om | rest
        sweep[t] = round(C.iou(both, ref, magzone), 4)
    best_t = max(sweep, key=sweep.get)
    # parabola through the best and its neighbours
    ts = sorted(sweep)
    k = ts.index(best_t)
    if 0 < k < len(ts) - 1:
        x = np.array(ts[k - 1:k + 2], float)
        y = np.array([sweep[v] for v in ts[k - 1:k + 2]])
        c2, c1, c0 = np.polyfit(x, y, 2)
        t_star = float(-c1 / (2 * c2)) if c2 < 0 else float(best_t)
    else:
        t_star = float(best_t)
    out["magazine_thickness_check"] = {"iou_in_mag_zone_by_thickness_mm": sweep, "best_mm": best_t,
                                       "parabola_peak_mm": round(t_star, 2), "spec_mm": 28.0,
                                       "verdict": "28.0 kept" if abs(t_star - 28.0) <= 3.0 else
                                       "28.0 questioned (peak %.1f)" % t_star}
    print(json.dumps(out, indent=1))
    (REVIEW / tag / "q34_result.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
