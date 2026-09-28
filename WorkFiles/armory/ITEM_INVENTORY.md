# Armory: item inventory (what every display must hold)

**Date:** 2026-09-26. **Role:** inventory, planning only. Nothing was modelled, rendered, imported or built, and no
project file outside `WorkFiles/armory/` was changed.
**Sources read:** every item's `Exports/<Item>/` folder, `*.sockets.json` / `*.skeletal.json` sidecars, READMEs, and
the build reports (`WorkFiles/shuriken/*_report.json`, `WorkFiles/kunai/KUNAI_PLAIN_REPORT.md`,
`WorkFiles/smokebomb/SMOKEBOMB_REPORT.md` + json, `WorkFiles/blackhat/BLACKHAT_REPORT.md` + json,
`WorkFiles/fan/FAN_REPORT.md`, `Exports/Fan/README.md`, `WorkFiles/paperbomb/PAPERBOMB_REPORT.md` header,
`Exports/PaperBomb/README.txt`, `WorkFiles/SnowFlower/v4/sword_report.json` + `SWORD_AUDIT.md`,
`References/SnowFlower/SHEATH_REFERENCE_SPEC.md` + `SHEATH_STUDY.md`, `Exports/BlackCloak/README.md` +
`asset_report.json` + `RECOLOR.md`, `WorkFiles/materials/MATERIALS_REPORT.md`), plus the heels reference image.

**Status labels.** MEASURED means the value was measured on the shipped mesh by its build. DESIGNED means a
decided value in the item's spec. ESTIMATE means the value has no build behind it yet. Where an item is still being
built, its numbers are the spec's, and the display must be re-fitted once the item ships.

**Frames.** Every static prop exports with the pipeline's axis convention (sidecar `axis`: forward -Y, up Z).
Socket locations are in cm in the item's own frame, as their sidecars give them. Unreal 5.8.2 drops FBX sockets
from a LodGroup file, so a display that snaps to a socket must use the pack's imported assets
(`/Game/NinjaPack/...`), where the sockets were recreated from the sidecars. The raw FBX will not have them.

---

## 1. Summary

| # | Item | Kind | Size (cm, W x D x H or L) | Mass | Status | Display in one line |
|---|---|---|---|---|---|---|
| 1 | Shuriken, four-point (juji) | static | 9.7 across, 0.30 thick | 33 g | done | flat, face-up, on a slotted tray or angled board |
| 2 | Shuriken, eight-point (happo) | static | 10.0 across, 0.25 thick | 54 g | done | flat, as above |
| 3 | Shuriken, senban (square plate) | static | 7.62 side, 10.78 corner to corner, 0.19 thick | 63 g | done | flat, as above |
| 4 | Shuriken, six-point (roppo) | static | 9.8 x 8.49, 0.20 thick | 36 g | done | flat, as above |
| 5 | Spike (bo-shuriken) | static | 15.0 long, 0.6 stock | 35 g | done | lying in a fitted groove, or a fan of spikes in a rack |
| 6 | Hooked cross | static | 8.46 x 8.46, 0.25 thick | 34 g | done | flat, face-up. **Never mirrored** |
| 7 | Plain kunai | static | 28.0 x 3.6 x 2.0 | 162 g | done; blade-section rework queued | hung by its ring, or on a two-peg rack; pairs with the paper bomb |
| 8 | Smoke bomb | static | 7.0 ball (7.00 x 7.03 x 7.13) | 121 g | done (accepted as-is) | in a cradle ring or a shallow dish. It rolls |
| 9 | Black hat (kasa) | static | 60.3 x 61.7 x 23.9 | 300 g | done | on a head form via the HEAD socket |
| 10 | Folding fan (+ tassel) | **skeletal**, animated | open 37.3 x 21.0 x 1.6; closed 21.0 x 1.6 x 1.6 | 22 g + 3 g | done | on a fan stand, opening and closing |
| 11 | Paper bomb (tag) | static | 16.2 x 7.0 x 1.24 | 0.9 g | exported; exact pass queued | pinned face-out, or tied to the kunai's ring |
| 12 | Snow Flower sword, v4 | static | 11.8 x 6.2 x 125.6 | not recorded | **being rebuilt** (v4 exported, verifying) | on a sword stand, drawn and sheathed |
| 13 | Snow Flower sheath | static | 10.1 x 2.2 x 100.8 (DESIGNED) | 0.7 kg (ESTIMATE) | **not built yet** | on the same stand; Holster + BeltMount sockets |
| 14 | Snow Flower heels (pair) | **skeletal**, worn (MH_PlayerFemale) | about 24-26 L, 10-11 heel (ESTIMATE) | not recorded | **queued, not started** | as a pair on a plinth, or worn on a female form |
| 15 | Black cloak | static + optional rigid skeletal | 103.2 x 67.8 x 172.1 | not recorded | made elsewhere; **review queued** | on a full-height mannequin or shoulder form |

**Scale spread.** The items run from 1.9 mm thick (senban) to 1.72 m tall (cloak), and from 0.9 g to about 1 kg.
The room therefore needs at least three display scales:

| Scale | Items | Typical fixture |
|---|---|---|
| **Small (under 30 cm)** | the six throwing stars, spike, kunai, smoke bomb, paper bomb, closed fan | trays, cases, wall boards, pedestals at eye height (100-140 cm) |
| **Medium (30-130 cm)** | open fan, hat, sword, sheath, heels on a plinth | stands, head forms, plinths, sword racks |
| **Large (over 130 cm)** | cloak, and any worn outfit (hat + cloak + heels on one figure) | full-height mannequins, alcoves |

**Pack LOD rule (it matters for the room).** Every pack prop switches to LOD1 at about **0.89 m** and to LOD2 at
about **2.54 m** (16:9, 90 degree horizontal FOV; `S = 1.778 R / d`). Measured: stars 0.86-0.89 / 2.46-2.54 m, smoke bomb 0.89 /
2.54 m, hat 0.89 / 2.54 m. A visitor standing 1-2 m from a case sees LOD1. Hero shots need the camera within 0.9 m,
or a forced LOD on the display's components for the shot.

**Nanite.** Off on every item (hand-authored LODs; the fan is skeletal). The display pieces themselves may use Nanite
(see `ASSET_GUIDELINES.md` and `FAB_ASSET_STUDY.md` for that decision).

---

## 2. Material families (the environment must sit beside these)

| Master (pack, `Scripts/unreal/materials/`) | Items and buyer instances | Recolour |
|---|---|---|
| `M_Steel_Master` | six stars + spike (`MI_Shuriken_<Form>_Steel`); kunai blade (`MI_Kunai_Plain_Steel`); fan rivet (`MI_Fan_Rivet`) | Steel Tint (a multiplier) only; rivet not tintable |
| `M_Fabric_Master` | kunai wrap `MI_Kunai_Plain_Wrap` (`#373532`); smoke bomb `MI_SmokeBomb_Cloth` (`#3F3A37`); hat `MI_BlackHat_Straw` (`#3F3C3B`) and `MI_BlackHat_Cloth` (`#383737`); fan `MI_Fan_Leaf` (`#272B30`), `MI_Fan_Ribs` (`#212628`), `MI_Fan_Tassel` (`#14181F`) | Colour = the part's mean colour; Lightest Colour cap; black lifted to about `#191919` |
| `M_PaperInk_Master` | paper bomb `MI_PaperBomb_Tag` | Paper `#F3E3C3`, Black Ink `#0F0F0E`, Red Ink `#D5180B` |
| **Not yet in the pack system** | Snow Flower v4 (`M_SnowFlower_Steel` 4096, `M_SnowFlower_Wrap` 2048 with a Detail map; "joins the pack materials" is planned); sheath (planned); heels (planned); cloak (its own `M_Cloak_Recolor` with CloakColor, plus `M_Cloak_BlackenedSteel` and `M_Cloak_CharcoalLeather`) | per item |

**What this means for the room.** Almost everything is **near-black**: black straw, blue-black silk, dark cotton
tape, black leather, black lacquer, black wool. The bright exceptions are the steel (stars, spike, kunai blade, Snow
Flower blade and silver fittings), the paper bomb's cream paper and vermilion ink, and the fan's polished rivet. The
backgrounds, shelves and case linings must therefore **not** be black or dark brown behind the black items. A
mid-value warm neutral (pale wood, plaster, tatami, pale linen) keeps their silhouettes, and the steel needs something
to reflect (a soft rim light or a bright card). This is also the showcase's lesson: a near-black studio made the fan
rivet read grey (`FAN_REPORT.md` gap 5).

---

## 3. Per-item records

### 3.1 The throwing stars (shuriken pack, six forms)

Common to all six:
- **Exports:** `Exports/Shuriken/SM_Shuriken_<Form>.fbx` + `.sockets.json`; textures `Exports/Shuriken/Textures/`
  (BC / ORM / N, 2048). Pack assets under `/Game/NinjaPack/Meshes/`.
- **Frame and pivot:** the plate lies in the XY plane, thickness along Z, the **presented face +Z**. The origin is
  the centre (the hole's centre on the holed forms); the `Trail` socket sits on it.
- **Sockets:** `Grip` (on an arm, at the finger hold) and `Trail` (the centre, for a spin trail).
- **Material:** one slot, `M_Steel_Master` → `MI_Shuriken_<Form>_Steel`. Not recolourable except Steel Tint.
- **Collision:** one convex hull (UCX). **Mass override** is not carried by the FBX (set on the Body Instance).
- **Status:** all six done, frozen by regression (78 of 78 files), Unreal-verified.

| Form (mesh) | Size (MEASURED) | Thickness | Hole | Mass (finished) | LOD0 / 1 / 2 tris | Grip socket (cm) |
|---|---|---|---|---|---|---|
| Four-point `SM_Shuriken_FourPoint` | 9.70 across | 3.0 mm | 8.0 mm round | 32.6 g (0.033 kg) | 1,232 / 592 / 232 | (0.78, -0.78, 0), yaw -45 |
| Eight-point `SM_Shuriken_EightPoint` | 10.0 across | 2.5 mm | 9.5 mm round | 53.8 g (0.054 kg) | 1,536 / 672 / 240 | (2.03, -0.84, 0), yaw -22.5 |
| Senban `SM_Shuriken_SquarePlate` | 7.62 side (concave arcs), 10.78 corner to corner | 1.9 mm | 12.7 mm square | 63.4 g (0.063 kg) | 1,344 / 576 / 128 | (2.27, -2.27, 0), yaw -45 |
| Six-point `SM_Shuriken_SixPoint` | 9.80 tip to tip x 8.49 | 2.0 mm | 8.0 mm round | 35.8 g (0.036 kg) | 1,320 / 576 / 228 | (1.56, -0.90, 0), yaw -30 |
| Hooked cross `SM_Shuriken_HookedCross` | 8.46 x 8.46 (tips on a 10.0 circle) | 2.5 mm | none | 34.2 g (0.034 kg) | 1,760 / 784 / 216 | (0.55, -0.55, 0), yaw -45 |

**How to show them.** Flat, presented face up or out, on a tray, a slotted board or an angled lectern-style case so
the knife grind (35 degrees, 0.15 mm land) catches a light. Each is 8-11 cm, so a star set reads best as a grid of
equal cells (about 14 x 14 cm each, one star per cell) with a small label plate. The stars are only 2-3 mm thick: a
fitted recess or two small pins at the rim hold one upright on a wall board; set them with a slight tilt toward the
viewer (15-30 degrees) so the grind reads.

**Display must:**
- **Never mirror the hooked cross** (no negative scale, no mirrored duplicate, no "flip" when laying out a symmetric
  wall). Mirroring it produces a forbidden symbol. Its handedness is fixed: presented face +Z, the +X arm hooks toward
  +Y. Rotating it in plane is fine.
- Show the senban's thin concave-sided plate edge-lit: at 1.9 mm it disappears side-on.
- Keep a clean, even, mid-value background under steel: the grind is the detail.
- Optional motion: a star can spin slowly about Z on a turntable using `Trail` as the centre (it is the origin).

### 3.2 Spike (bo-shuriken) `SM_Shuriken_Spike`

- **Size:** 15.0 cm long, 6 mm square stock, a 25 mm point, a 20 mm tail taper (MEASURED). **Mass** 35.3 g (0.0353 kg).
- **Pivot:** the centre of mass (4.1 mm toward the butt from the middle). Long axis +X, the point toward +X.
- **Sockets:** `Grip` (-3.09, 0, 0) cm and `Trail` (-7.09, 0, 0) cm (the butt).
- **LOD:** 92 / 60 / 28 tris. One slot, `MI_Shuriken_Spike_Steel`. Done.
- **How to show:** lying in a fitted groove on a tray, or several in a row in a wall rack (point up or angled). It is
  the one star-pack piece with a long axis, so it breaks up a grid of discs.

### 3.3 Plain kunai `SM_Kunai_Plain`

- **Size:** 28.0 cm overall (tip to ring end), 14.0 cm blade, 3.6 cm max blade width, 2.0 cm grip, ring 3.2 OD /
  2.0 ID cm (MEASURED). **Mass** 162 g assembled (0.1619 kg override); steel 149 g, wrap 13 g.
- **Pivot:** the mass-weighted centre, 15.1 mm inside the grip. +X toward the tip, +Z out of the lettering face.
- **Sockets:** `Tip` (16.05, 0, 0), `Grip` (-3.35, 0, 0), `Ring` (-10.35, 0, 0), `Trail` (-11.95, 0, 0) cm.
- **Materials:** 2 slots. Slot 0 steel `MI_Kunai_Plain_Steel`; slot 1 grip wrap `MI_Kunai_Plain_Wrap` (recolourable,
  `#373532`; preset `Presets/MI_Kunai_Plain_Wrap_Undyed`). A **blank 72 x 12 mm lettering band** on the grip's +Z face
  takes a 1536 x 256 mask (05 Lettering). **Center Of Mass Offset** (+3.06, 0, 0) cm on the Body Instance.
- **LOD:** 2,182 / 696 / 366 tris. Unreal-verified.
- **Status:** done and frozen; a **blade-section rework is queued** after the stop in the queue (not authorised yet).
  Plan the display for the current shape; the length and the sockets should not change, but re-check after the rework.
- **How to show:** hung point-down by its ring from a peg (the `Ring` socket is the hang point), laid across two pegs
  on a wall rack, or stuck point-first into a wooden post or target (the `Tip` socket gives the embed depth). A
  lettered example (the user's own text in the band) is a good close-up.
- **Display must:** show the +Z face if a lettered copy is used (that is where the band is).

### 3.4 Smoke bomb `SM_SmokeBomb`

- **Size:** 7.00 x 7.03 x 7.13 cm (MEASURED), a hand-wound cloth-tape ball with loose threads. **Mass** 121 g
  designed; physics 0.12 kg.
- **Pivot:** the ball's centre. **Sockets:** `Grip` and `Burst`, both at the centre (0, 0, 0). `Burst` is the smoke
  spawn point: spawn with ABSOLUTE rotation so smoke rises whatever the ball's orientation.
- **Material:** one slot, `M_Fabric_Master` → `MI_SmokeBomb_Cloth` (recolourable, `#3F3A37`). BC and Detail at 4096,
  ORM + N at 2048 (about 21-32 MiB).
- **LOD:** 16,108 / 2,952 / 1,406 tris. One convex hull. Unreal 19 of 19.
- **Status:** done; the user accepted it as-is (it is **not** indistinguishable from the reference, section 9 of its
  report). Its known weak spots: the top whorl, and a small crumpled pocket seen from the top and the back.
- **How to show:** it is a sphere, so it needs a **cradle** (a ring, a shallow dish, a small stand of three pegs), or
  a small pile of 3-5 in a basket or bowl (rotate each copy so no two show the same face). Face its **reference view**
  (the build's -Y front) toward the viewer and keep the top-down view away from the hero camera.
- **Optional:** a small idle smoke wisp from `Burst` for the showcase.

### 3.5 Black hat (kasa) `SM_BlackHat`

- **Size:** 60.3 x 61.7 x 23.9 cm (MEASURED). A 60 cm conical woven straw hat with a rolled rim, 26 lashings, 13
  ribs, a cloth band tied in a knot with **two torn tails that hang 9.2 cm below the rim**. **Mass** 300 g (designed).
- **Pivot:** on the axis at the bottom of the rim tube (z = 0).
- **Socket:** `HEAD` at (0, 0, 13.48) cm, rotation 0: where the top of a 57 cm head touches the inner cone. +Z up,
  +X forward, the knot on the wearer's left (+Y). Attach with SnapToTarget.
- **Materials:** 2 slots, both recolourable on `M_Fabric_Master`: straw `MI_BlackHat_Straw` (`#3F3C3B`) and cloth
  `MI_BlackHat_Cloth` (`#383737`). 8 maps at 2048. The cloth UV0 is in the second UV tile (keep Wrap addressing).
- **LOD:** 16,504 / 6,306 / 2,033 tris. One convex hull round the straw body; the hanging tails have **no collision**.
- **Status:** done (blind 19 of 20 after the surface pass; the user closed it). Unreal 20 of 20.
- **How to show:** **on a head form** (a stylised bust or a simple head-and-neck post sized to a 57 cm head
  circumference, about 18 cm head diameter), snapped at `HEAD`. It can also sit on a wide pedestal tilted forward, or
  hang on a wall peg, but the head form shows the knot and tails as worn.
- **Display must:**
  - give it a 70-80 cm wide bay (the brim is 60-62 cm);
  - leave at least 12 cm clear under the brim for the hanging tails;
  - face the knot side (+Y) and front (+X) toward the viewer;
  - not feature the underside: it is plain woven straw with **no headband ring, lining or chin cord** (an option for
    later, not built).

### 3.6 Folding fan (sensu) `SK_Fan` + `SK_Fan_Tassel`

- **Kind:** **skeletal**. 78 bones in Unreal (`root`, `pivot`, `stick_00..25`, `leaf_00..49`). The tassel is a
  separate skeletal mesh (6-bone chain) attached at the `Tassel` socket.
- **Size (MEASURED):** open **37.3 x 21.0 x 1.63 cm** (163.2 degrees); closed **21.0 x 1.64 x 1.55 cm**; stick length 19.0 cm.
  **Mass** 22 g, tassel 3 g.
- **Pivot:** the rivet at the origin, rivet axis +Z (the front), stick_00 (the held front guard) along +X, opening
  counter-clockwise.
- **Sockets:** `Grip` (stick_00, 40 mm above the butt; an ESTIMATE), `Pivot` (rivet axis), `Tassel` (back eyelet,
  (0, 0, -0.78) cm), `Tip` (stick_12 at the leaf edge).
- **Animation (60 fps):** `A_Fan_OpenClose` (1.3 s: open, hold, close; loops), `A_Fan_Openness` (0 = closed to
  1.0 s = fully open; **drive by time with a Sequence Evaluator, do not play it**), `A_Fan_OpenPose` (static open).
- **Materials:** leaf `MI_Fan_Leaf`, ribs `MI_Fan_Ribs` (FBX slot `M_Fan_Sticks`), tassel `MI_Fan_Tassel` (all
  `M_Fabric_Master`, recolourable), rivet `MI_Fan_Rivet` (polished metal, not tintable). Pack assets:
  `/Game/NinjaPack/Meshes/Fan/SK_Fan`.
- **LOD:** SK_Fan 5,572 / 2,720 / 1,320; tassel 1,384 / 384 / 76. No bones removed at any LOD.
- **Physics:** one body on `pivot` (a box round the closed handle, 22 g); **the open leaf has no collision**.
- **Status:** done (round 3; U1-U11 pass).
- **How to show:** on a **fan stand** (a small lacquered easel or cradle that holds the handle at the rivet and lets
  the leaf stand open), front (+Z) toward the viewer, tassel hanging. Best as a **living display**: closed at rest,
  opening as the player approaches (drive `A_Fan_Openness` from distance or an overlap), or looping
  `A_Fan_OpenClose` on a slow timer. A second, closed fan can lie beside it.
- **Display must:**
  - use the pack's `SK_Fan` with **DefaultRecorderBoneCompression** on the clips (ACL cracks the leaf) and the sidecar's
    `bounds_extension_cm` (the leaf swings 16 mm behind the rivet);
  - leave room to open: at least 40 cm wide and 23 cm tall above the rivet, plus clearance below for the tassel;
  - keep the hero camera **front-on or 45 degrees or steeper** across the leaf: from 25-30 degrees low across a
    partly open fan a few slits show at the leaf's inner edge;
  - hang the tassel with AnimDynamics (Chain, `tassel_root` → `skirt_02`) and make it ignore the fan's collision;
  - not show the back as a feature: it is plain black silk, with no ribs behind it;
  - light the rivet with a bright source (it reads grey in a near-black studio).

### 3.7 Paper bomb (explosive tag) `SM_PaperBomb`

- **Size:** 16.2 x 7.0 x 1.24 cm bounds; the card is 7.0 x 16.23 cm and 0.15 mm thick, with a curl and two creases
  in the geometry (MEASURED). **Mass** 0.9 g (0.001 kg override).
- **Pivot:** the card's centre, on its face.
- **Sockets:** `Face` (0.0008, 0, 0.0075) cm: decal and glow anchor on the printed face. `Attach` (-0.0008, 0,
  -0.0075), roll 180: stick it to a wall or crate, or parent it to a kunai. `Fuse` (4.92, 0, -0.33): spark and burn
  start. `Cord` (8.10, 0, -0.40): **ties to the kunai's `Ring` socket**.
- **Material:** one slot, `M_PaperInk_Master` → `MI_PaperBomb_Tag`, 3 colours (paper `#F3E3C3`, black ink, red ink).
  The M map's G channel is a **burn order** (0 at the fuse) for a burn effect; B is the ink mask.
- **LOD:** 1,132 / 428 / 172 tris. One convex hull (16 vertices).
- **Status:** exported and in the pack, but the art is recorded as **paused**; an **exact pass is queued** after the
  stop in the queue. The card size changed once already (70 x 156 → 70 x 162.3 mm), so plan a fitting with 1 cm of
  slack.
- **How to show:** pinned **face out** on a board or a post (via `Attach`), several in a fan as a "wall of tags", or
  **tied to a kunai's ring** (`Cord` → kunai `Ring`) with the kunai stuck in a post. That pairing is the strongest
  single read of the two items.
- **Display must:** show the printed face (the back shows only the ink's show-through); keep it off dark surfaces
  (cream paper, it is the brightest item in the set); optional burn VFX starts at `Fuse`.

### 3.8 Snow Flower sword, v4 `SM_SnowFlower`

- **Status: being rebuilt right now.** v4 was exported at 18:50 today (`Exports/SnowFlower/v4/SM_SnowFlower.fbx` +
  sidecar + 7 textures); its Unreal check was still running (`WorkFiles/SnowFlower/v4/UnrealCheck/`, pass 1 only).
  The rev-3 export (`Exports/SnowFlower/`, 456k triangles, tassel, 8 materials, no sockets) is superseded. The
  **tassel is removed** from the sword (user decision).
- **Size (v4, MEASURED by its build):** **11.8 x 6.24 x 125.6 cm** (bbox z -21.6 to +104.0 cm). The blade runs from
  `BladeBase` (12.85 cm) to `BladeTip` (104.0 cm): about 91 cm. The tip sweeps toward +X (BladeTip x = +3.18 cm).
- **Frame and pivot:** mm build frame, +Z along the blade, +X the spine, -Y the front; **origin = the Grip socket**.
- **Sockets:** `Grip` (0, 0, 0), `OffHand` (0, 0, -9.5), `BladeBase` (-0.43, 0, 12.85), `BladeTip` (3.18, 0, 104.0) cm.
- **Materials:** 2 slots, `M_SnowFlower_Steel` (4096; the blade, guard, pommel and silver ornament) and
  `M_SnowFlower_Wrap` (2048, near-black grip wrap with a Detail map for recolour). Joining the pack masters is planned.
- **LOD:** 19,386 / 7,883 / 2,650 tris; 4 convex hulls (blade, curved tip, guard, grip + pommel).
- **Mass:** **not recorded**. The sheath study's sabre sources (628-673 g for 68-71 cm blades) put a 91 cm blade near
  1 kg (ESTIMATE; for a physics override only, the display does not need it).
- **Open decision (from the audit):** the 1.256 m overall length is long for a one-handed dao and was to be
  confirmed against the player's height. The display should be sized with a margin (see 3.9).
- **How to show:** a sword stand with the ornament facing the viewer: the blossom relief, guard and pommel medallion
  are the hero details. The user asked for it both **sheathed and drawn**, which means either two actors (the
  sword drawn on the upper arms of a stand, the sheath below it) or one sword that draws on interaction (slide the
  sword out along the sheath's -Z from the `Holster` socket, then rest it on the stand).
- **Display must:** hold a 126 cm sword (a 135-140 cm long stand or rack); support it at the guard and near
  `BladeTip` minus 20-25 cm, not at the tip; present the -Y front.

### 3.9 Snow Flower sheath `SM_SnowFlower_Sheath` (planned name)

- **Status: not built yet.** The spec is `References/SnowFlower/SHEATH_REFERENCE_SPEC.md` (with machine twin
  `WorkFiles/SnowFlower/v4/sheath_spec.json`). No `SnowFlower_Sheath.blend` or sheath export exists yet. No tassel, no cord.
- **Size (DESIGNED at 0.687 mm per reference px):** **100.8 cm long**, 6.66 cm wide under the throat tapering to
  4.95 cm at the chape collar, **10.1 cm max at the throat's lateral plates**, 2.2 → 1.7 cm deep (a flattened
  octagon). Throat 9.4 cm long, chape 15.9 cm, one mid band (the belt mount) 18.8 cm below the mouth.
  (The sheath study's headline says 101.5 cm mouth to point and 2.0-2.4 cm thick: the same design, earlier numbers.)
- **Mass:** 0.5-0.9 kg; 0.7 kg for physics (ESTIMATE).
- **Sockets (DESIGNED):** `Holster` at the collar-top plane on the cavity axis, +Z out of the mouth, +X toward the
  blade's back edge; the sword's guard seat snaps here and the blade runs down -Z inside. `BeltMount` (the spec calls
  it `SOCKET_Hip`) at the mid band on the **back face** centre, +Z toward the mouth.
- **Materials:** dark marbled lacquer body, silver fittings (an eight-plate throat round a blossom, one blossom band,
  a pointed chape, one sinuous vine with three blossom clusters). Planned to join the pack masters.
- **Open user decision (spec 9.4):** the reference sheath is straight and the dao's tip is swept. The fit either
  keeps the blade's back edge straight, gives the sheath an 8 mm bow, or hides the blade while sheathed. It can change
  the sheath's shape slightly, not its length class.
- **Sheathed length (ESTIMATE):** the sheath plus the hilt above the collar, about 100.8 + 34 = **about 135 cm**.
- **How to show:** on the sword stand under the drawn sword, or with the sword sheathed in it; or hung by
  `BeltMount` on a wall peg or a belt on a mannequin. Blossoms are **on the front only**; the back is plain lacquer
  with plain rings, so the front must face the viewer.

### 3.10 Snow Flower heels (pair)

- **Status: queued, not started.** Reference `References/SnowFlowerHeels/snowflowerheels_reference.png` (the
  1254 x 1254 replacement; the `_OLD_superseded` file is not used). The heels wait for `MH_PlayerFemale` to be free
  (the other session's catwalk).
- **What it is (from the reference):** a pair (left and right) of black leather pointed pumps with an ankle strap and
  a blossom buckle, a stiletto heel wrapped in silver branch fittings, a silver vine with blossoms over the toe, a
  glossy black toe cap and a blossom-printed insole.
- **Kind:** **wearable skeletal** on `MH_PlayerFemale` (the 342-bone MetaHuman body in the CharacterLab project).
  They are modelled for her foot **posed in heels**, skinned to her foot and ball bones, and ship with a foot-pose
  correction (foot pitch, heel lift, a slight pelvis raise) so her animations stay grounded.
- **Size (ESTIMATE, from the reference proportions and an adult women's shoe):** about 24-26 cm long, a 10-11 cm
  heel, 15-18 cm tall at the heel counter. The real numbers come from her measured foot.
- **Materials (planned):** black leather (likely `M_Fabric_Master`, recolourable), silver fittings
  (`M_Steel_Master`), a glossy black toe cap (patent or lacquer: a gloss setting the masters may need), and the printed
  insole (a print mask). All are to join the colour system.
- **How to show:**
  - As a **pair on a low plinth or glass-topped pedestal** at 90-110 cm, three-quarter toward the viewer, as in the
    reference. Since the shoes are built in the heel pose, a static or reference-pose copy stands correctly on its own.
    Confirm this once they are built.
  - **Worn** on a female form (her posed body or a neutral mannequin with the same foot pose) in a full-height alcove.
- **Display must:** show both shoes (left and right are different meshes, never a mirrored copy of one); light the
  silver heel wrap and the toe vine; keep the insole print visible from a raised viewing angle.

### 3.11 Black cloak `BlackCloak` / `SM_BlackCloak` / `SK_BlackCloak`

- **Status:** made earlier by another agent (ChatGPT/Codex "Astra"), reference revision 2; **our review is queued**.
  Its own notes say the visual match is **not approved** (fine wrinkles, fabric look and the interpreted back are not
  certified) and that cloth simulation, collision and character fit are **untested**.
- **Size (MEASURED by its report):** **103.2 x 67.8 x 172.1 cm**, metres, Z-up, **ground-based origin**. It is modelled
  already draped around a body (asymmetric wings, a diagonal front leaf, a gathered left fall, a scarf collar, a ring
  clasp with a pin and a dark leather loop).
- **Kind:** static mesh (`BlackCloak.fbx` + LOD1/LOD2) **and** an optional skeletal version rigidly weighted to the
  **152-bone MakeHuman-based skeleton** shared with the JinMuWon character (collar on `neck01`, clasp on `clavicle.R`,
  the rest on `spine01`). It is not simulated cloth. It does **not** fit the MetaHuman bodies without a re-rig.
- **Materials:** 3 slots, `M_BlackCloak_WovenWool` (cloth; in Unreal `M_Cloak_Recolor`, parameter **CloakColor**, presets
  Black / Crimson / Navy / Ivory), `M_BlackCloak_BlackenedSteel` (clasp) and `M_BlackCloak_CharcoalLeather` (loop).
  2K maps, UV0 **tiles** (0.128 m repeat, not a bake atlas), no ORM. It sits **outside** the pack material system (its own
  Unreal project `Exports/BlackCloak/Unreal/BlackCloakRecolor.uproject`); the review decides whether to move it onto
  `M_Fabric_Master`.
- **LOD:** 84,612 / 47,088 / 25,646 tris (heavy for a garment; the review will decide).
- **Mass:** not recorded.
- **How to show:** on a **full-height mannequin or dress form** (a torso with shoulders and neck, about 170-180 cm
  tall), since the static mesh is already in its draped shape; a flat rack or hook would need a re-drape. Place the
  static mesh at the form's feet level (ground-based origin). A second choice: worn by the JinMuWon body (the skeleton it
  is weighted to) posed as a statue.
- **Display must:** allow about 110 x 80 cm of floor and 185 cm of height; **face the front to the viewer**, and put
  the back toward a wall until the review has checked the back (it is an interpretation); keep it off a black
  backdrop (it is near-black wool).

---

## 4. What the displays must do (checklist for the display-piece designer)

| Need | Items | Display piece |
|---|---|---|
| Hold flat, thin steel at an angle, face +Z | 6 stars, spike | slotted tray / angled board / case with recesses |
| **No mirroring** | hooked cross; heels (L and R are distinct) | layout rule, checked in the level |
| Hang by a ring or embed a tip | kunai (`Ring`, `Tip`) | wall pegs; a wooden post or target |
| Tie one item to another | paper bomb `Cord` → kunai `Ring` | a kunai-and-tag set on a post |
| Pin face-out | paper bomb (`Attach`) | board, post or wall |
| Stop a sphere rolling | smoke bomb | cradle ring, dish, basket |
| Sit on a head at a socket | hat (`HEAD`, 57 cm head) | head form / bust |
| **Animate** open and close | fan (`A_Fan_Openness`, `A_Fan_OpenClose`) | fan stand + a small display Blueprint (proximity or timer) |
| Hang a physics tassel | fan tassel (AnimDynamics) | clearance under the stand |
| **Drawn and sheathed** | Snow Flower sword + sheath (`Holster`, `BeltMount`) | a sword stand for two pieces, or a draw-on-interact Blueprint |
| Worn by a figure | hat, heels (MH_PlayerFemale), cloak (152-bone rig) | head form; female form or plinth; full mannequin |
| Show the front only | sheath (blossoms front only), cloak (interpreted back), fan (plain back), paper bomb (printed face), hat (plain underside) | orientation rule per piece |
| Optional VFX | smoke bomb (`Burst`), paper bomb (`Fuse` + burn order in M.G), stars (`Trail` spin) | display Blueprint hooks |

**Two different skeletons, one room.** The heels need the MetaHuman female body (342 bones); the cloak is weighted
to the MakeHuman-based 152-bone JinMuWon skeleton. A single "outfit mannequin" cannot wear both as skinned meshes
today. For display, a posed static mannequin with static copies of the worn items avoids the problem.

---

## 5. Designing for the growing line

The line keeps growing. Also on disk and **not** on this list: `Exports/BlackNunchucks/` (skeletal + static,
recolourable) and the JinMuWon character. Whether they belong in the armory is the user's call.

Proposed **display slot contract**, so a new item drops in without rebuilding the room:

| Field | Meaning |
|---|---|
| Size class | S (under 30 cm), M (30-130 cm), L (over 130 cm) → picks the fixture family |
| Mount | flat / standing / hanging / embedded / on a form / worn / animated |
| Anchor | which socket the fixture snaps to (every item already ships sockets in its sidecar) |
| Front | which axis faces the viewer, and what must not be shown |
| Handedness | may it be mirrored (no for the hooked cross and anything paired L/R) |
| Motion / VFX | none, or the clip / socket that drives it |
| Label | name, size, mass and material swatches from the item's report |

Each fixture family (star tray cell, peg rack, cradle, head form, fan stand, sword stand, plinth, mannequin) should
have **empty slots** built in: for example a star board with 8-12 cells for 6 stars, a sword stand with a second
tier, and at least one spare alcove at each size class.

---

## 6. Items still in progress (re-check before the display build)

| Item | State on 2026-09-26 | What could change for the display |
|---|---|---|
| Snow Flower sword v4 | exported, Unreal check running; lock `SnowFlower` held | length (1.256 m decision), sockets, materials joining the pack |
| Snow Flower sheath | spec only, not built; user decision on the tip fit open | slight bow, exact length (about 1.01 m), socket placement |
| Snow Flower heels | queued; waits for MH_PlayerFemale | real size, whether a static display copy ships |
| Black cloak | review queued; not approved visually | possible mesh, LOD and material changes; possible move to the pack masters |
| Paper bomb | exported; "exact pass" queued after the stop | small card-size or print changes |
| Plain kunai | done; blade-section rework queued after the stop | blade cross-section only (length and sockets expected to hold) |
