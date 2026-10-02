"""meas.py <dir> : numbers for every probe still in <dir> (Rec.709 luma on sRGB): whole-frame under-40 share, mean,
p10/p90, near-black (<10) share; CAM_Ref2Match regions through round 9's measure_r8 boxes; CU_HallUpperRoof tile colour
(lit top 30 % / shade bottom 50 % of a roof box); CU_Lantern glow (top 10 % of the lantern box, HLS saturation)."""
import colorsys, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
import types
_src = open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/unreal/round9/s1_work/measure_r8.py").read()
M = types.ModuleType("measure_r8")
exec(_src.rsplit(chr(10) + "main()", 1)[0], M.__dict__)

def luma(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722

def reg(px):
    m = np.median(px, 0)
    h, l, s = colorsys.rgb_to_hls(*(m / 255.0))
    return {"srgb": [round(float(v)) for v in m], "L": round(float(luma(m[None])[0]), 1), "hue": round(h * 360), "sat": round(s, 2),
            "r_b": round(float(m[0] / max(m[2], 1)), 2)}

def box(a, b, mode="median"):
    x0, y0, x1, y1 = b
    px = a[y0:y1, x0:x1].reshape(-1, 3)
    if mode != "median":
        L = luma(px)
        q = np.percentile(L, 70 if mode == "top30" else (90 if mode == "top10" else 50))
        px = px[L >= q] if mode in ("top30", "top10") else px[L <= q]
    return reg(px)

d = Path(sys.argv[1])
out = {}
for p in sorted(d.glob("*__*.png")):
    a = np.asarray(Image.open(p).convert("RGB"), float)
    L = luma(a)
    r = {"under40": round(float((L < 40).mean() * 100), 1), "mean": round(float(L.mean()), 1),
         "p10": round(float(np.percentile(L, 10)), 1), "p90": round(float(np.percentile(L, 90)), 1),
         "black10": round(float((L < 10).mean() * 100), 1)}
    cam = p.stem.split("__")[1]
    H, W = a.shape[:2]
    if cam == "CAM_Ref2Match":
        m = M.measure(str(p), "ours")
        r["regions"] = {k: {"srgb": v["rgb"], "r_b": v["r_over_b"], "sat": v["hls_s"], "hue": v["hue"]} for k, v in m["regions"].items()}
        r["sand_highpass"] = m["sand_texture_highpass_std"]
    if cam == "CU_HallUpperRoof":
        r["tiles_lit"] = box(a, (int(W * .25), int(H * .25), int(W * .75), int(H * .6)), "top30")
        r["tiles_shade"] = box(a, (int(W * .25), int(H * .25), int(W * .75), int(H * .6)), "bot50")
    if cam == "CAM_Drum":
        r["upper_third_under40"] = round(float((L[: H // 3] < 40).mean() * 100), 1)
    out[p.stem] = r
(d / "meas.json").write_text(json.dumps(out, indent=1))
for k, v in out.items():
    s = {kk: vv for kk, vv in v.items() if kk not in ("regions",)}
    print(k, json.dumps(s))
    if "regions" in v:
        for rk in ("top_sky", "horizon_sky_behind_hall", "sand_near", "sand_far", "timber", "tiles_lit", "tiles_shade", "shoji_glow", "lantern_glow", "plaster", "gravel"):
            if rk in v["regions"]:
                print("    ", rk, v["regions"][rk])
