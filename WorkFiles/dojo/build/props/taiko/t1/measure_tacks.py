"""t1 (2026-10-02): measure the taiko tacks on the EXPORTED drum FBX (LOD0), in a fresh headless Blender."""
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
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko" / "t1" / "measure_tacks.json"
SINK = 0.0025
SIDES = 12

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
iron_idx = {i for i, m in enumerate(me.materials) if m and "Iron" in m.name}
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
    if len(vs) != 1 + 2 * SIDES:
        continue
    vlist = [bm.verts[i] for i in vs]
    pole = [v for v in vlist if len(v.link_edges) == SIDES]
    if len(pole) != 1:
        continue
    pole = pole[0]
    r1 = {e.other_vert(pole).index for e in pole.link_edges}
    base = [P[v.index] for v in vlist if v.index not in r1 and v is not pole]
    ring1 = [P[i] for i in r1]
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
    rows[(t["s"], 0 if t["x"] < 0.703 else 1)].append(t)

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
    vis_d = []
    for t in lst:
        rb = sum(t["base_r"]) / SIDES
        r1 = sum(((q - t["cb"]) - t["n"] * (q - t["cb"]).dot(t["n"])).length for q in t["ring1"]) / SIDES
        z1 = sum((q - t["cb"]).dot(t["n"]) for q in t["ring1"]) / SIDES      # shoulder height above the base ring
        vis_d.append(2 * (rb + (r1 - rb) * (SINK / z1)))
    seat_d = [signed_dist(t["seat"]) for t in lst]
    base_depth = [min(-signed_dist(q) for q in t["base"]) for t in lst]
    base_depth_max = [max(-signed_dist(q) for q in t["base"]) for t in lst]
    shoulder = [min(signed_dist(q) for q in t["ring1"]) for t in lst]
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
        "visible_diameter_mm_min_max": [round(min(vis_d) * 1000, 3), round(max(vis_d) * 1000, 3)],
        "base_diameter_mm": round(bd * 1000, 3),
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
    vd = res["rows"][f"head{'+' if s > 0 else '-'}X_row0_body_side"]["visible_diameter_mm_min_max"][0] / 1000
    sym = max(abs(a - b) for a, b in dg_)
    res[f"head{'+' if s > 0 else '-'}X"] = {
        "row_offset_in_pitches": round(d / pa, 5),
        "row_spacing_axial_mm": round(sp * 1000, 3),
        "row_spacing_over_visible_d": round(sp / vd, 3),
        "diagonal_neighbour_distance_mm_min_max": [round(min(min(x) for x in dg_) * 1000, 3),
                                                   round(max(max(x) for x in dg_) * 1000, 3)],
        "diagonal_left_right_asymmetry_mm_max": round(sym * 1000, 4)}
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
