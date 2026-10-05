"""AR-01 gate H1, EARLY form (RIFLE_BUILD_PLAN 12 stage 2): measurement-based checks of the grip against the locked
MH_PlayerDefault fit body's right hand and against DOCUMENTED real-world numbers (form fix round 1 replaced the
round-0 proxy bands; sources in REAL_WORLD below). The full H1 (the posed hand on SK_AR01, penetration, two-bone IK)
runs at the rig stage; this one measures what the form must already satisfy:

  girth    perimeter and Y width of the grip section perpendicular to its axis at the Grip origin, against real AK
           grips: width 30 mm (IMI Defense AK47/AK74 grip) to 36 mm (FAB Defense Gradus AK grip); with the measured
           front-back depth and the spec's strap radii R 8-10 those widths give the girth band
  reach    trigger reach = back strap at the web (the hollow under the tang, deepest point Z -40..-60) -> trigger face,
           against documented reaches: AR-15 2.25 in = 57.2 mm, Glock 17 trigger distance 72 mm. The trigger position
           comes from the sheet and is NOT moved to meet a band; a miss is reported
  grip     the Grip origin depth down the axis (spec, set from this hand: palm centre projected on the index->pinky
           knuckle line from the web) vs the hand estimate (|diff| <= 1 mm); the 55 mm Euclidean web->palm-centre
           distance is reported too
  support  SupportHand lies on the lower handguard's underside (ray hit) and is reachable (hand separation vs arm)

    blender -b References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend --factory-startup
        --python Scripts/guns/rifle/rifle_h1.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SPEC, GRIP, BLEND, SCRATCH  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

LOCK = json.loads((ROOT / "References" / "Characters" / "MH_PlayerDefault" / "base_lock.json").read_text())
out = {"body": "References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend",
       "body_sha256_locked": LOCK.get("blend_sha256"), "mode": "early (measurement-based); posed H1 at the rig stage"}

import hashlib  # noqa: E402
blend_path = ROOT / out["body"]
out["body_sha256_now"] = hashlib.sha256(blend_path.read_bytes()).hexdigest()
out["body_sha256_matches_lock"] = out["body_sha256_now"] == out["body_sha256_locked"]

arm = bpy.data.objects["root"]
Mw = arm.matrix_world


def head(n):
    return np.array(Mw @ arm.data.bones[n].head_local) * 1000.0


def tail(n):
    return np.array(Mw @ arm.data.bones[n].tail_local) * 1000.0


wrist = head("hand_r")
mid_tip = tail("middle_03_r")
hand_len = float(np.linalg.norm(mid_tip - wrist))
palm_len = float(np.linalg.norm(head("middle_01_r") - wrist))
idx_mcp, idx_pip, idx_dip, idx_tip = head("index_01_r"), head("index_02_r"), head("index_03_r"), tail("index_03_r")
thumb_cmc = head("thumb_01_r")
thumb_mcp = head("thumb_02_r")
# web (thumb-index crotch) ~ midway between the thumb MCP and the index MCP, on the palm side
web = 0.5 * (idx_mcp + thumb_mcp)
L_web_dip = float(np.linalg.norm(idx_dip - web))
L_web_pad = float(np.linalg.norm(0.5 * (idx_dip + idx_tip) - web))
palm_centre = 0.5 * (wrist + 0.5 * (head("index_01_r") + head("pinky_01_r")))
L_web_palmc = float(np.linalg.norm(palm_centre - web))
arm_len = float(np.linalg.norm(head("lowerarm_r") - head("upperarm_r")) + np.linalg.norm(wrist - head("lowerarm_r")))
out["hand"] = {"hand_length_mm": round(hand_len, 1), "palm_length_mm": round(palm_len, 1),
               "web_to_index_DIP_mm": round(L_web_dip, 1), "web_to_index_pad_mm": round(L_web_pad, 1),
               "web_to_palm_centre_mm": round(L_web_palmc, 1), "upper+lower arm_mm": round(arm_len, 1)}

# ---- the gun parts we need, appended from Assets/Guns/AR01.blend
with bpy.data.libraries.load(str(BLEND), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n in ("pistol_grip", "trigger", "lower_handguard", "receiver",
                                                     "trigger_guard")]
for o in dst.objects:
    bpy.context.scene.collection.objects.link(o)
G = {o.name: o for o in dst.objects}


def tris(o):
    me = o.data
    me.calc_loop_triangles()
    V = np.array([v.co for v in me.vertices]) * 1000.0 + GRIP      # frame M, mm
    T = np.array([t.vertices[:] for t in me.loop_triangles])
    return V, T


REAL_WORLD = {
    "grip_width_mm": {"min": 30.0, "max": 36.0, "sources": [
        {"what": "IMI Defense AK47/AK74 EG polymer pistol grip", "value": "Width: 3 cm (Length 6 cm, Height 11 cm)",
         "url": "https://imidefense.com/product/ak47-ak74-eg-polymer-pistol-grip/"},
        {"what": "FAB Defense GRADUS AK ergonomic pistol grip", "value": "36 mm (W) x 114 mm (H)",
         "url": "https://platatac.com/products/f-a-b-gradus-ak-ergonomic-pistol-grip"}]},
    "trigger_reach_mm": {"min": 57.2, "max": 72.0, "sources": [
        {"what": "AR-15 standard grip", "value": "basic trigger length 2.25 in (57.2 mm)",
         "url": "https://www.bluesheepdog.com/2015/03/18/new-accu-grip-ar-15-pistol-grip/"},
        {"what": "Glock 17 (full-size service pistol, manufacturer spec)", "value": "Trigger Distance 72 mm | 2.83 inch",
         "url": "https://us.glock.com/en/products/law-enforcement/pistols/g17"}]},
    "strap_radius_mm": {"min": 8.0, "max": 10.0, "source": "rifle_spec pistol_grip.construction (straps R 8-10)"},
}


def rounded_oblong_perimeter(D, W, R):
    return 2 * (D + W) - (8 - 2 * math.pi) * R


# girth: section of the grip perpendicular to its axis at the Grip origin (M), via bmesh bisect
ang = math.radians(SPEC.dims("pistol_grip")["axis_rake_deg_from_vertical"])
axis = np.array([-math.sin(ang), 0.0, -math.cos(ang)])          # down the grip
origin = np.array(SPEC.d["frames"]["B"]["Grip_in_M"])
bm = bmesh.new()
bm.from_mesh(G["pistol_grip"].data)
co = (origin - GRIP) / 1000.0
res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-7,
                             plane_co=Vector(co), plane_no=Vector(axis), clear_inner=False, clear_outer=False)
cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
perim = sum(e.calc_length() for e in cut_edges) * 1000.0
pts = np.array([v.co for v in res["geom_cut"] if isinstance(v, bmesh.types.BMVert)]) * 1000.0
bm.free()
pdir = np.array([math.cos(ang), 0.0, -math.sin(ang)])          # front-back direction in the section plane
depth = float(np.ptp(pts @ pdir))
width = float(np.ptp(pts[:, 1]))
band = [round(rounded_oblong_perimeter(depth, REAL_WORLD["grip_width_mm"]["min"], REAL_WORLD["strap_radius_mm"]["max"]), 1),
        round(rounded_oblong_perimeter(depth, REAL_WORLD["grip_width_mm"]["max"], REAL_WORLD["strap_radius_mm"]["min"]), 1)]
d_opt = 0.197 * hand_len
out["girth"] = {"section_at": "Grip origin, perpendicular to the grip axis (22.35 deg)",
                "perimeter_mm": round(perim, 1), "width_Y_mm": round(width, 2), "depth_mm": round(depth, 2),
                "real_world_width_band_mm": [REAL_WORLD["grip_width_mm"]["min"], REAL_WORLD["grip_width_mm"]["max"]],
                "girth_band_mm": band,
                "band_rule": "rounded oblong of the measured depth: width 30 / straps R 10 (min) .. width 36 / straps R 8 "
                             "(max); +2 mm allowance above the band for the 0.6 mm checker-panel recess walls; width "
                             "+-0.25 mm for tessellation and bevels",
                "kong_lowe_cylinder_optimum_mm_info": round(math.pi * d_opt, 1),
                "width_tolerance_mm": 0.25,
                "pass": (REAL_WORLD["grip_width_mm"]["min"] - 0.25 <= width <= REAL_WORLD["grip_width_mm"]["max"] + 0.25)
                        and band[0] <= perim <= band[1] + 2.0}

# reach: back strap at the web (deepest point of the hollow under the tang) -> trigger face
Vg, Tg = tris(G["pistol_grip"])
trig_face = np.array([s for s in SPEC.d["sockets"]["rifle"] if s["socket"] == "Trigger"][0]["M_mm"])
near_mid = np.abs(Vg[:, 1]) < 1.5
best = None
for zz in np.arange(-40.0, -60.01, -0.5):
    sel = near_mid & (np.abs(Vg[:, 2] - zz) < 0.6) & (Vg[:, 0] < 275.0)        # back strap only
    if sel.any():
        xb = float(Vg[sel, 0].min())
        if best is None or xb > best[0]:
            best = (xb, zz)
web_pt = np.array([best[0], 0.0, best[1]])
reach = float(np.linalg.norm(trig_face - web_pt))
sel_t = near_mid & (np.abs(Vg[:, 2] - trig_face[2]) < 1.2)
reach_x = float(trig_face[0] - Vg[sel_t, 0].min())
out["reach"] = {"web_point_M": np.round(web_pt, 2).tolist(), "trigger_face_M": trig_face.tolist(),
                "reach_mm": round(reach, 1), "reach_at_trigger_height_along_X_mm_round0_definition": round(reach_x, 1),
                "real_world_band_mm": [REAL_WORLD["trigger_reach_mm"]["min"], REAL_WORLD["trigger_reach_mm"]["max"]],
                "hand_web_to_DIP_mm": round(L_web_dip, 1), "hand_web_to_pad_mm": round(L_web_pad, 1),
                "rule": "web hollow -> trigger face within the documented 57.2-72.0 mm (AR-15 .. Glock 17); trigger NOT moved",
                "pass": REAL_WORLD["trigger_reach_mm"]["min"] <= reach <= REAL_WORLD["trigger_reach_mm"]["max"]}

# Grip origin depth: palm centre projected on the index->pinky knuckle line from the web
i1, p1 = head("index_01_r"), head("pinky_01_r")
u_k = (p1 - i1) / np.linalg.norm(p1 - i1)
along = float((palm_centre - web) @ u_k)
junction = np.array(SPEC.dims("pistol_grip")["junction_M"])
gz = SPEC.d["frames"]["B"]["Grip_in_M"]
depth_spec = float(np.hypot(gz[0] - junction[0], gz[2] - junction[1]))
out["grip"] = {"spec_Grip_depth_mm": round(depth_spec, 2), "hand_palm_centre_along_knuckle_line_mm": round(along, 1),
               "hand_web_to_palm_centre_euclid_mm": round(L_web_palmc, 1),
               "palm_offset_behind_axis_mm": round(math.sqrt(max(L_web_palmc ** 2 - along ** 2, 0)), 1),
               "history": "40 mm provisional (study 5.1) -> set from this hand in form fix round 1",
               "pass": abs(depth_spec - along) <= 1.0}

# support hand: ray up from below at the socket X,Y must hit the lower handguard underside at the socket Z
Vh, Th = tris(G["lower_handguard"])
tree = BVHTree.FromPolygons([tuple(v) for v in Vh], [tuple(t) for t in Th], all_triangles=True)
sh = np.array([s for s in SPEC.d["sockets"]["rifle"] if s["socket"] == "SupportHand"][0]["M_mm"])
hit = tree.ray_cast(Vector((sh[0], sh[1], sh[2] - 50.0)), Vector((0, 0, 1)))
hz = None if hit[0] is None else float(hit[0][2])
sep = float(np.linalg.norm(sh - origin))
out["support"] = {"SupportHand_M": sh.tolist(), "underside_hit_Z": None if hz is None else round(hz, 2),
                  "offset_from_surface_mm": None if hz is None else round(sh[2] - hz, 2),
                  "hand_separation_mm": round(sep, 1), "arm_length_mm": round(arm_len, 1),
                  "pass": hz is not None and abs(sh[2] - hz) <= 1.5 and sep < 1.6 * arm_len}
out["real_world_sources"] = REAL_WORLD
out["pass_early"] = all(out[k]["pass"] for k in ("girth", "reach", "grip", "support"))
(SCRATCH / "h1_result.json").write_text(json.dumps(out, indent=1))
print("[H1]", json.dumps(out))
