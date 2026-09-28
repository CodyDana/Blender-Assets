"""Headless self-test for the pipeline package.

Run::

    blender -b --factory-startup --python Scripts/pipeline/test_pipeline.py

Builds SM_TestCrate (0.8 m beveled box, Smart UV Project, baked-AO ORM and a
DirectX normal), adds a UCX hull, a "Lid" socket Empty and a LOD group, runs
``qa_check`` and exports FBX files into WorkFiles/pipeline_test/, then
round-trips them through Blender's FBX importer. It also re-asserts the
Unreal-space socket transform against the values UE 5.8.2 reported for three
exported variants, so a change to the axis pair or to the socket correction
cannot pass silently. Writes test_report.json and SM_TestCrate.blend there.
Exits non-zero on any failure.
"""
from __future__ import annotations

import json
import math
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles" / "pipeline_test"
SCRIPTS = ROOT / "Scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Euler, Matrix  # noqa: E402

from pipeline import VERSION  # noqa: E402
from pipeline.export_fbx import export_fbx, sidecar_path  # noqa: E402
from pipeline.helpers import (  # noqa: E402
    apply_modifier, decimate_lods, make_lod_group, make_socket, make_ucx_hull, ue_socket_transform,
)
from pipeline.qa_check import DENY_RE, qa_check  # noqa: E402
from pipeline.textures import (  # noqa: E402
    bake_ao, flip_normal_green, image_pixels, is_power_of_two, load_data_image, pack_orm, write_png,
)

ASSET = "SM_TestCrate"
LOD0 = f"{ASSET}_LOD0"
SIZE = 512

# Measured on UE 5.8.2 (WorkFiles/pipeline_test/UnrealTest/Validation/legacy_report.json):
# a socket Empty exported with the house axis pair arrives at these transforms.
UE_SOCKET_CASES = [
    ("identity", (0.0, 0.0, 0.0), (0.0, 0.0, 0.8), [0.0, 0.0, 80.0], (180.0, 0.0, 180.0)),
    ("blender_y180", (0.0, math.pi, 0.0), (0.0, 0.0, 0.8), [0.0, 0.0, 80.0], (0.0, 0.0, 0.0)),
    ("blender_z90", (0.0, 0.0, math.pi / 2), (0.1, 0.2, 0.8), [10.0, -20.0, 80.0], (180.0, 0.0, 90.0)),
]
# Names the deny list missed before the CamelCase fix, and names it must not flag.
DENY_MUST_HIT = ("SM_KamishBlade", "SM_NarutoSeal", "T_Gilgamesh2K", "SM_AWM01",
                 "M_SoloLevelingDagger", "SM_Kamish2", "SM_kamishdagger", "SM_JinMuWon_Blade", "SM_EA2")
DENY_MUST_MISS = ("SM_Sea_Blade", "SM_Feather", "SM_Ocean_Rock", "SM_Beam_01", "SM_Crate")


def check(condition: bool, message: str) -> None:
    """Raise AssertionError with ``message`` when ``condition`` is false."""
    if not condition:
        raise AssertionError(message)


def angles_equal(got: float, expected: float, tolerance: float = 1e-4) -> bool:
    """Compare two angles in degrees modulo 360."""
    return abs(((got - expected + 180.0) % 360.0) - 180.0) < tolerance


def fresh_scene() -> "bpy.types.Scene":
    """Start from an empty factory scene in metres."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    return scene


def build_crate() -> "bpy.types.Object":
    """0.8 m box, Bevel (3 segments, harden normals) + Weighted Normal applied, smart-projected UVs."""
    bpy.ops.mesh.primitive_cube_add(size=0.8, location=(0.0, 0.0, 0.4))
    crate = bpy.context.active_object
    crate.name = ASSET
    crate.data.name = ASSET
    # Bake the pivot to the base centre so the object's location stays at the origin.
    crate.data.transform(crate.matrix_world)
    crate.matrix_world.identity()
    crate.data.shade_smooth()
    bevel = crate.modifiers.new("Bevel", "BEVEL")
    bevel.width = 0.03
    bevel.segments = 3
    bevel.harden_normals = True
    bevel.face_strength_mode = "FSTR_AFFECTED"
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = math.radians(30.0)
    weighted = crate.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
    weighted.keep_sharp = True
    weighted.use_face_influence = True
    apply_modifier(crate, bevel)
    apply_modifier(crate, weighted)
    ngons = [poly.index for poly in crate.data.polygons if len(poly.vertices) > 4]
    if ngons:
        bm = bmesh.new()
        bm.from_mesh(crate.data)
        bm.faces.ensure_lookup_table()
        bmesh.ops.triangulate(bm, faces=[bm.faces[i] for i in ngons])
        bm.to_mesh(crate.data)
        bm.free()
    bpy.ops.object.select_all(action="DESELECT")
    crate.select_set(True)
    bpy.context.view_layer.objects.active = crate
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.02, correct_aspect=True,
                             scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return crate


def build_material(crate: "bpy.types.Object", report: Dict[str, Any]) -> "bpy.types.Material":
    """M_TestCrate with a baked-AO ORM and a DirectX normal produced by the texture helpers."""
    material = bpy.data.materials.new("M_TestCrate")
    if material.node_tree is None:
        material.use_nodes = True
    crate.data.materials.append(material)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    output = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)
    if principled is None:
        principled = nodes.new("ShaderNodeBsdfPrincipled")
    if output is None:
        output = nodes.new("ShaderNodeOutputMaterial")
    if not output.inputs["Surface"].is_linked:
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    principled.inputs["Base Color"].default_value = (0.42, 0.30, 0.18, 1.0)

    ao_image = bake_ao(crate, "T_TestCrate_AO", size=SIZE, samples=64, margin=16)
    check(tuple(ao_image.size) == (SIZE, SIZE), "AO image has the wrong size")
    check(ao_image.colorspace_settings.name == "Non-Color", "AO image is not Non-Color")
    check(bpy.context.scene.render.bake.margin_type in {"ADJACENT_FACES", "EXTEND"},
          "bake margin_type was not restored")
    ao_pixels = image_pixels(ao_image)
    covered = float(np.mean(ao_pixels[..., 0] > 0.5))
    check(covered > 0.2, f"AO bake looks empty: {covered:.1%} of pixels are lit")
    check(float(ao_pixels[..., 0].max()) > 0.9, "AO bake has no bright pixels")
    ao_path = write_png(ao_pixels, OUT / "T_TestCrate_AO.png", name="__ao_copy")
    report["images"]["ao"] = {"path": ao_path, "lit_fraction": round(covered, 4)}

    rough_image = bpy.data.images.new("T_TestCrate_R", width=SIZE, height=SIZE, alpha=False, is_data=True)
    rough = np.empty((SIZE, SIZE, 4), dtype=np.float32)
    rough[..., :3] = 0.55
    rough[..., 3] = 1.0
    rough_image.pixels.foreach_set(rough.ravel())
    orm_path = pack_orm(ao_image, rough_image, None, OUT / "T_TestCrate_ORM.png", metal_default=0.0)
    orm_image = load_data_image(orm_path, "T_TestCrate_ORM")
    check(is_power_of_two(orm_image), "ORM is not power of two")
    orm_pixels = image_pixels(orm_image)
    check(abs(float(orm_pixels[..., 1].mean()) - 0.55) < 0.01, "ORM G (roughness) is not 0.55")
    check(float(orm_pixels[..., 2].max()) < 0.01, "ORM B (metallic) should be 0")
    check(float(np.abs(orm_pixels[..., 0] - ao_pixels[..., 0]).max()) < 2.5 / 255.0, "ORM R does not match the baked AO")
    report["images"]["orm"] = {"path": orm_path, "mean_ao": round(float(orm_pixels[..., 0].mean()), 4)}

    gl = np.empty((SIZE, SIZE, 4), dtype=np.float32)
    gl[..., 0] = 0.5
    gl[..., 1] = np.linspace(0.25, 0.75, SIZE, dtype=np.float32)[:, None]
    gl[..., 2] = 1.0
    gl[..., 3] = 1.0
    gl_path = write_png(gl, OUT / "T_TestCrate_NormalGL.png", name="__normal_gl")
    dx_path = flip_normal_green(gl_path, OUT / "T_TestCrate_N.png")
    normal_image = load_data_image(dx_path, "T_TestCrate_N")
    gl_check = bpy.data.images.load(gl_path, check_existing=False)
    try:
        gl_check.colorspace_settings.name = "Non-Color"
        dx_pixels = image_pixels(normal_image)
        gl_pixels = image_pixels(gl_check)
    finally:
        bpy.data.images.remove(gl_check)
    check(float(np.abs((1.0 - gl_pixels[..., 1]) - dx_pixels[..., 1]).max()) < 2.5 / 255.0, "green channel was not flipped")
    check(float(np.abs(gl_pixels[..., 0] - dx_pixels[..., 0]).max()) < 2.5 / 255.0, "red channel changed during flip")
    check(float(np.abs(gl_pixels[..., 2] - dx_pixels[..., 2]).max()) < 2.5 / 255.0, "blue channel changed during flip")
    report["images"]["normal_dx"] = {"path": dx_path, "source_gl": gl_path}

    orm_node = nodes.new("ShaderNodeTexImage")
    orm_node.name = "ORM"
    orm_node.image = orm_image
    separate = nodes.new("ShaderNodeSeparateColor")
    links.new(orm_node.outputs["Color"], separate.inputs["Color"])
    links.new(separate.outputs["Green"], principled.inputs["Roughness"])
    links.new(separate.outputs["Blue"], principled.inputs["Metallic"])
    normal_node = nodes.new("ShaderNodeTexImage")
    normal_node.name = "Normal"
    normal_node.image = normal_image
    normal_map = nodes.new("ShaderNodeNormalMap")
    links.new(normal_node.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], principled.inputs["Normal"])
    for image in (ao_image, rough_image):
        image.filepath_raw = str(OUT / f"{image.name}.png")
        image.file_format = "PNG"
        image.save()
        image.source = "FILE"
        image.filepath = str(OUT / f"{image.name}.png")
        image.colorspace_settings.name = "Non-Color"
    return material


def check_socket_model(report: Dict[str, Any]) -> None:
    """Re-assert the Blender -> Unreal socket transform against the UE 5.8.2 measurements."""
    measured = []
    for name, rotation, location, expect_loc, expect_rot in UE_SOCKET_CASES:
        local = (Matrix.Translation(location) @ Euler(rotation, "XYZ").to_matrix().to_4x4())
        result = ue_socket_transform(local)
        roll, pitch, yaw = (result["rotation_deg"][key] for key in ("roll", "pitch", "yaw"))
        check(all(abs(a - b) < 1e-3 for a, b in zip(result["location_cm"], expect_loc)),
              f"socket model {name}: location {result['location_cm']} != measured {expect_loc}")
        check(all(angles_equal(a, b) for a, b in zip((roll, pitch, yaw), expect_rot)),
              f"socket model {name}: rotation {(roll, pitch, yaw)} != measured {expect_rot}")
        measured.append({"case": name, **result})
    # The correction make_socket bakes in must land as identity in Unreal.
    corrected = ue_socket_transform(Matrix.Translation((0.0, 0.0, 0.8))
                                    @ Matrix.Rotation(math.pi, 4, "Y"))
    check(all(angles_equal(corrected["rotation_deg"][key], 0.0) for key in ("roll", "pitch", "yaw")),
          f"corrected socket does not land identity in Unreal: {corrected['rotation_deg']}")
    report["ue_socket_model"] = {"cases": measured, "corrected_identity": corrected}


def check_deny_list(report: Dict[str, Any]) -> None:
    """The franchise/brand deny list must catch CamelCase and digit-suffixed names."""
    missed = [name for name in DENY_MUST_HIT if not DENY_RE.search(name)]
    false_hits = [f"{name} -> {DENY_RE.search(name).group(0)!r}" for name in DENY_MUST_MISS if DENY_RE.search(name)]
    check(not missed, f"deny list missed: {missed}")
    check(not false_hits, f"deny list false positives: {false_hits}")
    report["deny_list"] = {"caught": list(DENY_MUST_HIT), "ignored": list(DENY_MUST_MISS)}


def check_qa_is_read_only(crate: "bpy.types.Object", report: Dict[str, Any]) -> None:
    """qa_check must not destroy hide state, even when the UV operator path runs."""
    mesh = crate.data
    attribute = mesh.attributes.get(".hide_poly") or mesh.attributes.new(".hide_poly", "BOOLEAN", "FACE")
    attribute.data[0].value = True
    qa_check([crate], require_ucx=False, check_names=False, overlap_method="both")
    restored = mesh.attributes.get(".hide_poly")
    check(restored is not None and restored.data[0].value, "qa_check destroyed the mesh hide state")
    mesh.attributes.remove(mesh.attributes[".hide_poly"])  # leave the shipped mesh clean
    report["qa_read_only"] = True


def roundtrip(fbx_path: Path) -> Dict[str, Any]:
    """Import ``fbx_path`` into an empty scene and describe what arrived."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx_path))
    objects = {}
    for obj in bpy.context.scene.objects:
        entry: Dict[str, Any] = {"type": obj.type, "parent": obj.parent.name if obj.parent else None}
        if obj.type == "MESH":
            entry["triangles"] = len(obj.data.loop_triangles)
            entry["uv_maps"] = len(obj.data.uv_layers)
        if obj.type == "EMPTY":
            entry["fbx_type"] = obj.get("fbx_type")
        objects[obj.name] = entry
    return objects


def main() -> int:
    """Build, check, export and verify; return the process exit code."""
    OUT.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Any] = {"status": "failed", "pipeline_version": VERSION,
                              "blender_version": bpy.app.version_string, "images": {}, "fbx": {}}
    report_path = OUT / "test_report.json"
    try:
        check_deny_list(report)
        check_socket_model(report)

        fresh_scene()
        crate = build_crate()
        build_material(crate, report)

        hull = make_ucx_hull(crate, index=0, max_verts=32)
        check(hull.name == f"UCX_{ASSET}_00", f"hull name {hull.name}")
        check(len(hull.data.vertices) <= 32, f"hull has {len(hull.data.vertices)} vertices")
        check(hull.parent == crate and hull.hide_render and not hull.data.materials, "hull parenting/material/render flags")
        bm = bmesh.new()
        bm.from_mesh(hull.data)
        check(all(edge.is_manifold for edge in bm.edges), "hull is not closed")
        bm.free()

        socket = make_socket(crate, "Lid", (0.0, 0.0, 0.8))
        check(socket.type == "EMPTY", f"socket must be an Empty (FBX Null), got {socket.type}")
        check(socket.name == f"SOCKET_{ASSET}_Lid" and socket.parent == crate, "socket name/parent")
        bpy.context.view_layer.update()  # matrix_world is only current after a depsgraph update
        check(abs((socket.matrix_world.translation - crate.matrix_world.translation).z - 0.8) < 1e-6,
              "socket is not at the top centre")
        socket_ue = ue_socket_transform(socket.matrix_local)
        check(all(angles_equal(socket_ue["rotation_deg"][key], 0.0) for key in ("roll", "pitch", "yaw")),
              f"the built socket does not land identity in Unreal: {socket_ue['rotation_deg']}")
        report["socket"] = {"name": socket.name, "type": socket.type,
                            "world_location": [round(v, 4) for v in socket.matrix_world.translation],
                            "unreal": socket_ue}

        lods = decimate_lods(crate, ratios=(0.5, 0.25))
        check(all(not lod.modifiers for lod in lods), "LOD copies still carry modifiers")
        group = make_lod_group(ASSET, [crate] + lods)
        check(crate.name == LOD0, f"LOD0 rename failed: {crate.name}")
        check(hull.name == f"UCX_{LOD0}_00",
              f"the hull was not renamed with the mesh: {hull.name} (Unreal would drop the collision)")
        check(socket.name == f"SOCKET_{LOD0}_Lid", f"the socket was not renamed with the mesh: {socket.name}")
        check([o.name for o in lods] == [f"{ASSET}_LOD1", f"{ASSET}_LOD2"], "LOD names")
        check(group.name == f"{ASSET}_LodGroup" and group.get("fbx_type") == "LodGroup", "LOD group empty")
        check(all(o.parent == group for o in [crate] + lods), "LOD parenting")
        check(all(o.data.materials and o.data.materials[0].name == "M_TestCrate" for o in lods), "LOD materials lost")
        check(all(o.data.uv_layers for o in lods), "LOD UVs lost")
        report["ucx"] = {"name": hull.name, "vertices": len(hull.data.vertices), "faces": len(hull.data.polygons)}

        qa = qa_check([crate] + lods, budget_tris=5000, require_ucx=True)
        report["qa"] = qa
        report["lod_triangles"] = {name: qa["triangles"][name] for name in [crate.name] + [o.name for o in lods]}
        failed = [c for c in qa["checks"] if not c["passed"]]
        check(qa["passed"], "qa_check failed: " + "; ".join(f"{c['name']}[{c['object']}]: {c['detail']}" for c in failed))
        counts = list(report["lod_triangles"].values())
        check(counts[0] > counts[1] > counts[2] > 0, f"LOD triangle counts not descending: {counts}")
        check_qa_is_read_only(crate, report)

        exports = {
            # Shipping file: LOD group + UCX. The socket is moved to the sidecar because
            # UE 5.8.2 discards every socket in a file that carries a LodGroup.
            "all": (OUT / f"{ASSET}.fbx", [group], {}),
            # Control: the socket is excluded outright, so the sidecar carries only the
            # LOD screen sizes (an FBX LodGroup has no thresholds of its own).
            "no_socket": (OUT / f"{ASSET}_NoSocket.fbx", [group], {"exclude": [socket.name]}),
            # Flat file: no LodGroup, so the socket Empty does survive the import.
            "single": (OUT / f"{ASSET}_Single.fbx", [crate], {}),
            # Opt-in to the combination UE cannot import, to keep the warning path covered.
            "lod_socket": (OUT / f"{ASSET}_LodSocket.fbx", [group], {"include_sockets": True}),
        }
        expected_objects = {
            "all": {group.name, crate.name, lods[0].name, lods[1].name, hull.name},
            "no_socket": {group.name, crate.name, lods[0].name, lods[1].name, hull.name},
            "single": {crate.name, hull.name, socket.name},
            "lod_socket": {group.name, crate.name, lods[0].name, lods[1].name, hull.name, socket.name},
        }
        expected_sockets = {"all": 1, "no_socket": 0, "single": 1, "lod_socket": 1}
        for key, (path, objects, extra) in exports.items():
            result = export_fbx(path, objects, kind="static", **extra)
            check(Path(result["filepath"]).is_file() and Path(result["filepath"]).stat().st_size > 0, f"{path.name} not written")
            check(set(result["objects"]) == expected_objects[key],
                  f"{path.name} exported {result['objects']}, expected {sorted(expected_objects[key])}")
            check(len(result["sockets"]) == expected_sockets[key],
                  f"{path.name} recorded {len(result['sockets'])} socket(s), expected {expected_sockets[key]}")
            in_fbx = b"SOCKET_" in Path(result["filepath"]).read_bytes()
            check(in_fbx == (key in ("single", "lod_socket")), f"{path.name}: SOCKET_ node present={in_fbx}")
            # A multi-LOD export always writes the sidecar, sockets or not: the FBX
            # LodGroup carries no screen sizes and Unreal invents its own without it.
            expect_screen_sizes = [1.0, 0.5, 0.25] if key != "single" else None
            check(result["lod_screen_sizes"] == expect_screen_sizes,
                  f"{path.name}: lod_screen_sizes {result['lod_screen_sizes']}, expected {expect_screen_sizes}")
            if expected_sockets[key] or expect_screen_sizes:
                check(result["sidecar"] == sidecar_path(str(path)) and Path(result["sidecar"]).is_file(),
                      f"{path.name}: sidecar missing")
                payload = json.loads(Path(result["sidecar"]).read_text(encoding="utf-8"))
                check(payload.get("lod_screen_sizes") == expect_screen_sizes,
                      f"{path.name}: sidecar lod_screen_sizes {payload.get('lod_screen_sizes')}")
                check(len(payload["sockets"]) == expected_sockets[key],
                      f"{path.name}: sidecar carries {len(payload['sockets'])} socket(s)")
            else:
                check(result["sidecar"] is None, f"{path.name}: unexpected sidecar")
            if expected_sockets[key]:
                payload = json.loads(Path(result["sidecar"]).read_text(encoding="utf-8"))
                record = payload["sockets"][0]
                check(record["socket"] == "Lid" and record["mesh"] == crate.name, f"{path.name}: sidecar socket record")
                check(record["in_fbx"] is (key in ("single", "lod_socket")), f"{path.name}: sidecar in_fbx flag")
                check(all(abs(a - b) < 1e-3 for a, b in zip(record["location_cm"], [0.0, 0.0, 80.0])),
                      f"{path.name}: sidecar location {record['location_cm']}")
                check(all(angles_equal(record["rotation_deg"][k], 0.0) for k in ("roll", "pitch", "yaw")),
                      f"{path.name}: sidecar rotation {record['rotation_deg']}")
            report["fbx"][key] = {"path": result["filepath"], "objects": result["objects"],
                                  "warnings": result["warnings"], "sockets": result["sockets"],
                                  "sidecar": result["sidecar"], "bytes": Path(result["filepath"]).stat().st_size}
        check(any("sidecar" in w for w in report["fbx"]["all"]["warnings"]),
              "the LodGroup export did not warn that the sockets moved to the sidecar")
        check(any("discards every socket" in w for w in report["fbx"]["lod_socket"]["warnings"]),
              "include_sockets did not warn that UE discards the socket")
        report["export_settings"] = result["settings"]

        for bad_name in ("TestCrate.fbx", "Crate_SM.fbx"):
            try:
                export_fbx(OUT / bad_name, [crate], kind="static")
            except ValueError:
                pass
            else:
                raise AssertionError(f"export_fbx accepted the bad basename {bad_name}")
        try:
            export_fbx(OUT / f"{ASSET}_Empty.fbx", [crate], kind="static",
                       exclude=[crate.name, hull.name, socket.name])
        except ValueError:
            pass
        else:
            raise AssertionError("export_fbx accepted an empty selection")
        crate.rotation_euler = (0.0, 0.0, 0.3)
        try:
            export_fbx(OUT / f"{ASSET}_Rotated.fbx", [crate], kind="static")
        except ValueError:
            pass
        else:
            raise AssertionError("export_fbx accepted an unapplied rotation")
        finally:
            crate.rotation_euler = (0.0, 0.0, 0.0)

        blend_path = OUT / f"{ASSET}.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), relative_remap=True)
        report["blend"] = str(blend_path)

        group_name = group.name  # the round-trip resets the scene, so keep names as strings
        socket_name = socket.name
        for key, info in report["fbx"].items():
            imported = roundtrip(Path(info["path"]))
            info["roundtrip"] = imported
            check(set(imported) == expected_objects[key], f"{key}: round-trip objects {sorted(imported)} != {sorted(expected_objects[key])}")
            if socket_name in imported:
                check(imported[socket_name]["type"] == "EMPTY", f"{key}: the socket node is not an Empty")
            for name, tris in report["lod_triangles"].items():
                if name in imported:
                    check(imported[name]["triangles"] == tris, f"{key}: {name} round-trip triangles {imported[name]['triangles']} != {tris}")
            # Blender's importer does not restore the fbx_type custom property, so the
            # LodGroup node attribute is verified in the file bytes instead.
            lod_group_hits = Path(info["path"]).read_bytes().count(b"LodGroup")
            info["lod_group_attribute_hits"] = lod_group_hits
            if group_name in imported:
                check(imported[group_name]["type"] == "EMPTY", f"{key}: LodGroup node lost")
                check(lod_group_hits > 0, f"{key}: no LodGroup node attribute in the FBX")
                check(all(imported[n]["parent"] == group_name for n in report["lod_triangles"]), f"{key}: LODs not parented to the LodGroup")
            else:
                check(lod_group_hits == 0, f"{key}: unexpected LodGroup node attribute in the FBX")
        report["status"] = "passed"
    except Exception:  # noqa: BLE001 - the report must record any failure
        report["error"] = traceback.format_exc()
    finally:
        report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    if report["status"] != "passed":
        print(report.get("error", "unknown failure"))
        print(f"PIPELINE_TEST_FAILED {report_path}", flush=True)
        return 1
    print(f"PIPELINE_TEST_PASSED {report_path} lod_triangles={report['lod_triangles']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
