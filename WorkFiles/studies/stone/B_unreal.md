# Stone study B: stone, masonry and rocks in Unreal Engine 5.8

Research phase, 2026-09-30. This is one of the research notes for the durable stone study (the root
`STONE_BUILDING_STUDY.md` to come). It covers what Unreal 5.8 needs from **every** future stone asset: dressed and rough
masonry walls (ishigaki nozura-zumi / uchikomi-hagi / kirikomi-hagi, dry-stone, rubble, ashlar), steps, paving and
kerbs, footings, stone lanterns and carved stone, and natural rocks and boulders (river boulders, cliff rocks, rocks that
trees grow from). The first clients are the dojo stone kit rebuild (`SM_DKT_*`) and the D-pine rock.

It is the Unreal half. How to *shape* stone (the craft) and how to *build* it in Blender 5.2 are the sibling notes; this
note only says what the geometry must carry for Unreal, and what Unreal can add on top.

**Evidence tags.** [M] = measured on this PC, read-only: the installed engine (UE **5.8.3**, CL 58210709,
`Engine/Build/Build.version`) and its source headers, plugin files and engine content; DojoLab's `Config/DefaultEngine.ini`
and our own earlier read-only reports; owned content file names, sizes and asset-registry tags. [D] = Epic documentation.
[S] = secondary source (forum, blog, tutorial). [U] = uncertain for 5.8, still to verify in Unreal. No Unreal project was
opened or modified, no commandlet was run, and no MCP tool was used.

---

## 0. Summary

1. **Unreal cannot rescue a stone's form; it can only finish it.** Our evidence says the judges score *shape* first
   (pillow rubble "closest piece to its sheet"; the pine boulder "a faceted block"; the f1 wall's "uniform pillows").
   Nanite makes real geometry nearly free to render, so every stone form (outline, crown, arris, chips, joint depth)
   belongs in the mesh. Unreal adds the parts that are **scale- and placement-dependent**: macro tone variation, moss by
   exposure, wetness, the ground seam, and the distance behaviour.
2. **Nanite for all stone above about 2k triangles, opaque, Shape Preservation `None`.** [D][M] Rocks and masonry are
   Nanite's best case: dense, opaque, static, heavily instanced, strong occluders. Author **smooth normals** and few UV
   seams: Epic wants vertices < triangles (ratio well under 2:1; 3:1 means fully faceted and is expensive). [D] The owned
   scanned rocks sit at 0.59-0.60 vertices per triangle. [M]
3. **Displacement exists in two forms in 5.8, and they are different tools.** [M]
   - **Build-time displacement** (`FMeshNaniteSettings.DisplacementMaps`): the Nanite builder tessellates and displaces
     the mesh once, at import/build, along vertex normals. No runtime cost beyond the extra triangles. Needs
     `TrimRelativeError != 0` and a single-LOD source. [M: `NaniteBuilder.cpp`, `NaniteDisplace.cpp`]
   - **Runtime tessellation** (material `bEnableTessellation` + Displacement output): on by default in 5.8
     (`r.Nanite.Tessellation=1`, scalability; the 5.4-era `r.Nanite.AllowTessellation` project gate **no longer exists**
     in 5.8 source). Costs programmable raster every frame. [M]
   - **Neither is crack-free across UV seams or hard edges** [D], so neither suits squared blocks, arrises or joints.
     Use them for micro-relief on rounded natural rock and ground, never as the method that makes a masonry form
     (the height-field lesson in CLAUDE.md, again).
4. **Materials: one stone master family, single Substrate slab.** DojoLab runs Substrate with the **Blendable GBuffer**
   (one closure per pixel) [M], so moss, wetness and dirt are *parameter-blended into one slab*, not layered. The master
   combines: base maps (UV0 for masonry, triplanar for round stone), a tiling **detail normal**, world-space **macro
   variation**, a **per-actor / per-instance tone hash**, **moss** from world-up exposure x joint/occlusion mask x height
   lerp, **wetness** (water level and rain), and an optional **RVT ground blend** at the foot. We already have most of
   these pieces in `Scripts/dojo/unreal/dj_sc_materials.py`. [M]
5. **Nanite components cannot be vertex-painted per instance** ("Don't vertex paint on nanite", measured in 5.8
   `StaticMeshComponent.cpp`). Per-asset vertex colours from the FBX *do* work, and 5.8 supports **texture-colour mesh
   painting** (Mesh Paint Virtual Texture, `r.MeshPaintVirtualTexture.Support=1`). Per-placement variation therefore
   comes from the position hash, `PerInstanceRandom` / Per-Instance Custom Data, decals, or mesh-paint textures. [M]
6. **Collision is simple by default; GASP needs markers.** Measured 5.8.3 GASP facts [M: our `GASP_TRAVERSAL.md`]:
   a plain mesh is **never** traversed (the hit actor must be a `LevelBlock_Traversable`); mantle ≤ 275 cm; hurdle and
   vault ≤ 125 cm over ≤ 59 cm deep; a top sloped more than about 2° fails the mantle; 10-50 cm cover is dead;
   MaxStepHeight 45 cm; walkable 44.77°. So every climbable wall top and rock top needs a **flat collision top ≥ 0.5 m
   deep** plus a traversal marker, whatever the render mesh does.
7. **Complex collision for a Nanite mesh is its fallback** (`LODForCollision` indexes the render LODs, and LOD0 of a
   Nanite mesh is the fallback [M]). Our pipeline's "fallback RELATIVE_ERROR 0" (set for the bounds gate) therefore makes
   any complex collision full-resolution. `UStaticMesh.ComplexCollisionMesh` exists in 5.8 to point complex collision at
   a separate low mesh. [M]
8. **Placement:** hand-placed or Packed Level Actor modules on the kit grid for masonry; **PCG** for rubble, boulders and
   river stones (Surface Sampler, Self Pruning, Difference, slope/height filters, embed offset) and for
   **spline-driven walls** (Spline Sampler or the shape-grammar Subdivide Spline nodes, all in 5.8 PCG [M]). With Nanite,
   ISM is enough (no HISM benefit). [S]
9. **Battle-royale scale:** Nanite handles per-object detail; **World Partition HLOD** handles region-level cost at
   distance (Instancing for rubble ISMs, Simplified/Approximated Mesh for wall runs and cliffs). Keep the **unique rock
   mesh count low** (Lumen and memory scale with unique meshes, not instances). Mesh Terrain (5.8, Experimental) can do
   overhangs and cliffs as terrain, but is a prototype tool. [D][S][M]
10. **Scanned rocks mix with our masonry through the shared master, not by eye.** Pipe Megascans / Fisherman's Cabin
    rocks' *unique normal and cavity* into our stone master and replace or tint their albedo toward our measured granite;
    share detail normal, macro variation, moss, wetness and RVT blend parameters. **License:** Fab/Megascans content can
    ship inside the game, **never inside a Fab product** of ours. [S: Fab Standard License]

---

## 1. What is on this PC (read-only inspection)

### 1.1 Engine and project state [M]

| Item | Value | Source |
|---|---|---|
| Engine | 5.8.3, CL 58210709 | `Engine/Build/Build.version` |
| GPU | NVIDIA GeForce RTX 4070 SUPER | round 8/9 DojoLab logs |
| DojoLab Nanite | `r.Nanite.ProjectEnabled=True`, `r.Nanite.Foliage=True` (this also turns on Nanite Assemblies and Voxels, see the tree study) | `DefaultEngine.ini` |
| Substrate | `r.Substrate=True`, `r.Substrate.ProjectGBufferFormat=0` (**Blendable**, one closure per pixel) | same |
| Lumen | GI + reflections Lumen; runtime cvar dump shows **`r.Lumen.HardwareRayTracing=1`** | `round8/s1_work/start_backup/json/perf.json` |
| Ray tracing | `r.RayTracing=True`, **`r.RayTracing.RayTracingProxies.ProjectEnabled=True`** (read-only, "whether ray tracing proxies are generated by default for this project") | ini + `RenderUtils.cpp:59` |
| Distance fields | `r.GenerateMeshDistanceFields=True`, `r.Lumen.TraceMeshSDFs=1`, `r.DistanceFields=1` | ini + perf dump |
| Decals | `r.DBuffer=1`; 86 weathering decal actors, 6 decal materials | perf dump |
| Shadows | VSM on; `r.Shadow.Virtual.ResolutionLodBiasDirectional=-1.5` | perf dump |
| Collision channels | `ECC_GameTraceChannel1` "Traversable" (default Ignore), profile `TraversalObjectPreset` | ini |
| Round 8 frame | GPU mean 8-14 ms (66-100 fps), p95 over 16.7 ms at 1440p | `DOJO_QUEUE.md` |

This resolves one open point of the tree study: **Lumen runs hardware ray tracing in DojoLab**, so what Lumen "sees" of
a stone mesh is its **ray-tracing representation** (RT proxy, else the Nanite fallback), not only its distance field.

### 1.2 The dojo scene as a stone budget reference [M]

From the round 8 pre-change perf snapshot (`perf.json`): 1,111 static mesh actors, 253 Nanite actors, 92 unique Nanite
meshes, **8.15 M Nanite source triangles placed**, of which the wall footing alone is **4.12 M** (35 x
`SM_DK_WallFooting_4m` at 117,657 triangles each) and the wall cap 1.06 M. The frame still ran 66-100 fps. The stone
kit extension adds 3.15 M (wall) + 0.68 M (stairs) triangles of LOD0 source per catalogue (`BUILD_NOTES.md`), the largest
pieces `StairOpening_H4` 386k and `Flight_W180_R200` 121k. Those numbers are well inside what Nanite streams comfortably;
the risk is disk and memory per *unique* mesh, not frame time. [M, inference]

### 1.3 Owned rock and stone content (names, sizes, asset-registry tags only) [M]

| Content | Where | What the tags say |
|---|---|---|
| **Nordic_Beach_Rocks** (Megascans 3D, UE 5.2 package) | `Documents/Unreal Projects/Scenery_Tutorial/Content/Megascans/3D_Assets/Nordic_Beach_Rocks_vckqccbga_3d/` | Nanite on; **19,132 Nanite triangles** / 10,469 vertices; fallback 5,383 tris / 3,205 verts; fallback percent 100; ApproxSize 1658 x 937 x 270 cm; DefaultCollision BlockAll; DF 1.1 MB; **1K** albedo and normal (≈ 0.6 px/cm on a 16.6 m rock) |
| Its material `MS_DefaultMaterial` (edited by the tutorial) | same folder | Albedo Tint / controls, Min/Max Roughness, Normal Strength, **Detail Normal** (tiling, rotation, strength), Specular from Albedo, `MF_Tiling`, `MF_MapAdjustments`, `MF_DetailNormalTiling`, `MF_Transmission`, and **`MF_VTGroundBlend`** (RVT ground blend) wired in |
| Megascans surfaces | `Scenery_Tutorial/Content/Megascans/Surfaces/` | BeachCliff (BC/N/Roughness/**Displacement**), MossyCreekStones, MossyRockyGround (4K D/N + DISPDISPLACE), ForestGround, MossyGrass, Snow |
| Scenery_Tutorial landscape toolkit | `Scenery_Tutorial/Content/Landscape/Materials/Functions/`, `Example/VirtualTextures/` | `MF_VTGroundBlend`, `MF_SlopeBlend`, `MF_TriplanarProjection(_Normal)`, `MF_CellBomb(Distance)`, `MF_BlendTexture`, `MF_Material_Triplanar`; `RVT_Height`, `RVT_Mat`; `T_MacroVariation` (10.6 MB), `T_NoiseMask_RGB`, `T_Voronoi_Perturbed_4k` |
| **Fisherman's Cabin rocks** (Fab, UE 5.2 package, launcher vault) | `C:/ProgramData/Epic/EpicGamesLauncher/VaultCache/NordicFi1d739256ce1cV1/data/Content/Fishermans_Cabin/Meshes/Rocks`, `/Small_Rocks` | `SM_Rocks_01..04`: **78.6-80.0k Nanite tris**, fallback 5.7-8.2k tris (verts/tris 0.59), 1.3-2.9 m; `SM_Small_Rocks_01..05`: 118-270 tris, 8-15 cm (Nanite on, BlockAll); `SMF_*` foliage types for them |
| Its rock master `M_Masked_Asset` / `MI_Rocks_01` | `.../Materials/Material_Masters` | **unique mask + unique normal per rock** (`T_Rocks_Mask`, `T_Rocks_N`) over a **tiling rock set** (`Tiling_Textures/Rock/T_Rocks_D/N/R/DP`), `MF_Triplanar_Mapping`, **Crevices Dirt** (colour, contrast, power, roughness, channel), **Detail Normal** with max distance and start offset, **World Aligned Noise Color Variation**, **Enable Toplayer Blend**, **Enable RVT Blend** (`RVT_Height`, `RVT_Material`), Blend Bias / Sharpness / Side Culling |
| Megaplants, Nordic Fisherman's Cabin, Ultra Dynamic Sky, Electric Dreams, GASP 5.8 | launcher vault | Electric Dreams is the Epic sample with large Nanite rock/cliff kits (not inspected further) [U] |

**Takeaway.** The two owned scanned rock sets reveal the production pattern that works: **unique normal + cavity/AO
mask per rock, tiling detail material on top, world-aligned colour noise, top-layer (moss/snow) blend, RVT ground
blend.** That is the same master we need for our own rocks, so scanned and custom rocks can share one material.

### 1.4 Engine material functions for stone (engine content, shipping) [M]

`Engine/Content/Functions/`:

| Function | Use for stone |
|---|---|
| `Engine_MaterialFunctions01/Texturing/WorldAlignedTexture`, `WorldAlignedNormal`, `WorldAlignedTexture_MipBias`, `_SeperateChannels`; `Engine_MaterialFunctions02/Texturing/WorldAlignedTexture_Complex`; `HighQualityWorldAlignedNormals` | triplanar for round stone, rocks, lantern caps; world-continuous masonry cores |
| `Engine_MaterialFunctions01/AlphaBlend/WorldAlignedBlend` | top-down moss / snow / dust mask from world normal |
| `Engine_MaterialFunctions01/Texturing/SlopeMask` | slope-based masks |
| `Engine_MaterialFunctions02/Texturing/HeightLerp`, `HeightLerpWithTwoHeightMaps` | moss creeping into crevices first (height-aware blend) |
| `Engine_MaterialFunctions01/Texturing/DetailTexturing` | detail diffuse + normal |
| `Engine_MaterialFunctions02/MacroUVs` | two-scale sampling against tiling |
| `Engine_MaterialFunctions03/Texturing/TextureVariation(_RotateUV/_RotateNormals)`, `Engine_MaterialFunctions01/Texturing/Texture_Bombing(_POM)` | anti-tiling on long walls and cliffs |
| `Engine_MaterialFunctions02/Utility/BlendAngleCorrectedNormals(_WS)` | combining base + detail normals correctly |
| `MaterialLayerFunctions/MatLayerBlend_*` | Material Layers route (see 4.6) |

---

## 2. Nanite for stone

### 2.1 When to use it, when not

- **Use Nanite** on every stone mesh that is dense (> ~2k tris), opaque, static and either repeated or a large occluder:
  wall modules, steps, footings, lanterns, boulders, cliffs. This matches the DOJO rule "Nanite for the props over about
  2k tris". [D][M]
- **Epic's own list of beneficiaries**: meshes with many triangles or tiny on-screen triangles, many instances, major
  occluders, and VSM shadow casters. Kitbash and sculpted geometry are named. [D]
- **Skip Nanite** for tiny low-poly pebbles that are far below 2k tris (they gain little) and for anything translucent.
  Nanite supports **Opaque and Masked** only; mesh decals are not supported on Nanite. [D]
- **Stone is never masked.** No alpha-cut moss cards on stone faces; moss is shading (or real geometry for cushions).

### 2.2 Authoring rules that change Nanite cost [D][M]

| Rule | Why | Our status |
|---|---|---|
| **Smooth normals, few hard edges** | "Low amounts of vertex sharing ... can become significantly more expensive both in rendering performance and data size." Vertex/triangle ratio should stay below 2:1; 3:1 = fully faceted. Hard-normal thresholds from the DCC add cost on dense meshes. [D] | `pillow_face` and `rough_block` are smooth-shaded (`fsm = True`) [M]. The pine rock "faceted masses ... chipped with 26 planes ... hulled" risks flat-shaded facets: check its ratio. |
| **Few UV seams** | seams split vertices (and break displacement, 3.3) | box UV per face (`BOX_UV_MATS`) creates a seam on every stone face boundary; fine for block masonry, but rounded rocks want one or few charts or triplanar |
| **Target ratio** | owned scanned rocks sit at **0.59-0.60** verts/tris [M] | add a Nanite gate to `qa_check`: verts/tris ≤ 1.0 warn, ≤ 2.0 hard (proposal; pipeline owner's call) |
| **Avoid near-coplanar stacked surfaces** | when layers are at almost the same depth Nanite cannot tell which is on top and draws both; imprecision grows with distance [D][S] | the kit's joint core recessed **8 cm** behind the faces is good; hidden stone backs buried deep are culled cheaply [S] |
| **Piles of small rocks:** merge (boolean/shrink-wrap) into one surface rather than stacking dozens of closed rocks | culling is per cluster; large hidden polygons cull poorly [S] | for rubble fields and cheek cores |
| **Don't import tiny then scale up** | distance-field resolution is fixed per mesh; a scaled-up rock gets a coarse SDF; raise *Distance Field Resolution Scale* in the build settings instead [D] | our pieces import at 1:1 |

### 2.3 How dense? A pixel-footprint rule instead of a triangle count

Nanite targets **1 pixel per triangle edge** (`r.Nanite.MaxPixelsPerEdge = 1.0`) [M]. Source detail finer than the
closest camera can resolve is wasted disk. For a 2560-px-wide view at 90° horizontal FOV, one pixel spans about
**d / 1280**: 0.8 mm at 1 m, 2.3 mm at 3 m (typical third-person distance to a wall), 8 mm at 10 m. [inference]

| Feature | Source edge length that is enough |
|---|---|
| Silhouette arrises, nosings, chipped edges, joint rims (read at 1-3 m) | **2-5 mm** segments along the edge |
| Stone crowns / pillow relief (normal map adds the rest) | **1-2 cm** |
| Buried backs, cores, undersides | as coarse as possible |
| Cliff faces seen from ≥ 10 m | 2-5 cm; micro detail from detail normal or build-time displacement |

Measured current densities: footing 4 m module 117,657 tris; Fisherman's rocks ~80k tris for 1.3-2.9 m boulders; the
16.6 m Nordic beach rock only 19k (it relies on its normal map and is soft up close). [M]

### 2.4 Nanite settings per stone mesh (`FMeshNaniteSettings`, 5.8) [M]

| Field | Stone setting |
|---|---|
| `bEnabled` | True |
| `ShapePreservation` | **`None`** (`PreserveArea` and `Voxelize` are foliage techniques) |
| `PositionPrecision` | auto (`MIN_int32`). Set explicitly only if hairline gaps appear where two modules abut (each mesh quantizes independently) [U]; the kit's interlocking teeth and recessed joint cores already hide module seams |
| `KeepPercentTriangles` / `TrimRelativeError` | 1.0 / 0.0 unless using build-time displacement (3.1), where Trim must be non-zero |
| `GenerateFallback`, `FallbackTarget`, `FallbackPercentTriangles`, `FallbackRelativeError` (default 1.0) | see 2.5 |
| `DisplacementUVChannel`, `DisplacementMaps[]` | build-time displacement (3.1) |
| `bExplicitTangents`, `bLerpUVs`, `NormalPrecision`, `TangentPrecision` | defaults |

`FMeshNaniteSettings` fields are BlueprintReadWrite, so the import script can set them from Unreal Python;
`DisplacementMaps` is EditAnywhere only (set via `set_editor_property` [U]).

### 2.5 Fallback, ray-tracing proxy, bounds, complex collision [M][D][S]

- **Three representations now exist** for a Nanite static mesh in 5.8:
  1. the Nanite data (rendering);
  2. the **fallback mesh** (`FallbackTarget` Auto / PercentTriangles / RelativeError) = the mesh's LOD0 render data,
     used for **complex collision** and non-Nanite paths;
  3. the **ray-tracing proxy** (`FMeshRayTracingProxySettings`: `bEnabled`, `FallbackTarget`, `FallbackPercentTriangles`,
     `FallbackRelativeError` **default 2.0**, `FoliageOverOcclusionBias`), used by hardware RT when the project enables
     RT proxies, which **DojoLab does**. [M] Epic notes that when fallbacks serve only RT, *Generate Nanite Fallback
     Meshes* can be turned off per platform to save memory, and RT proxies stream on demand. [S]
- **Bounds.** Measured round 2: a Nanite mesh's render bounds are the union of *every* DAG level's cluster boxes and sit
  **0.5-27.6 cm outside the real surface** whatever the fallback; with fallback RelativeError 0 the fallback equals the
  source (38/38 meshes). Our bounds gate measures the fallback's vertex box. [M: `dj_sc_nanite.py`]
- **Consequence for stone.** The DOJO fix "fallback RELATIVE_ERROR 0 on every Nanite mesh" was a *verification* choice.
  It ships full-resolution fallbacks: large CPU/GPU memory, and **full-resolution complex collision** if any piece uses
  complex-as-simple. Recommendation for the pipeline owner:
  - keep RE 0 only on the verification import (or measure bounds from the Blender box in the sidecar instead);
  - shipped stone: fallback **RelativeError 1** (default) or PercentTriangles 5-15 %; RT proxy default 2.0, lowered to
    ~1.0 only for hero rocks whose Lumen/RT shadow silhouette visibly drifts. [U: measure the look]
- **Complex collision source.** `GetPhysicsTriMeshData` clamps `LODForCollision` into the render LODs, i.e. the
  fallback on a Nanite mesh. `UStaticMesh.ComplexCollisionMesh` (EditAnywhere) lets complex collision use a separate,
  purpose-built low mesh instead. [M: `StaticMesh.h`, `StaticMesh.cpp`]

### 2.6 Nanite Assemblies and spline meshes for stone [M][D][U]

- **Assemblies** (`r.Nanite.AllowAssemblies`, read-only, default 0; on in DojoLab through `r.Nanite.Foliage=True`):
  micro-instanced parts inside one mesh. A wall laid from a **library of repeated stone units** could ship as an
  assembly (parts x transforms) instead of a merged mesh, cutting disk sharply. That only pays if stones repeat; our
  current walls lay a unique stone per slot. Worth a pilot if the Blender side moves to a "stone-unit library + layout"
  method. Assemblies are authored through the Nanite Assembly builder utilities or USD import (schema present in 5.8, see
  the tree study). [U: untested for static walls]
- **Nanite spline meshes** (`r.Nanite.AllowSplineMeshes`, read-only, default **1**). Use only for constant-section
  pieces (kerbs, copings, gutter channels). Never bend laid masonry along a spline: it stretches every stone.

---

## 3. Displacement and tessellation (5.8 status)

### 3.1 Build-time displacement: `DisplacementMaps` in the Nanite settings [M][D]

What the 5.8 source does (`NaniteBuilder.cpp PreprocessMesh`, `NaniteDisplace.cpp`):

- Runs only if `DisplacementMaps.Num() > 0` **and** the source has a single LOD **and** `TrimRelativeError != 0`.
- `TessellateAndDisplace` adaptively tessellates to a target error of
  `TrimRelativeError x 0.01 x sqrt(min(2 x surface area, bounds surface area))`, then moves each new vertex along the
  interpolated **vertex normal** by the map sampled at `DisplacementUVChannel`.
- **One map per material index** (`DisplacementMaps[MaterialIndex]`), each with `Texture`, `Magnitude`, `Center`.
- Vertex colours are carried through (so our `Wear` channels survive).
- Epic: set Trim Relative Error "other than 0", default 0.04, keep it above 0.02; keep Magnitude as small as needed;
  "there is currently no solution for crack-free displacement" at UV seams or hard edges. [D]

**Use:** micro-relief on rounded rocks and cliff faces from a height map (ours, or the owned Megascans displacement
maps for *game-only* content). The result is ordinary static Nanite triangles: no runtime tessellation, no VSM concern.
It is an alternative to baking the same relief in Blender; the Blender route keeps the geometry visible to our own
measurements and judges, so prefer it unless disk size forces the Unreal route. [inference]

### 3.2 Runtime tessellation: material displacement [M][D][S]

- Material: `bEnableTessellation` ("NOTE: Required for displacement to work"), `DisplacementScaling`
  (`Magnitude` default **4.0**, `Center` default **0.5**), optional `DisplacementFadeRange` (`StartSizePixels` >
  `EndSizePixels`: fade and disable displacement once it is too small on screen). [M: `Material.h`, `EngineTypes.h`]
- Engine: `r.Nanite.Tessellation` default **1** (scalability), needs programmable + compute raster;
  `r.Nanite.DicingRate` default **2 px** micropolygons; `r.Shadow.Virtual.Nanite.AllowTessellationDirectional/Local`
  (default 1; setting either to 0 forces the displacement fallback in shadows). **No `r.Nanite.AllowTessellation`
  project switch exists in 5.8 source**, unlike 5.4 guides. [M]
- Status: introduced as Experimental in 5.4 [S]; the 5.8 release notes announce no status change [D]. Treat as
  **not production-proven** for a Fab product. [U]
- Cost: every tessellated material runs the programmable raster path; Magnitude inflates culling bounds ("if the
  Magnitude is large it can have serious impacts on performance, especially with virtual shadow maps"). Static
  displacement does not invalidate VSM pages by itself, but *changing* displacement is not tracked by the cache. [S]
- Collision is **not** displaced (it comes from the fallback / UCX). A displaced rock top can float or sink feet by up
  to the magnitude. [inference]

### 3.3 Verdict for stone

| Stone type | Displacement? |
|---|---|
| Masonry blocks, ashlar, kerbs, steps, lantern parts (hard arrises, many UV charts) | **No.** Model the form; normal map for texture. Seams would crack. |
| Rubble / pillow faces | No: geometry already carries the crown and relief (`pillow_face`). |
| Natural boulders, river stones, cliff faces | Optional: **build-time** displacement for sub-centimetre relief if the Blender mesh is lighter; runtime only for a hero close-up, with a Fade range, magnitude ≤ 2 cm. |
| Ground around stone (gravel, soil) | Landscape / Mesh Terrain displacement is the natural home. |

---

## 4. Stone materials in Unreal 5.8

### 4.1 Architecture: one master family, instances per stone type

Proposed family (built as code in the dojo materials builder, under the PackMaterials lock when it touches the pack):

| Master | Mapping | For |
|---|---|---|
| `M_ST_Masonry` | UV0 base maps in tile units (the library's `box_uv`), plus world-space overlays | walls, steps, paving, kerbs, footings, carved stone with flat faces |
| `M_ST_RockUnique` | UV0 **unique** normal + cavity/AO (baked per rock), tiling detail on top | our sculpted rocks **and** scanned rocks (Megascans, Fisherman's Cabin) |
| `M_ST_Triplanar` | world-aligned (or local-aligned) triplanar | round stone (lantern caps, finials), rock cores, long cliff meshes |

They share one parameter vocabulary and one function stack (below), so a wall, a scanned boulder and our boulder can
be set to the same tone, moss and wetness by one MPC and a few instance values.

### 4.2 The function stack (all engine content or our existing code) [M][D]

1. **Base.** BC x Tint, lerp toward MeanColour by FlattenToMean (kit 1's rule), ORM, Normal with FlattenNormal. This is
   `lib_colour` / `lib_finish` in `dj_sc_materials.py`. [M]
2. **Detail normal** (tiling granite grain, 0.25-0.5 m tile) blended with `BlendAngleCorrectedNormals`, **faded by
   distance** (Fisherman's: "Detail Normal Max Distance", "Start Offset"). This is what makes 1K scanned albedo and our
   4 m granite tile hold up at 1 m. [M][D]
3. **Macro variation** in world space: large-scale (8-32 m) noise multiplying albedo and roughness, to break repeats
   along a 50 m terrace wall or a cliff. `T_MacroVariation` exists in Scenery_Tutorial; we already do this for ground
   (`T_DKG_Macro_M` on world XY / 32 m). [M]
4. **Per-piece tone.** Actors: the position hash we already use (`actor_hash`); ISM/PCG instances:
   `PerInstanceRandom` or Per-Instance Custom Data. Small (±5-10 % value, ±2° hue) so neighbouring modules differ.
   The kit's `stone_tone` already writes per-stone grime into vertex colours in Blender; the Unreal hash adds the
   per-*placement* layer on top. [M]
5. **Moss / lichen**, three masks multiplied:
   - **exposure**: world-up dot normal (`WorldAlignedBlend` or a `VertexNormalWS.z` smoothstep), biased by a world
     noise so it never forms a hard contour;
   - **occlusion / joints**: the Blender-baked vertex colour (kit rule: moss "only in the joints and on ledges, never as
     a tint across whole faces") or the rock's baked cavity map;
   - **height-aware**: `HeightLerp` against the stone's height/AO so moss fills crevices before crowns.
   Moss colour from the kit (`#56613A` linear 0.093/0.120/0.042); roughness up (0.85-0.95); normal flattened under moss.
6. **Wetness** (river boulders, rain, splash zone): albedo x 0.55-0.75 on porous stone, roughness toward 0.15-0.3,
   normal slightly flattened; masks from an **MPC water level** (a band a few cm to 0.5 m above the water plane, with
   noise), an MPC rain amount x exposure, and decals for streaks (section 5). [inference; standard practice]
7. **Ground seam (RVT blend)** for stones that sit in terrain: sample the landscape RVT (BaseColor/Normal/Roughness +
   World Height) and blend the bottom band of the stone into the ground by height difference. The owned
   `MF_VTGroundBlend` and Fisherman's "Enable RVT Blend" do exactly this. [M][D]
8. **Look** (our `G.look()`: Saturation, ValueMult, TopBleach) last, so the Unreal chroma gain measured in the look
   passes is corrected in one place. [M]

### 4.3 Vertex colours: what the FBX must carry [M]

- Nanite keeps **imported** vertex colours; import with vertex colour **Replace** (materials README). [M]
- The dojo convention on stone: the `Wear` layer (R grime, G edge wear, B dirt) and **A = moss** (`lib_colour` moss by
  VertexColor.A). Keep it. Stone uses Shape Preservation None, so the Voxelize "alpha overwritten" caveat does not apply.
- The exporter writes `colors_type="SRGB"`: masks are gamma-encoded on the way. Verify one known 0.25/0.5/0.75 ramp
  through a debug material before trusting mask thresholds in Unreal. [U, as in the tree study]
- **Per-instance vertex painting is off on Nanite components** (`StaticMeshComponent.cpp`: "Don't vertex paint on
  nanite"). For hand-touched moss/dirt on a placed wall, use **Mesh Paint textures** (`CanMeshPaintTextureColors`,
  `r.MeshPaintVirtualTexture.Support` default true; the mesh needs a paint UV and texture resolution, overridable per
  component) or decals. [M] How our master reads the paint texture (the Mesh Paint Texture material node) is [U].

### 4.4 Triplanar and world-aligned mapping: when

- **UV0 (box UV in tile units)** for all block masonry. It is cheapest, keeps each stone's texture unmirrored, and the
  library's `space='WORLD'` option keeps neighbouring pieces continuous. [M]
- **Triplanar** (3 samples per map; ~3x texture cost) for round stone, rock cores and cliff meshes too big for a unique
  UV. `WorldAlignedTexture` swims when the rock moves or rotates, so for rocks placed with random yaw use a
  *local-space* (object) triplanar, or bake UVs. Our materials README already says "Round stone ... in Unreal,
  WorldAlignedTexture". [M][inference]
- **Normals in triplanar** need `WorldAlignedNormal` / `HighQualityWorldAlignedNormals` (the DirectX tangent maps must
  be reoriented per projection); `dj_sc_materials.triplanar_normal_ws` already implements this. [M]

### 4.5 Substrate in DojoLab (Blendable GBuffer) [M][D]

- **One closure per pixel.** A material that exceeds it is simplified automatically; haziness, glint, F90 and
  per-pixel-MFP SSS are "visually missing". [D]
- So stone + moss + wet must be **one Slab** whose inputs are lerped (the material-attribute / parameter-blend way), or
  Substrate operators with **"Use Parameter Blending"** on (which "merges multiple slabs into a single slab"). A true
  Vertical Layer (e.g. a water film coat over stone) is not available in Blendable. [D]
- Useful slab inputs for stone: Roughness, Specular (F0 ≈ 0.04 for rock: keep the default), **Fuzz** (a hint of fuzz
  on moss gives the soft backlit rim at low sun; fuzz is among the features Blendable keeps [D]) [U: verify look and cost].
- Author with Slab nodes; the legacy shading-model conversion also works (DefaultLit → slab). [D]
- Substrate still carries Epic's "features and UX are subject to change" caveat. For a Fab stone pack, ship legacy-
  compatible masters (Substrate converts them) rather than Substrate-only graphs. [D][inference]

### 4.6 Material Layers?

Material Layers (the `MaterialLayerFunctions` blends) give an artist-friendly stack (stone / moss / wet / dirt layers
per instance). They cost the same as a hand-built graph once compiled but add editor complexity and are harder to
build from Python. For our code-built materials, a **single master with static switches** (UseMoss, UseWet, UseRVT,
UseDetail) is simpler and already how the dojo library works. [inference]

### 4.7 Texel density and texture sets

- Library stone sets are 2048 px over 4 m = **5.12 px/cm** [M]; with a detail normal that is enough for masonry at
  third-person distance.
- Scanned rocks: 1K on a 16 m rock (0.6 px/cm) or 4K on a 2 m rock (20 px/cm) are both common; the **detail normal +
  macro variation** stack is what equalizes them visually. Downsize Megascans maps to 2K where the rock is < 3 m. [S]
- Keep BaseColor sRGB, ORM linear (TC_Masks), Normal DirectX (TC_Normalmap, no flip), power-of-two, full mips (pipeline
  rule). [M]

---

## 5. Decals and weathering on stone

- **DBuffer decals work on Nanite and with the Blendable GBuffer** ("Blendable GBuffer format will continue to support
  both blendable decal and DBuffer decal"; Adaptive supports only DBuffer). DojoLab has `r.DBuffer=1`. [D][M]
- **Mesh decals are not supported on Nanite.** Use projected decal actors. [D]
- Good decal jobs on stone: rain streaks under copings and lantern caps; water stains at wall feet; soot above a
  lantern fire box; a darker damp band at the base of the terrace wall; moss/lichen patches that break the procedural
  masks. The dojo already places 86 weathering decals (moss, rain streaks, grime, water stains, worn paths). [M]
- Prefer the **material** for wetness that depends on a level or on exposure (river waterline, rain) because it follows
  every rock automatically; use decals for authored, one-off marks. [inference]
- The stone master's `MaterialDecalResponse` should stay the default (Color, Normal, Roughness) so decals can darken
  and roughen stone. [M: `Material.h` field]
- Decal cost scales with screen coverage; many large overlapping decals at the wall foot are a Lumen/base-pass cost to
  check with `stat GPU`. [inference]

---

## 6. Lumen, shadows and distance fields on stone

- **HWRT is active in DojoLab** (1.1). Stone meshes reach Lumen through their RT proxy/fallback. Keep RT proxies
  reasonable (2.5); check the Lumen *Surface Cache* view for grey (uncovered) cards on deeply concave rocks and on long
  wall modules. [M][D]
- **Kitbashed, intersecting layers** are named by Epic as a Lumen reflection-tracing cost, and HWRT is "quite sensitive
  to large amounts of instance overlaps". Rubble piles of many interpenetrating rocks: merge or reduce. [D]
- **Distance fields**: still used for DF shadows/AO and SW-Lumen fallback. Small rubble and pebbles: turn off *Affect
  Distance Field Lighting* or set DF Resolution Scale 0 to cut Global Distance Field update cost. [D]
- **VSM**: static stone is the easy case (cached pages). Never put WPO or Pixel Depth Offset on stone materials (both
  invalidate VSM pages every frame) [D]; do the ground seam with RVT, not PDO. Keep displacement magnitudes small (3.2).
- **Low sun.** The dojo is lit at ~9° from the west [M]. Grazing light exaggerates normal-map pits ("sponge" in the
  kit's rounds) and hides geometry-less edges: another reason arrises must be geometry and normal strength modest
  (kit: 0.18-0.35). [M]
- Budget: Epic's High scalability targets **4 ms for Lumen GI + reflections at 1080p / 60 fps on consoles**; **Lumen
  Lite (Beta in 5.8)** is described as about 2x faster. [D]

---

## 7. Collision for walls, steps and rocks

### 7.1 General rules

| Asset | Collision | Notes |
|---|---|---|
| Wall modules (straight, corner, end, openings) | `UCX_<node>_NN` boxes/convex per module, **flat vertical faces and a flat top** at the coping's walking height | the render face has batter, crowns and chips; the collision face must not snag a sliding capsule (a smooth box or a few planes per face) |
| Steps / flights | one convex **ramp** through the tread midpoints (the kit: 25.97-26.43°, 8.3 cm lip) plus flat landing boxes | the kit already passes GASP step/walkable checks [M] |
| Paving, kerbs | flat boxes; kerbs as their own boxes | kerb tops below 45 cm are stepped |
| Lanterns | post box + lamp box; "thin upright" responses (block pawn, ignore camera and visibility), recorded R8 exception [M] | |
| Boulders ≤ 1 m | 1-3 convex hulls | or none for pebbles (NoCollision, *Can Ever Affect Navigation* off) |
| Boulders 1-4 m, cliff rocks | 3-8 convex hulls fitted to the walkable/climbable surfaces | hull tops flattened where the player should stand or mantle |
| Huge cliffs / rocks players walk over | **complex-as-simple** on a purpose-built low mesh via `ComplexCollisionMesh` (a few thousand tris), not on the fallback | complex-as-simple is expensive and "unnecessary for most environment assets" [D]; our fallback may be full-res (2.5) |
| Rock a tree grows from | UCX on the rock + trunk hulls; canopy none (tree study) | |

- Our measured UCX rule stands: `UCX_<render mesh NODE name>_NN` (or `_LOD0_NN` with LODs), **One Convex Hull per UCX**,
  Auto Generate Collision OFF when UCX present. [M: ASSET_GUIDELINES 6.2]
- Hull count per piece: keep ≤ 8 for rocks; Chaos cost scales with hull count and vertex count. [S]
- **Physical material** `PM_Stone` on every stone material/collision (footstep, kunai-impact FX and sound) and a
  `PM_StoneWet` / `PM_Moss` variant if the game uses surface types. [inference; game feature]
- **Camera**: large rocks and walls block Camera; rubble < 0.5 m ignores Camera so the spring arm does not pop. [inference]
- **Navigation**: walls, steps and boulders affect the navmesh; decorative rubble does not. [inference]

### 7.2 GASP traversal on stone (measured, DojoLab 5.8.3) [M: `WorkFiles/dojo/build/GASP_TRAVERSAL.md`]

- GASP's forward trace sees only the **Traversable** channel, and the hit actor must **be a `LevelBlock_Traversable`**
  (a Blueprint cast). **A plain stone mesh is never vaulted, hurdled or mantled**, whatever its collision.
- Ledges are the block's four top-edge splines; a front ledge must be **≥ 60 cm long**; contact is clamped 30 cm from
  the ends.
- Ranges: **Mantle** up to **275 cm** above the feet (1 m clips to 150, climb clips to 275); **hurdle/vault** 0-125 cm
  over obstacles **≤ 59 cm** deep (hurdle needs ≥ 50 cm to the floor behind; vault needs no floor within ~1.36 m);
  **10-50 cm cover matches no row**.
- **The mantle fails on any top sloped more than ~2°**: the top sweep hits the slope within 10-22 cm, the depth drops
  under 59 cm, no row matches. Every climbable stone top needs a **flat landing ≥ 0.49 m deep (0.75 m used)**.
- Capsule r 30 cm, half height 86 cm; **MaxStepHeight 45 cm**; **walkable 44.77°**; jump apex 1.28 m.

**What this means for stone assets:**

1. Wall copings, terrace wall tops, pavilion plinths and big flat-topped boulders on climb routes each need a
   traversal marker (the dojo's hidden `LevelBlock_Traversable`, "Traversable only, query only") **and** a flat UCX top.
   The catalogue should carry a `traversal` block per piece (box in piece space) so the level builder places markers
   automatically. [proposal]
2. Rock tops that are meant to be climbed must be **flattened in collision** (≤ 2°) even if the render top is domed;
   rocks that should *not* be climbed should present > 44.77° faces and no marker.
3. Avoid rubble and low walls **10-50 cm** high on routes (dead band): make cover ≥ 50 cm or ≤ 45 cm (steppable).
4. Stone steps: risers ≤ 45 cm are walked; the kit's 16.7 cm risers and 26° UCX ramp pass. [M]

---

## 8. Placement

### 8.1 Masonry: grid, pivots, prefabs

- The kit's grid is measured in the catalogue: riser 1/6 m, tread 1/3 m, wall pivot on the face line at the module
  start, face → -Y, interlocking 0.18 m course teeth at module ends, chaining rules and snaps in `kit_catalog.json`
  (`how_to_chain`, `pieces[*].snaps`). Unreal snapping: set the editor grid to 1/6 m multiples (16.67 cm is not a preset:
  use 50 / 100 cm plus the catalogue's snap points, or place by script as the dojo level builder does). [M]
- Group repeated assemblies (a terrace run, a stair flight with cheeks and lanterns) as **Level Instances**, and convert
  to **Packed Level Actors** for shipping: they become ISM components, which is what Nanite wants. [D][inference]
- Socket Empties + `.sockets.json` for lantern light points and rail attach points (pipeline rule). [M]

### 8.2 PCG for rubble, boulders and river stones (5.8 PCG, production) [M][S]

Available nodes in 5.8 (`Plugins/PCG/Source/PCG/Public/Elements`): `SurfaceSampler`, `SplineSampler`, `SelfPruning`,
`DifferenceElement`, `Distance`, `ProjectionElement`, `BoundsFromMesh`, `ApplyScaleToBounds`, `CullPointsOutsideActorBounds`,
`CreateCollisionData`, `StaticMeshSpawner`, `SpawnSplineMesh`, and the shape-grammar set `Grammar/PCGSubdivideSpline`,
`PCGSubdivideSegment`, `PCGSelectGrammar`, `PCGDuplicateCrossSections`. [M]

Recipe for a river-bank or slope boulder field:
1. Surface Sampler on the landscape (density per m²), or Spline Sampler along the river spline (bank band).
2. Filter by slope (normal Z), height above the water level (MPC value), distance from paths (Difference against the
   path spline/volume), and noise for clumping.
3. Assign mesh + scale by size class (weighted list of 8-20 rock meshes; big rocks first).
4. **Self Pruning** (large to small) so rocks never interpenetrate heavily; **Difference** against trees and
   walkways.
5. Transform: random yaw, small tilt aligned to the ground normal, **sink 15-35 % of the rock's height** (Z offset from
   `BoundsFromMesh`), scale 0.7-1.4.
6. Static Mesh Spawner → ISM (Nanite). Per-instance custom data can carry a tone value into the stone master.
7. Small pebbles: PCG GPU runtime scatter (5.8 "performance range as the landscape GPU grass system" [D]) or landscape
   grass types, no collision.

Spline-driven walls: a Spline Sampler at module length, or `Subdivide Spline` with a grammar that picks straight /
corner / end modules, then Static Mesh Spawner. This suits the BR village's field walls and dry-stone boundaries. Our
laid ishigaki (batter, corner flare, stair openings) stays hand/script-placed from the catalogue. [inference]

Experimental extras (off by default): **PCG Biome Core** (biome authoring), **PCG FastGeo Interop** (runtime spawning
of componentless primitives), **FastGeo Streaming** (converts partitioned world geometry for faster streaming). [M]

### 8.3 ISM vs HISM

With Nanite, ISM is enough; HISM only helps non-Nanite (per-cluster CPU culling). 5.8 adds hierarchical CPU culling for
non-Nanite ISM. [S, via the tree study]

### 8.4 Seating stones in terrain

- Sink rocks and footings into the ground (the kit: every stone piece runs **0.35 m below** its walking level [M]);
  never let a base float.
- Hide the contact line with the RVT ground blend (4.2 step 7), a soil/moss decal, or scattered pebbles and grass. No
  Pixel Depth Offset (VSM invalidation).
- The Mesh Terrain / landscape owner supplies the terrain; stone assets must work on an unknown slope, so give walls a
  buried foot course and rocks a buried volume rather than a flat bottom face. [inference]

---

## 9. LOD, HLOD and battle-royale scale

- **Nanite meshes have no discrete LODs.** Non-Nanite stone (small props under ~2k tris, or a Fab non-Nanite
  fallback) keeps LOD0 > LOD1 > LOD2 strictly descending (ASSET_GUIDELINES), dithered transition in the master. [M]
- **World Partition HLOD layer types** [D][S]:
  - *Instancing*: ISMs with the lowest LOD; for PCG rubble/boulder instances.
  - *Merged Mesh* / *Simplified Mesh*: merge (and simplify) a cell's wall runs and buildings into one proxy.
  - *Approximated Mesh*: a remeshed, re-textured shell; for cliffs, walls and whole compounds seen from far.
  - Nanite handles close range per object; HLOD handles region-level cost at distance; they work together. [S]
  - HLOD bakes materials: the stone master's world-space features (macro variation, moss) bake into the proxy, so check
    HLOD against the live view at the HLOD transition distance. [U]
- **Unique mesh count** is the real BR constraint: Lumen scene cost and memory scale with unique meshes, not
  instances. A rock library of **10-20 meshes per biome**, reused with scale/yaw/tint, beats hundreds of unique rocks. [S]
- **Mesh Terrain** (5.8, Experimental; plugins `MeshTerrainMode`, `MeshPartition`, `PCGMeshPartitionInterop`, all off by
  default [M]): terrain as a Nanite mesh stack with overhangs, tunnels, cliffs, variable tessellation, virtual
  textures. [D][S] A future route for cliffs instead of placed cliff meshes; treat as a prototype and validate
  collision, navigation, streaming and memory first. The user sources the landscape, so this is their call.
- **Fab products**: state the engine version, ship Nanite-enabled meshes with a sensible fallback, a collision and LOD
  statement ("even when the answer is zero"), and no Experimental-only features as the baseline. [M: ASSET_GUIDELINES]

---

## 10. Mixing owned scanned rocks with our masonry so they read as one set

1. **Same master.** Re-parent scanned rock instances to `M_ST_RockUnique`: their *unique normal* and cavity/AO drive
   form; their albedo is either replaced by our granite detail set tinted per rock, or kept but **tinted to our measured
   stone median** (library granite linear mean about 0.25 / 0.22 / 0.20; kit rule "mid-grey tone with moss/dirt in
   the joints"; Unreal target s < 0.20, R/B 1.00-1.20 from the r3 look pass). The Fisherman's master is already built
   this way (unique mask + normal over a tiling rock set). [M]
2. **Measure, don't eyeball.** Capture a scanned rock and a kit wall under the same sunset rig and compare albedo median,
   saturation, roughness range and dE76 of crops, as the materials README does for the library (target dE76 < 5). [M]
3. **Share the world-space layers**: the same macro variation texture and scale, the same moss exposure threshold and
   colour, the same wetness MPC, the same RVT ground blend. Differences in these read instantly as "two packs". [inference]
4. **Match detail frequency.** Scanned rocks carry fine photo detail; our masonry carries crisp modelled arrises. Give
   both the same tiling detail normal (granite grain) and cap scanned normal strength so crowns do not look sharper
   than our stones. [inference]
5. **Match scale cues.** Real granite grain, lichen spot size and moss cushion size must be the same world size on both
   (texel density ≥ 5 px/cm or a detail layer). [M/inference]
6. **Collision and GASP** apply equally: scanned rocks come with auto collision (`BlockAll`, generated); replace with
   hand hulls on anything on a route. [M]
7. **License / IP.** Megascans and Fab Standard License content may be used in the **game** (commercial use allowed),
   but "you may not resell or redistribute the asset ... on a standalone basis". **No scanned asset, texture or baked
   derivative goes into a Fab product of ours**; Fab stone packs must be entirely our own work. [S: Fab EULA / FAQ]
   Owned packs here were built for **UE 5.2**; they load in 5.8 but should be re-saved in a staging copy, not in
   DojoLab while other workflows run (the DOJO staging rule). [M]

---

## 11. Budgets for a 60 fps third-person game (proposals; measure before adopting) [U]

Frame 16.6 ms at 1440p with TSR on the RTX 4070 SUPER (round 8 measured 8-14 ms mean for the whole dojo). Starting split
for **all stone** in view:

- Nanite visibility + raster + base pass for stone: **≤ 1.5 ms**.
- VSM for stone (cached, no WPO/PDO): **≤ 0.8 ms** steady state.
- Stone share of Lumen: inside Lumen's **4 ms** total (Epic's figure). [D]
- Decals on stone: **≤ 0.3 ms**.

| Tier | Distance (guide) | Examples | Source triangles | Material features | Collision | Shadows / DF |
|---|---|---|---|---|---|---|
| **Hero** | 0-10 m | courtyard walls, stair flights, lanterns, footing, the pine rock, gate kerbs | Nanite; arris segments 2-5 mm; typically 50-400k per module (footing 4 m 118k, StairOpening_H4 386k measured) | full stack: detail normal, moss, wet, RVT seam, per-piece tone; optional build-time displacement on round rocks | UCX boxes / ramps / ≤ 8 hulls; GASP markers on routes | VSM; DF on |
| **Mid** | 10-60 m | terrace wall runs, stair path, river boulders | same meshes (Nanite scales itself) | detail normal fades out by ~15-25 m; moss/wet/macro stay | same | VSM; DF on |
| **Far** | 60-300 m | cliff rocks, far bank boulders, outer walls | library meshes 20-150k; big cliffs up to ~1 M | no detail normal; macro variation dominant; RVT seam | hulls only if reachable | VSM coarse; DF on for big ones only |
| **Vista** | > 300 m | mountains, far cliffs | landscape / Mesh Terrain / HLOD Approximated Mesh | baked HLOD material | none | coarse / none |

**Per-piece checks for hero stone** (proposals):

- verts/tris ≤ 1.0; Nanite *Overdraw* shows no hotspots on stacked rubble at the gameplay camera;
- `stat GPU` Nanite + ShadowDepths delta for a whole terrace run < 0.3 ms at the courtyard camera;
- disk per unique mesh noted in the asset report (the uasset sizes of scanned 80k-tri rocks run 4.9-6.9 MB including
  the source, fallback and DF [M]);
- unique rock meshes per biome ≤ 20.

---

## 12. Verification checklist in Unreal (a second, fresh process on the exact exported bytes)

1. **Import**: Nanite on, Shape Preservation None, fallback per 2.5 (verification import may use RE 0 for the bounds
   gate), RT proxy on; vertex colours Replace; textures BC sRGB, ORM Masks linear, Normal DirectX; UCX count equals the
   shipped hulls ("stored hull identical" gate).
2. **Nanite views**: *Triangles*, *Clusters*, *Overdraw* (rubble piles, joint cores), *Evaluate WPO* (must be none on
   stone); *Tessellation* only on pieces that use it.
3. **Material**: the scanned rock next to a kit wall under the sunset: albedo median, saturation, R/B and dE76 of crops;
   moss only in joints/ledges/tops; wet band at the waterline; no triplanar swimming on placed-with-yaw rocks.
4. **Vertex-colour ramp test** for the SRGB export (4.3).
5. **Lumen/VSM**: *Surface Cache* coverage on concave rocks; VSM *Cached Page* view with stone static
   (`r.Shadow.Virtual.Stats 1`, invalidations ≈ 0); HWRT shadows from the RT proxy match the render silhouette.
6. **Collision**: walk every wall foot, stair and landing; slide along wall faces without snagging; GASP trace gate
   (markers, ledge normals, flat tops ≥ 0.49 m); no 10-50 cm dead cover on routes; camera does not pop on rubble.
7. **Performance**: `stat GPU`, `stat unit`, `ProfileGPU` at the courtyard and the widest river shot; record ms in the
   asset report.
8. **Blind judge on image pairs** (reference vs Unreal capture), with measurements against the reference taking
   precedence over a single judge's steer (the stone kit's round-1 and f1 judge flips).

---

## 13. Uncertain items (verify before relying on them)

- Whether Nanite runtime tessellation is still labelled Experimental in 5.8 (the release notes say nothing; the
  project gate is gone from source).
- Build-time `DisplacementMaps`: setting it from Unreal Python (`set_editor_property`, field is EditAnywhere only) and
  its interaction with the fallback and RT proxy (are they built from the displaced mesh?).
- How HLOD Approximated/Simplified Mesh bakes a world-space stone master (macro variation, moss, RVT seam).
- Whether a Fuzz amount on the moss mask survives the Blendable GBuffer's one-closure simplification with the look we
  want, and its cost.
- The Mesh Paint Texture material node name and UV/resolution setup for Nanite stone.
- FBX vertex-colour gamma (`colors_type="SRGB"`) for moss and wear thresholds.
- Hairline gaps between abutting Nanite modules from independent position quantization (`PositionPrecision`).
- Real cost of the proposed budgets on this GPU (section 11), and of runtime tessellation on a hero rock.
- Nanite Assemblies for *static* stone walls built from a repeated stone-unit library (disk and streaming gain vs
  unique laid stones).
- Mesh Terrain (Experimental) for cliffs: collision, navigation, PCG interop and memory.
- Electric Dreams sample rock kits: not inspected; may be a further owned reference for large Nanite rock layouts.

---

## 14. What this means for the stone kit rebuild and the next rocks

1. **Form in geometry, everything else in the master.** Build stones, arrises, crowns, chips and joint depth in Blender
   (smooth-shaded, verts/tris ≤ 1). Do not plan on Unreal displacement for masonry.
2. **Create the missing Unreal materials** for the kit (`M_DKT_WallGranite`, `M_DKT_StepGranite`, `M_DKT_StepRiser`,
   `M_DKT_JointDark`, per `tracks.*.materials` in the catalogue) as instances of one stone master that adds detail
   normal (distance-faded), macro variation, per-piece tone, joint/ledge moss from vertex A, a wetness switch and an
   optional RVT seam. Under the PackMaterials lock if it touches the pack.
3. **Collision and traversal as data.** Keep UCX boxes/ramps; add a per-piece `traversal` box to the catalogue for every
   climbable top (flat, ≥ 0.5 m deep, ≥ 0.6 m long ledge) so the level builder places GASP markers.
4. **Fallback policy.** Ask the pipeline owner to separate "verification fallback RE 0" from the shipped setting
   (fallback RE ~1 or 5-15 %, RT proxy default), and to add `ComplexCollisionMesh` only where complex collision is
   really needed.
5. **Rocks (pine rock, river boulders, cliffs).** One `M_ST_RockUnique` for ours and the scanned ones; a library of
   10-20 rock meshes per biome; UCX hulls (≤ 8) with flattened climbable tops; PCG for scatter with self-pruning, slope
   and waterline filters and 15-35 % burial; wet band by water level MPC. The pine rock gets smooth shading, a unique
   normal/cavity bake and moss by exposure x cavity, instead of flat faceted planes.
6. **Scanned rocks in the dojo**: game-only, re-tinted to our granite median through the shared master; never in a Fab
   pack.
7. **Stop point.** If a stone type does not converge in the Blender geometry (form), change the construction method there;
   do not try to fix form with Unreal displacement or decals.

---

## Sources

Local, read-only [M]:

- `C:/Program Files/Epic Games/UE_5.8/Engine/Build/Build.version` (5.8.3)
- `Engine/Source/Runtime/Engine/Classes/Engine/EngineTypes.h` (`FMeshNaniteSettings`, `FMeshDisplacementMap`,
  `ENaniteFallbackTarget`, `FDisplacementScaling`, `FDisplacementFadeRange`, `FMeshRayTracingProxySettings`)
- `Engine/Source/Runtime/Engine/Public/Materials/Material.h` (`bEnableTessellation`, `DisplacementScaling`,
  `DisplacementFadeRange`, `MaterialDecalResponse`, `MaxWorldPositionOffsetDisplacement`)
- `Engine/Source/Developer/NaniteBuilder/Private/NaniteBuilder.cpp`, `NaniteDisplace.cpp` (build-time displacement)
- `Engine/Source/Runtime/Renderer/Private/Nanite/NaniteCullRaster.cpp` (`r.Nanite.Tessellation`, `MaxPixelsPerEdge`,
  `DicingRate`), `RenderCore/Private/RenderUtils.cpp` (`UseNaniteTessellation`, `r.RayTracing.RayTracingProxies.ProjectEnabled`),
  `Renderer/Private/VirtualShadowMaps/VirtualShadowMapArray.cpp`, `Renderer/Private/PrimitiveSceneInfo.cpp`
- `Engine/Source/Runtime/Engine/Private/Rendering/NaniteResources.cpp` (`AllowSplineMeshes`, `AllowAssemblies`)
- `Engine/Source/Runtime/Engine/Classes/Engine/StaticMesh.h`, `Private/StaticMesh.cpp` (`LODForCollision`,
  `ComplexCollisionMesh`, `RayTracingProxySettings`), `Private/Components/StaticMeshComponent.cpp` (no vertex paint on
  Nanite), `Private/VT/MeshPaintVirtualTexture.cpp`
- `Engine/Plugins/PCG/Source/PCG/Public/Elements/*` (node list); `Engine/Plugins/Experimental/{MeshTerrainMode,
  MeshPartition, FastGeoStreaming, PCGBiomeCore, PCGInterops/PCGFastGeoInterop}/*.uplugin`
- `Engine/Content/Functions/**` (material function names)
- `Documents/Unreal Projects/DojoLab/Config/DefaultEngine.ini` (read-only grep)
- `Documents/Unreal Projects/Scenery_Tutorial/Content/Megascans/**`, `Landscape/Materials/Functions/**`,
  `Example/VirtualTextures/**` (names, sizes, asset-registry strings)
- `C:/ProgramData/Epic/EpicGamesLauncher/VaultCache/NordicFi1d739256ce1cV1/data/Content/Fishermans_Cabin/{Meshes/Rocks,
  Meshes/Small_Rocks, Materials}` (names, sizes, asset-registry strings)
- Repo: `WorkFiles/dojo/DOJO_QUEUE.md`, `WorkFiles/dojo/build/stonekit/BUILD_NOTES.md`, `kit_catalog.json`,
  `WorkFiles/dojo/build/GASP_TRAVERSAL.md`, `WorkFiles/dojo/build/unreal/gasp_inspect.json`,
  `WorkFiles/dojo/build/unreal/round8/s1_work/start_backup/json/perf.json`, `WorkFiles/dojo/build/pines/BUILD_NOTES.md`,
  `Scripts/dojo/kit1_geo.py` (`pillow_face`, `rough_block`), `Scripts/dojo/materials/README.md`,
  `Scripts/dojo/unreal/dj_sc_materials.py`, `dj_sc_nanite.py`, `dj_gasp_inspect.py`, `ASSET_GUIDELINES.md`,
  `WorkFiles/studies/trees/B_unreal.md`; references `References/Dojo/dojo_landscape_ref.png`

Web:

- [Nanite Virtualized Geometry (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/nanite-virtualized-geometry-in-unreal-engine)
- [Working with Nanite-Enabled Content (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/working-with-naniteenabled-content)
- [Using Nanite with Landscapes (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/using-nanite-with-landscapes-in-unreal-engine)
- [UE 5.8 release notes (Epic)](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes)
- [Unreal Engine 5.8 is now available (Epic)](https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available)
- [Tom Looman: UE 5.8 performance highlights](https://tomlooman.com/unreal-engine-5-8-performance-highlights/)
- [Community tutorial: Nanite Tessellation & Displacement, UE 5.4](https://dev.epicgames.com/community/learning/tutorials/bOda/unreal-engine-nanite-tessellation-displacement-ue-5-4-step-by-step-tutorial-any-asset-not-just-landscapes)
- [Forum: Nanite tessellation and shadows](https://forums.unrealengine.com/t/nanite-tesselation-and-shadows/1688608)
- [Forum: UE5.4 Nanite displacement shadows in motion](https://forums.unrealengine.com/t/ue5-4-nanite-displacement-shadows-in-motion/1793131)
- [Forum: Static mesh Nanite assemblies RT proxy / fallback vertex count](https://forums.unrealengine.com/t/static-mesh-nanite-assemblies-rt-proxy-nanite-fallback-vertex-count-issues/2709323)
- [Ray Tracing Performance Guide (Epic docs)](https://dev.epicgames.com/documentation/en-us/unreal-engine/ray-tracing-performance-guide-in-unreal-engine)
- [Lumen Performance Guide (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/lumen-performance-guide-for-unreal-engine)
- [Lumen Technical Details (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/lumen-technical-details-in-unreal-engine?lang=en-US)
- [Virtual Shadow Maps (Epic docs)](https://dev.epicgames.com/documentation/en-us/unreal-engine/virtual-shadow-maps-in-unreal-engine)
- [Overview of Substrate Materials (Epic docs)](https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-substrate-materials-in-unreal-engine)
- [Runtime Virtual Texturing (Epic docs)](https://dev.epicgames.com/documentation/en-us/unreal-engine/runtime-virtual-texturing-in-unreal-engine)
- [Runtime Virtual Texturing Quick Start (Epic docs)](https://dev.epicgames.com/documentation/en-us/unreal-engine/runtimevirtual-texturing-quick-start-in-unreal-engine)
- [Simple versus Complex Collision (Epic docs)](https://dev.epicgames.com/documentation/en-us/unreal-engine/simple-versus-complex-collision-in-unreal-engine)
- [Setting Up Collisions With Static Meshes (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/setting-up-collisions-with-static-meshes-in-unreal-engine)
- [World Partition HLOD (Epic docs)](https://dev.epicgames.com/documentation/en-us/unreal-engine/world-partition---hierarchical-level-of-detail-in-unreal-engine)
- [World Partition deep dive: streaming, data layers, HLOD (StraySpark)](https://www.strayspark.studio/blog/ue5-world-partition-deep-dive-streaming-hlod)
- [PCG Biome Core and Sample plugins (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/procedural-content-generation-pcg-biome-core-and-sample-plugins-reference-guide-in-unreal-engine)
- [PCG splines: fence generator in UE 5.7 (StraySpark)](https://www.strayspark.studio/learn/tutorials/pcg-spline-fence-generator-ue5)
- [PCG introduction tips: self pruning / difference (gam0022)](https://gam0022.net/blog/2024/01/01/ue5-pcg-introduction-tips/)
- [HISM vs ISM explained (StraySpark)](https://www.strayspark.studio/blog/hism-vs-ism-unreal-engine-explained)
- [Mesh Terrain in UE 5.8: caves, overhangs (StraySpark)](https://www.strayspark.studio/blog/mesh-terrain-ue5-8-caves-overhangs-guide)
- [Forum: Mesh Terrain / Mesh Partition 5.8](https://forums.unrealengine.com/t/mesh-terrain-mesh-partition-5-8/2730153)
- [Polycount: best practices for Nanite assets](https://polycount.com/discussion/236540/best-practices-when-creating-assets-specifically-for-nanite)
- [80.lv: possibilities and drawbacks of Nanite](https://80.lv/articles/discussing-the-possibilities-and-drawbacks-of-unreal-engine-5-s-nanite)
- [Bringing Nanite to Fortnite Battle Royale in Chapter 4 (Epic tech blog)](https://www.unrealengine.com/en-US/tech-blog/bringing-nanite-to-fortnite-battle-royale-in-chapter-4)
- [Fab Standard License / EULA](https://www.fab.com/eula?lang=en)
- [Quixel to Fab transition FAQs](https://support.fab.com/s/article/Fab-Transition-FAQs?language=en_US)
- [Megascans update, March 2025 (Epic forum)](https://forums.unrealengine.com/t/megascans-update-march-2025/2419561)
