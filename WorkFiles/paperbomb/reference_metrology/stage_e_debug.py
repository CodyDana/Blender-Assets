# -*- coding: utf-8 -*-
"""Stage E: debug diagrams drawn PURELY FROM MEASURED NUMBERS onto a blank
canvas. No reference pixels are read, copied, traced or derived here."""
import os, json, math

HERE = os.path.dirname(os.path.abspath(__file__))
DEBUG = os.path.join(HERE, "debug")
os.makedirs(DEBUG, exist_ok=True)
RAW = json.load(open(os.path.join(HERE, "typography_raw.json"), encoding="utf-8"))["measurements"]
V1, V2, OA = RAW["V1"], RAW["V2"], RAW["OURS_ATLAS"]
CW, CH = 70.0, 156.0

BANNER = ('<rect x="0" y="0" width="{w}" height="26" fill="#b00020"/>'
          '<text x="8" y="18" font-family="monospace" font-size="14" fill="#fff">'
          'DEBUG - NEVER SHIP - measured geometry only, no reference artwork</text>')


def box(o, cls, label=None):
    if not o:
        return ""
    b = o
    s = ('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" class="%s"/>'
         % (b["x0_mm"], b["y0_mm"], b["w_mm"], b["h_mm"], cls))
    if label:
        s += ('<text x="%.3f" y="%.3f" class="lbl">%s</text>'
              % (b["x0_mm"], b["y0_mm"] - 0.6, label))
    return s


def layout_svg():
    S = 4.2
    w, h = CW * S + 320, CH * S + 60
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
             'viewBox="0 0 %d %d">' % (w, h, w, h),
             '<rect width="100%" height="100%" fill="#faf7f2"/>',
             BANNER.format(w=w),
             '<style>'
             '.ref{fill:none;stroke:#1a6fd4;stroke-width:0.22}'
             '.our{fill:none;stroke:#d4381a;stroke-width:0.22;stroke-dasharray:1.2 0.8}'
             '.tag{fill:#fff;stroke:#333;stroke-width:0.3}'
             '.lbl{font-family:monospace;font-size:1.6px;fill:#1a6fd4}'
             '.k{font-family:monospace;font-size:13px;fill:#222}'
             '.kh{font-family:monospace;font-size:14px;fill:#000;font-weight:bold}'
             '</style>',
             '<g transform="translate(30,40) scale(%f)">' % S,
             '<rect x="0" y="0" width="%.2f" height="%.2f" class="tag"/>' % (CW, CH)]
    pairs = [("centre_glyph", "bbox", "bao"),
             ("flame_emblem", "bbox", "flame"),
             ("column_upper_left", "bbox", "UL"),
             ("column_upper_right", "bbox", "UR"),
             ("column_lower_right", "bbox", "LR"),
             ("column_lower_centre", "bbox", "LC"),
             ("seal_big", "outer_bbox", "sealB"),
             ("seal_small", "outer_bbox", "sealS")]
    for key, bk, lab in pairs:
        r = (V2 if key.startswith("column") else V1).get(key)
        o = OA.get(key)
        if r:
            parts.append(box(r.get(bk), "ref", lab))
        if o:
            parts.append(box(o.get(bk), "our"))
    for src, cls in ((V1, "ref"), (OA, "our")):
        rg = src["ring"]
        cx, cy = rg["centre"]["x_mm"], rg["centre"]["y_mm"]
        for rr in (rg["r_inner_mean_mm"], rg["r_outer_mean_mm"]):
            parts.append('<ellipse cx="%.3f" cy="%.3f" rx="%.3f" ry="%.3f" class="%s"/>'
                         % (cx, cy, rr, rr, cls))
        parts.append('<circle cx="%.3f" cy="%.3f" r="0.6" class="%s"/>' % (cx, cy, cls))
    parts.append("</g>")
    y = 60
    parts.append('<text x="%d" y="%d" class="kh">blue solid = reference</text>' % (CW * S + 48, y))
    y += 18
    parts.append('<text x="%d" y="%d" class="kh">red dashed = our shipped map</text>' % (CW * S + 48, y))
    y += 26
    rows = [
        ("bao box mm", "%.2f x %.2f" % (V1["centre_glyph"]["bbox"]["w_mm"],
                                        V1["centre_glyph"]["bbox"]["h_mm"]),
         "%.2f x %.2f" % (OA["centre_glyph"]["bbox"]["w_mm"], OA["centre_glyph"]["bbox"]["h_mm"])),
        ("bao w/h", "%.3f" % V1["centre_glyph"]["bbox"]["w_over_h"],
         "%.3f" % OA["centre_glyph"]["bbox"]["w_over_h"]),
        ("ring centre mm", "%.2f, %.2f" % (V1["ring"]["centre"]["x_mm"], V1["ring"]["centre"]["y_mm"]),
         "%.2f, %.2f" % (OA["ring"]["centre"]["x_mm"], OA["ring"]["centre"]["y_mm"])),
        ("ring band mm", "%.2f" % V1["ring"]["core_thickness_mm"]["mean"],
         "%.2f" % OA["ring"]["core_thickness_mm"]["mean"]),
        ("flame box mm", "%.2f x %.2f" % (V1["flame_emblem"]["bbox"]["w_mm"],
                                          V1["flame_emblem"]["bbox"]["h_mm"]),
         "%.2f x %.2f" % (OA["flame_emblem"]["bbox"]["w_mm"], OA["flame_emblem"]["bbox"]["h_mm"])),
        ("UL axis x mm", "%.2f (V2)" % V2["column_upper_left"]["axis"]["axis_mean_x_mm"],
         "%.2f" % OA["column_upper_left"]["axis"]["axis_mean_x_mm"]),
        ("UR axis x mm", "%.2f (V2)" % V2["column_upper_right"]["axis"]["axis_mean_x_mm"],
         "%.2f" % OA["column_upper_right"]["axis"]["axis_mean_x_mm"]),
    ]
    for name, a, b in rows:
        parts.append('<text x="%d" y="%d" class="k">%-14s %-14s %s</text>'
                     % (CW * S + 48, y, name, a, b))
        y += 17
    parts.append("</svg>")
    p = os.path.join(DEBUG, "DEBUG-NEVER-SHIP_layout_boxes.svg")
    open(p, "w", encoding="utf-8").write("\n".join(parts))
    return p


def ring_svg():
    w, h = 980, 560
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">' % (w, h),
             '<rect width="100%" height="100%" fill="#faf7f2"/>', BANNER.format(w=w),
             '<style>.ax{stroke:#888;stroke-width:1;fill:none}'
             '.v1{stroke:#1a6fd4;stroke-width:1.6;fill:none}'
             '.our{stroke:#d4381a;stroke-width:1.6;fill:none}'
             '.t{font-family:monospace;font-size:12px;fill:#222}'
             '.h{font-family:monospace;font-size:14px;font-weight:bold;fill:#000}</style>']
    for i, (field, title, ymax) in enumerate(
            (("core_thick", "ring band thickness vs angle (mm)", 9.0),
             ("cover", "radial ink coverage vs angle (0-1)", 1.05))):
        ox, oy, pw, ph = 60, 70 + i * 240, 860, 190
        parts.append('<text x="%d" y="%d" class="h">%s</text>' % (ox, oy - 8, title))
        parts.append('<rect x="%d" y="%d" width="%d" height="%d" class="ax"/>' % (ox, oy, pw, ph))
        for src, cls in ((V1, "v1"), (OA, "our")):
            pr = src["ring"]["profile_36"]
            pts = []
            for j, p in enumerate(pr):
                x = ox + (p["deg"] + 180.0) / 360.0 * pw
                v = p.get("thick" if field == "core_thick" else "cover") or 0.0
                y = oy + ph - min(v / ymax, 1.0) * ph
                pts.append("%.1f,%.1f" % (x, y))
            parts.append('<polyline points="%s" class="%s"/>' % (" ".join(pts), cls))
        for d in (-180, -90, 0, 90, 180):
            x = ox + (d + 180) / 360.0 * pw
            parts.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" class="ax"/>' % (x, oy, x, oy + ph))
            parts.append('<text x="%.1f" y="%d" class="t">%d deg</text>' % (x - 12, oy + ph + 14, d))
        parts.append('<text x="%d" y="%d" class="t">0 = 3 oclock, +90 = straight down '
                     '(y points down), so increasing angle is clockwise on screen</text>'
                     % (ox, oy + ph + 30))
    y = 530
    parts.append('<text x="60" y="%d" class="t">blue = reference V1  |  red = our shipped map  '
                 '|  V1 one radial mode, brush FWHM %.2f mm  |  ours one radial mode, brush '
                 'FWHM %.2f mm</text>'
                 % (y, V1["ring"]["lap_verdict"]["brush_width_from_fwhm_mm"],
                    OA["ring"]["lap_verdict"]["brush_width_from_fwhm_mm"]))
    parts.append("</svg>")
    p = os.path.join(DEBUG, "DEBUG-NEVER-SHIP_ring_profile.svg")
    open(p, "w", encoding="utf-8").write("\n".join(parts))
    return p


def stroke_svg():
    rows = [
        ("centre 爆", V1["centre_glyph"]["stroke"], OA["centre_glyph"]["stroke"]),
        ("flame emblem", V1["flame_emblem"]["stroke"], OA["flame_emblem"]["stroke"]),
        ("UL cell 0", V2["column_upper_left"]["glyphs"][0]["stroke"],
         OA["column_upper_left"]["glyphs"][0]["stroke"]),
        ("UR cell 0", V2["column_upper_right"]["glyphs"][0]["stroke"],
         OA["column_upper_right"]["glyphs"][0]["stroke"]),
        ("LC cell 0", V2["column_lower_centre"]["glyphs"][0]["stroke"],
         OA["column_lower_centre"]["glyphs"][0]["stroke"]),
    ]
    w, h = 900, 120 + len(rows) * 74
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">' % (w, h),
             '<rect width="100%" height="100%" fill="#faf7f2"/>', BANNER.format(w=w),
             '<style>.t{font-family:monospace;font-size:12px;fill:#222}'
             '.h{font-family:monospace;font-size:14px;font-weight:bold}'
             '.b1{fill:#1a6fd4;opacity:.85}.b2{fill:#d4381a;opacity:.85}'
             '.ax{stroke:#bbb;stroke-width:1}</style>',
             '<text x="30" y="52" class="h">stroke-width span per element: p05 - median - p95 - max '
             '(mm). blue = reference, red = ours</text>']
    SC = 92.0
    for i, (name, a, b) in enumerate(rows):
        oy = 78 + i * 74
        parts.append('<text x="30" y="%d" class="t">%s</text>' % (oy + 12, name))
        for j, (s, cls) in enumerate(((a, "b1"), (b, "b2"))):
            yy = oy + j * 24
            x0 = 150 + s["stroke_p05_ridge_mm"] * SC
            x1 = 150 + s["stroke_p95_ridge_mm"] * SC
            parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="12" class="%s"/>'
                         % (x0, yy, max(x1 - x0, 1.0), cls))
            parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="ax"/>'
                         % (150 + s["stroke_max_mm"] * SC, yy - 2,
                            150 + s["stroke_max_mm"] * SC, yy + 14))
            parts.append('<text x="%.1f" y="%.1f" class="t">p05 %.2f  med %.2f  p95 %.2f  max %.2f'
                         '   thick/thin %.1f</text>'
                         % (150 + s["stroke_max_mm"] * SC + 8, yy + 10,
                            s["stroke_p05_ridge_mm"], s["stroke_median_ridge_mm"],
                            s["stroke_p95_ridge_mm"], s["stroke_max_mm"],
                            s.get("thick_thin_ratio") or 0))
    parts.append('<text x="30" y="%d" class="t">the reference p05 values sit at its own 2-pixel '
                 'limit, so every reference thick/thin ratio here is a LOWER bound</text>' % (h - 18))
    parts.append("</svg>")
    p = os.path.join(DEBUG, "DEBUG-NEVER-SHIP_stroke_ladder.svg")
    open(p, "w", encoding="utf-8").write("\n".join(parts))
    return p


for fn in (layout_svg, ring_svg, stroke_svg):
    print("wrote", fn())

open(os.path.join(DEBUG, "README-DEBUG-NEVER-SHIP.txt"), "w", encoding="utf-8").write(
    "DEBUG - NEVER SHIP\n"
    "==================\n\n"
    "Everything in this folder is a diagnostic drawing produced from the NUMBERS in\n"
    "../typography.json. Nothing here was traced, sampled, cut out, thresholded or in\n"
    "any other way derived from the pixels of References/PaperBomb/*.png.\n\n"
    "These files must never be read by a build, packed into an asset, or shipped.\n"
    "They exist so a human can check that the metrology found the right elements.\n")
print("wrote README")
