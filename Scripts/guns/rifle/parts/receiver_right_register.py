"""Detail round 2: re-register this part's private c1 camera on the c1 close-up's own receiver landmarks.

The shared c1 camera was solved on the whole panel (grip, guard, magazine, receiver outline). On the receiver's right
face it leaves the drawn rivets / pin / clip / teardrop ~45 px (3x crop) to the right of ours, which the round-1 judge
read as a design difference ('rivet layout shifted, front-lower rivet at the far left edge'). c1 is not to scale, so
this fits only a uniform scale + a 2D shift (rotation kept) of the ortho camera to the landmarks below, and writes the
result to scratch/detail/receiver_right/cameras/receiver_right__c1.json (the original is kept as *_shared.json).
Positions in the model are NOT changed (side view / spec stay the position authority).

    py -3 -B Scripts/guns/rifle/parts/receiver_right_register.py [--dry] [--no-scale]
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from rifle_common import SCRATCH, REVIEW  # noqa: E402
from gunlib import closeup as CU  # noqa: E402

CAM = SCRATCH / "detail" / "receiver_right" / "cameras" / "receiver_right__c1.json"
SHARED = CAM.with_name("receiver_right__c1_shared.json")
WIN0 = (0, 0)                     # c1 crop window origin (panel px); ref crops are 3x
Y_HEAD = -21.6                    # rivet crown plane (wall -20.75, heads ~1 proud)
# (frame M point, ref_c1.png px at 3x) read off 3x zooms of ref_c1.png (features_c1.json + round-2 reads)
LANDMARKS = [
    ((260.0, Y_HEAD, -4.0), (133, 313)),          # rivet
    ((250.0, Y_HEAD, -25.0), (90, 438)),          # rivet
    ((313.0, Y_HEAD, -25.0), (427, 425)),         # rivet
    ((379.0, Y_HEAD, -21.0), (792, 388)),         # rivet
    ((388.0, -20.75, -8.0), (830, 303)),          # flush pin
    ((350.0, -21.2, -25.0), (612, 410)),          # retainer clip eye
    ((372.5, -20.75, -2.6), (755, 262)),          # teardrop recess centre
]


NO_SCALE = False


def main(dry=False):
    if not SHARED.exists():
        shutil.copy(CAM, SHARED)
    d = json.loads(SHARED.read_text())
    cam = CU.cam_from_json(d["camera"])
    P = np.array([p for p, _ in LANDMARKS], float)
    ref = np.array([q for _, q in LANDMARKS], float) / 3.0 + WIN0
    uv = cam.project(P)
    c = np.array([cam.u0, cam.v0])
    # ref ~ k (uv - c) + c + t   (linear least squares in k, tx, ty)
    A = np.zeros((2 * len(P), 3))
    b = np.zeros(2 * len(P))
    A[0::2, 0], A[0::2, 1], b[0::2] = uv[:, 0] - c[0], 1.0, ref[:, 0] - c[0]
    A[1::2, 0], A[1::2, 2], b[1::2] = uv[:, 1] - c[1], 1.0, ref[:, 1] - c[1]
    (k, tx, ty), *_ = np.linalg.lstsq(A, b, rcond=None)
    if NO_SCALE:                      # shift only: keeps the shared solve's scale (its outline fit) and moves the features
        k = 1.0
        tx, ty = (ref - uv).mean(0)
    new = CU.OrthoCam(cam.R, cam.c0, cam.s * k, cam.u0 + tx, cam.v0 + ty, cam.W, cam.H)
    e0 = np.linalg.norm(uv - ref, axis=1) * 3
    e1 = np.linalg.norm(new.project(P) - ref, axis=1) * 3
    rep = {"k": round(float(k), 4), "shift_panel_px": [round(float(tx), 2), round(float(ty), 2)],
           "landmark_err_3x_px_before": {"mean": round(float(e0.mean()), 1), "max": round(float(e0.max()), 1)},
           "landmark_err_3x_px_after": {"mean": round(float(e1.mean()), 1), "max": round(float(e1.max()), 1)},
           "per_landmark_after": [round(float(x), 1) for x in e1]}
    print(json.dumps(rep, indent=1))
    if not dry:
        d2 = {"panel": "c1", "part": "receiver_right", "camera": new.to_json(),
              "report": {"registered_from": SHARED.name, "method": "uniform scale + shift on c1 receiver landmarks",
                         **rep}}
        CAM.write_text(json.dumps(d2, indent=1))
        (REVIEW / "detail" / "receiver_right" / "c1_registration.json").write_text(json.dumps(d2, indent=1))
    return rep


if __name__ == "__main__":
    NO_SCALE = "--no-scale" in sys.argv
    main("--dry" in sys.argv)
