# Independent measurer r1: silhouette + tone comparison between the reference and an EXR render of the shipped asset.
import bpy, numpy as np, sys, json
argv = sys.argv[sys.argv.index('--')+1:]
exr = argv[0]; png_out = argv[1]; exposure = float(argv[2]) if len(argv) > 2 else 1.0
REF = 'C:/Users/Cody/Desktop/Blender_Projects/References/BlackHat/blackhat_guide.png'
def load(p, cs=None):
    i = bpy.data.images.load(p)
    if cs: i.colorspace_settings.name = cs
    a = np.array(i.pixels[:], dtype=np.float32).reshape(i.size[1], i.size[0], i.channels)[::-1]
    return a
ref = load(REF)[..., :3]  # sRGB-decoded linear? Blender pixels for 8-bit sRGB png are stored as sRGB floats
def s2l(s): return np.where(s <= 0.04045, s/12.92, ((s+0.055)/1.055)**2.4)
def l2s(l): l = np.clip(l, 0, 1); return np.where(l <= 0.0031308, l*12.92, 1.055*l**(1/2.4)-0.055)
ref_lin = s2l(ref)
r = load(exr); rgb = r[..., :3]*exposure; al = np.clip(r[..., 3], 0, 1)
comp_lin = rgb + (1-al)[..., None]*1.0     # premultiplied over white
comp_s = l2s(comp_lin)
H, W = al.shape
# save png
img = bpy.data.images.new('o', W, H, alpha=False); img.colorspace_settings.name = 'Non-Color'
px = np.ones((H, W, 4), np.float32); px[..., :3] = comp_s; img.pixels[:] = px[::-1].ravel()
img.filepath_raw = png_out; img.file_format = 'PNG'; img.save()
lumw = np.array([0.2126, 0.7152, 0.0722])
Lr = ref_lin @ lumw; Ls = comp_lin @ lumw
ref_cov = np.clip((0.985 - l2s(Lr)) / (0.985 - 0.35), 0, 1)   # sRGB-space coverage proxy
ren_cov = al
def top_edge(cov, x):
    col = cov[:, x]; idx = np.where(col >= 0.5)[0]
    if len(idx) == 0: return np.nan
    y = idx[0]; 
    if y == 0: return 0.0
    c0, c1 = col[y-1], col[y]
    return y - 0.5 + (0.5 - c0)/(c1 - c0 + 1e-9) - 0.5  # subpixel crossing
def bot_edge(cov, x):
    col = cov[:, x]; idx = np.where(col >= 0.5)[0]
    return np.nan if len(idx) == 0 else idx[-1]
res = {}
for nm, cov in (('ref', ref_cov), ('ren', ren_cov)):
    d = {}
    m = cov >= 0.5
    xs = np.where(m.any(0))[0]; ys = np.where(m.any(1))[0]
    d['x_extent'] = [int(xs[0]), int(xs[-1])]; d['y_extent'] = [int(ys[0]), int(ys[-1])]
    for side, rng in (('left', range(60, 261)), ('right', range(420, 611))):
        X = np.array(list(rng)); Y = np.array([top_edge(cov, x) for x in X]); ok = ~np.isnan(Y)
        k, b = np.polyfit(X[ok], Y[ok], 1); d[f'gen_{side}'] = [float(b), float(k)]
        d[f'gen_{side}_rms'] = float(np.sqrt(np.mean((Y[ok] - (k*X[ok]+b))**2)))
    d['rim_bottom_y_at_340'] = float(np.nanmean([bot_edge(cov, x) for x in range(335, 346)]))
    d['crown_top_y'] = float(np.nanmin([top_edge(cov, x) for x in range(320, 350)]))
    # tail tips: lowest object pixel for x in 560..620 and 620..664
    for tnm, (a, bb) in (('tipA', (560, 615)), ('tipB', (615, 665))):
        sub = m[:, a:bb]; yy, xx = np.where(sub); i = np.argmax(yy)
        d[tnm] = [int(xx[i]+a), int(yy[i])]
    res[nm] = d
mr = ref_cov >= 0.5; ms = ren_cov >= 0.5
res['iou'] = float((mr & ms).sum() / (mr | ms).sum())
res['xor_px'] = int((mr ^ ms).sum())
# tone: object pixels well inside both masks
both = (ref_cov > 0.98) & (ren_cov > 0.98)
for nm, L, lin in (('ref', Lr, ref_lin), ('ren', Ls, comp_lin)):
    v = L[both]; res[nm]['lum_p10_50_90'] = [float(np.percentile(v, p)) for p in (10, 50, 90)]
    c = lin[both]; s = c.sum(1, keepdims=True) + 1e-9; res[nm]['chroma'] = (c/s).mean(0).round(4).tolist()
# regional medians (image boxes): front bay, left worn, right bay, band/knot, tails, rim front
boxes = {'front_bay': (300, 330, 380, 380), 'left_worn': (80, 250, 200, 330), 'left_mid': (170, 230, 260, 300),
         'right_bay': (560, 270, 630, 320), 'knot': (445, 205, 480, 240), 'tailA_below_rim': (565, 440, 600, 510),
         'tailB_below_rim': (615, 430, 645, 500), 'rim_front': (240, 405, 440, 432), 'cap': (305, 145, 365, 160),
         'upper_cone': (250, 170, 330, 210)}
res['regions_lin_p50'] = {}
for k, (x0, y0, x1, y1) in boxes.items():
    sel = both[y0:y1, x0:x1]
    res['regions_lin_p50'][k] = [float(np.median(Lr[y0:y1, x0:x1][sel])) if sel.any() else None,
                                 float(np.median(Ls[y0:y1, x0:x1][sel])) if sel.any() else None]
# local contrast (texture crispness): std of high-pass in sRGB within boxes
def hp_std(S, x0, y0, x1, y1, sel):
    a = S[y0:y1, x0:x1]; 
    blur = (a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:] + a[1:-1, 1:-1]) / 5
    h = (a[1:-1, 1:-1] - blur)[sel[1:-1, 1:-1]]
    return float(h.std())
res['highpass_std_srgb'] = {}
for k, (x0, y0, x1, y1) in boxes.items():
    sel = both[y0:y1, x0:x1]
    res['highpass_std_srgb'][k] = [hp_std(l2s(Lr), x0, y0, x1, y1, sel), hp_std(l2s(Ls), x0, y0, x1, y1, sel)]
print('RESULT ' + json.dumps(res))
