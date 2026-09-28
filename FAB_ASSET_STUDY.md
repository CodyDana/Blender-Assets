# Blender -> Unreal -> Fab: Asset Creation Study

Date: 2026-09-17. Scope: Blender 5.2 LTS to Unreal Engine (UE) 5.8 to Fab, for the project folder `C:/Users/Cody/Desktop/Blender_Projects`. This study extends ASSET_GUIDELINES.md; section 3.12 lists the edits that file needs.

Updated 2026-09-25 for the character decision (player character on MetaHuman). The additions are dated and sit in sections 1, 2, 3.6, 3.7, 3.11, 3.12, 3.13, 4.7, 5.1, 6, 7 and 8, with sources [69]-[84]. The fact-checked basis is CHARACTER_PIPELINE_REVIEW.md [69]; the house rules are in ASSET_GUIDELINES.md section 12.

A bracketed number such as [n] points to section 8, which lists each source's URL and verification status. Open points carry [unconfirmed] or [disputed: ...]; lone forum reports are labelled.

## 1. TL;DR

This section gives the findings that matter most, including the three biggest changes. Read it first; sections 2 to 7 hold the detail and sources.

- **Nothing on disk is sellable**, because Kamish, Ea, the Naruto seal and Jin Mu-Won are third-party intellectual property, two project the copyrighted art as a texture, and AWM is a manufacturer's product name [64][65]. Fab bars "copyrighted or trademark protected names, branding, or content" [1][9], and one seller reported a 14-day suspension over a Coca-Cola logo [9] [unverified forum report].
- **Reusable parts** are the build scripts, the bake, manifest, SHA-256 and round-trip scaffolding in `export_modules.py`, the UE import commandlet, the seal decal technique, and the CC0 MakeHuman plugin for Blender (MPFB) base [1][65][66].
- **Method:** mid-poly hard-surface modelling for weapons, and the MPFB base re-skinned to the Epic skeleton for characters. Use the GUI for art, blender-mcp for live tweaks, and headless bpy for bakes, level-of-detail (LOD) meshes, quality checks and export; validate in the live UE 5.8 editor through Unreal MCP; keep one UE project per product plus FBX and .blend slots [3][15][23][33][45][47][65].
- **FBX first:** Epic's 5.8 notes say FBX "remains the main data format", and glTF skeletal import truncates to 4 bone influences [35][36]. Keep UnrealDemo on the legacy importer, with `Interchange.FeatureFlags.Import.FBX=0` and Import Normals, until a duplicated `DefaultFBXOBJAssetsPipeline` in Interchange, Unreal's newer import framework, passes the same checks with Recompute Normals OFF; import textures only [3][28][40][66].
- **First product:** an original realistic wuxia or fantasy melee weapon pack, tagged Realistic and physically based rendering (PBR), with 5 pieces, Fab's recommended realistic count, whereas stylized needs about 25. Sell it under the Standard License in the $9.99-$59.99 band, then apply for Limited-Time Free [15][57][58].
- **Change 1, intellectual property:** no franchise names, likenesses, product designations or projected art on anything for sale. Rename AWM_Sniper and fork JinMuWon_v2 de-branded [1][9][64].
- **Change 2, game-readiness:** add script gates that take the character LOD0 from 635k to about 100k triangles, bake real ambient occlusion (AO) into the red channel of the packed occlusion/roughness/metallic (ORM) texture, now a constant 1.0, write DirectX-style normal maps to disk, add UCX_ convex hulls, using Unreal's collision-mesh name prefix, for every static mesh, and generate per-part LODs [65][66].
- **Change 3, export:** one shared `export_fbx()` helper with Apply Transform OFF, FBX Units Scale, Triangulate ON and no leaf bones, a Fab-shaped UE project, and re-validation in Unreal before any README says "passed" [25][38][66].
- **Update 2026-09-25, characters:** the player character moves to MetaHuman. The CC0 MPFB body is converted with "From Custom Mesh" and given an original face. JinMuWon_v2 is frozen as a customization testbed and is never shipped or sold as-is; renaming it does not clear the IP. This replaces the character part of the "Method" bullet above as the default route; MPFB re-skinned to the Epic skeleton stays the fallback (3.6). It also supersedes the "fork JinMuWon_v2 de-branded" part of Change 1. See 3.6, 3.13 and 4.7 [69].

## 2. Reality check on the existing assets

This section audits each asset against Fab's content rules and says what can be salvaged. Use it to decide what to rebuild, rename or discard.

None is sellable as-is [64][66]. The table gives each asset's state, blockers and reusable parts.

| Asset | State on disk | Blockers; reusable parts |
|---|---|---|
| AWM_Sniper | Blockout, 4,772 tris, unapplied transforms, no textures | Product name [1][9]; Fab firearms need rigged parts + full animations [15]; remodel generic |
| Ea_Sword | 5,792 tris, partial UVs, projects The_Ea.webp | Fate/stay night art projected [1] |
| Kamish_Daggers | 150,588 tris, no UVs, projects manhwa art | Solo Leveling; 3x over budget [64][67]; outline scripts reusable |
| Ninja | Skin-modifier figure, no armature or body UVs, 29,362 tris | Original IP; rebuild |
| SummoningJutsu | 2-tri decal + 4096 RGBA bake; 855,766-tri render mesh in file | Naruto seal; notes record MasaFont OFL (max32002/masafont), YujiBoku OFL; no license file in References/Fonts [65] [unconfirmed]; decal workflow reusable |
| JinMuWon v1 | 365,212 tris, ORM AO constant | Fan art; SOURCE_NOTES admits no character rights; superseded |
| JinMuWon_v2 + modules | LOD0 635,371 tris; OpenGL normals; ORM.R constant; 3 of 26 Manny bone names; no collision; export unvalidated | Same IP; closest candidate after de-branding |

In the table, OFL is the Open Font License and IP is intellectual property. No official Fab text on fan art or firearm names was retrievable [unconfirmed]. The CC0 MPFB base passes if "modified so as to bring new value" and is cited with a link in the Technical Information field [1]. Keep the GPL-licensed MPFB code out of the Exports/ folder [66]. Declare MPFB under Third-Party Software [3]. The same clause bars fonts or textures under GPL, LGPL or CC-BY-SA, but not the Open Font License [1].

**2026-09-25 update: character tracks reviewed** [69][83]. Both character tracks were reviewed against UE 5.8.3.

- **JinMuWon_v2.** Dressed, it is still 635,371 triangles at LOD0 against the 80-120k budget. The body alone (Human_Clothed) is 87,691 and fits; hair (221,056) and clothing (326,624) are the overrun. Its 152-bone custom skeleton shares only 3 of 26 Manny bone names. The skin-tone and nail controls work, verified on UE 5.8.2 only.
- **CharacterLab.** MH_MaleBase is an editable copy of Epic's Kelvin preset. It has no rig, no high-resolution textures and no assembled Blueprint, because the Epic sign-in was never completed.
- **Outcome.** Both tracks aimed at the Jin Mu-Won likeness, which is third-party IP. Decision 2026-09-25: they are replaced by `MH_PlayerBase`, a MetaHuman with an original face (3.6). JinMuWon_v2 stays a frozen testbed.

**Not re-audited here.** The assets added since the 2026-09-17 audit have not been checked against this section: BlackCloak, BlackNunchucks, SnowFlower, the shuriken/kunai pack, the paper bomb and the smoke bomb. The review found two SnowFlower problems. Its source image, `SnowFlower_user_reference.png`, is unattributed, so its IP is unaudited. Its LOD0 is 456,024 triangles and even LOD2 is 118,428, against the 20-50k weapon budget [69].

## 3. Recommended production pipeline (Blender 5.2 to UE 5.8)

This section lays out the nine-step pipeline and the settings for each step. Use it while building product 1; 3.10 and 3.11 are the checks to run before any setting is frozen.

| # | Step | Do it | Why |
|---|---|---|---|
| 1 | Blockout, detailing | GUI + blender-mcp | Art judgement [45] |
| 2 | UVs | GUI unwrap; headless density check | bmesh measures [56] |
| 3 | Bake, ORM pack | Headless | Repeatable [67] |
| 4 | PBR texturing | External painter | No curvature/ID bake [24] |
| 5 | Collision, sockets, LODs | Headless | Exact naming [26] |
| 6 | Rig, skin | GUI weights; headless normalisation | Scripted gates [66] |
| 7 | FBX export | Shared headless helper | Identical settings [25] |
| 8 | UE import, validation | Unreal MCP + commandlet | One session [47] |
| 9 | Fab packaging | UE editor; headless zip/QA | Structure rejections [20] |

### 3.1 Scene and units

Work in Metric at unit scale 1.0, so 1 Blender unit (BU) equals 1 m; Unreal converts so 1 Unreal unit (UU) equals 1 cm [38][66]. Fab scales the standard exchange formats to a 192 cm humanoid and wants Unreal Engine assets Z-up [3]. Build modules on whole-metre multiples and put each pivot where the next piece meets [33]. Use `bpy.ops.object.shade_auto_smooth` for smoothing, because `use_auto_smooth` is gone since Blender 4.1 [23].

### 3.2 Modelling and budgets

For hard surface, build one mid-poly mesh. Add a Bevel modifier with Harden Normals and Face Strength Affected or All, then a Weighted Normal modifier with Face Influence and Keep Sharp. Bake support maps from it; there is no high-poly to low-poly bake [23][33]. Fab's bar is "no visual defects", quads or tris, correct normals, no non-manifold geometry and correct pivots [3][16]. Put hard edges on UV seams. Triangulate before mirroring and before baking. Set budgets by vertex count [32]. Fab publishes no triangle numbers, and no authoritative 2025-26 budgets were found [unconfirmed]. The house numbers stand: hero weapon 20-50k triangles, prop 1-5k, background piece 0.5-2k [67]; dressed character LOD0 about 80-120k, with hair cards and a scalp only [66]. Community texel-density targets are 10.24 px/cm for first-person or hero assets and 5.12 px/cm for third-person [33]. Padding is 8 px at 1K and 16 px at 2K [32]. Use power-of-two textures, 2048 for props and 4096 for hero and skin, and nothing above 4K for exchange-format uploads [3][16].

### 3.3 UVs

Use Angle Based for hard surface, and Minimum Stretch, the SLIM method since 4.3, for organic shapes [34]. Pack Islands with Exact Shape, Rotation Cardinal and a Margin Fraction of 16/2048 = 0.008. Never rotate or mirror UVs after baking. Offset mirrored shells by +1 in U before the bake [32][34]. For lightmaps, Unreal generates UV channel 1 from channel 0 and sets Lightmap Coordinate Index to 1. Hand-made lightmap UVs must be non-overlapping and inside 0-1. Lumen ignores lightmaps, but Fab still requires a non-overlapping lightmap UV with an index other than 0 [3][31].

### 3.4 Baking (Cycles 5.2)

Bake Selected to Active with a Cage. Use Max Ray Distance only when there is no cage. Set Normal Space to Tangent and Margin to Extend, measured in pixels. Join the high-poly objects first [24]. Blender has no Curvature or ID bake [24]. For those, use Substance 3D Painter 2026 at $199.99 perpetual on Steam or $24.99 per month, ArmorPaint 1.0 at $19, the free Ucupaint, or the bakers in section 5 [54]. Pack the ORM texture with AO in R, Roughness in G and Metallic in B, with sRGB off [33]. In `finalize_character.py`, bake real AO into ORM.R instead of writing `np.ones` [65]. Flip the green channel on write with `pixels[:,:,1] = 1 - pixels[:,:,1]` to produce DirectX normals, Fab in Launcher's default, then clear the `flip_normal_green` flag [16][66]. Set normal maps and ORM to Non-Color. Metals should sit at 0.95-1.0; the v2 buckle is at 0.72 [65][67].

### 3.5 Collision, sockets, LODs, Nanite

Unreal recognises collision and socket helpers in an FBX by name prefix; the table gives each rule.

| Helper | Name | Rule |
|---|---|---|
| Convex hull | `UCX_[RenderMeshNodeName]_00`, `_01`... | Closed convex; preferred; survives non-uniform scale [26]. **Measured:** the name must key to the render mesh NODE name, so a LOD0 node needs `UCX_<base>_LOD0_00`; `UCX_<base>_00` imports silently with zero collision [68] |
| Box / capsule / sphere | `UBX_` / `UCP_` / `USP_` | Unmodified vertices; fail under non-uniform scale [26] |
| Socket | `SOCKET_[RenderMeshName]_[Name]` | **Measured: must be an Empty (FBX Null), never a child mesh.** A child mesh is not imported as a socket and is silently welded into the render mesh, inflating its triangle count. An FBX socket also arrives with relative scale (100,100,100), so the pipeline writes a `.sockets.json` sidecar and applies it with `ue_import_sockets.py` [68]. Interchange skeletal sockets remain untested [43] |
| LOD group | Empty with custom property `fbx_type = "LodGroup"` parenting `_LOD0.._LODn` | Blender 5.2 writes an FBX LodGroup; bare `_LOD0` names are ignored; verify order [29] |

Ship one FBX per weapon when sockets ship. Epic allows one socketed mesh per FBX and imports collision only for the first mesh of a multi-mesh file [26][43]. **MEASURED 2026-09-17 on UE 5.8.2, legacy FBX importer (supersedes the pre-test wording):** the January 2025 report that UCX_ meshes block Empty-based SOCKET_ import does NOT reproduce; a hull and an Empty socket arrive together in one file. Sockets are applied from the sidecar after import rather than trusted to the FBX, which also fixes the scale bug and the naming (the importer names a socket after the whole node) [68]. For character LODs, use per-part ratios, seam protection and screen sizes of 1.0, 0.5 and 0.25, instead of a blind Decimate at 0.4 and 0.12 [66].

Epic's Nanite guidance: enable it wherever supported, except on translucent meshes, since 5.8 translucency is Experimental, and on morph-target meshes. Aggregates merely perform worse. Tune Fallback Relative Error, because the fallback mesh serves complex collision, lightmaps and default ray tracing. Skeletal Nanite is Experimental in 5.7 and 5.8 [30]. Fab's Nanite guidance: tag only dense meshes with Nanite on by default, because "simplistic unoptimized assets" are refused. State collision "where applicable" and which LODs ship, even zero [3][15].

### 3.6 Characters

Fab gives humanoids two routes. Route one is the Epic or MetaHuman skeleton, in A-pose, with unchanged bone names and orientations, inverse-kinematics (IK) bones unweighted and in place, the Third Person Template animations laid out in the overview map, and any extra bones documented. Route two is a custom skeleton with idle, jump, walk and run plus genre moves, such as attack and block for a fighter, or a full Control Rig. A Physics Asset is required either way [3][15]. Retargeting animations onto the 152-bone rig satisfies neither route; only re-skinning does. Option one: re-skin onto the full Manny/Quinn skeleton from Fab's "Mannequins Asset Pack", since 5.6+ templates ship only SKM_Manny_Simple, with one `root` bone at the origin carrying motion [41][66]. Option two: keep the custom rig with idle, jump, walk and run, a martial-arts attack set or a Control Rig, a tuned Physics Asset and a bone list [15][66]. Uefy 2 declares Blender 5.0 and Auto-Rig Pro 5.1, but only through third-party listings; the vendor page returned 403. Blender 5.2 is unverified for both, so test on a copy or use MPFB's game-engine rig target. Auto-Rig Pro's exporter lacks the 4.4+ shape-key action slots [41][42][66].

**2026-09-25 update: characters go the MetaHuman route.** The evidence is in CHARACTER_PIPELINE_REVIEW.md [69], and the house rules that follow are in ASSET_GUIDELINES.md section 12. The text above stays as the fallback route. These decisions were made on 2026-09-25:

1. **Base.** The player character is a MetaHuman built as a mix. Our CC0 MPFB-based body is converted with UE 5.8 "From Custom Mesh" into `/Game/Characters/MetaHumans/MH_PlayerBase` in the Exports/CharacterLab project. Its first From Custom Mesh conform ran on 2026-09-25 (`Scripts/MetaHuman/pb_conform.py`; reports in `WorkFiles/MetaHuman/player_base/`), so the asset exists but is work in progress. It is not rigged or assembled and has no high-resolution textures; those need spike stage 2a, and it has not passed any spike stage yet. The face is original. Claude picks one default face, and there is no face-selection step. Do not ship a lightly edited Epic preset such as Kelvin as the character; resale of edited presets is unconfirmed (4.7). A Kelvin copy is fine for testing.
2. **IP.** JinMuWon_v2 is frozen as a customization testbed. Never ship or sell it as-is, because it is a third-party likeness. Renaming it or lightly changing the face does not clear the IP. The test is whether a fan would recognise the character, so the default hair and outfit must not reproduce his signature look. This is not legal advice.
3. **Ownership.** Claude owns the whole character track. The user stopped Codex's work on it; Codex may still work on other assets it has locked separately.
4. **Face swap.** Build a library of pre-built interchangeable heads, not sliders.
5. **Runtime customization contract.** Keep the parameter names `SkinToneColor`, `SkinToneAmount`, `NailColor`, `NailPolishAmount` and `NailRoughness`, and add `IrisColor`. Give each character one dynamic material instance per material slot; this is a per-character runtime copy of the material. Push the same values to every face LOD material and to the body.
6. **Export gates are PLANNED, not implemented.** Once the MetaHuman is rigged, Scripts/pipeline gets skeletal gates checked against its real bone list: a skeleton and rest-pose hash compared with the locked base, `ik_*` bones kept, a skeletal test case, a triangle budget for the whole character, and skeleton sockets. *Update 2026-09-26: implemented except skeleton sockets; see 3.13.*
7. **Acceptance tests.** The review's MetaHuman "spike", a throwaway test build, is the acceptance test. Each multi-hour stage needs the user's explicit go-ahead:
   - 2a. Sign in, rig and assemble. The user types their own Epic credentials; no agent enters them.
   - 2b. Manny/GASP locomotion with a katana on `hand_r`.
   - 2c. Runtime skin and nail colour across every face LOD, checked at the seams at the neck, the back of the shoulders and the waist.
   - 2d. Two heads swapping in a packaged build.
   - 2e. Eight characters on screen hit the PROPOSED target (60 FPS at 1440p, High scalability, with cloth; not signed off), and cloth works on a Leader Pose follower.

   If a stage fails, stop and report. The review's fallback is the MPFB body re-skinned onto Manny, which is also several days of work.
8. **Open points and defaults.** Single-player versus multiplayer is not decided, so save cosmetics as IDs plus colours and add replication later if needed. Body shape is fixed, with one body per sex. The face rig defaults to Joints Only. Marvelous Designer has not been bought.

These are the 5.8 facts the route depends on:

- **From Custom Mesh** [70][71][72]:
  - It converts a head and body, separately or together in one step, from a humanoid mesh of any topology: a sculpt, a scan or an AI mesh. It runs inside Unreal.
  - An A-pose gives the best result. Since 5.7, any source pose from A-pose to T-pose is accepted.
  - The output is always MetaHuman topology in the MetaHuman A-pose, and it keeps the source proportions. In Epic's words, stylized or cartoon features "solve with varying quality", and extreme proportions can cause "volume loss or pinching" at the shoulders and hips.
  - Loose clothing is fitted as if it were the body. Holes, self-intersections and stray vertices destabilise the fit, so submit a clean, closed, unclothed body.
  - Our masks are in MPFB's UV layout and will not carry over [inferred], so redraw them in MetaHuman UV space.
  - **Sign-in.** Auto-rigging and the high-resolution texture download run on Epic's cloud and need a signed-in Epic account. Preview-resolution textures are generated locally without sign-in. Epic's docs say assembly also needs the downloaded source textures [unconfirmed locally; verify in the spike].
- **Assembly** [72]. Assemble as UE Optimized, not UE Cine:
  - UE Optimized has compressed textures, baked materials and more aggressive LODs. It is typically under 100 MB and comes in High, Medium and Low.
  - UE Cine has full-resolution textures and strand hair at LOD0, at about 1-2 GB.
  - Use card hair, and let the performance test choose between High and Medium.
  - Baked assembly bakes skin tone and nail tint into the textures and keeps only global colour adjustments. The runtime contract therefore needs either an override material with a nail mask that is not a child of Epic's MetaHuman materials (derived overrides still get baked) or 5.8's unbaked assembly, whose cost is unmeasured [verify in the spike].
- **Skeleton** [72][76]:
  - MetaHumans do not share Manny's skeleton asset. Epic plays Manny and Game Animation Sample (GASP) animation on them through its retargeters, such as `RTG_UEFN_to_MetaHuman_nrw`.
  - Community sources say the skeleton uses Manny's bone names and hierarchy plus extra joints. Whether it has the `ik_*` bones that Fab's Epic-skeleton route needs is UNCONFIRMED; record the bone list in spike stage 2b.
  - A May 2026 user report saw deformed retargets on a body made in 5.7. The poster said a manual two-stage retarget "minimized" the problem, and Epic has not replied, so treat it as a risk to test.
  - The face is a separate RigLogic mesh, so test every head.

### 3.7 FBX export settings (shared helper)

One shared export helper holds these settings so every FBX leaves Blender identically; MikkTSpace is the tangent-space standard Unreal uses.

| Option | Value |
|---|---|
| Selected Objects; Object Types | ON; Mesh (+socket mesh, LOD Empty), or Armature + Mesh |
| Scale / Apply Unit / Apply Scalings | 1.0 / ON / FBX Units Scale |
| Forward / Up | -Y / Z. House setting; imports and skins correctly in 5.8.2, Sep 16 revision; facing axis unchecked, see 3.11 |
| Use Space Transform / Apply Transform | ON / OFF |
| Smoothing / Apply Modifiers / Triangulate | Face / ON (OFF with shape keys) / ON |
| Tangent Space | OFF (UE MikkTSpace) |
| Add Leaf Bones / Only Deform Bones / Node Type | OFF / ON / Null |
| Animation | Baked, Key All Bones, Force Start/End, Sampling 1.0, Simplify 0.0, NLA Strips OFF, All Actions OFF |
| Path mode / Embed / Vertex Colors | RELATIVE or COPY / OFF / sRGB |

Why these values: "All Local" bakes the 100x factor into transforms, the 0.01-bone bug [25][38]. Apply Transform is "known to be broken with armatures/animations" [25]. The default -Z forward and Y up also works when Unreal's Convert Scene is on [25][39]. Unreal needs triangles and one animation per file [27]. Blender 5.2 still exports through the Python add-on at FBX 7.4; 5.1 only added shape-key normals [26][37].

**Amended 2026-09-25 (ASSET_GUIDELINES.md section 7):** Only Deform Bones ON still applies to our own prop and weapon skeletons. On the Epic or MetaHuman skeleton, keep the `ik_*` bones, unweighted and in place, as 3.6 requires, and never let a deform-only export strip them [3][15][69].

### 3.8 UE 5.8 import

Keep `Interchange.FeatureFlags.Import.FBX=0` in UnrealDemo, the validated commandlet path, until a duplicated Interchange pipeline passes the same 45 checks [28][66]. Interchange, the FBX default for assets since 5.5 [disputed, section 7], recomputes normals by default. In 5.8 it routes FBX through `DefaultFBXOBJAssetsPipeline`, so duplicating `DefaultAssetsPipeline` alone does nothing [28][35]. The table gives the matching settings for both importers.

| Setting | Interchange (5.8) | Legacy FBX Import Options (UnrealDemo) |
|---|---|---|
| Transform | Convert Scene ON, Force Front X Axis OFF, Convert Scene Unit ON, hidden behind the three-dot "Translator Settings" button beside the source path; Offset Uniform Scale 1.0 [38][39] | Convert Scene ON, Force Front XAxis OFF, Convert Scene Unit ON, Import Uniform Scale 1.0 [38][66] |
| Normals | Recompute Normals OFF in a duplicate of `DefaultFBXOBJAssetsPipeline` assigned at Project Settings > Engine > Interchange > Pipeline Stacks > Assets > Per Translator Pipelines > InterchangeFbxTranslator; MikkTSpace tangents [28][40] | Normal Import Method = Import Normals; Normal Generation Method = MikkTSpace [28][40] |
| Collision | Import Collision According to Mesh Name; One Convex Hull Per UCX [26] | Auto Generate Collision OFF with UCX_ present; One Convex Hull per UCX [26]. Import Mesh LODs must be ON or the LOD meshes merge into one [68] |
| LODs, lightmaps | Import Lods (requires Bake Meshes); Lod Groups picker; Generate Lightmap UVs ON unless Nanite; Build Nanite for dense opaque meshes [29][30][31][40] | Import Mesh LODs, or LOD Import > Import LOD Level N per file; Generate Lightmap UVs ON [29][31][66] |
| Materials | Import Materials OFF; 5.7+ makes PhongSurfaceMaterial instances anyway [unconfirmed]; Detect Normal Map Texture ON; Flip Normal Map Green Channel only for OpenGL maps; sRGB off on ORM/normals [40][44] | Do Not Create Material; Invert Normal Maps only for OpenGL maps [40][44] |
| Skeletal, animation | Skeleton picker only with identical bone names and order; one root; Import Morph Targets ON; Use T0 As Ref Pose only on a "no Bind Pose" error; Bone Influence Limit 4; Import Only Animations for animation FBX [27][40][41][66] | Same fields; Create Physics Asset ON, then hand-tune; one animation per file [27][66] |

Build one `M_Master` material with `MI_` instances [3].

### 3.9 Packaging the UE format

Each row maps a packaging check to its clause in the Fab Technical Requirements page; the Check column says what the clause covers.

| Check | Clause [3][15] |
|---|---|
| No-login link to a zip with one project folder; password in Version Notes; link live until Live | 4.2.1.a-c |
| Only `Config/`, `Content/<Pack>/`, `<Pack>.uproject`; no Binaries/Intermediate/Saved/Plugins | 4.3.7.2.a-b |
| Type-sorted subfolders; descriptive alphanumeric names; paths <= 140 chars; redirectors fixed; unused plugins `Enabled=false` | 4.3.7.2.c-d, 4.3.7.1.b-c, 4.3.1.e, 4.3.1.h |
| UE 5.8 listed; zip built in the earliest ticked version | 4.2.2.b, 4.2.1.b |
| Asset Pack; no Level Blueprints or required .ini | 4.2.4 |
| Overview map with every asset; lighting built; no errors or consequential warnings on load or in Play In Editor (PIE); no z-fighting | 4.3.2 |
| Static meshes: collision, LOD statement (even zero), non-overlapping lightmap UVs, Lightmap Coordinate Index != 0 | 4.3.3.2 |
| Textures power-of-two, max 16348 (sic) per side; material instances | 4.3.3.1, 4.3.3.5 |
| Skeletal: Epic/MetaHuman skeleton or custom rig + animations/Control Rig; Physics Asset | 4.3.3.3-4 |
| No /Engine/ or Starter Content references; Epic sample content as example only; dependencies and third-party software declared | 4.3.1.f-g, 4.2.5 |
| English documentation link; Technical Information filled; AI / Mature / Promotional flags | 4.3.8, 1.8.4, 1.8.8-10 |

Versions: tick only 5.8 for product 1. If you also tick 5.6 or 5.7, build lighting and save the zip from the earliest ticked version, then confirm it opens clean in 5.8. That is clause 4.2.1.b; an April 2025 rejection was a 5.1 project tested in 5.5 with unbuilt lighting [3][20]. Self-tests: migrate `Content/<Pack>` alone into a blank 5.8 project [3][15]. Then delete `Config/` and reopen the overview map, because a Config-dependent map drew a "change to Complete Project" rejection [20].

### 3.10 Headless QA checklist

These Blender Python calls were verified on the installed 5.2.0 [56]. Assert each item before export.

1. `ob.matrix_basis` is the identity and unit scale is 1.0. Post-modifier triangle counts, read from `evaluated_get(dg).to_mesh().loop_triangles`, are within budget, and LOD counts descend.
2. There are no n-gons, no non-manifold edges, checked with `BMEdge.is_manifold`, and no loose vertices.
3. UV0 is present. Texel density, computed as UV area over `BMFace.calc_area()`, is within tolerance. No overlap, checked with `uv.select_overlap`. Islands sit inside 0-1. Static meshes carry a clean UV1.
4. Images are power-of-two, present and in the correct colour space. Normal maps are flagged DirectX.
5. Names use the SM_, SK_, T_, M_ and MI_ prefixes. Every SM_ has a `UCX_<that object's exact name>_##`, so a `_LOD0` node needs the `_LOD0` in its hull name too. Sockets are Empties. No franchise or brand strings appear.
6. Skeletal: one root at the origin, at most 4 influences per vertex, 0 unweighted vertices, weight error below 1e-6, and no "." in bone names [66].
7. One action per animation export, with the motion on the root. Round-trip through `bpy.ops.wm.fbx_import` and assert skeleton-hash equality. Write the manifest, the SHA-256 and the AI flag.
8. On the Unreal side, through the commandlet or Unreal MCP: the mesh faces the same axis as SK_Mannequin, which is +Y; the counts match the manifest; no /Engine/ dependencies [47][66].

### 3.11 Verify in UnrealDemo before standardising

**All four tests were run on 2026-09-17 against copies of the validation project; results are folded in above and in ASSET_GUIDELINES.md section 6.2 [68].** Test 1 failed as first built and produced the two naming rules now enforced by `Scripts/pipeline`. Tests 2, 3 and 4 passed. Re-run them after any Unreal upgrade.

**2026-09-25:** the installed engine is now UE 5.8.3, but all four tests, the skin and nail checks, and the BlackCloak recolor were measured on 5.8.2. Re-running them on 5.8.3 is pending, so treat those results as 5.8.2-only until then [69][82].

1. UCX_ and SOCKET_ in one FBX. **Result: failed as first built, then fixed.** A hull named for the file base rather than the LOD0 node gave zero collision, and a child-mesh socket was welded into the render mesh. With `UCX_<node>_00` and an Empty socket both arrive [68].
2. LOD group: a `LodGroup` Empty with the custom property `fbx_type`, parenting `SM_Test_LOD0..2`. Expect three LODs with LOD0 the densest; a February 2025 report saw LOD0 and LOD1 swapped [29].
3. Facing axis: import the current `JinMuWon.fbx` and compare its forward axis with SK_Mannequin. The commandlet never checks this [66].
4. Importer choice: duplicate `DefaultFBXOBJAssetsPipeline` with Recompute Normals OFF, re-enable Interchange in a copy of UnrealDemo, rerun `ImportCharacter.ps1`, and compare the result with the legacy 45/45 [28][66].

### 3.12 Changes to ASSET_GUIDELINES.md

These edits stop the house guidelines file contradicting the findings above.

- **Target and export.** Target UE 5.8, not 5.6 [66]. Strike the line "Blender 5.0+ FBX exporter is significantly improved (skeletal hierarchies, shape keys)", which the release notes do not support [37]. In section 6, set Apply Transform OFF (it was ON), Use Space Transform ON, FBX Units Scale, Triangulate ON, Add Leaf Bones OFF, Tangent Space OFF (it was ON), and one action per FBX [25][38].
- **Textures and layout.** Section 3: ORM.R is baked AO, and normals are DirectX [16][65]. Sections 2 and 4: the LOD0 budget, texel density, padding and the UV1 rule [31][32][33]. Sections 5 and 6: `modelname_suffix` texture naming, sockets, the LOD-group Empty, Nanite and the Fab layout [3][16][26][29]. Section 8: MCP refuses Blender's `-b` background flag and sends telemetry home [45]. Add "Skeletal meshes" and "Marketplace" sections.
- **Amendments approved 2026-09-25** [69]:
  - **Section 7, Only Deform Bones.** Keep it ON for our own prop and weapon skeletons. For anything on the Epic or MetaHuman skeleton, keep the `ik_*` bones, unweighted and in place (see 3.6); deform-only must not strip them.
  - **Section 9, "regenerable end to end from Scripts/".** GUI- or cloud-authored SOURCE assets are allowed, such as MetaHuman Creator characters and Marvelous Designer `.zprj`/`.zpac` files, if three conditions hold. The source files are versioned and backed up. Their recipe is written down, including settings, presets, weights and hashes. Every step downstream of them is scripted.
  - Characters get a new ASSET_GUIDELINES.md section 12.

### 3.13 Clothing and cosmetics pipeline

This section gives the approved order for clothing and cosmetics on the MetaHuman base (3.6), and what each tool costs. It was added 2026-09-25 and none of it has been tested here yet [69]. The table gives the order.

| # | Step | Do it | Notes |
|---|---|---|---|
| 1 | Concept | Design sheet | IP check: original design, no franchise look. Choose each piece's recolor regions and physics tier. The tiers are skin weights, then bone chains, then Chaos Cloth for hero pieces only [inferred] |
| 2 | Body | MetaHuman | Take the locked body from MetaHuman. Marvelous Designer (MD) 2025.2 imports MetaHuman DNA directly; the alternative is Geometry Export to FBX [72][78] |
| 3 | Garment | MD for draped pieces; Blender for hard ones | MD: hakama, haori, sleeves, cloak. Blender: armor, belts, bracers, tabi, tight suits [inferred]. Keep MD files as versioned sources under amended guidelines section 9 (3.12) |
| 4 | Cleanup | Blender | Retopology, UVs, bake, LODs, a separate low-poly simulation mesh, and body hiding. Scripts/pipeline has no high-to-low bake yet. USD can instead go from MD straight into a UE Cloth Asset [69] |
| 5 | Weights | Blender, or Unreal Dataflow | Fixed-size pieces: Data Transfer, then Robust Weight Transfer, then hand fixes. Unreal's Dataflow transfers weights for resizable outfits. Whether garments keep the 4-influence limit is open [unconfirmed] |
| 6 | Unreal | Same skeleton | Import onto the locked base skeleton. BlackCloak shows why: its skeletal version got a separate skeleton asset of its own [69] |
| 7 | QA | In Unreal, not in Blender renders | Seiza, crouch-walk, ledge hang, wall-run, roll, flips, ragdoll, katana draw, scabbard vs cloak, hood vs every head, LOD transitions, 8+ characters on screen |
| 8 | Template | Frozen from pilots | Pilot A: a fitted inner suit made in Blender. Pilot B: the cloak via MD, USD, Cloth/Outfit Asset and Chaos Cloth. Pilot C: one weapon at 20-50k triangles with a socket and an animation layer. Then freeze naming, export settings, LOD rules and the QA checklist |

**Update 2026-09-26: the garment pipeline exists and is measured** (ASSET_GUIDELINES.md 12.10, `Scripts/garments/README.md`). Steps 2, 5 and 6 above are now tooling:

- **Step 2, the body:** the locked fitting body is `References/Characters/MH_PlayerDefault/` (LOD0 body, face skin, the BrushCut helmet as the hair proxy, `metahuman_base_skel`), hashed in `base_lock.json` and cross-checked against Unreal's reference skeleton (0.0005 mm). Garments start on it with `new_garment.py`, typed `cloak`, `fitted`, `rigid_head` or `rigid_socket`.
- **Step 5, weights:** answered for the MetaHuman. The body itself uses up to 8 influences, so fitted garments take the body's weights with at most 8; cloaks stay on the spine chain (at most 2); rigid pieces use one bone. The fitted path interpolates the body's weights at the nearest body triangle; it has only run on test garments so far, so Robust Weight Transfer stays the fallback for a real one.
- **Step 6, Unreal:** `export_fbx(kind="garment")` writes the whole skeleton with the armature object named `root`. In a CharacterLab commandlet the regressed BlackCloak and two test garments import onto `metahuman_base_skel` with all 342 bones and the body's reference pose (0.0001 cm; 0.139 deg on a 0.1 mm twist bone, which the in-game one-off shows too).
- **Gates** (`garment_qa.py`): skeleton and rest-pose hash vs the lock; body intersection at rest and in four poses on the armature (0 vertices deeper than 1 mm at rest, at most 1 % deeper than 5 mm per pose); weights per type; garment, cloth (6,000 triangles) and whole-character budgets; material sections and the cloth PinMask. 13 test cases plus an FBX round trip; the BlackCloak regression matches the 2026-09-26 one-off (see 12.10 for the numbers).
- **Budget finding:** the MetaHuman base alone is 121,892 LOD0 triangles (body 60,816, face 34,514, hair cards 26,562), over the 80-120k dressed budget of section 2 before any garment. Needs a decision: a higher budget, UE Optimized Medium, lighter hair cards, or body hiding under outfits.

**Risks to test** [69][75][77]:

- **Maturity.** The Chaos Cloth editor is Production-Ready in 5.8, but the Outfit Asset is still Beta in 5.8.3 [77][82].
- **Cloth on a follower.** Epic's 5.8 modular-characters table marks Leader Pose followers "Physics: No" and says nothing about cloth. Test cloth on a follower in spike stage 2e [unconfirmed].
- **Lost cloth sim.** A July 2026 user report says 5.8 loses the cloth simulation when an outfit is converted to a parametric wardrobe asset. Epic had not responded as of 2026-09-15.
- **Resizing.** In September 2025, the 5.6 era, Epic said outfit resizing cannot run at runtime. Nothing confirms that for 5.8. Body shape is fixed by default, so this does not apply unless that changes.
- **Cost.** One undated third-party guide puts unoptimized cloth at 1-3 ms per character [81] [unverified].

**Assembling cosmetics** [69][75]:

- **Method.** Start with Leader Pose, where one mesh drives the others' animation. It is cheap on the game thread, heavy on the render thread, keeps morphs and gives followers no physics of their own. Mesh Merge renders cheapest but loses morphs. For Mutable, the 5.8 release notes say "production readiness", but the installed 5.8.3 plugin says Beta [disputed].
- **Body hiding.** Options are trimmed bodies per outfit, like Human_Clothed, MetaHuman hidden-face maps, opacity masks or Mutable clipping. Keep trimmed edges away from the known seam lines at the neck, the back of the shoulders and the waist.
- **Saved data.** Store cosmetics as Primary Data Assets with soft references, loaded asynchronously, and save only IDs and colours. If multiplayer is chosen, the server picks the parts and replicates only the IDs and colours.
- **Weapons.** Put the sockets on `hand_r`. Use per-weapon animation layers on Lyra's pattern (`ALI_ItemAnimLayers`).

**Tool costs.** The table gives each tool's cost and the date of its source.

| Tool | Cost | Note | Source, date |
|---|---|---|---|
| MetaHuman | no upfront fee | Standard UE EULA; see 4.7 | [74], accessed 2026-09-25 |
| MD Personal | $39/mo or $280/yr | For "solo freelancers, hobbyists and sole proprietors". Whether a one-person LLC qualifies is unconfirmed, so ask the vendor | MD pricing guide, 2026-09-18 [78] |
| MD Indie | price not published | Requires 2+ employees, so it does not fit a one-person LLC | MD announcement, 2026-01-21 [78] |
| MD Enterprise | $199/mo | - | CG Channel, 2026-04-20 [78] |
| MD trial | free, 14 days | Commercial-use and export terms unknown [unconfirmed]; check them before shipping anything made with it | MD trial page, accessed 2026-09-25 [78] |
| CLO (Individual) | $50/mo or $450/yr | Aimed at fashion production; MD targets games | Price: MD pricing guide, 2026-09-18 [78]; positioning: clo3d.com comparison, 2026-09-18 [79] |
| Simply Cloth (Blender) | $36-66 | $66 includes the Cut & Sew pattern library | Superhive, accessed 2026-09-25 [80] |
| Robust Weight Transfer (Blender) | free | GPL-3.0; fixes armpit and crotch weights | GitHub, accessed 2026-09-25 [80] |
| Character DNA add-on (Blender, base edition) | free | Third-party (Poly Hammer), built on OpenRigLogic; Blender 4.5+, UE 5.6+ | CG Channel, 2026-07-17 [80] |

The pricing guide and the CLO comparison are vendor-authored.

## 4. Fab

This section covers the seller side of Fab: onboarding, money, content policy, formats, listing media, post-publish duties and the MetaHuman selling rules (4.7). Use it when setting up the account and filling in each listing.

### 4.1 Seller setup

Onboarding is self-serve: the agreement, a Publisher Profile, a Creator Code, Trader Verification, the tax survey and Hyperwallet. No approval queue is documented [6] [unverified]. Self-identify as a Trader or a Non-Trader under Publisher Settings > Trader Details. Unidentified sellers have been unable to sell to EU buyers since February 2025. Traders upload a government ID and verify a phone; the contact email is public. Non-Traders carry an "EU consumer rights do not apply" disclaimer [8]. Register as a Trader, one who "sells frequently for profit", with a dedicated business email [8]. Sellers report Trolley verification taking 5-9 weeks against a stated 3-7 days [8] [unconfirmed forum reports]. File the W-9 tax form at once, because there is no payout without it, and mail the class-action-waiver opt-out within 30 days [1].

### 4.2 Money

You keep 88% after sales tax, processing fees, discounts and fraud charges. Refunds, chargebacks and wire fees come off payouts. Payment is in USD, with a $100 minimum rolled monthly and a forced payout after a year [1][13]. Timing is [disputed: agreement within 45 days of month end, never beyond 60; docs ~30; sellers report the 15th]; plan on 45-60 days [1][6]. Quarterly Revenue Reports become binding unless challenged within 12 months [1]. Hyperwallet, not Fab, handles transfer problems [13]. The agreement is non-exclusive apart from update parity [1]. For cross-listing, Unity pays 70% and CGTrader 55-80% [62] [unverified].

Prices sit on fixed rungs; the table shows the increment per range.

| Range (USD) | Increment | Example |
|---|---|---|
| $0.00 | free only | CC-BY or Standard |
| $0.99-$99.99 | $1 | $19.99 |
| $104.99-$149.99 | $5 | $104.99 |
| $159.99-$249.99 | $10 | $159.99 |
| $274.99-$499.99 | $25 | $299.99 |
| $599.99-$1,499.99 | $100 | $699.99 |
| > $1,500 | contact Fab Support | - |

All prices end in .99 [4]. Offer both Personal and Professional tiers. Personal is for buyers whose group grossed at most $100,000 in 12 months. The rights are identical, apart from the Unreal Editor for Fortnite (UEFN) Reference Only option [2][4]. CC-BY is free-only and cannot carry the NoAI tag, so use the Standard License for anything you may charge for [1][4].

What you give up: under the Fab Distribution Agreement, section 2(c)(i), the license-grant clause, you grant "an irrevocable, royalty-free, sublicensable (through multiple tiers), fully paid-up, worldwide license". Moral rights are waived in section 2(e). No credit is owed. Withdrawn content stays licensed to earlier buyers under section 10(b)(ii) [1][2]. Under the Fab end-user license, buyers may modify and ship assets in games and linear media, and share them with collaborators. They may not resell them standalone, because projects "must reasonably add value beyond the value of the Content", and may not expose them in level-editing or modelling tools that allow export, under end-user license section 6(b)(ii)-(iii) [2]. No GPL, LGPL or CC-BY-SA material is allowed, and Epic sample content is display-only, under end-user license section 6(a) and Distribution Agreement section 3(f)(ii) [1][2]. Audit fonts and CC0 inputs against this.

Seller-run sales: 10-50% off for at most 14 days, only after 30 days at an unchanged price, with a 30-day cooldown, requested 14-60 days ahead through a Fab Sale Case. Epic event sales pay on the base price and averaged up to 50% of monthly revenue in 2025. No savings claims on the listing [7][12].

### 4.3 Content rules

No trademarked or copyrighted names, branding or content unless licensed, and no publicity-right violations [1][9]. Mature content, such as gore, nudity, drugs or alcohol, is allowed only when the whole product is rated Mature. If any part of the files or media is mature, the whole product must carry the flag, so keep weapon renders bloodless [3][10] [unverified]. The CreatedWithAI tag is mandatory when a "material portion" is AI-generated; upscaling and content-aware fill are excluded. Epic may apply the tag itself and removes mis-declared products. NoAI, Standard License only, bars buyers from AI training [1][11] [unverified]. Our reading of the material-portion test, not Fab's text: output from Rodin, Hunyuan3D, Meshy or Tripo triggers the tag even after retopology, while procedural bmesh, MakeHuman and hand modelling do not. Fab is silent on AI-assisted textures over hand-modelled meshes, and on build scripts written by a large language model, which "aid in the creation of new content" [unconfirmed] [11][45]. Keep a per-product decision log. The selection changes without re-review [5]. Declare paid promotional content [8].

### 4.4 Formats and technical requirements

The table gives the limit and rule for each format slot.

| Slot | Accepts | Limit / rule |
|---|---|---|
| Unreal Engine | hosted zip of one project or plugin | 15 GB; list UE 5.8 at first submission; built in the earliest ticked version [3][15] |
| FBX / OBJ / GLB / GLTF / USD / USDZ | that format only, one per type | 6 GB (docs print "6B") [15] |
| Blender / Maya / Max / C4D | that app's files only | 6 GB; Fab reads counts from .blend; no Launcher export [15][21] |
| Additional Files (max 3) | product-related; count toward Mature rating | 6 GB each [3][15] |

Only .zip is accepted, never a zip inside a zip [3][16]. Exchange-format packaging follows the Launcher's auto-mapping best practice, not an approval rule. Place textures beside the model, named `modelfile_suffix` with the suffixes basecolor, normal, roughness, metallic, ao, emissive and height, in lowercase ASCII, with DirectX normals. For multi-asset packs, give each asset a unique prefix such as `sword1_basecolor.png`, or one folder each. Matching fails in subfolders when a .glb, .gltf or .usd file sits in the parent. glTF and GLB files should embed textures or use relative paths [16]. Fab auto-converts FBX listings to GLB, glTF and USDZ, so a GLB slot is optional [15][21]. Minimum counts: realistic props 1, with 5 recommended; stylized about 25; firearms 1, rigged and animated; animations 10 or more; materials 1 [15] [unverified].

### 4.5 Listing media and text

The table gives the media limits.

| Item | Limit |
|---|---|
| Gallery images | min 1920x1080, JPEG or PNG, < 3 MB each, < 25 MB total [15] |
| Video | 1920x1080, MP4/MOV/WEBM, <= 300 MB [15] |
| 3D preview | < 500 MB [15][17] |
| Thumbnail | uploader enforces "16:9 ratio or 1920x1080px" [18]; a 5 MB cap appeared only in a search snippet [unconfirmed] |
| Minimum | thumbnail plus one image, 3D preview or video [6] |

Two unanswered bug reports, from October 2024 and January 2026, say exact-1080p uploads are served at 720p [22] [unverified]. Render at 3840x2160 and save as a JPEG under 3 MB. No standalone Unreal Engine logos or sale marks; use a grid overview image for packs [19]. Write in English. Keep the title ideally at or under 30 characters. Fill every technical field and tag slot. Search reads the thumbnail [3][5][59].

### 4.6 Review and updates

The listing states run Draft, then Pending Approval, then Changes Needed or Approved, then Live. Declined means a new listing. There is no first-review service-level agreement [unconfirmed: community reports 2-5 hours to 2-3 days, plugins up to 18 days]. Fab says "most updates are processed within 24 hours" [5][14]. Documented rejections: folder structure, unbuilt lighting in the latest version, Config-dependent or unlit maps, dead links, non-16:9 thumbnails, brand logos and loose file dumps [9][20]. Editing a live listing spawns a moderated duplicate while the original stays live [5]. The table shows which edits trigger a review.

| Requires review | No review |
|---|---|
| Title | Product type, category |
| Description | License selection, prices |
| Thumbnail | Tags, linked forum thread |
| Images, video, 3D media | AI usage, promotional declaration |
| Open-text engine technical details | 3D technical detail fields |
| Format files and engine packages | Supported target platforms |

Post-publish duties [1][3][5][13]: keep every product on one of the three latest engine versions, under clause 4.2.2.c of the Fab Technical Requirements page, and update it "shortly after each new engine release"; for 5.9, Edit Existing Version adds compatibility without new files. Monitor a support channel set in Publish Settings, and ship bug fixes while listed. Refunds: buyers ask within 14 days; Epic auto-refunds if never downloaded; you may approve for any reason; declined requests escalate to Fab Support; every refund comes off the next payout.

### 4.7 Selling MetaHuman-based characters and outfits

Added 2026-09-25. This section covers the extra Fab rules for MetaHuman characters, outfits and grooms, and the MetaHuman license. Use it before listing anything built on the MetaHuman base. None of it is legal advice.

Fab accepts characters made in MetaHuman Creator on UE 5.6 or later, and MetaHuman-compatible clothing and grooms. Characters from the old web app, 5.5 and earlier, are licensed for Unreal projects only and cannot be sold [73]. The table gives the listing rules.

| Rule | Detail |
|---|---|
| Package | Verify and package with MetaHuman Manager as `.mhpkg`. The MetaHuman format is UE 5.6+ only. An assembly may carry both Cinematic and Optimized packages [73] |
| License and AI tag | The NoAI tag is applied automatically, and CC BY 4.0 is not allowed [73] |
| Clothing skeleton | Build skeletal clothing on the MetaHuman base skeleton, or a very close variant, without reparenting any bones [73] |
| Outfits | Chaos Outfit assets (`OA_`), with a matching body included for each outfit size [73] |
| Folders | Fixed top-level folders: `/Game/Outfits`, `/Game/SkeletalClothing`, `/Game/Grooms`, `/Game/CharacterAssemblies` [73] |
| Known 5.8 issue | Packaging a character with clothing or grooms from outside the plugin, such as Fab wardrobe items, produces an `.mhpkg` missing its parent materials. The clothing then renders with the default grid texture. There is no workaround yet, so test every package for it [70] |
| Presets | Whether a lightly edited Epic preset such as Kelvin can be sold is UNCONFIRMED; Epic's pages do not say. Sell only original designs [69][73] |
| Outside `.mhpkg` | If the MetaHuman skeleton lacks `ik_*` bones, anything sold through Fab's Epic-skeleton route (3.6) needs them added [inferred; verify in the spike] [69] |

The license points [74]:

- Since UE 5.6 (June 2025), MetaHuman falls under the standard UE EULA.
- For a game made in Unreal, the usual royalty applies: 5% of gross revenue above $1M per product.
- The $1M seat-license threshold is for rendering MetaHumans outside Unreal. It does not apply to a game made in Unreal.
- Using MetaHuman characters or animation curves to train or test AI is banned. Using MetaHumans in AI-assisted workflows is allowed.

The IP rules in 4.3 still apply in full. A Jin Mu-Won likeness cannot go on Fab under any name (3.6). Log any AI-generated design reference behind a sold character in the per-product decision log (4.3).

## 5. Tooling

This section rates the add-ons, the two Model Context Protocol (MCP) bridges and the AI generators against Blender 5.2 and Fab's resale rules.

The table rates each add-on.

| Tool | Blender 5.2 | Price | Verdict |
|---|---|---|---|
| Hard Ops / Boxcutter | 3.5-5.2 | $38 | Buy [54] |
| MESHmachine 0.21 / DECALmachine 2.17 | 4.2-5.2 / 4.3-5.2 | $44.99 / $54.99 | Buy; DECALmachine atlases feed UE decals [54] |
| Zen UV 5.4 | 4.2-5.2 | $39 | Buy: texel density, trim sheets, overlap checks [54] |
| UVPackmaster 4 PRO | 2.93-5.2, GPU | $55 | Only if Pack Islands falls short [54] |
| TexTools 1.6.1 | Broken on 5.0+ (issue #268) | free | Avoid [54] |
| SimpleBake 2.9.11 | Blender 5 edition | not captured | Background baking, channel packing, Bake Health Check, curvature/ID [54] |
| Bake Wrangler 2.0.4 | 5.0.1+ | $40 commercial / $25 indie | Node-based batch bakes, curvature/ID [54] |
| RetopoFlow 4 | 4.2-5.2 | $59.99 (CG Channel: $85.99) [disputed] | Character retopo [54] |
| Quad Remesher 1.4.1 | 5.0 per users; 5.2 unconfirmed | $109.90 Pro (Indie non-commercial) | Trial first [54] |
| Send to Unreal (poly-hammer 2.6.7) | tested 3.6/4.2, UE 5.3/5.4; Epic repo idle since 2023 | free | Skip; FBX + Unreal MCP [42][47] |

### 5.1 blender-mcp

This is the setup as confirmed on this machine on 2026-09-25; it replaces the 2026-09-17 text. Day-to-day instructions are in the "2026-09-17 update" section of `Scripts/BLENDER_MCP.md`; its top section predates the rename [45][84].

- **Server.** Upstream renamed the package blender-mcp to mcp-for-blender (the installed 2.0.0 metadata still links github.com/ahujasid/blender-mcp). Version 2.0.0, released 16 September 2026, adds `export_scene` and an opt-in safe mode. It is installed as a uv tool, with the shim `C:/Users/Cody/.local/bin/mcp-for-blender.exe`, and both agents' registrations point at that shim. The older `blender-mcp.exe` shim still sits in the same folder, but nothing uses it.
- **Addon.** Version 1.7 with protocol 7 is installed in the Blender 5.2 addons folder as `blender_mcp.py`. The old `blender_mcp_addon.py` was removed from that folder, with backups in `Backups/blender_mcp_setup_2026-09-17`. The project copy at `Scripts/blender_mcp_addon.py` is addon 1.2 and stale; never install it.
- **Two agents, two ports.** Claude Code uses port 9876 and Codex uses 9877, and each drives its own GUI Blender window.
  - **Launch** with `Scripts/launch_blender.ps1 -Blend Assets\<X>.blend -Port <9876|9877> -Agent <claude|codex>`.
  - **Launcher checks.** It refuses a port that already has a listener. It claims `WorkFiles/locks/<X>.json` through `Scripts/pipeline/lock.py` first, and refuses an asset the other agent has locked. It then starts the socket through `Scripts/mcp_autostart.py`.
  - **No `-Blend`.** Without it, the launcher opens a scratch file and takes no lock.
  - **Release** a lock with `py Scripts\pipeline\lock.py release <X> --agent <agent>`. Never open, save or run headless scripts against an asset whose lock the other agent holds.
- **Probe.** `Scripts/mcp_probe.py --port <n>` checks a server and addon link without an AI client, using `--list` or `--tool <name> --args '<json>'`. Run it with the mcp-for-blender tool environment's Python; the path is in the script's header. It exits 0 on success.
- **Telemetry.** Telemetry is on by default and may collect prompts, code and screenshots [45]. It is now off for both agents, which closes the Claude Code gap recorded on 2026-09-17:
  - The Claude Code user-scope registration sets `DISABLE_TELEMETRY=true`, `BLENDER_PORT=9876` and `BLENDER_HOST=127.0.0.1`.
  - `.codex/config.toml` sets `DISABLE_TELEMETRY=true`, `BLENDER_MCP_DISABLE_TELEMETRY=1` and `BLENDER_PORT=9877`.
  - `mcp_autostart.py` also sets the addon's telemetry consent to off.
  - The upstream README documents only `DISABLE_TELEMETRY=true`, plus a consent checkbox under Edit > Preferences > Add-ons > MCP for Blender. The 1.8.0 server's telemetry.py also honoured `BLENDER_MCP_DISABLE_TELEMETRY` and `MCP_DISABLE_TELEMETRY`; the installed 2.0.0 server's telemetry.py still honours both.

Limits: the server refuses `blender -b`, and it runs unsandboxed Python over unauthenticated localhost sockets, now on ports 9876 and 9877 [45]. Blender's own MCP extension, version 1.0.3 for 5.1 and later, uses port 9876 with an incompatible protocol, so never enable both [46] [unverified].

### 5.2 Unreal MCP

Epic's plugin ships in 5.8 as Experimental. Enable "Unreal MCP" and "All Toolsets". It speaks HTTP plus server-sent events only, at `http://127.0.0.1:8000/mcp`, with no authentication. Calls are serial and toolsets drift between versions [47]. The live connection exposes 52 toolsets with 830 tools. Useful: `StaticMeshTools.import_file` with an absolute path, import_materials=false and import_textures=false; `generate_lods([0.5, 0.25])`; `set_lod_thresholds`; `generate_convex_collisions(hull_count=4, max_hull_verts=16)`; `set_nanite_enabled`; `get_triangle_count`; `SkeletalMeshTools.import_file`, with skeleton, import_animations and create_physics_asset; `TextureTools.import_file`; and AutomationTest RunTests [47].

### 5.3 AI generation

The table shows which tier of each generator is resale-safe.

| Tool | Resale-safe tier | Caveat |
|---|---|---|
| Hyper3D Rodin (blender-mcp) | Creator $30/mo or Business $120/mo ("Unlimited export and any use"); free tier exports legacy models only | Pricing page, not ToS, limits the free tier [48] [disputed]; the addon's built-in trial key ("vibecoding") is free-tier, not resale-safe [45][48] |
| Hunyuan3D 2.1 open weights | Commercial OK; excludes EU/UK/South Korea; Tencent license above 1M MAU | 3.0 is API-only with no ownership terms found [49] [unconfirmed]; blender-mcp's "Official API" routes International accounts (this one) to the older `hunyuan` 2023-09-01 service in ap-singapore, not the 3.0 AI3D API [49] |
| Meshy | Pro $20/mo+: private ownership, resale allowed | Free tier is CC BY 4.0 with attribution [50] |
| Tripo | Pro $20/mo+ | Free tier "Public Models, Non-Commercial Use"; Tripo keeps rights to free output [51] |

In the table, ToS is terms of service and MAU is monthly active users. TRELLIS.2 is MIT-licensed but needs 24 GB of VRAM and is Linux-only tested [52] [unverified]. All yield dense, auto-UV'd meshes that need retopology and a re-bake. Under our reading, all trigger CreatedWithAI [11][45]. Unity requires an "AI description" field, and CGTrader's policy is silent on AI [53] [unverified].

### 5.4 Blender 5.x features that matter

Blender 5.0: files from 5.0 need Blender 4.5+; the C++ FBX importer `bpy.ops.wm.fbx_import` became the default; UV selection moved to shared `.uv_select_*` attributes, which killed TexTools; actions became slot-based [55][56]. Blender 5.1: Python 3.13; "corrective flip normals" on by default in Apply Transform; an OpenGL/DirectX toggle on the Normal Map node; FBX shape-key normals [37][55]. Blender 5.2 LTS, supported to July 2028: Geometry Nodes modifier inputs are RNA properties, so `mod["Socket_2"]` raises a TypeError; `bpy.data.file_path_foreach`; `gpu.init()` for background mode; Select by Winding [55][56].

## 6. Market and presentation

This section sizes the market, sets the product order and prices, and ends with the listing checklist.

Characters & Creatures, at about 78K listings, dwarfs Environments at about 23K and Weapons at about 18K [58]. Epic's 2025 top demand was environments, characters, tools and procedural systems [12]. Price bands: stylized prop packs $9.99-$19.99, weapon packs $9.99-$59.99, stylized characters $12.99-$49.99, modular kits $49.99-$129.99, with Professional at 1x to about 3.3x Personal [58]. Sellers report spam and weak search [60][61] [unverified]. Tag one rendering style per product. Product 1 is Realistic plus PBR, because Fab's floor is 1 realistic model as an Asset Pack, with 5 recommended, versus about 25 "simple stylized" [15].

The table sets the product order, scope and prices.

| Product (in order) | Scope | Personal / Professional |
|---|---|---|
| 1. Realistic melee weapon pack (original) | 5 pieces, 20-50k tris, 2K/4K PBR, UCX hulls, LODs, sockets (one FBX each); UE 5.8 project + FBX + .blend (GLB auto-converted); tags Realistic, PBR, Weapon [15][58] | $19.99 / $39.99 |
| 2. Modular wuxia martial artist (de-branded JinMuWon_v2) | ~100k LOD0; re-skinned to the Epic skeleton, the full Manny from the Fab Mannequins pack, with the Third Person Template animations in the overview map, or custom rig + idle/jump/walk/run + attack set (or Control Rig) + Physics Asset; CC0 base cited [3][15][66] | $29.99 / $59.99 |
| 3. Original sigil decal pack | Materials & Textures: 10+ 4K masked decals + reveal master material, overview map; no video unless Niagara ships; original glyphs, licensed fonts; automated Mature flags hit fire VFX and post-process materials (appeals denied): keep glows restrained [3][10][15][65] | $9.99 / $14.99 |

**2026-09-25:** product 2 is on hold as written. JinMuWon_v2 is frozen as a testbed and will not be sold, and de-branding by renaming does not clear the IP (3.6). What replaces product 2 has not been decided. Any character or outfit product must be an original design, and one built on MetaHuman follows 4.7 [69].

Sequence: in week 1, sign the Distribution Agreement, get a Creator Code, complete Trader self-identification with ID and phone, which sellers report taking 5-9 weeks [unconfirmed], file the W-9, and set up Hyperwallet [1][6][8]. Start product 1 after the export gates and the 3.11 tests. No source gives hours per product, so time product 1 first. Submit a week early, because first reviews are reported at 2-5 hours to 2-3 days [14]. Hold the price for 30 days, then file a Sale Case 14-60 days ahead and a Limited-Time Free application, a one-time payment of up to $5,000 [7][57].

Listing checklist [3][5][15][16][19][59]:

- **Content:** original design, generic names, and a logo and font audit.
- **Account:** Standard License at both tiers; Trader status and the W-9 filed.
- **Files:** the UE 5.8 zip on a public link; one format per slot.
- **Media:** a 3840x2160 JPEG thumbnail without text or logos; a grid overview; a GLB preview.
- **Text:** a title of 30 characters or fewer; a description with the contents, the LOD and collision statement, dependencies and the CC0 citation; every tag slot filled.
- **Declarations:** honest AI, Mature and promotional flags; a support email and a documentation URL.

## 7. What changed recently (2025-2026)

These changes since 2024 make older tutorials wrong; check any guide against them.

- **Marketplaces:** Fab replaced the Unreal Engine Marketplace and the Sketchfab Store in October 2024. Megascans went paid in 2025. ArtStation and Sketchfab went to KitBash in August 2026 [63] [unverified].
- **Fab policy:** the Distribution Agreement was revised in June 2025 and February 2026. EU Trader self-identification has been enforced since February 2025. CreatedWithAI has been mandatory since May 2025. New Unreal products must list 5.8 since June 2026 [1][3][8][11][35].
- **Unreal import:** Interchange imports FBX by default with Recompute Normals ON, for assets since 5.5 [disputed: no note states an asset default] and for levels since 5.6. Materials import as instances since 5.7 [unconfirmed]. The legacy importer survives behind a console variable [28][35][39][40].
- **Unreal 5.8:** USD is production-ready for assets only in 5.8. glTF skeletal import has an open 4-influence bug. Nanite skeletal meshes are Experimental. The full Manny/Quinn skeleton moved into a Fab pack [unverified] [30][35][36][41].
- **Blender:** 4.1 removed Auto Smooth. Versions 5.0 to 5.2 changed the FBX importer, UV selection, the action API and the Geometry Nodes modifier API [23][37][55][56].
- **MCP:** blender-mcp became mcp-for-blender in September 2026. Blender ships its own MCP extension. Epic's experimental Unreal MCP plugin ships in 5.8 [45][46][47].
- **MetaHuman 5.6 (2025-06-03):** MetaHuman Creator moved into the Unreal editor. It gained a parametric body and Outfit Assets that resize to fit a body, but cloud auto-rigging and texture synthesis still need a connection. In June 2025 MetaHuman moved to the standard UE EULA, which allows use in other engines and tools, and sales on marketplaces including Fab [71][73][74].
- **MetaHuman 5.7 (2025-11-12):** it added a Python and Blueprint automation API and body-conform upgrades. Conforming now accepts any source pose from A-pose to T-pose, and it round-trips FBX through the UVs, so a Blender sculpt keeps its vertex IDs. It also added volumetric joint estimation and a wider height range; Epic's article on the upgrades is dated 2026-03-19 (date unconfirmed) [71].
- **MetaHuman 5.8 (announced 2026-06-17):**
  - **Conversion.** From Custom Mesh converts a head and body from any topology in a single step.
  - **Experimental runtime and crowd tools.** MetaHuman Instances and Collections can be assembled at runtime in cooked builds; Epic staff had said in March 2026 that runtime assembly was unsupported. Crowds is built on Mass.
  - **Materials and rigs.** Unbaked-material assembly. OpenRigLogic, Epic's rig libraries, released under the MIT license. New fingernail and toenail texture and colour parameters.
  - **Known issues.** Texture seams at the head/body line, the back of the shoulders and the waist, with no workaround. Packaged outfits can lose their materials (4.7) [70][71][72][76].
- **Cloth:** the Chaos Cloth editor, built on Dataflow, is Production-Ready and the default in 5.8, up from Beta in 5.7. The Chaos Outfit Asset plugin is still Beta in 5.8.3. Marvelous Designer 2025.2, shipped in mid-November 2025, imports MetaHuman head and body DNA directly [77][78][82].

## 8. Sources

Fab policy
1. Distribution Agreement (Feb 23, 2026). Verified. https://www.fab.com/distribution-agreement
2. EULA (Oct 1, 2024). Verified. https://www.fab.com/eula
3. Technical Requirements (Mar 17, 2026). Verified. https://www.fab.com/o/technical-requirements
4. Licenses and Pricing. Verified, rungs corrected. https://dev.epicgames.com/documentation/en-us/fab/licenses-and-pricing-in-fab
5. Publishing Assets. Verified. https://dev.epicgames.com/documentation/en-us/fab/publishing-assets-for-sale-or-free-download-in-fab
6. Publisher Get Started. Unverified. https://dev.epicgames.com/documentation/en-us/fab/publisher-get-started-in-fab
7. Sales and Discounts. Verified. https://dev.epicgames.com/documentation/en-us/fab/sales-and-discounts-in-fab
8. Marketplace Disclosure Requirements. Verified; Trolley waits forum 2743730 only. https://legal.epicgames.com/epicgames/marketplace-disclosure-requirements
9. Brand-names FAQ; Coca-Cola case forum 2717861, one seller. Unverified. https://support.fab.com/s/article/Can-I-publish-products-that-include-brand-names-or-logos
10. Epic Content Guidelines; mature auto-flags forum 2440390. Unverified. https://www.epicgames.com/site/en-US/content-guidelines
11. AI announcement (forum 2523501); NoAI article. Unverified. https://support.fab.com/s/article/Introducing-NoAI-meta-tags-and-Created-with-AI-self-declaration
12. Fab 2025 Year in Review. Sale percentages verified; totals unverified. https://www.unrealengine.com/en-US/news/fab-2025-year-in-review
13. Fab support: Hyperwallet, payouts, refunds. Partly verified. https://support.fab.com/s/article/How-can-I-get-assistance-with-Hyperwallet-payout
14. Review-timing threads 2695936, 2711372. Unverified. https://forums.unrealengine.com/t/2695936

Fab technical
15. Asset File Format and Structure Requirements. Verified (minimums, character rules unverified). https://dev.epicgames.com/documentation/en-us/fab/asset-file-format-and-structure-requirements-in-fab
16. Setting up Assets for Fab in Launcher. Verified. https://dev.epicgames.com/documentation/en-us/fab/setting-up-assets-for-fab-in-launcher
17. Using the 3D Editor. Unverified. https://dev.epicgames.com/documentation/en-us/fab/using-the-3d-editor-in-fab
18. Thumbnail uploader post. Unverified. https://forums.unrealengine.com/t/2734774
19. Fab Brand Guidelines. Unverified. https://brand.epicgames.com/document/411
20. Rejection threads 2036677, 2449610, 2452569, 2452444. Partly verified. https://forums.unrealengine.com/t/2452569
21. Live listings. Examples. https://www.fab.com/listings/bd5dfb9c-82cc-45e6-90c0-4875e3c0ac4c
22. 720p reports 2094900, 2693108, no Epic reply. Exist only. https://forums.unrealengine.com/t/2094900

Blender modelling
23. Blender 4.1/4.2 notes; 5.2 shading manual. Verified. https://projects.blender.org/blender/blender-developer-docs/raw/branch/main/docs/release_notes/4.1/modeling.md
24. Blender 5.2 manual, Cycles baking. Verified. https://projects.blender.org/blender/blender-manual/raw/branch/blender-v5.2-release/manual/render/cycles/baking.rst
25. Blender 5.2 io_scene_fbx source. Verified. https://projects.blender.org/blender/blender/raw/branch/blender-v5.2-release/scripts/addons_core/io_scene_fbx/__init__.py
26. Epic FBX Static Mesh Pipeline. Verified. https://dev.epicgames.com/documentation/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine
27. Epic FBX Skeletal Mesh Pipeline, FBX Import Errors. Verified. https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-skeletal-mesh-pipeline-in-unreal-engine
28. Interchange normals thread 2313203; Interchange Import Reference. Disputed, corrected. https://dev.epicgames.com/documentation/unreal-engine/interchange-import-reference-in-unreal-engine
29. Epic LOD docs; LodGroup post 461303. Disputed, corrected. https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-static-mesh-lods-using-fbx-in-unreal-engine
30. Epic Nanite docs. Disputed, corrected. https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine
31. Epic lightmap UV, UV channel, Lumen docs. Unverified. https://dev.epicgames.com/documentation/unreal-engine/generating-lightmap-uvs-in-unreal-engine
32. Polycount wiki. Unverified; unreachable. http://wiki.polycount.com/wiki/Texture_Baking
33. 80.lv mid-poly workflow; texel-density articles. Unverified. https://80.lv/articles/creating-assets-within-the-mid-poly-workflow-in-ue5
34. Blender 4.3-5.2 modeling/UV notes. Unverified as text. https://projects.blender.org/blender/blender-developer-docs/raw/branch/main/docs/release_notes/5.2/modeling.md

Blender to UE
35. UE 5.5-5.8 release notes. Verified; default wording corrected. https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-5-8-release-notes
36. glTF influence bug. Verified. https://forums.unrealengine.com/t/2745391
37. Blender 5.0-5.2 pipeline_io notes. Verified. https://projects.blender.org/blender/blender-developer-docs/raw/branch/main/docs/release_notes/5.1/pipeline_io.md
38. Blender issue #47043. Verified. https://projects.blender.org/blender/blender-addons/issues/47043
39. Force Front X thread 2169794; Epic KB "Interchange FBX options"; FBX Import Options Reference. Verified. https://dev.epicgames.com/community/learning/knowledge-base/KPql/unreal-engine-interchange-fbx-options
40. FBX materials-as-instances thread. Legacy flags verified; material behaviour unverified. https://forums.unrealengine.com/t/2664714
41. Epic Skeletons, Root Motion, IK Rig Retargeting; Manny thread 2580712. Unverified. https://dev.epicgames.com/documentation/en-us/unreal-engine/ik-rig-animation-retargeting-in-unreal-engine
42. BlenderTools releases; Uefy; Auto-Rig Pro docs. Unverified. https://lucky3d.fr/auto-rig-pro/doc/ge_export_doc.html
43. Socket threads 2303521, 2691279; Send to Unreal doc. Disputed, corrected. https://forums.unrealengine.com/t/2303521
44. Epic Python API, Texture. Unverified. https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Texture?application_version=5.8

Tooling
45. mcp-for-blender PyPI/GitHub (2.0.0). Verified. https://github.com/ahujasid/mcp-for-blender
46. Blender Lab MCP Server. Unverified. https://www.blender.org/lab/mcp-server/
47. Epic "Unreal MCP in Unreal Editor"; tc-imba catalog. Verified, corrected. https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor
48. hyper3d.ai terms and pricing. Disputed, corrected. https://hyper3d.ai/pricing
49. Hunyuan3D licenses; blender-mcp PR #342. Verified. https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/LICENSE
50. Meshy help center and pricing. Verified. https://help.meshy.ai/en/articles/10137554-what-is-the-ownership-of-the-generated-models
51. Tripo pricing and terms. Verified. https://www.tripo3d.ai/pricing
52. microsoft/TRELLIS.2 README. Unverified. https://github.com/microsoft/TRELLIS.2
53. Unity Submission Guidelines; CGTrader content policy. Unverified. https://assetstore.unity.com/publishing/submission-guidelines
54. Add-on vendor pages (Superhive, machin3.io, Exoside, SimpleBake, Bake Wrangler, Steam); TexTools issue #268. Unverified. https://superhivemarket.com/products/zen-uv
55. Blender devtalk 5.0 breakages; blender.org release pages. Unverified. https://www.blender.org/download/releases/5-2/
56. Local headless probes on installed Blender 5.2.0. Executed.

Market
57. Limited-Time Free thread. Verified; $5,000 only in the original post. https://forums.unrealengine.com/t/2092736
58. fab.com category and search pages. Observations. https://www.fab.com/category/3d-model/environments
59. Epic tutorial on Fab discoverability. Unverified. https://dev.epicgames.com/community/learning/tutorials/OyaM/improving-your-products-discoverability-on-fab
60. Reviews in Fab doc; seller threads 2279155, 2092291. Unverified. https://dev.epicgames.com/documentation/fab/reviews-in-fab
61. StraySpark blog. Unverified; conflicts with official sources. https://www.strayspark.studio/blog/fab-marketplace-12-month-retrospective-seller-2026
62. Unity Provider Agreement; CGTrader Payout Rate System (Sep 15, 2026). Unverified. https://help.cgtrader.com/hc/en-us/articles/35293756906257
63. Epic/Sketchfab blogs; KitBash newsroom. Unverified. https://www.epicgames.com/site/news/kitbash-acquires-artstation-and-sketchfab

Local audit
64. Blender 5.2 inventory of Assets/*.blend (2026-09-17): WorkFiles/asset_audit_2026-09-17/inv_*.json, produced by inventory.py in the same folder.
65. Scripts/JinMuWon/v2/*.py, jutsu_gameready.py, kd_*.py, build_summoning3.py, build_ninja.py; memory note on fonts.
66. Exports/JinMuWon_v2 reports, manifest, UnrealDemo scripts, import_report.json; SOURCE_NOTES.
67. ASSET_GUIDELINES.md (rewritten 2026-09-17; house rules now carry the measured values).
68. Measured on this machine 2026-09-17, UE 5.8.2 commandlet imports of pipeline test files. Evidence: WorkFiles/pipeline_test/UnrealTest/Validation/legacy_report.json, UnrealTest_Interchange/Validation/interchange_report.json, UnrealCheck/shipped_report.json and reload_report.json. Enforced by Scripts/pipeline.

Characters, MetaHuman and clothing (added 2026-09-25; web pages accessed 2026-09-25 unless a date is given; "date unconfirmed" means a later check could not open the page to confirm the date)
69. CHARACTER_PIPELINE_REVIEW.md (2026-09-25), the fact-checked review behind the 2026-09-25 decisions; its tags are [V] verified, [I] inferred, [U] unconfirmed. Its raw research, with URLs and dates, is in the session workflow journal (wf_c9a532fb-0c2/journal.jsonl).
70. MetaHuman 5.8 release notes; MetaHuman 5.8 known issues. Verified; pages undated. https://dev.epicgames.com/documentation/metahuman/metahuman-5-8-release-notes-in-unreal-engine ; https://dev.epicgames.com/documentation/metahuman/metahuman-known-issues-5-8-in-unreal-engine
71. MetaHuman version announcements: 5.8 on the Epic forum (2026-06-17), plus metahuman.com news (date unconfirmed); 5.7 on the Epic forum (2025-11-12); the 5.7 body-conforming article (2026-03-19, date unconfirmed); the 5.6 launch (2025-06-03). Verified. https://forums.unrealengine.com/t/metahuman-5-8-released/2729288 ; https://www.metahuman.com/news/metahuman-5-8-is-now-available ; https://forums.unrealengine.com/t/metahuman-5-7-released/2672724 ; https://www.metahuman.com/news/metahuman-5-7-brings-major-improvements-to-body-conforming-with-more-to-come ; https://www.metahuman.com/news/metahuman-leaves-early-access-with-a-feature-packed-new-release
72. Epic MetaHuman docs (5.8, undated): from-custom-mesh, from-template, assembly, LODs, runtime-retargeting, materials-and-textures, material-overrides, export tool, instances, collections, crowds. Verified. https://dev.epicgames.com/documentation/metahuman/metahuman-creator-from-custom-mesh-tool-in-unreal-engine ; https://dev.epicgames.com/documentation/metahuman/assembly ; https://dev.epicgames.com/documentation/metahuman/runtime-retargeting ; https://dev.epicgames.com/documentation/metahuman/metahuman-instances-in-unreal-engine ; https://dev.epicgames.com/documentation/metahuman/metahuman-creator-material-overrides-in-unreal-engine ; https://dev.epicgames.com/documentation/metahuman/controlling-metahuman-levels-of-detail-lods-in-unreal-engine ; GASP + MetaHuman (5.8): https://dev.epicgames.com/documentation/unreal-engine/adding-a-metahuman-to-the-game-animation-sample-project-in-unreal-engine
73. MetaHuman on Fab: Selling MetaHumans on Fab; Asset Format and Structure Requirements for MetaHumans on Fab; Fab support article (2025-10-17, date unconfirmed). Verified; preset resale not addressed. https://dev.epicgames.com/documentation/metahuman/selling-metahumans-on-fab ; https://dev.epicgames.com/documentation/metahuman/asset-format-and-structure-requirements-for-metahumans-on-fab ; https://support.fab.com/s/article/Can-I-sell-characters-created-with-MetaHuman-Creator-on-Fab
74. MetaHuman license FAQ; Unreal Engine EULA; CG Channel on the license change (June 2025). Verified; not legal advice. https://www.metahuman.com/license ; https://www.unrealengine.com/eula/unreal ; https://www.cgchannel.com/2025/06/you-can-now-sell-metahumans-or-use-them-in-unity-or-godot/
75. Epic, Working with Modular Characters (5.8); Using Mutable and MetaHumans (5.7). Verified. https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-modular-characters-in-unreal-engine ; https://dev.epicgames.com/documentation/en-us/unreal-engine/using-mutable-and-metahumans-in-unreal-engine ; Lyra animation (5.7): https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-in-lyra-sample-game-in-unreal-engine ; Asset Manager: https://dev.epicgames.com/documentation/unreal-engine/asset-management-in-unreal-engine ; Lyra character parts (community notes, undated): https://x157.github.io/UE5/LyraStarterGame/CharacterParts/
76. Epic forum: staff on runtime assembly, thread 2715460 (2026-03-11 to 03-16); retarget deformation report, thread 2720169 (2026-05-05/06; a user report with no Epic reply). Verified as posts. https://forums.unrealengine.com/t/metahuman-collections-and-character-instances/2715460 ; https://forums.unrealengine.com/t/animation-retargeting-broken-on-new-skm-mhc-metahuman-skeletal-mesh-ue-5-7/2720169 ; login fixes, thread 2542895 (Jun-Jul 2025): https://forums.unrealengine.com/t/error-not-logged-in-5-6/2542895
77. Cloth threads: Chaos Cloth 5.8, thread 2729420 (2026-06-17); outfit resizing addendum, thread 2647376 (2025-08-19, Epic reply 2025-09-12); wardrobe cloth loss, thread 2736828 (2026-07-19, last reply 2026-09-15). Verified. https://forums.unrealengine.com/t/tutorial-chaos-cloth-updates-5-8/2729420 ; https://forums.unrealengine.com/t/tutorial-chaos-cloth-outfit-asset-resizing-addendum/2647376 ; https://forums.unrealengine.com/t/metahuman-parametric-wardrobe-asset-missing-cloth-simulation-5-8/2736828
78. Marvelous Designer: MetaHuman DNA Importer (2025-10-30, date unconfirmed; MD 2025.2 shipped mid-November 2025); pricing guide (2026-09-18, vendor-authored); Indie license announcement (2026-01-21); MD 2026.0 and the Enterprise price, CG Channel (2026-04-20); trial page (title only). Verified; LLC eligibility and trial terms unconfirmed. https://support.marvelousdesigner.com/hc/en-us/articles/51752244831897 ; https://www.marvelousdesigner.com/explore/guide/3d-clothing-software-pricing-licensing-models-compared ; https://www.cgchannel.com/2026/04/clo-virtual-fashion-releases-marvelous-designer-2026-0/ ; https://www.marvelousdesigner.com/support/news/view/b9471a7acc77478a863fd114756d5c19 ; https://www.marvelousdesigner.com/product/trial
79. CLO vs Marvelous Designer comparison (2026-09-18, vendor-authored). Verified. https://www.clo3d.com/explore/clo-vs-marvelous-designer-software-compared
80. Blender add-ons: Robust Weight Transfer (GitHub); Simply Cloth (Superhive); the free Character DNA base edition, CG Channel (2026-07-17). Verified. https://github.com/sentfromspacevr/robust-weight-transfer ; https://superhivemarket.com/products/simply-cloth ; https://www.cgchannel.com/2026/07/the-character-dna-metahuman-add-on-for-blender-is-now-free/
81. Chaos Cloth cost guide, getperfguard (undated, third-party). Unverified. https://getperfguard.com/tutorials/chaos-physics
82. Local engine check 2026-09-25: UE_5.8/Engine/Build/Build.version (5.8.3), plugin .uplugin files (ChaosOutfitAsset Beta, Mutable Beta, MetaHumanCrowd Experimental), MetaHumanInstance.h. Executed.
83. Local project review 2026-09-25: Exports/JinMuWon_v2 reports and CUSTOMIZATION.md; Exports/CharacterLab README and Validation; WorkFiles/MetaHuman logs; Exports/{BlackCloak, BlackNunchucks, SnowFlower}/README.md.
84. Local MCP setup check 2026-09-25: Scripts/BLENDER_MCP.md, Scripts/launch_blender.ps1, Scripts/mcp_autostart.py, Scripts/mcp_probe.py, Scripts/pipeline/lock.py; the installed addon's bl_info and protocol constant; the Claude Code user-scope registration and .codex/config.toml; the installed mcp-for-blender 2.0.0 package's telemetry.py and METADATA.
