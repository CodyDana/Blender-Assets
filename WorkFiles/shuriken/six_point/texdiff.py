"""Pixel difference of two directories of baked maps (T_*.png), 8-bit stored values.

    <blender python> texdiff.py <dir_a> <dir_b> [--out result.json] [--label text]

Per map: max |a - b| over channels, the fraction of pixels that differ at all and by more than 2/255, and the
mean absolute difference.  Used to show that the GPU (OptiX) bake is not bit-reproducible run to run: two
identical frozen-only rebuilds differ from each other by exactly the same 1/255 noise as the pack build
with the six-point differs from the post_restyle2 baseline.
"""
import json
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio

argv = sys.argv[1:]
a_dir, b_dir = Path(argv[0]), Path(argv[1])
out = {"a": str(a_dir), "b": str(b_dir), "label": argv[argv.index("--label") + 1] if "--label" in argv else "",
       "maps": {}}
for f in sorted(a_dir.glob("T_*.png")):
    g = b_dir / f.name
    if not g.exists():
        out["maps"][f.name] = {"missing_in_b": True}
        continue
    A = np.asarray(oiio.ImageBuf(str(f)).get_pixels(oiio.UINT8)).astype(np.int32)
    B = np.asarray(oiio.ImageBuf(str(g)).get_pixels(oiio.UINT8)).astype(np.int32)
    if A.shape != B.shape:
        out["maps"][f.name] = {"shape": [list(A.shape), list(B.shape)]}
        continue
    d = np.abs(A - B).max(-1)
    out["maps"][f.name] = {"max_abs_8bit": int(d.max()), "pixels_differing": int((d > 0).sum()),
                           "fraction_differing": round(float((d > 0).mean()), 7),
                           "pixels_over_2": int((d > 2).sum()), "mean_abs": round(float(np.abs(A - B).mean()), 7)}
out["max_abs_8bit"] = max((m.get("max_abs_8bit", 999) for m in out["maps"].values()), default=None)
out["max_pixels_differing"] = max((m.get("pixels_differing", 10 ** 9) for m in out["maps"].values()), default=None)
if "--out" in argv:
    Path(argv[argv.index("--out") + 1]).write_text(json.dumps(out, indent=2), encoding="utf-8")
print("TEXDIFF", out["label"], "max", out["max_abs_8bit"], "max_px", out["max_pixels_differing"])
