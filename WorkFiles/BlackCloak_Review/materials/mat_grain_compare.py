"""Compare fine fabric grain (slub/mottle) of the reference against the cloak's own renders, same pixel scale.
Read-only. Output: WorkFiles/BlackCloak_Review/materials/mat_grain_compare.json + side-by-side crops PNG.
"""
import bpy, json
import numpy as np
from pathlib import Path

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/BlackCloak_Review/materials"


def load(p):
    img = bpy.data.images.load(str(p), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)[::-1, :, :3]  # top row first


def resize(a, W, H):
    h, w = a.shape[:2]
    ys = (np.arange(H) + 0.5) * h / H - 0.5; xs = (np.arange(W) + 0.5) * w / W - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, h - 2); x0 = np.clip(np.floor(xs).astype(int), 0, w - 2)
    fy = np.clip(ys - y0, 0, 1)[:, None, None]; fx = np.clip(xs - x0, 0, 1)[None, :, None]
    # area-average first to avoid aliasing when shrinking
    k = max(1, int(round(w / W)))
    if k > 1:
        hh, ww = (h // k) * k, (w // k) * k
        a = a[:hh, :ww].reshape(hh // k, k, ww // k, k, -1).mean(axis=(1, 3)); return resize(a, W, H)
    A = a[y0][:, x0]; B = a[y0][:, x0 + 1]; C = a[y0 + 1][:, x0]; D = a[y0 + 1][:, x0 + 1]
    return (A * (1 - fx) + B * fx) * (1 - fy) + (C * (1 - fx) + D * fx) * fy


def box(a, r):
    k = 2 * r + 1
    p = np.pad(a, r, mode="edge")
    c = np.cumsum(np.cumsum(p, 0), 1); c = np.pad(c, ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def analyse(rgb, label):
    Y = rgb @ np.array([0.2126, 0.7152, 0.0722])  # stored (sRGB-encoded) luma, 0..1
    cloth = Y < 0.45
    cloth = box(cloth.astype(float), 4) > 0.999  # erode
    fine = Y - box(Y, 2)            # detail below ~5 px
    mid = box(Y, 2) - box(Y, 6)     # 5-13 px
    grad = np.hypot(*np.gradient(box(Y, 3)))
    flat = cloth & (grad < np.percentile(grad[cloth], 50))
    return {"label": label, "cloth_px": int(cloth.sum()), "flat_px": int(flat.sum()),
            "cloth_luma_stored_p5_p50_p95": [float(np.percentile(Y[cloth], q)) * 255 for q in (5, 50, 95)],
            "fine_std_levels_flat": float(fine[flat].std() * 255),
            "mid_std_levels_flat": float(mid[flat].std() * 255),
            "fine_over_median_luma": float(fine[flat].std() / max(np.median(Y[flat]), 1e-4))}


ref = load(ROOT / "References/BlackCloak/blackcloak.png")
H, W = ref.shape[:2]
res = [analyse(ref, "reference 417x674")]
for p in ["Renders/BlackCloak/Recolor/Cloak_Black.png", "Renders/BlackCloak/ReferenceRevision/Revision_Front.png",
          "Renders/BlackCloak/BlackCloak_Front.png"]:
    a = load(ROOT / p)
    # same framing is claimed for Recolor (ortho scale matched to the reference); resize to the reference size
    res.append(analyse(resize(a, W, H), p + " resized to 417x674"))
    res.append(analyse(a, p + " native"))
(OUT / "mat_grain_compare.json").write_text(json.dumps(res, indent=2), encoding="utf-8")

# side-by-side crop: reference chest/front panel vs Cloak_Black same region, 4x nearest upscale, levels stretched equally
a = resize(load(ROOT / "Renders/BlackCloak/Recolor/Cloak_Black.png"), W, H)
y0, y1, x0, x1 = 380, 480, 180, 280
def crop(x):
    c = x[y0:y1, x0:x1].mean(axis=2)
    c = np.clip((c - 0.02) / 0.35, 0, 1)
    return np.kron(c, np.ones((4, 4)))
sheet = np.concatenate([crop(ref), np.ones((400, 8)), crop(a)], axis=1)
img = bpy.data.images.new("mat_grain_side_by_side", sheet.shape[1], sheet.shape[0], alpha=False)
px = np.ones((*sheet.shape, 4), np.float32); px[:, :, :3] = sheet[::-1, :, None]
img.pixels.foreach_set(px.ravel()); img.filepath_raw = str(OUT / "mat_grain_ref_vs_cloakblack_crop.png"); img.file_format = "PNG"; img.save()
print("GRAIN_DONE")
