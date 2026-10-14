"""DRAFT (W6, not part of any build): SR01 recolour maps in the pack schema + a pre-check through the pack's own derive
step. Plain Python; READ-ONLY use of Scripts/unreal/materials/maps (no edit there, no PackMaterials lock, no Unreal).
Modelled on Scripts/guns/smg/smg_recolour.py (the SMG01 maps writer) and maps/derive_constants_smg01.py.

    py -3 -B WorkFiles/guns/sniper/materials/sr01_recolour_pack_draft.py [--out DIR]

Recolour group SR01 = ONE member, M_SR01_Chassis (M_Fabric_Master, Metal From ORM on); the user colour = the OD paint.
The magazine set carries no OD (Masks A = 0 on every texel), so M_SR01_Mag is not a member (baked, not recolourable).
Cover = the Chassis texels with Masks A = 1 (the OD paint only); d = normalised lum(BC) over those texels at the BC's
size up to 2048, 3 px edge extension, one fill constant elsewhere (exactly smg_recolour.detail()).

Writes into --out (default WorkFiles/guns/sniper/materials/draft_out/, NEVER Exports/):
    T_SR01_Chassis_Detail16.png   the pack-schema detail map (the shipped Recolour/ map is the W2 one, a different recipe)
    recolour_maps.json            schema ninjapack.recolour_maps/1 (what Exports/Guns/SR01/Textures/Recolour/ would get)
    recolour_constants_draft.json derive_constants.fabric_part on the draft map (what derive_constants_sr01.py would write)
    precheck.json                 the gates below
Gates (reported): derive_constants.fabric_part (v1 contract at every mip, guards inactive, mip fit within 2 %); the
13-colour stress; black floor / knee; the default recolour path vs the shipped BC ON THE OD (P1 bar p99.9 <= 2 levels);
and the tint exposure: the share of the set's covered texels that are NOT OD paint, which M_Fabric_Master would tint
with the user colour when Use Original Baked Colours is off (the master has no mask input; Metal From ORM only restores
metallic or bright texels).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MAPS = ROOT / "Scripts" / "unreal" / "materials" / "maps"
Image.MAX_IMAGE_PIXELS = None


def _load(name):
    sp = importlib.util.spec_from_file_location(name, str(MAPS / f"{name}.py"))
    m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m
    sp.loader.exec_module(m)
    return m


sys.path.insert(0, str(MAPS))
rc = _load("recolour_common")
tw = _load("np_twin")
dc = _load("derive_constants")
assert Path(rc.PROJECT).resolve() == ROOT.resolve(), rc.PROJECT
DET_MAX = 2048
STRESS = ("FFFFFF", "FF0000", "0000FF", "F2E8D5", "000000", "808080", "1A1A1A", "3050A0", "2E5E2E", "6B3C27",
          "C2B280", "4B5320", "B08D57")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return Path(p).resolve().relative_to(ROOT.resolve()).as_posix()


def detail(lum, cover):
    """smg_recolour.detail(), unchanged."""
    DET = min(DET_MAX, lum.shape[0])
    a_lo, a_hi = float(np.percentile(lum[cover], 0.05)), float(np.percentile(lum[cover], 99.95))
    d = np.clip((lum - a_lo) / max(a_hi - a_lo, 1e-9), 0.0, 1.0)
    n2 = lum.shape[0] // DET
    cm = cover.reshape(DET, n2, DET, n2).astype(np.float64)
    w = cm.sum(axis=(1, 3))
    dd = np.where(cover, d, 0.0).reshape(DET, n2, DET, n2).sum(axis=(1, 3))
    cov1 = w > 0
    d1 = np.where(cov1, dd / np.maximum(w, 1e-9), 0.0)
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
    q = np.where(ok & (q == fill), np.minimum(fill + 1, 65535), q)
    return q, cov1, a_lo, a_hi, n2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex", default=str(ROOT / "Exports" / "Guns" / "SR01" / "Textures"))
    ap.add_argument("--out", default=str(HERE / "draft_out"))
    a = ap.parse_args()
    tex, out = Path(a.tex), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    st = "Chassis"
    bcp = tex / f"T_SR01_{st}_BC.png"
    bc8 = np.asarray(Image.open(bcp).convert("RGB"), np.float64) / 255.0
    S = bc8.shape[0]
    bc = tw.s2l(bc8)
    mk = np.asarray(Image.open(tex / f"T_SR01_{st}_Masks.png").convert("RGBA").resize((S, S), Image.NEAREST))
    A = mk[..., 3] > 127
    cover = A                                       # the OD paint (Masks A, half size, nearest-upsampled)
    # the BC is dilated 32 px into empty atlas space and the Masks are not, so the set's real coverage comes from the
    # painter's own texel counts (sr_paint paint_report.json, finishes per set), not from the maps
    rep = json.loads((ROOT / "WorkFiles/guns/sniper/scratch/w2/paint/paint_report.json").read_text())[st]
    fins = {k: (v.get("texels") if isinstance(v, dict) else v) for k, v in rep["finishes"].items()}
    painted = sum(fins.values())
    exposure = {"source": "WorkFiles/guns/sniper/scratch/w2/paint/paint_report.json (W2 painter; W4b changed it < 0.5 %)",
                "texels_painted": painted, "finishes": fins,
                "non_od_share": round(1.0 - fins.get("od", 0) / painted, 4),
                "od_texels_masks_A": int(cover.sum()),
                "note": "anodize, polymer and rubber on the Chassis set: tinted by M_Fabric_Master's recolour path (no "
                        "mask input; Metal From ORM restores only metallic or bright texels) when Use Original Baked "
                        "Colours is off"}
    lum = bc @ rc.LUM
    colour = bc[cover].mean(axis=0)
    q, cov1, a_lo, a_hi, n2 = detail(lum, cover)
    DET = q.shape[0]
    p16 = out / f"T_SR01_{st}_Detail16.png"
    rc.png_write(p16, q, 16)
    back, bits, _ = rc.png_read(p16)
    ok_rt = bool(np.array_equal(back, q)) and bits == 16
    lum_c = float(colour @ rc.LUM)
    bias, scale = a_lo / lum_c, (a_hi - a_lo) / lum_c
    fillv = int(np.unique(q, return_counts=True)[0][np.argmax(np.unique(q, return_counts=True)[1])])
    kc = rc.fabric_constants(bias + scale * (q[q != fillv] / 65535.0))
    gen = {"instance": "MI_SR01_Chassis", "master": "M_Fabric_Master",
           "params": {"Colour": [*[round(float(x), 6) for x in colour], 1.0], "Detail Bias": round(bias, 6),
                      "Detail Scale": round(scale, 6), "Detail Mean": kc["mean"],
                      "Detail Highlight Ratio": kc["highlight_ratio"], "Detail Moments Low": kc["moments_low"],
                      "Detail Moments High": kc["moments_high"], "Dark Detail Follow": rc.DARK_FOLLOW,
                      "Albedo Ceiling": rc.ALBEDO_CEILING, "Specular Strength": 0.5},
           "switches": {"Metal From ORM": True, "Cloth Sheen": False, "Use Lettering": False,
                        "Use Original Baked Colours": "ON in the shipped instance (non-OD texels on the set)"}}
    der = dc.fabric_part("SR01", f"SR01/{st}", rel(p16), gen)
    p = der["params"]
    d16 = np.repeat(np.repeat(back / 65535.0, n2, 0), n2, 1)
    g, ce, _ = tw.fabric_scalar(p, d16, np.asarray(p["Colour"][:3]))
    alb = ce[None, None, :] * g[..., None]
    lev = np.abs(rc.q8_srgb(alb).astype(np.int32) - np.rint(bc8 * 255).astype(np.int32)).max(axis=2)
    od_lev = lev[cover]
    stress, ok_stress = {}, True
    for hx in STRESS:
        a_, info = tw.fabric_albedo(p, d16[cover], dc.hexlin(hx))
        lu = a_ @ rc.LUM
        row = {"max": round(float(a_.max()), 4),
               "grain_kept_p99_over_p1": round(float(np.percentile(lu, 99) / max(np.percentile(lu, 1), 1e-9)), 2)}
        row["pass"] = bool(np.isfinite(a_).all() and a_.max() <= tw.LIMIT + 1e-9 and row["grain_kept_p99_over_p1"] > 1.2)
        ok_stress &= row["pass"]
        stress[hx] = row
    cmax = float(max(p["Colour"][:3]))
    amax = float(alb[cover].max())
    maps = {"schema": "ninjapack.recolour_maps/1", "item": "SR01", "generated": datetime.date.today().isoformat(),
            "generator": {"script": rel(__file__), "script_sha256": sha256(__file__),
                          "common_sha256": sha256(MAPS / "recolour_common.py"), "status": "DRAFT, not shipped"},
            "recolour_group": {"name": "SR01", "members": ["M_SR01_Chassis"],
                               "user_colour": "the OD paint colour (Colour)"},
            "maps": {f"T_SR01_{st}_Detail16": {
                "file": f"Exports/Guns/SR01/Textures/Recolour/T_SR01_{st}_Detail16.png", "draft_file": rel(p16),
                "sha256": sha256(p16), "size": [DET, DET], "encoding": "LINEAR: value / 65535 = d",
                "source": rel(bcp), "source_sha256": sha256(bcp), "png_roundtrip_exact": ok_rt}},
            "parts": {f"SR01/{st}": gen}}
    (out / "recolour_maps.json").write_text(json.dumps(maps, indent=1))
    (out / "recolour_constants_draft.json").write_text(json.dumps(
        {"schema": "ninjapack.recolour_constants/1", "item": "SR01", "status": "DRAFT (derive_constants.fabric_part "
         "run read-only on the draft map; the real file is written by maps/derive_constants_sr01.py in the build)",
         "base_script_sha256": sha256(MAPS / "derive_constants.py"), "parts": {f"SR01/{st}": der}}, indent=1,
        default=float))
    res = {"generated": datetime.date.today().isoformat(), "status": "DRAFT pre-check, nothing built",
           "png_roundtrip_exact": ok_rt,
           "derive_constants_fabric_part": {"gates": der["gates"], "pass": der["pass"]},
           "black_floor": {"colour_max": round(cmax, 5), "floor": tw.COLOUR_FLOOR, "pass": cmax > tw.COLOUR_FLOOR},
           "knee": {"max_default_albedo": round(amax, 4), "knee": tw.KNEE, "pass": amax <= tw.KNEE},
           "stress_13_colours": {"colours": stress, "pass": ok_stress},
           "default_path_vs_bc_on_od": {"levels_p50": float(np.percentile(od_lev, 50)),
                                        "levels_p99": float(np.percentile(od_lev, 99)),
                                        "levels_p999": float(np.percentile(od_lev, 99.9)), "p1_bar_levels": 2.0,
                                        "pass": float(np.percentile(od_lev, 99.9)) <= 2.0},
           "tint_exposure": exposure}
    res["pass_maps_and_derive"] = bool(ok_rt and der["pass"] and ok_stress and res["black_floor"]["pass"] and
                                       res["knee"]["pass"])
    (out / "precheck.json").write_text(json.dumps(res, indent=1, default=float))
    print("[SR01-recolour-draft]", json.dumps({k: (v["pass"] if isinstance(v, dict) and "pass" in v else v)
                                                for k, v in res.items() if k != "tint_exposure"}))
    print("[SR01-recolour-draft] OD p50/p99/p99.9 levels",
          res["default_path_vs_bc_on_od"]["levels_p50"], res["default_path_vs_bc_on_od"]["levels_p99"],
          res["default_path_vs_bc_on_od"]["levels_p999"], "exposure", json.dumps(exposure)[:200])


if __name__ == "__main__":
    main()
