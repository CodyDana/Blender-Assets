"""Compare Unreal's re-export of the saved SM_PaperBomb with the bytes that shipped.

Unreal's legacy FBX exporter writes the BUILT render data - every texcoord channel,
so the generated lightmap UV1 becomes visible - and, with Collision ON, the convex
hull out of the body setup, which Python cannot read directly.  This is the gate an
API cannot fool.

Checks
  * per-LOD triangle counts in both files
  * two-sided nearest-vertex distance, shipped LOD vs Unreal's LOD (cm)
  * UV0 range, UV1 (lightmap) range, and a raster overlap count on UV1
  * the convex hull: vertex count, convexity, and whether it CONTAINS every LOD0
    vertex (signed distance outside the hull's own face planes)
  * the hull Unreal kept vs the hull that shipped

Run:
  blender.exe -b --factory-startup --python-exit-code 3 --python pbr_roundtrip.py
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealReview"
SHIPPED = PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.fbx"
FROM_UE = HERE / "roundtrip" / "SM_PaperBomb_from_unreal.fbx"
OUT = HERE / "pbr_roundtrip.json"
MESH = "SM_PaperBomb"


def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)


def load(path):
    """Import an FBX and return {node: {verts_cm, polys_cm, tris, uv_names, uv_tris}}."""
    clear()
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        me = ob.data
        me.calc_loop_triangles()
        mw = ob.matrix_world
        verts = [(mw @ v.co) * 100.0 for v in me.vertices]     # metres -> cm, Blender frame
        rec = {
            "verts_cm": [(v.x, v.y, v.z) for v in verts],
            "polys_cm": [[tuple((mw @ me.vertices[i].co) * 100.0) for i in p.vertices] for p in me.polygons],
            "tris": len(me.loop_triangles),
            "polygons": len(me.polygons),
            "vertices": len(me.vertices),
            "uv_names": [uv.name for uv in me.uv_layers],
            "uv_tris": {},
        }
        for uv in me.uv_layers:
            tris = []
            for t in me.loop_triangles:
                tris.append([tuple(uv.data[li].uv) for li in t.loops])
            rec["uv_tris"][uv.name] = tris
        out[ob.name] = rec
    return out


def two_sided(a, b):
    def one(src, dst):
        worst = 0.0
        for p in src:
            best = min((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2 for q in dst)
            worst = max(worst, best)
        return worst
    return math.sqrt(max(one(a, b), one(b, a)))


def uv_stats(tris, res=1024):
    """Range, coverage and a strict overlap-pixel count for a UV channel."""
    us = [u for t in tris for u, _ in t]
    vs = [v for t in tris for _, v in t]
    cover = {}
    area_sum = 0.0
    for t in tris:
        (u0, v0), (u1, v1), (u2, v2) = t
        area_sum += abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) * 0.5
        x0, x1 = min(u0, u1, u2), max(u0, u1, u2)
        y0, y1 = min(v0, v1, v2), max(v0, v1, v2)
        for px in range(max(0, int(x0 * res)), min(res - 1, int(x1 * res)) + 1):
            for py in range(max(0, int(y0 * res)), min(res - 1, int(y1 * res)) + 1):
                cx, cy = (px + 0.5) / res, (py + 0.5) / res
                w0 = (u1 - u0) * (cy - v0) - (v1 - v0) * (cx - u0)
                w1 = (u2 - u1) * (cy - v1) - (v2 - v1) * (cx - u1)
                w2 = (u0 - u2) * (cy - v2) - (v0 - v2) * (cx - u2)
                if (w0 > 0 and w1 > 0 and w2 > 0) or (w0 < 0 and w1 < 0 and w2 < 0):
                    cover[(px, py)] = cover.get((px, py), 0) + 1
    over = sum(1 for c in cover.values() if c > 1)
    return {"u": [round(min(us), 6), round(max(us), 6)], "v": [round(min(vs), 6), round(max(vs), 6)],
            "inside_0_1": bool(min(us) >= -1e-6 and max(us) <= 1 + 1e-6
                               and min(vs) >= -1e-6 and max(vs) <= 1 + 1e-6),
            "coverage": round(len(cover) / (res * res), 5), "triangle_area_sum": round(area_sum, 5),
            "overlap_pixels": over, "res": res}


def hull_planes(polys):
    """Outward face planes of a convex polyhedron given its polygons."""
    allv = [Vector(v) for poly in polys for v in poly]
    centre = sum(allv, Vector()) / len(allv)
    planes = []
    for poly in polys:
        if len(poly) < 3:
            continue
        p0 = Vector(poly[0])
        n = None
        for i in range(1, len(poly) - 1):
            cand = (Vector(poly[i]) - p0).cross(Vector(poly[i + 1]) - p0)
            if cand.length > 1e-9:
                n = cand.normalized()
                break
        if n is None:
            continue
        if n.dot(p0 - centre) < 0:
            n = -n
        planes.append((n, n.dot(p0)))
    return planes


def max_outside(planes, pts):
    """Largest signed distance any point lies OUTSIDE the hull (cm, >= 0)."""
    worst = 0.0
    for p in pts:
        v = Vector(p)
        d = max(n.dot(v) - off for n, off in planes)
        worst = max(worst, d)
    return worst


def convexity(planes, verts):
    """Every vertex must lie on or inside every face plane for the shape to be convex."""
    return max(max(n.dot(Vector(p)) - off for n, off in planes) for p in verts)


def main():
    rep = {"blender": bpy.app.version_string, "shipped": str(SHIPPED), "from_unreal": str(FROM_UE)}
    shipped = load(SHIPPED)
    back = load(FROM_UE)
    rep["shipped_nodes"] = sorted(shipped)
    rep["unreal_nodes"] = sorted(back)

    lods = {}
    for i in range(3):
        name = f"{MESH}_LOD{i}"
        s = shipped.get(name)
        u = back.get(name) or back.get(f"{MESH}_LOD{i}_LOD{i}") or back.get(MESH if i == 0 else "")
        entry = {"shipped_tris": s["tris"] if s else None, "shipped_verts": s["vertices"] if s else None}
        if u:
            entry.update({"unreal_node": next(k for k, v in back.items() if v is u),
                          "unreal_tris": u["tris"], "unreal_verts": u["vertices"],
                          "unreal_uv_names": u["uv_names"]})
            entry["two_sided_max_cm"] = round(two_sided(s["verts_cm"], u["verts_cm"]), 7) if s else None
            entry["tri_delta"] = u["tris"] - s["tris"] if s else None
            if u["uv_names"]:
                entry["uv0"] = uv_stats(u["uv_tris"][u["uv_names"][0]])
            if len(u["uv_names"]) > 1:
                entry["uv1_lightmap"] = uv_stats(u["uv_tris"][u["uv_names"][1]])
                entry["uv1_lightmap_2048"] = {k: v for k, v in
                                              uv_stats(u["uv_tris"][u["uv_names"][1]], 2048).items()
                                              if k in ("overlap_pixels", "coverage", "res")}
        lods[f"LOD{i}"] = entry
    rep["lods"] = lods

    # ---- collision ----
    ship_hulls = sorted(k for k in shipped if k.startswith("UCX_"))
    ue_hulls = sorted(k for k in back if k.startswith("UCX_"))
    rep["shipped_hull_nodes"] = ship_hulls
    rep["unreal_hull_nodes"] = ue_hulls
    lod0_pts = shipped[f"{MESH}_LOD0"]["verts_cm"]
    coll = {}
    if ship_hulls:
        sh = shipped[ship_hulls[0]]
        pl = hull_planes(sh["polys_cm"])
        coll["shipped"] = {"node": ship_hulls[0], "verts": sh["vertices"], "faces": sh["polygons"],
                           "convexity_max_cm": round(convexity(pl, sh["verts_cm"]), 8),
                           "lod0_max_outside_cm": round(max_outside(pl, lod0_pts), 8)}
    if ue_hulls:
        uh = back[ue_hulls[0]]
        pl = hull_planes(uh["polys_cm"])
        coll["unreal"] = {"node": ue_hulls[0], "verts": uh["vertices"], "faces": uh["polygons"],
                          "convexity_max_cm": round(convexity(pl, uh["verts_cm"]), 8),
                          "lod0_max_outside_cm": round(max_outside(pl, lod0_pts), 8)}
        # every LOD's vertices, not just LOD0
        coll["unreal"]["all_lods_max_outside_cm"] = {
            f"LOD{i}": round(max_outside(pl, shipped[f"{MESH}_LOD{i}"]["verts_cm"]), 8) for i in range(3)}
    if ship_hulls and ue_hulls:
        coll["shipped_vs_unreal_two_sided_max_cm"] = round(
            two_sided(shipped[ship_hulls[0]]["verts_cm"], back[ue_hulls[0]]["verts_cm"]), 8)
    rep["collision"] = coll

    rep["gates"] = {
        "lod_triangles_survive_roundtrip": all(lods[f"LOD{i}"].get("tri_delta") == 0 for i in range(3)),
        "lod_positions_agree": all((lods[f"LOD{i}"].get("two_sided_max_cm") or 1.0) < 1e-4 for i in range(3)),
        "uv1_present_on_every_lod": all("uv1_lightmap" in lods[f"LOD{i}"] for i in range(3)),
        "uv1_inside_0_1_every_lod": all((lods[f"LOD{i}"].get("uv1_lightmap") or {}).get("inside_0_1")
                                        for i in range(3)),
        "uv1_no_overlap_every_lod": all((lods[f"LOD{i}"].get("uv1_lightmap") or {}).get("overlap_pixels", 1) == 0
                                        for i in range(3)),
        "uv0_inside_0_1_every_lod": all((lods[f"LOD{i}"].get("uv0") or {}).get("inside_0_1") for i in range(3)),
        "one_hull_in_unreal": len(ue_hulls) == 1,
        "hull_convex": bool(coll.get("unreal", {}).get("convexity_max_cm", 1.0) < 1e-5),
        "hull_contains_every_lod": bool(coll.get("unreal") and
                                        max(coll["unreal"]["all_lods_max_outside_cm"].values()) < 1e-5),
        "hull_survives_roundtrip": bool(coll.get("shipped_vs_unreal_two_sided_max_cm", 1.0) < 1e-4),
    }
    rep["all_passed"] = all(rep["gates"].values())
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("PBR_ROUNDTRIP_DONE " + str(OUT))
    print(json.dumps({"lods": {k: {kk: vv for kk, vv in v.items() if kk != "uv_tris"}
                              for k, v in lods.items()},
                      "collision": coll, "gates": rep["gates"]}, indent=2))


main()
