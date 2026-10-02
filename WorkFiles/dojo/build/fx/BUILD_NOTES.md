# DojoFX build notes (landscape round, FX stage, 2026-09-30)

Lock `DojoFX` (claude). Blender 5.2 headless only; no Unreal in this stage. Own folders: `Scripts/dojo/fx/`,
`Assets/Dojo/DojoFX.blend`, `Exports/DojoKit/FX/` (`SM_DKF_*`, `T_DKF_*`), `WorkFiles/dojo/build/fx/`.
Chain: `Scripts/dojo/fx/run_all.sh` (petal chain `run_petals.sh`). Recipe for Unreal: `fx_catalog.json`.

References: `References/Dojo/dojo_petals_ref.png`, `dojo_mist_ref.png` (both AI-generated look references; measured and
traced only, no reference pixel in any texture).

## Petals

**Method.**
- Outline: the mean silhouette of the sheet's four flat petals, front + mirrored back (16 samples), traced in a
  length-normalised frame (`measure_petal_ref.py --outline`, `ref/petal_outline.json`). The mean blurs the V-notch, so the
  notch depth is restored to the per-petal mean (gain 1.25).
- Colour: the sheet's band means (claw / lower / middle / upper / tip, front and back), converted to albedo by the grey-card
  ratio, `albedo = lin(petal) / lin(card) * 0.18` per channel (card measured 101/98/97 sRGB, which also neutralises its
  warm cast). The texture is painted with our own veins, claw, speckle and rim, then renormalised row by row so that each
  band's mean hits its target. The upper/tip targets are lifted 5-7 %, because the cup shading darkens the rendered rim.
- Meshes: a hull of the traced outline (8 rows x 4 or 6 columns, 56 / 84 triangles). UV0 is the flat pattern in the
  texture frame (0-1, no overlap) and UV1 is a copy of it. Shapes come only from developable bends of the flat pattern:
  cup, base / tip bend, twist, cylinder rolls, and a rest pose rotated about the length axis for C. So the texture never
  stretches.
- The sheet's six petals:
  - A, B, D and F are flat and cupped;
  - C is curled (a lengthwise curl lying on its side, which reads as the crescent from above);
  - E is folded into a cone (two tilted rolls).
- `PetalOld_A` is browned and crumpled, with a ragged outline shrunk to 0.9.
- Real size: 12.5-14.5 mm long.

**Numbers (sheet vs ours, `renders/sheet_final/ours_measure.json`, same measuring code on both).**

| | sheet | ours |
|---|---|---|
| flat petals W/L | 0.717 | 0.730 |
| notch depth / L | 0.075 | 0.077 |
| max width at (from base) | 0.561 L | 0.573 L |
| C (curled) W/L | 0.544 | 0.486 |
| E (folded) W/L | 0.468 | 0.487 |
| front claw / middle / tip sRGB | (210,138,157) / (201,176,180) / (198,176,177) | (203,141,160) / (202,178,185) / (197,179,182) |
| back claw / middle / tip sRGB | (193,159,164) / (183,166,168) / (185,168,168) | (157,137,142) / (184,170,174) / (186,174,176) |
| lying 3/4 view h/l (A B D F) | 0.41-0.46 | 0.34-0.40 |

**QA:** `qa_check` passes on all seven petal meshes: 0 fails, UV1 inside 0-1, no overlap. The drift clusters
`SM_DKF_PetalDrift_A/B/C` (1596 / 3052 / 5544 triangles, about 1 in 8 old petals) pass every check except
`uv_no_overlap`. That exception is by design: every petal copy shares the petal texture (TREE_BUILDING_STUDY 4.12 / P38),
and the full QA runs per petal unit.

**Decal:** `T_DKF_PetalScatter_BC/_N/_ORM` is a top-down Cycles bake of four 0.35 m scatter cells (sparse / medium /
dense drift / strays) in a 2x2, 2048 px atlas, at 2.9 px/mm:
- albedo is taken from the Diffuse Color pass, with transmission zeroed for the bake;
- the tangent normal is the world normal (top view), with G flipped for DirectX;
- the alpha is film coverage, and the passes are un-premultiplied.

**Rejected / open (petals):**
- the back claw reads darker than the sheet's: it's the curled base in shade in our back view, not the texture;
- the lying views are a little flatter than the sheet's;
- C is narrower than the sheet's crescent;
- the fallen tests use our kit's ground maps (T_DJ_Granite, T_DKN_Moss, T_DKG_Gravel), not the sheet's surfaces. They
  test the petals, not the ground.

## Mist, spray, haze, foam

**Flipbooks.**
- Each is 64 frames, 8 x 8, 512 px cells, so the atlases are 4096.
- Colour-neutral: white media lit by six white suns, each in its own Cycles light group. One render per frame gives all
  six directional passes plus the film alpha.
- Packing (`render_flipbooks.pack`):
  - the passes are coverage-weighted, so they are divided by max(alpha, 0.5). This keeps the thin, feathered edges dim;
    a floor of 0.15 gave white halos;
  - a 3x3 binomial blur removes the grain of the undenoised light-group passes;
  - there is one normalisation factor per flipbook (the p99.5 of all six passes).
- The flipbooks:
  - `MistPuff` and `MistWisp` are procedural volumes: a warped 4D fBm, eroded, inside a lumpy growing ellipsoid, with a
    life fade;
  - `SprayBurst` is a **method change** (see below);
  - `Haze` is one 2048 x 1024 render of a flat, soft bank.

**Spray method change.**
- Rounds 1-3 of a point-sprite spray failed decisively. They read as beads and brown dust with no water sheets (a
  crown of point sheets gave a blocky "cone").
- A Mantaflow FLIP sim replaced it:
  - a 0.18 m-deep pool in a 3.4 x 1.4 x 2 m domain, at resolution 176;
  - a 6.5 m/s surge, inflowing for the first 0.2 s, runs into an ellipsoid boulder (collision effector, hidden in the
    render). The bake takes about 100 s;
  - the sheet climbs the rock face, tears into fingers and droplets, then falls.
- Rendering:
  - the water is white, 45 % translucent (aerated);
  - the pool and the crater surge ring are faded out below the water line with a noise-broken edge, and faded toward
    the window's sides;
  - fine droplets (points) and a soft base-mist volume start when the surge hits (18 % into the life);
  - the camera window is 1.3 m.
- A first sim, a blob dropped into a pool, gave a wide, low crown whose surge ring read as a flat slab. It was dropped
  for the boulder case, which is the river's own situation.
- Mantaflow's baked mesh `velocity` attribute read 0 with cache type ALL, so a speed-based fade was not usable.

**Measurements vs the sheet's cut-outs** (`json/mist_measure.json`, same code on both; the sheet's alpha is estimated
from luminance on black):

| cut-out | aspect w/h sheet / ours | fill sheet / ours | feather sheet / ours | core p95 sheet / ours |
|---|---|---|---|---|
| puff (MistPuff f26) | 1.70 / 1.48 | 0.62 / 0.61 | 0.58 / 0.42 | 0.92 / 1.00 |
| wisp (MistWisp f22) | 2.13 / 1.77 | 0.59 / 0.50 | 0.68 / 0.63 | 0.88 / 0.77 |
| plume (MistWisp f40) | 1.24 / 1.85 | 0.60 / 0.60 | 0.73 / 0.46 | 0.79 / 0.95 |
| bank (Haze) | 2.03 / 2.24 | 0.77 / 0.69 | 0.57 / 0.50 | 0.93 / 0.91 |
| spray crown (SprayBurst f22) | 1.34 / 1.13 | 0.48 / 0.36 | 0.64 / 0.10 | 0.87 / 1.00 |
| spray column (SprayBurst f34) | 1.00 / 0.99 | 0.55 / 0.46 | 0.69 / 0.11 | 0.86 / 1.00 |

- Cell usage: MistPuff 0.76 x 0.48 of a cell (max), MistWisp 0.78 x 0.41, SprayBurst reaches the cell edges (the
  droplets).
- Render time: MistPuff / MistWisp about 6 min each at 256 spp. The spray is about 100 s of bake plus about 3 min of
  render.

**Foam.**
- `T_DKF_Foam_M` / `_N` are 2048, built on the torus: FFT fBm plus periodic Voronoi at two scales (lace rims, bubble
  holes, dense patches, flow streaks along V).
- Seam proof: the Voronoi evaluated half a period further equals the rolled field to 4e-15.
- Coverage mean is 0.26.

**Open (mist / spray), honest state.**
- **Mist lighting.** Under one key, the dense mist cores read darker than their rims, while the sheet's mist is brightest
  in the core. The puff is also too opaque in the core (p95 1.0 against 0.92), and its edge is harder than the sheet's
  (feather 0.42 against 0.58).
- **Next step (method, not tuning).** Add an ambient / sky light group as a seventh pass, stored in `SixWayN.A` (the
  Unity six-way layout keeps emissive there). Lower the density about 2x and enlarge the envelope so the content fills
  the cell height (it uses only 48 % now).
- **Plume.** There is no dedicated vertical plume. The "plume" cut-out is compared with a late wisp frame, so its aspect
  is wrong (1.85 against 1.24). A third mist flipbook (a rising plume) would close this.
- **Spray.** The spray has the sheet's structure: a sheet up the rock, torn fingers, droplets. It is smoother and more
  "gel"-like than the sheet's foamy splash, and its edge is far harder (feather 0.10 against 0.64: a liquid surface has a
  hard edge; the sheet's splash has a misty halo). A larger base-mist volume, plus Mantaflow spray/foam secondary
  particles (`use_spray_particles`) rendered as tiny points, would add the halo and the white froth.
- **Preview only.** The sunset-lit previews (`compose_mist.py`) use the catalog material formula with a guessed sun
  direction and sky colour. The real look must be judged in Unreal under the UDS sun.
