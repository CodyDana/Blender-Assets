"""3/4 FRONT (LEFT) panel: reference mask, camera solve, silhouette gate L2 3/4, magazine-thickness check (plain Python).

    py -3 -B Scripts/guns/smg/smg_q34.py --npz <tris.npz> --stage blockout|form [--solve]

--solve   (re)solve the camera: landmarks -> least squares -> silhouette refinement on the gun WITHOUT the magazine
          zone (so the magazine check is independent of the solve); saved to scratch/q34/camera_<stage>.json and reused
          by the 3/4 render (smg_render.py).
Gate (spec L2): camera-solved IoU >= 0.93 and contour P95 <= 3 px on the outer silhouettes (both hole-filled: the
reference mask is hole-filled). Magazine thickness (Q8 / R14 / R26, at blockout): the magazine's visible silhouette
for thickness t in 21..33 (Y scaled about the mid-plane), IoU in the magazine zone, against the spec's 27.0.
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
from smg_common import SHEET, SCRATCH, REVIEW, WORK, D as SPECD, dims  # noqa: E402
from gunlib import compare as C  # noqa: E402
from gunlib import camsolve as CS  # noqa: E402

sys.path.insert(0, str(WORK / "tools"))
import refimg as R  # noqa: E402

BOX = tuple(json.loads((WORK / "smg_measured.json").read_text())["panels_sheet_px_x0_y0_x1_y1_inclusive"]["Q34_FRONT_LEFT"])
QDIR = SCRATCH / "q34"
QDIR.mkdir(parents=True, exist_ok=True)
MAG_T = float(dims("magazine_body")["thickness"])
_f = SPECD["frames"]["mag"]
_o, _x, _z = (np.array(_f[k], float) for k in ("Mag_in_M", "x_axis_in_M", "z_axis_in_M"))
_md = dims("magazine_body")


def _mag(xl, yl, zl):
    return tuple(np.round(_o + xl * _x + zl * _z + np.array([0, yl, 0]), 2))


# panel px <-> frame M (mm), read off a 2x gridded crop (scratch/w1b q34_grid); +-2 px (the silhouette refine follows)
LANDMARKS = [
    ("muzzle device front face centre", (36.5, 201.0), (625.0, 0.0, 1.69)),
    ("rear sight frame top centre", (350.0, 71.0), (299.4, 0.0, 76.4)),
    ("front sight ear tops centre", (140.0, 86.0), (542.2, 0.0, 76.0)),
    ("butt pad top rear corner (near, left)", (598.0, 129.0), (0.0, 26.25, 23.3)),
    ("butt pad bottom rear corner (near)", (592.0, 260.0), (0.0, 26.25, -79.3)),
    ("grip bottom toe (near)", (340.0, 367.0), (308.6, 16.0, -152.0)),
    ("mag floor plate front corner (near)", (174.0, 495.0), _mag(_md["foreaft"] / 2, MAG_T / 2 + 1.0, _md["floor_along_axis"])),
    ("mag floor plate rear corner (near)", (232.0, 500.0), _mag(-_md["foreaft"] / 2, MAG_T / 2 + 1.0, _md["floor_along_axis"])),
    ("lower rail front bottom (near)", (116.0, 247.0), (553.6, 10.6, -37.2)),
    ("charging knob centre", (220.0, 160.0), tuple(dims("charging_handle")["knob_centre_XZ"][:1] +
                                                   [dims("charging_handle")["knob_centre_Y"]] +
                                                   dims("charging_handle")["knob_centre_XZ"][1:])),
]
MAG_ZONE = [(168, 285), (262, 285), (262, 505), (168, 505)]       # panel px polygon holding the visible magazine


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
    zone[480:, 150:270] = True
    F[zone] = Fs[zone]
    F[:3, :] = F[-3:, :] = 0
    F[:, :3] = F[:, -3:] = 0
    m = R.largest_component(F > 0.5)
    m = ndi.binary_fill_holes(m)
    return m, P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    ap.add_argument("--stage", default="blockout")
    ap.add_argument("--solve", action="store_true")
    a = ap.parse_args()
    Dz = np.load(a.npz)
    V, T, lab, names = Dz["V"], Dz["T"], Dz["lab"], [str(n) for n in Dz["names"]]
    ref, P = ref_mask()
    H, W = ref.shape
    magzone = C.poly_cov([np.array(MAG_ZONE, float)], ref.shape) > 0
    magk = [i for i, n in enumerate(names) if n.startswith("magazine")]
    selm = np.isin(lab, magk)
    camf = QDIR / f"camera_{a.stage}.json"
    out = {"stage": a.stage, "panel_box_sheet_px": list(BOX)}
    if a.solve or not camf.exists():
        p2 = np.array([l[1] for l in LANDMARKS])
        p3 = np.array([l[2] for l in LANDMARKS])
        cam0, err = CS.solve_landmarks(p2, p3, W / 2, H / 2, init_cam=(1000.0, 900.0, 350.0),
                                       init_target=(380.0, 0.0, -30.0), f0=1500.0)
        out["landmark_rms_px"] = float(np.sqrt(np.mean(err ** 2)))
        out["landmark_err_px"] = {l[0]: round(float(e), 2) for l, e in zip(LANDMARKS, err)}
        cam, siou = CS.refine_silhouette(cam0, V, T[~selm], ref, valid=~magzone)
        out["refine_soft_iou_no_mag"] = siou
        d = cam.to_dict()
        d["landmark_rms_px"] = out["landmark_rms_px"]
        camf.write_text(json.dumps(d, indent=1))
    cd = json.loads(camf.read_text())
    out.setdefault("landmark_rms_px", cd.get("landmark_rms_px"))
    cam = CS.Camera(cd["rvec"], cd["centre_M_mm"], cd["f_px"], cd["cx"], cd["cy"])
    out["camera"] = {"centre_M_mm": [round(v, 1) for v in cam.C], "f_px": round(cam.f, 1),
                     "forward_M": [round(v, 4) for v in cam.R[2]],
                     "hfov_deg": round(float(2 * np.degrees(np.arctan(W / 2 / cam.f))), 2)}
    ours_raw = C.raster_tris(cam.project(V), T, ref.shape) > 0.5
    ours = ndi.binary_fill_holes(ours_raw)
    out["iou_raw_unfilled"] = round(C.iou(ours_raw, ref), 4)
    out["iou"] = round(C.iou(ours, ref), 4)
    out["contour_px"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in C.contour_distance(ours, ref).items()}
    out["iou_without_mag_zone"] = round(C.iou(ours, ref, ~magzone), 4)
    tag = a.stage
    (REVIEW / tag).mkdir(parents=True, exist_ok=True)
    C.overlay(P, ours, ref, REVIEW / tag / "q34_overlay.png")
    C.diff_image(ours, ref, REVIEW / tag / "q34_diff.png")
    # magazine thickness sweep (the 3/4 view is the thickness's only witness)
    sweep = {}
    rest = C.raster_tris(cam.project(V), T[~selm], ref.shape) > 0.5
    Vm = V.copy()
    idx = np.unique(T[selm].ravel())
    for t in (21, 23, 25, 27, 29, 31, 33):
        Vm[:, 1] = V[:, 1]
        Vm[idx, 1] = V[idx, 1] * (t / MAG_T)
        om = C.raster_tris(cam.project(Vm), T[selm], ref.shape) > 0.5
        sweep[t] = round(C.iou(ndi.binary_fill_holes(om | rest), ref, magzone), 4)
    best_t = max(sweep, key=sweep.get)
    ts = sorted(sweep)
    k = ts.index(best_t)
    t_star = float(best_t)
    if 0 < k < len(ts) - 1:
        x = np.array(ts[k - 1:k + 2], float)
        y = np.array([sweep[v] for v in ts[k - 1:k + 2]])
        c2, c1, c0 = np.polyfit(x, y, 2)
        if c2 < 0:
            t_star = float(-c1 / (2 * c2))
    out["magazine_thickness_check"] = {"iou_in_mag_zone_by_thickness_mm": sweep, "best_mm": best_t,
                                       "parabola_peak_mm": round(t_star, 2), "spec_mm": MAG_T,
                                       "band_mm": [27.0, 31.0],
                                       "verdict": "%.1f kept (the panel peaks at %.1f; real minimum 27)" % (MAG_T, t_star)}
    out["gate"] = {"rule": "L2 3/4: IoU >= 0.93 and contour P95 <= 3 px (outer silhouettes, camera solved)",
                   "pass": bool(out["iou"] >= 0.93 and out["contour_px"]["p95"] is not None and
                                out["contour_px"]["p95"] <= 3.0)}
    print(json.dumps(out, indent=1, default=str))
    (REVIEW / tag / "q34_result.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
