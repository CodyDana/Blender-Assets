# Black Nunchucks

Reference-based Blender asset with black textured grips, brushed silver caps, two attachment eyes, and seven chain links. Handle proportions and displayed pose follow the supplied image. The surface grain and hidden construction are reconstructed rather than an exact copy of every photographed pixel. Scale assumes approximately 30 cm handles because the reference has no scale marker.

## Files

- `Assets/BlackNunchucks.blend` — editable scene, packed textures, three LODs, custom rig and presentation studio. LOD0 is visible; LOD1/2 are hidden. The studio is excluded from all model exports.
- `Exports/BlackNunchucks/SK_BlackNunchucks_LOD0.fbx` through `LOD2.fbx` — skeletal versions.
- `Exports/BlackNunchucks/SM_BlackNunchucks_LOD0.fbx` through `LOD2.fbx` — static versions with convex handle collision proxies.
- `Exports/BlackNunchucks/SM_BlackNunchucks_LOD0.glb` — textured, rigged LOD0 with embedded textures. The SM filename does not mean it lacks skinning.
- `Textures/BlackNunchucks/` — 4K BaseColor, DirectX Normal, OpenGL Normal companion, AO and packed ORM (R=AO, G=Roughness, B=Metallic), four RGBA part masks and neutral tint detail.
- `Exports/BlackNunchucks/UnrealDemo/` — native Unreal Engine 5.8 recolor materials, imported skeletal mesh and three LODs.
- `Exports/BlackNunchucks/Unreal_Recolor_Guide.md` — setup, saved color presets, runtime parameter changes and full reskins.
- `Renders/BlackNunchucks/Reference_Comparison.html` — local reference comparison with an opacity slider. Open in a browser after extracting the ZIP.
- `Scripts/BlackNunchucks/` — construction, baking, validation and packaging scripts.

## Mesh and rig

LOD triangle counts: **28,360 / 14,216 / 7,488**. Each file contains one LOD; assign additional LOD files manually in the target application. UV0 is the unique texture atlas; UV1 is a separate copy for lightmaps. Components remain separate in Blender and share one baked material.

The custom 10-bone rigid-part rig is `root → handle_L → chain_01 → … → chain_07 → handle_R`. Each component has normalized rigid weights. Select and unhide `Nunchucks_Rig` to pose it. There are no animation clips, IK controls, physical chain constraints or engine Physics Asset. Anchor attached objects using the handle bones; the scene origin is at floor level in the pictured pose.

## Unreal import

Use the skeletal FBX for posing or later animation, or the static FBX for a fixed prop. Files use metre-scale source geometry and the shared unit-aware FBX exporter. Leave import scale at 1. Import geometry and create the material separately; FBX materials are not the authoritative shading setup.

Connect BaseColor using sRGB. Treat ORM as linear data: R to Ambient Occlusion, G to Roughness, B to Metallic. Use `blacknunchucks_normal.png` with normal-map compression and **no additional green flip**. The `_normal_opengl` companion is for Blender and glTF. For static meshes use lightmap coordinate index 1. Collision hulls cover handles only; tune engine collision and constraints for your intended gameplay.

## Verification

Source meshes passed topology, applied-transform, UV and skin-weight checks. All six FBX files and the GLB were reimported in Blender and checked against the saved source for triangle counts, dimensions, UV statistics, material assignments, bones and weights. GLB retains embedded BaseColor, normal, metallic/roughness and occlusion maps. The real GLB is also rendered in `BlackNunchucks_ExportCheck.png`.

All 36 pairs among seven chain links and two eyes are free of triangle intersections at each LOD (108 checks). All eight intended connections remain interlocked. This required small pose and link-width adjustments relative to the image. Welds and the intentional eye anchoring inside caps are excluded from these clearance checks.

Reports and file hashes are included. Recolor material compilation, saved asset reload and dynamic parameter changes are checked in Unreal; see the included engine validation report for the exact scope and source hashes. **Physics, animation playback and a gameplay customization UI are not supplied or verified.**

## Recoloring in Unreal

Use `MI_BlackNunchucks_Default`, or create a Dynamic Material Instance from it for gameplay. Set `Amount_Grip_L` to 1 and `Color_Grip_L` to the desired color to change only the left grip. Every region has matching `Amount_` and `Color_` controls; Amount 0 restores the original texture. Caps, eyes, seven chain links, grips and weld seams are independent. Bright grip colors retain surface grain. Texture parameters support full skins using the same UV layout.

The optional Blender preview material mirrors these controls. FBX/GLB retain the simple original PBR material; use the native Unreal material or the provided setup script for runtime recoloring. See `Unreal_Recolor_Guide.md` for the complete parameter list and Blueprint steps.

## Regeneration

Run from the extracted root using Blender 5.2 and system Python. Claim `BlackNunchucks` with `Scripts/pipeline/lock.py` as agent `codex`, then run `build.py`, `resolve_chain.py`, `bake.py`, `finalize_names.py`, `add_recolor.py`, `export_validate.py`, and `render_export.py` in that order with Blender's background Python option. The included `WorkFiles/BlackNunchucks/chain_solution.json` is the fixed clearance solution used by `resolve_chain.py`. To recompute it, run `extract_chain_centers.py` inside the procedural Blender file, then run `optimize_chain.py` with system Python and the packages in `requirements-resolve.txt`. Run `unreal_recolor_setup.py` inside Unreal to create the native material and imports. Re-run the provided validation scripts before packaging. `package.py` runs under system Python. Release the asset lock when finished. GPU rendering uses Cycles OptiX; adjust the device in scripts for other hardware.
