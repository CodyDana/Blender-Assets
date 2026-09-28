DEBUG - NEVER SHIP
==================

overlay_reference_vs_ours.png
-----------------------------
1154 x 954 px. Three panels at a common 5 px/mm over a 70 x 156 mm tag:

  LEFT    the V1 guide, cropped to its fitted tag rectangle and resampled.
  MIDDLE  our shipped base colour (Exports/PaperBomb/Textures/T_PaperBomb_BC.png,
          front card island, exact atlas origin: card (0,0) at atlas px (16,16),
          12.923 px/mm), same crop, same scale.
  RIGHT   the difference. Each panel is first normalised to its OWN paper level, so
          the panel shows where ink IS and IS NOT, not the overall value error
          (which is reported as a number instead - see REFERENCE_SPEC.md row 1).
            RED  = the reference has ink we lack
            BLUE = we have ink the reference lacks

Boxes drawn on top are MEASURED VALUES from reference_spec.json, not tracings:
  blue     border rule rectangle        orange  enso ring (mid-stroke ellipse
  green    centre glyph bounding box            plus the +-half-stroke pair)
  cyan     flame emblem bounding box    magenta text columns
  yellow   seal boxes                   grey    card outline with its chamfer

READ WITH CARE - two traps in the difference panel:

  1. The TEXT COLUMNS in the difference panel are not actionable. V1's side and
     lower-centre columns are PSEUDO-GLYPHS - invented squiggles, not characters -
     so the red there is a difference in content, not a defect in our drawing.
     Use V2 for anything about the columns.

  2. The lower-centre column region likewise differs by content, not by error.

This file exists so a human can check that the metrology found the right elements
and to make the size and weight errors visible at a glance. It is a diagnostic
picture that CONTAINS REFERENCE PIXELS. It must never be read by a build, packed
into an asset, used as source art, or shipped in any form. It is not a crop, mask,
trace or threshold intended for reuse - it is a side-by-side for the eye.

Written by the reconciliation pass that produced:
  References/PaperBomb/REFERENCE_SPEC.md
  WorkFiles/paperbomb/reference_metrology/reference_spec.json
