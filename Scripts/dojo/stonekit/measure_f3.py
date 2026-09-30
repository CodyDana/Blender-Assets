"""Stone kit FIX ROUND 3 (f3; measure_f2.py writing f3_measure.json). From f2 (from measure_f1.py): measure the judge's numbers on the built pieces (read-only on Assets/Dojo/DojoStoneKit.blend).

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
        return 0.10 * s                     # f2: the straight 1:10 default profile
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
        for x in (-0.55, -0.12, 0.33):
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
# ---------------------------------------------------------------- f2 additions
if w:                                   # the batter: the stone fronts' mean set-back per 0.5 m of depth (rays from -Y)
    t, mats = bvh_of(w)
    st = slots(w, {"M_DKT_WallGranite"})
    prof = []
    for k in range(1, 7):
        z = -0.40 - 0.45 * k
        ys = []
        for i in range(160):
            h = t.ray_cast(Vector((0.3 + 0.022 * i, -3.0, z)), Vector((0, 1, 0)), 9.0)
            if h[0] is not None and mats[h[2]] in st:
                ys.append(h[0].y)
        ys.sort()
        if ys:
            prof.append((round(-z, 3), round(-ys[len(ys) // 10], 4)))     # the proud 10 %: the crowns
    import math as _m
    sl = [(prof[i + 1][1] - prof[i][1]) / (prof[i + 1][0] - prof[i][0]) for i in range(len(prof) - 1)]
    res["wall_4m_H3_batter"] = {"crown_setback_by_depth_m": prof,
                                "slope_per_m": [round(x, 4) for x in sl],
                                "fit_slope_first_to_last": round((prof[-1][1] - prof[0][1]) / (prof[-1][0] - prof[0][0]), 4),
                                "mean_batter": "1:%.1f" % ((prof[-1][0] - prof[0][0]) / max(1e-6, prof[-1][1] - prof[0][1])),
                                "face_angle_from_vertical_deg": round(_m.degrees(_m.atan(
                                    (prof[-1][1] - prof[0][1]) / (prof[-1][0] - prof[0][0]))), 2)}
    # stone sizes: the face stones' outline boxes (width, height) from the mesh parts' front vertices
    import bmesh as _bm
    bm = _bm.new()
    bm.from_mesh(w.data)
    bm.faces.ensure_lookup_table()
    seen, parts = set(), []
    for f in bm.faces:
        if f.index in seen or f.material_index not in st:
            continue
        stack, comp = [f], set()
        while stack:
            q = stack.pop()
            if q.index in comp:
                continue
            comp.add(q.index)
            for e in q.edges:
                for q2 in e.link_faces:
                    if q2.index not in comp and q2.material_index in st:
                        stack.append(q2)
        seen |= comp
        vs = {v for i in comp for v in bm.faces[i].verts}
        xs_ = [v.co.x for v in vs]
        zs_ = [v.co.z for v in vs]
        wd, ht = max(xs_) - min(xs_), max(zs_) - min(zs_)
        if min(zs_) > -0.30 or wd > 1.5:
            continue
        parts.append((wd, ht))
    bm.free()
    asp = sorted(h_ / w_ for w_, h_ in parts if w_ > 0.05)
    res["wall_4m_H3_stones"] = {"n": len(parts), "width_m": {"p10": pct([p[0] for p in parts], 0.1),
                                                           "median": pct([p[0] for p in parts], 0.5),
                                                           "p90": pct([p[0] for p in parts], 0.9)},
                                "height_m": {"p10": pct([p[1] for p in parts], 0.1),
                                             "median": pct([p[1] for p in parts], 0.5),
                                             "p90": pct([p[1] for p in parts], 0.9)},
                                "upright_share_h_gt_w": round(sum(1 for a in asp if a > 1.05) / max(1, len(asp)), 3),
                                "long_share_w_gt_1.6h": round(sum(1 for a in asp if a < 1 / 1.6) / max(1, len(asp)), 3)}
ft = OBJ.get("SM_DKT_WallFoot_4m")
if ft:
    t, mats = bvh_of(ft)
    tops = []
    for i in range(80):
        h = t.ray_cast(Vector((0.02 + 0.05 * i, -0.02, 2.0)), Vector((0, 0, -1)), 9.0)
        if h[0] is not None and h[0].z > 0.0:
            tops.append(h[0].z)
    res["wallfoot_4m_course_top_m"] = {"min": round(min(tops), 4), "max": round(max(tops), 4), "samples": len(tops),
                                       "note": "rays through the 1.4-2 cm joints drop below 0 and are excluded"}
for kn in ("SM_DKT_Stair_Kerb_L180", "SM_DKT_Stair_Cheek_Low_R100", "SM_DKT_Stair_Cheek_R100"):
    o = OBJ.get(kn)
    if not o:
        continue
    t, mats = bvh_of(o)
    tops = []
    for i in range(30):
        y = 0.03 + (o.dimensions.y - 0.06) * i / 29
        h = t.ray_cast(Vector((0.0, y, 5.0)), Vector((0, 0, -1)), 12.0)
        if h[0] is not None:
            tr = (y // (1 / 3) + 1) / 6 if "Cheek_" in kn and "_R" in kn else 0.0
            tops.append(round(h[0].z - tr, 4))
    res[kn.replace("SM_DKT_Stair_", "") + "_top_over_walk_m"] = {"min": min(tops), "max": max(tops)}
rs = OBJ.get("SM_DKT_Stair_Rail_Slope_R100")
if rs:
    res["rail_slope_R100"] = {"dims_m": [round(x, 3) for x in rs.dimensions],
                              "slots": [m.name for m in rs.data.materials]}
# walkability measured on the meshes: nosing-to-nosing treads and centre-line risers (flights + the wall's opening)
for fn in ("SM_DKT_Stair_Flight_W120_R050", "SM_DKT_Stair_Flight_W180_R100", "SM_DKT_Stair_Flight_W180_R200"):
    o = OBJ.get(fn)
    if not o:
        continue
    t, mats = bvh_of(o)
    n = round(o.dimensions.z) if False else int(round((max(v.co.z for v in o.data.vertices)) / (1 / 6)))
    noses, tops = [], []
    for i in range(n):
        zt = (i + 1) / 6
        hs = []
        for x in (-0.31, 0.07, 0.29):
            h = t.ray_cast(Vector((x, i / 3 - 0.6, zt - 0.012)), Vector((0, 1, 0)), 2.0)
            if h[0] is not None:
                hs.append(h[0].y)
            h2 = t.ray_cast(Vector((x, i / 3 + 0.16, zt + 1.0)), Vector((0, 0, -1)), 3.0)
            if h2[0] is not None:
                tops.append((i, h2[0].z))
        if hs:
            noses.append(sum(hs) / len(hs))
    tr = [round(b_ - a_, 4) for a_, b_ in zip(noses, noses[1:])]
    import statistics as _st
    zs = {}
    for i, z in tops:
        zs.setdefault(i, []).append(z)
    lv = [_st.mean(zs[i]) for i in sorted(zs)]
    rs = [round(lv[0], 4)] + [round(b_ - a_, 4) for a_, b_ in zip(lv, lv[1:])]
    res[fn.replace("SM_DKT_Stair_", "") + "_walk"] = {"tread_nosing_to_nosing_m": {"min": min(tr), "max": max(tr)},
                                                      "riser_m": {"min": min(rs), "max": max(rs)}}
so = OBJ.get("SM_DKT_Wall_StairOpening_H3")
if so:
    t, mats = bvh_of(so)
    lv = []
    for i in range(1, 18):
        zs_ = []
        for x in [1.25 + 0.1 * k for k in range(16)]:
            h = t.ray_cast(Vector((x, -i / 3 + 0.16, 2.0)), Vector((0, 0, -1)), 9.0)
            if h[0] is not None:
                zs_.append(h[0].z)
        zs_.sort()
        lv.append(zs_[len(zs_) // 2])                  # the median: a ray down an end joint is not the tread
    rs = [round(a_ - b_, 4) for a_, b_ in zip(lv, lv[1:])]
    res["Wall_StairOpening_H3_walk"] = {"riser_m": {"min": min(rs), "max": max(rs)}, "tread_m": round(1 / 3, 4)}
# ---------------------------------------------------------------- f2 round 2 (STONE_BUILDING_STUDY 4.13 / 4.14 / SG17)
vt = {n: round(len(o.data.vertices) / max(1, sum(len(q.vertices) - 2 for q in o.data.polygons)), 3)
      for n, o in OBJ.items() if o.parent is None and not n.startswith("UCX_")}
res["verts_per_tri"] = {"max": max(vt.values()), "median": sorted(vt.values())[len(vt) // 2], "n": len(vt),
                        "worst": sorted(vt.items(), key=lambda kv: -kv[1])[:5]}
walk = {"target": {"riser_m": [0.15, 0.18], "tread_m_min": 0.30, "ramp_deg_max": 44.77, "max_step_m": 0.45}}
ok = True
for k, v in res.items():
    if k.endswith("_walk"):
        rr, tt = v["riser_m"], v.get("tread_nosing_to_nosing_m", {"min": v.get("tread_m")})
        good = 0.15 <= rr["min"] and rr["max"] <= 0.18 and tt["min"] >= 0.30
        walk[k] = {"riser_m": rr, "tread_m_min": tt["min"], "pass": good}
        ok &= good
smp = SK / "stairs" / "measure.json"
if smp.exists():
    sm = json.loads(smp.read_text(encoding="utf-8"))
    ramps = {k.replace("SM_DKT_Stair_", ""): v.get("ucx_ramp_deg") for k, v in sm.items() if v.get("ucx_ramp_deg")}
    walk["ucx_ramp_deg"] = ramps
    rmax = max((max(r) if isinstance(r, list) else r) for r in ramps.values()) if ramps else None
    walk["ucx_ramp_pass"] = rmax is not None and rmax < 44.77
    ok &= bool(walk["ucx_ramp_pass"])
walk["pass"] = bool(ok)
res["walkability"] = walk
out = SK / "f3_measure.json"
out.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
