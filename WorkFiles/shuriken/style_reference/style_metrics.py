"""Style metrics: the STYLE_TARGET.md recipe measured on a set of PBR maps inside a mesh's UV mask.

The analysis of the reference (scratch styleref_textures.py, 2026-09-18) sampled the 4K maps at
stride 4 (N = 1024, about 15 px/cm) and used pixel-sized kernels: a 7 x 7 median for the
scratch / pit high-pass and a 12 px erosion for the island border.  Our maps are 2048 px at
135-175 px/cm, so the same pixel kernels would mean different millimetres.  This script keeps
the reference path bit-for-bit (stride 4, point sampled) and samples OUR maps at the integer
stride that brings them closest to the reference's px/cm at analysis resolution, so every
kernel covers the same millimetres on both.  The effective px/cm is reported alongside.

    blender -b --factory-startup --python style_metrics.py -- --reference <ref_dir> --out <json>
    blender -b --factory-startup --python style_metrics.py -- --blend <Shuriken.blend> --mesh SM_Shuriken_FourPoint_LOD0 \
        --textures <Exports/Shuriken/Textures> --stem T_Shuriken_FourPoint --out <json>

Our maps: BC (sRGB stored), ORM (R = AO, G = roughness, B = metallic, linear), N (DirectX; the
tilt uses the blue channel only, so the green flip does not matter).  The mask comes from the
LOD0 mesh appended from the .blend (never opened or saved).
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def absolute(value):
    return str(Path(value).resolve()) if value else value


REF_DIR = absolute(arg("--reference"))
BLEND = absolute(arg("--blend"))
MESH = arg("--mesh")                 # the LOD0 OBJECT name (its mesh datablock keeps the un-suffixed name)
TEXTURES = absolute(arg("--textures"))
STEM = arg("--stem")
OUT = Path(arg("--out", "style_metrics.json")).resolve()
REF_STRIDE = 4                      # the reference analysis: 4096 -> 1024
REF_PX_PER_CM = float(arg("--target-px-per-cm", "0"))   # 0 = the default below
# The reference's density at its analysis resolution, measured HERE the same way as ours
# (sqrt(mask fraction x N^2 / surface area)): 36.47 px/cm at N = 1024 (145.9 px/cm at 4K).
# STYLE_TARGET.md's "about 61 px/cm at 4K" was a different estimate; this one is what makes the
# two analyses comparable.  Pass --target-px-per-cm to override (e.g. from metrics_reference.json).
DEFAULT_REF_PX_PER_CM = 36.47
# The island "interior" is the mask eroded by ERODE_MM.  The reference analysis eroded by 12 px
# (~7.9 mm at its density), which on the pack's 11 mm arms and 7 mm hub annulus leaves no
# interior at all; 3 mm keeps an interior on every form and, on the reference's uniform coat,
# moves its interior p50 by under 0.01 (p05 0.323 / p95 0.362 at 12 px).  --erode-mm overrides.
ERODE_MM = float(arg("--erode-mm", "3.0"))
MEDIAN = 7
# The COAT INTERIOR: the interior with every bare-steel area (stored value above BARE_THRESHOLD)
# removed together with a BARE_DILATE_MM halo, so the scratch / pit high-pass counts authored
# marks only, never the coat / bare wear boundary (the first style pass measured 2.3-2.5 % "pits"
# that were the torn boundary's dark side).  Applied identically to the reference and our maps.
BARE_THRESHOLD = float(arg("--bare-threshold", "0.41"))
BARE_DILATE_MM = float(arg("--bare-dilate-mm", "1.0"))


def load_raw(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    img.reload()
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::-1]        # top-origin rows, raw stored values


def sample(a, stride):
    n = a.shape[0] // stride
    return a[:n * stride:stride, :n * stride:stride, :3]


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def uv_mask(mesh, matrix, n):
    """Rasterise the UV triangles to an n x n boolean mask (top-origin rows) plus |face normal z|."""
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active.data
    mask = np.zeros((n, n), dtype=bool)
    nz = np.zeros((n, n), dtype=np.float32)
    mw = matrix.to_3x3()
    for t in mesh.loop_triangles:
        p = np.array([uv[i].uv for i in t.loops]) * n
        x0, y0 = np.floor(p.min(0)).astype(int)
        x1, y1 = np.ceil(p.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, n - 1), min(y1, n - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = p
        d = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        if abs(d) < 1e-9:
            continue
        w0 = ((bx - xs) * (cy - ys) - (by - ys) * (cx - xs)) / d
        w1 = ((cx - xs) * (ay - ys) - (cy - ys) * (ax - xs)) / d
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        rows = (n - 1 - ys[inside].astype(int))
        cols = xs[inside].astype(int)
        mask[rows, cols] = True
        normal = (mw @ t.normal).normalized()
        nz[rows, cols] = abs(normal.z)
    return mask, nz


def surface_area_cm2(mesh, matrix):
    mesh.calc_loop_triangles()
    co = np.array([matrix @ v.co for v in mesh.vertices])
    total = 0.0
    for t in mesh.loop_triangles:
        a, b, c = (co[i] for i in t.vertices)
        total += 0.5 * np.linalg.norm(np.cross(b - a, c - a))
    return total * 1e4


def erode(m, k):
    out = m.copy()
    for _ in range(k):
        e = out.copy()
        e[1:] &= out[:-1]
        e[:-1] &= out[1:]
        e[:, 1:] &= out[:, :-1]
        e[:, :-1] &= out[:, 1:]
        out = e
    return out


def dilate(m, k):
    out = m.copy()
    for _ in range(k):
        e = out.copy()
        e[1:] |= out[:-1]
        e[:-1] |= out[1:]
        e[:, 1:] |= out[:, :-1]
        e[:, :-1] |= out[:, 1:]
        out = e
    return out


def stats(a, m):
    v = a[m]
    if not len(v):
        return None
    return {"mean": round(float(v.mean()), 4), "p05": round(float(np.percentile(v, 5)), 4),
            "p50": round(float(np.percentile(v, 50)), 4), "p95": round(float(np.percentile(v, 95)), 4)}


def analyse(bc, metal, rough, normal, mask, nz, px_per_cm, source):
    n = mask.shape[0]
    plate = mask & (nz > 0.7)
    wall = mask & (nz <= 0.7)
    erode_px = max(1, int(round(ERODE_MM * px_per_cm / 10.0)))
    interior = erode(mask, erode_px)
    border = mask & ~interior
    lin = srgb_to_lin(bc)
    lum = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    sat = (bc.max(-1) - bc.min(-1)) / np.maximum(bc.max(-1), 1e-6)
    hue_bias = bc[..., 2] - bc[..., 0]
    v = bc.mean(-1)
    pad = np.pad(v, MEDIAN // 2, mode="edge")
    win = sliding_window_view(pad, (MEDIAN, MEDIAN))
    local_med = np.median(win.reshape(n, n, -1), axis=-1)
    resid = v - local_med
    scratch = mask & (resid > 0.10)
    pit = mask & (resid < -0.10)
    bare = mask & (v > BARE_THRESHOLD)
    dilate_px = max(1, int(round(BARE_DILATE_MM * px_per_cm / 10.0)))
    coat_interior = interior & ~dilate(bare, dilate_px)
    coat_plate = plate & ~dilate(bare, dilate_px)
    nvec = normal * 2 - 1
    ang = np.degrees(np.arccos(np.clip(nvec[..., 2] / np.maximum(np.linalg.norm(nvec, axis=-1), 1e-6), -1, 1)))
    interior_p50 = stats(v, interior)["p50"] if interior.any() else None
    border_mean = stats(v, border)["mean"] if border.any() else None
    interior_mean = stats(v, interior)["mean"] if interior.any() else None
    return {
        "source": source,
        "analysis_px": n,
        "px_per_cm_at_analysis": round(px_per_cm, 3),
        "erode_px": erode_px, "erode_mm": round(erode_px / px_per_cm * 10.0, 3),
        "interior_fraction_of_mask": round(float(interior.sum() / mask.sum()), 4),
        "bare_threshold_stored": BARE_THRESHOLD, "bare_dilate_px": dilate_px,
        "bare_fraction_of_plate": round(float(bare[plate].mean()), 4),
        "coat_interior_fraction_of_mask": round(float(coat_interior.sum() / mask.sum()), 4),
        "median_window_px": MEDIAN, "median_window_mm": round(MEDIAN / px_per_cm * 10.0, 3),
        "uv_coverage_fraction": round(float(mask.mean()), 4),
        "plate_fraction_of_mask": round(float(plate.sum() / mask.sum()), 4),
        "basecolor_stored": {"plate": stats(v, plate), "wall": stats(v, wall), "border": stats(v, border),
                             "interior": stats(v, interior)},
        "coat_p50_stored": interior_p50,
        "coat_p50_linear": round(float(srgb_to_lin(np.array(interior_p50))), 4) if interior_p50 is not None else None,
        "border_over_interior": round(border_mean / interior_mean, 4) if border_mean and interior_mean else None,
        "basecolor_linear_luminance": {"plate": stats(lum, plate), "wall": stats(lum, wall)},
        "saturation": stats(sat, mask), "blue_minus_red": stats(hue_bias, mask),
        "metallic": {"all": stats(metal, mask), "plate": stats(metal, plate), "wall": stats(metal, wall),
                     "fraction_below_0.5": round(float((metal[mask] < 0.5).mean()), 4),
                     "mean_basecolor_where_nonmetal": (round(float(v[mask & (metal < 0.5)].mean()), 4)
                                                       if (mask & (metal < 0.5)).any() else None),
                     "mean_basecolor_where_metal": round(float(v[mask & (metal >= 0.5)].mean()), 4)},
        "roughness": {"plate": stats(rough, plate), "wall": stats(rough, wall), "border": stats(rough, border),
                      "interior": stats(rough, interior)},
        # The high-pass also fires on both sides of a coat / bare-metal boundary (bright bare
        # islands read as scratches, dark coat islands as pits), and the pack's narrow arms carry
        # far more torn boundary per area than the 197 mm reference; the *coat_interior* figures
        # (the interior with every bare area and a 1 mm halo removed) count authored marks only
        # and are the comparable ones; *interior* (the mask eroded by ERODE_MM) is kept for history.
        "scratches": {"fraction_of_mask": round(float(scratch[mask].mean()), 4),
                      "mean_brightness_gain": round(float(resid[scratch].mean()), 4) if scratch.any() else 0,
                      "plate_fraction": round(float(scratch[plate].mean()), 4),
                      "interior_fraction": round(float(scratch[interior].mean()), 4) if interior.any() else None,
                      "coat_plate_fraction": round(float(scratch[coat_plate].mean()), 4) if coat_plate.any() else None,
                      "coat_interior_fraction": (round(float(scratch[coat_interior].mean()), 4)
                                                 if coat_interior.any() else None),
                      "coat_interior_gain": (round(float(resid[scratch & coat_interior].mean()), 4)
                                             if (scratch & coat_interior).any() else 0),
                      "wall_fraction": round(float(scratch[wall].mean()), 4) if wall.any() else None},
        "dark_pits": {"fraction_of_mask": round(float(pit[mask].mean()), 4),
                      "interior_fraction": round(float(pit[interior].mean()), 4) if interior.any() else None,
                      "coat_plate_fraction": round(float(pit[coat_plate].mean()), 4) if coat_plate.any() else None,
                      "coat_interior_fraction": (round(float(pit[coat_interior].mean()), 4)
                                                 if coat_interior.any() else None),
                      "coat_interior_darkening": (round(float(resid[pit & coat_interior].mean()), 4)
                                                  if (pit & coat_interior).any() else 0),
                      "mean_darkening": round(float(resid[pit].mean()), 4) if pit.any() else 0},
        "normal_map_tilt_deg": {"plate": stats(ang, plate), "wall": stats(ang, wall), "border": stats(ang, border),
                                "interior": stats(ang, interior),
                                "fraction_over_10deg": round(float((ang[mask] > 10).mean()), 4)},
    }


def reference():
    ref = Path(REF_DIR)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.fbx_import(filepath=str(ref / "shuriken_lp.fbx"))
    obj = next(o for o in bpy.data.objects if o.type == "MESH")
    bc = sample(load_raw(ref / "shuriken_Shuriken_BaseColor.png"), REF_STRIDE)
    n = bc.shape[0]
    metal = sample(load_raw(ref / "shuriken_Shuriken_Metallic.png"), REF_STRIDE)[..., 0]
    rough = sample(load_raw(ref / "shuriken_Shuriken_Roughness.png"), REF_STRIDE)[..., 0]
    normal = sample(load_raw(ref / "shuriken_Shuriken_Normal.png"), REF_STRIDE)
    mask, nz = uv_mask(obj.data, obj.matrix_world, n)
    px_per_cm = float(np.sqrt(mask.mean() * n * n / surface_area_cm2(obj.data, obj.matrix_world)))
    return analyse(bc, metal, rough, normal, mask, nz, px_per_cm, f"reference {ref.name}, stride {REF_STRIDE}")


def ours():
    with bpy.data.libraries.load(str(BLEND), link=False) as (src, dst):
        if MESH not in src.objects:
            raise KeyError(f"{MESH} not in {BLEND}: {sorted(src.objects)}")
        dst.objects = [MESH]
    mesh = dst.objects[0].data
    tex = Path(TEXTURES)
    bc_full = load_raw(tex / f"{STEM}_BC.png")
    full = bc_full.shape[0]
    from mathutils import Matrix
    identity = Matrix.Identity(4)
    area = surface_area_cm2(mesh, identity)
    mask_full, _ = uv_mask(mesh, identity, 256)          # coverage at a coarse resolution is enough for px/cm
    px_per_cm_full = float(np.sqrt(mask_full.mean() * full * full / area))
    target = REF_PX_PER_CM or DEFAULT_REF_PX_PER_CM
    stride = max(1, int(round(px_per_cm_full / target)))
    bc = sample(bc_full, stride)
    n = bc.shape[0]
    orm = sample(load_raw(tex / f"{STEM}_ORM.png"), stride)
    normal = sample(load_raw(tex / f"{STEM}_N.png"), stride)
    mask, nz = uv_mask(mesh, identity, n)
    px_per_cm = float(np.sqrt(mask.mean() * n * n / area))
    rep = analyse(bc, orm[..., 2], orm[..., 1], normal, mask, nz, px_per_cm,     # B = metallic, G = roughness
                  f"{STEM} ({full} px, {px_per_cm_full:.1f} px/cm), stride {stride} to match the reference's "
                  f"{target} px/cm")
    rep["ao_mean_in_mask"] = round(float(orm[..., 0][mask].mean()), 4)
    rep["stride"] = stride
    rep["px_per_cm_full"] = round(px_per_cm_full, 2)
    return rep


def main():
    rep = reference() if REF_DIR else ours()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("STYLE_METRICS", json.dumps({k: rep[k] for k in ("source", "px_per_cm_at_analysis", "coat_p50_stored",
                                                           "border_over_interior")}))
    print("STYLE_METRICS_FULL", json.dumps(rep))


main()
