DEBUG - NEVER SHIP
==================

Everything in this folder is diagnostic output from the paper-bomb reference
metrology pass. Nothing here may be consumed by a build, shipped in a pack, or
used as source art. Several agents write here; this note applies to all of it.

From the INK AND COLOUR pass (see ../INK_NOTES.md and ../ink_colour.json):

  DEBUG_NEVER_SHIP_ring_and_glyph_schematic.png
      DRAWN FROM MEASURED NUMBERS ONLY. Fitted enso-ring ellipses (mid-stroke,
      outer and inner) and centre-glyph bounding boxes for V1 (red), V2
      (orange) and our build (blue), over a 70 x 156 mm card outline with a
      7.6 mm corner chamfer. It contains no pixel of either reference image and
      is not a crop, mask, trace, threshold or derivative of one.

  probe01.json          file facts for both references and our four shipped
                        maps, plus the stored-vs-linear cross-check that proved
                        Blender's Image.pixels returns stored sRGB for 8-bit
                        PNGs.
  stage1_rectify.json   fitted tag quadrilaterals, edge angles, keystone
                        diagnostics and the rectification homographies.
  diag_edges.py         one-shot: why the first edge fit traced ink, not paper.
  diag_seg.py           one-shot: ink/red threshold selection from the data.
  patch_sev.py          one-shot: severity ranking helper.

Rectified reference arrays were cached only in the session scratchpad, never
under the project. If a _cache/ directory appears here it means PB_SCRATCH was
unset on some run; delete it.

Other files in this folder belong to the layout and typography passes.
