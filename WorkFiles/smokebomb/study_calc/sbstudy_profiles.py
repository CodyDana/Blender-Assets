"""SMOKEBOMB_STUDY.md section 3: luminance profiles across bands, to read tape edges (the selvedge bead is a bright
ridge, the step's foot a dark line).  Writes profile plots (viewing aids) to the scratch dir and the ridge positions to
sbstudy_profiles.json.  Run: blender -b --factory-startup --python sbstudy_profiles.py -- <scratch_dir>"""
import bpy, numpy as np, os, sys, json
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/SmokeBomb/smokebomb.png"
HERE = os.path.dirname(os.path.abspath(__file__))
SCR = sys.argv[sys.argv.index("--") + 1]
img = bpy.data.images.load(REF); img.colorspace_settings.name = 'Non-Color'
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1, :, :3].copy()
bpy.data.images.remove(img)
L = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)

def bilinear(x, y):
    x0 = np.clip(np.floor(x).astype(int), 0, w - 2); y0 = np.clip(np.floor(y).astype(int), 0, h - 2)
    fx = x - x0; fy = y - y0
    return (L[y0, x0] * (1 - fx) * (1 - fy) + L[y0, x0 + 1] * fx * (1 - fy) + L[y0 + 1, x0] * (1 - fx) * fy
            + L[y0 + 1, x0 + 1] * fx * fy)

def profile(p0, p1, half_len=12, n=None):
    """Luminance along p0->p1, averaged over +-half_len px along the perpendicular... no: along the BAND direction,
    which is perpendicular to the profile, so the average blurs the weave but keeps the edges."""
    p0 = np.array(p0, float); p1 = np.array(p1, float)
    d = p1 - p0; length = np.linalg.norm(d); u = d / length; v = np.array([-u[1], u[0]])
    n = int(length)
    t = np.arange(n)
    acc = np.zeros(n)
    for s in np.linspace(-half_len, half_len, 2 * half_len + 1):
        q = p0[None, :] + t[:, None] * u[None, :] + s * v[None, :]
        acc += bilinear(q[:, 0], q[:, 1])
    return acc / (2 * half_len + 1)

# profiles chosen on the gridded views: each crosses bands roughly at right angles, away from the limb
PROFILES = {
    "right_vertical_x950": ((950, 300), (950, 700)),
    "right_vertical_x880": ((880, 300), (880, 720)),
    "centre_diag": ((520, 380), (700, 800)),
    "left_vertical_x330": ((330, 560), (330, 1000)),
    "bottom_vertical_x640": ((640, 800), (640, 1090)),
}
res = {}
plots = []
for name, (a, b) in PROFILES.items():
    p = profile(a, b)
    # detrend with a 41-px moving average, then find local maxima above +0.035 (ridges) and minima below -0.035
    k = 41
    ma = np.convolve(np.pad(p, k // 2, mode='edge'), np.ones(k) / k, mode='valid')
    d = p - ma
    ridges = [int(i) for i in range(2, len(d) - 2) if d[i] == d[i - 2:i + 3].max() and d[i] > 0.03]
    feet = [int(i) for i in range(2, len(d) - 2) if d[i] == d[i - 2:i + 3].min() and d[i] < -0.03]
    res[name] = {"from": a, "to": b, "ridges_at_px": ridges, "dark_lines_at_px": feet,
                 "profile_stored_luma": [round(float(x), 4) for x in p]}
    plots.append((name, p))
json.dump(res, open(os.path.join(HERE, "sbstudy_profiles.json"), "w"), indent=0)
# plot: one strip per profile, 3 px per sample, 200 px tall, value mapped 0..0.45
H = 200
for name, p in plots:
    W = len(p) * 3
    im = np.ones((H, W, 3), np.float32)
    for i, v in enumerate(p):
        y = int(np.clip(H - 1 - v / 0.45 * (H - 1), 0, H - 1))
        im[y:, i * 3:(i + 1) * 3] = (0.2, 0.2, 0.2)
    for k in range(0, len(p), 25):
        im[:, k * 3] = (1, 0, 0) if k % 100 == 0 else (0, 0.7, 0.7)
    o = bpy.data.images.new(name, W, H, alpha=False); o.colorspace_settings.name = 'Non-Color'
    o.pixels.foreach_set(np.concatenate([im[::-1], np.ones((H, W, 1), np.float32)], 2).ravel())
    o.filepath_raw = os.path.join(SCR, 'sbstudy_prof_' + name + '.png'); o.file_format = 'PNG'; o.save()
    bpy.data.images.remove(o)
for k, v in res.items():
    print("SBPROF", k, "ridges", v["ridges_at_px"], "dark", v["dark_lines_at_px"])
