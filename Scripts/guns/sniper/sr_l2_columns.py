"""SR01 W1 follow-up L2 evidence: per X station (mm), the traced silhouette's top / bottom Z in GR and GL against the
build's, so a residual can be called 'geometry off the trace' (GR and GL agree, we differ) or 'sheet problem' (GR
and GL disagree with each other). Plain Python on the form npz.
    py -3 -B Scripts/guns/sniper/sr_l2_columns.py [--npz ...] [--json ...]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import sr_silhouette as S  # noqa: E402
from sr_common import SCRATCH, trace  # noqa: E402
from gunlib import compare as C  # noqa: E402


def columns(npz, with_npz):
    z = np.load(npz, allow_pickle=True)
    V, T = z["V"], z["T"]
    w = np.load(with_npz, allow_pickle=True)
    wn = [str(n) for n in w["names"]]
    sel = np.array([wn[l].startswith("scope") for l in w["lab"]])
    T = np.vstack([T, w["T"][sel] + len(V)])
    V = np.vstack([V, w["V"]])
    out = {}
    for view in ("GR", "GL"):
        j = trace(view)
        X, _ = S.affine(j["silhouette"]["px"], j["silhouette"]["mm"])
        ref = S.ref_mask(view)
        ours = C.raster_tris(S.project(V, view, X), T, ref.shape, ss=4) > 0.5
        A = np.r_[X.T, [[0.0, 0.0, 1.0]]]
        Ai = np.linalg.inv(A)
        H, W = ref.shape
        rows = {}
        for xm in range(40, 1101, 20):
            px = A @ np.array([xm, 0.0, 1.0])
            c = int(round(px[0]))
            if not 0 <= c < W:
                continue
            def ext(m):
                ys = np.nonzero(m[:, c])[0]
                if not len(ys):
                    return None
                zz = [(Ai @ np.array([c, y, 1.0]))[1] for y in (ys.min(), ys.max())]
                return [round(max(zz), 1), round(min(zz), 1)]
            rows[xm] = {"ref_top_bot": ext(ref), "ours_top_bot": ext(ours)}
        out[view] = rows
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", default=str(SCRATCH / "form_tris.npz"))
    ap.add_argument("--with-npz", default=str(SCRATCH / "blockout_tris.npz"))
    ap.add_argument("--json", default=str(SCRATCH / "l2_columns.json"))
    a = ap.parse_args()
    r = columns(a.npz, a.with_npz)
    Path(a.json).write_text(json.dumps(r, indent=1))
    print("X    GR ref(t,b)   ours(t,b)   | GL ref(t,b)   ours(t,b)")
    for xm in r["GR"]:
        g, l = r["GR"][xm], r["GL"].get(xm, {})
        print(xm, g["ref_top_bot"], g["ours_top_bot"], "|", l.get("ref_top_bot"), l.get("ours_top_bot"))
