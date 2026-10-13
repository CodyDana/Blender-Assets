"""SMG01 W5: the verification summary (plain Python + numpy + PIL). Reads every pass record of this harness and writes
WorkFiles/guns/smg/UnrealCheck/verification_summary.json with one row per SMG_BUILD_PLAN 14.3 gate (U1-U12, U2b, C2,
M9, triangles equal) plus the byte guards (name, value, threshold, pass). "engine_verified" only when the bytes every
pass used are the shipped bytes and the bytes the W3 gates recorded (rig_export.json, mag.json M7).

    py -3 -B WorkFiles/guns/smg/UnrealCheck/smF_summary.py
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
import sm_common as C  # noqa: E402


def j(name):
    p = HERE / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


A, A2, A3, B, CR, D, E = (j(n) for n in ("smA_import.json", "smA2_level.json", "smA3_abp.json", "smB_verify.json",
                                         "smC_render.json", "smD_analysis.json", "smE_game.json"))
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
gate("bytes: every pass used the shipped bytes (sha256 of every Exports/Guns/SMG01 file before and after passes A, A2, A3, B, C)",
     {"files": len(START), "unchanged_per_pass": same, "now_equal_start": now == START}, "all equal",
     all(same.values()) and now == START)
rx = json.loads((C.GATES / "rig_export.json").read_text())
rec = {f.split("Exports/Guns/SMG01/")[-1]: v for f, v in rx["sha256"].items()}
mism = [k for k, v in rec.items() if START.get(k) != v]
mag = json.loads((C.GATES / "mag.json").read_text())
m7 = next(g for g in mag["gates"] if g["name"].startswith("M7"))["value"]
gate("bytes = the W3 gated bytes (rig_export.json sha256, mag.json M7)",
     {"rig_export_files": len(rec), "mismatch": mism, "SM_SMG01.fbx": START["SM_SMG01.fbx"] == m7.get("gun"),
      "SM_SMG01_Mag.fbx": START["SM_SMG01_Mag.fbx"] == m7.get("mag")},
     "equal", not mism and START["SM_SMG01.fbx"] == m7.get("gun") and START["SM_SMG01_Mag.fbx"] == m7.get("mag"))

# ---------------------------------------------------------------- import
gate("pass A import (fresh process; legacy FBX importer, the sidecar settings; SK_AR01_Skeleton set compatible)",
     {"status": A["status"], "lods_SK": A["lod_count_after_import"], "clips": len(A["steps"]["animations"]),
      "sockets_SK": len(A["steps"]["sockets"]) if isinstance(A["steps"]["sockets"], list) else A["steps"]["sockets"],
      "physics": A["steps"]["physics"].get("asset") if isinstance(A["steps"]["physics"], dict) else None,
      "physics_elements": A["steps"]["physics"].get("elements_written") if isinstance(A["steps"]["physics"], dict) else None,
      "textures": len(A["textures"]), "compatible_skeletons": A.get("compatible_skeletons")},
     "ok; 4 LODs; 8 clips; 21 sockets", A["status"] == "ok" and A["lod_count_after_import"] == 4 and len(A["steps"]["animations"]) == 8
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
for k in ("selector_SAFE", "selector_AUTO"):
    r = u2[k]
    rv = rotvec(quat_m(r["got_component"][3:7]))
    sel[k] = {"blender_deg_commanded": r["blender_deg"], "about_Y_deg": round(float(rv[1]), 5),
              "off_axis_deg": round(float(abs(rv[0]) + abs(rv[2])), 6),
              "head_moved_cm": float(np.abs(np.array(r["got_component"][:3]) - np.array(r["ref_component"][:3])).max())}
ok2 = (np.abs(dv - [bolt["commanded_cm"], 0, 0]).max() <= 1e-3
       and all(abs(v["about_Y_deg"] - v["blender_deg_commanded"]) <= 1e-3 and v["off_axis_deg"] < 1e-4 and v["head_moved_cm"] < 1e-6
               for v in sel.values()))
gate("U2 procedural (engine pose maths, bone-space offsets): the bolt's -X moves it straight back by the full travel; the "
     "selector turns about its own Y to SAFE / AUTO", {"bolt_component_motion_cm": dv.round(6).tolist(), "selector": sel},
     "bolt (-6.79, 0, 0) +- 0.001 cm; selector about Y, angle +- 0.001 deg, pivot fixed", ok2)

# ---------------------------------------------------------------- U2b
U = CR["U2b"]
heads = {"SMG01": {n: v["head_cm"] for n, v in SC["bones_rest"].items()},
         "AR01": {n: v["head_cm"] for n, v in C.sidecar_ar()["bones_rest"].items()}}
SOCK_ON = {"SMG01": {"trigger": "Trigger", "selector": "Selector", "mag_release": "MagRelease", "stock": "Shoulder"},
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
    if gun == "SMG01":
        sfr = g["clip_reference"]["A_SMG01_Selector"]["frames"]
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
    # missing bone probe (stock): SMG = the StockFold clip's end; AR = nothing moves
    if gun == "SMG01":
        sf = g["clip_reference"]["A_SMG01_StockFold"]["frames"]
        last = sf[str(max(int(k) for k in sf))]["sockets"]["Shoulder"]
        got = cs["stock_1"]["sockets"]["Shoulder"]
        dloc = float(np.abs(np.array(got[:3]) - np.array(last[:3])).max())
        dang = float(np.linalg.norm(rotvec(quat_m(got[3:7]) @ quat_m(last[3:7]).T)))
        r["stock"] = {"vs_StockFold_end_cm": round(dloc, 6), "vs_StockFold_end_deg": round(dang, 6), "ok": bool(dloc <= 0.01 and dang <= 0.01)}
    else:
        moved = max(float(np.abs(np.array(cs["stock_1"]["bones"][b][:3]) - np.array(bind["bones"][b][:3])).max()) for b in g["bones"])
        moved_s = max(float(np.abs(np.array(cs["stock_1"]["sockets"][s][:7]) - np.array(bind["sockets"][s][:7])).max()) for s in bind["sockets"])
        r["stock"] = {"missing_bone": "stock", "max_bone_motion_cm": moved, "max_socket_change": moved_s, "ok": bool(moved < 1e-6 and moved_s < 1e-6)}
    # rest: the bind pose except the SEMI detent (AR-01: 32 deg)
    rest_dev = {}
    for b in g["bones"]:
        dd = float(np.abs(np.array(bind["bones"][b][:7]) - np.array(g["bind"]["bones"][b][:7])).max())
        if dd > 1e-6:
            rest_dev[b] = round(dd, 6)
    r["rest_vs_bind"] = rest_dev
    r["rest_ok"] = set(rest_dev) <= ({"selector"} if gun == "AR01" else set())
    r["ok"] = all(r[k]["ok"] for k in ("bolt", "trigger", "selector", "release", "stock")) and r["rest_ok"] and r["anim_instance_every_case"]
    ok2b &= r["ok"]
    u2b[gun] = r
clog = (HERE / "smC_render.log").read_text(errors="ignore")
rt_err = sorted({l.strip()[:200] for l in clog.splitlines() if re.search(r"(Warning|Error):", l) and re.search(r"ABP_Gun|stock|AnimInstance|Anim", l)
                 and "DeprecationWarning" not in l})
abp_compile = sorted({l.strip()[-140:] for l in (HERE / "smA3_abp.log").read_text(errors="ignore").splitlines()
                      if "ABP_Gun_LongGun" in l and re.search(r"(Warning|Error):", l)})
u2b["runtime_log_lines_about_the_ABP_or_stock"] = rt_err
u2b["compile"] = {"status": A3["compile"]["status"], "chain": A3["chain_from_output"], "log": abp_compile}
gate("U2b one ABP (ABP_Gun_LongGun, authored on SK_AR01_Skeleton) drives SK_SMG01 (Compatible Skeletons) and SK_AR01 through "
     "normalized inputs mapped by each gun's angle table: bolts straight back by the table travel (= each Fire clip's rear "
     "stop), both triggers pull their lower end rearward by the table angle (= each Fire clip's full pull), the detent index "
     "reaches each gun's SAFE / SEMI / AUTO (= its own clips), each release moves its own way (= its Reload clip), no error on "
     "the missing bone (stock on SK_AR01)", u2b,
     "0.01 cm / 0.01 deg on both guns; no runtime error lines", ok2b and not rt_err,
     "the only compile message is the authoring-time warning 'Bone stock not found in Skeleton' for the SMG-only node on the "
     "AR-01 pilot skeleton (status UP_TO_DATE_WITH_WARNINGS); at runtime the node does nothing on SK_AR01 and folds the SMG's "
     "stock exactly to its StockFold clip's end")
issues.append("U2b: a node on an SMG-only bone (stock) compiles with a warning ('Bone stock not found in Skeleton') because the class "
              "ABP is authored on the AR-01 pilot skeleton; it raises no runtime error and works on the SMG. For a warning-free class "
              "ABP the game should drive SMG-only bones (stock, sight_front, charging_handle) by clips on the slot / a linked layer, or "
              "author the class ABP on the superset skeleton. The game's DemoGame_1_Guns ABP_Gun_LongGun still drives the trigger with "
              "a constant AR-01 angle (-12) and no table: it needs the normalized inputs (this harness's graph) before the SMG is wired "
              "into the game (prototype work, not done here).")
u3 = D["U3"]
gate("U3 sockets on SK_SMG01: from the sidecar, on the right bones, scale 1, outered to the asset, fresh process",
     {"count": len(u3["sockets"]), "worst_loc_cm": u3["worst_loc_cm"], "worst_rot_deg": u3["worst_rot_deg"], "extra": u3["extra"]},
     "21; <= 0.001 cm / 0.001 deg; no extras", u3["pass"] and len(u3["sockets"]) == 21)
for nm, n_exp in (("SM_SMG01", 21), ("SM_SMG01_Mag", 5)):
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
gate("U4 First Person rendering with VSM (FP_Weapon + FP_Mag vs TP_Weapon + TP_Mag): FP casts no ground shadow, TP does; FP at "
     "ForcedLodModel 1 renders LOD0 where the auto-LOD TP component falls to LOD3", {"ground_shadow_px": shadow, "lod_pixels_differing": lodt,
     "components": {k: v for k, v in u4.get("shots", {}).items() if isinstance(v, dict)}},
     "TP shadow > 1000 px, FP < 1 % of it; FP closer to the LOD0 reference, TP to LOD3", ok4,
     "'the owner sees no TP component' needs a possessed player pawn carrying both components (game-side weapon Blueprint); "
     "not measurable here (same as the AR-01)")
issues.append("U4: 'owner sees no TP component' is not measured (needs the weapon Blueprint on a possessed pawn: game-side, as on the AR-01).")

# ---------------------------------------------------------------- U5 LODs, triangles, sizes, bounds
tri = D["triangles"]
gate("U5 LOD count 4 (SK_SMG01, SM_SMG01, SM_SMG01_Mag)",
     {"SK": len(B["sk_lods"]), "SM": B["SM_SMG01"]["num_lods"], "Mag": B["SM_SMG01_Mag"]["num_lods"]}, "4 each",
     len(B["sk_lods"]) == 4 and B["SM_SMG01"]["num_lods"] == 4 and B["SM_SMG01_Mag"]["num_lods"] == 4)
gate("U5 triangles per LOD equal in Blender, the FBX and Unreal (render data, mesh description, Unreal's FBX export); predicted "
     "static-import drops 0 (UD1)", tri, "equal per LOD", all(r["equal"] and r["predicted_import_drops"] == 0 for rows in tri.values() for r in rows))
sks = B["sk_lod_settings"]["screen_sizes"] if isinstance(B["sk_lod_settings"], dict) else None
gate("screen sizes from the sidecars (SK LOD settings, SM, Mag)",
     {"SK": sks, "SK_sidecar": SC["lod_screen_sizes"], "SM": B["SM_SMG01"]["lod_screen_sizes"], "SM_sidecar": B["SM_SMG01"]["sidecar_lod_screen_sizes"],
      "Mag": B["SM_SMG01_Mag"]["lod_screen_sizes"], "Mag_sidecar": B["SM_SMG01_Mag"]["sidecar_lod_screen_sizes"]},
     "equal (1e-6)", sks is not None and max(abs(a - b) for a, b in zip(sks, SC["lod_screen_sizes"])) < 1e-6
     and B["SM_SMG01"]["lod_screen_sizes"] == B["SM_SMG01"]["sidecar_lod_screen_sizes"]
     and B["SM_SMG01_Mag"]["lod_screen_sizes"] == B["SM_SMG01_Mag"]["sidecar_lod_screen_sizes"])
rad = D["U5_bounds"]["radii"]
okr = (abs(rad["SK_engine_cm"] - rad["SK_build_cm"]) <= 0.01 and abs(rad["SM_engine_cm"] - rad["SM_build_cm"]) <= 0.01
       and abs(rad["Mag_engine_cm"] - rad["Mag_build_cm"]) <= 0.01)
gate("U5 engine sphere radii = the radii the screen sizes were derived from (SK: bind box + extension; SM / Mag: max |v - box "
     "centre|)", rad | {"extension_enters_lod_radius": D["U5_bounds"]["extension_enters_lod_radius"]}, "<= 0.01 cm", okr,
     "the SK's LOD radius includes the bounds extension (37.54 cm vs 33.55 cm imported): the sizes were derived at the extended radius")
ms = D["mag_screen_sizes"]
gate("mag screen sizes re-derived from the engine radii (size_SK x r_mag / r_SK)", ms, "<= 0.001 from the sidecar", ms["max_diff"] <= 1e-3)
be = SC["import"]["bounds_extension_cm"]
u5 = D["U5_bounds"]
outside = sum(v["vertices_outside"] for v in u5["clips"].values())
gate("U5 bounds: the stored bounds (+ the sidecar extension) hold every LOD0-3 vertex at every runtime frame of every clip "
     "(both stock states: StockFold / StockUnfold; sights folded: SightFlip)",
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
     "spring-loaded catch is cammed aside)", ip, "0 released; 0 non-catch contacts; insert 68.2 mm along the magazine's +Z, rotation "
     "constant", okip)
gate("U6 reload clips in engine: the magazine on the posed SMG (catch posed by the clip) at every runtime frame (LOD0)",
     {k: {"frames": v["frames"], "frames_with_intersections": v["frames_with_intersections"]} for k, v in u6["reload_frames"].items()},
     "0 frames", all(not v["frames_with_intersections"] for v in u6["reload_frames"].values()))

# ---------------------------------------------------------------- U7 physics
ph = B["sk_physics"] or {}
body = (ph.get("bodies") or {}).get("body", {})
els = body.get("elements", [])
coll = [e for e in els if "NO_COLLISION" not in str(e.get("collision_enabled"))]
nocoll = [e for e in els if "NO_COLLISION" in str(e.get("collision_enabled"))]
sc_els = SC["physics_bodies"][0]["elements"]
exp_coll = sum(1 for e in sc_els if e["collision"])
exp_env = sum(1 for e in sc_els if not e["collision"])
gate("PHYS_SMG01: one body on 'body'; the sidecar's colliding shapes (7 boxes + 1 capsule) and its no-collision, no-mass bounds "
     "envelope; 2.5 kg; consider_for_bounds; fresh process",
     {"bodies": sorted((ph.get("bodies") or {}).keys()), "colliding": sorted(e["shape"] for e in coll),
      "no_collision": [{"shape": e["shape"], "contribute_to_mass": e.get("contribute_to_mass")} for e in nocoll],
      "mass_kg": body.get("mass_kg"), "override": body.get("override_mass"), "consider_for_bounds": body.get("consider_for_bounds")},
     "1 body; 7 box + 1 capsule colliding; the envelope box(es) no collision, no mass; 2.5 kg",
     sorted((ph.get("bodies") or {}).keys()) == ["body"] and sorted(e["shape"] for e in coll).count("box") == 7
     and sorted(e["shape"] for e in coll).count("capsule") == 1 and len(coll) == exp_coll and len(nocoll) == exp_env
     and all(e.get("contribute_to_mass") in (False, "False") for e in nocoll) and abs((body.get("mass_kg") or 0) - 2.5) < 1e-4)
u7v = D.get("U7_vertices") or {}
if E and u7v:
    gate("U7 physics in a ticking game world: SM_SMG01 (level, rolled 70 deg), SM_SMG01_Mag, SK_SMG01 (PHYS_SMG01) with the stock "
         "extended and a second SK_SMG01 with the stock folded, dropped 1 m: rest on their collision, no tunnelling (read-back LOD0 "
         "placed at every sampled transform; the folded one posed by the StockFold clip's end)",
         {k: {kk: v[kk] for kk in ("rests", "no_tunnelling", "min_lowest_vertex_cm", "final_lowest_vertex_cm", "max_speed_last_1s_cm_s")}
          for k, v in u7v.items()}, "speed < 1 cm/s over the last 1 s; lowest vertex never < -2 cm, final >= -0.5 cm (ground top 0)",
         all(v["rests"] and v["no_tunnelling"] for v in u7v.values()) and len(u7v) == 5)
    gate("U7 (W4 review addition) the COMPONENT's runtime bounds of every dropped, simulating actor hold every vertex at every sample, "
         "the folded-stock SK_SMG01 included", {k: {"max_outside_cm": v["runtime_bounds_max_outside_cm"], "samples_outside": v["runtime_bounds_samples_outside"],
                                                    "shoulder_engine_vs_analysis_cm": v.get("shoulder_engine_vs_analysis_cm")} for k, v in u7v.items()},
         "0 samples outside (0.001 cm)", all(v["runtime_bounds_samples_outside"] == 0 for v in u7v.values()))
else:
    gate("U7 physics in a ticking game world", None, "measured", False, "pass E did not run")

# ---------------------------------------------------------------- U8 statics (Q13 authored UV1), textures
lm = {nm: {"index": B[nm]["light_map_coordinate_index"],
           "generate_off": [b["generate_lightmap_u_vs"] is False for b in B[nm]["lod_build_settings"]],
           "uv_channels": B[nm]["uv_channels_per_lod"]} for nm in ("SM_SMG01", "SM_SMG01_Mag")}
gate("U8 lightmap (plan Q13): index 1, Generate Lightmap UVs OFF on every LOD, 2 UV channels (the authored UV1 is the lightmap)", lm,
     "index 1; off on 4 / 4 LODs; 2 channels", all(v["index"] == 1 and all(v["generate_off"]) and len(v["generate_off"]) == 4
                                                  and all(c == 2 for c in v["uv_channels"]) for v in lm.values()))
uv1 = D["uv1"]
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
log = (HERE / "smC_render.log").read_text(errors="ignore")
mips = {}
for m in re.finditer(r"\]\s*(\d+)x(\d+) \([^)]*\), (\d+)x(\d+) \([^)]*\), (PF_\w+), (\w+), (/Game/[^,]+), \w+, \w+, \w+, \d+, (\d+), \w+", log):
    name = m.group(7).split(".")[-1]
    if "SMG01" in name:
        mips[name] = {"size": int(m.group(1)), "format": m.group(5), "group": m.group(6), "mips": int(m.group(8))}
full = {n: v["mips"] == int(math.log2(v["size"])) + 1 for n, v in mips.items()}
gate("full mip chains (ListTextures, real RHI); Detail16 builds PF_G16", mips, "all full; Detail16 PF_G16",
     len(mips) == len(B["textures"]) and all(full.values()) and all(v["format"] == "PF_G16" for n, v in mips.items() if n.endswith("Detail16")))

# ---------------------------------------------------------------- U9 clips
u9 = D["U9"]
ok9 = True
decl = {a["file"][:-4]: a for a in SC["animations"]}
for k, v in u9.items():
    a = decl[k]
    allowed_end = {"selector"} if 45.0 in a["selector_held_deg"] and len(a["selector_held_deg"]) == 1 else set()
    if not a["ends_at_rest"] or k == "A_SMG01_StockFold":
        allowed_end |= {"stock"} if k == "A_SMG01_StockFold" else set()
    allowed_start = set(allowed_end) | ({"bolt"} if not a["starts_at_rest"] else set())
    if k == "A_SMG01_StockUnfold":
        allowed_start |= {"stock"}
    ok_k = (v["engine_num_frames"] == a["frames"][1] and v["max_runtime_vs_raw_mm"] <= 0.1 and v["max_raw_vs_authored_mm"] <= 0.01
            and set(v["end_vs_bind_mm"]) <= allowed_end and set(v["start_vs_bind_mm"]) <= allowed_start
            and v["notifies_ok"] and "DefaultRecorderBoneCompression" in v["compression"])
    v["declared_ok"] = ok_k
    ok9 &= ok_k
gate("U9 clips: frames = the sidecar's; engine-evaluated runtime (compressed) vs raw <= 0.1 mm on every rigid part; raw = the authored "
     "clip (smg_clips) <= 0.01 mm; start / end poses = bind except what the sidecar declares (AUTO held where the bolt moves, "
     "ReloadEmpty's held-open bolt at the start, the folded stock at StockFold's end / StockUnfold's start); every sidecar notify on its "
     "frame (+-0.5), no extras", {k: {kk: vv for kk, vv in v.items() if kk != "notifies"} for k, v in u9.items()}, "as stated", ok9)

# ---------------------------------------------------------------- U10 warnings
warn = {}
for nm in ("smA_import.log", "smA2_level.log", "smA3_abp.log", "smB_verify.log", "smC_render.log", "smE_game.log"):
    p = HERE / nm
    if not p.exists():
        continue
    lines = [l.strip()[:220] for l in p.read_text(errors="ignore").splitlines()
             if re.search(r"(Warning|Error):", l) and re.search(r"SMG01|SK_|SM_|A_SMG01|PHYS_|T_SMG01|Notifies", l)
             and "DeprecationWarning" not in l and "LogInit: Display" not in l and "ABP_Gun_LongGun" not in l]
    warn[nm] = {"count": len(lines), "lines": sorted(set(lines))[:12]}
gate("U10 0 warning / error lines from the assets in every pass log (the harness ABP's compile warning is reported under U2b)", warn,
     "0", all(v["count"] == 0 for v in warn.values()))

# ---------------------------------------------------------------- U12 residency
u12 = {}
elog = (HERE / "smE_game.log").read_text(errors="ignore") if (HERE / "smE_game.log").exists() else ""
for view in ("hip", "ads"):
    blk = re.search(rf"SM_STREAM_BEGIN {view}(.*?)SM_STREAM_END {view}", elog, re.S)
    if not blk:
        continue
    for m in re.finditer(r"Texture2D (/Game/[^\s]+)\s*\n[^\n]*Current=(\d+)x\d+\s+Wanted=(\d+)x\d+ MaxAllowed=(\d+)x\d+", blk.group(1)):
        n = m.group(1).split(".")[-1]
        if "SMG01" in n:
            u12.setdefault(view, {})[n] = {"current": int(m.group(2)), "wanted": int(m.group(3)), "max": int(m.group(4))}
gun = ("T_SMG01_Metal_BC", "T_SMG01_Metal_N", "T_SMG01_Furniture_BC", "T_SMG01_Furniture_N")
ok12 = bool(u12) and all(u12.get(v, {}).get(n, {}).get("current") == u12.get(v, {}).get(n, {}).get("max") for v in ("hip", "ads") for n in gun)
gate("U12 texture residency in a ticking game world (streaming on): the gun's BC and N resident at the top mip at the hip (35 cm, 90 deg) "
     "and at ADS (Sight eye, 55 deg)", u12, "current = max for Metal / Furniture BC and N at both views", ok12,
     "the magazine's own maps are reported (a separate mesh)")

# ---------------------------------------------------------------- C2, hulls, slots, nanite, U11
c2 = D["C2"]
gate("C2 every LOD0 surface sample (300k + every vertex) of the read-back geometry inside the stored hulls", c2, "0 outside",
     all(v["outside_gt_0.001cm"] == 0 for v in c2.values()))
hs = D["hull_shells"]
gate("hulls stored: SM_SMG01 8, SM_SMG01_Mag 1, <= 32 vertices each (Unreal's own export split into shells)",
     {**hs, "pass_B_convex_elems": {"SM_SMG01": B["SM_SMG01"]["convex_elems"], "SM_SMG01_Mag": B["SM_SMG01_Mag"]["convex_elems"]}},
     "8 + 1; <= 32", hs["SM_SMG01"]["count"] == 8 and hs["SM_SMG01_Mag"]["count"] == 1 and B["SM_SMG01"]["convex_elems"] == 8
     and B["SM_SMG01_Mag"]["convex_elems"] == 1 and max(hs["SM_SMG01"]["vertices"] + hs["SM_SMG01_Mag"]["vertices"]) <= 32)
slots = {"SK_SMG01": [s["slot"] for s in B["sk_slots"]], "SM_SMG01": [s["slot"] for s in B["SM_SMG01"]["material_slots"]],
         "SM_SMG01_Mag": [s["slot"] for s in B["SM_SMG01_Mag"]["material_slots"]]}
gate("material slots (2 + 3 + 1, sidecar names); Nanite off", {"slots": slots, "nanite": {"SM_SMG01": B["SM_SMG01"]["nanite"], "SM_SMG01_Mag": B["SM_SMG01_Mag"]["nanite"]}},
     "SK [Metal, Furniture], SM [Metal, Furniture, Mag], Mag [Mag]; nanite false",
     slots == {"SK_SMG01": ["M_SMG01_Metal", "M_SMG01_Furniture"], "SM_SMG01": ["M_SMG01_Metal", "M_SMG01_Furniture", "M_SMG01_Mag"],
               "SM_SMG01_Mag": ["M_SMG01_Mag"]} and B["SM_SMG01"]["nanite"] is False and B["SM_SMG01_Mag"]["nanite"] is False)
gate("U11 hand fit in engine", None, "if a player MetaHuman exists in the verification project", True,
     "not run: the verification project holds no MetaHuman; the posed hand fit H1 full (gates/rig_export.json, MH_PlayerDefault in "
     "Blender) passed and its result is in the sidecar gun.hand_offset for the game to reproduce", kind="not_applicable")
issues.append("U11 not run: no player MetaHuman in the verification project (H1 full passed in Blender; gun.hand_offset carries it).")

failed = [g["name"] for g in gates if not g["pass"]]
for f in json.loads((HERE / "w5_findings.json").read_text(encoding="utf-8")) if (HERE / "w5_findings.json").exists() else []:
    findings.append(f)
out = {"stage": "W5 Unreal (UE 5.8, SMG_BUILD_PLAN 14.3 + GUN_BUILDING_STUDY 7.4)",
       "engine": (A or {}).get("engine"), "content_path": C.dest(),
       "project": "WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject (the katana / AR-01 verification project, main checkout)",
       "passes": {"A import": "smA_import.py (-nullrhi)", "A3 ABP": "smA3_abp.py (-nullrhi, -EnablePlugins=AllToolsets)",
                  "A2 check level": "smA2_level.py (-nullrhi)", "B read-back": "smB_verify.py (-nullrhi)",
                  "C render + U2b": "smC_render.py (D3D12, -RenderOffscreen)", "E game world": "smE_game.py (-game, D3D12, -RenderOffscreen)",
                  "D analysis": "smD_analyse.py (Blender)", "F summary": "smF_summary.py"},
       "status": "pass" if not failed else "fail", "engine_verified": not failed and gates[0]["pass"] and gates[1]["pass"],
       "failed": failed, "issues": issues, "findings": findings, "sha256": START, "gates": gates}
(HERE / "verification_summary.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print("STATUS", out["status"], "gates", len(gates), "failed:", failed)
