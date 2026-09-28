"""Contact sheet: blade_section_options.png.  Columns PHOTO | CURRENT | A | B | C.
Row 1 the photo pose (render_photo_pose.py, same crop as the photo), row 2 the 3/4 hero pose (render_3q.py) with a blade
zoom, row 3 the true end-on sections (make_sections.py), row 4 a table per column.
The photo is a SHAPE reference used for measurement only: it appears on this WorkFiles diagnostic sheet, never in an asset.
python make_sheet.py  (Python 3.12 with PIL; run collect.py and make_sections.py first)"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DATA = json.loads((HERE / "options_data.json").read_text())
IDS = ["current", "A", "B", "C"]
CW, GUT, LM = 640, 14, 14
W = LM + 5 * (CW + GUT)
BG, INK, SUB, HEAD = (24, 24, 26), (238, 238, 238), (170, 170, 170), (255, 214, 90)
OK, BAD, WARN = (120, 220, 120), (255, 110, 110), (255, 190, 90)
COLC = {"photo": (200, 200, 200), "current": (180, 180, 180), "A": (110, 175, 245), "B": (245, 150, 70), "C": (100, 210, 130)}


def font(size, bold=False):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "segoeui.ttf"):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + name, size)
        except OSError:
            continue
    return ImageFont.load_default()


F_TITLE, F_H, F_L, F_T, F_S = font(34, True), font(24, True), font(18, True), font(17), font(15)
PHOTO_CROP = (228, 52, 448, 250)            # photo px (500 x 333): the blade and the shoulder
ZOOM3Q = (700, 380, 1500, 660)              # 3/4 render px (1600 x 900): the blade


def fit(img, w, h):
    return img.resize((w, h), Image.LANCZOS)


def on_bg(rgba, colour=(96, 92, 86)):
    base = Image.new("RGB", rgba.size, colour)
    base.paste(rgba, mask=rgba.split()[3] if rgba.mode == "RGBA" else None)
    return base


def col_x(i):
    return LM + i * (CW + GUT)


titles = {"photo": "PHOTO (shape reference, measured only)", "current": "CURRENT  (3.10.1 shipped)",
          "A": "A  deeper diamond at 5 mm stock", "B": "B  match the photo ratio", "C": "C  full diamond, 7 mm forged"}
subs = {"photo": "forged replica, tip in bark; face slope 0.21 front (0.15-0.27)",
        "current": "ridge 5.0 mm, 1.5 mm edge flat, 1.1 mm grind",
        "A": "ridge 5.0 held to x 63.6, edge flat 0.6, grind 0.4 mm",
        "B": "ridge 9.0 mm, edge flat 1.5 kept, grind 1.4 mm",
        "C": "ridge 7.0 mm, edge flat 0.3 (faces to the grind), grind 0.15"}

row1_h = int(CW * (PHOTO_CROP[3] - PHOTO_CROP[1]) / (PHOTO_CROP[2] - PHOTO_CROP[0]))
row2_h = int(CW * 900 / 1600)
zoom_h = int(CW * (ZOOM3Q[3] - ZOOM3Q[1]) / (ZOOM3Q[2] - ZOOM3Q[0]))
row3_h = 580
row4_h = 560
top = 150
lab = 34
H = top + 60 + (lab + row1_h) + (lab + row2_h + zoom_h + 6) + (lab + row3_h) + (lab + row4_h) + 60
sheet = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(sheet)
d.text((LM, 16), "Kunai blade section - three options (pick one; nothing in the live pack has changed)", font=F_TITLE, fill=INK)
d.text((LM, 62), "face_slope = (ridge half-thickness - edge half-thickness) / half-width = tan(face angle).  "
                 "ridge_ratio = ridge half-thickness / half-width.  Stations = fraction of the photo's VISIBLE blade from "
                 "the shoulder (0.20 / 0.45 / 0.75 = our x 26.7 / 56.7 / 91.4 mm).", font=F_T, fill=SUB)
d.text((LM, 88), "Every option is a real prototype: a copy of the pack generator with only the section changed, built "
                 "headless (kunai only) with its own bake, gates, FBX and report under WorkFiles/kunai/blade_section/options/.",
       font=F_T, fill=SUB)
d.text((LM, 114), "Figures below are measured on each option's own LOD0 mesh and its own build report.", font=F_T, fill=SUB)

y = top
for i, key in enumerate(["photo"] + IDS):
    d.text((col_x(i), y), titles[key], font=F_H, fill=COLC[key])
    d.text((col_x(i), y + 30), subs[key], font=F_S, fill=SUB)
y += 60

# ---- row 1: photo pose
d.text((LM, y + 6), "ROW 1  the photo's pose (roll 5, axis 23.8 deg, 200 mm lens, photo-like sky and key; same crop as the "
                    "photo).  Look at the contrast between the upper and lower facets: that is the ridge height.",
       font=F_L, fill=HEAD)
y += lab
photo = Image.open(ROOT / "References" / "Kunai" / "kunai_reference2.jpg").convert("RGB").crop(PHOTO_CROP)
sheet.paste(fit(photo, CW, row1_h), (col_x(0), y))
for i, oid in enumerate(IDS, start=1):
    p = HERE / oid / "views" / "photo_pose.png"
    if p.exists():
        im = on_bg(Image.open(p).convert("RGBA"))
        c = tuple(2 * v for v in PHOTO_CROP)
        sheet.paste(fit(im.crop(c), CW, row1_h), (col_x(i), y))
y += row1_h

# ---- row 2: 3/4 hero pose
d.text((LM, y + 6), "ROW 2  the 3/4 diagonal hero (kunai_plain_3q.png's rig: yaw 40, 72 mm, el 29 / az -22, the gallery "
                    "lamps).  Below each: the blade enlarged.  Coat figures are in row 4.", font=F_L, fill=HEAD)
y += lab
# photo column: the photo-measured table as text
pt = ImageDraw.Draw(sheet)
py = y + 6
pt.text((col_x(0), py), "Photo, measured (reconciled, validated method):", font=F_L, fill=INK)
py += 28
pt.text((col_x(0), py), "frac   our x     face_slope (p10-p90)     angle", font=F_S, fill=SUB)
py += 22
for s in DATA["photo"]["stations"]:
    pt.text((col_x(0), py), f"{s['frac_from_shoulder']:.2f}   {s['ours_x_mm']:5.1f}    {s['face_slope']:.3f} "
                            f"({s['face_slope_p10_p90'][0]:.2f}-{s['face_slope_p10_p90'][1]:.2f})      {s['face_angle_deg']:.1f} deg",
            font=F_S, fill=INK)
    py += 21
py += 8
for line in ["Front blade 0.21 (range 0.15-0.27), roughly constant", "from the widest point to the bark: planar facets.",
             "Rear (shoulder to widest) 0.24-0.33: ridge held high.", "Ours today: 0.08-0.10 on the front (2.45x flatter).",
             "", "Method check: read back on our own render at the", "photo's scale 0.98-1.08x the known slope."]:
    pt.text((col_x(0), py), line, font=F_S, fill=SUB)
    py += 20
for i, oid in enumerate(IDS, start=1):
    p = HERE / oid / "views" / "kunai_3q_y40.png"
    if p.exists():
        im = Image.open(p).convert("RGB")
        sheet.paste(fit(im, CW, row2_h), (col_x(i), y))
        sheet.paste(fit(im.crop(ZOOM3Q), CW, zoom_h), (col_x(i), y + row2_h + 6))
y += row2_h + zoom_h + 6

# ---- row 3: sections
d.text((LM, y + 6), "ROW 3  true end-on sections of each option's LOD0 mesh at three stations, to scale (dashed = current; "
                    "magenta = the photo's face angle drawn from the edge)", font=F_L, fill=HEAD)
y += lab
for i, name in enumerate(["overlay"] + IDS):
    p = HERE / "sections" / f"section_{name}.png"
    if p.exists():
        sheet.paste(fit(Image.open(p).convert("RGB"), CW, row3_h), (col_x(i), y))
y += row3_h

# ---- row 4: tables
d.text((LM, y + 6), "ROW 4  what each option changes (build report + mesh; masses at steel 7.85, wood 0.70, tape 0.75 "
                    "g/cm3)", font=F_L, fill=HEAD)
y += lab
cur = DATA["options"]["current"]["extract"]


def st(o, x):
    return next((r for r in o["stations"] if abs(r["x_mm"] - x) < 0.05), None)


def ridge_profile(sec):
    rb = sec.get("RIDGE_BASE", 5.0)
    s = ""
    if sec.get("RIDGE_RAMP"):
        s += f"5.0 at x 5 -> {rb:.1f} at x {sec['RIDGE_RAMP'][1]:g}, "
    else:
        s += f"{rb:.1f} from the shoulder, "
    knots = sec.get("RIDGE_KNOTS") or []
    held = knots[0][0] if knots else 35
    s += f"held to x {held:g}, -> {sec.get('RIDGE_TIP', 1.6):.1f} at x 135"
    return s


for i, oid in enumerate(["photo"] + IDS):
    x0 = col_x(i)
    ty = y + 4
    lines = []
    if oid == "photo":
        lines = [("Reading the table", INK, F_L),
                 ("face_slope at 0.20 / 0.45 / 0.75 of the blade,", SUB, F_S),
                 ("with the ratio to the photo in brackets.", SUB, F_S),
                 ("ridge_ratio = ridge half-thickness / half-width;", SUB, F_S),
                 ("*photo's assumes our 1.5 mm edge (not resolvable).", SUB, F_S),
                 ("", SUB, F_S),
                 ("un-ground steel = the mass-gate basis (no grind);", SUB, F_S),
                 ("its target is the study arithmetic re-run with", SUB, F_S),
                 ("the option's section (plain_calc, copied).", SUB, F_S),
                 ("", SUB, F_S),
                 ("PACK_COAT_ANCHOR: hero p50 0.560 / mean 0.550,", SUB, F_S),
                 ("top 0.430 / 0.424, tolerance 0.05.", SUB, F_S),
                 ("'flat coat' = the ring flats + neck plateau", SUB, F_S),
                 ("(|N.z| >= 0.9995), the anchor plates' orientation.", SUB, F_S),
                 ("", SUB, F_S),
                 ("Gates: every geometry / UV / LOD / hull / qa gate", SUB, F_S),
                 ("ran in each prototype build; failures in red.", SUB, F_S)]
    else:
        o = DATA["options"][oid]
        e = o["extract"]
        sec = o["section"]
        a, b, c = st(o, 26.7), st(o, 56.7), st(o, 91.4)
        fmt = lambda r: f"{r['face_slope']:.3f} ({r['vs_photo']:.2f}x)"
        g = e["grind_width_mm"]
        q3 = o["poses"].get("kunai_3q_y40") or {}
        hero = o["poses"].get("kunai_hero_y-25") or {}
        top_ = o["poses"].get("kunai_top_y0") or {}
        dm = lambda k: f"{e[k] - cur[k]:+.1f}" if oid != "current" else ""
        lines = [
            (f"Ridge: {ridge_profile(sec)}", INK, F_S),
            (f"Edge flat (un-ground) {sec.get('EDGE_T', 1.5):.1f} mm;  grind band {g['at_widest']:.2f} mm at x 35", INK, F_S),
            (f"face_slope {fmt(a)} / {fmt(b)} / {fmt(c)}", INK, F_T),
            (f"front median {o['front_face_slope_median']:.3f}  vs photo 0.215", INK, F_S),
            (f"ridge_ratio {a['ridge_ratio']:.3f} / {b['ridge_ratio']:.3f} / {c['ridge_ratio']:.3f}  (photo* 0.285 / 0.235 / 0.297)",
             INK, F_S),
            (f"Steel un-ground {e['steel_unground_g']:.1f} g {dm('steel_unground_g')}   finished {e['steel_finished_g']:.1f} g",
             INK, F_T),
            (f"Assembled {e['assembled_g']:.1f} g {dm('assembled_g')}   (physics {e['physics']['mass_kg_override']:.4f} kg)",
             INK, F_T),
            (f"Mass gate target {e['mass_target_g']:.2f} g (was 153.02); error {e['mass_error_g']:+.2f} g",
             OK if e["mass_gate_passed"] else BAD, F_S),
            (f"Pivot x {e['pivot_design_x_mm']:.1f} mm;  Unreal COM offset +{e['collision']['unreal_com_nudge_cm'][0]:.2f} cm",
             INK, F_S),
            (f"Blade {e['thickness_mm']:.1f} mm thick; head hull {e['hulls']['UCX_00']['volume_mm3']:.0f} mm3 "
             f"({e['hulls']['UCX_00']['vertices']} v); apex x {e['apex_x_mm']:.1f}", INK, F_S),
            (f"LOD tris {' / '.join(str(t) for t in e['lod_triangles'])};  blade texels {o['texel_blade_px_per_mm']:.2f} px/mm",
             INK, F_S),
            (f"Geometry gates (qa, hulls, UV, LOD, mass, slots): {'all pass' if all(v for k, v in e['gates'].items() if k != 'render_gates') else 'FAIL'}",
             OK if all(v for k, v in e["gates"].items() if k != "render_gates") else BAD, F_S),
        ]
        lr = o.get("lod_ridge_vs_lod0") or {}
        l2 = lr.get("SM_Kunai_Plain_LOD2") or {}
        lines.append((f"LOD2 ridge vs LOD0: {l2.get('max_ridge_thickness_delta_mm', 0):+.2f} mm at x {l2.get('at_x_mm')}"
                      + ("  (needs a 2nd base station)" if abs(l2.get('max_ridge_thickness_delta_mm', 0)) > 0.5 else ""),
                      WARN if abs(l2.get('max_ridge_thickness_delta_mm', 0)) > 0.5 else INK, F_S))
        rg = e["render_gates"]
        lines.append((f"Render gates: top_plate {'pass' if rg['top_plate']['passed'] else 'FAIL'} "
                      f"(coat {rg['top_plate']['p50']:.3f}/{rg['top_plate']['mean']:.3f}), hero_plate "
                      f"{'pass' if rg['hero_plate']['passed'] else 'FAIL'}", OK if rg["passed"] else BAD, F_S))
        kc = e["knife_coat_vs_anchor"]
        lines.append((f"Pack coat vs anchor (end-on hero / top): {kc['hero']['kunai_plain']['p50']['offset']:+.3f} / "
                      f"{kc['top']['kunai_plain']['p50']['offset']:+.3f}  "
                      f"{'PASS' if e['pack_consistency_passed'] else 'FAIL'}", OK if e["pack_consistency_passed"] else BAD, F_S))
        if q3:
            fl = q3.get("flat") or {}
            ft = q3.get("finish_transfer_tilted_minus_flat") or {}
            lines.append((f"3/4 hero coat p50 {q3['coat_p50']:.3f} ({q3['vs_anchor']['p50']:+.3f} vs anchor: FAIL today's rule)"
                          if abs(q3['vs_anchor']['p50']) > 0.05 else
                          f"3/4 hero coat p50 {q3['coat_p50']:.3f} ({q3['vs_anchor']['p50']:+.3f}) pass", WARN, F_S))
            if fl:
                ok = abs(q3["flat_vs_anchor"]["p50"]) <= 0.05 and abs(q3["flat_vs_anchor"]["mean"]) <= 0.05 and (
                    not ft or abs(ft.get("p50", 0)) <= 0.05)
                lines.append((f"  proposed knife rule: flat {fl['p50']:.3f}/{fl['mean']:.3f} ({q3['flat_vs_anchor']['p50']:+.3f})"
                              + (f", finish transfer {ft['p50']:+.3f}" if ft else "") + (" PASS" if ok else " FAIL"),
                              OK if ok else BAD, F_S))
    for text, colour, f in lines:
        d.text((x0, ty), text, font=f, fill=colour)
        ty += 26 if f in (F_T, F_L) else 23
y += row4_h - 60
REC = ("RECOMMENDATION: C.  It reaches 0.87-1.06x of the photo's front face slope at 7.0 mm (the forged replicas' 6.35-8 mm) for "
       "+1.5 g of steel (assembled 164.8 g, now inside the study's plain range), moves the pivot 0.9 mm and passes every "
       "geometry gate.  Its cost is the grind: 1.1 mm -> 0.15 mm (a bright line, not a band).  B is the exact ratio "
       "but 9 mm, +33 g and the pivot 12 mm forward; A is safe but reaches only ~0.7x.")
cut = REC.index("Its cost")
d.text((LM, y - 28), REC[:cut], font=F_L, fill=HEAD)
d.text((LM, y), REC[cut:], font=F_L, fill=HEAD)
d.text((LM, y + 28), "Hero: every option (and today's blade) fails today's coat rule in the 3/4 pose; the principled knife "
                     "rule (flat coat vs the anchor + finish transfer on the tilted faces) passes all four - see OPTIONS.md.",
       font=F_T, fill=SUB)
y += 60
d.text((LM, y + 10), "Recommendation and the full comparison: options/OPTIONS.md.  Sources: options/<id>/report/"
                     "kunai_plain_report.json, <id>/mesh_measure.json, <id>/views/kunai_3q_stats.json, options_data.json.",
       font=F_T, fill=SUB)
sheet.save(HERE / "blade_section_options.png", optimize=True)
print("sheet", sheet.size)
