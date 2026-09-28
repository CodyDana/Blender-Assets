"""Probe AnimGraph node types for variable getters (commandlet + EditorToolset; transient assets, saves nothing)."""
import json
import traceback

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as BT

OUT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlowerHeels/ue/probe_abp.json"
rep = {"errors": []}
try:
    f = unreal.AnimBlueprintFactory()
    f.set_editor_property("target_skeleton", unreal.load_asset("/Game/MetaHumans/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel"))
    abp = unreal.AssetToolsHelpers.get_asset_tools().create_asset("ABP_Probe2", "/Game/HeelsCheck/_probe", unreal.AnimBlueprint, f)
    BT.add_variable(abp, "AnimTime", "float")
    BT.compile_blueprint(abp)
    rep["vars"] = [str(v) for v in unreal.BlueprintEditorLibrary.list_member_variable_names(abp, False)]
    for gname in ("AnimGraph", "EventGraph"):
        g = BT.get_graph(abp, gname)
        rep[gname + "_cats"] = BT.find_node_categories(g, "")
        rep[gname + "_var"] = [t for t in BT.find_node_types(g, "variables") if "Cast" not in t][:80]
        rep[gname + "_animtime"] = BT.find_node_types(g, "animtime")
    ag = BT.get_graph(abp, "AnimGraph")
    for tid in ("Variables|AnimTime", "Variables|GetAnimTime", "Default|AnimTime", "Default|GetAnimTime", "|AnimTime", "AnimTime"):
        try:
            n = BT.create_node(ag, tid, unreal.IntPoint(0, 0))
            rep.setdefault("created", {})[tid] = [p.get_pin_name() for p in n.list_all_pins()] + [type(n).__name__]
        except Exception as exc:  # noqa: BLE001
            rep.setdefault("created", {})[tid] = "ERR " + str(exc)[:200]
    eg = BT.get_graph(abp, "EventGraph")
    try:
        n = BT.create_node(eg, [t for t in BT.find_node_types(eg, "animtime") if "Get" in t][0], unreal.IntPoint(0, 0))
        rep["eg_get_node"] = [type(n).__name__, str(n.get_node_title()), str(n.get_node_category())]
    except Exception as exc:  # noqa: BLE001
        rep["eg_get_node"] = "ERR " + str(exc)[:300]
    rep["bpge_methods"] = [m for m in dir(unreal.BlueprintGraphEditor) if not m.startswith("_")]
    rep["bel_methods"] = [m for m in dir(unreal.BlueprintEditorLibrary) if "var" in m.lower() or "node" in m.lower()]
except Exception:  # noqa: BLE001
    rep["errors"].append(traceback.format_exc())
finally:
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
