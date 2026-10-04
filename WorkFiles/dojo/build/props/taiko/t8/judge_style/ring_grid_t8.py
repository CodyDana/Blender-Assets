# t8: the ring hardware, photo vs ours (judge-aligned frame), 5x with a 10 px grid labelled in frame pixels (as the
# judge's r7 ring_grid5.png), contrast stretched so the black ring reads on the black plate
from PIL import Image, ImageDraw, ImageOps
T = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/props/taiko/t8/judge_style/'
U0, V0, U1, V1, Z = 430, 550, 600, 700, 5
out = Image.new('RGB', (2 * (U1 - U0) * Z + 10, (V1 - V0) * Z), (255, 0, 0))
for k, f in enumerate(('photo.png', 'ours_aligned.png')):
    im = Image.open(T + f).convert('RGB').crop((U0, V0, U1, V1))
    im = ImageOps.autocontrast(im, cutoff=1).point(lambda x: int(255 * (x / 255) ** 0.5))
    im = im.resize(((U1 - U0) * Z, (V1 - V0) * Z), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for u in range(U0, U1, 10):
        d.line([((u - U0) * Z, 0), ((u - U0) * Z, im.height)], fill=(40, 60, 255))
        d.text(((u - U0) * Z + 2, 2), str(u), fill=(255, 255, 0))
    for v in range(V0, V1, 10):
        d.line([(0, (v - V0) * Z), (im.width, (v - V0) * Z)], fill=(40, 60, 255))
        d.text((2, (v - V0) * Z + 2), str(v), fill=(255, 255, 0))
    for v in (572, 672):
        d.line([(0, (v - V0) * Z), (im.width, (v - V0) * Z)], fill=(0, 255, 0), width=2)
    out.paste(im, (k * ((U1 - U0) * Z + 10), 0))
out.save(T + 'ring_grid5_t8.png')
print('saved', out.size)
