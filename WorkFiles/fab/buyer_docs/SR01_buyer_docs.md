<!-- Buyer documentation draft generated 2026-10-16 by the Batch API from the shipped docs; review before publishing. -->

# Sniper Rifle SR-01: Documentation

*Version 1.0 · 2026-10-16 · Unreal Engine 5.8*

---

## 1. Overview

The Sniper Rifle SR-01 is a game-ready bolt-action precision rifle prop. It has an olive-drab painted chassis, an adjustable cheek riser, a folding, extending and canting bipod, a detachable 10-round box magazine and a separate long-range scope.

- **Rigged rifle.** The skeletal mesh moves its bolt, trigger, safety, magazine release, magazine, cheek riser and bipod. Eight weapon-side animation clips drive them.
- **Static twin.** A static version is included for pickups and world props.
- **Markings.** The rifle carries generic markings only: "S" and "F" at the safety. There are no names, serials or logos.

---

## 2. What's included

### 2.1 Meshes

| Asset | Type | LODs | Triangles per LOD (LOD0 / 1 / 2 / 3) | Collision | Sockets |
|---|---|---|---|---|---|
| `SK_SR01` | Skeletal mesh (rifle without scope and magazine) | 4 | 44,224 / 19,872 / 6,588 / 2,502 | Physics asset `PHYS_SR01` (rebuilt from the included proxy, see 4.6) | 20 |
| `SM_SR01` | Static mesh (static twin: bipod folded, magazine merged in) | 4 | 45,102 / 20,266 / 6,734 / 2,560 | 10 convex hulls | 20 |
| `SM_SR01_Mag` | Static mesh (removable 10-round magazine) | 4 | 878 / 394 / 146 / 58 | 1 convex hull | 5 |
| `SM_Att_Scope_LongRange` | Static mesh (long-range scope with rings) | 3 | 9,938 / 4,464 / 1,454 | 3 convex hulls | 5 |
| `SK_SR01_PhysicsProxy` | Helper mesh, used only to rebuild `PHYS_SR01` | n/a | n/a | n/a | n/a |

**Skeleton and mesh settings**

- **Skeleton:** `SK_SR01_Skeleton` has a `root` bone plus 13 rigid bones: `body`, `bolt`, `trigger`, `selector`, `mag_release`, `magazine`, `muzzle_device`, `cheek_riser`, `bipod`, `bipod_leg_l`, `bipod_leg_l_ext`, `bipod_leg_r`, `bipod_leg_r_ext`. Each vertex has one influence.
- **Collision hulls:** every hull has 32 vertices or fewer.
- **Nanite:** off on every mesh.
- **Lightmap UVs:** authored on UV channel 1, with Lightmap Coordinate Index 1.

### 2.2 Animation clips (on `SK_SR01_Skeleton`)

| Clip | Frame rate | Frames | What happens |
|---|---|---|---|
| `A_SR01_Fire` | 60 fps | 8 | The trigger breaks and resets; the bolt does not move |
| `A_SR01_BoltCycle` | 30 fps | 30 | The bolt lifts 60°, runs 88 mm back, holds, runs forward and turns down |
| `A_SR01_Reload` | 30 fps | 60 | The paddle is pressed and the magazine goes straight out and drops; a new one goes straight in and the catch snaps |
| `A_SR01_ReloadEmpty` | 30 fps | 90 | Starts with the bolt open, does the reload, then closes the bolt (forward and down) |
| `A_SR01_Selector` | 30 fps | 20 | Safety: Fire, Safe, Fire |
| `A_SR01_BipodDeploy` | 30 fps | 36 | The legs swing down (the left leads by 2 frames) and extend 38 mm |
| `A_SR01_BipodStow` | 30 fps | 36 | The reverse of Deploy, ending at the rest pose |
| `A_SR01_CheekRiser` | 30 fps | 24 | Optional: the riser goes up 12 mm, down to -12.9 mm and back |

### 2.3 Texture sets

Each set has four maps: BaseColor (`_BC`), packed occlusion/roughness/metallic (`_ORM`), Normal (`_N`) and `_Masks` (half size). There are 21 maps in total.

| Texture set | Size (BC / ORM / N) | Masks | Covers |
|---|---|---|---|
| `T_SR01_Metal_*` | 2048 | 1024 | Steel parts: receiver, 15-slot rail, fluted barrel and compensator, bolt and handle, trigger, safety, release paddle, pins and screws |
| `T_SR01_Chassis_*` | 4096 | 2048 | The olive-drab painted chassis, forend, butt and cheek riser; the black anodized bipod and hardware; the polymer grip; the rubber butt pad |
| `T_SR01_Mag_*` | 1024 | 512 | The magazine: phosphated steel body and polymer parts |
| `T_Att_Scope_LongRange_Scope_Body_*` | 2048 | 1024 | The scope tube, rings, turrets (generic tick and numeral markings), eyepiece and objective bell |
| `T_Att_Scope_LongRange_Scope_Lens_*` | 512 | 256 | The lenses: opaque, glossy, with a coated look |
| `Recolour/T_SR01_Chassis_Detail16` | 2048 (16-bit) | n/a | Detail map for a future paint recolour (see 5.8) |

### 2.4 Material slots

| Slot | Used by | Texture set |
|---|---|---|
| `M_SR01_Metal` | Slot 0 on `SK_SR01` and `SM_SR01` | Metal |
| `M_SR01_Chassis` | Slot 1 on `SK_SR01` and `SM_SR01` | Chassis |
| `M_SR01_Mag` | Slot 2 on `SM_SR01`, slot 0 on `SM_SR01_Mag` | Mag |
| `M_Att_Scope_Body` | Slot 0 on the scope | Scope Body |
| `M_Att_Scope_Lens` | Slot 1 on the scope | Scope Lens |

**Material instances**

| Instance | Parent material |
|---|---|
| `MI_SR01_Metal` | `M_Steel_Master` |
| `MI_SR01_Chassis` | `M_Fabric_Master` (baked colours on) |
| `MI_SR01_Mag` | `M_Steel_Master` |
| `MI_Att_Scope_LongRange_Body` | `M_Steel_Master` |
| `MI_Att_Scope_LongRange_Lens` | `M_Steel_Master` |

- Each instance has a matching `_Base` instance that holds the textures and settings.
- The instance on the mesh overrides only its colour. Use *Reset to Default* to get back the shipped look.

### 2.5 Data files

- **`SK_SR01.skeletal.json`:** bones, the 20 sockets, LOD sizes, import settings, the bounds extension, the notify frames, physics bodies, materials, masses and the bone angle table.
- **`SM_SR01.sockets.json`, `SM_SR01_Mag.sockets.json` and `SM_Att_Scope_LongRange.sockets.json`:** each static mesh's sockets and LOD screen sizes.
- **`Recolour/recolour_maps.json` and `Recolour/recolour_constants.json`:** data for the paint recolour.

---

## 3. Requirements

- **Engine:** Unreal Engine 5.8, verified in 5.8.3.
- **Plugins:** no third-party plugins are required.
- **First-person setup (optional):** the first-person pattern in 5.6 uses Unreal Engine 5.8's built-in First Person rendering (*First Person Primitive Type*). It is a usage instruction, not a dependency of the content.
- **Importer:** the import steps below were verified with Unreal's legacy FBX importer.

---

## 4. Import and setup (Unreal Engine 5.8)

### 4.1 Units and axes

- **Source frame:** millimetres, +X toward the muzzle, +Z up and +Y to the gun's left. The bolt handle is on the right.
- **Unreal conversion:** Unreal positions are in centimetres with Y flipped: (X, -Y, Z) / 10.
- **Sidecar values:** the JSON files give values in both frames. Use the `location_cm` and `unreal_rotation_deg` fields in Unreal.
- **Origin:** the `Grip` socket, on the grip axis.
- **Overall length:** 1,100 mm.

### 4.2 Skeletal rifle (`SK_SR01`)

1. **Import `SK_SR01.fbx`** with these settings:
   - Normal Import Method: **Import Normals**
   - *Convert Scene*: on
   - *Force Front X Axis*: off
   - *Import Mesh LODs*: on
   - *Create Physics Asset*: **off** (you build it in 4.6)
2. **Add LOD1-3.** In the Skeletal Mesh editor, import `SK_SR01_LOD1.fbx`, `SK_SR01_LOD2.fbx` and `SK_SR01_LOD3.fbx` as LOD 1, 2 and 3 of `SK_SR01`, on the same skeleton. Do not remove any bones.
3. **Set the LOD screen sizes** to the values listed in `SK_SR01.skeletal.json`. The verified values are **1 / 0.273 / 0.0886 / 0.0361**.
4. **Set the bounds extension** on `SK_SR01` (Skeletal Mesh editor, *Positive / Negative Bounds Extension*):
   - Positive: (0, 8.681, 2.31) cm
   - Negative: (0, 12.877, 18.386) cm

   The values are also in `import.bounds_extension_cm` in the sidecar. They keep the deployed bipod, the open bolt and the raised riser inside the bounds at every frame. Do not shrink them.
5. **Lightmaps:** *Generate Lightmap UVs* off. UV channel 1 is authored, with Lightmap Coordinate Index 1.

### 4.3 Animation clips

1. **Import the eight `A_SR01_*.fbx` files** onto `SK_SR01_Skeleton`:
   - Import each clip at its own frame rate (see 2.2).
   - Set *Use T0 As Ref Pose* off.
2. **Set the bone compression.** In each clip, set *Bone Compression Settings* to **`/Engine/Animation/DefaultRecorderBoneCompression`**. The project default compression moves the rigid parts by about 1 mm. With this setting, the runtime poses match the authored clips exactly.
3. **Add the notifies by hand.** The FBX files carry no notifies. Add these at the listed frames (they are also in the sidecar's `notifies`):

| Clip | Notify (frame) |
|---|---|
| `A_SR01_Fire` | `Fire` 2, `TriggerReset` 8 |
| `A_SR01_BoltCycle` | `BoltUnlock` 1, `ShellEject` 13, `BoltForward` 16, `BoltLock` 30 |
| `A_SR01_Reload` | `MagRelease` 2, `MagOut` 9, `MagDrop` 18, `MagIn` 50 |
| `A_SR01_ReloadEmpty` | `MagRelease` 2, `MagOut` 9, `MagDrop` 18, `MagIn` 50, `BoltForward` 62, `BoltLock` 76 |
| `A_SR01_BipodDeploy` | `BipodLegOut_L` 10, `BipodLegOut_R` 12, `BipodLocked` 30 |
| `A_SR01_BipodStow` | `BipodRetracted` 14, `BipodStowed` 32 |

### 4.4 Static meshes (`SM_SR01`, `SM_SR01_Mag`, `SM_Att_Scope_LongRange`)

1. **Import each FBX** with these settings:
   - Normal Import Method: **Import Normals**
   - *Convert Scene*: on
   - *Force Front X Axis*: off
   - *Import Mesh LODs*: on
   - *Auto Generate Collision*: **off**
   - *One Convex Hull per UCX*: **on**
   - *Generate Lightmap UVs*: off (UV1 is authored; index 1)
   - Nanite: off

   The hulls import automatically from the `UCX_` meshes in the file.
2. **Set the LOD screen sizes** from each mesh's `.sockets.json`:
   - `SM_SR01`: 1.0 / 0.25 / 0.06561 / 0.033
   - `SM_SR01_Mag`: 1.0 / 0.03448 / 0.00905 / 0.00455
   - `SM_Att_Scope_LongRange`: 1.0 / 0.09516 / 0.02497
3. **Add the sockets by hand.** Unreal Engine 5.8 drops the FBX sockets of any file that contains a LOD group, so recreate them from the sidecar.

### 4.5 Adding sockets from the sidecar files

**Static meshes**

1. Open the static mesh and its `.sockets.json` in a text editor.
2. In the Static Mesh editor, open the **Socket Manager** (Window > Socket Manager).
3. For each socket in the JSON:
   1. Click *Create Socket* and give it exactly the name in the file.
   2. Set *Relative Location* to the socket's `location_cm` values.
   3. Set *Relative Rotation* to its `unreal_rotation_deg` values.
   4. Set *Relative Scale* to (1, 1, 1).
4. Save the mesh.

**Skeletal mesh (`SK_SR01`)**

1. Open the Skeleton editor for `SK_SR01_Skeleton`.
2. For each of the 20 sockets in `SK_SR01.skeletal.json`:
   1. Right-click the socket's bone and choose *Add Socket*.
   2. Rename it.
   3. Enter the `location_cm` and `unreal_rotation_deg` values.

### 4.6 Physics asset (`PHYS_SR01`)

`PHYS_SR01` is one body on the `body` bone, at 5.9 kg. It is built from:

- 7 boxes: the butt, grip, action, trigger guard, magazine well, the forend with the clamp, and the folded bipod.
- 1 capsule: the barrel.
- 1 bounds-envelope box with **no collision and no mass**. A skeletal component takes its bounds from the physics asset, so this box keeps the deployed bipod and the open bolt inside the bounds.

**Steps**

1. **Import the proxy.** Import `Physics/SK_SR01_PhysicsProxy.fbx` onto `SK_SR01_Skeleton` with *Create Physics Asset* **on**. This creates one body on `body`.
2. **Replace the shapes.** In the Physics Asset editor, replace that body's shapes with the ones listed under `physics_bodies` in `SK_SR01.skeletal.json`. Enter each shape's position, rotation and size, and keep each element's collision and mass flags exactly as listed. The envelope box must have collision off and must not contribute mass.
3. **Set the mass.** Set the body's mass override to 5.9 kg.
4. **Finish up.** Rename the asset `PHYS_SR01`, assign it to `SK_SR01` and delete the proxy mesh.

### 4.7 Textures

| Map | sRGB | Compression | Notes |
|---|---|---|---|
| `*_BC` | On | Metal and scope: Default (BC1). Chassis and Mag: **BC7** | |
| `*_ORM` | Off | Masks | R = ambient occlusion, G = roughness, B = metallic. Optional: set *Composite Texture* to the set's normal map (*Normal Roughness To Green*, power 1) to reduce specular shimmer at distance |
| `*_N` | Off | Normal map | **DirectX** convention. *Flip Green Channel*: **off**. 16-bit source |
| `*_Masks` | Off | Masks | Not used by the included materials; for your own wear or dirt layers (see 5.8) |
| `Recolour/T_SR01_Chassis_Detail16` | Off | Grayscale | Builds as G16 (lossless) |

- **Format:** every map is a square power of two. Keep the full mip chains (the 4096 maps have 13 mips).
- **Texture groups (suggested):** use `Weapon` for BC, ORM and Detail16. Use a weapon normal-map group for N.
- **UV tiles:** `SM_SR01` places each material's UV0 in its own U tile (Metal 0-1, Chassis 1-2, merged magazine -1-0). The scope places its Body in tile 0-1 and its Lens in tile 1-2. Keep texture addressing on **Wrap** (the default).

### 4.8 Without the included material instances

Any standard PBR material works with these connections:

- BaseColor = BC
- Ambient Occlusion / Roughness / Metallic = ORM R / G / B
- Normal = N

---

## 5. How to use

### 5.1 Sockets on the rifle (`SK_SR01`; also on `SM_SR01`)

| Socket | Bone | Use |
|---|---|---|
| `Grip` | body | The origin, on the grip axis. The firing-hand attach point |
| `SupportHand` | body | The forend belly behind the bipod clamp. The off-hand point (see Known limitations) |
| `SupportHandBipod` | body | The off hand under the butt when prone (see Known limitations) |
| `Trigger` | trigger | The trigger face |
| `Selector` | selector | The safety lever tip |
| `MagRelease` | mag_release | The release paddle |
| `BoltHandle` | bolt | The bolt knob centre: the hand target for the bolt cycle |
| `Muzzle` | muzzle_device | The muzzle face (for muzzle effects) |
| `MuzzleSeat` | body | Where a muzzle device seats |
| `ShellEject` | body | The ejection port centre. +X is the throw direction (right, up, slightly back) |
| `Mag` | magazine | The magazine well entry. The magazine snaps here |
| `MagInsertStart` | body | 67.8 mm straight below `Mag`. The start of the insert path |
| `Rail_Top` | body | The centre of rail slot 0 of 15 |
| `SlingFront` / `SlingRear` | body | The front of the bipod clamp, and the sling cup on the left of the butt |
| `Shoulder` | body | The butt-pad rear centre |
| `CenterOfMass` | body | 200.2 / -0.3 / 68.7 mm from the origin (bipod folded) |
| `Holster` | body | At the same position as `CenterOfMass` |
| `BipodFoot_L` / `BipodFoot_R` | bipod_leg_*_ext | The foot end faces: the ground contacts when deployed |

On the static twin, `BipodFoot_*` are at the folded positions.

**Magazine sockets:** `Mag`, `Feed`, `Base`, `HandReload`, `CenterOfMass`.

**Scope sockets:** see 5.5.

### 5.2 Moving parts and their ranges

All ranges are measured from the rest pose. The angle table in the sidecar (`abp_angle_table`) lists them for use in an Animation Blueprint.

| Bone | Motion |
|---|---|
| `bolt` | Rotates about X from 0 to -60°, then slides -X from 0 to 88 mm. It only slides at -60° and only turns at 0° |
| `trigger` | Rotates about Y from 0 to +6° |
| `selector` | Rotates about Y: Fire 0° (rest), Safe -12° |
| `mag_release` | Rotates about Y from 0 to -4.5° |
| `magazine` | Carries the magazine along the reload path. Attach `SM_SR01_Mag` here |
| `cheek_riser` | Translates Z from -12.9 to +12.0 mm |
| `bipod` | Cant: rotates about X from -15° to +15° (0 in every clip) |
| `bipod_leg_l` / `bipod_leg_r` | Rotate from 0° (folded forward) to +90° (deployed down) about the leg pin. The pins are rolled 12° outward, so a deployed leg leans 12° out |
| `bipod_leg_l_ext` / `bipod_leg_r_ext` | Translate +X in the leg's rest frame from 0 to 76 mm, with detents every 19 mm |

### 5.3 Clip behaviour

- **Bolt action.** `A_SR01_Fire` does not cycle the bolt. Chain `Fire` into `BoltCycle` in your game logic, or skip the bolt cycle if you prefer.
- **Safety.** `Fire`, `BoltCycle` and `ReloadEmpty` hold the safety at Fire.
- **Start and end poses.** Every clip starts and ends at the rest pose, except these three:
  - `A_SR01_ReloadEmpty` starts with the bolt open.
  - `A_SR01_BipodDeploy` ends deployed.
  - `A_SR01_BipodStow` starts deployed at 38 mm extension.

### 5.4 Magazine and reloads

- **Attach.** Attach `SM_SR01_Mag` to the `Mag` socket with a zero relative transform (*Snap To Target*). On the rifle's skeleton, the `magazine` bone carries this socket, so the magazine follows `A_SR01_Reload` automatically.
- **Path.** The reload path is **straight**: from `MagInsertStart` (67.8 mm below the seat) up to `Mag`, along +Z, with the rotation constant.
- **Hand-held magazine.** To hold the magazine in the character's hand (`hand_l`, using the magazine's `HandReload` socket), copy the clip's `MagOut` and `MagIn` notify frames to your character montage.
- **Release catch.** The catch is spring-loaded: the magazine pushes it back and it snaps into the notch.
- **Static twin.** `SM_SR01` has the magazine merged in. At every LOD, the separate magazine is the same mesh as the merged one.

### 5.5 Scope attachment (`SM_Att_Scope_LongRange`)

- **Attach.** Place the scope's origin (its `Mount` point, on the rail-top plane) on the rifle's `Rail_Top` socket **+ 2 slots: X +2.002 cm** (20.02 mm), with zero rotation.
  - `Rail_Top` is the centre of slot 0.
  - Slot k is at +k × 10.01 mm.
- **Aim sockets.** The rifle has no iron sights, so the scope's sockets are the aim sockets:

| Socket | Use |
|---|---|
| `Sight` | The scope axis at the eyepiece face, 57.6 mm above the bore and parallel to it |
| `EyePoint` | 95 mm behind `Sight`, over the cheek riser. **Place the aim-down-sights camera here** |
| `Lens_Front` | The objective face |
| `CenterOfMass` | The scope's centre of mass |

- **No zero is built in.** At 10 m, the bore sits 5.76 cm below the scope axis. Apply your game's own zero.
- **Clearance.** The bolt knob clears the mounted scope by 29.9 mm over the whole bolt cycle.
- **Lenses.** The lenses are opaque, not transparent. A magnified scope view needs your own material or render target.

### 5.6 First-person and third-person components

Use two components per part:

| Components | Mesh | Attach to |
|---|---|---|
| `FP_Weapon`, `TP_Weapon` | `SK_SR01` | The hand |
| `FP_Mag`, `TP_Mag` | `SM_SR01_Mag` | The `Mag` socket |
| `FP_Scope`, `TP_Scope` | `SM_Att_Scope_LongRange` | `Rail_Top` + 2 slots |

- **First-person components:** set *First Person Primitive Type* = **FirstPerson** and *Forced LOD Model* = **1** (always LOD0).
- **Third-person components:** keep normal LOD switching.
- **Shadows:** the third-person components cast the ground shadow; the first-person components cast none.
- **Draw calls:** the held rifle with magazine and scope costs 10 draw calls with both first- and third-person components.
- **Hiding the third-person components from the owning player** is set up in your own weapon Blueprint.

### 5.7 The bipod

- **Deploy and stow.** Play `A_SR01_BipodDeploy` (legs 0° to 90°, then extension 0 to 38 mm) and `A_SR01_BipodStow` (the reverse). The legs are independent, with detents at 0° and 90°.
- **Extension and ground height.** The extension runs from 0 to 76 mm in five detents. This table gives the ground height below the bore at each detent, with both legs deployed and no cant:

| Extension (mm) | 0 | 19 | 38 | 57 | 76 |
|---|---|---|---|---|---|
| Ground below the bore (mm) | 266.7 | 285.3 | 303.9 | 322.5 | 341.1 |

- **Prone placement.** Set both legs to 90°, then pick each leg's extension so that `BipodFoot_L` and `BipodFoot_R` reach the ground. Each leg is a single value; there is no IK chain. The rear rests on `SupportHandBipod` or on your own rear support.
- **Cant.** Rotate the `bipod` bone about X up to ±15°, folded or deployed.
- **Physics.** `PHYS_SR01` uses the folded pose. Fold the legs (play `BipodStow`, or snap them to 0) before dropping the gun. While the gun is held, the deployed legs are kinematic.
- **Deployed world prop.** `SM_SR01` has the bipod folded. For a deployed prop, use `SK_SR01` posed at the last frame of `A_SR01_BipodDeploy`.

### 5.8 Collision and mass in play

**While the gun is held:** set the rifle, magazine and scope components to *No Collision* (or a query-only weapon profile) with *Simulate Physics* off, so they never push the character capsule. Turn collision and physics on only for a dropped gun or a world pickup.

**Masses**

| Part | Mass |
|---|---|
| Rifle (bipod included, no scope or magazine) | 5.9 kg |
| Magazine, empty | 0.20 kg |
| Magazine, with 10 rounds | 0.45 kg |
| Scope | 1.15 kg |
| Ready to fire | about 7.5 kg |

### 5.9 Colours: what is baked and what you can tint

- **As shipped.** Everything ships with its baked colours: the olive-drab paint (with wear, chips and handling polish), the black anodize, the polymer grip, the rubber pad, the steel, the magazine and the scope.
- **Steel, magazine and scope.** These materials have one colour control, **Steel Tint**. White is the shipped look, and other colours multiply the base colour. The worn bare-steel edges come from the metallic channel, so a strong tint also colours them.
- **Chassis paint.** Leave *Use Original Baked Colours* **on** in the chassis material. The chassis texture set also holds the bipod, the grip and the butt pad. Turning the setting off would tint all of them, not just the paint.
- **Your own paint colour.** In your own material, lerp between the BC and your tinted colour, using **Masks A** as the mask. A = 1 only on the olive-drab paint.
- **`_Masks` channels:**

| Channel | Meaning |
|---|---|
| R | Edge-wear propensity (convex edges and corners) |
| G | Handling wear (where hands and gear rub) |
| B | Cavity (recesses that collect dust) |
| A | Repaintable: 1 only on the olive-drab paint, 0 everywhere else |

---

## 6. Known limitations

- **Animation.** The clips are weapon-side only. No character, arms or hand animations or poses are included.
- **Audio and effects.** No sounds, muzzle effects or shell casings are included. The `Muzzle` and `ShellEject` sockets and the notifies mark where your own go.
- **Hand placement.** `Grip`, `SupportHand` and `SupportHandBipod` are **provisional**. They have not been tested with a character hand pose in Unreal, so expect to adjust them for your characters.
  - The `SupportHand` position can be far forward for a square-on stance.
  - A typical firing-hand pose may need its own thumb placement on the grip.
- **Scope.** The lenses are opaque, and no scope-view material or render target is included. No zero is built in.
- **Recolour.** Only the steel, magazine and scope can be tinted, using Steel Tint. The olive-drab paint ships baked; to repaint it, use the Masks A method in 5.9.
- **Owner-only visibility.** Hiding the third-person components from the owning player is your game's Blueprint work.
- **Static twin.** `SM_SR01` is posed with the bipod folded only.
- **Nanite.** Nanite is off on all meshes.
- **Physics.** The physics asset assumes the folded bipod.

---

## 7. FAQ

**Which Unreal Engine version does it support?**
Unreal Engine 5.8. It was verified in 5.8.3.

**Does it include character, hand or arms animations?**
No. The eight clips move the rifle's own parts: fire, bolt cycle, reload, empty reload, safety, bipod deploy and stow, and the cheek riser. Use the sockets and notifies to sync them with your own character animations.

**Why does the rifle not cycle its bolt when it fires?**
It is a bolt-action rifle. `A_SR01_Fire` only breaks and resets the trigger. Play `A_SR01_BoltCycle` afterwards, or skip it if your game does not need it.

**Why do the parts drift slightly during animation?**
The clips are probably using the project's default animation compression. Set every clip's bone compression to `/Engine/Animation/DefaultRecorderBoneCompression`; the parts then match the authored clips exactly.

**My static meshes imported without sockets. Is something missing?**
No. Unreal 5.8 drops FBX sockets from files that contain LODs. Recreate them from the `.sockets.json` files (see 4.5).

**Where do I put the aim-down-sights camera?**
On the scope's `EyePoint` socket, with the scope mounted at `Rail_Top` + 2 slots (+2.002 cm in X). There are no iron sights.

**Can I change the rifle's colour?**
You can tint the steel, magazine and scope with Steel Tint. The olive-drab paint ships baked; to repaint it in your own material, blend over the BC using the Masks texture's A channel (see 5.9).

**Can I use it for commercial projects?**
Yes. Both the Personal and Professional licences allow commercial use.

---

## 8. Changelog

- **v1.0 (2026-10-16):** first release.

---
---

# Before publishing (internal; not for the buyer page)

**Blockers**

1. **Design distance.** The blind test picked the source design in 14 of 14 pairs. The gun study requires original design deltas for Fab versions, and none are documented for SR-01. It is not sellable until deltas


*(Internal notes truncated at the generation limit; see WorkFiles/fab/listing_drafts/SR01_fab_listing_draft.md for the full pre-publishing checklist.)*
