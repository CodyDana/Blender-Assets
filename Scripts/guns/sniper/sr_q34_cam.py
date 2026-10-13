"""SR01 W4: the sheet's 3/4 FRONT RIGHT panel camera, solved on the silhouette (plain Python; gunlib.camsolve), for the
blind pairs and the 3/4 set render. Started from the W2 tex_q34 look (eye M (1180, -820, 300) -> (560, 0, -20), 30 deg)
and refined (Nelder-Mead on the soft IoU: rotation, centre, focal, principal point) against trace/Q34_silhouette.png
with the form-stage gun + the mounted scope (bipod folded, as drawn). The floor's contact shadows sit partly inside the
traced mask (trace note), so a band under the lowest gun pixels is left out of the IoU.

    py -3 -B Scripts/guns/sniper/sr_q34_cam.py

Writes scratch/w4/q34_camera.json (camsolve dict + panel_px + the IoU).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import WORK  # noqa: E402
from gunlib import camsolve as CS  # noqa: E402
from gunlib import compare as C  # noqa: E402

S1 = WORK / "scratch" / "w1"
OUT = WORK / "scratch" / "w4" / "q34_camera.json"


def model():
    Vs, Ts, off = [], [], 0
    for f in ("form_tris", "scope_tris"):
        d = np.load(S1 / f"{f}.npz", allow_pickle=True)
        Vs.append(d["V"])
        Ts.append(d["T"] + off)
        off += len(d["V"])
    return np.vstack(Vs), np.vstack(Ts)


def main():
    ref = (np.array(Image.open(WORK / "trace" / "Q34_silhouette.png")) > 127).astype(float)
    H, W = ref.shape
    V, T = model()
    eye, tgt, fov = np.array([1180.0, -820.0, 300.0]), np.array([560.0, 0.0, -20.0]), 30.0
    f0 = (W / 2.0) / math.tan(math.radians(fov / 2.0))
    cam0 = CS.Camera(CS.mat_to_rvec(CS.look_at(eye, tgt)), eye, f0, W / 2.0 - 0.5, H / 2.0 - 0.5)
    iou0 = 1.0 - float(np.minimum(C.raster_tris(cam0.project(V), T, ref.shape, ss=2), ref).sum() /
                       np.maximum(C.raster_tris(cam0.project(V), T, ref.shape, ss=2), ref).sum())
    best, biou = None, -1.0
    for scale in (1.0, 0.85, 1.2):                  # a few distances along the start ray (focal follows)
        e = tgt + (eye - tgt) * scale
        c0 = CS.Camera(CS.mat_to_rvec(CS.look_at(e, tgt)), e, f0 * scale, W / 2.0 - 0.5, H / 2.0 - 0.5)
        cam, iou = CS.refine_silhouette(c0, V, T, ref, iters=900, ss=2)
        print("[q34] start scale", scale, "IoU", round(iou, 4))
        if iou > biou:
            best, biou = cam, iou
    d = best.to_dict()
    d.update({"type": "PERSP", "panel_px": [W, H], "iou_silhouette": round(biou, 4), "iou_start": round(1 - iou0, 4),
              "note": "solved on trace/Q34_silhouette.png (gun + scope, bipod folded) from the W2 tex_q34 look"})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(d, indent=1))
    print("[q34] DONE IoU", round(biou, 4), "centre", [round(v, 1) for v in d["centre_M_mm"]], "f", round(d["f_px"], 1))


if __name__ == "__main__":
    main()
