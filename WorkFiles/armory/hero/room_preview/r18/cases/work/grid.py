import sys
from PIL import Image, ImageDraw
src, out, x0, y0, x1, y1 = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])
sc = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
im = Image.open(src).convert('RGB').crop((x0, y0, x1, y1))
im = im.resize((int(im.width*sc), int(im.height*sc)))
d = ImageDraw.Draw(im)
step = 25
for gx in range((x0//step+1)*step, x1, step):
    X = (gx-x0)*sc; c = (0,255,255) if gx % 100 == 0 else (0,120,120)
    d.line([(X,0),(X,im.height)], fill=c, width=1)
    if gx % 50 == 0: d.text((X+2, 2), str(gx), fill=(255,255,0))
for gy in range((y0//step+1)*step, y1, step):
    Y = (gy-y0)*sc; c = (255,0,255) if gy % 100 == 0 else (120,0,120)
    d.line([(0,Y),(im.width,Y)], fill=c, width=1)
    if gy % 50 == 0: d.text((2, Y+2), str(gy), fill=(255,255,0))
im.save(out)
