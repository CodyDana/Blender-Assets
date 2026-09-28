"""Recolour maps of the Snow Flower sword grip and sheath lacquer (ADDED 2026-09-26, the Snow Flower final pass).

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/unreal/materials/maps/make_snowflower_recolour_maps.py

The two builders (Scripts/SnowFlower/v4/build_sword_game.py, build_sheath.py) ship a TINT-READY Detail map per
recolourable part, in the fan's convention: sRGB-encoded linear d = (albedo luminance - a_lo) / (a_hi - a_lo) over the
part's texels, the part's texels plus 3 px of edge extension keep their values and every other texel holds ONE constant
(so derive_constants finds the coverage as 'every texel but the most common value').  This script:

    1  writes Exports/SnowFlower/v4/Textures/Recolour/<stem>16.png, a LOSSLESS 16-bit linear copy of each shipped
       Detail (d16 = round(65535 * sRGBdecode(level / 255)); gate: it re-encodes to the same 8-bit levels)
    2  writes Exports/SnowFlower/v4/Textures/Recolour/recolour_maps.json in the pack's schema with the v1 fields:
       Colour = the part's mean linear base colour over its texels (the builders' maps_report.json), Detail Bias =
       a_lo / lum(Colour), Detail Scale = (a_hi - a_lo) / lum(Colour), so Colour x (Bias + Scale x d) reproduces the
       baked albedo luminance with the part's mean chroma; Detail Mean / Highlight Ratio / Moments =
       recolour_common.fabric_constants over every texel (the fan's builder does the same)

Then run maps/derive_constants_snowflower.py (v2 constants: covered texels, Lightest Colour, mip compensation).
Re-run both after any Snow Flower rebuild: run_build.sh's maps_check refuses a stale chain.
Parts: Grip (MI_SnowFlower_Grip, the sword's cord wrap, 1024) and Sheath_Lacquer (MI_SnowFlower_Sheath_Lacquer, 2048;
its metal texels - the baked silver twigs, buds and second stem - keep their baked colour and metal through
M_Fabric_Master's 'Metal From ORM' switch, so its range a_lo..a_hi is taken over the dielectric lacquer only).
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import recolour_common as rc  # noqa: E402

VERSION = "1.0.0-snowflower"
GROUP = "SnowFlower"
TEX = rc.PROJECT / "Exports" / "SnowFlower" / "v4" / "Textures"
RECOLOUR = TEX / "Recolour"
SWORD_MAPS = rc.PROJECT / "WorkFiles" / "SnowFlower" / "v4" / "sword_build" / "maps_report.json"
SHEATH_MAPS = rc.PROJECT / "WorkFiles" / "SnowFlower" / "v4" / "sheath_build" / "maps_report.json"

PARTS = {
    "Grip": {"slot_material": "M_SnowFlower_Grip", "instance": "MI_SnowFlower_Grip", "detail": "T_SnowFlower_Wrap_Detail",
             "bc": "T_SnowFlower_Wrap_BC", "report": SWORD_MAPS, "key": "wrap",
             "a_lo": "detail_a_lo", "a_hi": "detail_a_hi", "tint": "default_tint_linear",
             "note": "the sword's two-cord grip wrap (near-black silk)"},
    "Sheath_Lacquer": {"slot_material": "M_SnowFlower_Sheath_Lacquer", "instance": "MI_SnowFlower_Sheath_Lacquer",
                       "detail": "T_SnowFlower_Sheath_Lacquer_Detail", "bc": "T_SnowFlower_Sheath_BC",
                       "report": SHEATH_MAPS, "key": None,
                       "a_lo": "lacquer_detail_a_lo", "a_hi": "lacquer_detail_a_hi",
                       "tint": "lacquer_dielectric_tint_linear",
                       "note": "the scabbard's marbled black lacquer (body and cavity); its metal texels use the baked colour"},
}


def main() -> int:
    try:
        import bpy
        blender = bpy.app.version_string
    except ImportError:
        blender = None
    out = {"schema": "ninjapack.recolour_maps/1", "item": GROUP, "generated": datetime.date.today().isoformat(),
           "generator": {"script": rc.rel(__file__), "script_sha256": rc.sha256(__file__),
                         "common_sha256": rc.sha256(rc.__file__), "version": VERSION, "blender": blender},
           "sidecar": {"files": ["Exports/SnowFlower/v4/SM_SnowFlower.sockets.json",
                                 "Exports/SnowFlower/v4/SM_SnowFlower_Sheath.sockets.json"]},
           "maps": {}, "parts": {}}
    ok = True
    for part, cfg in PARTS.items():
        rep = json.loads(Path(cfg["report"]).read_text(encoding="utf-8"))
        r = rep[cfg["key"]] if cfg["key"] else rep
        a_lo, a_hi = float(r[cfg["a_lo"]]), float(r[cfg["a_hi"]])
        tint = np.asarray(r[cfg["tint"]], np.float64)
        src = TEX / f"{cfg['detail']}.png"
        lev, bits, ctype = rc.png_read(src)
        if lev.ndim == 3:
            if not (np.all(lev[..., 0] == lev[..., 1]) and np.all(lev[..., 0] == lev[..., 2])):
                raise RuntimeError(f"{src}: not greyscale")
            lev = lev[..., 0]
        if bits != 8 or lev.shape[0] != lev.shape[1] or (lev.shape[0] & (lev.shape[0] - 1)):
            raise RuntimeError(f"{src}: expected a square power-of-two 8-bit map")
        dec = rc.s2l(lev / 255.0)
        d16 = np.rint(dec * 65535.0).astype(np.int64)
        name = f"{cfg['detail']}16"
        path16 = RECOLOUR / f"{name}.png"
        rc.png_write(path16, d16, 16)
        back, b16, _ = rc.png_read(path16)
        back8 = np.rint(rc.l2s(back / 65535.0) * 255.0).astype(np.int64)
        lossless = bool(np.array_equal(back, d16) and np.array_equal(back8, lev))
        ok &= lossless
        out["maps"][name] = {"file": rc.rel(path16), "sha256": rc.sha256(path16), "size": list(d16.shape),
                             "format": "PNG, 16-bit greyscale (colour type 0), no colour chunks, row 0 = top",
                             "encoding": "LINEAR: value / 65535 = the linear detail d (sRGB-decoded shipped Detail)",
                             "unreal_import": {"srgb": False, "compression": "TC_GRAYSCALE", "expected_pc_format": "G16",
                                               "sampler": "SAMPLERTYPE_LINEAR_GRAYSCALE",
                                               "mips": "TMGS_FROM_TEXTURE_GROUP", "address": "Wrap"},
                             "source": {"file": rc.rel(src), "sha256": rc.sha256(src),
                                        "stored_levels": int(len(np.unique(lev)))},
                             "recipe": "d16 = round(65535 * sRGBdecode(Detail8 / 255)); lossless (one code per 8-bit level)",
                             "gates": {"lossless_back_to_8bit": lossless}}
        lum = float(tint @ rc.LUM)
        bias, scale = a_lo / lum, (a_hi - a_lo) / lum
        n = bias + scale * dec
        kc = rc.fabric_constants(n)
        bcp = TEX / f"{cfg['bc']}.png"
        out["parts"][part] = {
            "slot_material": cfg["slot_material"], "instance": cfg["instance"], "master": "M_Fabric_Master",
            "detail_map": name, "base_colour_map_reference": {"file": rc.rel(bcp), "sha256": rc.sha256(bcp)},
            "params": {"Colour": [*[round(float(x), 6) for x in tint], 1.0], "Detail Bias": bias, "Detail Scale": scale,
                       "Detail Mean": kc["mean"], "Detail Highlight Ratio": kc["highlight_ratio"],
                       "Detail Moments Low": kc["moments_low"], "Detail Moments High": kc["moments_high"],
                       "Dark Detail Follow": rc.DARK_FOLLOW, "Albedo Ceiling": rc.ALBEDO_CEILING},
            "n_range": [kc["n_min"], kc["n_max"]], "fraction_n_le_1": kc["fraction_n_le_1"],
            "moment_samples": {"c": list(rc.MOMENT_POINTS), "low": kc["moment_samples_low"],
                               "high": kc["moment_samples_high"]},
            "builder_constants": {"a_lo": a_lo, "a_hi": a_hi, "tint_linear": [float(x) for x in tint],
                                  "report": rc.rel(cfg["report"])},
            "param_notes": {"Colour": "linear RGBA; the part's MEAN colour (the buyer's one colour); default = the baked "
                                      "part's mean linear albedo"},
            "note": cfg["note"],
            "derivation": "BaseColor = saturate(Colour x (DetailBias + DetailScale x Detail)): Colour = the part's mean "
                          "linear albedo, Bias = a_lo / lum(Colour), Scale = (a_hi - a_lo) / lum(Colour), so the default "
                          "reproduces the baked luminance with the mean chroma. The v1 fields are "
                          "recolour_common.fabric_constants over every texel of the Detail16; recolour_constants.json (v2) "
                          "is written by Scripts/unreal/materials/maps/derive_constants_snowflower.py"}
        print(f"[SF-RECOLOUR] {part}: {d16.shape[0]}px lossless={lossless} bias {bias:.5f} scale {scale:.5f} "
              f"mean n {kc['mean']:.4f} highlight {kc['highlight_ratio']:.4f}", flush=True)
    out["pass"] = ok
    rc.write_json(RECOLOUR / "recolour_maps.json", out)
    print(f"[SF-RECOLOUR] wrote {rc.rel(RECOLOUR / 'recolour_maps.json')} pass={ok}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    code = main()
    try:
        import bpy  # noqa: F401
        sys.stdout.flush()
        import os
        os._exit(code)
    except ImportError:
        sys.exit(code)
