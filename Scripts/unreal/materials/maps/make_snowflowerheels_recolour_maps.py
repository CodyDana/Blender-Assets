"""Recolour maps of the Snow Flower heels' leather and insole (ADDED 2026-09-27, the heels' finalise pass).

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/unreal/materials/maps/make_snowflowerheels_recolour_maps.py

The heels builder (Scripts/SnowFlowerHeels/fin_recolour_maps.py) ships a TINT-READY 16-bit LINEAR Detail map per
recolourable part - d = (albedo luminance - a_lo) / (a_hi - a_lo) over the part's covered texels plus 3 px of edge
extension, every other texel ONE constant (so derive_constants finds the coverage as 'every texel but the most common
value') - and WorkFiles/SnowFlowerHeels/final/maps_report.json (a_lo, a_hi, the mean linear tint).  This script checks
each Detail16 (16-bit greyscale, square power of two, sha256 = the report's) and writes
Exports/SnowFlowerHeels/Textures/Recolour/recolour_maps.json in the pack's schema with the v1 fields, exactly as the
Snow Flower's generator does: Colour = the part's mean linear base colour, Detail Bias = a_lo / lum(Colour), Detail
Scale = (a_hi - a_lo) / lum(Colour), Detail Mean / Highlight Ratio / Moments = recolour_common.fabric_constants.

Then run maps/derive_constants_snowflowerheels.py.  Re-run both after any heels rebuild (maps_check refuses a stale chain).
Parts: Leather (MI_SnowFlowerHeels_Leather, 2048) and Insole (MI_SnowFlowerHeels_Insole, 1024: the 2048 x 1024 insole
detail box-filtered along U).  The Metal slot (antiqued silver, pearl, patent toe cap) is M_Steel_Master: Steel Tint only.
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

VERSION = "1.0.0-snowflowerheels"
GROUP = "SnowFlowerHeels"
TEX = rc.PROJECT / "Exports" / "SnowFlowerHeels" / "Textures"
RECOLOUR = TEX / "Recolour"
MAPS_REPORT = rc.PROJECT / "WorkFiles" / "SnowFlowerHeels" / "final" / "maps_report.json"
PARTS = {
    "Leather": {"slot_material": "M_SnowFlowerHeels_Leather", "instance": "MI_SnowFlowerHeels_Leather",
                "detail": "T_SnowFlowerHeels_Leather_Detail16", "bc": "T_SnowFlowerHeels_Leather_BC",
                "note": "the black leather: upper, lining, ankle strap, sole, heel cover, binding and crackle medallion"},
    "Insole": {"slot_material": "M_SnowFlowerHeels_Insole", "instance": "MI_SnowFlowerHeels_Insole",
               "detail": "T_SnowFlowerHeels_Insole_Detail16", "bc": "T_SnowFlowerHeels_Insole_BC",
               "note": "the blossom-printed insole (the print keeps its luminance; the tint recolours it)"},
}


def main() -> int:
    try:
        import bpy
        blender = bpy.app.version_string
    except ImportError:
        blender = None
    rep = json.loads(MAPS_REPORT.read_text(encoding="utf-8"))
    out = {"schema": "ninjapack.recolour_maps/1", "item": GROUP, "generated": datetime.date.today().isoformat(),
           "generator": {"script": rc.rel(__file__), "script_sha256": rc.sha256(__file__),
                         "common_sha256": rc.sha256(rc.__file__), "version": VERSION, "blender": blender,
                         "builder": "Scripts/SnowFlowerHeels/fin_recolour_maps.py",
                         "builder_report": {"file": rc.rel(MAPS_REPORT), "sha256": rc.sha256(MAPS_REPORT)}},
           "sidecar": {"files": ["Exports/SnowFlowerHeels/SK_SnowFlowerHeels.skeletal.json",
                                 "Exports/SnowFlowerHeels/SK_SnowFlowerHeels.garment.json"]},
           "maps": {}, "parts": {}}
    ok = True
    for part, cfg in PARTS.items():
        r = rep["parts"][part]
        path16 = RECOLOUR / f"{cfg['detail']}.png"
        d16, bits, ctype = rc.png_read(path16)
        gates = {"sha256_matches_builder": rc.sha256(path16) == r["sha256"], "bits_16": bits == 16,
                 "greyscale": d16.ndim == 2,
                 "square_power_of_two": d16.ndim == 2 and d16.shape[0] == d16.shape[1]
                 and not (d16.shape[0] & (d16.shape[0] - 1))}
        vals, cnts = np.unique(d16, return_counts=True)
        fill = int(vals[np.argmax(cnts)])
        gates["fill_is_builder_fill"] = fill == int(r["fill_d16"])
        ok &= all(gates.values())
        d = d16 / 65535.0
        cov = d16 != fill
        a_lo, a_hi = float(r["a_lo"]), float(r["a_hi"])
        tint = np.asarray(r["tint_linear"], np.float64)
        lum = float(tint @ rc.LUM)
        bias, scale = a_lo / lum, (a_hi - a_lo) / lum
        n = bias + scale * d
        kc = rc.fabric_constants(n)
        out["maps"][cfg["detail"]] = {
            "file": rc.rel(path16), "sha256": rc.sha256(path16), "size": list(d16.shape),
            "format": "PNG, 16-bit greyscale (colour type 0), no colour chunks, row 0 = top",
            "encoding": "LINEAR: value / 65535 = the linear detail d",
            "unreal_import": {"srgb": False, "compression": "TC_GRAYSCALE", "expected_pc_format": "G16",
                              "sampler": "SAMPLERTYPE_LINEAR_GRAYSCALE", "mips": "TMGS_FROM_TEXTURE_GROUP",
                              "address": "Wrap"},
            "source": {"builder_report": rc.rel(MAPS_REPORT), "covered_fraction": float(cov.mean())},
            "recipe": "d = clip((lum(BC linear) - a_lo) / (a_hi - a_lo)) over covered texels + 3 px, one constant elsewhere",
            "gates": gates}
        bcp = TEX / f"{cfg['bc']}.png"
        out["parts"][part] = {
            "slot_material": cfg["slot_material"], "instance": cfg["instance"], "master": "M_Fabric_Master",
            "detail_map": cfg["detail"], "base_colour_map_reference": {"file": rc.rel(bcp), "sha256": rc.sha256(bcp)},
            "params": {"Colour": [*[round(float(x), 6) for x in tint], 1.0], "Detail Bias": bias, "Detail Scale": scale,
                       "Detail Mean": kc["mean"], "Detail Highlight Ratio": kc["highlight_ratio"],
                       "Detail Moments Low": kc["moments_low"], "Detail Moments High": kc["moments_high"],
                       "Dark Detail Follow": rc.DARK_FOLLOW, "Albedo Ceiling": rc.ALBEDO_CEILING},
            "n_range": [kc["n_min"], kc["n_max"]], "fraction_n_le_1": kc["fraction_n_le_1"],
            "moment_samples": {"c": list(rc.MOMENT_POINTS), "low": kc["moment_samples_low"],
                               "high": kc["moment_samples_high"]},
            "builder_constants": {"a_lo": a_lo, "a_hi": a_hi, "tint_linear": [float(x) for x in tint],
                                  "report": rc.rel(MAPS_REPORT)},
            "param_notes": {"Colour": "linear RGBA; the part's MEAN colour (the buyer's one colour); default = the baked "
                                      "part's mean linear albedo"},
            "note": cfg["note"],
            "derivation": "BaseColor = saturate(Colour x (DetailBias + DetailScale x Detail)) as the Snow Flower's parts; "
                          "the v2 constants are written by maps/derive_constants_snowflowerheels.py"}
        print(f"[SFH-RECOLOUR] {part}: {d16.shape} gates {gates} bias {bias:.5f} scale {scale:.5f} "
              f"mean n {kc['mean']:.4f} highlight {kc['highlight_ratio']:.4f}", flush=True)
    out["pass"] = bool(ok)
    rc.write_json(RECOLOUR / "recolour_maps.json", out)
    print(f"[SFH-RECOLOUR] wrote {rc.rel(RECOLOUR / 'recolour_maps.json')} pass={ok}", flush=True)
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
