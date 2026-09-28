import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/m2")
from m2_lib import *
EX = ROOT + "WorkFiles/paperbomb/exact/"
A = json.load(open(OUT+"m2_align.json"))
r = load(REF); H, W = r.shape[:2]
bc = load(BC); frraw = load(FRONT); fr = np.load(OUT+"m2_scan_raw.npy")
ph = {k: np.load(OUT+f"m2_photo_{k}.npy") for k in ("bc", "scan")}
def sample_native(src, p, x0, x1, y0, y1, f):
    ys, xs = np.mgrid[0:(y1-y0)*f, 0:(x1-x0)*f].astype(np.float32)
    u = x0+(xs+0.5)/f; v = y0+(ys+0.5)/f
    return bilinear(src, p[0]*u+p[2]-0.5, p[1]*v+p[3]-0.5)
def ref_smooth(x0, x1, y0, y1, f):
    ys, xs = np.mgrid[0:(y1-y0)*f, 0:(x1-x0)*f].astype(np.float32)
    return bilinear(r, x0+(xs+0.5)/f-0.5, y0+(ys+0.5)/f-0.5)
def inkmask(img):
    L = lab(img); return (L[..., 0] < 55) | (L[..., 1] > 30)
def diffov(a, b):
    ma, mb = inkmask(a), inkmask(b)
    o = np.ones(a.shape, np.float32)
    o[ma & mb] = [0.25, 0.25, 0.25]; o[ma & ~mb] = [1.0, 0.1, 0.6]; o[~ma & mb] = [0.0, 0.6, 1.0]
    return o
def hcat(ps, gap=6):
    h = max(p.shape[0] for p in ps); outs = []
    for i, p in enumerate(ps):
        if p.shape[0] < h: p = np.concatenate([p, np.ones((h-p.shape[0], p.shape[1], 3), np.float32)], 0)
        outs.append(p)
        if i < len(ps)-1: outs.append(np.full((h, gap, 3), 0.5, np.float32))
    return np.concatenate(outs, 1)
def vcat(ps, gap=6):
    w = max(p.shape[1] for p in ps); outs = []
    for i, p in enumerate(ps):
        if p.shape[1] < w: p = np.concatenate([p, np.ones((p.shape[0], w-p.shape[1], 3), np.float32)], 1)
        outs.append(p)
        if i < len(ps)-1: outs.append(np.full((gap, w, 3), 0.5, np.float32))
    return np.concatenate(outs, 0)
def panel(x0, x1, y0, y1, f):
    refn = upscale_nn(r[y0:y1, x0:x1], f)
    bcn = sample_native(bc, A["bc"], x0, x1, y0, y1, f)
    bcp = upscale_nn(ph["bc"][y0:y1, x0:x1], f)
    frn = sample_native(fr, A["scan"], x0, x1, y0, y1, f)
    return [refn, bcn, bcp, diffov(r[y0:y1, x0:x1], ph["bc"][y0:y1, x0:x1]).repeat(f, 0).repeat(f, 1), frn]
# emblem zoom (8x and 4x)
em = (100, 204, 80, 182)
p8e = panel(*em, 8); p4e = panel(*em, 4)
save(vcat([hcat(p8e[:4]), hcat([p4e[0], p4e[4], p4e[1], p4e[3]])]), EX+"m2_emblem_zoom.png")
p8 = panel(*em, 8); save(hcat([p8[0], p8[1]]), OUT+"m2_emblem_ref_vs_bc_x8.png")
save(hcat([p8[2], p8[3], p8[4]]), OUT+"m2_emblem_photo_diff_render_x8.png")
# side by side, same height (2x ref grid), card crop
cx0, cx1, cy0, cy1 = 8, 294, 4, 650
f = 2
sbs = [ref_smooth(cx0, cx1, cy0, cy1, f), sample_native(fr, A["scan"], cx0, cx1, cy0, cy1, f),
       sample_native(bc, A["bc"], cx0, cx1, cy0, cy1, f), sample_native(frraw, A["front"], cx0, cx1, cy0, cy1, f)]
save(hcat(sbs, 10), EX+"m2_side_by_side.png")
# per element zooms
boxes = {"baku": (38, 278, 176, 448, 4), "colTL": (28, 102, 44, 230, 6), "colTR": (200, 274, 42, 228, 6),
         "yakujin": (204, 274, 409, 531, 6), "shungyo": (116, 186, 456, 598, 6), "sealbig": (32, 113, 484, 603, 6),
         "smallseal": (224, 269, 541, 611, 8), "chain": (136, 167, 436, 648, 6), "cTL": (20, 60, 24, 62, 8), "cTR": (244, 284, 24, 62, 8),
         "cBL": (20, 60, 592, 636, 8), "cBR": (244, 284, 592, 636, 8), "ruleTop": (40, 262, 26, 46, 6), "ruleBot": (40, 262, 606, 628, 6),
         "ruleL": (18, 42, 60, 600, 4), "ruleR": (262, 286, 60, 600, 4)}
for n, (x0, x1, y0, y1, f) in boxes.items():
    ps = panel(x0, x1, y0, y1, f)
    if n.startswith("ruleL") or n.startswith("ruleR") or n == "chain":
        save(hcat(ps), OUT+f"m2_zoom_{n}.png")
    elif n.startswith("rule"):
        save(vcat(ps), OUT+f"m2_zoom_{n}.png")
    else:
        save(vcat([hcat(ps[:2]), hcat(ps[2:4])]), OUT+f"m2_zoom_{n}.png")
print("done")
