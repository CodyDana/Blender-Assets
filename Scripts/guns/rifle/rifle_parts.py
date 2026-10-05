"""Stage 2 form: every AR-01 part as real geometry (frame M, mm), from rifle_spec.json.

Rules (RIFLE_BUILD_PLAN 4, GUN_BUILDING_STUDY 3.1/3.2/3.7):
- side outlines come from the traced profiles (spec side_profile_M), cleaned (Douglas-Peucker for steel, smoothing
  for wood) or authored from the trace numbers where the trace is noisy; widths from TOP; sections from the
  close-ups and the real pattern;
- every part a closed solid; butt joints keep a 0.02 mm modelled gap (no shared vertices); moving parts are
  separate solids with their pivot, axis and limits (sweep: fit.py);
- every opening the sheet shows is cut with its wall; fasteners are real geometry.

Detail pass (2026-10-04): every detailed part lives in its own module Scripts/guns/rifle/parts/<module>.py with
build(spec, ctx) (parts/__init__.py lists them and which registry keys each owns). This file keeps the shared
constants and helpers (GAP, WO, WT, COVER_O / COVER_I, LEDGE, prof, the lower-handguard tenon), the rear trunnion and
the build harness; rifle_parts2.py keeps the other non-detailed parts. ORDER fixes the object order of the .npz and
build report (the refactor rebuilt the identical model: same bytes in form_tris.npz).
"""
from __future__ import annotations

import json
from typing import Dict

import numpy as np

from rifle_common import SPEC, GRIP
from gunlib import geo2d as G
from gunlib import mesh as MS
from gunlib.mesh import Mesh
from gunlib.parts import PartDef

GAP = 0.02            # butt-joint modelled gap (clearance table 3.7: 0.01-0.05)
WO = 20.75            # receiver wall outer half width (key dim 41.5)
WT = 1.0              # sheet thickness
COVER_O = 21.75       # dust cover outer half width (key dim 43.5)
COVER_I = WO + GAP    # dust cover inner half width
LEDGE = [(241.0, -32.85), (255.0, -32.5), (300.0, -31.3), (360.0, -29.5), (370.0, -29.25)]


def ledge_z(x):
    return float(G.polyline_interp(LEDGE, x))


def prof(pid, tol=0.55):
    return G.clean_hard(SPEC.profile(pid), tol)


def lower_handguard_tenon(grow, x0, x1) -> Mesh:
    """Hidden tenon on the lower handguard's rear end (sits in the receiver's front cup, X 484.0-485.3); with
    grow > 0 it is the matching pocket cutter."""
    sec = G.rounded_rect(-16.0 - grow, 16.0 + grow, -25.5 - grow, 8.5 + grow, 3.0, 3)
    m = MS.prism(np.c_[sec[:, 0], sec[:, 1]], x0, x1, "YZ")
    return m


def rear_trunnion() -> PartDef:
    d = 2 * GAP                     # rear face 0.04 forward of the stock's front face (which is this outline)
    o = [(225.2 + d, 7.0), (225.2 + d, -17.5), (228.7 + d, -22.0), (229.0 + d, -28.5), (230.1 + d, -34.0),
         (231.6 + d, -37.2), (240.9 - GAP, -37.2), (240.9 - GAP, 10.38), (238.2, 10.38), (237.2, 7.8), (226.4, 7.8)]
    # TOP: the block is the stock-wrist width (33) back to X ~233, then flares to the receiver width
    rear = MS.prism(G.clip_x(np.array(o, float), None, 234.0), -16.6, 16.6)
    front = MS.prism(G.clip_x(np.array(o, float), 233.0, None), -WO, WO)
    import rifle_parts2 as R2       # realism round 2: the trunnion's upper tang over the wrist (object rear_tang)
    return (PartDef("rear_trunnion", [rear], unions=[front], cls="M-chamfer", recipe=[(0.45, 1, 40.0)],
                    joint={"type": "butt", "parent": "receiver", "gap_mm": [0.01, 0.05]}), R2.rear_tang())


# ======================================================================================== harness
# registry keys in build / export order (the .npz object order; unchanged by the detail-pass refactor)
ORDER = ("receiver", "rear_trunnion", "dust_cover", "recoil_spring_button", "rivets", "receiver_rails", "bolt_carrier",
         "rear_sight_block", "rear_sight_leaf", "handguard_retainer", "gas_tube_rear_cap", "upper_handguard",
         "lower_handguard", "handguard_front_band", "gas_tube", "gas_piston", "gas_block", "barrel", "cleaning_rod",
         "front_sight_block", "front_sight_post", "muzzle_brake", "trigger", "trigger_guard", "mag_catch",
         "pistol_grip", "buttstock", "butt_plate", "butt_screws", "sling_swivel_base", "sling_swivel_loop",
         "stock_hardware", "selector", "magazine", "magazine_floor_plate")


def part_defs() -> Dict[str, object]:
    """registry key -> provider: a legacy callable (PartDef factory, or builder(coll, offset) -> object) for the parts
    outside the detail pass, or the NAME (str) of the detail-part module in Scripts/guns/rifle/parts/ that builds it."""
    import rifle_parts2 as R2
    import parts as PM
    legacy = {"rear_trunnion": rear_trunnion,
              "gas_tube_rear_cap": R2.gas_tube_rear_cap, "upper_handguard": R2.upper_handguard,
              "lower_handguard": R2.lower_handguard, "handguard_front_band": R2.front_band, "gas_tube": R2.gas_tube,
              "gas_piston": R2.gas_piston, "gas_block": R2.gas_block, "barrel": R2.barrel,
              "buttstock": R2.build_buttstock, "sling_swivel_base": R2.sling_swivel, "sling_swivel_loop": R2.sling_loop,
              "stock_hardware": R2.stock_hardware}
    d = {}
    for k in ORDER:
        d[k] = legacy[k] if k in legacy else PM.owner_of(k)
    for k, v in EXTRA.items():
        d[k] = v
    return d


EXTRA: Dict[str, object] = {}


def build_all(only=None, tag=None, coll_name="AR01_Parts"):
    """Build every part (or only the registry keys listed) into collection coll_name; export the triangles
    (scratch/form_tris.npz, or form_partial_tris.npz with only, or <tag>_tris.npz) and the manifold report, in ORDER.
    The LOD builds (build_rifle --stage lod) pass a tag so the form stage's files are never overwritten."""
    from gunlib import bl
    from gunlib.parts import BuildCtx
    from rifle_common import SCRATCH
    import parts as PM
    coll = bl.collection(coll_name)
    ctx = BuildCtx(coll, GRIP, SPEC, only)
    defs = part_defs()
    built: Dict[str, list] = {}
    done = set()
    for name, prov in defs.items():
        if only and name not in only:
            continue
        if isinstance(prov, str):                         # a detail-part module builds all its keys at once
            if prov not in done:
                built.update(PM.load(prov).build(SPEC, ctx))
                done.add(prov)
        else:
            built[name] = ctx.make(name, prov)
    objs, report = [], {}
    for name in defs:
        for ob in built.get(name, []):
            nf = bl.fix_slivers(ob)              # integration round: qa_check's degenerate-face rule (B6a)
            if nf:
                print("[AR01] %s: %d sliver faces removed" % (ob.name, nf))
            rep = bl.manifold_report(ob)
            report[ob.name] = rep
            objs.append(ob)
            print("[AR01] part %-24s tris %6d  boundary %d  multi %d  shells %d" % (
                ob.name, rep["triangles"], rep["boundary_edges"], rep["multi_face_edges"], rep["shells"]))
    tag = tag or ("form" if not only else "form_partial")
    bl.export_npz(objs, SCRATCH / f"{tag}_tris.npz", GRIP, [o.name for o in objs])
    (SCRATCH / f"{tag}_build_report.json").write_text(json.dumps(report, indent=1))
    print("[AR01] total tris", sum(r["triangles"] for r in report.values()))
    return objs, report
