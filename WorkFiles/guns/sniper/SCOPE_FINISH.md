# SR-01 scope finish (texture-only), 2026-10-16

Branch `claude/sniper-sr01-scope`, lock SR01 (claude). This targets FINAL_JUDGES 6 / 11: the lens read as pure black, and the scope looked sterile.

## What changed
- `Scripts/guns/sniper/sr_surface.py`
  - `FIN["lens"]`: the centre is now deep green-black (26,36,33). The coating has three phases: violet (86,50,128), amber (132,94,36) and green (48,108,76).
  - The coat strengthens toward the rim (`coat_ring` smoothstep 0.45 to 0.98, strength 0.78). A faint inner coat ring was added (`inner_ring`).
  - The lens stays in the opaque glossy slot (Q6): metal 0, rough 0.02 to 0.04, with the convex normal.
  - New `POWER_MARKS` with generic marks only:
    - power-ring numerals 5 6 8 10 15 20 25, one in each of 7 of the 8 scallop gaps (the bottom gap is left blank);
    - a tick at each numeral on the ring's rear band;
    - a fixed index line on top of the eyepiece;
    - a diopter scale by the eyecup: 9 ticks, 6 degrees apart, with long ticks at the centre and both ends.
- `Scripts/guns/sniper/sr_paint.py`
  - The lens code now blends the three coat phases.
  - A new Scope_Body block paints the power ring and diopter marks the same way as the turret marks: paint fill (214,214,206), rough 0.55, -0.03 mm engraving. It painted 985 texels.
- Re-painted the scope only (`SR01_SURFACE_TARGET=scope sr_paint.py`, from the existing w2_scope bakes).
- Re-exported the scope only, through `sr_attach.py` (SR01_ATTACH=scope) as `run_rig_mag.sh` does: qa_check True [], ATTACH_DONE. LOD0 has 9,938 triangles, LOD1 4,464 and LOD2 1,454.
- A fresh-process verify on the exported bytes (`sr_verify_static.py`) gave `[SR01-scopev] pass []`.
- Visual check: crops of the texture are in `scratch/scope_finish/` (body_marks.png, lens_new.png). The numerals and ticks are crisp.
- **Not yet checked in a 3D render:** whether the numerals face the right way on the model. The UV islands could mirror them. Do one close-up render to confirm.

## Byte identity
Every other file under `Exports/Guns/SR01/` has an unchanged sha256, including SM_SR01, SK_SR01*, SM_SR01_Mag and all T_SR01_* files. Only these files changed:

| file | sha256 |
|---|---|
| SM_Att_Scope_LongRange.fbx | 4b32201206bdd08df9883b3db99e60a22a19d7dcdcbe1f463a9d8ba10aa59dd1 |
| T_Att_Scope_LongRange_Scope_Body_BC.png | ff6e859893ad0feeae79be7b6f0612d64bc4ccffa8fa1ed73b29de7a755b6479 |
| T_Att_Scope_LongRange_Scope_Body_N.png | 21815534b98e614712c17d7055580d8030d515c6407a6d8c3675159e49c095e2 |
| T_Att_Scope_LongRange_Scope_Body_ORM.png | 653e54f2c6a6faa4e5a577dde1b39e33ab72364a41e63976139f47675bca11c2 |
| T_Att_Scope_LongRange_Scope_Lens_BC.png | 7db714d663e5750d00320dab13c75df0c802bad7ee9040ee61c91a61b2095c4b |

Also modified: `Assets/Guns/Att_Scope_LongRange.blend` (written by sr_attach) and `gates/scope_export.json`.

## Gates
- qa_check: pass. scope_export (fresh-process verify): pass.
- A1 to A5 (`sr_scope_gates.py`) and the W2 scope rows (`sr_w2_gates.py`): `sr_scope_gates.py` ran with no traceback, but my grep didn't print the A-gate summary. Read `scratch/w3/logs/scope_gates.log` to confirm A1 to A5. In `sr_w2_gates.py`, the only failure is "scope: B9 density Scope_Body class C". That is the known, unchanged UV near-miss (P5 40.9 vs 41.1, already noted in the gates file). The UV layout was not touched in this round.

## Left for the main chat
- Do one close-up render of the eyepiece and objective to confirm the numerals read the right way and the coat looks good under the rig.
- Run the Unreal check of the new textures.
- Commit.
