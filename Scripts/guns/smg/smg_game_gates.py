"""SMG01 W3 Blender-side gates on the saved twin (headless Blender; the AR-01's rifle_game_gates.py):

    blender -b Assets/Guns/SMG01.blend --factory-startup --python Scripts/guns/smg/smg_game_gates.py

- qa_check on SM_SMG01_LOD0..3 (pipeline; budget 55,000 = the gun's 50,000 ceiling + the merged magazine's 5,000; UV1
  required; UCX keyed to the node name; texel target = the measured LOD0 aggregate, qa's rule for mixed sets; LOD3 is
  recorded against it, not graded);
- C1: an independent jittered 0.5 mm sampling of every LOD0 part and every vertex of every LOD inside the union of the
  8 hulls (plane test, 1e-7 m);
- S1: a test export through Scripts/pipeline/export_fbx (LodGroup, sockets to the sidecar, the LOD-pop screen sizes)
  into scratch/game/export_test/, every sidecar socket vs the build (<= 0.001 mm, <= 0.001 deg) and vs the spec
  (CenterOfMass / Holster: the computed value);
- UD1 / UD3 on each joined twin LOD (gunlib.ud, gunlib.tspace unreal=True) and the layer order (UV0, UV1);
- B10 tokenised deny list on every object / material / image / socket name.
Writes scratch/game/game_gates_blender.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import SCRATCH, GATES, SPEC, CODE, PARTS_COLL  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import qa_gun  # noqa: E402
from gunlib import ud as UD  # noqa: E402
from gunlib import tspace as TS  # noqa: E402

GAME = SCRATCH / "game"
NAME = f"SM_{CODE}"
BUDGET = int(SPEC.d["budgets_triangles"]["twin_qa_budget"])


def log(*a):
    print("[SMG01-gates]", *a, flush=True)


def main():
    out = {}
    lods = [bpy.data.objects[f"{NAME}_LOD{k}"] for k in range(4)]
    q0 = qa_check(lods, budget_tris=BUDGET, texel_density=None, require_uv1=True)
    agg = {c["object"]: float(c["detail"].split(" px/cm")[0]) for c in q0["checks"] if c["name"] == "texel_density"}
    q = qa_check(lods[:3], budget_tris=BUDGET, texel_density=agg[f"{NAME}_LOD0"], require_uv1=True)
    failed = [c for c in q0["checks"] if not c["passed"]] + [c for c in q["checks"] if not c["passed"]]
    out["qa_check"] = {"passed": q0["passed"] and q["passed"], "triangles": q0["triangles"], "budget": BUDGET,
                       "texel_target_px_cm": agg[f"{NAME}_LOD0"], "texel_aggregate_px_cm": agg,
                       "lod3_texel_vs_lod0": round(agg[f"{NAME}_LOD3"] / agg[f"{NAME}_LOD0"] - 1.0, 3),
                       "failed": failed, "checks": len(q0["checks"]) + len(q["checks"])}
    log("qa", out["qa_check"]["passed"], q0["triangles"], [c["name"] + ":" + str(c["object"]) for c in failed][:12])
    # ---------------------------------------------------------------- C1
    hulls = sorted((c for c in lods[0].children if c.name.startswith("UCX_")), key=lambda o: o.name)
    rng = np.random.default_rng(20261011)
    P = np.vstack([GM.dense_samples(*GM.mesh_vt(o), 0.5, rng) * 0.001
                   for o in bpy.data.collections[PARTS_COLL].objects if o.type == "MESH"])
    ins = GM.inside_union(P, hulls)
    Vall = np.vstack([GM.mesh_vt(o)[0] * 0.001 for o in lods])
    insv = GM.inside_union(Vall, hulls)
    out["C1"] = {"hulls": [h.name for h in hulls], "hull_vertices": [len(h.data.vertices) for h in hulls],
                 "jittered_lod0_samples": int(len(P)), "samples_outside": int((~ins).sum()),
                 "lod_vertices": int(len(Vall)), "vertices_outside": int((~insv).sum()),
                 "pass": bool(ins.all() and insv.all() and len(hulls) == 8 and
                              max(len(h.data.vertices) for h in hulls) <= 32)}
    log("C1", {k: v for k, v in out["C1"].items() if k != "hulls"})
    # ---------------------------------------------------------------- S1 (test export)
    sizes = json.loads((GATES / "game_lod_sizes.json").read_text())[NAME]
    ex = GAME / "export_test"
    ex.mkdir(parents=True, exist_ok=True)
    grp = bpy.data.objects[f"{NAME}_LodGroup"]
    res = export_fbx(str(ex / f"{NAME}.fbx"), [grp], kind="static", lod_screen_sizes=list(sizes))
    side = json.loads(Path(res["sidecar"]).read_text())
    rep = json.loads((GAME / "game_report.json").read_text())
    spec = {r["socket"]: r for r in SPEC.gun_sockets()}
    rows, worst_mm, worst_deg = [], 0.0, 0.0
    for s in side["sockets"]:
        nm = s["socket"]
        b = rep["sockets"][nm]
        exp_cm = [b["blender_mm"][0] / 10.0, -b["blender_mm"][1] / 10.0, b["blender_mm"][2] / 10.0]
        dmm = max(abs(a - e) for a, e in zip(s["location_cm"], exp_cm)) * 10.0
        er = spec[nm]["unreal_rotation_deg"]
        ddeg = max(abs(((s["rotation_deg"][k] - er[k]) + 180.0) % 360.0 - 180.0) for k in ("roll", "pitch", "yaw"))
        dspec = None
        if not b["computed"]:
            dspec = max(abs(a - e) for a, e in zip(s["location_cm"], spec[nm]["unreal_cm"])) * 10.0
        rows.append({"socket": nm, "location_cm": s["location_cm"], "rotation_deg": s["rotation_deg"],
                     "d_build_mm": round(dmm, 5), "d_rot_deg": round(ddeg, 5),
                     "d_spec_mm": None if dspec is None else round(dspec, 5), "computed": b["computed"]})
        worst_mm = max(worst_mm, dmm, dspec or 0.0)
        worst_deg = max(worst_deg, ddeg)
    names = sorted(r["socket"] for r in rows)
    out["S1"] = {"export": res["filepath"], "warnings": res["warnings"], "lod_screen_sizes": side.get("lod_screen_sizes"),
                 "sockets": rows, "count": len(rows), "names_match_spec": names == sorted(spec),
                 "worst_mm": round(worst_mm, 5), "worst_deg": round(worst_deg, 5),
                 "pass": names == sorted(spec) and worst_mm <= 0.001 and worst_deg <= 0.001}
    log("S1", out["S1"]["count"], out["S1"]["worst_mm"], out["S1"]["worst_deg"], out["S1"]["pass"])
    # ---------------------------------------------------------------- UD on the joined twin LODs
    out["twin_ud"] = {}
    for o in lods:
        r = UD.check_object(o)
        out["twin_ud"][o.name] = {"ud1_drops": int(r["unreal_drops"]), "min_area_mm2": r["min_area_mm2"],
                                  "ud3_collapsed_unreal": int(len(TS.collapsed(o.data, "UV0", unreal=True))),
                                  "layers": [l.name for l in o.data.uv_layers]}
    log("twin UD", out["twin_ud"])
    # ---------------------------------------------------------------- B10
    allnames = [o.name for o in bpy.data.objects] + [m.name for m in bpy.data.materials] + \
        [i.name for i in bpy.data.images] + [r["socket"] for r in rows]
    hits = {n: qa_gun.deny_hits(n) for n in allnames if qa_gun.deny_hits(n)}
    out["B10_names"] = {"checked": len(allnames), "hits": hits, "pass": not hits}
    (GAME / "game_gates_blender.json").write_text(json.dumps(out, indent=1, default=str))
    log("GATES_DONE")


main()
