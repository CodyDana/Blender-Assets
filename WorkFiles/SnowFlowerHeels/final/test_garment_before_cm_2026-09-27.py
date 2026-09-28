"""Garment gate tests: positive garments on the real locked MetaHuman base, and one defect per negative case.

Run::

    blender -b --factory-startup --python Scripts/pipeline/test_garment.py

Every case starts from an empty scene with the locked fitting body appended (``References/Characters/
MH_PlayerDefault``), builds a small garment with the pipeline's own helpers and asserts that the set of blocking
failures equals the expected set - nothing more, nothing less (``test_qa_negative.py``'s rule). The whole-character
budget is 160k (decided 2026-09-26; the base alone is 121,892 LOD0 triangles), so no case needs a waiver; the
budget case adds loadout triangles to push past it.

Positive: a fitted shirt band (body weights), a rigid hat (head, clear of the hair proxy), a small cloak (tight
collar on the spine chain + a cloth cape rigid on the chest), and a garment FBX export that is re-imported and
compared with the locked skeleton. Negative: wrong skeleton (a moved bone; an armature not named ``root``), body
poke-through at rest, a shirt skinned rigidly to the pelvis (pokes through in the poses), limb weights on a cloak,
a hat inside the hair, over budget (garment, cloth section, whole character), a tampered fitting body, and the
export refusing a bad armature name / mesh prefix. Writes WorkFiles/pipeline_test/test_garment.json.
"""
from __future__ import annotations

import json
import math
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Iterator, List, Set, Tuple

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles" / "pipeline_test"
SCRIPTS = ROOT / "Scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from pipeline import garment_helpers as gh  # noqa: E402
from pipeline import garment_qa as gq  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402

BUDGET_WAIVER: dict = {}  # no waiver needed since the 160k character budget (2026-09-26)
Case = Tuple[str, List["bpy.types.Object"], str, Set[str], Dict[str, Any]]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def fresh() -> Dict[str, "bpy.types.Object"]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    units = bpy.context.scene.unit_settings
    units.system, units.scale_length = "METRIC", 1.0
    return gh.append_fitbody()


def material(name: str) -> "bpy.types.Material":
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)


def new_object(name: str, bm: "bmesh.types.BMesh", material_name: str) -> "bpy.types.Object":
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(material(material_name))
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def planar_uvs(obj: "bpy.types.Object") -> None:
    """Cylindrical UVs around Z (tiling is fine on a garment; the UV layout gates are informational there)."""
    mesh = obj.data
    layer = mesh.uv_layers.new(name="UVMap")
    for loop in mesh.loops:
        co = mesh.vertices[loop.vertex_index].co
        layer.data[loop.index].uv = (math.atan2(co.y, co.x) / (2 * math.pi) + 0.5, co.z)


def shirt(fit, z_range=(1.08, 1.36), offset=0.015, name="SK_TestShirt") -> "bpy.types.Object":
    """A band of the body's own torso triangles, pushed out ``offset`` along the normals, body weights transferred."""
    body = fit["body"]
    regions = gq.dominant_regions(body)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    keep = [f for f in bm.faces if all(regions[v.index] == "torso" and z_range[0] <= v.co.z <= z_range[1] for v in f.verts)]
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in set(keep)], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    for layer in list(bm.verts.layers.deform):  # the body's raw weights would bind to the wrong group indices
        bm.verts.layers.deform.remove(layer)
    bm.normal_update()
    for vert in bm.verts:
        vert.co += vert.normal * offset
    obj = new_object(name, bm, "M_TestShirt")
    for attribute in [a.name for a in obj.data.color_attributes]:
        obj.data.color_attributes.remove(obj.data.color_attributes[attribute])
    obj.data.uv_layers[0].name = "UVMap"
    for layer in list(obj.data.uv_layers)[1:]:
        obj.data.uv_layers.remove(layer)
    gh.transfer_body_weights(obj, [fit["body"], fit["head"]], 8)
    gh.bind(obj, fit["armature"])
    return obj


def hat(fit, bottom=1.80, radius=0.13, name="SK_TestHat") -> "bpy.types.Object":
    """A closed crown (cone with caps) and a flat brim ring, rigid on head."""
    bm = bmesh.new()
    height = 0.12
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=24, radius1=radius, radius2=radius * 0.92,
                          depth=height)
    bmesh.ops.translate(bm, vec=Vector((0.0, -0.005, bottom + height / 2)), verts=bm.verts)
    ring_inner = [bm.verts.new((radius * math.cos(a), -0.005 + radius * math.sin(a), bottom - 0.002))
                  for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
    ring_outer = [bm.verts.new((0.22 * math.cos(a), -0.005 + 0.22 * math.sin(a), bottom - 0.01))
                  for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
    for i in range(24):
        j = (i + 1) % 24
        bm.faces.new((ring_inner[i], ring_inner[j], ring_outer[j], ring_outer[i]))
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    bmesh.ops.triangulate(bm, faces=ngons)
    obj = new_object(name, bm, "M_TestHat")
    planar_uvs(obj)
    gh.skin_rigid(obj, "head")
    gh.bind(obj, fit["armature"])
    return obj


def skullcap(fit, offset=0.006, above=1.83, name="SK_TestCap") -> "bpy.types.Object":
    """The head's own scalp above ``above``, pushed out ``offset``: outside the skin, inside the hair proxy."""
    head = fit["head"]
    bm = bmesh.new()
    bm.from_mesh(head.data)
    keep = {f for f in bm.faces if all(v.co.z >= above for v in f.verts)}
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in keep], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    for layer in list(bm.verts.layers.deform):
        bm.verts.layers.deform.remove(layer)
    bm.normal_update()
    for vert in bm.verts:
        vert.co += vert.normal * offset
    obj = new_object(name, bm, "M_TestCap")
    for attribute in [a.name for a in obj.data.color_attributes]:
        obj.data.color_attributes.remove(obj.data.color_attributes[attribute])
    gh.skin_rigid(obj, "head")
    gh.bind(obj, fit["armature"])
    return obj


def cloak(fit, cape_grid=(20, 20), name="SK_TestCape") -> "bpy.types.Object":
    """Tight collar ring (cleared 1 cm off the neck) + a cloth cape behind the back, joined like build_garment."""
    arm = fit["armature"]
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=0.085, radius2=0.075, depth=0.06)
    bmesh.ops.translate(bm, vec=Vector((0.0, 0.01, 1.60)), verts=bm.verts)
    collar = new_object("Collar", bm, "M_TestCape")
    skin = gh.SkinTree([fit["body"], fit["head"]])
    gh.clearance_pass(collar, skin, gh.CLEAR_TIGHT)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=cape_grid[0], y_segments=cape_grid[1], size=1.0)
    lo = min(v.co.x for v in bm.verts)
    hi = max(v.co.x for v in bm.verts)
    for vert in bm.verts:  # the XY grid -> a vertical sheet 7 cm behind the back: x -0.2..0.2, z 0.85..1.45
        u, w = (vert.co.x - lo) / (hi - lo), (vert.co.y - lo) / (hi - lo)
        vert.co = Vector((-0.2 + 0.4 * u, 0.20, 0.85 + 0.6 * w))
    cape = new_object("Cape", bm, "M_TestCape")
    for obj in (collar, cape):
        planar_uvs(obj)
        gh.bake_pin_mask(obj)
    gh.skin_cloak(collar, arm, rigid=False)
    gh.skin_cloak(cape, arm, rigid=True)
    gh.make_sim_material([cape])
    garment = gh.join(cape, [collar], name)
    gh.bind(garment, arm)
    gh.set_active_pin_mask(garment)
    return garment


def cases() -> Iterator[Case]:
    """(name, garment objects, type, expected blocking failures, qa kwargs), one fresh scene at a time."""
    fit = fresh()
    yield ("fitted_shirt_passes", [shirt(fit)], "fitted", set(), {})

    fit = fresh()
    yield ("character_budget_over_160k", [shirt(fit)], "fitted", {"character_triangle_budget"},
           {"waive": {}, "extra_loadout_tris": 40000})

    fit = fresh()
    yield ("rigid_hat_passes", [hat(fit)], "rigid_head", set(), {})

    fit = fresh()
    yield ("cloak_passes", [cloak(fit)], "cloak", set(), {})

    # wrong skeleton 1: a bone moved 1 cm in the rest pose (the body mesh does not move at rest)
    fit = fresh()
    garment = shirt(fit)
    arm = fit["armature"]
    arm.hide_select = False
    bpy.data.collections[gq.fitbody_collection()].hide_select = False
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    bone = arm.data.edit_bones["spine_03"]
    bone.head.x += 0.01
    bone.tail.x += 0.01
    bpy.ops.object.mode_set(mode="OBJECT")
    yield ("wrong_skeleton_moved_bone", [garment], "fitted", {"skeleton_matches_base"}, {})

    # wrong skeleton 2: the armature object is not called "root" (Unreal would add a bone above root)
    fit = fresh()
    garment = shirt(fit)
    fit["armature"].name = "Armature"
    yield ("wrong_skeleton_armature_name", [garment], "fitted",
           {"armature_object_name", "root_bone_at_origin", "skeleton_matches_base"}, {})

    # body poke-through at rest: 10 shirt vertices pushed 2 cm under the skin. Rest allows none; the poses allow
    # 1 % (10 of 2,518 is 0.4 %), so only the rest gate fails - with 40 vertices every pose fails too.
    fit = fresh()
    garment = shirt(fit)
    mesh = garment.data
    front = sorted(range(len(mesh.vertices)), key=lambda i: mesh.vertices[i].co.y)[:10]
    for index in front:
        mesh.vertices[index].co += Vector((0.0, 0.035, 0.0))
    mesh.update()
    yield ("body_poke_through_rest", [garment], "fitted", {"intersection_rest"}, {})

    # skinning that does not follow the body: the shirt rides the pelvis alone, so the chest comes through it when
    # the spine bends (the rest pose cannot see this - Outfit_Pipeline trap 2)
    fit = fresh()
    garment = shirt(fit)
    gh.skin_rigid(garment, "pelvis")
    yield ("rigid_pelvis_shirt_pokes_in_poses", [garment], "fitted", {"intersection_deep_crouch"}, {})

    # limb weights on a cloak: the hem of the cape on thigh_l - what nearest-surface weight transfer did to the
    # first BlackCloak (Outfit_Pipeline trap 3); the cloth section is then no longer rigid on the chest either
    fit = fresh()
    garment = cloak(fit)
    thigh = garment.vertex_groups.get("thigh_l") or garment.vertex_groups.new(name="thigh_l")
    sim_mask, _slots = gq._section_vertices(garment)
    hem = sorted((i for i in range(len(garment.data.vertices)) if sim_mask[i]),
                 key=lambda i: garment.data.vertices[i].co.z)[:10]
    for group in garment.vertex_groups:
        if group.name != "thigh_l":
            group.remove(hem)
    thigh.add(hem, 1.0, "REPLACE")
    yield ("limb_weights_on_cloak", [garment], "cloak", {"cloak_weight_bones", "cloak_sim_rigid_on_chest"}, {})

    # a cap that sits in the hair (6 mm off the scalp: outside the skin, inside the hair proxy)
    fit = fresh()
    yield ("hat_in_hair", [skullcap(fit)], "rigid_head", {"hair_clearance"}, {})

    # over budget: the garment triangle budget, and a cloth section over 6,000 triangles
    fit = fresh()
    yield ("over_garment_budget", [shirt(fit)], "fitted", {"garment_triangle_budget"}, {"triangle_budget": 1000})
    fit = fresh()
    yield ("over_sim_budget", [cloak(fit, cape_grid=(60, 60))], "cloak", {"sim_triangle_budget"}, {})

    # a tampered fitting body: one foot vertex moved 1 mm
    fit = fresh()
    garment = shirt(fit)
    body = fit["body"].data
    lowest = min(range(len(body.vertices)), key=lambda i: body.vertices[i].co.z)
    body.vertices[lowest].co.z -= 0.001
    body.update()
    yield ("fitbody_tampered", [garment], "fitted", {"fitbody_intact"}, {})


def export_roundtrip(report: Dict[str, Any]) -> None:
    """Export a fitted shirt and a cloak as garments, re-import them and compare with the locked skeleton."""
    lock = gq.load_base_lock()
    results = {}
    for label, builder, garment_type in (("shirt", shirt, "fitted"), ("cape", cloak, "cloak")):
        fit = fresh()
        garment = builder(fit)
        qa = gq.qa_garment([garment], garment_type, waive=BUDGET_WAIVER)
        check(qa["passed"], f"{label}: gates failed before export: {qa['failed']}")
        path = OUT / f"SK_Test{label.capitalize()}.fbx"
        # the refusals first: a wrong armature name and a mesh without the SK_ prefix
        fit["armature"].name = "Armature"
        try:
            export_fbx(path, [garment], kind="garment")
        except ValueError:
            pass
        else:
            raise AssertionError("export_fbx(kind='garment') accepted an armature not named root")
        fit["armature"].name = "root"
        garment.name = "Test" + label
        try:
            export_fbx(OUT / "SK_TestNoPrefix.fbx", [garment], kind="garment")
        except ValueError:
            pass
        else:
            raise AssertionError("export_fbx(kind='garment') accepted a mesh without the SK_ prefix")
        garment.name = path.stem
        tris = gq.triangle_count(garment)
        weights = {v.index: {garment.vertex_groups[g.group].name: g.weight for g in v.groups if g.weight > 0}
                   for v in garment.data.vertices}
        coords = np.array([v.co[:] for v in garment.data.vertices])
        result = export_fbx(path, [garment], kind="garment")
        check(set(result["objects"]) == {garment.name, "root"}, f"{label}: exported {result['objects']}")
        check(result["settings"]["use_armature_deform_only"] is False, "garment export must keep every bone")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(path), automatic_bone_orientation=False)
        arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
        mesh = next(o for o in bpy.context.scene.objects if o.type == "MESH")
        check(arm.name == "root", f"{label}: re-imported armature is {arm.name!r}")
        # A re-import is float-close, not bit-identical (measured 0.003 mm / 0.003 deg): 0.01 mm / 0.01 deg.
        ok, detail, numbers = gq.compare_skeleton(arm, lock["skeleton"], tolerance_m=1e-5, tolerance_deg=0.01)
        check(ok, f"{label}: re-imported skeleton differs from the lock: {detail}")
        check(len(mesh.data.polygons) == tris, f"{label}: {len(mesh.data.polygons)} faces after import, {tris} before")
        imported = np.array([(mesh.matrix_world @ v.co)[:] for v in mesh.data.vertices])
        check(len(imported) == len(coords), f"{label}: vertex count {len(imported)} != {len(coords)}")
        drift = float(np.abs(imported - coords).max())
        check(drift < 1e-5, f"{label}: vertices moved {drift} m through the FBX")
        names = {g.index: g.name for g in mesh.vertex_groups}
        worst = 0.0
        for vertex in mesh.data.vertices:
            got = {names[g.group]: g.weight for g in vertex.groups if g.weight > 0}
            want = weights[vertex.index]
            for key in set(got) | set(want):
                worst = max(worst, abs(got.get(key, 0.0) - want.get(key, 0.0)))
        check(worst < 1e-4, f"{label}: weights changed by {worst} through the FBX")
        if garment_type == "cloak":
            check(mesh.data.color_attributes.get(gq.PIN_MASK) is not None, f"{label}: PinMask lost")
        results[label] = {"fbx": str(path), "triangles": tris, "vertex_drift_m": drift, "weight_drift": worst,
                          "skeleton": numbers, "armature": arm.name, "bones": len(arm.data.bones) + 1}
    report["export_roundtrip"] = results


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Any] = {"status": "failed", "cases": {}}
    report_path = OUT / "test_garment.json"
    problems: List[str] = []
    try:
        for name, objects, garment_type, expected, kwargs in cases():
            kwargs = dict(kwargs)
            kwargs.setdefault("waive", BUDGET_WAIVER)
            result = gq.qa_garment(objects, garment_type, **kwargs)
            failing = set(result["failed"])
            report["cases"][name] = {"type": garment_type, "expected": sorted(expected), "failed": sorted(failing),
                                     "passed": result["passed"], "waived": result["waived"],
                                     "metrics": result["metrics"],
                                     "details": [f"{c['name']}: {c['detail']}" for c in result["checks"]
                                                 if not c["passed"]]}
            if failing != expected:
                problems.append(f"{name}: blocking failures {sorted(failing)} != expected {sorted(expected)}")
            if bool(expected) == result["passed"]:
                problems.append(f"{name}: qa_garment passed={result['passed']} with expected={sorted(expected)}")
        export_roundtrip(report)
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
        print(f"GARMENT_TEST_FAILED {report_path}", flush=True)
        return 1
    print(f"GARMENT_TEST_PASSED {report_path} cases={len(report['cases'])} roundtrip={sorted(report['export_roundtrip'])}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
