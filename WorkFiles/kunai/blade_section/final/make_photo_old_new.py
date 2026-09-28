"""Side-by-side for the visual reviewer: the reference photo (measurement only - never used in any shipped asset) | the
3.10.1 kunai in the photo's pose | the 3.11 (option C) kunai in the same pose, with the face_slope at the photo's
stations (photo: reconciled; 3.10.1 and 3.11: measured on each LOD0 mesh).  Plain Python + Pillow.

  py -3 make_photo_old_new.py
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
BS = HERE.parent
PHOTO = Path("C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg")
OLD = BS / "ours" / "ours_photo_pose_gallery.png"
NEW = HERE / "photo_pose.png"
REC = json.loads((BS / "ours" / "photo_reconciled.json").read_text(encoding="utf-8"))
MEAS = json.loads((HERE / "face_slope_vs_photo.json").read_text(encoding="utf-8"))
W, H = 1000, 666
HEAD, FOOT = 60, 250


def font(size, bold=False):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "segoeui.ttf"):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + name, size)
        except OSError:
            continue
    return ImageFont.load_default()


F_T, F_L, F_S = font(24, True), font(18, True), font(16)


def on_bg(path):
    rgba = Image.open(path).convert("RGBA").resize((W, H), Image.LANCZOS)
    bg = Image.new("RGBA", rgba.size, (92, 82, 70, 255))
    bg.alpha_composite(rgba)
    return bg.convert("RGB")


panels = [(Image.open(PHOTO).convert("RGB").resize((W, H), Image.LANCZOS), "Reference photo (measurement only)"),
          (on_bg(OLD), "3.10.1 shipped: ridge 5.0 mm, edge 1.5 mm"),
          (on_bg(NEW), "3.11 option C: ridge 5 -> 7.0 mm, edge 0.3 mm")]
sheet = Image.new("RGB", (3 * W + 40, H + HEAD + FOOT), (24, 24, 26))
d = ImageDraw.Draw(sheet)
for i, (img, title) in enumerate(panels):
    x = i * (W + 20)
    sheet.paste(img, (x, HEAD))
    d.text((x + 14, 16), title, font=F_T, fill=(235, 235, 235))
rows = MEAS["stations"]
y = HEAD + H + 14
d.text((14, y), "face_slope = (ridge half-thickness - edge half-thickness) / half-width, at the photo's stations "
                "(our x, mm).  Photo: reconciled measurement; ours: true LOD0 mesh sections.", font=F_L,
       fill=(255, 230, 150))
y += 34
d.text((14, y), f"{'x mm':>8}{'photo':>10}{'3.10.1':>10}{'3.11':>10}{'3.11 / photo':>16}{'prototype C':>16}", font=F_S,
       fill=(235, 235, 235))
for k, r in enumerate(rows):
    d.text((14, y + 24 * (k + 1)),
           f"{r['x_mm']:>8.1f}{r['photo']:>10.3f}{r['v3_10_1']:>10.3f}{r['v3_11']:>10.3f}{r['v3_11_over_photo']:>16.2f}"
           f"{r['prototype_c']:>16.3f}", font=F_S, fill=(235, 235, 235))
fm = MEAS["front_median"]
d.text((1100, y + 24), f"front median (0.30-0.90): photo {fm['photo']:.3f} (range {REC['summary']['front_range'][0]:.2f}-"
                       f"{REC['summary']['front_range'][1]:.2f})", font=F_S, fill=(235, 235, 235))
d.text((1100, y + 48), f"3.10.1 {fm['v3_10_1']:.3f} ({fm['v3_10_1'] / fm['photo']:.2f}x)   3.11 {fm['v3_11']:.3f} "
                       f"({fm['v3_11'] / fm['photo']:.2f}x)   prototype C {fm['prototype_c']:.3f}", font=F_S,
       fill=(235, 235, 235))
d.text((1100, y + 84), "Same photo-pose rig for both renders (ours/render_photo_pose.py, gallery mode: the shipped",
       font=F_S, fill=(200, 200, 200))
d.text((1100, y + 106), "baked maps; roll +5 deg, axis 23.8 deg, 200 mm lens, the photo-like world).", font=F_S,
       fill=(200, 200, 200))
out = HERE / "side_by_side_photo_old_new.png"
sheet.save(out, optimize=True)
print("WROTE", out)
