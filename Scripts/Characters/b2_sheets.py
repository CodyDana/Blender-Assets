"""b2_sheets.py - PRIVATE / DO NOT SHIP. Builds renders/unsubdiv_wire.png and renders/stepA_sheet.png (py -3)."""
import json, os
from PIL import Image, ImageDraw, ImageFont

R = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private/renders"
A = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private/stepA_build_analysis.json"


def font(sz):
    for f in ("arialbd.ttf", "arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def label(im, text, sz=26, pos=(10, 8)):
    d = ImageDraw.Draw(im)
    f = font(sz)
    x, y = pos
    bb = d.textbbox((x, y), text, font=f)
    d.rectangle((bb[0] - 6, bb[1] - 4, bb[2] + 6, bb[3] + 4), fill=(20, 20, 24))
    d.text((x, y), text, font=f, fill=(255, 255, 255))


ana = json.load(open(A))
ex = ana["unsubdiv"]["exact_topological"]
sh = [v for k, v in ana["unsubdiv"].items() if k.startswith("SkinShell")][0]
cap = [f"original GLB tris ({sh['orig_verts']:,} v)",
       f"Blender UNSUBDIV x2 ({sh['unsub2']['verts']:,} v, {100*sh['unsub2']['quad_fraction']:.0f}% quads)",
       f"exact un-subdiv L1 ({ex['exact1']['verts']:,} v, 100% quads)",
       f"exact un-subdiv L0 ({ex['exact2']['verts']:,} v, 100% quads)"]
P = 700
wire = Image.new("RGB", (4 * P, 2 * P + 60), (30, 30, 34))
for i in range(4):
    for j, part in enumerate(("face", "back")):
        im = Image.open(f"{R}/_wire_{i}_{part}.png").convert("RGB")
        if j == 0:
            label(im, cap[i], 22)
        wire.paste(im, (i * P, 60 + j * P))
label(wire, "2B private - skin shell wire: original vs Blender Decimate UNSUBDIV vs exact topological un-subdivide "
            f"(re-subdiv error L0: mean {ex['exact2_resubdiv_limit0']['mean_mm']} mm, max {ex['exact2_resubdiv_limit0']['max_mm']} mm)", 24, (12, 14))
wire.save(f"{R}/unsubdiv_wire.png")

rows = [
    ("full", ["full_front", "full_tq", "full_side", "full_back"]),
    ("body (+ underwear, render-only band)", ["body_front", "body_tq", "body_side", "body_back"]),
    ("clothing", ["clothing_front", "clothing_tq", "clothing_side"]),
    ("hair (own framing)", ["hair_front", "hair_tq", "hair_side"]),
    ("face close-ups", ["face_front_close", "face_front_close_nohair", "face_tq_close", "face_side_close"]),
]
W, H = 300, 420
sheet = Image.new("RGB", (5 * W + 20, len(rows) * (H + 10) + 60), (30, 30, 34))
label(sheet, "2B private - step A (PRIVATE / DO NOT SHIP)  1.68 m skin height, Z-up, facing -Y, boots at z=0", 26, (12, 14))
for r, (title, names) in enumerate(rows):
    for c, n in enumerate(names):
        im = Image.open(f"{R}/{n}.png").convert("RGB").resize((W, H), Image.LANCZOS)
        label(im, n, 16, (6, 6))
        sheet.paste(im, (10 + c * W, 60 + r * (H + 10)))
    if r == 3:
        im = Image.open(f"{R}/diag_feet_close.png").convert("RGB").resize((W, H), Image.LANCZOS)
        label(im, "diag_feet_close", 16, (6, 6)); sheet.paste(im, (10 + 4 * W, 60 + r * (H + 10)))
    if r == 2:
        im = Image.open(f"{R}/unsubdiv_wire.png").convert("RGB")
        im = im.crop((0, 60, 4 * P, 60 + P)).resize((W * 2 - 10, int((W * 2 - 10) * P / (4 * P))), Image.LANCZOS)
        sheet.paste(im, (10 + 3 * W, 60 + r * (H + 10) + (H - im.size[1]) // 2))
    d = ImageDraw.Draw(sheet)
    d.text((14 + 0, 60 + r * (H + 10) + H - 26), title, font=font(18), fill=(255, 220, 120))
sheet.save(f"{R}/stepA_sheet.png")
print("ok", sheet.size, wire.size)
