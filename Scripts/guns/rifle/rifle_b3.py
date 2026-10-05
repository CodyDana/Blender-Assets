"""AR-01 gate B3 (motion clearance, rest + extremes + sweep) and G5 static contacts, on Assets/Guns/AR01.blend:

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_b3.py -- [--quick]

Writes WorkFiles/guns/rifle/scratch/b3_result.json (the gates stage file is assembled by rifle_gates.py).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import GRIP, SCRATCH  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

from gunlib import fit as F  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in argv

ROWS = {"sliding": [0.15, 0.40], "hinge": [0.10, 0.30], "butt": [0.01, 0.05]}

objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")]
G = F.geom(objs)
rec = {o.name: json.loads(o["gun_part"]) for o in objs if "gun_part" in o}


def B(p):
    return np.asarray(p, float) - GRIP


GROUPS = {
    "bolt": {"parts": ["bolt_carrier"], "kind": "slide", "axis": [-1, 0, 0],
             "range": [0.0, rec["bolt_carrier"]["joint"]["travel_mm"]], "row": "sliding"},
    "trigger": {"parts": ["trigger"], "kind": "rot", "pivot": B([318.0, 0, -20.0]), "axis": [0, 1, 0],
                "range": [0.0, 12.0], "row": "hinge"},
    "selector": {"parts": ["selector"], "kind": "rot", "pivot": B([282.8, 0, -7.8]), "axis": [0, 1, 0],
                 "range": [0.0, 32.0], "row": "hinge"},
    "mag_release": {"parts": ["mag_catch"], "kind": "rot", "pivot": B([362.0, 0, -50.0]), "axis": [0, -1, 0],
                    "range": [0.0, 10.0], "row": "hinge"},
    "sight_rear": {"parts": ["rear_sight_leaf", "rear_sight_slider"], "kind": "rot", "pivot": B([504.0, 0, 41.0]),
                   "axis": [0, 1, 0], "range": [0.0, 6.0], "row": "hinge"},
}

out = {"groups": {}, "rule": "translation step <= min(c_min/2, 1 mm); rotation step <= min(1 deg, c_min / r_max); "
                             "0 intersections at every step; clearance (min distance to anything) >= the row's lower "
                             "bound at rest, over the sweep and at both extremes; the guide clearance (the minimum) "
                             "<= the row's upper bound"}
for g, d in GROUPS.items():
    mov = {n: G[n] for n in d["parts"]}
    fixed = {n: v for n, v in G.items() if n not in d["parts"]}
    lo, hi = ROWS[d["row"]]
    if d["kind"] == "slide":
        step = min(lo / 2.0, 1.0)
        if QUICK:
            step = 1.0
        vals = np.arange(d["range"][0], d["range"][1] + 1e-9, step)
        if vals[-1] < d["range"][1] - 1e-9:
            vals = np.r_[vals, d["range"][1]]
        every = max(1, int(round(1.0 / step)))
        motion = (lambda ax: (lambda v: F.trans_matrix(ax, v)))(d["axis"])
    else:
        V = np.vstack([G[n][0] for n in d["parts"]])
        rmax = float(np.linalg.norm(V - d["pivot"], axis=1).max())
        step = min(1.0, math.degrees(lo / rmax))
        if QUICK:
            step = 1.0
        vals = np.arange(d["range"][0], d["range"][1] + 1e-9, step)
        if vals[-1] < d["range"][1] - 1e-9:
            vals = np.r_[vals, d["range"][1]]
        every = 1 if len(vals) < 200 else 2
        motion = (lambda pv, ax: (lambda v: F.rot_matrix(pv, ax, v)))(d["pivot"], d["axis"])
    recs, summ = F.sweep(mov, fixed, motion, vals, clearance_every=every)
    summ["row_mm"] = [lo, hi]
    summ["pass_intersections"] = summ["intersecting_steps"] == 0
    summ["pass_clearance_lower"] = summ["min_clearance_mm"] >= lo - 1e-4
    summ["pass_guide_upper"] = summ["min_clearance_mm"] <= hi + 1e-4
    summ["pass"] = summ["pass_intersections"] and summ["pass_clearance_lower"] and summ["pass_guide_upper"]
    if d["kind"] == "rot":
        summ["r_max_mm"] = round(rmax, 2)
    out["groups"][g] = {"summary": summ, "worst_steps": sorted([r for r in recs if r["intersections"]],
                                                               key=lambda r: -r["intersections"])[:8]}
    print("[B3]", g, json.dumps(summ))

# static: every pair intersecting at rest (G5)
pairs = F.pair_intersections(G)
out["static_intersections"] = pairs
print("[B3] static intersecting pairs:", len(pairs), pairs[:12])
# contact gaps for every butt joint parent pair present in the records
contact = []
for n, r in rec.items():
    par = r.get("joint", {}).get("parent")
    if par and par in G:
        contact.append((n, par))
contact += [("pistol_grip", "trigger_guard"), ("pistol_grip", "receiver"), ("trigger_guard", "receiver"),
            ("buttstock", "rear_trunnion"), ("buttstock", "butt_plate"), ("rear_sight_block", "receiver"),
            ("rear_sight_block", "dust_cover"), ("upper_handguard", "lower_handguard"),
            ("gas_tube_rear_cap", "rear_sight_block"), ("muzzle_brake", "front_sight_block"),
            ("butt_screws", "butt_plate"), ("rivets", "receiver"), ("magazine", "receiver"),
            ("magazine", "mag_catch"), ("selector", "receiver"), ("selector", "rivets"),
            ("bolt_carrier", "receiver_rails"), ("bolt_carrier", "dust_cover"), ("bolt_carrier", "receiver"),
            ("trigger", "receiver"), ("trigger", "trigger_guard"), ("mag_catch", "trigger_guard"),
            ("rear_sight_leaf", "rear_sight_block"), ("rear_sight_slider", "rear_sight_leaf"),
            ("sling_swivel_loop", "sling_swivel_base"), ("gas_piston", "gas_tube")]
seen = set()
cp = []
for a, b in contact:
    k = tuple(sorted((a, b)))
    if k not in seen:
        seen.add(k)
        cp.append(k)
gaps = F.min_gaps(G, cp)
out["contact_gaps"] = gaps
print("[B3] gaps:", json.dumps(gaps))
(SCRATCH / ("b3_result_quick.json" if QUICK else "b3_result.json")).write_text(json.dumps(out, indent=1))
print("[B3] DONE")
