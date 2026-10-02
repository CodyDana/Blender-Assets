"""DojoLab ninja look vs DemoGame_1's own male MetaHuman + cloak shots, at the SAME framing (DemoGame_1
Tools/Claude/Cloak/cloak_mh_test.ps1 Cam(): arm 300 / pitch -8 / FOV 70 / no lag, 1600x900, yaw 180 / 90 / 0 / 270, the
two close-ups). DemoGame_1 is only READ (Saved/Claude/Shots/metahuman_cloak/final, the male player of 2026-09-26).

Measures per pair (identical projection, so pixels compare directly):
  dark mask  = the black cloak + hair (luminance < 28 of 255) inside the character ROI; IoU of the two masks, each mask's
               bounding box (top / bottom / left / right / height / width in px) and the box deltas
  head / skin = a skin-tone mask (R > G > B, R - B > 25, luminance 45-200) in the head ROI of the close-ups: centroid and
               area (where the face sits in the cowl opening)
Writes test/look/compare/<pair>.jpg (DemoGame_1 | DojoLab | mask overlay: red = DemoGame only, green = DojoLab only,
yellow = both) and compare.json.
    py -3 -B pt_compare_demogame.py
"""
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

DG = Path("C:/Users/Cody/Documents/Unreal Projects/DemoGame_1/Saved/Claude/Shots/metahuman_cloak/final")
T = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/ninja_character/test/look")
PAIRS = [("b01_front", "L01_front"), ("b02_side_a", "L02_side_a"), ("b03_back", "L03_back"), ("b04_side_b", "L04_side_b"),
         ("b05_close", "L05_close"), ("b06_close_threequarter", "L06_close_threequarter")]
ROI = (520, 330, 1080, 900)        # x0, y0, x1, y1: the character at arm 300 (both projects put it there)
ROI_CLOSE = (300, 450, 1300, 900)


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def character(m, band=(700, 900)):
    """the largest 8-connected dark component that touches the central band (the character; drops the level's dark
    posts, shadows and roof lines that fall inside the ROI)"""
    h, w = m.shape
    lab = np.zeros((h, w), np.int32)
    best, best_n, cur = 0, 0, 0
    ys, xs = np.nonzero(m)
    for y0, x0 in zip(ys, xs):
        if lab[y0, x0]:
            continue
        cur += 1
        q = deque([(y0, x0)])
        lab[y0, x0] = cur
        n, touch = 0, False
        while q:
            y, x = q.popleft()
            n += 1
            touch |= band[0] <= x <= band[1]
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and m[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = cur
                        q.append((yy, xx))
        if touch and n > best_n:
            best, best_n = cur, n
    return lab == best if best else np.zeros_like(m)


def bbox(m):
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        return None
    return {"top": int(ys.min()), "bottom": int(ys.max()), "left": int(xs.min()), "right": int(xs.max()),
            "h": int(ys.max() - ys.min() + 1), "w": int(xs.max() - xs.min() + 1), "area": int(m.sum()),
            "cx": round(float(xs.mean()), 1), "cy": round(float(ys.mean()), 1)}


def main():
    out = {}
    (T / "compare").mkdir(exist_ok=True)
    for dg, dl in PAIRS:
        a = np.asarray(Image.open(DG / f"{dg}.png").convert("RGB").resize((1600, 900))).astype(np.float32)
        b = np.asarray(Image.open(T / "shots" / f"{dl}.png").convert("RGB").resize((1600, 900))).astype(np.float32)
        roi = ROI_CLOSE if "close" in dl else ROI
        x0, y0, x1, y1 = roi
        ma = np.zeros(a.shape[:2], bool)
        mb = np.zeros(b.shape[:2], bool)
        ma[y0:y1, x0:x1] = lum(a)[y0:y1, x0:x1] < 28
        mb[y0:y1, x0:x1] = lum(b)[y0:y1, x0:x1] < 28
        ma, mb = character(ma), character(mb)
        inter, union = (ma & mb).sum(), (ma | mb).sum()
        ba, bb = bbox(ma), bbox(mb)
        rec = {"iou_dark": round(float(inter / union), 3) if union else None, "demogame_box": ba, "dojolab_box": bb}
        if ba and bb:
            rec["box_delta_px"] = {k: bb[k] - ba[k] for k in ("top", "bottom", "left", "right", "h", "w")}
            rec["area_ratio"] = round(bb["area"] / ba["area"], 3)
        if "close" in dl:
            def skin(x):
                r, g, bl = x[..., 0], x[..., 1], x[..., 2]
                L = lum(x)
                m = (r > g) & (g > bl) & ((r - bl) > 25) & (L > 45) & (L < 200)
                mm = np.zeros(m.shape, bool)
                mm[y0:y1, x0:x1] = m[y0:y1, x0:x1]
                return mm
            sa, sb = skin(a), skin(b)
            rec["skin_demogame"], rec["skin_dojolab"] = bbox(sa), bbox(sb)
            if rec["skin_demogame"] and rec["skin_dojolab"]:
                rec["skin_centroid_delta_px"] = [round(rec["skin_dojolab"]["cx"] - rec["skin_demogame"]["cx"], 1),
                                                 round(rec["skin_dojolab"]["cy"] - rec["skin_demogame"]["cy"], 1)]
            # hair: dark pixels above the skin top in the close-ups -> mean colour (lighting differs between the levels)
        ov = np.zeros(a.shape, np.uint8)
        ov[ma & ~mb] = (220, 40, 40)
        ov[mb & ~ma] = (40, 200, 40)
        ov[ma & mb] = (230, 210, 40)
        W = 640
        H = 360
        S = Image.new("RGB", (W * 3, H + 18), (0, 0, 0))
        for i, im in enumerate((a.astype(np.uint8), b.astype(np.uint8), ov)):
            S.paste(Image.fromarray(im).resize((W, H)), (i * W, 18))
        d = ImageDraw.Draw(S)
        d.text((4, 3), f"DemoGame_1 {dg}", fill=(255, 230, 80))
        d.text((W + 4, 3), f"DojoLab {dl}", fill=(255, 230, 80))
        d.text((2 * W + 4, 3), f"dark-mask IoU {rec['iou_dark']} (red DG only, green DojoLab only)", fill=(255, 230, 80))
        S.save(T / "compare" / f"{dl}.jpg", quality=90)
        out[dl] = rec
    (T / "compare" / "compare.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, v["iou_dark"], v.get("box_delta_px"), v.get("area_ratio"), v.get("skin_centroid_delta_px"))


if __name__ == "__main__":
    main()
