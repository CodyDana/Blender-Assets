"""UnrealCheck12: compare what Unreal SAVED for SM_Kunai_Plain with the shipped FBX.  Headless Blender, saves nothing:

    blender.exe -b --factory-startup --python-exit-code 3 --python b2_roundtrip.py

Inputs: the shipped FBX (b1_truth.json arrays), Unreal's re-export of the saved asset (u5, roundtrip/), Unreal's render
data of every LOD (u6_renderdata.json) and the fresh read-back (u3_readback.json).
  R1 hulls   Unreal's collision node(s) split into position-welded connected components; each matched to a shipped
             UCX (two-sided vertex distance, counts, volume, convexity); LOD0 (shipped and Unreal's) inside the UNION of
             Unreal's stored hulls; Unreal's hull-derived centre of mass (uniform density, as Unreal computes it)
  R2 LODs    Unreal's re-export per LOD: triangle count, two-sided position distance, (position, UV0) pairs, normals
  R3 UV1     Unreal's generated lightmap UVs per LOD: inside [0, 1]; exact pairwise triangle-overlap area (convex
             clipping); texels at the asset's lightmap resolution claimed by two charts; a negative control
  R4 render  u6 render data per LOD against the FBX truth under the legacy importer's conversion (Blender m (x,y,z) ->
             Unreal cm (100x, -100y, 100z)): positions two-sided, (position, UV0) pairs with Unreal's V = 1 - V within the
             float16 half-ulp, normals, per-section material slot and triangle count, the lettering band (+Z, x range,
             U toward +X, V toward Unreal +Y), each section's UV tile
  R5 lod     the LodGroup thresholds Unreal's exporter wrote (10 / RenderData ScreenSize) - the render-side screen sizes
Writes b2_roundtrip.json.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils.kdtree import KDTree

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck12_KunaiPlainVerify"
MESH = "SM_Kunai_Plain"
SHIPPED = PROJ / "Exports" / "Shuriken" / f"{MESH}.fbx"
BACK = HERE / "roundtrip" / f"{MESH}_from_unreal.fbx"
B1 = json.loads((HERE / "b1_truth.json").read_text(encoding="utf-8"))
U3 = json.loads((HERE / "u3_readback.json").read_text(encoding="utf-8"))
U6 = json.loads((HERE / "u6_renderdata.json").read_text(encoding="utf-8"))
REPORT = json.loads((PROJ / "WorkFiles" / "shuriken" / "kunai_plain_report.json").read_text(encoding="utf-8"))


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    ln = math.sqrt(dot(a, a)) or 1.0
    return (a[0] / ln, a[1] / ln, a[2] / ln)


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
            "slots": [s.material.name if s.material else None for s in ob.material_slots],
            "parent": ob.parent.name if ob.parent else None,
            "det": mw.to_3x3().determinant(),
        }
    nodes = sorted((o.name, o.type, o.parent.name if o.parent else None, round(o.matrix_world.to_3x3().determinant(), 9))
                   for o in bpy.data.objects)
    return out, nodes


def kd(points):
    t = KDTree(len(points))
    for i, p in enumerate(points):
        t.insert(p, i)
    t.balance()
    return t


def two_sided(a, b):
    ka, kb = kd(a), kd(b)
    return max(max(kb.find(p)[2] for p in a), max(ka.find(p)[2] for p in b))


def half_ulp16(x):
    """Half the float16 spacing at |x| (Unreal's default 16-bit UV storage)."""
    ax = abs(x)
    if ax < 2.0 ** -14:
        return 2.0 ** -25
    return 2.0 ** (math.floor(math.log2(ax)) - 11)


def pairs_match(src, dst, pos_tol, bound=None):
    """src/dst: lists of (position, uv).  For every src pair, the best UV delta among dst pairs at the same position."""
    tree = kd([p for p, _ in dst])
    worst, worst_ratio, unmatched = 0.0, 0.0, 0
    for p, uv in src:
        best, best_ratio = None, None
        for (_, idx, _) in tree.find_range(p, pos_tol):
            q = dst[idx][1]
            d = max(abs(uv[0] - q[0]), abs(uv[1] - q[1]))
            r = max(abs(uv[0] - q[0]) / half_ulp16(q[0]), abs(uv[1] - q[1]) / half_ulp16(q[1])) if bound else 0.0
            if best is None or d < best:
                best = d
            if best_ratio is None or r < best_ratio:
                best_ratio = r
        if best is None:
            unmatched += 1
        else:
            worst = max(worst, best)
            worst_ratio = max(worst_ratio, best_ratio)
    return {"pairs": len(src), "no_position_match": unmatched, "worst_uv_axis_delta": worst,
            "worst_delta_over_float16_half_ulp": worst_ratio}


def normals_match(src, dst, pos_tol):
    """src/dst: lists of (position, normal); worst over src of the smallest angle to a dst normal at that position."""
    tree = kd([p for p, _ in dst])
    worst, unmatched = 0.0, 0
    for p, n in src:
        best = None
        for (_, idx, _) in tree.find_range(p, pos_tol):
            m = dst[idx][1]
            a = math.degrees(math.acos(max(-1.0, min(1.0, dot(norm(n), norm(m))))))
            best = a if best is None or a < best else best
        if best is None:
            unmatched += 1
        else:
            worst = max(worst, best)
    return {"no_position_match": unmatched, "worst_deg": worst}


# ------------------------------------------------------------------ convex hull helpers
def planes(verts, tris):
    cen = tuple(sum(v[i] for v in verts) / len(verts) for i in range(3))
    out = []
    for i, j, k in tris:
        n = cross(sub(verts[j], verts[i]), sub(verts[k], verts[i]))
        ln = math.sqrt(dot(n, n))
        if ln < 1e-14:
            continue
        n = (n[0] / ln, n[1] / ln, n[2] / ln)
        if dot(n, sub(cen, verts[i])) > 0:
            n = (-n[0], -n[1], -n[2])
        out.append((n, verts[i]))
    return out


def outside(pl, p):
    return max(dot(n, sub(p, a)) for n, a in pl)


def solid(verts, tris):
    """Volume and centroid of a convex solid from its surface triangles, winding-independent (fan from the centroid)."""
    c0 = tuple(sum(v[i] for v in verts) / len(verts) for i in range(3))
    vol, acc = 0.0, [0.0, 0.0, 0.0]
    for i, j, k in tris:
        a, b, c = sub(verts[i], c0), sub(verts[j], c0), sub(verts[k], c0)
        v = abs(dot(a, cross(b, c))) / 6.0
        vol += v
        for m in range(3):
            acc[m] += v * (c0[m] + (verts[i][m] + verts[j][m] + verts[k][m] - 3.0 * c0[m]) / 4.0 + 0.0)
    return vol, [x / vol for x in acc] if vol > 0 else None


def components(m, weld=1e-5):
    """Split a mesh into connected components after welding coincident positions."""
    key = {}
    vid = []
    for v in m["verts"]:
        k = tuple(round(c / weld) for c in v)
        vid.append(key.setdefault(k, len(key)))
    parent = list(range(len(key)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for t in m["tris"]:
        a = find(vid[t[0]])
        for q in t[1:]:
            b = find(vid[q])
            if a != b:
                parent[b] = a
    groups = {}
    for ti, t in enumerate(m["tris"]):
        groups.setdefault(find(vid[t[0]]), []).append(t)
    out = []
    for tris in groups.values():
        used = sorted({i for t in tris for i in t})
        remap = {i: n for n, i in enumerate(used)}
        out.append({"verts": [m["verts"][i] for i in used], "tris": [tuple(remap[i] for i in t) for t in tris]})
    return out


def unique(vs, nd=4):
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


def uv1_check(tris, res_list):
    us = [c[0] for t in tris for c in t]
    vs = [c[1] for t in tris for c in t]
    over_pairs, total, worst, cand = 0, 0.0, 0.0, 0
    bb = [(min(p[0] for p in t), max(p[0] for p in t), min(p[1] for p in t), max(p[1] for p in t)) for t in tris]
    order = sorted(range(len(tris)), key=lambda i: bb[i][0])
    for n, i in enumerate(order):
        for j in order[n + 1:]:
            if bb[j][0] >= bb[i][1]:
                break
            if bb[j][2] >= bb[i][3] or bb[i][2] >= bb[j][3]:
                continue
            cand += 1
            poly = clip(tris[i], tris[j])
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
                a, b = find(ti), find(corner[k])
                if a != b:
                    parent[a] = b
            else:
                corner[k] = ti
    texel = {}
    for res in res_list:
        owner, shared = {}, set()
        for ti, (a, b, c) in enumerate(tris):
            ch = find(ti)
            y0 = max(int(math.floor(min(a[1], b[1], c[1]) * res)), 0)
            y1 = min(int(math.ceil(max(a[1], b[1], c[1]) * res)), res)
            x0 = max(int(math.floor(min(a[0], b[0], c[0]) * res)), 0)
            x1 = min(int(math.ceil(max(a[0], b[0], c[0]) * res)), res)
            for y in range(y0, y1):
                for x in range(x0, x1):
                    p = ((x + 0.5) / res, (y + 0.5) / res)
                    if area2(b, c, p) >= 0 and area2(c, a, p) >= 0 and area2(a, b, p) >= 0:
                        if owner.setdefault((x, y), ch) != ch:
                            shared.add((x, y))
        texel[str(res)] = {"texels_claimed_by_two_charts": len(shared), "texels_covered": len(owner)}
    return {"u_range": [min(us), max(us)], "v_range": [min(vs), max(vs)],
            "inside_0_1": min(us) >= 0.0 and min(vs) >= 0.0 and max(us) <= 1.0 and max(vs) <= 1.0,
            "bbox_candidate_pairs": cand, "overlapping_pairs": over_pairs, "overlap_area_total": total,
            "overlap_area_max": worst, "zero_area_triangles": sum(1 for t in tris if abs(area2(*t)) < 1e-14),
            "charts": len({find(i) for i in range(len(tris))}), "texel": texel,
            "uv1_area_fraction": sum(abs(area2(*t)) / 2.0 for t in tris)}


def uv_tris(m, ch):
    uv = m["uvs"][m["uv_names"][ch]]
    return [ccw(tuple(uv[li] for li in tl)) for tl in m["tri_loops"]]


# ------------------------------------------------------------------ FBX LodGroup thresholds
def lod_thresholds(path):
    try:
        from io_scene_fbx import parse_fbx
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}
    root, version = parse_fbx.parse(str(path))
    found = []

    def walk(e, ctx):
        name = e.id.decode("utf-8", "replace") if isinstance(e.id, bytes) else str(e.id)
        if name == "NodeAttribute":
            cls = e.props[2] if len(e.props) > 2 else b""
            ctx = cls.decode("utf-8", "replace") if isinstance(cls, bytes) else str(cls)
            if ctx == "LodGroup":
                rec = {"name": e.props[1].decode("utf-8", "replace") if isinstance(e.props[1], bytes) else str(e.props[1]),
                       "properties": {}}
                for sub_e in e.elems:
                    if sub_e.id == b"Properties70":
                        for p in sub_e.elems:
                            key = p.props[0].decode("utf-8", "replace") if isinstance(p.props[0], bytes) else str(p.props[0])
                            rec["properties"][key] = [x.decode("utf-8", "replace") if isinstance(x, bytes) else x
                                                      for x in p.props[4:]]
                found.append(rec)
        for c in e.elems:
            walk(c, ctx)
    for e in root.elems:
        walk(e, None)
    return {"fbx_version": version, "lod_groups": found}


# ------------------------------------------------------------------ main
def fbx_pairs_ue(arrays):
    """FBX truth corners -> (Unreal cm position, Unreal UV0 (u, 1 - v)), (position, normal) under the documented map."""
    vs = [(100.0 * x, -100.0 * y, 100.0 * z) for x, y, z in arrays["verts_m"]]
    pu, pn = [], []
    for li, vi in enumerate(arrays["loop_vert"]):
        u, v = arrays["uv0"][li]
        pu.append((vs[vi], (u, 1.0 - v)))
        n = arrays["loop_normals"][li]
        pn.append((vs[vi], (n[0], -n[1], n[2])))
    return vs, pu, pn


def render_checks():
    lett = REPORT["lettering"]["uv"]["uv0_blender"]
    rect = {"u_min": lett["u_min"], "u_max": lett["u_max"], "v_min": 1.0 - lett["v_max"], "v_max": 1.0 - lett["v_min"]}
    out = {"rect_unreal": rect, "static_materials": U6.get("static_materials"), "lods": {}}
    for lod, secs in U6["lods"].items():
        arr = B1["fbx_arrays"][lod]
        fvs, fpu, fpn = fbx_pairs_ue(arr)
        verts, pu, pn = [], [], []
        rec = {"sections": []}
        band_pts, band_uv, band_tris = [], [], 0
        for s in secs:
            us = [q[0] for q in s["uv0"]]
            vv = [q[1] for q in s["uv0"]]
            rec["sections"].append({"section": s["section"], "material_slot": s["material_slot"],
                                    "triangles": len(s["tris"]), "vertices": len(s["verts_cm"]),
                                    "u_range": [min(us), max(us)], "v_range": [min(vv), max(vv)]})
            for p, uv, n in zip(s["verts_cm"], s["uv0"], s["normals"]):
                verts.append(tuple(p))
                pu.append((tuple(p), tuple(uv)))
                pn.append((tuple(p), tuple(n)))
            if s["material_slot"] == 1:
                for t in s["tris"]:
                    cu = sum(s["uv0"][k][0] for k in t) / 3.0
                    cv = sum(s["uv0"][k][1] for k in t) / 3.0
                    if rect["u_min"] - 1e-4 <= cu <= rect["u_max"] + 1e-4 and rect["v_min"] - 1e-4 <= cv <= rect["v_max"] + 1e-4:
                        band_tris += 1
                        for k in t:
                            band_pts.append(s["verts_cm"][k])
                            band_uv.append(s["uv0"][k])
        rec["triangles_total"] = sum(x["triangles"] for x in rec["sections"])
        rec["fbx_triangles_per_slot"] = B1["fbx_scene"]["lods"][lod]["triangles_per_slot"]
        rec["position_two_sided_max_cm"] = two_sided(verts, fvs)
        rec["uv0_unreal_to_fbx"] = pairs_match(pu, fpu, 1e-4, bound=True)
        rec["uv0_fbx_to_unreal"] = pairs_match(fpu, pu, 1e-4, bound=True)
        rec["normals_unreal_to_fbx"] = normals_match(pn, fpn, 1e-4)
        rec["normals_fbx_to_unreal"] = normals_match(fpn, pn, 1e-4)
        mirrored = [(x, -y, z) for x, y, z in fvs]
        rec["position_two_sided_max_cm_if_y_not_negated"] = two_sided(verts, mirrored)
        if band_pts:
            def corr(a, b):
                ma, mb = sum(a) / len(a), sum(b) / len(b)
                num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
                den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) or 1.0
                return num / den
            xs, ys, zs = [p[0] for p in band_pts], [p[1] for p in band_pts], [p[2] for p in band_pts]
            rec["lettering_band"] = {"triangles": band_tris, "x_cm": [min(xs), max(xs)], "y_cm": [min(ys), max(ys)],
                                     "z_cm": [min(zs), max(zs)], "u": [min(q[0] for q in band_uv), max(q[0] for q in band_uv)],
                                     "v": [min(q[1] for q in band_uv), max(q[1] for q in band_uv)],
                                     "corr_u_x": corr([q[0] for q in band_uv], xs),
                                     "corr_v_unreal_y": corr([q[1] for q in band_uv], ys),
                                     "normal_z_min": None}
        else:
            rec["lettering_band"] = {"triangles": 0}
        out["lods"][lod] = rec
    return out


def main():
    shipped, ship_nodes = load(SHIPPED)
    back, back_nodes = load(BACK)
    res = int(U3["mesh"]["light_map_resolution"])
    rec = {"shipped": str(SHIPPED), "unreal_export": str(BACK), "shipped_nodes": ship_nodes, "unreal_nodes": back_nodes,
           "lightmap_resolution": res, "lods": {}}
    back_lods = sorted((k for k in back if not k.startswith("UCX_")), key=lambda k: -len(back[k]["tris"]))
    rec["unreal_lod_nodes_by_tri_count"] = back_lods
    for i in range(min(3, len(back_lods))):
        s, b = shipped[f"{MESH}_LOD{i}"], back[back_lods[i]]
        sp = [(s["verts"][s["loop_vert"][li]], s["uvs"][s["uv_names"][0]][li]) for li in range(len(s["loop_vert"]))]
        bp = [(b["verts"][b["loop_vert"][li]], b["uvs"][b["uv_names"][0]][li]) for li in range(len(b["loop_vert"]))]
        sn = [(s["verts"][s["loop_vert"][li]], s["loop_normals"][li]) for li in range(len(s["loop_vert"]))]
        bn = [(b["verts"][b["loop_vert"][li]], b["loop_normals"][li]) for li in range(len(b["loop_vert"]))]
        e = {"unreal_node": back_lods[i], "shipped_tris": len(s["tris"]), "unreal_tris": len(b["tris"]),
             "shipped_uv_channels": s["uv_names"], "unreal_uv_channels": b["uv_names"],
             "unreal_material_slots": b["slots"], "unreal_det": b["det"],
             "position_two_sided_max_cm": two_sided(s["verts"], b["verts"]),
             "uv0_unreal_to_shipped": pairs_match(bp, sp, 1e-4, bound=True),
             "uv0_shipped_to_unreal": pairs_match(sp, bp, 1e-4, bound=True),
             "normals_unreal_to_shipped": normals_match(bn, sn, 1e-4),
             "normals_shipped_to_unreal": normals_match(sn, bn, 1e-4)}
        if len(b["uv_names"]) >= 2:
            tris = uv_tris(b, 1)
            e["uv1"] = uv1_check(tris, [res, 256, 1024])
            d = 0.25 / res
            big = max(range(len(tris)), key=lambda t: abs(area2(*tris[t])))
            ctl = uv1_check(tris + [ccw(tuple((c[0] + d, c[1] + d) for c in tris[big]))], [res])
            e["uv1_negative_control"] = {"overlapping_pairs": ctl["overlapping_pairs"],
                                         "overlap_area_total": ctl["overlap_area_total"],
                                         "texels_claimed_by_two_charts": ctl["texel"][str(res)]["texels_claimed_by_two_charts"],
                                         "detects": ctl["overlapping_pairs"] >= 1}
        rec["lods"][f"LOD{i}"] = e
    # ---- hulls
    sh = sorted(k for k in shipped if k.startswith("UCX_"))
    bh = sorted(k for k in back if k.startswith("UCX_"))
    rec["shipped_hull_nodes"], rec["unreal_hull_nodes"] = sh, bh
    comps = []
    for n in bh:
        for c in components(back[n]):
            c["node"] = n
            comps.append(c)
    rec["unreal_hull_components"] = len(comps)
    hulls = {}
    for n in sh:
        H = shipped[n]
        best = None
        for ci, c in enumerate(comps):
            d = two_sided(H["verts"], c["verts"])
            if best is None or d < best[0]:
                best = (d, ci)
        c = comps[best[1]]
        pl = planes(c["verts"], c["tris"])
        vol_u, cen_u = solid(c["verts"], c["tris"])
        vol_s, cen_s = solid(H["verts"], H["tris"])
        hulls[n] = {"matched_component": best[1], "unreal_node": c["node"],
                    "two_sided_vertex_distance_cm": best[0],
                    "shipped_unique_verts": len(unique(H["verts"])), "unreal_unique_verts": len(unique(c["verts"])),
                    "shipped_tris": len(H["tris"]), "unreal_tris": len(c["tris"]),
                    "shipped_volume_cm3": vol_s, "unreal_volume_cm3": vol_u,
                    "shipped_centroid_cm": cen_s, "unreal_centroid_cm": cen_u,
                    "unreal_self_convex_max_outside_cm": max(outside(pl, v) for v in c["verts"])}
    rec["hulls"] = hulls
    matched = sorted({h["matched_component"] for h in hulls.values()})
    rec["hull_components_matched_one_to_one"] = len(matched) == len(sh) == len(comps)
    upl = [planes(c["verts"], c["tris"]) for c in comps]

    def union_out(pts):
        return max(min(outside(pl, p) for pl in upl) for p in pts)
    rec["containment_in_unreal_hull_union_cm"] = {
        "LOD0_shipped": union_out(shipped[f"{MESH}_LOD0"]["verts"]),
        "LOD0_unreal": union_out(back[back_lods[0]]["verts"]) if back_lods else None,
        "LOD1_unreal": union_out(back[back_lods[1]]["verts"]) if len(back_lods) > 1 else None,
        "LOD2_unreal": union_out(back[back_lods[2]]["verts"]) if len(back_lods) > 2 else None}
    tv = sum(solid(c["verts"], c["tris"])[0] for c in comps)
    com = [sum(solid(c["verts"], c["tris"])[0] * solid(c["verts"], c["tris"])[1][m] for c in comps) / tv for m in range(3)]
    rec["unreal_hulls_total_volume_cm3"] = tv
    rec["unreal_hull_derived_com_cm_blender_axes"] = com
    rec["com_nudge_needed_to_reach_pivot_cm_unreal_axes"] = [-com[0], com[1], -com[2]]
    # ---- render data (u6) against the FBX truth
    rec["render"] = render_checks()
    # ---- LodGroup thresholds written by Unreal's exporter
    rec["unreal_export_lodgroup"] = lod_thresholds(BACK)
    rec["shipped_lodgroup"] = lod_thresholds(SHIPPED)
    (HERE / "b2_roundtrip.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print("UC12_B2_DONE")


main()
