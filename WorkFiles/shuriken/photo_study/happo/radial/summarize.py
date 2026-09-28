import os, json, math, numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))
res = json.load(open(os.path.join(OUT, "results.json")))
th, r = np.load(os.path.join(OUT, "r_theta.npy"))
span = res["span_px"]
tips = res["tips"]; nots = res["notches"]
tr = np.array([v["r_virtual"] for v in tips]); nr = np.array([v["r_virtual"] for v in nots])
ta = np.array([v["angle"] for v in tips]); na = np.array([v["angle"] for v in nots])
sub = np.array([v["angle"] for v in tips if v["name"] not in ("T_SSW", "T_SSE")])
fill = np.array([v["fill_px"] for v in nots])
bands = [b for b in res["bands"] if b["near_tip"] > 3]
S = dict(
  photo="Happo.JPG (1217x1224)",
  outline_rule="outermost sharp lum step to a plateau along the edge normal, made consistent per edge by 2 line-fit passes; lid shadow (soft ramp) excluded, ground bevels included",
  centre_px=res["centre_px"], span_px=span, span_note="between virtual sharp tips (line intersections); 4 diagonals 1213-1283 px, sd 18.7; the SSW point is cut off by the image edge",
  point_count=8,
  tip_radius_ratio=[float((tr/span).mean()), float((tr/span).std())],
  notch_radius_ratio=[float((nr/span).mean()), float((nr/span).std())],
  notch_over_tip_radius=[float(nr.mean()/tr.mean()), float((nr/tr.mean()).std())],
  tip_angle_deg_all=[float(ta.mean()), float(ta.std())],
  tip_angle_deg_6clean=[float(sub.mean()), float(sub.std())],
  notch_angle_deg=[float(na.mean()), float(na.std())],
  notch_minus_tip_deg=float(na.mean()-ta.mean()),
  notch_floor_rounding_ratio=[float((fill/span).mean()), float((fill/span).std())],
  notch_fillet_radius_ratio=float(np.mean([v["fillet_radius_px"] for v in nots])/span),
  centre_hole=False,
  bevel_band_ratio=dict(near_tip=[float(np.median([b["near_tip"] for b in bands])/span), float(np.min([b["near_tip"] for b in bands])/span), float(np.max([b["near_tip"] for b in bands])/span)],
                        mid=[float(np.median([b["mid"] for b in bands])/span)],
                        near_notch=[float(np.median([b["near_notch"] for b in bands])/span)],
                        extent_fraction=[float(np.median([b["frac_gt3px"] for b in bands]))]),
  star_polygon=dict(measured_inner_over_outer=float(nr.mean()/tr.mean()), star_8_2=0.7654, star_8_3=0.5412,
                    k_continuous=float((180-ta.mean())*8/360), k_continuous_6clean=float((180-sub.mean())*8/360)),
  widths=res["widths_by_radius_fraction"],
  per_tip=[dict(name=v["name"], theta=v["theta"], r_ratio=v["r_virtual"]/span, angle=v["angle"], blunt_ratio=v["blunt_px"]/span) for v in tips],
  per_notch=[dict(name=v["name"], theta=v["theta"], r_ratio=v["r_virtual"]/span, angle=v["angle"], fill_ratio=v["fill_px"]/span) for v in nots],
  per_edge=[dict(name=e["name"], rms_ratio=e["rms_px"]/span, sagitta_ratio=e["sagitta_px"]/span, dir_deg=e["dir_deg"]) for e in res["edges"]],
)
json.dump(S, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
print(json.dumps(S, indent=1)[:3000])
