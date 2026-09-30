"""r17 mat: crop sheet + stats. sheet.py OUT.png img1 [img2 ...] (all 1448x1086 C1): the mat crop (340-1110 x 920-1086)
at 2x, stacked under the reference; prints field mean / B/R, column FFT period at y 960/1010/1050, row period, and the
high-pass contrast (std/mean) of the field."""
import sys
import numpy as np
from PIL import Image, ImageDraw

REF = r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\armory\reference\armory3_reference2.png"
BOX = (340, 920, 1110, 1086)
FIELD = (560, 960, 900, 1040)


def peak(b, lo=2.2, hi=20):
    b = b - np.convolve(b, np.ones(21) / 21, "same")
    b = b[12:-12] * np.hanning(len(b) - 24)
    F = np.abs(np.fft.rfft(b, 8192)); f = np.fft.rfftfreq(8192)
    per = 1 / np.maximum(f, 1e-9)
    m = (per > lo) & (per < hi)
    i = np.argmax(F * m)
    return round(float(per[i]), 2), round(float((F * m)[i] / (F[m].mean() + 1e-9)), 1)


def stats(p):
    rgb = np.asarray(Image.open(p).convert("RGB")).astype(float)
    L = rgb.mean(-1)
    x0, y0, x1, y1 = FIELD
    f = rgb[y0:y1, x0:x1].reshape(-1, 3).mean(0)
    cols = [peak(L[y - 2:y + 3, 480:980].mean(0)) for y in (960, 1010, 1050)]
    rows = [peak(L[948:1066, x - 8:x + 9].mean(1), 2.2, 14) for x in (600, 720, 850)]
    fl = L[y0:y1, x0:x1]
    hp = fl - np.array(Image.fromarray(fl.astype(np.float32)).resize((fl.shape[1] // 12, fl.shape[0] // 12), Image.BILINEAR)
                       .resize((fl.shape[1], fl.shape[0]), Image.BILINEAR))
    return {"field": [round(v, 1) for v in f], "B/R": round(f[2] / f[0], 2), "colP": cols, "rowP": rows,
            "hp_std/mean": round(float(hp.std() / fl.mean()), 3)}


out, imgs = sys.argv[1], [REF] + sys.argv[2:]
tiles = []
for p in imgs:
    im = Image.open(p).convert("RGB")
    c = im.crop(BOX)
    c = c.resize((c.width * 2, c.height * 2), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, 700, 22), fill=(0, 0, 0))
    d.text((6, 4), p.replace("\\", "/").split("/")[-3] + "/" + p.replace("\\", "/").split("/")[-1], fill=(255, 255, 255))
    tiles.append(c)
    print(p.replace("\\", "/").split("armory/")[-1], stats(p))
W = max(t.width for t in tiles)
sheet = Image.new("RGB", (W, sum(t.height for t in tiles)))
y = 0
for t in tiles:
    sheet.paste(t, (0, y)); y += t.height
sheet.save(out)
