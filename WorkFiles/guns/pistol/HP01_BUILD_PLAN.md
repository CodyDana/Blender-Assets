# Heavy Pistol HP-01 (`HP01`): build plan (W0)

**Date:** 2026-10-14. **Status: W0 plan.** Nothing has been built.

The numbers live in `hp01_spec.json`, written by `tools/make_spec.py`; **where this plan and the spec differ, the spec
wins.** Decisions R1-R18 and questions Q1-Q14 are in `HP01_STUDY.md`. The game interface is `hp01_interface.json`.

**The pistol is the pistol-class pilot:**
- `SK_HP01_Skeleton` carries `ABP_Gun_Pistol` (study 5.2);
- its H1 sets the class grip pose;
- its clip set is the class set.

---

## 0. The plan on one screen

| Item | Value |
|---|---|
| Asset set | `SK_HP01` (+ LOD1-3, clips), `SM_HP01` (static twin, UCX x4), `SM_HP01_Mag`, `PHYS_HP01`, textures, sidecars in `Exports/Guns/HP01/` |
| Frame | B: +X muzzle, +Z up, -Y right; origin `Grip` = F (-215.9, -78.5), grip axis 17.4 deg |
| Bones (8) | `body`, `slide`, `selector` (on slide), `hammer`, `trigger`, `slide_stop`, `mag_release`, `magazine` |
| Motion | slide -X 48 (lock 46, press check 14); hammer +58 (falls from cocked); trigger -9; safety -40; slide stop +10; release 3 mm |
| Clips | `A_HP01_Fire`, `_FireLast`, `_Reload`, `_ReloadEmpty`, `_Safety`, `_SlideRack`, `_Inspect` (press check) |
| Budgets | LOD0 22,800 allocated (target 15-25k, ceiling 30k); mag 1.8k (ceiling 2.5k); LOD1 ~45 %, LOD2 ~15 %, LOD3 0.8-1.2k |
| Slots / sets | `M_HP01_Steel` (Steel 4096), `M_HP01_Furniture` (1024), `M_HP01_Mag` (1024), `T_HP01_Masks` 2048 |
| Method | traced and **faired** outlines; section / outline generators with **authored bevel lands**; HP bakes for pebble, checkering and machining marks; finish cards; ER0 at W1c |
| Before W1 | the user rules on **Q1 (width)**. Without an answer, the build uses the default (the TOP view as drawn) with `K_Y` as a single parameter |

---

## 1. Lessons from the earlier guns, applied here

| Lesson (source) | Applied |
|---|---|
| Bevel clamp collapsed widths across the whole mesh; exclusion boxes made a patchwork (sniper W4b) | Bevels are lands inside each part's generator (section rings or the outline offset), with widths per edge set. No mesh-wide Bevel modifier on curved / multi-edge parts. Gate CU2 measures every land |
| Jagged traced edges, a zig-zag nose, wavy edges (sniper W4b judges) | Outlines are faired before geometry (CU1). The fairing is a gunlib module proposal (§9); here it lives in `Scripts/guns/pistol/hp_fair.py` until the gun chat promotes it |
| Flat cut-out trigger, slab levers, identical flush pins, smooth buttons (carbine ER1, 24 of 24 calls) | real-pattern small parts (CRAFT §2, CU6); ER0 checks them at W1c, before any paint |
| Paint knobs did not converge; noise amplitudes read as clouds; sheet-lit colours pinned the finishes (CLOSEUP 1.1-1.3) | Finish cards on a swatch board first (CU5), located features from bakes (CU8), L5 / G20 reported (subject to the user's D1 for the line) |
| Shape tells treated as finish problems (CLOSEUP 1.5) | ER0 is judged on clay as well as with finish: a geometry call is fixed in geometry |
| Light changed every round (CLOSEUP 1.4) | Judge rigs A (product) and B (courtyard + sun) are frozen, with grey-card exposure, AgX and real-photo controls (the close-up plan's rig, reused) |
| Late discovery cost whole rounds (AR-01, SMG) | ER0 at W1c is a gate; the triangle and texel estimates are checked at blockout |

---

## 2. Geometry method per part (headless Blender 5.2, generators in `Scripts/guns/pistol/`)

| Part | Primitive | Notes |
|---|---|---|
| Barrel group | lofted section rings (rib + facets + hood), revolve (crown, bore) | facet run-out = a section-ring parameter along X; bore depth >= 25.4 |
| Slide | extrusion of the faired side outline with **Y-profile lands** (the octagonal section = 2D section x outline, built as one closed solid) + serrations as outline teeth on the rear block | the serration crest and root lands are part of the section; the ejection window and the guide-rod bores are built into the solid (revealed only when the slide is back) |
| Front plate | extruded outline with chamfer lands | own object, joined into the slide part group |
| Frame | outline extrusion + C-fillet lands (variable along the edge set: cast 1.0-1.5, machined 0.5) | guard opening is part of the outline (not a boolean); parting line as a 0.05 step |
| Grip | traced side outline lofted to a YZ lens (the SR01 W4b grip method) with the border as real geometry; panel field dropped 0.6 | pebble from the HP bake |
| Trigger | loft of crowned sections along the traced centre curve | 6.5 thick |
| Hammer, safety, slide stop, release, flank tab | outline extrusions with lands; grooves as outline features | dished pad = shallow loft |
| Sights | outline extrusions; dovetails part of the section | front dot ring as a flush inset |
| Rail | gunlib `rail_1913(6)` (read only; called, not edited) | sits in the drawn recess |
| Magazine | gunlib `mag_box` with single-stack parameters (proposal §9) or a local generator if the parameters are missing | base plate machined |

Avoid (study 4.4): SDF / remesh, subdivision on shipped meshes, Decimate LODs, booleans on curved faces.

---

## 3. Clips (FP and TP use the same clips; fps and keys in the spec)

| Clip | Content | Notifies |
|---|---|---|
| `A_HP01_Fire` (60 fps, 10 f) | trigger pulls, hammer falls (+58), slide back 48 (f4) and home (f8), hammer recocked by the slide (5 deg over-travel), trigger resets | `Fire` f1, `ShellEject` f3 |
| `A_HP01_FireLast` | as Fire, but the slide stops at 46 and the slide stop rises (+10) | `Fire`, `ShellEject`, `SlideLock` f6 |
| `A_HP01_Reload` (30 fps, 60 f) | release pressed, mag out along -Z of `Mag` (130 mm), new mag in, seated f42 | `MagRelease`, `MagOut`, `MagDrop`, `MagIn` |
| `A_HP01_ReloadEmpty` (70 f) | starts at FireLast's end (S0 check); mag swap; slide stop down f52, slide home f55 | + `BoltRelease` f52 (the standard name for the slide release) |
| `A_HP01_Safety` | 0 -> -40 -> 0 | - |
| `A_HP01_SlideRack` | slide back 48, held, released; hammer cocked | `BoltRelease` |
| `A_HP01_Inspect` | press check: slide 14 mm back, held, home. The gun's turn is the character's montage | - |

**Reload patterns 1 and 2 are both supported** (study 6.2): the `magazine` bone is keyed, and the notifies travel in
the sidecar.

**Procedural use** (`ABP_Gun_Pistol`): slide -X for recoil kick, hammer and selector about Y, trigger pull. The table
is in `hp01_interface.json`.

**FP / TP:** FP_Weapon + TP_Weapon on `SK_HP01`, FP_Mag + TP_Mag. The FP components use `ForcedLodModel = 1`, so LOD0
and the textures must hold at 25 cm (inspect).

---

## 4. Gates (copied into the spec; thresholds from study 7 unless noted)

- **S0** (spec): pass.
- **L1-L7** with the pistol notes in the spec. LEFT is the authority; RIGHT is reported, being a mirror. TOP is gated
  on the Q1 width.
- **B1-B10, H1, M1-M5, U1-U12** as study 7.2 / 7.4. B3 sweeps the slide over 0..48 together with the hammer
  (combined states: slide back x hammer cocked / down, slide stop up x slide at 46) and the mag path along the 17.4 deg
  axis.
- **Close-up gates CU1-CU8** (spec `gates`), from W1 on:
  - **CU1** faired outlines;
  - **CU2** authored bevel lands;
  - **CU3** no slivers (UD + 2 deg + B6a);
  - **CU4** ER0 at W1c (decisive fail = stop);
  - **CU5** finish cards on swatches;
  - **CU6** real-pattern small-part audit;
  - **CU7** marks audit;
  - **CU8** feature identity at real scale.

---

## 5. Stages: separate fresh workflows, each from a commit (rough cost = API spend at the line's history)

**Every workflow:**
- holds lock `HP01` (and nothing else of another chat's);
- runs one Blender process at a time, headless;
- writes `WorkFiles/guns/pistol/gates/<stage>.json`;
- ends with a commit the user asked for;
- exports only through `Scripts/pipeline/`, with `qa_check` first.

**Stop and show the user on:**
- L1 < 0.90;
- an ER0 decisive fail;
- a triangle projection > 30k with the rules met;
- Q1 unanswered when W1b starts and the user has asked to be consulted.

| Stage | Does | Gates | Rough cost |
|---|---|---|---|
| **W0 (this run)** | measurement, traces, craft study, spec, plan, design sheet | S0 pass | ~$5 |
| **W1a setup** | `Scripts/guns/pistol/` skeleton (`build_pistol.py` staged with the lock asserted, `hp_parts.py`, `hp_fair.py`, `run_pistol.sh`); read-only use of gunlib 0.3.x (`mesh`, `rail_1913`, `hardware`, `ud`, `qa_gun`, `fit`, `rig`); gunlib proposals (§9) handed to the gun chat | gunlib untouched (hash check) | $3-5 |
| **W1b blockout** | primary volumes from the faired traces; H1 early (pistol pose on `MH_PlayerDefault`); triangle and texel projection | L1, H1-early, projection <= 25k | $5-8 |
| **W1c form G1 (rear: slide rear block + serrations, hammer, safety, slide stop, frame tang, grip top)** + **ER0** | full form with lands; sweeps; CU1-CU3, CU6 on G1; **ER0**: 8 crops on clay + flat finish cards, 2 judges, 6 controls | form_g1.json, early_realism_g1.json | $8-12 |
| **W1d form G2 (barrel, rail, sights, front plate, slide front, guide rods)** + **W1e G3 (frame, guard, trigger, release, grip, mag)** | as G1, with an ER round each (cheaper: 4 crops) | form.json, early_realism_g2/g3.json, form_magfit.json | $12-18 |
| **W2 surface** | UV by class (Steel / Furniture / Mag), HP bakes (pebble, checkering, machining, parting lines), finish cards, wear by cause, marks, Masks; renders from baked maps only; ER-tex (at most 2 rounds) | uv_bake_paint.json, early_realism_tex.json | $15-25 |
| **W3 rig + mag + export** | LOD1-3 from the generators; rig, 7 clips, sidecar with notifies; twin (4 UCX), `PHYS_HP01`; mag LODs, M1-M5 on exported bytes; H1 full; fresh-process verify | game.json, rig_export.json, mag.json | $12-18 |
| **W4 review + one fix round** | review sets from the exported bytes (fp35, ADS, TP 3 m, hero, inspect 25 cm), L6, L7, two realism judges with controls; one fix round in the generators, then the full chain from nothing | review_fixes.json | $10-20 |
| **W5 Unreal** | harness copied from the carbine / SMG `UnrealCheck`; U1-U12, U2b (the second pistol, when one exists, is reported) | verification_summary.json | $8-12 |
| **W6 finish** | pack materials under `PackMaterials` (`run_build.sh`), README + MATERIALS_README, showcase via `studio.py`, `ASSET_LIST.md` row; release the lock; ask before merge / push | pack_materials.json, docs_showcase.json | $6-10 |

**Total, rough:** $80-130 to an engine-verified, packed pistol, with one fix round. The biggest uncertainty is the
number of ER rounds.

---

## 6. Collision, physics, LODs

- **`SM_HP01` UCX hulls (4):** slide + barrel box, frame front box, grip hull, guard hull, all `UCX_SM_HP01_00..03`
  keyed to the node name.
- **`SM_HP01_Mag`:** 1 hull.
- **`PHYS_HP01`:** one body on `body`, 2.0 kg, CoM from part volumes.
- **LOD screen sizes:** start at 1.0 / 0.25 / 0.09 / 0.03. The bounding radius is ~0.17 m against the rifle's 0.45,
  so the LOD-pop gate measures and fixes them. The mag sizes are derived (study 5.6).
- **Bounds extension:** the envelope over every clip (slide back 48 mm, mag 130 mm out).

---

## 7. Texel and texture estimate

See CRAFT §5:
- Steel: ~800 cm2 at classes A-D (pistol targets), ~4.1 M texels at 70 % fill, so 4096 (2048 holds 2.9 M).
- Furniture: 1024.
- Mag: 1024.

The packer decides at W2: the smallest power of two that meets the classes.

---

## 8. Risks

| Risk | Handling |
|---|---|
| **Q1 width:** a 47 mm slide reads toy-like in first person; judges may call it on proportion | Ask before W1; `K_Y` is one parameter; ER0 includes an fp35 crop to show the user both widths if the default stays |
| The octagonal slide with facet bands needs crisp, evenly lit facets; brushed stainless shows every normal error | Section-ring generator with analytic normals per facet; G4 (flat-face normal deviation < 1 deg) checked at W1c |
| Serration teeth at 0.25 breaks may shimmer (TSR) at 45 cm | Crest break >= visibility minimum 0.35 at the rear; the LOD1 serration simplification is checked by the LOD-pop gate |
| Pebble grip reading as noise | HP bake at real scale, >= 3 texels per cell (CU8); swatch-judged first |
| The mirrored sheet invites mirrored wear | No mirrored UVs (study 5.8); wear by cause, with left and right different (G9) |
| An invented mag release looks off-design | Low profile, inside the drawn steel strip; L3 checks the silhouette is unchanged |
| The gunlib changes the pistol needs are not made by the gun chat | Local modules in `Scripts/guns/pistol/` with the same interfaces; promotion later |

---

## 9. Proposed gunlib changes (for the gun chat; **not made**)

| # | Change | Why |
|---|---|---|
| GL1 | `gun_standard.json`: a `budgets_triangles.pistol` row (LOD0 15-25k, ceiling 30k, lod3 0.8-1.2k) and `mag_pistol` (1-2k, ceiling 2.5k) | study 5.7 has the numbers; the standard lacks the row |
| GL2 | `motion_axes.HP01`: slide -X, hammer / trigger / selector / slide_stop about Y, mag_release -Y | the standard's shared names move differently on a pistol (as CB01 needed for its release) |
| GL3 | `camera.pistol`: the eye-to-part distances (hip 350-450, ADS 300, inspect 250-350) and the raised C / D texel targets | first person sits closer than for long guns (CRAFT §5) |
| GL4 | `fair.py`: an outline fairing module (curvature-limited spline fit with pinned corners, deviation report) used by every traced outline | the sniper W4b and carbine ER1 geometry calls; CU1 |
| GL5 | `mesh.py`: per-edge-set authored bevel lands on outline extrusions (no modifier clamp) | sniper W4b root cause; CU2 |
| GL6 | `mag_box`: single-stack parameters (tube section, wall, witness holes, base-plate step) | HP01 magazine |
| GL7 | `rail_1913`: an option to sit in a recess (end walls and ramp to the parent surface) | the HP01 rail sits in a drawn recess |
| GL8 | Socket rule note: `Muzzle` on `body` when the barrel is fixed (the pistol table says slide) | R4 |
| GL9 | Pistol-class grip pose in `gun_standard.json` after the HP01 H1 (replaces the provisional 46 mm for the class) | R16 |

---

## 10. Sources checked

- The repo's study and plans: GUN_BUILDING_STUDY (1-9), CB01 W0 (format), CLOSEUP_METHOD_PLAN, carbine ER1 gate,
  sniper W4b report.
- `gun_standard.json` 0.3.0 and gunlib `qa_gun.py` (deny list), both read only.
- The sheet.

No web sources: WebSearch was not permitted in this run, so the class figures are from the study table.
