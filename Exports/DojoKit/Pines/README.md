# DojoKit Pines (SM_DKN_*)

Four niwaki Japanese black pines (Pinus thunbergii), two structural variants each, for the sunset mountain dojo.
Built headless in Blender 5.2 by `Scripts/dojo/pines/` on the reusable generator in `Scripts/vegetation/`, following
`TREE_BUILDING_STUDY.md`. Exported only through `Scripts/pipeline/export_fbx.py` (kind static, metres, -Y forward,
Z up, triangulated). **Not yet imported into Unreal** (no Unreal step in this build).

**Fix round v2f (2026-09-30, current).** Judge deltas checked against the sheet before acting (BUILD_NOTES):
rosettes are 6 units (4 round stars for the pad tops, 2 upright brushes for some rim sites; no needle hangs below
its twig), grouped in twig-end clumps with a fill, sampled toward the dome top; yellow sheath flecks and yellow-tipped
needles; needle colour re-measured against the sheet (~12 % brighter, not bluer); limbs zig-zag in the view plane
and are pushed apart where they touched; knobs on the A/B/D trunks; new plated bark (`T_DKN_Bark_*` v4: vertical plate
columns + terraced flaky layers, brighter, orange under-bark); mounds A-C rebuilt as a lumpy moss bed (vertex colour R =
moss cushion, gaps dark) with rocks and fern sprays; pine D's rock is ONE fused broad boulder (width / height 1.24 /
1.28 above grade) with the trunk slimmed to ~1/5 of the rock's width (0.26 / 0.30 m at the rock), 13 thinner roots +
forks draping its left flank and a fern / shrub skirt on `SM_DKN_BaseMound_D`. Heights unchanged except D (3.08 /
3.21 m). Foliage over the 150k soft cap on B1, B2, C1 (239k), C2; trunk over 80k on C1 (102k): measure in Unreal first.

**Round v2 (2026-09-30, owner-approved new method).** Pads are domes of separate needle ROSETTES (5 hand-shaped
units, 108-160 needles each, 7-11 cm needles, pale bud and sheaths) on a knuckled spanning-tree twig lattice; limbs end
inside their pads; trunk girth from the sheet per panel; heights from the sheet's 1.8 m figure (A ~2.2-2.5 m, B ~3.4-3.6
m, C ~4.3-4.5 m, D ~3.6-3.9 m; instance scale up to ~1.3x in Unreal, C up to ~1.05x); plated bark (T_DKN_Bark_* v3);
needle colour from the sheet's measured pixels; and an optional mossy base mound per family,
`SM_DKN_BaseMound_<A-D>.fbx` (one UCX hull, same origin as the trees; A/B/C mounds follow the sheet's mound, D's is a
low apron round the rock's foot).

**Rock stage (2026-09-30, D only).** Pine D's boulder was rebuilt with `STONE_BUILDING_STUDY.md` 4.9 / 8.3: 2-3 fused,
rounded-but-fractured granite corestone lobes (ellipsoids cut by joint-family planes, a per-lobe SDF opening, fresh
fracture chips, 2 cracks, meso noise and 13 cm flake facets), at 0.65 x the v2 rock's size relative to the tree (owner):
D1 1.28 x 0.79 x 1.11 m, D2 1.48 x 0.85 x 1.21 m above grade (12 cm buried). A unique UV0 (58-80 charts, 5.4 px/cm at
2K) carries baked `T_DKN_<V>_Rock_N` (DirectX), `_ORM` and `_M` (R moss, G lichen, B dirt) over the shared library
granite; moss only in the crevices and on top (moss-cushion shell on the top). The trees were set lower onto the new
rock (D1 3.15 m, D2 3.18 m tall; ~1.15-1.2x instance scale restores the sheet's 3.6-3.9 m); D1 now leans left over
the rock with a heavier lower S-bend; 10 roots per tree hug the rock and run into its clefts and cracks to the ground.

**Fix round f1 (2026-09-30).** Trunks thinned (girth set by a trunk/crown-width target); pads rebuilt as an open
lattice of angular forked twigs carrying separate radial needle bursts (no solid pad cores); zig-zag limbs with
knuckles; new plated bark (vertical plate columns, rust edges); pine D's boulder rebuilt as fused faceted masses
with a mossy crown, darker lichened granite and roots walked over the rock surface; grass tufts at every base.

| Pine | Variants | Height | Meshes |
|---|---|---|---|
| A: small S-curve garden pine, cloud pads | PineA1, PineA2 | 2.24 / 2.48 m | _Trunk, _Foliage (+ BaseMound_A) |
| B: tall layered pine | PineB1, PineB2 | 3.58 / 3.40 m | _Trunk, _Foliage (+ BaseMound_B) |
| C: big leaning pine, long reaching limb, broken stub | PineC1, PineC2 | 4.53 / 4.32 m | _Trunk, _Foliage (+ BaseMound_C) |
| D: cliff pine on a boulder | PineD1, PineD2 | 3.08 / 3.21 m incl. the rock (v2f) | _Trunk, _Foliage, _Rock (+ BaseMound_D) |

Variant 1 of each pine is traced from the sheet's front panel (depth from its side panel); variant 2 is traced from
the sheet's 3/4 panel as its own design (the AI sheet's views of one tree disagree with each other).

**Origin.** The trunk base on the ground at (0, 0, 0) for A-C (trunk and nebari continue 0.2 m below grade); for D the
rock's ground-contact centre (rock sunk 0.12 m). All meshes of one tree share the origin: place them with one transform.

**Per tree:** `SM_DKN_<V>_Trunk.fbx` (UCX hulls on 2-4 trunk runs), `SM_DKN_<V>_Foliage.fbx` (no collision by
design; needles only in v2: the ground cover moved to the optional mound), `SM_DKN_<V>_Rock.fbx` (D only, one UCX hull per
lobe: D1 3, D2 2; no traversal marker, the top is the tree's root plate), `Textures/T_DKN_<V>_Rock_N/_ORM/_M.png`
(D only, 2K unique maps), `SM_DKN_<V>.wind.json`, `Textures/T_DKN_<V>_Trunk_ORM.png`
(unique AO bake, UV2), `Textures/T_DKN_<V>_PivotPos.exr` + `_XVector.png` (Pivot Painter 2, UV2 of the foliage).
**Shared:** `T_DKN_Bark_*` (1 m tile, 10.24 px/cm), `T_DKN_Needle_*` (incl. linear `_SSS`), `T_DKN_Moss_*`, `T_DKN_Soil_*`,
`T_DKN_RockOverlay_M` (linear: R lichen, G stain, B grit; 1 m tile; now used by the D mound's small stones only).
The D rock's slot 0 is `MI_DKN_<V>_Rock`: the dojo library's `M_DJ_Granite` (`Exports/DojoKit/Materials/Textures/
T_DJ_Granite_*`, Tint (0.68, 0.67, 0.665) in v2f, tiled on UV0 x S/4, S = 3.79 m per UV0 unit) under the unique N / ORM / M
maps; slot 1 `MI_DKN_<V>_RockMoss` (the moss set on the cushions). Recipe in the catalog.

**Channels.** Trunk: UV0 tiling bark (whole-tile packed, no overlap), UV1 lightmap, UV2 unique bake; colour R junction,
G moss, B branch AO. Foliage: UV0 needle cells, UV1 lightmap, UV2 PP2 index, UV3.U canopy AO; colour R hierarchy
weight, G pad phase, B tuft phase, A unused. **Import vertex colours with Replace** (the static default Ignore drops
them). Foliage: Nanite Voxelize with Lerp UVs OFF; trunk and rock: Nanite, Shape Preservation None.

The full import, material and wind recipe is in `WorkFiles/dojo/build/pines/pines_catalog.json`; build notes,
deviations and measured numbers in `WorkFiles/dojo/build/pines/BUILD_NOTES.md`.

**Provenance.** Our own procedural work. The reference sheet is AI-generated (ChatGPT); it was only measured and
traced, no pixel of it is in any texture (disclose AI-reference use for Fab, ASSET_GUIDELINES 11).
Collision/LOD statement: Nanite, no hand LODs; UCX collision on trunks and the rock only.
