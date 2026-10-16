# K4 note: why "small-part bare-metal texels" went 8,331 → 19,463 (2026-10-16, investigation only)

**Cause: the gate measures wrong. The paint is fine.** `Scripts/guns/sniper/sr_closeup.py` `maps_metrics()`
compares two images whose rows run in opposite directions:
- `Metal_ids.npy` and `Metal_pos.npy` are stored bottom-up, in Blender pixel order (`bake_meta.json` → `encoding.rows`).
- `T_SR01_Metal_ORM.png` is stored top-down, like any PNG.

The gate never flips one to match the other. K4 therefore counts the metallic texels that sit in the *vertically
mirrored* position of each small part. Those mirrored spots mostly land on the bolt, receiver and rail islands.

On the shipped maps, with the rows lined up, **K4 = 0**.

## How K4 is computed
- `small` = texels whose bake id (R channel of `scratch/w2/bake/Metal_ids.npy`) is one of `SMALL`: pins,
  fasteners, rail_screws, safety, trigger, mag_release.
- "Metal" = ORM B channel > 0.5.
- `small_parts_metal_texels` = the count of texels that are both.
- The paint itself (`sr_paint.py`) cannot put metal on small parts:
  - phosphate chips skip `SMALL_PARTS` (W4b, line 323);
  - anodized bright wear skips them (R2, line 277).

## Evidence
Scripts and outputs are in `scratch/k4/` (`probe.py` / `probe.json`, `orient.py` / `orient_*.json`,
`scope_orient.txt`).

**Current shipped `Exports/Guns/SR01/Textures/T_SR01_Metal_ORM.png` + current bake ids:**

| Measure | as the gate reads it | rows flipped (correct) |
|---|---|---|
| small-part metallic texels (K4) | **19,463** (the gate value, reproduced exactly) | **0** |
| bolt texels metallic (bolt_polish = metal 1 everywhere) | 24 % | 82 % |
| receiver texels metallic (phosphate, should be ~0) | 20 % | 0 % |
| bolt body (X ≥ 372) roughness P5 / P50 / P95 (K2) | 0.384 / 0.627 / 0.89 | **0.565 / 0.608 / 0.655** |
| scope body anodize roughness P50 (K5, same bug) | 0.60 | 0.51 |

The flipped orientation is the physically consistent one:
- the bolt reads as metal;
- the receiver reads as dielectric;
- the R2 bolt floor (0.46) is visible.

With the gate's orientation, a quarter of the "bolt" texels are metal and a fifth of the "receiver" texels are.

**Why the number changes between rounds:**
- The value is just whatever metal happens to lie in the mirrored spots. It moves every time the Metal set is
  re-unwrapped or repacked.
- The R2 final chain rebuilt the Metal set from nothing, and its layout changed. The ORM AO-channel correlation
  between round 1's shipped map and the current one is only 0.47, and 484,819 metal texels differ.
- So 13,254 (r1), 8,331 (R2 first pass, whose bake was a later pass than its exports) and 19,463 (R2 final) cannot be
  compared with each other. None of them describes the small parts.

**Round 1 can't be judged with today's data.** The round-1 bake ids were overwritten. Reading round 1's ORM with the
current ids gives 11,990 flipped and 18,453 unflipped, but the layout has changed, so those numbers mean nothing. It
is plausible that round 1 really had some bright anodize wear on the screws, safety and release, because R2 added the
`wl &= ~SMALL_PARTS` fix for exactly that. The current maps no longer have any.

## Visible?
No. The shipped maps have no bare metal on any small part, so nothing shows at normal or close range. The K4 FAIL in
`gates/closeup_r2.json` is a false alarm.

Side effects of the same bug:
- **K2** really passes its P5 ≥ 0.45 test (0.565). REALISM_R2_REPORT.md's note "the floor did not reach the shipped
  ORM" is wrong.
- **K5** anodize roughness is 0.51 and still passes (≥ 0.45).
- The lens BC statistics are also misregistered. The lens is probably near-uniform, so the error there is likely
  small, but this was not checked.

## Status: APPLIED (2026-10-16)
- `sr_closeup.py`: the bake arrays are flipped to PNG row order, and a registration guard checks bolt > 0.5 / receiver
  < 0.05 metal (measured 0.817 / 0.0). New `--reuse-k1` flag skips the Blender K1 step.
- `scratch/r2/before_metrics.json` is marked `invalid`; K2's P50 test falls back to the absolute ≥ 0.45 bar.
- Re-run: K2 P5 0.565 pass, K4 0 pass, K5 anodize 0.51 pass. The gate file is still fail, on K1 / K3 / K9 / K10
  (K9 because of the form gate's failed list, not K1–K4). Old gate file: `scratch/k4/closeup_r2_before_fix.json`.
- Not done: the grep of other checks that read `*_ids.npy` / `*_pos.npy` alongside a PNG.
- Nothing was re-exported; W5 stays valid.

## Fix proposal (as written before it was applied)
1. **Fix the measurement only.** No generator, paint or export change is needed.
   - In `sr_closeup.py` `maps_metrics()`, flip the bake arrays to PNG row order before comparing:
     `np.load(...)[::-1]` for `Metal_ids`, `Metal_pos` (reshape after the flip), `Scope_Body_ids` and
     `Scope_Lens_ids`.
   - Alternatively, flip the PNG arrays with `[::-1]`.
   - Add a guard: assert that the bolt's metallic fraction is > 0.5 and the receiver's is < 0.05, so a misregistration
     fails loudly.
   - Grep any other gate or check that reads `*_ids.npy` / `*_pos.npy` together with a PNG. `sr_paint.py` does it
     correctly, otherwise the flipped numbers above would not be clean.
2. **Re-run** `py -3 -B Scripts/guns/sniper/sr_closeup.py --round r2` to rewrite `gates/closeup_r2.json`.
   - The "before" side (`scratch/r2/before_metrics.json`) was measured with the same bug and with ids that no longer
     match round 1's maps. Mark it invalid rather than re-snapshot it: round 1's bake ids are gone.
   - Expected results: K4 = 0 (pass) and K2 P5 0.565 (pass). The P50 relative test needs a valid "before".
   - Note: the script also starts a headless Blender for K1 (`sr_closeup_edges.py`). To stay Blender-free, reuse the
     existing `scratch/r2/K1.json`.
3. **Then:** update K9 (it inherits K1–K4) and correct the K2 / K4 rows in `REALISM_R2_REPORT.md`.
4. **Exports and W5:** nothing is re-exported by this fix, so W5 (37/37 on the current bytes) stays valid. If any
   later change does re-export (paint, geometry, anything in `Exports/Guns/SR01/`), qa_check must run before it and
   **W5 must be re-run on the new bytes**.
