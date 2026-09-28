"""Unreal import check for garment FBX files (CharacterLab commandlet; imports in memory, saves NOTHING).

Run through ``Scripts/garments/run_ue_characterlab.ps1 -Script Scripts/garments/ue_check_garment.py -Tag <tag>``
after writing ``WorkFiles/garment_pipeline/ue_runs/garment_check_input.json``::

    {"skeleton": "/Game/MetaHumans/Common/.../metahuman_base_skel", "body": "/Game/MetaHumans/MH_PlayerDefault/Body/SKM_...",
     "fbx": {"label": "C:/.../SK_Name.fbx", ...}, "report": "C:/.../out.json"}

Each FBX is imported with the legacy FBX importer onto the existing skeleton (never a new one) under the transient
``/Game/_GarmentCheck`` folder; nothing is saved, and the runner confirms no file appeared under Content. For every
import the report holds: success, the skeleton actually assigned, bone count, vertex count, material slot names,
and the reference skeleton compared bone by bone (component space) with the body mesh's - the engine-side proof
that the garment's bind pose IS metahuman_base_skel's.
"""
import hashlib
import json
import math
import traceback

import unreal

INPUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/garment_pipeline/ue_runs/garment_check_input.json"
DEST = "/Game/_GarmentCheck"


def component_space(mesh):
    comp = unreal.new_object(unreal.SkeletalMeshComponent)
    if hasattr(comp, "set_skinned_asset_and_update"):
        comp.set_skinned_asset_and_update(mesh)
    else:
        comp.set_skeletal_mesh_asset(mesh)
    local = {}
    parent = {}
    for index in range(comp.get_num_bones()):
        name = str(comp.get_bone_name(index))
        local[name] = comp.get_ref_pose_transform(index)
        p = str(comp.get_parent_bone(name))
        parent[name] = None if p in ("None", "") else p
    world = {}

    def resolve(name):
        if name not in world:
            t = local[name]
            world[name] = t if parent[name] is None else unreal.MathLibrary.compose_transforms(t, resolve(parent[name]))
        return world[name]

    for name in local:
        resolve(name)
    return world, parent


def rotation_delta_deg(a, b):
    qa, qb = a.rotation, b.rotation
    dot = abs(qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w)
    return math.degrees(2.0 * math.acos(min(1.0, dot)))


def import_one(path, name, skeleton):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("skeleton", skeleton)
    ui.set_editor_property("create_physics_asset", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    data = ui.get_editor_property("skeletal_mesh_import_data")
    data.set_editor_property("import_morph_targets", False)
    data.set_editor_property("convert_scene", True)
    data.set_editor_property("force_front_x_axis", False)
    data.set_editor_property("convert_scene_unit", True)
    data.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", DEST)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", False)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("options", ui)
    unreal.log("[garment_check] BEGIN import " + name)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    unreal.log("[garment_check] END import " + name)
    paths = list(task.get_editor_property("imported_object_paths"))
    meshes = [unreal.load_asset(p) for p in paths]
    return [m for m in meshes if isinstance(m, unreal.SkeletalMesh)], paths


config = json.load(open(INPUT, encoding="utf-8"))
report = {"status": "failed", "results": {}}
try:
    skeleton = unreal.load_asset(config["skeleton"])
    body = unreal.load_asset(config["body"])
    body_world, body_parent = component_space(body)
    report["body_bones"] = len(body_world)
    subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    for label, path in config["fbx"].items():
        entry = {"fbx": path, "fbx_sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()}
        try:
            meshes, paths = import_one(path, "SK_Check_" + label, skeleton)
            entry["imported"] = paths
            if not meshes:
                entry["error"] = "no skeletal mesh imported"
            else:
                mesh = meshes[0]
                world, parent = component_space(mesh)
                entry["skeleton"] = mesh.get_editor_property("skeleton").get_path_name()
                entry["bones"] = len(world)
                entry["missing_bones"] = sorted(set(body_world) - set(world))[:10]
                entry["extra_bones"] = sorted(set(world) - set(body_world))[:10]
                entry["reparented"] = sorted(n for n in set(world) & set(body_world) if parent[n] != body_parent[n])[:10]
                worst_t = worst_r = 0.0
                worst = None
                for name in set(world) & set(body_world):
                    dt = (world[name].translation - body_world[name].translation).length()
                    dr = rotation_delta_deg(world[name], body_world[name])
                    if dt > worst_t or dr > worst_r:
                        worst = name if (dt > 0.001 or dr > 0.01) else worst
                    worst_t, worst_r = max(worst_t, dt), max(worst_r, dr)
                entry["ref_pose_vs_body"] = {"max_translation_cm": worst_t, "max_rotation_deg": worst_r, "worst_bone": worst}
                entry["vertices_lod0"] = subsystem.get_num_verts(mesh, 0)
                entry["lods"] = subsystem.get_lod_count(mesh)
                entry["material_slots"] = [str(m.get_editor_property("material_slot_name"))
                                           for m in mesh.get_editor_property("materials")]
                bounds = mesh.get_bounds()
                entry["bounds_z_cm"] = [bounds.origin.z - bounds.box_extent.z, bounds.origin.z + bounds.box_extent.z]
        except Exception:  # noqa: BLE001
            entry["error"] = traceback.format_exc()
        report["results"][label] = entry
    report["status"] = "ok"
except Exception:  # noqa: BLE001
    report["error"] = traceback.format_exc()
finally:
    with open(config["report"], "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=1)
    unreal.log("[garment_check] status " + report["status"])
