"""Grip silhouette overlay (plain Python): reference crop at 4x with the reference mask boundary (cyan) and our
silhouette boundary (orange) of a grip_loop render tag, per panel -> review/detail/grip/<tag>_sil_<panel>.png.

    py -3 -B Scripts/guns/rifle/parts/grip_overlay.py --tag r2_i1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import rifle_common  # noqa: E402,F401  (puts Scripts/guns on the path)
from gunlib import closeup as CU  # noqa: E402
from gunlib import compare as C  # noqa: E402
from parts import grip_loop as GL  # noqa: E402


def main(tag, k=4):
    K = GL.kit()
    for key in K.cfg["parts"][GL.PART]["panels"]:
        P = K.panel(key)
        rgba = np.asarray(Image.open(K.scratch / "renders" / f"{GL.PART}__{key}_{tag}.png").convert("RGBA"))
        alpha = CU.downscale(np.repeat(rgba[:, :, 3:4], 3, 2).astype(np.uint8), K.ss)[:, :, 0] / 255.0
        x0, y0, x1, y1 = K.window(GL.PART, key)
        ref = K.mask(key)[y0:y1, x0:x1]
        ours = (alpha > 0.5)[y0:y1, x0:x1]
        im = Image.fromarray(np.clip(P[y0:y1, x0:x1], 0, 255).astype(np.uint8)).resize(((x1 - x0) * k, (y1 - y0) * k), Image.LANCZOS)
        A = np.asarray(im).copy()
        up = lambda m: np.kron(m.astype(np.uint8), np.ones((k, k), np.uint8)).astype(bool)
        A[C.boundary(up(ref))] = (0, 200, 230)
        A[C.boundary(up(ours))] = (255, 140, 0)
        Image.fromarray(A).save(GL.REV / f"{tag}_sil_{key}.png")
        print(key, "window", (x0, y0, x1, y1), "->", GL.REV / f"{tag}_sil_{key}.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    main(ap.parse_args().tag)
