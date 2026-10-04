"""SAYA_DESIGN_COMPARE.png: the design sheet's row 2 (saya) and row 3 (sheathed) next to the SHIPPED saya (and the
shipped katana seated by the exported Holster) rendered at the sheet's own scale and framing (saya_render --set sheet:
renders of the re-imported exported FBX with their baked maps), silhouette overlays with IoU and edge error, and the
measured dimensions (saya_measured.json) and fit gates (saya_fit_verify.json) against katana_spec.json.

    blender -b --factory-startup --python Scripts/Katana/saya_compare.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[1]
from katana_tex import write_png  # noqa: E402

RDIR = ROOT / "Renders" / "Katana"
SHEET = ROOT / "WorkFiles" / "katana" / "KATANA_DESIGN_SHEET.png"
OUT = ROOT / "WorkFiles" / "katana" / "SAYA_DESIGN_COMPARE.png"
MEAS = ROOT / "WorkFiles" / "katana" / "saya_measured.json"
VER = ROOT / "WorkFiles" / "katana" / "saya_fit_verify.json"
CROPS = {"B": (1695, 2000, 5400, 2990), "B_end": (5700, 2140, 6060, 2960),
         "C": (330, 3040, 5400, 4320), "C_end": (5690, 3470, 6110, 4310)}
LABEL = {"B": "row 2 saya: top (from the ha) + side (omote, edge up), 1:1",
         "B_end": "row 2 end (from the kojiri)", "C": "row 3 sheathed: top + side, 1:1",
         "C_end": "row 3 end (from the tip)"}


def load_rgba(path):
    img = bpy.data.images.load(str(path))
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    a = px.reshape(h, w, 4)[::-1].copy()
    bpy.data.images.remove(img)
    return a


def shift_or(x, d, axis):
    y = np.zeros_like(x)
    if axis == 0:
        y[d:] = x[:-d]
        y[:-d] |= x[d:]
    else:
        y[:, d:] = x[:, :-d]
        y[:, :-d] |= x[:, d:]
    return y


def morph(m, r, op):
    out = m.copy()
    for ax in (0, 1):
        acc = out.copy()
        for d in range(1, r + 1):
            if op == "erode":
                s1 = np.ones_like(out)
                s2 = np.ones_like(out)
                if ax == 0:
                    s1[d:] = out[:-d]
                    s2[:-d] = out[d:]
                else:
                    s1[:, d:] = out[:, :-d]
                    s2[:, :-d] = out[:, d:]
                acc &= s1 & s2
            else:
                acc |= shift_or(out, d, ax)
        out = acc
    return out


def opening(m, r):
    return morph(morph(m, r, "erode"), r, "dilate")


def boundary(m):
    return m & ~morph(m, 1, "erode")


def edge_err(a, b, ppm):
    """mean / p95 distance (mm) from a's boundary pixels to b's boundary (brute force on a coarse sample)."""
    pa = np.argwhere(boundary(a))
    pb = np.argwhere(boundary(b))
    if len(pa) == 0 or len(pb) == 0:
        return None, None
    pa = pa[:: max(1, len(pa) // 3000)]
    d = []
    for i in range(0, len(pa), 200):
        q = pa[i:i + 200]
        dd = np.sqrt(((q[:, None, :] - pb[None, ::2, :]) ** 2).sum(-1)).min(axis=1)
        d.append(dd)
    d = np.concatenate(d) / ppm
    return float(d.mean()), float(np.percentile(d, 95))


def text_image(lines, width, line_h=34, size=22, pad=20):
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
        cu = bpy.data.curves.new("t", "FONT")
        red = line.startswith("!")
        cu.body = line[1:] if red else line
        cu.size = size
        ob = bpy.data.objects.new("t", cu)
        ob.location = (pad, -pad - (i + 0.8) * line_h, 0)
        ob.color = (0.7, 0.05, 0.05, 1) if red else (0.05, 0.05, 0.05, 1)
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
    tmp = ROOT / "WorkFiles" / "katana" / "saya_build" / "_txt.png"
    sc.render.filepath = str(tmp)
    with bpy.context.temp_override(scene=sc):
        bpy.ops.render.render(write_still=True, scene=sc.name)
    a = load_rgba(tmp)[..., :3]
    tmp.unlink()
    return a


def resize(a, f):
    h, w = a.shape[:2]
    h2, w2 = h // f, w // f
    return a[:h2 * f, :w2 * f].reshape(h2, f, w2, f, -1).mean(axis=(1, 3))


def pad_to(a, W, val=1.0):
    if a.shape[1] >= W:
        return a[:, :W]
    return np.concatenate([a, np.full((a.shape[0], W - a.shape[1], 3), val, np.float32)], 1)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sheet = load_rgba(SHEET)[..., :3]
    stats, rows = {}, []
    W = 3900
    for name, (x0, y0, x1, y1) in CROPS.items():
        sc_ = sheet[y0:y1, x0:x1]
        ours = load_rgba(RDIR / f"saya_sheet_{name}.png")[..., :3]
        om = load_rgba(RDIR / f"saya_sheet_{name}_mask.png")[..., 3] > 0.5
        lum = sc_ @ np.array([0.2126, 0.7152, 0.0722])
        sm = opening(lum < 0.85, 3)
        om = opening(om, 3)
        inter, union = (sm & om).sum(), (sm | om).sum()
        iou = float(inter / max(union, 1))
        e_mean, e_p95 = edge_err(om, sm, 5.0)
        stats[name] = {"iou": round(iou, 4), "edge_err_mean_mm": round(e_mean, 3), "edge_err_p95_mm": round(e_p95, 3),
                       "sheet_px": int(sm.sum()), "ours_px": int(om.sum())}
        ov = np.ones(sm.shape + (3,), np.float32)
        ov[sm & ~om] = (0.85, 0.15, 0.15)
        ov[om & ~sm] = (0.1, 0.55, 0.9)
        ov[sm & om] = (0.35, 0.35, 0.35)
        f = {"B": 2, "C": 3}.get(name, 1)
        panels = [resize(sc_, f), resize(ours, f), resize(ov, f)]
        hdr = text_image([f"{LABEL[name]}:  sheet | shipped FBX render | overlay (grey both, red sheet only, blue "
                          f"ours only).  IoU {iou:.4f}, edge error mean {e_mean:.2f} mm, p95 {e_p95:.2f} mm"], W, size=24)
        rows.append(hdr)
        if name in ("B", "C"):
            gap = np.ones((panels[0].shape[0], 30, 3), np.float32)
            rows.append(pad_to(np.concatenate([panels[0], gap, panels[1]], 1).astype(np.float32), W))
            rows.append(np.ones((10, W, 3), np.float32))
            rows.append(pad_to(panels[2].astype(np.float32), W))
        else:
            gap = np.ones((panels[0].shape[0], 30, 3), np.float32)
            rows.append(pad_to(np.concatenate([panels[0], gap, panels[1], gap, panels[2]], 1).astype(np.float32), W))
        rows.append(np.ones((20, W, 3), np.float32))
    meas = json.load(open(MEAS))
    ver = json.load(open(VER))
    k = meas["kurikata"]
    pairs = ver["pairs"].values()
    lines = [
        "MEASURED on the exported SM_Katana_Saya.fbx (sword frame, mm)                          measured            spec",
        f"length along the blade's mune arc (mouth face -> kojiri end)                      {meas['length_on_mune_arc']:<20}{meas['spec_length_on_mune_arc']}",
        f"depth x width just inside the mouth round (s 0.7)                                 {meas['mouth_depth_x_width']}    {meas['spec_mouth_depth_x_width_at_s']}  (40.0 x 27.5 at s 0.3)",
        f"depth x width where the kojiri round-over starts (s 718.09)                       {meas['kojiri_depth_x_width_at_round_start']}    {meas['spec_kojiri_depth_x_width_at_round_start']}",
        f"outer mune line (rho from the blade's mune)                                       {meas['mune_line_rho']:<20}{meas['spec_mune_line_rho']}",
        f"koiguchi / kojiri lengths (to the seam groove centre)                             {meas['koiguchi_length']} / {meas['kojiri_length']}       20 / 28",
        f"kurikata from the mouth, along x radial x proud, offset toward the ha             {k['from_mouth']}, {k['along']} x {k['radial']} x {k['proud_of_face']}, {k['radial_centre_offset_from_section_centre']}   80, 30 x 11 x 9, 3",
        "   (radial 12.2 incl. the two 0.6 mm shitodome flanges; the horn knob is 11.0)",
        f"tip to cavity end                                                                 {meas['tip_to_cavity_end_mm']:<20}10",
        "FIT GATES on the exported bytes (katana seated by the exported Holster socket), 9 LOD pairs:",
        f"  intersections max {max(p['F1_intersections'] for p in pairs)}; blade clearance min {min(p['F2_min_clearance_blade_mm'] for p in pairs):.3f} (>= 0.3); "
        f"habaki clearance min {min(p['F3_min_clearance_habaki_mm'] for p in pairs):.3f} (0.1-0.5); hilt clearance min {min(p['F4_min_clearance_hilt_mm'] for p in pairs):.3f} (>= 0.2)",
        f"  enclosure failures {sum(p['F5_enclosure_failures'] for p in pairs)}; arc draw about DrawPivot: {list(pairs)[0]['F6_draw_steps']} steps of 0.156 deg, max intersections {max(p['F6_draw_max_intersections'] for p in pairs)}",
        f"  visible seat gap (front / edge-on) max {ver['F7_visible_seat_gap']['katana_LOD0']['front_x']['max_gap_mm']} / {ver['F7_visible_seat_gap']['katana_LOD0']['side_y']['max_gap_mm']} mm (<= 2; design 0.3)",
        f"  walls LOD0: koiguchi pocket {ver['F8_walls']['saya_LOD0']['min_wall_koiguchi_pocket_mm']} (>= 2.3), body {ver['F8_walls']['saya_LOD0']['min_wall_body_mm']} (>= 3.0); mouth-face rim after the 0.4 round {ver['mouth_face_rim_min_mm']}",
        f"  straight slide along the Mouth socket (info): collides after {ver['F12_straight_draw_info']['first_collision_after_mm']} mm - a curved blade draws along its arc",
        f"  overall: {'PASS' if ver['pass'] else 'FAIL'};  LOD triangles {meas['lod_triangles']};  FBX sha256 {meas['fbx_sha256'][:16]}...",
    ]
    rows.append(text_image(lines, W, line_h=34, size=22))
    img = np.vstack([pad_to(r.astype(np.float32), W) for r in rows])
    write_png(OUT, (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
    json.dump({"silhouettes": stats, "measured": str(MEAS), "verify": str(VER)},
              open(OUT.with_suffix(".json"), "w"), indent=1)
    print("SAYA_COMPARE", json.dumps(stats), flush=True)


main()
