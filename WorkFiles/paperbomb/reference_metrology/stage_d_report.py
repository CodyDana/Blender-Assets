# -*- coding: utf-8 -*-
"""Stage D: curate typography.json, write TYPE_NOTES.md, draw debug diagrams."""
import sys, os, json, math, hashlib, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
DEBUG = os.path.join(HERE, "debug")
os.makedirs(DEBUG, exist_ok=True)
RAW = json.load(open(os.path.join(HERE, "typography_raw.json"), encoding="utf-8"))
M = RAW["measurements"]
V1, V2, OA, OT = M["V1"], M["V2"], M["OURS_ATLAS"], M["OURS_ART"]

CW, CH = 70.0, 156.0


def g(o, *p, default=None):
    for k in p:
        if not isinstance(o, dict):
            return default
        o = o.get(k)
        if o is None:
            return default
    return o


def pct(ours, ref):
    if ref in (None, 0) or ours is None:
        return None
    return round(100.0 * (ours - ref) / abs(ref), 1)


def sha(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()[:16]
    except Exception:
        return None


FILES = RAW["meta"]["files"]
SNAP = (r"C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/"
        r"70fec35b-8f87-4dbe-ba33-6e5ba8c5d846/scratchpad/snap/T_PaperBomb_BC.snap.png")

# ---------------------------------------------------------------- deltas
D = []


def add(elem, what, ref, ours, unit, matters, refsrc="V1", extra=None, sev=0):
    d = dict(element=elem, quantity=what, reference=ref, reference_from=refsrc,
             ours=ours, unit=unit, matters=matters)
    if isinstance(ref, (int, float)) and isinstance(ours, (int, float)):
        d["delta"] = round(ours - ref, 3)
        d["delta_pct"] = pct(ours, ref)
        d["severity_score"] = abs(d["delta_pct"] or 0) if sev == 0 else sev
    else:
        d["severity_score"] = sev
    if extra:
        d.update(extra)
    D.append(d)


cg1, cg2, cgo = V1["centre_glyph"], V2["centre_glyph"], OA["centre_glyph"]
r1, r2, ro = V1["ring"], V2["ring"], OA["ring"]
f1, f2, fo = V1["flame_emblem"], V2["flame_emblem"], OA["flame_emblem"]

add("centre_glyph_bao", "ink bounding-box width", cg1["bbox"]["w_mm"], cgo["bbox"]["w_mm"], "mm",
    "the character is the whole point of the tag; 18% narrow reads as a timid, "
    "undersized 爆 rattling inside the ring")
add("centre_glyph_bao", "ink bounding-box height", cg1["bbox"]["h_mm"], cgo["bbox"]["h_mm"], "mm",
    "same, on the other axis")
add("centre_glyph_bao", "width / ring mean diameter",
    g(cg1, "in_ring", "glyph_bbox_w_over_ring_diam"),
    g(cgo, "in_ring", "glyph_bbox_w_over_ring_diam"), "ratio",
    "the reference glyph is WIDER than the ring (1.046) and bursts out of it; ours "
    "is safely inside it")
add("centre_glyph_bao", "ink area / ring inner area",
    g(cg1, "in_ring", "glyph_area_over_ring_inner_area"),
    g(cgo, "in_ring", "glyph_area_over_ring_inner_area"), "ratio",
    "how much of the ring's field the character actually blackens")
add("centre_glyph_bao", "clear space to ring, median",
    g(cg1, "in_ring", "clear_space_mm", "median"),
    g(cgo, "in_ring", "clear_space_mm", "median"), "mm",
    "the reference nearly touches the ring all round; ours floats")
add("centre_glyph_bao", "stroke thick/thin ratio (p95/p05)",
    g(cg1, "stroke", "thick_thin_ratio"), g(cgo, "stroke", "thick_thin_ratio"), "ratio",
    "brush modulation. The reference runs from hairline dry-brush filaments to a "
    "7.3 mm belly; ours is nearly a constant-width pen")
add("centre_glyph_bao", "widest stroke", g(cg1, "stroke", "stroke_max_mm"),
    g(cgo, "stroke", "stroke_max_mm"), "mm", "the fattest part of the brush")
add("centre_glyph_bao", "edge roughness (perimeter / 0.25 mm-smoothed perimeter)",
    g(cg1, "stroke", "perimeter_over_smoothed"), g(cgo, "stroke", "perimeter_over_smoothed"),
    "ratio", "this is the 'too vector-smooth' test, and the centre glyph fails it")
add("centre_glyph_bao", "ink-gap from the 火 radical to the body",
    g(cg1, "satellite_components", default=[{}])[0].get("ink_gap_to_main_mm"),
    g(cgo, "satellite_components", default=[{}])[0].get("ink_gap_to_main_mm"), "mm",
    "in the reference the radical all but touches the body (0.75 mm) and their boxes "
    "overlap by 8.7 mm; ours is a detached island", sev=120,
    extra=dict(reference_bbox_overlap_x_mm=g(cg1, "satellite_components", default=[{}])[0].get("bbox_overlap_x_mm"),
               ours_bbox_overlap_x_mm=g(cgo, "satellite_components", default=[{}])[0].get("bbox_overlap_x_mm"),
               reference_component_count=cg1["n_components"],
               ours_component_count=cgo["n_components"],
               ours_second_satellite_gap_mm=(g(cgo, "satellite_components", default=[{}, {}])[1].get("ink_gap_to_main_mm")
                                             if len(g(cgo, "satellite_components", default=[])) > 1 else None)))
add("ring", "core band thickness, mean", g(r1, "core_thickness_mm", "mean"),
    g(ro, "core_thickness_mm", "mean"), "mm",
    "a thin ring reads as drawn with a pen, not swung with a loaded brush")
add("ring", "brush width from the radial FWHM", g(r1, "lap_verdict", "brush_width_from_fwhm_mm"),
    g(ro, "lap_verdict", "brush_width_from_fwhm_mm"), "mm",
    "the single most direct measure of how fat the brush was")
add("ring", "radial ink coverage (how solidly the band is inked)",
    g(r1, "radial_ink_coverage", "mean"), g(ro, "radial_ink_coverage", "mean"), "fraction",
    "the reference band is only 59% inked across its width - that IS the dry brush. "
    "Ours is 90% solid, so it reads as a filled shape")
add("ring", "number of radial modes (laps)", g(r1, "lap_verdict", "n_radial_modes"),
    g(ro, "lap_verdict", "n_radial_modes"), "count",
    "one mode = one lap. The shipped map is already a single lap; the older art map "
    "in WorkFiles still shows two", sev=5,
    extra=dict(stale_workfiles_art_modes=g(OT, "ring", "lap_verdict", "n_radial_modes"),
               stale_workfiles_art_brush_mm=g(OT, "ring", "lap_verdict", "brush_width_from_fwhm_mm")))
add("ring", "centre x", g(r1, "centre", "x_mm"), g(ro, "centre", "x_mm"), "mm",
    "the ring sits right of where the reference puts it")
add("ring", "centre y", g(r1, "centre", "y_mm"), g(ro, "centre", "y_mm"), "mm",
    "and lower")
add("ring", "ellipse axis ratio (minor/major)", g(r1, "ellipse", "axis_ratio"),
    g(ro, "ellipse", "axis_ratio"), "ratio",
    "ours is a more pronounced oval than the reference's")
add("ring", "major-axis tilt off vertical",
    round(abs(abs(g(r1, "ellipse", "major_axis_deg")) - 90.0), 2),
    round(abs(abs(g(ro, "ellipse", "major_axis_deg")) - 90.0), 2), "deg",
    "the reference ring is visibly canted; ours is almost upright, which looks machined")
add("ring", "wet-to-dry contrast between the two ends of the lap",
    g(r1, "lap_ends", "wet_to_dry_contrast"), g(ro, "lap_ends", "wet_to_dry_contrast"),
    "fraction", "the reference's arc ends drier than it starts, which is what tells the "
    "eye the brush was moving; ours ends WETTER than it starts, so the stroke reads "
    "directionless", sev=40,
    extra=dict(reference_wetter_end=g(r1, "lap_ends", "wetter_end"),
               ours_wetter_end=g(ro, "lap_ends", "wetter_end"),
               reference_travel=g(r1, "lap_ends", "implied_travel"),
               ours_travel=g(ro, "lap_ends", "implied_travel")))
add("flame_emblem", "ink area", f1["ink_area_mm2"], fo["ink_area_mm2"], "mm2",
    "the reference emblem is an airy five-stroke mark; ours is a heavy solid blob")
add("flame_emblem", "ink fill of its own bounding box", f1["fill_of_bbox"], fo["fill_of_bbox"],
    "fraction", "same, normalised for size")
add("flame_emblem", "widest stroke", g(f1, "stroke", "stroke_max_mm"),
    g(fo, "stroke", "stroke_max_mm"), "mm", "ours is twice as fat at its fattest")
add("flame_emblem", "separate strokes (connected components)", f1["n_components"],
    fo["n_components"], "count",
    "the reference is five strokes with paper between them; ours is one welded mass",
    sev=80)
add("flame_emblem", "fully enclosed holes", f1["n_enclosed_holes"], fo["n_enclosed_holes"],
    "count", "the reference's curl stays open to the outside; ours closes nine pockets",
    sev=60)
add("flame_emblem", "bounding-box width", f1["bbox"]["w_mm"], fo["bbox"]["w_mm"], "mm",
    "REFUTES the '13% narrow' claim - the width matches")
add("flame_emblem", "bounding-box height", f1["bbox"]["h_mm"], fo["bbox"]["h_mm"], "mm",
    "ours is the one that is too tall")
add("flame_emblem", "mirror symmetry IoU about its own axis",
    g(f1, "mirror_symmetry", "best_iou"), g(fo, "mirror_symmetry", "best_iou"), "ratio",
    "the reference is the MORE symmetric of the two; ours is lopsided")
add("flame_emblem", "edge roughness", g(f1, "stroke", "perimeter_over_smoothed"),
    g(fo, "stroke", "perimeter_over_smoothed"), "ratio",
    "REFUTES 'too vector-smooth' for the emblem - ours is rougher, not smoother")
add("flame_emblem", "empty disc at the heart (eye radius)",
    g(f1, "spiral", "eye_radius_mm"), g(fo, "spiral", "eye_radius_mm"), "mm",
    "our spiral's eye is more than twice as open")

for key, chars, refsrc in (("column_upper_left", "火遁術", "V2"),
                           ("column_upper_right", "爆炎陣", "V2"),
                           ("column_lower_right", "焼尽", "V2"),
                           ("column_lower_centre", "瞬業", "V2")):
    ref = (V2 if refsrc == "V2" else V1).get(key)
    our = OA.get(key)
    if not ref or not our:
        continue
    add(key + " (" + chars + ")", "column axis x", g(ref, "axis", "axis_mean_x_mm"),
        g(our, "axis", "axis_mean_x_mm"), "mm",
        "this is the 'columns pulled inboard' claim, measured", refsrc=refsrc,
        extra=dict(also_vs_V1=g(V1.get(key) or {}, "axis", "axis_mean_x_mm")))
    add(key + " (" + chars + ")", "glyph cell width, first cell",
        ref["glyphs"][0]["bbox"]["w_mm"], our["glyphs"][0]["bbox"]["w_mm"], "mm",
        "our column characters are set far too small", refsrc=refsrc)
    add(key + " (" + chars + ")", "gap between cells (first gap)",
        (ref["gap_mm"] or [None])[0], (our["gap_mm"] or [None])[0], "mm",
        "reference characters touch or nearly touch down the column; ours are spaced "
        "like a word processor", refsrc=refsrc, sev=70)
    add(key + " (" + chars + ")", "ink area, first cell",
        ref["glyphs"][0]["ink_area_mm2"], our["glyphs"][0]["ink_area_mm2"], "mm2",
        "weight on the page", refsrc=refsrc)

sb1, sbo = V1["seal_big"], OA["seal_big"]
ss1, sso = V1["seal_small"], OA["seal_small"]
add("seal_big", "outer frame width", sb1["outer_bbox"]["w_mm"], sbo["outer_bbox"]["w_mm"], "mm",
    "our big seal is oversized")
add("seal_big", "outer frame height", sb1["outer_bbox"]["h_mm"], sbo["outer_bbox"]["h_mm"], "mm",
    "same")
add("seal_big", "structure: separate outline rect + inset solid block", 2, 1, "count",
    "the reference draws a 1.07 mm outline rectangle and then an inset solid block "
    "2.1 mm inside it; ours is one mass with no inset block", sev=90,
    extra=dict(reference_outline_rule_mm=1.071,
               reference_block_mm=[13.664, 22.125],
               reference_inset_mm=[2.07, 2.19],
               ours_pieces=[p.get("role") for p in sbo.get("pieces", [])]))
add("seal_big", "red fill of the outer box", sb1["red_fill_of_outer_bbox"],
    sbo["red_fill_of_outer_bbox"], "fraction", "ours prints thinner and more broken")
add("seal_small", "outer frame width", ss1["outer_bbox"]["w_mm"], sso["outer_bbox"]["w_mm"],
    "mm", "our small seal box is too big")
add("seal_small", "outer frame height", ss1["outer_bbox"]["h_mm"], sso["outer_bbox"]["h_mm"],
    "mm", "same")
add("seal_small", "frame rule thickness", 0.691,
    (sso.get("pieces") or [{}])[0].get("implied_rule_thickness_mm"), "mm",
    "our seal outline is drawn with a finer pen than the reference's")
add("seal_small", "火 glyph width", 6.50, 4.74, "mm",
    "the seal text is far too small for its box")
add("seal_small", "火 glyph height", 6.18, 4.80, "mm", "same")
add("seal_small", "gap between 火 and 道", 1.24, 3.33, "mm",
    "reference seal text is packed tight; ours is airy")

for side, refv, ourv, note in (
        ("left border rule x", 4.088, 3.923, "our rule sits further out"),
        ("right border rule x", 65.24, 65.999, "and further out on this side too"),
        ("top border rule y", 6.739, 6.426, "and higher")):
    add("border_rule", side, refv, ourv, "mm", note)
add("border_rule", "number of parallel rules per side", 1, 2, "count",
    "the reference frame is ONE thin rule (0.22-0.25 mm) plus corner ornament; ours "
    "draws a double rule", sev=55,
    extra=dict(reference_left_rules=[r["x_mm"] for r in g(V1, "border_rule", "left", default=[])],
               ours_left_rules=[r["x_mm"] for r in g(OA, "border_rule", "left", default=[])],
               ours_top_rules=[r["y_mm"] for r in g(OA, "border_rule", "top", default=[])]))

D.sort(key=lambda d: -(d.get("severity_score") or 0))

# ------------------------------------------------- V1 / V2 disagreements
DIS = [
    dict(what="raster aspect of the tag itself",
         v1="tag 624.9 x 1388.5 px, aspect 0.4500 (card 70/156 = 0.4487, so V1 is true to 0.3%)",
         v2="tag 278 x 643 px, aspect 0.4323; V2 is a non-uniform resize of V1, stretched "
            "3.8% vertically (px/mm 3.971 across, 4.122 down)",
         follow="V1",
         why="fractions of the tag are unaffected (a resize preserves them, and the big "
             "seal lands within 0.004 of V1), but ANY aspect ratio or stroke width read "
             "off V2 in pixels is 3.8% wrong unless you use its two different px/mm. "
             "All V2 numbers in this file already use the separate x and y scales."),
    dict(what="V2 is cropped at the bottom",
         v1="full tag, bottom edge at row 1448 of 1536",
         v2="the paper still occupies 75.3% of full width in the LAST canvas row (652); "
            "matching that width ratio against V1's bottom chamfer profile puts the true "
            "bottom edge about 2.3 px (0.55 mm) below the canvas",
         follow="V1",
         why="V2's tag height is under-measured by ~0.36%, so every V2 y-fraction in this "
             "file is ~0.4% too large. That is below the noise for layout work but it is "
             "why V2 must not be used to set the card's aspect."),
    dict(what="the side columns themselves",
         v1="pseudo-glyphs: the upper-left column is a 63.7 mm string of marks running "
            "y 10.45-74.12 mm, only 8.74 mm wide, and there is an extra lower-LEFT mark "
            "group at x 7.28-15.90, y 100.07-114.11 mm that V2 does not have",
         v2="real kanji: 火遁術 in three ~13-15 mm cells over y 10.19-51.92 mm, 爆炎陣 "
            "likewise; no lower-left group",
         follow="V2",
         why="V2 is the brief for WHICH characters go WHERE. V1's columns are 46% longer "
             "and half the width, so copying V1's column extent would be copying its "
             "pseudo-glyph filler."),
    dict(what="position of the small 火道 seal",
         v1="x 54.66-63.50 mm, y 123.09-140.84 mm (8.85 x 17.75 mm)",
         v2="x 54.89-64.71 mm, y 130.28-147.02 mm (9.82 x 16.74 mm) - 6.6 mm LOWER and "
            "1.2 mm further right",
         follow="V1",
         why="V1 already carries real 火道 kanji here, so V2's edit gave no new text "
             "information for this element, and V1 is 2.2x the resolution. V2's box also "
             "runs to 0.5 mm of the border rule, which is why its bbox is wider."),
    dict(what="the lower-centre column's vertical placement",
         v1="ink y 112.42-145.22 mm",
         v2="ink y 109.42-141.20 mm - about 3.4 mm higher",
         follow="V2",
         why="this is a text slot and V2 is authoritative for text placement; the 瞬業 "
             "pair needs the extra room at the bottom for the diamond ornament, which "
             "both versions put at y 145.3-149.0 mm."),
    dict(what="the flame emblem's height",
         v1="23.41 x 23.36 mm (w/h 1.002)",
         v2="23.92 x 21.84 mm (w/h 1.095) - 6.5% shorter",
         follow="V1",
         why="the width agrees to 2%; the height does not, because V2's 2.2x coarser "
             "raster loses the thin tongue tips at the top. Ink AREA agrees to within "
             "0.8% (163.3 vs 164.6 mm2), which confirms it is a resolution artefact and "
             "not an edit."),
    dict(what="stroke modulation you can actually measure",
         v1="centre glyph thick/thin p95/p05 = 22.6, thinnest resolved filament 0.22 mm "
            "(2 px, i.e. at the resolution limit)",
         v2="the same glyph measures 11.0, thinnest 0.49 mm (2 px at V2's scale)",
         follow="V1",
         why="both numbers are floored by their own pixel grid, so the TRUE ratio is at "
             "least 22.6 and probably higher. Treat 22.6 as a lower bound and never "
             "quote V2's 11.0 as the target."),
]

# ---------------------------------------------------------------- output
out = dict(
    meta=dict(
        role="typography and stroke metrologist",
        generated=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        tool="WorkFiles/paperbomb/reference_metrology/{pbmetro,pbtag,pbelem,stage_c_measure,"
             "stage_d_report}.py run in Blender 5.2 python with numpy "
             + RAW["meta"]["tool"].split("numpy ")[-1],
        legal="MEASUREMENT ONLY. Nothing in this study writes, saves or derives any pixel "
              "of the reference guides. Every output is a number, a ratio or a written "
              "description. The debug diagrams under debug/ are drawn from these numbers "
              "onto a blank canvas and contain no reference imagery; they are labelled "
              "DEBUG - NEVER SHIP.",
        coordinate_convention=RAW["meta"]["coordinate_convention"],
        colour_convention=RAW["meta"]["colour_convention"],
        ink_threshold_rule=RAW["meta"]["ink_threshold_rule"],
        rectification_applied=dict(
            V1=dict(rotation_deg=g(V1, "rectification", "rotation_deg_applied"),
                    keystone_vertical_deg=g(V1, "rectification", "keystone_vertical_convergence_deg"),
                    keystone_horizontal_deg=g(V1, "rectification", "keystone_horizontal_convergence_deg"),
                    width_taper_pct=g(V1, "rectification", "width_taper_pct"),
                    verdict="V1 is square to the pixel grid: 0.001 deg rotation, both keystone "
                            "convergences under 0.02 deg, width taper 0.07%. The homography "
                            "applied is therefore a scale-only normalisation."),
            V2=dict(rotation_deg=g(V2, "rectification", "rotation_deg_applied"),
                    keystone_vertical_deg=g(V2, "rectification", "keystone_vertical_convergence_deg"),
                    keystone_horizontal_deg=g(V2, "rectification", "keystone_horizontal_convergence_deg"),
                    width_taper_pct=g(V2, "rectification", "width_taper_pct"),
                    verdict="V2 is also square (0.010 deg), but it is anisotropically scaled "
                            "(3.8% taller per unit width than V1) and clipped ~2.3 px at the "
                            "bottom. Both are corrected for in this file."),
            OURS=dict(rotation_deg=g(OA, "rectification", "rotation_deg_applied"),
                      verdict="the shipped atlas's front-card UV island was located from its "
                              "grain/deckle edge energy: 901.3 x 2015.0 px, aspect 0.4473 "
                              "against the true 0.4487, so the island is isotropic to 0.3% "
                              "and no anisotropy correction was needed."),
        ),
    ),
    sources=dict(
        V1=dict(path=FILES["V1"], role="layout/style reference, high resolution, "
                                       "PSEUDO-glyph side columns",
                sha256_16=sha(FILES["V1"]), rectified_px=V1["rectified_px"],
                px_per_mm=[V1["px_per_mm_x"], V1["px_per_mm_y"]]),
        V2=dict(path=FILES["V2"], role="layout/style reference, authoritative for WHICH text "
                                       "appears WHERE, 2.2x lower resolution",
                sha256_16=sha(FILES["V2"]), rectified_px=V2["rectified_px"],
                px_per_mm=[V2["px_per_mm_x"], V2["px_per_mm_y"]]),
        OURS_ATLAS=dict(path=FILES["OURS_ATLAS"],
                        measured_from=SNAP,
                        note="the build was re-exporting throughout this study, so the shipped "
                             "map was snapshotted and every OURS number comes from that one "
                             "frozen copy",
                        snapshot_sha256_16=sha(SNAP),
                        snapshot_of_mtime="2026-09-19T22:12:49 local",
                        rectified_px=OA["rectified_px"],
                        px_per_mm=[OA["px_per_mm_x"], OA["px_per_mm_y"]]),
        OURS_ART_STALE=dict(path=FILES["OURS_ART"],
                            note="WorkFiles/paperbomb/art/paperbomb_front_bc.png is from "
                                 "19:30, while Scripts/props/props_lib/paperbomb_art.py was "
                                 "last edited 22:06 and the atlas re-exported at 22:12 and "
                                 "again at 22:31. The WorkFiles art maps are STALE and "
                                 "measurably different from the shipped map (side columns "
                                 "~3 mm further out, ring showing two radial modes instead "
                                 "of one). Do not review our build from them."),
    ),
    reference_measurements=dict(V1=V1, V2=V2),
    our_build=dict(OURS_ATLAS=OA, OURS_ART_STALE=OT),
    v1_v2_disagreements=DIS,
    deltas_worst_first=D,
    uncertainties=[
        "The reference's thinnest strokes are at its own pixel limit: V1's 0.224 mm p05 is "
        "exactly 2 px. Every thick/thin ratio quoted for the reference is therefore a LOWER "
        "bound - the real brush went finer than the guide can show.",
        "The shipped atlas was re-exported at 22:12 and again at 22:31 while this study ran. "
        "All OURS numbers describe the 22:12 export (sha in sources). Re-measure before "
        "acting if the build has moved on.",
        "The atlas card rect was found from grain/deckle edge energy, not from the UV data. "
        "Three thresholds agreed within 1.7 px on width and 4 px on height, so the card "
        "scale is good to about +-0.15 mm; a systematic error there would scale all OURS mm "
        "numbers by the same small factor and would NOT explain any of the large deltas.",
        "The flame's spiral turn count is not reliably automatable on an open curl: the "
        "reference's curl escapes to the outside (0 enclosed holes), so ray-band counting "
        "gives a median of 1 band with a tail out to 5. The eye radius (largest empty disc "
        "in the emblem's core) is the robust number: 1.25 mm reference, 2.78 mm ours.",
        "V1 shows a lower-LEFT mark group (x 7.28-15.90, y 100.07-114.11 mm) that V2 drops "
        "and our build does not have. Whether to reinstate it is a design call, not a "
        "metrology one; V2 being authoritative for text placement argues for leaving it out.",
        "Seal 'device' area counts every paper island inside the inked block, so it mixes "
        "the drawn flame with the seal's wear/mottle. The stroke statistics for the device "
        "are the safer comparison.",
    ],
    raw_file="typography_raw.json",
)
p = os.path.join(HERE, "typography.json")
with open(p, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print("wrote", p, os.path.getsize(p))
