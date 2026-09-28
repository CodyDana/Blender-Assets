"""pf_beauty_sheet.py -- BEFORE (v1) vs AFTER (v2 beauty pass) sheet for MH_PlayerFemale (plain Python + Pillow).

BEFORE = v1_verify_captures (fresh-reload verify of v1), AFTER = verify_captures (fresh-reload verify of v2); same
ambient rig and camera definitions (face cameras aimed at each version's own landmark centre, body cameras at half
height). Writes WorkFiles/MetaHuman/player_female/beauty_before_after.png.
usage: py Scripts/MetaHuman/pf_beauty_sheet.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_female")
BEFORE, AFTER = ROOT / "v1_verify_captures", ROOT / "verify_captures"
OUT = ROOT / "beauty_before_after.png"
FACE = (150, 120, 850, 1080)
BODY = (250, 60, 750, 1160)
COLS = [("Face front", "pf_Face_Front.png", FACE), ("Face 3/4", "pf_Face_TQ_L.png", FACE),
        ("Profile", "pf_Face_Profile_L.png", FACE), ("Close-up", "pf_Face_Close.png", (100, 100, 900, 1100)),
        ("Body front", "pf_Body_Front.png", BODY), ("Body side", "pf_Body_Side.png", BODY)]
TW, TH = 360, 494


def tile(p, crop):
    if not p.exists():
        im = Image.new("RGB", (TW, TH), (70, 20, 20))
        ImageDraw.Draw(im).text((8, 8), "missing " + p.name, fill=(255, 255, 255))
        return im
    im = Image.open(p).convert("RGB").crop(crop)
    im.thumbnail((TW, TH), Image.LANCZOS)
    bg = Image.new("RGB", (TW, TH), (46, 46, 46))
    bg.paste(im, ((TW - im.width) // 2, (TH - im.height) // 2))
    return bg


def main():
    head, lab = 34, 22
    S = Image.new("RGB", (len(COLS) * TW, head + 2 * (lab + TH + 6)), (24, 24, 24))
    d = ImageDraw.Draw(S)
    d.text((10, 10), "MH_PlayerFemale  BEFORE (v1, top)  vs  AFTER (v2 beauty pass, bottom) -- fresh-reload verify, "
                     "ambient rig, not rigged", fill=(240, 240, 240))
    for r, (tag, folder) in enumerate((("BEFORE v1", BEFORE), ("AFTER v2", AFTER))):
        y = head + r * (lab + TH + 6)
        for i, (label, f, crop) in enumerate(COLS):
            d.text((i * TW + 6, y + 4), f"{tag}: {label}" if i == 0 else label, fill=(255, 230, 120))
            S.paste(tile(folder / f, crop), (i * TW, y + lab))
    S.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
