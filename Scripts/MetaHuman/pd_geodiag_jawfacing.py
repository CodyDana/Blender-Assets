"""pd_geodiag_jawfacing.py -- how much DOWN-facing skin under the jaw is visible to the UE capture cameras.

Area of head triangles below the mouth whose outward normal points down (n.z < -0.6 / -0.8), and the part of it the
front and 3/4 capture cameras see (front-facing, projected to 1000x1200 px, no occlusion test), for FaceC, ref,
Kelvin (similarity-aligned to FaceC) and the source input. Down-facing skin gets no direct light from the capture
rig (all three lights come from above) and no sky light (UE SkyLight lower hemisphere black by default), so this is
the area that renders near-black in the simple (no-GI) captures.
Blender Python:  ".../5.2/python/bin/python.exe" Scripts/MetaHuman/pd_geodiag_jawfacing.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pd_geodiag_lib import DUMPS, OUT, apply, face_normals, kabsch, load_obj  # noqa: E402

NH = 24049
FC = np.array((0.0, 5.959721088409424, 173.6))
a = math.radians(35)
CAMS = {"Front": FC + (0, 70, 0), "ThreeQuarter": FC + (70 * math.sin(a), 70 * math.cos(a), 0)}
FPX = 500.0 / math.tan(math.radians(15))
M = {k: load_obj(DUMPS[k]) for k in ("FaceC_Face", "ref_Face", "kelvin_Face", "source")}
F = M["kelvin_Face"][1]
FH = F[np.all(F < NH, axis=1)]
R, t, s = kabsch(M["kelvin_Face"][0][:NH], M["FaceC_Face"][0][:NH], scale=True)
meshes = {"FaceC": (M["FaceC_Face"][0][:NH], FH), "ref": (M["ref_Face"][0][:NH], FH),
          "Kelvin_aligned": (apply(R, t, s, M["kelvin_Face"][0][:NH]), FH), "source": M["source"]}
out = {}
for name, (V, Fm) in meshes.items():
    n, area = face_normals(V, Fm)
    n = -n                                           # dump winding -> outward
    c = V[Fm].mean(1)
    # lower face of THIS mesh: between chin bottom - 1 cm and the mouth corners, in front of the ears
    head_front = c[:, 1] > np.percentile(V[:, 1], 5)
    nose_y = V[np.argmax(np.where(V[:, 2] > 150, V[:, 1], -1e9))]
    zmouth = nose_y[2] - 4.0
    zlo = zmouth - 12.0
    sel = (c[:, 2] > zlo) & (c[:, 2] < zmouth) & (np.abs(c[:, 0]) < 9.5) & (c[:, 1] > nose_y[1] - 16)
    res = {"nose_tip": np.round(nose_y, 2).tolist(), "z_window": [round(zlo, 2), round(zmouth, 2)]}
    for thr in (-0.6, -0.8):
        m = sel & (n[:, 2] < thr)
        res[f"area_cm2_nz_lt_{thr}"] = round(float(area[m].sum()), 2)
    for cam_name, cam in CAMS.items():
        vdir = cam - c
        dist = np.linalg.norm(vdir, axis=1)
        vdir /= dist[:, None]
        ndv = (n * vdir).sum(1)
        for thr in (-0.6, -0.8):
            m = sel & (n[:, 2] < thr) & (ndv > 0)
            px = area[m] * ndv[m] * (FPX / dist[m]) ** 2
            res[f"{cam_name}_visible_px_nz_lt_{thr}"] = int(px.sum())
    out[name] = res
(OUT / "jawfacing_report.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
