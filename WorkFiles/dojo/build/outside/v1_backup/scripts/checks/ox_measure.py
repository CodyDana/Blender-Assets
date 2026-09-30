"""ROUND 5 OUTSIDE: measured numbers on the composed DojoOutside.blend (read only; nothing saved).

  ground_along_walls   the outside ground under a line 0.30 m and 1.00 m out from each wall face, every 0.5 m (rays down
                       on this track's ground / verge pieces): min / max z (spec 7: within 0.5 m of the courtyard level)
  street_section       z of every street surface on the gate axis (X 22) and at X 0, every 5 cm across Y
  apron_step           kit 1's front step top (+0.05) over the road surface in front of it (Y -3.05)
  alley_hulls          the UCX world boxes of SM_DKX_AlleyFence_W / _E beside the grey-box SM_DGB_AlleyFence hull boxes
  modern               world positions of the re-placed street lamps, poles, transformer and the drop's end point
Out: WorkFiles/dojo/build/outside/checks/measure_outside.json
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(bpy.data.filepath).resolve().parents[2]
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "outside" / "checks" / "measure_outside.json"
dg = bpy.context.evaluated_depsgraph_get()
asm = list(bpy.data.collections["Assembly"].objects)


def piece(o):
    return o.name.split("__")[0]


def bvh_of(objs):
    verts, polys = [], []
    for o in objs:
        me = o.data
        M = o.matrix_world
        base = len(verts)
        verts += [M @ v.co for v in me.vertices]
        polys += [[base + i for i in p.vertices] for p in me.polygons]
    return BVHTree.FromPolygons(verts, polys)


GROUND = ("SM_DKX_Verge", "SM_DKX_Ground_W", "SM_DKX_Ground_E", "SM_DKX_Ground_N")
g_bvh = bvh_of([o for o in asm if piece(o).startswith(GROUND)])
street = [o for o in asm if piece(o).startswith(("SM_DKX_Road", "SM_DKX_Verge", "SM_DKX_Kerb", "SM_DKX_Gutter",
                                                 "SM_DKX_FarVerge", "SM_DKX_Landing", "SM_DKX_Terrace",
                                                 "SM_DKX_Canal", "SM_DKX_Water", "SM_DKX_Ground_South"))]
s_bvh = bvh_of(street)
all_bvh = bvh_of(street + [o for o in asm if piece(o) == "SM_DK_Gate_Paving"])


def zdown(bvh, x, y, top=5.0):
    hit = bvh.ray_cast(Vector((x, y, top)), Vector((0, 0, -1)), 50.0)
    return None if hit[0] is None else round(hit[0].z, 4)


res = {"ground_along_walls": {}}
lines = {
    "south (Y -1.30 / -2.00)": [((x, -1.30), (x, -2.00)) for x in [k * 0.5 - 1.0 for k in range(93)]],
    "west (X -1.30 / -2.00)": [((-1.30, y), (-2.00, y)) for y in [k * 0.5 - 1.0 for k in range(77)]],
    "east (X 45.30 / 46.00)": [((45.30, y), (46.00, y)) for y in [k * 0.5 - 1.0 for k in range(77)]],
    "north (Y 37.30 / 38.00)": [((x, 37.30), (x, 38.00)) for x in [k * 0.5 - 1.0 for k in range(93)]],
}
worst = 0.0
for side, pts in lines.items():
    z30 = [zdown(g_bvh, *a) for a, _ in pts]
    z100 = [zdown(g_bvh, *b) for _, b in pts]
    z30 = [z for z in z30 if z is not None]
    z100 = [z for z in z100 if z is not None]
    res["ground_along_walls"][side] = {"samples": len(z30) + len(z100),
                                       "z_0.30m": [min(z30), max(z30)], "z_1.00m": [min(z100), max(z100)]}
    worst = max(worst, max(abs(z) for z in z30 + z100))
res["ground_along_walls"]["worst_abs_z_m"] = worst
res["ground_along_walls"]["spec_within_0.5m"] = worst <= 0.5
res["street_section"] = {}
for X in (22.0, 0.0):
    prof = []
    y = -0.9
    while y > -17.0:
        prof.append([round(y, 2), zdown(all_bvh if X == 22.0 else s_bvh, X, y)])
        y -= 0.05
    res["street_section"][f"X {X}"] = prof
step = zdown(all_bvh, 22.0, -2.75)
road = zdown(s_bvh, 22.0, -3.05)
res["apron_step"] = {"step_top": step, "road_at_Y-3.05": road, "rise_m": round(step - road, 4) if step and road else None}
res["kerb_near"] = {"verge_Y-2.20": zdown(s_bvh, 10.5, -2.20), "kerb_top_Y-2.40": zdown(s_bvh, 10.5, -2.40),
                    "gutter_lip_Y-2.52": zdown(s_bvh, 10.5, -2.52), "gutter_centre_Y-2.675": zdown(s_bvh, 10.5, -2.675),
                    "road_edge_Y-2.90": zdown(s_bvh, 10.5, -2.90), "road_crown_Y-5.30": zdown(s_bvh, 10.5, -5.30), "x": 10.5}
res["kerb_near"]["kerb_face_over_gutter_lip_m"] = round(res["kerb_near"]["kerb_top_Y-2.40"] -
                                                         res["kerb_near"]["gutter_lip_Y-2.52"], 4)
res["far_side"] = {"road_edge_Y-7.70": zdown(s_bvh, 0.5, -7.70), "kerb_top_Y-7.85": zdown(s_bvh, 0.5, -7.85),
                   "far_verge_Y-8.50": zdown(s_bvh, 0.5, -8.50), "coping_Y-9.35": zdown(s_bvh, 0.5, -9.35),
                   "canal_water_Y-10.5": zdown(s_bvh, 0.5, -10.5), "lower_lane_Y-14": zdown(s_bvh, 0.5, -14.0), "x": 0.5,
                   "landing_Y-8.5_at_X22": zdown(s_bvh, 22.0, -8.5)}
res["far_side"]["terrace_drop_to_water_m"] = round(res["far_side"]["coping_Y-9.35"] - res["far_side"]["canal_water_Y-10.5"], 3)
res["far_side"]["terrace_drop_to_lower_lane_m"] = round(res["far_side"]["coping_Y-9.35"] - res["far_side"]["lower_lane_Y-14"], 3)
kit = {o.name: o for o in bpy.data.collections["Kit"].objects}
hull = {}
for o in asm:
    p = piece(o)
    if p.startswith("SM_DKX_AlleyFence"):
        src = kit[p]
        for h in src.children:
            if h.name.startswith("UCX_"):
                pts = [o.matrix_world @ (h.matrix_local @ Vector(c)) for c in h.bound_box]
                hull[o.name] = [round(min(q[i] for q in pts), 4) for i in range(3)] + \
                               [round(max(q[i] for q in pts), 4) for i in range(3)]
res["alley_hulls"] = hull
res["alley_greybox_hulls"] = {"W": [10.5, 34.0, 0.0, 13.0, 34.1, 2.0], "E": [31.0, 34.0, 0.0, 33.5, 34.1, 2.0]}
res["alley_hulls_match_greybox"] = sorted(hull.values()) == sorted(res["alley_greybox_hulls"].values())
mod = {}
for o in asm:
    p = piece(o)
    if p in ("SM_DKP_Modern_StreetLamp_A", "SM_DKP_Modern_StreetLamp_B", "SM_DKP_Modern_UtilityPole",
             "SM_DKP_Modern_PoleTransformer", "SM_DKP_Modern_PoleGuy"):
        mod.setdefault(p, []).append([round(v, 3) for v in o.matrix_world.translation] +
                                     [round(math.degrees(o.matrix_world.to_euler().z), 2)])
    if p == "SM_DKP_Modern_Wire_Drop12":
        M = o.matrix_world
        mod["Wire_Drop12_start_end"] = [[round(v, 3) for v in M.translation],
                                        [round(v, 3) for v in (M @ Vector((12.0, 0.0, -3.0)))]]
res["modern"] = mod
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print("MEASURE", json.dumps({k: v for k, v in res.items() if k not in ("street_section",)})[:3000])
