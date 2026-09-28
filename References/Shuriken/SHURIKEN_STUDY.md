# Shuriken Asset Study

**Date:** 2026-09-17
**Status:** reference for modelling. Nothing built yet.

**Purpose.** Shapes, dimensions, construction and finish of the shuriken forms worth modelling for a small pack, so modelling starts from measured numbers rather than from someone else's design. No mesh, material or Blender file exists yet; section 4 is a plan, not a build log. Status flags: SOURCED = a museum, school or retail figure with a URL. DERIVED = computed from a sourced outline and thickness at 7.85 g/cm³. ESTIMATE = no measured source. SNIPPET = seen only in a search summary of a page that could not be opened. Companions: `shuriken_reference_sheet.svg`, `sources.md`.

---

## 1. Summary and recommended variant set

Two families. **Hira-shuriken** (平手裏剣, flat plate), also **shaken** (車剣, wheel blade), are thin steel plates with three or more points and usually a centre hole. **Bo-shuriken** (棒手裏剣, stick) are straight spikes thrown point-first. Both are public domain. Section 5 lists what is not.

| Rank | Form | Asset name | Build-to headline | Why |
|---|---|---|---|---|
| 1 | Juji / shiho, 4 point | `SM_Shuriken_FourPoint` | 97 mm, 3.0 mm, 39 g | The universal "ninja star". Every buyer expects it. |
| 2 | Happo, 8 point | `SM_Shuriken_EightPoint` | 100 mm, 2.5 mm, 60 g | Classic sun shape. Best museum reference. |
| 3 | Senban, square plate | `SM_Shuriken_SquarePlate` | 108 mm diagonal, 1.9 mm, 66 g | Not a star. Most silhouette variety per unit of work. |
| 4 | Roppo, 6 point | `SM_Shuriken_SixPoint` | 98 mm, 2.0 mm, 40 g | Fills the gap between 4 and 8 points. |
| 5 | Throwing spike, Katori / MSR | `SM_Shuriken_Spike` | 150 mm, 6 mm square, 37 g | Archetypal bo-shuriken. Best-documented numbers here. |
| 6 | Manji, hooked cross | `SM_Shuriken_HookedCross` | 100 mm corner to corner, 2.5 mm, 60 g | Iconic pop shape that is genuinely public domain. |
| 7 | Sanpo, 3 point | `SM_Shuriken_ThreePoint` | 100 mm tip circle, 2.5 mm, 37 g | Odd-count variety. Reads very differently. |
| 8 | Tasselled dart, Negishi | `SM_Shuriken_TasselledDart` | 140 mm, octagonal head, 50 g | Adds cloth and lacquer to an all-steel pack. |

**Build these five first:** four-point, eight-point, senban, six-point, spike. Both families, three point counts, one non-star outline, and the strongest sourced dimensions. Ranks 6 to 8 are the variety tier. The four-point and six-point outlines below reproduce their sourced masses to within 1 g, which is good evidence the arm widths are right.

**Considered and not selected**, on record as reserves:

- **Goho 五方, five point.** In the glossaries, sold at 4.25 x 2.75 in [22][18]. Sits between the four- and six-point without giving a new read.
- **Itomaki 糸巻, thread-spool.** In the Japanese Wikipedia list, labelled in image N [2]. One glossary treats it as a synonym of the senban and a Japanese list calls it a rhombus variant of the four-point family, so it overlaps rank 3 [22].
- **Teppan 鉄板, plain plate.** Square, 7.5 to 10 cm, up to 12 cm, edges **not sharpened** [22][39]. The only form with no ground edge at all, so the best material-study contrast piece, but the dullest silhouette.

A ninth candidate, a measured antique ring-hub six-point, is at §2.9.

---

## 2. Type catalogue

**No source publishes a tip angle or a notch depth for any shuriken.** Every angle below is a modelling default chosen to reproduce a sourced mass. Check them against the photographs in section 6 during blockout. "Tip angle" is the included angle between the two ground edges of one point.

### 2.1 Juji / shiho, four point

**Japanese** 十字剣 / 四方剣, juji-ken / shiho-ken. **Family** hira-shuriken.
**Outline** 4 points, 90° pitch. Parallel-sided arms off a round hub, tapering only near the tip. No edge concavity. Round centre hole. The notch between arms is the hub circle, not a sharp vee.

| Dimension | Min | Typical | Max | **Build to** | Status |
|---|---|---|---|---|---|
| Across (tip to tip) | 70 mm | 95 to 100 mm | 114 mm | **97 mm** | SOURCED [7] |
| Thickness | 1.9 mm | 2.5 to 3.0 mm | 4.8 mm | **3.0 mm** | SOURCED [7] |
| Mass | 34 g (SNIPPET) | 40 to 57 g | 80 g | **39 g** | SOURCED [7] |
| Centre hole | 5 mm | 6 to 10 mm | 25 mm | **8 mm** | ESTIMATE |
| Arm width | n/a | n/a | n/a | **11 mm** | DERIVED |

Build-to is one real object: a Japanese four-point star, 9.7 x 9.7 cm, 0.3 cm, 39 g, tempered and quenched, surface deliberately uneven with visible scratches [7]. Cross-check, **corrected 2026-09-17 after the first build measured the mesh**: 48.5 mm tip radius, 11 mm arm, 11 mm hub and a 40° tip give **1668 mm²**, at 3.0 mm **39.3 g**. The 1647 mm² / 38.8 g figure first published here was 1.3% low. The built asset measures 1651.6 mm² and 38.90 g by mesh volume, against the 39 g sourced object. The hole is bracketed by 5 mm on a 100 mm Japanese practice star [62] and 6.35 to 9.5 mm on retail [34].

**Modelling.** C4. One arm plus hub wedge over 90°, then array. Bevel only the last 15 mm of each arm on the two long edges; faces dead flat. Thickness-to-width 3.0 : 11.

### 2.2 Happo, eight point

**Japanese** 八方剣, happo-gata. **Family** hira-shuriken.
**Outline** 8 points, 45° pitch. Large round hub, short arms, reads as a sun. Round centre hole, no concavity.

| Dimension | Min | Typical | Max | **Build to** | Status |
|---|---|---|---|---|---|
| Across | 89 mm | 100 to 102 mm | 146 mm | **100 mm** | DERIVED, rounded from the 102.0 mm record [4] |
| Thickness | 2.0 mm | 2.5 mm | 4.8 mm | **2.5 mm** | SOURCED [4] |
| Mass | 53 g [67] | 57 to 65 g | 79 g | **60 g** | DERIVED |
| Centre hole | 6.35 mm | 9.5 mm | 25 mm | **9.5 mm** | SOURCED [34] |
| Arm width | n/a | n/a | n/a | **10 mm** | DERIVED |

The best-measured object in the study is Royal Armouries XXVIM.21: 102.0 mm, 2.5 mm, 57.5 g, black-coated steel, Taiwan, about 1980 [4]. Two traps in that record. Its eight points are each "three-tipped", a trident rather than a plain spike. Its 3.0 mm hole sits **near the rim beside the engraved dragon's head, not at the centre** [4], so it is an excellent mass reference and a poor hole reference; centre holes are the norm on historical and modern stars alike [1][34]. XXVIM.26, a blackened six-point at 53.0 g, sets the bottom of the mass range [67]. Cross-check, **corrected 2026-09-17 after the eight-point build**: 50 mm tip radius, 10 mm arm, 22 mm hub and a 35° tip give **3070.6 mm²**, at 2.5 mm **60.3 g**. The 3055 mm² / 60.0 g first published here was 0.5% low: it dropped the eight small slivers where each arm root meets the hub circle, the same slip as §2.1. The built asset measures 3042.1 mm² and 59.70 g, the difference being the ground bevel (27.4 mm²) and polygonising the arcs.

**Finish.** XXVIM.21 shows "some loss of the black coating on the points" [4]. That is the wear to reproduce.

**Modelling.** C8. Arms occupy 26° of each 45° sector, leaving 19° of clear hub. Bevel the last 16 mm. Thickness-to-width 2.5 : 10.

### 2.3 Senban, square plate

**Japanese** 銛盤手裏剣, senban (also 銛磐, 旋盤). **Family** hira-shuriken, but not a star.
**Outline** a square standing on a corner. Four corner points, four **concave** sides, square centre hole. The only recommended form with edge concavity.

| Dimension | Min | Typical | Max | **Build to** | Status |
|---|---|---|---|---|---|
| Diagonal | 76 mm | 100 to 114 mm | 127 mm | **108 mm** | SOURCED [17] |
| Side | 57 mm | 76 mm | 102 mm | **76 mm** | SOURCED [17] |
| Thickness | 1.9 mm | 1.9 to 2.0 mm | 3.4 mm | **1.9 mm** | SOURCED [16][17] |
| Mass | 45 g [68] | 60 to 66 g | 82 g | **66 g** | DERIVED |
| Square hole | 12.7 mm | 12.7 mm | 25.4 mm | **12.7 mm** | SOURCED [17] |
| Side concavity (sagitta) | n/a | n/a | n/a | **6 mm** | ESTIMATE |

Two listings from one maker disagree and only one is possible. The "traditional" model gives 4.5 in tip to tip and 3.5 in cross tip [16], but a true square with a 4.5 in diagonal has 3.18 in sides. The other gives 3 in closest tips and 4.25 in farthest [17], and 3 x √2 = 4.24, so that pair describes a 76 mm square. **Build the second pair**; the same listing states the traditional hole is 1/2 in. A Japanese reproduction at 8 cm, 2 mm, about 60 g brackets the derived 66 g [20]; a 2¼ in senban at about 45 g sets the bottom [68].

**Construction.** Tradition derives the senban from the carpenter's **kugi-nuki** nail puller, with Togakure-ryu throwing from a stack of nine. Nawa Yumio's nail-puller theory is reported by [40]; the 1964 description, "like the shape of a spool, with a square hole opened in the centre used as a nail puller", is from a translation of Hatsumi's *Ninpo Gaho* [69]. The Togakure secret set is normally **Sanpo Hiden** (三宝秘伝, three treasures) [41][42]; "four secrets" is contradicted and must not go in listing copy.

**Modelling.** C4 about the diagonals, not the sides. One corner over 90°. Each concave side is a single arc, so two or three segments is plenty. Fillet the hole corners; a punched hole in 1.9 mm plate is never razor-cornered. At 1.9 mm this is the thinnest plate in the pack outright, so it carries the most z-fighting risk: real thickness, never a plane.

### 2.4 Roppo, six point

**Japanese** 六方剣, roppo-gata. An Iga and Koga six-point form is also called **kagome** (籠目) and was treated as a charm [22][19]. **Family** hira-shuriken.
**Outline** 6 points, 60° pitch. Round hub, round centre hole, no concavity.

| Dimension | Min | Typical | Max | **Build to** | Status |
|---|---|---|---|---|---|
| Across | 82 mm | 96 to 100 mm | 135 mm | **98 mm** | SOURCED [32] |
| Thickness | 2.0 mm | 2.0 to 3.0 mm | 5.0 mm (SNIPPET) | **2.0 mm** | SOURCED [32] |
| Mass | 40 g | 40 to 54 g | 79 g | **40 g** | SOURCED [32] |
| Centre hole | 6.35 mm | 6 to 10 mm | 25 mm | **8 mm** | ESTIMATE |
| Arm width | n/a | n/a | n/a | **11 mm** | DERIVED |

Retail gives 9.8 cm, 2 mm, 40 g for a one-piece steel six-point [32]. Cross-check, **corrected 2026-09-18 after the six-point build**: 49 mm tip radius, 11 mm arm, 18 mm hub and a 38° tip give **2505.3 mm²**, at 2.0 mm **39.3 g**. The 2486 mm² / 39.0 g first published here was 0.77% low, the same arm-root slip as §2.1 and §2.2 (six root slivers of 3.13 mm² dropped). §2.9 records a measured antique six-point on an open ring hub; treat it as the alternate hub treatment for this form.

**Modelling.** C6. With one tip up the bounding box is not square: 98 mm tall, 85 mm wide. Do not let that surprise the UV or collision pass. Bevel the last 16 mm. Thickness-to-width 2.0 : 11.

### 2.5 Throwing spike, Katori / Meifu Shinkage pattern

**Japanese** 棒手裏剣, also 打ち針 uchi-bari. **Family** bo-shuriken.
**Outline** a straight square bar, sharpened one end, shorter taper at the other, square in section including through the point. No hole.

| Dimension | Min | Typical | Max | **Build to** | Status |
|---|---|---|---|---|---|
| Length | 140 mm | 150 to 160 mm | 170 mm | **150 mm** | SOURCED [8][12][13] |
| Section | 6 mm | 6 to 7 mm | 8 mm | **6 mm square** | SOURCED [8][13] |
| Mass | 35 g | 37 to 38 g | 42 g | **37 g** | SOURCED [12][13] |
| Point length | n/a | 25 mm | n/a | **25 mm** | SOURCED [8] |
| Tail taper | n/a | n/a | n/a | **20 mm to 3 mm** | ESTIMATE |

Best documented in the pack, because a living school publishes its own spec: straight square steel, 14 to 15 cm, 6 to 7 mm, about 38 g, tip about 25 mm with one or two tapers, derived from the Katori Shinto-ryu uchi-bari [8]. Two independent retailers give 150 mm / 37 g and 15 cm / 6 mm / 37 g [12][13].

**One trap.** A reseller lists a "Katori" replica as 16 cm, 8 mm square, 35 g [14]. Those cannot coexist: a solid 8 mm square bar 160 mm long is about 80 g before tapering. The maker's own ladder pairs 16 cm / 35 g with **6 mm** and puts 8 mm at 17 cm / 60 g [64]. Build 6 mm.

**Construction.** Cold-rolled or forged square bar, ground to the point, hardened. Japanese sets are blackened iron [12], Western copies black-oxide AR400 [63]. Antique spikes often carry a linen flight or a drilled cord hole at the tail [38].

**Modelling.** C4 about the long axis, not an array shape. Extrude a 6 x 6 mm section 150 mm, taper the last 25 mm to a point and the last 20 mm of tail to 3 mm. Bevel the four long arrises about 0.3 mm. At 1 : 25 the silhouette is nearly all straight line, so the triangles belong at the point.

### 2.6 Manji, hooked cross

**Japanese** 卍字剣, manji-gata. A curved-arm variant is 流れ卍 nagare-manji. **Family** hira-shuriken.
**Outline** 4 arms, 90° pitch, each with a 90° hook at its end. No concavity. **Centre-hole state not established:** nothing was downloaded, so the photographs were not inspected, and a centre hole is usual on hira forms [1][22]. The reference sheet draws it without one. Check images D and E before committing; see §8.

| Dimension | Min | Typical | Max | **Build to** | Status |
|---|---|---|---|---|---|
| Corner to corner | n/a | about 100 mm | n/a | **100 mm** | ESTIMATE |
| Across the arms | n/a | n/a | n/a | **85 mm** | DERIVED |
| Thickness | 2.0 mm | 2.5 mm | 3.4 mm | **2.5 mm** | ESTIMATE |
| Mass | n/a | n/a | n/a | **60 g** | DERIVED |
| Arm width / stem / hook | n/a | n/a | n/a | **13 / 36 / 20 mm** | ESTIMATE |

No source read gives a measured manji, so the numbers are scaled to sit in the same family as the other plates. The outline is a 13 mm central square, four 13 x 36 mm arms and four 20 x 13 mm hooks: 3,081 mm², at 2.5 mm that is 60.5 g. The extreme points are the hook corners on the diagonals, which is why corner-to-corner exceeds across-the-arms by 15 mm.

**Handedness, which matters more than the mesh.** The correct form is the **left-facing manji 卍**: with one arm pointing up, its hook turns to the viewer's **left**, and the pattern reads counter-clockwise. The mirror image, clockwise-reading 卐, is the Nazi Hakenkreuz and must never be produced. That, not tidiness, is why no Mirror modifier goes near this mesh. The reference sheet draws the correct handedness; check the model against it during blockout.

**The back face is always 卐, and that cannot be modelled away** (added 2026-09-18). A flat plate is two-sided, and turning any chiral outline over shows its mirror image, so every real manji shuriken reads 卐 from behind. The rule is therefore about the presented face: model the 卍 face on +Z; every gallery image, thumbnail, turntable and store render must show +Z; and the export must be checked for an accidental mirror, since an axis flip anywhere in the Blender-to-Unreal chain would put 卐 on the presented face. In the game, a spinning star shows both faces, and a star embedded in a wall shows whichever face landed outward. That adds to the storefront risk in §5: decide before release whether the pack ships this form.

**Automated handedness gate for any build:** in Blender top view (+Z toward the viewer, X right, Y up) the hook on the arm along +Y must lie at negative X, the hook on the arm along +X at positive Y. Verified on the reference sheet's polygon on 2026-09-18: top hooks left, right hooks up, bottom hooks right, left hooks down, which is 卍.

**Provenance.** Devised as a safer prop by Nishimura Shun'ichi, credited with planning on the TBS series *Onmitsu Kenshi*, 7 October 1962 to 28 March 1965, because pointed tips were dangerous on set [2][29][30]. A 1943 book by Naruse Kanji reportedly shows a similar but not identical shape [29][31]. A 1960s television treatment of a generic Buddhist symbol; nobody owns it.

**Modelling.** C4 rotational, **no mirror symmetry**. One L-arm over 90°, then array. Every corner is a right angle, so a single-segment chamfer reads correctly throughout.

### 2.7 Sanpo, three point

**Japanese** 三方剣, sanpo-gata. Often conflated with **sanko** 三光剣, a larger form the glossaries gloss as "three rays of light radiating from the sun", or simply as three directions [22][42]. Reading sanko as 三鈷, the three-pronged Buddhist vajra, is a plausible etymology that no shuriken source read states; keep it out of listing copy. **Family** hira-shuriken.
**Outline** 3 points, 120° pitch. Round hub, round centre hole, no concavity.

| Dimension | Min | Typical | Max | **Build to** | Status |
|---|---|---|---|---|---|
| Tip circle diameter | 82 mm | 90 to 100 mm | n/a | **100 mm** | ESTIMATE |
| Tip to tip (adjacent) | n/a | n/a | n/a | **87 mm** | DERIVED |
| Thickness | 2.0 mm | 2.5 mm | 3.4 mm | **2.5 mm** | ESTIMATE |
| Mass | 38 g | 44 g | n/a | **37 g** | DERIVED |
| Centre hole | n/a | 6 to 10 mm | n/a | **8 mm** | ESTIMATE |
| Arm width | n/a | n/a | n/a | **16 mm** | DERIVED |

The only measured three-point objects are Royal Armouries XXVIM.30 at 82.0 mm diameter, 93.0 mm length, 44.5 g, and XXVIM.23 at 89.0 mm and 38 g [5][6]. Neither gives a thickness, so that row is an estimate. With three points the arms must be noticeably wider (16 mm) or the piece looks spindly.

**Modelling.** C3. With one tip up the bounding box is **87 mm wide by 75 mm tall**: the tip sits 50 mm above centre, the two lower tips only 25 mm below it. This is the one form whose centre-to-tip and centre-to-notch distances differ that much, which is the real reason to watch the UV island and collision box here. Thickness-to-width 2.5 : 16, the flattest arm ratio in the pack, so it needs the most care against shading artefacts. Add a loop at the hub-to-arm transition, the widest in the pack.

### 2.8 Tasselled throwing dart, Negishi pattern

**Japanese** 棒手裏剣, 根岸流 pattern. **Family** bo-shuriken.
**Outline** a front-heavy spike with an enlarged **octagonal** head, tapering back to a thin tail carrying a bound and lacquered tassel of animal hair. No hole.

| Dimension | Min | Typical | Max | **Build to** | Status |
|---|---|---|---|---|---|
| Length | 135 mm | 135 to 160 mm | 180 mm (SNIPPET) | **140 mm** | DERIVED, midpoint of the vendor's 135 and 145 mm sizes [10][11] |
| Head across flats | n/a | n/a | n/a | **11 mm** | ESTIMATE |
| Tail diameter | n/a | n/a | n/a | **5 mm** | ESTIMATE |
| Mass | 44 g (SNIPPET) | 50 to 60 g | 100 g (SNIPPET) | **50 g** | weakly SOURCED [39] |

A Japanese maker sells hand-made Negishi-ryu darts at about 135 mm with a weasel-hair tail "firmly wrapped by cotton string and finished by Japanese lacquer painting", and a Dai at about 145 mm with wild boar hair [10][11]. **No school publishes a diameter or a weight.** The 50 g is from one anonymous practitioner essay [39]; the 11 mm head is an estimate chosen to land the derived mass near 50 to 60 g. The SNIPPET bounds come from a blocked retailer page and from vendor pages that now return 404 [64], the weakest numbers here. Treat the octagonal head as likely but unproven: Wikipedia asserts it without a citation and the school's own site is the same organisation, while an independent account describes only "a slender bomb" with enlarged head and tail [3][24][39]. Antique spikes measured by a Japanese collector are octagonal [36], which supports the shape generally.

**Modelling.** C8 about the long axis at the head, blending to round at the tail. The only asset with a second material. Tassel as a low-poly tapered tube or a few card strips, under 200 triangles. The cord wrap is normal-map detail, not geometry.

### 2.9 Ring-hub six point, measured antique (reserve variant)

**Japanese** 六方 on a 鉄環 iron ring. **Family** hira-shuriken. **Not one of the eight.** Recorded because it is the only measured antique flat-shuriken construction in the source set, and because it documents a large open ring hub rather than a drilled hole.

| Dimension | **Build to** | Status |
|---|---|---|
| Maximum length | 130 mm | SOURCED [36] |
| Thickness | 3.5 mm | SOURCED [36] |
| Mass | 70 g | SOURCED [36] |
| Ring outer / inner diameter | 60 mm / 35 mm | SOURCED [36] |
| Blade maximum width | 9 mm | SOURCED [36] |

**Construction.** Visibly forged, and the six blades are **integral with the stock, not welded on** [36]. The collector reconstructs it as one steel strip about 5.5 cm wide, over 40 cm long, 3.5 mm thick, six blades chisel-cut from its centre at about 3.5 cm spacing, then heated, wrapped around a 35 mm iron bar and forge-welded at a single lap, edges hardened and tempered. That lap has separated and the gap is visible. One specimen on a private blog; the sequence is the author's reconstruction, not documented provenance.

**Modelling.** C6, but the topology differs from §2.4: a 35 mm open bore rather than an 8 mm drilled hole, so the blades read as tangential to a ring instead of radiating from a disc. More silhouette variety than a second drilled star, and the strongest candidate if the pack grows to nine. Model the separated lap as a normal-map seam.

---

## 3. Construction and materials in general

**Plate versus bar.** Hira-shuriken are flat plates, described in Japanese sources as 鉄板, iron plate [25]. Bo-shuriken are bar stock: square, octagonal or round by school [1][3][36].

**The re-purposed object story.** Wikipedia, citing Serge Mol's *Classical Weaponry of Japan* (2003, pp. 159 to 160), says flat shuriken were cut from coins (hishi-gane), carpentry tools (kugi-nuki), spools and nail removers (senban), and that the centre hole is inherited from those holed objects and let stars be strung on a belt cord [1]. Use it as **tradition, not fact**. It is one author, and Japanese references push back: flat shuriken are called heavy and bulky, three or four carried at most [25]. The senban / kugi-nuki link is the well-supported part [21][40][42]. "Spools" appears nowhere outside Wikipedia.

**Sharpening convention.** This matters more for modelling than the history does. Flat shuriken are "sharpened mainly at the tip", not along the whole edge [1], and several forged reproductions ship with the long edges completely blunt and only the points ground [43]. **Model the bevel as a short ground facet near each point and leave the long edges square.** That separates a shuriken that reads as forged steel from one that reads as a cookie cutter.

**Heat treatment, surface, finish.** Points hardened and tempered, surface deliberately uneven with visible scratches on the museum-shop piece [7]. A hand-forged piece keeps its hammer texture. Historical pieces are dark oxidised or lacquered iron; modern reproductions use black oxide, acid wash or polished stainless [16][18][32]. For PBR: dark blackened steel with bright bare metal at the points, exactly the wear XXVIM.21 records [4].

**Ornamentation.** Restrained. Stamped characters with paint-filled grooves plus a country or maker mark on the reverse [4]; engraved kanji invocations along the four faces of a square spike on an 1868 dealer-catalogued set [37]; maker's marks stamped centrally on both faces of a 1980s star [43]. **No family mon was found in any source read.** Do not invent a crest resembling a real one.

**Carrying.** Small numbers: three or four flat stars [25], nine senban by Togakure tradition [21], antique spikes in a bamboo tube [38] or a chain-closed pouch [37]. Relevant if the pack ever ships a quiver prop.

---

## 4. Modelling plan notes

A plan. Nothing here has been executed.

**Scale and orientation.** Real metric scale, 1 Blender unit = 1 m, so a 97 mm star is 0.097 m. Project export convention is Forward -Y, Up Z, **Apply Transform OFF**, Use Space Transform ON, FBX Units Scale, Smoothing Face, Triangulate ON and **Tangent Space OFF** (Unreal computes MikkTSpace tangents). Do not hand-export: `Scripts/pipeline/export_fbx.py` owns these settings and refuses a file with an unapplied transform (`ASSET_GUIDELINES.md` §6.1). Still test-import one star and confirm 9.7 cm in Unreal before batch-exporting.

| Form | Symmetry | Approach |
|---|---|---|
| Four point | C4 | One arm + hub wedge, Array with Object Offset empty rotated 90°, Merge on |
| Eight point | C8 | Same, 45° |
| Six point | C6 | Same, 60° |
| Three point | C3 | Same, 120° |
| Senban | C4 about diagonals | One corner + concave half-sides, array 90° |
| Manji | C4 rotational, no mirror | One L-arm, array 90°. No Mirror modifier: it produces 卐, the Hakenkreuz |
| Spike | C4 about long axis | Not an array. Square section, extrude, taper both ends |
| Tasselled dart | C8 about long axis | Octagonal profile lofted head to tail, tassel a separate object |

Keep the centre hole as its own 12 to 16 segment ring bridged to the hub, so the array seam lands on flat hub geometry and never across a bevel.

**Pivot.** Origin at the geometric centre, which for a symmetric uniform plate is the centre of mass. Blade in local XY, +Z through the hole, +X at one tip, the same forward axis on every variant so one Blueprint drives the pack. Apply all transforms before export; Unreal takes the FBX origin as the pivot [49]. For the two spikes use Origin to Center of Mass (Volume), which needs a manifold mesh.

**Sockets.** Empties named `SOCKET_<RenderMeshName>_<Name>`, matching the render mesh object name exactly. `SOCKET_Grip` at the rim between two points, +X out of the hand, for hand attachment and holstering. `SOCKET_Trail` at the centre, +Z on the spin axis, for a ribbon or spark emitter. Optionally one per point for impact effects. Identical names across all eight variants. **Measured 2026-09-17 on UE 5.8.2:** a socket must be an Empty and never a child mesh, which is welded into the render mesh instead; a hull and an Empty socket do arrive together in one file, so the January 2025 report does not reproduce; and an FBX socket lands with relative scale 100, so `Scripts/pipeline` writes a `.sockets.json` sidecar and applies it after import with `ue_import_sockets.py`. Use `pipeline.make_socket`, which handles all of this.

**Collision.** One convex hull per star, 8 to 24 vertices [49], named for the render mesh **node**: `UCX_<that object's exact name>_00`. **Measured:** a hull named for the file base rather than the node imports with zero collision and no warning, so a `_LOD0` node needs the `_LOD0` in the hull name; `pipeline.make_ucx_hull` and `rename_with_helpers` keep the pair in step. A hull spans the gaps between points, so the collider is effectively a disc: correct and cheap for a thrown projectile, but the star will not visually bite into a surface. For a stick-into-wall mechanic, trace from the leading tip socket and swap to a small `USP_` sphere on impact rather than attempting concave collision. Never set Use Complex Collision As Simple on a simulated object; it cannot simulate [61].

**Triangle budgets.** Shipping shuriken assets run 48 to 1,896 triangles per star, with one 20.6k hero outlier [46][47][48]. 144 is the typical single-model listing figure; 48 is the floor, reached inside a 24-piece pack. Project prop budget 1,000 to 5,000.

| LOD | Screen size | Triangles | What changes |
|---|---|---|---|
| LOD0 | 1.0 | 1,200 to 2,500 | Full outline, bevels, hole ring |
| LOD1 | **0.10** | 500 to 900 | Halve the hole ring and bevel segments |
| LOD2 | **0.035** | 120 to 250 | Drop the bevel and the hole entirely |

**Screen sizes amended 2026-09-17, measured on the eight-point.** The first plan of 1.0 / 0.5 / 0.25 switched to LOD2 at about 0.36 m, arm's length, where the filled-in hole is plainly visible. Screen size here is S = 1.778 R / d for tip radius R at distance d. At 0.10 LOD1 takes over at about 0.89 m, where a star is about 108 px tall at 1080p. At 0.035 LOD2 takes over at about 2.54 m, where the missing hole is about 3.6 px. These values travel in the `.sockets.json` sidecar and Unreal read them back in a fresh process. Scale them with R for the spike and the dart.

A 10 cm prop is sub-pixel within a few metres, so LOD2 can be aggressive. Nanite is not the right default: Epic's candidates are high-triangle, many-instance or occluder meshes, and Fab refuses "simplistic unoptimized assets" tagged Nanite-on (`FAB_ASSET_STUDY.md` §3). Ship classic LODs.

**Texel density and texture size.** Guides put third-person props at 512 to 1024 texels/m, first-person weapons at 1024 to 2048 [52][53]. A 100 mm star on a 1K map is already about 10,000 px/m, so 1K per star is generous and 512 defensible. **Author at 2K, ship one 2K atlas for the pack, or 1K per star.** Fab listings routinely advertise 4096 x 4096 on a 144-triangle star [46]; state the real resolution.

**Material setup.** One master plus instances. Base colour very dark grey, not pure black. Metallic 0.85 to 0.95 on coated areas, 1.0 on worn steel; the project rule is 0.95 to 1.0 (`ASSET_GUIDELINES.md` §3), so the lower coated value is a deliberate exception worth a comment in the material. Roughness 0.5 to 0.7 on coating, 0.25 to 0.4 on ground steel. Edge wear from a baked curvature and AO mask, driven hard on point tips and ground bevels, masked back around the hub. Stamped maker's mark on its own layer so variants can swap it, baked into the normal map at LOD0 and dropped by LOD2; the mark must be an invented glyph. Pack ORM with AO in R, roughness in G, metallic in B, sRGB off, DirectX normals with green flipped.

**Naming.** `SM_Shuriken_<Form>` as in section 1. Collision `UCX_SM_Shuriken_<Form>_00` on the LOD0 node, so `UCX_SM_Shuriken_<Form>_LOD0_00` once LODs exist. Textures `T_Shuriken_<Form>_BC / _N / _ORM`, or `T_Shuriken_Pack_*` for the atlas. Material `M_Shuriken_Master`, instances `MI_Shuriken_Blackened` and `MI_Shuriken_Bright`. Export one mesh per FBX; only the first mesh's custom collision imports from a multi-mesh file [49].

**Physics.** Set an explicit Mass in KG override rather than trusting hull volume times density [59]: 0.04 four-point, 0.06 eight-point, 0.06 senban, 0.04 six-point, 0.037 spike, 0.06 manji, 0.037 three-point, 0.05 tasselled dart, all kg. Spin with a RotatingMovementComponent on a child mesh plus a ProjectileMovementComponent on the actor, not a baked animation [58].

**Throwing, for whoever animates it.** Three named methods, not interchangeable. **Jiki-daho** 直打法 is the direct throw: point forward, no rotation, the documented Negishi and Meifu method [3][23]. **Hanten-daho** 反転打法 is the half-turn: the spike leaves the hand point-inward and rotates 180° in flight [3][70]. **Kaiten-daho** 回転打法 is the full spin, the normal method for the flat wheel type [70]. The half-turn is why the spike's centre of mass placement matters: a centre-balanced bar turns predictably, a head-heavy dart does not, which is why §2.8 is thrown direct. The recorded spike grip is the dart lying along the palm, held by three fingers with the thumb securing the butt, sliding out through the fingers on release [70]. Image R shows a thrower at a target, front on: stance, not finger placement.

**Blockout checklist.** Before UVs: confirm the manji reads counter-clockwise as 卍 and not 卐; check tip angles against images A, B, C and P; settle the manji centre-hole question from images D and E; size the three-point box at 87 x 75 mm, not 100 mm tall; confirm every plate has real thickness rather than a plane.

---

## 5. Franchise and brand avoidance

Historical forms are public domain. The risk is the specific proportions, styling and names attached to franchises. The project rule bars franchise designs and names and real product or brand names (`FAB_ASSET_STUDY.md` §2).

**Rule above everything below: no franchise name appears anywhere in the product text.** Not in the title, not in the tags, not in the description, not in a screenshot caption, whether or not the silhouette it labels is generic. A generic star tagged with a franchise name is a takedown risk the geometry cannot rescue.

| Recognisable design | Franchise | Traits that make it recognisable | What to do |
|---|---|---|---|
| Standard four-point star | Naruto [54] | Four **thin** prongs, large open **round** hole, flat grey blades with a dark hub, arrow-headed tips | The historical juji is fine. Differentiate on arm width (11 mm, not thread-thin), hole size (8 mm, not a large ring), tip taper, and a blackened rather than flat-grey finish |
| Fuma Shuriken / Shadow Windmill | Naruto [55] | Oversized, four **curved** blades, folds or collapses at a central hub | Do not make giant folding stars. No generic equivalent exists |
| Windmill Shuriken | Ninja Gaiden [56] | Four blades folding on a central axis, forearm-mounted, boomerang return | Do not make |
| Loaded Shuriken / Shuriken Wheel | Sekiro [57] | Prosthetic-arm launcher with a star magazine | Do not make wrist launchers or wheel magazines. Plain thrown stars are unaffected |
| Turtle and Shadow Warrior stars | TMNT, Shadow Warrior | **Silhouettes not researched.** Both are named in the project's marketplace constraint; neither was examined for a non-generic star shape | Bar the names outright in titles, tags and descriptions. Silhouettes unresolved: §8 |
| Clan markings ("Konoha", "Hayabusa") | Naruto, Ninja Gaiden | Clan symbol stamped on the hub | Invent a glyph. Stamp nothing resembling a real clan or studio mark |

**Do not use real maker or retailer names**, even though their measurements informed the build-to values here.

**The manji is the one judgement call.** The silhouette is a public-domain Buddhist symbol with a documented 1962 television origin [2][29][30], but the swastika reading is a real commercial risk on a Western storefront, and shipping the mirrored 卐 would turn that risk into a certainty (§2.6). List it as "Hooked Cross Star", no Japanese name in the title, provenance in the body text, and be ready to drop it if store moderation objects. A marketing judgement, not a legal one.

Five Wikimedia Commons vector files in the shuriken category are Naruto-derived fan art: `Fuuma_Shuriken.svg`, `Fuuma_Shuriken_fermé.svg`, `Shurikens_géants.svg`, `Shuriken_(Naruto).svg`, `Senbon.svg`. Do not use any as shape references [38].

---

## 6. Reference image index

**Six public-domain photos were downloaded on 2026-09-18 with the user's approval** into `References/Shuriken/images/`: A Happo, B Juji, C Roppo, D Manjiken, F Senban and H Shaken, each SHA-1-verified against Wikimedia's record, with source, licence and checksum in `images/provenance.json`. They are flat top-down scans but carry no trustworthy scale (the 96 dpi header is a re-save default), so use them for proportions only. Their measured outlines are in `WorkFiles/shuriken/photo_study/PHOTO_MEASUREMENT.md`. Everything else below is URLs, licences and subjects only. Most are CC BY-SA, which the project bars from shipping inside a Fab product but which is fine for private modelling reference. Check each file page before any use in marketing.

| # | Type shown | View | Licence | Page URL |
|---|---|---|---|---|
| A | Happo, 8 point | Top, neutral bg, 1217x1224 | Public domain | commons.wikimedia.org/wiki/File:Happo.JPG |
| B | Juji, 4 point | Top, neutral bg, 1370x1363 | Public domain | commons.wikimedia.org/wiki/File:Juji.JPG |
| C | Roppo, 6 point | Top, neutral bg, 1294x1047 | Public domain | commons.wikimedia.org/wiki/File:Roppo.JPG |
| D | Manji | Top, 2562x2550 | Public domain | commons.wikimedia.org/wiki/File:Manjiken.JPG |
| E | Nagare-manji (curved arms) | Top, 2968x2853 | Public domain | commons.wikimedia.org/wiki/File:Nagare_manji.JPG |
| F | Senban | Top, 1002x972 | Public domain | commons.wikimedia.org/wiki/File:Senban.jpg |
| G | Ya-juji (arrow cross) | Top, 1370x1376 | Public domain | commons.wikimedia.org/wiki/File:Yajuji.JPG |
| H | Five types together | Top, **594x537** (earlier recorded here as 2544x2032; Wikimedia's current file is 594x537). Modern retail novelties with dragon and yin-yang engravings, not historical pieces: no use as geometry reference | Public domain | commons.wikimedia.org/wiki/File:Shaken.JPG |
| I | Senban variants chart | Flat chart, 2421x1048 | CC BY-SA 4.0 | commons.wikimedia.org/wiki/File:Senban_Shuriken_types.jpg |
| J | Antique bo-shuriken, linen flights | Top-down, 3648x2736 | CC BY-SA 3.0 / GFDL | commons.wikimedia.org/wiki/File:4_bo_shuriken.JPG |
| K | Single antique bo-shuriken | Close-up, 3648x2736 | CC BY-SA 3.0 / GFDL | commons.wikimedia.org/wiki/File:Bo_shuriken_1.JPG |
| L | Bo-shuriken in bamboo tube | 3648x2736 | CC BY-SA 3.0 / GFDL | commons.wikimedia.org/wiki/File:Shuriken_in_container.JPG |
| M | Antique juji + senbon darts, Odawara | Case view, 1200x1600 | CC BY-SA 3.0 / CC BY 2.5 / GFDL | commons.wikimedia.org/wiki/File:Edo_period_shuriken.jpg |
| N | Museum display, 5 labelled types, Koka | Oblique, 4608x3456 | CC BY-SA 4.0 | commons.wikimedia.org/wiki/File:Shurikens_at_Kusuri_gakushukan(medichine_museum)_,_Koka.jpg |
| O | Mixed hira, Iga-ryu Ninja Museum | 1333x2000 | CC BY-SA 2.0 | commons.wikimedia.org/wiki/File:Ninja_museum_shuriken.jpg |
| P | Hira on red bg (easy to key) | Top, 3264x2176 | CC BY-SA 3.0 | commons.wikimedia.org/wiki/File:Hira_Shuriken.JPG |
| Q | Hari-gata needle darts | 480x640 | CC BY-SA 4.0 | commons.wikimedia.org/wiki/File:Musashi-Shibata-ryu_needles.jpg |
| R | Throwing stance: man facing a target, mid-throw | 2877x1619 | CC BY-SA 4.0 | commons.wikimedia.org/wiki/File:Le_dojo_de_lancer_de_Shuriken.png |
| S | 3-point star, 82 mm, 44.5 g, stamped dragon | 2 images, zoomable | Royal Armouries copyright, view only | royalarmouries.org/collection/object/object-17839 |

S is the only **measured** object here with viewable photographs, so it is the one image where the dimensions and the picture belong to the same piece. Do not download or redistribute it. XXVIM.21 and XXVIM.23 have no images at all. R gives stance and release, not a close grip; for the grip use §4.

The Odawara "Edo period" dating (M) is the 2006 photographer's own caption with no museum catalogue behind it, and Odawara City attributes its shuriken to the 20th-century Fujita Seiko collection [60]. The five type names on the Koka photo (N) are the uploader's caption, not display labels. **Do not write "authentic Edo period" in listing copy on the strength of these files.**

**Japanese search terms** that surface museum and school pages English searches miss:

| Term | Use |
|---|---|
| 手裏剣 | shuriken, general |
| 棒手裏剣 / 平手裏剣 / 平型手裏剣 | bo (spike) / hira (flat) |
| 車剣 / 車手裏剣 | shaken, kuruma-shuriken |
| 十字手裏剣 / 四方手裏剣 | juji / shiho, 4 point |
| 三方 / 六方 / 八方 / 十方手裏剣 | sanpo / roppo / happo / juppo |
| 卍手裏剣 | manji |
| 銛盤手裏剣 / 銛磐 / 旋盤 | senban, all three spellings |
| 糸巻き手裏剣 | itomaki, thread-spool form |
| 針型手裏剣 / 釘型 / 短刀型 | hari-gata / kugi-gata / tanto-gata |
| 直打法 / 反転打法 / 回転打法 | direct / half-turn / spinning throw |
| 江戸時代 博物館 所蔵 骨董 古武器 | Edo period, museum, collection, antique, old weapon |
| 根岸流 / 明府真影流 / 香取神道流 / 戸隠流 / 柳生流 | school names |
| 藤田西湖 | Fujita Seiko, the major collection |

---

## 7. Marketplace notes

Observed on Fab, 2026-09-17: about 24 "shuriken" listings, almost all **single models** at Free to $9.99 [44]. Only two are packs. The one traditional pack is 12 stars with 3 LOD levels at $9.99 to $11.99, about 14.2k triangles for the set, first published 2016 [45]. The other is a sci-fi pack at $18.99 [44]. Sellers file under 3D > Weapons & Combat > Throwing weapons. **There is no well-made, historically grounded, 6 to 8 piece traditional shuriken pack on Fab.**

| Observation | Value | Implication |
|---|---|---|
| Single-model price band | Free to $9.99 | Do not ship singles |
| Pack price band | $9.99 to $18.99 | Target **$12.99 to $14.99** for 8 pieces with LODs and collision |
| Triangles per star, shipping assets | 48 to 1,896 | The LOD0 plan in §4 is comfortably normal |
| Advertised texture spec | 4096 x 4096 is routine, even on 144-triangle assets | State the truth: 1K, or a 2K atlas |
| What the one real pack includes | 12 variants, 3 LODs | Match the LODs, beat it on materials and documentation |
| What no listing advertises | Rigging, animation | Static meshes are correct |
| What listings do advertise | "pivot centered and balanced for spin", "correct scale" | Say both explicitly in the description |

Fab mechanics: prices end in .99, both Personal and Professional tiers must be offered, a thumbnail plus at least one gallery item is required, tags auto-generate from the thumbnail [50][51]. Gallery plan: hero shot of all eight fanned on a neutral backdrop, one scale shot against a mannequin hand or a 10 cm rule, one wireframe plus LOD strip, one texture sheet.

---

## 8. Open questions

1. **Tip angles and notch depths are unpublished.** Every angle in section 2 is reverse-engineered from mass. Check against images A, B, C and P before committing the blockout.
2. **No measured drilled centre hole exists for a modern-proportion star.** Two measured anchors do: the 35 mm ring inner diameter on the antique ring-hub six-point [36] and the 5 mm hole on a 100 mm Japanese practice star [62]. Retail gives 6.35 to 9.5 mm [34]. Only the senban's 12.7 mm square hole is sourced outright [17].
3. **No museum record gives a thickness or weight for a genuine Edo-period hira-shuriken.** Every thickness and mass in section 2 is a modern replica, modern retail, or a 20th-century Taiwanese star. The biggest gap. Touken World, the Iga-ryu Ninja Museum or Odawara Castle Museum could be contacted.
4. **Negishi head diameter and weight are unknown**, and the octagonal head rests on an uncited Wikipedia line plus the school's own site.
5. **Manji has no measured dimensions at all**, and its centre-hole state was never established: nothing was downloaded, so images D and E were not inspected (§2.6). **Partly answered 2026-09-18** by measuring Manjiken.JPG (`WorkFiles/shuriken/photo_study/PHOTO_MEASUREMENT.md`): the photographed piece has **no centre hole**, reads 卍 as stored, and differs from this study's placeholder: arms taper (11.2 to 8.5 mm at 100 mm span), hooks are slim swept triangular blades with a 24.5° ground point, the arm end and hook back form one arc of R 98 mm, and extreme points sit 35° off the arm axis, not on the diagonals. Area 1,890 mm², so 37 g at 2.5 mm, against the placeholder's 60.5 g. Absolute size is still unknown; the photo gives proportions only.
6. **Senban side concavity depth is unsourced.** 6 mm sagitta is a visual judgement. **Measured 2026-09-18** on Senban.jpg: sagitta 0.0616 of the side, which is **4.7 mm** at the 76.2 mm build side, 22% shallower than the 6 mm estimate, giving 61.9° corners. The same piece has a 20.1 mm hole at build scale (the sourced 12.7 mm is the bottom of the 12.7 to 25.4 mm range) and a ground bevel along the full perimeter.
7. **TMNT and Shadow Warrior star silhouettes were never researched.** Both are named in the project's marketplace constraint. The names are barred either way (§5), but whether either uses a non-generic star shape the pack should avoid is unresolved.
8. ~~The `UCX_` plus `SOCKET_` in one FBX question~~ **RESOLVED 2026-09-17** by the §3.11 tests: both arrive together on UE 5.8.2, provided the hull keys to the node name and the socket is an Empty. See §4 and `ASSET_GUIDELINES.md` §6.2.
9. **Fab thumbnail and gallery pixel requirements** are not published by Fab; the project file records 16:9 or 1920x1080 enforced by the uploader.
10. Whether the manji survives Western store moderation is untested.

---

## 9. Sources and verification status

Full URLs in `sources.md`. High-stakes claims:

| Claim | Status | Note |
|---|---|---|
| Two-family split, hira vs bo | **Verified** | EN and JA Wikipedia plus independent Japanese sources [1][2][3][25] |
| XXVIM.21: 102.0 mm, 2.5 mm, 57.5 g, 3.0 mm hole | **Verified, read 2026-09-17** | Single institutional source. Hole near the rim, not central [4] |
| Museum-shop 4-point replica: 97x97x3 mm, 39 g | **Verified, read 2026-09-17** | A modern recreation, not an antique [7] |
| MSR spike: 14 to 15 cm, 6 to 7 mm, ~38 g, 25 mm tip | **Verified, read 2026-09-17** | School's own page. Prose and spec box differ; prose is the typical piece [8] |
| Senban 76 mm side / 108 mm diagonal / 12.7 mm hole | **Verified, read 2026-09-17** | The maker's 4.5 in / 3.5 in listing is geometrically impossible and was rejected [16][17] |
| Ring-hub antique six-point: 13 cm, 3.5 mm, 70 g, one-strip build | **Single collector-measured specimen** | The only measured antique flat-shuriken construction found. Private blog; the sequence is the author's reconstruction [36] |
| Negishi dart 135 to 145 mm, lacquered hair tail | **Verified for length, single vendor** | Tail independently attested; animal-hair specifics vendor-only [10][11][39] |
| Bo-shuriken 12 to 21 cm, 35 to 150 g | **Disputed** | One author (Mol 2003) via Wikipedia. Measured antiques run 30 to 150 g; Japanese encyclopedias give lower and much higher extremes [1][26][36] |
| Bo-shuriken "usually four-sided" | **Disputed, treat as false** | Every measured antique found is octagonal. Square is typical of the modern MSR spike only [3][36] |
| Hira from coins and spools, hole for belt-stringing | **Disputed** | Mol via Wikipedia only. Japanese sources call flat shuriken heavy and awkward to carry. The kugi-nuki link is the sound part [1][21][25][40] |
| "Modern stars have a small rim hole" | **False** | Modern retail stars normally have a large central hole. XXVIM.21's rim hole is a one-off decorative feature [4][34] |
| Togakure "Yon-po Hiden", four secrets | **Disputed, use Sanpo Hiden** | Three treasures is standard [41][42] |
| Seven-point "shichiho" | **Unconfirmed, omitted** | In no source read, including JA Wikipedia's own list [2] |
| "Teppan", "biao", "matsuba-gata", "kunai-gata" as bo profiles | **Disputed, avoid** | Teppan is a flat plate; biao is the Chinese dart 鏢; the other two are Wikipedia-only [1][2][22] |
| Katori replica at 16 cm / 8 mm / 35 g | **False as a set** | Physically impossible. 16 cm / 35 g pairs with 6 mm stock [14][64] |
| Manji is a 1962 TV prop shape, public domain | **Verified** | Nishimura Shun'ichi, Onmitsu Kenshi, 7 Oct 1962 to 28 Mar 1965, possible 1943 precedent [2][29][30][31] |
| Sanko named for the 三鈷 vajra | **Unsourced inference, softened** | The glossaries say only "three rays of light" or "three directions" [22][42] |
| Fab has ~24 shuriken listings, only 2 packs | **Observed 2026-09-17** | Point-in-time snapshot; re-check before pricing [44][45] |
