"""Per-image extra measures for a probe folder: sand lit/shade (Ref2Match framing) or the sky band, by shot name."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).parent))
import extra_r9 as X
d = Path(sys.argv[1])
for p in sorted(d.glob("*.png")):
    a = np.asarray(Image.open(p).convert("RGB"))
    lu = X.luma(a.astype(float))
    row = {"under40": round(float((lu < 40).mean() * 100), 1), "mean": round(float(lu.mean()), 1)}
    if "e_" in p.stem.split("_")[0] + "_" or p.stem.startswith(tuple(f"{c}e" for c in "abcdefghij")) and "e_" in p.stem[:4]:
        row["sky_est"] = X.sky(a, (0, int(235 * a.shape[0] / 1440), a.shape[1], int(330 * a.shape[0] / 1440)))
    else:
        row["sand"] = X.lit_shade(a)
        row["sky_r2m"] = X.sky(a, (0, 0, a.shape[1], int(280 * a.shape[0] / 1440)))
    print(p.stem, json.dumps(row))
