"""Independent verifier step 0 (Blender 5.2 headless, factory startup): re-import each SHIPPED FBX and record what
the file itself contains: node names, parents, per-node triangle counts (the 'Blender' truth the Unreal LOD counts are
gated against), UCX nodes, their convexity, whether the UCX union contains LOD0, socket empties, material slots,
UV layers, bounds (cm).  Also PNG header facts for every shipped map read directly from the bytes.
Adapted copy of WorkFiles/SnowFlower/v4/UnrealVerify_Indep/iv0_blender_fbx.py.
"""
import bpy, bmesh, json, struct, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\katana\UnrealVerify_Indep")
import kv_common as C  # noqa: E402

OUT = C.HERE / "kv0_blender_fbx.json"
res = {"blender": bpy.app.version_string}


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def world_verts(ob):
    me = ob.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    M = np.array(ob.matrix_world)
    return (co @ M[:3, :3].T) + M[:3, 3]


def hull_planes(pts):
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts)
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
    off = 0.0
    for poly in ob.data.polygons:
        pv = V[list(poly.vertices)]
        best = min(max(abs(float(n @ v - d)) for v in pv) for n, d in planes)
        off = max(off, best)
    return {"verts": len(V), "faces": len(ob.data.polygons), "max_vertex_outside_hull_cm": worst * 100,
            "max_face_off_hull_cm": off * 100, "convex": bool(off <= 1e-4 * scale)}, planes


for name in C.MESHES:
    fbx = C.EXP / f"{name}.fbx"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    r = {"sha256": C.sha(fbx), "sha_equals_shipped": C.sha(fbx) == C.SHIPPED_SHA[name], "objects": {}}
    for ob in bpy.data.objects:
        d = {"type": ob.type, "parent": ob.parent.name if ob.parent else None,
             "matrix_world_scale": [round(v, 6) for v in ob.matrix_world.to_scale()],
             "world_location_cm": [round(v * 100, 5) for v in ob.matrix_world.translation]}
        if ob.type == "MESH":
            d["triangles"] = tri_count(ob)
            d["vertices"] = len(ob.data.vertices)
            d["materials"] = [m.name if m else None for m in ob.data.materials]
            d["uv_layers"] = [u.name for u in ob.data.uv_layers]
            V = world_verts(ob) * 100
            d["bbox_min_cm"] = V.min(axis=0).round(5).tolist()
            d["bbox_max_cm"] = V.max(axis=0).round(5).tolist()
        r["objects"][ob.name] = d
    lods = sorted((o for o in bpy.data.objects if o.type == "MESH" and "_LOD" in o.name and not o.name.startswith("UCX_")),
                  key=lambda o: o.name)
    r["lod_nodes"] = [o.name for o in lods]
    r["lod_triangles"] = [tri_count(o) for o in lods]
    r["sockets_in_fbx"] = {o.name: [round(v * 100, 5) for v in o.matrix_world.translation]
                           for o in bpy.data.objects if o.name.startswith("SOCKET_")}
    lod0 = bpy.data.objects.get(f"{name}_LOD0")
    ucx = sorted((o for o in bpy.data.objects if o.name.startswith("UCX_")), key=lambda o: o.name)
    r["ucx_names"] = [o.name for o in ucx]
    r["ucx_keyed_to_lod0_node"] = bool(ucx) and lod0 is not None and all(o.name.startswith(f"UCX_{name}_LOD0_") for o in ucx)
    if lod0 is not None and ucx:
        hulls = {}
        for lname in r["lod_nodes"]:
            V0 = world_verts(bpy.data.objects[lname])
            inside_any = np.zeros(len(V0), bool)
            dist_out = np.full(len(V0), np.inf)
            for o in ucx:
                info, planes = is_convex(o)
                N = np.array([p[0] for p in planes])
                D = np.array([p[1] for p in planes])
                m = (V0 @ N.T - D).max(axis=1)
                inside_any |= m <= 1e-6
                dist_out = np.minimum(dist_out, np.maximum(m, 0))
                hulls[o.name] = info
            r.setdefault("containment", {})[lname] = {
                "vertices": len(V0), "inside_frac": float(inside_any.mean()),
                "max_outside_cm": float(dist_out.max() * 100)}
        r["ucx"] = hulls
    res[name] = r

pngs = {}
for p in sorted((C.EXP / "Textures").glob("*.png")):
    b = p.read_bytes()[:40]
    w, h = struct.unpack(">II", b[16:24])
    pngs[p.name] = {"w": w, "h": h, "bit_depth": b[24], "colour_type": b[25], "sha256": C.sha(p),
                    "pow2": bool((w & (w - 1)) == 0 and (h & (h - 1)) == 0),
                    "full_mip_count": int(np.log2(max(w, h))) + 1}
res["pngs"] = pngs
OUT.write_text(json.dumps(res, indent=1, default=lambda o: bool(o) if hasattr(o, "dtype") else str(o)), encoding="utf-8")
print("KV0_DONE", OUT)
