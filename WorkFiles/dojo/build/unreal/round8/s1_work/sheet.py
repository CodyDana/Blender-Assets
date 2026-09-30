import sys, glob, os
from PIL import Image
d, out = sys.argv[1], sys.argv[2]
names = sys.argv[3].split(",") if len(sys.argv) > 3 else None
fs = [os.path.join(d, n + ".png") for n in names] if names else sorted(glob.glob(os.path.join(d, "*.png")))
tw, th, cols = 480, 330, 4
rows = (len(fs) + cols - 1) // cols
sheet = Image.new("RGB", (tw * cols, th * rows), (0, 0, 0))
for i, f in enumerate(fs):
    t = Image.open(f).convert("RGB"); t.thumbnail((tw, th - 4)); sheet.paste(t, ((i % cols) * tw, (i // cols) * th))
sheet.save(out, quality=85)
