"""Summarise a spike build's report + pack report (Blender's python or any python 3).

    python iter_summary.py <reports_dir> [form]
"""
import json
import sys
from pathlib import Path

R = Path(sys.argv[1])
form = sys.argv[2] if len(sys.argv) > 2 else "spike"
r = json.loads((R / f"{form}_report.json").read_text(encoding="utf-8"))
print("library", r.get("library_version"), "gates", r["gates"])
for k, v in (r.get("render_gates") or {}).items():
    if isinstance(v, dict):
        print("  ", k, {kk: vv for kk, vv in v.items() if kk not in ("whole_object", "reference", "band", "mean_band")})
ps, ts = r["render_stats"][f"{form}_persp"], r["render_stats"][f"{form}_top"]
print("hero obj p50/mean", ps["object_luminance"]["p50"], ps["object_luminance"]["mean"],
      "coat", (ps.get("coat_luminance") or {}).get("p50"), (ps.get("coat_luminance") or {}).get("mean"))
print("top  obj p50/mean", ts["object_luminance"]["p50"], ts["object_luminance"]["mean"],
      "coat", (ts.get("coat_luminance") or {}).get("p50"), (ts.get("coat_luminance") or {}).get("mean"))
if ps.get("bar_wall_luminance"):
    bw = ps["bar_wall_luminance"]
    print("side p50/mean", bw["p50"], bw["mean"], "rgb", bw["mean_rgb"], "spread", bw["rgb_spread"])
    print("side dots", ps.get("bar_wall_dots"))
    print("coat dots hero", ps.get("coat_dots"))
    print("coat dots top", ts.get("coat_dots"))
print("backdrop", ps.get("backdrop_points"))
rig = r.get("render_rig") or {}
print("rig scale", rig.get("hero_rig_scale"), "placement", rig.get("hero_placement"), "composition", rig.get("hero_composition"))
print("uv", r["uv"])
print("uv_consistency", r["uv_consistency"]["passed"], r["uv_consistency"].get("island_map_deviation_px_at_2048"))
print("tex", (r.get("textures") or {}).get("size"), (r.get("textures") or {}).get("unused_texel_fill"))
print("knife curved", r["knife_shading"]["curved_side_facets_max_corner_normal_dev_deg"], "passed", r["knife_shading"]["passed"])
p = json.loads((R / "pack_report.json").read_text(encoding="utf-8"))["pack_consistency"]
print("pack_consistency passed", p["passed"])
print("  coat", p.get("bar_coat_vs_coat_anchor"))
print("  walls", p.get("bar_walls_vs_wall_anchor"))
for f, b in (p.get("backdrop") or {}).get("per_form", {}).items():
    print("  backdrop", f, b["passed"], b["misses"], b["min_headroom"])
print("  drift", p.get("anchor_drift", {}).get("drift"), p.get("anchor_drift", {}).get("coat"), "stale", p.get("anchor_drift", {}).get("anchor_stale"))
