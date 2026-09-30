# Stone study A: the craft of believable stone (engine-agnostic)

**Written:** 2026-09-30, research only (web + local files, no Unreal project opened, no MCP tools). **Scope:** a
durable reference for EVERY future stone build in this repo: dressed and rough masonry walls (Japanese ishigaki:
nozura-zumi, uchikomi-hagi, kirikomi-hagi; dry-stone; rubble; ashlar), stone steps, paving and kerbs, footings, stone
lanterns and carved stone, and natural rocks and boulders (river boulders, cliff rocks, rocks that trees grow from).
**First clients:** the dojo stone kit rebuild (terrace ishigaki + stair path, `WorkFiles/dojo/build/stonekit/`) and the
D-pine rock (`WorkFiles/dojo/build/pines/`).

Tags: **[UNCERTAIN 5.2]** / **[UNCERTAIN 5.8]** = not verified on this machine's Blender 5.2 or Unreal 5.8.
**[SECONDARY]** = the source is a forum, a search-engine summary or a blocked (403) page, not a primary document.
**[LOCAL]** = measured or read here, in this repo or in the owned content folders. Numbered sources are at the end.

---

## 0. The twelve rules (read this if nothing else)

1. **Stone is read by its form shading, not its texture.** Each stone must carry a real light-to-shadow gradient
   across its crown and a dark shadow where it meets its neighbours. Measured [LOCAL, §1.2]: the reference wall's
   luminance spread (p25-p75) is 0.40-0.70; our f1 wall was 0.47-0.56 (flat crowns), our r0 wall 0.22-0.36 (dark,
   chocolate). Neither had the range. Fix the geometry and the joints before touching the material.
2. **Classify before you build.** Every stone asset is one of a small number of kinds (Section 2-6): natural field stone
   (nozura), roughly dressed (uchikomi), cut (kirikomi / ashlar), river-rounded (tamaishi), jointed-and-rounded
   bedrock blocks (corestones, tors), or fresh angular fracture (talus). Each kind has its own edge radius, face
   flatness and joint width. Mixing kinds in one wall is the fastest way to look wrong.
3. **Real edges are rounded in proportion to exposure, not uniformly.** Weathering attacks corners fastest, then edges,
   then faces [12]; river abrasion rounds edges first while the axes stay put [13]. So a boulder is a *rounded block*
   (flat-ish faces, big soft arrises), not a blob and not a faceted polyhedron.
4. **Joints are dark and deep, never bright.** In dry masonry the joint is a void or packed small stone in shadow; in
   the dojo references it is 7-17 % of the wall area below luma 0.2 [LOCAL]. Bright, flat or "pebbled" joints read as
   CG at once (our r0 judge).
5. **Stone size falls with height; big stones at the foot and corners.** Ishigaki uses ne-ishi (root stones) at the base
   and dressed sumi-ishi at the corners [2][5]; dry-stone walls grade biggest at the bottom [11].
6. **Stones go in long axis INTO the wall.** Ishigaki face stones show their short end; the long side runs back into the
   bank [2]. So a face stone is roughly as deep as it is wide or deeper, and the visible face is a *pillow end*, not a
   thin tile. Model a real depth behind the face or the edge silhouettes will betray it.
7. **Corners are a different construction.** Sangi-zumi: long stones with the long side 2-3 x the short side,
   alternating left/right each course, with 1-2 kadowaki-ishi (corner-side stones, 1-2 x the short side) tucked
   beside each short end [6].
8. **Batter is a curve, not a plane, on tall ishigaki.** Temple slope (tera-kobai / ogi-no-kobai): straight and gentle for
   the lower half (Kumamoto: about 2/3 at ~45 deg), then curving to near vertical at the top [7][SECONDARY]. Low
   terrace walls (1-4 m) are nearly straight.
9. **Growth follows water.** Moss sits in joints, on ledges and tops, on shaded faces and at the wall foot; lichen spots
   the exposed faces; dark water streaks run down from joints and ledges [15]. Never tint whole faces green.
10. **Ground it.** Boulders are buried a third to two thirds, the widest part at or below grade [19][SECONDARY]; debris
    and smaller pieces of the SAME rock gather at the foot. Floating stones and clean contact lines are the classic fake.
11. **Measure against the reference, not the judge.** Two of our stone rounds followed a blind judge the wrong way
    (round 1 footing, stone kit f1: "pale polygonal stones"). The judge is a detector, not a spec. Measure stone size,
    aspect, joint fraction and value spread on the reference (Section 10), then build to the numbers.
12. **If a construction does not converge, change the method.** Our procedural natural assets (sand, mountains, the
    faceted D-pine rock) were the weakest; built-from-a-sheet man-made stone was the strongest. For natural rock the
    method is "real jointed block, then weathered" (Section 7) or an owned scan, never noise on a sphere.

---

## 1. Our own evidence (what failed, what worked)

### 1.1 Timeline [LOCAL: `WorkFiles/dojo/DOJO_QUEUE.md`, `WorkFiles/dojo/build/stonekit/BUILD_NOTES.md`, `wall/BUILD_NOTES.md`]

| Round | What we built | Judge | What the judge / our look said |
|---|---|---|---|
| Kit 1 r1 | Wall footing as rounded rubble | 5 | Judge 1 steered to "rough-hewn, chisel-faced polygonal rubble" |
| Kit 1 r2 | Polygonal shards (`kit1_geo.hewn_stone`) | 6 → 5.5 | Wrong way: the sheet is ROUNDED pillow rubble under one dressed course |
| Kit 1 r3 | `kit1_geo.pillow_face` footing: quarter-round shoulder, flat-topped superellipse crown, two octaves of real relief | 7.5 final | "Closest piece to its sheet" |
| Stone kit r0 | Terrace ishigaki + stair path, pillow stones in courses, pebbled `M_DK_JointEarth` joints | 6 | Uniform pillows, wide pebbled joints, one pitted "sponge" material, chocolate at sunset, steps had no nosing |
| Stone kit f1 | `lay_courses` 5-7-sided convex polygons, flat crowns (bulge ≤ 1.4 cm), thin joints, pale granite | 5.5 | Followed the judge into pale polygonal stones, long tread slabs, crazy-paving landings. Judge 2 and our reading: the reference is rounded mid-grey stones with moss in joints |
| Pines f1 | D-pine rock: 3 convex masses chipped by 26 planes, then hulled | (tree 4.5) | "A big faceted block"; the sheet shows a multi-lobed, craggy, lichened rock with 8-12 wrapping roots |
| Courtyard lanterns | Granite lanterns | 6.3 → 6.5 | Stone texture stretched/mirrored, cap (kasa) too thin |

**Lessons that generalise:**
- The two best stone results (kit 1 r3 footing, the kit 1 wall's dressed blocks) were **modelled stones with a real
  crown and shoulder**, built from an outline taken off the sheet.
- The two worst were **plane-chipped convex hulls** (hewn shards, the D rock): flat facets + sharp creases read as
  low-poly, not as stone.
- Both "polygonal" steers came from ONE judge and contradicted the sheet. Measuring the sheet would have stopped both.

### 1.2 Measured value and joint statistics [LOCAL]

Measured with PIL on the reference crops the stone kit already uses and on our renders (luma = Rec.709 on sRGB
values; "dark" = luma < 0.20; local std = mean standard deviation of luma in 16 px blocks). Scales differ between
crops, so compare the pattern, not the third decimal.

| Image | luma p5 / p25 / p50 / p75 / p95 | dark | R/B | local std |
|---|---|---|---|---|
| Ref, terrace wall stone faces (`f1/refcrops/ref_stone_faces.png`) | 0.17 / 0.40 / 0.58 / 0.70 / 0.85 | 7.0 % | 1.33 | 0.056 |
| Ref, lower wall (`ref_wall_lower.png`) | 0.12 / 0.25 / 0.47 / 0.64 / 0.83 | 17.1 % | 1.40 | 0.074 |
| Ref, terrace wall wide (`ref_terrace_wall.png`) | 0.13 / 0.29 / 0.49 / 0.70 / 0.87 | 12.8 % | 1.35 | 0.092 |
| Ref, wall sheet footing (`dojo_wall_ref.png` 118,272-605,332) | 0.09 / 0.26 / 0.34 / 0.42 / 0.55 | 14.7 % | 1.23 | 0.128 |
| Ref, river boulders (`dojo_landscape_ref.png` two crops) | 0.06-0.08 / 0.19-0.21 / 0.26-0.42 / 0.56-0.75 / 0.82-0.86 | 22-27 % | 1.17-1.24 | 0.136-0.149 |
| **Ours f1** `f1/close_stone_faces.png` | 0.21 / 0.47 / 0.52 / 0.56 / 0.59 | 4.7 % | 1.45 | 0.058 |
| **Ours r0** `wall/close_stone_faces.png` | 0.07 / 0.22 / 0.31 / 0.36 / 0.41 | 22.5 % | 1.71 | 0.058 |

Readings:
- **f1 has no highlights and no deep shadow.** p95 0.59 against the reference's 0.83-0.87; the dark fraction is a third of
  the reference. The flat crown (≤ 1.4 cm bulge) removed the lit top / shaded shoulder gradient that the reference
  stones all show.
- **r0 is too dark and too red** (median 0.31, R/B 1.71 vs 1.33-1.40). That is the "chocolate" call.
- **The sheet footing and the boulders have about twice our local contrast** (0.128-0.149 vs 0.058). That contrast is
  form shading (crowns, cracks, undersides), not texture speckle.
- The strict "green" count was near zero everywhere: the reference moss is olive-yellow (R ≈ G), so a moss mask test
  must use hue ~50-80 deg, not "G > R".

### 1.3 What the references actually show [LOCAL, looked at + crops]

- **`dojo_wall_ref.png` (compound wall footing):** rounded-rectangle, pillow-faced field stones, about 0.25-0.5 m, mostly
  wider than tall, in rough courses; one course of squared blocks on top; deep dark joints; moss patches low and in
  joints; the corner and pier bases use larger squarer blocks. Stone type: **uchikomi-hagi, nunozumi-leaning**.
- **`dojo_landscape_ref.png`, terrace wall by the river:** rounded lens/egg-shaped stones, many **upright** (taller than
  wide), strong crown shading, dark irregular joints 2-4 cm, grass and moss tufts growing out of the joints. Stone type:
  **nozura-zumi / ranzumi** (natural stones, random bond).
- **Same image, upper terrace near the gate:** squarer blocks with softly rounded arrises in near-level courses:
  **uchikomi-hagi nunozumi**. So one scene holds two wall kinds; each wall piece must be told which it is.
- **Steps (lower left):** long single slabs per step on the lower flight, lighter worn treads, darker risers, rounded
  nosings; landings of large flat flags.
- **Boulders and cliff (river banks, left cliff):** granite as **rounded cuboids**: flat-ish faces meeting at big soft
  arrises, split by a few deep straight cracks (joint planes); the cliff is stacked jointed blocks with vertical
  fractures (a tor/cliff of columnar-jointed granite); moss on tops and ledges only; smaller rounded stones at the water.
- **`dojo_courtyard_stone_ref.png` lanterns:** Kasuga-type granite lanterns: carved square/hex parts with bush-hammered
  texture, softened arrises, lichen/moss specks on the kasa top and around the base.
- **Pine D sheet:** a multi-lobed craggy rock (several fused rounded blocks with deep clefts), yellow-grey lichen, moss
  cushions in the clefts and on top, roots entering the cracks.

---

## 2. Japanese masonry (ishigaki)

### 2.1 Three processing grades (how much the stone is worked)
| Grade | Stone | Joints | Surface | Read |
|---|---|---|---|---|
| **Nozura-zumi** 野面積 (field-stone) | Natural or roughly split stones, sizes vary greatly; sedimentary and igneous; builders reused mill stones etc. [1] | Wide, irregular; gaps packed with small stones (ma-zume-ishi) [5][2] | Natural weathered faces | Oldest (late 16th c.). Gentle, linear slope [1]. Many footholds, cannot go very high [3] |
| **Uchikomi-hagi** 打込接 (pounded-and-fitted) | Corners and face knocked flat to cut the gaps [3][5] | Smaller; small stones still fill the remaining gaps [3] | Dressed, bumpy-flat faces, rounded arrises | After Sekigahara (1600); fan-shaped slopes, corners in sangi-zumi [1] |
| **Kirikomi-hagi** 切込接 (cut-and-fitted) | Cut to fit, rectangular or polygonal, "without gaps" [1][3] | Hairline; drain holes needed because water cannot seep [3] | Chisel-dressed; sometimes only the margins dressed and the centre left rough (Kanazawa's *kaneba-torinokoshi*) [4] | Early Edo; gates and show faces |

Plus **tamaishi-zumi** 玉石積 (river-rounded stones, limited height) [3][5].

### 2.2 Laying patterns (how stones are arranged on the face)
- **Nunozumi** 布積: stones of similar size in level rows; the bed joints run through horizontally [3][5].
- **Ranzumi** 乱積: sizes vary, no continuous rows [3][5]. Most nozura walls are ranzumi.
- **Tanizumi / otoshizumi** 谷積 / 落し積: stones set diagonally, like a valley pattern (later Edo) [3][5].
- **Kikkō-zumi** 亀甲積: hexagonal (5-6-sided) cut stones [3][4]. **Our f1 polygons drifted into this look**, which is a
  kirikomi pattern, not what the dojo references show.
- **Warai-zumi** 笑い積: large stones ringed with small ones [5].
- **Kagami-ishi** 鏡石: a very large "mirror stone" set in a gate face for show [4]. Osaka's Tako-ishi is about
  5.5 x 5.5 m, ~108 t [2].

### 2.3 Parts of the wall (what is behind the face)
- **Tsuki-ishi** (face stones): short end on the face, long side into the bank [2].
- **Kai-ishi** 飼石 (wedge/shim stones) at the back and under the face stones to stop rocking; **ma-zume / tsume-ishi**
  間詰石 (packing stones) in the visible face gaps [2][5][8].
- **Uragome / guri-ishi** 裏込/栗石: fist-sized rubble backfill behind the face, for drainage [2][9].
- **Ne-ishi** 根石 (root/base stones): the largest, carry the load [2]. **Tenba-ishi** 天端石: the top course [5].
- **Sumi-ishi / sumiwaki-ishi** (corner and corner-side stones): see 2.4.
- Craft rule from the Anō-shū tradition: placement ("suekata") over stacking; "let the stone go where it wants to go"
  [8][9]. For us: each stone sits on 2-3 contact points on the stones below, and its outline follows its neighbours.

### 2.4 Corners: sangi-zumi 算木積
- Long corner stones, **long side 2-3 x the short side**, alternating long/short to each face every course [6].
- **1-2 kadowaki-ishi** beside each short end, about **1-2 x the short side** [6]. Degenerate late examples have a
  1.5 x ratio [6].
- The arris of a batter corner sweeps upward (the corner line is the steepest line of the wall) and is often the
  best-dressed stone in the wall.

### 2.5 Batter and curve (kōbai and sori)
- **Tera-kōbai** 寺勾配 (temple slope / ogi-no-kōbai, fan slope): gentle straight lower part, then steepening to near
  vertical at the top [2][7]. The usual rule: straight to half height, curve in the upper half [7]. Kumamoto's small
  keep base: straight at about 45 deg for the lower two thirds, then the curve [SECONDARY, search summary of [7]].
  Marugame: the curve starts about half way; the tallest single wall is about 22 m [10][SECONDARY].
- **Miya-kōbai** 宮勾配 (shrine slope): straight, no curve [2][7].
- Pre-1600 walls were gentler; Keichō-era (1596-1615) walls got steeper [7].
- **Our d(s) = 0.10 s + 0.035 s² profile** (6 deg off vertical at the top, 27.5 deg at 6 m) is a reasonable low-wall
  tera-kōbai. Low garden/terrace walls (1-4 m) in the references read nearly straight; keep the curve subtle below 3 m.

### 2.6 Surface marks and wear on dressed stone
- **Ya-ana** 矢穴: rows of wedge holes from splitting, left on some faces [2].
- **Hatsuri-shiage**: an even field of ~1 cm chisel marks; **sudare-shiage**: striped (blind-like) tooling [2].
- **Kokuin** 刻印: carved crests/marks [2]. (IP: invent our own marks; never a real clan crest.)
- Stone colour can vary within one wall by quarry: Kanazawa's Tomuro stone comes as reddish-grey "aka" and blue-grey
  "ao" [4]. A 2-3 hue family per wall is authentic, one flat colour is not.

---

## 3. Dry-stone, rubble and ashlar (the Western vocabulary, same physics)

- **Batter:** each face leans in; typical 1:6 to 1:10 (run:rise); the width under the coping is about half the base [11].
- **Two faces + hearting:** a free-standing dry wall is two skins with the core packed by smaller, flat or angular
  stones (rounded hearting "acts like ball bearings") [11].
- **Through-stones** span the full width, about every 0.9-1 m along, at about half height (or at 0.5 and 1 m) [11].
- **One over two, two over one:** every vertical joint is crossed by the stone above; no straight joint runs through
  two courses [11]. (Our wall's module "teeth" do this at the seams; keep it inside modules too.)
- **Size grading:** the biggest stones at the foundation (often partly buried), smaller toward the top [11][SECONDARY].
- **Coping:** a top course of large stones, all at the same angle, not projecting past the faces [11].
- **Rubble** (random or coursed) = the same logic with mortar; **ashlar** = sawn/dressed rectangular blocks in level
  courses with thin, straight joints (the kirikomi / nunozumi equivalent). Ashlar joints are millimetres, rubble joints
  centimetres. Joint width is a style parameter, not a free variable.

---

## 4. Steps, paving and kerbs

### 4.1 Steps
- **Geometry:** outdoor stone risers typically 150-180 mm [20]; garden steps are gentler, rise 100-150 mm with a going of
  300-400 mm [20][SECONDARY]. Japanese building code allows much steeper house stairs (riser to 230, tread to
  150 mm) [20]. The usual comfort rule (2R + G ≈ 600-650 mm, Blondel) puts our 1/6 m riser with a 1/3 m tread at 667 mm:
  slightly long, fine for a path.
- **Treads:** block steps (solid stones, the reference's type) vs slab treads on risers (30-60 mm thick slabs) [20].
  The reference's lower flight uses one long block per step; a 1.2-1.8 m step of one stone is plausible for granite.
- **Nosing:** stone nosings project about 25-38 mm when there is a separate riser [20]; solid block steps have no
  overhang, only a rounded front arris. Our f1 put a 4 cm set-back on block steps; check this against the reference
  rather than a code number.
- **Wear:** foot traffic hollows the tread in the middle, deepest a little behind the nosing, sloping forward; old stairs
  can wear up to about 75 mm deep in the centre, while light-use stairs show a shallow, spread-out dip [20][SECONDARY].
  The nosing rounds and chips most where people step; the tread ends stay sharper and gather moss and dirt.
  Treads polish lighter than risers.

### 4.2 Paving and paths
- **Shin / gyō / sō:** formal (shin) = cut stones fitted close; semi-formal (gyō) = cut and natural stones with small
  gaps; informal (sō) = stepping stones or gravel/earth [18].
- **Nobedan** 延段: a paved strip of cut and/or natural stones; **ishidatami** 石畳: mixed stones laid into a strip about
  the size of a tatami, 1.8 x 0.9 m [18][SECONDARY].
- **Tobi-ishi** (stepping stones): about 10 cm apart, closer over water, set a few centimetres proud of gravel or moss
  [18][SECONDARY]. Their tops are flat and nearly level; the sides go down into the ground.
- **Flags:** thick stones with flat tops, joints filled with sand, soil or moss. Real flags tilt a few millimetres
  relative to each other; the edges are slightly lower than the centre where feet round them.

### 4.3 Kerbs and edges
- Long rectangular stones set on edge, mostly buried, the top 5-15 cm proud; ends butt with thin joints. Wear shows as a
  rounded top outer arris and chips; moss and grass grow along the soft (soil) side.

---

## 5. Stone lanterns and carved stone

- **Parts (top to bottom):** hōju (jewel finial), ukebana (lotus seat), kasa (roof, corners may curl up into *warabide*),
  hibukuro (fire box), chūdai (platform), sao (shaft, set into the base), kiso (base) [17]. Mostly carved granite [17].
- **Carving reads as carving:** crisp primary planes (the kasa slopes, the hibukuro openings) with softened arrises;
  a bush-hammered or chisel texture on broad faces; smoother on turned parts.
- **Weathering on carved stone:** tops (kasa, chūdai ledges) collect lichen, moss and dark water stain; drips run from
  the kasa corners; the base gets moss and soil splash; faces toward the sun stay paler. Our lantern judge's calls
  (mirrored texture, kasa too thin) are both classic tells: carved stone needs per-part UVs with no mirroring, and the
  kasa is a thick block with a real eave depth.
- Same rules for any carved stone (pedestals, basins, markers): primary planes crisp, arris radius small but never
  zero, weathering concentrated on tops and horizontal ledges.

---

## 6. Granite surface character

- **What granite is:** quartz (grey, glassy), feldspar (white to pink or cream, the bulk), and a few per cent of dark
  mica (biotite). Inada granite: 3-4 mm grains, 34 % quartz, 62 % feldspar, 4 % biotite, light grey [16]. Aji granite
  is fine-grained and blue-grey with small black mica specks [16][SECONDARY]. **So the black speckle is sparse and
  small.** Our round 2 "terrazzo" granite had speckles too big and too contrasty.
- **Scale ladder** (what each LOD must carry):
  - grain 1-5 mm: speckle in the albedo, nearly invisible past 3-5 m;
  - tool marks 5-20 mm (dressed stone only);
  - pits and weathered grain relief 2-10 mm (feldspar decays first, so old faces are rough and grainy);
  - chips and spalls 2-10 cm at arrises;
  - cracks and joint planes 10 cm to metres;
  - the stone's crown and arris rounding (the form).
- **Weathering:** exposed granite rounds at corners and edges first [12], goes grainy (grus), and stains with iron
  (rust-brown streaks) and organic grime (grey-black streaks below ledges and joints).
- **Value and colour:** weathered granite is a light-mid grey with warm or cool bias per quarry. A PBR guide gives
  granite grey albedo about 0.35-0.40 linear [34][SECONDARY], which is fresh stone; old wall stone is darker from
  grime and lichen. Our library `Granite` v2 is about sRGB (115, 111, 106) ≈ 0.16 linear, and the f1 wall tint
  about 0.25 / 0.22 / 0.20 linear. **Do not pick an albedo from a chart: match the reference's rendered value
  distribution (1.2) under the scene's own light.**
- **Lichen on granite:** crustose lichens favour siliceous rock like granite; colours range from pale grey-green and
  yellow-green to grey-brown and near-black crusts; some species prefer full sun on exposed boulders [15]. They are
  discrete rounded patches 1-10 cm, not a tint.
- **Moss:** needs moisture and shade: joints, ledges, tops that hold water, north/shaded faces, the foot where soil
  splashes [15]. Colour olive to yellow-green in sun, darker green in shade.

---

## 7. Natural rocks and boulders

### 7.1 How granite boulders form (the shape logic)
1. **Joints first.** Bedrock is cut by 2-3 sets of fracture planes into rough cubes or prisms; joint spacing sets the
   block size [12].
2. **Rounding from outside in.** Weathering along the joints attacks corners most, edges next, faces least, so the
   blocks round into **corestones** inside the weathered layer; concentric shells (rindlets) peel off [12].
3. **Exhumation.** Erosion strips the weathered layer and leaves corestones as free boulders or stacked **tors**; on
   large domes the same process peels sheets (**exfoliation**) [12].

**Consequence for modelling:** a granite boulder is a *jointed block with rounded arrises*. Faces are broad and nearly
flat or gently convex (they are old joint planes), edges have a large radius (10-30 % of the block size), and a few
deep straight cracks (unopened joints) cross it. This is exactly what the landscape reference's boulders and cliff
show. It is neither a sphere with noise (the "potato") nor a plane-chipped hull (our D rock).

### 7.2 River boulders
- Abrasion runs in two phases: **(I) edges and corners round fast while the axes barely change**, losing up to ~50 % of
  the mass, until the stone is fully convex; **(II) the convex stone then slowly shrinks toward rounder axis ratios**
  [13]. Phase I happens within the first km or so of transport [13].
- Curvature drives it: protruding (positive-curvature) parts wear; flat and concave parts are protected [13].
- So river boulders near their source (our mountain river) are **rounded blocks that still show their joint-block
  proportions**; far downstream they are smooth ellipsoids. Spherical shapes travel farthest, discs least [14]
  [SECONDARY]. Wet zone: darker, smoother, no lichen below the high-water line, moss and a stain band above it.

### 7.3 Cliff rock and talus
- Cliffs expose the joint sets: long straight fracture lines, stepped ledges where horizontal sheeting joints cross,
  blocks detaching along the joints. Ledges collect soil, moss and plants.
- Fresh rockfall (talus) is **angular** with sharp edges and clean faces; it rounds only with time. Use sharp-edged
  pieces only for fresh breaks, scree and quarry spoil.

### 7.4 Rocks that trees grow from
- Roots enter along existing cracks and joints, wedge them open, and hug the rock surface as flattened, fused roots
  heading downhill to soil. Moss and soil build up in the clefts and at the tree base. The rock is usually several
  fused or split blocks (the pine D sheet: multi-lobed, deep clefts). Build the cracks first and route roots through
  them; then the trunk's flare sits in soil-filled clefts, not on a smooth top.

### 7.5 How rocks sit in terrain
- **Burial:** a third to two thirds below ground, widest point at or below grade [19][SECONDARY]; the Sakuteiki's
  principle is to set stones as nature would, following the stone's own character [36].
- **Contact:** soil and small debris bank against the uphill side; grass and moss close the contact line; nothing
  shows a clean intersection line.
- **Families:** a hero rock is surrounded by mid pieces and chips of the *same* rock and colour, dropping in size away
  from it (the "hero + scatter" set, Section 8). Clusters of 3, 5 or 7 in scalene triangles is the Japanese garden
  grammar [19][SECONDARY].
- **Orientation:** jointing and bedding are consistent within an outcrop; neighbouring rocks share the same crack
  directions. Randomly rotated rocks break this and look placed.

### 7.6 Where moss, lichen and soil go on a rock
- Moss: tops that hold water, horizontal ledges, clefts, the shaded side, the base. Lichen: exposed faces and tops in
  sun, round patches. Soil: clefts and the uphill base. Water stain: dark streaks down from where water sheds
  (cleft mouths, ledge lips). All of these are **masks driven by geometry** (up-facing normal, cavity/occlusion,
  distance to ground, a directional "shade" axis), plus noise to break them.

---

## 8. How AAA games and scan libraries build stone

### 8.1 The approaches
| Approach | How | Strength | Weakness | Use here for |
|---|---|---|---|---|
| **Scan library (Megascans on Fab)** | Photogrammetry hero rocks with LODs + "scatter" small rocks; tiling surfaces up to 8K [32] | Real forms, real value range | Not our design; licence limits for resale in Fab packs; 8K default textures give texel mismatches when kitbashed [32][SECONDARY] | Game-only natural rock (river, cliffs) if the user approves; never in a Fab stone pack |
| **Kitbashed assemblies** | Many instances of a few scanned rocks combined into cliffs; Valley of the Ancient is ~90 % Megascans, uses Packed Level Instances and bends meshes in Modeling Mode with no UV rework [24]; Electric Dreams ships a "PCGLargeAssembly" cliff built from assemblies [25] | Huge variety from a small set | Needs a good base set; seams hidden by overlap | Cliffs and river banks from our own 5-10 rock "parts" |
| **Grey-box proxy → sculpt** | Ghost of Tsushima: a grey-box rock collection proxies, then high-res sculpts used across the island [26][SECONDARY] | Level design first, art second; one set reused everywhere | Sculpting skill | The process model for our rock set |
| **Tileable sculpted wall surface** | Sculpt a tileable wall patch (stone shapes all different, edges checked for tiling), bake height/normal/AO/curvature, build the material from those (gradient maps, directional-warp water streaks, moss by normal) [21][22] | Cheap, great at mid/far distance | Flat silhouette, repetition | Far walls, LOD/impostor for our walls |
| **Modelled unique stones (Nanite)** | Each stone is geometry | Real silhouettes, shadows and joints | Tri counts (our walls 40k-390k per piece) | Near walls, footings, steps (what we do) |
| **Trim sheets** | Strips of dressed edges/mouldings on a shared texture | Very cheap for carved/dressed parts | Poor for natural stone | Coping, kerbs, lantern mouldings, step nosings |
| **Material layering on vertex colour** | Height-blended layers (stone / moss / dirt / wet) driven by vertex colour × heightmap; Naughty Dog blends A-B and B-C pairs sharing B so any two materials meet seamlessly; moss lightened with Fresnel [27][SECONDARY][30] | Per-instance variation without new textures | Needs enough vertices or a mask texture | Moss in joints, wet bands, grime per stone |
| **Unique normal + mask per rock, tiling detail** | Local example: Fishermans_Cabin `SM_Rocks_01..04` ship `T_Rocks_N` + `T_Rocks_Mask` per rock and a tiling `Tiling_Textures/Rock/T_Rocks_D/N/R/DP` [LOCAL, names only] | Unique form + sharp close-up detail at low cost | Two UV sets / triplanar cost | Our boulders and hero rocks |
| **Procedural rock generation** | Houdini example: airtight base, Worley F2-F1 macro displacement ("best for blocky, cellular shapes"), planar strata slices with per-layer transforms, several noise octaves with normal blur between, noise-warped noise; bake to low, texture with triplanar scans [23] | Endless variants | Looks like noise if the macro form is wrong (our experience) | Only as the "weathering" stage on a jointed block, never as the whole method |
| **Far distance** | Horizon: rock faces at ~300 m reduced to heightmap terrain that looks the same [28] | Budget | — | Mountains/cliffs beyond the playable area |

### 8.2 What the pros repeat
- **Primary forms first:** big planes and the silhouette, then secondary (cracks, chips, ledges), then tertiary (grain,
  pits). Hard-surface "trim" and "planar" brushes make the flat facets that separate rock from clay [23][SECONDARY].
- **Every stone has its own story:** different sizes and proportions; rotate and offset each stone a little so the
  normal/height bake has life [22].
- **Rest areas:** balance detailed zones with calm faces; detail everywhere looks CG [22][33].
- **Wear follows use and exposure:** walked centres worn, edges less; dirt and damage varied per instance [33].
- **Scale reference in the scene from day one** [33]. (We already put a 1.8 m figure on every kit sheet.)
- **Hide tiling** with macro variation (a large-scale noise multiplied in at 2-3 scales), distance-based UV scaling,
  and UE's TextureVariation / texture bombing [29][SECONDARY].
- **Right reference:** walls differ by region; pick references from the right place and period [21].

### 8.3 What this means for us
- **Masonry (walls, steps, footings, kerbs): modelled stones stay the method** (it gave our best scores), with three
  corrections from this study: a real crown (value range), dark deep joints with packing stones, and the laying pattern
  taken from the reference (ranzumi vs nunozumi, stone aspect).
- **Natural rock: build a small owned "rock parts" set** (5-10 jointed-and-rounded granite blocks, 3-4 cleft/multi-lobed
  hero rocks, a scatter set of 10-20 chips and cobbles of the same rock), then assemble boulders, banks and the pine
  rock from them. This is the GoT / Valley of the Ancient model at our scale.
- **Materials: unique form from geometry + one tiling granite detail + vertex-colour masks** for moss/dirt/wet/lichen,
  height-blended. Our shared library already has the granite and moss parts; the height-blend and a lichen layer are
  missing (the pines notes flag the lichen overlay as not in the kit master).

---

## 9. What makes CG stone look fake (the checklist a judge will hit)

| # | Failure | Why it reads fake | Measurable check |
|---|---|---|---|
| S1 | **Uniform pillow radius** | Every stone has the same shoulder and crown, like upholstery | CV of arris radius and crown height across stones ≥ 0.3; crown/width ratio in the reference's range |
| S2 | **Flat crowns / low value range** | No lit top, no shaded shoulder; reads as a printed texture | Luma p25-p75 and p5-p95 within ±0.05 of the reference crop (1.2) |
| S3 | **Bright, flat or pebbled joints** | Real joints are shadowed voids with packing stones | Dark fraction (luma < 0.2) within ±30 % of the reference; joint core albedo ≤ 0.5 × stone |
| S4 | **Wrong laying pattern** (kikkō polygons where the ref is ranzumi, or level courses where it is random) | Style mismatch a judge sees at once | Stone aspect histogram (h/w), share of upright stones, count of straight bed joints longer than 3 stones |
| S5 | **Stones too uniform in size** | Nature grades sizes | Stone area CV; big-at-bottom check (mean area per third of height) |
| S6 | **Thin tiles, no depth** | Face stones must be deep blocks | Every face stone's depth ≥ 0.8 × face width (hidden but affects edge silhouettes and ends) |
| S7 | **Faceted / chipped hulls for natural rock** | Reads low-poly | No dihedral crease sharper than ~150 deg except on fresh-break surfaces; arris radius ≥ 10 % of block size |
| S8 | **Blob / potato rocks** | Sphere + noise has no joint planes | ≥ 60 % of the surface area within 15 deg of 3-6 dominant face planes; 1-3 straight cracks |
| S9 | **Repeating noise / tiling** | Same speckle or pit pattern everywhere | Autocorrelation peak of the albedo at the tile period < a threshold; ≥ 2 macro scales |
| S10 | **Speckle too big or contrasty ("terrazzo")** | Real granite grain is 1-5 mm, dark mica ~4 % | Dark speckle area ≤ ~5 %; speckle size at 1-5 mm in world scale |
| S11 | **Moss as a tint** | Moss is 3D and lives in joints/tops | Moss mask vs up-normal and cavity correlation > 0; no moss on overhangs |
| S12 | **Floating or clean-cut contact** | Stones must be buried and banked | Rock burial ≥ 1/3; no visible intersection line; debris of the same rock at the foot |
| S13 | **Wrong scale** | Pebble-size detail on a boulder, or boulder-size stones in a garden wall | Stone sizes from the reference's own scale (Section 10) |
| S14 | **Mirrored / stretched UVs** | Stone grain has no mirror symmetry | Box/triplanar or per-face UVs; texel density within ±20 % across a piece (our kit: 5.08-5.37 px/cm) |
| S15 | **Everything clean and new** | No age: no chips, stains, streaks, lichen | Chips on ≥ 30 % of exposed arrises; streaks below ledges |
| S16 | **Colour off under the scene light** | "Chocolate" (r0) or pale beige (f1) | Rendered R/B and median luma vs the reference crop under the same sun |

---

## 10. Matching a reference sheet (the procedure)

1. **Set the scale** from something known in the same image (a 0.16-0.17 m riser, a 1.8 m figure, a door). Record px/m
   per region: the landscape reference needs two scales (47-50 px/m at the gate steps, 17-25 px/m at the terrace)
   [LOCAL, wall BUILD_NOTES].
2. **Classify each stone surface** with Sections 2-7: processing grade, laying pattern, joint type, natural rock kind.
   Write it into the spec. One wall piece = one class.
3. **Trace the stone outlines** on the clearest crop (our proven "tracing is the 2D outline authority" rule, CLAUDE.md).
   From the tracing measure: stone widths and heights (median, p10, p90), aspect h/w, upright share, bed-joint
   straightness, joint width, stones per m².
4. **Measure the value field** (1.2 table): luma percentiles, dark fraction, local contrast, R/B, moss hue share. Do it on
   the reference and on our render of the same view with the same crop.
5. **Build to the numbers,** render the same view, compare side by side, then run the blind judge.
6. **When the judge disagrees with the measurement, the measurement wins** unless the judge points at something
   unmeasured. Then add a measurement for it.
7. **Stop early** when a round fails decisively and show the user (CLAUDE.md).

---

## 11. Where this lands for the stone kit and the rocks (input to the plan, not a plan)

- **Terrace ishigaki (river terrace):** nozura / uchikomi-hagi in **ranzumi**: rounded, lens and egg stones, many upright,
  sizes 0.28-0.55 x 0.28-0.47 m (already measured), a real crown with the reference's value range (S2), dark 2-4 cm
  joints with packing stones and moss/grass tufts in them, big root stones at the foot, sangi-zumi corners at 2-3 : 1.
  Restore the r0/r3 shapes and fix r0's material, joints and pillow uniformity; do not keep f1's polygons.
- **Upper terrace and footings:** uchikomi-hagi **nunozumi**: squarer blocks with soft arrises in near-level courses;
  kit 1's r3 footing is the anchor.
- **Steps:** solid block steps (1 long block per step on the lower flight per the reference, 2-3 elsewhere), lighter
  worn treads, darker risers, a rounded worn nosing with no overhang unless the reference shows one, a centre hollow a
  few mm deep, moss at tread ends and backs. Flat flag landings with moss/soil joints.
- **Boulders, river banks, cliff:** a rock-parts set built as **jointed blocks → rounded arrises → cracks → grain**
  (Section 7), assembled into formations; river stones as phase-I/II rounded blocks; burial and same-rock debris.
  The user sources scenery rocks per the standing rule; this method is for our own hero rocks (pine rock, set pieces)
  and for anything sold on Fab.
- **The D-pine rock:** 3-4 fused rounded blocks with deep clefts, roots through the clefts, lichen patches, moss
  cushions in clefts and on top, a soil/moss base mound.
- **Lanterns and carved stone:** thicker kasa, per-part non-mirrored UVs, weathering on tops and ledges.
- **Gates to add to the build specs:** S1-S16 measured checks, the 1.2 value table against the reference crop, the
  traced stone-size statistics, plus the usual qa_check, UCX and fresh-process Unreal verify.

---

## 12. Uncertain / to verify

- Kumamoto "about 45 deg for the lower two thirds" and Marugame's "curve from half height, 22 m" come from search
  summaries of Japanese pages, not a survey drawing [7][10] [SECONDARY]. No measured sori curve equation was found.
- No primary source gave ishigaki joint widths, face-stone depth ratios or backfill thickness in numbers. The 2-4 cm
  joints are measured on our references, not on real walls.
- Stair-wear depths (up to 75 mm; 0.8-1.2 mm centre vs 0.2-0.5 mm edge in a model study) are secondary [20].
- The granite albedo 0.35-0.40 figure is from a secondary chart [34]; match the reference instead.
- Burial "one third to two thirds" and stepping-stone spacing/height are from garden-craft blogs [18][19][SECONDARY].
- Game-studio methods for Ghost of Tsushima rocks, Naughty Dog's blend shader and Sekiro's stone are known from
  portfolio captions, search summaries and talk abstracts, not the full talks (paywalled or 403) [26][27][35].
- **[UNCERTAIN 5.8]** Nanite Tessellation/displacement for stone walls (introduced 5.3-5.4 as experimental; a 5.8
  regression was reported for landscape displacement, see the tree study) [31]. UE's HeightLerp and
  TextureVariation material functions exist in 5.x; not checked in 5.8's function library.
- **[UNCERTAIN 5.8]** Megascans / Fab licence terms for including scanned rocks in a Fab product: assume NOT allowed in
  our Fab packs; game use only, and only with the user's approval.
- **[UNCERTAIN 5.2]** Nothing here depends on a Blender feature; the geometry methods (Section 7, 8.3) belong in study C.

---

## Sources

1. Japan Tourism Agency multilingual DB (MLIT), *Castle Craftsmanship: Stone Walls* (Himeji) — https://www.mlit.go.jp/tagengo-db/common/001561168.pdf ; *Stone Walls at Himeji Castle* — https://www.mlit.go.jp/tagengo-db/en/R2-00194.html
2. Roots of Japan, *You and I are Stone Wall Enthusiasts: A More Detailed Explanation* — https://note.com/rootsofjapan/n/n1137c867873d?hl=en
3. JCastle, *Stone walls* — https://jcastle.info/view/Stone_walls
4. Kanazawa Castle Park, *Museum of stone walls* — https://shiro-niwa.pref.ishikawa.lg.jp/kanazawa-castle/en/explore/museum.php
5. Wikipedia (ja), *石垣の積み方* — https://ja.wikipedia.org/wiki/%E7%9F%B3%E5%9E%A3%E3%81%AE%E7%A9%8D%E3%81%BF%E6%96%B9 ; Kojodan, *石垣の種類* — https://blog.kojodan.jp/entry/2019/03/02/113353 [SECONDARY]
6. Shirobito, *石垣を崩れにくくするための積み方* (sangi-zumi 2-3 x, kadowaki-ishi) — https://shirobito.jp/article/1130 ; Kojodan, *算木積* — https://blog.kojodan.jp/entry/2020/10/14/180000
7. Kojodan, *石垣の反りと勾配* — https://blog.kojodan.jp/entry/2020/10/19/180000 ; Shirobito, *勾配と反り* — https://shirobito.jp/article/1213 ; Takamaru office, *石垣の反りと勾配* — https://www.takamaruoffice.com/shiro-shiro/warp-slope-stonewall/ [SECONDARY for the Kumamoto figure]
8. Isan no Sekai, *伝統技術にもとづいた城郭石垣の整備* — https://www.isan-no-sekai.jp/feature/32_souron02
9. Seattle Japanese Garden, *Japan's Stone Wall Culture* — https://www.seattlejapanesegarden.org/blog/2025/6/20/japans-stonewall-culture ; *Ishigaki Wall and Accessible Pathway Project* — https://www.seattlejapanesegarden.org/blog/2026/4/24/ishigaki-wall-project
10. Roots of Japan, *The Tallest Stone Walls ... Marugame* — https://note.com/rootsofjapan/n/n9bdb288354f1?hl=en [SECONDARY]; Muza-chan, *Hikone Castle sloping wall* — https://muza-chan.net/japan/index.php/blog/hikone-castle-sloping-wall
11. The Stone Trust, *Dry stone walling: 5 basic rules* — https://thestonetrust.org/wp-content/uploads/2018/02/Dry-stone-walling-guide-5-basic-rules-1.pdf ; DSWAA, *Building dry stone walls: a guide for beginners* — https://dswaa.org.au/wp-content/uploads/2021/05/Manual_June_2020_RetWall_vlr.pdf ; Peak District NP, *Guidelines for drystone walling* — https://www.peakdistrict.gov.uk/__data/assets/pdf_file/0022/64642/drystonewalling.pdf (403; search summary) ; Field Mag, *The Art of Dry Stone Walling* — https://www.fieldmag.com/articles/dry-stone-wall-how-to-guide [SECONDARY for batter ratios]
12. Wikipedia, *Spheroidal weathering* — https://en.wikipedia.org/wiki/Spheroidal_weathering
13. Domokos, Jerolmack, Sipos, Török, *How River Rocks Round: Resolving the Shape-Size Paradox* (PLoS ONE 2014) — https://pmc.ncbi.nlm.nih.gov/articles/PMC3922984/
14. *The Shape of Fluvial Gravels: Insights from Fiji's Sabeto River* (Geosciences 2021) — https://www.mdpi.com/2076-3263/11/4/161 [SECONDARY, search summary]
15. Wikipedia, *Lecanora polytropa* — https://en.wikipedia.org/wiki/Lecanora_polytropa ; *The Role of Lichens, Mosses, and Vascular Plants in the Biodeterioration of Historic Buildings* — https://pmc.ncbi.nlm.nih.gov/articles/PMC9781475/ ; InspectApedia, *Lichens, algae, moss on stone* — https://inspectapedia.com/exterior/Lichens_on_Stone.php [SECONDARY]
16. Litos Online, *The Inada Granite* — https://www.litosonline.com/en/article/inada-granite-japanese-traditional-light-grey-ornamental-rock ; MLIT, *Aji Stone* — https://www.mlit.go.jp/tagengo-db/en/R3-00412.html [SECONDARY]
17. Wikipedia, *Stone lantern* — https://en.wikipedia.org/wiki/Stone_lantern
18. NAJGA, *The Garden Path* — https://najga.org/the-garden-path/ ; *Japanese Garden Paths* — https://najga.org/japanese-garden-paths/ [SECONDARY for spacing/heights]
19. NAJGA, *Chapter 20: Garden Rocks* — https://najga.org/japanese-garden-garden-rocks/ ; Robert Ketchell, *Notes on Ishigumi* — http://robertketchell.blogspot.com/2013/05/notes-on-ishigumi-or-art-of-arranging.html [SECONDARY, burial figures]
20. Dimensions.com, *Stair Tread & Riser Sizes* — https://www.dimensions.com/element/stair-tread-riser-sizes ; Chippy Tools, *Japanese Stair Rules* — https://www.chippy.tools/building-codes/jp/stairs/stair-and-guard-requirements/ ; Petros Stone, *Stone Staircase Treads* — https://petrosstone.com/stone-steps-treads/ ; London Stone Step, *Garden step dimensions* — https://londonstonestep.co.uk/guides/garden-step-dimensions-rise-and-going/ ; Trebles Going, *Worn Tower Steps* — https://www.treblesgoing.org.uk/wornsteps.html ; stair-wear model — https://hsetdata.org/index.php/ojs/article/download/11/7/7 [SECONDARY]
21. 80.lv, *Japanese Stone Wall Production in ZBrush & SD* (Sharlene Lin) — https://80.lv/articles/001agt-japanese-stone-wall-production-in-zbrush-sd
22. 80.lv, *Creating a Stone Wall Material in ZBrush, Substance 3D Designer & Marmoset Toolbag* (Sergii Zlobin) — https://80.lv/articles/creating-a-stone-wall-material-in-zbrush-substance-3d-designer-marmoset-toolbag
23. 80.lv, *Breakdown: Procedural Rock Generation in Houdini* — https://80.lv/articles/006sdf-breakdown-procedural-rock-generation-in-houdini ; rock sculpting brush lists — https://vkgamedev.com/blog/top-rock-stone-sculpting-brushes-blender [SECONDARY]
24. Epic, *Valley of the Ancient Sample Game* — https://dev.epicgames.com/documentation/en-us/unreal-engine/valley-of-the-ancient-sample-game-for-unreal-engine
25. Epic, *Electric Dreams Environment* — https://dev.epicgames.com/documentation/en-us/unreal-engine/electric-dreams-environment-in-unreal-engine
26. Tyler Smith, *Ghost of Tsushima: Rock Sculpting* — https://www.artstation.com/artwork/yk42A3 (403; search summary) ; ArtStation Magazine, *Ghost of Tsushima Art Blast* — https://magazine.artstation.com/2020/08/sucker-punch-productions-ghost-of-tsushima-art-blast/ ; GDC, *Samurai Landscapes* — https://gdcvault.com/play/1027352/Samurai-Landscapes-Building-and-Rendering [SECONDARY]
27. Maximov, *Technical Art Techniques of Naughty Dog* (GDC 2017) — https://gdcvault.com/play/1024103/Technical-Art-Techniques-of-Naughty ; Naughty Dog tech art slides — https://www.advances.realtimerendering.com/other/2016/naughty_dog/NaughtyDog_TechArt_Final.pdf (too large to fetch) ; Polycount, *Creating Uncharted 4's Libertalia* — https://polycount.com/discussion/194424/creating-uncharted-4s-libertalia-unity [SECONDARY]
28. 80.lv, *Real-Time Procedural Placement in Horizon Zero Dawn* — https://80.lv/articles/real-time-procedural-placement-in-horizon-zero-dawn ; Guerrilla, *GPU-Based Procedural Placement* — https://www.guerrilla-games.com/read/gpu-based-procedural-placement-in-horizon-zero-dawn [SECONDARY]
29. Jan Arenz, *About Texture Repetition & Texture Variation (UE4/5)* — https://janarenz.artstation.com/blog/L6Qq/about-texture-repetition-texture-variation-unreal-engine-4-5 (403; search summary) ; World of Level Design, *Macro/micro variation* — https://www.worldofleveldesign.com/categories/ue4/landscape-macro-tiling-variation.php [SECONDARY]
30. Epic, *Setting up a texture-blended material for vertex weights painting* — https://dev.epicgames.com/documentation/unreal-engine/setting-up-a-texture-blended-material-for-vertex-weights-painting-in-unreal-engine?lang=en-US
31. Epic, *Nanite Virtualized Geometry* — https://dev.epicgames.com/documentation/unreal-engine/nanite-virtualized-geometry-in-unreal-engine ; UE forum, *Displacement and Nanite Tessellation* — https://forums.unrealengine.com/t/community-tutorial-displacement-and-nanite-tessellation-in-unreal-engine-5/1800313 [SECONDARY]
32. CG Channel, *Quixel launches Megascans 2018* (hero + scatter, 8K) — https://www.cgchannel.com/2017/11/quixel-launches-megascans-2018/ ; Althera Games, *Nanite guide* (Megascans kitbash texel mismatch) — https://altheragames.com/en/blog/ue5-nanite-guide [SECONDARY] ; Quixel Japanese stone assets (Japanese Stone Wall, Japanese Mossy Stone Wall, Modular Japanese Stairs Kit, Japanese Stone Lantern) — https://quixel.com/megascans/home?category=3D+asset&category=historical&search=japan&assetId=ufokciifa [SECONDARY]
33. Outpost VFX, *22 Pro Tips and Tricks for Environment Artists* — https://www.outpost-vfx.com/fr/news/22-pro-tips-and-tricks-for-environment-artists
34. Ron Haimov, *PBR Albedo guide for Lighting Artists* — https://www.linkedin.com/pulse/pbr-albedo-values-guide-lighting-artists-only-ron-haimov [SECONDARY]
35. Siliconera, *Sekiro Environments Were Designed to Reflect Culture* (CEDEC+KYUSHU 2021) — https://www.siliconera.com/sekiro-environments-were-designed-to-reflect-culture/ [SECONDARY]
36. Wikipedia, *Sakuteiki* — https://en.wikipedia.org/wiki/Sakuteiki

**Local (read-only) evidence:** `WorkFiles/dojo/DOJO_QUEUE.md`; `WorkFiles/dojo/build/stonekit/BUILD_NOTES.md`,
`wall/BUILD_NOTES.md`, `renders/{wall,f1}/` (sbs pairs, close-ups, ref crops); `Scripts/dojo/kit1_geo.py`
(`pillow_face`, `rubble_pillow`, `hewn_stone`, `rough_block`); `Scripts/dojo/materials/README.md`;
`WorkFiles/dojo/build/pines/BUILD_NOTES.md` + `renders/f1/sbs_PineD1_front.png`; references
`References/Dojo/dojo_landscape_ref.png`, `dojo_wall_ref.png`, `dojo_courtyard_stone_ref.png` (value statistics in
1.2 measured with PIL on this PC). Owned rock content, names and sizes only:
`Documents/Unreal Projects/Scenery_Tutorial/Content/Megascans/3D_Assets/Nordic_Beach_Rocks_vckqccbga_3d/` (1K albedo
and normal, one LOD0 mesh ~1.9 MB), `.../Surfaces/{BeachCliff, MossyCreekStones, MossyRockyGround,
Mossy_Rocky_Ground_vcrkeax}` (4K D/N/displacement), `DemoGame_1/Content/Fishermans_Cabin/Meshes/{Rocks,Small_Rocks}`
(SM_Rocks_01-04, SM_Small_Rocks_01-05, per-rock `_N` + `_Mask`, tiling `Tiling_Textures/Rock`), and the same pack in
`C:/ProgramData/Epic/EpicGamesLauncher/VaultCache/NordicFi1d739256ce1cV1/`.
