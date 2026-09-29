"""matfix side-by-sides (PIL): crop | ours (C1 bottom strip, golden and night), reference 2 | ours C1, the mat zoomed
(reference over ours), and the entry views. Usage: compare.py <tag>"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
HERE = Path(__file__).resolve().parent
REF = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference")
tag = sys.argv[1]
out = HERE / "compare"
out.mkdir(exist_ok=True)
ref = Image.open(REF / "armory3_reference2.png").convert("RGB")
crop = Image.open(REF / "entry_foreground_crop.png").convert("RGB")
R = HERE / "renders" / tag


def pair(a, b, path, la, lb, h=None, vertical=False):
    if vertical:
        w = min(a.width, b.width)
        a = a.resize((w, round(a.height * w / a.width))); b = b.resize((w, round(b.height * w / b.width)))
        im = Image.new("RGB", (w, a.height + b.height + 56), (20, 20, 20))
        im.paste(a, (0, 28)); im.paste(b, (0, a.height + 56))
        d = ImageDraw.Draw(im); d.text((6, 6), la, fill=(230, 230, 230)); d.text((6, a.height + 34), lb, fill=(230, 230, 230))
    else:
        h = h or min(a.height, b.height)
        a = a.resize((round(a.width * h / a.height), h)); b = b.resize((round(b.width * h / b.height), h))
        im = Image.new("RGB", (a.width + b.width + 16, h + 28), (20, 20, 20))
        im.paste(a, (0, 28)); im.paste(b, (a.width + 16, 28))
        d = ImageDraw.Draw(im); d.text((6, 6), la, fill=(230, 230, 230)); d.text((a.width + 22, 6), lb, fill=(230, 230, 230))
    im.save(path)
    print("wrote", path.name)


for P in ("golden", "night"):
    p = R / f"C1_EntryReveal_{P}.png"
    if not p.exists():
        continue
    ours = Image.open(p).convert("RGB")
    pair(ref, ours, out / f"C1_ref_vs_{tag}_{P}.png", "reference 2", f"ours {tag} {P} 1448x1086")
    # the crop is reference 2's bottom strip (463 x 82 of 1448 wide = y ~830-1086)
    strip = ours.crop((0, 830, 1448, 1086))
    pair(crop, strip, out / f"C1_crop_vs_{tag}_{P}.png", "user crop (entry_foreground_crop.png)", f"ours {tag} {P} (y 830-1086)",
         vertical=True)
    box = (380, 900, 1080, 1086)
    pair(ref.crop(box).resize((1400, 372), Image.LANCZOS), ours.crop(box).resize((1400, 372), Image.LANCZOS),
         out / f"C1_mat_zoom_{tag}_{P}.png", "reference 2 mat x2", f"ours {tag} {P} mat x2", vertical=True)
for cam in ("CE_EntryDown", "CE_MatTop", "CE_BarFromMat"):
    ims = [Image.open(R / f"{cam}_{P}.png").convert("RGB") for P in ("golden", "night") if (R / f"{cam}_{P}.png").exists()]
    if len(ims) == 2:
        pair(ims[0], ims[1], out / f"{cam}_{tag}_golden_night.png", f"{cam} {tag} golden", f"{cam} {tag} night", h=600)
