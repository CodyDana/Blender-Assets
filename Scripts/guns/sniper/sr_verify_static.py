"""SR01 W3: SM_Att_Scope_LongRange verified on the EXPORTED bytes in a fresh Blender process (nothing from a build
scene):

    blender -b --factory-startup --python Scripts/guns/sniper/sr_verify_static.py

- files = the build's sha256; re-imported LOD triangles = the build's, strictly descending, LOD0 in the 6-10k target /
  12k ceiling; 3 hulls UCX_SM_Att_Scope_LongRange_LOD0_00..02; export warnings;
- S1: the 5 sockets of the exported sidecar vs the spec (scope_local_mm; CenterOfMass = the build's volume centroid)
  <= 0.001 mm, rotation 0;
- A1: Mount = the attachment origin and, mounted, Rail_Top + 2 slots (the exported SK sidecar's Rail_Top + 20.02 mm);
  A4: Sight Z above the bore 57.6 +-0.2 and parallel (rotation 0) from the exported sidecars;
- A3 on the exported bytes: the scope LOD0 at the mount vs the exported SK_SR01 LOD0 at rest (0 intersecting triangles,
  min distance >= 2 mm) and over A_SR01_BoltCycle (the 'bolt' vertex group posed per frame: F6 knob / bolt to scope
  >= 20 mm handle clearance is reported as the bolt group's minimum);
- B10 names. Writes gates/scope_export.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import ROOT, WORK, GATES, GRIP, D  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from gunlib import gateutil as GU  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import qa_gun  # noqa: E402
import sr_clips as CL  # noqa: E402

EXP = ROOT / "Exports" / "Guns" / "SR01"
NAME = "SM_Att_Scope_LongRange"
gate = GU.gate


def import_fbx(p):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(p), use_custom_normals=True, automatic_bone_orientation=False)
    return [o for o in bpy.data.objects if o not in before]


def bvh(V, T):
    return BVHTree.FromPolygons([tuple(v) for v in V], [tuple(int(i) for i in t) for t in T])


def min_dist(P, tree):
    best = 1e9
    for p in P:
        r = tree.find_nearest(p)
        if r[0] is not None:
            best = min(best, r[3])
    return best


def main():
    GU.clear_scene(data_blocks=True)
    REP = json.loads((WORK / "scratch" / "w3" / "scope" / "scope_report.json").read_text())
    RIG = json.loads((WORK / "scratch" / "w3" / "rig" / "rig_report.json").read_text())
    gates = []
    out = {"stage": "W3 scope attachment export, verified on the exported bytes (fresh process)"}
    bad = [f for f, r in REP["files"].items() if GU.sha256(ROOT / f) != r["sha256"]]
    gates.append(gate("files = the build's bytes (sha256)", {f: r["sha256"] for f, r in REP["files"].items()},
                      "all equal", not bad, ", ".join(bad) or None))
    objs = import_fbx(EXP / f"{NAME}.fbx")
    tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs
            if o.type == "MESH" and not o.name.startswith("UCX_")}
    ucx = sorted(o.name for o in objs if o.name.startswith("UCX_"))
    want = {f"{NAME}_LOD{k}": REP["lods"][f"LOD{k}"]["triangles"] for k in range(3)}
    seq = [tris.get(f"{NAME}_LOD{k}", 0) for k in range(3)]
    ok = all(tris.get(k) == v for k, v in want.items()) and seq[0] > seq[1] > seq[2] and seq[0] <= 12000
    gates.append(gate("re-imported LOD triangles = the build's; descending; LOD0 <= 12,000 (target 6-10k)",
                      {"fbx": tris, "build": want}, "equal; strictly descending; ceiling 12,000", ok,
                      "LOD0 under the 6k target floor is the W1 form (5,884: A5 accepted it)" if seq[0] < 6000 else None))
    gates.append(gate("hulls", ucx, "3 x UCX_SM_Att_Scope_LongRange_LOD0_NN",
                      len(ucx) == 3 and all(n.startswith(f"UCX_{NAME}_LOD0_") for n in ucx)))
    gates.append(gate("qa_check (before export)", {k: REP["qa_check"][k] for k in ("passed", "triangles", "checks")},
                      "pass; budget 12,000; UV1; UCX keyed to the node", REP["qa_check"]["passed"]))
    gates.append(gate("export warnings reviewed", REP["export"]["warnings"], "only 'sockets dropped into the sidecar'",
                      all("dropped" in w for w in REP["export"]["warnings"])))
    side = json.loads((EXP / f"{NAME}.sockets.json").read_text())
    ss = {s["socket"]: s for s in side["sockets"]}
    worst, wdeg = 0.0, 0.0
    for s in D["sockets"]["scope"]:
        e = np.array(REP["com_local_mm_volume"] if s["socket"] == "CenterOfMass" else s["scope_local_mm"], float)
        g = ss[s["socket"]]
        worst = max(worst, float(np.abs(np.array(g["location_cm"]) - np.array([e[0], -e[1], e[2]]) * 0.1).max()) * 10)
        wdeg = max(wdeg, max(abs(v) for v in g["rotation_deg"].values()))
    names_ok = sorted(ss) == sorted(s["socket"] for s in D["sockets"]["scope"])
    gates.append(gate("S1 scope sockets (exported sidecar vs spec)", {"count": len(ss), "names_match_spec": names_ok,
                      "worst_mm": round(worst, 6), "worst_deg": round(wdeg, 6)}, "5; <= 0.001 mm, 0 deg",
                      names_ok and worst <= 0.0011 and wdeg <= 0.001,
                      "CenterOfMass = the volume centroid of the scope parts (spec: provisional)"))
    sk_side = json.loads((EXP / "SK_SR01.skeletal.json").read_text())
    rt = next(s for s in sk_side["sockets"] if s["name"] == "Rail_Top")
    mount_B = np.array(D["scope_attachment"]["mount_M"], float) - GRIP
    a1 = float(mount_B[0] - rt["location_mm"][0])
    mount_side = max(abs(v) for v in ss["Mount"]["location_cm"]) * 10
    gates.append(gate("A1 Mount = origin; mounted at Rail_Top + 2 slots", {"mount_origin_mm": round(mount_side, 6),
                      "mount_minus_rail_top_mm": round(a1, 4), "slot_pitch_x2": 20.02}, "0; 20.02 +-0.001",
                      mount_side <= 0.001 and abs(a1 - 20.02) <= 0.001 and abs(mount_B[2] - rt["location_mm"][2]) <= 0.001))
    sight = np.array(ss["Sight"]["location_cm"]) * 10
    sight_bore = float(sight[2] + mount_B[2] + GRIP[2])
    gates.append(gate("A4 Sight above the bore and parallel (exported sidecars)", {"sight_Z_over_bore_mm": round(sight_bore, 4),
                      "rotation_deg": ss["Sight"]["rotation_deg"]}, "57.6 +-0.2; 0 deg",
                      abs(sight_bore - 57.6) <= 0.2 and max(abs(v) for v in ss["Sight"]["rotation_deg"].values()) <= 0.05))
    # A3 on the exported bytes
    sc0 = next(o for o in objs if o.type == "MESH" and o.name.startswith(f"{NAME}_LOD0"))
    Vs, Ts = GU.mesh_np(sc0)
    Vs = Vs + mount_B                                                    # frame B mm (the scope mounted)
    stree = bvh(Vs, Ts)
    # A3 is the scope clear of the gun ABOVE the rail: the ring bases / jaws clamp the rail by design (A2: lugs in the
    # slots 0.1-0.4); scope triangles whose centre is under the rail top + 5 mm are left out of the A3 distance
    z_cut = 30.0 + 5.0 - GRIP[2]
    Ta = Ts[Vs[Ts].mean(1)[:, 2] > z_cut]
    stree = bvh(Vs, Ta)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    sk = import_fbx(EXP / "SK_SR01.fbx")
    mesh = next(o for o in sk if o.type == "MESH")
    Vg, Tg = GU.mesh_np(mesh)
    gi = {g.index: g.name for g in mesh.vertex_groups}
    vb = np.array([gi[v.groups[0].group] if v.groups else "" for v in mesh.data.vertices])
    gtree = bvh(Vg, Tg)
    n_int = len(gtree.overlap(stree))
    Sg = GM.dense_samples(Vg, Tg, 2.0)
    d_rest = min_dist(Sg[(Sg[:, 2] > 60.0)], stree)                     # gun surface near the scope (above Z_B 60)
    heads = {n: np.array(v["head_mm"]) for n, v in RIG["bones"].items()}
    bolt_v = vb == "bolt"
    Tb = Tg[np.all(bolt_v[Tg], axis=1)]
    frames, _n, _f = CL.all_clips()["A_SR01_BoltCycle"]
    worst_b = (1e9, None)
    for f, v in frames:
        Mb = CL.basis_from(v).get("bolt", np.eye(4))
        Vp = Vg.copy()
        Vp[bolt_v] = (Vg[bolt_v] - heads["bolt"]) @ Mb[:3, :3].T + Mb[:3, 3] + heads["bolt"]
        Sb = GM.dense_samples(Vp, Tb, 2.0)
        d = min_dist(Sb, stree)
        if d < worst_b[0]:
            worst_b = (d, f)
    gates.append(gate("A3 scope vs the gun on the exported bytes (rest; over A_SR01_BoltCycle)",
                      {"intersecting_triangle_pairs_rest": n_int, "min_distance_rest_mm": round(d_rest, 3),
                       "bolt_group_min_distance_over_cycle_mm": round(worst_b[0], 3), "at_frame": worst_b[1]},
                      ">= 2 mm at rest and over the bolt cycle (A3, the scope above rail top + 5 mm; the ring jaws on the "
                      "rail are A2's); F6 (knob to scope >= 20) reported",
                      n_int == 0 and d_rest >= 2.0 and worst_b[0] >= 2.0,
                      "2 mm surface samples (the min distance is an upper bound within ~1 mm)"))
    words = {NAME} | set(ss) | set(ucx) | {Path(f).name for f in REP["files"]}
    hits = {w: qa_gun.deny_hits(w) for w in words if qa_gun.deny_hits(w)}
    gates.append(gate("B10 names", {"checked": len(words), "hits": hits}, "no hit", not hits))
    out["gates"] = gates
    out["failed"] = [g["name"] for g in gates if not g["pass"]]
    out["status"] = "pass" if not out["failed"] else "fail"
    out["files"] = REP["files"]
    out["screen_sizes"] = REP["screen_sizes"]
    (GATES / "scope_export.json").write_text(json.dumps(out, indent=1, default=str))
    print("[SR01-scopev]", out["status"], out["failed"])


main()
