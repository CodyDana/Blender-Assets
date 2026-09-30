# Study C: building stone with Python in headless Blender 5.2 (and getting it into UE 5.8 through our pipeline)

**Written:** 2026-09-30, research phase only. Inputs were web sources, the repo files and read-only API probes in a
throwaway headless Blender 5.2 (factory startup, nothing saved). No project `.blend`, Unreal project or asset was
opened or changed. The probes are kept in `WorkFiles/studies/stone/c_probes/` with their JSON output.
**Companions:** `A_craft.md` (the craft: masonry types, ishigaki, rock geology, failure modes) and `B_unreal.md` (the
engine side), written by the sibling research tracks. This file is the **Blender and pipeline how-to**. It serves every
future stone build:
- dressed and rough masonry walls (ishigaki nozura-zumi, uchikomi-hagi, kirikomi-hagi; dry stone; rubble; ashlar);
- steps, paving, kerbs, footings;
- stone lanterns and carved stone;
- natural rocks and boulders: river boulders, cliff rocks, and rocks that trees grow from.

Tags:
- **[VERIFIED 5.2]**: probed in Blender 5.2.0 LTS on this PC today (numbers from `c_probes/*_out.json`).
- **[REPO]**: read in our code, notes or renders.
- **[WEB]**: from a cited source (section 15).
- **[UNCERTAIN]**: not tested here; section 14 lists them.

---

## 0. The short version

1. **Split stone into two families and use a different construction for each.**
   - **Dressed / laid stone** (wall faces, steps, paving, kerbs, lanterns): keep our analytic builders. That means a
     traced or packed 2D outline, then a ring-lofted pillow or rounded block with a real arris, crown and wear
     (`kit1_geo.pillow_face`, `rough_block`). These pieces worked: the footing is the judges' "closest piece to its
     sheet". The failures there were in the *layout*, *value* and *texture*, not in the stone body.
   - **Natural stone** (boulders, cliff rocks, rubble lumps, the tree rock): stop displacing blobs and stop shipping
     raw plane-chipped hulls. Use an **SDF pipeline**: multi-lobe plane-chipped convex hulls, then SDF union, then an
     SDF *opening* (erode r, dilate r) that rounds every arris by a chosen radius, then a few crack cuts, then meso
     noise. Mesh the result as the high poly, then decimate and bake to the low poly. Every step runs headless in
     Blender 5.2 Geometry Nodes or bmesh [VERIFIED 5.2] (section 7).
2. **Wall layout is the main lever.** Build the face as a 2D pattern first, in unrolled face coordinates, and
   measure it against the reference before any 3D. Then place each stone rigidly on the battered surface
   (`sk_shared.rigid_warp` already does this). Use one layout generator per masonry type (section 4). A layout
   passes when its measured statistics match the reference: stone size distribution, aspect ratios, course
   regularity, joint width, interlock and 4-way-joint count.
3. **Relief lives in exactly one place per scale.**
   - Silhouette and form (more than 2 cm): geometry.
   - Meso (2 mm to 2 cm): geometry on hero pieces, or a per-stone baked normal on unique-UV rocks.
   - Micro grain (under 2 mm): the tiling library texture at low normal strength.
   The r0 "sponge" and "chocolate" reads came from stacking the tiling granite's 3.5 / 9 cm facet relief on top of
   geometric relief [REPO].
4. **Value and hue come per stone and per region.** Measure them on the reference (section 11). Our f2 wall is
   pinker (stone hue 23 deg against 32 deg) and flatter (p90/p50 luminance 1.29 against 2.04) than the reference
   close crop. The stones need stronger crown shading, and each stone needs its own albedo offset, written to vertex
   colour (our `Wear` attribute path already reaches Unreal).
5. **Moss and lichen are masks, not tints.** Build them from up-facing x cavity/AO x joint proximity x breakup noise
   (moss), and from exposed convex x spot noise (lichen). Write them to the vertex-colour channels for kit pieces,
   and to a baked mask texture for unique-UV rocks.
6. **UVs by class.**
   - Kit masonry: tiling library textures, box UV per stone with a random offset (today's method), UV0 overlap
     waived, texel 5.12 px/cm.
   - Boulders: unique packed UV0 with a baked normal, AO and curvature, plus a tiling detail layer in the material.
   - Lanterns and carved stone: unique UVs or triplanar.
   - Every Fab-bound static mesh keeps a clean UV1. The f1 stone kit dropped UV1 on its Nanite pieces [REPO]; that is
     fine for the game but blocks Fab (ASSET_GUIDELINES section 3).
7. **Gate on measurements plus a blind judge, with measurement as the tie-breaker.** Two stone rounds flipped because
   a judge steered us away from the reference (round 1 footing, stone kit f1) [REPO]. Section 12 is the render and
   judge practice.

---

## 1. What our own rounds say (the evidence)

| Piece | Method | Result | Why (my reading of renders and notes) |
|---|---|---|---|
| Kit 1 footing (r3) | `pillow_face`: Chaikin-rounded convex outline, quarter-round shoulder, superellipse crown, 2 octaves of relief, moss in joints, under a dressed course | "closest piece to its sheet" (round 3 judge) [REPO] | The outline and crown were right for the sheet's rounded pillow rubble. The joints were dark and mossy. The scale matched the sheet |
| Stone kit round 0 wall | `lay_face_r0`: rounded quads in rough courses, pillow stones, packing chips, pebbled `M_DK_JointEarth` joints | 6 / 10 [REPO] | The judge could pick it: uniform pillows, wide pebbled joints, chocolate "sponge" granite at sunset. My look at `renders/wall/sbs_close_stone_faces.png`: rounded rectangles on a grid, one corner radius, brown |
| Stone kit f1 | `lay_courses` 5-7 sided flat polygons, `dressed_stone` flat crowns, pale tint | 5.5 [REPO] | It followed judge 1 into pale polygonal stones. The reference is rounded mid-grey pillows with moss in the joints (judge 2 and the owner) |
| Stone kit f2 (built, not judged) | `lay_rounded` + `pillow_stone` (round 0 shapes, mixed widths, upright ovals) | not judged | `renders/f2/sbs_close_stone_faces.png`: better tone, but still rounded rectangles on visible straight courses. Very regular corner radii. Stones float on a flat brown joint plane. Weak crown shading |
| Pine D rock | visual hull of traced front/side outlines, 26 chip planes per mass, 3 fused masses (`Scripts/vegetation/rock.py`) | "a big faceted block" [REPO] | One scale of flat facets with sharp arrises and no rounding. No cracks or crevices. The reference rock is 2-3 lobes, craggy at 3 scales, with softened arrises, dark crevices and lichen |
| Sand, mountains (kit 2, round 5) | procedural natural surfaces | our weakest (5.5; "smooth sine mountains") [REPO] | Single-scale noise, no structure. The same failure as a noise-displaced boulder |

**Measured, reference close crop against ours** (method in section 11; linear luminance Y; "stone" = the brightest
half of the pixels; joint = Y < 0.45 x median):

| Image | Y p10 / p50 / p90 | p90 / p50 | dark-joint fraction | stone hue / sat | joint RGB (sRGB 0-1) |
|---|---|---|---|---|---|
| Reference (`f2/refcrops/ref_close_stone_faces.png`, from `dojo_landscape_ref.png`) | 0.044 / 0.297 / 0.606 | 2.04 | 0.25 | 32 deg / 0.24 | 0.32 0.25 0.18 |
| Round 0 (`wall/sbs_close_stone_faces.png`, right half) | 0.015 / 0.078 / 0.129 | 1.65 | 0.24 | 27 deg / 0.26 | 0.15 0.12 0.09 |
| f2 (`f2/sbs_close_stone_faces.png`, right half) | 0.024 / 0.157 / 0.203 | 1.29 | 0.22 | 23 deg / 0.16 | 0.18 0.14 0.11 |

Read with care. The reference is daylight; ours are sunset renders, so the absolute Y is not comparable. The
*ratios* and the *hue* are comparable:
- The joint area is already right: about a quarter of the face in all three.
- What differs is the **spread of value across each stone**. The reference crowns catch light, and the lower rims
  fall into shadow.
- The **hue** also differs: ours is pinker.
So f3 should change crown height and profile, albedo per stone and the tint, not the joint width.

**Lessons carried into this study:**
- Man-made stone from sheets works when the outline is traced or measured.
- Natural stone fails when it is one noise or one facet scale.
- Judges steer wrong on stone twice out of three rounds, so measure first.
- CLAUDE.md applies: if a construction does not converge, change the method.

---

## 2. Method map (what to use for what)

| Class | Primary method | Secondary / optional | Avoid |
|---|---|---|---|
| Dressed face stone (uchikomi, kirikomi, ashlar, coping, quoins, sangi-zumi corner blocks) | analytic: 2D outline, then ring loft with arris + crown (`pillow_face`) or rounded box lattice (`rough_block`), then chips by `bisect_plane` or boolean | bmesh bevel + subdivide + displace for sharp-cut kirikomi blocks | height-field relief on flat plates (failed on the Snow Flower pieces, CLAUDE.md) |
| Rough/natural face stone (nozura-zumi, rubble, footing, dry stone) | SDF lumps from a stone library (section 5) or `pillow_face` with high crown and irregular outline | per-stone plane chips then SDF opening | pure 3D noise on an icosphere ("potato") |
| Packing stones / wedges | small SDF lumps or chipped hulls placed in the layout's triangular gaps, recessed | instancing from the library | random scatter not tied to gaps |
| Steps, slabs, kerbs, flags | `rough_block` slabs + wear (tread hollow, nosing round, chips); layout by guillotine splits (ashlar paving) or power diagram (crazy paving) | | per-vertex noise on sparse lattices (r0 "lumpy sponge" treads) |
| Lanterns, carved stone | lathe / loft / prism primitives in `kit1_geo` (`lathe`, `prism`, `dome`), crisp small bevels, then SDF opening at 3-8 mm only if the piece should look weathered | unique UV + baked AO | box UVs on round parts (seams; see the materials README) |
| Boulders, river stones, cliff chunks, tree rock | SDF pipeline (section 7): chipped lobes, union, opening, cracks, noise; high to low bake | strata slicing for layered rock; own Voronoi bisect fracture for cliff faces | noise blob; raw faceted hull |

---

## 3. Individual dressed stones

### 3.1 What we have (keep it)
- `kit1_geo.pillow_face` [REPO] builds a face stone from a convex outline. It Chaikin-rounds the corners, wobbles the
  rim, adds a side wall back to `depth`, a quarter-round shoulder (`edge`) and a superellipse crown (`bulge`, `crown`
  exponent). It adds 2-3 octaves of real relief (9 / 26 per m) faded in from the shoulder. It writes explicit tile-unit
  UVs.
- `rough_block` / `rounded_stone` [REPO] build a subdivided box mapped to a rounded box, pillowed on the front face,
  with 3 relief octaves.
- `sk_shared.dressed_stone` (f1 numbers) and `sk_shared.pillow_stone` (f2 numbers) are parameter sets over
  `pillow_face`.

### 3.2 Improvements (to be tried in f3)
1. **Vary the corner radius per corner, not per stone.** Real dressed stones have one or two sharp corners and one
   knocked-off corner. Use per-vertex Chaikin weights, or cut one corner (`_cut_corner` exists) and round the rest
   with 0.5-1.5 x the mean radius. f2 reads "rounded rectangle" because every corner has the same radius.
2. **Asymmetric crown.** Put the crown peak off-centre and higher toward the top edge (`peak_off` already exists; use
   0.15-0.30, not 0.10-0.12). Let the lower rim roll off further than the upper one: rain and hammer dressing leave
   the bottom edge more rounded. That produces the reference's lit crown and dark lower rim (p90/p50 of about 2).
3. **Mask the relief away from the arris.** Today the relief fades in over 3 rings from the shoulder. Keep the arris
   *line* clean, and make the wear on the arris a separate term: pits and chips on exposed top corners only. The
   "crisp but worn" read is a clean line with a few bites out of it, not uniform noise on the edge.
4. **Chips.** Take 0-3 chips per stone on the exposed corners with `bmesh.ops.bisect_plane(clear_outer=True)`, then
   fill (`contextual_create` / `edgeloop_fill`) [VERIFIED 5.2]. That gives a flat conchoidal facet. For a scooped chip,
   subtract a small noisy icosphere with the Boolean modifier using the `MANIFOLD` solver. In the probe that took
   7 ms for one chip on a beveled cube, `EXACT` 13 ms, `FLOAT` 1 ms but less robust [VERIFIED 5.2]. Recompute the
   normals and weld afterwards (`kit1_geo.weld`).
5. **Bevel alternatives.**
   - `bmesh.ops.bevel(geom, offset, segments, profile, affect='EDGES', clamp_overlap=True)` [VERIFIED 5.2] suits
     kirikomi-hagi (sharp-cut) blocks. A 0.5-1.2 cm offset with 2-3 segments and profile 0.5-0.7, then a light
     subdivision and a displacement *masked to the face interior*.
   - Blender 5.2 adds a **Mesh Bevel geometry node** [VERIFIED 5.2: `GeometryNodeMeshBevel`; WEB: 5.2 release notes].
     Its inputs are Selection, Affect Kind, per-side Start/End Left/Right Offset, Offset, Miter, Spread, Segments,
     Shape and a Profile curve. Its outputs include the bevel's Vertex/Edge Face and Outer/Mid Edge selections, which
     are ready-made masks for edge wear. It is new; treat it as a spike, not a dependency [UNCERTAIN on stability].
6. **Size and density rule.** Keep the ring step at 2-3 cm on a 30-60 cm stone. The r3 footing used 1.8 cm, the f2
   pillow 2.1-3.2 cm. At the wall's 5.12 px/cm, anything under about 4 mm belongs in the texture, not the mesh.

### 3.3 Parameters come from the reference, not from taste
For each masonry type, put these numbers in a spec JSON before building (section 11 measures them):
- the outline class (quad, 5-7 gon, oval, free);
- the corner radius as a fraction of the stone's short side (distribution);
- the crown height as a fraction of the short side (the r3 footing used about 7 %: `bulge = 0.07 x s`);
- the shoulder radius;
- the proud distance (how far the face stands in front of the joint core);
- the tilt spread (the f1 value was ±2 deg);
- the chip rate.

---

## 4. Wall layout (packing) algorithms

All layouts work in **unrolled face coordinates (a, s)**: a = along the wall, s = down the face from the top. Our
`lay_courses` / `lay_rounded` already work this way, with `F.P(a, z)` mapping onto the battered face [REPO]. Each
generator outputs convex (or near-convex) polygons plus a *joint inset* per stone. The stone builder turns each polygon
into a 3D stone on the face's tangent plane at the polygon centroid, and `rigid_warp` moves it rigidly onto the
curved batter, so no stone is sheared [REPO].

### 4.1 Coursed (uchikomi-hagi, ashlar, the dojo footing)
- **Course heights:** draw them from the measured distribution. Allow *broken courses*: a course that splits into
  two thinner ones for 1-3 stones, then merges back. This is the most visible difference between hand-laid walls and
  our "straight course lines" in f2.
- **Widths:** `mixed_widths` [REPO] draws about 24 % upright, 58 % ordinary and 18 % long stones. Replace the fixed
  shares with the reference's measured width/height histogram.
- **Stagger:** "one over two, two over one". Every vertical joint lands near the middle third of the stone below it
  [WEB: DSWA, Stone Trust]. Enforce a minimum overlap of 0.25 x the stone width, and reject any 4-way joint (a
  vertical joint continuing through two courses).
- **Wandering boundaries:** the course boundary is a piecewise-linear curve through the joints (`Boundary` [REPO]),
  amplitude 3-6 % of the course height. Pin it straight at module ends so kit modules interlock (`pins`).
- **Upright / through stones:** tall stones spanning two courses (the `talls` in `lay_rounded`). In dry stone, through
  stones about 1 m apart halfway up [WEB: Stone Trust]. For a retaining ishigaki, place long stones (the "tail"
  depth) where the craft study says.

### 4.2 Random / polygonal (nozura-zumi, rubble, crazy paving)
1. **Seed points** by Poisson-disc sampling with a per-point radius drawn from the measured size distribution.
2. **Cells** by a *power diagram* (weighted Voronoi) so that big and small stones coexist. Then run 2-4 Lloyd
   iterations toward the centroids, which removes slivers while keeping the size mix [WEB: Bourne and Roper; Lloyd].
   `kit1_geo.voronoi_cells` does plain Voronoi by half-plane clipping (`convex_clip`) [REPO]. For a power diagram,
   shift each bisector by (w_i - w_j) / (2 |p_i - p_j|). No scipy in Blender 5.2's Python [VERIFIED 5.2: scipy
   missing, numpy 2.3.4], so keep our own clipper.
3. **Anisotropy:** stretch the sampling domain by the measured mean aspect ratio (for example 1.3 x in `a` for stones
   laid long), run the diagram, then unstretch.
4. **Joints:** inset each cell by its own half-joint (`inset_convex` [REPO]), drawn from the measured joint
   distribution.
5. **Rejects:** drop any cell whose narrowest caliper width is under 6 cm (`min_width`, f1). Mark it as a packing
   gap instead (4.4).

### 4.3 Ishigaki specifics
The craft is in `A_craft.md`; these are the geometry hooks.
- **Batter (sori):** a concave profile d(s) that steepens toward the top. The kit uses d(s) = 0.10 s + 0.035 s^2
  [REPO]. Store it as a function of s, and never deform stones by it (rigid placement only).
- **Corner (sangi-zumi):** alternate long and short rectangular blocks, with the long side on alternate faces per
  course. The ratio comes from the reference, typically 2-3 : 1 [UNCERTAIN; see `A_craft.md`]. The corner blocks are
  `rough_block`s placed *first*. The field stones then fill the remaining polygon in each course, using `force_first`
  / `force_last` [REPO].
- **The three types as layout modes:**
  - **nozura-zumi:** 4.2 with natural lumps (section 5), wide irregular joints, packing stones in every gap.
  - **uchikomi-hagi:** 4.1 with rough courses, shaped faces, fewer gaps, small wedges at junctions.
  - **kirikomi-hagi:** 4.1 or 4.2 with near-zero joints (2-5 mm), crisp bevels (bmesh bevel 3.2.5), polygons fitted
    edge to edge. Nothing recessed.
- **Coping and the top line:** a separate course of long blocks. The coping line is straight in plan but follows the
  sori at the ends.

### 4.4 Packing stones and wedges
After the layout, find the gaps: the triangle-ish holes where three stones meet, and any rejected sliver cell. Fill
each gap with 1-3 small lumps, scaled to 60-85 % of the gap's inscribed circle. Recess them 1-4 cm behind the face
plane, and rotate each one so its long axis follows the gap. The mason-inspired generators treat the wall as
constrained packing and add wedging stones for exactly this [WEB: Saloustros-type microstructure generator,
image-convolution packing]. We only need the visual rule: the gaps are dark, and each holds a small stone at the back.

### 4.5 Joint depth as geometry
- Every face stone has a side wall running back `depth` (22-24 cm) [REPO]. The joint core (`M_DKT_JointDark`) sits
  8 cm behind the face [REPO].
- The **visible joint** is the rim gap plus the pillow shoulder falloff plus the rounded corners. f1 measured 1.8 cm
  median, with a p90 of 4.6 cm at diagonal junctions [REPO].
- Measure the visible joint by ray scans (as `measure_f1.py` does) and compare it with the reference (section 11).
- The joint core should not be a flat plane. Give it a few centimetres of noise, occasional soil pockets and small
  packing-stone backs, so grazing light does not show a sheet ("stones floating on a board" in f2).

### 4.6 Heavy alternative (not for now)
True 3D mason-style packing (placing stone meshes by stability and contact) exists in the engineering literature
[WEB: 3D microstructure generator; image-convolution stone packing; Minnesota bin-packing]. It gives very
convincing dry-stone and rubble sections. It is too slow and too complex for a kit module, and the visible face is
2D anyway. Keep it as an idea for a hero dry-stone ruin.

---

## 5. Rubble, lumps and a stone library

For nozura-zumi, rubble footings, dry-stone field walls, packing stones and scree, build a **library of 24-40 unique
lumps** once per stone type, then *pick* per layout cell:
1. **Lump construction:** a convex hull of 30-60 jittered points on an ellipsoid (the measured aspect ratios), chipped
   by 6-20 planes (`bisect_plane`, never on the bottom or back). Then an SDF opening at r = 4-12 % of the short axis
   (section 7.2) and meso noise.
2. **Fit to cell:** for each layout polygon, choose the lump whose front silhouette (projected onto the face plane)
   has the best IoU with the polygon after a similarity transform. Allow a small non-uniform scale (at most ±12 %)
   and a rotation about the face normal. Library reuse is then invisible, because each placement differs in scale,
   rotation and neighbours. This is the "few sculpted stones, many placements" practice of modular environment art
   [WEB: Experience Points modular kit].
3. **Merge per module:** join the chosen stones into one mesh per kit module for Nanite. Nanite Assemblies (instanced
   parts in one asset) are experimental and USD-only in 5.7 [WEB], so do not depend on them [UNCERTAIN for 5.8].

---

## 6. Steps, paving, kerbs and footings

- **Slabs:** `rough_block` slabs with wear [REPO, track 9]:
  - a tread hollow of 5-8 mm, deepest at the nosing and along the walking line;
  - a 2-3 cm rounded nosing;
  - 0-2 chips on the nosing;
  - ±4 mm per-stone tilt;
  - the top keeps about 30 % of the block relief.
  Keep this, and drive the hollow from a **traffic field**: a 2D density along the path centre line, higher on the
  stair centre and at landings. That replaces the per-stone constant.
- **Tread slabs per step** come from the reference count. The f1 fix went to 1-2 long slabs by judge; the owner's
  reading is 3-5 short blocks [REPO]. Measure it (section 11) and put it in the spec.
- **Paving layouts:**
  - ashlar / random rectangular: recursive guillotine splits of the landing rectangle, with minimum sizes and a
    no-4-way-joint check;
  - running bond: offset rows;
  - crazy paving: the 4.2 power diagram with flat crowns.
  - Joints 1.0-1.6 cm, flush tops ±3 mm (the f1 landings measured -7 to +1 mm) [REPO].
- **Kerbs and footings:** `rough_block` runs with a buried depth. Everything runs 0.35 m below the walking level in
  the stair kit [REPO]. The ground-contact dirt band comes from `bake_wear` B.
- **Collision:** unchanged from the kit rules: a convex ramp per flight, flat boxes per landing, one flat-topped box per
  cheek stone [REPO].

---

## 7. Natural rocks and boulders

### 7.1 Why the two simple methods fail
- **A noise-displaced sphere or blob** has no planes and no arrises, and its detail is the same everywhere. It reads
  as a potato, or as "smooth sine mountains" [REPO round 5].
- **A plane-chipped convex hull** (pine D) has planes but only at one scale. Every arris is knife-sharp and there is
  no concavity, so it reads as a crystal or a faceted block [REPO].

Real granite boulders (the landscape reference's river boulders, and the ishigaki's big stones) are **sub-rounded
blocks**: large near-planar faces from joint fractures, arrises rounded by weathering, a few deep cracks, pits, and
concave clefts where lobes meet. Artists build them in three passes: primary silhouette and planes, then secondary
fractures and edge breaks, then tertiary pits and chips [WEB: Beyond Extent; Neil Blevins; polycount]. The SDF
pipeline below does each pass with one controlled operation.

### 7.2 The SDF boulder pipeline (recommended)
All steps are headless-safe. The GN nodes were probed in 5.2 [VERIFIED 5.2]:
`GeometryNodeMeshToSDFGrid`, `GeometryNodeSDFGridOffset`, `GeometryNodeSDFGridBoolean`, `GeometryNodeSDFGridFillet`,
`GeometryNodeSDFGridMean`, `GeometryNodeSDFGridMedian`, `GeometryNodeSDFGridLaplacian`,
`GeometryNodeSDFGridMeanCurvature`, `GeometryNodeGridToMesh`, `GeometryNodeSampleGrid`.

1. **Lobes (primary).** 1-4 convex hulls from jittered ellipsoid points, sized and placed from the traced outlines
   (front and side). Each lobe is chipped by 10-25 planes at 0.72-0.95 of its radius, never on the ground side.
   For a cliff or joint-block rock, use a few *parallel* plane families (joint sets) instead of random directions.
   That is what makes granite look like granite and not like a crystal.
2. **Union.** Build a Mesh to SDF Grid per lobe (voxel 0.5-1 cm for a 1-2 m boulder) and take the SDF Boolean union.
   A *smooth* union (a small closing, below) makes the cleft between lobes.
3. **Round the arrises (the key step).** An **opening** is SDF Offset -r, then SDF Offset +r. It rounds every
   convex arris to radius r and leaves the flat faces where they were.
   - Probe on a 1 m cube, r = 0.10: the corner extent went from 0.866 to 0.788, and the theory for a rounded cube
     says 0.793. The dimensions stayed 1.0 [VERIFIED 5.2].
   - A **closing** (+r then -r) or **SDF Grid Fillet** rounds concave corners (clefts, lobe joins).
   - Choose r by rock class: sharp talus 1-3 % of the short axis; the tree rock and cliff chunks 4-8 %; river boulders
     15-30 %.
4. **Cracks (secondary).** Subtract thin slabs (SDF Boolean difference) along 1-3 planes that cut the rock. Each slab
   is 1-3 cm wide, widens toward the surface and runs 10-40 cm deep. The crack lines in `ref_boulder_crop4x` follow
   the joint planes. Then do a small opening so the crack lips round too.
5. **Meso noise (tertiary).** Displace along the normal with 2-3 octaves (the probe used 3 cm @ 2/m, 1.2 cm @ 6/m,
   4 mm @ 18/m). *Mask* the noise down on the rounded arrises and up on the flat faces and in the clefts. Weather
   pits (tafoni, visible on the reference boulder) are small SDF subtractions of noisy spheres on the vertical faces.
6. **Mesh.** Grid to Mesh with **Threshold 0**. The node's default threshold is **0.1** (a density-grid default). On
   an SDF that meshes the 10 cm offset surface, or nothing at all when the narrow band is thinner than 10 cm
   [VERIFIED 5.2]. Set the Band Width to at least r / voxel + 3 voxels, or the offsets clip.
7. **High to low.** Probe numbers for a 3-lobe boulder about 1.4 m across [VERIFIED 5.2]:
   - voxel remesh at 1 cm: 77k quads in 0.05 s;
   - displacement: 0.08 s;
   - decimate COLLAPSE from 154k to 4k tris: 0.7 s;
   - smart-project UV on the low poly: under 0.1 s;
   - normal bake (tangent, selected to active, cage extrusion 3 cm, EXTEND margin): 0.2 s at 1k, 0.8 s at 2k;
   - AO bake at 2k and 64 spp: 5.9 s on the CPU.
   Keep the Nanite high (roughly 50-300k tris) for game use, and a 2-6k LOD0 with baked maps for non-Nanite and Fab
   LOD statements.
8. **Baked maps:**
   - Normal: tangent, then DirectX via `textures.flip_normal_green` [REPO].
   - AO: into ORM.R.
   - Curvature: from the baked normal, by numpy divergence: dNx/du + dNy/dv. The probe gave p1/p99 of -0.19 / +0.18
     [VERIFIED 5.2]. Pointiness is density-dependent and patchy on decimated meshes [WEB: StraySpark]. The SDF Mean
     Curvature grid, sampled to vertices, is a second source for the high poly [UNCERTAIN, not probed].
   - An optional height or cavity map for the moss mask.

### 7.3 Rock sub-types
- **River boulders:**
  - large opening radius and gentle noise;
  - lobes elongated along the flow;
  - a wet band: albedo darker by 20-35 % below a waterline height, and a smoother roughness (a mask channel);
  - moss only above the splash line.
- **Cliff / outcrop chunks:**
  - joint-set planes;
  - a few strata slices: cut into layers, scale each a little, rejoin before the opening, as in the Houdini strata
    method [WEB: 80.lv procedural rock];
  - designed to be kit-bashed and overlapped, with the bottoms buried.
- **Scree / rubble:** the section 5 library with a small opening radius.
- **The tree rock (pine D):**
  - traced outlines (the visual hull stays the 2D authority) split into 2-3 lobes along the trunk crack;
  - chip planes in joint families;
  - SDF union, opening r = 5-8 %, cracks where the roots go;
  - the root-walk over the *final* surface (BVH, as in `build_pines.py`) [REPO];
  - a separate base mound mesh.
- **Own Voronoi fracture for cliff faces:** Cell Fracture is not bundled in 5.2. It is an extension on
  extensions.blender.org [VERIFIED 5.2: operator missing; WEB], and a download needs the user's go. It isn't needed:
  a cell is the intersection of the half-spaces of the perpendicular bisectors of the seed points, so repeated
  `bmesh.ops.bisect_plane(clear_outer=True)` on a copy of the source gives each cell [WEB: 4rknova; Cell Fracture
  design]. `mathutils.geometry.points_in_planes` exists for hull-from-planes [VERIFIED 5.2].

### 7.4 Gotchas found while probing
- **`--factory-startup` loads the default scene: Cube, Camera, Light.** A boulder built at the origin sat inside the
  2 m default cube, and every AO bake came out 0.0. The same bake on a clean scene gave a median of 0.95 [VERIFIED
  5.2]. Our kit builders clear the scene; any new stone script must do so too (`for o in list(bpy.data.objects):
  bpy.data.objects.remove(o)`).
- Hiding the low poly from render (`hide_render`) makes the bake refuse to run ("not enabled for rendering")
  [VERIFIED 5.2]. To stop the low poly occluding the AO, move it away, or bake the high poly's AO before the low poly
  exists.
- The bake target image must be the *active* Image Texture node in every material of the low poly (the pipeline's
  `bake_ao` handles this) [REPO].
- Voxel remesh and SDF need closed input. Check `not e.is_manifold` for zero edges after the chips and fills.

---

## 8. Procedural granite, moss and lichen

### 8.1 Granite albedo and relief
- Our library granite (`dojo_tex_gen.granite`, 4 m tile, 2048 px = 5.12 px/cm, 1.95 mm/px) carries chipped facets at
  3.5 and 9 cm plus cavity darkening [REPO]. On individual stones with their own geometric relief, those facets double
  the relief and read as "sponge" at arm's length. r3 already made the grain finer after "terrazzo" [REPO].
- For kit stone, split the set: a *micro* set (grain, mica sparkle, speckle under 5 mm; normal strength 0.15-0.3) and
  per-stone *macro* in vertex colour.
- Granite grain has three mineral populations: pale quartz, white-to-pink feldspar, black biotite and hornblende.
  Model them as three thresholded multi-scale noises with the measured area fractions. Grade the result to the
  reference's measured stone hue: 32 deg, sat 0.24, on the landscape reference's walls.
- **Per-stone variation:**
  - a random albedo offset (±8-12 % value, ±3 deg hue);
  - darker undersides;
  - lighter weathered tops;
  - grime down from joints (rain streaks).
  `sk_shared.stone_tone` already writes grime per part and top wear into `Wear` [REPO]. Extend it with a hue channel
  or a second colour attribute. UE imports one vertex-colour set [REPO, tree study C].

### 8.2 Moss and lichen masks
- Build the masks on the mesh (vertex colour) for kit pieces, and bake them to a mask texture for unique-UV rocks.
- **Moss:**
  ```
  moss = smoothstep(up_facing)
       x (cavity or AO occlusion)
       x joint proximity (distance to the stone rim)
       x breakup noise at 2-3 scales
  ```
  - up_facing: normal z over 0.3-0.5;
  - joint proximity: along the joint lines and on ledges;
  - on boulders: tops and north-side clefts.
  - This is the rule the judges asked for: moss in joints and on ledges, never as a face tint [REPO f1].
- **Lichen:**
  ```
  lichen = exposure (convex curvature, high AO)
         x spot noise (Voronoi F1 thresholded into 2-15 cm roundish patches)
  ```
  Pale grey-green and ochre, on the reference's boulders and lantern tops.
- Unreal combines these with a world-aligned top blend and tiling moss detail (`B_unreal.md`) [WEB: Michael Arby
  moss tutorial; 80.lv rock shader].
- **Nanite:** vertex colours baked *into the mesh asset* do reach Nanite materials (our `Wear` path) [REPO].
  *Per-instance painting* on Nanite needs the Texture Color tool (UE 5.5+, virtual textures on) [WEB: Epic]. So
  per-placement variation should come from a per-instance random value in the material, not painted vertex colour.

---

## 9. UVs and texel density

| Class | UV0 | Maps | Texel | Notes |
|---|---|---|---|---|
| Kit masonry (walls, steps, paving) | box UV per stone in tile units with a random per-part offset (`sk_shared._box_uv`, `BOX_UV_MATS`) [REPO] | library tiling sets + vertex colour Wear/tone/moss | 5.12 px/cm (third-person rule; `qa_check --texel 5.12`) | UV0 overlap and tile range are waived (`WAIVE`) [REPO]. Never mirrored |
| Unique boulders / cliff chunks | unique, packed (smart project or angle-based seams on the hidden side; `pack_islands` with rotate, margin about 0.008) [VERIFIED 5.2: operator props] | baked N, ORM (AO + roughness), a mask (moss / lichen / wet), plus a tiling detail in the material | 5.12 px/cm for the unique maps, capped at 2k-4k per rock. The tiling detail adds 10-20 px/cm | Megascans Nanite rocks ship 8k maps, which makes texel density inconsistent in scenes; a tiling detail layer is the common fix [WEB: polycount] |
| Lanterns, carved stone | unique or triplanar (box UV seams on round parts: materials README) [REPO] | library + baked AO | 5.12 (10.24 for a hero close-up) | |
| Trim-sheet option (ashlar coping, sills) | strips of a stone trim sheet | trim atlas | 5.12 | for long straight dressed members [WEB: trim-sheet guides] |

- **UV1:** Fab needs a non-overlapping UV1 in 0-1 on every static mesh, with Lightmap Coordinate Index 1
  (`ASSET_GUIDELINES.md` section 3). The f1 stone kit dropped UV1 on its Nanite pieces because the two R200 flights
  failed the UV1 overlap check [REPO]. Before any Fab release, restore UV1 with a lightmap pack per piece, or with
  Unreal's generated lightmap UVs.
- Nanite takes at most 4 UV sets [tree study C, VERIFIED 5.8 SRC there].

---

## 10. Fitting into the repo pipeline

### 10.1 Where code goes
Other chats own `Scripts/dojo/stonekit/` (lock `dojostonekit`) and `Scripts/vegetation/` (pines). Do not edit them
from a study or another chat. Proposed neutral library, used by the dojo kit and by future kits:

| Module | Content |
|---|---|
| `Scripts/stone/stone_geo.py` | dressed stone, slab, block and lump builders, lifted from `kit1_geo` (`pillow_face`, `rough_block`, chips) behind stable signatures; the Geo container stays `kit1_geo.Geo` |
| `Scripts/stone/stone_layout.py` | course, power-diagram, guillotine and ishigaki-corner layouts in (a, s); gap finder for packing stones; the layout statistics of section 11 |
| `Scripts/stone/stone_sdf.py` | builds and applies GN node groups from Python: SDF union, opening and closing, crack subtract, `Grid to Mesh` with threshold 0; a numpy fallback via voxel remesh |
| `Scripts/stone/stone_bake.py` | high to low: clean scene, cage, normal/AO bakes via `pipeline.textures`, curvature from the normal, mask bakes |
| `Scripts/stone/stone_measure.py` | the reference and render measurements (section 11), numpy + PIL only (no scipy / skimage / cv2 on this PC) [VERIFIED] |

Each builder follows the house shape [REPO]:
- `build_<kit>.py` run as `blender -b --factory-startup --python ... -- args`;
- a spec JSON;
- `WorkFiles/<item>/build/{measure, qa_report, export_report}.json`;
- a `run_all.sh` chaining textures, build, render and compose.

### 10.2 Export and QA
- **Export only through `pipeline.export_fbx`** after `pipeline.qa_check`. Pass the waive set for tiling kit
  materials: `{"uv0_tile_range", "uv_no_overlap"}`, as kit 1 and the stone kit do [REPO]. Unique-UV boulders pass
  with no UV waiver.
- **Collision** (UCX keyed to the render node name; with LODs `UCX_<base>_LOD0_NN`):
  - wall modules: one hull per batter segment;
  - steps: the ramp;
  - boulders: 1-4 hulls from the lobes (`helpers.make_ucx_hull`, max_verts 32) [REPO].
  - The lobes are convex before the union, so they are ready-made hull sources.
- **LOD / Nanite:**
  - Nanite for anything over about 2k tris (dojo decision) [REPO].
  - Light pieces ship LOD0-2 via `decimate_lods`.
  - Boulders ship the Nanite high plus a baked low as its LOD statement or fallback.
- **Budgets seen:** wall module LOD0 up to 386k (StairOpening_H4), flights 5.6-121k [REPO]. A 1-2 m hero boulder at
  100-300k Nanite tris is in line.
- **Verification:** fresh-process FBX re-import (`verify_stairs_fbx.py` pattern) [REPO], then the Unreal verify in
  a second fresh process on the exact bytes (CLAUDE.md).

---

## 11. Measuring a reference (pixels, never eyeballing)

All in numpy + PIL (available: `py -3`, numpy 2.5.3, PIL 12.2.0; no scipy, skimage or cv2) [VERIFIED].

1. **Scale.** Take pixels per metre from a known size in the same image plane: the sheet's 1.8 m figure, a riser
   (0.167 m on our grid), or a module length. Record the uncertainty. In a perspective image, measure only near the
   feature.
2. **Tracing.** Upscale the crop 3-4 x (LANCZOS). Trace stone outlines as polygons, by hand or with a helper script.
   Store them in `References/<Item>/trace_<crop>.json` with their scale. Tracing is the 2D outline authority
   (CLAUDE.md). At the landscape reference's resolution (1024 x 1536) a wall stone is only 15-25 px tall, so trace
   30-60 stones per wall type and accept ±1 px.
3. **Stone statistics from the traces:**
   - area, and equivalent diameter sqrt(4A / pi);
   - the minimum-area bounding box → length, height, aspect and orientation;
   - corner radius / short side (fit circles at the vertices);
   - convexity (area / hull area);
   - course height and course waviness (the std of boundary heights along a course);
   - the fraction of upright stones;
   - the number of 4-way joints per m².
   Compare the distributions (median and p10 / p90, or a KS distance), not the means.
4. **Interlock.** The *line of minimum trace* (LMT): the shortest path through the joints between two corners,
   divided by the straight distance. It is the masonry-quality index used in engineering, where good interlock gives
   a longer path [WEB: Borri MQI; geometric indices]. Compute it on the traced joint graph with Dijkstra, which is
   easy in plain Python.
5. **Joints.** Take intensity profiles perpendicular to 20+ joints and measure the FWHM of the dark trough, in cm and
   as a fraction of the adjacent stone height. Also measure the dark-joint area fraction: Y < 0.45 x median; the
   reference crop gives 0.25 (section 1).
6. **Value and hue per region.** Work in linear luminance Y. Per region (stone crowns, joints, moss, lower courses,
   wet band), record:
   - the Y percentiles p10 / p50 / p90;
   - the p90 / p50 ratio (form contrast);
   - the hue and saturation of the brightest half;
   - the joint RGB.
   The Y values depend on the light, so compare ratios and hue between images with different lighting, and absolutes
   only under matched lighting.
7. **Boulders:**
   - silhouette IoU against the traced front and side (pines used 0.72-0.80 gates) [REPO];
   - the plane fraction: the share of the surface whose normal is within 10 deg of one of k fitted planes;
   - the edge-rounding ratio (the arris radius over the short axis, from profiles across arrises);
   - crack count and length;
   - moss cover on the up-facing area.
8. **Ours, the same way.** Render our piece with a camera matching the reference crop (focal length, height, angle),
   with light matched as closely as possible (the sun direction from the reference shadows). Run the *same* script
   on our render. A gate passes on ratios within ±15 % and on distributions (for example the median size within 10 %
   and the p10 / p90 within 20 %).

---

## 12. Render and judge practice

- **Fixed render set per stone asset:**
  - ortho front, side and top with the 1.8 m figure;
  - a 3/4 view;
  - a grazing-light close-up at 1.5 m (the "sponge" test);
  - a matched-camera reference side-by-side for every reference crop (`Scripts/armory/side_by_side.py`) [REPO];
  - for walls, a straight-on elevation (for the layout measure) and a raking-sun view;
  - for rocks, a silhouette pass (black on white) for IoU.
- **Two lighting rigs:** the neutral studio grey of the sheets, and the reference's light (daylight for
  `dojo_landscape_ref`, sunset for the dojo scene). Judge the *shape* under the studio rig and the *look* under the
  reference rig.
- **Blind judges:**
  - Show image pairs only (ref | ours, in random order and random sides).
  - Ask for (a) which is the copy, (b) the top 3 *shape* differences, (c) the top 3 *material* differences, each tied
    to a location.
  - Ask for descriptions, never for prescriptions ("make the stones polygonal").
  - Use two judges with independent prompts.
- **Measurement is the tie-breaker.**
  - Accept a judge delta only if the section 11 measurement agrees, or if the delta concerns something the
    measurements do not cover.
  - When two judges disagree, measure. This rule would have stopped both flips: the round 1 footing and stone kit f1
    [REPO].
- **Staged rounds:**
  1. layout only (flat-shaded polygons against the traced reference);
  2. one stone type in close-up;
  3. the full piece.
  Stop and show the user when a stage fails decisively (CLAUDE.md, memory "stop early").

---

## 13. Pitfalls

1. Stacking tiling-texture relief on geometric relief: the "sponge", pitted look.
2. One corner radius, one crown and straight course lines: the "rounded rectangles on a grid" look (f2).
3. A flat joint-core plane under grazing light: stones floating on a board.
4. Chasing a judge's style word ("polygonal", "pale") against the reference (f1).
5. Noise blobs for boulders (potato) and single-scale plane chips (crystal / faceted block, pine D).
6. SDF Grid to Mesh with its default threshold 0.1 (meshes the offset surface, or nothing); a band width smaller than
   the offsets.
7. The factory-startup default cube enclosing the object (every AO bake black).
8. A curve-deformed batter shearing stones: always move each stone rigidly (`rigid_warp`).
9. Tint-only moss: masks only, in joints and on ledges.
10. Measuring absolute brightness across different lighting: use ratios and hue.
11. Mirrored or rotated UVs after a bake; box UVs on round carved parts.
12. Nanite pieces without UV1 in a Fab release.
13. Depending on add-ons or extensions (Cell Fracture, Rock Generator, A.N.T.) at build time. Probes show none is
    installed in 5.2 [VERIFIED 5.2], and a download needs the user's go. Our own bmesh / GN code covers every use.

---

## 14. Uncertain (to confirm before relying on it)

- **Mesh Bevel geometry node (new in 5.2):** its behaviour on high-density or non-manifold stone meshes, and the exact
  output masks, are not tested beyond listing its sockets.
- **SDF Grid Fillet / Mean Curvature:** only their sockets were listed, and they were not run on a stone. The opening
  and closing via SDF Grid Offset *was* verified.
- **Voxel and memory cost of the SDF path on a 4 m wall module at 5 mm voxels** was not measured. The probe used a
  1-1.4 m object at 8-10 mm.
- **SDF output UVs:** SDF output meshes carry no UVs. Unique-UV unwrapping of a 100k+ high poly is not needed (bake
  to the low poly), but a Nanite-high-only asset needs its own UV0 (smart project on the decimated Nanite source).
  The speed and quality of that on 300k tris was not tested.
- **Ishigaki proportions** (sangi-zumi long/short ratio, typical stone sizes per type, sori curve constants): from
  `A_craft.md`, not from this study.
- **UE 5.8 details** (Nanite vertex colour limits, Texture Color painting, Nanite Assemblies status in 5.8,
  world-aligned blend cost): per `B_unreal.md`. The web sources are for 5.5-5.7.
- **The section 1 value/hue numbers** come from a 4 x upscaled, JPEG-like crop of an AI-generated reference, measured
  against sunset renders. They are good for direction (hue, ratios), not for absolute targets.
- **Scratch files:** the probes were written into the session scratchpad with generic names (`probe2.py` ...
  `probe12.py`). That scratchpad also holds other sessions' files with similar names, so some older scratch files of
  the same name may have been overwritten. The kept copies are in `c_probes/`.

---

## 15. Sources

**Local (read):**
- `CLAUDE.md`, `ASSET_GUIDELINES.md`, `FAB_ASSET_STUDY.md`, `TREE_BUILDING_STUDY.md`,
  `WorkFiles/studies/trees/C_blender.md`
- `WorkFiles/dojo/DOJO_QUEUE.md`
- `WorkFiles/dojo/build/stonekit/BUILD_NOTES.md`, `renders/{wall,f1,f2}/sbs_close_stone_faces.png`
- `Scripts/dojo/kit1_geo.py` (`pillow_face`, `rough_block`, `rounded_stone`, `voronoi_cells`, `inset_convex`)
- `Scripts/dojo/stonekit/sk_shared.py` (`lay_courses`, `lay_rounded`, `dressed_stone`, `pillow_stone`, `stone_tone`,
  `rigid_warp`)
- `Scripts/dojo/materials/README.md`, `dojo_tex_gen.py`, `dojo_materials.py`
- `Scripts/pipeline/{qa_check,export_fbx,helpers,textures}.py`
- `Scripts/vegetation/rock.py`, `WorkFiles/dojo/build/pines/BUILD_NOTES.md`, `renders/f1/PineD1_3q_final.png`
- References: `dojo_landscape_ref.png`, `dojo_wall_ref.png`, `dojo_courtyard_stone_ref.png`,
  `dojo_japanese_pine_ref.png`
- Owned rock content, file names only: `Documents/Unreal Projects/Scenery_Tutorial/Content/Megascans/3D_Assets/Nordic_Beach_Rocks_vckqccbga_3d`
  (LOD0 1.9 MB, 1K albedo and normal), `Surfaces/MossyRockyGround`, `BeachCliff`; `Fishermans_Cabin/Meshes/Rocks` in
  DemoGame_1 / MyProject6

**Web:**
- Blender 5.2 LTS release notes, geometry nodes (Mesh Bevel node): https://developer.blender.org/docs/release_notes/5.2/geometry_nodes/
- Mesh Bevel node, manual: https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/mesh/operations/mesh_bevel.html
- Blender 5.0 geometry nodes release notes (SDF grid nodes): https://developer.blender.org/docs/release_notes/5.0/geometry_nodes/
- SDF Grid Fillet node: https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/volume/operations/sdf_grid_fillet.html
- Mesh to SDF Grid node: https://docs.blender.org/manual/en/5.0/modeling/geometry_nodes/mesh/operations/mesh_to_sdf_grid.html
- New grid nodes 5.0 / 5.1 (community overview): https://blenderartists.org/t/new-grid-nodes-from-5-0-5-1-sdf-volumes-voxels-advection/1616473
- Cycles render baking (5.2 manual): https://docs.blender.org/manual/en/latest/render/cycles/baking.html
- Curvature maps in Blender (pointiness vs GN vs normal-based): https://www.strayspark.studio/blog/curvature-maps-blender-substance-painter-alternative
- Cell Fracture extension: https://extensions.blender.org/add-ons/cell-fracture/
- Voronoi fragmentation of a mesh (bisector-plane method): https://www.4rknova.com/blog/2026/07/27/voronoi-fracture
- Procedural rock generation in Houdini (Worley F2-F1, VDB, strata, chipping, polyreduce, bake): https://80.lv/articles/006sdf-breakdown-procedural-rock-generation-in-houdini
- Houdini HIVE, VDB + voronoi rock formations: https://80.lv/articles/houdini-hive-procedural-rock-formations-for-ue4
- Rock shader pipeline ZBrush to Unreal (2k-poly low, curvature/AO masks, top moss): https://80.lv/articles/rock-shader-pipeline-from-zbrush-to-unreal
- Sculpting for environment art (form hierarchy): https://www.beyondextent.com/articles/sculpting-for-environment-art-in-games
- Primary, secondary and tertiary shapes: http://www.neilblevins.com/art_lessons/composition_primary_secondary_and_tertiary_shapes/composition_primary_secondary_and_tertiary_shapes.htm
- Polycount, primary/secondary/tertiary shapes: https://polycount.com/discussion/233026/sculpting-issue-primary-secondary-and-tertiary-shapes
- Procedural generation of rock piles using aperiodic tiling (Peytavie et al. 2009): https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-8659.2009.01557.x
- Modeling rocky scenery using implicit blocks: https://link.springer.com/article/10.1007/s00371-020-01905-6
- A virtual microstructure generator for 3D stone masonry walls: https://www.sciencedirect.com/science/article/pii/S0997753822001218
- A mason-inspired pattern generator for historic masonry: https://www.sciencedirect.com/science/article/pii/S0141029624001664
- Image convolution-based irregular stone packing: https://www.sciencedirect.com/science/article/pii/S0377221724000730
- From bin packing to masonry wall construction: https://experts.umn.edu/en/publications/from-bin-packing-to-masonry-wall-construction/
- Geometric indices to quantify texture irregularity of stone masonry (LMT, MQI): https://www.sciencedirect.com/science/article/abs/pii/S0950061816300988
- Centroidal power diagrams and Lloyd's algorithm (Bourne and Roper): https://cvgmt.sns.it/media/doc/paper/2517/BourneRoper.pdf
- Lloyd's relaxation (interactive): https://www.jasondavies.com/lloyd/
- DSWA, what is a dry stone wall: https://www.dswa.org.uk/wp-content/uploads/2018/07/What-is-a-dry-stone-wall.pdf
- The Stone Trust, how to build walls: https://thestonetrust.org/resource-information/how-to/
- Dry stone walling glossary: https://conservationhandbooks.com/dry-stone-walling-introduction/glossary/
- MLIT, Castle craftsmanship: stone walls: https://www.mlit.go.jp/tagengo-db/en/R1-00697.html
- Jcastle, stone walls: https://jcastle.info/view/Stone_walls
- Texel density 5.12 / 10.24 and Megascans 8k Nanite maps (polycount): https://polycount.com/discussion/227863/texel-density-5-12-10-24
- Modular kit variation with few sculpted stones: https://www.exp-points.com/vuk-single-material-modular-kit-environment-ue4
- Trim sheets and atlases: https://3dtexel.com/trim-sheets-texture-atlases-the-game-environment-workflow/
- Procedural moss / snow on rocks in Unreal: https://www.michaelarby.com/post/tutorial-unreal-procedural-moss-snow-on-rocks
- Texture Color tool, mesh painting on Nanite (UE 5.5): https://dev.epicgames.com/community/learning/tutorials/JZxm/texture-color-tool-in-unreal-engine-5-5-mesh-painting-on-nanite-meshes-deep-dive
- Nanite Assemblies in UE 5.7: https://liamwedge.artstation.com/blog/mpygZ/nanite-assemblies-in-unreal-engine-5-7-from-dcc-to-ue-import
- Far Cry 5 procedural world generation (cliff rocks), GDC 2018: https://www.gdcvault.com/play/1025557/Procedural-World-Generation-of-Far

Note: developer.blender.org and docs.blender.org returned HTTP 403 to the fetch tool. Their content is cited from
search snippets and confirmed by the in-Blender probes where marked [VERIFIED 5.2].
