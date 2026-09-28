import sys, json; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/measure_sword_lm1")
from mlm1_lib import *
ref = np.load(D+"mlm1_ref_rgb.npy"); H, W = ref.shape[:2]
lum = ref.mean(2); sat = ref.max(2)-ref.min(2)
rfg = (lum < 0.9) | (sat > 0.08)
MMPP = 1256.3/1205.0
views = {"front": ("front", 215, 420), "back": ("back", 600, 800), "side_px": ("side_px", 420, 600), "side_mx": ("side_mx", 420, 600)}
regions = {"pommel": (10, 45), "grip": (45, 255), "collar_guard": (255, 335), "blade_upper": (335, 700), "blade_lower": (700, 1100), "tip": (1100, 1216)}
out = {}
def runs(row, ax):
    c = np.where(row)[0]
    if not len(c): return None
    # run containing / nearest to ax, merging gaps <= 2 px
    splits = np.where(np.diff(c) > 3)[0]
    segs = np.split(c, splits+1)
    best = min(segs, key=lambda s: 0 if s[0] <= ax <= s[-1] else min(abs(s[0]-ax), abs(s[-1]-ax)))
    return best[0], best[-1]+1
for key, (fn, x0, x1) in views.items():
    a4 = load(D+"mlm1_ours_"+fn+".png")
    a1 = resize(a4, a4.shape[0]//4, a4.shape[1]//4)
    oal = a1[..., 3]; ocol = over(a1)
    h1, w1 = oal.shape
    # our frame: centre px (w1/2, h1/2) <-> X'=0, Z'=cz ; pommel top at row h1/2 - 628.15/MMPP
    top_ours = h1/2 - 628.15/MMPP
    dy = int(round(10 - top_ours))    # put pommel top on sheet row 10 (length is matched by construction)
    # horizontal: search shift maximising IoU on blade rows 340..1200
    best = None
    rm = rfg[:, x0:x1]
    for cx in range(x0 + 30, x1 - 30):
        canvas = np.zeros((H, x1-x0), bool)
        ox = cx - x0 - w1//2
        for_rows = slice(max(0, dy), min(H, dy+h1))
        src = oal[for_rows.start-dy:for_rows.stop-dy] > 0.5
        c0 = max(0, ox); c1 = min(x1-x0, ox+w1)
        canvas[for_rows, c0:c1] = src[:, c0-ox:c1-ox]
        m = slice(340, 1200)
        iou = (canvas[m] & rm[m]).sum() / max(1, (canvas[m] | rm[m]).sum())
        if best is None or iou > best[0]: best = (iou, cx, canvas)
    iou, cx, om = best
    axis = cx - x0
    res = {"axis_col": cx, "row_shift": dy, "blade_iou": round(float(iou), 4), "regions": {}}
    for rn, (r0, r1) in regions.items():
        dl, dr, dw, n, ious = [], [], [], 0, []
        for r in range(r0, r1):
            ro = runs(om[r], axis); rr = runs(rm[r], axis)
            if ro is None or rr is None: continue
            dl.append(ro[0]-rr[0]); dr.append(ro[1]-rr[1]); dw.append((ro[1]-ro[0])-(rr[1]-rr[0]))
        sl = slice(r0, r1)
        res["regions"][rn] = {"mean_width_err_mm": round(float(np.mean(dw))*MMPP, 1) if dw else None,
                              "mean_abs_width_err_mm": round(float(np.mean(np.abs(dw)))*MMPP, 1) if dw else None,
                              "left_edge_err_mm": round(float(np.mean(dl))*MMPP, 1) if dl else None,
                              "right_edge_err_mm": round(float(np.mean(dr))*MMPP, 1) if dr else None,
                              "iou": round(float((om[sl] & rm[sl]).sum() / max(1, (om[sl] | rm[sl]).sum())), 3)}
    out[key] = res
    # per-row profile for tip/sweep: spine edge col and edge col
    prof = []
    for r in range(330, 1216, 20):
        ro = runs(om[r], axis); rr = runs(rm[r], axis)
        prof.append([r, ro, rr])
    res["profile_rows_ours_ref"] = [[p[0], [int(v) for v in p[1]] if p[1] else None, [int(v) for v in p[2]] if p[2] else None] for p in prof]
    # overlay image ref | ours | overlay (ours=blue, ref=red), sheet scale
    oc = np.ones((H, x1-x0, 3), np.float32)*0.985
    ox = cx - x0 - w1//2
    rs = slice(max(0, dy), min(H, dy+h1)); c0 = max(0, ox); c1 = min(x1-x0, ox+w1)
    oc[rs, c0:c1] = ocol[rs.start-dy:rs.stop-dy, c0-ox:c1-ox]
    ov = np.ones((H, x1-x0, 3), np.float32)
    ov[rm] = [0.9, 0.2, 0.2]; ov[om] = [0.2, 0.4, 0.95]; ov[om & rm] = [0.35, 0.35, 0.35]
    np.save(D+"mlm1_sheet_"+key+".npy", oc)
    np.save(D+"mlm1_mask_"+key+".npy", om)
    savepng(D+"mlm1_cmp_"+key+".png", np.concatenate([ref[:, x0:x1], oc, ov], 1))
json.dump(out, open(D+"mlm1_metrics.json", "w"), indent=1)
for k, v in out.items():
    print(k, v["axis_col"], v["row_shift"], v["blade_iou"])
    for rn, m in v["regions"].items(): print("   ", rn, m)
