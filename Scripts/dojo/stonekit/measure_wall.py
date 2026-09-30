"""Stone kit track 8: measure the built wall pieces (read-only on WorkFiles/dojo/build/stonekit/wall/DojoStoneKit_wall.blend).

  batter      ray casts from the valley side (-Y) at x = 0.5 .. L-0.5 every 0.25 m and every 0.1 m of depth: the median
              stone-rim y per depth vs the kit profile d(s) (face set-back)
  coping      the walkable top: every vertex above -0.05 in the coping band (y 0.05 .. 0.5): max / min z
  seams       two modules side by side (4m_H3 at x 0 and 4m_H4 at x 4): the fraction of face rays that hit STONE (not
              the joint core) in a 0.3 m band on the seam vs the module interiors (a straight joint through the courses
              would show as a low seam fraction)
  stairs      StairOpening_H*: downward rays on the flight centre line every 1 cm: tread tops (risers) and the nosing
              positions (treads), the curb tops above the nosing line
  ucx         every piece: its hulls' top z (wall tops at 0.0), the stair ramp's slope
Run: blender -b --factory-startup --python Scripts/dojo/stonekit/measure_wall.py
Out: WorkFiles/dojo/build/stonekit/wall/measure_wall.json
"""
import json
import math
import statistics as st
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
W = ROOT / "WorkFiles" / "dojo" / "build" / "stonekit" / "wall"
bpy.ops.wm.open_mainfile(filepath=str(W / "DojoStoneKit_wall.blend"))
OBJ = {o.name: o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("SM_DKT_")}


def d(s):
    s = max(0.0, s)
    return 0.10 * s + 0.035 * s * s


def bvh(o, M=Matrix()):
    me = o.data
    vs = [M @ v.co for v in me.vertices]
    return BVHTree.FromPolygons(vs, [tuple(p.vertices) for p in me.polygons]), me


def mat_of_hit(me, idx):
    return me.materials[me.polygons[idx].material_index].name


def batter(name, L, h):
    t, me = bvh(OBJ[name])
    out = []
    for i in range(int((h + 0.3) / 0.1)):
        z = -0.30 - 0.1 * i
        if z < -h:
            break
        ys = []
        x = 0.5
        while x < L - 0.5:
            hit = t.ray_cast(Vector((x, -5.0, z)), Vector((0, 1, 0)), 10.0)
            if hit[0] is not None and mat_of_hit(me, hit[2]) != "M_DK_JointEarth":
                ys.append(hit[0].y)
            x += 0.05
        if ys:
            s = -z
            out.append({"s": round(s, 2), "d_kit": round(d(s), 3), "rim_median_out": round(-st.median(ys), 3),
                        "crown_max_out": round(-min(ys), 3), "stone_fraction": round(len(ys) / ((L - 1.0) / 0.05), 3)})
    dev = [o["rim_median_out"] - o["d_kit"] for o in out]  # >0: the stone rims stand proud of the profile
    return {"rows": out[::5], "median_stone_proud_of_profile_m": round(st.median(dev), 4),
            "max_abs_dev_m": round(max(abs(x) for x in dev), 4), "stone_fraction_mean": round(st.mean(o["stone_fraction"] for o in out), 3)}


def coping(name):
    me = OBJ[name].data
    zs = [v.co.z for v in me.vertices if 0.05 < v.co.y < 0.50 and v.co.z > -0.05]
    return {"top_max_z": round(max(zs), 4), "top_min_z": round(min(zs), 4), "n": len(zs)}


def seams():
    a, b = OBJ["SM_DKT_Wall_4m_H3"], OBJ["SM_DKT_Wall_4m_H4"]
    ta, ma = bvh(a)
    tb, mb = bvh(b, Matrix.Translation((4, 0, 0)))

    def frac(x0, x1):
        hit_s = tot = 0
        z = -0.4
        while z > -2.9:
            x = x0
            while x < x1:
                best = None
                for (t, me) in ((ta, ma), (tb, mb)):
                    hh = t.ray_cast(Vector((x, -5.0, z)), Vector((0, 1, 0)), 10.0)
                    if hh[0] is not None and (best is None or hh[3] < best[0][3]):
                        best = (hh, me)
                tot += 1
                if best and mat_of_hit(best[1], best[0][2]) != "M_DK_JointEarth":
                    hit_s += 1
                x += 0.02
            z -= 0.02
        return round(hit_s / max(tot, 1), 3)
    return {"seam_band_x_3.85_4.15": frac(3.85, 4.15), "interior_band_x_1.85_2.15": frac(1.85, 2.15),
            "interior_band_x_5.85_6.15": frac(5.85, 6.15)}


def stairs(h):
    name = f"SM_DKT_Wall_StairOpening_H{h}"
    t, me = bvh(OBJ[name])
    tops = []
    y = 0.5
    while y > -(6 * h) / 3.0 - 0.3:
        hit = t.ray_cast(Vector((2.0, y, 1.0)), Vector((0, 0, -1)), 10.0)
        if hit[0] is not None:
            tops.append((round(y, 3), hit[0].z))
        y -= 0.01
    # group into treads by height
    levels = []
    for (y, z) in tops:
        if levels and abs(z - levels[-1]["z"]) < 0.05:
            levels[-1]["ys"].append(y)
            levels[-1]["zs"].append(z)
            levels[-1]["z"] = st.median(levels[-1]["zs"])
        else:
            levels.append({"z": z, "zs": [z], "ys": [y]})
    lv = [{"z": round(st.median(l["zs"]), 4), "y_front": round(min(l["ys"]), 3), "y_back": round(max(l["ys"]), 3)}
          for l in levels if len(l["ys"]) > 5]
    risers = [round(lv[i]["z"] - lv[i + 1]["z"], 4) for i in range(len(lv) - 1)]
    treads = [round(lv[i]["y_front"] - lv[i + 1]["y_front"], 4) for i in range(len(lv) - 1)]
    curb = t.ray_cast(Vector((0.9, -2.0, 1.0)), Vector((0, 0, -1)), 10.0)
    return {"levels": len(lv), "risers_m": {"min": min(risers), "max": max(risers), "median": st.median(risers)},
            "treads_m": {"min": min(treads[1:-1]), "max": max(treads[1:-1]), "median": st.median(treads)},
            "top_z": lv[0]["z"], "bottom_tread_z": lv[-1]["z"],
            "curb_top_at_y-2_m": round(curb[0].z, 4) if curb[0] else None,
            "nosing_line_at_y-2_m": round(-2.0 / 2.0, 4)}


def ucx():
    out = {}
    for n, o in OBJ.items():
        tops = []
        for ch in o.children:
            tops.append(round(max(v.co.z for v in ch.data.vertices), 4))
        out[n] = {"hulls": len(o.children), "max_top_z": max(tops) if tops else None}
    return out


R = {"batter": {n: batter(n, L, h) for (n, L, h) in (("SM_DKT_Wall_4m_H3", 4, 3), ("SM_DKT_Wall_4m_H6", 4, 6),
                                                      ("SM_DKT_Wall_2m_H2", 2, 2))},
     "coping": {n: coping(n) for n in ("SM_DKT_Wall_4m_H3", "SM_DKT_WallCoping_4m", "SM_DKT_Wall_2m_H6")},
     "seams": seams(),
     "stairs": {str(h): stairs(h) for h in (2, 3, 4)},
     "ucx": ucx(),
     "tris": {n: len(o.data.loop_triangles) if o.data.loop_triangles else sum(len(p.vertices) - 2 for p in o.data.polygons)
              for n, o in OBJ.items()}}
(W / "measure_wall.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
print(json.dumps({k: R[k] for k in ("coping", "seams", "stairs")}, indent=1))
print(json.dumps({n: {k: v for k, v in b.items() if k != "rows"} for n, b in R["batter"].items()}, indent=1))
