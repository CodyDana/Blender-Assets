"""V4 sheen calibration, comparison (Blender headless, reads EXRs only).

For every Unreal Fuzz Colour / Cloth amount candidate: ratio(N.V bin) = L(candidate) / L(Cloth amount 0) under the key
and the rim light; Blender's ratio = L(sheen 0.35) / L(sheen 0). Error = pixel-weighted RMS of log(ratio_UE /
ratio_Blender) over lit bins of both lights. Also reports the absolute sheen-off match (the Default-Lit part of the
two renderers) so the comparison's baseline is visible.

    blender -b --factory-startup --python sheen_compare.py -- <dir with the EXRs>
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

D = Path(sys.argv[sys.argv.index("--") + 1])
RES = 512


def load(path):
    img = bpy.data.images.load(str(path))
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)


def profile(a):
    h, w = a.shape[:2]
    lum = a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722
    ys, xs = np.mgrid[0:h, 0:w]
    u = (xs + 0.5) / w * 2 - 1
    v = (ys + 0.5) / h * 2 - 1
    r2 = u * u + v * v
    inside = r2 < 0.995
    nv = np.sqrt(np.clip(1 - r2, 0, 1))
    bins = np.linspace(0, 1, 11)
    vals, ns = [], []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = inside & (nv >= lo) & (nv < hi)
        vals.append(float(lum[m].mean()) if m.any() else 0.0)
        ns.append(int(m.sum()))
    return np.array(vals), np.array(ns), float(lum[inside].mean())


ref = json.loads((D / "blender_sheen_reference.json").read_text())
frames = json.loads((D / "ue_sheen_frames.json").read_text())["frames"]
out = {"blender": {}, "ue_off": {}, "candidates": {}}
bl = {}
for light in ("key", "rim"):
    on, n, mon = profile(load(D / f"blender_sheen_{light}_on.exr"))
    off, _, moff = profile(load(D / f"blender_sheen_{light}_off.exr"))
    bl[light] = (on, off, n)
    out["blender"][light] = {"ratio_bins": [round(x, 4) for x in np.where(off > 1e-6, on / np.maximum(off, 1e-12), 0)],
                             "mean_ratio": round(mon / moff, 4)}
ue = {}
for key, f in frames.items():
    ue[key] = profile(load(f["exr"]))
for light in ("key", "rim"):
    on, off, n = bl[light]
    uoff = ue[f"{light}_off"][0]
    lit = (off > 1e-4) & (uoff > 1e-6)
    # shape of the no-sheen baseline: UE vs Blender after normalising the means (units differ)
    s = (uoff[lit] * n[lit]).sum() / (off[lit] * n[lit]).sum()
    out["ue_off"][light] = {"shape_ratio_bins": [round(x, 3) for x in (uoff / np.maximum(off * s, 1e-12))[lit]],
                            "unit_scale": s}
labels = sorted({k.split("_", 1)[1] for k in frames if not k.endswith("_off")})
for lab in labels:
    errs, w, rec = 0.0, 0, {}
    for light in ("key", "rim"):
        on, off, n = bl[light]
        uon, uoff = ue[f"{light}_{lab}"][0], ue[f"{light}_off"][0]
        lit = (off > 1e-4) & (uoff > 1e-6)
        rb = on[lit] / off[lit]
        ru = uon[lit] / uoff[lit]
        e = np.log(ru / rb)
        errs += float((e * e * n[lit]).sum())
        w += int(n[lit].sum())
        rec[light] = {"ue_ratio_bins": [round(x, 4) for x in ru], "mean_ratio": round(ue[f"{light}_{lab}"][2] / ue[f"{light}_off"][2], 4)}
    f = frames[f"key_{lab}"]
    rec.update({"k": f["k"], "amount": f["amount"], "rms_log_ratio_error": round(math.sqrt(errs / max(w, 1)), 4)})
    out["candidates"][lab] = rec
# the Default-Lit alternative (no Cloth lobe at all): UE ratio 1 everywhere
errs, w = 0.0, 0
for light in ("key", "rim"):
    on, off, n = bl[light]
    uoff = ue[f"{light}_off"][0]
    lit = (off > 1e-4) & (uoff > 1e-6)
    e = -np.log(on[lit] / off[lit])
    errs += float((e * e * n[lit]).sum())
    w += int(n[lit].sum())
out["default_lit_no_sheen_rms_log_ratio_error"] = round(math.sqrt(errs / w), 4)
best = min(out["candidates"].items(), key=lambda kv: kv[1]["rms_log_ratio_error"])
out["best"] = {"label": best[0], **{k: best[1][k] for k in ("k", "amount", "rms_log_ratio_error")},
               "sheen_colour": [round(c * best[1]["k"], 4) for c in (0.62, 0.60, 0.56)]}
out["current_default"] = out["candidates"].get("k1.0_a0.35") or out["candidates"].get("k1_a0.35")
(D / "sheen_compare.json").write_text(json.dumps(out, indent=1))
print("SHEEN_COMPARE", json.dumps(out["best"]))
for lab, r in sorted(out["candidates"].items(), key=lambda kv: kv[1]["rms_log_ratio_error"])[:8]:
    print(lab, r["rms_log_ratio_error"], r["key"]["mean_ratio"], r["rim"]["mean_ratio"])
print("default lit (no sheen) error", out["default_lit_no_sheen_rms_log_ratio_error"], "current k1.0_a0.35", out["current_default"]["rms_log_ratio_error"])
print("blender", out["blender"]["key"]["mean_ratio"], out["blender"]["rim"]["mean_ratio"])
print("ue_off shape", out["ue_off"])
