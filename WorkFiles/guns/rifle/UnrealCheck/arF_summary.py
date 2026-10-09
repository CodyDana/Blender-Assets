"""AR-01 stage 8: the verification summary (plain Python). Reads every pass record of this harness and writes
WorkFiles/guns/rifle/UnrealCheck/verification_summary.json with one row per RIFLE_BUILD_PLAN 10.2 / GUN_BUILDING_STUDY
7.4 gate (name, value, threshold, pass). Promoted to "engine-verified" only when the bytes every pass used are the
shipped bytes and the bytes the stage-5 / 6 gates recorded.

    py -3 -B WorkFiles/guns/rifle/UnrealCheck/arF_summary.py
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
import ar_common as C  # noqa: E402

W = C.ROOT / "WorkFiles" / "guns" / "rifle"


def j(name):
    p = HERE / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


A, A2, B, CR, D, E = (j(n) for n in ("arA_import.json", "arA2_level.json", "arB_verify.json", "arC_render.json",
                                     "arD_analysis.json", "arE_game.json"))
START = j("SHA256_at_start.json")
SC = C.sidecar_sk()
gates = []
issues = []


def gate(name, value, threshold, ok, note=None, kind="gate"):
    g = {"name": name, "value": value, "threshold": threshold, "pass": bool(ok)}
    if note:
        g["note"] = note
    if kind != "gate":
        g["kind"] = kind
    gates.append(g)
    return ok


def qangle(q):
    return math.degrees(2 * math.acos(min(1.0, abs(q[3]))))


# ---------------------------------------------------------------- bytes
def assets(h):
    """The shipped asset bytes (the two READMEs are documentation, edited after the passes)."""
    return {k: v for k, v in (h or {}).items() if not k.endswith(".md")}


now = C.all_hashes()
same = {k: assets((r or {}).get("hashes_before")) == assets(START) and assets((r or {}).get("hashes_after")) == assets(START)
        for k, r in (("A", A), ("A2", A2), ("B", B), ("C", CR))}
gate("bytes: every pass used the shipped bytes (sha256 of every asset file before and after passes A, A2, B, C)",
     {"files": len(assets(START)), "unchanged_per_pass": same, "now_equal_start": assets(now) == assets(START)},
     "all equal", all(same.values()) and assets(now) == assets(START))
rig = json.loads((W / "scratch" / "rig" / "rig_report.json").read_text())
rec = {f.split("/")[-1]: r["sha256"] for f, r in rig["files"].items()}
mism = [k for k, v in rec.items() if START.get(k) not in (None, v) and k in START]
mag = json.loads((W / "gates" / "mag.json").read_text())
m7 = next(g for g in mag["gates"] if g["name"].startswith("M7"))["value"]
gate("bytes = the stage-5 / 6 gated bytes (rig_report files, mag.json M7)",
     {"stage5_files": len(rec), "mismatch": mism, "SM_AR01_Mag.fbx": START["SM_AR01_Mag.fbx"] == m7.get("mag")},
     "equal", not mism and START["SM_AR01_Mag.fbx"] == m7.get("mag"))

# ---------------------------------------------------------------- import
gate("pass A import (fresh process; legacy FBX importer, the README / sidecar settings)",
     {"status": A["status"], "lods_SK": A["lod_count_after_import"], "clips": len(A["steps"]["animations"]),
      "sockets_SK": len(A["steps"]["sockets"]) if isinstance(A["steps"]["sockets"], list) else A["steps"]["sockets"],
      "physics": A["steps"]["physics"].get("asset") if isinstance(A["steps"]["physics"], dict) else None,
      "textures": len(A["textures"])}, "ok", A["status"] == "ok")

# ---------------------------------------------------------------- U1 / U2 / U3
u1 = D["U1"]
gate("U1 skeleton: names, parents, reference heads (<= 0.001 cm), root scale 1, axes (muzzle +X, up +Z, right +Y)",
     {k: u1[k] for k in ("mesh_bones", "names_match", "parents_match", "max_head_err_cm", "root_scale_1",
                         "max_bone_rest_rotation_deg", "axes")}, "all true; head err <= 0.001 cm", u1["pass"])
u2 = B["U2"]
bolt = u2["bolt_back_10.325cm"]
dv = np.array(bolt["got_component"][:3]) - np.array(bolt["ref_component"][:3])
sel = {}
for k in ("selector_16deg_about_Y", "selector_32deg_about_Y"):
    r = u2[k]
    q = np.array(r["got_component"][3:7])
    ax = q[:3] / max(np.linalg.norm(q[:3]), 1e-12)
    sel[k] = {"angle_deg": round(qangle(q), 4), "axis": ax.round(6).tolist(),
              "head_moved_cm": float(np.abs(np.array(r["got_component"][:3]) - np.array(r["ref_component"][:3])).max())}
ok2 = (np.abs(dv - [-10.325, 0, 0]).max() <= 1e-3 and all(abs(abs(v["axis"][1]) - 1) < 1e-6 and v["head_moved_cm"] < 1e-6
                                                          for v in sel.values())
       and abs(sel["selector_16deg_about_Y"]["angle_deg"] - 16) < 1e-3 and abs(sel["selector_32deg_about_Y"]["angle_deg"] - 32) < 1e-3)
gate("U2 procedural (engine pose maths, bone-space offsets): bolt -X moves straight back; selector turns about its pin",
     {"bolt_component_motion_cm": dv.round(6).tolist(), "selector": sel}, "bolt (-10.325, 0, 0) +- 0.001 cm; selector about Y "
     "(the sidecar's transverse pin; the study's generic 'about X' does not apply to this pattern), angle +- 0.001 deg", ok2)
u3 = D["U3"]
gate("U3 sockets on SK_AR01: from the sidecar, on the right bones, scale 1, outered to the asset, fresh process",
     {"count": len(u3["sockets"]), "worst_loc_cm": u3["worst_loc_cm"], "worst_rot_deg": u3["worst_rot_deg"], "extra": u3["extra"]},
     "17; <= 0.001 cm / 0.001 deg; no extras", u3["pass"] and len(u3["sockets"]) == 17)
for nm, n_exp in (("SM_AR01", 17), ("SM_AR01_Mag", 5)):
    r = B[nm]
    sc = r["sidecar_compare"]
    vals = [v for v in sc.values() if isinstance(v, dict)]
    gate(f"sockets on {nm} (sidecar, fresh process)", {"count": len(r["sockets"]), "worst_loc_cm": max(v["max_loc_err_cm"] for v in vals),
                                                     "worst_rot_deg": max(v["max_rot_err_deg"] for v in vals),
                                                     "extra": r["sidecar_extra_sockets"], "missing": [k for k, v in sc.items() if not isinstance(v, dict)]},
         f"{n_exp}; <= 0.001 cm / 0.001 deg; scale 1; outer = asset; no extras",
         len(vals) == n_exp and not r["sidecar_extra_sockets"] and all(v["max_loc_err_cm"] <= 1e-3 and v["max_rot_err_deg"] <= 1e-3
                                                                       and v["scale1"] and v["outer_is_asset"] for v in vals))

# ---------------------------------------------------------------- U5 LODs, triangles, sizes, bounds
tri = D["triangles"]
gate("U5 LOD count 4 (SK_AR01, SM_AR01, SM_AR01_Mag)",
     {"SK": len(B["sk_lods"]), "SM": B["SM_AR01"]["num_lods"], "Mag": B["SM_AR01_Mag"]["num_lods"]}, "4 each",
     len(B["sk_lods"]) == 4 and B["SM_AR01"]["num_lods"] == 4 and B["SM_AR01_Mag"]["num_lods"] == 4)
gate("U5 triangles per LOD equal in Blender, the FBX and Unreal (render data, mesh description, Unreal's FBX export)",
     tri, "equal per LOD", all(r["equal"] for rows in tri.values() for r in rows))
sks = B["sk_lod_settings"]["screen_sizes"] if isinstance(B["sk_lod_settings"], dict) else None
gate("screen sizes from the sidecars (SK LOD settings, SM, Mag)",
     {"SK": sks, "SK_sidecar": SC["lod_screen_sizes"], "SM": B["SM_AR01"]["lod_screen_sizes"], "SM_sidecar": B["SM_AR01"]["sidecar_lod_screen_sizes"],
      "Mag": B["SM_AR01_Mag"]["lod_screen_sizes"], "Mag_sidecar": B["SM_AR01_Mag"]["sidecar_lod_screen_sizes"]},
     "equal (1e-6)", sks is not None and max(abs(a - b) for a, b in zip(sks, SC["lod_screen_sizes"])) < 1e-6
     and B["SM_AR01"]["lod_screen_sizes"] == B["SM_AR01"]["sidecar_lod_screen_sizes"]
     and B["SM_AR01_Mag"]["lod_screen_sizes"] == B["SM_AR01_Mag"]["sidecar_lod_screen_sizes"])
ms = D["mag_screen_sizes"]
gate("mag screen sizes re-derived from the engine bounds (plan 2.4: size_rifle x r_mag / r_rifle)", ms, "<= 0.001 from the sidecar",
     ms["max_diff"] <= 1e-3)
be = SC["import"]["bounds_extension_cm"]
u5 = D["U5_bounds"]
outside = sum(v["vertices_outside"] for v in u5["clips"].values())
gate("U5 bounds: the stored bounds (+ the sidecar extension) hold every LOD0-3 vertex at every runtime frame of every clip",
     {"extension_applied": {"pos": B["sk_bounds"]["pos_ext"], "neg": B["sk_bounds"]["neg_ext"], "sidecar": [be["positive_cm"], be["negative_cm"]]},
      "vertices_outside": outside, "per_clip": u5["clips"], "by_bone": u5.get("by_bone")}, "0 outside", outside == 0)

# ---------------------------------------------------------------- U6 / M9
u6 = D["U6_M9"]
rest = u6["rest"]
gate("U6 magazine at Mag (engine attach, SnapToTarget, gun at an arbitrary world transform): composed transform zero",
     {"attached_vs_socket_cm": rest["attached_vs_socket_cm"], "rot": rest["attached_vs_socket_rot"],
      "relative_to_socket": rest["relative_to_socket"][:7], "socket_vs_sidecar_cm": rest["socket_vs_sidecar_cm"],
      "reload_frames_attached_vs_socket": {k: v["attached_vs_socket_max"] for k, v in u6["reload_frames"].items()}},
     "<= 0.001 cm, identity", rest["attached_vs_socket_cm"] <= 1e-3 and rest["attached_vs_socket_rot"] <= 1e-6
     and rest["socket_vs_sidecar_cm"] <= 1e-3 and all(v["attached_vs_socket_max"] <= 1e-3 for v in u6["reload_frames"].values()))
seat = u6["seated_intersecting_pairs"]
gate("M9 seated fit on the read-back geometry (co-visible LOD0 / LOD1 pairs; LOD2 / LOD3 reported as mag.json M1 does)",
     seat, "0 at LOD0 and LOD1", seat["rifle LOD0 / mag LOD0"] == 0 and seat["rifle LOD1 / mag LOD1"] == 0)
rp = u6["rock_path"]
gate("M9 reload path from the engine sockets (insert 0.5 mm, rock 0.25 deg about the front-lug hook) on the read-back geometry",
     {k: rp[k] for k in ("insert_mm", "rock_deg", "hook_point_cm", "axis", "rock_end_vs_Mag_cm")} |
     {"pairs": {k: {"steps": v["steps"], "intersecting_steps": len(v["intersecting_steps"])} for k, v in rp["pairs"].items()}},
     "0 intersecting steps at LOD0 / LOD1; ends on Mag", all(not v["intersecting_steps"] for v in rp["pairs"].values())
     and rp["rock_end_vs_Mag_cm"] <= 1e-3)
gate("U6 reload clips in engine: the magazine on the posed rifle at every runtime frame (LOD0)",
     {k: {"frames": v["frames"], "frames_with_intersections": v["frames_with_intersections"]} for k, v in u6["reload_frames"].items()},
     "0 frames", all(not v["frames_with_intersections"] for v in u6["reload_frames"].values()))

# ---------------------------------------------------------------- U7 physics
ph = B["sk_physics"] or {}
body = (ph.get("bodies") or {}).get("body", {})
kinds = sorted(e["shape"] for e in body.get("elements", []))
gate("PHYS_AR01: one body on 'body', the sidecar's 7 boxes + 1 capsule, 3.1 kg, fresh process",
     {"bodies": sorted((ph.get("bodies") or {}).keys()), "shapes": kinds, "mass_kg": body.get("mass_kg"), "override": body.get("override_mass")},
     "1 body; 7 box + 1 capsule; 3.1 kg", sorted((ph.get("bodies") or {}).keys()) == ["body"] and kinds.count("box") == 7
     and kinds.count("capsule") == 1 and abs((body.get("mass_kg") or 0) - 3.1) < 1e-4)
u7v = D.get("U7_vertices")
if E and u7v:
    gate("U7 physics in a ticking game world: SM_AR01 (level, rolled 70 deg), SM_AR01_Mag and SK_AR01 (PHYS_AR01) dropped 1 m "
         "rest on their collision, no tunnelling (read-back LOD0 placed at every sampled transform)",
         u7v, "speed < 1 cm/s over the last 1 s; lowest vertex never < -2 cm, final >= -0.5 cm (ground top 0)",
         all(v["rests"] and v["no_tunnelling"] for v in u7v.values()) and len(u7v) == 4)
else:
    gate("U7 physics in a ticking game world", None, "measured", False, "pass E did not run")

# ---------------------------------------------------------------- U8 statics, textures
lm = {nm: {"index": B[nm]["light_map_coordinate_index"],
           "generated": [b["generate_lightmap_u_vs"] and b["src_lightmap_index"] == 0 and b["dst_lightmap_index"] == 1
                         for b in B[nm]["lod_build_settings"]], "uv_channels": B[nm]["uv_channels_per_lod"]}
      for nm in ("SM_AR01", "SM_AR01_Mag")}
gate("U8 lightmap: index 1, UV1 generated (0 -> 1) on every LOD", lm, "index 1; generated on 4 / 4 LODs",
     all(v["index"] == 1 and all(v["generated"]) and len(v["generated"]) == 4 for v in lm.values()))
uv1 = D["uv1"]
gate("U8 the GENERATED UV1 (Unreal's export): inside 0..1, overlap 0 (strict-interior pixel test at 1024; 64 / 256 / 2048 reported)",
     {k: {kk: v[kk] for kk in ("inside_0_1", "overlap_px_64", "overlap_px_256", "overlap_px_1024", "overlap_px_2048")} for k, v in uv1.items()},
     "inside; 0 px at 1024", all(v["inside_0_1"] and v["overlap_px_1024"] == 0 for v in uv1.values()))
want = {"BC": ("True", "TC_DEFAULT", "TEXTUREGROUP_WEAPON"), "ORM": ("False", "TC_MASKS", "TEXTUREGROUP_WEAPON"),
        "N": ("False", "TC_NORMALMAP", "TEXTUREGROUP_WEAPON_NORMAL_MAP"), "Masks": ("False", "TC_MASKS", "TEXTUREGROUP_WEAPON"),
        "Detail16": ("False", "TC_GRAYSCALE", "TEXTUREGROUP_WEAPON")}
bad = {}
for n, t in B["textures"].items():
    k = "Detail16" if n.endswith("Detail16") else n.rsplit("_", 1)[-1]
    s_, c_, g_ = want[k]
    ok = t["srgb"] == s_ and c_ in t["compression_settings"] and g_ in t["lod_group"] and (k != "N" or t["flip_green_channel"] == "False")
    if not ok:
        bad[n] = t
gate("texture flags persisted (fresh process): BC sRGB TC_Default, ORM / Masks linear TC_Masks, N TC_Normalmap flip-green off "
     "(group WeaponNormalMap), Detail16 linear Grayscale; groups Weapon", {"textures": len(B["textures"]), "wrong": bad}, "all", not bad)
log = (HERE / "arC_render.log").read_text(errors="ignore")
mips = {}
for m in re.finditer(r"\]\s*(\d+)x(\d+) \([^)]*\), (\d+)x(\d+) \([^)]*\), (PF_\w+), (\w+), (/Game/[^,]+), \w+, \w+, \w+, \d+, (\d+), \w+", log):
    name = m.group(7).split(".")[-1]
    if "AR01" in name:
        mips[name] = {"size": int(m.group(1)), "format": m.group(5), "group": m.group(6), "mips": int(m.group(8))}
full = {n: v["mips"] == int(math.log2(v["size"])) + 1 for n, v in mips.items()}
gate("full mip chains (ListTextures, real RHI): 13 at 4096, 12 at 2048, 11 at 1024, 10 at 512; Detail16 builds PF_G16",
     mips, "all full; Detail16 PF_G16", len(mips) == len(B["textures"]) and all(full.values())
     and mips.get("T_AR01_Furniture_Detail16", {}).get("format") == "PF_G16")

# ---------------------------------------------------------------- U9 clips
u9 = D["U9"]
ok9 = True
for k, v in u9.items():
    sc_frames = next(a["frames"][1] for a in SC["animations"] if a["file"].startswith(k))
    held = {b for b in v["end_vs_bind_mm"] if b != "selector"}
    ok9 &= (v["engine_num_frames"] == sc_frames and v["max_runtime_vs_raw_mm"] <= 0.1 and v["max_raw_vs_authored_mm"] <= 0.01
            and v["end_vs_start_mm"] <= 0.01 and not held and v["notifies_ok"] and "DefaultRecorderBoneCompression" in v["compression"])
gate("U9 clips: frames = the sidecar's; engine-evaluated runtime (compressed) vs raw <= 0.1 mm on every rigid part; raw = the "
     "authored clip; end pose = start pose (= bind except the selector held at Auto, README); every sidecar notify on its frame "
     "(+-0.5), no extras", {k: {kk: vv for kk, vv in v.items() if kk not in ("notifies",)} for k, v in u9.items()},
     "as stated", ok9)

# ---------------------------------------------------------------- U10 warnings
warn = {}
for nm in ("arA_import.log", "arA2_level.log", "arB_verify.log", "arC_render.log", "arE_game.log"):
    p = HERE / nm
    if not p.exists():
        continue
    lines = [l.strip()[:220] for l in p.read_text(errors="ignore").splitlines()
             if re.search(r"(Warning|Error):", l) and re.search(r"AR01|GunCheck|SK_|SM_|A_AR01|PHYS_|T_AR01|Notifies", l)
             and "DeprecationWarning" not in l and "LogInit: Display" not in l]
    warn[nm] = {"count": len(lines), "lines": sorted(set(lines))[:12]}
gate("U10 0 warning / error lines from the assets in every pass log", warn, "0", all(v["count"] == 0 for v in warn.values()))

# ---------------------------------------------------------------- U12 residency
u12 = {}
elog = (HERE / "arE_game.log").read_text(errors="ignore") if (HERE / "arE_game.log").exists() else ""
for view in ("hip", "ads"):
    blk = re.search(rf"AR_STREAM_BEGIN {view}(.*?)AR_STREAM_END {view}", elog, re.S)
    if not blk:
        continue
    for m in re.finditer(r"Texture2D (/Game/[^\s]+)\s*\n[^\n]*Current=(\d+)x\d+\s+Wanted=(\d+)x\d+ MaxAllowed=(\d+)x\d+", blk.group(1)):
        n = m.group(1).split(".")[-1]
        if "AR01" in n:
            u12.setdefault(view, {})[n] = {"current": int(m.group(2)), "wanted": int(m.group(3)), "max": int(m.group(4))}
gun = [n for n in ("T_AR01_Metal_BC", "T_AR01_Metal_N", "T_AR01_Furniture_BC", "T_AR01_Furniture_N")]
ok12 = bool(u12) and all(u12.get(v, {}).get(n, {}).get("current") == u12.get(v, {}).get(n, {}).get("max") for v in ("hip", "ads") for n in gun)
gate("U12 texture residency in a ticking game world (streaming on): the gun's BC and N resident at the top mip at the hip "
     "(35 cm, 90 deg) and at ADS (Sight eye, 55 deg)", u12, "current = max for Metal / Furniture BC and N at both views", ok12,
     "the magazine's own maps are reported (a separate mesh: at the hip it streams one mip lower)")

# ---------------------------------------------------------------- C2, hulls, slots, nanite
c2 = D["C2"]
gate("C2 every LOD0 surface sample (300k + every vertex) of the read-back geometry inside the stored hulls", c2,
     "0 outside", all(v["outside_gt_0.001cm"] == 0 for v in c2.values()))
hs = D["hull_shells"]
gate("hulls stored: SM_AR01 7, SM_AR01_Mag 2, <= 32 vertices each (Unreal's own export split into shells)",
     {**hs, "pass_B_convex_elems": {"SM_AR01": B["SM_AR01"]["convex_elems"], "SM_AR01_Mag": B["SM_AR01_Mag"]["convex_elems"]}},
     "7 + 2; <= 32", hs["SM_AR01"]["count"] == 7 and hs["SM_AR01_Mag"]["count"] == 2 and B["SM_AR01"]["convex_elems"] == 7
     and B["SM_AR01_Mag"]["convex_elems"] == 2 and max(hs["SM_AR01"]["vertices"] + hs["SM_AR01_Mag"]["vertices"]) <= 32)
slots = {"SK_AR01": [s["slot"] for s in B["sk_slots"]], "SM_AR01": [s["slot"] for s in B["SM_AR01"]["material_slots"]],
         "SM_AR01_Mag": [s["slot"] for s in B["SM_AR01_Mag"]["material_slots"]]}
gate("material slots (2 + 3 + 1, sidecar names); Nanite off", {"slots": slots, "nanite": {"SM_AR01": B["SM_AR01"]["nanite"], "SM_AR01_Mag": B["SM_AR01_Mag"]["nanite"]}},
     "SK [Metal, Furniture], SM [Metal, Furniture, Mag], Mag [Mag]; nanite false",
     slots == {"SK_AR01": ["M_AR01_Metal", "M_AR01_Furniture"], "SM_AR01": ["M_AR01_Metal", "M_AR01_Furniture", "M_AR01_Mag"],
               "SM_AR01_Mag": ["M_AR01_Mag"]} and B["SM_AR01"]["nanite"] is False and B["SM_AR01_Mag"]["nanite"] is False)

# ---------------------------------------------------------------- U4 first person
u4 = CR.get("U4", {})
try:
    from PIL import Image
    rd = HERE / "renders"
    L = lambda n: np.asarray(Image.open(rd / f"{n}.png").convert("RGB")).astype(float).mean(2)
    G, M = L("u4_ground_only"), L("u4_tp_noshadow")
    gun_mask = np.abs(M - G) > 6
    shadow = {n: int(((L(n) - G < -0.25 * np.maximum(G, 1)) & ~gun_mask).sum()) for n in ("u4_tp", "u4_none", "u4_fp")}
    I = {n: np.asarray(Image.open(rd / f"u4_lod_{n}.png").convert("RGB")).astype(float) for n in ("ref0", "ref3", "tp_auto", "fp_forced")}
    dpx = lambda a, b: int((np.abs(I[a] - I[b]).sum(2) > 30).sum())
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
     "'the owner sees no TP component' needs a possessed player pawn carrying the components (a weapon Blueprint: plan "
     "section 11, game-side, needs the user's go); Python cannot add components or spawn actors in a game world, so it is "
     "not measured here")
issues.append("U4: 'owner sees no TP component' is not measured (needs the weapon Blueprint on a possessed pawn: game-side "
              "integration, plan 11).")
gate("U11 hand fit in engine", None, "if the player body is available", True,
     "not run: MH_PlayerDefault is not in the verification project and the posed H1 (hand_r frame) it would reproduce has not "
     "been run (sidecar gun.hand_offset 'identity (provisional)')", kind="not_applicable")
issues.append("U11 not run: no MH_PlayerDefault in the verification project and no posed H1 baseline to reproduce.")

failed = [g["name"] for g in gates if not g["pass"]]
findings = [
    {"gate": "U5 triangles equal / U10",
     "cause": "Unreal 5.8's static FBX import (Remove Degenerates, the default) drops every triangle with |cross|^2 < 1e-8 "
              "cm^4 (area < 0.005 mm^2; FbxStaticMeshImport.cpp GetTriangleAreaThreshold). gunlib.tspace.unreal_drops() "
              "predicts exactly Unreal's counts: SM_AR01 4,584 / 580 / 122 / 0 and SM_AR01_Mag 772 / 33 / 0 / 0 of LOD0-3 "
              "(the skeletal import keeps them: SK_AR01 has 3,812 / 547 / 122 / 0 such triangles). They are micro bevel and "
              "boolean run-out strips (4-25 microns wide) made by the part generators, plus decimation slivers at LOD1-2.",
     "effect": "triangle counts differ Blender / FBX vs Unreal; hairline cracks where the strips were (sub-pixel)"},
    {"gate": "U10",
     "cause": "'nearly zero tangents / bi-normals' (SM_AR01, SM_AR01_Mag) and 'degenerate tangent bases' (SM_AR01): "
              "StaticMeshBuild.cpp HasBadNTB on the render data. Unreal's exported render data (ASCII FBX) located them: "
              "20 / 44 / 24 / 1 zero tangents on SM_AR01 LOD0-3 and 6 / 4 / 1 / 0 on SM_AR01_Mag; tangent = normal on "
              "12 / 63 / 26 SM_AR01 LOD1-3 vertices. Causes: needle corners of the micro strips (float32 angle weight 0), "
              "faces seen edge-on by their shading normal, and LOD faces whose UV collapsed onto a line / point (island "
              "snapping).",
     "effect": "normal-map shading wrong at those few vertices (sub-pixel strips; LOD1-3 snapped faces)"},
    {"gate": "fix attempts (stage 8, generator side)",
     "result": "gunlib.tspace.unreal_safe (collapse micro edges, split needles, re-UV degenerate faces, tilt edge-on corner "
               "normals) made the test meshes import with 0 warnings, 0 dropped triangles and 0 zero tangents (TVB "
               "variants, ar_tan_ue.log), but as an export step it opened 3-face edges (qa_skeletal edge_manifold), moved "
               "vertices up to ~1 mm, pushed UVs out of their tile (uv0_inside_0_1) and multiplied the generated-lightmap "
               "overlaps (LOD0 85 -> 2,718 px at 1024); applied to the parts it broke G5 (butt gap 0.0074 mm, 3 LOD1 "
               "pairs) and the LOD-share targets (LOD0 shrank 8 %). A link-checked live-bmesh variant does not converge. "
               "Everything was reverted; the shipped bytes are the stage-7 geometry.",
     "recommendation": "change the method: remove the micro strips where the part generators make them (minimum bevel "
                       "segment and boolean sliver >= 0.05 mm, triangles >= 0.01 mm^2, checked by unreal_drops() == 0 as "
                       "a form-stage gate), and give LOD faces non-degenerate UVs at the LOD UV stage; then re-run stages "
                       "2-8."},
    {"gate": "U8 generated UV1 overlap",
     "cause": "Unreal's FLayoutUV output overlaps on this many-chart mesh: at the lightmap's own 64 px SM_AR01 LOD1-3 "
              "overlap 1 / 3 / 4 texels (LOD0 0), at 1024 px 85 / 77 / 53 / 53 (mag LOD0-1 22 / 190); the shipped UV0 and "
              "UV1 have 0 overlapping triangles (SAT test, lodfix.overlap_pairs). Higher minimum lightmap resolutions "
              "(256-1024) and full-precision UVs reduce but do not remove it (lmtest/).",
     "recommendation": "decide the lightmap route for static-lit buyers (plan R12): the authored UV1 with Generate "
                       "Lightmap UVs off measured fewer overlaps (LOD0 11 px at 1024) but not zero either"},
    {"gate": "U5 bounds",
     "cause": "LOD2 is 2.78 mm wider on the left than LOD0's bind box (fix log N4); the sidecar extension was computed on "
              "LOD0 only. Fixed in rifle_rig.posed_envelope (LOD0-3) and re-exported in this stage (see U5 bounds row)."},
]
out = {"stage": "8 Unreal (UE 5.8, RIFLE_BUILD_PLAN 10.2 + GUN_BUILDING_STUDY 7.4)",
       "engine": (A or {}).get("engine"), "content_path": C.dest(),
       "project": "WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject (the katana's verification project)",
       "passes": {"A import": "arA_import.py (-nullrhi)", "A2 check level": "arA2_level.py (-nullrhi)",
                  "B read-back": "arB_verify.py (-nullrhi)", "C render": "arC_render.py (D3D12, -RenderOffscreen)",
                  "E game world": "arE_game.py (-game, D3D12, -RenderOffscreen)", "D analysis": "arD_analyse.py (Blender)"},
       "status": "pass" if not failed else "fail", "engine_verified": not failed and gates[0]["pass"] and gates[1]["pass"],
       "failed": failed, "issues": issues, "findings": findings, "sha256": START, "gates": gates}
(HERE / "verification_summary.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print("STATUS", out["status"], "failed:", failed)
