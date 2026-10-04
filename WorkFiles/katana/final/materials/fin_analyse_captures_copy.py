"""Analyse Unreal's UV-plane base-colour captures (Blender headless; reads files only, writes WorkFiles only).

    blender -b --factory-startup --python analyse_captures.py -- [--keep-exr]

Input: WorkFiles/materials/ue_renders/captures/capture_jobs.json + the EXRs np_render.py wrote (SCS_BASE_COLOR = the
GBuffer's 8-bit sRGB base colour, decoded; re-quantising to stored levels is exact).

For every capture the EXPECTED image is the material graph evaluated in float64 numpy (the "twin": MF_TintDetail +
MF_AlbedoRollOff, or the paper/ink recomposition with MF_InkDerive, the same math as recolour_common.py) on the SAME PNG
maps Unreal samples. Default instances are also compared with the shipped BC PNG (the look contract).

Capture geometry. The engine Plane does not map its UVs onto the capture's pixel grid exactly: measured, the texel under
a pixel drifts by up to ~0.03 texel towards the edges (the same in a 4x4-tiled capture, so it is the plane's UV mapping,
not the camera; a Nearest-filtered sample is therefore useless and a Bilinear one blends a few % of the neighbour at
the edges). On a high-contrast texel (a thread against the dark weave) that shows as up to tens of levels on isolated
texels, while a pure texture sample (no material math) shows the same error (build/debug_sampling). So each part's
per-axis affine texel mapping (offset + scale) is FITTED on its default capture (8 x 8 tiles, sub-texel shift search,
linear regression), and the expected images are also computed from the maps RESAMPLED (bilinear, wrap) at that mapping,
before the (non-linear) graph math, as the GPU does. UPDATE: the mapping is now MEASURED per pixel instead of fitted:
np_render captures a transient "UV probe" material (BaseColor = frac(u*N), frac(v*N)) at every capture's own place,
which records where inside its texel each pixel sampled (to ~0.002 texel); the expected images are the graph applied
to the maps bilinearly sampled at exactly those positions. Both the raw and the geometry-corrected statistics are reported;
the gates use the corrected ones.

Outputs: ue_renders/uv_capture_analysis.json, ue_renders/basecolour/<capture>.png (stored levels of every default
capture, lossless), ue_renders/basecolour/stress_sheet_<part>.png; the EXRs are deleted unless --keep-exr.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/unreal/materials/verify")
sys.path.insert(0, str(HERE.parent / "maps"))
import np_twin as tw  # noqa: E402  (v2 twin: the final-pass graphs, node for node)
import recolour_common as rc  # noqa: E402

PROJECT = rc.PROJECT
R = rc.WORK / "ue_renders"
CAPS = R / "captures"
OUTDIR = R / "basecolour"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KEEP = "--keep-exr" in ARGS
ONLY = ARGS[ARGS.index("--only") + 1] if "--only" in ARGS else None      # debugging: analyse a subset, write nothing


# ----------------------------------------------------------------------------------------------------------- io
def load_exr(path) -> np.ndarray:
    import bpy
    img = bpy.data.images.load(str(path), check_existing=False)
    try:
        w, h = img.size
        a = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(a)
        return a.reshape(h, w, 4)[::-1, :, :3].astype(np.float64)       # row 0 at the top, as the PNGs
    finally:
        bpy.data.images.remove(img)


def dihedral(a, k):
    b = np.rot90(a, k % 4)
    return b[:, ::-1] if k >= 4 else b


def save_levels_png(path, levels):
    a = np.concatenate([levels, np.full(levels.shape[:2] + (1,), 255, levels.dtype)], axis=-1)
    rc.png_write(path, np.clip(a, 0, 255).astype(np.int32), 8)


# ----------------------------------------------------------------------------------------------------------- geometry
# ----------------------------------------------------------------------------------------------------------- twins
def fabric_inputs(job):
    """KATANA FINALISER COPY: (1) a Detail map smaller than the BC (katana: 1024 detail, 2048 BC) is bilinearly
    upsampled onto the BC's texel grid (texel centres), as the GPU samples it at the same UV; (2) for a part with
    'Metal From ORM' on, the baked BC and the master's keep weight max(ORM.B, sat((lum(BC) - 0.2) x 5)) are inputs too,
    so the twin includes the keep lerp."""
    d16, _, _ = rc.png_read(PROJECT / job["detail_png"])
    d = d16.astype(np.float64) / 65535.0
    bc = rc.s2l(rc.load_levels8(PROJECT / job["reference_png"])[..., :3] / 255.0)
    n = bc.shape[0]
    if d.shape[0] != n:
        f = d.shape[0] / n
        r, c = np.mgrid[0:n, 0:n].astype(np.float64)
        d = gather(d, (r + 0.5) * f - 0.5, (c + 0.5) * f - 0.5)
    out = {"d": d}
    if bool(job["params"].get("Metal From ORM", False)):
        orm = rc.load_levels8(PROJECT / job["reference_png"].replace("_BC.png", "_ORM.png"))[..., :3] / 255.0
        keep = np.maximum(orm[..., 2], np.clip((bc @ np.array([0.2126, 0.7152, 0.0722]) - 0.2) * 5.0, 0, 1))
        out["bc"] = bc
        out["keep"] = keep
    return out


def fabric_model(job, inp, colour):
    """v2 twin (np_twin.fabric_albedo) at mip 0: the captures sample mip 0 (one pixel per texel), so K = 1.
    (finaliser copy: + the Metal From ORM keep lerp when the part has it)"""
    a, info = tw.fabric_albedo(job["params"], inp["d"], colour, lod=0.0)
    if "keep" in inp:
        k = inp["keep"][..., None]
        a = a * (1 - k) + inp["bc"] * k
    return a, {k: v for k, v in info.items() if isinstance(v, float)}


def paper_inputs(job):
    pd, _, _ = rc.png_read(PROJECT / job["paper_detail_png"])
    iw, _, _ = rc.png_read(PROJECT / job["ink_weights_png"])
    orm = rc.load_levels8(PROJECT / job["orm_png"])
    return {"pd_rgb": rc.s2l(pd[..., :3] / 255.0), "pd_a": pd[..., 3:4] / 255.0, "iw": iw / 255.0,
            "ao": orm[..., 0:1] / 255.0}


def paper_model(job, inp, overrides):
    """v2 twin (np_twin.paper_albedo): paper colour guards, neutral red pool, the art's 0.962 ceiling, AO in colour."""
    p = dict(job["params"])
    for key, v in overrides.items():
        p[key] = v
    tot, _, der = tw.paper_albedo(p, inp, ao_in_colour=float(p.get("Baked AO In Colour", 1.0)))
    return tot, der


def gather(img, yy, xx):
    """Bilinear sample (wrap) of img at per-pixel coordinates yy, xx (texel units, texel centres at integers)."""
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


PROBE_VARIANTS = [(sw, su, sv) for sw in (False, True) for su in (1, -1) for sv in (1, -1)]


PROBE_GAIN = 8.0     # np_render.PROBE_GAIN: the probe stores 0.5 + gain x (offset from the texel centre)


def probe_coords(probe_lin, variant):
    """Texel coordinates of every capture pixel from the UV probe (after the orientation transform)."""
    n = probe_lin.shape[0]
    fu = 0.5 + (probe_lin[..., 0] - 0.5) / PROBE_GAIN
    fv = 0.5 + (probe_lin[..., 1] - 0.5) / PROBE_GAIN
    if variant[0]:
        fu, fv = fv, fu
    r, c = np.mgrid[0:n, 0:n].astype(np.float64)
    return r + variant[2] * (fv - 0.5), c + variant[1] * (fu - 0.5)


def resample_inputs(inp, yy, xx):
    return {k: gather(v, yy, xx) for k, v in inp.items()}


# ----------------------------------------------------------------------------------------------------------- metrics
def diff_stats(a, b) -> dict:
    d = np.abs(np.asarray(a, np.int32) - np.asarray(b, np.int32)).max(axis=-1)
    return {"max": int(d.max()), "mean": round(float(d.mean()), 5), "p99_9": float(np.percentile(d, 99.9)),
            "texels_gt0": int((d > 0).sum()), "texels_gt1": int((d > 1).sum()), "texels_gt2": int((d > 2).sum()),
            "texels": int(d.size)}


def rank(x):
    o = np.argsort(x, kind="stable")
    r = np.empty(len(x), dtype=np.float64)
    r[o] = np.arange(len(x), dtype=np.float64)
    return r


def spearman(a, b, step=7):
    a, b = a.ravel()[::step], b.ravel()[::step]
    return float(np.corrcoef(rank(a), rank(b))[0, 1])


def v3_metrics(cap_lin, default_lin, colour) -> dict:
    s8 = rc.q8_srgb(cap_lin).reshape(-1, 3)
    dom = int(np.argmax(colour))
    ly = np.log(np.maximum(cap_lin.reshape(-1, 3) @ rc.LUM, 1e-7))
    ly0 = np.log(np.maximum(default_lin.reshape(-1, 3) @ rc.LUM, 1e-7))
    return {"clip_frac": round(float((cap_lin.reshape(-1, 3) >= 0.949).any(axis=1).mean()), 6),
            **rc.banding(s8, dom), "std_ratio_logL": round(float(ly.std() / ly0.std()), 4),
            "spearman_vs_default_capture": round(spearman(ly, ly0), 5),
            "mean_albedo": rc.rnd(cap_lin.reshape(-1, 3).mean(axis=0), 5)}


def gate_twin(s):
    """The default-look gate (MATERIAL_PLAN V2): p99.9 <= 1 stored level and mean <= 0.3."""
    return bool(s["p99_9"] <= 1 and s["mean"] <= 0.3)


def gate_stress_twin(s):
    """Recolour captures vs the twin: the GPU's pow/exp/log differ from float64 by a fraction of a level, which
    rounds to 1 level on many texels of a LIGHT colour (finer sRGB steps); gate p99.9 <= 2."""
    return bool(s["p99_9"] <= 2)


# ----------------------------------------------------------------------------------------------------------- main
def main():
    jobs_doc = json.loads((CAPS / "capture_jobs.json").read_text(encoding="utf-8"))
    jobs = {j["name"]: j for j in jobs_doc["jobs"]}
    results = jobs_doc["results"]
    out = {"orientation": None, "captures": {}, "mappings": {}, "method": __doc__.split("Outputs:")[0].strip()}
    OUTDIR.mkdir(parents=True, exist_ok=True)
    names = [n for n in jobs if n in results and results[n].get("exr") and not n.startswith("uvprobe")]
    first = next(n for n in names if jobs[n]["kind"] == "fabric_default")
    ref0 = rc.load_levels8(PROJECT / jobs[first]["reference_png"])[..., :3].astype(np.int32)
    raw0 = rc.q8_srgb(load_exr(results[first]["exr"])).astype(np.int32)
    scores = [float(np.abs(dihedral(raw0, kk)[::4, ::4] - ref0[::4, ::4]).mean()) for kk in range(8)]
    k = int(np.argmin(scores))
    out["orientation"] = {"from": first, "dihedral_k": k, "scores": [round(s, 4) for s in scores]}
    defaults, sheets, inputs, mappings = {}, {}, {}, {}
    probes_at = {v["at_job"]: p for p, v in jobs_doc["probes"].items()}
    # steel captures come first in the job list: analyse them last so they reuse a measured probe variant
    names = [n for n in names if jobs[n]["kind"] != "steel_default"] + [n for n in names if jobs[n]["kind"] == "steel_default"]
    if ONLY:
        names = [n for n in names if ONLY in n]
    for name in names:
        job = jobs[name]
        slot, kind = job["slot"], job["kind"]
        lin = dihedral(load_exr(results[name]["exr"]), k)
        lev = rc.q8_srgb(lin)
        rec = {"kind": kind, "slot": slot, "overrides": job["overrides"], "size": list(lev.shape[:2])}
        bc_lin = rc.s2l(rc.load_levels8(PROJECT / job["reference_png"])[..., :3] / 255.0)
        if kind == "steel_default":
            probe = dihedral(load_exr(results[probes_at[name]]["exr"]), k)
            yy, xx = probe_coords(probe, eval(next(iter(mappings.values()))["variant"]) if mappings else (False, 1, 1))
            rec["vs_BC_png_raw"] = diff_stats(lev, rc.q8_srgb(bc_lin))
            rec["vs_BC_png"] = diff_stats(lev, rc.q8_srgb(gather(bc_lin, yy, xx)))
            rec["note"] = "the steel IS the BC map: this is BC1 (DXT1) block-compression error, reported, not gated"
            save_levels_png(OUTDIR / f"{name}.png", lev)
        else:
            if slot not in inputs:
                inputs[slot] = fabric_inputs(job) if kind.startswith("fabric") else paper_inputs(job)
            inp = inputs[slot]
            probe = dihedral(load_exr(results[probes_at[name]]["exr"]), k)
            if slot not in mappings:
                # which probe channel / sign is which texture axis: the variant that best explains this slot's default
                dname = name if kind in ("fabric_default",) else name.replace("_default_aoon", "_default")
                dlin = lin if dname == name else dihedral(load_exr(results[dname]["exr"]), k)
                errs = {}
                for var in PROBE_VARIANTS:
                    yy, xx = probe_coords(probe, var)
                    sl = (slice(None, None, 3), slice(None, None, 3))
                    sub = {kk: gather(v, yy[sl], xx[sl]) for kk, v in inp.items()}
                    e, _ = (fabric_model(jobs[dname], sub, jobs[dname]["params"]["Colour"][:3]) if kind.startswith("fabric")
                            else paper_model(jobs[dname], sub, jobs[dname]["overrides"]))
                    errs[str(var)] = float(np.abs(e - dlin[sl]).mean())
                best = min(errs, key=errs.get)
                mappings[slot] = {"variant": best, "variant_errors": errs}
            var = eval(mappings[slot]["variant"])  # noqa: S307 - our own tuple repr
            yy, xx = probe_coords(probe, var)
            m = {"probe": probes_at[name], "variant": mappings[slot]["variant"],
                 "sample_offset_texels": {"row_min": float((yy - np.round(yy)).min()), "row_max": float((yy - np.round(yy)).max()),
                                          "col_min": float((xx - np.round(xx)).min()), "col_max": float((xx - np.round(xx)).max())}}
            rinp = resample_inputs(inp, yy, xx)
            if kind.startswith("fabric"):
                colour = job["overrides"].get("Colour", job["params"]["Colour"])[:3]
                exp_raw, info = fabric_model(job, inp, colour)
                exp, _ = fabric_model(job, rinp, colour)
                rec["twin_info"] = {kk: round(v, 5) for kk, v in info.items()}
                rec["colour"] = colour
            else:
                exp_raw, der = paper_model(job, inp, job["overrides"])
                exp, _ = paper_model(job, rinp, job["overrides"])
                rec["derived_colours"] = der
                rec["derived_inside_0_1"] = bool(all(0 <= x <= 1 for vv in der.values() for x in vv))
            rec["mapping"] = m
            rec["vs_twin_raw"] = diff_stats(lev, rc.q8_srgb(exp_raw))
            rec["vs_twin"] = diff_stats(lev, rc.q8_srgb(exp))
            rec["gate_vs_twin"] = gate_twin(rec["vs_twin"]) if "default" in kind else gate_stress_twin(rec["vs_twin"])
            if kind in ("fabric_default", "paper_default"):
                bc_s = gather(bc_lin, yy, xx)
                rec["vs_BC_png_raw"] = diff_stats(lev, rc.q8_srgb(bc_lin))
                rec["vs_BC_png"] = diff_stats(lev, rc.q8_srgb(bc_s))
                rec["twin_vs_BC_png"] = diff_stats(rc.q8_srgb(exp_raw), rc.q8_srgb(bc_lin))
                de = rc.de2000(lin.reshape(-1, 3)[::3], bc_s.reshape(-1, 3)[::3])
                rec["dE00_vs_BC"] = {"mean": round(float(de.mean()), 4), "p99": round(float(np.percentile(de, 99)), 4),
                                     "max": round(float(de.max()), 4)}
                # the look contract: the twin equals the shipped BC at every texel centre (generator gates: 0 levels
                # for the smoke bomb and hat, <= 2 for the kunai wrap, <= 1 for the paper), so the default gate is the
                # capture vs the twin; the direct capture-vs-BC figures are reported beside it (resampling an 8-bit
                # BC adds its own rounding)
                rec["gate_default_equals_BC"] = gate_twin(rec["vs_twin"])
                defaults[slot] = lin
                save_levels_png(OUTDIR / f"{name}.png", lev)
            elif kind == "paper_default_ao":
                rec["note"] = ("Baked AO In Colour = 1 (the shipped default = the gallery's BC x ORM.R), compared with "
                               "the twin x the ORM PNG's R. Unreal samples the DXT1-compressed ORM, so the block "
                               "error of the AO shows here; the AO-off capture is the base-colour contract check")
                rec.pop("gate_vs_twin")
                save_levels_png(OUTDIR / f"{name}.png", lev)
            else:
                rec["v3"] = v3_metrics(lin, defaults[slot], rec.get("colour") or job["overrides"][job["part"]][:3])
                v = rec["v3"]
                if kind == "fabric_stress":
                    rec["gate_v3"] = bool(v["clip_frac"] <= 0.001 and v["pass"] and v["std_ratio_logL"] >= 0.25
                                          and v["spearman_vs_default_capture"] >= 0.98)
                else:
                    rec["part"] = job["part"]
                sheets.setdefault(slot, []).append((name, lev))
        out["captures"][name] = rec
        print("[analyse]", name, json.dumps({kk: rec.get(kk) for kk in ("vs_BC_png", "vs_twin")})[:320], flush=True)
    out["mappings"] = mappings
    for slot, items in sheets.items():
        tiles = []
        for _name, lev in [(f"uv_{slot}_default", rc.q8_srgb(defaults[slot]))] + items:
            h = lev.shape[0]
            f = max(1, h // 512)
            t = lev[: h // f * f, : h // f * f].reshape(h // f, f, h // f, f, 3).mean(axis=(1, 3))
            tiles.append(np.rint(t).astype(np.int32))
        save_levels_png(OUTDIR / f"stress_sheet_{slot}.png", np.concatenate(tiles, axis=1))
        out.setdefault("stress_sheets", {})[slot] = ["default"] + [n for n, _ in items]
    caps = out["captures"].values()
    out["summary"] = {
        "defaults_equal_BC": {r["slot"]: r["gate_default_equals_BC"] for r in caps if "gate_default_equals_BC" in r},
        "all_vs_twin": all(r.get("gate_vs_twin", True) for r in caps),
        "vs_twin_failures": [n for n, r in out["captures"].items() if r.get("gate_vs_twin") is False],
        "all_v3_fabric": all(r.get("gate_v3", True) for r in caps),
        "v3_failures": [n for n, r in out["captures"].items() if r.get("gate_v3") is False]}
    if ONLY:
        print("ONLY", ONLY, json.dumps(out["summary"]), json.dumps(mappings))
        Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/katana/final/materials/uv_capture_analysis_katana_only.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
        return
    (R / "uv_capture_analysis.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    if not KEEP:
        for name, r in results.items():
            if r.get("exr"):
                Path(r["exr"]).unlink(missing_ok=True)
    print("ANALYSE_DONE", json.dumps(out["orientation"]), json.dumps(out["summary"]))


main()
