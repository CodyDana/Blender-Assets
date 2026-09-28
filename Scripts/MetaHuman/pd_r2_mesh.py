"""pd_r2_mesh.py -- offline geometry metrics for the round-2 jaw variants (no Unreal).

Run with Blender's bundled Python (numpy):
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/MetaHuman/pd_r2_mesh.py [stems...]
Reads WorkFiles/MetaHuman/player_default/mesh_dump/<stem>.obj (GeometryScript dumps, UE world cm, same topology) and
writes WorkFiles/MetaHuman/player_default/r2_mesh_metrics.json:
  * displacement of every variant vs the control (C0 = FaceC): max / mean over the head, max outside the lower-jaw
    box (how local the change is), the top-moved vertices' location
  * ramus bend: in the posterior jaw-ramus band (both sides), the largest angle between vertex normals of vertices
    closer than 6 mm (a tight fold gives a large angle over a short distance) and the p95 of that measure
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pd_geodiag_lib import load_obj, vertex_normals  # noqa: E402

OUT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_default")
DUMPS = OUT / "mesh_dump"


def ramus_mask(V):
    """Posterior jaw ramus / jaw angle band on both sides (FaceC dump coordinates, cm)."""
    ax = np.abs(V[:, 0])
    return (ax > 3.8) & (ax < 8.5) & (V[:, 2] > 159.5) & (V[:, 2] < 169.0) & (V[:, 1] > -3.5) & (V[:, 1] < 6.0)


def lowerjaw_box(V):
    ax = np.abs(V[:, 0])
    return (ax > 2.0) & (V[:, 2] > 157.0) & (V[:, 2] < 171.0) & (V[:, 1] > -4.5) & (V[:, 1] < 9.5)


def bend(V, F, mask, radius=0.6):
    N = -vertex_normals(V, F)          # dumps are left-handed: flip to outward normals
    idx = np.nonzero(mask)[0]
    P = V[idx]
    Nn = N[idx]
    out = np.zeros(len(idx))
    for k in range(len(idx)):
        d = np.linalg.norm(P - P[k], axis=1)
        near = (d > 1e-6) & (d < radius)
        if near.any():
            c = np.clip(Nn[near] @ Nn[k], -1, 1)
            out[k] = np.degrees(np.arccos(c.min()))
    return idx, out


def main(stems):
    res = {}
    ref_name = stems[0]
    V0, F0 = load_obj(DUMPS / f"{ref_name}.obj")
    m_ram = ramus_mask(V0)
    m_box = lowerjaw_box(V0)
    head = np.ones(len(V0), bool)                 # every Face-component vertex (head, eyes, teeth, lashes...)
    for s in stems:
        V, F = load_obj(DUMPS / f"{s}.obj")
        if V.shape != V0.shape or not np.array_equal(F, F0):
            res[s] = {"error": "topology differs from " + ref_name}
            continue
        d = np.linalg.norm(V - V0, axis=1)
        idx, b = bend(V, F, m_ram)
        side = np.sign(V[idx, 0])
        row = {"disp_max_cm": round(float(d.max()), 4), "disp_mean_all_cm": round(float(d[head].mean()), 5),
               "disp_max_outside_lowerjaw_cm": round(float(d[~m_box].max()), 4),
               "disp_max_at": [round(float(x), 2) for x in V0[int(d.argmax())]],
               "n_moved_gt_1mm": int((d > 0.1).sum()),
               "ramus_bend_max_deg_per6mm": round(float(b.max()), 2),
               "ramus_bend_p95": round(float(np.percentile(b, 95)), 2),
               "ramus_bend_p95_left(+X)": round(float(np.percentile(b[side > 0], 95)), 2),
               "ramus_bend_p95_right(-X)": round(float(np.percentile(b[side < 0], 95)), 2),
               "ramus_max_at": [round(float(x), 2) for x in V[idx[int(b.argmax())]]],
               "ramus_n": int(len(idx))}
        res[s] = row
        print(s, json.dumps(row))
    (OUT / "r2_mesh_metrics.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:] or ["R2X_C0_Face", "R2X_R0_Face"])
