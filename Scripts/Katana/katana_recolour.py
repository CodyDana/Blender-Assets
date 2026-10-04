"""Recolour maps of the basic katana's grip and the saya's lacquer (finaliser, 2026-10-03; the senbon / flashbang
convention: the item build writes the Recolour maps + recolour_maps.json, the finaliser derives recolour_constants.json
under the materials lock with Scripts/unreal/materials/maps/derive_constants_katana.py).

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/Katana/katana_recolour.py

Parts (both on M_Fabric_Master, the pack's recolourable master):
    Katana/Grip      MI_Katana_Grip        T_Katana_Grip_BC (2048, UV0 tile u 1..2). Metal From ORM ON: the master keeps
                     the baked colour where lum(BC) > 0.2..0.4 (linear), so the ivory same in the windows keeps its colour
                     and only the dark ito (and the cord-dark core under the folds, and the LOD2 shell's cord) recolours.
    Saya/Lacquer     MI_Katana_Saya_Lacquer T_Katana_Saya_BC (2048): the black roiro body and the cavity (Metal From ORM
                     OFF; the horn and brass are the other slot, M_Steel_Master).

For each part: d = clip((lum - a_lo) / (a_hi - a_lo)) over the part's texels (a_lo / a_hi = the 0.05 / 99.95
percentiles of the linear luminance), box-downsampled to 1024 over covered texels only, 3 px of edge extension, every
other texel ONE constant (derive_constants finds the coverage as 'every texel but the most common value'); written as a
16-bit LINEAR greyscale PNG (value / 65535 = d). recolour_maps.json carries the v1 fields: Colour = the part's mean
linear albedo, Detail Bias = a_lo / lum(Colour), Detail Scale = (a_hi - a_lo) / lum(Colour) (so Colour x (Bias + Scale
x d) reproduces the baked luminance with the mean chroma) and recolour_common.fabric_constants over the covered texels.
Re-run after every katana / saya maps stage, then derive_constants_katana.py; run_build.sh's maps_check refuses a stale
chain.
"""
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True

import katana_uvpack as UP  # noqa: E402
from katana_tex import cover_mask  # noqa: E402

_sp = importlib.util.spec_from_file_location("np_recolour_common_ro",
                                             str(ROOT / "Scripts/unreal/materials/maps/recolour_common.py"))
rc = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(rc)

VERSION = "1.0.0-katana"
TEX = ROOT / "Exports" / "Katana" / "Textures"
REC = TEX / "Recolour"
DET = 1024
KEEP_LO = 0.4          # Metal From ORM keeps the baked colour fully above this linear luminance (ramp 0.2 -> 0.4)


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def read_bc(path):
    lev, bits, _ = rc.png_read(path)
    return rc.s2l(lev[..., :3] / 255.0)          # linear, row 0 = top


def saya_lacquer_mask():
    """Texels of the saya's LACQUER slot (every LOD), from the build's part data and atlas (row 0 = top)."""
    sys.path.insert(0, str(HERE))
    import saya_spec as S
    work = ROOT / "WorkFiles" / "katana" / "saya_build"
    parts = pickle.load(open(work / "parts.pkl", "rb"))
    at = UP.load(work / "atlas_saya.json")
    m = np.zeros((at.size, at.size), bool)
    for lv in ("lod0", "lod1", "lod2"):
        uvs = []
        for mb in parts[lv].values():
            for fi, f in enumerate(mb.faces):
                if mb.fmat[fi] != S.SLOT_LACQUER:
                    continue
                uv = at.transform(mb.fisl[fi], np.array(mb.fuv[fi])) * at.size
                for k in range(1, len(f) - 1):
                    uvs.append(uv[[0, k, k + 1]])
        m |= cover_mask(np.array(uvs), at.size, 0)
    return m[::-1]


def detail(lum, cover, stats):
    a_lo, a_hi = float(np.percentile(lum[stats], 0.05)), float(np.percentile(lum[stats], 99.95))
    d = np.clip((lum - a_lo) / max(a_hi - a_lo, 1e-9), 0.0, 1.0)
    n2 = lum.shape[0] // DET
    cm = cover.reshape(DET, n2, DET, n2).astype(np.float64)
    w = cm.sum(axis=(1, 3))
    dd = (np.where(cover, d, 0.0).reshape(DET, n2, DET, n2)).sum(axis=(1, 3))
    cov1 = w > 0
    d1 = np.where(cov1, dd / np.maximum(w, 1e-9), 0.0)
    # 3 px edge extension (mean of covered neighbours), then one constant everywhere else
    val, ok = d1.copy(), cov1.copy()
    for _ in range(3):
        acc = np.zeros_like(val)
        cnt = np.zeros_like(val)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                acc += np.roll(np.roll(np.where(ok, val, 0.0), dy, 0), dx, 1)
                cnt += np.roll(np.roll(ok.astype(np.float64), dy, 0), dx, 1)
        new = (~ok) & (cnt > 0)
        val = np.where(new, acc / np.maximum(cnt, 1e-9), val)
        ok = ok | new
    q = np.rint(np.clip(val, 0, 1) * 65535.0).astype(np.int64)
    fill = int(np.rint(float(d1[cov1].mean()) * 65535.0))
    q = np.where(ok, q, fill)
    # the coverage derive_constants will see is 'every texel but the most common value': keep covered texels off it
    q = np.where(ok & (q == fill), np.minimum(fill + 1, 65535), q)
    return q, cov1, a_lo, a_hi


def part(name, bc_png, cover, stats, instance, slot, switches, note):
    bc = read_bc(bc_png)
    lum = bc @ rc.LUM
    colour = bc[stats].mean(axis=0)
    q, cov1, a_lo, a_hi = detail(lum, cover, stats)
    stem = f"{Path(bc_png).stem.replace('_BC', '')}_{name.split('/')[1]}_Detail16" if "Saya" in name else \
        f"{Path(bc_png).stem.replace('_BC', '')}_Detail16"
    p16 = REC / f"{stem}.png"
    rc.png_write(p16, q, 16)
    back, bits, _ = rc.png_read(p16)
    ok_rt = bool(np.array_equal(back, q)) and bits == 16
    lum_c = float(colour @ rc.LUM)
    bias, scale = a_lo / lum_c, (a_hi - a_lo) / lum_c
    vals, cnts = np.unique(q, return_counts=True)
    fill = int(vals[np.argmax(cnts)])
    cov = q != fill
    n = bias + scale * (q[cov] / 65535.0)
    kc = rc.fabric_constants(n)
    mp = {"file": rel(p16), "sha256": sha256(p16), "size": [DET, DET],
          "format": "PNG, 16-bit greyscale, no colour chunks, row 0 = top",
          "encoding": "LINEAR: value / 65535 = the linear detail d",
          "uv": "the part's UV0 grid (same layout as its BC at half resolution; Wrap addressing)",
          "unreal_import": {"srgb": False, "compression": "TC_GRAYSCALE", "expected_pc_format": "G16",
                            "sampler": "SAMPLERTYPE_LINEAR_GRAYSCALE", "mips": "TMGS_FROM_TEXTURE_GROUP",
                            "address": "Wrap"},
          "source": {"file": rel(bc_png), "sha256": sha256(bc_png)},
          "recipe": "d = clip((lum(BC_linear) - a_lo) / (a_hi - a_lo)) over the part's texels, 2x2 box mean over covered "
                    "texels to 1024, 3 px edge extension, one fill constant elsewhere; value = round(65535 d)",
          "gates": {"png_roundtrip_exact": ok_rt}}
    pp = {"slot_material": slot, "instance": instance, "master": "M_Fabric_Master", "detail_map": stem,
          "switches": switches, "base_colour_map_reference": {"file": rel(bc_png), "sha256": sha256(bc_png)},
          "params": {"Colour": [*[round(float(x), 6) for x in colour], 1.0], "Detail Bias": round(bias, 6),
                     "Detail Scale": round(scale, 6), "Detail Mean": kc["mean"],
                     "Detail Highlight Ratio": kc["highlight_ratio"], "Detail Moments Low": kc["moments_low"],
                     "Detail Moments High": kc["moments_high"], "Dark Detail Follow": rc.DARK_FOLLOW,
                     "Albedo Ceiling": rc.ALBEDO_CEILING, "Specular Strength": 0.5},
          "n_range": [kc["n_min"], kc["n_max"]], "fraction_n_le_1": kc["fraction_n_le_1"],
          "covered_texels": int(cov.sum()), "covered_texels_2048": int(cover.sum()),
          "builder_constants": {"a_lo": a_lo, "a_hi": a_hi, "colour_linear": [float(x) for x in colour],
                                "colour_srgb8": [int(round(float(x) * 255)) for x in rc.l2s(np.clip(colour, 0, 1))]},
          "note": note,
          "derivation": "BaseColor = saturate(Colour x (DetailBias + DetailScale x Detail)); v1 fields over the covered "
                        "texels; recolour_constants.json (v2) by Scripts/unreal/materials/maps/derive_constants_katana.py"}
    print(f"[KAT-RECOLOUR] {name}: covered {int(cov.sum())} colour srgb8 {pp['builder_constants']['colour_srgb8']} "
          f"a_lo {a_lo:.5f} a_hi {a_hi:.5f} bias {bias:.4f} scale {scale:.4f} roundtrip {ok_rt}", flush=True)
    return stem, mp, pp, ok_rt


def main():
    try:
        import bpy
        blender = bpy.app.version_string
    except ImportError:
        blender = None
    REC.mkdir(parents=True, exist_ok=True)
    out = {"schema": "ninjapack.recolour_maps/1", "item": "Katana", "generated": datetime.date.today().isoformat(),
           "generator": {"script": rel(__file__), "script_sha256": sha256(__file__),
                         "common_sha256": sha256(ROOT / "Scripts/unreal/materials/maps/recolour_common.py"),
                         "version": VERSION, "blender": blender},
           "sidecar": {"files": ["Exports/Katana/SM_Katana.sockets.json", "Exports/Katana/SM_Katana_Saya.sockets.json"]},
           "maps": {}, "parts": {}}
    ok = True
    # ---- grip: every grip texel darker than the keep ramp's top (the ivory same keeps its baked colour)
    gbc = TEX / "T_Katana_Grip_BC.png"
    g = read_bc(gbc)
    glum = g @ rc.LUM
    gcov = np.load(ROOT / "WorkFiles" / "katana" / "build" / "paint_grip_cov.npy")[::-1]
    cover = gcov & (glum < KEEP_LO)
    stats = gcov & (glum < 0.2)
    stem, mp, pp, r = part("Katana/Grip", gbc, cover, stats, "MI_Katana_Grip", "M_Katana_Grip",
                           {"Metal From ORM": True, "Cloth Sheen": False, "Use Lettering": False,
                            "Specular From ORM Alpha": False},
                           "the black ito (cord), the cord-dark core under its edge folds and the LOD2 shell's cord; "
                           "the ivory same keeps its baked colour (Metal From ORM keep ramp, linear lum 0.2 -> 0.4)")
    out["maps"][stem], out["parts"]["Katana/Grip"] = mp, pp
    ok &= r
    # ---- saya lacquer: the lacquer slot's texels (body and cavity)
    sbc = TEX / "T_Katana_Saya_BC.png"
    lm = saya_lacquer_mask()
    stem, mp, pp, r = part("Saya/Lacquer", sbc, lm, lm, "MI_Katana_Saya_Lacquer", "M_Katana_Saya_Lacquer",
                           {"Metal From ORM": False, "Cloth Sheen": False, "Use Lettering": False,
                            "Specular From ORM Alpha": False},
                           "the black roiro lacquer of the saya body (with its wear) and the cavity")
    out["maps"][stem], out["parts"]["Saya/Lacquer"] = mp, pp
    ok &= r
    out["other_slots"] = {"Katana/Blade": {"slot_material": "M_Katana_Blade", "instance": "MI_Katana_Blade",
                                           "master": "M_Steel_Master", "recolourable": False},
                          "Katana/Fittings": {"slot_material": "M_Katana_Fittings", "instance": "MI_Katana_Fittings",
                                              "master": "M_Steel_Master", "recolourable": False},
                          "Saya/Fittings": {"slot_material": "M_Katana_Saya_Fittings",
                                            "instance": "MI_Katana_Saya_Fittings", "master": "M_Steel_Master",
                                            "recolourable": False}}
    out["pass"] = bool(ok)
    (REC / "recolour_maps.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[KAT-RECOLOUR] wrote {rel(REC / 'recolour_maps.json')} pass={ok}", flush=True)
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
