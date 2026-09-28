"""Compare Unreal's re-export of each verified asset with the shipped FBX (headless Blender).

For each form and LOD: triangle count, UV channel count, UV1 (lightmap) range and a
raster overlap estimate, and a two-sided nearest-vertex distance between the shipped LOD
and what Unreal built (positions only, cm). For the collision hull Unreal exported from its
body setup: vertex count, and how far any shipped LOD0 vertex lies outside it (plane test).
Saves nothing into any .blend. Writes roundtrip_compare.json next to this file. Every form in
FORMS whose Unreal re-export exists in roundtrip/ is compared (one entry per pack form).
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck6"
FORMS = {"eight_point": "SM_Shuriken_EightPoint", "four_point": "SM_Shuriken_FourPoint",
         "square_plate": "SM_Shuriken_SquarePlate"}


def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)


def load(path):
    clear()
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        me = ob.data
        me.calc_loop_triangles()
        mw = ob.matrix_world
        out[ob.name] = {
            "tris": len(me.loop_triangles),
            "verts_cm": [tuple((mw @ v.co) * 100.0) for v in me.vertices],
            "uv_names": [uv.name for uv in me.uv_layers],
            "uv_tris": {uv.name: [[tuple(uv.data[li].uv) for li in t.loops] for t in me.loop_triangles]
                        for uv in me.uv_layers},
            "polys_cm": [[tuple((mw @ me.vertices[i].co) * 100.0) for i in p.vertices] for p in me.polygons],
            "uv0_loops": [(tuple(me.uv_layers[0].data[l.index].uv), tuple((mw @ me.vertices[l.vertex_index].co) * 100.0))
                          for l in me.loops] if me.uv_layers else [],
        }
    return out


def two_sided(a, b):
    def one(src, dst):
        kd = KDTree(len(dst))
        for i, p in enumerate(dst):
            kd.insert(p, i)
        kd.balance()
        return max(kd.find(p)[2] for p in src) if src else None
    return max(one(a, b), one(b, a))


def uv_stats(tris, res=1024):
    us = [c[0] for t in tris for c in t]
    vs = [c[1] for t in tris for c in t]
    grid = bytearray(res * res)
    over = 0
    for (a, b, c) in tris:
        minx = max(int(min(a[0], b[0], c[0]) * res), 0)
        maxx = min(int(max(a[0], b[0], c[0]) * res) + 1, res)
        miny = max(int(min(a[1], b[1], c[1]) * res), 0)
        maxy = min(int(max(a[1], b[1], c[1]) * res) + 1, res)
        area = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(area) < 1e-14:
            continue
        for y in range(miny, maxy):
            py = (y + 0.5) / res
            for x in range(minx, maxx):
                px = (x + 0.5) / res
                w0 = (b[0] - px) * (c[1] - py) - (c[0] - px) * (b[1] - py)
                w1 = (c[0] - px) * (a[1] - py) - (a[0] - px) * (c[1] - py)
                w2 = (a[0] - px) * (b[1] - py) - (b[0] - px) * (a[1] - py)
                if (w0 > 0 and w1 > 0 and w2 > 0) or (w0 < 0 and w1 < 0 and w2 < 0):  # strict: shared edges are not overlap
                    k = y * res + x
                    if grid[k]:
                        over += 1
                    grid[k] = 1
    covered = sum(grid)
    area_sum = sum(abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2 for a, b, c in tris)
    return {"u_range": [round(min(us), 5), round(max(us), 5)], "v_range": [round(min(vs), 5), round(max(vs), 5)],
            "inside_0_1": min(us) >= 0 and min(vs) >= 0 and max(us) <= 1 and max(vs) <= 1,
            "coverage": round(covered / (res * res), 4), "triangle_area_sum": round(area_sum, 4), "overlap_pixels": over, "res": res}


def uv_keyed(a_loops, b_loops):
    """Handedness-sensitive match: same UV0 coordinate must land on the same position.

    The outline is mirror-symmetric, so a position-only nearest-vertex test cannot see a
    Y flip; UV0 is not mirror-symmetric, so keying positions by UV0 can.
    """
    def key(uv):
        return (round(uv[0], 4), round(uv[1], 4))
    bmap = {}
    for uv, p in b_loops:
        bmap.setdefault(key(uv), p)
    worst, matched = 0.0, 0
    for uv, p in a_loops:
        q = bmap.get(key(uv))
        if q is None:
            continue
        matched += 1
        worst = max(worst, (Vector(p) - Vector(q)).length)
    return {"loops": len(a_loops), "matched": matched, "max_position_diff_cm": round(worst, 6)}


def hull_outside(hull_polys, pts):
    centroid = Vector((0, 0, 0))
    allv = [Vector(v) for poly in hull_polys for v in poly]
    for v in allv:
        centroid += v
    centroid /= len(allv)
    planes = []
    for poly in hull_polys:
        a, b, c = (Vector(poly[0]), Vector(poly[1]), Vector(poly[2]))
        n = (b - a).cross(c - a)
        if n.length < 1e-12:
            continue
        n.normalize()
        if n.dot(centroid - a) > 0:
            n = -n
        planes.append((n, a))
    worst = max(max(n.dot(Vector(p) - a) for n, a in planes) for p in pts)
    return round(max(worst, 0.0), 5)


def main():
    result = {}
    for form, mesh in FORMS.items():
        unreal_fbx = HERE / "roundtrip" / f"{mesh}_from_unreal.fbx"
        if not unreal_fbx.exists():
            continue
        shipped = load(PROJ / "Exports" / "Shuriken" / f"{mesh}.fbx")
        back = load(unreal_fbx)
        rec = {"unreal_export_nodes": sorted(back.keys()), "lods": {}}
        back_lods = sorted(k for k in back if not k.startswith("UCX_"))
        # Unreal names exported LOD meshes after the asset; map by triangle order (LOD0 largest).
        back_lods.sort(key=lambda k: -back[k]["tris"])
        for i in range(3):
            s = shipped[f"{mesh}_LOD{i}"]
            b = back[back_lods[i]] if i < len(back_lods) else None
            entry = {"shipped_tris": s["tris"], "unreal_node": back_lods[i] if b else None}
            if b:
                entry["unreal_tris"] = b["tris"]
                entry["unreal_uv_channels"] = b["uv_names"]
                entry["position_two_sided_max_cm"] = round(two_sided(s["verts_cm"], b["verts_cm"]), 6)
                if len(b["uv_names"]) >= 2:
                    entry["uv1_lightmap"] = uv_stats(b["uv_tris"][b["uv_names"][1]])
                    entry["uv1_lightmap_2048"] = {k: v for k, v in uv_stats(b["uv_tris"][b["uv_names"][1]], 2048).items() if k in ("overlap_pixels", "coverage", "res")}
                entry["control_shipped_uv0"] = uv_stats(s["uv_tris"][s["uv_names"][0]])
                entry["uv0_keyed_position_check"] = uv_keyed(s["uv0_loops"], b["uv0_loops"])
            rec["lods"][f"LOD{i}"] = entry
        hulls = [k for k in back if k.startswith("UCX_")]
        rec["unreal_hulls"] = {}
        for h in hulls:
            hv = back[h]
            uniq = {tuple(round(c, 4) for c in v) for v in hv["verts_cm"]}
            rec["unreal_hulls"][h] = {
                "verts_unique": len(uniq), "tris": hv["tris"],
                "lod0_max_outside_cm": hull_outside(hv["polys_cm"], shipped[f"{mesh}_LOD0"]["verts_cm"]),
                "size_cm": [round(max(v[i] for v in hv["verts_cm"]) - min(v[i] for v in hv["verts_cm"]), 4)
                            for i in range(3)],
            }
        sh = shipped[f"UCX_{mesh}_LOD0_00"]
        rec["shipped_hull"] = {"verts": len(sh["verts_cm"]), "tris": sh["tris"],
                               "lod0_max_outside_cm": hull_outside(sh["polys_cm"], shipped[f"{mesh}_LOD0"]["verts_cm"])}
        if hulls:
            rec["hull_shipped_vs_unreal_two_sided_max_cm"] = round(
                two_sided(sh["verts_cm"], back[hulls[0]]["verts_cm"]), 6)
        result[form] = rec
    (HERE / "roundtrip_compare.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("ROUNDTRIP_DONE")


main()
