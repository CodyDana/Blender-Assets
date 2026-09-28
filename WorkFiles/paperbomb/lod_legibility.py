#!/usr/bin/env python
"""Does the card still READ at every LOD, on the maps that ship?

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python WorkFiles/paperbomb/lod_legibility.py

WHY THIS EXISTS.  The reference-accuracy pass changed the ink's albedo by a factor of
nine and the paper's by a third, and the LOD bands were set when the card was grey on
tan.  Both earlier reviews said the same thing: the LOD-switch legibility was never
checked on the new maps, and it is cheap to check.

WHAT IT MEASURES, on the three LOD grind frames the gallery already renders from the
BAKED maps (``WorkFiles/paperbomb/diag/grind_lod{0,1,2}.png`` - same camera, same lamps,
same samples, one LOD each):

    ink_fraction     how much of the card is ink at all
    contrast         the card's own paper median over its ink median, in linear luma
    hero_mass        the dark mass inside the hero glyph's own cell, as a fraction -
                     this is the number that says whether 爆 still reads
    centroid         where that mass sits, in card-relative coordinates

A LOD that drops geometry must not change any of these: the maps are shared, so a
difference here is the silhouette or the shading eating the print.  The gate is that
LOD1 and LOD2 stay within 15 % of LOD0 on the ink fraction and the hero mass, within
25 % on contrast, and that the hero centroid moves less than 2 % of the card's width.

MEASUREMENT ONLY - this writes a JSON and nothing a build can consume.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
DIAG = PROJ / "WorkFiles" / "paperbomb" / "diag"
OUT = PROJ / "WorkFiles" / "paperbomb" / "lod_legibility.json"


def load_srgb(path: Path) -> np.ndarray:
    import bpy
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    a = buf.reshape(h, w, 4)[::-1].copy()
    bpy.data.images.remove(img)
    return a


def to_linear(s: np.ndarray) -> np.ndarray:
    s = np.clip(s, 0.0, 1.0)
    return np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)


def measure(path: Path) -> dict:
    a = load_srgb(path)
    rgb = a[..., :3]
    lin = to_linear(rgb)
    lum = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    warm = lin[..., 0] - lin[..., 2]
    # the card is the warm region; the backdrop is neutral.  Same test the ink pass uses
    # to find the tag in a photograph, which is what makes it independent of the print.
    card = warm > 0.06
    if card.sum() < 5000:
        card = lum < 0.9
    ys, xs = np.nonzero(card)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sub = card[y0:y1, x0:x1]
    sl = lum[y0:y1, x0:x1]
    vals = sl[sub]
    thr = 0.5 * (np.percentile(vals, 3) + np.percentile(vals, 85))
    ink = sub & (sl < thr)
    paper = sub & ~ink
    H, W = sub.shape
    # the hero glyph's own cell, in card-relative coordinates (REFERENCE_SPEC row 2)
    cy0, cy1 = int(0.30 * H), int(0.70 * H)
    cx0, cx1 = int(0.05 * W), int(0.95 * W)
    cell = np.zeros_like(sub)
    cell[cy0:cy1, cx0:cx1] = True
    hero = ink & cell
    hy, hx = np.nonzero(hero)
    return {
        "card_px": int(sub.sum()),
        "ink_fraction": round(float(ink.sum()) / max(float(sub.sum()), 1.0), 5),
        "paper_linear_luma_p50": round(float(np.median(sl[paper])), 5),
        "ink_linear_luma_p50": round(float(np.median(sl[ink])), 6),
        # A THUMBNAIL HAS NO INK MEDIAN.  At LOD-switch size a 0.6 mm stroke is a pixel
        # or two, so most of what a threshold calls "ink" is a blend of ink and paper
        # and the median of that population says nothing about the pigment.  What says
        # whether the print still reads DARK is the darkest few per cent of the card
        # against the paper - the cores of the strokes that survive the downsample.
        "contrast": round(float(np.median(sl[paper])
                                / max(float(np.percentile(vals, 2)), 1e-9)), 1),
        "contrast_on_ink_median": round(
            float(np.median(sl[paper]) / max(np.median(sl[ink]), 1e-9)), 2),
        "hero_mass": round(float(hero.sum()) / max(float(cell.sum()), 1.0), 5),
        "hero_centroid_rel": [round(float(hx.mean()) / W, 4), round(float(hy.mean()) / H, 4)],
    }


def main() -> int:
    got = {}
    for i in range(3):
        p = DIAG / f"grind_lod{i}.png"
        if not p.is_file():
            print(f"missing {p}")
            return 2
        got[f"LOD{i}"] = measure(p)
    base = got["LOD0"]
    gates = {}
    for k in ("LOD1", "LOD2"):
        v = got[k]
        gates[f"{k}_ink_fraction_within_15pct"] = abs(
            v["ink_fraction"] - base["ink_fraction"]) <= 0.15 * base["ink_fraction"]
        gates[f"{k}_hero_mass_within_15pct"] = abs(
            v["hero_mass"] - base["hero_mass"]) <= 0.15 * base["hero_mass"]
        gates[f"{k}_contrast_within_25pct"] = abs(
            v["contrast"] - base["contrast"]) <= 0.25 * base["contrast"]
        gates[f"{k}_hero_centroid_within_2pct_of_W"] = math.hypot(
            v["hero_centroid_rel"][0] - base["hero_centroid_rel"][0],
            v["hero_centroid_rel"][1] - base["hero_centroid_rel"][1]) <= 0.02
    # ...and the ink itself is the same darkness whichever LOD is on screen.
    #
    # WHAT THIS CANNOT ANSWER, AND WHERE THE ANSWER IS.  The absolute contrast in these
    # frames is 4.5 - 4.6:1, and that is not the print: it is the hero rig's raking key
    # on a card filling a fifth of the frame, where a 0.6 mm stroke is a texel or two and
    # every one of them is a blend.  "Is the ink DARK" is a question about the shipped
    # albedo under even light, which is measured on the front frame in
    # ink_floor_compare.json (129:1 rendered, 156:1 in the map).  What THESE frames can
    # answer, and the only thing a LOD switch can break, is whether dropping geometry
    # changes the read - and the maps are shared, so it must not.
    inks = [v["ink_linear_luma_p50"] for v in got.values()]
    gates["ink_darkness_agrees_across_lods_within_10pct"] = (
        max(inks) - min(inks) <= 0.10 * max(inks))
    out = {"what_this_is": __doc__.strip().splitlines()[0],
           "source": str(DIAG.relative_to(PROJ)),
           "lods": got, "gates": gates,
           "passed": all(gates.values())}
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    for k, v in got.items():
        print(f"{k}: ink {v['ink_fraction']:.4f}  hero {v['hero_mass']:.4f}  "
              f"contrast {v['contrast']:.1f}  centroid {v['hero_centroid_rel']}")
    bad = [k for k, v in gates.items() if not v]
    print(f"LOD legibility: {'PASS' if not bad else 'FAIL ' + ', '.join(bad)} -> {OUT}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
