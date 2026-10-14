# SR01 W0 run report (2026-10-12)

**Run:** unattended Agent SDK session in worktree `sniper-sr01` (branch `claude/sniper-sr01`, from e77f0ce9).
**Scope:** stage 1 only (study, measurement, spec, build plan). Nothing was committed, pushed, merged or deleted.
Neither Blender nor Unreal was run. Lock `SR01` stays claimed (agent `claude`); no other lock or folder was touched.

## Done

- **Sides:** checked by handed features. The labels are swapped (sheet LEFT = gun right).
- **Tracer:** `tools/trace_reference.py`, new for the sniper; `refimg.py` and `gridzoom.py` are copied from the SMG,
  unchanged. It writes the outlines for GR, GL, TOP and Q34, 20 labelled GR parts, the face features,
  `sr01_measured.json` and `SR01_TRACE_OVERLAY.png`.
  - Two methods are new: a TOP edge detector that ignores the floor shadow, and hole rules for the low-chroma OD
    paint.
- **Scale:** 1100 mm from eight sheet anchors (see Q1).
- **Craft:** `craft_parts.json` and `CRAFT_STUDY.md`, with rulings RP1-RP15.
- **Plan:** `sr01_interface.json` and `SR01_BUILD_PLAN.md`: stages W1-W6 with gates and rough costs, plus gunlib
  proposals P1-P9 for the gun chat.
- **Spec:** `tools/make_spec.py` writes `sr01_spec.json`: 25 parts, 13 bones, 20 + 5 + 5 sockets and 8 clips.
  - It computes the bipod clearances in both poses (0.5 deg sweep), the bolt and knob path against the scope, and
    the leverage of the mag-release paddle.
  - **S0 PASS:** 0 missing fields and 0 of 33 consistency checks failed. The deny list is clean.
- **Design sheet:** `tools/design_sheet.py` draws `SR01_DESIGN_SHEET.png`, with the bipod folded and deployed, a
  front view of the deployed bipod with cant, the TOP view, and the mechanisms.
- **Docs:** `SR01_STUDY.md` (decisions R1-R22, open questions Q1-Q6) and `MEASUREMENT_NOTES.md`.

## Findings worth the user's eye

1. **The 3/4 view shows the bipod folded, not deployed.** No view of the sheet shows the deployed pose, so it comes
   from the real pattern only.
2. **Scale 1100 mm, not the study's 1270.** The sheet's 34 mm scope tube fixes it. At 1270 the tube would be 39 mm.
3. Two changes are declared deviations from the sheet:
   - the mag-release paddle sits 3.4 mm behind the drawn lever, so it has room to move;
   - the folded feet are wider in TOP than drawn (76 vs ~60 mm).

## Left for later

- **W1 opens with a real-photo pass** (local only, never committed). This run gathered no photos (unattended, no go),
  so rulings RP1, RP5, RP10 and RP15 rest on general knowledge until that pass.
- The GL fastener heads are read at W1.
- The provisional sockets (`SupportHand`, `SupportHandBipod`, `CenterOfMass`, `Holster`) are fixed at W1 / W3 / H1.
- The gun chat decides on P1 (the parent bone for `cheek_riser`). Without it the riser goes static.
- PNGs in `WorkFiles/` are git-ignored. The SMG force-added its design sheet and overlay; do the same for
  `SR01_DESIGN_SHEET.png` and `SR01_TRACE_OVERLAY.png` if wanted. `scratch/` stays local, but two throwaway exploration scripts in it (`scratch/explore.py`, `scratch/edges.py`) are
  not git-ignored. Leave them out of the commit; the tools in `tools/` replace them.

## Files (all under `WorkFiles/guns/sniper/`)

`SR01_STUDY.md`, `MEASUREMENT_NOTES.md`, `CRAFT_STUDY.md`, `SR01_BUILD_PLAN.md`, `W0_REPORT.md`, `sr01_spec.json`,
`sr01_measured.json`, `craft_parts.json`, `sr01_interface.json`, `trace/*.json` (+ local PNGs),
`SR01_TRACE_OVERLAY.png`, `SR01_DESIGN_SHEET.png`, `tools/` (refimg, gridzoom, trace_reference, make_spec,
design_sheet), `scratch/` (local only).
