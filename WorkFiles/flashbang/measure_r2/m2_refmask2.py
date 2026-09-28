import sys, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r2")
from m2_io import *
from collections import deque
W = ROOT + "WorkFiles/flashbang/measure_r2/"
R = load(REFP)[..., :3]
obj = np.load(W + "m2_refmask_raw.npy")
H, Wd = obj.shape


def label(m):
    lab = np.zeros(m.shape, np.int32); n = 0; h, w = m.shape; flat = m.ravel(); L = lab.ravel()
    sizes = [0]
    for s in np.flatnonzero(flat):
        if L[s]:
            continue
        n += 1; L[s] = n; q = deque([s]); cnt = 0
        while q:
            p = q.popleft(); cnt += 1; y, x = divmod(p, w)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w:
                    pp = yy * w + xx
                    if flat[pp] and not L[pp]:
                        L[pp] = n; q.append(pp)
        sizes.append(cnt)
    return lab, np.array(sizes)


# fill small background holes (< 600 px) inside the object; keep the large ones (ring interior, gaps)
lab, sz = label(~obj)
small = np.isin(lab, np.flatnonzero(sz < 600)) & (lab > 0)
obj = obj | small
# remove small object specks
lab, sz = label(obj)
obj = np.isin(lab, np.flatnonzero(sz > 3000)) & (lab > 0)
# per view: cut the floor contact/shadow below each bottom
VB = {"v1": (40, 345), "v2": (345, 615), "v3": (615, 950), "v4": (950, 1240)}
info = {}
for v, (x0, x1) in VB.items():
    m = obj[:, x0:x1]
    # cap x-span at y=690
    xs = np.flatnonzero(m[690]); cx0, cx1 = xs.min(), xs.max()
    capw = cx1 - cx0 + 1
    bot = 690
    for y in range(690, H):
        if m[y, cx0:cx1 + 1].mean() > 0.9:
            bot = y
    m[bot + 1:] = False
    ys = np.flatnonzero(m.any(1))
    # body width: rows 560-575 (between row C and cap? use the band just above the cap)
    widths = {}
    for y in (250, 380, 480, 600, 660, 700):
        xx = np.flatnonzero(m[y]); widths[y] = [int(xx.min() + x0), int(xx.max() + x0)]
    info[v] = {"bot": int(bot), "top": int(ys.min()), "cap_x": [int(cx0 + x0), int(cx1 + x0)], "cap_cx": float((cx0 + cx1) / 2 + x0),
               "capw": int(capw), "rows": widths}
    obj[:, x0:x1] = m
obj[:, :40] = False; obj[:, 1240:] = False
print("M2INFO", json.dumps(info))
np.save(W + "m2_refmask.npy", obj)
ov = R[:H].copy(); e = obj ^ (np.roll(obj, 1, 0) & np.roll(obj, -1, 0) & np.roll(obj, 1, 1) & np.roll(obj, -1, 1))
ov[e] = [255, 40, 40]
save(W + "m2_refmask_edge.png", ov)
json.dump(info, open(W + "m2_refinfo.json", "w"), indent=1)
