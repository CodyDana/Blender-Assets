# Showcase Plan — the presentation package for every item in the ninja line

**Date:** 2026-09-20
**Status:** plan only. Nothing built, nothing rendered, no build script touched. Written while the paper-bomb
build owns the machine.
**Scope:** how each finished item gets shown — on Fab and in the dev's own project — what it costs, and when it
happens.

**Flags, as in `SHURIKEN_STUDY.md` and `KUNAI_STUDY.md`:** **MEASURED** = read this pass from a build report, a
build log or an image on disk, with the file named. **DERIVED** = computed from measured figures. **ESTIMATE** =
a design choice or a scaled projection, not confirmed on this machine. Every render-time figure past section 7
is an ESTIMATE scaled from a MEASURED one, because this was a read-only job.

---

## 1. Summary

| Item | Value |
|---|---|
| What it is | One shared module, `Scripts/showcase/`, that consumes a finished build and emits every image |
| Per item | 9–11 masters at 3200x1800, declared in a ~15-line `ShowcaseSpec` beside the build's own spec |
| Per pack | 10 Fab gallery images + thumbnail + a technical PDF in Additional Files |
| The one architectural call | **One rig, two lighting profiles** — not two rigs, and not one rig doing two jobs |
| The one cheap structural fix | **Exact 2:1 frame tiers** (13.846 / 6.923 / 3.462 px/mm) retire the line sheet's apology |
| The one blocker fixed first | The hero's exposure anchor moves to the fixed-camera spec shot, which frees the kunai pose |
| Engineering | ~40 h total; **5 h** of it makes today's gallery uploadable at all |
| Render | ~2.5 min per steel item, ~37 min for a cold eleven-item regeneration (ESTIMATE, scaled 4x from MEASURED) |
| Pilot | Four-point first, kunai second |
| Queue | Stage 0–4 after the paper bomb; stages 5–8 in the gaps while the fan / smoke bomb / hat build |

**The three facts that shape everything below.**

1. **Nothing on disk can be uploaded.** MEASURED, this pass, over all 49 PNGs in `Renders/Shuriken` and
   `Renders/PaperBomb`: 48 are 1600x900 or 1599x900, one (`modern_line_sheet.png`) is 5600x900, one
   (`style_comparison.png`) is 8220x1740 at 12.2 MB. Fab's gallery floor is 1920x1080 at under 3 MB each
   (`FAB_ASSET_STUDY.md` 4.5). **Zero of 49 pass.** The set totals 79.8 MB against a 25 MB gallery budget. A
   resolution and packaging pass is not an improvement, it is the price of entry.
2. **The existing rig is a calibration instrument that was asked to also be an advertisement, and the kunai is
   where that broke.** MEASURED, from `kunai_plain_report.json` → `gallery.reason`: the hero yaw was probed at
   ten angles, 96 samples; coat p50 ran 0.40 / 0.39 / 0.45 / 0.48 / 0.50 / 0.52 / 0.54 / 0.53 / 0.51 / 0.49
   against the anchor forms' 0.56; "only about −10 to −30 pass"; a 3/4 pose across the frame reads 0.39 and
   fails. The end-on hero is not a taste failure, it is the only pose the pack-consistency gate allowed.
3. **The fix does not need a new rig.** `Renders/Shuriken/kunai_plain_3q.png` already exists, on the existing
   rig, with the blade on the frame diagonal reading its full 280 mm. It was rendered as a close-up extra
   because it could not pass the hero gate. Move the gate and the shot is already proven.

---

## 2. What the current gallery actually measures

All figures MEASURED this pass from `render_stats.<form>_persp` in the seven per-form reports under
`WorkFiles/shuriken/`. `coverage` is `object_pixel_fraction`; `separation` is `|object p50 − backdrop mean|`.

| Form | coverage | obj p50 | backdrop mean | separation | bbox W x H | verdict |
|---|---|---|---|---|---|---|
| square_plate | 0.3232 | 0.5543 | 0.5116 | 0.043 | 0.899 x 0.802 | best of the set |
| eight_point | 0.2337 | 0.5493 | 0.5124 | 0.037 | 0.897 x 0.742 | fine |
| six_point | 0.2005 | 0.5504 | 0.5312 | 0.019 | 0.900 x 0.751 | fine |
| hooked_cross | 0.1648 | 0.5344 | 0.5337 | **0.001** | 0.900 x 0.807 | plate value = backdrop value |
| four_point | 0.1593 | 0.5308 | 0.5362 | **0.005** | 0.899 x 0.801 | plate value = backdrop value |
| spike | 0.0785 | 0.3120 | 0.5403 | 0.228 | 0.897 x 0.449 | dark bar, good separation, low coverage |
| kunai_plain | **0.0595** | 0.4944 | 0.5659 | 0.072 | **0.139** x 0.856 | the broken one |

**Read it honestly.** The heroes are *not* "a grey object on a grey background" — looking at
`four_point_persp.png`, the dark ground chamfers, the bright edge lands and the cast shadow carry the read, and
the image is good. What the table says is narrower and still true: **the flat plate value sits on top of the
backdrop value** (0.001 and 0.005 on two forms), so the only contrast in the frame comes from thin features.
That survives at 1600 px and dies at 300 px, which is the size the Fab search grid uses. And the kunai covers
6 % of frame inside a bbox 14 % wide.

Three specific image defects confirmed by looking:

- `kunai_plain_persp.png` — near end-on, blade foreshortened into a stub, over half the frame empty grey.
- `kunai_plain_grip_closeup.png` — a full-bleed abstract of black tape. No tip, no ring, no blade, nothing that
  tells a buyer what they are looking at.
- `modern_line_sheet.png` — 5600x900, and the kunai's top-view cell prints
  `top view at 5.0 px/mm (pack 6.9): its own frame`. A marketing image apologising for itself.

---

## 3. The architecture: one rig, two lighting profiles

`Scripts/shuriken/shuriken_lib/render.py` is frozen and six forms are byte-identical across builds against it.
It is not modified. What changes is that its lamp set and world become **one named profile among several**, and a
second profile is added for the sales shots.

| Profile | World backdrop (linear) | Lamps | Object luminance rule | Used by |
|---|---|---|---|---|
| `SPEC` | the frozen value ramp, unchanged | the frozen key / two rakes / fill / bounce / top / wall card | `PLATE_BAND` (0.36–0.64), `PACK_COAT_ANCHOR`, hard | spec, wire, lods, grind, collision |
| `SALES` | 0.045 at the top → 0.012 at the horizon (ESTIMATE, tuned at the pilot) | same key + wall card, plus a tight rim from lower-right-behind | `silhouette_contrast` + `coverage`, coat reported not gated | hero, reverse, edge, detail |
| `PAPER` | the props rig's ramp, ground roughness 0.32 | props raking key, no glossy-only cards | albedo-scaled band, as `props_lib.gallery.object_p50_band` already does | the tag |
| `PAPER_WOOD` | `PAPER` + a small glossy card | for lacquered fan ribs | as `PAPER` | the fan |
| `CLOTH` | `PAPER` + a rim light | **its own dark band** | silhouette separation, not the steel band | the hat, the smoke bomb |

**Why a profile and not a second rig.** Both judges split on this. A second rig is the right *diagnosis* and the
wrong *unit*: the line already has four more material classes queued (paper, lacquered wood, straw, black
cloth), so "two rigs" becomes five within a month, and the two would drift into two products. A profile is a
data record — world nodes, lamp weights, a luminance rule and a gate set — over one shared ground, one set of
placement helpers, one `LABEL_COLOUR`, one `fit_perspective` / `centre_perspective` / `place_for_shift` /
`solve_depth_of_field`. Adding the hat costs a table row, not a module.

**The rim-wall risk is real and is checked, not assumed.** A 0.9-metallic mirrors the world; a darker world is
exactly the condition that sent the rim walls to ink before the wall card was built. So under `SALES`:
`WALL_GATE`, `FACET_GATE` and `BAR_WALL_DOT_GATE` stay **live and hard**, the emissive wall card and the
overhead glossy-only panel transplant unchanged, and the **first thing tested at the pilot is the four-point
under `SALES` with those three gates on**. If they fail, the backdrop is lifted until they pass and the sales
profile ends up closer to `SPEC` than planned. That is an acceptable outcome; shipping ink-black rim walls is
not.

### 3.1 The one gate that moves

**Today:** `pack_consistency` is evaluated on the **hero**, whose camera and yaw are free. So composition and
exposure fight, and exposure wins — that is the whole kunai story.

**Change:** the pack-consistency anchors (`PACK_ANCHOR`, `PACK_COAT_ANCHOR`, `PACK_WALL_ANCHOR`,
`PACK_BACKDROP_ANCHOR`) are evaluated on the **spec shot**, which is orthographic with a fixed camera, a fixed
lamp set and no pose freedom. On the hero the coat figure is **measured and reported**, never gated.

That is one line of consequence and one real cost: the four anchors must be re-derived from one clean rebuild
on frozen maps, with the old values archived and the reason recorded. Do it **alone**, never in the same build
as a material change, or a regression hides inside the re-baseline.

### 3.2 The gates the sales shots get instead

Each is fed by the same mask pass `render.py` already renders. Baselines are the MEASURED column from section 2.

| Gate | Rule | Baseline today | Notes |
|---|---|---|---|
| `coverage_relative` | ≥ 0.85 x the best coverage found in the yaw sweep | — | the primary gate: relative, so it cannot be unreachable |
| `coverage_floor` | star/plate 0.15 · bar 0.075 · knife 0.14 · card 0.20 · fan 0.20 · cone 0.18 · ball 0.12 | 0.0595–0.3232 | a regression floor, set at today's values; **the kunai fails it today and must move** |
| `silhouette_contrast` | ≥ 0.15, object p50 vs the backdrop median in a 12 px annulus | 0.001–0.228, median 0.037 | six of seven fail today; that is the point |
| `foreshortening` | hero silhouette area ≥ 0.62 of the item's max over the yaw sweep | kunai fails | P4's rule, kept verbatim |
| `anchor_in_frame` | on any `detail_*`: the named feature **and** ≥ 20 % of the body's silhouette both in frame | `kunai_plain_grip_closeup.png` fails | the cheapest quality win in the plan |
| `thumb_blob_count` | downsample the tile to 320x180 LANCZOS, count separable object blobs, must equal the item count | — | the only way to learn that two forms merge into one smear at grid size |
| `label_legibility` | every burned-in glyph ≥ 45 px cap height at 3200 wide (4.5 % of tile width on a 4-up board) | line sheet is ~2.75 % | survives Fab's downscale to 1280 |
| `wall` / `facet` / `plate` / `dark_dots` | unchanged, still hard, now also on the sales shots | all pass | the ink-in-the-rim-walls insurance |

**Honesty note on the floors.** A four-arm star fills about 22 % of its own bounding box; with the bbox already
at 0.90 x 0.80 there is no route to 0.30 coverage without cropping the arms off. Absolute coverage gates above
~0.20 are unreachable for this geometry. The relative gate does the work; the floors only catch regressions.
The kunai's floor of 0.14 is an **ESTIMATE** — `kunai_plain_3q.png` looks like it lands near it, and the pilot
measures it. If the diagonal pose comes in at 0.12, the floor becomes 0.12 and the number is recorded as
measured, not wished for.

---

## 4. The standard per-item package

**Masters** are 3200x1800 PNG — exactly **2x** the frozen 1600x900 measurement domain. Every pixel-denominated
gate (`WIRE_PX` 1.1, `HERO_MAX_COC_PX` 1.5, `BACKDROP_PATCH_HALF` 5, `BAR_WALL_DOT_GATE`'s erode 4 / window 7 /
max blob 16) runs on an exact 2:1 box downsample of the master, so **no threshold is retuned and no anchor is
rescaled**. 3840x2160 is rejected for precisely that reason: 2.4x is not an integer relation, it would force a
rescale of every pixel gate on top of the anchor move, and Fab serves the gallery downscaled anyway. Mask passes
render at **1600x900**, because that is already the downsampled domain — a free saving of about 7 s per item.

Fab delivery is a JPEG derived from the master, quality bisected down until it is under 2.6 MB.

| # | Shot | File | Framing | Profile | Gallery? |
|---|---|---|---|---|---|
| 1 | **hero** | `<item>_hero.png` | 72 mm, elev 29°, az −22° (the frozen hero rig). **Yaw solved, not declared**: 8 mask passes at 400x225 pick the largest silhouette whose declared `must_read` feature is unoccluded. Long axis on the frame diagonal. DOF via the existing solver, CoC ≤ 1.5 px at 1600, f/16 floor. No text, ever — the thumbnail crops from here. | `SALES` | **yes** (per-item) |
| 2 | **reverse** | `<item>_reverse.png` | same rig, azimuth +140°, elev 18°. Kills "is the back modelled". For the manji this is a 180° yaw about Z, never a camera move under the plate — the `presented_face` +Z guard is absolute. | `SALES` | internal / PDF |
| 3 | **edge** | `<item>_edge.png` | Orthographic down the item's thin axis so the whole silhouette is the section. Fill 0.90 of frame width. Raking key at 6–8° elevation skimming the edge. | `SALES` | **yes** (triptych source) |
| 4 | **detail_\<name\>** | `<item>_detail_<name>.png` | 105–110 mm at a named anchor — a socket name (`Grip`, `Tip`, `Ring`, `Trail`, `Face`, `Fuse` all exist as Empties) or a mesh landmark. **`anchor_in_frame` is hard here.** 1–2 per item. | `SALES` | **yes** (triptych source) |
| 5 | **spec** | `<item>_spec.png` | Orthographic, axis by class, at a declared **frame tier** (section 4.1). Drawn scale bar computed from the panel's own recorded px/mm. **This is the pack's exposure anchor.** | `SPEC` | internal / board source |
| 6 | **wire** | `<item>_wire.png` | The existing `wire_pair` at the **hero** pose, not the flat top — a flat wire of a 3 mm plate shows nothing about the grind. | `SPEC` | board source |
| 7 | **lods** | `<item>_lods.png` | The existing LOD strip, captions gaining `switch_distance_m` and the FOV convention. | `SPEC` | board source |
| 8 | **grind** | `<item>_grind.png` | The existing `GRIND_VIEW` (elev 21°, az −34°, 105 mm, 75 mm), **three panels in ONE frame** via per-panel sensor shift, framed wider so the three LODs visibly differ. | `SPEC` | board source |
| 9 | **collision** | `<item>_collision.png` | Same 3/4 camera as `reverse`, mesh ghosted 40 %, UCX hulls as a translucent amber shell with hard wire edges, sockets as 20 mm three-axis gizmos with names. Built from the **exported** hulls and the `.sockets.json` sidecar. | `SPEC` | board source |
| 10 | **extra_\<name\>** | `<item>_extra_<name>.png` | One shot that exists only because of what the item *is*. Steel stars get none. See section 5. | per class | varies |
| — | *diagnostics* | `WorkFiles/showcase/<item>/diag/*.png` | mask passes at 1600x900, the yaw-sweep contact strip, the calib frame | — | **never shipped** |

**Closed shot vocabulary.** `hero · reverse · edge · detail_* · spec · wire · lods · grind · collision · front ·
back · states · interior · pairing · extra_*`. The board compositor finds panels by name, never by convention,
so a renamed shot is a manifest error rather than a silently missing tile.

### 4.1 Frame tiers — the fix for the line sheet's apology

The pack's frozen ortho frame is 231.111 x 130.0 mm, MEASURED as 6.9231 px/mm at 1600x900
(`render_rig.top_px_per_mm`, all six star forms). At 3200x1800 that same frame is 13.846 px/mm. Define the tiers
as exact doublings of it:

| Tier | Frame (mm) | px/mm at 3200x1800 | Composites onto a board at | Items |
|---|---|---|---|---|
| **S** | 231.1 x 130.0 | 13.846 | 0.5x | every star, the senban, the spike, the smoke bomb |
| **L** | 462.2 x 260.0 | 6.923 | 1.0x | the kunai (280 mm), the open fan, the tag |
| **XL** | 924.4 x 520.0 | 3.462 | 2.0x | the kasa, if it measures over 260 mm in plan |

Every tier is an exact power-of-two multiple, so **every panel on a shared board lands at 6.923 px/mm — the
pack's own existing number** — with no resampling artefacts and no exception. The kunai's top view goes from
5.0 px/mm in a bespoke frame to 6.923 px/mm in a declared one. The caption
`top view at 5.0 px/mm (pack 6.9): its own frame` disappears because the condition that produced it is gone, not
because it was suppressed. Each spec panel still prints its own scale bar, computed from its recorded px/mm and
gated against it.

---

## 5. Where a shared camera set does not fit

The package above is designed around a flat steel plate. Four items break it, and one is the pack's colour.

### 5.1 The paper tag — the print is the product, so the rules invert

MEASURED from `paperbomb_report.json`: 161.99 x 69.82 x 12.41 mm (curled), 1132 / 428 / 172 tris, 0.90 g,
2048 atlas at 12.42 px/mm, one UCX octagonal prism (16 v / 10 f), four sockets `Face` / `Attach` / `Cord` /
`Fuse`, LOD screen sizes 1.0 / 0.1768 / 0.0619, switch at 0.888 m and 2.539 m.

| Shot | Change | Why |
|---|---|---|
| `hero` | **Keep the existing raking 3/4 unchanged.** | `paperbomb_hero.png` is the best image on disk. Do not replace a working shot with a systematic one. |
| `reverse` | becomes **`back`**, a flat ortho at tier L | For a two-sided printed object the back is a *selling* image — aged paper, show-through — not a doubt-killer |
| `spec` | becomes the **front/back flat pair** `props_lib.gallery` already renders | That pair is the tag's natural line-sheet identity |
| `edge` | becomes a **curl silhouette** from 8° elevation | Proves it is a card with real cockling and a 12.4 mm curl, not a decal plane. The exact analogue of the star's edge profile, and the answer to "why is a paper tag a mesh" |
| `detail_*` | at fibre scale on the seal and the ring, plus a **legibility pair**: the calligraphy at 1.5 m beside the 1:1 crop | States the texel density honestly instead of only ever showing it at macro |
| `wire` | over the **raking** shot, not flat-on | A flat wire of a 1132-tri card shows nothing; the raking light shows the curl that is the geometry story |
| new | **face-orientation panel** (blue front / red back) | Thin two-sided item: whether the back renders is the buyer's first question |
| **banned** | any ember, flame or lit fuse, in a still or a video | `FAB_ASSET_STUDY.md` 6 records automated Mature flags hitting fire VFX with appeals denied. Unappealable, bot-applied, and it would bury the listing |

**The tag is the pack's colour anchor and its biggest single judgement call — see section 10, decision 3.**

### 5.2 The folding fan — the selling fact is that it folds, and it may not

The fan is queued **shape only** (user, 2026-09-19: "hold off on [the design], just make the shape first"), with
the opening angle parameterised and a closed version and animation deferred.

- If it ships as **one static mesh in one state**: the states strip is **NOT BUILT** and the description says
  one state. This is the single most important rule in the plan. An image that implies articulation the buyer
  does not get is the fastest refund an unknown seller can buy, and it is the exact opposite of the house rule
  that every claim be checkable.
- If it ships with **states**: `extra_states` is a three-panel closed / half / open frame, built by the same
  panel renderer as the grind strip, and the description names the mechanism (separate meshes / shape key /
  rib bone chain) because each implies different engine work for the buyer.
- `spec` = front flat **open** at tier L plus a back flat — a sensu leaf is printed both sides.
- `edge` = the **closed** fan's profile: rib count and leaf thickness in one silhouette.
- `detail_*` = the pivot rivet and one rib-to-leaf joint, the two places a buyer looks for cheating.
- Hero yaw is solved but constrained so the leaf is never edge-on — the fan's version of the kunai problem.
- Profile `PAPER_WOOD`. Collision: one hull closed, a hull set open; show both if both ship.

### 5.3 The kasa — a costume piece, and the interior is the quality signal

- `hero` = a **low** 3/4 with the brim edge near eye level and the interior partly visible.
- `spec` = **side elevation** at tier L or XL with height and diameter ticks, plus a small plan inset composited
  in the corner. A top view of a cone is a circle and says nothing.
- `extra_interior` = looking up into the crown, showing the weave from inside and the band's attachment. A
  hollow cone with no interior geometry is a known cheap-asset tell; this is a two-minute render that answers it.
- `detail_*` = the straw weave and one torn cloth tail's frayed edge.
- Profile `CLOTH`: a blackened kasa against the pack's dark sweep is the **inverse** of the metal problem and
  must not be forced to the steel band. It declares its own dark object band and is gated on **silhouette
  separation from the backdrop**, not on the steel band.
- Face-orientation panel required if the torn tails are alpha rather than geometry. If they are geometry, say
  so — "the fray is geometry, not an alpha card" is a stronger claim than any render.
- Scale: it is worn, so the spec panel gains a drawn **1.8 m height line** and the inner clearance diameter in
  mm. **No mannequin mesh.** Epic sample content is display-only under EULA 6(a) and DA 3(f)(ii), and a drawn
  rule carries no IP.

### 5.4 The spike (bo-shuriken) — a 150 mm rod, already the pack's odd one out

MEASURED: 150 x 6 x 6 mm, 92 / 60 / 28 tris, coverage 0.0785, bbox 0.897 x 0.449, separation 0.228 — the best
separation and the second-worst coverage in the pack, because it is a thin dark bar on a light sweep.

- It already has a **section inset** in its LOD strip (`lod_strip_section_inset`: the butt end, end-on, at 5x).
  Promote that idea: the spike's `edge` shot **is** the end-on section at 5x, filling the frame.
- Hero yaw solved with the rod on the frame diagonal; its coverage floor is 0.075, its own measured value.
- It is the worst turntable subject in the line — a thin rod vanishes edge-on twice per turn. If a video is ever
  built, the spike gets a tumble or a tilted camera ring, never a flat turntable.
- Keep it out of the thumbnail's front rank for the same reason a round object is kept out: at 300 px it is a
  line.

### 5.5 The smoke bomb — small and round, the weakest tile shape there is

- `spec` = one elevation at tier S plus a cut section; a sphere has no informative second ortho axis.
- `edge` becomes a **scale pairing** beside a four-point star, so size reads instantly.
- Its whole selling detail is the frayed tape wrap, so `detail_wrap` is the **main** image, not a supporting one.
- Collision should be `USP_` (sphere). Labelling it as the deliberate choice it is, rather than shipping a
  generic UCX, is itself a trust signal.
- Keep it out of the thumbnail's front rank.
- **No smoke VFX anywhere in the media.** The pack ships a mesh and maps; a VFX-looking gallery over a mesh-only
  package is a top refund cause, and the project's existing smoke system descends from an engine Niagara example.

---

## 6. Pack-level pieces

Ten gallery images plus the thumbnail. **The operative budget is not "25 MB", it is 10 images** — at 3200x1800
with genuine detail, JPEGs land near 2.2 MB each and 11 files is ~24 MB against the cap. Rank ruthlessly, and
let the bisect-and-assert step enforce it.

| # | Piece | File | Must contain | Text |
|---|---|---|---|---|
| **T** | **Thumbnail** | `thumbnail.jpg` | **The whole line, never one item.** 3-2-3 staggered fan, every form tilted 55–65° so the ground edges catch the light, overlap ≤ 15 % per item, the kunai as the diagonal spine. Cluster silhouette ≥ 0.55 of frame. Flat near-black backdrop, **no gradient** (a gradient makes corner items read dimmer and buyers read that as inconsistent quality). Exactly one warm accent — the tag's vermillion. Round and thin forms out of the front rank. Gated by `thumb_blob_count`. | **NONE.** Search reads the thumbnail and Fab's tagger reads it; text pollutes the tags, is illegible at 300 px, and a "50+ ASSETS 4K PBR" banner reads as an asset flip |
| **1** | Overview grid | `01_grid.jpg` | Fab's documented ask for packs. 4 columns x 3 rows, cells 800x600 at 3200x1800, **one px/mm across the whole grid** via the tiers, long items span two cells. One FLAT backdrop value, no vignette, no cell borders — whitespace separates. **Rendered as ONE Cycles frame** with lamps fixed in world space and objects moved into cells: identical light per cell, no per-tile denoise variance, and the shared-scale claim becomes trivially true instead of asserted | item names only |
| **2** | Kit hero | `02_kit.jpg` | The same arrangement, breathing: looser spacing, slightly higher elevation, the one image that makes a solo seller look like a studio. **Positions live in a data file read by the same script** — if it cannot be generated, it is cut | none |
| **3** | Scale board | `03_scale.jpg` | All eleven at ONE px/mm on a 10 mm / 100 mm grid, ordered by size, with a 100 mm bar | item name + across-dimension in mm, from the report |
| **4** | Kunai sales hero | `04_kunai.jpg` | The single best craft shot. The 3/4 diagonal, full 280 mm | none |
| **5** | Detail triptych | `05_detail.jpg` | Three raking close-ups side by side — steel pitting, paper fibre, straw weave. Three materials in one frame is a stronger claim than three images | material name only |
| **6** | LOD board | `06_lods.jpg` | Every item's LODs, tri counts, screen sizes, **and the switch distances in metres**, plus the reference convention printed once: *16:9, 90° horizontal FOV, Unreal ComputeBoundsScreenSize S = 1.778 R / d*. A distance without its convention is not a fact | tris, screen size, metres |
| **7** | Collision + sockets | `07_collision.jpg` | Hulls over ghosted meshes, hull counts and volumes, socket names, all from the exported hulls and sidecars. Almost no competing weapon pack documents sockets at all | hull count, socket names |
| **8** | Wire board | `08_wire.jpg` | Every LOD0 wire on the shared backdrop | tri counts |
| **9** | Contents card | `09_contents.jpg` | Every item, tri counts, texture sets, what is included. The image people screenshot to show a teammate | the table |
| **—** | 3D preview | — | **Do not author a GLB.** `FAB_ASSET_STUDY.md` 4.4: Fab auto-converts an FBX listing to GLB / glTF / USDZ. Verify what the conversion produces before spending an hour on it | — |
| **—** | Technical PDF | `TECHNICAL_REFERENCE.pdf` | All per-item sheets — spec-plate grid, material proof (BC / N / ORM / render quadrants read from the shipped PNGs), UV0 island layouts, per-item number blocks — plus the import notes verbatim. Fab allows 3 Additional Files at 6 GB each and the slot is otherwise wasted. Generated from the same label table, so it cannot drift | full |
| **—** | Video | — | **Not for listing one.** 20–30 min of Cycles for a turntable montage that the 3D-preview slot largely covers. Revisit once the pack has sold something | — |

### 6.1 Text policy

**On an image**, only where the image is meaningless without it *and* the value is a number the build report
emits: dimensions in mm, triangle counts, LOD screen sizes and switch distances, map names and resolutions,
hull counts, socket names, item names.

**Never on an image:** "AAA", "game ready", "optimised", "4K PBR" banners, price, sale marks, engine logos,
seller name or logo, star bursts, version badges that could read as Epic branding. Several are outright
rejection categories (`FAB_ASSET_STUDY.md` 4.6 lists brand logos and non-16:9 thumbnails among documented
rejections).

**In the description only:** the LOD and collision statement, the socket list, the texture list with
resolutions, the mass and dimension table, the CC0 / third-party statement, the AI-usage declaration, support
email, changelog.

**Two claims to phrase carefully, both caught by the judges:**

- **Lightmap UV.** `known_gaps` says plainly: *"The FBX carries only UV0. UV1 (lightmap) exists only because the
  import generates it."* The measurement (`uv1_overlap_pixels_2048` = 0 on LOD0/1/2) is real. Ship it as
  *"our UV0 generates a clean lightmap UV1 on import — measured 0 overlap at 2048, Generate Lightmap UVs ON,
  LightMapCoordinateIndex 1"*, never as "ships with a lightmap UV". The disclosure sits at the same type size
  as the claim.
- **QA count.** 62 checks is the **kunai's** number; the six star forms run 55 each. Any badge is per-item, read
  from that item's own report, and reads `qa 55/55, build <date>` — never an unqualified "validated".

---

## 7. Module design

```
Scripts/showcase/
  build_showcase.py            CLI, the only entry point
  showcase_lib/
    __init__.py                VERSION
    profile.py                 LightProfile: SPEC / SALES / PAPER / PAPER_WOOD / CLOTH
    spec.py                    ShowcaseSpec, ShotSpec, the class table
    rig.py                     the shared rig: world, ground, cameras, fit/centre/DOF solvers
    shots.py                   one function per shot in the closed vocabulary
    panels.py                  N panels in ONE frame via per-panel sensor shift
    boards.py                  OIIO composition: grid, scale, LOD, wire, collision, triptych, contents
    labels.py                  THE ONLY PLACE A NUMBER BECOMES A STRING
    gates.py                   the section 3.2 gates
    manifest.py                fingerprints, cache, freshness, orphan detection
    encode.py                  downsample, JPEG bisect, thumbnail, MEDIA_MANIFEST
```

**One toolchain.** MEASURED this pass: Blender 5.2's Python has `numpy` 2.3.4 and `OpenImageIO` and **no PIL**;
the system Python has PIL and **no numpy**. Everything — render, panel stitch, overlay text via
`OpenImageIO.render_text`, resize, JPEG — therefore runs inside Blender's Python, and
`Scripts/shuriken/line_sheet.py`'s separate `py -3` Pillow pass disappears along with
`WorkFiles/kunai/plain_build/postbuild_sheets.sh`, the hand-written per-build script that juggles three
interpreters today. The **one** sanctioned exception is PDF assembly, which needs PIL: it runs under system
Python, reads only fingerprinted PNGs named in the manifest, and is covered by the staleness gate like anything
else.

### 7.1 What an asset package declares

A module-level `SHOWCASE` object beside the existing `FORM`, discovered by attribute exactly as `build_pack.py`
already discovers forms. About 15 lines:

```python
SHOWCASE = ShowcaseSpec(
    item="folding_fan", title="Folding fan", profile=PAPER_WOOD, klass="articulated",
    hero_yaw="solve", must_read="rib_tips",
    spec_axis="front", spec_tier="L", spec_back=True,
    details=(Detail("rivet",      anchor="SOCKET_Pivot", lens=110, frame_frac=0.55),
             Detail("leaf_joint", anchor="SOCKET_Rib3",  lens=110, frame_frac=0.45)),
    states=("closed", "half", "open"),     # omit entirely if the fan ships one state
    extra_shots=("back",),
    caption=("{title}",
             "{across_mm:.0f} mm open   {mass_g:.1f} g",
             "LOD {tris0:,} / {tris1:,} / {tris2:,}   {texture_size} px  {px_per_cm:.0f} px/cm"),
)
```

Everything else — cameras, lamps, resolutions, file names, overlays, encoding, gates — is derived from `klass`
and `profile`. Item twelve costs a spec, plus one recipe function if it is a genuinely new shape class.

**The classes:** `plate` (stars, senban, manji) · `bar` (spike) · `knife` (kunai) · `card` (tag) ·
`articulated` (fan) · `hollow` (kasa) · `round` (smoke bomb).

### 7.2 Every number stays true — four mechanisms, none optional

1. **Pointer provenance.** A label is a `(json_pointer, formatter)` pair and `labels.py` is the only module that
   turns a number into a string. Example: `("$.lod_switching.switch_distance_m[1]", "{:.2f} m")`. Each sheet
   writes `<sheet>.labels.json` recording every string with the pointer it came from and the report's
   `generated` timestamp. `--check` re-resolves every pointer against the report on disk **and re-parses every
   numeric token actually printed**, comparing to the printed precision. A number not in the report cannot
   appear on an image; if it is wanted, the **build** is extended to emit it.
2. **Fingerprints.** `input_fingerprint` = sha256 over LOD0/1/2 vertex+index bytes · the sha256 of every shipped
   texture · the `ShowcaseSpec` repr · the `LightProfile` version · `showcase.VERSION` · resolution · samples ·
   the Blender version and render device. A master is re-rendered only when its fingerprint changes or its own
   file hash has drifted.
3. **Staleness, made mechanical.** `build_showcase.py --check` renders nothing and fails if: any master's
   fingerprint is stale; any pack board is older than a master it composites; any report is newer than its
   images; or `Renders/Showcase/<item>/` holds a PNG the manifest does not list (that last one is how a renamed
   shot leaves a stale file behind today). `--no-cache` is forced on release builds.
4. **Conditional claims.** The engine-verified block renders **only** when `engine_check.status == "verified"`
   **and** `matches_this_build` is true — the report already models this exactly, and
   `attach_engine_check.py` already promotes a pending block only when the SHA-256 Unreal imported equals the
   bytes on disk. Otherwise the block is replaced by "engine check pending for this build". This is the
   highest-risk object in the package.

**Baked maps only** is enforced by construction: every 3D panel uses the existing `M_Preview_Baked_<mesh>` path
(`render_gates.beauty_source` already records `"baked textures only"`), and `--check` fails any panel whose
recorded `beauty_source` is not the baked material.

### 7.3 When it runs

```
py -3 Scripts/showcase/build_showcase.py --items all --out Renders/Showcase [--fab] [--check] [--no-cache]
```

- **Inside the build.** `build_pack.py --showcase` and `build_paper_bomb.py --showcase` call `render_item` after
  `qa_check`, in the same process, where the scene is loaded and the baked preview materials are already
  assigned. Cheapest place to render, and it guarantees the images and the report come from one build.
- **Standalone**, against a saved `.blend`, for presentation-only iteration (a caption, a yaw, an encode
  setting) without paying for geometry and bakes. In this mode it **claims the asset lock** via
  `Scripts/pipeline/lock.py` and refuses to run if the `.blend`'s mesh fingerprint disagrees with the report.
- `--fab` writes `Exports/Fab/<Pack>/gallery/NN_<name>.jpg` in display order plus `thumbnail.jpg` and
  `MEDIA_MANIFEST.json` (bytes, dimensions, quality, sha256, source master, build id), asserting: every image
  ≥ 1920x1080 and exactly 16:9, each under 2.6 MB, the set under 24 MB, the thumbnail from the no-overlay
  variant. `FAB_ASSET_STUDY.md` 4.5 encoded as code rather than remembered.

### 7.4 Output layout

```
Renders/Showcase/<item>/<item>_<shot>.png        3200x1800 masters
Renders/Showcase/_pack/<piece>.png               grid, kit, scale, LOD, wire, collision, triptych, contents
WorkFiles/showcase/<item>/diag/                  masks, yaw sweeps, calib frames — never shipped
WorkFiles/showcase/<item>/<sheet>.labels.json    every label with its JSON pointer
WorkFiles/showcase/showcase_manifest.json        fingerprints, per-shot seconds, gate results
Exports/Fab/<Pack>/gallery/NN_<name>.jpg         the listing set, numbered in display order
Exports/Fab/<Pack>/thumbnail.jpg                 1920x1080 16:9, no overlay
Exports/Fab/<Pack>/MEDIA_MANIFEST.json
Exports/Fab/<Pack>/TECHNICAL_REFERENCE.pdf
```

---

## 8. What cannot be shot today, and the smallest thing that unlocks it

| Cannot shoot | Blocked by | Smallest unlock | Recommendation |
|---|---|---|---|
| An in-engine material shot | MEASURED, `known_gaps`: *"The Unreal side has no M_Shuriken_Master or M_Kunai_Wrap asset yet (pack-wide)... both slots bind to WorldGridMaterial"* | Build `M_Shuriken_Master` + `MI_` per form in the validation project (~1 session) | **Do it before the listing.** Cheapest remaining trust win in the project, and it is upstream of every image here. Until then the material board shows the shipped PNGs only and the description says plainly what is and is not included |
| A shipped-lightmap claim | UV1 is import-generated, not in the FBX | none needed | Disclose at the same type size as the claim (section 6.1) |
| The fan's states strip | Articulation undecided; the fan is queued shape-only | Decide the mechanism before the fan build starts | Decide first; it swings the fan's showcase cost about 3x |
| The tag's backlit transmission shot | The shipped material is opaque two-sided | A translucent preview MI | **Drop the shot.** Faking transmission on an opaque material is exactly the untrue marketing image the house rules forbid |
| In-hand, scale-beside-a-human, worn kasa | No attach point, no grip pose, and the only production-grade character is Epic's Manny — display-only under EULA 6(a) / DA 3(f)(ii) | A drawn 1.8 m height line and a 100 mm bar at the panel's own px/mm (~2 h, in Blender, zero IP) | Use the drawn rule. Revisit a real character for listing two |
| Stuck-in-wood, in-flight with a trail | No `ANinjaProjectile`, no stick-on-impact actor, no attach point; MRQ is not even enabled in `DemoGame_1.uproject` | ~3–4 sessions of gameplay work the game wants anyway | **Listing two.** These are the two best shots a thrown weapon can have and they are worth building — after the pack has revenue |
| Smoke, trail ribbon, impact decal | Those systems do not ship with the pack | — | **Never show them.** If the VFX is not in the download it is not in the media |
| Any fire or lit fuse | `FAB_ASSET_STUDY.md` 6: automated Mature flags on fire VFX, appeals denied | — | **Banned outright.** A bot-applied Mature rating on a $19.99 pack is a search-placement death sentence |
| A turntable video | 20–30 min of Cycles per pass | — | Skip for listing one; the auto-converted 3D preview does most of the job free |

---

## 9. Order of work and cost

### 9.1 Render cost

**MEASURED** on this machine (RTX 4070 SUPER, OPTIX, Cycles), from
`WorkFiles/kunai/plain_build/build_pack_final.log` and `WorkFiles/paperbomb/full_build.log`, by differencing the
`Saved:` timestamps:

| Frame | 1600x900 | Samples |
|---|---|---|
| steel beauty (persp / top) | **5.1 s** | 220 |
| steel mask pass | **2.3 s** | 18 |
| grind panel (one of three) | **2.2 s** | 220 |
| wire | **0.58 s** | flat emission |
| LOD strip | **0.67 s** | flat emission |
| paper beauty | **9.5 s** | 320 |
| paper wire / lods | **6.1 s / 6.0 s** | flat |
| whole 7-form pack build, incl. bakes, export, QA | **328.81 s** | `pack_report.json` |

**ESTIMATE** at 3200x1800 = 4x the pixels, scaled linearly (±30 %; nothing was rendered this pass):

| Per item | Frames | Time |
|---|---|---|
| steel star / bar / plate | 5 beauty + wire + lods + 1 grind panel-frame + collision + 5 masks @1600 + yaw solve | **~2.5 min** |
| kunai | + 1 detail | **~2.8 min** |
| paper tag | 6 beauty @ ~38 s + flats + relief diagnostic pair | **~5.5 min** |
| folding fan | + states panel + back flat | **~5.5 min** |
| kasa | + interior | **~4 min** |
| smoke bomb | 2 details, no back | **~3 min** |
| **pack boards** | grid 1 frame ~60 s, kit ~60 s, scale ~40 s; the rest are OIIO composites (seconds) | **~3 min** |

| Scenario | Time |
|---|---|
| Cold eleven-item regeneration | **~37 min** GPU, unattended |
| One item changed (cache hit on the rest) | **3–6 min** |
| Presentation-only iteration (caption, yaw, encode) | **< 1 min** |
| First full run, while the new gates are being tuned | **budget 3–4 h** — the gates will fail and you will re-render |
| Dev attention per build | **~30 s** — one contact sheet with PASS/FAIL badges |

The grind change alone (3 full frames → 1 panel frame) saves ~18 s per item, ~3 min per cold rebuild. The
fingerprint cache turns the normal case from 37 min into 5.

### 9.2 Engineering cost

ESTIMATE, one person, ~40 h ≈ eight to ten evenings. Staged so the first 5 h already ship something.

| Stage | Work | Hours | Delivers |
|---|---|---|---|
| **0** | `manifest.py`: fingerprints, `showcase_manifest.json`, `--check`, orphan detection — over the **existing** renders | 2 | No visual change; kills the stale-image class of bug immediately |
| **1** | `encode.py` + the Fab packer: OIIO downsample, JPEG bisect, thumbnail, budget assert, `MEDIA_MANIFEST.json` | 3 | **The gallery becomes uploadable at all** |
| **2** | `rig.py` + `profile.py`: extract the shared rig, `SPEC` / `PAPER` profiles, both call sites switched, regression run on the seven steel forms | 6 | `props_lib/render.py`'s hand-copy is deleted; item twelve stops being a third copy |
| **3** | 3200x1800 masters, gates on the exact 2:1 downsample, `panels.py` | 3 | Fab-legal resolution with zero gate retuning |
| **4** | Anchor move to the spec shot, yaw solver, foreshortening / coverage / contrast gates, re-derive the four anchors on one clean frozen-map build | 5 | **The kunai gets its real hero** |
| **5** | The three new per-item shots: `edge`, `detail_*` with the anchor rule, `collision` | 5 | The shots the pack has never had |
| **6** | `boards.py`: thumbnail, grid, kit, scale, LOD, wire, collision, triptych, contents; retire `line_sheet.py` | 8 | The pack-level gallery |
| **7** | `labels.py` pointer contract + the re-parse check + the conditional engine block | 3 | Every claim checkable, mechanically |
| **8** | Class recipes for `card` / `articulated` / `hollow` / `round` + a one-page onboarding note | 5 | The tag, fan, hat and smoke bomb fit the system |
| | **Total** | **40** | |
| | **Core (0–4)** | **19** | A proven per-item package + uploadable delivery |
| | **Per new item thereafter** | **15 min** | Write the `ShowcaseSpec`; 0–45 min more only if it is a new shape class |

### 9.3 The pilot

**Item: the four-point.** It is the pack's anchor form, it is frozen, it carries the full gate set, it renders in
~2.5 min, and its coverage (0.1593) and separation (0.005) sit exactly at the two values the new gates are meant
to move. The pilot is done when:

1. `four_point_spec.png` renders at 3200x1800 and every existing gate passes on the 2:1 downsample **unchanged**.
   If any threshold has to move, stop — the 2x premise is wrong and the whole resolution plan needs rethinking.
2. `four_point_hero.png` renders under `SALES` and `WALL_GATE`, `FACET_GATE` and `BAR_WALL_DOT_GATE` **all
   still pass**. This is the single highest-probability technical failure in the plan and it is tested first.
3. `silhouette_contrast` measures ≥ 0.15 (baseline 0.005) and `coverage` ≥ 0.15.
4. One JPEG lands under 2.6 MB at 3200x1800 and is exactly 16:9.

**Second pilot: the kunai**, because it is the one item whose hero must actually change, and because its measured
coverage floor (currently 0.0595) is the number the plan most needs confirmed rather than assumed.

---

## 10. Queue placement

The queue is: **paper bomb → folding fan → smoke bomb → black hat → showcase.** Do not run the showcase as one
block at the end. Split it, because most of the work is not Blender work and the fan / smoke bomb / hat builds
will own the machine for days at a time.

| Phase | When | What | Machine |
|---|---|---|---|
| **A** | Right after the paper bomb lands, before the fan starts | Stages 0–4 (19 h) + the four-point and kunai pilots | Needs Blender for ~1 day; run it in the gap between two builds |
| **B** | **In parallel with** the fan, smoke bomb and hat builds | Stages 5–8 (21 h). `boards.py`, `labels.py` and the class recipes are OIIO, JSON and layout work — almost no rendering | Almost none; short pilot renders only |
| **C** | After the black hat | One cold regeneration (~37 min), gallery assembly, PDF, listing text | One unattended run |

**And a standing rule that stops this from ever becoming a catch-up job:** from the fan onward, **each item's
own build workflow writes its `ShowcaseSpec` as its last step** — 15 minutes, while its geometry and gates are
fresh in mind. The showcase never accumulates a backlog.

**Two things happen before phase A, and both are upstream of every image in this plan:**

- **Build `M_Shuriken_Master` + `MI_` instances** (section 8). One session. A gallery advertising 2K PBR over a
  package with no master material is the fastest refund an unknown seller can buy.
- **Settle the paper tag's reference provenance in writing** (section 10, decision 3).

**Resource note** (from the project's own working rules): only ~6 GB of RAM is free while the user's
UnrealEditor holds 11 GB, so never two Unreal commandlets at once; claim the asset lock before any `.blend`;
and subagents share one scratchpad directory, so scratch files need distinctive names.

---

## 11. Risks, and how each is checked

| # | Risk | Check |
|---|---|---|
| 1 | **The `SALES` backdrop sends the rim walls to ink** — a 0.9-metallic mirrors the world, and this is the exact failure the wall card was built to fix | `WALL_GATE` / `FACET_GATE` / `BAR_WALL_DOT_GATE` stay hard on the sales shots. **Tested at the pilot, on the four-point, before any board work.** If they fail, lift the backdrop until they pass |
| 2 | **The anchor move invalidates four frozen constants** (`PACK_ANCHOR`, `PACK_COAT_ANCHOR`, `PACK_WALL_ANCHOR`, `PACK_BACKDROP_ANCHOR`) | Re-derive from **one** clean rebuild on frozen maps, alone, never in the same build as a material change. Archive the old values with the reason. Diff |
| 3 | **Extracting the frozen rig changes shipped bytes.** `shuriken_lib/render.py` is explicitly frozen and six forms are byte-identical against it | Stage 2 ships only if a rebuild of the seven forms matches. **Note:** `WorkFiles/shuriken/regression/compare_frozen.py` classes gallery PNGs as *"informational; expected to differ run to run"*, so "byte-identical masters" is **not** an achievable gate — use a tolerance diff on the PNGs and keep byte-identity for blend / fbx / sidecar / report / textures, where the harness already passes |
| 4 | **The coverage floors turn out unreachable** | They are set at today's measured values and the primary gate is relative. If the kunai's diagonal pose measures 0.12, the floor becomes 0.12 and is recorded as measured |
| 5 | **Cache invalidation ships a stale image** | The fingerprint covers meshes, textures, spec, profile, module version, resolution, samples, Blender version and device. `--no-cache` forced on release builds. `--check` cheap enough to run every time |
| 6 | **The 25 MB gallery cap breaks if one board comes in heavy** | Ship 10 images, not 14. `encode.py` bisects quality and **hard-fails** on the set total |
| 7 | **The kit shot gets hand-tweaked and goes stale** | Its positions live in a data file read by the same script. If it cannot be generated, it is cut. No exceptions — one exception kills the rule |
| 8 | **The engine-verified badge renders for an unchecked build** | Conditional on `engine_check.status == "verified"` **and** `matches_this_build`, suppressed automatically, never by anyone remembering |
| 9 | **An image claim outlives the number behind it** (the kunai went 1,256 → 2,182 tris in library 3.10.1) | The pointer contract plus the numeric re-parse in `--check` |
| 10 | **Overlay text is distributed artwork drawn with a Windows system font.** MEASURED: `line_sheet.py` line 30 is `FONT = Path("C:/Windows/Fonts/arial.ttf")`, and `References/Fonts/` holds `MasaFont-Bold.ttf` and `YujiBoku-Regular.ttf` with **no licence file on disk** | Switch every overlay to an OFL face, record the licence file beside it, and record the font and its licence in `MEDIA_MANIFEST.json`. Five-minute fix, real exposure |
| 11 | **Fab's thumbnail auto-tagger is a black box**; a deliberately dark tile may tag worse than a bright one | After publishing, read back the tags Fab generated. If they are wrong, lift the key ~15 % and re-upload — but **batch it with another edit**, because a thumbnail change triggers re-review |
| 12 | **Regeneration is not free once the listing is live.** `FAB_ASSET_STUDY.md` 4.6: images, video, thumbnail, title and description each spawn a moderated duplicate while the original stays live | `--check` reports *which* images changed, so only those are republished, and media edits are batched into one re-review. Tags and 3D technical detail fields need **no** review, so tune those freely |
| 13 | **The class recipes for the fan, hat and smoke bomb are predictions from a one-line description** | Build and tune against the seven steel forms plus the tag first. Treat sections 5.2–5.5 as a checklist to confirm when each item actually lands, not as a specification |
| 14 | **At 30 items a full regeneration is ~90 min and someone starts skipping it** | The `--items` filter and the report-newer-than-render refusal both exist from day one, not retrofitted |
| 15 | **The 1080p-served-at-720p claim is two unanswered bug reports** (2024, 2026), marked unverified in the study | Rendering at 3200x1800 costs ~4x the pixels but only ~2.5 min per item, so it is a cheap hedge. But do **not** let it justify text below the 45 px legibility rule on the assumption it will be served at full size |

---

## 12. Decisions the user should make

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | **The kunai's hero pose** | Keep the end-on yaw −25, or swap to the 3/4 diagonal (`kunai_plain_3q.png`, which already exists) | **Swap.** This has been flagged as open since the kunai landed. It requires moving the exposure anchor to the spec shot and re-deriving four anchors — about 5 h and one rebuild. It is the single biggest visible improvement in the plan |
| 2 | **The Unreal master material** | Build `M_Shuriken_Master` + `MI_` instances before the listing, or state plainly that maps and import settings ship and the master material does not | **Build it**, one session, before phase A. It is upstream of the material-proof board and of the buyer's first-open experience |
| 3 | **The paper tag's place in the media** | (a) thumbnail focal point and gallery hero, (b) present in the line-up but not the focal point, (c) held back from listing one | **(b).** The tag is the pack's only colour and genuinely the best image on disk, and `References/PaperBomb/sources.md` supports the layout as generic ofuda — shrine sizes, two-colour black-and-vermilion printing. But `REFERENCE_SPEC.md` matches "position, size, proportion, weight, colour and density… **and the silhouette**" to one supplied file, with only the strokes original. Search reads the thumbnail, so making a vermillion-and-black tag the tile's focal point is how a franchise-adjacent design gets found by the people most likely to report it. Put the provenance reasoning in writing first; the same release-time decision already exists for the kunai (`KUNAI_STUDY.md` 1: *"the user's accepted risk, decided at release"*) |
| 4 | **Master resolution** | 3200x1800 (exact 2x) or 3840x2160 | **3200x1800.** Clears Fab's floor with zero gate retuning and zero anchor rescaling; 2.4x would force both, for pixels Fab's downscale discards |
| 5 | **Fan articulation** | One static mesh · separate meshes per state · shape key · rib bone chain | **Decide before the fan build starts.** It swings the fan's showcase cost about 3x. If it ships one state, the states strip is not built and the description says one state — no exceptions |
| 6 | **Video for listing one** | Ship a turntable, or skip | **Skip.** 20–30 min of Cycles per pass, and the auto-converted 3D preview covers most of it. Revisit when the pack has sold something |
| 7 | **Price** | $9.99–$59.99 is the band for weapon packs (`FAB_ASSET_STUDY.md` 6) | **$19.99 Personal / $39.99 Professional**, matching the study's product-1 row. This sets the budget: at $19.99 a 40 h showcase is defensible only because it is reusable across every future listing |
| 8 | **Overlay font** | Keep `C:/Windows/Fonts/arial.ttf`, or switch to an OFL face | **Switch**, and put a licence file next to it. Five minutes, and these images are distributed |
| 9 | **Listing scope** | Ship 8 items now (7 steel + tag), or wait for all 11 | **Wait for 11** if the fan, smoke bomb and hat stay on schedule — a kit of knives, a tag, a fan and a hat reads as a *ninja kit* rather than "some knives", and that is worth more on the tile than three months of earlier revenue. But the system is built so that 8 is shippable at any point, which is the real insurance |
| 10 | **Listing text budget** | Unbudgeted in every proposal | **Budget 4–6 h** for the title (≤ 30 chars), description, every tag slot and every structured technical field. `FAB_ASSET_STUDY.md` 4.6: tags and 3D technical detail fields need **no** re-review, so they can be tuned freely after publish — that makes them the highest-leverage hours in the whole project, and higher-leverage than the ninth gallery image |

---

## 13. One free test nobody has run

Before writing a line of rig code: open Fab's Weapons category, screenshot the grid at the size a buyer actually
browses, and paste each candidate thumbnail in at 300 px among 24 real competitor tiles. Twenty minutes, zero
cost, and it answers the one question the whole plan is guessing at — whether a dark tile stands out or
disappears in *that particular grid*. `thumb_blob_count` is a good mechanical proxy and should still exist, but
it is a proxy. The competitive context is data, and it is free.

---

## 14. Sources

Everything measured this pass, with the file it came from:

- `WorkFiles/shuriken/{four_point,eight_point,six_point,square_plate,spike,hooked_cross,kunai_plain}_report.json`
  — `render_stats`, `render_rig`, `render_gates`, `lod_switching`, `physics`, `sockets`, `known_gaps`,
  `engine_check`, `gallery`
- `WorkFiles/shuriken/pack_report.json` — 328.81 s whole-pack build, `pack_consistency` rules
- `WorkFiles/paperbomb/paperbomb_report.json` — tag geometry, atlas, collision, sockets, gates
- `WorkFiles/kunai/plain_build/build_pack_final.log`, `WorkFiles/paperbomb/full_build.log` — per-frame times
- `Renders/Shuriken/*.png`, `Renders/PaperBomb/*.png` — the 49-file dimension and size audit
- `Scripts/shuriken/shuriken_lib/render.py`, `Scripts/shuriken/line_sheet.py`,
  `Scripts/props/props_lib/{render,gallery}.py` — constants, gates, the duplicated rig, the font path
- `FAB_ASSET_STUDY.md` 4.4 / 4.5 / 4.6 / 6 — formats, media limits, review cost, market and price bands
- `ASSET_GUIDELINES.md` 3 / 4 / 6 / 11 — texture, UV, export and marketplace house rules
- `References/PaperBomb/{REFERENCE_SPEC.md,sources.md}`, `References/BlackHat/provenance.json`,
  `References/Kunai/KUNAI_STUDY.md` — reference provenance and the existing release-time IP decisions
