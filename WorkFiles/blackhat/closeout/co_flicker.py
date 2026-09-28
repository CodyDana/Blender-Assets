# Temporal second-difference flicker on the EEVEE 1-sample turn frames (old vs new build), sRGB luminance.
import bpy, numpy as np, json, glob
D = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/closeout/'
def load(p):
    i = bpy.data.images.load(p); i.colorspace_settings.name = 'Non-Color'
    x = np.array(i.pixels[:], dtype=np.float32).reshape(i.size[1], i.size[0], i.channels)[::-1]; bpy.data.images.remove(i); return x
def l2s(l): l = np.clip(l, 0, 1); return np.where(l <= 0.0031308, l*12.92, 1.055*l**(1/2.4)-0.055)
lw = np.array([0.2126, 0.7152, 0.0722]); res = {}; maps = {}; frames0 = {}
for tag in ('old', 'new'):
    fs = sorted(glob.glob(D+f'turn_{tag}/f_*.exr')); X = [load(f) for f in fs]
    S = np.stack([l2s(x[..., :3] @ lw) for x in X]); A = np.stack([x[..., 3] for x in X]).min(0)
    m = A > 0.99
    F = np.abs(S[1:-1] - 0.5*(S[:-2] + S[2:])).mean(0)
    F1 = np.abs(np.diff(S, axis=0)).mean(0)
    v = F[m]; res[tag] = {'hat_px': int(m.sum()), 'mean_srgb': round(float(S[:, m].mean()), 4),
        'flicker2_mean': round(float(v.mean()), 5), 'flicker2_p99': round(float(np.percentile(v, 99)), 5),
        'flicker2_p999': round(float(np.percentile(v, 99.9)), 5),
        'frac_px_flicker2_gt_0.02': round(float((v > 0.02).mean()), 5),
        'flicker2_mean_rel': round(float(v.mean()/S[:, m].mean()), 4), 'diff1_mean': round(float(F1[m].mean()), 5)}
    maps[tag] = np.where(m, F, 0); frames0[tag] = np.where(A > 0.5, S[len(S)//2], 1.0)
print('FLICKER ' + json.dumps(res))
H, W = maps['new'].shape
y = np.where((maps['new'] > 0).any(1) | (maps['old'] > 0).any(1))[0]; x = np.where((maps['new'] > 0).any(0) | (maps['old'] > 0).any(0))[0]
y0, y1, x0, x1 = y[0]-4, y[-1]+5, x[0]-4, x[-1]+5
tiles = [frames0['old'][y0:y1, x0:x1], frames0['new'][y0:y1, x0:x1],
         1 - np.clip(maps['old'][y0:y1, x0:x1]/0.04, 0, 1), 1 - np.clip(maps['new'][y0:y1, x0:x1]/0.04, 0, 1)]
g = np.full((y1-y0, 6), 0.5); top = np.concatenate([tiles[0], g, tiles[1]], 1); bot = np.concatenate([tiles[2], g, tiles[3]], 1)
img = np.concatenate([top, np.full((6, top.shape[1]), 0.5), bot], 0)
k = 3; img = np.kron(img, np.ones((k, k)))
h, w = img.shape; im = bpy.data.images.new('f', w, h, alpha=False); im.colorspace_settings.name = 'Non-Color'
px = np.ones((h, w, 4), np.float32); px[..., 0] = px[..., 1] = px[..., 2] = img; im.pixels[:] = px[::-1].ravel()
im.filepath_raw = D+'closeout_flicker_old_new.png'; im.file_format = 'PNG'; im.save(); print('SAVED')
