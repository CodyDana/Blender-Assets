"""Compose the per-prop model sheets (front | side | top | 3/4) from render_modern.py --mode views, on a plain
light-grey background with view labels (review sheets only; labels never go into an asset), and write the reference
crops used by the side-by-side sheets.

Run with the system Python (Pillow): py Scripts/dojo/props/modern/compose_sheets.py [round]
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
RND = sys.argv[1] if len(sys.argv) > 1 else "r0"
BASE = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "modern"
OUT = BASE / "renders" / RND
VIEWS = OUT / "_views"
REF = ROOT / "References" / "Dojo" / "dojo_modern_props_ref.png"
BG = (200, 201, 202)
# panel 11 crops (pixel boxes on the 1536 x 1024 board) per prop
CROPS = {
    "VendingMachine": (1210, 735, 1352, 865), "ACUnit_Roof": (1352, 735, 1452, 865),
    "ACUnit_Wall": (1352, 735, 1452, 865), "WallLamp": (1452, 735, 1536, 865),
    "UtilityPole": (1210, 862, 1332, 1020), "Wire_Span25": (1210, 862, 1332, 1020),
    "Wire_Drop12": (1210, 862, 1332, 1020), "StreetLamp_A": (1330, 862, 1412, 1020),
    "StreetLamp_B": (1400, 862, 1462, 1020), "JunctionBox": (1455, 862, 1536, 1020),
    "PoleTransformer": (1210, 862, 1332, 1020), "PoleGuy": (1210, 862, 1332, 1020),
    "Wire_Telecom25": (1210, 862, 1332, 1020),
}


def font(sz):
    for f in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def over_bg(im):
    bg = Image.new("RGBA", im.size, BG + (255,))
    bg.alpha_composite(im.convert("RGBA"))
    return bg.convert("RGB")


def main():
    meta = {}
    for f in sorted(VIEWS.glob("views_meta*.json")):
        meta.update(json.loads(f.read_text()))
    ref = Image.open(REF).convert("RGB")
    (BASE / "refcrops").mkdir(exist_ok=True)
    made = []
    for name, m in meta.items():
        short = name.replace("SM_DKP_Modern_", "")
        ims = {v: over_bg(Image.open(VIEWS / f"{name}_{v}.png")) for v in ("front", "side", "top", "34")}
        hmax = max(ims[v].height for v in ("front", "side", "top"))
        hmax = max(hmax, 700)
        s = hmax / ims["34"].height
        ims["34"] = ims["34"].resize((int(ims["34"].width * s), hmax), Image.LANCZOS)
        pad, top, lab = 30, 84, 50
        W = sum(ims[v].width for v in ims) + pad * 5
        H = top + hmax + lab
        sheet = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(sheet)
        d.text((pad, 18), f"{name}   (review sheet {RND}; grey figure = 1.8 m; ortho views share one scale, "
                          f"{m['px_per_m']:.0f} px/m)", fill=(40, 40, 40), font=font(26))
        if m.get("note"):
            d.text((pad, 46), f"NOTE: {m['note']}", fill=(150, 30, 30), font=font(22))
        x = pad
        for v, label in (("front", "Front"), ("side", "Side (right)"), ("top", "Top"), ("34", "3/4 perspective")):
            im = ims[v]
            y = top + (hmax - im.height if v != "top" else 0)
            sheet.paste(im, (x, y))
            d.text((x + 6, top + hmax + 8), label, fill=(40, 40, 40), font=font(24))
            x += im.width + pad
        path = OUT / f"sheet_{short}.png"
        sheet.save(path)
        made.append(str(path))
        crop = ref.crop(CROPS[short])
        k = max(1, int(round(H / crop.height)))
        crop = crop.resize((crop.width * k, crop.height * k), Image.LANCZOS)
        crop.save(BASE / "refcrops" / f"ref_{short}.png")
    print("\n".join(made))


if __name__ == "__main__":
    main()
