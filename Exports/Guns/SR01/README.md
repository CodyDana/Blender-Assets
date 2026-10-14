# Sniper Rifle SR-01: SK_SR01, SM_SR01, SM_SR01_Mag, SM_Att_Scope_LongRange

A bolt-action precision rifle in an olive chassis with an adjustable cheek riser, a folding and extending bipod, a
detachable box magazine and a separate long-range scope. It is a rigged skeletal mesh whose bolt, trigger, safety,
magazine release, magazine, cheek riser and bipod move. A static twin is included for pickups and world props. The
magazine and the scope are separate static meshes. The gun carries generic markings only (S / F at the safety); no
names, serials or logos.

> **Status (W5, 2026-10-14): verified in Unreal Engine 5.8.3.** These exact bytes (sha256 recorded before and after
> in `WorkFiles/guns/sniper/UnrealCheck/SHA256_at_start.json` / `_at_end.json`) were imported and checked in fresh
> Unreal processes: 37 of 37 gates pass (`WorkFiles/guns/sniper/UnrealCheck/verification_summary.json`). The hand fit on
> a player MetaHuman (U11) was not run: there is no player MetaHuman in the verification project.
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

## Measured in Unreal 5.8.3 (W5, run `/Game/GunCheck/SR01_1014b`)

- Import: the legacy FBX importer with the settings above. Triangles per LOD are identical in Blender, the FBX and
  Unreal: SK_SR01 40,518 / 18,202 / 6,028 / 2,490; SM_SR01 41,396 / 18,596 / 6,178 / 2,552; SM_SR01_Mag
  878 / 394 / 150 / 62; the scope 9,938 / 4,464 / 1,454. LOD screen sizes match the sidecars: SK 1 / 0.273 / 0.0717 /
  0.0360, SM 1 / 0.25 / 0.0656 / 0.033, Mag 1 / 0.0345 / 0.00905 / 0.00455. Nanite off.
- Textures: BaseColor sRGB `TC_Default`; ORM and Masks linear `TC_Masks`; Normal `TC_Normalmap` with flip green OFF
  (DirectX), group `WeaponNormalMap`; Detail16 builds `PF_G16`. Full mip chains (4096 maps: 13 mips). With streaming on,
  the Metal and Chassis BC / N are resident at the top mip both at the hip and at ADS.
- Lightmap: index 1, Generate Lightmap UVs OFF on every LOD; the authored UV1 has 0 overlapping texels at 64 and 128 px
  as Unreal stores it (UV1 is snapped to the half-float grid at build time, so the stored UVs match the shipped ones).
- Collision: 10 hulls on SM_SR01, 1 on the magazine, 3 on the scope, all 32 vertices or fewer. Every LOD0 surface
  sample lies inside them.
- Sockets: 20 on SK_SR01 (on their bones), 20 on SM_SR01, 5 on the magazine, 5 on the scope; all within 0.001 cm /
  0.001 deg of the sidecars after `ue_import_sockets.py`.
- Scope: `SM_Att_Scope_LongRange` attached by its Mount at `Rail_Top` (+2 slots, +20.02 mm) lands where Blender
  puts it (error 0.001 cm or less). Sight is 57.6 mm above the bore and parallel to it (no zero built in: at 10 m the bore
  sits 5.76 cm under the cross).
- Clips: 8 clips with the sidecar frame counts; with `DefaultRecorderBoneCompression`, the runtime poses match the
  authored clips (0.0 mm on every rigid part). BipodDeploy ends / BipodStow starts with the legs at +90 deg on the
  12 deg splayed pins and 38 mm of extension. Bounds (+ the sidecar extension) hold every vertex at every frame of
  every clip.
- Skeleton: the SR01 skeleton is set compatible with `SK_AR01_Skeleton`. One ABP authored on the AR-01 skeleton drives
  the SR-01's bolt, trigger, selector and release. Nodes on the sniper-only bones (cheek riser, bipod) compile with a
  "bone not found" warning on the AR-01 skeleton and are ignored there.
- Magazine: SnapToTarget on `Mag` composes exactly. Seated fit: 0 intersecting triangles at LOD0-1. On the reload
  clips, only the catch nose touches the magazine (frame 2, while the paddle releases), 0.09 mm deep: within the
  Blender rule.
- Physics: `PHYS_SR01` = one body on `body`, 7 boxes + 1 capsule colliding plus a no-collision, no-mass bounds box,
  5.9 kg. Dropped 1 m in a ticking game world, SM_SR01 (level and rolled), the magazine and SK_SR01 come to rest
  without tunnelling.
- Asset warnings: 0 in every import / read-back / render / game log.
