<!-- Draft generated 2026-10-14 by the Batch API from the shipped docs; review before use. -->

# Fab Listing Draft: Sniper Rifle SR-01 (`SR01`)

## 1. Title

**Bolt-Action Sniper Rifle SR-01 with Bipod** (41 characters)

Alternatives:
- Sniper Rifle SR-01: Rigged and Animated
- Rigged Bolt-Action Rifle with Scope
- SR-01 Sniper Rifle, Bipod and Scope

## 2. Short description

A rigged, animated bolt-action sniper rifle with a folding, extending, canting bipod, a detachable magazine and a separate long-range scope, with LODs.

## 3. Long description

The SR-01 is a bolt-action sniper rifle built for Unreal Engine 5.8. It has an olive-drab painted chassis, an adjustable cheek riser, a detachable 10-round box magazine and a separate long-range scope that mounts on the rail.

The rifle is a rigged skeletal mesh with 13 rigid bones plus a root. These parts move:
- the bolt, which turns and slides;
- the trigger and the safety;
- the magazine release and the magazine;
- the cheek riser;
- the two bipod legs and their extensions.

Eight weapon-side clips come with it: fire, bolt cycle, reload, empty reload, safety, bipod deploy, bipod stow and cheek riser.

**The bipod:**
- The legs work independently and lean 12 degrees outward when deployed.
- They extend from 0 to 76 mm in five detents.
- The bipod cants up to ±15 degrees.
- Foot sockets and a table of ground heights help you place the rifle prone.

**Also included:**
- A static twin for pickups and world props, with the bipod folded and the magazine merged in.
- The magazine as its own static mesh, which snaps to the `Mag` socket.
- The scope as its own static mesh, with `Sight` and `EyePoint` aim sockets.
- Custom convex collision on every static mesh.
- A physics setup for the skeletal mesh.

Every mesh has LODs. The rifle uses PBR texture sets at 1K to 4K with DirectX normals. A Masks texture marks the painted chassis area, so you can recolour the paint in your own material.

The gun has generic markings only: S / F at the safety, and no names, serials or logos.

**Not included:** characters, first-person arms, hand animations, an animation Blueprint, gameplay code, audio, VFX and a scope render-target view. The lenses are opaque.

## 4. Features

- A rigged skeletal rifle with 13 rigid bones plus a root and one influence per vertex.
- 8 weapon clips. The bolt action is chained separately (Fire, then BoltCycle).
- A bipod with independent legs and detents at 0 and 90 degrees, a 12-degree splay, 0-76 mm extension in 19 mm detents, and ±15 degrees of cant.
- A detachable 10-round magazine with a straight reload path and a spring-loaded release catch.
- A separate long-range scope that mounts at a documented rail slot.
- A static twin for world props and pickups.
- 20 sockets on the rifle: hand targets, muzzle, shell eject, rail, sling, shoulder, bipod feet and more.
- Custom convex collision and a physics body setup.
- LOD0-3 on the rifle and magazine, and LOD0-2 on the scope.
- A notify frame table for fire, bolt, magazine and bipod events.
- First-person and third-person component setup documented for UE 5.8 First Person rendering.

## 5. Technical details

**Meshes and LOD triangle counts**
- `SK_SR01` (skeletal, no scope or magazine): 40,518 / 18,202 / 6,028 / 2,490. LOD screen sizes are 1.0 / 0.27301 / 0.07165 / 0.03604.
- `SM_SR01` (static twin, bipod folded, magazine merged): 41,396 / 18,596 / 6,178 / 2,552. Screen sizes are 1.0 / 0.25 / 0.06561 / 0.033.
- `SM_SR01_Mag`: 878 / 394 / 150 / 62. Screen sizes are 1.0 / 0.03448 / 0.00905 / 0.00455.
- `SM_Att_Scope_LongRange` (scope with rings): 9,938 / 4,464 / 1,454. Screen sizes are 1.0 / 0.09516 / 0.02497.
- The held set at LOD0 totals 51,334 triangles (gun, magazine and scope).
- Nanite is off on every mesh.
- Overall length is 1,100 mm.

**Texture sets and sizes**

Each set has BC, ORM (R = AO, G = roughness, B = metallic) and N maps, plus a Masks map at half size.

| Set | Size |
|---|---|
| `T_SR01_Metal_*` | 2048 |
| `T_SR01_Chassis_*` | 4096 |
| `T_SR01_Mag_*` | 1024 |
| `T_Att_Scope_LongRange_Scope_Body_*` | 2048 |
| `T_Att_Scope_LongRange_Scope_Lens_*` | 512 |

- Normal maps follow the DirectX convention and have a 16-bit source.
- All maps are square powers of two with full mip chains.
- `Recolour/T_SR01_Chassis_Detail16` is 2048, Grayscale/G16.
- The Masks channels are: R = edge wear, G = handling, B = cavity, A = painted area. A is 1 only on the OD paint.

**Materials and recolour**
- The material slots are `M_SR01_Metal`, `M_SR01_Chassis`, `M_SR01_Mag`, `M_Att_Scope_Body` and `M_Att_Scope_Lens`.
- The maps work with any standard PBR material.
- To repaint the chassis, use Masks A as the lerp mask in your own material.
- The UV0 tiles sit in separate U tiles on the twin and the scope, so keep Wrap addressing.
- UV1 is an authored lightmap UV at index 1. Generate Lightmap UVs is off.
- The in-hand setup costs 10 draw calls across the FP and TP components.

**Rig**
- Skeleton: `SK_SR01_Skeleton`.
- Bones: `root`, `body`, `bolt`, `trigger`, `selector`, `mag_release`, `magazine`, `muzzle_device`, `cheek_riser`, `bipod`, `bipod_leg_l`, `bipod_leg_l_ext`, `bipod_leg_r`, `bipod_leg_r_ext`.

Bone ranges:

| Bone | Range |
|---|---|
| `bolt` | Rotates 0 to -60 degrees about X, then slides 88 mm back |
| `trigger` | 0 to +6 degrees |
| `selector` | Fire at 0, Safe at -12 degrees |
| `mag_release` | 0 to -4.5 degrees |
| `cheek_riser` | -12.9 to +12.0 mm |
| `bipod` | Cant of ±15 degrees |
| Bipod legs | 0 to 90 degrees |
| Leg extensions | 0 to 76 mm |

**Animations**

| Clip | Frame rate | Frames |
|---|---|---|
| `A_SR01_Fire` | 60 fps | 8 |
| `A_SR01_BoltCycle` | 30 fps | 30 |
| `A_SR01_Reload` | 30 fps | 60 |
| `A_SR01_ReloadEmpty` | 30 fps | 90 |
| `A_SR01_Selector` | 30 fps | 20 |
| `A_SR01_BipodDeploy` | 30 fps | 36 |
| `A_SR01_BipodStow` | 30 fps | 36 |
| `A_SR01_CheekRiser` | 30 fps | 24 |

- Use bone compression `/Engine/Animation/DefaultRecorderBoneCompression` for these clips.
- Notify frames are documented separately, because the FBX files carry no notifies.

**Sockets**
- `SK_SR01` and `SM_SR01` each have 20 sockets: `Grip`, `SupportHand`, `SupportHandBipod`, `Trigger`, `Selector`, `MagRelease`, `BoltHandle`, `Muzzle`, `MuzzleSeat`, `ShellEject`, `Mag`, `MagInsertStart`, `Rail_Top`, `SlingFront`, `SlingRear`, `Shoulder`, `CenterOfMass`, `Holster`, `BipodFoot_L` and `BipodFoot_R`.
- The magazine has 5 sockets: `Mag`, `Feed`, `Base`, `HandReload` and `CenterOfMass`.
- The scope has 5 sockets, including `Sight`, `EyePoint`, `Lens_Front` and `CenterOfMass`.
- For the static meshes, the sockets ship as `.sockets.json` sidecars, because UE 5.8 drops FBX sockets on files with LOD groups.

**Collision**
- `SM_SR01` has 10 convex hulls (`UCX_SM_SR01_LOD0_00..09`), the magazine has 1 and the scope has 3. Every hull has 32 vertices or fewer.
- Import with *One Convex Hull per UCX* on and *Auto Generate Collision* off.

**Physics**
- `PHYS_SR01` is one body on `body` with a mass of 5.9 kg.
- It is made of 7 boxes and 1 capsule, plus a bounds box with no collision and no mass.
- It is rebuilt from `Physics/SK_SR01_PhysicsProxy.fbx` and the sidecar shapes.
- Game masses: the magazine is 0.20 kg empty and 0.45 kg loaded, and the scope is 1.15 kg.

**Magazine and attachments**
- The magazine snaps to `Mag` with a zero relative transform.
- The reload path runs straight from `MagInsertStart`, 67.8 mm below `Mag`.
- The scope's `Mount` goes on `Rail_Top` plus 2 slots, which is X +20.02 mm.
- `Sight` is 57.6 mm above the bore and parallel to it.
- No zero is built in.

**Unreal version and import**
- Verified in Unreal Engine 5.8.3 with the legacy FBX importer.
- Import settings: Import Normals on, Convert Scene on, Force Front X Axis off, Import Mesh LODs on.
- Apply the bounds extension from the sidecar: Positive (0, 8.681, 2.31) cm and Negative (0, 12.877, 18.386) cm.

**First person**
- Use FP and TP component pairs for the gun, magazine and scope.
- On each FP component, set *First Person Primitive Type* to FirstPerson and *ForcedLodModel* to 1.

**File formats**
- FBX: skeletal mesh and LODs, static meshes, clips and the physics proxy.
- Texture maps.
- JSON sidecars.
- Unreal Engine 5.8 project: *[pending, see section 7]*.

## 6. Category, tags and price

- **Category:** 3D Models > Weapons, in the Firearms category. Confirm the exact path in the uploader.
- **Tags (14):** Sniper Rifle, Bolt Action, Rifle, Firearm, Weapon, Bipod, Scope, Magazine, Rigged, Animated, Realistic, PBR, LODs, First Person.
- **Price:** Personal $19.99-$29.99, Professional $39.99-$59.99, with both tiers required.
  - Reasoning: the studies put weapon packs at $9.99-$59.99, with a 2-2.6x Professional ratio observed for weapon and prop packs.
  - A single rifle with a scope and magazine sits in the lower half of that band.

## 7. Before publishing (internal, not buyer-facing)

### IP, design and declarations

1. **Design distance from real rifles.**
   - The rifle and long-rifle sheets are near-replicas of real designs. Fab versions need original design deltas (GUN_BUILDING_STUDY §9).
   - Deltas are documented only for AR01 (rifle plan 13). The SR01 has none listed.
   - No blind reverse IP test is recorded for the SR01, where a judge must not be able to name the real rifle (FAB_PUBLISHING_STUDY 3.1).
   - Clarify the W4 blind result, "copy picked 14/14 on design" (SR01_REPORT §3, §8.6).
2. **Scope markings.** The turrets carry "generic tick and numeral markings" (MATERIALS_README). This conflicts with the "no numerals" rule in GUN_BUILDING_STUDY §9. Decide on it or remove the numerals.
3. **AI declaration.**
   - The source is "the user's AI design sheet" (SR01_REPORT §1), and the rifle was built by Claude sessions.
   - Catalogue policy P1 recommends Created with AI = Yes, with NoAI on (FAB_PUBLISHING_STUDY 3.3, 8.3). The user decides.
4. **Firearms category risk.**
   - "A full set of animations" is undefined, and reviewers may reject weapon-only clips.
   - Either ask Fab support, or plan a minimal arms set (idle, fire, reload, reload empty, equip on UE5 Manny). This is Q6 in GUN_BUILDING_STUDY §9.
5. **Remaining declarations.**
   - Confirm there are no third-party inputs (TR 4.2.5.a).
   - Keep the Mature flag off.
   - Decide whether to offer the Blender sources (`Assets/Guns/SR01.blend`, `Att_Scope_LongRange.blend`).

### Art quality

6. **Close-up realism has not passed.**
   - Both judges called it fake 8/8 at W4b, at FP 35 cm, in the scope view and in a 3x crop.
   - Open geometry problems include grip slivers, jagged riser and pad edges, a forend zig-zag and a crude trigger.
   - The next round needs a different edge method.
   - Gallery media must not oversell close views (SR01_REPORT §3, §8.1; README "Good to know").
7. **Form and surface gates open.** L2, L3 and L4 are open, B9 had near-misses, and the TOP conventions need the user's call (SR01_REPORT §2, §8.2-8.3).

### Materials

8. **Pack material instances are not built.**
   - `MI_SR01_*` and `MI_Att_Scope_LongRange_*` are proposals only. Fab requires material instances where possible (TR 4.3.3).
   - Decide D1 first: `M_Fabric_Master` has no mask, so a recolour would tint 28.4% of the Chassis texels that are not paint.
   - The shipped `recolour_maps.json` is the W2 stub (MATERIALS_README; SR01_REPORT §6, §8.5).
   - Do not advertise a built-in recolour until this is done.
9. **Texture details not measured.** BC7 versus BC1 has not been measured on the SR-01, and total texture memory is not recorded (MATERIALS_README).

### Unreal project and verification

10. **No Unreal Engine project exists yet.** Build a fresh UE 5.8 `<Pack>` project with one folder under Content, then:
    - build `PHYS_SR01` in the project;
    - add the notifies;
    - apply the sidecar sockets, LOD screen sizes, bounds extension and compression;
    - make an overview map with every asset and no warnings in load or PIE;
    - make an example Blueprint using the sockets, which GUN_BUILDING_STUDY §9 says top listings ship;
    - run the migrate test with `Config/` deleted and a dependency scan.

    See FAB_PUBLISHING_STUDY R3-R4 and 4.2, and GUN_BUILDING_STUDY §9 (FP settings as README instructions only).
11. **No byte deny-scan tool for Unreal output.** `ue_deny_scan.py` does not exist yet (FAB_PUBLISHING_STUDY 4.2.6). The W6 deny scan covered the FBX and text only. Also scan this listing's text, tags and video titles.
12. **Hand fit not run.** U11 hand fit is not run, so `Grip`, `SupportHand` and `SupportHandBipod` are provisional. Owner-only hiding of the TP components is unverified (README; SR01_REPORT §4, §8.4).

### Documentation

13. **The shipped README is internal.** It mentions W-stages, judges, `WorkFiles/` paths, U11, `Scripts/pipeline/ue_import_sockets.py` (which buyers don't have) and `SK_AR01_Skeleton`, which is not in this pack.
    - Write a buyer-facing version and an English documentation page with no auto-download (TR 4.3.8; FAB_PUBLISHING_STUDY 6.5).
    - Do not claim AR-01 skeleton compatibility unless the AR-01 is bundled.

### Media

14. **Showcase images are not at Fab spec.**
    - The 15 showcase images come from `studio.py`, whose default output is 4:3 at 1600x1200, which is below Fab's floor and the wrong ratio.
    - Add the 16:9 preset (P6) and make a thumbnail.
    - An animated product needs an animation video (TR 4.1.1.a).
    - No Unreal pack frame exists (SR01_REPORT §5; FAB_PUBLISHING_STUDY 6.5).

### Repository housekeeping

15. **Housekeeping items:**
    - The branch `claude/sniper-sr01` is not merged.
    - The `ASSET_LIST.md` row has not been added.
    - The `SR01` lock is still held.
    - `studio.py` was copied from another branch (SR01_REPORT §5, §8.7, §9).

### Listing and account

16. **Listing and account items:**
    - The title is above the ideal of about 30 characters, so consider shortening it (FAB_PUBLISHING_STUDY 6.1).
    - Set both licence tiers on the .99 ladder (2.3-2.4).
    - Complete seller onboarding and decisions P2-P9 (8.3).
