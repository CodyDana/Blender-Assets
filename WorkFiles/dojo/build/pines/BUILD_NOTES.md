# DojoPines build notes: fix round f1 (2026-09-30)

Four niwaki Japanese black pines from `References/Dojo/dojo_japanese_pine_ref.png`, two variants each, rebuilt to
answer the r0 judge (3.5/10: six blockers, 13 deltas). Lock `DojoPines` (claude), re-claimed from the stale r0
lock. No Unreal in this run. Nothing committed.

**Verdict.** The r0 blockers were structural, and the structure is fixed:
- trunks are cut 35-65 %;
- pads are open lattices of forked twigs with separate needle bursts, no solid cores;
- limbs zig-zag with knuckles;
- the bark is plated columns;
- the boulder is fused faceted masses with roots walked over it.

All 18 mesh QA runs and all 4 tuft-unit QA runs pass, with no waivers and no skips. Export went only through
`Scripts/pipeline`.

The match to the sheet is still short of "to the T":
- The sheet's crowns are fuller and chunkier than ours.
- The front silhouette IoU fell against r0 (see Gates).
- Bark contrast is 4.0 against the sheet's 5.8.
- D's rock is smoother and more monolithic than the sheet's craggy rock.

The next step should be a judge round on `renders/f1` before any more build work.

## What changed, by judge item

| # | Judge delta | f1 |
|---|---|---|
| 1 | Trunk girth -50-60 % (A/B/D), -35 % (C) | The spec trunk diameter at 15-50 % of height is set to 0.056-0.074 of the traced crown width. Scale factors: A1 0.59, A2 0.47, B1 0.35, B2 0.54, C1 0.65, C2 0.54, D1 0.63, D2 0.57. Limbs scale with the trunk. The trunk keeps its measured taper (`trunk_exact`), plus a root flare (G8 1.39-2.16), buttress lobes and nebari |
| 2 | Delete the pad-core discs; build pads from forked twigs carrying needle-tuft clusters | New `Scripts/vegetation/cloudpad.py`. A fan of 3-8 angular arms runs from the limb end through the lower third of the pad and forks 1-2 times. Bursts sit on a jittered hex grid in 1-3 layers, each on a kinked shoot no steeper than about 45 degrees. 1-2 sky holes per pad. **No cores or shells** |
| 3 | Angular zig-zag branches, 2-3 fork levels, no vertical support sticks, a real fork close-up | `skeleton.angularize`: the direction changes every 0.15/0.20/0.28/0.17 m (A/B/C/D), with knuckle swellings at the nodes. The traced ends stay fixed. The pad arms fork below the bursts. Bursts with no arm in reach are dropped, which ends the hanging "curtains". The fork close-up is now pine C1's trunk top, where two scaffold limbs leave together |
| 4 | Flat, separated pads, 2.5-4x wider than tall; row fill within 0.05 | Thickness is capped at 0.36-0.40 of the width. The pixel-traced top is clamped under a smooth dome and the hand-traced height. Front row fill is now within 0.05 on A1, B1, B2, C1 and C2 (it was +0.12 to +0.38) |
| 5 | Bark: tall raised plates 1:2-1:3, dark tops, near-black fissures, rust at edges, less pink and crackle | New generator (third construction; see "Deviations"): 18 meandering columns per metre, staggered slanted cross cracks, three flaky terraces and ridged centimetre crumble. Rust sits in pits and on risers. Texture luma P90/P10 is 9.1. The render median (71,61,54) matches the sheet's (85,72,63) closely, but **render contrast is 4.0 against 5.8** |
| 6 | Foliage colour: cooler blue-green, lighter, pale fascicle bases; thinner, straighter, radial needles | The sheet's needles **measure hue 66-72 (olive)**, not 120-150 (study P54). Render hue is now 70-76 on the model sheets: G11 passes on all 8 trees and 3 close-ups. Value rose from (48,52,28) to (56-73, 64-79, 36-46); the sheet is (83,88,50). Four needle variants: standard, dark, pale new-growth tips, glaucous. Pale yellow-green sheaths. Needles are straight radial bursts: 32-44 fascicles, 2.7 mm base (1.35 mm mean), 7.8-12.9 cm |
| 7 | Rock: 2-3 fused angular masses, darker grey with lichen, moss on top and in the crevices, grass tufts | The visual hull is split through the trunk's crack into 3 convex masses. Each is chipped with 26 planes (never on its fused faces) and hulled. Granite is `M_DJ_Granite` at Tint 0.40, plus our lichen/stain overlay. Moss covers the crown, creases and foot (45 % of faces). 19 grass clumps. The side outline was rescaled to the front's rock height, so the side reads taller than wide |
| 8 | 6-10 thick roots from a flared base, hugging the rock, forking into cracks | 8 main roots (0.8x / 0.55x the base radius): 5 over the front half, 3 at the back. Each walks the rock surface through a BVH, half sunk, sliding downhill, and forks 1-2 times (28 root branches). The trunk is seated on the rock surface; the r0 bulb floated above it |
| 9 | C1: a 20-30 degree bend, crown filled, pads moved down in the side view | The thinner trunk shows the traced bend. Pads are fuller. Side-view pad matching now penalises reuse (study P53): C1 side has 6 auto-pads (r0: 2) |
| 10 | C2: fewer, fuller pads; a broader 3/4 view | P3Q was retraced as 8 pads in 6 tiers (from 11) with a depth shear of 0.25. The **3/4 view still pairs badly with P3F** (IoU 0.24): C2 has no reaching limb, and the sheet's views disagree |
| 11 | B: remove the pendant; S-curve in the side view | The pendant came from pad 8's traced top; the dome and height cap removed it. A small upright burst cluster remains at that pad's end. The B side trunk now shows the traced S |
| 12 | Base: a mossy mound, or at least moss blending | Moss on the root flare (vertex colour G), nebari, and 8 grass clumps per tree in the foliage mesh (slot 1, `MI_DKN_Groundcover`). **No mound mesh**: ground is the user's scenery |
| 13 | Sunset re-check; translucency or sheen | No saucers: the pads read as open lattices against the sky (`context_sunset_close.png`). The foliage is still dark at back-lit sunset. The translucent mix was tried at 0.5, but that darkened front-lit pads, so it ships at 0.3. In Unreal, the Two-Sided Wrap strength should be tuned at the sunset camera |

## Gates (renders/f1, Cycles 160 spp, denoised)

| Gate | f1 | r0 |
|---|---|---|
| G16 qa_check | 18/18 meshes + 4/4 tuft units, 0 waivers, 0 skips. UCX on every trunk and rock; foliage has none by design (study 4.10) | 26/26 |
| G4 front IoU (A1 A2 B1 B2 C1 C2 D1 D2) | 0.61 0.65 0.56 0.42 0.50 0.55 0.64 0.59 | 0.72 0.73 0.70 0.66 0.59 0.69 0.67 0.67 |
| G5 front row fill (ours / sheet) | A1 0.53/0.55, A2 0.59/0.51, B1 0.52/0.49, B2 0.54/0.52, C1 0.46/0.43, C2 0.52/0.56 | ours 0.61-0.74 |
| G3 auto pads, side views (ours / sheet) | A1 6/5, A2 2/5, B1 4/6, B2 4/6, C1 6/4, C2 4/4, D1 7/7, D2 7/7 | 1-3 |
| G11 render hue (sheet 66.6) | 70.0-76 on all trees: pass | 68-70 |
| G11 render value (median sRGB) | about (56-73, 64-79, 36-46) against (83,88,50) | (48,52,28) |
| G13 bark luma P90/P10 | 3.99 against 5.8: **fail** | 3.31 |
| G7 fork exponent n in 1.8-3.0 | 91-97 % (D2 0.909), 0 child > parent | 98-99 % |
| G8 flare | 1.39-2.16 | 1.30-2.07 |
| G9 needles / min twig | 7.8-12.9 cm (C's longest is 0.9 cm over 12) / 3.0-4.5 mm (r0 2.55: now passes) | |
| Tris trunk / foliage | A 56-71k / 97-132k, B 110-124k / 195-209k, C 189-240k / 243-305k, D 60-72k / 77-86k, rock 15k. The twig lattice is about 80 % of the trunk-mesh tris (P56) | |
| PP2 | half-float parent-index round trip OK on all 8; 3-4 levels | |

**Why front IoU fell while row fill came right.** Our pads are now open and flat; the sheet's pads are fuller,
rounder masses whose outlines take in their gaps. IoU rewards solid blobs, which is the look the judge rejected. It is
reported here and not optimised. The next lever is fuller, chunkier pads with more bursts per pad and a rounder top.

## Deviations from the study (and why)

- **Pad construction** is an authored fan lattice (`cloudpad.py`), not space colonisation (study 4.4). Colonisation
  toward sites above the limb grew vertical support sticks (P47). The study's rule to change the method was applied.
- **Bark**: three constructions this round. Voronoi plates still read as a net. Level-set furrows came out sparse.
  Explicit plate columns converged (P50). A lit numpy preview checked each before rendering.
- **Needle width** is 2.7 mm at the base (about 1.35 mm mean) against the study's 1 mm, to hold burst density at
  garden distance. This is the P43 widening, recorded.
- **Needle albedo** is well above the study's conifer band (body sRGB about 106/126/62). The sheet is a bright AI
  render. G11's albedo band is still an unverified gate (study 3.9), so render hue was used as the gate.
- **Judge's colour description.** It conflicts with the pixels (P54). We followed the measurement: hue about 70,
  with glaucous highlights for the cool read.
- **Triangles** are over the study's 8.7 soft caps on B and C (Nanite). Measure in Unreal (G18) before cutting.
- **No mound mesh.** Moss blending and grass tufts only (judge item 12's fallback).
- **Rock UVs** are per-mass box charts, overlap-free because each mass is convex. They use whole-tile offsets on
  UV0 (the granite's 4 m tiles).
- **No pipeline change.** The UCX point-hull stays local (`build_pines.ucx_from_points`).

## Open issues

- **Fullness:** A/B/C crowns are sparser and pads thinner than the sheet's. C's pads are thin discs against the
  sheet's dense overlapping clouds.
- **B trunks** may now be over-thinned at the base: the sheet's P2F lower trunk looks about 1.5-2x ours. The judge
  asked for the cut; check it in the next judge round.
- **G13 bark** still fails (4.0 against 5.8). The close-up reads as plated columns but smooth ("clay"). A 2048 bark map
  or real plate geometry at the close-up would help.
- **Pad close-ups:** the rosettes do not read as distinct starbursts from above, and the shoots under the pad are
  thin sticks where the sheet's twigs are knobbly 1-2 cm branches.
- **D rock** is smooth-faceted and monolithic. The sheet's rock is craggy, and the tree sits on it with more, thicker
  roots.
- **PineC2's 3/4 view** cannot match P3F (the sheet's views disagree); IoU is 0.24.
- **Sunset:** the back-lit foliage is still dark. The context terrace is a stand-in; judge in Unreal (P32).
- **Unverified in Unreal** (carried over from r0): vertex-colour Replace, PP2 decode and Y flip, XVector scale,
  Voxelize with lerp UVs off, WPO/voxel takeover, performance, collision presets.
- The rock overlay (lichen and stain) needs a small material function in the kit master. It is not in the shared
  library.

## Files

- **Code:**
  - `Scripts/vegetation/`: `cloudpad.py` (new), `trunk_ratio.py` (new); `skeleton.py` (angularize, chaikin,
    knuckles, exact radii, a min twig radius), `tubes.py` (knuckles, buttress, twist, ring density),
    `foliage.py` (bursts, clumps), `rock.py` (faceted masses), `treegen.py`.
  - `Scripts/dojo/pines/`: `make_spec.py` (girth targets, side-pad matching, C2 shear, rock height), `pines_trace.py`
    (P3Q retrace), `make_pine_textures.py` (bark, needles, rock overlay), `build_pines.py` (rock, roots, seating,
    ground cover, materials), `render_pines.py` (per-view framing, fork, context), `compose_pines.py` (look numbers),
    `make_catalog.py`, `run_all.sh` (default round f1).
- **Outputs:**
  - Blend: `Assets/Dojo/DojoPines.blend`.
  - Exports: `Exports/DojoKit/Pines/`, with 61 hashed files in `export_report.json`.
  - Catalog: `pines_catalog.json`, with the Unreal import, material (rock MI, ground cover, needle translucency) and
    wind recipe.
  - Reports: `qa_report.json`, `build_report.json`, `renders/f1/measure.json`, `renders/f1/look_numbers.json`.
- **Renders (`renders/f1/`):**
  - model sheets: `model_sheet_v1.png`, `model_sheet_v2.png`;
  - side-by-sides: 24 `sbs_<V>_<view>.png` and 4 `sbs_closeup_*.png`;
  - silhouettes: 24 `sil_*`;
  - context: `context_sunset_terrace.png`, `context_sunset_close.png`;
  - the raw passes.
- **Study:** `TREE_BUILDING_STUDY.md` gained pitfalls P45-P56 and a revision entry.


# Pines v2: the rosette method (2026-09-30, relaunched run)

The owner-approved method (items 1-8), rebuilt after the stopped run at ~09:33. Lock `DojoPines` re-claimed (claude).
No Unreal in this run, no git commit or push. **Pine D's rock was not touched** (the owner asked for a stone/rock study
first): it is the f1 rock, and D's roots are still walked over whatever rock mesh is built (BVH), so a new rock refits
them by a rebuild. The roots were not polished against the old rock.

**Verdict.** At tree scale the v2 pads read as rounded masses of rosettes, the heights and girths come from the sheet,
and the colour now measures close to the sheet. Front-view silhouette IoU is 0.61-0.76 (f1: 0.42-0.65). This is still
short of the 0.80 target and of "to the T". The close-ups remain the weakest part:
- the bark is plated but smooth and too dark;
- the pad from above shows separate small stars where the sheet shows big, packed rosettes;
- the pad side hides its twigs;
- the limb fork is a smooth tube where the sheet's is gnarled.

The next step should be a blind judge round on `renders/v2`.

## What was reused from the stopped run

- **Kept:**
  - `rosette.py` (the unit builder);
  - the `rosettepad.py` chain, kink, shoot and stats code;
  - `make_spec.py` (sheet girths by pixel ruler, figure-scale heights, mound extents, stubs and trunk knuckles);
  - the texture, render and compose scripts;
  - `v2work/` rulers and crops.
- **Replaced:**
  - the footprint site sampler (now `dome_sites`) and the k-means lattice (now a spanning tree);
  - the rosette library parameters;
  - `bark_v2` (now `bark_v3`);
  - the mound surface and its dressing.
- **Archived, not reused:** the stopped run's partial `renders/v2` is in `v2work/renders_v2_stopped_run_0905/`, and a
  snapshot of the code as found is in `v2work/code_at_relaunch_0937/`.
- **Restoring f1:** use `Backups/DojoPines_f1_2026-09-30/RESTORE.md`.

## Method changes (quick-look rounds s0-s17 on A1, then all eight)

| Item | v2 |
|---|---|
| 1 Rosettes | 5 units: 54-80 fascicles (108-160 needles), 8.0-9.8 cm needles (7.0-11.0 with the 0.88-1.12 instance scale; C 7.5-11.5), 3.8 mm base width, upright cone 6-68 degrees, pale 2.2 cm candle, yellow sheaths. 15.5-18.4 cm across (P90 13.1-15.2). Full qa_check on every unit: 5/5 pass |
| 2 Pads | Sites are Poisson-sampled on the dome SURFACE (top and flanks) at a 3D spacing of 9-10 cm, inset by half a fan. Fans stay upright (at most ~30 degrees off vertical on a flank); a few under-rim fans sit at 30-45 degrees. The lattice is a Prim spanning tree over internal points in the lower 6-38 % of the pad, with 2-9 fork orders. Every fan hangs on a short shoot from its nearest node below it. The underside is lowered by 18 % of the local thickness. The apex pad may be 0.58x as thick as it is wide (rounded crown) |
| 3 Branches | Traced limbs, zig-zag every 15-28 cm. Each limb ends at the pad hub, and its floor radius tapers to 45 % there. Pipe exponent 2.6. C's reaching limb girth was read by hand (0.21 m base to 0.045 m) |
| 4 Trunk | Girth at 1/4 height from the sheet per panel (pixel ruler), strong taper. C: twist, two knuckles, a broken stub; its leader thins to 9 % at the apex. The nebari start on the mound top (reach capped at 0.45 m) |
| 5 Heights | From the 1.8 m figure: A 2.24/2.48, B 3.58/3.40, C 4.53/4.32, D 3.63/3.87 m. The catalog notes an instance scale up to ~1.3x (C ~1.05x for the needle cap) |
| 6 Bark | `bark_v3`: 14 plate columns per metre, cross cracks at full fissure width (5-12 mm half width), three stepped flaky terraces, a shingle tilt, faint flakes, rust only on the risers. Tops (90,76,63) albedo |
| 7 Colour | The needle albedo was regraded twice against the rendered measurement. First pass: (60,68,40) at hue 77. Final: (72-77, 78-83, 44-49) at hue 70.6-72.4, against the sheet's (80-85, 84-89, 46-50) at hue 66.6. Translucency stays 0.35 x SSS |
| 8 Base mound | `SM_DKN_BaseMound_A-D`: a conical moss hill with gaussian hummocks, the edge dipping under grade, a ragged soil band, a boulder, 3 stones and 10 pebbles, a rosette-ball shrub, and 80-320 moss-cushion clumps plus grass and fern sprays. One UCX. D's mound is an apron round the rock |

## Gates (renders/v2: Cycles 160 spp, denoised, 1100 px; the full table is in `renders/v2/gates_v2.json`)

| Gate | Result |
|---|---|
| G16 qa_check | 22/22 meshes and 5/5 rosette units pass, 0 hard fails, 0 waivers, 0 skips. 68 files exported through `Scripts/pipeline/export_fbx` |
| G4 IoU front (A1 A2 B1 B2 C1 C2 D1 D2) | 0.72 0.73 0.71 0.61 0.64 0.76 0.73 0.72. **Fails 0.80** |
| G4 IoU side | 0.57 0.65 0.52 0.50 0.66 0.45 0.65 0.62 |
| G4 IoU 3/4 | 0.47 0.40 0.36 0.41 0.35 0.29 0.58 0.58. Variant 1's 3/4 is paired with the sheet's 3/4 panel, which is variant 2's design |
| G5 front row fill (sheet / ours) | A1 0.55/0.64, A2 0.51/0.66, B1 0.49/0.62, B2 0.52/0.64, C1 0.43/0.67, C2 0.56/0.75, D1 0.37/0.67, D2 0.32/0.71. **Fails**: our crowns fill their rows more than the sheet's |
| G3 pads (hand-traced = built / auto, sheet : ours) | A1 6=6 5:5; A2 7=7 5:3; B1 9=9 6:5; B2 9=9 5:5; C1 11=11 6:4; C2 8=8 4:3; D1 6=6 7:4; D2 6=6 6:1 |
| Rosettes per pad | 18-233 (the dome surface at 9-10 cm spacing). **Deviation from 15-25** (P59) |
| Trunk girth at 1/4 height (sheet / ours, m) | A1 0.28/0.34, A2 0.26/0.29, B1 0.32/0.30, B2 0.33/0.32, C1 0.68/0.74, C2 0.53/0.56 |
| Trunk / crown (sheet / ours) | A1 0.119/0.144, A2 0.095/0.105, B1 0.115/0.107, B2 0.120/0.115, C1 0.127/0.146, C2 0.165/0.173 |
| Trunk / 1.8 m figure (sheet / ours) | A1 0.156/0.190, B1 0.178/0.166, C1 0.378/0.412 |
| G11 render hue (sheet 66.6) | 70.6-72.4 on all 8 trees, 72.7-74.5 on the close-ups: **pass** |
| G11 render median | (72-77, 78-83, 44-49) against (80-85, 84-89, 46-50): about 8 % dark |
| G13 bark luma P90/P10 | 4.77 against 5.8. Passes the ±20 % band only just. Render median (50,43,37) against (85,72,63): **too dark** |
| G7 fork n in 1.8-3.0 | A1 0.89, A2 0.83, B1 0.85, B2 0.85, C1 0.90, C2 0.94, D1 0.61, D2 0.76. 0 children thicker than their parent. **Below 0.90 on 6 trees**: D's rock roots and the dense pad lattices |
| G8 flare | 1.82-3.48 |
| G9 | Needles 7.0-11.5 cm; min twig 3.0-3.6 mm: **pass** |
| PP2 | Half-float parent index round trip OK on all 8 |

**Triangles (Nanite).**

| Tree | Trunk | Foliage | Mound | Rock |
|---|---|---|---|---|
| A1 / A2 | 37k / 42k | 78k / 96k | 22k (A) | |
| B1 / B2 | 65k / 61k | 131k / 128k | 23k (B) | |
| C1 / C2 | **95k** / 74k | **197k** / **165k** | 35k (C) | |
| D1 / D2 | 70k / **95k** | 62k / 74k | 11k (D) | 13k / 16k |

Over the study 8.7 caps (trunk 80k, foliage 150k; 250k if density needs it):
- C1 trunk (the lattice is 44k of it) and D2 trunk (the roots are 57k of it);
- C1 and C2 foliage, both still under 250k.

Measure in Unreal before cutting (G15, G18).

## Deviations (recorded)

- **Rosettes per pad: 18-233, not 15-25.** At 15-25 fans the sheet's 0.8-1.8 m pads came out as sparse sprigs (s1-s2).
  The count follows the pad surface at the fans' spacing (P59).
- **Needle base width 3.8 mm** (1.9 mm mean). This is the P43 widening; at tree distance thinner needles vanish.
- **Base mound size follows the SHEET, not the owner's 1.2-1.5x crown width.** The sheet's mounds measure 0.65-0.9x
  the crown (A 1.8 m under a 2.35 m crown). The mound is a separate optional mesh, so the owner can ask for a bigger
  one. **Open decision for the owner.**
- **Pad "2.5-4x wider than tall".** The builder's proxy (dome thickness at the sites) gives 2.3-8.3x. Visually, with
  the fans, the pads read about 2.5-4x on A/B and flatter on C.
- **The bark close-up light** was raised (world 0.35 to 0.60). The matched close-up was too dark to compare.

## Judge steer

No blind judge ran in this round. No judge delta was acted on, so none was rejected. The owner's reading (items 1-8)
was followed throughout.

## Open issues

- **Close-ups:**
  - the bark is smooth plated slabs, too dark (render median 50 against 85);
  - the pad from above shows separate small stars on visible twigs, where the sheet shows big packed rosettes with
    pale centres;
  - the pad side hides its lattice (the sheet shows knobbly twigs under the fans);
  - the limb fork is a smooth tube.
- **The sheet's trunks are gnarlier** (bulges, a hole at C's fork). Ours are smooth tapered tubes with plates.
- **Side views merge the tiers** (row fill 0.72-0.85 against 0.49-0.70). The AI sheet's side panels are not
  consistent with its fronts (P53); our 6-11 front pads project into 1-4 masses.
- **G5 row fill is 0.08-0.39 over the sheet on every tree.** The crowns are denser between pads than the sheet's.
- **G7 is below 0.90 on 6 trees** (D1 0.61).
- **Unverified in Unreal** (carried over): vertex-colour Replace, PP2 decode, Voxelize with Lerp UVs off, performance,
  collision presets.

## Files

- **Code:**
  - `Scripts/vegetation/`: `rosette.py` (library v2 s13), `rosettepad.py` (`dome_sites`, spanning-tree lattice),
    `treegen.py` (limb taper at the hub, per-pad thickness).
  - `Scripts/dojo/pines/`:
    - `make_spec.py` (spacing, caps, `LIMB_R`, nebari on the mound, C leader tip);
    - `pines_trace.py` (P1F apex pad);
    - `make_pine_textures.py` (`bark_v3`, needle and moss colours);
    - `build_pines.py` (mound v2, UV1 fit on both axes, rosette scale per pine);
    - `render_pines.py` (camera roll for the bark, a limb fork, pad 2 for the pad side);
    - `make_catalog.py` (v2 heights, scale note, budgets, mounds, D rock status);
    - `run_all.sh` (default round v2).
  - Scratch tools: `v2work/{look.sh, lab.sh, pad_lab.py, xor.py, big.py, cu.py}`.
- **Outputs:**
  - `Assets/Dojo/DojoPines.blend`;
  - `Exports/DojoKit/Pines/` (68 hashed files in `export_report.json`; README updated for v2);
  - `pines_catalog.json`;
  - `qa_report.json`, `build_report.json`;
  - `renders/v2/{measure.json, look_numbers.json, gates_v2.json}`.
- **Renders (`renders/v2/`, same names as f1):**
  - model sheets `model_sheet_v1.png` and `model_sheet_v2.png`;
  - 24 `sbs_<V>_<view>.png`, 4 `sbs_closeup_*.png`, 24 `sil_*.png`;
  - `context_sunset_terrace.png` and `context_sunset_close.png`;
  - the raw passes.
- **Study:** pitfalls P57-P63 were added to `TREE_BUILDING_STUDY.md`, with a revision entry.


# Rock stage: the D cliff-pine rock with the stone study's method (2026-09-30)

Scope: pine D only (D1, D2). `STONE_BUILDING_STUDY.md` read first (sections 3.9-3.12, 4.9, 4.13-4.15, 6.2, 7, 8.3). Lock
`DojoPines` re-claimed (claude). No Unreal, no git, no downloads. **Backup of v2 first:**
`Backups/DojoPines_v2_2026-09-30/` (blend, exports, both code folders, reports, `renders/v2`; `RESTORE.md` inside).

**Verdict.** The rock changed class. Before: a blobby block with big moss blotches and 1-2 rope roots. Now: 2-3 fused,
rounded-but-fractured granite corestone lobes with V clefts, two cracks, orange lichen specks, moss in the crevices
and on top, and 10 roots that follow the clefts to the ground. It is still clearly short of the sheet in four places,
listed under open issues: flake relief, moss abundance, root count and fineness, and D2's composition.

## Method (study 4.9.2, as built)

`Scripts/vegetation/rock_sdf.py` (new, reusable) + `Scripts/dojo/pines/rock_v3.py` (the D plans, masks, mid, UVs, bakes):
1. **Lobes.** Each lobe is an ellipsoid (semi-axes a, b along two vertical joint families at the plan's yaw, top - zc
   up) cut by tangent planes:
   - the joint faces (4 verticals with a 4-16 deg batter plus the sheeting top) at 0.78-0.85 / 0.84-0.90 of the
     support, which gives broad near-flat faces;
   - 9-11 fracture facets at 0.87-0.94.

   Sizes are in metres from the sheet's D panels at 0.65 x (owner). D1 has 3 lobes (front-left, right, crown). D2 has
   2 (front-left, tall back-right); lab l4 showed a third low lobe as a separate "tooth", so it was dropped.
2. **SDF.** Geometry Nodes, voxel 5 mm, band 26-30:
   - a per-lobe opening, r = 0.12 / 0.075 / 0.11 m (D1) and 0.10 / 0.07 m (D2): 10-19 % of the lobe short axis,
     varied per lobe (S1);
   - union, then a 1.2 cm closing at the joins;
   - 3 fresh-fracture cutters and 2 crack wedges ("face", "back": 2.2-2.6 cm mouth tapering shut at the ends, 10-12 cm
     deep, 4 cm steps with a ragged wander), both by SDF difference;
   - a 1.2 cm lip opening, then Grid to Mesh at threshold 0.

   The lobe joins stay as deep V clefts (they are the root and moss crevices). Probe finding (5.2):
   `GeometryNodeSDFGridBoolean` UNION / INTERSECT expose only the multi-input (identifier "Grid 2"); DIFFERENCE keeps
   "Grid 1" too.
3. **Dense source** (0.51 / 0.62 M tris):
   - meso noise of 3 octaves (4 / 2.5 / 1.2 mm), masked down on the arrises;
   - 13 cm Voronoi flake facets cut 3-16 mm along the normal, stronger on the arrises;
   - masks: moss (top zone x up-normal x breakup, plus crevices = cracks, clefts and lobe joins, never overhangs),
     lichen (0.8-3 cm specks in 2-6 /m clusters on exposed faces), dirt (the foot).
4. **Shipped mid.** A 1.15 cm voxel remesh of the dense source (93.5k / 115.7k tris). Collapse decimation left slivers
   and folds that every unwrap flipped. A moss-cushion shell (8-40 mm lumpy lift, rim sunk 2 mm) is added on the mossy
   top (15.0k / 18.4k tris).
5. **UV0.** Charts from the SMOOTHED normal in 6 box directions, small pieces merged. Then an angle-based unwrap with
   seams at the chart borders, average island scale and a concave pack: **80 / 58 charts, 0 overlaps**, texel 5.4 px/cm
   at 2K (qa 5.5 % off 5.12). What failed first:
   - smart project: 170-408 overlapping pairs;
   - its ABF repair: 12.5k islands.

   UV1 is the full-tile packing.
6. **Bakes, dense -> mid** (Cycles, CPU, 6-7 s): normal (to DirectX by `textures.flip_normal_green`), mask (EMIT of
   the colour attribute), and AO on the mid alone. Outputs: `T_DKN_<V>_Rock_N / _ORM / _M.png`.
7. **Material.** `MI_DKN_<V>_Rock` is the library `M_DJ_Granite` (tint (0.60, 0.58, 0.55)) tiled at S/4 on UV0. On
   top:
   - the unique normal (the library's facet normal is not used, rule 10);
   - contrast x1.45 about the granite's linear median, saturation x0.85;
   - grime from `Wear`.R (clefts, cracks, a 10-30 cm weathering mottle) and light patches in `Wear`.G;
   - lichen: ochre / yellow-grey / pale, by M.G;
   - soil by M.B, moss (the moss set) by M.R.

   Slot 1 is `MI_DKN_<V>_RockMoss`.
8. **Collision.** One UCX hull per lobe (D1 3, D2 2). **No traversal marker:** the top is the tree's root plate, with
   no flat landing >= 0.49 m free of the trunk (study 4.13, rule 2).

**Tree (make_spec `d_rock_v3`).**
- The traced rock outlines are scaled x0.65 and stay the 2D authority (the sheet originals are kept as
  `rock.sheet_*`).
- The tree is moved onto the rock top (`tree_shift_m`: D1 (0.00, -0.08, -0.47), D2 (-0.32, -0.25, -0.70)). The build
  re-seats the trunk on the real surface (D1 +1 mm, D2 -3.5 cm).
- The trunk sinks 12 cm into the rock, not 0.35 m (at 0.35 m the trunk poked out of the smaller rock's back, t3).
- The pine-4 tube flare is 0.12 (was 0.30): the roots make the root plate, not a bulb.
- **D1:** leans left over the rock (-0.45 m over the lower 1 m) with a heavier lower S-bend (+-0.10 m, lower trunk
  radius x1.08). Build 1's -0.22 m left the trunk still rising to the right.
- **D2:** base at (-0.25, -0.05), on the front-left lobe beside the tall block.
- **Heights:** D1 3.15 m, D2 3.18 m (sheet 3.63 / 3.87 m). The catalog notes ~1.15-1.2x instance scale.

**Roots** (`grow_rock_roots_v3`):
- 10 primaries per tree, r0 = 0.20-0.26 x the base radius (t1's 0.30-0.40 read as 12-16 cm ropes).
- Each root runs 12-30 cm over the top first, then follows the fall line snapped to the bare rock every 2.5 cm, with
  its centre 0.25 r above the rock (sunk into rock and cushions).
- Roots are pulled into the lobe clefts and cracks and follow them down, keep clear of the roots already laid, and
  dive under the moss apron at the foot.
- Forks: 6 (D1) and 3 (D2), with pipe-rule thinning.
- Azimuths follow the panels: the left flank and the front cleft.

**Base mound D.** Moss to the rim (soil only at the ragged edge), 220 moss clumps and 28 tufts, 7 small same-rock
stones (3.5-10 cm). t2's 6-20 cm stones read as a ring of boulders.

## Rounds (all in `v2work/rock/`, lab = clay renders of the dense SDF rock)

| Round | Change | Result |
|---|---|---|
| l1 | box joint planes + chips, r 3.5-6.5 cm | stacked crates, knife-slit cracks |
| l2-l3 | batter, top chamfers, r 7.5-13 cm | pyramids / huts |
| l4-l6 | planes tangent to an ellipsoid (planes only) | fractured prisms; D2's third lobe a "tooth" |
| l7 | ellipsoid clipped lightly by the planes | potatoes (plane fraction 0.33-0.47, P12) |
| **l8** | deeper joint cuts, 9-11 facets | **rounded-but-fractured corestones** (kept) |
| t1-t4 | full D builds | polka-dot lichen (fixed: clustered specks), rope roots, trunk sink poking out, D mound boulders |
| t5-t8 | colour | black rock (Bright/Contrast pivots on 0.5; fixed with a median pivot), brown terrazzo (sat 0.25; fixed) |
| t9 | UVs | collapse-decimation folds; voxel-remesh mid + smoothed-normal charts: 0 overlaps |
| build 1-2 | QA | UV overlaps, then a texel of 0.6-1.3 px/cm (FRACTION margins on 12.5k islands): both fixed before export |
| t10 | trees | D1 lean -0.22 -> -0.45 m (it still rose to the right); D2 base moved onto the front-left lobe |

## Gates (`renders/v2/rock_gates.json`)

| Gate | D1 | D2 | Target |
|---|---|---|---|
| SG15 IoU, front / side, vs the traced outline x0.65 | 0.862 / 0.841 | 0.836 / 0.835 | >= 0.80: **pass** |
| SG14 plane fraction (within 15 deg and 2 cm of a lobe plane) | 0.515 | 0.586 | >= 0.60: **fail** (D1), borderline (D2) |
| SG14 arris radius / lobe short axis | 0.17 / 0.12 / 0.19 | 0.14 / 0.10 | >= 0.10: pass. Above the 4-8 % tree-rock row: the owner asked for "rounded-but-fractured" |
| SG14 edges sharper than 150 deg | 1.7 % | 1.3 % | fresh fractures and flakes only |
| SG14 cracks | face, back, plus the lobe clefts | same | 1-3 straight cracks: pass |
| SG11 hue / sat / R/B | 33.5 / 0.12 / 1.15 | 32.6 / 0.13 / 1.17 | sheet 33.5-36.6 / 0.16-0.18 / 1.21-1.25. Hue passes; sat and R/B sit at the edge of +-0.05 / +-0.1 |
| SG10 luma p5-p95 (method A) | 0.27-0.54 | 0.22-0.54 | sheet 0.14-0.19 to 0.64-0.69: **fail** (no highlights) |
| SG10 p90/p50 (method C) | 1.46 | 1.69 | sheet 3.3: **fail** |
| SG10 local std | 0.080 | 0.075 | sheet 0.105-0.115: **fail** (-30 %) |
| Dark fraction (method C) | 0.09 | 0.15 | sheet 0.15-0.18 |
| SG12 moss | 17-18 % of the rock (mask > 0.5): top and crevices only, positive correlation with up-normal and cavity by construction | same | |
| SG16 seating | rock sunk 12 cm (10 % of its height, under the study's 15-35 %); the D apron covers the foot | same | |
| SG17 qa_check | 22 / 22 pass (D rocks: texel 5.4 px/cm, 0 UV0 / UV1 overlaps, UCX 3 / 2) | | |
| SG17 verts / tris | 0.51 | 0.51 | <= 1.0 |
| Rock tris | 108.5k | 134.1k | 50-150k: pass |
| Trunk tris | 39.1k | 44.5k | v2: 70k / 95k (the rock roots were 57k of D2's) |
| G7 forks in band | 0.78 | 0.91 | v2: 0.61 / 0.76 |

The sheet IoU of the whole D trees fell (front 0.49 / 0.53, v2 0.73 / 0.72) **by design**: the sheet draws the rock
at 1.6-1.9 m and the owner asked for 0.65 x.

A-C are byte-for-byte the same geometry: tri counts match the v2 report on all six, and the textures regenerate
bit-identically. Their FBX files were re-exported by the full build (new hashes in `export_report.json`, same
content).

## Deviations (recorded)

- **Owner over sheet:**
  - rock size 0.65 x;
  - D heights 3.15 / 3.18 m;
  - D1's left lean. The sheet's P4F trunk rises to the right before the crown swings left. **Owner's reading
    followed.**
- **Arris radius 10-19 %**, above the study's 4-8 % tree-rock row. At 4-8 % (l1) the lobes read as crates.
- **Rock sunk 12 cm**, not a third. The trunk base and roots set the rock top; the mound apron hides the foot.
- **The mid is a voxel remesh, not a decimation.** That is the study's fallback path, used because of the unwrap. The
  1.15 cm voxel softens sub-cm relief, which lives in the baked normal.

## Judge steer

No blind judge ran in this stage. No judge delta was acted on, so none was rejected. The owner's reading was followed.

## Open issues

- **Flake relief.** The sheet's faces are craggy, with many crisp 5-20 cm flakes and ledges. Ours read as smooth
  rounded blocks at tree distance, and the 13 cm facets are shallow after the 1.15 cm remesh. SG10 fails for the same
  reason: no bright lit crowns and no dark ledges (p90/p50 1.5-1.7 against 3.3).
  - Next: deeper, larger flakes in the SDF stage (as cutters), not on the mesh.
- **Moss is too thin.**
  - The sheet has thick yellow-green cushions over the whole top and down the clefts, and ferns at the foot.
  - Ours: moss on 17 % of the rock, mostly hidden under the trunk base; the D apron is flat moss with grass.
- **Roots.** The sheet shows a tangle of many thin roots (15-25 visible) draping the left flank. Ours are 10 thicker
  primaries, some running as parallel strands.
- **D2 composition.** The trunk base and roots engulf the front-left lobe, and the tall block stands beside it like a
  second stone. The sheet's P4Q reads as one broad rock with the tree on top.
- **D1 plane fraction 0.515** (< 0.60).
- **Colour.** Saturation and R/B sit at the low edge. The value spread needs the relief fix above, not more albedo
  contrast: t6 went to terrazzo that way.
- **The D mound is one per family** (built with D1), so D2's wider rock intersects it.
- **Carried over:**
  - no fresh-process FBX re-import in this stage;
  - Unreal unverified (materials not built in Unreal; `M_ST_RockUnique` does not exist yet);
  - the 12 cm burial.

## Files

- **Code:**
  - `Scripts/vegetation/rock_sdf.py` (new);
  - `Scripts/dojo/pines/rock_v3.py` (new);
  - `build_pines.py`: v3 rock, materials, roots v3, the pine-4 flare, the D mound; the dead f1/v2 rock builders
    removed;
  - `make_spec.py`: `d_rock_v3`, the D1 bend, D sink;
  - `make_catalog.py`.
- **Lab and tools:** `v2work/rock/`:
  - `rock_lab.py` (clay + SG14/15), `rock_look.py` (close-ups), `rock_measure.py` (SG10/11 via
    `Scripts/stone/stone_measure.py`, imported read-only);
  - rounds l1-l8, t1-t10, `final_lab/`, `final_rock_measure.json`.
- **Outputs:**
  - `Assets/Dojo/DojoPines.blend`;
  - `Exports/DojoKit/Pines/`: 74 files in `export_report.json`, README updated;
  - `pines_catalog.json`.
- **Renders (`renders/v2/`):**
  - D1 / D2: `<V>_{front,side,3q}_{final,sil}.png`, `sbs_<V>_*.png`, `sil_<V>_*.png`;
  - `model_sheet_v1.png`, `model_sheet_v2.png`;
  - `context_sunset_terrace.png`, `context_sunset_close.png` (D1 is in the scene);
  - new: `<V>_rock_{front,q3,high,back}.png`, `sbs_rock_closeup.png`, `rock_gates.json`;
  - `measure.json`, `look_numbers.json`, `gates_v2.json` recomposed.

  The A-C renders are unchanged.


# Pines v2f: judge-delta fix round (2026-09-30)

Scope: all eight pines, from the v2 + rock-stage state. Lock `DojoPines` re-claimed (claude). No Unreal, no git, no
downloads, headless Blender only. **Backup first:** `Backups/DojoPines_v2r_2026-09-30/` (blend, exports, both code
folders, reports, `tex/`, `renders/v2`, `RESTORE.md`). Lab rounds in `v2fwork/` (l0-l16 tree labs, `rock/r1-r2` clay,
`padtop_lab.py`, `mound_lab.py`, `barkprev.py`, `finish_v2f.py`). The stonekit chat's Blender job ran alongside and
was left alone.

## Judge deltas, checked against the sheet first (JUDGE-STEER RULE)

| Delta | Sheet check | Action |
|---|---|---|
| 1 D rock: one broad boulder, not pillars; moss cap; fern skirt | P4F / P4Q / P4S crops: confirmed (one rounded-angular mass, fused lobes, moss on the top shoulder, ferns and shrubs at the foot) | Rock plans reshaped: lobes overlap, 5.5 cm SDF closing, shallower sheeting cut (domed tops), more batter; D1 lowered and widened. Visible width / height 1.24 (D1) / 1.28 (D2); v2 was about 1.1, with a separate slab on D2. Moss mask on the top shoulder only; fern and shrub skirt on BaseMound_D. **Size part rejected** (below) |
| 2 D trunk and roots: trunk ~1/5 of the rock width, 8-12 thin roots | P4F: trunk ~50 px of a ~300 px rock (1/6), many thin roots: confirmed | Trunk at the rock set from that ratio: r 0.13 / 0.15 m = 0.19 / 0.20 of the rock width (v2: ~0.4 with the swell); tube flare 0.12, buttress 0.10; 13 primary roots (r 0.20-0.38 x base) + 19 / 13 forks, draped on the left flank, a third lifted off the stone, weaker crack pull |
| 2b D2 side: 5 tiers of small pads | P4S shows 5-7 tiers | **Not done** (open issue) |
| 3 needles blue-green, darker, yellow tips | Measured: sheet tree panels (78-85, 83-91, 48-52) hue 66-71, luma ~73; v2 renders (66-70, 74-78, 43-45) hue 74-76, luma 61-64 | **Hue and 'darken' rejected**: v2 was already greener and darker than the sheet. Yellow part confirmed and applied: yellow sheath band 0.08-0.15 of each needle, 2 of 8 cell columns yellow-tipped. Albedo ~12 % brighter and a touch warmer, roughness 0.42. v2f renders (73-76, 79-82, 44-46) hue 68-70 |
| 4 pads: rosettes up and out, open underside, no fringe; compact oval from above | Pad-side and pad-top close-ups: confirmed | 6 units: 4 round stars for the pad tops, 2 upright brushes (fascicles along 4-6 cm, 6-50 deg) on a quarter of the rim sites; fan bases floored at 22 % of the local thickness above the underside; under-rim fans removed; lattice lowered (0.02-0.24); twig-end clumps plus a fill; sampling weighted toward the dome top; the needle kink no longer always bends down. Pad-top close-up: A1 pad 4 rendered alone (temporary cut copies of the meshes; the asset is unchanged) |
| 5 ramification; limbs through each other | Fork close-up: angular, knobby secondaries confirmed | Zig-zag nodes now move 35-65 deg up or down from the side (they moved in depth only, invisible from the front); two-pass limb separation with the final pipe radii. A numeric check finds no limb-limb overlap outside shared junction nodes. The v2 fork picture was a sub-limb running beside C1's reaching limb; the fork close-up now frames A1's trunk fork (a 12-15 cm stem, like the sheet's) |
| 6 bark: chunky irregular flaky plates, orange fissures | Close-up confirmed. Sheet: median (84,71,63), luma p10/50/90 24/73/144, rust 0.11, dark 0.14, pale 0.11. v2 close-up: (50,43,37), 18/44/87, 0.036, 0.28, 0.003 | **Method change**: `bark_v4` = warped anisotropic Voronoi plate columns (17 x 5 per metre, vertical fissures wider than the cross breaks) + terraced-noise flaky layers + cork crumbs, coloured by layer (pale tops, orange under-bark, warm fissure walls), normal strength 0.20. Tried and dropped: flat Voronoi flakes (stained glass), healing 40 % of the edges (camouflage). Close-up light raised (world 1.05, key 6.5): v2f close-up (70,59,52), 33/61/105, rust 0.064, dark 0.069, pale 0.013 |
| 7 mounds: low, rocks, ferns, moss clumps | P1F-P3F confirmed: lumpy moss, rocks, ferns, a gravel rim; the sheet's mound still rises ~0.2 m at the trunk | Moss bed 0.72 h + a trunk rise; 150 small cushions (2.5-6 cm) with a cushion vertex colour (R: gaps x0.30 .. tops x1.35, `MI_DKN_MoundMoss`); 1-3 cm moss tufts on the cushion tops; a bigger boulder, 5 stones, 22 pebbles; real fern sprays (`foliage.make_fern`); no lawn grass; lighter ochre soil rim (sheet rim median (99-111, 86-92, 45-62)). **'Thin disc' partly rejected**: lab l7's thin bed let the nebari exit under the rim and read as a plate |
| 8 trunk flare, knobs; C1 thick limb + stub | P1F / P2F / P3F confirmed | Knobs on the A, B and D trunks (TRUNK_KNUCKLES); C knuckles 3 / 2. C1's reaching limb already starts at the sheet's 0.21 m radius and carries the stub: unchanged |

**Rejected deltas** (also in the stage output):
- "shift the needles toward blue-green and darken": the sheet measures yellow-green hue 66-71, and the v2 render was
  already darker (luma 61-64 against ~73) and greener (hue 74-76);
- "one boulder filling the bottom ~40-45 % of the asset": the owner set the rock at 0.65 x the v2 size (rock stage);
  the shape and the trunk ratio were fixed, the size was not;
- "flatten the mounds into thin discs": the sheet's mounds rise ~0.2 m at the trunk, and a thin disc failed in lab l7.

## Numbers (`renders/v2f/gates_v2f.json`, `rock_gates.json`, `measure.json`, `look_numbers.json`)

- **QA:** 22 / 22 qa_check passes, 6 / 6 rosette units pass. 74 files exported through `Scripts/pipeline/export_fbx`
  (`export_report.json`). The textures regenerate byte-identically to the exported hashes.
- **Silhouette IoU against the sheet, mean of 24 views: v2 0.532 -> v2f 0.520.** Most views lost 0.01-0.04:
  clumped pads with open gaps fill less of the traced outline. D2 front and side rose (0.526 -> 0.556,
  0.468 -> 0.521); D1 front fell (0.487 -> 0.419) with the stronger left lean. G4 (0.80) still fails everywhere.
- **Tris:**
  - foliage: A1 110k, A2 136k, B1 189k, B2 181k, C1 239k, C2 183k, D1 88k, D2 106k. B1, B2, C1 and C2 are over the
    150k soft cap and under the 250k "if density needs it" cap;
  - trunk: C1 102k (over 80k); the others 42-76k;
  - rocks 110k / 134k; mounds A-D 44k / 44k / 64k / 49k.

  Nanite: measure in Unreal before cutting.
- **Needles:** 7.04-11.07 cm (C 7.48-11.76 cm) including the instance scales. G7 fork share in band 0.85-0.96 (D1 0.68).
- **Rock:**
  - lab IoU against the traced outline x0.65: D1 0.859 / 0.822, D2 0.842 / 0.736;
  - plane fraction 0.504 / 0.549; moss share 0.20;
  - roots 13 + 19 forks (D1) and 13 + 13 (D2);
  - trunk diameter / rock width 0.193 / 0.203.
- **Heights:** A 2.24 / 2.48, B 3.58 / 3.40, C 4.53 / 4.32, D 3.08 / 3.21 m (D includes the rock).

## Reused
The rosette, rosettepad, treegen, rock_sdf and rock_v3 code, the render / compose / catalog / quick-look tools and the
rock-stage lab (`rock_lab.py`, `rock_look.py`) were reused and edited. Nothing from `renders/v2` was reused as output.

## Open issues
- **Pads.** At tree distance they still read more "brushed" than the sheet's granular star masses. The pad-side
  close-up still shows a comb of rim brushes. The pad-top close-up is sparser than the sheet's, with a thin patch
  toward its middle.
- **Bark.**
  - The plate network still reads as a crack net at close range.
  - Highlights (pale 0.013 against 0.11) and rust (0.064 against 0.11) are short of the sheet.
  - The bark tile is metric, so thin trunks (the fork close-up) show plates that are too large.
- **Rock.** The granite grain reads as speckle. The facets lack the sheet's light / dark flake relief (SG10 still
  short). The moss cap is thin. The fern skirt is a flat mat rather than bushy clumps.
- **D side views.** They merge the pads into 2 masses where the sheet shows 5-7 tiers. The D2 side delta is not done.
- **IoU** fell slightly (0.532 -> 0.520); no view reaches 0.80.
- **Budgets** are over (above).
- **Unverified:** nothing checked in Unreal; no fresh-process FBX re-import in this stage.

## Files
- **Code:**
  - `Scripts/vegetation/`: `rosette.py`, `rosettepad.py`, `treegen.py`, `skeleton.py`, `foliage.py` (`make_fern`);
  - `Scripts/dojo/pines/`: `make_spec.py`, `make_pine_textures.py` (`bark_v4`), `build_pines.py`, `rock_v3.py`,
    `render_pines.py`, `make_catalog.py`.
- **Outputs:** `Assets/Dojo/DojoPines.blend`, `Exports/DojoKit/Pines/` (README updated), `pines_catalog.json`,
  `qa_report.json`, `build_report.json`, `export_report.json`.
- **Renders (`renders/v2f/`, same names as f1):**
  - the model sheets;
  - 24 `sbs_<V>_<view>.png`, 4 `sbs_closeup_*.png`, 24 `sil_*.png`;
  - the context shots;
  - `<V>_rock_{front,q3,high,back}.png` and `sbs_rock_closeup.png`;
  - the gates JSONs.
- **Study:** `TREE_BUILDING_STUDY.md` pitfalls P64-P71 and a revision entry.
