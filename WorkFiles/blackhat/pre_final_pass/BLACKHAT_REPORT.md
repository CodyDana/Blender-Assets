# SM_BlackHat: build report (round 1)

**Date:** 2026-09-26. **Library:** props_lib blackhat **1.0.0**. **Build:** `Scripts/props/build_black_hat.py`, run
from scratch with no arguments (Blender 5.2.0 LTS, headless, `--factory-startup`, 90 s). It rebuilt
`Assets/BlackHat.blend`, `Exports/BlackHat/` and `Renders/BlackHat/`. Log: `WorkFiles/blackhat/build_full_2.log`.

## Status

- **Build gates: 22 of 22 pass** (`WorkFiles/blackhat/blackhat_report.json`, `gates`). `qa_check` passes **78 of 78**.
  The build's own fidelity gates F1-F7 (outline, rim, crown, extent, mask IoU, tone, chroma) all pass.
- **Unreal 5.8: 18 of 18 gates** on the exact exported bytes, each pass in its own fresh process, **0 warning or
  error lines**, content path `/Game/PropsCheck/BlackHat_0926b` in the shuriken validation project.
  Harness: `WorkFiles/blackhat/UnrealCheck/` (`verification_summary.json`). Run `0926a` (the previous build's
  bytes, used to debug the harness's two-hull round trip) is archived in `UnrealCheck/archive_0926a/`.
- **Frozen assets unchanged** (checked by the build at start and end): shuriken **41 of 41**, paper bomb **6 of 6**,
  smoke bomb **29 of 29** (every Assets/Exports/Renders/Scripts line of `post_smoke_bomb/SHA256SUMS.txt`).
- **Fidelity: close, not indistinguishable.** The silhouette, cone, crown, rib and lashing layout, rim, band ring,
  knot position and tail tips match the measured reference to about 1.5 px. The surface read (weave, sheen, wear
  streaks), the band's folds at the knot, and the tails' width and fraying still differ (section 8). There was no
  blind test in this round.

**Bytes:** FBX `92f135cc…21dedf`, sidecar `16c9c11c…1376c9`, blend `19533805…`.

---

## 1. Headwear decisions (the orchestrator's defaults; change any of these)

| Decision | What was built |
|---|---|
| **HEAD socket** | An Empty (`SOCKET_SM_BlackHat_LOD0_HEAD`, sidecar-applied in Unreal) on the axis at **z = 134.83 mm**, rotation 0: +Z up out of the crown, +X forward. It is where the top of a 57 cm head (a sphere of r = 90.72 mm) touches the **inner** cone (half-angle 64 deg): 10.22 mm below the inner apex (z 145.05 mm). Unreal reads it at (0, 0, 13.4833) cm, scale 1. |
| Orientation | +X forward, knot on the wearer's **left (+Y)**. In Unreal (mirrored Y) the knot is at -Y = the wearer's left for a character facing +X. The reference camera then sits at azimuth +29 deg from +X. |
| Pivot | On the axis at the **bottom of the rim tube** (z = 0; the tails hang 90 mm below it). |
| Headband ring / lining / chin cord | **None.** The reference never shows the underside, so it is the plain inner woven skin (`Renders/BlackHat/blackhat_underside.png`). |
| Band and tails | Part of the same static mesh, in their own slot `M_BlackHat_Cloth`, hanging in the reference pose (static; a cloth-sim or skeletal tail is a later option). |
| Size | D = 600 mm (REFERENCE_SPEC's DESIGNED default; the study estimated 500 mm). Mass 300 g (DESIGNED). |

## 2. The method (how the hat is made)

The build follows **REFERENCE_SPEC.md** where it and BLACKHAT_STUDY.md differ (the study itself says the spec takes
precedence): perspective camera at 2.6 R, 13 ribs, 26 lashings, band ring at rho 0.365, knot at theta +61.

| Part | Built as | Module |
|---|---|---|
| Woven skin | TWO straight-cone surfaces 1.8 mm apart (outer and inner), one patch per rib bay, the seams under the ribs. UV'd in each bay's **cone development**: a circumferential strand is an arc of constant slant, zero stretch, and it runs on under the rib into the next bay. Two bays interleave head-to-tail into one rectangle (~98 % fill). | `blackhat_geom.build_skin` |
| Ribs | 13 round rods (3.3 mm, 8 sides) lying on the outer skin along the generators, relief 0.75 d (spec 0.6-1.0), from under the cap lip into the rim. Rope twist is texture + normal. | `build_ribs` |
| Crown cap | A low spherical **dome** (radius 31.65 mm) with a rolled lip overhanging the skin, casting the black line; 13 lighter rib lines over the lid. | `build_cap` |
| Rim | A rolled tube (13.2 mm, 10 sides x 144) the skin runs into, and a binding cord (1.5 mm) on its inner top. | `build_rim` |
| Lashings | 26 sleeves of **three round cords** looped round the tube, cord and skin edge (4.5 mm onto the skin), at REFERENCE_SPEC 6's measured azimuths where given, rib ends and bay midpoints elsewhere. | `build_lashings` |
| Band | One turn round the cone at rho 0.365, lying over the ribs as a taut cloth does (straight between rib tops): a twisted roll round the back and front-left, fanning to 0.14 R with three folds and a gathered bundle into the knot. Tape-space UVs (x along, y round the section), LOD-independent. | `build_band` |
| Knot | A gathered lump with fold ridges and a crossing wrap, at theta 61, rho 0.43, sitting on the band. | `build_knot` |
| Tails | Two ribbons 1.2 mm thick (top, bottom and edge walls). Each runs down the cone as a geodesic, A over B, A turned 75 deg for 0.15 R after the knot, B standing 3.6 mm off the cone near the rim, then over the roll and hanging face-on to its **measured tip pixel at its measured hang** (the tip is the reference camera's ray through (592, 533) / (643, 520) at 0.30 / 0.32 R below the rim). Each ends in a long diagonal tear to a point on the outer edge (A 54 mm, B 75 mm), with an irregular bitten edge and loose fibre bundles; B has a deep notch splitting off a sliver. | `build_tail_path`, `tail_outline`, `build_tail` |

All geometry goes through a **1 nm position-keyed vertex factory** (`MeshBuilder.vid`); nothing uses
`bmesh.ops.bevel`. Every face carries per-corner local coordinates in its part's own strand / tape space, per-corner
normals and a slot.

**Frame fit (measured, not guessed).** Two numbers are not in the spec: where the skin enters the rim tube and how
high the metrology's rim-outline circle sits on our tube. `WorkFiles/blackhat/build_dev/tools/fit_frame.py` projected
the analytic parts with the spec camera and fitted them to REFERENCE_SPEC 1's silhouette rows: skin entry
**-0.40 tube radii** (the skin meets the roll below its centre, so the roll stands proud), camera z offset
**0.008 R**, rib relief 0.75 d, crown top at the virtual apex.

## 3. Textures, recolour and mip safety

Two sets at **2048** (the house size): `T_BlackHat_Straw_{BC,ORM,N,Detail}` and `T_BlackHat_Cloth_{BC,ORM,N,Detail}`.
Straw 21.7 px/cm (outer skin; the never-seen inner skin at 0.4x), cloth 61.6 px/cm. The cloth's UV0 is offset to the
second tile (U + 1), so qa_check's single-layout overlap test passes; the textures wrap.

Every texel is painted from its own part's coordinates (`blackhat_paint.py`), never projected, and nothing reads the
reference:
- **Skin weave:** courses 9.3 mm (0.031 R) of five 1.86 mm strands, irregular 3-8 deg radial seams per course (brick
  runs, half of them faint), per-strand tone runs.
- **Wear:** light strand tops in 4-18 mm streaks along the strands, at the zone covers of REFERENCE_SPEC 9 (left
  -62..-25 highest, front lowest, far side 10 %). The left zone is broadly lighter and glossier. There is one dull
  dark smudge at theta about -36.
- **Other parts:** twisted rope on the ribs, cord and lashings (three cords with dark valleys); split-cane fibres
  and front scuffs on the rim tube; a fine plain weave on the cloth, with dusty patches on the tails and twist lines
  on the band roll.
- **No damage, holes or colour were added.**

**Recolour (both parts):**

| | Straw | Cloth |
|---|---|---|
| Detail (sRGB-encoded linear d, full range, quantised once from float) | 228 levels, p1 / p10 / p50 / p99.9 = 51 / 69 / 104 / 252 | 203 levels, 88 / 125 / 163 / 252 |
| Default Tint (linear) | (0.230343, 0.210341, 0.204534) | (0.090159, 0.087765, 0.088031) |
| Tint (sRGB) | (0.5172, 0.4960, 0.4896) | (0.3321, 0.3278, 0.3283) |
| BC = sRGB8(decode(Detail8) x Tint), max linear error | 0.0017 | 0.0010 |
| Detail x Tint vs BC, mean over mips 0-8 | within **0.43 %** | within **0.86 %** (8-bit BC rounding on a narrow dark range) |

- **Detail and BC** are imported sRGB ON, so Unreal decodes both before filtering.
- **The specular mask** is linear in ORM.A. Every filtered sample is therefore the correct average.
- **Material:** BaseColor = Detail.R x Tint; Specular = **1.0 x ORM.A** (lacquered strand tops reach F0 0.08; the
  smoke bomb uses 0.5); Roughness = ORM.G; Metallic 0; N DirectX.
- **Where it is written:** the sidecar's `materials` block holds both graphs and default tints.
- **Limitation:** one tint per part. The rim and lashings use the straw tint, although REFERENCE_SPEC's rim is a
  little warmer (sRGB 0.241 / 0.223 / 0.213 against 0.233 / 0.225 / 0.224). That is within the spec's +-0.03, but
  it is not reproduced.

ORM.R is the analytic cavities x a Cycles AO bake of LOD0 alone (256 samples, 6 cm distance), one image per slot.

## 4. LODs and triangles

| LOD | Triangles (straw / cloth) | Screen size | Switch | LOD0 -> LODn p99 / 1 px at switch |
|---|---|---|---|---|
| 0 | **16,788** | 1.0 | - | - |
| 1 | **6,042** | 0.7036 | 0.89 m | 1.76 mm / 0.93 mm |
| 2 | **1,849** | 0.2463 | 2.54 m | 3.96 mm / 2.65 mm |

**Why LOD0 is over ~10k.** It is a 600 mm prop, the pack's largest, and its signature details are real geometry:
- 26 lashings x 3 cords: 4,992 triangles;
- the rim tube: 2,880;
- the band: 2,800;
- the binding cord: 1,152.

**The pack rule and what it forces.** The rule (x 351.8 / 50 mm bounds radius) switches LOD1 in at 0.70 screen
size, so LOD1 has to keep everything:
- lashings as three-cord sleeves;
- the rim, cord, ribs and band;
- the torn tails.

LOD2 keeps the ribs (3-sided), the rim, lashing bands, the band and the tails.

**What the switch costs.** The p99 deviations exceed 1 px at the switch. Both come from the torn tails' teeth (LOD1
and LOD2 cut the tear straight) and the band's section. Measured on the shaded frames
(`blackhat_lod_switch.png`), the mean pop is:
- LOD0 -> LOD1: 0.0039;
- LOD1 -> LOD2: 0.0072.

All three LODs use the same analytic UVs (their local coordinates stay inside LOD0's islands; gate 6b).

## 5. Collision

Two convex hulls, because the tails hang ~100 mm outside the body's cone and the containment gate wants every
vertex of every LOD inside a hull:
- **UCX_SM_BlackHat_LOD0_00:** a 15-gon band round the rim (bottom and top ring) plus a raised apex. 31 vertices,
  circumscribed.
- **UCX_SM_BlackHat_LOD0_01:** an oriented box round the hanging tails. 8 vertices.

**Containment:** every LOD vertex lies inside a hull, with the worst at -0.30 mm (inside). In Unreal's own export,
every LOD0 vertex is inside, the worst at -0.03 cm.

## 6. Unreal verification (`/Game/PropsCheck/BlackHat_0926b`, bytes `92f135cc…`)

These were one at a time, each in a fresh process, with the harness waiting while any UnrealEditor-Cmd was running.

**Steps:**
1. Blender FBX count;
2. pass 1 import (legacy FBX, Import Mesh LODs ON) + sidecar, via `Scripts/pipeline/ue_import_sockets.py`
   unchanged;
3. props texture import (`props_lib/ue_import_textures.py`, unchanged);
4. fresh texture verify;
5. pass 2 reload + gates;
6. pass 3 Unreal FBX export;
7. Blender round trip;
8. UV1 overlap.

**VERIFIED 18 / 18:**
- **LODs:** 16,788 / 6,042 / 1,849, identical to Blender and to the FBX re-import. Positions round-trip within
  3e-6 cm, and no triangle was dropped.
- **Collision:** 2 hulls. Their vertices round-trip within 1.8e-6 cm; the gate is 1e-5 cm because float32 at 30 cm
  is about 3e-6 cm, so the smoke bomb's 1e-6 cm limit for a 70 mm ball cannot hold here. The hulls contain LOD0.
- **Socket:** HEAD at scale 1, owned by the asset.
- **Screen sizes:** 1.0 / 0.7036 / 0.2463 from the sidecar, with the bounds radius matching.
- **Lightmap:** UV1 generated on every LOD with 0 overlap at 1024 and 2048.
- **Material slots:** 2 (straw, cloth).
- **Nanite:** off.
- **Textures:**
  - all 8 are sRGB / compression / mips as intended;
  - Detail is sRGB ON and TC_Grayscale;
  - ORM is TC_Masks with its alpha kept;
  - N is TC_Normalmap with flip OFF;
  - all are TMGS_FROM_TEXTURE_GROUP at 2048.

M_BlackHat_Straw / _Cloth are not shipped as Unreal assets. The recolour step builds them from the sidecar.

## 7. Renders (all from the baked maps)

`Renders/BlackHat/` holds:
- **reference view:** `blackhat_reference_view.png` (670 x 599, the spec camera, 512 spp, composited on the
  0.996 backdrop with no cast shadow), plus the side-by-side `blackhat_side_by_side.png` and the 3x crops
  `blackhat_crops_3x.png` (crown, knot, left bays, front rim, tails, right rim);
- **pack gallery:** `hero`, `raking`, `underside`, `top`, `wire`, `lods`, `lod_switch`, and the line sheet
  `blackhat_linesheet.png`.

**The reference-view lights.** Seven soft discs plus a weak white world, fitted by non-negative least squares to
REFERENCE_SPEC 2's brightness-by-azimuth rows and the part regions (rms relative error 17 %):
- `WorkFiles/blackhat/build_dev/tools/fit_lights.py`;
- the result is written into `blackhat_look.REF_LIGHTS`.

**The gallery exposure.** The hero lamps run at 0.15x the smoke bomb's product-lamp scale, so a black hat reads black
(object p50 stored 0.11). The sweep is hidden for the hero, raking and underside shots, because the tails hang below
the rim.

**Measured on the shipped render** (the metrology's own instruments; `build_dev/eval/final_eval.json`):

| Row | Reference | Render |
|---|---|---|
| Generator lines (mean top offset) | - | -1.5 px left, -1.4 px right (tolerance 1 px in REFERENCE_SPEC 11: **not met**, 0.5 px over) |
| Rim bottom at x 340 | 433.47 | 433.46 |
| Crown top | 142.53 | 142.52 |
| x extent | 1 ... 664 | 1 ... 664 |
| Lowest tail tip y | 533 | 533 |
| Mask IoU | - | 0.954 |
| Object lum lin p10 / p50 / p90 | 0.0086 / 0.0242 / 0.0601 | 0.0117 / 0.0223 / 0.0580 |
| Object chroma | 0.349, 0.328, 0.323 | 0.342, 0.331, 0.327 |
| Straw by azimuth (p50, 34 bins) | - | most within +-15 %. The misses: theta -40 +43 % and -32 -32 % (the smudge's edges); +72..+76 +16..26 %; +84 -52 % (our rib at 85 sits in that bin at the silhouette) |
| Left worn bay p10 / p50 / p90 | 0.024 / 0.055 / 0.097 | 0.025 / 0.064 / 0.097 |
| Front bay p10 / p50 / p90 | 0.015 / 0.024 / 0.047 | 0.015 / 0.027 / 0.045 |

## 8. What still does not match (honest)

1. **The weave's read.**
   - The reference shows crisp dark lines between the strands and bright streaky sheen along them (the left bays
     especially).
   - Ours is softer at pixel level and more even. At grazing views (the right side) it shows a fine wavy
     strand pattern where the reference shows broad course bands.
   - Tone statistics now match. The texture of the look does not.
2. **The wear and the smudge.**
   - The left worn zone is lighter in ours, but it lacks the reference's bright scratched streaks.
   - The dark smudge reads as a stripe along the generators, where the reference has an irregular patch.
3. **The ribs** are less bright than the reference's light twisted rods.
4. **The band at the knot.**
   - The reference band arrives as a thick rolled bundle with 3-4 visible fold lines.
   - Ours is a softer, flatter fan, and the knot reads as a lump rather than a wrapped knot.
5. **The tails.**
   - On the cone they read narrower and more diagonal than the reference's broad strips falling from the knot.
   - The torn ends are ragged, but not yet the reference's fibrous long points.
   - Face-on below the rim, the widths are at the top of the spec's tolerance (A 0.080 R, B 0.097 R). B crosses
     the rim at theta 38.5 (spec 40 +- 4).
6. **The crown cap** is a dome (the reference's profile is convex). REFERENCE_SPEC called it a 20 deg cone
   (INFERRED); the mean slope matches. Ours is darker and less "lit lid" than the reference.
7. **The rim** tube reads slightly flatter and lighter at the front (+26 % on the rim-front region). The lashings are
   right in count, place and wraps, but a touch smooth.
8. **The generator lines** are 1.4-1.5 px high: the designed far-side ribs at 112.7 / 250.6 sit near the
   silhouette tangents.
9. **One tint per part:** the rim's slight warmth is not carried (section 3).
10. **LOD pops:** LOD1 / LOD2 exceed the 1 px deviation at their switch (section 4), because the pack rule switches a
    600 mm hat at 0.70 screen size.

## 9. Gates

- **Build (22):**
  - qa_check clean;
  - LOD bands descending;
  - UVs: no collapsed or mirrored triangles, UV0 in two tiles, LOD UVs inside LOD0's islands;
  - hulls contain every LOD;
  - HEAD socket;
  - power of two with no colour chunks;
  - Detail full range;
  - mip parity within 1 %;
  - frozen assets unchanged;
  - no franchise string;
  - no triangle Unreal would drop;
  - F1-F7.
- **Unreal (18):** section 6.

## 10. Files

| Path | What |
|---|---|
| `Scripts/props/build_black_hat.py` | The build: stages, measure, gates, sidecar material block, fidelity |
| `Scripts/props/props_lib/blackhat_spec.py` | Build-to numbers (REFERENCE_SPEC, labelled), lashing rule, HEAD derivation |
| `Scripts/props/props_lib/blackhat_camera.py` | The reference camera in the build frame |
| `Scripts/props/props_lib/blackhat_geom.py` | Every part, the vertex factory, the LOD table |
| `Scripts/props/props_lib/blackhat_atlas.py` | Handedness fix, wedge pairing, skyline packing |
| `Scripts/props/props_lib/blackhat_paint.py` | The texel painters, maps, recolour |
| `Scripts/props/props_lib/blackhat_look.py` | Materials, AO bake, hulls, reference rig (fitted lights) |
| `Scripts/props/props_lib/blackhat_gallery.py` | Gallery on the shared rig, LOD-switch frame |
| `Assets/BlackHat.blend` | Rebuilt from scratch; textures packed |
| `Exports/BlackHat/` | `SM_BlackHat.fbx`, `SM_BlackHat.sockets.json`, `Textures/` (8 maps) |
| `Renders/BlackHat/` | Section 7 |
| `WorkFiles/blackhat/blackhat_report.json` | Every number, measured on what was built |
| `WorkFiles/blackhat/UnrealCheck/` | Harness (adapted copy of the smoke bomb's) and run `0926b`; `archive_0926a/` |
| `WorkFiles/blackhat/build_dev/` | Dev tools (`tools/bh_eval.py`, `fit_frame.py`, `fit_lights.py`, `set_lights.py`, `crop.py`), iteration builds `b1`-`b19`, `eval/` crops |

**Not touched:**
- the shuriken pack, the smoke bomb, and the paused paper bomb;
- the generic props_lib modules, `ue_import_textures.py` and `Scripts/pipeline/**` (all used as they are);
- the locks (BlackHat is held by claude, and was only read).

No GUI Blender, blender-mcp or running editor was used, and nothing was downloaded.
