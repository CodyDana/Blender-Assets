"""LANDSCAPE ROUND (world stage): measurements on the -game HighResShot stills (plain Python + PIL/numpy).

1. LANDSCAPE_vs_OURS.png: dojo_landscape_ref.png | CAM_LandscapeRef, both at the reference's 1024 x 1536 (our still is
   captured at 1280 x 1920, the same 2:3 frame, and resampled).
2. Matched-framing numbers (the reference camera fit): whole-frame luma (Rec.709 on sRGB) share under 40, mean, p10, p90,
   clipped share; region colours (median sRGB, HLS hue / saturation, R/B) in boxes on the 1024 x 1536 frame, placed from
   the plan's reference-camera landmarks (ref_camera_check): sky, peaks, forest slopes, river water, foam, the terrace
   wall, the compound. The same boxes on both images (the camera is the plan's fit; the plan measured the landmark
   error at 12-116 px, so the boxes are generous).
3. Landmark check: the plan's projected pixels are listed with our capture's local contrast there (information).
4. Per-still health for every capture: share under luma 40, mean, p10, p90, clipped.
usage: py -3 -B measure_landscape.py <caps dir>          out: <caps>/json/measure_landscape.json + the sheets
"""
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
REF = ROOT / "References/Dojo/dojo_landscape_ref.png"
WH = (1024, 1536)
BOXES = {
    "sky": [(80, 150, 480, 400)],
    "peaks": [(290, 445, 420, 530), (500, 480, 640, 560)],
    "forest_slopes": [(60, 540, 250, 650), (640, 600, 900, 700)],
    "river_water": [(480, 1180, 640, 1330), (420, 1330, 560, 1450)],
    "foam": [(600, 960, 780, 1080), (640, 1080, 860, 1180)],
    "terrace_wall": [(240, 950, 480, 1030), (450, 880, 640, 950)],
    "compound": [(40, 820, 660, 900)],
}


def luma(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def stats(a):
    L = luma(a)
    return {"under40_pct": round(float((L < 40).mean() * 100), 2), "mean": round(float(L.mean()), 1),
            "p10": round(float(np.percentile(L, 10)), 1), "p90": round(float(np.percentile(L, 90)), 1),
            "clipped_pct": round(float((a.max(-1) >= 254).mean() * 100), 2)}


def region(a, boxes):
    px = np.concatenate([a[y0:y1, x0:x1].reshape(-1, 3) for x0, y0, x1, y1 in boxes])
    m = np.median(px, 0)
    h, l, s = colorsys.rgb_to_hls(*(m / 255.0))
    return {"median_srgb": [round(float(v), 1) for v in m], "hue_deg": round(h * 360, 1), "sat": round(s, 3),
            "light": round(l, 3), "r_over_b": round(float(m[0] / max(m[2], 1)), 3)}


def load(p, size=None):
    im = Image.open(p).convert("RGB")
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return im


def sheet(a_im, b_im, path, labels):
    h = max(a_im.size[1], b_im.size[1])
    s = Image.new("RGB", (a_im.size[0] + b_im.size[0] + 10, h + 40), (20, 20, 20))
    s.paste(a_im, (0, 40))
    s.paste(b_im, (a_im.size[0] + 10, 40))
    d = ImageDraw.Draw(s)
    d.text((10, 12), labels[0], fill=(240, 240, 240))
    d.text((a_im.size[0] + 20, 12), labels[1], fill=(240, 240, 240))
    s.save(path)


def main():
    caps = Path(sys.argv[1])
    out = {"frame": WH, "boxes": BOXES}
    ref = load(REF, WH)
    ours_p = caps / "CAM_LandscapeRef.png"
    if ours_p.exists():
        ours = load(ours_p, WH)
        sheet(ref, ours, caps / "LANDSCAPE_vs_OURS.png", ("reference dojo_landscape_ref.png (daytime)",
                                                          "ours CAM_LandscapeRef (sunset kept: UDS 1730)"))
        A, B = np.asarray(ref, float), np.asarray(ours, float)
        def foam_share(a, boxes):
            px = np.concatenate([a[y0:y1, x0:x1].reshape(-1, 3) for x0, y0, x1, y1 in boxes])
            mx, mn = px.max(1), px.min(1)
            sat = (mx - mn) / np.maximum(mx, 1)
            lum = px @ np.array([0.2126, 0.7152, 0.0722])
            foam = (lum > 140) & (sat < 0.28)
            water = foam | ((px[:, 2] > px[:, 0]) & (px[:, 1] > px[:, 0]))
            return {"foam_pct_of_water": round(float(foam.sum() / max(water.sum(), 1) * 100), 1),
                    "water_px": int(water.sum())}
        rapids = BOXES["foam"]
        out["foam"] = {"boxes": rapids, "reference": foam_share(A, rapids), "ours": foam_share(B, rapids),
                       "rule": "foam = luma > 140 and HSV saturation < 0.28; water = foam or (G > R and B > R)"}
        out["landscape_ref"] = {"reference": stats(A), "ours": stats(B),
                                "regions": {k: {"reference": region(A, v), "ours": region(B, v)} for k, v in BOXES.items()}}
        # the boxes drawn on ours for the record
        dbg = ours.copy()
        d = ImageDraw.Draw(dbg)
        for k, bx in BOXES.items():
            for x0, y0, x1, y1 in bx:
                d.rectangle([x0, y0, x1, y1], outline=(255, 60, 60))
                d.text((x0 + 3, y0 + 3), k, fill=(255, 255, 0))
        dbg.save(caps / "json_boxes_CAM_LandscapeRef.png")
    r2 = ROOT / "References/Dojo/dojo1_reference2.png"
    o2 = caps / "CAM_Ref2Match.png"
    if o2.exists():
        a = load(r2)
        sheet(a, load(o2, a.size), caps / "REF2_vs_OURS.png", ("reference 2 (dojo1_reference2.png)", "ours CAM_Ref2Match"))
    out["health"] = {}
    for p in sorted(caps.glob("CAM_*.png")):
        out["health"][p.stem] = dict(stats(np.asarray(load(p), float)), size=list(Image.open(p).size))
    (caps / "json").mkdir(exist_ok=True)
    (caps / "json" / "measure_landscape.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out.get("landscape_ref", {}).get("reference")), json.dumps(out.get("landscape_ref", {}).get("ours")))


main()
