"""FIX round: luma stats of the probe variants against the armory chat's own r20 stills (read only).
usage: py -3 -B probe_stats.py <probe dir> [prefixes]"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
AK = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\unreal\captures")
d = Path(sys.argv[1])
pre = sys.argv[2].split(",") if len(sys.argv) > 2 else sorted({p.name.split("_")[0] for p in d.glob("*_CAM_*.png")})
def st(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float32)
    l = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return [round(float(l.mean()), 1), round(float(np.percentile(l, 10)), 1), round(float(np.percentile(l, 50)), 1),
            round(float(np.percentile(l, 90)), 1)]
cams = sorted({p.stem.split("_", 1)[1] for p in d.glob("*_CAM_*.png")})
out = {}
print("cam".ljust(24), "armory".ljust(24), *[x.ljust(24) for x in pre])
for c in cams:
    ak = AK / (c.replace("CAM_AK_", "") + ".png")
    row = {"armory": st(ak) if ak.exists() else None}
    for x in pre:
        p = d / f"{x}_{c}.png"
        row[x] = st(p) if p.exists() else None
    out[c] = row
    print(c.ljust(24), str(row["armory"]).ljust(24), *[str(row[x]).ljust(24) for x in pre])
# mean log ratio of the mean luma vs the armory (display space)
for x in pre:
    r = [np.log2(out[c][x][0] / out[c]["armory"][0]) for c in cams if out[c].get(x) and out[c]["armory"]]
    r50 = [np.log2(max(out[c][x][2], 1) / max(out[c]["armory"][2], 1)) for c in cams if out[c].get(x) and out[c]["armory"]]
    print(x, "mean log2(ours/armory) of mean", round(float(np.mean(r)), 3), "of p50", round(float(np.mean(r50)), 3))
(d / "probe_stats.json").write_text(json.dumps(out, indent=1))
