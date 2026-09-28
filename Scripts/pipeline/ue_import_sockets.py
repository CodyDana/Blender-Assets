"""Apply what an FBX cannot carry to an imported Static Mesh (runs inside Unreal).

Two things: the sockets an FBX with a LodGroup loses, and the LOD screen sizes an
FBX LodGroup never had. Both travel in ``<name>.sockets.json`` beside the FBX.


Unreal 5.8.2's legacy FBX importer drops every ``SOCKET_`` node from a file that
contains a LodGroup, so ``pipeline.export_fbx`` writes the sockets to
``<name>.sockets.json`` beside the FBX and this module puts them back after the
import. Verified on UE 5.8.2 by reloading the saved asset in a second
commandlet process:

* ``unreal.new_object(unreal.StaticMeshSocket, outer=mesh)`` persists
* the bare ``unreal.StaticMeshSocket()`` constructor is outered to
  ``/Engine/Transient``: the socket shows up in the in-process component query,
  ``save_loaded_asset`` returns True, and the socket is **silently gone** when
  the asset is loaded again. Never use it, and never trust a socket assertion
  made in the process that wrote it.

``mesh.modify()`` and ``mark_package_dirty()`` are not required.

Usage inside a commandlet script::

    from pipeline.ue_import_sockets import apply_sidecar
    result = apply_sidecar(r"...\\SM_TestCrate.sockets.json", "/Game/Props/SM_TestCrate")

CLI (through the pythonscript commandlet)::

    UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript \
        -script="Scripts/pipeline/ue_import_sockets.py -- --sidecar <path> --asset /Game/Props/SM_TestCrate"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import unreal  # type: ignore[import-not-found]  # noqa: F401 - provided by the Unreal Python environment

NAME_FIELDS = ("socket", "fbx_node")


def load_sidecar(sidecar: str) -> List[Dict[str, Any]]:
    """Return the socket records of a ``<name>.sockets.json`` written by export_fbx."""
    payload = json.loads(Path(sidecar).read_text(encoding="utf-8"))
    records = payload.get("sockets", [])
    if not isinstance(records, list):
        raise ValueError(f"{sidecar}: 'sockets' is not a list")
    return records


def _rotator(rotation: Dict[str, float]) -> "unreal.Rotator":
    """Build a Rotator by name, because the constructor's positional order is easy to get wrong."""
    rotator = unreal.Rotator()
    rotator.roll = float(rotation.get("roll", 0.0))
    rotator.pitch = float(rotation.get("pitch", 0.0))
    rotator.yaw = float(rotation.get("yaw", 0.0))
    return rotator


def apply_sockets(mesh: "unreal.StaticMesh", records: Iterable[Dict[str, Any]],
                  name_from: str = "socket", replace: bool = True) -> List[Dict[str, Any]]:
    """Create one ``StaticMeshSocket`` per record on ``mesh`` and return what was set.

    ``name_from`` picks the socket name: ``"socket"`` is the short authored name
    (``Lid``), ``"fbx_node"`` the full node name the FBX importer would have
    produced (``SM_TestCrate_LOD0_Lid``).

    A socket the FBX importer created for the same record is removed first, even
    when it has the other name: a socket that arrives through the FBX inherits
    the exporter's unit scale as ``relative_scale`` (measured: 100, 100, 100),
    which would scale anything attached to it a hundredfold.
    """
    if name_from not in NAME_FIELDS:
        raise ValueError(f"name_from must be one of {NAME_FIELDS}, got {name_from!r}")
    applied: List[Dict[str, Any]] = []
    for record in records:
        name = record.get(name_from) or record.get("socket")
        if not name:
            continue
        if name_from == "fbx_node" and name.startswith("SOCKET_"):
            name = name[len("SOCKET_"):]
        aliases = {name}
        for field in NAME_FIELDS:
            other = record.get(field)
            if other:
                aliases.add(other[len("SOCKET_"):] if other.startswith("SOCKET_") else other)
        existing = mesh.find_socket(name)
        if existing is not None and not replace:
            applied.append({"socket": str(name), "skipped": "already present"})
            continue
        removed = []
        for alias in sorted(aliases):
            stale = mesh.find_socket(alias)
            if stale is not None:
                mesh.remove_socket(stale)
                removed.append(alias)
        location = record.get("location_cm", [0.0, 0.0, 0.0])
        scale = record.get("scale") or [1.0, 1.0, 1.0]
        socket = unreal.new_object(unreal.StaticMeshSocket, outer=mesh)  # never the bare constructor
        socket.set_editor_property("socket_name", name)
        socket.set_editor_property("relative_location", unreal.Vector(*[float(v) for v in location]))
        socket.set_editor_property("relative_rotation", _rotator(record.get("rotation_deg", {})))
        socket.set_editor_property("relative_scale", unreal.Vector(*[float(v) for v in scale]))
        mesh.add_socket(socket)
        applied.append({"socket": str(name), "location_cm": [float(v) for v in location],
                        "rotation_deg": record.get("rotation_deg", {}), "scale": [float(v) for v in scale],
                        "replaced": removed})
    return applied


def _static_mesh_editor_subsystem():
    """Return a usable StaticMeshEditorSubsystem, or None.

    Measured on UE 5.8.2 under ``-run=pythonscript``:
    ``get_editor_subsystem(StaticMeshEditorSubsystem)`` returns **None** in a
    commandlet, but ``unreal.new_object(unreal.StaticMeshEditorSubsystem)`` works
    and its methods take effect (``add_uv_channel`` moved the channel count 1 -> 2
    in the same process). Try the documented route first anyway, because it is the
    correct one inside a real editor session.
    """
    try:
        subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    except Exception:  # noqa: BLE001 - absent on some configurations
        subsystem = None
    if subsystem is None:
        try:
            subsystem = unreal.new_object(unreal.StaticMeshEditorSubsystem)
        except Exception:  # noqa: BLE001
            subsystem = None
    return subsystem


def apply_lod_screen_sizes(mesh: "unreal.StaticMesh", sizes: List[float]) -> Dict[str, Any]:
    """Set the LOD screen sizes an FBX LodGroup cannot carry.

    An imported LodGroup has no thresholds of its own, so Unreal invents them
    (measured 2.0 / 0.75 / 0.5625 for three LODs). Left alone, a small prop runs on
    its lowest LOD at almost any camera distance. ``sizes`` comes from the
    ``lod_screen_sizes`` field ``pipeline.export_fbx`` writes into the sidecar.
    """
    result: Dict[str, Any] = {"requested": [float(v) for v in sizes]}
    subsystem = _static_mesh_editor_subsystem()
    if subsystem is None:
        result["error"] = "StaticMeshEditorSubsystem unavailable"
        return result
    try:
        result["before"] = [float(v) for v in subsystem.get_lod_screen_sizes(mesh)]
        count = int(subsystem.get_lod_count(mesh))
        applied = [float(v) for v in sizes][:count]
        subsystem.set_lod_screen_sizes(mesh, applied)
        result["applied"] = applied
        result["after"] = [float(v) for v in subsystem.get_lod_screen_sizes(mesh)]
        result["changed"] = result["after"] != result.get("before")
    except Exception as exc:  # noqa: BLE001 - never fail an import over a threshold
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def apply_sidecar(sidecar: str, asset_path: str, name_from: str = "socket", save: bool = True) -> Dict[str, Any]:
    """Apply ``sidecar`` to the Static Mesh at ``asset_path`` and save it.

    Applies both halves of what the FBX cannot carry: the sockets, and the LOD
    screen sizes. Returns ``{"asset", "sidecar", "applied", "lod_screen_sizes",
    "saved", "sockets"}``. Verify the result by loading the asset again in a
    **fresh** process: an in-process query cannot tell a persisted socket from a
    transient one.
    """
    mesh = unreal.load_asset(asset_path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise TypeError(f"{asset_path} is a {type(mesh).__name__}, not a StaticMesh")
    payload = json.loads(Path(sidecar).read_text(encoding="utf-8"))
    applied = apply_sockets(mesh, load_sidecar(sidecar), name_from=name_from)
    screen_sizes = payload.get("lod_screen_sizes") or []
    lod_result = apply_lod_screen_sizes(mesh, screen_sizes) if screen_sizes else None
    touched = bool(applied) or bool(lod_result and lod_result.get("changed"))
    saved = bool(unreal.EditorAssetLibrary.save_loaded_asset(mesh)) if save and touched else False
    component = unreal.new_object(unreal.StaticMeshComponent)
    component.set_static_mesh(mesh)
    return {
        "asset": asset_path,
        "sidecar": str(sidecar),
        "applied": applied,
        "lod_screen_sizes": lod_result,
        "saved": saved,
        "sockets": [str(name) for name in component.get_all_socket_names()],
    }


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(prog="ue_import_sockets.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sidecar", required=True, help="path to <name>.sockets.json")
    parser.add_argument("--asset", required=True, help="/Game/... path of the imported Static Mesh")
    parser.add_argument("--name-from", default="socket", choices=NAME_FIELDS)
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--json", default=None, help="also write the result to this path")
    return parser.parse_args(argv)


def main() -> int:
    """CLI entry point: apply the sidecar and log the result as JSON."""
    try:
        args = _parse_args()
        result = apply_sidecar(args.sidecar, args.asset, name_from=args.name_from, save=not args.no_save)
    except Exception as exc:  # noqa: BLE001 - the commandlet log is the only channel
        unreal.log_error(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
        return 1
    text = json.dumps(result, indent=2, default=str)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(text, encoding="utf-8")
    unreal.log("PIPELINE_SOCKETS " + json.dumps(result, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
