# Snow Flower — detailed reference-fidelity review

Review date: 2026-09-18. Scope: visual design accuracy of the saved full-detail master against the supplied reference.

**Verdict: revisions required before visual sign-off.**

The current asset is recognizable as the supplied Snow Flower design, but it does not pass a close reference-fidelity review. The most important gaps are construction and decorative composition, not polygon count. Previous topology and export checks remain valid; they do not establish design accuracy.

[Open the illustrated comparison](REFERENCE_REVIEW.html)

## What already matches

- Long narrow sword, black-and-silver palette, thin blade and gently swept asymmetric point.
- Floral theme, major hilt components, side cord, blossom charm and tassel.
- Broad grip-to-blade relationship. Exact contour and relative widths still need aligned comparison.

## Detailed findings and correction order

### 01. Guard construction — Major revision

The reference has compact, swept angular shoulders, stepped borders and dense recessed scrollwork. The model has large rounded open loops and an oversized, evenly arranged leaf fan. The lower pointed lacework and decorated transition into the grip are simplified.

**Correction and acceptance criterion:** Rebuild the outer silhouette and layered backing first. Reduce open loop area, restore angular shoulders, tuck the lateral leaves and add the recessed scrollwork and pointed lower frame. Verify an aligned front silhouette before surface detailing.

### 02. Blade branches and clusters — Major revision

The reference has substantial, uneven woody branches with knots, short offshoots and clustered blossoms. The model uses thin, smooth wire-like stems, long diagonal offshoots and small isolated flowers. Some buds read as detached dots. The primary decorative composition does not yet match.

**Correction and acceptance criterion:** Trace the major cluster locations separately for front and back. Build a tapered irregular trunk with short connected twigs and attached buds. Establish larger focal blossoms and dense clusters before minor filler details; judge their readability at full-sword scale.

### 03. Grip wrap and ornament — Major revision

The reference wrap is close, flat and visibly crossed, with pebbled leather and connected silver ornament. The model reads as thick padded spiral bands with deep, regular gaps and three isolated floral accents. Two mathematical helices do not produce the same visible interlaced construction.

**Correction and acceptance criterion:** Flatten the strips and establish readable over-under crossings on the front and side. Reduce raised band edges and deep gaps. Reconstruct the larger connected silver motifs and the shaped lower collar.

### 04. Pommel envelope and engraving — Major revision

The model adds prominent front/back flower plates to a broad drum. The reference close-up presents a compact circular cap, recessed flower, concentric borders and dense surrounding engraving. The current model is conspicuously bulkier and emptier around the flower.

**Correction and acceptance criterion:** Resolve cap orientation against all three reference views, then reduce the projecting plate assembly to the compact envelope. Recess the main flower and reconstruct the concentric rim and ornamental ring. Hidden mounting details remain an interpretation.

### 05. Blossom anatomy and finish — Revision required

Repeated smooth oval petals and bead centers make the model look uniform and inflated. Reference flowers have more individual contours, fine center markings, controlled cupping and varied sizes. Broad cloudy metal variation and consistently bright wire borders also differ from the finer worked metal in the sheet.

**Correction and acceptance criterion:** Match one principal blossom closely, then create controlled variants for the blade, guard and pommel. Use finer petal borders and centers. Compare neutral lighting before changing material values; refine directional grain and localized wear after geometry is corrected.

### 06. Tassel and small fittings — Revision required

The main cord, charm, bead/cap and bundle are present. The model bundle is narrower and straighter, with a wire-like spread at its ends; it hangs below the guard center, while the reference ends roughly at that level. The charm silhouette, gathered cap, cord texture and knots are simplified.

**Correction and acceptance criterion:** Match the attachment, charm, cap and bundle endpoints at equal sword height. Increase controlled fullness, refine the gathered cap and braided/knotted appearance, and match the sharper layered charm silhouette. Keep dynamics as a separate game-integration task.

## Evidence and limits

The reference is a concept sheet rather than a dimensioned orthographic specification. Perspective, view-to-view differences and hidden construction limit certainty. Absolute dimensions are modeling assumptions. Lighting and backgrounds differ, so exact roughness, color and metalness changes cannot be inferred from these renders alone. Pommel orientation needs resolution across all views. Comparisons below are detail crops, not registered geometric overlays.

Reviewed front, back, side, oblique, guard, blade and pommel renders of the full-detail master. The same primary design is present in the LOD0 export. Low-LOD simplification is not the cause of these discrepancies.

Reference: `References/SnowFlower/SnowFlower_user_reference.png`.
Render evidence: `Renders/SnowFlower/SnowFlower_{Front,Back,Side,Oblique,Guard,BladeDetail,Pommel}.png`.
Master reviewed: `Assets/SnowFlower/SnowFlower_Master.blend`, SHA-256 `edd6fa25465b164fcf034ce913edfee296d55c3012bc7b9e177ee0bcb041882d`.

## Follow-up checklist

- [x] Compare full-detail front/back silhouette and major components against the reference.
- [x] Inspect guard, blade ornament, grip, pommel, floral anatomy, materials and tassel.
- [x] Obtain an independent second visual review and reconcile findings.
- [ ] Match guard silhouette and layered metalwork.
- [ ] Match front/back blade branch hierarchy and floral cluster placement.
- [ ] Rebuild flat crossed grip wrap, connected ornament and lower collar.
- [ ] Resolve and rebuild the compact decorated pommel.
- [ ] Refine blossom variants, silver borders and surface detail.
- [ ] Match tassel silhouette, endpoint and small fittings.
- [ ] Compare revised front/back silhouettes at equal sword height and inspect details under neutral lighting.
- [ ] Re-bake, re-export and repeat relevant structural/export checks after geometry changes.

This turn produced a review and correction checklist. No sword geometry, materials or exports were changed. The existing ZIP contains the earlier technical handoff and has not been repackaged for this review.
