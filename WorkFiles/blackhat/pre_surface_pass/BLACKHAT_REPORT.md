# SM_BlackHat: build report (final pass)

**Date:** 2026-09-26. **Library:** props_lib blackhat **1.1.0**. **Build:** `Scripts/props/build_black_hat.py`, run
from scratch with no arguments (Blender 5.2.0 LTS, headless, `--factory-startup`, 85 s). It rebuilt
`Assets/BlackHat.blend`, `Exports/BlackHat/` and `Renders/BlackHat/`. Log: `WorkFiles/blackhat/build_full_3.log`.

## Status

- **Fidelity: FAILED the blind test.** Round 1 was 20 of 20 pairs picked correctly, all 20 confidently. The match
  loop stopped there. This pass fixed engineering only; it did **not** start a new fidelity round. That is your
  call (section 9).
- **Engineering:**
  - **Build gates: 25 of 25 pass.** They are in `WorkFiles/blackhat/blackhat_report.json` under `gates`, and
    include new gates for the recolour convention, roughness floors, the single hull, and tail tips in x and y.
  - **qa_check: 76 of 76 pass.** Round 1 had 78; one hull fewer means 2 fewer checks.
- **Unreal 5.8.3: VERIFIED, 20 of 20 gates** on the exact exported bytes:
  - each step ran in its own fresh process, with **0 warning or error lines**;
  - content path `/Game/PropsCheck/BlackHat_0926d` in the shuriken validation project;
  - summary in `WorkFiles/blackhat/UnrealCheck/verification_summary.json`.
- **Frozen assets unchanged, every line of every list:**
  - shuriken **78 of 78** (live, and 78 of 78 against the snapshot's own copies);
  - smoke bomb **30 of 30**;
  - paper bomb **6 of 6**;
  - proof in `WorkFiles/blackhat/regression/post_black_hat/compare_result.json`.

**Bytes:**
- FBX `fa35264c5f075883e2e2bc0d819d8494f3d2e97a66a9a3ae59cb6a1b21738848`
- sidecar `993045f3…ad656c1`
- blend `9652cfab…a0e7c6`

---

## 1. Headwear decisions (the orchestrator's defaults; change any of these)

| Decision | What was built |
|---|---|
| **HEAD socket** | An Empty (`SOCKET_SM_BlackHat_LOD0_HEAD`), applied in Unreal from the sidecar. It sits on the axis at **z = 134.83 mm**, rotation 0: +Z points up out of the crown, +X forward. This is where the top of a 57 cm head (a sphere of r = 90.72 mm) touches the **inner** cone (half-angle 64°), 10.22 mm below the inner apex (z 145.05 mm). Unreal reads it at (0, 0, 13.4833) cm, scale 1. |
| Orientation | +X is forward. The knot is on the wearer's **left (+Y)**. |
| Pivot | On the axis at the bottom of the rim tube (z = 0). The tails hang 92 mm below it. |
| Headband ring / lining / chin cord | **None.** The reference never shows the underside, so it is the plain inner woven skin. Near the apex it now fades into a plain seat disc. **A head ring is an option** if you want one; buyers should be told the underside is plain. |
| Band and tails | Same static mesh, own slot `M_BlackHat_Cloth`, hanging in the reference pose. A cloth-sim or skeletal tail is a later option. |
| **Collision (new)** | **One** convex hull round the hat's body. The hanging tails have **no collision**, so a limp tail on a worn hat cannot block or snag the wearer. |
| Size | D = 600 mm, mass 300 g (both DESIGNED). |

## 2. What this pass changed (issue by issue)

| Issue (severity) | Decision | What was done / why not |
|---|---|---|
| Recolour tint semantics (minor) + recolour ergonomics (major) + detail range (minor) | **Applied** | The Tint is now the part's **mean colour**. `BaseColor = saturate(Tint x (DetailBias + DetailScale x Detail))`. Detail is **full range at both ends** (codes 0-255, 256 levels, both parts), quantised once from float. The defaults are in the sidecar (section 3). `mean(Bias + Scale x Detail)` = 1.000004 (straw) and 0.999992 (cloth), so a buyer who types a colour gets that colour as the part's average and at the far mips. |
| BC-vs-recolour equality under BC1 (minor) | **Applied** (documented) | The sidecar, the material spec and this report now say that equality holds at the **source / 8-bit** level. In Unreal, BC is BC1 and Detail is uncompressed G8, so the two paths differ by BC1 block error. |
| Second tint for the warmer rim and lashings (optional) | **Declined** | It needs a mask channel (ORM.B is free). But `lerp(TintA, TintB, mask) x Detail` is a product of two filtered terms, so the per-mip identity breaks along every mask border. The rim's warmth difference is within REFERENCE_SPEC's ±0.03. |
| Straw near-mirror roughness (part of the rim blocker) | **Applied** | Straw roughness is clipped to **≥ 0.25** (round 1 reached 0.05). Floors on the painted parts: **ribs 0.58**, **rim tube and lashings 0.52**, **crown cap 0.58**. |
| Specular levels | **Applied** | Straw Specular = **0.8 x ORM.A**, so F0 is at most 0.064 on the polished strand tops and about 0.04 on a typical texel (round 1: 1.0, F0 0.08). Straw 0.6 was tried first: it dropped the reference view's object p50 23 % below the reference (gate F6), so 0.8 was kept. |
| Cloth sheen (part of the cloth blocker) | **Applied** | Cloth roughness is **0.85-0.95**. Specular is **0.25-0.35** (mask 0.50-0.70 x 0.5); round 1 was mask 0.35-0.90 x 1.0. |
| Weave moire and shimmer at distance (part of the weave blocker) | **Applied (engineering part)** | Each ORM names its part's `_N` as **Composite Texture**, mode **CTM_NormalRoughnessToGreen**. That is Unreal's per-mip Toksvig: roughness widens by the normal map's variance at each mip, so distant weave goes rough instead of ringing. Unreal step `bhu_tex_composite.py` sets it; pass 2 re-reads it in a fresh process (gate 19). It is also recorded in the sidecar (`orm_texture_settings`) for buyers. |
| Weave look: record-groove rings, soft streaks, missing brick seams and flecks | **Not done: fidelity** | The rings are the authored course dome (a 0.30 mm height bump every 9.3 mm course) seen at grazing angles, not a UV stretch: the UVs are the cone's development, with zero stretch. Re-authoring the strands (4-6 texel pitch, brick runs, flecks) is a fidelity round. |
| Rib sparkle and crawl (major) | **Applied (engineering part)** | Rib roughness went 0.30 → 0.58-0.83, so a highlight spreads along the rod instead of breaking into dashes. The lighter worn core in BC and a twist in geometry are fidelity work and **not done**. |
| Crown cap metallic look (major) | **Applied (material)** | Cap roughness is 0.58+ and its mask is 0.4-0.8 x 0.8. The flat lipped lid geometry is fidelity work and **not done**. |
| Collision fit (minor) | **Applied** | See section 5. Round 1's hulls stood 15 mm above the crown and 30 mm below the tail tips, with a tail box. Now one hull, **1.0 mm** above the crown and below the rim, no tail box. |
| Triangle budget (minor) | **Justified, kept** | See section 4. The breakdown is also written into the sidecar (`triangle_budget`). |
| Mip count not measured (minor) | **Reported as INFERRED** | See section 6. |
| LOD tail pops (minor) | **Applied (partly)** | Coarse LODs now subdivide the tail outline wherever the centre line turns more than 15° between samples (the bend over the rim roll and the fall). The shaded pop went from 0.0039 / 0.0072 to **0.0030 / 0.0057** (mean stored difference at the switch). LOD2's tear is still cut straight: its teeth are 1-3 mm, sub-pixel at LOD2's 2.54 m switch. |
| Tail placement (minor) | **Applied (a real bug)** | Round 1 aimed the tail's **centre line** at the measured tip pixel. The torn point sits on the outer edge, half a width to image-right, which is exactly the measurer's 15-20 px. Now the **pointed tip** is solved onto the pixel, and gate F8 checks **x and y** on the render. Tip A lands at (591, 532) vs (592, 533); tip B at (638, 519) vs (643, 520). Tolerance is 6 px. The tails' width on the cone is fidelity and unchanged. |
| Underside (minor) | **Applied** | The inner weave fades into a plain seat disc at the apex (rho < 0.13); the swirl is gone. The underside shot is re-lit (lamp scale 0.45 vs 1.2); with the cloth's satin specular fixed, the tails read dark. |
| Product-line fit (major) | **Applied (presentation)** | New line sheet in the house framing: a 3/4 view at the hero angle on the left, a top view at the right, the caption at the smoke bomb's line pitch, and the smoke bomb sheet's own backdrop gradient composited behind (read only). The hat is fully in frame. The wire render was a real bug: it reused the camera the underside shot had moved below the rim. It is now a 3/4 view from 40° above, showing ribs, band and rim topology. The top view is lit at 0.5 (was 1.2). |
| Spec camera shift signs (measurer) | **Applied** | REFERENCE_SPEC 1 now carries an erratum: `+0.0030 / −0.0113`, with the aim point as the authority. The build was never affected: `blackhat_camera.py` derives its shift from the aim point, and the render's rim bottom and crown land within 0.02 px. |
| Rim roll / lashings rebuild, band / knot / tails as cloth, crown lid, wear in strand space, torn-end shapes (the craft blockers and majors) | **Not done: fidelity** | These are model and texture rebuilds, a new match round, which the brief reserves for your decision. They are listed in section 9. |

## 3. Textures, recolour and mip safety

Two sets at **2048**: `T_BlackHat_Straw_{BC,ORM,N,Detail}` and `T_BlackHat_Cloth_{BC,ORM,N,Detail}`. Straw is
21.7 px/cm, cloth 62.2 px/cm. The cloth's UV0 is in the second tile (U + 1); keep the textures on Wrap. Every
texel is painted from its own part's coordinates; nothing reads the reference.

**Recolour, per part** (the sidecar's `materials` block holds all of it):

| | Straw | Cloth |
|---|---|---|
| **Tint** (the part's MEAN colour, linear) | (0.042821, 0.039103, 0.038023) | (0.035018, 0.034089, 0.034192) |
| Tint (sRGB) | (0.2289, 0.2183, 0.2152) | (0.2060, 0.2031, 0.2035) |
| **DetailBias / DetailScale** | 0.122772 / 5.256401 | 0.133561 / 2.444596 |
| Detail codes used | 0-255, 256 levels (p1 / p50 / p99 = 27 / 96 / 212) | 0-255, 256 levels (60 / 156 / 236) |
| BC vs graph at defaults, max linear error (8-bit source) | 0.0017 | 0.0010 |
| Graph vs BC, mean over mips 0-8 | within **0.38 %** | within **0.82 %** |

- **Encoding.** Detail is `d = (albedo − a_lo) / (a_hi − a_lo)`, sRGB-encoded linear, imported sRGB ON. Unreal
  decodes before filtering, and the affine `Bias + Scale x d` commutes with the filter, so every mip is correct.
- **Specular mask.** It is linear in ORM.A.
- **Which parameter a buyer edits.** Edit **Tint**. For a light recolour whose flecks should not clip, lower
  DetailScale and raise DetailBias together, keeping `Bias + Scale x mean(d)` at 1.
- **BC1 caveat.** In Unreal the fixed-colour BC is BC1-compressed, so it differs from the recolour path by BC1
  block error. Equality holds at the 8-bit source only.

**Material:**
- Specular = 0.8 x ORM.A (straw), 0.5 x ORM.A (cloth);
- Roughness = ORM.G, with the Composite Texture = `_N`, NormalRoughnessToGreen;
- Metallic 0;
- N is DirectX, flip green OFF.

**Roughness as shipped:**
- straw min 0.251, p50 0.580;
- cloth 0.851-0.933.

ORM.R is the analytic cavities x a Cycles AO bake of LOD0 (256 samples).

## 4. LODs and triangles

| LOD | Triangles | Screen size | Switch | LOD0 → LODn p99 / 1 px at switch |
|---|---|---|---|---|
| 0 | **16,816** (straw 12,012 + cloth 4,804) | 1.0 | - | - |
| 1 | **6,290** | 0.695 | 0.89 m | 1.43 mm / 0.93 mm |
| 2 | **1,977** | 0.2432 | 2.54 m | 3.77 mm / 2.65 mm |

The bounds radius is 347.5 mm (it moved from 351.8 mm because the tails moved). The screen sizes follow the pack rule.

**Why LOD0 is 16.8k and not ~10k.** It is a 600 mm hat, the pack's largest prop, and its signature details are real
geometry:

| Part | LOD0 triangles |
|---|---|
| 26 lashings of three cords | 4,992 |
| rim tube | 2,880 |
| band | 2,800 |
| tails with walls | 1,572 |
| binding cord | 1,152 |
| cap | 1,088 |
| outer skin | 1,106 |
| ribs | 416 |
| knot | 432 |
| inner skin | 378 |

- **Where the budget could come down.** The reviewer is right that it sits in smooth tubes and rings. Moving
  triangles from the rim tube and lashing segments into the cap lip, knot folds and tail ends belongs with the
  fidelity rebuild of those parts; doing it now would only reshuffle geometry that is going to be remodelled.
- **What this pass added.** The tail change added 28 triangles to LOD0, 248 to LOD1 and 128 to LOD2.

## 5. Collision

**UCX_SM_BlackHat_LOD0_00**, one hull with **49 vertices** and 94 faces. It is the intersection of support planes,
each **1.0 mm** outside the body:
- straight down;
- straight up (the crown);
- 13 horizontal planes (the rim);
- 13 planes at the cone's normal elevation (64°);
- 2 greedy planes at the band and knot.

It contains the body of every LOD by construction; the worst body vertex is 1.0 mm inside.

**Fit, measured:**
- 1.0 mm above the crown and below the rim;
- 9.9 mm beyond the widest radius at the 13-gon's corners;
- mean 7.8 mm (max 13.5) proud of the points' exact convex hull.

Round 1 was mean 11.7 / max 27.8 mm, plus a 326 cm³ box round the tails.

**Why 49 vertices.** The cap is Chaos's own geometry-complexity threshold (`p.Chaos.ConvexParticlesWarningThreshold`
= 50; its check is off by default). A 20-azimuth hull would fit to a 4.7 mm mean, but needs 79 vertices.

**The hanging tails have no collision, by design.** That is 379 LOD0 vertices, down to z = −91.6 mm. Unreal's round trip:
- the hull's 49 vertices come back within 1.6e-6 cm;
- all 8,605 LOD0 body vertices are inside;
- the 379 tail vertices are excluded by the same rule the build uses.

## 6. Unreal verification (`/Game/PropsCheck/BlackHat_0926d`, bytes `fa35264c…`)

Each step ran in a fresh process, one commandlet at a time. The harness refuses to start if any UnrealEditor-Cmd is
running.

**Steps:**
1. Blender FBX count;
2. pass 1 import (legacy FBX, Import Mesh LODs ON) + sidecar (`Scripts/pipeline/ue_import_sockets.py`, unchanged);
3. props texture import (`ue_import_textures.py`, unchanged);
4. **new:** `bhu_tex_composite.py` (ORM composite = N);
5. fresh texture verify;
6. pass 2 reload + gates;
7. pass 3 Unreal FBX export;
8. Blender round trip;
9. UV1 overlap.

**VERIFIED 20 / 20:**
- **LODs:** 16,816 / 6,290 / 1,977, identical in Blender, in the FBX re-import and in Unreal. Positions round-trip
  exactly; no triangle was dropped.
- **Collision:** 1 hull, round trip within 1.6e-6 cm, and it contains the LOD0 body.
- **Socket:** HEAD at (0, 0, 13.4833) cm, scale 1, owned by the asset.
- **Screen sizes:** from the sidecar, with the bounds radius matching.
- **Lightmap:** UV1 generated, 0 overlap at 1024 and 2048 on every LOD.
- **Material slots:** 2.
- **Nanite:** off.
- **Texture flags:** all 8 persisted.
- **ORM:**
  - Composite = its `_N`, NormalRoughnessToGreen (gate 19, re-read in a fresh process);
  - alpha kept, with the source alpha equal to the shipped mask's range (straw 0.024-1.0, cloth 0.502-0.698).

**Gate-rule change.** Run `0926c` failed gate 9 only on the old rule "ORM alpha spread > 0.5", which the matte cloth
mask (0.50-0.70) no longer meets. The rule now compares against the shipped range. That run is archived in
`UnrealCheck/archive_0926c_gate9_alpha_rule/`; round 1's run `0926b` is in `archive_0926b/`.

**Mip count: INFERRED, not measured.** A `-nullrhi` commandlet builds no platform data: ListTextures reads 1x1 with
0 mips, and Texture2D has no mip-count accessor in 5.8. The 12-mip chain follows from:
- 2048² power-of-two sources;
- TMGS_FROM_TEXTURE_GROUP, with the World / WorldNormalMap groups on SimpleAverage;
- LOD bias 0 and max size 0;
- no streaming VT.

**Why it was not measured.** Measuring needs a render-capable process or a cook. Neither was run, because other
Unreal editors were open on this machine.

## 7. Renders (all from the baked maps; `Renders/BlackHat/`)

- **Reference view:** `blackhat_side_by_side.png` (reference | render); `blackhat_reference_view.png` (670 x 599,
  the spec camera, 512 spp); `blackhat_crops_3x.png`.
- **Gallery:**
  - `blackhat_hero.png` and `blackhat_raking.png`;
  - `blackhat_underside.png` (re-lit);
  - `blackhat_top.png`;
  - `blackhat_wire.png` (3/4 from above; was the underside);
  - `blackhat_lods.png` and `blackhat_lod_switch.png`;
  - **`blackhat_linesheet.png`** (house framing).

**Measured on the shipped render** (`blackhat_report.json`, `fidelity`):

| Measure | Result |
|---|---|
| Generator lines | −1.55 / −1.41 px (REFERENCE_SPEC 11 asks for 1 px; still 0.5 px over) |
| Rim bottom | −0.02 px |
| Crown | +0.01 px |
| x extent | exact |
| Mask IoU | 0.959 |
| Object luminance p10 / p50 / p90 | 0.0109 / 0.0205 / 0.0485 vs 0.0086 / 0.0242 / 0.0601 |
| Chroma | (0.343, 0.330, 0.327) vs (0.349, 0.328, 0.323) |
| Tail tips | A (−1, −1) px, B (−5, −1) px |

## 8. Blind-test history

| Round | Pairs | Picked correctly | Confident and correct | Outcome |
|---|---|---|---|---|
| 1 (2026-09-26) | 20, sides randomised, non-image PNG chunks stripped, no key on disk (`WorkFiles/blackhat/blind_r1/`) | **20 / 20** | 20 | **Failed decisively.** The loop stopped early, and no round 2 was run. |

**The judges' tells**, consistent across all 20 pairs:
- **Straw skin:** vinyl-record rings or smeared streaks where the reference has a plank weave.
- **Wear:** no pale scuffed patches, only soft dark blotches.
- **Rim:** a thick glossy tube.
- **Lashings:** neat smooth loops.
- **Ribs and band:** smooth dark rods.
- **Crown:** a soft dome instead of a flat capped lid.
- **Knot:** a rubbery blob.
- **Cloth:** flat vector-black, with blunt comb-like torn ends.
- **Overall:** a soft, plastic, clean look.

**What this pass removes from that list.** Only the glossy tube and the plastic sheen, partly, through the roughness
and specular fixes. The rest needs the fidelity rebuild.

## 9. Per-element fidelity (after this pass) and what still does not match

**Status key.** Every row is from the round-1 measurement unless it says otherwise.
- "Within tolerance" is against REFERENCE_SPEC.
- "Looks different" is the round-1 judgement. This pass did not re-judge by eye with a new blind round.

| Element | Within tolerance | Looks different | After this pass |
|---|---|---|---|
| Camera / frame | yes (spec erratum fixed) | no | Unchanged. |
| Cone silhouette / generator lines | no (−1.5 / −1.4 px vs 1 px) | yes | Unchanged: the far rim tube and lashings stand proud at the side tips. |
| Crown cap | no | yes | Matte now, no metal highlight. It is still a dome with no flat lid and no lip line. |
| Ribs | yes (count / place) | yes | Rougher, so there are no crawling dashes. They are still smooth dark rods, with no light twisted core. |
| Woven skin / weave | no | yes | There is a per-mip roughness fold in Unreal. The course bands still read as rings at grazing angles. There are no crisp strand lines, brick seams or flecks at the reference's contrast (40-60 %). |
| Rim (rolled tube, cord, groove) | no | yes | Less glossy. It is still a thick pipe with a trench at the side tips, and no visible light binding cord. |
| Lashings | yes (count / place) | yes | Unchanged: smooth, uniform, dark, bridging the trench like staples. |
| Band | yes (path / height) | yes | Matte now. It is still a thin strip that turns into a sausage roll at the knot. |
| Knot | no | yes | Unchanged: a smooth lump that bumps the top-right silhouette. |
| Tails: position | **yes now** (A −1 / −1 px, B −5 / −1 px) | partly | The torn points are on the measured pixels in x and y. |
| Tails: width / drape / cloth | no | yes | Matte now, no satin. They are still narrow and diagonal on the cone, about 1.9 mm thick, with no weave read. |
| Torn ends | no | yes | Unchanged: blunt, with hair-like spikes; B's notch is not the reference's split sliver. |
| Wear / worn patches | no | yes | Unchanged: a dark diagonal stripe plus soft mottling, with no bright scratched streaks. |
| Colour / tone | yes (p50 −15 %, chroma within 0.006) | no | Slightly darker than round 1 (−8 %) because the sheen is lower. One tint per part, so there is no warmer rim. |
| Underside / invented nothing | yes | no | Plain, with a seat disc at the apex. Nothing is invented: no chin cord, lining, decal or colour. |

**Honest summary.** The hat's shape, layout and engineering are right, and it recolours and imports cleanly. Its
surface and cloth do not yet look like the reference: the blind test found it every time. Closing that gap is a
new fidelity round built the way the object is built:
- the skin rolled over a core hoop, with a light binding cord;
- 2-ply crossed lashings;
- a flat lipped lid;
- the band as a folded twisted strip;
- a 3-4 layer knot;
- broad draped tails with hems and long ragged points;
- strand-space weave with brick runs and flecks, and strand-aligned bright wear.

Nothing was started. It is your decision.

## 10. Files

| Path | What |
|---|---|
| `Scripts/props/build_black_hat.py` | The build: stages, measure, gates (25), sidecar material, budget and collision blocks, fidelity |
| `Scripts/props/props_lib/blackhat_{spec,camera,geom,atlas,paint,look,gallery}.py` | The library (1.1.0). New: `geom.solve_tail_paths` / `tail_u_samples`, `paint.finish` (mean-colour recolour), `look.support_hull`, `gallery._line_sheet` |
| `Assets/BlackHat.blend` | Rebuilt from scratch; textures packed |
| `Exports/BlackHat/` | `SM_BlackHat.fbx`, `SM_BlackHat.sockets.json`, `Textures/` (8 maps, 2048) |
| `WorkFiles/blackhat/UnrealCheck/` | Harness (new `bhu_tex_composite.py`), run `0926d`, archives |
| `WorkFiles/blackhat/regression/post_black_hat/` | Snapshot (36 files), `SHA256SUMS.txt`, `compare_black_hat.py`, `compare_result.json` (black hat plus all three frozen lists) |
| `WorkFiles/blackhat/pre_final_pass/` | Round 1's scripts, exports, renders, blend and report, kept for comparison |
| `WorkFiles/blackhat/final_pass/` | This pass's patch scripts, hull prototypes and dev-build logs (`build_dev/fp1`-`fp4`) |
| `Backups/BlackHat_2026-09-25/` | Backup: blend, `Exports/BlackHat`, `Renders/BlackHat`, the modules and build script, this report, `References/BlackHat` |
| `References/BlackHat/REFERENCE_SPEC.md` | Now with the camera-shift erratum |

**Not touched:**
- the shuriken pack, the smoke bomb (its line sheet was only **read** for the backdrop gradient) and the paused
  paper bomb;
- the generic props_lib modules;
- `ue_import_textures.py` and `Scripts/pipeline/**`;
- the locks (BlackHat is held by claude, and was read only).

No GUI Blender, blender-mcp or running editor was used, and nothing was downloaded.
