# Garments: building clothing on the game's MetaHuman

Every hat, cloak and outfit is built **on the locked fitting body** (`References/Characters/MH_PlayerDefault/`,
see its README) and leaves Blender through the gates in `Scripts/pipeline/garment_qa.py`. The house rules are in
`ASSET_GUIDELINES.md` 12.10; the Unreal-side traps are in DemoGame_1 `Docs/Outfit_Pipeline.md` (read traps 1-15).

## 1. Pick the type

| Type | For | Skinning (automatic in the build) | Gates that differ |
|---|---|---|---|
| `cloak` | cloak, cape, long loose sleeves, scarf ends | spine chain only (pelvis..head); tight pieces height-blended, cloth panels (collection `GARMENT_SIM`) rigid on the chest (spine_03..05) | <= 2 influences, one `*_Sim` section, `PinMask` active, cloth <= 6,000 tris; the cloth section is tested at rest only, arms ignored |
| `fitted` | shirt, trousers, bodysuit, gloves, armour that follows the limbs | the body's own weights from the nearest body triangle, top 8 | <= 8 influences (the body's own maximum), only bones the body uses, every region tested in every pose |
| `rigid_head` | hat, sandogasa, mask, hood that does not deform | every vertex on `head` | 1 influence; must also clear the hair proxy |
| `rigid_socket` | sheath, pouch, holster on one bone | every vertex on `--socket-bone` | 1 influence |

## 2. Start the work file

```
py Scripts/pipeline/lock.py claim BlackHat --agent claude --blend Assets/Garments/BlackHat.blend
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python Scripts/garments/new_garment.py -- --name BlackHat --type rigid_head
```

`--socket-bone thigh_l` for `rigid_socket`; `--out` to put the file elsewhere (default `Assets/Garments/<name>.blend`,
never overwritten). Open it and model into `GARMENT` (and `GARMENT_SIM` for a cloak's cloth panels, all sharing one
material). Reference geometry goes in `GARMENT_HELPERS`. The `FITBODY_MH_PlayerDefault` collection is locked and
hash-checked at export: model around it, never on it, and never rename `root`.

Rules the gates will hold you to:
- **Air between cloth and skin**: 1-1.5 cm (cloth panels 1.5, tight pieces 1.0). A vertex that starts inside the
  body can never be fixed in Unreal (trap 13). A hat must clear the hair proxy (the BrushCut's own helmet shell).
- One mesh per piece is fine; the build joins them. Mark metal hardware (buckles, rings) with the object property
  `garment_hard = True`: never decimated, moved rigidly by a refit.
- Materials `M_`/`MI_`, textures `T_`, at most 4 material slots; a cloak's cloth panels share one material (the build
  makes its `*_Sim` copy). Tiling fabric UVs may overlap; set the scene property `garment_unique_uvs = True` when the
  textures are baked/unique and UV0 must not overlap.
- A cloak's `CLOTH_Pin` vertex groups become the red `PinMask` colour the cloth mask is built from (trap 9).
- Decimation targets are scene properties (`garment_sim_target_tris` 6000, `garment_skin_target_tris` by type).

## 3. Clear, build, gate, export

```
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b Assets/Garments/BlackHat.blend --factory-startup --python Scripts/garments/build_garment.py -- --out Exports/Garments/BlackHat/SK_BlackHat.fbx
py Scripts/pipeline/lock.py release BlackHat --agent claude
```

The build never saves the work file. It exports only when every gate passes and writes `SK_<Name>.qa.json`
(every check), `SK_<Name>.garment.json` (the sidecar for the Unreal side: type, skeleton, physics asset, cloth
section, waivers, FBX hash) and `Textures/`. Add `--gate-only` to check without exporting. To push small pokes out
of the skin, `garment_helpers.clearance_pass` is the tool the refit uses (spread in space, arms ignored).

**Whole-character budget: 160k** (decided by Cody 2026-09-26; the base alone is body 60,816 + face 34,514 + BrushCut
cards 26,562 = 121,892 LOD0 triangles). Per-type budgets (cloak 30k, fitted 20k, hat 10k, socket 5k, cloth 6k) are
decided too. `--waive character_triangle_budget="reason"` still exists for an explicit, recorded exception; no
other gate can be waived.

## 4. A garment made on another body (legacy)

`refit_garment.py` warps a sculpt made on another body (the BlackCloak was sculpted on Manny) onto the base with a
landmark thin-plate-spline, then clears it; the recipe JSON names the cloth pieces, hard parts and targets
(`recipes/BlackCloak.json`). Run it on a COPY of the sculpt; it writes a new work file for `build_garment.py`.

```
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b WorkFiles/garment_pipeline/BlackCloak/BlackCloak_sculpt_copy.blend --factory-startup --python Scripts/garments/refit_garment.py -- --recipe Scripts/garments/recipes/BlackCloak.json --out WorkFiles/garment_pipeline/BlackCloak/BlackCloak_MH_garment.blend
```

## 5. Into Unreal

Import onto the base skeleton (the sidecar names it), never a new skeleton; then DemoGame_1's Outfit_Pipeline
steps: material slots through MCP in the mesh's slot order (traps 6/7), cloth on the `*_Sim` section from the
PinMask (trap 9, the MetaHuman settings of trap 14), the component on the MetaHuman body. The expected import warning
"invalid bind poses ... rebind using the time zero pose" is harmless (the exported pose is the rest pose).
**2026-09-27:** garments export in centimetres (pipeline 1.2.0) and `ue_check_garment.py` also compares the LOCAL
reference pose with scale (`ref_pose_local_vs_body`, `follower_safe`): a metre garment passes the component-space
check but is drawn 100x too small as a Leader Pose follower (measured with the Snow Flower heels).

`ue_check_garment.py` (through `run_ue_characterlab.ps1`) imports an FBX in a CharacterLab commandlet without saving
and compares its reference skeleton with the body's.

## Files

| File | What |
|---|---|
| `build_fitbody.py`, `ue_export_fitbody.py` | build the locked fitting body (+ Unreal-side export of the hair helmet and reference skeleton) |
| `new_garment.py` | start a work file |
| `refit_garment.py`, `recipes/*.json` | legacy garments sculpted on another body |
| `build_garment.py` | per-type build, gates, export, sidecar |
| `regress_blackcloak.py` | the BlackCloak regression against the 2026-09-26 one-off |
| `run_ue_characterlab.ps1`, `ue_check_garment.py` | headless Unreal import check (saves nothing) |
| `../pipeline/garment_qa.py`, `../pipeline/garment_helpers.py`, `../pipeline/test_garment.py` | gates, build helpers, tests |
