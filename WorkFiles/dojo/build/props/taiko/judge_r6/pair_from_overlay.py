# judge r6: aligned photo / ours crops cut from the t6 silhouette_overlay panels A and B (same camera, same head width)
from PIL import Image
T = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/props/taiko/'
im = Image.open(T + 't6/silhouette_overlay.png').convert('RGB')
XA, XB = 0, 1038
def pair(x0, y0, x1, y1, name, z=2, vertical=True):
    a = im.crop((XA + x0, y0, XA + x1, y1)); b = im.crop((XB + x0, y0, XB + x1, y1))
    w, h = a.size
    if vertical:
        out = Image.new('RGB', (w * z, 2 * h * z + 8), (255, 0, 0)); out.paste(a.resize((w * z, h * z)), (0, 0)); out.paste(b.resize((w * z, h * z)), (0, h * z + 8))
    else:
        out = Image.new('RGB', (2 * w * z + 8, h * z), (255, 0, 0)); out.paste(a.resize((w * z, h * z)), (0, 0)); out.paste(b.resize((w * z, h * z)), (w * z + 8, 0))
    out.save(T + 'judge_r6/' + name)
pair(0, 40, 1024, 1064, 'pair_full.png', 1, vertical=False)
pair(330, 160, 700, 400, 'pair_upper_band_centre.png', 2)
pair(90, 150, 400, 420, 'pair_upper_left_ear.png', 2, vertical=False)
pair(120, 700, 920, 1010, 'pair_lower_collar.png', 1)
