"""T_Kunai_Wrap_Detail16: a tint-ready 16-bit LINEAR greyscale detail for the kunai's grip wrap, from a FLOAT re-bake of
M_Kunai_Wrap (Dye = 0) on SM_Kunai_Plain_LOD0, plus Exports/Shuriken/Textures/Recolour/recolour_maps.json
(MATERIAL_PLAN.md 5.1).

Why: the shipped T_Kunai_Wrap_BC is 8-bit sRGB with only ~79 distinct levels on a dark cloth; dividing it by its mean
colour would band as soon as a buyer picks a light colour.  So the wrap's base colour is baked again, the same way
kunai_wrap.bake_kunai bakes it (B._alone(lod0), _absorber(steel), _wrap_uv(lod0), B._bake_channel(..., "Base Color"),
EMIT, 16 samples, 16 px EXTEND margin, OPTIX when present, spec.wrap_px 1024, B._fill over B._coverage) but into a
FLOAT image, and its luminance is written full range at 16 bits:

    Y = luminance(linear rgb);  Ymean = mean over covered texels (fill texels carry the mean colour, so n = 1 there)
    d = (Y - Ylo) / (Yhi - Ylo)             -> 16-bit PNG, linear
    Colour = mean linear rgb, Bias = Ylo / Ymean, Scale = (Yhi - Ylo) / Ymean     (n = Bias + Scale d = Y / Ymean)

Assets/Shuriken.blend is opened READ-ONLY (it is the frozen pack's scene; nothing is ever saved) and its sha256 is
checked before and after.  The wrap's material, UVs and every map on disk are untouched: the bake runs through the
same temporary layers bake_kunai uses and removes them again.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b Assets/Shuriken.blend --factory-startup \
        --python Scripts/unreal/materials/maps/make_kunai_wrap_detail.py
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

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import recolour_common as rc  # noqa: E402

sys.path.insert(0, str(rc.PROJECT / "Scripts"))
sys.path.insert(0, str(rc.PROJECT / "Scripts" / "shuriken"))

from pipeline.textures import image_pixels  # noqa: E402
from shuriken_lib import bake as B  # noqa: E402
from shuriken_lib import kunai_wrap as KW  # noqa: E402

VERSION = "1.0.0"
BLEND = rc.PROJECT / "Assets" / "Shuriken.blend"
BLEND_SHA_BASELINE = "f712b421"            # MATERIAL_PLAN.md section 1 (post_kunai_plain baseline)
LOD0 = "SM_Kunai_Plain_LOD0"
SIZE = 1024
SHIPPED_BC = rc.EXPORTS / "Shuriken" / "Textures" / "T_Kunai_Wrap_BC.png"
OUT_DIR = rc.EXPORTS / "Shuriken" / "Textures" / "Recolour"
OUT = OUT_DIR / "T_Kunai_Wrap_Detail16.png"


def log(msg):
    print(f"[kunai_wrap16] {msg}", flush=True)


def bake_wrap(lod0, wrap_mat, steel_mat):
    """Top-down arrays: float linear rgb (H, W, 3), today's byte bake as stored levels (H, W, 3), covered (islands +
    their 16 px EXTEND margin) and islands (margin 0)."""
    fimg = B._new_image("__np_wrap_bc_float", SIZE, data=True)          # float buffer, Non-Color: scene linear
    bimg = B._new_image("__np_wrap_bc_byte", SIZE, data=False)          # the shipped path: byte buffer, sRGB
    try:
        with B._alone(lod0), KW._absorber(steel_mat), KW._wrap_uv(lod0):
            t0 = time.time()
            B._bake_channel(lod0, wrap_mat, "Base Color", fimg)
            log(f"float bake {time.time() - t0:.1f} s on {B.BAKE_DEVICE['device']}")
            B._bake_channel(lod0, wrap_mat, "Base Color", bimg)
            covered = B._coverage(lod0, wrap_mat, SIZE)
            saved_margin = B.BAKE_MARGIN
            B.BAKE_MARGIN = 0                                           # the islands alone (no margin)
            try:
                islands = B._coverage(lod0, wrap_mat, SIZE)
            finally:
                B.BAKE_MARGIN = saved_margin
        if not fimg.is_float:
            raise RuntimeError("the float bake target is not a float buffer")
        fpx = image_pixels(fimg)
        bpx = B._fill(image_pixels(bimg), covered)                      # exactly as _bake_form does for the BC
        return (fpx[::-1, :, :3].astype(np.float64), np.rint(bpx[::-1, :, :3] * 255.0).astype(np.int16),
                covered[::-1].copy(), islands[::-1].copy())
    finally:
        bpy.data.images.remove(fimg)
        bpy.data.images.remove(bimg)


def main():
    t_start = time.time()
    if Path(bpy.data.filepath).resolve() != BLEND.resolve():
        raise RuntimeError(f"open {BLEND} with -b: got {bpy.data.filepath!r}")
    sha_before = rc.sha256(BLEND)
    if not sha_before.startswith(BLEND_SHA_BASELINE):
        raise RuntimeError(f"Assets/Shuriken.blend is not the frozen baseline ({sha_before[:16]})")
    lod0 = bpy.data.objects[LOD0]
    steel_mat, wrap_mat = lod0.data.materials[0], lod0.data.materials[1]
    if wrap_mat.name != KW.WRAP_MATERIAL:
        raise RuntimeError(f"slot 1 of {LOD0} is {wrap_mat.name}")
    dye = wrap_mat.node_tree.nodes["Dye"].outputs[0]
    dye_saved = float(dye.default_value)
    dye.default_value = 0.0
    fbake, byte_levels, covered, islands = bake_wrap(lod0, wrap_mat, steel_mat)
    dye.default_value = dye_saved
    shipped = rc.load_levels8(SHIPPED_BC)[..., :3]
    shipped_lin = rc.s2l(shipped / 255.0)
    cov, isl = covered, islands
    margin = cov & ~isl
    # --- G-K1 bake parity.  Inside the islands the float bake quantises to the shipped BC; in the 16 px EXTEND margin
    # Blender extends a BYTE buffer differently from a FLOAT one (measured: up to 6 levels, only there), and today's
    # byte bake reproduces the shipped BC bit for bit, so the shipped BC = Q(this float bake) + a byte-margin variant.
    f8 = rc.q8_srgb(fbake)
    gk1_isl = rc.level_diff_stats(f8[isl], shipped[isl])
    byte_vs_shipped = rc.level_diff_stats(byte_levels, shipped)
    gk1 = {"islands": gk1_isl, "margin_only_float_extend_vs_byte_extend": rc.level_diff_stats(f8[margin], shipped[margin]),
           "reference_todays_byte_bake_vs_shipped": byte_vs_shipped,
           "islands_texels": int(isl.sum()), "margin_texels": int(margin.sum()), "fill_texels": int((~cov).sum()),
           "note": "gated on the islands (the baked surface).  The margin and the fill of the detail are taken from the "
                   "shipped BC itself (below), so its mips agree with the BC's",
           "bake_noise_note": "OPTIX bakes are not bit-deterministic: today's byte bake vs the shipped BC differs "
                              "in 0-1 texels by 1 level, and three runs of this generator (2026-09-26) differed in "
                              "~420 of 1048576 texels by 1 16-bit code (1.5e-5 of the range).  The Detail16 is "
                              "therefore reproducible to that noise, not bit for bit; its sha256 is recorded here",
           "pass": bool(gk1_isl["max"] <= 1 and gk1_isl["mean"] <= 0.2 and byte_vs_shipped["max"] <= 1
                        and byte_vs_shipped["texels_diff_gt0"] <= 16)}
    # --- the linear colour the detail encodes: the FLOAT bake on the islands; the shipped BC (decoded) in the margin
    # and the fill, which are copies of island-edge texels / the pack's mean fill and must match the BC for its mips
    lin = np.where(isl[..., None], fbake, shipped_lin)
    y = lin @ rc.LUM
    colour = lin[cov].mean(axis=0)
    ymean = float(y[cov].mean())
    ylo, yhi = float(y.min()), float(y.max())
    d_float = (y - ylo) / (yhi - ylo)
    d16 = rc.q16_linear(d_float)
    rc.png_write(OUT, d16, 16)
    back, bits, ctype = rc.png_read(OUT)
    bpy_back = rc.load_png_bpy(OUT)[..., 0].astype(np.float64)
    readback = {"own_decoder_equal": bool(np.array_equal(back, d16)), "bits": bits, "colour_type": ctype,
                "blender_decoder_max_abs": float(np.abs(bpy_back - d16 / 65535.0).max()),
                "png_chunks": rc.png_chunks(OUT)}
    readback["pass"] = bool(readback["own_decoder_equal"] and bits == 16 and ctype == 0
                            and readback["blender_decoder_max_abs"] < 1e-6)
    d = d16 / 65535.0
    bias, scale = ylo / ymean, (yhi - ylo) / ymean
    n = bias + scale * d
    k = rc.fabric_constants(n)
    # --- G-K2: the default model vs the shipped BC (and vs the float bake, which isolates the model's own error)
    model = np.clip(colour[None, None, :] * n[..., None], 0.0, 1.0)
    m8 = rc.q8_srgb(model)
    de_ship = rc.de2000(model[cov], shipped_lin[cov])
    de_float = rc.de2000(model[cov], lin[cov])
    gk2 = {"texels": "covered (islands + margin)", "dE00_vs_shipped_BC": {"mean": round(float(de_ship.mean()), 4),
                                  "p99": round(float(np.percentile(de_ship, 99)), 4),
                                  "p99.9": round(float(np.percentile(de_ship, 99.9)), 4),
                                  "max": round(float(de_ship.max()), 4)},
           "dE00_vs_encoded_linear_colour": {"mean": round(float(de_float.mean()), 4),
                                  "p99": round(float(np.percentile(de_float, 99)), 4),
                                  "max": round(float(de_float.max()), 4)},
           "stored_levels_vs_shipped_BC_covered": rc.level_diff_stats(m8[cov], shipped[cov]),
           "stored_levels_vs_shipped_BC_all": rc.level_diff_stats(m8, shipped),
           "why_not_zero": "one greyscale detail cannot carry the fibre flecks' slight hue shift (FIBRE (0.150, 0.142, "
                           "0.126) vs DARK (0.042, 0.039, 0.036)); the luminance is carried exactly"}
    gk2["pass"] = bool(gk2["dE00_vs_shipped_BC"]["mean"] <= 0.5 and gk2["dE00_vs_shipped_BC"]["p99"] <= 1.5)
    # luminance-only exactness: the model's luminance vs the shipped BC's luminance, in stored levels of Y
    ylev = rc.level_diff_stats(rc.q8_srgb(model @ rc.LUM)[cov], rc.q8_srgb(shipped_lin @ rc.LUM)[cov])
    # --- mips: BC 8-bit sRGB SimpleAverage in linear light; Detail16 G16
    mips = []
    for f in rc.mip_factors(SIZE, SIZE):
        bcm = rc.q8_srgb(rc.block_mean(shipped_lin, f))
        dm = rc.q16_linear(rc.block_mean(d, f)) / 65535.0
        mm = rc.q8_srgb(np.clip(colour[None, None, :] * (bias + scale * dm)[..., None], 0.0, 1.0))
        mips.append({"mip": len(mips), "size": list(dm.shape), **rc.level_diff_stats(mm, bcm)})
    # --- G-H1
    h_def = float(np.log(rc.ALBEDO_CEILING / colour.max()) / np.log(k["highlight_ratio"]))
    max_def = float(colour.max() * k["n_max"])
    gh1 = {"H_default": round(h_def, 4), "max_default_albedo": round(max_def, 5),
           "pass": bool(h_def >= 1.0 and max_def <= rc.KNEE)}
    twin, _ = rc.tint_detail(n, colour, k)
    twin_err = float(np.abs(rc.rolloff(twin) - model.reshape(-1, 3)).max())
    stress = rc.stress_fabric(n, k, {**rc.STRESS, **rc.REPORT_ONLY}, colour)
    stress_pass = all(v["pass"] for name, v in stress.items() if name in rc.STRESS)
    # the old path for contrast: the shipped 8-bit BC's own luminance as the detail (what a divide would give)
    y8 = shipped_lin @ rc.LUM
    n8 = y8 / float(y8[cov].mean())
    stress_old = rc.stress_fabric(n8, rc.fabric_constants(n8), {"white": rc.STRESS["white"]}, colour)["white"]
    sha_after = rc.sha256(BLEND)
    gk3 = {"sha256_before": sha_before, "sha256_after": sha_after, "pass": bool(sha_before == sha_after)}
    gates = {"G-K1_bake_parity": gk1, "G-K2_default_model_vs_shipped_BC": gk2,
             "luminance_only_stored_levels_covered": ylev, "G-K3_blend_unchanged": gk3, "G-H1": gh1,
             "readback": readback,
             "default_every_mip_vs_BC_mips": {"max_level_diff": max(m["max"] for m in mips), "per_mip": mips,
                                              "note": "reported, not gated at 1 level: the greyscale model drops the "
                                                      "flecks' hue at every mip as at mip 0 (G-K2)"},
             "twin_default_vs_contract_max_abs_linear": twin_err,
             "recolour_stress": {"pass": stress_pass, "colours": stress},
             "contrast_white_from_shipped_8bit_BC": {k2: stress_old[k2] for k2 in
                                                     ("max_gap_levels", "levels_used", "p1_p99_span_levels",
                                                      "occupied_fraction_of_span", "pass")}}
    ok = all(gates[g]["pass"] for g in ("G-K1_bake_parity", "G-K2_default_model_vs_shipped_BC",
                                        "G-K3_blend_unchanged", "G-H1", "readback", "recolour_stress")) \
        and twin_err < 1e-9
    params = {"Colour": rc.rnd(list(colour) + [1.0], 9), "Detail Bias": bias, "Detail Scale": scale,
              "Detail Mean": k["mean"], "Detail Highlight Ratio": k["highlight_ratio"],
              "Detail Moments Low": k["moments_low"], "Detail Moments High": k["moments_high"],
              "Dark Detail Follow": rc.DARK_FOLLOW, "Albedo Ceiling": rc.ALBEDO_CEILING}
    doc = {
        "schema": "ninjapack.recolour_maps/1", "item": "Shuriken",
        "generated": datetime.date.today().isoformat(),
        "generator": {"script": rc.rel(__file__), "script_sha256": rc.sha256(__file__),
                      "common": rc.rel(rc.__file__), "common_sha256": rc.sha256(rc.__file__), "version": VERSION,
                      "blender": bpy.app.version_string, "bake_device": B.BAKE_DEVICE["device"],
                      "bake": {"source": f"{rc.rel(BLEND)} (opened read-only, never saved)", "object": LOD0,
                               "material": wrap_mat.name, "Dye": 0.0, "samples": B.EMIT_SAMPLES,
                               "margin_px": B.BAKE_MARGIN, "margin_type": "EXTEND", "size": SIZE,
                               "path": "kunai_wrap.bake_kunai's wrap half: B._alone, _absorber(steel), _wrap_uv, "
                                       "B._bake_channel('Base Color') into a FLOAT image, B._fill over B._coverage"}},
        "maps": {"T_Kunai_Wrap_Detail16": {
            "file": rc.rel(OUT), "sha256": rc.sha256(OUT), "size": [SIZE, SIZE],
            "format": "PNG, 16-bit greyscale (colour type 0), no colour chunks, row 0 = top",
            "encoding": "LINEAR: value / 65535 = d = (Y - Ylo) / (Yhi - Ylo), Y = Rec.709 luminance of the float bake",
            "uv": "the wrap's UV tile u 1..2 (same texel grid as T_Kunai_Wrap_BC; Wrap addressing)",
            "unreal_import": {"srgb": False, "compression": "TC_GRAYSCALE", "expected_pc_format": "G16",
                              "sampler": "SAMPLERTYPE_LINEAR_GRAYSCALE", "mips": "TMGS_FROM_TEXTURE_GROUP",
                              "address": "Wrap"},
            "source": {"blend": rc.rel(BLEND), "blend_sha256": sha_before, "shipped_bc": rc.rel(SHIPPED_BC),
                       "shipped_bc_sha256": rc.sha256(SHIPPED_BC)},
            "luminance": {"Ylo": ylo, "Yhi": yhi, "Ymean_covered": ymean,
                          "covered_fraction": round(float(cov.mean()), 5),
                          "islands_fraction": round(float(isl.mean()), 5)},
            "texel_sources": {"islands": "the float bake (linear, full precision)",
                              "margin_16px_and_fill": "the shipped T_Kunai_Wrap_BC decoded (its own EXTEND margin and "
                                                      "mean fill), so the detail's far mips match the BC's"},
            "recipe": "d = (Y - Ylo) / (Yhi - Ylo), round(65535 d)"}},
        "parts": {"Kunai_Plain/Wrap": {
            "slot_material": "M_Kunai_Wrap", "slot_index": 1, "instance": "MI_Kunai_Plain_Wrap",
            "master": "M_Fabric_Master", "detail_map": "T_Kunai_Wrap_Detail16",
            "base_colour_map_reference": {"file": rc.rel(SHIPPED_BC), "sha256": rc.sha256(SHIPPED_BC)},
            "params": params,
            "param_notes": {
                "Colour": "linear RGBA; the wrap's MEAN colour (covered texels of the float bake)",
                "Detail Moments": "ASCENDING cubic coefficients as RGBA: E(c) = R + G*c + B*c^2 + A*c^3; Low = "
                                  "E[n^c; n <= 1], High = E[n^c; n > 1], over every texel, exact through c = 0, 0.5, "
                                  "1, 1.5 (Low(1) + High(1) = Detail Mean)",
                "n": "n = Detail Bias + Detail Scale x Detail16 = Y / Ymean"},
            "moment_samples": {"c": list(rc.MOMENT_POINTS), "low": k["moment_samples_low"],
                               "high": k["moment_samples_high"]},
            "n_range": [k["n_min"], k["n_max"]], "fraction_n_le_1": k["fraction_n_le_1"],
            "gates": gates, "pass": bool(ok)}},
    }
    doc["pass"] = bool(ok)
    rc.write_json(OUT_DIR / "recolour_maps.json", doc)
    rc.write_json(rc.WORK / "maps" / "gates_kunai_wrap.json", doc)
    log(f"G-K1 islands max {gk1_isl['max']} mean {gk1_isl['mean']} (byte bake vs shipped max "
        f"{byte_vs_shipped['max']}); G-K2 dE00 mean {gk2['dE00_vs_shipped_BC']['mean']} p99 "
        f"{gk2['dE00_vs_shipped_BC']['p99']}; H {h_def:.3f}; white gap {stress['white']['max_gap_levels']} "
        f"(shipped-BC divide: {stress_old['max_gap_levels']}); blend unchanged {gk3['pass']}; "
        f"{time.time() - t_start:.0f} s -> {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        sys.stdout.flush()
        import os
        os._exit(code)
