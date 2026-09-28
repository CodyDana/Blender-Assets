# Black Nunchucks

Draft handoff notes. Final export counts, dimensions, file hashes, and validation results belong to `Exports/BlackNunchucks/asset_report.json`.

The model reconstructs the supplied reference as black textured handles, satin metal caps and attachment eyes, and seven chain links. Scale assumes approximately **30 cm per handle**; it is not a measured product specification. Blender units are metres (`METRIC`, unit scale `1.0`). Hidden surfaces are interpreted from the visible reference.

## Delivery layout

- `Assets/BlackNunchucks.blend`: editable asset, baked materials, three LODs, and custom rig.
- `Exports/BlackNunchucks/SM_BlackNunchucks_LOD0.fbx` through `LOD2.fbx`: static versions of each LOD, including convex handle collision proxies.
- `Exports/BlackNunchucks/SK_BlackNunchucks_LOD0.fbx` through `LOD2.fbx`: skeletal versions of each LOD.
- `Exports/BlackNunchucks/SM_BlackNunchucks_LOD0.glb`: LOD0 with embedded textures and the custom rig.
- `Textures/BlackNunchucks/`: 4096 × 4096 baked PBR textures (`basecolor`, `orm`, `ao`, DirectX `normal`, and `normal_opengl`).
- `Exports/BlackNunchucks/asset_report.json` and `source_qa.json`: export inventory and Blender validation evidence.

Each FBX contains one LOD. Assign the separate files as LOD0, LOD1, and LOD2 in the target application. FBX export uses the shared project settings: −Y forward, Z up, unit-aware scaling, triangulated geometry, no leaf bones, and no animation export. The GLB filename retains the asset's `SM_` naming convention although it includes skinning.

## Rig and textures

`Nunchucks_Rig` is a custom **10-bone rigid-part rig**. Its hierarchy is `root → handle_L → chain_01 → … → chain_07 → handle_R`. Each handle, cap, and eye follows its handle bone; each chain link follows its matching chain bone. Vertices receive full weight on their assigned bone. This supports manual posing and later animation work; no gameplay animation clips, IK controls, or chain simulation are supplied.

The 4K normal texture uses the **DirectX** convention. An **OpenGL** companion is supplied for the Blender material and GLB. Choose the map that matches the target material's normal convention; do not apply a second green-channel inversion to an already matching map. Base color uses sRGB; normal and other material-data maps use Non-Color/linear interpretation. UV0 carries the baked atlas; UV1 is reserved for lightmaps.

## Validation and limits

The exporter checks source geometry, UVs, materials, transforms, and bone weights, then reimports each FBX and GLB into Blender. It compares triangle counts, UV statistics, material assignments, dimensions, bone hierarchy, and skin weights against the source. Consult the final report's `status` and individual checks; this draft does not establish that an export run has passed.

**No game-engine import or gameplay verification has been performed.** Handle collision hulls are geometry proxies; engine collision setup, physical constraints, chain response, LOD switching, and lightmap behavior still require integration and testing.

## Re-export prerequisites

Save the baked source before calling `export_asset(project_root, source_path)` from `Scripts/BlackNunchucks/export_validate.py` inside Blender 5.2. The `BLACK_NUNCHUCKS` collection must contain LOD0–2 meshes with unique `part_id` and `lod_level` tags, the expected `SM_BlackNunchucks_<part>_LOD<n>` names, applied geometry modifiers and transforms, UV0/UV1, baked image materials, and one Armature modifier targeting `Nunchucks_Rig`. Surfaces must be closed and clean, weights normalized, and combined triangle totals decrease at each LOD. The helper preserves the saved source and reopens it after export.
