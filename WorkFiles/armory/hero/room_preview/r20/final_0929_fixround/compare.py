"""r20 final side-by-sides (PIL): reference 2 | ours (golden C1 1448x1086, also night), the user's entry crop over
ours (C1 bottom strip y 830-1086, golden and night). Usage: compare.py"""
from pathlib import Path
from PIL import Image, ImageDraw
HERE = Path(__file__).resolve().parent
REF = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference")
out = HERE / "compare"
out.mkdir(exist_ok=True)
ref = Image.open(REF / "armory3_reference2.png").convert("RGB")
crop = Image.open(REF / "entry_foreground_crop.png").convert("RGB")


def pair(a, b, path, la, lb, vertical=False):
    if vertical:
        w = max(a.width, b.width)
        a = a.resize((w, round(a.height * w / a.width)), Image.LANCZOS)
        b = b.resize((w, round(b.height * w / b.width)), Image.LANCZOS)
        im = Image.new("RGB", (w, a.height + b.height + 56), (20, 20, 20))
        im.paste(a, (0, 28)); im.paste(b, (0, a.height + 56))
        d = ImageDraw.Draw(im); d.text((6, 6), la, fill=(230, 230, 230)); d.text((6, a.height + 34), lb, fill=(230, 230, 230))
    else:
        h = min(a.height, b.height)
        a = a.resize((round(a.width * h / a.height), h)); b = b.resize((round(b.width * h / b.height), h))
        im = Image.new("RGB", (a.width + b.width + 16, h + 28), (20, 20, 20))
        im.paste(a, (0, 28)); im.paste(b, (a.width + 16, 28))
        d = ImageDraw.Draw(im); d.text((6, 6), la, fill=(230, 230, 230)); d.text((a.width + 22, 6), lb, fill=(230, 230, 230))
    im.save(path)
    print("wrote", path.name, im.size)


for P in ("golden", "night"):
    p = HERE / P / "ref_aspect" / f"C1_EntryReveal_{P}.png"
    if not p.exists():
        cands = list((HERE / P / "ref_aspect").glob("C1_EntryReveal*.png"))
        p = cands[0] if cands else p
    ours = Image.open(p).convert("RGB")
    pair(ref, ours, out / f"C1_ref_vs_r20_{P}.png", "reference 2", f"ours r20 {P} C1 1448x1086")
    # the crop is reference 2's bottom strip (463 x 82 of 1448 wide = y ~830-1086)
    pair(crop, ours.crop((0, 830, 1448, 1086)), out / f"entry_crop_vs_r20_{P}.png",
         "user crop (entry_foreground_crop.png)", f"ours r20 {P} C1 (y 830-1086)", vertical=True)

# r20 fix round (2026-09-29): the judged 7/10 set (prev_7of10/) against the fixed set, per view and preset, and the
# reference's rear zoom (x 380-1070, y 180-420) / mat zoom (x 350-850, y 900-1040) against both C1s
PREV = HERE / "prev_7of10"
for P in ("golden", "night"):
    for cam in ("C3_Case3", "C10_Hero", "CW_WestAisle", "CX_FromPlatform", "CE_EntryDown", "CG_Garden"):
        a, b = PREV / P / f"{cam}_{P}.png", HERE / P / f"{cam}_{P}.png"
        if a.exists() and b.exists():
            pair(Image.open(a).convert("RGB"), Image.open(b).convert("RGB"), out / f"{cam}_7of10_vs_fix_{P}.png",
                 f"judged 7/10 {cam} {P}", f"fix round {cam} {P}")
    a = Image.open(PREV / P / "ref_aspect" / f"C1_EntryReveal_{P}.png").convert("RGB")
    b = Image.open(HERE / P / "ref_aspect" / f"C1_EntryReveal_{P}.png").convert("RGB")
    pair(a, b, out / f"C1_7of10_vs_fix_{P}.png", f"judged 7/10 C1 {P}", f"fix round C1 {P}")
    for tag, box in (("rear", (380, 180, 1070, 420)), ("mat", (350, 900, 850, 1040))):
        cr = [im.crop(box) for im in (ref, a, b)]
        w, h = cr[0].size
        sheet = Image.new("RGB", (w * 2, (h * 2 + 28) * 3), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, (im, lab) in enumerate(zip(cr, ("reference 2", f"judged 7/10 ({P})", f"fix round ({P})"))):
            sheet.paste(im.resize((w * 2, h * 2), Image.LANCZOS), (0, i * (h * 2 + 28) + 28))
            d.text((6, i * (h * 2 + 28) + 8), lab, fill=(230, 230, 230))
        sheet.save(out / f"C1_{tag}_zoom_ref_7of10_fix_{P}.png")
        print("wrote", f"C1_{tag}_zoom_ref_7of10_fix_{P}.png", sheet.size)
