"""SMG01 W4b close-up realism pass, ROUND 2 (plain Python; renders via headless Blender, gunlib/export_review_job.py,
from the EXPORTED bytes: SK_SMG01.fbx + SM_SMG01_Mag.fbx on the magazine bone + the shipped textures):

    py -3 -B Scripts/guns/smg/smg_closeup_r2.py [--no-render]

Renders review/closeup_r2/: the judges' close views (fp_35cm, ads_55deg, hero_34, hero_34_folded, tp_3m) under the r2
realism rig (smg_review_export.STUDIO: the product set, spec R47), the same five under the L5 colour-calibration rig in
l5/, the three close-ups at ~21-24 cm (c1 rear sight + top rail, c2 receiver left, c3 front end), clay looks of the FP /
ADS foreground and the stock head under the r1 rig in diag/ (the shading of the curved stock top, before / after), and
before / after contacts against review/closeup_r1. Measures the judges' r1 tells and writes gates/closeup_r2.json:

  K1 shading follows the curved surfaces (the "banded, streaky ribbon" stock head): smg_curved_check.py on the r1 W2
     blend (scratch/SMG01_r1_head.blend, recovered from git) and on the current Assets/Guns/SMG01.blend: the
     area-weighted ratio shading spread / geometric spread over every curved region; after >= 0.85 (r1 ~0.1);
  K2 exposure: hero_34 receiver side, realism rig / L5 rig <= 1.3 (the "mid-grey clay" bar of r1);
  K3 material split (the maps): roughness P50 phosphate - polymer >= 0.20 with G20 (the sheet's albedo ratio) passing;
  K4 sparkle: isolated hot pixels (connected clusters of <= 3 px at >= 235) on fp_35cm, ads_55deg and c1 <= 5 (the
     "white hairline glints / slivers on random edges");
  K5 no bare steel on the sights or the selector (paint info sight_selector_bare_texels == 0);
  K6 wear present in the maps: polymer BC P99 - P50 >= 20 sRGB levels (r1: 13; edge rub, scuffs and specks);
  K7 every stage gate of the rebuilt chain passes;
  K8 the set is complete.
The realism verdict itself belongs to the judges (reported, not self-judged).
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, SCRATCH, REVIEW, GATES  # noqa: E402

import gunlib  # noqa: E402
import smg_review_export as R  # noqa: E402
import smg_closeup as C1  # noqa: E402

ROUND = 2
PREV = REVIEW / "closeup_r1"
BEFORE_CLAY = SCRATCH / "closeup_r2_before"
R1_BLEND = SCRATCH / "SMG01_r1_head.blend"
VIEWS = C1.VIEWS
CHAIN = C1.CHAIN
HEAD_CAM = {"name": "head_rearL", "eye": (120.0, 90.0, 120.0), "target": (235.0, 0.0, 15.0), "fov": 35.0}


def clay_shots(out, samples):
    """The r1 rig (STUDIO_R1) in the clay look: geometry and its shading only, comparable with the 'before' clays."""
    S = []
    for s in R.realism_shots(samples):
        if s["name"] in ("fp_35cm", "ads_55deg"):
            L = dict(R.STUDIO_R1, target_M=s["lights"]["target_M"], dist_m=s["lights"]["dist_m"])
            S.append(dict(s, out=str(out / f"{s['name']}.png"), lights=L, look="clay", samples=256, denoise=True,
                          note=s["note"].replace("[studio rig]", "[clay, r1 rig]")))
    cam = R.persp_look(np.array(HEAD_CAM["eye"]), np.array(HEAD_CAM["target"]), HEAD_CAM["fov"], (1600, 900))
    S.append({"name": "head_rearL", "out": str(out / "head_rearL.png"), "camera": cam, "look": "clay",
              "lights": dict(R.STUDIO_R1, target_M=list(HEAD_CAM["target"]), dist_m=0.8), "samples": 256,
              "denoise": True, "note": "the stock head and neck from behind-left-above (clay, r1 rig)"})
    return S


def contact(pairs, out, labels, w=760):
    ims = []
    for a, b, lab in pairs:
        A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
        h = int(w * A.height / A.width)
        ims.append((A.resize((w, h)), B.resize((w, h)), lab))
    H = sum(i[0].height + 24 for i in ims)
    Cc = Image.new("RGB", (2 * w + 10, H + 24), (255, 255, 255))
    d = ImageDraw.Draw(Cc)
    d.text((6, 4), labels[0], fill=(0, 0, 0))
    d.text((w + 16, 4), labels[1], fill=(0, 0, 0))
    y = 24
    for A, B, lab in ims:
        d.text((6, y + 4), lab, fill=(0, 0, 0))
        Cc.paste(A, (0, y + 20))
        Cc.paste(B, (w + 10, y + 20))
        y += A.height + 24
    Cc.save(out)


def curved_check(blend, out_json):
    if out_json.exists() and out_json.stat().st_mtime > blend.stat().st_mtime:
        return json.loads(out_json.read_text())
    subprocess.run([gunlib.BLENDER, "-b", "--factory-startup", str(blend), "--python",
                    str(HERE / "smg_curved_check.py"), "--", "--out", str(out_json)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return json.loads(out_json.read_text())


def sparkles(p):
    a = np.asarray(Image.open(p).convert("RGB")).max(-1) >= 235
    lab, n = ndi.label(a, structure=np.ones((3, 3), int))
    if not n:
        return 0, 0
    sz = np.bincount(lab.ravel())[1:]
    return int((sz <= 3).sum()), int(a.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    out = REVIEW / f"closeup_r{ROUND}"
    (out / "diag").mkdir(parents=True, exist_ok=True)
    R.REAL = out
    shots = [s for s in R.realism_shots(a.samples) if s["name"].replace("_l5", "") in VIEWS]
    shots += C1.close_shots(out, a.samples)
    clays = clay_shots(out / "diag", a.samples)
    if not a.no_render:
        R.run_job(f"closeup_r{ROUND}", shots + clays, a.samples)
    (out / "shots.json").write_text(json.dumps({"source": "EXPORTED bytes (SK_SMG01 + SM_SMG01_Mag + shipped textures "
                                                          "+ shipped clips)", "rig": R.STUDIO,
                                                "shots": [dict(s, out=R.rel(s["out"])) for s in shots + clays]},
                                               indent=1))
    R.contact([(s["out"], s["name"] + ": " + s["note"]) for s in shots if not s["name"].endswith("_l5")],
              out / "contact.png")
    contact([(PREV / f"{v}.png", out / f"{v}.png", v) for v in
             ["fp_35cm", "ads_55deg", "hero_34", "c1_rear_sight_rail", "c2_receiver_left", "c3_front_end"]],
            out / "before_after.png", ("BEFORE (W4b close-up r1, R46)", "AFTER (W4b close-up r2, R47)"))
    contact([(BEFORE_CLAY / f"{v}.png", out / "diag" / f"{v}.png", v) for v in ["fp_35cm", "ads_55deg", "head_rearL"]],
            out / "diag" / "clay_before_after.png",
            ("BEFORE (r1 bytes, clay): curved tops flattened into bands", "AFTER (r2 bytes, clay): smooth curved shading"))

    G = []

    def gate(name, value, threshold, ok, note=""):
        G.append({"name": name, "value": value, "threshold": threshold, "pass": bool(ok), "note": note})
    cb = curved_check(R1_BLEND, BEFORE_CLAY / "curved_check_r1.json")
    ca = curved_check(ROOT / "Assets" / "Guns" / "SMG01.blend", SCRATCH / "curved_check_r2.json")
    gate("K1 shading follows the curved surfaces: area-weighted shading spread / geometric spread over the curved "
         "regions (W2 blends)",
         {"before_r1": {k: cb[k] for k in ("curved_regions", "curved_area_mm2", "area_weighted_shading_ratio")},
          "after_r2": {k: ca[k] for k in ("curved_regions", "curved_area_mm2", "area_weighted_shading_ratio")},
          "stock_frame_after": ca["by_part"].get("stock_frame")},
         "after >= 0.85", ca["area_weighted_shading_ratio"] >= 0.85,
         "the 'banded, streaky ribbon' on the stock head (FP / ADS): smg_parts._flatten_planar flattened every curved "
         "region into 3-6 deg planes; diag/clay_before_after.png")
    v, ok = C1.k_exposure(out / "hero_34.png", out / "l5" / "hero_34.png")
    gate("K2 exposure: hero_34 receiver side, realism rig / L5 calibration rig (mean sRGB luma)", v, "<= 1.3", ok,
         "the r2 product rig keeps the black polymer black (backdrop sRGB 150)")
    rep = json.loads((SCRATCH / "paint" / "paint_report.json").read_text())
    rp = rep["Metal"]["finishes"]["phosphate"]["rough_p5_p50_p95"][1]
    rf = rep["Furniture"]["finishes"]["polymer"]["rough_p5_p50_p95"][1]
    w2 = json.loads((GATES / "uv_bake_paint.json").read_text())
    g20 = next((g for g in w2["gates"] if g["name"].startswith("G20")), {})
    gate("K3 material split: roughness P50 phosphate - polymer (the maps), G20 passing",
         {"phosphate_p50": rp, "polymer_p50": rf, "split": round(rp - rf, 3), "G20": g20.get("value"),
          "G20_pass": g20.get("pass")}, ">= 0.20 with G20 passing", (rp - rf) >= 0.20 and bool(g20.get("pass")),
         "satin polymer 0.40-0.48 against the dead-flat phosphate 0.66-0.78")
    sp = {v_: sparkles(out / f"{v_}.png") for v_ in ("fp_35cm", "ads_55deg", "c1_rear_sight_rail")}
    sp_prev = {v_: sparkles(PREV / f"{v_}.png") for v_ in ("fp_35cm", "ads_55deg", "c1_rear_sight_rail")}
    gate("K4 sparkle: isolated hot pixels (clusters <= 3 px at >= 235) on fp_35cm, ads_55deg, c1",
         {"after": {k: {"isolated": v_[0], "hot_px": v_[1]} for k, v_ in sp.items()},
          "before_r1": {k: {"isolated": v_[0], "hot_px": v_[1]} for k, v_ in sp_prev.items()}},
         "after <= 5 in total", sum(v_[0] for v_ in sp.values()) <= 5,
         "the judges' 'white hairline glints on random edges' of the rear sight and its base")
    info = rep["Metal"].get("info", {})
    gate("K5 no bare steel on the sights or the selector (rubbed phosphate only)",
         {"sight_selector_bare_texels": info.get("sight_selector_bare_texels")}, "0",
         info.get("sight_selector_bare_texels", 1) == 0)
    r1rep = json.loads((BEFORE_CLAY / "paint_report_r1.json").read_text())

    def spread99(rp_):
        q = rp_["Furniture"]["finishes"]["polymer"]["bc_srgb_dielectric_p1_p50_p99"]
        return round(q[2] - q[1], 1)
    gate("K6 wear present in the maps: polymer BC P99 - P50 (sRGB levels)",
         {"before_r1": spread99(r1rep), "after_r2": spread99(rep),
          "mag_after": round(rep["Mag"]["finishes"]["polymer_mag"]["bc_srgb_dielectric_p1_p50_p99"][2] -
                             rep["Mag"]["finishes"]["polymer_mag"]["bc_srgb_dielectric_p1_p50_p99"][1], 1)},
         ">= 20", spread99(rep) >= 20.0, "edge rub, scuffs and the sheet's specks (r1's rub was ~6 levels)")
    chain = {}
    for f in CHAIN:
        p = GATES / f"{f}.json"
        chain[f] = json.loads(p.read_text()).get("status") if p.exists() else "missing"
    gate("K7 every stage gate of the rebuilt chain passes", chain, "all 'pass'",
         all(v_ == "pass" for v_ in chain.values()))
    need = [out / f"{v_}.png" for v_ in VIEWS] + [out / "l5" / f"{v_}.png" for v_ in VIEWS] + \
        [Path(s["out"]) for s in shots if s["name"].startswith("c")] + [Path(s["out"]) for s in clays]
    miss = [R.rel(p) for p in need if not p.exists()]
    gate("K8 the close-up set rendered from the exported bytes", {"images": len(need) - len(miss), "missing": miss},
         "5 views x 2 rigs + 3 close-ups + 3 clay diagnostics", not miss)
    failed = [g["name"] for g in G if not g["pass"]]
    res = {"stage": f"W4b close-up realism pass round {ROUND}", "date": datetime.datetime.now().isoformat(
        timespec="seconds"), "status": "pass" if not failed else "fail", "failed": failed, "gates": G,
        "folder": R.rel(out), "rig": R.STUDIO, "denoise": R.STUDIO_DENOISE, "samples": R.STUDIO_SAMPLES,
        "spec_ruling": "R47",
        "inputs_sha256": {R.rel(p): R.sha(p) for p in sorted(R.EXP.glob("*.fbx")) + sorted(R.TEXD.glob("*.png"))},
        "note": "the realism verdict (both judges on the close views) is the judges', reported, not self-judged"}
    (GATES / f"closeup_r{ROUND}.json").write_text(json.dumps(res, indent=1))
    print("[closeup_r2]", res["status"], failed)


if __name__ == "__main__":
    main()
