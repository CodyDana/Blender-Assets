"""Stage 17: numeric rows - local scales, rim face profile, rib width, weave periods, band rho/width, brightness vs theta."""
import sys, os, numpy as np, json
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *
c = load('bh_s07_joint.json')['2.6']; d = 2.6
H, e, f, u0, v0, roll = c['H'], np.radians(c['e_deg']), c['f'], c['u0'], c['v0'], np.radians(c['roll_deg'])
pr = lambda P: project(np.asarray(P, float), e, d, f, u0, v0, roll)
im = load_srgb(); Lm = lum(im); out = {}
def cone(t, r): t = np.radians(t); return [r * np.sin(t), -r * np.cos(t), H * (1 - r)]
def scale_at(t, r):
    p0 = pr([cone(t, r)])[0]; p1 = pr([cone(t + 0.1, r)])[0]
    return float(np.hypot(*(p1 - p0)) / (np.radians(0.1) * r))   # px per unit length along the circle
for nm, (t, r) in dict(rim_front=(0, 1.0), band_front=(0, 0.36), crown=(0, 0.11), rim_right60=(60, 1.0), rim_left_m60=(-60, 1.0)).items():
    out['scale_px_per_R_' + nm] = scale_at(t, r)
print({k: round(v, 1) for k, v in out.items()})
# slant-direction scale at front rho 0.8
p0 = pr([cone(0, 0.8)])[0]; p1 = pr([cone(0, 0.81)])[0]
sl = np.hypot(*(p1 - p0)) / (0.01 * np.sqrt(1 + H * H)); out['scale_px_per_R_slant_front_rho0.8'] = float(sl)
p0 = pr([cone(0, 0.8)])[0]; p1 = pr([cone(0.1, 0.8)])[0]; out['scale_px_per_R_circ_front_rho0.8'] = float(np.hypot(*(p1 - p0)) / (np.radians(0.1) * 0.8))
print('slant scale front rho .8', sl, 'circ', out['scale_px_per_R_circ_front_rho0.8'])
# ---- rim face vertical profiles at front columns between lashings
cols = [300, 310, 320, 330, 340, 350, 360, 420, 430, 440, 200, 210, 220]
prof = []
for x in cols:
    col = Lm[380:440, x]
    ybot = None
    for y in range(439, 380, -1):
        if Lm[y, x] < 0.58: ybot = y + (Lm[y + 1, x] - 0.58) / (Lm[y + 1, x] - Lm[y, x]) if Lm[y+1,x] != Lm[y,x] else y; break
    seg = Lm[395:int(ybot) - 3, x]; yg = 395 + int(np.argmin(seg))
    prof.append((x, round(float(ybot), 2), yg, round(float(Lm[yg, x]), 3)))
print('rim face (x, bottom_outline, groove_row, groove_lum)', prof)
out['rim_face_profiles'] = prof
# ---- rib cross profiles at theta 7.6 (front primary rib), rho 0.7..0.9: FWHM in px, convert to R
S = np.load(os.path.join(D, 'bh_cone_theta_rho.npy')); th = np.arange(-100, 100.001, 0.1); rho = np.arange(0.10, 1.001, 0.0025)
for t0 in (7.6, -23.5, -54.5):
    rows = (rho >= 0.65) & (rho <= 0.9)
    j = np.argmin(np.abs(th - t0)); seg = S[rows][:, j - 25:j + 26]
    m = seg.mean(0); print('rib', t0, 'cross profile (0.1 deg steps)', np.round(m, 3).tolist())
# ---- weave periods in a clean bay: theta -20..5 rho 0.62..0.9 (autocorrelation)
rows = (rho >= 0.62) & (rho <= 0.90); colsel = (th >= -19) & (th <= 4)
P = S[np.ix_(rows, colsel)]; P = P - P.mean()
# along rho (circumferential strands): average column autocorr
def acorr(a, axis):
    a = a - a.mean(axis=axis, keepdims=True)
    n = a.shape[axis]; F = np.fft.rfft(a, n=2 * n, axis=axis); ac = np.fft.irfft(F * np.conj(F), axis=axis)
    ac = ac.take(range(n), axis=axis); ac = ac.mean(axis=1 - axis); return ac / ac[0]
acr = acorr(P, 0); act = acorr(P, 1)
print('acorr along rho (lag in 0.0025 rho):', np.round(acr[:40], 3).tolist())
print('acorr along theta (lag in 0.1 deg):', np.round(act[:120:2], 3).tolist())
# spectra
spr = np.abs(np.fft.rfft(P - P.mean(0), axis=0)).mean(1); fr = np.fft.rfftfreq(P.shape[0], d=0.0025)
k = np.argsort(spr[3:])[::-1][:6] + 3; print('rho spectrum peaks: period in rho', [(round(1 / fr[i], 4), round(float(spr[i]), 2)) for i in k])
spt = np.abs(np.fft.rfft(P - P.mean(1, keepdims=True), axis=1)).mean(0); ft = np.fft.rfftfreq(P.shape[1], d=0.1)
k = np.argsort(spt[3:])[::-1][:8] + 3; print('theta spectrum peaks: period deg', [(round(1 / ft[i], 3), round(float(spt[i]), 2)) for i in k])
dump('bh_s17_measure.json', out)
