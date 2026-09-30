"""Round-2 review sheets: BEFORE_AFTER_SHEET.png (every showcase camera, round-1 capture | round-2 capture) and
SBS_COLOUR.png (Blender render | round 1 | round 2 for the gate view; reference 2 | Blender ground | round 2 for the
establishing view). Labels are plain text on a strip (review images, not deliverables)."""
from pathlib import Path

from PIL import Image, ImageDraw

R = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\unreal\round2_polish")
B = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build")
REF = Path(r"C:\Users\Cody\Desktop\Blender_Projects\References\Dojo\dojo1_reference2.png")
CAMS = ["CAM_GateFromCourtyard", "CAM_Establishing", "CAM_PlayerEyeSand", "CAM_Drum", "CAM_EastYard",
        "CAM_VendingShed", "CAM_GateFromStreet", "CAM_WallTop", "CAM_WallCorner", "CAM_Overview"]
W, H, S = 640, 360, 22


def fit(p, w, h):
    im = Image.open(p).convert("RGB")
    im.thumbnail((w, h))
    c = Image.new("RGB", (w, h), (20, 20, 20))
    c.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return c


def strip(text, w):
    s = Image.new("RGB", (w, S), (235, 235, 235))
    ImageDraw.Draw(s).text((6, 5), text, fill=(0, 0, 0))
    return s


sheet = Image.new("RGB", (2 * W, len(CAMS) * (H + S)), (255, 255, 255))
for i, cam in enumerate(CAMS):
    y = i * (H + S)
    sheet.paste(strip(f"{cam}  round 1 (before)", W), (0, y))
    sheet.paste(strip(f"{cam}  round 2 (after)", W), (W, y))
    sheet.paste(fit(R / "before" / "captures" / f"{cam}.png", W, H), (0, y + S))
    sheet.paste(fit(R / "captures_after" / f"{cam}.png", W, H), (W, y + S))
sheet.save(R / "BEFORE_AFTER_SHEET.png")

rows = [[("Blender render (kit1_f2 beauty)", B / "renders/kit1_f2/beauty_gate_from_courtyard.png"),
         ("Unreal round 1", R / "before/captures/CAM_GateFromCourtyard.png"),
         ("Unreal round 2", R / "captures_after/CAM_GateFromCourtyard.png")],
        [("reference 2 (AI sheet)", REF), ("Blender ground render (C_Establish)", B / "ground/renders/f1/C_Establish.png"),
         ("Unreal round 2 (CAM_Establishing)", R / "captures_after/CAM_Establishing.png")]]
W2, H2 = 560, 420
sbs = Image.new("RGB", (3 * W2, 2 * (H2 + S)), (255, 255, 255))
for r, row in enumerate(rows):
    for c, (lab, p) in enumerate(row):
        sbs.paste(strip(lab, W2), (c * W2, r * (H2 + S)))
        sbs.paste(fit(p, W2, H2), (c * W2, r * (H2 + S) + S))
sbs.save(R / "SBS_COLOUR.png")
print("sheets written")
