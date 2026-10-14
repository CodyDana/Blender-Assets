<!-- Draft generated 2026-10-14 by the Batch API from the shipped docs; review before use. -->

# Fab Listing Draft: Compact SMG SM-01 (`SMG01`)

## 1. Title

**Main:** Compact SMG SM-01 - Rigged and Animated (39 characters)

**Alternatives:**
- Compact SMG SM-01 Game Weapon (29)
- Folding-Stock SMG - Rigged, 8 Animations (40)
- Compact Polymer SMG - Rigged Weapon (35)

*(The Fab study says titles should ideally be about 30 characters. The second alternative fits that best.)*

## 2. Short description

A rigged compact polymer SMG for UE 5.8. It has a side-folding stock, flip sights, a swappable 25-round magazine, 8 weapon animations, 4 LODs and a recolourable polymer. (166 characters)

## 3. Long description

The Compact SMG SM-01 is a polymer-framed submachine gun built as a game weapon for first- and third-person projects in Unreal Engine 5.8. It carries no names, markings or logos.

**Moving parts.** The gun is a rigged skeletal mesh with 11 moving parts:
- bolt, charging handle and trigger
- selector, with Safe, Semi and Auto detents
- magazine release and magazine
- side-folding skeleton stock
- front and rear flip sights
- muzzle device

**Animations.** Eight weapon animations cover:
- a single shot and a charge
- a reload and an empty reload
- a selector cycle
- stock fold and unfold
- a sight flip

The notify frames for shell eject, magazine out and in, and bolt release are documented for each clip.

**Static twin and magazine.** A static twin with the stock extended serves pickups and world props. It has 8 convex collision hulls. The magazine is a separate mesh that snaps to a `Mag` socket and follows a straight reload path. Twenty-one documented sockets cover grip, support hand, muzzle, sight, shell eject, rails, sling points, shoulder, holster and centre of mass. The shoulder and rear sling sockets follow the stock when it folds.

**Materials.** The materials are PBR, with a phosphated-steel set and a black polymer set. To recolour the polymer (tan, OD green, FDE or any other colour), switch off *Use Original Baked Colours* and set one Colour on the furniture and magazine instances. The moulded texture, polish and wear follow the new colour.

**First person.** The gun is set up for UE 5.8 First Person rendering. Use separate first-person and third-person components, and lock the first-person ones to LOD0.

**Documentation.** Full import, socket, physics and material documentation is included.

**Not included:** character, arms or character animations, sound, VFX and gameplay code.

*(About 240 words.)*

## 4. Features

- Rigged skeletal gun: `root` plus 11 bones, and 4 LODs that share one skeleton.
- 8 weapon animations, with documented notify frames.
- Side-folding stock that swings 180 degrees. Bounds and physics are set up so the folded gun stays inside its bounds.
- Folding front and rear sights.
- Selector with three detents. The documented per-bone blend lets the selector show the player's real fire mode.
- Removable 25-round magazine as its own mesh. It uses a straight insert path from `MagInsertStart` to `Mag`.
- Static twin for pickups and props, with 4 LODs and 8 convex hulls.
- 21 sockets on the skeletal mesh, 21 on the static twin and 5 on the magazine.
- Physics asset `PHYS_SMG01`: one 2.5 kg body that drops and rests with the stock extended or folded.
- Recolourable polymer: one Colour drives both the furniture and the magazine.
- Authored lightmap UVs (UV1) on every LOD.
- Set up for first-person rendering, with documented component settings.
- No names, markings, serials or logos anywhere.

## 5. Technical details

**Meshes and LOD triangle counts**

| Mesh | LOD0 | LOD1 | LOD2 | LOD3 |
|---|---|---|---|---|
| `SK_SMG01` (magazine not included) | 48,236 | 23,832 | 8,844 | 1,420 |
| `SM_SMG01` (static twin, stock extended, magazine merged) | 52,536 | 25,252 | 9,532 | 1,444 |
| `SM_SMG01_Mag` | 4,300 | 1,420 | 688 | 24 |

- The magazine is the same mesh as the twin's merged magazine at every LOD.
- **LOD screen sizes:**
  - `SK_SMG01`: 1.0 / 0.28612 / 0.06082 / 0.03777, giving switch distances of 2.3 / 11.0 / 17.7 m.
  - `SM_SMG01`: 1.0 / 0.25 / 0.05314 / 0.033.
  - `SM_SMG01_Mag`: 1.0 / 0.08465 / 0.01799 / 0.01117. These are derived from the gun's values so an attached magazine switches with the gun.
- **Overall length:** 625 mm with the stock extended and 383.6 mm folded.

**Texture sets**

| Set | Size | Maps |
|---|---|---|
| Metal | 2048 | BC, ORM, N, Masks |
| Furniture | 4096 | BC, ORM, N, Masks, plus a 2048 Detail16 map for recolouring |
| Mag | 1024 | BC, ORM, N, Masks, plus a 1024 Detail16 map |

- All maps are square powers of two with full mip chains.
- BC is sRGB. ORM is linear: R is ambient occlusion, G is roughness and B is metallic. N is a DirectX-convention normal map stored as 16-bit PNG.
- Masks are half size and linear: R is edge wear, G is handling, B is cavity and A is refinishable. The included materials do not use them; they are provided for your own wear layers.
- **Compression:**
  - Metal BC: BC1.
  - Furniture BC and Mag BC: **BC7**.
  - ORM and Masks: Masks.
  - N: Normalmap.
  - Detail16: Grayscale (G16).
- **Memory in Unreal with mips:** 81.0 MiB for the whole set.

**Materials and recolour**

| Slot | Instance | Master |
|---|---|---|
| `M_SMG01_Metal` | `MI_SMG01_Metal` | `M_Steel_Master` |
| `M_SMG01_Furniture` | `MI_SMG01_Furniture` | `M_Fabric_Master` |
| `M_SMG01_Mag` | `MI_SMG01_Mag` | `M_Fabric_Master` |

- Each instance has a `_Base` parent. *Reset to default* restores the shipped look.
- **Polymer recolour:** turn off *Use Original Baked Colours* on both polymer instances and set the same **Colour** on both.
  - Very light picks are capped at Lightest Colour 0.6.
  - Pure black is lifted to about sRGB 25.
- **Metal:** a single Steel Tint control. White leaves it as shipped.

**Rig**

- Skeleton `SK_SMG01_Skeleton`: `root`, `body`, `bolt`, `charging_handle`, `trigger`, `selector`, `mag_release`, `magazine`, `stock`, `sight_rear`, `sight_front` and `muzzle_device`.
- **Ranges:**
  - Bolt and charging handle: 67.9 mm travel.
  - Trigger: 0-13 degrees.
  - Selector: Safe -63.4, Semi 0 and Auto +45 degrees.
  - Release: 0 to -11 degrees.
  - Stock: 0-180 degrees.
  - Sights: 90 degrees.

**Animations**

| Clip | fps | Frames | Notifies (frame) |
|---|---|---|---|
| `A_SMG01_Fire` | 60 | 6 | Fire 1, ShellEject 3, TriggerReset 6 |
| `A_SMG01_Charge` | 30 | 22 | ChargeRear 10, BoltRelease 14 |
| `A_SMG01_Reload` | 30 | 55 | MagRelease 2, MagOut 10, MagDrop 17, MagIn 48 |
| `A_SMG01_ReloadEmpty` | 30 | 80 | As Reload, then ChargeRear 67, BoltRelease 71 |
| `A_SMG01_Selector` | 30 | 30 | (none listed) |
| `A_SMG01_StockFold` | 30 | 24 | StockUnlock 1, StockLocked 24 |
| `A_SMG01_StockUnfold` | 30 | 24 | StockUnlock 1, StockLocked 24 |
| `A_SMG01_SightFlip` | 30 | 20 | (none listed) |

- Fire, Charge and ReloadEmpty hold the selector at Auto from the first frame to the last.
- Bone compression is `DefaultRecorderBoneCompression`. The project default (ACL) moves rigid parts by about 1 mm.

**Sockets**

- 21 on the skeleton: `Grip`, `SupportHand`, `Trigger`, `Muzzle`, `MuzzleSeat`, `Sight`, `SightFront`, `Mag`, `MagInsertStart`, `ShellEject`, `ChargingHandle`, `Selector`, `MagRelease`, `Rail_Top`, `Rail_Bottom`, `Stock`, `Shoulder`, `SlingFront`, `SlingRear`, `CenterOfMass` and `Holster`.
- 21 on `SM_SMG01` and 5 on `SM_SMG01_Mag`.
- Socket locations are given in cm, with Unreal rotators, in the JSON sidecars.

**Collision**

- `SM_SMG01`: 8 convex hulls, `UCX_SM_SMG01_LOD0_00..07`.
- `SM_SMG01_Mag`: 1 hull, `UCX_SM_SMG01_Mag_LOD0_00`.
- Import with *One Convex Hull per UCX* on and *Auto Generate Collision* off.

**Physics**

- `PHYS_SMG01` has one body on `body` with a 2.5 kg mass override.
- It is made of 8 collision shapes plus one bounds-envelope box that has no collision and no mass.
- **Centre of mass:**
  - Stock extended: 47.5 / 0.7 / 83.1 mm from the `body` origin.
  - Stock folded: 100.0 / -10.0 / 83.1 mm.

**Magazine and attachments**

- The magazine snaps to `Mag` with a zero relative transform.
- The reload path is straight, 68.2 mm along the magazine's -Z axis.
- The rail sockets are `Rail_Top` and `Rail_Bottom`. The top and bottom rails use a 1913 profile.

**Unreal version and import notes**

- Measured in UE 5.8.3 on the shipped files:
  - Triangle counts match between Blender, the FBX and Unreal at every LOD.
  - Sockets land within 0.001 cm.
  - Clip motion is accurate to within 0.01 cm and 0.01 degrees.
  - Import produces 0 asset warnings.
- **Import settings:** Import Normals, Convert Scene on and Force Front X Axis off.
- **Bounds extension:** Positive (0, 24.752, 0.257) cm and Negative (0.749, 0, 0) cm.
- Unreal 5.8 drops FBX sockets from static meshes that have a LOD group, so recreate them from the sidecars.
- Lightmaps: keep *Generate Lightmap UVs* off and use the authored UV1. Higher lightmap resolutions than 128 px are not recommended.
- Nanite was not tested; the meshes were checked with Nanite off.

**First person**

- Use separate `FP_Weapon` / `TP_Weapon` and `FP_Mag` / `TP_Mag` components.
- On every first-person component, set *First Person Primitive Type* = FirstPerson and ForcedLodModel = 1.
- First-person components cast no world shadow.

**File formats**

- FBX: the meshes, LOD1-3 skeletal files, 8 clips and a physics proxy.
- PNG textures.
- JSON sidecars: `SK_SMG01.skeletal.json`, `*.sockets.json` and the recolour JSON files.
- README and MATERIALS_README.
- **[Unreal Engine 5.8 Asset Pack slot: fill in only once the project is packaged. See Before publishing.]**

**Blender note**

- Blender's importer reads a clip's first frame as the rest pose, so a clip that holds the selector re-imports at Auto. Unreal is not affected.

## 6. Category, tags, price

**Category:** 3D Models > Weapons > Firearms. This depends on the Firearms rule being met; see Before publishing, item 4.

**Tags (14):** SMG, Submachine Gun, Firearm, Gun, Weapon, Rigged, Animated, First Person, Third Person, Shooter, PBR, Realistic, Recolorable, Game Ready

**Price:** Personal $14.99-$24.99, Professional at 2x ($29.99-$49.99).

**Reasoning:** FAB_PUBLISHING_STUDY 7.1 puts entry packs at $9.99-$19.99 and observed weapon packs at $9.99-$99.99 with a 2-2.6x Professional ratio, and notes that ratings pile up on packs under $20. A single rigged gun with 8 clips sits at the low end of the weapon band.

## 7. Before publishing (internal, not buyer-facing)

### Must resolve

1. **Close-up realism is not passed.**
   - Both realism judges call every close view fake after W4b r2. Their reasons are:
     - one grey for all materials;
     - the stock head reads as a draped sheet;
     - the hinge barrel reads as a bare cylinder;
     - the ball charging knob reads as a CG primitive;
     - the rail teeth read as fins;
     - the receiver step and grooves read as decorative booleans;
     - the wear reads as speckle.
   - Only the `tp_3m` view passed.
   - The decision on a W4c round is the user's. Until then, the "Realistic" tag and any close-up hero media are a risk.
   - *Documented in:* SMG_REPORT section 4 and section 9.1.

2. **Design distance and IP.**
   - The study states the gun follows a real SMG family's construction, and its small parts follow "the real pattern" from real photos (rulings RP1-RP22).
   - GUN_BUILDING_STUDY section 9 requires original design deltas for Fab versions. A list exists for the AR-01 only; **no SMG01 delta list is documented.**
   - An IP review is needed, including the blind reverse test: a judge must not be able to name the real model.
   - *Documented in:* SMG_REPORT section 1; GUN_BUILDING_STUDY section 9; FAB_PUBLISHING_STUDY 3.1.
   - The internal docs contain real model and rail-standard names. Confirm by byte deny-scan that none reach shipped files, the listing, tags or video titles. Use "1913-profile" only. The `ue_deny_scan.py` tool does not exist yet. *Documented in:* FAB_PUBLISHING_STUDY 4.2.6.
   - Screen the product name "SM-01" for trademark clashes. *Documented in:* FAB_PUBLISHING_STUDY 3.1, "Real brands".

3. **AI declaration.**
   - The gun was matched to the user's **AI design sheet** (`smg_sheetA.webp`) and built by Claude sessions.
   - Policy P1 recommends "Created with AI = Yes". The user decides.
   - *Documented in:* SMG_REPORT header; FAB_PUBLISHING_STUDY 3.3 and 8.3.

4. **Firearms category rule.**
   - The category requires "all expected moving parts rigged and a full set of animations". Epic does not define a full set, and competitor listings ship first-person arms.
   - Weapon-only clips may be refused. Ask Fab support, or add a minimal arms set (idle, fire, reload, reload empty, equip on UE5 Manny).
   - *Documented in:* GUN_BUILDING_STUDY section 9 (Q6).

5. **No Unreal-format product exists yet.**
   - The gun was verified only in the katana / AR-01 verification project, under `/Game/GunCheck/...` and `/Game/NinjaPack`.
   - Still needed:
     - a fresh UE 5.8 `<Pack>` project;
     - shared masters (`M_Steel_Master`, `M_Fabric_Master`) copied under the pack root;
     - an overview map;
     - built lighting or Force No Precomputed Lighting;
     - a PIE-clean check;
     - the migrate test with `Config/` deleted;
     - a dependency scan.
   - *Documented in:* FAB_PUBLISHING_STUDY R3-R4, 4.2 and 5.5.
   - Merge the branch before the next pack build. *Documented in:* SMG_REPORT 9.6.

6. **Example Blueprint and ABP.**
   - GUN_BUILDING_STUDY section 9 expects example Blueprints that use the sockets. None is documented for SMG01.
   - The game-side `ABP_Gun_LongGun` still uses a constant AR-01 trigger angle. The SMG-only bones give a "bone not found" warning, and Fab requires warning-free Blueprints.
   - *Documented in:* SMG_REPORT 9.2; README "Shared long-gun Anim Blueprint"; FAB_PUBLISHING_STUDY 4.2.5.

7. **AR-01 compatibility claim.**
   - The skeleton is compatible with `SK_AR01_Skeleton`. Mention this in buyer text only if the AR-01 ships in the same product or is listed. It was left out of the draft.
   - *Documented in:* README.

8. **Animation preview is mandatory.**
   - Animated products need a video URL in the description or a 3D gallery model. No video exists yet.
   - *Documented in:* FAB_PUBLISHING_STUDY 1.1 item 8 and 5.3 (TR 4.1.1.a).

9. **Media size.**
   - The 10 showcase images come from `studio.py`, which has no Fab 16:9 preset yet and defaults to 4:3 at 1600x1200.
   - Fab needs at least 1920x1080, each image under 3 MB and under 25 MB in total. The thumbnail must be 16:9 and logo-free.
   - *Documented in:* FAB_PUBLISHING_STUDY 6.5 and P6; SMG_REPORT section 7.

10. **Buyer documentation needs cleanup.**
    - The README contains internal references: "W5 U2b", the "pack's validation project", `run_build.sh smg01_1013b`, the `gates/*.json` paths and `MH_PlayerDefault` wording.
    - MATERIALS_README says the masters are shared with "the AR-01, the katana, the fan and the throwables", which this product may not include.
    - A public English documentation page is also needed.
    - *Documented in:* FAB_PUBLISHING_STUDY 6.5 and P5.

### Untested items (keep out of buyer claims)

11. **Hand fit in Unreal (U11)** was not run. `SupportHand` and the `Grip` offset come from a Blender fit on the player MetaHuman only. *Documented in:* SMG_REPORT 5 and 9.3; README "Good to know".
12. **Other untested areas:**
    - a full in-game first-person weapon Blueprint, including owner-only visibility;
    - mobile;
    - Nanite.

    *Documented in:* README "Good to know".

### Discrepancies to resolve

13. **Physics shape count.** The README says 8 collision shapes plus an envelope box. SMG_REPORT section 6 says "8 boxes + 1 capsule". Confirm against the sidecar's `physics_bodies` before stating shape types.
14. **Static meshes in a packaged project.** The README tells FBX users to rebuild `PHYS_SMG01` by hand from a proxy and to add notifies manually. In the packaged UE project these should ship pre-built. Decide what the FBX slot documents.
15. **`/Engine` dependency.** The clips reference `/Engine/Animation/DefaultRecorderBoneCompression`, which is not the default compression. Check it against the house dependency scan; only engine defaults are allowed. *Documented in:* FAB_PUBLISHING_STUDY 4.2.4.
16. **Near-black recolour.** At near-black the Spearman score is 0.946-0.973 against a 0.98 bar. This is the pack's known 8-bit floor; accept it or document it. *Documented in:* SMG_REPORT 9.4; MATERIALS_README "Measured".
17. **Texture budget.** Decide whether to keep the 4096 furniture set (21.4 MiB BC7). *Documented in:* SMG_REPORT 9.5.
18. **UV1 overlap.** Unreal's stored UV1 overlaps by 17-22 px at 1024 px on `SM_SMG01` LOD0-2. Fab requires non-overlapping lightmap UVs; it is clean at 64 and 128 px. *Documented in:* README import notes.

### Account, listing and housekeeping

19. **Housekeeping:**
    - add the ASSET_LIST row on main;
    - release the GunLib lock if it is unused.

    *Documented in:* SMG_REPORT 9.7 and 9.8.
20. **Seller setup and listing decisions:**
    - seller onboarding, publisher name, support channels and hosting (P2-P5);
    - competitor check (R0);
    - Mature flag: keep the media bloodless and free of muzzle flash or fire;
    - third-party content: none documented, so confirm;
    - whether to offer the Blender source (`Assets/Guns/SMG01.blend`);
    - whether to add a Unity slot.

    *Documented in:* FAB_PUBLISHING_STUDY 2.1, 3.5, 4.3 and 8.3.
