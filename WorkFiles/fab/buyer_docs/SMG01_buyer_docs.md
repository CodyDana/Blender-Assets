<!-- Buyer documentation draft generated 2026-10-16 by the Batch API from the shipped docs; review before publishing. -->

# Compact SMG SM-01: Documentation

**Product code:** `SMG01` · **Engine:** Unreal Engine 5.8 (verified on 5.8.3) · **Version:** 1.0

---

## 1. Overview

The Compact SMG SM-01 is a compact submachine gun game asset with a polymer frame, a side-folding skeleton stock, folding iron sights and a straight 25-round polymer magazine. It is built for first- and third-person use.

The gun is a rigged skeletal mesh with eight weapon animations. Its bolt, charging handle, trigger, selector, magazine release, magazine, stock and both sights all move. A static version is included for pickups and world props, and the magazine is a separate mesh you can swap during reloads. The gun has no names, markings or logos anywhere.

---

## 2. What's included

### 2.1 Meshes

| Asset | Type | LOD0 / LOD1 / LOD2 / LOD3 triangles | Collision | Sockets |
|---|---|---|---|---|
| `SK_SMG01` | Skeletal mesh, rigged (magazine not included) | 48,236 / 23,832 / 8,844 / 1,420 | Physics asset `PHYS_SMG01` | 21 |
| `SM_SMG01` | Static mesh, stock extended, magazine merged in | 52,536 / 25,252 / 9,532 / 1,444 | 8 convex hulls (`UCX_SM_SMG01_LOD0_00`..`07`) | 21 |
| `SM_SMG01_Mag` | Static mesh, removable magazine | 4,300 / 1,420 / 688 / 24 | 1 convex hull (`UCX_SM_SMG01_Mag_LOD0_00`) | 5 |

At every LOD, `SM_SMG01_Mag` is the same mesh as the magazine merged into `SM_SMG01`.

### 2.2 Skeleton

`SK_SMG01_Skeleton` has `root` plus 11 bones:

| Bone | Moves in |
|---|---|
| `body` | (main body) |
| `bolt` | Fire, Charge, ReloadEmpty |
| `charging_handle` | Charge, ReloadEmpty |
| `trigger` | Fire |
| `selector` | Selector. Fire, Charge and ReloadEmpty hold it at Auto |
| `mag_release` | Reload, ReloadEmpty |
| `magazine` | Reload, ReloadEmpty |
| `stock` | StockFold, StockUnfold |
| `sight_rear`, `sight_front` | SightFlip |
| `muzzle_device` | (static) |

### 2.3 Animations (weapon-side clips)

| Clip | What it shows | Frame rate | Frames |
|---|---|---|---|
| `A_SMG01_Fire` | One shot: the trigger breaks, and the bolt runs to the rear stop and back | 60 fps | 6 |
| `A_SMG01_Charge` | The charging handle pushes the bolt to the rear stop, then both run forward | 30 fps | 22 |
| `A_SMG01_Reload` | The paddle is pressed, the magazine comes straight out and drops, and a new one goes straight in | 30 fps | 55 |
| `A_SMG01_ReloadEmpty` | Starts with the bolt held open: the reload, then a charge that releases the bolt | 30 fps | 80 |
| `A_SMG01_Selector` | Semi, Safe, Semi, Auto, Semi | 30 fps | 30 |
| `A_SMG01_StockFold` | The stock swings 180° to the gun's right side and ends folded | 30 fps | 24 |
| `A_SMG01_StockUnfold` | The stock starts folded and swings back to extended | 30 fps | 24 |
| `A_SMG01_SightFlip` | Both sights fold flat and come back up | 30 fps | 20 |

### 2.4 Materials

| Material slot | Instance | Master | Covers |
|---|---|---|---|
| `M_SMG01_Metal` | `MI_SMG01_Metal` | `M_Steel_Master` | Phosphate-finish steel: rails, sights, barrel and nut, muzzle device, bolt, charging handle, selector, trigger, release paddle, pins, hinge pin |
| `M_SMG01_Furniture` | `MI_SMG01_Furniture` | `M_Fabric_Master` | Black polymer: receiver shells, grip frame and stippled cover, magwell, skeleton stock, butt pad and latch |
| `M_SMG01_Mag` | `MI_SMG01_Mag` | `M_Fabric_Master` | Black polymer magazine: body, floor plate, follower |

Each instance has a parent `MI_SMG01_<Part>_Base`, which holds the textures and matched settings. The instance on the mesh overrides only the colour, so **Reset to default** always brings back the shipped look.

### 2.5 Textures

| Set | Size | Maps | Covers |
|---|---|---|---|
| Metal | 2048 | `T_SMG01_Metal_BC`, `_ORM`, `_N`, `_Masks` | Steel parts |
| Furniture | 4096 | `T_SMG01_Furniture_BC`, `_ORM`, `_N`, `_Masks`, plus `T_SMG01_Furniture_Detail16` (2048) | Polymer body parts |
| Mag | 1024 | `T_SMG01_Mag_BC`, `_ORM`, `_N`, `_Masks`, plus `T_SMG01_Mag_Detail16` (1024) | Magazine |

- **Masks:** the `_Masks` maps are half the size of their set.
- **Map format:** all maps are square powers of two. Normal maps use the DirectX convention and are stored as 16-bit PNG.
- **Memory:** the whole set uses 81.0 MiB in Unreal, with mips, at the settings in section 4.5.

### 2.6 Data files (sidecars)

| File | Contents |
|---|---|
| `SK_SMG01.skeletal.json` | Bones, sockets, LOD sizes, import settings, notifies, physics bodies, materials, mass, centre of mass, stock-fold data |
| `SM_SMG01.sockets.json` | Sockets and LOD screen sizes for `SM_SMG01` |
| `SM_SMG01_Mag.sockets.json` | Sockets and LOD screen sizes for `SM_SMG01_Mag` |
| `Physics/SK_SMG01_PhysicsProxy.fbx` | A helper mesh used to rebuild `PHYS_SMG01` (not a render mesh) |
| `Textures/Recolour/recolour_maps.json`, `recolour_constants.json` | The matched recolour settings |

### 2.7 FBX files

`SK_SMG01.fbx`, `SK_SMG01_LOD1.fbx`, `SK_SMG01_LOD2.fbx`, `SK_SMG01_LOD3.fbx`, the eight `A_SMG01_*.fbx` clips, `SM_SMG01.fbx`, `SM_SMG01_Mag.fbx` and `Physics/SK_SMG01_PhysicsProxy.fbx`.

### 2.8 Key dimensions

| Item | Value |
|---|---|
| Overall length, stock extended | 625 mm |
| Overall length, stock folded | 383.6 mm |
| Bolt and charging-handle travel | 67.9 mm |
| Selector detents | Safe −63.4° / Semi 0° / Auto +45° |
| Trigger travel | 0–13° |
| Magazine release travel | 0 to −11° |
| Mass (physics) | 2.5 kg |

---

## 3. Requirements

- **Unreal Engine 5.8.** Imports were verified on 5.8.3. No other engine version has been tested.
- **No plugins** are needed for the content.
- **First-person rendering (optional).** The first-person component setup in section 5.5 uses the UE 5.8 First Person rendering features (*First Person Primitive Type*). It does not require any project setting for the content to load or render.

---

## 4. Import and setup (Unreal Engine 5.8)

Follow these steps in order. The values are the ones used when the asset was verified in Unreal.

### 4.1 Skeletal mesh

1. Import `SK_SMG01.fbx` with these settings:
   - **Normal Import Method: Import Normals**
   - **Convert Scene: on**
   - **Force Front X Axis: off**
   - **Create Physics Asset: off.** You build `PHYS_SMG01` in step 4.4.
2. Import `SK_SMG01_LOD1.fbx`, `SK_SMG01_LOD2.fbx` and `SK_SMG01_LOD3.fbx` as LODs 1–3 of `SK_SMG01`:
   - In the Skeletal Mesh Editor, use **LOD Settings > LOD Import > Import LOD Level N**.
   - All LODs share the skeleton and the root. Do not remove bones from any LOD.
3. Set the LOD screen sizes to **1.0 / 0.28612 / 0.06082 / 0.03777**. These switch LODs at about 2.3 m, 11.0 m and 17.7 m.
4. Set the mesh's **bounds extension**:
   - **Positive Bounds Extension: (0, 24.752, 0.257) cm**
   - **Negative Bounds Extension: (0.749, 0, 0) cm**

   Unreal uses the unfolded shape for the mesh bounds, but the folded stock swings 24.9 cm past it to the right. With this extension, every vertex stays inside the bounds on every frame of every clip, in both stock states and with the sights folded.

### 4.2 Animation clips

1. Import the eight `A_SMG01_*.fbx` files onto `SK_SMG01_Skeleton`:
   - Keep each clip at its own frame rate (section 2.3).
   - Set **Use T0 As Ref Pose: off**.
2. Open each clip and set **Bone Compression Settings** to `/Engine/Animation/DefaultRecorderBoneCompression`.

   The project default moves the rigid parts by about 1 mm, which opens visible gaps between parts.
3. Add the notifies by hand. The FBX files do not carry them. For each row, right-click the notify track at the listed frame and choose *Add Notify > New Notify*, using the name shown:

| Clip | Notify (frame) |
|---|---|
| `A_SMG01_Fire` | `Fire` 1, `ShellEject` 3 (bolt at the rear stop), `TriggerReset` 6 |
| `A_SMG01_Charge` | `ChargeRear` 10, `BoltRelease` 14 |
| `A_SMG01_Reload` | `MagRelease` 2, `MagOut` 10, `MagDrop` 17, `MagIn` 48 |
| `A_SMG01_ReloadEmpty` | `MagRelease` 2, `MagOut` 10, `MagDrop` 17, `MagIn` 48, `ChargeRear` 67, `BoltRelease` 71 |
| `A_SMG01_StockFold` | `StockUnlock` 1, `StockLocked` 24 |
| `A_SMG01_StockUnfold` | `StockUnlock` 1, `StockLocked` 24 |

The same frames are listed under `notifies` in `SK_SMG01.skeletal.json`.

### 4.3 Static meshes

1. Import `SM_SMG01.fbx` and `SM_SMG01_Mag.fbx` with these settings:
   - **Import Mesh LODs: on**, so the four LODs arrive as LODs and are not merged
   - **Normal Import Method: Import Normals**
   - **Convert Scene: on**, **Force Front X Axis: off**
   - **Auto Generate Collision: off**
   - **One Convex Hull Per UCX: on**
   - **Generate Lightmap UVs: off**
2. Set the LOD screen sizes:
   - `SM_SMG01`: **1.0 / 0.25 / 0.05314 / 0.033**
   - `SM_SMG01_Mag`: **1.0 / 0.08465 / 0.01799 / 0.01117**

   The magazine's sizes are derived from the gun's, so a magazine attached to the gun switches LODs together with it.
3. **Lightmaps.** Every LOD carries an authored lightmap UV in UV channel 1, with no overlaps at 64 and 128 px. Use it for static lighting. Do not use lightmap resolutions above 128.

### 4.4 Sockets

Unreal 5.8 does not keep FBX sockets from a file that contains a LOD group, so you create the sockets yourself from the JSON sidecars. Locations are in centimetres, rotations are Unreal rotators, and scale is 1.

**Skeletal mesh (21 sockets, from `SK_SMG01.skeletal.json`):**

1. Open `SK_SMG01_Skeleton` in the Skeleton Editor.
2. For each socket in the sidecar, right-click the bone it lists and choose **Add Socket**.
3. Rename the socket exactly as in the sidecar.
4. Enter its relative location and rotation.

**Static meshes (from `SM_SMG01.sockets.json` and `SM_SMG01_Mag.sockets.json`):**

1. Open the mesh in the Static Mesh Editor and open the **Socket Manager**.
2. For each socket in the sidecar, click **Create Socket**.
3. Rename it exactly as in the sidecar.
4. Enter its relative location, rotation and scale (1, 1, 1).

To script this instead, run Unreal's Python API in the editor. `unreal.new_object(unreal.StaticMeshSocket, outer=mesh)` creates a static-mesh socket; set its name and transform from the sidecar.

### 4.5 Textures

Keep full mip chains on every map.

| Map | sRGB | Compression | Notes |
|---|---|---|---|
| `T_SMG01_Metal_BC` | On | Default (BC1) | |
| `T_SMG01_Furniture_BC`, `T_SMG01_Mag_BC` | On | **BC7** | BC7 keeps the dark wear within 2 levels of the source; BC1 drifts 5–8 levels |
| `T_SMG01_*_ORM` | Off | Masks | No alpha. R = ambient occlusion, G = roughness, B = metallic |
| `T_SMG01_*_N` | n/a | Normalmap | DirectX convention. Leave **Flip Green Channel off** |
| `T_SMG01_Furniture_Detail16`, `T_SMG01_Mag_Detail16` | Off | Grayscale (G16) | Used by the polymer recolour |
| `T_SMG01_*_Masks` | Off | Masks | Not used by the included materials. For your own dirt or wear layer: R edge-wear propensity, G handling, B cavity, A refinishable |

- **Optional ORM setting:** set each ORM's **Composite Texture** to the matching normal map, with *Normal Roughness To Green* at power 1. Distant mips then get rougher where the normals vary, which reduces specular shimmer.
- **Address mode:** keep it on **Wrap** (the default). On `SM_SMG01`, each material slot's UVs sit in their own UV tile: Metal 0..1, Furniture 1..2 and Mag −1..0.
- **Texture groups (in a game):** use `Weapon` for BC, ORM and Detail16, and `WeaponNormalMap` for N.

### 4.6 Materials

Assign the instances by slot name:

| Mesh | Slot 0 | Slot 1 | Slot 2 |
|---|---|---|---|
| `SK_SMG01` | `MI_SMG01_Metal` | `MI_SMG01_Furniture` | n/a |
| `SM_SMG01` | `MI_SMG01_Metal` | `MI_SMG01_Furniture` | `MI_SMG01_Mag` |
| `SM_SMG01_Mag` | `MI_SMG01_Mag` | n/a | n/a |

### 4.7 Physics asset (`PHYS_SMG01`)

`PHYS_SMG01` has one body, on the `body` bone, with a 2.5 kg mass override. The body is made of the shapes listed under `physics_bodies` in `SK_SMG01.skeletal.json`:

- **8 collision shapes**
- **1 bounds-envelope box with no collision and no mass**

The envelope matters because a skeletal mesh with physics bodies takes its bounds from the physics asset. Without the envelope, a dropped gun with the stock folded would sit partly outside its own bounds and pick LODs on the wrong radius.

To build it:

1. Import `Physics/SK_SMG01_PhysicsProxy.fbx` onto `SK_SMG01_Skeleton` with **Create Physics Asset: on**. This creates exactly one body, on `body`.
2. Open the new physics asset and select the `body` body. Delete its generated shapes.
3. Add the shapes from the sidecar's `physics_bodies` one by one, with the type, position, rotation and size listed for each.
4. Set each shape's collision and mass flags as the sidecar lists them. For the envelope box, set collision to **No Collision** and turn **Contribute To Mass** off.
5. On the body, set **Mass Override** to **2.5 kg**.
6. Rename the asset to `PHYS_SMG01` and assign it to `SK_SMG01` (*Physics Asset* in the Skeletal Mesh Editor).
7. Delete the proxy mesh. It is only used to build the body.

---

## 5. How to use

### 5.1 Sockets

`SK_SMG01` and `SM_SMG01` have 21 sockets each:

| Socket | Notes |
|---|---|
| `Grip` | Primary hand position. The offset comes from a hand fit made in Blender (see section 6) |
| `SupportHand` | Support hand position. Also from the Blender hand fit |
| `Trigger`, `Selector`, `MagRelease`, `ChargingHandle` | At the matching controls |
| `Muzzle`, `MuzzleSeat` | At the muzzle device |
| `Sight`, `SightFront` | Rear and front sights |
| `Mag` | The magazine attaches here with a zero relative transform |
| `MagInsertStart` | 68.2 mm below the magazine seat; the start of the reload path |
| `ShellEject` | Matches the `ShellEject` notify in `A_SMG01_Fire` |
| `Rail_Top`, `Rail_Bottom` | Top and bottom accessory rails (1913-profile) |
| `Stock`, `Shoulder`, `SlingFront`, `SlingRear` | `Shoulder` and `SlingRear` are on the `stock` bone, so they follow the fold |
| `CenterOfMass` | Centre of mass with the stock extended |
| `Holster` | |

`SM_SMG01_Mag` has 5 sockets; their names and transforms are in `SM_SMG01_Mag.sockets.json`.

### 5.2 Magazine and reloads

- **Attaching:** `SM_SMG01_Mag` snaps to the `Mag` socket with a zero relative transform.
- **Reload path:** the path is **straight**. The magazine moves from `MagInsertStart` to `Mag` along its −Z axis, with constant rotation (no rocking).
- **In the clips:** `A_SMG01_Reload` and `A_SMG01_ReloadEmpty` move the `magazine` bone along this path. A magazine attached to that bone follows it.
- **Hand-held magazine:** if the magazine moves to the character's hand (for example `hand_l`), copy the weapon clip's `MagOut` and `MagIn` frames into your character montage.

### 5.3 Selector

- **Default position:** the bind pose and `SM_SMG01` show the selector on **Semi (0°)**. The detents are Safe −63.4° and Auto +45°.
- **Bolt clips:** `A_SMG01_Fire`, `A_SMG01_Charge` and `A_SMG01_ReloadEmpty` hold the selector at **Auto** for the whole clip. The reload and stock clips keep it on Semi.
- **Showing the player's fire mode:** in your weapon Anim Blueprint, use **Layered blend per bone** on the `selector` branch, with a pose taken from `A_SMG01_Selector`.

### 5.4 Stock and sights

- **Folding the stock:** the stock folds 180° about its hinge to lie along the gun's right side, where a moulded lug clips under the ejection-port catch. Play `A_SMG01_StockFold` / `A_SMG01_StockUnfold`.
- **Holding it folded:** hold the last frame of `A_SMG01_StockFold`. `SM_SMG01` is always the extended state.
- **Centre of mass:** with the stock folded it moves from 47.5 / 0.7 / 83.1 mm to **100.0 / −10.0 / 83.1 mm**, measured from the `body` origin.
- **Sights:** `A_SMG01_SightFlip` folds both sights flat and raises them again.

### 5.5 First person and third person

Use two components per weapon and two per magazine:

| Component | Mesh | Setting |
|---|---|---|
| `FP_Weapon` | `SK_SMG01` | *First Person Primitive Type* = **FirstPerson**, **Forced LOD Model = 1** (always LOD0) |
| `TP_Weapon` | `SK_SMG01` | Normal LOD switching |
| `FP_Mag` | `SM_SMG01_Mag`, on the `Mag` socket | *First Person Primitive Type* = **FirstPerson**, **Forced LOD Model = 1** |
| `TP_Mag` | `SM_SMG01_Mag`, on the `Mag` socket | Normal LOD switching |

First-person components cast no world shadow and stay on LOD0.

### 5.6 Collision in hand and dropped

- **In hand:** while the gun and magazine are attached to a character, set their components to **No Collision** (or a query-only weapon profile) and turn **Simulate Physics off**. This stops them pushing the character's capsule.
- **Dropped or world pickup:** turn collision and physics on. Use `SM_SMG01`, or `SK_SMG01` with `PHYS_SMG01`. Both rest correctly with the stock extended or folded.

### 5.7 Colours

**Recolourable: the polymer** (furniture and magazine), as one group.

1. Open `MI_SMG01_Furniture` and `MI_SMG01_Mag`. For a variant, duplicate both and put the copies on their slots:
   - slot 1 of `SK_SMG01` and `SM_SMG01`
   - slot 2 of `SM_SMG01`
   - slot 0 of `SM_SMG01_Mag`
2. In group **01 Colour**, tick the override of **Use Original Baked Colours** and set it **off** on both.
3. Set the same **Colour** on both, then save.

How the polymer colour behaves:

- **Colour sets the overall look.** It is the average colour of the polymer, so the gun reads as the colour you pick. The moulded texture, grip stipple, polish and whitening all follow it.
- **Light colours are capped** at **Lightest Colour** (0.6), so the highlights keep their detail.
- **Pure black is lifted slightly** (to about sRGB 25), so the texture stays visible.
- **Fine wear is softer.** With baked colours off, the finest wear specks look softer than in the shipped look.
- **Undo:** turning **Use Original Baked Colours** back on, or using *Reset to default*, returns to the shipped look.
- **Leave groups 08 Advanced and 09 Textures alone.** They are matched to the maps.

**Metal:** the phosphate finish is baked and is not designed to be recoloured. **Steel Tint** (white = as shipped) multiplies the base colour, for example to warm or grey the finish slightly. A strong tint also colours the bare-steel worn edges.

---

## 6. Known limitations

- **Only weapon-side animations are included.** There are no character, arms or hand animations, and no audio, VFX or gameplay Blueprints.
- **The FBX files carry no notifies.** Add them by hand from section 4.2.
- **Static-mesh sockets must be recreated by hand** from the sidecars (section 4.4).
- **The physics asset must be built by hand** from the proxy and the sidecar (section 4.7).
- **Hand fit:** the `Grip` and `SupportHand` positions were fitted on a human character in Blender only. They have not been tested on a character in Unreal.
- **Not tested:**
  - a complete in-game first-person weapon Blueprint, including owner-only visibility of the two components
  - mobile platforms
  - Nanite (all checks were done with Nanite off)
- **Lightmaps:** the authored lightmap UV is clean at 64 and 128 px. At 1024 px it shows 17–22 overlapping pixels on `SM_SMG01` LOD0–2, so do not use resolutions above 128.
- **Recolour limits:** the finest wear is softer with baked colours off, very light colours are capped, and pure black is lifted slightly (section 5.7). The metal only accepts a tint.
- **Magazine texture streaming:** the 1024 maps of the separate magazine stream at 512 at hip distance, which is Unreal's own choice.
- **No markings:** there are no markings, selector letters, serials or logos anywhere, by design.

---

## 7. FAQ

**Which Unreal versions are supported?**
Unreal Engine 5.8. Imports were verified on 5.8.3. Other versions have not been tested.

**Are character or arms animations included?**
No. The eight clips animate the gun's own parts. Notifies such as `MagOut` and `MagIn` give you the frames for syncing your character montages.

**Some parts look slightly apart or misaligned during the clips. Why?**
The clips are using the project's default bone compression. Set each clip's compression to `/Engine/Animation/DefaultRecorderBoneCompression` (section 4.2).

**The gun pops or disappears at the edge of the screen when the stock is folded. Why?**
The bounds extension or the physics envelope box is missing. Set the bounds extension from section 4.1, and make sure `PHYS_SMG01` includes the no-collision, no-mass envelope box (section 4.7).

**Where did the sockets go after import?**
Unreal 5.8 drops FBX sockets from files with LOD groups. Recreate them from the `.json` sidecars (section 4.4).

**How do I make a tan or green version?**
Duplicate `MI_SMG01_Furniture` and `MI_SMG01_Mag`, set **Use Original Baked Colours** off on both, and set the same **Colour** on both (section 5.7).

**Why does the selector show Auto in the firing clips?**
A gun set to Safe cannot fire, so the bolt clips hold Auto. To show the real fire mode, blend the `selector` bone from a pose of `A_SMG01_Selector` (section 5.3).

**I re-imported a clip in Blender and the selector rests at Auto. Is that a bug?**
No, and Unreal is not affected. Blender's FBX exporter writes each bone's pose at a clip's first frame as its default, and Blender's importer reads that as the rest pose. In Blender, read the clip's absolute bone matrices (`pose.bones[...].matrix`).

---

## 8. Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-10-16 | Initial release |

---
---

## Internal notes (not for the documentation page)

### Before publishing

1. **Close-up realism not passed.** Both realism judges call every close view fake. The listed tells are:
   - one grey for all materials
   - the stock head reads as a sheet, and the hinge as a bare cylinder
   - the ball charging knob
   - the rail teeth
   - the receiver step, grooves and pins
   - speckled wear

   Whether to run another geometry and material round is the user's decision.
2. **Design distance.** The line study says Fab versions get original design changes. The report describes the SMG as following a real construction family, with small parts matched to real photos. No SMG-specific design changes are listed (the seven listed are for the rifle). Define and apply them before sale.
3. **Firearms category rule.** Fab wants "all expected moving parts rigged and a full set of anim


*(Internal notes truncated at the generation limit; see WorkFiles/fab/listing_drafts/SMG01_fab_listing_draft.md for the full pre-publishing checklist.)*
