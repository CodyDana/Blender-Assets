# Sniper Rifle SR-01: SK_SR01, SM_SR01, SM_SR01_Mag, SM_Att_Scope_LongRange

A bolt-action precision rifle in an olive chassis with an adjustable cheek riser, a folding and extending bipod, a
detachable box magazine and a separate long-range scope. It is a rigged skeletal mesh whose bolt, trigger, safety,
magazine release, magazine, cheek riser and bipod move. A static twin is included for pickups and world props. The
magazine and the scope are separate static meshes. The gun carries generic markings only (S / F at the safety); no
names, serials or logos.

> **Status (W4, 2026-10-13): pre-Unreal draft.** Every file here passed the Blender-side gates on these exact bytes
> (fresh-process re-import: triangles, bones, sockets, clips, hulls, magazine fit). The Unreal 5.8 import has not been
> verified yet (W5); import settings below are the pipeline's measured UE 5.8 rules, not yet checked on this asset.
> `MATERIALS_README.md` and the pack recolour constants come with the pack materials (W6).

## What is in this folder

| File | What it is |
|---|---|
| `SK_SR01.fbx` + `SK_SR01_LOD1..3.fbx` | The rifle without the scope or the magazine, skeletal, LOD0-3. Skeleton: `root` + 13 rigid bones (body, bolt, trigger, safety, mag_release, magazine, cheek_riser, bipod hub / legs / extensions, muzzle_device); one influence per vertex |
| `A_SR01_*.fbx` | 8 clips: Fire (60 fps), BoltCycle, Reload, ReloadEmpty (starts bolt open), Selector, BipodDeploy (ends deployed), BipodStow (starts deployed), CheekRiser |
| `SK_SR01.skeletal.json` | Sidecar: bones, 20 sockets, LOD screen sizes, bounds extension, notifies, physics, materials, mass |
| `Physics/` | The physics proxy (an envelope box with the posed bounds) |
| `SM_SR01.fbx` (+ `.sockets.json`) | Static twin (bipod folded) with the magazine merged in, LOD0-3, 10 convex hulls `UCX_SM_SR01_LOD0_00..09` |
| `SM_SR01_Mag.fbx` (+ `.sockets.json`) | The removable magazine, LOD0-3, 1 hull, 5 sockets; at every LOD the same mesh as the twin's merged magazine |
| `SM_Att_Scope_LongRange.fbx` (+ `.sockets.json`) | The scope with its rings, 3 LODs, 3 hulls, 5 sockets; its origin is the Mount (attach to the gun's rail socket) |
| `Textures/` | `T_SR01_Metal_*` (2048), `T_SR01_Chassis_*` (4096), `T_SR01_Mag_*` (1024), `T_Att_Scope_LongRange_Scope_Body_*` (2048), `_Scope_Lens_*` (512): BC, ORM, N, Masks per set; `Recolour/` the OD Detail16 maps |

Exact triangle counts, LOD screen sizes and socket transforms are in the sidecars and in
`WorkFiles/guns/sniper/gates/` (`game.json`, `game_lod_sizes.json`, `rig_export.json`, `mag.json`, `scope_export.json`).

## Import rules (pipeline 1.2.0, measured on UE 5.8)

- Textures: **BaseColor sRGB; ORM, Masks and Normal linear**; the normal maps are **DirectX** (green down). The PNGs
  carry no colour-space tags: set the flags on import. All maps are power of two; keep full mip chains.
- Meshes: Import Mesh LODs on; Import Normals. LOD screen sizes from the sidecar (the LOD-pop switch distances on the
  engine bounds including the bipod / bolt bounds extension).
- Collision: the `UCX_<node>_LOD0_NN` hulls import as simple collision of their LOD0.
- Sockets: apply the `.sockets.json` sidecars with `Scripts/pipeline/ue_import_sockets.py` (FBX sockets arrive at
  scale 100; the sidecar is the authority).
- Clips: set the bone compression to `DefaultRecorderBoneCompression` (ACL moves rigid parts by about 1 mm); add the
  notifies from the sidecar (the FBX files carry none).
- The magazine inserts straight along the Mag socket's +Z from `MagInsertStart` (67.8 mm); the catch is spring-loaded
  (the magazine cams it back and it snaps into the notch).
