"""Silhouette extraction for the two shoe views (writes metro_mask_A/B.npy, metro_sil.json, metro_sil_viz.png to SP).
Needs SP/metro_ref.npy = the reference as HxWx3 float (made by a one-off bpy load; see metro_imgio.py)."""
import sys, numpy as np, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlowerHeels")
import metro_png as png, metro_common as mc
SP = r"C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/70fec35b-8f87-4dbe-ba33-6e5ba8c5d846/scratchpad"
a = np.load(SP + "/metro_ref.npy"); mn = a.mean(-1)
gy = np.abs(np.diff(mn, axis=0, append=mn[-1:])); gx = np.abs(np.diff(mn, axis=1, append=mn[:, -1:]))
g = np.maximum(np.maximum(gx, gy), np.maximum(mc.shift(gx, 0, 1), mc.shift(gy, 1, 0)))
bgc = (mn > 0.35) & (g < 0.035)
lb, sb = mc.label(bgc); border = set(np.unique(np.concatenate([lb[0], lb[-1], lb[:, 0], lb[:, -1]]))) - {0}
bg = np.isin(lb, list(border))
reg = mc.fill_holes(~bg)
dk = mn < 0.30; db = np.zeros_like(dk)
for k in range(1, 26): db |= mc.shift(dk, -k, 0)
reg = reg & ~((mn > 0.40) & (g < 0.08) & ~mc.dilate(dk, 1) & ~db & (np.arange(mn.shape[0])[:, None] > 700)); reg = mc.dilate(mc.erode(reg, 2), 2); reg = mc.fill_holes(mc.erode(mc.dilate(reg, 3), 3))
lab, s = mc.label(reg); order = np.argsort(s)[::-1]
print("sizes", s[order[:4]])
out = {}
viz = a.copy()
for name, li in zip(["A", "B"], order[:2]):
    m = lab == li; ys, xs = np.nonzero(m)
    if name == "A" and xs.mean() > 600: name = "B"
    elif name == "B" and xs.mean() < 600: name = "A"
    b = mc.trace_boundary(m); r = mc.rdp(b, 0.75)
    print(name, "area", m.sum(), "bbox", xs.min(), xs.max(), ys.min(), ys.max(), "boundary", len(b), "rdp", len(r))
    out[name] = {"area_px": int(m.sum()), "bbox_xyxy": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], "outline_xy": r.round(1).tolist()}
    np.save(SP + "/metro_mask_%s.npy" % name, m)
    mc.draw_poly(viz, r, (1, 0, 0), True)
json.dump(out, open(SP + "/metro_sil.json", "w"))
png.write(SP + "/metro_sil_viz.png", viz)
