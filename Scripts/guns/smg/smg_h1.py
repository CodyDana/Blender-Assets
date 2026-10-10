"""SMG01 gate H1, EARLY (SMG_BUILD_PLAN 14.2, W1): measurement-based hand-fit checks of the built grip and trigger
against the locked MH_PlayerDefault fit body's right hand and documented real-world numbers (the AR-01 method,
rifle_h1.py). PASS = trigger reach <= 80 mm AND grip girth <= real polymer SMG grips + 10 %; Grip depth within 1 mm of
the hand's palm centre; SupportHand on the magwell front reachable (<= 1.5 mm off the surface); length of pull and the
cheek-weld eye height reported. A FAIL does not stop the build: it is reported to the user with the numbers (Q1).

    blender -b References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend --factory-startup
        --python Scripts/guns/smg/smg_h1.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, SPEC, GRIP, BLEND, SCRATCH, dims, socket  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

LOCK = json.loads((ROOT / "References" / "Characters" / "MH_PlayerDefault" / "base_lock.json").read_text())
out = {"body": "References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend",
       "body_sha256_locked": LOCK.get("blend_sha256"), "mode": "early (measurement-based); posed H1 at W3"}
out["body_sha256_now"] = hashlib.sha256((ROOT / out["body"]).read_bytes()).hexdigest()
out["body_sha256_matches_lock"] = out["body_sha256_now"] == out["body_sha256_locked"]

arm = bpy.data.objects["root"]
Mw = arm.matrix_world


def head(n):
    return np.array(Mw @ arm.data.bones[n].head_local) * 1000.0


def tail(n):
    return np.array(Mw @ arm.data.bones[n].tail_local) * 1000.0


wrist = head("hand_r")
hand_len = float(np.linalg.norm(tail("middle_03_r") - wrist))
idx_dip, idx_tip = head("index_03_r"), tail("index_03_r")
web = 0.5 * (head("index_01_r") + head("thumb_02_r"))
L_web_dip = float(np.linalg.norm(idx_dip - web))
L_web_pad = float(np.linalg.norm(0.5 * (idx_dip + idx_tip) - web))
palm_centre = 0.5 * (wrist + 0.5 * (head("index_01_r") + head("pinky_01_r")))
L_web_palmc = float(np.linalg.norm(palm_centre - web))
arm_len = float(np.linalg.norm(head("lowerarm_r") - head("upperarm_r")) + np.linalg.norm(wrist - head("lowerarm_r")))
out["hand"] = {"hand_length_mm": round(hand_len, 1), "web_to_index_DIP_mm": round(L_web_dip, 1),
               "web_to_index_pad_mm": round(L_web_pad, 1), "web_to_palm_centre_mm": round(L_web_palmc, 1),
               "upper+lower arm_mm": round(arm_len, 1)}

with bpy.data.libraries.load(str(BLEND), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n in ("lower_receiver", "trigger", "grip_cover", "butt_pad",
                                                     "sight_rear_leaf", "sight_front_leaf")]
for o in dst.objects:
    bpy.context.scene.collection.objects.link(o)
G = {o.name: o for o in dst.objects}


def tris(o):
    me = o.data
    me.calc_loop_triangles()
    V = np.array([v.co for v in me.vertices]) * 1000.0 + GRIP
    T = np.array([t.vertices[:] for t in me.loop_triangles])
    return V, T


PG = dims("pistol_grip")
REAL_WORLD = {
    "grip_width_mm": {"min": 30.0, "max": 33.0, "sources": [
        {"what": "spec pistol_grip.width_note: real polymer SMG grips 31-33 (craft norm)", "url": None},
        {"what": "IMI Defense AK47/AK74 EG polymer pistol grip", "value": "Width 3 cm",
         "url": "https://imidefense.com/product/ak47-ak74-eg-polymer-pistol-grip/"},
        {"what": "Magpul MOE grip (AR-15 class)", "value": "width 1.2 in (30.5 mm)",
         "url": "https://blog.primaryarms.com/guide/what-is-the-best-ar-15-pistol-grip-guide/"}]},
    "strap_radius_mm": {"front": PG["front_strap_R"], "back": PG["back_strap_R"], "source": "spec pistol_grip dims"},
    "trigger_reach_mm": {"real_band": [57.2, 72.0], "gate_max": 80.0, "sources": [
        {"what": "AR-15 standard grip", "value": "trigger length 2.25 in (57.2 mm)",
         "url": "https://www.bluesheepdog.com/2015/03/18/new-accu-grip-ar-15-pistol-grip/"},
        {"what": "Glock 17", "value": "Trigger Distance 72 mm",
         "url": "https://us.glock.com/en/products/law-enforcement/pistols/g17"}]},
}


def oblong_perimeter(D, W, Rf, Rb):
    return 2 * (D + W) - (4 - math.pi) * (Rf + Rb)


# ---- girth: the grip section perpendicular to its axis at the Grip origin
ang = math.radians(PG["axis_rake_deg_from_vertical"])
axis = np.array([-math.sin(ang), 0.0, -math.cos(ang)])
origin = np.asarray(GRIP, float)
bm = bmesh.new()
bm.from_mesh(G["lower_receiver"].data)
res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-7, plane_co=Vector((0, 0, 0)),
                             plane_no=Vector(axis), clear_inner=False, clear_outer=False)
cut = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
pts = np.array([v.co for v in res["geom_cut"] if isinstance(v, bmesh.types.BMVert)]) * 1000.0
# keep the grip's own loop: the cut points within 40 mm of the axis
near = np.linalg.norm(pts, axis=1) < 40.0
perim = sum(e.calc_length() for e in cut if np.linalg.norm(np.array(e.verts[0].co) * 1000.0) < 40.0) * 1000.0
P = pts[near]
bm.free()
pdir = np.array([math.cos(ang), 0.0, -math.sin(ang)])
depth = float(np.ptp(P @ pdir))
width = float(np.ptp(P[:, 1]))
band_max = oblong_perimeter(depth, REAL_WORLD["grip_width_mm"]["max"], PG["front_strap_R"][0], PG["back_strap_R"][0])
band_min = oblong_perimeter(depth, REAL_WORLD["grip_width_mm"]["min"], PG["front_strap_R"][1], PG["back_strap_R"][1])
out["girth"] = {"section_at": "Grip origin, perpendicular to the grip axis (21.87 deg)", "perimeter_mm": round(perim, 1),
                "width_Y_mm": round(width, 2), "depth_mm": round(depth, 2),
                "real_band_mm": [round(band_min, 1), round(band_max, 1)],
                "limit_mm": round(1.10 * band_max, 1),
                "rule": "rounded oblong of the measured depth with the real width 30-33 and the spec strap radii; "
                        "PASS = perimeter <= the band's top + 10 % (plan 14.2 H1 early)",
                "pass": perim <= 1.10 * band_max}

# ---- reach: the back strap at the web (deepest point of the hollow under the beaver tail) -> the trigger face
trig_face = np.array(socket("Trigger")["M_mm"], float)
# (W1 realism round 1) the back strap's profile from the mid-plane SECTION of the moulding (bisect at Y 0), not from
# vertices that happen to lie within 1.5 mm of it: the UD repair's flat dissolve can leave none there
bm = bmesh.new()
bm.from_mesh(G["lower_receiver"].data)
res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-7, plane_co=Vector((0, 0, 0)),
                             plane_no=Vector((0, 1, 0)), clear_inner=False, clear_outer=False)
Vs = np.array([v.co for v in res["geom_cut"] if isinstance(v, bmesh.types.BMVert)]) * 1000.0 + np.asarray(GRIP, float)
bm.free()
Vg, Tg = tris(G["lower_receiver"])
near_mid = np.abs(Vs[:, 1]) < 1.5
best = None
for zz in np.arange(-48.0, -75.01, -0.5):
    sel = near_mid & (np.abs(Vs[:, 2] - zz) < 0.6) & (Vs[:, 0] < 300.0) & (Vs[:, 0] > 260.0)
    if sel.any():
        xb = float(Vs[sel, 0].min())
        if best is None or xb > best[0]:
            best = (xb, zz)
web_pt = np.array([best[0], 0.0, best[1]])
reach = float(np.linalg.norm(trig_face - web_pt))
out["reach"] = {"web_point_M": np.round(web_pt, 2).tolist(), "trigger_face_M": trig_face.tolist(),
                "reach_mm": round(reach, 1), "spec_reach_mm": float(PG.get("trigger_reach", 82.0))
                if "trigger_reach" in PG else 82.0,
                "real_band_mm": REAL_WORLD["trigger_reach_mm"]["real_band"], "gate_max_mm": 80.0,
                "hand_web_to_DIP_mm": round(L_web_dip, 1), "hand_web_to_pad_mm": round(L_web_pad, 1),
                "rule": "web hollow -> trigger face <= 80 mm (plan H1 early); the trigger is the sheet's, not moved",
                "pass": reach <= 80.0}

# ---- the Grip origin's depth (46 mm standard) vs this hand's palm centre on the knuckle line
i1, p1 = head("index_01_r"), head("pinky_01_r")
u_k = (p1 - i1) / np.linalg.norm(p1 - i1)
along = float((palm_centre - web) @ u_k)
web_on_axis = origin - axis * 46.0
out["grip"] = {"standard_Grip_depth_mm": 46.0, "hand_palm_centre_along_knuckle_line_mm": round(along, 1),
               "web_line_point_M": np.round(web_on_axis, 2).tolist(), "pass": abs(46.0 - along) <= 1.0}

# ---- SupportHand on the magwell front: a ray from the front must hit the lower's front face at the socket
tree = BVHTree.FromPolygons([tuple(v) for v in Vg], [tuple(t) for t in Tg], all_triangles=True)
sh = np.array(socket("SupportHand")["M_mm"], float)
hit = tree.ray_cast(Vector((sh[0] + 60.0, sh[1], sh[2])), Vector((-1, 0, 0)))
hx = None if hit[0] is None else float(hit[0][0])
sep = float(np.linalg.norm(sh - origin))
out["support"] = {"SupportHand_M": sh.tolist(), "front_face_hit_X": None if hx is None else round(hx, 2),
                  "offset_from_surface_mm": None if hx is None else round(sh[0] - hx, 2),
                  "hand_separation_mm": round(sep, 1), "arm_length_mm": round(arm_len, 1),
                  "pass": hx is not None and abs(sh[0] - hx) <= 1.5 and sep < 1.6 * arm_len}

# ---- reported: length of pull, cheek-weld eye height vs the sight line
lop = float(trig_face[0] - 0.0)
out["length_of_pull"] = {"mm": round(lop, 1), "real_mm": [350, 370], "note": "butt rear (X 0) to the trigger face along X"}
out["cheek_weld"] = {"sight_line_Z": float(socket("Sight")["M_mm"][2]), "stock_top_Z_at_cheek": 22.6,
                     "eye_over_comb_mm": round(float(socket("Sight")["M_mm"][2]) - 22.6, 1),
                     "note": "reported (B4b feeds on it)"}
out["real_world_sources"] = REAL_WORLD
out["pass_early"] = out["girth"]["pass"] and out["reach"]["pass"]
out["pass_all_rows"] = all(out[k]["pass"] for k in ("girth", "reach", "grip", "support"))
(SCRATCH / "h1_result.json").write_text(json.dumps(out, indent=1))
print("[H1]", json.dumps(out))
