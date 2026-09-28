import json, os, numpy as np
OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/happo/contour"
r = json.load(open(os.path.join(OUT, "b8_results.json")))
span = r["centre"]["span_px"]; print("span_px %.1f  R_tip %.1f  R_notch %.1f" % (span, r["centre"]["tip_circle_R_px"], r["centre"]["notch_circle_R_px"]))
T = {int(k): v for k, v in r["tips"].items()}; N = {int(k): v for k, v in r["notches"].items()}
clean_t = [1, 2, 4, 6, 7]; clean_n = [1, 3, 5, 6, 7]
def st(v): v = np.array(v, float); return "mean %.3f sd %.3f min %.3f max %.3f" % (v.mean(), v.std(ddof=1), v.min(), v.max())
print("tip angle all8 ", st([T[k]["included_angle_deg"] for k in range(8)]))
print("tip angle clean", st([T[k]["included_angle_deg"] for k in clean_t]), [round(T[k]["included_angle_deg"],2) for k in clean_t])
print("tip angle +T0  ", st([T[k]["included_angle_deg"] for k in clean_t + [0]]))
print("notch open all8", st([N[k]["opening_deg"] for k in range(8)]))
print("notch open clean", st([N[k]["opening_deg"] for k in clean_n]))
print("tip r ratio all8", st([T[k]["r_vertex_ratio"] for k in range(8)]))
print("tip r px       ", st([T[k]["r_vertex_px"] for k in range(8)]))
print("notch r ratio all8", st([N[k]["r_vertex_ratio"] for k in range(8)]), " excl N4", st([N[k]["r_vertex_ratio"] for k in range(8) if k != 4]))
print("notch bottom r ratio", st([N[k]["r_bottom_ratio"] for k in range(8)]))
pol = [T[k]["polar_deg"] for k in range(8)]
sp = [(pol[(k+1) % 8] - pol[k]) % 360 for k in range(8)]
print("tip polar", [round(p,2) for p in pol]); print("spacing", [round(s,3) for s in sp], st(sp))
print("axis skew", st([T[k]["axis_skew_deg"] for k in range(8)]), [round(T[k]["axis_skew_deg"],2) for k in range(8)])
print("tip end offset px", st([T[k]["end_offset_px"] for k in range(8) if T[k]["vertex_in_image"]]))
print("notch gap px", st([N[k]["bottom_gap_px"] for k in range(8)]), "ratio", st([N[k]["gap_ratio"] for k in range(8)]))
loc = [N[k]["local_circle_fits"]["10"]["radius_px"] for k in range(8)]
loc12 = [N[k]["local_circle_fits"]["12"]["radius_px"] for k in range(8)]
print("notch local radius D10", [round(v,1) for v in loc], st(loc), "ratio", st([v/span for v in loc]))
print("notch local radius D12", [round(v,1) for v in loc12], st(loc12), "ratio", st([v/span for v in loc12]))
print("excl N4: D10", st([loc[k] for k in range(8) if k != 4]), "ratio", st([loc[k]/span for k in range(8) if k != 4]))
E = r["edges"]
print("edge rms", st([e["rms_px"] for e in E.values()]), "max|res|", st([e["max_abs_res_px"] for e in E.values()]))
print("sagitta", st([abs(e["sagitta_px"]) for e in E.values()]), "as ratio", st([abs(e["sagitta_px"])/span for e in E.values()]))
print("fitted len ratio", st([e["fitted_len_px"]/span for e in E.values()]))
bv = {k: e["bevel"] for k, e in E.items() if e.get("bevel")}
print("edges with band %d/16:" % len(bv), sorted(bv))
for f in ("0.1", "0.2", "0.3", "0.5"):
    print("  band@%s px" % f, st([b["band_at_frac"][f] for b in bv.values()]), "ratio", st([b["band_at_frac"][f]/span for b in bv.values()]))
print("  taper deg", st([b["taper_deg"] for b in bv.values()]))
print("  run_out frac", st([b["run_out_frac_from_tip"] for b in bv.values()]), sorted(round(b["run_out_frac_from_tip"],2) for b in bv.values()))
print("  measured band median px", st([b["measured_band_px"]["median"] for b in bv.values()]), "detected to frac", st([b["measured_band_px"]["frac_max"] for b in bv.values()]))
print("star", r["star"])
print("psf", r["psf_sigma_px"]["median"], "blur sim", r["blur_sim"])
print("refined mask", {k: v for k, v in r["refined_mask"].items() if k != "polygon"})
print("holes", r["holes"])
print("edge circle radii ratio", st([E[k].get("circlefit_radius_px", 0)/span for k in E if E[k].get("circlefit_radius_px")]) if any(E[k].get("circlefit_radius_px") for k in E) else "n/a")
