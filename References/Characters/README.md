# Characters: locked fitting bodies

One folder per character base. Garments are built on these, never on anything else (Scripts/garments/README.md,
ASSET_GUIDELINES.md 12.10). Nothing here is edited by hand: rebuild with the scripts, and the lock changes with it.

```
MH_PlayerDefault/                        the male player (DemoGame_1 /Game/MetaHumans/MH_PlayerDefault), built 2026-09-26
  MH_PlayerDefault_FitBody.blend         collection FITBODY_MH_PlayerDefault, everything unselectable:
                                           root              metahuman_base_skel armature (object = Unreal's root bone)
                                           FIT_*_Body        LOD0 body, own weights (<= 8 influences)
                                           FIT_*_Head        face SKIN section, re-weighted onto the body skeleton
                                           FIT_*_HeadParts   eyes/teeth/lashes (reference, never a collider)
                                           FIT_*_HairProxy   the BrushCut helmet shell, rim closed, pushed out 4 mm to hold 99.4 % of the LOD0 cards
                                           FIT_*_HairCards   the LOD0 hair cards (reference, triangle count)
  base_lock.json                         SHA-256 of the .blend and every source, skeleton record + hash, per-mesh
                                         geometry hashes, LOD0 triangle counts, body influence histogram, Unreal cross-check
  source/                                SKM_*_BodyMesh.fbx / SKM_*_FaceMesh.fbx (Unreal export, 2026-09-26),
                                         Hair_S_BrushCut_* FBX + ue_reference.json (CharacterLab commandlet), bones.json
MH_PlayerFemale/                         the female player (CharacterLab /Game/MetaHumans/MH_PlayerFemale, 168 cm), built 2026-09-27
                                         for the Snow Flower heels: same layout and objects; hair = Hair_L_Straight (two card
                                         groups joined; the helmet proxy holds 89 % of the long cards: fine for shoes, re-check
                                         before a hat); body/face FBX exported from CharacterLab by ue_export_fitbody.py
                                         (FITBODY_BASE=MH_PlayerFemale, wrapper -Render); skeleton hash 9c994c38..., base 130,120 tris
```

Convention: metres, Z up, facing -Y, identity object transforms, rest pose == pose. Imported with
`automatic_bone_orientation=False` (Outfit_Pipeline trap 1). The skeleton matches Unreal's reference skeleton of the
body mesh to 0.0005 mm (342 bones including root, no `ik_*` bones).

Rebuild (only when the character itself changes; every garment then needs re-gating against the new lock):

```
powershell -ExecutionPolicy Bypass -File Scripts/garments/run_ue_characterlab.ps1 -Script Scripts/garments/ue_export_fitbody.py -Tag fitbody_export
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python Scripts/garments/build_fitbody.py -- --base MH_PlayerDefault --force
```

The male's body/face FBX come from DemoGame_1's `Tools/Claude/Cloak/export_mh_body_fbx.py` (editor Python). A new base is
a `BASES` entry in both `ue_export_fitbody.py` and `build_fitbody.py` (the female is the example):

```
$env:FITBODY_BASE="MH_PlayerFemale"; powershell -ExecutionPolicy Bypass -File Scripts/garments/run_ue_characterlab.ps1 -Script Scripts/garments/ue_export_fitbody.py -Tag fitbody_export_female_r -Render
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python Scripts/garments/build_fitbody.py -- --base MH_PlayerFemale --force
```

`-Render` is required when the script exports a skeletal mesh: under `-nullrhi` the FBX exporter asserts on `MeshObject`.
