"""Stage 5: angular profile of the polar unwrap between band and rim -> rib candidates (image angle phi from apex)."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *
pol = np.load(os.path.join(D, 'bh_polar.npy'))   # rows r=0..420 step .5, cols phi -66..66 step .1
rs = np.arange(0, 420, 0.5); phis = np.linspace(-66, 66, 1321)
rexit = np.full(phis.size, np.nan)
for j in range(phis.size):
    c = pol[:, j]; idx = np.where((rs > 150) & (c > 0.8))[0]
    rexit[j] = rs[idx[0]] if len(idx) else np.nan
prof = np.full(phis.size, np.nan); prof_hi = np.full(phis.size, np.nan)
for j in range(phis.size):
    if np.isnan(rexit[j]): continue
    r0, r1 = 135.0, rexit[j] - 45
    if r1 - r0 < 30: continue
    sel = (rs >= r0) & (rs <= r1)
    prof[j] = pol[sel, j].mean()
    prof_hi[j] = np.percentile(pol[sel, j], 80)
np.save(os.path.join(D, 'bh_ribprof.npy'), np.stack([phis, prof, prof_hi, rexit]))
# high-pass
def movavg(a, w):
    k = np.ones(w) / w; m = ~np.isnan(a); a0 = np.where(m, a, 0)
    return np.convolve(a0, k, 'same') / np.maximum(np.convolve(m.astype(float), k, 'same'), 1e-9)
hp = prof - movavg(prof, 31)
dk = -hp   # dark lines
for name, s in (('bright', hp), ('dark', dk)):
    pk = [j for j in range(2, phis.size - 2) if not np.isnan(s[j]) and s[j] == np.nanmax(s[j - 8:j + 9]) and s[j] > 0.006]
    print(name, [(round(phis[j], 1), round(float(s[j]), 4)) for j in pk])
print('rexit samples', [(round(phis[j], 0), rexit[j]) for j in range(0, phis.size, 60)])
