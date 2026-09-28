"""Stage 21: weave spectrum in band-interior patches (FFT of log-lum, Hann window).
Reports the strongest spectral peaks: thread pitch (px) and thread-row orientation, plus modulation depth."""
import sys, os, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/reference_metrology")
import numpy as np
import sb_lib as L

rgb = L.load_srgb(); Y = L.lum(rgb).astype(np.float64)
lin = L.srgb_to_lin(Y)
Yl = np.log(np.clip(Y, 0.01, 1))
PATCH = {"A1": (620, 745), "A2": (520, 690), "A3": (760, 800), "B1": (900, 470), "B2": (980, 465), "C1": (330, 810),
         "C2": (440, 800), "X1": (985, 620), "U1": (720, 385), "rim1": (330, 325), "E1": (820, 975), "W1": (930, 728)}
N = 64
han = np.outer(np.hanning(N), np.hanning(N))
fy = np.fft.fftfreq(N)[:, None]; fx = np.fft.fftfreq(N)[None, :]
fr = np.sqrt(fx ** 2 + fy ** 2)
out = {}
acc = np.zeros((N, N))
for k, (cx, cy) in PATCH.items():
    n = 32 if k == "W1" else N
    h = np.outer(np.hanning(n), np.hanning(n))
    p = Yl[cy - n // 2:cy + n // 2, cx - n // 2:cx + n // 2]
    p = p - p.mean()
    F = np.abs(np.fft.fft2(p * h)) ** 2
    f_y = np.fft.fftfreq(n)[:, None]; f_x = np.fft.fftfreq(n)[None, :]
    f_r = np.sqrt(f_x ** 2 + f_y ** 2)
    F[f_r < 1.5 / n * 2] = 0      # drop shading
    F[f_r > 0.45] = 0
    if n == N:
        acc += F / F.sum()
    # peaks: local maxima in half plane
    Fs = F.copy()
    peaks = []
    for _ in range(6):
        i = np.unravel_index(np.argmax(Fs), Fs.shape)
        fyy, fxx = np.fft.fftfreq(n)[i[0]], np.fft.fftfreq(n)[i[1]]
        f = np.hypot(fxx, fyy)
        # orientation of the wave vector (image, CCW from +x, y up); thread ROWS run perpendicular
        ang = np.degrees(np.arctan2(-fyy, fxx)) % 180
        peaks.append(dict(period_px=round(float(1 / f), 2), wavevec_deg=round(float(ang), 1),
                          rows_deg=round(float((ang + 90) % 180), 1), rel_power=round(float(Fs[i] / F.sum()), 4)))
        # suppress the peak and its mirror
        for (a_, b_) in ((i[0], i[1]), ((-i[0]) % n, (-i[1]) % n)):
            Fs[max(0, a_ - 1):a_ + 2, max(0, b_ - 1):b_ + 2] = 0
    # modulation depth: std of high-pass log-lum (sigma 1.5 vs 6 band), and linear contrast
    hp = (L.gauss_blur(Yl.astype(np.float32), 0.7) - L.gauss_blur(Yl.astype(np.float32), 4))[cy - n // 2:cy + n // 2, cx - n // 2:cx + n // 2]
    lp = lin[cy - n // 2:cy + n // 2, cx - n // 2:cx + n // 2]
    out[k] = dict(centre=[cx, cy], peaks=peaks, hp_log_std=round(float(hp.std()), 4),
                  lin_cv=round(float(lp.std() / lp.mean()), 3), lin_p90_p10=round(float(np.percentile(lp, 90) / np.percentile(lp, 10)), 2))
    print(k, "hpstd", out[k]['hp_log_std'], "cv", out[k]['lin_cv'], "p90/p10", out[k]['lin_p90_p10'])
    for pk in peaks:
        print("    ", pk)
# radial power spectrum pooled
fb = np.arange(0.02, 0.46, 0.02)
rp = [(round(float(1 / ((fb[i] + fb[i + 1]) / 2)), 2), float(acc[(fr >= fb[i]) & (fr < fb[i + 1])].sum())) for i in range(len(fb) - 1)]
print("pooled radial power (period px, power):", [(a, round(b, 4)) for a, b in rp])
out['pooled_radial_power'] = rp
L.dump("sb_s21_weave.json", out)
