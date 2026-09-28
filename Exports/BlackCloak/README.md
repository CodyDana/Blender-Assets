# Black cloak — reference revision 2

Separate black cloak rebuilt from the supplied front reference. The asymmetric wings, diagonal front leaf, upper overlaps, gathered left fall and continuous scarf collar replace the original procedural layout. Exact small wrinkles and hidden construction are not claimed; see COMPARE.html and REVISION_NOTES.md.

## Recolor in Unreal

The included `Unreal/BlackCloakRecolor.uproject` contains `M_Cloak_Recolor`, four color instances, and static/skeletal meshes with cloth-only assignments. Open or duplicate a supplied `MI_Cloak_*` instance and change **CloakColor**. The clasp and leather stay separate. See [RECOLOR.md](RECOLOR.md) for migration and runtime color changes, and [RECOLOR.html](RECOLOR.html) for preset previews.

## Files

- BlackCloak.blend: editable source in the ZIP; workspace copy is Assets/BlackCloak.blend. Contains separate cloth pieces, continuous cowl, ring/pin/loop, editable subdivision and thickness, packed textures and a studio excluded from exports.
- BlackCloak.glb: embedded materials/textures, static geometry.
- BlackCloak.fbx and _LOD1/_LOD2: static mesh files.
- BlackCloak_Skeletal.fbx and LODs: the existing shared 152-bone skeleton with rigid attachment weights. Collar follows neck01, clasp clavicle.R, other fabric spine01. This is not simulated or animated cloth.
- Textures: 2K base color, roughness, OpenGL normal and DirectX normal.
- Previews: actual saved-source and reimported-export renders.
- authoring_pin_weights.csv: pin groups indexed to the editable Blender cages, not FBX vertices.
- asset_report.json: file hashes, mesh counts and round-trip checks.

## Scale and LODs

Meters, Z-up, ground-based origin. Approximately 1.032 m wide, 0.678 m deep and 1.721 m tall. Character movement fit has not been validated.

| LOD | Triangles | Intended use |
| --- | ---: | --- |
| 0 | 84,612 | Closest view |
| 1 | 47,088 | Reduced detail |
| 2 | 25,646 | Distance; visible fold simplification close up |

Reduction is per part, weighted toward cloth interiors and performed before thickness. Transition distances and performance require testing in the intended game.

## Materials and UVs

The authoring shader uses meter UVs with a 0.128 m fabric repeat. Exported UV0 already includes that repeat scale; use texture tiling 1.0. UV0 intentionally tiles and is not a unique bake atlas. UV1 is a separate smart-projected layout inside 0–1; engine lightmap validation remains pending.

For Unreal use BaseColor as sRGB, Roughness as linear data, and the DirectX normal as a normal texture with green flip OFF. OpenGL normals are for Blender/glTF. Cloth is opaque/nonmetallic; the clasp has a separate dark steel material. FBX material assignment can require manual setup. No baked AO/ORM atlas is supplied, so this is not full house-pipeline/Fab approval.

## Validation and remaining integration

All six FBXs and the GLB were reimported. Triangle totals, UV channels, loose/degenerate geometry and optional rig structure were checked; LOD counts strictly descend. GLB and both reduced FBXs were rendered for material/silhouette comparison. The source and package are recorded by hashes.

Unreal collision, Chaos cloth, layer collision, cloth painting, character fit and animation tests remain unfinished. Use the open authoring surfaces as a starting point for a simulation mesh rather than the thickened render mesh. The back is an interpretation because only a front reference exists.

The character, hair and default clothing assets were not modified.
