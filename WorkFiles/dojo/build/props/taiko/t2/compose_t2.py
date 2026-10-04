"""t2: compare_tacks.png: the user's photo vs ours (photo-studio light), plus tack-band crops (the photo; ours under
the photo-studio light and under the t1 review studio). System Python + Pillow."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
HERE = Path(__file__).resolve().parent
try:
    F = ImageFont.truetype("arial.ttf", 22)
except OSError:
    F = ImageFont.load_default()
ref = Image.open(ROOT / "References" / "Dojo" / "taiko_tacks_ref_user.webp").convert("RGB")


def flat(p):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    return Image.alpha_composite(bg, im).convert("RGB")


ours = flat(HERE / "drum_front_standing_photo.png")
band_p = flat(HERE / "closeup_tack_band_photo.png")
band_s = flat(HERE / "closeup_tack_band.png")
W = 2000
im = Image.new("RGB", (W, 1960), "white")
d = ImageDraw.Draw(im)
top = 40
im.paste(ref.resize((760, 760), Image.LANCZOS), (10, top))
im.paste(ours.resize((760, 760), Image.LANCZOS), (800, top))
d.text((10, 8), "REFERENCE (user photo)", fill="black", font=F)
d.text((800, 8), "OURS t2: drum standing on a head, camera 15 deg above (photo-studio light)", fill="black", font=F)
y = top + 780
rc = ref.crop((300, 150, 700, 330)).resize((990, 446), Image.LANCZOS)
im.paste(rc, (10, y + 30))
d.text((10, y), "reference tack band (crop)", fill="black", font=F)
bp = band_p.crop((0, 120, 1200, 660)).resize((990, 446), Image.LANCZOS)
im.paste(bp, (1005, y + 30))
d.text((1005, y), "ours t2: tack band close-up (photo-studio light)", fill="black", font=F)
y2 = y + 500
bs = band_s.crop((0, 120, 1200, 660)).resize((990, 446), Image.LANCZOS)
im.paste(bs, (1005, y2 + 30))
d.text((1005, y2), "ours t2: same close-up, t1 review studio light", fill="black", font=F)
t1 = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko" / "t1" / "closeup_tack_band.png"
b1 = flat(t1).crop((0, 120, 1200, 660)).resize((990, 446), Image.LANCZOS)
im.paste(b1, (10, y2 + 30))
d.text((10, y2), "before (t1): 12-sided satin iron domes, same view", fill="black", font=F)
im = im.crop((0, 0, W, y2 + 30 + 446 + 10))
im.save(HERE / "compare_tacks.png")
print("saved", HERE / "compare_tacks.png", im.size)
