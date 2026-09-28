# Image metrics for the BlackCloak v2 surface kit. Runs in Blender 5.2 Python (numpy).
# spectrum() and the flattest-window picker are copied from WorkFiles/BlackCloak_Review/male/gap/scripts/gap_measure2.py,
# the structure-tensor anisotropy and hp_rel from WorkFiles/BlackCloak_Review/male/verify/vf_measure.py (read-only
# sources; copied so the review tools stay untouched).
import bpy, os, numpy as np


def load(path):
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = "Non-Color"   # raw stored (sRGB-encoded) values, also for 16-bit PNGs
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[::-1].copy()
    bpy.data.images.remove(img)
    rgb = a[..., :3] * 255.0
    al = a[..., 3]
    if (al < 0.999).any():                     # composite over white, in linear
        lin = s2l(rgb / 255.0) * al[..., None] + (1 - al[..., None])
        rgb = l2s(lin) * 255.0
    return np.ascontiguousarray(rgb)


def save(path, rgb):
    rgb = np.clip(np.asarray(rgb, dtype=np.float32), 0, 255)
    if rgb.ndim == 2:
        rgb = np.stack([rgb] * 3, -1)
    h, w = rgb.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = rgb / 255.0
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def s2l(x):
    x = np.asarray(x, np.float64)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def l2s(x):
    x = np.clip(np.asarray(x, np.float64), 0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def lum(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def blur2d(a, k):
    if k <= 1:
        return a
    pad = k // 2
    ap = np.pad(a, pad, mode='edge')
    c = np.cumsum(np.cumsum(ap, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = a.shape
    s = c[k:k + h, k:k + w] - c[0:h, k:k + w] - c[k:k + h, 0:w] + c[0:h, 0:w]
    return s / (k * k)


def spectrum(p):
    """gap_measure2.spectrum: share of high-passed power per wavelength band (px) + vertical/horizontal freq ratio."""
    p = p - blur2d(p, 9)
    n = p.shape[0]
    w = np.hanning(n)
    p = p * np.outer(w, w)
    F = np.abs(np.fft.fftshift(np.fft.fft2(p))) ** 2
    fy, fx = np.mgrid[-n // 2:n // 2, -n // 2:n // 2] / n
    fr = np.hypot(fx, fy)
    tot = F[fr > 0].sum()
    out = {}
    for nm, (plo, phi) in {'p2_3': (2, 3), 'p3_5': (3, 5), 'p5_10': (5, 10), 'p10_16': (10, 16)}.items():
        out[nm] = float(F[(fr <= 1 / plo) & (fr > 1 / phi)].sum() / tot)
    v = F[(np.abs(fy) > 2 * np.abs(fx)) & (fr > 0.06)].sum()
    h = F[(np.abs(fx) > 2 * np.abs(fy)) & (fr > 0.06)].sum()
    out['aniso_vfreq_over_hfreq'] = float(v / (h + 1e-9))
    return out


def struct_aniso(Ls):
    """vf_measure: eigenvalue ratio of the structure tensor of a 3x3-box-blurred patch (1 = no direction)."""
    gy, gx = np.gradient(blur2d(Ls, 3))
    J = np.array([[np.sum(gx * gx), np.sum(gx * gy)], [np.sum(gx * gy), np.sum(gy * gy)]])
    ev = np.linalg.eigvalsh(J)
    return float(ev[1] / max(ev[0], 1e-9))


def patch_stats(Ls, mm_per_px=None):
    """Ls: a patch of sRGB-coded luminance 0..255."""
    Ls = Ls.astype(np.float64)
    hp7 = Ls - blur2d(Ls, 7)
    extra = {}
    if mm_per_px:
        b = radial_bands_mm(s2l(Ls / 255.0), mm_per_px, bands_mm=((5.4, 10.0), (10.0, 20.0), (20.0, 45.0)))
        extra = {'lin_amp_5_10mm': b['amp_5.4_10mm'], 'lin_amp_10_20mm': b['amp_10_20mm'],
                 'lin_amp_20_45mm': b['amp_20_45mm'], 'orient_v_over_h': b['orient_vert_over_horiz_3_80mm'],
                 'orient_axes_over_diag': b['orient_axes_over_diag_3_80mm']}
    return {**extra, 'mean': float(Ls.mean()), 'median': float(np.median(Ls)),
            'hp_std': float(hp7[3:-3, 3:-3].std()), 'hp_rel': float(hp7[3:-3, 3:-3].std() / max(Ls.mean(), 1e-6)),
            'lf_std_rel': float(blur2d(Ls, 5)[4:-4, 4:-4].std() / max(Ls.mean(), 1e-6)),
            'p5_p95': [float(np.percentile(Ls, 5)), float(np.percentile(Ls, 95))],
            'struct_aniso': struct_aniso(Ls), 'spec': spectrum(Ls)}


def flat_patches(L, m, n=32, k=8, x_rng=(30, 390), y_rng=(100, 620), step=8, mm_per_px=None):
    """gap_measure2: k flattest n x n fully-garment windows (low-frequency gradient smallest), non-overlapping."""
    l = L.astype(np.float64)
    lf = blur2d(l, 9)
    H, W = l.shape
    cands = []
    for y in range(y_rng[0], min(y_rng[1], H) - n, step):
        for x in range(x_rng[0], min(x_rng[1], W) - n, step):
            if not m[y:y + n, x:x + n].all():
                continue
            w = lf[y:y + n, x:x + n]
            gy, gx = np.gradient(w)
            cands.append((float(np.hypot(gx, gy).mean() / (w.mean() + 1)), x, y))
    cands.sort()
    chosen = []
    for c in cands:
        if all(abs(c[1] - q[1]) >= n or abs(c[2] - q[2]) >= n for q in chosen):
            chosen.append(c)
        if len(chosen) == k:
            break
    rows = []
    for _, x, y in chosen:
        r = patch_stats(l[y:y + n, x:x + n], mm_per_px)
        r['xy'] = [x, y]
        rows.append(r)
    return rows


def agg(rows):
    out = {}
    for key in ('mean', 'median', 'hp_std', 'hp_rel', 'lf_std_rel', 'struct_aniso', 'lin_amp_5_10mm',
                'lin_amp_10_20mm', 'lin_amp_20_45mm', 'orient_v_over_h', 'orient_axes_over_diag'):
        if key not in rows[0]:
            continue
        v = [r[key] for r in rows]
        out[key + '_mean'] = float(np.mean(v))
        out[key + '_range'] = [float(np.min(v)), float(np.max(v))]
    for key in rows[0]['spec']:
        out['spec_' + key] = float(np.mean([r['spec'][key] for r in rows]))
    return out


def radial_bands_mm(Llin, mm_per_px, bands_mm=((0.5, 1.0), (1.0, 3.0), (3.0, 10.0), (10.0, 20.0), (20.0, 40.0), (40.0, 80.0))):
    """Relative amplitude (sqrt of power share of the mean-normalised field) per physical wavelength band; plus the
    orientation ratio of power within 10-45 deg sectors around horizontal vs vertical frequency axes (1 = isotropic)."""
    a = Llin / Llin.mean() - 1.0
    n0, n1 = a.shape
    F = np.abs(np.fft.fft2(a)) ** 2 / (n0 * n1) ** 2
    fy = np.fft.fftfreq(n0)[:, None] * np.ones((1, n1))
    fx = np.ones((n0, 1)) * np.fft.fftfreq(n1)[None, :]
    fr = np.hypot(fx, fy)
    wl = np.where(fr > 0, mm_per_px / np.maximum(fr, 1e-12), np.inf)
    out = {}
    for lo, hi in bands_mm:
        sel = (wl >= lo) & (wl < hi)
        out['amp_%g_%gmm' % (lo, hi)] = float(np.sqrt(F[sel].sum()))
    sel = (wl >= 3) & (wl < 80)
    ang = np.degrees(np.arctan2(np.abs(fy), np.abs(fx)))
    v = F[sel & (ang > 70)].sum()
    h = F[sel & (ang < 20)].sum()
    d = F[sel & (ang > 25) & (ang < 65)].sum()
    out['orient_vert_over_horiz_3_80mm'] = float(v / max(h, 1e-30))
    out['orient_axes_over_diag_3_80mm'] = float((v + h) / 2 / max(d / 2, 1e-30))   # sector widths 20,20 vs 40
    out['std_over_mean'] = float(a.std())
    return out
