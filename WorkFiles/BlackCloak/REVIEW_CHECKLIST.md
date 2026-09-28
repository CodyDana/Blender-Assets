# Black cloak review

## Unreal recoloring — completed 2026-09-23

- [x] Add `CloakColor`, with adjustable fabric detail, normal strength and roughness.
- [x] Keep cloth tint separate from the steel clasp and leather.
- [x] Supply Black, Crimson, Navy and Ivory material instances.
- [x] Import static and skeletal LOD0 meshes; persist the 152-bone skeleton dependency.
- [x] Reload saved assets in Unreal 5.8.2, compile the shader and verify independent dynamic colors on two components (64 checks passed).
- [x] Package the native Unreal project, color previews and fixed/runtime color instructions; verify all 13 packaged uasset hashes and ZIP integrity.

Delivery: `Exports/BlackCloak_Package.zip`; setup: `Exports/BlackCloak/RECOLOR.md`. Previews use Blender with the same material formula; they are not Unreal screenshots. Recoloring is complete. Reference likeness and cloth/gameplay integration retain the limits below.

**Current work: revision 2 has been rebuilt and exported from measured reference landmarks.** See [REVISION_2_REVIEW.md](REVISION_2_REVIEW.md) for completed changes, current evidence and remaining limits. The audit below describes the original version. Exact reproduction of every wrinkle is still not certified.

Scope: separate asset from `C:/Users/Cody/Downloads/blackcloak.png`. All Jin Mu-Won character/hair/clothing work is paused in this fork.

**Visual approval status, 2026-09-20: NOT APPROVED.** The checked items below record build/export work, not exact reference likeness. A strict comparison of the saved asset found substantial mismatches in silhouette, collar, panel layout, folds, hems, fastening and fabric appearance. See [REFERENCE_MATCH_REVIEW.md](REFERENCE_MATCH_REVIEW.md) for evidence and the open correction checklist. Do not treat this asset as an exact reproduction or the visual review as complete.

- [ ] Pass strict visible reference comparison after the documented corrections.
- [ ] Approve individual visible folds, panel edges, collar and fastening placement against the supplied front image.

- [x] Read the supplied image and preserve an unchanged reference copy.
- [x] Build separate long drape, asymmetric capelets, diagonal front overlap and gathered side fall.
- [x] Build a high collar from distinct scarf bands around an inner cowl.
- [x] Add the shoulder ring, fastening pin and dark leather tabs.
- [x] Create tileable woven-fabric color, roughness and normal maps.
- [x] Review real front, rear, three-quarter and collar renders; correct rigid early shoulders and excessive sheen.
- [x] Keep editable fabric surfaces, thickness modifiers and cloth pin groups.
- [x] Export FBX, GLB, LOD1/2 and optional shared-skeleton attachment versions.
- [x] Round-trip the exports and check UVs, geometry counts and skeleton structure.
- [x] Complete final exported material/LOD visual comparison and package.

Limits: the single reference does not show the rear; the back is an interpretation. Runtime cloth simulation, movement collision and actual in-game character fit are separate unfinished integration work. The skeletal attachment weights do not simulate fabric.

Export visual issue fixed: the initial GLB became white because the exporter emitted white sheen at full strength. The portable material disables that optional lobe; the Blender source retains its restrained sheen. The corrected GLB was reimported and rendered with its own embedded materials and textures. It retains the black color and cloth detail. LOD1 retains the drape; LOD2 simplifies edges and shows visible mantle-edge faceting in close inspection, so it is reserved for distance.

Delivery: Assets/BlackCloak.blend; Exports/BlackCloak/ contains static and skeletal FBX LODs, textured GLB, maps, pin-weight CSV, README and asset_report.json. Exports/BlackCloak_Package.zip bundles these deliverables and saved-asset previews. No character, hair or default garment deliverable was edited.
