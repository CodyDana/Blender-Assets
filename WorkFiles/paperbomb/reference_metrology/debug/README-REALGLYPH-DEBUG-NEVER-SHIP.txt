DEBUG - NEVER SHIP
==================
Every DEBUG_NEVER_SHIP_RG_*.png in this directory is a measurement aid: a crop,
a magnification, or an overlay drawn on top of
References/PaperBomb/paperbomb_guide_v2_real_glyphs.png.

They exist so a human can check the metrology by eye. They are NOT artwork,
they are NOT inputs to any build, and nothing under Scripts/ may read this
directory. paperbomb_art.py refuses to open the guides
(FORBIDDEN_INPUT_FRAGMENTS / GuideAccess / no_guide_access) and that gate also
keeps these derived rasters out of the product.

Do not copy, trace, sample, threshold or vectorise anything here.
