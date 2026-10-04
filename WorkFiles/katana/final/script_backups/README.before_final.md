# Basic katana (`SM_Katana`)

A plain, standard uchigatana: shinogi-zukuri blade with an iori-mune, a centred curve (one circular mune arc) and a
chu-kissaki with a crisp yokote; brass habaki and seppa, a plain round blackened-iron tsuba, iron fuchi and kashira,
black ito in the classic diamond pattern over white same, plain lozenge menuki of our own design, a bamboo mekugi.
No ornament, no groove, nothing hangs. It is the user's own design, built in headless Blender 5.2 by
`Scripts/Katana/` (2026-10-03) from `WorkFiles/katana/katana_spec.json` and `KATANA_DESIGN_SHEET.png`.
The saya (`SM_Katana_Saya`) is a separate asset built to fit this exact export.

## 1. Files

| File | What |
|---|---|
| `SM_Katana.fbx` | One LodGroup: LOD0 20,872 / LOD1 7,032 / LOD2 1,784 triangles. 6 convex hulls `UCX_SM_Katana_LOD0_00..05` (blade in four chords, the first including the habaki; tsuba + seppa; tsuka). 3 material slots |
| `SM_Katana.sockets.json` | The 8 sockets and the LOD screen sizes (1.0 / 0.35 / 0.15) |
| `Textures/T_Katana_Steel_{BC,ORM,N}.png` | 2048 steel atlas: blade, tsuba, fuchi, kashira (slot `M_Katana_Blade`) and habaki, seppa, menuki, kashira eyelets (slot `M_Katana_Fittings`) |
| `Textures/T_Katana_Grip_{BC,ORM,N}.png` | 2048 grip atlas (UV0 tile u 1..2): ito, same, mekugi, the ito band over the kashira, the LOD2 tsuka shell |

Every map is a power of two (import with a full mip chain):
- **BC**: sRGB, TC_Default.
- **ORM**: linear, TC_Masks. R = AO (Cycles bake of the game mesh), G = roughness, B = metallic.
- **N**: linear, TC_Normalmap. **DirectX (green down): import with Flip Green OFF.**

Texel density: steel atlas 28.9 px/cm on the blade (its 706 mm length caps a square 2048 atlas), fittings 104 px/cm,
tsuba 75 px/cm; grip atlas 85 px/cm on the ito, 60 px/cm on the same.

## 2. Import (Unreal 5.8)

Legacy FBX importer: Static Mesh, **Import Mesh LODs ON**, Combine Meshes OFF, Auto Generate Collision OFF,
One Convex Hull per UCX ON, Normals *Import Normals* with MikkTSpace tangents, Nanite OFF, Generate Lightmap UVs ON
(source 0, destination 1, Light Map Coordinate Index 1).

Then apply the sidecar with `Scripts/pipeline/ue_import_sockets.py` (Unreal drops FBX sockets from a LodGroup file and
computes its own LOD thresholds; the sidecar restores the 8 sockets and sets 1.0 / 0.35 / 0.15).

The proposed screen sizes keep the opponent's sword off LOD2 at duel distance (the long blade gives a ~49 cm bounds
sphere); they are the build plan's proposal and still to be confirmed by an LOD-pop measurement in Unreal.

## 3. Frame and sockets (Unreal cm)

The pivot is the `Grip` socket: the right-hand centre on the tsuka axis, 3.7 cm below the fuchi. +Z runs along the
tsuka toward the blade, +X is the mune (back) side (the tip sweeps toward +X), the edge faces -X, -Y is the omote face.

| Socket | Location | Rotation | Use |
|---|---|---|---|
| `Grip` | (0, 0, 0) | 0 | The pivot: attach to the right hand |
| `OffHand` | (0, 0, -17.0) | 0 | Left hand on the tsuka (two-hand IK) |
| `BladeBase` | (0, 0, 5.8) | 0 | Blade at the mune-machi: hit-trace start |
| `BladeMid` | (1.944, 0, 41.176) | 0 | Centre line at half the arc: trace Base -> Mid -> Tip follows the curve |
| `BladeTip` | (8.334, 0, 75.973) | pitch -11.044 (the tip tangent) | The point; thrust FX along the blade |
| `TrailStart` / `TrailEnd` | (0, 0, 10.8) / (7.299, 0, 74.643) | 0 | Swing-trail ribbon |
| `CenterOfMass` | (0.933, 0, 16.922) | 0 | From part volumes x densities (about 1.15 kg, balance 11.2 cm in front of the tsuba, a typical hidden tang included). Unreal computes CoM from the hulls at uniform density: set the body's Center Of Mass offset to this socket for dropped-weapon physics |

When the katana is sheathed, set it to NoCollision or QueryOnly (it lies inside the saya's hulls) and restore its
collision on the draw. The draw is a rotation about the saya's `DrawPivot` socket (the blade's arc centre).

## 4. Materials

| Slot | Parts | Pack master (planned) |
|---|---|---|
| `M_Katana_Blade` | blade, tsuba, fuchi, kashira | `M_Steel_Master` (`Steel Tint`) |
| `M_Katana_Fittings` | habaki, seppa, menuki, eyelets | `M_Steel_Master` (`Steel Tint`) |
| `M_Katana_Grip` | ito, same, mekugi | `M_Fabric_Master` (ito `Colour`, Metal From ORM on so the same keeps its baked colour) |

The pack-material wiring (instances, Detail16 recolour maps, `MATERIALS_README.md`) is done by the finalising step
under the shared materials lock; until then use the maps above in any PBR material.

## 5. How it was checked

On the exported bytes (`WorkFiles/katana/katana_measured.json`): nagasa 705.00, sori 17.00, mune arc radius 3663.10,
motohaba 31.00, sakihaba 22.00, kasane 7.00 / 5.00, kissaki 38.00, tip (83.34, 759.73), habaki 28.00, tsuba 76.00,
tsuka 265.00, overall 974.73 mm (all equal to the spec within 0.01 mm); ito 9 crossings per face on each side at the
spec positions (within the 0.25 mm sampling), pitch 26.78, the 4th omote diamond 17.65 x 32.3 mm open (sheet 17.75 x
31.9). Silhouettes against the design sheet at its own scale: IoU 0.990 side, 0.972 top, 0.991 end, 0.993 tsuka 2:1
(`WorkFiles/katana/KATANA_DESIGN_COMPARE.png`). `qa_check` passed (110 checks).

---

# Saya (`SM_Katana_Saya`)

The scabbard, fitted to the exact `SM_Katana.fbx` bytes above (sha256 `da401f78...`). Black roiro lacquer with subtle
wear (gloss dulled where a hand holds the mouth end, where the obi rubs the flats and along the ha / mune ridges; sparse
hairline scratches), black horn koiguchi, kurikata and kojiri, a brass-lined cord hole through the kurikata. The body is
concentric with the blade's mune arc. **No sageo (cord) and no kaeshizuno**: a static cord would freeze in one pose; the
open kurikata hole takes a rigged or simulated cord later. Built by `Scripts/Katana/build_saya.py` (+ `saya_*.py`,
`run_saya.sh`) from `WorkFiles/katana/katana_spec.json` and the shipped katana; source `Assets/Katana/Saya.blend`.

## Files

| File | What |
|---|---|
| `SM_Katana_Saya.fbx` | One LodGroup: LOD0 7,466 / LOD1 2,210 / LOD2 956 triangles. The cavity is real at every LOD. 5 convex hulls `UCX_SM_Katana_Saya_LOD0_00..04` (the body in four chords along the arc, koiguchi in 00 and kojiri in 03; the kurikata). 2 material slots |
| `SM_Katana_Saya.sockets.json` | The 4 sockets and the LOD screen sizes (1.0 / 0.35 / 0.15, as the katana) |
| `Textures/T_Katana_Saya_{BC,ORM,N}.png` | One 2048 atlas for both slots, 60.5 px/cm on every visible surface (the cavity 7 px/cm, the habaki pocket 36 px/cm) |

Maps and import settings exactly as for the katana (BC sRGB; ORM linear, R AO / G roughness / B metallic; N DirectX,
Flip Green OFF; legacy FBX importer with Import Mesh LODs ON, One Convex Hull per UCX, then
`Scripts/pipeline/ue_import_sockets.py` for the sidecar).

| Slot | Parts | Pack master (planned, `KATANA_BUILD_PLAN.md` 5.2) |
|---|---|---|
| `M_Katana_Saya_Lacquer` | lacquered body, cavity | `M_Fabric_Master` (lacquer `Colour`) |
| `M_Katana_Saya_Fittings` | horn koiguchi, kurikata, kojiri, the mouth face and habaki pocket; brass shitodome (ORM metallic 1) | `M_Steel_Master` |

## Frame and sockets (Unreal cm)

The saya frame is the SEATED katana's frame moved 13.83 cm along Z: the pivot `BeltMount` sits on the mouth's tangent
axis at the kurikata station; +Z runs toward the kojiri, +X is the mune side, -Y the omote (kurikata side).

| Socket | Location | Rotation | Use |
|---|---|---|---|
| `BeltMount` | (0, 0, 0) | 0 | The pivot: attach to the hip (obi) socket |
| `Holster` | (0, 0, -13.83) | 0 | Snap the katana's `Grip` here with zero relative transform: fully seated |
| `Mouth` | (0, 0, -8.0) | 0 | The koiguchi plane on the tsuka axis; the draw leaves along its -Z |
| `DrawPivot` | (367.86, 0, -8.03) | 0 | The blade's arc centre. **A clean draw rotates the katana about this socket's Y axis** (11.0 deg brings the tip to the mouth). The blade is curved (17 mm sori), so a straight slide along `Mouth` -Z collides after 1 cm |

Set the katana to NoCollision / QueryOnly while sheathed (it lies inside these hulls).

## How it was checked (on the exported bytes of both assets, katana placed by the exported `Holster`)

`WorkFiles/katana/saya_fit_verify.json`, all 9 saya LOD x katana LOD pairs: 0 intersecting triangles; blade clearance
>= 0.495 mm (design 0.5 at the mune, 1.0 at the edge and sides); habaki clearance 0.11 mm all round (a friction fit);
seppa / tsuba >= 0.58 mm; every blade vertex enclosed; the arc draw about the exported `DrawPivot` in 0.156 deg steps
is clean at every step. Visible seat gap seppa -> koiguchi 0.35 mm max (design 0.3). Walls: 2.32 mm around the habaki
pocket, >= 3.6 mm in the body (LOD0). The tip stops 10.0 mm short of the cavity end. Dimensions
(`WorkFiles/katana/saya_measured.json`): 721.79 along the mune arc, 40.0 x 27.5 at the mouth, 35.0 x 23.0 at the end,
koiguchi 20.0, kojiri 28.0, kurikata 80.0 from the mouth, 9.0 proud. Silhouettes against the design sheet at its own
scale: IoU 0.989 (saya side + top), 0.988 (end), 0.989 (sheathed side + top), 0.992 (sheathed end)
(`WorkFiles/katana/SAYA_DESIGN_COMPARE.png`). `qa_check` passed (88 checks).
Unreal 5.8.3 (`WorkFiles/katana/UnrealCheck_Saya`, a fresh second process on the exact bytes): 3 LODs with the same
triangle counts as Blender and the FBX, 5 hulls, the 4 sockets at scale 1 outered to the asset, screen sizes
1.0 / 0.35 / 0.15, lightmap index 1, 2 slots, Nanite off, all texture flags persisted, and the katana's 8 sockets
composed through the in-engine `Holster` land where the Blender fit puts them (0.000 cm); 0 warning/error lines.
