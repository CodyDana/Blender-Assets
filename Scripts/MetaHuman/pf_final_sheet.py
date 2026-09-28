"""pf_final_sheet.py -- contact sheet of the fresh-reload verify captures of MH_PlayerFemale (plain Python + Pillow).

Writes WorkFiles/MetaHuman/player_female/female_sheet.png: face front / 3/4 both sides / profiles, full body
front/side/back, hair close-ups (all ambient rig), plus the male MH_PlayerDefault face front (ambient rig, taken in
round 2 at 70 cm; the female face cameras sit at 58 cm, so the male reads slightly smaller) for comparison.
usage: py Scripts/MetaHuman/pf_final_sheet.py [verify attempt, default 1]
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman")
CAP = ROOT / "player_female/verify_captures"
MALE = ROOT / "player_default/captures/after_Face_Front_ambient.png"
OUT = ROOT / "player_female/female_sheet.png"

FACE_CROP = (150, 120, 850, 1080)
ROWS = [
    ("Face (ambient rig)", [("Front", "pf_Face_Front.png", FACE_CROP), ("3/4 left", "pf_Face_TQ_L.png", FACE_CROP),
                            ("3/4 right", "pf_Face_TQ_R.png", FACE_CROP), ("Profile left", "pf_Face_Profile_L.png", FACE_CROP),
                            ("Profile right", "pf_Face_Profile_R.png", FACE_CROP)]),
    ("Body + comparison", [("Body front", "pf_Body_Front.png", (250, 60, 750, 1160)),
                           ("Body side", "pf_Body_Side.png", (250, 60, 750, 1160)),
                           ("Body back", "pf_Body_Back.png", (250, 60, 750, 1160)),
                           ("Close-up", "pf_Face_Close.png", (100, 100, 900, 1100)),
                           ("MH_PlayerDefault (male, 70 cm cam)", str(MALE), FACE_CROP)]),
    ("Hair", [("Back 3/4 left", "pf_Hair_Back34_L.png", FACE_CROP), ("Back 3/4 right", "pf_Hair_Back34_R.png", FACE_CROP),
              ("Back", "pf_Hair_Back.png", FACE_CROP), ("Side", "pf_Hair_Side_L.png", FACE_CROP),
              ("Top", "pf_Hair_Top.png", FACE_CROP)]),
]
TW, TH = 420, 576


def tile(path, crop):
    p = Path(path) if Path(path).is_absolute() else CAP / path
    if not p.exists():
        im = Image.new("RGB", (TW, TH), (70, 20, 20))
        ImageDraw.Draw(im).text((10, 10), "missing " + p.name, fill=(255, 255, 255))
        return im
    im = Image.open(p).convert("RGB").crop(crop)
    im.thumbnail((TW, TH), Image.LANCZOS)
    bg = Image.new("RGB", (TW, TH), (46, 46, 46))
    bg.paste(im, ((TW - im.width) // 2, (TH - im.height) // 2))
    return bg


def main():
    global CAP
    if len(sys.argv) > 1:
        CAP = ROOT / f"player_female/verify_captures"
    cols = max(len(r[1]) for r in ROWS)
    head, lab = 34, 22
    H = head + len(ROWS) * (lab + TH + 8)
    S = Image.new("RGB", (cols * TW, H), (24, 24, 24))
    d = ImageDraw.Draw(S)
    d.text((10, 10), "MH_PlayerFemale -- fresh-reload verify captures (UE 5.8.3, ambient grey-studio rig; not rigged)",
           fill=(240, 240, 240))
    y = head
    for title, items in ROWS:
        for i, (label, f, crop) in enumerate(items):
            d.text((i * TW + 6, y + 4), f"{title}: {label}" if i == 0 else label, fill=(255, 230, 120))
            S.paste(tile(f, crop), (i * TW, y + lab))
        y += lab + TH + 8
    S.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
