"""LANDSCAPE ROUND, FX + LIGHTING stage: the numbers on a -game capture folder (plain Python + PIL / numpy).
- measure_landscape.py (the world stage's measurer, run as is): LANDSCAPE_vs_OURS.png, REF2_vs_OURS.png, the
  CAM_LandscapeRef matched-framing stats and region colours (sky, peaks, forest slopes, river water, foam, terrace wall,
  compound), the foam share in the rapids boxes, per-still health
- round 9's measure_r8 boxes on CAM_Ref2Match against dojo1_reference2 (top sky, sand near / far, timber, tiles lit /
  shade, shoji, lantern, plaster, gravel; sand high-pass)
- extra regions: the LandscapeRef top sky band (0-120 px of 1536: the upper sky the brief asks about), CAM_Drum near-black
  share (luma < 10), CU_HallUpperRoof tiles lit / shade (top 30 % / bottom 50 % of a central roof box)
usage: py -3 -B measure_fxlight.py <caps dir> [<compare caps dir>]    out: <caps>/json/fxl_measure.json (+ the sheets)
"""
import colorsys
import json
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
_src = (ROOT / "WorkFiles/dojo/build/unreal/round9/s1_work/measure_r8.py").read_text(encoding="utf-8")
M8 = types.ModuleType("measure_r8")
exec(_src.rsplit(chr(10) + "main()", 1)[0], M8.__dict__)  # noqa: S102  (our own script, without its CLI main)


def luma(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def reg(px):
    m = np.median(px, 0)
    h, l, s = colorsys.rgb_to_hls(*(m / 255.0))
    return {"srgb": [int(round(v)) for v in m], "luma": round(float(luma(m[None])[0]), 1), "hue": round(h * 360, 1),
            "sat": round(s, 3), "r_over_b": round(float(m[0] / max(m[2], 1)), 3)}


def box(a, b, mode="median"):
    x0, y0, x1, y1 = b
    px = a[y0:y1, x0:x1].reshape(-1, 3)
    if mode != "median":
        L = luma(px)
        px = px[L >= np.percentile(L, 70)] if mode == "top30" else px[L <= np.percentile(L, 50)]
    return reg(px)


def stats(a):
    L = luma(a)
    return {"under40_pct": round(float((L < 40).mean() * 100), 2), "mean": round(float(L.mean()), 1),
            "p10": round(float(np.percentile(L, 10)), 1), "p90": round(float(np.percentile(L, 90)), 1),
            "near_black_lt10_pct": round(float((L < 10).mean() * 100), 2)}


def extras(caps):
    out = {}
    p = caps / "CAM_LandscapeRef.png"
    if p.exists():
        a = np.asarray(Image.open(p).convert("RGB").resize((1024, 1536), Image.LANCZOS), float)
        out["landscape_top_sky_band"] = box(a, (0, 0, 1024, 120))
        out["landscape_sky_box"] = box(a, (80, 150, 480, 400))
    p = caps / "CAM_Ref2Match.png"
    if p.exists():
        r = M8.measure(str(p), "ours")
        out["ref2match"] = {k: r[k] for k in ("luma_share_under_40_pct", "luma_mean", "luma_p10", "luma_p90",
                                              "sand_texture_highpass_std")}
        out["ref2match"]["regions"] = {k: {"srgb": v["rgb"], "hue": v["hue"], "sat": v["hls_s"], "r_over_b": v["r_over_b"]}
                                       for k, v in r["regions"].items()}
    for cam in ("CAM_Drum", "CAM_HallVeranda", "CU_Lantern", "CU_HallUpperRoof", "CAM_EastYard"):
        p = caps / f"{cam}.png"
        if not p.exists():
            continue
        a = np.asarray(Image.open(p).convert("RGB"), float)
        out[cam] = stats(a)
        if cam == "CU_HallUpperRoof":
            H, W = a.shape[:2]
            b = (int(W * .25), int(H * .25), int(W * .75), int(H * .6))
            out[cam]["tiles_lit"] = box(a, b, "top30")
            out[cam]["tiles_shade"] = box(a, b, "bot50")
    return out


def main():
    caps = Path(sys.argv[1])
    subprocess.run([sys.executable, "-B", str(ROOT / "Scripts/dojo/landscape/measure_landscape.py"), str(caps)], check=True)
    base = json.loads((caps / "json/measure_landscape.json").read_text(encoding="utf-8"))
    ref2 = M8.measure(M8.REF, "ref")
    res = {"landscape": base, "extras": extras(caps),
           "ref2_reference": {"stats": {k: ref2[k] for k in ("luma_share_under_40_pct", "luma_mean", "luma_p10", "luma_p90",
                                                             "sand_texture_highpass_std")},
                              "regions": {k: {"srgb": v["rgb"], "hue": v["hue"], "sat": v["hls_s"], "r_over_b": v["r_over_b"]}
                                          for k, v in ref2["regions"].items()}}}
    if len(sys.argv) > 2:
        res["compare_dir"] = sys.argv[2]
        res["compare_extras"] = extras(Path(sys.argv[2]))
    (caps / "json/fxl_measure.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    e = res["extras"]
    print("LandscapeRef", json.dumps(base.get("landscape_ref", {}).get("ours")), "foam", json.dumps(base.get("foam", {}).get("ours")))
    print("top sky band", e.get("landscape_top_sky_band"))
    print("Ref2Match", json.dumps({k: v for k, v in e.get("ref2match", {}).items() if k != "regions"}))
    for k in ("top_sky", "sand_near", "sand_far", "timber", "tiles_lit", "tiles_shade", "shoji_glow", "lantern_glow",
              "plaster", "gravel"):
        print("   ", k, e.get("ref2match", {}).get("regions", {}).get(k))
    for c in ("CAM_Drum", "CAM_HallVeranda", "CU_Lantern", "CU_HallUpperRoof", "CAM_EastYard"):
        print(c, e.get(c))


main()
