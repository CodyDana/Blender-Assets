# HP01 W0 report (2026-10-14)

**Scope:** the W0 study only: measurement, traces, craft study, spec and build plan.

**What was not done:**
- No geometry, no Blender, no Unreal.
- No commit, push, merge or delete.
- Nothing outside `WorkFiles/guns/pistol/` was edited. gunlib, `gun_standard.json` and `qa_gun.py` were only read.

**Lock:** `HP01` (claude) is held and was not released. **Spend:** about $5.5 of the $12 cap.

## Done

| Deliverable | State |
|---|---|
| `MEASURE.md`, `hp01_measured.json`, `traces/` (LEFT with holes, RIGHT mirrored, TOP), `HP01_TRACE_OVERLAY.png` | done; the chain was re-run several times with identical numbers |
| `HP01_STUDY.md` | R1-R18, sides, scale ruling, self-consistency, IP deltas D1-D8 (not applied), the close-up design rules, Q1-Q14 with defaults |
| `CRAFT_STUDY.md`, `craft_parts.json` | process / bevel / finish per part; the real-pattern small-part rulings; fastener sources; texel classes |
| `hp01_spec.json` (`tools/make_spec.py`) | **S0 pass**: 0 missing fields, 19 checks, deny list clean (gunlib `GUN_DENY`, 48 terms) |
| `HP01_BUILD_PLAN.md`, `hp01_interface.json` | W1a-W6 with gates and rough cost (~$80-130 total); 7 clips with notifies; FP / TP; gunlib proposals GL1-GL9 |
| `HP01_DESIGN_SHEET.png` (`tools/design_sheet.py`) | done; drawn from the spec |

## Findings that matter

1. **The RIGHT view is a mirrored redraw of LEFT** (IoU 0.995). No handed part is drawn: no ejection port, no
   magazine release. The rulings R2, R5, R7 and R8 handle it.
2. **Width.** TOP draws the slide 46.9 mm wide, about 45 % wider than the real class (~32). The 3/4 view implies about
   17 % narrower than TOP. **Q1 is the one question to answer before W1.** The default follows the TOP view (the
   user's bar) through the single parameter `K_Y`.
3. **Ruler +9.5 %.** The scale rests on 273 mm overall (2.1097 px/mm). The sheet is 7 % taller than the class; kept.
4. **Mechanism:** fixed barrel and rib (`body`), the slide running under the rib, an ejection window that opens only
   when the slide is back, and the front plate on the slide.

## Left for later

- The user's rulings on Q1 (width) and, optionally, Q2-Q14.
- Commit by the user. The PNG deliverables sit under the `WorkFiles/**/*.png` ignore rule; the carbine's PNGs are in
  git as LFS pointers, so they need `git add -f`.
- **Don't commit** `scratch/`. It holds zooms, masks and npz/npy probe files: `masks.npz`, `stage1.json`,
  `top_6.npy`, `top_9.npy`.
- The gun chat to consider GL1-GL9.
- W1 on the user's go.

## Blocked / caveats

- WebSearch was not permitted. The class figures (height ~159, width ~32, cartridge overall length 40.4) are from the
  study table and general knowledge, marked [K]. Only the slide travel depends on them, with 7.6 mm of margin.
- During the hand reads, the first rear reads were taken in zoom pixels instead of grid labels. I caught this on the
  overlay, re-read the values and re-ran everything; the numbers in the files are the corrected ones.
