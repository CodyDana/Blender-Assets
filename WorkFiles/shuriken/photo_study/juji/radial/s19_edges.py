"""Final per-arm edge estimates along the arm normals.

Reference frame per arm: watershed axis (arm_ws_<arm>.npz). Reference edges: closed (r=5) smoothed
watershed mask, run containing the arm midline.
Per side:
  E50  : half-contrast crossing between the lid colour B (28..40 px outside the reference edge) and the
         object colour O (6..14 px inside), approached from outside (sides without the black band).
  Up-facing sides of the horizontal arms (image -y; the black-band sides) additionally:
    Eincl: outer boundary of the near-black band (lum crossing halfway between lid level and band level,
           approached from outside)  -> band counted as metal.
    Eexcl: inner boundary of the band (lum crossing halfway between band level and the metal just inside)
           -> band counted as cast shadow.  Where there is no band (min lum >= 0.10) Eincl = Eexcl = E50.
Outputs edges_<arm>.npz with arrays over stations S.
"""
import sys, os, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/radial")
import numpy as np
import jlib

a = jlib.load_image()
H, W, _ = a.shape
ab = jlib.gblur(a, 0.7)
m = np.load(os.path.join(jlib.OUT, "mask_final_ws.npy")).astype(bool)
m = jlib.closing(m, 5)
m, _ = jlib.fill_holes(m)
np.save(os.path.join(jlib.OUT, "mask_ref.npy"), m)
mf = jlib.gblur(m.astype(np.float32), 1.0)
names = ["right", "top", "left", "bottom"]
UP_SIDE = {"right": "L", "left": "R"}   # arm side whose outward normal points to image -y
BAND_T = 0.10


def crossing_from_outside(q, f, level, qmax=None):
    """q ascending = outward. Return the first q (scanning from large q to small) where f >= level."""
    idx = np.arange(len(q))[::-1]
    if qmax is not None:
        idx = idx[q[idx] <= qmax]
    prev = None
    for i in idx:
        if f[i] >= level:
            if prev is None:
                return q[i]
            fa, fb = f[prev], f[i]
            return q[prev] + (level - fa) / (fb - fa) * (q[i] - q[prev])
        prev = i
    return np.nan


allout = {}
for nme in names:
    d = np.load(os.path.join(jlib.OUT, "arm_ws_%s.npz" % nme))
    u, n, origin = d["u"], d["n"], d["origin"]
    prof = d["prof"]
    R = prof[np.isfinite(prof[:, 1]), 0].max()
    S = np.arange(40, int(R) + 12, 1.0)
    T = np.arange(-150, 150.01, 0.5)
    acc = np.zeros((len(S), len(T), 3))
    macc = np.zeros((len(S), len(T)))
    for ds in (-2, -1, 0, 1, 2):
        X = origin[0] + (S[:, None] + ds) * u[0] + T[None, :] * n[0]
        Y = origin[1] + (S[:, None] + ds) * u[1] + T[None, :] * n[1]
        acc += jlib.bilinear(ab, X, Y)
    X = origin[0] + S[:, None] * u[0] + T[None, :] * n[0]
    Y = origin[1] + S[:, None] * u[1] + T[None, :] * n[1]
    ok = (X >= 0) & (X <= W - 1) & (Y >= 0) & (Y <= H - 1)
    Mv = jlib.bilinear(mf, X, Y); Mv[~ok] = 0
    C = acc / 5
    L = C.mean(2)
    out = {k: np.full(len(S), np.nan) for k in ("refL", "refR", "E50L", "E50R", "EinclL", "EinclR", "EexclL", "EexclR", "bandw", "clipL", "clipR")}
    prev_mid = 0.0
    for i, s in enumerate(S):
        ins = Mv[i] > 0.5
        if not ins.any():
            continue
        i0 = int(np.argmin(np.abs(T - prev_mid)))
        if not ins[i0]:
            idx = np.nonzero(ins)[0]
            i0 = idx[np.argmin(np.abs(idx - i0))]
        j = i0
        while j + 1 < len(T) and ins[j + 1]:
            j += 1
        k = i0
        while k - 1 >= 0 and ins[k - 1]:
            k -= 1
        tl, tr = T[j], T[k]
        out["refL"][i], out["refR"][i] = tl, tr
        prev_mid = 0.5 * (tl + tr)
        for side, te in (("L", tl), ("R", tr)):
            sg = 1.0 if side == "L" else -1.0
            q = sg * (T - prev_mid)       # outward coordinate from the midline
            order = np.argsort(q)
            q = q[order]; col = C[i][order]; Lq = L[i][order]; okq = ok[i][order]
            qe = sg * (te - prev_mid)
            out["clip" + side][i] = float(not okq[(q > qe) & (q < qe + 40)].all())
            B = np.median(col[(q >= qe + 28) & (q <= qe + 40)], 0)
            O = np.median(col[(q >= qe - 14) & (q <= qe - 6)], 0)
            v = O - B
            den = float(v @ v)
            if den > 0.03 ** 2:
                f = (col - B) @ v / den
                qq = crossing_from_outside(q, f, 0.5, qmax=qe + 40)
                if np.isfinite(qq):
                    out["E50" + side][i] = prev_mid + sg * qq
            if UP_SIDE.get(nme) == side:
                Bl = float(np.median(Lq[(q >= qe + 30) & (q <= qe + 45)]))
                win = (q >= qe - 40) & (q <= qe + 10)
                qi = np.nonzero(win)[0]
                kmin = qi[np.argmin(Lq[qi])]
                Lmin = Lq[kmin]
                if Lmin < BAND_T:
                    a0 = kmin
                    while a0 - 1 >= 0 and Lq[a0 - 1] < BAND_T:
                        a0 -= 1
                    b0 = kmin
                    while b0 + 1 < len(q) and Lq[b0 + 1] < BAND_T:
                        b0 += 1
                    Lband = float(np.median(Lq[a0:b0 + 1]))
                    # outer boundary (from outside)
                    half_o = 0.5 * (Bl + Lband)
                    fo = -(Lq - half_o)  # >=0 where darker than half
                    qo = crossing_from_outside(q, fo, 0.0, qmax=qe + 40)
                    # inner boundary
                    inner = Lq[max(0, a0 - 20):max(1, a0 - 6)]
                    Lobj = float(np.median(inner)) if len(inner) else np.nan
                    qi_ = np.nan
                    if np.isfinite(Lobj) and Lobj - Lband > 0.04:
                        half_i = 0.5 * (Lobj + Lband)
                        kk = a0
                        while kk - 1 >= 0 and Lq[kk - 1] < half_i:
                            kk -= 1
                        if kk - 1 >= 0:
                            qi_ = q[kk - 1] + (half_i - Lq[kk - 1]) / (Lq[kk] - Lq[kk - 1]) * (q[kk] - q[kk - 1])
                    if np.isfinite(qo):
                        out["Eincl" + side][i] = prev_mid + sg * qo
                    if np.isfinite(qi_):
                        out["Eexcl" + side][i] = prev_mid + sg * qi_
                        if np.isfinite(qo):
                            out["bandw"][i] = qo - qi_
                else:
                    # no band: single half-contrast edge in luminance between lid and the dark metal at the edge
                    Onear = float(np.median(Lq[max(0, kmin - 12):kmin + 3]))
                    half = 0.5 * (Bl + Onear)
                    fo = -(Lq - half)
                    qo = crossing_from_outside(q, fo, 0.0, qmax=qe + 40)
                    if np.isfinite(qo):
                        out["Eincl" + side][i] = out["Eexcl" + side][i] = prev_mid + sg * qo
                        out["bandw"][i] = 0.0
    np.savez(os.path.join(jlib.OUT, "edges_%s.npz" % nme), S=S, R=R, u=u, n=n, origin=origin, **out)
    allout[nme] = out
    # quick table
    print("==", nme, "R=%.1f" % R)
    for s in (100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 630):
        i = int(np.argmin(np.abs(S - s)))
        o = out
        print(" s%4d ref %6.1f %6.1f | E50 %6.1f %6.1f | incl %6.1f %6.1f | excl %6.1f %6.1f | band %5.1f" % (
            s, o["refL"][i], o["refR"][i], o["E50L"][i], o["E50R"][i], o["EinclL"][i], o["EinclR"][i],
            o["EexclL"][i], o["EexclR"][i], o["bandw"][i]))
