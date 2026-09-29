"""entryfix side-by-sides (PIL): reference | ours, crop | ours' foreground strip, plus lantern / bar measurements."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
HERE = Path(__file__).resolve().parent
REF = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference")
tag = sys.argv[1]                      # render folder under renders/, e.g. b1
out = HERE / "compare"
out.mkdir(exist_ok=True)
ref = Image.open(REF / "armory3_reference2.png").convert("RGB")
crop = Image.open(REF / "entry_foreground_crop.png").convert("RGB")


def pair(a, b, path, la, lb, h=None):
    h = h or min(a.height, b.height)
    a = a.resize((round(a.width * h / a.height), h))
    b = b.resize((round(b.width * h / b.height), h))
    im = Image.new("RGB", (a.width + b.width + 16, h + 28), (20, 20, 20))
    im.paste(a, (0, 28)); im.paste(b, (a.width + 16, 28))
    d = ImageDraw.Draw(im)
    d.text((6, 6), la, fill=(230, 230, 230)); d.text((a.width + 22, 6), lb, fill=(230, 230, 230))
    im.save(path)
    print("wrote", path)


R = HERE / "renders" / tag
for name, extra in (("ref_aspect/C1_EntryReveal_night.png", ""), ("ref_aspect/C1_Old_night.png", "_oldcam")):
    p = R / name
    if not p.exists():
        continue
    ours = Image.open(p).convert("RGB")
    pair(ref, ours, out / f"C1_ref_vs_{tag}{extra}.png", "reference 2", f"ours {tag}{extra} night 1448x1086")
    strip = ours.crop((0, 830, 1448, 1086))
    pair(crop, strip, out / f"C1_crop_vs_{tag}{extra}.png", "user crop", f"ours {tag}{extra} (y 830-1086)", h=256)
    rstrip = ref.crop((0, 830, 1448, 1086))
    im = Image.new("RGB", (1448, 256 * 2 + 12), (20, 20, 20))
    im.paste(rstrip, (0, 0)); im.paste(strip, (0, 268))
    im.save(out / f"C1_foreground_ref_over_{tag}{extra}.png")
p = R / "C1_EntryReveal_night.png"
if p.exists():
    pair(ref, Image.open(p).convert("RGB"), out / f"C1_ref_vs_{tag}_1600x900.png", "reference 2", f"ours {tag} 1600x900")
