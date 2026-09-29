"""Image statistics for the ArmoryLab captures (system Python with Pillow + numpy: `py -3 ak_image_stats.py`).

1. Tone: display-value luminance (Rec.709 weights on the 8-bit sRGB values / 255) mean, p10, p50, p90, share below 0.2,
   cream share (L > 0.6 and HSV saturation < 0.35), mean HSV saturation (pixels with max > 0.02), for every Unreal capture,
   the matching Blender render of the preset (env AK_PRESET, default night: renders/night_r16, fallback night_20m; golden:
   renders/hero_live; key "blender") and the LOOK reference.
2. Exposure sweep (captures/diag/<cam>_bias_*.png): the bias whose frame mean / p50 best matches the Blender golden render.
3. Convergence: mean absolute difference (8-bit levels) between successive checkpoints of each camera's capture sequence,
   and between the last two; plus the share of pixels that still move by more than 4 levels.
4. Diagnostics: mean absolute difference of the Lumen-GI-off and volumetric-fog-off frames from the final C1 frame.
Out: WorkFiles/armory/build/unreal/capture_stats.json
"""
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\unreal")
CAP = OUT / "captures"
PRESET = os.environ.get("AK_PRESET", "night").strip().lower() or "night"   # night + genkan (2026-09-28)
# the Blender renders of the same preset: night = renders/night_live2 (the live entry-fix round 2 build; was night_live); golden =
# renders/hero_live (hero round: the live hero build; was stage_f2, fix1 before)
# r16 round live (2026-09-29): night = renders/night_r16 (all eight views), fallback night_20m
# 12 x 20 m hall live (2026-09-29): night = renders/night_20m (all eight views), fallback night_live4
# rear dais live (2026-09-28): night = renders/night_live4 (C1, CX, C10, C3, CW, CG); views it lacks (C4, C5) fall back
# to night_live2 via bl_file()
_RENDERS = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\build\renders")
BL = _RENDERS / ("night_r16" if PRESET == "night" else "hero_live")
BL_FALLBACK = _RENDERS / "night_20m" if PRESET == "night" else None


def bl_file(rel):
    """The Blender baseline file (relative to BL); falls back to the previous night build for views not re-rendered."""
    b = BL / rel
    if not b.exists() and BL_FALLBACK is not None and (BL_FALLBACK / rel).exists():
        return BL_FALLBACK / rel
    return b
REF = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference\armory3_reference2.png")


def _crops():
    try:
        caps = json.loads((OUT / "capture.json").read_text(encoding="utf-8")).get("captures", {})
    except (OSError, ValueError):
        return {}
    return {k: (v["target_wh"][1], v["crop"]) for k, v in caps.items() if v.get("crop")}


CROPS = _crops()


def load_cap(p, name):
    """A capture frame; the raw tall frames of a shift-lens camera (sequence, diag) are cropped like the final
    (capture.json "crop"; ak_crop.py) so every comparison is on the same framing."""
    a = load(p)
    c = CROPS.get(name)
    if c and a.shape[0] == c[0]:
        a = a[c[1][0]:c[1][1]]
    return a


def load(p, size=None):
    im = Image.open(p).convert("RGB")
    if size and im.size != size:
        im = im.resize(size, Image.BILINEAR)
    return np.asarray(im).astype(np.float64) / 255.0


def stats(a):
    L = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    sat = np.where(mx > 0.02, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    return {"mean": round(float(L.mean()), 3), "p10": round(float(np.percentile(L, 10)), 3),
            "p50": round(float(np.percentile(L, 50)), 3), "p90": round(float(np.percentile(L, 90)), 3),
            "below_0.2": round(float((L < 0.2).mean()), 3),
            "cream": round(float(((L > 0.6) & (sat < 0.35)).mean()), 3),
            "sat_mean": round(float(sat[mx > 0.02].mean()), 3),
            "blue_red": round(float(a[..., 2].mean() / max(a[..., 0].mean(), 1e-6)), 3)}


def mad(a, b):
    d = np.abs(a - b) * 255.0
    return round(float(d.mean()), 3), round(float((d.max(-1) > 4).mean()), 4)


def main():
    rep = {"preset": PRESET, "blender_dir": str(BL), "tone": {}, "sweep": {}, "convergence": {}, "diag": {}}
    rep["tone"]["LOOK_reference"] = stats(load(REF))
    finals = sorted(p for p in CAP.glob("*.png"))
    for p in finals:
        cam = p.stem
        ue_img = load(p)
        rep["tone"][cam] = {"unreal": stats(ue_img)}
        b = (bl_file(Path("ref_aspect") / f"{cam.replace('_ref_aspect', '')}_{PRESET}.png") if cam.endswith("_ref_aspect")
             else bl_file(f"{cam}_{PRESET}.png"))
        if cam.endswith("_ref_aspect"):   # C1 at 1448 x 1086 against the LOOK reference itself
            rep["tone"][cam]["LOOK_reference"] = stats(load(REF, (ue_img.shape[1], ue_img.shape[0])))
        if b.exists():
            rep["tone"][cam]["blender"] = stats(load(b, (ue_img.shape[1], ue_img.shape[0])))
        seq = sorted((CAP / "sequence").glob(f"{cam}_f*.png"), key=lambda q: int(q.stem.rsplit("_f", 1)[1]))
        imgs = [(int(q.stem.rsplit("_f", 1)[1]), load_cap(q, cam)) for q in seq]
        steps = {}
        for (f0, a0), (f1, a1) in zip(imgs, imgs[1:]):
            steps[f"{f0}->{f1}"] = mad(a0, a1)
        rep["convergence"][cam] = {"steps_mean_abs_levels_and_share_gt4": steps,
                                   "final_vs_f1": mad(imgs[0][1], ue_img) if imgs else None}
    c1 = CAP / "C1_EntryReveal.png"
    if c1.exists():
        base = load(c1)
        for q in sorted((CAP / "diag").glob("C1_EntryReveal_*_off.png")):
            rep["diag"][q.stem] = {"mean_abs_levels_vs_final": mad(load_cap(q, "C1_EntryReveal"), base)[0],
                                   "mean_L_off": stats(load_cap(q, "C1_EntryReveal"))["mean"],
                                   "mean_L_final": stats(base)["mean"]}
        target = rep["tone"].get("C1_EntryReveal", {}).get("blender")
        for q in sorted((CAP / "diag").glob("C1_EntryReveal_bias_*.png")):
            m = re.search(r"bias_([+-][0-9.]+)", q.stem)
            s = stats(load_cap(q, "C1_EntryReveal"))
            s["abs_err_mean"] = round(abs(s["mean"] - target["mean"]), 3) if target else None
            s["abs_err_p50"] = round(abs(s["p50"] - target["p50"]), 3) if target else None
            rep["sweep"][m.group(1)] = s
        if rep["sweep"] and target:
            best = min(rep["sweep"].items(), key=lambda kv: kv[1]["abs_err_mean"] + kv[1]["abs_err_p50"])
            rep["sweep_best_bias"] = float(best[0])
    (OUT / "capture_stats.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps(rep, indent=1)[:6000])


main()
