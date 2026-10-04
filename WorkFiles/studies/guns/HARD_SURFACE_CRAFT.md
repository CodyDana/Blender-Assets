# Gun study, role: hard-surface modelling craft

How professional weapon artists build realistic game guns, and how that translates to this repo's method: procedural
Python in headless Blender 5.2, matched "to the T" against the user's orthographic reference sheets, exported through
`Scripts/pipeline/`, verified in Unreal 5.8. One of several role notes in `WorkFiles/studies/guns/`. The rifle-specific
study in `WorkFiles/guns/rifle/` was not read for its conclusions and is not edited here; where this note disagrees
with it (static meshes, a single mag split), the disagreement is deliberate and flagged in section 9.

**Written:** 2026-10-04. **Versions:** Blender 5.2.0 LTS (probed headless for this note), Unreal Engine 5.8.

**Evidence tags.**
- **[E]** external: a cited source (numbers in square brackets point to section 10). **[E,s]** means the page itself
  was blocked (403) and only the search engine's summary of it was read, so treat it as weaker.
- **[M]** measured in this repo for this note, or already measured in a shipped report (the report is named).
- **[J]** judgement: our reading or arithmetic, not measured.

---

## 0. The answer in one screen

| Question | Industry practice | Our method (decision) |
|---|---|---|
| High-to-low bake or mid-poly? | Both are used. AAA FP weapons are usually a high poly (CAD or subdivision) baked onto a low of roughly 8-20k [E][19] (a pistol with optic and light: 39k polygons over 6 sets [E][3]); mid-poly with face-weighted normals plus decals/trims is used on Star Citizen and Alien: Isolation style work [E,s][12][14][15] | **Mid-poly is the shipped mesh and also its own "high".** Real geometry with crisp process-correct bevels, custom/hardened normals, and a normal map that carries only micro relief (checkering, knurl, stipple, grain, machining) painted per texel from analytic height. Cycles bakes AO only, plus ray-cast shells for the far LODs (the katana's method [M]) |
| Triangles, hero FP rifle | Low polys of 8-20k with baked normals [E][19]; Fab realistic rifles 10-28k, a musket 39k [E,s][18]; house range 20-50k [M ASSET_GUIDELINES] | **Rifle LOD0 target 30-45k, ceiling 50k** (no bake means bevels cost geometry, about 1.5-2x a baked low [J]). LOD1 ~45 %, LOD2 ~15 %, **LOD3 ~4 % (1.5-2.5k) for the battle royale**. All LODs from the same generator |
| Texel density | Community 10.24 px/cm FP and 5.12 TP [E][20]; hero assets up to 20.48 px/cm and FP weapons break the norms [E,s][20]; texels allocated by visibility: the back of the gun gets more than the front [E][4][19] | **Density by visibility class**, computed from screen math (section 3.3): ADS sights 50-60, FP rear zone 40-50, FP mid 30-40, front 25-30, hidden 8-15 px/cm. Three 2048 sets reach that on the rifle (section 3.4) |
| One atlas, several sets, UDIM, trims? | AAA close-range guns split sets by part: upper, lower, mag, stock [E,s][17]; COD-class guns carry 30-50 materials [E][8]; swappable attachments get their own sets [E,s][17] | **2-4 sets per gun by material family and swap unit** (Metal, Furniture, Magazine; Optic/Rail for attachments), each 2048, placed in UV0 tiles u 0..1, 1..2, 2..3 like the katana. **No UDIM** (virtual-texture dependency for buyers [J]). **No trim sheets on the guns**: unique texels are free for a per-texel painter; reuse happens at the module level (one shared rail mesh) |
| Knurl / checkering / stipple | Normal map for the fine pattern, geometry for silhouette and borders [E][7][E,s][23] | Same: the pattern is analytic height -> normal + roughness + AO-ish cavity; the panel's border step, scalloped turret rims and anything on the silhouette are geometry |
| Screws, pins, rivets | "If a screw is supporting your silhouette make it geometry" [E][4]; small screws and threads to the normal map [E][7] | At FP distance every protruding head is geometry at LOD0 (domed rivets, screw heads, pin ends); flush pins are an inset ring in geometry; LOD1 keeps heads at fewer segments; LOD2 moves them to the shell texture. Count and position from the sheet; size from the sheet if >= 4 px, else from engineering norms (3.7) |
| Markings | Proof marks and text drive realism in AAA [E][6] | **Text-free, always.** Realism comes from process marks the sheet supports: lathe and mill marks, stamping bend lines, polymer parting lines, wood grain. Never invent a stamp the sheet does not show |
| Moving parts | Separate parts that move or detach in the reference [E][4]; **Fab: firearms must have "all expected moving parts rigged and a full set of animations"** [E][11] | **Build every expected moving part as its own closed solid with a pivot** (mag, dust cover, carrier/charging handle, selector, trigger, mag catch, sight leaf, stock hinge, bolt, slide, hammer, bipod legs), and model what an animation reveals (bolt face, chamber, carrier rails through the port, mag feed lips and top round). Merge to a static mesh or rig rigidly at export: the build does not change |

**Does a gun study pay off before continuing?** Yes [J]. The two highest-risk calls for the whole line (six guns
plus a backlog) are made once here: (1) parts are separate solids with pivots, because Fab's firearm rule requires a
rig and the game will want reloads; (2) the reference sheets are AI images whose own left and right views disagree
(section 4.1, measured ~0.89 IoU), so "to the T" needs an authority rule per part before any trace starts. Getting
either wrong on the rifle would be paid again on the SMG and every gun after it.

---

## 1. Purpose, scope and how to use it

**Scope.** Modelling and surfacing craft for realistic hand-held guns: the line in `References/Guns/` (Rifle, SMG,
Carbine, LongRifle, Sniper, Pistol) and the backlog in `WorkFiles/guns/GUN_REFERENCE_PROMPTS.md` (pump shotgun, DMR,
second SMG, LMG, crossbow, attachments kit on one shared rail). Out of scope here: rigging and animation, collision,
sockets, Unreal materials and the shared colour system (other roles); IP and the Fab design deltas (the Fab role).

**How to use it.**
1. Section 3 is the industry practice, with numbers.
2. Section 3.12 is the fake-gun checklist: walk it before every judge round.
3. Section 4 is our method: how each practice becomes code in the katana style.
4. Section 6 is the gates to copy into each gun's spec.
5. Section 8 has per-gun notes; section 9 lists what the rifle plan must change.

**The rules** (condensed):
1. **A gun reads by its edges.** Every hard edge catches a thin highlight; the width and profile of that highlight
   says "machined", "stamped", "cast", "moulded" or "wood". A model with one bevel radius everywhere reads as CG
   before anything else [J, from [1][7][16]].
2. **Classify every part by its manufacturing process first** (3.5), write it into the spec, and let the process
   set the bevel profile, the surface marks, the finish and the wear.
3. **Silhouette and seams are geometry; texture is micro.** Form over ~0.5 mm in geometry, micro relief in the
   painted normal map, nothing in between faked [E][7], house rule 10 of the stone study [M].
4. **Bevels are sized for the screen, not only for reality**: max(process radius, 2 px at the nearest view
   distance) (3.3, 4.5). Exaggerate rather than lose them [E][4].
5. **Parts are parts.** Separate closed solids with real contact: pins through holes, rivet heads on both faces,
   shut-line gaps with depth. No floating, no buried, no zero-thickness sheet.
6. **Model what moves, and what moving reveals.** Fab requires the rig [E][11]; the reload shows the mag top and
   the port interior.
7. **Wear tells one story of use**, placed by hand contact, holster and sling rub, motion paths, heat and
   handedness, never by curvature alone [E][3][7].
8. **Metal is metal.** Metallic 0 or 1, bare steel near Epic's iron value, roughness doing the work [E][10][3].
9. **No text, no logos, no invented marks** (CLAUDE.md IP rule, sheet prompt rules [M]).
10. **The sheet is the outline authority, with a per-part authority view** because AI sheets disagree with
    themselves (4.1). Measure, then blind-test.
11. **Same generator, every LOD** (katana, flashbang precedent [M]): no Decimate, no UV transfer.
12. **If a construction does not converge, change the method** (CLAUDE.md). For guns: height-field relief on flat
    slabs failed on ornate items before [M CLAUDE.md]; do not try to fake a receiver's cuts with a normal map.

---

## 2. Decision guide: which modelling method

### 2.1 The three methods in industry

| Method | How | Where used | Cost / risk |
|---|---|---|---|
| **High-to-low bake** | High poly by CAD (Fusion 360 -> MoI) or subdivision with support loops/booleans, optionally ZBrush damage; low poly retopologised around it; Normal/AO/Curvature baked [E][1][2][3][4] | Most AAA FP weapons; portfolio work | Two meshes per part, cages, skew, ray misses; normal-map gradients have to be killed with custom normals [E][8]. Tangent basis must match the engine (MikkTSpace on both sides) |
| **Mid-poly + weighted normals** | Thin bevels on hard edges, normals locked perpendicular to large faces (FWN); the mesh is source and target; normal map only for micro detail; decals and trims for surface detail [E,s][12][13][14][15] | Star Citizen, Alien: Isolation, many environment props | More triangles; very stable shading; no bake failures; silhouette better than a baked low [E,s][12] |
| **CAD + bevel shader** | CAD geometry, soft edges generated by a renderer's bevel shader at bake time, two bevel sizes (large parts, small parts) [E][7] | Recent weapon work in Marmoset | Requires a bake; bevel only in the normal map, silhouette stays sharp |

### 2.2 Ours: generator mid-poly, analytic micro relief

We cannot sculpt or drive CAD; we generate exact geometry from code. That makes **mid-poly the natural method**, and
the katana proved the chain end to end: real crisp bevels, parametric per-corner UVs and paint attributes,
per-texel painting, Cycles AO bake of the game mesh, authored LODs, Unreal verify on exact bytes, IoU 0.93-0.99
against its design sheet [M KATANA_REPORT].

What we do not do, and why [J]:
- **No high-poly bake of form.** A generated "high" with more bevel segments baked onto a lower mid-poly would bring
  back cages and skew for no gain; the mid-poly already carries the form.
- **No baked normal for micro relief either**, when the relief is a function of part-local coordinates
  (checkering, knurl, stipple, lathe rings, brushing, wood pores, rifling). The katana painted these straight from
  height functions (`katana_tex.height_to_normal`) [M]. It is exact, seam-aware, resolution-independent and cannot
  miss a ray.
- **Selected-to-Active bakes only where geometry is replaced**: far-LOD shells (katana LOD2 tsuka shell, ray-cast
  [M]) and grouped small parts collapsed at LOD2/LOD3.

A side benefit [J]: because our normal maps carry only micro relief of a fraction of a millimetre, a small mismatch
between our tangent frame and Unreal's MikkTSpace (computed after custom normals) is visually negligible; a
form-carrying high-to-low bake would not forgive it.

### 2.3 Build or buy

Fab's Firearms category needs at least one asset "with all expected moving parts rigged and a full set of
animations" [E][11], and the FAB_ASSET_STUDY already notes common realistic guns could be bought for the game and
only signature weapons built [M GUN_REFERENCE_PROMPTS]. That choice belongs to the user (section 11). This note
assumes we build.

---

## 3. Principles from industry, with numbers

### 3.1 Workflow order (common to every breakdown read)

Reference grouped by shapes, silhouettes, scale and detail distribution [E][1] -> blockout big to small [E][1] ->
separate the parts that move or detach [E][4] -> form detail -> low/mid poly with silhouette-supporting detail as
geometry [E][4] -> UVs with straight islands and every 90-degree edge split [E][2][4] -> bake -> texture in passes:
raw material, surface treatment, damage/wear, micro detail [E][8] -> check in engine early, at the game's
distances [E][1][7].

### 3.2 Triangle budgets

| Source | Number |
|---|---|
| AAA FP baked low (secondary blog) | 8-20k; "a well-optimised rifle 8-14k reading like 30k" [E][19] |
| Fab realistic M4-style rifle with suppressor | ~27.7k, textures 2K/1K/512 by part size [E,s][18] |
| Fab flintlock musket | 39,150 LOD0, 4 LODs, 4K [E,s][18] |
| Fab AR + 2 SMGs pack | AR 10,195, no LODs [E,s][18] |
| Treyarch (Hiley) | FP guns "tend to have very dense geometry" and are reduced for the world model [E][5] |
| House | hero weapon 20-50k [M ASSET_GUIDELINES]; katana 20,368 / 6,824 / 1,724 with 45 % in the wrap [M]; flashbang 5,848 (165 mm) [M] |

**Proposal [J]** (one mesh serves FP and TP; Unreal streams mips and switches LODs):

| Gun | LOD0 target (ceiling) | LOD1 | LOD2 | LOD3 (BR) |
|---|---|---|---|---|
| Rifle (AK-style, wood) | 30-45k (50k) | ~45 % | ~15 % | 1.5-2.5k |
| SMG | 25-40k (50k) | ~45 % | ~15 % | 1.2-2k |
| Carbine / LongRifle | 30-45k (50k) | ~45 % | ~15 % | 1.5-2.5k |
| Sniper incl. scope + bipod | 40-50k (50k; waiver question) | ~45 % | ~15 % | 2-3k |
| Pistol | 15-25k (30k) | ~45 % | ~15 % | 0.8-1.2k |
| Magazine (separate mesh) | 2-4k | | | |

Where LOD0 goes on a mid-poly rifle [J]: bevel rings on every edge are the main cost (2 segments on ~20-30 m of edge
length at ~1.5-2 mm spacing is 10-15k alone), then round parts (barrel, gas tube, pins, sight drum: 32-48 sides at
LOD0), then the mag ribs and rivets. LOD1 halves segment counts and drops 1-segment chamfers on hidden edges; LOD2
removes bevels under ~1 mm and moves fasteners into the shell texture; LOD3 is the silhouette hull plus baked maps.

LOD screen sizes: measured, not defaulted (kunai 1.0 / 0.28 / 0.098; katana proposal 1.0 / 0.35 / 0.15 for a long
thin bounding sphere) [M]. A rifle's ~0.45 m bounding radius behaves like the katana [J].

### 3.3 Texel density and bevel width from screen math

The weapon-art norm is to give texels by visibility: back of the gun more than the front [E][19], stocks less in
FP [E][4], hidden faces scaled down [E][1][2]. To size it, compute how many screen pixels a millimetre covers [J]:

px per mm on screen = W / (2 d tan(HFOV/2)), W = horizontal resolution, d = eye-to-surface distance.

| View | d | HFOV | 1080p (W 1920) | 1440p (W 2560) |
|---|---|---|---|---|
| FP, rear receiver, selector, rear sight | 0.30-0.35 m | 70 deg (a typical narrower FP weapon FOV) | 3.9 px/mm | **5.2 px/mm** |
| FP, ADS: rear sight leaf / front post | 0.15-0.25 m / 0.6-0.7 m | 70 deg | 5.5-9 / 2.0 | 7-12 / 2.6 |
| FP, mag, handguard | 0.45-0.6 m | 70 deg | 2.3-3.0 | 3.0-4.1 |
| FP, front sight block, brake | 0.65-0.8 m | 70 deg | 1.7-2.1 | 2.3-2.8 |
| TP, opponent at 3 m | 3 m | 90 deg | 0.32 | 0.43 |

Unreal 5.6+ First Person Rendering draws FP-tagged primitives with their own FOV and a scale that pulls them toward
the camera [E][9]; the projection is what matters, so the table holds with the FP FOV the game picks [J].

**Texel targets [J]** (1:1 texel-to-pixel at 1440p is the ceiling worth paying for; above it, mips discard texels):

| Class | Surfaces | Target px/cm |
|---|---|---|
| A, ADS | rear sight leaf and notch, front post and hood (and optic eyepiece on the sniper) | 50-60 |
| B, FP rear | receiver rear half, dust cover, selector, charging handle, grip top, stock comb near the cheek | 40-50 |
| C, FP mid | mag, mag well, trigger guard, handguards, receiver front | 30-40 |
| D, front | gas block, front sight base, barrel, brake | 25-30 |
| E, hidden | undersides, insides, faces behind other parts, contact faces | 8-15 |

TP needs only ~4-5 px/cm at 3 m; the same textures serve it through mips [J].

**Bevel width rule [J]:** a highlight narrower than ~2 screen pixels shimmers and vanishes under TAA/TSR. Minimum
visible bevel width = 2 px / (px per mm): **about 0.4 mm on class A/B surfaces, 0.5-0.7 mm on C, 0.7-0.9 mm on
D** (1440p, 70 deg FP FOV). Rosenberger-Loosmann (Rocksteady) exaggerates bevels "to prevent anti-aliasing artifacts" for the same
reason [E][4]; Stokaliuk uses a thinner bevel material for small parts so they are not lost [E][7].

### 3.4 Texture sets, atlas, UDIM, trims

Arithmetic for the rifle [J], approximate surface areas from the sheet's proportions at ~880 mm overall:

| Group | Parts | Area (cm2) | 2048 set at 70 % packing, uniform | With classes |
|---|---|---|---|---|
| Metal | receiver + dust cover ~540, barrel/gas tube/blocks/brake ~510, small parts ~200 | ~1,250 | ~48 px/cm | B 45, C 35, D 28, E 10 fits |
| Furniture (wood) | stock ~500, lower handguard ~240, upper ~160, grip ~110 | ~1,010 | ~54 px/cm | comb/grip 45, rest 35, inner 10 |
| Magazine | body, ribs, spine, feed lips, follower, top round | ~680 | ~66 px/cm | 40-50 is enough; spare goes to class A sights if the mag shares nothing |

So **three 2048 sets** reach the targets on the rifle; 4096 is not needed in game [J]. The painter is
resolution-independent, so a 4096 export for the Fab listing costs only compute time (user decision, section 11).

Why split by family and swap unit [E,s][17][J]:
- the shared colour system: metal on `M_Steel_Master`, wood/polymer on `M_Fabric_Master` (katana precedent [M]);
- the magazine is its own mesh (reload, reuse across variants), so it owns its texels;
- attachments (optics, rail, suppressor) get their own sets so a gun does not pay for an optic it never mounts.

**UDIM: no** [J]. Unreal reads UDIMs through virtual texturing, which a Fab buyer may not have enabled, and the
pipeline already gets the same separation from slot-per-tile UV0 (katana: steel u 0..1, grip u 1..2 [M]).
**Trim sheets: no** on hero guns [J]. Trims share memory across many assets; a per-texel painter makes unique texels
free, and wear must differ per instance anyway (3.12 G9). Reuse instead happens as **modules**: one rail mesh family
to MIL-STD-1913 dimensions (slot pitch 10.01 mm, slot width 5.23 mm, depth 3.0 mm, top width 21.2 mm, 45-degree
flanks [E][21]) shared by the carbine, longrifle, SMG and the attachments kit.

### 3.5 Form language by manufacturing process

Classify every part (rule 2). Radii and marks below are typical engineering values [J] unless cited; the sheet
overrides anything it resolves.

| Process | Parts (examples) | Edges | Faces and marks | Finish and wear |
|---|---|---|---|---|
| **Machined** (milled, turned) | trunnions, barrel, gas block, bolt, rails, sight blocks, pistol slide | sharp-broken 0.2-0.6 mm chamfers (1 segment), crisp; concave inside corners carry the cutter radius (2-6 mm) | flat true faces; turned parts show fine concentric lathe rings; milled flats show cutter arcs or parallel passes (roughness only) | blued/parkerized/nitrided dark; wear to bright steel on high edges, polished streaks along sliding axes |
| **Stamped / formed sheet** | AK receiver and dust cover, magazine body, trigger guard (sheet), sling swivels | bends with inside radius >= sheet thickness (AK receiver ~1 mm sheet [J]): rounded, 2-4 segments; cut edges show the sheet's thickness as a flat land | slight oil-canning on large flats (very low amplitude in normal map); pressed ribs with soft radii; dimples; rivet heads; spot-weld dimples where shown | paint or blue over sheet; wear on rib crests and bend apexes, never on the flat between them |
| **Cast / forged** | hammers, triggers, some sight parts, pistol frame | fillets 1-3 mm (3 segments), softer than machined | faint casting grain (roughness), parting line on non-machined faces | same finish family, usually less wear-polished |
| **Polymer (moulded)** | SMG receiver, grips, stocks, mags of modern guns | radii 0.5-2 mm (2-3 segments), never razor; ribs with root fillets | draft 1-2 degrees on walls (silhouette visible on ribs and grip), parting line, subtle sink at thick ribs, ejector-pin circles on hidden faces; textured (stippled) grip zones | matte; wear is scuff to a **lighter, glossier** satin and white stress marks, never bright metal [E][1] |
| **Wood** | AK stock, handguards, grip, classic sniper stock | rounded 1.5-4 mm (3-4 segments), softer where handled | grain follows the blank's long axis, end grain on the butt and cut ends, pores; finish pools in inside corners [E][6] | varnish/oil gloss over rougher raw wood; dents on toe and heel, polish on grip and handguard bottom, worn-through finish at corners [E][6] |
| **Wire / spring / rubber** | sling loops, springs, butt pads, scope eye cups | round sections; rubber edges 1-2 mm radii | rubber: matte, fine texture | rubber greys and shines at contact edges |

Two edge materials for scale: large parts and small parts get different bevel widths, as in [E][7]; our rule
(3.3) already scales by view class and process.

### 3.6 Knurling, checkering, stippling, serrations

| Pattern | Real scale | Our build [J] |
|---|---|---|
| Wood checkering | 18-24 lines per inch on rifle stocks (1.06-1.41 mm pitch), 20-24 most functional [E][22] | analytic diamond height in the panel's own (u, v) frame -> normal + cavity in BC/roughness; panel border step and the panel outline are geometry; >= 4 texels per pitch needed: 1.3 mm pitch needs >= 31 px/cm, so the grip panels are class B |
| Knurl (round parts) | diamond or straight, ~0.6-1.2 mm pitch [J] | normal + roughness on the cylinder's (angle, z); if the knurl scallops a silhouette (turret cap rims), the scallops are geometry |
| Polymer stipple | random 0.3-0.8 mm bumps [J] | blue-noise bump field in normal + roughness only; never geometry [E,s][23] |
| Slide / cocking serrations | 1.5-3 mm pitch grooves [J] | **geometry**: they cut the silhouette at the top edge and catch strong highlights in FP |
| Magazine ribs | pressed, several mm wide | geometry (they shape the mag's silhouette and the reference shows them as forms) |

### 3.7 Screws, pins, rivets

- **Count and position** come from the sheet only (CLAUDE.md "invent nothing"); the Sheet B close-ups resolve the
  rifle's fasteners at ~2.4 px/mm [M, 4.1].
- **Size**: measured when the head spans >= 4 px on the sheet; otherwise engineering norms [J]: rivet heads 4-7 mm
  domed 0.6-1.5 mm proud; cross pins 3-5 mm, flush or 0.2-0.5 mm proud with a chamfer ring; small screws M3-M5 with
  5.5-8.5 mm heads. "Wrong scale of screws" is one of the fastest judge tells (3.12 G6).
- **Geometry vs texture**: protruding heads are geometry at LOD0 (they break the silhouette in FP raking light)
  [E][4]; flush pins are an inset ring of geometry (a dark gap) with a domed or flat end; threads and tiny set
  screws are texture [E][7].
- **Slot clocking random** per screw (seeded), not all aligned [J]; rivets slightly irregular in dome height and
  centre (±0.1 mm) [J].
- Rivets show a head on **both** faces of the sheet where both are visible; a pin passes **through** visible holes.

### 3.8 Markings without text

Proof marks, serials and logos are a large share of AAA realism [E][6], and they are banned here (CLAUDE.md IP; the
sheet prompts ask for none [M]). Replace their job, not their look [J]:
- process marks that the sheet's surfaces imply (3.5): lathe rings, milling arcs, stamping die lines, polymer
  parting lines, wood grain and pores;
- functional geometry the sheet shows: selector detents as notches, sight-leaf graduations only as plain ticks if
  the sheet shows ticks (the AK leaf normally carries numerals: plain ticks or nothing);
- no stamped circles, triangles, arrows or "fake-text" scribbles (they read as text and as invention).

### 3.9 Material values (metal/rough, Unreal)

- Metallic binary, 0 or 1 [E][10] (house rule too [M]).
- Bare steel (edge wear, bore crown, polished bolt): base colour near iron (0.56, 0.57, 0.58) linear [E][10],
  roughness 0.15-0.35. Aluminium (carbine receiver wear) (0.91, 0.92, 0.93) [E][10].
- Blued / parkerized / anodized finishes [J]: treat as metallic 1 with a dark base colour (linear ~0.04-0.10) and
  roughness 0.35-0.5 (blued) or 0.55-0.75 (parkerized, crystalline); anodized black aluminium the same family at
  0.35-0.55. Calibrate against a sheet crop under matched light before locking (the katana's first blade was far too
  dark, below polished steel's F0 [M KATANA_REPORT]).
- Wood and polymer dielectrics; dark polymer base colour sRGB ~40-55 (Andrushkiv clamps the whole palette to
  40-240 sRGB for UE [E][1]); wood varnish glossier than the wood under it [E][6].
- Roughness carries most of the realism: gradients and handling zones instead of flat uniform values [E][7]; edge
  gloss changes for interest [E][5]; glossy, bright edge highlights with dark, glossy grease in cavities [E][6].

### 3.10 Wear: one story

Breakdowns describe wear as a life story: factory finish -> coating -> scratches -> dust -> oil -> fingerprints ->
edge damage -> dirt [E][3][7], concentrated where hands, heat and gases act: grip, mag, handguard, muzzle [E][7],
and subtle: "edge wear is a great detail but ... subtlety is key" [E][5]. Variation inside one damage type: two
scratches from one object are not equally deep [E][6]. At 3-5 m the scratches and dust must vanish and only the big
forms remain [E][7].

Our wear inputs, all available per texel from the generator [J]:
- **exposure**: edge proximity from the analytic bevel parameter (not a curvature bake), so the wear hugs real
  bevels and stops on flats;
- **handling map** per part from the spec: right hand (grip, selector, trigger guard front), support hand (lower
  handguard and its left side for a right-handed shooter), cheek (left side of the comb), shoulder (butt plate);
- **motion paths**: polished streaks along the carrier rails, charging handle slot, mag catch, mag front/back
  where it rubs the well; sling-swivel arcs;
- **heat and gas**: blued-to-straw discolouration and carbon at the muzzle, gas port and ejection port;
- **cavity dust** only where hands do not reach; oil sheen (low roughness) near moving metal;
- the sheet's own wear level ("moderate", per the prompts [M]) is the target, not a stylistic choice.

### 3.11 Moving parts and what moving reveals

Separate everything "which could move or are attached/detached" [E][4]; Fab firearms need them rigged and animated
[E][11]. Per part [J]:
- a closed manifold solid (the katana's capped kurikata lesson: open shells broke ray-parity tests [M]);
- a pivot frame and motion limits in the spec (axis, travel or angle), with real clearance (0.1-0.3 mm) to its
  neighbours so the animation never intersects (the saya fit method checks this on exported bytes [M]);
- **revealed geometry**: what the extreme pose shows must exist: the bolt face, chamber mouth and receiver rails
  when the carrier is back; the mag's feed lips, follower and top round; the dust cover's inside and the recoil
  spring guide if the cover is removed; the inside of a folding stock's hinge.

### 3.12 What makes a CG gun look fake (the checklist a judge will hit)

| # | Tell | Cause | Avoid / measurable check |
|---|---|---|---|
| G1 | **Soft, blobby bevels** | one large radius everywhere, subdivision look | process table (3.5) in the spec; measure bevel width per edge class on the mesh, CV across classes > 0.3 |
| G2 | **Missing chamfers** (razor edges, no highlight line) | edges left at zero width | every edge class has width >= the 3.3 minimum; a raking-light render shows a continuous highlight on every hard edge |
| G3 | **Faceted rounds** | too few sides on barrels, pins, grips | max facet angle on rounds <= 7.5 deg at LOD0 (48 sides on a barrel); analytic custom normals on rounds (saya, kunai precedent [M]) |
| G4 | **Shading gradients on flats** | smoothed normals across bevels | hardened/weighted normals; flat-face normal deviation < 1 deg [E][8] |
| G5 | **Floating or buried parts** | parts placed, not assembled | contact report: every part touches its parent within 0.05 mm or sits in a modelled gap 0.2-0.8 mm with depth; 0 visible intersections |
| G6 | **Wrong scale of screws, pins, rivets** | guessed sizes, usually too big | sizes from the sheet when >= 4 px; otherwise norms (3.7); listed in the spec with their source |
| G7 | **Plastic-looking metal** | metallic < 1, flat roughness, albedo too dark or too saturated | metallic exactly 0/1; bare-steel BC near Epic iron; roughness histogram on metal has >= 2 modes (finish vs worn) |
| G8 | **Metal-looking plastic** | bright edge wear on polymer | polymer wear lightens and glosses slightly; no texel of polymer with metallic 1 |
| G9 | **Uniform, symmetric or repeated wear** | curvature-only masks, mirrored UVs, one noise seed | wear = exposure x handling x motion (3.10); no mirrored UVs on asymmetric parts; per-instance seeds; left/right wear differs |
| G10 | **Symmetric stamping / everything mirrored** | modelling half and mirroring | asymmetric features (selector, charging handle, ejection port, mag catch) only where the sheet shows them; a left-vs-mirrored-right render diff is non-zero where the sheet's is |
| G11 | **Too-clean bores and openings** | black disc or flat cap in the muzzle | real bore >= 2 calibres deep with a crown chamfer, darkening with depth in BC/AO, carbon at the crown; rifling as normal only in close renders; muzzle-brake ports cut through |
| G12 | **Holes and slots without walls** | normal-map holes, zero depth | every opening the sheet shows is cut in geometry with visible wall thickness |
| G13 | **Zero-thickness sheet metal** | single-surface shells | stamped parts have their sheet thickness (~1 mm) visible at cut edges and openings |
| G14 | **Stretched or wrong-direction wood grain** | UV-projected 2D wood | solid 3D grain in a virtual blank frame (4.7): continuous across bevels and faces, end grain on cut ends |
| G15 | **Too clean / too new, or uniformly dirty** | no wear story, or a global grunge | dust only in cavities away from hands; scratches gone at 5 m [E][7] |
| G16 | **Fake markings or invented details** | decoration to "add realism" | nothing the sheet does not show (CLAUDE.md); text-free (3.8) |
| G17 | **Silhouette drift** | eyeballed outline | traced outline authority, IoU per view (6) |
| G18 | **Lost detail at distance / LOD pops** | Decimate, missing LOD3 | same-generator LODs, measured switch distances, silhouette difference <= 1 px at each switch (kunai/flashbang method [M]) |
| G19 | **Polymer without draft or parting lines** | CAD-perfect walls | 1-2 deg draft on moulded walls, parting line on the mould split |
| G20 | **Colour off under the scene light** | values picked in Blender only | crop-matched R/B, hue and median luma vs the sheet under matched light (stone S16 method [M]) |

---

## 4. Our method: the translation

### 4.1 The reference sheets: what they can and cannot tell us [M]

Measured for this note (scratchpad script, crude threshold masks):
- **Resolution.** The rifle sheet is 1536 x 1024 px; each side view spans ~720 px for ~880 mm, **about 0.8 px/mm
  (1.2 mm per pixel)**. The 1254 x 1254 sheets give ~580-600 px per gun: SMG ~0.85 px/mm, carbine ~0.7, longrifle
  ~0.6, sniper ~0.5, pistol ~2.1 px/mm. The rifle's Sheet B close-ups are ~2-3 px/mm.
- **Consequences.** Chamfers (0.2-1 mm) and most pins are below one pixel on the side views: their size comes from
  the process norms (3.5, 3.7), which is not invention, it is the manufacturing truth below the sheet's resolution
  [J]. Placement and count still come from the sheet. Small parts are measured on Sheet B where it exists.
- **Self-consistency.** The rifle's LEFT view against the mirrored RIGHT view, bounding-box aligned: **IoU ~0.89**.
  The disagreement is visible: grip angle and magazine position and rake differ between the two views. The rulers
  are unreliable too (the prompts file says so [M]). No single 3D gun can match both side views beyond about that.

So "to the T" needs rules the katana (an exact synthetic sheet, IoU 0.96-0.99 [M]) never needed [J]:
1. **Authority view per part**, recorded in the spec (e.g. magazine and grip from the view that agrees with the
   top view and the 3/4; selector and charging handle from RIGHT; dust cover and rear sight from TOP + Sheet B).
2. **Gate each view on its authority parts** (section 6), and on the rest against the sheet's own disagreement.
3. If two views disagree on something that changes the design (not just a drawing error), stop and ask the user
   which wins, or ask for a regenerated sheet (section 11).

### 4.2 The spec (one JSON per gun, like `katana_spec.json`)

Parts list with, per part: process class (3.5), bevel class per edge set, material family and texture set, texel
class (3.3), authority view, traced outline id, pivot and motion, contact parents, fastener list (position, type,
size, source = sheet px or norm), handling zones, revealed geometry. Plus the gun's frame (origin at the grip, house
rule [M ASSET_GUIDELINES]), LOD budgets and gates. Everything else reads it.

### 4.3 Geometry primitives (headless Blender 5.2)

| Primitive | For | How [M probe / M katana] |
|---|---|---|
| **Bevelled extrusion of a traced outline** | slab parts read from a side view: receiver sides, trigger guard, stock and grip blanks, sight ears, slide | Our own builder (katana `MB` style): offset the traced polygon inward by the bevel width, build the profile rings, cap. Blender's curve route (2D curve, `extrude` + `bevel_depth`, `bevel_mode` ROUND/PROFILE) also works headless: a 6-point outline gave 60 verts / 50 faces, **24 non-manifold edges until a remove-doubles weld, then 0 non-manifold and no n-gons** [M probe]. Tight concave corners need the bevel width below the corner radius |
| **Lofted sections** | barrel, gas tube, handguards, magazine body (swept along its curve), stock (sections varying along its length), rails | katana blade/saya method: section rings with explicit bevel lands, lofted on a spine; analytic normals per ring [M] |
| **Revolves** | muzzle brake body, pins, rivet heads, sight drum, scope tube, turrets | katana `revolve` [M]; 32-48 sides LOD0 |
| **Boolean cuts** | ejection port, mag well, lightening cuts, brake ports, slots | Blender 5.2 Boolean solvers FLOAT / EXACT / MANIFOLD [M probe]; cut tools carry their own chamfer; prefer building the cut into the outline/loft when possible (cleaner topology, exact UVs) |
| **Bevel modifier + Weighted Normal** | parts that are easier as boxes plus cuts | Bevel has `harden_normals`, `face_strength_mode` (FSTR_NONE/NEW/AFFECTED/ALL), `profile_type`, `limit_method`, `miter_outer`, `mark_sharp`; Weighted Normal has `mode` FACE_AREA / CORNER_ANGLE / FACE_AREA_WITH_ANGLE, `keep_sharp`, `use_face_influence` [M probe]. The house rule (Bevel with Harden Normals, then Weighted Normal with Keep Sharp) applies [M ASSET_GUIDELINES] |
| **Analytic custom normals** | rounds and large curved surfaces | `mesh.normals_split_custom_set(...)` (no auto-smooth flag in 5.x) as in `saya_game.py` and `shuriken_lib/kunai.py` [M] |

**Avoid** [J]: SDF/remesh hulls (the stone pipeline's rock method; it rounds everything, G1), subdivision surfaces
on the shipped mesh, and Decimate for LODs.

### 4.4 Topology rules

- Quads on flats; triangulate before export (house). Bevel rings follow the outline; support for rounds is the
  ring itself, not extra support loops (support loops are a subdivision tool, we do not subdivide).
- Sharp edges on bevel boundaries and on every UV seam; every 90-degree turn is a UV split [E][4].
- No hidden faces kept inside parts unless an animation reveals them (3.11).
- Mirroring only for truly symmetric hidden or tiny parts; never mirror UVs on the receiver, furniture or mag (G9).

### 4.5 Bevel classes (to put in each gun's spec) [J]

| Class | Process | Width at LOD0 | Segments LOD0 / LOD1 / LOD2 | Profile |
|---|---|---|---|---|
| M-chamfer | machined broken edge | max(0.4 mm, 3.3 minimum) | 1 / 1 / 0 | 45 deg chamfer |
| M-round | machined radius (sight ears, slide top) | 0.8-1.5 mm | 3 / 2 / 1 | round |
| S-bend | stamped sheet bend | inside radius >= thickness, outside = inside + t | 3 / 2 / 1 | round |
| S-cut | stamped cut edge | 0.2-0.3 mm land, the sheet thickness shows | 1 / 0 / 0 | chamfer |
| C-fillet | cast or forged | 1-3 mm | 3 / 2 / 1 | round |
| P-round | moulded polymer | 0.6-2 mm | 2-3 / 2 / 1 | round, with 1-2 deg draft on the wall |
| W-round | wood | 1.5-4 mm; larger in handled zones | 3-4 / 2 / 1 | round, softened |

Width is always at least the visibility minimum of the part's texel class (3.3). The LOD2 column drops bevels that
fall under ~2 px at the LOD2 switch distance.

### 4.6 UVs and the texel plan

- Parametric per-corner UVs in millimetres and an island id per face, packed once per set by the skyline packer at
  one density per class, with per-island scale (katana `katana_uvpack.py` [M]); LOD1-3 reuse the same islands.
- Sets in UV0 tiles (Metal u 0..1, Furniture 1..2, separate meshes like the magazine have their own 0..1).
- Straight, axis-aligned islands for hard surface [E][2] (fewer wasted texels, cleaner mips).
- UV1 lightmap: separate uniform pack (house rule; Fab requires it on static meshes [M ASSET_GUIDELINES]).
- `qa_check --texel` grades the object's average density [M qa_check.py]: pass the set-weighted average with a
  tolerance wide enough for the classes, and report the per-class densities from the builder (katana precedent:
  blade 54.8 px/cm with hidden faces at 0.12-0.3x [M]).

### 4.7 Per-texel painting (the katana painter, extended)

Every LOD0 face carries attributes (part code, process class, local coordinates, bevel parameter, island) that are
rasterised into each set with the 3D position; each texel is then painted from them [M katana_tex.py]. For guns [J]:
- **Edge exposure** from the analytic bevel parameter (distance across the bevel), not a curvature bake: wear lands
  exactly on bevels (G1, G9).
- **Solid wood**: grain rings computed in a **virtual blank** frame per wooden part (the axis of the tree along the
  part's long axis, ring spacing 1-3 mm, gentle ring distortion, rays and pores), evaluated at each texel's 3D
  position: continuous across bevels and faces, end grain where a cut crosses the rings (G14). Laminated furniture
  (SKS-style strips [E][6]) is the same with a strip index.
- **Process marks**: lathe rings on turned parts (radius-based), milling passes on flats (plane coordinates),
  stamping bend lines (bevel parameter), parting lines (mould split plane), all at very low normal strength and
  mostly in roughness.
- **Patterns**: checkering, knurl, stipple, serrations as height functions in the part's own frame (3.6).
- **Wear story** from the spec's handling zones and motion paths (3.10), with per-instance seeds.
- **Normal map** from the painted height only, DirectX on disk (house). **AO** from the Cycles bake of the LOD0 game
  mesh (`cycles.bake_type` AO; margin type EXTEND available [M probe]), assembled with every part in its rest pose so
  contact shadows exist (G5); metals get a mild cavity darkening in BC because Unreal's AO only touches indirect light
  (katana [M]) and Epic suggests cavity as micro-occlusion [E][10].

### 4.8 LODs

Same generators at lower resolution (segments, ring counts, bevel classes per 4.5), same islands; LOD2 replaces
dense groups (fasteners, checkered panels, small linkages) by shells whose maps are ray-cast from LOD0 (katana LOD2
tsuka shell [M]); LOD3 is the silhouette hull per part group with baked maps. Screen sizes measured: render each
switch at its distance and require <= 1 px mean silhouette difference (kunai/flashbang [M]).

### 4.9 Parts, pivots and export shape

Build: one generator per part, a pivot frame per moving part, an assembly that places parts by the spec. Export
(decided later by the engine/rig role and the user): either merged static mesh(es) plus separate mag (current rifle
plan), or one skeletal mesh with one rigid bone per moving part (Fab firearms rule [E][11]). The flashbang already
ships both forms side by side, a whole mesh plus separate body, lever and ring with pivots at sockets [M
Exports/Flashbang/README.md]. Because parts are built separately either way, the decision does not touch modelling
[J].

---

## 5. Unreal notes that affect modelling (details belong to the engine role)

- First Person Rendering (5.6+): FP primitives get their own FOV and a scale toward the camera; a "World Space
  Representation" component casts shadows and shows in reflections for other players [E][9]. One mesh with LODs can
  serve both [J]; whether the game uses a separate world model is the engine role's call.
- Import normals (not recompute), MikkTSpace tangents: our micro-only normal maps tolerate the tangent difference
  (2.2) [J]. FP self-shadow is screen-space traced [E][9]: shut-line gaps and port interiors need real depth to
  shadow at all (G12).
- Textures: BC sRGB, ORM linear, N DirectX, power-of-two with full mips (house rules [M CLAUDE.md]).

---

## 6. Gates (copy into each gun's spec)

| Gate | Threshold [J unless marked] |
|---|---|
| Silhouette IoU, authority parts, per view (ortho render of the exported FBX vs the traced sheet mask at sheet scale) | >= 0.95 side views, >= 0.93 top (sheet edges are soft at ~1 px = 1.2 mm; the katana's 0.97 was against an exact synthetic sheet [M]) |
| Silhouette IoU, whole view | >= the sheet's own left-vs-mirrored-right IoU in that region minus 0.01 (rifle whole-view self-consistency ~0.89 [M]) |
| Feature position (sight tips, pins, rivets, selector pivot, mag catch, grip and mag angles) | within 2 sheet px (side views) or 1 mm on Sheet B; angles within 1 deg |
| Bevel widths per class | equal to the spec within 0.05 mm; none below the 3.3 minimum for its texel class |
| Normals | flat-face deviation < 1 deg; max facet angle on rounds <= 7.5 deg at LOD0 |
| Contacts | 0 intersections between parts in rest and in every motion's extreme pose; every part touches its parent within 0.05 mm or sits in a modelled gap |
| Texel classes | each class within ±15 % of its target |
| Materials | metallic exactly 0/1; bare-steel BC within ±0.05 of Epic iron; crop-matched luma and hue vs the sheet within the stone S16 tolerances [M] |
| Fake checklist | G1-G20 reviewed with evidence images; 0 major |
| LOD | strictly descending; switch silhouette difference <= 1 px at 1440p |
| Blind tests (CLAUDE.md bar) | (a) **design judge**: 20 image pairs sheet crop vs our render at matched camera, light and scale (side, top, 3/4, each Sheet B close-up); the judge must not pick ours above chance (<= 12/20). (b) **realism judge**: our FP crop at 35 cm, TP at 3 m and the hero 3/4 scored against G1-G20, no "fake" call on any item. Stop early and show the user when a round fails decisively |

Review render set (per round): the sheet's views at sheet scale, a raking-light pass for edges (G1-G4), FP crops at
the 3.3 distances (hip and ADS), TP at 3 m, the muzzle and port close-ups (G11-G13), every motion's extreme pose,
LOD strip and switch frames, wireframe.

---

## 7. Pitfalls carried over from this repo

| Lesson | Source [M] | For guns |
|---|---|---|
| Ornament baked onto flat solids read flat at grazing angles; height-field relief on ornate items failed | CLAUDE.md, Snow Flower, katana plan | receiver cuts, ribs, rivets, serrations, sight ears are geometry |
| A smooth spiral with implied diamonds was the judge's first tell | katana plan (Snow Flower grip) | magazine ribs, checkered panel borders and slide serrations must be real |
| First blade colour far below polished steel's F0 | KATANA_REPORT #3 | calibrate metal against a matched crop before the look round |
| Atlas 46 % empty, hidden faces at 3.6x | KATANA_REPORT #4 | texel classes and per-island scale from day one |
| Open shells broke ray-parity tests | KATANA_REPORT #12 | every part a closed solid |
| Lacquer facets fixed by analytic custom normals | KATANA_REPORT #8 | use analytic normals on barrels, tubes, grips |
| Collision hull gaps between consecutive hulls | KATANA_REPORT #1 | (collision role) dense-sample hulls |
| A visible seat gap went unmeasured until the end | katana plan | the contact gate (6) runs from the first build |
| Two stone rounds followed a blind judge away from the sheet | STONE study rule 11 | when a judge and a measurement disagree, the measurement wins |
| Sub-texel lands broke Unreal's lightmap packer | katana plan (kunai) | do not unfold sub-texel bevel lands into their own UV charts; keep them with their neighbour face |

---

## 8. Per-gun notes (what the craft rules mean for each sheet)

| Gun | Dominant processes | Craft focus |
|---|---|---|
| **Rifle** (AK-style, wood) | stamped 1 mm sheet receiver and dust cover, machined trunnion/blocks/barrel, riveted assembly, wood furniture, stamped ribbed mag | S-bend radii and visible sheet thickness at the ejection port and dust-cover edges; rivet heads from Sheet B; mag ribs as geometry; slanted brake with cut-through port; wood with solid grain, checkered grip panels (class B); right-side selector and charging handle only; right-handed wear story |
| **SMG** (boxy polymer, folding stock) | moulded polymer upper/lower, machined steel barrel and rails, stippled grip | P-round radii and draft on ribs; stipple in normal/roughness; parting lines; polymer wear rules (G8); rail module; stock hinge as a moving part with revealed inside |
| **Carbine** (M4-style) | machined/forged aluminium receivers (anodized), polymer furniture, steel barrel, slotted handguard | M-chamfer everywhere on the receivers; aluminium wear to bright silver on high edges; original slot pattern on the handguard (no M-LOK copy); rail module; flip-up sights as moving parts |
| **LongRifle** (M16-style) | shares the carbine's receiver family, ribbed round handguard, carry handle | reuse carbine generators and the magazine; handguard ribs as geometry; fixed stock polymer with draft |
| **Sniper** (chassis, scope, bipod) | machined/painted chassis, fluted barrel, scope (machined tube, rubber eye cup), bipod (sheet/machined) | flutes as geometry; scope tube 48+ sides with analytic normals; turret knurl and scallops; painted chassis wear (paint to dark grey per the prompt); bipod legs and bolt as moving parts; most likely to press the 50k ceiling |
| **Pistol** (large-frame stainless) | machined stainless slide/barrel, rubber grip, cast/MIM small parts | brushed stainless (directional roughness along the slide axis), crisp M-chamfers, slide serrations as geometry, pebbled rubber grip in normal/roughness, slide and hammer as moving parts; the pistol sheet's ~2.1 px/mm allows tighter gates |

---

## 9. What this means for the rifle (AR-01) plan

1. Build every expected moving part as a separate closed solid with a pivot and motion limits (mag, dust cover,
   carrier + charging handle, selector, trigger, mag catch, rear sight leaf), and model what they reveal (port
   interior, bolt face, mag feed lips, follower, top round). Export as static `SM_AR01` + `SM_AR01_Mag` if that stays
   the plan, but do not weld the parts at build time: Fab's firearm rule needs them rigged.
2. Write the spec with a process class, bevel class, texel class, authority view and fastener source for every part.
3. Settle the authority view per part before tracing: the sheet's left and right views agree to only ~0.89 IoU
   (grip angle and mag position differ).
4. Gates: IoU >= 0.95 side / 0.93 top on authority parts, whole-view relative to the sheet's own self-consistency,
   feature positions within 2 px, G1-G20, two blind judges.
5. Texture plan: three 2048 sets (Metal, Wood, Magazine) in UV0 tiles, classes A-E, no mirrored UVs on the receiver,
   furniture or mag; no UDIM, no trims.
6. Bevel widths at least ~0.4 mm (rear), 0.5-0.7 mm (mid), 0.7-0.9 mm (front) at LOD0, from the process table; stamped-sheet bends
   rounded with the 1 mm sheet thickness visible at cut edges.
7. Geometry for rivets, pins, mag ribs, brake ports, the bore (>= 2 calibres deep) and checkered-panel borders;
   normal map only for checkering, grain, pores and process marks.
8. Painter: solid wood grain in a virtual blank, edge exposure from the bevel parameter, a right-handed wear story,
   metal calibrated against a sheet crop (metallic 0/1, bare steel near Epic iron).
9. LOD0 target 30-45k (ceiling 50k), LOD1-2 from the same generator, plus a LOD3 for the battle royale; screen sizes
   measured.

---

## 10. Sources

1. Taras Andrushkiv, "Gun Production From Start to Finish", 80.lv. https://80.lv/articles/gun-production-from-start-to-finish
2. Ilya Blinder, "Breakdown: How to Design a Highly Detailed AK-47 Magazine", 80.lv. https://80.lv/articles/breakdown-designing-a-highly-detailed-ak-47-magazine
3. Daulet Bekishev, "Weapon Production: Modeling and Rendering Tips", 80.lv (39k polygons over 6 texture sets; CAD to high, CAD without fillets to low). https://80.lv/articles/001agt-002mrs-003qxl-004adk-weapon-production-modeling-and-rendering-tips
4. Malte Rosenberger-Loosmann (freelance weapons artist at Rocksteady), "Modeling a Revolver: High-Low Poly, UVs, Baking", 80.lv. https://80.lv/articles/002mrs-004adk-modeling-a-revoler-high-low-poly-uvs-baking
5. Ethan Hiley (Treyarch), "Production of 3D Weapons for Video Games", 80.lv, 2017. https://80.lv/articles/production-of-3d-weapons-for-video-games
6. Simon Mercuzot (Wardog Studios), "SKS: Hard-Surface Texturing in Weapons Art", 80.lv. https://80.lv/articles/sks-hard-surface-texturing-in-weapons-art
7. Andrew Stokaliuk (Lead Weapon Artist, Team from Earth), "Breakdown: How to Make a Weapon Look Realistic and Eye-Catching", 80.lv. https://80.lv/articles/breakdown-how-to-make-a-weapon-look-realistic-and-eye-catching
8. Room 8 Studio (Kirill Udodov; COD and Overwatch credits), "FPS Weapon Creation: How To Match AAA Standards". https://room8studio.com/news/fps-weapon-creation-how-to-match-aaa-standards/
9. Epic Games, "First Person Rendering" (UE 5.6+). https://dev.epicgames.com/documentation/unreal-engine/first-person-rendering?lang=en-US
10. Epic Games, "Physically Based Materials in Unreal Engine". https://dev.epicgames.com/documentation/en-us/unreal-engine/physically-based-materials-in-unreal-engine
11. Epic Games, "Asset File Format and Structure Requirements in Fab" (Firearms: moving parts rigged, full set of animations). https://dev.epicgames.com/documentation/en-us/fab/asset-file-format-and-structure-requirements-in-fab
12. Polycount, "Weighted Normals (Mid Poly) Workflow Clarification?" [E,s]. https://polycount.com/discussion/238054/weighted-normals-mid-poly-workflow-clarification
13. Polycount, "Is a high poly model needed for realistic PBR game assets?" [E,s]. https://polycount.com/discussion/174528/is-a-high-poly-model-needed-for-realistic-pbr-game-assets
14. Matthias Patscheider, "Quarry Bank Mill 3D #08: The mid-poly workflow" [E,s]. https://matthias-patscheider.artstation.com/blog/ZXnP/quarry-bank-mill-3d-08-the-mid-poly-workflow
15. Polycount, "Decal technique from Star Citizen" [E,s]. https://polycount.com/discussion/155894/decal-technique-from-star-citizen/p6
16. Radiator Blog, "Bevels in video games", 2017. https://www.blog.radiator.debacle.us/2017/07/bevels-in-video-games.html
17. Polycount, "Best practice for modular weapon UV/Textures" [E,s]. https://polycount.com/discussion/225405/best-practice-for-modular-weapon-uv-textures
18. Fab listings, numbers from search snippets (pages return 403) [E,s]: M416/M4 rifle ~27.7k tris https://www.fab.com/listings/39d0bfca-4378-44d1-a7c3-586564b7c48c ; flintlock musket 39,150 LOD0 https://www.fab.com/listings/4ede68f1-b60b-45df-8ea7-e260f74f2382 ; assault rifle 10,195 https://www.fab.com/listings/9f7d2374-8bf4-48a2-b0c6-75e35771ee37
19. Nasty Rodent, "3D Weapon Art for Games: The AAA Production Pipeline Explained" (secondary, low authority; numbers used only as a range). https://nastyrodent.com/3d-weapon-art-for-games/
20. Texel density norms [E,s]: Timothy Dries, Beyond Extent deep dive https://www.beyondextent.com/deep-dives/deepdive-texeldensity ; Clinton Crumpler, Texel Density PDF https://static1.squarespace.com/static/5d5eb34eac3f110001ae71de/t/61fbc17457c3c3465fe8edf4/1643889045474/clinton_crumpler-abf6b83b3b65-Texel_Density.pdf
21. MIL-STD-1913 (Picatinny) dimensions. https://en.wikipedia.org/wiki/Picatinny_rail ; https://www.biggerhammer.net/picatinny/1913_specs.pdf
22. Shooting Sportsman, "Considering Checkering" (18-24 lpi; 20-24 most functional). https://shootingsportsman.com/considering-checkering/
23. Polycount, "Plastic Stippling Effect on Weapons" [E,s]. https://polycount.com/discussion/220684/plastic-stippling-effect-on-weapons

Repo sources [M]: `WorkFiles/katana/KATANA_REPORT.md`, `KATANA_BUILD_PLAN.md`, `Scripts/Katana/katana_mesh.py`,
`katana_parts.py`, `katana_tex.py`, `katana_uvpack.py`, `saya_game.py`, `Scripts/shuriken/shuriken_lib/kunai.py`,
`Exports/Flashbang/README.md`, `ASSET_GUIDELINES.md` sections 2-4, `STONE_BUILDING_STUDY.md` (3.12, rules),
`Scripts/pipeline/qa_check.py` (texel average), `References/Guns/*`, `WorkFiles/guns/GUN_REFERENCE_PROMPTS.md`.
Blender 5.2.0 API probes and the sheet measurements were run from the session scratchpad, not kept in the repo.

---

## 11. Open questions for the user

1. **Rig the guns?** Fab's Firearms category requires moving parts rigged and a full animation set. For the game MVP,
   static meshes plus a separate magazine, or skeletal guns from the start? (The build is the same either way.)
2. **Reloads and bolt cycling in the game?** If yes, the port interior, bolt face and mag top are modelled for LOD0.
3. **When the sheet's views disagree** (rifle: grip angle and mag position between LEFT and RIGHT), pick per part as
   proposed, or regenerate the sheet?
4. **Triangle ceiling for the sniper** (scope + bipod): stay at 50k or allow a recorded waiver to ~60k?
5. **Fab textures:** ship 4096 maps in the Fab version (the in-game set stays 2048)?
6. **Wear variants:** only the sheet's moderate wear, or also a clean factory variant later (cheap with the painter)?
