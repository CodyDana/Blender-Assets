"""TEST ONLY: import the centimetre re-export (WorkFiles/SnowFlowerHeels/ue/test_export_cm) as
/Game/HeelsCheck/<RUN>/fixtest/SK_SnowFlowerHeels_cm with the same import settings, LODs, LOD screen sizes and test
materials as the shipped import, and compare its reference pose (LOCAL, incl. scale) with her body.
Writes WorkFiles/SnowFlowerHeels/ue/import_fix_<RUN>.json."""
import json
import traceback

import unreal

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
UE = ROOT + "/WorkFiles/SnowFlowerHeels/ue"
RUN = json.load(open(UE + "/run.json", encoding="utf-8"))["run"]
DEST = "/Game/HeelsCheck/%s/fixtest" % RUN
SRC = UE + "/test_export_cm"
SKELETON = "/Game/MetaHumans/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel"
BODY = "/Game/MetaHumans/MH_PlayerFemale/Body/SKM_MH_PlayerFemale_BodyMesh"
SMS = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
rep = {"status": "failed", "errors": []}


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


try:
    skeleton = unreal.load_asset(SKELETON)
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
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", SRC + "/SK_SnowFlowerHeels.fbx")
    task.set_editor_property("destination_path", DEST)
    task.set_editor_property("destination_name", "SK_SnowFlowerHeels_cm")
    task.set_editor_property("automated", True)
    task.set_editor_property("save", False)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("options", ui)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
    mesh = [m for m in (unreal.load_asset(p) for p in paths) if isinstance(m, unreal.SkeletalMesh)][0]
    for i, f in ((1, "SK_SnowFlowerHeels_LOD1.fbx"), (2, "SK_SnowFlowerHeels_LOD2.fbx")):
        rep["import_lod_%d" % i] = SMS.import_lod(mesh, i, SRC + "/" + f)
    rep["verts"] = [SMS.get_num_verts(mesh, i) for i in range(SMS.get_lod_count(mesh))]
    mats = mesh.get_editor_property("materials")
    for i, m in enumerate(mats):
        slot = str(m.get_editor_property("material_slot_name")).replace("M_SnowFlowerHeels_", "")
        m.set_editor_property("material_interface", unreal.load_asset("/Game/HeelsCheck/%s/Materials/MI_HeelsCheck_%s" % (RUN, slot)))
        mats[i] = m
    mesh.set_editor_property("materials", mats)
    mesh.set_editor_property("lod_settings", unreal.load_asset("/Game/HeelsCheck/%s/LODS_SnowFlowerHeels" % RUN))
    local, cs = ref(mesh)
    body_local, body_cs = ref(unreal.load_asset(BODY))
    r = local["root"]
    rep["root_local_scale"] = [r.scale3d.x, r.scale3d.y, r.scale3d.z]
    rep["local_max_dt_cm"] = max((local[n].translation - body_local[n].translation).length() for n in body_local if n in local)
    rep["cs_max_dt_cm"] = max((cs[n].translation - body_cs[n].translation).length() for n in body_cs if n in cs)
    rep["max_local_scale_dev"] = max(max(abs(local[n].scale3d.x - 1), abs(local[n].scale3d.y - 1), abs(local[n].scale3d.z - 1)) for n in local)
    b = mesh.get_bounds()
    rep["bounds"] = [[b.origin.x - b.box_extent.x, b.origin.y - b.box_extent.y, b.origin.z - b.box_extent.z],
                     [b.origin.x + b.box_extent.x, b.origin.y + b.box_extent.y, b.origin.z + b.box_extent.z]]
    rep["saved"] = unreal.EditorAssetLibrary.save_asset(DEST + "/SK_SnowFlowerHeels_cm", only_if_is_dirty=False)
    rep["path"] = mesh.get_path_name()
    rep["status"] = "ok"
except Exception:  # noqa: BLE001
    rep["errors"].append(traceback.format_exc())
finally:
    with open("%s/import_fix_%s.json" % (UE, RUN), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
