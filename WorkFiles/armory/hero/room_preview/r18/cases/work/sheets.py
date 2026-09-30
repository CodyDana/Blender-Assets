"""r18 cases: comparison sheets (PIL). reference | night_r17 | r18 for C1; r17 | r18 for C4 / C5 / CW; and a box overlay."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
P = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory")
D = P / "hero/room_preview/r18/cases"; OUT = D / "compare"; OUT.mkdir(exist_ok=True)
REF = P / "reference/armory3_reference2.png"
N17 = P / "build/renders/night_r17"; F17 = P / "hero/room_preview/r17/final"
try:
    FONT = ImageFont.truetype("arial.ttf", 30)
except OSError:
    FONT = ImageFont.load_default()

def sheet(items, out, h=None):
    ims = [Image.open(p).convert("RGB") for p, _ in items]
    h = h or min(i.height for i in ims)
    ims = [i.resize((round(i.width * h / i.height), h)) for i in ims]
    W = sum(i.width for i in ims) + 24 * (len(ims) - 1)
    s = Image.new("RGB", (W, h + 48), (255, 255, 255)); d = ImageDraw.Draw(s); x = 0
    for im, (_, lab) in zip(ims, items):
        s.paste(im, (x, 48)); d.text((x + 8, 8), lab, fill=(0, 0, 0), font=FONT); x += im.width + 24
    s.save(out); print("saved", out, s.size)

sheet([(REF, "reference 2"), (N17 / "ref_aspect/C1_EntryReveal_night.png", "night_r17 (live)"),
       (D / "ref_aspect/C1_EntryReveal_night.png", "r18 cases (night)")], OUT / "C1_ref_vs_night_r17_vs_r18cases_night.png")
sheet([(REF, "reference 2"), (F17 / "ref_aspect/C1_EntryReveal_golden.png", "r17 final (golden)"),
       (D / "ref_aspect/C1_EntryReveal_golden.png", "r18 cases (golden)")], OUT / "C1_ref_vs_r17_vs_r18cases_golden.png")
for cam in ("C4_ShurikenTray", "C5_CloakCase", "CW_WestAisle"):
    sheet([(N17 / f"{cam}_night.png", "night_r17 (live)"), (D / f"{cam}_night.png", "r18 cases (night)")],
          OUT / f"{cam}_night_r17_vs_r18cases_night.png")
    sheet([(F17 / f"{cam}_golden.png", "r17 final (golden)"), (D / f"{cam}_golden.png", "r18 cases (golden)")],
          OUT / f"{cam}_r17_vs_r18cases_golden.png")

# box overlay: reference 2 with its measured side-case boxes | r18 night with the mesh-projected boxes
REFB = {"kunai": [28, 195, 545, 855], "cloak": [130, 312, 325, 700], "scrolls": [258, 407, 400, 590],
        "tall W": [287, 450, 255, 470], "shuriken": [1260, 1408, 625, 855], "boots": [1180, 1410, 470, 715],
        "hat": [1078, 1210, 345, 575], "tall E": [1000, 1130, 255, 470]}
cb = json.loads((D / "c1_boxes.json").read_text())
COL = [(255, 60, 60), (60, 220, 60), (60, 160, 255), (255, 220, 0)]
def overlay(src, boxes, keep=None):
    im = Image.open(src).convert("RGB"); d = ImageDraw.Draw(im)
    for n, (lab, b) in enumerate(boxes.items()):
        c = COL[n % 4]; d.rectangle([b[0], b[2], b[1], b[3]], outline=c, width=3); d.text((b[0] + 4, b[2] + 4), lab, fill=c, font=FONT)
    for lab, b in (keep or {}).items():
        d.rectangle([b[0], b[2], b[1], b[3]], outline=(255, 0, 255), width=2)
    return im
KEEP = {"niche lit W": [365, 413, 165, 232], "niche lit E": [1035, 1083, 165, 232],
        "foot lantern W": cb["keep_clear_mesh_boxes"]["foot_lantern_W"], "foot lantern E": cb["keep_clear_mesh_boxes"]["foot_lantern_E"]}
order = ["5", "4", "G3", "G1", "8", "6", "G2", "7"]
a = overlay(REF, REFB)
b = overlay(D / "ref_aspect/C1_EntryReveal_night.png", {k: cb["cases"][k]["box"] for k in order}, KEEP)
s = Image.new("RGB", (a.width * 2 + 24, a.height + 48), (255, 255, 255)); dd = ImageDraw.Draw(s)
s.paste(a, (0, 48)); s.paste(b, (a.width + 24, 48))
dd.text((8, 8), "reference 2: side-case boxes (measured by eye, +-5 px)", fill=(0, 0, 0), font=FONT)
dd.text((a.width + 32, 8), "r18 cases night: plinth+glass boxes projected from the built meshes; magenta = keep-clear", fill=(0, 0, 0), font=FONT)
s.save(OUT / "C1_boxes_ref_vs_r18cases.png"); print("saved boxes overlay")
