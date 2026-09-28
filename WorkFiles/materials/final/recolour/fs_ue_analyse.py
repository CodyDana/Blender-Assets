"""Analyse the FINAL Unreal recolour captures (fs_ue_capture.py) against the v2 float64 twin (np_twin.py).

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python WorkFiles/materials/final/recolour/fs_ue_analyse.py -- [--keep-exr]

Orientation: the dihedral transform the build's capture analysis measured (ue_renders/uv_capture_analysis.json).
Fabric: the twin is driven by the detail value recovered from Unreal's OWN default capture (default = Colour x n
exactly, every v2 guard inactive), so the engine Plane's sub-texel UV drift cancels and each stress capture compares per
pixel with the twin. Paper: the twin on the maps at texel centres (edge pixels carry the plane's sub-texel bleed).
Distance: the 1/16-resolution capture (GPU mip 4, material mip level 4) vs the 16x16 box of the mip-0 capture.
Writes ue/fs_ue_results.json and swatch_UE_<part>.png (one sheet per recolourable part; the paper bomb's three
colours get one sheet each); deletes the EXRs unless --keep-exr.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

PROJECT = Path("C:/Users/Cody/Desktop/Blender_Projects")
HERE = PROJECT / "WorkFiles/materials/final/recolour"
UE = HERE / "ue"
sys.path.insert(0, str(PROJECT / "Scripts/unreal/materials/maps"))
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
_argv = sys.argv
sys.argv = [sys.argv[0]]
_src = (HERE / "fs_twin_stress.py").read_text(encoding="utf-8").rsplit("\nmain()", 1)[0]
T = {"__name__": "fs_twin_defs", "__file__": str(HERE / "fs_twin_stress.py")}
exec(compile(_src, "fs_twin_stress.py", "exec"), T)  # noqa: S102
sys.argv = _argv
tw, rc = T["tw"], T["rc"]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KEEP = "--keep-exr" in ARGS
DUMP_PATH = PROJECT / "WorkFiles/materials/build/dump_f2.json"
DUMP = json.loads(DUMP_PATH.read_text(encoding="utf-8"))["instances"]
K = json.loads((PROJECT / "WorkFiles/materials/ue_renders/uv_capture_analysis.json").read_text())["orientation"]["dihedral_k"]
LUM = tw.LUM
q8, box, de, hex_lin, lin_hex = T["q8"], T["box"], T["de"], T["hex_lin"], T["lin_hex"]
WARN, FG = T["WARN"], T["FG"]


def params(inst):
    d = DUMP[inst]
    return {**d["scalar"], **d["vector"], **d["static_switch"]}


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
    lev = q8(lin)
    return tw.s2l(lev / 255.0), lev


def diffstats(a, b, mask=None):
    d = np.abs(a.astype(np.int32) - b.astype(np.int32)).max(-1)
    if mask is not None:
        d = d[mask]
    return {"max": int(d.max()), "p99_9": float(np.percentile(d, 99.9)), "mean": round(float(d.mean()), 4),
            "gt1": int((d > 1).sum()), "n": int(d.size)}


def fabric(part, jobs, out):
    inst, det_png, _ = T["FABRIC"][part]
    p = params(inst)
    col_def = np.asarray(p["Colour"][:3])
    d16, _, _ = rc.png_read(PROJECT / det_png)
    vals, cnts = np.unique(d16, return_counts=True)
    cov = d16 != vals[np.argmax(cnts)]
    n_map = np.maximum(p["Detail Bias"] + p["Detail Scale"] * d16 / 65535.0, 1e-6)
    dlin, dlev = cap(jobs[f"{part}__default"], "mip0")
    g_def, ce_def, _ = tw.fabric_scalar(p, d16 / 65535.0, col_def)
    orient = diffstats(dlev, q8(ce_def * g_def[..., None]), cov)
    n_cap = (dlin @ LUM) / float(col_def @ LUM)
    d_cap = (n_cap - p["Detail Bias"]) / p["Detail Scale"]
    hi = n_map > 1.0
    base_ll = T["logl"](dlev[cov].reshape(-1, 3))
    res = {"default_vs_twin_at_texel_centres_levels": orient, "colours": {}}
    rows = []
    S = dlev.shape[0]
    cy, cx = T["pick_crop"](np.kron(box(n_map * n_map, 8) - box(n_map, 8) ** 2, np.ones((8, 8))), 160, max(32, S // 64))
    order = [f"{part}__default"] + [f"{part}__{h}" for h in ("FFFFFF", "F2E8D5", "FF0000", "0000FF", "808080", "000000",
                                                              "E7E7E7", "B01010", "1A1A1A")]
    for name in order:
        job = jobs.get(name)
        if not job or "error" in job:
            res["colours"][name] = {"error": (job or {}).get("error", "missing")}
            continue
        hx = job["hex"]
        colour = col_def if hx is None else hex_lin(hx)
        lin, lev = cap(job, "mip0")
        g, ce, info = tw.fabric_scalar(p, d_cap, colour)
        pred = q8(ce * g[..., None])
        dom = int(np.argmax(ce))
        lv = lev[..., dom]
        pl, used = T["plateau"](lv[cov])
        plh, _ = T["plateau"](lv[cov & hi])
        gap, _ = T["gaps"](lv[cov])
        ll = T["logl"](lev[cov].reshape(-1, 3))
        mean = lin[cov].mean(0)
        m4lin, m4lev = cap(job, "mip4")
        truth = box(lin, 16)
        c16 = box(cov.astype(np.float64), 16) >= 0.5
        gm, tm = m4lin[c16].mean(0), truth[c16].mean(0)
        sub = slice(None, None, 7)
        r = {"hex": hx or lin_hex(col_def), "readback": job.get("readback"), "ps_instructions": job.get("ps_instructions"),
             "effective_hex": lin_hex(ce), "mean_hex": lin_hex(mean),
             "vs_twin_levels": diffstats(lev, pred, cov),
             "plateau_frac": round(pl, 4), "plateau_frac_highlights": round(plh, 4), "levels_used": used,
             "max_gap": gap, "mean_albedo": rc.rnd(mean, 5),
             "dE00_mean_vs_picked": round(float(de(mean, colour)), 3),
             "logL_std_ratio": round(float(ll.std() / base_ll.std()), 4) if ll.std() > 0 else 0.0,
             "spearman_vs_default": round(float(np.corrcoef(T["rank"](ll[sub]), T["rank"](base_ll[sub]))[0, 1]), 4)
             if ll.std() > 0 else None,
             "mip4_dE00_mean": round(float(de(gm, tm)), 3),
             "mip4_luminance_ratio": round(float((gm @ LUM) / max(tm @ LUM, 1e-9)), 4),
             "C_hi": round(info["C_hi"], 4)}
        near_black = float(ce.max()) <= 0.0105      # 8-bit GBuffer: ~50-100 levels for the whole part (reported)
        gates = {"vs_twin_p999_le_2": r["vs_twin_levels"]["p99_9"] <= 2,
                 "plateau_highlights_le_0.20": plh <= 0.20 or near_black, "plateau_le_0.15": pl <= 0.15 or near_black,
                 "gap_le_2": gap <= 2,
                 "mip4_lum_within_3pct": abs(r["mip4_luminance_ratio"] - 1) <= 0.03, "mip4_dE00_le_1": r["mip4_dE00_mean"] <= 1.0}
        if hx is not None:
            gates["detail_ge_0.25"] = r["logL_std_ratio"] >= 0.25
        r["gates"], r["pass"] = gates, all(gates.values())
        res["colours"][hx or "default"] = r
        f = max(1, S // 512)
        rows.append({"label_lines": [f"UNREAL {'DEFAULT' if hx is None else 'PICK #' + hx}",
                                     f"EFFECTIVE #{r['effective_hex']}  MEAN #{r['mean_hex']}",
                                     (f"PLATEAU {100 * pl:.1f}%  HI {100 * plh:.1f}%", WARN if plh > 0.2 else FG),
                                     f"LEVELS {used}  GAP {gap}",
                                     f"DETAIL {100 * r['logL_std_ratio']:.0f}%  SPEARMAN {r['spearman_vs_default']}",
                                     f"VS TWIN MAX {r['vs_twin_levels']['max']} P99.9 {r['vs_twin_levels']['p99_9']:.0f}",
                                     (f"MIP4 L X{r['mip4_luminance_ratio']:.3f} DE00 {r['mip4_dE00_mean']:.2f}",
                                      WARN if not gates["mip4_lum_within_3pct"] else FG),
                                     (f"GATES {'PASS' if r['pass'] else 'FAIL'}", FG if r["pass"] else WARN)],
                     "panels": [(q8(box(lin, f)) if f > 1 else lev, 512), (lev[cy:cy + 160, cx:cx + 160], 480),
                                (m4lev, 256), (q8(truth), 256)],
                     "hist": T["histogram"](lv[cov], ce),
                     "hist_lines": ["UNREAL CAPTURE, DOMINANT CHANNEL", "COVERED TEXELS, LOG COUNT"]})
        print(f"[ue] {part} {hx}: pl {pl:.3f}/{plh:.3f} gap {gap} vs twin {r['vs_twin_levels']['p99_9']}/{r['vs_twin_levels']['max']} "
              f"mip4 L{r['mip4_luminance_ratio']} {'PASS' if r['pass'] else 'FAIL ' + str([k for k, v in gates.items() if not v])}",
              flush=True)
    res["pass"] = all(v.get("pass", False) for v in res["colours"].values())
    out[part] = res
    T["make_sheet"](HERE / f"swatch_UE_{part}.png", f"UNREAL 5.8.3 FINAL RECOLOUR: {part.upper()} (V2)",
                    "SCS_BASE_COLOR OF TEMPORARY CHILD MICS OF THE SHIPPED MI (DELETED). MIP 4 = CAPTURE AT 1/16 RES.",
                    rows, ["WHOLE CAPTURE (BOX TO 512)", "1:1 CROP X3", "MIP 4: GPU AT 1/16 RES (V2)", "MIP 4 TRUE: BOX16 OF MIP 0"])


def paper(jobs, out):
    P = T["PAPER"]
    p = params(P["inst"])
    pd8, _, _ = rc.png_read(PROJECT / P["pd"])
    iw8, _, _ = rc.png_read(PROJECT / P["iw"])
    ao8 = rc.load_levels8(PROJECT / P["orm"])[..., 0:1].astype(np.float64)
    maps = T["paper_maps"](pd8, iw8, ao8, 0)
    iw = maps["iw"]
    paper_reg = (iw.sum(-1) < 0.004) & (maps["pd_a"][..., 0] < 0.004)
    pool = maps["pd_a"][..., 0] >= 0.5
    default = {k: np.asarray(p[k][:3]) for k in ("Paper Colour", "Black Ink Colour", "Red Ink Colour")}
    res = {"colours": {}}
    sheets = {"Paper Colour": [], "Black Ink Colour": [], "Red Ink Colour": []}
    names = ["PaperBomb__default"] + sorted(n for n in jobs if n.startswith("PaperBomb_") and n != "PaperBomb__default")
    for name in names:
        job = jobs[name]
        if "error" in job:
            res["colours"][name] = {"error": job["error"]}
            continue
        cols = dict(default)
        if job["param"]:
            cols[job["param"]] = hex_lin(job["hex"])
        pred_lin, unclipped, der = tw.paper_albedo(p, maps, cols["Paper Colour"], cols["Black Ink Colour"],
                                                   cols["Red Ink Colour"], ao_in_colour=float(p["Baked AO In Colour"]))
        lin, lev = cap(job, "mip0")
        pred = q8(pred_lin)
        picked = cols[job["param"]] if job["param"] else cols["Paper Colour"]
        dom = int(np.argmax(picked)) if picked.max() > 0 else 1
        pl, used = T["plateau"](lev[paper_reg][:, dom])
        clip = (unclipped >= p["Albedo Ceiling"]).any(-1)
        m4lin, m4lev = cap(job, "mip4")
        truth = box(lin, 16)
        gm, tm = m4lin.reshape(-1, 3).mean(0), truth.reshape(-1, 3).mean(0)
        pool_mean = lin[pool].mean(0)
        r = {"param": job["param"], "hex": job["hex"], "readback": job.get("readback"),
             "vs_twin_levels_all": diffstats(lev, pred), "vs_twin_levels_paper": diffstats(lev, pred, paper_reg),
             "paper_region_plateau": round(pl, 4), "paper_region_levels": used,
             "paper_region_mean_hex": lin_hex(lin[paper_reg].mean(0)),
             "twin_clip_frac_paper": round(float(clip[paper_reg].mean()), 5),
             "red_pool_mean_ue": lin_hex(pool_mean), "red_pool_chroma_ue": round(T["chroma"](pool_mean), 2),
             "derived_hex": {k: lin_hex(v) for k, v in der.items()},
             "mip4_dE00_mean": round(float(de(gm, tm)), 3)}
        r["red_pool_derived_chroma"] = round(T["chroma"](der["RedPool"]), 2)
        # paper: the twin samples texel centres (no UV-probe correction), so edge texels carry the plane's sub-texel
        # bleed; the build's probe-corrected analysis (ue_renders/uv_capture_analysis.json) holds p99.9 <= 2
        gates = {"vs_twin_paper_p999_le_3": r["vs_twin_levels_paper"]["p99_9"] <= 3, "mip4_dE00_le_1": r["mip4_dE00_mean"] <= 1.0}
        if job["param"] == "Paper Colour" and job["hex"] not in ("1A1A1A", "000000"):
            gates["paper_plateau_le_0.20"] = pl <= 0.20
            gates["paper_at_ceiling_le_1pct"] = r["twin_clip_frac_paper"] <= 0.01
        if job["param"] == "Red Ink Colour" and job["hex"] in ("FFFFFF", "808080", "000000"):
            gates["neutral_red_pools_neutral_Cab_le_3"] = r["red_pool_derived_chroma"] <= 3.0
        r["gates"], r["pass"] = gates, all(gates.values())
        res["colours"][name] = r
        cy, cx = 1504, 1408
        row = {"label_lines": [name.replace("PaperBomb_", "").replace("__", " #").upper(),
                               (f"PAPER PLATEAU {100 * pl:.1f}%  LEVELS {used}", WARN if pl > 0.2 else FG),
                               f"PAPER MEAN #{r['paper_region_mean_hex']}",
                               f"VS TWIN (PAPER) P99.9 {r['vs_twin_levels_paper']['p99_9']:.0f} MAX {r['vs_twin_levels_paper']['max']}",
                               f"POOL #{r['red_pool_mean_ue']} C {r['red_pool_chroma_ue']:.1f}",
                               f"MIP4 DE00 {r['mip4_dE00_mean']:.2f}",
                               (f"GATES {'PASS' if r['pass'] else 'FAIL'}", FG if r["pass"] else WARN)],
               "panels": [(q8(box(lin, 4)), 512), (lev[cy:cy + 160, cx:cx + 160], 480), (m4lev, 256), (q8(truth), 256)],
               "hist": T["histogram"](lev[paper_reg][:, dom], picked if picked.max() > 0 else np.array([.5, .5, .5])),
               "hist_lines": ["UNREAL, PAPER TEXELS"]}
        for k in sheets:
            if job["param"] in (None, k):
                sheets[k].append(row)
        print(f"[ue] {name}: pl {pl:.3f} vs twin {r['vs_twin_levels_paper']['p99_9']} pool #{r['red_pool_mean_ue']} "
              f"C{r['red_pool_chroma_ue']} {'PASS' if r['pass'] else 'FAIL ' + str([k for k, v in gates.items() if not v])}", flush=True)
    res["pass"] = all(v.get("pass", False) for v in res["colours"].values())
    out["PaperBomb"] = res
    for k, rows in sheets.items():
        key = k.replace(" Colour", "").replace(" ", "")
        T["make_sheet"](HERE / f"swatch_UE_PaperBomb_{key}.png", f"UNREAL 5.8.3 FINAL RECOLOUR: PAPER BOMB {k.upper()} (V2)",
                        "SCS_BASE_COLOR OF TEMPORARY CHILD MICS OF MI_PAPERBOMB_TAG (AO IN COLOUR ON, AS SHIPPED).",
                        rows, ["WHOLE CAPTURE (BOX TO 512)", "1:1 CROP X3", "MIP 4: GPU AT 1/16 RES", "MIP 4 TRUE"])


def main():
    rep = json.loads((UE / "fs_ue_capture.json").read_text(encoding="utf-8"))
    jobs = rep["jobs"]
    out = {"capture_run": {k: rep[k] for k in rep if k != "jobs"}, "dihedral_k": K, "dump": str(DUMP_PATH),
           "errors": {k: v["error"] for k, v in jobs.items() if "error" in v}}
    for part in T["FABRIC"]:
        fabric(part, jobs, out)
    paper(jobs, out)
    out["pass"] = all(out[k]["pass"] for k in list(T["FABRIC"]) + ["PaperBomb"]) and not out["errors"]
    rc.write_json(UE / "fs_ue_results.json", out)
    if not KEEP:
        for j in jobs.values():
            for k in ("exr_mip0", "exr_mip4"):
                if j.get(k):
                    Path(j[k]).unlink(missing_ok=True)
    print("FS_UE_ANALYSE_DONE pass=", out["pass"], flush=True)


main()
