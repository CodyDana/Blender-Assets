"""Blender 5.2 -> Unreal 5.8 asset pipeline package (FAB_ASSET_STUDY.md section 3).

Modules that touch bpy (export_fbx, qa_check, helpers, textures, garment_qa,
garment_helpers) only import
inside Blender; ``lock`` is stdlib-only and also runs under the system Python.
``ue_import_sockets`` runs inside an Unreal commandlet and imports neither.
"""
from __future__ import annotations

VERSION = "1.2.0"  # 1.2.0 (2026-09-27): garments exported in cm; 1.1.0 (2026-09-26): garment gates, kind "garment"

from .lock import LockError, LockHeldError, LockMissingError, assert_owner, claim, list_locks, release, status  # noqa: E402

try:
    import bpy  # noqa: F401
except ImportError:  # system Python: only the lock API is available
    bpy = None  # type: ignore[assignment]

if bpy is not None:
    from .export_fbx import export_fbx, lod_screen_sizes, sidecar_path, write_socket_sidecar
    from .helpers import (
        apply_modifier, decimate_lods, evaluated_bmesh, helper_children, make_lod_group, make_socket,
        make_ucx_hull, rename_with_helpers, resolve_objects, socket_children, socket_record,
        transform_is_applied, ue_rotator, ue_socket_transform,
    )
    from .qa_check import qa_check
    from .garment_qa import qa_garment
    from .textures import bake_ao, flip_normal_green, image_pixels, is_power_of_two, load_data_image, pack_orm, write_png

__all__ = [
    "VERSION", "LockError", "LockHeldError", "LockMissingError", "assert_owner", "claim", "list_locks",
    "release", "status",
]
if bpy is not None:
    __all__ += [
        "export_fbx", "lod_screen_sizes", "sidecar_path", "write_socket_sidecar", "qa_check", "qa_garment",
        "apply_modifier", "decimate_lods",
        "evaluated_bmesh", "helper_children", "make_lod_group", "make_socket", "make_ucx_hull",
        "rename_with_helpers", "resolve_objects", "socket_children", "socket_record", "transform_is_applied",
        "ue_rotator", "ue_socket_transform", "bake_ao", "flip_normal_green", "image_pixels",
        "is_power_of_two", "load_data_image", "pack_orm", "write_png",
    ]
