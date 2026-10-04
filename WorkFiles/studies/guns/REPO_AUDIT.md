# Gun building: repo audit (what we have, what is missing, how to lay it out)

**Date:** 2026-10-04. **Role:** repo audit for the gun-building study (`GUN_BUILDING_STUDY.md`, to be written from
the role notes in this folder). **Scope:** what `Scripts/pipeline/` and the Unreal scripts support today, what rigged
weapons would need, which tools can be reused, how the six reference sheets share parts, and the folder / naming /
lock scheme. Nothing was built, no lock was taken, no Blender or Unreal process was run. The rifle-specific study in
`WorkFiles/guns/rifle/` was read only.

Tags: **[M]** measured or read in this repo (file and line given), **[E]** external (source number, list at the end),
**[J]** judgement.

Measurement scripts for section 4: `WorkFiles/studies/guns/repo_audit/sheet_silhouettes.py` and `sheet_rulers.py`
(numpy + Pillow + scipy, system Python).

---

## 0. The audit in one screen

| Question | Answer |
|---|---|
| Is there a skeletal export path? | **Yes, a measured one.** `Scripts/pipeline/skeletal_prop.py` (made for the folding fan `SK_Fan`, 2026-09-26) does skeletal QA, centimetre multi-file export (mesh per LOD + one FBX per action) and a `<name>.skeletal.json` sidecar with sockets on bones, physics bodies, LOD sizes, import settings. `Scripts/unreal/materials/np_skeletal.py` imports it in Unreal (mesh, LODs, LOD screen sizes, bounds, sockets on bones, physics asset from a proxy, animations with a chosen bone compression). The fan passed a two-process Unreal check on UE 5.8.3. [M] |
| Does Fab accept a static gun? | **Not as a firearm.** Fab's file-format page asks realistic firearms for "at least 1 high-quality firearms asset with all expected moving parts rigged and a full set of animations" [1]. Static `SM_` guns are fine for our own world props and the armory, but the Fab version has to be rigged and animated. [E] |
| Does the user's game need rigging? | **Yes.** User 2026-10-04: the magazine must move for reloads on every gun (memory `realistic-guns.md`). A separate static magazine attached to a bone socket covers the mag; trigger, bolt, slide, stock fold and bipod need bones. [M]/[J] |
| What the industry does | A skeletal receiver whose parts are weighted rigidly (100 %) to one bone each, a `Magazine` bone, and the magazine shipped as a **separate static mesh** placed on that bone; some bones exist only as sockets [2]. Lyra's rifle, shotgun and pistol skeletons are reused for new weapons so they need no unique animations [5]. Skeletal mesh sockets sit on bones [4]. [E] |
| What is missing for guns | A **gun library** (`Scripts/guns/gunlib/`): a standard bone and socket table, rigid binding of separate part objects, an export wrapper that writes SK (skeletal) + SM (static world variant) + SM_Mag from one build, gun QA gates on top of `qa_skeletal`, a gun deny list, and a gun Unreal harness adapted from the fan's. No change to `Scripts/pipeline/` is required for the first gun. [M]/[J] |
| Shared parts | Carbine and long rifle share the lower receiver, magazine, trigger group, grip, upper core and barrel/flash-hider profile; carbine, SMG, sniper and pistol carry rails (one rail standard); carbine and SMG both use flip-up sights. The sheets are **not** drawn at a common scale, so shared parts must come from one spec, not from each sheet. [M] |
| Impact on AR-01 | Keep the parts as separate objects with recorded pivots; add a rig stage (`SK_AR01` + bones) after the static build; keep `SM_AR01` as the world / armory variant and `SM_AR01_Mag` as the attached magazine. Details in section 7. [J] |

---

## 1. What `Scripts/pipeline/` supports today

### 1.1 Static path (every shipped prop so far) [M]

| Module | What it gives a gun |
|---|---|
| `export_fbx.py` (`kind="static"`) | House FBX settings (-Y forward, Z up, FBX Units Scale, triangulate, no tangents); selects `UCX_`/`SOCKET_`/`_LODn` children automatically; drops `SOCKET_` nodes from a LodGroup file (UE 5.8.2 loses them) and writes `<name>.sockets.json` with socket transforms in Unreal space plus `lod_screen_sizes` (house default 1.0 / 0.5 / 0.25). Refuses unapplied transforms, non-metric scenes and names without `SM_`/`SK_`/`A_`. |
| `helpers.py` | `make_ucx_hull`, `make_socket`, `make_lod_group`, `decimate_lods`, `ue_socket_transform`, `rename_with_helpers`. |
| `qa_check.py` | Transforms, unit scale, budget, descending LODs, n-gons, non-manifold, loose verts, degenerate geometry, UV0 tile range (default -1..2), UV overlap, UV1 for lightmaps, power-of-two images, colour spaces, `SM_`/`M_`/`MI_`/`T_` prefixes, `UCX_<node>_NN` keyed to the render node, `SOCKET_` = Empty, a deny list. Its skeletal item expects **one top-level bone** (lines 564-587), so it does not fit the fan-style rig; use `qa_skeletal` instead. |
| `textures.py` | Cycles AO bake, ORM pack, DirectX green flip, Non-Color reload. |
| `ue_import_sockets.py` | Recreates the sidecar sockets on a **static** mesh after import with `unreal.new_object(unreal.StaticMeshSocket, outer=mesh)` and applies the LOD screen sizes. |
| `lock.py` | Per-asset locks; `DEFAULT_LOCK_DIR` is the **main checkout's** `WorkFiles/locks` (line 53), so a worktree session sees and takes the same locks as the main checkout: good. |

### 1.2 Skeletal path (the fan) [M]

`Scripts/pipeline/skeletal_prop.py` (VERSION 1.0.0) is a separate module on top of the static pipeline; it does not
change `export_fbx`, `qa_check` or `helpers`.

- **Rig convention** (from ASSET_GUIDELINES 12.10): the armature OBJECT is named `root` (it becomes Unreal's root
  bone, so no bone is called `root`), identity transform, every bone deforms, no "." in bone names, optional bone
  budget (`skeleton_checks`).
- **Skin gates** (`skin_checks`): every mesh parented to the armature with an Armature modifier, every vertex
  weighted, weights sum to 1 (1e-5), at most `max_influences` (default 4; a rigid gun passes 1), every vertex group is
  a deform bone, mesh at identity.
- **Geometry gates** (`geometry_checks`): triangles only (the mesh must be triangulated **before** QA, unlike the
  static path, which triangulates at export), no stray verts, no zero-area faces or zero-length edges, edge-manifold,
  consistent winding, optional closed-solid groups.
- **UV / material gates** (`uv_material_checks`): UV0 finite and **strictly inside 0..1**, no collapsed UV triangles,
  at most `max_slots` (default 4) slots named `M_*`/`MI_*`.
- **Export** (`export_skeletal_set`): `<mesh>.fbx` (LOD0 + armature), `<mesh>_LOD<n>.fbx`, one `A_*.fbx` per action,
  all written from a throwaway **centimetre copy** (`SKELETAL_FBX_OVERRIDES`: FBX_SCALE_ALL, global scale 0.01) because
  Blender never scales bone translations and a metre file arrives in Unreal with scale 100 on the root bone (measured
  on UE 5.8.3). Location keys are scaled x100 too.
- **Sidecar** (`write_skeletal_sidecar`, schema `ninjapack.skeletal_prop/1`): free-form payload; the fan's carries
  `skeleton`, `bones`, `lod_files`, `lod_screen_sizes`, `animations` (file, fps, loop), `import`
  (bone compression, bounds extension, importer flags), `physics_proxies`, `physics_bodies`, `sockets`
  (`name`, `bone`, `location_mm`, `matrix`, `unreal_component` from `ue_component_transform`), `materials`.

Unreal side, `Scripts/unreal/materials/np_skeletal.py` (dispatched from `np_meshes.py` lines 61-149 for a spec item
with `"kind": "skeletal"`): legacy FBX importer (`FbxFactory` + `FbxImportUI`, import normals, convert scene and
unit, `use_t0_as_ref_pose` off), `SkeletalMeshEditorSubsystem.import_lod` for LOD1+, LOD screen sizes through a
`SkeletalMeshLODSettings` asset (LODInfo is not exposed to Python), positive/negative bounds extension, sockets made
relative to each bone's reference pose and added with `unreal.new_object(unreal.SkeletalMeshSocket, outer=mesh)`,
the physics asset built from a shipped proxy FBX (one body per proxy cube) then rewritten from the sidecar,
animations at their own rate with the sidecar's bone compression and loop flag, one save. The fan's independent
check (`WorkFiles/fan/UnrealCheck/fan_ue_pass2_verify.py`) reloads in a fresh process with a real RHI and checks
bones, reference poses, socket transforms, LODs, animation lengths, engine-evaluated poses, physics bodies, bounds
and offscreen renders.

### 1.3 Garment path (not for guns) [M]

`export_fbx(kind="garment")` + `garment_qa.py` write every bone of the locked MetaHuman skeleton in centimetres and
are verified through **Interchange** (ASSET_GUIDELINES 6.5). Guns are our own skeletons, so the fan path applies, not
the garment path. Note the importer split: garments go through Interchange, the fan (and everything static) through
the legacy FBX importer; a gun harness must say which one it uses (the fan's legacy path is the one measured for
props). [M]/[J]

### 1.4 Gaps and traps found in the existing code [M]

| # | Finding | Consequence for guns |
|---|---|---|
| G1 | `qa_skeletal` requires UV0 strictly inside 0..1 (`uv_material_checks`). The katana and kunai put their second slot in UV tile u 1..2 to keep slots apart for the lightmap packer (KATANA_BUILD_PLAN 1). | A gun that copies the katana UV trick fails skeletal QA. Either keep every island in 0..1 (a skeletal mesh needs no lightmap UV) or extend the check with a tile-range argument (a pipeline change, with its self-test). |
| G2 | `qa_skeletal` wants triangles only before export. | Triangulate the bound mesh in the build (the fan does) before QA. |
| G3 | The `export_fbx` CLI with `--kind skeletal` defaults to **metres** (`DEFAULT_UNITS` covers only garments). | Never export a gun through the CLI or `export_fbx(kind="skeletal")` directly; always `skeletal_prop.export_skeletal_set` (centimetre copy). |
| G4 | The deny list (`qa_check.py` lines 64-67) holds franchise words plus `awm`, matched as a **substring**. It catches `SM_AR01_DrawMag`, `A_AR01_DrawMagazine`, `SM_EA_Rail`, `SK_AR01_Hawmount` (tested). It has **no** gun trademarks (Kalashnikov, AKM, Colt, ArmaLite, M16, M4A1, UMP, Heckler, Glock, Desert Eagle, Magnum Research, Barrett, Remington...). | Gun part names must avoid "...dr**awm**ag..." style joins (use `MagDraw`, `A_AR01_ReloadDraw`). Gun names need their own deny list, checked by gunlib (word-boundary for short tokens such as `m4`, `m16`, `akm`), rather than editing the shared `qa_check` list. |
| G5 | `Scripts/Katana/katana_spec.py` line 19 hardcodes `ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")`; so do `garment_qa.py`, `test_pipeline.py`, `test_qa_negative.py`, `test_garment.py`. The senbon builder uses `Path(__file__).resolve().parents[2]`; `np_spec.py` uses `HERE.parents[2]`. | A gun script copied from the katana would read and **write the main checkout** when run from this worktree. gunlib must derive its root from `__file__` (or an env var), never a literal path. |
| G6 | `Scripts/showcase/studio.py` (the showcase renderer the house rule requires) exists **only** in `.claude/worktrees/cardshop-build-integration-5227b4/` - not in main, not in this branch. The katana report calls it from there. | The gun branch can call it by absolute path for now; it should land in main before the guns' showcase step. It imports FBX, so a skeletal LOD0 FBX renders in its rest pose. |
| G7 | `FAB_PUBLISHING_STUDY.md` is also only in the cardshop worktree (CLAUDE.md lists it as a root standard). | Read it from there; cite it as such. |
| G8 | The Unreal test project `WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject` is untracked and exists only in the main checkout. Every harness (`fan/UnrealCheck/run_ue.sh`, `katana/UnrealCheck/run_unreal_checks.sh`) imports into it under a new `/Game/<Item>Check/<run>` path. | Unreal checks from this worktree write into the main checkout's untracked project. Either accept that as the house practice (content path per run) or give the guns their own validation project (open question). |
| G9 | `np_skeletal` is reachable only through the pack-materials build (`np_meshes` spec items), which needs the `PackMaterials` lock and `run_build.sh`. Its functions (`mesh_ui`, `anim_ui`, `import_one`, `_add_sockets`, `_build_physics`) are plain and reusable from a gun harness. | Dev checks: call them from a gun harness. Pack integration (material instances, buyer recolour) stays in the shared materials build under the lock. |
| G10 | The three masters are `M_Steel_Master`, `M_Fabric_Master`, `M_PaperInk_Master` (`np_masters.py` line 223). | Steel covers blued/parkerized steel, anodized aluminium and stainless; Fabric (Default Lit mode, as the katana lacquer uses it) can carry wood, polymer, rubber and painted chassis. No glass master exists: a scope lens needs an opaque glossy stand-in or a new master (shared-materials work under the lock). |

---

## 2. What rigged weapons need on top (proposal)

### 2.1 The asset set per gun [J], grounded in [1][2][4][5]

| Asset | Kind | Role |
|---|---|---|
| `SK_<Code>` (+ `_LOD1`, `_LOD2`) | skeletal | The held gun: receiver and every non-detachable part, each part weighted 100 % to one bone. Physics asset from a proxy (fan method). No Nanite (skeletal Nanite is Experimental in 5.7 and 5.8, FAB_ASSET_STUDY.md Nanite paragraph). |
| `SM_<Code>_Mag` | static | The magazine: attaches to the `Mag` socket on the `magazine` bone while seated (so a reload animation on the gun moves it), to `hand_l` while being swapped, and drops as a physics object with its own `UCX_`. Carries a `SupportGrip` socket for the off hand. This is the Infima pattern [2]. |
| `A_<Code>_<Clip>` | animation | One action per FBX (house rule): `Fire` (trigger, bolt or slide, hammer), `Reload` / `ReloadEmpty` (mag release, `magazine` bone out and in, charging handle or bolt), `Inspect`, gun-specific (`StockFold`, `BipodDeploy`, `BoltCycle`, `SightFlip`). Character arm animations are a separate decision (section 8). |
| `SM_<Code>` | static | The world variant from the same parts at rest pose: pickups, the armory glass cases, set dressing; `UCX_` hulls, sockets sidecar, Nanite-capable. Cheap to produce from the same build (static export path, unchanged). |

### 2.2 Bone standard (one table for every gun; each gun uses a subset) [J]

The armature object is `root` (Unreal root bone, at the grip point = the weapon pivot, ASSET_GUIDELINES 1). Bones are
lower-case, underscore, no dots, all deforming (the exporter writes deform bones only; a socket-only bone still needs
`use_deform` on, so give it no weights):

| Bone | Parent | Guns | Motion |
|---|---|---|---|
| `body` | (top level) | all | carries every fixed part; the physics body |
| `trigger`, `hammer`, `selector`, `mag_release`, `bolt_catch` | `body` | all / as present | rotate about their pins |
| `bolt` | `body` | rifles, SMG, sniper | translate (AK carrier with its charging handle; AR bolt carrier); sniper: rotate then translate |
| `charging_handle` | `body` | carbine, long rifle, SMG | translate (AR T-handle, SMG side cocking handle) |
| `dust_cover` / `port_cover` | `body` | AK (cover removal not needed), AR (port door) | rotate |
| `slide` | `body` | pistol | translate (recoil) |
| `magazine` | `body` | all | translate/rotate out of the well; `SM_<Code>_Mag` attaches here |
| `stock` | `body` | SMG (fold), carbine (collapse) | rotate / translate |
| `sight_front`, `sight_rear` | `body` | SMG, carbine (flip), AK (leaf) | rotate |
| `bipod_l`, `bipod_r` | `body` | sniper | rotate (fold) |
| `cheek_riser` | `body` | sniper | translate (optional) |

Sockets (sidecar records on bones, the fan's format): `Grip` (on `body`, attach to `hand_r`), `SupportHand` (off-hand
IK target on the handguard), `Muzzle`, `Eject` (shell/VFX), `Mag` (on `magazine`), `AimPoint` (eye line through the
sights or optic), `Rail_<Name>_<NN>` (rail slots, section 4.3), `Sling_Front`, `Sling_Rear`, `Back` (character back
or holster slot), `CenterOfMass`. On `SM_<Code>_Mag`: `Seat` (= pivot, coincides with the gun's `Mag` socket),
`SupportGrip`. [J]

Frame: Blender metres, model in mm; **muzzle +X, up +Z, the gun's right side toward Blender -Y**. Through the pipeline
(forward -Y, up Z) and `ue_component_transform` (Unreal = x, -y, z) that lands as muzzle +X, right +Y, up +Z in
Unreal's left-handed space, i.e. actor-forward. The sidecar transform is measured for the fan [M]; the gun frame
itself is [J] and needs one measured round trip in Unreal on the first gun.

### 2.3 Code to add (none of it edits `Scripts/pipeline/`) [J]

| Piece | Built from |
|---|---|
| `gunlib/rig.py`: armature from the bone table, **rigid bind** (each part object gets one vertex group at weight 1.0, then the parts of one LOD are joined into one mesh), triangulate, actions from keyed bone transforms | `props_lib/fan_look.py` (`make_armature`, `mesh_object` with weights, `pose`, `key_action`, `rest_matrices`) |
| `gunlib/export_gun.py`: SK set (`skeletal_prop.export_skeletal_set`), the skeletal sidecar with sockets on bones, physics proxy FBX, `SM_<Code>_Mag` and `SM_<Code>` through `export_fbx(kind="static")` with UCX + sockets sidecar | `skeletal_prop`, `export_fbx`, `helpers`, `build_fan.py` (sidecar assembly) |
| `gunlib/qa_gun.py`: `qa_skeletal(max_influences=1)` + bone-table names + gun deny list + frame check (muzzle +X) + **mag seat** (SM_Mag at the `Mag` socket coincides with the well within 0.05 mm, no interpenetration) + **pose sweep** (every animation frame: no rigid part intersects another, bolt/slide return to rest at the clip end) + `qa_check` on the static variants | `qa_check`, `skeletal_prop`, the saya fit checks (`Scripts/Katana/saya_fit.py`, `saya_verify.py`: BVH intersection on exported bytes) |
| Unreal gun harness (`WorkFiles/guns/<gun>/UnrealCheck/`): pass 1 imports SK + LODs + animations + physics + both static meshes in one process; pass 2 in a fresh process checks bones and reference poses, socket transforms vs the sidecar, **the mag composition** (SM_Mag attached at `Mag` lands on the sidecar transform within 0.001 cm, at rest and at sampled reload frames), animation lengths and engine-evaluated end poses, **bone compression error** on rigid parts (ACL default vs `DefaultRecorderBoneCompression`; the fan measured ACL cracks of 1.1 mm), physics bodies, bounds over every clip, offscreen renders; sha256 of the bytes | `WorkFiles/fan/UnrealCheck/` (`run_ue.sh`, pass 1/2, `fan_ue_common.py`), `WorkFiles/katana/UnrealVerify_Indep/` (sha256 start/end, independent re-verify), `np_skeletal` functions |

---

## 3. Tools that can be reused as they are or with small changes [M]

| Tool | Where | Reuse for guns |
|---|---|---|
| Spec-as-authority pattern | `WorkFiles/katana/katana_spec.json` + `Scripts/Katana/katana_spec.py` (pure numpy, shared by builder, painter, measurer, fit) | One `<gun>_spec.json` per gun + one shared `gun_standard.json` (bones, sockets, frame, rail, shared parts); fix the hardcoded root (G5). |
| Mesh builder | `Scripts/Katana/katana_mesh.py` (`MB` mesh builder, `grid`, `sweep`, `ring_uv`, `profile_loft_uv`, `cap_fill`), `katana_parts.py` (`loft_rings`, `revolve`, super-ellipse rings) | Barrels, tubes, gas tubes, scopes, muzzle devices, pins (revolve/loft); a generalized copy goes to `gunlib/mesh.py`. |
| Same-generator LODs | KATANA_BUILD_PLAN 1: LOD1/LOD2 from the same generator at lower resolution, same UV islands, no Decimate | Gun parts are generated per LOD the same way; the skeletal LOD files need the same bones (no bone removal, as the fan). |
| Game stage | `Scripts/Katana/katana_game.py` (`make_game_material`, `mass_properties`, hull from points, grow hull to contain, dense samples) | Static variant hulls and centre of mass; `mass_properties` feeds `CenterOfMass` and the physics body mass. |
| Measure / compare | `katana_measure.py`, `katana_compare.py`, `katana_render.py` (`sheet_views`, `shot`, orthographic cameras), `katana_render_crops.py`, `katana_preview.py` | Orthographic renders matched to the sheet views and side-by-side composites for the blind test. |
| Trace | `props_lib/trace.py` (sub-pixel contours, spline fit, analysis-by-synthesis refinement), `paperbomb_trace.py`; the rifle study's `WorkFiles/guns/rifle/tools/refimg.py` (panel finder, backdrop model, marching squares, Douglas-Peucker) | Side-view silhouettes as the 2D outline authority (CLAUDE.md: tracing works as the outline authority). `refimg.py` should be promoted into gunlib once the rifle study is done with it (it is not ours to edit now). |
| Senbon / kunai | `Scripts/props/build_senbon.py`, `props_lib/senbon_*.py` | Small hard-surface parts, recolour wraps; `__file__`-relative root (the pattern to copy). |
| Skeletal QA/export | `Scripts/pipeline/skeletal_prop.py` | Used unchanged (`max_influences=1`). |
| Skeletal import | `Scripts/unreal/materials/np_skeletal.py` | Called from the gun harness; pack integration through the materials build. |
| Static sockets | `Scripts/pipeline/ue_import_sockets.py` | `SM_<Code>` and `SM_<Code>_Mag` sockets after import. |
| Fit verification | `Scripts/Katana/saya_fit.py`, `saya_verify.py`, `WorkFiles/katana/UnrealVerify_Indep/kv3_fit.py` | Mag seat, mag draw path out of the well, stock fold clearance. |
| Unreal harness | `WorkFiles/fan/UnrealCheck/run_ue.sh` (refuses to start when another `UnrealEditor-Cmd` runs; kills only its own leftover), `WorkFiles/katana/UnrealCheck/run_unreal_checks.sh` | Copy and adapt per gun. |
| Recolour | `Scripts/Katana/katana_recolour.py`, `Scripts/unreal/materials/` (`material_spec.json` items, `run_build.sh`) | Buyer recolour of furniture (wood, polymer, paint); `PackMaterials` lock required. |
| Showcase | `.claude/worktrees/cardshop-build-integration-5227b4/Scripts/showcase/studio.py` | Studio shots of `SM_<Code>` (static is simplest); see G6. |
| Locks | `Scripts/pipeline/lock.py` | One lock per gun plus shared locks (section 6). |

---

## 4. The six sheets: shared parts and build order

### 4.1 What each sheet shows [M by eye, numbers measured]

| Gun | Sheet | Views | Ruler-scaled length (asked) | Notes |
|---|---|---|---|---|
| Rifle (AK style) | `Rifle/rifle_sheetAB.webp` | L, R, top, 3/4 + 7 close-ups | 97 cm if the ruler spans 90 cm, 108 cm if its ticks are 10 cm (asked 88) | Ruler has **11 ticks labelled 0..90 with "90" twice**, so it cannot set scale. The panel labelled LEFT shows the muzzle to the right and the selector lever, i.e. the gun's **right** side (the AK selector is on the right); the labels are swapped. |
| SMG | `SMG/smg_sheetA.webp` | L, R, top, 3/4 | 86.6 cm (asked 69) | Labels consistent (charging handle on the left panel, as asked). No close-ups (ChatGPT refused Sheet B). |
| Carbine (M4 style) | `Carbine/carbine_sheetA.webp` | L, R, top, 3/4 (no labels) | 99 cm (asked 84) | Flat-top rail, slotted free-float handguard, flip sights up, collapsible stock half out. |
| Long rifle (M16 style) | `LongRifle/longrifle_sheetA.webp` | L, R, top, 3/4 | 117 cm (asked 100) | Carry handle, round ribbed handguard, triangle front sight, fixed stock, sling loops. |
| Sniper | `Sniper/sniper_sheetA.webp` | L, R, top, 3/4 | no ruler (asked ~120) | LEFT panel shows the bolt handle, i.e. the gun's **right** side (labels swapped); bipod folded in the side views, deployed in the 3/4. Detachable box mag drawn. |
| Pistol | `Pistol/pistol_sheetA.webp` | L, R, top, 3/4 | ~29.5 cm (asked 27) | Views consistent; short top rail on the barrel; flush grip mag (base plate visible). |

Rule from this: identify sides by handed features (selector, ejection port, bolt handle, charging handle), never by
the panel label, and set real-world scale ourselves (the prompts file already says the rulers are unreliable).

### 4.2 Cross-sheet scale check (why shared parts need one spec) [M]

The magazine hangs the same way on the carbine and long-rifle sheets, so if both drew the same magazine at the same
scale, the long rifle should be about 1.19x the carbine's length (asked 1000 / 840 mm). Measured on the left views
(silhouette, magazine drop below the handguard line, coarse to about 5 %): carbine 115 px drop on a 592 px gun, long
rifle 112 px on a 601 px gun. Scaling both so the magazines match makes the long rifle only **1.04x** the carbine.
With each sheet's own ruler, the same magazine measures 19.2 cm on the carbine and 21.8 cm on the long rifle. So the
sheets are mutually inconsistent by about 13 %: a part shared by two guns must be modelled once from a single spec, and
each gun's own proportions are fitted around the shared part, not read independently from its sheet.

### 4.3 Part map [M by eye / J]

| Part family | AR-01 Rifle | SMG | Carbine | Long rifle | Sniper | Pistol | Share how |
|---|---|---|---|---|---|---|---|
| Lower receiver (mag well, guard, controls, buffer ring) | own (stamped) | own (polymer) | **A** | **A** | own (chassis) | own (frame) | carbine + long rifle: one mesh/generator |
| Upper core (port, port door, forward assist, charging handle) | own | own | **B** | **B** | own | slide | one core; carbine adds rail top, long rifle adds a **separate carry-handle part** on the same core |
| Magazine, curved 30 | own curve (AK) | - | **C** | **C** | - | - | one `SM_` mag for both black rifles; the AK mag from the same **curved-box generator** with its own parameters |
| Magazine, straight box | - | own | - | - | own | own (grip) | one **straight-box generator** |
| Trigger, guard, selector, mag release | own | own | **D** | **D** | own | own | black rifles share; others share generators only |
| Pistol grip | wood | integral | ergonomic | plain A2 | own | wraparound | separate black-rifle grips (the sheets differ); same mount |
| Barrel + flash hider | slant brake | short + cage | birdcage, short | birdcage, long | fluted + cap | inside slide | barrel generator; one birdcage design at two lengths |
| Front sight | AK block | flip | flip on rail | triangle tower | - | fixed block | SMG + carbine flip sights: one design |
| Rear sight | AK leaf | flip diopter | flip diopter | in carry handle | - | fixed block | SMG + carbine: one design |
| Rail | - | top + lower | top + handguard | (carry-handle top none) | top (scope base) | short top | **one rail standard** (profile, slot pitch, socket names `Rail_<Name>_<NN>`), shared with the planned attachments kit |
| Handguard | wood pair | integral | slotted free-float | round ribbed | chassis slots | - | own each |
| Stock | wood fixed | skeleton folding | collapsible on tube | fixed A2 | chassis + riser + pad | - | own each; black-rifle buffer-tube interface shared |
| Scope | - | - | - | - | rings + scope | - | build the scope as the first **attachment** on the rail standard, not baked into the sniper |
| Bipod | - | - | - | - | folding | - | own (bones `bipod_l/r`) |
| Small hardware (pins, screws, rivets, swivels, springs) | all | all | all | all | all | all | gunlib hardware generators |

### 4.4 Build order [J]

1. **AR-01 Rifle** (running). Pilot for the rig stage, the gun harness and the gunlib split (extract what is generic
   after it works, as the fan's module was extracted).
2. **SMG** (user: automatically after the rifle). Adds the straight-box mag generator, the rail standard, flip sights
   and a folding stock bone.
3. **Carbine**. Defines the black-rifle shared parts A-D, reuses the SMG's rail and flip sights.
4. **Long rifle**. Reuses A-D plus the barrel and birdcage; new carry handle, ribbed handguard, triangle sight, fixed
   stock. Expect roughly half of its parts to come from the carbine.
5. **Pistol**. Small, slide bone; reuses the rail and the straight-box generator.
6. **Sniper**. Bolt (rotate + translate), bipod, chassis; the scope is attachment no. 1 for the attachments kit.

(The pistol can move earlier if the 1v1 MVP wants a sidearm first.)

---

## 5. Folder and file layout (proposal) [J]

```
Scripts/guns/
  gunlib/                      shared library (lock GunLib)
    __init__.py                LIB_VERSION; root from __file__, never a literal path (G5)
    standard.py                loads WorkFiles/guns/gunlib/gun_standard.json: frame, bone table, socket names, rail
    mesh.py                    generalized katana_mesh (MB, loft, revolve, sweep, caps, UV helpers)
    parts/                     generators: barrel.py, muzzle.py, rail.py, mag_curved.py, mag_box.py,
                               trigger_group.py, sights_flip.py, hardware.py (pins, screws, swivels, springs)
    rig.py                     armature from the table, rigid bind, triangulate, key actions
    sockets.py                 socket records on bones -> sidecar (skeletal_prop.ue_component_transform)
    qa_gun.py                  qa_skeletal(max_influences=1) + gun gates + gun deny list
    export_gun.py              SK set + SM world variant + SM_Mag + physics proxy + sidecars
    render.py, compare.py      sheet-matched ortho renders and side-by-sides (from katana_render / katana_compare)
    refimg.py                  promoted from WorkFiles/guns/rifle/tools/ after the rifle study
  rifle/  smg/  carbine/  longrifle/  sniper/  pistol/
    build_<gun>.py             staged builder (geo -> rig -> maps -> game -> export), lock asserted at the top
    <gun>_parts.py             gun-specific parts
    run_<gun>.sh
WorkFiles/guns/
  gunlib/gun_standard.json     the shared standard (bones, sockets, frame, rail profile, shared-part specs)
  <gun>/                       study, <gun>_spec.json (authority), reports, UnrealCheck/, check scripts
Assets/Guns/<Code>.blend       one per gun (LFS)
Exports/Guns/<Code>/           SK_<Code>.fbx, SK_<Code>_LOD1/2.fbx, SK_<Code>.skeletal.json, A_<Code>_*.fbx,
                               SM_<Code>.fbx + .sockets.json, SM_<Code>_Mag.fbx + .sockets.json,
                               Physics/SK_<Code>_PhysicsProxy.fbx, Textures/, README.md, MATERIALS_README.md
Exports/Guns/Shared/           meshes used by more than one gun (black-rifle mag, flip sights), later Attachments/
Renders/Guns/<Code>/           final renders and reference side-by-sides (LFS)
showcase/<Product_Name>/       e.g. showcase/AssaultRifle_AR01/ plus the ASSET_LIST.md row
```

Folders under `Scripts/guns/` and `WorkFiles/guns/` follow the **role** (rifle, smg...), as `References/Guns/<Role>/`
and the running `WorkFiles/guns/rifle/` already do, so a product rename for Fab touches only the code-named outputs.

### 5.1 Names [J]

| Role | Product name (generic) | Asset code | Lock |
|---|---|---|---|
| Rifle (AK style) | Assault Rifle AR-01 | `AR01` | `AR01` |
| SMG | Compact SMG SM-01 | `SMG01` (not `SM01`: `SM_SM01` / `SK_SM01` collide visually with the `SM_` prefix) | `SMG01` |
| Carbine (M4 style) | Carbine CB-01 | `CB01` | `CB01` |
| Long rifle (M16 style) | Long Rifle LR-01 | `LR01` | `LR01` |
| Sniper | Sniper Rifle SR-01 | `SR01` | `SR01` |
| Pistol | Heavy Pistol HP-01 | `HP01` | `HP01` |
| Shared | - | `Shared` meshes, e.g. `SM_GunMag_Curved30A`, `SM_GunSight_FlipFront` | `GunShared` |
| Library + standard | - | - | `GunLib` |

Materials and textures per gun: `M_<Code>_<Part>` / `MI_<Code>_<Part>`, `T_<Code>_<Part>_BC/ORM/N`. Skeleton asset in
Unreal: `SK_<Code>_Skeleton` per gun at first (a skeleton shared across guns is tied to the animation-source decision,
section 8). Physics: `PHYS_<Code>`. Unreal content root: a gun pack root (e.g. `/Game/<GunPack>/Guns/<Code>/`) once
the pack name is chosen; `/Game/GunCheck/<Code>_<run>` for verification runs.

IP notes [J]: "AR" is commonly read as ArmaLite Rifle and "AR-15" is a trademark; "AR-01" is a different designation
and low risk, but never write "AR-15", "M4", "M16", "AK", "UMP" or maker names in any name, README or listing; the gun
deny list enforces this. Both black rifles and the AK sheet are near-replicas of real designs (memory
`realistic-guns.md`), so the Fab versions need original detail changes, which the shared-parts spec makes cheap to
apply once for both black rifles.

---

## 6. Locks and concurrency [M]/[J]

- Each gun takes its own lock before opening its `.blend` (`py -3 Scripts/pipeline/lock.py claim AR01 --agent
  claude`); the lock dir is the main checkout's, shared with every worktree (section 1.1, `lock.py`).
- `GunLib` guards `Scripts/guns/gunlib/` and `gun_standard.json`; a gun build that needs a library change takes it,
  bumps `LIB_VERSION`, re-runs the earlier guns' QA (the katana/kunai pattern of hash checks at start and end, as
  `build_fan.py` does for modules it must not touch).
- `GunShared` guards `Exports/Guns/Shared/`.
- `PackMaterials` (existing, `np_lock.py`) for any change under `Scripts/unreal/materials/`.
- One Unreal commandlet at a time on the machine; the fan harness's guard (refuse to start, stop only its own leftover)
  is the one to copy.

---

## 7. What the AR-01 rifle plan must change [J]

The rifle study assumed static `SM_AR01` + `SM_AR01_Mag`. To stay compatible with the user's reload requirement and
Fab's firearm rule [1]:

1. Build every moving part as its **own object** (trigger, hammer if visible, selector lever, mag release, bolt carrier
   with its charging handle, dust cover, rear sight leaf) with its **pivot and axis recorded in the spec** (pin
   centres, slide axis, travel limits). No booleans or joins of moving parts into the receiver.
2. Add a rig stage after the static build: `root` object at the grip point, bones from the standard table, rigid
   weights, `qa_skeletal(max_influences=1)`, export with `skeletal_prop.export_skeletal_set` into `SK_AR01*.fbx`.
3. Keep `SM_AR01` as the static world / armory variant (same parts at rest, UCX hulls) and `SM_AR01_Mag` as the
   attached magazine with `Seat` and `SupportGrip` sockets; the gun's `Mag` socket sits on the `magazine` bone.
4. Keep every UV island inside 0..1 (no katana u 1..2 tile) so the skeletal UV gate passes (G1).
5. Frame: muzzle +X, up +Z, right side toward -Y, origin at the grip; sockets per section 2.2.
6. Export to `Exports/Guns/AR01/` (the memory note says `Exports/AR01`; pick one before the first export).
7. Avoid deny-list joins in part and clip names (`DrawMag` hits `awm`, G4).
8. Animations for the Fab version: at least `Fire`, `Reload`, `ReloadEmpty`; which character animations go with them
   is open (section 8).

Doing the static build first and rigging second is fine as long as points 1 and 4 hold; nothing has to be remodelled.

---

## 8. Decisions only the user can make

1. **Where character (arms) animations come from.** If we adopt an existing weapon skeleton (Lyra's rifle / pistol /
   shotgun skeletons [5], or a Fab FPS animation pack's, e.g. Infima's bone names [2]), our bone names and sockets
   should match it from the first gun, and existing reload/fire animations work without new ones. If we keep our own
   standard, every reload needs our own character animation. This decides the bone table in 2.2.
2. **Static first, rig later, or rig from the AR-01 onward?** (Recommendation: AR-01 is the rig pilot; the rig stage is
   small once parts are separate.)
3. **Exports layout:** `Exports/Guns/<Code>/` (proposed) or `Exports/<Code>/` (the rifle study's assumption).
4. **SMG asset code:** `SMG01` (proposed) or keep `SM01`.
5. **Unreal validation project:** keep importing into the main checkout's untracked `ShurikenValidation` project
   (house practice, new content path per run) or give the guns their own project.
6. **Fab packaging:** one gun pack (one content root, shared rail and mags) or a product per gun; and whether the
   game's guns may stay closer to the real designs than the Fab versions.
7. **Scope lens:** accept an opaque glossy lens on an existing master, or add a glass master to the shared materials.

---

## Sources

1. Epic Games, "Asset File Format and Structure Requirements" (Fab): firearms need "all expected moving parts rigged
   and a full set of animations"; smart-asset weapons "rigged and animated".
   https://dev.epicgames.com/documentation/en-us/fab/asset-file-format-and-structure-requirements-in-fab
2. Infima Games, "How to Replace the Weapon With a Custom Model in Unreal Engine 5 (Blender to UE5)": skeletal weapon
   on an existing weapon skeleton; everything weighted to `Grip` first, moving parts reassigned rigidly to `Trigger`,
   `Bolt`, `Dust_Cover`, `Charging_Handle`, `Magazine_Release`, `Fire_Selector`; `Magazine` bone; some bones are
   socket-only; the magazine is a separate static mesh with its origin on the magazine bone.
   https://docs.infimagames.com/product/tactical-fps-animation-packs/guides-and-tutorials/editor/how-to-replace-the-weapon-with-a-custom-model-in-unreal-engine-5-blender-to-ue5
3. Epic Games, "FBX Import Errors in Unreal Engine": meshes nested in a bone hierarchy need Import Meshes In Bone
   Hierarchy; a skeletal mesh needs at least one weighted vertex.
   https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-import-errors-in-unreal-engine
4. Epic Games, "Skeletal Mesh Sockets in Unreal Engine": sockets are attach points relative to a parent bone.
   https://dev.epicgames.com/documentation/en-us/unreal-engine/skeletal-mesh-sockets-in-unreal-engine
5. TPS-Docs, "How to add custom weapons": weapons built on Lyra's base meshes; the rifle, shotgun and pistol skeletons
   are reused for new weapons without unique animations. https://docs.page/soriox/TPS-Docs/tutorials/custom-weapon
6. Epic Games, "Lyra Inventory and Equipment in Unreal Engine": equipment definitions list the actors spawned at equip
   time. https://dev.epicgames.com/documentation/en-us/unreal-engine/lyra-inventory-and-equipment-in-unreal-engine

Repo files read (all [M]): `Scripts/pipeline/` (`__init__.py`, `export_fbx.py`, `skeletal_prop.py`, `qa_check.py`,
`ue_import_sockets.py`, `lock.py`), `Scripts/unreal/materials/np_skeletal.py`, `np_meshes.py`, `np_masters.py`,
`material_spec.json`, `Scripts/props/build_fan.py`, `props_lib/fan_look.py`, `props_lib/trace.py`,
`props_lib/paperbomb_trace.py`, `Scripts/Katana/` (spec, mesh, parts, game, measure, compare, render), `Exports/Fan/README.md`
and `SK_Fan.skeletal.json`, `WorkFiles/fan/UnrealCheck/` (`run_ue.sh`, pass 2), `WorkFiles/katana/` (build plan,
report, UnrealCheck, UnrealVerify_Indep), `ASSET_GUIDELINES.md` (1, 5-9), `FAB_ASSET_STUDY.md` (firearm and Fab
minimum lines), `References/Guns/` (six sheets and README), `WorkFiles/guns/GUN_REFERENCE_PROMPTS.md`,
`WorkFiles/guns/rifle/tools/refimg.py` (read only), `showcase/ASSET_LIST.md`, `WorkFiles/asset_audit_2026-09-17/inv_AWM_Sniper.json`.
