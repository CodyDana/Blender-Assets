"""Heels Unreal check, step 0: read-only recon of CharacterLab (commandlet, -nullrhi, saves nothing).

Reports her BP's components, the body mesh (post-process ABP, LODs, skeleton), candidate locomotion clips in the
MetaHumanCharacter plugin, which editor Python APIs exist (Control Rig / RigVM, IK retarget, EditorToolset), and the
leg bones' reference frames (for the two-bone IK axes). Writes WorkFiles/SnowFlowerHeels/ue/recon.json.
"""
import json
import traceback

import unreal

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlowerHeels/ue/recon.json"
BP = "/Game/MetaHumans/MH_PlayerFemale/BP_MH_PlayerFemale"
BODY = "/Game/MetaHumans/MH_PlayerFemale/Body/SKM_MH_PlayerFemale_BodyMesh"
rep = {"status": "failed", "errors": []}


def safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return "ERR " + str(exc)[:200]


def v(x):
    return [round(x.x, 5), round(x.y, 5), round(x.z, 5)]


try:
    rep["engine"] = unreal.SystemLibrary.get_engine_version()
    apis = {}
    for name in ["ControlRigBlueprintFactory", "ControlRigBlueprint", "RigVMController", "RigHierarchyController",
                 "IKRetargetBatchOperation", "IKRetargeterController", "IKRigController", "BlueprintGraphEditor",
                 "AnimGraphNode_ControlRig", "AnimGraphNode_SequenceEvaluator", "AnimGraphNode_SequencePlayer",
                 "ControlRigComponent", "AnimBlueprintFactory", "SkeletalMeshEditorSubsystem", "RigUnit_TwoBoneIKSimplePerItem",
                 "RigVMFunction_MathFloatAtan2", "RigVMFunction_MathQuaternionFromAxisAndAngle", "EditorAnimationLibrary",
                 "AnimationLibrary", "ControlRigBlueprintLibrary", "RigVMBlueprint", "ControlRigBlueprintEditorLibrary"]:
        apis[name] = hasattr(unreal, name)
    rep["apis"] = apis
    if hasattr(unreal, "ControlRigBlueprintFactory"):
        rep["cr_factory_methods"] = [m for m in dir(unreal.ControlRigBlueprintFactory) if not m.startswith("_")][:80]
    if hasattr(unreal, "ControlRigBlueprint"):
        rep["cr_bp_methods"] = [m for m in dir(unreal.ControlRigBlueprint) if not m.startswith("_")]
    if hasattr(unreal, "RigVMController"):
        rep["rigvm_controller_methods"] = [m for m in dir(unreal.RigVMController) if not m.startswith("_")]
    # the BP
    bp = unreal.load_asset(BP)
    gen = unreal.load_object(None, BP + ".BP_MH_PlayerFemale_C")
    cdo = unreal.get_default_object(gen)
    rep["bp_class"] = gen.get_name() if gen else None
    subsys = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    comps = []
    handles = subsys.k2_gather_subobject_data_for_blueprint(bp)
    for h in handles:
        data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
        obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data)
        if obj is None:
            continue
        entry = {"name": obj.get_name(), "class": obj.get_class().get_name()}
        if isinstance(obj, unreal.SkinnedMeshComponent):
            entry["mesh"] = safe(lambda: obj.get_editor_property("skeletal_mesh_asset").get_path_name())
            entry["anim_class"] = safe(lambda: str(obj.get_editor_property("anim_class")))
            entry["anim_mode"] = safe(lambda: str(obj.get_editor_property("animation_mode")))
            entry["leader"] = safe(lambda: str(obj.get_editor_property("leader_pose_component")))
            entry["update_in_editor"] = safe(lambda: obj.get_editor_property("update_animation_in_editor"))
        if isinstance(obj, unreal.SceneComponent):
            entry["attach"] = safe(lambda: str(obj.get_editor_property("attach_parent")))
            entry["rel_loc"] = safe(lambda: v(obj.get_editor_property("relative_location")))
            entry["rel_rot"] = safe(lambda: str(obj.get_editor_property("relative_rotation")))
        comps.append(entry)
    rep["bp_components"] = comps
    # function/graph names on the BP (does it have a construction script / LODSync etc.)
    rep["bp_graphs"] = safe(lambda: [g.get_name() for g in unreal.BlueprintEditorLibrary.list_graphs(bp)]) \
        if hasattr(unreal, "BlueprintEditorLibrary") else "n/a"
    body = unreal.load_asset(BODY)
    rep["body"] = {
        "skeleton": body.get_editor_property("skeleton").get_path_name(),
        "post_process_abp": safe(lambda: str(body.get_editor_property("post_process_anim_blueprint"))),
        "lods": unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(body),
        "physics": safe(lambda: body.get_editor_property("physics_asset").get_path_name()),
    }
    lod_info = []
    for i, li in enumerate(safe(lambda: body.get_editor_property("lod_info"), []) or []):
        lod_info.append({"i": i, "screen_size": safe(lambda: str(li.get_editor_property("screen_size")))})
    rep["body"]["lod_info"] = lod_info
    # clips
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    clips = []
    for path in ["/MetaHumanCharacter/Optional/Animation"]:
        ar.scan_paths_synchronous([path], True)
        for ad in ar.get_assets_by_path(path, recursive=True):
            cls = str(ad.asset_class_path.asset_name)
            name = str(ad.asset_name)
            if cls in ("AnimSequence",) and any(k in name for k in ("Walk_Loop_F", "Run_Loop_F", "Idle", "Stand")):
                a = ad.get_asset()
                clips.append({"path": str(ad.package_name), "skeleton": safe(lambda: a.get_editor_property("skeleton").get_path_name()),
                              "length": safe(lambda: a.get_play_length()),
                              "root_motion": safe(lambda: a.get_editor_property("enable_root_motion")),
                              "rate": safe(lambda: str(a.get_editor_property("target_frame_rate")))})
            elif cls != "AnimSequence":
                clips.append({"path": str(ad.package_name), "class": cls})
    rep["clips"] = clips[:120]
    # leg frames at ref pose (component space)
    comp = unreal.new_object(unreal.SkeletalMeshComponent)
    comp.set_skinned_asset_and_update(body) if hasattr(comp, "set_skinned_asset_and_update") else comp.set_skeletal_mesh_asset(body)
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
    frames = {}
    for n in ["root", "pelvis", "thigh_l", "calf_l", "foot_l", "ball_l", "thigh_r", "calf_r", "foot_r", "ball_r",
              "calf_twist_01_l", "calf_twist_02_l", "thigh_twist_01_l"]:
        if n not in local:
            continue
        t = cs(n)
        m = t.to_matrix()
        frames[n] = {"parent": parent[n], "loc_cs": v(t.translation), "rot_cs": str(t.rotation.rotator()),
                     "x_axis": v(t.rotation.get_axis_x()), "y_axis": v(t.rotation.get_axis_y()), "z_axis": v(t.rotation.get_axis_z()),
                     "local_loc": v(local[n].translation), "local_rot": str(local[n].rotation.rotator())}
    rep["frames"] = frames
    rep["children_of_foot_l"] = [n for n, p in parent.items() if p == "foot_l"]
    rep["children_of_calf_l"] = [n for n, p in parent.items() if p == "calf_l"]
    rep["children_of_ball_l"] = [n for n, p in parent.items() if p == "ball_l"]
    rep["status"] = "ok"
except Exception:  # noqa: BLE001
    rep["errors"].append(traceback.format_exc())
finally:
    import os
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
    unreal.log("[hc_recon] " + rep["status"])
