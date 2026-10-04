"""KATANA_DESIGN_COMPARE.png: the design sheet's views next to the SHIPPED katana rendered at the same scale and
framing (renders of the re-imported exported FBX with its baked maps), silhouette overlays with IoU, and the
measured dimensions (katana_measured.json, measured on the exported FBX) against katana_spec.json.

    blender -b --factory-startup --python Scripts/Katana/katana_compare.py -- [--renders DIR] [--prefix fbx_sheet]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import katana_spec as K  # noqa: E402
import katana_render_crops as CR  # noqa: E402
from katana_tex import write_png  # noqa: E402

ROOT = HERE.parents[1]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d):
    return argv[argv.index(n) + 1] if n in argv else d


RDIR = Path(arg("--renders", str(ROOT / "Renders" / "Katana")))
PREFIX = arg("--prefix", "fbx_sheet")
OUT = Path(arg("--out", str(ROOT / "WorkFiles" / "katana" / "KATANA_DESIGN_COMPARE.png")))
SHEET = ROOT / "WorkFiles" / "katana" / "KATANA_DESIGN_SHEET.png"
MEAS = ROOT / "WorkFiles" / "katana" / "katana_measured.json"


def load_rgba(path):
    img = bpy.data.images.load(str(path))
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    a = px.reshape(h, w, 4)[::-1].copy()          # top-down rows
    bpy.data.images.remove(img)
    return a


def to_srgb8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def opening(m, r):
    """binary opening with a (2r+1) square: removes annotation strokes thinner than the kernel."""
    def erode(x):
        y = x.copy()
        for d in range(1, r + 1):
            y[d:] &= x[:-d]
            y[:-d] &= x[d:]
        z = y.copy()
        for d in range(1, r + 1):
            z[:, d:] &= y[:, :-d]
            z[:, :-d] &= y[:, d:]
        return z

    def dilate(x):
        y = x.copy()
        for d in range(1, r + 1):
            y[d:] |= x[:-d]
            y[:-d] |= x[d:]
        z = y.copy()
        for d in range(1, r + 1):
            z[:, d:] |= y[:, :-d]
            z[:, :-d] |= y[:, d:]
        return z
    return dilate(erode(m))


def resize(a, f):
    """box downscale by an integer factor f."""
    h, w = a.shape[:2]
    h2, w2 = h // f, w // f
    a = a[:h2 * f, :w2 * f]
    return a.reshape(h2, f, w2, f, -1).mean(axis=(1, 3))


def text_image(lines, width, line_h=34, size=22, pad=20, cols=None):
    """Render text lines with Blender (Workbench, black on white) -> numpy RGB (top-down)."""
    sc = bpy.data.scenes.new("txt")
    H = pad * 2 + line_h * len(lines)
    cam_d = bpy.data.cameras.new("tc")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = float(max(width, H))
    cam = bpy.data.objects.new("tc", cam_d)
    sc.collection.objects.link(cam)
    cam.location = (width / 2, -H / 2, 100)
    sc.camera = cam
    for i, line in enumerate(lines):
        parts = line if isinstance(line, (list, tuple)) else [line]
        x = pad
        for j, txt in enumerate(parts):
            cu = bpy.data.curves.new("t", "FONT")
            cu.body = txt
            cu.size = size
            ob = bpy.data.objects.new("t", cu)
            ob.location = ((cols[j] if cols else x), -pad - (i + 0.8) * line_h, 0)
            ob.color = (0.05, 0.05, 0.05, 1) if not txt.startswith("!") else (0.7, 0.05, 0.05, 1)
            if txt.startswith("!"):
                cu.body = txt[1:]
            sc.collection.objects.link(ob)
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "FLAT"
    sc.display.shading.color_type = "OBJECT"
    w = bpy.data.worlds.new("tw")
    w.color = (1, 1, 1)
    sc.world = w
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x = width
    sc.render.resolution_y = H
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    tmp = ROOT / "WorkFiles" / "katana" / "build" / "_txt.png"
    sc.render.filepath = str(tmp)
    bpy.context.window_manager  # noqa
    with bpy.context.temp_override(scene=sc):
        bpy.ops.render.render(write_still=True, scene=sc.name)
    a = load_rgba(tmp)[..., :3]
    tmp.unlink()
    return a


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sheet = load_rgba(SHEET)[..., :3]
    meas = json.load(open(MEAS))
    views = [("side", CR.SIDE_CROP, 5.0), ("top", CR.TOP_CROP, 5.0), ("end", CR.END_CROP, 5.0),
             ("tsuka2x", CR.TSUKA2_CROP, 10.0), ("kissaki3x", CR.KISSAKI3_CROP, 15.0)]
    stats = {}
    panels = {}
    for name, crop, ppm in views:
        x0, y0, x1, y1 = crop
        sc_ = sheet[y0:y1, x0:x1]
        ours = load_rgba(RDIR / f"{PREFIX}_{name}.png")[..., :3]
        om = load_rgba(RDIR / f"{PREFIX}_{name}_mask.png")[..., 3] > 0.5
        lum = sc_ @ np.array([0.2126, 0.7152, 0.0722])
        sm = lum < 0.85
        r = 3 if ppm <= 5 else 4
        sm_o = opening(sm, r)
        om_o = opening(om, r)
        inter = (sm_o & om_o).sum()
        union = (sm_o | om_o).sum()
        iou = inter / max(union, 1)
        # per-column extent difference (side-type views): top and bottom silhouette rows where both exist
        cols = np.where(sm_o.any(0) & om_o.any(0))[0]
        dt, db = [], []
        for c in cols:
            a, b = np.where(sm_o[:, c])[0], np.where(om_o[:, c])[0]
            dt.append(abs(a.min() - b.min()))
            db.append(abs(a.max() - b.max()))
        err = np.array(dt + db) / ppm if cols.size else np.array([0.0])
        stats[name] = {"iou": round(float(iou), 4), "edge_err_mean_mm": round(float(err.mean()), 3),
                       "edge_err_p95_mm": round(float(np.percentile(err, 95)), 3), "px_per_mm": ppm}
        ov = np.ones(sc_.shape, np.float32)
        ov[sm_o & ~om_o] = (0.85, 0.15, 0.1)
        ov[om_o & ~sm_o] = (0.1, 0.45, 0.9)
        ov[sm_o & om_o] = (0.62, 0.62, 0.62)
        panels[name] = (sc_, ours, ov)
    W = 2500
    rows = []

    def label(txt):
        return text_image([txt], W, line_h=40, size=26, pad=6)

    def fit(a, w):
        f = max(1, int(round(a.shape[1] / w)))
        return resize(a, f) if f > 1 else a

    def pad_to(a, w):
        if a.shape[1] >= w:
            return a[:, :w]
        out = np.ones((a.shape[0], w, 3), np.float32)
        out[:, :a.shape[1]] = a
        return out

    rows.append(text_image(["BASIC KATANA - DESIGN SHEET vs THE SHIPPED SM_Katana (exported FBX re-imported, baked maps, Cycles)",
                            "Same scale and framing as the sheet. Overlays: grey = both, red = sheet only, blue = ours only "
                            "(annotation strokes removed by a 3-4 px opening on both). Numbers measured on the exported bytes."],
                           W, line_h=40, size=26))
    for name, title in (("side", "1  SIDE (omote, edge up), sheet row 1, 1:1 at 5 px/mm"),
                        ("top", "1  TOP (from the ha), sheet row 1, 1:1"),):
        s_, o_, ov = panels[name]
        st = stats[name]
        rows.append(label(f"{title}:  sheet / ours / overlay   IoU {st['iou']:.3f}, silhouette edge error mean "
                          f"{st['edge_err_mean_mm']:.2f} mm, p95 {st['edge_err_p95_mm']:.2f} mm"))
        for a in (s_, o_, ov):
            rows.append(pad_to(fit(a, W), W))
    # details: tsuka 2:1 and kissaki 3:1 and end, side by side
    s_, o_, ov = panels["tsuka2x"]
    st = stats["tsuka2x"]
    rows.append(label(f"4a  TSUKA WRAP 2:1 (10 px/mm): sheet / ours / overlay   IoU {st['iou']:.3f}"))
    for a in (s_, o_, ov):
        a2 = fit(a, 1340)
        rows.append(pad_to(a2, W))
    ks, ko, kov = panels["kissaki3x"]
    es, eo, eov = panels["end"]
    rows.append(label(f"4c  KISSAKI 3:1: sheet / ours / overlay (IoU {stats['kissaki3x']['iou']:.3f})      "
                      f"END VIEW 1:1: sheet / ours / overlay (IoU {stats['end']['iou']:.3f})"))
    k3 = [fit(a, 400) for a in (ks, ko, kov)]
    e3 = [fit(a, 300) for a in (es, eo, eov)]
    hh = max(k3[0].shape[0], e3[0].shape[0] * 1)
    strip = np.ones((hh, W, 3), np.float32)
    x = 0
    for a in k3:
        strip[:a.shape[0], x:x + a.shape[1]] = a
        x += a.shape[1] + 10
    x += 40
    for a in e3:
        strip[:a.shape[0], x:x + a.shape[1]] = a
        x += a.shape[1] + 10
    rows.append(strip)
    # ---- measured table
    b = meas["blade"]
    it = meas["ito"]
    d4 = it["diamond_4_omote"]

    def row(name, m, s_, tol=0.5):
        ok = abs(m - s_) <= tol
        return [name, f"{m:.2f}", f"{s_:.2f}", f"{m - s_:+.2f}", ("ok" if ok else "!OFF")]
    table = [["dimension (mm)", "measured", "spec", "diff", ""],
             row("nagasa (chord, mune-machi to tip)", b["nagasa_chord"], b["spec_nagasa"]),
             row("sori", b["sori"], b["spec_sori"]),
             row("mune arc radius (circle fit)", b["mune_arc_fit"]["radius"], K.R),
             row("motohaba", b["motohaba"], b["spec_motohaba"]),
             row("sakihaba (at the yokote)", b["sakihaba_at_yokote"], b["spec_sakihaba"]),
             row("motokasane", b["motokasane"], b["spec_motokasane"]),
             row("sakikasane", b["sakikasane"], b["spec_sakikasane"]),
             row("kissaki (on the mune arc, yokote found by the taper break)", b["kissaki_on_mune_arc"], b["spec_kissaki"]),
             row("tip x", b["tip_xz"][0], b["spec_tip_xz"][0]),
             row("tip z", b["tip_xz"][1], b["spec_tip_xz"][1]),
             row("habaki length", meas["habaki"]["length"], meas["habaki"]["spec_length"]),
             row("tsuba diameter", meas["tsuba"]["diameter"], meas["tsuba"]["spec"]),
             row("tsuka (fuchi top - kashira end)", meas["tsuka"]["length"], meas["tsuka"]["spec"]),
             row("overall along Z (tip - kashira)", meas["overall"]["along_z_tip_to_kashira"], meas["overall"]["spec"]),
             row("ito pitch (mean, omote crossings)", it["pitch_mean"], it["spec_pitch"]),
             row("diamond 4 (omote) along", d4["along_mm"], d4["spec_along"]),
             row("diamond 4 (omote) across, open between cords", d4["across_open_mm"], d4["spec_across"], 1.0),
             [f"ito crossings per face: omote {it['crossings']['omote']['count']} (max z err {it['crossings']['omote']['max_abs_err']} mm), "
              f"ura {it['crossings']['ura']['count']} (max z err {it['crossings']['ura']['max_abs_err']} mm); spec 9 + 9, 8 full diamonds; "
              f"edge scallop {it['edge_scallop_ha_mm']} mm (gate >= 1)", "", "", "", ""],
             [f"triangles LOD0/1/2 {meas['lod_triangles']}; hulls {len(meas['hulls'])}; FBX sha256 {meas['fbx_sha256'][:16]}...", "", "", "", ""]]
    for nm, st in stats.items():
        table.append([f"silhouette {nm}: IoU {st['iou']:.4f}, edge error mean {st['edge_err_mean_mm']:.2f} mm / p95 {st['edge_err_p95_mm']:.2f} mm", "", "", "", ""])
    rows.append(text_image(table, W, line_h=36, size=24, cols=[20, 1350, 1600, 1850, 2100]))
    gap = np.ones((14, W, 3), np.float32)
    out = []
    for r_ in rows:
        out.append(pad_to(r_, W))
        out.append(gap)
    img = np.vstack(out)
    write_png(OUT, to_srgb8(img))
    json.dump({"silhouettes": stats, "measured": str(MEAS), "renders": str(RDIR), "prefix": PREFIX},
              open(OUT.with_suffix(".json"), "w"), indent=1)
    print("KAT_COMPARE", json.dumps(stats), flush=True)


main()
