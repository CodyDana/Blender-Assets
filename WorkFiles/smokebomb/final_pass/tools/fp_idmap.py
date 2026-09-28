"""fp_idmap - build the Ball (numpy only) and paint every exposed stretch in the reference view.
usage: python fp_idmap.py OUTSTEM"""
import sys, time, json, pickle
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
import numpy as np
from wd_png import write_png, read_png
from props_lib import smokebomb_ball as SB
t0 = time.time()
out = sys.argv[1]
ball = SB.Ball(SB.BALL, log=print).build()
print("built", time.time() - t0)
H = 1254
img = np.ones((H, H, 3)); zb = np.full((H, H), np.inf); sid = -np.ones((H, H), int)
rng = np.random.default_rng(3)
cols = rng.uniform(0.15, 1.0, (len(ball.stretches), 3))
info = []
for st in ball.stretches:
    if not st.exposed.any():
        continue
    Q, u, a = SB._exposed_top_points(ball, st, 1)
    xy = SB.build_to_img(Q, ball.spec.outline_mm)
    x = np.round(xy[..., 0]).astype(int); y = np.round(xy[..., 1]).astype(int)
    d = Q[:, 1]
    ok = (x >= 0) & (x < H) & (y >= 0) & (y < H) & (d < 0)
    info.append(dict(k=st.index, key=st.key, pass_=st.pass_name, front_pts=int(ok.sum()), area=round(st.exposed_area_mm2, 1)))
    x, y, d = x[ok], y[ok], d[ok]
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            xx, yy = np.clip(x + dx, 0, H - 1), np.clip(y + dy, 0, H - 1)
            o = np.lexsort((-d,))  # far first so near overwrites
            better = d < zb[yy, xx]
            zb[yy[better], xx[better]] = d[better]
            sid[yy[better], xx[better]] = st.index
for k in np.unique(sid[sid >= 0]):
    img[sid == k] = cols[k]
# edges
e = np.zeros((H, H), bool)
e[:, 1:] |= sid[:, 1:] != sid[:, :-1]; e[1:, :] |= sid[1:, :] != sid[:-1, :]
img[e] = 0
write_png(out + "_id.png", img)
np.save(out + "_sid.npy", sid)
json.dump(info, open(out + "_info.json", "w"), indent=0)
ref = read_png(r"C:/Users/Cody/Desktop/Blender_Projects/References/SmokeBomb/smokebomb.png")[..., :3] / 255.0
write_png(out + "_pair.png", np.concatenate([ref, img], 1)[::2, ::2])
print("front stretches", sum(1 for i in info if i["front_pts"] > 0), "total", len(info), time.time() - t0)
