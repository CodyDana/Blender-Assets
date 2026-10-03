# Senbon needles: history and design study

**Date:** 2026-10-03. **Role:** history and design study for the senbon workflow. **Status:** design fixed, nothing
built. **Deliverables:** this file, `senbon_spec.json` (every number the builder needs, with a `derived` block of
measured masses and balance points) and `SENBON_DESIGN_SHEET.png` (the reference the build is judged against), all in
`WorkFiles/senbon/`. The sheet is rebuilt from the spec by `senbon_design_sheet.py` (Blender 5.2 headless).

There is no user reference image for this item. The design below is our own, built from generic historical forms.
The game and tech study (`SENBON_BUILD_PLAN.md`, written in parallel) owns the frame, sockets, collision, triangle
budgets, LODs, maps and projectile set-up. This study owns the design: how many items, every dimension, the point and
tail forms, the wrap and the finish.

Status flags, as in the shuriken study: **SOURCED** = a school, museum, encyclopedia or maker figure with a URL;
**RETAIL** = a reproduction maker's or seller's figure (real, but a modern design); **WEAK** = a fan wiki, a game
wiki or an anonymous page; **DESIGN** = our own choice.

---

## 1. Summary

| | `SM_Senbon_Needle` | `SM_Senbon_Heavy` | (existing, frozen) `SM_Shuriken_Spike` |
|---|---|---|---|
| Role | Volley needle: 3 at once, direct throw | Heavy single throw, direct | Bo-shuriken spike |
| Length | **130 mm** | **170 mm** | 150 mm |
| Section | **Round**, Ø 2.8 at the middle, Ø 2.3 at the shoulders | **Round**, Ø 2.8 tail thickening to Ø 4.5 behind the point | 6 mm square |
| Points | **Two**, 15 mm cones, included 8.8° | **One**, 22 mm, **three flat facets** | One, 25 mm, four facets |
| Tail | (second point) | Flat butt, 0.3 mm chamfer, **45 mm cotton thread wrap** (Ø 4.2) between two Ø 4.6 bindings | Short taper to 3 mm |
| Mass (steel 7.85 g/cm³) | **4.6 g** | **11.9 g** (11.7 steel + 0.2 wrap) | 37 g |
| Balance | Centre (symmetric) | **93.7 mm from the butt**, 8.7 mm ahead of the middle | 70.9 mm from the butt |
| Finish | Blackened steel, bright ground points | Same, plus a matte recolourable wrap | Blackened, bright point |

Two meshes, not three. A bundle is not a mesh (the game places three needle instances), and a holder or case does
not earn its place yet (section 7).

Why these two:

- **The needle** is what everyone expects from the word: thin, double-pointed, thrown in a spray. It is the one
  shape the existing spike cannot stand in for.
- **The heavy needle** gives the game a second, slower throw and gives the Fab pack a variety piece with the pack's
  recolour system (the wrap uses the kunai's fabric master). Its three-facet point, round section and wrapped tail
  keep it clearly apart from the square spike.

---

## 2. What real needle-type throwing weapons were

### 2.1 The family

Japanese throwing weapons split into flat plates (hira-shuriken, the "stars") and straight bars (bo-shuriken). Bo-shuriken were "modelled on traditional Japanese nails or needles", most commonly round or square [1]. They were sorted by the everyday object they resembled: *kugi-gata* (nail form), *hari-gata* (needle form), *tantō-gata* (knife form), plus spear, pine-needle and other forms [2]. Japanese Wikipedia lists the needle type (針型, also called the fire-chopstick type 火箸型) and a separate round-rod type (丸棒型) [3]. Most were single-pointed, but "some double-pointed variations did exist" [1], and Japanese sources describe rods "sharpened at one end or both" [3][4].

**Hari-gata** is defined as "a thin, straight shuriken resembling a large needle", used by several schools [5]. In the Kukishin-ryū it is called *uchibari* (striking needle) [5][6].

### 2.2 The schools that matter here

| School | What the sources say | Status |
|---|---|---|
| **Ganritsu-ryū** (c. 1625, the first recorded school) | Its shuriken were "thin, small and light enough to be stuck into the hair on either side of the head" (頭髪の左右に差せるほど細く小形軽量) [7]; "slim, needle-like darts that could be easily concealed in the hair (top-knot)" [8]. Direct, no-spin throw [8]. | SOURCED (official kobudō association, school site) |
| **Negishi-ryū** (late Edo) | Made the Ganritsu darts "thicker and heavier" (太く重く) [7] and enlarged them while keeping the shape [8]. Front-weighted, heavier shuriken for stable flight and impact [3]; an octagonal head [1]; a bound and lacquered hair tail [9]. Direct throw only (直打法) [7]. | SOURCED |
| **Shirai-ryū** (founded early 1800s by Shirai Tōru) | "Long, needle-like darts", thrown direct or half-spin [10]. A reproduction maker gives 19 cm, 6 mm, 43 g, round [10]; a retailer describes Shirai darts as hari-gata, "typically round", 15-25 cm, traditional diameters 5-6 mm, with "an easily identifiable triangular point" [11]. | School facts SOURCED; dimensions RETAIL; the triangular point is one retailer's statement (search snippet of a page now 404) |
| **Katori Shintō-ryū / uchi-bari** | A reproduction maker notes that the period uchi-bari "were very long and thin" and that its own 16 cm × 6 mm, 36 g design follows a modern scheme instead [6]. Meifu Shinkage-ryū's square spike derives from it [12]. | Historical remark RETAIL |
| **Meifu Shinkage-ryū** (1979) | Straight square steel, 14-15 cm, 6-7 mm, about 38 g, tip about 25 mm [12]. **This is the pack's existing spike** (`SHURIKEN_STUDY.md` 2.5). | SOURCED |
| **Kadono Hirohide** (上遠野流) | "Always wore 4 needles in each side of his hair, 8 in all", thrown "held between the fingers" and never missing [13]. | SOURCED (Japanese Wikipedia, anecdote) |

The Iga-ryū Ninja Museum adds that because real shuriken "aroused suspicion", ninja carried five-inch nails and sewing needles instead, needles being the most practical tool because they could be carried without suspicion [14].

### 2.3 Real dimensions

| Item | Length | Diameter / section | Mass | Status |
|---|---|---|---|---|
| Bo-shuriken, general | 12-21 cm | usually four-sided, sometimes round or octagonal | 35-150 g | SOURCED via one author (Mol 2003) [2]; the shuriken study marks this range "disputed" |
| Hari-gata (needle type) | 15-25 cm | round, 5-6 mm | n/a | RETAIL [11] |
| Shirai-ryū reproduction | 19 cm | 6 mm round | 43 g | RETAIL [10] (another 19 cm × 6 mm model: 38 g, slightly heel heavy, ground then acid-washed [11]) |
| Katori uchi-bari reproduction | 16 cm | 6 mm | 36 g | RETAIL [6] |
| Meifu Shinkage-ryū spike | 14-15 cm (to 17) | 6-7 mm square | 38 g (to 42) | SOURCED [12] |
| Ganritsu-ryū hair needles | not given | "thin, small, light" | not given | SOURCED, no numbers [7][8] |
| Mouth needles (fukumi-bari) | about 5 cm | very thin | n/a | WEAK [15] |
| Kogai (sword-fitting hairpin, sometimes improvised as a throwing object) | up to 15 cm (one example 12.5 cm × 8.2 mm) | flat | n/a | WEAK [16]; Wikipedia lists hairpins and chopsticks as thrown "in the same way as bo-shuriken" [2] |
| Chinese training needle (fei biao) | 18 cm overall, 4 cm point | 6 mm | n/a | RETAIL [17] |
| Popular-culture "senbon" | about 10-15 cm | under 2 mm | a few grams | WEAK (fan wikis) [18] |

**What the numbers say.** No historical needle has a published measurement. The real schools' surviving needle-type darts are 15-20 cm long and 5-6 mm thick, as heavy as the square spike: "needle" describes the round, slim, pointed form, not a sewing-needle thickness. The only truly thin needles in the record are the Ganritsu and Kadono hair needles, and nobody measured those. The popular "senbon" (very thin, double-pointed, thrown in sprays) sits at that thin end, and the word itself is ordinary Japanese (千本, "a thousand").

### 2.4 Construction and finish

Bo-shuriken were bar stock, forged or cold-rolled, ground to a point and hardened [12][19]. Japanese sets are blackened iron; Western copies black oxide or acid-washed [10][11][19]. A senbon maker notes that a double-pointed needle "must imperatively" be thickest at the centre of its length, and that this makes it the hardest model to forge [20]. Negishi tails are hair "firmly wrapped by cotton string and finished by Japanese lacquer" [9]. Antique spikes sometimes carried a linen flight or a cord hole at the tail (`SHURIKEN_STUDY.md` 3). Ornament is rare; no crest was found on any source.

### 2.5 Carrying and throwing

- **Carrying:** in the hair (Ganritsu, Kadono) [7][8][13]; bo-shuriken "thin, easy to stack in a bunch" [21]; antique spikes in a bamboo tube or a chain-closed pouch (`SHURIKEN_STUDY.md` 3); modern sets in a canvas forearm band [19]; Chinese needles in the sleeve or in containers [22].
- **Throwing:** three methods. *Jiki-daho*, direct, point first, no rotation (Ganritsu, Negishi) [7][8]; *hanten-daho*, half-turn; and the full spin used for flat stars [1][4]. Kadono held needles between the fingers [13]. Chinese sources describe single, simultaneous and sequential needle throws [22].
- **Why the front weight:** Negishi made its darts front-heavy to stabilise a direct, no-spin flight [3]. A centre-balanced bar turns predictably and suits the half-spin; a front-weighted one flies point first.

---

## 3. Popular culture and IP

The thin, double-pointed throwing needle thrown in sprays is the generic popular image of "senbon". It is close to the
real hair needles and to the double-pointed bo-shuriken, so the form is free to use. What we avoid:

- **No specific anime or game design.** Our needles are blackened steel with bright ground points, a visible swell at
  the middle, and (on the heavy) a three-facet point and a wrapped tail. None of that is a franchise trait.
- **No franchise names** in any asset, material, texture or listing text. The word "senbon" is generic and is used.
- **Do not use Wikimedia Commons `Senbon.svg`** (fan art; the shuriken study already lists it) or fan-wiki images as
  shape references. Fan-wiki numbers appear in 2.3 only to bracket the thin end of the range.
- No crest, mark or lettering on either needle.

---

## 4. The design

All numbers below are in `senbon_spec.json`, which wins over this text. Lengths in mm; +X toward the point; Z up.

### 4.1 `SM_Senbon_Needle`, the standard needle

- **130 mm overall**, double-pointed, mirror-symmetric, round. DESIGN: the hair-needle and kogai scale (12-15 cm)
  and clearly shorter than the 150 mm spike.
- **A gentle swell, thickest at the middle:** Ø 2.8 at x = 0 easing to Ø 2.3 at x = ±50 along
  `D(x) = 2.30 + 0.50 (1 - (x/50)²)`. This follows the maker's rule that a double-pointed needle is thickest at the
  centre [20], and it is the needle's signature line: the spike is a straight bar.
- **Two 15 mm conical points**, included 8.8°, tip radius 0.05 mm. The shoulder ring at x = ±50 is a **hard edge**
  (the profile bends 3.8° there) and is where the blackened coat stops and bright ground steel starts.
- **Why Ø 2.8 and not under 2 mm:** at the game's 90° field of view on a 1920-pixel-wide screen, one pixel covers
  about 1.04 mm at 1 m. A 2.8 mm needle is about 2.7 px wide at 1 m, 6.7 px in the hand at 0.4 m and under 1 px past
  3 m. A sub-2 mm needle would already shimmer at arm's length. The trail effect carries the read at range (the build
  plan covers the VFX side).
- **Mass 4.6 g**, balance at the centre (`derived`), a ninth of the spike.

### 4.2 `SM_Senbon_Heavy`, the heavy needle

- **170 mm overall**, single point, round. DESIGN, within the real hari-gata range (15-25 cm) [11].
- **Front-weighted:** steel Ø 2.8 from the butt to s = 54, then a straight taper to **Ø 4.5 at s = 148**, just
  behind the point. That puts the balance at **s = 93.7**, 8.7 mm ahead of the middle (the Negishi principle [3][7],
  without its octagonal head or hair tail). A first draft at Ø 3.0 -> 4.0 balanced only 2.6 mm ahead of the middle,
  too little to matter, so the taper was widened.
- **Three-facet point, 22 mm:** three flat ground facets meet at the tip, facet normals at 90°, 210° and 330° (90° =
  facing up). Each facet is 5.84° to the axis. Where a facet cuts the round stock it leaves an elliptical grind line,
  starting at s = 148 on the facet centreline. Between the facets the round survives to s = 159, and from there three
  straight ridges run to the tip. The point is DESIGN after the retailer's note of a "triangular point" on Shirai-ryū
  needles [11]. It is visibly unlike the spike's four-facet pyramid.
- **Tail:** a flat butt (Ø 2.8, 0.3 mm × 45° chamfer), 6 mm of bare steel, then a **45 mm cotton thread wrap**
  (Ø 4.2, 0.6 mm pitch, right-hand) between two raised **bindings** (Ø 4.6 × 1.5 mm), ending at s = 54. The wrap shell
  and the bindings are real geometry; the thread helix is normal-map detail. DESIGN after the Negishi tail binding
  (cotton string [9]) without the hair tassel, which belongs to the shuriken pack's planned Negishi dart.
- **Mass 11.9 g** (11.7 g steel, 0.2 g thread), about a third of the spike.

### 4.3 Finish and colours (the pack's own values)

| Surface | Look | Values |
|---|---|---|
| Body steel | Blackened oxide, faintly violet, satin, fine scratches, a few specks; drawn wire, so no hammer texture | linear (0.097, 0.093, 0.103), roughness 0.34, metallic 1.0 (the shuriken library's COAT) |
| Points (both cones; the heavy's three facets) | Bright ground steel with fine grind lines along the axis; the coat ends at the grind line with a 1.5-2.5 mm worn fade, not a painted stripe | linear 0.42, roughness 0.22 (BARE_POLISH) |
| Body wear | Faint polished lines where the fingers slide: the needle's middle, the heavy just ahead of the wrap | at most +25 % value over the coat |
| Wrap (heavy) | Matte twisted cotton, single layer, slightly tighter bindings, no lacquer gloss | shipped `#373532` (the kunai grip's colour), lightest `#CBCBCB`, roughness 0.9; recolourable through `M_Fabric_Master` |

Material slots: needle 1 (steel), heavy 2 (steel, wrap). Steel through `M_Steel_Master` instances, so the Steel Tint
and Roughness Adjust presets the pack already documents apply (for a blued or polished look).

### 4.4 How it differs from the spike, in one line each

| | Spike | Needle | Heavy |
|---|---|---|---|
| Section | square | round | round |
| Thickness | 6 mm | 2.3-2.8 mm | 2.8-4.5 mm |
| Points | one, four-facet | two, conical | one, three-facet |
| Tail | short square taper | second point | thread wrap with bindings |
| Silhouette | straight bar | swell at the middle | thickens toward the point, bump at the tail |
| Mass | 37 g | 4.6 g | 11.9 g |

### 4.5 What the build plan sets (summary, not owned here)

Pivot at the centre of mass; sockets Grip, Tip, Trail, Throw and Embed with +X toward the tip; one convex hull;
12 / 8 / 6 sides at LOD0 / 1 / 2; screen sizes 1.0 / 0.10 / 0.035 × (bounds radius / 50 mm), so about 0.13 / 0.046
for the needle and 0.17 / 0.060 for the heavy; 2048 × 256 maps. This study asks for only one deviation: the
double-pointed needle's **Grip is at its middle**, not 40 mm from a butt it does not have.

---

## 5. The design sheet

`SENBON_DESIGN_SHEET.png` (4800 × 3200 px) shows:

- **1 : 1 views (12 px = 1 mm)** of both needles (side from -Y, top from +Z, end), the frozen spike for contrast and
  a 0-200 mm ruler, all at the same scale and aligned at the left end so lengths read straight off the ruler;
- **details:** D1 the needle point at 5 : 1 with its section, D2 the heavy point at 5 : 1 (side, top, end from the
  tip, showing the three facets and the elliptical grind lines), D3 the heavy tail and wrap at 3 : 1 with its
  section;
- a **3/4 sketch** of all three and a close-up of the two points (perspective, not to scale);
- notes, the derived masses and balance point, and colour swatches.

The geometry on the sheet is built from `senbon_spec.json` in headless Blender. The script measures it: mesh volumes
agree with an analytic integral of the cross-sections to 0.01 % (needle 587.9 mm³; heavy steel 1,490.3 against
1,490.5 mm³), both meshes are closed, and the balance point agrees to 0.001 mm. Those numbers are in the spec's
`derived` block, so the build has measured targets for mass and balance, not only for shape.

---

## 6. Game notes

- **Volley:** three needles fanned about ±4°, direct throw, between the fingers as Kadono threw them [13]. The heavy
  is a single, slower throw.
- **A hair carry is the historical one** (Ganritsu, Kadono: four needles a side [7][13]). A cosmetic: needle
  instances on head sockets. No mesh is needed for it.
- The tassel-free, wrapped heavy needle and the shuriken pack's planned Negishi dart (octagonal head, hair tassel)
  stay distinct, so both can exist in the pack.

## 7. Considered and not built

- **Bundle mesh:** not needed. A bundle is three or five needle instances, which the game and the Fab demo map can
  place.
- **Holder or case:** a bamboo tube or a forearm band is historically grounded (section 2.5), but it earns its place
  only when the character has a belt or forearm socket to hang it on. A tube wants a wood or lacquer look that the
  pack's three masters (steel, fabric, paper-ink) do not have, and a forearm band is a skinned garment, a much larger
  job. Revisit with the character loadout.
- **Tassels, flights, cord holes, marks:** none. The tassel is the Negishi dart's identity; marks would need an
  invented glyph and add nothing at this size.

## 8. Open questions

1. The plan's single asset name (`SM_Senbon`) versus this design's two meshes (`SM_Senbon_Needle`,
   `SM_Senbon_Heavy`): the main chat decides whether to build both now or the needle first.
2. Should the needle ship a bright (polished) preset as well as the blackened coat? Popular imagery is bright steel;
   the pack is blackened. The material's existing Steel Tint / Roughness Adjust can make one without new textures.
3. The heavy's "triangular point" rests on one retailer's text. It is a design choice either way, not a historical
   claim, and is labelled so.

---

## 9. Sources

Read on 2026-10-03 unless marked. "Snippet" means the figure was seen only in a search-engine summary.

| # | Source | URL | Used for | Status |
|---|---|---|---|---|
| 1 | Wikipedia (EN), Shurikenjutsu | https://en.wikipedia.org/wiki/Shurikenjutsu | Nails/needles origin; round or square; double-pointed variants; Negishi octagonal head; direct, half and full spin | Encyclopedia |
| 2 | Wikipedia (EN), Shuriken (citing Mol, *Classical Weaponry of Japan*, 2003) | https://en.wikipedia.org/wiki/Shuriken | 12-21 cm, 35-150 g; kugi-, hari-, tantō-gata; hairpins and chopsticks thrown | Encyclopedia, one author |
| 3 | Wikipedia (JA), 手裏剣 | https://ja.wikipedia.org/wiki/手裏剣 | 針型 (火箸型) and 丸棒型 types; one or both ends sharpened; Negishi front-weighted heavier darts | Encyclopedia |
| 4 | Touken World, 手裏剣 | https://www.touken-world.jp/tips/51517/ | Rod shuriken pointed one or both ends; three throwing methods | Japanese sword-museum site |
| 5 | Bujinkan Huovi Dojo glossary | https://www.bhd.fi/ningueng/ | Harigata definition; uchibari = Kukishin-ryū harigata; fukumibari; fingertip needles | Practitioner glossary |
| 6 | bo-shuriken.org, Katori / Togakure uchi-bari | https://www.bo-shuriken.org/en/p/bo-shuriken-tenshin-shoden-katori-shinto-ryu-uchi-bari-togakure-ryu-uchi-bari | 16 cm × 6 mm, 36 g; period uchi-bari "very long and thin" | RETAIL |
| 7 | Nihon Kobudo Kyokai, Negishi-ryū | https://www.nihonkobudokyoukai.org/martialarts/075/ | Ganritsu needles worn in the hair; Negishi thicker and heavier; direct throw | Official association |
| 8 | Renbukan, Negishi-ryū | https://www.renbukan.org/negishi-ryu | Ganritsu needle-like darts in the top-knot; Negishi enlarged; jiki-daho | School site |
| 9 | Yamato Budogu, Negishi-ryū | https://www.yamatobudogu.com/products/negishi-ryu | Hair tail wrapped with cotton string and lacquered (read 2026-09-17 for the shuriken study) | RETAIL |
| 10 | bo-shuriken.org, Shirai-ryū | https://www.bo-shuriken.org/en/p/bo-shuriken-shirai-ryu | 19 cm, 6 mm, 43 g; Shirai Tōru, early 1800s; long needle-like darts; direct and half-spin | RETAIL |
| 11 | Delta2Alpha, Shirai Ryu 6 mm × 19 cm | https://delta2alpha.com/shop/shirai-ryu-6mm-x-19cm-bo-shuriken-throwing-spike/ | Hari-gata round, 15-25 cm, 5-6 mm, triangular point; 38 g, heel heavy, acid-washed | RETAIL, **snippet only** (page returns 404) |
| 12 | Meifu Shinkage-ryū Canada / Japan Honbu | https://meifushinkageryu.ca/bo-shuriken-%E6%A3%92%E6%89%8B%E8%A3%8F%E5%89%A3/ ; https://meifushinkageryu.jp/bo-shuriken-%E6%A3%92%E6%89%8B%E8%A3%8F%E5%89%A3/ | Square spike 14-15 cm, 6-7 mm, 38 g, 25 mm tip; Katori origin | School sites |
| 13 | Wikipedia (JA), 上遠野広秀 | https://ja.wikipedia.org/wiki/上遠野広秀 | Eight needles in the hair, four a side, thrown between the fingers | Encyclopedia, anecdote |
| 14 | Iga-ryū Ninja Museum | https://iganinja.jp/2007/12/post-48.html | Nails and sewing needles carried instead of shuriken | Museum site |
| 15 | Search summaries of game and hobby pages on fukibari / fukumi-bari | (no single page relied on) | Mouth needles about 5 cm | WEAK |
| 16 | Aoi Art, Hair comb and kogai | https://www.aoijapan.net/hair-comb-and-kogaijapanese-hairpin/ | Kogai example 12.5 cm × 0.82 cm | Dealer, snippet |
| 17 | DragonSports, Throwing Needle | https://www.dragonsports.eu/en/11576-throwing-needles.html | Chinese training needle 18 cm, 4 cm point, 6 mm | RETAIL |
| 18 | Fan wikis on "senbon" (search summaries) | (not used as references) | Popular-culture senbon under 2 mm, about 10-15 cm | WEAK |
| 19 | Ippon Supplies, Bo Shuriken (Throwing Needles) | https://ipponsupplies.com/products/bo-shuriken-throwing-needles | About 6.25 in, 60 g, forged blackened steel, canvas forearm band, set of 6 | RETAIL |
| 20 | Khurts, "Bo Shuriken, Shaken, Senbon, which models to choose?" | https://www.khurts.com/en/blog/bo-shuriken-shaken-senbon-which-models-to-choose--n34 | Senbon have two points; thickest part at the centre; hardest model to forge | Maker's blog |
| 21 | Light in the Clouds, "Bo Shuriken At a Glance" | https://lightinthecloudsblog.com/2017/06/20/bo-shuriken-at-a-glance/ | Round, flat or squared bodies; single or double pointed; easy to stack in a bunch | Practitioner blog |
| 22 | Wuxia Society, Needle | https://wuxiasociety.com/needle/ | Chinese needles: sleeves and containers; single, multiple and sequential throws | Hobby site, low authority |
| — | `References/Shuriken/SHURIKEN_STUDY.md`, sections 2.5, 2.8, 3, 4, 5 | local | The spike's numbers, carrying (bamboo tube, pouch), the Negishi dart plan, IP rules, the `Senbon.svg` warning | Project file |
