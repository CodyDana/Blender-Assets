# Kunai Asset Study

**Date:** 2026-09-19
**Status:** reference for modelling. Nothing built yet.

**Purpose.** Build-to numbers, construction and finish for a kunai added to the shuriken pack. The user chose the three-pronged "winged" look: a main blade with two side prongs at its base, a wrapped grip and a ring pommel. The seal lettering on the grip is franchise text and is not modelled; the grip gets a blank band for the user's own lettering. Flags as in `SHURIKEN_STUDY.md`: SOURCED = measured, with a URL. DERIVED = computed from sourced figures. ESTIMATE = a design choice. SNIPPET = search summary only. Companions: `sources.md` ([n] numbers) and `WorkFiles/kunai/study_calc/kunai_mass_check.py` with its `.json` (section 4 arithmetic) [95].

---

## 1. Summary

| Item | Value |
|---|---|
| Asset | `SM_Kunai`, built with the pack's library, look and pipeline |
| Form | Leaf main blade, two side prongs rooted at the fork, round wrapped grip, flat ring pommel |
| Build-to headline | 280 mm overall, 140 mm main blade, 100 mm prong span, 5 mm stock, about 190 g |
| Finish | Pack steel plus a cotton tape wrap |
| Lettering | Blank 72 x 12 mm band on the grip's +Z face, own texture |
| Fab status | Franchise-specific, licensed silhouette. The user's accepted risk, decided at release (section 6) |

Three facts shape the build. No source gives the prong length or angle; both are estimates that land the measured prong span. The historical kunai was a blunt iron tool of 36 to 48 cm, so the sharp grind and the 28 cm scale follow modern replicas. The grip is cloth over steel, so the pivot comes from a mass-weighted centre, not mesh volume.

---

## 2. The historical kunai, briefly

An Edo-period shinobi digging and climbing tool [5][13][16]. The earliest mention is a 1628 Hosokawa clan list [5]. The 1676 *Bansenshukai*, volume 18 (climbing tools), gives it as iron, 1 shaku 2 sun or 1 shaku 6 sun long, made like the hera-kunai (spatula kunai) [1][2]: 36.4 or 48.5 cm overall at 30.303 cm per shaku. Its illustration is described as a flat, elongated triangular scraper; the plate was not inspected [5][8].

| Size claim | Value | Source | Status |
|---|---|---|---|
| Bansenshukai, 1676 | 36.4 or 48.5 cm overall | [1][2] | Verified, two renderings agree |
| Koka tourism text, Shinobi no Sato Prara, FY2024 | 45 to 60 cm, loops on the handles | [13] | Verified |
| Bujinkan glossaries | sho-kunai about 18 cm, dai-kunai 35 to 48 cm | [21][22] | Verified as quoted, practitioner sites |
| JA Wikipedia, Togakushi museum | dai 13 to 15 cm, sho 8 to 10 cm | [11][12][17] | Verified as quoted, unclear what is measured |
| EN Wikipedia | blade 20 to 30 cm | [20] | Weak: cited to a popular web article |
| Shinobi hiden "big kunai" | 2 shaku 2 sun = 66.7 cm | [6][7] | Do not use: probably a fire-carrying tool |

The sources agree on a flat iron body, a pointed tip and mostly blunt side edges [15][16][20]. Museum and modern descriptions add a rear ring [12][13][15]; no Edo text is cited as showing it [6]. Tuck traces the leaf-blade dagger image to 20th-century books, from Fujita Seiko (1958) and Hatsumi Masaaki (1964) on [8]. Many unrelated makers produce it, so it is generic.

---

## 3. The winged three-prong design

The franchise design is a standard kunai blade with "two prongs flanking the standard single blade", a handle "thicker than normal" to carry an inscription, and a little more weight than a normal kunai [63]. The prongs flare "from the guard" [64]. No historical source shows side prongs.

| Feature | Origin | Treatment |
|---|---|---|
| Leaf main blade, pointed tip | Generic | Build |
| Two side prongs from the fork | Franchise | Build. The user's accepted Fab risk |
| Round wrapped grip | Generic | Build at 20 mm, next to the generic 19 mm grip [34] |
| Ring pommel | Generic | Build, as a flat ring in the same stock |
| Seal lettering on the grip | Franchise text | **Not modelled, not traced, not in any texture** |
| Blank lettering band | Ours | Build, for the user's own text |

Measured replicas fix the proportions (section 4). One mass-market model lists a 100 mm blade on 280 mm [35][38][50]; it probably measures from the prong fork and is not used.

---

## 4. Build-to table

Frame for every number: X along the long axis, +X toward the tip. Y across, in the blade plane. Z through the thickness. X = 0 is the fork plane, where the main blade, the prongs and the grip meet.

| Dimension | Build to | Sourced range | Status |
|---|---|---|---|
| Overall length, tip to ring end | **280 mm** | 276 to 300 mm [35][38][40][41][43][54][55] | SOURCED |
| Main blade, fork to tip | **140 mm** | 0.46 to 0.54 of overall; 140 mm on 276 mm [43] | DERIVED |
| Main blade max width | **36 mm**, 35 mm from the fork | 30.3 to 46.3 mm on 305 mm [24] | DERIVED: set mean 39.4 x 280/305 |
| Main blade width at the fork | **16 mm** | none | ESTIMATE |
| Blade section | **Shallow diamond**: flat faces from a centre ridge | modern diamond [26]; historical flat [11][12] | ESTIMATE, design choice |
| Ridge thickness | **5.0 mm** to the widest point, tapering to **1.6 mm** at 135 mm | 4.6 to 1.6 mm [24]; 5.1 mm at 12 in [32] | SOURCED range |
| Edge | **1.5 mm** shoulder, then 35° per side to a 0.15 mm land | pack recipe [89] | ESTIMATE |
| Prong root | **At the fork plane**, centre at Y = ±13 mm | "from the guard" [64] | SOURCED position, ESTIMATE offset |
| Prong length along its axis | **60 mm** | none | ESTIMATE |
| Prong angle off the main axis | **38°** | none | ESTIMATE |
| Prong root width | **14 mm**, tapering to the point | none | ESTIMATE |
| Prong span, tip to tip | **100 mm**; tips 47 mm forward of the fork | 0.32 to 0.41 x overall [43][48][51] | DERIVED |
| Prong section | Diamond, ridge 5.0 to 1.6 mm | none | ESTIMATE |
| Crotch, prong to blade | X 7, Y ±10 mm; V opening about 27°; fillet r 2 mm | none | DERIVED / ESTIMATE |
| Grip, wrapped length | **96 mm** (X -102 to -6), plus a 6 mm bare neck | handle about equal to blade [44][45][48] | DERIVED |
| Grip diameter over the wrap | **20 mm**, round | 19.1 mm generic [34]; "thicker than normal" [63] | DERIVED |
| Tang under the wrap | **16 x 5 mm**, hidden | none | ESTIMATE |
| Wrap | Flat cotton tape, 10 mm wide, 1 mm thick, 9 mm pitch, **10.7 turns** | cotton or fabric on replicas [38][40][42]; waxed cord [25] | ESTIMATE |
| Ring outer / inner diameter | **32 / 20 mm**, centre at X = -124 | inner 20 mm [33] | ID SOURCED, OD DERIVED |
| Ring section | **6 mm** radial x **5 mm** stock, edges rounded r 1 mm | none | DERIVED / ESTIMATE |
| Mass, assembled | **190 g** | 196 to 212 g for 28 cm replicas [35][38][40]; 290 g all-metal [41] | DERIVED |

**Cross-check.** Steel at 7.85 g/cm³, integrated on a 0.05 mm grid [95]:

| Part | Volume, ground | Mass |
|---|---|---|
| Main blade | 7,900 mm³ | 62.0 g |
| Two prongs | 2,203 mm³ | 17.3 g |
| Fork web | 1,344 mm³ | 10.5 g |
| Tang and neck | 8,215 mm³ | 64.5 g |
| Ring | 2,450 mm³ | 19.2 g |
| **Steel, ground** | **22,112 mm³** | **173.6 g** |
| Steel, un-ground (the pack's mass-gate basis) | 22,530 mm³ | 176.9 g |

The wrap is separate: an 18 mm wooden core at 0.6 to 0.8 g/cm³ is 10.0 to 13.4 g, the 1 mm tape shell 3.4 to 5.2 g. Assembled: **187 to 192 g**, 3 to 10% under the three comparable 28 cm replicas (196, 210, 212 g) [35][38][40], as expected for ground steel against display castings. Plan areas: main blade 2,958 mm², both prongs 910 mm², ring 490 mm². At the widest point the grind is 1.04 mm wide in plan, so the 0.7 mm polished band fills most of it, as on the senban's 1.25 mm grind.

**Honshu check.** A 179 x 41.5 mm leaf at 4.6 to 1.6 mm holds only about 117 g of steel, so about 110 g of that kunai's 227 g sits in its grip, ring and cord [24]. This build has the same heavy handle end: 84 g of tang and ring plus about 16 g of wrap. The Honshu balances 12.7 mm forward of its grip [24]; this build balances 12.6 mm inside the grip. Acceptable for a game prop.

---

## 5. Modelling notes

**Frame and symmetry.** Blade in the XY plane, +X toward the tip, +Z the presented face. Blender +X arrives as Unreal +X: the spike's sidecar puts its butt socket at -7.09 cm [93]. The steel body is mirror-symmetric about XZ and XY and, unlike the hooked cross, has no handedness, so Mirror modifiers are safe. Mirror the mesh, never the UVs: the baked wear needs unique islands. The wrap helix is chiral, so it stays procedural and unmirrored.

**Where the knife grind goes.**

| Edge | Treatment |
|---|---|
| Main blade, both edges, crotch to tip | Pack knife grind: 35° per side, 0.15 mm land, tip radius 0.075 mm |
| Prongs, inner and outer edges | Same grind, run out into the crotch and the shoulder with the 3.9.1 run-out taper [90] |
| Two crotch fillets | Cavity corners, as on the hooked cross: chamfer, grime and dish from the corner distance [90] |
| Fork rear shoulders | The stars' scallop treatment: 0.45 mm chamfer plus wall |
| Centre ridge, blade and prongs | Coat. A 152 to 169° edge, not a grind line (the spike's 3.8.1 lesson) [90] |
| Neck and ring | 0.5 to 1.0 mm round, worn satin, no grind |
| Three tips | Polished over the last 2.5 mm. Review against the spike's 10 mm |

**Pivot at the centre of mass.** The origin goes on the long axis at the **mass-weighted** centre, X = -18.6 mm, 12.6 mm inside the grip: steel at 7.85 g/cm³, wrap at its own density. Do **not** run Origin to Center of Mass (Volume) on the joined mesh: it counts the grip as steel and lands at X = -34.8 mm, 16 mm too far back.

**Sockets.** Empties via `pipeline.make_socket`, restored after import from the `.sockets.json` sidecar [91]. Positions are from the fork plane; rewrite them relative to the pivot.

| Socket | Position | Axes | Use |
|---|---|---|---|
| `Grip` | Long axis, X = -54 mm, mid-grip | +X to the tip, +Z out of the lettering face | Hand attach, holster |
| `Trail` | Long axis, X = -140 mm, pommel end of the ring | +X to the tip | Ribbon or spark trail |
| `Tip`, optional | X = +140 mm | +X | Impact trace, stick-in-wall |
| `Ring`, optional | Ring centre, X = -124 mm | +X | Rope, or the queued paper tag |

**Throw.** Rotation Follows Velocity turns a projectile along its velocity every frame [80], so the +X tip flies point-first with no offset. For a spinning throw, spin a child mesh about the pivot, as the shuriken do [92].

**Collision.** Two convex hulls on the LOD0 node [88]: `UCX_SM_Kunai_LOD0_00` over the blade, prongs and web (10 to 16 vertices) and `UCX_SM_Kunai_LOD0_01` over the grip, neck and ring (12 to 20 vertices). One hull would make a fat wedge. `pipeline.make_ucx_hull` hulls a whole object, so split the vertex sets first. Unreal derives the body's centre of mass from the hulls: set Mass in KG to **0.19** and check the centre-of-mass offset against the pivot in-engine [87].

**LOD budget.** Project prop budget 1,000 to 5,000 triangles [91]. Winged kunai game assets exist at 558 and 960 triangles [71][72]; sold kunai run 450 to 3,600 [70].

| LOD | Screen size | Triangles | What changes |
|---|---|---|---|
| LOD0 | 1.0 | 1,600 to 2,800 | Full outline, diamond, grind, fillets, 24 x 8 ring, 16-sided grip |
| LOD1 | **0.28** | 650 to 1,100 | Half the outline and ring segments; grind as one facet |
| LOD2 | **0.098** | 220 to 400 | No grind; prongs and ring hole kept; 12 x 4 ring, 8-sided grip |

Screen sizes are the pack's 1.0 / 0.10 / 0.035 scaled by the bounds radius, 140 / 50 mm (`spec.scaled_lod_screen_sizes`), so the switches stay at about 0.89 m and 2.54 m. At 2.54 m the kunai is still about 106 px long at 1080p, so LOD2 keeps the silhouette and the ring hole (about 7.6 px).

**Texel density.** The pack runs 134 to 170 px/cm [96]. About 10,400 mm² of steel on a 2048 map at 55% packing gives about **150 px/cm**. The wrap unrolls to 96 x 62.8 mm: a 1024 map at about **107 px/cm**.

**Material setup, two slots.**

| Slot | Material | Maps | Recipe |
|---|---|---|---|
| Steel | Baked from the `M_Shuriken_Master` source | `T_Kunai_BC / _ORM / _N`, 2048 | Coat linear ~0.10, metallic 1.0, roughness 0.34; 0.7 mm polished band, satin grimy grind; soft smears, fine dark micro-scratches, faint pits, two rust specks at most, polished tips [89][90] |
| Wrap | `M_Kunai_Wrap`; `MI_Kunai_Wrap_Dark`, `_Natural` | `T_Kunai_Wrap_BC / _ORM / _N`, 1024; `T_Kunai_Lettering` | Metallic 0, roughness 0.85 to 0.9; dark default (linear ~0.03), undyed option (~0.40); tape edges and weave from a procedural helix height field, 0.3 to 0.5 mm, baked; grip-zone grime; frayed ends |

The second slot lets the user recolour the cloth and swap lettering without touching the steel maps. ORM packing and DirectX normals as in the rest of the pack.

**Lettering region.** A **72 x 12 mm** band on the grip's +Z face, X = -90 to -18 mm, 12 mm clear of each wrap end, about ±34° around the grip. It gets its own straight, unrolled UV0 island, light grime only, and its UV rectangle recorded in the build report. The wrap material remaps that rectangle to 0 to 1 and samples `T_Kunai_Lettering`: a single-channel ink mask at 6:1, shipped **blank** (for example 1536 x 256, about 21 px/mm). U runs from the ring end toward the blade; V toward +Y, seen from +Z. An optional -Z band reuses the texture. Ink follows the tape relief, as on a real wrap.

**Naming.** `SM_Kunai`; LODs `SM_Kunai_LOD0` to `_LOD2`; hulls `UCX_SM_Kunai_LOD0_00` and `_01`; sockets `SOCKET_SM_Kunai_LOD0_<Name>`; textures `T_Kunai_*`. If a plain kunai is ever added, rename to `SM_Kunai_ThreeProng` and `SM_Kunai_Plain` before release.

---

## 6. Franchise avoidance

**Names.** No franchise word in any object, collection, material, texture, socket, file, report or listing text. The pipeline's deny list catches "naruto" only [94]. Gate the rest in the kunai build script: minato, namikaze, hiraishin, flying thunder god, flying raijin, yondaime, hokage, yellow flash, konoha, shippuden, boruto. Retail listings use them freely [58][59].

**Lettering.** The seal text is not modelled, traced, sampled or approximated. `T_Kunai_Lettering` ships blank. If the user writes the franchise formula into it, the asset carries franchise text again: their call for their game, a blocker for Fab.

**Geometry references.** Build from section 4. Never trace fan-wiki images, replica photos or third-party 3D files [51][52][53][69].

**The silhouette is the Fab risk.** The three-prong head is the recognisable part, and it is actively licensed: an official ¥50,000 metal replica (Nijigen no Mori, 2026) [66][67] and a licensed foam "Tri Blade Kunai" [68]. On Fab, two franchise-named winged kunai listings return "Page not found" while a third is live [85]: inconsistent enforcement, not safety. The user accepted this risk and decides at release. A plain single-blade kunai from the same generator, prongs off, would be generic.

---

## 7. Open questions

1. Prong length, angle, root width and curve are ESTIMATES. Show the user the blockout silhouette before UVs.
2. Section: shallow diamond (modern) or flat (historical)?
3. Wrap: flat tape (chosen) or round cord? Dark or natural default? Lettering on +Z only or both faces?
4. Mass: 190 g derived against 196 to 212 g replicas. Accept, or thicken the stock?
5. Two part hulls need a vertex-subset step that `make_ucx_hull` lacks.
6. The Bansenshukai plate was never inspected for a ring.

---

## 8. Verification of high-stakes claims

Checked 2026-09-19 by WebFetch and WebSearch. Nothing was downloaded.

| Claim | Status | Checked against |
|---|---|---|
| Bansenshukai kunai: iron, 1 shaku 2 sun or 1 shaku 6 sun | **Verified** | Italian rendering [1] and Nakajima's Japanese text [2] agree. Tuck's "35 to 45 cm" [5] is low: 1 shaku 6 sun is 48.5 cm |
| Bansenshukai plate shows a flat triangular scraper | **Unconfirmed** | Tuck only [5][8]. [1] calls the hera-kunai "a conical digging tool" |
| Shinobi hiden 2 shaku 2 sun is a fire-carrying tool | **Verified, value corrected** | [7] and the 宮内 spelling [11]. It is 66.7 cm, not 68 cm |
| dai 13 to 15 cm, sho 8 to 10 cm | **Verified as quoted** | [11][12][17]. [11] and [12] share wording, so probably one source |
| Bujinkan: sho 18 cm, dai 35 to 48 cm, average 34 to 40 cm | **Verified as quoted** | [21][22] |
| Koka text: 45 to 60 cm, loops on handles | **Verified** | [13], which also calls kunai "trowel-like" |
| EN Wikipedia 20 to 30 cm blade, weakly cited | **Verified** | Cited to a vocal.media article [20]. Its trowel origin is cited to Turnbull (2003) p. 61, not left uncited |
| Edges mostly unsharpened | **Verified, contested** | [15][16][20]. Nakajima's commentary calls it double-edged [2] |
| Historical flat, modern diamond; one-piece body, cord wrap | **Verified** | [11][12] against [26]; [22][24][25] |
| Honshu: 12 in, 7 1/16 in blade, 4.6 to 1.6 mm, 30.3 to 46.3 mm, 3 1/4 in handle, 8 oz | **Verified** | [24]. [25] gives a 7 1/8 in edge and both 3Cr13 and 7Cr13 |
| Leones 26 cm 162 g; Ninja Store 290 x 50 mm 140 g zinc; Miki 4 mm blade | **Verified** | [27][28][29] |
| Forged kunai 12 in, 47.6 mm, 4.8 mm, 283 g | **Unconfirmed, SNIPPET** | [30] returned HTTP 403 |
| Research density check, about 195 g for the Honshu | **Disputed** | Its 30 mm mean width is too wide; a 41.5 mm leaf gives 117 g of blade |
| Prongs (rooted at the guard), thick handle, inscription are franchise features | **Verified** | [63][64]. No historical source shows prongs |
| No source gives prong angle or length | **Confirmed** | Also absent from [54][55] |
| Full size about 28 cm; main blade about 0.50 of it | **Verified** | [35][38][40][41][43][44][45][48]; new: [54] 292 mm and 0.46, [55] 30 cm |
| 100 mm blade on 280 mm is an outlier | **Verified** | [35][38][50] |
| Prong span 0.32 to 0.41 of overall | **Verified** | [43][48][51]. The hairpin charm [61] stays unconfirmed |
| Handle about equal to blade; stock 2.85 to 5.1 mm; ring inner 20 mm; grip 19 mm | **Verified** | [32][33][34][44][45][48]. The 12 mm thrower [43] is an outlier |
| Replica mass 196 to 290 g | **Verified** | [35][38][40][41] |
| Research mass target 220 to 260 g | **Disputed: 190 g** | This geometry at 5 mm stock gives 187 to 192 g |
| Origin at the centre of mass, hilt as a socket | **Unconfirmed** | Tutorial unreadable [79]; Epic's socket page confirms the attach-point use [78] |
| Rotation Follows Velocity | **Verified** | [80] |
| Balanced knife has its centre of mass at the centroid | **Verified, single source** | [23] |
