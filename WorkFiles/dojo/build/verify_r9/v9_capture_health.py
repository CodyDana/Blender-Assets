"""VERIFY r8: frame health of every round-5 f1 still (plain Python, read-only). Near-black = max channel < 12 (sRGB);
blown = min channel >= 250; 32 px tiles: black tile = >90 % near-black pixels, blown tile = >50 % blown pixels.
Also a missing-texture / default-material probe: the UE WorldGrid / checker look (grey 0.5 with a regular grid) is
flagged by a tile whose pixels are nearly neutral (sat < 0.04) with two dominant levels. Out: verify_r9/capture_health.json,
verify_r9/near_black/<cam>.png (near-black pixels painted red, blown painted cyan)."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

B = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
CAP = B / "WorkFiles/dojo/build/unreal/round9/s1_work/it3"
VD = B / "WorkFiles/dojo/build/verify_r9"
(VD / "near_black").mkdir(exist_ok=True)
res = {}
for p in sorted(CAP.glob("C*_*.png")):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.int32)
    mx, mn = a.max(axis=2), a.min(axis=2)
    h, w = mx.shape
    t = 32
    def tiles(mask):
        return mask[: h // t * t, : w // t * t].reshape(h // t, t, w // t, t).swapaxes(1, 2).reshape(h // t, w // t, t * t).mean(axis=2)
    nb = mx < 12
    bl = mn >= 250
    bt = tiles(nb) > 0.9
    wt = tiles(bl) > 0.5
    sat = (mx - mn) / np.maximum(mx, 1)
    grey = tiles((sat < 0.04) & (mx > 60)) > 0.95
    res[p.stem] = {"size": [w, h], "near_black_frac": round(float(nb.mean()), 4), "dark25_frac": round(float((mx < 25).mean()), 4),
                   "black_tiles": int(bt.sum()), "black_tile_rows_cols": [[int(r), int(c)] for r, c in zip(*np.nonzero(bt))][:60],
                   "blown_frac": round(float(bl.mean()), 5), "blown_tiles": int(wt.sum()),
                   "blown_tile_rows_cols": [[int(r), int(c)] for r, c in zip(*np.nonzero(wt))][:20],
                   "neutral_grey_tiles": int(grey.sum()), "n_tiles": int(bt.size),
                   "pure_black_frac(max<=2)": round(float((mx <= 2).mean()), 4)}
    im = a.copy().astype(np.uint8)
    im[nb] = (255, 0, 0)
    im[bl] = (0, 255, 255)
    Image.fromarray(im).resize((w // 2, h // 2)).save(VD / "near_black" / f"{p.stem}.png")
(VD / "capture_health.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
for k, v in res.items():
    print(f"{k:24s} nb {v['near_black_frac']:.4f} pure {v['pure_black_frac(max<=2)']:.4f} dark25 {v['dark25_frac']:.4f} blacktiles {v['black_tiles']:4d}/{v['n_tiles']} blown {v['blown_frac']:.5f} blowntiles {v['blown_tiles']} greytiles {v['neutral_grey_tiles']}")
