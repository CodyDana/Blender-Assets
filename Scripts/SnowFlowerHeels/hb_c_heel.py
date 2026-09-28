"""Stage C: stiletto, top-lift and ankle strap (local frame, right shoe, mm). Writes r1/cache/heel_r.npz.

    blender -b --factory-startup --python Scripts/SnowFlowerHeels/hb_c_heel.py
"""
import json
import math
import sys
from pathlib import Path

import bpy  # noqa: F401
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hb_camera as HC  # noqa: E402
import hb_common as C  # noqa: E402
import hb_geo as G  # noqa: E402


def superellipse(cu, cv, a, b, n, w, npts=32, rot0=0.0):
    t = np.linspace(0, 2 * np.pi, npts, endpoint=False) + rot0
    c, s = np.cos(t), np.sin(t)
    x = a * np.sign(c) * np.abs(c) ** (2.0 / n)
    y = b * np.sign(s) * np.abs(s) ** (2.0 / n)
    return np.column_stack([cu + x, cv + y, np.full(npts, w)])


def main():
    z = np.load(C.CACHE / "last_r.npz")
    zs = G.zins_sampler(z)
    last = G.Surf(z["last_v"], z["last_q"].tolist())
    cam = json.loads((C.CACHE / "camera.json").read_text())
    cam = HC.Cam(cam["az"], cam["el"], cam["s"], cam["tx"], cam["ty"], cam.get("roll", 0.0))
    cdir, _, _ = cam.basis()
    out = {}
    tu, tv = C.D["toplift_uv"]
    lu, lv = C.D["toplift_size"]
    th = C.D["toplift_h"]
    # ---- top-lift: rounded block (separate black part)
    secs = []
    for w, inset in ((0.0, 0.5), (0.5, 0.0), (th - 0.6, 0.0), (th, 0.3)):
        secs.append(superellipse(tu, tv, lu / 2 - inset, lv / 2 - inset, 6.0, w, 32))
    v, f = G.loft(secs, cap_start=True, cap_end=True)
    out["toplift_v"], out["toplift_f"] = v, np.array([x for x in f if len(x) == 4])
    out["toplift_t"] = np.array([x for x in f if len(x) == 3])
    # ---- stiletto sections
    ws = np.concatenate([np.linspace(th - 0.8, 45, 14), np.linspace(47, 104, 30)])
    secs = []
    for w in ws:
        t = max(0.0, (w - 45.0) / 51.0)
        ub = tu - lu / 2 - 0.3 - 8.5 * t ** 2.2
        tf = max(0.0, (w - 45.0) / 32.0)
        uf = tu + lu / 2 + 0.5 + 19.0 * tf ** 2.6
        b = 4.35 + 0.05 * min(w, 45) / 45 + 13.0 * t ** 2.0
        n = 3.6 - 1.2 * min(t * 1.5, 1.0)
        cu = 0.5 * (ub + uf)
        a = 0.5 * (uf - ub)
        secs.append(superellipse(cu, tv, a, b, n, w, 40, rot0=math.pi / 40))
    secs = np.array(secs)
    # clamp into the sole (embedded 1.2 mm) so the top follows the inclined seat
    lim = zs(secs[..., 0], secs[..., 1]) - C.D["forefoot_sole"] + 1.2
    secs[..., 2] = np.minimum(secs[..., 2], lim)
    # drop sections that collapsed completely
    keep = [0]
    for i in range(1, len(secs)):
        if np.abs(secs[i] - secs[keep[-1]]).max() > 0.2:
            keep.append(i)
    secs = [secs[i] for i in keep]
    v, f = G.loft(secs, cap_start=False, cap_end=True)
    out["stil_v"] = v
    out["stil_f"] = np.array([x for x in f if len(x) == 4])
    out["stil_t"] = np.array([x for x in f if len(x) == 3])
    out["stil_sections"] = np.array(secs)

    # ---- ankle strap: a closed loop hugging the leg (and riding on the counter at the back)
    def near(xy):
        o, d = cam.ray(np.array(xy, dtype=float))
        h = [x for x in last.hits(o, d, max_hits=12) if x[0][2] < 288 and np.dot(x[1], cdir) > 0]
        return h[0][0]
    buckle = near((201.0, 221.0))
    w_back = buckle[2]
    ang_c = []
    sl = last.v[np.abs(last.v[:, 2] - (w_back - 5)) < 2.0]
    ctr = sl[:, :2].mean(0)
    ctr[0] += 12.0            # centre toward the shin so rays from it see the whole loop
    loop = []
    nloop = 96
    for k in range(nloop):
        th_ = 2 * math.pi * k / nloop
        d = np.array([math.cos(th_), math.sin(th_), 0.0])
        # the loop dips 9 mm toward the front of the ankle
        wv = w_back - 9.0 * (0.5 + 0.5 * math.cos(th_))
        o = np.array([ctr[0], ctr[1], wv])
        h = last.hits(o, d, max_hits=3)
        p = h[0][0] if h else o + d * 40
        n = h[0][1] if h else d
        off = C.D["upper_thick"] + 1.2 if p[0] < 30 else 2.0
        loop.append(p + n * off)
    loop = np.array(loop)
    for _ in range(6):
        loop = (np.roll(loop, 1, 0) + 2 * loop + np.roll(loop, -1, 0)) / 4.0
    tang = np.roll(loop, -1, 0) - np.roll(loop, 1, 0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    up = np.array([0, 0, 1.0])
    nrm = np.cross(tang, up)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    # make nrm point outward
    if ((loop[:, :2] - loop[:, :2].mean(0)) * nrm[:, :2]).sum() < 0:
        nrm = -nrm
    binorm = np.cross(nrm, tang)
    half_w, t_in, t_out = 5.0, 0.0, 2.0
    prof = [(-half_w, t_in + 0.3), (-half_w + 0.4, t_out), (half_w - 0.4, t_out), (half_w, t_in + 0.3), (half_w - 0.4, t_in),
            (-half_w + 0.4, t_in)]
    ring = []
    for i in range(nloop):
        ring.append(np.array([loop[i] + binorm[i] * a + nrm[i] * b for a, b in prof]))
    ring = np.array(ring)                       # (nloop, 6, 3)
    sv = ring.reshape(-1, 3)
    np_ = len(prof)
    sf = []
    for i in range(nloop):
        i1 = (i + 1) % nloop
        for j in range(np_):
            j1 = (j + 1) % np_
            sf.append([i * np_ + j, i * np_ + j1, i1 * np_ + j1, i1 * np_ + j])
    out["strap_v"], out["strap_f"] = sv, np.array(sf)
    out["strap_loop"] = loop
    out["strap_frame"] = np.stack([tang, nrm, binorm], 1)
    out["buckle_pt"] = buckle
    np.savez_compressed(C.CACHE / "heel_r.npz", **out)
    print("HEEL_OK buckle", buckle.round(1), "loop w", loop[:, 2].min().round(1), loop[:, 2].max().round(1))


main()
