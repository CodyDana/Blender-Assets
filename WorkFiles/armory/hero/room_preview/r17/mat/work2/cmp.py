"""cmp.py OUTPREFIX label=path ... : mat sheets (field 3x, mat 2x, right edge 3x) with reference 2 first + metrics."""
import sys
import numpy as np
from PIL import Image, ImageDraw
REF = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/reference/armory3_reference2.png"
out = sys.argv[1]
rows = [("reference 2", REF)] + [tuple(a.split("=", 1)) for a in sys.argv[2:]]


def sheet(box, scale, path, horiz=False):
    tiles = []
    for lab, p in rows:
        c = Image.open(p).convert("RGB").crop(box)
        c = c.resize((c.width * scale, c.height * scale), Image.LANCZOS)
        d = ImageDraw.Draw(c); d.rectangle((0, 0, 8 * len(lab) + 10, 16), fill=(0, 0, 0)); d.text((5, 2), lab, fill=(255, 255, 255))
        tiles.append(c)
    if horiz:
        s = Image.new("RGB", (sum(t.width for t in tiles), tiles[0].height)); x = 0
        for t in tiles: s.paste(t, (x, 0)); x += t.width
    else:
        s = Image.new("RGB", (tiles[0].width, sum(t.height for t in tiles))); y = 0
        for t in tiles: s.paste(t, (0, y)); y += t.height
    s.save(path)


def metrics(p):
    im = np.asarray(Image.open(p).convert("RGB")).astype(float)
    L = im.mean(-1)
    a = L[965:1045, 600:856]
    k = np.ones(9) / 9
    b = np.apply_along_axis(lambda r: np.convolve(np.pad(r, 4, mode="edge"), k, "valid"), 1, a)
    b = np.apply_along_axis(lambda r: np.convolve(np.pad(r, 4, mode="edge"), k, "valid"), 0, b)
    hp = a - b
    lc = hp.std() / a.mean()
    # column vs row energy: horizontal (along x) and vertical high-pass variance
    gx = np.diff(a, axis=1).std(); gy = np.diff(a, axis=0).std()
    rgb = im[965:1045, 600:856].reshape(-1, 3).mean(0)
    return dict(mean=round(float(a.mean()), 1), local_contrast=round(float(lc), 3), gx=round(float(gx), 2),
                gy=round(float(gy), 2), gy_gx=round(float(gy / gx), 2), chroma=[round(float(v), 3) for v in rgb / rgb.sum()])


for lab, p in rows:
    print(lab, metrics(p))
sheet((560, 960, 860, 1060), 3, out + "_field3x.png")
sheet((340, 900, 1110, 1086), 2, out + "_mat2x.png")
sheet((960, 900, 1200, 1086), 3, out + "_right3x.png", horiz=True)
sheet((0, 830, 1448, 1086), 1, out + "_band.png")
