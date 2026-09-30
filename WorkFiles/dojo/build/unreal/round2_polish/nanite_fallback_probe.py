"""Round-2 diagnostic (pythonscript commandlet, -nullrhi, READ-ONLY): for every Nanite mesh of the showcase, compare
  - the SOURCE box (mesh description LOD0),
  - the FALLBACK box (LOD0 render data vertices, ProceduralMeshLibrary.get_section_from_static_mesh; for a Nanite mesh
    LOD0 render data IS the fallback),
  - the asset render bounds (get_bounding_box: for Nanite = ClusterDAG.TotalBounds, the union of every DAG level's
    cluster boxes, NaniteEncode.cpp CalculateMeshBounds <- ClusterDAG.cpp TotalBounds += Cluster.Bounds)
with the Blender LOD0 box (showcase/blender_bounds.json), in cm. Out: round2_polish/nanite_fallback_probe.json"""
import json
import unreal

B = r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build"
L = json.load(open(B + r"\showcase\layout_showcase.json", encoding="utf-8"))
BL = json.load(open(B + r"\showcase\blender_bounds.json", encoding="utf-8"))["pieces"]
OUT = B + r"\unreal\round2_polish\nanite_fallback_probe.json"


def bl_box_cm(piece):
    (x0, y0, z0), (x1, y1, z1) = BL[piece]["bbox_lod0"]
    return [[x0 * 100, -y1 * 100, z0 * 100], [x1 * 100, -y0 * 100, z1 * 100]]


def err(a, b):
    return max(abs(a[i][k] - b[i][k]) for i in range(2) for k in range(3))


R = {}
for piece, p in sorted(L["pieces"].items()):
    if not p.get("nanite"):
        continue
    m = unreal.load_asset(f"{p['ue_dir']}/{piece}")
    e = {}
    lo, hi = [1e18] * 3, [-1e18] * 3
    n = 0
    for s in range(m.get_num_sections(0)):
        verts = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(m, 0, s)[0]
        for v in verts:
            n += 1
            for k, c in enumerate((v.x, v.y, v.z)):
                lo[k] = min(lo[k], c)
                hi[k] = max(hi[k], c)
    e["fallback_box"] = [lo, hi]
    e["fallback_verts"] = n
    d = m.get_static_mesh_description(0)
    xs = [d.get_vertex_position(unreal.VertexID(i)) for i in range(d.get_vertex_count())]
    e["source_box"] = [[min(v.x for v in xs), min(v.y for v in xs), min(v.z for v in xs)],
                       [max(v.x for v in xs), max(v.y for v in xs), max(v.z for v in xs)]]
    bb = m.get_bounding_box()
    e["render_bounds"] = [[bb.min.x, bb.min.y, bb.min.z], [bb.max.x, bb.max.y, bb.max.z]]
    want = bl_box_cm(piece)
    e["blender_box"] = want
    e["err_fallback_cm"] = round(err(e["fallback_box"], want), 3) if n else None
    e["err_source_cm"] = round(err(e["source_box"], want), 3)
    e["err_render_bounds_cm"] = round(err(e["render_bounds"], want), 3)
    e["lod0_tris"] = m.get_num_triangles(0)
    e["source_tris"] = d.get_triangle_count()
    R[piece] = e
summary = {"n": len(R), "max_err_fallback_cm": max((v["err_fallback_cm"] or 0) for v in R.values()),
           "max_err_source_cm": max(v["err_source_cm"] for v in R.values()),
           "max_err_render_bounds_cm": max(v["err_render_bounds_cm"] for v in R.values()),
           "fallback_tris_eq_source": sum(1 for v in R.values() if v["lod0_tris"] == v["source_tris"])}
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump({"summary": summary, "meshes": R}, fh, indent=1)
unreal.log("NANITE_PROBE_DONE " + json.dumps(summary))
