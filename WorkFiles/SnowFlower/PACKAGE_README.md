# Snow Flower — design revision 3

Start with `Exports/SnowFlower/README.md` for models, texture conventions, measured scale, LOD counts and integration limits.

- `Assets/SnowFlower/`: editable master and consolidated game Blender files.
- `Exports/SnowFlower/`: revised FBX/GLB files and baked PNG textures.
- `Renders/SnowFlower/`: actual current Blender renders, including imported exports.
- `References/SnowFlower/`: unchanged user-supplied reference.
- `WorkFiles/SnowFlower/`: current QA, checklist and illustrated comparison.
- `WorkFiles/SnowFlower/Revision1/Renders/`: selected previous renders for comparison.
- `Scripts/SnowFlower/`: reproducible Blender construction, baking and export code. Update hard-coded ROOT paths before running elsewhere; generation overwrites asset outputs. Blender 5.2 was used.

Revision 3 adjusts the guard from reference landmarks, increases branch surface variation and visible engraving, and replaces the angled pommel with one wheel bearing matching front and rear flowers. Existing revision 2 work on blossoms, crossed grip wrap, hilt ornament and the curved tassel is retained.

Exact reference identity is not established. Fine engravings are reconstructed and hidden geometry is inferred. The tassel is static and Unreal runtime testing remains outstanding. This archive is SnowFlower_DesignRevision3.zip; earlier ZIP archives remain unchanged.

Every entry was checked against the SHA-256 hashes in PACKAGE_MANIFEST.json after packaging.
