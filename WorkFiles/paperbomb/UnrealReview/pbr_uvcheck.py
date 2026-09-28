"""Exact, resolution-independent UV overlap for SM_PaperBomb, on Unreal's own re-export.

The raster overlap count in pbr_roundtrip.py disagreed with itself between 1024
and 2048, which is exactly what a rasteriser does near chart edges.  This measures
the real thing: for every pair of UV triangles whose bounding boxes intersect,
clip one against the other (Sutherland-Hodgman) and add the intersection area.
Sum ~ 0 means no overlap, whatever the resolution.

Also reports the raster overlap at the mesh's ACTUAL lightmap resolution (64) and
at 128/256, because that is the grid Unreal's baked lighting will use.
"""
import json
import math
from pathlib import Path

import bpy

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealReview"
FROM_UE = HERE / "roundtrip" / "SM_PaperBomb_from_unreal.fbx"
OUT = HERE / "pbr_uvcheck.json"
MESH = "SM_PaperBomb"


def tri_area(p):
    a = 0.0
    for i in range(len(p)):
        x0, y0 = p[i]
        x1, y1 = p[(i + 1) % len(p)]
        a += x0 * y1 - x1 * y0
    return abs(a) * 0.5


def clip(subject, clipper):
    """Sutherland-Hodgman: clip polygon `subject` by convex polygon `clipper`."""
    def inside(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-15

    def inter(p, q, a, b):
        x1, y1 = p; x2, y2 = q; x3, y3 = a; x4, y4 = b
        d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(d) < 1e-18:
            return q
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / d
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    # make the clipper counter-clockwise
    c = list(clipper)
    a2 = sum(c[i][0] * c[(i + 1) % len(c)][1] - c[(i + 1) % len(c)][0] * c[i][1] for i in range(len(c)))
    if a2 < 0:
        c.reverse()
    out = list(subject)
    for i in range(len(c)):
        a, b = c[i], c[(i + 1) % len(c)]
        if not out:
            return []
        inp, out = out, []
        s = inp[-1]
        for e in inp:
            if inside(e, a, b):
                if not inside(s, a, b):
                    out.append(inter(s, e, a, b))
                out.append(e)
            elif inside(s, a, b):
                out.append(inter(s, e, a, b))
            s = e
    return out


def overlap_area(tris):
    """Total pairwise UV intersection area (an upper bound on true overlap)."""
    boxes = [(min(p[0] for p in t), min(p[1] for p in t),
              max(p[0] for p in t), max(p[1] for p in t)) for t in tris]
    order = sorted(range(len(tris)), key=lambda i: boxes[i][0])
    total = 0.0
    pairs = 0
    worst = 0.0
    for ii in range(len(order)):
        i = order[ii]
        for jj in range(ii + 1, len(order)):
            j = order[jj]
            if boxes[j][0] > boxes[i][2]:
                break
            if boxes[j][2] < boxes[i][0] or boxes[j][1] > boxes[i][3] or boxes[j][3] < boxes[i][1]:
                continue
            poly = clip(tris[i], tris[j])
            if len(poly) >= 3:
                a = tri_area(poly)
                if a > 1e-14:
                    total += a
                    worst = max(worst, a)
                    pairs += 1
    return {"overlap_area_uv2": total, "overlapping_pairs": pairs, "largest_pair_area_uv2": worst}


def raster_overlap(tris, res):
    cover = {}
    for t in tris:
        (u0, v0), (u1, v1), (u2, v2) = t
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
    return {"res": res, "texels_used": len(cover), "overlap_texels": sum(1 for c in cover.values() if c > 1)}


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=str(FROM_UE))
    rep = {"from_unreal": str(FROM_UE), "lods": {}}
    for i in range(3):
        ob = bpy.data.objects.get(f"{MESH}_LOD{i}")
        if ob is None:
            continue
        me = ob.data
        me.calc_loop_triangles()
        entry = {"uv_names": [uv.name for uv in me.uv_layers], "triangles": len(me.loop_triangles)}
        for uv in me.uv_layers:
            tris = [[tuple(uv.data[li].uv) for li in t.loops] for t in me.loop_triangles]
            area = sum(tri_area(t) for t in tris)
            ent = {"triangle_area_sum": round(area, 7)}
            ent.update({k: (round(v, 10) if isinstance(v, float) else v)
                        for k, v in overlap_area(tris).items()})
            ent["overlap_fraction_of_area"] = round(ent["overlap_area_uv2"] / area, 10) if area else None
            ent["raster"] = [raster_overlap(tris, r) for r in (64, 128, 256)]
            entry[uv.name] = ent
        rep["lods"][f"LOD{i}"] = entry
    rep["gates"] = {
        "uv0_exact_overlap_zero": all(rep["lods"][k]["UVmap_0"]["overlap_area_uv2"] < 1e-9 for k in rep["lods"]),
        "uv1_exact_overlap_zero": all(rep["lods"][k]["LightMapUV"]["overlap_area_uv2"] < 1e-9 for k in rep["lods"]),
        "uv1_no_overlap_at_lightmap_res_64": all(
            rep["lods"][k]["LightMapUV"]["raster"][0]["overlap_texels"] == 0 for k in rep["lods"]),
    }
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("PBR_UVCHECK_DONE " + str(OUT))
    print(json.dumps(rep, indent=2))


main()
