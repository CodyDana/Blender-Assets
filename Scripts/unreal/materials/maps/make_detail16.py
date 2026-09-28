"""T_SmokeBomb_Detail16 / T_BlackHat_Straw_Detail16 / T_BlackHat_Cloth_Detail16: lossless 16-bit LINEAR copies of the
shipped sRGB-encoded Detail maps, plus each item's Recolour/recolour_maps.json (MATERIAL_PLAN.md 5.2, D3).

Why: the shipped Detail maps are 8-bit greyscale PNGs holding sRGB-ENCODED linear detail, meant for Unreal's G8 + sRGB.
Engine source (Texture.cpp) rebuilds G8 + sRGB as BGRA8 on every target platform, 4 bytes per texel (the smoke bomb's
4096 map is ~85 MiB with mips).  A 16-bit linear greyscale PNG imports as G16 (TC_Grayscale, sRGB OFF): 2 bytes per
texel, decoded exactly, mips built in linear light.  d16 = round(65535 * sRGBdecode(d8 / 255)) is LOSSLESS: every
8-bit level maps to its own 16-bit code, so nothing about the item's contract changes.

Read-only on every shipped file; writes only NEW files under Exports/<Item>/Textures/Recolour/ and a gate report under
WorkFiles/materials/maps/.  Never saves a .blend.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/unreal/materials/maps/make_detail16.py -- [--items SmokeBomb,BlackHat]
"""
from __future__ import annotations

import datetime
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import recolour_common as rc  # noqa: E402

VERSION = "1.0.0"

PARTS = {
    "SmokeBomb": {
        "sidecar": "SmokeBomb/SM_SmokeBomb.sockets.json",
        "parts": {"Cloth": {"instance": "MI_SmokeBomb_Cloth", "detail": "SmokeBomb/Textures/T_SmokeBomb_Detail.png",
                            "bc": "SmokeBomb/Textures/T_SmokeBomb_BC.png",
                            "out": "SmokeBomb/Textures/Recolour/T_SmokeBomb_Detail16.png"}},
    },
    "BlackHat": {
        "sidecar": "BlackHat/SM_BlackHat.sockets.json",
        "parts": {p: {"instance": f"MI_BlackHat_{p}", "detail": f"BlackHat/Textures/T_BlackHat_{p}_Detail.png",
                      "bc": f"BlackHat/Textures/T_BlackHat_{p}_BC.png",
                      "out": f"BlackHat/Textures/Recolour/T_BlackHat_{p}_Detail16.png"} for p in ("Straw", "Cloth")},
    },
}


def log(msg):
    print(f"[detail16] {msg}", flush=True)


def contract(item: str, part: str, sidecar: dict, d: np.ndarray):
    """(Colour, Bias, Scale, derivation text) in the mean-colour form, from the item's own sidecar."""
    if item == "SmokeBomb":
        tint = np.array(sidecar["material"]["tint_default_linear"], np.float64)
        m = float(d.mean())
        return (tint * m, 0.0, 1.0 / m,
                f"sidecar: BaseColor = Detail x Tint, Tint = {list(tint)}.  Mean-colour form: Colour = Tint x mean(d), "
                f"Bias = 0, Scale = 1 / mean(d), mean(d) = {m!r} over the whole written Detail16 (so Colour x Scale = "
                f"Tint exactly, for any mean)", {"tint_default_linear": list(tint), "mean_d": m})
    mm = sidecar["materials"][f"M_BlackHat_{part}"]
    return (np.array(mm["tint_default_linear"], np.float64), float(mm["detail_bias_default"]),
            float(mm["detail_scale_default"]),
            "sidecar: BaseColor = saturate(Tint x (DetailBias + DetailScale x Detail)), Tint = the part's MEAN colour "
            "(sidecar values; BLACKHAT_REPORT.md's Bias/Scale table is stale)",
            {"tint_default_linear": mm["tint_default_linear"], "detail_bias_default": mm["detail_bias_default"],
             "detail_scale_default": mm["detail_scale_default"], "specular_scale": mm["specular_scale"]})


def run_part(item, part, cfg, sidecar) -> tuple:
    t0 = time.time()
    src, bc_path, out = rc.EXPORTS / cfg["detail"], rc.EXPORTS / cfg["bc"], rc.EXPORTS / cfg["out"]
    if "/Recolour/" not in out.as_posix():
        raise RuntimeError(f"{out}: generators write only inside a Recolour/ folder (NEW files)")
    lv = rc.load_levels8(src)
    grey_rgb = bool((lv[..., 0] == lv[..., 1]).all() and (lv[..., 0] == lv[..., 2]).all())
    d8 = lv[..., 0].astype(np.int32)
    lin = rc.s2l(d8 / 255.0)
    d16 = rc.q16_linear(lin)
    # --- lossless: every stored level -> its own 16-bit code, and the code decodes back within half a 16-bit step
    levels = np.unique(d8)
    codes = rc.q16_linear(rc.s2l(levels / 255.0))
    lossless = {"levels_present": int(len(levels)), "distinct_codes": int(len(np.unique(codes))),
                "injective": bool(len(np.unique(codes)) == len(levels)),
                "max_abs_decode_error": float(np.abs(d16 / 65535.0 - lin).max()),
                "limit_half_step": 0.5 / 65535.0}
    lossless["pass"] = bool(lossless["injective"] and lossless["max_abs_decode_error"] <= lossless["limit_half_step"])
    rc.png_write(out, d16, 16)
    # --- read back through two independent decoders
    back, bits, ctype = rc.png_read(out)
    bpy_back = rc.load_png_bpy(out)[..., 0].astype(np.float64)
    readback = {"own_decoder_equal": bool(np.array_equal(back, d16)), "bits": bits, "colour_type": ctype,
                "blender_decoder_max_abs": float(np.abs(bpy_back - d16 / 65535.0).max()),
                "png_chunks": rc.png_chunks(out)}
    readback["pass"] = bool(readback["own_decoder_equal"] and bits == 16 and ctype == 0
                            and readback["blender_decoder_max_abs"] < 1e-6
                            and not any(c in ("sRGB", "gAMA", "cHRM", "iCCP") for c in readback["png_chunks"]))
    del bpy_back, back
    d = d16 / 65535.0
    colour, bias, scale, derivation, source_values = contract(item, part, sidecar, d)
    n = bias + scale * d
    k = rc.fabric_constants(n)
    # --- default: Colour x n vs the shipped BC, and vs the item's own 8-bit Detail path
    bc = rc.load_levels8(bc_path)[..., :3]
    if bc.shape[:2] != d.shape:
        raise RuntimeError(f"{bc_path} is {bc.shape[:2]}, Detail is {d.shape}")
    albedo = np.clip(colour[None, None, :] * n[..., None], 0.0, 1.0)
    model8 = rc.q8_srgb(albedo)
    default_vs_bc = rc.level_diff_stats(model8, bc)
    n8 = bias + scale * lin
    via8 = rc.q8_srgb(np.clip(colour[None, None, :] * n8[..., None], 0.0, 1.0))
    old_path_vs_bc = rc.level_diff_stats(via8, bc)
    del via8, n8
    twin_default, info = rc.tint_detail(n, colour, k)
    twin_default = rc.rolloff(twin_default)
    twin_err = float(np.abs(twin_default - albedo.reshape(-1, 3)).max())
    del twin_default
    # --- every mip: Unreal SimpleAverage in linear light; BC stored 8-bit sRGB, Detail16 stored G16
    bc_lin = rc.s2l(bc / 255.0)
    mips = []
    for f in rc.mip_factors(*d.shape):
        bcm = rc.q8_srgb(rc.block_mean(bc_lin, f))
        dm = rc.q16_linear(rc.block_mean(d, f)) / 65535.0
        mm = rc.q8_srgb(np.clip(colour[None, None, :] * (bias + scale * dm)[..., None], 0.0, 1.0))
        s = rc.level_diff_stats(mm, bcm)
        mips.append({"mip": len(mips), "size": list(dm.shape), **s})
    del bc_lin
    mip_max = max(m["max"] for m in mips)
    # --- G-H1: the default colour must sit inside the model's exact region
    h_def = float(np.log(rc.ALBEDO_CEILING / colour.max()) / np.log(k["highlight_ratio"]))
    max_default_albedo = float(colour.max() * k["n_max"])
    gh1 = {"H_default": round(h_def, 4), "max_default_albedo": round(max_default_albedo, 5),
           "pass": bool(h_def >= 1.0 and max_default_albedo <= rc.KNEE)}
    # --- recolour stress (the MF twin), light colours included
    stress = rc.stress_fabric(n, k, {**rc.STRESS, **rc.REPORT_ONLY}, colour)
    stress_pass = all(v["pass"] for name, v in stress.items() if name in rc.STRESS)
    gates = {
        "lossless_16bit": lossless,
        "readback": readback,
        "default_8bit_vs_shipped_BC": {**default_vs_bc, "pass": bool(default_vs_bc["max"] == 0)},
        "reference_shipped_detail8_path_vs_BC": old_path_vs_bc,
        "default_every_mip_vs_BC_mips": {"max_level_diff": mip_max, "per_mip": mips, "pass": bool(mip_max <= 1)},
        "twin_default_vs_contract_max_abs_linear": twin_err,
        "G-H1": gh1,
        "recolour_stress": {"pass": stress_pass, "colours": stress},
    }
    ok = all(g.get("pass", True) for g in gates.values() if isinstance(g, dict)) and twin_err < 1e-9
    log(f"{item}/{part}: default max diff {default_vs_bc['max']} (texels>0 {default_vs_bc['texels_diff_gt0']}), "
        f"mips max {mip_max}, H {h_def:.3f}, stress {'PASS' if stress_pass else 'FAIL'}, "
        f"white gap {stress['white']['max_gap_levels']}, {time.time() - t0:.0f} s -> {'PASS' if ok else 'FAIL'}")
    params = {
        "Colour": rc.rnd(list(colour) + [1.0], 9),
        "Detail Bias": float(bias),
        "Detail Scale": float(scale),
        "Detail Mean": k["mean"],
        "Detail Highlight Ratio": k["highlight_ratio"],
        "Detail Moments Low": k["moments_low"],
        "Detail Moments High": k["moments_high"],
        "Dark Detail Follow": rc.DARK_FOLLOW,
        "Albedo Ceiling": rc.ALBEDO_CEILING,
    }
    map_entry = {
        "file": rc.rel(out), "sha256": rc.sha256(out), "size": [int(d.shape[1]), int(d.shape[0])],
        "format": "PNG, 16-bit greyscale (colour type 0), no colour chunks, row 0 = top",
        "encoding": "LINEAR: value / 65535 = the linear detail d (sRGB-decoded shipped Detail)",
        "unreal_import": {"srgb": False, "compression": "TC_GRAYSCALE", "expected_pc_format": "G16",
                          "sampler": "SAMPLERTYPE_LINEAR_GRAYSCALE", "mips": "TMGS_FROM_TEXTURE_GROUP",
                          "address": "Wrap"},
        "source": {"file": rc.rel(src), "sha256": rc.sha256(src), "stored_levels": int(len(levels)),
                   "source_png_rgb_equal": grey_rgb},
        "recipe": "d16 = round(65535 * sRGBdecode(Detail8.R / 255)); lossless (one code per 8-bit level)",
    }
    part_entry = {
        "slot_material": f"M_BlackHat_{part}" if item == "BlackHat" else "M_SmokeBomb",
        "instance": cfg["instance"], "master": "M_Fabric_Master", "detail_map": Path(out).stem,
        "base_colour_map_reference": {"file": rc.rel(bc_path), "sha256": rc.sha256(bc_path)},
        "params": params,
        "param_notes": {
            "Colour": "linear RGBA; the part's MEAN colour in the mean-colour form (the buyer's one colour)",
            "Detail Moments": "ASCENDING cubic coefficients as RGBA: E(c) = R + G*c + B*c^2 + A*c^3; Low = E[n^c; "
                              "n <= 1], High = E[n^c; n > 1], over every texel of the map, fitted exactly through c = "
                              "0, 0.5, 1, 1.5 (so Low(1) + High(1) = Detail Mean)",
            "n": "n = Detail Bias + Detail Scale x Detail16 (the texel's multiple of the mean colour)",
        },
        "derivation": derivation, "sidecar_values": source_values,
        "moment_samples": {"c": list(rc.MOMENT_POINTS), "low": k["moment_samples_low"],
                           "high": k["moment_samples_high"]},
        "n_range": [k["n_min"], k["n_max"]], "fraction_n_le_1": k["fraction_n_le_1"],
        "gates": gates, "pass": bool(ok),
    }
    return map_entry, part_entry, ok


def main(argv):
    items = list(PARTS)
    if "--items" in argv:
        items = argv[argv.index("--items") + 1].split(",")
    import bpy
    overall = True
    summary = {}
    for item in items:
        cfg = PARTS[item]
        sidecar_path = rc.EXPORTS / cfg["sidecar"]
        sidecar = json.loads(sidecar_path.read_text())
        doc = {"schema": "ninjapack.recolour_maps/1", "item": item,
               "generated": datetime.date.today().isoformat(),
               "generator": {"script": rc.rel(__file__), "script_sha256": rc.sha256(__file__),
                             "common": rc.rel(rc.__file__), "common_sha256": rc.sha256(rc.__file__),
                             "version": VERSION, "blender": bpy.app.version_string},
               "sidecar": {"file": rc.rel(sidecar_path), "sha256": rc.sha256(sidecar_path)},
               "maps": {}, "parts": {}}
        for part, pcfg in cfg["parts"].items():
            map_entry, part_entry, ok = run_part(item, part, pcfg, sidecar)
            doc["maps"][Path(pcfg["out"]).stem] = map_entry
            doc["parts"][part] = part_entry
            overall &= ok
            summary[f"{item}/{part}"] = ok
        doc["pass"] = all(p["pass"] for p in doc["parts"].values())
        out = rc.EXPORTS / item / "Textures" / "Recolour" / "recolour_maps.json"
        rc.write_json(out, doc)
        rc.write_json(rc.WORK / "maps" / f"gates_detail16_{item}.json", doc)
        log(f"wrote {out}")
    log(f"SUMMARY {json.dumps(summary)} overall={'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    code = main(argv)
    sys.stdout.flush()
    import os
    os._exit(code)
