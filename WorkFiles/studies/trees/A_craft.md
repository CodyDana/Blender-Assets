# Study A: the craft of believable trees (engine-agnostic)

**Written:** 2026-09-29, research only (web + local files). **Scope:** a durable reference for EVERY future tree,
shrub or vegetation build in this repo, not only the dojo pines. **First client:** four niwaki (garden-pruned) Japanese
black pines from `References/Dojo/dojo_japanese_pine_ref.png` for the sunset mountain dojo
(`References/Dojo/dojo_landscape_ref.png`).

Tags: **[UNCERTAIN 5.2]** / **[UNCERTAIN 5.8]** = not verified on this machine's Blender 5.2 or Unreal 5.8.
**[SECONDARY]** = the source is a forum, a search summary or a blocked page, not a primary document.
Numbered sources are at the end.

---

## 0. The ten rules (read this if nothing else)

1. **Structure first, surface last.** A tree reads by its silhouette and its negative space before any texture.
   "Foliage textures are 90% silhouette" [15]. Our own lesson agrees: the natural parts that failed every judge
   (sand, mountains, far town) were procedural noise standing in for structure.
2. **Obey the thickness rule.** At each fork the parent's radius^n equals the sum of the children's radius^n, with
   n between 2 (Leonardo / da Vinci, area preserved) and 3 (Murray) [1][2][3]. Real trees and good art both sit in
   roughly 1.5 to 2.8 [3]. Child thicker than parent, or a twig as thick as a limb, reads fake at once.
3. **Growth is a history.** Branches carry their story: gravity sag, light-seeking, apical dominance, broken stubs,
   dead limbs, needle-free old wood [4][5][6]. A tree with no damage and no age reads as CG.
4. **Asymmetry and irregular spacing.** Even spacing and "hedge-trimmer" outlines are the classic fake [14][15].
5. **Sky holes.** Leave gaps through the canopy. Dense uniform alpha turns into a green blob at distance [14].
6. **Joints are the tell.** Root flare into the ground, branch collars at every fork, and no texture seam at welds [7][8].
7. **Value and hue, not saturation.** Foliage is dark: conifer forest albedo is about 0.08-0.12 linear
   (about sRGB 80-97) [16, SECONDARY]. Interior shading (AO) and back-light translucency sell volume [10][11].
8. **Wind is a hierarchy.** Trunk slowest, primary branches faster, leaves/needles fastest; each with its own phase
   [10][11][12].
9. **Plan the far view from day one.** LODs, impostors or voxels, and alpha coverage in the mips all decide how
   the tree looks at 50-500 m [11][17][18].
10. **Blind judge + measured numbers** is the gate for trees as for everything else (CLAUDE.md). The measurable
    items below (Section 11) are written so a check script can compute them.

---

## 1. Tree anatomy and growth rules

### 1.1 Branch hierarchy (orders)
- Trunk (order 0) → scaffold/primary limbs (1) → secondary (2) → twigs/shoots (3+) → leaf/needle-bearing shoots.
  Generators (SpeedTree, PVE, Weber-Penn) are organised around these levels: one generator per level with its own
  length, angle, count and radius curves [9][13][20].
- **Monopodial vs sympodial.** Monopodial: a dominant leader continues straight and laterals come off it (pines,
  spruce; "excurrent" crowns). Sympodial: the leader stops and laterals take over, so the crown is forked and
  rounded ("decurrent"; most broadleaves, old pines) [4][5]. Honda's model uses contraction ratios r1 (continuing
  axis) and r2 (lateral) plus branching angles; the ABOP reference values are r1 = 0.9, r2 = 0.6-0.9, branch angle
  about 30-45 deg, divergence 137.5 deg [4].
- **Pines specifically** grow in yearly **whorls**: each spring the terminal bud extends as a "candle" and forms a
  ring of new laterals at its tip. So an unpruned young pine has tiers of branches at about one-year intervals.
  Japanese black pine can make **two flushes a year** (a second set of shoots after the first) [21]. Needles are in
  **pairs** (fascicles of two, with a grey-white sheath), 7-12 cm long, 0.7-1.2 mm wide, dark green, stiff and often
  twisted, and they **persist 3-4 years**. So the needles sit only on the outer 3-4 years of each shoot and the
  wood inside is bare [21][22]. Winter buds are white, 1.5-2 cm; the bark is dark grey or purple-grey, scaly and
  plated with long fissures on old wood, and grey-brown on young branches [22].

### 1.2 Taper and the pipe model
- **Pipe model / Leonardo's rule:** the total cross-section above a fork equals the cross-section below it, so
  r_parent^2 = sum r_child^2 [1][2]. Generalised as r^n = r1^n + r2^n, with n "usually between 2 and 3" in the
  space colonisation paper [5]. The ABOP ternary example uses the da Vinci width ratio sqrt(3) ≈ 1.732 for 3 equal
  children [4].
- Measured exponents in trees and in celebrated tree art span about **1.5-2.8**. Lower values give fast taper and
  many fine twigs; values near 3 give chunky limbs [3]. Reviews warn that the rule "does not hold in general"
  branch by branch, so use it as a statistical target, not an exact law [1][2].
- **Along a single branch**, taper is not linear: it flares at the base (collar), is fairly even along the middle,
  and thins sharply at the tip. Trunks flare at the ground (root flare / buttress) [8].

### 1.3 Branch angles and placement (phyllotaxis)
- Successive laterals rotate about the parent by a **divergence angle**, often near the golden angle 137.5 deg,
  which avoids stacking laterals directly above each other [4][19]. Pine whorls instead put 3-6 laterals at one node.
- Branching angle from the parent: about 30-60 deg for young laterals; older laterals droop lower under their own
  weight. Honda/ABOP tables give usable starting sets (e.g. r1 0.9, r2 0.7, a1 10, a2 60 for sympodial forms) [4].
- Bonsai/niwaki rule of placement: branches alternate **left, right, back**, never in symmetrical pairs, and no
  major branch crosses the trunk seen from the front. The first branch sits at about **1/3 of the height**, and
  branch size decreases toward the apex [23].

### 1.4 Tropisms and competition
- **Gravitropism / weight:** ABOP bends each segment slightly toward a tropism vector T. The rotation is
  proportional to |H × T| (torque), scaled by a susceptibility e [4]. Heavy horizontal limbs sag then turn up at the
  tip (light-seeking), giving the S-curve typical of old pines.
- **Phototropism / light competition:** buds in shade die and lit buds grow. This produces hollow crown interiors
  and outward-facing foliage [6]. Space colonisation models the same effect as competition for space: attraction
  points inside a crown envelope pull branch tips toward them. The parameters are the point count N, the
  influence radius di and the kill distance dk (e.g. N = 375-12000, dk = 2D-20D, di = 8D-17D, where D = segment
  length). Fewer points + larger dk give sparser, straighter branching [5].
- **Apical dominance / apical control:** hormonal signalling decides whether the leader dominates (a conical
  excurrent crown) or laterals catch up (a domed decurrent crown). Palubicki et al. model bud fate from light plus an
  internal signal [6]. Stava et al. use apical dominance, phototropism, gravitropism and a light-driven pruning
  factor as fitted parameters [24].

### 1.5 Age and damage (the believability layer)
- Dead branches, broken stubs with caps, knots, scars, missing limbs and lean are what separate a real tree from a
  generated one. "Not adding dead branches is a common pitfall ... making trees totally straight is another" [14].
  SpeedTree exposes this directly with Break Chance, Break Spot, caps, Disturbance and Jink properties [13].
- Bonsai/niwaki vocabulary: **nebari** (visible radial surface roots, flaring wider than the trunk, not crossing),
  **tachiagari** (the trunk's curve between roots and first branch), **jin** (dead stripped branch), **shari** (dead
  stripped trunk strip) [23].
- Niwaki pines are maintained twice a year: **midoritsumi** in spring shortens the new candles, and **momiage** in
  autumn/winter hand-plucks old needles and thins shoots to one or two, leaving about 7-8 needle pairs per shoot.
  Result: **open, layered pads** with light through them and bare wood visible inside [25][26]. That is exactly
  what the reference close-ups show (radiating needle tufts at twig tips, brown twigs visible between).

---

## 2. Generation approaches (what each is good at)

| Approach | How it works | Strength | Weakness | Use here for |
|---|---|---|---|---|
| **L-systems** [4] | String rewriting + turtle geometry; parameters per production (length ratios, angles, width ratio, tropism) | Compact, exact control of branching topology and ratios | Hard to art-direct the overall silhouette; no environment response without extensions | Secondary/tertiary ramification inside a pad; quick parameter studies |
| **Recursive parametric (Weber-Penn 1995)** [9] | Per-level params: Shape, BaseSize, Levels, DownAngle, Rotate, Branches, Length, Curve, Taper, Leaves; paper presets for real species; built-in distance degradation | Artist-readable; Blender's Sapling add-on implements it [27] | Generic "CG tree" look if left at defaults; weak on designed forms like niwaki | Background filler; not hero niwaki |
| **Space colonisation (Runions 2007)** [5] | Attraction points in a crown envelope; tips grow toward points and remove them | Natural, space-filling branching that fits a given envelope (can be a traced silhouette) | Can't do strongly weeping forms; topology can look "vascular" without pruning and tropism | Filling a pad or crown envelope traced from a reference |
| **Self-organising / bud-fate (Palubicki 2009)** [6] | Buds compete for light; signalling sets apical control; shedding | Most botanically convincing, emergent age structure | Many parameters; slow to art-direct | Studies of natural (unpruned) species |
| **Node/generator model (SpeedTree)** [13][20] | Generators per level; each property is a curve over the parent's length/age; hand-drawn splines can replace any procedural branch and procedural children still grow on them; node-edit individual branches | Industry standard; mixes procedural and hand-drawn | Paid; not in our Blender pipeline | Reference for our own design (see 2.1) |
| **UE 5.8 Procedural Vegetation Editor (PVE)** [28] | PCG-based graph: Grower (pseudo-botanical: phyllotaxy, phototropism, gravity, bifurcations, auxin-based apical dominance), Graft Distributor, Foliage Distributor, Mesh Builder, Bone Reduction, Import/Extract; exports Nanite Foliage assets with Dynamic Wind data | Native output to Nanite Foliage + wind; Megaplants presets | Experimental; "5.7 assets are not compatible with 5.8"; architecture changes between releases [28] | Possible final assembly step for a Blender-made skeleton (to test, see 9) |
| **Hand-guided splines** | Artist draws the trunk and primary limbs; procedural rules fill the rest | The only reliable way to match a designed, reference-specific form | Manual time | **Hero trees that must match a reference: niwaki, bonsai, signature trees** |

### 2.1 What this means for us
- A designed tree (niwaki) is **authored at the top of the hierarchy, generated at the bottom**. Trace the trunk
  and scaffold limbs from the reference (our proven "tracing as 2D outline authority" method), then generate the
  ramification and needle tufts procedurally inside traced pad envelopes (space colonisation or L-system inside an
  envelope). This is exactly SpeedTree's "hand-drawn generator with procedural children" model [13][20].
- Do not try to make a growth simulator produce a niwaki: pruned trees are human-designed, and no botanical rule
  produces cloud pads.
- **Build from reusable parts.** Guerrilla builds a few components at high detail with their own LOD chains, then
  assembles trees from them [11]. Megaplants ship the same way. The local `Megaplant_Library` holds instanced parts
  (`Ginkgo_Branch_01..05`, `Ginkgo_Spur_01..05`, `Ginkgo_Dead_Branch`, `Tree_Japanese_Cypress_Branch_01..06`,
  `Japanese_Cypress_Decorations_01_A..E`) plus 4-7 whole-tree variants (`Tree_*_01_A..G`, each with its own
  `_Skeleton`) and a `PVE_Preset_*` [local listing, DemoGame_1/Content/Megaplant_Library, read-only]. Nanite
  Assemblies instance up to 65,000 parts per asset (one Epic example: 3.5 GB compressed to 29 MB) [17].

---

## 3. Silhouette: distance vs close up

- **At distance (> ~30 m)** only the outline, the value masses and the sky holes survive. Judge by squinting or
  down-sampling: the tree must still read as its species/style at 64 px tall. Megaplants and Nanite Voxels exist
  because at distance "clusters of leaves and needles are reduced to individual voxels" [17][29]. The masses must
  already be right in the geometry.
- **Mid (5-30 m):** branch structure through the gaps, pad layering and the trunk line. This is where niwaki live in
  our dojo (courtyard/outside-wall distances).
- **Close (< 5 m):** needle fascicles, bark plates, collars, bud candles, moss at the base.
- Rules that hold at every distance [14][15]:
  - vary cluster sizes and space them unevenly;
  - let a few shoots break the silhouette (a sprig into the sky sells scale);
  - dead trunks, bare branches and sparse zones add realism;
  - "cluster a lot of things together while leaving other parts practically barren".
- **Niwaki reading:** a strongly curved dark trunk plus 5-12 flattened, dome-topped pads stacked in tiers, each with
  a dark underside and a lit top rim, and clear sky between tiers. The reference sheet's 12 variants all follow
  this: pads get smaller toward the apex; the apex is a small rounded crown; the lowest pad often reaches far out on
  one side (the "reaching arm" of the large slanted variants).

---

## 4. Foliage representation

### 4.1 The options

| Representation | Cost profile | Looks | Notes |
|---|---|---|---|
| **Real geometry per leaf/needle** | Massive triangle counts; OK only with Nanite Foliage (assemblies + voxels) | Best close-up and at glancing angles; no alpha shimmer | Epic's Nanite Foliage explicitly drops alpha cards: masking "causes excessive overdraw", so "use fully modelled geometry down to individual leaves" [17]. Witcher 4 demo: every leaf and pine needle modelled, 500k+ trees, voxels at distance, 60 fps on PS5 [29]. **Experimental in 5.8** [17]. |
| **Cluster meshes (cutout geometry)** | Medium triangles, low overdraw | Good; the silhouette is in the geometry | SpeedTree advice: cut transparent pixels out of cards with mesh cutouts to cut overdraw [30]. |
| **Alpha cards (atlas of baked clusters)** | Few triangles, high overdraw, alpha shimmer | Good at mid distance if the atlas is good; flat edge-on | The classic game approach (HZD: trees ~10k tris LOD1 → 12-tri billboard at LOD5) [11]. Masked in Nanite costs more than opaque. |
| **Fronds** (strips following a spine) | Low | Good for fern-like needle sprays (spruce) | "Norway spruce needles are often made with fronds ... more like furry twigs" [31, SECONDARY]. |

### 4.2 Conifers and needle pads specifically
- Conifer needles are "difficult to get right without things feeling noisy" [31, SECONDARY]. Production answers:
  - **Needle cluster cards:** render a small branchlet with many needles into an atlas and put that on crossed or
    bent cards. A 2K cluster atlas with Color/Opacity/Normal/AO/Roughness/Subsurface is typical [32, SECONDARY].
  - **Branch-end meshes plus inner filler cards:** a generated mesh at each branch end, then camera-facing cards
    between it and the trunk for fullness (attributed to The Witcher 3) [31, SECONDARY].
  - **Rotated planes + vertex noise** around a stem until "full and bushy" (longleaf pine clusters) [33].
  - **Geometry needles on Nanite Foliage** (Megaplants conifers: Norway Spruce, Japanese Cypress) [17][34].
- **For a pine fascicle tuft** (the reference close-ups): each shoot tip is a radiating starburst of 2-needle
  fascicles, a hemisphere of stiff needles, 7-12 cm, with the white candle in the centre and bare twig behind. Model
  ONE tuft (or 3-5 variants) as real geometry and instance it at every twig tip. Each needle can be a 3-sided or
  flat 2-tri strip. This matches the Nanite Foliage direction and gives a clean source to bake cards from for a
  card LOD.
- **Needle pad = cloud of tufts.** A pad is not a textured dome. It is 20-80 tufts on a flat, fan-shaped twig
  network, denser at the top and rim, with the underside darker and more open.

### 4.3 Foliage normals and shading
- **Card/cluster normals:** raw card normals make each card shade flat. Transfer normals from a proxy volume
  (sphere/ellipsoid around a pad) so the pad shades as one soft volume. In Blender: a Data Transfer modifier with Face
  Corner Data > Custom Normals from a bigger sphere, or a Normal Edit modifier (Radial) [35]
  **[UNCERTAIN 5.2: modifier names/options unchanged since 4.x]**. HZD flips normals "incorrectly" on purpose for
  canopies (it abs()'s the view-space normal Z) but keeps correct tangent-space flipping for "most pine trees" [11].
- **Translucency:** back-lit needles and leaves glow. Crysis multiplies a thickness/subsurface map by a back-side
  lighting term [10]. HZD's translucency = back light × view/light angle × albedo max luminance × thickness × AO ×
  an artistic boost [11]. In UE: Two Sided Foliage shading model with Subsurface Color, masked, two-sided [36]
  (Megascans tip: push normal intensity and translucency contrast because defaults look flat [36, SECONDARY]).
  **For sunset back-light (our dojo), translucency is a first-order look item, not polish.**
- **AO:** bake AO into vertex colour or texture so pad interiors are darker (Crysis: vertex alpha = AO; HZD: baked
  AO per vertex and in textures) [10][11].
- **Reflectance:** HZD fixes vegetation F0 at 4% dielectric; roughness is artist-set and modulated by AO and
  translucency [11].

---

## 5. Bark

- **Three texture strategies, usually combined:**
  1. **Tiling bark** for branches (cheap, shared; one draw call per branch material, so keep it to one or two)
     [30].
  2. **Unique baked trunk** for hero trees: sculpt or scan the trunk and root flare, bake to a unique texture. The
     trunk is the most-seen part up close.
  3. **Trim/detail overlays:** moss, lichen, char, wet streaks via vertex colour or a second UV (the longleaf pine
     project blended a charred bark variant by vertex paint) [33].
- **Displacement vs normal:** bark plates on an old pine are deep (cm scale), and a normal map alone reads flat at
  silhouettes and grazing sunset light. Options: real geometry for the big plates on the trunk (our house rule:
  "model real forms as real geometry"), normal + AO for the small scale. Megaplants ship `T_*_NAH` (normal, AO and
  height packed, by name) plus `T_PVE_MeshDisplacement_*` textures [local listing], so they displace the mesh.
  UE 5.8 Nanite tessellation/displacement exists but a 5.8 forum report says it broke where 5.7 worked
  [37, SECONDARY] **[UNCERTAIN 5.8]**. Don't depend on runtime displacement; bake it into geometry in Blender.
- **UV and texel density:** keep bark texel density consistent from trunk to branches, and run UVs along the
  length so fissures follow the grain [33]. Mismatched density at a fork is a classic tell.
- **Branch joints:** SpeedTree does not fuse branches. It **welds** the child's base ring onto the parent's surface
  with a "web" spread, then **blends the parent's texture coordinates** a short distance up the child to hide the
  texture seam. Game exports add seam-blend geometry that fades by vertex alpha [7]. In Blender we can fuse the
  first ring into the parent (skin modifier, voxel remesh of the trunk+limb union, or a manual weld) and blend with
  a vertex-colour mask. Real anatomy to imitate: the **branch collar** is a swelling formed by trunk tissue growing
  over the branch base each season [8].
- **Root flare:** the trunk widens into radial buttress roots at the ground [8]. For niwaki, exposed **nebari**
  spreading wider than the trunk [23]. The reference's rock-planted variants show roots gripping over stone.
- **Bark colour on this reference (measured on the rendered close-up, NOT albedo):** darkest 10% sRGB about
  (34,22,17), median (82,73,64) at hue ~30 deg sat 0.22, brightest 10% (163,141,123). The deep fissures are nearly
  black-brown and the plate tops are pale warm grey-brown: **high value contrast** between plate and fissure is the
  look.

---

## 6. Texture atlases and baking (high-poly foliage → cards)

- **Pipeline** (SpeedTree Leaf Map Maker, Guerrilla, industry): model a small branchlet at full detail → render or
  bake it orthographically to an atlas (colour, alpha/opacity, normal, AO, translucency/thickness, optionally
  depth/height) → cut the atlas into card meshes → build the tree from cards [11][38].
  - SpeedTree map-maker tips: vary hue/saturation/value/normals per leaf while rendering, and use leaf collision to
    cull overlapping leaves before the capture [38].
  - Pack several trees into one atlas for draw-call and memory savings [38].
- **HZD packing:** BC7 (normal + mask + AO), BC7 (colour + translucency), BC4 alpha [11]. Megaplants naming seen
  locally: `_CA` (colour+alpha), `_NT` (normal + translucency, by name), `_C`, `_NAH` [local listing]. Those channel
  meanings are read from the suffixes, not opened **[UNCERTAIN]**.
- **Alpha in the mips:** plain mip generation shrinks alpha-tested foliage at distance (trees "thin out"). HZD
  rebuilt each mip to preserve the original coverage at the 0.5 cutoff (a histogram-based scale per mip) [11].
  Ben Golus covers coverage-preserving mips and alpha-to-coverage [18]. In UE, check that masked foliage keeps its
  coverage at LOD distances **[UNCERTAIN 5.8: exact texture setting]**.
- **Leaf/needle scale honesty:** needles must match the species' size (7-12 cm for black pine [22]); oversized
  needles on cards are an instant scale error.
- **Blender-side:** Cycles can bake Selected-to-Active or render orthographic passes of a branchlet. Baking alpha
  onto a card may need an emission/holdout trick **[UNCERTAIN 5.2: whether a native alpha bake pass exists]**.

---

## 7. Colour and value ranges

- **Albedo (linear) guidance** from a widely used chart: conifer forest 0.08-0.12, summer foliage 0.09-0.12,
  deciduous 0.15-0.18, short grass 0.20-0.25 [16, SECONDARY]. In sRGB 8-bit: 0.08 → 80, 0.12 → 97, 0.18 → 118
  (computed). General PBR practice: avoid albedo under about sRGB 30-50 and over 240 [16, SECONDARY].
- **Measured on the owner's pine reference (rendered, lit, not albedo):** needle close-up median sRGB (80,91,50),
  hue ~75 deg (yellow-olive, NOT blue-green), sat ~0.45; 10th percentile (46,54,22); 90th (148,158,114). Use these
  as a **look target for renders**, not as albedo.
- **Art direction lesson (Ghost of Tsushima):** "limiting the variety of foliage, pushing color values, increasing
  translucency levels, and reducing noise on textures" [12]. Readable, bold and clean beats noisy and "realistic".
  The team photo-scanned real leaves from Tsushima [12].
- **Per-instance tint:** HZD colourises most vegetation in the shader: Result = Texture × (2 × Colorize × Mask +
  1 − Mask), with the colour picked from a texture array by asset type, world data (erosion, flow, nearness to water)
  and ecotope [11]. Longleaf pine project: per-instance colour shift where "small values go a long way" [33].

---

## 8. Variation strategy

- **Seeds:** every generator level gets its own seed (SpeedTree groups seeds by property type and can randomise
  one or all) [13]. Keep seeds in the build script's spec so a variant can be rebuilt byte for byte.
- **Variants from one kit:** Megaplants ship 4-7 whole-tree variants per species, each built from the same shared
  branch parts [local listing]. HZD builds each asset out of shared components [11].
- **Cheap variation:** rotation about Z, ±10-15% uniform scale, mirroring (only for trees without a designed front;
  niwaki HAVE a front, so do not mirror them blindly), per-instance hue/value tint, and a different wind phase per
  instance.
- **Real variation lives in structure.** Four niwaki should differ in trunk line (the reference shows upright,
  slanting, twin-curved and rock-planted forms), pad count, and the side of the reaching limb, not just tint.

---

## 9. Wind animation principles

- **Hierarchy (every source agrees):**
  - **Trunk / main bending:** slow, whole-tree sway along the wind direction, weighted by height [10][11][39];
  - **Branch motion:** each primary branch sways with its own phase, weighted by distance from the trunk [10][11][39];
  - **Leaf/needle detail:** fast, small amplitude, noise-driven flutter or ripple along normals, weighted by distance
    from the branch [10][11][39].
  - SpeedTree's rule: Shared motion slower than Branch motion, which is slower than leaf motion. Only one or two
    branch levels get independent motion, usually the big limbs off the trunk [39].
- **Data encoding (classic WPO path):** Crysis paints vertex colours: R = edge stiffness, G = per-leaf phase,
  B = overall stiffness, A = AO. It keeps bending length-preserving by re-normalising each vertex's distance to the
  centre, and it layers object, branch and vertex phases so "every leaf moves differently" [10]. HZD stores height,
  distance-to-trunk, distance-to-branch, an index/offset and AO per vertex, and samples a global wind field
  (~150 µs compute) at the object centre. It drives leaf motion from a tiny 16³ simplex noise texture [11].
- **Nanite Foliage path (UE 5.8, experimental):** wind is **skeletal**, not WPO. The Dynamic Wind plugin groups
  bones into simulation groups (trunk / branch / twig). Wind is global direction only: no local wind, no player
  collision. Animation stops below a screen size (Animation Min Screen Size). 100k bones update in ~0.1 ms [17].
  So a Blender tree bound for Nanite Foliage needs a **bone per trunk segment and per primary/secondary branch**
  (a few dozen to a few hundred bones), with the needle tufts rigid on their twig bone.
- **Ghost of Tsushima:** a single world wind grid drives grass, trees, cloth and particles, and plants are "rigged
  with joints that respond to the local wind speed, with separate controls for trunks from the branches" [12][40].
- **Stiffness by species/style:** niwaki black pines are stiff (thick short limbs, stiff needles, pads thinned for
  light). Wind should be a gentle pad bob plus needle shimmer, never a whole-tree rocking.
- **Performance hygiene (from our look research):** set WPO Disable Distance for WPO foliage; watch Virtual Shadow
  Map cache invalidation from animated foliage [local CINEMATIC_LOOK_RESEARCH.md §2.9]. Nanite Foliage doc: disable
  animation at distance for VSM performance [17].

---

## 10. LOD and impostor strategies

- **Classic chain (HZD trees):** LOD1 ~10,000 tris high shader → LOD2 ~2,600 → LOD3 ~1,200 low shader → LOD4
  ~200 + 12 with a billboard fading in → LOD5 12-tri billboard. Separate, cheaper **shadow-caster meshes** (even
  non-alpha-tested, non-animated for the far cascade). "LOD up, not down": build the lowest LOD first and add
  detail [11]. SpeedTree real-time library trees: 1,000-12,000 tris at the top LOD; about 3 draw calls (branches,
  fronds, leaves) [30].
- **Impostors:** octahedral impostors capture the tree from many view angles into an atlas (with G-buffer data);
  Epic's Impostor Baker was used for Fortnite BR distant trees [41]. Good for far LODs of non-Nanite trees and for
  HLOD.
- **Nanite Foliage (UE 5.7+, experimental in 5.8):** Assemblies (instanced parts) + Skinning (bones for wind) +
  **Voxels**. Near-pixel-sized voxels replace triangles at distance and keep volume, animation and material, turned
  on with Nanite Settings > Shape Preservation > Voxelize. Enable Nanite Foliage in Project Settings > Rendering
  [17]. Our DojoLab ini already has `r.Nanite.Foliage=True` [local CINEMATIC_LOOK_RESEARCH.md].
  **[UNCERTAIN 5.8: whether a Blender FBX static mesh with voxelize gives acceptable results without PVE/assemblies;
  to test.]**
- **Fab/our rules still apply:** Import Mesh LODs ON, a LOD statement even when zero; Nanite for dense opaque
  meshes (ASSET_GUIDELINES §6.2). Masked (alpha) materials under Nanite work but cost more; geometry needles avoid
  alpha entirely.
- **Our measured warning:** "Megaplants are extremely heavy: a few at the edge, not a forest" [local
  CINEMATIC_LOOK_RESEARCH.md]. Budget the four niwaki as heroes; far forests stay pack/impostor/voxel.

---

## 11. Common failure modes (the checklist a judge will hit)

| # | Failure | Why it reads fake | Measurable check |
|---|---|---|---|
| F1 | Green blob, no sky holes | No negative space; canopy reads as one surface [14] | Canopy gap fraction in the silhouette mask vs the reference panel |
| F2 | Even spacing / symmetry / "hedge-trimmer" outline | Nature is clustered and asymmetric [14][15] | Pad size CV; left/right mass ratio; no mirrored pairs |
| F3 | Straight trunk, linear taper, no flare | Trees record gravity, light and age [14] | Trunk curvature vs a traced centreline; flare ratio (base radius / radius at 1 m) |
| F4 | Wrong thickness hierarchy | Violates the pipe model [1][3][5] | Per fork: n solving r^n = Σ r_i^n in 1.8-3.0; no child > parent |
| F5 | Visible seams at forks, cylinder-into-cylinder | Real forks have collars and continuous bark [7][8] | Visual close-up + no open boundary edges at joints |
| F6 | Cards visible edge-on / flat-shaded cards | Card normals, no volume normals [35] | Rotate 360°: no card lines in silhouette at mid distance |
| F7 | Foliage too bright / too saturated / blue-green for this species | Albedo out of range; wrong hue [16][22] | Albedo median in band; render hue near the ref's ~75 deg |
| F8 | No interior darkness or back-light | No AO, no translucency [10][11] | Pad underside/top luminance ratio; back-lit render check |
| F9 | Everything the same age: no deadwood, no bare inner wood | Real pines shed inner needles (3-4 yrs) [22]; niwaki are hand-thinned [25] | Needle-free fraction of inner twig length |
| F10 | Scale errors (giant needles, thick twigs) | Kills scale instantly | Needle length 7-12 cm; twig min radius |
| F11 | Rigid or synchronised wind; stretching | Hierarchy/phase missing [10][39] | Visual; per-instance phase present |
| F12 | Thinning or popping at distance | Alpha mips / LOD transitions [11][18] | Silhouette area at LOD N ≥ ~90% of LOD0 at switch distance |
| F13 | Procedural noise instead of structure | **Our own repeated failure** (sand, mountains, far town) | The judge's design-level blind test |
| F14 | Repeated identical clusters | The tiling of one card/tuft is visible | ≥ 3 tuft/card variants, random roll and scale |

---

## 12. Where this lands for the four niwaki (input to the plan, not a plan)

- **Method:** hand-guided. The trunk and scaffold limbs are traced from the reference panels (the 2D outline
  authority), with pad envelopes also traced. Procedural ramification fills inside each envelope (space colonisation
  or an L-system with the Honda/ABOP ratios), with needle-free inner wood. The needles are an instanced, modelled
  2-needle fascicle tuft (3-5 variants) with a white candle. The bark is real geometry for plates on the trunk plus
  one unique trunk bake and one tiling branch bark, with collars and nebari modelled.
- **Two foliage tiers from one source:** (a) geometry needles for Nanite Foliage **[UNCERTAIN 5.8, experimental]**;
  (b) a baked needle-tuft atlas on cutout cards as the fallback LOD and for non-Nanite use. Both come from the same
  modelled tuft.
- **Wind readiness:** keep a bone hierarchy (trunk segments → limbs → pad twigs) in the build spec even if the
  first ship is static. It is needed for Dynamic Wind (skeletal) and useful for WPO pivots.
- **Worth a spike, not an assumption:** PVE's **Import / Extract From Mesh** workflow can turn an existing
  vegetation mesh into PVE skeleton data. If a Blender-built pine imports this way, PVE's Mesh Builder, Foliage
  Distributor and Export could give us Nanite Foliage with Dynamic Wind natively [28]. **[UNCERTAIN 5.8; the
  feature is experimental with breaking changes between versions.]**
- **Gates** (to add to the build spec): silhouette IoU per variant against its traced reference panel; pad count
  and tier count; canopy gap fraction; per-fork exponent n in 1.8-3.0; needle length 7-12 cm; needle albedo in
  band and render hue near the reference; bark plate/fissure value contrast; triangle and bone counts per LOD; a blind
  judge on image pairs.

---

## 13. Uncertain / to verify

- Blender 5.2: Sapling Tree Gen is an extension now (0.3.7 for 4.4+; a fork claims 5.2 LTS support) and Modular
  Tree updated for 5.0 [27]. Not tested here. We would write our own generator anyway (headless, spec-driven).
- Blender 5.2: Data Transfer / Normal Edit modifier behaviour for custom normals; alpha baking options.
- UE 5.8: Nanite Foliage, Nanite Assemblies, Dynamic Wind and PVE are all **Experimental** [17][28]. 5.7 PVE
  assets are not compatible with 5.8 [28]. Nanite displacement had a 5.8 regression report [37].
- UE 5.8: exact texture settings to preserve alpha coverage in mips for masked foliage.
- Megaplants channel packing (`_NT`, `_NAH`, `_CA`) is inferred from names in the local folder, not opened.
- The albedo chart values [16] come via a search summary of a blocked page. Cross-check against a primary chart
  before hard-coding gates.
- The Witcher 3 pine technique and the spruce "fronds" tip are forum claims [31].

---

## Sources

1. Lehnebach et al., *The pipe model theory half a century on: a review* (Annals of Botany, 2018) — https://pmc.ncbi.nlm.nih.gov/articles/PMC5906905/
2. Sone et al., *Maintenance mechanisms of the pipe model relationship and Leonardo da Vinci's rule* (J Plant Res 2009) — https://link.springer.com/article/10.1007/s10265-008-0177-5
3. *Scaling in branch thickness and the fractal aesthetic of trees* (PNAS Nexus 2025) — https://academic.oup.com/pnasnexus/article/4/2/pgaf003/7996468
4. Prusinkiewicz & Lindenmayer, *The Algorithmic Beauty of Plants*, ch. 2 "Modeling of trees" — https://algorithmicbotany.org/papers/abop/abop-ch2.pdf (phyllotaxis ch. 4: https://algorithmicbotany.org/papers/abop/abop-ch4.pdf)
5. Runions, Lane, Prusinkiewicz, *Modeling Trees with a Space Colonization Algorithm* (EG NPH 2007) — https://algorithmicbotany.org/papers/colonization.egwnp2007.large.pdf
6. Palubicki et al., *Self-organizing tree models for image synthesis* (SIGGRAPH 2009) — https://algorithmicbotany.org/papers/selforg.sig2009.html
7. SpeedTree docs, *Branch Intersections* (welding, intersection blending, seam blends) — https://docs.speedtree.com/doku.php?id=branchintersections
8. *Branch collar* — https://en.wikipedia.org/wiki/Branch_collar ; root flare: https://extension.illinois.edu/blogs/garden-scoop/2021-08-27-tree-root-collar-disorders
9. Weber & Penn, *Creation and rendering of realistic trees* (SIGGRAPH 1995) — https://dl.acm.org/doi/10.1145/218380.218427 ; https://history.siggraph.org/learning/creation-and-rendering-of-realistic-trees-by-weber-and-penn/
10. Sousa, *Vegetation Procedural Animation and Shading in Crysis* (GPU Gems 3, ch. 16) — https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-16-vegetation-procedural-animation-and-shading-crysis
11. Sanders, *Between Tech and Art: The Vegetation of Horizon Zero Dawn* (GDC 2018 slides) — https://media.gdcvault.com/gdc2018/presentations/gilbert_sanders_between_tech_and.pdf ; https://www.gdcvault.com/play/1025530/Between-Tech-and-Art-The
12. PlayStation Blog, *Crafting the world of Tsushima* — https://blog.playstation.com/2020/07/09/crafting-the-world-of-tsushima/ ; *How stunning visual effects bring Ghost of Tsushima to life* — https://blog.playstation.com/2021/01/12/how-stunning-visual-effects-bring-ghost-of-tsushima-to-life/
13. SpeedTree docs, *Spine Generator* (seeds, hand drawn, disturbance, jink, break, bifurcation) — https://docs.speedtree.com/doku.php?id=spine_generator
14. Polycount, *Best Practices for Creating 3D Trees for Games* — https://polycount.com/discussion/98091/best-practices-for-creating-3d-trees-for-games (search-summarised) [SECONDARY]
15. Weinbaum, *Art Tips for Building Forests* (Game Developer) — https://www.gamedeveloper.com/art/art-tips-for-building-forests
16. Iri Shinsoj, *PBR, colour space conversion and albedo chart* — https://shinsoj.artstation.com/blog/Q9j6/pbr-color-space-conversion-and-albedo-chart (403 on fetch; values via search summary) [SECONDARY]; DONTNOD PBR chart referenced there
17. Epic, *Nanite Foliage* (UE 5.8 docs) — https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-foliage ; *Nanite Assemblies* — https://dev.epicgames.com/documentation/unreal-engine/nanite-assemblies
18. Golus, *Anti-aliased Alpha Test: The Esoteric Alpha To Coverage* — https://medium.com/@bgolus/anti-aliased-alpha-test-the-esoteric-alpha-to-coverage-8b177335ae4f
19. *Phyllotaxis* — https://en.wikipedia.org/wiki/Phyllotaxis ; Honda 1981 branch interaction — https://harvardforest1.fas.harvard.edu/publications/pdfs/Honda_AmJBotany_1981.pdf
20. SpeedTree docs, *Generators* — https://docs.speedtree.com/doku.php?id=generators
21. *Pinus thunbergii* — https://en.wikipedia.org/wiki/Pinus_thunbergii ; NC State — https://plants.ces.ncsu.edu/plants/pinus-thunbergii/
22. Gymnosperm Database, *Pinus thunbergii* — https://www.conifers.org/pi/Pinus_thunbergii.php
23. *Bonsai aesthetics* — https://en.wikipedia.org/wiki/Bonsai_aesthetics
24. Stava et al., *Inverse Procedural Modelling of Trees* (CGF 2014) — https://onlinelibrary.wiley.com/doi/abs/10.1111/cgf.12282
25. Niwaki (Jake Hobson), *Momiage pine pruning* — https://www.niwaki.com/mid-winter-momiage ; *Pine workshop* — https://www.niwaki.com/pine-workshop/
26. RHS, *Cloud pruning* — https://www.rhs.org.uk/plants/types/trees/cloud-pruning ; Promesse de fleurs, *Cloud pruning or niwaki* — https://www.promessedefleurs.ie/gardening-tips/advicesheet/cloud-pruning-or-niwaki/
27. Blender Extensions, *Sapling Tree Gen* — https://extensions.blender.org/add-ons/sapling-tree-gen/ ; *Modular Tree* — https://extensions.blender.org/add-ons/modular-tree/reviews/ ; fork — https://github.com/meet-brad-ch/add_curve_sapling
28. Epic, *Procedural Vegetation Editor in Unreal Engine* (5.8) — https://dev.epicgames.com/documentation/unreal-engine/procedural-vegetation-editor-in-unreal-engine?lang=en-US
29. CD Projekt Red / Epic, Witcher 4 UE5 tech demo — https://www.cdprojektred.com/en/blog/149/working-with-epic-to-debut-the-witcher-4-unreal-engine-5-tech-demo-at-unreal-fest ; talk listing — https://www.classcentral.com/course/youtube-large-scale-animated-foliage-in-the-witcher-4-unreal-engine-5-tech-demo-unreal-fest-stockholm-2025-505458
30. SpeedTree docs, *Real-Time Modeling* (tri budgets, draw calls, overdraw, atlases) — https://docs.speedtree.com/doku.php?id=real-time_modeling_tips
31. Polycount, *Making proper conifers with SpeedTree* — https://polycount.com/discussion/107617/making-proper-conifers-with-speedtree-default-textures-looks-terrible ; *Any SpeedTree gurus? Conifers* — https://polycount.com/discussion/228579/speedtree-any-speedtree-gurus-here-conifers [SECONDARY]
32. ArtStation, *Realistic game-ready pine tree models* — https://www.artstation.com/artwork/dyl1J3 [SECONDARY]
33. 80.lv, *Building Pine Flatwoods in UE4* — https://80.lv/articles/building-pine-flatwoods-in-ue4
34. Quixel, *Quixel on Fab: new Megascans and Megaplants* — https://quixel.com/news/quixel-on-fab-new-megascans-and-megaplants ; *Discover the latest Megascans and free Megaplants* — https://quixel.com/news/discover-the-latest-quixel-megascans-and-free-megaplants
35. Yarsa DevBlog, *Transferring normal data in Blender* — https://blog.yarsalabs.com/normal-transfer-in-blender/ ; UE forum, *Spherical normals for trees (Blender)* — https://forums.unrealengine.com/t/spherical-normals-for-trees-blender/98732
36. Epic community tutorial, *Shading Models Part 3 — Two Sided Foliage* — https://dev.epicgames.com/community/learning/tutorials/o8x/unreal-engine-shading-models-part-3-two-sided-foliage-using-two-sided-foliage-to-simulate-a-translucent-subsurface-effect ; 80.lv, *Getting the best of Megascans in UE4* — https://80.lv/articles/getting-the-best-of-megascans-in-ue4
37. UE forum, *Nanite displacement bugged in UE 5.8 but not 5.7* — https://forums.unrealengine.com/t/nanite-displacement-bugged-in-exact-same-landscape-in-ue-5-8-but-not-in-ue-5-7/2739815 [SECONDARY]
38. SpeedTree docs, *Thoughts from the developers* (leaf map maker, atlases) — https://docs.speedtree.com/doku.php?id=thoughts_from_the_developers ; *Leaf Map Maker* — https://docs.speedtree.com/doku.php?id=leaf_map_maker
39. SpeedTree (Unity docs), *Games wind* — https://docs.unity3d.com/speedtree-modeler/manual/wind-games.html ; *Wind Wizard* — https://docs.speedtree.com/doku.php?id=windwizard
40. Rockenbeck, *Blowing from the West: Simulating Wind in Ghost of Tsushima* (GDC 2021) — https://gdcvault.com/play/1027124/Blowing-from-the-West-Simulating ; https://www.gamedeveloper.com/design/using-vorticles-to-simulate-wind-in-i-ghost-of-tsushima-i-
41. 80.lv, *Impostor Baker for UE4* (Ryan Brucks, octahedral impostors, Fortnite) — https://80.lv/articles/impostor-baker-for-ue4

**Local (read-only) evidence:** `Documents/Unreal Projects/DemoGame_1/Content/Megaplant_Library/` (Tree_Ginkgo,
Tree_Japanese_Cypress: 109 files, names and sizes listed only), `C:/ProgramData/Epic/EpicGamesLauncher/VaultCache/
Megaplan*` (two packs), `WorkFiles/dojo/DOJO_QUEUE.md`, `WorkFiles/dojo/CINEMATIC_LOOK_RESEARCH.md` §2.9,
`References/Dojo/dojo_japanese_pine_ref.png` (colour measured with PIL on the bark and needle close-ups).
