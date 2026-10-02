"""Pilot 2 full measurement (called by rocks_measure2.py all [--sbs]). The same code runs on the sheet and on ours;
ours is cropped to the rock and resampled to the sheet's pixel size first (study 6.1 step 10).

Per rock: IoU per view (front / side over elevations 0-15 deg; the sheet's lower small views (elevated 3/4 views)
against our oblique silhouettes over a grid of azimuths and elevations, best pair reported with its angle; plan;
RiverRound's second end view), the scale-free shape measures (corner radius / short side, solidity, top-profile
std), values per region (luma percentiles, local std, R/B, hue / sat, moss share; the wet band = bottom 30 %), and
the form measures from the catalog (arris radius / short axis, plane fraction, crease share). Close-ups and the
riverbank: the contrast set at the sheet panel's pixel size.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

import rock_ref as rr
import rocks_ref as ref
import rocks_measure2 as M

BUILD = M.BUILD
P2 = M.P2
SBS = M.SBS
REFC = M.REFC
ROCKS = M.ROCKS
BG = M.BG


def comp(path, bg=BG):
    im = Image.open(path).convert("RGBA")
    out = Image.new("RGBA", im.size, (*bg, 255))
    out.alpha_composite(im)
    return np.asarray(out.convert("RGB"), np.float64), np.asarray(im)[..., 3]


def best_iou(ref_mask, paths):
    best = (-1.0, None)
    for p in paths:
        m = np.asarray(Image.open(p).convert("RGBA"))[..., 3] > 127
        if m.sum() < 50:
            continue
        v = rr.iou(ref_mask, rr.crop_to_mask(m))
        if v > best[0]:
            best = (v, p.name)
    return best


def crop_to(rgb, mask, pad=0.06):
    ys, xs = np.nonzero(mask)
    h, w = mask.shape
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    py, px = int((y1 - y0) * pad), int((x1 - x0) * pad)
    return Image.fromarray(rgb[max(0, y0 - py):min(h, y1 + py), max(0, x0 - px):min(w, x1 + px)].astype(np.uint8))


def values_at_sheet_px(rgb, mask, w, h):
    ys, xs = np.nonzero(mask)
    cr = Image.fromarray(rgb[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8))
    cm = Image.fromarray((mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1] * 255).astype(np.uint8))
    cr = np.asarray(cr.resize((w, h), Image.LANCZOS), np.float64)
    cm = np.asarray(cm.resize((w, h), Image.BILINEAR)) > 127
    return ref.value_regions(cr, (0, 0, w, h), cm)


def run(do_sbs):
    refm = json.loads((BUILD / "ref_measure.json").read_text(encoding="utf-8"))
    sheet = rr.load(M.SHEET)
    sheet_im = Image.open(M.SHEET).convert("RGB")
    cat = json.loads((BUILD / "rocks_catalog.json").read_text(encoding="utf-8"))
    out = {"rig": "studio: film transparent over sRGB 186 grey, key area front-left above, fill right, top; "
                  "Standard view transform; main view perspective 85 mm at 8 deg; 3/4 view 35 deg azimuth, 22 deg "
                  "up, 60 mm", "rocks": {}, "closeups": {}, "sbs": []}
    sil = P2 / "sil"
    for r in ROCKS:
        Rr = {}
        masks = {v: np.load(REFC / f"mask_{r}_{v}.npy") for v in ("front", "side", "top")}
        if r == "RiverRound":
            masks["side_small"] = np.load(REFC / f"mask_{r}_side_small.npy")
        if sil.exists():
            iou = {
                "front": best_iou(masks["front"], sorted(sil.glob(f"sil_{r}_front_e*.png"))),
                "side": best_iou(masks["side"], sorted(sil.glob(f"sil_{r}_side_e*.png"))),
                "sheet_lower_view_vs_our_obliques": best_iou(masks["top"], sorted(sil.glob(f"sil_{r}_obl_*.png"))),
                "plan_ortho_top": best_iou(masks["top"], sorted(sil.glob(f"sil_{r}_top_e90.png"))),
            }
            if "side_small" in masks:
                iou["side_small_vs_obliques_and_side"] = best_iou(
                    masks["side_small"], sorted(sil.glob(f"sil_{r}_side_e*.png")) + sorted(sil.glob(f"sil_{r}_obl_*.png")))
            # the sheet's main view against our 3/4 view (how far the 3/4 silhouette departs from the main view)
            q = sil / f"sil_{r}_q34.png"
            if q.exists():
                iou["sheet_main_vs_our_q34"] = best_iou(masks["front"], [q])
            Rr["iou"] = iou
            for vw, key in (("front", "front"), ("side", "side")):
                b = iou[key]
                if b[1]:
                    m = np.asarray(Image.open(sil / b[1]).convert("RGBA"))[..., 3] > 127
                    Rr[f"shape_{vw}"] = {"ours": rr.shape_measures(rr.crop_to_mask(m)),
                                         "sheet": rr.shape_measures(masks[vw])}
        main = P2 / "sheet" / f"{r}_mainonly.png"
        if main.exists():
            rgb, a = comp(main)
            mask = a > 250
            fr = refm["rocks"][r]["front"]
            Rr["values_ours"] = values_at_sheet_px(rgb, mask, fr["w_px"], fr["h_px"])
            Rr["values_sheet"] = fr["values"]
        c = cat["rocks"].get(r, {})
        if c:
            s = c["size_above_grade_m"]
            short = min(s["D"], s["H"]) if r != "CliffChunk" else min(s["L"], s["D"])
            ar = c["sg14"].get("arris_radius_m_p25_p50_p75")
            Rr["form"] = {"plane_fraction_k6_15deg": c["sg14"]["plane_fraction_k6_15deg_dense"],
                          "sharp_crease_share_30deg": c["sg14"]["sharp_crease_share_30deg"],
                          "arris_radius_m_p25_p50_p75": ar,
                          "arris_p50_over_short_axis": round(ar[1] / short, 3) if ar else None,
                          "mask_shares": c.get("mask_shares_dense"), "lichen_rosettes": c.get("lichen_rosettes")}
        out["rocks"][r] = Rr
        if do_sbs and main.exists():
            pad = 6
            b = refm["rocks"][r]["front"]["bbox_px"]
            sc_main = Image.fromarray(sheet[b[1] - pad:b[3] + pad, b[0] - pad:b[2] + pad].astype(np.uint8))
            out["sbs"].append(M.sbs(sc_main, crop_to(rgb, mask), SBS / f"sbs_{r}_main.png"))
            for vw in ("top", "side"):
                p = P2 / "sheet" / f"{r}_{vw}.png"
                if p.exists() and vw in refm["rocks"][r]:
                    rgb2, a2 = comp(p)
                    bb = refm["rocks"][r][vw]["bbox_px"]
                    scv = Image.fromarray(sheet[bb[1] - pad:bb[3] + pad, bb[0] - pad:bb[2] + pad].astype(np.uint8))
                    out["sbs"].append(M.sbs(scv, crop_to(rgb2, a2 > 250), SBS / f"sbs_{r}_{vw}.png"))
            for nm, lab in (("q34", "ours 3/4"), ("clay_q34", "ours clay 3/4")):
                p = P2 / "sheet" / f"{r}_{nm}.png"
                if p.exists():
                    rgb3, a3 = comp(p)
                    out["sbs"].append(M.sbs(sc_main, crop_to(rgb3, a3 > 250), SBS / f"sbs_{r}_{nm}.png",
                                            labels=("sheet (main)", lab)))
            p = P2 / "sheet" / f"{r}_main.png"
            if p.exists():
                rgb4, _ = comp(p)
                bx = {"RiverRound": (0, 250, 610, 444), "RiverLong": (0, 250, 900, 444),
                      "CliffChunk": (0, 598, 365, 836)}[r]
                scp = Image.fromarray(sheet[bx[1]:bx[3], bx[0]:bx[2]].astype(np.uint8))
                out["sbs"].append(M.sbs(scp, Image.fromarray(rgb4.astype(np.uint8)), SBS / f"sbs_{r}_panel.png"))
                row = row_sheet(r)
                if row is not None:
                    row.save(P2 / "sheet" / f"{r}_row.png")
                    out["sbs"].append(M.sbs(scp, row, SBS / f"sbs_{r}_row.png"))
    # close-ups + riverbank
    for k, b in M.PANELS.items():
        p = P2 / ("river/riverbank_sunset.png" if k == "riverbank" else f"close/close_{k}.png")
        if not p.exists():
            continue
        im = Image.open(p).convert("RGB")
        size = (b[2] - b[0], b[3] - b[1])
        W, H = im.size
        asp = size[0] / size[1]
        if W / H > asp:
            w = int(H * asp)
            im_c = im.crop(((W - w) // 2, 0, (W - w) // 2 + w, H))
        else:
            h = int(W / asp)
            im_c = im.crop((0, (H - h) // 2, W, (H - h) // 2 + h))
        ours = M.to_size(im_c, size)
        refp = np.asarray(sheet_im.crop(b), np.float64) / 255.0
        out["closeups"][k] = {"sheet": M.contrast(refp), "ours_at_sheet_px": M.contrast(ours)}
        if do_sbs:
            out["sbs"].append(M.sbs(sheet_im.crop(b), im, SBS / f"sbs_close_{k}.png"))
    (P2 / "measure.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    report(out)
    return out


def row_sheet(r, h=520):
    """Our row laid out like the sheet's: the main view with the figure on the left, the top and side views at the
    right (stacked for the river boulders as in row 2, side by side above for the cliff as in row 4)."""
    S = P2 / "sheet"
    ps = [S / f"{r}_{v}.png" for v in ("main", "top", "side")]
    if not all(p.exists() for p in ps):
        return None
    ims = []
    for p in ps:
        rgb, a = comp(p)
        ims.append(crop_to(rgb, a > 30, pad=0.04) if p != ps[0] else Image.fromarray(rgb.astype(np.uint8)))
    main = ims[0].resize((int(ims[0].width * h / ims[0].height), h), Image.LANCZOS)
    half = h // 2 - 6
    top = ims[1].resize((max(1, int(ims[1].width * half / ims[1].height)), half), Image.LANCZOS)
    side = ims[2].resize((max(1, int(ims[2].width * half / ims[2].height)), half), Image.LANCZOS)
    wr = max(top.width, side.width)
    out = Image.new("RGB", (main.width + wr + 20, h), BG)
    out.paste(main, (0, 0))
    out.paste(top, (main.width + 10, 4))
    out.paste(side, (main.width + 10, half + 10))
    return out


def report(out):
    for r, R in out["rocks"].items():
        print(r)
        for k, v in R.get("iou", {}).items():
            print(f"  IoU {k:36s} {v}")
        for vw in ("front", "side"):
            if f"shape_{vw}" in R:
                o, s = R[f"shape_{vw}"]["ours"], R[f"shape_{vw}"]["sheet"]
                print(f"  shape {vw}: corner r/short ours {o['corner_radius_over_short_median']} sheet "
                      f"{s['corner_radius_over_short_median']} | solidity {o['solidity']} / {s['solidity']} | "
                      f"top std {o['top_profile_std_over_h']} / {s['top_profile_std_over_h']} | corners "
                      f"{o['corners_gt35deg']} / {s['corners_gt35deg']}")
        vo, vs = R.get("values_ours", {}), R.get("values_sheet", {})
        for k in ("all", "top25", "mid", "bottom30"):
            if k in vo and k in vs:
                print(f"  {k:8s} ours p50 {vo[k]['luma_p5_p25_p50_p75_p95'][2]:.3f} std {vo[k]['local_std_16px']} "
                      f"hue {vo[k]['hue']} sat {vo[k]['sat']} RB {vo[k]['R_over_B']} moss {vo[k]['moss_share']} | "
                      f"sheet p50 {vs[k]['luma_p5_p25_p50_p75_p95'][2]:.3f} std {vs[k]['local_std_16px']} "
                      f"hue {vs[k]['hue']} sat {vs[k]['sat']} RB {vs[k]['R_over_B']} moss {vs[k]['moss_share']}")
        if "form" in R:
            print("  form", R["form"])
    for k, v in out["closeups"].items():
        o, s = v["ours_at_sheet_px"], v["sheet"]
        print(f"close {k:9s} ours luma {o['luma_p5_p25_p50_p75_p95']} lstd {o['local_std_16px']} lstd/p50 "
              f"{o['local_std_over_p50']} dark_rel {o['dark_rel']} hue {o['hue']} sat {o['sat']} moss "
              f"{o['moss_share']} | sheet {s['luma_p5_p25_p50_p75_p95']} lstd {s['local_std_16px']} lstd/p50 "
              f"{s['local_std_over_p50']} dark_rel {s['dark_rel']} hue {s['hue']} sat {s['sat']} moss "
              f"{s['moss_share']}")
