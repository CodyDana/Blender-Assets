# Armory hall: two-way sync rules

Revision 4, 2026-10-01. Owner decisions of 2026-10-01: the armory is the interior of the dojo's main hall, the two
projects stay in sync both ways, and **ArmoryLab shows the same extended hall around its interior** (section 11).
Revision 4 adds: the ArmoryLab step order (section 3.2: the armory's own steps first, the shell tool last), which
revisions need a sync (3.4), and the shell master graph as a revisioned shared input (section 15).
This folder is the shared source of truth. Every command below runs from the repo root
`C:/Users/Cody/Desktop/Blender_Projects` with `py -3 -B` (plain Python 3; no Unreal, no Blender) unless it says Unreal.

| Side | Chat | Unreal project / level |
|---|---|---|
| Interior (the armory) | the armory chat | `ArmoryLab`, `/Game/Armory/Maps/L_Armory` |
| Shell (the hall + its rear extension) | the dojo chat | `DojoLab`, `L_Dojo` |

## 0. Session start (both chats, every time, before any armory or hall work)

```
py -3 -B WorkFiles/shared/armory_hall/tools/check_sync.py --side armory     # the armory chat
py -3 -B WorkFiles/shared/armory_hall/tools/check_sync.py --side dojo       # the dojo chat
```

It runs every section-8 check and compares the revision your project last synced with the revision it needs
(section 3.4).

| Exit | Meaning | Do |
|---|---|---|
| 0 | all checks pass, your project is synced (at or after the revision it needs, section 3.4) | work |
| 2 | all checks pass, your project is behind (or, armory side, L_Armory is no longer the hall variant) | sync your project first (section 3), then work |
| 3 | a generated shared file is stale: `interior_layout.json` / `lights_design.json` against the armory's own build data; on the dojo side also `shell_materials.json` / `shell_masters.json` against the dojo's | armory chat: section 12 steps 4-7. Dojo chat: its own files, section 13 steps 4-6; the interior files: tell the owner, do not edit them |
| 1 | a check failed (the message names the file and who owes what; armory side: also a dojo master graph change not yet snapshotted and bumped, section 15) | fix it, or tell the owner; never build on a failed check |

## 1. What is here

| File | Holds | Owner |
|---|---|---|
| `SYNC.md` | These rules | both |
| `manifest.json` | Revision, dated change log, last synced revision per project, sha256 of every FBX / texture / material and of every shared file | both, written only by `tools/bump_manifest.py` |
| `interior_layout.json` | Every interior instance (stable `AKI_*` ids), case, item, the not-used list, reference cameras | armory chat, written only by `tools/regen_interior.py` |
| `lights_design.json` | The design lights that travel with the interior + per-level values | armory chat (`tools/regen_interior.py`); per-level entries by their level's chat |
| `hall_shell_layout.json` | The hall shell: kept / removed / replaced `SM_DKH_*` instances, the new ones, the shell's lights | dojo chat |
| `shell_materials.json` | Everything ArmoryLab needs to rebuild the shell's materials and import its meshes (section 11) | dojo chat, written only by `Scripts/dojo/hall/make_shell_materials.py` |
| `shell_masters.json` | The exact graph code + parameters of the two shell masters ArmoryLab builds, and its `graph_sha256` (section 15) | dojo chat, written only by `tools/master_snapshot.py --write` |
| `interface.json` | The contract: frames, floors, the interior envelope, doors, gameplay, site moves (DojoLab only), decisions | both, only when the owner asks (`INTERFACE CHANGED` in the change line) |
| `tools/` | `check_sync.py`, `regen_interior.py`, `bump_manifest.py`, `master_snapshot.py`, `ue_armorylab_shell.py` (Unreal), helpers `ahcommon.py`, `fbxlite.py` | both; a tool change is a shared change (bump) |

## 2. Frames and units

- **Metres** everywhere. `rot_z` is in degrees about +Z. Unreal: cm = (x·100, −y·100, z·100), yaw = −rot_z.
- **Hall-local** (all layout files): the origin is the hall's centre door threshold (the door-bay sill centre line)
  at finished floor level. +X is east, +Y is north into the hall, +Z is up.
- **DojoLab world** = hall-local + (22.0, 24.0, 0.50). `hall_shell_layout.json` `loc_world_m` / `bbox_world_m` are in
  this frame: hall-local = loc_world_m − (22.0, 24.0, 0.50).
- **Armory frame → hall-local**: hall-local = armory + (−6.0, 0.0, 0.0). A pure translation.
- **ArmoryLab world** = hall-local + (6.0, 0.0, 0.0) = the armory frame, so ArmoryLab's interior stays where it is.
  The hall's courtyard grade is then at ArmoryLab z −0.50, the hall floor = the armory floor at z 0.
- Instance ids are stable strings: `AKI_*` (interior) and `DKH_S*` / `DKH_N*` (shell). An id is never reused. A
  moved instance keeps its id. `regen_interior.py` keeps the ids by piece + armory location (+ nearest within 1 m for
  a moved piece); a vanished id goes to `interior_layout.json` `retired_ids`.

## 3. Sync your project

### 3.1 DojoLab (the dojo chat)

`bash Scripts/dojo/unreal/run_armory_sync.sh` (after `sc_import` / `sc_materials` / `sc_level` when the shell changed;
after `sc_materials` when the shell master graph changed, section 15). It writes
`WorkFiles/dojo/build/unreal/armory_sync/synced_revision.json`. Then section 3.3.

### 3.2 ArmoryLab (the armory chat): your own steps first, the shell tool LAST

The order is fixed, every sync. `ue_armorylab_shell.py` turns L_Armory into the hall variant, and the armory's own
gates are written for the standalone armory, so they run before it, never after it.

1. `py -3 -B WorkFiles/shared/armory_hall/tools/check_sync.py --side armory`: exit 0 or 2 (1 or 3: section 0).
2. **Your own routine, complete, on your own unmodified layout** (exactly as today; every gate must pass):
   ```
   bash Scripts/armory/unreal/run_armory_unreal.sh
   ```
   (its default list: `project bounds build import materials level manny firstperson verify character walk capture
   fptest stats`; or the subset you need, as long as it contains `level` and every Unreal step you want this session,
   e.g. `bash Scripts/armory/unreal/run_armory_unreal.sh import materials level verify character`). Here `ak_verify.py`
   (1 cm bounds on every `<piece>__<nnn>`), `ak_character.py`, the walk check, `ak_capture.py`, `ak_fptest.ps1` and
   `ak_image_stats.py` judge the armory as its own design: its own entrance, PlayerStart and Blender baselines.
3. **The shell tool, the LAST Unreal step** (one commandlet; no ArmoryLab editor open, no other commandlet running):
   ```
   "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "C:/Users/Cody/Documents/Unreal Projects/ArmoryLab/ArmoryLab.uproject" -run=pythonscript -script="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shared/armory_hall/tools/ue_armorylab_shell.py" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput
   ```
   It saves L_Armory as the hall variant: 161 shell actors (tag `AH_Shell`), the armory's 165 exterior actors hidden
   (tag `AH_ExteriorHidden`), the 8 floor tiles `AKI_9001..9008`, and +0.12 m on `SM_AK_EntryMat__335`,
   `SM_AK_Lantern__612`, `SM_AK_Lantern__613` and the lights `Lantern_3.76_1.8`, `Lantern_8.24_1.8`. Its log ends
   `AH_SHELL_DONE passed=True`; on a pass it writes
   `WorkFiles/armory/build/unreal/armory_hall_sync/{shell.json, shell_import_manifest.json, synced_revision.json}`.
4. **The hall-variant check**: `py -3 -B WorkFiles/shared/armory_hall/tools/check_sync.py --side armory` must exit 0.
   Besides section 8 it reads `shell.json` (passed, not a test run, at the recorded revision; `shell_placed`, exterior
   hidden `found` = `want`, `substitution_tiles` and `lifted` equal to what the shared files give now; bounds <= 1 cm;
   `lifted_missing` empty) and checks that `WorkFiles/armory/build/unreal/level.json` is not newer than `shell.json`.
5. Record it: section 3.3.

**After step 3, no `ak_*` Unreal step runs on L_Armory.** `ak_verify.py` gate_level would fail on exactly the three
lifted actors (+12 cm in Z: the hall variant, not a defect), and character / capture / fptest / stats would judge the
hall variant against the standalone armory's baselines (the PlayerStart now stands in front of the hall's steps, the
armory's entrance is hidden). To re-run any of them: from `level` again (`bash Scripts/armory/unreal/run_armory_unreal.sh
level <steps>`; `ak_level.py` rebuilds the standalone level), then steps 3 and 4 again. A forgotten step 3 shows as
exit 2 (`hall_variant: ak_level.py rebuilt L_Armory after the tool`). Gameplay on the hall variant (walk routes,
CONTROLs) is gated in DojoLab (section 8); in ArmoryLab look at it in the editor (section 14 step 6).

*Optional, the armory chat's own decision and code (nothing in this folder needs it):* to also verify the saved hall
variant in a fresh process with your own verify, teach `ak_verify.py` gate_level to honour exactly the hall-variant
exceptions, read from the shared files (no separate offsets file): every `interior_layout.json` instance with
`z_shift_m` and a `src_armory.layout_index` -> actor `<piece>__<layout_index, 3 digits>` expects its Blender box
+ `z_shift_m` x 100 cm on both Z bounds (today `SM_AK_EntryMat__335`, `SM_AK_Lantern__612`, `SM_AK_Lantern__613`,
+12 cm). Then `bash Scripts/armory/unreal/run_armory_unreal.sh verify` after step 3. As far as a read of
`ak_verify.py` shows, nothing else in it changes with the hall variant: hidden actors keep their mesh and bounds, light
locations are not gated, and the added actors (`<piece>__AKI_9001..9008`, `SM_DKH_*__DKH_*`, `BackerLight_*`,
`AH_CourtyardGround_StandIn`) are not in `layout.json` (gate_hero counts by label prefix; no floor-tile piece is a
hero piece today).

### 3.3 Record the sync (both chats)

- `check_sync.py --side <yours>` must exit 0; claim the lock, `bump_manifest.py --record-sync DojoLab|ArmoryLab`,
  release, and write `armory_hall synced rev N` in your own BUILD_NOTES.md.
- Never build on top of an unsynced revision. One Unreal process per project, one commandlet machine-wide.

### 3.4 Which revisions need a sync (rev 4)

- `manifest.json` `sync_needed_rev[<project>]` is the last revision that changed something that project's Unreal sync
  reads; `bump_manifest.py` sets it. A bump that changes only `SYNC.md` or the plain-Python tools (`ahcommon.py`,
  `fbxlite.py`, `regen_interior.py`, `bump_manifest.py`, `check_sync.py`, `master_snapshot.py`) leaves it;
  `ue_armorylab_shell.py` moves ArmoryLab's; any other shared file, any FBX / texture / material entry, the shell
  master graph (section 15) or an interface change moves both; `--sync-all` forces both. A shared file or asset section
  recorded for the first time is "added", not "changed".
- `check_sync.py`: your project's synced revision >= its `sync_needed_rev` = synced (exit 0). A docs / tools-only
  revision is therefore recorded without an Unreal run: exit 0, `--record-sync`, `armory_hall synced rev N`.

## 4. Ownership and who may edit

- The **interior** belongs to the armory chat: `interior_layout.json`, `lights_design.json`, `SM_AK_*`,
  `Scripts/armory`, `Exports/ArmoryKit`, ArmoryLab.
- The **shell** belongs to the dojo chat: `hall_shell_layout.json`, `shell_materials.json`, `SM_DKH_*`,
  `Scripts/dojo/hall`, `Scripts/dojo/roof`, DojoLab.
- **Either chat may edit either side when the owner asks.** The editing chat takes the `ArmoryHall` lock (section 5),
  also the other side's asset lock for that edit only (`ArmoryKit` for `Scripts/armory` / `Exports/ArmoryKit`;
  `DojoHall` for the hall builder), and writes in its change line what it changed on the other side and that the
  owner asked for it.
- Without the owner's request a chat never edits the other side's files, locks or Unreal project. The dojo chat
  never opens ArmoryLab, and the armory chat never opens DojoLab.

## 5. The lock

- Asset name `ArmoryHall` (file `WorkFiles/locks/armoryhall.json`):
  `py -3 -B Scripts/pipeline/lock.py claim ArmoryHall --agent claude`, then
  `py -3 -B Scripts/pipeline/lock.py release ArmoryHall --agent claude`.
- Hold it from the first write to this folder to the manifest bump (and the `--record-sync`). Release it in the same
  session. `regen_interior.py --write`, `make_shell_materials.py --write` and `bump_manifest.py` refuse without it.
- If it is held by another chat, wait. Never `--force` it unless the owner says so.

## 6. Sky, sun and time stay per level

- **Travels with the interior:** every light in `lights_design.json` `lights` (case, glow, panel, down, alcove, rack,
  lantern, banner, sill, wash). Each project applies its own `level_scale` and may switch shadows off per level for
  performance; it records that in its own notes, not in the design.
- **Travels with the shell:** the meshes and materials of section 11 and the lights in `hall_shell_layout.json`
  `lights` (the window backers; their intensity is per level: DojoLab off, ArmoryLab default off).
- **Stays per level** (never synced): sun, moon, sky (DojoLab: the sunset Ultra Dynamic Sky; ArmoryLab: its own
  presets), sky light, fog, exposure, post-process, emissive level scales, and the level-only lights listed in
  `lights_design.json` `level_only_not_travelling` with a `level` key (DojoLab: `DJ_ThresholdFill`). The armory's
  `Sun_WindowFill` also stays per level.

## 7. After an edit (the general rule; sections 12 and 13 are the step lists)

1. Export only through `Scripts/pipeline` (`qa_check` 0 hard fails; UCX keyed to the render-mesh node name).
2. Regenerate the layout json(s) with the tools. Never hand-edit numbers that a script derives.
3. `check_sync.py --side <yours>` (exit 0 or 2).
4. `bump_manifest.py --chat <you> --summary "..."`: it recomputes every sha256, bumps the revision by 1 and appends
   the change line `{rev, date, chat, summary, files}`. Never edit or remove an older line.
5. If `interface.json` changed (owner only), add `--interface-changed`. The other chat must re-check its side against
   the new envelope before its next build.
6. Sync your project (section 3), `--record-sync`, release the lock, then tell the owner:
   "armory_hall revision N is waiting for the <other> chat".

## 8. Checks (`tools/check_sync.py`; the sync scripts repeat the placement gates in Unreal)

- **files**: every shared file's sha256 equals `manifest.json` `shared_files` (an edit without a bump fails).
- **sha**: every FBX, item FBX, texture PNG and material / texture `.uasset` equals `manifest.json`; DojoLab's byte
  copies of the armory's packages on the dojo side (a different copy = sync needed).
- **pieces**: every instance's piece is listed and its FBX exists; ids unique; no retired id reused.
- **envelope**, measured on the exported FBX bytes (render meshes, LODs and UCX hulls): every interior vertex and
  design light inside `interface.json` `envelope.with_walls` (tolerance 0.012 m); every placed shell vertex outside
  it except inside `envelope.shell_intrusions`; each interior instance's layout bbox within 2 cm of its FBX.
- **names**: no listed mesh name has disappeared unless retired (section 9).
- **lights**: shadowed local lights within the level's budget (ArmoryLab 12; DojoLab `dj_armory_look.SHADOW_BUDGET`).
- **fresh**: the interior jsons equal what `regen_interior.py` builds from the armory's data now; on the dojo side
  `shell_materials.json` equals what `make_shell_materials.py` builds.
- **masters** (rev 4): the shell masters' live graph code equals `shell_masters.json` and `manifest.json`
  `shell_master_graph` (section 15). Dojo side: exit 3 (snapshot + bump owed); armory side: exit 1.
- **hall_variant** (rev 4, armory side, once ArmoryLab has synced): section 3.2 step 4. A miss = exit 2.
- **revision**: your project's synced revision against `sync_needed_rev` (section 3.4).
- **Unreal, per sync**: placement / bounds gates (1 cm), walk routes and CONTROLs in `interface.json` `gameplay`
  (DojoLab: in the 1v1 setup).

## 9. Mesh name stability

- A mesh name in use is never renamed or deleted.
- A rebuilt piece keeps its name only if its pivot, facing and interface footprint are unchanged (bbox within 2 cm).
  Otherwise it gets a new name, and the old one is retired: `bump_manifest.py --retire <old name>` (only with the
  owner's agreement); it then stays under `retired` with the revision that retired it.
- Prefixes stay with their kit: `SM_AK_*` = interior; `SM_AKX_*` = the armory's own exterior, not used in the hall;
  `SM_DKH_*` = the hall shell, with `SM_DKH_Rear*` for the extension.

## 10. Git

- This folder is plain git (JSON, Markdown, the tools). FBX and textures stay in `Exports/` (LFS).
- Commit the shared folder together with the exports and scripts of the same change, in one commit, and only when the
  owner allows commits.
- If the manifest moved under you (another chat bumped since you started), the later writer re-syncs, re-runs its
  tool (`regen_interior.py` or `make_shell_materials.py`) on the newer files, keeps both change lines and bumps again.

## 11. ArmoryLab shows the extended hall

ArmoryLab places the **full hall shell** around its interior, imported from `Exports/DojoKit/Hall`, and keeps its own
exterior only as a hidden reference. `tools/ue_armorylab_shell.py` does all of it (section 3); this is what it does.

1. **Instances**: from `hall_shell_layout.json`, every `instances_existing` entry whose `status` starts with `kept`
   plus every `instances_new` entry whose `status` does not start with `removed` (161 at revision 3; a `replaced`
   existing entry is not placed: its replacement is in `instances_new`). Position: ArmoryLab world = hall-local +
   (6, 0, 0), hall-local = `loc_world_m` − (22, 24, 0.5); yaw = −`rot_z_deg`. Label `<piece>__<shell id>`, tag
   `AH_Shell`, folder `ArmoryHall/Shell`, collision per `interface.json` `gameplay.collision_classes`.
2. **FBX** (32 pieces, `Exports/DojoKit/Hall/<name>.fbx`, sha256 in `manifest.json` `fbx`; a `.sockets.json` sidecar
   where marked *): SM_DKH_Bay_ClereFrieze*, SM_DKH_Bay_ClerePlaster*, SM_DKH_Bay_Door, SM_DKH_Bay_DoorOpen,
   SM_DKH_Bay_Lattice, SM_DKH_Bay_Plaster*, SM_DKH_Bay_Transom, SM_DKH_DoorLeaf_Parked*, SM_DKH_Downpipe*,
   SM_DKH_EaveLanding*, SM_DKH_Frame_Open, SM_DKH_Rear_Bay1_ClerePlaster, SM_DKH_Rear_Bay1_Plaster*,
   SM_DKH_Rear_Bay1_Transom, SM_DKH_Rear_Bay_ClerePlaster*, SM_DKH_Rear_Frame, SM_DKH_Rear_Roof,
   SM_DKH_Rear_RoofGable, SM_DKH_Rear_RoofRidge, SM_DKH_Rear_WindowBacker, SM_DKH_RoofChidori_E,
   SM_DKH_RoofChidori_W, SM_DKH_RoofLower_Front, SM_DKH_RoofLower_SideE, SM_DKH_RoofLower_SideW,
   SM_DKH_RoofUpper_BackValley, SM_DKH_RoofUpper_End, SM_DKH_RoofUpper_Front, SM_DKH_RoofUpper_Ridge,
   SM_DKH_StepBand*, SM_DKH_Veranda, SM_DKH_VerandaFrame. Import recipe: `shell_materials.json` `import_recipe`
   (legacy FBX, Import Mesh LODs ON, one convex hull per UCX, imported normals, vertex colours replaced, Nanite per
   piece with the fallback at full detail) into `/Game/DojoKit/Hall/Meshes`.
3. **Textures** (31 PNG, `Exports/DojoKit/Materials/Textures/<name>.png`, sha256 in `manifest.json`
   `shell_textures`): T_DJ_{Granite, GraniteRubble, Iron, PlasterCream, RoofTile, ShojiPaper, TimberAged,
   TimberAgedEnd, TimberDark, TimberDarkEnd}_{BC, ORM, N} and T_DJ_WearMask_M. BC sRGB TC_Default; ORM and _M
   linear TC_Masks; N linear TC_Normalmap, DirectX (no green flip). Into `/Game/DojoKit/Materials/Textures`.
4. **Materials** (the recipe lives in `shell_materials.json`): two masters, `M_DJ_Lib_Opaque` and `M_DJ_Lib_Emissive`
   in `/Game/DojoKit/Materials/Masters`, built from the dojo's graph code (`Scripts/dojo/unreal/dj_sc_materials.py`
   `build_lib_opaque` / `build_lib_emissive`; the code and parameters they run are revisioned in `shell_masters.json`,
   section 15); ten instances in `/Game/DojoKit/Materials/Materials/Library`
   (M_DJ_Granite, GraniteRubble, Iron, PlasterCream, RoofTile, ShojiPaper, TimberAged, TimberAgedEnd, TimberDark,
   TimberDarkEnd) with the exact scalars, linear vectors, static switches and textures listed; each mesh slot takes
   the instance with the slot's name. Emission is per level: `level_values.EmissiveIntensity` gives DojoLab's value
   and the ArmoryLab parity scale (x 14.72 for the same look at ArmoryLab's exposure; the tool's default). Interior
   paper: the parked leaves' and backers' `M_DJ_ShojiPaper` gets an unlit child (as DojoLab's per-actor overrides).
5. **The armory's own exterior is hidden and kept**: every instance in `interior_layout.json`
   `not_used_in_the_hall.instances` (all `SM_AKX_*`, the entrance wall `SM_AK_Entrance_12`, `SM_AK_Threshold_4`,
   `SM_AK_GenkanFloor`, `SM_AK_StepBeam`, `SM_AK_Floor_Plank_EntryBand`, the door leaves, the jamb posts, the wall
   sconces and the two south corner posts) stays in L_Armory with its mesh component invisible, no collision,
   hidden in game, tag `AH_ExteriorHidden`, folder `ArmoryHall_Reference/ArmoryExterior`. `ak_level.py` re-creates
   them visible: the tool runs after it every time, as the last Unreal step (section 3.2).
6. **The interior is the hall variant**, exactly as `interior_layout.json`: the eight floor tiles `AKI_9001..9008`
   fill the genkan + entry band (placed by the tool, tag `AH_Shell`), and the entry lanterns, the entry mat and their
   lights stand +0.12 higher (on the floor, not the hidden genkan).
7. **Stays ArmoryLab's own**: sky, sun / moon, time, fog, exposure, post-process; the window-backer rects (default off,
   `AH_BACKER_CD`); a flat courtyard stand-in at hall-local z −0.50 (`AH_CourtyardGround_StandIn`, ArmoryLab only,
   because the armory's garden ground is hidden; `AH_GROUND=0` leaves it out).
8. The armory chat never edits the shell files, `Exports/DojoKit` or `Scripts/dojo`; a shell change it needs goes to
   the owner (section 4).

## 12. Interior change flow (the armory chat)

1. `check_sync.py --side armory` (section 0).
2. `py -3 -B Scripts/pipeline/lock.py claim ArmoryHall --agent claude` (and `ArmoryKit` as usual for the kit).
3. Edit `Scripts/armory` / the armory layout as usual; build; export through `Scripts/pipeline`; run your own
   ArmoryLab routine to the end (section 3.2 step 2: `bash Scripts/armory/unreal/run_armory_unreal.sh`, verify and the
   steps after it included, all passing on the standalone armory) so `WorkFiles/armory/build/{layout,qa_report,
   export_report}.json` and `unreal/{import,materials,level}.json` are current. No `ue_armorylab_shell.py` yet.
4. `py -3 -B WorkFiles/shared/armory_hall/tools/regen_interior.py` (dry run): read the diff (ids added / retired /
   moved, envelope). An envelope violation stops here: change the layout or ask the owner for an interface change.
5. `py -3 -B WorkFiles/shared/armory_hall/tools/regen_interior.py --write --chat armory`.
6. `check_sync.py --side armory`: exit 2 expected (ArmoryLab not yet at the new revision); 1 or 3 = fix first.
7. `py -3 -B WorkFiles/shared/armory_hall/tools/bump_manifest.py --chat armory --summary "<what and why>"`
   (`--retire <name>` only for a name the owner agreed to retire).
8. Sync ArmoryLab: section 3.2 steps 3-4 (step 2 already ran in step 3 above, and no `ak_*` Unreal step ran since):
   `tools/ue_armorylab_shell.py` as the last Unreal step, then `check_sync.py --side armory` must exit 0 (the
   hall-variant check); `bump_manifest.py --record-sync ArmoryLab`; release the lock; write `armory_hall synced rev N`
   in `WorkFiles/armory/build/BUILD_NOTES.md`.
9. Tell the owner: "armory_hall revision N (interior) is waiting for the dojo chat".

## 13. Shell change flow (the dojo chat)

1. `check_sync.py --side dojo` (section 0).
2. Claim `ArmoryHall` (and `DojoHall` for the hall builder).
3. Edit `Scripts/dojo/hall` / `Scripts/dojo/roof`; build; export through `Scripts/pipeline`; update
   `hall_shell_layout.json` from the build output with the round's update script (pattern:
   `Scripts/dojo/hall/update_shared_hall_armory_fix.py`); re-measure the doors if they changed.
4. `py -3 -B Scripts/dojo/hall/make_shell_materials.py --write` (any piece, slot, material or texture change), and
   `py -3 -B WorkFiles/shared/armory_hall/tools/master_snapshot.py --write` when the shell masters' graph changed
   (section 15; `check_sync.py --side dojo` exit 3 naming `masters` tells you).
5. `check_sync.py --side dojo` (exit 2 expected).
6. `bump_manifest.py --chat dojo --summary "<what and why>"`.
7. Sync DojoLab (`sc_import`, `sc_materials`, `sc_level`, `run_armory_sync.sh`, `sc_verify`); `check_sync.py --side
   dojo` exit 0; `bump_manifest.py --record-sync DojoLab`; release; `armory_hall synced rev N` in
   `WorkFiles/dojo/build/BUILD_NOTES.md`.
8. Tell the owner: "armory_hall revision N (shell) is waiting for the armory chat" (ArmoryLab then re-runs section
   3.2).

## 14. First-time setup for ArmoryLab (the armory chat, once)

1. Read sections 0-6, 11, 15 and this one. Run `check_sync.py --side armory`: exit 2 expected (ArmoryLab has no
   synced revision yet).
2. Make sure no Unreal editor has ArmoryLab open and no other commandlet runs. Back up
   `ArmoryLab/Content/Armory/Maps/L_Armory.umap`.
3. Section 3.2 step 2: `bash Scripts/armory/unreal/run_armory_unreal.sh` with its full default list, every gate passing
   on the standalone armory exactly as today (verify, character, walk, capture, fptest, stats included).
4. Section 3.2 step 3: `tools/ue_armorylab_shell.py`, the last Unreal step. Its
   `WorkFiles/armory/build/unreal/armory_hall_sync/shell.json`: `passed` true, `shell_placed` 161,
   `bounds_gate.max_bounds_err_cm` <= 1, `exterior_hidden.found` = `want` (165), `hall_variant.substitution_tiles` 8,
   `hall_variant.lifted` 5, `lifted_missing` empty.
5. Section 3.2 step 4: `check_sync.py --side armory` exit 0 (the hall-variant check reads that `shell.json`).
6. Look in the editor (no `ak_*` Unreal step after step 4): your interior cameras (C1_EntryReveal now stands under the
   hall's lower roof: use an interior camera), and one from the courtyard toward the hall. Sky / sun / exposure are
   yours; set the backers and the shoji emission per level if you want (section 11 items 4 and 7).
7. Section 3.3: claim `ArmoryHall`; `bump_manifest.py --record-sync ArmoryLab`; release; write `armory_hall synced rev
   N` in `WorkFiles/armory/build/BUILD_NOTES.md`. From now on every ArmoryLab sync is section 3.2 (the tool last).

## 15. The shell master graph (rev 4)

- ArmoryLab builds the two shell masters (`M_DJ_Lib_Opaque`, `M_DJ_Lib_Emissive`) by executing the dojo's live
  `Scripts/dojo/unreal/dj_sc_materials.py` (section 11 item 4). `shell_masters.json` is the revisioned record of
  exactly what those two graphs run: the call graph from their `MASTERS` entries (the builders, `get_or_create`, every
  module function / constant / `G` graph method they reach, the `dj_sc_common.py` members they reach) as source lines
  with comments, docstrings and blank lines removed, plus the `layout_showcase.json` values they read (the sampler
  default textures' package paths), and its `graph_sha256`. `manifest.json` hashes the file (`shared_files`) and
  records `shell_master_graph.graph_sha256` at every bump.
- **Dojo chat**, after any change to `dj_sc_materials.py`, `dj_sc_common.py` or `layout_showcase.json`:
  `check_sync.py --side dojo`. Exit 3 naming `masters` = the shell masters' graph changed: claim `ArmoryHall`,
  `py -3 -B WorkFiles/shared/armory_hall/tools/master_snapshot.py --write`, `check_sync.py --side dojo` (2 expected),
  `bump_manifest.py --chat dojo --summary "..."`, then sync DojoLab (`sc_materials`, `run_armory_sync.sh`) and record
  (section 13 steps 4-8). The bump moves `sync_needed_rev` of both projects, so ArmoryLab is behind (exit 2) until the
  armory chat re-runs section 3.2.
- A change to the dojo's other masters (`build_ground`, the kit and prop masters ...), to comments or to docstrings
  leaves the snapshot unchanged: no bump. `master_snapshot.py` without `--write` compares only (exit 0 fresh, 4
  differs).
- **Armory side**: a live graph that differs from the snapshot is exit 1 (the dojo chat owes the snapshot and the bump):
  never run `ue_armorylab_shell.py` then; tell the owner.
- The tool still executes the live dojo file (unchanged at rev 4, the path proven in test mode); the snapshot is the
  revisioned record and the gate, not the executed code.
