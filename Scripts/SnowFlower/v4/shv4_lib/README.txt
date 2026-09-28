Frozen copies of the sword's sfv4_* helper modules, taken 2026-09-27 from
Backups/SnowFlower_v4_pre_lookmatch_2026-09-27/Scripts/SnowFlower/v4 (identical to the shipped v4 build).
The sheath look-match round imports these FIRST (shv4_* put this folder at the head of sys.path) so the sword
builder's concurrent edits to Scripts/SnowFlower/v4/sfv4_*.py can never change the sheath build mid-run.
The sheath never edits the sword's own sfv4_*.py files.
