# silhouette comparison: reference (coverage proxy from luminance vs white) vs render alpha
import bpy, numpy as np, sys, json
a = sys.argv[sys.argv.index('--')+1:]
def load(p):
    i = bpy.data.images.load(p); i.colorspace_settings.name = 'Non-Color'
    x = np.array(i.pixels[:], dtype=np.float32).reshape(i.size[1], i.size[0], i.channels)[::-1]; bpy.data.images.remove(i); return x
ref = load('C:/Users/Cody/Desktop/Blender_Projects/References/BlackHat/blackhat_guide.png')[..., :3]
Ls = ref @ np.array([0.2126, 0.7152, 0.0722])
rc = np.clip((0.985 - Ls)/(0.985 - 0.35), 0, 1)
al = np.clip(load(a[0])[..., 3], 0, 1)
def te(cov, x):
    col = cov[:, x]; idx = np.where(col >= 0.5)[0]
    if len(idx) == 0 or idx[0] == 0: return np.nan
    y = idx[0]; c0, c1 = col[y-1], col[y]; return y - 1 + (0.5-c0)/(c1-c0+1e-9)
def be(cov, x):
    col = cov[:, x]; idx = np.where(col >= 0.5)[0]
    if len(idx) == 0: return np.nan
    y = idx[-1]; c0, c1 = col[y], col[min(y+1, len(col)-1)]; return y + (c0-0.5)/(c0-c1+1e-9)
res = {}
for nm, cov in (('ref', rc), ('ren', al)):
    d = {}; m = cov >= 0.5
    xs = np.where(m.any(0))[0]; ys = np.where(m.any(1))[0]; d['x'] = [int(xs[0]), int(xs[-1])]; d['y'] = [int(ys[0]), int(ys[-1])]
    for s, rg in (('L', range(60, 261)), ('R', range(420, 611))):
        X = np.array(list(rg)); Y = np.array([te(cov, x) for x in X]); ok = ~np.isnan(Y); k, b = np.polyfit(X[ok], Y[ok], 1)
        d['gen'+s] = [round(float(b), 2), round(float(k), 5)]
    d['rimbot340'] = round(float(np.nanmean([be(cov, x) for x in range(330, 351)])), 2)
    d['crowntop'] = round(float(np.nanmin([te(cov, x) for x in range(320, 350)])), 2)
    for t, (x0, x1) in (('tipA', (560, 615)), ('tipB', (615, 668))):
        yy, xx = np.where(m[:, x0:x1]); i = np.argmax(yy); d[t] = [int(xx[i]+x0), int(yy[i])]
    res[nm] = d
mr, ms = rc >= 0.5, al >= 0.5
res['iou'] = round(float((mr & ms).sum()/(mr | ms).sum()), 4); res['xor'] = int((mr ^ ms).sum())
# best integer-ish shift by IoU search
best = None
for dy in np.arange(-5, 5.01, 0.5):
    for dx in np.arange(-3, 3.01, 0.5):
        sh = np.roll(np.roll(al, int(round(dy)), 0), int(round(dx)), 1) >= 0.5
        v = (mr & sh).sum()/(mr | sh).sum()
        if best is None or v > best[0]: best = (float(v), int(round(dx)), int(round(dy)))
res['best_int_shift_iou_dx_dy'] = best
print('SIL ' + json.dumps(res))
