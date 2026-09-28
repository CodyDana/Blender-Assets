"""Finalise: the heels' tint-ready Detail maps for the pack colour system (replaces the round 1 draft hb_i_recolour.py).

    blender -b Assets/SnowFlowerHeels/SnowFlowerHeels_Build.blend --factory-startup --python Scripts/SnowFlowerHeels/fin_recolour_maps.py

For each recolourable part (M_Fabric_Master): Leather (the upper, lining, strap, sole, stiletto cover, binding and
crackle medallion - one slot) and Insole (the printed insole):
  * covered texels = texels whose centre lies in a right-shoe triangle of the slot (the left shoe shares them, UV +1)
  * Y = linear luminance of the shipped BC; a_lo / a_hi = p0.1 of the non-zero Y / p99.9 of Y over covered texels
  * d = clip((Y - a_lo) / (a_hi - a_lo), 0, 1) on covered texels plus a 3 px edge extension; every other texel holds ONE
    constant (the covered mean), so the pack's derive_constants finds the coverage as "every texel but the most common value"
  * written as a LOSSLESS 16-bit linear greyscale PNG, square power of two (the pack's derive step requires square maps:
    the 2048 x 1024 insole detail is box-filtered along U to 1024 x 1024; UVs are normalised, so it maps the same)
  * Colour (tint) = mean linear BC over covered texels
Writes Exports/SnowFlowerHeels/Textures/Recolour/T_SnowFlowerHeels_<Part>_Detail16.png and
WorkFiles/SnowFlowerHeels/final/maps_report.json (a_lo, a_hi, tint, coverage). Saves no blend.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts" / "unreal" / "materials" / "maps"))
import recolour_common as rc  # noqa: E402  (read-only use of the pack's PNG / colour helpers)

TEX = ROOT / "Exports" / "SnowFlowerHeels" / "Textures"
OUT = TEX / "Recolour"
REPORT = ROOT / "WorkFiles" / "SnowFlowerHeels" / "final" / "maps_report.json"
PARTS = {"Leather": {"slot": 0, "tile": (0.0, 0.0), "size": (2048, 2048)},
         "Insole": {"slot": 1, "tile": (0.0, 1.0), "size": (2048, 1024)}}


def raster(uvtris, w, h):
    mask = np.zeros((h, w), dtype=bool)
    P = np.asarray(uvtris, dtype=np.float64) * np.array([w, h])
    for t in P:
        x0 = max(int(math.floor(t[:, 0].min() - 0.5)), 0)
        x1 = min(int(math.ceil(t[:, 0].max() - 0.5)), w - 1)
        y0 = max(int(math.floor(t[:, 1].min() - 0.5)), 0)
        y1 = min(int(math.ceil(t[:, 1].max() - 0.5)), h - 1)
        if x1 < x0 or y1 < y0:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = t
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
        mask[y0:y1 + 1, x0:x1 + 1] |= (l1 >= -1e-7) & (l2 >= -1e-7) & (1 - l1 - l2 >= -1e-7)
    return mask


def grow(mask, px):
    m = mask.copy()
    for _ in range(px):
        n = m.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            n |= np.roll(np.roll(m, dy, 0), dx, 1)
        m = n
    return m


def main():
    ob = bpy.data.objects["SK_SnowFlowerHeels"]
    me = ob.data
    me.calc_loop_triangles()
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    tri_uv = np.array([[uv[l] for l in t.loops] for t in me.loop_triangles])
    tri_mat = np.array([t.material_index for t in me.loop_triangles])
    report = {"note": "finalise 2026-09-27; inputs of Scripts/unreal/materials/maps/make_snowflowerheels_recolour_maps.py",
              "parts": {}}
    OUT.mkdir(parents=True, exist_ok=True)
    for part, cfg in PARTS.items():
        w, h = cfg["size"]
        q = tri_uv[tri_mat == cfg["slot"]] - np.array(cfg["tile"])
        q = q[(q[:, :, 0].min(1) >= -1e-4) & (q[:, :, 0].max(1) <= 1 + 1e-4)]          # right shoe
        cov = raster(q, w, h)                                                          # row 0 = V 0 (bottom)
        stored = rc.load_png_bpy(TEX / f"T_SnowFlowerHeels_{part}_BC.png")            # row 0 = top, 8-bit levels / 255
        bc = rc.s2l(np.rint(stored[..., :3] * 255.0) / 255.0)[::-1]                   # row 0 = bottom
        Y = bc @ rc.LUM
        # a_lo from the lit texels: a few covered texels bake to pure 0 (hidden ornament footprints), and a zero Detail
        # Bias leaves the pack's v2 twin 3.5e-7 off the v1 contract (derive_constants' gate is 1e-9)
        a_lo = max(float(np.percentile(Y[cov & (Y > 0)], 0.1)), 1e-4)
        a_hi = float(np.percentile(Y[cov], 99.9))
        report_zero = float((Y[cov] <= 0).mean())
        tint = bc[cov].mean(0)
        d = np.clip((Y - a_lo) / max(a_hi - a_lo, 1e-9), 0.0, 1.0)
        keep = grow(cov, 3)
        if w != h:                                                                   # 2048 x 1024 -> 1024 x 1024
            f = w // h
            d = d.reshape(h, h, f).mean(2)
            keep = keep.reshape(h, h, f).any(2)
            cov_sq = cov.reshape(h, h, f).any(2)
        else:
            cov_sq = cov
        fill = float(d[cov_sq].mean())
        d16 = np.rint(np.where(keep, d, fill) * 65535.0).astype(np.int64)
        f16 = int(np.rint(fill * 65535.0))
        d16[~keep] = f16
        # the fill must be the single most common value and must not occur inside the coverage (derive_constants' rule)
        inside = d16[keep] == f16
        if inside.any():
            d16[keep & (d16 == f16)] = f16 + 1
        vals, cnts = np.unique(d16, return_counts=True)
        assert int(vals[np.argmax(cnts)]) == f16, "fill is not the most common value"
        path = OUT / f"T_SnowFlowerHeels_{part}_Detail16.png"
        rc.png_write(path, d16[::-1], 16)                                             # PNG row 0 = top
        back, bits16, _ = rc.png_read(path)
        report["parts"][part] = {"detail16": rc.rel(path), "sha256": rc.sha256(path), "size": list(d16.shape),
                                 "a_lo": a_lo, "a_hi": a_hi, "tint_linear": [float(x) for x in tint],
                                 "coverage_fraction": float(cov.mean()), "kept_fraction": float(keep.mean()),
                                 "covered_texels_at_zero_fraction": report_zero,
                                 "fill_d16": f16, "lossless_roundtrip": bool(np.array_equal(back, d16[::-1])),
                                 "bits": int(bits16),
                                 "base_colour": {"file": rc.rel(TEX / f"T_SnowFlowerHeels_{part}_BC.png"),
                                                 "sha256": rc.sha256(TEX / f"T_SnowFlowerHeels_{part}_BC.png")}}
        print("FIN_RECOLOUR", part, json.dumps({k: v for k, v in report["parts"][part].items() if k != "base_colour"}))
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("FIN_RECOLOUR_OK")


main()
