"""t6 (2026-10-03, adapted from t5/measure_t5.py): the t6 drum (built in design units, scaled x taiko_uv.DRUM_SCALE;
79 tacks per row; DRUM_Z 1.393; the cradle beams at x 0.350-0.470), all in REAL metres; plus the post tops under the
drum mesh and the skirt's self-intersection. Before: t4 (2026-10-03, adapted from t3/measure_t3.py: 18-sided domes, 76 per row, rows 36.5 mm apart, X_TACK 0.662, the
bulged barrel (taiko_uv.body_r), DRUM_Z 1.30, the cradle beams at x 0.390-0.510; plus the barrel profile, the tack
gaps / front-view overlap, the gold ramp position and the lathe UV scale). Before: t3 (adapted from
t2/measure_t2.py: 24-sided true domes, rows 40 mm apart, X_TACK 0.678, the
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
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko" / "t6" / "measure_t6.json"
import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "props" / "taiko"))
import taiko_uv as UVL  # noqa: E402
STAND_FBX = ROOT / "Exports" / "DojoKit" / "Props" / "taiko" / "SM_DKP_Taiko_Stand.fbx"
S6 = UVL.DRUM_SCALE
DRUM_Z = 1.393
X_TACK = (0.655 - UVL.D_SHIFT) * S6       # t6: real (t5: 0.655)
SINK = 0.0025
SIDES = 18
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
ax = 0          # t6: the drum axis is X (the wider t6 drum's ring handles make Y the longest extent, 1.62 m)
scale = 1.554 / ext[ax]
others = [i for i in range(3) if i != ax]
cen = [(max(p[i] for p in P0) + min(p[i] for p in P0)) / 2 for i in range(3)]
cen = [cen[0], 0.0, 0.0]   # t6: the pivot is the drum's axis (the t6 skirt ears make the y / z bounding box asymmetric)
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
    """t6: the REAL barrel radius (build_taiko.body_R)"""
    return S6 * UVL.body_r(x / S6)


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
tabs = [s_ for s_ in cisl if min(abs(P[i].x) for i in s_) < 0.57]   # t5: the skirts (t3/t4: tabs, < 1000 verts)
main = [s_ for s_ in cisl if min(abs(P[i].x) for i in s_) >= 0.57]
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
        "gold_ramp_top_below_band_in_D": round((bot_edge - S6 * UVL.X_GOLD) / vd, 2),
        "gold_ramp_top_below_band_in_D_with_wave_min_max": [round((bot_edge - S6 * (UVL.X_GOLD + UVL.GOLD_WAVE)) / vd, 2),
                                                            round((bot_edge - S6 * (UVL.X_GOLD - UVL.GOLD_WAVE)) / vd, 2)],
        "gold_ramp_top_below_skirt_root_mm_min": round(1000 * S6 * (UVL.X_SK - UVL.X_GOLD - UVL.GOLD_WAVE), 1),
        "gold_full_below_band_in_D": round((bot_edge - S6 * (UVL.X_GOLD - UVL.GOLD_RAMP)) / vd, 2),
        "gold_ramp_length_in_D": round(S6 * UVL.GOLD_RAMP / vd, 2),
        "t4_targets_in_D": "about 2.0 above / 0.5 band to gold start / 2.4 band to tab tips (judge r3 item 3)"}
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
        "skirt_shells": len(lst), "verts": sum(len(s_) for s_ in lst), "hem_x_min_max_m": [round(min(tips), 4), round(max(tips), 4)],
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
    if 0.36 < abs(p.x) < 0.46 and p.z < DRUM_Z - 0.50 and abs(p.y) < 0.37:
        loc, _n, _i, d = felt_bvh.find_nearest(p)
        if d < 0.01:
            dz.append(d)
seat = {}
for xf, name in ((0.350, "inner_face_x0.350"), (0.470, "outer_face_x0.470")):
    g = []
    for i, p in enumerate(SP):
        if i in felt_v or abs(abs(p.x) - xf) > 0.002 or abs(p.y) > 0.42 or p.z < 0.6:
            continue
        g.append(side_dist(p))
    seat[name] = [round(min(g) * 1000, 2), round(max(g) * 1000, 2)] if g else None
ov_wood = drum_bvh.overlap(wood_bvh)
ov_felt = drum_bvh.overlap(felt_bvh)
# nearest wood point to any drum vertex (tabs and tacks included) outside the saddle contact
near, near_at = 1e9, None
close = []
for p in DP:
    loc, _n, _i, d = wood_bvh.find_nearest(p, 0.05)
    if loc is not None:
        if d < near:
            near, near_at = d, (p.copy(), loc.copy())
        if d < 0.002:
            close.append(p.copy())
res["drum_in_stand"] = {
    "stand_mesh": st.name,
    "felt_top_vertex_to_barrel_mm_min_max": [round(min(ft) * 1000, 3), round(max(ft) * 1000, 3)],
    "wood_seat_vertex_to_barrel_mm_min_max": seat,
    "t5_wood_seat_gap_mm": [2.92, 3.11],
    "drum_vs_wood_intersecting_triangle_pairs": len(ov_wood),
    "drum_vs_felt_intersecting_triangle_pairs": len(ov_felt),
    "nearest_drum_vertex_to_wood_mm": round(near * 1000, 2),
    "nearest_drum_vertex_and_wood_point_stand_local_m": [[round(c, 4) for c in q] for q in near_at],
    "drum_vertices_within_2mm_of_wood": len(close),
    "drum_vertices_within_2mm_x_y_z_ranges": ([[round(min(abs(q[i]) for q in close), 4),
                                                round(max(abs(q[i]) for q in close), 4)] for i in range(3)]
                                              if close else None)}
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))



# ---- t4: the tacks' gaps (in-row and diagonal neighbours: vertex-to-surface distance over the dome above the hide,
# and BVH triangle overlap) and the front-view overlap of the two rows' outlines
isl_faces = []
tack_isl = [isl for isl in islands if len({v.index for f in isl for v in f.verts}) == 1 + NRING * SIDES]
for isl in tack_isl:
    vs = sorted({v.index for f in isl for v in f.verts})
    loc = {g: i for i, g in enumerate(vs)}
    isl_faces.append((vs, BVHTree.FromPolygons([P[g] for g in vs], [[loc[v.index] for v in f.verts] for f in isl])))
cent = [sum((P[g] for g in vs), Vector()) / len(vs) for vs, _b in isl_faces]
gap_min, overlaps, pairs = {"in_row": 1e9, "diagonal": 1e9}, 0, 0
for i, (vs, bv) in enumerate(isl_faces):
    near = sorted(range(len(isl_faces)), key=lambda j: (cent[j] - cent[i]).length)[1:5]
    for j in near:
        if j < i:
            continue
        kind = "in_row" if abs(abs(cent[j].x) - abs(cent[i].x)) < 0.01 else "diagonal"
        bj = isl_faces[j][1]
        pairs += 1
        overlaps += len(bv.overlap(bj))
        for g in vs:
            if signed_dist(P[g]) < 0:        # the sunk skirt below the hide
                continue
            hit = bj.find_nearest(P[g], 0.05)
            if hit[0] is not None:
                gap_min[kind] = min(gap_min[kind], hit[3])
front = {}
for s in (-1, 1):
    # the tacks nearest the front centre (-Y side, z ~ 0) of each row: the outline in an orthographic view along +Y
    rows_ = {}
    for vs, _b in isl_faces:
        c = sum((P[g] for g in vs), Vector()) / len(vs)
        if c.x * s <= 0 or c.y > -0.3 or abs(c.z) > 0.06:
            continue
        row = 0 if abs(c.x) < X_TACK else 1
        xs = [abs(P[g].x) for g in vs if signed_dist(P[g]) >= -1e-4]
        zs = [P[g].z for g in vs if signed_dist(P[g]) >= -1e-4]
        rows_.setdefault(row, []).append((min(xs), max(xs), min(zs), max(zs), abs(c.x)))
    if 0 in rows_ and 1 in rows_:
        r0_top = max(q[1] for q in rows_[0])
        r1_bot = min(q[0] for q in rows_[1])
        ax_ext = [q[1] - q[0] for q in rows_[0] + rows_[1]]
        wid = [q[3] - q[2] for q in rows_[0] + rows_[1]]
        c0 = sum(0.5 * (q[0] + q[1]) for q in rows_[0]) / len(rows_[0])
        c1 = sum(0.5 * (q[0] + q[1]) for q in rows_[1]) / len(rows_[1])
        dvis = sum(wid) / len(wid)
        front["head%sX" % ("+" if s > 0 else "-")] = {
            "tacks_used": [len(rows_[0]), len(rows_[1])],
            "outline_width_across_mm": round(dvis * 1000, 2),
            "outline_extent_along_axis_mm": round(sum(ax_ext) / len(ax_ext) * 1000, 2),
            "row_outline_centre_spacing_mm": round((c1 - c0) * 1000, 2),
            "row_spacing_over_visible_d": round((c1 - c0) / dvis, 3),
            "outline_overlap_mm": round((r0_top - r1_bot) * 1000, 2),
            "outline_overlap_over_d": round((r0_top - r1_bot) / dvis, 3)}
res["t4_tack_gaps"] = {"neighbour_pairs_checked": pairs, "intersecting_triangle_pairs": overlaps,
                       "min_gap_in_row_mm": round(gap_min["in_row"] * 1000, 2),
                       "min_gap_diagonal_mm": round(gap_min["diagonal"] * 1000, 2),
                       "note": "vertex-to-neighbour-surface over each dome above the hide (an upper bound of the "
                               "true gap within the 18-gon facet size)"}
res["t4_front_view_rows"] = front

# ---- t4: the barrel profile on the exported lacquer vertices (ratio to the belly), the head / belly
lac_idx = {i for i, m in enumerate(me.materials) if m and m.name.startswith("M_DKP_Taiko_Lacquer")}
lac_v = {v.index for f in bm.faces if f.material_index in lac_idx for v in f.verts}
byx = defaultdict(list)
for i in lac_v:
    byx[round(abs(P[i].x), 3)].append(math.hypot(P[i].y, P[i].z))
belly = max(max(v) for v in byx.values())
prof = {"%.3f" % k: round(sum(v) / len(v) / belly, 4) for k, v in sorted(byx.items()) if len(v) > 100}
res["t4_barrel_profile_exported"] = {
    "belly_diameter_m": round(2 * belly, 4), "length_m": round(ext[ax] * scale, 4),
    "ring_radius_over_belly_by_x": prof,
    "head_lip_outline_over_belly": round(S6 * UVL.BODY_RC / belly, 4),
    "length_over_belly": round(ext[ax] * scale / (2 * belly), 4),
    "crown_half_length_over_belly_radius_design": round(UVL.BODY_LC / UVL.body_r(0), 4),
    "reference_head_over_max_body": 0.7906,
    "belly_over_body_at_lowest_hem_real_x%.4f" % (S6 * (0.5145 - UVL.D_SHIFT)): round(belly / body_r(S6 * (0.5145 - UVL.D_SHIFT)), 4),
    "reference_max_over_collar_line": 1.0571,
    "note": "the reference's collar line (flap hem at the silhouette) sits at 0.526 of its crown half-length; ours "
            "(mean hem x 0.520) at 0.67: the same profile by relative height gives 1.10 there"}

# ---- t4: lathe UV scale on the lacquer and the collar (U by arc length: metres of texture per metre of surface)
uvl = bm.loops.layers.uv.get("UV0") or bm.loops.layers.uv[0]
tab_v = set().union(*tabs)
sc_l, sc_c = [], []
for f in bm.faces:
    if f.material_index not in lac_idx | coll_idx:
        continue
    if f.material_index in coll_idx and any(v.index in tab_v for v in f.verts):
        continue
    for lp in f.loops:
        a, b = lp.vert, lp.link_loop_next.vert
        d3 = (P[b.index] - P[a.index])
        if d3.length < 1e-3:
            continue
        du = lp.link_loop_next[uvl].uv - lp[uvl].uv
        if abs(d3.x) > 0.8 * d3.length and abs(du.x) > 1e-6:      # along the axis: U
            tile = UVL.LAC_TILE if f.material_index in lac_idx else UVL.COLLAR_TILE_U
            (sc_l if f.material_index in lac_idx else sc_c).append(abs(du.x) * tile / d3.length)
res["t4_uv_scale_along_profile"] = {
    "lacquer_texture_m_per_surface_m_min_max": [round(min(sc_l), 4), round(max(sc_l), 4)] if sc_l else None,
    "collar_texture_m_per_surface_m_min_max": [round(min(sc_c), 4), round(max(sc_c), 4)] if sc_c else None,
    "lacquer_V_tile_m_at_belly_and_root": [round(2 * math.pi * belly / UVL.LAC_WRAPS, 3),
                                           round(2 * math.pi * body_r(S6 * UVL.X_ROOT) / UVL.LAC_WRAPS, 3)],
    "lacquer_U_tile_m": UVL.LAC_TILE}
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print("T4", json.dumps({k: res[k] for k in ("t4_tack_gaps", "t4_front_view_rows", "t4_barrel_profile_exported",
                                            "t4_uv_scale_along_profile")}, indent=1))

# ---- t6: the post tops under the drum mesh (vertical gap from each post-top vertex up to the drum, exported meshes)
post_top_z = max(p.z for p in SP if p.z < 1.0)
post_tops = [p for p in SP if abs(p.z - post_top_z) < 0.002 and abs(abs(p.x) - 0.450) < 0.10 and abs(abs(p.y) - 0.544) < 0.10]
gaps_up = []
for p in post_tops:
    hit = drum_bvh.ray_cast(p + Vector((0, 0, 1e-4)), Vector((0, 0, 1)), 0.5)
    if hit[0] is not None:
        gaps_up.append(hit[3])
# ---- t6: the skirts' self-intersection (no shared vertex), exported LOD0
sk_faces = [f for f in bm.faces if f.material_index in coll_idx and any(v.index in tab_v for v in f.verts)]
SKP = [[v.index for v in f.verts] for f in sk_faces]
sk_bvh = BVHTree.FromPolygons(P, SKP)
selfx = [(a, b) for a, b in sk_bvh.overlap(sk_bvh) if a < b and not (set(SKP[a]) & set(SKP[b]))]
res["t6_extra"] = {"post_top_z_m": round(post_top_z, 4), "post_top_vertices": len(post_tops),
                   "post_top_vertical_gap_up_to_drum_mm_min": round(1000 * min(gaps_up), 2) if gaps_up else None,
                   "post_top_vertices_with_drum_above": len(gaps_up),
                   "skirt_faces": len(SKP), "skirt_self_intersecting_face_pairs": len(selfx)}
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print("T6", json.dumps(res["t6_extra"]))
