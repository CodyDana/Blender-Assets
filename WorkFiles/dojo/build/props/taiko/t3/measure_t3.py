"""t3 (2026-10-03, adapted from t2/measure_t2.py: 24-sided true domes, rows 40 mm apart, X_TACK 0.678, the
rolled tabs, the cradle beams at x 0.435-0.555). Measure the taiko on the EXPORTED FBX (LOD0), in a fresh headless Blender: the tacks (rounded
14-sided caps on the hide atlas), the pale-hide spacing above / below the band, the flap tabs, and the drum seated in the
stand's felt-lined saddles (drum FBX placed at the layout's DRUM_Z over the stand FBX)."""
import json
import math
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
FBX = ROOT / "Exports" / "DojoKit" / "Props" / "taiko" / "SM_DKP_Taiko_Drum.fbx"
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko" / "t3" / "measure_t3.json"
STAND_FBX = ROOT / "Exports" / "DojoKit" / "Props" / "taiko" / "SM_DKP_Taiko_Stand.fbx"
DRUM_Z = 1.25
X_TACK = 0.678
SINK = 0.0025
SIDES = 24
NRING = 5          # t3: pole + 4 profile rings (the last, r = R at z = 0, is the widest) + the sunk skirt ring

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(FBX))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.name.startswith("UCX")]
print("meshes", [o.name for o in meshes])
lod0 = next(o for o in meshes if "LOD0" in o.name)
M = lod0.matrix_world
me = lod0.data
P0 = [M @ v.co for v in me.vertices]
L = max(abs(p.x) for p in P0) - min(p.x for p in P0) if False else (max(p.x for p in P0) - min(p.x for p in P0))
ext = [max(p[i] for p in P0) - min(p[i] for p in P0) for i in range(3)]
ax = max(range(3), key=lambda i: ext[i])          # the drum axis = the longest extent
scale = 1.554 / ext[ax]
others = [i for i in range(3) if i != ax]
cen = [(max(p[i] for p in P0) + min(p[i] for p in P0)) / 2 for i in range(3)]
# canonical frame: x along the drum axis, (y, z) across, metres, centred
P = [Vector(((p[ax] - cen[ax]) * scale, (p[others[0]] - cen[others[0]]) * scale,
             (p[others[1]] - cen[others[1]]) * scale)) for p in P0]
print("extent", ext, "axis", ax, "scale", scale)

bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
iron_idx = {i for i, m in enumerate(me.materials) if m and m.name.startswith("M_DKP_Taiko_Hide") and "Collar" not in m.name}   # t2: tacks on the hide atlas
seen, islands = set(), []
for f in bm.faces:
    if f.material_index not in iron_idx or f.index in seen:
        continue
    stack, isl = [f], []
    seen.add(f.index)
    while stack:
        c = stack.pop()
        isl.append(c)
        for e in c.edges:
            for g in e.link_faces:
                if g.index not in seen and g.material_index in iron_idx:
                    seen.add(g.index)
                    stack.append(g)
    islands.append(isl)
tacks = []
for isl in islands:
    vs = {v.index for f in isl for v in f.verts}
    if len(vs) != 1 + NRING * SIDES:
        continue
    vlist = [bm.verts[i] for i in vs]
    pole = [v for v in vlist if len(v.link_edges) == SIDES]
    if len(pole) != 1:
        continue
    pole = pole[0]
    depth = {pole.index: 0}
    front = [pole]
    while front:
        nxt = []
        for v in front:
            for e in v.link_edges:
                o = e.other_vert(v)
                if o.index not in depth and o.index in vs:
                    depth[o.index] = depth[v.index] + 1
                    nxt.append(o)
        front = nxt
    base = [P[i] for i, d_ in depth.items() if d_ == NRING]          # the sunk skirt ring
    ring1 = [P[i] for i, d_ in depth.items() if d_ == NRING - 1]     # t3: the widest ring, at the hide (silhouette)
    cb = sum(base, Vector()) / len(base)
    cs = sum(ring1, Vector()) / len(ring1)
    n = (cs - cb).normalized()
    apex = P[pole.index]
    tacks.append({"cb": cb, "n": n, "apex": apex, "base": base, "ring1": ring1,
                  "base_r": [((q - cb) - n * (q - cb).dot(n)).length for q in base], "h": (apex - cb).dot(n)})
print("tack islands", len(tacks), "of", len(islands), "iron islands")

fv = [[v.index for v in f.verts] for f in bm.faces if f.material_index not in iron_idx]
bvh = BVHTree.FromPolygons(P, fv)


def signed_dist(p):
    loc, _n, _i, d = bvh.find_nearest(p)
    radial = Vector((0, p.y, p.z)).normalized()
    return d if (p - loc).dot(radial) >= 0 else -d


rows = defaultdict(list)
for t in tacks:
    seat = t["cb"] + t["n"] * SINK
    t.update(seat=seat, x=abs(seat.x), r=math.hypot(seat.y, seat.z), th=math.atan2(seat.z, seat.y),
             s=1 if seat.x > 0 else -1)
    rows[(t["s"], 0 if t["x"] < X_TACK else 1)].append(t)

res = {"source": str(FBX.relative_to(ROOT)).replace("\\", "/"), "mesh": lod0.name, "tacks_found": len(tacks),
       "rows": {}}
phase = {}
for (s, row), lst in sorted(rows.items()):
    N = len(lst)
    xm = sum(t["x"] for t in lst) / N
    rm = sum(t["r"] for t in lst) / N
    lst.sort(key=lambda t: t["th"] % (2 * math.pi))
    pa = 2 * math.pi / N
    ph = math.atan2(sum(math.sin(N * t["th"]) for t in lst), sum(math.cos(N * t["th"]) for t in lst)) / N
    phase[(s, row)] = ph
    ang_dev = [abs((t["th"] - ph) - round((t["th"] - ph) / pa) * pa) * rm for t in lst]
    gaps = [(a["seat"] - b["seat"]).length for a, b in zip(lst, lst[1:] + lst[:1])]
    vis_d, contact_d = [], []
    for t in lst:
        rb = sum(t["base_r"]) / SIDES
        r1 = sum(((q - t["cb"]) - t["n"] * (q - t["cb"]).dot(t["n"])).length for q in t["ring1"]) / SIDES
        z1 = sum((q - t["cb"]).dot(t["n"]) for q in t["ring1"]) / SIDES      # shoulder height above the base ring
        contact_d.append(2 * r1)        # t3: the widest ring sits at the hide
        vis_d.append(2 * r1)            # t3: = the silhouette
    seat_d = [signed_dist(t["seat"]) for t in lst]
    base_depth = [min(-signed_dist(q) for q in t["base"]) for t in lst]
    base_depth_max = [max(-signed_dist(q) for q in t["base"]) for t in lst]
    shoulder = [min(signed_dist(q) for q in t["ring1"]) for t in lst]   # t3: the widest ring vs the hide
    angs = []
    for t in lst:
        _l, nrm, _i, _d = bvh.find_nearest(t["seat"])
        radial = Vector((0, t["seat"].y, t["seat"].z)).normalized()
        nrm = nrm if nrm.dot(radial) > 0 else -nrm
        angs.append(math.degrees(t["n"].angle(nrm)))
    vd = sum(vis_d) / N
    bd = 2 * sum(sum(t["base_r"]) / SIDES for t in lst) / N
    pitch = 2 * math.pi * rm / N
    res["rows"][f"head{'+' if s > 0 else '-'}X_row{row}_{'head_side' if row else 'body_side'}"] = {
        "tacks": N, "row_x_mean_m": round(xm, 5), "row_radius_mean_m": round(rm, 5),
        "pitch_mm": round(pitch * 1000, 2),
        "neighbour_centre_distance_mm_min_max": [round(min(gaps) * 1000, 3), round(max(gaps) * 1000, 3)],
        "visible_equator_diameter_mm_min_max": [round(min(vis_d) * 1000, 3), round(max(vis_d) * 1000, 3)],
        "base_diameter_mm": round(bd * 1000, 3),
        "contact_diameter_at_hide_mm": round(sum(contact_d) / N * 1000, 3),
        "pitch_over_visible_d": round(pitch / vd, 3), "pitch_over_base_d": round(pitch / bd, 3),
        "gap_between_neighbours_at_hide_mm": round((pitch - vd) * 1000, 2),
        "dev_axial_mm_max": round(max(abs(t["x"] - xm) for t in lst) * 1000, 4),
        "dev_radial_mm_max": round(max(abs(t["r"] - rm) for t in lst) * 1000, 4),
        "dev_around_mm_max": round(max(ang_dev) * 1000, 4),
        "base_radius_mm_min_max": [round(min(min(t["base_r"]) for t in lst) * 1000, 4),
                                   round(max(max(t["base_r"]) for t in lst) * 1000, 4)],
        "dome_height_mm_min_max": [round(min(t["h"] for t in lst) * 1000, 4),
                                   round(max(t["h"] for t in lst) * 1000, 4)],
        "seat_point_to_hide_mm_min_max": [round(min(seat_d) * 1000, 3), round(max(seat_d) * 1000, 3)],
        "base_rim_buried_depth_mm_min_max": [round(min(base_depth) * 1000, 3), round(max(base_depth_max) * 1000, 3)],
        "shoulder_ring_above_hide_mm_min": round(min(shoulder) * 1000, 3),
        "tack_axis_vs_surface_normal_deg_max": round(max(angs), 3)}
for s in (-1, 1):
    N = len(rows[(s, 0)])
    pa = 2 * math.pi / N
    d = (phase[(s, 1)] - phase[(s, 0)]) % pa
    sp = sum(t["x"] for t in rows[(s, 1)]) / N - sum(t["x"] for t in rows[(s, 0)]) / N
    dg_ = []
    for t in rows[(s, 1)]:
        nb = sorted(rows[(s, 0)], key=lambda q: (q["seat"] - t["seat"]).length)[:2]
        dg_.append([(q["seat"] - t["seat"]).length for q in nb])
    vd = res["rows"][f"head{'+' if s > 0 else '-'}X_row0_body_side"]["visible_equator_diameter_mm_min_max"][0] / 1000
    sym = max(abs(a - b) for a, b in dg_)
    res[f"head{'+' if s > 0 else '-'}X"] = {
        "row_offset_in_pitches": round(d / pa, 5),
        "row_spacing_axial_mm": round(sp * 1000, 3),
        "row_spacing_over_visible_d": round(sp / vd, 3),
        "diagonal_neighbour_distance_mm_min_max": [round(min(min(x) for x in dg_) * 1000, 3),
                                                   round(max(max(x) for x in dg_) * 1000, 3)],
        "diagonal_left_right_asymmetry_mm_max": round(sym * 1000, 4)}
# ---- t2: pale hide above / below the band, measured in visible tack diameters
def body_r(x):
    return 0.600 - 0.052 * (x / 0.70) ** 2


crown = max(abs(p.x) for p in P)
coll_idx = {i for i, m in enumerate(me.materials) if m and m.name.startswith("M_DKP_Taiko_HideCollar")}
seen, cisl = set(), []
for f in bm.faces:
    if f.material_index not in coll_idx or f.index in seen:
        continue
    stack, isl = [f], []
    seen.add(f.index)
    while stack:
        c = stack.pop()
        isl.append(c)
        for e in c.edges:
            for g in e.link_faces:
                if g.index not in seen and g.material_index in coll_idx:
                    seen.add(g.index)
                    stack.append(g)
    cisl.append({v.index for q in isl for v in q.verts})
tabs = [s_ for s_ in cisl if len(s_) < 1000]     # t3: the rolled tabs (closed shells)
main = [s_ for s_ in cisl if len(s_) >= 1000]
root_x = min(abs(P[i].x) for s_ in main for i in s_)
res["hide_spacing"] = {}
for s in (-1, 1):
    key = f"head{'+' if s > 0 else '-'}X"
    r0 = res["rows"][f"{key}_row0_body_side"]
    r1 = res["rows"][f"{key}_row1_head_side"]
    vd = (r0["visible_equator_diameter_mm_min_max"][0] + r1["visible_equator_diameter_mm_min_max"][0]) / 2000
    top_edge = r1["row_x_mean_m"] + vd / 2
    bot_edge = r0["row_x_mean_m"] - vd / 2
    tip = min(abs(P[i].x) for s_ in tabs for i in s_ if P[i].x * s > 0)
    res["hide_spacing"][key] = {
        "visible_tack_diameter_mm": round(vd * 1000, 2),
        "head_edge_(lip_crown)_x_m": round(crown, 4),
        "pale_hide_above_band_mm": round((crown - top_edge) * 1000, 1),
        "pale_hide_above_band_in_D": round((crown - top_edge) / vd, 2),
        "band_width_in_D": round((top_edge - bot_edge) / vd, 2),
        "flap_root_x_m": round(root_x, 4),
        "pale_hide_below_band_to_flap_root_in_D": round((bot_edge - root_x) / vd, 2),
        "band_bottom_to_tab_tips_in_D": round((bot_edge - tip) / vd, 2),
        "reference_in_D": "about 1.6 above / 1.9 band / 2.5 below (incl. the flap)"}
# ---- t2: the flap tabs
tinfo = {}
for s in (-1, 1):
    lst = [s_ for s_ in tabs if P[next(iter(s_))].x * s > 0]
    tips, offs, ang = [], [], []
    for s_ in lst:
        pts = [P[i] for i in s_]
        xm = min(abs(p.x) for p in pts)
        tips.append(xm)
        offs.append(max(math.hypot(p.y, p.z) - body_r(abs(p.x)) for p in pts))
        ang.append(math.atan2(sum(p.z for p in pts), sum(p.y for p in pts)))
    tinfo[f"head{'+' if s > 0 else '-'}X"] = {
        "tabs": len(lst), "tip_x_min_max_m": [round(min(tips), 4), round(max(tips), 4)],
        "tab_length_root_to_tip_mm_min_max": [round((root_x - max(tips)) * 1000, 1), round((root_x - min(tips)) * 1000, 1)],
        "max_flare_outer_surface_above_barrel_mm_min_max": [round(min(offs) * 1000, 1), round(max(offs) * 1000, 1)]}
res["flap_tabs"] = tinfo

# ---- t2: the drum seated in the stand (drum FBX at (0, 0, DRUM_Z) over the stand FBX, stand-local frame)
assert ax == 0 and abs(scale - 1) < 1e-3 and max(abs(c) for c in cen[1:]) < 0.01, (ax, scale, cen)
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(STAND_FBX))
st = next(o for o in set(bpy.data.objects) - before if o.type == "MESH" and o.name.endswith("LOD0")
          and not o.name.startswith("UCX"))
SP = [st.matrix_world @ v.co for v in st.data.vertices]
smat = {i for i, m in enumerate(st.data.materials) if m and m.name.startswith("M_DKP_Taiko_Hide")}
felt_v, wood_f, felt_f = set(), [], []
for pl in st.data.polygons:
    (felt_f if pl.material_index in smat else wood_f).append(list(pl.vertices))
    if pl.material_index in smat:
        felt_v.update(pl.vertices)
DP = [Vector((p.x, p.y, p.z + DRUM_Z)) for p in P0]
drum_faces = [[v.index for v in f.verts] for f in bm.faces]
drum_bvh = BVHTree.FromPolygons(DP, drum_faces)
barrel_faces = [[v.index for v in f.verts] for f in bm.faces if f.material_index not in iron_idx | coll_idx]
barrel_bvh = BVHTree.FromPolygons(DP, barrel_faces)
wood_bvh = BVHTree.FromPolygons(SP, wood_f)
felt_bvh = BVHTree.FromPolygons(SP, felt_f)


def side_dist(p):
    """signed distance from a stand point to the drum barrel surface (+ outside the drum)"""
    loc, _n, _i, d = barrel_bvh.find_nearest(p)
    radial = Vector((0, p.y, p.z - DRUM_Z)).normalized()
    return d if (p - loc).dot(radial) >= 0 else -d


felt_top = [SP[i] for i in felt_v if math.hypot(SP[i].y, SP[i].z - DRUM_Z) < body_r(abs(SP[i].x)) + 0.0015]
ft = [side_dist(p) for p in felt_top]
# drum barrel points over each felt strip: distance down to the felt top
dz = []
for p in DP:
    if 0.445 < abs(p.x) < 0.545 and p.z < DRUM_Z - 0.45 and abs(p.y) < 0.33:
        loc, _n, _i, d = felt_bvh.find_nearest(p)
        if d < 0.01:
            dz.append(d)
seat = {}
for xf, name in ((0.435, "inner_face_x0.435"), (0.555, "outer_face_x0.555")):
    g = []
    for i, p in enumerate(SP):
        if i in felt_v or abs(abs(p.x) - xf) > 0.002 or abs(p.y) > 0.37 or p.z < 0.6:
            continue
        g.append(side_dist(p))
    seat[name] = [round(min(g) * 1000, 2), round(max(g) * 1000, 2)] if g else None
ov_wood = drum_bvh.overlap(wood_bvh)
ov_felt = drum_bvh.overlap(felt_bvh)
# nearest wood point to any drum vertex (tabs and tacks included) outside the saddle contact
near = 1e9
for p in DP:
    loc, _n, _i, d = wood_bvh.find_nearest(p, 0.05)
    if loc is not None:
        near = min(near, d)
res["drum_in_stand"] = {
    "stand_mesh": st.name,
    "felt_top_vertex_to_barrel_mm_min_max": [round(min(ft) * 1000, 3), round(max(ft) * 1000, 3)],
    "wood_seat_vertex_to_barrel_mm_min_max": seat,
    "t2_wood_seat_gap_mm": {"inner_face_x0.46": [3.2, 3.3], "outer_face_x0.58": [3.0, 3.1]},
    "drum_vs_wood_intersecting_triangle_pairs": len(ov_wood),
    "drum_vs_felt_intersecting_triangle_pairs": len(ov_felt),
    "nearest_drum_vertex_to_wood_mm": round(near * 1000, 2)}
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))

