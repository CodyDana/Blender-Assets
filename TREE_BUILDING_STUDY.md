# Tree Building Study

Best practice for building game-ready trees, shrubs and other vegetation in this repo: Blender 5.2 (headless Python)
through `Scripts/pipeline/` into Unreal Engine 5.8, for the ninja game and for Fab.

**Written:** 2026-09-29. **Versions:** Blender 5.2.0 LTS, Unreal Engine 5.8.3 (CL 58210709, read from
`Engine/Build/Build.version`). **Research notes behind it:** `WorkFiles/studies/trees/A_craft.md` (the craft),
`B_unreal.md` (the engine), `C_blender.md` (Blender and the pipeline). Go to those for the long form. This file is
the working rulebook.

**Evidence tags.**
- **[M]** measured on this PC: installed engine source, plugin files, a Blender 5.2 API probe, or a read-only
  listing of the Megaplants files.
- **[D]** primary documentation (Epic, Blender, papers).
- **[S]** secondary (forum, blog, search summary, blocked page).
- **[U5.2] / [U5.8]** not verified on this machine's Blender 5.2 or Unreal 5.8. The full list is in section 9.2.

Numbers in square brackets such as [35] point to the sources in section 9.1.

**Revision history.**
- 2026-09-29: first version.
- 2026-09-30: critic revision. Fixed: Nanite `bSeparable` is a flag, not a Shape Preservation value; source [53] is about
  landscape displacement; bark texel density now follows the house 5.12 / 10.24 px/cm. Added: FBX vertex-colour import
  (Ignore by default, sRGB decode), `bLerpUVs` for the PP2 index, WPO on voxels, a channel map for AO, the qa_check
  changes (UV0 overlap skip, `_sss` data suffix, a point-set UCX helper), needle welding, gameplay collision channels,
  origin and export layout, the SSS map colour space, sub-pixel needle shimmer, the exact PP2 encoding and second
  texture, open-world (battle royale) scale, short recipes for bamboo, hedges and broadleaf seasons, and the Fab
  licence source.
- 2026-09-30: pines fix round f1. Added pitfalls P45-P56: pad construction, shoots, angular limbs, girth, bark
  pattern, boulder, roots, side-view pad matching, colour judging, framing and the triangle share.
- 2026-09-30: pines v2 (rosette method). Added pitfalls P57-P63: dome-surface rosette sites, the spanning-tree twig
  lattice, fan density, limb girth at the pad, the base mound, plated bark and colour against density.
- 2026-09-30: pines fix round v2f. Added pitfalls P64-P71: rosette clumps, top-weighted dome sampling, the rim fringe,
  in-view zig-zag, two-pass limb separation, trunk girth on a rock, root visibility and the mound bed.

---

## 1. Purpose, scope and how to use it

**Read this before any tree, plant or foliage build.** That covers hero trees, shrubs, hedges, topiary, bamboo, and
card or atlas work for plants. It also covers placing pack vegetation, because sections 2 and 5 decide what we build
and how Unreal runs it. The full method is written for trees. Bamboo, clipped hedges and topiary, and broadleaf
seasonal variants get short recipes in 4.15 that reuse the same stages.

**Scope.**
- In scope: custom hero trees built by Claude sessions, how they reach Unreal, and how pack vegetation is chosen and
  set up around them.
- Out of scope: landscapes, rocks, water and FX. Those follow the user's rule that **scenery is sourced by the
  user**, and Claude integrates it (memory `scenery-assets-sourced-by-user`).

**How to use it.**
1. **Section 2** decides whether to build at all. Most vegetation should come from packs.
2. If building, copy the stage list in **section 4** and the gates in **section 6** into the asset's spec before
   writing any geometry.
3. Set up the Unreal side from **section 5**. Start with the route choice in 5.1.
4. Before each judge round, walk through the pitfalls in **section 7**.
5. **Section 8** applies all of this to the first client: the four niwaki black pines from
   `References/Dojo/dojo_japanese_pine_ref.png`, for the sunset mountain dojo
   (`References/Dojo/dojo_landscape_ref.png`).

**The ten rules** (condensed from A_craft section 0):
1. **Structure first, surface last.** A tree reads by its silhouette and its negative space before any texture.
2. **Obey the thickness rule** at every fork (3.2).
3. **Growth is a history.** Show sag, light-seeking, stubs, deadwood and bare old wood.
4. **Asymmetry and irregular spacing.** Never even spacing and never a hedge-trimmer outline.
5. **Sky holes.** Leave gaps through the canopy.
6. **Joints are the tell.** Model the root flare, the branch collars and seamless bark at the forks.
7. **Value and hue, not saturation.** Foliage is dark. Back-light translucency and interior AO sell the volume.
8. **Wind is a hierarchy.** The trunk moves slowest, the branches faster, the needles fastest, each with its own
   phase.
9. **Plan the far view from day one.** Voxels, LODs and alpha coverage decide the 50-500 m look.
10. **Measured numbers plus a blind judge on image pairs** are the gate (CLAUDE.md).

---

## 2. Decision guide: build or buy

### 2.1 Default: buy, and integrate

Scanned packs beat anything procedural we can make for natural, unpruned vegetation. **This is our own measured
lesson:** in every dojo judge round, the procedurally generated natural parts were the weakest pieces. The raked
sand, the sine-wave mountains and the far box town were flagged each time (`WorkFiles/dojo/DOJO_QUEUE.md`, rounds
2-8). Pieces built from reference sheets worked. The user has since said to source scenery rather than generate it
with Python.

| Situation | Choice | How |
|---|---|---|
| Forest, slope cover, background ridges, anything past ~60 m | **Pack** | Megaplants or Scenery_Tutorial firs through PCG or Foliage mode. Nanite Voxelize, no wind past ~60 m (5.9) |
| A common species that a pack has (cypress, ginkgo, cherry, fir, grass, ground cover) | **Pack** | Integrate: copy in, place, collision, material hookup, run the climb check |
| A pack species whose form is close but whose colour is off | **Pack + material instance** | Use the per-instance tint (3.8). Don't rebuild |
| A designed, human-shaped form: niwaki, bonsai, topiary, clipped hedges, espalier | **Custom build** | No growth simulator or scanned pack gives cloud pads. The form is a design, so it follows the reference-sheet method that works for our man-made kits |
| A signature tree with a gameplay role (a climbable limb, a landmark, a tree that is part of a fight arena) | **Custom build** or a heavily edited pack | The collision and the limb geometry are gameplay contracts |
| An asset for sale on Fab | **Custom build** | Pack content cannot be resold as part of our own products: Megascans and Megaplants are sold through Fab [34], and the Fab Standard License forbids distributing licensed content on a standalone basis, except to collaborators on a project [74, S]. Check the licence shown on each listing before relying on this. Everything sold must be our own design (CLAUDE.md IP rule) |
| A stylised tree matching a specific art sheet | **Custom build** | Only if the user supplies the sheet and asks |

**Owned vegetation, as of 2026-09-30:**
- **Megaplants Ginkgo and Japanese Cypress.** Unreal-native. There are copies in
  `DemoGame_1/Content/Megaplant_Library/` and in the launcher `VaultCache/Megaplan*` [M].
- **Megaplants Yoshino Cherry.** To be downloaded; confirm the name and size with the user first.
- **Scenery_Tutorial** firs, bushes and grass.
- **Megaplants are Route B.** They are skeletal Nanite Foliage trees with 300-960 bones, and they need the
  ProceduralVegetationEditor plugin, which pulls in DynamicWind (5.1) [M].
- **They are heavy.** The rule is "a few at the edge, not a forest" (`CINEMATIC_LOOK_RESEARCH.md`).

**Before starting a custom build, confirm all four:**
1. The user asked for it, or agreed to it. Big builds need the user's go (memory `stop-before-expensive-work`).
2. A reference sheet is on disk under `References/<Item>/`.
3. No owned or free pack matches the form.
4. The build has a lock (`Scripts/pipeline/lock.py`).

If the reference sheet is AI-generated (the pine sheet was made with ChatGPT), record that in the asset README for
Fab's AI disclosure (ASSET_GUIDELINES 11).

---

## 3. Principles of believable trees

### 3.1 Anatomy and branch orders
- **Orders.** Trunk (0) → scaffold or primary limbs (1) → secondary (2) → twigs and shoots (3+) → the shoots that
  carry leaves or needles. Plan geometry, wind and LODs per order. Every generator is organised this way
  (SpeedTree, PVE, Weber-Penn) [9][13].
- **Monopodial and sympodial growth.** A monopodial tree (a pine or spruce when young) keeps a straight leader with
  laterals, giving a conical crown. A sympodial tree hands the lead to its laterals, giving a forked, domed crown
  (broadleaves and old pines) [4][5].
- **Honda/ABOP starting ratios** [4]:
  - continuing axis r1 = 0.9;
  - lateral r2 = 0.6-0.9;
  - branch angle 30-45°;
  - divergence 137.5°;
  - one sympodial set: r1 0.9, r2 0.7, a1 10°, a2 60°.
- **Pines grow in yearly whorls.** Each spring a candle extends and sets a ring of 3-6 laterals at its tip.
  Japanese black pine can flush twice a year [18].
  - Needles grow in **pairs** (2-needle fascicles with a grey-white sheath). They are **7-12 cm** long and
    **0.7-1.2 mm** wide, stiff and often twisted [18][19].
  - Needles **persist 3-4 years**, so needles sit only on the outer part of each shoot and the inner wood is bare.
  - Winter buds are white, 1.5-2 cm. The bark is dark grey to purple-grey, plated and fissured on old wood, and
    grey-brown on young branches [19].

### 3.2 Taper and the thickness rule
- **Pipe model / Leonardo's rule:** `r_parent^n = Σ r_child^n`. With n = 2 the cross-section is preserved (da
  Vinci); n = 3 is Murray's law [1][2][5].
  - Real trees and admired tree art sit around **n = 1.5-2.8** [3].
  - Low n gives fast taper and many fine twigs. High n gives chunky limbs.
  - Use it as a statistical target, not an exact law per fork [1].
  - Worked example: a 10 cm parent with 8 cm and 6 cm children gives 8² + 6² = 10², so n = 2.
- **Along one branch the taper is not linear.** It flares at the collar, stays even through the middle, and thins
  sharply at the tip. **Trunks flare at the ground** (root flare, buttress) [8].
- **Build rule, enforced in code:** per fork, n must lie in **1.8-3.0**, and no child may be thicker than its
  parent (gate G7).

### 3.3 Angles and placement
- **Divergence.** Successive laterals rotate about the parent by about 137.5°, so they don't stack [4][73]. Pine
  whorls instead place 3-6 laterals at one node.
- **Angles.** Young laterals leave the parent at 30-60°. Older laterals droop under their own weight.
- **Bonsai and niwaki placement** [20]:
  - branches alternate left, right and back, never as symmetrical pairs;
  - no major branch crosses the trunk seen from the front;
  - the first branch sits at about 1/3 of the height;
  - branch size decreases toward the apex.

### 3.4 Tropisms, competition and age
- **Gravity and weight.** Heavy horizontal limbs sag, then turn up at the tip. This is the S-curve of old pines. In
  ABOP, each segment bends toward a tropism vector, proportional to |H × T| times a susceptibility [4].
- **Light.** Shaded buds die and lit buds grow, so the crown interior is hollow and the foliage faces outward.
  Space colonisation models this as competition for points inside an envelope [5]. Bud-fate models add apical
  control [6][21].
- **Age and damage are the believability layer.** Add dead branches, broken stubs with caps, knots, scars, lean
  and missing limbs [13][14]. "Not adding dead branches is a common pitfall" [14].
- **Bonsai vocabulary** [20]:
  - **nebari**: visible radial surface roots, wider than the trunk and not crossing;
  - **tachiagari**: the trunk's curve from the roots to the first branch;
  - **jin**: a dead, stripped branch;
  - **shari**: a dead, stripped strip of trunk.

### 3.5 Silhouette by distance
| Band | What survives | What to get right |
|---|---|---|
| Far, over ~30 m | outline, value masses, sky holes | Masses in the geometry. The tree must still read at 64 px tall; test by down-sampling [35] |
| Mid, 5-30 m | branch structure through the gaps, pad layering, trunk line | This is where courtyard trees live |
| Close, under 5 m | needle fascicles, bark plates, collars, candles, moss | Scale honesty and junctions |

Rules for every band [14][15]:
- vary cluster sizes and space them unevenly;
- let a few shoots break the outline;
- keep sparse zones and bare branches: "cluster a lot of things together while leaving other parts practically
  barren".

### 3.6 Foliage massing
- **A pad or cluster is a cloud of shoots, not a textured dome.** It is denser at the top and rim, with the
  underside darker and more open.
- **Normals.** Shade clusters as volumes by bending the normals toward a proxy ellipsoid (4.5) [70].
- **Translucency.** Back-lit needles and leaves glow [10][11]. In low-sun scenes this is a **first-order look
  item**, not polish.
- **AO.** Bake interior darkness per vertex or into the texture [10][11]. On instanced foliage a texture can't carry
  it, because every tuft shares the same UVs. Section 4.8 says which channel carries AO on each mesh.
- **Reflectance.** HZD fixes vegetation F0 at 4% dielectric [11]. Needle roughness is about 0.5-0.6.

### 3.7 Bark
- Use **three layers**:
  1. a **unique trunk** for hero trees: geometry plates plus a baked trunk texture;
  2. a **tiling branch bark**;
  3. **overlays** for moss, lichen and wet streaks, by vertex colour or a second UV [31].
- **Deep plates are geometry.** A normal map alone reads flat at silhouettes and in grazing sunset light. This is
  also our house rule: "real forms as real geometry"; height-field relief failed on ornate items.
- **Don't depend on Nanite displacement for bark.** The house rule (real geometry) already decides this. For the record,
  the only 5.8 report found [53, S] is about **landscape** Nanite displacement with tessellation on 5.8 and 5.8.1,
  with no Epic reply. It says nothing about static meshes or about 5.8.3, so it is not evidence either way for bark
  [U5.8].
- **Texel density must match along the grain** from trunk to branches. UVs run along the length. A density jump at
  a fork is a classic tell [28][31].
- **Joints.** SpeedTree welds the child's base ring onto the parent and blends the parent's UVs a short way up the
  child [7]. The real anatomy is the **branch collar**, a swelling at every branch base [8].

### 3.8 Variation
- **Seeds per generator level**, stored in the spec so any variant rebuilds byte for byte [13].
- **Real variation lives in structure:** trunk line, pad or cluster count, which side the reaching limb is on, and
  lean. Tint alone is not variation.
- **Cheap variation on top:**
  - rotation about Z;
  - ±10-15% uniform scale;
  - per-instance hue and value (`PerInstanceRandom`);
  - a per-instance wind phase.
- **Mirroring.** Never mirror a tree with a designed front (niwaki, bonsai) blindly.
- **Build from shared parts.** Megaplants ship 4-7 whole-tree variants per species, all assembled from 5-6 shared
  branch parts [M]. HZD assembles from shared components [11].

### 3.9 Colour and value ranges
- **Albedo (linear), from a widely used chart** [16, S]:
  - conifer forest 0.08-0.12 (sRGB 80-97);
  - summer foliage 0.09-0.12;
  - deciduous 0.15-0.18 (sRGB 118);
  - short grass 0.20-0.25;
  - general PBR practice: nothing below about sRGB 30-50 or above 240.
  - **Cross-check against a primary chart before hard-coding these as gates** [U].
- **Render look vs albedo.** A colour measured on a reference image is a **render look target**, not albedo. The
  pine sheet's needle close-up has median sRGB (80,91,50), hue ~75° (yellow-olive, not blue-green) and saturation
  ~0.45 (A_craft section 7).
- **Art direction from Ghost of Tsushima:** "limiting the variety of foliage, pushing color values, increasing
  translucency levels, and reducing noise on textures" [12]. Readable beats noisy.

---

## 4. The pipeline in this repo

### 4.1 Overview

```
reference sheet ──► measure (6.2) ──► <species>_spec.json  (traced polylines, pad envelopes, seeds, targets)
                                              │
 stage a  skeleton            order 0-1 traced, order 2+ grown inside envelopes ──► line render ──► GATE silhouette
 stage b  bark mesh           tubes + collars + nebari + plate geometry + UV0/UV1 ──► clay render ──► GATE form/taper
 stage c  foliage             instanced tufts/leaf parts on shoot tips, volume normals ──► GATE gaps/pads/IoU
 stage d  textures            bark tiling + unique trunk bake, foliage atlas (for card LOD), ORM with real AO
 stage e  wind data           <asset>.wind.json + vertex colours + UV2 pivots (+ PP2 textures)
 stage f  collision           UCX hulls on trunk (and a rock, if any); none on foliage
 stage g  LOD / Nanite        Nanite trunk (None) + foliage (Voxelize, bLerpUVs off); card LOD chain only for Fab non-Nanite
 stage h  QA + export         qa_check (waivers in the report) ──► export_fbx(kind="static"|"skeletal")
 stage i  Unreal              fresh-process import on the exact bytes ──► captures ──► blind judge + perf numbers
```

- **Build in stages that can be judged separately** (the kunai staged-build lesson). Never mesh a skeleton that
  failed its silhouette gate.
- If a stage fails decisively, **stop and show the user** (CLAUDE.md).

### 4.2 Files, folders and naming

| What | Where | Notes |
|---|---|---|
| Lock | `WorkFiles/locks/<asset>.json` via `py Scripts/pipeline/lock.py claim <TreeSet> --agent claude --blend Assets/<Kit>/<TreeSet>.blend` | One lock per tree set. Never touch another chat's lock or folder |
| Reference + log | `References/<Kit>/<species>_ref.png`, `References/<Kit>/REFERENCE_LOG.md` | Plain git |
| Spec | `Scripts/<kit>/<species>/<species>_spec.json` | Traced polylines, envelopes, seeds, reference panel ids, measured targets |
| Builder | `Scripts/<kit>/<species>/build_<species>.py` (+ `<species>_geo.py`) | Headless: `blender.exe -b --factory-startup --python build_<species>.py -- [--stage a..h] [--no-export]` |
| Textures | `Scripts/<kit>/<species>/make_<species>_textures.py` | Uses `pipeline/textures.py` (AO bake, ORM pack, DirectX flip, Non-Color reload) |
| Render / compose / measure | `render_<species>.py`, `compose_<species>.py`, `measure_<species>.py` | Side-by-sides like the stone and modern kits |
| Chain | `run_all.sh` | textures → build → render → compose (the `Scripts/dojo/props/stone/run_all.sh` pattern) |
| Source blend | `Assets/<Kit>/<TreeSet>.blend` (LFS) | Textures packed |
| Exports | `Exports/<Kit>/<TreeSet>/SM_*.fbx` (one mesh per file), `Textures/T_*`, `<asset>.wind.json`, `README.md` | Also `T_*_PivotPos.exr` + `T_*_XVector.png` if PP2 is used |
| Reports | `WorkFiles/<kit>/build/<species>/{layout_*.json, measure.json, qa_report.json, export_report.json, judge_*.md}` | Heavy scratch (bakes, renders in progress) stays out of git |
| Unreal scripts | the kit's Unreal folder (dojo: `Scripts/dojo/unreal/`) | Materials: dojo → `Scripts/dojo/unreal/dj_materials.py` (owned by the dojo chats); Fab pack → `Scripts/unreal/materials/` under the PackMaterials lock, built only via `run_build.sh` |

**Naming.**
- **Split each tree into two static meshes with a shared origin:**
  - `SM_<Kit><Tree>_Trunk`: bark, opaque. Nanite Shape Preservation **None**. It carries the UCX hulls.
  - `SM_<Kit><Tree>_Foliage`: needles or leaves. Nanite **Voxelize**, `bLerpUVs` off (4.13). No collision.
  - A planted variant's rock is a third mesh, `SM_<Kit><Tree>_Rock`, with its own hulls.
- **Why split:** Shape Preservation is set per mesh (5.2). Voxelize punches holes in trunks [52, S], and a trunk
  with Shape Preservation None is never voxelized, so it can't get voxel holes. The foliage's wind WPO then never
  invalidates the trunk's shadow pages (5.5).
- **One mesh per FBX:** `SM_<Kit><Tree>_Trunk.fbx` (with its `UCX_` children), `SM_<Kit><Tree>_Foliage.fbx`, and
  `SM_<Kit><Tree>_Rock.fbx` if there is one. `export_fbx` requires the `SM_` basename. On the foliage file it warns
  "no UCX_/SOCKET_ helper children were found for this static export". **That warning is expected;** copy it into
  `export_report.json` as expected.
- **Origin and ground contact:**
  - The origin sits at the trunk base: the point where the trunk axis meets the ground, at z = 0, on the Unreal
    import origin. All meshes of one tree share it, so one transform places the tree.
  - The trunk and nebari continue **below z = 0** far enough for sloped placement: depth ≥ root spread radius ×
    tan(max slope). Example: a 0.5 m nebari on a 15° slope needs 0.5 × 0.27 ≈ 0.13 m, so sink 0.2 m. Close the
    buried end with a cap; it is never seen.
  - **Rock-planted trees (Pine D):** the rock, trunk and foliage share one origin, at the rock's ground contact
    centre. The tree base sits on the rock at its authored height, and the rock goes 0.1-0.2 m below grade the same
    way.
- **Textures:** `T_<Kit><Tree>_Bark_BC/_N/_ORM`, `T_<Kit><Tree>_Trunk_BC/_N/_ORM` (the unique trunk bake),
  `T_<Kit><Tree>_Needle_BC/_N/_ORM/_SSS` and, if PP2 is used, `T_<Kit><Tree>_PivotPos` (16-bit EXR) and
  `T_<Kit><Tree>_XVector` (8-bit). `_SSS` is a **linear, single-channel thickness/transmission mask**; the
  subsurface colour is a material parameter (4.8).
- **Deny list:** no franchise or brand strings anywhere. `qa_check` enforces this.

### 4.3 The spec (one JSON that everything reads)

```json
{
  "id": "SM_DKN_PineA1", "species": "pinus_thunbergii", "style": "niwaki",
  "ref": {"sheet": "References/Dojo/dojo_japanese_pine_ref.png", "panel": "T4", "px_per_m": 90.9},
  "seed": 7, "height_m": 3.4, "lean_deg": -6, "front": "-Y",
  "pipe_exponent": [2.0, 2.5],
  "nodes":    [{"id": 0, "p": [0, 0, 0], "r": 0.16, "parent": -1, "order": 0}],
  "branches": [{"id": 0, "nodes": [0, 1, 2], "order": 0, "parent_branch": -1, "parent_t": 0.0, "seed": 11}],
  "pads":     [{"id": 0, "branch": 5, "envelope": {"centre": [0, 0, 2.1], "rx": 0.6, "ry": 0.5,
                "rz_top": 0.25, "rz_bot": 0.06}, "tuft_density": 1.0, "seed": 23}],
  "targets":  {"height_m": 3.47, "crown_w_m": 2.65, "pads": 6, "row_fill": 0.31, "iou_min": 0.80}
}
```

- **Order 0-1 are traced:** x and z from the front panel. y comes from a second view, or from an authored depth
  curve when the sheet has only one view.
- **Order 2+ are grown inside envelopes** (4.4).
- `measure.json`, `wind.json`, the judge prep and the Unreal import all read this same file, so every number is
  traceable to one source.

### 4.4 Stage a: skeleton

- **The skeleton is traced, not grown.** Tracing is our proven 2D outline authority (the paper bomb and the sword
  outlines). Resample the traced polylines with Catmull-Rom.
- **Radii** come from the pipe model, top-down: tip radius set by species (a pine twig is about 3-4 mm), then
  `r_parent = (Σ r_child^n)^(1/n)` with n from the spec. Add the collar flare and the root flare afterwards (4.5).
- **Frames:** use **parallel-transport (rotation-minimising) frames**, never Frenet. Frenet flips at inflection
  points, and an S-trunk has several. The frame also places the UV seam (4.6).
- **Ramification inside each envelope, by space colonisation** [5]. This is about 150 lines of numpy, with no
  add-on.
  - Seed the growth at the limb end.
  - Sample attraction points inside the envelope: a half-ellipsoid, domed on top, **flat underneath** for niwaki
    pads [23].
  - Starting values: segment D ≈ 3 cm; kill distance dk ≈ 3-4 cm; influence radius di ≈ 20-30 cm; N ≈ 300-800
    points per pad. Add a small upward tropism.
  - Prune any shoot whose tip leaves the envelope.
  - Fewer points and a larger dk give sparser, straighter branching [5].
- **L-system (Honda ratios, 3.1)** is an alternative for regular ramification. Weber-Penn / Sapling only suits
  generic background filler (2.1 says buy that instead).
- **Don't** use Sapling, Modular Tree (MTree) or a space-colonisation add-on as a runtime dependency.
  - `--factory-startup` loads no extensions, so the build would not be reproducible headless.
  - Their 5.2 support is unverified [U5.2] [62][66][67].
  - MTree is worth one spike to compare its Pivot Painter 2 export with ours.
- **Output check:** a **line render** (the skeleton as width-scaled strokes, orthographic, on the sheet's grey) next
  to the traced panel. This is gate G1.

### 4.5 Stage b: trunk and branch mesh

- **Tubes in Python (bmesh + numpy) are the default.**
  - **Rings per radius:** trunk 16-24; limbs 10-12; twigs 5-6; last twig 3-4 with a triangle-fan cap.
  - **Ring spacing:** about 1.2 × the radius, closer on bends (angle threshold about 8°).
  - Quads until export (the exporter triangulates). No n-gons. Closed, manifold tubes.
- **Junctions.** Sink the child's first ring about 60% of the parent radius into the parent, along the child
  direction. Flare the child radius × 1.3-1.5 over its first 1-1.5 diameters: this is the **collar**. Intersecting
  tubes pass `qa_check`, which tests manifoldness per edge, not self-intersection.
- **Hide the texture seam at junctions** with a vertex-colour blend weight (4.9), SpeedTree-style [7].
- **Nebari and big forks.** Try an SDF weld in 5.2 Geometry Nodes [M]: `Mesh to SDF Grid` → `SDF Grid Boolean` →
  `SDF Grid Fillet` → `Grid to Mesh`.
  - **Spike only.** It needs voxels of about 5 mm or less, then decimation, and it loses UVs. Re-projecting the UVs
    with Data Transfer may smear [U5.2]; triplanar bark in Unreal is the alternative.
  - If it doesn't converge, model the nebari as swept root tubes instead. Change the method; don't patch.
- **The Skin modifier** gives welded quad junctions but no UVs, and it bulges at 3+ edges. Use it for small shrubs
  only, never hero trunks [M].
- **Bark plates on hero trunks are geometry:**
  - low-frequency lobes (2-4 around the trunk);
  - fissure grooves;
  - crisp plate relief at the reference's scale;
  - a normal map for the fine scale on top.
- **Deadwood and scars** are authored features in the spec, never random noise.

### 4.6 Stage b: UVs

- **UV0, bark (tiling):**
  - **U around:** `u = k_b · i / ring_count`, where `k_b = max(1, round(2π · r_start / tile_width))` is an
    **integer per branch**, constant along it. Split UVs at the seam column only; the vertices stay shared.
  - **V along:** `v = v_offset + arclength / tile_height`. A child starts at its parent's V at the attachment point,
    so bark doesn't restart visibly at forks.
  - **Seam placement,** on the least-seen side in the parallel-transport frame: the trunk's back (toward the wall);
    the **top** of limbs above eye level; the back of low limbs [71].
  - **Density: follow the house numbers** (ASSET_GUIDELINES 4): **5.12 px/cm** for third-person trees, **10.24
    px/cm** only for a trunk that a close-up camera frames. What a camera can resolve is about **12.5 px/cm ÷ the
    distance in metres** at 1440p (2560 px across a 90° horizontal FOV, or 1440 px down a 60° vertical one: one
    pixel covers about 0.4 cm at 5 m). So 5.12 px/cm holds to about 2.5 m and 10.24 to about 1.2 m. More is wasted
    memory and shimmer. Examples: 5.12 px/cm is a 2048 map on a 4 m tile or a 1024 map on a 2 m tile.
  - Pass `--texel` to `qa_check` on the bark mesh like any other asset. Its density is sqrt(UV area ÷ mesh area) ×
    map size, which is valid for tiling UVs.
  - **Thin twigs:** with `k_b ≥ 1`, a twig whose circumference is far below the tile width gets a whole tile around
    it and a huge U density. Where `2πr < tile_width / 2`, let u run over a fraction of the tile (the seam is
    sub-pixel on a twig) and record the per-order density in `measure.json`. The mesh-wide qa_check figure is then
    dominated by the trunk and limbs, which is what the camera sees.
  - **Keep UV0 bounded** with qa_check's own `uv0_tile_range` argument instead of waiving the check: pass
    `(min(0, v_min), max(k_max, v_max))` rounded out to whole tiles, where `k_max` is the largest per-branch k and
    `v_max` the largest V. The default `(-1, 2)` is too tight for long branches.
- **UV0, foliage:** all tufts share the needle UVs (or the atlas UVs on cards), so they overlap by design. qa_check
  can't just waive this: see 4.12, it has to skip the test.
- **UV1 (lightmap):** always ship it, inside 0-1 and non-overlapping (Fab rule), via `lightmap_pack`. On dense
  meshes `lightmap_pack` has overlapped (`build_kit1.py` note). Gate with the SAT method, and fall back to Smart UV
  Project.
- **UV2 and UV3.** **Nanite allows at most 4 UV sets** (`NANITE_MAX_UVS 4`) [M], so there is no UV4. The full
  channel map:

| Channel | Trunk mesh | Foliage mesh |
|---|---|---|
| UV0 | tiling bark (overlapping, bounded) | shared needle or leaf UVs (overlapping) |
| UV1 | lightmap, 0-1, no overlap | lightmap, 0-1, no overlap |
| UV2 | **unique trunk bake** (0-1, no overlap, density-matched): the trunk BC/N/ORM and its AO | PP2 element index (4.9) |
| UV3 | spare | **U = baked canopy AO** (0-1, per vertex); V spare |
| Vertex colour R | junction bark-blend weight | hierarchy weight |
| Vertex colour G | moss/lichen mask | per-pad phase |
| Vertex colour B | per-vertex AO for the tiling branch bark | per-tuft phase |
| Vertex colour A | unused | unused (voxels overwrite it) |

  - If a free-growing tree ever needs PP2 on its trunk, UV2 is taken on the trunk too. Then the unique bake moves to
    UV1 (a clean, well-padded lightmap pack doubles as the bake UV) and the report says so.
- **If Geometry Nodes builds the tubes:**
  - `Curve to Mesh` has no UV output. Write a FLOAT2 **CORNER** attribute named `UVMap`; it becomes a real UV
    layer [M].
  - The naive U wraps across the seam (14 of 56 faces in the probe) [M].
  - Since 4.5, curve radius must be plugged into Scale [63].

### 4.7 Stage c: foliage

- **Model the leaf or needle unit as real geometry and instance it.** Epic's Nanite Foliage guidance: model the
  leaves, avoid alpha masking [35]. It also matches our real-geometry rule.
- **Conifer tuft** (reusable for any pine):
  - a twig tip plus a candle (a tapered cone, 6-10 tris);
  - fascicles on a 137.5° spiral;
  - each needle a 2-4 triangle strip, the species' length (7-12 cm for black pine) and about 1 mm wide, splayed
    30-70° from the twig, with a slight droop and ±15% length jitter;
  - about 40-160 tris per tuft;
  - **3-5 tuft variants.** Randomise roll and scale per instance, or the tiling shows (F14).
  - **No coincident vertices.** qa_check fails `no_coincident_vertices` for separate vertices closer than 1 µm
    (`COINCIDENT_DISTANCE`). The two needles of a fascicle, and all needles on a tuft, must not start at one point
    as separate strips. Either **weld the needle bases** into one shared vertex per fascicle (inside the sheath) or
    start each needle ≥ 0.05 mm from its neighbour, which survives float error after instancing. Check the single
    tuft with qa_check before instancing it (4.12).
  - **Width vs pixels.** A 1 mm needle is about 0.25 px wide at 5 m and 0.08 px at 15 m at 1440p (4.6 maths). See
    5.12 for shimmer.
- **Broadleaf:** a leaf mesh with a midrib fold and 4-12 tris, instanced on the petiole points in spiral or opposite
  phyllotaxis per species.
- **Placement:** on the space-colonisation tips, oriented along the tip direction with a small upward bias.
  - Deterministic Python (write transformed vertices into one bmesh), or GN `Instance on Points` →
    `Realize Instances` [M].
  - Store a per-tuft id attribute. It becomes the wind phase and pivot.
- **Bare inner wood:** needles only on the outer growth segments of each shoot (3-4 years for pines). Keep the
  inner twigs bare.
- **Volume normals.** Blend each vertex normal toward the cluster's proxy-ellipsoid normal:
  `n = normalize(lerp(n_geo, normalize(p − centre), 0.6))`.
  - Write the result as custom split normals, computed directly in Python, or with a Data Transfer from an
    ellipsoid [70] [U5.2 modifier behaviour].
  - Whether the FBX keeps custom normals with `mesh_smooth_type="FACE"` needs a test [U5.2]. Unreal must import
    with Import Normals (the house setting).
- **Card fallback, from the same tuft** (4.8 stage d). Use it only for a Fab non-Nanite LOD chain, or for a far LOD
  where voxels aren't available.

### 4.8 Stage d: textures

- **Bark:**
  - one tiling bark set (BC/N/ORM, 2048) for the branches;
  - for a hero trunk, one **unique trunk bake** from the plate geometry, on the trunk's **UV2** (4.6 channel map);
  - both graded to the reference's measured bark values.
  - The material blends them: the trunk samples `T_*_Trunk_*` through TexCoord[2] and the tiling `T_*_Bark_*`
    through TexCoord[0], mixed by vertex colour R (the junction blend) so limbs fade from the unique bake into the
    tiling bark.
  - **Source order:** (1) a CC0 scan (e.g. Poly Haven bark), graded, with provenance recorded for Fab; (2) our own
    procedural bark **baked onto real UVs**. Unreal can't read Blender procedurals (ASSET_GUIDELINES 3).
  - ORM.R is a real AO bake (`pipeline/textures.bake_ao`, margin EXTEND). **`bake_ao` bakes onto the active UV
    map**, so make UV2 active for the unique trunk bake and restore UV0 afterwards. Never bake AO onto the tiling
    UV0: it overlaps, so the bake would be a mix of every branch.
  - The tiling branch bark's ORM.R is the tile's own small-scale AO only. Branch-scale darkness (inside the crown,
    under pads) goes into **trunk vertex colour B**, sampled per vertex and multiplied in the material.
- **Foliage (geometry needles):** a small needle texture set, or vertex colour only.
  - BC with a subtle tip-to-base gradient and ±hue jitter;
  - an SSS/thickness map for translucency (below);
  - roughness about 0.5-0.6.
- **Foliage AO has its own channel: UV3.U** (4.6 channel map). Every tuft shares the needle UVs, so a texture can't
  hold per-position darkness, and vertex colour R/G/B are taken by wind. Compute it per vertex in Python: a
  hemisphere ray-cast against the pad envelopes and wood (Blender `BVHTree`), or, cheaper, the normalised depth
  inside the pad envelope blended with the height below the pad top. Write 0-1 into UV3.U; the material multiplies
  the base colour and the subsurface by it.
  - **Fallback** if UV3 is ever needed for something else: a pad-level gradient in the material from the PP2 pivot
    (vertex height relative to its pad pivot). It is coarser but costs no channel.
- **The SSS map** (`_SSS`) is a **linear** single-channel thickness/transmission mask (white = thin, lets light
  through). It is data, not colour: sRGB off in Unreal (4.13). The subsurface colour is the `SubsurfaceTint` material
  parameter, graded against the back-lit reference, not a texture. qa_check doesn't list `_sss` in `DATA_SUFFIXES`
  yet (`qa_check.py` line 71), so a map mis-tagged as sRGB wouldn't be caught: add `_sss` to it (4.12 pipeline
  changes).
- **Card atlas bake** (only when a card LOD is needed). Cycles in 5.2 has **no alpha bake type** [M]. Two methods:
  - **A. Selected-to-active per card:**
    - albedo = `DIFFUSE`, COLOR pass only;
    - normal = `NORMAL`, tangent space;
    - **opacity** = `EMIT` with the source set to white emission, the target cleared to black, and
      `max_ray_distance` ≈ the tuft half-thickness;
    - thickness = the AO node with Inside on, through Emission, inverted;
    - ORM from an AO bake.
  - **B. Orthographic render passes:** lay the variants on a grid, `film_transparent=True` [M] (render alpha =
    opacity), use the Diffuse Color pass, and convert the camera-space Normal pass to tangent space with a fixed
    matrix. Simpler for a flat atlas [72].
  - **Normals:** DirectX either way. Either bake with `normal_g="NEG_Y"` or flip with
    `pipeline/textures.flip_normal_green`. **Pick one and test for a double flip.**
  - **Atlas rules:**
    - 2048, power of two;
    - dilate colour and normal into the transparent area;
    - **cutout card meshes** (8-12 verts following the alpha outline, not quads) to cut overdraw [25];
    - alpha coverage at mip 2-3 ≥ 90% of mip 0 (gate G14) [11][17].
- **Channel packing:** the house BC sRGB + ORM linear + Normal DirectX, plus a **linear SSS/thickness map** for
  foliage. Put translucency in a texture channel, **never in vertex-colour alpha** on a Voxelize mesh (5.2).

### 4.9 Stage e: wind data (one hierarchy, several encodings)

**Always write `<asset>.wind.json`, even if v1 ships static.** It records:
- the branch hierarchy (node positions, the parent of each branch, order, length);
- which branch each pad or cluster and each tuft belongs to;
- pivots in Blender and Unreal space.

The encodings below are all derived from it, so either Unreal route can be exported later.

- **Rig-readiness rules:**
  - every limb and every pad or cluster is a separate logical element with its pivot at the attachment point;
  - at most **4 hierarchy levels** (trunk → limb → sub-limb → pad). That is the Pivot Painter 2 sample limit
    [46], and Dynamic Wind builds its chains from exactly this hierarchy (5.4).
- **Vertex colour: exactly one set.** Unreal's FBX import takes the first set only [49]. Blender exports every set
  (2 survived a round trip [M]).
  - **Foliage mesh:** R = hierarchy weight (0 at the attachment → 1 at the tips); G = per-pad phase; B = per-tuft
    phase; **A unused** (Nanite voxels overwrite vertex-colour alpha [35]).
  - **Trunk mesh:** R = junction bark-blend weight; G = moss/lichen mask; B = per-vertex AO for the branch bark
    (4.8); A unused.
  - **Unreal drops vertex colours by default.** UE 5.8.3 `BaseEditorPerProjectUserSettings.ini`,
    `[/Script/UnrealEd.FbxStaticMeshImportData]`, sets `VertexColorImportOption=EVertexColorImportOption::Ignore`
    (the skeletal default is Replace) [M]. The import **must set it to Replace** (4.13), or every mask above is
    silently lost.
  - **What the importer does to the values** (`FbxStaticMeshImport.cpp` lines 946-952, 5.8.3) [M]: it clamps each
    FBX channel to 0-1, **truncates** it to 8 bits (`uint8(255 × v)`, not rounded), builds an `FColor`, then stores
    `FLinearColor(FColor)`. That constructor decodes **RGB as sRGB** (through `sRGBToLinearTable`) and keeps **A
    linear**.
  - **So:** author masks as linear 0-1 floats in Blender and export with `colors_type="SRGB"` (the pipeline
    default), which encodes linear → sRGB. Unreal's decode then returns about the authored linear value in the
    material's VertexColor node. `colors_type="LINEAR"` would be decoded as sRGB a second time and come out too dark.
    Precision is 8-bit in sRGB space: fine near 0, about 1% steps near 1. Truncation biases values down by up to
    one step.
  - **Test it once per project:** round-trip a 0.25 / 0.5 / 0.75 ramp in R, G, B and A into a debug material and
    read the values back [U5.2: that Blender's SRGB export converts linear to sRGB for float colour attributes and
    leaves alpha linear].
- **UV2 = the Pivot Painter 2 element index** (pointing at a texel centre). UV3 carries the foliage AO (4.6).
  - **Elements** are the trunk, limbs, sub-limbs and pads: tens per tree, not thousands. Tufts are **not** PP2
    elements; their flutter phase is vertex colour B.
  - **Two textures, both needed.** `PivotPainter2FoliageShader` takes a *Pivot Position + Index* texture and an
    *X-Vector + X-Extent* texture [46]:
    - `T_*_PivotPos`: 16-bit (half) RGBA EXR. RGB = pivot position in **Unreal space centimetres**
      (x_ue = 100·x, y_ue = −100·y, z_ue = 100·z). A = parent index.
    - `T_*_XVector`: 8-bit RGBA. RGB = the element's X axis (its direction from the pivot, packed 0.5 + 0.5·v),
      A = its X extent (length), decoded by `ms_PivotPainter2_Decode8BitAlphaAxisExtent` [M: the function exists in
      5.8.3 engine content]. Confirm the extent scale against the function in the editor [U5.8].
    - One texel per element, power-of-two size, at most 30,000 elements and 4 hierarchy levels [46].
  - **Parent index encoding.** PP2 offers "Parent Index (Int as float)" and "Parent Index (Float - Up to 2048)"
    [46]. A plain half float is exact only up to 2048. **Use Int as float:** write the integer's bits as the half's
    bits (numpy: `np.uint16(n).view(np.float16)`), which the engine decodes with `ms_PivotPainter2_UnpackIntegerAsFloat`
    [M: present in 5.8.3]. Small integers become half-float subnormals, so check that the EXR writer doesn't flush
    them to zero. Test with indices 0, 1, 1500, 2047 and 2049 [U5.8: that the foliage shader decodes Int as float by
    default].
  - **Position precision.** Half floats step 0.25 cm at 256-512 cm, 0.5 cm to 1024 cm, 1 cm to 2048 cm and 2 cm to
    4096 cm. Fine for garden pines (under 4 m). For trees over about 20 m, pivots are off by 1-2 cm: test whether that
    shows, and if it does try a 32-bit float texture (HDR F32 compression) with the stock functions [U5.8]. Note the
    choice in the spec.
  - **Verify the Y flip with a one-vertex test mesh in Unreal** [U5.8].
  - PP2 is the recommended static encoding because it also feeds Unreal's
    `ConvertPivotPainterTreeToSkeletalMesh` (5.4). One export serves both routes.
  - The PP2 material functions and the converter take a UV index, so UV2 works and UV1 stays the lightmap
    [U5.8: confirm the index input on the 5.8 PP2 functions].
- **Planned `Scripts/pipeline/pivot_painter.py`** (new; a pipeline change, so run `test_pipeline.py` and
  `test_qa_negative.py` after it):
  - write both PP2 textures with numpy (the 16-bit PivotPos EXR with the Int-as-float index, and the 8-bit
    XVector map);
  - set UV2 to the texel centres;
  - emit the element table into `wind.json`.
  - Don't bundle GPL add-ons (Gvgeo, lukasreznicek, MTree) with Fab products. Our own baker avoids the question
    [69].
- **Skeletal (Route B, optional):**
  - an armature named `root` (the house skeletal convention, `pipeline/skeletal_prop.py`);
  - one bone chain per limb, one rigid bone per pad or cluster;
  - rigid single-bone weights;
  - export with `export_skeletal_set`;
  - write the Dynamic Wind JSON beside the FBX (5.4).

### 4.10 Stage f: collision

- **Trunk only.** Split the trunk polyline into 2-4 nearly straight runs, one convex hull each (≤ 32 verts). A
  leaning S-trunk is not convex.
- **This needs a new pipeline helper.** `helpers.make_ucx_hull(obj, index)` (helpers.py line 270) hulls the **whole
  evaluated object** and names the hull after that object. It can't hull part of a trunk:
  - hulling the real trunk gives one convex block that includes the limbs and blocks the wall-top and climb routes;
  - hulling temporary segment objects gives hulls named after the temporary objects, which Unreal won't match.
  - **Add `helpers.make_ucx_hull_from_points(parent, points, index, max_verts=32)`:** build the hull from a point set
    in the parent's local space (the ring vertices of one trunk run, from the skeleton), decimate and re-hull to the
    vertex budget the way `make_ucx_hull` does, name it `UCX_<parent.name>_<index:02d>`, parent it to `parent` with
    an identity parent inverse, no material, hidden from render.
  - Add tests to `test_pipeline.py` (name, parenting, convexity, vertex budget, a hull that stays inside the run)
    and a negative case to `test_qa_negative.py`, then run both. This is a pipeline change like any other.
- Add a limb hull only when gameplay needs it. A climbable limb is a deliberate spec decision.
- The **foliage mesh gets no collision.** Run `qa_check` with `require_ucx=False` on it and state it in the report.
  Canopies must not block wall-top runners or climb routes (DOJO_QUEUE).
- A rock-planted variant's rock gets its own hulls.
- Name hulls `UCX_<render node name>_NN`, or `UCX_<base>_LOD0_NN` inside a LOD group (ASSET_GUIDELINES 6.2).
- **After placement, re-run the kit's walk and climb checks** (dojo: `Scripts/dojo/walk_check.py`,
  `climb_check.py`).

### 4.11 Stage g: LOD and Nanite

- **The game ships Nanite:**
  - **trunk:** Shape Preservation **None** (never voxelized, so no voxel holes);
  - **foliage:** **Voxelize**, with `bLerpUVs` off (4.13 step 2);
  - no hand LODs.
  - **`bSeparable` is not a Shape Preservation value.** In 5.8.3 `ENaniteShapePreservation` is None / PreserveArea /
    Voxelize, and `bSeparable` is a separate flag in `FMeshNaniteSettings` that only affects voxelization
    (`EngineTypes.h` lines 3266 and 3306) [M]. Source [52] proposes Separable on a **voxelized** mesh as the
    alternative to splitting it. We split, so we don't need it. Use it only on a single-mesh tree that must be
    Voxelize (for example a pack tree) and shows trunk holes.
  - **Fallback:** set it deliberately, e.g. RelativeError 1-5 or 10-20% of triangles, and check it in the RT debug
    view. The dojo's "fallback RELATIVE_ERROR 0" rule is too heavy for hardware ray tracing on trees [U5.8].
- **Fab non-Nanite variant (Route C), only when shipping to Fab:**
  - `LodGroup` Empty → `_LOD0.._LODn` with strictly descending triangles;
  - LOD0 20-40k, LOD1 about 10k, LOD2 about 4k, then cards or an impostor;
  - "LOD up, not down": build the lowest LOD first [11];
  - LODs and FBX sockets are mutually exclusive (ASSET_GUIDELINES 6.2).
- **Fab's statement:** always write the collision and LOD statement, even "Nanite, no LODs".

### 4.12 Stage h: QA and export

- **A waiver can't stop qa_check hanging on foliage.** A waiver filters results after they are computed.
  `uv_overlap_sat` (`qa_check.py` lines 228-276) buckets triangles by UV cell and builds
  `itertools.combinations` for every bucket. With every tuft sharing identical UVs, one cell holds about 150-250k
  triangles, which is about 10^10 pairs: it runs out of memory or never finishes. The bark mesh's overlapping tiling
  UV0 is a milder case of the same thing.
- **Pipeline changes needed first** (in `Scripts/pipeline/qa_check.py`; run `test_pipeline.py` and
  `test_qa_negative.py` afterwards; bump the pipeline version):
  1. a `uv0_overlap=False` argument (CLI `--no-uv0-overlap`) that **skips** the UV0 overlap test and reports
     `uv_no_overlap` as "skipped by request" in the results, while UV1 is still tested with SAT. `overlap_method`
     alone can't do this, because it applies to UV0 and UV1 together;
  2. `_sss` (and `_thk`) added to `DATA_SUFFIXES`, so the colour-space check catches a mis-tagged thickness map;
  3. `helpers.make_ucx_hull_from_points` (4.10).
- **Then `qa_check` per object:**
  - **trunk:** `require_uv1=True`, `require_ucx=True`, `texel_density=5.12` (or 10.24 for a close-up trunk),
    `uv0_tile_range` set to the bark's real bounds (4.6), `uv0_overlap=False` (tiling bark overlaps by design);
  - **foliage:** `require_uv1=True`, `require_ucx=False`, `uv0_overlap=False`;
  - **per unit:** run the full qa_check (UV0 overlap included) on **one tuft of each variant** before instancing. The
    unit's UV0 must not overlap within itself, and it must have no coincident vertices (4.7);
  - time the UV1 SAT test on the realised foliage mesh once; it loops per triangle in Python;
  - no triangle budget under Nanite: report tris against the soft caps in 5.9.
  - Write every waiver and skip into `qa_report.json` the way `build_kit1.py` does (its `waive` set).
- **Export** only through `pipeline.export_fbx.export_fbx(path, objects, kind="static")`. It uses metres, FBX Units
  Scale, −Y forward / Z up, triangulate, `use_mesh_modifiers=True`.
  - **Realise all instances and apply modifiers before `qa_check`,** so QA sees what ships.
  - Route B uses `kind="skeletal"` via `skeletal_prop.export_skeletal_set`.
- **Reports:** `measure.json` (the gates in 6.1), `qa_report.json`, `export_report.json` with SHA-256 of every
  shipped file, and `<asset>.wind.json`.

### 4.13 Stage i: Unreal import recipe (static, Route A)

1. Use the legacy FBX importer (house setting):
   - Import Normals + MikkTSpace; Convert Scene ON; Convert Scene Unit ON; Import Uniform Scale 1.0;
   - Do Not Create Material;
   - Auto Generate Collision OFF with One Convex Hull per UCX;
   - Import Mesh LODs ON;
   - **Generate Lightmap UVs OFF** (Nanite; our UV1-3 must survive);
   - **Vertex Color Import Option = Replace.** The static-mesh default is Ignore (4.9) [M]. Without this every wind,
     junction, moss and AO mask is dropped with no warning;
   - Build Nanite ON.
2. Set the Nanite settings per mesh from Unreal Python. `FMeshNaniteSettings` fields are BlueprintReadWrite [M]
   [U5.8: exact Python spellings]:
   - trunk: `shape_preservation` = NONE; `lerp_uvs` stays on (its UVs are real texture coordinates);
   - foliage: `shape_preservation` = VOXELIZE and **`bLerpUVs` = False** (Python may spell it `lerp_u_vs`). The 5.8.3 field comment says to disable
     it "if indexes are stored in UVs. Lerping an index doesn't make sense and would break the shader"
     (`EngineTypes.h` ~line 3290) [M]. Our PP2 index is in UV2. If Nanite interpolates it where it merges tufts from
     different pads, the in-between index samples another element's pivot (Nearest filtering) and triangles tear
     away under wind.
   - **The cost:** with `bLerpUVs` off, UV error no longer counts when Nanite picks a LOD. For needles that's
     acceptable: their UV0 is a small uniform texture and the geometric error dominates. Gate it (G19 in 6.1): wind
     on, look at the mid and far bands for torn or stretched triangles, and for texture swimming on the needles.
   - **Alternative, if the gate fails:** keep `bLerpUVs` on and move the index where simplification can't blend
     it. A per-element constant is safe only if the simplifier never merges vertices across elements, which we
     can't guarantee, so prefer fixing the flag over this [U5.8].
   - the fallback fields.
3. Import textures:
   - BC sRGB; ORM linear; Normal DirectX;
   - **SSS/thickness: sRGB off, compression Grayscale** (or Masks if it's packed with other data), full mips;
   - PP2 PivotPos EXR as HDR (16-bit), sRGB off, **NoMipMaps**, **Filter Nearest** [46];
   - PP2 XVector: sRGB off, NoMipMaps, Filter Nearest, uncompressed (VectorDisplacementmap) so the 8-bit values
     survive [U5.8: the exact compression setting];
   - power of two, full mips (except PP2).
4. Build material instances from the kit's master (5.3). Assign `PerInstanceRandom` tint parameters.
5. Set the component or foliage-type settings (5.5):
   - WPO Disable Distance;
   - Shadow Cache Invalidation Behavior;
   - `NanitePixelProgrammableDistance` if anything is masked;
   - collision presets and trace responses (5.7).
6. Verify in a **second, fresh process** on the exact exported bytes (hash match) before calling it
   engine-verified (ASSET_GUIDELINES 6.5). Run one commandlet at a time and never leave one running.

### 4.14 Reusable generator module plan

**Build the first tree's generator inside its kit folder** (the pines: `Scripts/dojo/pines/`, owned by the pines
chat). Then **lift the parts that passed their gates** into a neutral package when a second tree needs them. Don't
design the generic core before one tree has passed.

| Module (target: `Scripts/vegetation/`) | Does | Lifted from |
|---|---|---|
| `veg_spec.py` | Load and validate the spec (4.3); seeds; units | first build |
| `trace.py` | Import traced polylines and envelopes from a reference panel; Catmull-Rom resample; px → m by the figure scale | first build + `measure_tree.py` |
| `skeleton.py` | Parallel-transport frames; pipe-model radii; collar and root-flare profiles; per-fork exponent report | first build |
| `colonize.py` | Space colonisation inside an envelope (numpy); tropism; pruning to the envelope | first build |
| `lsystem.py` | Optional Honda/ABOP ramification | only if needed |
| `tubes.py` | Rings, junction sinking, bark UV0 (integer k, V offsets, seam placement), UV1 pack | first build |
| `foliage.py` | Tuft and leaf unit builders; deterministic instancing; per-unit ids; volume normals | first build |
| `atlas_bake.py` | Card atlas (methods A/B), cutout card meshes, mip coverage check | when a card LOD is first needed |
| `wind_data.py` | `wind.json`, vertex-colour convention, UV2 index, Dynamic Wind JSON | first build |
| `Scripts/pipeline/pivot_painter.py` | PP2 EXR + UV2 texel centres (pipeline package, with self-tests) | first build |
| `measure_tree.py` | Section 6.2 metrics from a reference panel or a render (PIL + numpy only) | study C section 11 |
| `render_tree.py`, `compose_tree.py` | Judge render set (6.3) and side-by-sides | the stone/modern kit composers |

Species builders then shrink to a spec plus a few species hooks, such as the conifer tuft or a broadleaf leaf.

### 4.15 Short recipes for other species classes

These reuse stages a-i. They are starting points, not tested methods: the first build of each class writes its own
gates and adds what it learns here.

- **Bamboo** (culms, nodes, leaf sprays):
  - Check packs first (2.1). Build only for a designed grove or a gameplay role (cutting, climbing).
  - **Culm:** a straight or gently curved tube, 12-16 rings around, near-constant radius with a slight taper to the
    top. Internode length grows from the base to mid-height, then shortens. Each **node** is a raised ring (a
    slightly wider band plus a thin sheath scar), modelled as geometry.
  - **Branches** leave alternately at the upper nodes, 1-3 per node by species. **Leaf sprays** are instanced leaf
    units (4.7 broadleaf), long and narrow, hanging from the branch tips.
  - **UVs:** V along the culm, one tile per internode or a tile that spans several; U with an integer k (4.6).
  - **Wind:** culms sway whole with height weighting (SimpleGrassWind or PP2 with the culm as one element); leaves
    flutter by vertex colour B.
  - **Collision:** a capsule or 1-2 hulls per culm, only for culms a player touches. A grove uses one hull per clump
    or none.
- **Clipped hedges and topiary** (volume-shell foliage, not pads):
  - The form is a **designed volume** (box, ball, cloud, animal), authored as a closed low-poly shell from the
    reference.
  - Scatter leaf or needle units **on and just under the shell** (a 2-6 cm band), pointing outward, denser at the
    surface, with small random gaps. No branching skeleton except a few stems where the hedge is thin or seen from
    below.
  - Volume normals toward the shell (not an ellipsoid). AO from depth below the shell into UV3.U.
  - **Wind:** shimmer only. Clipped forms don't sway.
  - **Collision:** the shell itself (simplified to convex hulls) is a good blocker; decide per gameplay (hedges often
    block movement and sight).
  - The clipped look is a hard, readable outline with fine noise on it: gate the outline (IoU) and the surface
    gap fraction.
- **Broadleaf seasonal variants:**
  - One skeleton and one set of leaf placements; the seasons differ in **material and leaf count**, not structure.
  - Summer: full leaf count. Autumn: the same leaves with a per-leaf hue shift (a per-leaf random in UV3.V, the
    spare channel in 4.6, scaled by a material season parameter from green to red/yellow) and 10-30% removed. Winter: no leaf mesh, and the bare branch
    structure must carry the silhouette, so it needs the full twig order (3+) as geometry.
  - Blossom (cherry): a separate petal/flower unit set on the same points, and a petal FX the user sources.
  - Export each season as its own foliage mesh sharing the trunk mesh; the trunk is season-independent.

---

## 5. Unreal 5.8 setup

### 5.1 Pick a route per asset

| Route | What it is | Status in 5.8.3 | Use for |
|---|---|---|---|
| **A: static Nanite + WPO wind** | Static meshes (trunk None, foliage Voxelize), wind from Pivot Painter 2 or SimpleGrassWind in the material | Stable; works in any 5.x project and on Fab | **Default** for our custom trees; the Fab baseline |
| **B: Nanite Foliage (skeletal)** | Nanite skeletal mesh, optionally a Nanite Assembly of instanced parts, per-bone wind from DynamicWind, voxels at distance | **Experimental**: Nanite Foliage, Assemblies, Dynamic Wind (v0.1: "extremely experimental") and PVE all are [35][36][37][M]. **5.7 PVE assets are not compatible with 5.8** [37] | Megaplants; an optional pilot of one custom tree |
| **C: legacy LOD chain + impostor** | Non-Nanite LODs, dithered transitions, octahedral impostor [32] | Stable | Fab non-Nanite fallback only |

- **Project state [M]:**
  - DojoLab and DemoGame_1 already set `r.Nanite.Foliage=True`. This is read-only at runtime; it enables
    Assemblies, Voxels and TSR thin-geometry detection.
  - Both run Substrate with the Blendable GBuffer (`r.Substrate.ProjectGBufferFormat=0`: one closure per pixel),
    Lumen GI and reflections, and `r.RayTracing=True`.
  - DemoGame_1 has the ProceduralVegetationEditor plugin enabled. **DojoLab does not.** Enabling PVE or
    DynamicWind in DojoLab is the user's call.

### 5.2 Nanite settings

- **Shape Preservation** (`ENaniteShapePreservation`) [M]:
  - `None` for trunks;
  - `Voxelize` for foliage (needs `r.Nanite.Foliage` or `r.Nanite.AllowVoxels`);
  - `PreserveArea` is the legacy foliage technique, for projects without Nanite Foliage.
- **`bSeparable`** is a separate flag, not a Shape Preservation value, and it only affects voxelization [M]
  (4.11).
- **Voxel caveats:**
  - Voxelize can punch holes in solid trunks at small screen sizes. The fixes are splitting trunk and foliage, which
    we do (the trunk is None, so never voxelized), or `bSeparable` on the voxelized mesh (more disk, may look
    denser) [52].
  - **Voxels overwrite vertex-colour alpha** [35].
  - **Voxels don't sway.** Reading the 5.8.3 shaders, voxel clusters are drawn by `ClusterTraceBricks`
    (`NaniteRasterizer.usf`), which ray-traces the bricks in the instance's local space and never evaluates WPO;
    only the triangle paths (the software `ClusterRasterize` and the hardware-raster vertex shader) evaluate it
    [M, source reading, not yet seen on screen]. So a
    Route A tree's wind stops where its clusters turn into voxels, whatever the WPO Disable Distance says.
  - **Where voxels take over** depends on screen size (cluster LOD error), not on a distance setting, so it moves
    with resolution and FOV. Measure it per tree in the Nanite visualisation at the gameplay camera, then set **WPO
    Disable Distance at or below that distance**, so the sway fades out on triangles instead of popping to still at
    the voxel switch [U5.8: confirm in the Evaluate WPO view].
  - Epic's Nanite Foliage page steers foliage away from WPO toward Dynamic Wind and doesn't cover WPO on voxels
    [35]. Whether Route B's skinned voxels follow their bones is also unverified [U5.8].
- **Masked materials** run on the programmable rasterizer. Epic says to avoid alpha masking on foliage because it
  "causes overdraw and excessive mask function execution" [35]. Fortnite shipped opaque modelled leaves [55].
  - The "+20-30% for masked" figure is secondary [58, S]; measure it.
- **5.8 additions** [M][56]:
  - `NanitePixelProgrammableDistance` on foliage types, static and skinned components: beyond N cm it switches off
    mask, WPO and PDO rasterization;
  - "mask material only in early Z" is on by default;
  - skinned components gained WPO Disable Distance.
- **Clamp `Max World Position Offset Displacement`** on every WPO material. Nanite culls clusters with conservative
  bounds [39][M].
- **Debug views:** Nanite *Overdraw*, *Evaluate WPO*, *Clusters*.

### 5.3 Materials (foliage shading)

- **Needles and leaves:**
  - a Substrate **Slab** with `Sub-Surface Type = Two-Sided Wrap` (`MSS_TwoSidedWrap`, the Substrate equivalent of
    Two Sided Foliage) [44][M];
  - **one closure only** (Blendable GBuffer);
  - two-sided;
  - opaque if the needles are geometry.
  - Author with Slab nodes, not the "Substrate Shading Models" node [44].
- **Bark:** a Substrate Slab without wrap. Blend the unique trunk and the tiling bark by UV region or vertex colour
  R (the junction blend). Add moss from G.
- **Never use the translucent blend mode** for foliage. "Translucency" in foliage means subsurface colour
  (`r.Nanite.AllowTranslucency` is 0, "Heavy WIP") [M].
- **Pixel Depth Offset always invalidates VSM pages** [41]. Avoid it, or give it a Pixel Programmable Distance.
- **Per-instance variation:** `PerInstanceRandom`, and Per-Instance Custom Data on ISM or PCG. Follow the HZD
  formula: `Result = Tex × (2 × Colorize × Mask + 1 − Mask)` [11]. "Small values go a long way" [31].
- **Proposed master parameters:**
  - `Needle_BC`, `Needle_N`, `Needle_ORM`, `Needle_SSS`;
  - `SubsurfaceTint`, `TranslucencyStrength`, `HueJitter`, `ValueJitter`;
  - `WindStrength`, `PadSwayAmp`, `TuftFlutterAmp`, `MaxWPO`;
  - `PP2_UVIndex` (= 2).
  - Megascans advice: push normal intensity and translucency contrast, because the defaults look flat [60, S].
- **Lumen foliage cvars** [M][43]:
  - `r.Lumen.Reflections.MaxRoughnessToTraceForFoliage` (default 0.2; Epic suggests 0 for big savings; A/B it);
  - `r.Lumen.ScreenProbeGather.TwoSidedFoliageBackfaceDiffuse` (back-lighting, extra cost);
  - `r.Lumen.ScreenProbeGather.ShortRangeAO.FoliageOcclusionStrength` (0.7).
  - Whether a Substrate Two-Sided Wrap slab counts as a "foliage pixel" for these is unconfirmed [U5.8].
- **Where the masters live:** dojo → `Scripts/dojo/unreal/dj_materials.py` (coordinate with the dojo chats); Fab
  pack → `Scripts/unreal/materials/` (PackMaterials lock, `run_build.sh`).

### 5.4 Wind

| Method | Data from Blender | Cost | Use |
|---|---|---|---|
| **SimpleGrassWind** (engine function) [47] | a weight mask (vertex colour R/G/B or a UV gradient) | WPO: programmable raster + VSM invalidation | shrubs, grass, subtle flutter |
| **Pivot Painter 2** (`PivotPainter2FoliageShader`, `ms_PivotPainter2_*`) [46] | UV2 index + PP2 EXR (4.9); material *Tangent Space Normals* off | WPO; hierarchical sway | **Route A default** for hero trees |
| **Dynamic Wind** (Nanite skinning) [35][M] | a skeleton + a JSON of joints → simulation groups | per-bone GPU skinning, ~0.1 ms per 100k bones [35] | Route B |

- **Wind character by species.** Stiff clipped trees (niwaki, topiary) get a **gentle pad bob plus needle or leaf
  shimmer, never whole-tree rocking**. Free-growing trees get trunk sway weighted by height, per-limb phase, and
  leaf flutter [10][11][27].
- **Route A detail:**
  - if the trunk and limbs are stiff, put **no WPO on the trunk mesh** (its shadows stay cached);
  - the foliage mesh sways each pad about its pivot, with falloff by vertex R, and flutters tufts by B;
  - WPO Disable Distance 4000-6000 cm (40-60 m), **capped at the measured voxel takeover distance** (5.2: voxels
    don't sway).
- **Route B data model** (`UDynamicWindSkeletalData`, 5.8 source) [M]:
  - JSON `{"Joints":[{"JointName","SimulationGroupIndex"}], "SimulationGroups":[{"bUseDualInfluence","Influence",
    "MinInfluence","MaxInfluence","ShiftTop","bIsTrunkGroup"}], "bIsGroundCover", "GustAttenuation"}`;
  - a chain is a run of parent-child bones in the same group, and its length comes from the **rest pose**, so the
    Blender hierarchy and rest pose matter directly;
  - groups: 0 = trunk (`bIsTrunkGroup`), 1 = scaffold limbs, 2 = pad branches, 3 = twigs.
- **The Route B headless gap** [M]:
  - `ImportDynamicWindSkeletalDataFromFile` **opens a file dialog**, and the lookup UPROPERTYs are not
    Python-settable;
  - options: one manual GUI step per mesh; a small C++ editor helper calling `DynamicWind::ImportSkeletalData`; or
    PVE's exporter.
  - `ConvertPivotPainterTreeToSkeletalMesh(StaticMesh, PivotPosTexture, PivotUVIndex, TargetSkeletalMesh,
    TargetSkeleton)` turns a PP2 tree into a skeletal mesh (bones `Root`/`Trunk_N`/`Branch_N`/`Leaf_N`, rigid
    skinning, Nanite settings copied). The targets must be empty assets [M].
- **Route B limits:**
  - global wind direction only;
  - no player or object interaction;
  - animation stops below `AnimationMinScreenSize` (`r.Skinning.DefaultAnimationMinScreenSize`) [35][M].
- **Route B placement:** an `InstancedSkinnedMeshComponent` whose Transform Provider is
  `Wind_TransformProvider`, plus `BP_GlobalFoliageActor_UE5` (`MPC_GlobalFoliageActor`). Both are PVE plugin content
  [M].
- **PVE as a converter** (Extract From Mesh → Foliage/Graft Distributor → Export) is **a spike only**. PVE regrows
  and re-meshes, and may change a designed silhouette [37] [U5.8].

### 5.5 Shadows (Virtual Shadow Maps)

- **Invalidation.** WPO, PDO and skeletal deformation **invalidate cached pages every frame** [41].
- **Mitigations, most effective first:**
  1. **WPO Disable Distance** on every WPO component and foliage type. It made a "huge" difference in Fortnite
     [41][55].
  2. **`Shadow Cache Invalidation Behavior = Rigid`** on gently swaying foliage. The shadow stops following the
     sway, but no pages are redrawn. Check at low sun that the pad shadows don't visibly detach. Use `Static` for
     anything that never moves [M].
  3. **`r.Shadow.Virtual.Clipmap.WPODisableDistance.LodBias`** (default 3). Epic: "may need to be adjusted for
     **very low light angles**". For sunset scenes, test 3 against 4 and 5 [M].
  4. **Stop distant skeletal animation** (`AnimationMinScreenSize`).
  5. **Tight bounds:** clamp Max WPO Displacement.
  6. **Nanite on everything supported.** Non-Nanite is "much more expensive" in VSM [41].
     `r.Shadow.Virtual.NonNanite.IncludeInCoarsePages 0` can be a big win.
- **Don't** use the 5.1-era `r.Shadow.Virtual.Cache.MaxMaterialPositionInvalidationRange`. It is not in the 5.8
  source [M].
- **Profile:**
  - Viewport > Virtual Shadow Map > **Cached Page**;
  - `r.ShaderPrintEnable 1` + `r.Shadow.Virtual.Stats 1`;
  - Invalidated pages should be about 0 with the wind at rest and bounded with it on.

### 5.6 Lumen

- **Software ray tracing sees instanced foliage and ISM only when the mesh is Nanite.** Foliage also needs *Affect
  Distance Field Lighting* [42]. Turn on *Two-Sided Distance Field Generation* on the foliage mesh [57, S].
- **Skeletal (Route B) trees have no mesh distance field.** In SWRT they are seen by screen traces only; hardware RT
  uses the fallback mesh [42][U5.8]. Whether DojoLab runs HWRT or SWRT is unverified (`r.RayTracing=True`, no
  explicit `r.Lumen.HardwareRayTracing`) [U5.8]. Compare Route A and Route B at the same spot.
- **Lumen cost scales with unique meshes, not instances** [S]. Keep the variant counts low.
- **Budget:** Lumen GI + reflections 4 ms for 60 fps (Epic's console figure) [43].

### 5.7 Collision

- **Route A:** UCX hulls on the trunk (4.10). Collision presets: BlockAll on the trunk as the base, adjusted per the
  table below; the foliage mesh has no collision.
- **Route B:** a Physics Asset with **trunk bodies only** (PVE's `TrunkOnly`). UCX does not apply to skeletal
  meshes. `pipeline/skeletal_prop.py` already writes physics bodies to its sidecar [M].
- **Wind never collides** [35].
- The trunk should affect the navmesh and the canopy should not. Check with the navigation view.

**Gameplay channels (a proposal; the user decides, 8.9).** Presets alone don't settle what a ninja game needs. Set
these per mesh and write them in the spec:

| Query | Trunk (and rock) | Foliage mesh | Why |
|---|---|---|---|
| Pawn movement | Block | Ignore | Canopies must not block wall-top runs and climbs (4.10) |
| **Visibility** (AI line of sight) | Block | **Ignore** in v1 | A player in a canopy is otherwise seen through the needles. Hiding in trees is a gameplay feature: build it as a separate concealment volume (a simple box or hull on a custom channel or an overlap trigger per pad cluster), not as collision on the render mesh |
| **Camera** | Block (or let the spring arm probe ignore thin limbs) | Ignore | The third-person camera must not snap in and out of pads. If the camera ends up inside a canopy, fade or hide by distance, not with a masked dither on Nanite foliage (5.2 masked cost) |
| **Projectiles** (shuriken, kunai) | Block; they stick in the trunk | Ignore | A thrown weapon passing through needles reads right; a hit sound or needle FX can come from an overlap test later |
| Complex traces | Hit the trunk's **Nanite fallback mesh** | none | ASSET_GUIDELINES 6.2: the fallback serves complex collision. Keep the trunk's fallback error low enough that limbs a projectile can hit still exist in it; check a complex trace against the limbs [U5.8] |

- Set the foliage component's collision to **NoCollision** (not just "no UCX"). Otherwise complex traces can still
  hit its fallback mesh.
- For the battle royale, the same table holds. Bullet-like traces against thousands of trees should hit trunk
  hulls (simple) rather than fallback meshes (complex), for cost [U5.8].

### 5.8 Placement

| Tool | Route A (static Nanite) | Route B (skeletal) |
|---|---|---|
| Hand-placed hero trees | Static Mesh Actors (trunk + foliage), a small ISM, or a Blueprint / Packed Level Actor grouping the two | Blueprint with ISKM + `Wind_TransformProvider` + `BP_GlobalFoliageActor_UE5` |
| Foliage mode | yes: WPO disable distance, shadow invalidation, `NanitePixelProgrammableDistance`, collision, cull distance | **no**: there is no skinned foliage type in 5.8 [M] |
| PCG | Static Mesh Spawner (ISM) | **Instanced Skinned Mesh Spawner** [M] |

- With Nanite, ISM is enough; HISM only helps non-Nanite [59, S].
- Hero trees are placed by hand. Forests go through PCG or Foliage mode from packs.

### 5.9 Budgets per tier (proposed; measure before adopting) [U]

The frame is 16.6 ms at 60 fps. A proposed vegetation split at 1440p with TSR:
- Nanite visibility + base pass for all foliage: ≤ 2.0 ms;
- VSM for foliage (after caching): ≤ 1.5 ms;
- Lumen total: ≤ 4 ms [43];
- skinning and wind: ≤ 0.2 ms.

| Tier | Distance | Route A geometry | Route B | Non-Nanite (Fab) | Wind | Shadows | Collision |
|---|---|---|---|---|---|---|---|
| **Hero** | 0-15 m | trunk ≤ 80k tris, foliage ≤ 150-250k (source); 1 bark + 1 foliage set at 2K (4K bark only for a close-up) | ≤ 20 unique parts, ≤ 5k part instances, **≤ 1,000 bones** | LOD0 20-40k, LOD1 10k, LOD2 4k, impostor | PP2 pad-level; off at 40-60 m | Rigid (Auto if the sway must read) | UCX trunk / Physics Asset TrunkOnly |
| **Mid** | 15-60 m | the same asset | the same asset | LOD1-2 | off beyond 60 m | Rigid | trunk |
| **Background** | 60-300 m | pack trees, Voxelize | voxels, `AnimationMinScreenSize` ~0.05-0.1 | 1-3k + impostor | none | Static | none |
| **Forest / mountain** | over 300 m | voxels or HLOD | voxels, no animation | impostor / HLOD | none | coarse or none | none |

- **Per hero tree:** `stat GPU` Nanite + ShadowDepths delta **< 0.3 ms** at the gameplay camera [U].
- **Reference points:**
  - SpeedTree real-time trees are 1-12k tris at LOD0 [25];
  - Epic's Nanite Foliage demo tree is 41M tris, 12 parts, 2,160 instances, 850 bones [35];
  - Megaplants have 300-960 bones [M].

### 5.10 Unreal verification checklist

Run it in the kit's lab project, in a second fresh process, on the exact bytes:
1. **Import settings:** as 4.13. Confirm the imported mesh **has vertex colours** (Vertex Color Import Option =
   Replace; the default Ignore drops them) and that the ramp test reads back the authored values (4.9).
2. **Nanite views:** voxels at distance, no trunk holes, no overdraw hotspots at the gameplay camera. With
   `bLerpUVs` off on the foliage, no torn or stretched triangles with wind on (G19). Note the distance where voxels
   take over and check that WPO Disable Distance sits at or below it.
3. **VSM:** Cached Page + stats at the scene's sun angle, wind on and off, LodBias 3 against 5.
4. **Lumen:** subsurface back-light visible; no light leaks under pads; Route A against Route B if piloted.
5. **Performance:** `stat unit`, `stat GPU`, `ProfileGPU` at the gameplay camera and the widest shot. Record the ms
   in the report.
6. **Collision and navigation:** walk around the trunk; the wall-top and climb routes stay open; the navmesh is
   right. Check the trace responses in 5.7: a Visibility and a Camera trace pass through the canopy; a projectile
   sticks in the trunk and passes through needles.
7. **Motion:** a short capture with the camera orbiting and the wind on at 5, 15 and 40 m, for shimmer (5.12).
8. **Blind judge** on Unreal captures (6.4).

### 5.11 Open-world scale (the battle royale)

The MVP is a 1v1 duel, but the long-term game is a battle royale on about 32 km² (memory `world-map-plan`). Trees
built now should not block that. Everything here is **a proposal until measured** [U5.8].

- **World Partition HLOD.** HLOD layers come in three types: **Instancing** (static meshes become ISM components
  using their lowest LOD settings; Epic recommends it for trees and foliage), **Merged Mesh** and **Simplified Mesh**
  (both with a "Generate Nanite Enabled Mesh" option) [75].
  - Trees: an **Instancing** HLOD layer. For a Nanite mesh with Voxelize, the instanced HLOD should draw the same
    Nanite mesh, voxels included, so the hand-made card or impostor chain wouldn't be needed in-game [U5.8: check
    what "lowest LOD" means for a Nanite mesh].
  - Forest masses beyond the streaming range: try a Simplified Mesh layer with Nanite on, per cell, and compare it
    with instancing on memory and look.
  - A 5.7.3 forum report says the HLOD colouration view doesn't show Instancing proxies for Nanite meshes; judge by
    the real result, not that view [76, S].
- **Placement at scale:** PCG (Static Mesh Spawner → ISM) for forests, with runtime generation only if the static
  data gets too big. Hand-placed hero trees stay actors. PCG runtime (GPU) generation in 5.8 is unverified here.
- **Proposed budgets** (to measure on the target PC before adopting):
  - unique tree meshes per biome ≤ 20-30 (Lumen and memory scale with unique meshes, 5.6);
  - trees in a fully forested 1 km² ≈ 10-40k instances (one per 25-100 m²); across a 32 km² map with about 30%
    forest, 100-400k instances. Nanite is built for large instance counts [39], but each instance
    still costs culling, VSM and Lumen work: **measure one forested 1 km² cell first**;
  - WPO only inside 40-60 m; nothing moves beyond it;
  - collision: trunk hulls only; far cells may drop collision where no player can reach;
  - Nanite streaming pool and disk: record the per-tree Nanite resource size (Size Map) for each species and sum it
    per cell.
- **Visibility for 100 players:** the Visibility trace rule in 5.7 (canopies don't block sight) is a design choice
  with bigger stakes in a battle royale. Revisit it with the user before the BR map.

### 5.12 Thin needles, shimmer and TSR

- **Needles are sub-pixel at gameplay distance.** At 1440p a 1 mm needle is about 0.25 px wide at 5 m and 0.08 px
  at 15 m (4.6 maths). Sub-pixel geometry flickers from frame to frame as it hits and misses pixel centres, and wind
  makes it worse.
- **TSR thin-geometry detection.** `r.TSR.ThinGeometryDetection` (default 0) runs a pass that finds sub-pixel
  geometry and relaxes history rejection for it; the 5.8.3 source notes it is **on by default when Nanite Foliage is
  enabled** in the project, which DojoLab is [M]. `r.TSR.ThinGeometryDetection.Coverage.ShadingRange` (default 3)
  decides which shading models count: 0 = two-sided foliage only, 3 = all but unlit, with full dilation for foliage
  [M]. Whether a Substrate Two-Sided Wrap slab counts as "foliage" here is unverified [U5.8].
- **Mitigations, in order:**
  1. rely on voxels: at distance Nanite Foliage replaces the needle triangles with a volume, which is its purpose;
  2. check TSR thin-geometry detection is active (`r.TSR.Visualize 15` shows the classes);
  3. widen needles modestly (to 1.5-2 mm) **only if** the motion judge sees shimmer, and record it as a deliberate
     deviation from G9;
  4. if shimmer stays in the 15-40 m band, try an earlier voxel transition for the foliage mesh (the voxel and
     fallback settings in 4.13 step 2) and re-check the WPO distance cap [U5.8: which setting moves it].
  - Never fix shimmer with masked alpha fades on Nanite foliage (5.2).
- **Judge in motion.** Still frames hide shimmer. Every Unreal round includes the orbit capture in 5.10 step 7.

---

## 6. Quality gates

### 6.1 Measured gates (put them in the spec; `measure_tree.py` computes them)

| # | Gate | Target | Stage |
|---|---|---|---|
| G1 | Skeleton line-render IoU against the traced panel's trunk and limb mask | proposed ≥ 0.75; calibrate on the first tree | a |
| G2 | Height, crown width, crown base, lean (apex − base), foliage-centroid offset | each within ±5% of the panel (± 0.05 m for lean) at the spec scale | a, c |
| G3 | Pad / cluster count and tier count | equal to the hand-calibrated count | c |
| G4 | **Silhouette IoU** (foliage + wood masks, orthographic, trunk bases aligned, heights matched) | proposed **≥ 0.80**; per-row width-profile error mean \|Δw\|/w ≤ 0.10 | c |
| G5 | **Row fill / gap fraction** (foliage px ÷ Σ per-row span) | within ±0.05 of the panel | c |
| G6 | Pad size coefficient of variation; left/right mass ratio | within ±25% of the panel; no mirrored pairs | c |
| G7 | **Per-fork exponent n** (r^n = Σ r_i^n); child ≤ parent | n in 1.8-3.0 at ≥ 90% of forks; 0 violations of child ≤ parent | a, b |
| G8 | Flare ratio (base radius ÷ radius at 1 m) and trunk centreline error against the trace | flare ≥ 1.3 (tune to the reference); centreline mean error ≤ 2% of height | b |
| G9 | Leaf or needle length; min twig radius | species range (black pine 7-12 cm; twig ≥ 3 mm) | c |
| G10 | Needle-free inner wood fraction | measured from the reference close-up, ±25% | c |
| G11 | Foliage albedo median (linear) and render hue | albedo in the species band (conifer 0.08-0.12, after a primary cross-check); matched-light render hue within ±10° of the reference | d |
| G12 | Pad underside ÷ top luminance ratio (matched light) | within ±25% of the ratio measured on the reference | d |
| G13 | Bark plate/fissure contrast: sRGB-luma P90 ÷ P10 on a matched close-up | within ±20% of the reference (the pine sheet's close-up is about 6.0) | d |
| G14 | Card LODs only: alpha coverage at mip 2-3 ÷ mip 0; LOD silhouette-area retention at the switch distance | ≥ 0.90 each | g |
| G15 | Tris per mesh and per LOD; bones; unique parts; texture list and sizes | within 5.9 | h |
| G16 | `qa_check` passed, waivers and skips listed; per-unit tuft QA passed; UCX present on the trunk; hashes recorded | pass | h |
| G17 | 360° turntable, 8 views: no card lines, bald backs, visible seams or junction cracks | judge note, 0 defects | c, d |
| G18 | Unreal perf: Nanite + ShadowDepths delta per hero tree; VSM invalidated pages at rest | < 0.3 ms; about 0 | i |
| G19 | Unreal motion check, wind on, orbit capture at 5, 15 and 40 m: torn or stretched foliage triangles (`bLerpUVs` off), needle texture swimming, shimmer, a pop where voxels take over | 0 torn triangles; shimmer and pops not named by the judge | i |

**Gate against the reference, not against generic rules.** A generic "no near-black" gate once flattened the dojo
lighting (DOJO_QUEUE round 8).

### 6.2 Measuring a reference sheet (pixels, never eyeballing)

The method is in `C_blender.md` section 11. It uses PIL + numpy only (there is no scipy or cv2 on this PC's Python).
1. **Split the panels:** find row bands and separator lines, record each panel box, and hand-trace any panel whose
   crown overlaps a neighbour.
2. **Masks:**
   - background = the median of a corner patch;
   - foreground = colour distance > 45;
   - foliage = foreground with G > R+4 and G > B+4;
   - wood = foreground with R > B+8 and not foliage;
   - the scale figure = neutral grey.
   - **Mask the mound or grass band first,** or the crown base reads 0.
3. **Scale:** from the sheet's human figure, taken as 1.75 m. **The kit spec wins on heights.**
4. **Metrics:** height, crown width and base, lean, trunk base angle, foliage centroid, pads (connected components
   after a 5 px closing at half resolution, components ≥ 2% of the area; **calibrate the kernel against a hand
   count**), tiers (peaks of the per-row width profile), row fill.
5. **IoU:** render ours orthographic on the same grey, scale it so the heights match with the trunk bases aligned,
   and compute IoU and the per-row width error. Make an XOR heatmap for judge prep only; never show it to the blind
   judge.

### 6.3 Render set (for every judge round)

- **Silhouette pair:** flat black masks on the sheet's grey, orthographic or the sheet's long-lens look, with the
  same human figure at the same scale.
- **Clay pair:** grey material, soft front-top studio light (form, taper, junctions).
- **Final pair:** materials, lit to match the reference panel.
- **Turntable:** 8 views at 45°.
- **Context:** in the kit's lighting (dojo: low sunset sun, **back-lit through the foliage**) at 5, 15 and 40 m.
- **Unreal captures** of the same views. The dojo judges found Unreal colour shifts that Blender never showed, so the
  final judge always sees Unreal.
- **Motion capture** in Unreal: a short orbit with the wind on at 5, 15 and 40 m (G19, 5.12). Stills hide shimmer.
- **Render setup:** Cycles on the PC GPU for finals. A cloud VM does only low-sample silhouette and clay gates.

### 6.4 Blind judge prompts

Randomise the left/right order per pair and record the key outside the judge's view. Show the judge only images:
no filenames, no heatmaps, no numbers.

**J1 Silhouette (after stage c):**
> You will see N pairs of silhouettes of garden trees on grey. In each pair one comes from a hand-drawn design
> sheet and one is a 3D reconstruction. For each pair: (1) say which you think is the reconstruction and how
> confident you are (50-100%); (2) list only DESIGN differences: trunk line, where branches leave the trunk, number,
> size, shape and spacing of foliage masses, gaps and sky holes, overall proportions. Ignore resolution, edge
> softness and noise.

**Pass:** accuracy over ≥ 8 pairs is no better than chance (≤ 60%), and no design difference is named twice.

**J2 Clay / form:**
> Two grey renders of a tree trunk and branches. Which looks more like a real, living tree, and why? Comment on
> taper, how branches join the trunk, the root flare, bends and age marks, and anything that looks generated or
> repeated.

**J3 Final look (scored, as in the dojo rounds):**
> Score how closely the right image matches the left reference, 0-10, on design and on look (colour, value, light
> through the foliage, bark). Name the top 5 differences, most important first, and say which are design and which
> are material or lighting.

- Keep J1 as the pass/fail bar ("must not be able to pick the copy on design").
- Use J3's score and top-5 list to drive one fix round.
- Stop and show the user if J1 fails decisively twice.

**J4 Unreal context:** the J3 prompt on Unreal captures at gameplay distance against the scene reference.

**J5 Motion (G19):**
> Watch these short clips of trees in wind. Note anything that flickers, shimmers, sparkles, tears, stretches,
> pops or suddenly stops moving, with the time and where in the frame.

### 6.5 Numbers every report carries

`measure.json` holds:
- G1-G15 with targets and pass/fail;
- tris per mesh; bones; unique parts; texture list with sizes and colour spaces;
- waivers and skipped checks, with the reason;
- the per-order bark texel density and the UV0 tile range used;
- the measured voxel takeover distance and the WPO Disable Distance chosen;
- SHA-256 of the shipped files;
- Unreal ms (G18) with the camera, resolution and scalability used;
- judge results (J1 accuracy, J3 score and top 5).

---

## 7. Pitfalls and how to avoid them

| # | Pitfall | Avoid it by |
|---|---|---|
| P1 | **Procedural noise standing in for structure** (our sand, mountains and far town: weakest in every judge round) | Trace the structure from a reference; generate only the fine ramification inside traced envelopes; buy natural scenery (section 2) |
| P2 | Trying to grow a designed form (niwaki, topiary) from a botanical simulator or PVE | Author the top of the hierarchy by hand, generate the bottom (4.4) |
| P3 | Patching a construction that doesn't converge | Change the method (CLAUDE.md). Stop early and show the user on a decisive fail |
| P4 | Green blob, no sky holes | Gate G5 row fill; sparse pad interiors |
| P5 | Even spacing, symmetry, mirrored variants | G6; structural variants (3.8); never mirror a designed front |
| P6 | Straight trunk, linear taper, no flare | Traced centreline; collar and root-flare profiles; G8 |
| P7 | Child thicker than parent; twig as thick as a limb | Pipe-model radii in code; G7 |
| P8 | Cylinder-into-cylinder forks with texture seams | Sunk, flared collars plus a vertex-colour bark blend; V offsets continue from the parent |
| P9 | Bark relief only in a normal or height map | Plates as geometry on hero trunks (house rule); don't plan on Nanite displacement for bark |
| P10 | Texel density jumps at forks; seams on the visible side | Integer-k UVs, V continuity, seam on the least-seen side (4.6) |
| P11 | Flat-shaded or edge-on cards; masked-card overdraw | Modelled foliage units; volume normals; cutout cards only for the Fab LOD |
| P12 | Foliage too bright, too saturated, or the wrong hue (blue-green for a yellow-olive pine) | G11; derive albedo, never copy render colours |
| P13 | No interior darkness or back-light at sunset | Baked AO; Two-Sided Wrap subsurface; judge back-lit shots |
| P14 | Scale errors (giant needles, thick twigs) | G9 at the species' measured sizes |
| P15 | One tuft or card visibly repeated | ≥ 3 variants with random roll and scale |
| P16 | Rigid, synchronised or whole-tree rocking wind on stiff clipped trees | Pad bob + shimmer; per-pad and per-tuft phase; no WPO on the trunk |
| P17 | Wind or masks stored in vertex-colour **alpha** on a Voxelize mesh | Alpha unused; R/G/B only (4.9) |
| P18 | Vertex colours lost or shifted: the static FBX import default is **Ignore**; the importer truncates to 8 bits and decodes RGB as sRGB, A as linear (4.9) | Import with Vertex Color Import Option = Replace; author linear, export `colors_type="SRGB"`; ramp round trip before trusting values |
| P19 | UV1 lightmap rule vs wind UVs; more than 4 UV sets under Nanite | Follow the channel map in 4.6: UV0 material, UV1 lightmap, UV2 PP2 (foliage) or unique bake (trunk), UV3 foliage AO. Never more |
| P20 | Frenet frames flipping on S-curves (twisted bark, jumping seams) | Parallel-transport frames |
| P21 | GN `Curve to Mesh` ignoring radius (since 4.5) and wrapping UVs | Plug radius into Scale; fix the seam; better, tubes in Python |
| P22 | Depending on an add-on (Sapling, MTree) that `--factory-startup` doesn't load | Own Python generator; add-ons for spikes only |
| P23 | Double normal-map green flip | Pick `NEG_Y` bake or `flip_normal_green`, not both; test |
| P24 | Alpha-tested foliage thinning at distance | Coverage-preserving mips; G14; prefer geometry + voxels |
| P25 | Voxel holes in trunks | Separate trunk mesh with Shape Preservation None (never voxelized). `bSeparable` is a flag for a mesh that must stay Voxelize, not a trunk setting |
| P26 | WPO invalidating VSM every frame; pad shadows lagging at sunset | Disable distance, Rigid, LodBias test at low sun (5.5) |
| P27 | Old cvars from 5.1-era guides | Check the name exists in the 5.8 source before using it |
| P28 | Canopy collision blocking wall-top runners and climb routes | Trunk-only hulls; re-run walk and climb checks |
| P29 | Megaplants used as a forest | A few at the edge; forests from lighter packs, voxels and HLOD |
| P30 | 5.7 PVE assets in 5.8; version drift in Experimental features | Match versions; Route A as the baseline; state the engine version on Fab |
| P31 | A Dynamic Wind import step inside a commandlet (file dialog) | Plan a manual step or a C++ helper up front, or stay on Route A |
| P32 | Judging only in Blender | Final judges on Unreal captures in the scene light |
| P33 | Gates that encode a proxy instead of the reference (the dojo's anti-black rule flattened the lighting) | Measure the reference and gate against it (6.1) |
| P34 | Inventing features the reference doesn't show (judges marked down invented dojo items) | Every feature traces back to a reference panel or the spec |
| P35 | Two agents on one asset; a Blender GUI left open on a file edited headlessly | Locks; never open another chat's files; close GUI windows first |
| P36 | Bundling GPL add-on code or pack content in a Fab product | Own code only; record texture provenance; AI disclosure for AI reference sheets |
| P37 | Nanite interpolating the PP2 index in UV2 (torn triangles under wind) | `bLerpUVs` off on the foliage mesh; G19 |
| P38 | qa_check running out of memory on instanced foliage (every tuft shares UV0) | Skip the UV0 overlap test with the new argument, not a waiver; full QA per tuft unit (4.12) |
| P39 | Coincident needle bases failing qa_check | Weld the bases per fascicle or offset them ≥ 0.05 mm (4.7) |
| P40 | One convex hull for a whole tree, or hulls named after temporary objects | `make_ucx_hull_from_points` per trunk run, named after the trunk (4.10) |
| P41 | AO baked onto overlapping UVs (tiling bark, shared tuft UVs) | Trunk AO on UV2; branch AO in vertex colour B; foliage AO in UV3.U (4.6, 4.8) |
| P42 | Expecting wind on voxels | Voxels don't evaluate WPO: cap the WPO Disable Distance at the voxel takeover (5.2) |
| P43 | Sub-pixel needles shimmering in motion | Voxels, TSR thin-geometry detection, a motion judge; widen needles only as a recorded deviation (5.12) |
| P44 | Bark texel density far above what the camera resolves | House 5.12 / 10.24 px/cm; resolvable ≈ 12.5 px/cm ÷ metres at 1440p (4.6) |
| P45 | **Solid pad cores or shells** added to make needle pads look dense. They read as opaque brown saucers from below and in back-light, and as a green sheet under the needles from above (pines f1) | Build a pad only from needle bursts on an open twig lattice. Get density from the burst count and 1-3 burst layers, never from a shell |
| P46 | **Bursts on vertical shoots** rising from arms on the pad's underside. The pad reads as a cage of sticks; a burst with no arm nearby hangs a long shoot from a limb far below ("curtains") | Run the arms through the lower third of the pad. Attach each burst by a kinked shoot no steeper than about 45 degrees, and let the allowed rise scale with the pad's thickness. Drop a burst that has no arm within reach rather than attaching it anywhere |
| P47 | Space colonisation toward burst sites above the limb grows **vertical pad-support sticks** and smooth, even networks | For designed forms (niwaki), author the lattice: a fan of 3-8 angular arms from the limb end, forking 1-2 more times toward the pad outline (`Scripts/vegetation/cloudpad.py`) |
| P48 | Limbs smoothed with Catmull-Rom read as **single smooth tubes** | Zig-zag the traced path, changing direction every 15-30 cm (scaled to the tree), with knuckle swellings at the nodes. Keep the traced ends fixed (`skeleton.angularize`) |
| P49 | **Trunk girth taken from a closed wood mask of an AI sheet** takes in the mound, roots and pale highlights, so trunks come out 2-3x too thick. A row-scan trunk/crown ratio is also fooled wherever pads cover the trunk | Set the girth from a trunk-diameter/crown-width target and check it by eye on side-by-sides. Our renders came out about 1.5x the spec radius (flare, relief, lobes, collars), so aim the spec below the visual target |
| P50 | **Voronoi bark reads as a cellular or giraffe net**, whatever the anisotropy or edge width. Level sets of stretched noise give too few, jagged furrows | Build the plate pattern explicitly: meandering vertical columns, staggered slanted cross cracks, flaky terraces, and ridged centimetre crumble carrying the look. Check a lit numpy preview (Lambert from the normal map x AO) before rendering (`make_pine_textures.bark`) |
| P51 | A **two-view visual hull boulder** comes out as a drum with vertical sides and a flat top. Where the sheet's two views disagree on height, the hull takes the lower one | Split the hull into 2-3 masses through the trunk's crack. Chip each mass with random planes, never on the faces it shares with another mass, and hull each one. Convex masses give fused creases, an overlap-free per-mass box UV and exact UCX hulls. Pick one view as the height authority and rescale the other |
| P52 | **Roots projected from 2D guides** stand off the rock like spider legs | Walk each root over the rock: snap every step to the nearest surface point (BVH) with the root half sunk, blend heading persistence with the downhill tangent, fork once or twice, and taper to the ground |
| P53 | Matching front-panel pads to side-panel pads by vertical overlap **stacks several pads onto one side pad**. The side view then shows 1-3 merged masses where the sheet has 5-7 | Penalise reusing a side pad in the matching, so the pads spread over distinct depths |
| P54 | **A judge's colour words against the pixels.** The judge called the sheet's needles blue-green (hue 120-150); they measure hue 70-76 (olive), with grey-green highlights and pale bases | Gate on the measurement (G11). Answer the perception with value and saturation: lighter, less saturated body, glaucous highlight needles, pale fascicle bases |
| P55 | Framing an **asymmetric tree** (a reaching limb) symmetrically about its origin renders it at a third of the frame | Frame each view on its projected bounds. Keep one scale per tree across its views |
| P56 | The **twig lattice dominates the triangle count**: about 80 % of the trunk mesh once every burst has its own shoot tube | Use 3-sided shoots under 7.5 mm and plate-density rings on the trunk only. Report the lattice share against the 5.9 caps. Under Nanite, measure before cutting (G15, G18) |
| P57 | **Rosette sites sampled on a pad's FOOTPRINT** leave its flanks bare (thin "wing" pads), and rim rosettes turned outward hang their needles down (a hairy fringe, an umbrella in close-up) (pines v2) | Sample the sites on the pad's dome SURFACE, area-weighted, thinned to a 3D spacing; keep every fan upright (at most ~30 degrees off vertical on a flank, a few under-rim fans at 30-45 degrees); inset the sampled surface by half a fan so the needle tips land on the traced outline (`rosettepad.dome_sites`) |
| P58 | A **recursive k-means twig lattice** runs long twigs to the pad rim and loops down to the flank fans: loops from above, "curtains" from the side | Grow the lattice as a spanning tree (Prim) over internal points in the lower half of the pad, costs favouring short, level, outward edges; hang every fan on a short shoot from its nearest node below it |
| P59 | **Thin, sparse fans** (1-1.5 mm needles, ~80 per fan, 12-15 cm apart) read as faint stars at tree distance: the pads look transparent next to the sheet's cloud masses | 120-160 needles per fan at a 3.8 mm base (the P43 widening, recorded), fans 9-11 cm apart so they nearly touch; the per-pad count then follows the pad surface (tens to 200+), not a fixed 15-25 |
| P60 | The **pipe model with ~100 tips per pad** makes the feeding limb a log where it enters the pad | Pipe exponent ~2.6 and taper the limb's floor radius to ~45 % where it enters the pad (G7 then sits at 0.85-0.94 in band: report it) |
| P61 | A **base mound built as a flat disc** with a vertical soil edge reads as a slab; roots under it make the trunk go into the moss like a post | A conical profile with gaussian moss hummocks, the edge dipping under grade, a boulder and a shrub by the trunk, hundreds of tiny moss-cushion clumps; start the nebari on the mound top |
| P62 | **Bark as thin cracks on narrow columns with random rust spots** reads as a spotted log | Plates 7-10 cm wide and 1.5-2.8x as tall, cross cracks as wide as the vertical fissures, stepped flaky terraces with a shingle tilt, rust only on the terrace risers; keep any flake net faint (P50). Roll the close-up camera to the trunk axis on a leaning trunk |
| P63 | **Denser foliage renders darker**: the same needle albedo measured hue 61 on open pads and (60,68,40) hue 77 on dense rosette pads (self-shadow) | Re-measure G11 after every density change and re-grade the albedo; the render hue shift under the warm key is about -7 to -14 degrees |
| P64 | **Evenly spaced rosettes** (one Poisson spacing over the whole dome) read at tree distance as a uniform hairy mat, and all-brush pads as grass (pines v2f) | Group the sites into twig-end CLUMPS (3-6 rosettes, centres ~0.19-0.23 m apart) and fill between them to ~60 % of the area target; round stars on the pad top, upright brushes only on some rim sites |
| P65 | **Area-weighted dome sampling starves the dome TOP** (flanks carry more area per plan area): small pads show a ring of rosettes round an empty crown from above | Weight the sampling toward up-facing cells (x 0.45 + 0.55 n_z) |
| P66 | **Rim rosettes rooted below the twig lattice** read as a hanging fringe even when every fan points up | Floor the fan bases at ~20 % of the local pad thickness above the underside and drop the under-rim fans |
| P67 | An **angularize zig-zag that is purely sideways** is invisible in the front view of a limb that lies in the view plane (judge: "straight rods") | Mix the kink direction 35-65 degrees up or down from the side, so every view sees the direction changes |
| P68 | **Limb separation with the floor radii** misses the overlaps the pipe model creates later | Two passes: build once for the final radii, repeat the same random sequence and push limbs apart with those radii (`treegen.build_skeleton_separated`) |
| P69 | For a **tree on a rock**, a trunk girth read at 1/4 of the tree height falls ON the rock and the root swell doubles it: the trunk swells to half the rock's width | Set the trunk at the rock top from the sheet's trunk / rock-width ratio (~1/5 on the dojo sheet) and let the roots make the root plate |
| P70 | **Roots pulled hard into cracks** all run down as parallel vertical strands; sunk 3/4 into the rock they vanish at tree distance | Weak crack attraction, a longer run over the top first, the centre ~0.85 r above the stone, azimuths where the sheet drapes them, a third of them lifted over a stretch |
| P71 | **A thin flat mound bed** fixes the "thick hump" read but becomes a lawn plate once grass tufts and 2-9 cm moss blades cover it | Keep a low moss bed (0.7 h) that is LUMPY from many 2.5-6 cm cushions with a cushion vertex colour (dark gaps), 1-3 cm moss tufts, real fern sprays (paired pinnae), no lawn grass |

---

## 8. Appendix: the niwaki black pine plan

This is an input for the pines build (workflow `dojo-niwaki-pines`, `Scripts/dojo/pines/`, lock `DojoPines`, owned
by the pines chat), not its spec. The pines chat and the user decide the final picks, names and heights.

### 8.1 What the reference shows

`References/Dojo/dojo_japanese_pine_ref.png` has **12 panels**: a top row T1-T6 and a middle row M1-M6, with a
human figure for scale, plus bark and needle close-ups.

- **The niwaki reading:**
  - a dark, strongly curved trunk;
  - **5-12 flattened, dome-topped pads** in tiers, each with a dark underside and a lit rim;
  - clear sky between tiers;
  - pads get smaller toward a small rounded apex;
  - the lowest pad often reaches far out on one side.
- **The close-ups:** radiating 2-needle brushes at the twig tips, with brown twigs visible between them (the
  momiage look [22][24]).
- **First automatic measurement** (C_blender section 11; figure = 1.75 m; pad counts **uncalibrated**; M4-M6
  heights include the rock):

| Panel | Form | H (m) | Crown W (m) | Lean (m) | Pads (auto) | Row fill |
|---|---|---|---|---|---|---|
| T1 | twin-curve, low | 2.20 | 2.20 | +0.32 | 5 | 0.30 |
| T2 | narrow tiered | 2.38 | 1.31 | −0.11 | 4 | 0.38 |
| T3 | wide, low | 2.38 | 2.56 | −0.59 | 5 | 0.25 |
| T4 | tall S-curve | 3.47 | 2.65 | −0.31 | 6 | 0.31 |
| T5 | slender column | 3.36 | 1.81 | −0.17 | 7 | 0.37 |
| T6 | tall S, wide | 3.32 | 2.44 | +0.66 | 6 | 0.29 |
| M1 | reaching limb (width clipped; ≈ 3.9 m by hand) | 2.87 | ≥ 3.21 | −0.85 | 5 | 0.28 |
| M2 | straight tall | 2.78 | 1.13 | +0.11 | 7 | 0.33 |
| M3 | leaning | 2.66 | 2.02 | −0.23 | 4 | 0.33 |
| M4 | rock-planted | 2.20 | 1.35 | +0.28 | 2 (merged; recount) | 0.31 |
| M5 | rock, slender | 2.19 | 0.87 | −0.03 | 6 | 0.37 |
| M6 | rock, wide | 2.34 | 1.53 | +0.42 | 5 | 0.27 |

- **Reading the table:**
  - garden scale, about 2.2-3.5 m;
  - crowns 0.9-2.7 m (3.9 m for the reaching limb);
  - **row fill 0.25-0.38, so about two-thirds of each crown's row span is sky.** That separation is the signature
    to keep.
- **Colour look targets** (rendered, not albedo):
  - needles median sRGB (80,91,50), hue ~75°, P10 (46,54,22), P90 (148,158,114);
  - bark P10 (34,22,17), median (82,73,64), P90 (163,141,123), luma ratio P90/P10 ≈ 6.0.

### 8.2 Choosing four structurally different pines (proposal)

| Pine | Archetype | Candidate panels | Why |
|---|---|---|---|
| A | tall S-curve hero | T4 (or T6) | tallest, many tiers; the classic niwaki line |
| B | reaching limb | M1 | the sheet's signature "reaching arm"; strongest silhouette |
| C | twin-curve, low | T1 (or T3) | a different trunk topology (two leaders) |
| D | rock-planted | M6 (or M4) | exposed nebari over stone; a separate rock piece with its own hulls |

- **Two variants per pine** (the queue asks for 4 × 2) should differ in structure: which side the reaching limb is
  on, pad count ±1-2, apex shape, seeds. **Not a mirror, not a tint.**
- The two variants may share the trunk's lower third to save work, if the judge can't tell.
- Proposed names: `SM_DKN_Pine<A-D><1-2>_Trunk` and `_Foliage`.
- **Heights:** take the panel proportions and scale to the dojo layout's slot sizes. The spec wins over the sheet's
  assumed 1.75 m figure.

### 8.3 Skeleton design per tree

- **Trunk:** trace the centreline from the panel; get depth from an authored curve.
  - 4-8 bones or segments;
  - radius at 1 m about 0.10-0.18 m for 2.2-3.5 m trees (measure from the panel's wood mask);
  - flare ratio ≥ 1.3;
  - the tachiagari curve kept exactly as traced.
- **Scaffold limbs (order 1):** 4-8 per tree, each traced to its pad.
  - Alternate left, right and back; no pairs; no limb crossing the front view; the first limb at about 1/3 height
    (3.3).
  - Heavy horizontal limbs sag, then rise at the pad (3.4).
  - Pine B's reaching limb is long and near-horizontal with a slight downward belly; model it as a gameplay-neutral
    limb with no collision unless the spec says otherwise.
- **Pads (order 2+):** one envelope per pad, traced from the panel: a half-ellipsoid, domed top, flat bottom.
  - Typical size: rx 0.3-0.9 m; rz_top ≈ 0.25-0.4 × rx; rz_bot small.
  - Space colonisation inside each envelope, seeded from the limb end (4.4 starting values). Denser toward the top
    and rim, open underneath.
- **Deadwood:** only where the panel shows it (no invented jin).

### 8.4 Needles

- **One modelled 2-needle-fascicle tuft, 3-5 variants:**
  - needles 7-12 cm, about 1 mm wide, 2-4 tris each, splayed 30-70°, slightly twisted and drooping;
  - a white candle (1.5-2 cm) in the centre;
  - a bare twig behind;
  - the two needles of each fascicle welded at the base inside the sheath (4.7, no coincident vertices).
  - Fascicles per tuft: **choose the count by matching the needle close-up.** Momiage leaves about 7-8 pairs per
    shoot [22][24], and the close-up's radiating brushes may be denser. Try variants spanning about 8-20
    fascicles.
- **About 40-160 tris per tuft; 20-150 tufts per pad by pad size.** That gives roughly 30-150k foliage tris per
  tree (within 5.9).
- **Keep the inner 3-4 years of wood needle-free** (G10).
- **Volume normals** toward each pad's ellipsoid (4.7).
- **Card atlas:** bake it from the same tufts only if the Fab non-Nanite variant is wanted.

### 8.5 Bark

- **Trunk:** real plate geometry (lobes, fissures, crisp plates) at the close-up's plate scale, plus a unique trunk
  bake. Aim for the reference's **high plate/fissure value contrast** (G13 ≈ 6.0 on a matched close-up):
  near-black-brown fissures, pale warm grey-brown plate tops.
- **Limbs and twigs:** one tiling branch bark, grey-brown on young wood, at matched texel density along the grain:
  5.12 px/cm (4.6), 10.24 only if a close-up camera frames a trunk. The unique trunk bake goes on the trunk's UV2.
- **Collars** at every limb; **nebari** on all four trees, strongest on Pine D over the rock.
- **Moss** at the base via vertex colour G, if the dojo's look pass wants it.

### 8.6 Wind hierarchy

- **Levels:** trunk → scaffold limb → pad, plus per-tuft flutter as the fourth level. At most 4 levels.
- **Bones if Route B:** trunk 4-8, limbs 4-8 × 2-4, pads 5-12 × 1-2, so about **40-120 bones** per tree (≤ 200),
  far below Megaplants' 300-960.
- **Route A (ship first):**
  - no WPO on the trunk mesh (niwaki are stiff);
  - the foliage mesh bobs gently about each pad's pivot (PP2 via UV2) and shimmers the needles by tuft phase;
  - WPO Disable Distance 40-60 m, capped at the measured voxel takeover distance; Shadow Cache Invalidation
    **Rigid**;
  - foliage mesh `bLerpUVs` off (the PP2 index is in UV2); vertex colours imported with Replace;
  - test LodBias 3 against 4 and 5 at the sunset sun angle;
  - per-instance wind phase and hue via `PerInstanceRandom`.
- **Route B pilot** (one tree, only when the user says go):
  - `ConvertPivotPainterTreeToSkeletalMesh` from the Route A PP2 data, or a Blender armature;
  - the Dynamic Wind JSON with groups trunk / limb / pad;
  - requires enabling PVE and DynamicWind in DojoLab (the user's call);
  - compare cost and look against Route A.
  - **Stop and show the user** if it needs the manual dialog step, or if a PVE pass changes the silhouette.
- **PVE Import / Extract From Mesh spike:** separate, experimental, only on the user's go.

### 8.7 Budgets and checks

- **Geometry, per tree:** trunk ≤ 80k tris, foliage ≤ 150k (up to 250k if a judge needs density), ≤ 200 bones
  (Route B).
- **Textures:** one bark set plus one needle set at 2K, shared by all four pines. A 4K unique trunk only if a
  close-up camera needs it.
- **Unique meshes:** 8 variants × 2 meshes. Lumen cost scales with unique meshes; if Unreal numbers are high, drop to
  one variant per pine.
- **Unreal:** < 0.3 ms per tree at the courtyard camera [U]; VSM invalidations bounded with wind on.
- **Collision:** 2-4 UCX trunk hulls per tree (`make_ucx_hull_from_points`, 4.10), plus rock hulls on Pine D.
  Trace responses per 5.7. Re-run `walk_check.py` and `climb_check.py` around every placement.
- **Origin:** trunk base at z = 0, trunk and nebari sunk about 0.2 m below grade; Pine D's rock, trunk and foliage
  share the rock's ground-contact origin (4.2). Three FBX files for Pine D, two for the others.

### 8.8 Build order and stop points

1. **Calibrate the reference measurements** (hand-count pads, hand-trace M1) and trace the four chosen panels.
2. **Stage a** skeletons → J1 on line renders against the panels. **Stop** if it fails decisively.
3. **Stage b** bark mesh → J2 clay.
4. **Stage c** pads and tufts → G3-G6 + J1 silhouette.
5. **Stage d** materials → G11-G13 + J3 (back-lit sunset).
6. **Stages e-h** wind data, UCX, QA, export. **Before stage h,** land the pipeline changes in 4.12 (UV0 overlap
   skip, `_sss` data suffix, `make_ucx_hull_from_points`) with `test_pipeline.py` and `test_qa_negative.py` passing.
   They touch the shared pipeline, so coordinate with the other chats first.
7. **Stage i** DojoLab (landscape round, after round 8 releases it) → J4 + G18. One fix round, then the final judge.

### 8.9 Open decisions for the user

- Which four panels (8.2), and whether 2 variants per pine are needed after seeing the Unreal cost.
- Whether to pilot Route B (Nanite Foliage + Dynamic Wind) at all. It needs PVE and DynamicWind enabled in DojoLab.
- Whether the pines should also become a Fab product. That adds the Route C card LOD chain, the AI-reference
  disclosure, and CC0 bark provenance.
- The gameplay trace rules in 5.7: do canopies block AI sight (Visibility), and is hiding in a tree a feature (a
  concealment volume) now or later?

---

## 9. Sources and uncertainties

### 9.1 Sources

**Botany and tree craft**
1. [Lehnebach et al., The pipe model theory half a century on (Annals of Botany 2018)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5906905/)
2. [Sone et al., Leonardo da Vinci's rule and the pipe model (J Plant Res 2009)](https://link.springer.com/article/10.1007/s10265-008-0177-5)
3. [Scaling in branch thickness and the fractal aesthetic of trees (PNAS Nexus 2025)](https://academic.oup.com/pnasnexus/article/4/2/pgaf003/7996468)
4. [Prusinkiewicz & Lindenmayer, The Algorithmic Beauty of Plants, ch. 2](https://algorithmicbotany.org/papers/abop/abop-ch2.pdf) and [ch. 4](https://algorithmicbotany.org/papers/abop/abop-ch4.pdf)
5. [Runions, Lane, Prusinkiewicz, Modeling Trees with a Space Colonization Algorithm (2007)](https://algorithmicbotany.org/papers/colonization.egwnp2007.large.pdf)
6. [Palubicki et al., Self-organizing tree models (SIGGRAPH 2009)](https://algorithmicbotany.org/papers/selforg.sig2009.html)
7. [SpeedTree docs, Branch Intersections](https://docs.speedtree.com/doku.php?id=branchintersections)
8. [Branch collar (Wikipedia)](https://en.wikipedia.org/wiki/Branch_collar); [root flare (Illinois Extension)](https://extension.illinois.edu/blogs/garden-scoop/2021-08-27-tree-root-collar-disorders)
9. [Weber & Penn, Creation and rendering of realistic trees (SIGGRAPH 1995)](https://dl.acm.org/doi/10.1145/218380.218427)
10. [Sousa, Vegetation Procedural Animation and Shading in Crysis (GPU Gems 3, ch. 16)](https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-16-vegetation-procedural-animation-and-shading-crysis)
11. [Sanders, The Vegetation of Horizon Zero Dawn (GDC 2018 slides)](https://media.gdcvault.com/gdc2018/presentations/gilbert_sanders_between_tech_and.pdf)
12. [PlayStation Blog, Crafting the world of Tsushima](https://blog.playstation.com/2020/07/09/crafting-the-world-of-tsushima/); [Rockenbeck, Simulating Wind in Ghost of Tsushima (GDC 2021)](https://gdcvault.com/play/1027124/Blowing-from-the-West-Simulating)
13. [SpeedTree docs, Spine Generator](https://docs.speedtree.com/doku.php?id=spine_generator); [Generators](https://docs.speedtree.com/doku.php?id=generators)
14. [Polycount, Best Practices for Creating 3D Trees for Games](https://polycount.com/discussion/98091/best-practices-for-creating-3d-trees-for-games) [S]
15. [Weinbaum, Art Tips for Building Forests (Game Developer)](https://www.gamedeveloper.com/art/art-tips-for-building-forests)
16. [Shinsoj, PBR colour space conversion and albedo chart](https://shinsoj.artstation.com/blog/Q9j6/pbr-color-space-conversion-and-albedo-chart) [S: 403 on fetch; values via a search summary]
17. [Golus, Anti-aliased Alpha Test: The Esoteric Alpha To Coverage](https://medium.com/@bgolus/anti-aliased-alpha-test-the-esoteric-alpha-to-coverage-8b177335ae4f)
18. [Pinus thunbergii (Wikipedia)](https://en.wikipedia.org/wiki/Pinus_thunbergii); [NC State plant toolbox](https://plants.ces.ncsu.edu/plants/pinus-thunbergii/)
19. [Gymnosperm Database, Pinus thunbergii](https://www.conifers.org/pi/Pinus_thunbergii.php)
20. [Bonsai aesthetics (Wikipedia)](https://en.wikipedia.org/wiki/Bonsai_aesthetics)
21. [Stava et al., Inverse Procedural Modelling of Trees (CGF 2014)](https://onlinelibrary.wiley.com/doi/abs/10.1111/cgf.12282)
22. [Niwaki, Mid-winter momiage](https://www.niwaki.com/mid-winter-momiage); [Pine workshop](https://www.niwaki.com/pine-workshop/)
23. [RHS, Cloud pruning](https://www.rhs.org.uk/plants/types/trees/cloud-pruning); [Promesse de fleurs, Cloud pruning or niwaki](https://www.promessedefleurs.ie/gardening-tips/advicesheet/cloud-pruning-or-niwaki/)
24. [Japanese Gardens, Midoritsumi and momiage pruning pines](https://japanesegardens.jp/2018/06/15/midoritsumi-and-momiage-pruning-pines/)
25. [SpeedTree docs, Real-Time Modeling tips](https://docs.speedtree.com/doku.php?id=real-time_modeling_tips)
26. [SpeedTree docs, Leaf Map Maker](https://docs.speedtree.com/doku.php?id=leaf_map_maker); [Thoughts from the developers](https://docs.speedtree.com/doku.php?id=thoughts_from_the_developers)
27. [SpeedTree (Unity docs), Games wind](https://docs.unity3d.com/speedtree-modeler/manual/wind-games.html); [Wind Wizard](https://docs.speedtree.com/doku.php?id=windwizard)
28. [SpeedTree (Unity docs), Texel density solutions](https://docs.unity3d.com/speedtree-modeler/manual/texel-density-solutions.html)
29. [Polycount, Making proper conifers with SpeedTree](https://polycount.com/discussion/107617/making-proper-conifers-with-speedtree-default-textures-looks-terrible); [SpeedTree conifers thread](https://polycount.com/discussion/228579/speedtree-any-speedtree-gurus-here-conifers) [S]
30. [ArtStation, Realistic game-ready pine tree models](https://www.artstation.com/artwork/dyl1J3) [S]
31. [80.lv, Building Pine Flatwoods in UE4](https://80.lv/articles/building-pine-flatwoods-in-ue4)
32. [80.lv, Impostor Baker for UE4](https://80.lv/articles/impostor-baker-for-ue4)
33. [CD Projekt Red, Witcher 4 UE5 tech demo](https://www.cdprojektred.com/en/blog/149/working-with-epic-to-debut-the-witcher-4-unreal-engine-5-tech-demo-at-unreal-fest); [Large Scale Animated Foliage in The Witcher 4 (talk)](https://www.youtube.com/watch?v=EdNkm0ezP0o)
34. [Quixel, Megascans and Megaplants on Fab](https://quixel.com/news/quixel-on-fab-new-megascans-and-megaplants)

**Unreal Engine**

35. [Epic, Nanite Foliage (5.8)](https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-foliage)
36. [Epic, Nanite Assemblies](https://dev.epicgames.com/documentation/unreal-engine/nanite-assemblies)
37. [Epic, Procedural Vegetation Editor](https://dev.epicgames.com/documentation/unreal-engine/procedural-vegetation-editor-in-unreal-engine?lang=en-US)
38. [Epic, UE 5.8 release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes)
39. [Epic, Nanite virtualized geometry](https://dev.epicgames.com/documentation/unreal-engine/nanite-virtualized-geometry-in-unreal-engine); [Nanite technical details](https://dev.epicgames.com/documentation/unreal-engine/nanite-technical-details)
40. [Epic, ISM component](https://dev.epicgames.com/documentation/en-us/unreal-engine/instanced-static-mesh-component-in-unreal-engine)
41. [Epic, Virtual Shadow Maps](https://dev.epicgames.com/documentation/unreal-engine/virtual-shadow-maps-in-unreal-engine)
42. [Epic, Lumen technical details](https://dev.epicgames.com/documentation/unreal-engine/lumen-technical-details-in-unreal-engine)
43. [Epic, Lumen performance guide](https://dev.epicgames.com/documentation/unreal-engine/lumen-performance-guide-for-unreal-engine)
44. [Epic, Overview of Substrate materials](https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-substrate-materials-in-unreal-engine); [Shading models](https://dev.epicgames.com/documentation/en-us/unreal-engine/shading-models-in-unreal-engine)
45. [Epic, UE 5.7 is now available](https://www.unrealengine.com/news/unreal-engine-5-7-is-now-available)
46. [Epic, Pivot Painter Tool 2.0](https://dev.epicgames.com/documentation/en-us/unreal-engine/pivot-painter-tool-2.0-in-unreal-engine)
47. [Epic, WPO material functions (SimpleGrassWind)](https://dev.epicgames.com/documentation/en-us/unreal-engine/world-position-offset-material-functions-in-unreal-engine)
48. [Epic forum, Foliage in current version and forward looking (Epic staff)](https://forums.unrealengine.com/t/foliage-in-current-version-and-forward-looking/2685424)
49. [Epic, FBX static mesh pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine); [forum: one vertex-colour set](https://forums.unrealengine.com/t/is-there-a-way-to-import-multiple-vertex-color-sets/291637)
50. [Epic forum, Dynamic wind system questions (Epic staff)](https://forums.unrealengine.com/t/dynamic-wind-system-questions/2698278)
51. [obilang/UE_NaniteDynamicWindData (JSON wind import)](https://github.com/obilang/UE_NaniteDynamicWindData)
52. [Epic forum, Nanite voxelization holes (Separable fix)](https://forums.unrealengine.com/t/nanite-voxelization-holes-in-the-mesh/2723578) [S]
53. [Epic forum, Nanite displacement bugged in the exact same landscape in 5.8 but not 5.7](https://forums.unrealengine.com/t/nanite-displacement-bugged-in-exact-same-landscape-in-ue-5-8-but-not-in-ue-5-7/2739815) [S: a user report about landscape displacement with tessellation, 5.8 and 5.8.1, no Epic reply]
54. [Class Central summary of the Witcher 4 foliage talk](https://www.classcentral.com/course/youtube-large-scale-animated-foliage-in-the-witcher-4-unreal-engine-5-tech-demo-unreal-fest-stockholm-2025-505458) [S]
55. [Epic tech blog, Bringing Nanite to Fortnite BR Chapter 4](https://www.unrealengine.com/en-US/tech-blog/bringing-nanite-to-fortnite-battle-royale-in-chapter-4); [Virtual Shadow Maps in Fortnite Chapter 4](https://www.unrealengine.com/tech-blog/virtual-shadow-maps-in-fortnite-battle-royale-chapter-4) [S: 403 to the fetcher; content via search summaries]
56. [Tom Looman, UE 5.8 performance highlights](https://tomlooman.com/unreal-engine-5-8-performance-highlights/); [UE 5.7](https://tomlooman.com/unreal-engine-5-7-performance-highlights/) [S]
57. [Shinsoj, Notes on foliage in Unreal 5](https://medium.com/@shinsoj/notes-on-foliage-in-unreal-5-3522b6eb159f) [S]
58. [nhance, Next-Gen Foliage: Nanite in UE 5.4](https://nhance-school.com/articles/ue5-nanite-foliage) [S]
59. [StraySpark, HISM vs ISM explained](https://www.strayspark.studio/blog/hism-vs-ism-unreal-engine-explained) [S]
60. [Epic community, Two Sided Foliage shading model](https://dev.epicgames.com/community/learning/tutorials/o8x/unreal-engine-shading-models-part-3-two-sided-foliage-using-two-sided-foliage-to-simulate-a-translucent-subsurface-effect); [80.lv, Getting the best of Megascans in UE4](https://80.lv/articles/getting-the-best-of-megascans-in-ue4) [S]
61. [Fab, Megaplants: Japanese Cypress](https://www.fab.com/listings/0843f3cf-41c1-4980-b46a-3df5742ddaef); [Megaplants: Yoshino Cherry](https://www.fab.com/listings/97f6cdb0-810d-470d-9e3a-3c9f059e6763)

**Blender**

62. [Blender Extensions, Space colonization tree generator](https://extensions.blender.org/add-ons/space-colonization-tree-generator/)
63. [Blender Studio, Geometry Nodes from Scratch: Tree Generator](https://studio.blender.org/training/geometry-nodes-from-scratch/example-tree-generator/)
64. [IRCSS, Trees with Geometry Nodes](https://github.com/IRCSS/Trees-With-Geometry-Nodes-Blender)
65. [Blender 5.0 Geometry Nodes release notes](https://developer.blender.org/docs/release_notes/5.0/geometry_nodes/); [5.2](https://developer.blender.org/docs/release_notes/5.2/geometry_nodes/) [403 to the fetcher; node names verified by probe]
66. [Sapling Tree Gen extension](https://extensions.blender.org/add-ons/sapling-tree-gen/); [5.2 fork v0.4.0](https://github.com/meet-brad-ch/add_curve_sapling/releases/tag/v0.4.0)
67. [Modular Tree extension](https://extensions.blender.org/add-ons/modular-tree/); [GitHub](https://github.com/MaximeHerpin/modular_tree)
68. [Blender Extensions review page, Modular Tree](https://extensions.blender.org/add-ons/modular-tree/reviews/)
69. [lukasreznicek/PivotPainter2](https://github.com/lukasreznicek/PivotPainter2); [Gvgeo/Pivot-Painter-for-Blender](https://github.com/Gvgeo/Pivot-Painter-for-Blender)
70. [Yarsa DevBlog, Transferring normal data in Blender](https://blog.yarsalabs.com/normal-transfer-in-blender/); [UE forum, Spherical normals for trees](https://forums.unrealengine.com/t/spherical-normals-for-trees-blender/98732)
71. [3D Skill Up, Tree bark UV workflow](https://3dskillup.art/tree-bark-textures-blender-uv-workflow/); [Polycount, tree texturing question](https://polycount.com/discussion/74330/real-quick-tree-texturing-question)
72. [Atlas Bake documentation](https://johndelta.github.io/atlas_bake_documentation/); [Blender Artists, Baking vegetation to a texture atlas](https://blenderartists.org/t/baking-vegetation-models-to-plane-texture-atlas/1419574)
73. [Phyllotaxis (Wikipedia)](https://en.wikipedia.org/wiki/Phyllotaxis); [Honda 1981, branch interaction](https://harvardforest1.fas.harvard.edu/publications/pdfs/Honda_AmJBotany_1981.pdf)

**Licensing and open world** (added 2026-09-30)

74. [Fab Standard License](https://www.fab.com/eula) [S: the page is behind a bot check for the fetcher; the clause "may not distribute content on a standalone basis to third parties except to your collaborators" came via search summaries]; [Epic, Licenses and pricing in Fab](https://dev.epicgames.com/documentation/en-us/fab/licenses-and-pricing-in-fab)
75. [Epic, World Partition: Hierarchical Level of Detail](https://dev.epicgames.com/documentation/en-us/unreal-engine/world-partition---hierarchical-level-of-detail-in-unreal-engine)
76. [Epic forum, 5.7.3 World Partition Nanite HLOD visualisation issue](https://forums.unrealengine.com/t/5-7-3-hlod/2711859) [S]

**Local evidence (read-only) [M]:**
- UE 5.8.3 engine source and plugins: `Engine/Plugins/Experimental/{DynamicWind,ProceduralVegetationEditor}`,
  `EngineTypes.h` (`ENaniteShapePreservation` l.3266, `bLerpUVs` comment ~l.3290, `bSeparable` l.3306),
  `Material.cpp`, `FoliageType.h`, `NaniteDefinitions.h` (`NANITE_MAX_UVS 4`),
  `Renderer/Private/{Lumen,VirtualShadowMaps,Nanite}`, `Shaders/Private/Nanite/NaniteRasterizer.usf` (voxel
  `ClusterTraceBricks`, no WPO), `PostProcess/TemporalSuperResolution.cpp` (`r.TSR.ThinGeometryDetection*`),
  `Editor/UnrealEd/Private/Fbx/FbxStaticMeshImport.cpp` (vertex colour conversion, l.946-952),
  `Config/BaseEditorPerProjectUserSettings.ini` (static `VertexColorImportOption=Ignore`), the PP2 material
  function names in `Content/Functions/Engine_MaterialFunctions02/`, `PCGSkinnedMeshSpawner.h`, and the USDCore
  `schema.usda`.
- The Megaplants files, names and sizes only: `DemoGame_1/Content/Megaplant_Library`,
  `VaultCache/Megaplan1093c7601c36V1` and `Megaplanb3dc3e6c5a59V1`.
- DojoLab and DemoGame_1 `DefaultEngine.ini` and `.uproject`.
- Blender 5.2.0 LTS API probes: GN nodes, bake enums, FBX options, and a UV and colour round trip.
- `Scripts/pipeline/*` (`qa_check.py` l.71 `DATA_SUFFIXES`, l.228-276 `uv_overlap_sat`, `COINCIDENT_DISTANCE`;
  `helpers.py` l.270 `make_ucx_hull`; `textures.bake_ao` on the active UV map; `export_fbx.py` helper-children
  warning), `ASSET_GUIDELINES.md`, `WorkFiles/dojo/DOJO_QUEUE.md`, `CINEMATIC_LOOK_RESEARCH.md`.

### 9.2 Uncertain for these versions (verify before relying on it)

**Unreal 5.8:**
- Nanite Foliage, Nanite Assemblies, Nanite Voxels, skeletal Nanite, Dynamic Wind (v0.1) and PVE are all
  **Experimental**. 5.7 PVE assets don't load in 5.8, and the architecture may change again.
- Whether a Blender FBX goes through PVE Import/Extract From Mesh into Nanite Foliage with Dynamic Wind without
  changing the silhouette. Also whether a plain static mesh with Voxelize looks acceptable without assemblies.
- The headless Dynamic Wind JSON import: the Blueprint function opens a file dialog, so it needs a C++ helper or a
  manual step.
- How `ConvertPivotPainterTreeToSkeletalMesh` behaves on our data (it needs empty target assets).
- The Blender USD → Unreal skeletal Nanite assembly path (the schema exists in 5.8.3; it needs a `pxr`
  post-process). Untested.
- Nanite displacement on static meshes in 5.8.3: untested. The only report [53] is about landscape displacement on
  5.8 and 5.8.1. Bark relief is geometry anyway (house rule).
- **`bLerpUVs` off on the foliage mesh:** whether Nanite then keeps the PP2 index intact, whether needle textures
  swim, and how LOD selection changes without UV error (G19). The Python spelling of the field.
- **WPO on voxels:** the source reading says voxel clusters never evaluate WPO. Confirm in the Evaluate WPO view,
  measure where voxels take over for each tree, and check whether Route B's skinned voxels follow their bones.
- **PP2 encoding:** that `PivotPainter2FoliageShader` decodes "Int as float" by default, that the EXR writer keeps
  half-float subnormals, and the X-extent scale in `ms_PivotPainter2_Decode8BitAlphaAxisExtent`.
- The texture compression that keeps the 8-bit PP2 XVector values exact.
- Complex traces against the Nanite fallback mesh: whether trunk limbs survive the fallback at the chosen error.
- World Partition HLOD Instancing layers on Nanite Voxelize meshes; PCG runtime generation in 5.8; all the
  open-world budgets in 5.11.
- Whether a Substrate Two-Sided Wrap slab counts as foliage for TSR thin-geometry detection.
- The real masked vs opaque Nanite raster cost on the user's GPU (the "+20-30%" figure is secondary).
- Whether a Substrate Two-Sided Wrap slab counts as a Lumen "foliage pixel".
- Whether DojoLab's Lumen runs HWRT or SWRT, and how Route B trees look in each.
- The exact texture settings that preserve alpha coverage in mips for masked foliage.
- The Unreal Python spellings for the Nanite settings enums and the component properties in 4.13 and 5.5.
- The PP2 material functions' UV index input in 5.8, and the pivot axis and unit convention (cm, Y flip). Test
  with a one-vertex mesh.
- FBX vertex colours: the static import default is Ignore and the importer decodes RGB as sRGB (both [M] from
  source). Still unverified end to end: the ramp round trip with Replace on.
- A deliberate Nanite fallback setting for trees under hardware RT.
- All budget numbers in 5.9: proposals until measured.
- The "Lumen Lite" setting name and cost in 5.8.3.

**Blender 5.2:**
- Data Transfer (Custom Normals) and Normal Edit (Radial) behaviour, and whether custom split normals survive
  `mesh_smooth_type="FACE"` into Unreal.
- There is no native alpha bake type (verified). The EMIT-based opacity bake is untested in our pipeline.
- `normal_g="NEG_Y"` bake against `flip_normal_green`: pick one and test for a double flip.
- SDF-weld quality and UV re-projection at junctions.
- Sapling (extension 0.3.7; a fork claims 5.2) and Modular Tree (lists 4.3.1-5.1) are untested on 5.2 headless.
- That the FBX exporter's `colors_type="SRGB"` converts linear float colour attributes to sRGB and leaves alpha
  linear.
- That `bake_ao` with UV2 active bakes cleanly to the unique trunk UV, and the cost of a per-vertex canopy AO
  ray-cast (`BVHTree`) on 150-250k foliage triangles.
- The runtime of qa_check's UV1 SAT test on a 250k-triangle foliage mesh.

**Pipeline changes this study asks for (not yet made):** the `uv0_overlap` skip in `qa_check`, `_sss`/`_thk` in
`DATA_SUFFIXES`, `helpers.make_ucx_hull_from_points`, and `pipeline/pivot_painter.py`. Each needs
`test_pipeline.py` and `test_qa_negative.py` re-run.

**Data:**
- Megaplants texture packing (`_CA`, `_NT`, `_NAH`) is inferred from file names only.
- The albedo chart values (conifer 0.08-0.12 linear) come from a search summary of a blocked page. Cross-check them
  before using G11 as a hard gate.
- The Witcher 3 pine-card technique and the "spruce needles as fronds" tip are forum claims.
- The botany numbers come from consistent web summaries (conifers.org, NCSU). Cross-check before hard-coding.
- The reference colours are from a rendered, lit image: look targets, not albedo.
- The reference measurements have uncalibrated pad counts, M1 needs a hand trace, and the 1.75 m figure is an
  assumption.
- Several SpeedTree pages returned 403 to WebFetch and were read via curl with a browser user agent. The content
  matched the doc pages.
