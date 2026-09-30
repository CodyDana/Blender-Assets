"""Round 3 measurements of the hall (headless, read-only; nothing is saved):
  upper roof  ray-cast profiles of the front slope's render meshes: the outer-wing eave, the raised centre eave, the
              ridge crest and ridge-end tops, the ridge / eave length ratio; the centre plane's collision pitch
  deck        the veranda deck meets the wall (front X 16 and west Y 28 profiles); the board joints: rays down every
              2 mm across the deck must stop on the dark backing or a sleeper, never on the ground under the veranda
  headroom    R5: rays up from the deck / the step band to the first hall mesh along the front at the bays' centres
  lods        SM_DKH_StepBand (and every LOD piece): each exported LOD's box inside LOD0's (re-imported FBX)
Run: blender -b --factory-startup Assets/Dojo/DojoHall.blend --python Scripts/dojo/hall/measure_r3.py
Out: WorkFiles/dojo/build/hall/measure_r3.json
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(bpy.data.filepath).resolve().parents[2]
HW = ROOT / "WorkFiles" / "dojo" / "build" / "hall"
EXP = ROOT / "Exports" / "DojoKit" / "Hall"
LH = json.loads((HW / "layout_hall.json").read_text(encoding="utf-8"))
dg = bpy.context.evaluated_depsgraph_get()


def bvh_of(pred):
    verts, polys, owner = [], [], []
    for o in bpy.data.collections["Assembly"].objects:
        piece = o.name.split("__")[0]
        if o.type != "MESH" or not pred(piece):
            continue
        me = o.evaluated_get(dg).to_mesh()
        mw = o.matrix_world
        base = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        for p in me.polygons:
            polys.append([base + i for i in p.vertices])
            owner.append(piece)
        o.evaluated_get(dg).to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys, epsilon=0.0), owner


HALL, OWN = bvh_of(lambda p: p.startswith("SM_DKH_"))


def down(x, y, z0=20.0):
    h = HALL.ray_cast(Vector((x, y, z0)), Vector((0, 0, -1)), 40.0)
    return (round(h[0].z, 4), OWN[h[2]]) if h[0] is not None else (None, None)


def up(x, y, z0):
    h = HALL.ray_cast(Vector((x, y, z0)), Vector((0, 0, 1)), 20.0)
    return (round(h[0].z, 4), OWN[h[2]]) if h[0] is not None else (None, None)


def horiz(x, z, y0=15.0):
    h = HALL.ray_cast(Vector((x, y0, z)), Vector((0, 1, 0)), 30.0)
    return (round(h[0].y, 4), OWN[h[2]]) if h[0] is not None else (None, None)


R = {"date": "2026-09-28", "stage": "hall round 3 (look pass): measured on Assets/Dojo/DojoHall.blend"}
# ---- upper roof: eave lines from the front (the lowest roof-mesh point along Y at each X, found by horizontal rays)
def eave_front(x):
    """The front-most upper-roof mesh edge at X: scan z downward from +7 and keep the first z where a horizontal ray from
    the courtyard hits an upper-roof piece before Y 23.9 (the fascia / tile lip), i.e. the eave's lowest visible z."""
    lowest = None
    z = 7.0
    while z > 4.8:
        yh, who = horiz(x, z)
        if who and who.startswith("SM_DKH_RoofUpper") and yh < 23.95:
            lowest = (round(z, 3), yh)
        z -= 0.01
    return lowest


R["upper_roof"] = {
    "eave_lowest_visible_z_and_y": {str(x): eave_front(x) for x in (13.5, 15.6, 16.5, 19.0, 22.0, 25.0, 27.5, 28.4)},
    "crest_z": {str(x): down(x, 29.0) for x in (16.0, 22.0, 28.0)},
    "ridge_end_top": max((down(x, 29.0 + dy)[0] or 0) for x in [14.0 + 0.02 * i for i in range(40)]
                         for dy in (-0.1, 0.0, 0.1)),
    "front_slope_top_surface_z": {f"{x},{y}": down(x, y) for x in (15.6, 22.0) for y in (23.3, 23.7, 24.5, 26.0, 27.5)},
}
num = LH["numbers"]["upper_roof"]
R["upper_roof"]["layout_numbers"] = {k: num[k] for k in ("planes_meet", "ridge_cap_top", "ridge_end_top",
                                                          "ridge_end_above_cap_m", "ridge_to_eave_length",
                                                          "gable_face_x", "verge_x", "front_recess")}
# ---- collision pitch of every upper-front hull face (the slabs' tops)
kit = {o.name: o for o in bpy.data.collections["Kit"].objects}
fr = kit["SM_DKH_RoofUpper_Front"]
slopes = []
for h in fr.children:
    if not h.name.startswith("UCX_"):
        continue
    top = max(h.data.polygons, key=lambda p: (h.matrix_world.to_3x3() @ p.normal).z)
    n = (h.matrix_world.to_3x3() @ top.normal).normalized()
    slopes.append(round(math.degrees(math.acos(max(-1, min(1, n.z)))), 2))
R["upper_roof"]["front_hull_top_pitches_deg"] = sorted(slopes)
# ---- deck to wall + board joints
prof = []
y = 21.9
while y < 24.05:
    prof.append([round(y, 3), *down(16.0, y, 3.0 - 0.3)])
    y += 0.01
R["deck_to_wall_front_x16"] = {"samples": len(prof), "below_0.49": [p for p in prof if p[1] is not None and p[1] < 0.49 and p[0] < 23.9],
                               "wall_face_hit": [p for p in prof if p[2] and not p[2].startswith(("SM_DKH_Veranda", "SM_DKH_StepBand"))][:3]}
profw = []
x = 10.95
while x < 13.05:
    profw.append([round(x, 3), *down(x, 28.9, 2.7)])
    x += 0.01
R["deck_to_wall_west_y28.9"] = {"samples": len(profw),
                                "below_0.49": [p for p in profw if p[1] is not None and p[1] < 0.49 and 11.02 < p[0] < 12.9]}
thru = 0
n = 0
for x in [11.3 + 0.002 * i for i in range(0, 10000, 7)]:          # a 2 mm-pitch sweep across the front strip
    for yy in (22.4, 23.0, 23.6):
        n += 1
        z, who = down(x, yy, 1.2)
        if z is None or z < 0.40:
            thru += 1
for yy in [24.2 + 0.002 * i for i in range(0, 4800, 7)]:        # and along the west strip
    for xx in (11.5, 12.2):
        n += 1
        z, who = down(xx, yy, 1.2)
        if z is None or z < 0.40:
            thru += 1
R["deck_board_joints"] = {"rays": n, "rays_reaching_below_+0.40": thru,
                          "note": "rays straight down through the deck boards (5 mm joints); round 3 adds a dark backing "
                                  "board under the boards (top +0.452), so a joint shows the backing, not the lit ground"}
# ---- R5 headroom (rays up from the walking surfaces at the bay centres)
hr = {}
for label, yy, z0 in (("step_band_lower_tread_Y21.475", 21.475, 0.25), ("step_band_upper_tread_Y21.825", 21.825, 0.5),
                      ("deck_Y22.3_at_the_post_line", 22.3, 0.5), ("deck_Y22.6", 22.6, 0.5), ("deck_Y23.0", 23.0, 0.5),
                      ("deck_Y23.5", 23.5, 0.5)):
    vals = []
    for x in (12.0, 14.0, 16.0, 18.0, 20.0, 22.0):
        zt, who = up(x, yy, z0 + 0.01)
        vals.append(round(zt - z0, 3) if zt else None)
    hr[label] = {"min_m": min(v for v in vals if v), "values_m": vals}
R["headroom_R5"] = hr
# ---- LODs (fresh import of the exported FBX, one scene per file)
lods = {}
for fbx in sorted(EXP.glob("SM_DKH_*.fbx")):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH" and not o.name.startswith("UCX_")]
    boxes = {}
    for o in new:
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        boxes[o.name] = [min(p[i] for p in pts) for i in range(3)] + [max(p[i] for p in pts) for i in range(3)]
    l0 = next((k for k in boxes if k.endswith("_LOD0")), None)
    if l0 and len(boxes) > 1:
        b0 = boxes[l0]
        out = {}
        for k, b in boxes.items():
            if k == l0:
                continue
            out[k] = round(max(max(b0[i] - b[i] for i in range(3)), max(b[i + 3] - b0[i + 3] for i in range(3)), 0.0), 5)
        lods[fbx.stem] = {"max_past_lod0_m": out}
    for o in [o for o in bpy.data.objects if o not in before]:
        bpy.data.objects.remove(o, do_unlink=True)
R["lods_past_lod0"] = lods
(HW / "measure_r3.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
print("MEASURE_R3 written", json.dumps({k: R[k] for k in ("deck_board_joints", "lods_past_lod0")}))
