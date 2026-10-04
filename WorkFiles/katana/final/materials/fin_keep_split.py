"""Katana finaliser: Metal-From-ORM-aware analysis of the katana_1003 UV-plane base-colour captures (read-only on the
captures; writes only WorkFiles/katana/final/materials/uv_capture_keep_split_katana.json).

    blender -b --factory-startup --python fin_keep_split.py

The pack's analyse_captures.py has no Metal From ORM branch (the flashbang precedent). This reuses the katana copy of
it (fin_analyse_captures_copy.py: twin + keep lerp, UV-probe geometry) and splits every MI_Katana_Grip capture by the
master's keep weight k = max(ORM.B, sat((lum(BC) - 0.2) x 5)) sampled at each pixel:
  tinted  k < 0.02   the recolourable cord: the gate is capture vs twin (default p99.9 <= 1, mean <= 0.3; stress
                     p99.9 <= 2), and v3 (clip, banding, std ratio, Spearman vs the default) on these texels only
  kept    k > 0.98   the ray skin keeps its baked colour: Unreal samples the BC1 (DXT1) compressed BC, the twin the PNG,
                     so capture vs twin here is block-compression error (reported); the gate is that every stress
                     capture equals the DEFAULT capture on these texels (the colour really is kept)
  ramp    otherwise  reported only
The saya lacquer (Metal From ORM off) is re-reported from the same run for completeness.
"""
import json
import sys
from pathlib import Path

import numpy as np

SRC = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/katana/final/materials/fin_analyse_captures_copy.py")
code = SRC.read_text(encoding="utf-8").rsplit("\nmain()", 1)[0]
ns = {"__name__": "fin_copy", "__doc__": None}
exec(compile(code, str(SRC), "exec"), ns)  # noqa: S102 - our own file, minus its main() call
rc, tw = ns["rc"], ns["tw"]
OUT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/katana/final/materials/uv_capture_keep_split_katana.json")


def stats(a, b, m):
    d = np.abs(np.asarray(a, np.int32) - np.asarray(b, np.int32)).max(axis=-1)[m]
    if d.size == 0:
        return None
    return {"texels": int(d.size), "max": int(d.max()), "mean": round(float(d.mean()), 4),
            "p99": float(np.percentile(d, 99)), "p99_9": float(np.percentile(d, 99.9)), "gt2": int((d > 2).sum())}


def main():
    jobs_doc = json.loads((ns["CAPS"] / "capture_jobs.json").read_text(encoding="utf-8"))
    jobs = {j["name"]: j for j in jobs_doc["jobs"]}
    results = jobs_doc["results"]
    probes_at = {v["at_job"]: p for p, v in jobs_doc["probes"].items()}
    prev = json.loads(OUT.with_name("uv_capture_analysis_katana_only.json").read_text(encoding="utf-8"))
    k = prev["orientation"]["dihedral_k"]
    out = {"method": __doc__.strip(), "captures": {}}
    for slot in ("MI_Katana_Grip", "MI_Katana_Saya_Lacquer"):
        var = eval(prev["captures"][f"uv_{slot}_default"]["mapping"]["variant"])  # noqa: S307
        names = [n for n in jobs if jobs[n].get("slot") == slot and not n.startswith("uvprobe")]
        names.sort(key=lambda n: 0 if n.endswith("_default") else 1)
        inp = ns["fabric_inputs"](jobs[names[0]])
        default_lev = None
        for name in names:
            job = jobs[name]
            lin = ns["dihedral"](ns["load_exr"](results[name]["exr"]), k)
            lev = rc.q8_srgb(lin)
            probe = ns["dihedral"](ns["load_exr"](results[probes_at[name]]["exr"]), k)
            yy, xx = ns["probe_coords"](probe, var)
            rinp = ns["resample_inputs"](inp, yy, xx)
            colour = job["overrides"].get("Colour", job["params"]["Colour"])[:3]
            exp, _ = ns["fabric_model"](job, rinp, colour)
            exp_lev = rc.q8_srgb(exp)
            keep = rinp.get("keep")
            if keep is None:
                keep = np.zeros(lev.shape[:2])
            m_t, m_k = keep < 0.02, keep > 0.98
            m_r = ~(m_t | m_k)
            rec = {"colour": colour, "fractions": {"tinted": round(float(m_t.mean()), 4), "kept": round(float(m_k.mean()), 4),
                                                   "ramp": round(float(m_r.mean()), 4)},
                   "tinted_vs_twin": stats(lev, exp_lev, m_t), "kept_vs_twin": stats(lev, exp_lev, m_k),
                   "ramp_vs_twin": stats(lev, exp_lev, m_r)}
            st = rec["tinted_vs_twin"]
            if name.endswith("_default"):
                default_lev, default_lin = lev, lin
                rec["gate_tinted_vs_twin"] = bool(st["p99_9"] <= 1 and st["mean"] <= 0.3)
            else:
                rec["gate_tinted_vs_twin"] = bool(st["p99_9"] <= 2)
                if m_k.any():
                    rec["kept_vs_default_capture"] = stats(lev, default_lev, m_k)
                    rec["gate_kept_equals_default"] = bool(rec["kept_vs_default_capture"]["max"] <= 1)
                # v3 on the tinted texels only (the recolourable part)
                cl, dl = lin[m_t], default_lin[m_t]
                s8 = rc.q8_srgb(cl)
                dom = int(np.argmax(colour))
                ly = np.log(np.maximum(cl @ rc.LUM, 1e-7))
                ly0 = np.log(np.maximum(dl @ rc.LUM, 1e-7))
                v = {"clip_frac": round(float((cl >= 0.949).any(axis=1).mean()), 6), **rc.banding(s8, dom),
                     "std_ratio_logL": round(float(ly.std() / ly0.std()), 4),
                     "spearman_vs_default_capture": round(ns["spearman"](ly, ly0), 5),
                     # the default (near-black ito) capture holds only a few 8-bit levels, so its ranks are mostly ties;
                     # the recolour's own input is the Detail16 map: rank agreement with it is the detail-preservation figure
                     "spearman_vs_detail_map": round(ns["spearman"](ly, rinp["d"][m_t].reshape(-1)), 5),
                     "default_capture_levels_used": int(len(np.unique(rc.q8_srgb(dl).reshape(-1, 3), axis=0))),
                     "mean_albedo": rc.rnd(cl.mean(axis=0), 5)}
                rec["v3_tinted"] = v
                rec["gate_v3_tinted"] = bool(v["clip_frac"] <= 0.001 and v["pass"] and v["std_ratio_logL"] >= 0.25
                                             and max(v["spearman_vs_default_capture"], v["spearman_vs_detail_map"]) >= 0.98)
            out["captures"][name] = rec
            print("[split]", name, json.dumps({kk: rec.get(kk) for kk in ("fractions", "tinted_vs_twin", "gate_tinted_vs_twin",
                                                                      "gate_kept_equals_default", "gate_v3_tinted")}), flush=True)
    OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("SPLIT_DONE", OUT)


main()
