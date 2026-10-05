"""AR-01 stage 4 Blender-side gates on the saved twin (headless Blender):

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_game_gates.py

- qa_check on SM_AR01_LOD0..3 (pipeline; budget 57,000 = the rifle's 50,000 ceiling + the merged magazine's 7,000;
  texel target = the measured aggregate, qa's own rule for mixed sets; UV1 required; UCX keyed to the node name)
- C1: an independent jittered 0.5 mm sampling of every LOD0 part, and every vertex of every LOD, inside the union of
  the 7 hulls (plane test, 1e-7 m)
- S1: a test export through Scripts/pipeline/export_fbx (LodGroup, sockets to the sidecar, the LOD-pop screen sizes)
  into scratch/game/export_test/, then every sidecar socket vs the build value (<= 0.001 mm, <= 0.001 deg) and vs the
  spec (CenterOfMass / Holster: the computed value)
Writes scratch/game/game_gates_blender.json.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SCRATCH, GRIP, SPEC  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(ROOT / "Scripts"))
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import qa_gun  # noqa: E402

GAME = SCRATCH / "game"
NAME = "SM_AR01"


def log(*a):
    print("[AR01-gates]", *a, flush=True)


def main():
    out = {}
    lods = [bpy.data.objects[f"{NAME}_LOD{k}"] for k in range(4)]
    # ---------------------------------------------------------------- qa_check
    # every check on all four LODs (LOD order included); the texel figure qa grades is one aggregate over mixed sets
    # (4096 Metal + 2048 Furniture / Mag), so its target is the measured LOD0 aggregate +-25 % (plan 5.3, katana
    # precedent) for LOD0-2; LOD3 (the silhouette level, >= 20 m: blockout faces snapped onto the LOD0 islands) is
    # recorded against it, not graded
    q0 = qa_check(lods, budget_tris=57000, texel_density=None, require_uv1=True)
    agg = {}
    for c in q0["checks"]:
        if c["name"] == "texel_density":
            agg[c["object"]] = float(c["detail"].split(" px/cm")[0])
    q = qa_check(lods[:3], budget_tris=57000, texel_density=agg[f"{NAME}_LOD0"], require_uv1=True)
    failed = [c for c in q0["checks"] if not c["passed"]] + [c for c in q["checks"] if not c["passed"]]
    out["qa_check"] = {"passed": q0["passed"] and q["passed"], "triangles": q0["triangles"],
                       "texel_target_px_cm": agg[f"{NAME}_LOD0"], "texel_aggregate_px_cm": agg,
                       "lod3_texel_vs_lod0": round(agg[f"{NAME}_LOD3"] / agg[f"{NAME}_LOD0"] - 1.0, 3),
                       "failed": failed, "checks": len(q0["checks"]) + len(q["checks"])}
    log("qa", q["passed"], q["triangles"], [c["name"] + ":" + str(c["object"]) for c in q["checks"] if not c["passed"]])
    # ---------------------------------------------------------------- C1
    hulls = sorted((c for c in lods[0].children if c.name.startswith("UCX_")), key=lambda o: o.name)
    rng = np.random.default_rng(20261005)
    pts = []
    for o in bpy.data.collections["AR01_Parts"].objects:
        V, T = GM.mesh_vt(o)
        pts.append(GM.dense_samples(V, T, 0.5, rng) * 0.001)
    P = np.vstack(pts)
    ins = GM.inside_union(P, hulls)
    verts = []
    for o in lods:
        V, _ = GM.mesh_vt(o)
        verts.append(V * 0.001)
    Vall = np.vstack(verts)
    insv = GM.inside_union(Vall, hulls)
    out["C1"] = {"hulls": [h.name for h in hulls], "hull_vertices": [len(h.data.vertices) for h in hulls],
                 "jittered_lod0_samples": int(len(P)), "samples_outside": int((~ins).sum()),
                 "lod_vertices": int(len(Vall)), "vertices_outside": int((~insv).sum()),
                 "pass": bool(ins.all() and insv.all() and len(hulls) == 7 and
                              max(len(h.data.vertices) for h in hulls) <= 32)}
    log("C1", out["C1"])
    # ---------------------------------------------------------------- S1 (test export)
    sizes = json.loads((ROOT / "WorkFiles" / "guns" / "rifle" / "gates" / "game_lod_sizes.json").read_text())["SM_AR01"] \
        if (ROOT / "WorkFiles" / "guns" / "rifle" / "gates" / "game_lod_sizes.json").exists() else [1.0, 0.3, 0.12, 0.04]
    ex = GAME / "export_test"
    ex.mkdir(parents=True, exist_ok=True)
    grp = bpy.data.objects[f"{NAME}_LodGroup"]
    res = export_fbx(str(ex / "SM_AR01.fbx"), [grp], kind="static", lod_screen_sizes=list(sizes))
    side = json.loads(Path(res["sidecar"]).read_text())
    rep = json.loads((GAME / "game_report.json").read_text())
    rows = []
    worst_mm, worst_deg = 0.0, 0.0
    spec = {r["socket"]: r for r in SPEC.sockets["rifle"]}
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
    expect = sorted(r["socket"] for r in SPEC.sockets["rifle"])
    out["S1"] = {"export": res["filepath"], "sidecar": res["sidecar"], "warnings": res["warnings"],
                 "lod_screen_sizes": side.get("lod_screen_sizes"), "sockets": rows, "count": len(rows),
                 "names_match_spec": names == expect, "worst_mm": round(worst_mm, 5), "worst_deg": round(worst_deg, 5),
                 "pass": names == expect and worst_mm <= 0.001 and worst_deg <= 0.001}
    log("S1", out["S1"]["count"], out["S1"]["worst_mm"], out["S1"]["worst_deg"], out["S1"]["pass"])
    # ---------------------------------------------------------------- names (B10)
    allnames = [o.name for o in bpy.data.objects] + [m.name for m in bpy.data.materials] + \
               [i.name for i in bpy.data.images] + [r["socket"] for r in rows]
    hits = {n: qa_gun.deny_hits(n) for n in allnames if qa_gun.deny_hits(n)}
    out["B10_names"] = {"checked": len(allnames), "hits": hits, "pass": not hits}
    (GAME / "game_gates_blender.json").write_text(json.dumps(out, indent=1))
    log("GATES_DONE")


main()
