# Dojo references: provenance and notes

All images here are **AI-generated (ChatGPT image generation)** by the user, 2026-09-27, as MODELLING REFERENCE ONLY.
No pixels from them go into any shipped texture or mesh; the meshes and textures are built new. Recorded for Fab's AI
disclosure (FAB_ASSET_STUDY section 4) in case the dojo kit is ever listed.

| File | Source | Prompt | Notes |
|---|---|---|---|
| `dojo1_reference1.png` | ChatGPT, from `WorkFiles/world/DOJO_ARENA_IMAGE_PROMPT.md` prompt 1 + the top-down plan | arena overview | High-angle dusk overview; layout matches `DOJO_ARENA_SPEC.md` |
| `dojo1_reference2.png` | ChatGPT, prompt 2 | eye-level from the gate | Sunset establishing view (the chosen time of day) |
| `dojo_wall_ref.png` | ChatGPT, `WorkFiles/world/DOJO_PIECE_PROMPTS.md` piece 1 | perimeter wall model sheet | See measurements below |
| `dojo_gatehouse_ref.png` | ChatGPT, piece 2 | gatehouse model sheet | See measurements below |
| `dojo_hall_front_ref.png` | ChatGPT, piece 3 | hall front model sheet (sha256 cbbe6c92...) | See measurements below |
| `dojo_roof_details_ref.png` | ChatGPT, piece 4 | roof detail sheet (sha256 a2e03756...) | Also adds a compound overview and small elevations of the hall, wall + gate, storehouse, shed, drum pavilion and well |
| `dojo_outbuildings_ref.png` | ChatGPT, piece 5 | storehouse + residence sheet (sha256 334400b6...) | See notes below |
| `dojo_corridor_ref.png` | ChatGPT, piece 6 | covered corridor sheet (sha256 9a0ca954...) | See notes below |
| `dojo_drum_pavilion_ref.png` | ChatGPT, piece 7 | drum pavilion + taiko sheet (sha256 cd418719...) | See notes below |
| `dojo_training_shed_ref.png` | ChatGPT, piece 8 | training shed sheet (sha256 a1cffefa...) | See notes below |
| `dojo_courtyard_stone_ref.png` | ChatGPT, piece 9 | lanterns, well, cistern (sha256 2a427679...) | See notes below |
| `dojo_training_props_ref.png` | ChatGPT, piece 10 | training props (sha256 863b50ec...) | See notes below |
| `dojo_modern_props_ref.png` | ChatGPT, piece 11 | a SUMMARY BOARD of all 11 pieces with dimension labels; panel 11 is the modern props (sha256 776b3739...) | See notes below |
| `dojo_modern_props_ref2.png` | ChatGPT, piece 11 retry | a second summary board of pieces 1-10 with labels, no modern props panel (sha256 afa61ecf...) | See notes below |

## Measurements against the spec (scale from each sheet's 1.8 m silhouette; approximate, about +-10 cm)

**Wall** (127.8 px/m, ground at row 336 of the front view)

| Feature | Sheet | Spec | Decision |
|---|---|---|---|
| Stone footing | about 0.5 m, rough-cut granite, moss | about 0.5 m | Match the sheet |
| Top of wall incl. cap | about 1.85-1.9 m | top +2.0 | Build to 2.0 m |
| Thickness | about 0.6 m (end view) | 1.0 m (walkable top) | Keep 1.0 m for gameplay; widen the cap to match |
| Cap | a real pitched tile roof about 35-40 cm tall with a ridge and round ridge ends | a visual cap, flat 1.0 m walkable collision | Keep the sheet's look; collision stays one flat plane |
| Corner, wall end, section | mitred cap at the corner, a gabled end cap, earth fill inside | - | Adopt all three (corner, end and section pieces) |

**Gatehouse** (111.1 px/m, ground at row 516 of the front view)

| Feature | Sheet | Spec | Decision |
|---|---|---|---|
| Type | single line of heavy posts carrying a gable roof (a munamon-style gate), iron-strapped double doors, bracket lamps, granite threshold, plain upturned ridge ends | gatehouse, roof 8 x 5 m | Keep the sheet's design |
| Opening | about 3.3 m wide x 2.5 m tall | 4.0 x 3.5 m | Scale to the spec (proposed; confirm) |
| Eave / ridge | about 2.8 m / 4.0 m | +3.25 / +4.4 | Spec heights: the eave at +3.25 is the 1.25 m climb from the wall top (route 6) |
| Roof | about 6.2 m wide, shallow depth (about 2 m, one post line) | 8 x 5 m | Proposed: 8 m wide, about 4 m deep with a second (rear) post line, so the roof is a usable platform |

**Hall front** (1448x1086; front view 58.3 px/m, ground at row 474; side view 59.4 px/m)

| Feature | Sheet | Spec | Decision |
|---|---|---|---|
| Overall width | about 15.7 m (roof), deck about 15.1 m | 18 m body + 2 m veranda each side = 22 m | Build to the spec footprint |
| Depth | side view about 6.9 m; the top view is deeper (about 1.45:1), so the views disagree | 10 m body + 2 m front veranda | Spec |
| Bays | about 1.9 m | about 2 m | Match: 2 m bays, 9 across the 18 m body |
| Lower eave | about 3.0 m | +3.0 | Match |
| Upper eave | about 4.4 m | +5.5 | Spec (it sets the climb from the lower roof) |
| Ridge | about 6.9 m (about 7.1 with the ridge ends) | +8.3 | Spec |
| Veranda floor | about 0.75 m on a granite plinth | +0.5 | Spec height, the sheet's plinth look |
| Steps | one wide central stair of three steps, no band | a continuous band of two 0.25 m steps | Central stair as the sheet (two steps at 0.5 m). Whether the rest of the veranda edge needs a step band depends on the kit 0 GASP check: is 0.5 m a step-up or a mantle? |
| Front | 4-panel lattice sliding doors in the middle, lattice windows, cream plaster, lower wood panels, a lattice clerestory band between the roofs, 2 AC units, corner downpipes | same | Match |
| Roof form | hip-and-gable upper roof, gable to the sides, plain block ridge ends | same | Match |

**Roof details**
- Round-ended eave tiles with plain discs, fascia with square rafter ends.
- The ridge is stacked with plain block-and-disc ends; a faint radial line pattern on one verge disc is modelled as a plain disc.
- The hip-and-gable corner has a round hip roll.
- The gable end is dark vertical boarding with a king post and a plain disc on top.
- Verge boards, plus a half-round gutter on brackets and a round downpipe with two bends.
- No faces, creatures or symbols. Matches the prompt and the spec's 25 degree roofs.
- **Bonus:** the overview matches the spec layout. It shows lanterns flanking the hall stair, a well NE, a vending machine by the shed, and a stone step flight outside the gate. The small elevations are stand-in references for kits 5-8 until their own sheets arrive.

**Sheets 5-7** (estimated by eye from each 1.8 m silhouette, about +-15 cm; the spec wins on size, as before)

| Piece | Sheet | Spec | Decision |
|---|---|---|---|
| Storehouse | cream plaster; about 1 m granite base band; steel double door with a small tile canopy ON THE GABLE END; gable vent; about 5.4 m wide, eave about 3.7, ridge about 5.8 | 7.6 x 8.6 m, eave 3.25, ridge 5.25 | Spec footprint and heights; keep the gable-end door facing the courtyard |
| Residence | timber-framed cream plaster; about 0.9 m wood board base; wooden door + lattice window under one canopy; meter box + conduit | same footprint and heights as the storehouse | Same |
| Corridor | 3 bays of about 2.5 m (about 8 m long); posts on stone pedestals; closed side plaster over boards; open side lattice rail; floor about 0.4 m; eave about 2.0 m; roof tucks under both neighbours | about 3 m long, floor 0.5, roof 3.7 to 3.0 | Build as bay modules at spec heights and repeat them to fit the gap in the layout |
| Drum pavilion | granite plinth about 3.6 m square x 0.6 m; front stair of 4 steps; posts on stone pedestals; pyramid roof with a plain ball finial, eave about 2.7, apex about 4.2; bracketed eaves | plinth 4 x 4 x 1.0, roof 5.2, eave 3.25, apex 4.5 | Spec heights (the 1.0 m plinth is a climb surface), the sheet's design |
| Taiko | about 1.2 m across; red-brown body; tacked hides; ring handles; timber stand; 2 sticks; close-ups of the tacks, ring and joints | about 1.2 m | Match. SEPARATE asset from the pavilion (user decision): its own .blend + export; drum, stand and each stick are separate meshes |

No symbols, faces or text on any of the three sheets (the pavilion finial is a plain ball).

**Sheets 8-11**
- **Training shed (8):**
  - lean-to of corrugated galvanised steel on steel purlins;
  - two round pipe posts on concrete footing blocks;
  - a rear wall of dark vertical boards, set in front of the compound wall;
  - an empty 4-shelf wooden rack;
  - a packed-earth floor.
  - Proportions follow the prompt (roof high side at the wall). Decision: build to the spec, 6 x 5 m, roof 3.0 m falling to 2.5 m.
- **Courtyard stone (9):**
  - Lanterns: tall (about 2 m) and short (about 1.2 m). Each has a stepped base, a post with a panel, a light box with 4-pane windows (warm emissive) and a curved hipped cap with a plain ball finial. There is moss at the base.
  - Two well variants: a round block well with a plank-roofed frame, pulley, bucket and rope; and a lighter gable frame. The top view shows a plank cover with a crossbeam.
  - The cistern is a board tank with iron bands, corner posts on stone feet and a battened lid (a climb prop, 1.25 m).
  - No symbols.
- **Training props (10):**
  - rope-wrapped makiwara and a plain striking post, both on braced timber bases;
  - a wooden dummy (3 arms + leg) and a single long-arm dummy;
  - a weapon rack with top pegs and two rows of cradles, shown empty;
  - a long bench and two stools.
  - Every piece is a separate asset (the same rule as the taiko).
- **Modern props (11):**
  - `dojo_modern_props_ref.png` panel 11 shows:
    - a vending machine 0.9 x 0.8 x 1.75 m, teal and white with a blank front;
    - an AC unit on a stand;
    - a wall lamp;
    - a utility pole about 4 m with a crossarm and wires;
    - street lamps A (3.0 m) and B (2.5 m);
    - a junction box.
  - The views are small, so model from them plus the style guide.
  - Both boards carry dimension TEXT labels. That's fine for reference, but nothing from them goes into a texture. The boards also re-show pieces 1-10 with the SPEC numbers written on them. They're useful as a one-page summary, but they're labels, not measurements.

## Landscape reference (2026-09-30)
`dojo_landscape_ref.png` (1024x1536, converted from the user's webp; sha256 6114ad0a...). Supplied by the user in chat as the new target for the surroundings ("pivot for the landscape/surrounding area"). Provenance not stated; it looks AI-generated, so treat it as a look reference only.
Shows:
- the dojo compound on a raised terrace with a tall dressed-stone (ishigaki-style) retaining wall;
- a turquoise mountain river with white-water rapids and big rounded granite boulders along one side below the terrace;
- a stone stair path with wooden handrails and stone lanterns climbing the rocky, mossy cliff from the lower left up to the gate;
- cherry trees in full blossom everywhere (a big hero cherry in the foreground, along the river banks, around the compound);
- sculpted pines by the compound, conifer forest on the slopes;
- two snow-capped peaks beyond forested ridges;
- falling petals;
- a bright daytime sky with cumulus.
Replaces the wheat-field brief.

## Japanese pine sheet (2026-09-30)
`dojo_japanese_pine_ref.png` (ChatGPT, from the niwaki pine prompt with dojo_landscape_ref attached; sha256 00d7b60f...). Four niwaki black pines, each with front + side + 3/4 views and the 1.8 m silhouette:
1. small garden pine, ~2.5 m, curved trunk, 5-7 cloud pads;
2. medium, ~4.5 m, S-curved trunk, layered pads;
3. large leaning pine, ~7 m, long horizontal limb reaching out;
4. cliff pine on a granite boulder, roots gripping the rock.
Close-ups: dark plated/fissured bark with warm orange-brown in the cracks; a side view of a cloud pad (dense needle tufts on a flat, domed pad with the zig-zag branch structure under it); a pad from above (radiating needle rosettes); the branch fork structure. No text or symbols.

## Cherry petal sheet (2026-09-30)
`dojo_petals_ref.png` (1448x1086, ChatGPT from the petals prompt with dojo_landscape_ref attached; sha256 cf30b5a8...). FX reference for falling and fallen Yoshino petals. Shows:
- six single petals, front + back: broad obovate, a shallow V-notch at the tip, fine veins, pale pink to near-white with a stronger pink claw at the base; two curled, one folded (tube);
- the same six edge-on / 3/4, showing the thin cupped curve;
- a sunset-backlit drift of petals with rim glow and depth-of-field bokeh;
- a 3-5 blossom cluster on a dark twig (5 petals, yellow-tipped stamens, a pink bud) for scale and colour;
- fallen petals on grey granite pavers, on moss against a boulder, and on raked pale gravel, with browned old petals mixed in (roughly 1 in 8).
No text or symbols.

## River mist sheet (2026-09-30)
`dojo_mist_ref.png` (1448x1086, ChatGPT from the mist prompt with dojo_landscape_ref attached; sha256 c2587183...). FX reference for the river. Shows:
- low mist hanging over white-water rapids among rounded granite boulders, backlit gold/peach by a low sun, cherries and pines on the banks;
- a high-shutter spray burst against a boulder: large separate droplets and sheets, backlit;
- the same spray further back blurring into soft white mist;
- a thin haze layer drifting along the river surface at dusk, thinning with height;
- cut-outs on black: three soft mist wisps and two spray bursts (edge softness and density study).
Note: the water is turquoise-grey with white foam, which matches the landscape reference. No text, people or buildings.
