# SM_Kunai_Plain: build report

**Date:** 2026-09-19. **Library:** shuriken_lib 3.10.1. **Status:** built, reviewed (geometry / Unreal / visual), the review's blocker and majors fixed and rebuilt; all gates pass and all seven forms are verified in Unreal 5.8 on the exact exported bytes.

> **Library 3.11.0 (2026-09-27): section 14 is the blade-section rework (option C: a 7 mm diamond over a 0.3 mm edge, the knife coat rule, the 3/4 hero); its numbers win over sections 1-13.**
>
> **Sections 1-12 describe the 3.10.0 build. Section 13 is the review and what changed** - the tape wrap is geometry
> now, the lettering band is unrolled inside the wrap's own island, the ring's walls are smooth, and the lettering
> mask gets its mips in Unreal. Where a number below moved, section 13 gives the new one.

The user asked for a kunai in the pack, then also a plain (non-winged) one, then said "skip the winged kunai for now". This build is the **plain kunai only**. The three-pronged head stays a spec option (`KunaiSpec.prongs`), OFF, and the generator refuses it. Nothing winged was built, exported or rendered.

Machine-readable report: `WorkFiles/shuriken/kunai_plain_report.json` (plus `pack_report.json`).

---

## 1. What was built

A plain kunai: a leaf blade in a shallow diamond section with the pack's knife grind, a clean shoulder, a 6 mm bare neck, a worn dark tape-wrapped grip with collars, a tapered rear neck and a flat forged ring. It has no lettering anywhere. A blank 72 x 12 mm band on the grip's +Z face samples its own mask texture for the user's text.

| | Build-to (study 4, plain) | Measured |
|---|---|---|
| Overall, tip to ring end | 280 mm | 280.000 mm |
| Blade, shoulder to tip | 140 mm | 140.000 mm |
| Blade max width / base width | 36 / 16 mm | 36.000 / 16.0 mm |
| Stock (ridge at base) | 5.0 mm | 5.0 mm |
| Knife grind | 35°/side, 0.15 mm land, tip radius 0.075 mm | 35°, 0.15 mm, 0.075 mm; grind 1.06 to 1.35 mm wide; apex x 135.2 mm |
| Grip over wrap / collars | 20 mm / (21.2 mm estimate) | 20.0 / 21.2 mm — **3.10.1: 20.0 mm over the tape ridges, 19.0 mm flat; the collars are gone (13.1)** |
| Ring OD / ID / stock | 32 / 20 / 5 mm, r 1 mm rounds | 32.000 / 20.000 / 5.0 mm |
| Shoulder | blade base meets the 6 mm bare neck | 16° concave corner, 0.45 mm chamfer, 3 mm grind run-out, V plunge at x 3.6 mm |

**The shoulder.** The fork plane became a normal kunai shoulder. The blade's base edges flare 16° out of the neck's straight sides. The 16 x 5 mm neck carries the stars' non-cutting treatment: a 0.45 mm chamfer at the grind angle over a wall. The knife grind runs out into that chamfer over 3 mm (the 3.9.1 run-out taper). The flat neck stock ends in a V-shaped plunge line, one planar plunge triangle per side from the stock face down to the grind line.

## 2. Mass, assembled mass and pivot

Study basis for the plain kunai: `WorkFiles/kunai/plain_calc/kunai_plain_mass_check.py`. This is the study's own arithmetic (imported from `study_calc/kunai_mass_check.py`), with the prongs and the fork web removed.

| | Study basis (plain) | Mesh |
|---|---|---|
| Steel, un-ground (the mass gate) | 153.02 g | **151.89 g** (-1.13 g, gate ±2 g **PASS**) |
| Steel, finished | 151.37 g | 148.51 g |
| Wrap: tape 0.75 + wooden core 0.70 g/cm³ | 13.4 to 18.6 g | 16.04 g (tape 4.27, core 11.77) |
| **Assembled** | 164.8 to 170.0 g (mid 167.4) | **164.55 g** |
| Mass-weighted centre (pivot) | x = -22.49 mm | **x = -21.06 mm**, 15.1 mm inside the grip |
| Wrong pivot (Origin to Center of Mass, Volume) | -37.9 mm | -37.33 mm — **measured on the mesh in 3.10.1: -35.85 mm (13.3)** |

- The finished steel is 2.9 g under the study basis for three reasons. The ring has r 1 mm rounds on a 24-gon. The rear neck tapers from 16 x 5 to 12 x 4.4 mm into the ring, so its faces never lie in the ring's faces. The study's flat-stock grid has neither. That puts the assembled figure 0.25 g under the study's lower bound. It is reported, not gated.
- **Against the plain replicas in the study:** zinc 290 x 50 mm casting 140 g, Leones 26 cm 162 g, 12 in / 5.1 mm thrower up to 176 g, Honshu 12 in 227 g (a 41.5 mm-wide, 305 mm one-piece blade), forged 12 in 283 g (unconfirmed). 164.6 g sits inside that spread.
- **Removing the prongs moved the centre of mass toward the grip:** -18.6 mm (winged study), -22.5 mm (plain study basis), -21.1 mm (mesh). The object origin IS the mass-weighted centre: the mesh is authored shifted by it.
- **Physics override:** 0.1646 kg, the assembled mass. The study's 0.19 kg was the winged kunai's. **3.10.1: 0.1619 kg (13.6).**

## 3. Collision: two hulls (re-decided)

| Option | Volume |
|---|---|
| Render mesh (shells summed, joins counted twice) | 41,838 mm³ |
| **Two hulls (chosen)** | **64,337 mm³**: head 10,356 (1.2 x the steel head) + grip/rear-neck/ring 53,981. **3.10.1: 60,316 mm³ = 10,356 + 49,961 (13.3)** |
| One hull | 83,171 mm³ (1.29 x) |
| Three hulls (ring apart) | 50,910 mm³ |

The plain head is 36 mm wide against the winged 100 mm, which removes the winged head's worst case. One hull still has to span the 21 mm grip and the 5 mm blade together. Its faces run from the collars (±11 mm) to the tip, so there is about 8 mm of invisible collider above and below the blade at its widest. A kunai stuck in a wall or hitting a character would touch 5 to 8 mm before the steel does.

Two hulls follow the blade and the grip. A third hull would take a further 21 % off at the ring end, but it was not taken: the study's plan is two, and the ring end sits behind the hand.

Unreal derives the centre of mass from the hulls at uniform density. The hull-derived centre is x = -30.6 mm from the pivot, so set the Body Instance's **Center Of Mass Offset to (+3.06, 0, 0) cm**.

## 4. Sockets, LODs, screen sizes

- **Sockets** (Empties + sidecar, positions relative to the pivot):
  - `Grip`: x -54 mm from the shoulder, -3.29 cm from the pivot.
  - `Trail`: -140 mm (ring end).
  - `Tip`: +140 mm.
  - `Ring`: -124 mm (ring centre, for a rope or the queued paper tag).
  - Axes: +X to the tip, +Z out of the lettering face.
- **LODs:** 1,256 / 600 / 238 triangles against the plain bands 1,000-2,000 / 400-900 / 150-400. Nothing is padded. The study's winged table does not apply to the plain kunai. **3.10.1: 2,182 / 696 / 366 against 1,000-2,600 / 400-900 / 150-400 (13.6).**
  - LOD1 has half the stations, a 10-sided grip with collar steps, a 12 x 8 ring and a square rear neck.
  - LOD2 has land-0 edge lines, square neck edges, an 8-sided grip without collars and an 8 x 4 square ring.
  - All three keep the lettering band's mesh lines.
- **Screen sizes:** 1.0 / 0.28 / 0.098, the pack's values scaled by Unreal's bounds radius of 140.008 mm. They switch at 0.889 m and 2.540 m.
- **Two-sided LOD deviation:** LOD1 0.55 mm, LOD2 1.48 mm. **3.10.1: 0.63 / 1.18 mm.**

## 5. Materials, textures, UVs

- **Two material slots:**
  - Slot 0, `M_Shuriken_Master` (the steel), in the new **class mode**: the surface class comes from a FACE attribute instead of |N.z|, because the diamond faces tilt 4 to 12°. It is one Mix, **proven a bitwise no-op on all six frozen forms** by a CPU bake (`WorkFiles/kunai/plain_build/material_noop_check.json`).
  - Slot 1, `M_Kunai_Wrap` (the cloth), in `shuriken_lib/kunai_wrap.py`. It is dark cotton tape (linear ~0.04), wound as a 9 mm-pitch helix with 0.35 mm tape edges and a weave in the normal map. The collars are wound straight with frayed ends. It has faded patches, fibre flecks, hand grime mid-grip, the cut ends as dark wound layers, and roughness 0.85 to 0.9. **3.10.1: the tape’s overlap is geometry and this material carries the crown, the foot line, the fray and an irregular 1.15 mm weave (13.1).**
- **Maps:**
  - `T_Kunai_Plain_BC/_ORM/_N`: 2048, **UV tile u 0..1**, 13.4 px/mm.
  - `T_Kunai_Wrap_BC/_ORM/_N` + `T_Kunai_Wrap_Natural_BC` (the undyed option, linear ~0.40): 1024, **UV tile u 1..2**, 10 px/mm.
  - `T_Kunai_Lettering`: 1536 x 256 greyscale, **blank**.
  - Unused texels are filled. ORM and N carry no colour chunk, and N is DirectX.
- **Why two UV tiles:** the slots sample different maps, and keeping the wrap in u 1..2 means no UV0 triangle overlaps another anywhere. Wrap addressing (Unreal's default) reads the same texels. Unreal's generated lightmap UV1 is then overlap-free on every LOD.
- **UVs are analytic on every LOD** (hook `lod_uv`): one function of each face's island, with no packer and no transfer.
  - Head top and bottom: planar projections, with the 0.15 mm knife lands unfolded onto the top island.
  - The remaining wall strips.
  - Ring top and bottom: planar.
  - Ring inner and outer strips.
  - Rear neck strips.
  - Wrap: unrolled, seam on -Z.
  - The lettering band as its own straight island. **3.10.1: the band is a rectangle inside the wrap island (13.2).**
  - Two caps.

## 6. Lettering band

The band covers X -90 to -18 mm on the +Z face, ±34.4° (12 mm of arc).

| Convention | UV rectangle (3.10.0) | **UV rectangle (3.10.1, shipped)** |
|---|---|---|
| Blender UV0 | u 1.015625 to 1.718750, v 0.65265482 to 0.76984232 | **u 1.13281250 to 1.83593750, v 0.26382741 to 0.38101491** |
| Unreal UV0 (V flipped) | v 0.23015768 to 0.34734518 | **v 0.61898509 to 0.73617259** |
| Wrap-map pixels | x 16 to 736, rows 235.68 to 355.68 | **x 136 to 856, rows 633.84 to 753.84** |

The band is a rectangle of the wrap's own straight unroll from 3.10.1, not its own island (13.2).

- **Orientation:** U runs from the ring end toward the tip; V runs toward +Y. Seen from the +Z face with the tip to the right, text drawn upright in the mask reads upright.
- **The mask:** `T_Kunai_Lettering` is 1536 x 256 (6:1, 21.3 px/mm). Suggested 1536 x 256, or 3072 x 512 for close-ups.
- **Unreal import:** sRGB off, Grayscale, Clamp, Stretch to power of two — **and Mip Gen Settings “From Texture Group”: a non-power-of-two PNG imports with NoMipmaps and Stretch does not reset it (13.2). All five are set and verified in a fresh process.**
- **Gates (3.10.1):** every face of the unrolled grip carries the analytic wrap UV to 0.01 px on every LOD and the recorded rectangle is that map's image of the 72 x 12 mm region (`form_gates.lettering_band_island_and_blank_mask`); in Unreal, every band corner of the render data sits within half a float16 step of that same map, on the +Z face, covering the 72 mm, with U toward the tip (gate 13).
- **Full swap instructions and the material graph:** `References/Kunai/LETTERING_HOWTO.md`.
- **Neutral test pattern (not shipped):** `WorkFiles/kunai/lettering_test/` (`lettering_test_sheet.png`).

## 7. Gallery (baked maps only)

- **Hero:** `Renders/Shuriken/kunai_plain_persp.png`, yaw -25°, the point toward the viewer. **The yaw was chosen by measurement.** The diamond faces tilt, so how much of the key strip they mirror depends on the blade's direction.
  - A 3/4 pose across the frame (yaw 40, the spike's) reads coat p50 0.39 against the anchor forms' 0.56.
  - Only about -10 to -30° lands inside the pack's 0.05. At -25° the coat is p50 0.534 / mean 0.509: headroom 0.025 on the p50 and **0.009 on the mean**.
  - Evidence: `WorkFiles/kunai/iteration/hero_yaw_probe*.json/png`.
- **Top view:** `kunai_plain_top.png`, drawn at 5.0 px/mm in its own 0.18 m frame. The pack's 0.13 m frame is only 0.231 m wide. The line sheet labels this.
- **Other gallery images:** `kunai_plain_lodgrind.png` (the tip's grind on all three LODs), `kunai_plain_wire.png`, `kunai_plain_lods.png`.
- **Sheets:** `Renders/Shuriken/modern_line_sheet.png` has a Kunai panel, and `style_comparison.png` has a new KUNAI column. Both were regenerated from the final build by `WorkFiles/kunai/plain_build/postbuild_sheets.sh`, which also re-renders the lettering proof.

## 8. Gates and evidence

| Gate | Result |
|---|---|
| Final `build_pack.py`, all seven forms, `--frozen-maps post_hooked_cross/textures` (`WorkFiles/kunai/plain_build/build_pack_final.log`, 324.8 s, finished 2026-09-19 04:34) | exit 0, every form passed |
| Kunai: knife shading, outline mass, qa_check (62 checks), LOD bands, UV consistency (0 overlaps; per-slot tiles; cross-LOD top plate 0.0001 px, surface ≤ 2.3 px), textures, render gates, franchise names, lettering band + blank mask, two slots every LOD, no collapsed UV faces | all pass |
| Pack consistency (knife like with like: steel coat pixels against PACK_COAT_ANCHOR; whole object and wrap information; hero backdrop at 12 points) | pass; no anchor drift |
| Frozen maps of the six frozen forms | fresh bakes within noise (≤ 1/255); the snapshot bytes shipped |
| Frozen-forms regression against `post_hooked_cross` on the final build (geometry, hulls, sockets, UVs, corner normals, maps, FBX content, sidecars, report figures, material export scalars) | **identical for all six** (`WorkFiles/shuriken/regression/regression_kunai_plain_frozen.json`) |
| M_Shuriken_Master class mode on the frozen forms (CPU bake, 512 px, every channel) | bitwise identical |
| Unreal 5.8 UnrealCheck6, on the final build's bytes, fresh content path `/Game/ShurikenCheck6/KunaiPlainFinal`, each pass its own process, pass 2 reloads in a fresh process, SHA-256 bound (kunai FBX `0a08104f...`) | **all seven VERIFIED**, 0 Warning/Error lines in all 21 passes |
| Kunai in Unreal | LOD triangles delta 0; exactly 2 convex hulls; 4 sockets at scale 1; bounds 28.0 x 3.6 x 2.12 cm; screen sizes 1.0/0.28/0.098; UV1 from UV0; 2 sections per LOD, steel in u 0..1 and wrap in u 1..2; lettering band on +Z; round trip positions and UV-keyed positions 1e-6 cm; both hulls round-trip 1e-6 cm and contain LOD0; UV1 overlap 0 on every LOD |
| Texture flags (import, then verify in a fresh process), all 26 maps | pass |
| New baseline `WorkFiles/shuriken/regression/post_kunai_plain` (seven forms, taken from the final build after the Unreal result was attached), self-check | identical |

`Scripts/pipeline` was not changed.

## 9. Defects found and fixed during the build

1. **Ring UV seam across its flat face.** The first ring layout was a torus unwrap, and the cross-LOD top-plate gate read a 1,094 px jump across its seam. The fix: planar top and bottom islands plus inner and outer strips.
2. **The wrap's cut ends drew radial streaks.** The tape recipe's coordinates reduce to an angle on a cap. The caps now have their own pattern: concentric dark layers, fraying only at the rim.
3. **The bare neck's side wall collapsed in UV0 to a line.** It was on the hidden rear wall strip. Unreal's round trip caught it: two positions shared one UV. The fix: the wall between two columns belongs to the first column's chain. A new form gate now checks every LOD for collapsed UV faces.
4. **Lightmap overlap.** The 140 mm x 0.15 mm blade lands made a sub-texel-thin chart that Unreal's lightmap packer laid across the wrap's chart (4,050 px overlapping at 2048). The fix: the lands are unfolded onto the head's top island. UV1 overlap is now 0 on every LOD. Evidence: `WorkFiles/kunai/plain_build/uv1_lightmap_run2_overlap.png`.
5. **Checker fixes (UnrealCheck6).** Unreal writes both convex elements into one `UCX_` node, so the round trip now splits it by connectivity. The gates learned a form's own hull count, socket names and material slots. Originals are kept as `*.before_kunai.py`.
6. **Transient engine warning in run 2.** A `LogPackageName` warning appeared during pass 1's second save: the uncontrolled-changelist scan raced the save. Nothing was relaxed. Run 3 went into a fresh path and was clean. Run logs: `run_all_kunai_plain_run1_neck_uv_bug.out`, `run_all_kunai_plain_run2_lightmap_overlap.out`, `run_all_kunai_plain_run3_build3.out` (clean, on the previous build), and `run_all_kunai_plain.out` (the final run, on the final build, `/Game/ShurikenCheck6/KunaiPlainFinal`, clean).
7. **Stale gate text in the kunai's `engine_check`.** The build writes a "pending" block whose gate list is the stars' (one hull, two sockets). The kunai's own gates (2 hulls, 4 sockets, gate 13) were right, but the description was not. `attach_engine_check.py` now writes the gates the kunai was actually held to when it attaches the verified result. Only that text and the attach time changed; the six frozen forms' reports changed only in the attach time.

## 10. The paused winged work: what was reused

`WorkFiles/kunai/winged_wip_scripts_2026-09-19/` was diffed against the live tree and reviewed.

- **Kept, and rewritten for the plain head:**
  - the 1 nm keyed vertex factory per shell
  - the column / diamond-station / plunge construction and the CDT plateau
  - per-shell volume, mass and centre of mass
  - the analytic-UV hook
  - per-shell cross-LOD UV
  - explicit part hulls with a vertex containment check
  - the class-mode idea in M_Shuriken_Master
  - the tape-helix recipe idea
  - the render knife class, wrap mask and top-frame options
- **Not kept:**
  - the fork, prong and crotch code
  - the single-material 4096 x 2048 layout (the wrap was a branch of M_Shuriken_Master, and the lettering sat inside the BC)
  - the elliptical wire-torus ring
- **WIP defects found in review:**
  - the neck chamfers would have been polished as knife facets
  - the un-ground reference had no closing diamond triangle at the tip, which leaves a hole and a wrong mass

## 11. Known gaps

- The pack has **no Unreal materials yet**. Both slots bind to WorldGridMaterial in the validation import. The wrap material's lettering graph is specified in `LETTERING_HOWTO.md`, not built.
- The physics override (0.1646 kg) and the COM nudge (+3.06 cm X) are recorded, not applied. They have to be set in the throwing Blueprint.
- The hero is nearly end-on. That is the pose that keeps the diamond coat inside the pack tolerance; the coat-mean headroom is 0.009. A 3/4 pose would need a knife-specific hero rule, and that is a decision for the user.
- The top view is at 5.0 px/mm, not the pack's common 6.9.
- The assembled mass is 0.25 g under the study's plain range (ring rounds and the neck taper), and the un-ground steel is 1.13 g under the study basis, inside the gate.
- The winged head is an option that is refused today. Bringing it back means a new outline chain in `kunai_spec.KunaiPlan`, then its own build and gates. The silhouette's Fab risk stands (study 6).
- `compare_frozen.py` compares a form's `T_<mesh>_BC/_ORM/_N`. The kunai's wrap maps are protected in later builds by the `--frozen-maps` freeze (tested: identical maps pass, a perturbed map fails), not by that script.

## 12. Files

- **Scripts:**
  - `Scripts/shuriken/build_kunai_plain.py`
  - `Scripts/shuriken/shuriken_lib/kunai_spec.py`, `kunai.py`, `kunai_wrap.py` (new)
  - `material.py`, `bake.py`, `pack.py`, `render.py`, `hooks.py`, `__init__.py`, `line_sheet.py`, `ue_import_textures.py` (changed; every change defaults to the old path)
- **Assets:**
  - `Assets/Shuriken.blend` (seven forms)
  - `Exports/Shuriken/SM_Kunai_Plain.fbx` + `.sockets.json`
  - `Exports/Shuriken/Textures/T_Kunai_*`
- **Renders:** `Renders/Shuriken/kunai_plain_{persp,top,lodgrind,wire,lods}.png`, `modern_line_sheet.png`, `style_comparison.png`
- **Evidence:**
  - `WorkFiles/kunai/plain_calc/`
  - `WorkFiles/kunai/plain_build/` (build logs with `build_pack_final.log` the shipped one, the material no-op check, the style sheet script, `postbuild_sheets.sh`)
  - `WorkFiles/kunai/iteration/`
  - `WorkFiles/kunai/lettering_test/` (`lettering_test_render.py`, `compose_sheet.py`)
  - `WorkFiles/shuriken/UnrealCheck6/` (`run_all_kunai_plain.sh`, `kunai_plain_pass{1,2,3}.json`, `verification_summary.json`, `roundtrip_compare.json`)
  - `WorkFiles/shuriken/regression/post_kunai_plain/`
- **Documentation:** `References/Kunai/LETTERING_HOWTO.md`

---

## 13. Review and fixes (library 3.10.1, 2026-09-19)

The build above was reviewed three times independently, on the shipped bytes: geometry (a scratch copy of the blend
and of the FBX), Unreal 5.8.2 (fresh processes on the exact FBX), and visual (the gallery rig with the shipped maps).
Verdicts: geometry **PASS with minor findings**; Unreal **VERIFIED, with one latent major** (the lettering mask imports
with no mips); visual **NOT READY** - the grip read as a moulded rubber / knurled handle rather than cloth tape, and
the bare neck read as a black slot in the hero.

Everything below was fixed by rebuilding the whole pack from the scripts; the six frozen forms are untouched (13.5).

### 13.1 The blocker: the wrap read as moulded rubber

The tape was a smooth 16-sided cylinder with raised collars and a 0.35 mm normal-map helix, so no overlap ever reached
the silhouette; its weave was a 0.5 mm sine (5 texels at 10 px/mm) that moired; the cut ends were flat discs of
concentric rings. **The tape's overlap is geometry now.** `kunai_spec.tape_phase / tape_radius / wrap_radius` define
the wound tape - the study's flat 10 mm tape at a 9 mm pitch, so 1 mm of every turn lies on the turn before and its
exposed edge stands one tape thickness (0.5 mm) proud - and `kunai.author_wrap` authors it in the unrolled grip: one
strip per grip face, cut by every profile break of the helix and by the rings inside the wound-down ends, each piece a
flat face whose corners carry the analytic radius.

| | 3.10.0 | 3.10.1 |
|---|---|---|
| Grip over the wrap | 20.0 mm smooth, 21.2 mm over collars | **20.0 mm over the overlap ridges, 19.0 mm over a single layer** |
| Tape relief | 0.35 mm in the normal map | **0.5 mm of geometry** (the study's "1 mm tape" = the doubled overlap; core 18 mm) |
| Ends | 6 mm collars, flat cap discs | **wound down onto the tang over 6 mm** (a lashing), a thin cut rim |
| Weave | 0.5 mm sine crosshatch | **1.15 / 0.94 mm irregular threads** with slubs and a fibre fuzz |
| LOD0 triangles | 1,256 | **2,182** (band raised to 1,000-2,600; the wrap is ~1,300 of them) |
| Wrap luminance p05-p95, top view | 0.075 | **0.149** |

`M_Kunai_Wrap` now carries only what geometry cannot: the burnished crown the hand rubs along each turn's edge, the
dirt line at the foot of each step, loose fibres fraying along every tape edge and at the two cut ends, the weave, and
more value variation (faded patches at 7 and 16 mm, hand grime). The gallery's preview material adds a cloth **sheen**
term - a shading model, not a map: in Unreal use the Cloth shading model's fuzz for the same read.

### 13.2 The majors

**The bare neck read as a black slot.** The 21.2 mm collar rose 8.1 mm over the 6 mm neck, and the neck's +Z face
mirrored it; the class-mode gates called that face coat and averaged it away. The wound-down ends removed the collar,
so nothing towers over the neck: the hero's object fraction below 0.05 luminance is **0.0066** (0.021 before, frozen
forms 0.000-0.002), and its coat fraction below 0.03 is **0.0088**. A gate came with it: `render.coat_gate` (hero and
top) fails a form whose flat coat steel has more than 2 % of its pixels below 0.03 - dark pixels are a wall's business,
not the plate's. All seven forms pass; the six frozen ones measure 0.000.

**The lettering band showed as an outlined panel.** Its own UV island drew a seam along the grip, and the relief /
cleanliness switch over 0.3 mm of arc baked a ridge and cut a clean rectangle out of the grime. The band is now a
rectangle **inside the wrap's own straight unroll** - the same square-texel mapping, no island seam - at full tape
relief, with only a light grime reduction feathered over 4 mm of grip and 2.5 mm of arc. New rectangle: UV0 (Blender)
u 1.13281250 to 1.83593750, v 0.26382741 to 0.38101491; wrap-map pixels x 136 to 856, rows 633.84 to 753.84
(`References/Kunai/LETTERING_HOWTO.md` section 4). Its gate was rewritten on the MAPPING: every face of the unrolled
grip carries the analytic wrap UV to 0.01 px on every LOD, and the recorded rectangle is that map's image of the
72 x 12 mm region, so a mask drawn for LOD0 still lands identically on LOD1 and LOD2. The Unreal gate 13 was rewritten
the same way (every band corner in the render data within half a float16 step of that map).

**The ring's walls were flat-shaded.** `write_ring_normals` gave the 24-gon's inner and outer walls their face
normals, so every facet edge was a hard seam, unlike the stars' smooth hole walls. The walls take the **radial normal**
now; the r 1 mm rounds keep their analytic arc normals, which are tangent to it, and the flats keep their exact face
normal.

**The lettering mask imported with no mips.** Measured twice in fresh UE 5.8.2 processes: the texture factory imports
the non-power-of-two 1536 x 256 PNG with `MipGenSettings = TMGS_NoMipmaps`, and Power Of Two Mode "Stretch to power of
two" does **not** reset it. The mask ships blank so nothing was visible, but lettering painted into it would be sampled
without mips (the band is ~78 px wide at the LOD1 switch and ~27 px at 2.54 m) and shimmer.
`Scripts/shuriken/ue_import_textures.py` now sets `mip_gen_settings = TMGS_FROM_TEXTURE_GROUP` and **fails
verification on NoMipmaps**; section 6's claim above is corrected here, and the howto lists five flags, not four.
Verified in a fresh process on the shipped mask: `TMGS_FROM_TEXTURE_GROUP`, `STRETCH_TO_POWER_OF_TWO`, sRGB off,
TC_Grayscale, Clamp/Clamp (`WorkFiles/shuriken/UnrealCheck6/textures_verify.json`).

### 13.3 Minors fixed

- **The steel's wall wear was a barcode.** The scratch and pit cells were laid in object XY, which is constant along a
  tall wall, so the ring's and the neck's walls carried vertical blocky dashes. In class mode the cells are laid in the
  wall's own plane now - the arc length ALONG the wall (the generator's `shuriken_wall_s` point attribute) and the
  height - through one Mix whose factor is 0 on every other form (proven a bitwise no-op again: 13.5).
- **The head hull** was not mirror-symmetric, overshot the tip by 0.86 mm and came from simplifying a vertex hull. It
  is built from SUPPORTING LINES now (the blade's base edge, three tangents to the leaf, and the tip plane x = 140),
  emitted as +-y pairs: exactly symmetric, outside the outline everywhere by at most ~0.13 mm, and stopping at the
  point. 26 vertices, 10,356 mm3.
- **The grip hull** follows the wound-down ends instead of running a 21 mm collar prism to the end: **49,961 mm3**
  against 53,981, same 32 vertices. Two hulls total 60,316 mm3 (was 64,337); one hull would be 75,778, three 47,193.
  Unreal's hull-derived centre of mass is x = -30.41 mm, so the **COM offset is (+3.04, 0, 0) cm** and the physics
  override **0.1619 kg**.
- **The hidden tang** is counted as the study's 16 x 5 mm bar (3.10 used the rear neck's chamfered octagon, 79.28 mm2),
  so the finished steel is **149.04 g** (148.51 before). The un-ground gate figure is unchanged (it has no chamfers).
- **Four UV islands were mirrored** (the ring's two wall strips, the two cut ends, two rear-neck chamfers) and the
  code comments' handedness reasoning was wrong. Every island is unmirrored now: **0 mirrored triangles on all three
  LODs** (`symmetry.uv_mirrored_islands`).
- **The "wrong pivot" figure** in section 2 was not what Blender's Origin to Center of Mass (Volume) returns. The
  report measures that operator's own definition on the mesh now: `measured.centre_of_volume_x_mm` = **-35.85 mm**
  (the analytic-shell figure it used to quote is -35.38 mm; both are 'do not use this operator', not the pivot).
- **The Unreal harness' triple save.** `UnrealCheck6/pass1_import.py` imported with `save=True`, then `apply_sidecar`
  saved, then it saved again - three writes of a new package within milliseconds, which intermittently raced Unreal's
  uncontrolled-changelist scan and put a `LogPackageName` warning on a clean asset. It imports with `save=False` now
  and lets `apply_sidecar` perform the only save. 21 passes, 0 warning or error lines.

### 13.4 Findings not acted on, and why

- **"The study basis double-counts the rear neck's end inside the ring" - it does not.**
  `plain_calc/kunai_plain_mass_check.py` builds a plan field as the MAXIMUM of the parts, so the overlap contributes
  its 5 mm once, and the per-part breakdown claims the ring first: tang rectangle 8,800.0 mm3 - overlap 104.6 mm3 =
  8,695.4 mm3, exactly the reported tang, and ring + tang + blade = 19,492.6 mm3 = the field's own total. The script
  records that check now (`ring_tang_overlap`). The mass target stays 153.02 g and the gate error -1.13 g.
- **Texel density** (13.2 px/mm on the head, the pack's floor): the 146.5 mm head island laid straight along u caps a
  2048 map at 13.8 px/mm. Splitting it would buy ~1.5 px/mm and cost a seam across the blade. Accepted.
- **The front neck's 0.45 mm chamfer** against the study's 0.5-1.0 mm round: it is the stars' non-cutting treatment and
  the knife grind runs out into it. Kept for pack consistency, recorded as a deviation.
- **Sliver triangles along the 0.15 mm knife land** (LOD1's minimum angle 0.26 deg): they follow from the land design
  and nothing is degenerate. The wrap adds none: LOD0's minimum edge is 0.15 mm (the land itself), its minimum face
  0.039 mm2, its minimum angle 0.78 deg and 12 triangles under 1 deg - the same as 3.10.0's.
- **The FBX exporter's quad diagonals** differ from Blender's own triangulation (folds at most 0.4 deg). Triangulating
  before the bake would change every form's maps for no visible gain.
- **The physics override and the COM offset** are still applied by hand: neither the FBX nor the sockets sidecar can
  carry them, and `Scripts/pipeline` was out of scope for a non-bug change. They are in section 2, in the known gaps,
  and they belong in the Fab listing.
- **The hero pose and the blade's straight-edged outline** are user decisions (section 11). Fixing the neck removed the
  artifact that made the end-on hero look wrong; a 3/4 or side beauty shot for the listing is still worth a decision.
- **The kunai rests on its 20 mm grip**, so the 5 mm blade hovers ~7.5 mm above the floor in the gallery, as a real one
  does until it tips onto its point. Tilting the gallery pose would move the diamond faces' mirror direction, and the
  hero coat has 0.02 of headroom against the pack anchor; not taken.

### 13.5 Gates re-run on the fix

| Gate | Result |
|---|---|
| `build_pack.py`, all seven forms, `--frozen-maps post_hooked_cross/textures` (329 s) | exit 0, every form passed |
| Kunai's own gates (knife shading, outline mass, qa_check, LOD bands, UV consistency, textures, render gates, franchise names, lettering band + blank mask, two slots every LOD, no collapsed UV0 faces) | all pass |
| New render gate `hero_coat_dark` / `top_coat_dark` on all seven forms | pass (kunai 0.0088 in the hero and 0.000 in the top view; the six frozen forms 0.000 in both) |
| Pack consistency (coat against PACK_COAT_ANCHOR, backdrop, anchor drift) | pass, no drift |
| Frozen-forms regression against `post_hooked_cross` (geometry, hulls, sockets, UVs, corner normals, maps, FBX content, sidecars, report figures, material export scalars) | **identical for all six** (`regression/regression_kunai_fix_frozen.json`) |
| M_Shuriken_Master 3.10.1 (class mode + the wall cell frame) against 3.9.1, CPU bake, every channel | **bitwise identical on all six frozen forms** (`WorkFiles/kunai/plain_build/material_noop_check_3101.json`) |
| Unreal 5.8.2, fresh path `/Game/ShurikenCheck8/KunaiFix6`, 21 passes each in its own process, pass 2 re-reads what pass 1 saved | **all seven VERIFIED**, 0 warning/error lines in all 21 |
| Kunai in Unreal | 2,182 / 696 / 366 triangles, delta 0 against the FBX and the blend; 2 convex hulls; 4 sockets at scale 1; bounds 28.0 x 3.6 x 2.0 cm; screen sizes 1.0 / 0.28 / 0.098; UV1 generated from UV0 with **0 overlapping pixels at 1024 and 2048 on every LOD**; 2 sections per LOD, steel in u 0..1 and wrap in u 1..2; the lettering band's map within half a float16 step on every LOD |
| Texture flags, all 26 maps, import then verify in a second fresh process | pass, including the lettering mask's **mips** |
| Sheets and the lettering proof regenerated (`postbuild_sheets.sh`) | `modern_line_sheet.png`, `style_comparison.png`, `lettering_test_sheet.png` |
| New baseline `regression/post_kunai_plain` (seven forms) and its self-check | identical |

**Shipped bytes:** `SM_Kunai_Plain.fbx` SHA-256 `ebb6612b58e04c4c1724be1cdfaf86e2048e4a83634792308a04e31881cd3f95`,
sidecar `589bc324...`. Backup: `Backups/Shuriken_after_kunai_plain_2026-09-19/`.

### 13.6 Numbers that moved

| | 3.10.0 | 3.10.1 |
|---|---|---|
| LOD triangles | 1,256 / 600 / 238 | **2,182 / 696 / 366** |
| Two-sided LOD deviation | 0.55 / 1.48 mm | **0.63 / 1.18 mm** |
| Finished steel / assembled | 148.51 / 164.55 g | **149.04 / 161.93 g** (tape 2.63 g, core 10.26 g) |
| Pivot (mass-weighted centre) | x = -21.06 mm | **x = -20.52 mm** |
| Physics override / COM offset | 0.1646 kg / +3.06 cm | **0.1619 kg / +3.04 cm** |
| Hull volumes (head + grip) | 10,356 + 53,981 mm3 | **10,356 + 49,961 mm3** |
| Unreal bounds | 28.0 x 3.6 x 2.12 cm | **28.0 x 3.6 x 2.0 cm** (no collars) |
| Band rectangle (Blender UV0) | u 1.015625-1.718750, v 0.6527-0.7698 | **u 1.132813-1.835938, v 0.2638-0.3810** |
| Hero object fraction below 0.05 | 0.021 | **0.0066** |

The assembled mass is 2.9 g under the study's plain range (164.8-170.0 g) because the tape is modelled as it is wound:
0.5 mm of cotton, doubled over the 1 mm overlap, where the study's arithmetic took its "1 mm tape" as a single layer
(4.3 g of tape against the wound model's 2.6 g). The mass GATE is the un-ground steel and is unaffected (-1.13 g of
153.02, tolerance 2 g). A core at the study's upper density (0.8 g/cm3 instead of 0.7) would add ~1.5 g.

---

## 14. Blade-section rework, option C (library 3.11.0, 2026-09-27)

The user picked **option C** of `WorkFiles/kunai/blade_section/options/OPTIONS.md` (a full diamond at forged-replica thickness) and the **knife-specific hero coat rule**, and made the 3/4 diagonal the kunai's main picture. Where a number in sections 1-13 differs from this section, this section wins. The change log of every live write is `WorkFiles/kunai/blade_section/LIVE_CHANGES.md`.

### 14.1 The section

| | 3.10.1 | 3.11 (option C) |
|---|---|---|
| Ridge | 5.0 mm to x 35, then linear to 1.6 mm at x 135 | 5.0 mm (the neck stock) to x 5, rising to **7.0 mm** at x 24.42, held to x 35, then linear to 1.6 mm at x 135 |
| Un-ground edge `EDGE_T` | 1.5 mm | **0.3 mm** (the faces run into the 35° grind's 0.15 mm land) |
| Max blade thickness | 5.0 mm | 7.0 mm |
| Grind plan width, plunge / x 35 / x 90 / x 130 | 1.35 / 1.12 / 1.10 / 1.06 mm | 0.176 / 0.146 / 0.149 / 0.234 mm |
| Apex (grind reaches the ridge) | x 135.2 | x 135.2 |
| LOD base stations (plunge -> kite corner) | LOD0 3, LOD1 1, LOD2 1 | LOD0 3, **LOD1 3**, **LOD2 2** (the plunge station and x 24.42, the ramp's end: `KunaiLodSpec.blade_base_fractions`) |

`kunai_spec.py` holds it as constants (`RIDGE_BASE` 7.0, `RIDGE_RAMP` (5.0, 24.42), `EDGE_T` 0.3; the old section is kept as `SECTION_3_10_1`); `kunai.py`'s head hull samples the ridge at the ramp's knots. The report's `blade_section` block has the numbers.

**Face slope at the reference photo's stations** (measured on the built LOD0 mesh, true sections: `WorkFiles/kunai/blade_section/final/face_slope_vs_photo.json`):

| x (mm) | photo | 3.10.1 | 3.11 | 3.11 / photo |
|---|---|---|---|---|
| 13.4 (rear) | 0.325 | 0.148 | 0.236 | 0.72 |
| 26.7 (rear) | 0.237 | 0.112 | 0.214 | 0.90 |
| 39.4 | 0.175 | 0.096 | 0.186 | 1.06 |
| 56.7 | 0.185 | 0.092 | 0.184 | 0.99 |
| 74.1 | 0.215 | 0.088 | 0.186 | 0.87 |
| 91.4 | 0.217 | 0.084 | 0.193 | 0.89 |
| 108.7 | 0.228 | 0.079 | 0.216 | 0.95 |
| **front median** | **0.215** | 0.088 (0.41x) | **0.186 (0.87x)** | |

Face angle mid-blade 10.43° against the photo's 10.5°. The built mesh equals option C's prototype at every station (difference 0.0000).

### 14.2 Mass, balance, collision, LODs

| | 3.10.1 | 3.11 |
|---|---|---|
| Mass-gate target (study basis re-run with the section, `WorkFiles/kunai/plain_calc`) | 153.02 g (19,492.6 mm³) | **154.06 g** (19,625.3 mm³); the old figures kept in `kunai_plain_mass_check_3_10_1_section.json` |
| Steel, un-ground (gated) | 151.89 g | **153.34 g** (error -0.72 g, tolerance ±2) |
| Steel, finished | 149.04 g | 151.96 g |
| Assembled / physics override | 161.93 g / 0.1619 kg | **164.85 g / 0.1648 kg** (study basis with this section: 167.4-172.6 g; the modelled wound tape is lighter than the study's, section 13) |
| Pivot (mass centre, design x) | -20.52 mm | **-19.59 mm** |
| Head hull UCX_00 | 10,356 mm³, 26 v | **10,739 mm³, 30 v**; grip hull 49,961 mm³, 32 v; two hulls 60,699 mm³ (one hull 74,922) |
| Unreal COM offset | +3.04 cm | **+3.10 cm** |
| LOD triangles (bands 1,000-2,600 / 400-900 / 150-400) | 2182 / 696 / 366 | **2182 / 736 / 382** |
| Two-sided LOD deviation (set by the grip) | 0.63 / 1.18 mm | 0.63 / 1.18 mm |
| LOD ridge vs LOD0, worst | LOD2 -0.15 mm (tip) | LOD1 +0.0004 mm; LOD2 -0.15 mm at the tip (the prototype's -0.63 mm at x 25 is gone; the ramp is now at most +0.07 mm proud on LOD2 at x 12-15) |

All geometry gates pass: qa_check (62 checks), knife shading (0.10 / 0.19 / 0.27°), outline mass, LOD bands, UV consistency (0 overlaps, 0 collapsed UV faces, 0 mirrored islands on every LOD), textures, franchise names (105 names), two material slots on every LOD, lettering band + blank mask. **The lettering band's rectangle did not move** (UV0 u 1.1328125-1.8359375, v 0.26382741-0.38101491); `References/Kunai/LETTERING_HOWTO.md` is unchanged.

### 14.3 The knife coat rule (render.py, class knife only)

The hero rule up to 3.10.1 averaged every coat pixel (|N.z| >= 0.95) of the knife against `PACK_COAT_ANCHOR`, the anchor stars' flat plates. A diamond face tilted 5-13° mirrors a different part of the rig than a flat plate, so in the 3/4 pose every section failed it - including 3.10.1's - while the uniform reference coat on the same mesh read the same darkness (the rig and the geometry, not the finish). 3.11 replaces `hero_plate` / `top_plate` and `pack_consistency`'s all-coat check **for a knife only** (`knife_coat_rule` on the render outline; the six other forms carry none, and their staged rebuild is content-identical):

1. **Orientation-matched anchor:** the coat pixels within 1.8° of flat (|N.z| >= 0.9995: the ring flats, the neck plateau, the rear neck; at least 2,000 px) against `PACK_COAT_ANCHOR` p50 and mean, tolerance 0.05, in the hero and the top view.
2. **Finish transfer:** the frame is rendered again with the pack's nominal coat as a uniform material; on the tilted faces, (baked - reference) must equal the flat faces' (baked - reference) within 0.05 on p50 and mean.
3. **The hole gate stays:** at most 2 % of the coat below 0.03.

It is a **stricter like-for-like rule, not a relaxation**: every comparison is flat against flat at the same 0.05; part 2 is a new check (an averaged coat could hide a mis-baked blade island); and part 1 would have failed 3.10.1's end-on hero, whose neck plateau mirrored the dark grip (flat coat 0.48 / 0.41, the review's "black slot"), which the averaged rule passed.

| Built kunai | hero (3/4) | top |
|---|---|---|
| Flat coat p50 / mean (anchor 0.560 / 0.550 hero, 0.430 / 0.424 top) | 0.565 / 0.564 (6,937 px; +0.005 / +0.013) | 0.429 / 0.425 (13,014 px; -0.001 / +0.001) |
| Finish transfer p50 / mean | 0.000 / +0.003 | -0.004 / +0.003 |
| Coat below 0.03 | 0.0012 | 0.0000 |
| Tilted faces p50; the two faces either side of the ridge | 0.432; 0.29 / 0.54 | 0.366 |
| All coat (the old rule, information) | 0.475 / 0.450 | 0.373 / 0.370 |

`pack_consistency` passes (the knife under `knife_coat_rule`; hero backdrop: no point off, smallest headroom 0.014 at `bl`).

### 14.4 The hero: the 3/4 diagonal

`kunai_plain_persp.png` is now the 3/4 diagonal (the pose of `kunai_plain_3q.png`, the tip to the lower right) through the build's own hero path; **`kunai_plain_3q.png` is a byte copy of it**, and the line sheet's Kunai panel shows it. Chosen by measurement (`WorkFiles/kunai/blade_section/build/hero_yaw_probe_summary.json`, 20 probe shots at 220 samples):

- With the pack rig alone, every yaw from 20 to 70 left **both** diamond faces in the gap between the key (el 32°) and the overhead panel (el 52°+): tilted p50 0.23-0.29, the two faces 0.00-0.07 apart. The blade read as one dark slab where the photo has one lit and one dark facet.
- A **glossy-only blade key** (`render.hero_blade_key`, kunai only: 0.16 x 0.13 m at 0.62 m, elevation 47° / azimuth 169°, the pack key's radiance, diffuse and shadow rays off, scaled with the hero lamps) sits where the camera-facing face mirrors. The flat coat still mirrors the pack key (gated above) and the floor never mirrors it (backdrop gate unchanged).
- **Yaw 35** with it: faces 0.29 / 0.54, all hero gates pass with margin (near facets 1.3 % dark, max 6 %). Yaw 40 fails the facet gate: the shoulder's run-out facet, steeper with the 0.3 mm edge, mirrors the dark floor (8.5 % of the near facets below 0.05). Yaw 37.5 passes it by 0.001, so 35 is the nearest robust yaw.

### 14.5 The polished edge band

With a 0.3 mm edge the grind is a 0.15-0.23 mm facet, so the material's polished band (clipped to the knife facet by the class mask) is the whole facet, about 2-3 texels at 13.4 px/mm. **It does not alias** (`WorkFiles/kunai/blade_section/build/edge_band_probe.py`, bilinear lookups of the shipped maps at 6,160 points on LOD0's knife facets). Per-mm roughness along the edge is 0.224-0.235 (std 0.004; polish 0.22, satin 0.47), BC 0.649-0.669 (std 0.006), with no periodic component (spectrum peak/mean 2.5). 3.10.1's two-finish band varied more (std 0.022). The hero's edge reads as one continuous thin line. `material.py` is unchanged, so no M_Shuriken_Master no-op proof was needed.

### 14.6 Regression: the six other forms

The build ran staged (`WorkFiles/kunai/blade_section/build/stage1`, all seven forms, `--frozen-maps pre_blade_section/frozen_maps_six`, exit 0). Only the kunai and the pack-level files were promoted (`build/promote.py`).

- `compare_frozen` passes on the staged six: blend, FBX content, sidecar, report figures and textures are identical to `pre_blade_section`, so the 3.11 code is a no-op for them.
- The same check passes on the live six: `WorkFiles/shuriken/regression/regression_blade_section_frozen.json`.
- Every live file of the six (FBX, sidecar, three maps, five renders, report) is **byte-identical**, 66 of 66, to `prep/frozen_six_sha256.json` and to the snapshot.

### 14.7 Unreal verification: VERIFIED

> **Re-run for 3.11.1 (review round 1, section 14.9).** The 3.11.1 rebuild re-exported the kunai (geometry identical, new FBX bytes `a2d464722c30ef440e166e1032965bb2b828b9f15794d79ca96d4cf2eb019d7b`, sidecar unchanged `bf6990550357...`) and re-baked its maps, so the check below was repeated in a fresh content path, `/Game/ShurikenCheck9/KunaiBladeC2`, evidence in `WorkFiles/shuriken/UnrealCheck6/blade_section_c2/` (23 guarded launches, all free). Every gate passed again with the same figures; the kunai's `engine_check` is `verified` on the new bytes and `pack_report.engine_checks_verified` is true. The text below is the first run (3.11.0, KunaiBladeC1).

Unreal 5.8 (`5.8.3-58210709`), fresh content path `/Game/ShurikenCheck9/KunaiBladeC1`, run by `WorkFiles/shuriken/UnrealCheck6/run_all_kunai_blade_section.sh`. Each of the 21 passes (seven forms x import / fresh-process re-read / export) and both texture passes ran in its own `UnrealEditor-Cmd` process. The one-Unreal-at-a-time guard ran before every launch (`blade_section_c1/guard.log`: 23 checks, all free). Evidence is in `WorkFiles/shuriken/UnrealCheck6/blade_section_c1/`; the earlier run's files, which the six frozen reports cite, were not overwritten.

- **Bytes.** Unreal imported FBX `af148d55bd2cfd2469c0825a54c51b4a3297d52bed69e7ec0719efcfdec15799` and sidecar `bf6990550357363ddf674ece92dbf1d1114ba70e1798f19015a0e8b3c5a53e5e`. These equal the report's `export_sha256` and the files on disk. All 40 imported files (7 FBX, 7 sidecars, 26 maps) hash the same before and after the run (`input_sha256_{before,after}.json`), and each map's import hash equals its disk hash.
- **Kunai gates, all pass.**
  - LOD triangles 2,182 / 736 / 382, delta 0 against the report and the Blender re-import.
  - Exactly 2 convex hulls. Each matches its shipped hull within 1e-6 cm, and their union contains LOD0 (0.0 cm outside).
  - 4 sockets (Grip -3.4413, Ring -10.4413, Tip 15.9587, Trail -12.0413 cm) at scale 1.
  - Bounds 28.0 x 3.6 x 2.0 cm. Screen sizes 1.0 / 0.28 / 0.098.
  - UV1 is generated from UV0 on every LOD: inside 0..1 with 0 overlapping pixels at 1024 and at 2048. The round-trip positions and the UV0-keyed positions match within 1e-6 cm.
  - 2 sections per LOD: steel in u 0..1, wrap in u 1..2.
  - Gate 13 on the unchanged lettering rectangle. The map error is at most 0.45 / 0.20 texels (tolerance 0.6), the band is fully covered and sits on +Z on every LOD.
  - 0 Warning/Error lines in any of the kunai's logs.
- **Textures, all pass.** 26 maps imported with their flags, then read back in a second fresh process: BC is sRGB/Default; ORM is linear/Masks; N is Normalmap with Flip Green off. The lettering mask is Grayscale, Clamp, Stretch to power of two, and From Texture Group (it has mips). The wrap maps use Wrap addressing. Both logs have 0 Warning/Error lines.
- **The six other forms verify identically.** Their pass-2 figures and round trip equal the previous run's exactly, and each verdict equals the `engine_check` already in its report. Those reports were checked but **not rewritten**, so they are still byte-identical.
- `attach_engine_check.py` ran with the kunai as the only report it could write (`UC6_ATTACH_WRITE=kunai_plain`). The kunai's `engine_check` is `verified`, and `pack_report.engine_checks_verified` is true.

### 14.8 Still to do

- The materials job's Recolour files (`T_Kunai_Wrap_Detail16.png`, `recolour_maps.json`, `recolour_constants.json`) are bound to the old blend and wrap BC.
  - Regenerate them with `Scripts/unreal/materials/maps/`.
  - Then rebuild the kunai in `/Game/NinjaPack`.

### 14.9 Review round 1 (library 3.11.1, 2026-09-27)

An independent review of the shipped 3.11.0 kunai raised two major findings and ten minors. Each was reproduced first; the evidence is in `WorkFiles/kunai/blade_section/fix_r1/`.

**Fixed.**

- **The point read blunt (major).** The polished edge stopped about 8 mm short of the tip. The last few mm were a dull wedge ending in a detached bright speck, and the hero showed a small jog in the near edge.
  - Reproduced: on the 35 deg facets the baked roughness was 0.22 along the leaf but 0.47-0.48 at x 131-137.5 (`tip_probe_live_before.json`).
  - Root cause: the material's run-out taper (3.9.1) measures how "full" the knife is from the local grind width, scaled between the chamfer's width (0.45 mm) and the knife's. The 3.11 knife grind (0.15-0.23 mm) is narrower than the chamfer, so that scale runs backwards. On the leaf it still gives a full knife. Near and past the apex, where the grind widens to the whole point, the width passed 0.45 mm and read as chamfer, which switched the polished band off.
  - Fix, in the material and not the section: `material.RUNOUT_CONTOUR_PROP`, which only the kunai sets. Past the full knife's start, the band is now full knife whatever the width says. On the run-out itself nothing changes. On the six other forms the property is absent, and a CPU bake shows the change is bitwise a no-op for their BC, roughness, metallic and normal (`material_noop_check_3_11_1.json`).
  - Result: roughness is 0.22 through x 131-138. The top view's edge highlight now runs cleanly into the point with no detached speck, and the hero's near-edge jog is gone (`tip_top_before_after.png`, `tip_hero_before_after.png`). The hero's near-facet p50 went from 0.449 to 0.497. The coat numbers under the knife coat rule are unchanged.
- **The neck close-up still showed 3.10.1 (major).** `kunai_plain_neck_closeup.png` and `kunai_plain_grip_closeup.png` were the Sep 19 renders. They were re-rendered from the 3.11.1 blend with `WorkFiles/kunai/blade_section/final/closeups_3_11.py`, a port of the script that made them (same rig, cameras and samples). Run on the pre-rework blend and maps, the port reproduces the old files to within 0.001, so the new ones differ only in the section.
- **Frayed lodgrind patch (minor).** This was the same tip-polish fault. The abrupt dark wedge is gone and the band runs on (`lodgrind_before_after.png`). The band's inner edge still shows texel steps in this 4x macro, as it does along the whole leaf.

**Kept, with reasons.** None of these needs a geometry change to be correct, and the section stays option C as approved:

- **Steeper plunge / black run-out triangle.** This is a real ground-blade plunge (37.4 deg). The hero's yaw 35 keeps the near-dark facets at 1.3%.
- **Kite-corner panel.** The panel between x 24.42 and 35 sits up to 0.152 mm under the analytic diamond, with a 3.21 deg crease. It is not visible in any render, and both masses are inside the gate. A 4th base station (about +16 triangles) remains available.
- **Ridge knee.** The mesh ramps from the plunge station (x 3.317) and not from x 5, so it is up to 0.146 mm thicker than `kunai_spec.ridge_blade` at x 5. It is never thinner. In the mesh, the ramp starts at the plunge station.
- **Assembled mass.** 164.85 g is 2.55 g under the re-run study basis (167.4-172.6 g), because the tape is modelled as wound (section 13). No shipped text says it is inside the study range. The "now inside the study range" line in `options/OPTIONS.md` was written against the old 164.8-170.0 range.
- **No bright edge bevel on the kunai hero.** This is physically right for a 0.15 mm land and is a style note only.
- **Unreal 5.8.3.** For information: the engine is now 5.8.3.

**Rebuild and gates.**

- The full seven-form build ran staged in `build/stage2/` (build_pack.py, exactly as before) and exited 0 after 660 s. The pack passed.
- The kunai passed every gate: 62 qa checks, knife shading, mass, LOD bands, UV, textures, render gates including the knife coat rule in the hero and top view, franchise names, lettering, and two material slots.
- The kunai's geometry is identical to 3.11.0: positions, loops, corner normals, UVs and every float attribute on LOD0-2 (`geometry_same_live_vs_stage2.json`). Mass, pivot, hulls, LODs and face slope are therefore unchanged.
- compare_frozen passed on the staged six and on the live six. All 66 live files of the six (FBX, sidecar, maps, renders, report) are byte-identical to `prep/frozen_six_sha256.json` and to the pre_blade_section snapshot, both before and after the promotion (`WorkFiles/shuriken/regression/regression_blade_section_fix_r1_frozen.json`).
- The Unreal check was repeated as described in 14.7 and verified.
- The line sheet and the style comparison were regenerated.

Section 14.8 (the Recolour files and the /Game/NinjaPack rebuild) is still to do. The wrap maps were re-baked again in this rebuild; they differ only by GPU bake noise.
