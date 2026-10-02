"""Sunset-lit preview of single flipbook frame EXRs (the compose_mist lighting), for quick iteration.

    blender -b --factory-startup --python Scripts/dojo/fx/lit_preview.py -- Name frame [frame ...]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_common as fx  # noqa: E402
import render_flipbooks as RF  # noqa: E402

SUN = np.array([1.0, 0.70, 0.46])
FILL = np.array([0.20, 0.22, 0.30])
argv = sys.argv[sys.argv.index("--") + 1:]
name, frames = argv[0], [int(v) for v in argv[1:]]
tiles = []
for f in frames:
    alpha, lg = RF.frame_passes(RF.read_exr(fx.SRC_TEX / name / f"{name}_{f:03d}.exr"))
    allv = np.concatenate([lg[k].ravel() for k in lg])
    norm = float(np.percentile(allv[allv > 1e-5], 99.8))
    am = np.maximum(alpha, 1e-3)
    g = {k: np.where(alpha > 0.004, lg[k] / norm / am, 0) for k in lg}
    key = 0.30 * g["PY"] + 0.35 * g["PZ"] + 0.35 * g["NX"]
    fill = 0.6 * g["NY"] + 0.2 * g["NZ"] + 0.2 * g["PX"]
    rgb = np.clip(key[..., None] * SUN + fill[..., None] * FILL * 0.8, 0, 1) * alpha[..., None]
    tiles.append(rgb)
fx.save_png(np.concatenate(tiles, axis=1), fx.WORK / f"renders/flipbooks/preview/{name}_lit.png")
print("LIT", name, frames)
