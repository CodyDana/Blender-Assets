"""Outline regression for the style pass: every form's LOD0 silhouette must equal the pre-restyle backup's.

The restyle changes the edge treatment (a full-length ground chamfer on every outer edge) and
the surface, nothing else: outlines, sizes, thicknesses and hole sizes stay.  This gate
projects each LOD0's silhouette (every face, in plan) to XY at RESOLUTION mm per pixel and
compares it with the backup's; the two must be identical apart from raster noise.  It then
compares the flat TOP faces (the plate at z = +t/2): those may differ only inside the chamfer
band, i.e. every differing pixel must lie within the form's chamfer width (plus a raster
tolerance) of the outline.  Sizes from the two reports (tip radius, hole, arm width, thickness)
are compared as well.

Headless, read-only on both .blend files (they are appended from, never opened or saved):
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python-exit-code 3 \
        --python WorkFiles/shuriken/regression/compare_outline_restyle.py -- \
        [--backup DIR] [--blend FILE] [--reports DIR] [--forms four_point,eight_point,square_plate] [--out FILE]

Writes regression_restyle.json next to this file (or --out) and a diff PNG per form in
WorkFiles/shuriken/regression/restyle_diff/: grey = both silhouettes, red = backup only, green =
new only, with the top-face difference drawn as a lighter band.
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils.kdtree import KDTree

PROJECT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


BACKUP = Path(arg("--backup", str(PROJECT / "Backups" / "Shuriken_pre_restyle_2026-09-18")))
NEW_BLEND = Path(arg("--blend", str(PROJECT / "Assets" / "Shuriken.blend")))
REPORTS = Path(arg("--reports", str(PROJECT / "WorkFiles" / "shuriken")))
FORMS = [f for f in arg("--forms", "four_point,eight_point,square_plate").split(",") if f]
OUT = Path(arg("--out", str(HERE / "regression_restyle.json")))
DIFF_DIR = HERE / "restyle_diff"
RESOLUTION = 0.05e-3          # m per pixel
RASTER_TOLERANCE_PX = 1.5     # a silhouette edge lands on either side of a pixel centre
MESH = {"four_point": "SM_Shuriken_FourPoint", "eight_point": "SM_Shuriken_EightPoint",
        "square_plate": "SM_Shuriken_SquarePlate"}
SIZE_KEYS = ("across_mm", "across_y_mm", "thickness_mm", "tip_radius_mm", "hole_across_flats_mm", "arm_width_mm",
             "hub_radius_mm", "corner_to_corner_mm", "side_chord_mm", "sagitta_mm")


def append_mesh(blend: Path, name: str):
    """Append the object ``name`` from ``blend`` (never opened, never saved) and return its mesh."""
    with bpy.data.libraries.load(str(blend.resolve()), link=False) as (src, dst):
        if name not in src.objects:
            raise KeyError(f"{name} not in {blend}: {sorted(src.objects)[:12]}")
        dst.objects = [name]
    obj = dst.objects[0]
    mesh = obj.data
    mesh.name = f"{name}__{blend.parent.name}"
    bpy.data.objects.remove(obj)
    return mesh


def triangles(mesh):
    mesh.calc_loop_triangles()
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    tris = np.array([[co[i] for i in t.vertices] for t in mesh.loop_triangles])
    normals = np.array([t.normal[:] for t in mesh.loop_triangles])
    return co, tris, normals


def rasterise(tris_xy, origin, size):
    """Boolean mask (rows = y up... stored row 0 = min y) of the union of triangles, pixel centres."""
    mask = np.zeros((size, size), dtype=bool)
    for tri in tris_xy:
        p = (tri - origin) / RESOLUTION
        x0, y0 = np.floor(p.min(0)).astype(int)
        x1, y1 = np.ceil(p.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = p
        d = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        if abs(d) < 1e-12:
            continue
        w0 = ((bx - xs) * (cy - ys) - (by - ys) * (cx - xs)) / d
        w1 = ((cx - xs) * (ay - ys) - (cy - ys) * (ax - xs)) / d
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        mask[ys[inside].astype(int), xs[inside].astype(int)] = True
    return mask


def boundary(mask):
    inner = mask.copy()
    for axis in (0, 1):
        inner &= np.roll(mask, 1, axis=axis) & np.roll(mask, -1, axis=axis)
    return mask & ~inner


def kd_of(points_px):
    tree = KDTree(len(points_px))
    for i, (r, c) in enumerate(points_px):
        tree.insert((float(c), float(r), 0.0), i)
    tree.balance()
    return tree


def max_distance_px(query_mask, ref_boundary_mask, where=None):
    """Largest distance (px) from a set pixel of ``query_mask`` to the nearest ``ref_boundary_mask`` pixel.

    ``where`` (a dict) receives the worst pixel's (row, col).
    """
    qs = np.argwhere(query_mask)
    if not len(qs):
        return 0.0
    tree = kd_of(np.argwhere(ref_boundary_mask))
    worst, worst_at = 0.0, None
    for r, c in qs:
        _co, _i, dist = tree.find((float(c), float(r), 0.0))
        if dist > worst:
            worst, worst_at = dist, (int(r), int(c))
    if where is not None:
        where["at"] = worst_at
    return float(worst)


def save_diff(path: Path, both, old_only, new_only, top_diff):
    h, w = both.shape
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    rgb[both] = (0.35, 0.35, 0.35)
    rgb[top_diff & both] = (0.55, 0.55, 0.45)
    rgb[old_only] = (0.9, 0.15, 0.1)
    rgb[new_only] = (0.1, 0.85, 0.2)
    img = bpy.data.images.new(path.stem, w, h, alpha=False)
    img.pixels.foreach_set(np.concatenate([rgb, np.ones((h, w, 1), np.float32)], -1).ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def compare(form: str) -> dict:
    name = MESH[form] + "_LOD0"
    old_mesh = append_mesh(BACKUP / "Shuriken.blend", name)
    new_mesh = append_mesh(NEW_BLEND, name)
    co_old, tris_old, n_old = triangles(old_mesh)
    co_new, tris_new, n_new = triangles(new_mesh)
    half_t = float(co_new[:, 2].max())
    extent = max(np.abs(co_old[:, :2]).max(), np.abs(co_new[:, :2]).max()) + 1e-3
    size = int(np.ceil(2 * extent / RESOLUTION))
    origin = np.array([-extent, -extent])
    sil_old = rasterise(tris_old[:, :, :2], origin, size)
    sil_new = rasterise(tris_new[:, :, :2], origin, size)
    top_old = rasterise(tris_old[(n_old[:, 2] > 0.999) & (tris_old[:, :, 2].min(1) > half_t - 1e-7)][:, :, :2], origin, size)
    top_new = rasterise(tris_new[(n_new[:, 2] > 0.999) & (tris_new[:, :, 2].min(1) > half_t - 1e-7)][:, :, :2], origin, size)
    xor = sil_old ^ sil_new
    outline_old = boundary(sil_old)
    outline_new = boundary(sil_new)
    sil_dev_px = max(max_distance_px(sil_old & ~sil_new, outline_new), max_distance_px(sil_new & ~sil_old, outline_old))
    top_xor = top_old ^ top_new
    where = {}
    top_band_px = max_distance_px(top_xor, outline_new, where)     # how far the top-face change reaches inward
    worst_mm = None
    if where.get("at"):
        r, c = where["at"]
        worst_mm = [round(float(origin[0] + (c + 0.5) * RESOLUTION) * 1e3, 3),
                    round(float(origin[1] + (r + 0.5) * RESOLUTION) * 1e3, 3)]
    new_report = json.loads((REPORTS / f"{form}_report.json").read_text(encoding="utf-8"))
    old_report = json.loads((BACKUP / f"{form}_report.json").read_text(encoding="utf-8"))
    build_to = new_report["build_to"]
    chamfer_mm = build_to.get("chamfer_width_mm") or new_report["measured"].get("chamfer_width_measured_mm") \
        or new_report["measured"].get("facet_plan_width_mm")
    old_facet_mm = old_report["build_to"].get("bevel_offset_mm", 0.0)
    # The band is W wide along every edge, but at a CONCAVE corner (a star's arm root, where the
    # arm edge meets the notch arc) both chamfers run through the corner and meet in a mitre, so
    # the plate corner sits farther from the outline corner than W: the distance between the
    # outline's root corner and the plate's (the generator's X_ROOT stations), as a ground inside
    # corner does.  Convex-only outlines (the senban) stay at W.
    density = new_report.get("density") or {}
    reach_mm = chamfer_mm
    if "X_ROOT_mm" in density and "X_ROOT_PLATE_mm" in density:
        reach_mm = float(np.hypot(density["X_ROOT_mm"] - density["X_ROOT_PLATE_mm"], chamfer_mm))
    band_limit_px = (max(reach_mm, old_facet_mm) * 1e-3) / RESOLUTION + RASTER_TOLERANCE_PX
    sizes = {}
    for key in SIZE_KEYS:
        a, b = old_report["measured"].get(key), new_report["measured"].get(key)
        if a is not None and b is not None:
            sizes[key] = {"backup": a, "new": b, "equal": a == b}
    DIFF_DIR.mkdir(parents=True, exist_ok=True)
    save_diff(DIFF_DIR / f"{form}_outline_diff.png", sil_old & sil_new, sil_old & ~sil_new, sil_new & ~sil_old, top_xor)
    result = {
        "mesh": name,
        "resolution_mm_per_px": RESOLUTION * 1e3,
        "raster_size_px": size,
        "silhouette": {
            "pixels_backup": int(sil_old.sum()), "pixels_new": int(sil_new.sum()),
            "xor_pixels": int(xor.sum()), "xor_fraction": round(float(xor.sum() / max(1, (sil_old | sil_new).sum())), 8),
            "max_deviation_mm": round(sil_dev_px * RESOLUTION * 1e3, 4),
            "tolerance_mm": round(RASTER_TOLERANCE_PX * RESOLUTION * 1e3, 4),
            "unchanged": bool(sil_dev_px <= RASTER_TOLERANCE_PX),
        },
        "top_face": {
            "pixels_backup": int(top_old.sum()), "pixels_new": int(top_new.sum()),
            "xor_pixels": int(top_xor.sum()),
            "change_reaches_inward_mm": round(top_band_px * RESOLUTION * 1e3, 4),
            "change_worst_at_mm": worst_mm,
            "chamfer_width_mm": chamfer_mm,
            "mitre_reach_mm": round(reach_mm, 4),
            "allowed_band_mm": round(band_limit_px * RESOLUTION * 1e3, 4),
            "note": ("the flat top plate shrinks by the chamfer band (the backup's facet reached only the taper); "
                     "every changed pixel must lie within the chamfer width of the outline, or within the mitre "
                     "reach at a concave root corner where the arm and notch chamfers meet"),
            "within_chamfer_band": bool(top_band_px <= band_limit_px),
        },
        "sizes": sizes,
        "sizes_unchanged": all(v["equal"] for v in sizes.values()),
        "diff_png": str(DIFF_DIR / f"{form}_outline_diff.png"),
    }
    result["passed"] = bool(result["silhouette"]["unchanged"] and result["top_face"]["within_chamfer_band"]
                            and result["sizes_unchanged"])
    bpy.data.meshes.remove(old_mesh)
    bpy.data.meshes.remove(new_mesh)
    return result


def main() -> int:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    out = {"backup": str(BACKUP), "blend": str(NEW_BLEND), "forms": {}}
    for form in FORMS:
        out["forms"][form] = compare(form)
        r = out["forms"][form]
        print(f"[outline] {form}: silhouette max dev {r['silhouette']['max_deviation_mm']} mm "
              f"(xor {r['silhouette']['xor_pixels']} px), top-face change reaches {r['top_face']['change_reaches_inward_mm']} mm "
              f"(allowed {r['top_face']['allowed_band_mm']}), sizes unchanged {r['sizes_unchanged']} -> "
              f"{'PASS' if r['passed'] else 'FAIL'}")
    out["passed"] = all(r["passed"] for r in out["forms"].values())
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("OUTLINE_REGRESSION", "PASS" if out["passed"] else "FAIL", OUT)
    return 0 if out["passed"] else 1


if __name__ == "__main__":
    code = main()
    if code:
        raise SystemExit(code)
