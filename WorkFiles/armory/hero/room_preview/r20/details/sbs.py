# sbs.py <out> <box x0,y0,x1,y1> <k> <img>... : crops stacked vertically (labels), ref first
import sys
from PIL import Image, ImageDraw
out, box, k = sys.argv[1], tuple(map(int, sys.argv[2].split(','))), float(sys.argv[3])
ims = sys.argv[4:]
w, h = int((box[2]-box[0])*k), int((box[3]-box[1])*k)
S = Image.new('RGB', (w, h*len(ims)))
for i, p in enumerate(ims):
    lab = p.split('|')[0] if '|' in p else p.split('/')[-1]
    p = p.split('|')[-1]
    c = Image.open(p).convert('RGB').crop(box).resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(c); d.rectangle([0, 0, 8*len(lab)+8, 18], fill=(0, 0, 0)); d.text((4, 3), lab, fill=(255, 255, 0))
    S.paste(c, (0, h*i))
S.save(out); print(out, S.size)
