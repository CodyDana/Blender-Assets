# Kunai blade section: research for options A / B / C

**Date:** 2026-09-26. Research only: WebSearch / WebFetch, nothing downloaded, nothing in the live tree touched.
Companion calculator: `WorkFiles/kunai/blade_section/research/section_calc.py` (read-only copy of `kunai_spec.h_blade` /
`ridge_blade` / `z_blade_face`; run with Blender's bundled python).

Labels as in the study: **SOURCED** = page fetched 2026-09-26 and the figure read from it; **SNIPPET** = seen only in a
search summary (page 403/500 or not fetched); **ESTIMATE** = derived or judged here. `[n]` = existing numbers in
`References/Kunai/sources.md`; `R1..` = new in this pass.

Metrics (per station): `ridge_ratio = ridge half-thickness / half-width`; `face_slope = (ridge half - edge half) / half-width`
(= tan of the face angle). For a full diamond (no edge flat) the two are equal. For retail items with one thickness and
one width the ratio is `thickness / width` at the widest/thickest point (stock ratio); where the item is flat stock with
bevels this is an upper bound on the true face slope.

---

## 1. Our current section (for scale)

Blade 140 mm, half-width 8 mm at the shoulder, 18 mm at x = 35, leaf taper to the tip; ridge 5.0 mm to x = 35, linear to
1.6 mm at x = 135; edge flat 1.5 mm; then the 35 deg/side grind to a 0.15 mm land.

| Station (of 140 mm) | x mm | half-width | ridge T | ridge_ratio | face_slope | face angle |
|---|---|---|---|---|---|---|
| 0.10 | 14 | 12.00 | 5.00 | 0.208 | 0.146 | 8.3 deg |
| 0.25 | 35 | 18.00 | 5.00 | 0.139 | 0.097 | 5.6 deg |
| 0.40 | 56 | 15.12 | 4.29 | 0.142 | 0.092 | 5.3 deg |
| 0.50 | 70 | 13.00 | 3.81 | 0.147 | 0.089 | 5.1 deg |
| 0.60 | 84 | 10.72 | 3.33 | 0.156 | 0.086 | 4.9 deg |
| 0.75 | 105 | 7.00 | 2.62 | 0.187 | 0.080 | 4.6 deg |
| 0.90 | 126 | 2.92 | 1.91 | 0.326 | 0.070 | 4.0 deg |

Why it reads flat (ESTIMATE, from the numbers): the 1.5 mm edge flat is a large share of the ridge everywhere, and
towards the tip the ridge (1.6 - 2.6 mm) is barely above the edge flat, so the face slope falls to 4 - 5 deg over the
front half; the front 40 % of the blade is effectively a 1.5 - 2.6 mm plate. Blade steel (analytic, before the grind):
8,347 mm^3 = 65.5 g; plan area 2,958 mm^2 (matches the study).

## 2. Sources and numbers

### Kunai, forged / hand-made and throwing kunai

| # | Source | Figures | Ratio / angle | Label |
|---|---|---|---|---|
| [24] | Kult of Athena, Honshu kunai (re-read) https://www.kultofathena.com/product/honshu-kunai-set-with-sheath/ | 46.3 / 30.3 / 41.5 mm wide; 4.6 - 1.6 mm thick; no section wording | 4.6 / 46.3 = 0.099 (5.7 deg if a full diamond) | SOURCED |
| [30] | Etsy forged "tobu kunai" | 12 in, 1 7/8 in (47.6 mm) wide, 3/16 in (4.8 mm), 10 oz (283 g) | 0.100 (5.7 deg) | SNIPPET (unchanged) |
| [32] | Slash2Gash kunai throwers | 2.85 mm (6 in) to 5.1 mm (12 in) | width not given | SOURCED earlier |
| R1 | Bladesmith's Forum, Tim Crocker "Kunai" https://www.bladesmithsforum.com/index.php?/topic/30735-kunai/ | 12.5 in OAL; forged from 9260M round bar, **hollow ground**; "handle thickness before wrap was 1/8" and swells to 1/4" blade thickness" (6.35 mm); weight not stated | width not given | SOURCED |
| R2 | ACEJET Kunai (no-spin thrower, hand-made, Bohemia) https://www.acejetofficial.com/kunai-3 | 254 mm, 31 mm wide, **8 mm thick**, 214 g, 14260 spring steel | 8 / 31 = 0.258 (stock; 14.5 deg if full diamond) | SOURCED |
| R3 | Miki Kajiya ZZ117, hand-forged kunai paper knife https://www.miki-japan.com/zz117.html | 110 mm, 53 mm blade, 1.8 mm, 18 g, SUS420 | toy scale; width not given | SOURCED |
| R4 | Amazon, "Custom Handmade Kunai ... Forged Spring Steel" https://www.amazon.com/Custom-Handmade-Kunai-Perfect-Hunting/dp/B09SQ2K6RJ | 13 in OAL, 7 in blade, 6 in handle, **6 mm** thick | width not given | SNIPPET (HTTP 500) |
| R5 | EverestForge "Japanese Ninja Kunai" https://everestforge.com/japanese-ninja-kunai-dagger | 12 in blade (10 - 20 options), 5160 hand-forged, "pronounced central ridge", ~513 g | no width/thickness | SOURCED |
| R6 | EverestForge "Kunai Mandevilla" https://everestforge.com/kunai-mandevilla-dagger | 20 in / 12 in blade, ~510 g, 5160 | no section numbers | SOURCED |
| R7 | Swordis 5160 kunai (was [31], now read) https://swordis.com/product/japanese-ninja-kunai-dagger-with-ringed-pommel/ | 19 in / 12 in blade, 0.907 kg, "reinforced central mid-rib" | no section numbers | SOURCED |
| R8 | Jayger Damascus kunai https://jayger.co.uk/products/damascus-kunai-throwing-knife-with-leather-sheath | 8.7 in, 4.6 oz (130 g), central fuller | no section numbers | SOURCED |
| R9 | Tactical Elements, hand-forged kunai paper knife https://www.tacticalelements.com/hand-forged-kunai-fixed-blade-paper-knife-black/ | 5.4 - 6.6 in, SK85, Japan | no section numbers | SOURCED |
| R10 | United Cutlery Honshu UC3453 page https://www.unitedcutlery.com/ProductDetail.aspx?itemno=UC3453&cat=HS | page has no numbers; search summary: 0.2 in (5.1 mm) thick, another retailer 4 mm | - | SNIPPET |
| R11 | Search summary, "Z-hunter" and other forged spring-steel kunai | 3 - 6 mm blade thickness across 7 - 13 in kunai | - | SNIPPET |

Across every kunai that states a figure, ridge/stock thickness is **4 - 8 mm**: mass-market 4.0 - 5.1 mm, hand-forged
6 - 6.35 mm (R1, R4), a hand-made no-spin thrower 8 mm (R2). No kunai source gives thickness at more than one point
except Honshu [24], and none states "no edge flat" in words; R1's hollow grind and R5/R7's "central ridge / mid-rib" are
the only section descriptions. The forged makers do not publish width, so their ratio can only be bracketed:
at a 36 - 48 mm blade, 6.35 mm is ratio 0.13 - 0.18.

### Throwing knives (flat stock, comparison only)

| # | Source | Figures | Label |
|---|---|---|---|
| R12 | Cold Steel Sure Balance Thrower https://www.coldsteel.com/sure-balance-thrower/ | 13 3/8 in, 9 in blade, **5 mm**, 18.5 oz, 1055 | SOURCED |
| R13 | knifethrowing.info, Cold Steel Perfect Balance https://www.knifethrowing.info/throwing_knife_perfect_balance_thrower.html | 34.3 cm, 16 cm sharpened, **5 mm**, 430 g | SOURCED |

Commercial throwers sit at 5 mm stock with edge bevels only (flat faces, no ridge); the 8 mm ACEJET (R2) is the thick end.

### Double-edged leaf blades and spear heads with a ridge

| # | Source | Figures | ridge_ratio (face angle, full diamond) | Label |
|---|---|---|---|---|
| R14 | Kult of Athena, 3rd c. Roman pugio (Deepeeka) https://www.kultofathena.com/product/3rd-century-roman-pugio-dagger/ | leaf blade 10.5 in, 59 mm (base) / 54 mm wide, **10 - 8 mm "measured from thick central ridge"**, 1 lb 4 oz | 10/59 = 0.169 (9.6 deg); 8/54 = 0.148 (8.4 deg) | SOURCED |
| R15 | Armor Venue, Late Roman pugio https://www.armorvenue.com/late-roman-pugio.html | 63.8 mm wide, 10.3 - 9.9 mm thick, EN45 | 0.161 (9.2 deg) | SOURCED |
| R16 | Dark Knight Armoury, Long Viking spearhead (hand-forged) https://www.darkknightarmoury.com/product/long-viking-spearhead/ | 9.5 in, 2 in (50.8 mm) wide, 3/16 in (4.8 mm), 1 lb | 0.094 (5.4 deg) | SOURCED |
| R17 | Celtic Webmerchant, leaf spearhead 31.5 cm https://www.celticwebmerchant.com/en-int/products/leaf-shaped-spearhead-approx-315-cm | 20 cm blade, 5 cm wide, 4 mm, 400 g, EN45 | 0.080 (4.6 deg) | SOURCED |
| R18 | Mandarin Mansion, large (Chinese) spearhead https://archive.mandarinmansion.com/large-spearhead | 34.2 cm, 42 mm wide, **13 mm at the forte**; rectangular at the base, flattened hexagon, "flattened diamond shape with two sharp edges" toward the tip; 724 g | 0.31 at the forte (not a diamond there) | SOURCED |
| R19 | Ginza Choshuya, 両鎬直槍 (ryo-shinogi su-yari) 銘 盛重 http://ginza.choshuya.co.jp/sale/gj/r6/007/21_morishige.php | 穂 13.3 cm; 元幅 六分七厘 = 2.03 cm; 重ね 二分 = 0.61 cm; forged full diamond | 0.61/2.03 = **0.30 (16.7 deg)** | SOURCED (unit conversion 1 sun = 3.03 cm: ESTIMATE) |
| R20 | Ginza Choshuya, 大身槍 銘 政次 https://ginza.choshuya.co.jp/sale/sword/21/11/masatsugu_yari.htm | 穂長 59.1 cm, 元幅 2.9 cm, 重ね 1.2 cm, grooved (樋); not a diamond | 0.41 - not comparable | SOURCED |
| R21 | Secrets of the Ice, Lendbreen Viking spear https://secretsoftheice.com/news/2017/11/29/spear/ | blade 31 cm, 5.3 cm max width, Petersen type F; no thickness | - | SOURCED |
| R22 | myArmoury, Manning Imperial ballock dagger https://myarmoury.com/review_mi_bd.html | 13/16 in at base; "approximately 1/2" thick after the false ricasso"; asymmetrical diamond, hollow ground | thrusting-dagger extreme, not comparable | SOURCED |
| R23 | myArmoury, diamond vs lenticular thread https://myarmoury.com/talk/viewtopic.php?t=33248&view=previous | qualitative: same mass and width, lenticular is thinner with a less acute edge | - | SOURCED |
| R24 | The Dark Blade [26] (search summary) | modern kunai: diamond section "much more shallow ... than some traditional designs" | - | SNIPPET of [26] |

## 3. Typical face angles (full-diamond equivalent, atan(ridge_ratio))

| Class | ridge_ratio | Face angle |
|---|---|---|
| Stamped/retail kunai (Honshu [24], Etsy [30]); thin leaf spears (R16, R17) | 0.08 - 0.10 | 4.5 - 5.7 deg |
| **Ours today** (face_slope; the 1.5 mm edge flat eats the rest) | 0.07 - 0.15 | 4 - 8 deg (5 deg mid-blade) |
| Leaf daggers with a real midrib (pugio R14, R15) | 0.15 - 0.17 | 8.4 - 9.6 deg |
| Hand-forged kunai, 6.35 mm on a 36 - 48 mm blade (R1, R4; width unknown) | 0.13 - 0.18 | 7.5 - 10 deg (ESTIMATE) |
| Thick no-spin thrower (R2, stock) | 0.26 | 14.5 deg if ground as a diamond |
| Forged ryo-shinogi spear (R19); spear forte (R18) | 0.30 - 0.31 | 16.7 - 17 deg |

A diamond "reads" as a diamond once the face angle is roughly 9 deg or more (the pugio class); at 5 deg the facets
catch light almost like one plane (ESTIMATE, consistent with the study's own "shallow diamond" wording and R24).
Edge (secondary) bevels on sharpened blades are far steeper, 15 - 25 deg per side (ESTIMATE, general knife practice;
no source read this pass); the pack's 35 deg/side grind is steeper still.

## 4. Recommendation for option C (full diamond at forged-replica thickness)

**Ridge 7.0 mm at the widest point (x = 35), linear taper to 1.6 mm at x = 135 (keep RIDGE_TIP_AT), EDGE_T -> 0 (faces
meet at the edge; the pack grind then only sets the 0.15 mm land). Range 6.0 - 8.0 mm at the ridge; tip 1.6 - 2.0 mm.**

- Why 7.0: the only read hand-forged kunai figure is 6.35 mm (R1), a snippet gives 6 mm (R4), the thick hand-made
  thrower is 8 mm (R2). 7 mm is the middle of the forged range and gives ridge_ratio 0.19 - 0.20 over the central blade:
  just above the pugio midrib class (0.15 - 0.17), below the forged spear (0.30). ESTIMATE within a SOURCED range.
- Resulting section (calculator):

| Station | x | C 7 -> 1.6 full: T / ratio / angle | C 6 -> 1.6 | C 8 -> 2.0 |
|---|---|---|---|---|
| 0.10 | 14 | 7.00 / 0.292 / 16.3 deg | 0.250 / 14.0 deg | 0.333 / 18.4 deg |
| 0.25 | 35 | 7.00 / 0.194 / 11.0 deg | 0.167 / 9.5 deg | 0.222 / 12.5 deg |
| 0.40 | 56 | 5.87 / 0.194 / 11.0 deg | 0.168 / 9.5 deg | 0.223 / 12.6 deg |
| 0.50 | 70 | 5.11 / 0.197 / 11.1 deg | 0.172 / 9.7 deg | 0.227 / 12.8 deg |
| 0.60 | 84 | 4.35 / 0.203 / 11.5 deg | 0.179 / 10.2 deg | 0.236 / 13.3 deg |
| 0.75 | 105 | 3.22 / 0.230 / 13.0 deg | 0.209 / 11.8 deg | 0.271 / 15.2 deg |
| 0.90 | 126 | 2.09 / 0.357 / 19.7 deg | 0.342 / 18.9 deg | 0.435 / 23.5 deg |

- **Mass:** blade steel (analytic, before the grind) 7 -> 1.6 full diamond = 8,342 mm^3 = 65.5 g, **the same as today**
  (the thicker ridge is paid for exactly by losing the 1.5 mm edge flat). 6 -> 1.6: -8.7 g; 7 -> 2.0: +1.1 g;
  8 -> 2.0: +9.8 g. So C at 7 mm keeps the study's 187 - 192 g assembled figure. (Keeping the 1.5 mm edge flat with a
  7 mm ridge would add +17.4 g - that is option A territory.)

### Consequences the rebuild must handle (ESTIMATE, from `kunai_spec.py`)

1. **The knife grind band disappears.** With EDGE_T = 0 and a face angle (11 deg) below the pack grind (35 deg), the
   grind only truncates the apex to the 0.15 mm land about 0.4 mm in from the outline; there is no 35 deg band above it
   (today's band is ~1.1 mm wide at x = 35). The pack's polished-grind read (0.7 mm polished band, satin grind) would be
   lost on the kunai. Options: accept it (a forged look), or keep a micro edge flat of ~1.0 mm, which restores a ~0.8 mm
   band at +11.6 g (then it is not a "full" diamond), or add a separate fixed-width secondary bevel (new code).
2. **Shoulder / tang step.** The neck/tang is 16 x 5 mm (`NECK_HALF = (8, 2.5)`, `STOCK = 5.0`). A 7 mm ridge at the
   shoulder stands 1 mm proud per side of the 5 mm tang. Either ramp the ridge 5 -> 7 mm over x = 0..15 (forged blades
   usually swell out of the tang; R1: "swells to 1/4" blade thickness") or thicken the neck (mass on the grip side,
   moves the pivot). `STOCK` and anything keyed to it (ring stock 5 mm, LOD / collision bounds, sockets) need checking.
3. **Tip.** With the linear taper the ratio climbs to 0.36 at x = 126 and the 1.6 mm floor meets a 2.1 mm-wide point at
   x = 135: the point becomes a stout near-square spike (fine for a thrown/forged kunai; matches forged points being
   thick), but the tip radius / land logic should be checked for a degenerate section.
4. **Collision / bounds:** Z extent grows from 5.0 to 7.0 mm at the blade (UCX hulls, bounds, texel layout of the faces).

### Sanity check for A and B

- **A (raise the ridge at 5 mm stock):** with the ridge capped at 5 mm, the only lever is the edge flat and the taper.
  Dropping EDGE_T to ~0 at 5 mm gives ratio 0.139 / 7.9 deg at x = 35 - in the pugio-to-forged-kunai bracket's lower
  edge; holding the ridge at 5 mm further forward (slower taper) is what lifts the front half, which is where today's
  blade is flattest (4 - 5 deg). Losing the edge flat entirely at 5 mm removes 1.5 mm x 1,479 mm^2 = 2,218 mm^3 = -17.4 g of
  blade steel (calculator arithmetic: the edge flat's volume is EDGE_T x half the plan area) and has the same
  grind-band consequence as C; a thinner flat (e.g. 0.8 mm) costs proportionally less (-8.1 g).
- **B (match the photo's ratio):** any measured photo ratio in 0.15 - 0.20 is well supported (pugio R14/R15, forged
  kunai bracket R1/R4). A photo ratio above ~0.25 would put it with the thick thrower (R2) and forged spear (R19) and
  would imply a ridge of 9+ mm at our 36 mm width, beyond any kunai source.
