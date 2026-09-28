"""Compare Unreal's re-export of the verifier's saved asset with the shipped FBX (headless Blender, saves nothing).

    blender.exe -b --factory-startup --python-exit-code 3 --python roundtrip.py

Per LOD: triangle count; two-sided nearest-vertex position distance (cm); UV0 keyed by position (for every
Unreal loop, the nearest shipped UV at the same position - catches a handedness flip that the D4-symmetric
positions cannot); loop normals keyed the same way (Import Normals must survive); UV1 (generated lightmap)
range and raster overlap at 1024 and 2048. Hull: the UCX node(s) Unreal wrote from its body setup, vertex and
triangle counts vs the shipped UCX, two-sided vertex distance, and the plane test of every LOD against it.
Writes <form>_roundtrip.json next to this file.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vsp_config as V  # noqa: E402

S = V.spec()
UNREAL_FBX = V.HERE / "roundtrip" / f"{S['mesh']}_from_unreal.fbx"


def load(path):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        me = ob.data
        me.calc_loop_triangles()
        mw = ob.matrix_world
        n3 = mw.to_3x3().inverted().transposed()
        cn = me.corner_normals
        verts = [(mw @ v.co) * 100.0 for v in me.vertices]
        out[ob.name] = {
            "tris": len(me.loop_triangles),
            "verts_cm": verts,
            "polys_cm": [[verts[i] for i in p.vertices] for p in me.polygons],
            "uv_names": [uv.name for uv in me.uv_layers],
            "uv_tris": {uv.name: [[tuple(uv.data[li].uv) for li in t.loops] for t in me.loop_triangles]
                        for uv in me.uv_layers},
            "loops": [(verts[l.vertex_index],
                       tuple(me.uv_layers[0].data[l.index].uv) if me.uv_layers else None,
                       (n3 @ Vector(cn[l.index].vector)).normalized())
                      for l in me.loops],
        }
    return out


def two_sided(a, b):
    def one(src, dst):
        kd = KDTree(len(dst))
        for i, p in enumerate(dst):
            kd.insert(p, i)
        kd.balance()
        return max(kd.find(p)[2] for p in src)
    return max(one(a, b), one(b, a))


def keyed(unreal_loops, shipped_loops, pos_tol_cm=1e-4):
    """For each Unreal loop: shipped loops at the same position -> min UV distance and min normal angle."""
    kd = KDTree(len(shipped_loops))
    for i, (p, _, _) in enumerate(shipped_loops):
        kd.insert(p, i)
    kd.balance()
    worst_uv, worst_ang, unmatched = 0.0, 0.0, 0
    for p, uv, n in unreal_loops:
        cands = kd.find_range(p, pos_tol_cm)
        if not cands:
            unmatched += 1
            continue
        best_uv = min(math.dist(uv, shipped_loops[i][1]) for _, i, _ in cands)
        best_ang = min(math.degrees(n.angle(shipped_loops[i][2], 0.0)) for _, i, _ in cands)
        worst_uv = max(worst_uv, best_uv)
        worst_ang = max(worst_ang, best_ang)
    return {"loops": len(unreal_loops), "unmatched_positions": unmatched,
            "uv0_max_diff": round(worst_uv, 7), "uv0_max_diff_px_at_2048": round(worst_uv * 2048, 4),
            "normal_max_angle_deg": round(worst_ang, 4)}


def uv_raster(tris, res):
    us = [c[0] for t in tris for c in t]
    vs = [c[1] for t in tris for c in t]
    grid = bytearray(res * res)
    over = 0
    for (a, b, c) in tris:
        area = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(area) < 1e-14:
            continue
        minx, maxx = max(int(min(a[0], b[0], c[0]) * res), 0), min(int(max(a[0], b[0], c[0]) * res) + 1, res)
        miny, maxy = max(int(min(a[1], b[1], c[1]) * res), 0), min(int(max(a[1], b[1], c[1]) * res) + 1, res)
        for y in range(miny, maxy):
            py = (y + 0.5) / res
            for x in range(minx, maxx):
                px = (x + 0.5) / res
                w0 = (b[0] - px) * (c[1] - py) - (c[0] - px) * (b[1] - py)
                w1 = (c[0] - px) * (a[1] - py) - (a[0] - px) * (c[1] - py)
                w2 = (a[0] - px) * (b[1] - py) - (b[0] - px) * (a[1] - py)
                if (w0 > 0 and w1 > 0 and w2 > 0) or (w0 < 0 and w1 < 0 and w2 < 0):
                    k = y * res + x
                    if grid[k]:
                        over += 1
                    grid[k] = 1
    return {"u_range": [round(min(us), 6), round(max(us), 6)], "v_range": [round(min(vs), 6), round(max(vs), 6)],
            "inside_0_1": min(us) >= 0 and min(vs) >= 0 and max(us) <= 1 and max(vs) <= 1,
            "coverage": round(sum(grid) / (res * res), 4), "overlap_pixels": over, "res": res,
            "zero_area_tris": sum(1 for a, b, c in tris
                                  if abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) < 1e-14)}


def plane_outside(hull_polys, pts):
    allv = [Vector(v) for poly in hull_polys for v in poly]
    centroid = sum(allv, Vector((0, 0, 0))) / len(allv)
    planes = []
    for poly in hull_polys:
        a, b, c = Vector(poly[0]), Vector(poly[1]), Vector(poly[2])
        n = (b - a).cross(c - a)
        if n.length < 1e-12:
            continue
        n.normalize()
        if n.dot(centroid - a) > 0:
            n = -n
        planes.append((n, a))
    return round(max(max(max(n.dot(Vector(p) - a) for n, a in planes) for p in pts), 0.0), 8)


def main():
    rec = {"form": V.FORM, "shipped_fbx": str(S["fbx"]), "shipped_fbx_sha256": V.sha256(S["fbx"]),
           "unreal_fbx": str(UNREAL_FBX), "unreal_fbx_sha256": V.sha256(UNREAL_FBX)}
    shipped = load(S["fbx"])
    back = load(UNREAL_FBX)
    rec["unreal_export_nodes"] = sorted(back)
    rec["shipped_nodes"] = sorted(shipped)
    back_lods = sorted((k for k in back if not k.startswith("UCX_")), key=lambda k: -back[k]["tris"])
    rec["lods"] = {}
    for i in range(3):
        s = shipped[S["lod_node"][i]]
        name = back_lods[i] if i < len(back_lods) else None
        e = {"shipped_node": S["lod_node"][i], "unreal_node": name, "shipped_tris": s["tris"]}
        if name:
            b = back[name]
            e["unreal_tris"] = b["tris"]
            e["unreal_uv_channels"] = b["uv_names"]
            e["position_two_sided_max_cm"] = round(two_sided(s["verts_cm"], b["verts_cm"]), 8)
            e["keyed_uv0_normals"] = keyed(b["loops"], s["loops"])
            if len(b["uv_names"]) >= 2:
                e["uv1_1024"] = uv_raster(b["uv_tris"][b["uv_names"][1]], 1024)
                e["uv1_2048"] = uv_raster(b["uv_tris"][b["uv_names"][1]], 2048)
        rec["lods"][f"LOD{i}"] = e
    sh = shipped[S["ucx_node"]]
    rec["shipped_hull"] = {"node": S["ucx_node"], "verts_unique": len({tuple(round(c, 5) for c in v) for v in sh["verts_cm"]}),
                           "tris": sh["tris"]}
    hulls = sorted(k for k in back if k.startswith("UCX_"))
    rec["unreal_hulls"] = {}
    for h in hulls:
        hv = back[h]
        uniq = {tuple(round(c, 5) for c in v) for v in hv["verts_cm"]}
        rec["unreal_hulls"][h] = {
            "verts_unique": len(uniq), "tris": hv["tris"],
            "vertex_set_equal_to_shipped_1e-5cm": uniq == {tuple(round(c, 5) for c in v) for v in sh["verts_cm"]},
            "two_sided_vs_shipped_cm": round(two_sided(sh["verts_cm"], hv["verts_cm"]), 8),
            "size_cm": [round(max(v[i] for v in hv["verts_cm"]) - min(v[i] for v in hv["verts_cm"]), 6) for i in range(3)],
            **{f"LOD{i}_max_outside_cm": plane_outside(hv["polys_cm"], shipped[S["lod_node"][i]]["verts_cm"]) for i in range(3)},
        }
    t = V.TOL
    lods = rec["lods"].values()
    hl = list(rec["unreal_hulls"].values())
    rec["checks"] = {
        "tris_equal_all_lods": all(e.get("unreal_tris") == e["shipped_tris"] for e in lods),
        "positions_roundtrip_within_1e-6_cm": all(e.get("position_two_sided_max_cm", 1.0) <= t["roundtrip_position_cm"] for e in lods),
        "uv0_keyed_all_positions_matched": all(e.get("keyed_uv0_normals", {}).get("unmatched_positions", 1) == 0 for e in lods),
        "uv1_inside_0_1": all(e.get("uv1_2048", {}).get("inside_0_1") for e in lods),
        "uv1_zero_overlap_1024_and_2048": all(e.get("uv1_1024", {}).get("overlap_pixels", 1) == 0
                                              and e.get("uv1_2048", {}).get("overlap_pixels", 1) == 0 for e in lods),
        "exactly_one_hull_exported": len(hl) == 1,
        "hull_counts_equal_shipped": len(hl) == 1 and hl[0]["verts_unique"] == rec["shipped_hull"]["verts_unique"]
        and hl[0]["tris"] == rec["shipped_hull"]["tris"],
        "hull_vertices_identical_to_shipped": len(hl) == 1 and hl[0]["vertex_set_equal_to_shipped_1e-5cm"]
        and hl[0]["two_sided_vs_shipped_cm"] <= t["roundtrip_position_cm"],
        "lod0_0cm_outside_stored_hull": len(hl) == 1 and hl[0]["LOD0_max_outside_cm"] <= t["hull_outside_cm"],
    }
    rec["passed"] = all(rec["checks"].values())
    (V.HERE / f"{V.FORM}_roundtrip.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print("VSP_ROUNDTRIP_DONE passed=" + str(rec["passed"]))


main()
