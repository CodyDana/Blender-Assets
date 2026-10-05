"""AR-01 gate H1, EARLY form (RIFLE_BUILD_PLAN 12 stage 2): measurement-based checks of the grip against the locked
MH_PlayerDefault fit body's right hand. The full H1 (the posed hand on SK_AR01, penetration, two-bone IK) runs at the
rig stage; this one measures what the form must already satisfy:

  girth    perimeter of the grip section perpendicular to its axis at the Grip origin, vs the power-grasp optimum
           (handle diameter ~19.7 % of hand length, Kong & Lowe 2005), accepted band +-15 %
  reach    trigger reach (back strap at the web line -> trigger face, along the bore direction) vs the hand's
           web -> index DIP and web -> index distal-pad distances
  grip40   the provisional 40 mm (junction -> palm centre down the grip axis) vs the hand: web line to palm centre
  support  SupportHand lies on the lower handguard's underside (ray hit) and is reachable (hand separation vs arm)

    blender -b References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend --factory-startup \
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
d_opt = 0.197 * hand_len
c_opt = math.pi * d_opt
out["girth"] = {"section_at": "Grip origin, perpendicular to the grip axis (22.35 deg)",
                "perimeter_mm": round(perim, 1), "section_extent_mm": np.round(np.ptp(pts, axis=0), 1).tolist(),
                "optimum_perimeter_mm": round(c_opt, 1), "band_mm": [round(0.85 * c_opt, 1), round(1.15 * c_opt, 1)],
                "pass": 0.85 * c_opt <= perim <= 1.15 * c_opt}

# reach: from the back strap at the trigger-face height to the trigger face, along X
Vg, Tg = tris(G["pistol_grip"])
tz = SPEC.d["sockets"]["rifle"][2]["M_mm"]                        # Trigger socket (321.3, 0, -46.0)
trig_face = np.array(tz)
zline = trig_face[2]
sel = np.abs(Vg[:, 2] - zline) < 1.2
back_x = float(Vg[sel, 0].min())
reach = float(trig_face[0] - back_x)
out["reach"] = {"back_strap_X_at_trigger_height": round(back_x, 2), "trigger_face_X": trig_face[0],
                "reach_mm": round(reach, 1), "hand_web_to_DIP_mm": round(L_web_dip, 1),
                "hand_web_to_pad_mm": round(L_web_pad, 1),
                "rule": "reach between web->DIP - 8 mm and web->pad + 5 mm (pad on the face, DIP not past it)",
                "pass": (L_web_dip - 8.0) <= reach <= (L_web_pad + 5.0)}

# grip 40: junction (web line) -> palm centre
out["grip40"] = {"provisional_mm": 40.0, "hand_web_to_palm_centre_mm": round(L_web_palmc, 1),
                 "suggested_mm": round(L_web_palmc, 1),
                 "pass_within_10mm": abs(L_web_palmc - 40.0) <= 10.0,
                 "note": "early estimate from bone positions; the posed H1 sets the final value and hand_offset"}

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
out["pass_early"] = all(out[k]["pass"] for k in ("girth", "reach", "support")) and out["grip40"]["pass_within_10mm"]
(SCRATCH / "h1_result.json").write_text(json.dumps(out, indent=1))
print("[H1]", json.dumps(out))
