# Crop pairs of the reference and our render at the same scale. mode 'inspect' = fixed order (ref left) to a given dir;
# mode 'blind' = random side per pair; the side list is printed to stdout only, never written.
import bpy, numpy as np, sys, random, os
argv = sys.argv[sys.argv.index('--')+1:]
mode, ours_png, outdir = argv[0], argv[1], argv[2]
REF = 'C:/Users/Cody/Desktop/Blender_Projects/References/BlackHat/blackhat_guide.png'
def load(p):
    i = bpy.data.images.load(p); i.colorspace_settings.name = 'Non-Color'
    a = np.array(i.pixels[:], dtype=np.float32).reshape(i.size[1], i.size[0], i.channels)[::-1][..., :3]
    bpy.data.images.remove(i); return a
ref = load(REF); ours = load(ours_png)
REG = [  # (x0, y0, x1, y1) in reference px, output long side
    ((0, 0, 670, 599), 670), ((0, 0, 670, 599), 300),
    ((285, 128, 385, 188), 420), ((180, 175, 300, 255), 420), ((300, 250, 420, 370), 420),
    ((540, 240, 650, 330), 420), ((20, 280, 140, 360), 420), ((220, 365, 420, 440), 480),
    ((40, 320, 200, 420), 480), ((440, 340, 600, 425), 480), ((420, 185, 520, 265), 420),
    ((200, 175, 330, 235), 420), ((470, 240, 580, 380), 420), ((540, 420, 620, 545), 420),
    ((590, 395, 668, 540), 420), ((60, 240, 220, 340), 480), ((130, 225, 250, 320), 420),
    ((0, 255, 95, 365), 420), ((380, 150, 560, 240), 480), ((560, 255, 670, 385), 420)]
def zoom(a, s):
    h, w, _ = a.shape; H, W = max(1, round(h*s)), max(1, round(w*s))
    ys = (np.arange(H)+0.5)/s - 0.5; xs = (np.arange(W)+0.5)/s - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, h-1); y1 = np.clip(y0+1, 0, h-1); fy = np.clip(ys - y0, 0, 1)[:, None, None]
    x0 = np.clip(np.floor(xs).astype(int), 0, w-1); x1 = np.clip(x0+1, 0, w-1); fx = np.clip(xs - x0, 0, 1)[None, :, None]
    if s < 1:  # box prefilter for downscale
        k = int(round(1/s)); pad = np.pad(a, ((k, k), (k, k), (0, 0)), mode='edge'); acc = np.zeros_like(a)
        for dy in range(k):
            for dx in range(k): acc += pad[k+dy-k//2:k+dy-k//2+h, k+dx-k//2:k+dx-k//2+w]
        a = acc/(k*k)
    top = a[y0][:, x0]*(1-fx) + a[y0][:, x1]*fx; bot = a[y1][:, x0]*(1-fx) + a[y1][:, x1]*fx
    return top*(1-fy) + bot*fy
def save(arr, path):
    H, W, _ = arr.shape
    im = bpy.data.images.new('p', W, H, alpha=False); im.colorspace_settings.name = 'Non-Color'
    px = np.ones((H, W, 4), np.float32); px[..., :3] = np.clip(arr, 0, 1); im.pixels[:] = px[::-1].ravel()
    im.filepath_raw = path; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
os.makedirs(outdir, exist_ok=True)
rng = random.SystemRandom(); sides = []
for i, ((x0, y0, x1, y1), L) in enumerate(REG):
    s = L / max(x1-x0, y1-y0)
    a = zoom(ref[y0:y1, x0:x1], s); b = zoom(ours[y0:y1, x0:x1], s)
    gap = np.full((a.shape[0], 12, 3), 0.5, np.float32)
    if mode == 'blind':
        ours_left = rng.random() < 0.5; sides.append('left' if ours_left else 'right')
        pair = np.concatenate([b, gap, a] if ours_left else [a, gap, b], 1)
    else:
        pair = np.concatenate([a, gap, b], 1)
    save(pair, os.path.join(outdir, f'pair_{i+1:02d}.png'))
if mode == 'blind':
    print('SIDES ' + ' '.join(sides))
print('DONE', len(REG))
