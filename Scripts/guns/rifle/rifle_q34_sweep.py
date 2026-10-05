"""Section sweeps against the camera-solved 3/4 FRONT RIGHT panel (plain Python; form fix round 1).

    py -3 -B Scripts/guns/rifle/rifle_q34_sweep.py --npz WorkFiles/guns/rifle/scratch/form_tris.npz

The side outline of the grip and the stock is fixed by the trace (LEFT-labelled panel); their SECTIONS are not seen
there. This replaces the part in the built model by plain-numpy variants (same generators as the build) and scores
the 3/4 silhouette in a zone round the part (outer silhouettes, holes filled, solved camera scratch/q34/camera.json):
  grip   width W 26..32 x strap radius R 6..14 (rifle_parts2.grip_mesh_numpy) + the section girth at the Grip depth
  stock  section edge radius R 5..15 (rifle_parts2.STOCK_R, wrist kept at STOCK_R_WRIST)
-> WorkFiles/guns/rifle/scratch/q34_sweeps.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import SCRATCH  # noqa: E402
import rifle_q34 as Q  # noqa: E402
import rifle_parts2 as R2  # noqa: E402
from gunlib import compare as C, camsolve as CS  # noqa: E402


def tris(m):
    T = [t for f in m.F for t in ([f] if len(f) == 3 else [(f[0], f[i], f[i + 1]) for i in range(1, len(f) - 1)])]
    return m.verts(), np.array(T)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    a = ap.parse_args()
    D = np.load(a.npz)
    V, T, lab, names = D["V"], D["T"], D["lab"], [str(n) for n in D["names"]]
    ref, _ = Q.ref_mask()
    cd = json.loads((Q.QDIR / "camera.json").read_text())
    cam = CS.Camera(cd["rvec"], cd["centre_M_mm"], cd["f_px"], cd["cx"], cd["cy"])
    out = {"camera": cd["centre_M_mm"]}

    def zone_for(part):
        k = names.index(part)
        m = C.raster_tris(cam.project(V), T[lab == k], ref.shape) > 0.5
        ys, xs = np.nonzero(m)
        z = np.zeros_like(ref)
        z[max(ys.min() - 12, 0):ys.max() + 12, max(xs.min() - 12, 0):xs.max() + 12] = True
        rest = C.raster_tris(cam.project(V), T[lab != k], ref.shape) > 0.5
        return z, rest, m

    def score(z, rest, m):
        allm = ndi.binary_fill_holes(rest | m)
        return round(C.iou(allm, ref, z), 4), C.contour_distance(allm, ref, z)["p95"]

    # grip
    z, rest, built = zone_for("pistol_grip")
    g = {"built": score(z, rest, built), "W_R": {}}
    for W in (26, 28, 30, 31, 32):
        for Rr in (6, 8, 10, 12, 14):
            Vg, Tg = tris(R2.grip_mesh_numpy(W, Rr, R2.GRIP_CROWN))
            m = C.raster_tris(cam.project(Vg), Tg, ref.shape) > 0.5
            sec = R2.grip_section(39.6, W, Rr, R2.GRIP_CROWN, 400)
            Qs = np.vstack([sec, sec[:1]])
            girth = float(np.linalg.norm(np.diff(Qs, axis=0), axis=1).sum())
            iou, p95 = score(z, rest, m)
            g["W_R"]["%g_%g" % (W, Rr)] = {"zone_iou": iou, "zone_p95_px": p95, "section_girth_mm": round(girth, 1)}
    out["grip"] = g
    # stock
    z, rest, built = zone_for("buttstock")
    s = {"built": score(z, rest, built), "R": {}}
    keep = R2.STOCK_R
    for r in (5, 7, 9, 11, 13, 15):
        R2.STOCK_R = r
        Vs, Ts = tris(R2.buttstock().solids[0])
        m = C.raster_tris(cam.project(Vs), Ts, ref.shape) > 0.5
        iou, p95 = score(z, rest, m)
        s["R"][str(r)] = {"zone_iou": iou, "zone_p95_px": p95}
    R2.STOCK_R = keep
    s["wrist_R"] = R2.STOCK_R_WRIST
    out["stock"] = s
    (SCRATCH / "q34_sweeps.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
