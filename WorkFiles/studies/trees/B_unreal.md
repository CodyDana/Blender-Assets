# Tree study B: Unreal Engine 5.8 vegetation

Research phase, 2026-09-29. This is part of the durable tree/vegetation study. It covers what Unreal 5.8 needs from any
tree we build: Nanite, materials, wind, shadows, Lumen, collision, placement, LOD and budgets. The first client is the
four niwaki black pines for the dojo (`References/Dojo/dojo_japanese_pine_ref.png`), but these notes apply to every
future tree, shrub or vegetation asset.

**Evidence tags.** [M] = measured on this PC from the installed engine (UE **5.8.3**, CL 58210709,
`Engine/Build/Build.version`), from its source headers and plugin files, or from the cached Megaplants files, all
read-only. [D] = Epic documentation. [S] = secondary source (blog, forum, talk summary). [U] = uncertain for 5.8,
still to verify in Unreal. No Unreal project was opened or modified, and no MCP tools were used.

---

## 0. Summary

1. **Unreal 5.8 has two ways to do trees, and the choice is made per asset.**
   - **Route A (stable): a Nanite static mesh with material wind (WPO).** Wind comes from SimpleGrassWind or Pivot
     Painter 2. Placement uses Foliage mode, PCG or ISM. This works in any 5.x project and on Fab.
   - **Route B (Experimental): "Nanite Foliage".** The tree is a Nanite *skeletal* mesh, optionally a Nanite
     Assembly. It gets per-bone wind from the DynamicWind plugin and draws as voxels at distance. This is what
     Megaplants and the Procedural Vegetation Editor (PVE) produce. [D][M]
   - **Route C (legacy fallback only): a non-Nanite LOD chain plus impostor.** Use it for platforms without Nanite.
2. **Epic's Nanite Foliage guidance: do not alpha-mask.** Model leaves and needles as real opaque geometry, and use
   bones instead of WPO for wind. [D] Fortnite already shipped opaque, modelled leaves under Nanite. [S] This suits
   our "real geometry, crisp forms" rule. There is one catch: Epic's own Megaplants master material is still
   `BLEND_Masked` and two-sided [M]. Masking is supported; it is just the more expensive path.
3. **WPO wind costs twice.**
   - Nanite: per-vertex WPO, conservative bounds and the programmable raster.
   - Virtual Shadow Maps: WPO invalidates cached shadow pages every frame.

   Mitigations: WPO Disable Distance on every WPO mesh; `Shadow Cache Invalidation Behavior = Rigid` where the
   shadow may lag the sway; the Nanite Pixel Programmable Distance (new 5.8 foliage-type property [M][S]); and
   `r.Shadow.Virtual.Clipmap.WPODisableDistance.LodBias`, which Epic says may need raising for **very low light
   angles**. That is exactly our sunset. [M]
4. **`r.Nanite.Foliage` is read-only and defaults to 0.** [M] Turning it on also enables Nanite Assemblies, Nanite
   Voxels and TSR thin-geometry detection. DojoLab and DemoGame_1 already set it to True. Both projects also run
   **Substrate with the Blendable GBuffer** (`r.Substrate.ProjectGBufferFormat=0`, one closure per pixel), Lumen
   GI and reflections, and `r.RayTracing=True`. [M]
5. **Lumen software ray tracing (SWRT) only sees instanced foliage and ISM when the mesh is Nanite.** Foliage also
   needs *Affect Distance Field Lighting*. [D] Skeletal meshes, and therefore Nanite Foliage trees, have **no mesh
   distance field**. SWRT then sees them only through screen traces; hardware RT uses the fallback mesh. [S][U]
6. **Collision is trunk-only, simple convex.** Static meshes use `UCX_<node>_NN` hulls on the trunk and main limbs,
   with no canopy collision. Skeletal (Route B) meshes use a Physics Asset with trunk bodies only; the PVE export
   offers exactly `None / TrunkOnly / AllGenerations`. [M]
7. **Placement depends on the route.**
   - Foliage mode supports static meshes (ISM/HISM) and Actors only, **not skeletal foliage**. [M]
   - Route B trees go through PCG's **Instanced Skinned Mesh Spawner**, or a hand-placed Blueprint with an
     `InstancedSkinnedMeshComponent`, `Wind_TransformProvider` and `BP_GlobalFoliageActor_UE5`. [M][S]
   - With Nanite, ISM is enough; HISM brings no extra benefit. [S]
8. **Recommendation for the niwaki pines:** build Route A first, keeping the tree rig-ready, then pilot Route B on one
   tree. Details in section 13.

---

## 1. What is on this PC (read-only inspection)

### 1.1 Engine 5.8.3 plugins [M]

| Plugin | Path | Status | Notes |
|---|---|---|---|
| Procedural Vegetation Editor | `Engine/Plugins/Experimental/ProceduralVegetationEditor` | Experimental, off by default | "Node Graph based Editor that allows users to create Nanite Foliage ready vegetation directly in the engine". Depends on Dataflow, GeometryScripting, PCG and **DynamicWind**. Runtime module `ProceduralVegetation`, Win64/Linux/Mac only. |
| Dynamic Wind | `Engine/Plugins/Experimental/DynamicWind` | Experimental, v0.1, off by default | Its own description: "Extremely experimental dynamic wind support for Nanite foliage." |
| PCG + interops | `Engine/Plugins/PCG`, `Experimental/PCGBiomeCore`, `PCGBiomeSample` | PCG is production | `PCGSkinnedMeshSpawner.h` exists, so PCG can spawn instanced skinned meshes. |
| Pivot Painter 2 functions | `Engine/Content/Functions/Engine_MaterialFunctions02/PivotPainter2/*`, `.../ExampleContent/PivotPainter2/SimplePivotPainterExample*` | shipping | Engine content. |
| SimpleGrassWind | `Engine/Content/Functions/Engine_MaterialFunctions01/WorldPositionOffset/SimpleGrassWind` | shipping | Engine content. |

### 1.2 Project settings already in place (from `Config/DefaultEngine.ini`, read-only) [M]

| Setting | DojoLab | DemoGame_1 |
|---|---|---|
| `r.Nanite.Foliage` | True | True |
| `r.Nanite.ProjectEnabled` | True | (default) |
| `r.Substrate` / `ProjectGBufferFormat` | True / 0 (Blendable) | True / 0 |
| `r.DynamicGlobalIlluminationMethod` / `r.ReflectionMethod` | 1 / 1 (Lumen) | 1 / 1 |
| `r.GenerateMeshDistanceFields` | True | True |
| `r.Lumen.TraceMeshSDFs` | 1 | default |
| `r.RayTracing` | True | True |
| `r.AntiAliasingMethod` | 4 (TSR) | default |
| `r.Shadow.Virtual.Enable` | default (VSM) | 1 |
| ProceduralVegetationEditor plugin | not enabled in `.uproject` | **enabled** |

DojoLab would need the PVE and DynamicWind plugins enabled before it can load Megaplants or any Route B tree [U].
Enabling a plugin changes the project, so it is the user's call.

### 1.3 Megaplants content structure (read-only) [M]

- **Where it is.** Copies sit in `DemoGame_1/Content/Megaplant_Library/` (109 files, 0.42 GB) and in the launcher
  vault: `Megaplan1093c7601c36V1` is Ginkgo (49 files, 0.14 GB) and `Megaplanb3dc3e6c5a59V1` is Japanese Cypress
  (62 files, 0.28 GB).
- **Engine version.** The packages are tagged `++UE5+Release-5.8`. PVE docs say **5.7 PVE assets are not compatible
  with 5.8** [D], so matching versions matter.

Layout per species (Japanese Cypress shown; Ginkgo is the same):

```
Megaplant_Library/Tree_Japanese_Cypress/
  Tree_Japanese_Cypress_01/
    Tree_Japanese_Cypress_01_A..G.uasset     1.9-8.5 MB each: /Script/Engine.SkeletalMesh (Nanite, Voxelize, NaniteAssemblyData,
                                             DynamicWindSkeletalData user data, PhysicsAsset); 7 variants (Ginkgo: 4, A..D)
    Tree_Japanese_Cypress_01_A..G_Skeleton   one Skeleton per variant
    PVE_Tree_Japanese_Cypress_01.uasset      the PVE graph (ProceduralVegetationGraphInstance; PCG-based)
    PVE_Preset_Japanese_Cypress_01 / Preset_ PVFoliageParams presets (foliage mesh + weight)
  Instances/                                 the assembly PARTS
    Tree_Japanese_Cypress_Branch_01..06      StaticMesh branch kits (Nanite, ShapePreservation::Voxelize), 0.2-1.5 MB
    SKM_Tree_Japanese_Cypress_Branch_01..06  SkeletalMesh versions of the branch parts, 0.8-10.9 MB
    SK_Tree_Japanese_Cypress_Branch_01..06   their Skeletons
    Japanese_Cypress_Decorations_01_A..E (+SKM_/SK_) cones/decorations
  Materials/  MI_*_Bark_01, MI_*_Foliage_01, MI_*_Decorations_01 -> parent /ProceduralVegetationEditor/SampleAssets/
              Materials/MasterMaterials/MA_Foliage_Trees (engine plugin content, not in the pack)
  Textures/   T_*_Foliage_01_CA / _NT, T_*_Bark_01_C / _NAH, T_*_Decorations_01_C / _NAH, T_PVE_MeshDisplacement_0x
              (15-48 MB uassets each -> very high-res source)
```

**Bone counts per tree** (distinct `Bone_N` names in each skeletal mesh; the string count is an estimate):

| Tree | Bones |
|---|---|
| Ginkgo A / B / C / D | 791 / 579 / 414 / 298 |
| Cypress A / B / C / D / E / F / G | 906 / 958 / 455 / 304 / 43 / 837 / 837 |

This matches Epic's example tree of about 850 bones. [D]

**What the property strings in the packages show** [M]:

- **Wind.** `DynamicWindSkeletalData` with `SimulationGroups`, `BoneChains` and `ExtraBonesData`.
- **Assemblies.** `NaniteAssemblyData`, `NaniteAssemblyPart`, `NaniteAssemblyNode` and `NaniteAssemblyBoneInfluence`;
  the branch parts are micro-instanced and bound to bones.
- **Physics.** `PhysicsAsset` and `ShadowPhysicsAsset`.
- **Master material.** `MA_Foliage_Trees` is `BLEND_Masked`, `TwoSided`, with the shading model from an expression
  (`MSM_FromMaterialExpression`), `bUsedWithNanite` and `bUsedWithVoxels`. It uses `DitheredLODTransition`,
  `PixelDepthOffsetMode`, `PerInstanceRandom` and `PerInstanceCustomData`, and a global `MPC_GlobalFoliageActor`
  for wind, season and health. Its translucency and "Distance Translucency Gradient" controls are
  subsurface-colour controls, not the translucent blend mode.
- **PVE export options** (strings found in the PVE graph):
  - `ExportSettings/bCreateNaniteFoliage` ("Add Nanite foliage support for the exported mesh").
  - Mesh type: "StaticMesh: no wind animation support. SkeletalMesh: includes bones for wind sway".
  - `CollisionGeneration`: "None: no physics asset. TrunkOnly: collide only with the trunk. AllGenerations: collide
    with every branch (highest cost)".
  - `NaniteShapePreservation` (Voxelize default) and `WindSettings` (`DefaultTreeWindSettings`).
  - A Bone Reduction slider: "0 = no reduction (full bone count, max wind accuracy)".
- **Texture names** (my inference from names and material parameters [U]): `_CA` = colour + alpha,
  `_NT` = normal + translucency, `_NAH` = normal + AO + height.

**Takeaway for our builds.** Megaplants trees are PVE outputs made of a few instanced branch *parts* on a skeleton
of about 300 to 960 bones. They are not one monolithic mesh. A custom pine that should behave like a Megaplant has to
arrive the same way: parts plus skeleton plus wind data. Alternatively it arrives as a plain static mesh (Route A).

---

## 2. Nanite for foliage

### 2.1 Cost model

- **Supported blend modes.** Nanite takes Opaque and Masked. Masked, two-sided, WPO and PDO all run on the
  *programmable* rasterizer path. [D]
- **Masking costs extra.** Epic's Nanite Foliage page says to *avoid alpha masking*: it "causes overdraw and
  excessive mask function execution". [D] Model the geometry instead.
- **Fortnite precedent.** Fortnite avoided masked foliage by modelling leaves as geometry with an opaque material. It
  also found masked Nanite compresses worse, so it costs memory as well. [S]
- **The often-quoted "+20-30% raster for masked Nanite foliage"** comes from a tutorial site. [S][U] Measure it.
- **WPO on Nanite.**
  - Clusters get conservative bounds and are culled individually, so displacement must be clamped with the
    material's `Max World Position Offset Displacement`. That property exists in 5.8 `Material.h`. [D][M]
  - Epic calls WPO "generally not suitable for Nanite" and replaces it with Nanite Skinning. [D][S]
- **5.8 additions** [M][S]:
  - `NanitePixelProgrammableDistance` on `UFoliageType`, `UStaticMeshComponent` and `USkinnedMeshComponent`. It
    "forcefully disable[s] pixel programmable rasterization of Nanite when the mesh is further than a given
    distance". So mask, WPO and PDO turn off beyond N cm.
  - "Mask material only in early Z-pass" is now on by default.
  - Skinned meshes gained WPO Disable Distance.
- **Views and cvars:**
  - Nanite visualisation: *Overdraw* and *Evaluate WPO* (green = WPO in use). [D]
  - `r.Nanite.Culling.WPODisableDistance` (1) is the global test switch for the per-primitive disable distance. [M]
  - `r.Nanite.AllowMaskedMaterials` (1). [M]

### 2.2 Shape preservation (Nanite Settings on the mesh) [M]

`ENaniteShapePreservation` in 5.8 `EngineTypes.h`:

| Value | Engine comment | Use |
|---|---|---|
| `None` | no shape preservation | trunks, rocks, man-made |
| `PreserveArea` | "Try to maintain the same surface area at all distances (**Legacy** foliage technique)" | foliage without Nanite Foliage enabled. [D] says to enable it on all foliage and nothing else. |
| `Voxelize` | "Simplify triangles to voxels in the distance to preserve the perceived volume of the object. Useful for foliage that thins out otherwise." | Nanite Foliage. Needs `r.Nanite.Foliage=1` or `r.Nanite.AllowVoxels=1`. |

**`FMeshNaniteSettings` fields** (BlueprintReadWrite, so they can be set from Unreal Python):

- `bEnabled`, `ShapePreservation`, `bSeparable`, `bVoxelNDF`, `bVoxelOpacity`, `NumRays` (64), `VoxelLevel`,
  `RayBackUp`
- `KeepPercentTriangles`, `TrimRelativeError`, `MaxEdgeLengthFactor`
- `GenerateFallback`, `FallbackTarget`, `FallbackPercentTriangles`, `FallbackRelativeError`
- `PositionPrecision`, `BoneWeightPrecision` (0 = rigid), `DisplacementUVChannel`
- `NaniteAssemblyData`

**Voxel caveats:**

- **Holes in solid trunks.** Voxelize can punch holes in trunks when the mesh gets small on screen (forum report,
  5.7.4). Epic's answer: enable **`Separable`** (6-separable voxelization). It costs more disk and can make foliage
  look denser. The alternative is to split trunk and foliage into separate meshes. [S]
- **Vertex-colour alpha is taken.** Voxel shading stores normal-distribution statistics in the **vertex colour alpha**,
  overwriting whatever was there. **Never put wind or masks in vertex colour A on a Voxelize mesh.** [D]

### 2.3 Nanite Foliage = Assemblies + Voxels + Skinning [D][M]

- **Enabling it.** Project Settings > Rendering > Nanite Foliage (Experimental), then restart. The cvar is
  `r.Nanite.Foliage`, default 0, `ECVF_ReadOnly`. In `RenderUtils.cpp` it enables
  `NaniteAssembliesSupported()` (or `r.Nanite.AllowAssemblies`), `NaniteVoxelsSupported()` (or
  `r.Nanite.AllowVoxels`) and TSR thin-geometry detection (`r.TSR.ThinGeometryDetection`). [M]
- **Assemblies.**
  - Micro-instanced *parts*, up to 65,536 instances per assembly. Epic's example tree went from 3.5 GB to 29 MB on
    disk and from 36 MB to 2.7 MB streaming.
  - No nesting; part geometry is not deduplicated across assemblies.
  - **Skeletal assembly parts are not skinned**: they move rigidly with the bone(s) they are bound to. [D]
  - `r.Nanite.MaxVisibleAssemblyParts` = 262,144 by default [M].
  - Authoring routes: the PVE Export node; the "Nanite Assembly Editor Utilities" plugin (Blueprint
    `UNaniteAssemblyStaticMeshBuilder` / `UNaniteAssemblySkeletalMeshBuilder`); or **USD import**. [D]
- **USD schema** (5.8 `USDCore/.../unreal/schema.usda`) [M]:
  - `NaniteAssemblyRootAPI` with `unreal:naniteAssembly:meshType` = `staticMesh | skeletalMesh` and
    `unreal:naniteAssembly:skeleton` rel.
  - `NaniteAssemblyExternalRefAPI` with `meshAssetPath`.
  - `NaniteAssemblySkelBindingAPI` with `primvars:unreal:naniteAssembly:bindJoints` and `bindJointWeights`;
    applies to Xform, Mesh, SkelRoot and **PointInstancer**.
  - `NaniteBuildSettingsAPI` with every Nanite field, including `unreal:nanite:shapePreservation` =
    None/PreserveArea/Voxelize and `unreal:nanite:separable`.
  - So **a Blender to USD to Unreal path can author a skeletal Nanite assembly outside the engine.** It would need
    post-processing of Blender's USD with `pxr` to add the API schemas. [U: untested]
- **Skinning.** GPU per-bone animation. About 0.1 ms GPU per 100,000 bones. [D]
  - Animation stops below a screen size: component `AnimationMinScreenSize`, global
    `r.Skinning.DefaultAnimationMinScreenSize` [M]. Disabled instances fall back to unskinned rendering.
  - Epic ties VSM performance to disabling distant animation. [D]
  - `r.Skinning.TransformProviders` is the master switch. [M]
- **Known limits** [D]:
  - Global wind direction only.
  - Trees do not bend when players or objects touch them.
  - Wind data comes from JSON (or the PVE); USD auto-import is "future".
  - Voxel normal distribution is stochastic per pixel.

### 2.4 Procedural Vegetation Editor (5.8, Experimental) [D][M]

- **Graph nodes.** Built on PCG: Grower, Point Scatter/Seed Generator, **Extract From Mesh** (takes any static mesh,
  uses the trunk material as a mask, extracts a skeleton only), Extract From Image, Object Interaction
  (avoid/trim), Manual Edit, Simplify, Carve, Gravity, Slope, Mesh Builder, Trunk Texture Setup, Foliage
  Distributor/Palette, Graft Distributor/Palette, **Export**, Bone Reduction.
- **5.8 breaking changes.** The Preset Loader is replaced by Growth Data Loader + Profile Loader. External foliage
  import is removed and handled by the Foliage Distributor.
- **Relevance for us.** PVE is procedural botany. Our lessons say procedural natural shapes judged weakest, and the
  niwaki are *pruned sculptures*, so PVE should not be the authoring tool. It could still serve as a **converter**:
  a Blender trunk skeleton goes through Extract From Mesh, then foliage parts are grafted, then Export to Nanite
  Foliage with wind and TrunkOnly collision. This has to be tested before relying on it. [U]

---

## 3. Foliage material model

### 3.1 Legacy shading models and their Substrate equivalents

| Legacy (non-Substrate) | Substrate Slab `Sub-Surface Type` (5.8 enum `EMaterialSubSurfaceType`) [M] | Use |
|---|---|---|
| Two Sided Foliage | **`MSS_TwoSidedWrap`**: "Approximation using wrap-lighting and handling thin surface (e.g.: foliage)" | leaves, needles, petals |
| Subsurface | `MSS_Wrap` | thick fleshy parts |
| Subsurface Profile | `MSS_Diffusion` | skin; not for foliage |
| (translucent blend) | `MSS_SimpleVolume` | avoid for foliage |

- **Automatic conversion.** When a legacy material is converted, 5.8 picks `TwoSidedWrap` for the slab if the
  material is opaque or masked, not SSS-diffusion, and flagged as a *thin surface*. [M: `Material.cpp`
  `ConvertSlabExpressionMaterialSubSurfaceType`]
- **Author with Slab nodes.** Epic says to avoid the "Substrate Shading Models" node in new materials. [D]
- **GBuffer format.** Both projects use the Blendable GBuffer, which allows **one closure per pixel**. Keep foliage
  to a single slab; do not layer or mix. [D][M]
- **Lumen treats foliage specially.** Pixels whose material is Two Sided Foliage or Subsurface are "foliage":
  - `r.Lumen.ScreenProbeGather.TwoSidedFoliageBackfaceDiffuse` gathers backface lighting as
    `DiffuseColor * front + SubsurfaceColor * back`, at extra cost.
  - `r.Lumen.Reflections.MaxRoughnessToTraceForFoliage` defaults to 0.2; Epic suggests 0 for big savings.
  - `r.Lumen.ScreenProbeGather.MaxRoughnessToEvaluateRoughSpecularForFoliage` (0.8).
  - `r.Lumen.ScreenProbeGather.ShortRangeAO.FoliageOcclusionStrength` (0.7).
  - `r.Lumen.ScreenProbeGather.Temporal.DistanceThresholdForFoliage` (0.03).
  - `r.Lumen.ScreenProbeGather.ScreenTraces.HZBTraversal.SkipFoliageHits`.
  - [M from `Renderer/Private/Lumen/*.cpp`][D]
  - Whether a Substrate `TwoSidedWrap` slab counts as a "foliage pixel" to Lumen is not confirmed [U]; the
    Two-Sided Wrap docs imply it does.

### 3.2 Other material features

- **Two Sided.** Needed for thin cards, needles and petals. Supported on Nanite through the programmable raster
  path. [D]
- **Translucency.** Never use the translucent blend mode for leaves: it is not Nanite, sorts badly and costs a lot
  of overdraw. "Translucency" in foliage materials means the subsurface or transmission colour. [D]
  (`r.Nanite.AllowTranslucency` is 0, "Heavy WIP". [M])
- **Pixel Depth Offset.**
  - Nanite supports it through programmable raster. [D]
  - **It always invalidates VSM cache pages**, just like WPO. [D]
  - Use it only if needed, for example to blend a trunk into the ground, and give it a Pixel Programmable Distance.
- **Dithered LOD transition.** Only meaningful for non-Nanite LOD chains (Route C). Nanite has no discrete LODs to
  dither. Megaplants' master still has the switch for its non-Nanite fallback.
- **Per-instance variation.** `PerInstanceRandom` works on ISM/HISM/Foliage/PCG instances, and Per-Instance Custom
  Data on ISM and PCG. Use them for hue/health variation between the pines instead of separate textures.
- **TSR on foliage.** 5.7+ adds the experimental material outputs *Motion Vector World Offset (Per-Pixel)* and
  *Temporal Responsiveness*, plus `r.TSR.ThinGeometryDetection` (auto-on with Nanite Foliage). [S][M]
- **Texture channel packing.** The Megaplants convention is `C`/`CA` + `NT`/`NAH`. Ours (ASSET_GUIDELINES) is
  BaseColor sRGB + ORM linear + Normal DirectX. For foliage, add a translucency/thickness mask. Per the voxel
  caveat, put it in a texture channel, not in vertex colour alpha.

---

## 4. Wind

### 4.1 Options

| Method | Data the DCC must export | Cost / caveats | Where it fits |
|---|---|---|---|
| **SimpleGrassWind** (engine function; inputs `WindIntensity`, `WindWeight`, `WindSpeed`, `AdditionalWPO`) [D] | A weight mask: vertex colour channel (R/G/B, **not A on Voxelize meshes**) or a UV gradient. Non-directional. | WPO: Nanite programmable raster + VSM invalidation. Cheapest to author. | shrubs, grass, subtle canopy flutter |
| **Pivot Painter 2** (engine `PivotPainter2FoliageShader`, `ms_PivotPainter2_*`) [D][M] | One **extra UV channel** pointing each element to a texel. Textures are 16-bit RGB **EXR** (pivot position; alpha = parent index as float, up to 2048) and 8-bit x-vector/extent textures. Import settings: `HDR (RGB, no sRGB)` or `VectorDisplacementMap(RGBA8)`, sRGB off, **NoMipMaps**, **Filter Nearest**. Elements must be separate logical pieces; max 30,000 elements. The sample function supports **4 hierarchy levels**. Material needs *Tangent Space Normals* off. | WPO, so it pays the full Nanite + VSM WPO cost. Hierarchical branch-level sway. | Route A hero trees; also the *input* to the Dynamic Wind converter below |
| **Dynamic Wind** (Nanite skinning) [D][M] | A **skeleton**: trunk and branch bone chains, rigid part binding, plus a **JSON** of joints to simulation groups. | Per-bone on GPU, about 0.1 ms per 100k bones [D]. Epic calls it "much cheaper than WPO" [S]. **Experimental**; no local interaction. | Route B, Megaplants |

### 4.2 Dynamic Wind data model (5.8 source) [M]

`UDynamicWindSkeletalData` is asset user data on the skeletal mesh. Its fields:

- `bIsEnabled`
- `bIsGroundCover`: no height attenuation.
- `GustAttenuation`
- `SimulationGroups[]`: each has `bUseDualInfluence`, `Influence` (or `MinInfluence`/`MaxInfluence`/`ShiftTop`)
  in 0..1, and `bIsTrunkGroup` ("Is Trunk?").

**JSON import struct** `FDynamicWindSkeletalImportData`:

```json
{
  "Joints": [ { "JointName": "Trunk_0", "SimulationGroupIndex": 0 }, ... ],
  "SimulationGroups": [ { "bUseDualInfluence": false, "Influence": 0.2, "bIsTrunkGroup": true }, ... ],
  "bIsGroundCover": false,
  "GustAttenuation": 0.0
}
```

**How the importer builds bone chains** (`DynamicWindImportData.cpp`):

- It walks the skeleton hierarchy. A chain is a run of **parent-child bones with the same group index**.
- Chain length is the sum of rest-pose bone lengths.
- So the **bone hierarchy and rest pose from Blender matter directly**: each pad or branch should be its own chain,
  and trunk bones should be marked as trunk groups.

**Editor entry points** (`UDynamicWindBlueprintLibrary`, editor-only):

- `ImportDynamicWindSkeletalDataFromFile(SkeletalMesh)` **opens a file dialog**. A third-party script calls it from
  Unreal Python. [S] This is **not headless**. A commandlet pipeline would need a tiny C++ editor module that calls
  `DynamicWind::ImportSkeletalData(...)` (exported, `DYNAMICWINDEDITOR_API`), or one manual UI step. The lookup
  arrays are plain `UPROPERTY()` and cannot be set from Python. [M][U]
- **`ConvertPivotPainterTreeToSkeletalMesh(StaticMesh, PivotPosTexture, PivotUVIndex, TargetSkeletalMesh,
  TargetSkeleton)`** turns a **Pivot Painter 2 tree** (pivot-position texture, RGB = position, A = parent index
  encoded as half-float bits) into a skeletal mesh.
  - Bones are named `Root` / `Trunk_N` / `Branch_N` / `Leaf_N`.
  - Vertices are bound by their pivot UV; UVs outside 0..1 bind to the root.
  - It copies the Nanite settings and materials.
  - So **one Blender PP2 export can serve both Route A (WPO) and Route B (skeletal Dynamic Wind)**. The target
    skeletal mesh and skeleton must be empty assets. [M]

**Runtime:**

- Cvars: `DynamicWind.Enable`, `DynamicWind.OverrideSpeed`, `DynamicWind.OverrideAmplitude`,
  `DynamicWind.OverrideRateOfChange`, `DynamicWind.UseSine`, `DynamicWind.PreferAsyncCompute`. [M]
- A placed tree needs an `InstancedSkinnedMeshComponent` whose **Transform Provider** is a Dynamic Wind data asset.
  PVE ships `SampleAssets/Materials/GlobalFoliageActor/Wind_TransformProvider`.
- A `BP_GlobalFoliageActor_UE5` (with `MPC_GlobalFoliageActor`) drives wind, season and health. [M][S]

### 4.3 FBX data contract from Blender (applies to Route A and to the PP2 converter)

- **UV channels in order.** UV0 = material UVs. UV1 = the Pivot Painter index UV, if used. Nanite does not need a
  lightmap UV, but our QA's `--require-uv1` and the Fab lightmap rule assume UV1 is a lightmap. A PP2 tree
  therefore needs an explicit exception or a UV2 slot; decide once and record it in the pipeline. [U]
- **Vertex colours for masks.** Our exporter writes `colors_type="SRGB"`. Wind weights stored as colours will be
  gamma-encoded on the way. Verify with a known-value round trip (0.25/0.5/0.75 ramps sampled in a debug material)
  before trusting any vertex-colour mask. [U]
- **Units and axes.** Pivot positions must be in Unreal space (cm, Unreal axes). PP2 textures bake object-space
  positions, so bake *after* the pipeline's cm scale and axis conversion, or bake in Blender with the same
  conversion. [U: verify against `SimplePivotPainterExample`]
- **Existing Blender PP2 exporters.**
  - *Modular Tree (MTree)* 5.5.2 writes two EXRs + a UV2 layer "compatible with Epic's PivotPainter2FoliageShader";
    it officially supports Blender 4.3.1 to 5.1, so 5.2 is unverified. [S]
  - Gvgeo's *Pivot-Painter-for-Blender* (GPL, 2.80+). [S]
  - Writing our own baker in `Scripts/pipeline` is simple: pivot RGB + parent index as float16 alpha, one texel per
    element, UV pointing at texel centres.
  - GPL add-ons are fine as tools but must not be bundled with a Fab product.

---

## 5. Virtual Shadow Maps and WPO invalidation

**The rule** [D]: "Geometry that can be deformed using Skeletal animation, or materials using World Position Offset or
Pixel Depth Offset always invalidates cached pages every frame." With WPO the cache cannot know whether anything
moved.

**Mitigations, most effective first:**

1. **`World Position Offset Disable Distance`** on the component or foliage type (cm). Epic says to set it on *all*
   foliage and *all* WPO meshes; it made "a huge performance difference" in Fortnite. [D][S] 5.8 also has it on
   skinned components. [M]
2. **`Shadow Cache Invalidation Behavior`** on the component or `UFoliageType` [M][D]:
   - `Auto`: default.
   - `Always`.
   - **`Rigid`**: "Suppress invalidations that would otherwise be generated by, for example, World Position Offset".
     The shadow stops tracking the sway, but no pages are redrawn.
   - `Static`: Rigid plus ignore transform changes.

   **For clipped niwaki with small pad sway, Rigid is a good default.** Check at sunset that the pad shadows don't
   visibly detach.
3. **Clipmap WPO distance** [M] (`VirtualShadowMapClipmap.cpp`):
   - `r.Shadow.Virtual.Clipmap.WPODisableDistance` (1, scalability) disables WPO in clipmap levels beyond the
     primitive's disable distance.
   - `r.Shadow.Virtual.Clipmap.WPODisableDistance.LodBias` (3): "Typically 2-4 works well but may need to be
     adjusted for **very low light angles** with significant WPO movement". The dojo is lit by a low sunset sun, so
     test 3 against 4 or 5.
4. **Stop distant skeletal animation:** `AnimationMinScreenSize` and `r.Skinning.DefaultAnimationMinScreenSize`.
   [D][M]
5. **Keep bounds tight.** Invalidation covers every page the bounds overlap. Clamp
   `Max World Position Offset Displacement`, and don't inflate bounds casually. [D]
6. **Non-Nanite foliage is "much more expensive"** in VSM. Epic recommends Nanite on everything supported. [D]
   Related cvars: `r.Shadow.Virtual.NonNanite.IncludeInCoarsePages` (1; setting 0 "can be a significant
   performance win"), `r.Shadow.RadiusThreshold`, `r.Shadow.Virtual.UseFarShadowCulling`. [M][D]
7. **Grass and small foliage:** Contact Shadows alone can replace high-res VSM. [D]
8. **Other 5.7/5.8 cache behaviour** [M][S]:
   - `r.Shadow.Virtual.Cache.InvalidateUseHZB` (1): fully occluded instances don't invalidate.
   - `r.Shadow.Virtual.Cache.FramesStaticThreshold` (100).
   - VSM receiver masks on for directional lights (5.7).
   - `r.Shadow.Virtual.DeferredInvalidationBudget` throttles `r.Nanite.VSMInvalidateOnLODDelta` (5.8).
   - The 5.1-era `r.Shadow.Virtual.Cache.MaxMaterialPositionInvalidationRange` does **not** exist in 5.8 source,
     so don't use old guides that cite it. [M]

**Profiling** [D]: Viewport > Virtual Shadow Map > **Cached Page** (green cached, red uncached, blue static-only).
Run `r.ShaderPrintEnable 1` with `r.Shadow.Virtual.Stats 1` and watch Invalidated pages; static invalidations should
be about 0. Use the *ShadowCasters* view to find invalidators.

---

## 6. Lumen on foliage

- **SWRT needs Nanite for instanced foliage.** "Foliage and Instanced Static Mesh Components can only be supported if
  the mesh is using Nanite", and foliage needs **Affect Distance Field Lighting** on the foliage type. [D]
- **Two-sided distance fields.** Masked or thin foliage should have *Two-Sided Distance Field Generation* on the
  static mesh, or SWRT loses volume and leaks. [S]
- **Skeletal Nanite Foliage trees have no mesh distance fields.** SWRT sees them only in screen traces. Hardware RT
  traces the Nanite fallback mesh. Skinned surface-cache quality is "fairly limited". [D][S][U]
  - With `r.RayTracing=True` in DojoLab, check which mode Lumen actually runs (`r.Lumen.HardwareRayTracing`, not set
    in the ini). [U]
  - Consequence: in SWRT, a Route B pine may get weaker occlusion and GI contribution than a Route A static pine.
    Test both side by side at sunset.
- **Lumen treats unique meshes as the cost unit.** Scene cost scales with unique meshes, not instances: one mesh with
  a million instances is cheaper than ten meshes with 100k each. [S] Keep the pine variant count low (2 variants x
  4 trees is fine).
- **Foliage cvars** (see 3.1): `MaxRoughnessToTraceForFoliage` 0,
  `ShortRangeAO.FoliageOcclusionStrength`, and `TwoSidedFoliageBackfaceDiffuse`.
- **Budget.** Epic targets Lumen GI + reflections at **4 ms for 60 fps on consoles at 1080p**. [D]
- **5.8 "Lumen Lite"** is described as about 2x cheaper than high quality. [S][U: check the name and setting in
  5.8.3]

---

## 7. Collision

- **Static (Route A).** Our measured 5.8.2 rule: `UCX_<render mesh NODE name>_NN`, or `UCX_<base>_LOD0_NN` with LODs.
  - Use a few convex hulls on the trunk and main limbs only.
  - The canopy gets **no collision**: characters, wall-top runs and climb routes must pass. DOJO_QUEUE already says
    canopies must not block wall-top runners.
  - Foliage type: collision preset per type, for example BlockAll on the trunk and nothing on leaves.
- **Skeletal (Route B).** Collision comes from the **Physics Asset** (capsules or convex per bone). UCX does not
  apply.
  - PVE export `CollisionGeneration`: `None / TrunkOnly / AllGenerations`. TrunkOnly is the default choice. [M]
  - `InstancedSkinnedMeshComponent` supports per-instance bodies (`FInstancedMeshComponentBodies`) and has
    `bDisableCollision`. [M]
  - Megaplants trees carry both `PhysicsAsset` and `ShadowPhysicsAsset`. [M]
  - From Blender: a Physics Asset can be generated on import, or built from named primitives. [U] Otherwise author
    it in Unreal via Python.
- **Wind never collides.** There is no interaction between wind and characters or props. [D]
- **Navigation.** Trunk hulls should affect navmesh; canopy should not. Check with the navigation debug view.

---

## 8. Placement

| Tool | Static Nanite (Route A) | Skeletal Nanite Foliage (Route B) | Notes |
|---|---|---|---|
| **Foliage mode** (`UFoliageType_InstancedStaticMesh` / `_Actor`) | yes; exposes WPO disable distance, shadow invalidation behaviour, `NanitePixelProgrammableDistance`, collision, cull distances | **no** (no skinned foliage type in 5.8 [M]) | good for the hand-placed 4 pines if static |
| **PCG** Static Mesh Spawner | yes (ISM/HISM, FastGeo componentless in 5.7+ via `pcg.RuntimeGeneration.ISM.ComponentlessPrimitives`) | **Instanced Skinned Mesh Spawner** (5.7+) [M][S] | forests, slopes, biome (PCGBiomeCore) |
| Blueprint / level actor | Static Mesh Actor or ISM | **ISKM component + `Wind_TransformProvider` + `BP_GlobalFoliageActor_UE5`** [S][M] | exact hero placement |
| ISM vs HISM | With Nanite, ISM is enough (GPU culling and LOD). HISM only helps non-Nanite (per-cluster CPU culling). 5.8 adds hierarchical CPU culling for non-Nanite ISM (`r.SceneCulling.HierarchicalCPUCulling`). [S] | n/a | |

For the dojo: 4 pines are hero placements, so use actors or a small ISM. The slope forest and background use PCG or
Foliage mode with pack trees; the user has Megaplants Cypress and Ginkgo, plus the Yoshino Cherry to download.

---

## 9. LOD versus Nanite fallback

- **Nanite meshes have no discrete LODs.** The **fallback mesh** (`GenerateFallback`, `FallbackTarget`,
  `FallbackPercentTriangles`/`FallbackRelativeError`) is used for:
  - hardware ray tracing (`r.RayTracing.Nanite.Mode` 0 = fallback);
  - complex-as-simple collision;
  - platforms or paths without Nanite.

  Our DOJO rule sets fallback RELATIVE_ERROR 0 on Nanite props. For trees, that is too heavy for HWRT. Pick a
  deliberate fallback (for example RelativeError 1 to 5 or 10-20% triangles) and look at it in the RT debug view. [U]
- **Nanite Foliage voxels replace LODs and impostors.** There is no crossfade and no pop. [D]
- **Non-Nanite (Route C / Fab fallback).**
  - LOD0 > LOD1 > LOD2 strictly descending, per ASSET_GUIDELINES, then an impostor (octahedral, or billboard cards).
  - Use dithered LOD transitions in the material.
  - Our LodGroup Empty rule applies; sockets and LODs are mutually exclusive in one FBX (5.8.2 measured).
- **Fab.** Nanite skeletal meshes, PVE and Dynamic Wind are Experimental, and 5.7 PVE assets don't load in 5.8. A Fab
  tree product should ship **Route A (static Nanite + WPO/PP2) as the baseline**, with Route B as an optional extra,
  and state the engine version. [D][inference]

---

## 10. Practical budgets for a 60 fps third-person game (proposed; measure before adopting)

The frame is 16.6 ms. As a starting split for vegetation on the target PC at 1440p with TSR:

- Nanite visibility + base pass for all foliage: **2.0 ms or less**.
- VSM rendering for foliage (after caching): **1.5 ms or less**.
- Lumen total: **4 ms or less** (Epic's 60 fps console figure).
- Skinning and wind: **0.2 ms or less**.

These are my proposals, not Epic numbers except the Lumen figure. [U]

**Background figures:**

- SpeedTree real-time library trees: **1k-12k triangles at LOD0**. [S]
- Common game hero trees: up to about **20k**. Conventional LOD chains run about 15k/10k/5k, then a billboard. [S]
- Epic's Nanite Foliage demo tree: **41M triangles, 12 unique parts, 2,160 part instances, 850 bones**. [D]
- Megaplants: **300-960 bones per tree** [M].

| Tier | Distance (guide) | Route A static Nanite | Route B Nanite Foliage | Non-Nanite fallback (Fab/low) | Wind | Shadows | Collision |
|---|---|---|---|---|---|---|---|
| **Hero** (the 4 niwaki; ≤ 15 m, few instances) | 0-15 m | 0.3-2M source tris, **opaque modelled needles** (no mask); 1 bark set + 1 needle set, 2K each (4K bark only if a close-up needs it) | assembly: ≤ 20 unique parts, ≤ 5k part instances, **≤ 1,000 bones** (bone reduction as needed) | LOD0 20-40k, LOD1 10k, LOD2 4k, impostor | PP2 or pad-level WPO, disable at 40-60 m; or Dynamic Wind | Rigid (or Auto if the sway must read) | UCX trunk and limbs / PhysAsset TrunkOnly |
| **Mid** (courtyard edge, walls) | 15-60 m | same asset; `NanitePixelProgrammableDistance` ≈ 40 m (masked parts only) | same asset; skinning continues | LOD1/LOD2 | WPO off beyond 60 m | Rigid | trunk only |
| **Background** (outside walls, slope near) | 60-300 m | pack trees (Megaplants/Scenery_Tutorial firs), Voxelize | voxels, `AnimationMinScreenSize` ~0.05-0.1 | 1-3k + impostor | none | Static; coarse pages | none, or a simple capsule where reachable |
| **Forest / mountain** | > 300 m | voxels or HLOD | voxels, no animation | impostor cards / HLOD, or landscape texture only | none | distance-field or none | none |

**Per-tree checks for the hero tier:**

- Unique-mesh count: 2 variants.
- Nanite *Overdraw* view shows no hotspots at the gameplay camera.
- VSM Invalidated pages about 0 with wind at rest, and bounded while wind is active.
- `stat GPU` Nanite + ShadowDepths delta under 0.3 ms per hero tree at the courtyard camera.

These thresholds are proposals. [U]

---

## 11. Verification checklist in Unreal (DojoLab, second fresh process, exact exported bytes)

1. **Import settings.** Nanite on; Shape Preservation per part (Voxelize on foliage, None or Separable on trunk);
   Import Mesh LODs as per the pipeline; textures BaseColor sRGB, ORM linear, Normal DirectX, pivot textures
   HDR/Nearest/NoMips.
2. **Nanite views.** *Overdraw*, *Evaluate WPO*, *Clusters*; voxels appear at distance with no holes in the trunk.
3. **VSM.** *Cached Page* view plus `r.Shadow.Virtual.Stats 1` at sunset, wind on and off, and LodBias 3 against 5.
4. **Lumen.** Compare Route A and Route B at the same spot. Check SWRT against HWRT, backface lighting (subsurface
   colour visible), and no light leaks under canopy pads.
5. **Performance.** `stat GPU`, `stat unit`, and `ProfileGPU` at the courtyard gameplay camera and at the widest
   shot; record ms in the asset's report.
6. **Collision.** Player walks around the trunk with no snagging on canopy; the wall-top route stays passable; navmesh
   is correct.
7. **Blind judge on image pairs.** Reference against the Unreal render, per the repo rule.

---

## 12. Uncertain items (verify before relying on them)

- The real masked versus opaque cost on this GPU: the "20-30%" figure is secondary.
- Whether a Substrate `TwoSidedWrap` slab is classified as a Lumen "foliage pixel" for the foliage-specific cvars.
- Whether Lumen runs HWRT or SWRT in DojoLab (`r.RayTracing=True`, no explicit `r.Lumen.HardwareRayTracing`).
- How Route B skeletal pines appear in SWRT Lumen (no mesh distance fields) and in HWRT (fallback quality).
- Headless Dynamic Wind JSON import: the Blueprint function opens a file dialog, so a C++ helper or a manual step is
  needed.
- Whether PVE "Extract From Mesh" plus Export can turn a Blender-authored trunk into a Nanite Foliage tree with our
  exact silhouette (PVE regrows and meshes; it may change the form).
- Blender USD export plus a `pxr` post-process adding `NaniteAssemblyRootAPI`/`SkelBindingAPI`/`NaniteBuildSettingsAPI`
  to import a skeletal Nanite assembly. The schema exists in 5.8.3; end-to-end use is untested.
- FBX vertex-colour gamma (`colors_type="SRGB"`) for wind masks: needs a round-trip test.
- PP2 axis and unit conventions from Blender (cm and Y flip), and whether the UV1 lightmap QA rule conflicts with a PP2
  UV.
- Whether MTree works with Blender 5.2 (it lists 4.3.1 to 5.1).
- The exact meaning of Megaplants texture suffixes `_CA`/`_NT`/`_NAH`, and their resolutions (inferred from names and
  sizes only).
- The 5.8 "Lumen Lite" setting name and cost.
- Budget numbers in section 10: they are starting proposals, to be measured.

---

## 13. What this means for the four niwaki black pines (and the next custom tree)

1. **Geometry.** Model the needle pads as opaque, modelled needle-tuft parts instanced over each pad, with a solid
   bark trunk and limbs. Avoid masked cards where possible (Epic guidance, and our "real geometry, crisp forms"
   rule). If needle cards are used for density, keep them to the pad interiors and give them a Pixel Programmable
   Distance.
2. **Build order.**
   - **Route A first.** A static Nanite mesh per variant (`SM_DKN_*`):
     - trunk and limbs: Shape Preservation None (or Separable);
     - pads: Voxelize;
     - pad-level wind by Pivot Painter 2 (one pivot per pad, parent = limb), with WPO Disable Distance ≈ 40-60 m and
       Shadow Cache Invalidation Behavior = Rigid.
   - **Then pilot Route B on one tree.** Feed the same PP2 data to `ConvertPivotPainterTreeToSkeletalMesh`, or use a
     Blender armature (one bone chain per limb, one rigid bone per pad). Import the Dynamic Wind JSON, place the tree
     with ISKM + `Wind_TransformProvider`, and compare cost and look against Route A.
3. **Keep the Blender build rig-ready from day one.**
   - Every pad and limb is a separate element with a clean pivot at its attachment point.
   - The hierarchy has at most 4 levels (trunk, limb, sub-limb, pad).
   - Store the hierarchy in the `.blend` so either route can be exported.
4. **Materials.**
   - Bark: Substrate slab, default wrap off.
   - Needles: slab with `Sub-Surface Type = Two-Sided Wrap`, one closure only.
   - `PerInstanceRandom` for hue variation across the 4 trees.
   - Build them in `Scripts/unreal/materials` under the PackMaterials lock.
5. **Collision.** `UCX_SM_DKN_<name>_NN` hulls on the trunk and the lowest limbs only; pads get none. Re-check the
   wall-top and climb routes.
6. **Budgets.** Hero tier from section 10. Measure in DojoLab at the sunset camera, record the ms, then blind-judge.
7. **Stop point.** If Route B needs the manual JSON dialog or PVE regrowth changes the silhouette, stop and show the
   user rather than patching.

---

## Sources

Local, read-only [M]:

- `C:/Program Files/Epic Games/UE_5.8/Engine/Build/Build.version` (5.8.3)
- `Engine/Source/Runtime/Engine/Private/Rendering/NaniteResources.cpp` (`r.Nanite.Foliage`, `AllowAssemblies`,
  `AllowVoxels`, `AllowMaskedMaterials`)
- `RenderCore/Private/RenderUtils.cpp`
- `Renderer/Private/Nanite/NaniteShared.cpp` and `NaniteCullRaster.cpp`
- `Renderer/Private/PostProcess/TemporalSuperResolution.cpp`
- `Renderer/Private/VirtualShadowMaps/*.cpp`
- `Renderer/Private/Lumen/*.cpp`
- `Renderer/Private/Skinning/SkinningSceneExtension.cpp`
- `Engine/Classes/Engine/EngineTypes.h` (`FMeshNaniteSettings`, `ENaniteShapePreservation`)
- `Engine/Public/Materials/MaterialExpressionSubstrate.h`, `Engine/Private/Materials/Material.cpp`
- `Foliage/Public/FoliageType.h`
- `Components/StaticMeshComponent.h`, `SkinnedMeshComponent.h`, `InstancedSkinnedMeshComponent.h`
- `Plugins/Experimental/DynamicWind/**` (uplugin, `DynamicWindSkeletalData.h`, `DynamicWindImportData.*`,
  `DynamicWindBlueprintLibrary.*`, `DynamicWindProvider.cpp`)
- `Plugins/Experimental/ProceduralVegetationEditor/**` (uplugin, Content listing, `MA_Foliage_Trees` strings)
- `Plugins/PCG/Source/PCG/Public/Elements/PCGSkinnedMeshSpawner.h`
- `Plugins/Runtime/USDCore/Resources/UsdResources/Win64/X64/plugins/unreal/resources/unreal/schema.usda`
- `C:/ProgramData/Epic/EpicGamesLauncher/VaultCache/Megaplan1093c7601c36V1`, `Megaplanb3dc3e6c5a59V1`;
  `Documents/Unreal Projects/DemoGame_1/Content/Megaplant_Library` (names and sizes);
  DojoLab/DemoGame_1 `Config/DefaultEngine.ini` and `.uproject` (read-only grep)

Web:

- [Nanite Foliage (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/nanite-foliage)
- [Nanite Assemblies (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/nanite-assemblies)
- [Procedural Vegetation Editor (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/procedural-vegetation-editor-in-unreal-engine)
- [UE 5.8 release notes](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes)
- [UE 5.7 is now available (Epic)](https://www.unrealengine.com/news/unreal-engine-5-7-is-now-available)
- [Tom Looman: UE 5.8 performance highlights](https://tomlooman.com/unreal-engine-5-8-performance-highlights/)
- [Tom Looman: UE 5.7 performance highlights](https://tomlooman.com/unreal-engine-5-7-performance-highlights/)
- [Nanite virtualized geometry (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/nanite-virtualized-geometry-in-unreal-engine)
- [Nanite technical details (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/nanite-technical-details)
- [Virtual Shadow Maps (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/virtual-shadow-maps-in-unreal-engine)
- [Lumen technical details (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/lumen-technical-details-in-unreal-engine)
- [Lumen performance guide (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/lumen-performance-guide-for-unreal-engine)
- [Overview of Substrate materials (Epic docs)](https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-substrate-materials-in-unreal-engine)
- [Shading models (Epic docs)](https://dev.epicgames.com/documentation/en-us/unreal-engine/shading-models-in-unreal-engine)
- [Pivot Painter Tool 2.0 (Epic docs)](https://dev.epicgames.com/documentation/unreal-engine/pivot-painter-tool-2.0-in-unreal-engine)
- [WPO material functions / SimpleGrassWind (Epic docs)](https://dev.epicgames.com/documentation/en-us/unreal-engine/world-position-offset-material-functions-in-unreal-engine)
- [Instanced Static Mesh Component (Epic docs)](https://dev.epicgames.com/documentation/en-us/unreal-engine/instanced-static-mesh-component-in-unreal-engine)
- [Forum: Foliage in current version and forward looking (Epic staff answer, Nov 2025)](https://forums.unrealengine.com/t/foliage-in-current-version-and-forward-looking/2685424)
- [Forum: Nanite voxelization holes (Separable fix)](https://forums.unrealengine.com/t/nanite-voxelization-holes-in-the-mesh/2723578)
- [obilang/UE_NaniteDynamicWindData (JSON wind import tool)](https://github.com/obilang/UE_NaniteDynamicWindData)
- [Large Scale Animated Foliage in The Witcher 4 (Unreal Fest Stockholm 2025 talk)](https://www.youtube.com/watch?v=EdNkm0ezP0o)
- [Class Central summary of the talk](https://www.classcentral.com/course/youtube-large-scale-animated-foliage-in-the-witcher-4-unreal-engine-5-tech-demo-unreal-fest-stockholm-2025-505458)
- [Bringing Nanite to Fortnite BR Chapter 4 (Epic tech blog)](https://www.unrealengine.com/en-US/tech-blog/bringing-nanite-to-fortnite-battle-royale-in-chapter-4)
- [Virtual Shadow Maps in Fortnite Chapter 4 (Epic tech blog)](https://www.unrealengine.com/tech-blog/virtual-shadow-maps-in-fortnite-battle-royale-chapter-4)
  (both 403 to the fetcher; content via search summaries)
- [Notes on foliage in Unreal 5 (shinsoj)](https://medium.com/@shinsoj/notes-on-foliage-in-unreal-5-3522b6eb159f)
- [Next-Gen Foliage: Nanite in UE 5.4 (nhance)](https://nhance-school.com/articles/ue5-nanite-foliage)
- [HISM vs ISM explained (StraySpark)](https://www.strayspark.studio/blog/hism-vs-ism-unreal-engine-explained)
- [Modular Tree extension](https://extensions.blender.org/add-ons/modular-tree/)
- [Pivot-Painter-for-Blender](https://github.com/Gvgeo/Pivot-Painter-for-Blender)
- [SpeedTree real-time modelling tips](https://docs.speedtree.com/doku.php?id=real-time_modeling_tips)
- [Megaplants: Japanese Cypress (Fab)](https://www.fab.com/listings/0843f3cf-41c1-4980-b46a-3df5742ddaef)
- [Megaplants: Yoshino Cherry (Fab)](https://www.fab.com/listings/97f6cdb0-810d-470d-9e3a-3c9f059e6763)
