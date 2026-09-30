import sys
from PIL import Image, ImageDraw
out = sys.argv[1]; ps = [('ref', r'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/armory/reference/armory3_reference2.png')] + [tuple(a.split('=', 1)) for a in sys.argv[2:]]
ts = []
for lab, p in ps:
    im = Image.open(p).convert('RGB')
    a = im.crop((990, 930, 1110, 1086)).resize((360, 468), Image.LANCZOS)
    b = im.crop((330, 930, 450, 1086)).resize((360, 468), Image.LANCZOS)
    t = Image.new('RGB', (720, 468)); t.paste(b, (0, 0)); t.paste(a, (360, 0))
    ImageDraw.Draw(t).text((5, 5), lab, fill=(255, 255, 0)); ts.append(t)
s = Image.new('RGB', (720 * ((len(ts) + 1) // 2), 468 * 2))
for i, t in enumerate(ts): s.paste(t, ((i // 2) * 720, (i % 2) * 468))
s.save(out)
