# sm_m20: assemble WorkFiles/SnowFlower/v4/sheath_spec.json from the stage outputs (sm_s*.json) + the hand reads below
import sys, os, json, hashlib, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sm_lib import *
J = lambda n: json.load(open(os.path.join(HERE, n)))
s00, s01, s02, s04, s05 = J("sm_s00.json"), J("sm_s01.json"), J("sm_s02.json"), J("sm_s04.json"), J("sm_s05.json")
s09, s10, s11, s12, s13, s14, s15, s16, s16b, s17 = (J(n) for n in ("sm_s09.json", "sm_s10.json", "sm_s11.json", "sm_s12.json", "sm_s13.json", "sm_s14.json", "sm_s15.json", "sm_s16.json", "sm_s16b.json", "sm_s17.json"))
prof = np.array(s01["profile"]); TOP, BOT = s01["top"], s01["bottom"]; LPX = BOT - TOP  # 1465
edge = {int(r[0]): (int(r[1]), int(r[2])) for r in prof}
K = 0.687e-3  # DESIGNED scale, metres per reference px (see fit section)
def t(y): return round((y - TOP) / LPX, 4)
def u(y, x):
    l, r = edge[int(round(y))]; return round((x - (l + r) / 2) / ((r - l) / 2), 3)
def W(y): l, r = edge[int(y)]; return r - l + 1
def mm(px): return round(px * K * 1000, 1)
rows = []
def row(sec, name, value, tol, status, method, **extra):
    d = dict(section=sec, row=name, value=value, tolerance=tol, status=status, method=method); d.update(extra); rows.append(d)

M = "MEASURED"; I = "INFERRED"; D = "DESIGNED"; V = "MEASURED (visual read on zoomed crops, pixel-grid ticks)"
# ---- 0 instrument
row("0 reference", "file", "References/SnowFlower/SnowFlower_sheath_reference.png", "-", M, "sm_m00", sha256=s00["sheath"]["sha256"], size=[s00["sheath"]["w"], s00["sheath"]["h"]], backdrop_lum=0.994)
row("0 reference", "view", "orthographic-looking front view, sheath vertical, mouth up; top face of the mouth collar visible as a thin ellipse (camera slightly above); no shadow", "-", I, "sm_m01 + crops")
# ---- 1 overall
row("1 overall", "length_px (mouth-collar top row 31 to chape point row 1496)", LPX + 1, "+-2 px", M, "sm_m01 flood-fill silhouette, lum<0.92")
row("1 overall", "centre_x_px", 505.5, "+-1.5", M, "sm_m01 per-row centre")
row("1 overall", "axis lean", "-0.12 deg (centre 506.9 at top -> 504.5 at tip = 2.4 px drift over the length): reads straight", "straight: total centre drift <= 3 px (0.2 % of length)", M, "sm_m01 line fit rows 470-1200")
row("1 overall", "max width_px (throat lateral plates, row 89)", 147, "+-2", M, "sm_m01")
row("1 overall", "length / body width below throat", round((LPX + 1) / 97, 2), "+-0.3", M, "1466 / 97")
row("1 overall", "length / max width", round((LPX + 1) / 147, 2), "+-0.2", M, "1466 / 147")
# ---- 2 body taper + section
taper = [(y, W(y), t(y), round(W(y) / 97, 3)) for y in (170, 250, 340, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1250, 1292)]
row("2 body", "body width profile [row, px, t, width/97]", taper, "+-2 px per row", M, "sm_m01 (rows 287-321 are the mid band; 169-286 and 322+ are lacquer body)")
row("2 body", "body width under throat (rows 169-286)", 97, "+-2", M, "sm_m01; constant 97 px")
row("2 body", "body width at chape collar (rows 1250-1292)", 72, "+-2", M, "sm_m01")
row("2 body", "taper", "linear 96 px (row 322) -> 72 px (row 1250): -0.0258 px/row, symmetric (left edge slope +0.0104, right -0.0146 px/row); ratio 0.742", "ratio 0.74 +-0.03, symmetric +-0.005 px/row", M, "sm_m01 edge line fits")
row("2 body", "section - front face width", "0.51 of silhouette width (facet lines at u = -0.52 and +0.51); the facet lines taper with the silhouette (constant u)", "u +-0.04", M, "sm_m03 metal-masked median lum across width: dark groove + highlight at u -0.53/-0.50 and +0.50/+0.53")
row("2 body", "section - visible faces", "3 faces + bright rims: flat front face (u -0.51..+0.51), two chamfer faces (u 0.51..~0.92) brighter than the front face (median lum 0.21-0.25 vs 0.13-0.20), and a 2-4 px bright rim at each silhouette edge (median lum 0.44) = narrow side faces / rounded arrises catching light", "-", M, "sm_m02/m03 profiles + crop_facets.png")
row("2 body", "section - shape", "flattened octagon: front face 50 % of width, chamfers 21 % each in projection, narrow side faces 4 % each; back = mirror of front", "-", D, "front view cannot show depth; octagon is the simplest solid with the measured front-view facets")
row("2 body", "section - depth (thickness)", "22 mm at the throat -> 17 mm at the chape collar (depth/width 0.33); chamfer planes meet the side faces at 35-40 % of depth", "depth >= cavity + 2 x 2.5 mm wall", D, "not visible in the reference; set by the fit (section 9)")
# ---- 3 throat
row("3 throat", "rows", "31-167 (137 px = 9.3 % of length)", "+-2 px", M, "sm_m06 + crop_throat4.png")
row("3 throat", "top collar ring (mouth)", "rows 31-40; outer width 63-64 px (0.66 of body width); its top face shows as an ellipse (row 31 w 23 -> row 39 w 63)", "+-2 px", M, "sm_m06")
row("3 throat", "plate tiers (silhouette)", {"tier1 upper plates": "rows 41-63, width 112 max (rows 43-50)", "tier2": "rows 65-80, width 117 max (row 67-69)", "tier3 lateral flare": "rows 81-141, width 147 max at row 89, 115 at rows 127-139", "sleeve": "rows 143-167, width 102 (2.5 px proud of the body each side)"}, "+-2 px", M, "sm_m06")
row("3 throat", "leaf/petal plates visible on the front", "8 pointed plates radiating from the central blossom at ~45 deg steps: 1 small up (behind top petal), 2 upper (up-out, tips at row 44 x 450/561), 2 lateral (largest, tips at row 86 x 432/576), 2 lower (down-out, lower edge row ~140), 1 central drop plate (point at row 165 x 507, lands on the body). Each plate = silver rim 3-4 px + dark lacquer inset", "count 8 +-1", V, "crop_throat4.png (4x)")
row("3 throat", "central blossom", "5 petals, one petal pointing up; centre (505, 87) = t 0.038; diameter ~60 px (57 w x 62 h), domed silver stamen centre ~10 px", "centre +-3 px, diameter +-6 px", V, "crop_throat4.png; bright-blob peaks sm_m05 rows 59-108")
row("3 throat", "small filigree", "thorn/lace sprigs between the petals and under the blossom (above the drop plate), silver, low relief", "-", V, "crop_throat4.png")
row("3 throat", "lace drips on the body below the throat", "short pointed silver lace/leaf sprigs on the lacquer rows 150-178 at both sides of the drop plate", "+-4 px", V, "crop_throat.png")
# ---- 4 mid band
row("4 mid band", "rows / position", "rows 287-321 (35 px = 2.4 % of length); centre row 304 = t 0.186 from the mouth", "+-2 px", M, "sm_m06")
row("4 mid band", "structure", "upper ring rows 284-292 + engraved leaf-scroll frieze on dark ground rows 292-308 (pointed ends bulge at the sides) + lower ring rows 308-317; blossom over the frieze centre", "+-2 px", V, "crop_band5.png (5x)")
row("4 mid band", "width", "rings 104-106 px (4 px proud of the body per side), frieze ends 117 px at row 304 (10 px proud)", "+-2 px", M, "sm_m06")
row("4 mid band", "blossom", "5 petals; centre (504, 300); ~50 px wide x ~40 px tall (petals overlap both rings)", "centre +-3, size +-6", V, "crop_band5.png")
row("4 mid band", "count", "exactly ONE band (the belt mount); no loop, ring or cord is shown", "1", M, "full view")
# ---- 5 chape
row("5 chape", "rows / length", "row 1265 (top of the up-pointing lancet frame) to 1496 = 231 px (15.8 % of length)", "+-3 px", V + " + sm_m06", "crop_chape3.png")
row("5 chape", "silhouette", {"collar (body width, no step)": "rows 1250-1292 width 72", "side plates": "rows 1293-1387 width 75-84, max 84 at row 1344", "ogive point": "row 1388 w 68 -> 1420 w 60 -> 1440 w 50 -> 1460 w 38 -> 1480 w 21 -> 1496 w 3"}, "+-2 px", M, "sm_m06")
row("5 chape", "point", "ogive: sides tangent-ish at row 1388 (half-angle ~10 deg) steepening to ~33 deg half-angle over the last 16 px; very slightly blunt (3 px at the last row)", "+-3 deg", M, "sm_m06 widths")
row("5 chape", "plates", "1 up-pointing lancet frame (tip row ~1268) through which the vine enters; blossom; 2 lateral plates (tips x 465/545 row 1346 = the 84 px max); 2 lower-lateral plates (tips x 475/538 row 1383 = the step to 68 px at row 1388); 1 central down plate under the blossom (tip row ~1397); the ogive = 2 nested silver lancet outlines around a dark lacquer inset (inner inset ends row ~1457)", "count +-1", V, "crop_chape3.png (3x)")
row("5 chape", "blossom", "5 petals, one up; centre (505, 1330) = t 0.887; diameter ~54 px", "centre +-3, size +-6", V, "crop_chape3.png; sm_m05 peaks rows 1310-1348")
# ---- 6 vine
row("6 vine", "path (row, x) main stem", s17["path"], "+-4 px lateral", V + " cross-checked by sm_m04 metal runs (rows 399, 767, 799, 847, 887, 919, 951, 983, 1007, 1167, 1239, 1255 agree within 3 px)", "overlay debug/DEBUG_NEVER_SHIP_sheath_vine_path.png")
row("6 vine", "path character", "one continuous stem: leaves the throat under the drop plate (row 167), S-bend to the right (x 527 row 193) and back to the band blossom; below the band a sinuous stem with lateral extremes at rows ~460 (u -0.66), ~660 (u +0.66), ~800 (u -0.55), ~920 (u +0.66), ~1140 (u -0.40), ~1245 (u +0.33); half-wavelength 150-230 px; a second thinner stem twines around the main one rows ~930-1000 and runs beside it rows 1060-1200; enters the chape lancet at row ~1262", "extremes +-15 rows, u +-0.1", V, "crops + sm_m04")
row("6 vine", "stem width", {"trunk rows 170-286": "9 px (0.09 W)", "rows 322-700": "6-7 px", "rows 700-1100": "4-6 px", "rows 1100-1262": "4-5 px", "side twigs": "2-3 px"}, "+-2 px", M + " (noisy: specular stem)", "sm_m17 run width of L>0.33 nearest the path")
row("6 vine", "stem relief", "raised, half-round, polished silver with dark outline shading", "-", V, "crops")
bl = [(495, 486, 42, "A"), (503, 515, 20, "A"), (544, 508, 43, "A"), (570, 532, 26, "A"), (592, 502, 25, "A"),
      (693, 525, 42, "B"), (718, 498, 28, "B"), (740, 523, 20, "B"),
      (1043, 518, 39, "C"), (1077, 495, 38, "C"), (1127, 513, 27, "C")]
row("6 vine", "open blossoms on the vine (5 petals, stamen)", [dict(row=y, x=x, t=t(y), u=u(y, x), diameter_px=d, cluster=c) for y, x, d, c in bl], "count 11 +-1; centre +-5 px; diameter +-20 %", V, "crop_cl1/cl2/cl3.png (3x); sm_m05 density peaks")
row("6 vine", "clusters", {"A": "rows 450-605 (t 0.29-0.39): 2 large + 3 small/medium blossoms + ~7 buds, left of centre then right", "B": "rows 630-750 (t 0.41-0.49): 1 large + 2 small/medium + ~4 buds, right of centre", "C": "rows 1005-1140 (t 0.66-0.76): 2 large + 1 medium + ~5 buds", "gap": "rows 750-1000 carry only stem + 2 teardrop pods"}, "rows +-15", V, "crops")
row("6 vine", "blossom sizes", "large 38-43 px (0.45-0.50 of local body width), medium 25-28 px, small ~20 px; fittings blossoms larger: throat 60, band 50, chape 54", "+-20 %", V, "crops")
row("6 vine", "buds", "round closed buds on short stalks, 5-9 px, in clusters: rows 355-365 (2-3), 215-225 above the band (2), 452-458 (2), 523 (1 leafy), 558 (1), 635-685 (4), 1008-1023 (3), 1093-1100 (2)", "count 18 +-4", V, "crops; sm_m05 small peaks")
row("6 vine", "teardrop pods", "2 large pointed white pods on thin curved stalks: (506, 820) t 0.539 and (501, 919) t 0.606, ~12 x 22 px", "+-5 px", V, "crop_body_b.png, crop_facets.png")
row("6 vine", "leaves", "few small pointed silver leaves on the stems (e.g. (472, 523), (482, 1125)); ", "-", V, "crops")
row("6 vine", "engraved twigs in the lacquer", "faint flat grey etched twigs (not raised) along both chamfers, e.g. rows 420-470 left, 550-600 right, 1100-1230 both; albedo/normal-only detail", "-", V, "crop_body_a/b.png")
row("6 vine", "vine coverage", "front face only (|u| < ~0.75); back not shown", "-", M, "sm_m04")
# ---- 7 lacquer
lp = s10["lacquer_lum_percentiles"]
row("7 lacquer", "tone (display lum of metal-free body pixels)", {k: round(v, 3) for k, v in lp.items()}, "p50 +-0.03, p5/p95 +-0.04", M, "sm_m10")
row("7 lacquer", "colour", {"mean_rgb": [round(c, 3) for c in s10["lacquer_rgb_mean"]], "dark_quartile_rgb": [round(c, 3) for c in s10["lacquer_rgb_p50_dark_quartile"]], "bright_decile_rgb": [round(c, 3) for c in s10["lacquer_rgb_bright_decile"]], "saturation": round(s10["lacquer_sat_mean"], 3), "cast": "cool blue-grey (B exceeds R by ~0.03)"}, "+-0.03 per channel", M, "sm_m10 (stored sRGB values)")
row("7 lacquer", "veins", "thin (1-2 px) light grey wisps (lum 0.30-0.45) over soft cloudy mottling; ~7 % of lacquer pixels read as vein; vein edge energy mostly ALONG the sheath (66 % within 60-120 deg of the across direction; peak 75-105), with diagonal branches", "direction +-15 deg; fraction 4-10 %", M, "sm_m10/m11 structure-tensor histogram (facet lines excluded)")
row("7 lacquer", "mottling scale", "clouds 15-40 px (10-27 mm at the design scale); autocorrelation 1/e length ~11 px along vs ~4 px across (only 6 metal-free patches - weak)", "+-50 %", M + " (weak)", "sm_m11")
row("7 lacquer", "finish", "glossy: the chamfers carry a broad soft sheen (brighter than the front face), silhouette rims bright; suggest roughness 0.15-0.25, specular 0.5, no metalness", "-", I, "sm_m03 profile")
# ---- 8 metal
row("8 metal", "fittings value (display lum, metal pixels L>0.30)", {"throat p50": round(s10["throat_metal_L>0.30"]["50"], 3), "chape p50": round(s10["chape_metal_L>0.30"]["50"], 3), "p95": round(s10["throat_metal_L>0.30"]["95"], 3)}, "+-0.05", M, "sm_m10")
row("8 metal", "hue", "neutral silver (saturation 0.047; rgb ~[0.55,0.54,0.55])", "sat < 0.07", M, "sm_m10")
row("8 metal", "sheen", "polished: near-white highlights (L>0.9) on 3-6 % of fitting pixels, dark recesses/insets (L<0.15) on 16-25 %; petals brightest (mean rgb [0.88,0.88,0.89]) with soft gradients = polished silver, lower roughness than the plate rims", "-", M, "sm_m10")
row("8 metal", "suggested PBR", "silver base colour sRGB ~0.80-0.85 neutral, metallic 1, roughness 0.25-0.35 on plates/stems, 0.15-0.2 on petals; AO/cavity darkening in engraving", "-", I, "tone reads above")
# ---- 9 sword + fit
row("9 sword (sheet)", "sheet front view", {"pommel_top_row": 10, "tip_row": 1216, "px_per_m": round(s12["PXM"], 1), "guard_seat_row": 338, "blade_seat_to_tip": "878 px = 0.915 m", "blade_width_at_seat": "51-54 px = 53 mm", "blade_width_at_70pct": "40.6 mm", "taper_seat_to_70pct": "0.77 (23 %)", "back_edge": "straight to ~63 % of the blade, then bows 19.8 mm outward to the tip", "tip_offset_from_base_axis": "44.9 mm (to the viewer's LEFT in the front view)"}, "+-2 px (+-2 mm)", M, "sm_m07/m12 silhouette rows; scale = rev-3 overall length 1.2563 m / (1216-10) px")
row("9 sword (sheet)", "sheet side view thickness", "22 px at the guard -> 10 px near the tip = 23 mm -> 10 mm: NOT credible for a blade (would be 45 % of its width); the side view is stylised -> not used", "-", M, "sm_m07")
row("9 sword (rev3)", "rev-3 blade (Assets/SnowFlower/SnowFlower_Master.blend, SF_Blade + SF_BladeRelief_*; read-only)", {"axis": "+Z (tip at z 1.085), width X, thickness Y", "seat plane (guard under-leaf face)": "z 0.1628", "pendant below seat": "z 0.1628-0.1708, 24.8 x 18.4 mm", "blade_seat_to_tip": "0.922 m", "width": "46.0 mm at the seat -> 43.6 mm at z 0.80 (5 % taper)", "steel thickness": "6.0 mm -> 2.0 mm linear", "half-thickness incl. relief": "max 6.2 mm (z 0.23); 3.2 mm at 50 %; 1.9 mm at 85 %; relief ends z 1.008", "tip": "from z ~0.80 the -X edge sweeps to meet the +X back edge; the back edge bows 7.5-8.2 mm outward; tip at x +30.5 mm", "orientation": "MIRRORED vs the sheet front view (tip and tassel toward +X seen from -Y; the sheet front shows them on the left) - i.e. rev-3 front = sheet back view"}, "+-0.5 mm", M, "sm_m09 plane slices every 10 mm")
row("9 fit", "conflict", "The reference sheath is straight and symmetric with a centred point; the sword is a single-edged dao whose tip lies on (rev-3) or beyond (sheet) the back-edge line, 30-45 mm off the blade's base axis, while the reference body tapers 26 % toward the tip. A straight symmetric sheath of natural length (tip resting ~65-80 mm above the chape point) cannot hold the rev-3 blade (static margin -1 to -3 mm even with optimal cavity offset) or the sheet blade (-10 to -12 mm).", "-", M, "sm_m12 static/swept fit, wall 3.0/2.5 mm, clearance 1.5/1.0 mm per side")
row("9 fit", "trade-off: blade back-edge sweep -> sheath bow needed (natural length ~1.0 m, wall 2.5, clearance 1.0)", {k: dict(sweep_mm=v["sweep_mm"], tip_rests_row=v["y_end"], sheath_len_m=round(v["sheath_len"], 3), bow_mm=round(v["bow_mm"], 1), bow_ref_px=round(v["bow_ref_px"], 1), bow_from_row=round(v["bow_start_row"]), cavity_offset_mm=round(v["cavity_offset_mm"], 1)) for k, v in s16.items() if v}, "-", M, "sm_m16 (rev-3 outline, back edge capped at the given sweep)")
row("9 fit", "long straight alternative", "a straight sheath holds the rev-3 blade only if the tip rests at ref row <= ~1225 (k >= 0.777 mm/px, sheath >= 1.14 m, >= 21 cm hollow past the tip; margin +0.2 mm at wall 3/clr 1.5); tilting the blade 1 deg inside gains little (sm_m15) and shifts the guard 8 mm off-centre. The sheet blade (19.8 mm sweep) needs a >= 16 mm bow at any length <= 1.2 m.", "-", M, "sm_m12/m14/m15")
row("9 fit", "RECOMMENDED resolution", "Sheath exactly as the reference: straight, symmetric, centred point. Scale k = 0.687 mm/px -> length 1.008 m, body 66.6 mm wide below the throat, 49.5 mm at the chape collar, throat 101 mm, chape 159 mm long. The blade tip rests at ref row 1380 (just above the lower-lateral chape plates, 80 mm of solid ogive below). Cavity = blade outline + 1.0 mm clearance per side, 2.5 mm walls, cavity axis offset 2.5 mm toward the blade's BACK edge; a hidden bow of <= 2 mm (<= 3 ref px, reads straight) is allowed from ref row ~840 down. REQUIRES the v4 blade's back edge to stay straight to the tip (sweep <= 2 mm beyond the back-edge line): the curved-tip look must come from the cutting edge sweeping up to a straight back. This conflicts with rev-3 (8.2 mm sweep) and the sheet (19.8 mm) -> USER DECISION.", "bow <= 2 mm; margin >= 0 at every 10 mm slice", D, "sm_m16 sweep 0-2 mm rows")
row("9 fit", "fallback if the blade keeps its sweep", {"rev-3 sweep 8 mm": "sheath lower part bows 8 mm (11.7 ref px) toward the back edge from ref row ~860, tip rests row 1380, length 1.008 m - a slight sori, the chape sits ~12 px off the mouth axis in the front view", "sheet sweep 20 mm": "bow 21 mm (31 ref px) from ref row ~440 - visibly curved, no longer the reference", "engine-side": "or hide the blade while sheathed (hilt-only mesh / masked blade section) so no poke-through can show"}, "-", D, "sm_m13/m14/m16/m16b")
row("9 fit", "mouth collar", "measured outer width 64 px = 44 mm at k 0.687 < rev-3 blade 46 mm: the collar must be widened to >= blade width at the seat + 2 x 1.0 clearance + 2 x 1.5 metal = 51 mm (74 px, 0.77 of the body width instead of 0.66); it is hidden under the guard when sheathed", ">= 51 mm (rev-3 blade); >= 58 mm for a sheet-width 53 mm blade", D, "deviation from the reference, flagged")
row("9 fit", "mouth interior / pendant pocket", "mouth opening = blade section + 1 mm; a pocket 27 x 21 x 9 mm (rev-3 pendant 24.8 x 18.4 x 7.8 mm + clearance) so the guard's under-leaves seat on the collar top; the opening lined dark (lacquer black), not visible when sheathed", "-", D, "not shown in the reference")
row("9 fit", "cavity thickness", "2 x (blade half-thickness incl. relief + 1.0 mm): 14.4 mm near the mouth (relief up to +-6.2 mm), 8.4 mm at 50 %, 5.8 mm at 85 %; outer depth 22 -> 17 mm leaves >= 2.5 mm walls", "walls >= 2.5 mm", D, "sm_m09 rev-3 slices")
row("9 fit", "swept vs static", "a game only needs the STATIC fit (sheathed pose); straight insertion through a tapered sheath additionally needs the tip's lateral position to pass every station (swept margin in sm_s12). Draw animations are fast; the swept fit is not required.", "-", I, "sm_m12")
row("10 sockets", "SOCKET_Holster (sheath)", "at the mouth-collar top plane, on the cavity axis (2.5 mm toward the blade's back edge from the sheath axis); +Z out of the mouth (toward the grip), +X toward the blade's back edge; the sword's matching point = centre of its guard seat plane on the blade axis (rev-3 z 0.1628), blade along -Z of the socket, blade fully inside", "-", D, "fit section")
row("10 sockets", "SOCKET_Hip (sheath)", "at the mid band (ref row 304, t 0.186 = 188 mm below the mouth at k 0.687), on the BACK face centre (behind the vine side), +Z toward the mouth", "+-10 mm", D, "the band is the only belt mount shown")
row("11 not shown (DESIGNED)", "parts", ["back face (plain marbled lacquer; fittings continue around as plain rings/plates, blossoms only on the front)", "sides/depth and the cross-section depth", "mouth interior, cavity, pendant pocket", "belt hardware (none shown - socket only)", "tassel/cord: NONE (decided; none shown)"], "-", D, "reference is a single front view")

spec = dict(
    title="Snow Flower sheath - reference specification (machine twin of References/SnowFlower/SHEATH_REFERENCE_SPEC.md)",
    date="2026-09-26", instrument="Blender 5.2 headless Python + NumPy 2; scripts WorkFiles/SnowFlower/v4/sheath_metrology/sm_m00..sm_m20, stage outputs sm_s*.json",
    reference=dict(file="References/SnowFlower/SnowFlower_sheath_reference.png", sha256=s00["sheath"]["sha256"], size=[1024, 1536]),
    sword_reference=dict(file="References/SnowFlower/SnowFlower_user_reference.png", sha256=s00["sword"]["sha256"], size=[1222, 1287]),
    conventions=dict(rows="image rows, 0 = top; the sheath runs from row 31 (mouth collar top) to row 1496 (chape point)",
                     t="(row - 31) / 1465, 0 = mouth top, 1 = chape point", u="-1 = left silhouette edge, +1 = right edge of that row",
                     scale_designed_m_per_px=K, status="MEASURED = read off pixels; INFERRED = consequence of measured rows; DESIGNED = proposal for what the reference does not show or where the fit forces a change",
                     build_input_policy="the build must never read, sample, project or trace the reference pixels or any debug image"),
    decided=dict(tassel="none on the sheath; the sword's tassel (cord, charm, bundle) is removed"),
    ip_note="The sword reference sheet is titled 'JIN MUWON - SNOW FLOWER BLADE'. Jin Mu-won is the protagonist of the Korean webtoon 'The Legend of the Northern Blade'. Fine for a personal project; must not be sold on Fab under that name/design unless the user decides otherwise.",
    rows=rows)
p = os.path.join(os.path.dirname(HERE), "sheath_spec.json")
json.dump(spec, open(p, "w"), indent=1, default=float)
print("wrote", p, len(rows), "rows")
