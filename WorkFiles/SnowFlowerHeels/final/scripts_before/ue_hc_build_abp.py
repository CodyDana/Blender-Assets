"""Heels Unreal check, step 3 (commandlet, -EnablePlugins=EditorToolset): the TEST anim blueprints.

    /Game/HeelsCheck/<RUN>/ABP_HeelsTest_<Clip>   (Idle, Walk, Run; target skeleton = her metahuman_base_skel)
        Sequence Evaluator (clip AS_Her_<Clip>, Explicit Time <- AnimTime)  ->  Control Rig (CR_HeelPose, HeelAlpha <- HeelAlpha)
        ->  Output Pose
AnimTime / HeelAlpha are ABP variables the capture script sets per frame, so every captured frame is deterministic.
These stand in for her game ABP (ABP_MH_NinjaBody_Female in DemoGame_1, where the Control Rig node goes right after the
Retarget Pose From Mesh node). The body mesh's own post-process ABP (ABP_Body_PostProcess) still runs after them.
Writes WorkFiles/SnowFlowerHeels/ue/build_abp_<RUN>.json.
"""
import json
import traceback

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as BT

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
UE = ROOT + "/WorkFiles/SnowFlowerHeels/ue"
RUN = json.load(open(UE + "/run.json", encoding="utf-8"))["run"]
DEST = "/Game/HeelsCheck/" + RUN
SKELETON = "/Game/MetaHumans/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel"
CR_CLASS = "/Game/HeelsCheck/CR_HeelPose.CR_HeelPose_C"
EAL = unreal.EditorAssetLibrary
rep = {"run": RUN, "status": "failed", "errors": [], "abps": {}}
IN, OUT = unreal.EdGraphPinDirection.EGPD_INPUT, unreal.EdGraphPinDirection.EGPD_OUTPUT


def pins(node):
    return [(p.get_pin_name(), "in" if p.get_pin_direction() == IN else "out", str(p.get_pin_type_display_string()),
             p.get_pin_value()) for p in node.list_all_pins()]


def pin(node, name, direction):
    for p in node.list_all_pins():
        if p.get_pin_direction() == direction and p.get_pin_name() == name:
            return p
    raise RuntimeError("no %s pin %s on %s; has %s" % (direction, name, node.get_node_title(), [x[0] for x in pins(node)]))


def first_pose(node, direction):
    for p in node.list_all_pins():
        if p.get_pin_direction() == direction and "Pose" in str(p.get_pin_type_display_string()):
            return p
    raise RuntimeError("no pose pin on %s" % node.get_node_title())


def connect(a, b, log):
    ok = a.try_create_connection(b)
    log.append("connect %s -> %s : %s" % (a.get_pin_name(), b.get_pin_name(), ok))
    if not ok:
        raise RuntimeError("could not connect %s -> %s" % (a.get_pin_name(), b.get_pin_name()))


def getter(graph, var, x, y, log):
    ed = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    errs = []
    for args in ((var, unreal.Vector2D(x, y)), (unreal.Name(var), unreal.Vector2D(x, y)), (var,), (unreal.Name(var),)):
        try:
            node = ed.add_get_member_variable_node(*args)
            if node is not None:
                log.append("getter %s via %d args" % (var, len(args)))
                return node
        except Exception as exc:  # noqa: BLE001
            errs.append(str(exc)[:200])
    raise RuntimeError("no getter for %s: %s" % (var, errs))


try:
    skeleton = unreal.load_asset(SKELETON)
    for clip in ("Idle", "Walk", "Run"):
        entry = {"log": []}
        log = entry["log"]
        name = "ABP_HeelsTest_" + clip
        path = DEST + "/" + name
        try:
            if EAL.does_asset_exist(path):
                old_asset = unreal.load_asset(path)
                log.append("delete old %s" % unreal.EditorAssetLibrary.delete_loaded_asset(old_asset))
                del old_asset
                unreal.SystemLibrary.collect_garbage()
            f = unreal.AnimBlueprintFactory()
            f.set_editor_property("target_skeleton", skeleton)
            abp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST, unreal.AnimBlueprint, f)
            BT.add_variable(abp, "AnimTime", "float")
            BT.add_variable(abp, "HeelAlpha", "float")
            for v in ("AnimTime", "HeelAlpha"):
                unreal.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(abp, v, True)
            BT.compile_blueprint(abp)
            cdo = unreal.get_default_object(abp.generated_class())
            try:
                cdo.set_editor_property("HeelAlpha", 1.0)
                log.append("HeelAlpha default 1.0")
            except Exception as exc:  # noqa: BLE001
                log.append("HeelAlpha default not set: %s" % exc)
            ag = BT.get_graph(abp, "AnimGraph")
            types = {
                "evaluator": BT.find_node_types(ag, "sequenceevaluator"),
                "controlrig": BT.find_node_types(ag, "controlrig"),
                "animtime": BT.find_node_types(ag, "animtime"),
                "heelalpha": BT.find_node_types(ag, "heelalpha"),
            }
            entry["types"] = types
            ev_t = [t for t in types["evaluator"] if t.lower().endswith("|sequenceevaluator")] or \
                   [t for t in types["evaluator"] if "Casting" not in t and "Make" not in t and "Break" not in t and "Setmembers" not in t]
            cr_t = [t for t in types["controlrig"] if t.lower().endswith("|controlrig")] or \
                   [t for t in types["controlrig"] if "Casting" not in t and "Make" not in t and "Break" not in t]
            get_time_t = [t for t in types["animtime"] if "get" in t.lower()]
            get_alpha_t = [t for t in types["heelalpha"] if "get" in t.lower()]
            log.append("chosen %s %s %s %s" % (ev_t[:1], cr_t[:1], get_time_t[:1], get_alpha_t[:1]))
            ev = BT.create_node(ag, ev_t[0], unreal.IntPoint(-700, 0))
            crn = BT.create_node(ag, cr_t[0], unreal.IntPoint(-300, 0))
            gtime = getter(ag, "AnimTime", -1000, 150, log)
            galpha = getter(ag, "HeelAlpha", -600, 200, log)
            ok = unreal.ToolsetLibrary.set_object_properties(
                ev, json.dumps({"Node": {"Sequence": "%s/Anims/AS_Her_%s.AS_Her_%s" % (DEST, clip, clip), "bShouldLoop": True}}))
            log.append("evaluator props %s" % ok)
            ok = unreal.ToolsetLibrary.set_object_properties(crn, json.dumps({"Node": {"ControlRigClass": CR_CLASS}}))
            log.append("controlrig class (json) %s" % ok)
            ok = unreal.ToolsetLibrary.set_object_properties(crn, json.dumps({"Node": {
                "ControlRigAssetReference": {"BlueprintRigClass": CR_CLASS}}}))
            log.append("asset reference (json) %s" % ok)
            entry["cr_node_Node_after_json"] = str(unreal.ToolsetLibrary.get_object_properties(crn, ["Node"]))[:3000]
            try:
                ns = crn.get_editor_property("node")
                entry["anim_node_struct_props"] = [m for m in dir(ns) if not m.startswith("_")][:120]
                ns.set_editor_property("control_rig_class", unreal.load_object(None, CR_CLASS))
                crn.set_editor_property("node", ns)
                log.append("controlrig class via set_editor_property: %s" %
                           crn.get_editor_property("node").get_editor_property("control_rig_class"))
            except Exception as exc:  # noqa: BLE001
                log.append("set_editor_property route: %s" % str(exc)[:300])
            entry["cr_node_Node_after"] = str(unreal.ToolsetLibrary.get_object_properties(crn, ["Node"]))[:3000]
            try:
                BT.compile_blueprint(abp)
            except Exception as exc:  # noqa: BLE001
                log.append("pre-compile: %s" % str(exc)[:300])
            entry["cr_node_class_props"] = [m for m in dir(crn) if not m.startswith("_")][:200]
            try:
                crn.reconstruct_node()
            except Exception as exc:  # noqa: BLE001
                log.append("reconstruct: %s" % exc)
            entry["cr_node_pins_before_expose"] = pins(crn)
            if not any(p[0] == "HeelAlpha" for p in pins(crn)):
                props = unreal.ToolsetLibrary.get_object_properties(crn, [])
                entry["cr_node_props"] = str(props)[:6000]
                for attempt in ({"ExposedPropertyNames": ["HeelAlpha"]},
                                {"CustomPinProperties": [{"PropertyName": "HeelAlpha", "bShowPin": True}]}):
                    ok = unreal.ToolsetLibrary.set_object_properties(crn, json.dumps(attempt))
                    log.append("expose attempt %s -> %s" % (list(attempt)[0], ok))
                    try:
                        crn.reconstruct_node()
                    except Exception:  # noqa: BLE001
                        pass
                    if any(p[0] == "HeelAlpha" for p in pins(crn)):
                        break
            entry["cr_node_pins"] = pins(crn)
            entry["ev_pins"] = pins(ev)
            root = [n for n in BT.find_nodes(ag) if "Root" in type(n).__name__ or "Output" in str(n.get_node_title())]
            root = root[0]
            connect(pin(gtime, "AnimTime", OUT), pin(ev, "ExplicitTime", IN), log)
            connect(first_pose(ev, OUT), first_pose(crn, IN), log)
            connect(first_pose(crn, OUT), first_pose(root, IN), log)
            if any(p[0] == "HeelAlpha" for p in pins(crn)):
                connect(pin(galpha, "HeelAlpha", OUT), pin(crn, "HeelAlpha", IN), log)
                entry["heel_alpha_wiring"] = "CR variable pin HeelAlpha"
            else:
                # the rig variable pin cannot be exposed from Python in 5.8 (CustomPinProperties is not settable), so the
                # ABP's HeelAlpha drives the node's Alpha: 0 = input pose untouched (barefoot), 1 = full correction
                alpha_pin = [p for p in crn.list_all_pins() if p.get_pin_direction() == IN and p.get_pin_name() == "Alpha"]
                connect(pin(galpha, "HeelAlpha", OUT), alpha_pin[0], log)
                entry["heel_alpha_wiring"] = "ABP HeelAlpha -> Control Rig node Alpha (rig variable HeelAlpha stays 1)"
            entry["cr_node_Node_final"] = str(unreal.ToolsetLibrary.get_object_properties(crn, ["Node"]))[:3000]
            BT.compile_blueprint(abp)
            entry["status"] = str(abp.get_editor_property("status")) if True else ""
            entry["graph_dsl"] = str(BT.read_graph_dsl(ag))[:4000] if hasattr(BT, "read_graph_dsl") else None
            entry["saved"] = EAL.save_asset(path, only_if_is_dirty=False)
            entry["path"] = path
        except Exception:  # noqa: BLE001
            entry["error"] = traceback.format_exc()
        rep["abps"][clip] = entry
    rep["status"] = "ok" if all("error" not in e for e in rep["abps"].values()) else "partial"
except Exception:  # noqa: BLE001
    rep["errors"].append(traceback.format_exc())
finally:
    with open("%s/build_abp_%s.json" % (UE, RUN), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
    unreal.log("[hc_build_abp] status " + rep["status"])
