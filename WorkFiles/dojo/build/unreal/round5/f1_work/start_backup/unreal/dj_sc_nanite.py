"""Nanite geometry boxes for the showcase bounds gates (imports `unreal`; used by dj_sc_level.py and dj_sc_verify.py).

Why (round 2, 2026-09-28, measured): a Nanite mesh's render bounds (StaticMesh.get_bounding_box / actor bounds) are
UE 5.8's ClusterDAG.TotalBounds, the union of the cluster boxes of EVERY level of the Nanite DAG, simplified levels
included (NaniteEncode.cpp CalculateMeshBounds <- ClusterDAG.cpp `TotalBounds += Bounds`), so they sit 0.5-27.6 cm
outside the real surface whatever the fallback settings. With the fallback at full detail (fallback_target
RELATIVE_ERROR, error 0) the LOD0 render data (the fallback) equals the source mesh exactly (38 / 38 meshes: triangles
equal, box error 0.000 cm; round2_polish/nanite_fallback_probe.json). So the Nanite gate measures the rendered geometry:
the fallback's vertex box, carried through the actor transform, against the Blender box.
"""
import unreal


def fallback_box(mesh):
    """Local box (cm) of the LOD0 render vertices (every section); for a Nanite mesh that is its fallback mesh."""
    lo, hi = [1e18] * 3, [-1e18] * 3
    for s in range(mesh.get_num_sections(0)):
        verts = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, s)[0]
        for v in verts:
            for k, c in enumerate((v.x, v.y, v.z)):
                lo[k] = min(lo[k], c)
                hi[k] = max(hi[k], c)
    return lo, hi


def world_box(actor, box):
    """World AABB [x0, y0, z0, x1, y1, z1] (cm) of the 8 corners of a local box under the actor's transform (the same
    construction as compose_showcase.py's Blender bounds: the LOD0 box corners through the instance matrix)."""
    lo, hi = box
    t = actor.get_actor_transform()
    pts = [t.transform_location(unreal.Vector(x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
           for z in (lo[2], hi[2])]
    return [min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts),
            max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)]
