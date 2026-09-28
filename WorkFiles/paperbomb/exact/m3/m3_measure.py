import sys, json; sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/m3")
from m3_lib import *
PPMM = 3.917
A = json.load(open(OUT+"m3_align.json"))
r = load(REF); H, W = r.shape[:2]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
bc = load(BC); fr = np.load(OUT+"m3_front_expnorm.npy"); sc = np.load(OUT+"m3_scan_raw.npy")
def photo(src, p, sig, box):
    s = box_blur(src, box) if box > 1 else src
    w = bilinear(s, p[0]*(xx+0.5)+p[2]-0.5, p[1]*(yy+0.5)+p[3]-0.5)
    return gauss_blur(w, sig)
imgs = {"ref": r,
        "bc": photo(bc, A["bc"], A["bc_sigma"], 3),
        "bc_nopsf": photo(bc, A["bc"], 0.0, 3),
        "front": photo(fr, A["front"], A["front_sigma"], 1),
        "scan": photo(sc, A["scan"], A["scan_sigma"], 1)}
for k, v in imgs.items(): np.save(OUT+f"m3_photo_{k}.npy", v.astype(np.float32))
card = (xx > 16) & (xx < 286) & (yy > 14) & (yy < 646)
def endmembers(L):
    paper = np.median(L[card & (L[..., 0] > 80) & (np.abs(L[..., 1]) < 15)], 0)
    black = np.median(L[card & (L[..., 0] < 25)], 0)
    red = np.median(L[card & (L[..., 1] > 45)], 0)
    return paper, black, red
def soft(L, em):
    p, k, rd = em
    kr = np.clip((L[..., 1]-p[1])/(rd[1]-p[1]), 0, 1)
    kb = np.clip((p[0]-L[..., 0])/(p[0]-k[0]), 0, 1)
    thr_a = (p[1]+rd[1])/2
    kb = np.where(L[..., 1] > thr_a, 0.0, kb)
    return kb, kr
labs = {k: lab(v) for k, v in imgs.items()}
ems = {k: endmembers(v) for k, v in labs.items()}
softs = {k: soft(labs[k], ems[k]) for k in imgs}
def box(x0, x1, y0, y1): return (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
corners = {"corner_TL": box(22, 52, 26, 57), "corner_TR": box(250, 282, 26, 57),
           "corner_BL": box(22, 54, 597, 632), "corner_BR": box(248, 282, 597, 632)}
chain = box(142, 161, 438, 462) | box(142, 161, 589, 646)
seal_big = box(34, 111, 486, 601); small = box(226, 267, 543, 609)
yake = box(206, 273, 411, 529)
bakuC = box(38, 277, 213, 426) & ~yake
ring = box(35, 268, 178, 447)
band = (box(22, 37, 26, 632) | box(268, 282, 26, 632) | box(22, 282, 28, 43) | box(22, 282, 609, 632))
rules = band & ~corners["corner_TL"] & ~corners["corner_TR"] & ~corners["corner_BL"] & ~corners["corner_BR"] & ~chain & ~seal_big & ~small
E = {"emblem": (box(100, 203, 80, 181), ("b",)),
     "centre_baku": (bakuC, ("b",)),
     "col_TL": (box(30, 100, 46, 228), ("b",)),
     "col_TR": (box(203, 271, 44, 226), ("b",)),
     "col_BR_yakujin": (yake, ("b",)),
     "col_BC_shungyo": (box(118, 184, 458, 596) & ~chain, ("b",)),
     "seal_big": (seal_big, ("r", "b")),
     "small_seal": (small, ("r", "b")),
     "ring": (ring & ~box(206, 273, 411, 529), ("r",)),
     "rules": (rules, ("r", "b")),
     "chain": (chain, ("r", "b"))}
for k, v in corners.items(): E[k] = (v, ("r", "b"))
def erode(m):
    o = m.copy(); o[1:] &= m[:-1]; o[:-1] &= m[1:]; o[:, 1:] &= m[:, :-1]; o[:, :-1] &= m[:, 1:]; return o
def dilate(m, n=1):
    o = m.copy()
    for _ in range(n):
        q = o.copy(); q[1:] |= o[:-1]; q[:-1] |= o[1:]; q[:, 1:] |= o[:, :-1]; q[:, :-1] |= o[:, 1:]; o = q
    return o
def up4(a):
    h, w = a.shape; ys, xs = np.mgrid[0:h*4, 0:w*4].astype(np.float32)
    return bilinear(a, (xs+0.5)/4-0.5, (ys+0.5)/4-0.5)
def edge_pts(m):
    b = m & ~erode(m); ys, xs = np.nonzero(b); return np.stack([xs, ys], 1).astype(np.float32)
def nn_dist(a, b):
    out = np.empty(len(a), np.float32)
    for i in range(0, len(a), 2000):
        d = ((a[i:i+2000, None, :]-b[None, :, :])**2).sum(-1); out[i:i+2000] = np.sqrt(d.min(1))
    return out
def score(key, name):
    region, chans = E[name]
    ys, xs = np.nonzero(region); y0, y1, x0, x1 = ys.min(), ys.max()+1, xs.min(), xs.max()+1
    res = {}
    for ch in chans:
        ci = 0 if ch == "b" else 1
        sr = np.where(region, softs["ref"][ci], 0)[y0:y1, x0:x1]; so = np.where(region, softs[key][ci], 0)[y0:y1, x0:x1]
        mr = sr >= 0.5; mo = so >= 0.5
        if mr.sum() < 5: continue
        iou = (mr & mo).sum()/max(1, (mr | mo).sum())
        ur = up4(sr) >= 0.5; uo = up4(so) >= 0.5
        pr = edge_pts(ur); po = edge_pts(uo)
        d1 = nn_dist(pr, po); d2 = nn_dist(po, pr); d = np.concatenate([d1, d2])/4/PPMM
        iou4 = (ur & uo).sum()/max(1, (ur | uo).sum())
        # ink colour: core pixels (soft>0.85) in each image
        Lr_ = labs["ref"][y0:y1, x0:x1]; Lo_ = labs[key][y0:y1, x0:x1]
        cr = np.where(region[y0:y1, x0:x1], softs["ref"][ci][y0:y1, x0:x1], 0) > 0.85
        co = np.where(region[y0:y1, x0:x1], softs[key][ci][y0:y1, x0:x1], 0) > 0.85
        if cr.sum() > 3 and co.sum() > 3:
            medr = np.median(Lr_[cr], 0); medo = np.median(Lo_[co], 0)
            dec = float(de2000(medr, medo))
        else: medr = medo = np.zeros(3); dec = float('nan')
        both = mr & mo
        pix = de2000(Lr_[both], Lo_[both]) if both.sum() else np.array([np.nan])
        res[ch] = {"iou": round(float(iou), 4), "iou_4x": round(float(iou4), 4), "n_ref": int(mr.sum()), "n_ours": int(mo.sum()),
                   "edge_mean_mm": round(float(d.mean()), 4), "edge_p95_mm": round(float(np.percentile(d, 95)), 4), "edge_max_mm": round(float(d.max()), 4),
                   "de_core_median_colour": round(dec, 3), "ref_core_lab": [round(float(v), 2) for v in medr], "ours_core_lab": [round(float(v), 2) for v in medo],
                   "de_pixel_median": round(float(np.median(pix)), 3), "de_pixel_mean": round(float(np.mean(pix)), 3)}
    # all-pixels dE over region
    allde = de2000(labs["ref"][region], labs[key][region])
    res["region_de_mean"] = round(float(allde.mean()), 3); res["region_de_p90"] = round(float(np.percentile(allde, 90)), 3)
    return res
out = {"align": A, "endmembers": {k: [[round(float(x), 2) for x in e] for e in v] for k, v in ems.items()}}
allink = np.zeros((H, W), bool)
for k in ("ref",): allink |= (softs[k][0] > 0.08) | (softs[k][1] > 0.08)
paper_reg = card & ~dilate(allink, 2) & (xx > 20) & (xx < 282) & (yy > 18) & (yy < 640)
for key in ("bc", "bc_nopsf", "front", "scan"):
    o = {}
    for name in E: o[name] = score(key, name)
    pr = np.median(labs["ref"][paper_reg], 0); po = np.median(labs[key][paper_reg], 0)
    pd = de2000(labs["ref"][paper_reg], labs[key][paper_reg])
    o["paper"] = {"de_median_colour": round(float(de2000(pr, po)), 3), "ref_lab": pr.round(2).tolist(), "ours_lab": po.round(2).tolist(),
                  "de_pixel_median": round(float(np.median(pd)), 3), "de_pixel_mean": round(float(pd.mean()), 3), "de_pixel_p90": round(float(np.percentile(pd, 90)), 3),
                  "ref_L_std": round(float(labs["ref"][paper_reg][:, 0].std()), 3), "ours_L_std": round(float(labs[key][paper_reg][:, 0].std()), 3)}
    wc = de2000(labs["ref"][card], labs[key][card])
    o["whole_card"] = {"de_mean": round(float(wc.mean()), 3), "de_p90": round(float(np.percentile(wc, 90)), 3)}
    out[key] = o
json.dump(out, open(OUT+"m3_scores.json", "w"), indent=1, ensure_ascii=False)
for key in ("bc", "scan"):
    print("==", key)
    for n, v in out[key].items():
        print(n, json.dumps({c: ({kk: vv[kk] for kk in ("iou", "iou_4x", "edge_mean_mm", "edge_p95_mm", "de_core_median_colour", "de_pixel_median")} if isinstance(vv, dict) else vv) for c, vv in v.items()}, ensure_ascii=False))
np.save(OUT+"m3_regions.npy", np.stack([E[n][0] for n in E]))
json.dump(list(E.keys()), open(OUT+"m3_region_names.json", "w"))
