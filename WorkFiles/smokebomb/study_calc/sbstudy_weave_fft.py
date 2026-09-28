"""SMOKEBOMB_STUDY.md section 3: the weave period of the reference, from the 2-D power spectrum of patches that lie
inside single tapes near the disc centre (least foreshortening).  Writes sbstudy_weave_fft.json.
Run: blender -b --factory-startup --python sbstudy_weave_fft.py"""
import bpy, numpy as np, os, json
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/SmokeBomb/smokebomb.png"
HERE = os.path.dirname(os.path.abspath(__file__))
img = bpy.data.images.load(REF); img.colorspace_settings.name = 'Non-Color'
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1, :, :3].copy()
bpy.data.images.remove(img)
L = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
CX, CY, R = 627.3, 629.1, 463.9          # sbstudy_measure_ref.json, threshold 0.6
N = 96
PATCHES = {"centre_lower": (560, 640), "centre_right": (760, 600), "centre_left": (470, 560),
           "lower_mid": (640, 760), "upper_mid": (650, 420), "right_band": (900, 470), "left_band": (330, 720)}
win = np.outer(np.hanning(N), np.hanning(N))
res = {}
for name, (x, y) in PATCHES.items():
    p = L[y - N // 2:y + N // 2, x - N // 2:x + N // 2].astype(np.float64)
    p = (p - p.mean()) * win
    F = np.fft.fftshift(np.abs(np.fft.fft2(p)) ** 2)
    fy, fx = np.mgrid[-N // 2:N // 2, -N // 2:N // 2] / N    # cycles per px
    fr = np.hypot(fx, fy)
    F[fr < 1.0 / 30.0] = 0                                    # drop shading (periods > 30 px)
    peaks = []
    Fw = F.copy()
    for _ in range(6):
        i = np.unravel_index(np.argmax(Fw), Fw.shape)
        f = fr[i]
        if f == 0: break
        ang = (np.degrees(np.arctan2(-fy[i], fx[i])) + 180.0) % 180.0
        peaks.append({"period_px": round(float(1.0 / f), 2), "wavevector_angle_deg": round(float(ang), 1),
                      "power_rel": round(float(Fw[i] / F.max()), 3)})
        # suppress the peak and its mirror
        yy, xx = i
        for (a, b) in ((yy, xx), (N - yy, N - xx)):
            Fw[max(a - 2, 0):a + 3, max(b - 2, 0):b + 3] = 0
    # radially binned spectrum: where is the energy?
    bins = np.arange(2, 31)
    radial = []
    for pp in bins:
        m = (fr >= 1.0 / (pp + 0.5)) & (fr < 1.0 / (pp - 0.5))
        radial.append(float(F[m].sum()))
    radial = np.array(radial) / max(radial)
    rr = np.hypot(x - CX, y - CY) / R
    res[name] = {"centre_xy": [x, y], "r_over_R": round(float(rr), 3), "peaks": peaks,
                 "radial_energy_by_period_px": {int(b): round(float(v), 3) for b, v in zip(bins, radial)}}
json.dump(res, open(os.path.join(HERE, "sbstudy_weave_fft.json"), "w"), indent=1)
for k, v in res.items():
    print("SBFFT", k, v["r_over_R"], [(p["period_px"], p["wavevector_angle_deg"], p["power_rel"]) for p in v["peaks"]])
