"""pd_r2_explore_sheet.py -- one sheet of the round-2 jaw-ramus exploration (Pillow; no Unreal).
Rows: FaceC (control), MH_PlayerBase face (unmodified conform), the chosen fix L9N8, Epic preset Kelvin (explore2,
aligned to our face centre); columns: JawClose studio / ambient / headlight, 3/4 ambient crop.
usage: py Scripts/MetaHuman/pd_r2_explore_sheet.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_default")
X1, X2, X3 = OUT / "r2_explore_captures", OUT / "r2_explore2_captures", OUT / "r2_explore3_captures"
try:
    FONT = ImageFont.truetype("arial.ttf", 17)
except Exception:  # noqa: BLE001
    FONT = ImageFont.load_default()
ROWS = [("FaceC (control)", {"jc_s": X3 / "x3_C0_JawClose_studio.png", "jc_a": X3 / "x3_C0_JawClose_ambient.png",
                             "jc_h": X3 / "x3_C0_JawClose_headlight.png", "tq_a": X3 / "x3_C0_Face_ThreeQuarter_ambient.png"}),
        ("MH_PlayerBase face (conform)", {"jc_s": X1 / "x_R0_JawClose_studio.png", "jc_a": X1 / "x_R0_JawClose_ambient.png",
                                          "jc_h": None, "tq_a": X1 / "x_R0_Face_ThreeQuarter_ambient.png"}),
        ("FaceC + fix L9N8 (chosen)", {"jc_s": X3 / "x3_L9N8_JawClose_studio.png", "jc_a": X3 / "x3_L9N8_JawClose_ambient.png",
                                       "jc_h": X3 / "x3_L9N8_JawClose_headlight.png", "tq_a": X3 / "x3_L9N8_Face_ThreeQuarter_ambient.png"}),
        ("Epic preset Kelvin", {"jc_s": X2 / "k_Kelvin_JawClose_studio.png", "jc_a": X2 / "k_Kelvin_JawClose_ambient.png",
                                "jc_h": None, "tq_a": X2 / "k_Kelvin_Face_ThreeQuarter_ambient.png"})]
COLS = [("JawClose studio rig", "jc_s", (560, 150, 960, 650)), ("JawClose ambient rig", "jc_a", (560, 150, 960, 650)),
        ("JawClose headlight", "jc_h", (560, 150, 960, 650)), ("3/4 ambient rig", "tq_a", (500, 600, 900, 1100))]
S = 0.62
tw, th = int(400 * S), int(500 * S)
lab, left, top = 24, 250, 34
sheet = Image.new("RGB", (left + len(COLS) * tw, top + lab + len(ROWS) * th), (25, 25, 25))
d = ImageDraw.Draw(sheet)
d.text((6, 6), "Round-2 jaw-ramus line: same cameras + rigs; the line is darkest where the ramus turns away from the key light",
       fill=(255, 255, 255), font=FONT)
for c, (name, _, _) in enumerate(COLS):
    d.text((left + c * tw + 4, top + 3), name, fill=(255, 255, 160), font=FONT)
for r, (rname, files) in enumerate(ROWS):
    y = top + lab + r * th
    d.text((6, y + th // 2 - 10), rname, fill=(160, 255, 200), font=FONT)
    for c, (_, key, box) in enumerate(COLS):
        p = files.get(key)
        if p is None or not Path(p).exists():
            d.text((left + c * tw + 10, y + th // 2), "(not captured)", fill=(150, 150, 150), font=FONT)
            continue
        im = Image.open(p).convert("RGB").crop(box).resize((tw, th), Image.LANCZOS)
        sheet.paste(im, (left + c * tw, y))
out = OUT / "r2_jawfix_explore_sheet.png"
sheet.save(out)
print(out, sheet.size)
