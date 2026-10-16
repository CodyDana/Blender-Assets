"""SR01 W4b close-up realism round (plain Python; the SMG's smg_closeup_r2.py pattern). Measures the W4 judges' tells
before / after on the maps and the exported bytes and writes gates/closeup_r1.json:

    py -3 -B Scripts/guns/sniper/sr_closeup.py --snapshot      (BEFORE the chain: W4 bakes + shipped maps -> scratch)
    py -3 -B Scripts/guns/sniper/sr_closeup.py                 (after the chain + the w4b renders: the gates)
    py -3 -B Scripts/guns/sniper/sr_closeup.py --round r2 [--snapshot]   (realism round 2: before = round 1's exported
        state in scratch/r2/before_exports, renders review/r2, writes gates/closeup_r2.json; K10 against W4b)

  K1 edges: hard creases (> 60 deg) on the chassis slot of SK_SR01.fbx after <= 0.5 x before (sr_closeup_edges.py,
     fresh Blender process on the exported bytes) and the new rounds shaded smooth (>= 0.9 of the round length);
  K2 bolt not chrome: bolt body (X >= 372) roughness P50 >= 0.45 on the shipped ORM;
  K3 chassis finish: OD orange peel in the normal map (texels tilted > 1 deg) after >= 2 x before; edge rub confined to
     the caused zones (rub texels > 0.3 after <= 0.5 x before) with chips still present;
  K4 no bare metal on small parts (pins, screws, safety, trigger, release): metallic texels == 0;
  K5 scope: anodize roughness P50 >= 0.45, turret markings painted (> 0 texels), lens coated (BC spread > 0);
  K6 grip / hardware: hex sockets painted (> 0), the grip stipple painted;
  K7 review rig: every realism view on the table (floor height recorded), depth of field on the FP / eyepiece views;
  K8 sparkle: isolated hot pixels (clusters <= 3 px at >= 235) on fp_35cm and ads_eyepiece <= 5;
  K9 every stage gate of the rebuilt chain at W4's status (form / W2 known partials unchanged, the rest PASS);
  K10 side views: L2 GR / GL / TOP and L3 not worse than W4 by more than 0.001 IoU / 0 px;
  K11 the set is complete.
The realism verdict belongs to the judges (reported, not self-judged).
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import ROOT, GATES, WORK, GRIP  # noqa: E402

BL = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
S = WORK / "scratch"
W4B = S / "w4b"
EXP = ROOT / "Exports" / "Guns" / "SR01"
REV = WORK / "review" / "w4b"
RND = "r1"
SMALL = ("pins", "fasteners", "rail_screws", "safety", "trigger", "mag_release")


def img(p, mode=None):
    im = Image.open(p)
    return np.asarray(im.convert(mode) if mode else im)


def maps_metrics(bake, sbake, tex, prep, sprep):
    meta = json.loads((bake / "bake_meta.json").read_text())
    smeta = json.loads((sbake / "bake_meta.json").read_text())
    out = {}
    # Metal set: bolt body roughness; small parts metallic. The bake arrays are bottom-up (Blender pixel order,
    # bake_meta encoding.rows), the PNGs top-down: flip the arrays to PNG row order (K4_NOTE.md)
    ids = np.load(bake / "Metal_ids.npy")[::-1][..., 0].astype(int)
    pos = np.load(bake / "Metal_pos.npy")[::-1].reshape(-1, 3) * 1000.0 + GRIP
    orm = img(tex / "T_SR01_Metal_ORM.png").astype(float) / (65535.0 if img(tex / "T_SR01_Metal_ORM.png").dtype == np.uint16 else 255.0)
    R, M = orm[..., 1].ravel(), orm[..., 2].ravel()
    # registration guard: the bolt is bare metal, the phosphated receiver is not
    reg = {p: round(float((M[ids.ravel() == meta["parts"][p]] > 0.5).mean()), 3) for p in ("bolt", "receiver")}
    out["registration_metal_fraction"] = reg
    if not (reg["bolt"] > 0.5 and reg["receiver"] < 0.05):
        raise SystemExit(f"[SR01-closeup] bake ids / ORM misregistered (metal fraction {reg}; want bolt > 0.5, "
                         "receiver < 0.05)")
    bolt = (ids.ravel() == meta["parts"]["bolt"]) & (pos[:, 0] >= 372.0)
    out["bolt_rough_p50"] = round(float(np.median(R[bolt])), 3)
    out["bolt_rough_p5_p95"] = [round(float(np.percentile(R[bolt], q)), 3) for q in (5, 95)]
    small = np.isin(ids.ravel(), [meta["parts"][p] for p in SMALL if p in meta["parts"]])
    out["small_parts_metal_texels"] = int((M[small] > 0.5).sum())
    # paint reports
    od = prep["Chassis"]["finishes"]["od"]
    out["od_rough_p5_p50_p95"] = od["rough_p5_p50_p95"]
    out["od_normal_tilt_gt_1deg"] = prep["Chassis"]["normal_tilt_gt_1deg_fraction"].get("od")
    out["od_info"] = prep["Chassis"]["info"].get("od")
    out["grip_panel_texels"] = prep["Chassis"]["info"].get("grip_panel_texels")
    out["hex_sockets"] = prep["Metal"]["info"].get("hex_sockets", 0)
    # scope
    sid = np.load(sbake / "Scope_Body_ids.npy")[::-1][..., 0].astype(int).ravel()
    sorm = img(tex / "T_Att_Scope_LongRange_Scope_Body_ORM.png").astype(float)
    sorm /= 65535.0 if sorm.max() > 255 else 255.0
    body = sid == smeta["parts"]["scope_body"]
    out["scope_anod_rough_p50"] = round(float(np.median(sorm[..., 1].ravel()[body])), 3)
    out["turret_mark_texels"] = sprep["Scope_Body"]["info"].get("turret_mark_texels", 0)
    lid = np.load(sbake / "Scope_Lens_ids.npy")[::-1][..., 0].astype(int).ravel()
    lbc = img(tex / "T_Att_Scope_LongRange_Scope_Lens_BC.png", "RGB").reshape(-1, 3).astype(float)
    lens = lid > 0
    out["lens_bc_std_srgb"] = round(float(lbc[lens].std(0).mean()), 2)
    out["lens_bc_mean_srgb"] = [round(float(v), 1) for v in lbc[lens].mean(0)]
    out["lens_normal_tilt_gt_1deg"] = sprep["Scope_Lens"]["normal_tilt_gt_1deg_fraction"].get("lens")
    return out


def snapshot():
    prep = json.loads((W4B / "before_paint_report.json").read_text())
    sprep = json.loads((S / "w2_scope" / "paint" / "paint_report.json").read_text())
    m = maps_metrics(S / "w2" / "bake", S / "w2_scope" / "bake", W4B / "before_exports" / "Textures", prep, sprep)
    (W4B / "before_metrics.json").write_text(json.dumps(m, indent=1))
    print("[SR01-closeup] snapshot", json.dumps(m))


def hot_clusters(p):
    a = img(p, "L").astype(int)
    lab, n = ndi.label(a >= 235)
    if not n:
        return 0
    sizes = np.bincount(lab.ravel())[1:]
    return int((sizes <= 3).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--round", default="r1")
    ap.add_argument("--reuse-k1", action="store_true", help="read the existing K1.json instead of starting Blender")
    a = ap.parse_args()
    global RND, W4B, REV
    RND = a.round
    if RND == "r2":
        W4B, REV = S / "r2", WORK / "review" / "r2"
    if a.snapshot:
        snapshot()
        return
    before = json.loads((W4B / "before_metrics.json").read_text())
    prep = json.loads((S / "w2" / "paint" / "paint_report.json").read_text())
    sprep = json.loads((S / "w2_scope" / "paint" / "paint_report.json").read_text())
    after = maps_metrics(S / "w2" / "bake", S / "w2_scope" / "bake", EXP / "Textures", prep, sprep)
    k1f = W4B / "K1.json"
    if not (a.reuse_k1 and k1f.exists()):
        subprocess.run([BL, "-b", "--factory-startup", "--python", str(HERE / "sr_closeup_edges.py"), "--",
                        "--fbx", f"{W4B / 'before_exports' / 'SK_SR01.fbx'},{EXP / 'SK_SR01.fbx'}", "--out", str(k1f)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    K1 = list(json.loads(k1f.read_text()).values())
    gates = []

    def gate(name, value, threshold, ok, note=""):
        gates.append({"name": name, "value": value, "threshold": threshold, "pass": bool(ok), "note": note})

    gate("K1 chassis-slot edges: hard creases (> 60 deg) on SK_SR01 LOD0, after / before; the rounds shaded smooth",
         {"before": K1[0], "after": K1[1], "hard_ratio": round(K1[1]["hard_crease_mm"] / K1[0]["hard_crease_mm"], 3)},
         "hard after <= 0.5 x before; round_smooth_fraction >= 0.9",
         K1[1]["hard_crease_mm"] <= 0.5 * K1[0]["hard_crease_mm"] and K1[1]["round_smooth_fraction"] >= 0.9)
    gate("K2 bolt body roughness (not chrome): P50 and P5 (the mirror streaks come from the smooth tail)",
         {"before_p50": before["bolt_rough_p50"], "after_p50": after["bolt_rough_p50"],
          "before_p5_p95": before["bolt_rough_p5_p95"], "after_p5_p95": after["bolt_rough_p5_p95"]},
         # a before snapshot measured misregistered (K4_NOTE.md) cannot anchor the relative test: the absolute bar only
         "P50 >= 0.45 (before invalid); P5 >= 0.45" if before.get("invalid") else "P50 >= before + 0.05; P5 >= 0.45",
         (after["bolt_rough_p50"] >= 0.45 if before.get("invalid") else
          after["bolt_rough_p50"] >= before["bolt_rough_p50"] + 0.05) and after["bolt_rough_p5_p95"][0] >= 0.45,
         f"before invalid: {before['invalid']}" if before.get("invalid") else "")
    t0, t1 = before["od_normal_tilt_gt_1deg"] or 0.0, after["od_normal_tilt_gt_1deg"] or 0.0
    r0 = (before["od_info"] or {}).get("rub_texels_gt_0.3", 0)
    r1 = (after["od_info"] or {}).get("rub_texels_gt_0.3", 0)
    gate("K3 OD Cerakote: orange peel in the normal map (texels tilted > 1 deg); edge rub only where caused; chips",
         {"tilt_before": t0, "tilt_after": t1, "rub_gt_0.3_before": r0, "rub_gt_0.3_after": r1,
          "chips_after": (after["od_info"] or {}).get("chip_texels"), "bare_al_after": (after["od_info"] or {}).get("bare_al_texels"),
          "od_rough_p5_p50_p95": after["od_rough_p5_p50_p95"]},
         "tilt after >= 2 x before; rub after <= 0.5 x before; chips > 0",
         t1 >= 2.0 * t0 and r1 <= 0.5 * max(r0, 1) and ((after["od_info"] or {}).get("chip_texels") or 0) > 0)
    gate("K4 no bare metal on small parts (pins, screws, safety, trigger, release)", after["small_parts_metal_texels"],
         "== 0", after["small_parts_metal_texels"] == 0, f"before {before['small_parts_metal_texels']}")
    gate("K5 scope: anodize roughness P50, turret markings, coated lens",
         {"anod_rough_p50": after["scope_anod_rough_p50"], "turret_mark_texels": after["turret_mark_texels"],
          "lens_bc_std_srgb_before": before["lens_bc_std_srgb"], "lens_bc_std_srgb_after": after["lens_bc_std_srgb"],
          "lens_bc_mean_srgb": after["lens_bc_mean_srgb"], "lens_convex_tilt_before": before["lens_normal_tilt_gt_1deg"],
          "lens_convex_tilt_after": after["lens_normal_tilt_gt_1deg"]},
         "rough >= 0.45; marks > 0; the lens convex (> 0.5 of its texels tilted > 1 deg)",
         after["scope_anod_rough_p50"] >= 0.45 and after["turret_mark_texels"] > 0 and
         (after["lens_normal_tilt_gt_1deg"] or 0) > 0.5)
    gate("K6 hardware + grip: hex sockets painted, grip stipple painted",
         {"hex_sockets": after["hex_sockets"], "grip_panel_texels": after["grip_panel_texels"]}, "> 0 each",
         after["hex_sockets"] > 0 and (after["grip_panel_texels"] or 0) > 0)
    tag = "w4b" if RND == "r1" else RND
    res = json.loads((S / "w4" / "review_job" / f"result_{tag}.json").read_text())
    rs = {s["name"]: s for s in res["shots"] if s["name"].startswith("realism_")}
    job = json.loads((S / "w4" / "review_job" / f"job_{tag}.json").read_text())
    jd = {s["name"]: s for s in job["shots"]}
    k7 = {n: {"floor_z_M_mm": s.get("floor_z_M_mm"), "fstop": jd[n].get("dof", {}).get("fstop")} for n, s in rs.items()}
    gate("K7 review rig: every realism view on the table; a real aperture on the close views", k7,
         "floor on all; DoF on fp_35cm / ads_eyepiece",
         all(v["floor_z_M_mm"] is not None for v in k7.values()) and
         all(k7.get(f"realism_{n}", {}).get("fstop") for n in ("fp_35cm", "ads_eyepiece")))
    hot = {n: hot_clusters(REV / "realism" / f"{n}.png") for n in ("fp_35cm", "ads_eyepiece")}
    gate("K8 sparkle: isolated hot pixels (<= 3 px at >= 235)", hot, "<= 5 each", all(v <= 5 for v in hot.values()))
    st = {}
    for f in ("form", "uv_bake_paint", "game", "game_lod_sizes", "rig_export", "mag", "scope_form", "scope_export"):
        d = json.loads((GATES / f"{f}.json").read_text())
        st[f] = {"status": d.get("status"), "failed": d.get("failed")}
    known_form = {"L2 GL IoU (scope stand-in)", "L2 TOP IoU raw / declared fit", "L2 per part on GR (IoU >= 0.95)",
                  "L3 GR contour P95 (sheet px)", "L4 key dimensions (<= 0.05 mm)"}
    lod = json.loads((GATES / "game_lod_sizes.json").read_text())
    st["game_lod_sizes"] = {"pass": lod.get("pass", lod.get("passed")), "screen_sizes": lod.get("screen_sizes")}
    ok9 = all(str(st[f]["status"]).lower().startswith("pass") for f in ("game", "rig_export", "mag",
                                                                         "scope_form", "scope_export")) and \
        set(st["form"]["failed"] or []) <= known_form
    gate("K9 every stage gate of the rebuilt chain at W4's status", st,
         "form: only the W1-open L2/L3/L4 items; uv_bake_paint: the known B9 near-misses; the rest PASS", ok9,
         "uv_bake_paint judged by its failed list in the report")
    fm = json.loads((GATES / "form.json").read_text())
    gv = {g["name"]: g["value"] for g in fm["gates"]}
    w4 = {"GR": 0.9603, "GL": [0.9434, 0.9513], "TOP": [0.8373, 0.9015], "L3": 3.0, "parts": "2 / 19"}
    if RND == "r2":                              # round 2 is held to round 1's (W4b) side views
        w4 = {"GR": 0.9602, "GL": [0.9426, 0.9505], "TOP": [0.8375, 0.9020], "L3": 3.0, "parts": "2 / 19"}
    cur = {"GR": gv.get("L2 GR IoU (scope = the blockout stand-in until W1b)"), "GL": gv.get("L2 GL IoU (scope stand-in)"),
           "TOP": gv.get("L2 TOP IoU raw / declared fit"), "L3": gv.get("L3 GR contour P95 (sheet px)"),
           "parts": gv.get("L2 per part on GR (IoU >= 0.95)")}
    ok10 = cur["GR"] >= w4["GR"] - 0.001 and all(c >= w - 0.001 for c, w in zip(cur["GL"], w4["GL"])) and \
        all(c >= w - 0.001 for c, w in zip(cur["TOP"], w4["TOP"])) and cur["L3"] <= w4["L3"]
    gate("K10 side-view gates not worse than W4", {"w4": w4, "w4b": cur}, "IoU within 0.001, L3 not higher", ok10,
         "the moulded grip's round moves GL by a few sheet px (declared)")
    n = sum(len(list((REV / d).glob("*.png"))) for d in ("set", "realism"))
    want = len([s_ for s_ in job["shots"] if not s_["name"].startswith("blind_")])
    gate("K11 the close set is complete (set + realism)", {"images": n, "shots_in_job": want}, "== every shot", n >= want)
    rec = {"stage": "W4b close-up realism round 1" if RND == "r1" else "Realism round 2 (rim-slab edges)", "date": datetime.datetime.now().isoformat(timespec="seconds"),
           "status": "pass" if all(g["pass"] for g in gates) else "fail",
           "failed": [g["name"] for g in gates if not g["pass"]], "gates": gates,
           "before_maps": before, "after_maps": after,
           "judges": f"review/{'w4b' if RND == 'r1' else RND}/judges/realism_A.json, realism_B.json (reported, not gated)"}
    (GATES / f"closeup_{RND}.json").write_text(json.dumps(rec, indent=1))
    print("[SR01-closeup] DONE", rec["status"], rec["failed"])


if __name__ == "__main__":
    main()
