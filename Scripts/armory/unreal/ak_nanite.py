"""Which ArmoryKit meshes are Nanite (2026-10-01, the "[VSM] Non-Nanite Marking Job Queue overflow" warning in PIE and
in the capture run: "This occurs when many non-nanite meshes cover a large area of the shadow map").

Cause: the whole kit (618 instances: floor, walls, roof, lattice ceiling, cases, the exterior cards) was imported with
Nanite OFF, so every shadow-casting mesh went through the non-Nanite VSM page-marking path, for the moon's directional
VSM and the 12 shadowed local lights. Fix: every kit mesh whose slots are all opaque or masked is Nanite; a mesh with a
translucent slot (the case glass pieces: SM_AK_Case_*_Glass, glass pane + bronze frame) stays non-Nanite, because
Nanite renders only opaque / masked materials (a translucent section would draw with the default material).
The Nanite fallback keeps 100 % of the triangles (FallbackTarget PercentTriangles 1.0, always generated), so the LOD0
triangle count stays equal to Blender's (verify gate 1) and the ray-tracing / Lumen fallback is the full mesh.
Shared by ak_import.py (sets it), ak_level.py (material usage) and ak_verify.py (gate 1 checks it).
"""
import ak_common as C

TRANSLUCENT_MASTERS = {"M_AK_Glass_Master"}
FALLBACK_PERCENT = 1.0


def slot_masters(slots, mats=None):
    """{slot: master} for a mesh's material slots (slot name = layout.json material name); None for an unknown slot."""
    mats = mats if mats is not None else C.blender_materials()
    out = {}
    for s in slots:
        if s in mats:
            tex, p = mats[s]
            out[s] = C.material_spec(tex, p)[0]
        else:
            out[s] = None
    return out


def want_nanite(slots, mats=None):
    """True when every slot is a known opaque / masked material (no translucent master, no unknown slot)."""
    m = slot_masters(slots, mats)
    return bool(m) and all(v is not None and v not in TRANSLUCENT_MASTERS for v in m.values())


def nanite_masters(mats=None):
    """The masters the Nanite meshes use (they need the Nanite material usage)."""
    mats = mats if mats is not None else C.blender_materials()
    return sorted({C.material_spec(t, p)[0] for t, p in mats.values()} - TRANSLUCENT_MASTERS)


# The bounds gate (ak_level / ak_verify): a Nanite mesh's render bounds enclose its whole cluster hierarchy, whose
# simplified (coarse) levels stand off the real surface (measured 2026-10-01: the lattice ceiling +1.9 cm, the lit wall
# panel +10 cm, the entrance +19 cm, the mountain ring card 6.4 m), so they no longer equal the Blender box. The gate
# checks the Blender -> Unreal conversion, so for a Nanite mesh it uses the LOD0 SOURCE geometry (the imported mesh
# description, the same vertices Blender exported) placed by the actor's transform; a non-Nanite mesh keeps its render
# bounds as before. The Nanite render-bounds deviation is reported, not gated.
_SOURCE_XYZ = {}


def source_points(mesh):
    """The mesh's LOD0 source vertex positions (cm, local), cached per mesh."""
    import unreal
    key = mesh.get_path_name()
    if key not in _SOURCE_XYZ:
        smd = mesh.get_static_mesh_description(0)
        pts = []
        for i in range(int(smd.get_vertex_count())):
            p = smd.get_vertex_position(unreal.VertexID(i))
            pts.append((p.x, p.y, p.z))
        _SOURCE_XYZ[key] = pts
    return _SOURCE_XYZ[key]


def is_nanite(mesh):
    return bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))


def actor_box(actor):
    """-> (min[3], max[3], basis, render_min_max) world AABB in cm. For a Nanite mesh: the local box of its source
    vertices, its 8 corners placed by the actor (location + yaw; the kit is never tilted or scaled), which is the same
    convention as the Blender bounds (blender_bounds.py: the object's local bound box in world space) and as a classic
    mesh's render bounds. Else the actor's render bounds. render_min_max is the actor's render bounds (for the
    informational Nanite deviation)."""
    import math
    o, e = actor.get_actor_bounds(False)
    rmin, rmax = [o.x - e.x, o.y - e.y, o.z - e.z], [o.x + e.x, o.y + e.y, o.z + e.z]
    mesh = actor.static_mesh_component.get_editor_property("static_mesh")
    if mesh is None or not is_nanite(mesh):
        return rmin, rmax, "render", (rmin, rmax)
    loc, rot, sc = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
    if abs(rot.pitch) > 1e-3 or abs(rot.roll) > 1e-3 or max(abs(sc.x - 1), abs(sc.y - 1), abs(sc.z - 1)) > 1e-6:
        return rmin, rmax, "render (tilted or scaled)", (rmin, rmax)
    pts = source_points(mesh)
    lo = [min(q[k] for q in pts) for k in range(3)]
    hi = [max(q[k] for q in pts) for k in range(3)]
    c, s_ = math.cos(math.radians(rot.yaw)), math.sin(math.radians(rot.yaw))
    xs, ys = [], []
    for x in (lo[0], hi[0]):
        for y in (lo[1], hi[1]):
            xs.append(loc.x + x * c - y * s_)
            ys.append(loc.y + x * s_ + y * c)
    return [min(xs), min(ys), loc.z + lo[2]], [max(xs), max(ys), loc.z + hi[2]], "nanite_source", (rmin, rmax)
