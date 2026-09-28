# Game Asset Guidelines — Blender_Projects

House rules for creating game-ready assets here (Blender 5.2 LTS → Unreal Engine 5.8 → Fab). Short on purpose:
the reasoning, the measurements and the source list live in `FAB_ASSET_STUDY.md`. Where this file and a
tutorial disagree, this file wins — every rule below was measured on this machine. Last updated: 2026-09-17.
**Character update 2026-09-25:** the character rules in sections 6.1, 6.4, 7, 8, 9 (amendment B), 10, 11 and
12 come from `CHARACTER_PIPELINE_REVIEW.md` (reasoning, evidence tags, sources) and have **not** been measured
here yet. **UNVERIFIED** marks a claim the MetaHuman spike (12.9) must confirm; **PLANNED** marks tooling not
built yet; **UNCONFIRMED** marks a point the sources leave open or disagree on (the spike may not settle it);
**PROPOSED** marks a target not yet signed off.
**Garment pipeline 2026-09-26:** 12.10 is implemented and measured here (locked fitting body, garment gates, tests,
the BlackCloak regression and an Unreal import check). The lines it changes in 2, 6.1, 6.3, 6.4 and 7 are dated.

---

## 1. Scale & Units
- Model at real-world scale, Metric, unit scale 1.0 (1 Blender unit = 1 m). Unreal is centimetres (1 UU = 1 cm).
  The exporter's FBX Units Scale does the conversion; never eyeball a ×100 and never pre-scale a mesh.
  Z-up; build modular pieces on whole-metre multiples with the pivot where the next piece meets.
- Apply transforms before export (Ctrl+A → All Transforms): scale (1,1,1), no rotation left in `matrix_basis`.
  This is a gate, not a habit — `qa_check` fails an unapplied transform and the export helper refuses the file.
- Pivot placement: grip point for weapons, floor contact for props, joint face for modular kit pieces.
  Never turn on the exporter's "Apply Transform" to compensate for a bad transform — see section 6.

## 2. Geometry / Topology
- Triangle budgets: hero weapon 20–50k · prop 1–5k · background piece 0.5–2k · dressed character **LOD0 80–120k**
  (hair cards and a scalp only). JinMuWon_v2's 635k LOD0 is five times over and cannot ship as-is.
  **Measured 2026-09-26:** the MetaHuman player base alone is 121,892 LOD0 triangles (body 60,816 + face 34,514
  + BrushCut cards 26,562), already over 120k before any garment.
  **DECIDED 2026-09-26 (Cody): hero player character LOD0 budget = 160k** (base + garments + loadout; supersedes
  the 120k above for the MetaHuman player). Reason: 1v1 duel, RTX 4070 SUPER, one MetaHuman measured ~0.4 ms.
  Revisit only if the multi-character / clone performance test struggles (fallbacks: MetaHuman Medium build,
  lighter hair, hiding the body under clothes). Static prop / weapon budgets are unchanged.
- Mid-poly hard surface: Bevel modifier with Harden Normals, then Weighted Normal with Keep Sharp. There is no
  high-poly → low-poly bake for hard surface here; bake support maps off the mid-poly.
- No n-gons, no non-manifold edges (an edge with 3+ faces, or a wire edge), no loose vertices, normals outside.
  Open **boundary** edges are legitimate — decals, hair cards, open-bottom props — and are reported, not failed.
- Bevel hard edges slightly; put hard edges on UV seams. Triangulate before mirroring and before baking.
- LOD triangle counts must strictly descend (LOD0 > LOD1 > LOD2), verified in Blender *and* again in Unreal.
  Character LODs use per-part decimate ratios with seam protection and screen sizes 1.0 / 0.5 / 0.25, never a
  blind whole-mesh Decimate.

## 3. Materials & Textures (PBR)
- Standard set per asset: **Base Color · Normal · ORM packed** (Occlusion R, Roughness G, Metallic B).
- **ORM.R is baked ambient occlusion.** Writing a constant (`np.ones`) there is a bug, not a shortcut.
  Bake with Cycles, Selected-to-Active with a cage, Margin type **Extend** (5.2 defaults to Adjacent Faces).
- **Normal maps are DirectX on disk.** Flip green on write (`pixels[:,:,1] = 1 - pixels[:,:,1]`), then leave
  "Invert Normal Maps" / "Flip Normal Map Green Channel" **OFF** in Unreal. Fab's Launcher expects DirectX.
- Colourspace: colour textures sRGB; normal, ORM and masks **Non-Color**. `image.pixels` are raw *stored* values
  and a PNG has no colourspace tag, so reload data maps with `textures.load_data_image`; wrong tags = pastel wash.
- Metals 0.95–1.0; dielectrics 0.0. No partial metallic on painted colour — it reads as plastic.
- Procedural and object-space projection materials must be **baked to textures on real UVs before export**;
  Unreal cannot read a material that samples by object position, and FBX carries no materials we want anyway.
- Power-of-two only: 2048 for props, 4096 for hero and skin, nothing above 4K in an exchange-format upload.
  Pack textures into the .blend (File → External Data → Pack) so files under `Assets/` stay self-contained.
  In Unreal, build one `M_Master` material with `MI_` instances; never import materials from the FBX.

## 4. UVs
- UV0: non-overlapping islands, consistent texel density, nothing rotated or mirrored after the bake.
  Mirrored shells are offset **+1 in U**, so UV0 is graded against a tile range (default −1..2), not strict 0–1.
- Texel density: **10.24 px/cm** first-person / hero, **5.12 px/cm** third-person.
- Padding: **8 px at 1K, 16 px at 2K**. Pack Islands margin fraction 16/2048 = 0.008, Rotation Cardinal.
  Angle Based unwrap for hard surface; Minimum Stretch (SLIM) for organic shapes.
- **UV1 is the lightmap channel.** Every static mesh ships one: strictly inside 0–1, non-overlapping, and
  Unreal's Lightmap Coordinate Index must be 1, never 0. Fab rejects a static mesh without this.
- Read UV0 **by index**, never "whichever layer is active" — an overlapping UV1 left active used to fail the
  UV0 test and hide the real problem.

## 5. Naming & Organization
```
Assets/       final .blend files (self-contained, textures packed)
Backups/      .blend1 auto-backups + manual safety copies
Exports/      FBX + sidecar JSON + per-product UE projects
References/   source artwork + Fonts/
Renders/      presentation stills + videos
Scripts/      all build/processing .py (assets are regenerable from these)
  pipeline/   the shared export / QA / lock package (section 6)
WorkFiles/    masks, contours, frames, debug composites, locks/, pipeline_test/
```
- Objects named by role; materials prefixed by asset. Unreal prefixes on export:
  `SM_` static mesh, `SK_` skeletal mesh, `T_` texture, `M_` material, `MI_` instance, `A_` animation.
- Textures ship beside the model named `modelname_suffix`, lowercase ASCII, suffixes `basecolor`, `normal`,
  `roughness`, `metallic`, `ao`, `emissive`, `height` — e.g. `sword1_basecolor.png`. In a multi-asset pack
  give each piece a unique prefix or its own folder; matching fails when a .glb/.gltf/.usd sits in the parent.
- Helper names (`UCX_`, `SOCKET_`, LOD group) are matched **literally** by Unreal: a typo is silently dropped (6.2).
- **No franchise, brand or product names** anywhere: object, material, texture, file or folder.
  `qa_check`'s deny list is a case-insensitive substring test over kamish, naruto, gilgamesh, jinmuwon,
  jin mu-won, solo leveling, northern blade, accuracy international and awm, plus "ea" at a word start.
- Fab UE package layout (section 11): `Config/`, `Content/<Pack>/`, `<Pack>.uproject`, type-sorted, ≤ 140 chars.

## 6. Export to Unreal

### 6.1 FBX settings (the shared helper owns these — never hand-export)
| Option | Value |
|---|---|
| Selected Objects; Object Types | ON; Mesh (+ LOD Empty, socket Empty), or Armature + Mesh |
| Scale / Apply Unit / Apply Scalings | 1.0 / ON / **FBX Units Scale** |
| Forward / Up | **−Y / Z** — confirmed correct against the UE mannequin, see 6.5 |
| Use Space Transform / Apply Transform | **ON / OFF** (Apply Transform is broken with armatures) |
| Smoothing / Apply Modifiers / Triangulate | Face / ON (OFF with shape keys) / **ON** |
| Tangent Space | **OFF** — Unreal recomputes MikkTSpace |
| Add Leaf Bones / Only Deform Bones / Node Type | **OFF** / ON / Null |
| Animation | Baked, Key All Bones, Force Start/End, Sampling 1.0, Simplify 0.0, NLA OFF, All Actions OFF |
| Path mode / Embed / Vertex Colors | RELATIVE or COPY / OFF / sRGB |
- **One action per FBX** (Unreal imports one animation per file), one FBX per asset, instances placed in-engine.
- Only Deform Bones ON is for our own prop/weapon skeletons. Anything on the Epic/MetaHuman skeleton keeps its
  `ik_*` bones (section 7); since 2026-09-26 `export_fbx(kind="garment")` does that by writing every bone (12.10).
- **Garments are written in CENTIMETRES** (2026-09-27, pipeline 1.2.0, measured on UE 5.8.3 with the Snow Flower heels).
  A metre garment FBX imports with scale 100 on the `root` bone and every child bone's local translation left in
  metres; the component-space bind pose still matches the body, so every gate passed, but as a Leader Pose / Copy Pose
  follower on the body it is drawn 100x too small. `export_fbx(kind="garment")` now exports temporary x100 copies from
  a unit-scale-0.01 scene (the source objects and scene stay as they were); `ue_check_garment.py` reports
  `follower_safe` (local reference pose incl. scale vs the body). Garments exported before this date (e.g. the
  BlackCloak_MH_v2 garment) should be re-exported and re-checked by their owners.

### 6.2 Collision, sockets, LODs, Nanite — measured on UE 5.8.2, legacy FBX importer
- **Convex hull: `UCX_<render mesh NODE name>_NN`.** The name must repeat the *node* name exactly. Because the
  pipeline renames the mesh to `<base>_LOD0` when it builds a LOD group, the shipped hull is
  `UCX_<base>_LOD0_00`. `UCX_<base>_00` on a node called `<base>_LOD0` imports with **convex count 0** and no
  error. `UBX_` / `USP_` / `UCP_` follow the same rule and must keep unmodified vertices.
- **Sockets are Empties (FBX Nulls), named `SOCKET_<node name>_<socket>`.** A child *mesh* named `SOCKET_` is not
  a socket: it is welded into the render mesh and inflates the triangle count. This reverses the older
  "child mesh, not Empty" guidance, which was wrong for 5.8.2.
- **LOD group: an Empty with custom property `fbx_type = "LodGroup"` parenting `<base>_LOD0.._LODn`.**
  Verified: LOD count equals the number of `_LODn` children, order is correct, triangles strictly descend.
  The reported LOD0/LOD1 swap does **not** reproduce on 5.8.2. Bare `_LOD0` names without the group are ignored.
  Import needs `import_mesh_lods=True`; with it false the LOD meshes collapse into one merged mesh.
- **LODs and FBX sockets are mutually exclusive on 5.8.2.** Any FBX containing a LodGroup keeps its LODs and its
  hull and loses *every* socket, whatever the node type. So: export the LOD group with UCX only, let the helper
  write `<name>.sockets.json`, and recreate the sockets after import with `ue_import_sockets.py`. `export_fbx`
  drops `SOCKET_` nodes from a LodGroup file by default and warns; `--include-sockets` keeps them and warns
  that Unreal discards them anyway.
- A socket that *does* arrive through an FBX (a flat, non-LOD file) inherits the exporter's unit scale as
  `relative_scale` **(100,100,100)** — a hundredfold scale on anything attached. The sidecar writes scale 1 and
  the import script replaces the FBX-imported socket of the same name.
- **Never** use the bare `unreal.StaticMeshSocket()` constructor: it is outered to `/Engine/Transient`, the
  in-process query shows the socket, the save returns True, and the socket is gone on reload. Use
  `unreal.new_object(unreal.StaticMeshSocket, outer=mesh)` then `mesh.add_socket(socket)`.
- Nanite: on for dense opaque meshes, off for translucency and morph-target meshes. Tune Fallback Relative
  Error — the fallback mesh serves complex collision, lightmaps and ray tracing. Fab refuses "simplistic
  unoptimised assets" tagged Nanite, and wants a collision and LOD statement even when the answer is zero.

### 6.3 The export checklist is now a script
`Scripts/pipeline/` is the export path. Do not hand-drive the FBX exporter and do not copy settings by eye.

| Module | Does |
|---|---|
| `helpers.py` | UCX hulls, socket Empties, LOD groups, helper-aware rename, Blender→Unreal socket transform |
| `export_fbx.py` | the one FBX exporter (6.1), helper/LOD/socket rules, the `<name>.sockets.json` sidecar |
| `qa_check.py` | the headless gate (6.4); returns JSON, never prints, never edits the scene |
| `textures.py` | Cycles AO bake, ORM pack, DirectX green flip, Non-Color reload |
| `lock.py` | per-asset locks for two concurrent agents (section 10); stdlib only, runs under system Python |
| `ue_import_sockets.py` | runs inside Unreal: recreates the sidecar sockets after import |
| `test_pipeline.py`, `test_qa_negative.py` | self-tests; run both after touching any of the above |
| `garment_qa.py`, `garment_helpers.py` | garment gates and build helpers on the locked character base (12.10) |
| `test_garment.py` | garment self-test (positive garments, one defect per negative case, FBX round trip) |

Commands, from the project root, one line each:
```
py Scripts/pipeline/lock.py claim SM_Sword --agent claude --blend Assets/SM_Sword.blend --port 9876
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b Assets/SM_Sword.blend --factory-startup --python Scripts/pipeline/qa_check.py -- --objects SM_Sword_LOD0 --budget 50000 --texel 10.24 --require-uv1 --json WorkFiles/qa_SM_Sword.json
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b Assets/SM_Sword.blend --factory-startup --python Scripts/pipeline/export_fbx.py -- --objects SM_Sword_LodGroup --out Exports/Pack/SM_Sword.fbx --kind static
py Scripts/pipeline/lock.py release SM_Sword --agent claude
```
`qa_check` exits 1 and prints JSON when anything fails. `--kind` is `static | skeletal | animation`;
`--exclude A,B` leaves helper children out. Self-tests, then the Unreal re-check in two processes:
```
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python Scripts/pipeline/test_pipeline.py
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python Scripts/pipeline/test_qa_negative.py
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python Scripts/pipeline/test_garment.py
"C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" <project>.uproject -run=pythonscript -script="WorkFiles/pipeline_test/UnrealCheck/verify_shipped.py" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput
"C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" <project>.uproject -run=pythonscript -script="WorkFiles/pipeline_test/UnrealCheck/verify_reload.py" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput
```
Package files — `Scripts/pipeline/`: `__init__.py`, `helpers.py`, `export_fbx.py`, `qa_check.py`, `textures.py`,
`lock.py`, `ue_import_sockets.py`, `test_pipeline.py`, `test_qa_negative.py`. Evidence — `WorkFiles/pipeline_test/`:
`test_report.json`, `test_qa_negative.json`, `SM_TestCrate.blend`, the sidecars `SM_TestCrate.sockets.json`,
`SM_TestCrate_Single.sockets.json`, `SM_TestCrate_LodSocket.sockets.json`, and `UnrealCheck/` with
`verify_shipped.py`, `verify_reload.py`, `shipped_report.json`, `reload_report.json`.

### 6.4 What `qa_check` enforces
Transforms applied and unit scale 1.0 · triangle budget and descending LODs · no n-gons, non-manifold edges or
loose verts · UV0 present, texel density in tolerance, no overlap, inside the tile range · UV1 inside 0–1 and
non-overlapping when required · textures power-of-two, present, correct colourspace, DirectX normals ·
prefixes correct, every `SM_` carrying a matching `UCX_<node>_NN`, every `SOCKET_` child an Empty, no deny-list
strings · skeletal: one root at the origin, ≤ 4 influences, no unweighted verts, weight error < 1e-6, no "."
in bone names. `qa_check` is read-only and restores hide/select state, so it is safe to run at any time.
Garments on the locked character base get `garment_qa.py` on top (2026-09-26, 12.10). Two `qa_check` items were
extended for it: the influence limit is a parameter (garments pass their type's limit), and an armature object named
`root` whose bones start at `pelvis` counts as its own root bone (Blender imports Unreal's root that way).

### 6.5 Import side (Unreal 5.8)
- **Skeletal garments (2026-09-26, Cody):** import with Unreal's DEFAULT importer (Interchange) — it is what DemoGame_1 and
  CharacterLab actually use and what every garment check (12.10) was verified with. The legacy-importer rules below
  still apply to static meshes.
- Ship on the **legacy FBX importer** (`Interchange.FeatureFlags.Import.FBX=0` in `DefaultEngine.ini`): Import
  Normals + MikkTSpace, Convert Scene ON, Force Front XAxis OFF, Convert Scene Unit ON, Import Uniform Scale
  1.0, Do Not Create Material, Auto Generate Collision OFF with UCX present, One Convex Hull per UCX, Import
  Mesh LODs ON, Generate Lightmap UVs ON unless Nanite.
- **Interchange works, but is not the default yet.** A duplicated `DefaultFBXOBJAssetsPipeline` with
  **Recompute Normals OFF** reproduced the legacy character import exactly: 152 bones, identical bounds, max
  per-bone reference-pose delta 0.0001 cm. Recompute Normals ON silently rewrites every normal by about 7° and
  welds hard edges. Two gotchas: the asset registry returns nothing for `/Interchange` until
  `scan_paths_synchronous(["/Interchange/Pipelines"], force_rescan=True)` runs, and Interchange ignores
  `AssetImportTask.destination_name` and emits far more assets than asked for. Switch only once the exporter
  enforces the 6.2 naming rules.
- **Facing axis is verified, not assumed.** JinMuWon and `SKM_Manny_Simple` both face **+Y** in mesh space with
  sideways −X, so Forward −Y / Up Z is correct, no export-time rotation is needed, and the Character Blueprint's
  −90° yaw applies unchanged. The bone-vector facing check stays a permanent QA gate: the commandlet never
  looks at it otherwise.
- **Read hull presence from `body_setup.agg_geom` directly.** `StaticMeshEditorSubsystem` returns `None` under
  `-run=pythonscript` and `EditorStaticMeshLibrary`'s collision counters return −1, both failing silently.
- **Hull geometry IS verifiable, through a re-export round trip** (resolved 2026-09-17 on the shuriken pack).
  `KConvexElem` still exposes no data fields, but exporting the imported StaticMesh back to FBX from the
  commandlet writes the stored hull out. Gate on it: the stored hull must be identical to the shipped `UCX_`
  (same vertex and face counts, e.g. 16/28 and 24/44 on the shuriken), LOD0 must sit 0.0 cm outside it,
  positions must round-trip within 1e-6 cm, and the generated UV1 must be inside 0–1 with zero overlap.
  Reference implementation: `WorkFiles/shuriken/UnrealCheck6/` (passes 1–3).
- **Only promote a report to "engine-verified" when the bytes match.** The shuriken build writes its engine
  check as pending with the SHA-256 of the FBX and sidecar; `attach_engine_check.py` promotes it only when
  the bytes Unreal imported equal the bytes on disk. A verification of a previous export proves nothing.
- **Assert saved state in a second, fresh process.** An assertion made in the process that did the write proves
  nothing about what reached disk — that is exactly how the transient-socket trap hides. Likewise, a single-run
  helper-import result is not trustworthy: re-run any helper claim with a matched control before it lands here.

## 7. Skeletal Meshes
- One `root` bone at the origin carrying the motion; no "." in bone names; bone influence limit 4; zero
  unweighted vertices; weight sums within 1e-6. Create Physics Asset ON, then hand-tune — Fab requires one.
- Fab gives two routes: the Epic/MetaHuman skeleton in A-pose, bone names and orientations unchanged and IK
  bones unweighted and in place; or a custom skeleton with idle, jump, walk, run plus genre moves or a Control
  Rig. **Retargeting animations onto a custom rig satisfies neither route — only re-skinning does.** 5.6+
  templates ship only `SKM_Manny_Simple`; the full Manny/Quinn comes from Fab's Mannequins pack.
- Export armature + mesh, Only Deform Bones ON, Add Leaf Bones OFF, one action per animation FBX. With shape
  keys, Apply Modifiers must be OFF; the export helper does that automatically and warns.
- **Amended 2026-09-25: Only Deform Bones ON is for our own prop/weapon skeletons.** Anything on the
  Epic/MetaHuman skeleton keeps its `ik_*` bones, unweighted and in place (Fab route one,
  `FAB_ASSET_STUDY.md` 3.6); deform-only must not strip them. The helper's skeletal default is still
  deform-only, so check the exported bone list by hand until the PLANNED gate (12.10) exists.
  Whether the MetaHuman body skeleton has `ik_*` bones at all is UNVERIFIED (community sources: Manny's names
  and hierarchy plus extra joints, probably no `ik_*`) — record the bone list in spike 2b. If they are missing,
  anything sold outside the `.mhpkg` route (section 11) needs them added.
  **Measured 2026-09-26:** metahuman_base_skel has 342 bones and **no** `ik_*` bones. Garments export every bone
  (`kind="garment"`, deform-only off), so the policy holds by construction; Fab route one would need them added.

**Character skeleton rules (2026-09-25)**
- **The locked base** is `/Game/Characters/MetaHumans/MH_PlayerBase` (project `Exports/CharacterLab`, 12.1).
  Locked: the MetaHuman body skeleton, body topology and UVs, the neck boundary and the material parameter
  names (12.2). **The face is not locked** — heads are swappable (12.3). Never rename a material parameter or
  move the neck boundary.
- **Every garment and attachment uses the base's skeleton asset** — select it at import. BlackCloak is the
  counter-example: rigidly weighted to the JinMuWon skeleton, it still got its own skeleton asset in Unreal.
  BlackNunchucks also has its own skeleton and needs a plan before it can be equipped.
- Whether character garments keep the 4-influence limit or follow the base's influence count is an open
  question (UNVERIFIED): record the base's influence counts in spike 2b (12.9) and decide then. Until a dated
  amendment says otherwise, the 4-influence rule above applies to every skeletal mesh and `qa_check` tests ≤ 4.
  **Amended 2026-09-26 for garments on the MetaHuman base:** the body itself uses up to 8 influences (8,374 of
  32,334 LOD0 vertices), and a fitted garment limited to 4 would deform differently from the skin under it. So
  `fitted` ≤ 8, `cloak` ≤ 2 (the spine height blend), `rigid_head` / `rigid_socket` exactly 1. Every other skeletal
  mesh keeps ≤ 4. That Unreal keeps all 8 on an FBX garment import is not verified in the engine yet.
- **Garments are fitted to `MH_PlayerDefault` (2026-09-26)**, the rigged and assembled player (same body as
  MH_PlayerBase): `References/Characters/MH_PlayerDefault/`. In Blender its armature object must stay named `root`
  (Unreal's root bone; any other name adds a bone above it) and its pose must equal its rest pose.
- No "." in bone names still applies (JinMuWon_v2 breaks it with 114 such names).
- Weapon sockets live on `hand_r` / `hand_l` (Manny naming; the MetaHuman skeleton reportedly matches, so
  confirm in the spike 2b bone list; JinMuWon_v2 only has `wrist.R`). Confirmed 2026-09-25: both are bones of
  metahuman_base_skel.
  The helper does not export skeleton sockets yet (PLANNED, 12.10).

## 8. Animation
- Keep rig-driven and material-driven animation simple and bakeable. Material value animations (the seal's
  reveal `Front` value, for instance) do **not** travel through FBX — re-create them in Unreal as Scalar
  Parameters driven by a timeline or curve.
- Blender 5.2 API: actions are layered — fcurves live at `action.layers[].strips[].channelbags[].fcurves`
  (`action.fcurves` is gone). Geometry Nodes modifier inputs are RNA properties, so `mod["Socket_2"]` raises.
- **Manny and Game Animation Sample (GASP) animation plays on MetaHumans through Epic's retargeters**, not a
  shared skeleton asset. Retargeting = transferring animation between skeletons through an IK Rig mapping.
  Runtime: the `ABP_GenericRetarget` AnimBP or a Retarget Pose From Mesh node with `RTG_UEFN_to_MetaHuman_nrw`,
  Manny hidden as the driver. Offline: an IK Retargeter. Fab animation packs made for Manny need the same.
- **Risk to test (spike 2b):** a May 5, 2026 forum post reports deformed retargets on a 5.7-made MetaHuman
  body; the next day the poster said a manual two-stage retarget "minimized" it. No Epic reply. Whether it
  affects our 5.8-made base is UNVERIFIED.
- The MetaHuman face is a separate mesh driven by RigLogic (Epic's face-rig solver): test animation on every
  head.
- **Per-weapon animation layers, Lyra's pattern:** each weapon links an animation layer AnimBP that implements
  `ALI_ItemAnimLayers` (Lyra's base is `ABP_ItemAnimLayersBase`) and overrides locomotion, aiming and
  skeletal-control poses for that weapon (Lyra animation doc, 5.7).

## 9. House Pipeline Rules (learned the hard way)
- **Reference-first:** get reference images on disk and verify against them with side-by-side composites and
  error heatmaps. Measure from pixels, never eyeball proportions.
- **Headless is the reliable path:** `blender.exe -b file.blend --factory-startup --python script.py -- args`.
  The GUI + MCP live link crashes under heavy scenes. Never launch GUI Blender for batch work.
- **Animations:** render PNG frame chunks in separate processes and assemble with ffmpeg
  (`ffmpeg -framerate 24 -i f%04d.png -c:v libx264 -pix_fmt yuv420p out.mp4`).
- **Never leave a stale Blender window open on a file you are editing headlessly** — a save from that window
  silently clobbers the disk file. Close it first, reopen after. This applies to your own windows as much as to
  the other agent's (section 10).
- **Backups:** Blender writes `.blend1` next to every save — first place to look after a bad save. Make a manual
  `_backup.blend` copy before a destructive pass.
- **Scripts are the source of truth:** every asset is regenerable end to end from `Scripts/`.
  **Amended 2026-09-25:** GUI- or cloud-authored **source** assets are allowed — MetaHuman Creator characters
  (rigged on Epic's cloud) and Marvelous Designer `.zprj` / `.zpac` files — on three conditions: the source
  files are versioned and backed up; their recipe is written down beside them (settings, presets, weights,
  hashes); and every step downstream of them is scripted.
- **MCP notes:** blender-mcp refuses Blender's `-b` background flag, so it is GUI-only and never replaces the
  headless path. It runs unsandboxed Python over an unauthenticated localhost socket, and telemetry is **on by
  default** and may collect prompts, code and screenshots — set `DISABLE_TELEMETRY=true` in the MCP
  registration's env block. Blender's own MCP extension shares that port with an incompatible protocol: never
  enable both. **2026-09-25:** the server is now mcp-for-blender 2.0.0 on ports 9876 (Claude Code) and 9877
  (Codex); see section 10 and `FAB_ASSET_STUDY.md` 5.1. Blender's own extension uses 9876.

## 10. Working alongside another agent
Two AI agents — Claude Code and Codex — may run Blender at the same time, on **different** assets.
- Each agent gets its **own GUI Blender instance on its own MCP port**: Claude Code **9876**, Codex **9877**.
  The port is the Scene property `blendermcp_port`. Launch with
  `Scripts/launch_blender.ps1 -Blend <file> -Port <port> -Agent <name>` — it refuses a port that already has a
  listener, and claims the asset lock before Blender starts.
- **Claim before opening any .blend**, GUI or headless:
  `py Scripts/pipeline/lock.py claim <Asset> --agent <name> --blend <path> --port <port>`, then
  `py Scripts/pipeline/lock.py release <Asset> --agent <name>` when done. Locks are JSON files in
  `WorkFiles/locks/`; `status` and `list` report the holder, the age and a stale flag.
- **Never open, save, or run a headless script against an asset locked by the other agent.** Exit code 2 from
  `claim` means the other agent holds it — stop there; do not work around it.
- A stale lock is released with `--force` **only after confirming no Blender window has that file open.** The
  recorded `pid` is a hint, not proof; the default staleness TTL is 8 hours.
- Asset names are case-folded, so `SM_Crate` and `sm_crate` are one lock. The stale-window clobber rule in
  section 9 still applies to your own windows.
- **Ownership (2026-09-25): the character track is Claude's** — every `MH_*` asset, `Exports/CharacterLab`
  and `JinMuWon_v2`. Codex may still work on other assets under their own locks.
- **One Unreal editor per project at a time.** Never run another Unreal job alongside the MetaHuman spike:
  RAM is tight.
- **Unreal and MetaHuman scripts claim the lock before editing**, with the `.uasset` as the path:
  `py Scripts/pipeline/lock.py claim MH_PlayerBase --agent claude --blend Exports/CharacterLab/Unreal/Content/Characters/MetaHumans/MH_PlayerBase.uasset`.
  Not every `Scripts/MetaHuman/` script checks the lock. The `pb_*.py` scripts that open assets call
  `assert_owner` and stop without it (`pb_conform.py` checks both `MH_PlayerBase` and `MH_MaleBase`). The older
  male-track scripts `assemble_male.py`, `create_male_preview.py`, `extract_preset_thumbnails.py`,
  `preflight.py` and `setup_comparison.py` do not. Claim by hand before running any of them; adding the check
  everywhere is PLANNED.

## 11. Marketplace (Fab)
- Nothing ships with a franchise name, likeness, product designation or projected third-party art; audit logos
  and fonts too. Nothing currently on disk clears this bar without a rename and a re-texture.
- Per static mesh Fab wants collision, an LOD statement (even "zero"), a non-overlapping lightmap UV and
  Lightmap Coordinate Index ≠ 0. Per skeletal mesh: the Epic/MetaHuman skeleton or a custom rig with
  animations or a Control Rig, plus a Physics Asset.
- UE package: one project folder in a single .zip (never a zip inside a zip), only `Config/`, `Content/<Pack>/`
  and `<Pack>.uproject`, no `/Engine/` or Starter Content references, unused plugins disabled, redirectors
  fixed. Build lighting and save the zip from the **earliest** engine version you tick. Ship an overview map
  containing every asset, with no errors or consequential warnings on load or in PIE.
- Self-test: migrate `Content/<Pack>` alone into a blank 5.8 project, then delete `Config/` and reopen the
  overview map — a Config-dependent map has drawn a rejection before.
- Declare AI use, third-party software (MPFB's output is CC0 but its code is GPL — keep that code out of
  `Exports/`), Mature and promotional flags honestly. Fill every technical field and tag slot; English only.
  Keep every live product on one of the three latest engine versions, updated shortly after each release.
- **MetaHuman products** (characters, clothing and grooms made in UE 5.6+): verify and package with MetaHuman
  Manager as `.mhpkg`; the NoAI tag is applied automatically; CC BY is not allowed. Build clothing on the
  MetaHuman base skeleton without reparenting any bone, and include a matching body for each outfit size.
  Known 5.8 issue: packaged outfits can lose their materials — test the package before listing. Whether a
  lightly edited preset (e.g. Kelvin) can be sold is UNCONFIRMED: sell original characters only.
- **Character IP rule (2026-09-25, not legal advice).** JinMuWon_v2 is a third-party likeness: it is frozen as
  the customization testbed and is never shipped in the game or sold on Fab as-is. Renaming or lightly changing
  a face does **not** clear IP; the test is whether a fan would recognise the character. Default hair and
  outfit must not reproduce that character's signature look. The player base uses an original face (12.1).
  Note AI-generated references for Fab's AI disclosure if a design derived from them is sold.

## 12. Characters, customization and cosmetics
Decisions dated 2026-09-25; reasoning, evidence tags and sources are in `CHARACTER_PIPELINE_REVIEW.md`.
Nothing in this section has been measured here yet (UNVERIFIED and PLANNED: see the top of this file).

### 12.1 Decisions
- **Player base = MetaHuman, built as a mix:** our CC0 MPFB-based body, converted with UE 5.8 "From Custom
  Mesh" (fits a mesh of any topology to MetaHuman topology inside Unreal) into
  `/Game/Characters/MetaHumans/MH_PlayerBase` (project `Exports/CharacterLab`), with an **original default face
  picked by Claude** — no face-selection step. Epic warns stylized features "solve with varying quality" and
  extreme proportions can pinch. Masks drawn in MPFB's UV layout will not carry over (inferred).
- **JinMuWon_v2 is frozen** as the customization testbed and never ships or is sold as-is (section 11).
  **Claude owns the character track** (section 10).
- **Face swap = a library of pre-built, interchangeable heads**, not sliders (12.3).
- **Body shape is fixed: one body per sex** by default — no outfit resizing, no body morphs on every garment.
- **Face rig: Joints Only** by default (already scripted, lighter). Full Rig only for expressive cutscenes.
- **Default (review recommendation, not a user decision): assemble as UE Optimized** (typically under 100 MB),
  not Cine (about 1–2 GB), with card hair and LODSync.
  Optimized High vs Medium is settled by the performance test (12.7).
- **Single-player vs multiplayer is undecided:** cosmetics are saved IDs + colours so replication can be
  added later (12.5). **Marvelous Designer is not purchased.**

### 12.2 Customization contract
- Parameter names are fixed — never rename one: `SkinToneColor`, `SkinToneAmount`, `NailColor`,
  `NailPolishAmount`, `NailRoughness`, plus `IrisColor` (new).
- One dynamic material instance (a per-character runtime copy of a material) per character per slot. Push the
  same values to every face LOD material and to the body.
- **Why our own material setup:** MetaHuman bakes skin tone and nail tint into textures at assembly. The baked
  materials keep only global hue/value controls and no nail colour, so a runtime change there would be a
  global grade that also shifts lips and nails. Ways round it: an override material with a nail mask
  (overrides derived from Epic's materials still get baked) or 5.8's unbaked assembly (cost unmeasured).
  5.8 Creator added fingernail/toenail colour parameters; whether they survive to runtime is UNVERIFIED —
  verify in spike 2c.
- Redraw the masks in MetaHuman UV space. Fix JinMuWon's weak spots: clamp the output, hand-author the deep
  tones (a plain multiply skews red-orange), and make nail masks larger than its 12–17 px fingernails at 2048.
- Gate: the fresh-process capture harness passes on 5.8.3.

### 12.3 Head library and seams
- Heads are pre-built for the locked body (one per sex) and its neck boundary; start with 2. The MetaHuman face
  editor cannot ship inside a game. Each head needs its own rig, so another Epic sign-in.
- Swap routes, tested in spike 2d: (a) pre-assembled heads — swap the face mesh, its DNA (the head's
  rig-definition file) and its animation class on one body; (b) 5.8 MetaHuman Instances/Collections —
  Experimental, documented for runtime assembly in cooked builds; head swap through them is UNVERIFIED.
  Mutable (Epic's runtime mesh-customization plugin) needs "RigLogic Extensions for Mutable" for animated faces;
  it is missing from the local 5.8.3 install and working in 5.8 is UNVERIFIED.
- **Seams are the weak spot.** 5.8 known issue, no workaround: texture seams at the head/body line, the back of
  the shoulders and the waist. Check every head at every LOD on those three lines.

### 12.4 Hiding the body under clothes
- Use one of: a trimmed body per outfit (as `Human_Clothed` does); MetaHuman hidden-face maps (the outfit
  pipeline emits head/body maps that remove geometry under clothes); opacity masks; Mutable clipping.
- Keep trimmed edges away from the three known seam lines (12.3).

### 12.5 Cosmetic assembly and saved data
- **Start with Leader Pose** (one leader mesh drives the followers' animation): cheap on the game thread,
  heavy on the render thread, keeps morphs; followers cannot simulate physics independently (Epic's 5.8
  table: "Physics: No"). Mesh Merge renders cheapest but loses morphs. Mutable merges parts: the 5.8 notes
  claim "production readiness", the local 5.8.3 plugin says Beta — UNCONFIRMED for production. 5.8 MetaHuman
  Instances/Collections are Experimental; heads, skin tone, nails and multiplayer are undocumented there.
- Outfits are fitted at build time: the local 5.8.3 runtime code only picks pre-fitted outfits, and runtime
  resizing is unconfirmed for 5.8. The fixed body shape (12.1) makes that moot.
- **Cosmetics (outfits, skins, weapons) are Primary Data Assets with soft references**, loaded asynchronously
  by the Asset Manager. **Save only IDs and colours.**
- **If multiplayer is chosen:** the server picks the parts and replicates only IDs and colours via RepNotify
  (a replicated variable that runs a function on clients when it changes); dedicated servers never spawn
  cosmetics, as in Lyra. Test with PIE "Play As Client", including late join and a mid-match change.
  Packaging a dedicated server from a Launcher engine build is UNVERIFIED for 5.8.

### 12.6 Clothing
- **Three physics tiers, cheapest first:** skin weights only → bone chains → Chaos Cloth for hero pieces only.
  Decide each piece's tier and recolour regions at concept, together with its IP check. The Chaos Cloth
  editor is Production-Ready in 5.8; the Outfit Asset is Beta. **Test cloth on a Leader Pose follower**:
  Epic's 5.8 table marks followers "Physics: No" and says nothing about cloth. Call
  `ForceClothNextUpdateTeleportAndReset` on respawn. Reported July 2026, no Epic response as of 2026-09-15:
  converting an outfit to a parametric wardrobe asset loses its cloth sim.
- **Tools:** Marvelous Designer (MD) for draped pieces — hakama, haori, sleeves, cloak. Blender for armour,
  belts, bracers, tabi and tight suits. MD 2025.2 imports MetaHuman DNA directly (else Geometry Export
  → FBX), and MD's USD goes straight into a UE Cloth Asset. Before shipping anything made in MD, confirm the
  licence tier and the trial's commercial-use and export terms (both unknown). MD files follow section 9.
- **Weights (fixed-size garments):** Data Transfer from the body, then the free Robust Weight Transfer add-on,
  then hand fixes. Import onto the base skeleton (section 7).
- Recolour through one shared clothing master material modelled on BlackNunchucks (mask regions, texture
  reskins, a JSON manifest).
- **Pilots before the template.** A: a fitted inner suit built in Blender, skin-weighted, with recolour and
  body hiding. B: the cloak rebuilt MD → USD → Cloth/Outfit Asset → Chaos Cloth. C: one weapon at 20–50k
  with a socket and an animation layer. Freeze the template (naming, export settings, LOD rules, QA list)
  only after all three pass 12.7 and 12.8.

### 12.7 Budgets and performance
- Dressed character LOD0: **160k for the MetaHuman player (decided 2026-09-26, section 2)**; weapon 20–50k unchanged.
- **PROPOSED target, not signed off:** 8 characters on screen, 60 FPS at 1440p, High scalability, with cloth,
  on this machine's RTX 4070 SUPER. Compare Optimized High against Medium in that test.

### 12.8 Character QA — in Unreal, never from Blender renders
Seiza, crouch-walk, ledge hang, wall-run, roll, flips, ragdoll, katana draw, scabbard vs cloak, hood vs every
head, LOD transitions, 8+ characters on screen. Plus the head × outfit matrix, clean seams at every LOD, and
the 11-pose deformation audit against thresholds set in advance.

### 12.9 Acceptance tests: the MetaHuman spike
Throwaway map, one agent, one editor. **Every stage waits for the user's explicit go-ahead; none auto-starts.**
- **2a Sign-in, rig, assemble.** The user types their own Epic credentials; no agent ever enters them. Normal
  (non-admin) editor, Chrome or Edge as default browser, finish within about 10 minutes — the editor looks
  frozen while it waits. UNVERIFIED: whether assembly needs the downloaded source textures, and whether one
  login is reused by later headless runs.
- **2b Locomotion.** Manny/GASP locomotion plays through Epic's retargeter with a katana on `hand_r`; the bone
  list (including `ik_*`) and the influence counts are recorded.
- **2c Runtime colour.** Skin and nail colour change at runtime and match across every face LOD at the neck,
  the back of the shoulders and the waist.
- **2d Head swap.** Two heads swap in a **packaged** build; try pre-assembled heads and 5.8 Instances.
- **2e Performance.** 8 characters hit the 12.7 target, and cloth works on a Leader Pose follower.

A failed stage goes back to the user. The review's fallback (its section 5, stage 2) is the CC0 MPFB body
re-skinned onto Manny's skeleton — also several days of work.

### 12.10 Garment pipeline — implemented 2026-09-26
Every garment is built on the locked fitting body and leaves Blender through the garment gates. How-to:
`Scripts/garments/README.md`; the body: `References/Characters/README.md`.

- **Locked fitting body** `References/Characters/MH_PlayerDefault/`: the LOD0 body, the face's skin section,
  the BrushCut's own helmet shell as the hair proxy (closed, pushed out 4 mm to hold 99.4 % of the LOD0 cards) and
  the `root` armature, A-pose, metres, facing -Y. `base_lock.json` holds the SHA-256 of the .blend and every
  source, the skeleton record and hash, per-mesh geometry hashes and the LOD0 triangle counts. Its skeleton
  matches Unreal's reference skeleton of the body mesh to 0.0005 mm.
- **Start / build:** `new_garment.py --name X --type cloak|fitted|rigid_head|rigid_socket` appends the locked body
  (unselectable) with `GARMENT`, `GARMENT_SIM` (cloak) and `GARMENT_HELPERS`; `build_garment.py` skins per type,
  joins, gates and exports with `export_fbx(kind="garment")` only if every gate passes. `refit_garment.py` moves
  a garment sculpted on another body (landmark warp + clearance); the BlackCloak uses it.
- **Gates** (`garment_qa.py`; every threshold is a constant there):

| Gate | Threshold |
|---|---|
| skeleton | one armature, object named `root`, identity transform, pose = rest; every bone name, parent and rest transform equal to the lock (0.01 mm / 0.001°), hash reported; full bone set exported |
| fitting body intact | body, head skin and hair proxy hash to the lock |
| intersection, rest | 0 vertices more than 1 mm under the skin (body + head skin); a hat also 0 inside the hair proxy |
| intersection, 4 poses | arms up, deep crouch, long stride, arms forward set on the armature: ≤ 1 % of the checked vertices more than 5 mm under the skin. Cloak: cloth section at rest only, arms ignored; hat: arms and head ignored |
| weights | cloak: spine chain only (pelvis..head), ≤ 2, cloth section rigid on spine_03..05; fitted: bones the body uses, ≤ 8; rigid: one bone (`head` / the socket bone) |
| budgets | garment: cloak 30k, fitted 20k, rigid_head 10k, rigid_socket 5k (decided 2026-09-26); cloth ≤ 6,000 triangles; whole character ≤ 160k (base 121,892 + garment + `--extra-loadout-tris`; decided 2026-09-26) — waivable, and only this one, with a recorded reason |
| sections | ≤ 4 material slots, `M_`/`MI_`; cloak: exactly one `*_Sim` slot and `PinMask` the active colour; no `*_Sim` elsewhere |
| core `qa_check` | as 6.4 with the type's influence limit; UV0 overlap / tile range informational (tiling fabric) unless the work file sets `garment_unique_uvs` |

- **Tests:** `test_garment.py` — 13 cases (fitted shirt, hat, cloak pass; moved bone, armature not named `root`,
  poke-through at rest, pelvis-rigid shirt that pokes through in the crouch, limb weights on a cloak, hat in the
  hair, garment / cloth / character over budget, tampered fitting body each fail exactly their gates) plus an FBX
  round trip of a fitted and a cloak garment (skeleton 0.003 mm / 0.003°, vertices 1e-7 m, weights exact).
- **Regression (BlackCloak, from a copy of the original sculpt):** refit bit-identical to the 2026-09-26 one-off on
  16 of 17 pieces, 51 of 15,379 long-drape vertices ≤ 0.73 mm off (float noise in the importer's 0.01 matrix flips
  one clearance threshold); build: same 28,378 triangles per section, 15,045 vertices, weights, PinMask and bone
  set; 15,021 vertices within 0.01 mm, 24 cloth vertices up to 4.9 cm off because the 0.037 decimation amplifies
  those 51. Fed the one-off's own fit, the build matches it at every vertex (0.0007 mm). Unreal (CharacterLab
  commandlet, nothing saved): both land on metahuman_base_skel with 342 bones, 15,497 vertices, identical bounds.
- **Still open:** skeleton sockets (weapon sockets on `hand_r` / `hand_l` as Unreal skeleton sockets — the
  `rigid_socket` type gates the bone, nothing creates the socket); skeletal LODs; a high-to-low bake; body hiding;
  the character budget decision; per-type thresholds to re-tune on the first real fitted garment, hat and sheath.
  Blender stores MetaHuman twist bones (0.1 mm long) to ~0.14°, so an exported garment's bind pose differs from the
  body's by up to 0.139° on those bones (the in-game one-off identically; ≤ 0.2 mm on the skin).

## Sources
Every claim above traces back to `FAB_ASSET_STUDY.md`: section 8 there holds the URL list with per-source
verification status, and 3.5 / 3.7 / 3.8 / 3.10 / 3.11 hold the detail and measurements behind sections 6 and 7
here. Don't copy URLs into this file — cite the study.

**Exception, 2026-09-25:** the dated character rules (6.1, 6.4 and 7–12) trace to `CHARACTER_PIPELINE_REVIEW.md`
(sections 2–7 hold the reasoning and the [V]/[I]/[U] tags) and to `FAB_ASSET_STUDY.md` section 8, sources
[69]–[84]. Cite those, not URLs.
