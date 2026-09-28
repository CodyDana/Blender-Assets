"""Side-by-side diagnostic: the reference photo (measurement only - never used in any shipped asset) | our kunai rendered
in the photo's pose with the shipped baked maps.  Edges, ridge line, crease and the measurement stations are drawn on
both; each station is labelled with its face_slope (photo: reconciled; ours: analytic, and what the validated procedure
reads back from our render)."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import section_procedure as SP  # noqa: E402
from run_validate import FV, x_of_fvis  # noqa: E402

HERE = Path(__file__).parent
REC = json.loads((HERE / "photo_reconciled.json").read_text())
CHK = json.loads((HERE / "validate" / "final_check.json").read_text())["v9_z1_roll5@0.7"]["rows"]
W, H = 1000, 666
HEAD, FOOT = 64, 150


def font(size, bold=False):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + name, size)
        except OSError:
            continue
    return ImageFont.load_default()


F_T, F_L, F_S = font(24, True), font(17, True), font(15)
EDGE, RIDGE, STN, CREASE = (255, 214, 64), (64, 220, 255), (255, 90, 170), (170, 255, 120)


def poly(draw, pts, col, w=2):
    draw.line([tuple(map(float, p)) for p in pts], fill=col, width=w)


def annotate(img, blade, scale, stations, labels, crease_s, end_s):
    d = ImageDraw.Draw(img)
    ss = np.linspace(0.0, end_s, 120)
    for fn in (blade.top, blade.bot):
        poly(d, [blade.P(s, fn(s)) * scale for s in ss], EDGE, 2)
    poly(d, [blade.P(s, blade.ridge(s)) * scale for s in ss], RIDGE, 2)
    poly(d, [blade.P(crease_s, blade.bot(crease_s)) * scale, blade.P(crease_s, blade.top(crease_s)) * scale], CREASE, 2)
    for k, s in enumerate(stations):
        a = blade.P(s, blade.bot(s) - 4 / scale) * scale
        b = blade.P(s, blade.top(s) + 4 / scale) * scale
        poly(d, [a, b], STN, 2)
        tx, ty = b + np.array([-6.0, -22.0])
        box = d.textbbox((tx, ty), str(k + 1), font=F_S)
        d.rectangle([box[0] - 3, box[1] - 2, box[2] + 3, box[3] + 2], fill=(0, 0, 0))
        d.text((tx, ty), str(k + 1), font=F_S, fill=(255, 255, 255))
    # station table, lower right of the panel
    x0, y0 = img.width - 430, img.height - 34 - 22 * len(labels)
    d.rectangle([x0 - 10, y0 - 34, img.width - 10, img.height - 10], fill=(0, 0, 0))
    d.text((x0, y0 - 28), labels[0][0], font=F_L, fill=(255, 230, 150))
    for k, lab in enumerate(labels[1:]):
        d.text((x0, y0 + 22 * k), f"{k + 1}  " + lab, font=F_S, fill=(255, 255, 255))


def main():
    # ---------------- left: photo (x2, measurement overlay)
    M = json.loads(Path(SP.BS + "/photo_A/measure_raw.json").read_text())
    blade_p = SP.blade_from_lines(M)
    ph = Image.open(SP.PHOTO_PATH).convert("RGB").resize((W, H), Image.LANCZOS)
    st = REC["stations"]
    s_ph = [r["frac_from_shoulder"] * M["L_visible_px"] for r in st]
    lab_ph = [("st  frac   our x    face_slope (p10-p90)   ridge_ratio*",)] + [
        f"{r['frac_from_shoulder']:.2f}   {r['ours_x_mm']:5.1f} mm   {r['face_slope']:.3f} ({r['face_slope_p10_p90'][0]:.2f}-"
        f"{r['face_slope_p10_p90'][1]:.2f})   {r['ridge_ratio']:.3f}" for r in st]
    annotate(ph, blade_p, 2.0, s_ph, lab_ph, M["L_crease_px"], M["L_visible_px"])
    # ---------------- right: ours in the photo pose
    meta = json.loads((HERE / "ours_photo_pose_gallery.png.json").read_text())
    rgba = Image.open(HERE / "ours_photo_pose_gallery.png").convert("RGBA")
    bg = Image.new("RGBA", rgba.size, (92, 82, 70, 255))
    bg.alpha_composite(rgba)
    ours = bg.convert("RGB")
    blade_o = SP.blade_from_meta(meta, 1.0, visible_x=x_of_fvis(1.0))
    s_o = [blade_o.s_of_x(x_of_fvis(r["frac_from_shoulder"])) for r in st]
    lab_o = [("st  frac   x        face_slope  read back   ridge_ratio",)] + [
        f"{c['frac_vis']:.2f}   {c['x_mm']:5.1f} mm   {c['analytic_face_slope']:.3f}      {c['recovered_face_slope']:.3f}"
        f"        {c['analytic_ridge_ratio']:.3f}" for c in CHK]
    annotate(ours, blade_o, 1.0, s_o, lab_o, blade_o.s_of_x(35.0), blade_o.s_of_x(140.0))
    # ---------------- sheet
    sheet = Image.new("RGB", (2 * W + 20, H + HEAD + FOOT), (24, 24, 26))
    sheet.paste(ph, (0, HEAD))
    sheet.paste(ours, (W + 20, HEAD))
    d = ImageDraw.Draw(sheet)
    d.text((14, 16), "Reference photo (measurement only)  -  face_slope at stations (fraction of visible blade)",
           font=F_T, fill=(235, 235, 235))
    d.text((W + 34, 16), "Ours, SM_Kunai_Plain LOD0, same pose  -  analytic face_slope (read back)", font=F_T,
           fill=(235, 235, 235))
    fr = REC["summary"]
    lines = [
        f"face_slope = (ridge half-thickness - edge half-thickness) / half-width  (tan of the diamond face angle).  "
        f"Photo front blade {fr['front_face_slope']:.2f} (range {fr['front_range'][0]:.2f}-{fr['front_range'][1]:.2f}),"
        f" rear {fr['rear_face_slope']:.2f};  ours front 0.079-0.096, rear 0.11-0.15  ->  photo is ~{fr['photo_over_ours_front']:.1f}x steeper.",
        "Method: ring used as a round light probe, matcap forward-fitted through the pixel footprint; facet contrast "
        "inverted (albedo-free).  Validated on our render (round probe torus, same pose/world): reads 0.98-1.08x the "
        "known ratio.",
        "The measurers' kernel-smoothed matcap reads our render 2.1x too steep - the reason measurer A's 0.355 is high; "
        "B's 0.178 agrees with the validated value.",
        "Edges yellow, ridge cyan, crease green, stations magenta.  Photo: widest at 0.26 of the visible blade; its tip "
        "is buried (visible = 0.85 of shoulder->tip, our x 0-120 mm).  *ridge_ratio with our 1.5 mm edge (photo edge "
        "not resolvable).",
    ]
    y = HEAD + H + 12
    for i, t in enumerate(lines):
        d.text((14, y + i * 30), t, font=F_L if i == 0 else F_S, fill=(230, 230, 230) if i else (255, 230, 150))
    out = HERE / "side_by_side_photo_vs_ours.png"
    sheet.save(out)
    print("WROTE", out)


if __name__ == "__main__":
    main()
