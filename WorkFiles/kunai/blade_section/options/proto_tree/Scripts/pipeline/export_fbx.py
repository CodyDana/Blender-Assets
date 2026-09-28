"""Shared FBX export helper (FAB_ASSET_STUDY.md section 3.7).

Every FBX leaves Blender with identical settings: -Y forward / Z up, FBX Units
Scale, space transform on / apply transform off, face smoothing, triangulated,
no tangent space (Unreal recomputes MikkTSpace), no leaf bones, deform bones
only, baked animation only for ``kind="animation"``.

Sockets and LODs (measured on UE 5.8.2, legacy FBX importer):

* a ``SOCKET_`` node must be an **Empty**; a child mesh is not a socket
* a file that contains a ``LodGroup`` keeps its LODs and its UCX hull but
  **loses every socket**, whatever the socket node type. Sockets and LOD import
  are mutually exclusive, so a static export that carries a LodGroup drops the
  ``SOCKET_`` nodes by default (pass ``include_sockets=True`` to keep them and
  get a warning instead)
* every static export that has sockets writes ``<name>.sockets.json`` next to
  the FBX with the Unreal-space transform of each socket, so the import script
  can recreate them with ``unreal.new_object(unreal.StaticMeshSocket, outer=mesh)``
  after the mesh is in. ``Scripts/pipeline/ue_import_sockets.py`` does that.
* an FBX ``LodGroup`` carries **no LOD threshold data**, so Unreal computes its
  own screen sizes on import (measured on UE 5.8.2: 2.0 / 0.75 / 0.5625 for three
  LODs, which parks a small prop on its lowest LOD for the whole gameplay range).
  Any multi-LOD export therefore also writes ``lod_screen_sizes`` into the same
  sidecar - study 4's 1.0 / 0.5 / 0.25 by default - and the import script applies
  it with ``StaticMeshEditorSubsystem.set_lod_screen_sizes``.

Garments (``kind="garment"``, ASSET_GUIDELINES 12.10) are skeletal meshes on the locked character skeleton:

* the armature object must be named ``root``: Blender's importer turned Unreal's root bone into the object, and the
  exporter writes the object back as that node, so any other name adds a bone above ``root`` in Unreal
* EVERY bone is written (``use_armature_deform_only`` off) so the file carries the skeleton exactly as locked,
  including any ``ik_*`` bones (metahuman_base_skel has none - recorded in the base lock)
* primary / secondary bone axes Y / X, the same pair the fitting body was imported with
  (``automatic_bone_orientation`` off, Outfit_Pipeline trap 1), so the bind pose round-trips exactly
* every mesh is parented to that armature with an Armature modifier on it; run ``garment_qa`` first

CLI::

    blender -b file.blend --factory-startup --python Scripts/pipeline/export_fbx.py -- \
        --objects Name1,Name2 --out path/SM_Name.fbx --kind static|skeletal|animation|garment [--exclude A,B]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

_PACKAGE_PARENT = str(Path(__file__).resolve().parents[1])
if _PACKAGE_PARENT not in sys.path:
    sys.path.insert(0, _PACKAGE_PARENT)

import bpy  # noqa: E402

from pipeline.helpers import (  # noqa: E402
    AXIS_FORWARD, AXIS_UP, HELPER_PREFIX_RE, SOCKET_PREFIX, ObjectLike, helper_children, lod_index, resolve_objects,
    selection, socket_record, transform_is_applied,
)

KINDS = ("static", "skeletal", "animation", "garment")
NAME_PREFIXES = ("SM_", "SK_", "A_")
OBJECT_TYPES = {
    "static": {"MESH", "EMPTY"},
    "skeletal": {"ARMATURE", "MESH"},
    "animation": {"ARMATURE"},
    "garment": {"ARMATURE", "MESH"},
}
# Blender's FBX importer makes an Unreal skeleton's root bone the armature object; exporting it under any other
# name puts an extra bone above "root" in Unreal.
GARMENT_ARMATURE_NAME = "root"
SIDECAR_SUFFIX = ".sockets.json"
# Keys popped from ``overrides`` before they reach bpy.ops.export_scene.fbx.
RESERVED_OVERRIDES = ("exclude", "include_sockets", "sidecar", "lod_screen_sizes")
# An FBX LodGroup carries no threshold data, so Unreal invents its own screen sizes on
# import: measured on UE 5.8.2, a three-LOD group arrives as 2.0 / 0.75 / 0.5625, which
# puts a 10 cm prop on its lowest LOD for effectively the whole gameplay range. The
# house convention is study 4's table, 1.0 / 0.5 / 0.25, and it has to be applied after
# import - so it travels in the sidecar with the sockets.
DEFAULT_LOD_SCREEN_SIZES = (1.0, 0.5, 0.25)


def base_settings(kind: str) -> Dict[str, Any]:
    """Return the study 3.7 operator settings for ``kind`` (object_types as a set)."""
    settings: Dict[str, Any] = {
        "use_selection": True,
        "use_visible": False,
        "use_active_collection": False,
        "object_types": set(OBJECT_TYPES[kind]),
        "global_scale": 1.0,
        "apply_unit_scale": True,
        "apply_scale_options": "FBX_SCALE_UNITS",
        "axis_forward": AXIS_FORWARD,
        "axis_up": AXIS_UP,
        "use_space_transform": True,
        "bake_space_transform": False,
        "mesh_smooth_type": "FACE",
        "use_mesh_modifiers": True,
        "use_mesh_modifiers_render": True,
        "use_mesh_edges": False,
        "use_triangles": True,
        "use_tspace": False,
        "use_custom_props": False,
        "add_leaf_bones": False,
        "use_armature_deform_only": True,
        "armature_nodetype": "NULL",
        "primary_bone_axis": "Y",
        "secondary_bone_axis": "X",
        "bake_anim": False,
        "path_mode": "RELATIVE",
        "embed_textures": False,
        "colors_type": "SRGB",
        "batch_mode": "OFF",
    }
    if kind == "garment":
        settings["use_armature_deform_only"] = False  # the whole locked skeleton, ik_* bones included
    if kind == "animation":
        settings.update({
            "bake_anim": True,
            "bake_anim_use_all_bones": True,
            "bake_anim_use_nla_strips": False,
            "bake_anim_use_all_actions": False,
            "bake_anim_force_startend_keying": True,
            "bake_anim_step": 1.0,
            "bake_anim_simplify_factor": 0.0,
        })
    return settings


def _validate_scene() -> None:
    units = bpy.context.scene.unit_settings
    if units.system != "METRIC" or abs(units.scale_length - 1.0) > 1e-6:
        raise ValueError(f"Scene units must be METRIC with unit scale 1.0 (found {units.system}, {units.scale_length})")


def _validate_filepath(filepath: str) -> None:
    basename = os.path.basename(filepath)
    if not basename.startswith(NAME_PREFIXES):
        raise ValueError(f"FBX basename {basename!r} must start with one of {NAME_PREFIXES}")
    if not basename.lower().endswith(".fbx"):
        raise ValueError(f"FBX filepath {basename!r} must end with .fbx")


def _validate_transforms(objects: Iterable["bpy.types.Object"]) -> None:
    problems = []
    for obj in objects:
        if obj.name.startswith(SOCKET_PREFIX):
            continue  # sockets carry intentional local offsets and rotations
        ok, detail = transform_is_applied(obj)
        if not ok:
            problems.append(f"{obj.name}: {detail}")
    if problems:
        raise ValueError("Unapplied rotation/scale on: " + "; ".join(problems))


def _garment_selection(selected: List["bpy.types.Object"]) -> List["bpy.types.Object"]:
    """Validate a garment export and add the armature the meshes are skinned to; raise ValueError on a bad setup."""
    meshes = [obj for obj in selected if obj.type == "MESH"]
    others = [obj.name for obj in selected if obj.type not in {"MESH", "ARMATURE"}]
    if not meshes:
        raise ValueError("A garment export needs at least one mesh")
    if others:
        raise ValueError(f"A garment export takes meshes and their armature only, not {others}")
    armatures = {m.object for obj in meshes for m in obj.modifiers if m.type == "ARMATURE" and m.object is not None}
    armatures |= {obj for obj in selected if obj.type == "ARMATURE"}
    if len(armatures) != 1:
        raise ValueError(f"A garment export needs exactly one armature, found {sorted(a.name for a in armatures)}")
    armature = next(iter(armatures))
    if armature.name != GARMENT_ARMATURE_NAME:
        raise ValueError(f"The garment armature is named {armature.name!r}; it must be {GARMENT_ARMATURE_NAME!r} "
                         f"or Unreal adds a bone above the skeleton's root")
    unbound = [obj.name for obj in meshes
               if obj.parent != armature or not any(m.type == "ARMATURE" and m.object == armature for m in obj.modifiers)]
    if unbound:
        raise ValueError(f"Garment meshes must be parented to {armature.name!r} with an Armature modifier: {unbound}")
    bad_names = [obj.name for obj in meshes if not obj.name.startswith("SK_")]
    if bad_names:
        raise ValueError(f"Garment meshes must be named SK_*: {bad_names}")
    return meshes + [armature]


def _is_lod_group(obj: "bpy.types.Object") -> bool:
    return obj.type == "EMPTY" and obj.get("fbx_type") == "LodGroup"


def sidecar_path(filepath: str) -> str:
    """Path of the socket sidecar that belongs to ``filepath``."""
    return str(Path(filepath).with_suffix("")) + SIDECAR_SUFFIX


def lod_screen_sizes(lod_count: int, sizes: Optional[Iterable[float]] = None) -> List[float]:
    """``lod_count`` screen sizes: the house table, extended as halves past its end."""
    table = list(sizes if sizes is not None else DEFAULT_LOD_SCREEN_SIZES)
    while len(table) < lod_count:
        table.append(round(table[-1] * 0.5, 6))
    return [float(value) for value in table[:lod_count]]


def write_socket_sidecar(filepath: str, sockets: List[Dict[str, Any]],
                         screen_sizes: Optional[List[float]] = None) -> Optional[str]:
    """Write ``<name>.sockets.json`` for the Unreal-side post-import step; return its path."""
    if not sockets and not screen_sizes:
        return None
    path = sidecar_path(filepath)
    payload = {
        "fbx": os.path.basename(filepath),
        "axis": {"forward": AXIS_FORWARD, "up": AXIS_UP},
        "note": ("Unreal 5.8.2 drops FBX sockets from any file that contains a LodGroup, so recreate "
                 "them after import with unreal.new_object(unreal.StaticMeshSocket, outer=mesh); the bare "
                 "unreal.StaticMeshSocket() constructor is outered to /Engine/Transient and is silently "
                 "lost on save. Locations are cm, rotations are Unreal rotator degrees. "
                 "lod_screen_sizes must also be applied after import: an FBX LodGroup carries no "
                 "thresholds, so Unreal computes its own (measured 2.0 / 0.75 / 0.5625 on a three-LOD "
                 "group) and the asset sits on its lowest LOD almost always."),
        "sockets": sockets,
    }
    if screen_sizes:
        payload["lod_screen_sizes"] = screen_sizes
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def export_fbx(filepath: str, objects: Iterable[ObjectLike], kind: str = "static", **overrides: Any) -> Dict[str, Any]:
    """Export ``objects`` (names or objects) to ``filepath`` with the house FBX settings.

    ``kind`` is ``"static"``, ``"skeletal"``, ``"animation"`` or ``"garment"`` (see the module docstring). For static
    exports the UCX_/UBX_/USP_/UCP_/SOCKET_ and ``_LODn`` children of each object
    are selected too, except that ``SOCKET_`` nodes are dropped from a file that
    contains a LodGroup (Unreal cannot import both; see the module docstring) —
    pass ``include_sockets=True`` to keep them anyway. Reserved keywords:
    ``exclude`` (names/objects to drop), ``include_sockets`` and ``sidecar``
    (set False to skip the socket JSON); all other ``overrides`` are FBX
    operator keywords applied last.

    Raises ValueError for an unapplied rotation/scale, a non-metric scene, a
    basename without an SM_/SK_/A_ prefix or an empty selection. Returns
    ``{"filepath", "objects", "settings", "warnings", "sockets", "sidecar"}``.
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    filepath = str(filepath)
    _validate_filepath(filepath)
    _validate_scene()
    exclude_raw = overrides.pop("exclude", ()) or ()
    exclude: Set[str] = {item if isinstance(item, str) else item.name for item in exclude_raw}
    include_sockets = bool(overrides.pop("include_sockets", False))
    write_sidecar = bool(overrides.pop("sidecar", True))
    screen_size_override = overrides.pop("lod_screen_sizes", None)
    for key in RESERVED_OVERRIDES:
        overrides.pop(key, None)

    requested = resolve_objects(objects)
    if not requested:
        raise ValueError("No objects to export")
    selected: List[bpy.types.Object] = []
    for obj in requested:
        if obj.name in exclude:
            continue
        if obj not in selected:
            selected.append(obj)
        if kind == "static":
            for child in helper_children(obj, exclude):
                if child not in selected:
                    selected.append(child)
    if not selected:
        raise ValueError(f"No objects left to export after exclude={sorted(exclude)}")
    if kind == "garment":
        if not os.path.basename(filepath).startswith("SK_"):
            raise ValueError(f"A garment FBX must be named SK_*.fbx, got {os.path.basename(filepath)!r}")
        selected = _garment_selection(selected)

    warnings: List[str] = []
    socket_objects = [obj for obj in selected if obj.name.startswith(SOCKET_PREFIX)]
    has_lod_group = any(_is_lod_group(obj) for obj in selected)
    dropped_sockets: List[str] = []
    if kind == "static" and socket_objects and has_lod_group:
        if include_sockets:
            warnings.append("This file has a LodGroup and SOCKET_ nodes: UE 5.8.2 imports the LODs and "
                            "discards every socket. Use the .sockets.json sidecar after import.")
        else:
            dropped_sockets = [obj.name for obj in socket_objects]
            selected = [obj for obj in selected if obj not in socket_objects]
            warnings.append("SOCKET_ nodes dropped from this LodGroup export (UE 5.8.2 cannot import LODs "
                            "and sockets from one file); they are in the sidecar: " + ", ".join(dropped_sockets))
    mesh_sockets = [obj.name for obj in socket_objects if obj.type != "EMPTY"]
    if mesh_sockets:
        warnings.append("SOCKET_ nodes that are not Empties are not sockets in UE 5.8.2 and inflate the "
                        "render mesh: " + ", ".join(mesh_sockets))
    _validate_transforms(selected)

    settings = base_settings(kind)
    meshes = [obj for obj in selected if obj.type == "MESH"]
    if kind == "animation" and meshes:
        settings["object_types"].add("MESH")
    shape_keyed = [obj.name for obj in meshes if obj.data.shape_keys is not None]
    if shape_keyed:
        settings["use_mesh_modifiers"] = False
        warnings.append("use_mesh_modifiers disabled because of shape keys on: " + ", ".join(shape_keyed))
    if kind == "static":
        helpers = [obj.name for obj in selected if HELPER_PREFIX_RE.match(obj.name)]
        socketed = {obj.parent.name for obj in selected if obj.name.startswith(SOCKET_PREFIX) and obj.parent}
        if len(socketed) > 1:
            warnings.append("Unreal imports one socketed mesh per FBX; sockets found on: " + ", ".join(sorted(socketed)))
        if not helpers:
            warnings.append("no UCX_/SOCKET_ helper children were found for this static export")
    unknown = [key for key in overrides if key not in bpy.ops.export_scene.fbx.get_rna_type().properties.keys()]
    if unknown:
        raise ValueError(f"Unknown FBX export override(s): {unknown}")
    settings.update(overrides)
    if not isinstance(settings["object_types"], set):
        settings["object_types"] = set(settings["object_types"])

    directory = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(directory, exist_ok=True)
    active = next((obj for obj in selected if obj.type == "ARMATURE"), selected[0])
    with selection(selected, active):
        result = bpy.ops.export_scene.fbx(filepath=filepath, **settings)
    if "FINISHED" not in result:
        raise RuntimeError(f"FBX export failed: {result}")

    sockets: List[Dict[str, Any]] = []
    for socket in socket_objects:
        if socket.parent is None:
            warnings.append(f"{socket.name} has no parent mesh and cannot become a socket")
            continue
        record = socket_record(socket.parent, socket)
        record["in_fbx"] = socket.name not in dropped_sockets
        sockets.append(record)
    lod_count = sum(1 for obj in selected if obj.type == "MESH" and lod_index(obj.name) is not None
                    and not HELPER_PREFIX_RE.match(obj.name))
    screen_sizes = lod_screen_sizes(lod_count, screen_size_override) if lod_count > 1 else None
    sidecar = write_socket_sidecar(filepath, sockets, screen_sizes) if write_sidecar else None

    reported = dict(settings)
    reported["object_types"] = sorted(settings["object_types"])
    return {
        "filepath": filepath,
        "objects": [obj.name for obj in selected],
        "settings": reported,
        "warnings": warnings,
        "sockets": sockets,
        "lod_screen_sizes": screen_sizes,
        "sidecar": sidecar,
    }


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="export_fbx.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--objects", required=True, help="comma-separated object names")
    parser.add_argument("--out", required=True, help="output .fbx path (basename SM_/SK_/A_)")
    parser.add_argument("--kind", default="static", choices=KINDS)
    parser.add_argument("--exclude", default="", help="comma-separated helper children to leave out")
    parser.add_argument("--include-sockets", action="store_true",
                        help="keep SOCKET_ nodes in a LodGroup file (UE 5.8.2 will still drop them)")
    parser.add_argument("--no-sidecar", action="store_true", help="do not write <name>.sockets.json")
    return parser.parse_args(argv)


def main() -> int:
    """CLI entry point: export and print the result as JSON."""
    try:
        args = _parse_args()
        names = [name.strip() for name in args.objects.split(",") if name.strip()]
        exclude = [name.strip() for name in args.exclude.split(",") if name.strip()]
        result = export_fbx(args.out, names, kind=args.kind, exclude=exclude,
                            include_sockets=args.include_sockets, sidecar=not args.no_sidecar)
    except Exception as exc:  # noqa: BLE001 - the CLI contract is JSON on stdout plus exit 1
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
