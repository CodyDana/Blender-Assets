"""VERIFY r4 (independent verifier), Blender side, read-only. Builds its OWN scene from the exported FBX (Exports/DojoKit)
placed by the layout matrices of layout_showcase.json (nothing of the builder's composed blend is used), then measures
the round-4 buildings against the spec with BVH rays on the RENDER meshes (and on the UCX hulls where the player stands),
the taiko on the pavilion floor, and the ridge stacks (section profile: noshi course lips; ridge-end ornaments).
Also cross-checks that the showcase layout placed every round-4 track instance exactly as the track layouts wrote them.
Run: blender -b --factory-startup --python WorkFiles/dojo/build/verify_r4/v4_measure.py
Out: WorkFiles/dojo/build/verify_r4/measure_buildings.json
"""
import json
import math
import re
from pathlib import Path

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
WORK = ROOT / "WorkFiles" / "dojo" / "build"
OUT = WORK / "verify_r4"
L = json.loads((WORK / "showcase" / "layout_showcase.json").read_text(encoding="utf-8"))
KITS = ("outbuildings", "corridors", "shed", "pavilion", "taiko", "yard")


def strip(n):
    return re.sub(r"\.\d{3}$", "", n)


def import_piece(piece):
    """-> (render mesh datablock baked to the FBX-import frame, [ucx mesh datablocks])"""
    fbx = L["pieces"][piece]["fbx"]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fbx)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    lods = sorted([o for o in meshes if re.search(r"_LOD\d+$", strip(o.name))], key=lambda o: strip(o.name))
    main = lods[0] if lods else next(o for o in meshes if strip(o.name) == piece)
    ucx = [o for o in meshes if strip(o.name).startswith("UCX_")]
    out_r = main.data.copy()
    out_r.transform(main.matrix_world)
    out_c = []
    for u in ucx:
        d = u.data.copy()
        d.transform(u.matrix_world)
        out_c.append(d)
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    return out_r, out_c


def layout_matrix(inst):
    return (Matrix.Translation(Vector(inst["loc"])) @ Euler([math.radians(a) for a in inst["rot_xyz_deg"]], "XYZ").to_matrix().to_4x4()
            @ Matrix.Diagonal(Vector(inst["scale"] + [1.0])))


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    lib = {}
    objs = []
    for n, inst in enumerate(L["instances"]):
        p = inst["piece"]
        if L["pieces"][p]["kit"] not in KITS:
            continue
        if p not in lib:
            lib[p] = import_piece(p)
        r, cs = lib[p]
        mw = layout_matrix(inst)
        o = bpy.data.objects.new(f"R|{p}|{n}", r)
        o.matrix_world = mw
        bpy.context.scene.collection.objects.link(o)
        objs.append(("R", p, n, o))
        for k, c in enumerate(cs):
            oc = bpy.data.objects.new(f"C|{p}|{n}|{k}", c)
            oc.matrix_world = mw
            bpy.context.scene.collection.objects.link(oc)
            objs.append(("C", p, n, oc))
    return objs


def bvh_of(objs):
    verts, polys = [], []
    for o in objs:
        m = o.matrix_world
        base = len(verts)
        verts.extend(m @ v.co for v in o.data.vertices)
        polys.extend([base + i for i in p.vertices] for p in o.data.polygons)
    return BVHTree.FromPolygons(verts, polys, all_triangles=False) if polys else None


def wbox(objs):
    pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    return [round(min(p[i] for p in pts), 4) for i in range(3)] + [round(max(p[i] for p in pts), 4) for i in range(3)]


def down(bvh, x, y, z0=20.0):
    h = bvh.ray_cast(Vector((x, y, z0)), Vector((0, 0, -1)), 40.0)
    return round(h[0].z, 4) if h[0] is not None else None


def up(bvh, x, y, z0):
    h = bvh.ray_cast(Vector((x, y, z0)), Vector((0, 0, 1)), 20.0)
    return round(h[0].z, 4) if h[0] is not None else None


def fit(xs, zs):
    n = len(xs)
    mx, mz = sum(xs) / n, sum(zs) / n
    b = sum((x - mx) * (z - mz) for x, z in zip(xs, zs)) / sum((x - mx) ** 2 for x in xs)
    return mz - b * mx, b


def slope_fit(bvh, axis, fixed, a0, a1, n=40):
    """top-surface z along a line (axis 'x' or 'y'), fitted z = c0 + c1 * t (least squares)."""
    ts, zs = [], []
    for k in range(n + 1):
        t = a0 + (a1 - a0) * k / n
        z = down(bvh, t, fixed) if axis == "x" else down(bvh, fixed, t)
        if z is not None:
            ts.append(t)
            zs.append(z)
    c0, c1 = fit(ts, zs)
    resid = max(abs(z - (c0 + c1 * t)) for t, z in zip(ts, zs))
    return {"c0": c0, "c1": c1, "pitch_deg": round(math.degrees(math.atan(abs(c1))), 3), "n": len(ts),
            "max_resid_m": round(resid, 4), "samples": [[round(t, 3), z] for t, z in zip(ts, zs)][:: max(1, len(ts) // 10)]}


def meet(f1, f2):
    t = (f2["c0"] - f1["c0"]) / (f1["c1"] - f2["c1"])
    return round(t, 4), round(f1["c0"] + f1["c1"] * t, 4)


def at(f, t):
    return round(f["c0"] + f["c1"] * t, 4)


# ------------------------------------------------------------------ track layouts vs the showcase layout
def track_crosscheck():
    src = {"outbuildings": "outbuildings/layout_outbuildings.json", "corridors": "corridors/layout_corridors.json",
           "shed": "shed_pavilion/layout_shed.json", "pavilion": "shed_pavilion/layout_pavilion.json",
           "yard": "props/yard/layout_yard.json", "taiko": "props/taiko/layout_taiko.json"}
    res = {}
    for kit, rel in src.items():
        T = json.loads((WORK / rel).read_text(encoding="utf-8"))
        tins = T.get("instances") or T.get("placements") or []
        sins = [i for i in L["instances"] if L["pieces"][i["piece"]]["kit"] == kit]

        def key(i):
            loc = i.get("loc") or i.get("location")
            rot = i.get("rot_xyz_deg") or i.get("rot_deg") or [0, 0, i.get("rot_z", 0.0)]
            sc = i.get("scale", [1, 1, 1])
            return (i.get("piece") or i.get("name"), tuple(round(v, 4) for v in loc), tuple(round(v, 3) for v in rot),
                    tuple(round(v, 4) for v in sc))
        try:
            tk = sorted(key(i) for i in tins)
            sk = sorted(key(i) for i in sins)
            only_t = [k for k in tk if k not in sk]
            only_s = [k for k in sk if k not in tk]
            res[kit] = {"track_n": len(tk), "showcase_n": len(sk), "only_in_track": only_t[:20], "only_in_showcase": only_s[:20],
                        "match": not only_t and not only_s}
        except Exception as e:  # noqa: BLE001
            res[kit] = {"error": repr(e), "track_keys": list(T.keys())[:20],
                        "sample": (tins[0] if tins else None)}
    return res


# ------------------------------------------------------------------ ridge stack section profile
def section_profile(mesh, axis, frac=0.5, zmin=None):
    """Cut the (local-frame) mesh with the plane normal to `axis` at `frac` of its length; return the silhouette
    half-width w(z) (2 mm bins) about the stack centre and the lips (local maxima of w, prominence >= 3 mm)."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    ai = "xyz".index(axis)
    lo = min(v.co[ai] for v in bm.verts)
    hi = max(v.co[ai] for v in bm.verts)
    c = lo + (hi - lo) * frac
    no = Vector((0, 0, 0))
    no[ai] = 1.0
    co = Vector((0, 0, 0))
    co[ai] = c
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, dist=1e-6)
    cut = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    pi = 1 if ai == 0 else 0     # the across-ridge horizontal coordinate
    segs = [((e.verts[0].co[pi], e.verts[0].co[2]), (e.verts[1].co[pi], e.verts[1].co[2])) for e in cut]
    bm.free()
    if not segs:
        return None
    ztop = max(max(a[1], b[1]) for a, b in segs)
    z0 = zmin if zmin is not None else ztop - 0.6
    # stack centre = midpoint of the extent at the top 5 cm
    top = [p for s in segs for p in s if p[1] > ztop - 0.05]
    cen = (min(p[0] for p in top) + max(p[0] for p in top)) / 2
    prof = []
    z = z0
    while z <= ztop + 1e-9:
        ws = []
        for (a, b) in segs:
            if min(a[1], b[1]) <= z <= max(a[1], b[1]) and abs(a[1] - b[1]) > 1e-9:
                t = (z - a[1]) / (b[1] - a[1])
                ws.append(abs(a[0] + (b[0] - a[0]) * t - cen))
            elif abs(a[1] - z) < 1e-4 and abs(b[1] - z) < 1e-4:
                ws += [abs(a[0] - cen), abs(b[0] - cen)]
        prof.append((round(z, 4), round(max(ws), 4) if ws else None))
        z += 0.002
    # lips: local maxima of w over the window with a dip >= 3 mm on the upper side before the next rise
    lips = []
    vals = [(z, w) for z, w in prof if w is not None]
    for i in range(1, len(vals) - 1):
        z, w = vals[i]
        if w >= vals[i - 1][1] and w > vals[i + 1][1]:
            above = [vv for zz, vv in vals[i + 1: i + 40]]
            if above and w - min(above) >= 0.003:
                if not lips or z - lips[-1][0] > 0.02:
                    lips.append((z, w))
    return {"cut_at": round(c, 3), "axis": axis, "centre": round(cen, 4), "z_top": round(ztop, 4), "z_from": round(z0, 4),
            "lips_z_halfwidth": [[round(z, 4), round(w, 4)] for z, w in lips], "n_lips": len(lips),
            "profile_every_1cm": [p for k, p in enumerate(prof) if k % 5 == 0]}


def end_ornaments(mesh, axis, cap_top):
    """At both ends of the ridge axis (within 0.9 m): the top z and the envelope of the geometry standing above
    cap_top - 0.25 (the ornament block), vs the cap top at mid length."""
    ai = "xyz".index(axis)
    pi = 1 if ai == 0 else 0
    vs = [v.co for v in mesh.vertices]
    lo = min(v[ai] for v in vs)
    hi = max(v[ai] for v in vs)
    out = {}
    for nm, (a, b) in {"end_min": (lo, lo + 0.9), "end_max": (hi - 0.9, hi)}.items():
        sel = [v for v in vs if a <= v[ai] <= b and v[2] > cap_top - 0.25]
        if not sel:
            out[nm] = None
            continue
        out[nm] = {"top_z": round(max(v[2] for v in sel), 4), "above_cap_m": round(max(v[2] for v in sel) - cap_top, 4),
                   "across_m": round(max(v[pi] for v in sel) - min(v[pi] for v in sel), 4),
                   "along_m": round(max(v[ai] for v in sel) - min(v[ai] for v in sel), 4)}
    return out


def ridges():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    spec = {"SM_DKH_RoofUpper_Ridge": None, "SM_DK_Gate_Roof": None, "SM_DKO_Roof_Ridge": None, "SM_DKC_Bay_Roof": None,
            "SM_DKC_EndWall_W_Roof": None, "SM_DKC_EndGable_W_Roof": None}
    res = {}
    for p in spec:
        if p not in L["pieces"]:
            res[p] = {"error": "not in layout"}
            continue
        r, _ = import_piece(p)
        vs = [v.co for v in r.vertices]
        ext = [max(v[i] for v in vs) - min(v[i] for v in vs) for i in range(3)]
        # the ridge axis: the gate / hall ridge pieces run along their longer horizontal extent; corridor / outbuilding
        # pieces as their layouts say (corridor ridge along X; outbuilding ridge N-S = Y)
        axis = "x" if ext[0] >= ext[1] else "y"
        if p.startswith("SM_DKC_"):
            axis = "x"
        if p == "SM_DKO_Roof_Ridge":
            axis = "y" if ext[1] >= ext[0] else "x"
        sp = {f: section_profile(r, axis, f) for f in (0.37, 0.5, 0.63)}
        cap_top = sp[0.5]["z_top"] if sp[0.5] else None
        # loose parts count (tiles are separate shells)
        bm = bmesh.new()
        bm.from_mesh(r)
        seen, parts = set(), 0
        for v in bm.verts:
            if v.index in seen:
                continue
            parts += 1
            stack = [v]
            seen.add(v.index)
            while stack:
                x = stack.pop()
                for e in x.link_edges:
                    o = e.other_vert(x)
                    if o.index not in seen:
                        seen.add(o.index)
                        stack.append(o)
        bm.free()
        res[p] = {"extent_m": [round(e, 4) for e in ext], "axis": axis, "tris": sum(len(q.vertices) - 2 for q in r.polygons),
                  "loose_parts": parts, "sections": sp, "cap_top_mid": cap_top,
                  "ends": end_ornaments(r, axis, cap_top) if cap_top is not None else None}
    return res


def main():
    res = {"track_layouts_vs_showcase": track_crosscheck()}
    objs = build_scene()
    R = {}
    C = {}
    for kind, p, n, o in objs:
        (R if kind == "R" else C).setdefault(p, []).append(o)

    def rb(prefixes, xr=None, coll=R):
        sel = [o for p, os in coll.items() if any(p.startswith(x) for x in prefixes) for o in os]
        if xr:
            sel = [o for o in sel if xr[0] <= (o.matrix_world.translation.x) <= xr[1]]
        return sel

    def mid_x(o):
        return o.matrix_world.translation.x

    ob = {}
    for bname, xr, near_t, far_t, ridge_x in (("storehouse", (-5, 22), 7.6, -1.0, 3.3), ("residence", (22, 50), 36.4, 45.0, 40.7)):
        allo = [o for o in rb(["SM_DKO_"]) if xr[0] <= wbox([o])[0] <= xr[1] or xr[0] <= wbox([o])[3] <= xr[1]]
        allo = [o for o in allo if (wbox([o])[0] + wbox([o])[3]) / 2 > xr[0] and (wbox([o])[0] + wbox([o])[3]) / 2 < xr[1]]
        body = [o for o in allo if re.search(r"_(Wall_[NF]|Gable(Front|Rear))\|", o.name)]
        roof = [o for o in allo if "Roof_" in o.name]
        bv = bvh_of(roof)
        cv = bvh_of([o for o in rb(["SM_DKO_Roof"], coll=C) if xr[0] < (wbox([o])[0] + wbox([o])[3]) / 2 < xr[1]])
        e = {"all_render_box": wbox(allo), "body_box": wbox(body), "roof_box": wbox(roof)}
        for yy in (28.2, 33.5, 35.2):
            sgn = 1 if near_t > far_t else -1
            far = slope_fit(bv, "x", yy, far_t + sgn * 0.35, ridge_x - sgn * 0.45)
            near = slope_fit(bv, "x", yy, ridge_x + sgn * 0.45, near_t - sgn * 0.35) if yy > 32.7 or yy < 29.3 else None
            row = {"far_slope": far, "near_slope": near, "far_eave_z_at_edge": at(far, far_t)}
            if near:
                row["near_eave_z_at_edge"] = at(near, near_t)
                row["planes_meet_render_tile_top"] = meet(far, near)
            row["ridge_top_render"] = down(bv, ridge_x, yy)
            fc = slope_fit(cv, "x", yy, far_t + sgn * 0.35, ridge_x - sgn * 0.45)
            row["far_slope_collision"] = {k: fc[k] for k in ("c0", "c1", "pitch_deg", "max_resid_m")}
            row["far_eave_z_collision_at_edge"] = at(fc, far_t)
            if near:
                nc = slope_fit(cv, "x", yy, ridge_x + sgn * 0.45, near_t - sgn * 0.35)
                row["planes_meet_collision"] = meet(fc, nc)
                row["near_eave_z_collision_at_edge"] = at(nc, near_t)
            e[f"y{yy}"] = row
        ob[bname] = e
    res["outbuildings"] = ob

    co = {}
    for side, xr, xm in (("W", (6, 12), 8.8), ("E", (32, 38), 35.2)):
        allo = [o for o in rb(["SM_DKC_"]) if xr[0] < (wbox([o])[0] + wbox([o])[3]) / 2 < xr[1]]
        roof = [o for o in allo if "Roof" in o.name]
        floor = [o for o in allo if "Floor" in o.name]
        bv, fv = bvh_of(roof), bvh_of(floor)
        cv = bvh_of([o for o in rb(["SM_DKC_"], coll=C) if "Roof" in o.name and xr[0] < (wbox([o])[0] + wbox([o])[3]) / 2 < xr[1]])
        s = slope_fit(bv, "y", xm, 29.6, 30.75)
        n = slope_fit(bv, "y", xm, 31.25, 32.4)
        sc = slope_fit(cv, "y", xm, 29.6, 30.75)
        nc = slope_fit(cv, "y", xm, 31.25, 32.4)
        co[side] = {"all_render_box": wbox(allo), "roof_box": wbox(roof), "floor_box": wbox(floor),
                    "floor_top_mid": down(fv, xm, 31.0), "floor_top_samples": [down(fv, x, y) for x in (xm - 1, xm, xm + 1) for y in (30.0, 31.0, 32.0)],
                    "eave_z_render_at_29p5": at(s, 29.5), "eave_z_render_at_32p5": at(n, 32.5),
                    "planes_meet_render": meet(s, n), "ridge_top_render": down(bv, xm, 31.0),
                    "eave_z_collision_at_29p5": at(sc, 29.5), "planes_meet_collision": meet(sc, nc),
                    "pitch_render": [s["pitch_deg"], n["pitch_deg"]]}
    res["corridors"] = co

    shed = rb(["SM_DKS_"])
    sroof = rb(["SM_DKS_Roof"])
    bv = bvh_of(sroof)
    cv = bvh_of(rb(["SM_DKS_Roof"], coll=C))
    res["shed"] = {"all_render_box": wbox(shed), "roof_box": wbox(sroof),
                   "roof_render_y_profile_x3": [[y / 10, down(bv, 3.0, y / 10)] for y in range(0, 51, 2)],
                   "roof_collision_y_profile_x3": [[y / 10, down(cv, 3.0, y / 10)] for y in range(0, 51, 2)],
                   "floor_box": wbox(rb(["SM_DKS_Floor"]))}

    pav = rb(["SM_DKV_"])
    plinth = rb(["SM_DKV_Plinth"])
    proof = rb(["SM_DKV_RoofQuarter", "SM_DKV_Finial"])
    pv = bvh_of(plinth)
    rv = bvh_of(rb(["SM_DKV_RoofQuarter"]))
    rc = bvh_of(rb(["SM_DKV_RoofQuarter"], coll=C))
    allpav = bvh_of(pav)
    fx1 = slope_fit(rv, "x", 3.0, 38.5, 40.6)
    fx2 = slope_fit(rv, "x", 3.0, 41.4, 43.5)
    fy1 = slope_fit(rv, "y", 41.0, 0.5, 2.6)
    fy2 = slope_fit(rv, "y", 41.0, 3.4, 5.5)
    cx1 = slope_fit(rc, "x", 3.0, 38.5, 40.6)
    cx2 = slope_fit(rc, "x", 3.0, 41.4, 43.5)
    res["pavilion"] = {"all_render_box": wbox(pav), "plinth_box": wbox(plinth), "roof_box": wbox(proof),
                       "plinth_top_samples": [down(pv, x, y) for x in (39.2, 41.0, 42.8) for y in (1.2, 3.0, 4.8)],
                       "eave_z_render_x38p4": at(fx1, 38.4), "eave_z_render_x43p6": at(fx2, 43.6),
                       "eave_z_render_y0p4": at(fy1, 0.4), "eave_z_render_y5p6": at(fy2, 5.6),
                       "apex_planes_meet_render_x": meet(fx1, fx2), "apex_planes_meet_render_y": meet(fy1, fy2),
                       "eave_z_collision_x38p4": at(cx1, 38.4), "apex_planes_meet_collision_x": meet(cx1, cx2),
                       "finial_top": wbox(rb(["SM_DKV_Finial"]))[5], "pitch_render": [fx1["pitch_deg"], fy1["pitch_deg"]]}

    # taiko on the pavilion floor
    tk = rb(["SM_DKP_Taiko_"])
    stand = rb(["SM_DKP_Taiko_Stand"])
    drum = rb(["SM_DKP_Taiko_Drum"])
    sb, db, tb = wbox(stand), wbox(drum), wbox(tk)
    # feet: stand vertices within 1 cm of its lowest z; the plinth surface under each
    lowz = sb[2]
    feet = [o.matrix_world @ v.co for o in stand for v in o.data.vertices if (o.matrix_world @ v.co).z < lowz + 0.01]
    gaps = []
    for pnt in feet[:: max(1, len(feet) // 40)]:
        s = down(pv, pnt.x, pnt.y, pnt.z + 0.5)
        gaps.append(round(pnt.z - s, 4) if s is not None else None)
    cxy = ((db[0] + db[3]) / 2, (db[1] + db[4]) / 2)
    above_drum = up(bvh_of([o for o in pav]), cxy[0], cxy[1], db[5] + 0.001)
    res["taiko"] = {"stand_box": sb, "drum_box": db, "taiko_box": tb, "stand_lowest_z": lowz,
                    "feet_minus_plinth_surface_m": gaps, "n_feet_samples": len(gaps),
                    "drum_top_z": db[5], "taiko_top_z": tb[5], "first_pavilion_surface_above_drum_centre": above_drum,
                    "inside_plinth_xy": tb[0] >= 39.0 and tb[3] <= 43.0 and tb[1] >= 1.0 and tb[4] <= 5.0}
    res["ridges"] = ridges()
    OUT.joinpath("measure_buildings.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("V4_MEASURE_DONE")


main()
