"""SR01 W2 Blender-side gates on the surfaced LOD0 parts (headless Blender; the .blend is not saved):

    blender -b Assets/Guns/SR01.blend --factory-startup --python Scripts/guns/sniper/sr_w2_blender.py -- \
        [--tex DIR] [--out JSON]

- UD1 / UD2 re-run on every part as it now is (triangulated by the UV step; gunlib.ud.check_object): Unreal's drops,
  min triangle area >= 0.01 mm2, no edge < 0.05 mm, no needle < 0.02 mm, no strip < 0.1 mm;
- UD3 on every part's UV0 (gunlib.tspace: Blender MikkTSpace collapsed frames, float32_zero_corners (Unreal's float32
  MikkTSpace), edge_on_corners) = 0;
- layers: UV0 at index 0 and UV1 at index 1 on every part (qa_check grades UV0 by index);
- the static twin as W3 will join it (gunlib.game.join_copies: game materials on the painted maps, slot k on U tile k:
  Metal 0, Furniture 1, the merged magazine -1) through the pipeline's qa_check (budget 55,000 = 50,000 + the mag's
  5,000; UV1 required; texel target = the measured aggregate, qa's rule for mixed sets; UCX not yet: the hulls are
  W3), plus UD1 and UD3 on the joined mesh.
Writes scratch/w2_blender.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_surface import ROOT, SCRATCH, COLL as PARTS_COLL  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import sr_surface as SS  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import tspace as TS  # noqa: E402
from gunlib import ud as UD  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


TEX = Path(arg("--tex", str(SS.TEX)))
OUT = Path(arg("--out", str(SCRATCH / "w2_blender.json")))


def log(*a):
    print("[SR01-w2gates]", *a, flush=True)


def ud3(me):
    c = TS.collapsed(me, "UV0", unreal=False)
    z = TS.float32_zero_corners(me, "UV0")
    e = TS.edge_on_corners(me, "UV0")
    return {"collapsed": int(len(c)), "float32_zero_corners": int(len(z)), "edge_on_corners": int(len(e))}


def main():
    parts = [o for o in bpy.data.collections[PARTS_COLL].objects if o.type == "MESH"]
    out = {"parts": {}}
    for o in parts:
        r = UD.check_object(o)
        rec = {"ud1_drops": int(r["unreal_drops"]), "min_area_mm2": r["min_area_mm2"],
               "edges_under_0.05mm": r["edges_under_0.05mm"], "needles_under_0.02mm": r["needles_under_0.02mm"],
               "strip_polygons_under_0.1mm": r.get("strip_polygons_under_0.1mm", 0),
               "triangles": len(o.data.polygons), "layers": [l.name for l in o.data.uv_layers]}
        rec.update(ud3(o.data))
        out["parts"][o.name] = rec
        log(o.name, json.dumps(rec))
    P = out["parts"].values()
    out["ud1"] = {"drops": sum(p["ud1_drops"] for p in P), "min_area_mm2": min(p["min_area_mm2"] for p in P)}
    out["ud2"] = {k: sum(p[k] for p in P) for k in ("edges_under_0.05mm", "needles_under_0.02mm",
                                                     "strip_polygons_under_0.1mm")}
    out["ud3"] = {k: sum(p[k] for p in P) for k in ("collapsed", "float32_zero_corners", "edge_on_corners")}
    out["ud3"]["by_part"] = {n: {k: p[k] for k in ("collapsed", "float32_zero_corners", "edge_on_corners")}
                             for n, p in out["parts"].items()
                             if p["collapsed"] or p["float32_zero_corners"] or p["edge_on_corners"]}
    out["layers_ok"] = all(p["layers"][:2] == ["UV0", "UV1"] for p in P)
    out["triangles_lod0"] = {"gun": sum(p["triangles"] for n, p in out["parts"].items() if n not in SS.MAG_PARTS),
                             "magazine": sum(p["triangles"] for n, p in out["parts"].items() if n in SS.MAG_PARTS)}
    # ---------------------------------------------------------------- the twin as W3 joins it
    coll = bpy.data.collections.new("_W2_TwinCheck")
    bpy.context.scene.collection.children.link(coll)
    order = list(SS.SETS)
    mats = [GM.game_material(SS.SETS[st]["slot"], f"{SS.STEM}_{st}", TEX) for st in order]

    def slot_of(o):
        return order.index(SS.SLOT_SET[json.loads(o.get("gun_part", "{}"))["slot"]])
    tile = {order.index(st): SS.TILE_OF_SET[st] for st in order}
    tw = GM.join_copies(parts, "SM_SR01" if SS.TARGET == "gun" else "SM_Att_Scope_LongRange", coll, slot_of, mats, tile)
    budget = 55000 if SS.TARGET == "gun" else 12000      # (W4) the plan's attachment_optic ceiling (target 6-10k), as sr_attach
    q0 = qa_check([tw], budget_tris=budget, texel_density=None, require_uv1=True, require_ucx=False)
    agg = next(float(c["detail"].split(" px/cm")[0]) for c in q0["checks"] if c["name"] == "texel_density")
    q = qa_check([tw], budget_tris=budget, texel_density=agg, require_uv1=True, require_ucx=False)
    failed = [c for c in q["checks"] if not c["passed"]]
    out["qa_check_twin"] = {"passed": q["passed"], "triangles": q["triangles"], "texel_aggregate_px_cm": agg,
                            "checks": len(q["checks"]), "failed": failed,
                            "rows": {c["name"]: c["detail"] for c in q["checks"]
                                     if c["name"] in ("uv_no_overlap", "uv1_no_overlap", "uv0_tile_range",
                                                      "uv1_inside_0_1", "triangle_budget", "texel_density",
                                                      "no_coincident_vertices", "manifold")}}
    r = UD.check_object(tw)
    out["twin_ud1"] = {"drops": int(r["unreal_drops"]), "min_area_mm2": r["min_area_mm2"]}
    out["twin_ud3"] = ud3(tw.data)
    log("twin qa", q["passed"], json.dumps(failed)[:600])
    log("twin UD1", out["twin_ud1"], "UD3", out["twin_ud3"])
    OUT.write_text(json.dumps(out, indent=1, default=str))
    log("W2_BLENDER_DONE")


main()
