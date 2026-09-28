"""Scene helpers for Unreal-ready static meshes: UCX hulls, sockets, LOD groups.

All helpers return the objects they create and never save the file. They run
inside Blender (import bpy) and follow FAB_ASSET_STUDY.md section 3.5 naming,
as corrected by the UE 5.8.2 tests recorded in
``WorkFiles/pipeline_test/UnrealReview/ue_review_report.json`` and
``WorkFiles/pipeline_test/UnrealTest/Validation/``:

* ``UCX_<RenderNodeName>_NN`` closed convex collision hull, child of the mesh.
  The name must repeat the **render node name exactly**. Because this package
  renames the source mesh to ``<base>_LOD0`` when it builds a LOD group, the
  shipped hull is ``UCX_<base>_LOD0_00``; ``UCX_<base>_00`` on a node called
  ``<base>_LOD0`` is silently dropped by the importer (convex count 0).
* ``SOCKET_<RenderNodeName>_<socket>`` must be an **Empty** (an FBX Null).
  A child *mesh* named ``SOCKET_`` is not a socket on UE 5.8.2: it is welded
  into the render mesh or imported as its own junk Static Mesh. This reverses
  the ``[disputed]`` row of study 3.5.
* ``<Name>_LodGroup`` Empty with custom property ``fbx_type = "LodGroup"``
  parenting ``<Name>_LOD0.._LODn``. Sockets do **not** survive an import of a
  LOD'd FBX (see ``export_fbx``): ship them through the sidecar JSON instead.

Socket orientation: with the house axis pair (Forward ``-Y`` / Up ``Z``) the
exporter pre-multiplies root nodes with a 180 deg Z rotation while child nodes
keep their Blender local matrix, and Unreal mirrors Y on import. Measured on
UE 5.8.2, a socket Empty authored with ``rotation_euler=(0, 0, 0)`` arrives
rotated 180 deg about its own axis (rotator roll 180 / yaw 180), i.e. an
attached actor faces backwards. ``make_socket`` therefore bakes a local 180 deg
Y rotation into the Empty, which lands as identity in Unreal (verified by the
``RotY180`` variant), and ``ue_socket_transform`` reproduces the engine-side
numbers for the sidecar.
"""
from __future__ import annotations

import contextlib
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union

_PACKAGE_PARENT = str(Path(__file__).resolve().parents[1])
if _PACKAGE_PARENT not in sys.path:
    sys.path.insert(0, _PACKAGE_PARENT)

import bmesh  # noqa: E402
import bpy  # noqa: E402
from bpy_extras.io_utils import axis_conversion  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402

LOD_SUFFIX_RE = re.compile(r"_LOD(\d+)$")
COLLISION_PREFIXES = ("UCX_", "UBX_", "USP_", "UCP_")
SOCKET_PREFIX = "SOCKET_"
HELPER_PREFIX_RE = re.compile(r"^(UCX_|UBX_|USP_|UCP_|SOCKET_)")
ObjectLike = Union[str, "bpy.types.Object"]

# House FBX axis pair (study 3.7); kept here so helpers and export_fbx agree.
AXIS_FORWARD = "-Y"
AXIS_UP = "Z"
# What the exporter pre-multiplies onto root nodes for that pair (a 180 deg Z rotation).
AXIS_CONVERSION = axis_conversion(to_forward=AXIS_FORWARD, to_up=AXIS_UP).to_4x4()
# Blender -> Unreal point map once the file has been imported (Y mirrored, metres -> cm).
UE_MIRROR = Matrix.Diagonal((1.0, -1.0, 1.0))
UE_UNIT_SCALE = 100.0
# Constant offset Unreal applies to a child node's orientation (measured, see module docstring).
UE_SOCKET_NODE_FLIP = Matrix.Rotation(math.pi, 3, "Y")
SOCKET_CORRECTION = Matrix.Rotation(math.pi, 4, "Y")
SOCKET_DISPLAY_SIZE = 0.05


# --------------------------------------------------------------------------- utilities

def resolve_objects(objects: Iterable[ObjectLike]) -> List["bpy.types.Object"]:
    """Turn names or objects into a list of bpy objects; raise KeyError for unknown names."""
    resolved: List[bpy.types.Object] = []
    for item in objects:
        if isinstance(item, str):
            obj = bpy.data.objects.get(item)
            if obj is None:
                raise KeyError(f"No object named {item!r}")
            resolved.append(obj)
        else:
            resolved.append(item)
    return resolved


def lod_base_name(name: str) -> str:
    """``SM_Crate_LOD2`` -> ``SM_Crate``; names without a LOD suffix are returned unchanged."""
    return LOD_SUFFIX_RE.sub("", name)


def lod_index(name: str) -> Optional[int]:
    """Return the LOD index encoded in ``name`` or None when there is no ``_LODn`` suffix."""
    match = LOD_SUFFIX_RE.search(name)
    return int(match.group(1)) if match else None


def helper_children(obj: "bpy.types.Object", exclude: Iterable[str] = ()) -> List["bpy.types.Object"]:
    """Recursively collect UCX_/UBX_/USP_/UCP_/SOCKET_ and ``_LODn`` children of ``obj``."""
    skip = set(exclude)
    found: List[bpy.types.Object] = []
    for child in obj.children:
        if child.name in skip:
            continue
        if HELPER_PREFIX_RE.match(child.name) or LOD_SUFFIX_RE.search(child.name):
            found.append(child)
            found.extend(helper_children(child, skip))
    return found


def transform_is_applied(obj: "bpy.types.Object", tolerance: float = 1e-6) -> Tuple[bool, str]:
    """Return (ok, detail) telling whether ``matrix_basis`` carries no rotation or scale."""
    _location, rotation, scale = obj.matrix_basis.decompose()
    rotation_error = max(abs(value) for row in (rotation.to_matrix() - Matrix.Identity(3)) for value in row)
    scale_error = max(abs(component - 1.0) for component in scale)
    ok = rotation_error <= tolerance and scale_error <= tolerance
    detail = (f"rotation error {rotation_error:.2e}, scale error {scale_error:.2e}, "
              f"location ({_location.x:.4f}, {_location.y:.4f}, {_location.z:.4f})")
    return ok, detail


def link_like(obj: "bpy.types.Object", template: "bpy.types.Object") -> None:
    """Link ``obj`` into the collections of ``template`` (or the scene collection)."""
    collections = list(template.users_collection) or [bpy.context.scene.collection]
    for collection in collections:
        if obj.name not in collection.objects:
            collection.objects.link(obj)


@contextlib.contextmanager
def selection(objects: Sequence["bpy.types.Object"], active: Optional["bpy.types.Object"] = None) -> Iterator[None]:
    """Temporarily select exactly ``objects`` (unhidden, selectable) and restore the previous state.

    A collection with ``hide_select`` makes its objects unselectable even when the object flag is clear, and
    ``select_set(True)`` then does nothing without an error (the locked FITBODY collection did exactly that to the
    garment armature, and the FBX came out with no skeleton). Such collections are opened for the duration, and a
    ValueError is raised if any object still reports unselected.
    """
    view_layer = bpy.context.view_layer
    view_layer.update()  # objects linked this frame are not yet in view_layer.objects
    for obj in objects:
        if obj.name not in view_layer.objects:
            raise ValueError(f"{obj.name!r} is not in the active view layer; link it to a visible collection")
    previous_selected = [obj for obj in view_layer.objects if obj.select_get()]
    previous_active = view_layer.objects.active
    previous_hidden = {obj.name: (obj.hide_get(), obj.hide_viewport, obj.hide_select) for obj in objects}
    locked_collections = {c for obj in objects for c in obj.users_collection if c.hide_select}
    if bpy.context.mode != "OBJECT" and bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in view_layer.objects:
        obj.select_set(False)
    for collection in locked_collections:
        collection.hide_select = False
    for obj in objects:
        obj.hide_viewport = False
        obj.hide_select = False
        obj.hide_set(False)
        obj.select_set(True)
    view_layer.objects.active = active if active is not None else (objects[0] if objects else None)
    try:
        unselected = [obj.name for obj in objects if not obj.select_get()]
        if unselected:
            raise ValueError(f"could not select {unselected} (hidden or unselectable in the view layer)")
        yield
    finally:
        for collection in locked_collections:
            collection.hide_select = True
        for obj in view_layer.objects:
            obj.select_set(False)
        for obj in objects:
            hidden, hide_viewport, hide_select = previous_hidden[obj.name]
            obj.hide_viewport = hide_viewport
            obj.hide_select = hide_select
            obj.hide_set(hidden)
        for obj in previous_selected:
            if obj.name in view_layer.objects and not obj.hide_get():
                obj.select_set(True)
        if previous_active is not None and previous_active.name in view_layer.objects:
            view_layer.objects.active = previous_active


def apply_modifier(obj: "bpy.types.Object", modifier: Union[str, "bpy.types.Modifier"]) -> None:
    """Apply one modifier of ``obj`` headlessly (object mode, context override)."""
    name = modifier if isinstance(modifier, str) else modifier.name
    with selection([obj], obj):
        with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj],
                                       selected_editable_objects=[obj]):
            result = bpy.ops.object.modifier_apply(modifier=name)
    if "FINISHED" not in result:
        raise RuntimeError(f"Could not apply modifier {name!r} on {obj.name!r}: {result}")


def evaluated_bmesh(obj: "bpy.types.Object", depsgraph: Optional["bpy.types.Depsgraph"] = None) -> "bmesh.types.BMesh":
    """Return a BMesh copy of ``obj`` with modifiers applied (caller frees it)."""
    depsgraph = depsgraph or bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
    finally:
        evaluated.to_mesh_clear()
    return bm


# --------------------------------------------------------------------------- Unreal transforms

def ue_rotator(matrix: Matrix) -> Tuple[float, float, float]:
    """Decompose a 3x3 Unreal-space rotation into ``(roll, pitch, yaw)`` degrees.

    Unreal composes a rotator as ``Rz(yaw) @ Ry(-pitch) @ Rx(roll)``; this is the
    inverse of that, matching what ``StaticMeshSocket.relative_rotation`` reports.
    """
    matrix = matrix.to_3x3()
    forward = matrix.col[0]
    yaw = math.degrees(math.atan2(forward.y, forward.x))
    pitch = math.degrees(math.atan2(forward.z, math.hypot(forward.x, forward.y)))
    remainder = (Matrix.Rotation(math.radians(pitch), 3, "Y")
                 @ Matrix.Rotation(math.radians(-yaw), 3, "Z") @ matrix)
    roll = math.degrees(math.atan2(remainder[2][1], remainder[1][1]))
    return (roll, pitch, yaw)


def ue_socket_transform(matrix_local: Matrix) -> Dict[str, Any]:
    """Convert a socket's Blender local matrix into the transform Unreal reports.

    Returns ``{"location_cm", "rotation_deg": {"roll", "pitch", "yaw"}, "scale"}``.
    The model (``loc_ue = 100 * mirror(p)``, ``rot_ue = mirror @ R @ mirror @ Ry(180)``)
    was fitted to the UE 5.8.2 measurements of three exported variants and is
    re-asserted by ``test_pipeline.py``, so the sidecar JSON and the FBX-imported
    socket agree by construction.
    """
    location, rotation, scale = matrix_local.decompose()
    basis = UE_MIRROR @ rotation.to_matrix() @ UE_MIRROR @ UE_SOCKET_NODE_FLIP
    roll, pitch, yaw = ue_rotator(basis)

    def clean(value: float, digits: int = 4) -> float:
        """Round away float32 decomposition noise (and -0.0)."""
        return round(value, digits) + 0.0

    return {
        "location_cm": [clean(location.x * UE_UNIT_SCALE), clean(-location.y * UE_UNIT_SCALE),
                        clean(location.z * UE_UNIT_SCALE)],
        "rotation_deg": {"roll": clean(roll), "pitch": clean(pitch), "yaw": clean(yaw)},
        "scale": [clean(value) for value in scale],
    }


# --------------------------------------------------------------------------- collision

def _hull_only(bm: "bmesh.types.BMesh") -> None:
    """Replace the geometry of ``bm`` with its convex hull (in place)."""
    result = bmesh.ops.convex_hull(bm, input=list(bm.verts))
    remove = [g for g in result["geom_interior"] + result["geom_unused"] + result["geom_holes"]
              if isinstance(g, bmesh.types.BMVert)]
    if remove:
        bmesh.ops.delete(bm, geom=remove, context="VERTS")
    hull_faces = {g for g in result["geom"] if isinstance(g, bmesh.types.BMFace)}
    stale = [face for face in bm.faces if face not in hull_faces]
    if stale:
        bmesh.ops.delete(bm, geom=stale, context="FACES_ONLY")
    loose_edges = [edge for edge in bm.edges if not edge.link_faces]
    if loose_edges:
        bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")
    loose_verts = [vert for vert in bm.verts if not vert.link_edges]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))


def make_ucx_hull(obj: "bpy.types.Object", index: int = 0, max_verts: int = 32) -> "bpy.types.Object":
    """Create ``UCX_<obj.name>_<index:02d>``: a closed convex hull of ``obj`` with <= ``max_verts``.

    The hull is built from the evaluated (modifier-applied) mesh, decimated with
    a Collapse Decimate modifier until it fits the vertex budget, re-hulled so it
    stays convex, parented to ``obj`` with the same origin, has no material and
    is hidden from render.

    Unreal matches the hull against the **render node name**, so call this after
    the mesh has its final name, or let ``make_lod_group`` rename the hull with
    the mesh (it rewrites helper children).
    """
    if obj.type != "MESH":
        raise ValueError(f"{obj.name!r} is not a mesh")
    if max_verts < 4:
        raise ValueError("max_verts must be at least 4")
    name = f"UCX_{obj.name}_{index:02d}"
    existing = bpy.data.objects.get(name)
    if existing is not None:
        raise ValueError(f"{name!r} already exists")
    bm = evaluated_bmesh(obj)
    _hull_only(bm)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    hull = bpy.data.objects.new(name, mesh)
    link_like(hull, obj)
    hull.parent = obj
    hull.matrix_parent_inverse = Matrix.Identity(4)
    hull.matrix_basis = Matrix.Identity(4)
    ratio_scale = 1.0
    for _attempt in range(16):
        if len(mesh.vertices) <= max_verts:
            break
        target_faces = max(4, 2 * max_verts - 4)
        ratio = min(0.95, max(0.02, ratio_scale * target_faces / max(1, len(mesh.polygons))))
        before = len(mesh.vertices)
        modifier = hull.modifiers.new("UCX decimate", "DECIMATE")
        modifier.decimate_type = "COLLAPSE"
        modifier.ratio = ratio
        modifier.use_collapse_triangulate = True
        apply_modifier(hull, modifier)
        bm = bmesh.new()
        bm.from_mesh(hull.data)
        _hull_only(bm)
        bm.to_mesh(hull.data)
        bm.free()
        mesh = hull.data
        if len(mesh.vertices) >= before:
            ratio_scale *= 0.7
    if len(mesh.vertices) > max_verts:
        raise RuntimeError(f"{name}: could not reduce hull below {max_verts} vertices ({len(mesh.vertices)})")
    mesh.materials.clear()
    mesh.name = name
    hull.hide_render = True
    hull.display_type = "WIRE"
    hull["ue_collision"] = "UCX"
    return hull


# --------------------------------------------------------------------------- sockets

def make_socket(obj: "bpy.types.Object", socket_name: str, location: Sequence[float],
                rotation_euler: Sequence[float] = (0.0, 0.0, 0.0), ue_correction: bool = True,
                socket_as_mesh: bool = False) -> "bpy.types.Object":
    """Create ``SOCKET_<obj.name>_<socket_name>``: an Empty (FBX Null) child of ``obj``.

    ``location`` and ``rotation_euler`` are the orientation you want in Unreal,
    expressed in the parent's local Blender space. With ``ue_correction`` (the
    default) a local 180 deg Y rotation is baked in on top, because Unreal 5.8.2
    otherwise reports the socket flipped 180 deg; the Empty therefore looks
    "backwards" in the Blender viewport and correct in the engine. The authored
    values stay readable in the ``ue_socket_rotation`` custom property.

    ``socket_as_mesh=True`` reproduces the old single-triangle mesh socket. It is
    kept only to reproduce the failure: UE 5.8.2's legacy importer does not read
    a child mesh as a socket, it welds it into the render mesh (a 1-triangle
    inflation) or imports it as a separate junk Static Mesh.
    """
    if not socket_name or "." in socket_name or " " in socket_name:
        raise ValueError(f"Invalid socket name {socket_name!r}")
    name = f"{SOCKET_PREFIX}{obj.name}_{socket_name}"
    if bpy.data.objects.get(name) is not None:
        raise ValueError(f"{name!r} already exists")
    if socket_as_mesh:
        mesh = bpy.data.meshes.new(name)
        size = 0.001
        mesh.from_pydata([(0.0, 0.0, 0.0), (size, 0.0, 0.0), (0.0, size, 0.0)], [], [(0, 1, 2)])
        mesh.update()
        socket = bpy.data.objects.new(name, mesh)
    else:
        socket = bpy.data.objects.new(name, None)
        socket.empty_display_type = "ARROWS"
        socket.empty_display_size = SOCKET_DISPLAY_SIZE
    link_like(socket, obj)
    socket.parent = obj
    socket.matrix_parent_inverse = Matrix.Identity(4)
    basis = (Matrix.Translation(Vector(location))
             @ Euler(tuple(rotation_euler), "XYZ").to_matrix().to_4x4())
    socket.matrix_basis = basis @ SOCKET_CORRECTION if ue_correction else basis
    socket.hide_render = True
    socket.show_axis = True
    socket["ue_socket"] = socket_name
    socket["ue_socket_rotation"] = tuple(float(value) for value in rotation_euler)
    socket["ue_socket_correction"] = bool(ue_correction)
    return socket


def socket_children(obj: "bpy.types.Object") -> List["bpy.types.Object"]:
    """Return the ``SOCKET_`` children of ``obj`` in name order."""
    return sorted((child for child in obj.children if child.name.startswith(SOCKET_PREFIX)),
                  key=lambda child: child.name)


def socket_record(mesh_obj: "bpy.types.Object", socket: "bpy.types.Object") -> Dict[str, Any]:
    """Describe one socket for the export sidecar (Unreal-space transform included)."""
    record: Dict[str, Any] = {
        "socket": socket.get("ue_socket") or socket.name[len(SOCKET_PREFIX):],
        "fbx_node": socket.name,
        "mesh": mesh_obj.name,
        "node_type": socket.type,
        "ue_correction": bool(socket.get("ue_socket_correction", False)),
    }
    record.update(ue_socket_transform(socket.matrix_local))
    record["scale"] = [1.0, 1.0, 1.0]
    return record


# --------------------------------------------------------------------------- LODs

def decimate_lods(obj: "bpy.types.Object", ratios: Sequence[float] = (0.5, 0.25)) -> List["bpy.types.Object"]:
    """Create ``<base>_LOD1..n`` copies of ``obj`` decimated (Collapse) by ``ratios``.

    Each copy starts from the **evaluated** mesh of ``obj`` (modifiers baked) with
    an empty modifier stack, so the Decimate ratio applies to the geometry that
    ships rather than to a pre-modifier cage, and no source modifier is
    re-evaluated a second time at export. UVs, custom normals, vertex groups and
    materials are preserved. ``obj`` itself is not renamed.

    Intended for static meshes: an Armature modifier on ``obj`` would be baked at
    its current pose.
    """
    if obj.type != "MESH":
        raise ValueError(f"{obj.name!r} is not a mesh")
    base = lod_base_name(obj.name)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    copies: List[bpy.types.Object] = []
    for level, ratio in enumerate(ratios, start=1):
        if not 0.0 < ratio < 1.0:
            raise ValueError(f"LOD ratio must be in (0, 1); got {ratio}")
        name = f"{base}_LOD{level}"
        if bpy.data.objects.get(name) is not None:
            raise ValueError(f"{name!r} already exists")
        mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=depsgraph)
        copy = obj.copy()
        copy.data = mesh
        copy.modifiers.clear()  # obj.copy() brings the whole stack; the geometry is already baked
        copy.name = name
        copy.data.name = name
        copy.parent = obj.parent
        copy.matrix_parent_inverse = obj.matrix_parent_inverse.copy()
        link_like(copy, obj)
        modifier = copy.modifiers.new(f"LOD{level} decimate", "DECIMATE")
        modifier.decimate_type = "COLLAPSE"
        modifier.ratio = ratio
        modifier.use_collapse_triangulate = True
        apply_modifier(copy, modifier)
        copy["lod_ratio"] = float(ratio)
        copies.append(copy)
    return copies


def rename_with_helpers(obj: "bpy.types.Object", new_name: str) -> List[Tuple[str, str]]:
    """Rename ``obj`` and rewrite the UCX_/UBX_/USP_/UCP_/SOCKET_ children that embed its name.

    Unreal keys collision and sockets to the render node name, so renaming a mesh
    without its helpers silently drops them. Returns the ``(old, new)`` pairs.
    """
    old_name = obj.name
    if new_name == old_name:
        return []
    renamed: List[Tuple[str, str]] = []
    children = [child for child in obj.children_recursive if HELPER_PREFIX_RE.match(child.name)]
    obj.name = new_name
    renamed.append((old_name, new_name))
    for child in children:
        prefix_match = HELPER_PREFIX_RE.match(child.name)
        prefix = prefix_match.group(0)
        if not child.name.startswith(f"{prefix}{old_name}"):
            continue
        child_new = prefix + new_name + child.name[len(prefix) + len(old_name):]
        if bpy.data.objects.get(child_new) is not None:
            raise ValueError(f"Cannot rename {child.name!r} to {child_new!r}: the name is taken")
        old_child = child.name
        child.name = child_new
        if child.data is not None and child.data.name == old_child:
            child.data.name = child_new
        renamed.append((old_child, child_new))
    return renamed


def make_lod_group(name: str, lod_objects: Sequence["bpy.types.Object"]) -> "bpy.types.Object":
    """Create ``<name>_LodGroup`` (Empty, ``fbx_type="LodGroup"``) parenting ``lod_objects``.

    Objects without a ``_LODn`` suffix are renamed to ``<name>_LOD<i>`` in the
    given order (this is how the source mesh becomes ``_LOD0``) **together with
    their UCX_/SOCKET_ children**, so ``UCX_<base>_00`` becomes
    ``UCX_<base>_LOD0_00`` and Unreal still finds the hull. Every object must
    then be named ``<name>_LOD0..n`` or ValueError is raised.
    """
    if not lod_objects:
        raise ValueError("lod_objects is empty")
    group_name = f"{name}_LodGroup"
    if bpy.data.objects.get(group_name) is not None:
        raise ValueError(f"{group_name!r} already exists")
    for level, obj in enumerate(lod_objects):
        expected = f"{name}_LOD{level}"
        if lod_index(obj.name) is None:
            rename_with_helpers(obj, expected)
        if obj.name != expected:
            raise ValueError(f"LOD object {level} is named {obj.name!r}, expected {expected!r}")
    group = bpy.data.objects.new(group_name, None)
    group["fbx_type"] = "LodGroup"
    group.empty_display_type = "PLAIN_AXES"
    group.empty_display_size = 0.25
    link_like(group, lod_objects[0])
    group.matrix_world = Matrix.Identity(4)
    for obj in lod_objects:
        world = obj.matrix_world.copy()
        obj.parent = group
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_world = world
    return group


__all__ = [
    "AXIS_CONVERSION", "AXIS_FORWARD", "AXIS_UP", "COLLISION_PREFIXES", "HELPER_PREFIX_RE",
    "SOCKET_PREFIX", "UE_UNIT_SCALE", "apply_modifier", "decimate_lods", "evaluated_bmesh",
    "helper_children", "link_like", "lod_base_name", "lod_index", "make_lod_group", "make_socket",
    "make_ucx_hull", "rename_with_helpers", "resolve_objects", "selection", "socket_children",
    "socket_record", "transform_is_applied", "ue_rotator", "ue_socket_transform",
]
