# HP01 craft study: how each part is made, finished and worn

**Inputs:**
- `craft_parts.json`: the machine-readable rulings, merged into `hp01_spec.json` by `make_spec.py`.
- Positions from `hp01_measured.json`.
- Classes from GUN_BUILDING_STUDY 3.1-3.4.

**Tags:** [S] sheet, [N] real-pattern practice / engineering norm, [J] judgement.

The governing facts:
1. The sheet resolves **0.47 mm per px**, the best in the line. So the sheet decides presence and absence down to
   about 3 mm: a part it does not show is not built, except where a clip needs it (the magazine release, R8).
2. The pistol is seen at **25-45 cm**, so the visibility minimum of a highlight (~2 px at 1440p) is about **0.35 mm
   at the rear and 0.45 mm in the middle**. Every bevel below is at least that.

## 1. Process classes on this gun

| Part | Real process [N] | Class | Edge widths (LOD0) | Surface marks |
|---|---|---|---|---|
| Slide, barrel group, front plate | forged / bar stock, CNC milled, then brushed | M-chamfer (rib and facet breaks 0.4-0.5; corners 0.6) | 0.4-0.6, 1 segment; inside corners at the cutter radius 2-3 | brushing along X; milling passes in the serration grooves (roughness + normal from the bake) |
| Frame | investment cast, then machined on the rails, the top band and the grip seat | C-fillet on the guard, strap and tang (1.0-1.5, 3 segments); M-chamfer on the machined bands (0.5) | as stated | bead blast on the cast curves; brushed machined flats; a faint parting line at mid-thickness of the guard |
| Sights, rail, hammer, trigger, safety, slide stop, release, flank tab | machined (hammer and trigger: MIM / cast) then black oxide | M-chamfer 0.25-0.4; trigger and hammer C-fillet 0.6-1.0 (trigger face R 2.5 across) | as stated | oxide sheen with brighter crests |
| Grip | moulded rubber, one-piece wrap | P-round 0.6-0.8, draft 1 deg, parting line on the backstrap centre | as stated | pebble 0.7-1.1 mm cells (HP bake), fine stipple on the backstrap |
| Magazine | drawn / folded steel tube; machined base plate | S-bend R 1.0 (tube); M-chamfer 0.6 (plate) | as stated | insertion streaks on the spine; base plate corner dents |

Widths differ by class (0.25 / 0.5 / 1.2 / 2.5), so the edge-highlight widths spread with a CV well above 0.3 (G1).

## 2. Real-pattern small-part rulings

| Part | What the sheet shows [S] | Ruling (built) | Reason |
|---|---|---|---|
| **Slide + serrations** | 7 raked raised ribs (4.09 mm pitch normal, 16.6 deg lean) cut through the upper facet; a smooth panel behind them; the rear face slanted parallel to the ribs | Ribs 1.2 deep, flat tops with a 0.25 break, square groove roots with R 0.4. The grooves stop 1.5 mm above the slide bottom, as drawn. Each groove is part of the slide's 2D outline / profile generator (faired), never a boolean through a bevelled block. Crest polish from the curvature bake | study 3.2 (serrations are geometry); sniper W4b (stepped and torn edges from cuts in bevelled solids) |
| **Barrel / hood** | triangular rib top with upper facets, running out in a diagonal at X -178..-204; the rail sits on the hood | The rib section is a loft of explicit section rings with facet lands; the run-out is an outline feature of the facet. Bore 12.7 dia, >= 2 calibres deep with a 0.8 crown chamfer and darkening with depth; rifling as texture only. Hood end face and chamber block are revealed geometry (the ejection window, R5) | study 3.2 G11; R4 |
| **Recoil spring guide** | not visible at rest | Twin rods 6 dia with springs, forward 50 mm only (revealed when the slide is back). E class, 8 sides (facet rule waived for E: written in the spec) | real pattern of the class; R6 |
| **Hammer** | spur up and back (cocked), 17 mm wide in TOP at its body | Spur tapers 9 -> 6 mm; a 0.8 mm pyramid checkering field on the spur top only (HP bake); pivot pin hidden by the slide's rear block (none drawn) | study 3.2 (checkering = texture); TOP width |
| **Trigger + guard** | curved blade, smooth face; square-front guard, opening 43.1 x 32.7, one pin (3.8 dia) at the front upper corner | Blade 6.5 thick with a crowned face (R 2.5 across) and real side faces with 0.6 edges, lofted along the traced centre curve; tip R 1.0. Guard: cast fillets 1.0-1.2 inside and out, with a parting line. Pin flush with a 0.3 chamfer and a slight recess (-0.05) | carbine ER1 ("flat 2D cut-out trigger", "perfect flush discs") |
| **Safety / decocker** | a dark vertical block beside the hammer, 10 x 31 mm, with no protrusion in TOP | A slide-mounted lever on a transverse shaft, flush (+0.8 at most); a paddle with 3 grooves 0.25 deep; rotates -40 deg to SAFE; dot pictograms at the arc | Q5; ER1 ("constant-thickness plank") |
| **Slide stop** | a wedge on the frame under the serrations' front, both sides, 2 mm proud in TOP | Lever with a dished thumb pad (0.3) and 4 grooves 0.2 deep; pivot at its rear; +10 deg engages the slide's notch (the notch is in the slide's lower edge, revealed when locked) | ER1 ("blocky stacked slab"); R7 |
| **Mag release** | not drawn | A 9 mm round button, 0.8 proud, checkered 0.6 mm (bake), in a 1 mm fence relief in the steel strip at the guard root, left side | R8 / Q3; ER1 ("smooth domed button") |
| **Magazine + base plate** | the base plate only (63.0 x 4.7, black, a step at its top) | Single-stack tube 16.5 x 34 x 128 along the grip axis, wall 0.9; follower; witness holes on the spine (Q9); the base plate machined with drop-worn corners | real pattern; R14 |
| **Grips** | a wrap-around rubber grip: side panel of coarse pebble inside a raised border; a groove; fine stipple on the backstrap; no screw | Border 0.6 proud with an R 0.8 crest; panel field dropped 0.6; groove R 0.5; draft 1 deg; parting line on the backstrap. Pebble and stipple from an HP bake (0.7-1.1 mm cells, 0.12-0.2 tall). No screw (Q8) | CLOSEUP 2.2 (moulded features at real scale); study G19 |
| **Sights** | front: a dovetailed block with a sloped rear face and a dot (5 px ring); rear: a square block with two ears and a dot pin | Front: 60 deg dovetail with a visible 0.2 seam, a smooth rear face (the sheet shows no serration), a flush insert ring 2.4 dia (Q7). Rear: dovetailed, the notch between the ears, the visible cross pin 2.0 dia, chamfered | study 3.2; sheet |
| **Rail** | 6 crossbars on the hood (TOP shows 5) | gunlib `rail_1913` (6 bars, pitch 10.01, slot 5.24 x 3.0), square flat crossbar tops with a 0.25 break; slot floors in the rail's own oxide with root grime only | R11; CLOSEUP 2.3 ("fins") |
| **Flank tab** | a black tab on each slide flank, 3.8 proud | A fixed inlay with a 0.3 seam with depth; the top slightly crowned | R9 |

## 3. Finishes and wear (finish cards; values in `craft_parts.json` `finishes`)

**Stainless brushed** (study 3.3: metallic 1, base (0.67, 0.64, 0.60), roughness 0.25-0.40 along the brush and +0.15
across):
- The brush direction follows each part's long axis (slide and rib along X).
- The sheet's crisp light/dark facet bands are environment reflection, not paint. They come from the facet geometry
  and the brushed anisotropic look (micro-normal + roughness; anisotropy as an option).

**Wear** (study 3.4, by cause):
- holster bright: slide front, front sight base, rib edges;
- sliding polish: the slide rails and the frame rails (revealed);
- thumb travel: the safety arc and the slide-stop pad;
- insertion streaks: the mag spine, the magwell mouth;
- cavity grime: rail slots, serration roots, the grip border groove;
- soot: crown and ejection window.

The sheet's "moderate" wear (scratches across the brush) stays subtle. Edge wear stays hard.

**Bead blast** on the frame curves gives the second roughness mode (G7 needs >= 2 modes): 0.45-0.60.

**Black oxide** on the small parts: 0.16 base, roughness 0.3-0.55. It wears grey-brown first, then shows bright steel
on the crests only.

**Rubber:** 0.025 base, roughness 0.75-0.9. It polishes (roughness -0.1) at the palm swell and the thumb rest and
never shows metal.

**What failed before** (CLOSEUP 1.1-1.3) is avoided by construction:
- No global noise amplitudes. Variation comes from located features: the brushing direction per part, bead blast
  against brush, the parting lines, the oxide crests and the pebble cells.
- The finish identity sits above the pixel: pebble cells are >= 3 texels at class B.
- L5 / G20 are reported, not gates, if the user extends CM-R1 to this gun (it is D1 for the user in the close-up
  plan).

## 4. Fasteners (source per item, study 3.2 / G6)

| Item | Count | Size | Source |
|---|---|---|---|
| Guard pin | 1 (both sides) | 3.8 dia, flush, 0.3 chamfer | [S] 8 px ring |
| Rear-sight cross pin | 1 | 2.0 dia | [S] dot on the rear block |
| Front-sight dot insert | 1 | 2.4 dia ring | [S] 5 px ring |
| Hammer, trigger and slide-stop pins | **0 visible** | - | [S] absent at 2.1 px/mm (a 3-4 mm pin = 6-8 px): none invented; hidden under parts |
| Grip screw | 0 | - | [S] absent (Q8) |

## 5. Texel classes for the pistol (proposal, spec `camera.pistol`)

| Class | Pistol surfaces | Target px/cm |
|---|---|---|
| A | rear sight notch, front sight, rail top (ADS) | 80-100 |
| B | slide rear block, serrations, hammer, safety, slide stop, grip top / palm, rib top | 70-90 |
| C | slide flanks, frame guard, trigger, grip panels, mag base plate | 45-60 |
| D | front plate, crown, lower band front | 35-45 |
| E | insides, rails, revealed rods, mag tube | 10-15 |

The steel set is estimated at ~800 cm2. At these targets that needs ~4.1 M texels at 70 % fill, so **Steel 4096**
(2048 holds 2.9 M). Furniture is 1024 (grip ~120 cm2) and Mag 1024. The packer's report decides at W2.
