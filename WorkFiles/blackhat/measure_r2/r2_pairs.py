# r2 pairs: crop the reference and our render (EXR composited over a backdrop drawn from the reference's own backdrop
# pixel distribution) at the same scale. mode 'inspect' = reference always left, to a working dir;
# mode 'blind' = random side per pair; the side list goes to stdout only and is never written to disk.
import bpy, numpy as np, sys, random, os
a = sys.argv[sys.argv.index('--')+1:]
mode, exr, outdir = a[0], a[1], a[2]
def load(p):
    i = bpy.data.images.load(p); i.colorspace_settings.name = 'Non-Color'
    x = np.array(i.pixels[:], dtype=np.float32).reshape(i.size[1], i.size[0], i.channels)[::-1]; bpy.data.images.remove(i); return x
def s2l(s): return np.where(s <= 0.04045, s/12.92, ((s+0.055)/1.055)**2.4)
def l2s(l): l = np.clip(l, 0, 1); return np.where(l <= 0.0031308, l*12.92, 1.055*l**(1/2.4)-0.055)
ref = load('C:/Users/Cody/Desktop/Blender_Projects/References/BlackHat/blackhat_guide.png')[..., :3]
x = load(exr); rgb, al = x[..., :3], np.clip(x[..., 3], 0, 1)
H, W = al.shape
pool = ref[:100].reshape(-1, 3)                                   # reference backdrop pixels (object-free rows)
rng_bg = np.random.default_rng(12345)
bg = s2l(pool[rng_bg.integers(0, len(pool), H*W)].reshape(H, W, 3))
ours = np.round(l2s(rgb + (1-al)[..., None]*bg)*255)/255          # 8-bit like the reference
REG = [((0, 0, 670, 599), 670), ((0, 0, 670, 599), 300),
    ((285, 128, 385, 188), 420), ((180, 175, 300, 255), 420), ((300, 250, 420, 370), 420),
    ((540, 240, 650, 330), 420), ((20, 280, 140, 360), 420), ((220, 365, 420, 440), 480),
    ((40, 320, 200, 420), 480), ((440, 340, 600, 425), 480), ((420, 185, 520, 265), 420),
    ((200, 175, 330, 235), 420), ((470, 240, 580, 380), 420), ((540, 420, 620, 545), 420),
    ((590, 395, 668, 540), 420), ((60, 240, 220, 340), 480), ((130, 225, 250, 320), 420),
    ((0, 255, 95, 365), 420), ((380, 150, 560, 240), 480), ((560, 255, 670, 385), 420)]
def zoom(a, s):
    h, w, _ = a.shape; Hh, Ww = max(1, round(h*s)), max(1, round(w*s))
    if s < 1:
        k = int(round(1/s)); pad = np.pad(a, ((k, k), (k, k), (0, 0)), mode='edge'); acc = np.zeros_like(a)
        for dy in range(k):
            for dx in range(k): acc += pad[k+dy-k//2:k+dy-k//2+h, k+dx-k//2:k+dx-k//2+w]
        a = acc/(k*k)
    ys = (np.arange(Hh)+0.5)/s - 0.5; xs = (np.arange(Ww)+0.5)/s - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, h-1); y1 = np.clip(y0+1, 0, h-1); fy = np.clip(ys - np.floor(ys), 0, 1)[:, None, None]
    x0 = np.clip(np.floor(xs).astype(int), 0, w-1); x1 = np.clip(x0+1, 0, w-1); fx = np.clip(xs - np.floor(xs), 0, 1)[None, :, None]
    top = a[y0][:, x0]*(1-fx) + a[y0][:, x1]*fx; bot = a[y1][:, x0]*(1-fx) + a[y1][:, x1]*fx
    return top*(1-fy) + bot*fy
def save(arr, path):
    Hh, Ww, _ = arr.shape
    im = bpy.data.images.new('p', Ww, Hh, alpha=False); im.colorspace_settings.name = 'Non-Color'
    px = np.ones((Hh, Ww, 4), np.float32); px[..., :3] = np.clip(arr, 0, 1); im.pixels[:] = px[::-1].ravel()
    im.filepath_raw = path; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
os.makedirs(outdir, exist_ok=True)
rng = random.SystemRandom(); sides = []
for i, ((x0, y0, x1, y1), L) in enumerate(REG):
    s = L/max(x1-x0, y1-y0)
    A = zoom(ref[y0:y1, x0:x1], s); B = zoom(ours[y0:y1, x0:x1], s)
    gap = np.full((A.shape[0], 12, 3), 0.5, np.float32)
    if mode == 'blind':
        ol = rng.random() < 0.5; sides.append('left' if ol else 'right')
        pair = np.concatenate([B, gap, A] if ol else [A, gap, B], 1)
    else:
        pair = np.concatenate([A, gap, B], 1)
    save(pair, os.path.join(outdir, f'pair_{i+1:02d}.png'))
if mode == 'blind': print('SIDES ' + ' '.join(sides))
print('DONE', len(REG))
