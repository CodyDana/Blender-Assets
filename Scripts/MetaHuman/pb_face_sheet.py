"""pb_face_sheet.py -- side-by-side sheet of the face candidates (py -3, needs Pillow).

    py -3 Scripts/MetaHuman/pb_face_sheet.py <build_report.json> [out.png]

Columns: IP reference (References/JinMuWon/user_confirmed_reference.png, crops of the sheet) | unmodified conformed
face (ref_* captures, same cameras) | one column per candidate. Rows: face front, face 3/4, face profile, body front.
All renders are real SceneCapture exports from pb_face_design.py (builder cameras, studio light rig).
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
FACES = ROOT / "WorkFiles/MetaHuman/player_base/faces"
CAP = FACES / "captures"
REF = ROOT / "References/JinMuWon/user_confirmed_reference.png"

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else FACES / "face_candidates_sheet.png"
build = report["build"]
cands = list(build["candidates"])

TW, TH = 420, 504          # tile size (5:6 like the 1000x1200 captures)
HEAD = 190                 # column header height
ROWS = [("Face_Front", "face front"), ("Face_ThreeQuarter", "face 3/4"), ("Face_Profile", "face profile"),
        ("Body_Front", "body front")]
LABEL_W = 0
font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 22)
fontb = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
fonts = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 17)


def crop_capture(path: Path, kind: str) -> Image.Image:
    im = Image.open(path).convert("RGB")
    if kind.startswith("Face"):
        im = im.crop((150, 170, 850, 1010))        # head + neck, keeps the 5:6 aspect
    return im.resize((TW, TH), Image.LANCZOS)


def ref_tiles() -> list:
    ref = Image.open(REF).convert("RGB")
    w, h = ref.size
    sx, sy = w / 1225.0, h / 1284.0
    def c(box):
        b = (int(box[0] * sx), int(box[1] * sy), int(box[2] * sx), int(box[3] * sy))
        tile = ref.crop(b)
        tile.thumbnail((TW, TH), Image.LANCZOS)
        bg = Image.new("RGB", (TW, TH), (40, 40, 40))
        bg.paste(tile, ((TW - tile.width) // 2, (TH - tile.height) // 2))
        return bg
    return [c((860, 150, 1225, 590)),          # close-up face
            c((780, 0, 1225, 990)),            # close-up panel (3/4-ish portrait)
            c((140, 0, 330, 230)),             # front figure head
            c((20, 0, 420, 990))]              # front figure


cols = [("IP REFERENCE (third-party)", "user_confirmed_reference.png", None),
        ("CONFORMED, UNMODIFIED", "MH_PlayerBase face (scratch copy)", "ref_")]
def pct(d):
    return int(round(sum(d.values()) * 100))


for name in cands:
    c = build["candidates"][name]
    rc = c["recipe"]
    regs = rc.get("regions", {})
    presets = sorted({p for p in rc.get("blend", {})} | {p for g in regs.values() for p in g})
    mean = int(round(c.get("share", {}).get("mean", 0) * 100))
    sub = (f"presets {' + '.join(presets)}; mean preset share {mean}% (ours {100 - mean}%): "
           f"eyes {pct(regs.get('eyes', rc['blend']))}%, nose {pct(regs.get('nose', rc['blend']))}%, "
           f"mouth {pct(regs.get('mouth', rc['blend']))}%, jaw {pct(regs.get('jaw', rc['blend']))}%, "
           f"skull {pct(rc['blend'])}%" + ("; + eyelid landmark moves" if rc.get("landmark_moves") else ""))
    cols.append((name.replace("MH_PlayerBase_", ""), sub, name.replace("MH_PlayerBase_", "") + "_"))

W = TW * len(cols)
H = HEAD + TH * len(ROWS) + 40
sheet = Image.new("RGB", (W, H), (28, 28, 28))
d = ImageDraw.Draw(sheet)
rtiles = ref_tiles()
for ci, (title, sub, prefix) in enumerate(cols):
    x = ci * TW
    d.text((x + 10, 10), title, font=fontb, fill=(255, 255, 255) if ci else (255, 170, 120))
    # wrap subtitle
    words, line, y = sub.split(" "), "", 50
    for w_ in words:
        test = (line + " " + w_).strip()
        if d.textlength(test, font=fonts) > TW - 20:
            d.text((x + 10, y), line, font=fonts, fill=(200, 200, 200))
            y += 22
            line = w_
        else:
            line = test
    d.text((x + 10, y), line, font=fonts, fill=(200, 200, 200))
    for ri, (kind, _label) in enumerate(ROWS):
        y0 = HEAD + ri * TH
        if prefix is None:
            tile = rtiles[ri]
        else:
            p = CAP / f"{prefix}{kind}.png"
            tile = crop_capture(p, kind) if p.is_file() else Image.new("RGB", (TW, TH), (60, 0, 0))
        sheet.paste(tile, (x, y0))
    d.line([(x, HEAD), (x, H)], fill=(10, 10, 10), width=3)
for ri, (_k, label) in enumerate(ROWS):
    d.text((TW + 8, HEAD + ri * TH + 6), label, font=font, fill=(255, 255, 0))
d.text((10, H - 32), "UE 5.8.3 SceneCapture renders, builder cameras (face 70 cm / body 380 cm, fov 30), studio rig; "
       "no grooms (hair/brows/lashes off on all MetaHumans). Reference column = third-party IP, for comparison only.",
       font=fonts, fill=(180, 180, 180))
out_path.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out_path)
print(out_path, sheet.size)

