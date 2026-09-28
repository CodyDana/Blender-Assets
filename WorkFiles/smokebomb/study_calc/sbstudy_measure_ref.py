"""SMOKEBOMB_STUDY.md section 3: scalar measurements of the reference (silhouette, value, colour).

Research-agent script (the full band-by-band metrology is the metrology agent's REFERENCE_SPEC.md).
Reads the reference PNG with its colourspace forced to Non-Color, so pixels are the stored sRGB bytes / 255.
Writes only: sbstudy_measure_ref.json next to this file, and zoom crops into the scratch dir given as argv.
Run: blender -b --factory-startup --python sbstudy_measure_ref.py -- <scratch_dir>
"""
import bpy, numpy as np, json, os, sys, hashlib
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/SmokeBomb/smokebomb.png"
HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SCR = argv[0] if argv else None

img = bpy.data.images.load(REF)
img.colorspace_settings.name = 'Non-Color'
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1, :, :3].copy()  # top-down
bpy.data.images.remove(img)

def lin(s):
    return np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
Y = np.array([0.2126, 0.7152, 0.0722], np.float32)
lum_s = px @ Y
out = {"file": REF, "sha256": hashlib.sha256(open(REF, 'rb').read()).hexdigest(), "size": [w, h]}
bg = np.concatenate([px[:40, :40].reshape(-1, 3), px[:40, -40:].reshape(-1, 3), px[-40:, :40].reshape(-1, 3), px[-40:, -40:].reshape(-1, 3)])
out["background_stored_mean"] = bg.mean(0).round(4).tolist()

# silhouette: anything clearly darker than the white backdrop
for thr in (0.80, 0.60):
    m = lum_s < thr
    ys, xs = np.nonzero(m)
    area = int(m.sum())
    cy, cx = ys.mean(), xs.mean()
    d_eq = 2.0 * np.sqrt(area / np.pi)
    # radial profile of the boundary: farthest mask pixel per 1-degree bin
    ang = np.degrees(np.arctan2(-(ys - cy), xs - cx)) % 360.0
    r = np.hypot(ys - cy, xs - cx)
    rmax = np.zeros(360)
    np.maximum.at(rmax, ang.astype(int) % 360, r)
    out[f"silhouette_thr{thr}"] = {
        "area_px": area, "centre_xy": [round(float(cx), 2), round(float(cy), 2)],
        "bbox_x": [int(xs.min()), int(xs.max())], "bbox_y": [int(ys.min()), int(ys.max())],
        "bbox_w": int(xs.max() - xs.min() + 1), "bbox_h": int(ys.max() - ys.min() + 1),
        "equivalent_diameter_px": round(float(d_eq), 2),
        "boundary_radius_px": {"min": round(float(rmax.min()), 1), "p05": round(float(np.percentile(rmax, 5)), 1),
                                "p50": round(float(np.median(rmax)), 1), "p95": round(float(np.percentile(rmax, 95)), 1),
                                "max": round(float(rmax.max()), 1), "std": round(float(rmax.std()), 2)},
        "fill_of_bbox": round(area / float((xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1)), 4),
    }
sil = out["silhouette_thr0.6"]
cx, cy = sil["centre_xy"]; R = sil["equivalent_diameter_px"] / 2
yy, xx = np.mgrid[0:h, 0:w]
rr = np.hypot(xx - cx, yy - cy)
inner = rr < 0.80 * R            # the cloth, away from the limb and its white fringe
c = px[inner]
cl = lin(c)
out["cloth_inner80_stored"] = {"p05": np.percentile(c, 5, axis=0).round(4).tolist(),
                               "p50": np.percentile(c, 50, axis=0).round(4).tolist(),
                               "p95": np.percentile(c, 95, axis=0).round(4).tolist(),
                               "mean": c.mean(0).round(4).tolist()}
out["cloth_inner80_linear"] = {"p05": np.percentile(cl, 5, axis=0).round(5).tolist(),
                               "p50": np.percentile(cl, 50, axis=0).round(5).tolist(),
                               "p95": np.percentile(cl, 95, axis=0).round(5).tolist(),
                               "p99": np.percentile(cl, 99, axis=0).round(5).tolist(),
                               "mean": cl.mean(0).round(5).tolist()}
ls = c @ Y
out["cloth_inner80_stored_luma"] = {k: round(float(np.percentile(ls, q)), 4) for k, q in
                                     (("p01", 1), ("p05", 5), ("p25", 25), ("p50", 50), ("p75", 75), ("p95", 95), ("p99", 99))}
# hue: ratio of channels at the median
med = np.median(cl, axis=0)
out["cloth_linear_ratio_rgb"] = (med / med[0]).round(3).tolist()
# fine texture: high-pass sigma at a 9 px box (weave scale) on the inner region
k = 9
from numpy.lib.stride_tricks import sliding_window_view
L = lum_s
pad = np.pad(L, k // 2, mode='edge')
box = sliding_window_view(pad, (k, k)).mean(axis=(2, 3))
hp = (L - box)[inner]
out["highpass_sigma_9px_stored"] = round(float(hp.std()), 4)
json.dump(out, open(os.path.join(HERE, "sbstudy_measure_ref.json"), "w"), indent=1)
print("SBSTUDY", json.dumps(out))

if SCR:
    os.makedirs(SCR, exist_ok=True)
    def save_crop(name, x0, y0, x1, y1, scale=2):
        crop = px[y0:y1, x0:x1]
        crop = np.repeat(np.repeat(crop, scale, 0), scale, 1)
        hh, ww = crop.shape[:2]
        im = bpy.data.images.new(name, ww, hh, alpha=False)
        im.colorspace_settings.name = 'Non-Color'
        rgba = np.concatenate([crop[::-1], np.ones((hh, ww, 1), np.float32)], axis=2)
        im.pixels.foreach_set(rgba.ravel())
        im.filepath_raw = os.path.join(SCR, name + ".png"); im.file_format = 'PNG'; im.save()
        bpy.data.images.remove(im)
    save_crop("sbstudy_crop_top", 380, 130, 880, 480)
    save_crop("sbstudy_crop_mid", 480, 450, 980, 800)
    save_crop("sbstudy_crop_left", 140, 380, 540, 780)
    save_crop("sbstudy_crop_bottom", 380, 820, 880, 1140)
    save_crop("sbstudy_crop_right", 800, 380, 1120, 780)
    save_crop("sbstudy_crop_weave", 600, 600, 760, 720, scale=4)
