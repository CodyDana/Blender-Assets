# Black cloak: reference revision 2

The cloak was rebuilt using visible landmarks in the supplied 417 x 674 reference. This supersedes the first procedural version. The previous strict review remains a historical record of that version, not a review of these new files.

## Work completed

- [x] Record reference coordinates for the outer contour, fastening, collar creases, overlap edges and major folds.
- [x] Reconstruct the left wing, large right diagonal flap, long front leaf and shorter left fall as independent cloth surfaces.
- [x] Replace the evenly pleated front with broad panels and individually positioned ridges and valleys.
- [x] Rebuild the collar from the traced sagging crease paths as one continuous surface; add localized compression folds.
- [x] Rebuild the two short upper overlap edges and the long diagonal mantle edge independently.
- [x] Shape the front opening and staggered hems, including the pointed front-right end and longer left strip.
- [x] Reduce clasp reflectivity and replace the broad exposed tabs with a small dark loop.
- [x] Replace the coarse broad bump texture with a fine woven color/normal material.
- [x] Inspect front, three-quarter, back and collar renders; close side gaps and remove an intersecting inner panel.
- [x] Re-export static and optional skeletal FBXs, GLB and three detail levels; add a separate UV1.
- [x] Reopen all exported models and check geometry counts, UV channels and attachment rig structure.
- [x] Compare reimported GLB and FBX LOD renders with the saved Blender model.

## What the comparison supports

The main silhouette and panel boundaries now follow the supplied image much more closely. The construction explicitly uses the clasp center at (117, 90), left wing corner at (10, 332), right mantle corner at (402, 380), front leaf edge turn at (210, 533), and front leaf tip at (374, 640). These are authoring landmarks in reference pixels; subdivision, surface thickness and lighting still affect the rendered contours.

The folds are three-dimensional geometry. The front reference was not projected onto the model as a photograph. The side and rear views are actual renders of the same model.

## Remaining limits

- [ ] Exact correspondence of every small wrinkle and frayed edge: not certified. The reference still has finer irregularity than the modeled cloth, especially in the collar and small broken hems.
- [ ] Identical fabric appearance under the reference lighting: not certified. The cloth shader, grain and highlights are an approximation.
- [ ] Hidden/back design match: impossible to verify from this front image; the rear remains an authored interpretation.
- [ ] Unreal character fit, collision and moving cloth: not configured or tested in this revision. Skeletal files carry rigid attachment weights only.

This is a substantial reference-driven geometry revision, not a claim of exact photographic reconstruction or finished game integration.

## Files and evidence

- Saved asset: [BlackCloak.blend](../../Assets/BlackCloak.blend).
- Package: [BlackCloak_Package.zip](../../Exports/BlackCloak_Package.zip).
- Side-by-side comparison: [COMPARE.html](../../Exports/BlackCloak/COMPARE.html).
- Actual source render: [front](../../Renders/BlackCloak/ReferenceRevision/Revision_Front.png).
- Actual export render: [reimported GLB](../../Renders/BlackCloak/ReferenceRevision/Reimported_GLB_Front.png).
- Technical checks and hashes: [asset_report.json](../../Exports/BlackCloak/asset_report.json).
- Previous source preserved as `Backups/BlackCloak_before_reference_revision.blend`.
