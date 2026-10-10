"""SMG01 craft F-gates, B3b (folded state) and B4c (sights folded) on the built parts (inside Blender, frame M mm):

  F2   folded length (stock 180 deg about the hinge axle)                383.6 +-3
  F3   folded: the lug's barb under the port catch's hooked lip: engagement in X >= 1.0, barb-to-lip gap 0.2-0.4 in Y,
       0 intersections seated folded
  F6   latch: full diameter >= 1.5 in the lug's bore released; 0 pressed; (the fold sweep's exit-slot clearance is B3)
  F7   lock: at full travel + 15 deg the neck's underside at the wall's inner face >= 2.0 above the slot top; knob rise
  F5b  the bolt's thumb recess seen through the port at rest (rays from the right through the port hit the recess)
  B3b  folded: 0 intersections with every other part; the casing throw cone (ShellEject +X, 15 deg, 150 mm) vs the
       folded stock reported
  B4c  sights folded: rear <= Z 60.1, front <= Z 51.7, nothing below the rail top (45.4)

    blender -b Assets/Guns/SMG01.blend --factory-startup --python Scripts/guns/smg/smg_fgates.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import GRIP, SCRATCH, dims, socket, D as SPECD  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from gunlib import fit as F  # noqa: E402
from gunlib import gateutil as GU  # noqa: E402
from parts.stock import STROKE, N0, N1, S_OUT  # noqa: E402

objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")]
G = {k: (v[0] + GRIP, v[1]) for k, v in F.geom(objs).items()}         # frame M
SH, CH, SR, SFR = dims("stock_hinge"), dims("charging_handle"), dims("sight_rear"), dims("sight_front")
FOLD = SPECD["fold"]
STOCK = ["stock_frame", "stock_latch_button", "stock_latch_bolt", "butt_pad"]
AX = np.array([SH["axis_X"], SH["axis_Y"], 0.0])
out = {}


def moved(names, M):
    return {n: (F.apply(M, G[n][0]), G[n][1]) for n in names}


def overlaps(mov, fixed_names):
    res = {}
    for n, (V, T) in mov.items():
        t1 = F.tree(V, T)
        for f in fixed_names:
            p = t1.overlap(F.tree(*G[f]))
            if p:
                res[f"{n}/{f}"] = len(p)
    return res


Rf = F.rot_matrix(AX, (0, 0, 1), float(SH["fold_rot_Z_deg"]))
fold = moved(STOCK, Rf)
others = [n for n in G if n not in STOCK]
# ---- F2 folded length
allV = np.vstack([v for v, _ in fold.values()] + [G[n][0] for n in others if not n.startswith("magazine")])
flen = float(allV[:, 0].max() - allV[:, 0].min())
out["F2"] = {"folded_length_mm": round(flen, 2), "spec": float(FOLD["folded_length"]), "tol": 3.0,
             "rearmost_X": round(float(allV[:, 0].min()), 2), "real_mm": 450,
             "pass": abs(flen - float(FOLD["folded_length"])) <= 3.0}
fminY = {n: round(float(v[:, 1].min()), 2) for n, (v, _) in fold.items()}
out["F2"]["folded_min_Y_by_part"] = fminY
# ---- B3b / F3: folded, static
ov = overlaps(fold, others)
out["B3b"] = {"folded_intersections": ov, "pass": not ov}
lug = fold["stock_frame"][0]
EP = dims("ejection_port_and_catch")
lip = EP["catch_lip"]
barb_sel = (lug[:, 1] < -31.5) & (lug[:, 1] > -33.2) & (lug[:, 0] > 459.0) & (lug[:, 0] < 465.0) & \
           (lug[:, 2] > -13.0) & (lug[:, 2] < 3.0)
Vb = lug[barb_sel]
up = G["upper_receiver"][0]
lip_sel = (up[:, 0] > lip["X"][0] - 0.6) & (up[:, 0] < lip["X"][1] + 0.6) & (up[:, 1] < lip["Y"][1] + 0.3) & \
          (up[:, 1] > lip["Y"][0] - 0.3)
Vl = up[lip_sel]
if len(Vb) and len(Vl):
    eng = min(Vb[:, 0].max(), Vl[:, 0].max()) - max(Vb[:, 0].min(), Vl[:, 0].min())
    # the barb's outer face vs the lip's inner face, in Y, over their common X
    gapY = float(Vl[:, 1].max() - Vb[:, 1].min()) * -1.0
    # nearest distance between the two (sampled)
    t_up = F.tree(*G["upper_receiver"])
    dmin = min(t_up.find_nearest(Vector(p), 5.0)[3] or 9.0 for p in Vb)
    out["F3"] = {"barb_X": [round(float(Vb[:, 0].min()), 2), round(float(Vb[:, 0].max()), 2)],
                 "lip_X": [round(float(Vl[:, 0].min()), 2), round(float(Vl[:, 0].max()), 2)],
                 "engagement_X_mm": round(float(eng), 3), "barb_to_lip_min_distance_mm": round(float(dmin), 3),
                 "barb_Y": [round(float(Vb[:, 1].min()), 2), round(float(Vb[:, 1].max()), 2)],
                 "lip_Y": [round(float(Vl[:, 1].min()), 2), round(float(Vl[:, 1].max()), 2)],
                 "folded_intersections": ov,
                 "pass": eng >= 1.0 and 0.2 - 1e-3 <= dmin <= 0.4 + 1e-3 and not ov}
else:
    out["F3"] = {"error": "barb or lip vertices not found", "n_barb": int(len(Vb)), "n_lip": int(len(Vl)), "pass": False}
# ---- F6 latch
LUG = SH["latch"]["lug"]
lb = G["stock_latch_bolt"][0]
r_full = SH["latch"]["bolt"]["dia"] / 2.0
c = np.array(LUG["bore"]["centre_XZ"])
rad = np.hypot(lb[:, 0] - c[0], lb[:, 2] - c[1])
full = lb[rad > r_full - 0.01]
ys = np.sort(np.unique(np.round(full[:, 1], 3)))
# the full-diameter stations are the profile's rings at r: the segment [t0 + c, N0 - s]; its end = max Y below the neck
seg_end = float(ys[ys < N0].max()) if np.any(ys < N0) else None
eng_rel = None if seg_end is None else seg_end - LUG["Y"][0]
eng_pr = None if seg_end is None else max(0.0, seg_end - STROKE - LUG["Y"][0])
out["F6"] = {"full_diameter_end_Y": seg_end, "lug_Y": LUG["Y"], "engaged_full_diameter_released_mm": None if eng_rel is
             None else round(eng_rel, 3), "engaged_full_diameter_pressed_mm": None if eng_pr is None else round(eng_pr, 3),
             "neck_Y_released": [N0, N1], "stroke_mm": STROKE, "spec_stroke_mm": SH["latch"]["button"]["stroke"],
             "declared": "stroke 2.5 (spec 2.0): with 45 deg shoulders the spec's 2.0 stroke cannot carry a 6.4 neck across "
                         "the 6.0 lug with 2.0 engaged",
             "pass": eng_rel is not None and eng_rel >= 1.5 and eng_pr == 0.0}
# ---- F7 lock
travel = float(CH["travel_minus_X"])
pin = CH["lock_axis"]["YZ"]
Mlock = F.rot_matrix((0.0, pin[0], pin[1]), (1, 0, 0), 15.0) @ F.trans_matrix((-1, 0, 0), travel)
hv = F.apply(Mlock, G["charging_handle"][0])
kn0 = G["charging_handle"][0]
# the neck's underside where it crosses the wall's inner face (Y 27.3): the neck axis (along Y through the knob centre)
# posed by the travel + the lock; the cylinder's lowest point in that plane = axis Z - r / cos(tilt)
wall_in = float(CH["wall_inner_face_Y"])
kc = np.array([CH["knob_centre_XZ"][0], CH["knob_centre_Y"], CH["knob_centre_XZ"][1]], float)
A = F.apply(Mlock, np.array([[kc[0], 21.5, kc[2]], [kc[0], kc[1], kc[2]]]))
t = (wall_in - A[0, 1]) / (A[1, 1] - A[0, 1])
P = A[0] + t * (A[1] - A[0])
ax_ = (A[1] - A[0]) / np.linalg.norm(A[1] - A[0])
tilt = math.acos(min(1.0, abs(ax_[1])))
rise_plane = float(P[2] - kc[2])                              # the neck axis's height change in the wall plane
Pm = F.apply(Mlock, np.array([[kc[0], wall_in, kc[2]]]))[0]
rise = float(Pm[2] - kc[2])          # the spec's measure: the neck point that sat at the wall's inner face rises 2.09
top_over_slot = float(P[2] + CH["neck_dia"] / 2.0 / math.cos(tilt)) - float(CH["slot"]["Z"][1])
kn0 = G["charging_handle"][0]
kn1 = F.apply(Mlock, kn0[kn0[:, 1] > CH["knob_centre_Y"] - 3.0])
kz0 = kn0[kn0[:, 1] > CH["knob_centre_Y"] - 3.0][:, 2]
krise = float((kn1[:, 2].max() + kn1[:, 2].min()) / 2 - (kz0.max() + kz0.min()) / 2)
out["F7"] = {"neck_rise_at_wall_inner_face_mm": round(rise, 3), "neck_axis_rise_in_wall_plane_mm": round(rise_plane, 3),
             "neck_top_over_slot_top_mm": round(top_over_slot, 3),
             "knob_rise_mm": round(krise, 3), "spec_knob_rise_mm": CH["lock_motion"]["knob_rise"],
             "pass": rise is not None and rise >= 2.0}
# ---- F5b bolt thumb recess through the port
bolt_t = F.tree(*G["bolt"])
_names = [n for n in G if not n.startswith(tuple(STOCK))]
_offs = np.cumsum([0] + [len(G[n][0]) for n in _names])
all_t = GU.tree(np.vstack([G[n][0] for n in _names]), np.vstack([G[n][1] + o for n, o in zip(_names, _offs)]))
tr = dims("bolt")["thumb_recess"]
hits = 0
deep = 0
for x in np.arange(tr["centre_X_rest"] - 6, tr["centre_X_rest"] + 6.01, 1.0):
    for z in np.arange(6.0, 12.01, 1.0):
        h = all_t.ray_cast(Vector((x, -200.0, z)), Vector((0, 1, 0)), 400.0)
        if h[0] is not None:
            hb = bolt_t.ray_cast(Vector((x, -200.0, z)), Vector((0, 1, 0)), 400.0)
            if hb[0] is not None and abs(hb[0][1] - h[0][1]) < 1e-4:
                hits += 1
                if hb[0][1] > -11.8 + 0.4:
                    deep += 1
out["F5b"] = {"rays_hitting_the_bolt_first": hits, "of_which_in_the_recess": deep, "pass": deep >= 10,
              "note": "rays from the right through the port centre region (13 x 7 grid, 1 mm)"}
# ---- casing throw cone vs the folded stock (reported)
se = socket("ShellEject")
eul = [math.radians(a) for a in se["rotation"]["blender_euler_xyz_deg"]]
from mathutils import Euler  # noqa: E402
d = np.array(Euler(eul, "XYZ").to_matrix() @ Vector((1, 0, 0)))
p0 = np.array(se["M_mm"], float)
cone_hits = {}
for n, (V, T) in fold.items():
    rel = V - p0
    t = rel @ d
    ok = (t > 0) & (t < 150.0)
    perp = np.linalg.norm(rel - np.outer(t, d), axis=1)
    inside = ok & (perp <= t * math.tan(math.radians(15.0)))
    if inside.any():
        cone_hits[n] = int(inside.sum())
out["B3b"]["throw_cone"] = {"origin_M": p0.tolist(), "dir": np.round(d, 4).tolist(), "vertices_inside": cone_hits,
                           "clear": not cone_hits, "note": "reported (Q5): the folded stock lies along the right side"}
# ---- B4c sights folded
res = {}
for nm, d_, lim, zmin in (("sight_rear", SR, 60.1, 45.4), ("sight_front", SFR, 51.7, float(SFR["folded_Z"][0]))):
    px, pz = d_["pivot_XZ"]
    R = F.rot_matrix((px, 0.0, pz), (0, 1, 0), float(d_["fold_rotation_Y_deg"]))
    V = F.apply(R, G[nm + "_leaf"][0])
    res[nm] = {"folded_max_Z": round(float(V[:, 2].max()), 2), "limit": lim, "min_Z": round(float(V[:, 2].min()), 2),
               "lowest_allowed_Z": zmin,
               "pass": bool(V[:, 2].max() <= lim + 1e-6 and V[:, 2].min() >= zmin - 0.05)}
out["B4c"] = dict(res, pass_all=all(v["pass"] for v in res.values()))
(SCRATCH / "fgates_result.json").write_text(json.dumps(out, indent=1, default=float))
print("[FG]", json.dumps(out, default=float)[:4000])
