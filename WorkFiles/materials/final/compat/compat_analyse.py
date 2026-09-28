"""Compare the Substrate and forward-shading captures with the deferred reference (np_compat_capture.py).
    blender -b --factory-startup --python compat_analyse.py
base (Substrate only; forward has no GBuffer): stored 8-bit level differences of SCS_BASE_COLOR.
lit: SCS_FINAL_COLOR_HDR of the same plane under one directional light: mean luminance ratio, per-pixel dE00 (on the
     linear HDR values clamped to 0..1), and the plateau of the recoloured captures (posterisation check).
Writes compat_results.json and compat_sheet.png (deferred | substrate | forward, lit, per job)."""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

P = Path("C:/Users/Cody/Desktop/Blender_Projects")
H = P / "WorkFiles/materials/final/compat"
sys.path.insert(0, str(P / "Scripts/unreal/materials/maps")); sys.path.insert(0, str(P / "WorkFiles/materials/final/recolour"))
sys.dont_write_bytecode = True
import recolour_common as rc  # noqa: E402
from fs_font import draw_text  # noqa: E402


def load(p):
    img = bpy.data.images.load(str(p), check_existing=False)
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)[::-1, :, :3].astype(np.float64)


runs = {t: json.loads((H / f"out_{t}/compat_capture.json").read_text()) for t in ("deferred", "substrate", "forward")}
out = {"cvars": {t: r["cvars"] for t, r in runs.items()}, "ps_instructions": {t: r["stats"] for t, r in runs.items()},
       "jobs": {}}
tiles = []
for name in runs["deferred"]["captures"]:
    ref = runs["deferred"]["captures"][name]
    rec = {}
    lit_ref = load(ref["lit"])
    row = [lit_ref]
    for t in ("substrate", "forward"):
        c = runs[t]["captures"].get(name, {})
        if "lit" in c:
            lit = load(c["lit"])
            lr, ll = lit_ref @ rc.LUM, lit @ rc.LUM
            de = rc.de2000(np.clip(lit_ref, 0, 1).reshape(-1, 3)[::7], np.clip(lit, 0, 1).reshape(-1, 3)[::7])
            q = rc.q8_srgb(np.clip(lit, 0, 1))
            cnt = np.bincount(q.max(-1).ravel(), minlength=256)
            rec[f"lit_{t}"] = {"lum_ratio_vs_deferred": round(float(ll.mean() / max(lr.mean(), 1e-9)), 4),
                               "dE00_mean": round(float(de.mean()), 3), "dE00_p99": round(float(np.percentile(de, 99)), 3),
                               "plateau": round(float(cnt.max() / cnt.sum()), 4), "levels": int((cnt > 0).sum())}
            row.append(lit)
        if t == "substrate" and "base" in c and "base" in ref:
            a, b = rc.q8_srgb(load(ref["base"])).astype(int), rc.q8_srgb(load(c["base"])).astype(int)
            d = np.abs(a - b).max(-1)
            rec["base_substrate_vs_deferred_levels"] = {"max": int(d.max()), "p99_9": float(np.percentile(d, 99.9)),
                                                        "mean": round(float(d.mean()), 4)}
    out["jobs"][name] = rec
    tiles.append((name, row))
    print(name, json.dumps(rec))
T = 256
Wd = 300 + 3 * (T + 8)
canvas = np.full((60 + len(tiles) * (T + 8), Wd, 3), 24, np.int32)
draw_text(canvas, 10, 10, "LIT PLANE: DEFERRED | SUBSTRATE | FORWARD (UE 5.8.3)", (235, 235, 235), 2)
y = 50
for name, row in tiles:
    draw_text(canvas, 10, y + 10, name.upper(), (235, 235, 235), 1)
    for i, img in enumerate(row):
        f = img.shape[0] // T
        s = img[: T * f, : T * f].reshape(T, f, T, f, 3).mean(axis=(1, 3))
        canvas[y:y + T, 300 + i * (T + 8):300 + i * (T + 8) + T] = rc.q8_srgb(np.clip(s, 0, 1))
    y += T + 8
rc.png_write(H / "compat_sheet.png", np.concatenate([canvas, np.full(canvas.shape[:2] + (1,), 255, np.int32)], -1), 8)
(H / "compat_results.json").write_text(json.dumps(out, indent=1))
print("COMPAT_DONE")
