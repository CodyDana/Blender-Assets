"""Prototype numpy twin of MF_TintDetail + MF_AlbedoRollOff (design check, read-only).

Evaluates the designed recolour on the three shipped tint-ready parts for the V3 stress colours and
reports the V3 gate figures. Run: blender -b --factory-startup --python survey_twin_prototype.py -- out.json
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Exports")
OUT = Path(sys.argv[sys.argv.index("--") + 1])
LUM = np.array([0.2126, 0.7152, 0.0722])
COLOURS = {"default": None, "white": [0.8, 0.8, 0.8], "cream": [0.8, 0.7, 0.5], "pastel_pink": [0.9, 0.6, 0.7],
           "saturated_red": [0.8, 0.02, 0.02], "saturated_blue": [0.02, 0.05, 0.8], "yellow": [0.9, 0.8, 0.05],
           "mid_grey": [0.18, 0.18, 0.18], "near_black": [0.01, 0.01, 0.01]}
CEIL, KNEE, LIMIT = 0.9, 0.85, 0.95
FOLLOW = float(sys.argv[sys.argv.index("--") + 2]) if len(sys.argv) > sys.argv.index("--") + 2 else 0.5


def grey(path, step):
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::step, ::step, 0].astype(np.float64)


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def l2s(x):
    x = np.clip(x, 0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def cubic_fit(n, mask):
    cs = np.array([0.0, 0.5, 1.0, 1.5])
    vals = np.array([np.mean(np.where(mask, np.power(np.maximum(n, 1e-6), c), 0.0)) for c in cs])
    return np.polyfit(cs, vals, 3)          # exact through the 4 points


def rolloff(a):
    m = a.max(axis=-1, keepdims=True)
    t = np.maximum(m - KNEE, 0.0)
    mm = KNEE + (LIMIT - KNEE) * (1 - np.exp(-t / (LIMIT - KNEE)))
    return np.where(m > KNEE, a * (mm / np.maximum(m, 1e-9)), a)


def model(n, colour, mean_n, hr, lo_fit, hi_fit, strength=1.0):
    c = np.array(colour, dtype=np.float64)
    H = np.log(CEIL / max(c.max(), 1e-4)) / np.log(hr)
    c_hi = min(strength, max(H, 0.0))
    c_lo = strength + (c_hi - strength) * FOLLOW
    npr = np.where(n <= 1.0, np.power(np.maximum(n, 1e-6), c_lo), np.power(np.maximum(n, 1e-6), c_hi))
    e = np.polyval(lo_fit, c_lo) + np.polyval(hi_fit, c_hi)
    a = c[None, :] * (npr * (mean_n / e))[:, None]
    return rolloff(a), {"H": round(float(H), 4), "C_hi": round(c_hi, 4), "C_lo": round(c_lo, 4)}


parts = {}
sb = json.loads((ROOT / "SmokeBomb/SM_SmokeBomb.sockets.json").read_text())["material"]
d = s2l(grey(ROOT / "SmokeBomb/Textures/T_SmokeBomb_Detail.png", 2))
m = d.mean()
parts["SmokeBomb_Cloth"] = (d / m, [t * m for t in sb["tint_default_linear"]])
bh = json.loads((ROOT / "BlackHat/SM_BlackHat.sockets.json").read_text())["materials"]
for part in ("Straw", "Cloth"):
    mm = bh[f"M_BlackHat_{part}"]
    d = s2l(grey(ROOT / f"BlackHat/Textures/T_BlackHat_{part}_Detail.png", 1))
    parts[f"BlackHat_{part}"] = (mm["detail_bias_default"] + mm["detail_scale_default"] * d, mm["tint_default_linear"])

res = {"dark_detail_follow": FOLLOW, "ceiling": CEIL, "knee": KNEE, "limit": LIMIT}
for name, (n, cdef) in parts.items():
    n = n.ravel()
    mean_n = float(n.mean())
    hr = float(np.percentile(n, 99.9))
    lo_fit, hi_fit = cubic_fit(n, n <= 1.0), cubic_fit(n, n > 1.0)
    base, _ = model(n, cdef, mean_n, hr, lo_fit, hi_fit)
    exact = np.array(cdef)[None, :] * n[:, None]
    r = {"highlight_ratio": round(hr, 4), "mean_n": round(mean_n, 6),
         "default_max_abs_vs_contract_linear": float(np.abs(base - exact).max())}
    ly0 = np.log(np.maximum(exact @ LUM, 1e-6))
    for cname, col in COLOURS.items():
        if col is None:
            continue
        a, info = model(n, col, mean_n, hr, lo_fit, hi_fit)
        y = a @ LUM
        ly = np.log(np.maximum(y, 1e-6))
        s8 = np.round(l2s(a) * 255)
        dom = int(np.argmax(col))
        ch = s8[:, dom]
        lo_, hi_ = np.percentile(ch, 1), np.percentile(ch, 99)
        occ = np.unique(ch[(ch >= lo_) & (ch <= hi_)])
        gap = int(np.diff(occ).max()) if len(occ) > 1 else 0
        r[cname] = {**info, "clip_frac": round(float((a >= 0.949).any(axis=1).mean()), 5),
                    "max_gap_levels": gap, "levels_used": int(len(occ)),
                    "corr_logL": round(float(np.corrcoef(ly, ly0)[0, 1]), 4),
                    "std_ratio_logL": round(float(ly.std() / ly0.std()), 3),
                    "mean_albedo": [round(float(v), 4) for v in a.mean(0)],
                    "target_mean": [round(float(v) * mean_n, 4) for v in col]}
    res[name] = r
OUT.write_text(json.dumps(res, indent=1))
print("WROTE", OUT)
