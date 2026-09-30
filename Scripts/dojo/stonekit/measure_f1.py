"""Stone kit FIX ROUND 1: measure the judge's numbers on the built pieces (read-only on Assets/Dojo/DojoStoneKit.blend).

  joints   Wall_4m_H3: horizontal scan lines on the face (every 0.10 m of depth from 0.45 to 3.2 m), rays from the
           valley (-Y) every 2 mm along x 0.4 .. 3.6: runs of rays that do not hit a face stone's front (the core, or a
           stone flank steeper than 60 deg from the face normal) = the visible dark joint; median / p10 / p90 widths
  crown    the same rays: per stone run, the crown rise (max proudness minus the proudness 3 cm inside the run's ends)
  polygon  WallFoot skirt / wall: nothing here (the builders report their counts)
  flags    Landing_W180: the same joint scan across the paving (rays from above)
Run: blender -b --factory-startup --python Scripts/dojo/stonekit/measure_f1.py
Out: WorkFiles/dojo/build/stonekit/f1_measure.json
"""
import json
import math
import statistics as st
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[3]
SK = ROOT / "WorkFiles" / "dojo" / "build" / "stonekit"
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "Assets" / "Dojo" / "DojoStoneKit.blend"))
OBJ = {o.name: o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SM_DKT_")}


def bvh_of(o):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    mats = [f.material_index for f in bm.faces]
    t = BVHTree.FromBMesh(bm)
    bm.free()
    return t, mats


def pct(v, q):
    v = sorted(v)
    return round(v[min(len(v) - 1, int(q * len(v)))], 4) if v else None


def scan(o, stone_slots, origin_fn, direction, n_fn, xs, lines):
    """Rays along scan lines: returns (joint widths, crown rises)."""
    t, mats = bvh_of(o)
    joints, crowns = [], []
    step = xs[1] - xs[0]
    for ln in lines:
        run_j, run_s = 0, []
        for x in xs:
            h = t.ray_cast(origin_fn(x, ln), direction, 20.0)
            is_face = False
            if h[0] is not None and mats[h[2]] in stone_slots:
                nrm = h[1]
                is_face = nrm.dot(-direction) > math.cos(math.radians(60))
            if is_face:
                if run_j:
                    joints.append(run_j * step)
                    run_j = 0
                run_s.append(n_fn(h[0]))
            else:
                if run_s and len(run_s) > 30:
                    k = int(0.03 / step)
                    edge = max(run_s[min(k, len(run_s) - 1)], run_s[max(0, len(run_s) - 1 - k)])
                    crowns.append(max(run_s) - edge)
                run_s = []
                run_j += 1
    joints = [j for j in joints if j < 0.15]           # longer runs are module ends / openings
    return joints, crowns


def slots(o, names):
    return {i for i, m in enumerate(o.data.materials) if m and m.name in names}


res = {}
w = OBJ.get("SM_DKT_Wall_4m_H3")
if w:
    xs = [0.4 + 0.002 * i for i in range(1600)]
    lines = [-0.45 - 0.10 * k for k in range(28)]

    def d(s):
        return 0.10 * s + 0.035 * s * s
    js, cr = scan(w, slots(w, {"M_DKT_WallGranite"}), lambda x, z: Vector((x, -3.0, z)), Vector((0, 1, 0)),
                  lambda p: -p.y - d(-p.z), xs, lines)
    res["wall_4m_H3_joints_m"] = {"median": pct(js, 0.5), "p10": pct(js, 0.1), "p90": pct(js, 0.9), "n": len(js),
                                  "note": "visible joint = rays that miss a stone's FRONT (core, or a flank > 60 deg "
                                          "from the face): the dark line incl. the small arrises"}
    res["wall_4m_H3_crown_rise_m"] = {"median": pct(cr, 0.5), "p90": pct(cr, 0.9), "n": len(cr)}
lf = OBJ.get("SM_DKT_Stair_Landing_W180")
if lf:
    xs = [-0.85 + 0.002 * i for i in range(850)]
    lines = [-0.8 + 0.1 * k for k in range(17)]
    js, cr = scan(lf, slots(lf, {"M_DKT_StepGranite"}), lambda x, y: Vector((x, y, 2.0)), Vector((0, 0, -1)),
                  lambda p: p.z, xs, lines)
    res["landing_W180_joints_m"] = {"median": pct(js, 0.5), "p10": pct(js, 0.1), "p90": pct(js, 0.9), "n": len(js)}
    res["landing_W180_crown_rise_m"] = {"median": pct(cr, 0.5), "p90": pct(cr, 0.9), "n": len(cr)}
fl = OBJ.get("SM_DKT_Stair_Flight_W180_R100")
if fl:
    t, mats = bvh_of(fl)
    sg = slots(fl, {"M_DKT_StepGranite"})
    sr = slots(fl, {"M_DKT_StepRiser"})
    tread = riser = 0
    for i in range(6):
        for x in (-0.5, 0.0, 0.5):
            h = t.ray_cast(Vector((x, i / 3 + 0.17, 3.0)), Vector((0, 0, -1)), 9.0)
            tread += int(h[0] is not None and mats[h[2]] in sg)
            h = t.ray_cast(Vector((x, -1.0, (i + 1) / 6 - 0.10)), Vector((0, 1, 0)), 9.0)
            riser += int(h[0] is not None and mats[h[2]] in sr)
    res["flight_W180_R100_slots"] = {"tread_rays_on_StepGranite": f"{tread}/18", "riser_rays_on_StepRiser": f"{riser}/18"}
lt = OBJ.get("SM_DKT_Stair_Lantern_Timber")
if lt:
    vs = [v.co for v in lt.data.vertices]
    shaft = [abs(v.x) for v in vs if 0.25 < v.z < 0.45]
    head = [abs(v.x) for v in vs if 0.62 < v.z < 0.86]
    res["lantern_timber"] = {"shaft_width_m": round(2 * max(shaft), 3), "light_box_width_m": round(2 * max(head), 3),
                             "height_m": round(max(v.z for v in vs), 3)}
out = SK / "f1_measure.json"
out.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
