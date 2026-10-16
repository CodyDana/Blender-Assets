<!-- Draft generated 2026-10-16 by the Batch API from the shipped docs; review before use. -->

# Fab Listing Draft: Sniper Rifle SR-01 (`SR01`)

## 1. Title

**Bolt-Action Sniper Rifle SR-01: Rigged and Animated** (52 characters)

Alternatives:
- Sniper Rifle SR-01 with Bipod and Scope (39)
- Rigged Bolt-Action Rifle SR-01 for UE5 (38)
- SR-01 Bolt-Action Rifle: Bipod, Scope, Clips (44)

Fab's guidance is "ideally about 30 characters". The shortest option fits that best.

---

## 2. Short description

Rigged bolt-action sniper rifle for UE 5.8: 8 weapon clips, folding and canting bipod, detachable 10-round magazine, separate long-range scope, LODs, collision and sockets.

---

## 3. Long description

SR-01 is a bolt-action sniper rifle built for Unreal Engine 5.8 games. It comes as:

- a rigged skeletal mesh with eight weapon-side animations;
- a static twin for pickups and world props;
- a detachable 10-round box magazine;
- a separate long-range scope that mounts on the 15-slot top rail.

The olive-drab painted chassis has an adjustable cheek riser. The folding bipod has independent legs that lean 12 degrees outward when deployed. The legs extend up to 76 mm in 19 mm detents, and the bipod cants up to 15 degrees. Deploy and stow clips are included, and a foot socket on each leg helps with prone placement.

The bolt turns and slides on its own bone, so firing and cycling the bolt are separate clips that you can chain or skip. The reload and empty-reload clips move the magazine along a straight, socket-to-socket path. Notify frames for the fire, bolt, reload and bipod events are documented.

The rifle is built for use in a game:

- four LODs on the rifle;
- custom convex collision on the static meshes;
- a physics setup for dropped weapons;
- 20 sockets on the rifle for the hands, muzzle, shell ejection, rail, sling, shoulder and bipod feet;
- authored lightmap UVs;
- PBR textures with packed ORM and DirectX normals.

The scope provides the aim and eye-point sockets for an aim-down-sights camera. The documentation covers setup for UE 5.8's first-person rendering.

The rifle carries generic markings only: no names, serials or logos.

**Not included:** characters, arm or hand animations, audio, VFX, ammunition or shell casings, and a scope-view material. The lenses are opaque, so a scope view needs your own material or render target.

---

## 4. Features

- Rigged skeletal rifle: the bolt, trigger, safety, magazine release, magazine, cheek riser and bipod all move.
- 8 weapon clips:
  - fire;
  - bolt cycle;
  - reload;
  - empty reload;
  - safety;
  - bipod deploy;
  - bipod stow;
  - cheek riser.
- Bolt action kept separate from firing: chain `Fire` into `BoltCycle`, or skip the cycle.
- Folding bipod:
  - independent legs that lean 12° outward when deployed;
  - 0–76 mm extension in five detents;
  - ±15° cant, folded or deployed.
- Detachable 10-round magazine as its own static mesh. It snaps to the `Mag` socket and follows a straight reload path.
- Separate long-range scope with rings:
  - mounts on the rail at a documented slot offset;
  - provides the `Sight`, `EyePoint`, `Lens_Front` and `CenterOfMass` sockets.
- Static twin with the bipod folded and the magazine merged, for pickups and world props.
- Four LODs on the rifle and the static twin; three on the scope.
- Custom convex-hull collision, with every LOD0 surface sample inside the hulls.
- Physics setup for dropped weapons, with documented masses and centre of mass.
- First-person ready: documented FP and TP component setup for UE 5.8 first-person rendering.
- PBR texture sets with packed ORM, DirectX normals and a wear/paint Masks map for custom layers.
- Generic markings only: no names, serials or logos.

---

## 5. Technical details

**Meshes and LOD triangle counts** (measured in Unreal 5.8.3 on the shipped bytes)
- `SK_SR01` (rigged rifle, without scope or magazine): 44,224 / 19,872 / 6,588 / 2,502.
- `SM_SR01` (static twin, bipod folded, magazine merged): 45,102 / 20,266 / 6,734 / 2,560.
- `SM_SR01_Mag`: 878 / 394 / 146 / 58.
- `SM_Att_Scope_LongRange` (scope with rings): 9,938 / 4,464 / 1,454.
- Nanite: off on every mesh.
- LOD screen sizes: supplied in the sidecar files.
- Overall length: 1,100 mm. Real-world scale; the bore is 96.13 mm above the grip origin.

**Texture sets and sizes** (21 maps; BC, ORM, N and Masks per set)
- `T_SR01_Metal_*`: 2048.
- `T_SR01_Chassis_*`: 4096.
- `T_SR01_Mag_*`: 1024.
- `T_Att_Scope_LongRange_Scope_Body_*`: 2048.
- `T_Att_Scope_LongRange_Scope_Lens_*`: 512.
- Masks maps are half size. Their channels are:
  - R: edge wear;
  - G: handling;
  - B: cavity;
  - A: 1 only on the OD paint.
- `Recolour/T_SR01_Chassis_Detail16`: 2048, 16-bit linear.
- Colour spaces: BaseColor sRGB; ORM and Masks linear; normals DirectX (*Flip Green Channel* off).
- All maps are square powers of two with full mip chains.
- Chassis and Mag BaseColor are imported as BC7.

**Materials and recolour**
- Material slots:
  - `M_SR01_Metal` and `M_SR01_Chassis` on the rifle and the twin;
  - `M_SR01_Mag` on the twin and the magazine;
  - `M_Att_Scope_Body` and `M_Att_Scope_Lens` on the scope.
- Material instances:
  - `MI_SR01_Metal`, `MI_SR01_Mag`, `MI_Att_Scope_LongRange_Body` and `MI_Att_Scope_LongRange_Lens` are steel instances with a **Steel Tint** control (white = as shipped);
  - `MI_SR01_Chassis` shows the baked olive-drab finish.
- Draw calls in hand: 10 (gun 2 × 2, magazine 2 × 1, scope 2 × 2, FP and TP).
- The olive-drab paint ships as baked. A built-in paint recolour is not offered.
- For a custom paint colour, lerp the BaseColor toward your tint in your own material, using Masks A as the mask.

**Rig**
- Skeleton `SK_SR01_Skeleton`: `root` plus 13 rigid bones:
  - `body`, `bolt`, `trigger`, `selector`, `mag_release`, `magazine`, `muzzle_device`, `cheek_riser`;
  - `bipod`, `bipod_leg_l`, `bipod_leg_l_ext`, `bipod_leg_r`, `bipod_leg_r_ext`.
- One influence per vertex.
- An angle table gives the documented motion range of each bone.

**Animations**

| Clip | Frame rate | Frames | What happens |
|---|---|---|---|
| `A_SR01_Fire` | 60 fps | 8 | Trigger breaks and resets; the bolt does not move |
| `A_SR01_BoltCycle` | 30 fps | 30 | Bolt lifts 60°, runs 88 mm back and returns |
| `A_SR01_Reload` | 30 fps | 60 | Magazine out, new magazine in |
| `A_SR01_ReloadEmpty` | 30 fps | 90 | Starts with the bolt open; reload, then bolt forward and down |
| `A_SR01_Selector` | 30 fps | 20 | Safety: Fire, Safe, Fire |
| `A_SR01_BipodDeploy` | 30 fps | 36 | Legs swing down and extend 38 mm |
| `A_SR01_BipodStow` | 30 fps | 36 | Reverse of deploy |
| `A_SR01_CheekRiser` | 30 fps | 24 | Riser up 12 mm, down to −12.9 mm and back (optional clip) |

- Notify frames are documented for Fire, BoltCycle, Reload, ReloadEmpty, BipodDeploy and BipodStow.
- Recommended bone compression: `DefaultRecorderBoneCompression`. With it, runtime poses match the authored clips with 0.0 mm error on every rigid part.

**Sockets**
- 20 on `SK_SR01`, listed in the sidecar:
  - Grip, SupportHand, SupportHandBipod;
  - Trigger, Selector, MagRelease, BoltHandle;
  - Muzzle, MuzzleSeat, ShellEject;
  - Mag, MagInsertStart, Rail_Top;
  - SlingFront, SlingRear, Shoulder;
  - CenterOfMass, Holster;
  - BipodFoot_L, BipodFoot_R.
- 20 on `SM_SR01`.
- 5 on the magazine: Mag, Feed, Base, HandReload, CenterOfMass.
- 5 on the scope.

**Collision**
- `SM_SR01`: 10 convex hulls (`UCX_SM_SR01_LOD0_00..09`).
- Magazine: 1 hull.
- Scope: 3 hulls.
- All hulls have 32 vertices or fewer.
- Import with *One Convex Hull per UCX* on and *Auto Generate Collision* off.

**Physics**
- `PHYS_SR01` is one body on `body`:
  - 7 boxes and 1 capsule that collide;
  - a no-collision, no-mass bounds box.
- Rifle mass: 5.9 kg without scope or magazine, bipod included.
- Magazine mass: 0.20 kg empty, 0.45 kg loaded.
- Scope mass: 1.15 kg.
- Ready to fire: about 7.5 kg.
- Drop-tested from 1 m with no tunnelling.
- A physics proxy FBX is included for rebuilding the physics asset.

**Magazine and attachments**
- The magazine snaps to `Mag` with a zero relative transform.
- The reload path is a straight 67.8 mm line from `MagInsertStart` to `Mag`.
- The scope mounts on `Rail_Top` + 2 slots (X +20.02 mm) with zero rotation.
- The scope's `Sight` socket is 57.6 mm above the bore and parallel to it. No zero is built in.
- The bolt knob clears the mounted scope by 29.9 mm over the whole cycle.

**Unreal version and import notes**
- Verified in Unreal Engine 5.8.3.
- FBX import settings:
  - legacy FBX importer;
  - Import Normals;
  - *Convert Scene* on;
  - *Force Front X Axis* off;
  - Import Mesh LODs on.
- Lightmap UVs: UV1 authored at index 1, with 0 overlap. Generate Lightmap UVs off.
- A bounds extension is supplied in the sidecar. It covers every clip frame and the extreme poses.
- 0 asset warnings on import.

**First-person notes**
- Use one FP and one TP component per part.
- On every FP component, set *First Person Primitive Type* = FirstPerson and *ForcedLodModel* = 1.
- Measured: the TP ground shadow is present, and the FP components cast none.

**File formats**
- FBX: skeletal mesh and LODs, 8 clips, static meshes, physics proxy.
- Texture maps.
- JSON sidecars: sockets, LOD sizes, notifies, physics bodies, angle table.
- Documentation: README and MATERIALS_README.

---

## 6. Suggested category, tags and price

- **Category:** Weapons (Firearms subcategory; confirm the exact name in Fab's picker).
- **Tags (15):**
  - Sniper Rifle, Rifle, Bolt Action, Firearm, Gun, Weapon;
  - Scope, Bipod, Rigged, Animated, PBR;
  - First Person, Shooter, Military, Game Ready.
  - "Realistic" can be added as the one style tag once the close-up realism question below is settled.
- **Price:** $14.99–$19.99 Personal / $29.99–$39.99 Professional.
- **Reasoning:** Fab weapon packs sit at $9.99–$59.99 with an observed Professional ratio of 2–2.6x, and an entry pack is $9.99–$19.99 at 2x (FAB_ASSET_STUDY §6; FAB_PUBLISHING_STUDY §7.1). This is a single rifle plus magazine and scope, so it belongs in the entry band, where ratings tend to accumulate.

---

## 7. Before publishing (internal, not buyer-facing)

**IP and design (blockers)**
1. **The design is too close to a real gun for sale.**
   - At W4 the blind test picked the copy in 14 of 14 pairs on design. The tells were stock hardware, the open guard, the glossy scope, the flutes and the grip (SR01_REPORT §3, §8.6).
   - GUN_BUILDING_STUDY §9 requires original design changes before any Fab version.
   - Seven changes are listed for AR01, but **none are documented for SR01**.
   - Next steps: write the SR01 list, apply it, re-export, then re-run all gates and W5.
2. **Markings exception.**
   - The user approved the scope turret ticks and numerals as a generic marking.
   - GUN_BUILDING_STUDY §9 says "no ... numerals", and the safety also carries S / F letters.
   - Record both as a dated exception in `FAB_LISTING.md` (FAB_PUBLISHING_STUDY 3.6, R1).
3. **Deny scan is stale.**
   - The W6 deny scan (0 hits) ran on round-1 text and names (SR01_REPORT §5).
   - Re-run it on the final bytes, the listing text, tags and video titles, with the gun deny list.
   - The Unreal byte scanner `ue_deny_scan.py` does not exist yet (FAB_PUBLISHING_STUDY 4.2.6).
4. **"AR-01" references.**
   - Decide whether buyer text mentions compatibility with `SK_AR01_Skeleton` (README).
   - Mention it only if that product ships; otherwise remove it.
5. **AI declaration.**
   - The design came from "the user's AI design sheet" (SR01_REPORT §1).
   - Under recommended policy P1, Created with AI = Yes and NoAI = on, and the listing never says "handmade" (FAB_PUBLISHING_STUDY 3.3, 8.3).
   - This is the user's decision.

**Fab category rule**

6. **Firearms rule risk.**
   - Fab requires "all expected moving parts rigged and a full set of animations".
   - A reviewer may not accept weapon-only clips.
   - Ask Fab Support, or add a minimal UE5 Manny arms set: idle, fire, reload, reload empty, equip (GUN_BUILDING_STUDY §9, Q6).

**Quality open items**

7. **Close-up realism is not passed** (REALISM_R2_REPORT; SR01_REPORT §8).
   - The judges said fake 8/8 at W4b and again in round 2. The final pass was not re-judged.
   - K1, K2, K3, K9 and K10 still fail.
   - K4 got worse (8,331 → 19,463 bare-metal texels) and was not investigated.
8. **Form gates are open** (REALISM_R2_REPORT; SR01_REPORT §2, §8).
   - L2: GR 0.9571, GL 0.9410 / 0.9490, TOP 0.8376 / 0.9026.
   - L3: P95 3.61 px.
   - L4: 13 / 14.
   - B9 near-misses.
   - The TOP conventions need the user's call.
9. **Hand fit in Unreal (U11) was not run**, so the `Grip`, `SupportHand` and `SupportHandBipod` sockets are provisional. Measured follow-ups not yet applied (README "Good to know"):
   - `SupportHand` is out of reach by 83 mm in a square stance.
   - `SupportHand` sits 9.6 mm inside the forend.
   - `SupportHandBipod` sits 38.1 mm inside the butt.
   - The cheek riser is 1.6 mm short of travel.
   - The engine hand pose needs its own thumb.

**Materials**

10. **Pack materials** (MATERIALS_README; PACK_REPORT):
    - P1, P2 and P3a passed. P3b failed on 11 of 13 colours, so recolour must not be advertised.
    - P4, S1–S7, R2 memory and the R3 lit-frame review are not reported.
    - The BC1 vs BC7 choice is not recorded.
    - D1-b (a mask switch for paint-only recolour) is not built.
    - The `PackMaterials` lock state must be checked or released.
11. **Shared masters.** `M_Steel_Master` and `M_Fabric_Master` are shared masters. They must be copied under `Content/<Pack>/` and never referenced across products (FAB_PUBLISHING_STUDY 4.2.6).

**Documentation is stale or internal**

12. **README contradictions.** Fix these before shipping:
    - The file table and "Good to know" give round-1 triangle counts (40,518 / 41,396; held set 51,334; magazine LOD2/3 150/62) and round-1 LOD screen sizes. The measured round-2 values used above differ.
    - The status banners in README and MATERIALS_README still say the Unreal build is pending, while the measured pack-build line says it ran.
13. **README is not buyer-ready.**
    - It contains internal paths (`WorkFiles/...`) and jargon (W5, U11, `MH_PlayerDefault`).
    - It points to `Scripts/pipeline/ue_import_sockets.py`, which is not shipped.
    - A public English documentation page is needed (FAB_PUBLISHING_STUDY 6.5, P5).
14. **Hashes and branches.**
    - The W5 sha256 for `Textures/Recolour/*` no longer match (replaced on purpose).
    - Re-verify the final shipped set.
    - The round-2 work is uncommitted and the branches are unmerged (REALISM_R2_REPORT; SR01_REPORT).
    - Release the `SR01` lock when done.

**Unreal-format product (not built)**

15. **Build the clean project** (FAB_PUBLISHING_STUDY R3–R4; GUN_BUILDING_STUDY §9). Nothing below exists yet:
    - a fresh UE 5.8 `<Pack>` project;
    - an overview map with lighting built;
    - an example Blueprint that uses the sockets;
    - notifies applied (the FBX files carry none);
    - `PHYS_SR01` built;
    - static-mesh sockets applied;
    - a migrate test with `Config/` deleted;
    - a dependency scan;
    - the zip and a no-login link.
16. **Re-run the measurements.** The Unreal tests from FAB_ASSET_STUDY 3.11 were measured on 5.8.2. Re-run them on 5.8.3 (FAB_PUBLISHING_STUDY A18).

**Media**

17. **The showcase is stale and the wrong size.**
    - The 15 images were rendered in W6 from round-1 bytes, before round 2 changed the geometry (SR01_REPORT §5).
    - `studio.py` defaults to 4:3 1600×1200, which is below Fab's floor. It needs a 16:9 preset (FAB_PUBLISHING_STUDY 6.5, P6).
    - Still needed: a thumbnail, an overview grid, a trailer, and the `ASSET_LIST.md` row (SR01_REPORT §9).

**Listing decisions still open**

18. Decide these before submitting:
    - final price;
    - engine versions (list 5.8 only);
    - whether to offer the Blender sources (`Assets/Guns/SR01.blend`, `Att_Scope_LongRange.blend`);
    - FBX slot packaging and texture file format (only Detail16 is documented as PNG);
    - Mature = no;
    - third-party content = none (confirm);
    - seller onboarding and support channels P2–P9.
19. **Competitor gap.** Top listings ship ammo and casings, several material skins and example Blueprints (GUN_BUILDING_STUDY §9). SR01 has none of these; it has only a `ShellEject` socket. Decide whether to add them or state their absence.
