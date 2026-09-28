# Black cloak: reference match review

Historical review of the original version. The asset was subsequently rebuilt; see [REVISION_2_REVIEW.md](REVISION_2_REVIEW.md) for the current revision. The hashes and comparison renders below belong to the original review.

Reviewed: 2026-09-20

**Verdict: FAIL for exact reference likeness.** The saved asset captures the broad idea of a long black cloak with a wrapped collar, layered shoulders and a shoulder fastening. It does not reproduce the supplied reference's silhouette, panel arrangement or individual folds. It should be treated as a preliminary interpretation, not an exact reproduction or a visually approved final asset.

This was a review only. The source Blender file and exported asset geometry were not changed.

## Evidence and method

- Reference: [original reference copy](../../References/BlackCloak/blackcloak.png), verified identical to `C:/Users/Cody/Downloads/blackcloak.png`.
- Actual saved model: [BlackCloak.blend](../../Assets/BlackCloak.blend).
- New renders of that saved model: [front](reference_match_review/SavedAsset_Front.png), [collar and clasp](reference_match_review/SavedAsset_CollarClasp.png), [folds and hem](reference_match_review/SavedAsset_FoldsHem.png).
- The new review renders use a near-front camera and lighter studio background to make the geometry easier to compare. No geometry or asset material changes were made. Differences in brightness alone are not proof of a material mismatch because lighting differs.
- An independent visual review reached the same conclusion: the broad design is recognizable, but the detailed construction and folds do not match.

The supplied reference is one 417 by 674 pixel front image. It cannot establish hidden surfaces, the rear design, physical dimensions or microscopic fabric and hardware construction. No reliable numeric percentage of similarity is asserted.

## Visible differences

Left and right below mean the viewer's left and right in the reference.

| Area | Reference | Saved asset | Result |
| --- | --- | --- | --- |
| Overall silhouette | Irregular, asymmetric outline with a pronounced left hanging wing and distinct right diagonal flap. | Smoother, more regular A-shaped outline; those projections are reduced or differently located. | Major mismatch. |
| Collar volume | Soft scarf-like mass with a wider, irregular base blending into the shoulders. | More cylindrical/conical stack, with a comparatively rigid top and regular band spacing. | Major mismatch. |
| Collar folds | Compressed, uneven diagonal and crossing folds with varying widths and depths. | Repeated broad wrap bands; fold paths and compression do not correspond. | Major mismatch. |
| Shoulder and chest fabric | Gathering near the fastening generates diagonal tension folds and interrupted flatter areas. | Broad, smooth shoulder cap with little corresponding local gathering. | Major mismatch. |
| Upper layer edges | Asymmetric short overlaps, independently shaped corners and uneven lengths. | More regular, nearly parallel mantle boundaries with different endpoints. | Major mismatch. |
| Left gathered fall | A distinctive projecting corner and overlapping hanging layers. | A smaller/differently shaped fall with regular pleats radiating from the fastening. | Major mismatch. |
| Right outer flap | Large diagonal layer with a particular pointed termination below the waist. | Layer length, contour and termination differ. | Major mismatch. |
| Front overlap and opening | Angular, asymmetric opening bounded by independently hanging broad panels. | Different crossing-panel path, opening shape and exposed inner panel. | Major mismatch. |
| Main long folds | Varied widths; broad quiet planes alternate with deep valleys and shorter interrupted folds. | Repetitive curtain-like pleats continue too consistently down the fabric. | Major mismatch. Individual folds cannot be approved. |
| Hem and panel tips | Uneven angular/pointed ends, a diagonal front edge and small irregular notches on the left layers. | More rounded/scalloped terminations and repeated wave-like edge shapes. | Visible mismatch. |
| Edge treatment | Soft fabric turns and less uniform edge contours. | Thin, consistently rolled edges that read as more regular outlines. | Visible mismatch. |
| Fastening | Small, dark, dense circular feature on the left shoulder. | Brighter open ring with a conspicuous pin and broad tabs; it projects more visibly from the cloth. | Visible appearance mismatch. Exact reference hardware construction is unresolved at this resolution. |
| Fabric surface | Subdued fine cloth grain and soft matte highlights. | Coarser, rippled/pebbled-looking surface detail and stronger highlights. | Visible appearance mismatch; texture scale needs revision, with roughness judged under comparable lighting. |
| Rear and hidden construction | Not shown. | Authored interpretation. | Unverifiable from the supplied reference. |

## Correction checklist for future work

The following items are open. Listing them does not imply that corrections have been made.

- [ ] Trace the visible reference silhouette, panel boundaries, corners, front opening and fastening location before changing geometry.
- [ ] Rebuild the collar mass and irregular crossing/compression folds to follow the visible reference.
- [ ] Rebuild shoulder gathering and diagonal tension folds around the fastening.
- [ ] Match each visible upper panel's independent length, edge path and corner placement.
- [ ] Restore the left projecting wing and the right diagonal outer flap.
- [ ] Match the front overlap path and the shape of the visible opening.
- [ ] Replace repetitive long pleats with the reference's specific broad planes, valleys and interrupted folds.
- [ ] Match angular hem endpoints and visible small notches without inventing additional distress.
- [ ] Refine soft cloth edge thickness and turns.
- [ ] Reduce fastening brightness and revise its visible size/profile; keep uncertain hidden construction documented.
- [ ] Reduce apparent texture scale and tune matte cloth response under comparable lighting.
- [ ] Render the saved revised model from a matched front view and review each visible region again.
- [ ] After visual revisions pass, regenerate exports and repeat the relevant LOD, material and round-trip checks.
- [ ] Keep unseen rear/hidden detail explicitly marked as interpretation unless further references become available.

## Evidence integrity

The source file hash was unchanged before and after the review renders:

`c79799890aa4998ac7588da06be697fda8381d458c9951adc6a2b0e95a419416`

Reference SHA-256:

`34d9103bf65ddda7950ad3a38af287219455d3a42d0daa57ed8def3dc2507c2f`

Machine-readable record: [evidence.json](reference_match_review/evidence.json).
