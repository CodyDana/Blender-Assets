"""SR01 W5: the verification summary (plain Python + numpy + PIL). Reads every pass record of this harness and writes
WorkFiles/guns/sniper/UnrealCheck/verification_summary.json with one row per SR01_BUILD_PLAN W5 gate (U1-U12, U2b, U4 with
the scope pair, U5 bounds over every clip incl. BipodDeploy, the bipod poses, C2, M9, triangles equal) plus the byte guards (name, value, threshold, pass). "engine_verified" only when the bytes every
pass used are the shipped bytes and the bytes the W3 gates recorded (rig_export.json, mag.json M7).

    py -3 -B WorkFiles/guns/sniper/UnrealCheck/srF_summary.py
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sr_common as C  # noqa: E402


def j(name):
    p = HERE / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


A, A2, A3, B, CR, D, E = (j(n) for n in ("srA_import.json", "srA2_level.json", "srA3_abp.json", "srB_verify.json",
                                         "srC_render.json", "srD_analysis.json", "srE_game.json"))
START = j("SHA256_at_start.json")
SC = C.sidecar_sk()
gates, issues, findings = [], [], []


def gate(name, value, threshold, ok, note=None, kind="gate"):
    g = {"name": name, "value": value, "threshold": threshold, "pass": bool(ok)}
    if note:
        g["note"] = note
    if kind != "gate":
        g["kind"] = kind
    gates.append(g)
    return ok


def quat_m(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def rotvec(R):
    """axis * angle (deg) of a rotation matrix (Unreal component numbers; about +Y the numbers equal Blender's rot_y)."""
    ang = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2))))
    ax = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    n = np.linalg.norm(ax)
    return (ax / n * ang) if n > 1e-12 else np.zeros(3)


def delta(case_T, bind_T):
    Rc, Rb = quat_m(case_T[3:7]), quat_m(bind_T[3:7])
    return Rc @ Rb.T, np.array(case_T[:3]) - np.array(bind_T[:3])


# ---------------------------------------------------------------- bytes
now = C.all_hashes()
same = {k: (r or {}).get("hashes_before") == START and (r or {}).get("hashes_after") == START
        for k, r in (("A", A), ("A2", A2), ("A3", A3), ("B", B), ("C", CR))}
gate("bytes: every pass used the shipped bytes (sha256 of every Exports/Guns/SR01 file before and after passes A, A2, A3, B, C)",
     {"files": len(START), "unchanged_per_pass": same, "now_equal_start": now == START}, "all equal",
     all(same.values()) and now == START)
rx = json.loads((C.GATES / "rig_export.json").read_text())
rec = {f.split("Exports/Guns/SR01/")[-1]: v for f, v in rx["sha256"].items()}
mism = [k for k, v in rec.items() if START.get(k) != v]
mag = json.loads((C.GATES / "mag.json").read_text())
m7 = next(g for g in mag["gates"] if g["name"].startswith("M7"))["value"]
sx = json.loads((C.GATES / "scope_export.json").read_text())["files"]
smis = [k for k, v in sx.items() if START.get(k.split("Exports/Guns/SR01/")[-1]) != v["sha256"]]
gate("bytes = the W4b gated bytes (rig_export.json sha256, mag.json M7, scope_export.json files)",
     {"rig_export_files": len(rec), "mismatch": mism, "SM_SR01.fbx": START["SM_SR01.fbx"] == m7.get("rifle"),
      "SM_SR01_Mag.fbx": START["SM_SR01_Mag.fbx"] == m7.get("mag"), "scope_files": len(sx), "scope_mismatch": smis},
     "equal", not mism and not smis and START["SM_SR01.fbx"] == m7.get("rifle") and START["SM_SR01_Mag.fbx"] == m7.get("mag"))

# ---------------------------------------------------------------- import
gate("pass A import (fresh process; legacy FBX importer, the sidecar settings; SK_AR01_Skeleton set compatible)",
     {"status": A["status"], "lods_SK": A["lod_count_after_import"], "clips": len(A["steps"]["animations"]),
      "sockets_SK": len(A["steps"]["sockets"]) if isinstance(A["steps"]["sockets"], list) else A["steps"]["sockets"],
      "physics": A["steps"]["physics"].get("asset") if isinstance(A["steps"]["physics"], dict) else None,
      "physics_elements": A["steps"]["physics"].get("elements_written") if isinstance(A["steps"]["physics"], dict) else None,
      "textures": len(A["textures"]), "compatible_skeletons": A.get("compatible_skeletons")},
     "ok; 4 LODs; 8 clips; 20 sockets", A["status"] == "ok" and A["lod_count_after_import"] == 4 and len(A["steps"]["animations"]) == 8
     and any("SK_AR01_Skeleton" in s for s in A.get("compatible_skeletons", [])))

# ---------------------------------------------------------------- U1 / U2 / U3
u1 = D["U1"]
gate("U1 skeleton: names, parents, reference heads (<= 0.001 cm), root scale 1, rest rotations 0, axes (muzzle +X, up +Z, "
     "port right +Y)", {k: u1[k] for k in ("mesh_bones", "names_match", "parents_match", "max_head_err_cm", "root_scale_1",
                                           "max_bone_rest_rotation_deg", "axes")}, "all true; head err <= 0.001 cm", u1["pass"])
u2 = B["U2"]
bolt = u2["bolt_back_full"]
dv = np.array(bolt["got_component"][:3]) - np.array(bolt["ref_component"][:3])
sel = {}
for k in ("selector_SAFE", "selector_FIRE"):
    r = u2[k]
    rv = rotvec(quat_m(r["got_component"][3:7]))
    sel[k] = {"blender_deg_commanded": r["blender_deg"], "about_Y_deg": round(float(rv[1]), 5),
              "off_axis_deg": round(float(abs(rv[0]) + abs(rv[2])), 6),
              "head_moved_cm": float(np.abs(np.array(r["got_component"][:3]) - np.array(r["ref_component"][:3])).max())}
br = u2["bolt_rotated"]
rvb = rotvec(quat_m(br["got_component"][3:7]))
bolt_rot = {"blender_deg_commanded": br["blender_deg"], "about_X_deg": round(float(rvb[0]), 5),
            "off_axis_deg": round(float(abs(rvb[1]) + abs(rvb[2])), 6),
            "head_moved_cm": float(np.abs(np.array(br["got_component"][:3]) - np.array(br["ref_component"][:3])).max())}
ok2 = (np.abs(dv - [bolt["commanded_cm"], 0, 0]).max() <= 1e-3
       and abs(bolt_rot["about_X_deg"] + br["blender_deg"]) <= 1e-3 and bolt_rot["off_axis_deg"] < 1e-4 and bolt_rot["head_moved_cm"] < 1e-6
       and all(abs(v["about_Y_deg"] - v["blender_deg_commanded"]) <= 1e-3 and v["off_axis_deg"] < 1e-4 and v["head_moved_cm"] < 1e-6
               for v in sel.values()))
gate("U2 procedural (engine pose maths, bone-space offsets): the bolt's -X moves it straight back by the full travel; the "
     "bolt turns -60 deg about its own X (Unreal numbers +60: Y mirrored); the selector turns about its own Y to SAFE / FIRE",
     {"bolt_component_motion_cm": dv.round(6).tolist(), "bolt_rotation": bolt_rot, "selector": sel},
     "bolt (-8.8, 0, 0) +- 0.001 cm; bolt about X, angle +- 0.001 deg, pivot fixed; selector about Y, angle +- 0.001 deg", ok2)

# ---------------------------------------------------------------- U2b
U = CR["U2b"]
heads = {"SR01": {n: v["head_cm"] for n, v in SC["bones_rest"].items()},
         "AR01": {n: v["head_cm"] for n, v in C.sidecar_ar()["bones_rest"].items()}}
SOCK_ON = {"SR01": {"trigger": "Trigger", "selector": "Selector", "mag_release": "MagRelease"},
           "AR01": {"trigger": "Trigger", "selector": "Selector", "mag_release": "MagRelease"}}
u2b, ok2b = {}, True
for gun, g in U["guns"].items():
    t = U["tables"][gun]
    cs = g["cases"]
    bind = cs["rest"]
    so = SOCK_ON[gun]
    r = {"anim_instance_every_case": all(c["anim_instance"] for c in cs.values()), "skeleton": g["skeleton"]}

    def rot_case(case, bone):
        Rd, _ = delta(cs[case]["sockets"][so[bone]], bind["sockets"][so[bone]])
        return Rd, rotvec(Rd)
    # bolt
    b1 = np.array(cs["bolt_1"]["bones"]["bolt"][:3]) - np.array(bind["bones"]["bolt"][:3])
    b05 = np.array(cs["bolt_05"]["bones"]["bolt"][:3]) - np.array(bind["bones"]["bolt"][:3])
    fire = g["clip_reference"][f"A_{gun}_Fire"]["frames"]
    if gun == "SR01":
        # the bolt action: rotate -60 about X, then slide 8.8 cm (= A_SR01_BoltCycle frame 15, open and back)
        bc = g["clip_reference"]["A_SR01_BoltCycle"]["frames"]
        ob = cs["bolt_open_back"]["bones"]["bolt"]
        cf = bc["15"]["bones"]["bolt"]
        rot1 = rotvec(delta(cs["boltrot_1"]["bones"]["bolt"], bind["bones"]["bolt"])[0])
        d_loc = float(np.abs(np.array(ob[:3]) - np.array(cf[:3])).max())
        d_ang = float(np.linalg.norm(rotvec(quat_m(ob[3:7]) @ quat_m(cf[3:7]).T)))
        r["bolt"] = {"full_cm": b1.round(5).tolist(), "half_cm": b05.round(5).tolist(), "rot_about_X_deg_unreal": rot1.round(5).tolist(),
                     "open_back_vs_BoltCycle_f15_cm": round(d_loc, 6), "open_back_vs_BoltCycle_f15_deg": round(d_ang, 6),
                     "ok": bool(np.abs(b1 - [-t["bolt_cm"], 0, 0]).max() <= 0.01 and np.abs(b05 - [-t["bolt_cm"] / 2, 0, 0]).max() <= 0.01
                                and abs(rot1[0] + t["bolt_rot_deg"]) <= 0.01 and d_loc <= 0.01 and d_ang <= 0.01)}
    else:
        fb = [np.array(f["bones"]["bolt"][:3]) - np.array(fire["0"]["bones"]["bolt"][:3]) for f in fire.values()]
        rear = min(fb, key=lambda v: v[0])
        r["bolt"] = {"full_cm": b1.round(5).tolist(), "half_cm": b05.round(5).tolist(), "fire_clip_rear_stop_cm": rear.round(5).tolist(),
                     "ok": bool(np.abs(b1 - [-t["bolt_cm"], 0, 0]).max() <= 0.01 and np.abs(b05 - [-t["bolt_cm"] / 2, 0, 0]).max() <= 0.01
                                and np.abs(b1 - rear).max() <= 0.01)}
    # trigger: angle, axis, the lower end rearward, = the Fire clip's full pull
    Rt, rv = rot_case("trigger_1", "trigger")
    low = np.array(heads[gun]["trigger"]) + np.array([0, 0, -3.0])
    dx = float((Rt @ (low - np.array(heads[gun]["trigger"])) + np.array(heads[gun]["trigger"]) - low)[0])
    fr_t = [rotvec(delta(f["sockets"]["Trigger"], fire["0"]["sockets"]["Trigger"])[0])[1] for f in fire.values()]
    full = max(fr_t, key=abs)
    _, rv05 = rot_case("trigger_05", "trigger")
    r["trigger"] = {"about_Y_deg": round(float(rv[1]), 5), "half_deg": round(float(rv05[1]), 5), "off_axis_deg": round(float(abs(rv[0]) + abs(rv[2])), 6),
                    "point_3cm_below_pivot_dx_cm": round(dx, 5), "fire_clip_full_pull_deg": round(float(full), 5),
                    "ok": bool(abs(rv[1] - t["trigger_deg"]) <= 0.01 and abs(rv05[1] - t["trigger_deg"] / 2) <= 0.01 and dx < 0
                               and abs(rv[1] - full) <= 0.01 and abs(rv[0]) + abs(rv[2]) < 1e-3)}
    # selector detents (index 0 SAFE, 1 SEMI = the rest case, 2 AUTO)
    det = {}
    for case, idx in (("selector_SAFE", 0), ("rest", 1), ("selector_AUTO", 2)):
        Rs_ = quat_m(cs[case]["sockets"]["Selector"][3:7]) @ quat_m(g["bind"]["sockets"]["Selector"][3:7]).T
        det[["SAFE", "SEMI", "AUTO"][idx]] = round(float(rotvec(Rs_)[1]), 5)
    held = [rotvec(delta(f["sockets"]["Selector"], g["bind"]["sockets"]["Selector"])[0])[1] for f in fire.values()]
    clip_ref = {"AUTO_held_in_Fire": round(float(np.mean(held)), 5)}
    if gun == "SR01":
        sfr = g["clip_reference"]["A_SR01_Selector"]["frames"]
        sv = [rotvec(delta(f["sockets"]["Selector"], g["bind"]["sockets"]["Selector"])[0])[1] for f in sfr.values()]
        clip_ref.update({"SAFE_selector_clip_min": round(float(min(sv)), 5), "AUTO_selector_clip_max": round(float(max(sv)), 5),
                         "SEMI_bind": 0.0})
        ok_ref = abs(det["SAFE"] - min(sv)) <= 0.01 and abs(det["AUTO"] - max(sv)) <= 0.01 and abs(det["SEMI"]) <= 0.01
    else:
        clip_ref.update({"SAFE_bind": 0.0})
        ok_ref = abs(det["SAFE"]) <= 0.01
    r["selector"] = {"detents_about_Y_deg": det, "table": dict(zip(("SAFE", "SEMI", "AUTO"), t["selector_deg"])), "clips": clip_ref,
                     "ok": bool(all(abs(det[k] - v) <= 0.01 for k, v in zip(("SAFE", "SEMI", "AUTO"), t["selector_deg"]))
                                and abs(det["AUTO"] - clip_ref["AUTO_held_in_Fire"]) <= 0.01 and ok_ref)}
    # release: the gun's own way (= its Reload clip's extreme)
    _, rvr = rot_case("release_1", "mag_release")
    rl = g["clip_reference"][f"A_{gun}_Reload"]["frames"]
    rr = [rotvec(delta(f["sockets"]["MagRelease"], rl["0"]["sockets"]["MagRelease"])[0]) for f in rl.values()]
    ext = max(rr, key=lambda v: np.linalg.norm(v))
    r["release"] = {"rotvec_deg": rvr.round(5).tolist(), "reload_clip_extreme_rotvec_deg": ext.round(5).tolist(),
                    "same_way": bool(rvr @ ext > 0), "ok": bool(abs(rvr[1] - t["release_deg"]) <= 0.01 and rvr @ ext > 0
                                                                and np.abs(rvr - ext).max() <= 0.01)}
    # missing bone probe (cheek_riser): SR01 = the CheekRiser clip's +12 mm frame; AR = nothing moves
    if gun == "SR01":
        cr_ = g["clip_reference"]["A_SR01_CheekRiser"]["frames"]
        hi_ = max(cr_.values(), key=lambda f: f["bones"]["cheek_riser"][2])["bones"]["cheek_riser"]
        got = cs["riser_1"]["bones"]["cheek_riser"]
        dloc = float(np.abs(np.array(got[:3]) - np.array(hi_[:3])).max())
        rz = float(got[2] - bind["bones"]["cheek_riser"][2])
        r["riser"] = {"rise_cm": round(rz, 6), "vs_CheekRiser_top_cm": round(dloc, 6), "ok": bool(dloc <= 0.01 and abs(rz - t["riser_cm"]) <= 0.01)}
    else:
        moved = max(float(np.abs(np.array(cs["riser_1"]["bones"][b][:3]) - np.array(bind["bones"][b][:3])).max()) for b in g["bones"])
        moved_s = max(float(np.abs(np.array(cs["riser_1"]["sockets"][s][:7]) - np.array(bind["sockets"][s][:7])).max()) for s in bind["sockets"])
        rot_ = max(float(np.abs(np.array(cs["boltrot_1"]["bones"][b][:7]) - np.array(bind["bones"][b][:7])).max()) for b in g["bones"])
        r["riser"] = {"missing_bone": "cheek_riser", "max_bone_motion_cm": moved, "max_socket_change": moved_s,
                      "bolt_rot_case_motion (table 0)": rot_, "ok": bool(moved < 1e-6 and moved_s < 1e-6 and rot_ < 1e-6)}
    # rest: the bind pose except the SEMI detent (AR-01: 32 deg)
    rest_dev = {}
    for b in g["bones"]:
        dd = float(np.abs(np.array(bind["bones"][b][:7]) - np.array(g["bind"]["bones"][b][:7])).max())
        if dd > 1e-6:
            rest_dev[b] = round(dd, 6)
    r["rest_vs_bind"] = rest_dev
    r["rest_ok"] = set(rest_dev) <= ({"selector"} if gun == "AR01" else set())
    r["ok"] = all(r[k]["ok"] for k in ("bolt", "trigger", "selector", "release", "riser")) and r["rest_ok"] and r["anim_instance_every_case"]
    ok2b &= r["ok"]
    u2b[gun] = r
clog = (HERE / "srC_render.log").read_text(errors="ignore")
rt_err = sorted({l.strip()[:200] for l in clog.splitlines() if re.search(r"(Warning|Error):", l) and re.search(r"ABP_Gun|cheek_riser|AnimInstance|Anim", l)
                 and "DeprecationWarning" not in l})
abp_compile = sorted({l.strip()[-140:] for l in (HERE / "srA3_abp.log").read_text(errors="ignore").splitlines()
                      if "ABP_Gun_LongGun" in l and re.search(r"(Warning|Error):", l)})
u2b["runtime_log_lines_about_the_ABP_or_riser"] = rt_err
u2b["compile"] = {"status": A3["compile"]["status"], "chain": A3["chain_from_output"], "log": abp_compile}
gate("U2b one ABP (ABP_Gun_LongGun, authored on SK_AR01_Skeleton) drives SK_SR01 (Compatible Skeletons) and SK_AR01 through "
     "normalized inputs mapped by each gun's angle table: the sniper's bolt turns -60 deg and slides 8.8 cm (= A_SR01_BoltCycle open "
     "and back), the AR-01's slides its table travel (= its Fire clip's rear stop); both triggers pull their lower end rearward by "
     "the table angle (= each Fire clip's full pull); the detent index reaches each gun's SAFE / fire detents (= its own clips); each "
     "release moves its own way (= its Reload clip); the sniper-only cheek_riser rises 1.2 cm (= A_SR01_CheekRiser's top) and does "
     "nothing on SK_AR01", u2b, "0.01 cm / 0.01 deg on both guns; no runtime error lines", ok2b and not rt_err,
     "SR01's skeleton is compatible by design for the shared bones (bolt, trigger, selector, mag_release, magazine, "
     "muzzle_device); its bipod / riser bones are sniper-only and are driven by its own clips (or ABP nodes that do nothing on "
     "other guns: the cheek_riser node here)")
issues.append("U2b: nodes on sniper-only bones (cheek_riser; the bipod bones the same way) compile with a 'bone not found' warning "
              "because the class ABP is authored on the AR-01 pilot skeleton (as the SMG's stock node did); no runtime error. The "
              "bolt's roll node needs NO Invert Rotator (about X the Blender and Unreal numbers agree; about Y / Z they flip). The "
              "game's DemoGame_1_Guns ABP_Gun_LongGun has neither the table nor a bolt-rotation input yet (prototype work, not done here).")
u3 = D["U3"]
gate("U3 sockets on SK_SR01: from the sidecar, on the right bones, scale 1, outered to the asset, fresh process",
     {"count": len(u3["sockets"]), "worst_loc_cm": u3["worst_loc_cm"], "worst_rot_deg": u3["worst_rot_deg"], "extra": u3["extra"]},
     "20; <= 0.001 cm / 0.001 deg; no extras", u3["pass"] and len(u3["sockets"]) == 20)
for nm, n_exp in (("SM_SR01", 20), ("SM_SR01_Mag", 5), (C.SCOPE, 5)):
    r = B[nm]
    sc = r["sidecar_compare"]
    vals = [v for v in sc.values() if isinstance(v, dict)]
    gate(f"sockets on {nm} (sidecar, fresh process)", {"count": len(r["sockets"]), "worst_loc_cm": max(v["max_loc_err_cm"] for v in vals),
                                                     "worst_rot_deg": max(v["max_rot_err_deg"] for v in vals),
                                                     "extra": r["sidecar_extra_sockets"], "missing": [k for k, v in sc.items() if not isinstance(v, dict)]},
         f"{n_exp}; <= 0.001 cm / 0.001 deg; scale 1; outer = asset; no extras",
         len(vals) == n_exp and not r["sidecar_extra_sockets"] and all(v["max_loc_err_cm"] <= 1e-3 and v["max_rot_err_deg"] <= 1e-3
                                                                       and v["scale1"] and v["outer_is_asset"] for v in vals))

# ---------------------------------------------------------------- U4 first person
u4 = CR.get("U4", {})
try:
    from PIL import Image
    rd = HERE / "renders"
    L = lambda n: np.asarray(Image.open(rd / f"{n}.png").convert("RGB")).astype(float).mean(2)  # noqa: E731
    G, M = L("u4_ground_only"), L("u4_tp_noshadow")
    gun_mask = np.abs(M - G) > 6
    shadow = {n: int(((L(n) - G < -0.25 * np.maximum(G, 1)) & ~gun_mask).sum()) for n in ("u4_tp", "u4_none", "u4_fp")}
    I = {n: np.asarray(Image.open(rd / f"u4_lod_{n}.png").convert("RGB")).astype(float) for n in ("ref0", "ref3", "tp_auto", "fp_forced")}
    dpx = lambda a, b: int((np.abs(I[a] - I[b]).sum(2) > 30).sum())  # noqa: E731
    lodt = {"tp_auto_vs_ref0": dpx("tp_auto", "ref0"), "tp_auto_vs_ref3": dpx("tp_auto", "ref3"),
            "fp_forced_vs_ref0": dpx("fp_forced", "ref0"), "fp_forced_vs_ref3": dpx("fp_forced", "ref3")}
except Exception as e:  # noqa: BLE001
    shadow, lodt = {"error": str(e)}, {}
ok4 = (isinstance(shadow.get("u4_tp"), int) and shadow["u4_tp"] > 1000 and shadow["u4_fp"] < 0.01 * shadow["u4_tp"]
       and lodt and lodt["fp_forced_vs_ref0"] < lodt["fp_forced_vs_ref3"] and lodt["tp_auto_vs_ref3"] < lodt["tp_auto_vs_ref0"])
gate("U4 First Person rendering with VSM (FP_Weapon + FP_Mag + FP_Scope vs TP_Weapon + TP_Mag + TP_Scope): FP casts no ground shadow, TP does; FP at "
     "ForcedLodModel 1 renders LOD0 where the auto-LOD TP component falls to LOD3", {"ground_shadow_px": shadow, "lod_pixels_differing": lodt,
     "components": {k: v for k, v in u4.get("shots", {}).items() if isinstance(v, dict)}},
     "TP shadow > 1000 px, FP < 1 % of it; FP closer to the LOD0 reference, TP to LOD3", ok4,
     "'the owner sees no TP component' needs a possessed player pawn carrying both components (game-side weapon Blueprint); "
     "not measurable here (same as the AR-01)")
issues.append("U4: 'owner sees no TP component' is not measured (needs the weapon Blueprint on a possessed pawn: game-side, as on the AR-01).")
sp = D["U4_scope_pair"]
okp = True
for k in ("SM_SR01 (pass B)", "SK_SR01 (pass C)"):
    v = sp[k]
    if "error" in v:
        okp = False
        continue
    okp &= (v["mount_err_cm"] <= 1e-3 and v["attach_socket"] == "Rail_Top" and all(abs(x - 1) < 1e-6 for x in v["scale"])
            and all(v[sn]["vs_blender_cm"] <= 1e-3 and abs(v[sn]["lateral_mm"]) <= 0.01 and v[sn]["axis_vs_bore_deg"] <= 0.01
                    for sn in ("Sight", "EyePoint", "Lens_Front"))
            and abs(v["Sight"]["above_bore_mm"] - 57.6) <= 0.2 and v["bore_dir_sockets_vs_muzzle_axis_deg"] <= 0.01)
sv = CR.get("scope_view") or {}
okv = bool(sv) and abs(sv["bore_drop_below_sight_line_cm"] - 5.76) <= 0.02 and abs(sv["bore_lateral_cm"]) <= 0.01
gate("U4 scope pair: SM_Att_Scope_LongRange's Mount attached at Rail_Top (+2 slots, X +20.02 mm) on SM_SR01 and on SK_SR01 lands "
     "where Blender says (A1); Sight / EyePoint / Lens_Front on one line parallel to the bore, 57.6 mm above it (A4), centred; "
     "scope view: the bore's 10 m point sits 5.76 cm under the sight line (parallel lines)",
     {"pairs": sp, "scope_view": sv}, "mount <= 0.001 cm; sockets = Blender <= 0.001 cm; 57.6 +- 0.2 mm; axes <= 0.01 deg; "
     "scope-view drop 5.76 +- 0.02 cm", okp and okv)
bpz = D["bipod_poses"]
okb = True
for st in ("deploy_last", "stow_first"):
    for sd in ("l", "r"):
        v = bpz[st][sd]
        okb &= (v["rotation_vs_build_deg"] <= 0.01 and abs(v["swing_from_forward_deg"] - 90) <= 0.01 and abs(v["splay_deg"] - 12) <= 0.01
                and v["leans"] == "out" and abs(v["ext_travel_cm"][0] - v["ext_expected_cm"]) <= 1e-3
                and max(abs(v["ext_travel_cm"][1]), abs(v["ext_travel_cm"][2])) <= 1e-3)
for sd in ("l", "r"):
    okb &= bpz["deploy_last"][sd]["foot_vs_build_cm"] <= 0.01
okb &= max(bpz["stow_last"].values()) <= 1e-3
gate("bipod poses read back (runtime, compressed): BipodDeploy's end and BipodStow's start = legs +90 about the 12 deg splayed "
     "pins (leaning out), extensions 3.8 cm along each leg; the feet where Blender puts them; BipodStow ends at the bind pose",
     bpz, "rotation <= 0.01 deg vs the build; 90 / 12 deg +- 0.01; travel +- 0.001 cm; feet <= 0.01 cm; stow end <= 0.001 cm", okb)

# ---------------------------------------------------------------- U5 LODs, triangles, sizes, bounds
tri = D["triangles"]
gate("U5 LOD count (SK_SR01, SM_SR01, SM_SR01_Mag 4; the scope 3)",
     {"SK": len(B["sk_lods"]), "SM": B["SM_SR01"]["num_lods"], "Mag": B["SM_SR01_Mag"]["num_lods"], "Scope": B[C.SCOPE]["num_lods"]},
     "4, 4, 4, 3", len(B["sk_lods"]) == 4 and B["SM_SR01"]["num_lods"] == 4 and B["SM_SR01_Mag"]["num_lods"] == 4
     and B[C.SCOPE]["num_lods"] == 3)
gate("U5 triangles per LOD equal in Blender, the FBX and Unreal (render data, mesh description, Unreal's FBX export); predicted "
     "static-import drops 0 (UD1)", tri, "equal per LOD", all(r["equal"] and r["predicted_import_drops"] == 0 for rows in tri.values() for r in rows))
sks = B["sk_lod_settings"]["screen_sizes"] if isinstance(B["sk_lod_settings"], dict) else None
gate("screen sizes from the sidecars (SK LOD settings, SM, Mag)",
     {"SK": sks, "SK_sidecar": SC["lod_screen_sizes"], "SM": B["SM_SR01"]["lod_screen_sizes"], "SM_sidecar": B["SM_SR01"]["sidecar_lod_screen_sizes"],
      "Mag": B["SM_SR01_Mag"]["lod_screen_sizes"], "Mag_sidecar": B["SM_SR01_Mag"]["sidecar_lod_screen_sizes"]},
     "equal (1e-6)", sks is not None and max(abs(a - b) for a, b in zip(sks, SC["lod_screen_sizes"])) < 1e-6
     and B["SM_SR01"]["lod_screen_sizes"] == B["SM_SR01"]["sidecar_lod_screen_sizes"]
     and B["SM_SR01_Mag"]["lod_screen_sizes"] == B["SM_SR01_Mag"]["sidecar_lod_screen_sizes"]
     and B[C.SCOPE]["lod_screen_sizes"] == B[C.SCOPE]["sidecar_lod_screen_sizes"])
rad = D["U5_bounds"]["radii"]
okr = (abs(rad["SK_engine_cm"] - rad["SK_build_cm"]) <= 0.01 and abs(rad["SM_engine_cm"] - rad["SM_build_cm"]) <= 0.01
       and abs(rad["Scope_engine_cm"] - rad["Scope_build_cm"]) <= 0.01)
gate("U5 engine sphere radii = the radii the screen sizes were derived from (SK: bind box + extension; SM / Mag: max |v - box "
     "centre|)", rad | {"extension_enters_lod_radius": D["U5_bounds"]["extension_enters_lod_radius"]}, "<= 0.01 cm", okr,
     "the SK's LOD radius includes the bounds extension: the sizes were derived at the extended radius; the magazine's build radius "
     "is not recorded in the gates (see the next row)")
ms = D["mag_screen_sizes"]
gate("mag screen sizes re-derived from the engine radii (size x r_mag / r, from the SK's or the twin's sizes)", ms,
     "<= 0.001 from the sidecar", ms["max_diff"] <= 1e-3)
be = SC["import"]["bounds_extension_cm"]
u5 = D["U5_bounds"]
outside = sum(v["vertices_outside"] for v in u5["clips"].values())
gate("U5 bounds: the stored bounds (+ the sidecar extension) hold every LOD0-3 vertex at every runtime frame of every clip "
     "(BipodDeploy / BipodStow, BoltCycle, ReloadEmpty, CheekRiser ...)",
     {"extension_applied": {"pos": B["sk_bounds"]["pos_ext"], "neg": B["sk_bounds"]["neg_ext"], "sidecar": [be["positive_cm"], be["negative_cm"]]},
      "vertices_outside": outside, "per_clip": u5["clips"]}, "0 outside", outside == 0)

# ---------------------------------------------------------------- U6 / M9
u6 = D["U6_M9"]
rest = u6["rest"]
gate("U6 magazine at Mag (engine attach, SnapToTarget, gun at an arbitrary world transform): composed transform zero; every "
     "reload frame", {"attached_vs_socket_cm": rest["attached_vs_socket_cm"], "rot": rest["attached_vs_socket_rot"],
                      "relative_to_socket": rest["relative_to_socket"][:7], "socket_vs_sidecar_cm": rest["socket_vs_sidecar_cm"],
                      "reload_frames_attached_vs_socket": {k: v["attached_vs_socket_max"] for k, v in u6["reload_frames"].items()}},
     "<= 0.001 cm, identity", rest["attached_vs_socket_cm"] <= 1e-3 and rest["attached_vs_socket_rot"] <= 1e-6
     and rest["socket_vs_sidecar_cm"] <= 1e-3 and all(v["attached_vs_socket_max"] <= 1e-3 for v in u6["reload_frames"].values()))
seat = u6["seated_intersecting_pairs"]
okseat = all(seat[k] == 0 for k in ("gun LOD0 / mag LOD0", "gun LOD1 / mag LOD1", "gun LOD0 / mag LOD1", "gun LOD1 / mag LOD0"))
mag_m1 = next((g_["value"] for g_ in mag["gates"] if g_["name"].startswith("M1 seated: intersecting triangles")), None)
gate("M9 seated fit on the read-back geometry (co-visible pairs LOD0-1 incl. (k, k+-1); LOD2-3 reported: mag.json M1 rates them "
     "in px at the switch distance)", {"pairs": seat, "mag_json_M1": mag_m1}, "0 at LOD0 / LOD1", okseat)
ip = u6["insert_path"]
okip = (all(not v["released_intersecting_steps"] and not v["rest_noncatch_steps"] for v in ip["lods"].values())
        and abs(ip["insert_mm"] - SC["magazine"]["insert_mm"]) <= 0.01 and ip["rotation_constant_deg"] <= 1e-3
        and ip["insert_axis_vs_mag_z"] > 0.999999)
gate("M9 straight reload path from the engine sockets (MagInsertStart -> Mag, 0.5 mm steps) on the read-back geometry: with the "
     "catch at its release angle 0 intersections (M4b); with the catch at rest only the catch nose meets the magazine (R36: the "
     "spring-loaded catch is cammed aside)", ip, "0 released; 0 non-catch contacts; insert 67.8 mm along the magazine's +Z, rotation "
     "constant", okip)
f5 = next(g_["value"] for g_ in mag["gates"] if g_["name"].startswith("F5"))
m8 = next(g_["value"] for g_ in mag["gates"] if g_["name"].startswith("M8"))


def frame_ok(h):
    own = [o for o in h[2] if not o.startswith("depth_mm=")]
    dep = float(next(o for o in h[2] if o.startswith("depth_mm=")).split("=")[1])
    return own == ["mag_release"] and dep <= f5["worst_depth_mm"] + 0.005, dep


u6f = {k: {"frames": v["frames"], "frames_with_intersections": [[h[0], h[1], h[2]] for h in v["frames_with_intersections"]],
           "catch_only_within_F5_depth": all(frame_ok(h)[0] for h in v["frames_with_intersections"])}
       for k, v in u6["reload_frames"].items()}
gate("U6 reload clips in engine: the magazine on the posed SR01 at every runtime frame (LOD0): nothing meets it except the catch "
     "nose leaving the notch on the release stroke, no deeper than the Blender F5 sweep allows (mag.json F5; M8 reports the same "
     "frame in Blender)", {"engine": u6f, "blender_F5": f5, "blender_M8": m8},
     f"0 frames, or catch-only frames with depth <= F5 worst {f5['worst_depth_mm']} mm (+0.005)",
     all(v["catch_only_within_F5_depth"] for v in u6f.values()))

# ---------------------------------------------------------------- U7 physics
ph = B["sk_physics"] or {}
body = (ph.get("bodies") or {}).get("body", {})
els = body.get("elements", [])
coll = [e for e in els if "NO_COLLISION" not in str(e.get("collision_enabled"))]
nocoll = [e for e in els if "NO_COLLISION" in str(e.get("collision_enabled"))]
sc_els = SC["physics_bodies"][0]["elements"]
exp_coll = sum(1 for e in sc_els if e["collision"])
exp_env = sum(1 for e in sc_els if not e["collision"])
gate("PHYS_SR01: one body on 'body'; the sidecar's colliding shapes (7 boxes + 1 capsule) and its no-collision, no-mass bounds "
     "envelope; 5.9 kg; consider_for_bounds; fresh process",
     {"bodies": sorted((ph.get("bodies") or {}).keys()), "colliding": sorted(e["shape"] for e in coll),
      "no_collision": [{"shape": e["shape"], "contribute_to_mass": e.get("contribute_to_mass")} for e in nocoll],
      "mass_kg": body.get("mass_kg"), "override": body.get("override_mass"), "consider_for_bounds": body.get("consider_for_bounds")},
     "1 body; 7 box + 1 capsule colliding; the envelope box(es) no collision, no mass; 5.9 kg",
     sorted((ph.get("bodies") or {}).keys()) == ["body"] and sorted(e["shape"] for e in coll).count("box") == 7
     and sorted(e["shape"] for e in coll).count("capsule") == 1 and len(coll) == exp_coll and len(nocoll) == exp_env
     and all(e.get("contribute_to_mass") in (False, "False") for e in nocoll) and abs((body.get("mass_kg") or 0) - SC["physics_bodies"][0]["mass_kg"]) < 1e-4)
u7v = D.get("U7_vertices") or {}
if E and u7v:
    gate("U7 physics in a ticking game world: SM_SR01 (level, rolled 70 deg), SM_SR01_Mag, SK_SR01 (PHYS_SR01, bipod folded) "
         "dropped 1 m: rest on their collision, no tunnelling (read-back LOD0 placed at every sampled transform); the deployed-bipod "
         "SK rests (its legs have no collision by design: the game drops the gun with the legs folded; its leg depth is reported)",
         {k: {kk: v[kk] for kk in ("rests", "no_tunnelling", "min_lowest_vertex_cm", "final_lowest_vertex_cm", "max_speed_last_1s_cm_s")}
          for k, v in u7v.items()}, "speed < 1 cm/s over the last 1 s; lowest vertex never < -2 cm, final >= -0.5 cm (ground top 0); "
         "deployed: rests only", all(v["rests"] and (v["no_tunnelling"] or k.endswith("_deployed")) for k, v in u7v.items()) and len(u7v) == 5)
    gate("U7 (W4 review addition) the COMPONENT's runtime bounds of every dropped, simulating actor hold every vertex at every sample, "
         "the deployed-bipod SK_SR01 included", {k: {"max_outside_cm": v["runtime_bounds_max_outside_cm"], "samples_outside": v["runtime_bounds_samples_outside"],
                                                    "shoulder_engine_vs_analysis_cm": v.get("shoulder_engine_vs_analysis_cm")} for k, v in u7v.items()},
         "0 samples outside (0.001 cm)", all(v["runtime_bounds_samples_outside"] == 0 for v in u7v.values()))
else:
    gate("U7 physics in a ticking game world", None, "measured", False, "pass E did not run")

# ---------------------------------------------------------------- U8 statics (Q13 authored UV1), textures
lm = {nm: {"index": B[nm]["light_map_coordinate_index"],
           "generate_off": [b["generate_lightmap_u_vs"] is False for b in B[nm]["lod_build_settings"]],
           "uv_channels": B[nm]["uv_channels_per_lod"]} for nm in ("SM_SR01", "SM_SR01_Mag")}
gate("U8 lightmap (plan Q13): index 1, Generate Lightmap UVs OFF on every LOD, 2 UV channels (the authored UV1 is the lightmap)", lm,
     "index 1; off on 4 / 4 LODs; 2 channels", all(v["index"] == 1 and all(v["generate_off"]) and len(v["generate_off"]) == 4
                                                  and all(c == 2 for c in v["uv_channels"]) for v in lm.values()))
uv1 = {k: v for k, v in D["uv1"].items() if not k.startswith(C.SCOPE)}
issues.append("scope UV1 (reported, not a plan U8 item): " + json.dumps({k: {kk: v.get(kk) for kk in ("layers", "overlap_px_64", "overlap_px_128")}
                                                                       for k, v in D["uv1"].items() if k.startswith(C.SCOPE)}))
fu = D["fbx_uv1"]
gate("U8 the authored UV1 as Unreal exports it: inside 0..1, 0 overlapping pixels at 64 and 128 px (UD4's resolutions); 1024 px "
     "reported beside the shipped FBX's",
     {k: {kk: v.get(kk) for kk in ("inside_0_1", "overlap_px_64", "overlap_px_128", "overlap_px_1024")} | {"shipped_fbx_overlap_px_1024": (fu.get(k) or {}).get("overlap_px_1024")}
      for k, v in uv1.items()}, "inside; 0 at 64 and 128", all(v["inside_0_1"] and v["overlap_px_64"] == 0 and v["overlap_px_128"] == 0 for v in uv1.values()))
want = {"BC": ("True", "TC_DEFAULT", "TEXTUREGROUP_WEAPON"), "ORM": ("False", "TC_MASKS", "TEXTUREGROUP_WEAPON"),
        "N": ("False", "TC_NORMALMAP", "TEXTUREGROUP_WEAPON_NORMAL_MAP"), "Masks": ("False", "TC_MASKS", "TEXTUREGROUP_WEAPON"),
        "Detail16": ("False", "TC_GRAYSCALE", "TEXTUREGROUP_WEAPON")}
bad = {}
for n, t in B["textures"].items():
    k = "Detail16" if n.endswith("Detail16") else n.rsplit("_", 1)[-1]
    s_, c_, g_ = want[k]
    if not (t["srgb"] == s_ and c_ in t["compression_settings"] and g_ in t["lod_group"] and (k != "N" or t["flip_green_channel"] == "False")):
        bad[n] = t
gate("texture flags persisted (fresh process): BC sRGB TC_Default, ORM / Masks linear TC_Masks, N TC_Normalmap flip-green off "
     "(group WeaponNormalMap), Detail16 linear Grayscale; groups Weapon", {"textures": len(B["textures"]), "wrong": bad}, "all", not bad)
log = (HERE / "srC_render.log").read_text(errors="ignore")
mips = {}
for m in re.finditer(r"\]\s*(\d+)x(\d+) \([^)]*\), (\d+)x(\d+) \([^)]*\), (PF_\w+), (\w+), (/Game/[^,]+), \w+, \w+, \w+, \d+, (\d+), \w+", log):
    name = m.group(7).split(".")[-1]
    if "SR01" in name or "Att_Scope" in name:
        mips[name] = {"size": int(m.group(1)), "format": m.group(5), "group": m.group(6), "mips": int(m.group(8))}
full = {n: v["mips"] == int(math.log2(v["size"])) + 1 for n, v in mips.items()}
gate("full mip chains (ListTextures, real RHI); Detail16 builds PF_G16", mips, "all full; Detail16 PF_G16",
     len(mips) == len(B["textures"]) and all(full.values()) and all(v["format"] == "PF_G16" for n, v in mips.items() if n.endswith("Detail16")))

# ---------------------------------------------------------------- U9 clips
u9 = D["U9"]
ok9 = True
decl = {a["file"][:-4]: a for a in SC["animations"]}
LEGS = {"bipod_leg_l", "bipod_leg_r", "bipod_leg_l_ext", "bipod_leg_r_ext"}
for k, v in u9.items():
    a = decl[k]
    allowed_end = LEGS if not a["ends_at_rest"] else set()
    allowed_start = (LEGS if k == "A_SR01_BipodStow" else set()) | ({"bolt"} if k == "A_SR01_ReloadEmpty" else set())
    ok_k = (v["engine_num_frames"] == a["frames"][1] and v["max_runtime_vs_raw_mm"] <= 0.1 and v["max_raw_vs_authored_mm"] <= 0.01
            and set(v["end_vs_bind_mm"]) <= allowed_end and set(v["start_vs_bind_mm"]) <= allowed_start
            and v["notifies_ok"] and "DefaultRecorderBoneCompression" in v["compression"])
    v["declared_ok"] = ok_k
    ok9 &= ok_k
gate("U9 clips: frames = the sidecar's; engine-evaluated runtime (compressed) vs raw <= 0.1 mm on every rigid part; raw = the authored "
     "clip (sr_clips, composed through the bipod parents) <= 0.01 mm; start / end poses = bind except what the sidecar declares "
     "(ReloadEmpty's open bolt at the start, the deployed bipod at BipodDeploy's end / BipodStow's start); every sidecar notify on its "
     "frame (+-0.5), no extras", {k: {kk: vv for kk, vv in v.items() if kk != "notifies"} for k, v in u9.items()}, "as stated", ok9)

# ---------------------------------------------------------------- U10 warnings
warn = {}
for nm in ("srA_import.log", "srA2_level.log", "srA3_abp.log", "srB_verify.log", "srC_render.log", "srE_game.log"):
    p = HERE / nm
    if not p.exists():
        continue
    lines = [l.strip()[:220] for l in p.read_text(errors="ignore").splitlines()
             if re.search(r"(Warning|Error):", l) and re.search(r"SR01|SK_|SM_|A_SR01|PHYS_|T_SR01|Att_Scope|Notifies", l)
             and "DeprecationWarning" not in l and "LogInit: Display" not in l and "ABP_Gun_LongGun" not in l]
    warn[nm] = {"count": len(lines), "lines": sorted(set(lines))[:12]}
gate("U10 0 warning / error lines from the assets in every pass log (the harness ABP's compile warning is reported under U2b)", warn,
     "0", all(v["count"] == 0 for v in warn.values()))

# ---------------------------------------------------------------- U12 residency
u12 = {}
elog = (HERE / "srE_game.log").read_text(errors="ignore") if (HERE / "srE_game.log").exists() else ""
for view in ("hip", "ads"):
    blk = re.search(rf"SM_STREAM_BEGIN {view}(.*?)SM_STREAM_END {view}", elog, re.S)
    if not blk:
        continue
    for m in re.finditer(r"Texture2D (/Game/[^\s]+)\s*\n[^\n]*Current=(\d+)x\d+\s+Wanted=(\d+)x\d+ MaxAllowed=(\d+)x\d+", blk.group(1)):
        n = m.group(1).split(".")[-1]
        if "SR01" in n:
            u12.setdefault(view, {})[n] = {"current": int(m.group(2)), "wanted": int(m.group(3)), "max": int(m.group(4))}
gun = ("T_SR01_Metal_BC", "T_SR01_Metal_N", "T_SR01_Chassis_BC", "T_SR01_Chassis_N")
ok12 = bool(u12) and all(u12.get(v, {}).get(n, {}).get("current") == u12.get(v, {}).get(n, {}).get("max") for v in ("hip", "ads") for n in gun)
gate("U12 texture residency in a ticking game world (streaming on): the gun's BC and N resident at the top mip at the hip (35 cm, 90 deg) "
     "and at ADS (the scope's EyePoint, 55 deg)", u12, "current = max for Metal / Chassis BC and N at both views", ok12,
     "the magazine's own maps are reported (a separate mesh)")

# ---------------------------------------------------------------- C2, hulls, slots, nanite, U11
c2 = D["C2"]
gate("C2 every LOD0 surface sample (300k + every vertex) of the read-back geometry inside the stored hulls", c2, "0 outside",
     all(v["outside_gt_0.001cm"] == 0 for v in c2.values()))
hs = D["hull_shells"]
gate("hulls stored: SM_SR01 10, SM_SR01_Mag 1, SM_Att_Scope_LongRange 3, <= 32 vertices each (Unreal's own export split into shells)",
     {**hs, "pass_B_convex_elems": {k: B[k]["convex_elems"] for k in ("SM_SR01", "SM_SR01_Mag", C.SCOPE)}},
     "10 + 1 + 3; <= 32", hs["SM_SR01"]["count"] == 10 and hs["SM_SR01_Mag"]["count"] == 1 and hs[C.SCOPE]["count"] == 3
     and B["SM_SR01"]["convex_elems"] == 10 and B["SM_SR01_Mag"]["convex_elems"] == 1 and B[C.SCOPE]["convex_elems"] == 3
     and max(hs["SM_SR01"]["vertices"] + hs["SM_SR01_Mag"]["vertices"] + hs[C.SCOPE]["vertices"]) <= 32)
slots = {"SK_SR01": [s["slot"] for s in B["sk_slots"]], "SM_SR01": [s["slot"] for s in B["SM_SR01"]["material_slots"]],
         "SM_SR01_Mag": [s["slot"] for s in B["SM_SR01_Mag"]["material_slots"]], C.SCOPE: [s["slot"] for s in B[C.SCOPE]["material_slots"]]}
nan = {k: B[k]["nanite"] for k in ("SM_SR01", "SM_SR01_Mag", C.SCOPE)}
gate("material slots (2 + 3 + 1 + 2, sidecar names); Nanite off", {"slots": slots, "nanite": nan},
     "SK [Metal, Chassis], SM [Metal, Chassis, Mag], Mag [Mag], Scope [Body, Lens]; nanite false",
     slots == {"SK_SR01": ["M_SR01_Metal", "M_SR01_Chassis"], "SM_SR01": ["M_SR01_Metal", "M_SR01_Chassis", "M_SR01_Mag"],
               "SM_SR01_Mag": ["M_SR01_Mag"], C.SCOPE: ["M_Att_Scope_Body", "M_Att_Scope_Lens"]} and all(v is False for v in nan.values()))
gate("U11 hand fit in engine", None, "if a player MetaHuman exists in the verification project", True,
     "not run: the verification project holds no MetaHuman; the posed hand fit H1 full (gates/rig_export.json, MH_PlayerDefault in "
     "Blender) passed and its result is in the sidecar gun.hand_offset for the game to reproduce", kind="not_applicable")
issues.append("U11 not run: no player MetaHuman in the verification project (H1 full passed in Blender; gun.hand_offset carries it).")

# ---------------------------------------------------------------- the scope view with a generic reticle (render aid, no gate)
try:
    from PIL import Image, ImageDraw
    src = HERE / "renders" / "look_scope_view.png"
    if src.exists() and sv:
        im = Image.open(src).convert("RGB")
        W, H = im.size
        dr = ImageDraw.Draw(im)
        cx, cy = W / 2.0, H / 2.0
        px_per_cm = W / (2 * sv["range_cm"] * math.tan(math.radians(sv["fov_deg"] / 2)))
        mil = sv["range_cm"] / 1000.0 * px_per_cm              # 1 mil at the board
        col = (10, 10, 10)
        for sgn in (-1, 1):                                     # duplex: thick outer posts, thin centre cross
            dr.line([(cx + sgn * W, cy), (cx + sgn * 6 * mil, cy)], fill=col, width=7)
            dr.line([(cx, cy + sgn * H), (cx, cy + sgn * 6 * mil)], fill=col, width=7)
        dr.line([(cx - 6 * mil, cy), (cx + 6 * mil, cy)], fill=col, width=2)
        dr.line([(cx, cy - 6 * mil), (cx, cy + 6 * mil)], fill=col, width=2)
        for k in range(-5, 6):
            if k:
                r_ = 3
                dr.ellipse([cx + k * mil - r_, cy - r_, cx + k * mil + r_, cy + r_], fill=col)
                dr.ellipse([cx - r_, cy + k * mil - r_, cx + r_, cy + k * mil + r_], fill=col)
        R = min(W, H) / 2 - 4                                    # the ocular's round field
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
        im = Image.composite(im, Image.new("RGB", (W, H), (0, 0, 0)), mask)
        im.save(HERE / "renders" / "look_scope_view_reticle.png")
        issues.append(f"scope view: renders/look_scope_view_reticle.png (generic duplex + mil dots drawn afterwards; 1 mil = {mil:.1f} px at "
                      f"{sv['range_cm'] / 100:.0f} m; the bore's 10 m point should sit {sv['bore_drop_below_sight_line_cm'] * px_per_cm:.0f} px "
                      "under the cross)")
except Exception as e:  # noqa: BLE001
    issues.append(f"scope-view reticle overlay failed: {e}")

failed = [g["name"] for g in gates if not g["pass"]]
for f in json.loads((HERE / "w5_findings.json").read_text(encoding="utf-8")) if (HERE / "w5_findings.json").exists() else []:
    findings.append(f)
out = {"stage": "W5 Unreal (UE 5.8, SR01_BUILD_PLAN W5 + GUN_BUILDING_STUDY 6 / 7.4)",
       "engine": (A or {}).get("engine"), "content_path": C.dest(),
       "project": "WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject (the katana / AR-01 verification project, main checkout)",
       "passes": {"A import": "srA_import.py (-nullrhi)", "A3 ABP": "srA3_abp.py (-nullrhi, -EnablePlugins=AllToolsets)",
                  "A2 check level": "srA2_level.py (-nullrhi)", "B read-back": "srB_verify.py (-nullrhi)",
                  "C render + U2b": "srC_render.py (D3D12, -RenderOffscreen)", "E game world": "srE_game.py (-game, D3D12, -RenderOffscreen)",
                  "D analysis": "srD_analyse.py (Blender)", "F summary": "srF_summary.py"},
       "status": "pass" if not failed else "fail", "engine_verified": not failed and gates[0]["pass"] and gates[1]["pass"],
       "failed": failed, "issues": issues, "findings": findings, "sha256": START, "gates": gates}
(HERE / "verification_summary.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print("STATUS", out["status"], "gates", len(gates), "failed:", failed)
