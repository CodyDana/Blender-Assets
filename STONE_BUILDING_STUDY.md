# Stone Building Study

Best practice for building game-ready stone in this repo: masonry walls, steps, paving, kerbs, footings, lanterns and
carved stone, and natural rocks and boulders. Built in Blender 5.2 (headless Python), exported through
`Scripts/pipeline/`, and run in Unreal Engine 5.8, for the ninja game and for Fab.

**Written:** 2026-09-30. **Versions:** Blender 5.2.0 LTS, Unreal Engine 5.8.3 (CL 58210709, read from
`Engine/Build/Build.version`). **Research notes behind it:** `WorkFiles/studies/stone/A_craft.md` (the craft),
`B_unreal.md` (the engine), `C_blender.md` (Blender and the pipeline), and the API probes in
`WorkFiles/studies/stone/c_probes/`. Go to those for the long form. This file is the working rulebook.

**Evidence tags.**
- **[M]** measured on this PC: our renders and measure JSONs, the installed engine source, plugin and content files,
  a Blender 5.2 API probe, or a read-only listing of owned rock content.
- **[D]** primary documentation (Epic, Blender, papers, heritage bodies).
- **[S]** secondary (forum, blog, search summary, blocked page).
- **[E]** an estimate: our own arithmetic or reading, not measured to the precision the number suggests.
- **[U5.2] / [U5.8]** not verified on this machine's Blender 5.2 or Unreal 5.8. The full list is in section 9.2.

Numbers in square brackets such as [13] point to the sources in section 9.1.

**Revision history.**
- 2026-09-30: first version (research x3, then this draft).
- 2026-09-30 (rev. 1, after the critic's review):
  - **Tools.** Added the tracer and measurer that the study depends on: scope, trace JSON schema, existing tracers
    to reuse, time estimate (6.8).
  - **Sourcing.** Rock gap analysis and a sourcing list for the user (2.4).
  - **Nanite and QA.** Nanite `FallbackTarget` gotcha (5.2, 4.16, 4.18). qa_check `require_ucx=False` for
    NoCollision scatter, and `WAIVE` explained as a post-filter (4.13, 4.15).
  - **Kit design.** Module seeds, mirroring and terrain fit (4.5.7). f3 piece inventory (8.2). Mortared joints (3.3,
    4.5.8). Carved relief by traced Booleans, with the minimum stroke (4.8.1). One UV plan for shipped rock (4.9.5).
  - **Unreal.** RVT dependency and fallback seam (5.4, 5.8). Legacy importer settings and the scripts they live in
    (4.16, 5.12). Stage costs and times (4.19). Texture and disk budgets (5.10).
  - **Standards.** Proposed ASSET_GUIDELINES exceptions (4.18).
  - **Corrections.** Reference resolution: joint widths and 1 px tracing were not measurable at the terrace's
    17-25 px/m, and stones are about 8-15 px, not 15-25 px (3.6, 6.1, 6.2). The colour-target conflict is resolved
    (3.11). The footing is two classes in two zones, with a zone rule (1, 4.3, 8.1). The SDF rock chain is retagged
    [U5.2] and its step order fixed (4.9.2).
- 2026-09-30 (stone kit f2 round 2): pitfalls P49-P54 appended. `Scripts/stone/` now holds first versions of
  `stone_measure.py`, `stone_trace.py` (manual + seed modes) and `stone_layout.py` (lock `StoneTools`); the first
  trace is `References/Dojo/trace_terrace_lower.json`. Sections 4.17 / 6.8 still describe the full scope.
- 2026-09-30 (stone kit f3): pitfalls P56-P59 appended. `stone_layout.py` gains `coursed_fitted` (Y-junction fitted
  coursing) and pure-Python `convex_hull` / `inset_convex` / `chaikin`; `stone_measure.py` gains `joint_stats` (SG5 bed
  continuity and runs, SG6 4-way joints).

---

## 1. Purpose, scope and how to use it

**Read this before any stone, masonry or rock build.** That covers:
- **dressed and rough masonry walls:** Japanese ishigaki (nozura-zumi, uchikomi-hagi, kirikomi-hagi), dry-stone,
  rubble and ashlar, including wall footings and plinths;
- **steps, paving, kerbs and footings;**
- **stone lanterns and carved stone** (bases, basins, markers, pedestals);
- **natural rocks and boulders:** river boulders, cliff and outcrop rock, scree, and rocks that trees grow from;
- **placing owned scanned rock** so it sits in the same world as our masonry (sections 2 and 5.9).

**Out of scope:** terrain, landscape materials, water and FX (the user sources them; memory
`scenery-assets-sourced-by-user`). Plaster, timber and roof tiles belong to the dojo material library.

**How to use it.**
1. **Section 2** decides whether to build at all (scanned rock vs our own).
2. **Section 3** classifies the stone. Write the class (masonry grade, laying pattern, joint type, rock kind) into
   the spec before any geometry: **one zone, one class**. A piece may hold several zones when the reference shows
   them, for example a course of squared cap blocks over a random rubble body (the dojo footing, 8.1). Each zone is
   declared in the spec with its own class and its own statistics (4.3). Classes never blend inside a zone.
3. If building, follow the stages in **section 4** and copy the gates of **section 6** into the spec.
4. Set up the Unreal side from **section 5**.
5. Before each judge round, walk through the pitfalls in **section 7**.
6. **Section 8** applies all of this to the first clients: the dojo stone kit fix (terrace ishigaki, stair path,
   kerbs, landings) and the D-pine rock.

**The twelve rules** (condensed from A_craft section 0, C_blender section 0, B_unreal section 0):
1. **Stone reads by its form shading, not its texture.** Each stone needs a lit crown, a shaded lower rim and a dark
   shadow where it meets its neighbours. Our f1 wall had half the reference's value spread; r0 was dark and red.
   Fix geometry and joints before the material (3.11).
2. **Classify before you build.** Field stone, dressed stone, cut stone, river-rounded stone, jointed-and-rounded
   bedrock blocks and fresh angular fracture each have their own edge radius, face flatness and joint width.
   Mixing kinds in one piece reads wrong at once (3.1).
3. **Edges round in proportion to exposure.** Corners weather first, then edges, then faces. A boulder is a rounded
   block, not a blob and not a faceted polyhedron (3.9).
4. **Joints are dark and deep.** A dry joint is a shadowed void with a packing stone at the back. Bright, flat or
   pebbled joints read as CG (3.6).
5. **Big stones low and at the corners.** Root stones at the foot, dressed corner stones, sizes falling with height.
6. **Stones go long axis into the wall.** A face stone is a deep block showing its end, not a tile.
7. **Corners are their own construction.** Sangi-zumi long/short alternation at 2-3 : 1 (3.2).
8. **Growth follows water.** Moss in joints, on ledges and tops, on shaded faces and at the foot; lichen as round
   patches on exposed faces; dark streaks below ledges. Never a whole-face tint.
9. **Ground it.** Set stones buried a third to two thirds; debris of the same rock at the foot; no clean contact line.
10. **Relief lives in exactly one place per scale.** Form (over 2 cm) in geometry; meso (2 mm-2 cm) in geometry or a
    per-stone bake; grain (under 2 mm) in the tiling texture at low normal strength. Stacking them made our "sponge".
11. **Measure against the reference, not the judge.** Two stone rounds followed a blind judge away from the sheet.
    The judge is a detector, not a spec. When a judge and a measurement disagree, the measurement wins (6.6).
12. **If a construction does not converge, change the method.** Built-from-a-sheet masonry worked; procedural natural
    surfaces (sand, mountains) and the plane-chipped D rock failed. For rock the method is "jointed block, then
    rounded, then cracked, then grained" (4.9), never noise on a sphere.

---

## 2. Decision guide: build or buy

### 2.1 The split

Masonry and natural rock go opposite ways.

| Situation | Choice | Why and how |
|---|---|---|
| **Masonry matched to a sheet** (walls, footings, steps, landings, kerbs, lanterns, carved stone) | **Build** | Our best stone results were modelled stones built from a sheet: kit 1's r3 footing ("closest piece to its sheet") and the dressed wall blocks [M]. Scanned masonry kits exist (Quixel's Japanese Stone Wall, Modular Japanese Stairs Kit, Japanese Stone Lantern [32, S]) but will not match our sheets, our kit grid or our GASP rules |
| **Background scenery rock**: river-bank boulders, cliffs, scree, anything beyond ~60 m | **Owned scans or user-sourced**, integrated by us | Standing user rule: scenery is sourced by the user; Claude lists what is needed and integrates it. Scans have real forms and a real value range. Mix them in through the shared master (5.9). **What we own does not cover this yet; the sourcing list is 2.4** |
| **A rock with a design or gameplay role**: a rock a tree grows from, a sheet-drawn hero boulder, a climbable set piece, an arena rock | **Build** (4.9) | The form is a design contract (the D-pine rock) or a collision contract (flat mantle tops, 5.8) |
| **A rock-parts set for kitbashing** banks and small cliffs in our own style | **Build** only if the user asks, or when the scans do not fit | 5-10 jointed blocks, 3-4 cleft hero rocks, 10-20 scatter chips of the same rock (4.9.6) |
| **Anything sold on Fab** (a stone pack, a wall kit) | **Build, entirely our own** | Scanned content (Megascans, Fab Standard License assets) may ship inside the game but may not be redistributed on a standalone basis [63, S]. No scanned mesh, texture or baked derivative goes into a Fab product of ours. Everything sold must be our own design (CLAUDE.md IP rule) |
| A stylised stone look from a specific art sheet | **Build** | Only when the user supplies the sheet and asks |

### 2.2 Owned rock and stone content (read-only listing, 2026-09-30) [M]

| Content | Where | What it is |
|---|---|---|
| **Nordic_Beach_Rocks** (Megascans 3D, UE 5.2 package) | `Documents/Unreal Projects/Scenery_Tutorial/Content/Megascans/3D_Assets/Nordic_Beach_Rocks_vckqccbga_3d/` | 16.6 x 9.4 x 2.7 m; 19,132 Nanite tris, fallback 5,383; **1K** albedo and normal (about 0.6 px/cm, soft up close); `MS_DefaultMaterial` with detail normal and `MF_VTGroundBlend` wired in |
| Megascans surfaces | `Scenery_Tutorial/Content/Megascans/Surfaces/` | BeachCliff (with displacement), MossyCreekStones, MossyRockyGround (4K D/N/displacement), ForestGround, MossyGrass, Snow |
| Scenery_Tutorial landscape functions | `.../Landscape/Materials/Functions/`, `Example/VirtualTextures/` | `MF_VTGroundBlend`, `MF_SlopeBlend`, `MF_TriplanarProjection(_Normal)`, `MF_CellBomb`, `RVT_Height`, `RVT_Mat`, `T_MacroVariation` |
| **Fisherman's Cabin rocks** (Fab, UE 5.2 package) | `C:/ProgramData/Epic/EpicGamesLauncher/VaultCache/NordicFi1d739256ce1cV1/.../Fishermans_Cabin/Meshes/{Rocks,Small_Rocks}` (also in `DemoGame_1`) | `SM_Rocks_01..04`: 1.3-2.9 m, 78.6-80.0k Nanite tris, fallback 5.7-8.2k, 0.59 verts/tri; `SM_Small_Rocks_01..05`: 8-15 cm, 118-270 tris. Master: **unique normal + unique mask per rock over a tiling rock set**, crevice dirt, distance-faded detail normal, world-aligned colour noise, top-layer blend, RVT blend |
| Electric Dreams sample | launcher vault | Epic's large Nanite rock/cliff assemblies [25]; not inspected [U5.8] |

**Takeaway.** Both owned rock sets use the pattern this study recommends for our own rocks: unique form (normal +
cavity mask) per rock, tiling detail on top, world-space colour variation, a moss/top blend and an RVT ground seam.
One master can serve scanned and custom rock alike (5.4).

### 2.3 Before a custom stone build, confirm all four
1. The user asked for it or agreed (big builds need the user's go; memory `stop-before-expensive-work`).
2. A reference sheet or crop is on disk under `References/<Item>/`.
3. For rock: no owned scan does the job, or the rock has a design, gameplay or Fab reason (2.1).
4. The build has a lock (`Scripts/pipeline/lock.py`). The stone kit's lock is `dojostonekit`, the pines' `dojopines`.

If the reference is AI-generated (all the dojo sheets are), record that in the asset README for Fab's AI disclosure
(ASSET_GUIDELINES 11).

### 2.4 Gap analysis: owned rock vs what the scenes need, and the sourcing list [M for owned, E for needs]

**What we own does not make a biome.** 5.11 asks for 10-20 unique rocks per biome in size classes. From 2.2 we own:
- one 16.6 x 9.4 x 2.7 m Nordic beach shelf with 1K maps;
- four 1.3-2.9 m Fisherman's Cabin rocks;
- five 8-15 cm pebbles.

**None of it has been checked against the dojo reference.** The reference's river boulders and cliff are rounded,
jointed grey granite: stone hue about 32°, saturation about 0.24 (3.11), rounded-block forms (3.9). Colour can be
re-tinted through `M_ST_RockUnique` (5.9). Form cannot. A flat coastal shelf and a set of unknown-form cabin rocks
are not rounded granite blocks.

**The check before any owned or sourced rock is used** (read-only, then one staging capture):
1. Look at the form in a clay capture from four sides in a **staging copy** (never DojoLab while other workflows run).
   Score it against SG14 (plane fraction, arris radius, cracks), using the ratios, not the look.
2. Measure maps and triangles: Nanite ≥ 50k tris for anything within 10 m, and unique normal ≥ 2K for rocks over
   1 m. 1K maps work only as far rock, or behind a detail normal (5.4 step 2).
3. Measure colour only after re-tinting through our master, under the SG11 test light (6.2).

| Size class (dojo river / terrace biome) | Need | Owned candidates | Gap: ask the user to source |
|---|---|---|---|
| Huge foot boulders at the terrace, 1.5-3 m, rounded jointed granite | 2-3 | Fisherman's `SM_Rocks_01..04` **if** the form check passes | 2-3 rounded granite boulders, Nanite, 2K+ unique maps |
| River boulders, 0.5-1.5 m, rounded (river opening 15-30 %, 3.9) | 4-6 | none | 4-6 rounded granite river boulders, some elongated along the flow |
| Mid rocks and cobbles, 0.15-0.5 m | 3-5 | none | 3-5 cobbles or a cobble pile (one merged mesh, 4.14) |
| Pebbles, 5-15 cm (scatter, NoCollision) | 3-5 | Fisherman's `SM_Small_Rocks_01..05` (colour to check) | none if the colour check passes |
| Cliff and outcrop blocks, 2-8 m, jointed with vertical fractures (the landscape reference's left cliff) | 3-4 | Nordic beach shelf only as a far flat ledge | 3-4 jointed granite cliff chunks designed to overlap and bury |
| Far bank / vista rock, > 60 m | 1-2 | Nordic beach shelf (1K is acceptable at that distance) | none |

**Total asked of the user: about 12-16 rocks.** Megascans' granite or boulder families are the usual place to look,
as are the user's own scans or photogrammetry. Search terms: "granite boulder", "river rock", "rounded boulder",
"granite cliff". Licence: game only (5.9). A sourced rock never goes into a Fab product of ours (2.1).

If the user would rather we build them, that is the 4.9.4 rock-parts set, which needs the user's go
(`stop-before-expensive-work`).

---

## 3. Principles of believable stone

### 3.1 Classify first: the stone kinds

| Kind | Examples | Face | Arris radius | Joint | Read |
|---|---|---|---|---|---|
| **Field stone** (nozura) | nozura-zumi, dry-stone, rubble footings | natural, weathered, convex | large, irregular | wide, irregular, packed with small stones | oldest, rustic |
| **Rough-dressed** (uchikomi) | uchikomi-hagi, the dojo footing, kerbs | knocked flat, bumpy, pillowed | medium, rounded | smaller, wedged | the dojo's main language |
| **Cut** (kirikomi, ashlar) | kirikomi-hagi, gate faces, copings, lantern parts | flat, chisel-dressed | small but never zero (3-12 mm) | hairline to a few mm | formal |
| **River-rounded** (tamaishi) | river boulders, cobble walls | smooth, convex | very large | n/a | water-worn |
| **Jointed bedrock blocks** | boulders, tors, cliff blocks | broad, near-flat old joint planes | 10-30 % of the block | deep straight cracks | granite country |
| **Fresh fracture** (talus) | scree, quarry spoil, fresh rockfall | clean, conchoidal | sharp | n/a | young |

### 3.2 Japanese masonry (ishigaki)

**Processing grades** [1][2][3][5]:
| Grade | Stone | Joints | Surface | Notes |
|---|---|---|---|---|
| **Nozura-zumi** 野面積 | natural or roughly split, sizes vary greatly | wide, irregular, packed with ma-zume-ishi | natural | late 16th c.; gentle straight slope; many footholds, cannot go very high |
| **Uchikomi-hagi** 打込接 | corners and faces knocked flat to close the gaps | smaller, still wedged | dressed, bumpy-flat, rounded arrises | after 1600; fan slopes; sangi-zumi corners |
| **Kirikomi-hagi** 切込接 | cut to fit, rectangular or polygonal | hairline, "without gaps"; drain holes needed | chisel-dressed, sometimes only the margins dressed (*kaneba-torinokoshi*) [4] | early Edo; gates and show faces |
| **Tamaishi-zumi** 玉石積 | river-rounded stones | wide | smooth | limited height |

**Laying patterns** [3][5]:
- **Nunozumi** 布積: similar stones in level rows; bed joints run through.
- **Ranzumi** 乱積: sizes vary, no continuous rows. Most nozura walls.
- **Tanizumi / otoshizumi** 谷積: stones set diagonally (later Edo).
- **Kikkō-zumi** 亀甲積: hexagonal cut stones. **Our f1 polygons drifted into this look**, which is a kirikomi pattern
  the dojo references do not show.
- **Warai-zumi** 笑い積: large stones ringed with small ones.
- **Kagami-ishi** 鏡石: a huge show stone in a gate face (Osaka's Tako-ishi about 5.5 x 5.5 m) [2].

**Parts behind the face** [2][5][8][9]:
- **Tsuki-ishi** (face stones): short end on the face, long side into the bank.
- **Kai-ishi** (shims) behind and under the face stones; **ma-zume / tsume-ishi** (packing stones) in the visible gaps.
- **Uragome / guri-ishi**: fist-sized rubble backfill for drainage.
- **Ne-ishi** (root stones): the largest, at the foot. **Tenba-ishi**: the top course.
- Craft rule (Anō-shū): placement over stacking; each stone sits on 2-3 contact points on the stones below, and its
  outline follows its neighbours [8][9].

**Corners, sangi-zumi** 算木積 [6]: long corner stones with the **long side 2-3 x the short side**, alternating to each
face every course; **1-2 kadowaki-ishi** (1-2 x the short side) beside each short end. The corner arris is the
steepest, best-dressed line of the wall.

**Batter and curve** [2][7]:
- **Tera-kōbai** (fan slope): straight to about half height, then curving to near vertical at the top. Kumamoto's
  small keep base: about 45° for the lower two thirds [7, S]. Marugame: the curve starts about half way, tallest wall
  about 22 m [10, S].
- **Miya-kōbai**: straight, no curve.
- **Low walls (1-4 m) read nearly straight.** The kit's d(s) = 0.10 s + 0.035 s² (6° off vertical at the top, 27.5°
  at 6 m depth) is a reasonable tera-kōbai; f2 measured 1:9.6 (5.9° from vertical) on Wall_4m_H3 [M]. Keep the curve
  subtle below 3 m, and default the terrace to near-straight unless the reference shows a sweep.

**Surface marks:** ya-ana wedge-hole rows, hatsuri (even ~1 cm chisel marks) and sudare (striped) tooling, kokuin
carved marks [2]. **IP:** invent our own marks; never a real clan crest. A wall can hold 2-3 stone colours by quarry
(Kanazawa's reddish "aka" and blue-grey "ao" Tomuro stone [4]); one flat colour is not authentic.

### 3.3 Dry-stone, rubble and ashlar (same physics) [11][90][91]
- **Batter** 1:6 to 1:10 (run : rise); a free-standing wall is about half as wide under the coping as at the base.
- **Two faces plus hearting** (small angular stones; rounded hearting "acts like ball bearings").
- **Through-stones** every 0.9-1 m along, about half height.
- **One over two, two over one:** every vertical joint is crossed by the stone above; no joint runs through two
  courses (no 4-way joints).
- **Size grading:** biggest at the foundation, often partly buried.
- **Coping:** a top course of large stones at one angle, not projecting past the faces.
- **Rubble** = the same logic with mortar; **ashlar** = sawn/dressed rectangular blocks in level courses with
  millimetre joints. Joint width is a style parameter, never a free variable.
- **Walls on slopes** [101][11]: courses stay **level**, even on gentle slopes. Stones laid with the slope slide
  during settlement. The foundation is **stepped** into level shelves, and on steep hillsides the wall has "heads"
  (built ends) about every 20 m. The wall top steps with the courses or follows the ground with its coping. Only
  constant-section copings may slope.

**Mortared masonry (rubble, ashlar, mortared footings).** The joint is a material with a profile, not a void
[102][103][104]:

| Profile | Geometry | How it reads |
|---|---|---|
| **Flush** | level with the stone faces | no shadow line; stones read as a flat mosaic |
| **Recessed** | pressed back 5 mm or more | a shadow gap under the upper stone |
| **Weathered / struck** | inclined: the upper edge set in a few mm, the lower edge at the face | a thin shadow under each upper arris; sheds water |
| **Bucket handle (concave)** | a rounded groove a few mm deep | a soft shadow line |
| **Eroded (old lime)** | raked back unevenly by weather; Historic England treats 10-15 mm of loss as the point to consider repointing [104] | irregular dark pockets, moss, a lighter mortar face deeper in |

- **Lime mortar** is soft and porous. It is paler than the stone (cream to grey, with sand grain) and weathers
  faster than the stone, so old joints sit behind the arris. It collects moss and soil in the eroded pockets.
  Lime bloom (white efflorescence) streaks below joints where water leaves the wall [E].
- **How mortared differs from dry.** A dry joint is a **dark void**: albedo ≤ 0.5 x the stone, recess 8 cm or more.
  A mortar joint is a **pale shallow surface**: albedo at or above the stone's, recess 0-15 mm. The only dark part is
  the shadow under the upper arris. Treating one as the other reads wrong at once. **Take the profile and the
  mortar-to-stone value ratio from the reference** (6.1); neither the dojo sheets nor the landscape reference shows
  mortar.

### 3.4 Steps, paving and kerbs
- **Step geometry:** outdoor stone risers 150-180 mm; garden steps 100-150 mm rise with a 300-400 mm going [20, S].
  Our grid is riser 1/6 m, tread 1/3 m: 2R + G = 667 mm, slightly long by Blondel's 600-650 mm, fine for a path.
- **Block steps vs slab treads.** Solid block steps (the dojo reference) have **no overhang**, only a rounded front
  arris. Slab treads on separate risers project 25-38 mm [20]. Take the nosing from the reference, not a code number.
- **Blocks per step vary by flight in the same reference** [M, looked at the crops]: `ref_stairs_mid.png` (the
  middle flight) shows one long slab per step; `ref_stairs_low.png` (the foreground flight) shows 3-5 short blocks
  per tread. The two judges and our notes disagreed because each looked at a different flight. **Trace each flight
  and put its count in the spec.**
- **Wear:** foot traffic hollows the tread centre, deepest just behind the nosing; old stairs can wear up to ~75 mm,
  light-use stairs show a shallow spread dip [20, S]. The nosing rounds and chips where people step; tread ends stay
  sharper and collect moss and dirt. **Treads polish lighter than risers.**
- **Paving** (shin / gyō / sō: cut, mixed, informal) [18]: nobedan strips, ishidatami (about 1.8 x 0.9 m strips of
  mixed stone) [18, S]; tobi-ishi stepping stones about 10 cm apart, a few cm proud [18, S]. Flags: flat tops, joints
  of sand/soil/moss, neighbouring flags tilted a few mm, edges slightly lower than centres.
- **Kerbs:** long stones on edge, mostly buried, **5-15 cm proud**, thin butt joints; worn outer top arris; moss and
  grass on the soil side.

### 3.5 Stone lanterns and carved stone [17]
- **Parts (top to bottom):** hōju (finial), ukebana (lotus seat), kasa (roof, corners may curl up into warabide),
  hibukuro (fire box), chūdai (platform), sao (shaft), kiso (base). Mostly granite.
- **Carving reads as carving:** crisp primary planes, softened arrises (never zero), bush-hammered or chiselled broad
  faces, smoother turned parts.
- **Weathering:** tops (kasa, chūdai ledges) take lichen, moss and dark water stain; drips run from the kasa corners;
  the base gets moss and soil splash; sun-facing faces stay paler.
- **Our lantern judge's two calls are the classic tells:** a mirrored/stretched texture and a kasa too thin. Carved
  stone needs per-part, unmirrored UVs (or triplanar), and the kasa is a thick block with real eave depth.

### 3.6 Stone shape, size distributions and joints
- **Shape varies stone to stone:** corner radius per corner (one or two sharp corners, one knocked off), crown height
  and crown peak position, aspect, tilt. A uniform pillow radius reads as upholstery (S1).
- **Distributions, not means:** store median and p10/p90 of width, height, aspect h/w, upright share, corner radius /
  short side, crown / short side. Take them from a trace of the reference (6.1).
- **Size falls with height:** mean stone area per third of the wall height decreases upward; root stones at the foot.
- **Joints:** a dry joint is a void in shadow with a small stone at the back. Visible joint width comes from the rim
  gap plus the shoulder falloff plus corner rounding. Joint core albedo ≤ 0.5 x the stone.
- **Measured on the dojo references** [M]: joints are 7-17 % of the wall area below luma 0.20 (A 1.2), or about a
  quarter of the face below 0.45 x the median linear Y (C 1). These are **area fractions**, and they are measurable.
- **Estimated, not measured** [E]:
  - **Stones:** 0.28-0.55 x 0.28-0.47 m, many upright (wall `BUILD_NOTES.md`, read at the terrace scale of
    17-25 px/m).
  - **Joints:** 2-4 cm (same source).
  - **Why these are estimates:** at 17-25 px/m a 0.28-0.55 m stone is 5-14 px. On the 6x gridded crop
    (`renders/wall/refcrops/grid_terrace.png`) the body stones span about 8-15 source px, which agrees. A 2-4 cm
    joint is 0.3-1 px, so its width cannot be read from the image. Joint width can be measured only where the
    reference resolves it: the gate steps (47-50 px/m, a 3 cm joint about 1.5 px, still marginal) or the wall sheet
    `dojo_wall_ref.png` (footing stones about 30-45 px). On the terrace, gate joints by the dark-area fraction
    (SG8), never by a width in cm.

### 3.7 Wear and weathering
- **Scale ladder** (what each scale must carry, and where it lives):

| Scale | Feature | Lives in |
|---|---|---|
| metres | crown, arris rounding, the stone's form; cracks and joint planes 10 cm - metres | geometry |
| 2-10 cm | chips and spalls at arrises | geometry |
| 5-20 mm | tool marks (dressed stone only) | geometry on hero pieces, else normal map |
| 2-10 mm | pits, weathered grain relief (feldspar decays first) | per-stone bake or tiling normal |
| 1-5 mm | mineral grain, mica speckle | albedo + a low-strength tiling normal |

- **Weathering order:** corners, then edges, then faces [12]. Old granite goes grainy (grus) and stains: iron
  (rust-brown streaks, visible on the landscape reference's left cliff) and organic grime (grey-black streaks below
  ledges and joints).
- **Rest areas:** balance detailed zones with calm faces; detail everywhere looks CG [22][33].
- **Wear follows use:** walked centres worn, tread ends sharp; exposed tops weathered, undersides dark.

### 3.8 Moss, lichen, soil and water
- **Moss** needs moisture and shade: joints, ledges, tops that hold water, shaded faces, the wall foot (soil splash)
  [15]. Colour olive to yellow-green in sun (the reference moss measures R ≈ G, hue ~50-80°), darker green in shade.
  A moss test must use hue, not "G > R" [M].
- **Lichen:** crustose lichen favours siliceous rock like granite; pale grey-green, yellow-green, grey-brown to near
  black; discrete rounded patches 1-10 cm on exposed faces and tops, some species in full sun [15]. Not a tint.
- **Soil:** in clefts and against the uphill base. **Water stain:** dark streaks from cleft mouths and ledge lips.
- **All of these are masks driven by geometry:** up-facing normal, cavity/occlusion, distance to ground, distance to
  the stone rim (joints), a directional "shade" axis, then noise to break them.

### 3.9 Natural rock: how it forms and what that means for the model
1. **Joints first.** Bedrock is cut by 2-3 sets of fracture planes into rough cubes or prisms [12].
2. **Rounding from outside in.** Weathering along the joints rounds corners most, edges next, faces least, leaving
   **corestones**; concentric shells peel off [12].
3. **Exhumation** leaves free boulders or stacked **tors**; large domes exfoliate in sheets [12].

**So a granite boulder is a jointed block with rounded arrises**: broad, near-flat faces (old joint planes), edges
rounded to 10-30 % of the block size, a few deep straight cracks. Neighbouring rocks share crack directions. This is
what the landscape reference's river boulders and left cliff show [M].

- **River boulders** [13]: abrasion rounds edges and corners fast while the axes barely change (phase I, up to ~50 %
  mass lost, within about the first km), then the convex stone slowly shrinks toward rounder axes (phase II). Near a
  mountain source they are **rounded blocks still showing their joint proportions**. Wet zone: darker, smoother, no
  lichen below the high-water line, a moss and stain band above it.
- **Cliff rock:** long straight fracture lines, stepped ledges where sheeting joints cross, blocks detaching along the
  joints; ledges collect soil and plants.
- **Talus:** angular, sharp, clean faces. Use sharp edges only for fresh breaks.
- **Rocks that trees grow from:** roots enter along existing cracks, wedge them open and hug the rock as flattened,
  fused roots heading downhill to soil; moss and soil build up in the clefts and at the tree base. The rock is usually
  several fused or split blocks. **Build the cracks first, route the roots through them**, and seat the trunk flare in
  soil-filled clefts.

### 3.10 How rocks sit in terrain
- **Burial:** set or hero stones sit **a third to two thirds** below grade, widest part at or below grade [19, S].
  Loose scatter boulders (river banks, PCG) sink at least **15-35 % of their height** (5.8). Never a floating base.
- **Contact:** soil and small debris bank against the uphill side; grass and moss close the line.
- **Families:** a hero rock gets mid pieces and chips of the **same** rock and colour, falling in size away from it.
  Japanese garden grammar clusters 3, 5 or 7 stones in scalene triangles [19, S]; the Sakuteiki says set stones as
  nature would, following each stone's character [36].
- **Orientation:** jointing and bedding stay consistent within an outcrop. Random rotation per rock looks placed:
  constrain yaw so crack directions agree within a cluster.

### 3.11 Colour and value ranges (measured) [M]

Two measurement methods were used on the same images; both are kept because each answers a different question.

**Method A (A_craft 1.2):** luma = Rec.709 weights on sRGB values; "dark" = luma < 0.20; local std = mean standard
deviation of luma in 16 px blocks.

| Image | luma p5 / p25 / p50 / p75 / p95 | dark | R/B | local std |
|---|---|---|---|---|
| Ref, terrace wall faces (`renders/f1/refcrops/ref_stone_faces.png`) | 0.17 / 0.40 / 0.58 / 0.70 / 0.85 | 7.0 % | 1.33 | 0.056 |
| Ref, lower wall (`ref_wall_lower.png`) | 0.12 / 0.25 / 0.47 / 0.64 / 0.83 | 17.1 % | 1.40 | 0.074 |
| Ref, terrace wall wide (`ref_terrace_wall.png`) | 0.13 / 0.29 / 0.49 / 0.70 / 0.87 | 12.8 % | 1.35 | 0.092 |
| Ref, wall-sheet footing (`dojo_wall_ref.png` box 118,272-605,332) | 0.09 / 0.26 / 0.34 / 0.42 / 0.55 | 14.7 % | 1.23 | 0.128 |
| Ref, river boulders (`dojo_landscape_ref.png`, two crops) | 0.06-0.08 / 0.19-0.21 / 0.26-0.42 / 0.56-0.75 / 0.82-0.86 | 22-27 % | 1.17-1.24 | 0.136-0.149 |
| **Ours f1** (`renders/f1/close_stone_faces.png`) | 0.21 / 0.47 / 0.52 / 0.56 / 0.59 | 4.7 % | 1.45 | 0.058 |
| **Ours r0** (`renders/wall/close_stone_faces.png`) | 0.07 / 0.22 / 0.31 / 0.36 / 0.41 | 22.5 % | 1.71 | 0.058 |

**Method C (C_blender 1, 11.6):** linear luminance Y; "stone" = the brightest half; "dark joint" = Y < 0.45 x median.

| Image | Y p10 / p50 / p90 | p90 / p50 | dark-joint fraction | stone hue / sat |
|---|---|---|---|---|
| Ref close crop (`renders/f2/refcrops/ref_close_stone_faces.png`) | 0.044 / 0.297 / 0.606 | 2.04 | 0.25 | 32° / 0.24 |
| Round 0 (`wall/sbs_close_stone_faces.png`, right half) | 0.015 / 0.078 / 0.129 | 1.65 | 0.24 | 27° / 0.26 |
| f2 (`f2/sbs_close_stone_faces.png`, right half) | 0.024 / 0.157 / 0.203 | 1.29 | 0.22 | 23° / 0.16 |

**Readings:**
- **f1 had no highlights and no deep shadow** (p95 0.59 vs 0.83-0.87): the flat crowns (bulge ≤ 1.4 cm) removed the
  lit top / shaded shoulder gradient.
- **r0 was too dark and too red** (median 0.31, R/B 1.71 vs 1.33-1.40): the "chocolate" call.
- **f2 has the right joint area** (about a quarter in all three) **but too little spread across each stone** (p90/p50
  1.29 vs 2.04) and is pinker (23° vs 32°). The fix is crown height and profile, per-stone albedo and the tint, not
  the joint width.
- **Local contrast of the footing and the boulders is about twice ours** (0.128-0.149 vs 0.058): that is form
  shading (crowns, cracks, undersides), not speckle.
- **When to use which:** absolute percentiles (method A) only under matched lighting; ratios, dark fraction and hue
  (method C) across different lighting. The references are daylight AI images; our dojo renders are sunset.

**Albedo.** A PBR chart puts fresh granite at about 0.35-0.40 linear [34, S]; old wall stone is darker from grime and
lichen. Our library Granite v2 is about sRGB (115, 111, 106) ≈ 0.16 linear; the f1 kit tint about 0.25 / 0.22 / 0.20
linear [M]. **Do not pick albedo from a chart: match the reference's rendered value distribution under the scene's
own light.**

**Which colour target applies where (this resolves the conflict in the first version).** Two targets exist, and a
kit that passes one fails the other:
- **The reference target (SG11):** stone hue about 32°, saturation 0.24 ± 0.05, R/B 1.33-1.40, measured on the
  reference crops [M].
- **The materials README's r3 "Unreal capture target":** saturation < 0.20, R/B 1.00-1.20. It was set in the dojo
  sunset scene to stop the r2 red shift, before any stone reference was measured [M].

**For stone the reference wins** (the user's "to the T" bar):
1. **Blender:** SG11 on renders under a **reference-matched daylight rig** (6.4), compared with the reference crop.
2. **Unreal:** SG11 on captures under the **same daylight test light**, taken **after `G.look()`** (5.4 step 8).
   `G.look()` exists to cancel Unreal's chroma gain, so the Unreal numbers must land on the reference, not on the
   README range.
3. **In the sunset scene** there is no absolute colour gate. Only relative checks apply: scanned rock vs kit wall
   dE76 < 5 (5.9), R/B and hue ratios between neighbours.

The README's s < 0.20 and R/B 1.00-1.20 are **retired for stone**. They still apply to the library's other sets
unless their owner says otherwise. Tell the dojo materials owner. The albedo swatch (Granite v2 sRGB 115/111/106,
R/B 1.08) may need warming to reach 32° / 0.24 under daylight. Measure the render; do not tune the swatch.

**Granite grain** [16]: Inada granite 3-4 mm grains, 34 % quartz, 62 % feldspar, **4 % biotite**, light grey; Aji
granite fine-grained blue-grey with small black specks [S]. The dark speckle is **small and sparse** (≤ ~5 % area,
1-5 mm). Our round-2 "terrazzo" granite broke this.

### 3.12 What makes CG stone look fake (the checklist a judge will hit)

| # | Failure | Measurable check |
|---|---|---|
| S1 | **Uniform pillow radius** | CV of arris radius and crown height across stones ≥ 0.3; crown/width in the reference's range |
| S2 | **Flat crowns / low value range** | luma p25-p75 and p5-p95 within ±0.05 of the reference crop (matched light), or p90/p50 within ±15 % |
| S3 | **Bright, flat or pebbled joints** | dark fraction within ±30 % of the reference; joint core albedo ≤ 0.5 x stone |
| S4 | **Wrong laying pattern** (kikkō polygons for ranzumi; level courses for random) | aspect h/w histogram, upright share, count of straight bed joints longer than 3 stones |
| S5 | **Stones too uniform in size** | stone-area CV; mean area per third of height falls upward |
| S6 | **Thin tiles, no depth** | exposed stones (ends, corners, openings, coping returns) show depth ≥ 0.8 x face width; hidden stones may be shallower (our reading: the kit's 22-24 cm depth on ~0.5 m stones is fine only where the depth never shows) |
| S7 | **Faceted / chipped hulls for natural rock** | no dihedral crease sharper than ~150° except on fresh breaks; arris radius ≥ 10 % of block size |
| S8 | **Blob / potato rocks** | ≥ 60 % of surface within 15° of 3-6 dominant planes; 1-3 straight cracks |
| S9 | **Repeating noise / tiling** | albedo autocorrelation peak at the tile period under a threshold; ≥ 2 macro scales |
| S10 | **Speckle too big or contrasty** ("terrazzo") | dark speckle ≤ ~5 % area, 1-5 mm world size |
| S11 | **Moss as a tint** | moss mask correlates positively with up-normal and cavity; no moss on overhangs |
| S12 | **Floating or clean-cut contact** | burial per 3.10; no visible intersection line; same-rock debris at the foot |
| S13 | **Wrong scale** | stone sizes from the reference's own scale (6.1) |
| S14 | **Mirrored / stretched UVs** | box/triplanar or per-face UVs; texel within ±20 % across a piece (kit: 5.08-5.37 px/cm) |
| S15 | **Everything clean and new** | chips on ≥ 30 % of exposed arrises; streaks below ledges |
| S16 | **Colour off under the scene light** ("chocolate" r0, pale beige f1) | rendered R/B, hue and median luma vs the reference crop under the same light |

---

## 4. The pipeline in this repo

### 4.1 Overview

Stone splits into two families, each with its own construction [C 0, 2]:

| Class | Primary method | Optional | Avoid |
|---|---|---|---|
| Dressed face stone (uchikomi, kirikomi, ashlar, coping, quoins, sangi-zumi blocks) | analytic: 2D outline → ring loft with arris + crown (`kit1_geo.pillow_face`) or rounded box lattice (`kit1_geo.rough_block`) → chips | bmesh bevel + subdivide + masked displace for sharp kirikomi blocks | height-field relief on flat plates (failed on Snow Flower, CLAUDE.md) |
| Rough/natural face stone (nozura, rubble, footings, dry stone) | `pillow_face` with high crown and irregular outline, or SDF lumps from a stone library (4.6) | per-stone plane chips then SDF opening | pure 3D noise on an icosphere ("potato") |
| Packing stones / wedges | small lumps placed in the layout's gaps, recessed (4.5.5) | library instancing | random scatter not tied to gaps |
| Steps, slabs, kerbs, flags | `rough_block` slabs + wear; layouts by guillotine splits or power diagram (4.7) | | per-vertex noise on sparse lattices (r0 "lumpy sponge" treads) |
| Lanterns, carved stone | `kit1_geo` `lathe` / `prism` / `dome` primitives, crisp small bevels, SDF opening 3-8 mm only if weathered (4.8) | unique UV + baked AO | box UVs on round parts |
| Boulders, river stones, cliff chunks, tree rocks | **SDF pipeline** (4.9): chipped lobes → union → opening → cracks → meso noise → high to low bake | strata slicing; own Voronoi bisect fracture | noise blob; raw faceted hull |

**Stages for any stone asset:**
a. **Reference and spec**: scale, class per zone, trace, measured distributions (6.1; the tracer and measurer are
   6.8 and do not exist yet) → spec JSON (4.3).
b. **Layout** (walls, paving, steps): 2D pattern in unrolled face coordinates, gated flat against the trace before
   any 3D (4.5).
c. **Stones / rock body**: per-stone generators (4.4, 4.6) or the SDF rock pipeline (4.9).
d. **Weathering data**: chips, wear, per-stone tone, moss / lichen / wet masks in vertex colour or a baked mask (4.11).
e. **UVs and bakes** (4.10, 4.12).
f. **Collision and traversal data** (4.13).
g. **Nanite / LOD** (4.14).
h. **QA and export** through `Scripts/pipeline/` (4.15).
i. **Unreal import + material** (4.16, section 5), verified in a second fresh process on the exact exported bytes.

Staged rounds with stop points: layout only (flat polygons vs the trace) → one stone type in close-up → the full
piece (6.4). Stop and show the user when a stage fails decisively.

### 4.2 Files, folders and naming

| What | Where |
|---|---|
| Shared stone library (proposed, 4.17) | `Scripts/stone/` |
| Kit builders | `Scripts/<area>/<kit>/build_<track>.py` (dojo: `Scripts/dojo/stonekit/`, lock `dojostonekit`) |
| Spec JSON | `WorkFiles/<item>/build/<kit>/spec_<track>.json` |
| Traces | `References/<Item>/trace_<crop>.json` (with the px/m scale and the source crop box) |
| Reports | `WorkFiles/<item>/build/<kit>/{measure,qa_report,export_report,fbx_verify}.json`, `BUILD_NOTES.md` |
| Catalogue | `WorkFiles/<item>/build/<kit>/kit_catalog.json` (pieces, snaps, UCX, materials, traversal) |
| Renders | `WorkFiles/<item>/build/<kit>/renders/<round>/` during work; finals to `Renders/<Item>/` |
| Exports | `Exports/<Kit>/<Sub>/SM_<prefix>_<Piece>.fbx` + `Textures/` + README |
| Source blend | `Assets/<Area>/<Kit>.blend` (merged under `sk_shared.file_lock`) |

**Naming:** static meshes `SM_<KitPrefix>_<Class>_<Variant>` (dojo stone kit: `SM_DKT_Wall_4m_H3`,
`SM_DKT_Stair_Flight_W180_R100`); rocks `SM_<Prefix>_Rock_<Kind><NN>` (e.g. `SM_DKR_Boulder_River03`, proposal);
collision `UCX_<render mesh node name>_NN`; textures `T_<Prefix>_<Name>_{BC,N,ORM,M}` (M = mask: R moss, G lichen,
B wet/dirt, proposal); materials `M_ST_*` masters, `MI_<Prefix>_*` instances. One class per piece.

### 4.3 The spec (one JSON that everything reads)

Minimum fields for a masonry piece (numbers from 6.1, never taste):
```json
{
  "class": {"grade": "uchikomi", "pattern": "ranzumi", "joint": "dry_packed"},
  "zones": [{"name": "cap", "rows": "top 1 course", "class": {"grade": "uchikomi", "pattern": "nunozumi",
             "joint": "dry_tight"}, "stone": "..."},
            {"name": "body", "rows": "rest", "class": {"grade": "nozura", "pattern": "ranzumi",
             "joint": "dry_packed"}, "stone": "..."}],
  "scale_px_per_m": 21.0, "scale_uncertainty_px_per_m": 4.0, "trace": "References/Dojo/trace_terrace_wall.json",
  "stone": {"width_m": [0.28, 0.42, 0.55], "height_m": [0.28, 0.36, 0.47],
            "aspect_hw": [0.7, 0.95, 1.4], "upright_share": 0.35,
            "corner_r_over_short": [0.08, 0.18, 0.35], "crown_over_short": [0.05, 0.08, 0.12],
            "peak_off": [0.15, 0.30], "tilt_deg": 2.0, "chip_rate": 0.4, "depth_m": 0.24},
  "joint": {"visible_cm": [2, 3, 4], "core_recess_m": 0.08, "packing": true},
  "course": {"broken_course_share": 0.2, "waviness": 0.05, "min_overlap": 0.25},
  "batter": {"a": 0.10, "b": 0.035}, "corner": {"type": "sangi", "long_short": 2.5, "kadowaki": [1, 2]},
  "value_targets": {"p90_over_p50": 2.0, "dark_fraction": 0.25, "hue_deg": 32, "sat": 0.24},
  "gates": ["SG1", "SG2", "..."]
}
```
The three-number lists are p10 / median / p90. The values above are examples of shape only; take real ones from the
trace. A single-class piece leaves `zones` out, and the top-level `class` / `stone` apply to the whole piece. A
zoned piece gives every zone its own `class` and `stone` block, and the gates run per zone. `joint.visible_cm` is set
only when the trace resolved joint widths (6.1, 6.8); otherwise it is `null` and SG8 gates the dark-joint fraction
alone. Rocks add: lobes (from traced front/side), joint-set normals, opening radius, crack planes, burial, moss/lichen
rules.

### 4.4 Stage c: individual dressed stones

**What we have (keep it)** [M]:
- `kit1_geo.pillow_face(g, poly, origin, t, n, depth, proud, bulge, seed, mat, edge, rough, fine, ...)`: convex
  outline → Chaikin-rounded corners → wobbled rim → side wall back to `depth` → quarter-round shoulder (`edge`) →
  superellipse crown (`bulge`, crown exponent) → 2-3 octaves of real relief (9 / 26 per m) faded in from the shoulder;
  explicit tile-unit UVs. The r3 footing used `bulge ≈ 0.07 x short side`.
- `kit1_geo.rough_block` / `rounded_stone` / `block_stone`: subdivided box mapped to a rounded box, pillowed front,
  3 relief octaves.
- `sk_shared.dressed_stone` (f1 numbers) and `sk_shared.pillow_stone` (f2 numbers) are parameter sets over
  `pillow_face`. Both are smooth-shaded (Nanite-friendly, 4.14).

**Improvements for the next round** [C 3.2]:
1. **Corner radius per corner.** 0.5-1.5 x the mean radius; one or two sharp corners; one knocked off (`_cut_corner`).
   f2 reads "rounded rectangles" because every corner shares one radius.
2. **Asymmetric crown.** `peak_off` 0.15-0.30 (not 0.10-0.12), peak nearer the top edge; the lower rim rolls off
   further than the upper. That produces the reference's lit crown and dark lower rim (p90/p50 about 2).
3. **Clean arris line, separate wear.** Keep the arris line clean; wear is a separate term (pits and chips on exposed
   top corners only). "Crisp but worn" = a clean line with a few bites, not noise on the edge.
4. **Chips:** 0-3 per stone on exposed corners via `bmesh.ops.bisect_plane(clear_outer=True)` then fill
   (`contextual_create` / `edgeloop_fill`) for a flat conchoidal facet [M, 5.2 probe]. Scooped chips: Boolean
   difference with a small noisy icosphere, solver `MANIFOLD` (7 ms per chip in the probe; `EXACT` 13 ms; `FLOAT`
   1 ms but less robust). Recompute normals and `kit1_geo.weld` afterwards.
5. **Sharp-cut (kirikomi) blocks:** `bmesh.ops.bevel(geom, offset=0.005-0.012, segments=2-3, profile=0.5-0.7,
   affect='EDGES', clamp_overlap=True)` [M], light subdivision, displacement masked to the face interior. Blender 5.2
   adds a **Mesh Bevel geometry node** (`GeometryNodeMeshBevel`, with per-side offsets, a profile curve and outputs
   for the bevel's faces/edges usable as wear masks) [66][M]. New: spike it, do not depend on it [U5.2].
6. **Density:** ring step 2-3 cm on a 30-60 cm stone (r3 used 1.8 cm, f2 2.1-3.2 cm). At 5.12 px/cm, detail under
   ~4 mm belongs in the texture. Silhouette arrises need 2-5 mm segments (4.14).

### 4.5 Stage b: wall layout (the main lever)

All layouts work in **unrolled face coordinates (a, s)**: a along the wall, s down the face from the top
(`lay_courses` / `lay_rounded` already do; `F.P(a, z)` maps onto the battered face) [M]. Each generator outputs
convex (or near-convex) polygons plus a per-stone joint inset. Each polygon becomes a 3D stone on the face's tangent
plane at its centroid, and `sk_shared.rigid_warp` moves it **rigidly** onto the curved batter, so no stone is sheared.

**Gate the layout in flat 2D against the trace before building any 3D stone** (SG3-SG6).

#### 4.5.1 Coursed (uchikomi nunozumi, ashlar, footings)
- **Course heights** drawn from the measured distribution; **broken courses** (a course splits into two thinner ones
  for 1-3 stones, then merges back). This is the most visible difference between hand-laid walls and f2's straight
  course lines.
- **Widths** from the measured histogram (`sk_shared.mixed_widths` draws fixed shares 24 % upright / 58 % ordinary /
  18 % long; replace with measured shares).
- **Stagger:** one over two; every vertical joint lands in the middle third of the stone below; minimum overlap
  0.25 x stone width; **reject any 4-way joint** [90][91].
- **Wandering boundaries:** piecewise-linear course boundaries through the joints, amplitude 3-6 % of the course
  height (`Boundary`); pinned straight at module ends so kit modules interlock (`pins`, 0.18 m teeth).
- **Upright / through stones** spanning two courses (`talls` in `lay_rounded`); in dry stone about 1 m apart at half
  height.

#### 4.5.2 Random / polygonal (nozura ranzumi, rubble, crazy paving)
1. **Seeds** by Poisson-disc sampling with a per-point radius drawn from the measured size distribution.
2. **Cells** by a **power diagram** (weighted Voronoi) so big and small stones coexist; 2-4 Lloyd iterations toward
   the centroids remove slivers while keeping the mix [88][89]. `kit1_geo.voronoi_cells` does plain Voronoi by
   half-plane clipping (`convex_clip`); for the power diagram shift each bisector by
   (w_i − w_j) / (2 |p_i − p_j|). No scipy in Blender 5.2's Python (numpy 2.3.4 only) [M]: keep our own clipper.
3. **Anisotropy:** stretch the domain by the measured mean aspect, run the diagram, unstretch. For the river terrace
   (many upright stones) stretch in s, not a.
4. **Round the cells** (Chaikin, per-corner radius) so the result reads as rounded field stone, not kikkō polygons.
5. **Joints:** `kit1_geo.inset_convex` by each stone's own half-joint.
6. **Rejects:** a cell narrower than 6 cm at its minimum caliper (`sk_shared.min_width`) becomes a packing gap.

#### 4.5.3 Ishigaki specifics
- **Batter:** d(s) stored as a function of s; stones placed rigidly, never deformed by it.
- **Corner (sangi-zumi):** alternate long and short `rough_block`s at 2-3 : 1 with kadowaki-ishi, placed **first**;
  field stones then fill each course (`force_first` / `force_last`) [M].
- **The three grades as layout modes:**
  - nozura: 4.5.2 with natural lumps (4.6), wide irregular joints, packing in every gap;
  - uchikomi: 4.5.1 with rough courses, shaped faces, fewer gaps, small wedges at junctions;
  - kirikomi: 4.5.1 or 4.5.2 with 2-5 mm joints, crisp bevels (4.4.5), polygons fitted edge to edge, nothing recessed.
- **Root stones:** the lowest course 1.3-1.8 x the median stone size (our proposal; confirm on the trace), partly
  buried. **Coping / tenba-ishi:** a separate course of long blocks, straight in plan, following the sori at the ends.

#### 4.5.4 Joint depth as geometry
- Face stones have side walls back to `depth` (22-24 cm); the joint core (`M_DKT_JointDark`) sits **8 cm** behind the
  face [M].
- **The joint core must not be a flat plane.** Give it a few cm of noise, soil pockets and the backs of packing
  stones, so grazing light does not show a sheet (f2: "stones floating on a board").
- Measure the visible joint by 2 mm ray scans (`measure_f1.py` / `measure_f2.py` pattern): f1 median 1.8 cm, f2 2.6 cm
  (p90 8.6 cm at diagonal junctions) [M]. Compare with the traced reference.

#### 4.5.5 Packing stones and wedges
Find the gaps (triangle-ish holes where three stones meet, and rejected sliver cells). Fill each with 1-3 small lumps
at 60-85 % of the gap's inscribed circle, recessed 1-4 cm behind the face plane, long axis along the gap. The visual
rule: gaps are dark, each holds a small stone at the back [83][84][85].

#### 4.5.6 Heavy alternative (not for now)
True 3D mason-style packing by stability and contact exists [83][86]; convincing for a hero dry-stone ruin, too slow
for a kit module whose visible face is 2D anyway.

#### 4.5.7 Module variants, repetition and terrain fit
**Repetition.** A laid face is memorable: one distinctive stone repeated every 4 m reads as a kit at once.
- **Seeds per module.** Each wall module that makes up long runs (`Wall_4m_*`, `Wall_2m_*`, `WallFoot_*`) ships
  **3 layout seeds** (`_A/_B/_C`) at every height the level uses. A 20-40 m run is 5-10 modules of 4 m. With 3
  seeds and a "no repeat within 2 neighbours" placement rule, identical modules sit ≥ 12 m apart and never side by
  side [E]. Corners, ends and openings appear once per run: one seed each.
- **Layout statistics hold per seed.** Every seed passes SG3-SG7 on its own. Seeds differ in layout, never in class.
- **Hero stones** (a kagami-ishi, a split boulder in the face) belong in their own unique modules, never in the
  seeded runs. A memorable stone repeated is the fastest tell.
- **Per-placement tone** (5.4 step 4) and the world-space macro (step 3) break the rest. They do not replace seeds.
- **Cost.** A 4 m H3 module is roughly 100-150k tris [M, footing 117,657]. Three seeds for 2 lengths x 4 heights add
  about 16 modules (≈ 2 M source tris, about 30 MB of Nanite data at 14.4 B/tri [105]). Build only the heights the
  level uses.
- **Mirroring.** Do not rely on it.
  - A mirror along the wall (X scale −1) turns the battered face into a mirrored battered face, which is
    geometrically valid. It also mirrors the box-UV grain, which is invisible on granite.
  - But it swaps the module's end teeth (`pins`, 0.18 m). A mirrored module only chains if the tooth pattern is
    symmetric. Negative-scale Nanite instances with tangent-space normals and vertex colour are [U5.8].
  - Mirroring across the face is never valid (it inverts the batter).
  - If mirroring is ever used for variety, it is a tested placement option, never a substitute for the 3 seeds.

**Terrain fit** (level courses, stepped footings; 3.3 [101]):
- **Gentle fall along the wall** (up to about 0.3 m per 4 m module, 1 : 13): absorbed by burial. The foot course
  already runs 0.35 m below grade [M]. Courses stay level, the downhill end shows one more course of root stones,
  and the uphill end buries it.
- **Steeper fall:** **stepped modules.** New pieces: `Wall_Step_<H>to<H'>` (H3→H2, H4→H3, H6→H4). Each carries a
  built "head": dressed corner-style stones on the step riser, and a coping return where the top drops. The bottom
  steps too (a stepped `WallFoot`). The top steps in whole-course heights. **The current catalogue has no transition
  or stepped piece** (104 pieces, 0 transitions) [M].
- **Sloped tops** (a wall beside a stair): a raked coping on level courses. The body steps under a sloping
  constant-section coping (a Nanite spline mesh is fine there, 5.2) or under stepped coping stones. Never slope the
  courses.
- **Height transitions** in plan (a wall meeting a taller one) use the corner and end pieces plus a head. Do not
  scale a module vertically: it stretches every stone and breaks texel density (S14).

#### 4.5.8 Mortared joints (rubble, ashlar, mortared footings)
Only when the reference shows mortar (3.3). None of the dojo references does.
- **Geometry.** Stones keep their rounded arrises. The mortar is a **separate joint-fill surface** per module: the
  joint core (4.5.4) brought forward to the profile's recess, 0 mm (flush) to 15 mm (eroded). It is shaped per
  profile:
  - weathered/struck: inclined, with the upper edge set 3-6 mm deeper;
  - bucket handle: concave, 3-5 mm;
  - eroded: noisy depth 5-15 mm, with deeper pockets at the wall top and foot, where it is wettest.
  
  It meets each stone below its arris, so the arris shadow line survives. The depths are [E], to be taken from a
  raking-light reference.
- **Mesh budget.** The fill is one low-density surface per module (1-2 cm edges). Its silhouette never shows.
- **Material.** Mortar has its own slot (`M_<Prefix>_Mortar`):
  - lime albedo from the reference; often **≥ the stone's value**, cream to grey [E];
  - sand grain at micro scale, roughness 0.85-0.95;
  - vertex-colour masks for moss in eroded pockets, lime bloom streaks below joints, and grime.
  
  Never reuse `M_DKT_JointDark` for mortar.
- **Gates.** The mortar-to-stone value ratio and the joint shadow fraction come from the reference (6.1 step 7),
  replacing the dark-joint fraction of a dry wall. The recess comes from the raking-light render vs the reference.

### 4.6 Stage c: rubble lumps and a stone library
For nozura walls, rubble footings, field walls, packing stones and scree, build **24-40 unique lumps per stone type**
once, then pick per layout cell [C 5]:
1. **Lump:** convex hull of 30-60 jittered points on an ellipsoid with the measured aspect → 6-20 chip planes
   (`bisect_plane`, never on the bottom or back) → SDF opening at r = 4-12 % of the short axis (4.9) → meso noise.
2. **Fit to cell:** choose the lump whose front silhouette has the best IoU with the cell polygon after a similarity
   transform; allow ±12 % non-uniform scale and a rotation about the face normal. Reuse becomes invisible because
   scale, rotation and neighbours differ [95].
3. **Merge per module** into one mesh for Nanite. Nanite Assemblies (instanced parts) could cut disk for repeated
   units but are unproven for static walls [U5.8] (5.2).

### 4.7 Stage c: steps, paving, kerbs and footings
- **Step blocks:** `rough_block` slabs with wear [M, track 9]: tread hollow 5-8 mm, deepest behind the nosing and
  along the walking line; rounded nosing 2-3 cm radius (r0 used 28 mm); 0-2 chips on the nosing; ±4 mm per-stone
  tilt; the top keeps ~30 % of the block relief. **Drive the hollow from a traffic field** (a 2D density along the path
  centre line, higher on the stair centre and at landings) instead of a per-stone constant.
- **Blocks per step, nosing and overhang come from the trace** of each flight (3.4). Block steps: no overhang unless
  the reference shows one (f1's 4 cm set-back came from a judge, not the sheet).
- **Tread / riser split:** lighter, smoother treads (`M_DKT_StepGranite`), darker, rougher risers and ends
  (`M_DKT_StepRiser`). Keep it; tread rays 18/18 on StepGranite and riser rays 18/18 on StepRiser are the check [M].
- **Paving layouts:**
  - ashlar / random rectangular: recursive guillotine splits of the landing rectangle with minimum sizes and the
    no-4-way-joint check;
  - running bond: offset rows;
  - crazy paving: the 4.5.2 power diagram with flat crowns — **only if the reference shows it**.
  - Joints 1.0-1.6 cm, flush tops ±3 mm (f1 landings measured −7 to +1 mm; f2 joints median 1.2 cm) [M].
- **Kerbs:** `rough_block` runs 5-15 cm proud (f2 `Kerb_L180` measured 5.1-7.2 cm over the walk) [M], thin butt
  joints, worn outer top arris, moss/soil band on the soil side via the Wear B channel.
- **Footings:** buried course; every stair-kit stone runs **0.35 m below** its walking level [M].

### 4.8 Stage c: lanterns and carved stone
- Build from `kit1_geo.lathe` (turned parts: hōju, ukebana, sao), `prism` (hex/square kasa, hibukuro, chūdai),
  `dome`; crisp primary planes with 3-12 mm bevels; SDF opening 3-8 mm only for a weathered look.
- **Kasa is a thick block** with real eave depth; measure its thickness / width ratio on the sheet (the courtyard
  lantern judge: "cap too thin") [M].
- **UVs:** unique or triplanar per part, never mirrored (box UVs seam at 45° on round parts; materials README).
- **Weathering data:** lichen and moss on the kasa top and chūdai ledges, drip streaks from the kasa corners, soil
  splash at the base (4.11).
- Sockets (Empties + `.sockets.json`) for the light position (pipeline rule).

#### 4.8.1 Carved relief: markers, inscriptions, kokuin, lantern windows
**Height-field relief is not the method** (it failed on the Snow Flower sword, sheath and heels; CLAUDE.md).

**The method: traced vector outlines → cutter solids → Boolean → crisp bevels.**
1. **Trace** the mark's outline from the reference into resolution-independent curves.
   - `Scripts/props/props_lib/trace.py` is the model to reuse. It gives SHA-256 source provenance, sub-pixel marching
     squares, clamped cubic B-spline fits in real millimetres, and IoU / edge-distance scoring against the source.
     This is how the paper bomb reached emblem IoU 0.99.
   - For a hand-drawn mark, enter the polygon by hand (the `pines_trace.py` pattern).
2. **Cutter.** Offset and extrude the outline into a closed cutter.
   - V-cut strokes (inscriptions, kokuin): a triangular or trapezoid section swept along the stroke's centreline.
   - Flat-bottom recesses (panels, window reveals): a straight extrude with a small draft.
   - **Through-cuts** (hibukuro windows, the fire box's openings): a cutter that passes right through.
3. **Boolean** difference on the carved part, solver `MANIFOLD` (4.4 item 4) [M]. Then **bevel the cut's rim**,
   0.5-1.5 mm, 2 segments. Carved stone has softened but crisp arrises; a zero-radius rim reads as CG.
4. **Weather after cutting.** Moss or dirt in the grooves goes in the masks (4.11), and any SDF opening (3-8 mm) is
   applied after the cut. The opening also softens the carving, so keep r below half the stroke width.

**Minimum stroke** [E, from 5.12 px/cm and Nanite's 1 px target (4.14)]:
- **Geometry strokes:** ≥ **6 mm** wide (≥ 3 texels at 5.12 px/cm, about 7 px on screen at 1 m, 2-3 px at 3 m) and
  ≥ **3 mm** deep, or 0.5 x the width for V-cuts. The stroke must also cover ≥ 2 Nanite edges across (2-3 mm
  segments along the rim).
- **Finer strokes:** thicken them to 6 mm if the design allows, or drop them. Do not fake them with a normal map on
  a hero piece. At 10.24 px/cm (hero close-up) the texture limit halves to 3 mm, but the geometry rule stays.
- **Lantern window openings** follow the sheet's measured proportions, and their reveals show full stone depth (S6).

**IP:** every mark, crest and inscription is our own design (3.2). Font glyph outlines are someone else's design, so
check the font licence before cutting text. Prefer strokes we draw ourselves.

### 4.9 Stage c: natural rocks and boulders (the SDF pipeline)

#### 4.9.1 Why the simple methods fail
- **Noise-displaced sphere:** no planes, no arrises, the same detail everywhere: a potato, or "smooth sine mountains"
  (our round 5) [M].
- **Plane-chipped convex hull** (the pine D rock, `Scripts/vegetation/rock.py`): planes at one scale, every arris
  knife-sharp, no concavity: "a big faceted block" [M].

Artists build rock in three passes: primary silhouette and planes, secondary fractures and edge breaks, tertiary pits
and chips [78][79][80]. The SDF pipeline does each pass with one controlled operation.

#### 4.9.2 The pipeline [C 7.2; end-to-end chain U5.2]
**Evidence status.**
- **Measured:**
  - the node names below exist in 5.2 (`probe_api_5_2_out.json`);
  - SDF Offset opening/closing and Grid to Mesh at threshold 0 work on a 1 m cube (`probe_sdf_offset.py`);
  - the non-SDF boulder path (`probe_boulder_bake.py`: bmesh hulls with random-direction chip planes, a voxel REMESH
    modifier, noise applied to the mesh, decimate, bakes) runs, with the timings in step 8.
- **Not run on a rock:** SDF union, crack subtraction, Fillet, joint-set chips and Grid to Mesh.
- **So the chain below is [U5.2]** until the probe in 8.3 step 0 runs. If the SDF chain fails or is too slow, the
  measured voxel-remesh path is the fallback: the same stages, with the rounding done by remesh + smooth instead of
  an SDF opening. Its arris control is weaker [E].

Nodes: `GeometryNodeMeshToSDFGrid`, `GeometryNodeSDFGridOffset`, `GeometryNodeSDFGridBoolean`,
`GeometryNodeSDFGridFillet`, `GeometryNodeSDFGridMean`, `GeometryNodeSDFGridMedian`, `GeometryNodeSDFGridLaplacian`,
`GeometryNodeSDFGridMeanCurvature`, `GeometryNodeGridToMesh`, `GeometryNodeSampleGrid`.

0. **Clear the default scene first.** `--factory-startup` loads a Cube, Camera and Light; a boulder at the origin sat
   inside the 2 m cube and **every AO bake came out 0.0** (0.95 median on a clean scene) [M].
1. **Lobes (primary).** 1-4 convex hulls from jittered ellipsoid points, sized and placed from the **traced front and
   side outlines**. Chip each with 10-25 planes at 0.72-0.95 of its radius, never on the ground side. For cliff and
   joint-block rock, use **2-3 parallel plane families (joint sets)**, not random directions: that is what makes
   granite read as granite and not as a crystal.
2. **Union.** Mesh to SDF Grid per lobe (voxel 0.5-1 cm for a 1-2 m boulder), SDF Boolean union. A small **closing**
   (+r then −r) or **SDF Grid Fillet** rounds the concave cleft where lobes meet.
3. **Round the arrises (the key step): an opening.** SDF Offset −r, then +r. Rounds every convex arris to radius r and
   leaves flat faces in place. Probe: 1 m cube, r = 0.10 → corner extent 0.866 → 0.788 (theory 0.793), dimensions
   unchanged [M].

   | Rock class | r as a share of the short axis |
   |---|---|
   | fresh talus, quarry spoil | 1-3 % |
   | tree rock, cliff chunks | 4-8 % |
   | rubble lumps (4.6) | 4-12 % |
   | jointed boulders (3.9: arris 10-30 % of block) | 10-20 % |
   | river boulders | 15-30 % |

4. **Cracks (secondary).** SDF Boolean difference of thin slabs along 1-3 planes that belong to the joint sets: 1-3 cm
   wide, widening toward the surface, 10-40 cm deep. Then a small opening so the lips round too.
   Tafoni pits: small SDF subtractions of noisy spheres on vertical faces, in this same SDF stage.
5. **Mesh.** Grid to Mesh with **Threshold 0**. The node default is **0.1** (a density-grid default): on an SDF it
   meshes the 10 cm offset surface, or nothing if the band is thinner [M, node default read in the probe]. **Band
   width ≥ r / voxel + 3 voxels**, or the offsets clip.
6. **Masks, then meso noise (tertiary), on the mesh.** The first version put the noise before meshing, where a grid
   has no normal to displace along. Order:
   1. Compute the arris mask on the meshed surface: convex curvature, or the SDF Mean Curvature grid sampled to
      the vertices [U5.2].
   2. Displace along the vertex normal, 2-3 octaves (probe: 3 cm @ 2/m, 1.2 cm @ 6/m, 4 mm @ 18/m) [M, from the
      non-SDF probe]. **Mask it down on the rounded arrises and up on flat faces and in clefts**, so the opening's
      rounding survives.
   3. Put the finest octave (≤ 4 mm) **after** any further remesh, or into the bake. A 1 cm voxel remesh after the
      noise erases it.

   Equivalent alternative: add the noise field to the SDF values before step 5 (this moves the isosurface along the
   gradient, which is the normal). It is cheaper, but masking by curvature then needs the Mean Curvature grid.
7. **Density.** Decimate or remesh to the **shipped mid mesh** of 4.9.5 (50-150k tris for 1-3 m) from the dense
   source (0.5-2 M).
8. **UVs and bakes** per 4.9.5. Probe timings, non-SDF path, 3-lobe boulder about 1.4 m, **CPU** [M]:
   - voxel remesh at 1 cm: 77k quads in 0.05 s; displacement 0.08 s;
   - decimate COLLAPSE 154k → 4k tris: 0.7 s;
   - smart-project UV on the **4k** low: < 0.1 s;
   - normal bake (tangent, selected to active, cage extrusion 3 cm, EXTEND margin): 0.2 s at 1k, 0.8 s at 2k;
   - AO bake 2k at 64 spp: 5.9 s.
   
   The same steps on a 50-150k mid are not probed [U5.2] (4.19 has the estimates).
9. **Collision:** the lobes are convex before the union, so they are ready-made UCX hull sources (4.13).

Checks for closed input: voxel remesh and SDF need manifold meshes; count `not e.is_manifold` edges = 0 after chips
and fills.

#### 4.9.3 Sub-types
- **River boulders:** large opening radius, gentle noise, lobes elongated along the flow; wet band mask below a
  waterline height (albedo −20-35 %, smoother); moss only above the splash line.
- **Cliff / outcrop chunks:** joint-set planes, a few strata slices (cut into layers, scale each slightly, rejoin
  before the opening) [23]; designed to be kitbashed and overlapped, bottoms buried.
- **Scree / rubble:** the 4.6 library with a small opening radius.
- **The tree rock:** traced outlines (the visual hull stays the 2D authority) split into 2-4 lobes along the trunk
  crack; joint-family chips; union; opening r = 5-8 %; cracks where the roots go; the root walk over the **final**
  surface (BVH, as in `build_pines.py`); a separate base-mound mesh (appendix 8.3).
- **Own Voronoi fracture** for cliff faces: Cell Fracture is not bundled in 5.2 (an extension; a download needs the
  user's go) [74][M]. Not needed: repeated `bmesh.ops.bisect_plane(clear_outer=True)` on copies with the seed
  bisector planes gives each cell [75]; `mathutils.geometry.points_in_planes` gives hull-from-planes [M].

#### 4.9.4 The rock-parts set (when the user wants our own rock kit)
5-10 jointed blocks + 3-4 cleft hero rocks + 10-20 scatter chips and cobbles of the same rock, all from one spec
(joint-set directions, grain, colour). Assemble boulders, banks and small cliffs from them with overlap and burial
(the Valley of the Ancient / Ghost of Tsushima model at our scale [24][26]).

#### 4.9.5 The shipped rock: one UV plan (decided)
SDF and voxel output has no UVs, and smart project on a 300k mesh is untested. The first version said to "ship the
Nanite high" and bake onto a 2-6k low, which left the shipped mesh without UVs. **The plan for every unique rock up
to about 4 m:**

**(a) A UV'd mid-poly Nanite mesh, baked from a denser source.** This is the owned scanned rocks' pattern
(Fisherman's 1.3-2.9 m rocks: 78.6-80.0k Nanite tris with a unique normal and mask) [M].

| Item | Value |
|---|---|
| Dense source (bake only, never shipped) | 0.5-2 M tris from 4.9.2 step 6 (SDF or voxel path) |
| **Shipped Nanite mesh** | **50-150k tris** for 1-3 m (≈ 2-5 mm edges on arrises, 1-2 cm on faces; 4.14); up to ~300k for a 3-4 m hero |
| UV0 | unique, **few charts**: seams on the buried underside and in cracks; smart project or angle-based on the mid, then `pack_islands` (rotate, margin 0.008). Probe the speed and chart count at 150k before relying on it [U5.2] |
| Bakes (dense → mid, 4.10) | normal (DirectX), AO → ORM.R, roughness → ORM.G, mask (R moss, G lichen, B wet/dirt), cavity/curvature |
| Map size | 5.12 px/cm, capped: 1K for < 0.5 m, **2K for 0.5-2 m**, 4K for 2-4 m heroes only |
| UV1 | a second non-overlapping 0-1 set for Fab (4.12), or the documented Nanite exception (4.18) |
| Non-Nanite fallback / Fab LOD statement | Unreal's Nanite fallback from the mid (5.2), plus for Fab a 2-6k LOD mesh decimated from the mid **sharing its UV0** (bake once, reuse the maps) |
| Material | `M_ST_RockUnique`: UV0 unique normal + ORM + mask, tiling detail normal on top (5.4) |

**(b) Only for rock beyond one texture's reach**: cliff pieces over about 4 m, and long outcrops where 4K gives
< 2.5 px/cm. Ship the mesh without unique maps:
- vertex-colour masks: A moss, R grime/value, G edge wear, B wet;
- **local-space** triplanar tiling granite plus a macro layer (`M_ST_Triplanar`; world space swims under random yaw,
  5.4);
- form from geometry alone.

`M_ST_RockUnique` therefore always expects UV0 unique maps. `M_ST_Triplanar` takes class (b). No rock ships
without one of the two.

### 4.10 Stage e: high-to-low bakes
- Use `pipeline.textures.bake_ao` and the house bake settings (Cycles, selected-to-active with a cage, margin type
  **EXTEND**, not 5.2's default Adjacent Faces) [ASSET_GUIDELINES 3].
- **Normal:** tangent space, then DirectX via `textures.flip_normal_green` (pick one flip route, never two).
- **AO → ORM.R** (a baked value, never a constant). Roughness in G, metallic 0 in B (`textures.pack_orm`).
- **Curvature** from the baked normal by numpy divergence dNx/du + dNy/dv (probe p1/p99 −0.19 / +0.18) [M].
  Pointiness is density-dependent and patchy on decimated meshes [73]. The SDF Mean Curvature grid sampled to vertices
  is a second source for the high poly [U5.2].
- **Mask map** (R moss, G lichen, B wet/dirt) for unique-UV rocks, from the 4.11 rules.
- Gotchas [M]: `hide_render` on the low poly makes the bake refuse; move the low poly away or bake the high's AO
  first. The target image must be the active Image Texture node in every material of the low poly (`bake_ao` does it).
- Kit masonry with tiling UVs does not bake per piece; its per-stone data lives in vertex colour (4.11).

### 4.11 Stage d: textures, material library and weathering data

**Library** (`Scripts/dojo/materials/`, README v1.1.0) [M]: `M_DJ_Granite` (Granite set, 2048 px over 4 m = 5.12
px/cm; chipped facets at 3.5 and 9 cm, chisel grooves, pits, sparse biotite/feldspar), `M_DJ_GraniteRubble`
(dry-laid polygon tile, moss in joints), `make_material`, `box_uv`, `bake_wear` (the `Wear` corner colours: R grime,
G edge wear, B dirt). The kit adds `sk_shared.granite_moss_variant` / `kit_material` recipes (`M_DKT_WallGranite`,
`M_DKT_StepGranite`, `M_DKT_StepRiser`, `M_DKT_JointDark`).

**Split the granite for kit stone** [C 8.1]:
- A **micro** tiling set: grain, mica sparkle, speckle under 5 mm; normal strength **0.15-0.3**; no 3.5 / 9 cm facets
  on stones that carry geometric relief (stacking them made r0's "sponge").
- Grain as three thresholded multi-scale noises (pale quartz, white-to-pink feldspar, ~4 % black biotite); speckle
  1-5 mm, ≤ 5 % area (S10).
- Grade the tint toward the reference's measured stone hue (~32°, sat ~0.24 on the landscape walls) under the
  reference-matched daylight rig. SG11 applies in Blender and again in Unreal after `G.look()`. The README's
  s < 0.20 / R/B 1.00-1.20 is retired for stone (3.11).
- **Changing the shared library** is the library owner's call; kit variants live in the kit (`KIT_MATS`).

**Per-stone macro variation in vertex colour** (Blender, baked into the asset) [C 8.1]:
- albedo offset ±8-12 % value, ±3° hue per stone; darker undersides; lighter weathered tops; grime streaks down from
  joints and ledges.
- `sk_shared.stone_tone` already writes per-stone grime and top wear into `Wear`. Extend with a hue offset; UE imports
  **one** vertex-colour set, so pack carefully: R grime/value offset, G edge wear, B dirt/wet, **A moss** (the dojo
  convention read by `lib_colour`) [M]. A lichen mask needs either a texture mask or a channel trade (decide per kit).

**Moss and lichen masks** [C 8.2]:
```
moss   = smoothstep(normal_z, 0.3, 0.5) x cavity_or_AO x joint_proximity x breakup_noise(2-3 scales)
lichen = exposure(convex curvature, high AO) x spot_noise(Voronoi F1 thresholded to 2-15 cm round patches)
wet    = below(waterline + noise) or rain_exposure
```
- Moss on boulders: tops and shaded-side clefts. Moss on walls: joints, ledges, the foot. Never on overhangs.
- Kit pieces: masks in vertex colour. Unique-UV rocks: a baked mask texture.
- Unreal adds the world-space top blend, per-placement tone and wetness on top (5.4).

### 4.12 Stage e: UVs and texel density

| Class | UV0 | Maps | Texel | Notes |
|---|---|---|---|---|
| Kit masonry | box UV per stone in tile units with a random per-part offset (`sk_shared._box_uv`, `BOX_UV_MATS`) | library tiling sets + vertex colour | 5.12 px/cm (`--texel 5.12`) | UV0 overlap / tile range waived; never mirrored |
| Unique boulders up to ~4 m (4.9.5 a) | unique on the **shipped 50-150k mid** (smart project or angle-based, seams on the hidden side; `pack_islands` rotate, margin ~0.008) | baked N, ORM, mask + tiling detail in the material | 5.12 px/cm unique (1K / 2K / 4K by size, 4.9.5); detail adds 10-20 px/cm | scanned 8K maps make texel density inconsistent; a tiling detail layer is the fix [94] |
| Cliff pieces > ~4 m (4.9.5 b) | none unique (a box/lightmap UV1 only) | vertex-colour masks + local triplanar | tiling 5.12 | `M_ST_Triplanar` |
| Lanterns, carved stone | unique or triplanar | library + baked AO | 5.12 (10.24 hero close-up) | box UVs on round parts seam |
| Trim option (coping, sills) | strips of a trim sheet | trim atlas | 5.12 | long straight dressed members [96] |

- **UV1 (lightmap)** is required by Fab on every static mesh: non-overlapping in 0-1, Lightmap Coordinate Index 1
  (ASSET_GUIDELINES 3, 11). The f1 kit dropped UV1 on its Nanite pieces because the two R200 flights failed UV1
  overlap [M]: fine for the game, **blocks Fab**. Restore it before any Fab release.
- Nanite takes at most 4 UV sets (tree study, [M] 5.8 source).
- Rounded rocks want one or few charts (UV seams split vertices, raise Nanite cost and break displacement).

### 4.13 Stage f: collision, walkable tops and GASP

**Collision per class:**
| Asset | Collision |
|---|---|
| Wall modules | `UCX_<node>_NN` boxes/convex per module (one hull per batter segment): **flat vertical faces and a flat top** at the coping's walking height. The render face has batter, crowns and chips; the collision face must not snag a sliding capsule |
| Steps / flights | one convex **ramp** through the tread midpoints (kit: 25.97-26.43°, 8.3 cm lip) + flat landing boxes [M] |
| Paving, kerbs | flat boxes; kerbs their own boxes |
| Lanterns | post box + lamp box, the recorded "thin upright" responses [M] |
| Boulders ≤ 1 m | 1-3 convex hulls, or none for pebbles and small scatter (NoCollision, Can Ever Affect Navigation off). A UCX-less `SM_` fails `qa_check` by default (`require_ucx=True`, ASSET_GUIDELINES 6.4): call `qa_check(..., require_ucx=False)` (CLI `--no-ucx`) **for those pieces only**, and record the waiver `"no_ucx": "NoCollision scatter"` in the export report and the README collision statement |
| Boulders 1-4 m, cliff rocks | 3-8 hulls (from the lobes) fitted to the walkable/climbable surfaces, **tops flattened** where the player stands or mantles |
| Huge walkable cliffs | complex-as-simple on a purpose-built low mesh via `UStaticMesh.ComplexCollisionMesh` (a few thousand tris), **not** on the Nanite fallback [M] |
| Tree rock | UCX on the rock + trunk hulls; canopy none (tree study) |

- UCX rule (measured, ASSET_GUIDELINES 6.2): `UCX_<render mesh NODE name>_NN` (with LODs `UCX_<base>_LOD0_NN`), one
  convex hull per UCX, Auto Generate Collision OFF when UCX present. `helpers.make_ucx_hull(obj, index, max_verts=32)`.
- Keep ≤ 8 hulls per rock (Chaos cost scales with hulls and vertices) [S].
- **Physical material** `PM_Stone` on stone (footsteps, kunai impacts), `PM_StoneWet` / `PM_Moss` if the game uses
  surface types (proposal).
- **Camera:** big rocks and walls block Camera; rubble under 0.5 m ignores it (no spring-arm pops).
- **Navigation:** walls, steps and boulders affect the navmesh; decorative rubble does not.

**GASP traversal (measured, DojoLab 5.8.3, `WorkFiles/dojo/build/GASP_TRAVERSAL.md`)** [M]:
- The forward trace sees only the **Traversable** channel and the hit actor must **be a `LevelBlock_Traversable`**.
  **A plain stone mesh is never vaulted, hurdled or mantled**, whatever its collision.
- Front ledge ≥ 60 cm long; contact clamped 30 cm from the ends.
- **Mantle** up to 275 cm; **hurdle/vault** 0-125 cm over obstacles ≤ 59 cm deep; **10-50 cm cover matches no row**.
- **A top sloped more than ~2° fails the mantle.** Climbable tops need a **flat landing ≥ 0.49 m deep (0.75 used)**.
- Capsule r 30 cm, half height 86 cm; **MaxStepHeight 45 cm**; **walkable 44.77°**; jump apex 1.28 m.

**For stone assets that means:**
1. Every climbable top (copings, terrace tops, plinths, flat boulders on routes) carries a **`traversal` box in
   `kit_catalog.json`** (piece space) so the level builder places the hidden `LevelBlock_Traversable` marker
   automatically, **and** a flat UCX top (≤ 2°, ≥ 0.5 m deep, ledge ≥ 0.6 m).
2. Rocks meant to be climbed are **flattened in collision** even if the render top is domed; rocks that must not be
   climbed present faces steeper than 44.77° and get no marker.
3. No 10-50 cm rubble or low walls on routes: make cover ≥ 50 cm or ≤ 45 cm (steppable).
4. Stone steps: risers ≤ 45 cm are walked; the kit's 16.7 cm risers and 26° ramp pass.

### 4.14 Stage g: LOD and Nanite
- **Nanite for every stone mesh over ~2k tris** (dojo rule), opaque, **Shape Preservation None**. Stone is never
  masked (no alpha moss cards on faces).
- **Smooth normals, few hard edges, few UV seams.** Epic wants vertices < triangles; 3:1 is fully faceted and
  expensive [31][37]. Owned scanned rocks sit at 0.59-0.60 verts/tri [M]. Proposed gate: **verts/tris ≤ 1.0 warn,
  ≤ 2.0 fail** (pipeline owner's call).
- **Density by pixel footprint**, not a triangle count: Nanite targets 1 px per triangle edge
  (`r.Nanite.MaxPixelsPerEdge = 1.0`) [M]; one pixel spans about d / 1280 at 2560 px wide and 90° FOV (0.8 mm at 1 m,
  2.3 mm at 3 m, 8 mm at 10 m).

  | Feature | Source edge length |
  |---|---|
  | silhouette arrises, nosings, chips, joint rims (read at 1-3 m) | 2-5 mm along the edge |
  | crowns / pillow relief | 1-2 cm |
  | buried backs, cores, undersides | as coarse as possible |
  | cliff faces seen from ≥ 10 m | 2-5 cm + detail normal |

- **Measured budgets:** footing 4 m module 117,657 tris; `StairOpening_H4` 386k; flights 5.6-121k; wall track 2.96 M
  LOD0 total, stairs 0.68 M [M]. A shipped 1-3 m rock is 50-150k (4.9.5; up to ~300k for a 3-4 m hero); scanned
  1.3-2.9 m rocks run ~80k.
- **Avoid near-coplanar stacked surfaces** (Nanite draws both); the kit's 8 cm joint recess is good. Merge piles of
  small rocks into one surface rather than stacking dozens of closed rocks [60].
- **Non-Nanite** pieces (small props under ~2k tris, Fab non-Nanite fallback) ship LOD0 > LOD1 > LOD2 strictly
  descending via `helpers.decimate_lods` (0.5, 0.25).
- Import at 1:1; never import tiny and scale up (the distance field resolution is per mesh) [31].

### 4.15 Stage h: QA and export
- **Export only through `pipeline.export_fbx`** after `pipeline.qa_check` (CLAUDE.md). `--texel 5.12`.
- **Waivers are not qa_check options.** `qa_check` has parameters only for `require_uv1`, `require_ucx`,
  `texel_density`, `tolerance`, `uv0_tile_range` and the check toggles [M].
  - **The UV "waiver set" is a post-filter** in the stone kit's own code:
    - `sk_shared.WAIVE = {"uv0_tile_range", "uv_no_overlap"}`;
    - `qa_piece` runs `qa_check` and then drops the failures named in `WAIVE` from the hard fails, listing them as
      `"waived"` [M, `sk_shared.py` 59, 362-368];
    - `build_wall.py` applies the same filter inline.
  - A new kit copies that pattern (or imports `qa_piece`) and writes the waived names into `qa_report.json`.
  - Unique-UV rocks pass with no UV waiver.
  - Nanite pieces currently run with `require_uv1=not p.nanite` (the Nanite UV1 exception, 4.18).
  - UCX-less scatter runs with `require_ucx=False` (4.13).
- Vertex colours are written `colors_type="SRGB"` by the exporter; Unreal must import them with **Replace** (5.2).
- LOD pieces: `Import Mesh LODs ON`, UCX `_LOD0_NN` naming.
- Sockets: Empties + `.sockets.json` sidecar (lantern light points, rail attach points).
- **Verification:** fresh-process FBX re-import (`Scripts/dojo/stonekit/verify_stairs_fbx.py --all` pattern: LOD
  counts, UCX keyed to the render node, slots, sizes = catalogue), then the Unreal verify in a second fresh process on
  the exact bytes (5.12). f1 passed 71/71 in Blender; Unreal not yet run [M].

### 4.16 Stage i: the Unreal import and material recipe (summary; details in section 5)
1. **Import** with the **legacy FBX importer** (`Interchange.FeatureFlags.Import.FBX=0`; ASSET_GUIDELINES 6.5):
   - FbxImportUI settings:
     - Import Normals + MikkTSpace; Convert Scene and Convert Scene Unit ON; Force Front XAxis OFF; Uniform Scale 1.0;
     - **Do Not Create Material** (`import_materials` / `import_textures` off);
     - Auto Generate Collision OFF, One Convex Hull per UCX, Import Mesh LODs ON;
     - Generate Lightmap UVs off on Nanite pieces;
     - Vertex Color Import Option **Replace**.
   - Nanite on, Shape Preservation None.
   - **Fallback per 5.2, with `FallbackTarget` set explicitly.** Under AUTO the error and percent values do nothing
     [M]. Verification import: RELATIVE_ERROR with RE 0 (bounds gate). Shipped: RELATIVE_ERROR ~1, or the percent
     target at 5-15 %.
   - RT proxy on at its 2.0 default.
   - BC sRGB, ORM Masks linear, Normal DirectX (no flip).
   - UCX count equals the shipped hulls.

   **Where these settings live:** `Scripts/dojo/unreal/dj_sc_import.py` (`mesh_options()` for the FbxImportUI, and
   the Nanite fallback block after import, lines ~136-150) and `Scripts/dojo/unreal/dj_sc_verify.py` for the fresh
   second-process checks [M]. A new stone kit extends those two scripts, or copies them into its own
   `*_import.py` / `*_verify.py`. It does not write a third importer.
2. **Materials:** instances of the stone master family (5.4): `M_ST_Masonry` (kit masonry), `M_ST_RockUnique`
   (our and scanned rocks), `M_ST_Triplanar` (round parts, rock cores). Never import FBX materials.
3. **Collision profile** + physical material; traversal markers from the catalogue's `traversal` boxes.
4. **Placement:** hand/script from the catalogue snaps for masonry (Packed Level Actors for repeated assemblies);
   PCG for scatter (5.8).

### 4.17 Reusable module plan: `Scripts/stone/` (proposal)

Other chats own `Scripts/dojo/stonekit/` (lock `dojostonekit`) and `Scripts/vegetation/` (pines). A neutral library,
created under its own lock, that the dojo kit and future kits import:

| Module | Content |
|---|---|
| `Scripts/stone/stone_geo.py` | dressed stone, slab, block and lump builders lifted from `kit1_geo` (`pillow_face`, `rough_block`, chips) behind stable signatures; per-corner radius, asymmetric crown; `kit1_geo.Geo` stays the container |
| `Scripts/stone/stone_layout.py` | coursed (broken courses, stagger, no 4-way), power-diagram + Lloyd, guillotine paving, sangi-zumi corners, gap finder for packing stones; the layout statistics of 6.1 |
| `Scripts/stone/stone_sdf.py` | builds and applies GN node groups from Python: SDF union, opening/closing, crack subtract, Grid to Mesh at threshold 0 with a safe band width; voxel-remesh fallback |
| `Scripts/stone/stone_bake.py` | high to low: clean scene, cage, normal/AO bakes via `pipeline.textures`, curvature from the normal, mask bakes |
| `Scripts/stone/stone_weather.py` | per-stone tone, moss / lichen / wet masks to vertex colour or a mask texture (extends `sk_shared.stone_tone`) |
| `Scripts/stone/stone_trace.py` | the tracer: writes `References/<Item>/trace_<crop>.json` in the 6.8 schema (hand-entered polygons, optional dark-joint seeding); **does not exist yet** |
| `Scripts/stone/stone_measure.py` | the reference and render measurements (6.1, both value methods, SG1-SG13 from a trace + an image), numpy + PIL only (no scipy / skimage / cv2 on this PC) [M]; **does not exist yet** (scope 6.8) |

House shape [M]: `build_<kit>.py` run as `blender -b --factory-startup --python ... -- args`; a spec JSON;
`{measure,qa_report,export_report}.json`; a `run_all.sh` chaining textures, build, render and compose. Moving code
out of `kit1_geo` / `sk_shared` is a refactor of other chats' files: do it only with their lock and the user's go;
until then, import them.

### 4.18 Pipeline and shared-code changes this study asks for (NOT made)
- `qa_check`: a Nanite gate on verts/tris (warn > 1, fail > 2).
- **The fallback split.** Separate the **verification** fallback (RelativeError 0, used for the bounds gate) from the
  **shipped** fallback (~RE 1 or 5-15 % triangles). Leave the RT proxy at its 2.0 default (5.2).
  - **Gotcha:** set `fallback_target` explicitly: `unreal.NaniteFallbackTarget.RELATIVE_ERROR` for an error, or the
    percent-triangles member for a percent (the enum member name is [U5.8]).
  - `dj_sc_import.py` measured that under `AUTO` (the default) `fallback_relative_error` and
    `fallback_percent_triangles` **do nothing**. The engine decimates anyway, and the bounds grew 0.5-27.6 cm on
    38/38 meshes [M, `dj_sc_import.py` 136-150].
  - Today that script forces RELATIVE_ERROR with RE 0 on every Nanite mesh. The shipped split therefore needs a
    second, explicit setting (a flag or a post-verify pass), or it silently ships the full-resolution fallback (P22).
- `kit_catalog.json` schema: a per-piece `traversal` box.
- Library: a height-blend lerp for moss / dirt / wet and a lichen layer (the pines notes already flag the lichen
  overlay missing from the kit master).
- **An RVT ground seam** (5.4 step 7): a Runtime Virtual Texture volume over the play area, with the ground
  materials writing to it. Nothing in DojoLab or `Scripts/dojo/unreal/*.py` creates one today [M, grep]. Owner: the
  dojo ground / level chat. The stone master reads it behind `UseRVT`.
- **Our own `MF_ST_GroundBlend`**, written from Epic's RVT documentation [50]. `MF_VTGroundBlend` in Scenery_Tutorial
  is Epic sample content: it may be studied, and used in the game project, but never copied into a Fab pack.

**ASSET_GUIDELINES exceptions this study needs.** They are proposed, NOT made: the user or the guidelines owner
adds them, or a later session will flag the stone kit as non-compliant.

| Guideline | Conflict | Proposed exception text |
|---|---|---|
| **1. Whole-metre modules** | the stair track uses a 1/6 m riser and 1/3 m tread grid, and 1.2 / 1.8 m flight widths [M] | "Stair and step kits may use a declared sub-metre grid (riser / tread units, stored in `kit_catalog.json` `units`). Wall runs stay on whole metres." |
| **2. Triangle budgets** (prop 1-5k, background 0.5-2k) | Nanite stone modules are 50-400k; `StairOpening_H4` is 386k; the wall track is 2.96 M [M] | "Nanite static meshes: budget by edge length and pixel footprint (STONE_BUILDING_STUDY 4.14), typically 50-400k per stone module and 50-150k per 1-3 m rock. Gate verts/tris ≤ 1.0 and the per-scene ms budget (5.10) instead of a triangle count. The existing budgets stay for non-Nanite meshes." |
| **4. UV1 on every static mesh** | the stone kit ships Nanite pieces without UV1 (`require_uv1=not p.nanite`) [M] | "Nanite pieces used only in our game (Lumen, no baked lighting) may ship without UV1 and must record it in the export report. **Any Fab release restores UV1** (non-overlapping, 0-1, Lightmap Coordinate Index 1)." |
| **6.4 UCX required** | pebbles and small scatter are NoCollision | "`require_ucx=False` is allowed for NoCollision scatter under 0.5 m, recorded in the export report and README." |
| **6.4 UV0 overlap / tile range** | kit masonry uses box UVs in tile units | "Tiling-material kit pieces may waive `uv0_tile_range` / `uv_no_overlap` through the kit's `WAIVE` post-filter; unique-UV meshes may not." |

Each change needs its owner's OK (pipeline owner; PackMaterials lock for `Scripts/unreal/materials/`; dojo materials
owner; dojo ground/level owner for the RVT; the user for ASSET_GUIDELINES).

### 4.19 Cost and time per stage (for planning rounds)
The user's `stop-before-expensive-work` and usage-cap rules need these to plan a round. [M] numbers are from this
PC; [E] numbers are extrapolations to confirm on the first run.

| Stage | Cost | Evidence |
|---|---|---|
| Wall track build (65 pieces, headless, incl. QA and export) | **678 s (about 11 min)**, about 10 s per piece | [M] `wall/build_f2.log` |
| Stair track build (39 pieces) | **115 s** | [M] `stairs/build_f2.log`; catalogue `seconds` 113.8 |
| Judge-round render set (Cycles, GPU) | **30 stills in 2 min 18 s** (≈ 4.6 s each) | [M] `wall/render.log` |
| Closer stair match renders | 8 stills in ~46 s | [M] `stairs/render_cu.log` |
| Rock, non-SDF path to a 4k low with 2K bakes (CPU) | < 10 s | [M] probe |
| Rock bake onto a 50-150k mid at 2K / 4K | 2K AO 64 spp ≈ 6-15 s CPU; 4K ≈ 4 x that (25-60 s); GPU (OptiX, RTX 4070 SUPER) typically several times faster | [E] from the probe's 5.9 s at 2K on a 4k low |
| SDF rock at 5 mm voxels, 1-2 m boulder | sparse narrow band: about 0.5-2 M active voxels, tens of MB | [E]; probe step 0 (8.3) measures it |
| SDF on a whole 4 m wall module at 5 mm | about 25 m² of stone surface x a 12-voxel band ≈ 12 M voxels, ~100 MB | [E]. **Not planned:** wall stones are analytic per stone (4.4); SDF is used only per lump or rock |
| Tracer + measurer (6.8), one-time | 2-3 sessions writing the tools, plus about 1 h per traced crop (8-9 crops for the dojo): about 3-4 sessions in all | [E] |
| Unreal import + verify of a whole kit (commandlet) | not recorded for the stone kit; measure on the first run and add it here | [U5.8] |

**Round planning rule.** A judge round (build one track + renders + measure + judges) is about 15-25 min of machine
time on this PC [E from the rows above]. A full f3 is 3-4 staged rounds (8.4), plus the tool work. Say so, and wait
for the user's go before the first round.

---

## 5. Unreal 5.8 setup

### 5.1 Project state that matters for stone (DojoLab, read-only) [M]

| Item | Value |
|---|---|
| Engine | 5.8.3, CL 58210709; GPU RTX 4070 SUPER |
| Nanite | `r.Nanite.ProjectEnabled=True`, `r.Nanite.Foliage=True` (also turns on Assemblies and Voxels) |
| Substrate | `r.Substrate=True`, **Blendable GBuffer** (`r.Substrate.ProjectGBufferFormat=0`, one closure per pixel) |
| Lumen | GI + reflections; **`r.Lumen.HardwareRayTracing=1`** at runtime; RT proxies enabled for the project |
| Distance fields | on (`r.GenerateMeshDistanceFields`, `r.Lumen.TraceMeshSDFs=1`) |
| Decals | `r.DBuffer=1`; 86 weathering decal actors |
| Shadows | VSM; `r.Shadow.Virtual.ResolutionLodBiasDirectional=-1.5` |
| Collision | channel `ECC_GameTraceChannel1` "Traversable", profile `TraversalObjectPreset` |
| Ground | kit 2 **static meshes** (`SM_DGB_Floor_*`, `SM_DGB_Ground_Outside`), **not a Landscape**; no Runtime Virtual Texture volume is created by any `Scripts/dojo/unreal/*.py` [M, grep], so the RVT seam (5.4 step 7) has nothing to sample yet |
| Frame (round 8) | GPU mean 8-14 ms, p95 over 16.7 ms at 1440p; 8.15 M Nanite source tris placed (footing alone 4.12 M) |

Because Lumen runs **hardware RT**, Lumen sees a stone mesh through its **RT proxy** (else the Nanite fallback), not
only its distance field.

### 5.2 Nanite settings per stone mesh (`FMeshNaniteSettings`, 5.8) [M]

| Field | Stone setting |
|---|---|
| `bEnabled` | True |
| `ShapePreservation` | **None** (PreserveArea and Voxelize are foliage techniques) |
| `PositionPrecision` | auto; set explicitly only if hairline gaps appear where modules abut [U5.8]; the kit's teeth and recessed cores hide seams |
| `KeepPercentTriangles` / `TrimRelativeError` | 1.0 / 0.0 (non-zero only for build-time displacement, 5.3) |
| Fallback (`FallbackTarget`, `FallbackPercentTriangles`, `FallbackRelativeError` default 1.0) | **Set `FallbackTarget` explicitly first**: under the default AUTO the other two fields do nothing [M, `dj_sc_import.py` 136-150]. Shipped: RELATIVE_ERROR ~1, or percent 5-15 %. Verification import: RELATIVE_ERROR, RE 0 (bounds gate) |
| RT proxy (`FMeshRayTracingProxySettings`) | on, `FallbackRelativeError` **2.0** default; ~1.0 only for hero rocks whose RT/Lumen silhouette visibly drifts [U5.8] |

- The fields are BlueprintReadWrite, so the import script sets them; `DisplacementMaps` is EditAnywhere only [U5.8].
- **Render bounds** of a Nanite mesh sit 0.5-27.6 cm outside the real surface whatever the fallback (measured round 2,
  `dj_sc_nanite.py`); our bounds gate reads the fallback's vertex box, which is why the verification import uses RE 0.
- **Complex collision on a Nanite mesh is the fallback** (`LODForCollision` indexes the render LODs; LOD0 = the
  fallback). With RE 0 any complex collision is full resolution: use `ComplexCollisionMesh` where complex is needed.
- **Nanite spline meshes** (`r.Nanite.AllowSplineMeshes` default 1): only for constant-section pieces (kerbs, copings,
  gutters). Never bend laid masonry along a spline: it stretches every stone.
- **Nanite Assemblies** (on in DojoLab through `r.Nanite.Foliage`): a wall of repeated stone units could ship as
  parts x transforms; only pays if stones repeat. Untested for static walls [U5.8].

### 5.3 Displacement and tessellation (5.8 status) [M]
- **Build-time displacement** (`FMeshNaniteSettings.DisplacementMaps`): the Nanite builder tessellates and displaces
  once along vertex normals, one map per material index (`Texture`, `Magnitude`, `Center`); needs a single-LOD source
  and `TrimRelativeError ≠ 0` (Epic: default 0.04, keep > 0.02). Vertex colours carry through. No runtime cost beyond
  the triangles.
- **Runtime tessellation** (material `bEnableTessellation` + Displacement; `DisplacementScaling` Magnitude 4.0 /
  Center 0.5; optional `DisplacementFadeRange`): `r.Nanite.Tessellation=1` by default; **the 5.4 project gate
  `r.Nanite.AllowTessellation` no longer exists in 5.8 source**. Runs programmable raster every frame; large
  magnitudes inflate culling bounds and hurt VSM. Introduced as Experimental in 5.4; the 5.8 notes announce no status
  change [39][42]: **not production-proven** [U5.8].
- **Neither is crack-free across UV seams or hard edges** [31]. Collision is never displaced.

| Stone type | Displacement? |
|---|---|
| masonry blocks, ashlar, kerbs, steps, lantern parts | **No.** Model the form; normal map for texture |
| rubble / pillow faces | No: geometry carries crown and relief |
| natural boulders, river stones, cliff faces | optional **build-time** for sub-centimetre relief if the Blender mesh is lighter; runtime only for a hero close-up with a Fade range, magnitude ≤ 2 cm |
| ground around stone | landscape / Mesh Terrain displacement (the user's terrain) |

**Prefer the Blender route** (geometry stays visible to our measurements and judges) unless disk size forces the
Unreal route. Never use displacement or decals to make a masonry form (the height-field lesson, CLAUDE.md).

### 5.4 The stone master family (built as code)

| Master | Mapping | For |
|---|---|---|
| `M_ST_Masonry` | UV0 base maps in tile units (library `box_uv`) + world-space overlays | walls, steps, paving, kerbs, footings, flat-faced carved stone |
| `M_ST_RockUnique` | UV0 **unique** normal + cavity/AO (baked per rock), tiling detail on top | our rocks **and** scanned rocks (Megascans, Fisherman's Cabin) |
| `M_ST_Triplanar` | world- or local-aligned triplanar | round stone (lantern caps, finials), rock cores, long cliff meshes |

One parameter vocabulary and one function stack; static switches (UseMoss, UseWet, UseRVT, UseDetail) rather than
Material Layers (same compiled cost, simpler to build from Python). **Where the code lives:** dojo materials in
`Scripts/dojo/unreal/dj_sc_materials.py` (it already has `lib_colour` / `lib_finish`, `triplanar_normal_ws`,
`actor_hash`, `build_lib_opaque`, `build_lib_triplanar`); pack masters in `Scripts/unreal/materials/` **only under
the PackMaterials lock via `run_build.sh`** (CLAUDE.md).

**Function stack, in order** [B 4.2]:
1. **Base:** BC x Tint, lerp toward MeanColour by FlattenToMean (kit 1's rule), ORM, Normal with FlattenNormal.
2. **Detail normal** (tiling granite grain, 0.25-0.5 m tile) with `BlendAngleCorrectedNormals`, **faded by distance**
   (out by ~15-25 m). This is what makes 1K scans and our 4 m tile hold up at 1 m.
3. **Macro variation** in world space (8-32 m noise on albedo and roughness; `T_MacroVariation` exists; we already do
   `T_DKG_Macro_M` on world XY / 32 m for ground) [M].
4. **Per-placement tone:** actors by position hash (`actor_hash`), ISM/PCG by `PerInstanceRandom` or Per-Instance
   Custom Data; ±5-10 % value, ±2° hue. The Blender per-stone tone (4.11) sits underneath.
5. **Moss / lichen:** exposure (world-up · normal, `WorldAlignedBlend` or a `VertexNormalWS.z` smoothstep, biased by
   world noise) x occlusion (vertex A or the baked cavity) x **`HeightLerp`** (moss fills crevices before crowns).
   Moss colour `#56613A` (linear 0.093 / 0.120 / 0.042), roughness 0.85-0.95, normal flattened under moss. Lichen:
   exposure x spot mask, pale grey-green / ochre.
6. **Wetness:** albedo x 0.55-0.75 on porous stone, roughness toward 0.15-0.3, normal slightly flattened; masks from an
   **MPC water level** (a band a few cm to 0.5 m above the water plane, with noise) and an MPC rain amount x exposure.
7. **Ground seam (RVT blend):** sample the ground RVT (BaseColor/Normal/Roughness + World Height) and blend the
   stone's bottom band by height difference [50]. The pattern is in the owned `MF_VTGroundBlend` and Fisherman's
   "Enable RVT Blend". **Dependency:**
   - The RVT must exist, and the ground's materials must write into it. DojoLab has neither: its ground is kit 2
     meshes, not a Landscape (5.1). Building it is the dojo ground / level chat's job (4.18).
   - Until it exists, `UseRVT` stays off and the seam uses the **fallback** (5.8 Seating): burial, a mesh skirt,
     debris and pebbles, and projected decals.
   - The function we ship is our own `MF_ST_GroundBlend`. `MF_VTGroundBlend` is Epic sample content and never goes
     into a Fab pack.
8. **Look** (`G.look()`: Saturation, ValueMult, TopBleach) last, so Unreal's measured chroma gain is corrected in one
   place [M].

**Engine functions for stone (shipping content, [M]; presence in 5.8's library confirmed by file listing, behaviour
not tested):** `WorldAlignedTexture`, `WorldAlignedNormal`, `HighQualityWorldAlignedNormals`, `WorldAlignedBlend`,
`SlopeMask`, `HeightLerp`, `HeightLerpWithTwoHeightMaps`, `DetailTexturing`, `MacroUVs`,
`TextureVariation(_RotateUV/_RotateNormals)`, `Texture_Bombing`, `BlendAngleCorrectedNormals(_WS)`.

**Vertex colours on Nanite** [M]: Nanite keeps imported vertex colours (import **Replace**). **Per-instance vertex
painting is off on Nanite components** (`StaticMeshComponent.cpp`: "Don't vertex paint on nanite"). Hand-touched moss
on a placed wall: Mesh Paint textures (`r.MeshPaintVirtualTexture.Support`, default on; needs a paint UV and
resolution) [98] or decals. The Mesh Paint Texture material node setup is [U5.8]. Verify the `SRGB` vertex-colour
encoding with a 0.25 / 0.5 / 0.75 ramp through a debug material before trusting mask thresholds [U5.8].

**Triplanar vs UV0:** UV0 box UV for block masonry (cheapest, unmirrored, `space='WORLD'` keeps neighbours
continuous). Triplanar (~3x texture cost) for round stone and big cliffs. `WorldAlignedTexture` **swims** on rocks
placed with random yaw: use local-space (object) triplanar there, or bake UVs. Triplanar normals need
`WorldAlignedNormal` reorientation (`dj_sc_materials.triplanar_normal_ws`).

### 5.5 Substrate (Blendable GBuffer) [M][49]
- **One closure per pixel.** Stone + moss + wet must be **one Slab** with lerped inputs (parameter blend), or Substrate
  operators with "Use Parameter Blending" on. A true vertical layer (a water film over stone) is not available.
- Specular F0 ≈ 0.04 (default). A hint of **Fuzz** on moss gives a soft rim at low sun; whether it survives the
  one-closure simplification at an acceptable cost is [U5.8].
- Substrate still carries Epic's "subject to change" caveat: for a **Fab** stone pack, ship legacy-compatible masters
  (Substrate converts them), not Substrate-only graphs.

### 5.6 Decals on stone
- DBuffer decals work on Nanite and with the Blendable GBuffer; **mesh decals are not supported on Nanite** (use
  projected decal actors) [31][49].
- Good decal jobs: rain streaks under copings and lantern caps, water stains at wall feet, soot above a fire box, a
  damp band at the terrace foot, moss/lichen patches that break the procedural masks.
- Use the **material** for wetness driven by a level or exposure (it follows every rock); decals for one-off marks.
  Keep the master's `MaterialDecalResponse` at the default (Color, Normal, Roughness).
- Decal cost scales with screen coverage; many large overlapping decals at a wall foot: check `stat GPU`.

### 5.7 Lumen, VSM and distance fields
- HWRT Lumen reads the RT proxy: check the **Surface Cache** view for grey (uncovered) cards on deeply concave rocks
  and long wall modules.
- Kitbashed, heavily intersecting rock piles cost Lumen reflections and HWRT ("sensitive to large amounts of instance
  overlaps") [45][46]: merge or reduce.
- Small rubble and pebbles: turn off *Affect Distance Field Lighting* or set DF Resolution Scale 0.
- **Never put WPO or Pixel Depth Offset on stone materials** (both invalidate VSM pages every frame) [48]; do the
  ground seam with RVT, not PDO.
- **Low sun (~9° from the west in the dojo)** exaggerates normal-map pits ("sponge") and hides geometry-less edges:
  arrises must be geometry and normal strength modest (kit 0.18-0.35) [M].
- Epic budgets Lumen GI + reflections at about 4 ms (High, 1080p/60 on consoles); Lumen Lite (Beta in 5.8) is
  described as ~2x faster [46][41, S].

### 5.8 Placement

**Masonry:**
- Kit grid from the catalogue: riser 1/6 m, tread 1/3 m, wall pivot on the face line at the module start, face → −Y,
  0.18 m interlocking course teeth, chaining rules and snaps in `kit_catalog.json` (`how_to_chain`,
  `pieces[*].snaps`) [M]. 16.67 cm is not an editor grid preset: place by script (the dojo level builder) or use the
  snap points.
- Repeated assemblies as **Level Instances**, shipped as **Packed Level Actors** (ISM components, which Nanite likes).
- **Spline-driven walls** (BR village field walls, dry-stone boundaries): PCG Spline Sampler at module length or the
  5.8 shape-grammar `Subdivide Spline` picking straight / corner / end modules. Laid ishigaki (batter, flared
  corners, stair openings) stays script-placed from the catalogue.

**PCG scatter for boulders and river stones** (5.8 PCG nodes present: `SurfaceSampler`, `SplineSampler`,
`SelfPruning`, `DifferenceElement`, `Distance`, `ProjectionElement`, `BoundsFromMesh`, `StaticMeshSpawner`, the
grammar set) [M]:
1. Surface Sampler on the landscape, or Spline Sampler along the river bank band.
2. Filter by slope (normal Z), height above the water level (MPC), distance from paths (Difference), clumping noise.
3. Mesh + scale by size class from a weighted list of 8-20 rocks; big rocks first.
4. **Self Pruning** large to small; Difference against trees and walkways.
5. Random yaw **constrained per cluster** (3.10), small tilt to the ground normal, **sink 15-35 % of height**
   (`BoundsFromMesh`), scale 0.7-1.4.
6. Static Mesh Spawner → ISM (Nanite; HISM gives nothing extra with Nanite [58, S]); per-instance custom data carries
   tone.
7. Pebbles: PCG GPU runtime scatter or landscape grass types, no collision.

**Seating:** sink rocks and footings (kit pieces run 0.35 m below walking level). Stone must work on an unknown
slope: buried foot courses and buried rock volume, not flat bottom faces. No PDO. Hide the contact line, in this
order until the RVT exists (5.4 step 7):
1. **Burial** per 3.10: the contact is below grade.
2. **A mesh skirt:** a thin soil/moss band mesh at the foot of walls and hero rocks (the tree study's base-mound
   idea, 8.3 step 6), in the ground's own material.
3. **Same-rock debris and pebbles** scattered along the line (PCG or hand).
4. **Projected DBuffer decals** (soil splash, damp band; 5.6) where the line still shows.

The RVT blend replaces 2-4 only where the ground writes to the RVT.

### 5.9 Mixing owned scanned rocks with our masonry
1. **Same master.** Re-parent scanned rock instances to `M_ST_RockUnique` **in a staging copy** (they are UE 5.2
   packages; re-save there, not in DojoLab while other workflows run). Their unique normal and cavity drive the form;
   their albedo is replaced by our granite detail set or **tinted to our measured granite median**.
2. **Measure, don't eyeball:** a scanned rock and a kit wall under the same sunset rig: albedo median, saturation,
   R/B and **dE76 < 5** on crops (the materials README method).
3. **Share the world-space layers:** the same macro texture and scale, moss threshold and colour, wetness MPC, RVT
   blend. Differences here read instantly as "two packs".
4. **Match detail frequency:** give both the same tiling detail normal and cap scanned normal strength so crowns do
   not look sharper than our stones. Downsize scan maps to 2K where the rock is under 3 m.
5. **Match scale cues:** granite grain, lichen spots and moss cushions the same world size on both.
6. **Collision:** scans arrive with auto `BlockAll`; replace with hand hulls (≤ 8, flattened climbable tops) on any
   route rock.
7. **Licence:** game only, and only with the user's approval; **never in a Fab product** of ours [63][64][65, S].
   Confirm per-asset terms before any commercial decision [U].

### 5.10 Budgets (proposals; measure on the RTX 4070 SUPER before adopting) [U5.8]

Frame 16.6 ms at 1440p with TSR. Starting split for **all stone in view**: Nanite visibility + raster + base pass
≤ 1.5 ms; VSM for stone ≤ 0.8 ms steady state; stone's share inside Lumen's ~4 ms; decals on stone ≤ 0.3 ms.

| Tier | Distance | Examples | Source tris | Material | Collision | Shadows / DF |
|---|---|---|---|---|---|---|
| **Hero** | 0-10 m | courtyard walls, stair flights, lanterns, footing, pine rock, kerbs | Nanite; arris segments 2-5 mm; typically 50-400k per module | full stack (detail, moss, wet, RVT, tone) | UCX boxes/ramps/≤ 8 hulls; GASP markers | VSM; DF on |
| **Mid** | 10-60 m | terrace runs, stair path, river boulders | same meshes | detail normal fades by ~15-25 m | same | VSM; DF on |
| **Far** | 60-300 m | cliff rocks, far banks, outer walls | library meshes 20-150k; big cliffs up to ~1 M | macro dominant; RVT seam; no detail | hulls only if reachable | VSM; DF for big ones only |
| **Vista** | > 300 m | mountains, far cliffs | landscape / Mesh Terrain / HLOD Approximated | baked HLOD material | none | coarse / none |

Per-piece checks for hero stone: verts/tris ≤ 1.0; Nanite Overdraw shows no hotspots on rubble at the gameplay camera;
`stat GPU` Nanite + ShadowDepths delta for a whole terrace run < 0.3 ms at the courtyard camera; disk per unique mesh
in the asset report (scanned 80k-tri rocks: 4.9-6.9 MB uasset) [M]; unique rock meshes per biome ≤ 20.

**Disk and memory budgets.**

*Mesh data.* Epic gives **14.4 bytes per input triangle**, about 13.8 MB per million triangles, for cooked Nanite
data [105].
- **The current stone kit** [M sizes, E conversions]:
  - FBX on disk: **219 MB** for 104 pieces; the largest is `StairOpening_H4` at 16.1 MB.
  - Wall track: 2.96 M tris ≈ **43 MB** cooked Nanite. Stairs: 0.68 M ≈ **10 MB**.
  - Plus the fallback meshes: small at RE ~1, **full size again at RE 0** (P22).
  - Editor uassets keep the source mesh too. The owned 80k-tri rocks run 60-85 B per triangle on disk, which puts
    the wall track at about **180-250 MB of uasset** in the project [E].
- **Adding the 3 seeds of 4.5.7:** about +2 M tris ≈ +30 MB cooked.

*Textures.* Estimated from BC compression with mips [E]:
- **Per map:** a 2K BC1 map (BaseColor or ORM) ≈ **2.8 MB** resident; a 2K BC5 normal ≈ **5.6 MB**. **One 2K
  BC + N + ORM set ≈ 11 MB.**
- **Kit masonry:** the library sets are tiling and shared [M: `T_DJ_Granite_*`, `T_DJ_GraniteRubble_*`, 2048 px].
  Proposed kit budget: ≤ 3 full 2K sets + 1 micro-detail set (1K) + a macro map ≈ **≤ 40 MB** for all kit stone,
  whatever the kit's size.
- **Unique rocks** (4.9.5 a): N + ORM + mask at 2K ≈ 11 MB each at the top mip.
  - 20 rocks ≈ 220 MB if all were at full resolution.
  - Streaming keeps only the near ones at the top mip. Budget: **≤ 20 unique rocks per biome**, 4K only on ≤ 3
    heroes, and **≤ 150 MB of the texture streaming pool for stone** in a dojo-sized scene [E].
  - Check `stat streaming` and the pool-over-budget warning in the first Unreal pass [U5.8].

*Report.* Every export report lists maps with sizes, formats and estimated resident MB, next to the mesh MB (6.7).

### 5.11 Open-world (battle royale) scale
- Nanite handles per-object detail; **World Partition HLOD** handles region cost [53][54]: *Instancing* for PCG rubble
  and boulders; *Merged / Simplified Mesh* for wall runs and buildings; *Approximated Mesh* for cliffs and whole
  compounds. How HLOD bakes our world-space master (macro, moss, RVT) must be checked at the transition distance
  [U5.8].
- **Unique mesh count is the real constraint** (Lumen scene and memory scale with unique meshes, not instances): a
  library of **10-20 rocks per biome**, reused with scale / yaw / tint.
- **Mesh Terrain** (5.8, Experimental; `MeshTerrainMode`, `MeshPartition`, `PCGMeshPartitionInterop`, off by default)
  does cliffs and overhangs as terrain; a prototype tool, and the landscape is the user's call [59, S].
- **Fab products:** state the engine version; Nanite meshes with a sensible fallback; collision and LOD statements
  (even "zero"); no Experimental-only features as the baseline (ASSET_GUIDELINES 11).

### 5.12 Unreal verification checklist (a second, fresh process on the exact exported bytes)
1. **Import:** settings of 4.16, through `dj_sc_import.py` (or the kit's copy of it). Assert them in the fresh second
   process through `dj_sc_verify.py`:
   - the legacy importer was used; no FBX materials were created;
   - `fallback_target` is the explicit target (not AUTO) with the intended value;
   - UCX count equals the shipped hulls ("stored hull identical" gate).
2. **Nanite views:** Triangles, Clusters, **Overdraw** (rubble piles, joint cores), **Evaluate WPO** (must be none on
   stone), Tessellation only where used.
3. **Material:** a scanned rock next to a kit wall under the sunset: albedo median, saturation, R/B, dE76; moss only in
   joints / ledges / tops; wet band at the waterline; no triplanar swimming on yawed rocks.
4. **Vertex-colour ramp test** for the SRGB export.
5. **Lumen / VSM:** Surface Cache coverage on concave rocks; VSM cached pages static (`r.Shadow.Virtual.Stats 1`,
   invalidations ≈ 0); HWRT shadows from the RT proxy match the silhouette.
6. **Collision:** walk every wall foot, stair and landing; slide along wall faces without snagging; GASP trace gate
   (markers, ledge normals, flat tops ≥ 0.49 m); no 10-50 cm dead cover on routes; no camera pops on rubble.
7. **Performance:** `stat GPU`, `stat unit`, `ProfileGPU` at the courtyard and widest river cameras; record ms.
8. **Blind judges on Unreal captures** vs the reference (6.5), measurements first (6.6). One Unreal commandlet at a
   time on the machine; never leave one running (CLAUDE.md).

---

## 6. Quality gates

### 6.1 Measuring a reference (pixels, never eyeballing) [C 11, A 10]
All in numpy + PIL (`py -3`: numpy 2.5.3, PIL 12.2.0; no scipy / skimage / cv2) [M]. Code: `stone_trace.py` and
`stone_measure.py`, **both still to be written** (scope, schema and estimate in 6.8).
1. **Scale** from a known size in the same image plane: the sheet's 1.8 m figure, a 0.167 m riser, a module length.
   Record px/m per region **and its uncertainty**. The landscape reference needs two scales: **47-50 px/m** at the
   gate steps (from a 0.16 m riser), **17-25 px/m** at the terrace (from the compound wall's plaster band, itself an
   assumed height) [M, wall `BUILD_NOTES.md`]. In perspective, measure only near the feature. Where the scale range is
   ±20 % or more, every derived size carries that error: confirm the terrace scale with a second cue before f3.
2. **Classify** each surface (section 3): grade, pattern, joint type, rock kind. **One zone = one class**; declare the
   zones (1, 4.3).
3. **Resolution check before tracing.** Work out what the crop can resolve: the feature size in px = size (m) x
   px/m. Anything under **~3 px** is not measurable: a width, a joint, a chip. Record it as an estimate [E] and gate it
   by an area fraction instead.
   - **Terrace** (17-25 px/m): stones are about **8-15 px** across (6x gridded crop). The stone outline and aspect
     are traceable at ±1-2 px, i.e. ±10-20 % of a stone. Joints are 0.3-1 px: **no joint width**.
   - **Gate steps** (47-50 px/m): stones 15-30 px, joints about 1-2 px (marginal).
   - **Wall sheet** `dojo_wall_ref.png` (1448 x 1086): footing stones about 30-45 px, joints resolvable.
4. **Trace** outlines on the clearest crop, upscaled 3-6 x (LANCZOS). Trace 30-60 stones per zone and wall type into
   `References/<Item>/trace_<crop>.json` (schema 6.8), with the pixel error the resolution allows (±1 px at ≥ 30 px
   per stone, ±2 px below). Tracing is the 2D outline authority (CLAUDE.md).
5. **Stone statistics from the trace:** area and equivalent diameter √(4A/π); minimum-area bounding box → length,
   height, aspect, orientation; corner radius / short side (circle fits at vertices; **only where stones are ≥ 30 px**,
   else [E]); convexity (area / hull area); course height and waviness; upright share; 4-way joints per m²; mean area
   per third of height.
6. **Interlock:** the line of minimum trace (LMT): shortest path through the joints between two points divided by the
   straight distance (Dijkstra on the joint graph) [87]. Good interlock = a longer path.
7. **Joints:** the dark-joint area fraction (always). Intensity profiles across 20+ joints with the FWHM of the dark
   trough in cm **only where joints are ≥ 3 px wide** (step 3); otherwise `null`. Mortared walls: the mortar-to-stone
   value ratio and the arris shadow fraction (3.3).
8. **Value and hue per region** (crowns, joints, moss, lower courses, wet band): both methods of 3.11, plus local std
   (16 px blocks), R/B, hue and saturation of the brightest half, joint RGB, moss hue share (hue 50-80°).
9. **Boulders:** silhouette IoU against the traced front and side (pines used 0.72-0.80 gates); plane fraction (share
   of surface within 10-15° of k fitted planes); edge-rounding ratio (arris radius / short axis, from profiles);
   crack count and length; moss cover on the up-facing area.
10. **Ours, the same way:** render with a camera matched to the crop (focal length, height, angle), light matched as
   closely as possible (sun direction from the reference shadows), and run the **same** script on the render.

### 6.2 Gates (put them in the spec; `stone_measure.py` computes them)

Tolerances: ratios within ±15 %; distributions with the median within 10 % and p10 / p90 within 20 %; absolutes only
under matched light (±0.05 luma). **A tolerance is never tighter than the reference's pixel error**: for a size of
n px traced at ±e px, the floor is ±e/n. At the terrace (8-15 px stones, ±1-2 px) that is ±10-25 %, so SG3's median
tolerance there is **±20 %** and p10/p90 ±30 %. Record the floor used in `measure.json`.

| Gate | What | Target |
|---|---|---|
| SG1 | Scale | stone median size vs the trace at the recorded px/m (S13) |
| SG2 | Class | the spec's grade / pattern / joint class matches the reference reading, per zone; zone boundaries (e.g. the cap course) where the reference has them (S4) |
| SG3 | Size distribution | width, height, area: median ±10 %, p10/p90 ±20 %; area CV ±20 % (S5) |
| SG4 | Aspect and upright share | h/w histogram KS distance small; upright share ±0.1 (S4) |
| SG5 | Coursing | straight bed joints longer than 3 stones: count within the reference's; broken-course share; waviness |
| SG6 | Interlock | 4-way joints per m² ≤ the reference's (0 for coursed work); LMT ratio ±15 % |
| SG7 | Size grading | mean area per third of height falls upward if the reference does; root stones present |
| SG8 | Joints | dark-joint fraction ±30 % (S3), always. Visible width (ray scan) median ±15 % of the traced FWHM **only where the reference resolves joints (≥ 3 px)**; on the terrace the width is `null` and only the fraction gates. Mortared: mortar/stone value ratio ±15 % |
| SG9 | Stone shape variety | CV of corner radius and crown height ≥ 0.3 (S1) |
| SG10 | Form contrast | p90/p50 (linear Y) ±15 %; local std ±25 %; matched light: p25-p75 and p5-p95 ±0.05 (S2) |
| SG11 | Colour | stone hue ±4°, saturation ±0.05, R/B ±0.1 vs the reference crop, under the reference-matched daylight rig in Blender and the same test light in Unreal after `G.look()` (3.11). Supersedes the README's s < 0.20 / R/B 1.00-1.20 for stone (S16) |
| SG12 | Growth | moss hue 50-80°; moss cover per region ±30 %; moss mask vs up-normal and cavity correlation > 0 (S11) |
| SG13 | Grain | dark speckle ≤ 5 % area, 1-5 mm world size (S10); no tile-period autocorrelation peak (S9) |
| SG14 | Rock form (rocks) | plane fraction ≥ 60 % (3-6 planes); arris radius ≥ 10 % of block (≥ 15 % river); 1-3 straight cracks; no crease sharper than 150° off fresh breaks (S7, S8) |
| SG15 | Silhouette (rocks) | IoU vs traced front and side ≥ 0.80 (pines used 0.72-0.80) |
| SG16 | Seating | burial per 3.10; no visible contact line; same-rock debris (S12) |
| SG17 | Technical | qa_check 0 hard fails; verts/tris ≤ 1.0; texel 5.12 ±20 % (S14); UCX per 4.13; GASP rules; fresh-process FBX re-import OK |
| SG18 | Unreal | the 5.12 checklist; stone ms within the 5.10 budget |

### 6.3 The reference numbers to beat (dojo, 2026-09-30)
Use 3.11. In short: terrace wall faces luma **p25-p75 about 0.40-0.70, p95 ≥ 0.8** (method A); close crop
**p90/p50 ≈ 2.0, dark-joint fraction ≈ 0.25, stone hue ≈ 32°, sat ≈ 0.24** (method C); boulders and the wall-sheet
footing **local std 0.13-0.15** (ours 0.058). These come from soft AI references at different scales: **pattern
targets, not exact gates, until re-measured on matched views** (6.1 step 10).

### 6.4 Render set (for every judge round)
- **Ortho front / side / top + 3/4** on the sheet grey with the 1.8 m figure (the kit sheets).
- **Grazing-light close-up at 1.5 m** (the "sponge" test).
- **Matched-camera side-by-side** for every reference crop (`Scripts/armory/side_by_side.py`).
- Walls: a straight-on **elevation** (for the layout measure) and a **raking-sun** view.
- Rocks: a **silhouette pass** (black on white) for IoU; a **clay pass** for form.
- **Two light rigs:** neutral studio grey (judge the **shape**), the reference's own light (judge the **look**); plus the
  scene context (dojo sunset).
- **Unreal captures** of the same views for the final judge (the dojo judges found Unreal colour shifts Blender never
  showed); future judge stills via `-game HighResShot` (`run_game_capture.ps1`).
- **Staged rounds:** (1) layout only, flat-shaded polygons vs the traced reference; (2) one stone type close-up;
  (3) the full piece. Stop and show the user when a stage fails decisively.
- Cycles on the PC GPU for finals; a cloud VM does only low-sample silhouette and clay gates.

### 6.5 Blind judge prompts
Randomise left/right per pair and record the key outside the judge's view. Show only images: no filenames, no numbers.
**Ask for descriptions, never prescriptions.** Use two judges with independent prompts.

**J1 Layout (after stage b):**
> You will see N pairs of flat line drawings of stone wall faces. In each pair one is traced from a photo-like
> reference and one is generated. For each pair: (1) which is generated, and how confident (50-100 %)? (2) List only
> DESIGN differences: stone sizes and their mix, stone shapes and proportions, how stones are arranged (rows or
> random), joint widths, corners. Describe what you see; do not suggest fixes.

**Pass:** no better than chance (≤ 60 %) over ≥ 8 pairs, and no difference named twice.

**J2 Form (clay, studio light):**
> Two grey renders of stonework. Which looks more like real, hand-laid stone, and why? Comment on the stones' faces
> and edges, how they meet, the joints, the variety between stones, and anything that looks generated, repeated or
> soft. Describe; do not prescribe.

**J3 Look (scored, as in the dojo rounds):**
> Score how closely the right image matches the left reference, 0-10, on design and on look (value, colour, moss,
> weathering). Name the top 5 differences, most important first, each tied to a location in the image, and say which
> are design and which are material or lighting.

**J4 Rock (silhouette + clay + final):**
> Two images of a boulder. Which is the reconstruction? List differences in overall shape, the flat faces and how
> rounded the edges are, cracks and clefts, how it sits on the ground, and moss or lichen placement.

**J5 Unreal context:** J3 on Unreal captures at gameplay distance against the scene reference.

### 6.6 The judge-steer rule
- A judge is a **detector**: it tells us the copy is detectable and where, not what the reference is.
- **Accept a judge delta only if the 6.1 measurement agrees**, or if it concerns something unmeasured, in which case
  add a measurement for it before acting.
- **When two judges disagree, measure.** This rule would have stopped both of our flips: the round 1 footing
  ("polygonal rubble" against the sheet's rounded pillow rubble) and stone kit f1 ("pale polygonal stones, long
  slabs, crazy paving" against rounded mid-grey stones with moss in the joints).
- Style words from a judge ("polygonal", "pale", "flat") are never spec values.

### 6.7 Numbers every report carries
`measure.json`: SG1-SG18 with targets and pass/fail; the trace file and px/m used; tris and verts/tris per mesh;
unique meshes; texture list with sizes and colour spaces; waivers with reasons; texel density; UCX count and traversal
boxes; SHA-256 of shipped files; Unreal ms with camera, resolution and scalability; judge results (J1 accuracy, J3
score and top 5) and which judge deltas were accepted or rejected by measurement; mesh MB and estimated texture MB
(5.10); build, render and bake times (4.19).

### 6.8 The tracer and the measurer (tools to write before f3)
**Status: neither exists** [M]. Sections 6.1, 6.2 and 8.4 depend on them, so writing them is the first task of any
stone build, before layout or geometry.

**Existing tracers to reuse (read, import, do not fork):**
| Script | What it does | Reuse for stone |
|---|---|---|
| `Scripts/props/props_lib/trace.py` (paper bomb, 1,356 lines) | `read_source` (exact PNG decode + **SHA-256**, refuses removed sources), `provenance()`, ink-probability field → sub-pixel marching squares → clamped cubic B-spline fits in real units; `rasterise`; `score_element` (IoU, edge distance). Deterministic numpy, no bpy | provenance and hashing, marching squares, curve fit and IoU scoring for **carved marks** (4.8.1) and **rock silhouettes** (SG15) |
| `Scripts/dojo/pines/pines_trace.py` (224 lines) | **hand trace**: polygons and polylines typed in full-image pixel coordinates, read off 2-3x zoomed panel crops, one dict per panel | the **manual polygon** method and file shape; the rock outline field already exists for pine 4 |
| `Scripts/SnowFlower/v4/trace/tp_trace.py` (135 lines) | thresholded fields on a 6x grid inside hand ROIs → smoothed → sub-pixel contours | the threshold-field + ROI method for **dark-joint seeding** |

**`Scripts/stone/stone_trace.py` (scope).**
1. **Mode `manual` (default for the dojo terrace).** At 8-15 px per stone, automatic segmentation is not reliable, so
   the trace is hand-entered, in the `pines_trace.py` pattern:
   - one polygon per stone, 5-12 vertices, in **source-image pixels** (x right, y down), read off 4-6x gridded
     crops (as `renders/wall/refcrops/grid_*.png`);
   - the tool draws an overlay of the polygons on the upscaled crop for a look-check, and validates them: no
     self-intersection, overlaps below 1 px², gaps are the joints.
2. **Mode `seed` (for crops where stones are ≥ 30 px, e.g. `dojo_wall_ref.png`).**
   - Dark-joint mask: luma below k x the local median, with k from the 3.11 methods, inside a hand ROI.
   - Distance-to-joint map by a two-pass chamfer transform.
   - A seeded flood (priority-queue watershed in pure Python/numpy; no scipy).
   - Cells are vectorised with the marching-squares code of `trace.py`, then hand-corrected in the JSON.
   - Report the mode per stone.
3. Writes `References/<Item>/trace_<crop>.json` (below). Never writes into another chat's folders.

**Trace JSON schema (`stone_trace/1`):**
```json
{
  "schema": "stone_trace/1",
  "source": {"path": "References/Dojo/dojo_landscape_ref.png", "sha256": "…", "size_px": [1024, 1536]},
  "crop_box_px": [x0, y0, x1, y1], "view": "near-orthographic wall face",
  "scale": {"px_per_m": 21.0, "uncertainty": 4.0, "cues": ["plaster band 2.4 m (assumed)", "…"]},
  "resolution": {"stone_px_median": 11, "joint_resolved": false, "trace_error_px": 2},
  "method": "manual", "tool": "Scripts/stone/stone_trace.py", "tool_git": "<commit or 'uncommitted'>",
  "zones": [{"name": "body", "class": {"grade": "nozura", "pattern": "ranzumi", "joint": "dry_packed"},
             "polygon": [[x, y], "…"]}],
  "stones": [{"id": 1, "zone": "body", "poly": [[x, y], "…"], "conf": "clear|partial|guess",
              "cut_by_crop": false, "occluded_by": null, "mode": "manual|seed"}],
  "packing": [{"id": 1, "poly": [[x, y], "…"]}],
  "joints": {"dark_fraction": 0.24, "fwhm_px": null},
  "notes": "…"
}
```
Coordinates are source pixels as floats. The measurer converts to metres with `scale`. Stones with `cut_by_crop` or
`conf: guess` are excluded from size statistics but kept for the layout overlay.

**`Scripts/stone/stone_measure.py` (scope).** Input: a trace JSON + its image, or a render + its matched trace.
Output: the 6.1 statistics and SG1-SG13 into `measure.json`:
- size, aspect and upright share;
- course and waviness;
- 4-way joints and LMT (a Dijkstra on the joint graph);
- area per third of the height;
- corner radius where resolved;
- both value methods of 3.11, and hue / saturation / R/B;
- the dark-joint fraction;
- moss hue share;
- the tolerance floor of 6.2.

For rocks, SG14-SG15: silhouette IoU through `trace.py`'s scoring, and plane fraction on the mesh. numpy + PIL only.

**Estimate** [E]:
- **Writing the tools:** `stone_trace.py` about 300-500 lines (one session); `stone_measure.py` about 500-800 lines
  (one or two sessions).
- **Tracing:** about 1 h per crop for 30-60 stones by hand. The dojo needs the terrace, the upper wall, two flights,
  a landing, the wall-sheet footing and three pine rock panels: about 8-9 crops.
- **Total before f3 can start:** about 3-4 sessions. Ask the user before starting (`stop-before-expensive-work`).

---

## 7. Pitfalls and how to avoid them

| # | Pitfall | Avoid it by |
|---|---|---|
| P1 | **Following a judge away from the sheet.** Round 1 footing went to chisel-faced polygonal rubble (5 → 6 → 5.5); stone kit f1 went to pale polygonal stones, long tread slabs and crazy-paving landings (6 → 5.5). Both sheets show rounded stones [M] | The judge-steer rule (6.6): measure the trace first; a judge delta needs a measurement that agrees |
| P2 | **Flat crowns** (f1 bulge ≤ 1.4 cm): no lit top, no shaded shoulder; value spread p25-p75 0.47-0.56 vs 0.40-0.70 | A real crown (r3 footing: bulge ≈ 7 % of the short side), asymmetric peak (`peak_off` 0.15-0.30), SG10 |
| P3 | **Uniform pillows and one corner radius** (r0, f2: "rounded rectangles on a grid") | Per-corner radius, per-stone crown, SG9 CV ≥ 0.3 |
| P4 | **Straight course lines** in random work (f2) | Broken courses, wandering boundaries, measured upright share (4.5.1) |
| P5 | **Kikkō polygons where the reference is ranzumi** (f1's 5-7-gons) | Classify first (3.2); round the cells (4.5.2 step 4) |
| P6 | **Bright, pebbled or flat joints** (r0's `M_DK_JointEarth`); a flat joint-core plane under grazing light (f2: "stones floating on a board") | Dark core (`M_DKT_JointDark`), 8 cm recess, noisy core with soil pockets and packing-stone backs (4.5.4-4.5.5) |
| P7 | **Stacking tiling-texture relief on geometric relief** (r0 "sponge", chocolate at sunset) | One home per scale (rule 10); micro granite set at normal 0.15-0.3 (4.11) |
| P8 | **Colour judged by eye.** r0 R/B 1.71 ("chocolate"), f1 pale beige, f2 hue 23° vs 32° | SG11 under the same light; ratios across lighting |
| P9 | **Terrazzo granite**: speckle too big and contrasty | 1-5 mm, ≤ 5 % dark area (SG13) |
| P10 | **Moss as a tint** | Geometry masks (4.11); SG12 |
| P11 | **Plane-chipped hull rocks** (the D rock: 3 masses x 26 planes, hulled: "a big faceted block") | The SDF pipeline with an opening (4.9); SG14 |
| P12 | **Noise blobs** for boulders (potato) and single-scale natural surfaces (sand, "smooth sine mountains") | Jointed block → rounded → cracked → grained; or an owned scan (2.1) |
| P13 | **Randomly rotated rocks in one outcrop** | Constrained yaw per cluster so crack directions agree (3.10) |
| P14 | **Floating stones, clean contact lines** | Burial per 3.10; RVT seam; same-rock debris; no PDO |
| P15 | **Grid to Mesh at its default threshold 0.1** on an SDF (meshes the offset surface or nothing); a band width smaller than the offsets | Threshold 0; band ≥ r / voxel + 3 voxels (4.9.2) |
| P16 | **The factory-startup default cube** enclosing the object: every AO bake black | Clear the scene first (4.9.2 step 0) |
| P17 | `hide_render` on the bake target (bake refuses); a low poly occluding the AO | Move the low poly away or bake the high's AO first (4.10) |
| P18 | **A curve-deformed batter shearing stones** | Always move each stone rigidly (`rigid_warp`) |
| P19 | **Bending laid masonry along a spline** (Nanite spline mesh) | Splines only for constant-section kerbs and copings (5.2) |
| P20 | **Planning on Unreal displacement or decals to make a masonry form** | Form in Blender geometry; displacement only for sub-cm relief on rounded rock (5.3) |
| P21 | **Faceted normals / many UV seams** on Nanite stone (verts/tris toward 3:1) | Smooth shading, few charts; verts/tris ≤ 1.0 (4.14) |
| P22 | **Full-resolution fallback shipped** (RE 0 kept from the verification import): memory and full-res complex collision | Split verification and shipped fallback; `ComplexCollisionMesh` where needed (5.2) |
| P23 | **WPO or PDO on stone** (VSM invalidation every frame) | Neither on any stone material (5.7) |
| P24 | **A stone top that looks climbable but is not** (plain mesh; sloped > 2°; no marker) | `traversal` box in the catalogue + flat UCX top ≥ 0.5 m deep (4.13) |
| P25 | **10-50 cm rubble or walls on routes** (GASP dead band) | ≥ 50 cm cover or ≤ 45 cm step (4.13) |
| P26 | **Mirrored or stretched UVs** on carved stone (the lantern judge); box UVs on round parts | Per-part unmirrored UVs or triplanar (4.8, 4.12) |
| P27 | **Kasa and other carved parts too thin** | Measure part ratios on the sheet (4.8) |
| P28 | **Triplanar swimming** on rocks placed with random yaw | Local-space triplanar or baked UVs (5.4) |
| P29 | **Nanite stone without UV1 in a Fab release** (f1 dropped it) | Restore UV1 per piece before Fab (4.12) |
| P30 | **Scanned rock in a Fab product**, or scan-derived textures in our materials | Scans game-only; Fab packs entirely ours (2.1) |
| P31 | **Two packs that do not match** (scans and our walls under different tone, moss, wetness) | One master, shared world-space layers, dE76 < 5 (5.9) |
| P32 | **Comparing absolute brightness across different lighting** (daylight AI ref vs sunset renders) | Ratios and hue across lighting; absolutes only under matched light (3.11) |
| P33 | **Inventing features the reference does not show** (f1's 4 cm nosing set-back, crazy-paving landings) | Every feature traces back to a reference crop or the spec (CLAUDE.md) |
| P34 | **Treating one flight's step count as the reference's** (judges disagreed: 1 slab vs 3-5 blocks) | Trace every flight; per-flight counts in the spec (3.4) |
| P35 | **Thin face stones showing at ends, corners and openings** | Full-depth stones wherever the side is visible (S6) |
| P36 | **Depending on add-ons** (Cell Fracture, Rock Generator, A.N.T.): none installed in 5.2; a download needs the user's go [M] | Own bmesh / GN code (4.9.3) |
| P37 | **Editing another chat's stone code or blend** (`sk_shared.py`, `kit1_geo.py`, `DojoStoneKit.blend`, `Scripts/vegetation/`) | Locks; import, don't fork; propose refactors (4.17) |
| P38 | **Patching a construction that does not converge** | Change the method (CLAUDE.md); stop early and show the user |
| P39 | **Real clan crests or franchise marks** on carved stone | Invent our own marks (3.2, IP rule) |
| P40 | **Judging only in Blender** | Final judge on Unreal captures in the scene light (6.4) |
| P41 | **Numbers finer than the reference's pixels** (2-4 cm joints "measured" at 0.3-1 px; ±10 % on 8-px stones) | Resolution check first (6.1 step 3); [E] tags; tolerance floor (6.2) |
| P42 | **Nanite fallback settings that do nothing** (`FallbackTarget` left at AUTO) | Set the target explicitly; assert it in the verify process (5.2, 5.12) |
| P43 | **One layout per module in a long run** (a memorable stone every 4 m) | 3 seeds per run module; hero stones only in unique modules (4.5.7) |
| P44 | **Courses tilted to follow the ground; modules scaled to fit a height** | Level courses, stepped modules, burial (4.5.7) |
| P45 | **Mortar treated as a dark void, or a dry joint painted pale** | Classify the joint (3.3); mortar fill surface and material (4.5.8) |
| P46 | **An RVT seam in a scene with no RVT** | Check that the RVT exists (5.1); the fallback seam until then (5.8) |
| P47 | **Shipping a rock mesh with no UVs, or a dense SDF mesh as the game mesh** | The 4.9.5 plan: a UV'd 50-150k mid, or class (b) triplanar |
| P48 | **Two classes blended in one zone** (the footing's squared cap course mixed into its rubble body) | Zones in the spec (1, 4.3, 8.1) |
| P49 | **A colour number without its method** (added 2026-09-30, stone kit f2 round 2). 3.11's method-C stone saturation (ref 0.24, f2 0.16) did not reproduce: `Scripts/stone/stone_measure.py` (mean linear colour of the brightest half, then sRGB HSV) gives ref 30.5° / 0.176, f2 23° / 0.27 on the same crops; method A and the C percentiles / dark fraction did reproduce exactly [M] | Quote every colour gate with the tool that measured it; re-measure the reference with the same code as the render |
| P50 | **A tint tuned under one rig only** (f2 round 2): a warmer granite that met the reference's daylight saturation read tan-brown under the dojo sunset, which the owner rejects ("mid-grey, not beige or brown"); f2's cool grey read pink-lilac at sunset [M] | Check a tint under the daylight gate rig AND the scene's sunset before building; the owner's reading outranks SG11's saturation (record the deviation) |
| P51 | **Joints that lean in alternating directions** make trapezoid / wedge stones (f2 round 2 dev) | Lean joints in runs (the sign holds for a few joints, `stone_layout.coursed_rounded` `lean_alt`); the reference's leaning ovals are parallelograms |
| P52 | **Stacked corner rounding** (per-corner cuts at 18-34 % of the short side plus Chaikin keep 0.2-0.3) turned the wall into pebbles floating on the joint core: every T-junction left a dark triangle [M] | Keep the total corner rounding near 13-22 % of the short side on coursed work; rounding more needs outlines that follow their neighbours |
| P53 | **Gating the drawn targets instead of the built outlines**: leaning joints, corner cuts and the joint inset lower the built stones' h/w (drawn 1.30-2.10 tall stones measured as 0.42 upright share before tuning) | Log the built outlines (`sk_shared.LAYOUT_LOG` → `stone_layout/1`), simulate the layout outside Blender, gate SG3 / SG4 on what was built |
| P54 | **An unrecorded gate rig**: the same wall measured p90/p50 1.64 / 1.92 / 2.29 at sun elevations 45 / 62 / 72° [M] | Take the sun elevation from the reference's shadows (short, high sun: 62° used), and store the rig (elevation, exposure, look) with every SG10 / SG11 number |
| P55 | **A pointed crown** (f2 round 2): `pillow_face` with a crown exponent below 2 and `peak_off` 0.15-0.30 made a cone whose ring corners showed as pyramid creases from the peak under a high sun | Crown exponent 2.0-2.8 with an off-centre peak; check the close-up under the high-sun gate rig, where creases show first |
| P56 | **T-junctions under rounded corners** (added 2026-09-30, stone kit f3). A coursed layout's head joints end on the bed of the course above or below; rounding the two corners there always leaves a dark triangle, and the eye reads "stones floating on a board" however thin the joint [M: f2 gate_elevation] | Fit the outlines: turn every T into a Y (`stone_layout.coursed_fitted`: the through-stone pushed up the head joint, the corners chamfered to match), so neighbours share edges and one inset makes every joint; round only obtuse corners |
| P57 | **A gate view framed in metres after the stones changed size**: f3's stones grew 30 %, the f2 camera then held fewer stones and the dark-joint fraction fell from 0.21 to 0.18 on the same wall [M] | Frame the SG8 / SG10 view by stones across (matched stone size in px, 6.1 step 10), and re-frame it whenever the stone size changes |
| P58 | **A stand-in cutting a buried side reads as a mesh defect**: the f2 "spike under the kerb" was the stand-in slope falling away from the kerb's buried end (all kerb bottoms measured at -0.25 m) [M] | Probe the mesh (lowest vertices, silhouettes) before changing geometry; seat kerbs, footings and buried courses in a soil bank in every assembly |
| P59 | **Fitted coursing is still coursing**: with every stone convex, a coursed frame keeps its beds; f3 measured bed continuity 0.78-0.85 against the trace's 0.44 (joint_stats, tol 0.2 x h) even with +-12 cm wander and 30 % through-stones [M] | For ranzumi use the power diagram (4.5.2) with coursed teeth only at module ends; gate SG5 flat before 3D |

---

## 8. Appendix: the dojo stone kit and D-pine rock plans

These are inputs for the stone kit fix (lock `dojostonekit`, `Scripts/dojo/stonekit/`) and the pines chat's rock
(lock `dojopines`), not their specs. Those chats and the user decide the final numbers. **The traces of 6.1 are the
first task of both**; numbers below marked "to trace" are not yet measured.

### 8.1 What the references show [M, looked at + crops]
- **`dojo_wall_ref.png`** (compound wall footing): **two zones, two classes.** Re-read on a 3x crop of box
  100,240-720,360 (2026-09-30).
  - **Cap zone:** one course of **squared, dressed blocks** with soft arrises and tight joints (uchikomi nunozumi).
  - **Body zone:** **rounded pillow-faced rubble**, sizes mixed, **random and un-coursed** (nozura/uchikomi
    ranzumi), with small stones in the gaps, deep dark joints and moss low and in the joints.
  - Bigger squarer blocks at corners and pier bases.
  - The first version's "rough courses, nunozumi-leaning" was wrong for the body. The spec declares both zones (4.3).
  - Kit 1's r3 footing is the anchor (7.5, "closest piece to its sheet").
  - **DOJO_QUEUE reconciled:**
    - line 126, the later correction ("ROUNDED, roughly square pillow-faced rubble ... under a course of dressed
      blocks"), is the right reading;
    - line 11's "the sheet's rough polygonal rubble" is stale status text from before that correction;
    - the dojo chat should update line 11 (this study does not edit the queue).
- **`dojo_landscape_ref.png`, river terrace wall** (`ref_stone_faces.png`, `ref_wall_lower.png`): rounded lens- and
  egg-shaped stones, **many upright**, strong crown shading, dark irregular joints (width not resolvable at this
  scale; 3.6), grass and moss tufts growing out of the joints; huge rounded boulders at the foot. Squarer blocks in
  the top course (about 0.34 x 0.24-0.28 m [E], wall `BUILD_NOTES.md`). **Body: nozura / uchikomi ranzumi; cap:
  squarer blocks.** The same two-zone structure as the footing.
- **Same image, upper terrace near the gate:** squarer blocks with soft arrises in near-level courses. **Uchikomi
  nunozumi.** One scene, two wall classes: each piece is told which it is.
- **Steps:** the middle flight (`ref_stairs_mid.png`) has one long slab per step; the foreground flight
  (`ref_stairs_low.png`) has 3-5 short blocks per tread with dark gaps between them. Treads lighter and worn, risers
  darker, rounded nosings, no visible overhang. Landings: large flat flags, roughly rectangular and irregular, not a
  crazy-paving net.
- **Boulders and cliff:** granite as rounded cuboids with a few deep straight cracks; the left cliff is stacked jointed
  blocks with vertical fractures and an ochre (iron) streak; moss on tops and ledges only; smaller rounded stones at
  the water.
- **`dojo_courtyard_stone_ref.png`:** Kasuga-type granite lanterns, carved square/hex parts, bush-hammered texture,
  softened arrises, lichen/moss specks on the kasa top and around the base.
- **Pine sheet (`dojo_japanese_pine_ref.png`, the three trees on rocks):** each rock is several fused rounded blocks
  with deep clefts, grey with yellow-grey lichen, moss cushions in the clefts and on top, 8-12 roots wrapping over the
  rock into the cracks, a grassy soil mound at the base. The rocks stand roughly 0.5-0.8 x the 1.8 m figure (to trace).

### 8.2 Stone kit fix: what to change (from f2, not from f1)

**Start point.** f2 (built, not judged: `renders/f2/`, `f2_measure.json`) already restored the round-0 shapes
(`lay_rounded` + `pillow_stone`), added kerbs (`KIT_SHEET_stair_kerbs`) and a sweep variant. f2 measured on
Wall_4m_H3: stone width median 0.51 m (p10 0.19, p90 0.65), height 0.41 m, upright share 14.5 %, long share 30 %,
visible joint median 2.6 cm, crown rise median 1.4 cm (p90 2.9 cm), batter 1:9.6 [M]. **Do not return to f1's
polygons.** Backups: `Backups/DojoStoneKit_f1_2026-09-30`.

**Terrace wall, river terrace (class: nozura/uchikomi ranzumi):**
1. Trace 30-60 stones per zone on `ref_stone_faces` / `ref_wall_lower` / `ref_terrace_wall` at 17-25 px/m, by hand
   (6.8 `manual`); confirm the terrace scale with a second cue. Set width, height, aspect and upright share (expected
   well above f2's 14.5 %) at the 6.2 tolerance floor (±20 % median). Corner radius and crown come from the wall sheet
   and the gate-step region, where stones are big enough (6.1 step 3), not from the terrace (SG3-SG5).
2. Layout: power diagram with anisotropy toward upright stones, rounded cells, broken courses allowed, no 4-way
   joints; gate flat against the trace (J1) before 3D.
3. Stones: per-corner radius, asymmetric crown (peak_off 0.15-0.30), crown height from the trace (f2's 1.4 cm median
   is likely low: the reference's p90/p50 is 2.0 vs f2's 1.29), CV ≥ 0.3.
4. Joints: dark and deep; **gate the dark-joint fraction (≈ 0.25), not a width**. The visible width stays near f2's
   measured 2.6 cm median unless a resolvable crop says otherwise [E]. Noisy core with packing stones; grass and moss
   tufts from the joints (tuft units from the pines work if the pines chat agrees).
5. Root stones at the foot, partly buried; the huge foot boulders are separate rocks (8.3 method).
6. Batter: near-straight by default (f2's 1:9.6 is in range); the castle sweep stays an optional variant.

**Upper terrace (class: uchikomi nunozumi):** squarer `rough_block`-style faces in near-level courses, soft
arrises; sangi-zumi corners at 2-3 : 1 with kadowaki-ishi. **Footings and cap courses:** two zones (8.1), with a
squared dressed cap course (nunozumi) over a random rounded-rubble body (ranzumi). Kit 1's r3 footing numbers are
the anchor.

**Steps:** two flight variants from the trace: a long-slab flight (one block per step) and a short-block flight
(3-5 blocks per tread, staggered). Solid blocks, no overhang unless traced, rounded worn nosing 2-3 cm, tread hollow
from a traffic field (5-8 mm), moss at tread ends and backs, lighter treads, darker risers.

**Landings:** flush rectangular / irregular-rectangular flags by guillotine splits, joints 1.0-1.6 cm with soil/moss,
tops ±3 mm; the kerb piece (5-15 cm proud) where the reference shows an edge.

**Materials:** micro granite set (normal 0.15-0.3, no 3.5 / 9 cm facets on kit stones), per-stone vertex-colour
macro (±8-12 % value, ±3° hue), hue graded toward ~32°; moss by the 4.11 mask; in Unreal the `M_ST_Masonry` instances
`M_DKT_WallGranite`, `M_DKT_StepGranite`, `M_DKT_StepRiser`, `M_DKT_JointDark` (they do not exist in Unreal yet;
create them under the PackMaterials lock if they touch the pack).

**Data:** a `traversal` box per climbable top in `kit_catalog.json`; UV1 restored before any Fab use.

**f3 piece inventory** (from `kit_catalog.json`: 104 pieces, 65 wall + 39 stairs [M]). This is a proposal; the stone
kit chat and the user decide.

| Family (count) | f3 action | Why |
|---|---|---|
| `Wall_2m/4m_H2/H3/H4/H6` (8) | **rebuild**, 3 seeds each for the heights the level uses (4.5.7) | new trace-driven layout, stones and zones |
| `Wall_*_Sweep` variants (24 in all: 6 `Wall`, 6 `Wall_CornerIn/Out`, 6 `Wall_EndL/R`, 6 `WallFoot_Corner*`) | **keep as optional, rebuild only if the user keeps the sweep** (8.5) | near-straight is the proposed default |
| `Wall_CornerIn/Out` (8 non-sweep), `Wall_EndL/R` (8) | **rebuild**, 1 seed | corners and ends carry the new stones and sangi-zumi |
| `Wall_StairOpening_H2/H3/H4` (3) | **rebuild** | the same wall face; the opening's steps come from the stair track |
| `WallFoot_2m/4m` (2), `WallFoot_CornerIn/Out` (8 non-sweep) | **rebuild**, 3 seeds for the straight feet | root stones, zones, burial |
| `WallCoping_2m/4m/CornerIn/CornerOut` (4) | **keep geometry, re-tone** unless the trace changes the cap blocks | flat traversal tops already pass GASP |
| **New:** `Wall_Step_<H>to<H'>`, stepped `WallFoot` | **add** (4.5.7) | no transition pieces exist |
| `Stair_Flight_W120/W180_R050/R100/R200` (6) | **rebuild as two variants** (long slab, short block) per trace | blocks per step differ by flight (3.4) |
| `Stair_Landing*` (6) | **rebuild** | flush rectangular flags from the trace |
| `Stair_Cheek*` (11) | **rebuild** if the cheek stones share the wall layout; else keep | follows the wall decision |
| `Stair_Kerb*` (4) | **keep geometry, re-tone** | f2 kerbs measured in range (4.7) |
| `Stair_Lantern_Stone` (1) | **separate lantern fix** (thicker kasa, per-part UVs; 4.8) | not part of the wall/stair round |
| `Stair_Lantern_Timber`, `Stair_Rail_*` (11) | **keep** | not stone |
| Delete | **none** until the trace shows a piece has no reference basis | invent nothing, delete nothing unmeasured |

**Gates:** SG1-SG13, SG17, SG18; judges J1 (layout), J2, J3, J5, with the judge-steer rule.

### 8.3 The D-pine rock plan (the rock a tree grows from)

**Now:** `Scripts/vegetation/rock.py` (visual hull split into 3 convex masses, 26 chip planes each, hulled), 15k tris,
per-mass box UVs, moss on 45 % of faces, `M_DJ_Granite` at Tint 0.40 plus a lichen/stain overlay not in the kit
master; judged "a big faceted block" [M]. Owned by the pines chat (`dojopines`).

**Proposed method (4.9, method change):**
0. **Probe the SDF chain first** (it is [U5.2], 4.9.2). One headless run on a 3-lobe, 1.2 m test rock:
   joint-family chips → Mesh to SDF → SDF union → opening (r = 6 %) → one crack subtract → Fillet at the lobe joins →
   Grid to Mesh (threshold 0) → masked noise → decimate to 80k → smart-project UV → 2K bakes.
   - Record time and peak memory per step, and voxel counts at 5 and 10 mm.
   - Record the chart count and time for UV on the 80k mid.
   - Record SG14 on the result.
   
   If it fails or runs over about 5 min, use the measured voxel-remesh path (4.9.2 evidence status).
1. **Trace** the rock outlines on the sheet's three rock panels (front; side where shown); one view is the height
   authority (tree study P51). Record rock height and width against the 1.8 m figure.
2. **Lobes:** 3-4 fused blocks split along the trunk crack; chip planes in **2-3 joint families** (not random); lobe
   sizes from the trace.
3. **SDF union** with a small closing/fillet at the lobe joins (clefts); **opening r = 5-8 %** of the short axis;
   **1-3 cracks** along the joint planes where the roots enter; masked meso noise; tafoni pits on vertical faces.
4. **Mesh** (threshold 0, safe band), masked noise on the mesh, decimate to the **shipped 50-150k mid with unique
   UV0** (4.9.5 a), bake from the dense source: normal (DirectX), AO → ORM.R, curvature, and a mask (R moss: clefts, top, shaded side; G lichen: exposed convex, 2-15 cm yellow-grey patches; B soil/dirt: base).
5. **Roots** walk the **final** surface through the cracks (BVH, `build_pines.py`), 8-12 per the sheet.
6. **Base mound** as a separate mesh (soil + moss + grass tufts), burying the rock's lower third or more.
7. **Collision:** hulls from the lobes (≤ 8), plus trunk hulls; no canopy collision.
8. **Unreal:** `M_ST_RockUnique` instance with the moss by exposure x cavity x HeightLerp, lichen spots, RVT seam if it
   sits on terrain.
9. **Gates:** SG14 (planes ≥ 60 %, arris radius, cracks), SG15 (IoU ≥ 0.80 vs the traced panels), SG12, SG16, SG17; J4.

The same method, with river opening radii (15-30 %) and joint-block proportions, makes any sheet-drawn hero boulder
(e.g. the huge boulders at the terrace foot) if the user wants them built rather than sourced.

### 8.4 Build order and stop points
0. **Tools** (6.8): `stone_trace.py` and `stone_measure.py`, under a new lock (e.g. `stonetools`). Then the
   **SDF probe** (8.3 step 0). About 3-4 sessions with the tracing (4.19); needs the user's go.
1. **Traces and measurements** (6.1) for the terrace (with a second scale cue), upper wall, wall-sheet footing (both
   zones), each flight, the landing, and the pine rock panels. Stop and show the user the measured targets if they
   contradict the current kit reading.
2. **Stone kit layout round** (flat polygons vs trace, J1). Stop on a decisive fail.
3. **One stone type close-up** (terrace stones, grazing light + matched crop). Stop on a decisive fail.
4. **Full kit rebuild** (f3) + QA + FBX re-import + sheets + judges.
5. **Pine rock** (pines chat) with the SDF method, then roots and mound.
6. **Unreal** verify of both in a fresh process, when DojoLab is free.

### 8.5 Open decisions for the user
- **Terrace batter:** near-straight default with the castle sweep as a variant (recommended), or the sweep default?
- **Step flights:** ship both the long-slab and the short-block flight variants?
- **Root/foot boulders and river banks:** built by us (8.3 method) or sourced from owned scans (standing rule)?
- **`Scripts/stone/` library:** create it now under its own lock, or keep the code in the stone kit until a second
  stone kit needs it?
- **Shared changes** (4.18): the qa_check Nanite gate and the fallback split (pipeline owner), and the library's
  height-blend and lichen layer (materials owner).
- **Scanned rocks:** approve game-only use of the Nordic Beach and Fisherman's Cabin rocks (re-tinted through our
  master)? And source the 12-16 rocks of the 2.4 list, or have us build the rock-parts set?
- **Tools first:** approve the tracer and measurer (6.8, about 3-4 sessions) before any f3 round?
- **Seeds and transitions:** 3 layout seeds per run module and new stepped/transition pieces (4.5.7, about +30 MB
  of cooked Nanite)?
- **ASSET_GUIDELINES exceptions** (4.18): add the Nanite budget tier, the Nanite UV1 game-only exception, the stair
  sub-metre grid, and the NoCollision-scatter UCX waiver?
- **RVT:** ask the dojo ground/level chat to build an RVT for DojoLab, or keep the fallback seam (5.8)?

---

## 9. Sources and uncertainties

### 9.1 Sources

**Craft and heritage**
1. MLIT (Japan Tourism Agency), *Castle Craftsmanship: Stone Walls* — https://www.mlit.go.jp/tagengo-db/common/001561168.pdf ; *Stone Walls at Himeji Castle* — https://www.mlit.go.jp/tagengo-db/en/R2-00194.html
2. Roots of Japan, *You and I are Stone Wall Enthusiasts* — https://note.com/rootsofjapan/n/n1137c867873d?hl=en
3. JCastle, *Stone walls* — https://jcastle.info/view/Stone_walls
4. Kanazawa Castle Park, *Museum of stone walls* — https://shiro-niwa.pref.ishikawa.lg.jp/kanazawa-castle/en/explore/museum.php
5. Wikipedia (ja), *石垣の積み方* — https://ja.wikipedia.org/wiki/%E7%9F%B3%E5%9E%A3%E3%81%AE%E7%A9%8D%E3%81%BF%E6%96%B9 ; Kojodan, *石垣の種類* — https://blog.kojodan.jp/entry/2019/03/02/113353 [S]
6. Shirobito, sangi-zumi — https://shirobito.jp/article/1130 ; Kojodan, *算木積* — https://blog.kojodan.jp/entry/2020/10/14/180000
7. Kojodan, *石垣の反りと勾配* — https://blog.kojodan.jp/entry/2020/10/19/180000 ; Shirobito, *勾配と反り* — https://shirobito.jp/article/1213 ; Takamaru office — https://www.takamaruoffice.com/shiro-shiro/warp-slope-stonewall/ [S for the Kumamoto figure]
8. Isan no Sekai, *伝統技術にもとづいた城郭石垣の整備* — https://www.isan-no-sekai.jp/feature/32_souron02
9. Seattle Japanese Garden, *Japan's Stone Wall Culture* — https://www.seattlejapanesegarden.org/blog/2025/6/20/japans-stonewall-culture ; *Ishigaki Wall and Accessible Pathway Project* — https://www.seattlejapanesegarden.org/blog/2026/4/24/ishigaki-wall-project
10. Roots of Japan, *The Tallest Stone Walls ... Marugame* — https://note.com/rootsofjapan/n/n9bdb288354f1?hl=en [S]; Muza-chan, *Hikone Castle sloping wall* — https://muza-chan.net/japan/index.php/blog/hikone-castle-sloping-wall
11. The Stone Trust, *Dry stone walling: 5 basic rules* — https://thestonetrust.org/wp-content/uploads/2018/02/Dry-stone-walling-guide-5-basic-rules-1.pdf ; DSWAA guide — https://dswaa.org.au/wp-content/uploads/2021/05/Manual_June_2020_RetWall_vlr.pdf ; Peak District NP — https://www.peakdistrict.gov.uk/__data/assets/pdf_file/0022/64642/drystonewalling.pdf (403) ; Field Mag — https://www.fieldmag.com/articles/dry-stone-wall-how-to-guide [S for batter ratios]
12. Wikipedia, *Spheroidal weathering* — https://en.wikipedia.org/wiki/Spheroidal_weathering
13. Domokos et al., *How River Rocks Round* (PLoS ONE 2014) — https://pmc.ncbi.nlm.nih.gov/articles/PMC3922984/
14. *The Shape of Fluvial Gravels: Fiji's Sabeto River* (Geosciences 2021) — https://www.mdpi.com/2076-3263/11/4/161 [S]
15. Wikipedia, *Lecanora polytropa* — https://en.wikipedia.org/wiki/Lecanora_polytropa ; *Lichens, Mosses and Vascular Plants in the Biodeterioration of Historic Buildings* — https://pmc.ncbi.nlm.nih.gov/articles/PMC9781475/ ; InspectApedia — https://inspectapedia.com/exterior/Lichens_on_Stone.php [S]
16. Litos Online, *The Inada Granite* — https://www.litosonline.com/en/article/inada-granite-japanese-traditional-light-grey-ornamental-rock ; MLIT, *Aji Stone* — https://www.mlit.go.jp/tagengo-db/en/R3-00412.html [S]
17. Wikipedia, *Stone lantern* — https://en.wikipedia.org/wiki/Stone_lantern
18. NAJGA, *The Garden Path* — https://najga.org/the-garden-path/ ; *Japanese Garden Paths* — https://najga.org/japanese-garden-paths/ [S]
19. NAJGA, *Garden Rocks* — https://najga.org/japanese-garden-garden-rocks/ ; Robert Ketchell, *Notes on Ishigumi* — http://robertketchell.blogspot.com/2013/05/notes-on-ishigumi-or-art-of-arranging.html [S]
20. Dimensions.com, *Stair Tread & Riser Sizes* — https://www.dimensions.com/element/stair-tread-riser-sizes ; Chippy Tools, *Japanese Stair Rules* — https://www.chippy.tools/building-codes/jp/stairs/stair-and-guard-requirements/ ; Petros Stone — https://petrosstone.com/stone-steps-treads/ ; London Stone Step — https://londonstonestep.co.uk/guides/garden-step-dimensions-rise-and-going/ ; Trebles Going, *Worn Tower Steps* — https://www.treblesgoing.org.uk/wornsteps.html ; stair-wear model — https://hsetdata.org/index.php/ojs/article/download/11/7/7 [S]
36. Wikipedia, *Sakuteiki* — https://en.wikipedia.org/wiki/Sakuteiki
90. DSWA, *What is a dry stone wall* — https://www.dswa.org.uk/wp-content/uploads/2018/07/What-is-a-dry-stone-wall.pdf
91. The Stone Trust, *How to* — https://thestonetrust.org/resource-information/how-to/ ; dry stone glossary — https://conservationhandbooks.com/dry-stone-walling-introduction/glossary/ ; MLIT, *Castle craftsmanship: stone walls* — https://www.mlit.go.jp/tagengo-db/en/R1-00697.html
101. Conservation Handbooks (BTCV), *Walls on slopes* — https://conservationhandbooks.com/dry-stone-walling-introduction/technical-walling/walls-on-slopes/ ; Peak District NP, *Dry stone walling* — https://www.peakdistrict.gov.uk/__data/assets/pdf_file/0017/2159/drystonewalling.pdf [S]
102. Building Conservation, *Joint Finishes on Historic Brickwork* — https://www.buildingconservation.com/articles/brickwork-joint-finishes/brickwork-joint-finishes.htm
103. Designing The Past, *Mortar Joint Profiles* — https://www.designingthepast.com/restoration/masonry-joints-a-brief-guide ; Designing Buildings, *Pointing brickwork* — https://www.designingbuildings.co.uk/wiki/Pointing_brickwork [S]
104. Historic England, *Repointing Brick and Stone Walls* (HEAG144) — https://historicengland.org.uk/images-books/publications/repointing-brick-and-stone-walls/heag144-repointing-brick-and-stone-walls/ ; NI Department for Communities, *Technical note: Repointing stone and brick* — https://www.communities-ni.gov.uk/technical-note-repointing-stone-and-brick [S for the 10-15 mm figure, from a search summary]

**Game art and production**
21. 80.lv, *Japanese Stone Wall Production in ZBrush & SD* — https://80.lv/articles/001agt-japanese-stone-wall-production-in-zbrush-sd
22. 80.lv, *Creating a Stone Wall Material in ZBrush, Substance 3D Designer & Marmoset* — https://80.lv/articles/creating-a-stone-wall-material-in-zbrush-substance-3d-designer-marmoset-toolbag
23. 80.lv, *Procedural Rock Generation in Houdini* — https://80.lv/articles/006sdf-breakdown-procedural-rock-generation-in-houdini ; rock brushes — https://vkgamedev.com/blog/top-rock-stone-sculpting-brushes-blender [S]
24. Epic, *Valley of the Ancient Sample* — https://dev.epicgames.com/documentation/en-us/unreal-engine/valley-of-the-ancient-sample-game-for-unreal-engine
25. Epic, *Electric Dreams Environment* — https://dev.epicgames.com/documentation/en-us/unreal-engine/electric-dreams-environment-in-unreal-engine
26. Tyler Smith, *Ghost of Tsushima: Rock Sculpting* — https://www.artstation.com/artwork/yk42A3 (403) ; ArtStation Magazine, *Ghost of Tsushima Art Blast* — https://magazine.artstation.com/2020/08/sucker-punch-productions-ghost-of-tsushima-art-blast/ ; GDC, *Samurai Landscapes* — https://gdcvault.com/play/1027352/Samurai-Landscapes-Building-and-Rendering [S]
27. Maximov, *Technical Art Techniques of Naughty Dog* (GDC 2017) — https://gdcvault.com/play/1024103/Technical-Art-Techniques-of-Naughty ; slides — https://www.advances.realtimerendering.com/other/2016/naughty_dog/NaughtyDog_TechArt_Final.pdf ; Polycount, *Libertalia* — https://polycount.com/discussion/194424/creating-uncharted-4s-libertalia-unity [S]
28. 80.lv, *Procedural Placement in Horizon Zero Dawn* — https://80.lv/articles/real-time-procedural-placement-in-horizon-zero-dawn ; Guerrilla — https://www.guerrilla-games.com/read/gpu-based-procedural-placement-in-horizon-zero-dawn [S]
29. Jan Arenz, *Texture Repetition & Texture Variation* — https://janarenz.artstation.com/blog/L6Qq/about-texture-repetition-texture-variation-unreal-engine-4-5 (403) ; World of Level Design — https://www.worldofleveldesign.com/categories/ue4/landscape-macro-tiling-variation.php [S]
30. Epic, *Texture-blended material for vertex weights painting* — https://dev.epicgames.com/documentation/unreal-engine/setting-up-a-texture-blended-material-for-vertex-weights-painting-in-unreal-engine?lang=en-US
32. CG Channel, *Megascans 2018* — https://www.cgchannel.com/2017/11/quixel-launches-megascans-2018/ ; Althera Games, *Nanite guide* — https://altheragames.com/en/blog/ue5-nanite-guide [S] ; Quixel Japanese stone assets — https://quixel.com/megascans/home?category=3D+asset&category=historical&search=japan&assetId=ufokciifa [S]
33. Outpost VFX, *22 Pro Tips for Environment Artists* — https://www.outpost-vfx.com/fr/news/22-pro-tips-and-tricks-for-environment-artists
34. Ron Haimov, *PBR Albedo guide* — https://www.linkedin.com/pulse/pbr-albedo-values-guide-lighting-artists-only-ron-haimov [S]
35. Siliconera, *Sekiro Environments* — https://www.siliconera.com/sekiro-environments-were-designed-to-reflect-culture/ [S]
76. 80.lv, *Houdini HIVE rock formations* — https://80.lv/articles/houdini-hive-procedural-rock-formations-for-ue4
77. 80.lv, *Rock shader pipeline ZBrush to Unreal* — https://80.lv/articles/rock-shader-pipeline-from-zbrush-to-unreal
78. Beyond Extent, *Sculpting for environment art* — https://www.beyondextent.com/articles/sculpting-for-environment-art-in-games
79. Neil Blevins, *Primary, secondary and tertiary shapes* — http://www.neilblevins.com/art_lessons/composition_primary_secondary_and_tertiary_shapes/composition_primary_secondary_and_tertiary_shapes.htm
80. Polycount, *Primary/secondary/tertiary shapes* — https://polycount.com/discussion/233026/sculpting-issue-primary-secondary-and-tertiary-shapes [S]
94. Polycount, *Texel density 5.12 / 10.24* — https://polycount.com/discussion/227863/texel-density-5-12-10-24 [S]
95. Experience Points, *Single-material modular kit* — https://www.exp-points.com/vuk-single-material-modular-kit-environment-ue4
96. 3dtexel, *Trim sheets and atlases* — https://3dtexel.com/trim-sheets-texture-atlases-the-game-environment-workflow/ [S]
97. Michael Arby, *Procedural moss / snow on rocks in Unreal* — https://www.michaelarby.com/post/tutorial-unreal-procedural-moss-snow-on-rocks [S]
100. Ubisoft, *Procedural World Generation of Far Cry 5* (GDC 2018) — https://www.gdcvault.com/play/1025557/Procedural-World-Generation-of-Far

**Unreal Engine**
31. Epic, *Nanite Virtualized Geometry* — https://dev.epicgames.com/documentation/unreal-engine/nanite-virtualized-geometry-in-unreal-engine ; UE forum, *Displacement and Nanite Tessellation* — https://forums.unrealengine.com/t/community-tutorial-displacement-and-nanite-tessellation-in-unreal-engine-5/1800313 [S]
37. Epic, *Working with Nanite-Enabled Content* — https://dev.epicgames.com/documentation/unreal-engine/working-with-naniteenabled-content
38. Epic, *Using Nanite with Landscapes* — https://dev.epicgames.com/documentation/unreal-engine/using-nanite-with-landscapes-in-unreal-engine
39. Epic, *UE 5.8 release notes* — https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes ; *Unreal Engine 5.8 is now available* — https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available
41. Tom Looman, *UE 5.8 performance highlights* — https://tomlooman.com/unreal-engine-5-8-performance-highlights/ [S]
42. Epic community, *Nanite Tessellation & Displacement, UE 5.4* — https://dev.epicgames.com/community/learning/tutorials/bOda/unreal-engine-nanite-tessellation-displacement-ue-5-4-step-by-step-tutorial-any-asset-not-just-landscapes ; forum, *Nanite tessellation and shadows* — https://forums.unrealengine.com/t/nanite-tesselation-and-shadows/1688608 ; forum, *5.4 Nanite displacement shadows in motion* — https://forums.unrealengine.com/t/ue5-4-nanite-displacement-shadows-in-motion/1793131 [S]
44. UE forum, *Nanite assemblies RT proxy / fallback vertex count* — https://forums.unrealengine.com/t/static-mesh-nanite-assemblies-rt-proxy-nanite-fallback-vertex-count-issues/2709323 [S]
45. Epic, *Ray Tracing Performance Guide* — https://dev.epicgames.com/documentation/en-us/unreal-engine/ray-tracing-performance-guide-in-unreal-engine
46. Epic, *Lumen Performance Guide* — https://dev.epicgames.com/documentation/unreal-engine/lumen-performance-guide-for-unreal-engine ; *Lumen Technical Details* — https://dev.epicgames.com/documentation/unreal-engine/lumen-technical-details-in-unreal-engine?lang=en-US
48. Epic, *Virtual Shadow Maps* — https://dev.epicgames.com/documentation/en-us/unreal-engine/virtual-shadow-maps-in-unreal-engine
49. Epic, *Overview of Substrate Materials* — https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-substrate-materials-in-unreal-engine
50. Epic, *Runtime Virtual Texturing* — https://dev.epicgames.com/documentation/en-us/unreal-engine/runtime-virtual-texturing-in-unreal-engine ; *Quick Start* — https://dev.epicgames.com/documentation/en-us/unreal-engine/runtimevirtual-texturing-quick-start-in-unreal-engine
51. Epic, *Simple versus Complex Collision* — https://dev.epicgames.com/documentation/en-us/unreal-engine/simple-versus-complex-collision-in-unreal-engine ; *Setting Up Collisions With Static Meshes* — https://dev.epicgames.com/documentation/unreal-engine/setting-up-collisions-with-static-meshes-in-unreal-engine
53. Epic, *World Partition HLOD* — https://dev.epicgames.com/documentation/en-us/unreal-engine/world-partition---hierarchical-level-of-detail-in-unreal-engine
54. StraySpark, *World Partition deep dive* — https://www.strayspark.studio/blog/ue5-world-partition-deep-dive-streaming-hlod [S]
55. Epic, *PCG Biome Core and Sample plugins* — https://dev.epicgames.com/documentation/unreal-engine/procedural-content-generation-pcg-biome-core-and-sample-plugins-reference-guide-in-unreal-engine
56. StraySpark, *PCG spline fence generator* — https://www.strayspark.studio/learn/tutorials/pcg-spline-fence-generator-ue5 [S] ; gam0022, *PCG tips (self pruning / difference)* — https://gam0022.net/blog/2024/01/01/ue5-pcg-introduction-tips/ [S]
58. StraySpark, *HISM vs ISM* — https://www.strayspark.studio/blog/hism-vs-ism-unreal-engine-explained [S]
59. StraySpark, *Mesh Terrain in UE 5.8* — https://www.strayspark.studio/blog/mesh-terrain-ue5-8-caves-overhangs-guide ; forum, *Mesh Terrain / Mesh Partition 5.8* — https://forums.unrealengine.com/t/mesh-terrain-mesh-partition-5-8/2730153 [S]
60. Polycount, *Best practices for Nanite assets* — https://polycount.com/discussion/236540/best-practices-when-creating-assets-specifically-for-nanite [S] ; 80.lv, *Possibilities and drawbacks of Nanite* — https://80.lv/articles/discussing-the-possibilities-and-drawbacks-of-unreal-engine-5-s-nanite [S]
62. Epic, *Bringing Nanite to Fortnite Battle Royale* — https://www.unrealengine.com/en-US/tech-blog/bringing-nanite-to-fortnite-battle-royale-in-chapter-4
63. Fab, *Standard License / EULA* — https://www.fab.com/eula?lang=en
64. Fab, *Quixel to Fab transition FAQs* — https://support.fab.com/s/article/Fab-Transition-FAQs?language=en_US
65. Epic forum, *Megascans update, March 2025* — https://forums.unrealengine.com/t/megascans-update-march-2025/2419561 [S]
98. Epic community, *Texture Color tool (UE 5.5): mesh painting on Nanite* — https://dev.epicgames.com/community/learning/tutorials/JZxm/texture-color-tool-in-unreal-engine-5-5-mesh-painting-on-nanite-meshes-deep-dive
99. Liam Wedge, *Nanite Assemblies in UE 5.7* — https://liamwedge.artstation.com/blog/mpygZ/nanite-assemblies-in-unreal-engine-5-7-from-dcc-to-ue-import [S]
105. Epic, *Nanite Technical Details* (data size: 14.4 bytes per input triangle, ~13.8 MB per million; fallback target options) — https://dev.epicgames.com/documentation/unreal-engine/nanite-technical-details?lang=en-US

**Blender and geometry**
66. Blender 5.2 release notes, geometry nodes (Mesh Bevel) — https://developer.blender.org/docs/release_notes/5.2/geometry_nodes/ ; manual — https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/mesh/operations/mesh_bevel.html
68. Blender 5.0 release notes, geometry nodes (SDF grids) — https://developer.blender.org/docs/release_notes/5.0/geometry_nodes/
69. SDF Grid Fillet — https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/volume/operations/sdf_grid_fillet.html ; Mesh to SDF Grid — https://docs.blender.org/manual/en/5.0/modeling/geometry_nodes/mesh/operations/mesh_to_sdf_grid.html ; community overview — https://blenderartists.org/t/new-grid-nodes-from-5-0-5-1-sdf-volumes-voxels-advection/1616473 [S]
72. Cycles baking (5.2 manual) — https://docs.blender.org/manual/en/latest/render/cycles/baking.html
73. StraySpark, *Curvature maps in Blender* — https://www.strayspark.studio/blog/curvature-maps-blender-substance-painter-alternative [S]
74. Cell Fracture extension — https://extensions.blender.org/add-ons/cell-fracture/
75. 4rknova, *Voronoi fracture* — https://www.4rknova.com/blog/2026/07/27/voronoi-fracture
81. Peytavie et al., *Procedural generation of rock piles using aperiodic tiling* (2009) — https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-8659.2009.01557.x
82. *Modeling rocky scenery using implicit blocks* — https://link.springer.com/article/10.1007/s00371-020-01905-6
83. *A virtual microstructure generator for 3D stone masonry walls* — https://www.sciencedirect.com/science/article/pii/S0997753822001218
84. *A mason-inspired pattern generator for historic masonry* — https://www.sciencedirect.com/science/article/pii/S0141029624001664
85. *Image convolution-based irregular stone packing* — https://www.sciencedirect.com/science/article/pii/S0377221724000730
86. *From bin packing to masonry wall construction* — https://experts.umn.edu/en/publications/from-bin-packing-to-masonry-wall-construction/
87. *Geometric indices to quantify texture irregularity of stone masonry* (LMT, MQI) — https://www.sciencedirect.com/science/article/abs/pii/S0950061816300988
88. Bourne and Roper, *Centroidal power diagrams, Lloyd's algorithm* — https://cvgmt.sns.it/media/doc/paper/2517/BourneRoper.pdf
89. Jason Davies, *Lloyd's relaxation* — https://www.jasondavies.com/lloyd/

(Numbers are kept stable with the research notes where possible, so some are skipped.) developer.blender.org and
docs.blender.org returned HTTP 403 to the fetch tool; their content is from search snippets, confirmed by the in-Blender
probes where marked [M].

**Local evidence (read-only):** `CLAUDE.md`, `ASSET_GUIDELINES.md`, `FAB_ASSET_STUDY.md`, `TREE_BUILDING_STUDY.md`;
`WorkFiles/dojo/DOJO_QUEUE.md`; `WorkFiles/dojo/build/stonekit/{BUILD_NOTES.md, kit_catalog.json, f1_measure.json,
f2_measure.json}`, `renders/{wall,f1,f2}/` (sbs pairs, close-ups, ref crops); `WorkFiles/dojo/build/GASP_TRAVERSAL.md`;
`WorkFiles/dojo/build/pines/BUILD_NOTES.md`; `Scripts/dojo/kit1_geo.py`, `Scripts/dojo/stonekit/sk_shared.py`,
`Scripts/dojo/materials/{README.md, dojo_tex_gen.py, dojo_materials.py}`, `Scripts/dojo/unreal/{dj_sc_materials.py,
dj_sc_nanite.py, dj_sc_import.py, dj_sc_verify.py}`, `Scripts/pipeline/{qa_check,export_fbx,helpers,textures}.py`,
`Scripts/vegetation/rock.py`; `Scripts/dojo/stonekit/{build_wall.py, build_stairs.py}`; the tracers
`Scripts/props/props_lib/trace.py`, `Scripts/dojo/pines/pines_trace.py`, `Scripts/SnowFlower/v4/trace/tp_trace.py`;
`WorkFiles/dojo/build/stonekit/{wall,stairs}/{BUILD_NOTES.md, build_f2.log, render.log, render_cu.log}` (timings);
`Exports/DojoKit/StoneKit/*.fbx` sizes and `Exports/DojoKit/Materials/Textures/T_DJ_Granite*` sizes;
references `References/Dojo/{dojo_landscape_ref, dojo_wall_ref, dojo_courtyard_stone_ref, dojo_japanese_pine_ref}.png`;
UE 5.8.3 engine source and content (names in B_unreal's source list); DojoLab `Config/DefaultEngine.ini` (grep);
owned content listings under `Documents/Unreal Projects/Scenery_Tutorial`, `DemoGame_1` and the launcher VaultCache;
Blender 5.2 probes in `WorkFiles/studies/stone/c_probes/`.

### 9.2 Uncertain for these versions (verify before relying on it)

**Unreal 5.8:**
- Whether Nanite runtime tessellation is still Experimental in 5.8 (the release notes say nothing; the project gate is
  gone from source). Its real cost on a hero rock.
- Build-time `DisplacementMaps`: setting it from Unreal Python (EditAnywhere only), and whether the fallback and RT
  proxy are built from the displaced mesh.
- How HLOD Approximated / Simplified Mesh bakes a world-space stone master (macro, moss, RVT seam).
- Whether Fuzz on moss survives the Blendable GBuffer's one-closure simplification with an acceptable look and cost.
- The Mesh Paint Texture material node and the UV/resolution setup for Nanite stone.
- FBX vertex-colour gamma (`colors_type="SRGB"`) for moss and wear thresholds: needs the ramp round trip.
- Hairline gaps between abutting Nanite modules from independent `PositionPrecision` quantization.
- Nanite Assemblies for static walls from a repeated stone-unit library (C cites them as experimental and USD-only in
  5.7 [99]; B finds them enabled in DojoLab): untested.
- Mesh Terrain (Experimental) for cliffs: collision, navigation, PCG interop, memory.
- `HeightLerp`, `TextureVariation` and the other listed functions exist as files in 5.8's engine content; their
  behaviour in a Substrate slab graph is untested.
- All per-tier budgets in 5.10: proposals until measured on the RTX 4070 SUPER. The texture-pool and uasset figures
  are estimates from BC compression rates and Epic's 14.4 B/tri average.
- The enum member name for a percent-triangles `NaniteFallbackTarget` in 5.8 Python (RELATIVE_ERROR is measured).
- Negative-scale (mirrored) Nanite instances with tangent-space normals and vertex colour (4.5.7).
- An RVT volume fed by static-mesh ground (not a Landscape) in DojoLab: setup and cost.
- Unreal import and verify time for a whole stone kit (not recorded).
- The Electric Dreams sample's rock kits were not inspected.
- **Megascans / Fab licence** terms for scanned rocks: read from secondary summaries plus the Fab EULA page. This study
  assumes they are **not** allowed in our Fab products; confirm per asset before any commercial decision.

**Blender 5.2:**
- The **Mesh Bevel geometry node** (new in 5.2): behaviour on dense or non-manifold stone meshes and its output masks;
  only its sockets were listed.
- **The whole SDF rock chain** (4.9.2): SDF union, crack subtraction, Fillet, joint-set chips and Grid to Mesh on a
  rock were never run. Only the opening/closing via SDF Grid Offset and Grid to Mesh at threshold 0 on a 1 m cube
  were verified. The boulder probe's timings are from a non-SDF voxel-remesh path. Probe first (8.3 step 0).
- **SDF Grid Fillet / Mean Curvature:** sockets listed, not run on a stone.
- Voxel and memory cost of the SDF path at 5 mm (4.19 has estimates only; the probe used 1-1.4 m objects at 8-10 mm).
  SDF is not planned for whole wall modules.
- UV0 by smart project on the 50-150k shipped rock mid (4.9.5): speed, chart count and quality untested.
- Bake times onto a 50-150k mid at 2K/4K, CPU vs GPU (4.19 estimates).
- The curvature-from-normal bake is probed on one boulder only.

**Craft data:**
- Ishigaki batter numbers (Kumamoto ~45° for the lower two thirds; Marugame's half-height curve, 22 m) come from search
  summaries of Japanese pages, not survey drawings; no sori curve equation was found.
- No primary source gave ishigaki joint widths, face-stone depth ratios or backfill thickness. The 2-4 cm joints are
  **not measurable** on our AI references (0.3-1 px at the terrace scale); they are an estimate [E]. The terrace
  stone sizes (0.28-0.55 m) are ±20 % or worse from the scale uncertainty and the 8-15 px stone size.
- Mortar profile depths and lime albedo (3.3, 4.5.8) are from conservation guidance for brick and stone, not
  measured on a reference; no dojo reference shows mortar.
- The 6 mm minimum carved stroke (4.8.1) is derived from texel density and Nanite's pixel target, not tested in a
  render.
- Stair-wear depths (up to 75 mm), stepping-stone spacing and height, and the one-third-to-two-thirds burial rule come
  from secondary garden and conservation sources.
- The granite albedo 0.35-0.40 linear is from a secondary chart; match the reference's rendered values instead.
- Ghost of Tsushima, Naughty Dog and Sekiro stone methods are known from portfolio captions, abstracts and summaries
  (403 or paywalled), not the full talks.
- The value statistics (3.11) compare crops at different scales and resolutions from soft, AI-generated references
  (one 4 x upscaled) against sunset renders: pattern targets until re-measured on matched views.
- The pine-rock size relative to the figure, the root-stone size ratio (4.5.3) and the S6 depth reading are this
  study's estimates, to be traced.
- The Fisherman's Cabin per-rock `_N` / `_Mask` + tiling-detail setup is inferred from file names and asset-registry
  strings; no asset was opened.

**Changes this study asks for (not made):** see 4.18:
- qa_check Nanite gate;
- the fallback split with an explicit `FallbackTarget`;
- catalogue `traversal` box;
- library height-blend and lichen layer;
- an RVT and our own `MF_ST_GroundBlend`;
- the ASSET_GUIDELINES exceptions.

The new tools of 6.8 are new code under a new lock, not changes to shared code. Each change needs its owner's OK;
pipeline changes need `test_pipeline.py` and `test_qa_negative.py` re-run.
