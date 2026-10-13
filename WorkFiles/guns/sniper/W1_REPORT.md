# SR01 W1 report: form (W1a gun + W1b scope attachment)

**Date:** 2026-10-13. **Branch:** `claude/sniper-sr01` (worktree), nothing committed. **Lock:** `SR01` (claude),
asserted by `build_sniper.py`. Blender headless only. No UV, paint, rig, export or Unreal work in this stage.
**Decisions:** Q1-Q6 accepted at their defaults (recorded in `SR01_STUDY.md` section 9).

## What was built

| Item | Where | Notes |
|---|---|---|
| Research pass (RP1, RP5, RP10, RP15) | `CRAFT_STUDY.md` 4.1 | all four confirmed (sources listed); read-only web, nothing downloaded |
| Scripts | `Scripts/guns/sniper/` | `build_sniper.py` (stages blockout / form / scope, lock asserted), `sniper_parts.py` (33 parts), `sr_scope.py`, `sr_blockout.py`, `sr_motion.py`, `sr_silhouette.py`, `sr_fgates.py`, `sr_scope_gates.py`, `sr_gates.py`, `sr_render.py`, `run_sniper.sh`, `sr_common.py` |
| Gun form | `Assets/Guns/SR01.blend` | 33 closed parts, **36,338 tris** (ceiling 50k): chassis with receiver inlet, raceway, port to the stroke, lug grooves + lug-rotation annulus, well (walls, shelf, feed opening, catch window), release clevis + hook window, trigger pocket, riser post bores, barrel channel, slots, dovetail band; 3-lug bolt; fluted barrel (ball-end run-outs); closed-sleeve compensator with baffle; bipod with clamp, swivel yoke + outboard pivot cheeks, detent disks, telescoping bores, 5 notch rings, spool feet |
| Scope attachment form | `Assets/Guns/Att_Scope_LongRange.blend` | built at its mounted pose in gun frame M (Empty `Mount` = attachment origin), 12 parts, **5,884 tris**, 2 slots |
| Gate files | `gates/blockout.json`, `gates/form.json`, `gates/form_magfit.json`, `gates/scope_form.json`, `gates/l8_judges.json` | all values are measured on the built bytes |

## Gate results (numbers)

**Pass:**
- **B3:** 0 intersections on every motion, at these steps and clearances:
  - bolt rotate 0..-60 at 0.5 deg (with proof), clearance 0.20;
  - bolt slide 0..88 at 0.5 mm, 0.153;
  - trigger 0.174; safety 0.199; release 0.153;
  - bipod fold 0..90 at ext 0 and 76, both legs at 1 deg with proof, 0.167;
  - extension 0..76, folded and deployed, 0.200;
  - cant +-15 folded and deployed, with proof, 0.184.
- **G5:** 0 rest intersections.
- **F1-F9 all pass:**
  - F1: feet 2.07 apart.
  - F3: deployed feet at -268.3 / -287.3 / -306.3 / -325.3 / -344.3 (exactly the spec), coplanar 0.0, legs vertical 0.0 deg.
  - F6: knob to the real scope 25.7 mm (20.5 against the blockout stand-in).
  - F7: engagement 1.41, travel 1.76, pad 0.53.
  - F8: riser low stop 0.304.
  - F9: 0.20.
- **B6a** (qa_check topology on the joined twin + deny list) pass. **B7** 33/33 closed. **B8** 36.3k.
- **H1 early:** girth 161 mm at the palm (<= 167), trigger reach 49 mm.
- **Magfit:** M1 0 contacts; M3 well 0.30, receiver 0.50; M4b insert with the paddle pressed 0 hits (min 0.30); M5b only the hook retains.
- **L8** (two independent judges; one fix round used): chassis PLAUSIBLE/PLAUSIBLE, bolt group PLAUSIBLE/PLAUSIBLE, bipod PLAUSIBLE/FAKE. That passes the rule (at most one single-judge FAKE). Round 1 had the bipod FAKE/FAKE.
- **Scope A1-A5 all pass:**
  - A1: lug centre 416.15 = Rail_Top + 2 slots.
  - A2: lugs 0.12 / 0.12 mm in slots 2 and 12.
  - A3: >= 6 mm at rest, 13.7 mm over the bolt cycle, 60 mm over the riser travel.
  - A4: Sight Z 57.60, parallel within 0.0005 deg, EyePoint X 176.1 over the riser.
  - A5: 5.9k tris, closed, 2 slots, UD1 0.

**Fail or near-miss (not decisive; details in `gates/form.json`):**
- **L1 blockout:** GR 0.976 and GL 0.953 pass. TOP is 0.841 raw and 0.908 with declared conventions, against 0.92. That is not under the 0.90 stop line. The causes are the sheet's own TOP biases (floor shadow on the right edge, round parts drawn wide, the knob drawn 32 mm back) and a 1-px sensitivity of 0.933.
- **L2:**
  - GR 0.957 (needs 0.96).
  - GL 0.942 (needs 0.958).
  - TOP 0.837 raw / 0.902 with the declared fit (needs 0.93).
  - These are measured with the blockout scope as a stand-in for the sheet's scope.
  - Main residuals: the barrel OD per spec (Q3) is about 1 px above the drawn barrel; GL draws the forend bottom higher than GR.
  - **Per-part L2 is only 2/19.** The per-part check isn't trustworthy yet: trigger and paddle read 0.0 and receiver/shroud 0.3-0.5, which points at the label/painter's-order method rather than the geometry. Fixing that method is a W2 task.
- **L3:** contour P95 4 px (needs 2).
- **L4:** 13/14. The grip bottom is 0.21 mm high from contour smoothing (declared).
- **B3 riser:** min 0.140 against the 0.15 sliding row. No intersections; the posts sit 0.01 under the row after the UD repair.
- **G5 butt gaps:** min 0.0072 (muzzle device to barrel) against 0.01. This is at the 0.5 mm sampling limit.
- **UD1/UD2:** 647 Unreal-drop triangles remain, in chassis (35), bolt_handle (361), magazine (241), butt_knobs (8) and bipod_leg_l (2). The UD repair is applied everywhere else. On these three parts it moved gate-critical surfaces (the inlet lip into the receiver, the knob, the well walls), so it is skipped there. **This must be fixed at the source before export** (avoid micro bevel/boolean strips in those generators).

## Renders to look at

- Gun grey + rough-real: `Renders/Guns/SR01/form_{grey,real}_{right,left,top,q34,deployed_hero,bolt_open_back}.png`.
- With the scope: `Renders/Guns/SR01/form_{grey,real}_scope_{right,q34,rings_close,rear_q,deployed_hero}.png`. Best overall: `form_real_scope_q34.png` and `form_real_scope_deployed_hero.png`.
- L8 close-ups: `WorkFiles/guns/sniper/review/l8/form_real_l8_*.png` (judge sheets `judge2_*.png`).
- Silhouette overlays: `WorkFiles/guns/sniper/review/{blockout,form}/{GR,GL,TOP}_overlay.png`.

## What is left (W1 follow-ups, then W2)

1. **UD1 at the source** for chassis, bolt_handle and magazine, then re-run UD1/UD2, G5, B3, L4 and magfit. Also: posts 0.01 under the sliding row, and the device/barrel gap above 0.01 (bore +0.02).
2. The per-part L2 method (trigger / paddle / receiver labels), then L2/L3 tuning: the riser top, the bipod hub and the GL differences. The TOP gates need the user's call on whether the declared TOP conventions are acceptable.
3. L8 backlog for W4b:
   - bipod: a visible leg knuckle/clevis with a clip and a spring housing (judge B's FAKE);
   - butt: pocketing or contour, and visible riser hardware;
   - bolt body: detail when open;
   - knob: tapered "tactical" shape (the sheet draws a ball, so it was kept).
4. **Flag for the user:** both rounds of judges asked for splayed bipod legs, which conflicts with Q2 (straight down, kept).
5. Scope: the ring split line and markings go to W2 normal or texture work. Generic markings are allowed (user rule 2026-10-13); no real maker or model names.
6. The plan's gunlib proposal list is updated (P2/P5/P6/P8 sniper-local implementations, plus new helpers). gunlib was not touched.

## Spend

About $29 of this run's budget (the plan estimated W1 at $35-55). Long Blender runs over 5 minutes cost extra because the prompt cache expires; the final full sweep set takes about 20 minutes.
