"""UnrealCheck11: compare Unreal's re-export of the SAVED hooked-cross asset (u5_export.py) with the shipped FBX.
Headless Blender, saves nothing:

    blender.exe -b --factory-startup --python-exit-code 3 --python b2_roundtrip.py

  R1 hull   exactly one UCX node on each side; unique vertex sets equal (1e-5 cm), same triangle count, two-sided
            vertex distance, same volume; max distance of every LOD (shipped and Unreal's) OUTSIDE Unreal's stored hull
  R2 LODs   per LOD: triangle count, two-sided position distance, (position, UV0) pairs matched both ways within the
            float16 half-ulp Unreal's render data allows, loop normals matched both ways
  R3 UV1    Unreal's generated lightmap UVs per LOD: all inside [0, 1]; exact pairwise triangle-overlap area by
            convex clipping (shared edges give 0); a negative control (the largest triangle duplicated a quarter texel
            away) must be detected; informational: texels at the asset's lightmap resolution hit by two charts
  R4 hand   what a viewer above / below each re-exported LOD sees, read by hc_chirality (Blender frame, right-handed:
            the round trip Blender -> Unreal -> Blender must come back left-facing on +Z)
Writes b2_roundtrip.json.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils.kdtree import KDTree

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck11_HookedCrossVerify"
sys.path.insert(0, str(HERE))
import hc_chirality as HC  # noqa: E402

MESH = "SM_Shuriken_HookedCross"
SHIPPED = PROJ / "Exports" / "Shuriken" / f"{MESH}.fbx"
BACK = HERE / "roundtrip" / f"{MESH}_from_unreal.fbx"
U3 = json.loads((HERE / "u3_readback.json").read_text(encoding="utf-8"))
TOP = ((0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
BOTTOM = ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, -1.0, 0.0))


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
        out[ob.name] = {
            "verts": [tuple(c * 100.0 for c in (mw @ v.co)) for v in me.vertices],   # cm, Blender axes
            "tris": [tuple(t.vertices) for t in me.loop_triangles],
            "tri_loops": [tuple(t.loops) for t in me.loop_triangles],
            "loop_vert": [lp.vertex_index for lp in me.loops],
            "uv_names": [uv.name for uv in me.uv_layers],
            "uvs": {uv.name: [tuple(d.uv) for d in uv.data] for uv in me.uv_layers},
            "loop_normals": [tuple((mw.to_3x3() @ n.vector).normalized()) for n in me.corner_normals],
            "parent": ob.parent.name if ob.parent else None,
            "det": mw.to_3x3().determinant(),
        }
    return out, sorted((o.name, o.type, o.parent.name if o.parent else None,
                        round(o.matrix_world.to_3x3().determinant(), 9)) for o in bpy.data.objects)


def kd(points):
    t = KDTree(len(points))
    for i, p in enumerate(points):
        t.insert(p, i)
    t.balance()
    return t


def two_sided(a, b):
    ka, kb = kd(a), kd(b)
    return max(max(kb.find(p)[2] for p in a), max(ka.find(p)[2] for p in b))


def uv0_pairs_match(s, b, pos_tol=1e-4):
    half_ulp = 2.0 ** -12 + 1e-6

    def pairs(m):
        uv = m["uvs"][m["uv_names"][0]]
        return [(m["verts"][m["loop_vert"][li]], uv[li]) for li in range(len(m["loop_vert"]))]

    def one(src, dst):
        tree = kd([p for p, _ in dst])
        worst, unmatched = 0.0, 0
        for p, uv in src:
            best = None
            for (_, idx, _) in tree.find_range(p, pos_tol):
                q = dst[idx][1]
                d = max(abs(uv[0] - q[0]), abs(uv[1] - q[1]))
                best = d if best is None or d < best else best
            if best is None:
                unmatched += 1
            else:
                worst = max(worst, best)
        return {"loops": len(src), "no_position_match": unmatched, "worst_uv0_axis_delta": worst}
    a, c = one(pairs(b), pairs(s)), one(pairs(s), pairs(b))
    return {"unreal_to_shipped": a, "shipped_to_unreal": c, "half_ulp_bound": half_ulp,
            "ok": a["no_position_match"] == 0 and c["no_position_match"] == 0
            and max(a["worst_uv0_axis_delta"], c["worst_uv0_axis_delta"]) <= half_ulp}


def planes(m):
    vs = m["verts"]
    cen = tuple(sum(v[i] for v in vs) / len(vs) for i in range(3))
    out = []
    for i, j, k in m["tris"]:
        n = HC.cross(HC.sub(vs[j], vs[i]), HC.sub(vs[k], vs[i]))
        ln = math.sqrt(HC.dot(n, n))
        if ln < 1e-14:
            continue
        n = (n[0] / ln, n[1] / ln, n[2] / ln)
        if HC.dot(n, HC.sub(cen, vs[i])) > 0:
            n = (-n[0], -n[1], -n[2])
        out.append((n, vs[i]))
    return out


def max_outside(pl, pts):
    return max(max(HC.dot(n, HC.sub(p, a)) for n, a in pl) for p in pts)


def volume(m):
    vs = m["verts"]
    return abs(sum(HC.dot(vs[i], HC.cross(vs[j], vs[k])) for i, j, k in m["tris"]) / 6.0)


def unique(vs, nd=5):
    return sorted({tuple(round(c, nd) + 0.0 for c in v) for v in vs})


# ------------------------------------------------------------------ UV1 overlap
def area2(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])


def ccw(t):
    return t if area2(*t) > 0 else (t[0], t[2], t[1])


def clip(subject, clipper):
    out = list(subject)
    for i in range(3):
        a, b = clipper[i], clipper[(i + 1) % 3]
        inp, out = out, []
        if not inp:
            break

        def inside(p):
            return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

        def inter(p, q):
            den = (p[0] - q[0]) * (a[1] - b[1]) - (p[1] - q[1]) * (a[0] - b[0])
            if abs(den) < 1e-30:
                return q
            t = ((p[0] - a[0]) * (a[1] - b[1]) - (p[1] - a[1]) * (a[0] - b[0])) / den
            return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))
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


def uv1_check(tris, res):
    us = [c[0] for t in tris for c in t]
    vs = [c[1] for t in tris for c in t]
    over_pairs, total, worst, pairs = 0, 0.0, 0.0, 0
    for i in range(len(tris)):
        for j in range(i + 1, len(tris)):
            a, b = tris[i], tris[j]
            if (max(p[0] for p in a) <= min(p[0] for p in b) or max(p[0] for p in b) <= min(p[0] for p in a)
                    or max(p[1] for p in a) <= min(p[1] for p in b) or max(p[1] for p in b) <= min(p[1] for p in a)):
                continue
            pairs += 1
            poly = clip(a, b)
            if len(poly) >= 3:
                ar = poly_area(poly)
                if ar > 1e-12:
                    over_pairs += 1
                    total += ar
                    worst = max(worst, ar)
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
    owner, shared = {}, set()
    for ti, (a, b, c) in enumerate(tris):
        ch = find(ti)
        for y in range(max(int(math.floor(min(a[1], b[1], c[1]) * res)), 0), min(int(math.ceil(max(a[1], b[1], c[1]) * res)), res)):
            for x in range(max(int(math.floor(min(a[0], b[0], c[0]) * res)), 0), min(int(math.ceil(max(a[0], b[0], c[0]) * res)), res)):
                p = ((x + 0.5) / res, (y + 0.5) / res)
                if area2(b, c, p) >= 0 and area2(c, a, p) >= 0 and area2(a, b, p) >= 0:
                    if owner.setdefault((x, y), ch) != ch:
                        shared.add((x, y))
    return {"u_range": [min(us), max(us)], "v_range": [min(vs), max(vs)],
            "inside_0_1": min(us) >= 0.0 and min(vs) >= 0.0 and max(us) <= 1.0 and max(vs) <= 1.0,
            "bbox_candidate_pairs": pairs, "overlapping_pairs": over_pairs, "overlap_area_total": total,
            "overlap_area_max": worst, "zero_area_triangles": sum(1 for t in tris if abs(area2(*t)) < 1e-14),
            "charts": len({find(i) for i in range(len(tris))}), "lightmap_res": res,
            "texels_claimed_by_two_charts": len(shared),
            "uv1_area_fraction": sum(abs(area2(*t)) / 2.0 for t in tris)}


def uv1_tris(m):
    uv = m["uvs"][m["uv_names"][1]]
    return [ccw(tuple(uv[li] for li in tl)) for tl in m["tri_loops"]]


def normals_match(s, b, pos_tol=1e-4):
    def one(src, dst):
        tree = kd(dst["verts"])
        by_vert = {}
        for li, vi in enumerate(dst["loop_vert"]):
            by_vert.setdefault(vi, []).append(dst["loop_normals"][li])
        worst = 0.0
        for li, vi in enumerate(src["loop_vert"]):
            n = src["loop_normals"][li]
            best = 180.0
            for (_, idx, _) in tree.find_range(src["verts"][vi], pos_tol):
                for m in by_vert.get(idx, []):
                    best = min(best, math.degrees(math.acos(max(-1.0, min(1.0, HC.dot(n, m))))))
            worst = max(worst, best)
        return worst
    return {"unreal_to_shipped_max_deg": one(b, s), "shipped_to_unreal_max_deg": one(s, b)}


def hand(m):
    vmm = [tuple(c * 10.0 for c in v) for v in m["verts"]]
    fn = [HC.winding_normal(vmm[i], vmm[j], vmm[k], "blender") for i, j, k in m["tris"]]
    agree = sum(1 for tl, n in zip(m["tri_loops"], fn)
                if HC.dot(n, tuple(sum(m["loop_normals"][li][c] for li in tl) for c in range(3))) > 0)
    out = {"winding_agrees_with_normals": agree, "triangles": len(m["tris"]), "matrix_det": m["det"]}
    for name, (f, r, u) in (("viewer_above_plus_z", TOP), ("viewer_below_minus_z", BOTTOM)):
        t2, _ = HC.screen_view(vmm, m["tris"], fn, f, r, u)
        a = HC.analyse(t2)
        out[name] = {"reads": a["reads"], "left_facing": a["left_facing"],
                     "offsets": [t.get("offset_ccw_deg") for t in a["tips"]],
                     "screen_right_arm_hooks": a.get("screen_right_arm_hooks"),
                     "screen_up_arm_hooks": a.get("screen_up_arm_hooks"), "tip_radius_mm": a["tip_radius_mm"]}
    return out


def main():
    shipped, ship_nodes = load(SHIPPED)
    back, back_nodes = load(BACK)
    res = int(U3["mesh"][MESH]["light_map_resolution"])
    rec = {"shipped": str(SHIPPED), "unreal_export": str(BACK), "shipped_nodes": ship_nodes, "unreal_nodes": back_nodes,
           "lods": {}}
    back_lods = sorted((k for k in back if not k.startswith("UCX_")), key=lambda k: -len(back[k]["tris"]))
    rec["unreal_lod_nodes_by_tri_count"] = back_lods
    for i in range(3):
        s, b = shipped[f"{MESH}_LOD{i}"], back[back_lods[i]]
        e = {"unreal_node": back_lods[i], "shipped_tris": len(s["tris"]), "unreal_tris": len(b["tris"]),
             "shipped_uv_channels": s["uv_names"], "unreal_uv_channels": b["uv_names"],
             "position_two_sided_max_cm": two_sided(s["verts"], b["verts"]),
             "uv0": uv0_pairs_match(s, b), "normals": normals_match(s, b),
             "handedness_unreal_reexport": hand(b), "handedness_shipped": hand(s)}
        if len(b["uv_names"]) >= 2:
            tris = uv1_tris(b)
            e["uv1"] = uv1_check(tris, res)
            d = 0.25 / res
            big = max(range(len(tris)), key=lambda t: abs(area2(*tris[t])))
            ctl = uv1_check(tris + [ccw(tuple((c[0] + d, c[1] + d) for c in tris[big]))], res)
            e["uv1_negative_control"] = {"overlapping_pairs": ctl["overlapping_pairs"],
                                         "overlap_area_total": ctl["overlap_area_total"],
                                         "detects": ctl["overlapping_pairs"] >= 1}
        rec["lods"][f"LOD{i}"] = e
    sh = [k for k in shipped if k.startswith("UCX_")]
    bh = [k for k in back if k.startswith("UCX_")]
    rec["shipped_hull_nodes"], rec["unreal_hull_nodes"] = sh, bh
    if len(sh) == 1 and len(bh) == 1:
        H, B = shipped[sh[0]], back[bh[0]]
        pb, ps = planes(B), planes(H)
        us, ub = unique(H["verts"]), unique(B["verts"])
        # the hull must carry the same chirality: its vertex set mirrored (y -> -y) must NOT equal Unreal's
        um = unique([(x, -y, z) for x, y, z in H["verts"]])
        rec["hull"] = {
            "shipped": {"node": sh[0], "unique_verts": len(us), "tris": len(H["tris"]), "volume_cm3": volume(H)},
            "unreal": {"node": bh[0], "parent": B["parent"], "unique_verts": len(ub), "tris": len(B["tris"]),
                       "volume_cm3": volume(B)},
            "vertex_sets_equal_1e-5cm": us == ub,
            "mirrored_shipped_hull_equals_unreal_hull": um == ub,
            "two_sided_vertex_distance_cm": two_sided(H["verts"], B["verts"]),
            "two_sided_vertex_distance_cm_if_mirrored": two_sided([(x, -y, z) for x, y, z in H["verts"]], B["verts"]),
            "unreal_hull_self_convex_max_outside_cm": max_outside(pb, B["verts"]),
            "lod0_shipped_max_outside_unreal_hull_cm": max_outside(pb, shipped[f"{MESH}_LOD0"]["verts"]),
            "lod0_unreal_max_outside_unreal_hull_cm": max_outside(pb, back[back_lods[0]]["verts"]),
            "lod0_shipped_max_outside_shipped_hull_cm": max_outside(ps, shipped[f"{MESH}_LOD0"]["verts"]),
            "lod1_lod2_unreal_max_outside_unreal_hull_cm": max(max_outside(pb, back[back_lods[i]]["verts"]) for i in (1, 2)),
            "lod0_mirrored_max_outside_unreal_hull_cm": max_outside(pb, [(x, -y, z) for x, y, z in shipped[f"{MESH}_LOD0"]["verts"]]),
        }
    (HERE / "b2_roundtrip.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print("UC11_B2_DONE")


main()
