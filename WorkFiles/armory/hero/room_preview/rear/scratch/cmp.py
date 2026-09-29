import sys
from PIL import Image
ref, img, out = sys.argv[1:4]
box = tuple(int(v) for v in (sys.argv[4].split(',') if len(sys.argv) > 4 else (200, 20, 1250, 420)))
a = Image.open(ref).convert('RGB').resize((1448, 1086)); b = Image.open(img).convert('RGB')
w, h = box[2]-box[0], box[3]-box[1]
s = 1400 / w
o = Image.new('RGB', (1400, int(h*s)*2 + 8), (255, 255, 255))
o.paste(a.crop(box).resize((1400, int(h*s))), (0, 0)); o.paste(b.crop(box).resize((1400, int(h*s))), (0, int(h*s) + 8))
o.save(out)
