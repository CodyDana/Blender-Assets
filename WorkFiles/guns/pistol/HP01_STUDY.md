# Heavy Pistol HP-01 (`HP01`): W0 study

**Status:** 2026-10-14, W0 only: measurement, traces, craft study, spec and build plan. Nothing was built, and there
was no Blender and no Unreal work. Lock `HP01` is held by `claude`. The branch is `claude/pistol-hp01`, taken from
the gun chat's 01512387. Nothing is committed.

**Reference:** `References/Guns/Pistol/pistol_sheetA.webp`. It shows four views (LEFT, RIGHT, TOP, 3/4 FRONT LEFT)
of a stainless large-frame, gas-operated hand-cannon.

**Where the detail is:**
- `MEASURE.md` + `hp01_measured.json`: numbers and method.
- `CRAFT_STUDY.md` + `craft_parts.json`: construction, finish and the real-pattern rulings per part.
- `hp01_spec.json`: the single source the builder reads. S0 passes.
- `HP01_BUILD_PLAN.md` + `hp01_interface.json`: stages, gates, clips and the proposed gunlib changes.
- `HP01_DESIGN_SHEET.png`: the summary sheet.

Generic names only. In any asset, text or listing the gun is "Heavy Pistol HP-01" or `HP01`. The style reference's
name, maker and marks never appear; the gun deny list (gunlib `qa_gun.GUN_DENY`, 48 terms) is clean on every name in
the spec.

---

## 1. Decisions (R1-R18)

| # | Decision | Why |
|---|---|---|
| R1 | Product "Heavy Pistol HP-01", code `HP01`, lock `HP01`. Unreal names `SK_HP01`, `SK_HP01_Skeleton` (the pistol-class pilot), `SM_HP01`, `SM_HP01_Mag`, `PHYS_HP01`, `A_HP01_*`, `M_HP01_Steel / _Furniture / _Mag` | study 4.8; deny list clean (S0) |
| R2 | **Sides.** The sheet is a mirrored pair: LEFT against flipped RIGHT gives IoU 0.995, and neither shows a handed part. Labels are taken as given. LEFT is the outline authority; RIGHT is reported only. The handed parts of the real pattern are placed by ruling (R5, R7, R8) | MEASURE "Panels and sides"; 3/4 camera geometry |
| R3 | **Scale.** 273 mm overall (study 3.5; the ruler reads +9.5 %), giving 2.1097 px/mm. Heights and positions come from the sheet. The sheet is +7 % taller than the class (170.6 against ~159 mm) and that is kept: the side view is the trace authority and the user's bar is "exact on side / top". The barrel is the 152 mm class (rifled length; the visible rib reaches 217 mm because it carries the chamber block and hood). Mass is **2.0 kg** with an empty magazine | study 3.5, 3.6 G17, gun quality bar (memory, 2026-10-05) |
| R4 | **Mechanism: the gas-operated class with a fixed barrel.** The barrel group (crown boss, top rib with its upper facets, hood under the rail, chamber block) is fixed: it is part of `body`, with no bone. The **slide** is the U-section under the rib (the flanks below the facet line, the lower band) plus the rear block (serrations, rear sight, safety). It runs back under the rib. `Muzzle` sits on `body`, not on `slide` as the study table says for a pistol, because the barrel does not move | study 2.2 ("barrel fixed: gas design"); the sheet's facet line below the rib is the barrel/slide seam (MEASURE: upper facet band Z +7..+17, run-out diagonal) |
| R5 | **Ejection.** No port shows at rest (as drawn). When the slide runs back, an **ejection window** opens on the right between the hood end (X -217) and the slide's rear block, where the facet run-out diagonal is. `ShellEject` sits there on `body`. The opening, the chamber block and the breech face are revealed geometry | Keeps the sheet exact at rest and stays mechanically honest. A visible port at rest is Q2 |
| R6 | The **front plate** belongs to the slide, because it spans the lower band. The crown boss stays put, so a gap opens round it when the slide is back, and twin recoil guide rods show (real pattern, hidden at rest) | sheet: the plate runs over the lower band (MEASURE) |
| R7 | **Slide stop on both sides**, as drawn: an ambidextrous lever is a real option. One bone, `slide_stop`, carries both levers, joined through a cross shaft | mirrored sheet; G10 (a mirrored part is fine when the sheet draws it on both sides) |
| R8 | **Magazine release: added.** A low-profile 9 mm round button, 0.8 proud, on the LEFT in the steel strip at the guard root, with a checkered face. It is the only invented visible part. It is needed for the reload clips and absent on the sheet | Q3. ER1 called smooth buttons CG |
| R9 | **Flank tab** (on the slide, both sides, 3.8 mm proud): kept as drawn, as a fixed steel inlay with a 0.3 seam. The style reference has nothing like it, so it is an original element | Q4 asks whether it should be a takedown lever instead |
| R10 | **Serrations as drawn:** 7 raised flat-topped ribs over square-bottom grooves, pitch 4.09 normal, leaning 16.6 deg top-forward, depth 1.2. They are built from the slide's own 2D profile, not by booleans. The sheet's pitch is coarser than the 1.5-3 mm norm. It is kept, because it is what the sheet draws, and it widens the design distance | MEASURE serrations; study 3.2 |
| R11 | **Rail:** gunlib `rail_1913`, standard profile (pitch 10.01, slot 5.24 x 3.0), **6 crossbars** in the drawn recess (X -217.3..-153.3), integral with the barrel hood. The sheet pitch of 10.66 is the standard within the reading error. TOP's 5 bars are overruled by the two side views and the 3/4 (Q10). The crossbar tops are square and flat | CLOSEUP_METHOD_PLAN 2.3 ("rail teeth read as fins") |
| R12 | **Finishes** (finish cards, close-up method 2.1): `stainless_brushed` on the slide, barrel and frame flats; `stainless_bead` on the frame curves (the guard and strap read duller on the sheet); `black_oxide` on the sights, rail, hammer, trigger, safety, slide stop, release, flank tab and mag base plate; `rubber_pebble` on the grip; `soot` as bake masks | study 3.3 brushed stainless (0.67, 0.64, 0.60); sheet value order |
| R13 | **Slots:** `M_HP01_Steel` (`M_Steel_Master`; stainless plus black oxide as baked colour), `M_HP01_Furniture` (`M_Fabric_Master`, Metal From ORM off; the rubber grip), `M_HP01_Mag` (`M_Steel_Master`). A held gun costs 4 + 2 draws | study 5.9 |
| R14 | **Bones (8):** `body`, `slide` (-X: travel 48, lock 46, press check 14), `selector` on `slide` (about Y: 0 = FIRE, -40 = SAFE), `hammer` (about Y: 0 = cocked as drawn, +58 = down), `trigger` (about Y, -9 deg), `slide_stop` (about Y, +10 = engaged), `mag_release` (-Y, 3 mm), `magazine` (attach only). The rest pose is as drawn: slide forward, hammer cocked, safety on FIRE, magazine seated | study 5.2; the cartridge class's overall length 40.4 + 5 mm < 48 travel (S0) |
| R15 | **Close-up method from W0.** The faired-outline, authored-bevel, no-sliver and finish-card rules (gates CU1-CU8) run from the first form stage. An early-realism round (ER0) at W1c is a gate: a decisive fail stops the build and changes the method | §4 below; carbine ER1, sniper W4b |
| R16 | **Grip origin:** the tang web line (sheet y 285), then 46 mm down the 17.4 deg grip axis (the standard's depth, which came from the AR-01's H1). This is provisional for the pistol class: the pistol's own H1 sets the class depth and pose | study 5.1; gun_standard 0.3.0 |
| R17 | **Mass and CoM:** 2.0 kg on `PHYS_HP01`. `CenterOfMass` is estimated in the spec; the builder recomputes it from the part volumes and overwrites it | study 3.5, 5.3 |
| R18 | **Markings:** only the user's generic-marks rule (2026-10-13). The default is a safety dot-pictogram pair on the slide at the lever arc. Rail digits are optional (Q6). Never a maker, model, calibre, serial or logo | memory gun-quality-bar; CLOSEUP 2.4 (`marks.INVENTORY`) |

---

## 2. The sheet's self-consistency

| Check | Result | Ruling |
|---|---|---|
| LEFT vs mirrored RIGHT | IoU 0.9952 | a mirror: LEFT is the authority, RIGHT is reported |
| LEFT vs TOP length | 576 vs 570 px (-1.0 %) | TOP is used at the side-view scale; TOP X positions are checked within 1 % |
| Rail bars | side 6, TOP 5 | 6 (R11, Q10) |
| Width | TOP 46.9 mm slide; the 3/4 implies ~17 % narrower; the class is ~32 | Q1 |
| Top line | rises 2.2 deg toward the rear (side views and 3/4) | kept (Q11); a design delta from the style reference |

No disagreement in design (study 4.2 / Q11 of the line) was found, so there is nothing to stop for. The width is a
proportion question for the user (Q1).

---

## 3. IP: features too close to the style reference, and proposed original deltas (not applied)

The sheet is a near-replica of a famous large-calibre gas pistol. The game may use it as drawn. **For a Fab sale the
silhouette is too close**, through the combination of these features:
1. the triangular fixed-barrel top rib with its long upper facets running out in a diagonal over the chamber;
2. the front block with the crown boss proud of a thin front plate;
3. the square-fronted trigger guard on a frame that starts at the guard;
4. the slide's lower band under the barrel (recoil-spring housing);
5. the rear block with slanted serrations and the slide-mounted safety beside an exposed spur hammer;
6. the wrap-around grip with a bordered side panel.

Proposed deltas (as the rifle did; each is one generator parameter, and none is applied in W0):

| # | Delta | Where | Cost |
|---|---|---|---|
| D1 | Rib: replace the triangular facet section with a flat-top rib carrying a 1.5 mm-stepped shoulder; move the facet run-out to a vertical step 12 mm ahead of the rail | barrel | low (section profile) |
| D2 | Front: merge the crown boss into a squared muzzle block with lightening flats on each side | barrel + front plate | low |
| D3 | Trigger guard: a rounded front with a short forward hook in place of the square front | frame | low (outline) |
| D4 | Lower band: a vented recoil housing (3 elongated windows each side, with real walls) | slide | medium |
| D5 | Serrations: keep the 7 raked ribs (already different from the reference's grooves) and add a front-of-slide set of 3 | slide | low |
| D6 | Grip: our own border shape (a stepped panel with a thumb-rest shelf) and a backstrap with horizontal ribs in place of the stipple strip | grip | medium |
| D7 | Keep the flank tab (R9) and the 2.2 deg rising top line; both are already original | - | 0 |
| D8 | Rear sight: a U-notch with a sloped serrated face in place of the square ears | sight | low |

The game keeps the sheet's design; the Fab variant would be `SK_HP01` with deltas D1-D8 set (Q12). The sheet's
design is not sold as drawn.

---

## 4. Close range: why the earlier guns failed, and how HP01 avoids it

**Evidence read:**
- `CLOSEUP_METHOD_PLAN.md` (the SMG and AR-01 paint rounds did not converge);
- carbine ER1 (`gates/early_realism_g1.json`: 24 of 24 judge calls said CG on geometry, 0 of 6 controls);
- sniper W4b (16 of 16 fake: torn slivers, jagged traced edges, stepped seams, a wavy edge, a crude trigger, a thin
  mag release; the root cause was Blender's bevel clamp collapsing widths across the whole mesh, then a patchwork of
  exclusion boxes).

A pistol is seen closer than any long gun: 35-45 cm at the hip in first person, 25-35 cm in an inspect. Its slide fills
the lower screen, and the sheet resolves 0.47 mm per px.

| What judges called | HP01 design rule (gate) |
|---|---|
| Jagged traced outlines, zig-zags, wavy edges | Every traced outline is **faired** (curvature-limited spline fit, corners pinned where the sheet has corners) before it becomes geometry. Deviation from the trace <= 1 sheet px; 0 second-difference jags (CU1). The serration field, the guard and the grip outline come from faired 2D profiles |
| Stepped bevels, constant-width "CG" edge strips, bevels collapsed to microns | **Authored bevels**: every edge set's land is built into the section or outline generator with its process width (machined 0.4-0.6, cast 1.0-1.5, moulded 0.6-0.8 with draft). No Bevel modifier with clamp overlap, no exclusion boxes. Widths are measured along every edge set (CU2). Widths differ by process, so the highlight strips are not uniform (G1 CV > 0.3) |
| Torn slivers, thin triangles | Closed generators per part, booleans only on flat faces (if at all), the gunlib UD rule plus a 2 deg minimum visible angle, B6a twin topology from W1 on (CU3) |
| Flat 2D cut-out trigger, slab levers, flush identical pins, smooth domed button | **Real-pattern small parts** (CU6): a 6.5 mm crowned trigger blade lofted along the traced curve; grooved and dished pads on the safety and slide stop; a checkered release face; one flush chamfered guard pin, and no other pins (none drawn); a dovetail seam under the front sight |
| Uniform paint, noise "clouds", plastic metal | **Finish cards** tuned on a swatch board under the frozen grey-card rig before any gun render (CU5). Brushed stainless has a direction per part; bead blast on the frame curves gives a second roughness mode; the pebble and the spur checkering come from HP bakes at real scale, not noise (CU8) |
| Missing markings | the safety dot pictograms (R18) |
| Late discovery | **ER0 at W1c** (CU4): 8 rendered crops plus 6 real-photo controls, two judges. A decisive fail stops the build and changes the method before UV / paint money is spent |

---

## 5. Open questions with defaults (the build proceeds on the defaults unless the user rules)

| # | Question | Default |
|---|---|---|
| **Q1** | **Width.** TOP draws the slide 46.9 mm (55.0 at the levers); the 3/4 implies ~17 % narrower; the real class is ~32 mm. A 47 mm slide fills more of the first-person view than any real pistol | **The TOP view as drawn** (the user's bar: exact on side / top), with one parameter `K_Y` (spec `scale.width`). The real-pattern option is `K_Y` ~0.70 (slide ~33 mm), a one-number change. **Ask before W1** |
| Q2 | Should a visible ejection port show at rest? | No (R5: a window opens only when the slide is back) |
| Q3 | Add the magazine release, which the sheet does not draw? | Yes: a low-profile left button (R8) |
| Q4 | Flank tab: a fixed inlay, or a working takedown lever? | Fixed inlay (R9) |
| Q5 | Safety reading (the sheet's block is too dark to see) | A slide-mounted lever on a transverse shaft, flush (TOP shows no protrusion), 3 grooves on the paddle (R14) |
| Q6 | Markings | Safety dot pictograms yes; rail digits no |
| Q7 | Front-sight dot | A plain flush insert ring, no colour |
| Q8 | Grip retention screw (none drawn) | None (a hidden screw under the panel) |
| Q9 | Magazine witness holes (hidden at rest, visible in reloads) | Yes, on the tube spine |
| Q10 | Rail bars: 6 (sides, 3/4) or 5 (TOP)? | 6 |
| Q11 | Keep the 2.2 deg rising top line? | Yes (trace) |
| Q12 | Fab deltas D1-D8: when? | Game as drawn now; the deltas at the Fab stage on the user's go |
| Q13 | Grip origin depth for the pistol class | 46 mm provisional; replaced by the pistol H1 at W3 |
| Q14 | First-person texel targets for the pistol (raised class C/D, spec `camera.pistol`) | As in the spec; a gunlib proposal (plan §9) |

---

## 6. Things I could not verify offline

These class figures are from the study table [E49] and general knowledge [K]: height ~159 mm, width ~32 mm, mass
2.0 kg, the cartridge class's overall length 40.4 mm. WebSearch was not permitted in this run. The figures drive no
geometry (heights and widths come from the sheet) except the slide travel, which has 7.6 mm of margin.
