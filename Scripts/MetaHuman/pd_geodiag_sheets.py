"""pd_geodiag_sheets.py -- side-by-side sheets of the pd_geodiag_render.py renders (+ UE capture crops). Python 3.12 + PIL."""
from pathlib import Path
from PIL import Image, ImageDraw
G = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_default/geodiag")
R = G / "renders"
UE = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base")


def sheet(name, items, scale=0.5, crop=None, cols=None):
    tiles = []
    for path, label in items:
        im = Image.open(path).convert("RGB")
        if crop:
            im = im.crop(crop)
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        t = Image.new("RGB", (im.width, im.height + 22), (255, 255, 255))
        t.paste(im, (0, 22))
        ImageDraw.Draw(t).text((4, 4), label, fill=(0, 0, 0))
        tiles.append(t)
    cols = cols or len(tiles)
    rows = (len(tiles) + cols - 1) // cols
    w, h = max(t.width for t in tiles), max(t.height for t in tiles)
    out = Image.new("RGB", (cols * (w + 6), rows * (h + 6)), (255, 255, 255))
    for i, t in enumerate(tiles):
        out.paste(t, ((i % cols) * (w + 6), (i // cols) * (h + 6)))
    out.save(G / name)
    print(name, out.size)


sheet("sheet_ue34_plain_vs_ue.png", [
    (UE / "faces/captures/FaceC_Face_ThreeQuarter.png", "UE capture FaceC (MH skin material)"),
    (R / "ue34_ue_plain_FaceC.png", "Blender: FaceC dump geometry, plain mat, UE rig"),
    (R / "ue34_ue_plain_ref.png", "Blender: ref (unmodified conform)"),
    (R / "ue34_ue_plain_Kelvin.png", "Blender: Kelvin (sim-aligned)"),
    (R / "ue34_ue_plain_source.png", "Blender: source input")], scale=1.0, crop=(300, 600, 900, 1050), cols=3)
sheet("sheet_jaw34_frontbelow.png", [
    (R / "jaw34_frontbelow_plain_FaceC.png", "FaceC  jaw close-up, light front-below"),
    (R / "jaw34_frontbelow_plain_Kelvin.png", "Kelvin (aligned)"),
    (R / "jaw34_frontbelow_plain_ref.png", "ref (conform, no face edit)"),
    (R / "jaw34_frontbelow_plain_source.png", "source input")], scale=0.6, cols=2)
sheet("sheet_jaw34_uerig_and_backfaces.png", [
    (R / "jaw34_ue_plain_FaceC.png", "FaceC  UE-like rig (key has shadows)"),
    (R / "jaw34_ue_plain_Kelvin.png", "Kelvin  UE-like rig"),
    (R / "jaw34_ue_back_FaceC.png", "FaceC  backfaces = red"),
    (R / "jaw34_ue_back_Kelvin.png", "Kelvin  backfaces = red")], scale=0.6, cols=2)
sheet("sheet_chin_below.png", [
    (R / "chin_below_frontbelow_plain_FaceC.png", "FaceC  from below-front, light front-below"),
    (R / "chin_below_frontbelow_plain_Kelvin.png", "Kelvin (aligned)"),
    (R / "chin_below_frontbelow_plain_source.png", "source"),
    (R / "chin_below_front_back_FaceC.png", "FaceC backfaces = red"),
    (R / "chin_below_front_back_Kelvin.png", "Kelvin backfaces = red")], scale=0.5, cols=3)
sheet("sheet_earR.png", [
    (R / "earR_front_ue_plain_FaceC.png", "FaceC  -X ear (image-left), UE-like rig"),
    (R / "earR_front_ue_plain_Kelvin.png", "Kelvin (aligned)"),
    (R / "earR_front_ue_plain_source.png", "source"),
    (R / "earR_front_ue_back_FaceC.png", "FaceC backfaces = red"),
    (R / "earR_side_front_plain_FaceC.png", "FaceC -X ear from the side"),
    (R / "earR_side_front_plain_Kelvin.png", "Kelvin -X ear from the side")], scale=0.5, cols=3)
