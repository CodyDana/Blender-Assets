"""Analyse the Unreal recolour stress captures (rst_ue_capture.py) against the float64 replica (rst_twin_stress.py).

    blender -b --factory-startup --python WorkFiles/materials/recolour_tests/rst_ue_analyse.py -- [--keep-exr]

Orientation: the capture is turned into texture orientation with the dihedral transform the build's own capture
analysis measured (ue_renders/uv_capture_analysis.json, orientation.dihedral_k), and checked here again per part.
Fabric: the replica is driven by n recovered from Unreal's OWN default capture (default = Colour x n exactly), so the
engine Plane's sub-texel UV drift cancels and each stress capture can be compared per pixel with the replica.
Paper: the replica on the maps (texel centres); edge pixels carry the plane's sub-texel bleed.
Writes ue/rst_ue_results.json and swatch_UE_<part>.png; deletes the EXRs unless --keep-exr.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

PROJECT = Path("C:/Users/Cody/Desktop/Blender_Projects")
HERE = PROJECT / "WorkFiles/materials/recolour_tests"
UE = HERE / "ue"
sys.path.insert(0, str(PROJECT / "Scripts/unreal/materials/maps"))
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import recolour_common as rc  # noqa: E402

# the replica functions (importing the module would run its main): exec the definitions only
_src = (HERE / "rst_twin_stress.py").read_text(encoding="utf-8").rsplit("\nmain()", 1)[0]
T = {"__name__": "rst_twin_defs", "__file__": str(HERE / "rst_twin_stress.py")}
sys.argv = [a for a in sys.argv if a != "--only"]
exec(compile(_src, "rst_twin_stress.py", "exec"), T)  # noqa: S102

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KEEP = "--keep-exr" in ARGS
K = json.loads((PROJECT / "WorkFiles/materials/ue_renders/uv_capture_analysis.json").read_text())["orientation"]["dihedral_k"]
LUM = T["LUM"]
q8, box, de, hex_lin, lin_hex = T["q8"], T["box"], T["de"], T["hex_lin"], T["lin_hex"]


def load_exr(path):
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


def cap(job, which):
    lin = dihedral(load_exr(job[f"exr_{which}"]), K)
    return rc.s2l(q8(lin) / 255.0), q8(lin)          # the GBuffer's stored levels, decoded


def diffstats(a, b, mask=None):
    d = np.abs(a.astype(np.int32) - b.astype(np.int32)).max(-1)
    if mask is not None:
        d = d[mask]
    return {"max": int(d.max()), "p99_9": float(np.percentile(d, 99.9)), "mean": round(float(d.mean()), 4),
            "gt1": int((d > 1).sum()), "n": int(d.size)}


def fabric(part, jobs, out, sheets):
    inst, det_png, _ = T["FABRIC"][part]
    p = {**T["DUMP"][inst]["scalar"], **T["DUMP"][inst]["vector"]}
    col_def = np.asarray(p["Colour"][:3])
    d16, _, _ = rc.png_read(PROJECT / det_png)
    vals, cnts = np.unique(d16, return_counts=True)
    cov = d16 != vals[np.argmax(cnts)]
    n_map = np.maximum(p["Detail Bias"] + p["Detail Scale"] * d16 / 65535.0, 1e-6)
    dlin, dlev = cap(jobs[f"{part}__default"], "mip0")
    # orientation check: default capture vs the replica default at texel centres
    g_def, _, _ = T["fabric_scalar"](d16 / 65535.0, p, col_def)
    orient = diffstats(dlev, q8(col_def * g_def[..., None]), cov)
    n_cap = (dlin @ LUM) / float(col_def @ LUM)       # n as Unreal sampled it (default = Colour x n)
    # invert the default mapping to d: n = bias + scale d
    d_cap = (n_cap - p["Detail Bias"]) / p["Detail Scale"]
    hi = n_map > 1.0
    res = {"orientation_check_default_vs_replica_levels": orient, "colours": {}}
    rows = []
    for name, job in sorted(jobs.items()):
        if not name.startswith(part + "__") or "error" in job:
            continue
        hx = job["hex"]
        colour = col_def if hx is None else hex_lin(hx)
        lin, lev = cap(job, "mip0")
        g, _, info = T["fabric_scalar"](d_cap, p, colour)
        pred = q8(colour * g[..., None])
        dom = int(np.argmax(colour)) if colour.max() > 0 else 1
        lv = lev[..., dom]
        pl, used = T["plateau"](lv[cov])
        plh, _ = T["plateau"](lv[cov & hi])
        gap, _ = T["gaps"](lv[cov])
        mean = lin[cov].mean(0)
        # the distant view: GPU mip-4 capture vs box16 of the mip-0 capture (both GBuffer values, decoded)
        m4lin, m4lev = cap(job, "mip4")
        truth = box(lin, 16)
        c16 = box(cov.astype(np.float64), 16) >= 0.5
        gm, tm = m4lin[c16].mean(0), truth[c16].mean(0)
        r = {"hex": hx or lin_hex(col_def), "readback": job.get("readback"),
             "vs_replica_levels": diffstats(lev, pred, cov),
             "plateau_frac": round(pl, 4), "plateau_frac_highlights": round(plh, 4), "levels_used": used,
             "max_gap": gap, "mean_albedo": rc.rnd(mean, 5),
             "dE00_mean_vs_picked": round(float(de(mean, colour)), 3) if hx else None,
             "mip4_dE00_mean": round(float(de(gm, tm)), 3),
             "mip4_luminance_ratio": round(float((gm @ LUM) / max(tm @ LUM, 1e-9)), 4),
             "C_hi": round(info["C_hi"], 4)}
        res["colours"][hx or "default"] = r
        S = lev.shape[0]
        cy, cx = T["pick_crop"](np.kron(box(n_map * n_map, 8) - box(n_map, 8) ** 2, np.ones((8, 8))), 160, max(32, S // 64))
        f = max(1, S // 512)
        rows.append({"label_lines": [f"UNREAL {'DEFAULT' if hx is None else '#' + hx}",
                                     f"PLATEAU {100 * pl:.1f}%  HI {100 * plh:.1f}%",
                                     f"LEVELS {used}  GAP {gap}",
                                     f"VS REPLICA MAX {r['vs_replica_levels']['max']} P99.9 {r['vs_replica_levels']['p99_9']:.0f}",
                                     f"MIP4 L X{r['mip4_luminance_ratio']:.3f} DE00 {r['mip4_dE00_mean']:.2f}"],
                     "panels": [(q8(box(lin, f)) if f > 1 else lev, 512), (lev[cy:cy + 160, cx:cx + 160], 480),
                                (m4lev, 256), (q8(truth), 256)],
                     "hist": T["histogram"](lv[cov], colour if colour.max() > 0 else np.array([.5, .5, .5])),
                     "hist_lines": ["UNREAL CAPTURE, DOMINANT CHANNEL"]})
        print(f"[ue] {part} {hx}: pl {pl:.3f}/{plh:.3f} vsrep {r['vs_replica_levels']} mip4 L{r['mip4_luminance_ratio']}", flush=True)
    out[part] = res
    T["make_sheet"](HERE / f"swatch_UE_{part}.png", f"UNREAL 5.8.3 CAPTURES: {part.upper()}",
                    "SCS_BASE_COLOR OF TEMPORARY MICS (SCRATCH PATH, DELETED). MIP 4 = CAPTURE AT 1/16 RES (GPU MIP SELECTION).",
                    rows, ["WHOLE CAPTURE (BOX TO 512)", "1:1 CROP X3", "MIP 4: GPU AT 1/16 RES", "MIP 4 TRUE: BOX16 OF MIP 0"])


def paper(jobs, out):
    P = T["PAPER"]
    p = {**T["DUMP"][P["inst"]]["scalar"], **T["DUMP"][P["inst"]]["vector"]}
    pd8, _, _ = rc.png_read(PROJECT / P["pd"])
    iw8, _, _ = rc.png_read(PROJECT / P["iw"])
    ao8 = rc.load_levels8(PROJECT / P["orm"])[..., 0:1].astype(np.float64)
    maps = T["paper_mips"](pd8, iw8, ao8, 0)
    iw = maps["iw"]
    paper_reg = (iw.sum(-1) < 0.004) & (maps["pd_a"][..., 0] < 0.004)
    default = {k: np.asarray(p[k][:3]) for k in ("Paper Colour", "Black Ink Colour", "Red Ink Colour")}
    res = {"colours": {}}
    rows = []
    for name, job in sorted(jobs.items()):
        if not name.startswith("PaperBomb") or "error" in job:
            continue
        cols = dict(default)
        if job["param"]:
            cols[job["param"]] = hex_lin(job["hex"])
        pred_lin, unclipped, der = T["paper_base"](maps, p, cols["Paper Colour"], cols["Black Ink Colour"],
                                                   cols["Red Ink Colour"], float(p["Baked AO In Colour"]))
        lin, lev = cap(job, "mip0")
        pred = q8(pred_lin)
        picked = cols[job["param"]] if job["param"] else cols["Paper Colour"]
        dom = int(np.argmax(picked)) if picked.max() > 0 else 1
        pl, used = T["plateau"](lev[paper_reg][:, dom])
        clip = (unclipped >= p["Albedo Ceiling"]).any(-1)
        m4lin, m4lev = cap(job, "mip4")
        truth = box(lin, 16)
        gm, tm = m4lin.reshape(-1, 3).mean(0), truth.reshape(-1, 3).mean(0)
        r = {"param": job["param"], "hex": job["hex"], "readback": job.get("readback"),
             "vs_replica_levels_all": diffstats(lev, pred), "vs_replica_levels_paper": diffstats(lev, pred, paper_reg),
             "paper_region_plateau": round(pl, 4), "paper_region_levels": used,
             "replica_clip_frac_paper": round(float(clip[paper_reg].mean()), 4),
             "mip4_dE00_mean": round(float(de(gm, tm)), 3)}
        pool = maps["pd_a"][..., 0] >= 0.5
        if pool.any():
            r["red_pool_mean_ue"] = lin_hex(lin[pool].mean(0))
        res["colours"][name] = r
        cy, cx = 1504, 1408
        rows.append({"label_lines": [name.replace("PaperBomb_", "").replace("__", " #").upper(),
                                     f"PAPER PLATEAU {100 * pl:.1f}%  LEVELS {used}",
                                     f"VS REPLICA P99.9 {r['vs_replica_levels_all']['p99_9']:.0f} MAX {r['vs_replica_levels_all']['max']}",
                                     f"POOL {r.get('red_pool_mean_ue', '-')}",
                                     f"MIP4 DE00 {r['mip4_dE00_mean']:.2f}"],
                     "panels": [(q8(box(lin, 4)), 512), (lev[cy:cy + 160, cx:cx + 160], 480), (m4lev, 256), (q8(truth), 256)],
                     "hist": T["histogram"](lev[paper_reg][:, dom], picked if picked.max() > 0 else np.array([.5, .5, .5])),
                     "hist_lines": ["UNREAL, PAPER TEXELS"]})
        print(f"[ue] {name}: pl {pl:.3f} vsrep {r['vs_replica_levels_all']} pool {r.get('red_pool_mean_ue')}", flush=True)
    out["PaperBomb"] = res
    T["make_sheet"](HERE / "swatch_UE_PaperBomb.png", "UNREAL 5.8.3 CAPTURES: PAPERBOMB",
                    "SCS_BASE_COLOR OF TEMPORARY MICS (AO IN COLOUR ON, AS SHIPPED).",
                    rows, ["WHOLE CAPTURE (BOX TO 512)", "1:1 CROP X3 (PAPER GRAIN)", "MIP 4: GPU AT 1/16 RES", "MIP 4 TRUE"])


def main():
    rep = json.loads((UE / "rst_ue_capture.json").read_text(encoding="utf-8"))
    jobs = rep["jobs"]
    out = {"capture_run": {k: rep[k] for k in rep if k != "jobs"}, "dihedral_k": K,
           "errors": {k: v["error"] for k, v in jobs.items() if "error" in v}}
    for part in T["FABRIC"]:
        fabric(part, jobs, out, None)
    paper(jobs, out)
    rc.write_json(UE / "rst_ue_results.json", out)
    if not KEEP:
        for j in jobs.values():
            for k in ("exr_mip0", "exr_mip4"):
                if j.get(k):
                    Path(j[k]).unlink(missing_ok=True)
    print("RST_UE_ANALYSE_DONE", flush=True)


main()
