"""Independent verifier step 0 (Blender, headless): re-import each SHIPPED FBX in a fresh factory-startup Blender
and record what the file itself contains: node names, parents, per-node triangle counts, UCX nodes, their convexity
and whether the UCX union contains LOD0, socket empties, material slots, bounds (in the FBX's own units -> cm).
Also PNG header facts for every shipped map (size, bit depth, colour type) read directly from the bytes.
"""
import bpy, bmesh, json, hashlib, struct, sys, math
from pathlib import Path
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
EXP = PROJ / "Exports" / "SnowFlower" / "v4"
OUT = PROJ / "WorkFiles" / "SnowFlower" / "v4" / "UnrealVerify_Indep" / "iv0_blender_fbx.json"
res = {}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tri_count(ob):
    me = ob.data
    return sum(len(p.vertices) - 2 for p in me.polygons)


def world_verts(ob):
    me = ob.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    M = np.array(ob.matrix_world)
    return (co @ M[:3, :3].T) + M[:3, 3]


def hull_planes(pts):
    # convex hull via bmesh; return planes (n, d) with outward normals
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    r = bmesh.ops.convex_hull(bm, input=bm.verts)
    bm.faces.ensure_lookup_table()
    c = pts.mean(axis=0)
    planes = []
    for f in bm.faces:
        n = np.array(f.normal)
        if np.linalg.norm(n) < 1e-9:
            continue
        p0 = np.array(f.verts[0].co)
        d = n @ p0
        if n @ c - d > 0:
            n, d = -n, -d
        planes.append((n, d))
    bm.free()
    return planes


def is_convex(ob):
    V = world_verts(ob)
    planes = hull_planes(V)
    scale = np.ptp(V, axis=0).max()
    worst = max(max(float(n @ v - d) for n, d in planes) for v in V)
    # every mesh vertex must be on/inside the hull and every face must be planar-on-hull
    me = ob.data
    off = 0.0
    for poly in me.polygons:
        pv = V[list(poly.vertices)]
        # a face lies on the hull if some hull plane contains all its vertices
        best = min(max(abs(float(n @ v - d)) for v in pv) for n, d in planes)
        off = max(off, best)
    return {"verts": len(V), "faces": len(me.polygons), "max_vertex_outside_hull": worst,
            "max_face_off_hull": off, "convex": bool(off <= 1e-4 * scale)}, planes


for name in ("SM_SnowFlower", "SM_SnowFlower_Sheath"):
    fbx = EXP / f"{name}.fbx"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    r = {"sha256": sha(fbx), "objects": {}}
    unit = bpy.context.scene.unit_settings.scale_length
    r["scene_scale_length"] = unit
    for ob in bpy.data.objects:
        d = {"type": ob.type, "parent": ob.parent.name if ob.parent else None,
             "matrix_world_scale": [round(v, 6) for v in ob.matrix_world.to_scale()]}
        if ob.type == "MESH":
            d["triangles"] = tri_count(ob)
            d["vertices"] = len(ob.data.vertices)
            d["materials"] = [m.name if m else None for m in ob.data.materials]
            d["uv_layers"] = [u.name for u in ob.data.uv_layers]
            V = world_verts(ob)
            d["bbox_min"] = V.min(axis=0).round(5).tolist()
            d["bbox_max"] = V.max(axis=0).round(5).tolist()
        r["objects"][ob.name] = d
    lod0 = bpy.data.objects.get(f"{name}_LOD0")
    ucx = sorted((o for o in bpy.data.objects if o.name.startswith("UCX_")), key=lambda o: o.name)
    r["ucx_names"] = [o.name for o in ucx]
    r["ucx_keyed_to_lod0_node"] = all(o.name.startswith(f"UCX_{name}_LOD0_") for o in ucx) and lod0 is not None
    if lod0 is not None and ucx:
        V0 = world_verts(lod0)
        inside_any = np.zeros(len(V0), bool)
        dist_out = np.full(len(V0), np.inf)
        hulls = {}
        for o in ucx:
            info, planes = is_convex(o)
            N = np.array([p[0] for p in planes])
            D = np.array([p[1] for p in planes])
            s = V0 @ N.T - D  # >0 outside that plane
            m = s.max(axis=1)
            inside_any |= m <= 1e-4
            dist_out = np.minimum(dist_out, np.maximum(m, 0))
            hulls[o.name] = info
        r["ucx"] = hulls
        r["lod0_vertices_inside_ucx_union_frac"] = float(inside_any.mean())
        r["lod0_max_outside_ucx_union"] = float(dist_out.max())
        r["lod0_p99_outside_ucx_union"] = float(np.percentile(dist_out, 99))
        worst = np.argsort(-dist_out)[:5]
        r["lod0_worst_outside_points"] = [[*V0[i].round(3).tolist(), float(dist_out[i])] for i in worst]
    res[name] = r

# PNG headers
pngs = {}
for p in sorted((EXP / "Textures").glob("*.png")):
    b = p.read_bytes()[:40]
    w, h = struct.unpack(">II", b[16:24])
    bitdepth, ctype = b[24], b[25]
    pngs[p.name] = {"w": w, "h": h, "bit_depth": bitdepth, "colour_type": ctype, "sha256": sha(p),
                    "pow2": bool((w & (w - 1)) == 0 and (h & (h - 1)) == 0)}
res["pngs"] = pngs
OUT.write_text(json.dumps(res, indent=1, default=lambda o: bool(o) if hasattr(o, "dtype") else str(o)), encoding="utf-8")
print("IV0_DONE", OUT)
