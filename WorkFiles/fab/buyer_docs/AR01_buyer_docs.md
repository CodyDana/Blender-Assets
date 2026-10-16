<!-- Buyer documentation draft generated 2026-10-16 by the Batch API from the shipped docs; review before publishing. -->

# Assault Rifle AR-01: Documentation

**Version 1.0 · Unreal Engine 5.8**

---

## 1. Overview

The Assault Rifle AR-01 is a game-ready rifle with a stamped-steel receiver and walnut furniture, built for first- and third-person use. It ships as a rigged skeletal mesh with moving parts: bolt and carrier, trigger, selector, magazine catch, rear sight and magazine. Five weapon animation clips are included. A static twin covers pickups and world props, and the magazine is a separate mesh that you swap during reloads. The rifle carries no names, markings, serial numbers or logos.

---

## 2. What's included

### 2.1 Meshes

| Asset | Type | LODs | Triangles (LOD0 / LOD1 / LOD2 / LOD3) | Collision |
|---|---|---|---|---|
| `SK_AR01` | Skeletal mesh (magazine not included) | 4 | 48,386 / 22,462 / 8,450 / 1,076 | Physics asset `PHYS_AR01` (one body, 3.1 kg) |
| `SM_AR01` | Static mesh, magazine merged in | 4 | 55,052 / 24,460 / 9,098 / 1,324 | 7 convex hulls `UCX_SM_AR01_LOD0_00..06` |
| `SM_AR01_Mag` | Static mesh, removable magazine | 4 | 6,666 / 1,998 / 648 / 248 | 2 convex hulls `UCX_SM_AR01_Mag_LOD0_00..01` |

- The magazine merged into `SM_AR01` is the same mesh as `SM_AR01_Mag` at every LOD.
- Nanite: not used. The meshes were imported and checked with Nanite off.
- Triangle counts in Unreal are slightly lower for the static meshes (see Known limitations).

### 2.2 Skeleton

`SK_AR01_Skeleton` has `root` plus 8 bones:

| Bone | Moves |
|---|---|
| `body` | The rifle body; carries the physics body |
| `bolt` | Bolt carrier and charging handle |
| `trigger` | Trigger |
| `selector` | Selector lever (Safe / Auto / Semi) |
| `mag_release` | Magazine catch |
| `magazine` | Magazine (reload path) |
| `sight_rear` | Rear sight |
| `muzzle_device` | Muzzle device |

### 2.3 Animation clips

These are weapon-side clips on `SK_AR01_Skeleton`. They do not include character animations.

| Clip | What it does | Frame rate | Frames |
|---|---|---|---|
| `A_AR01_Fire` | One shot: the trigger breaks, the carrier runs to the rear stop and back | 60 fps | 8 |
| `A_AR01_Charge` | Charging handle pulled to the rear stop, held, released | 30 fps | 22 |
| `A_AR01_Reload` | Catch pressed, magazine rocked out, dropped, a new one rocked in | 30 fps | 60 |
| `A_AR01_ReloadEmpty` | The reload, followed by a charge | 30 fps | 84 |
| `A_AR01_Selector` | Safe, then Auto, then Semi, then back to Safe | 30 fps | 30 |

### 2.4 Sockets

| Mesh | Sockets |
|---|---|
| `SK_AR01` | 17 (listed in section 5.1) |
| `SM_AR01` | 17 |
| `SM_AR01_Mag` | 5 |

### 2.5 Textures

All maps are square powers of two with full mip chains.

| Set | Size | Maps | Covers |
|---|---|---|---|
| `T_AR01_Metal_*` | 4096 | BC, ORM, N, Masks | Receiver, cover, sights, barrel, gas system, bolt and carrier, small parts |
| `T_AR01_Furniture_*` | 2048 | BC, ORM, N, Masks | Stock, pistol grip, both handguards |
| `T_AR01_Mag_*` | 1024 | BC, ORM, N, Masks | The magazine |
| `T_AR01_Furniture_Detail16` | 1024 | Grayscale detail | Detail map for the walnut recolour |

- **BC:** base colour.
- **ORM:** R ambient occlusion, G roughness, B metallic.
- **N:** DirectX-convention normal map, 16-bit PNG.
- **Masks:** half the set's size (2048 / 1024 / 512). R edge wear, G handling, B cavity, A refinishable. The included materials do not use them. They are provided for your own dirt or wear layer.

### 2.6 Materials

| Instance | Master | Used on |
|---|---|---|
| `MI_AR01_Metal` | `M_Steel_Master` | Slot 0 of `SK_AR01` and `SM_AR01` |
| `MI_AR01_Furniture` | `M_Fabric_Master` | Slot 1 of `SK_AR01` and `SM_AR01` |
| `MI_AR01_Mag` | `M_Steel_Master` | Slot 2 of `SM_AR01`, slot 0 of `SM_AR01_Mag` |

Each instance has a parent `MI_AR01_<Part>_Base` that holds the textures and matched settings.

### 2.7 FBX and data files

| File | Purpose |
|---|---|
| `SK_AR01.fbx`, `SK_AR01_LOD1.fbx`, `SK_AR01_LOD2.fbx`, `SK_AR01_LOD3.fbx` | Skeletal mesh, LOD0 to LOD3 |
| `A_AR01_Fire.fbx`, `A_AR01_Charge.fbx`, `A_AR01_Reload.fbx`, `A_AR01_ReloadEmpty.fbx`, `A_AR01_Selector.fbx` | The five clips |
| `SM_AR01.fbx`, `SM_AR01_Mag.fbx` | Static meshes with LODs and hulls |
| `SK_AR01.skeletal.json` | Bones, sockets, LOD sizes, import settings, notifies, physics bodies, mass |
| `SM_AR01.sockets.json`, `SM_AR01_Mag.sockets.json` | Static-mesh sockets and LOD screen sizes |
| `Physics/SK_AR01_PhysicsProxy.fbx` | Helper mesh for rebuilding `PHYS_AR01`. It is not a render mesh |
| `Textures/Recolour/` | Walnut Detail16 map, `recolour_maps.json`, `recolour_constants.json` (the matched recolour settings) |

---

## 3. Requirements

- **Unreal Engine 5.8.** Tested in 5.8.3.
- **First-person use:** Unreal Engine 5.8 First Person rendering, set per component (section 5.5).

---

## 4. Import and setup (Unreal Engine 5.8)

Skip the FBX import steps if you use the included Unreal project. The material, texture, socket and notify notes still apply.

### 4.1 Skeletal mesh

1. Import `SK_AR01.fbx` with these settings:
   - **Normal Import Method:** Import Normals
   - **Convert Scene:** on
   - **Force Front X Axis:** off
   - **Create Physics Asset:** off (you build `PHYS_AR01` in 4.5)
2. Add the LODs.
   1. Open `SK_AR01` in the Skeletal Mesh Editor.
   2. Import `SK_AR01_LOD1.fbx`, `_LOD2.fbx` and `_LOD3.fbx` as LOD1, LOD2 and LOD3. They share the skeleton and root. Do not remove any bones.
   3. Set the LOD screen sizes to **1.0 / 0.30 / 0.12 / 0.04**.
3. Set the bounds.
   1. In the mesh details, set **Negative Bounds Extension** to **(0, 0.378, 0) cm**.
   2. Leave Positive Bounds Extension at 0.

   With these values, every vertex of every LOD stays inside the bounds on every frame of every clip.

### 4.2 Animation clips

1. Import the five `A_AR01_*.fbx` clips onto `SK_AR01_Skeleton`.
   - Each clip keeps its own frame rate (see 2.3).
   - Set **Use T0 As Ref Pose** to off.
2. Set the bone compression of every clip to **`/Engine/Animation/DefaultRecorderBoneCompression`**. The project default compression moves rigid parts by about 1 mm, which opens visible gaps between parts.
3. Add the notifies. The FBX files carry no notifies, so add them at these frames:

| Clip | Notify (frame) |
|---|---|
| `A_AR01_Fire` | `Fire` 1, `ShellEject` 3 (carrier at the rear stop), `TriggerReset` 8 |
| `A_AR01_Charge` | `ChargeRear` 12, `BoltRelease` 18 |
| `A_AR01_Reload` | `MagRelease` 2, `MagOut` 15, `MagDrop` 20, `MagIn` 53 |
| `A_AR01_ReloadEmpty` | Same as Reload, then `ChargeRear` 74, `BoltRelease` 80 |
| `A_AR01_Selector` | `SelectorAuto` 4, `SelectorSemi` 12, `SelectorAuto` 22, `SelectorSafe` 28 |

The same list is under `notifies` in `SK_AR01.skeletal.json`.

### 4.3 Static meshes

1. Import `SM_AR01.fbx` and `SM_AR01_Mag.fbx` with these settings:
   - **Normal Import Method:** Import Normals
   - **Convert Scene:** on
   - **Force Front X Axis:** off
   - **Import Mesh LODs:** on
   - **One Convex Hull per UCX:** on
   - **Auto Generate Collision:** off
2. Set each mesh's LOD screen sizes from its `.sockets.json` file.

### 4.4 Sockets

The FBX files do not bring the sockets in for you:
- Skeletal sockets must be recreated from the sidecar.
- Unreal 5.8 drops the FBX sockets of any static mesh file that contains a LOD group.

Recreate them from the JSON files. Locations are in centimetres; rotations are Unreal rotators.

**Skeletal (`SK_AR01.skeletal.json`):**
1. Open `SK_AR01_Skeleton` in the Skeleton Editor.
2. For each of the 17 sockets, right-click the bone named in the JSON and choose **Add Socket**.
3. Rename the socket to the JSON name.
4. Enter its Relative Location and Relative Rotation. Leave scale at 1.

**Static (`SM_AR01.sockets.json`, `SM_AR01_Mag.sockets.json`):**
1. Open the mesh in the Static Mesh Editor and open the **Socket Manager**.
2. For each entry, click **Create Socket**, then set its name, Relative Location and Relative Rotation from the JSON.

If you prefer to script it, `unreal.new_object(unreal.StaticMeshSocket, outer=mesh)` creates a static-mesh socket in Unreal's Python API.

### 4.5 Physics asset (`PHYS_AR01`)

1. Import `Physics/SK_AR01_PhysicsProxy.fbx` onto `SK_AR01_Skeleton` with **Create Physics Asset** on. This creates exactly one body, on `body`.
2. Open the new physics asset and delete that body's generated shapes.
3. Add each shape listed under `physics_bodies` in `SK_AR01.skeletal.json`, using the type, position, rotation and size given there.
4. Set the body's mass override to **3.1 kg**.
5. Rename the asset to `PHYS_AR01` and assign it to `SK_AR01` (mesh details, Physics Asset).
6. Delete the proxy skeletal mesh. You only needed it to create the body.

### 4.6 Textures

| Map | sRGB | Compression | Notes |
|---|---|---|---|
| `T_AR01_Metal_BC`, `T_AR01_Mag_BC` | On | Default (BC1) | |
| `T_AR01_Furniture_BC` | On | **BC7** | The shipped wood shows this map directly. BC7 keeps the grain about three times closer to the source than BC1 |
| `T_AR01_*_ORM` | Off | Masks | No alpha. Set the composite texture to the set's normal map (*Normal Roughness To Green*, power 1) to reduce specular shimmer at distance |
| `T_AR01_*_N` | Off | Normalmap | DirectX convention; *Flip Green Channel* off |
| `T_AR01_Furniture_Detail16` | Off | Grayscale | Builds as G16 (lossless) |
| `T_AR01_*_Masks` | Off | Masks | Not used by the included materials |

- Keep full mip chains on every map.
- Keep address mode on **Wrap** (the default). On `SM_AR01`, each material slot's UVs sit in their own U tile:

  | Slot | U tile |
  |---|---|
  | Metal | 0..1 |
  | Furniture | 1..2 |
  | Mag | −1..0 |

  Wrap makes every tile read the right texels. `SK_AR01` keeps every set in 0..1.
- **Texture groups (recommended):**
  - `Weapon` for BC, ORM and Detail16
  - `WeaponNormalMap` for N

  With these groups, every map stayed at its top mip both at the hip and when aiming down sights.

### 4.7 Materials

Assign the instances by slot name:

| Slot | Instance |
|---|---|
| `M_AR01_Metal` | `MI_AR01_Metal` |
| `M_AR01_Furniture` | `MI_AR01_Furniture` |
| `M_AR01_Mag` | `MI_AR01_Mag` |

`SK_AR01.skeletal.json` also contains a `materials` block. No import step uses it, so follow the table in section 2.6.

---

## 5. How to use

### 5.1 Sockets on `SK_AR01`

| Socket | Use |
|---|---|
| `Grip` | Firing-hand placement (provisional offset, see Known limitations) |
| `SupportHand` | Support-hand placement (provisional) |
| `Trigger` | Trigger position |
| `Muzzle` | Muzzle position |
| `MuzzleSeat` | Muzzle-device seat |
| `Sight` | Sight position |
| `Mag` | Seated magazine. `SM_AR01_Mag` attaches here with a zero relative transform |
| `MagRockStart` | Reload path: the point where the magazine starts its rock into the well |
| `MagInsertStart` | Reload path: the start of the insert |
| `ShellEject` | Ejection position (matches the `ShellEject` notify) |
| `ChargingHandle` | Charging handle position |
| `Selector` | Selector lever position |
| `MagRelease` | Magazine catch position |
| `Shoulder` | Buttstock / shoulder contact |
| `SlingRear` | Rear sling point |
| `CenterOfMass` | Centre of mass: 163.0 / 0.1 / 74.9 mm from the `body` origin |
| `Holster` | Stowed / holster attachment point |

The bone that carries each socket, and its exact transform, are listed in `SK_AR01.skeletal.json`.

### 5.2 Magazine and reloads

- **Seated magazine:** attach `SM_AR01_Mag` to the `Mag` socket with a zero relative transform.
- **Reload path:**
  1. The magazine moves from `MagInsertStart` (lerp) to `MagRockStart`.
  2. It rotates 8 degrees about the front-lug hook into `Mag`.

  `A_AR01_Reload` and `A_AR01_ReloadEmpty` move the `magazine` bone along this path, so a magazine attached to that bone follows it.
- **Hand-held magazine** (for example on the character's `hand_l`): copy the weapon clip's `MagOut` and `MagIn` frames to your character montage, so the hand takes and returns the magazine at the right moments.

### 5.3 Selector and fire mode

- The bind pose and `SM_AR01` show the selector on **Safe**.
- `A_AR01_Fire`, `A_AR01_Charge`, `A_AR01_Reload` and `A_AR01_ReloadEmpty` hold the selector at **Auto (16 degrees)** from the first frame to the last.

To show the player's actual fire mode, override the `selector` bone in the weapon's Animation Blueprint:
1. Add a **Layered blend per bone** node with branch `selector`.
2. Feed it a pose taken from `A_AR01_Selector`:

| Mode | Frame of `A_AR01_Selector` |
|---|---|
| Safe | 0 |
| Auto | 8 |
| Semi | 18 |

### 5.4 Moving parts

- **Bolt carrier:** travels 103.25 mm. With the bolt back, the ejection port shows the open receiver and the trunnion.
- **Other parts:** trigger, selector, magazine catch, rear sight and magazine each move on their own bones (see 2.2).

### 5.5 First- and third-person setup

Use two components per weapon and two per magazine:

| Component | Mesh | Settings |
|---|---|---|
| `FP_Weapon` | `SK_AR01` | First Person Primitive Type = **FirstPerson**, **ForcedLodModel = 1** (always LOD0) |
| `TP_Weapon` | `SK_AR01` | Normal LOD switching |
| `FP_Mag` | `SM_AR01_Mag` on the `Mag` socket | First Person Primitive Type = **FirstPerson**, **ForcedLodModel = 1** |
| `TP_Mag` | `SM_AR01_Mag` on the `Mag` socket | Normal LOD switching |

With these settings, the first-person components cast no world shadow and stay on LOD0, and the third-person component switches LODs normally.

### 5.6 Collision in hand and dropped

| State | Component settings |
|---|---|
| In hand (rifle and magazine attached to a character) | **No Collision** (or a query-only weapon profile) and **Simulate Physics** off, so they never push the character's capsule |
| Dropped or world pickup | Use `SM_AR01` with its hulls, or `SK_AR01` with `PHYS_AR01`, with collision and physics on |

### 5.7 Colours

| Part | Recolourable? | Control |
|---|---|---|
| Walnut furniture | Yes | Colour |
| Metal | Tint only | Steel Tint |
| Magazine | Tint only | Steel Tint |

**Wood:**
1. Open `MI_AR01_Furniture`. For a variant, duplicate it first and put the copy on slot 1.
2. In group **01 Colour**, tick the override of **Use Original Baked Colours** and turn it **off**.
3. Pick **Colour**, then save.

How the wood colour behaves:
- **Colour** is the average colour of the furniture. The grain, pores, handling wear and checkering follow the new colour.
- The four wood pieces keep their brightness differences. Their small hue differences belong to the baked map, so after a recolour they share one hue.
- Very light colours are capped at **Lightest Colour**, so highlights keep their detail.
- Pure black is lifted slightly, so the grain stays visible.
- To go back to the shipped look, turn **Use Original Baked Colours** back on, or use *Reset to default*.
- Leave groups **08 Advanced** and **09 Textures** alone. They are matched to the maps.

**Metal and magazine:**
- **Steel Tint** multiplies the base colour, for example to warm or grey the lacquer slightly. White is the shipped look.
- The bare and blued steel come from the metallic channel, so a strong tint also colours the worn edges.

**Shared instances:** `SK_AR01` and `SM_AR01` share the Metal and Furniture instances, and `SM_AR01` and `SM_AR01_Mag` share the Mag instance. A change to a shared instance shows on every mesh that uses it. Duplicate the instance for per-weapon variants.

---

## 6. Known limitations

**Not included:**
- Character, first-person arms or hand animations.
- Audio and VFX (muzzle flash, shells, impacts).
- Gameplay code. Only the setup steps above are provided.

**Not yet tested:**
- **Hand fit:** fit on a character has not been tested. The `Grip` offset and `SupportHand` socket are provisional and may need adjusting for your character.
- **Owner-only visibility:** the visibility setup of the first-person and third-person component pair in a full weapon Blueprint has not been tested.
- **Nanite:** the meshes were imported and checked with Nanite off.
- **Mobile.**

**Recolour limits:**
- Only the wood is truly recolourable. The metal and magazine finishes are baked; Steel Tint only tints them.
- A recoloured stock and handguards share one hue (see 5.7).

**Import messages and lightmaps:**
- **Dropped triangles:** with *Remove Degenerates* on (the import default), Unreal drops very small bevel triangles (under 0.005 mm²). The drops are invisible; the dropped triangles are tiny bevel strips.

  | Mesh | Triangles dropped |
  |---|---|
  | `SM_AR01` LOD0 / LOD1 / LOD2 | 4,584 / 580 / 122 |
  | `SM_AR01_Mag` LOD0 / LOD1 | 772 / 33 |

  The skeletal import keeps them.
- **Tangent warnings:** importing the static meshes logs "nearly zero tangents / bi-normals". For `SM_AR01` it also logs "degenerate tangent bases" for a few dozen vertices.
- **Lightmap UV overlap:** *Generate Lightmap UVs* produces a lightmap UV with a few overlapping texels on `SM_AR01` LOD1 to LOD3 at the default 64 px lightmap resolution. Projects that use only dynamic lighting are not affected.

**Other:**
- **Grip checkering** is a normal map on every LOD, not cut geometry.
- **Blender re-import:** Blender's FBX importer reads a clip's first frame as the rest pose. Clips that hold the selector at Auto therefore re-import in Blender with the selector at Safe. Unreal plays the baked curves and is not affected. In Blender, read a clip's absolute bone matrices instead.

---

## 7. FAQ

**Which engine versions are supported?**
Unreal Engine 5.8. It was tested in 5.8.3.

**Does it include first-person arms or character animations?**
No. The five clips animate the rifle's own parts only. The sockets (`Grip`, `SupportHand`, `Mag`, `MagInsertStart`, `MagRockStart`) and the notifies help you sync your own character montages.

**Why does the static mesh show fewer triangles in Unreal than listed?**
Unreal's *Remove Degenerates* import option drops very small bevel triangles. The counts are in section 6. The drops are invisible.

**Can I change the colours?**
The walnut furniture is fully recolourable (section 5.7). The metal and magazine can be tinted with Steel Tint but keep their baked finish.

**Will it fit my character's hands?**
Hand fit on a character has not been tested, and the grip and support-hand positions are provisional. Expect to adjust the attachment offsets for your character.

**Why does the selector sit on Auto during the fire and reload clips?**
Those clips hold it at Auto so the bolt and trigger can move. To display the actual fire mode, layer the `selector` bone from `A_AR01_Selector` (section 5.3).

**Why do I need to recreate the sockets by hand?**
Unreal 5.8 does not keep FBX sockets on static meshes that have LOD groups, and the skeletal sockets come from the sidecar file. The JSON files list every socket with exact transforms (section 4.4).

**Do I need baked lighting?**
No. If you bake lighting with generated lightmap UVs, expect a few overlapping lightmap texels on `SM_AR01` LOD1 to LOD3 at 64 px. Dynamic-only lighting is not affected.

---

## Changelog

**v1.0 (2026-10-16):** Initial release.

---
---

# Before publishing (for the owner, not for the buyer page)

These items come from the reports. Each one either blocks the listing or needs a decision before this page goes live.

**Design and Fab category**

1. **Design distance.** The rifle is a near-replica of a real design. The Fab design changes have not been applied: rifle plan section 13 lists seven for AR01, plus an original dust-cover rail as an eighth. Once applied, the triangle counts, textures and showcase images may change, and this page must be updated to match.
2. **Firearms category rule.** Fab wants "all expected moving parts rigged and a full set of animations." Weapon-only clips may not satisfy a reviewer. Either ask Fab support, or plan a minimal arms set on the UE5 Manny (idle, fire, reload, reload empty, equip). This decision is open in the gun study (Q6).

**Quality not yet passed**

3. **Close-up realism.** The close-up views were judged fake before the stage-7 fixes. The blind judge and the two realism judges have not been re-run on the fixed bytes. The target is at most 1 single-judge fake call over the 4 realism views.
4. **Open Unreal gates (U5, U10, U8).** The degenerate-triangle drops, tangent warnings and lightmap overlap are disclosed on this page. The planned fix is in the part generators. The tangent warnings are logged at import, not at map load or Play In Editor, so they should not violate Fab's "no load/PIE warnings" rule. Confirm this in the clean project.
5. **Hand fit (U11) not tested.** The `Grip` and `SupportHand` positions are provisional.

**Shipped files**

6. **Sidecar `materials` block is wrong.** It lists `M_Fabric_Master` for the metal set. Fix it in the next re-export. Until then the buyer page tells buyers to ignore that block.
7. **FBX files embed the absolute source path** (tech note N1). Fix this before Fab.

**Unreal-format product not built**

8. **Gates R3/R4 not done.** There is no clean `<Pack>` project, migrate test, dependency scan or byte deny-scan. Several things are unknown:
   - the final folder and asset paths;
   - whether `M_Steel_Master` and `M_Fabric_Master` are copied under the pack root;
   - whether AR01 sells alone or inside a larger pack.

   Section 2.6 assumes the instances ship with the masters. This needs confirming.
9. **Materials in an FBX-only purchase.** FBX-only buyers get textures but no material instances. This page does not yet say what they should do.

**Information the documents don't state**

10. **Documentation gaps:**
    - The static-mesh socket names (17 on `SM_AR01`, 5 on `SM_AR01_Mag`) are not listed in the docs.
    - The static-mesh LOD screen sizes are not listed in the docs.
    - The per-socket uses in 5.1 are inferred from the socket names, except for `Mag`, `MagRockStart`, `MagInsertStart`, `CenterOfMass`, `Grip` and `SupportHand`. Confirm them, or reduce the table to the documented ones.
    - The physics shape types are only in the sidecar.
11. **Import Mesh LODs = on** comes from the pipeline study, not the AR01 README. Confirm it is the setting that was used.
12. **First Person project settings.** The gun study lists deferred, VSM and Allow Static Lighting off as README-only FP instructions. The AR01 README does not state them, so they were left off this page. Add them once confirmed.
13. **Masks sizes** (2048 / 1024 / 512) are derived from "half size." Confirm them against the files.
14. **LOD0 count conflict.** The report gives LOD0 as 49,474 triangles (form stage), while the README gives 48,386 for `SK_AR01` without the magazine. This page uses the README figure. Confirm which number the listing should state.
15. **Dependencies and plugins.** The documents don't say whether any plugin is required. This is needed for the listing's dependency line.

**Wording and declarations**

16. **Removed wording.** The cartridge designation and the internal README's "as on the real rifle" phrasing were left out, to avoid real-gun references and real-world function claims. Keep them out of the listing too.
17. **AI declaration.** The design source is an AI design sheet. Under the catalogue policy (P1), declare "Created with AI = Yes." This is the owner's decision.
18. **Open owner decisions:**
    - LOD0 checkering as cut geometry (tech T5).
    - Where the documentation page is hosted (P5).
