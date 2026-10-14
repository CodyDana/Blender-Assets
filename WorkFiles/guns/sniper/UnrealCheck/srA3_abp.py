"""SR01 W5, pass A3 (a fresh UnrealEditor-Cmd, -nullrhi, -EnablePlugins=AllToolsets for the Blueprint graph toolset):
author <dest>/ABP_Gun_LongGun, the long-gun class Anim Blueprint for gate U2b, on SK_AR01_Skeleton (the AR-01's verified
import, /Game/GunCheck/AR01_1009b; nothing there is saved). Parent: AnimInstance (the verification project has no C++
module); the inputs are Blueprint variables, instance-editable so pass C sets them per gun.

Inputs (normalized, plan 2.2 / check fix C5):  Bolt01, BoltRot01, Trigger01, Release01, Riser01 (0..1), SelectorIndex
(0 SAFE, 1 SEMI / FIRE, 2 AUTO / FIRE).  Per-gun angle table (the gun's sidecar abp_angle_table):  BoltTravelCm,
BoltRotateDeg, TriggerMaxDeg, ReleaseMaxDeg, RiserMaxCm, SelectorDetentsDeg[3] (degrees about the bone's Blender axis,
Blender sign). The Blender -> Unreal sign: about Blender +Y = Unreal pitch -, about +Z = yaw - (one Invert Rotator per node,
as the SMG's), about +X = Unreal roll + (Y mirrored: F R_x(a) F = R_x(-a), and an FRotator roll r is R_x(-r); so the bolt's
roll node has NO Invert Rotator):

  Local Ref Pose -> Local To Component
    -> Transform (Modify) Bone `bolt`        translation ADDITIVE, bone space, -(BoltTravelCm, 0, 0), alpha Bolt01
    -> Transform (Modify) Bone `bolt`        rotation ADDITIVE, bone space, roll +BoltRotateDeg, alpha BoltRot01
    -> Transform (Modify) Bone `trigger`     rotation ADDITIVE, bone space, -(0, TriggerMaxDeg, 0), alpha Trigger01
    -> Transform (Modify) Bone `selector`    rotation ADDITIVE, bone space, -(0, SelectorDetentsDeg[SelectorIndex], 0)
    -> Transform (Modify) Bone `mag_release` rotation ADDITIVE, bone space, -(0, ReleaseMaxDeg, 0), alpha Release01
    -> Transform (Modify) Bone `cheek_riser` translation ADDITIVE, bone space, (0, 0, RiserMaxCm), alpha Riser01
       (`cheek_riser` is NOT in SK_AR01_Skeleton: the missing-bone probe of U2b)
  -> Component To Local -> Output Pose
Writes srA3_abp.json. Saves only <dest>/ABP_Gun_LongGun.
"""
import json
import sys
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import sr_common as C  # noqa: E402

DEST = C.dest()
PATH = f"{DEST}/{C.ABP_NAME}"
OUT = C.HERE / "srA3_abp.json"
IN, OUTD = unreal.EdGraphPinDirection.EGPD_INPUT, unreal.EdGraphPinDirection.EGPD_OUTPUT
EAL = unreal.EditorAssetLibrary
REP = {"t0": time.time(), "path": PATH, "log": [], "errors": [], "hashes_before": C.all_hashes()}
LOG = REP["log"]
FLOATS = ("Bolt01", "BoltRot01", "Trigger01", "Release01", "Riser01", "BoltTravelCm", "BoltRotateDeg", "TriggerMaxDeg",
          "ReleaseMaxDeg", "RiserMaxCm")


def dump():
    REP["seconds"] = round(time.time() - REP["t0"], 1)
    C.write(OUT, REP)


def pins(node):
    return [(str(p.get_pin_name()), "in" if p.get_pin_direction() == IN else "out", str(p.get_pin_type_display_string()))
            for p in node.list_all_pins()]


def pin(node, name, direction):
    for p in node.list_all_pins():
        if p.get_pin_direction() == direction and str(p.get_pin_name()) == name:
            return p
    raise RuntimeError(f"no {name} pin on {node.get_node_title()}; has {pins(node)}")


def pose_pin(node, direction, idx=0):
    ps = [p for p in node.list_all_pins() if p.get_pin_direction() == direction and "Pose" in str(p.get_pin_type_display_string())]
    if len(ps) <= idx:
        raise RuntimeError(f"no pose pin {idx} on {node.get_node_title()}: {pins(node)}")
    return ps[idx]


def data_pin(node, direction, skip=()):
    ps = [p for p in node.list_all_pins() if p.get_pin_direction() == direction and "Exec" not in str(p.get_pin_type_display_string())
          and str(p.get_pin_name()) not in skip and not str(p.get_pin_name()).startswith("self")]
    if len(ps) != 1:
        raise RuntimeError(f"expected one data pin on {node.get_node_title()}: {pins(node)}")
    return ps[0]


def connect(a, b):
    ok = a.try_create_connection(b)
    LOG.append(f"connect {str(a.get_owning_node().get_node_title())[:40]}.{a.get_pin_name()} -> "
               f"{str(b.get_owning_node().get_node_title())[:40]}.{b.get_pin_name()}: {ok}")
    if not ok:
        raise RuntimeError(LOG[-1])


def setp(node, props):
    ok = unreal.ToolsetLibrary.set_object_properties(node, json.dumps(props))
    LOG.append(f"set {str(node.get_node_title())[:40]} {list(props.get('Node', props))}: {ok}")
    if not ok:
        raise RuntimeError(LOG[-1])
    if hasattr(node, "reconstruct_node"):
        node.reconstruct_node()


def main():
    from editor_toolset.toolsets.blueprint import BlueprintTools as BT  # noqa: N814
    if EAL.does_asset_exist(PATH):
        raise RuntimeError(f"{PATH} exists: pick a new run name")
    skel = unreal.load_asset(C.AR_SKEL)
    if skel is None:
        raise RuntimeError(f"no {C.AR_SKEL}")
    f = unreal.AnimBlueprintFactory()
    f.set_editor_property("target_skeleton", skel)
    f.set_editor_property("parent_class", unreal.AnimInstance)
    abp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(C.ABP_NAME, DEST, unreal.AnimBlueprint, f)
    REP["parent"] = str(BT.get_parent(abp).get_path_name())
    REP["target_skeleton"] = abp.get_editor_property("target_skeleton").get_path_name()
    # ------------------------------------------------------------------ variables
    for v in FLOATS:
        BT.add_variable(abp, v, "float")
    BT.add_variable(abp, "SelectorIndex", "int")
    arr = None
    for ct in ("ARRAY", "Array", "array"):
        try:
            BT.add_variable(abp, "SelectorDetentsDeg", "float", None, getattr(__import__("editor_toolset.toolsets.blueprint", fromlist=["ContainerType"]).ContainerType, ct))
            arr = ct
            break
        except Exception as exc:  # noqa: BLE001
            LOG.append(f"array variable via {ct}: {exc}")
    REP["selector_array_variable"] = arr
    if arr is None:
        for v in ("SelectorSafeDeg", "SelectorSemiDeg", "SelectorAutoDeg"):
            BT.add_variable(abp, v, "float")
    for v in BT.list_variables(abp):
        BT.set_variable_instance_editable(abp, v, True)
    REP["variables"] = BT.list_variables(abp)
    unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    ag = BT.get_graph(abp, "AnimGraph")

    cache = {}

    def ntype(flt, *ends):
        key = (flt, ends)
        if key in cache:
            return cache[key]
        types = [t for f_ in flt.split(",") for t in BT.find_node_types(ag, f_)]
        for e in ends:
            hit = [t for t in types if t.lower().replace(" ", "").endswith(e)]
            if hit:
                cache[key] = hit[0]
                return hit[0]
        raise RuntimeError(f"no node type for {flt} {ends}: {types[:40]}")

    REP["candidates"] = {k: BT.find_node_types(ag, k)[:25] for k in ("bolt01", "selectorindex", "selectordetents", "refpose", "makerotator", "negaterotator", "invertrotator", "negatevector",
                                                                     "makevector", "get(acopy)", "getacopy", "selectfloat")}
    T = {"ref": ntype("refpose", "poses|localspacerefpose", "localrefpose"),
         "l2c": ntype("localtocomponent", "convertspaces|localtocomponent"),
         "c2l": ntype("componenttolocal", "convertspaces|componenttolocal"),
         "modify": ntype("modify", "transform(modify)bone"),
         "mkrot": ntype("makerotator", "math|rotator|makerotator", "|makerotator"),
         "negrot": ntype("invertrotator,negaterotator", "math|rotator|invertrotator", "|negaterotator"),
         "mkvec": ntype("makevector", "math|vector|makevector", "|makevector"),
         "negvec": ntype("negatevector", "math|vector|negatevector", "|negatevector")}
    if arr is not None:
        T["arrget"] = ntype("get", "array|get(acopy)", "|get(acopy)", "|getacopy", "array|get")
    REP["node_types"] = T

    def mk(key, x, y):
        return BT.create_node(ag, T[key], unreal.IntPoint(x, y))

    root = [n for n in BT.find_nodes(ag) if "Root" in type(n).__name__][0]
    ref, l2c, c2l = mk("ref", -2400, 0), mk("l2c", -2100, 0), mk("c2l", 1200, 0)
    chain = []
    xs = -1800
    specs = [("bolt", "bolt", "trans"), ("bolt_rot", "bolt", "rot"), ("trigger", "trigger", "rot"), ("selector", "selector", "rot"),
             ("mag_release", "mag_release", "rot"), ("cheek_riser", "cheek_riser", "trans")]
    nodes = {}
    for key, bone, kind in specs:
        n = mk("modify", xs, 0)
        xs += 550
        props = {"BoneToModify": {"BoneName": bone}, "ScaleMode": "BMM_Ignore"}
        if kind == "trans":
            props.update({"TranslationMode": "BMM_Additive", "TranslationSpace": "BCS_BoneSpace", "RotationMode": "BMM_Ignore"})
        else:
            props.update({"RotationMode": "BMM_Additive", "RotationSpace": "BCS_BoneSpace", "TranslationMode": "BMM_Ignore"})
        setp(n, {"Node": props})
        nodes[key] = n
        chain.append(n)
    # pose chain
    connect(pose_pin(ref, OUTD), pose_pin(l2c, IN))
    connect(pose_pin(l2c, OUTD), pin(chain[0], "ComponentPose", IN))
    for a, b in zip(chain, chain[1:]):
        connect(pin(a, "Pose", OUTD), pin(b, "ComponentPose", IN))
    connect(pin(chain[-1], "Pose", OUTD), pose_pin(c2l, IN))
    connect(pose_pin(c2l, OUTD), pose_pin(root, IN))

    ged = unreal.BlueprintGraphEditor.get_graph_editor(ag)

    def getter(v, x, y):
        g = ged.add_get_member_variable_node(unreal.Name(v))
        if g is None:
            raise RuntimeError(f"no getter for {v}")
        g.set_node_pos(unreal.IntPoint(x, y)) if hasattr(g, "set_node_pos") else None
        return data_pin(g, OUTD)

    # bolt: -(BoltTravelCm, 0, 0), alpha Bolt01
    x0 = nodes["bolt"].get_node_pos_x() if hasattr(nodes["bolt"], "get_node_pos_x") else -1800
    mv, nv = mk("mkvec", -1900, 500), mk("negvec", -1700, 500)
    connect(getter("BoltTravelCm", -2150, 500), pin(mv, "X", IN))
    connect(pin(mv, "ReturnValue", OUTD), data_pin(nv, IN))
    connect(data_pin(nv, OUTD), pin(nodes["bolt"], "Translation", IN))
    connect(getter("Bolt01", -2150, 700), pin(nodes["bolt"], "Alpha", IN))

    def rot_input(bone, value_pin, axis, alpha_var, y, negate=True):
        mr = mk("mkrot", -900, y)
        connect(value_pin, pin(mr, axis, IN))
        if negate:
            nr = mk("negrot", -700, y)
            connect(pin(mr, "ReturnValue", OUTD), data_pin(nr, IN))
            connect(data_pin(nr, OUTD), pin(nodes[bone], "Rotation", IN))
        else:
            connect(pin(mr, "ReturnValue", OUTD), pin(nodes[bone], "Rotation", IN))
        if alpha_var:
            connect(getter(alpha_var, -900, y + 200), pin(nodes[bone], "Alpha", IN))

    rot_input("bolt_rot", getter("BoltRotateDeg", -1150, 500), "Roll", "BoltRot01", 500, negate=False)
    rot_input("trigger", getter("TriggerMaxDeg", -1150, 900), "Pitch", "Trigger01", 900)
    if arr is not None:
        ag_ = mk("arrget", -1150, 1300)
        arr_pins = [p for p in ag_.list_all_pins() if p.get_pin_direction() == IN]
        connect(getter("SelectorDetentsDeg", -1400, 1300), arr_pins[0])
        connect(getter("SelectorIndex", -1400, 1400), arr_pins[1])
        outs = [p for p in ag_.list_all_pins() if p.get_pin_direction() == OUTD]
        REP["array_get_pins"] = pins(ag_)
        sel_val = outs[0]
    else:
        raise RuntimeError("array variable unavailable; the select-float fallback is not implemented")
    rot_input("selector", sel_val, "Pitch", None, 1300)
    rot_input("mag_release", getter("ReleaseMaxDeg", -1150, 1700), "Pitch", "Release01", 1700)
    # cheek riser: +(0, 0, RiserMaxCm) (Blender +Z = Unreal +Z), alpha Riser01
    mv2 = mk("mkvec", -900, 2100)
    connect(getter("RiserMaxCm", -1150, 2100), pin(mv2, "Z", IN))
    connect(pin(mv2, "ReturnValue", OUTD), pin(nodes["cheek_riser"], "Translation", IN))
    connect(getter("Riser01", -1150, 2300), pin(nodes["cheek_riser"], "Alpha", IN))

    # walk back from the output
    names, cur = [], root
    for _ in range(12):
        ins = [p for p in cur.list_all_pins() if p.get_pin_direction() == IN and "Pose" in str(p.get_pin_type_display_string())]
        linked = [q for p in ins for q in p.list_connected_pins()]
        if not linked:
            break
        cur = linked[0].get_owning_node()
        names.append(str(cur.get_node_title()).replace(chr(10), " ")[:80])
    REP["chain_from_output"] = names
    unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    msgs = []
    for g in unreal.BlueprintEditorLibrary.list_graphs(abp) if hasattr(unreal.BlueprintEditorLibrary, "list_graphs") else BT.list_graphs(abp):
        ed = unreal.BlueprintGraphEditor.get_graph_editor(g)
        try:
            for n in ed.list_nodes_with_errors() or []:
                msgs.append(f"{n.get_node_title()}: {C.safe(lambda n=n: n.get_editor_property('error_msg'))}")
        except Exception as exc:  # noqa: BLE001
            msgs.append(f"(list_nodes_with_errors: {exc})")
    REP["compile"] = {"status": str(abp.get_editor_property("status")), "node_messages": msgs}
    REP["readback"] = {b: str(unreal.ToolsetLibrary.get_object_properties(n, ["Node"]))[:900] for b, n in nodes.items()}
    REP["skeleton_dirty_after_compile"] = skel.get_outermost().get_name() in [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    REP["saved"] = bool(EAL.save_asset(PATH, only_if_is_dirty=False))
    REP["dirty_not_saved"] = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    REP["generated_class"] = C.safe(lambda: abp.generated_class().get_path_name())
    REP["status"] = "ok" if "UP_TO_DATE" in REP["compile"]["status"] and len(names) == 9 else "check"


try:
    main()
except Exception:  # noqa: BLE001
    REP["status"] = "error"
    REP["errors"].append(traceback.format_exc()[-3000:])
REP["hashes_after"] = C.all_hashes()
REP["exports_unchanged"] = REP["hashes_after"] == REP["hashes_before"]
dump()
unreal.log(f"SR_PASS_A3_DONE status={REP.get('status')}")
