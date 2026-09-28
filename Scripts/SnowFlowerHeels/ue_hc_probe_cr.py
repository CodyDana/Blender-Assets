"""Probe the Control Rig / RigVM / AnimGraph Python API in UE 5.8 (commandlet; creates only TRANSIENT assets, saves nothing).
Writes WorkFiles/SnowFlowerHeels/ue/probe_cr.json."""
import json
import traceback

import unreal

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlowerHeels/ue/probe_cr.json"
rep = {"errors": []}
WANT = ["RigUnit_BeginExecution", "RigUnit_GetTransform", "RigUnit_SetTransform", "RigUnit_SetTranslation",
        "RigUnit_TwoBoneIKSimplePerItem", "RigVMFunction_MathTransformTransformVector", "RigVMFunction_MathVectorSub",
        "RigVMFunction_MathVectorAdd", "RigVMFunction_MathVectorScale", "RigVMFunction_MathVectorLength",
        "RigVMFunction_MathVectorUnit", "RigVMFunction_MathVectorCross", "RigVMFunction_MathVectorMake",
        "RigVMFunction_MathFloatAdd", "RigVMFunction_MathFloatSub", "RigVMFunction_MathFloatMul", "RigVMFunction_MathFloatDiv",
        "RigVMFunction_MathFloatMin", "RigVMFunction_MathFloatMax", "RigVMFunction_MathFloatClamp", "RigVMFunction_MathFloatSqrt",
        "RigVMFunction_MathFloatAtan2", "RigVMFunction_MathFloatDeg", "RigVMFunction_MathFloatRad", "RigVMFunction_MathFloatLerp",
        "RigVMFunction_MathQuaternionFromAxisAndAngle", "RigVMFunction_MathQuaternionMul", "RigVMFunction_MathQuaternionRotateVector",
        "RigVMFunction_GetDeltaTime", "RigVMFunction_MathTransformMake", "RigVMFunction_MathFloatExp"]
try:
    rep["subsystems"] = {n: hasattr(unreal, n) for n in ["ControlRigBlueprintFactory"]}
    cr = unreal.ControlRigBlueprintFactory.create_new_control_rig_asset("/Game/HeelsCheck/_probe/CR_Probe")
    rep["cr"] = cr.get_path_name() if cr else None
    ctrl = cr.get_controller_by_name("RigVMModel") or cr.get_controller()
    graph = ctrl.get_graph()
    rep["initial_nodes"] = [n.get_name() + " : " + str(n.get_class().get_name()) for n in graph.get_nodes()]
    for n in graph.get_nodes():
        rep.setdefault("initial_pins", {})[n.get_name()] = [p.get_pin_path() for p in n.get_pins()]
    structs = []
    try:
        structs = [s.get_path_name() if hasattr(s, "get_path_name") else str(s) for s in ctrl.get_registered_unit_structs()]
    except Exception as exc:  # noqa: BLE001
        rep["errors"].append("registered structs: %s" % exc)
    rep["registered_unit_structs_count"] = len(structs)
    rep["registered_match"] = [s for s in structs if any(k in s for k in ("MathFloat", "MathVector", "MathQuaternion", "MathTransform",
                                                                       "DeltaTime", "TwoBone", "GetTransform", "SetTransform",
                                                                       "BeginExecution", "Select", "If", "Expression"))][:400]
    pins = {}
    for i, w in enumerate(WANT):
        found = [s for s in structs if s.endswith("." + w)]
        path = found[0] if found else None
        entry = {"path": path}
        if path:
            try:
                node = ctrl.add_unit_node_from_struct_path(path, "Execute", unreal.Vector2D(0, i * 200), w)
                if node is None:
                    entry["error"] = "add returned None"
                else:
                    entry["node"] = node.get_name()
                    entry["pins"] = [(p.get_pin_path(), str(p.get_direction()), p.get_cpp_type(), p.get_default_value())
                                     for p in node.get_pins()]
                    entry["subpins"] = {p.get_name(): [sp.get_pin_path() for sp in p.get_sub_pins()] for p in node.get_pins()
                                        if p.get_sub_pins()}
            except Exception as exc:  # noqa: BLE001
                entry["error"] = str(exc)
        pins[w] = entry
    rep["pins"] = pins
    # variables
    try:
        rep["add_var"] = str(cr.add_member_variable("HeelAlpha", "float", True, False, "1.0"))
        rep["vars"] = [str(v.get_editor_property("name")) + ":" + str(v.get_editor_property("type"))
                       for v in cr.get_member_variables()]
        vn = ctrl.add_variable_node("HeelAlpha", "float", None, True, "", unreal.Vector2D(0, -400), "Get_HeelAlpha")
        rep["var_node_pins"] = [p.get_pin_path() for p in vn.get_pins()] if vn else None
    except Exception:  # noqa: BLE001
        rep["errors"].append("var: " + traceback.format_exc())
    # hierarchy import
    try:
        hc = cr.get_hierarchy_controller()
        rep["hc_methods"] = [m for m in dir(hc) if "import" in m.lower()]
        sk = unreal.load_asset("/Game/MetaHumans/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel")
        keys = hc.import_bones(sk, "None", True, True, False, False)
        rep["imported_bones"] = len(keys)
        rep["preview_mesh_methods"] = [m for m in dir(cr) if "preview" in m.lower()]
    except Exception:  # noqa: BLE001
        rep["errors"].append("hier: " + traceback.format_exc())
    # control rig instance API
    try:
        rep["cr_generated_class"] = str(cr.generated_class())
        inst = cr.create_control_rig() if hasattr(cr, "create_control_rig") else None
        rep["instance"] = str(inst)
        if inst:
            rep["instance_methods"] = [m for m in dir(inst) if not m.startswith("_")]
            h = inst.get_hierarchy()
            rep["hier_methods"] = [m for m in dir(h) if not m.startswith("_")]
    except Exception:  # noqa: BLE001
        rep["errors"].append("inst: " + traceback.format_exc())
    # anim graph: ABP + editor toolset
    try:
        f = unreal.AnimBlueprintFactory()
        f.set_editor_property("target_skeleton", unreal.load_asset("/Game/MetaHumans/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel"))
        abp = unreal.AssetToolsHelpers.get_asset_tools().create_asset("ABP_Probe", "/Game/HeelsCheck/_probe", unreal.AnimBlueprint, f)
        from editor_toolset.toolsets.blueprint import BlueprintTools as BT
        graphs = BT.list_graphs(abp)
        rep["abp_graphs"] = [g.get_name() for g in graphs]
        ag = [g for g in graphs if g.get_name() == "AnimGraph"][0]
        rep["abp_types_controlrig"] = BT.find_node_types(ag, "control rig")[:40]
        rep["abp_types_seq"] = BT.find_node_types(ag, "sequence")[:40]
        rep["abp_types_evaluator"] = BT.find_node_types(ag, "evaluat")[:40]
        rep["sms_methods"] = [m for m in dir(unreal.SkeletalMeshEditorSubsystem) if "lod" in m.lower() or "screen" in m.lower()]
        rep["skm_props"] = [m for m in dir(unreal.SkeletalMesh) if not m.startswith("_")]
    except Exception:  # noqa: BLE001
        rep["errors"].append("abp: " + traceback.format_exc())
except Exception:  # noqa: BLE001
    rep["errors"].append(traceback.format_exc())
finally:
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
    unreal.log("[hc_probe] done")
