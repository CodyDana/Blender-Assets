# judge r7: clean aligned photo / ours (photo camera, same head width) built from the t7 render itself, then pair crops
import json, numpy as np
from PIL import Image
from scipy import ndimage as ndi
R = 'C:/Users/Cody/Desktop/Blender_Projects/'
T = R + 'WorkFiles/dojo/build/props/taiko/'
ref = Image.open(R + 'References/Dojo/taiko_tacks_ref_user.webp').convert('RGB')
o = Image.open(T + 't7/silhouette_ours_refcam_photo.png').convert('RGBA')
w = json.load(open(T + 't7/silhouette_widths.json'))
er, eo, s = w['head_ellipse_ref_px'], w['head_ellipse_ours_px'], w['scale_ours_to_ref']
OFF = 200
bg = Image.new('RGBA', o.size, (255, 255, 255, 255)); orgb = Image.alpha_composite(bg, o).convert('RGB')
nw, nh = round(o.width * s), round(o.height * s)
ox = round(er[0] - eo[0] * s); oy = round(er[1] - (eo[1] + OFF) * s)
B = Image.new('RGB', (1024, 1024), 'white'); B.paste(orgb.resize((nw, nh), Image.LANCZOS), (ox, oy))
Bm = Image.new('L', (1024, 1024), 0); Bm.paste(o.split()[3].resize((nw, nh), Image.LANCZOS), (ox, oy))
B.save(T + 'judge_r7/ours_aligned.png'); ref.save(T + 'judge_r7/photo.png')
def pair(x0, y0, x1, y1, name, z=2, vertical=True):
    a = ref.crop((x0, y0, x1, y1)); b = B.crop((x0, y0, x1, y1)); ww, hh = a.size
    if vertical:
        out = Image.new('RGB', (ww * z, 2 * hh * z + 8), (255, 0, 0)); out.paste(a.resize((ww * z, hh * z), Image.LANCZOS), (0, 0)); out.paste(b.resize((ww * z, hh * z), Image.LANCZOS), (0, hh * z + 8))
    else:
        out = Image.new('RGB', (2 * ww * z + 8, hh * z), (255, 0, 0)); out.paste(a.resize((ww * z, hh * z), Image.LANCZOS), (0, 0)); out.paste(b.resize((ww * z, hh * z), Image.LANCZOS), (ww * z + 8, 0))
    out.save(T + 'judge_r7/' + name)
pair(0, 0, 1024, 1024, 'pair_full.png', 1, vertical=False)
pair(330, 150, 700, 400, 'pair_upper_band_centre.png', 2)
pair(60, 140, 400, 420, 'pair_upper_left_ear.png', 2, vertical=False)
pair(640, 140, 990, 420, 'pair_upper_right_ear.png', 2, vertical=False)
pair(80, 700, 960, 1010, 'pair_lower_collar.png', 1)
pair(400, 380, 650, 640, 'pair_ring.png', 3, vertical=False)
# silhouettes per row
ra = np.asarray(ref).astype(float); refm = ndi.binary_fill_holes(ra.min(2) < 240)
om = ndi.binary_fill_holes(np.asarray(Bm) > 128)
res = {}
for y in range(140, 1000, 2):
    r_ = np.where(refm[y])[0]; q = np.where(om[y])[0]
    if len(r_) and len(q): res[y] = (int(q.min() - r_.min()), int(q.max() - r_.max()))
json.dump(res, open(T + 'judge_r7/sil_rows.json', 'w'))
def runs(lo, hi):
    L = [(y, d[0]) for y, d in res.items() if lo <= y < hi]; Rr = [(y, d[1]) for y, d in res.items() if lo <= y < hi]
    bl = [y for y, v in L if abs(v) > 8]; br = [y for y, v in Rr if abs(v) > 8]
    return dict(left_out=len(bl), left_rows=(min(bl), max(bl)) if bl else None, left_max=max((abs(v) for y, v in L), default=0),
                right_out=len(br), right_rows=(min(br), max(br)) if br else None, right_max=max((abs(v) for y, v in Rr), default=0), n=len(L))
print('UPPER skirt 200-380 (left: + = ours inside; right: - = ours inside)', runs(200, 380))
print('BODY 380-700', runs(380, 700))
print('LOWER skirt 700-900', runs(700, 900))
print('BOTTOM 900-1000', runs(900, 1000))
for y in range(700, 900, 10): print(y, res.get(y))
