"""pd_geodiag_cervicomental.py -- chin/jaw-to-neck angle (cervicomental angle) per sagittal strip, FaceC vs ref vs
Kelvin (aligned) vs source. Angle = 180 - angle between the mean outward normal of the under-chin surface (n.z < -0.6)
and of the front of the neck (|n.z| < 0.35, n.y > 0.5) inside a 1.2 cm wide strip at x = c.
Smaller angle = sharper jaw/neck corner = thinner, darker grazing band under the jaw.
Blender Python (numpy)."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pd_geodiag_lib import DUMPS, OUT, apply, kabsch, load_obj, vertex_normals  # noqa: E402

NH = 24049
M = {k: load_obj(DUMPS[k]) for k in ("FaceC_Face", "ref_Face", "kelvin_Face", "source")}
F = M["kelvin_Face"][1]
FH = F[np.all(F < NH, axis=1)]
R, t, s = kabsch(M["kelvin_Face"][0][:NH], M["FaceC_Face"][0][:NH], scale=True)
meshes = {"FaceC": (M["FaceC_Face"][0][:NH], FH), "ref": (M["ref_Face"][0][:NH], FH),
          "Kelvin_aligned": (apply(R, t, s, M["kelvin_Face"][0][:NH]), FH), "source": M["source"]}
out = {}
for name, (V, Fm) in meshes.items():
    used = np.unique(Fm)
    n = -vertex_normals(V, Fm)
    nose = V[np.argmax(np.where(V[:, 2] > 150, V[:, 1], -1e9))]
    zc = nose[2]
    res = {}
    for c in (0.0, 2.5, -2.5, 4.5, -4.5):
        m = np.zeros(len(V), bool)
        m[used] = True
        m &= (np.abs(V[:, 0] - c) < 0.6) & (V[:, 2] > zc - 20) & (V[:, 2] < zc - 5) & (V[:, 1] > nose[1] - 16)
        under = m & (n[:, 2] < -0.6)
        neck = m & (np.abs(n[:, 2]) < 0.35) & (n[:, 1] > 0.5) & (V[:, 2] < (V[under, 2].min() if under.any() else 0))
        if under.sum() < 3 or neck.sum() < 3:
            res[str(c)] = None
            continue
        a = n[under].mean(0)
        b = n[neck].mean(0)
        a /= np.linalg.norm(a)
        b /= np.linalg.norm(b)
        ang = 180.0 - np.degrees(np.arccos(np.clip(a @ b, -1, 1)))
        res[str(c)] = {"cervicomental_deg": round(float(ang), 1), "under_chin_normal": np.round(a, 3).tolist(),
                       "neck_front_normal": np.round(b, 3).tolist(), "n_under": int(under.sum()), "n_neck": int(neck.sum())}
    out[name] = res
(OUT / "cervicomental_report.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for k, v in out.items():
    print(k, {c: (d["cervicomental_deg"] if d else None) for c, d in v.items()})
