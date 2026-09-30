"""r18 mat side-by-sides: the user's crop (entry_foreground_crop.png = reference 2 y 830-1086, scaled to 1448 wide)
against the live r17 renders, the r18 first try (final_try1) and the r18 second pass (final) (C1 1448 x 1086), plus the mat at 2x / 3x and the down views."""
from PIL import Image, ImageDraw
R = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory"
M = R + "/hero/room_preview/r18/mat"
CROP = R + "/reference/entry_foreground_crop.png"
REF2 = R + "/reference/armory3_reference2.png"
rows = [("r17 live night (HEntSisalW + HEntBraidL)", R + "/build/renders/night_r17/ref_aspect/C1_EntryReveal_night.png"),
        ("r18 try 1 golden (HEntSisalT + HEntBraidC, judged 5.5)", M + "/final_try1/golden/ref_aspect/C1_EntryReveal_golden.png"),
        ("r18 mat night (HEntSisalR + HEntBraidD)", M + "/final/night/ref_aspect/C1_EntryReveal_night.png"),
        ("r18 mat golden (HEntSisalR + HEntBraidD)", M + "/final/golden/ref_aspect/C1_EntryReveal_golden.png")]


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 10 + 6 * len(text), 16), fill=(0, 0, 0))
    d.text((5, 2), text, fill=(255, 255, 255))
    return im


def stack(tiles, out):
    s = Image.new("RGB", (max(t.width for t in tiles), sum(t.height for t in tiles)))
    y = 0
    for t in tiles:
        s.paste(t, (0, y)); y += t.height
    s.save(out)


def sheet(box, scale, out, ref_from_crop=False):
    tiles = []
    if ref_from_crop:   # the user's crop itself, scaled back to reference 2's pixel grid (1448 x 256)
        c = Image.open(CROP).convert("RGB").resize((1448, 256), Image.LANCZOS)
        c = c.crop((box[0], box[1] - 830, box[2], box[3] - 830))
        lab = "entry_foreground_crop.png (x3.13 to C1 scale)"
    else:
        c = Image.open(REF2).convert("RGB").crop(box)
        lab = "reference 2"
    tiles.append(label(c.resize((c.width * scale, c.height * scale), Image.LANCZOS), lab))
    for lab, p in rows:
        c = Image.open(p).convert("RGB").crop(box)
        tiles.append(label(c.resize((c.width * scale, c.height * scale), Image.LANCZOS), lab))
    stack(tiles, out)


sheet((0, 830, 1448, 1086), 1, M + "/compare/crop_band_crop_r17_try1_r18.png", ref_from_crop=True)
sheet((340, 920, 1110, 1086), 2, M + "/compare/mat_2x_ref_r17_try1_r18.png")
sheet((520, 960, 800, 1050), 3, M + "/compare/field_3x_ref_r17_try1_r18.png")
sheet((370, 930, 520, 1080), 4, M + "/compare/left_edge_4x_ref_r17_try1_r18.png")
# the down views, golden over night
tiles = [label(Image.open(M + f"/{d}/{p}/CE_MatDown_{p}.png").convert("RGB"), f"r18 {d} CE_MatDown {p}")
         for p in ("golden", "night") for d in ("final_try1", "final")]
stack(tiles, M + "/compare/matdown_try1_vs_r18_golden_night.png")
print("sheets written to", M + "/compare")
