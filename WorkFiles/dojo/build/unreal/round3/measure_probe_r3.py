"""Round 3: measure the colour-probe cards (probe.json boxes) and the CAM_HallVeranda regions per variant.
Run: py -3 WorkFiles/dojo/build/unreal/round3/measure_probe_r3.py <probe_dir>"""
import colorsys, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
D = Path(sys.argv[1]); HERE = Path(__file__).resolve().parent
P = json.loads((D / "probe.json").read_text(encoding="utf-8"))
REG = json.loads((HERE / "regions_r3.json").read_text(encoding="utf-8"))
def st(a, b):
    x0, y0, x1, y1 = [int(v) for v in b]; px = a[y0:y1, x0:x1].reshape(-1, 3); m = np.median(px, 0)
    h, s, v = colorsys.rgb_to_hsv(*(m / 255)); return [int(x) for x in m], round(h * 360), round(s, 2), round(m[0] / max(m[2], 1), 2)
out = {}
for vn, rec in P["variants"].items():
    out[vn] = {}
    for cam, f in rec["captures"].items():
        a = np.asarray(Image.open(f).convert("RGB")).astype(float)
        boxes = {k: v["box_px"] for k, v in P["cards"].get(cam, {}).items()} or REG.get(cam, {})
        for k, b in boxes.items():
            out[vn][f"{cam}:{k}"] = st(a, b)
            print(f"{vn:18s} {cam}:{k:22s} {out[vn][f'{cam}:{k}']}")
(D / "probe_measure.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
