# Study C: building trees in Blender 5.2 with Python, headless (and getting them into UE 5.8 through our pipeline)

**Written:** 2026-09-29, research phase only (web + local files + read-only API probes in a throwaway headless Blender;
no project file, Unreal project or asset was opened or changed). **Companions:** `A_craft.md` (the craft: anatomy,
silhouette, foliage, bark, failure modes) and `B_unreal.md` (the engine side). This file is the **Blender and pipeline
how-to**. It serves every future tree or vegetation build. The first client is the four niwaki black pines
(`References/Dojo/dojo_japanese_pine_ref.png`) for the sunset mountain dojo (`References/Dojo/dojo_landscape_ref.png`).

Tags: **[VERIFIED 5.2]** means probed in Blender 5.2.0 LTS on this PC today. **[VERIFIED 5.8 SRC]** means read in the
installed UE 5.8 engine source or plugin files. **[UNCERTAIN]** means not tested; read section 13.

---

## 0. The short version

1. **Write our own spec-driven generator in plain Python (bmesh / numpy),** in the house builder style
   (`Scripts/dojo/props/stone/build_stone_props.py`, `Scripts/dojo/roof/roof_kit.py`). Geometry Nodes, Sapling, MTree
   and space-colonisation add-ons are useful as idea sources or spikes, but none should be a runtime dependency (see 2).
2. **The skeleton is traced, not grown.** Build the trunk and scaffold limbs as polylines traced from the reference
   panel, which is the 2D outline authority (the CLAUDE.md lesson). Build the pad envelopes the same way. Procedural
   growth (space colonisation) only fills the twigs *inside* each traced pad envelope.
3. **Mesh branches as per-branch tubes** with our own ring/UV code: continuous U around, V along the arc length, the
   seam on the hidden side, and an integer U-tile count per branch. Hide junctions with a flared collar that sinks
   into the parent. Use an SDF weld (new 5.x grid nodes) only as a spike for the trunk base (nebari) and the big
   limb forks.
4. **Needles are real geometry** (2-needle fascicles in tufts, instanced per shoot tip, realized for export). A needle
   atlas on cutout cards is baked from the same tuft as the fallback / far LOD (section 7). Epic's Nanite Foliage
   guidance steers away from alpha masking.
5. **Wind:** always write the branch hierarchy as data (bones / pivots) even if v1 ships static. v1 is a static
   Nanite mesh with pivots and weights in UV2/UV3 and one vertex-colour set for a WPO material. v2, if wanted, is a
   skeletal mesh for the Dynamic Wind plugin, built from the same hierarchy. UE 5.8 limits apply: Nanite takes max
   4 UV sets [VERIFIED 5.8 SRC], and UE imports one vertex-colour set.
6. **Export through `Scripts/pipeline/` unchanged.** Use a documented waiver list for foliage (UV0 overlap on the
   needle atlas, the triangle budget under Nanite), as the dojo kits already do. Collision is trunk-only UCX hulls.
7. **Gate with measurements plus a blind judge:** height, crown width, crown base, lean, tier/pad count, gap
   fraction, silhouette IoU against the traced panel, all at the sheet's human-figure scale. The measuring method
   and a first pass on the owner's sheet are in section 11.

---

## 1. What the repo already fixes for us (conventions a tree build must follow)

Read in `Scripts/pipeline/*.py` docstrings, `ASSET_GUIDELINES.md` sections 1-6 and 9, the dojo builders and
`WorkFiles/dojo/DOJO_QUEUE.md`:

| Topic | House rule | Consequence for trees |
|---|---|---|
| Builder shape | One `build_<kit>.py` (+ `<kit>_geo.py` lib) run headless: `blender -b --factory-startup --python build.py -- [--no-export]`. It writes `Assets/Dojo/<Kit>.blend`, `Exports/DojoKit/<Kit>/SM_*.fbx`, `WorkFiles/dojo/build/<kit>/{layout_*.json, measure.json, qa_report.json, export_report.json}`. A `run_all.sh` chains textures → build → render → compose side-by-sides (`Scripts/dojo/props/stone/run_all.sh`) | The pine generator lives in `Scripts/dojo/pines/` (already created and locked by the pines chat, lock `WorkFiles/locks/dojopines.json`; **not ours to edit**). A reusable generic core belongs in a neutral place later (e.g. `Scripts/vegetation/`), imported by per-species builders |
| Units / pivots | Metres, Z up, transforms applied, pivot at the floor contact; front faces -Y | Pivot = trunk base centre at ground level; "front" = the side the reference shows |
| Export | Only `pipeline.export_fbx.export_fbx(path, objects, kind=...)`: FBX units scale, -Y forward / Z up, face smoothing, triangulated, `colors_type="SRGB"`, no tangents, **`use_mesh_modifiers=True`** (a GN modifier is evaluated at export) | A GN-built tree could export without applying, but apply/realize anyway so `qa_check` sees what ships |
| QA | `qa_check(objects, budget_tris, texel_density, require_uv1, ...)` is read-only JSON. Dojo builders pass a **waive set** (`{"uv0_tile_range", "uv_no_overlap"}` in `build_kit1.py`, `build_corridors.py`) | Foliage legitimately overlaps UV0 (atlas / shared needle UVs). Waive `uv_no_overlap` **for the foliage object only**, keep it for bark, and write the waiver in the report |
| Collision | `UCX_<render node name>_NN`, convex, child of the mesh; with LODs `UCX_<base>_LOD0_NN` (`helpers.make_ucx_hull`) | Trunk-only: 2-4 convex hulls up the trunk (a leaning S-trunk is not convex). No canopy collision (climb routes, DOJO_QUEUE cherry note) |
| LOD / Nanite | Dojo decision 2026-10-02: Nanite for props over ~2k tris; the 5k budget is waived for Nanite pieces | Trees are Nanite: no hand LODs for the trunk, one card fallback for the foliage at most |
| Textures | BaseColor sRGB, ORM linear (R = **baked** AO), Normal DirectX (green flipped on write, `textures.flip_normal_green`), power-of-two, `load_data_image` for Non-Color, bake margin type **EXTEND** | The bark and needle-atlas bakes use `pipeline/textures.py`; ORM.R is a real AO bake |
| UV1 | Every static mesh ships a lightmap UV1 inside 0-1, non-overlapping (Fab) | Keep UV1 even under Nanite (Fab rule). That leaves **UV2 and UV3** for wind data: Nanite supports only 4 UV sets (`NANITE_MAX_UVS 4`, `Engine/Shaders/Shared/NaniteDefinitions.h`) [VERIFIED 5.8 SRC] |
| Skeletal | `pipeline/skeletal_prop.py`: armature object named `root`, deform bones only, `qa_skeletal`, `export_skeletal_set`, `<name>.skeletal.json` sidecar with physics bodies in UE space | The route for a Dynamic Wind v2 (section 8.3): bones per branch chain, rigid weights, physics bodies on the trunk bones |
| Locks | `py Scripts/pipeline/lock.py claim <Asset> --agent claude --blend ...`; `assert_owner` before opening a .blend | One lock per tree asset set |

---

## 2. Skeleton generation: the options and their trade-offs

| Option | Headless / scriptable | Strengths | Weaknesses for us | Verdict |
|---|---|---|---|---|
| **Own Python (bmesh + numpy + mathutils)** | Fully; the house style | Total control: spec in JSON, deterministic seeds, our own UVs and seams, per-vertex wind data, easy to measure. Matches every dojo builder | We write the maths (tube rings, parallel transport frames, UVs) | **Recommended core** |
| **Geometry Nodes built from Python** | Yes: a node group can be created and evaluated headless (`bpy.data.node_groups.new(..., "GeometryNodeTree")`, then `bpy.data.meshes.new_from_object(ob.evaluated_get(depsgraph))`) [VERIFIED 5.2] | Fast instancing (`Instance on Points` → `Realize Instances`), fields, Repeat and For-Each zones for recursion [VERIFIED 5.2 node types], `Curve to Mesh` with a **Scale** input | Wiring big graphs in Python is verbose and brittle across versions. **Since 4.5, Curve to Mesh no longer applies curve radius automatically: plug Radius into Scale** [Blender Studio]. No UV output; a naive UV wraps across the seam (section 5.2) [VERIFIED 5.2]. Harder to debug than Python | Use GN for **instancing** tufts on shoot tips if it's faster, and for SDF experiments. Not for the skeleton logic |
| **Sapling Tree Gen** (extension 0.3.7, GPL-3; a fork 0.4.0 claims 5.2.2) | Operator `bpy.ops.curve.tree_add(...)` in principle | Weber-Penn parametric model, presets | Not bundled since 4.2 (extension install needed on a factory-startup Blender). Reviews report 5.2.x breakage. Parametric trees fight a traced silhouette; there is no niwaki pad logic | Reference only |
| **Modular Tree / MTree** (GoodPie fork 5.5.2, Blender 4.3.1+, GPL addon / MIT core, compiled binaries) | Node-editor driven; scripting its node tree is possible but undocumented [UNCERTAIN] | L-system growth, gravity, crown envelopes, **Pivot Painter 2.0 export for UE5** | A compiled native dependency. Its own node system. Silhouette control is indirect | Worth one spike to compare its PP2 export against ours; not a dependency |
| **Space colonisation** (Runions et al. 2007; extension "Space colonization tree generator" 1.0.0, GPL, grows curves into a mesh volume) | The algorithm is ~150 lines of numpy; no add-on needed | Fills a **given envelope** with natural branching: exactly a niwaki pad | "Vascular" look without tropism/pruning; weak for the trunk line itself | **Recommended for twigs inside each traced pad envelope** |
| **L-system** | Pure Python | Compact ratio control (Honda/ABOP) | Hard to art-direct the silhouette | Optional for secondary ramification |

Output from a GPL add-on (a generated mesh) is not itself GPL. The reason to avoid these add-ons is headless
reproducibility (`--factory-startup` loads no extensions) and control, not licence.

**Recommended skeleton data model** (JSON, so the generator, wind export, measurements and judge all read the same
thing):

```
tree = {
  "id": "SM_DKN_Pine_A", "seed": 7, "height_m": 3.4, "lean_deg": -6,
  "nodes":   [{"id": 0, "p": [x,y,z], "r": 0.16, "parent": -1, "order": 0}, ...],   # polyline points with radius
  "branches":[{"id": 0, "nodes": [0,1,2,...], "order": 0, "parent_branch": -1, "parent_t": 0.0}, ...],
  "pads":    [{"id": 0, "branch": 5, "envelope": {"centre": [...], "rx":0.6,"ry":0.5,"rz_top":0.25,"rz_bot":0.06},
               "tips": [[x,y,z,dir...], ...]}]
}
```

- **Order 0/1 (trunk, scaffold limbs):** traced polylines from the panel (x,z from the front view; y from a second
  view or an authored depth curve), resampled with Catmull-Rom. Radius comes from the pipe model:
  `r_parent^n = Σ r_child^n`, with n ≈ 2-2.5 (A_craft 1.2).
- **Order 2+ (inside pads):** space colonisation seeded from the limb end with attraction points sampled in the pad
  envelope. The envelope is a half-ellipsoid, domed on top and **flat underneath** (the niwaki pad shape [niwaki/RHS
  refs]). Kill distance ≈ 3-4 cm, influence radius ≈ 20-30 cm, segment length ≈ 3 cm, plus a small upward tropism.
  Prune any shoot whose tip leaves the envelope.
- **Frames:** use parallel-transport (rotation-minimising) frames along each polyline, not Frenet. Frenet flips at
  inflection points, and an S-curved trunk has several. The frame also fixes where the UV seam goes (section 5).

---

## 3. Branch meshing and junctions

### 3.1 Tubes (recommended default)
- **Rings:** each branch is a sweep of rings along its resampled polyline. Ring vertex count comes from the radius
  (screen-driven): trunk 16-24, limbs 10-12, twigs 5-6, the last twig 3-4 (triangle cap). Rings sit every
  `~1.2 × radius` along the length, closer on bends (angle threshold ≈ 8°).
- **Taper:** linear in radius along the branch plus the pipe-model drop at each child.
- **Irregularity is geometry, not noise:** a low-frequency radial displacement (2-4 lobes on the trunk, with
  fissure grooves) and real bark-plate relief on the trunk (A_craft "plates as geometry"). Keep it to **crisp
  bevels, real forms**. The height-field-only approach failed on ornate items (CLAUDE.md); a normal map adds the
  fine plates on top.
- **Junction without welding:** the child tube starts **inside** the parent (sink its first ring to ~60% of the
  parent radius along the child direction) and flares at the root (radius × 1.3-1.5 over the first 1-1.5 child
  diameters). That is a branch collar, which real pines have. It hides the intersection line from every normal
  view. This is SpeedTree's default (intersecting, not welded, branches); its "seam blending" softens the texture
  across the join. We get the same with a vertex-colour or UV2 blend weight (section 8.1).
- **Topology:** quads until the export triangulates. No n-gons (the tip caps are triangle fans). Closed tubes are
  manifold. Intersecting tubes are fine for `qa_check` (it tests manifoldness per edge, not self-intersection).

### 3.2 Skin modifier
`SKIN` is present in 5.2 [VERIFIED 5.2]. Build a vertex+edge stick skeleton, set
`mesh.skin_vertices[0].data[i].radius`, mark a root, and apply (house memory: works headless; used for the ninja
body). It gives welded quad junctions for free.
- **Minuses:** bulges and twists at nodes with 3+ edges; no UVs (you'd need an unwrap, and continuous bark U
  becomes hard); radius steps show as kinks; no control of seam placement.
- **Use:** trunk + first-order limbs of a small shrub where the junctions matter more than the bark UVs. Not for
  hero trunks.

### 3.3 SDF / voxel weld (new in 5.x)
5.2 has these grid nodes [VERIFIED 5.2]:
- `Mesh to SDF Grid` (Voxel Size, Band Width);
- `SDF Grid Boolean` (union);
- `SDF Grid Fillet` (Iterations);
- `SDF Grid Offset`, `SDF Grid Laplacian`, `SDF Grid Mean`/`Median`;
- `Grid to Mesh` (Threshold, Adaptivity);
- also the older `Mesh to Volume` / `Volume to Mesh` and the Remesh modifier (voxel).

The recipe: union the trunk and limb tubes, fillet the junctions, meshed back as one smooth welded surface.
- **Pluses:** true organic junctions, nebari (root flare) blends.
- **Minuses:** dense triangle soup that needs decimation. All UVs are lost: re-project them from the source tubes
  with a Data Transfer (face-corner UV, nearest face interpolated), which smears at the junctions [UNCERTAIN 5.2
  quality], or use triplanar bark in UE (the house already uses triplanar granite on round stone). The voxel size
  must be ≤ ~5 mm to keep the plate detail.
- **Use:** **spike only**, for the trunk base / nebari and the 2-3 main forks, fused with the tube mesh behind the
  collar. Change method if it doesn't converge.

### 3.4 Metaballs
Obsolete for this. Poor control, poor topology, no UVs.

---

## 4. Needles, tufts and pads (conifer-specific)

**Botany (the numbers the geometry must hit):**
- *Pinus thunbergii* needles grow **2 per fascicle**, **7-12 cm long, 0.7-1.2 mm wide**. They are stiff, finely
  pointed, often twisted, and persist 3-4 years (conifers.org / NCSU).
- The bark is **black-grey, furrowed, plated** on the trunk and grey-brown on young branches.
- Candles (new shoots) are pale buds at the tips.
- Niwaki upkeep:
  - **momiage** strips old needles, leaving about **7-8 needle pairs** per tip;
  - **midoritsumi** pinches the candles;
  - so each tip is a sparse, radiating brush on a bare twig;
  - pads are **half-round clouds with a flat bottom**;
  - from below you see the twig structure (niwaki.com, japanesegardens.jp, RHS).
- The reference close-ups show exactly this: radiating brushes with visible twigs between them.

**Tuft asset (modelled once, 3-5 variants):**
- Twig tip, plus a candle (a small tapered cone, 6-10 tris), plus 12-30 fascicles on a short spiral (phyllotaxis
  137.5°).
- Each needle is a **2-4 triangle strip** (a thin quad with one twist split), 7-12 cm long, 1 mm wide, splaying
  30-70° from the twig axis.
- Give it a slight droop, plus a random length jitter of ±15%.
- **≈ 60-120 triangles per tuft.**
- **Per tree:** 5-7 pads × 60-150 tufts × ~100 tris ≈ **30k-100k foliage triangles**, plus bark 20-60k. That is
  trivial for Nanite, but too heavy for a non-Nanite fallback, hence the card LOD in section 7.
- **Placement:** instance tufts on the pad's twig tips (the space-colonisation leaves), oriented along the tip
  direction with a small upward bias.
  - Instance in Python by writing the transformed vertices into one bmesh (deterministic). Or use GN `Instance on
    Points` → `Realize Instances` [VERIFIED 5.2].
  - Keep a per-tuft id in an attribute: it becomes the wind pivot and the random phase (section 8).
- **Normals:**
  - For shading, bend the needle normals towards the **pad sphere normal** (a Data Transfer from a proxy
    ellipsoid, or computed directly: `n = normalize(lerp(n_geo, (p - pad_centre)/|p - pad_centre|, 0.6))`).
  - This is the standard foliage "volume normal" trick; it keeps pads reading as soft clouds under grazing sunset
    light (A_craft 4.3).
  - FBX carries custom normals if the mesh has them (`mesh_smooth_type="FACE"` still writes custom split normals
    [UNCERTAIN: verify in the export]).
  - The UE import must use Import Normals (the house legacy setting already does).

---

## 5. Bark UVs along branches

### 5.1 The rule set (Python tube generator)
- **U around the circumference:**
  - `u = k_b * (ring_vertex_index / ring_count)`, where `k_b` = the **integer** tile count for branch *b*:
    `k_b = max(1, round(2π r_start / tile_width_m))`;
  - U is 0..k across the ring;
  - duplicate the seam column in UV only (split the UV at the seam loop, keep the vertices shared). U is then
    continuous around the tube and repeats k times with no stretch at the seam;
  - hold `k_b` constant along one branch (texel density drifts with taper, which is acceptable);
  - change k only where a child branch starts.
- **V along the length:**
  - `v = v_offset + arclength / tile_height_m`;
  - `v_offset` for a child = V at its parent attachment point, so bark patterns don't restart visibly at forks;
  - the V range is unbounded, so bark must be a **tiling** texture in V.
  - House tile range: UV0 is graded against -1..2 (`--tile-range`). Long branches exceed it, so waive
    `uv0_tile_range` for bark (the dojo kits already do) or wrap V per branch by an integer.
- **Seam placement:**
  - in the parallel-transport frame, rotate the ring start so the seam lies on the side **least seen from the
    player's camera**;
  - trunk: facing the wall / away from the courtyard view;
  - limbs above eye level: the **top** of the limb (you look up at pads);
  - low limbs: the back.
  - This agrees with the classic advice to put the seam along the tops of branches [3DSkillUp, polycount].
- **Texel density:**
  - house third-person target: **5.12 px/cm**;
  - a 2048 px bark map at 5.12 px/cm covers 4 m, which is far too coarse for the reference's plate size;
  - the practical choice is a 2048 tiling bark at ~0.5 m tile (≈ 40 px/cm) for the trunk, re-used by branches;
  - `qa_check --texel` is optional (None), so omit it for tiling bark and note it in the report.
  - SpeedTree's "fractional U" alternative keeps parent-matched density with a visible seam; our integer-k approach
    is its tiling-safe counterpart (Unity SpeedTree docs).
- **UV1 (lightmap):**
  - a separate `lightmap_pack` / Smart UV Project into 0-1 with margin;
  - the dense r3 footings showed `lightmap_pack` can overlap on 60k-face meshes (`build_kit1.py` note), so gate
    `uv1_no_overlap` with the SAT method and fall back to Smart UV Project.

### 5.2 If Geometry Nodes builds the tubes
- `Curve to Mesh` has no UV output.
- Store a `FLOAT2` attribute on the **CORNER** domain named `UVMap` and it becomes a real UV layer
  [VERIFIED 5.2: evaluated mesh has `uv_layers == ['UVMap']`].
- The naive build (U = the profile circle's spline Factor, V = the main spline Length) **wraps across the seam**:
  14 of 56 faces had a U span > 0.5 in the test [VERIFIED 5.2]. Fix it one of two ways:
  - make the profile non-cyclic with a duplicated end point; or
  - post-process the corners of seam faces (U += 1 where the face spans > 0.5).
- The fiddliness is one more reason to do tubes in Python.

### 5.3 Bark texture source
- One trunk bark set (BC/N/ORM) plus possibly one branch bark.
- Sources, in order:
  1. a CC0 scan (Poly Haven bark; the house already uses CC0 gravel with a note), graded to the reference's
     measured bark values (A_craft 5);
  2. our own procedural bark, **baked to textures on real UVs** (ASSET_GUIDELINES 3: UE can't read Blender
     procedurals).
- Record provenance for Fab.

---

## 6. Materials in Blender (for our renders and judges)
- **Bark:** Principled BSDF with the BC/N/ORM images, used the same way UE will use them.
- **Needles:**
  - Principled BSDF with a small **subsurface** / translucency (in 5.x Principled has Subsurface Weight;
    translucency can also be a Translucent BSDF mixed/added);
  - back-lit needles glow at sunset, which is the look we must match in UE (Two Sided Foliage shading model,
    B_unreal).
  - Keep the Blender material close to what UE's master can do, otherwise the judge scores a Blender-only look.
- **Colour:** A_craft measured the reference needle close-up median sRGB ≈ (80,91,50) *rendered*. Albedo must be
  derived, not copied (a lit render is not albedo).

---

## 7. Baking a needle / tuft atlas in Cycles (fallback cards, far LOD, Fab non-Nanite variant)

**What 5.2 offers:**
- Cycles bake types: `COMBINED, AO, SHADOW, POSITION, NORMAL, UV, ROUGHNESS, EMIT, ENVIRONMENT, DIFFUSE, GLOSSY,
  TRANSMISSION`;
- pass filter `COLOR` etc.; normal space `OBJECT|TANGENT` with per-axis `normal_r/g/b`;
- `use_selected_to_active`, `cage_object`, `cage_extrusion`, `max_ray_distance`;
- `margin_type ADJACENT_FACES|EXTEND`;
- `target IMAGE_TEXTURES|VERTEX_COLORS` [VERIFIED 5.2].
- **There is no alpha/opacity bake type.**

**Two workable methods:**

A. **Selected-to-active bake onto a card (per tuft variant, per card layout)**
- **Albedo:** `DIFFUSE` with only the COLOR pass (no lighting).
- **Normal:** `NORMAL`, tangent space. Either set `normal_g = "NEG_Y"` to write DirectX directly, or bake OpenGL
  and flip with `pipeline/textures.flip_normal_green` (house rule: flip on write, never in UE). Pick one and test
  it: the classic failure is a double flip.
- **Opacity:** bake `EMIT` with the high-poly tuft's material temporarily set to Emission = white. Clear the target
  to black (`use_clear`). Rays that miss the tuft stay black, which gives the coverage mask.
  `max_ray_distance` must be ≈ the tuft half-thickness, so rays don't pick up the neighbouring tufts.
- **Translucency / thickness:** bake the AO node with **Inside** enabled (a thickness proxy), routed through
  Emission. Invert it so thin reads bright.
- **ORM:** AO bake (house rule: real AO, Extend margin); roughness from the material (~0.5-0.6 needles); metal 0.
- Pack Opacity into BaseColor alpha (UE masked). Keep translucency as a separate map, or in ORM alpha if the
  master supports it (B_unreal decides).

B. **Orthographic render passes (simpler for a flat atlas)**
- Lay the tuft variants in a grid under an orthographic camera looking down each card's normal.
- Set `film_transparent=True` [VERIFIED 5.2]; the render alpha is the opacity.
- A Diffuse Color pass gives albedo. The Normal pass (camera space) is converted to tangent space for a card facing
  the camera, which is a fixed matrix.
- Fast and reliable. It is effectively what many foliage-atlas add-ons (e.g. Atlas Bake) automate.

**Atlas rules:**
- Power of two: 2048 is enough for needles.
- Dilate colour and normal into the transparent area (Extend margin, or a dilation pass) so mips don't bleed grey
  halos.
- Keep alpha-coverage-preserving mips for UE (B_unreal).
- Pack the islands as the card mesh will use them.
- The card mesh is a **cutout** that follows the alpha outline (8-12 verts per card, not a quad) to cut overdraw
  (A_craft 4.1).
- **Opacity for alpha test:** check the coverage at mip 2-3 against mip 0 (target ≥ 90%). This is the "pads thin
  out at distance" failure (A_craft F12).

---

## 8. Wind data: three routes, one hierarchy

Whatever ships, the generator writes **`<asset>.wind.json`** with the branch hierarchy:
- node positions;
- the parent of each branch;
- the order/level;
- branch length;
- the tuft → branch mapping.

The routes below are just encodings of it.

### 8.1 Static mesh + WPO material (v1 recommendation; headless end-to-end)
- **Vertex colour (ONE set; UE's FBX import brings only the first set** (UE forums/docs); Blender exports every
  colour attribute, and a round trip kept 2 sets [VERIFIED 5.2], so write exactly one).
  Proposed house convention:
  - R = hierarchy weight (0 trunk → 1 needle tip, smooth along each branch);
  - G = per-pad random phase;
  - B = per-tuft random phase;
  - A = junction blend weight / AO (optional).
- **UV2 / UV3 (Nanite allows UV0..UV3):**
  - UV2 = the pivot of the vertex's pad branch (x, y), UV3 = (z, pad branch length), or one of them for the tuft
    pivot;
  - positions in **Unreal space centimetres**: x_ue = 100·x, y_ue = −100·y, z_ue = 100·z;
  - the Y flip is the same one `skeletal_prop.ue_component_transform` applies; verify with a one-vertex test mesh
    in UE [UNCERTAIN until measured];
  - a round trip kept 4 UV layers through FBX [VERIFIED 5.2].
- The UE master material (B_unreal) sways each pad about its pivot with falloff by R, and flutters tufts by B.
  WPO on Nanite costs extra and needs a "max WPO displacement" bound (B_unreal).

### 8.2 Pivot Painter 2 (texture + UV lookup)
- Per element, the PP2 texture stores:
  - RGB: pivot position (16-bit);
  - A: parent index as float (or hierarchy depth, random, extents);
  - a second texture holds the X-axis vector + extent.
- One UV channel points each element at its pixel. Import settings: **no mips, no sRGB, Nearest filter, HDR for
  16-bit EXR**. The hierarchy supports up to **4 levels deep and 30,000 elements** (Epic PP2 docs, current for 5.8).
- Blender implementations:
  - lukasreznicek/PivotPainter2;
  - Gvgeo/Pivot-Painter-for-Blender;
  - MTree exports PP2;
  - all of them are easy to reproduce in our own Python: write a float EXR with numpy, set UV2 to pixel centres.
- **Why it matters in 5.8:** the Dynamic Wind plugin has
  `UDynamicWindBlueprintLibrary::ConvertPivotPainterTreeToSkeletalMesh(StaticMesh, PivotPosTexture, PivotUVIndex,
  SkeletalMesh, Skeleton)` [VERIFIED 5.8 SRC, `Plugins/Experimental/DynamicWind/Source/DynamicWindEditor`]. It:
  - reads the PP2 position/parent texture, decoding the alpha parent index from half-float bits minus 1024;
  - builds bones named **`Root`, `Trunk_N`, `Branch_N`, `Leaf_N`**;
  - rigid-skins by the pivot UV;
  - copies the Nanite settings and materials.
- **So a PP2-encoded static tree is also the input to a skeletal Dynamic Wind tree.** That makes PP2 the most
  future-proof static encoding. A UV that is out of 0-1 binds to the root.

### 8.3 Skeletal mesh + Dynamic Wind (v2 option; UE 5.7+ Nanite Foliage path)
- **What the engine wants** [VERIFIED 5.8 SRC]:
  - a skeletal mesh with a `UDynamicWindSkeletalData` asset-user-data;
  - joints mapped to **simulation groups**, each with `Influence` (or dual Min/Max), `ShiftTop` and
    `bIsTrunkGroup`;
  - `bIsGroundCover` and `GustAttenuation`;
  - the engine derives bone chains itself (consecutive bones in the same group form a chain).
- The **JSON format** is exactly `FDynamicWindSkeletalImportData`:

  ```json
  {"Joints": [{"JointName": "Trunk_0", "SimulationGroupIndex": 0}, ...],
   "SimulationGroups": [{"bUseDualInfluence": false, "Influence": 0.2, "MinInfluence": 0, "MaxInfluence": 0,
                         "ShiftTop": 0, "bIsTrunkGroup": true}, ...],
   "bIsGroundCover": false, "GustAttenuation": 0.0}
  ```

  Epic ships `Resources/PythonExamples/export_dynamic_wind_json.py` (USD schema `DynamicWindSkeletonAPI` → JSON).
  The community tool obilang/UE_NaniteDynamicWindData builds it from SpeedTree XML.
- **Blender side:**
  - an armature object named `root` (house skeletal convention);
  - one bone chain per branch down to pad level, not per tuft: a niwaki needs ~60-200 bones;
  - rigid 1-bone weights on each branch's geometry and on its pads/tufts;
  - export via `skeletal_prop.export_skeletal_set`;
  - write the wind JSON beside the FBX: group 0 = trunk, 1 = scaffold limbs, 2 = pad branches, 3 = twigs.
- **Headless gap:** the only exposed importer, `import_dynamic_wind_skeletal_data_from_file(mesh)`, **opens a file
  dialog** (`FDesktopPlatformModule::OpenFileDialog`) [VERIFIED 5.8 SRC]. It cannot run in our `-run=pythonscript`
  commandlets. The C++ `DynamicWind::ImportSkeletalData` isn't a UFUNCTION, and the chain/lookup fields are
  non-editable `UPROPERTY()`. The options:
  1. one GUI step per mesh by the owner, or by us in an editor session the user OKs;
  2. a tiny editor C++ utility (the project would need a code module; DemoGame_1 has one);
  3. let PVE's exporter create it (PVE calls `ImportSkeletalData` internally), which needs PVE to accept our mesh
     (A_craft's "Import / Extract From Mesh" spike).
  **[UNCERTAIN; all Experimental]**
- **Epic's own status:** "a very tightly integrated framework" with assumptions/contracts; opening it to imported
  DCC foliage is planned, no timeline (Epic staff, forums).
- **Collision changes:** a skeletal mesh has no UCX. It needs a **Physics Asset** (capsules on the Trunk bones:
  `skeletal_prop` already writes physics bodies to its sidecar) or a separate invisible static collision mesh placed
  with the tree. The climb/walk checks must be re-run either way.
- **Evidence the path exists locally:** the owner's Megaplants Ginkgo/Cypress in DemoGame_1 are exactly this. They
  ship `Tree_*_A..D` + `_Skeleton`, `SKM_*_Branch_*` part meshes, `PVE_Preset_*` / `PVE_Tree_*`, and DemoGame_1
  enables the `ProceduralVegetationEditor` plugin (which pulls in `DynamicWind`, `PCG`, `GeometryScripting`,
  `Dataflow`). File names only were inspected; nothing was opened.

**Recommendation:**
- v1 = static Nanite with PP2-compatible pivot data in UV2 + a WPO master (§8.1/8.2). It is fully headless,
  collision stays UCX, and the climb checks stay valid.
- A skeletal Dynamic Wind v2 is a conversion of the same data (§8.2's converter or §8.3's JSON), done only if the
  owner wants Nanite-Foliage wind.

---

## 9. Collision, LOD, budgets for a tree asset
- **Collision:**
  - trunk-only convex hulls from the trunk tube segments: split the trunk polyline into 2-4 nearly-straight runs
    and make one `make_ucx_hull` each (≤ 32 verts);
  - add a limb hull only where gameplay needs it (a climbable limb must be a deliberate spec decision);
  - pads get no collision;
  - on a rock-planted variant, the rock gets its own hulls.
  - Then re-run the dojo walk/climb checks around each placement (the DOJO_QUEUE tree-slot note).
- **Split objects** so each can take its own material and QA profile, all under one asset:
  `SM_<Tree>` (bark: opaque, Nanite) and `SM_<Tree>_Foliage` (needles, possibly masked if cards). Alternatively one
  mesh with two material slots; keep bark and needles as **separate material slots** in any case.
- **Budgets** (house triangle budgets are for non-Nanite): report the tris per object in `measure.json`. Suggested
  soft caps: bark ≤ 80k, needle geometry ≤ 150k per hero tree, card fallback ≤ 15k.
- **Pivot / origin:** trunk base centre at z = 0. Ground mound / moss / rocks as a separate optional piece, so trees
  can sit on the dojo's own ground.

---

## 10. Fit with the repo pipeline (step list for a tree builder)

1. `lock.py claim <TreeSet> --agent claude --blend Assets/<Kit>/<TreeSet>.blend`.
2. `<species>_spec.json`: traced polylines, pad envelopes, radii, seeds, the reference panel id and its measured
   targets (section 11).
3. `build_<species>.py` (headless), in stages that can be judged separately (the kunai "staged build" lesson):
   a. skeleton → a line render against the traced panel (silhouette gate before any meshing);
   b. bark tubes + UVs → a clay render;
   c. tufts/pads → a silhouette + gap-fraction gate;
   d. materials → a colour gate;
   e. wind data + UCX → `qa_check` (waivers: foliage `uv_no_overlap`, bark `uv0_tile_range`; `require_uv1=True`)
      → `export_fbx(kind="static")`;
   f. write `measure.json`, `qa_report.json`, `export_report.json`, `<asset>.wind.json`.
4. Textures: `make_<species>_textures.py` (bark grade, needle atlas bake) using `pipeline/textures.py` (AO bake with
   Extend, ORM pack, DirectX flip, Non-Color reload). Pack into the .blend.
5. `render_<species>.py`: judge renders (section 12). `compose_<species>.py`: side-by-sides.
6. Unreal: a separate, fresh-process import and verify on the exact bytes (house rule, SHA-256 in the report). One
   commandlet at a time.

---

## 11. Measuring a reference sheet's silhouette (method + first pass on the owner's pine sheet)

**Method (pixels, not eyeballing; ASSET_GUIDELINES 9):**
1. **Panel split:** find the row bands (rows with ~0 foreground) and the thin separator lines; record each panel's
   box. Where crowns overlap a neighbour (sheet row 2: the reaching-limb tree spreads behind the straight tall one),
   trace that panel by hand.
2. **Masks:** background = the median of a corner patch (this sheet: sRGB ≈ (183,182,182)); foreground = colour
   distance > 45.
   - Foliage = foreground with G > R+4 and G > B+4.
   - Wood = foreground with R > B+8 and not foliage.
   - Scale figure = neutral grey (max−min < 14) in the figure's column.
3. **Scale:** the sheet's human figure is taken as **1.75 m** (an assumption; the sheet is an AI render, so heights
   are relative until the dojo spec fixes them; **the spec wins on heights**, as in DOJO_QUEUE). Measured figure
   heights: 159 / 157 px (top row), 223 / 234 px (middle row).
4. **Height** = foliage top → the lowest wood/foliage pixel (ground contact of the mound).
   **Crown width** = foliage x-extent above the mound band.
   **Crown base** = the lowest foliage pixel above the mound band. The mound grass is green too: mask the bottom
   ~14% (or the mound by its colour) first, or crown base reads 0.
5. **Lean** = apex x − trunk-base x, where the trunk base is the wood centroid in the 18-30% height band. Also report
   the trunk base angle (a line fit to wood pixels in that band) and the foliage-centroid offset (visual weight
   side).
6. **Tier / pad count** = connected components of the foliage mask after a 5 px closing, at half resolution,
   keeping components ≥ 2% of the foliage area. **Calibrate the closing kernel on one panel against a hand count
   before trusting it.** Also count tiers as peaks of the per-row foliage width profile.
7. **Gap fraction / row fill** = foliage pixels ÷ (the sum of the per-row foliage span) inside the crown. It catches
   the "green blob, no sky holes" failure (A_craft F1).
8. **Silhouette IoU:** render our tree orthographic from the matching view, on the same grey, and scale it so the
   heights match with the trunk bases aligned. IoU of the foliage+wood masks, plus a per-row width-profile error
   (mean |Δw|/w). Also show an XOR heatmap image to the judge-prep step, not to the blind judge.

**First pass on `dojo_japanese_pine_ref.png`**
- Automatic, 2026-09-29. The script was a throwaway in the scratchpad; the core is reproducible from the steps
  above with PIL + numpy only (no scipy/cv2 on this PC's Python). Pad counts are **uncalibrated**. The M1 width is
  clipped by the neighbouring panel. M4-M6 heights include the rock:

| Panel (sheet position) | H (m) | Crown W (m) | Lean apex−base (m) | Foliage centroid − base (m) | Pads (auto) | Row fill |
|---|---|---|---|---|---|---|
| T1 top-left, twin-curve low | 2.20 | 2.20 | +0.32 | +0.16 | 5 | 0.30 |
| T2 narrow tiered | 2.38 | 1.31 | −0.11 | −0.16 | 4 | 0.38 |
| T3 wide low | 2.38 | 2.56 | −0.59 | −0.44 | 5 | 0.25 |
| T4 tall S-curve | 3.47 | 2.65 | −0.31 | −0.25 | 6 | 0.31 |
| T5 slender column | 3.36 | 1.81 | −0.17 | −0.18 | 7 | 0.37 |
| T6 tall S, wide | 3.32 | 2.44 | +0.66 | +0.22 | 6 | 0.29 |
| M1 reaching limb (width clipped; ≈ 3.9 m by hand, x 12-515 px) | 2.87 | ≥3.21 | −0.85 | −1.39 | 5 | 0.28 |
| M2 straight tall | 2.78 | 1.13 | +0.11 | +0.09 | 7 | 0.33 |
| M3 leaning | 2.66 | 2.02 | −0.23 | −0.06 | 4 | 0.33 |
| M4 rock-planted (incl. rock) | 2.20 | 1.35 | +0.28 | −0.12 | 2 (merged; recount) | 0.31 |
| M5 rock slender (incl. rock) | 2.19 | 0.87 | −0.03 | −0.05 | 6 | 0.37 |
| M6 rock wide (incl. rock) | 2.34 | 1.53 | +0.42 | −0.11 | 5 | 0.27 |

Reading:
- The sheet's trees are **garden-scale, ~2.2-3.5 m** at a 1.75 m figure (1.3-2x a person).
- Crowns are 0.9-2.7 m wide, apart from the reaching-limb form (~3.9 m).
- Row fill is 0.25-0.38, so **~two-thirds of each crown's row span is sky**: pads are separated, which is the
  signature to preserve.
- Four dojo pines chosen from these twelve panels take their targets from this table (re-measured, calibrated) and
  from the dojo spec's slot sizes.

---

## 12. Render and judge practice for trees
- **Match the sheet's presentation for the silhouette judge:**
  - orthographic (or the sheet's long-lens look), camera at mid-height, the same grey background (183);
  - soft studio light from front-top;
  - the same human-figure silhouette at the same scale beside the tree.
- **Side-by-side pairs:** our render next to the reference panel, same pixel height. Build them with a `compose_*.py`
  like the stone/modern kits'.
- **Blind test (house bar):** the judge sees only image pairs and must not be able to pick the copy on *design*.
  Run it on:
  1. silhouette (flat black masks, no texture);
  2. clay (form, taper, junctions);
  3. final.
  Silhouette first: a failed silhouette makes texture work pointless (A_craft rule 1).
- **Also judge 360°:** 8 views at 45°, looking for card lines, bald backs, hidden seams showing, and junction
  cracks.
- **Also judge at gameplay distance** in UE captures (the dojo judges found UE colour shifts that Blender never
  showed): low sun, back light through the needles, and at 5 / 15 / 40 m.
- **Numbers with every judge round:** section 11 metrics + tris + bones + the texture list.
- If a round fails decisively, stop and show the owner (CLAUDE.md).
- Cycles on the PC GPU for finals. On a cloud VM, EEVEE/Cycles CPU at low samples for silhouette gates only.

---

## 13. Uncertain / to verify before relying on it
- **Blender 5.2:**
  - custom split normals survive our FBX settings (`mesh_smooth_type="FACE"`) and arrive in UE with Import Normals.
    Test with a pad-normal-bent mesh;
  - `normal_g="NEG_Y"` vs the pipeline flip: pick one, test for a double flip;
  - the SDF weld quality and the UV re-projection at junctions (spike);
  - scripting MTree's node trees headless;
  - the Sapling fork on 5.2.
- **FBX/UE:**
  - which colour attribute UE takes when several exist: export exactly one to avoid the question;
  - the pivot axis convention in UV2/UV3 (y flip) needs a one-vertex test;
  - UE's legacy importer must be told not to generate lightmap UVs over our UV1/UV2/UV3 when Nanite (house setting:
    Generate Lightmap UVs OFF for Nanite).
- **UE 5.8, all Experimental:**
  - Dynamic Wind, PVE, Nanite Assemblies, Nanite Foliage voxels;
  - the Nanite Foliage doc's advice against alpha masking and WPO;
  - there is no headless Dynamic Wind import;
  - `ConvertPivotPainterTreeToSkeletalMesh` requires an empty target SkeletalMesh + Skeleton; untested on our data;
  - the forum answer says the framework may change between versions (A_craft: 5.7 PVE assets aren't compatible with
    5.8).
- **Botany numbers** come from web summaries of conifers.org / NCSU (consistent with each other); cross-check before
  hard-coding gates.
- **Reference measurements** are uncalibrated for pads; M1 needs a hand trace; the figure height is an assumption.

---

## Sources
Local (read-only):
- `Scripts/pipeline/{export_fbx,qa_check,helpers,textures,lock,skeletal_prop}.py` docstrings;
- `ASSET_GUIDELINES.md` §1-6, 9;
- `Scripts/dojo/roof/roof_kit.py`, `Scripts/dojo/props/stone/{build_stone_props.py,run_all.sh}`,
  `Scripts/dojo/build_kit1.py` / `corridors/build_corridors.py` (QA waivers);
- `WorkFiles/dojo/DOJO_QUEUE.md`; `WorkFiles/studies/trees/A_craft.md`;
- UE 5.8 engine files:
  - `Engine/Plugins/Experimental/DynamicWind/` (uplugin, `DynamicWindSkeletalData.h`, `DynamicWindImportData.h/.cpp`,
    `DynamicWindBlueprintLibrary.h/.cpp`, `Resources/PythonExamples/export_dynamic_wind_json.py`);
  - `Engine/Plugins/Experimental/ProceduralVegetationEditor/` (uplugin, `PVWindSettings.h`, `PVExportHelper.cpp`);
  - `Engine/Shaders/Shared/NaniteDefinitions.h` (`NANITE_MAX_UVS 4`);
  - `Engine/Source/Runtime/Engine/Public/Components.h` (`MAX_STATIC_TEXCOORDS = 8`);
- DemoGame_1 `DemoGame_1.uproject` plugin list and `Content/Megaplant_Library` file names only.
- Blender 5.2.0 LTS API probes (node sockets, bake enums, FBX options, a UV/colour FBX round trip), run in a
  throwaway factory-startup session.

Web:
- Epic, Nanite Foliage (UE 5.8): https://dev.epicgames.com/documentation/unreal-engine/nanite-foliage
- Epic, Nanite Assemblies: https://dev.epicgames.com/documentation/unreal-engine/nanite-assemblies
- Epic, Pivot Painter Tool 2.0: https://dev.epicgames.com/documentation/en-us/unreal-engine/pivot-painter-tool-2.0-in-unreal-engine
- Epic forums, Dynamic Wind system questions (Epic staff reply): https://forums.unrealengine.com/t/dynamic-wind-system-questions/2698278
- obilang/UE_NaniteDynamicWindData (JSON format, import script): https://github.com/obilang/UE_NaniteDynamicWindData
- UE FBX static mesh pipeline (one vertex-colour set): https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine ; forum: https://forums.unrealengine.com/t/is-there-a-way-to-import-multiple-vertex-color-sets/291637
- Blender Studio, GN from Scratch, Tree Generator (Curve to Mesh radius → Scale since 4.5): https://studio.blender.org/training/geometry-nodes-from-scratch/example-tree-generator/
- IRCSS, Trees with Geometry Nodes: https://github.com/IRCSS/Trees-With-Geometry-Nodes-Blender
- Blender 5.0 / 5.2 GN release notes (SDF grid nodes, bundles/closures): https://developer.blender.org/docs/release_notes/5.0/geometry_nodes/ , https://developer.blender.org/docs/release_notes/5.2/geometry_nodes/ (pages 403 to the fetcher; node names verified by probe instead); https://code.blender.org/2025/10/geometry-nodes-workshop-september-2025/
- Sapling Tree Gen extension: https://extensions.blender.org/add-ons/sapling-tree-gen/ ; 5.2 fork: https://github.com/meet-brad-ch/add_curve_sapling/releases/tag/v0.4.0
- Modular Tree (MTree) extension, PP2 export: https://extensions.blender.org/add-ons/modular-tree/ ; https://github.com/MaximeHerpin/modular_tree
- Space colonisation: Runions, Lane, Prusinkiewicz 2007 https://algorithmicbotany.org/papers/colonization.egwnp2007.large.pdf ; extension https://extensions.blender.org/add-ons/space-colonization-tree-generator/
- Pivot Painter for Blender: https://github.com/lukasreznicek/PivotPainter2 , https://github.com/Gvgeo/Pivot-Painter-for-Blender
- SpeedTree texel density / fractional U: https://docs.unity3d.com/speedtree-modeler/manual/texel-density-solutions.html
- Bark UV seam placement: https://3dskillup.art/tree-bark-textures-blender-uv-workflow/ ; https://polycount.com/discussion/74330/real-quick-tree-texturing-question
- Foliage atlas baking: https://johndelta.github.io/atlas_bake_documentation/ ; https://blenderartists.org/t/baking-vegetation-models-to-plane-texture-atlas/1419574
- Pinus thunbergii: https://www.conifers.org/pi/Pinus_thunbergii.php ; https://plants.ces.ncsu.edu/plants/pinus-thunbergii/
- Niwaki pads / momiage / midoritsumi: https://japanesegardens.jp/2018/06/15/midoritsumi-and-momiage-pruning-pines/ ; https://www.niwaki.com/mid-winter-momiage ; https://www.rhs.org.uk/plants/types/trees/cloud-pruning
