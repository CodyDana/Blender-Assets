# Snow Flower — design revision 3

Updated from the detailed reference review, with a further pass on guard landmarks, branch surface detail and the wheel pommel. Revision 2 work on the cupped blossoms, crossed grip wrap, connected hilt ornament and curved tassel is retained. Editable source has 114 component meshes and 456,024 triangles. See [revision review](../../WorkFiles/SnowFlower/REFERENCE_REVIEW.md) and [illustrated comparison](../../WorkFiles/SnowFlower/REFERENCE_REVIEW.html).

## Files

- [SnowFlower_Master.blend](../../Assets/SnowFlower/SnowFlower_Master.blend): editable components and procedural materials.
- [SnowFlower_Game.blend](../../Assets/SnowFlower/SnowFlower_Game.blend): consolidated LOD0 with packed baked textures and collision meshes.
- FBX/GLB exports below contain revision 3. Use `SnowFlower_DesignRevision3.zip` for this update. Previous `SnowFlower_Package.zip` and `SnowFlower_ReferenceRevision.zip` archives remain snapshots of their earlier revisions.

| Detail | Visible triangles | FBX | GLB |
| --- | ---: | --- | --- |
| LOD0 | 456,024 | [FBX](SM_SnowFlower.fbx) | [GLB](SM_SnowFlower.glb) |
| LOD1 | 181,995 | [FBX](SM_SnowFlower_LOD1.fbx) | [GLB](SM_SnowFlower_LOD1.glb) |
| LOD2 | 118,428 | [FBX](SM_SnowFlower_LOD2.fbx) | [GLB](SM_SnowFlower_LOD2.glb) |

LOD0 is the heavy close-up source. Reduced versions preserve fewer fine ornamental faces; their screen-size transitions and performance need testing in the game. Triangle counts exclude collision objects.

## Scale and attachment

Measured bounds: **0.171856 × 0.040112 × 1.256295 m**, including tassel and pommel. The origin remains the grip center. The blade extends along Blender local +Z; FBX is Z-up and GLB uses the standard Y-up conversion.

Only LOD0 FBX contains three `UCX_SM_SnowFlower_00/01/02` convex collision objects. They approximate the rigid sword and exclude the tassel. Collision behavior and hand sockets still require setup in Unreal.

## Textures

32 PNG files cover 8 materials, including the new BranchSteel material. Exact hookups are in [material_manifest.json](material_manifest.json).

- BaseColor: sRGB.
- Normal: linear/non-color, OpenGL +Y. Enable Flip Green Channel for Unreal/DirectX.
- Roughness: linear grayscale.
- ORM: linear; R=1 (no baked AO), G=roughness, B=metallic. Use either standalone roughness or ORM.G.

The GLBs contain their textures. Check or recreate FBX material hookups in Unreal. The Blender game file has packed textures.

## Validation and limits

The master passed structural checks without reported degenerate/nonmanifold/loose geometry or UV defects. All six exports passed Blender reimport checks for expected triangle count, UV presence, and absence of degenerate faces/loose vertices. Imported GLBs were rendered with their own materials; texture loading and bounds checks passed.

Exact identity with the reference has not been established. Fine thornwork, flower engraving and small branch details are reconstructed rather than exact tracings. The wheel pommel reconciles the front, back and side silhouettes; its ornamental surface detail remains interpretive. Hidden geometry is inferred, and reference lighting and perspective cannot be recovered exactly from this sheet.

The tassel is static. No Unreal runtime, attachment, collision behavior, LOD-switching or performance test has been performed.
