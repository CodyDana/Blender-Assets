"""Heels Unreal check, step 2 (commandlet): build the foot-pose correction CR_HeelPose as a reusable Control Rig.

    /Game/HeelsCheck/CR_HeelPose     (Control Rig on metahuman_base_skel; hierarchy imported from HER body mesh, read only)

Implements WorkFiles/SnowFlowerHeels/HEEL_POSE.md section 4.3 per foot (component space, cm, deg), then pelvis + IK:
  H, B   = foot * barefoot heel / ball contact (bone-local constants)
  phi    = atan2(H.z - B.z, |B - H|xy) - RestInclineDeg          (the clip's own heel lift)
  delta  = HeelAlpha * softmax0(HeelPitchDeg - phi)               (softmax0(x) = (x + sqrt(x^2 + s^2)) / 2, s = SoftClampDeg)
  a      = unit(up x unit(foot axis xy));  Q = quat(a, delta)      (foot axis = foot rotation * the Study's forward axis)
  foot'  = Q * foot rotation, translation B + Q (foot.t - B) + (0, 0, HeelAlpha * BallLiftCm)
  ball'  = rotation quat(a, -HeelAlpha * ToeSpringDeg) * animated ball rotation (toes stay level + toe spring),
           translation B + Q (ball.t - B) + lift
  floor clamp, weight g = 1 - clamp((min(H.z, B.z) - GroundedCm) / (GroundedFadeCm - GroundedCm), 0, 1):
           dz = (min(H.z,B.z) - min(shoe heel tip.z, shoe ball sole.z)) * g * HeelAlpha, added to foot' and ball'
  pelvis = min over grounded feet (g > 0.5) of A'.z - hip.z + sqrt(L^2 - |A' - hip|xy^2)   (L = animated hip->ankle)
           no grounded foot -> hold; clamp [0, MaxPelvisLiftCm]; smoothed toward it with PelvisSmoothTime (0 = off)
  then pelvis up, two-bone IK thigh/calf -> foot' (pole = animated knee + lift + 30 cm along the foot), set foot', ball'.
Public variables (pins on the AnimGraph Control Rig node): HeelAlpha (0 barefoot .. 1 heels) and the tuning constants.

Self-test: an instance of the rig runs Forward Solve on her REST pose (the pose the Study solved) and the result is compared
with heel_pose.json (foot pitch, pelvis lift, ankle position, shoe heel tip / ball sole on the floor).
Writes WorkFiles/SnowFlowerHeels/ue/build_cr.json.
"""
import json
import math
import traceback

import unreal

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
UE = ROOT + "/WorkFiles/SnowFlowerHeels/ue"
POSE = json.load(open(ROOT + "/WorkFiles/SnowFlowerHeels/heel_pose.json", encoding="utf-8"))
SIDECAR = json.load(open(ROOT + "/Exports/SnowFlowerHeels/SK_SnowFlowerHeels.garment.json", encoding="utf-8"))
ASSET = "/Game/HeelsCheck/CR_HeelPose"
BODY = "/Game/MetaHumans/MH_PlayerFemale/Body/SKM_MH_PlayerFemale_BodyMesh"
S_CR = "/Script/ControlRig."
S_VM = "/Script/RigVM."
rep = {"asset": ASSET, "status": "failed", "errors": [], "link_failures": [], "default_failures": []}

VARS = [  # name, default, public
    ("HeelAlpha", 1.0, True), ("HeelPitchDeg", 33.67, True), ("BallLiftCm", 0.745, True), ("ToeSpringDeg", 3.0, True),
    ("RestInclineDeg", 0.207, True), ("SoftClampDeg", 1.0, True), ("GroundedCm", 2.0, True), ("GroundedFadeCm", 4.0, True),
    ("MaxPelvisLiftCm", 7.10, True), ("PelvisSmoothTime", 0.1, True), ("PelvisLift", 0.0, False)]
tip_l = SIDECAR["heel_tip_floor_in_foot_l_ue_cm"]
CONST = {}
for s in ("l", "r"):
    c = POSE["ue_contacts_local_cm"][s]
    CONST[s] = {"heel": c["barefoot_heel_contact_in_foot_cm"], "ballc": c["barefoot_ball_contact_in_foot_cm"],
                "sole": c["shoe_ball_sole_floor_in_ball_cm"],
                "tip": tip_l if s == "l" else [-tip_l[0], -tip_l[1], -tip_l[2]]}
AXES = {"l": {"primary": (-1, 0, 0), "secondary": (0, 1, 0)}, "r": {"primary": (1, 0, 0), "secondary": (0, -1, 0)}}
rep["constants"] = CONST


def vec(v):
    return "(X=%.6f,Y=%.6f,Z=%.6f)" % tuple(v)


def key(bone):
    return '(Type=Bone,Name="%s")' % bone


class Graph:
    def __init__(self, ctrl):
        self.c = ctrl
        self.n = 0
        self.y = 0

    def unit(self, struct, name, defaults=None, x=0):
        path = (S_CR if struct.startswith("RigUnit") else S_VM) + struct
        self.y += 1
        node = self.c.add_unit_node_from_struct_path(path, "Execute", unreal.Vector2D(x, (self.y % 60) * 120), name)
        if node is None:
            raise RuntimeError("could not add %s as %s" % (struct, name))
        for pin, value in (defaults or {}).items():
            self.default(name + "." + pin, value)
        return name

    def default(self, pin, value):
        if isinstance(value, bool):
            value = "True" if value else "False"
        elif isinstance(value, (int, float)):
            value = "%.8f" % value
        ok = self.c.set_pin_default_value(pin, value, True, False, False)
        if ok is False:
            rep["default_failures"].append([pin, value])

    def link(self, src, dst):
        ok = self.c.add_link(src, dst)
        if not ok:
            rep["link_failures"].append([src, dst])
        return ok

    def fed(self, dst, src):
        """src is a pin path (str) or a literal."""
        if isinstance(src, str):
            self.link(src, dst)
        else:
            self.default(dst, src)

    def auto(self, prefix):
        self.n += 1
        return "%s_%03d" % (prefix, self.n)

    # float ops ---------------------------------------------------------------------------------------------------
    def f2(self, op, a, b, x=0):
        n = self.unit("RigVMFunction_MathFloat" + op, self.auto("F" + op), x=x)
        self.fed(n + ".A", a)
        self.fed(n + ".B", b)
        return n + ".Result"

    def f1(self, op, v, x=0):
        n = self.unit("RigVMFunction_MathFloat" + op, self.auto("F" + op), x=x)
        self.fed(n + ".Value", v)
        return n + ".Result"

    def clamp(self, v, lo, hi, x=0):
        n = self.unit("RigVMFunction_MathFloatClamp", self.auto("FClamp"), x=x)
        self.fed(n + ".Value", v)
        self.fed(n + ".Minimum", lo)
        self.fed(n + ".Maximum", hi)
        return n + ".Result"

    def lerp(self, a, b, t, x=0):
        n = self.unit("RigVMFunction_MathFloatLerp", self.auto("FLerp"), x=x)
        self.fed(n + ".A", a)
        self.fed(n + ".B", b)
        self.fed(n + ".T", t)
        return n + ".Result"

    def atan2(self, y_, x_, x=0):
        n = self.unit("RigVMFunction_MathFloatAtan2", self.auto("FAtan2"), x=x)
        self.fed(n + ".A", y_)
        self.fed(n + ".B", x_)
        return n + ".Result"

    # vector ops --------------------------------------------------------------------------------------------------
    def v2(self, op, a, b, x=0):
        n = self.unit("RigVMFunction_MathVector" + op, self.auto("V" + op), x=x)
        for pin, src in (("A", a), ("B", b)):
            if isinstance(src, str):
                self.link(src, n + "." + pin)
            else:
                self.default(n + "." + pin, vec(src))
        return n + ".Result"

    def v1(self, op, v, x=0):
        n = self.unit("RigVMFunction_MathVector" + op, self.auto("V" + op), x=x)
        self.link(v, n + ".Value")
        return n + ".Result"

    def vmake(self, x_, y_, z_, x=0):
        n = self.unit("RigVMFunction_MathVectorMake", self.auto("VMake"), x=x)
        self.fed(n + ".X", x_)
        self.fed(n + ".Y", y_)
        self.fed(n + ".Z", z_)
        return n + ".Result"

    def vscale(self, v, f, x=0):
        n = self.unit("RigVMFunction_MathVectorScale", self.auto("VScale"), x=x)
        self.link(v, n + ".Value")
        self.fed(n + ".Factor", f)
        return n + ".Result"

    def ttv(self, transform, local, x=0):
        n = self.unit("RigVMFunction_MathTransformTransformVector", self.auto("TTV"), x=x)
        self.link(transform, n + ".Transform")
        self.default(n + ".Location", vec(local))
        return n + ".Result"

    def qaxis(self, axis, angle_rad, x=0):
        n = self.unit("RigVMFunction_MathQuaternionFromAxisAndAngle", self.auto("QAxis"), x=x)
        self.link(axis, n + ".Axis")
        self.fed(n + ".Angle", angle_rad)
        return n + ".Result"

    def qmul(self, a, b, x=0):
        n = self.unit("RigVMFunction_MathQuaternionMul", self.auto("QMul"), x=x)
        self.link(a, n + ".A")
        self.link(b, n + ".B")
        return n + ".Result"

    def qrot(self, q, v, x=0):
        n = self.unit("RigVMFunction_MathQuaternionRotateVector", self.auto("QRot"), x=x)
        self.link(q, n + ".Transform")
        if isinstance(v, str):
            self.link(v, n + ".Vector")
        else:
            self.default(n + ".Vector", vec(v))
        return n + ".Result"

    def tmake(self, t, q, x=0):
        n = self.unit("RigVMFunction_MathTransformMake", self.auto("TMake"), x=x)
        self.link(t, n + ".Translation")
        self.link(q, n + ".Rotation")
        return n + ".Result"

    def get(self, bone, name, x=0):
        return self.unit("RigUnit_GetTransform", name, {"Item": key(bone), "Space": "GlobalSpace"}, x=x) + ".Transform"

    def var(self, name, cpp="float"):
        node = self.auto("Get_" + name)
        n = self.c.add_variable_node(name, cpp, None, True, "", unreal.Vector2D(-600, self.n * 40), node)
        if n is None:
            raise RuntimeError("variable getter %s failed" % name)
        return node + ".Value"


try:
    eal = unreal.EditorAssetLibrary
    if eal.does_asset_exist(ASSET):
        rep["deleted_old"] = eal.delete_asset(ASSET)
    cr = unreal.ControlRigBlueprintFactory.create_new_control_rig_asset(ASSET)
    body = unreal.load_asset(BODY)
    hc = cr.get_hierarchy_controller()
    keys = hc.import_bones_from_skeletal_mesh(body, "None", True, True, False, False)
    rep["bones_imported"] = len(keys)
    try:
        cr.set_preview_mesh(body, False)
    except Exception as exc:  # noqa: BLE001
        rep["preview_mesh"] = str(exc)
    for name, default, public in VARS:
        cr.add_member_variable(name, "float", public, False, "%.6f" % default)
    hier = cr.get_hierarchy()
    LOCAL_FWD = {}
    for s in ("l", "r"):
        fa = POSE["solve"]["per_foot"][s]["forward_axis"]           # Blender axes -> UE: y mirrored
        fw = unreal.Vector(fa[0], -fa[1], fa[2])
        rest_foot = hier.get_global_transform(unreal.RigElementKey(type=unreal.RigElementType.BONE, name="foot_" + s), True)
        lf = unreal.MathLibrary.inverse_transform_direction(rest_foot, fw)
        LOCAL_FWD[s] = (lf.x, lf.y, lf.z)
    rep["local_forward_in_foot"] = LOCAL_FWD
    ctrl = cr.get_controller_by_name("RigVMModel") or cr.get_controller()
    g = Graph(ctrl)
    g.unit("RigUnit_BeginExecution", "ForwardSolve", x=-1200)
    alpha = g.var("HeelAlpha")
    pitch = g.var("HeelPitchDeg")
    blift = g.var("BallLiftCm")
    toe = g.var("ToeSpringDeg")
    incl = g.var("RestInclineDeg")
    soft = g.var("SoftClampDeg")
    gfull = g.var("GroundedCm")
    gfade = g.var("GroundedFadeCm")
    maxlift = g.var("MaxPelvisLiftCm")
    tau = g.var("PelvisSmoothTime")
    last = g.var("PelvisLift")
    lift_v = g.vmake(0.0, 0.0, g.f2("Mul", alpha, blift))
    side = {}
    for s in ("l", "r"):
        k = CONST[s]
        F = g.get("foot_" + s, "Get_foot_" + s)
        Bb = g.get("ball_" + s, "Get_ball_" + s)
        T = g.get("thigh_" + s, "Get_thigh_" + s)
        C = g.get("calf_" + s, "Get_calf_" + s)
        H = g.ttv(F, k["heel"])
        B = g.ttv(F, k["ballc"])
        D = g.v2("Sub", B, H)
        horiz = g.vmake(D + ".X", D + ".Y", 0.0)
        run = g.v1("Length", horiz)
        # pitch axis = horizontal normal of the FOOT AXIS (the Study's solve axis, HEEL_POSE.md 4.1: foot_l about
        # (-0.98522, 0.17130, 0)), taken from the animated foot orientation; the heel->ball contact line is 6 deg off it
        fdir = g.qrot(F + ".Rotation", LOCAL_FWD[s])
        fwd = g.v1("Unit", g.vmake(fdir + ".X", fdir + ".Y", 0.0))
        phi = g.f1("Deg", g.atan2(g.f2("Sub", H + ".Z", B + ".Z"), run))
        x = g.f2("Sub", pitch, g.f2("Sub", phi, incl))
        smax = g.f2("Mul", 0.5, g.f2("Add", x, g.f1("Sqrt", g.f2("Add", g.f2("Mul", x, x), g.f2("Mul", soft, soft)))))
        delta = g.f2("Mul", alpha, smax)
        axis = g.v1("Unit", g.v2("Cross", (0.0, 0.0, 1.0), fwd))
        Q = g.qaxis(axis, g.f1("Rad", delta))
        frot = g.qmul(Q, F + ".Rotation")
        ft = g.v2("Add", g.v2("Add", B, g.qrot(Q, g.v2("Sub", F + ".Translation", B))), lift_v)
        bt = g.v2("Add", g.v2("Add", B, g.qrot(Q, g.v2("Sub", Bb + ".Translation", B))), lift_v)
        qt = g.qaxis(axis, g.f1("Rad", g.f2("Mul", g.f2("Mul", alpha, toe), -1.0)))
        brot = g.qmul(qt, Bb + ".Rotation")
        tip = g.v2("Add", ft, g.qrot(frot, k["tip"]))
        sole = g.v2("Add", bt, g.qrot(brot, k["sole"]))
        low = g.f2("Min", tip + ".Z", sole + ".Z")
        contact = g.f2("Min", H + ".Z", B + ".Z")
        gw = g.f2("Sub", 1.0, g.clamp(g.f2("Div", g.f2("Sub", contact, gfull), g.f2("Max", g.f2("Sub", gfade, gfull), 0.001)), 0.0, 1.0))
        dzc = g.f2("Mul", g.f2("Mul", g.f2("Sub", contact, low), gw), alpha)
        dzv = g.vmake(0.0, 0.0, dzc)
        ft2 = g.v2("Add", ft, dzv)
        bt2 = g.v2("Add", bt, dzv)
        hip = T + ".Translation"
        L = g.v1("Length", g.v2("Sub", F + ".Translation", hip))
        dA = g.v2("Sub", ft2, hip)
        hor2 = g.f2("Add", g.f2("Mul", dA + ".X", dA + ".X"), g.f2("Mul", dA + ".Y", dA + ".Y"))
        inside = g.f2("Max", g.f2("Sub", g.f2("Mul", L, L), hor2), 0.0)
        lift_s = g.f2("Add", dA + ".Z", g.f1("Sqrt", inside))
        notg = g.f2("Sub", 1.0, g.clamp(g.f2("Mul", g.f2("Sub", gw, 0.5), 1000.0), 0.0, 1.0))
        eff = g.f2("Add", lift_s, g.f2("Mul", notg, 1000.0))
        side[s] = {"F": F, "C": C, "fwd": fwd, "frot": frot, "ft": ft2, "brot": brot, "bt": bt2, "eff": eff}
    raw = g.f2("Min", side["l"]["eff"], side["r"]["eff"])
    hold = g.clamp(g.f2("Mul", g.f2("Sub", raw, 500.0), 1000.0), 0.0, 1.0)
    target = g.clamp(g.lerp(raw, last, hold), 0.0, maxlift)
    dt = g.unit("RigVMFunction_GetDeltaTime", "DeltaTime") + ".Result"
    a_s = g.clamp(g.f2("Div", g.f2("Max", dt, 0.0001), g.f2("Max", tau, 0.000001)), 0.0, 1.0)
    new = g.lerp(last, target, a_s)
    # execution chain
    setvar = ctrl.add_variable_node("PelvisLift", "float", None, False, "", unreal.Vector2D(1200, 0), "Set_PelvisLift")
    g.link(new, "Set_PelvisLift.Value")
    chain = ["ForwardSolve", "Set_PelvisLift"]
    gp = g.get("pelvis", "Get_pelvis")
    g.unit("RigUnit_SetTranslation", "Set_pelvis", {"Item": key("pelvis"), "Space": "GlobalSpace", "bPropagateToChildren": True}, x=1500)
    g.link(g.v2("Add", gp + ".Translation", g.vmake(0.0, 0.0, new)), "Set_pelvis.Value")
    chain.append("Set_pelvis")
    for s in ("l", "r"):
        d = side[s]
        n = g.unit("RigUnit_TwoBoneIKSimplePerItem", "IK_leg_" + s, {
            "ItemA": key("thigh_" + s), "ItemB": key("calf_" + s), "EffectorItem": key("foot_" + s),
            "PrimaryAxis": vec(AXES[s]["primary"]), "SecondaryAxis": vec(AXES[s]["secondary"]),
            "PoleVectorKind": "Location", "bPropagateToChildren": True}, x=1800)
        g.link(g.tmake(d["ft"], d["frot"]), n + ".Effector")
        pole = g.v2("Add", g.v2("Add", d["C"] + ".Translation", g.vmake(0.0, 0.0, new)), g.vscale(d["fwd"], 30.0))
        g.link(pole, n + ".PoleVector")
        chain.append(n)
    for s in ("l", "r"):
        d = side[s]
        g.unit("RigUnit_SetTransform", "Set_foot_" + s, {"Item": key("foot_" + s), "Space": "GlobalSpace", "bPropagateToChildren": True}, x=2100)
        g.link(g.tmake(d["ft"], d["frot"]), "Set_foot_%s.Value" % s)
        g.unit("RigUnit_SetTransform", "Set_ball_" + s, {"Item": key("ball_" + s), "Space": "GlobalSpace", "bPropagateToChildren": True}, x=2400)
        g.link(g.tmake(d["bt"], d["brot"]), "Set_ball_%s.Value" % s)
        chain += ["Set_foot_" + s, "Set_ball_" + s]
    for a, b in zip(chain, chain[1:]):
        g.link(a + ".ExecutePin", b + ".ExecutePin")
    rep["nodes"] = len(ctrl.get_graph().get_nodes())
    rep["exec_chain"] = chain
    cr.recompile_vm()
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(cr)
    except Exception as exc:  # noqa: BLE001
        rep["compile_blueprint"] = str(exc)
    try:
        rep["status_after_compile"] = str(cr.get_editor_property("status"))
    except Exception as exc:  # noqa: BLE001
        rep["status_after_compile"] = "n/a " + str(exc)[:100]
    rep["saved"] = eal.save_asset(ASSET, only_if_is_dirty=False)
    # ------------------------------------------------------------------------------------ self-test on her rest pose
    test = {}
    inst = cr.create_control_rig()
    rep["events"] = [str(e) for e in inst.get_supported_events()]
    h = inst.get_hierarchy()
    h.reset_pose_to_initial(unreal.RigElementType.BONE)

    def gt(bone, initial=False):
        return h.get_global_transform(unreal.RigElementKey(type=unreal.RigElementType.BONE, name=bone), initial)

    def qang(a, b):
        return math.degrees(2 * math.acos(min(1.0, abs(a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w))))

    rest = {b: gt(b, True) for b in ("pelvis", "foot_l", "foot_r", "ball_l", "ball_r", "calf_l")}
    inst.set_variable_from_string("PelvisSmoothTime", "0.0")
    inst.set_delta_time(1.0 / 30.0)
    ev = "Forward Solve" if "Forward Solve" in rep["events"] else rep["events"][0]
    runs = []
    for i in range(3):
        runs.append(inst.execute(ev))
        if i < 2:
            h.reset_pose_to_initial(unreal.RigElementType.BONE)
    test["execute_returns"] = [str(r) for r in runs]
    test["pelvis_lift_var"] = inst.get_variable_as_string("PelvisLift")
    post = {b: gt(b) for b in ("pelvis", "foot_l", "foot_r", "ball_l", "ball_r", "calf_l", "thigh_l")}
    test["pelvis_dz_cm"] = post["pelvis"].translation.z - rest["pelvis"].translation.z
    for s in ("l", "r"):
        k = CONST[s]
        fr, fp = rest["foot_" + s], post["foot_" + s]
        ang = qang(fp.rotation, fr.rotation)
        ank_bl = POSE["solve"]["per_foot"][s]["posed_ankle_head_m"]
        exp = unreal.Vector(ank_bl[0] * 100, -ank_bl[1] * 100, ank_bl[2] * 100)
        tip = fp.transform_location(unreal.Vector(*k["tip"]))
        sole = post["ball_" + s].transform_location(unreal.Vector(*k["sole"]))
        test[s] = {"foot_rotation_deg": ang, "ankle_cm": [fp.translation.x, fp.translation.y, fp.translation.z],
                   "ankle_expected_cm": [exp.x, exp.y, exp.z], "ankle_error_mm": (fp.translation - exp).length() * 10,
                   "shoe_heel_tip_z_mm": tip.z * 10, "shoe_ball_sole_z_mm": sole.z * 10,
                   "ball_component_rotation_deg": qang(post["ball_" + s].rotation, rest["ball_" + s].rotation)}
    test["expected"] = {"foot_pitch_deg": 33.6693, "pelvis_lift_cm": 7.0996,
                        "note": "soft clamp adds ~0.007 deg; heel tip is the built top-lift (README), ball sole from heel_pose.json"}
    rep["self_test"] = test
    rep["status"] = "ok"
except Exception:  # noqa: BLE001
    rep["errors"].append(traceback.format_exc())
finally:
    with open(UE + "/build_cr.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
    unreal.log("[hc_build_cr] status " + rep["status"])
