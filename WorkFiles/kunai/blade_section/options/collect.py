"""Gather every option's figures into options_data.json (read by make_sheet.py and quoted in OPTIONS.md).
python collect.py  (Python 3.12)"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "calc"))
from section_post import post  # noqa: E402

IDS = ["current", "A", "B", "C"]
PHOTO = json.loads((HERE.parent / "ours" / "photo_reconciled.json").read_text())
PHOTO_ST = {f"{s['ours_x_mm']:g}": s for s in PHOTO["stations"]}
ANCHOR = {"hero": {"p50": 0.5599, "mean": 0.5503}, "top": {"p50": 0.4296, "mean": 0.4236}}
TOL = 0.05


def load(p):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


out = {"photo": {"stations": PHOTO["stations"], "summary": PHOTO["summary"]}, "anchor": ANCHOR, "tol": TOL, "options": {}}
for oid in IDS:
    d = HERE / oid
    ex = load(d / "extract.json")
    mm = load(d / "mesh_measure.json")
    st3 = load(d / "views" / "kunai_3q_stats.json") or {}
    stats_top = load(d / "views_top" / "kunai_3q_stats.json") or {}
    sec = load(d / "section.json") or {}
    basis = load(d / "study_basis.json")
    rep = load(d / "report" / "kunai_plain_report.json")
    o = {"section": sec, "extract": ex, "study_basis": {k: basis[k] for k in ("unground", "ground", "assembled")} if basis else None}
    # stations: mesh-measured
    rows = []
    for key, s in (mm or {}).get("stations", {}).items():
        p = post(s)
        ph = PHOTO_ST.get(key)
        rows.append({"x_mm": s["x_mm"], "half_width_mm": round(p["half_width_mm"], 3), "ridge_mm": s["ridge_thickness_mm"],
                     "face_slope": p.get("face_slope"), "face_angle_deg": p.get("face_angle_deg"),
                     "ridge_ratio": round(0.5 * s["ridge_thickness_mm"] / p["half_width_mm"], 4),
                     "grind_band_in_section_mm": p.get("grind_band_mm"),
                     "photo_face_slope": ph["face_slope"] if ph else None,
                     "photo_frac": ph["frac_from_shoulder"] if ph else None,
                     "vs_photo": round(p["face_slope"] / ph["face_slope"], 3) if ph and p.get("face_slope") else None})
    o["stations"] = rows
    front = [r["face_slope"] for r in rows if r["photo_frac"] and r["photo_frac"] >= 0.3]
    o["front_face_slope_median"] = sorted(front)[len(front) // 2] if front else None
    o["texel_blade_px_per_mm"] = (mm or {}).get("blade_texel_px_per_mm_area_weighted")
    o["lod_ridge_vs_lod0"] = {k: {kk: v[kk] for kk in ("max_ridge_thickness_delta_mm", "at_x_mm")} for k, v in ((mm or {}).get("lod_ridge_vs_lod0") or {}).items()}
    # coat figures by pose
    poses = {}
    for name, v in list(st3.items()) + list(stats_top.items()):
        c = v.get("coat") or {}
        sp = v.get("coat_split") or {}
        shot = "top" if "top" in name else "hero"
        poses[name] = {
            "coat_p50": c.get("p50"), "coat_mean": c.get("mean"), "coat_dark": c.get("fraction_below_0_03"),
            "vs_anchor": {k: round(c.get(k) - ANCHOR[shot][k], 4) for k in ("p50", "mean")} if c else None,
            "flat": sp.get("flat_coat_nz_ge_0_9995"), "tilted": sp.get("tilted_coat_0_95_to_0_9995"),
            "flat_vs_anchor": {k: round(sp["flat_coat_nz_ge_0_9995"][k] - ANCHOR[shot][k], 4) for k in ("p50", "mean")}
            if sp.get("flat_coat_nz_ge_0_9995") else None,
            "baked_minus_reference": sp.get("baked_minus_reference"),
            "reference": sp.get("reference_coat"),
        }
        bmr = sp.get("baked_minus_reference") or {}
        if "flat" in bmr and "tilted" in bmr:
            poses[name]["finish_transfer_tilted_minus_flat"] = {
                k: round(bmr["tilted"][k] - bmr["flat"][k], 4) for k in ("p50", "mean")}
    o["poses"] = poses
    if rep:
        o["lod_deviation_two_sided_mm"] = {k: v.get("two_sided") for k, v in rep.get("lod_surface_deviation_two_sided_mm", {}).items()}
        o["topology"] = rep.get("topology_quality")
    out["options"][oid] = o
(HERE / "options_data.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print("written options_data.json")
for oid, o in out["options"].items():
    print(oid, "front median", o["front_face_slope_median"], {k: (v["coat_p50"], v["coat_mean"], (v["flat"] or {}).get("p50"),
                                                                    v.get("finish_transfer_tilted_minus_flat")) for k, v in o["poses"].items()})
