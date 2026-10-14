<!-- Draft generated 2026-10-14 by the Batch API from the shipped docs; review before use. -->

# Fab Listing Draft: Assault Rifle AR-01 (`AR01`)

## 1. Title

**Rigged Assault Rifle AR-01** (26 characters)

Alternatives:
- Assault Rifle AR-01 – Rigged & Animated (38)
- Game-Ready Assault Rifle with Walnut Stock (42)
- Animated Assault Rifle, FP/TP Ready (35)

*The publishing study (6.2) suggests about 30 characters: a noun buyers search for, plus one differentiator.*

## 2. Short description

Rigged, game-ready assault rifle for UE 5.8: 4 LODs, 5 weapon clips, removable magazine, 17 sockets, physics body and recolourable walnut furniture.

## 3. Long description

**Video:** [Showcase](URL) | **Docs:** [Read me](URL) | **Support:** [Discord](URL) | email

A rigged assault rifle with a stamped steel receiver and walnut furniture, built for first-person and third-person games in Unreal Engine 5.8. It carries no names, markings or logos.

The rifle is a skeletal mesh with 8 moving bones. The bolt carrier with its charging handle runs its full travel. The trigger, selector, magazine catch, rear sight and magazine are also rigged. Five weapon-side clips drive them:
- fire
- charge
- reload
- empty reload
- selector cycle

Notify frames for shell ejection, magazine out and in, bolt release and fire-mode changes are listed so you can sync effects and sound.

A static twin with the magazine merged in is included for pickups and world props. The magazine is also a separate mesh that snaps to the `Mag` socket for reloads. Seventeen sockets cover the grip, support hand, muzzle, sight, shell ejection, sling, holster, centre of mass and the magazine path. The documented reload path is an insert, then an 8-degree rock about the front lug.

Textures are sized for close first-person views:
- a 4096 metal set
- a 2048 walnut set
- a 1024 magazine set

The walnut can be recoloured with a single colour control. Grain, wear and checkering follow the new colour. Turning one switch back on restores the shipped look. Wear sits only on edges and handling zones.

First-person setup is documented for UE 5.8 First Person rendering: separate FP and TP components, with first-person LOD0 forced.

**Not included:** characters, first-person arms or character animations, ammunition, casings, muzzle effects, audio.

If this rifle helped your project, a short review saying which part you used most helps us improve it.

## 4. Features

- Rigged skeletal rifle: `root` plus 8 bones, rigid skin.
- Five weapon clips with documented notify frames.
- Full-travel bolt carrier and charging handle. The rotating bolt is visible through the port when the carrier is back.
- Removable magazine mesh with a documented rock-in reload path. The reload clips are free of intersections on every frame (measured in Unreal).
- Static twin for pickups and props, with 7 convex collision hulls.
- 4 LODs on every mesh.
- 17 sockets on the skeletal rifle. Socket data for the static meshes is included.
- Single-body physics asset (3.1 kg mass override) for dropped weapons.
- Recolourable walnut furniture. The metal has a Steel Tint control.
- PBR maps: BaseColor, ORM, DirectX normal (16-bit), plus a Masks map for your own wear or dirt layers.
- Grip checkering baked from modelled cuts on every LOD.
- First-person and third-person setup documented for UE 5.8 First Person rendering.
- No markings, serial numbers or logos.

## 5. Technical details

**Meshes and LODs (triangles)**
- `SK_AR01` (skeletal, without magazine): LOD0 48,386 / LOD1 22,462 / LOD2 8,450 / LOD3 1,076. LOD screen sizes are 1.0 / 0.30 / 0.12 / 0.04.
- `SM_AR01` (static twin, magazine merged): 55,052 / 24,460 / 9,098 / 1,324.
- `SM_AR01_Mag` (magazine): 6,666 / 1,998 / 648 / 248. It is identical to the twin's merged magazine at every LOD.
- Nanite: off. The meshes were checked with Nanite off.

**Texture sets** (all square powers of two, full mips)

| Set | Size | Maps |
|---|---|---|
| Metal | 4096 | BC, ORM, N, Masks |
| Furniture | 2048 | BC, ORM, N, Masks, plus Detail16 at 1024 for the recolour |
| Mag | 1024 | BC, ORM, N, Masks |

Map settings:
- BC is sRGB, BC1. The exception is `T_AR01_Furniture_BC`, which uses BC7.
- ORM is linear: R ambient occlusion, G roughness, B metallic.
- N is a DirectX normal map stored as 16-bit PNG.
- Masks are linear and half size: R edge wear, G handling, B cavity, A refinishable. The materials do not use them.
- Detail16 uses Grayscale (G16) compression.

Measured texel density:
- Class A: 96.6 / 114.8 px/cm (P5 / median).
- Class B: 82.2 / 91.9 px/cm.
- Furniture: 73.9 / 95.7 px/cm.

**Materials and recolour**
- `MI_AR01_Metal` and `MI_AR01_Mag` use `M_Steel_Master` with a Steel Tint control (white means as shipped).
- `MI_AR01_Furniture` uses `M_Fabric_Master`. To recolour, turn off *Use Original Baked Colours* and pick a Colour. The default shows the baked map exactly.
- Each instance has a `_Base` parent. *Reset to default* restores the shipped look.

**Rig**
- Skeleton: `SK_AR01_Skeleton`.
- Bones: `root`, `body`, `bolt`, `trigger`, `selector`, `mag_release`, `magazine`, `sight_rear`, `muzzle_device`.

**Animations**

| Clip | Frame rate | Length |
|---|---|---|
| `A_AR01_Fire` | 60 fps | 8 frames |
| `A_AR01_Charge` | 30 fps | 22 frames |
| `A_AR01_Reload` | 30 fps | 60 frames |
| `A_AR01_ReloadEmpty` | 30 fps | 84 frames |
| `A_AR01_Selector` | 30 fps | 30 frames |

- Notifies: Fire, ShellEject, TriggerReset, ChargeRear, BoltRelease, MagRelease, MagOut, MagDrop, MagIn, SelectorAuto, SelectorSemi, SelectorSafe. Frames are listed in the docs.
- Fire, Charge, Reload and ReloadEmpty hold the selector at Auto (16°). The bind pose is Safe. Per-bone layering from `A_AR01_Selector` is documented: frame 0 Safe, frame 8 Auto, frame 18 Semi.
- Recommended bone compression: `/Engine/Animation/DefaultRecorderBoneCompression`.

**Sockets**
- `SK_AR01` has 17: `Grip`, `SupportHand`, `Trigger`, `Muzzle`, `MuzzleSeat`, `Sight`, `Mag`, `MagRockStart`, `MagInsertStart`, `ShellEject`, `ChargingHandle`, `Selector`, `MagRelease`, `Shoulder`, `SlingRear`, `CenterOfMass`, `Holster`.
- `SM_AR01` has 17 and `SM_AR01_Mag` has 5, supplied as `.sockets.json` sidecars.

**Collision**
- `SM_AR01`: 7 convex hulls, `UCX_SM_AR01_LOD0_00..06`.
- `SM_AR01_Mag`: 2 hulls, `UCX_SM_AR01_Mag_LOD0_00..01`.
- Every LOD0 surface point lies inside the hulls (measured in Unreal).
- `SK_AR01` collides through `PHYS_AR01`.

**Physics**
- `PHYS_AR01` has one body on `body` with a 3.1 kg mass override.
- Centre of mass is 163.0 / 0.1 / 74.9 mm from the `body` origin.
- It drops and rests in a game world (measured).

**Magazine and attachments**
- `SM_AR01_Mag` attaches to the `Mag` socket with a zero relative transform. Attach error is 1e-14 cm.
- Reload path: `MagInsertStart`, then `MagRockStart`, then an 8° rotation into `Mag`.
- `MuzzleSeat` and `Sight` sockets are provided. No attachments are included.

**Unreal version and import notes**
- Built for UE 5.8; measured on 5.8.3.
- Import settings: Import Normals, Convert Scene on, Force Front X Axis off.
- Set Negative Bounds Extension to (0, 0.378, 0) cm.
- Remove Degenerates drops sub-0.005 mm² triangles on the static meshes. They are micro bevel strips and are not visible.

**First person**
- Use `FP_Weapon`/`TP_Weapon` and `FP_Mag`/`TP_Mag` components.
- On the FP components, set First Person Primitive Type to FirstPerson and ForcedLodModel to 1.
- Measured: FP components cast no world shadow and stay on LOD0.

**File formats** (as documented)
- FBX: skeletal LOD0–3, 5 clips, static twin, magazine, physics proxy.
- PNG textures.
- JSON sidecars: skeletal, sockets, recolour.
- The Unreal Engine format package is still to be built (see Before publishing).

## 6. Category, tags, price

- **Category:** Weapons > Firearms. This depends on the Firearms-rule risk in Before publishing.
- **Tags:** Assault Rifle, Rifle, Firearm, Gun, Weapon, Rigged, Animated, First Person, Third Person, FPS, Shooter, PBR, Game Ready, Realistic\*. Run them through the deny scan first.
  - \*Use "Realistic" only once the realism re-review passes.
- **Price:** Personal $14.99–$19.99, Professional at 2× ($29.99–$39.99).
  - Reasoning: Fab weapon packs sit at $9.99–$59.99 with a Pro ratio of about 2–2.6× (FAB_ASSET_STUDY 6; FAB_PUBLISHING_STUDY 7.1). This is a single gun, and ratings pile up on packs under $20.
  - Confirm with the R0 competitor check.

## 7. Before publishing (internal, not buyer-facing)

**IP and design**
1. **Design too close to a real rifle.** The Fab version needs the original design changes: seven for AR01 plus an original dust-cover rail. None have been applied. *GUN_BUILDING_STUDY 9; RIFLE_REPORT 9.7.*
2. **Cartridge designation and real-gun references in the shipped docs.**
   - README line 1 gives the cartridge calibre. This draft omits it on purpose, because it points to the real pattern.
   - The README says "on the real rifle". MATERIALS_README says "as on real rifles of this pattern" and "as on real steel magazines".
   - Remove all of these, then rerun the deny scan on the shipped text. *README; MATERIALS_README; FAB_PUBLISHING_STUDY 3.1.*
3. **The name "AR-01".** Confirm it passes the gun deny list. The "AR-" prefix may read as a real designation pattern. *GUN_BUILDING_STUDY 4.8/4.9 (not provided here).*
4. **AI declaration.**
   - The design came from an AI design sheet, and the build was produced by Claude sessions.
   - Recommendation P1 is to declare Created with AI = Yes, with NoAI on.
   - This is the user's decision. *RIFLE_REPORT intro; FAB_PUBLISHING_STUDY 3.3.*
5. **Blind test.** The 12/12 identification against the sheet ran before the fixes and was not re-run. *RIFLE_REPORT 4.*

**Fab category and content risk**
6. **Firearms rule.** It requires "all expected moving parts rigged and a full set of animations". A reviewer may not accept weapon-only clips. Ask Fab support, or plan a minimal arms set on UE5 Manny (idle, fire, reload, reload empty, equip), Q6. *GUN_BUILDING_STUDY 9.*
7. **Skeleton compatibility.** No character skeleton has been tested. Make no Manny compatibility claim. *GUN_BUILDING_STUDY 9.*

**Quality items still open**
8. **Close-up realism not passed.** Earlier reviews called the hero, first-person and ADS views fake. The fixed bytes were not re-judged; the target is at most 1 fake call over the 4 views. *RIFLE_REPORT 4, 9.3.*
9. **Lightmap UV overlap (U8).** Generated UV1 overlaps on LOD1–3. Fab requires non-overlapping lightmap UVs. Options: an authored UV1, higher lightmap resolution, or declaring the rifle dynamic-lit only. *RIFLE_REPORT 5, 9.2; FAB_PUBLISHING_STUDY 4.2.5.*
10. **Micro bevel strips (U5, U10).** They cause the dropped triangles and the tangent-basis warnings. Fix them in the generators and rerun stages 2–8. Fab bars consequential warnings. *RIFLE_REPORT 5, 9.1; README.*
11. **Hand fit not tested (U11).** `SupportHand` and the `Grip` offset are provisional. *RIFLE_REPORT 9.4; README.*
12. **Other untested items.** First-person owner-only visibility in a weapon Blueprint, mobile and Nanite. *README "Good to know".*
13. **Triangle count discrepancy.** The README gives SK_AR01 LOD0 as 48,386. RIFLE_REPORT 2 and 3 give LOD0 as 49,474. Reconcile before stating counts. *README; RIFLE_REPORT 2–3.*
14. **Wrong sidecar materials block.** It lists `M_Fabric_Master` for the metal set. *RIFLE_REPORT 9.5; MATERIALS_README.*
15. **BC7 wood gate (P1).** The wood default reaches 4 levels against the 2-level gate. Accept the BC7 compression floor or go uncompressed (+18.6 MiB). *RIFLE_REPORT 6, 9.6.*
16. **LOD0 checkering.** Decide whether LOD0 gets checkering as cut geometry. *RIFLE_REPORT 9.7; README.*
17. **Absolute source path in the FBX files.** Fix before Fab. *RIFLE_REPORT 9.8.*

**Packaging (nothing built yet)**
18. **Fresh UE 5.8 product project.** R3 and R4 are not started. It needs:
    - one folder under Content, with masters and functions copied out of `/Game/NinjaPack` (never referenced across products);
    - `PHYS_AR01`, authored notifies, compression settings and sockets applied;
    - an overview map;
    - an example Blueprint that uses the sockets, loading with `Config/` deleted;
    - the migrate test, dependency scan and byte deny scan. The `ue_deny_scan.py` tool does not exist yet.
    *FAB_PUBLISHING_STUDY 1.2, 4.2; GUN_BUILDING_STUDY 9; RIFLE_REPORT 9.9 (merge order).*
19. **Engine version re-tests.** Rerun the 5.8.2-era pipeline tests on 5.8.3. *FAB_PUBLISHING_STUDY 4.2.6.*
20. **Media.**
    - A 16:9 thumbnail and a gallery of at least 1920×1080, each image under 3 MB and the total under 25 MB. `studio.py` needs a Fab preset.
    - A video showing all 5 clips, required for animated products.
    - Keep the media bloodless and free of fire effects.
    *FAB_PUBLISHING_STUDY 6.5, 3.5; TR 4.1.1.a.*
21. **Documentation and account.**
    - An English documentation page.
    - A support channel.
    - Seller onboarding and publisher name (P2–P5, P8, P9).
    *FAB_PUBLISHING_STUDY 2.1, 8.3.*
22. **Format slots.** Decide whether to offer the Blender sources. If they are offered, document the Blender re-import selector caveat. Confirm there are no third-party inputs to declare. *GUN_BUILDING_STUDY 9; README; FAB_PUBLISHING_STUDY 3.2.*
23. **Market gaps.** Top listings also ship ammo and casings, several skins and example Blueprints. Decide the scope or state what is not included. The R0 competitor check and price are still to do. *GUN_BUILDING_STUDY 9; FAB_PUBLISHING_STUDY 1.2.*
