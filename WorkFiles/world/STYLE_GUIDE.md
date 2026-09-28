# World Style Guide (DemoGame_1)

**Date:** 2026-09-27. **Status:** planning only; nothing built. **Covers:** every environment piece for the 1v1 dojo arena and,
later, the battle-royale (BR) map (about 32 km², 5.7 km square). **Companions:** `DOJO_ARENA_SPEC.md`,
`DOJO_ARENA_TOPDOWN.svg/.png`. House rules for making any asset stay in `ASSET_GUIDELINES.md`; this file adds the
world-specific ones.

## 1. The look in one paragraph

A lived-in ninja world: traditional Japanese timber, plaster, stone and tile, with modern infrastructure that has
been added on top over the years (power lines, electric lamps, vending machines, air-conditioning units, concrete,
corrugated steel). It must feel like the user's own place. Nothing may be recognisable from Naruto or any other
franchise (section 8).

## 2. Realism level: match the finished assets

The finished items (shuriken pack, kunai, paper bomb, smoke bomb, black hat, fan, Snow Flower) set the bar:
- **Grounded realism, PBR, real-world scale.** The line sheets list real millimetres and grams. No outlines, no
  cartoon proportions, no painted-on lighting.
- **Honest wear, not ruin.** Fine scratches on steel, frayed thread on cloth, soft paper creases. For the world that
  means rain streaks under eaves, moss at wall bases, worn stair edges, sun-faded paint. Buildings are maintained,
  not derelict (the BR can have a few damaged places as a deliberate exception).
- **Dark, desaturated materials.** The item line is near-black (cloth `#373532`-`#3F3C3B`, smoke bomb `#3F3A37`), worn
  grey steel, dark slate fan, black-and-silver sword. Colour comes from a few accents: parchment `#F3E3C3`, ink black
  `#0F0F0E`, vermilion ink `#D5180B`.
- **Readability rule (borrowed from the armory's "dark room, bright cases"):** the players wear black, and the
  default time is night. So the surfaces a player is seen against in play (fight floors, lower walls, streets) are
  mid-to-pale (sand, plaster, pale stone). Dark timber and tile go above head height and on roofs.

## 3. Palette (starting values; tune in the grey-box and first lighting pass)

| Group | Colour (sRGB, estimate) | Used for |
|---|---|---|
| Weathered dark timber | `#3A2E26` | Posts, beams, fascias, fences (lighter than the armory's indoor `#221A15`) |
| Worn pale timber | `#9C8466` | Veranda boards, steps, hand-worn edges |
| Cream plaster | `#D9CFBD` (albedo capped at 0.80, as in the armory) | Hall and storehouse walls |
| Earthen wall | `#A88D6A` | Perimeter wall body |
| Roof tile grey | `#55585C` | Kawara tile, wall caps |
| Granite | `#8A8680` | Lanterns, step stones, foundations |
| Fight-floor sand | `#B3A791` | Raked courtyard (the pale backdrop for black-clad players) |
| Moss / foliage | `#4F5A35` | Moss, grass tint at night |
| Red accent (sparingly) | `#8E1F1F` cloth, `#D5180B` ink | Banners, curtain trims, painted signs. Never whole buildings |
| Modern neutrals | concrete `#9A9892`, galvanised `#A7AAAD` | Poles, pipes, AC units, lean-to roofs |
| Modern accents | faded teal `#4E7C7A`, rust `#7A4A2E` | Vending machines, painted steel, old signs |

Light colour carries the old/new mix at night: **traditional light is warm flame (1900-2200 K)** from lanterns;
**modern light is cool white (about 4000 K) or orange sodium** from electric lamps. No pure black albedo (floor about
sRGB 30) and no pure white (ceiling about sRGB 240).

## 4. Mixing traditional and modern

| Place type | Traditional : modern (by eye, share of visible props and surfaces) |
|---|---|
| Dojo, shrines of your own design, old quarters | 85 : 15 |
| Towns and villages | 60 : 40 |
| Docks, workshops, industry | 40 : 60 |

- **Where modern appears:** added-on services. Overhead wires and poles, electric lamps on brackets, pipes and
  gutters, AC units, water tanks, vending machines, corrugated-steel lean-tos, concrete kerbs and footings, steel
  doors on storehouses, aluminium window frames in towns.
- **Where it does not:** the structure and silhouette of traditional buildings (roof shape, timber frame, plaster
  panels stay traditional); weapons; anything the player holds.
- **Era cue (to confirm, see open questions):** mid-to-late 20th-century infrastructure: analogue, bulbs, cables on
  poles, no screens or cars by default. All signage is original script or blank, never a real brand.
- **Game use:** modern pieces are often the climb props (a vending machine or an AC unit is a step up to a wall or
  roof). That makes them purposeful, not just decoration.

## 5. Materials

**Reuse the three shared masters** (`M_Steel_Master`, `M_Fabric_Master`, `M_PaperInk_Master`, built by
`Scripts/unreal/materials`) as instances for: iron fittings, nails, bells and hinges (Steel, tinted; check that the
tint range reaches bronze and brass, the same open check as the armory's `MI_AK_Brass`); banners, door curtains,
rope and cushions (Fabric); shoji paper, paper lanterns, signs and posters (PaperInk). The masters are frozen:
never edit them for the world. Any change goes through the PackMaterials lock and `run_build.sh` (see the shared
materials guard). Pieces that may be sold on Fab must not reference `/Game/NinjaPack/`: their instances live in a
game-only folder, or the kit gets its own copy built from the same spec.

**New masters the world needs.** One environment family, shared with the armory so the two never drift (the
armory's planned `M_AK_Wood/Plaster/Glass/Emissive/Decal` become this family). All built from code and added to
`material_spec.json` under `environment`, as the armory plan already proposes.

| Master | Covers |
|---|---|
| `M_Env_Wood` | Timber trim sheet, planks, lacquer, pale boards; weathering by vertex colour |
| `M_Env_Plaster` | Plaster, earthen walls; rain streaks and dirt by vertex colour; albedo cap 0.80 |
| `M_Env_Stone` | Granite, cobbles, foundations; optional world-aligned mode for big surfaces |
| `M_Env_RoofTile` | Kawara tile fields, ridges, caps; moss and lichen masks |
| `M_Env_Concrete` | Concrete, blocks, render, kerbs |
| `M_Env_PaintedMetal` | Corrugated steel, vending machines, poles, AC units; paint wear and rust masks |
| `M_Env_Ground` | Landscape and floor blends: sand, gravel, dirt, moss (runtime virtual texture for blending) |
| `M_Env_Glass`, `M_Env_Emissive`, `M_Env_Decal` | Windows, lamps and lantern paper, grime and leak decals |

## 6. Grid, scale and texel density

- **Grid (same as the armory):** 100 cm primary, 25 cm sub-grid, heights on 25 cm (stair risers 15 cm), interior
  walls 30 cm. Build real-world scale, metres in Blender, pivots on the inner face at the base, on the grid.
- **Movement numbers are part of the grid.** Steps 25 cm, walk-on ledges at least 100 cm deep, required climbs at
  most 200 cm, walkable roofs 25 degrees. `DOJO_ARENA_SPEC.md` section 3 shows where these come from.
- **Texel density:** hero and near pieces 5.12 px/cm (the third-person rule in `ASSET_GUIDELINES.md` and the
  armory's architecture value); mid pieces 5.12 on tiling materials and trims; background 2.56; terrain 2.56 near
  with detail textures. Prefer tiling materials and trim sheets over unique textures: they cost the same memory
  however many buildings use them.

## 7. Performance rules for a battle royale

- **Nanite on every opaque static piece** over about 2k triangles; pieces still ship LOD0-2 and UCX collision
  (Fab and the pipeline require them). Translucency only for glass.
- **World Partition with HLODs.** Each building is assembled once (a Packed Level Actor or Level Instance) so it
  gets a merged HLOD. Rough distances to test: kit pieces as instances out to about 300 m, merged HLOD beyond, a
  simple proxy beyond about 1 km.
- **Cull small things:** props at 80-150 m, grass and pebbles at 40-60 m; wind (world position offset) off beyond
  about 50 m.
- **Lights:** at most a handful of shadow-casting lights per location; lanterns beyond about 30 m become emissive
  only.
- **Collision:** simple hulls only, never complex-as-simple; roofs get one flat collision plane per slope; grass and
  canopies have none.
- **Network:** buildings and props are not replicated. Only doors and loot containers are, and they sleep when
  idle.
- **Heavy trees are rationed.** The Megaplants hinoki and ginkgo are tens of millions of Nanite triangles each and
  need an Experimental plugin (`Scenery_Options.md`). A few per landmark, never forests; forests use lighter trees.
- **Budget check per location:** measured in the grey-box and again after art, on the RTX 4070 SUPER, against the
  duel target (60 fps at 1080p with two players and effects, roadmap M4) and, for the BR, a target set when the BR
  starts.

## 8. Tiers: how much care each piece gets

| Tier | What | Process |
|---|---|---|
| **Hero** | Identity pieces seen up close: the dojo gatehouse and hall front, the drum, stone lanterns, the location emblem | The full reference-matching process the items used: an approved reference board, side-by-side composites against it, a blind review, every pipeline gate, an Unreal check. Unique detail where it shows |
| **Mid** | The modular kit: walls, roofs, verandas, doors, fences, most props | Built from trim sheets and tiling masters against the style board; one review round; `qa_check` and the pipeline gates; Nanite or LODs |
| **Background** | Distant buildings, skyline, out-of-bounds dressing | Assembled from mid-tier pieces or simple shells; silhouette check only; HLOD first |

## 9. Buy or build

- **Buy or reuse:** nature and sky. Terrain, grass, rocks, trees, fog, sky: the Nordic Fishing Hut pack (grass,
  rocks, firs, mountain, ground textures), the Megaplants hinoki and ginkgo, Ultra Dynamic Sky, NiagaraExamples fog
  cards. New downloads (Poly Haven CC0 textures, free Megaplants such as the Japanese cherry) only with the user's
  per-file OK. Check each Fab licence before a packaged build cooks it (roadmap section 8).
- **Build:** everything with identity. Architecture of named places, emblems, signage, loot containers, weapons,
  anything a player handles. Also the simple modern infrastructure (poles, pipes, vending machines, AC units): it is
  quick to make, and bought packs bring brand and style risk.
- **Never:** ripped game assets, "free" packs from piracy sites, CC-BY-SA or NC content in anything that ships.

## 10. IP rules

- **No Naruto marks:** no leaf, sand, mist, cloud or rock village symbols; no swirl emblems; no forehead
  protectors or plates with marks; no carved Hokage-style faces on cliffs; no "fire" kanji on hats or buildings as
  a village mark; no franchise names for places ("Konoha", "Hidden Leaf", ...).
- **The fan test** (`ASSET_GUIDELINES.md` section 11): if a fan would recognise it, it is out, however renamed.
- **No real crests** (kamon), no real brands on machines or signs, no copied artworks. Use one original emblem per
  faction or place, similarity-checked, as the armory plan proposes for its plinths.
- **No copies of real named buildings.** Real temples, castles and dojos are proportion and construction reference
  only. Religious symbols are left out unless designed originally and kept generic.
- **Text:** original script, invented words, or blank. The `qa_check` deny list applies to every name.
- **World art is original from day one.** The dev-only exceptions in roadmap D8 (anime audio, names) do not extend
  to environment art, which is far too costly to replace later.
