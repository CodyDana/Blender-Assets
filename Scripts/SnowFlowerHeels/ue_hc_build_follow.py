"""Heels Unreal check: /Game/HeelsCheck/<RUN>/ABP_HeelsFollow_CopyPose (commandlet + EditorToolset).

Copy Pose From Mesh (Use Attached Parent = true) -> Output Pose, on her skeleton. The alternative to Leader Pose for a
garment attached to her Body. Writes WorkFiles/SnowFlowerHeels/ue/build_follow_<RUN>.json.
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
IN, OUT = unreal.EdGraphPinDirection.EGPD_INPUT, unreal.EdGraphPinDirection.EGPD_OUTPUT
rep = {"status": "failed", "errors": [], "log": []}
try:
    f = unreal.AnimBlueprintFactory()
    f.set_editor_property("target_skeleton", unreal.load_asset(SKELETON))
    abp = unreal.AssetToolsHelpers.get_asset_tools().create_asset("ABP_HeelsFollow_CopyPose", DEST, unreal.AnimBlueprint, f)
    ag = BT.get_graph(abp, "AnimGraph")
    types = BT.find_node_types(ag, "copyposefrommesh")
    rep["types"] = types
    t = [x for x in types if x.lower().endswith("|copyposefrommesh")] or types
    node = BT.create_node(ag, t[0], unreal.IntPoint(-400, 0))
    rep["set"] = unreal.ToolsetLibrary.set_object_properties(node, json.dumps({"Node": {"bUseAttachedParent": True,
                                                                                        "bCopyCurves": True}}))
    rep["node_props"] = str(unreal.ToolsetLibrary.get_object_properties(node, ["Node"]))[:1500]
    root = [n for n in BT.find_nodes(ag) if "Root" in type(n).__name__][0]
    src = [p for p in node.list_all_pins() if p.get_pin_direction() == OUT and "Pose" in str(p.get_pin_type_display_string())][0]
    dst = [p for p in root.list_all_pins() if p.get_pin_direction() == IN and "Pose" in str(p.get_pin_type_display_string())][0]
    rep["connected"] = src.try_create_connection(dst)
    BT.compile_blueprint(abp)
    rep["abp_status"] = str(abp.get_editor_property("status"))
    rep["saved"] = unreal.EditorAssetLibrary.save_asset(DEST + "/ABP_HeelsFollow_CopyPose", only_if_is_dirty=False)
    rep["status"] = "ok"
except Exception:  # noqa: BLE001
    rep["errors"].append(traceback.format_exc())
finally:
    with open("%s/build_follow_%s.json" % (UE, RUN), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
