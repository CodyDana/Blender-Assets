"""SMG01 W4b close-up realism pass (plain Python; renders via headless Blender, gunlib/export_review_job.py, from the
EXPORTED bytes: SK_SMG01.fbx + SM_SMG01_Mag.fbx on the magazine bone + the shipped textures, as smg_review_export.py):

    py -3 -B Scripts/guns/smg/smg_closeup.py --round 1 [--samples 128] [--no-render]

Renders review/closeup_r<N>/: the judges' close views (fp_35cm, ads_55deg, hero_34, hero_34_folded, tp_3m) under the
realism rig (smg_review_export.STUDIO, spec R46), the same five under the L5 colour-calibration rig in l5/, three real
close-ups at ~20 cm (c1 rear sight + top rail, c2 receiver left: selector / grip / magwell, c3 front end: device, front
sight, charging knob) and a before / after contact against the W4 realism set (scratch/closeup_before, copied from
review/realism before the round). Measures the judges' tells on the renders and the maps and writes
gates/closeup_r<N>.json (+ the chain's stage gate files it requires):

  K1 clouds: band-pass (Gaussian 2 px - 10 px) luma std / mean on two hero_34 receiver-side flats (the
     "large, soft, cloudy blotches"), after <= 0.5 x before;
  K2 exposure: hero_34 receiver-side mean luma, realism rig / L5 rig <= 1.3 (R45: 1.94, "mid-grey clay, not black");
  K3 seam: ADS, the centre column of the receiver rear face against its neighbours (the painted parting line read as a
     UV seam), after <= 0.5 x before and <= 1.0 level;
  K4 glints: pixels at >= 235 (any channel) on fp_35cm + ads_55deg (the backdrop is 126): after <= 0.5 x before;
  K5 material split: the maps' roughness P50 phosphate - polymer >= 0.12 (R44: 0.02), at the G20 albedo ratio (W2 gate);
  K6 the chain: form, form_magfit, uv_bake_paint, game, rig_export, mag, review_export, gunlib_regression all pass.
The realism verdict itself belongs to the judges (reported, not self-judged).
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, SCRATCH, REVIEW, GATES  # noqa: E402

import smg_review_export as R  # noqa: E402

BEFORE = SCRATCH / "closeup_before"
VIEWS = ["fp_35cm", "ads_55deg", "hero_34", "hero_34_folded", "tp_3m"]
# fixed-camera measurement windows (rows, cols) on the 1600 x 900 hero_34 frame: flat polymer only
# (two windows on the receiver's left flats, between the drawn seams and slots; a stock window was tried and dropped:
# at 1.5 m every stock flat this size crosses an edge or a window border)
HERO_BOXES = {"receiver_upper_flat": (slice(380, 400), slice(790, 940)),
              "receiver_lower_flat": (slice(414, 434), slice(760, 860))}
CHAIN = ["form", "form_magfit", "uv_bake_paint", "game", "rig_export", "mag", "review_export", "gunlib_regression"]


def luma(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
    return a @ np.array([0.2126, 0.7152, 0.0722])


def close_shots(out, samples):
    U = R.unit
    S = []
    for name, tgt, d, dist, note in [
            ("c1_rear_sight_rail", (318.0, 0.0, 52.0), (-0.80, 0.42, 0.45), 210.0,
             "close-up ~21 cm: rear sight, top rail, receiver top rear (the FP / ADS foreground)"),
            ("c2_receiver_left", (360.0, 30.0, -42.0), (0.12, 1.0, 0.22), 230.0,
             "close-up ~23 cm: left side, selector, grip, trigger guard, magwell"),
            ("c3_front_end", (560.0, 18.0, 8.0), (0.62, 0.72, 0.30), 240.0,
             "close-up ~24 cm: muzzle device, front sight, vents, charging knob")]:
        t = np.array(tgt)
        cam = R.persp_look(t + dist * U(d), t, 40.0, (1600, 900))
        L = dict(R.STUDIO, target_M=[float(v) for v in t], dist_m=0.7)
        S.append({"name": name, "out": str(out / f"{name}.png"), "camera": cam, "lights": L, "samples": samples,
                  "note": note + " [realism rig]"})
    return S


def k_clouds(after, before):
    rows = {}
    for nm, (rs, cs) in HERO_BOXES.items():
        vals = []
        for p in (before, after):
            L = luma(p)
            bp = ndi.gaussian_filter(L, 2.0) - ndi.gaussian_filter(L, 10.0)
            vals.append(float(np.std(bp[rs, cs]) / max(np.mean(L[rs, cs]), 1e-6)))
        rows[nm] = {"before": round(vals[0], 4), "after": round(vals[1], 4), "ratio": round(vals[1] / vals[0], 3)}
    ok = all(r["ratio"] <= 0.5 for r in rows.values())
    return rows, ok


def k_exposure(real, l5):
    rs, cs = HERO_BOXES["receiver_lower_flat"]
    a, b = float(luma(real)[rs, cs].mean()), float(luma(l5)[rs, cs].mean())
    return {"realism_rig": round(a, 1), "l5_rig": round(b, 1), "ratio": round(a / b, 3)}, a / b <= 1.3


def seam_index(p):
    L = luma(p)
    H, W = L.shape
    x0 = W // 2
    rows = slice(int(H * 0.76), int(H * 0.97))          # the receiver rear face and the stock head under the sights
    best = 0.0
    for x in range(x0 - 3, x0 + 4):                     # the line is one or two columns wide; take the strongest
        d = np.abs(L[rows, x] - 0.5 * (L[rows, x - 4] + L[rows, x + 4]))
        best = max(best, float(np.mean(d)))
    return best


def glints(p):
    a = np.asarray(Image.open(p).convert("RGB"))
    return int((a.max(-1) >= 235).sum())


def contact(pairs, out, w=760):
    ims = []
    for a, b, lab in pairs:
        A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
        h = int(w * A.height / A.width)
        ims.append((A.resize((w, h)), B.resize((w, h)), lab))
    H = sum(i[0].height + 24 for i in ims)
    C = Image.new("RGB", (2 * w + 10, H + 24), (255, 255, 255))
    d = ImageDraw.Draw(C)
    d.text((6, 4), "BEFORE (W4 realism set, R45)", fill=(0, 0, 0))
    d.text((w + 16, 4), "AFTER (W4b close-up r1, R46)", fill=(0, 0, 0))
    y = 24
    for A, B, lab in ims:
        d.text((6, y + 4), lab, fill=(0, 0, 0))
        C.paste(A, (0, y + 20))
        C.paste(B, (w + 10, y + 20))
        y += A.height + 24
    C.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    out = REVIEW / f"closeup_r{a.round}"
    out.mkdir(parents=True, exist_ok=True)
    R.REAL = out
    shots = [s for s in R.realism_shots(a.samples) if s["name"].replace("_l5", "") in VIEWS]
    shots += close_shots(out, a.samples)
    if not a.no_render:
        R.run_job(f"closeup_r{a.round}", shots, a.samples)
    (out / "shots.json").write_text(json.dumps({"source": "EXPORTED bytes (SK_SMG01 + SM_SMG01_Mag + shipped textures "
                                                          "+ shipped clips)", "rig": R.STUDIO,
                                                "shots": [dict(s, out=R.rel(s["out"])) for s in shots]}, indent=1))
    R.contact([(s["out"], s["name"] + ": " + s["note"]) for s in shots if not s["name"].endswith("_l5")],
              out / "contact.png")
    contact([(BEFORE / f"{v}.png", out / f"{v}.png", v) for v in ["fp_35cm", "ads_55deg", "hero_34"]],
            out / "before_after.png")

    G = []

    def gate(name, value, threshold, ok, note=""):
        G.append({"name": name, "value": value, "threshold": threshold, "pass": bool(ok), "note": note})
    rows, ok = k_clouds(out / "hero_34.png", BEFORE / "hero_34.png")
    gate("K1 clouds: band-pass (2-10 px) luma std / mean on the hero_34 receiver flats (realism rig)", rows,
         "after <= 0.5 x before", ok,
         "the judges' 'large, soft, cloudy grey / white blotches' (R45 sheen + albedo fields)")
    v, ok = k_exposure(out / "hero_34.png", out / "l5" / "hero_34.png")
    vb, _ = k_exposure(BEFORE / "hero_34.png", BEFORE / "l5_hero_34.png")
    v["before_ratio"] = vb["ratio"]
    gate("K2 exposure: hero_34 receiver side, realism rig / L5 calibration rig (mean sRGB luma)", v, "<= 1.3", ok,
         "R45's studio rig lit the black polymer to twice the calibrated exposure: 'mid-grey clay'")
    sb, sa = seam_index(BEFORE / "ads_55deg.png"), seam_index(out / "ads_55deg.png")
    gate("K3 ADS centre seam on the receiver rear face (mean |column - neighbours|, sRGB levels)",
         {"before": round(sb, 3), "after": round(sa, 3)}, "after <= 0.5 x before and <= 1.0", sa <= 0.5 * sb and sa <= 1.0,
         "the painted mid-plane parting line on the rear face and the stock head (both judges, both ADS views)")
    gb = {v_: glints(BEFORE / f"{v_}.png") for v_ in ("fp_35cm", "ads_55deg")}
    ga = {v_: glints(out / f"{v_}.png") for v_ in ("fp_35cm", "ads_55deg")}
    gate("K4 glints: pixels >= 235 on fp_35cm + ads_55deg", {"before": gb, "after": ga},
         "after <= 0.5 x before", sum(ga.values()) <= 0.5 * max(sum(gb.values()), 1),
         "the 'fireflies / hot pixels' on the rail teeth and the sight drum")
    rep = json.loads((SCRATCH / "paint" / "paint_report.json").read_text())
    rp = rep["Metal"]["finishes"]["phosphate"]["rough_p5_p50_p95"][1]
    rf = rep["Furniture"]["finishes"]["polymer"]["rough_p5_p50_p95"][1]
    w2 = json.loads((GATES / "uv_bake_paint.json").read_text())
    g20 = next((g for g in w2["gates"] if g["name"].startswith("G20")), {})
    gate("K5 material split: roughness P50 phosphate - polymer (the maps)",
         {"phosphate_p50": rp, "polymer_p50": rf, "split": round(rp - rf, 3), "G20_albedo_ratio": g20.get("value"),
          "G20_pass": g20.get("pass")}, ">= 0.12 with G20 passing", (rp - rf) >= 0.12 and bool(g20.get("pass")),
         "'one material on every part': the steel now a dead-flat crystalline charcoal, the polymer a satin")
    chain = {}
    for f in CHAIN:
        p = GATES / f"{f}.json"
        chain[f] = json.loads(p.read_text()).get("status") if p.exists() else "missing"
    gate("K6 every stage gate of the rebuilt chain passes", chain, "all 'pass'", all(v_ == "pass" for v_ in chain.values()))
    need = [out / f"{v_}.png" for v_ in VIEWS] + [out / "l5" / f"{v_}.png" for v_ in VIEWS] + \
        [Path(s["out"]) for s in shots if s["name"].startswith("c")]
    miss = [R.rel(p) for p in need if not p.exists()]
    gate("K7 the close-up set rendered from the exported bytes", {"images": len(need) - len(miss), "missing": miss},
         "5 views x 2 rigs + 3 close-ups", not miss)
    failed = [g["name"] for g in G if not g["pass"]]
    res = {"stage": f"W4b close-up realism pass round {a.round}", "date": datetime.datetime.now().isoformat(
        timespec="seconds"), "status": "pass" if not failed else "fail", "failed": failed, "gates": G,
        "folder": R.rel(out), "rig": R.STUDIO, "spec_ruling": "R46",
        "inputs_sha256": {R.rel(p): R.sha(p) for p in sorted(R.EXP.glob("*.fbx")) + sorted(R.TEXD.glob("*.png"))},
        "note": "the realism verdict (both judges on the close views) is the judges', reported, not self-judged"}
    (GATES / f"closeup_r{a.round}.json").write_text(json.dumps(res, indent=1))
    print("[closeup]", res["status"], failed)


if __name__ == "__main__":
    main()
