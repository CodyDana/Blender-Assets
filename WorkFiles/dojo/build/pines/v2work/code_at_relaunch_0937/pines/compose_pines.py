"""Model sheets, reference | ours side-by-sides and the measured gates for the pines (system Python: PIL + numpy).

    py -3 -B Scripts/dojo/pines/compose_pines.py --renders WorkFiles/dojo/build/pines/renders/r0

Reads the render set from render_pines.py (<variant>_<view>_final.png / _sil.png + render_meta.json) and writes into
the same folder:
  model_sheet_v1.png / model_sheet_v2.png   laid out like the reference: each pine front + side + 3/4 on light grey
                                            with a 1.8 m figure at the tree's scale
  sbs_<variant>_<view>.png                  reference panel | ours (final), same height
  sil_<variant>_<view>.png                  reference mask | our mask (flat silhouettes), with the numbers
  sbs_closeup_<name>.png                    reference close-up | ours
  measure.json                              gates G2-G6 and IoU per view (study 6.1 / 6.2)
Pairings: variant 1 = front panel (front), side panel (side), 3/4 panel (3q); variant 2 was traced from the 3/4
panel, so its front pairs with the 3/4 panel, its side with the side panel.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "Scripts" / "vegetation"))
import measure_tree as mt  # noqa: E402
import pines_trace as pt  # noqa: E402
import ref_panels as rp  # noqa: E402

BG = (182, 182, 182)
SPEC = json.loads((HERE / "pines_spec.json").read_text(encoding="utf-8"))
PAIRS = {  # (variant, view) -> reference panel
    ("1", "front"): "F", ("1", "side"): "S", ("1", "3q"): "Q",
    ("2", "front"): "Q", ("2", "side"): "S", ("2", "3q"): "F",
}


def font(size):
    for f in ("arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def on_grey(path, cut_row=None):
    im = Image.open(path).convert("RGBA")
    if cut_row is not None:
        a = np.asarray(im).copy()
        a[int(round(cut_row)) + 1:, :, 3] = 0
        im = Image.fromarray(a)
    bg = Image.new("RGBA", im.size, BG + (255,))
    bg.alpha_composite(im)
    return bg.convert("RGB"), np.asarray(im)[..., 3]


def ref_panel_name(variant, view):
    pine = SPEC[variant]["pine"]
    return f"P{pine}{PAIRS[(variant[-1], view)]}"


def cut_below(mask, row):
    m = mask.copy()
    m[int(round(row)) + 1:, :] = False
    return m


def our_masks(rdir, v, view, meta, pine):
    img, alpha = on_grey(rdir / f"{v}_{view}_sil.png")
    arr = np.asarray(img).astype(np.float32)
    m = mt.masks(arr, None, bg=np.array(BG, np.float32))
    bx, by = meta[f"{v}_{view}"]["base_px"]
    # v2: our origin is the ground; the sheet's panels are measured from the trunk base on the mound top, so our
    # masks are cut at the same height (spec sheet_base_z, about 0.2 m)
    by = by - float(SPEC[v]["trunk"].get("sheet_base_z", 0.0)) * meta[f"{v}_{view}"]["px_per_m"]
    if pine != 4:
        for k in ("foliage", "wood", "fg"):
            m[k] = cut_below(m[k], by)
    else:
        m["fg"] = cut_below(m["fg"] | (alpha > 128), by)
    return m, (bx, by), meta[f"{v}_{view}"]["px_per_m"]


def ref_masks(sheet, bg, name):
    p = rp.PANELS[name]
    a = sheet.copy()
    for (x0, y0, x1, y1) in p.get("exclude", []):
        a[y0:y1, x0:x1] = bg
    x0, y0, x1, y1 = p["box"]
    crop = a[y0:y1, x0:x1]
    m = mt.masks(crop, None, bg=bg)
    if p["pine"] != 4:
        by = p["base"][1] - y0
        for k in ("foliage", "wood", "fg"):
            m[k] = cut_below(m[k], by)
        base = (p["base"][0] - x0, p["base"][1] - y0)
    else:
        rock = np.asarray(pt.TRACE[name]["rock"], float)
        cx = 0.5 * (rock[:, 0].min() + rock[:, 0].max())
        base = (cx - x0, p["ground"] - y0)
        m["fg"] = cut_below(m["fg"] & ~m["figure"], base[1])
    return m, base, crop


def metrics_pair(ref_m, ref_base, ref_pxm, our_m, our_base, our_pxm, pine):
    if pine == 4:
        rk, ok = ref_m["fg"], our_m["fg"]
        fol_r, wood_r = ref_m["foliage"] & ref_m["fg"], ref_m["wood"] & ref_m["fg"]
        fol_o, wood_o = our_m["foliage"], our_m["wood"] | (our_m["fg"] & ~our_m["foliage"])
    else:
        rk = ref_m["foliage"] | ref_m["wood"]
        ok = our_m["foliage"] | our_m["wood"]
        fol_r, wood_r, fol_o, wood_o = ref_m["foliage"], ref_m["wood"], our_m["foliage"], our_m["wood"]
    iou = mt.iou(rk, ref_base, ok, our_base)
    mr = mt.metrics(fol_r, wood_r, ref_base, ref_pxm)
    mo = mt.metrics(fol_o, wood_o, our_base, our_pxm)
    return iou, mr, mo


def figure_poly(x, y_ground, pxm, h=1.8):
    """A plain standing figure (like the sheet's grey silhouette), feet at y_ground, x = centre."""
    s = pxm * h / 1.8
    # body up to the neck (1.56 m); the head is drawn as an ellipse by the caller (figure_head)
    pts = [(-0.10, 0), (-0.03, 0), (-0.02, 0.85), (0.02, 0.85), (0.03, 0), (0.10, 0), (0.12, 0.05), (0.10, 0.95),
           (0.20, 0.85), (0.24, 0.88), (0.22, 1.45), (0.12, 1.52), (0.05, 1.56), (-0.05, 1.56),
           (-0.12, 1.52), (-0.22, 1.45), (-0.24, 0.88), (-0.20, 0.85), (-0.10, 0.95), (-0.12, 0.05)]
    return [(x + px * s, y_ground - py * s) for px, py in pts]


def content_box(alpha, margin=0.04):
    ys, xs = np.nonzero(alpha > 8)
    h, w = alpha.shape
    mx, my = int(margin * w), int(margin * h)
    return max(0, xs.min() - mx), max(0, ys.min() - my), min(w, xs.max() + mx), min(h, ys.max() + my)


def model_sheet(rdir, meta, suffix, out):
    """Two rows like the sheet: [pine A | pine B] over [pine C | pine D]; each: figure + front + side + 3/4."""
    groups = [["PineA", "PineB"], ["PineC", "PineD"]]
    row_imgs = []
    H = 520
    f = font(20)
    for row in groups:
        tiles = []
        for g in row:
            v = f"{g}{suffix}"
            views = []
            pxm_ref = None
            for view in ("front", "side", "3q"):
                m = meta[f"{v}_{view}"]
                img, alpha = on_grey(rdir / f"{v}_{view}_final.png", m["base_px"][1])
                pxm = m["px_per_m"]
                bx, by = m["base_px"]
                x0, y0, x1, y1 = content_box(alpha)
                y1 = max(y1, int(by) + 6)
                crop = img.crop((x0, y0, x1, y1))
                views.append((crop, pxm, by - y0))
            # one scale per tree: the tallest crop fits H
            k = min(H / c.size[1] for c, _, _ in views)
            parts = []
            for c, pxm, gy in views:
                parts.append(c.resize((max(1, int(c.size[0] * k)), max(1, int(c.size[1] * k))), Image.LANCZOS))
            pxm_s = views[0][1] * k
            fig_w = int(0.6 * pxm_s) + 20
            W = fig_w + sum(p.size[0] for p in parts) + 12 * len(parts)
            tile = Image.new("RGB", (W, H + 40), BG)
            d = ImageDraw.Draw(tile)
            ground = int(views[0][2] * k) + (H - parts[0].size[1])
            d.polygon(figure_poly(fig_w // 2, ground, pxm_s), fill=(120, 120, 120))
            hx, hy = fig_w // 2, ground - 1.685 * pxm_s
            d.ellipse([hx - 0.095 * pxm_s, hy - 0.12 * pxm_s, hx + 0.095 * pxm_s, hy + 0.12 * pxm_s], fill=(120, 120, 120))
            x = fig_w
            for p_, (c, pxm, gy) in zip(parts, views):
                tile.paste(p_, (x, H - p_.size[1]))
                x += p_.size[0] + 12
                d.line([(x - 6, 10), (x - 6, H)], fill=(200, 200, 200), width=1)
            d.text((8, H + 8), f"SM_DKN_{v}  front | side | 3/4   (figure 1.8 m)", fill=(40, 40, 40), font=f)
            tiles.append(tile)
        W = sum(t.size[0] for t in tiles) + 30
        r = Image.new("RGB", (W, H + 40), BG)
        x = 0
        for t in tiles:
            r.paste(t, (x, 0))
            x += t.size[0] + 30
        row_imgs.append(r)
    W = max(r.size[0] for r in row_imgs)
    sheet = Image.new("RGB", (W, sum(r.size[1] for r in row_imgs) + 20), BG)
    y = 0
    for r in row_imgs:
        sheet.paste(r, (0, y))
        y += r.size[1] + 20
        ImageDraw.Draw(sheet).line([(0, y - 10), (W, y - 10)], fill=(205, 205, 205), width=2)
    sheet.save(out)


def pair(left, right, labels, out, h=620):
    f = font(22)
    ims = []
    for im in (left, right):
        k = h / im.size[1]
        ims.append(im.resize((max(1, int(im.size[0] * k)), h), Image.LANCZOS))
    W = ims[0].size[0] + ims[1].size[0] + 24
    s = Image.new("RGB", (W, h + 40), (255, 255, 255))
    s.paste(ims[0], (0, 40))
    s.paste(ims[1], (ims[0].size[0] + 24, 40))
    d = ImageDraw.Draw(s)
    d.text((6, 8), labels[0], fill=(0, 0, 0), font=f)
    d.text((ims[0].size[0] + 30, 8), labels[1], fill=(0, 0, 0), font=f)
    s.save(out)


def mask_img(m, pine):
    h, w = m["fg"].shape
    img = np.full((h, w, 3), 205, np.uint8)
    if pine == 4:
        img[m["fg"]] = (95, 95, 95)
    img[m["wood"] & (m["fg"] if pine == 4 else True)] = (120, 70, 30)
    img[m["foliage"] & (m["fg"] if pine == 4 else True)] = (30, 110, 30)
    return Image.fromarray(img)


def _fol_stats(arr, mask):
    px = arr[mask]
    if len(px) == 0:
        return None
    med = np.median(px, 0)
    h, sat, _ = mt.hsv(med[None, None, :])
    return {"median_srgb": med.round().tolist(), "hue": round(float(h[0, 0]), 1), "sat": round(float(sat[0, 0]), 2),
            "p10": np.percentile(px, 10, 0).round().tolist(), "p90": np.percentile(px, 90, 0).round().tolist()}


def look_numbers(rdir, sheet, bg):
    """G11 (foliage render colour) and G13 (bark luma P90/P10) against the sheet, measured the same way."""
    out = {}
    ref = {}
    for name in ("P1F", "P2F", "P3F", "P4F"):
        x0, y0, x1, y1 = rp.PANELS[name]["box"]
        a = sheet[y0:y1, x0:x1]
        m = mt.masks(a, None, bg=bg)
        ref[name] = _fol_stats(a, m["foliage"])
    for name, box in rp.CLOSEUPS.items():
        x0, y0, x1, y1 = box
        a = sheet[y0:y1, x0:x1]
        if name == "bark":
            L = a.reshape(-1, 3) @ np.array([0.2126, 0.7152, 0.0722])
            ref["bark"] = {"median_srgb": np.median(a.reshape(-1, 3), 0).round().tolist(),
                           "luma_p90_p10": round(float(np.percentile(L, 90) / max(np.percentile(L, 10), 1)), 2)}
        else:
            m = mt.masks(a, None, bg=bg)
            ref[f"closeup_{name}"] = _fol_stats(a, m["foliage"])
    out["reference"] = ref
    ours = {}
    for v in SPEC:
        f = rdir / f"{v}_front_final.png"
        if not f.exists():
            continue
        img, alpha = on_grey(f)
        a = np.asarray(img).astype(np.float32)
        m = mt.masks(a, None, bg=np.array(BG, np.float32))
        ours[v] = _fol_stats(a, m["foliage"] & (alpha > 200))
    for name in ("pad_side", "pad_top", "fork"):
        f = rdir / f"closeup_{name}.png"
        if f.exists():
            img, alpha = on_grey(f)
            a = np.asarray(img).astype(np.float32)
            m = mt.masks(a, None, bg=np.array(BG, np.float32))
            ours[f"closeup_{name}"] = _fol_stats(a, m["foliage"] & (alpha > 200))
    f = rdir / "closeup_bark.png"
    if f.exists():
        img, alpha = on_grey(f)
        a = np.asarray(img).astype(np.float32)[alpha > 200]
        L = a @ np.array([0.2126, 0.7152, 0.0722])
        ours["bark"] = {"median_srgb": np.median(a, 0).round().tolist(),
                        "luma_p90_p10": round(float(np.percentile(L, 90) / max(np.percentile(L, 10), 1)), 2)}
    out["ours"] = ours
    rh = np.median([r["hue"] for k, r in ref.items() if k.startswith("P") and r])
    out["G11_hue_ref"] = round(float(rh), 1)
    out["G11_hue_pass"] = {k: bool(abs(o["hue"] - rh) <= 10) for k, o in ours.items() if o and "hue" in o}
    if "bark" in ours:
        out["G13_bark_ratio"] = [ref["bark"]["luma_p90_p10"], ours["bark"]["luma_p90_p10"]]
        out["G13_pass"] = bool(abs(ours["bark"]["luma_p90_p10"] / ref["bark"]["luma_p90_p10"] - 1) <= 0.2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", required=True)
    a = ap.parse_args()
    rdir = Path(a.renders)
    if not rdir.is_absolute():
        rdir = ROOT / rdir
    meta = json.loads((rdir / "render_meta.json").read_text())
    sheet = mt.load_rgb(str(ROOT / rp.SHEET))
    bg = mt.background_colour(sheet[20:60, 300:700])
    ref_img = Image.open(ROOT / rp.SHEET).convert("RGB")
    results = {}
    for v, spec in SPEC.items():
        pine = spec["pine"]
        for view in ("front", "side", "3q"):
            key = f"{v}_{view}"
            if key not in meta or not (rdir / f"{key}_sil.png").exists():
                continue
            rn = ref_panel_name(v, view)
            rm, rbase, rcrop = ref_masks(sheet, bg, rn)
            p = rp.PANELS[rn]
            # v2: the sheet's scale is its 1.8 m figure (heights from the figure, not the old spec heights)
            ref_pxm = (p["figure"][1] - p["figure"][0]) / rp.FIGURE_M
            om, obase, opxm = our_masks(rdir, v, view, meta, pine)
            iou, mr, mo = metrics_pair(rm, rbase, ref_pxm, om, obase, opxm, pine)
            gates = {
                "iou": iou["iou"], "width_err": iou["width_err"],
                "height_m": [mr.get("height_m"), mo.get("height_m")],
                "crown_w_m": [mr.get("crown_w_m"), mo.get("crown_w_m")],
                "lean_m": [mr.get("lean_m"), mo.get("lean_m")],
                "centroid_dx_m": [mr.get("foliage_centroid_dx_m"), mo.get("foliage_centroid_dx_m")],
                "row_fill": [mr.get("row_fill"), mo.get("row_fill")],
                "tiers": [mr.get("tiers"), mo.get("tiers")],
                "pads_auto": [mr.get("pads_auto"), mo.get("pads_auto")],
                "pad_size_cv": [mr.get("pad_size_cv"), mo.get("pad_size_cv")],
                "lr_mass_ratio": [mr.get("lr_mass_ratio"), mo.get("lr_mass_ratio")],
            }
            gates["pass"] = {
                "G4_iou_0.80": iou["iou"] >= 0.80,
                "G4_width_err_0.10": iou["width_err"] <= 0.10,
                "G5_row_fill_0.05": abs((mr.get("row_fill") or 0) - (mo.get("row_fill") or 0)) <= 0.05,
                "G2_crown_w_5pct": abs(mo["crown_w_m"] - mr["crown_w_m"]) <= 0.05 * mr["crown_w_m"],
            }
            results[key] = {"ref_panel": rn, **gates}
            # side-by-sides
            if (rdir / f"{key}_final.png").exists():
                img, alpha = on_grey(rdir / f"{key}_final.png", meta[key]["base_px"][1])
            else:
                img, alpha = on_grey(rdir / f"{key}_sil.png")
            x0, y0, x1, y1 = content_box(alpha)
            y1 = max(y1, int(meta[key]["base_px"][1]) + 8)
            ours = img.crop((x0, y0, x1, y1))
            bx0, by0, bx1, by1 = p["box"]
            pair(ref_img.crop((bx0, by0, bx1, by1)), ours, (f"reference {rn}", f"ours SM_DKN_{v} {view}"),
                 rdir / f"sbs_{key}.png")
            # silhouettes, normalised (heights matched, bases aligned)
            nr = mt.normalise(rm["fg"] if pine == 4 else (rm["foliage"] | rm["wood"]), rbase)
            no = mt.normalise(om["fg"] if pine == 4 else (om["foliage"] | om["wood"]), obase)
            vis = np.full(nr.shape + (3,), 235, np.uint8)
            vis[nr] = (60, 60, 60)
            vis2 = np.full(no.shape + (3,), 235, np.uint8)
            vis2[no] = (60, 60, 60)
            pair(Image.fromarray(vis), Image.fromarray(vis2),
                 (f"reference {rn} silhouette", f"ours {v} {view}: IoU {iou['iou']:.2f}, width err {iou['width_err']:.2f}"),
                 rdir / f"sil_{key}.png", h=400)
    # close-ups
    for name, box in rp.CLOSEUPS.items():
        ours = rdir / f"closeup_{name}.png"
        if ours.exists():
            img, _ = on_grey(ours)
            pair(ref_img.crop(box), img, (f"reference close-up: {name}", "ours"), rdir / f"sbs_closeup_{name}.png", h=560)
    for suffix in ("1", "2"):
        need = [f"Pine{g}{suffix}_{vw}" for g in "ABCD" for vw in ("front", "side", "3q")]
        if all(k in meta and (rdir / f"{k}_final.png").exists() for k in need):
            model_sheet(rdir, meta, suffix, rdir / f"model_sheet_v{suffix}.png")
    summ = {}
    for k, r in results.items():
        summ[k] = f"IoU {r['iou']:.3f} werr {r['width_err']:.3f} crown {r['crown_w_m']} row_fill {r['row_fill']}"
    (rdir / "measure.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    ln = look_numbers(rdir, sheet, bg)
    (rdir / "look_numbers.json").write_text(json.dumps(ln, indent=1), encoding="utf-8")
    print("look:", json.dumps({k: ln[k] for k in ln if k.startswith("G")}))
    for k, s in summ.items():
        print(k, s)


if __name__ == "__main__":
    main()
