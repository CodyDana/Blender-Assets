# Compose an EXR (or basis combination) over white, save sRGB PNG, and compare tone / local contrast with the reference by region.
import bpy, numpy as np, sys, json
a = sys.argv[sys.argv.index('--')+1:]
src, png_out = a[0], a[1]
D = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/measure_r2/'
def load(p):
    i = bpy.data.images.load(p); i.colorspace_settings.name = 'Non-Color'
    x = np.array(i.pixels[:], dtype=np.float32).reshape(i.size[1], i.size[0], i.channels)[::-1]; bpy.data.images.remove(i); return x
def s2l(s): return np.where(s <= 0.04045, s/12.92, ((s+0.055)/1.055)**2.4)
def l2s(l): l = np.clip(l, 0, 1); return np.where(l <= 0.0031308, l*12.92, 1.055*l**(1/2.4)-0.055)
ref_lin = s2l(load('C:/Users/Cody/Desktop/Blender_Projects/References/BlackHat/blackhat_guide.png')[..., :3])
if src.endswith('.json'):
    cfg = json.load(open(src)); acc = None
    for n, th, el, pw in cfg['lights']:
        if pw <= 0: continue
        x = load(D+f'r2_basis_{n}.exr'); acc = x[..., :3]*pw/100 if acc is None else acc + x[..., :3]*pw/100; al = x[..., 3]
    x = load(D+'r2_basis_world.exr'); acc = acc + x[..., :3]*cfg['world']; rgb = acc
else:
    x = load(src); rgb = x[..., :3]; al = x[..., 3]
al = np.clip(al, 0, 1); comp = rgb + (1-al)[..., None]
H, W = al.shape
im = bpy.data.images.new('o', W, H, alpha=False); im.colorspace_settings.name = 'Non-Color'
px = np.ones((H, W, 4), np.float32); px[..., :3] = l2s(comp); im.pixels[:] = px[::-1].ravel()
im.filepath_raw = png_out; im.file_format = 'PNG'; im.save()
lw = np.array([0.2126, 0.7152, 0.0722]); Lr = ref_lin @ lw; Ls = comp @ lw
both = (Lr < 0.35) & (al > 0.98)
e = both.copy()
for dy in (-2, 0, 2):
    for dx in (-2, 0, 2): e &= np.roll(np.roll(both, dy, 0), dx, 1)
boxes = {'front_bay': (300, 330, 380, 380), 'left_worn': (80, 250, 200, 330), 'left_mid': (170, 230, 260, 300),
         'far_left': (20, 280, 90, 330), 'right_bay': (560, 270, 630, 320), 'knot': (445, 205, 480, 240),
         'tailA_below_rim': (565, 440, 600, 510), 'tailB_below_rim': (615, 430, 645, 500), 'rim_front': (240, 405, 440, 432),
         'cap': (305, 145, 365, 160), 'upper_cone': (250, 170, 330, 210), 'band_left': (215, 185, 330, 215)}
def hp(S):
    b = (S[:-2, 1:-1] + S[2:, 1:-1] + S[1:-1, :-2] + S[1:-1, 2:] + S[1:-1, 1:-1])/5
    return S[1:-1, 1:-1] - b
out = {'overall_lin_p10_50_90': {}}
for nm, L in (('ref', Lr), ('ours', Ls)): out['overall_lin_p10_50_90'][nm] = [round(float(np.percentile(L[e], p)), 4) for p in (10, 50, 90)]
out['regions'] = {}
for k, (x0, y0, x1, y1) in boxes.items():
    s = e[y0:y1, x0:x1]
    if s.sum() < 20: continue
    r = {}
    for nm, L in (('ref', Lr), ('ours', Ls)):
        v = L[y0:y1, x0:x1][s]; h = hp(l2s(L[y0:y1, x0:x1]))[s[1:-1, 1:-1]]
        # pale-wear coverage proxy: pixels > 1.8 x local p30 (spec 9 definition, per box)
        p30 = np.percentile(v, 30)
        r[nm] = {'p50': round(float(np.median(v)), 4), 'p95': round(float(np.percentile(v, 95)), 4),
                 'p95/p50': round(float(np.percentile(v, 95)/np.median(v)), 2), 'hp_std_srgb': round(float(h.std()), 4),
                 'wear_cov': round(float((v > 1.8*p30).mean()), 3)}
    out['regions'][k] = r
print('ANA ' + json.dumps(out))
