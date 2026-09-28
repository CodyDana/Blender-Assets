# final pass: the judge's ink-core / paper-blotch measurement (blind_texture.py method) on
# any front render(s) and on the shipped BC.  usage: blender -b --python fx_measure.py -- out.json front1.png [front2.png ...]
import sys, json
import bpy, numpy as np
ROOT = "C:/Users/Cody/Desktop/Blender_Projects/"
REF = ROOT + "References/PaperBomb/paperbomb_guide_v2_real_glyphs.png"
AFF = [1.210940782563025, 1.2142481124161075, 615.9877888655462, 50.69158976510067]
BA = [3.171314994747901, 3.1715845218120817, -31.13865546218487, -18.782088926174495]
argv = sys.argv[sys.argv.index("--") + 1:]
OUTJ = argv[0]; FRONTS = argv[1:]
BCP = ROOT + "Exports/PaperBomb/Textures/T_PaperBomb_BC.png"
for a in list(FRONTS):
    if a.startswith("bc="):
        BCP = a[3:]; FRONTS.remove(a)

def load(p):
    im = bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name = 'Non-Color'
    w, h = im.size; c = im.channels; a = np.empty(w*h*c, np.float32); im.pixels.foreach_get(a)
    a = a.reshape(h, w, c)[::-1, :, :3].copy(); bpy.data.images.remove(im); return a

def bil(img, xs, ys):
    h, w = img.shape[:2]
    x0 = np.clip(np.floor(xs).astype(int), 0, w-2); y0 = np.clip(np.floor(ys).astype(int), 0, h-2)
    fx = np.clip(xs-x0, 0, 1)[..., None]; fy = np.clip(ys-y0, 0, 1)[..., None]
    return (img[y0, x0]*(1-fx)*(1-fy) + img[y0, x0+1]*fx*(1-fy) + img[y0+1, x0]*(1-fx)*fy + img[y0+1, x0+1]*fx*fy)

def lum(a): return a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
def warmth(a): return a[..., 0] - a[..., 2]
ref = load(REF); H, W = ref.shape[:2]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
roi = (xx > 30) & (xx < 270) & (yy > 30) & (yy < 628)
BOXES = {"emblem": (98, 202, 82, 180), "centre_baku": (40, 280, 212, 415), "col_TL": (28, 100, 45, 230),
         "col_TR": (200, 275, 42, 228), "col_BR_yakujin": (200, 272, 408, 528),
         "col_BC_shungyo": (115, 185, 455, 598), "ring": (35, 280, 178, 448)}
def erode(m, n):
    for _ in range(n):
        e = m.copy(); e[1:] &= m[:-1]; e[:-1] &= m[1:]; e[:, 1:] &= m[:, :-1]; e[:, :-1] &= m[:, 1:]; m = e
    return m
def core_stats(L, sl):
    Ls = L[sl]; core = erode(Ls < 0.14, 3)
    return {"mean": round(float(Ls[core].mean()), 4), "std": round(float(Ls[core].std()), 4), "n": int(core.sum())}
def paper_blotch(a):
    L = lum(a); w = warmth(a); ps = roi & (L > 0.8) & (w > 0.05); bl = []
    for yb in range(40, 620, 20):
        for xb in range(40, 260, 20):
            m = ps[yb:yb+20, xb:xb+20]
            if m.sum() > 150: bl.append(np.median(L[yb:yb+20, xb:xb+20][m]))
    return round(float(np.std(bl)), 4)
f = 2.0; H2, W2 = H*2, W*2
y2, x2 = np.mgrid[0:H2, 0:W2].astype(np.float32)
rx = (x2+0.5)/f; ry = (y2+0.5)/f
ref2 = bil(ref, rx-0.5, ry-0.5); Lr2 = lum(ref2)
out = {"ref": {n: core_stats(Lr2, (slice(b[2]*2, b[3]*2), slice(b[0]*2, b[1]*2))) for n, b in BOXES.items()}}
out["ref"]["paper_block_L_std"] = paper_blotch(ref)
bc = load(BCP)
bcb = sum(np.roll(bc, i, 1) for i in range(-2, 2))/4; bcb = sum(np.roll(bcb, i, 0) for i in range(-2, 2))/4
for tag, src in (("bc_point", bc), ("bc_boxed", bcb)):
    s2 = bil(src, BA[0]*rx+BA[2]-0.5, BA[1]*ry+BA[3]-0.5); L2 = lum(s2)
    out[tag] = {n: core_stats(L2, (slice(b[2]*2, b[3]*2), slice(b[0]*2, b[1]*2))) for n, b in BOXES.items()}
    s1 = bil(src, BA[0]*(xx+0.5)+BA[2]-0.5, BA[1]*(yy+0.5)+BA[3]-0.5)
    out[tag]["paper_block_L_std"] = paper_blotch(s1)
for fp in FRONTS:
    fr = load(fp)
    k = np.array([1, 2, 1], np.float32)/4
    frb = (np.roll(fr, 1, 1)*k[0] + fr*k[1] + np.roll(fr, -1, 1)*k[2])
    frb = (np.roll(frb, 1, 0)*k[0] + frb*k[1] + np.roll(frb, -1, 0)*k[2])
    raw = bil(frb, AFF[0]*(xx+0.5)+AFF[2]-0.5, AFF[1]*(yy+0.5)+AFF[3]-0.5)
    def psel(a):
        L = lum(a); return roi & (L > np.percentile(L[roi], 40)) & (warmth(a) > 0.05)
    g = np.median(ref[psel(ref)], 0)/np.median(raw[psel(raw)], 0)
    o2 = np.clip(bil(fr, AFF[0]*rx+AFF[2]-0.5, AFF[1]*ry+AFF[3]-0.5)*g, 0, 1); Lo2 = lum(o2)
    res = {n: core_stats(Lo2, (slice(b[2]*2, b[3]*2), slice(b[0]*2, b[1]*2))) for n, b in BOXES.items()}
    res["gain"] = [round(float(x), 4) for x in g]
    res["paper_block_L_std"] = paper_blotch(np.clip(bil(fr, AFF[0]*(xx+0.5)+AFF[2]-0.5, AFF[1]*(yy+0.5)+AFF[3]-0.5)*g, 0, 1))
    out[fp.split("/")[-1]] = res
json.dump(out, open(OUTJ, "w"), indent=1)
for k, v in out.items():
    print(k, {n: (x["mean"], x["std"]) if isinstance(x, dict) else x for n, x in v.items()})
