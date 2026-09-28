"""Print the key numbers of a (scratch or final) pack build: gates, masses, grind, render stats.

    <blender python> summarize.py <report_dir> [form ...]
"""
import json
import sys
from pathlib import Path

rep_dir = Path(sys.argv[1])
forms = sys.argv[2:] or ["four_point", "eight_point", "square_plate"]
ref = json.loads(Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\style_reference\ref_rig_stats.json")
                 .read_text())["scaled100"]


def lum(stats):
    if not stats:
        return "-"
    o = stats.get("object_luminance") or {}
    f = (stats.get("facet_luminance") or {})
    w = stats.get("wall_luminance") or {}
    return (f"mean {o.get('mean')} p50 {o.get('p50')} p05 {o.get('p05')} p95 {o.get('p95')} | facets all p50 "
            f"{(f.get('all') or {}).get('p50')} near p50 {(f.get('near') or {}).get('p50')} | walls p50 {w.get('p50')}")


print("REF   hero", lum(ref["hero"]))
print("REF   top ", lum(ref["top"]))
for form in forms:
    path = rep_dir / f"{form}_report.json"
    if not path.exists():
        print(form, "no report")
        continue
    r = json.loads(path.read_text())
    m = r["measured"]
    g = m.get("grind") or {}
    print(f"{form}: lods {r['lod_triangles']} bands {r['lod_bands_ok']} qa {r['qa']['passed']} "
          f"gates {r.get('gates')}")
    print(f"   outline {m.get('outline_mass_g')} g ground {m.get('ground_mass_g')} g "
          f"angle {(g.get('grind_angle_deg') or {}).get('area_weighted_mean')} land {(g.get('edge_land_mm') or {}).get('max')} "
          f"tip r {g.get('tip_radius_mm')} ridge {g.get('tip_ridge_included_deg')}")
    rs = r.get("render_stats") or {}
    print("   hero", lum(rs.get(f"{form}_persp")))
    print("   top ", lum(rs.get(f"{form}_top")))
    rg = r.get("render_gates") or {}
    print("   render gates", {k: v.get("passed") for k, v in rg.items() if isinstance(v, dict)}, rg.get("passed"))
pack = rep_dir / "pack_report.json"
if pack.exists():
    p = json.loads(pack.read_text())
    pc = p.get("pack_consistency") or {}
    print("pack passed", p.get("passed"), "consistency", pc.get("passed"),
          {k: v for k, v in pc.items() if k.endswith("max_offset")})
