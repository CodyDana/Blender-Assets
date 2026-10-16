"""SR-01 pack-colours gates, analysis half (Blender headless; reads files, writes WorkFiles only).
WorkFiles/guns/smg/materials/smg01_pack_analyse.py adapted to the sniper: one recolourable set (chassis, the OD paint;
tint captures at the Detail16's size, default captures at the BC's size), one gated baked set (mag, M_Steel_Master) and
three reported steel sets (metal, scope body, scope lens).

    blender -b --factory-startup --python WorkFiles/guns/sniper/pack/sr01_pack_analyse.py -- [--keep-exr]

Reads the EXRs sr01_ue_capture.py wrote (SR01_CAPTURE_OUT, default WorkFiles/guns/sniper/scratch/pack_captures) and
evaluates them with the pack's own math (SR01_PACK_DIR/maps: np_twin.fabric_albedo = MF_TintDetail +
MF_AlbedoRollOff in float64, recolour_common), the pack's metrics and the UV-probe sample positions:

    P1 default capture = shipped BC (chassis, mag): the shipped instance vs its BC PNG bilinearly sampled at the measured
       sample positions: p99.9 <= 2 stored levels (the shipped compression; the other compression measured beside it)
    P2 the chassis recolour path at the default Colour vs the twin, OD texels: p99.9 <= 1 level, mean <= 0.3
    P3a 13-colour stress (10 + tan / OD / FDE) on the chassis OD texels (mip 0) vs the twin: p99.9 <= 1 level per colour
    P3b the pack's v3 gate on the same captures (clip <= 0.1 %, banding, std ratio >= 0.25, Spearman >= 0.98): reported
    P4 mip drift: every colour's mip-4 capture mean (16 x 16 fully covered blocks) vs the box-filtered mip-0 capture:
       within 2 %
    R1 the steel sets (metal, scope body, scope lens) vs their BC PNG: BC1 error, reported (the pack does not gate steel)
Writes WorkFiles/guns/sniper/gates/pack_materials_captures.json, level PNGs and a stress sheet in the capture folder
(scratch, not in git); EXRs deleted unless --keep-exr. Exit 1 if the captures are missing or errored.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
PACK = Path(os.environ.get("SR01_PACK_DIR") or ROOT / "Scripts/unreal/materials")
sys.path.insert(0, str(PACK / "maps"))
import np_twin as tw  # noqa: E402
import recolour_common as rc  # noqa: E402

PROJECT = PACK.parents[2]
CAPS = Path(os.environ.get("SR01_CAPTURE_OUT") or ROOT / "WorkFiles/guns/sniper/scratch/pack_captures")
OUT_JSON = ROOT / "WorkFiles/guns/sniper/gates/pack_materials_captures.json"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KEEP = "--keep-exr" in ARGS
GAIN = 8.0
VARIANTS = [(sw, su, sv) for sw in (False, True) for su in (1, -1) for sv in (1, -1)]
DET = {"chassis": "Exports/Guns/SR01/Textures/Recolour/T_SR01_Chassis_Detail16.png"}


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
    if doc.get("errors"):
        print("SR01_ANALYSE_FAILED capture errors:", doc["errors"])
        return 1
    jobs = doc["jobs"]
    out = {"capture_run": {k: doc[k] for k in ("engine", "started", "shipped_baked_switch", "tint_switch_after",
                                                "shipped_bc_compression", "alt_texture", "scratch_removed", "errors")
                           if k in doc},
           "captures": {}, "sets": {}, "baked": {}, "gates": {}}
    # orientation: the shipped default IS the BC (from the chassis at its BC size)
    cs = doc["sets"]["chassis"]
    bc_c = rc.s2l(rc.load_levels8(PROJECT / cs["bc"])[..., :3] / 255.0)
    raw0 = rc.q8_srgb(load_exr(jobs["chassis_default"]["exr"])).astype(np.int32)
    ref0 = rc.q8_srgb(bc_c).astype(np.int32)
    scores = [float(np.abs(dihedral(raw0, kk)[::8, ::8] - ref0[::8, ::8]).mean()) for kk in range(8)]
    k = int(np.argmin(scores))
    out["orientation"] = {"dihedral_k": k, "scores": [round(s, 3) for s in scores]}
    del raw0, ref0, bc_c

    def cap(name):
        return dihedral(load_exr(jobs[name]["exr"]), k)

    def p1(key, s, v, cov_bc=None):
        """P1 for one set: shipped default and the other compression vs the BC PNG at the BC's size"""
        bc_lin = rc.s2l(rc.load_levels8(PROJECT / s["bc"])[..., :3] / 255.0)
        if bc_lin.shape[0] != s["bc_size"]:
            raise SystemExit(f"{s['bc']}: size {bc_lin.shape[0]} != {s['bc_size']}")
        py, px = probe_coords(cap(f"uvprobe_{s['bc_size']}"), v)
        bc_s = gather(bc_lin, py, px)
        del py, px, bc_lin
        for name in (f"{key}_default", f"{key}_default_alt"):
            if name not in jobs or not jobs[name].get("exr"):
                continue
            lin = cap(name)
            lev = rc.q8_srgb(lin)
            ref = rc.q8_srgb(bc_s)
            rec = {"compression": (doc.get("shipped_bc_compression", {}).get(key) if name.endswith("_default")
                                   else jobs[name].get("label")),
                   "vs_BC_png": diff_stats(lev, ref)}
            m = cov_bc if cov_bc is not None else np.ones(lev.shape[:2], bool)
            if cov_bc is not None:
                rec["vs_BC_png_covered"] = diff_stats(lev[m][None], ref[m][None])
            de = rc.de2000(lin[m][::7], bc_s[m][::7])
            rec["dE00_vs_BC"] = {"mean": round(float(de.mean()), 4), "p99": round(float(np.percentile(de, 99)), 4)}
            rec["gate_p999_le_2"] = bool(rec["vs_BC_png"]["p99_9"] <= 2)
            out["captures"][name] = rec
            if s["bc_size"] <= 2048:
                save_levels_png(CAPS / f"{name}.png", lev)
            else:
                save_levels_png(CAPS / f"{name}_half.png",
                                np.rint(rc.block_mean(lev.astype(np.float64), 2)).astype(np.int32))
            del lin, lev, ref
        return bc_s

    var = None
    all_drift, all_stress = {}, []
    for key, s in doc["sets"].items():
        p = doc["params"][key]
        so = {"params_Colour": p["Colour"]}
        d16, _, _ = rc.png_read(PROJECT / DET[key])
        vals, cnts = np.unique(d16, return_counts=True)
        fill = int(vals[np.argmax(cnts)])
        cov = d16 != fill
        d = d16.astype(np.float64) / 65535.0
        n = s["det_size"]
        tint0 = cap(f"{key}_tint_default")
        probe = cap(f"uvprobe_{n}")

        def twin_at(yy, xx, colour, lod=0.0):
            dd = gather(d, yy, xx)
            a, _ = tw.fabric_albedo(p, dd, np.asarray(colour[:3], np.float64), lod=lod)
            return a

        errs = {}
        for v in VARIANTS:
            yy, xx = probe_coords(probe, v)
            sl = (slice(None, None, 3), slice(None, None, 3))
            m = cov[sl]
            errs[str(v)] = float(np.abs(twin_at(yy[sl], xx[sl], p["Colour"]) - tint0[sl])[m].mean())
        best = min(errs, key=errs.get)
        v = eval(best)  # noqa: S307 - our own tuple repr
        var = var or v
        yy, xx = probe_coords(probe, v)
        so["probe"] = {"variant": best, "variant_errors": errs,
                       "sample_offset_texels": {"row": [float((yy - np.round(yy)).min()), float((yy - np.round(yy)).max())],
                                                "col": [float((xx - np.round(xx)).min()), float((xx - np.round(xx)).max())]}}
        f = s["bc_size"] // n
        cov_bc = np.kron(cov, np.ones((f, f), bool)) if f > 1 else cov
        bc_s = p1(key, s, v, cov_bc)
        bc_s_det = rc.block_mean(bc_s, f) if f > 1 else bc_s
        del bc_s, cov_bc
        # P2 the recolour path at the default (OD texels)
        exp0 = twin_at(yy, xx, p["Colour"])
        rec = {"vs_twin": diff_stats(rc.q8_srgb(tint0)[cov][None], rc.q8_srgb(exp0)[cov][None]),
               "vs_twin_all_texels": diff_stats(rc.q8_srgb(tint0), rc.q8_srgb(exp0)),
               "vs_BC_png_covered_at_detail_size": diff_stats(rc.q8_srgb(tint0)[cov][None],
                                                              rc.q8_srgb(bc_s_det)[cov][None]),
               "mean_covered_capture": [round(float(x), 5) for x in tint0[cov].mean(axis=0)],
               "mean_covered_BC": [round(float(x), 5) for x in bc_s_det[cov].mean(axis=0)]}
        rec["gate_vs_twin"] = bool(rec["vs_twin"]["p99_9"] <= 1 and rec["vs_twin"]["mean"] <= 0.3)
        out["captures"][f"{key}_tint_default"] = rec
        save_levels_png(CAPS / f"{key}_tint_default.png", rc.q8_srgb(tint0))
        # P3 / P4 stress
        sheet = [rc.q8_srgb(bc_s_det), rc.q8_srgb(tint0)]
        full = rc.block_mean(cov.astype(np.float64), 16) >= 1.0
        stress_names = [nm for nm in doc["order"] if jobs[nm].get("kind") == "stress" and jobs[nm].get("set") == key]
        drift, stress = {}, []
        for name in [f"{key}_tint_default"] + stress_names:
            if name != f"{key}_tint_default":
                lin = cap(name)
                col = jobs[name]["colour"]
                exp = twin_at(yy, xx, col)
                rec = {"hex": jobs[name]["hex"],
                       "vs_twin": diff_stats(rc.q8_srgb(lin)[cov][None], rc.q8_srgb(exp)[cov][None]),
                       "v3": v3_metrics(lin, tint0, np.asarray(col), cov)}
                v3 = rec["v3"]
                rec["gate_vs_twin"] = bool(rec["vs_twin"]["p99_9"] <= 1)
                rec["gate_v3"] = bool(v3["clip_frac"] <= 0.001 and v3["pass"] and v3["std_ratio_logL"] >= 0.25
                                      and v3["spearman_vs_default_capture"] >= 0.98)
                out["captures"][name] = rec
                stress.append(rec)
                sheet.append(rc.q8_srgb(lin))
                m4name = name.replace("_m0", "_m4")
            else:
                lin, m4name = tint0, f"{key}_tint_default_m4"
            m4 = cap(m4name)
            truth = rc.block_mean(lin, 16)
            lum_t = (truth[full] @ rc.LUM).mean()
            lum_4 = (m4[full] @ rc.LUM).mean()
            ratio = float(lum_4 / max(lum_t, 1e-9))
            drift[name] = {"luminance_ratio_mip4": round(ratio, 5),
                           "rgb_ratio_mip4": [round(float(a / max(b, 1e-9)), 5) for a, b in
                                              zip(m4[full].mean(axis=0), truth[full].mean(axis=0))],
                           "blocks": int(full.sum()), "pass": bool(abs(ratio - 1.0) <= 0.02)}
        tiles = []
        for lev in sheet:
            ff = lev.shape[0] // 256
            tiles.append(np.rint(lev.reshape(256, ff, 256, ff, 3).mean(axis=(1, 3))).astype(np.int32))
        while len(tiles) % 5:
            tiles.append(np.full_like(tiles[0], 255))
        rows = [np.concatenate(tiles[i:i + 5], axis=1) for i in range(0, len(tiles), 5)]
        save_levels_png(CAPS / f"stress_sheet_SR01_{key}.png", np.concatenate(rows, axis=0))
        so["stress_sheet"] = {"file": (CAPS / f"stress_sheet_SR01_{key}.png").as_posix(),
                              "order": ["BC png (detail size)", "tint default"] + [jobs[nm]["hex"] for nm in stress_names]}
        so["mip_drift"] = drift
        so["gates"] = {
            "P1_default_capture_equals_BC_p999_le_2": out["captures"][f"{key}_default"]["gate_p999_le_2"],
            "P1_alt_compression_p999_le_2": out["captures"].get(f"{key}_default_alt", {}).get("gate_p999_le_2"),
            "P2_recolour_default_equals_twin": out["captures"][f"{key}_tint_default"]["gate_vs_twin"],
            "P3a_stress_13_vs_twin_le_1": all(r["gate_vs_twin"] for r in stress) and len(stress) == 13,
            "P3b_stress_13_v3": all(r["gate_v3"] for r in stress) and len(stress) == 13,
            "P3b_v3_failures": [r["hex"] for r in stress if not r["gate_v3"]],
            "P3a_twin_failures": [r["hex"] for r in stress if not r["gate_vs_twin"]],
            "P4_mip_drift_le_2pct": all(x["pass"] for x in drift.values()) and len(drift) == 14}
        out["sets"][key] = so
        all_drift.update(drift)
        all_stress += stress
        del tint0, probe, d, d16
    # P1 on the baked (non-recolourable) gated sets
    for key, s in doc["baked"].items():
        p1(key, s, var)
        out["baked"][key] = {
            "P1_default_capture_equals_BC_p999_le_2": out["captures"][f"{key}_default"]["gate_p999_le_2"],
            "P1_alt_compression_p999_le_2": out["captures"].get(f"{key}_default_alt", {}).get("gate_p999_le_2")}
    # R1 steel
    for key, s in doc["steel"].items():
        lin = cap(f"{key}_default")
        sy, sx = probe_coords(cap(f"uvprobe_{s['bc_size']}"), var)
        ref = rc.s2l(rc.load_levels8(PROJECT / s["bc"])[..., :3] / 255.0)
        out["captures"][f"{key}_default"] = {"vs_BC_png": diff_stats(rc.q8_srgb(lin), rc.q8_srgb(gather(ref, sy, sx))),
                                             "note": "steel IS the BC map: BC1 (DXT1) block error, reported, not "
                                                     "gated (pack rule)"}
    g = {key: so["gates"] for key, so in out["sets"].items()}
    p1g = {k2: v2["P1_default_capture_equals_BC_p999_le_2"] for k2, v2 in (*g.items(), *out["baked"].items())}
    out["gates"] = {
        "P1_default_capture_equals_BC_p999_le_2": p1g,
        "P1_pass": all(p1g.values()),
        "P1_alt_compression_p999_le_2": {k2: v2["P1_alt_compression_p999_le_2"]
                                         for k2, v2 in (*g.items(), *out["baked"].items())},
        "P2_recolour_default_equals_twin": all(v2["P2_recolour_default_equals_twin"] for v2 in g.values()),
        "P3a_stress_vs_twin_le_1": all(v2["P3a_stress_13_vs_twin_le_1"] for v2 in g.values()),
        "P3b_stress_v3": all(v2["P3b_stress_13_v3"] for v2 in g.values()),
        "P4_mip_drift_le_2pct": all(v2["P4_mip_drift_le_2pct"] for v2 in g.values()),
        "worst_stress_twin_level_p999": max(r["vs_twin"]["p99_9"] for r in all_stress),
        "worst_mip_drift": round(max(abs(x["luminance_ratio_mip4"] - 1.0) for x in all_drift.values()), 5)}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    if not KEEP:
        for j in jobs.values():
            if j.get("exr"):
                Path(j["exr"]).unlink(missing_ok=True)
    print("SR01_ANALYSE_DONE", json.dumps(out["gates"]), json.dumps(out["orientation"]))
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
