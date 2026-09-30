"""KIT 1 measurements for the f1 / f2 fix rounds (every number in BUILD_NOTES comes from here), on Assets/Dojo/DojoKit1.blend.

 cap_float      wall cap: drop from the flat walk plane (collision top) to the visual tiles, cast straight down at the
                wall faces, 0.3 m in (a capsule centre at the strip edge) and the centre line, every 5 mm along 4 m
 noshi_slits    horizontal rays across the ridge's noshi band every 1 mm along the 4 m cap: any ray that passes the
                noshi band without hitting it is a see-through slit
 gate_leaves    each leaf against the frame, roof, paving and step piers: triangle overlaps (BVH) closed, open and at
                every 5 deg of the swing; the leaf's local x range (must stay >= 0 / <= 0), its bottom vs the threshold
                top under it, the open leaves' inner faces (the clear passage width)
 headroom       the lowest roof / frame timber over the gate passage (rays up on a 5 cm grid, x -2..2, y -2.6..2.6)
 gate_roof      where the slope planes meet, the ridge roll top, the ridge-end tile top; the visual tiles vs the flat
                slope planes (sag / upturn) on the N slope
 walls          the wall top (cap collision top) for each variant; the step piers' walk tops
 nanite         the layout's nanite flag vs the triangle count (STYLE_GUIDE 7: every opaque static piece over ~2k)

Run: blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/measure_kit1.py
Out: WorkFiles/dojo/build/kit1/measure_kit1_f2.json
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(bpy.data.filepath).resolve().parents[2]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
L = json.loads((WORK / "layout.json").read_text(encoding="utf-8"))
K = L["kit1"]
KIT = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}
OUT = {}


def bvh_of(name, M=Matrix()):
    o = KIT[name]
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.transform(M)
    t = BVHTree.FromBMesh(bm)
    verts = [v.co.copy() for v in bm.verts]
    bm.free()
    return t, verts


def hull_top(name):
    return max(max((h.matrix_local @ Vector(c)).z for c in h.bound_box) for h in KIT[name].children
               if h.name.startswith("UCX_"))


# ------------------------------------------------------------------------------------------------ cap float
cap_top = hull_top("SM_DK_WallCap_4m")
t, _ = bvh_of("SM_DK_WallCap_4m")
rows = {}
for label, y in (("inner_face_y0", -0.001), ("capsule_0.3_in", -0.30), ("centre", -0.50), ("capsule_0.3_in_outer", -0.70),
                 ("outer_face_y-1", -0.999)):
    drops = []
    for i in range(801):
        x = 0.0 + 4.0 * i / 800
        hit = t.ray_cast(Vector((x, y, cap_top + 0.5)), Vector((0, 0, -1)), 2.0)
        if hit[0] is not None:
            drops.append(cap_top - hit[0].z)
    rows[label] = {"min_m": round(min(drops), 4), "max_m": round(max(drops), 4),
                   "mean_m": round(sum(drops) / len(drops), 4)}
OUT["cap_float"] = {"walk_plane_z_local": round(cap_top, 4), "rows": rows,
                    "note": "positive = the tiles are below the walk plane (feet float); negative = the tiles stand above "
                            "it (feet sink)"}

# ------------------------------------------------------------------------------------------------ noshi slits
slits = {}
for cap in ("SM_DK_WallCap_1m", "SM_DK_WallCap_2m", "SM_DK_WallCap_4m", "SM_DK_WallCap_End"):
    t, verts = bvh_of(cap)
    Lc = {"SM_DK_WallCap_1m": 1.0, "SM_DK_WallCap_2m": 2.0, "SM_DK_WallCap_4m": 4.0, "SM_DK_WallCap_End": 1.0}[cap]
    n0 = L["pieces"][cap]  # noqa: F841
    # the noshi band: the layout does not carry it, so find it from the tile field: between the ridge bed top and the
    # ridge roll's lowest point, sampled at 3 heights inside the two layers
    # (z, ray start y just outside that layer's near face, "passed the face" threshold); layer faces: -0.35 / -0.37
    # f2: one height per noshi layer (layer widths from the build: 0.36 / 0.32 / 0.28 m), the ray starting 8 mm
    # outside that layer's +y face
    z0n, hn = K["cap_noshi0_m"], K["cap_noshi_h_m"]
    widths = K.get("cap_noshi_widths_m", [0.36, 0.32, 0.28])[:K.get("cap_noshi_layers", 2)]   # r2f: from the build
    zs = [(z0n + li * hn + hn / 2, -0.5 + w / 2 + 0.008, -0.5 + w / 2 - 0.012) for li, w in enumerate(widths)]
    count, rays = 0, 0
    for (z, y0, thr) in zs:
        for i in range(int(Lc * 1000) - 20):
            x = 0.010 + i / 1000.0
            rays += 1
            hit = t.ray_cast(Vector((x, y0, z)), Vector((0, -1, 0)), 0.90)
            if hit[0] is None or hit[0].y < thr:
                count += 1
    slits[cap] = {"rays": rays, "see_through": count}
# f1: the same rays across the joint BETWEEN pieces (two 1 m caps end to end at x = 1; a corner cap whose x-leg
# meets a 1 m cap at x = 0), every 0.5 mm over +-10 mm around the joint
def _joint(parts, xj):
    verts, polys = [], []
    for nm, M in parts:
        bm = bmesh.new()
        bm.from_mesh(KIT[nm].data)
        bm.transform(M)
        base = len(verts)
        verts += [v.co.copy() for v in bm.verts]
        polys += [[base + v.index for v in f.verts] for f in bm.faces]
        bm.free()
    t = BVHTree.FromPolygons(verts, polys, epsilon=0.0)
    n, bad = 0, 0
    for (z, y0, thr) in zs:
        for i in range(41):
            x = xj - 0.010 + i * 0.0005
            n += 1
            hit = t.ray_cast(Vector((x, y0, z)), Vector((0, -1, 0)), 0.90)
            if hit[0] is None or hit[0].y < thr:
                bad += 1
    return {"rays": n, "see_through": bad}


slits["joint_1m_to_1m"] = _joint([("SM_DK_WallCap_1m", Matrix()), ("SM_DK_WallCap_1m", Matrix.Translation((1, 0, 0)))], 1.0)
slits["joint_corner_to_1m"] = _joint([("SM_DK_WallCap_Corner", Matrix()), ("SM_DK_WallCap_1m", Matrix())], 0.0)
OUT["noshi_slits"] = slits

# ------------------------------------------------------------------------------------------------ gate leaves
GXw = 22.0
frame_names = ["SM_DK_Gate_Frame", "SM_DK_Gate_Roof", "SM_DK_Gate_Paving"]
others = []
for nm in frame_names:
    others.append((nm, bvh_of(nm, Matrix.Translation((GXw, 0, 0)))[0]))
# f2: the wall joins (the wall's last 0.5 m into the post clusters) and the route-6 eave stands
WINGS = {"SM_DK_Wall_GateJoin_W": ("SM_DK_Wall_GateJoin", (18.0, 0.0, 0.0), 0.0),
         "SM_DK_Wall_GateJoin_E": ("SM_DK_Wall_GateJoin", (26.0, -1.0, 0.0), 180.0)}
if K.get("gate_stands") and "SM_DK_Gate_Stand" in KIT:        # r2: the stands are removed
    WINGS["SM_DK_Gate_Stand_W"] = ("SM_DK_Gate_Stand", tuple(K["gate_stands"]["pivots"][0]), 0.0)
    WINGS["SM_DK_Gate_Stand_E"] = ("SM_DK_Gate_Stand", tuple(K["gate_stands"]["pivots"][1]), 0.0)
for key, (nm, loc, rot) in WINGS.items():
    others.append((key, bvh_of(nm, Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rot), 4, "Z"))[0]))
leaf_rep = {}
for side, it in (("L", K["gate_leaf_placements"]["closed"][0]), ("R", K["gate_leaf_placements"]["closed"][1])):
    name = it["piece"]
    o = KIT[name]
    xs = [v.co.x for v in o.data.vertices]
    zs_ = [v.co.z for v in o.data.vertices]
    ys = [v.co.y for v in o.data.vertices]
    rec = {"local_x_range": [round(min(xs), 4), round(max(xs), 4)], "local_y_range": [round(min(ys), 4), round(max(ys), 4)],
           "local_z_range": [round(min(zs_), 4), round(max(zs_), 4)]}
    sweep = {}
    sgn = 1 if side == "L" else -1
    for ang in list(range(0, 91, 5)):
        M = Matrix.Translation(it["loc"]) @ Matrix.Rotation(math.radians(sgn * ang), 4, "Z")
        lt, lv = bvh_of(name, M)
        hits = {}
        for nm, ot in others:
            ov = lt.overlap(ot)
            if ov:
                hits[nm] = hits.get(nm, 0) + len(ov)
        sweep[str(ang)] = hits
        if ang == 90:
            xs_w = [v.x for v in lv]
            rec["open_x_range_world"] = [round(min(xs_w), 4), round(max(xs_w), 4)]
            rec["open_y_range_world"] = [round(min(v.y for v in lv), 4), round(max(v.y for v in lv), 4)]
        if ang == 0:
            # the leaf bottom vs the paving right under it: rays up from below the paving at the leaf's footprint
            pt, _ = [x for x in others if x[0] == "SM_DK_Gate_Paving"][0][1], None
            bottom = min(v.z for v in lv)
            top_under = -1.0
            for i in range(60):
                for j in range(6):
                    xw = min(v.x for v in lv) + (max(v.x for v in lv) - min(v.x for v in lv)) * i / 59
                    yw = min(v.y for v in lv) + (max(v.y for v in lv) - min(v.y for v in lv)) * j / 5
                    h = pt.ray_cast(Vector((xw, yw, 1.0)), Vector((0, 0, -1)), 2.0)
                    if h[0] is not None:
                        top_under = max(top_under, h[0].z)
            rec["closed_bottom_z"] = round(bottom, 4)
            rec["paving_top_under_closed_leaf"] = round(top_under, 4)
            rec["closed_bottom_clearance_m"] = round(bottom - top_under, 4)
    rec["overlaps_by_angle"] = sweep
    rec["clear_all_angles"] = all(not v for v in sweep.values())
    leaf_rep[side] = rec
leaf_rep["open_clear_width_m"] = round(leaf_rep["R"]["open_x_range_world"][0] - leaf_rep["L"]["open_x_range_world"][1], 4)
OUT["gate_leaves"] = leaf_rep

# ------------------------------------------------------------------------------------------------ headroom
over = [o for o in others if o[0] in ("SM_DK_Gate_Frame", "SM_DK_Gate_Roof")]
low = (9.0, None)
for i in range(81):
    for j in range(105):
        x = GXw - 2.0 + 4.0 * i / 80
        y = -2.6 + 5.2 * j / 104
        for nm, ot in over:
            h = ot.ray_cast(Vector((x, y, 0.3)), Vector((0, 0, 1)), 6.0)
            if h[0] is not None and h[0].z < low[0]:
                low = (h[0].z, [round(x, 3), round(y, 3), nm])
OUT["headroom"] = {"lowest_timber_z": round(low[0], 4), "at": low[1],
                   "note": "floor +0.00 .. +0.10 under the passage; R5 needs 2.5 m"}

# ------------------------------------------------------------------------------------------------ gate roof
rt, _ = bvh_of("SM_DK_Gate_Roof")
diffs = []
for i in range(41):
    for j in range(21):
        x = -3.7 + 7.4 * i / 40
        y = 0.40 + 1.9 * j / 20
        h = rt.ray_cast(Vector((x, y, 6.0)), Vector((0, 0, -1)), 4.0)
        if h[0] is not None:
            plane = 3.25 + (2.5 - y) * math.tan(math.radians(25.0))
            diffs.append((h[0].z - plane, round(x, 3), round(y, 3)))
diffs.sort()
print("ROOF_DIFF_EXTREMES", diffs[:3], diffs[-6:])
diffs = [d[0] for d in diffs]
ext = L["pieces"]["SM_DK_Gate_Roof"].get("extra", {})
OUT["gate_roof"] = {"planes_meet_z": ext.get("planes_meet"), "ridge_roll_top_z": ext.get("ridge_roll_top"),
                    "ridge_end_top_z": ext.get("ridge_end_top"), "ridge_stack_hull_top": round(hull_top("SM_DK_Gate_Roof"), 4),
                    "N_slope_visual_minus_plane_m": {"min": round(min(diffs), 4), "max": round(max(diffs), 4)}}

# ------------------------------------------------------------------------------------------------ walls, piers
walls = {}
for key, zb in K["body_top_z"].items():
    walls[key] = round(zb + hull_top("SM_DK_WallCap_4m"), 4)
OUT["walls"] = {"wall_top_by_variant": walls, "cap_collision_h": round(hull_top("SM_DK_WallCap_4m"), 4),
                "footing_h": K["footing_h"]}
# r2 (the judge: stones poked past the end face): every footing piece's stones stay inside its module in the run
# direction and within 5 cm of the wall faces; the end / corner faces carry flush quoins
foot = {}
for nm, (x0, x1, y0, y1) in (("SM_DK_WallFooting_1m", (0, 1, -1, 0)), ("SM_DK_WallFooting_2m", (0, 2, -1, 0)),
                             ("SM_DK_WallFooting_4m", (0, 4, -1, 0)), ("SM_DK_WallFooting_End", (0, 1, -1, 0)),
                             ("SM_DK_WallFooting_Corner", (-1, 0, -1, 0)), ("SM_DK_Wall_GateJoin", (0, 0.49, -1, 0))):
    vs = [v.co for v in KIT[nm].data.vertices if v.co.z < K["footing_h"] + 0.01]
    foot[nm] = {"x_min_minus_module": round(min(v.x for v in vs) - x0, 4), "x_max_minus_module": round(max(v.x for v in vs) - x1, 4),
                "proud_outer_face_m": round(y0 - min(v.y for v in vs), 4), "proud_inner_face_m": round(max(v.y for v in vs) - y1, 4)}
OUT["footing_extents"] = foot
# f2: the joins and stands against the gatehouse (visual triangles): must not interpenetrate the roof / frame / paving
wing_ov = {}
for key in WINGS:
    wt = [o for o in others if o[0] == key][0][1]
    wing_ov[key] = {on: len(wt.overlap(ot)) for on, ot in others
                    if on in ("SM_DK_Gate_Frame", "SM_DK_Gate_Roof", "SM_DK_Gate_Paving")}
OUT["gate_wings_vs_gatehouse_tri_pairs"] = wing_ov

# ------------------------------------------------------------------------------------------------ f2: roof faces
# rays straight down over the roof footprint (the plan view / a camera above) and straight up from under the eaves
# (a player below): every first hit must be a FRONT face (normal against the ray); a back face there would vanish
# under backface culling in Unreal (the judge's missing-roof plan view)
ro = KIT["SM_DK_Gate_Roof"]
bm = bmesh.new()
bm.from_mesh(ro.data)
rbvh = BVHTree.FromBMesh(bm)
bm.free()
face_rep = {}
for label, z0, d in (("from_above", 7.0, Vector((0, 0, -1))), ("from_below", 2.6, Vector((0, 0, 1)))):
    n_hit = n_back = 0
    for i in range(161):
        for j in range(101):
            x = -4.1 + 8.2 * i / 160
            y = -2.6 + 5.2 * j / 100
            h = rbvh.ray_cast(Vector((x, y, z0)), d, 6.0)
            if h[0] is None:
                continue
            n_hit += 1
            if h[1].dot(d) > 0:
                n_back += 1
    face_rep[label] = {"rays": 161 * 101, "hits": n_hit, "back_face_hits": n_back}
OUT["gate_roof_faces"] = face_rep

# ------------------------------------------------------------------------------------------------ nanite
nan = {}
for nm, pc in L["pieces"].items():
    if pc.get("kit") != "kit1":
        continue
    nan[nm] = {"tris": pc["tris"], "nanite": pc["nanite"], "ok": pc["nanite"] or pc["tris"] < 2000}
OUT["nanite"] = {"all_ok": all(v["ok"] for v in nan.values()), "pieces": nan}

(WORK / "kit1" / "measure_kit1_r2.json").write_text(json.dumps(OUT, indent=1), encoding="utf-8")
print("MEASURE", json.dumps({k: v for k, v in OUT.items() if k != "nanite"}, indent=1))
print("NANITE_OK", OUT["nanite"]["all_ok"])
