"""Recolour contract on the SHIPPED PNG bytes, at every mip (independent verifier).

Sidecar claim, per part: BaseColor = Detail.R x Tint_linear (Detail imported sRGB ON, TC_Grayscale)
equals T_*_BC (sRGB) at the default Tint, at every mip.

Model of Unreal 5.8's build: both maps are sRGB, so the texture build linearises the 8-bit source
to float, builds mips with the World group's SimpleAverage (2x2 box) in LINEAR light, then
re-encodes each mip (Detail G8 sRGB, uncompressed; BC to BC1 - the BC1 block error is NOT modelled
and is reported separately as a caveat).  The sampler decodes sRGB before filtering.

    blender.exe -b --factory-startup --python bhv_detail_tint.py
"""
import hashlib
import json
from pathlib import Path

import bpy
import numpy as np

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\blackhat\UnrealVerify_indep_v1")
TEX = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Exports\BlackHat\Textures")
SIDECAR = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Exports\BlackHat\SM_BlackHat.sockets.json")
LUMA = np.array([0.2126, 0.7152, 0.0722])


def load(name):
    p = TEX / name
    img = bpy.data.images.load(str(p))
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    info = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "depth": img.depth, "size": [w, h],
            "channels": img.channels, "is_float": img.is_float}
    arr = np.round(px.reshape(h, w, 4).astype(np.float64) * 255.0)     # exact 8-bit codes
    bpy.data.images.remove(img)
    return info, arr


def s2l(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def l2s8(c):
    c = np.clip(c, 0, 1)
    s = np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)
    return np.round(s * 255.0)


def box(a, k):
    if k == 0:
        return a
    s = 2 ** k
    h, w = a.shape[:2]
    return a.reshape(h // s, s, w // s, s, *a.shape[2:]).mean(axis=(1, 3))


def part(prefix, tint):
    tint = np.asarray(tint, np.float64)
    ibc, bc = load(f"T_BlackHat_{prefix}_BC.png")
    idt, dt = load(f"T_BlackHat_{prefix}_Detail.png")
    rep = {"bc": ibc, "detail": idt, "tint_linear": tint.tolist()}
    rep["bc_alpha_codes_minmax"] = [float(bc[..., 3].min()), float(bc[..., 3].max())]
    rep["detail_rgb_equal"] = bool(np.array_equal(dt[..., 0], dt[..., 1]) and np.array_equal(dt[..., 0], dt[..., 2]))
    D8 = dt[..., 0]
    rep["detail_code_min_max"] = [float(D8.min()), float(D8.max())]
    rep["detail_code_p0_1_p1_p50_p99_p99_9"] = [float(np.percentile(D8, q)) for q in (0.1, 1, 50, 99, 99.9)]
    hist = np.bincount(D8.astype(np.int64).ravel(), minlength=256)
    rep["detail_codes_used"] = int((hist > 0).sum())
    bc_lin = s2l(bc[..., :3])
    d_lin = s2l(D8)
    # chroma of BC vs tint chroma (does one tint per part explain BC's colour?)
    bl = bc_lin @ LUMA
    m = bl > 1e-4
    chroma = bc_lin[m] / bl[m, None]
    tchroma = tint / float(tint @ LUMA)
    rep["bc_chroma_vs_tint_chroma"] = {"tint_chroma": tchroma.round(5).tolist(),
                                       "bc_chroma_p1": np.percentile(chroma, 1, axis=0).round(5).tolist(),
                                       "bc_chroma_p50": np.percentile(chroma, 50, axis=0).round(5).tolist(),
                                       "bc_chroma_p99": np.percentile(chroma, 99, axis=0).round(5).tolist()}
    rep["max_bc_linear_over_tint"] = (bc_lin.reshape(-1, 3).max(0) / tint).round(5).tolist()
    mips = []
    for k in range(0, 12):
        b = box(bc_lin, k)
        d = box(d_lin, k)
        # re-encode each mip to 8 bits as the build does (BC1 not modelled)
        b8 = l2s8(b)
        d8 = l2s8(d)
        rec = s2l(d8)[..., None] * tint
        bcm = s2l(b8)
        rec8 = l2s8(rec)
        diff8 = np.abs(rec8 - b8)
        # float (pre-quantisation) relation
        recf = d[..., None] * tint
        relf = (recf @ LUMA).mean() / (b @ LUMA).mean() - 1
        mips.append({"mip": k, "size": int(bc.shape[0] // 2 ** k),
                     "float_mean_luma_rel_percent": float(100 * relf),
                     "float_abs_max_linear": float(np.abs(recf - b).max()),
                     "q8_srgb_abs_max_levels": float(diff8.max()),
                     "q8_srgb_abs_p99_levels": float(np.percentile(diff8, 99)),
                     "q8_srgb_frac_texels_diff_gt1": float((diff8.max(-1) > 1).mean()),
                     "q8_mean_luma_rel_percent": float(100 * ((rec @ LUMA).mean() / (bcm @ LUMA).mean() - 1))})
    rep["mips"] = mips
    rep["worst_mip_q8_abs_max_levels"] = max(m["q8_srgb_abs_max_levels"] for m in mips)
    rep["worst_mip_abs_mean_luma_rel_percent"] = max(abs(m["q8_mean_luma_rel_percent"]) for m in mips)
    return rep


def main():
    side = json.loads(SIDECAR.read_text(encoding="utf-8"))
    out = {"sidecar_sha256": hashlib.sha256(SIDECAR.read_bytes()).hexdigest(), "parts": {}}
    for mat, prefix in (("M_BlackHat_Straw", "Straw"), ("M_BlackHat_Cloth", "Cloth")):
        rec = side["materials"][mat]
        tl = rec["tint_default_linear"]
        ts = rec["tint_default_srgb"]
        ts_from_tl = (l2s8(np.array(tl)) / 255.0).tolist()
        r = part(prefix, tl)
        r["tint_srgb_consistency"] = {"sidecar_srgb": ts, "srgb_from_linear_8bit": ts_from_tl,
                                      "abs_max": float(np.abs(np.array(ts) - np.array(
                                          [1.055 * v ** (1 / 2.4) - 0.055 for v in tl])).max())}
        out["parts"][prefix] = r
    (HERE / "detail_tint.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("BHV_DETAIL_TINT_DONE")


main()
