"""AR-01 pack-materials gates, analysis half (Blender headless; reads files, writes WorkFiles only).

    blender -b --factory-startup --python WorkFiles/guns/rifle/materials/ar01_pack_analyse.py -- [--keep-exr]

Reads the EXRs ar01_ue_capture.py wrote (WorkFiles/guns/rifle/scratch/pack_captures) and evaluates them with the pack's
own math (Scripts/unreal/materials/maps: np_twin.fabric_albedo = MF_TintDetail + MF_AlbedoRollOff in float64,
recolour_common), the pack's metrics and thresholds (verify/analyse_captures.py: diff_stats, the v3 recolour metrics,
the UV-probe sample positions):

    P1 default capture = shipped BC: the shipped MI_AR01_Furniture (baked colours ON) vs T_AR01_Furniture_BC.png
       bilinearly sampled at the measured sample positions: p99.9 <= 2 stored levels (BC1 as the pack imports it; the
       BC7 variant reported beside it)
    P2 the recolour path at the default Colour vs the twin: p99.9 <= 1 level, mean <= 0.3 (the pack's default gate);
       its distance from the BC is reported (the per-piece hue offsets the scalar detail drops)
    P3 10-colour stress on the wood (mip 0) vs the twin: p99.9 <= 2 levels (gate_stress_twin) and the pack's v3 gate
       (clip <= 0.1 %, banding, std ratio of log luminance >= 0.25, Spearman vs the default capture >= 0.98)
    P4 mip drift: every colour's mip-4 capture mean (16 x 16 fully covered blocks) vs the box-filtered mip-0 capture:
       within 2 %
    R1 the steel sets (Metal 4096, Mag 1024) vs their BC PNGs: BC1 error, reported (the pack does not gate steel)
Writes WorkFiles/guns/rifle/gates/pack_materials_captures.json and the stored levels of the default captures plus a
stress sheet as PNG in the scratch folder (gitignored); EXRs deleted unless --keep-exr.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
PACK = Path(os.environ.get("AR01_PACK_DIR") or ROOT / "Scripts/unreal/materials")
sys.path.insert(0, str(PACK / "maps"))
import np_twin as tw  # noqa: E402
import recolour_common as rc  # noqa: E402

PROJECT = PACK.parents[2]
CAPS = Path(os.environ.get("AR01_CAPTURE_OUT") or ROOT / "WorkFiles/guns/rifle/scratch/pack_captures")
OUT_JSON = ROOT / "WorkFiles/guns/rifle/gates/pack_materials_captures.json"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KEEP = "--keep-exr" in ARGS
GAIN = 8.0
VARIANTS = [(sw, su, sv) for sw in (False, True) for su in (1, -1) for sv in (1, -1)]


def load_exr(path) -> np.ndarray:
    import bpy
    img = bpy.data.images.load(str(path), check_existing=False)
    try:
        w, h = img.size
        a = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(a)
        return a.reshape(h, w, 4)[::-1, :, :3].astype(np.float64)
    finally:
        bpy.data.images.remove(img)


def dihedral(a, k):
    b = np.rot90(a, k % 4)
    return b[:, ::-1] if k >= 4 else b


def gather(img, yy, xx):
    h, w = img.shape[:2]
    y0 = np.floor(yy).astype(np.int64)
    x0 = np.floor(xx).astype(np.int64)
    fy, fx = yy - y0, xx - x0
    if img.ndim == 3:
        fy, fx = fy[..., None], fx[..., None]
    ya, yb, xa, xb = y0 % h, (y0 + 1) % h, x0 % w, (x0 + 1) % w
    top = img[ya, xa] * (1 - fx) + img[ya, xb] * fx
    bot = img[yb, xa] * (1 - fx) + img[yb, xb] * fx
    return top * (1 - fy) + bot * fy


def probe_coords(probe_lin, variant):
    n = probe_lin.shape[0]
    fu = 0.5 + (probe_lin[..., 0] - 0.5) / GAIN
    fv = 0.5 + (probe_lin[..., 1] - 0.5) / GAIN
    if variant[0]:
        fu, fv = fv, fu
    r, c = np.mgrid[0:n, 0:n].astype(np.float64)
    return r + variant[2] * (fv - 0.5), c + variant[1] * (fu - 0.5)


def diff_stats(a, b) -> dict:
    d = np.abs(np.asarray(a, np.int32) - np.asarray(b, np.int32)).max(axis=-1)
    return {"max": int(d.max()), "mean": round(float(d.mean()), 5), "p99_9": float(np.percentile(d, 99.9)),
            "p99": float(np.percentile(d, 99)), "texels_gt1": int((d > 1).sum()), "texels_gt2": int((d > 2).sum()),
            "texels": int(d.size)}


def rank(x):
    o = np.argsort(x, kind="stable")
    r = np.empty(len(x), dtype=np.float64)
    r[o] = np.arange(len(x), dtype=np.float64)
    return r


def spearman(a, b, step=7):
    a, b = a.ravel()[::step], b.ravel()[::step]
    return float(np.corrcoef(rank(a), rank(b))[0, 1])


def v3_metrics(cap_lin, default_lin, colour, mask) -> dict:
    c, d0 = cap_lin[mask], default_lin[mask]
    s8 = rc.q8_srgb(c).reshape(-1, 3)
    dom = int(np.argmax(colour[:3]))
    ly = np.log(np.maximum(c.reshape(-1, 3) @ rc.LUM, 1e-7))
    ly0 = np.log(np.maximum(d0.reshape(-1, 3) @ rc.LUM, 1e-7))
    return {"clip_frac": round(float((c.reshape(-1, 3) >= 0.949).any(axis=1).mean()), 6),
            **rc.banding(s8, dom), "std_ratio_logL": round(float(ly.std() / ly0.std()), 4),
            "spearman_vs_default_capture": round(spearman(ly, ly0), 5),
            "mean_albedo": [round(float(x), 5) for x in c.reshape(-1, 3).mean(axis=0)]}


def save_levels_png(path, levels):
    a = np.concatenate([levels, np.full(levels.shape[:2] + (1,), 255, levels.dtype)], axis=-1)
    rc.png_write(path, np.clip(a, 0, 255).astype(np.int32), 8)


def main():
    doc = json.loads((CAPS / "capture_jobs.json").read_text(encoding="utf-8"))
    jobs = doc["jobs"]
    p = doc["furniture_params"]
    out = {"capture_run": {k: doc[k] for k in ("engine", "started", "shipped_baked_switch", "tint_switch_after",
                                                "bc7_texture", "scratch_removed", "errors") if k in doc},
           "params_Colour": p["Colour"], "captures": {}, "gates": {}}
    bc_lin = rc.s2l(rc.load_levels8(PROJECT / "Exports/Guns/AR01/Textures/T_AR01_Furniture_BC.png")[..., :3] / 255.0)
    d16, _, _ = rc.png_read(PROJECT / "Exports/Guns/AR01/Textures/Recolour/T_AR01_Furniture_Detail16.png")
    vals, cnts = np.unique(d16, return_counts=True)
    fill = int(vals[np.argmax(cnts)])
    cov1024 = d16 != fill
    cov = np.kron(cov1024, np.ones((2, 2), bool))
    d = d16.astype(np.float64) / 65535.0
    # orientation: the shipped default IS the BC
    raw0 = rc.q8_srgb(load_exr(jobs["fur_default"]["exr"])).astype(np.int32)
    ref0 = rc.q8_srgb(bc_lin).astype(np.int32)
    scores = [float(np.abs(dihedral(raw0, kk)[::4, ::4] - ref0[::4, ::4]).mean()) for kk in range(8)]
    k = int(np.argmin(scores))
    out["orientation"] = {"dihedral_k": k, "scores": [round(s, 3) for s in scores]}

    def cap(name):
        return dihedral(load_exr(jobs[name]["exr"]), k)

    def twin_at(yy, xx, colour, lod=0.0):
        dd = gather(d, (yy + 0.5) * 0.5 - 0.5, (xx + 0.5) * 0.5 - 0.5)
        a, _ = tw.fabric_albedo(p, dd, np.asarray(colour[:3], np.float64), lod=lod)
        return a

    # probe variant: the one that best explains the recolour path's default capture
    probe = cap("uvprobe_2048")
    tint0 = cap("fur_tint_default")
    errs = {}
    for var in VARIANTS:
        yy, xx = probe_coords(probe, var)
        sl = (slice(None, None, 3), slice(None, None, 3))
        errs[str(var)] = float(np.abs(twin_at(yy[sl], xx[sl], p["Colour"]) - tint0[sl]).mean())
    best = min(errs, key=errs.get)
    var = eval(best)  # noqa: S307 - our own tuple repr
    yy, xx = probe_coords(probe, var)
    out["probe"] = {"variant": best, "variant_errors": errs,
                    "sample_offset_texels": {"row": [float((yy - np.round(yy)).min()), float((yy - np.round(yy)).max())],
                                             "col": [float((xx - np.round(xx)).min()), float((xx - np.round(xx)).max())]}}
    bc_s = gather(bc_lin, yy, xx)
    # P1 default = BC (BC1 as shipped by the pack) and the BC7 variant
    for name in ("fur_default", "fur_default_bc7"):
        if name not in jobs or not jobs[name].get("exr"):
            continue
        lin = cap(name)
        lev = rc.q8_srgb(lin)
        rec = {"vs_BC_png": diff_stats(lev, rc.q8_srgb(bc_s)), "vs_BC_png_raw": diff_stats(lev, rc.q8_srgb(bc_lin)),
               "vs_BC_png_covered": diff_stats(lev[cov][None], rc.q8_srgb(bc_s)[cov][None])}
        de = rc.de2000(lin[cov][::5], bc_s[cov][::5])
        rec["dE00_vs_BC_covered"] = {"mean": round(float(de.mean()), 4), "p99": round(float(np.percentile(de, 99)), 4)}
        rec["gate_p999_le_2"] = bool(rec["vs_BC_png"]["p99_9"] <= 2)
        out["captures"][name] = rec
        save_levels_png(CAPS / f"{name}.png", lev)
    # P2 the recolour path at the default
    exp0 = twin_at(yy, xx, p["Colour"])
    rec = {"vs_twin": diff_stats(rc.q8_srgb(tint0), rc.q8_srgb(exp0)),
           "vs_BC_png_covered": diff_stats(rc.q8_srgb(tint0)[cov][None], rc.q8_srgb(bc_s)[cov][None]),
           "mean_covered_capture": [round(float(x), 5) for x in tint0[cov].mean(axis=0)],
           "mean_covered_BC": [round(float(x), 5) for x in bc_lin[cov].mean(axis=0)]}
    rec["gate_vs_twin"] = bool(rec["vs_twin"]["p99_9"] <= 1 and rec["vs_twin"]["mean"] <= 0.3)
    out["captures"]["fur_tint_default"] = rec
    save_levels_png(CAPS / "fur_tint_default.png", rc.q8_srgb(tint0))
    # P3 / P4 stress
    sheet = [rc.q8_srgb(bc_lin), rc.q8_srgb(tint0)]
    full = rc.block_mean(cov.astype(np.float64), 16) >= 1.0
    drift = {}
    for name in ["fur_tint_default"] + [n for n in doc["order"] if jobs[n].get("kind") == "fur_stress"]:
        if name != "fur_tint_default":
            lin = cap(name)
            col = jobs[name]["colour"]
            exp = twin_at(yy, xx, col)
            rec = {"hex": jobs[name]["hex"], "vs_twin": diff_stats(rc.q8_srgb(lin), rc.q8_srgb(exp)),
                   "v3": v3_metrics(lin, tint0, np.asarray(col), cov)}
            v = rec["v3"]
            rec["gate_vs_twin"] = bool(rec["vs_twin"]["p99_9"] <= 2)
            rec["gate_v3"] = bool(v["clip_frac"] <= 0.001 and v["pass"] and v["std_ratio_logL"] >= 0.25
                                  and v["spearman_vs_default_capture"] >= 0.98)
            out["captures"][name] = rec
            sheet.append(rc.q8_srgb(lin))
            m4name = name.replace("_m0", "_m4")
        else:
            lin, m4name = tint0, "fur_tint_default_m4"
        m4 = cap(m4name)
        truth = rc.block_mean(lin, 16)
        lum_t = (truth[full] @ rc.LUM).mean()
        lum_4 = (m4[full] @ rc.LUM).mean()
        ratio = float(lum_4 / max(lum_t, 1e-9))
        drift[name] = {"luminance_ratio_mip4": round(ratio, 5),
                       "rgb_ratio_mip4": [round(float(a / max(b, 1e-9)), 5) for a, b in
                                          zip(m4[full].mean(axis=0), truth[full].mean(axis=0))],
                       "blocks": int(full.sum()), "pass": bool(abs(ratio - 1.0) <= 0.02)}
    out["mip_drift"] = drift
    tiles = []
    for lev in sheet:
        f = lev.shape[0] // 256
        tiles.append(np.rint(lev.reshape(256, f, 256, f, 3).mean(axis=(1, 3))).astype(np.int32))
    rows = [np.concatenate(tiles[i:i + 6], axis=1) for i in range(0, 12, 6)]
    save_levels_png(CAPS / "stress_sheet_AR01_Furniture.png", np.concatenate(rows, axis=0))
    out["stress_sheet"] = {"file": "WorkFiles/guns/rifle/scratch/pack_captures/stress_sheet_AR01_Furniture.png",
                           "order": ["BC png", "tint default"] + [jobs[n]["hex"] for n in doc["order"]
                                                                  if jobs[n].get("kind") == "fur_stress"]}
    # R1 steel
    for name, size in (("metal_default", 4096), ("mag_default", 1024)):
        lin = cap(name)
        pr = cap(f"uvprobe_{size}")
        sy, sx = probe_coords(pr, var)
        ref = rc.s2l(rc.load_levels8(PROJECT / jobs[name]["reference_png"])[..., :3] / 255.0)
        lev = rc.q8_srgb(lin)
        out["captures"][name] = {"vs_BC_png": diff_stats(lev, rc.q8_srgb(gather(ref, sy, sx))),
                                 "note": "the steel IS the BC map: BC1 (DXT1) block error, reported, not gated (pack rule)"}
    stress = [r for n, r in out["captures"].items() if n.startswith("fur_") and "hex" in r]
    out["gates"] = {
        "P1_default_capture_equals_BC_p999_le_2": out["captures"]["fur_default"]["gate_p999_le_2"],
        "P1_bc7_variant_p999_le_2": out["captures"].get("fur_default_bc7", {}).get("gate_p999_le_2"),
        "P2_recolour_default_equals_twin": out["captures"]["fur_tint_default"]["gate_vs_twin"],
        "P3_stress_10_vs_twin": all(r["gate_vs_twin"] for r in stress) and len(stress) == 10,
        "P3_stress_10_v3": all(r["gate_v3"] for r in stress) and len(stress) == 10,
        "P3_v3_failures": [r["hex"] for r in stress if not r["gate_v3"]],
        "P4_mip_drift_le_2pct": all(v["pass"] for v in drift.values()) and len(drift) == 11}
    OUT_JSON.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    if not KEEP:
        for j in jobs.values():
            if j.get("exr"):
                Path(j["exr"]).unlink(missing_ok=True)
    print("AR01_ANALYSE_DONE", json.dumps(out["gates"]), json.dumps(out["orientation"]))


main()
