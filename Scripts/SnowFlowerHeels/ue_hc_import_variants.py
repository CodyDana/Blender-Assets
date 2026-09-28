"""Heels Unreal check: does an IMPORT setting avoid the root-scale-100 reference skeleton? (commandlet, -Render)

Imports the shipped LOD0 FBX with variant options under /Game/HeelsCheck/<RUN>/variants/ and reports, per variant: root bone
local scale, pelvis local translation, component-space bind match with her body, and mesh bounds. Saves the variants that
come out right (so the worn test can use one), clearly named. Writes WorkFiles/SnowFlowerHeels/ue/import_variants_<RUN>.json.
"""
import json
import math
import traceback

import unreal

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
UE = ROOT + "/WorkFiles/SnowFlowerHeels/ue"
RUN = json.load(open(UE + "/run.json", encoding="utf-8"))["run"]
DEST = "/Game/HeelsCheck/%s/variants" % RUN
FBX = ROOT + "/Exports/SnowFlowerHeels/SK_SnowFlowerHeels.fbx"
SKELETON = "/Game/MetaHumans/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel"
BODY = "/Game/MetaHumans/MH_PlayerFemale/Body/SKM_MH_PlayerFemale_BodyMesh"
rep = {"status": "failed", "errors": [], "variants": {}}


def ref(mesh):
    comp = unreal.new_object(unreal.SkeletalMeshComponent)
    comp.set_skinned_asset_and_update(mesh)
    local, parent = {}, {}
    for i in range(comp.get_num_bones()):
        n = str(comp.get_bone_name(i))
        local[n] = comp.get_ref_pose_transform(i)
        p = str(comp.get_parent_bone(n))
        parent[n] = None if p in ("None", "") else p
    cache = {}

    def cs(n):
        if n not in cache:
            cache[n] = local[n] if parent[n] is None else local[n].multiply(cs(parent[n]))
        return cache[n]
    return local, {n: cs(n) for n in local}


VARIANTS = {
    "t0_ref_pose": {"use_t0_as_ref_pose": True},
    "no_unit_convert": {"convert_scene_unit": False},
    "t0_no_unit_convert": {"use_t0_as_ref_pose": True, "convert_scene_unit": False},
}
try:
    skeleton = unreal.load_asset(SKELETON)
    body_local, body_cs = ref(unreal.load_asset(BODY))
    for name, opts in VARIANTS.items():
        e = {"options": opts}
        try:
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
            d = ui.get_editor_property("skeletal_mesh_import_data")
            d.set_editor_property("import_morph_targets", False)
            d.set_editor_property("convert_scene", True)
            d.set_editor_property("force_front_x_axis", False)
            d.set_editor_property("convert_scene_unit", True)
            d.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
            for k, v in opts.items():
                d.set_editor_property(k, v)
            task = unreal.AssetImportTask()
            task.set_editor_property("filename", FBX)
            task.set_editor_property("destination_path", DEST)
            task.set_editor_property("destination_name", "SK_SnowFlowerHeels_" + name)
            task.set_editor_property("automated", True)
            task.set_editor_property("save", False)
            task.set_editor_property("replace_existing", True)
            task.set_editor_property("options", ui)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
            mesh = [m for m in (unreal.load_asset(p) for p in paths) if isinstance(m, unreal.SkeletalMesh)][0]
            local, cs = ref(mesh)
            r = local["root"]
            e["root_local_scale"] = [r.scale3d.x, r.scale3d.y, r.scale3d.z]
            e["pelvis_local_t"] = [local["pelvis"].translation.x, local["pelvis"].translation.y, local["pelvis"].translation.z]
            e["cs_max_dt_cm"] = max((cs[n].translation - body_cs[n].translation).length() for n in body_cs if n in cs)
            e["local_max_dt_cm"] = max((local[n].translation - body_local[n].translation).length() for n in body_local if n in local)
            b = mesh.get_bounds()
            e["bounds_min"] = [b.origin.x - b.box_extent.x, b.origin.y - b.box_extent.y, b.origin.z - b.box_extent.z]
            e["bounds_max"] = [b.origin.x + b.box_extent.x, b.origin.y + b.box_extent.y, b.origin.z + b.box_extent.z]
            e["ok"] = abs(e["root_local_scale"][0] - 1) < 1e-3 and e["local_max_dt_cm"] < 0.01 and abs(e["bounds_max"][1] - 26.1967) < 0.05
            e["path"] = mesh.get_path_name()
            if e["ok"]:
                e["saved"] = unreal.EditorAssetLibrary.save_asset(mesh.get_path_name().split(".")[0], only_if_is_dirty=False)
        except Exception:  # noqa: BLE001
            e["error"] = traceback.format_exc()
        rep["variants"][name] = e
    rep["status"] = "ok"
except Exception:  # noqa: BLE001
    rep["errors"].append(traceback.format_exc())
finally:
    with open("%s/import_variants_%s.json" % (UE, RUN), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
