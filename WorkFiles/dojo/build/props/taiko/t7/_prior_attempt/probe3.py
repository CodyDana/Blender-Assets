"""probe: slit candidates (dark vertical streaks just above the upper hem / below the lower hem) + manual picks"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import median_filter, uniform_filter1d
T7 = Path(__file__).resolve().parent
ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
img = Image.open(ROOT / "References/Dojo/taiko_tacks_ref_user.webp").convert("RGB")
a = np.asarray(img).astype(float)
lum = a.mean(2)
h = json.loads((T7 / "probe2_hems.json").read_text())
U = np.array(h["u"])
hu = np.array(h["upper_raw"], float)
hl = np.array(h["lower_raw"], float)
hu_s = median_filter(np.nan_to_num(hu, nan=320), 21)
hl_s = median_filter(np.nan_to_num(hl, nan=870), 21)
sig_u, sig_l = [], []
for i, u in enumerate(U):
    v = int(hu_s[i])
    sig_u.append(lum[v - 34:v - 6, u].min())
    v = int(hl_s[i])
    sig_l.append(lum[v + 6:v + 30, u].min())
sig_u, sig_l = np.array(sig_u), np.array(sig_l)
base_u = median_filter(sig_u, 41)
base_l = median_filter(sig_l, 41)
du, dl = base_u - sig_u, base_l - sig_l
W, Hh = 1640, 900
im = Image.new("RGB", (W, Hh), "white")
d = ImageDraw.Draw(im)
for k, (sg, y0) in enumerate(((du, 220), (dl, 650))):
    for i in range(len(U) - 1):
        d.line([(2 * (U[i] - 100), y0 - sg[i]), (2 * (U[i + 1] - 100), y0 - sg[i + 1])], fill=(0, 0, 0))
    d.line([(0, y0), (W, y0)], fill=(200, 200, 200))
    for x in range(100, 920, 10):
        d.line([(2 * (x - 100), y0), (2 * (x - 100), y0 + (8 if x % 50 else 16))], fill=(0, 0, 255))
        if x % 50 == 0:
            d.text((2 * (x - 100) - 8, y0 + 18), str(x), fill=(0, 0, 255))
im.save(T7 / "probe3_signal.png")
peaks_u = [int(U[i]) for i in range(3, len(U) - 3) if du[i] == du[i - 3:i + 4].max() and du[i] > 25]
peaks_l = [int(U[i]) for i in range(3, len(U) - 3) if dl[i] == dl[i - 3:i + 4].max() and dl[i] > 20]
print("upper peaks", peaks_u)
print("lower peaks", peaks_l)
json.dump({"hu_s": hu_s.tolist(), "hl_s": hl_s.tolist(), "peaks_u": peaks_u, "peaks_l": peaks_l},
          open(T7 / "probe3.json", "w"))
