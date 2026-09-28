"""UnrealCheck8: compare Unreal's re-export of each SAVED asset (p4_export.py) with the shipped FBX (headless Blender).

  blender.exe -b --factory-startup --python-exit-code 3 --python b2_roundtrip.py

Per form:
  R1 hull: the stored hull Unreal exported equals the shipped UCX_<node>_00 - same unique vertex count, same
     triangle count, two-sided vertex distance, same volume; LOD0 (shipped AND Unreal's) max distance outside it
  R2 per LOD: triangle count, two-sided position distance, UV0-keyed handedness check (every Unreal loop's
     (position, UV0) pair exists in the shipped LOD and vice versa)
  R3 UV1 (Unreal's generated lightmap, render data): strictly inside 0-1; EXACT pairwise triangle overlap area
     (convex clipping, shared edges give 0); plus, informational, texels at the asset's lightmap resolution
     sampled by more than one UV1 chart
Writes roundtrip_compare.json. Saves nothing.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils.kdtree import KDTree

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck8"
FORMS = {"four_point": "SM_Shuriken_FourPoint", "eight_point": "SM_Shuriken_EightPoint",
         "square_plate": "SM_Shuriken_SquarePlate", "six_point": "SM_Shuriken_SixPoint",
         "spike": "SM_Shuriken_Spike"}
P3 = json.loads((HERE / "p3_readback.json").read_text(encoding="utf-8"))


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        me = ob.data
        me.calc_loop_triangles()
        mw = ob.matrix_world
        verts = [tuple(c * 100.0 for c in (mw @ v.co)) for v in me.vertices]
        uvs = {}
        for uv in me.uv_layers:
            uvs[uv.name] = [tuple(d.uv) for d in uv.data]
        out[ob.name] = {
            "verts": verts,
            "tris": [tuple(t.vertices) for t in me.loop_triangles],
            "tri_loops": [tuple(t.loops) for t in me.loop_triangles],
            "loop_vert": [l.vertex_index for l in me.loops],
            "uv_names": [uv.name for uv in me.uv_layers],
            "uvs": uvs,
        }
    return out


def kd(points):
    t = KDTree(len(points))
    for i, p in enumerate(points):
        t.insert(p, i)
    t.balance()
    return t


def two_sided(a, b):
    ka, kb = kd(a), kd(b)
    return max(max(kb.find(p)[2] for p in a), max(ka.find(p)[2] for p in b))


def uv0_keyed(s, b, pos_tol=1e-4):
    """Every (position, UV0) loop of one mesh must exist in the other: a mirrored or rotated import moves UV0.

    Unreal's render data stores UVs as 16-bit floats (Use Full Precision UVs is off by default) and its FBX
    exporter writes V as 1 - v, so a faithful round trip moves each UV axis by at most half a float16 ulp:
    2^-12 = 0.000244 for values below 1 (0.5 texel at 2048). A mirror or rotation moves UV0 by ~0.1 or more.
    """
    half_ulp = 2.0 ** -12 + 1e-6

    def pairs(m):
        uv = m["uvs"][m["uv_names"][0]]
        return [(m["verts"][m["loop_vert"][li]], uv[li]) for li in range(len(m["loop_vert"]))]
    ps, pb = pairs(s), pairs(b)

    def one(src, dst):
        tree = kd([p for p, _ in dst])
        worst_uv, worst_du, worst_dv, unmatched = 0.0, 0.0, 0.0, 0
        for p, uv in src:
            best = None
            for (_, idx, dist) in tree.find_range(p, pos_tol):
                q = dst[idx][1]
                cand = (math.hypot(uv[0] - q[0], uv[1] - q[1]), abs(uv[0] - q[0]), abs(uv[1] - q[1]))
                best = cand if best is None or cand[0] < best[0] else best
            if best is None:
                unmatched += 1
                continue
            worst_uv, worst_du, worst_dv = max(worst_uv, best[0]), max(worst_du, best[1]), max(worst_dv, best[2])
        return {"loops": len(src), "no_position_match": unmatched, "worst_uv0_delta": worst_uv,
                "worst_du": worst_du, "worst_dv": worst_dv}
    a, c = one(pb, ps), one(ps, pb)
    ue_uv = b["uvs"][b["uv_names"][0]]
    return {"unreal_to_shipped": a, "shipped_to_unreal": c, "half_ulp_bound": half_ulp,
            "unreal_u_float16_exact_fraction": sum(float(np.float16(u)) == u for u, _ in ue_uv) / len(ue_uv),
            "unreal_one_minus_v_float16_exact_fraction": sum(float(np.float16(np.float32(1.0) - np.float32(v))) == float(np.float32(1.0) - np.float32(v)) for _, v in ue_uv) / len(ue_uv),
            "ok_position_and_handedness": a["no_position_match"] == 0 and c["no_position_match"] == 0
            and max(a["worst_du"], a["worst_dv"], c["worst_du"], c["worst_dv"]) <= half_ulp}


# ---- convex hull helpers (double precision) ----
def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def hull_planes(m):
    vs = m["verts"]
    cen = tuple(sum(v[i] for v in vs) / len(vs) for i in range(3))
    planes = []
    for (i, j, k) in m["tris"]:
        n = cross(sub(vs[j], vs[i]), sub(vs[k], vs[i]))
        ln = math.sqrt(dot(n, n))
        if ln < 1e-12:
            continue
        n = (n[0] / ln, n[1] / ln, n[2] / ln)
        if dot(n, sub(cen, vs[i])) > 0:
            n = (-n[0], -n[1], -n[2])
        planes.append((n, vs[i]))
    return planes, cen


def max_outside(planes, pts):
    return max(max(dot(n, sub(p, a)) for n, a in planes) for p in pts)


def volume(m):
    vs = m["verts"]
    cen = tuple(sum(v[i] for v in vs) / len(vs) for i in range(3))
    return sum(abs(dot(sub(vs[i], cen), cross(sub(vs[j], cen), sub(vs[k], cen)))) / 6.0 for i, j, k in m["tris"])


def unique(vs, nd=5):
    return sorted({tuple(round(c, nd) + 0.0 for c in v) for v in vs})


# ---- UV1 overlap ----
def tri_area(a, b, c):
    return 0.5 * ((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))


def ccw(t):
    return t if tri_area(*t) > 0 else (t[0], t[2], t[1])


def clip(subject, clipper):
    out = list(subject)
    n = len(clipper)
    for i in range(n):
        a, b = clipper[i], clipper[(i + 1) % n]
        inp, out = out, []
        if not inp:
            break

        def inside(p):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

        def inter(p, q):
            x1, y1, x2, y2 = p[0], p[1], q[0], q[1]
            x3, y3, x4, y4 = a[0], a[1], b[0], b[1]
            den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if abs(den) < 1e-30:
                return q
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        s = inp[-1]
        for e in inp:
            if inside(e):
                if not inside(s):
                    out.append(inter(s, e))
                out.append(e)
            elif inside(s):
                out.append(inter(s, e))
            s = e
    return out


def poly_area(p):
    return 0.5 * abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))))


def uv1_overlap(m, res, tris=None):
    if tris is None:
        uv = m["uvs"][m["uv_names"][1]]
        tris = [ccw(tuple(uv[li] for li in tl)) for tl in m["tri_loops"]]
    us = [c[0] for t in tris for c in t]
    vs = [c[1] for t in tris for c in t]
    boxes = [(min(p[0] for p in t), max(p[0] for p in t), min(p[1] for p in t), max(p[1] for p in t)) for t in tris]
    order = sorted(range(len(tris)), key=lambda i: boxes[i][0])
    pairs, total, worst, over_pairs = 0, 0.0, 0.0, 0
    active = []
    eps = 1e-12
    for i in order:
        bi = boxes[i]
        active = [j for j in active if boxes[j][1] > bi[0] + eps]
        for j in active:
            bj = boxes[j]
            if bj[2] >= bi[3] - eps or bi[2] >= bj[3] - eps:
                continue
            pairs += 1
            poly = clip(tris[i], tris[j])
            if len(poly) >= 3:
                a = poly_area(poly)
                if a > 1e-12:
                    over_pairs += 1
                    total += a
                    worst = max(worst, a)
        active.append(i)
    # charts (connected by shared UV1 corners) and texel sharing at the lightmap resolution
    parent = list(range(len(tris)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    corner = {}
    for ti, t in enumerate(tris):
        for c in t:
            k = (round(c[0], 6), round(c[1], 6))
            if k in corner:
                parent[find(ti)] = find(corner[k])
            else:
                corner[k] = ti
    owner = {}
    shared = set()
    for ti, t in enumerate(tris):
        a, b, c = t
        minx = max(int(math.floor(min(a[0], b[0], c[0]) * res)), 0)
        maxx = min(int(math.ceil(max(a[0], b[0], c[0]) * res)), res)
        miny = max(int(math.floor(min(a[1], b[1], c[1]) * res)), 0)
        maxy = min(int(math.ceil(max(a[1], b[1], c[1]) * res)), res)
        ch = find(ti)
        for y in range(miny, maxy):
            py = (y + 0.5) / res
            for x in range(minx, maxx):
                px = (x + 0.5) / res
                w0 = tri_area(b, c, (px, py))
                w1 = tri_area(c, a, (px, py))
                w2 = tri_area(a, b, (px, py))
                if w0 >= 0 and w1 >= 0 and w2 >= 0:
                    prev = owner.setdefault((x, y), ch)
                    if prev != ch:
                        shared.add((x, y))
    return {"u_range": [min(us), max(us)], "v_range": [min(vs), max(vs)],
            "strictly_inside_0_1": min(us) > 0 and min(vs) > 0 and max(us) < 1 and max(vs) < 1,
            "candidate_pairs": pairs, "overlapping_pairs": over_pairs, "overlap_area_total": total,
            "overlap_area_max": worst, "flipped_or_zero_triangles": sum(1 for t in tris if abs(tri_area(*t)) < 1e-14),
            "charts": len({find(i) for i in range(len(tris))}), "lightmap_res": res,
            "texels_sampled_by_two_charts": len(shared)}


def main():
    result = {}
    for form, mesh in FORMS.items():
        ue_fbx = HERE / "roundtrip" / f"{mesh}_from_unreal.fbx"
        shipped = load(PROJ / "Exports" / "Shuriken" / f"{mesh}.fbx")
        back = load(ue_fbx)
        res = int(P3["forms"][form]["info"]["light_map_resolution"])
        rec = {"unreal_export": str(ue_fbx), "unreal_nodes": sorted(back), "shipped_nodes": sorted(shipped), "lods": {}}
        back_lods = sorted((k for k in back if not k.startswith("UCX_")), key=lambda k: -len(back[k]["tris"]))
        for i in range(3):
            s = shipped[f"{mesh}_LOD{i}"]
            b = back[back_lods[i]]
            e = {"unreal_node": back_lods[i], "shipped_tris": len(s["tris"]), "unreal_tris": len(b["tris"]),
                 "unreal_uv_channels": b["uv_names"], "shipped_uv_channels": s["uv_names"],
                 "position_two_sided_max_cm": two_sided(s["verts"], b["verts"]),
                 "uv0_keyed": uv0_keyed(s, b)}
            if len(b["uv_names"]) >= 2:
                e["uv1"] = uv1_overlap(b, res)
                if i == 0:
                    # negative control: the same UV1 plus one copy of its first triangle moved by a quarter texel
                    # must report exactly one overlapping pair and a shared texel set, or the checker is blind
                    uv = b["uvs"][b["uv_names"][1]]
                    tris = [ccw(tuple(uv[li] for li in tl)) for tl in b["tri_loops"]]
                    d = 0.25 / res
                    extra = ccw(tuple((c[0] + d, c[1] + d) for c in tris[0]))
                    ctl = uv1_overlap(b, res, tris + [extra])
                    e["uv1_negative_control"] = {"overlapping_pairs": ctl["overlapping_pairs"],
                                                 "overlap_area_total": ctl["overlap_area_total"],
                                                 "detects": ctl["overlapping_pairs"] >= 1}
            rec["lods"][f"LOD{i}"] = e
        ship_h = [k for k in shipped if k.startswith("UCX_")]
        back_h = [k for k in back if k.startswith("UCX_")]
        rec["shipped_hull_nodes"], rec["unreal_hull_nodes"] = ship_h, back_h
        if len(ship_h) == 1 and len(back_h) == 1:
            sh, bh = shipped[ship_h[0]], back[back_h[0]]
            planes, _ = hull_planes(bh)
            splanes, _ = hull_planes(sh)
            us, ub = unique(sh["verts"]), unique(bh["verts"])
            rec["hull"] = {
                "shipped": {"node": ship_h[0], "unique_verts": len(us), "tris": len(sh["tris"]), "volume_cm3": volume(sh)},
                "unreal": {"node": back_h[0], "unique_verts": len(ub), "tris": len(bh["tris"]), "volume_cm3": volume(bh)},
                "vertex_sets_equal_1e-5cm": us == ub,
                "two_sided_vertex_distance_cm": two_sided(sh["verts"], bh["verts"]),
                "lod0_shipped_max_outside_unreal_hull_cm": max_outside(planes, shipped[f"{mesh}_LOD0"]["verts"]),
                "lod0_unreal_max_outside_unreal_hull_cm": max_outside(planes, back[back_lods[0]]["verts"]),
                "lod0_shipped_max_outside_shipped_hull_cm": max_outside(splanes, shipped[f"{mesh}_LOD0"]["verts"]),
                "lod1_2_unreal_max_outside_unreal_hull_cm": max(max_outside(planes, back[back_lods[i]]["verts"]) for i in (1, 2)),
            }
        result[form] = rec
    (HERE / "roundtrip_compare.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("UC8_ROUNDTRIP_DONE")


main()
