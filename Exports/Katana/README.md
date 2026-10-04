# Basic katana and saya (`SM_Katana`, `SM_Katana_Saya`)

A plain, standard uchigatana and its black-lacquer saya (scabbard), both our own design:
- **Blade:** shinogi-zukuri with an iori-mune, no groove. The curve is one circular arc, centred along the blade. A
  chu-kissaki with a crisp yokote and a quiet notare hamon.
- **Fittings:** brass habaki and seppa, a plain round blackened-iron tsuba, and an iron fuchi and kashira.
- **Handle:** black ito in the classic diamond pattern over ivory same, plain lozenge menuki and a bamboo mekugi.
- **Saya:** black gloss roiro lacquer with black horn koiguchi, kurikata and kojiri, and a brass-lined cord hole.

There is no ornament, and **nothing hangs**: no sageo cord, no tassel. A static cord would freeze in one pose; the open
kurikata hole can take a rigged or simulated cord later.

Both assets were built in headless Blender 5.2 by `Scripts/Katana/` (`run_katana.sh`, `run_saya.sh`) from the study's
spec `WorkFiles/katana/katana_spec.json` and its design sheet `WorkFiles/katana/KATANA_DESIGN_SHEET.png`. The sources
are `Assets/Katana/Katana.blend` and `Assets/Katana/Saya.blend`. Pack colours are in `MATERIALS_README.md`; the full
report is `WorkFiles/katana/KATANA_REPORT.md`.

## 1. Files

| File | What |
|---|---|
| `SM_Katana.fbx` | One LodGroup: LOD0 20,368 / LOD1 6,824 / LOD2 1,724 triangles. 6 convex hulls `UCX_SM_Katana_LOD0_00..05`: the blade in four overlapping chords (the habaki in 00), tsuba + seppa, and the tsuka. 3 material slots |
| `SM_Katana.sockets.json` | The 8 sockets and the LOD screen sizes (1.0 / 0.35 / 0.15) |
| `SM_Katana_Saya.fbx` | One LodGroup: LOD0 7,412 / LOD1 2,210 / LOD2 954 triangles. Every LOD is closed solids with a real cavity. 5 convex hulls `UCX_SM_Katana_Saya_LOD0_00..04`: the body in four overlapping chords along the arc, and the kurikata. 2 material slots |
| `SM_Katana_Saya.sockets.json` | The 4 sockets and the same LOD screen sizes |
| `Textures/T_Katana_Steel_{BC,ORM,N}.png` | 2048 steel atlas: the blade, tsuba, fuchi and kashira (slot `M_Katana_Blade`); the habaki, seppa, menuki, eyelets and mekugi (slot `M_Katana_Fittings`) |
| `Textures/T_Katana_Grip_{BC,ORM,N}.png` | 2048 grip atlas, in UV0 tile u 1..2: the ito, the same and the LOD2 tsuka shell (slot `M_Katana_Grip`) |
| `Textures/T_Katana_Saya_{BC,ORM,N}.png` | 2048 saya atlas for both saya slots |
| `Textures/Recolour/` | The pack's recolour maps: `T_Katana_Grip_Detail16.png`, `T_Katana_Saya_Lacquer_Detail16.png` (1024, 16-bit linear), `recolour_maps.json`, `recolour_constants.json` |

**Texel density:**
- Blade: 54.8 px/cm. It is split into two islands per face at mid-length; the paint is continuous across the seam
  (BC within 1 level).
- Fittings: about 1.9x the blade. Tsuba: 1.25x. Faces hidden by a neighbour: 0.12-0.3x.
- Grip: 89.7 px/cm.
- Saya: 60.5 px/cm on every visible surface.

## 2. Import (Unreal 5.8)

**Meshes.** Use the legacy FBX importer with these settings:
- Static Mesh, **Import Mesh LODs ON**, Combine Meshes OFF.
- **Convert Scene ON**, **Convert Scene Unit ON**, **Force Front X Axis OFF**, **Import Uniform Scale 1.0**.
- Auto Generate Collision OFF, **One Convex Hull per UCX ON**.
- Normals: *Import Normals*, with MikkTSpace tangents.
- Nanite OFF.
- Generate Lightmap UVs ON (source 0, destination 1, Light Map Coordinate Index 1).

**Sockets and LOD sizes.** Unreal drops FBX sockets from a LodGroup file and computes its own LOD thresholds. Apply
each `.sockets.json` with `Scripts/pipeline/ue_import_sockets.py`: it restores the sockets and sets
1.0 / 0.35 / 0.15.

**Textures.** Every map is a power of two; import with a full mip chain.

| Map | Settings |
|---|---|
| BC | sRGB, TC_Default |
| ORM | linear (sRGB off), TC_Masks, **Texture Group: World**. R = AO (Cycles bake of the game mesh), G = roughness, B = metallic |
| N | TC_Normalmap. **DirectX (green down): import with Flip Green OFF** |

A dark, metallic-heavy ORM can be auto-detected as a normal map and put in the WorldNormalMap group, so set the ORM
group by hand.

**Screen sizes.** 1.0 / 0.35 / 0.15 keep the opponent's sword off LOD2 at duel distance: the long blade gives a
49 cm bounds sphere. These are the build plan's proposal. The 1440p LOD-pop measurement has not been run.

## 3. Frames

**Blender vs Unreal Y.** Blender and the FBX use **-Y** for the omote (the face turned out when worn, the kurikata
side). **Unreal flips Y on import: in Unreal the omote and the kurikata are at +Y.** Example: the saya's Unreal
bounding box runs Y -1.37 to +2.25 cm, with the kurikata on the +Y side. All socket tables below are in Unreal cm.

**Katana.**
- The pivot is the `Grip` socket: the right-hand centre on the tsuka axis, 3.7 cm below the fuchi.
- +Z runs along the tsuka toward the blade.
- +X is the mune (back) side; the tip sweeps toward +X, and the edge faces -X.

**Saya.**
- The saya frame is the seated katana's frame moved 13.83 cm along Z.
- The pivot `BeltMount` sits on the mouth's tangent axis at the kurikata station.
- +Z runs toward the kojiri.

## 4. Katana sockets

| Socket | Location (cm) | Rotation | Use |
|---|---|---|---|
| `Grip` | (0, 0, 0) | 0 | The pivot: attach to the right hand |
| `OffHand` | (0, 0, -17.0) | 0 | Left hand on the tsuka (two-hand IK target) |
| `BladeBase` | (0, 0, 5.8) | 0 | Blade at the mune-machi: hit-trace start |
| `BladeMid` | (1.944, 0, 41.176) | 0 | Centre line at half the arc. Trace Base -> Mid -> Tip to follow the curve |
| `BladeTip` | (8.334, 0, 75.973) | pitch -11.044 (along the tip tangent) | The point: thrust FX along the blade |
| `TrailStart` / `TrailEnd` | (0, 0, 10.8) / (7.299, 0, 74.643) | 0 | Swing-trail ribbon |
| `CenterOfMass` | (0.933, 0, 16.922) | 0 | See below |

`CenterOfMass` comes from part volumes x densities: about 1.15 kg, balance 11.2 cm in front of the tsuba. It
includes an assumed hidden tang that is not modelled. Unreal computes the centre of mass from the hulls at uniform
density, so for dropped-weapon physics set the body's Center Of Mass offset to this socket.

## 5. Saya sockets, sheathing and the draw

| Socket | Location (cm) | Rotation | Use |
|---|---|---|---|
| `BeltMount` | (0, 0, 0) | 0 | The pivot: attach to the hip (obi) socket |
| `Holster` | (0, 0, -13.83) | 0 | Snap the katana's `Grip` here with zero relative transform: fully seated |
| `Mouth` | (0, 0, -8.0) | 0 | The koiguchi plane on the tsuka axis. The draw leaves tangent to its -Z |
| `DrawPivot` | (367.86, 0, -8.03) | 0 | The blade's arc centre, 3.68 m from the mouth |

**Sheathe.**
1. Set the katana to NoCollision or QueryOnly: it lies inside the saya's hulls.
2. Attach it to the saya's `Holster` with SnapToTarget (location, rotation and scale).

The seated seppa then sits 0.30 mm off the mouth, the habaki is a 0.11 mm friction fit, and the tip stops 10 mm short
of the cavity end.

**Draw.** The blade is curved (17 mm sori), so it must leave the saya **along its arc**:
- Rotate the katana about the `DrawPivot` socket's Y axis, in the direction that moves the `Grip` out of the mouth.
- The tip reaches the mouth after **11.04 deg**, and is 5 mm clear after 11.12 deg.
- The motion starts tangent to `Mouth` -Z.

Measured on Unreal's own geometry, this rotation has 0 intersections at every 0.05 deg step, with at least 0.55 mm
clearance. A straight slide along `Mouth` -Z **collides after about 3 mm**. Animators should key the draw from
`DrawPivot`, or hand-attach on a montage notify once the tip is out. Then attach `Grip` to the hand and restore the
katana's collision.

**Belt attach (game side).**
- Default carry: left hip, edge up, through the obi.
- Add a skeleton socket `Saya_L` on `pelvis` (not the thigh) and attach `BeltMount` to it. Add `Katana_R` on
  `hand_r` for the drawn sword.
- The socket rotations are tuned once in the editor on the player character.
- A back carry only needs another skeleton socket using the same `BeltMount`.
- These skeleton sockets are not authored by this build; they need the user's go-ahead in the game project.

## 6. Materials

| Mesh | Slot | Parts | Pack instance (master) |
|---|---|---|---|
| `SM_Katana` | 0 `M_Katana_Blade` | blade, tsuba, fuchi, kashira | `MI_Katana_Blade` (`M_Steel_Master`) |
| `SM_Katana` | 1 `M_Katana_Fittings` | habaki, seppa, menuki, eyelets, bamboo mekugi | `MI_Katana_Fittings` (`M_Steel_Master`) |
| `SM_Katana` | 2 `M_Katana_Grip` | ito, same, LOD2 tsuka shell | `MI_Katana_Grip` (`M_Fabric_Master`, recolourable ito, Metal From ORM on) |
| `SM_Katana_Saya` | 0 `M_Katana_Saya_Lacquer` | lacquered body and cavity | `MI_Katana_Saya_Lacquer` (`M_Fabric_Master`, recolourable) |
| `SM_Katana_Saya` | 1 `M_Katana_Saya_Fittings` | horn koiguchi, kurikata, kojiri, mouth face, brass shitodome | `MI_Katana_Saya_Fittings` (`M_Steel_Master`) |

Without the pack, plug the maps above into any PBR material (BaseColor = BC, AO/Roughness/Metallic = ORM R/G/B,
Normal = N).

## 7. How it was checked

All checks ran on the exact shipped bytes: `SM_Katana.fbx` sha256 `114c79f4...`, `SM_Katana_Saya.fbx`
`d97bd9b7...`.

**Katana dimensions** (`WorkFiles/katana/katana_measured.json`), all equal to the spec within 0.01 mm:

| Measure | mm |
|---|---|
| nagasa | 705.00 |
| sori | 17.00 |
| mune arc radius | 3663.10 |
| motohaba / sakihaba | 31.00 / 22.00 |
| kasane | 7.00 / 5.00 |
| kissaki | 38.00 |
| habaki | 28.00 |
| tsuba | 76.00 |
| tsuka | 265.00 |
| overall | 974.73 |

**Ito:** 9 crossings per face at the spec positions (within 0.56 mm), plus a half crossing tucked at each lip.
Pitch 26.77 mm.

**Saya dimensions** (`WorkFiles/katana/saya_measured.json`):
- 721.79 mm along the mune arc.
- 40.0 x 27.5 mm at the mouth, 35.0 x 23.0 mm at the end.
- Kurikata 80.0 mm from the mouth, 9.0 mm proud.

**Silhouettes vs the design sheet** (IoU):
- Katana: side 0.985, top 0.963, end 0.991, tsuka 2:1 0.981.
- Saya: 0.990, end 0.988.
- Sheathed: 0.986, end 0.992.

The tsuka figure dropped from 0.993 because the wrap now closes at the kashira; the sheet left an open band there.

**Fit:** 9 LOD pairs, 0 intersections, all walls at or above their gates (`WorkFiles/katana/saya_fit_verify.json`).

**QA:** `qa_check` passed: 110 checks (katana) and 88 (saya).

**Collision.** The hulls are built from dense surface samples, and neighbouring chords overlap by 3 mm of arc. A
second, independent sampling gates them:
- In Blender: 0 of every LOD0 surface sample, and 0 LOD vertices, fall outside the hull union.
- On Unreal's stored hulls: 0 of 300,000 LOD0 surface samples are outside, for both assets.

**Unreal 5.8.3** (`WorkFiles/katana/UnrealVerify_Final2`, content path `/Game/KatanaVerify/Final_1003c`). The import ran
in one process; the read-back, attach and render each ran in a further fresh process, one at a time. Results:
- Triangle counts equal Blender's.
- All 8 + 4 sockets match the sidecars exactly (0.000 cm, 0.000 deg), at scale 1, owned by the asset.
- Screen sizes 1.0 / 0.35 / 0.15, lightmap index 1, Nanite off, 3 + 2 slots.
- All 9 maps 2048 with their flags; every ORM in TEXTUREGROUP_World.
- Attaching to `Holster` gives (0, 0, -13.83) cm, rotation 0.
- The arc draw is clean in 223 steps for all 9 LOD pairs.
- Depth captures from 4 sides show no blade past the mouth.
- No warnings or errors from the assets.
