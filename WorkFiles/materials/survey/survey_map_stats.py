"""Survey: read-only statistics of every in-scope shipped map (Blender 5.2 headless, numpy).

Run:  blender.exe -b --factory-startup --python survey_map_stats.py -- <out.json>
Reads PNGs only (never writes next to them). Output: one JSON with per-map stats and the
tint-contract checks (smoke bomb, black hat), and the lum-only reconstruction error for
the maps that were NOT built tint-ready (kunai wrap, paper bomb regions).
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
OUT = Path(sys.argv[sys.argv.index("--") + 1])
LUM = np.array([0.2126, 0.7152, 0.0722])


def load(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    ch = img.channels
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)[::-1]                      # top-down
    info = {"size": [w, h], "channels": ch, "depth": img.depth, "is_float": img.is_float,
            "file_format": img.file_format}
    bpy.data.images.remove(img)
    return px, info


def s2l(x):
    x = np.asarray(x, dtype=np.float64)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def l2s(x):
    x = np.clip(np.asarray(x, dtype=np.float64), 0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def pct(a, qs=(0.1, 1, 5, 50, 95, 99, 99.9)):
    a = np.asarray(a, dtype=np.float64).ravel()
    return {f"p{q}": round(float(np.percentile(a, q)), 6) for q in qs}


def lab(rgb_lin):
    """linear sRGB (D65) -> CIELAB."""
    m = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = rgb_lin @ m.T
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def de76(a_lin, b_lin):
    return np.linalg.norm(lab(a_lin) - lab(b_lin), axis=-1)


def bc_stats(px, mask=None):
    rgb = px[..., :3].astype(np.float64)
    lin = s2l(rgb)
    if mask is not None:
        lin = lin[mask]
        rgb = rgb[mask]
    else:
        lin = lin.reshape(-1, 3)
        rgb = rgb.reshape(-1, 3)
    y = lin @ LUM
    mean = lin.mean(0)
    out = {"texels": int(len(y)), "mean_linear": [round(float(v), 6) for v in mean],
           "mean_srgb": [round(float(v), 6) for v in l2s(mean)],
           "lum_linear": pct(y), "max_channel_linear": round(float(lin.max()), 6),
           "min_channel_linear": round(float(lin.min()), 6),
           "distinct_stored_levels_lum": int(len(np.unique(np.round(rgb @ LUM * 255))))}
    # a luminance-only tint model: albedo = mean * (y / mean_y)  -> how far from the map?
    my = float(mean @ LUM)
    recon = mean[None, :] * (y / my)[:, None]
    d = de76(recon, lin)
    out["lum_only_model_dE76"] = pct(d, (50, 90, 99, 99.9))
    out["lum_only_model_dE76_mean"] = round(float(d.mean()), 4)
    return out


def data_stats(px, nch=4):
    out = {}
    for i, c in enumerate("RGBA"[:nch]):
        out[c] = {"min": round(float(px[..., i].min()), 5), "max": round(float(px[..., i].max()), 5),
                  "mean": round(float(px[..., i].mean()), 5)}
    return out


R = {}
T = ROOT / "Exports"

# ---------------------------------------------------------------- shuriken + kunai steel
for form in ("FourPoint", "EightPoint", "SquarePlate", "SixPoint", "Spike", "HookedCross"):
    bc, i1 = load(T / "Shuriken/Textures" / f"T_Shuriken_{form}_BC.png")
    orm, i2 = load(T / "Shuriken/Textures" / f"T_Shuriken_{form}_ORM.png")
    R[f"Shuriken_{form}"] = {"BC_info": i1, "ORM_info": i2, "BC": bc_stats(bc),
                             "ORM": data_stats(orm, 3), "ORM_G_roughness": pct(orm[..., 1], (1, 50, 99))}
bc, i1 = load(T / "Shuriken/Textures/T_Kunai_Plain_BC.png")
orm, i2 = load(T / "Shuriken/Textures/T_Kunai_Plain_ORM.png")
R["Kunai_Plain_Steel"] = {"BC_info": i1, "ORM_info": i2, "BC": bc_stats(bc), "ORM": data_stats(orm, 3)}

# ---------------------------------------------------------------- kunai wrap
bc, i1 = load(T / "Shuriken/Textures/T_Kunai_Wrap_BC.png")
nat, i3 = load(T / "Shuriken/Textures/T_Kunai_Wrap_Natural_BC.png")
orm, i2 = load(T / "Shuriken/Textures/T_Kunai_Wrap_ORM.png")
let, i4 = load(T / "Shuriken/Textures/T_Kunai_Lettering.png")
wrap = {"BC_info": i1, "Natural_info": i3, "ORM_info": i2, "Lettering_info": i4,
        "BC": bc_stats(bc), "Natural_BC": bc_stats(nat), "ORM": data_stats(orm, 3),
        "Lettering": data_stats(let, 1)}
# ratio natural / dark, per texel (does the undyed option follow the dark one multiplicatively?)
ld, ln = s2l(bc[..., :3]).reshape(-1, 3) @ LUM, s2l(nat[..., :3]).reshape(-1, 3) @ LUM
wrap["natural_over_dark_lum_ratio"] = pct(ln / np.maximum(ld, 1e-6), (1, 50, 99))
wrap["corr_dark_natural_lum"] = round(float(np.corrcoef(ld, ln)[0, 1]), 4)
R["Kunai_Wrap"] = wrap

# ---------------------------------------------------------------- smoke bomb: Detail x Tint == BC ?
sb = json.loads((T / "SmokeBomb/SM_SmokeBomb.sockets.json").read_text())
tint = np.array(sb["material"]["tint_default_linear"])
bc, i1 = load(T / "SmokeBomb/Textures/T_SmokeBomb_BC.png")
det, i2 = load(T / "SmokeBomb/Textures/T_SmokeBomb_Detail.png")
orm, i3 = load(T / "SmokeBomb/Textures/T_SmokeBomb_ORM.png")
d = s2l(det[..., 0].astype(np.float64))
model = d[..., None] * tint[None, None, :]
bcl = s2l(bc[..., :3].astype(np.float64))
lv = np.abs(np.round(l2s(model) * 255) - np.round(bc[..., :3] * 255))
dE = de76(model.reshape(-1, 3), bcl.reshape(-1, 3))
mean_d = float(d.mean())
R["SmokeBomb_Cloth"] = {"BC_info": i1, "Detail_info": i2, "ORM_info": i3, "BC": bc_stats(bc),
                        "ORM": data_stats(orm, 4), "Detail_linear": pct(d), "Detail_mean_linear": round(mean_d, 6),
                        "Detail_distinct_levels": int(len(np.unique(np.round(det[..., 0] * 255)))),
                        "tint_default_linear": tint.tolist(),
                        "model_vs_BC_stored_levels_absdiff": {"max": int(lv.max()), "mean": round(float(lv.mean()), 4)},
                        "model_vs_BC_dE76": pct(dE, (50, 99, 99.9)),
                        "mean_colour_equiv_linear": [round(float(v), 6) for v in tint * mean_d],
                        "detail_over_mean": pct(d / mean_d, (0.1, 1, 50, 99, 99.9)),
                        "detail_over_mean_max": round(float((d / mean_d).max()), 3)}

# ---------------------------------------------------------------- black hat
bh = json.loads((T / "BlackHat/SM_BlackHat.sockets.json").read_text())["materials"]
for part, key in (("Straw", "M_BlackHat_Straw"), ("Cloth", "M_BlackHat_Cloth")):
    m = bh[key]
    tint = np.array(m["tint_default_linear"])
    bias, scale = m["detail_bias_default"], m["detail_scale_default"]
    bc, i1 = load(T / "BlackHat/Textures" / f"T_BlackHat_{part}_BC.png")
    det, i2 = load(T / "BlackHat/Textures" / f"T_BlackHat_{part}_Detail.png")
    orm, i3 = load(T / "BlackHat/Textures" / f"T_BlackHat_{part}_ORM.png")
    d = s2l(det[..., 0].astype(np.float64))
    k = bias + scale * d
    model = np.clip(tint[None, None, :] * k[..., None], 0, 1)
    bcl = s2l(bc[..., :3].astype(np.float64))
    lv = np.abs(np.round(l2s(model) * 255) - np.round(bc[..., :3] * 255))
    dE = de76(model.reshape(-1, 3), bcl.reshape(-1, 3))
    R[f"BlackHat_{part}"] = {"BC_info": i1, "Detail_info": i2, "ORM_info": i3, "BC": bc_stats(bc),
                             "ORM": data_stats(orm, 4), "Detail_linear": pct(d),
                             "Detail_distinct_levels": int(len(np.unique(np.round(det[..., 0] * 255)))),
                             "k_multiple_of_mean": pct(k, (0.1, 1, 50, 99, 99.9)), "k_mean": round(float(k.mean()), 5),
                             "k_max": round(float(k.max()), 4),
                             "model_vs_BC_stored_levels_absdiff": {"max": int(lv.max()), "mean": round(float(lv.mean()), 4)},
                             "model_vs_BC_dE76": pct(dE, (50, 99, 99.9))}

# ---------------------------------------------------------------- paper bomb
bc, i1 = load(T / "PaperBomb/Textures/T_PaperBomb_BC.png")
mm, i2 = load(T / "PaperBomb/Textures/T_PaperBomb_M.png")
orm, i3 = load(T / "PaperBomb/Textures/T_PaperBomb_ORM.png")
lin = s2l(bc[..., :3].astype(np.float64))
ink = mm[..., 2]
paper = ink < 0.01
# red vs black by hue among solid ink
solid = ink > 0.95
redness = lin[..., 0] / np.maximum(lin[..., 1] + lin[..., 2], 1e-5)
red = solid & (redness > 3.0)
blk = solid & (redness <= 3.0)
R["PaperBomb"] = {"BC_info": i1, "M_info": i2, "ORM_info": i3, "M": data_stats(mm, 3), "ORM": data_stats(orm, 3),
                  "ink_mask_B": pct(ink, (50, 90, 99)), "ink_coverage_fraction": round(float((ink > 0.5).mean()), 5),
                  "ink_partial_fraction": round(float(((ink > 0.02) & (ink < 0.98)).mean()), 5),
                  "paper_region": bc_stats(bc, paper), "solid_red_region": bc_stats(bc, red),
                  "solid_black_region": bc_stats(bc, blk)}
# is the paper's own chroma variation multiplicative-grey (a stain) or hue-shifting?
pl = lin[paper]
ratio = pl / pl.mean(0)
R["PaperBomb"]["paper_per_channel_ratio"] = {c: pct(ratio[:, i], (1, 50, 99)) for i, c in enumerate("RGB")}

OUT.write_text(json.dumps(R, indent=1))
print("WROTE", OUT)
