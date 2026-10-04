# Basic katana + saya: anatomy and design study

**Date:** 2026-10-03. **Role:** anatomy and design study (workflow phase 1). **Outputs:**
- `WorkFiles/katana/katana_spec.json`: every dimension for both builds.
- `WorkFiles/katana/KATANA_DESIGN_SHEET.png`: the dimensioned design sheet (7000 x 6000 px, 5 px per mm at 1:1).
- `WorkFiles/katana/study/`: the generator scripts, the sheet's `.blend` and `sheet_measures.json`.

There is no user reference image. **The sheet and the spec are the reference.** The builds are judged against them, by
looking and by measuring.

## 0. The design in one screen

| | Design value |
|---|---|
| Type | Uchigatana in plain koshirae. Shinogi-zukuri, iori-mune, chu-kissaki, torii-zori. No hi (groove) |
| Blade | Nagasa **705.0** (chord). Sori **17.0**. Motohaba **31.0**, sakihaba **22.0**. Kasane **7.0 -> 5.0**. Kissaki **38** |
| Curve | The mune is **one circular arc, R 3663.1**, tangent to the tsuka axis at the mune-machi. Arc angle 11.04°. The tip is at (83.3, 759.7) in the sword frame |
| Hamon | Plain **ko-notare**: 6.5 -> 5.0 mm from the edge, ±1.0 mm gentle wave, soft 1 mm nioi line. **Ko-maru boshi**, kaeri 5 |
| Habaki | 28 long, satin brass, plain |
| Seppa | 2 x 1.5 mm, 40.5 x 28, polished brass |
| Tsuba | Round (maru-gata), **Ø 76**, plate 5.0, rounded rim 5.6 x 3 wide. Blackened iron, no openings, no relief |
| Fuchi / kashira | 13 / 11 high, blackened iron, plain. The ito passes over the kashira end as one flat double band |
| Tsuka | **265** (fuchi top to kashira end). Haichi shape: the mune side is straight, the ha side tapers. 36.5 x 25.6 at the fuchi, 34.2 x 23.6 at the kashira |
| Ito | **Black flat cord, hineri-maki.** 9 crossings and **8 full diamonds per face**, pitch **26.78**. The omote and ura crossings are offset half a pitch. Diamond opening 17.8 along x 31.9 across (pointed) |
| Same, menuki, mekugi | White same. Antique-brass menuki: our own plain domed lozenge, 30 x 10 x 3.2. Omote menuki in the 3rd diamond from the fuchi, ura menuki in the 3rd from the kashira. Bamboo mekugi Ø 6 in the 1st omote diamond |
| Saya | Black roiro lacquer, concentric with the blade arc. **40.0 x 27.5 at the mouth -> 35.0 x 23.0 at the kojiri**. 721.8 long on the arc |
| Saya fittings | Black horn: koiguchi 20, kojiri 28. Kurikata knob 80 from the mouth on the omote, 30 x 11 x 9 proud, brass shitodome. **No sageo, no kaeshizuno** |
| Sheathed | The seppa face sits **0.3** from the koiguchi. The habaki is fully inside the pocket. The tip stops 10 short of the cavity end. **The draw is a pure rotation about the arc centre** |
| Overall | 974.7 along the tsuka axis (978.3 chord, kashira end to tip) |
| Frame | Same convention as the Snow Flower and `KATANA_BUILD_PLAN.md` 2.1. Origin = `Grip`. +Z = the tsuka axis toward the blade. +X = mune; the tip curves toward +X. -Y = omote |

## 1. Research: the standard katana in measurable terms

Numbers marked [n] come from the sources in section 9. Where sources disagree, the range is given and the choice is
explained in section 2.

### 1.1 Blade (nihonto / katana)
- **Length class.** A katana (daito) has a nagasa over 2 shaku, i.e. **≥ 60.6 cm** [2]. Typical blades are 60-80 cm, and
  most practical blades are **70-73 cm** [3].
- **Nagasa** is measured as a straight line from the mune-machi (the notch at the spine where the blade meets the
  habaki) to the tip. **Sori** is the largest gap between that line and the mune. Typical sori is **1.5-2.0 cm** [3].
- **Width.** The motohaba (width at the machi) is typically **30-34 mm**. The sakihaba (width at the yokote) is about
  **70 %** of the motohaba, so **21-27 mm** [1][3].
- **Thickness.** The kasane at the machi is typically **6-8 mm**, tapering to about 70 % at the tip [1][3]. Some
  smiths keep it constant.
- **Section.** Shinogi-zukuri is standard [2]:
  - the **ji / hira-ji** is the face from the edge (ha) up to the ridge (**shinogi**);
  - the **shinogi-ji** is the narrow band from the shinogi to the spine (mune);
  - the **mune** is usually *iori* (peaked, like a roof).
  - The hira-ji is slightly convex (**hira-niku**).
  - A shinogi set nearer the mune gives a sharper, more fragile tip [2].
- **Kissaki.** The tip section starts at the **yokote**, a crisp line across the blade. Its ridge continuation is
  the **ko-shinogi**, and the curved edge is the **fukura**. Sizes [6]:
  - **ko-kissaki** about 3 cm;
  - **chu-kissaki** about 4-5 cm, the commonest; retail sources say 4-6 cm, on wider modern blades;
  - **o-kissaki** 7-8 cm.
  - On a 21-23 mm sakihaba, a chu-kissaki of about 1.5-2 x the sakihaba (33-45 mm) reads correctly.
- **Hamon.** This is the hardened-edge line. Its families are **suguha** (straight), **notare** (gentle waves),
  **gunome** (regular semicircles) and **choji** (clove buds) [2]. The **boshi** is the hamon inside the kissaki. A
  **ko-maru** boshi turns back toward the mune in a small round curve, and its return along the mune is the
  **kaeri**.
- **Hi (grooves)** are optional.

### 1.2 Mountings (koshirae)
- **Habaki.** This is a wedge-shaped metal collar at the blade base that holds the sword in the saya by friction [2].
  Its length is **about 22-29 mm** [7], and it is typically copper or brass.
- **Seppa.** These are thin washers on both sides of the tsuba [2]. Their outline matches the fuchi and the koiguchi.
- **Tsuba.** Usually round, sometimes mokko (four-lobed) [2][9].
  - A katana tsuba is typically **7.5-8 cm** across and seldom over about 7.5 cm on Edo duty swords [2][9].
  - It is commonly about **5 mm** thick; the range is 2 to over 10 mm [7].
  - Materials: iron, steel, brass, copper, shakudo [2].
  - Kozuka and kogai openings (hitsu-ana) are optional.
- **Fuchi and kashira.** The fuchi is a collar at the tsuba end of the tsuka; the kashira is the end cap [2].
  Measured katana sets [8]:
  - fuchi **40-41.5 x 23 x 10.5-14 mm**;
  - kashira **35.5-38 x 18-18.5 x 9-12.5 mm**.
- **Tsuka.**
  - Length: usually **25-30 cm**. Historically it averaged **8 sun (24 cm)** [4][9], and the most common modern range
    is 10.5-11.5 in (27-29 cm) [10].
  - The section is **oval**, not round, so the hand feels the edge direction [5].
  - Basic shapes [5]:
    - **haichi**: the commonest; "mune side almost straight, ha side slightly tapered" [9];
    - **rikko**: hourglass;
    - **imogata**;
    - **morozori**: curved.
  - The core is ho wood under **same** (ray skin). Wood strips build the edges [11].
- **Tsuka-ito and tsukamaki.**
  - The ito is silk, cotton or leather [2].
  - **Hineri-maki** twists the ito at each crossing and forms raised diamonds [12][13]. **Hira-maki** lays the cord
    flat. **Katate-maki** (battle wrap) is a single spiral that leaves same bare on one side [13].
  - **Hishigami** are folded paper triangles under the ito at the edges. They set the diamond shape and build the
    grip [11]:
    - about **60-70 per katana tsuka**;
    - finished size about **14 x 9.5 mm** (two pulled strands of 10 mm ito measure about 14 mm);
    - height a little under half the flat side [14].
  - The wrap is usually tied off at the kashira, and the knot holds the kashira in place [11].
- **Menuki.** These are grip ornaments under the ito, seen through the diamonds [2][11]. Common katana placement is
  [15]:
  - the omote menuki at or after the **3rd open diamond from the fuchi**;
  - the ura menuki **3 diamonds from the kashira**.
- **Mekugi.** A bamboo peg through the tsuka and the tang [2].

### 1.3 Saya
- **Body.** Two halves of **honoki** (Magnolia obovata) are hollowed to the blade, glued and lacquered. Ho is used
  because it is soft, light, stable and inert to steel [16]. Black **roiro** (gloss) was the standard duty finish;
  samenuri and ishime are variants [9].
- **Koiguchi.** The mouth or its fitting, traditionally buffalo horn [2]. Horn koiguchi pieces measure about 46 x 20 x
  8 mm [17].
- **Kurikata.** A "chestnut-shaped" knob on the **omote**, about **7.5 cm** from the koiguchi ("four finger-widths").
  The sageo passes through it [16][18].
- **Shitodome.** A metal eyelet lining the kurikata hole, about 18 x 8 x 6 mm [16].
- **Kojiri.** The end fitting, traditionally horn. Kojiri pieces measure about 40-42 x 25 x 7 mm [17].
- **Kaeshizuno.** A hook that locks the saya in the obi during the draw [2]. Optional.
- **Sageo.** The cord that ties the saya to the obi [2].

## 2. Design decisions (the user's own basic katana)

The aim is an instantly readable, plain, believable katana: the textbook form, nothing signature.

1. **Blade proportions.**
   - Nagasa 705 sits in the practical 70-73 cm band. Sori 17 is the middle of 15-20.
   - Motohaba 31 and sakihaba 22 give a 71 % taper (the 70 % rule). Kasane 7.0 -> 5.0 (71 %).
   - Chu-kissaki 38 is 1.73 x the sakihaba, a normal medium point. The first draft had 34, which read small; it was
     lengthened before the sheet was finalised.
2. **One circular arc for the mune.** This is the build plan's preferred model, and it was chosen here (2.1 of the
   plan asked the Study to decide):
   - **torii-zori** (curvature centred) is classic and plain;
   - a single arc makes the draw an exact rotation, so the saya cavity is just the blade plus clearance;
   - width, thickness and roof all shrink toward the tip, so the swept cavity has no slop.
   - The arc is tangent to the tsuka axis at the mune-machi. The tsuka is straight (no tsuka-zori).
3. **Section.**
   - The width is measured from the mune peak.
   - The shinogi sits at 0.27 w from the mune: 8.4 mm at the machi, 5.9 at the yokote. This is a moderate, common
     placement.
   - The shoulders of the iori-mune are 0.74 x kasane thick. The roof rises 1.4 -> 0.9 -> 0.
   - The hira-niku is 0.35 -> 0.25, a parabolic bulge.
   - The edge is 0.5 -> 0.4 mm, the game minimum.
4. **Hamon: ko-notare, deliberately quiet.**
   - The hamon line is 6.5 -> 5.0 mm from the edge with a ±1 mm low wave. Its wavelengths (87-131 mm) are a fixed
     list in the spec, so the line is deterministic and irregular enough not to look drawn by a ruler.
   - The boshi is ko-maru, 4 mm inside the fukura, turning back 5 mm along the mune.
   - Rejected: gunome, choji and anything showy, because "basic" means calm. A dead-straight suguha was also
     rejected, because at game distance a perfectly straight line reads as a texture seam.
5. **No hi.** A groove would add relief geometry, a fit concern and a read that is not needed. It stays an option for
   a variant.
6. **Koshirae.**
   - Round iron tsuba, 76 mm across. This is the plainest classic, with no hitsu-ana and no relief. Mokko is also
     common but more decorative.
   - Brass habaki and seppa. Blackened iron fuchi and kashira matching the tsuba: one metal family, no ornament.
   - Haichi tsuka of 265 mm, sized for two hands:
     - 36.5 x 25.6 at the fuchi, inside the measured fuchi range;
     - the mune side straight and the ha side tapering 2.3 mm, as the haichi form calls for.
7. **The wrap (the Snow Flower's failure point).** It is **real geometry**, and the sheet shows it built.
   - **Path model.** Two opposite wraps:
     - The cords cross only at the face centres, so the omote and ura crossings fall half a pitch apart.
     - Across a face, each cord runs in a **straight** diagonal from a crossing to the edge.
     - Over the ha and mune edges, one cord passes every half pitch.
     - Near the edges the flat ito spreads (8 -> 16 mm wide) and rises 0.8 mm over its hishigami. This closes the
       diamonds' side corners to points and gives the edge its scalloped silhouette.
   - **Hineri twist.** At each face crossing the upper cord is twisted into a sharp raised fold. Over and under
     alternate along the face.
   - **Pattern.** 9 crossings and 8 full diamonds per face, pitch 26.78 over the 241 mm of ito. That is about 60-70
     hishigami in total, matching the craft count in [14].
   - **Ends.** The cords start under the fuchi. At the kashira they pass through brass eyelets and over the end as
     one flat double band, with the ends hidden. **Nothing dangles.**
   - The first sheet draft used constant-angle helices. They produced rounded "barrel" openings that touched the
     edges and did not look like tsukamaki. The method was changed to the straight-diagonal plus spreading-fold model
     above, which gives the classic pointed diamonds.
8. **Menuki and mekugi.**
   - The menuki are an abstract domed lozenge with a low ridge, so no motif or IP question arises. They sit at the
     craft-standard diamonds, and the ito rises over their ends.
   - The mekugi sits in the 1st omote diamond. On the ura it lies under the first ura crossing; with a half-pitch
     offset, no position shows on both faces.
9. **Saya.**
   - **Shape.** Concentric with the blade arc, so it looks right and draws cleanly. The section is an oval
     (superellipse n 2.4).
   - **Size.** 40 x 27.5 at the mouth, matching the seppa outline, tapering to 35 x 23.
   - **Mouth walls.** The mune wall is 4.0 and the edge wall 3.5, with clearances of 0.5 at the mune and 1.0 at the
     edge and sides. Around the habaki pocket the wall is at least 2.35, at the pocket corners.
   - **Horn fittings.** Koiguchi 20 and kojiri 28 long, flush, with a 0.3 x 0.2 seam groove.
   - **Kurikata.** On the omote, 80 mm from the mouth, offset 3 mm toward the ha, with a brass-lined slot.
10. **Sageo: omitted.** A static cord freezes in one pose; the Snow Flower tassels were removed for the same reason.
    The kurikata and its open shitodome stay, so a rigged or simulated cord can be added later. A cord "tied flat
    round the kurikata" was rejected: it is still a second wrap to model and fit, and not "basic". The kaeshizuno is
    omitted as well (optional historically, extra silhouette noise).
11. **Seat and draw.**
    - The blade-side seppa face rests **0.3 mm** off the koiguchi face; the gate is 0.3 ± 0.2.
    - The 28 mm habaki is fully inside a pocket with 0.1 clearance.
    - The cavity ends 10 mm past the tip, with a 6 mm horn floor beyond.
    - A clean draw rotates the katana about the arc centre, `DrawPivot`, at saya-frame (3678.6, 0, -80.3) mm.

## 3. Colours and finishes (spec `materials`; sRGB hex, roughness, metallic)

| Part | Base | Rough | Metal | Note |
|---|---|---|---|---|
| Ji (hira-ji) | #6E757B | 0.14 | 1 | polished, dark blue-grey |
| Shinogi-ji, mune | #5C6268 | 0.09 | 1 | burnished, darker mirror |
| Hamon zone | #C9CDD0 | 0.34 | 1 | frosted; 1 mm soft nioi boundary |
| Habaki | #B08D57 | 0.30 | 1 | satin brass |
| Seppa, eyelets, shitodome | #B8955E | 0.24-0.30 | 1 | polished brass |
| Tsuba, fuchi, kashira | #393633 | 0.55 | 1 | blackened iron; faint forged texture in the normal map only |
| Menuki | #9A7A45 | 0.42 | 1 | antique brass |
| Ito | #19191B | 0.72 | 0 | black flat cord; weave in the normal map |
| Same | #E8E2D2 | 0.55 | 0 | ivory; 0.6-1.2 mm nodules (normal + AO) |
| Mekugi | #A88A5A | 0.60 | 0 | bamboo |
| Saya lacquer | #0C0C0D | 0.12 | 0 | roiro gloss (the sheet draws it at #1A1A1C so the seams read) |
| Horn | #16120F | 0.28 | 0 | koiguchi, kurikata, kojiri |

Every material is either metal (1) or dielectric (0); none is in between (house rule).

## 4. The design sheet: what is on it and how to read it

`KATANA_DESIGN_SHEET.png` is a Workbench render of quick primitives, all built from `katana_spec.json` in headless
Blender. Rows 1-3 are at a **common 1:1 scale** with a 1000 mm ruler (5 px per mm):
1. **Katana, drawn.** Side view (omote, edge up, handle left), top view (from the ha) and end view (from the tip).
   Dimensioned: overall, tsuka, nagasa chord, sori, motohaba, sakihaba and tsuba. Leaders mark every part.
2. **Saya.** Side, top and end (from the kojiri). Dimensioned: length, depth and width at both ends, koiguchi,
   kojiri and the kurikata station.
3. **Sheathed pair.** Side and top views, with the blade drawn dashed inside, the seat gap marked, and an end view.
4. **Details.**
   - 4a: tsuka wrap, omote, 2:1, crossings numbered, with pitch, diamond, menuki and mekugi.
   - 4b: the tsuka seen from the ha edge, 2:1.
   - 4c: the kissaki, 3:1, with yokote, ko-shinogi and ko-maru boshi.
   - 4d: blade sections at 3:1 (machi, mid, yokote), the tsuka section and the koiguchi with its habaki pocket at
     2:1.
   - 4e: the tsuba from the blade side, 1.5:1.
   - 4f: looking into the koiguchi, 1.5:1.

The sheet's model is also saved as `study/katana_design_sheet.blend` (sword-frame mm, all parts named). A builder can
measure against it directly.

**Measured on the sheet model** (`study/sheet_measures.json`): the omote diamond opening is 17.75 mm along the axis by
31.9 mm across (side-view projection, 4th diamond); the tip is at (83.34, 759.73).

## 5. Sockets and frames (spec `sockets`)

**Katana (mm, sword frame):**
- `Grip` (0, 0, 0).
- `OffHand` (0, 0, -170).
- `BladeBase` (0, 0, 58), at the mune-machi plane.
- `BladeMid` (19.42, 0, 411.76).
- `TrailStart` (0, 0, 108).
- `TrailEnd` (72.51, 0, 746.52).
- `BladeTip` (83.34, 0, 759.73), with pitch 11.044° (the tip tangent).

**Saya (mm, saya frame = sword frame - (0, 0, 138.3)):**
- `BeltMount` (0, 0, 0): the pivot, at the kurikata station.
- `Mouth` (0, 0, -80).
- `Holster` (0, 0, -138.3): the katana's Grip goes here with zero relative rotation.
- `DrawPivot` (3678.6, 0, -80.3).

`KATANA_BUILD_PLAN.md` puts the `BeltMount` about 110 mm in. This design uses the kurikata station (80 mm), because the
obi passes there; either works, since the `Holster` is derived from it.

## 6. Differences from `KATANA_BUILD_PLAN.md` nominal numbers (the plan says the sheet replaces them)

| Item | Plan nominal | This design | Why |
|---|---|---|---|
| Nagasa / R / tip z | 710 / 3715 / ~795 | 705 / 3663.1 / 759.7 | middle of the 70-73 cm band; the plan's tip z included its 33 mm habaki |
| Habaki | 33 | 28 | inside the measured 22-29 mm range [7] |
| Machi z | 88 | 58 | follows the shorter stack: seppa 1.5 + tsuba 5 + seppa 1.5 + fuchi 13, with Grip 37 below the fuchi |
| Kashira end | -220 | -215 | tsuka 265 in both |
| Wrap pitch | ≈ 23, 8-9 per face over ~200 | 26.78, 9 crossings / 8 diamonds over 241 | the ito length is fixed by the tsuka; 8 diamonds is the craft norm for this length |
| Hineri twist | at the edges | at the face crossings, with edge scallops from hishigami lift and spread | sources put the hineri twist at the crossings [12][13]; the plan's edge-scallop gate (≥ 1 mm) is still met by the 0.8 lift plus the cord thickness |
| Sakihaba | ~21 | 22.0 | 71 % taper |

Budgets, texture sizes, slots, LOD screen sizes and collision are the **plan's** call. The spec marks its own values
for those as advisory.

## 7. Notes for the builders and reviewers

- **Build from the spec numbers, never from the sheet's pixels.** The sheet is for looking. Confirm by measuring
  against the spec.
- **The fit.**
  - The cross-sections never grow toward the tip, and the mune is one arc. So the cavity is simply the seated blade
    plus clearance (edge 1.0, sides 1.0, mune 0.5), plus the habaki pocket swept along the arc.
  - Gate the draw as a rotation about `DrawPivot`, in steps of 0.25° or less.
- **The wrap.**
  - Use the path model exactly: `ito.path_model`, the width rule, the lift, and the alternating over/under at the
    crossings.
  - The sheet's ribbons are flat bands with outlines. The build needs crowned cords with sunk side walls (plan
    section 4) and the braid in the normal map.
  - Check the pattern: diamond count, pitch, half-pitch omote/ura offset, menuki diamonds, and pointed openings
    about 17.8 x 31.9.
- **Look bar.** A blind judge seeing image pairs (build vs sheet views at the same camera) must not be able to pick
  the build on design. Areas to watch, from the Snow Flower failures:
  - a spiral wrap;
  - flat, unbevelled fittings;
  - invented ornament (anything not in the spec: no file marks, no crest, no hitsu-ana, no hi, no motif on the
    menuki, no sageo).
- **IP.**
  - Everything here is a generic historical form with plain fittings.
  - No named sword, smith, school, brand, film or game design was used or copied.
  - The menuki form is our own abstract shape.
  - The example sword that turned up in a dimension search (a smith-signed 71.0 cm blade) was **not** used. Our
    numbers are rounded design choices inside published ranges.

## 8. Files and how to regenerate

| File | What |
|---|---|
| `WorkFiles/katana/katana_spec.json` | The authority: all dimensions, rules, sockets, colours, gates |
| `WorkFiles/katana/KATANA_DESIGN_SHEET.png` | The design sheet (7000 x 6000) |
| `WorkFiles/katana/study/make_spec.py` | Writes the spec (plain Python). Change a number here |
| `WorkFiles/katana/study/make_design_sheet.py` | Builds and renders the sheet from the spec (headless Blender) |
| `WorkFiles/katana/study/katana_design_sheet.blend` | The sheet's scene (parts in sword-frame mm) |
| `WorkFiles/katana/study/sheet_measures.json` | Values measured on the sheet model, folded back into the spec |

```
py -3 -B WorkFiles/katana/study/make_spec.py
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python WorkFiles/katana/study/make_design_sheet.py -- --res 7000 --blend WorkFiles/katana/study/katana_design_sheet.blend
py -3 -B WorkFiles/katana/study/make_spec.py
```

The second spec run folds the measured diamond size into the spec. The geometry does not change.

## 9. Sources (read 2026-10-03)

1. Pavel Bolf, *Dimensions of Japanese sword blades*: https://pavel-bolf-katana-kaji.com/en/dimensions-of-blades
2. Wikipedia, *Japanese sword* and *Japanese sword mountings*: https://en.wikipedia.org/wiki/Japanese_sword ,
   https://en.wikipedia.org/wiki/Japanese_sword_mountings
3. Battlewares, *Katana lengths and dimensions*: https://battlewares.com/katana-length/
4. Swords of Northshire / Swordis / Katana Empire on tsuka length (search summaries):
   https://www.swordsofnorthshire.com/blogs/theblade/katana-length , https://swordis.com/blog/katana-length/
5. Hanbon Forge, *Basic shapes of katana tsuka*: https://www.hanbonforge.com/BLOG/Basic-Shapes-of-Katana-Tsuka
6. Kissaki sizes: https://www.kultofathena.com/japanese-sword-guide-kissaki-options/ ,
   https://katana-corp.com/pages/kissaki-katana-tip
7. Habaki and tsuba thickness (search summaries): https://www.seidoshop.com/products/minosaka-habaki ,
   https://www.militaria.co.za/nmb/topic/13266-tsuba-thickness/
8. Tozando, *Ishime fuchi & kashira* (41.5 x 23 x 13 / 38 x 18.5 x 11 mm, brass):
   https://tozandoshop.com/products/ishime-fuchi-kashira
9. Japanese Sword Index, *Koshirae*: http://www.japaneseswordindex.com/koshirae/koshirae.htm
10. Musashi Swords, *Katana tsuka length*: https://musashiswords.com/blogs/news/katana-tsuka-length
11. NCJSC glossary, *Tsukamaki*: http://www.ncjsc.org/gloss_tsukamaki.htm
12. JapaneseSword.net, *Tsukamaki guide*: https://japanesesword.net/blogs/news/tsukamaki-the-essential-guide-to-japanese-sword-handle-wrapping
13. Katana Corp, *Tsuka-ito guide*: https://katana-corp.com/pages/tsuka-ito-katana-handle-wrap
14. Cottontail Customs, *Making hishigami*: https://cottontailcustoms.com/hishigami/
15. Cottontail Customs, *Tosogu positioning for katana*: https://cottontailcustoms.com/tosogu-positioning-for-katana/
16. Seido, *Kurikata shitodome*: https://www.seidoshop.com/products/kurikata-shitodome ; Katana USA, *Saya*:
    https://katana-usa.com/blogs/katana-saya-scabbard-explained/
17. Horn saya fittings (search summaries): https://sjswords.com/products/full-set-horn-kurigata-koiguchi-koijiri-saya-sheath-for-japanese-samurai-swords
18. Katana Corp, *Kurigata and shitodome*: https://katana-corp.com/pages/kurigata-shitadome-katana

Some figures come from search-result summaries of retail and craft pages, not primary measurements. They are used
only as ranges, and every design value sits inside them.
