"""Round 8 s2: REF2_vs_OURS.png (reference | our matched camera) and BEFORE_AFTER_vs_R7T1_STATE.png (the saved round-6 f1
level = the 't1 state', captured -game in s1 | round 8 s1 | round 8 s2), all labelled."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
R8 = Path(__file__).resolve().parent.parent
REF = Path(r"C:/Users/Cody/Desktop/Blender_Projects/References/Dojo/dojo1_reference2.png")
try:
    F = ImageFont.truetype("arial.ttf", 30); FS = ImageFont.truetype("arial.ttf", 22)
except OSError:
    F = FS = ImageFont.load_default()
def lab(im, t, f=F):
    d = ImageDraw.Draw(im); d.rectangle((0, 0, im.width, 44), fill=(0, 0, 0)); d.text((10, 7), t, fill=(255, 255, 255), font=f); return im
H = 1086
a = Image.open(REF).convert("RGB"); a = a.resize((round(a.width * H / a.height), H))
b = Image.open(R8 / "s2" / "CAM_Ref2Match.png").convert("RGB"); b = b.resize((round(b.width * H / b.height), H))
s = Image.new("RGB", (a.width + b.width + 12, H + 44), (30, 30, 30))
s.paste(lab(Image.new("RGB", (a.width, 44)), "dojo1_reference2 (reference)"), (0, 0)); s.paste(a, (0, 44))
s.paste(lab(Image.new("RGB", (b.width, 44)), "OURS round 8 s2: CAM_Ref2Match, -game HighResShot, UDS"), (a.width + 12, 0)); s.paste(b, (a.width + 12, 44))
s.save(R8 / "s2" / "REF2_vs_OURS.png")
cams = ["CAM_Ref2Match", "CAM_Establishing", "CAM_PlayerEyeSand", "CAM_Overview", "CAM_GateFromStreet", "CAM_HallVeranda",
        "CU_HallUpperRoof", "CU_R5_Skyline", "CAM_EastYard", "CAM_Drum", "CU_R4_StorehouseFront", "CAM_EstablishingRef2"]
cols = [("BEFORE: saved round-6 f1 level (the 't1 state'), -game", R8 / "s1" / "before_game"),
        ("round 8 s1 (UDS, sun 5.2 deg behind-left)", R8 / "s1"), ("round 8 s2 (UDS retune, sun 9.1 deg from the west)", R8 / "s2")]
tw, th = 640, 400
sheet = Image.new("RGB", (220 + tw * 3, 50 + th * len(cams)), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for j, (t, _) in enumerate(cols):
    d.text((230 + j * tw, 12), t, fill=(255, 255, 255), font=FS)
for i, c in enumerate(cams):
    d.text((8, 50 + i * th + th // 2 - 12), c, fill=(255, 255, 255), font=FS)
    for j, (_, p) in enumerate(cols):
        f = p / f"{c}.png"
        if f.exists():
            t = Image.open(f).convert("RGB"); t.thumbnail((tw - 8, th - 8)); sheet.paste(t, (220 + j * tw, 50 + i * th))
sheet.save(R8 / "s2" / "BEFORE_AFTER_vs_R7T1_STATE.png")
print("ok")
