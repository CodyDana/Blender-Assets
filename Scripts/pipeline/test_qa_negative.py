"""Negative tests for ``qa_check``: every defect must fail, and only that defect.

Run::

    blender -b --factory-startup --python Scripts/pipeline/test_qa_negative.py

Each case builds a small scene in which exactly one thing is wrong and asserts
that the set of failing check names equals the expected set - a gate that passes
a broken asset is worse than no gate, and a gate that fails a legitimate one
(an open mesh, a mirrored UV shell offset by +1 in U) gets switched off. The
cases cover the review findings: the n-gon, overlapping UV, unapplied scale and
missing UCX defects; the ``UCX_<base>_NN`` spelling Unreal silently drops on a
``<base>_LOD0`` node; a socket authored as a child mesh; the CamelCase gap in
the franchise deny list; boundary edges counted as non-manifold; and UV0 checks
that graded whichever layer happened to be active.

Writes WorkFiles/pipeline_test/test_qa_negative.json and exits non-zero on any
unexpected result.
"""
from __future__ import annotations

import json
import math
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles" / "pipeline_test"
SCRIPTS = ROOT / "Scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import bmesh  # noqa: E402
import bpy  # noqa: E402

from pipeline.helpers import make_socket, make_ucx_hull  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402

Case = Tuple[str, "bpy.types.Object", Set[str], Dict[str, Any]]


def fresh_scene() -> None:
    """Empty metric scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0


def _layout_uvs(bm: "bmesh.types.BMesh", layer: Any, single_cell: bool = False) -> None:
    """Give every face its own UV cell (or all faces the same cell, which overlaps)."""
    faces = list(bm.faces)
    columns = max(1, math.ceil(math.sqrt(len(faces))))
    cell = 1.0 / columns
    radius = cell * 0.35
    for index, face in enumerate(faces):
        column = 0 if single_cell else index % columns
        row = 0 if single_cell else index // columns
        centre = ((column + 0.5) * cell, (row + 0.5) * cell)
        corners = len(face.loops)
        for corner, loop in enumerate(face.loops):
            angle = 2.0 * math.pi * corner / corners
            loop[layer].uv = (centre[0] + radius * math.cos(angle), centre[1] + radius * math.sin(angle))


def build_mesh(name: str, edit: Optional[Callable[["bmesh.types.BMesh"], None]] = None,
               overlap_uv0: bool = False, extra_uv: Optional[str] = None,
               overlap_extra_uv: bool = True, active_uv: int = 0) -> "bpy.types.Object":
    """Build a 1 m cube named ``name`` with laid-out UVs; ``edit`` may change the topology first."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    if edit is not None:
        edit(bm)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    _layout_uvs(bm, bm.loops.layers.uv.new("UV0"), single_cell=overlap_uv0)
    if extra_uv:
        _layout_uvs(bm, bm.loops.layers.uv.new(extra_uv), single_cell=overlap_extra_uv)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    if len(mesh.uv_layers) > active_uv:
        mesh.uv_layers.active_index = active_uv
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    return obj


def _add_loose_face(bm: "bmesh.types.BMesh") -> None:
    """Attach a third face to an existing edge, which is the real non-manifold defect."""
    bm.edges.ensure_lookup_table()
    edge = bm.edges[0]
    apex = bm.verts.new(edge.verts[0].co + (edge.verts[0].co - edge.verts[1].co).orthogonal() * 0.5)
    bm.faces.new((edge.verts[0], edge.verts[1], apex))


def _make_ngon(bm: "bmesh.types.BMesh") -> None:
    """Subdivide one edge so its two neighbouring quads become pentagons."""
    bm.edges.ensure_lookup_table()
    bmesh.ops.subdivide_edges(bm, edges=[bm.edges[0]], cuts=1, use_grid_fill=False)


def _delete_face(bm: "bmesh.types.BMesh") -> None:
    """Open the mesh: boundary edges must not count as non-manifold."""
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[0]], context="FACES_ONLY")


def _split_bevel_runout(bm: "bmesh.types.BMesh") -> None:
    """Reproduce the defect a clamped bmesh bevel leaves at a run-out.

    A face is split into a sliver whose first and third vertex sit at exactly the
    same place: one coincident pair, one zero-length edge and one zero-area
    triangle. Every other check is blind to it - the sliver stitches the split
    shut, so the mesh still reads as closed and manifold.
    """
    bm.faces.ensure_lookup_table()
    face = bm.faces[0]
    verts = list(face.verts)
    bmesh.ops.delete(bm, geom=[face], context="FACES_ONLY")
    twin = bm.verts.new(verts[0].co.copy())
    bm.verts.ensure_lookup_table()
    bm.faces.new((verts[0], verts[1], twin))       # the zero-area sliver
    bm.faces.new([twin] + verts[1:])               # the real face, now on the twin


def cases() -> Iterator[Case]:
    """Yield (name, object, expected failing checks, qa_check kwargs) one scene at a time.

    This is a generator on purpose: each ``fresh_scene`` invalidates the objects
    of the previous case, so every case must be checked before the next is built.
    """

    # Control: a clean asset with a correctly named hull must pass everything.
    fresh_scene()
    clean = build_mesh("SM_CleanCrate")
    make_ucx_hull(clean)
    yield ("clean_control", clean, set(), {})

    # 1. n-gon
    fresh_scene()
    ngon = build_mesh("SM_NgonCrate", edit=_make_ngon)
    make_ucx_hull(ngon)
    yield ("ngon", ngon, {"no_ngons"}, {})

    # 2. overlapping UVs on UV0
    fresh_scene()
    overlap = build_mesh("SM_OverlapCrate", overlap_uv0=True)
    make_ucx_hull(overlap)
    yield ("overlapping_uv", overlap, {"uv_no_overlap"}, {})

    # 3. unapplied scale
    fresh_scene()
    scaled = build_mesh("SM_ScaledCrate")
    make_ucx_hull(scaled)
    scaled.scale = (2.0, 1.0, 1.0)
    bpy.context.view_layer.update()
    yield ("unapplied_scale", scaled, {"transforms_applied"}, {})

    # 4. missing UCX hull
    fresh_scene()
    no_hull = build_mesh("SM_NoHullCrate")
    yield ("missing_ucx", no_hull, {"ucx_present"}, {})

    # 5. hull named for the pre-rename base: Unreal keys collision to the render node name,
    #    so UCX_SM_RenamedCrate_00 under a node called SM_RenamedCrate_LOD0 is dropped.
    fresh_scene()
    renamed = build_mesh("SM_RenamedCrate")
    make_ucx_hull(renamed)
    renamed.name = "SM_RenamedCrate_LOD0"  # rename without the helper fix-up
    yield ("stale_ucx_name", renamed, {"ucx_present", "collision_name_matches_mesh"}, {})

    # 6. socket authored as a child mesh instead of an Empty
    fresh_scene()
    mesh_socket = build_mesh("SM_MeshSocketCrate")
    make_ucx_hull(mesh_socket)
    make_socket(mesh_socket, "Lid", (0.0, 0.0, 0.5), socket_as_mesh=True)
    yield ("socket_as_mesh", mesh_socket, {"socket_is_empty"}, {})

    # 7. franchise/brand string in a CamelCase name
    fresh_scene()
    branded = build_mesh("SM_KamishBlade")
    make_ucx_hull(branded)
    yield ("franchise_name", branded, {"no_franchise_strings"}, {})

    # 8. open mesh: boundary edges are reported but must not fail
    fresh_scene()
    open_mesh = build_mesh("SM_OpenCrate", edit=_delete_face)
    make_ucx_hull(open_mesh)
    yield ("open_mesh_passes", open_mesh, set(), {})

    # 9. three faces on one edge: the real non-manifold defect must still fail
    fresh_scene()
    non_manifold = build_mesh("SM_NonManifoldCrate", edit=_add_loose_face)
    make_ucx_hull(non_manifold)
    yield ("non_manifold", non_manifold, {"no_non_manifold_edges"}, {})

    # 10. clean UV0 with the lightmap layer active and overlapping: UV0 is what gets graded
    fresh_scene()
    lightmap = build_mesh("SM_LightmapCrate", extra_uv="UV1", overlap_extra_uv=True, active_uv=1)
    make_ucx_hull(lightmap)
    yield ("uv1_active_uv0_graded", lightmap, set(), {})
    yield ("uv1_required_and_broken", lightmap, {"uv1_no_overlap"}, {"require_uv1": True})

    # 11. UV0 mirrored shell offset by +1 in U (study 3.3) must pass, and leaving the tile
    #     range must still fail.
    fresh_scene()
    mirrored = build_mesh("SM_MirroredCrate")
    make_ucx_hull(mirrored)
    for loop in mirrored.data.uv_layers[0].uv:
        loop.vector[0] += 1.0
    yield ("mirrored_u_offset", mirrored, set(), {})
    yield ("uv0_outside_tile_range", mirrored, {"uv0_tile_range"}, {"uv0_tile_range": (0.0, 1.0)})

    # 12. degenerate geometry at a bevel run-out: a coincident vertex pair, a zero-length
    #     edge and a zero-area triangle. A shipped shuriken carried 16 of each and passed
    #     all 46 checks; Unreal stripped them on import and reported 32 fewer triangles
    #     than Blender. The non-manifold, n-gon and UV checks all stay green here, which
    #     is the point: nothing else in the gate can see this class.
    fresh_scene()
    degenerate = build_mesh("SM_DegenerateCrate", edit=_split_bevel_runout)
    make_ucx_hull(degenerate)
    yield ("degenerate_bevel_runout", degenerate,
           {"no_zero_length_edges", "no_degenerate_faces", "no_coincident_vertices"}, {})



def main() -> int:
    """Run every case; return the process exit code."""
    OUT.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Any] = {"status": "failed", "cases": {}}
    report_path = OUT / "test_qa_negative.json"
    problems: List[str] = []
    try:
        for name, obj, expected, kwargs in cases():
            result = qa_check([obj], **kwargs)
            failing = {check["name"] for check in result["checks"] if not check["passed"]}
            details = [f"{check['name']}: {check['detail']}" for check in result["checks"] if not check["passed"]]
            report["cases"][name] = {"object": obj.name, "expected": sorted(expected),
                                     "failed": sorted(failing), "passed": result["passed"],
                                     "details": details}
            if failing != expected:
                problems.append(f"{name}: failing checks {sorted(failing)} != expected {sorted(expected)}")
            if bool(expected) == result["passed"]:
                problems.append(f"{name}: qa_check passed={result['passed']} with expected={sorted(expected)}")
        report["status"] = "passed" if not problems else "failed"
        report["problems"] = problems
    except Exception:  # noqa: BLE001 - the report must record any failure
        report["error"] = traceback.format_exc()
        problems.append(report["error"])
    finally:
        report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    if problems:
        for problem in problems:
            print(problem)
        print(f"QA_NEGATIVE_TEST_FAILED {report_path}", flush=True)
        return 1
    print(f"QA_NEGATIVE_TEST_PASSED {report_path} cases={len(report['cases'])}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
