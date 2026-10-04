# Unreal weapon tech: how a gun asset must be built for UE 5.8

Role note for the gun best-practice study (one file per role). Scope: the Unreal side of a firearm asset. Static or
skeletal mesh, bone and socket standard, magazines and reloads, first-person rendering, LODs and Nanite, attachments,
pickup collision, attaching to the hand (Lyra, Game Animation Sample, Epic's 5.8 FP template), and what Fab weapon
listings advertise. Applies to the whole gun line in `References/Guns/` (Rifle, SMG, Carbine, LongRifle, Sniper, Pistol)
and the backlog in `WorkFiles/guns/GUN_REFERENCE_PROMPTS.md`.

**Written:** 2026-10-04. **Versions:** Unreal Engine 5.8 (installed at `C:/Program Files/Epic Games/UE_5.8`), Blender 5.2.

**Evidence tags.**
- **[M]** measured in this repo or on this PC: engine headers, engine shaders, Epic's 5.8 template assets (name tables
  read straight from the `.uasset` files), the Game Animation Sample project, our own pipeline code and exports.
- **[E]** external: Epic docs, vendor docs, forum posts, Fab listing pages (read 2026-10-04). Numbers like [3] point to
  section 12.
- **[J]** judgement: my recommendation from the evidence.

A note on the [M] uasset reads. I pulled bone, socket and property names from each package's name table (a string scan,
not a full parse). That tells us which names exist in the asset. It does not tell us values or the exact hierarchy, so
anything beyond "this name is in this asset" stays [J] until a 5.8 Python dump confirms it (gate U1 in section 10).

---

## 1. The answer in ten lines

1. **Every gun ships as a skeletal mesh (`SK_<Gun>`), rigidly skinned, with a small skeleton of named moving parts.**
   Epic's own UE 5.8 First Person template does this for every weapon: `SKM_Rifle`, `SKM_Pistol` and
   `SKM_GrenadeLauncher`, each with an `SK_` skeleton and a `PA_` physics asset [M]. So does every animated Fab gun pack
   read for this study [E][8-16]. A static-only gun cannot run a bolt, slide, trigger or folding stock [J].
2. **A static mesh of each gun still ships** (`SM_<Gun>`, UCX hulls, LODs, UV1). It is the world-loot or pickup mesh and
   the version for buyers who only dress scenes. Epic's template pickup uses a static mesh with a physics body [M], and
   the top Fab packs advertise "a static mesh and a rigged skeletal mesh" [E][13].
3. **The magazine is its own static mesh (`SM_<Gun>_Mag`).** It attaches to a `Mag` socket on a `magazine` bone, so a
   reload can move it with the gun's animation, hand it to the left hand, or drop it as a physics prop [M][E][3][15].
4. **One standard bone list and socket list for all guns** (section 3). Bones are lowercase like Manny's. Sockets are
   PascalCase like Epic's template (`Muzzle`, `ShellEject`, `GripPoint`) and our existing sockets (`Grip`, `Pivot`).
5. **First person: one weapon asset in two components.** One component is set to `First Person` (custom FOV and scale,
   casts no shadow). The other is set to `World Space Representation` (hidden from its owner, casts the shadow, shows in
   reflections). This is exactly how Epic's 5.8 template weapon Blueprint is built (`FP_Weapon` and `TP_Weapon`, both
   the same `SKM_`) [M][1].
6. **Classic LODs, not Nanite, on the gun skeletal meshes for v1.** Nanite skinning is on by default in 5.8 [M] and
   Epic's 5.8 page lists skeletal mesh support [E][4]. But the first-person gun is always at LOD0 anyway, the gun is
   only 20-50k triangles, and Fab buyers on non-Nanite targets need real LODs [J]. Nanite can be tried later on the
   static loot mesh.
7. **Attach to a `weapon_r` socket on `hand_r`** (Lyra's name [E][6]; the Game Animation Sample (GASP) project's `SK_Mannequin` holds
   `weapon_r`, `weapon_l` and `weapon_r_muzzle` [M]). Our MetaHuman body skeleton has no `ik_*` bones [M, ASSET_GUIDELINES
   section 7], so `ik_hand_gun` is not available on the player without extra work. Drive the off-hand with two-bone IK
   to the gun's `LeftHand` socket [E][7], the same job Epic's template Control Rig `Ctrl_HandAdjusment` does with
   `hand_l` and `hand_r` [M].
8. **Attachments are static meshes on rail sockets** (`Rail_Top`, `Rail_Bottom`, `Rail_Left`, `Rail_Right`, plus
   `Muzzle` and `Stock`). Each attachment carries its own override sockets: `Sight` on an optic, `Muzzle` on a
   suppressor, `LeftHand` on a foregrip [J; pattern in E][9][10][13].
9. **Physics:** a `PA_<Gun>` with one simple body on `body`, kinematic while held and simulated when dropped, the same
   shape as Epic's template (one box or capsule on the grip bone) [M]. Loot on the ground uses the static `SM_` with UCX
   hulls, which our pipeline already ships and checks [M].
10. **What Fab weapon listings sell:** rigged or skeletal meshes, weapon-side animations, modular parts and
    attachments, several material skins, 4K PBR, Blender sources, sockets with example Blueprints, ammo and casings, and
    a named compatible skeleton (UE5 Manny). Poly counts are rarely in the description text [E][8-16].

---

## 2. Static or skeletal

### 2.1 What the evidence says

| Source | What the gun is | Detail |
|---|---|---|
| Epic UE 5.8 FP template, `Templates/TemplateResources/Standard/Weapons` | `SKM_` + `SK_` + `PA_` + `SM_` per weapon [M] | Pistol bones: `Root`, `Grip`, `Slide`, `Trigger`, `Magazine`, `Barrel`; sockets `Muzzle`, `ShellEject`; `PA_Pistol` one box on `Grip`. Grenade launcher bones: `Root_Bone`, `Grip_Bone`, `Slide_Bone`, `Trigger_Bone`, `Clip_Bone`; sockets `GripPoint`, `Muzzle`; `PA_` one capsule on `Grip_Bone`. Rifle: **a single bone** (`LP_LowerFront_001`), sockets `GripPoint`, `GripPoint_002`, `Muzzle`; `PA_Rifle` one capsule. `SM_Pistol` carries convex hulls (`KConvexElem`) [M] |
| Epic template Blueprints | `BP_ShooterWeaponBase` holds `FP_Weapon` and `TP_Weapon` skeletal mesh components, sets `FirstPersonPrimitiveType`, reads sockets with `GetSocketLocation` (`Muzzle`) [M] | `BP_ShooterPickup` is a `StaticMeshComponent` with a physics body [M]. Character attach socket name: `HandGrip_R` [M] |
| Epic UDK weapon docs [5] | Skeletal mesh used for both first and third person [E] | The long-standing Unreal pattern |
| Infima Games (Tactical FPS packs, Modern Guns) [3][8][15] | Skeletal mesh receiver + **separate static magazine** with its pivot on the `Magazine` bone; per-weapon skeletons (`SKEL_TFA_AR`, `SKEL_TFA_Pistol`) [E] | Bones `Grip`, `Trigger`, `Bolt`, `Dust_Cover`, `Charging_Handle`, `Magazine_Release`, `Fire_Selector`; `CB_` controller bones stay in Blender; sockets `SOCKET_Muzzle`, `SOCKET_Laser`, `SOCKET_Grip` |
| nanos world weapon spec [17] | Skeletal mesh, root bone attaches to `hand_r_socket`; points along **+X**; sockets `muzzle` and `shell_eject` [E] | X out of the muzzle, Y the shell direction |
| Call of Duty modding rigs [18] | `tag_weapon` (main animated joint, hands IK to it), `tag_flash` (muzzle), `tag_brass` (eject), `tag_clip` (magazine) [E] | Same four jobs under other names |

### 2.2 What each gun needs to animate

Only parts you can **see from outside** get a bone. Internals are not modelled, and they are not rigged [J].

| Part | Rifle (AK-style) | SMG (boxy, folding stock) | Carbine (M4-style) | LongRifle (M16-style) | Sniper (bolt, bipod) | Pistol (large frame) |
|---|---|---|---|---|---|---|
| Bolt or carrier | `bolt` (carrier with the charging handle in one piece) | `bolt` (seen in the port) | `bolt` (seen in the port) | `bolt` | `bolt` (rotates about the bore, then slides) | - |
| Separate charging handle | - | `charging_handle` (front, non-reciprocating) | `charging_handle` (T-handle, rides back with the carrier only when charging) | `charging_handle` | - | - |
| Slide / barrel | - | - | - | - | - | `slide`, `barrel` (tilt) |
| Trigger | `trigger` | `trigger` | `trigger` | `trigger` | `trigger` | `trigger` |
| Hammer | only if visible (no) | - | - | - | - | `hammer` (external) |
| Selector / safety | `selector` (right-side lever) | `selector` | `selector` | `selector` | `selector` (safety) | `selector` (safety or decocker) |
| Magazine | `magazine` | `magazine` | `magazine` | `magazine` | `magazine` | `magazine` |
| Mag release | `mag_release` (paddle) | `mag_release` | `mag_release` | `mag_release` | `mag_release` | `mag_release` |
| Bolt catch / slide stop | - | optional | `bolt_catch` | `bolt_catch` | - | `slide_stop` |
| Dust cover | removable cover, not animated | - | `dust_cover` (hinged, pops open) | `dust_cover` | - | - |
| Stock | fixed (wood) | `stock` (hinge fold) | `stock` + `stock_ext` (telescoping) | fixed | optional `cheek_riser` | - |
| Sights | `sight_rear` (ladder leaf slider) | flip-ups if the sheet shows them | `sight_front`, `sight_rear` (folding) | carry-handle drum (no) | - (scope) | - |
| Bipod | - | - | - | - | `bipod`, `bipod_leg_l`, `bipod_leg_r` (+ `_ext` if the legs extend) | - |

Backlog, the same way: the pump shotgun gets `pump`, the LMG gets `feed_cover`, `bipod` and `belt_*`, and the crossbow
gets `string` and `limb_l` / `limb_r`.

**Why skeletal and not "static plus separate moving-part meshes":** you could attach separate static parts (a bolt
mesh, a trigger mesh) and move them in Blueprint. That means many components per gun, each one twice (FP and TP), and
no authored animation clips. Every listing and Epic's own template use bones instead [M][E]. Fab buyers expect the
weapon to accept animation [E][8-16]. [J]

---

## 3. The house gun skeleton and sockets (proposed standard for every gun)

### 3.1 Conventions

- **Armature object named `root`**, identity transform. Unreal makes the object node the root bone, so no bone is
  called `root`. This is the measured house rule from `SK_Fan` (`Scripts/pipeline/skeletal_prop.py`,
  `skeleton_checks`) [M].
- **Origin = grip point.** This is the centre of the pistol grip where the right hand's web sits, on the bore's vertical
  plane (Y = 0). ASSET_GUIDELINES section 1 already says "grip point for weapons" [M]. The origin is the default
  attach point, and the `Grip` socket marks it explicitly.
- **Axes:** the barrel points along Blender **+X** and the top faces **+Z**. Through the house FBX axes (forward -Y,
  up Z, as `SM_Katana.sockets.json` records), that arrives in Unreal as muzzle +X, up +Z and the gun's right side +Y
  [M for the axis mapping; J for the choice]. nanos world requires +X [E][17]. Epic's template weapons should be checked
  against this in gate U1.
- **Bone names** are lowercase snake_case with no dots, like Manny (`hand_r`) [M]. **Socket names** are PascalCase,
  like Epic's template (`Muzzle`, `ShellEject`) [M] and our existing `Grip` / `Pivot` / `Tassel` / `BladeBase` [M].
- **Rigid skinning:** every vertex has exactly one influence at weight 1.0. Each part is a closed, separate mesh object
  with its pivot on the real hinge or slide axis, and has clearance so the motion never intersects. A slot the
  charging handle travels in must be real cut geometry the full travel length [J].
- **Bone rest orientation = weapon axes.** Each bone's rest rotation equals the root's, so "bolt back" is always -X and
  a selector turns about X in every gun. Procedural code (Transform Modify Bone) then works on every gun unchanged.
  Hinge bones put their head on the hinge axis [J; must be measured in Unreal, gate U2].
- **Bones that a gun does not have are left out**, not added as dummies [J]. Code reads bones by name and skips the
  ones that are missing.
- **One skeleton asset per gun** (`SK_<Gun>_Skeleton`), as Infima does [E][3]. Bolt travel and hinge positions differ
  per gun, so animations do not transfer anyway. The common names keep the Blueprints generic [J].

### 3.2 Bone list

```
root                      (armature object = Unreal root bone; no geometry)
  body                    receiver, barrel, handguard, grip, fixed stock, fixed sights: everything rigid
    trigger
    hammer                pistol (external) only
    selector              fire selector / safety lever
    mag_release
    bolt_catch | slide_stop
    bolt                  carrier or bolt group (AK: includes the charging handle)
    charging_handle       AR / SMG separate handle (child of body, not of bolt)
    slide                 pistol
      barrel              pistol tilting barrel (child of slide)
    dust_cover            hinged ejection-port cover
    magazine              the attach bone for SM_<Gun>_Mag (no skinned geometry needed)
    stock                 folding or telescoping stock
      stock_ext           telescoping segment
      cheek_riser
    sight_front / sight_rear      folding or adjustable sights
    bipod
      bipod_leg_l, bipod_leg_r   (+ bipod_leg_l_ext, bipod_leg_r_ext)
    pump                  shotgun forend
```

Typical counts: Rifle 7 (body, trigger, selector, mag_release, bolt, magazine, sight_rear). Carbine 11. Pistol 9.
Sniper 10-12. All are far below any budget [J].

**Every bone stays a deform bone** (the house exporter writes deform bones only; `skeleton_checks` fails a non-deform
bone [M]). The `magazine` bone has no weighted vertices when the magazine is a separate mesh. It only needs
`use_deform`, which the current check allows [M; confirm in gate B1 that the FBX keeps an unweighted deform bone].

### 3.3 Socket list

All sockets ride on bones and are written to the `.skeletal.json` sidecar. That sidecar already carries sockets on
bones in both Blender and Unreal space (`write_skeletal_sidecar`) [M]. As with the fan, they are applied after import,
not trusted to the FBX [M].

| Socket | Bone | Place and axes | Used by |
|---|---|---|---|
| `Grip` | body | the origin; +X forward, +Z up | attach to the character's `weapon_r`; Epic calls it `GripPoint` [M] |
| `LeftHand` | body (or the foregrip attachment) | the off-hand palm centre on the handguard or magazine well (pistol: the support-hand wrap) | off-hand two-bone IK target [E][7]; Epic's rifle has a second grip socket `GripPoint_002` [M] |
| `Muzzle` | body (pistol: barrel) | the bore exit; +X out of the bore | flash VFX, the muzzle-device mount, trace start for VFX [M][E] |
| `ShellEject` | body (pistol: slide) | the ejection port; +X out of the port, +Y the throw direction | casing Niagara or mesh spawn [M][E][17] |
| `Sight` | body | on the iron-sight line, at the rear aperture; +X along the sight line | ADS camera alignment. An optic's own `Sight` overrides it [J]. Epic's FP ABP has an `IronSight` value [M] |
| `Mag` | magazine | the magazine's own origin (the top centre of its feed lips, on the bore plane) | attaching `SM_<Gun>_Mag` [E][3] |
| `Rail_Top`, `Rail_Bottom`, `Rail_Left`, `Rail_Right` | body | the centre of the first slot of each rail, on the rail top face; +Z away from the rail | attachments; slot index n gives a position of socket + n x pitch along X [J] |
| `Stock` | body | the stock interface (buffer tube end or hinge face) | modular stocks [J] |
| `Laser`, `Light` | body | where a gun has fixed mounts | optional [E][3] |
| `Sling_F`, `Sling_R` | body | the sling swivels | holstered or back-carry placement [J] |
| `Holster` | body | the point the gun hangs from on the back or hip | third-person stowed weapon [J] |

Pitch: if the rail is a Picatinny-style rail, the slot pitch is about 10 mm (0.394 in). The pitch is recorded in the
sidecar per rail, so the attachments kit can snap to slots [J; it is a shared standard in the backlog].

---

## 4. Magazines and reloads

**Asset rule:** `SM_<Gun>_Mag` is a separate static mesh with LODs and one simple UCX hull. Its origin equals the `Mag`
socket's frame. The top round, if visible, is modelled into it. Optional `Round_01..` sockets allow per-round
visibility, as Infima's `Bullet_001..` sockets do [E][3][15]. Drum and extended magazines are more `SM_` meshes on the
same socket [E][10].

Two reload patterns, both supported by that asset rule [J]:

1. **The mag rides the weapon's bone (simplest, same in FP and TP).** The weapon's reload clip moves the `magazine`
   bone out and back in, synced to the character's reload montage. At a `MagDrop` notify, spawn a physics copy of
   `SM_<Gun>_Mag` at the socket and hide the attached one. At `MagIn`, show it again. This is Infima's setup: the
   magazine pivot sits on the `Magazine` bone [E][3].
2. **Hand swap.** At `MagOut`, detach the magazine component from the weapon's `Mag` socket and attach it to a
   character socket on `hand_l` (for example `Mag_L`). At `MagIn`, attach it back. Animation notifies plus attach and
   detach are the standard Unreal method [E][19].

Pattern 1 needs weapon-side reload clips per gun. Pattern 2 needs only the character montage. Both need the separate
mesh and the `magazine` bone, which is why both go into the standard [J].

**Casings:** ship small generic casing meshes per calibre class (rifle intermediate, rifle full-power, pistol), spawned
at `ShellEject`. Both the Tactical Gun Pack and the Developer Weapon Kit ship casings [E][11][16]. Generic names, no
headstamps (IP) [J].

---

## 5. First-person rendering in UE 5.8

### 5.1 The engine feature (measured in the 5.8 source, matches the docs)

- `EFirstPersonPrimitiveType` on every primitive component has three values: `None`, `FirstPerson` and
  `WorldSpaceRepresentation` [M: `Engine/Classes/Components/PrimitiveComponent.h` lines 150-161].
  - `FirstPerson` uses the camera's `FirstPersonFieldOfView` and `FirstPersonScale`. Its dynamic, static, far and
    capsule shadow flags are disabled by an EditCondition, so it **casts no shadow onto the scene** [M][1].
  - `WorldSpaceRepresentation` "is the primitive that other players would see and is used to cast shadow onto the
    ground". It internally sets `bOwnerNoSee = true` and `bCastHiddenShadow = false`, "required for first person shadow
    to work correctly with VSM" [M, the header comment][1].
- `UCameraComponent` holds `FirstPersonFieldOfView` and `FirstPersonScale` (0.001-1, it "scale[s] down primitives
  towards the camera such that they are small enough not to intersect with the scene"), each behind an enable flag
  (`bEnableFirstPersonFieldOfView`, `bEnableFirstPersonScale`) [M: `CameraComponent.h` lines 49-60, 207-217].
- The morph happens on the GPU after World Position Offset and before projection. **Transform World to First Person**
  maps a world point into that space, for example to spawn a projectile from the on-screen muzzle [E][1][2].
- Limits: **deferred renderer only** (no mobile, no forward). **Allow Static Lighting** must be off. Ground shadows
  from the WSR mesh need **Virtual Shadow Maps or ray-traced shadows**. Self-shadow on the FP mesh is opt-in
  (`r.FirstPerson.SelfShadow=1`, screen-space traced). Works on static meshes, skinned meshes and Niagara. Grooms are
  not supported [E][1].
- Nanite geometry honours the first-person transform: `NaniteCullingCommon.ush` has
  `ApplyFirstPersonTransformToBounds` [M]. So a Nanite static attachment or loot mesh can sit in a first-person view
  without bounds popping [J].

### 5.2 How Epic's 5.8 template uses it (measured)

- `BP_FirstPersonCharacter` has `FirstPersonMesh` (Manny arms/body for the owner) and `CharacterMesh0` (the full body
  for the world), with `ABP_FP_Copy` copying the pose [M].
- `BP_ShooterWeaponBase` has **`FP_Weapon` and `TP_Weapon`, both pointing at the same `SKM_` asset**, and sets
  `FirstPersonPrimitiveType` on them [M]. `ABP_FP_Weapon` and `ABP_TP_Rifle` animate them. The FP ABP carries
  `IronSight`, `GripOffset` and `Hand_R_Target` [M].
- The shooter character attaches at `HandGrip_R` and uses `FirstPersonScale` [M].

### 5.3 What that means for our assets [J]

- **One weapon mesh asset, not separate FP and TP models.** Shipped games often keep a separate, richer viewmodel [E][20],
  but with the 5.8 feature and a 20-50k LOD0 gun, one asset in two components covers both views (Epic's own template
  does exactly this [M]). Revisit only if the FP close-up shows something the TP mesh does not need (for example, the
  inside of the ejection port at ADS distance).
- **The FP component is forced to LOD0** (`ForcedLodModel = 1`). The WSR component uses the LOD chain. So LOD0 must
  hold up at 20-60 cm from the eye, under the first-person FOV the game picks (Fab packs quote FP animations made at
  90 deg with ADS at 70 deg [E][11]).
- **Texel density for the FP view:** the house first-person figure of 10.24 px/cm [M, ASSET_GUIDELINES section 4]. A
  ~90 cm rifle unwrapped at that density needs a 4K set, or 2K sets split by material (metal, wood, polymer). The
  listings advertise 4K PBR [E][8][12].
- **Every attachment also needs both components** (FP and WSR), because each mesh component has one primitive type.
  This argues for keeping attachments few and static [J].
- **Muzzle VFX:** the owner sees the FP muzzle; everyone else sees the TP muzzle. Gameplay traces start from the
  camera, not the morphed FP muzzle; use Transform World to First Person when a visual must line up [E][1].
- **Project setting the game needs:** Virtual Shadow Maps on, Allow Static Lighting off, deferred renderer. Record this
  in the gun pack README, because a buyer with forward rendering will get no FP rendering [E][1].

---

## 6. LODs, Nanite and budgets

- **Nanite skinning in 5.8:** `r.Nanite.AllowSkinnedMeshes` defaults to **1** (read-only cvar) [M:
  `Engine/Private/Rendering/NaniteResources.cpp`]. `USkeletalMesh` has `NaniteSettings` [M: `SkeletalMesh.h` line 964].
  Epic's 5.8 Nanite page lists skeletal meshes with "no geometry LODs; Nanite Skeletal Mesh uses animation LODs", says
  morph targets are not supported, and allows Opaque or Masked materials only [E][4]. Our `FAB_ASSET_STUDY.md` line
  478 still says "Experimental [unverified]" [M]. Treat the status as **not yet verified on our content**.
- **Decision for v1 [J]:** classic LODs on `SK_<Gun>` (LOD0-LOD3) and `SM_<Gun>`, Nanite off on the skeletal mesh.
  - The first-person gun is pinned to LOD0, so Nanite saves nothing there.
  - The guns are small (house hero-weapon budget 20-50k LOD0 [M, ASSET_GUIDELINES section 2]).
  - Fab buyers on mobile, forward or VR need real LODs.
  - Skeletal LODs can drop the small bones at LOD2+ (`trigger`, `selector`, `mag_release`, `bolt_catch`) with the
    LOD's Bones To Remove. Keep `body`, `bolt` / `slide`, `magazine`, `stock` and `bipod*` at every LOD [J].
  - For the static loot mesh in the battle royale (many instances on the ground), test Nanite later with the LODs
    kept as the fallback (gate U6).
- **LOD screen sizes must be set after import.** An FBX LodGroup carries no thresholds; for statics Unreal computed
  2.0 / 0.75 / 0.5625 and the mesh sat on its lowest LOD [M, `SM_Katana.sockets.json` note]. The fan's skeletal LODs
  were imported as LODs of one mesh with screen sizes from the sidecar [M, FAN_REPORT section 4].
- **Bounds:** a folding stock or a deployed bipod moves outside the bind-pose box. Do what the fan did: write a
  posed-envelope `bounds_extension_cm` to the sidecar and apply it on import [M, FAN_REPORT B-table "Bounds"].

---

## 7. Attachment system

- **Pattern:** an attachment is a **static** mesh (`SM_Att_<Type>_<Name>`). The game attaches it to a weapon socket
  (`Rail_*`, `Muzzle`, `Stock`, `Mag`) with an optional slot offset along the rail. Every Fab modular pack read works
  this way: swappable barrels, stocks, magazines, sights and grips [E][9][10][12][13][14]. Plugins such as
  AttachmentSync key attachments by gameplay tag on sockets [E][21].
- **Override sockets on the attachment itself [J]:**
  - Optics carry `Sight`, the eye line through the reticle. ADS uses the highest-priority `Sight` that is present.
  - Muzzle devices carry `Muzzle`, so the flash moves to the suppressor's end.
  - Foregrips carry `LeftHand`, so the off-hand IK moves to the grip.
  - Bipods carry their own legs as a small skeletal attachment (`SK_Att_Bipod`) or stay part of the sniper's skeleton
    (the sniper sheet shows it fixed to the gun). Infima ships a bipod in both rigged and static versions [E][15].
- **Iron sights that fold** when an optic mounts are why `sight_front` / `sight_rear` are bones (section 3.2).
- **Materials:** attachments use the same pack masters and material instances, so one skin applies to the whole
  assembly [J; house rule: `Scripts/unreal/materials/`].
- **Scope glass and reticle:** a separate material slot. The Infima sniper advertises "edge fading, crosshairs, and
  glass" materials [E][15]. Note: Nanite allows only Opaque or Masked, so translucent lens glass is one more reason to
  keep Nanite off the optic [E][4].

---

## 8. Collision, physics and pickups

| Case | Mesh | Collision | Evidence |
|---|---|---|---|
| Gun in hand | `SK_<Gun>` (FP + TP components) | `PA_<Gun>` with **one simple body on `body`** (a box plus a capsule along the barrel), kinematic, query only | Epic `PA_Pistol` (box on `Grip`), `PA_Rifle` (capsule), `PA_GrenadeLauncher` (capsule on `Grip_Bone`) [M]. Fab requires a physics asset on skeletal meshes [M, ASSET_GUIDELINES section 7] |
| Gun dropped by a duelist (keeps its state: mag, attachments, skin) | the same `SK_<Gun>` (TP component) | `PA_<Gun>` set to simulate | the fan's `PHYS_Fan` pattern: one body, kinematic while held, simulate when dropped [M] |
| World loot / pickup (battle royale), display, Fab static users | `SM_<Gun>` | **UCX hulls** (3-6 convex: receiver, barrel/handguard, stock, magazine) keyed to the LOD0 node name | Epic template pickup is a static mesh with a physics body, and `SM_Pistol` has convex hulls [M]. The house UCX rules are measured on 5.8 [M] |
| Dropped magazine | `SM_<Gun>_Mag` | one UCX box | [J] |
| Pickup interaction | the pickup actor | a sphere or box overlap on the actor, not the mesh hulls | [J] |

`skeletal_prop.py` already writes physics bodies to the sidecar, and the fan's import rebuilds `PHYS_` from proxy FBX
files in `Exports/Fan/Physics/` [M]. The gun needs nothing new there.

---

## 9. Attaching to the hand: Lyra, Game Animation Sample, the 5.8 template, and our MetaHuman

- **Lyra:** each weapon's animation behaviour lives in a linked animation layer (`ALI_ItemAnimLayers`, base
  `ABP_ItemAnimLayersBase`, child per weapon such as `ABP_PistolAnimLayers`) [E][22]. Weapons attach at `weapon_r`
  [E][6]. The equipment definition (`WID_Pistol`) holds the attach transform [E][23]. Lyra is not installed on this PC,
  so I could not measure its weapon meshes [J].
- **Manny's IK bones:** `SKM_Manny_Simple` and the Game Animation Sample (GASP) project's `SK_Mannequin` contain `ik_hand_root`, `ik_hand_gun`,
  `ik_hand_l` and `ik_hand_r` [M]. The community method: animate `ik_hand_gun` (child of `ik_hand_root`), attach the
  weapon to it, and IK both hands to `ik_hand_l` / `ik_hand_r`. This frees hand-to-hand weapon moves, recoil and sway
  from the arms [E][24][25].
- **Game Animation Sample:** `SK_Mannequin` also holds the names `weapon_l`, `weapon_r` and `weapon_r_muzzle` next to
  its socket data [M; name table only, so socket versus virtual bone is unconfirmed].
- **Epic 5.8 FP template:** attaches at `HandGrip_R`. Its Control Rig `Ctrl_HandAdjusment` (and `_Pistol`) runs
  two-bone IK and aim-bone math over `hand_l`, `hand_r`, `ik_hand_gun`, `ik_hand_l` and `ik_hand_r`, with
  `DisableLHandIK` and `IronSight` switches [M].
- **Our player is a MetaHuman (`metahuman_base_skel`, 342 bones, no `ik_*` bones)** [M, ASSET_GUIDELINES section 7]. GASP
  and Manny animation reach it through runtime retargeting with Manny hidden as the driver [M, ASSET_GUIDELINES
  section 8].

**Recommendation [J]:**
- Add a `weapon_r` socket on the MetaHuman's `hand_r` and attach the gun's `Grip` there (Lyra's naming).
- Solve the off-hand with two-bone IK from `upperarm_l` to `hand_l`. The target is the weapon's `LeftHand` socket
  converted into `hand_r` space, so the left hand never lags the right [E][7].
- Keep the weapon asset independent of whichever hand-attach method wins. The gun only needs `Grip` and `LeftHand`.
- Whether to add `ik_hand_gun` style bones to the player rig, or read them from the hidden Manny driver, is a
  character-pipeline decision (open question Q3).

---

## 10. Gates for every gun (add to the gun spec before building)

Blender side (headless, `skeletal_prop` plus new checks):

- **B1** Skeleton: the armature object is `root`. Bone names come from section 3.2 only, with no dots. Every bone
  deforms, including an unweighted `magazine` bone, and the exported FBX still contains it. Rest rotations equal the
  root's.
- **B2** Rigid skin: exactly one influence per vertex at weight 1.0. This is a new `max_influences=1` check, since
  `skin_checks` today allows up to 4 [M].
- **B3** Motion clearance: sweep every moving bone through its range (bolt travel, trigger pull, selector arc, stock
  fold, bipod legs). Zero intersections with any other part, at LOD0 and every LOD, the way the fan proved its
  folds [M precedent].
- **B4** Sockets: every section 3.3 socket the gun's sheet calls for is present on the right bone with the right axes.
  `Muzzle` X lies on the bore axis within 0.5 mm. `Sight` X lies on the sight line through the front post.
- **B5** Mag fit: `SM_<Gun>_Mag` at the `Mag` socket overlaps the receiver by no more than the seating tolerance, and
  its UCX is one hull.
- **B6** Static twin: `SM_<Gun>` passes `qa_check` (UCX keyed to the node name, UV1, LOD triangles strictly
  descending).

Unreal side (a fresh process on the exported bytes, house rule):

- **U1** Dump the skeleton: bone names, parents and ref-pose transforms. Muzzle along +X, up +Z, right +Y. Root
  scale 1 (the fan's centimetre-copy export, measured necessary [M]).
- **U2** Procedural test: Transform Modify Bone on `bolt` by -X moves the bolt straight back, and the selector turns
  about X.
- **U3** Sockets from the sidecar exist on the right bones at scale 1 (the 100x FBX socket bug [M]).
- **U4** First person: FP + WSR components in a test pawn. The FP mesh casts no ground shadow, the WSR mesh does (with
  VSM on), and the owner does not see the WSR mesh.
- **U5** LOD screen sizes and bounds extension applied. The stock and bipod do not pop.
- **U6** (later) The Nanite flag on `SM_<Gun>` with LODs kept, compared in a 100-instance loot field.
- **U7** Physics: `PA_<Gun>` simulates and comes to rest. `SM_<Gun>` dropped from 1 m comes to rest on its hulls
  without tunnelling.

---

## 11. What Fab weapon listings advertise (read 2026-10-04)

| Listing | Price, rating | What it advertises |
|---|---|---|
| Infima, Modern Guns Bundle [8] | $149.99-199.99, 4.8 (5) | 8 rigged guns; "4K PBR textures"; Blender sources "include the full rigs and pre-made idle poses"; attachments (silencer, scope, laser, two grips); modular barrels and handguards; gun cases; example Blueprints "using the provided sockets"; third-person idle poses; UE5 Manny rig; FP and TP animation templates; UE 5.0-5.8 |
| Infima, Low Poly Animated Modern Guns [12] | from $99.99, 4.7 (105) | "All gun models are exported as skeletal meshes"; swappable barrels, slides and magazines; attachments include a bipod; 16+ materials (camo, patterns, glowing sight dots); a full FP arms animation list; warns it is on the UE4 mannequin, "not compatible with the UE5 Manny skeleton" |
| Infima, Modern Sniper Rifle [15] | free, 5.0 (1) | rigged; 3 barrel lengths; scope materials (edge fade, crosshair, glass); "Animated Bipod" (open and close), rigged and static versions; "Two Magazine Variations - With separate bullet meshes ... using the socket setup" |
| Nando Studio, Developer Weapon Kit [16] | $70.99-209.99, new | 20 skeletal meshes, 54 animations, 69 static meshes (mags, attachments, ammo, casings, projectiles); "real-world scale"; no player animations; UE 5.3-5.8 |
| Deadghost, FPS Weapon Bundle (Epic permanent free) [13] | free, 4.6 (377) | 7 weapons and 4 attachments, "rigged for animation", alternative textures for every firearm |
| AB3D, AK74 Assault Rifle (Fps-Tps) [14] | $34.99-69.99, 3.7 (3) | weapon and arm animations (ADS, hip, auto fire, reload, reload from dry, chamber); "Elements requiring animation are detached and correctly named"; "Removable logo"; UE, Unity, FBX |
| FPS AK Modular Weapons Pack [9] | 5.0 (4) | modular parts with counts (4 stocks, 6 handguards, 5 magazines...); "11 520 variations"; material floats for dirt, wear and damage per material; safety and shot animations |
| Modular Weapon Pack: Assault Rifles [10] | free, 4.4 (7) | 5 platforms, swappable barrels, 10+ stocks across all 5, drum mags, independent front and rear iron sights; Blender |
| Manifold, Tactical Gun Pack [11] | $39.99-189.99, 5.0 (1) | FP hand animations "(90 deg FOV, ADS at 70 deg)"; modular attachments; "Bones for attachments, muzzle flash, and case ejection"; calibre-specific casings; SFX; default UE skeleton |
| Weapon IMPACT [26] | free, 4.7 (3) | clips Fire, BarrelFire, TriggerFire, ReloadMag (pump on the shotgun); 4 texture sets per weapon; 512 / 1K / 2K |

**Pattern [J]:**
- The baseline is a rigged skeletal gun plus static parts and magazines.
- The headline features are weapon-side clips (fire, reload, safety, bolt or pump), modular parts with counts,
  several material skins or wear parameters, and 4K PBR.
- They name the skeleton they are compatible with. The UE5 Manny name is now a selling point, and UE4-only packs carry
  a warning.
- Blender sources and example Blueprints with sockets are offered as value.
- **Poly counts and texture sizes are rarely in the descriptions**, so our README and the Fab technical fields can
  stand out by stating them.
- For us, IP comes first: no real model names, no markings, and a "removable logo" is not a thing we need because we
  ship none.

---

## 12. Impact on the AR-01 rifle plan

The rifle study (`WorkFiles/guns/rifle/`) assumed static `SM_AR01` plus a separate `SM_AR01_Mag`. This study keeps
the magazine and changes the gun [J]:

1. **Add `SK_AR01`**: a rigidly skinned skeletal mesh with bones `body`, `bolt` (carrier and charging handle in one),
   `trigger`, `selector`, `mag_release`, `magazine` (the attach bone only) and `sight_rear` (ladder leaf, plus a
   slider if the sheet shows one). Add `PA_AR01` (one body on `body`), LOD0-LOD3, and sockets `Grip`, `LeftHand`,
   `Muzzle`, `ShellEject`, `Sight` and `Mag`. Add `Rail_*` only if the Fab version gets a rail (the sheet's AK
   has none).
2. **Keep `SM_AR01`** as the static twin for loot and display, with UCX and UV1, built from the same parts with the
   magazine either merged in or attached (open question Q2).
3. **Keep `SM_AR01_Mag`**, with its origin moved to the `Mag` socket frame and one UCX hull.
4. **Model for motion:** the moving parts are separate closed meshes with pivots on their real axes. The receiver's
   charging-handle slot and the ejection port are real cuts the full bolt travel long, and the selector lever clears
   the slot over its arc. These change the modelling, not just the export, so they must be in the build plan before
   geometry starts.
5. **Export path:** `skeletal_prop.export_skeletal_set` (the centimetre copy, one FBX per LOD and per clip) for
   `SK_AR01`, and the static pipeline for `SM_AR01` and `SM_AR01_Mag`. The sidecar carries sockets, physics, LOD sizes
   and bounds extension.
6. **Clips (if we author weapon-side animation):** `A_AR01_Fire` (bolt cycle, trigger), `A_AR01_Charge`,
   `A_AR01_Reload` / `A_AR01_ReloadEmpty` (mag bone path, section 4 pattern 1) and `A_AR01_Selector`. A procedural bolt
   kick in the weapon ABP can replace the per-shot fire clip for automatic fire [J].

The same template carries straight to the SMG next: add `charging_handle`, `stock` (hinge fold) and the folding-stock
bounds extension.

---

## 13. Open questions only the user can answer

- **Q1** Who makes the character reload, fire and ADS animations: bought packs (they come with their own guns'
  weapon clips and expect their own bone names), our own Blender work, or procedural only? This decides whether
  weapon-side clips are worth authoring, and which reload pattern from section 4 we standardise.
- **Q2** Should the static twin `SM_<Gun>` include the magazine merged in (simplest loot), or always attach
  `SM_<Gun>_Mag` (allows drum or extended mags on ground loot)?
- **Q3** Hand attach on the MetaHuman player: a plain `weapon_r` socket on `hand_r` plus two-bone IK (recommended), or
  add Manny-style `ik_hand_root` / `ik_hand_gun` bones to the player rig?
- **Q4** Are the game's views true first person (body visible) and third person, with the FP rendering feature
  (deferred, VSM, no static lighting)? Confirm that DemoGame_1 can turn off Allow Static Lighting.
- **Q5** Fab versions: animated (weapon clips plus a compatibility statement for UE5 Manny) or "rigged,
  animation-ready" only? This sets price band and workload.
- **Q6** Rails on the Fab versions: one shared rail standard across the line (the backlog suggests yes), including
  guns whose reference has none (the AK-style rifle)?

---

## 14. Sources

1. Epic, First Person Rendering (UE 5.8). https://dev.epicgames.com/documentation/en-us/unreal-engine/first-person-rendering
2. Epic, Blueprint API: Transform World to First Person. https://dev.epicgames.com/documentation/unreal-engine/BlueprintAPI/Camera/TransformWorldtoFirstPerson?lang=en-US
3. Infima Games docs, How to replace the weapon with a custom model in UE5 (Blender to UE5). https://docs.infimagames.com/product/tactical-fps-animation-packs/guides-and-tutorials/editor/how-to-replace-the-weapon-with-a-custom-model-in-unreal-engine-5-blender-to-ue5
4. Epic, Nanite Virtualized Geometry (5.8 page; skeletal mesh section). https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine
5. Epic, UDK Setting Up Weapons. https://docs.unrealengine.com/udk/Three/SettingUpWeapons.html
6. Epic forums, Problem with weapon rotation on custom animation with Lyra (weapons attach to `Weapon_r`). https://forums.unrealengine.com/t/problem-with-weapon-rotation-on-custom-animation-with-lyra/1841283
7. Zaggoth, UE4 Tutorial: The Right Way to Do Left-Hand Weapon IK. https://zaggoth.wordpress.com/2019/01/26/ue4-tutorial-the-right-way-to-do-left-hand-weapon-ik/
8. Fab, Infima Games, Modern Guns Bundle - Rigged & Game Ready Models. https://www.fab.com/listings/eb4258b3-cec4-4995-85fe-ace8c9b5d45f
9. Fab, FPS AK Modular Weapons Pack (HQ soviet assault rifles). https://www.fab.com/listings/98e6e4cd-4589-4cff-a392-ce0c4fda3c34
10. Fab, Modular Weapon Pack: Assault Rifles. https://www.fab.com/listings/38ff34af-76cc-42fc-bde5-e975ac2631c6
11. Fab, Tactical Gun PACK: Pistol, Assault Rifle & SMG with Attachments & FP Animations. https://www.fab.com/listings/5eacefd6-79cf-40a5-924a-7cce66e99838
12. Fab, Infima Games, Low Poly Animated - Modern Guns Pack. https://www.fab.com/listings/6914a185-4b14-475c-8f4f-cc0a6a3c589f
13. Fab, FPS Weapon Bundle (Deadghost, Epic permanent collection). https://www.fab.com/listings/8aeb9c48-b404-4dcd-9e56-1d0ecedba7f5 ; marketplace text "All weapons have a static mesh and a rigged skeletal mesh", UE Marketplace FPS Weapon Pack (search summary): https://www.unrealengine.com/marketplace/en-US/item-detail/40d1f3ab15944a6db997e7e528bb4805
14. Fab, AK74 Assault Rifle (Fps - Tps). https://www.fab.com/listings/06cdc435-e96f-4d77-91fb-6f9bf26bcf15
15. Fab, Infima Games, Modern Sniper Rifle - Rigged & Game Ready Model. https://www.fab.com/listings/6d872a60-fbd2-48f0-9df6-16a385519dbb
16. Fab, Nando Studio, Developer Weapon Kit - Starter Pack. https://www.fab.com/listings/6e9c4979-d31c-492f-b76c-f3b2b889a52c
17. nanos world docs, Weapons Meshes. https://docs.nanos-world.com/docs/assets-modding/creating-assets/skeletal-meshes/weapons-meshes
18. Call of Duty modding: Steam guide "Call of Duty Weapon Porting Guide" https://steamcommunity.com/sharedfiles/filedetails/?id=384822367 ; CoD4 ViewModels wiki https://wiki.zeroy.com/index.php?title=Call_of_Duty_4:_ViewModels
19. Epic forums, spawning or attaching a magazine through anim notifies. https://forums.unrealengine.com/t/how-can-i-spawn-a-second-gun-magazine-to-my-double-reload-anim-through-anim-notifies/1392383 ; Unreal X-Editor, Weapon Magazine Reload tutorial https://unrealxeditor.wordpress.com/2012/10/02/tutorial-weapon-magazine-reload/
20. Polycount, First Person Perspective Camera with World Model? https://polycount.com/discussion/145654/first-person-perspective-camera-with-world-model ; Sahil Dhanju, Render first-person meshes with a separate FOV https://sahildhanju.com/posts/render-first-person-fov/
21. Fab, Attachment Sync plugin. https://www.fab.com/listings/2ebc4fbe-24c8-41bf-9db5-7e134d4fbd2c
22. Epic, Animation in Lyra Sample Game. https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-in-lyra-sample-game-in-unreal-engine
23. Epic forums, Misplaced weapon socket in Lyra custom character (`WID_Pistol` attach transform). https://forums.unrealengine.com/t/misplaced-weapon-socket-in-lyra-custom-character/765566
24. Epic forums, Unable to fix Lyra weapon attachment on IK-retargeted actor (`ik_hand_gun` / `ik_hand_root` roles, retarget modes). https://forums.unrealengine.com/t/unable-to-fix-lyra-weapon-attachment-on-ik-retargeted-actor/2269752
25. Dev_Unallocated, Procedural Weapon Animations Condensed (weapon on `ik_hand_gun`, ADS pivot on the sight). https://www.devunallocated.com/projects/project-killhouse/procedural-weapon-animations-condensed
26. Fab, Weapon IMPACT - Animated Gun Bundle. https://www.fab.com/listings/d8a6c0a4-d3ff-4379-98ba-5971ab17cafe

**Measured on this PC [M]:**
- `C:/Program Files/Epic Games/UE_5.8/Engine/Source/Runtime/Engine/Classes/Components/PrimitiveComponent.h` (lines
  150-161, 495-497, 566-621, 728-730)
- `.../Classes/Camera/CameraComponent.h` (lines 49-60, 207-217)
- `.../Engine/Private/Rendering/NaniteResources.cpp` (`r.Nanite.AllowSkinnedMeshes` = 1)
- `.../Classes/Engine/SkeletalMesh.h` line 964
- `Engine/Shaders/Private/Nanite/NaniteCullingCommon.ush` line 211
- `C:/Program Files/Epic Games/UE_5.8/Templates/TemplateResources/Standard/Weapons/Content/{Rifle,Pistol,GrenadeLauncher}/Meshes/{SKM_,SK_,PA_,SM_}*.uasset`
  and `.../Variant_Shooter/Content/{Blueprints/Pickups,Anims}/*.uasset` (name tables)
- `C:/Users/Cody/Documents/Unreal Projects/GameAnimationSample/Content/Characters/UE5_Mannequins/Meshes/{SK_Mannequin,SKM_Manny_Simple}.uasset`
  (name tables)
- Repo: `Scripts/pipeline/skeletal_prop.py`, `Exports/Fan/README.md`, `WorkFiles/fan/FAN_REPORT.md`,
  `Exports/Katana/SM_Katana.sockets.json`, `ASSET_GUIDELINES.md` sections 1, 2, 4, 7 and 8, `FAB_ASSET_STUDY.md`
  line 478
