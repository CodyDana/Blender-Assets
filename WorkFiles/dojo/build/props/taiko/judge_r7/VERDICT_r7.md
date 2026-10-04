FAIL

The drum is closer this round, but two things are still visibly off. First, the ring handle, which the user asked for this round: the plate, rivets and washer outline match, but the ring and pivot sit too high and every piece looks too matte. Second, the skirt (items 2 and 3 below). Everything else passes on my own measurements of the final files.

What passes:
- **Tacks:** 324 tacks with 0 intersecting pairs. Measured by phase folding in the photo camera:
  - In-row pitch is 30.3 px against the photo's 30.07.
  - Row spacing is 21.45 px against 19.8, which is 0.86 of the 25 px tack width (target 0.85 ± 0.03).
  - The rows are offset 0.58 of a pitch against the photo's 0.63, so the upper row sits in the lower row's gaps.
- **Gold:** the front-centre profile matches. Ours turns warm at row 254, saturation 0.18, against the photo's 0.22. Hue is 36–38 in both, and the gold zone's saturation is 0.23–0.30 against 0.22–0.28. There are no drip streaks.
- **Lower collar:** there is no black slot. The darkest band is luminance 39–49 (10th percentile 18–20), against the photo's 37–47 (19–21). The lower gold fades from saturation 0.31 to 0.12, against 0.33 to 0.14.
- **Felt:** +0.098 mm in every contact vertex (174), with 0 drum-to-felt pairs and 0 drum-to-wood pairs.
- **Triangles:** 58,856 / 29,428 / 14,714 for LOD0 / LOD1 / LOD2. Stand 2,984, stick 840.
- **No regressions:**
  - Upper skirt and body outlines are within 5 px per row on both sides.
  - Panel C bulge is unchanged: head/belly 0.791 in both.
  - The stand end elevation looks clean, and the layout still places 2 sticks.
- **Ring hardware, the parts that match:**
  - The plate outline sits on the photo's within about 2 px over its whole upper half.
  - The rivets are 22 px against 20 px, at the same positions.
  - The washer has 12 petals: its notches fall at −75/−44/−14/15/44/75° in ours and −74/−43/−13/15/44/73° in the photo.
  - Washer size is 111×102 px against 106×101.

Remaining differences, most important first:

1. **The ring and pivot hang too high (user request).** In the photo camera:
   - Ring outer edge: top 569 / bottom 661 in ours, against 572 / 674 in the photo.
   - Ring diameter: 92 px against 102. In real size that is about 167 mm against about 172 mm.
   - Ring centre: 10 px below the plate centre, against 16.5 px.
   - The boss sits at the washer centre in ours. In the photo it is 5–6 px below it, and the build's own `ring_trace.json` has the boss 12.4 mm (design units) below the plate centre.
   - **Change:**
     - Move the boss about 9 mm (real) down the drum axis, to −X on the +Y handle, and mirror the move on the −Y side.
     - Re-hang the ring from the boss at that point and raise its outer diameter from 166.8 to about 172 mm, keeping the 17.7 mm tube.
     - Keep the ring clear of the plate, washer and barrel. They have 0 intersecting pairs now, and the ring through the boss is its pivot, as intended.
   - **Target in the photo camera:** ring bottom at row 672 ± 2 and top at 572 ± 2.

2. **The ring hardware finish does not match the photo (user request).**
   - **Plate, ring and boss are grey and matte.** Our plate is luminance 32–42. The photo's is 4–20, which is 5–25 after scaling to our exposure (head white 186 in the photo, 235 in ours).
     - **Change:** iron base colour to about sRGB 10/255, roughness about 0.25–0.3, and a 1–1.5 mm bevel round the plate outline. The photo's stepped edges each catch a thin highlight line.
   - **Washer is flat and paper-like.** Its tone spread is 144–151, against the photo's 86–114 (top petals dark olive, right petals pale).
     - **Change, shape:** dome the washer about 3–4 mm toward the boss. Emboss each petal as a convex lobe about 1.5–2 mm high, with a shallow radial crease between petals and a small notch at each petal tip (the photo shows split tips near ±55–62°).
     - **Change, brass:** hue 42–45 and saturation about 0.2 (ours is 39–40 and 0.28), metallic with roughness about 0.35.
   - **The ring reads as a flat band with a double rim, and the boss outline is faceted** (`t7/ring_layout.png`, `t7/compare_ring.png`).
     - **Change:** at least 12 smooth cross-section segments on the ring and at least 24 on the boss dome. The photo shows a single thin specular streak along a round rod.

3. **The skirt reads as a thin segmented tube glued under a flat apron.** The photo shows hide rolling outward (`judge_r7/pair_upper_band_centre.png`, `pair_upper_left_ear.png`, `pair_lower_collar.png`, `t7/closeup_skirt.png`).
   - **Apron to lip:** the tube is about the right size (the lip band covers rows 296–318 in both), but a hard crease and shadow line runs along its top.
     - **Change:** a tangent-continuous fillet of 8 mm or more from apron to lip, so the hide curls over with no shadow seam.
   - **Slits:** they render as 1–2 px hairline cracks; the photo's are open V's with a visible 4–6 px dark interior at the hem, about 20 px tall.
     - **Change:** taper and round the lip into each slit, with no flat end caps. Open the visible gap to 10–15 mm real at the hem, so the dark interior shows from the photo camera.
   - **White shards:** flat white slivers show at the hem beside the ears, left and right in `compare_skirt.png` and `closeup_skirt.png`.
     - **Change:** remap the lip's underside and the slit faces onto the gold collar zone of the texture.
   - **Ears:** ours are thin folded sheets with angular pleats; the photo's are thick rounded rolls.
     - **Change:** give the ears the lip's full roll thickness, about 30 mm real.
   - **Lower skirt:** apply the same lip, slit and ear changes there. It currently shows a uniform thin tube with tick slits.
   - **Band bottom (minor):** there is a faint ledge where the white band meets the apron. Smooth it.

4. **The lower-left outline misses, and part of that is the photo camera fit.**
   - Ours sits 8–15 px inside the photo on rows 799–891 at the left. The bottom outline is 8–12 px high across all columns: photo 980 against ours 972 at x 524.
   - Our head ellipse is more open than the photo's: minor axis 55.7 px against 51.6, which means our camera looks down slightly more steeply.
   - **Change:** refit the `photo_cam.py` elevation so the head ellipse's minor axis matches 51.6 px. Then re-measure the lower skirt rows, and fit the lower-left lobe only to whatever is still outside ±8 px.

5. **Minor: the wood seat is 0.03 mm short.** The nearest drum vertex to the wood is 2.97 mm, against a 3 mm or more target. The nearest wood vertex to the drum is 3.12 mm. **Change:** move the seat faces 0.1 mm outward.

6. **Optional:**
   - Our tack rows are about 1.7 px (8%) further apart than the photo's. If the 1.11 mm diagonal dome gap allows, cut the axial row spacing from 32 to about 30.5 mm while keeping the gap at 0.2 mm or more.
   - The photo's plate is turned about 1.6° (its bottom tip sits 7–10 px right of its top tip; ours is 2 px). Match it only if the trace confirms it.

Out of scope, noted only: the wood grain, the lighter lacquer, and our renders being brighter overall (head 235 against 186).

Everything I made is in `C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/props/taiko/judge_r7/`:
- **Scripts:**
  - `pairs.py`: builds the aligned photo-camera image and the pair crops
  - `tack_fold.py`: the tack phase-fold measurement
  - `geo_check.py`: geometry checks on the exported FBX
  - `ring_segs.py`: an inconclusive probe of the ring and boss segment counts, so the segment numbers in item 2 come from looking only
- **Results:** `geo_check.json`, `tack_fold.json`, `sil_rows.json`
- **Images:**
  - aligned copies: `photo.png`, `ours_aligned.png`
  - pair crops: `pair_full.png`, `pair_upper_band_centre.png`, `pair_upper_left_ear.png`, `pair_upper_right_ear.png`, `pair_lower_collar.png`, `pair_ring.png`
  - ring and washer close-ups: `ring_grid.png`, `ring_grid5.png`, `washer_photo.png`, `washer_ours.png`, `plate_outline_overlay.png`
  - tack masks: `tack_fold_pair.png`