"""Pilot measurement (study 6.1 / 6.2 on the renders, the SAME code as on the sheet): silhouette IoU per view, aspect
and the scale-free shape measures, value / hue per region (studio rig), moss share, the close-ups, and the
side-by-side sheets (sheet crop | ours). numpy + PIL (py -3).

    py -3 -B Scripts/dojo/rocks/rocks_measure.py [--sbs]

Writes WorkFiles/dojo/build/rocks/pilot/measure.json and pilot/sbs/*.png.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "stone"))
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "rocks"))
import rock_ref as rr          # noqa: E402
import stone_measure as sm     # noqa: E402
import rocks_ref as ref        # noqa: E402

BUILD = ROOT / "WorkFiles" / "dojo" / "build" / "rocks"
PILOT = BUILD / "pilot"
SBS = PILOT / "sbs"
BG = (186, 186, 186)
ROCKS = ["RiverRound", "RiverLong", "CliffChunk"]


def comp(path, bg=BG):
    im = Image.open(path).convert("RGBA")
    out = Image.new("RGBA", im.size, (*bg, 255))
    out.alpha_composite(im)
    return np.asarray(out.convert("RGB"), np.float64), np.asarray(im)[..., 3] > 127


def rock_alpha(path):
    """Rock-only mask of a sheet-mode render: alpha minus the shadow catcher's shadow (low alpha, neutral) ."""
    a = np.asarray(Image.open(path).convert("RGBA"), np.float64)
    return a[..., 3] > 250


def values(rgb, mask):
    return ref.value_regions(rgb, (0, 0, rgb.shape[1], rgb.shape[0]), mask)


def best_iou(ref_mask, paths):
    best = (-1, None)
    for p in paths:
        m = np.asarray(Image.open(p).convert("RGBA"))[..., 3] > 127
        if m.sum() < 50:
            continue
        v = rr.iou(ref_mask, m)
        if v > best[0]:
            best = (v, p.name)
    return best


def label(im, text):
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        f = ImageFont.load_default()
    d.rectangle((0, 0, 12 + 12 * len(text), 32), fill=(30, 30, 30))
    d.text((6, 4), text, fill=(240, 240, 240), font=f)
    return im


def sbs(left, right, path, h=520):
    L = left.copy()
    Rm = right.copy()
    L = L.resize((max(1, int(L.width * h / L.height)), h), Image.LANCZOS)
    Rm = Rm.resize((max(1, int(Rm.width * h / Rm.height)), h), Image.LANCZOS)
    out = Image.new("RGB", (L.width + Rm.width + 12, h), (20, 20, 20))
    out.paste(label(L, "sheet"), (0, 0))
    out.paste(label(Rm, "ours"), (L.width + 12, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path)
    return str(path.relative_to(ROOT))


def crop_to(im_rgb, mask, pad=0.06):
    ys, xs = np.nonzero(mask)
    h, w = mask.shape
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    py, px = int((y1 - y0) * pad), int((x1 - x0) * pad)
    return Image.fromarray(im_rgb[max(0, y0 - py):min(h, y1 + py), max(0, x0 - px):min(w, x1 + px)].astype(np.uint8))


def main():
    do_sbs = "--sbs" in sys.argv
    refm = json.loads((BUILD / "ref_measure.json").read_text(encoding="utf-8"))
    sheet = rr.load(ROOT / refm["sheet"])
    out = {"rig": "studio: film transparent over sRGB 186 grey, key area front-left above, fill right, top; "
                  "Standard view transform; perspective 85 mm at 8 deg (main), 50 deg (top), 8 deg (side)",
           "rocks": {}, "closeups": {}, "sbs": []}
    for r in ROCKS:
        R = {}
        views = ref.VIEWS[r]
        # ---- silhouettes (ortho alpha passes, best elevation per view)
        sil = PILOT / "sil"
        sm_front = np.load(BUILD / "pilot" / "refcrops" / f"mask_{r}_front.npy")
        sm_side = np.load(BUILD / "pilot" / "refcrops" / f"mask_{r}_side.npy")
        sm_top = np.load(BUILD / "pilot" / "refcrops" / f"mask_{r}_top.npy")
        if sil.exists():
            f_iou = best_iou(sm_front, sorted(sil.glob(f"sil_{r}_front_e0*.png")) +
                             sorted(sil.glob(f"sil_{r}_front_e1*.png")))
            s_iou = best_iou(sm_side, sorted(sil.glob(f"sil_{r}_side_e*.png")))
            t_iou = best_iou(sm_top, sorted(sil.glob(f"sil_{r}_top_e*.png")) +
                             [p for p in sil.glob(f"sil_{r}_front_e*.png") if int(p.stem[-2:]) >= 30])
            R["iou"] = {"front": f_iou, "side": s_iou, "top_or_oblique": t_iou}
            # shape measures on the best front / side silhouettes, beside the sheet's
            for vw, best, refmask in (("front", f_iou, sm_front), ("side", s_iou, sm_side)):
                if best[1]:
                    m = np.asarray(Image.open(sil / best[1]).convert("RGBA"))[..., 3] > 127
                    R[f"shape_{vw}"] = {"ours": rr.shape_measures(m), "sheet": rr.shape_measures(refmask)}
        # ---- values per region on the studio main view (rock pixels only)
        main = PILOT / "sheet" / f"{r}_mainonly.png"
        if main.exists():
            rgb, _ = comp(main)
            mask = rock_alpha(main)
            # matched scale (study 6.1 step 10): our crop resampled so the rock spans the sheet's pixels
            bw = refm["rocks"][r]["front"]["w_px"]
            bh = refm["rocks"][r]["front"]["h_px"]
            ys, xs = np.nonzero(mask)
            cr = Image.fromarray(rgb[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8))
            cm = Image.fromarray((mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1] * 255).astype(np.uint8))
            cr = np.asarray(cr.resize((bw, bh), Image.LANCZOS), np.float64)
            cm = np.asarray(cm.resize((bw, bh), Image.BILINEAR)) > 127
            R["values_ours"] = values(cr, cm)
            R["values_ours_fullres"] = values(rgb, mask)
            R["values_sheet"] = refm["rocks"][r]["front"]["values"]
            if do_sbs:
                b = refm["rocks"][r]["front"]["bbox_px"]
                pad = 6
                sc = Image.fromarray(sheet[b[1] - pad:b[3] + pad, b[0] - pad:b[2] + pad].astype(np.uint8))
                out["sbs"].append(sbs(sc, crop_to(rgb, mask), SBS / f"sbs_{r}_main.png"))
                for vw in ("top", "side"):
                    p = PILOT / "sheet" / f"{r}_{vw}.png"
                    if p.exists() and vw in refm["rocks"][r]:
                        rgb2, _ = comp(p)
                        m2 = rock_alpha(p)
                        b = refm["rocks"][r][vw]["bbox_px"]
                        sc = Image.fromarray(sheet[b[1] - pad:b[3] + pad, b[0] - pad:b[2] + pad].astype(np.uint8))
                        out["sbs"].append(sbs(sc, crop_to(rgb2, m2), SBS / f"sbs_{r}_{vw}.png"))
                p = PILOT / "sheet" / f"{r}_main.png"
                if p.exists():
                    rgb3, _ = comp(p)
                    # the whole sheet panel (with its figure) | ours with the figure
                    bx = {"RiverRound": (0, 250, 610, 444), "RiverLong": (0, 250, 900, 444),
                          "CliffChunk": (0, 598, 365, 836)}[r]
                    sc = Image.fromarray(sheet[bx[1]:bx[3], bx[0]:bx[2]].astype(np.uint8))
                    out["sbs"].append(sbs(sc, Image.fromarray(rgb3.astype(np.uint8)), SBS / f"sbs_{r}_panel.png"))
        out["rocks"][r] = R
    # ---- close-ups
    for k, b in ref.CLOSEUPS.items():
        p = PILOT / ("river/riverbank_sunset.png" if k == "riverbank" else f"close/close_{k}.png")
        if not p.exists():
            continue
        ours = np.asarray(Image.open(p).convert("RGB"), np.float64)
        v = sm.image_values(ours / 255.0)
        out["closeups"][k] = {"ours": {"luma_p5_p25_p50_p75_p95": v["method_A"]["luma_p5_p25_p50_p75_p95"],
                                       "local_std_16px": v["method_A"]["local_std_16px"],
                                       "R_over_B": v["method_A"]["R_over_B"], "hue": v["method_C"]["stone_hue_deg"],
                                       "sat": v["method_C"]["stone_sat"], "moss_share": v["moss_share"]},
                              "sheet": refm["closeups"][k]}
        if k == "grain":
            lu = 0.2126 * ours[..., 0] + 0.7152 * ours[..., 1] + 0.0722 * ours[..., 2]
            out["closeups"][k]["ours"]["dark_lt_0.25"] = round(float((lu / 255 < 0.25).mean()), 4)
        if do_sbs:
            sc = Image.fromarray(sheet[b[1]:b[3], b[0]:b[2]].astype(np.uint8))
            out["sbs"].append(sbs(sc, Image.fromarray(ours.astype(np.uint8)), SBS / f"sbs_close_{k}.png"))
    (PILOT / "measure.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for r, R in out["rocks"].items():
        print(r, "IoU", R.get("iou"))
        vo, vs = R.get("values_ours", {}), R.get("values_sheet", {})
        for k in ("all", "top25", "mid", "bottom30"):
            if k in vo and k in vs:
                print(f"  {k:8s} ours p50 {vo[k]['luma_p5_p25_p50_p75_p95'][2]:.3f} std {vo[k]['local_std_16px']} "
                      f"hue {vo[k]['hue']} sat {vo[k]['sat']} RB {vo[k]['R_over_B']} moss {vo[k]['moss_share']} | "
                      f"sheet p50 {vs[k]['luma_p5_p25_p50_p75_p95'][2]:.3f} std {vs[k]['local_std_16px']} "
                      f"hue {vs[k]['hue']} sat {vs[k]['sat']} RB {vs[k]['R_over_B']} moss {vs[k]['moss_share']}")
    for k, v in out["closeups"].items():
        print(k, "ours", v["ours"]["luma_p5_p25_p50_p75_p95"], v["ours"]["local_std_16px"], v["ours"]["hue"],
              v["ours"]["sat"], "| sheet", v["sheet"]["luma_p5_p25_p50_p75_p95"], v["sheet"]["local_std_16px"],
              v["sheet"]["hue"], v["sheet"]["sat"])


if __name__ == "__main__":
    main()
