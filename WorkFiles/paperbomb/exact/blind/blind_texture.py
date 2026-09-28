# quantify the tells found in the blind test: ink-core texture, edge sharpness, paper low-frequency variation
import bpy, numpy as np, json
exec(open("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/blind/blind_build.py", encoding="utf-8-sig").read().split("key = {}")[0].split("# light anti-alias")[0])
BOXES = {
    "emblem": (98, 202, 82, 180), "centre_baku": (40, 280, 212, 415), "col_TL": (28, 100, 45, 230),
    "col_TR": (200, 275, 42, 228), "col_BR_yakujin": (200, 272, 408, 528), "col_BC_shungyo": (115, 185, 455, 598),
    "ring": (35, 280, 178, 448)}
g = np.array([1.168451629171994, 1.1793596431678997, 1.2031434706849922], np.float32)
# ours at render-native density, 2x oversampled onto a 2x ref grid (no prefilter)
f = 2.0; H2, W2 = H*2, W*2
y2, x2 = np.mgrid[0:H2, 0:W2].astype(np.float32)
rx = (x2+0.5)/f; ry = (y2+0.5)/f
ours2 = np.clip(bil(fr, AFF[0]*rx+AFF[2]-0.5, AFF[1]*ry+AFF[3]-0.5)*g, 0, 1)
ref2 = bil(ref, rx-0.5, ry-0.5)
bc = load(ROOT + "Exports/PaperBomb/Textures/T_PaperBomb_BC.png"); BA = [3.171314994747901, 3.1715845218120817, -31.13865546218487, -18.782088926174495]
bc2 = bil(bc, BA[0]*rx+BA[2]-0.5, BA[1]*ry+BA[3]-0.5)
# BC box-averaged to the reference density (area of one ref px ~ 3.17 texels): 4x4 box before sampling
kb = np.ones(4, np.float32)/4; bcb = bc.copy()
for sh in (0,):
    pass
bcb = sum(np.roll(bcb, i, 1) for i in range(-2, 2))/4; bcb = sum(np.roll(bcb, i, 0) for i in range(-2, 2))/4
bcr = bil(bcb, BA[0]*rx+BA[2]-0.5, BA[1]*ry+BA[3]-0.5)
roi = (xx > 30) & (xx < 270) & (yy > 30) & (yy < 628)
BOXES = {"emblem": BOXES["emblem"]}
def erode(m, n):
    for _ in range(n):
        e = m.copy(); e[1:] &= m[:-1]; e[:-1] &= m[1:]; e[:, 1:] &= m[:, :-1]; e[:, :-1] &= m[:, 1:]; m = e
    return m
out = {}
Lr2 = lum(ref2); Lo2 = lum(ours2)
for n, (x0, x1, y0, y1) in BOXES.items():
    sl = (slice(y0*2, y1*2), slice(x0*2, x1*2))
    res = {}
    for tag, L in (("ref", Lr2[sl]), ("ours", Lo2[sl]), ("bc_point", lum(bc2)[sl]), ("bc_boxed", lum(bcr)[sl])):
        core = erode(L < 0.14, 3)
        # edge sharpness: 10-90 rise measured as mean gradient magnitude on the ink edge band
        gy, gx = np.gradient(L); gm = np.hypot(gx, gy)
        band = (L > 0.25) & (L < 0.6)
        res[tag] = {"core_px": int(core.sum()), "core_L_mean": round(float(L[core].mean()), 4),
                    "core_L_std": round(float(L[core].std()), 4), "core_L_p95": round(float(np.percentile(L[core], 95)), 4),
                    "edge_grad_mean": round(float(gm[band].mean()), 4)}
    out[n] = res
    print(n, res)
# paper low-frequency variation (block medians of paper, 20 px blocks on ref grid)
for tag, a in (("ref", ref), ("ours", np.clip(warp_front(AFF)*g, 0, 1))):
    L = lum(a); w = warmth(a); ps = roi & (L > 0.8) & (w > 0.05)
    bl = []; bw = []
    for yb in range(40, 620, 20):
        for xb in range(40, 260, 20):
            m = ps[yb:yb+20, xb:xb+20]
            if m.sum() > 150:
                bl.append(np.median(L[yb:yb+20, xb:xb+20][m])); bw.append(np.median(w[yb:yb+20, xb:xb+20][m]))
    out["paper_" + tag] = {"block_L_std": round(float(np.std(bl)), 4), "block_warmth_std": round(float(np.std(bw)), 4),
                           "block_warmth_range": [round(float(np.min(bw)), 3), round(float(np.max(bw)), 3)]}
    print("paper", tag, out["paper_" + tag])
json.dump(out, open(OUT + "blind_texture.json", "w"), indent=1)

