"""r17 mat side-by-sides: the crop band (reference 2 y 830-1086, = entry_foreground_crop.png) and the mat at 2x."""
from PIL import Image, ImageDraw
R = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory"
M = R + "/hero/room_preview/r17/mat"
rows = [("reference 2", R + "/reference/armory3_reference2.png"),
        ("live r16 night (HEntCoirL)", R + "/build/renders/night_r16/ref_aspect/C1_EntryReveal_night.png"),
        ("r17 mat night (HEntSisalV)", M + "/final/night/ref_aspect/C1_EntryReveal_night.png"),
        ("r17 mat golden (HEntSisalV)", M + "/final/golden/ref_aspect/C1_EntryReveal_golden.png")]


def sheet(box, scale, out):
    tiles = []
    for lab, p in rows:
        c = Image.open(p).convert("RGB").crop(box)
        c = c.resize((c.width * scale, c.height * scale), Image.LANCZOS)
        d = ImageDraw.Draw(c); d.rectangle((0, 0, 260, 18), fill=(0, 0, 0)); d.text((5, 3), lab, fill=(255, 255, 255))
        tiles.append(c)
    s = Image.new("RGB", (tiles[0].width, sum(t.height for t in tiles)))
    y = 0
    for t in tiles:
        s.paste(t, (0, y)); y += t.height
    s.save(out)


sheet((0, 830, 1448, 1086), 1, M + "/compare/crop_band_ref_live_r17night_r17golden.png")
sheet((340, 920, 1110, 1086), 2, M + "/compare/mat_2x_ref_live_r17night_r17golden.png")
sheet((560, 960, 860, 1060), 3, M + "/compare/field_3x_ref_live_r17night_r17golden.png")
