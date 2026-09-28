"""Does T_PaperBomb_M carry what the sidecar and the study say it carries?

The fourth map is the one the pack's own texture importer skips, so nothing has
checked its contents in engine terms.  Claimed:
    R = torn-edge opacity / fibre fringe   -> should live at the card's edges,
                                              concentrated on the bottom edge
    G = scorch gradient radiating from the Fuse socket
                                           -> its peak should sit at the Fuse
                                              socket's card position, x 0.5,
                                              y 0.196 (47.4 mm from the centre,
                                              at the flame emblem)
    B = ink mask for recolouring           -> should agree with the ink in BC
"""
import json
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealReview"
TEX = PROJ / "Exports" / "PaperBomb" / "Textures"
OUT = HERE / "pbr_mask_check.json"
ISLAND = (16, 921, 16, 2032)
CARD_W, CARD_H = 69.865, 155.931
FUSE_X_MM = 47.365                      # asset frame; y_frac = 0.5 - 47.365/155.931


def load(name):
    img = bpy.data.images.load(str(TEX / f"{name}.png"))
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(h, w, 4)


def main():
    u0, u1, v0, v1 = ISLAND
    m = load("T_PaperBomb_M")[v0:v1, u0:u1, :3]
    bc = load("T_PaperBomb_BC")[v0:v1, u0:u1, :3]
    h, w, _ = m.shape
    # card fractions: card top is at HIGH v, card left at LOW u (measured in pb_legibility.py)
    yf = 1.0 - (np.arange(h)[:, None] / (h - 1)) * np.ones((1, w), np.float32)
    xf = (np.arange(w)[None, :] / (w - 1)) * np.ones((h, 1), np.float32)

    lum = bc @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    mxc = bc.max(2); mnc = bc.min(2)
    sat = np.where(mxc > 1e-6, (mxc - mnc) / np.maximum(mxc, 1e-6), 0.0)
    ink = ((lum < 0.35) & (sat < 0.18)) | (((bc[:, :, 0] - bc[:, :, 1]) > 0.25) & (bc[:, :, 0] > 0.22))

    rep = {"island_px": list(ISLAND), "channels": {}}
    names = {0: "R_torn_edge_fibre_fringe", 1: "G_scorch_from_Fuse", 2: "B_ink_mask"}
    for c in range(3):
        ch = m[:, :, c]
        ent = {"mean": round(float(ch.mean()), 5), "min": round(float(ch.min()), 5),
               "max": round(float(ch.max()), 5), "std": round(float(ch.std()), 5),
               "fraction_above_0_5": round(float((ch > 0.5).mean()), 5)}
        wsum = float(ch.sum())
        if wsum > 1e-6:
            ent["centroid_card_frac_xy"] = [round(float((ch * xf).sum() / wsum), 4),
                                            round(float((ch * yf).sum() / wsum), 4)]
        rep["channels"][names[c]] = ent

    # R: is it an edge band?  compare the outer 3 mm ring with the interior
    edge_mm = 3.0
    ring = (xf * CARD_W < edge_mm) | ((1 - xf) * CARD_W < edge_mm) | \
           (yf * CARD_H < edge_mm) | ((1 - yf) * CARD_H < edge_mm)
    bottom = (1 - yf) * CARD_H < 16.0
    rep["R_edge_behaviour"] = {
        "mean_in_outer_3mm_ring": round(float(m[:, :, 0][ring].mean()), 5),
        "mean_in_interior": round(float(m[:, :, 0][~ring].mean()), 5),
        "mean_in_bottom_16mm": round(float(m[:, :, 0][bottom].mean()), 5),
    }

    # G: where is the peak, and does it fall off with distance from the Fuse socket?
    g = m[:, :, 1]
    gi = int(np.argmax(g))
    peak = [round(float(xf.ravel()[gi]), 4), round(float(yf.ravel()[gi]), 4)]
    fuse_yf = 0.5 - FUSE_X_MM / CARD_H
    d_mm = np.sqrt(((xf - 0.5) * CARD_W) ** 2 + ((yf - fuse_yf) * CARD_H) ** 2)
    bands = {}
    for lo, hi in ((0, 10), (10, 25), (25, 50), (50, 100), (100, 200)):
        sel = (d_mm >= lo) & (d_mm < hi)
        if sel.sum():
            bands[f"{lo}-{hi}mm"] = round(float(g[sel].mean()), 5)
    rep["G_scorch_behaviour"] = {
        "fuse_card_frac_xy": [0.5, round(float(fuse_yf), 4)],
        "peak_card_frac_xy": peak,
        "peak_value": round(float(g.max()), 5),
        "mean_by_distance_from_fuse": bands,
        "monotonic_falloff": all(list(bands.values())[i] >= list(bands.values())[i + 1]
                                 for i in range(len(bands) - 1)),
    }

    # B: agreement with the ink actually drawn in BC
    b = m[:, :, 2] > 0.5
    inter = float((b & ink).sum()); union = float((b | ink).sum())
    rep["B_ink_agreement"] = {
        "bc_ink_fraction": round(float(ink.mean()), 5),
        "mask_fraction": round(float(b.mean()), 5),
        "intersection_over_union": round(inter / union, 5) if union else None,
        "recall_of_bc_ink": round(inter / float(ink.sum()), 5) if ink.sum() else None,
    }
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=2))


main()
