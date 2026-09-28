"""Is T_PaperBomb_N really DirectX green, as Unreal's flip-green-OFF import assumes?

A flipped green channel is silent: lighting simply looks wrong from one side and
nobody can point at a number.  This gets a number.

Method.  The study puts "cockling depressions 0.02-0.05 mm along the heaviest
strokes" into the normal map, so the ink tells us where the surface dips.  Let M be
the ink mask read from the BC map.  Where M rises as v increases, the surface is
descending into a depression, so dh/dv < 0 there.

    tangent-space normal  N = normalize(-dh/du, -dh/dv, 1)
    OpenGL green = N.y          -> green-0.5 correlates POSITIVELY with dM/dv
    DirectX green = -N.y        -> green-0.5 correlates NEGATIVELY with dM/dv

Red is not flipped by either convention, so corr(red-0.5, dM/du) must come out
POSITIVE either way: that is the control that the reasoning and the texture's
orientation are right.  If the control fails, the green verdict is not trusted.
"""
import json
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealReview"
TEX = PROJ / "Exports" / "PaperBomb" / "Textures"
OUT = HERE / "pbr_normal_green.json"
ISLAND = (16, 921, 16, 2032)     # front island, measured in pb_legibility.py: u px, v rows


def load(name):
    img = bpy.data.images.load(str(TEX / f"{name}.png"))
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(h, w, 4)


def grad(a):
    """Central differences: (d/d(row) = d/dv, d/d(col) = d/du)."""
    dv = np.zeros_like(a); du = np.zeros_like(a)
    dv[1:-1, :] = 0.5 * (a[2:, :] - a[:-2, :])
    du[:, 1:-1] = 0.5 * (a[:, 2:] - a[:, :-2])
    return dv, du


def corr(x, y):
    x = x - x.mean(); y = y - y.mean()
    d = float(np.sqrt((x * x).sum() * (y * y).sum()))
    return float((x * y).sum() / d) if d > 0 else 0.0


def main():
    u0, u1, v0, v1 = ISLAND
    bc = load("T_PaperBomb_BC")[v0:v1, u0:u1, :3]
    n = load("T_PaperBomb_N")[v0:v1, u0:u1, :3]

    lum = bc @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    mx = bc.max(2); mn = bc.min(2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    ink = ((lum < 0.35) & (sat < 0.18)).astype(np.float32)          # black sumi only: the heaviest strokes

    # smooth the mask a little so its gradient is the stroke EDGE, not single-texel noise
    k = np.ones((5, 5), np.float32) / 25.0
    sm = ink.copy()
    for _ in range(2):
        p = np.pad(sm, 2, mode="edge")
        sm = sum(p[i:i + sm.shape[0], j:j + sm.shape[1]] * k[i, j] for i in range(5) for j in range(5))

    dMdv, dMdu = grad(sm)
    green = n[:, :, 1] - 0.5
    red = n[:, :, 0] - 0.5

    rep = {"island_px": list(ISLAND), "note": "stored bytes / 255, colourspace forced Non-Color"}
    rep["normal_map_channel_stats"] = {
        "red_mean": round(float(n[:, :, 0].mean()), 5), "green_mean": round(float(n[:, :, 1].mean()), 5),
        "blue_mean": round(float(n[:, :, 2].mean()), 5),
        "red_std": round(float(n[:, :, 0].std()), 5), "green_std": round(float(n[:, :, 1].std()), 5),
        "blue_min": round(float(n[:, :, 2].min()), 5),
    }
    results = {}
    for label, thresh in (("all_edges", 0.0), ("strong_edges", 0.02), ("strongest_edges", 0.05)):
        mv = np.abs(dMdv) > thresh
        mu = np.abs(dMdu) > thresh
        results[label] = {
            "texels_v": int(mv.sum()), "texels_u": int(mu.sum()),
            "corr_green_vs_dMdv": round(corr(green[mv], dMdv[mv]), 5) if mv.sum() > 100 else None,
            "corr_red_vs_dMdu_CONTROL": round(corr(red[mu], dMdu[mu]), 5) if mu.sum() > 100 else None,
        }
    rep["correlations"] = results
    s = results["strong_edges"]
    ctrl = s["corr_red_vs_dMdu_CONTROL"]
    g = s["corr_green_vs_dMdv"]
    rep["control_valid"] = bool(ctrl is not None and ctrl > 0.05)
    rep["verdict"] = ("DirectX (green flipped) - matches Unreal flip_green OFF" if rep["control_valid"] and g < -0.05
                      else "OpenGL (green NOT flipped) - Unreal flip_green OFF would be WRONG"
                      if rep["control_valid"] and g > 0.05
                      else "inconclusive")
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=2))


main()
