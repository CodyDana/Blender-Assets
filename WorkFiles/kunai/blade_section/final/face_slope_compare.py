"""face_slope at the photo's stations: photo (reconciled) vs 3.10.1 (options/current, the shipped section rebuilt by the
prototype tree, identical figures) vs prototype C (options/C) vs the BUILT 3.11 LOD0 (final/mesh_measure.json).
Plain Python.  Writes final/face_slope_vs_photo.json."""
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
BS = HERE.parent
rec = json.loads((BS / "ours" / "photo_reconciled.json").read_text(encoding="utf-8"))
old = json.loads((BS / "options" / "current" / "mesh_measure.json").read_text(encoding="utf-8"))["stations"]
proto = json.loads((BS / "options" / "C" / "mesh_measure.json").read_text(encoding="utf-8"))
new = json.loads((HERE / "mesh_measure.json").read_text(encoding="utf-8"))
rows = []
for st in rec["stations"]:
    key = f"{st['ours_x_mm']:g}"
    rows.append({"frac_from_shoulder": st["frac_from_shoulder"], "section": st["section"], "x_mm": st["ours_x_mm"],
                 "photo": st["face_slope"], "photo_p10_p90": st["face_slope_p10_p90"],
                 "v3_10_1": old[key]["face_slope_mesh"], "prototype_c": proto["stations"][key]["face_slope_mesh"],
                 "v3_11": new["stations"][key]["face_slope_mesh"],
                 "v3_11_face_angle_deg": new["stations"][key]["face_angle_deg"],
                 "v3_11_ridge_thickness_mm": new["stations"][key]["ridge_thickness_mm"],
                 "v3_11_over_photo": round(new["stations"][key]["face_slope_mesh"] / st["face_slope"], 3),
                 "v3_11_minus_prototype_c": round(new["stations"][key]["face_slope_mesh"]
                                                  - proto["stations"][key]["face_slope_mesh"], 5)})
front = [r for r in rows if r["section"] == "front"]
fm = {k: round(statistics.median(r[k] for r in front), 4) for k in ("photo", "v3_10_1", "prototype_c", "v3_11")}
out = {"method": ("face_slope = (ridge half-thickness - edge half-thickness) / half-width; ours fitted by least squares on "
                  "the top diamond face of a true LOD0 section (options/measure_mesh.py: bmesh bisect at the station); the "
                  "photo's reconciled figures from ours/photo_reconciled.json (the 0.90 station is its least reliable)"),
       "stations": rows,
       "front_median": fm,
       "front_median_over_photo": {k: round(fm[k] / fm["photo"], 3) for k in ("v3_10_1", "prototype_c", "v3_11")},
       "photo_front_range": rec["summary"]["front_range"],
       "face_angle_mid_blade_deg": {"photo": 10.5, "v3_11": new["stations"]["56.7"]["face_angle_deg"]},
       "lod_ridge_vs_lod0": {"v3_11": {k: {kk: v[kk] for kk in ("max_ridge_thickness_delta_mm", "at_x_mm")}
                                       for k, v in new["lod_ridge_vs_lod0"].items()},
                             "prototype_c": {k: {kk: v[kk] for kk in ("max_ridge_thickness_delta_mm", "at_x_mm")}
                                             for k, v in proto["lod_ridge_vs_lod0"].items()}},
       "texel_px_per_mm": {"v3_11": new["blade_texel_px_per_mm_area_weighted"],
                           "prototype_c": proto["blade_texel_px_per_mm_area_weighted"]}}
(HERE / "face_slope_vs_photo.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("FACESLOPE", json.dumps({"front_median": fm, "ratio": out["front_median_over_photo"],
                               "lod_ridge": out["lod_ridge_vs_lod0"]["v3_11"]}))
