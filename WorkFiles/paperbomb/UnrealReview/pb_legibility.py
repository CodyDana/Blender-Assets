"""Legibility of SM_PaperBomb at the LOD1 / LOD2 switch distances, measured on the shipped bytes.

Reads the EXACT Exports/PaperBomb/Textures/T_PaperBomb_BC.png and the EXACT
Exports/PaperBomb/SM_PaperBomb.fbx.  Nothing is written except JSON and preview
PNGs under WorkFiles/paperbomb/UnrealReview/.

Method
------
1. Re-import the shipped FBX; take LOD0's front face (polygon normal +Z) and read
   its UV0 bounding box -> the front island's rectangle on the 2048 map, plus the
   sign of the mapping between card millimetres and UV.
2. Read the BC map with colourspace forced to Non-Color, so image.pixels are the
   stored sRGB bytes / 255 (the same convention the study used).
3. Measure the real ink bounding boxes of the centre glyph and of each column in
   card fractions, classifying black ink (low luma, low saturation) and red ink
   (R-G large).
4. Unreal's ComputeBoundsScreenSize keeps the horizontal FOV, so with aspect > 1
   the screen size is a fraction of screen HEIGHT:
       S = 2 * max(0.5 P00, 0.5 P11) * R / d,  P11 = aspect / tan(hfov/2)
   Therefore at the switch the bounding SPHERE diameter spans S of the height:
       px_per_mm = S * height_px / (2 * R_mm)
5. Box-downsample the front island to exactly the on-screen size at each switch
   (the honest approximation of what trilinear/aniso filtering delivers), and
   write a nearest-neighbour magnification of it so a human can LOOK at it.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealReview"
FBX = PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.fbx"
BC = PROJ / "Exports" / "PaperBomb" / "Textures" / "T_PaperBomb_BC.png"
OUT = HERE / "pb_legibility.json"

SCREEN_H = 1080.0
HFOV = 90.0
ASPECT = 16.0 / 9.0
SCREEN_SIZES = [1.0, 0.171, 0.0598]

# Study windows in CARD FRACTIONS (x from the left of the printed face seen from +Z, y from the top).
# Each is a generous box around the element; the ink bbox is MEASURED inside it.
WINDOWS = {
    "centre_glyph":  {"x": (0.06, 0.96), "y": (0.28, 0.72), "ink": "black", "nominal_em_mm": 67.1},
    "upper_left":    {"x": (0.06, 0.30), "y": (0.04, 0.33), "ink": "black", "nominal_em_mm": 14.4},
    "upper_right":   {"x": (0.70, 0.94), "y": (0.04, 0.33), "ink": "black", "nominal_em_mm": 14.4},
    "lower_right":   {"x": (0.72, 0.94), "y": (0.63, 0.81), "ink": "black", "nominal_em_mm": 14.0},
    "lower_centre":  {"x": (0.37, 0.63), "y": (0.70, 0.92), "ink": "black", "nominal_em_mm": 16.1},
    "small_seal":    {"x": (0.80, 0.90), "y": (0.80, 0.90), "ink": "red",   "nominal_em_mm": 7.5},
}


def front_island():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    ob = bpy.data.objects["SM_PaperBomb_LOD0"]
    me = ob.data
    uv = me.uv_layers[0].data
    mw = ob.matrix_world
    us, vs, xs, ys = [], [], [], []
    for p in me.polygons:
        n = mw.to_3x3() @ p.normal
        if n.z <= 0.5:
            continue
        for li in p.loop_indices:
            vi = me.loops[li].vertex_index
            co = mw @ me.vertices[vi].co
            us.append(uv[li].uv[0]); vs.append(uv[li].uv[1])
            xs.append(co.x * 1000.0); ys.append(co.y * 1000.0)   # mm, asset frame (+X top, +Y left)
    us = np.array(us); vs = np.array(vs); xs = np.array(xs); ys = np.array(ys)
    # card fraction: X_mm = (0.5 - y_frac) * 156 -> y_frac = 0.5 - x_mm/156 ; x_frac = 0.5 - y_mm/70
    # which axis of UV carries which? correlate.
    def slope(a, b):
        return float(np.polyfit(a, b, 1)[0])
    return {
        "u": (float(us.min()), float(us.max())),
        "v": (float(vs.min()), float(vs.max())),
        "du_per_mm_along_cardY": slope(ys, us),   # card x direction
        "dv_per_mm_along_cardX": slope(xs, vs),   # card y direction
        "x_mm": (float(xs.min()), float(xs.max())),
        "y_mm": (float(ys.min()), float(ys.max())),
    }


def load_bc():
    img = bpy.data.images.load(str(BC))
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    arr = px.reshape(h, w, 4)          # row 0 is the BOTTOM of the image (v = 0)
    return arr, w, h


def write_png(name, rgb):
    """rgb: (h, w, 3) float 0..1 in STORED sRGB; written straight out as bytes."""
    h, w, _ = rgb.shape
    img = bpy.data.images.new(name, width=w, height=h, alpha=False, float_buffer=False)
    img.colorspace_settings.name = "Non-Color"
    flat = np.concatenate([rgb.astype(np.float32), np.ones((h, w, 1), np.float32)], axis=2).ravel()
    img.pixels.foreach_set(flat)
    img.file_format = "PNG"
    path = HERE / name
    img.filepath_raw = str(path)
    img.save()
    return str(path)


def box_down(a, out_w, out_h):
    h, w, c = a.shape
    yi = (np.arange(out_h + 1) * h / out_h).astype(int)
    xi = (np.arange(out_w + 1) * w / out_w).astype(int)
    out = np.empty((out_h, out_w, c), np.float32)
    for j in range(out_h):
        for i in range(out_w):
            out[j, i] = a[yi[j]:max(yi[j] + 1, yi[j + 1]), xi[i]:max(xi[i] + 1, xi[i + 1])].reshape(-1, c).mean(0)
    return out


def nn_up(a, f):
    return np.repeat(np.repeat(a, f, axis=0), f, axis=1)


def main():
    rep = {"bc": str(BC), "screen_height_px": SCREEN_H, "hfov_deg": HFOV, "aspect": ASPECT}
    isl = front_island()
    rep["front_island_uv"] = isl
    arr, W, H = load_bc()
    rep["bc_size"] = [W, H]

    u0, u1 = isl["u"]; v0, v1 = isl["v"]
    px0, px1 = int(round(u0 * W)), int(round(u1 * W))
    # image row 0 = v 0 (bottom); crop in row space directly
    py0, py1 = int(round(v0 * H)), int(round(v1 * H))
    rep["front_island_px"] = {"u": [px0, px1], "v_rows": [py0, py1],
                              "size_px": [px1 - px0, py1 - py0]}
    isl_rgb = arr[py0:py1, px0:px1, :3].copy()
    ih, iw, _ = isl_rgb.shape

    # card-fraction axes of the crop.  Card +X (top of tag) maps to v with sign dv_per_mm_along_cardX.
    # y_frac = 0.5 - x_mm/156 : so y_frac 0 (top of tag) is x_mm = +78.
    top_is_high_v = isl["dv_per_mm_along_cardX"] > 0
    left_is_high_u = isl["du_per_mm_along_cardY"] > 0   # card x_frac 0 is y_mm = +35 (left)
    rep["orientation"] = {"card_top_at_high_v": bool(top_is_high_v),
                          "card_left_at_high_u": bool(left_is_high_u)}

    def frac_to_crop(xf, yf):
        """card fraction -> (col, row) in the cropped island array (row 0 = low v)."""
        col = (1.0 - xf) * (iw - 1) if left_is_high_u else xf * (iw - 1)
        row = (1.0 - yf) * (ih - 1) if top_is_high_v else yf * (ih - 1)
        return col, row

    lum = isl_rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    mx = isl_rgb.max(2); mn = isl_rgb.min(2)
    sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    black = (lum < 0.35) & (sat < 0.18)
    red = ((isl_rgb[:, :, 0] - isl_rgb[:, :, 1]) > 0.25) & (isl_rgb[:, :, 0] > 0.22)
    rep["ink_coverage"] = {"black": round(float(black.mean()), 4), "red": round(float(red.mean()), 4),
                           "total": round(float((black | red).mean()), 4)}

    card_w_mm, card_h_mm = 69.865, 155.931
    mm_per_col = card_w_mm / (iw - 1)
    mm_per_row = card_h_mm / (ih - 1)
    rep["island_px_per_mm"] = {"across": round((iw - 1) / card_w_mm, 4), "along": round((ih - 1) / card_h_mm, 4)}

    elements = {}
    for name, spec in WINDOWS.items():
        c0, r0 = frac_to_crop(spec["x"][0], spec["y"][0])
        c1, r1 = frac_to_crop(spec["x"][1], spec["y"][1])
        cc0, cc1 = int(min(c0, c1)), int(max(c0, c1))
        rr0, rr1 = int(min(r0, r1)), int(max(r0, r1))
        mask = (black if spec["ink"] == "black" else red)[rr0:rr1 + 1, cc0:cc1 + 1]
        ys_, xs_ = np.nonzero(mask)
        if len(ys_) == 0:
            elements[name] = {"found": False}
            continue
        w_mm = (xs_.max() - xs_.min() + 1) * mm_per_col
        h_mm = (ys_.max() - ys_.min() + 1) * mm_per_row
        elements[name] = {"found": True, "ink_px": int(mask.sum()),
                          "ink_w_mm": round(float(w_mm), 3), "ink_h_mm": round(float(h_mm), 3),
                          "nominal_em_mm": spec["nominal_em_mm"],
                          "coverage_in_window": round(float(mask.mean()), 4)}
    rep["elements"] = elements

    # ---- screen projection ----
    R_mm = 85.483
    proj = {}
    for i, S in enumerate(SCREEN_SIZES[1:], start=1):
        px_per_mm = S * SCREEN_H / (2.0 * R_mm)
        mult = max(1.0, ASPECT) / math.tan(math.radians(0.5 * HFOV))
        dist_m = mult * (R_mm / 1000.0) / S
        entry = {"screen_size": S, "switch_distance_m": round(dist_m, 4),
                 "px_per_mm_at_1080p": round(px_per_mm, 4),
                 "mm_per_screen_px": round(1.0 / px_per_mm, 4),
                 "card_px": [round(card_w_mm * px_per_mm, 1), round(card_h_mm * px_per_mm, 1)],
                 "island_minification": round((iw - 1) / (card_w_mm * px_per_mm), 3)}
        entry["mip_sampled"] = round(math.log2(entry["island_minification"]), 2)
        el = {}
        for name, e in elements.items():
            if not e.get("found"):
                continue
            el[name] = {"ink_w_px": round(e["ink_w_mm"] * px_per_mm, 2),
                        "ink_h_px": round(e["ink_h_mm"] * px_per_mm, 2),
                        "em_px": round(e["nominal_em_mm"] * px_per_mm, 2)}
        entry["elements_px"] = el
        # fine features from the study
        entry["red_rule_0p90mm_px"] = round(0.90 * px_per_mm, 3)
        entry["side_lozenge_0p56mm_px"] = round(0.56 * px_per_mm, 3)
        proj[f"LOD{i}_switch"] = entry
    rep["projection"] = proj

    # ---- what it actually looks like ----
    previews = {}
    for i, S in enumerate(SCREEN_SIZES[1:], start=1):
        px_per_mm = S * SCREEN_H / (2.0 * R_mm)
        ow = max(1, int(round(card_w_mm * px_per_mm)))
        oh = max(1, int(round(card_h_mm * px_per_mm)))
        small = box_down(isl_rgb, ow, oh)
        f = max(1, int(round(700.0 / oh)))
        previews[f"LOD{i}_switch"] = {"on_screen_px": [ow, oh], "magnification": f,
                                      "png": write_png(f"pb_lod{i}_switch_{ow}x{oh}_x{f}.png", nn_up(small, f))}
    # a full-size reference of the same crop, downsampled to a viewable height
    ref = box_down(isl_rgb, int(round(iw * 700.0 / ih)), 700)
    previews["reference_700"] = {"png": write_png("pb_front_reference_700.png", ref)}
    rep["previews"] = previews

    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("PB_LEGIBILITY_DONE " + str(OUT))
    print(json.dumps({"front_island_px": rep["front_island_px"], "orientation": rep["orientation"],
                      "ink_coverage": rep["ink_coverage"], "elements": elements,
                      "projection": proj}, indent=2))


main()
