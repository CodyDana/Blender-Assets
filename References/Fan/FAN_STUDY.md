# Folding Fan (Sensu) Asset Study

**Date:** 2026-09-26
**Status:** reference for modelling and rigging. Nothing built yet.

**Purpose.** Construction facts, build-to numbers and the rigging plan for `SK_Fan`, a black folding fan for the pack. It is a skeletal mesh whose ribs open and close in the engine. This job covers shape and mechanism only: no painting, no seal and no rib piercing. The ribs are solid, and the leaf and ribs are plain black.

**Flags** (as in `KUNAI_STUDY.md`):

- **SOURCED:** stated by a cited page.
- **DERIVED:** computed from sourced or measured figures. Arithmetic is in `WorkFiles/fan/study/fanstudy_*.py` and `.json`.
- **ESTIMATE:** a design choice.
- **SNIPPET:** a search-result summary only; the page was not fetched.

**Shape authority.** `REFERENCE_SPEC.md` (written in parallel from the pixels of fan2 and fan1) owns every shape number. This study cites its rows as "RS n". Where the two disagree, section 9 says so.

---

## 1. Summary

| Item | Value |
|---|---|
| Asset | `SK_Fan`: a skeletal mesh with 26 sticks (2 guards and 24 inner ribs), a rivet, and a pleated one-sided silk leaf of 25 pleats (50 faces). The tassel is a separate piece, `SK_Fan_Tassel` |
| Build-to headline | 210 mm closed. The pivot is 20 mm above the butt, so the ribs reach 190 mm (L). The fan opens 163.2° guard axis to guard axis. The leaf runs from 82 mm to 190 mm. About 20 g |
| Skeleton | 52 bones: `root` at the rivet, 26 `stick_NN` bones, and 25 `pleat_NN` bones, one per rib gap. Every vertex has **one** influence at weight 1.0 |
| Fold | Rigid-panel (isometric) pleats. Every leaf vertex lies on a fold line. The mid-gap folds are driven by pleat bones whose path the build script computes exactly |
| Corrective morphs | **None needed** (section 5.5) |
| Bind pose | The reference opening, which is also the shipped static open pose |
| Animations | `A_Fan_OpenClose`, `A_Fan_Openness` (for gameplay scrubbing) and `A_Fan_OpenPose` |
| Materials | Leaf, sticks and tassel are tint-ready through `M_Fabric_Master`. Default = the reference colour; the parameter means the part's mean colour. The rivet is plain metal |

Three findings shape the build:

1. **Rib-only skinning cannot fold the leaf.** With the mid-gap fold vertices split 50/50 between the two neighbouring rib bones, the pleat keeps its open depth at every angle. A face then loses 36 to 58 % of its width when the fan closes (section 5.3).
2. **Stacked sticks make pleat direction a design decision.** The sticks sit one behind another on the rivet, which the rig must copy. If every mid-gap fold points toward the viewer, as in fan2, the pleats next to the front guard pass through it at every opening below about 100° (section 5.4). No source covers this; the numbers come from this study's own geometry test.
3. **The closed leaf is wider than the guards.** Rigid faces of the reference's size fold into a bundle 11.5 to 23 mm wide at the tip, against a guard 8.9 mm wide. `REFERENCE_SPEC` section 10 proposes a closed width equal to the guard width, which is not physically possible (section 9).

---

## 2. The real sensu

### 2.1 Parts and terms

| Term | Meaning | Source |
|---|---|---|
| 扇骨 *senkotsu* | The whole rib frame. It divides into 親骨 and 中骨/仲骨 | [12][15] |
| 親骨 *oyabone* | The two outer guard sticks. They are thick, strong bamboo | [3][5][12] |
| 中骨 / 仲骨 *nakabone* | The inner ribs. They are thin, flexible bamboo | [3][5] |
| 間数 *kensū* (間 *ken/ma*) | The count of all sticks, guards included | [3][5][7] |
| 要 *kaname* | The pivot fastener that binds all sticks at one point. When it fails, the fan is unusable | [5][12][16] |
| 扇面 / 地紙 *senmen / jigami* | The leaf: paper or cloth mounted on the ribs | [5][9][15] |
| 山 / 谷 *yama / tani* | The mountain and valley folds of the leaf | [5] |
| ため *tame* | An inward bend heat-set into the guard tips, which keeps the closed fan shut | [5][11][12][14] |
| 房 *fusa* | A tassel on a cord threaded through the pivot. Originally functional, now ornamental | [5] |
| 短地 / 地長 | A short leaf with long bare ribs, or the ordinary long leaf | [12][18] |

Western terms: guards, sticks, ribs or slips (the part inside the leaf), gorge (the bare part between the head and the leaf), head (the pivot end) and rivet [21][22]. The brief's word "sagari" appears in none of the makers' glossaries read; they say 房 *fusa*.

### 2.2 Sizes and rib counts

One sun (寸) is about 3.03 cm [17]. Shops round it to 3 cm [1][2].

| Class | Closed length | Typical count | Status |
|---|---|---|---|
| Women's | 6.5 sun, 19.5 to 20 cm | 35 間 | SOURCED [1][3][4][7][17] |
| Unisex (the most popular size), also the silk and cloth fan size | 7 sun, 21 cm | 30 to 35 間; silk fan "7 sun 35 ken" | SOURCED [3][4][6][7][10] |
| Men's | 7.5 sun, 22 to 22.5 cm | 35 間; Edo fans 15 間; 45 間 short-leaf | SOURCED [1][3][7][26] |
| 8 sun | 24 cm | not given | SOURCED [2] |
| Men's large / persimmon | 8.5 sun, 25.5 to 26 cm | 16 間 | SOURCED [1][7][10] |
| Festival and decorative | 9 sun, 27 cm | 10 to 11 間 | SOURCED [2][3][7] |
| Count range | 8 to about 40 間; everyday 20 to 35 間; 25 to 35 間 "common" | | SOURCED [4][12][17] |

**Our fan.** The retail 21 cm black silk fans with tassel (the type in both photos) are 21 cm closed [27][28][29]. fan2 has 26 sticks (RS 3), fewer than the 35 間 of a Japanese 7-sun silk sensu [7], which fits its Chinese-market style. **Build 26**, as the photo shows.

### 2.3 Ribs and guards

| Fact | Source |
|---|---|
| Madake, hachiku or moso bamboo (also ivory or bone) | [14] |
| Bamboo aged 3 to 5 years | [11][15] |
| About 90 % of Japanese ribs come from Takashima, Shiga | [16] |
| Rib-making steps, in order: cut to size, split, boil, separate the springy outer skin (カワ) from the brittle inner layer, punch the rivet hole, sand hundreds together as a block, dry, polish, dye or lacquer | [8] |
| The rib ends that go into the leaf are shaved "paper-thin" (末削) | [8] |
| Guards take 18 process steps, inner ribs 16 | Takashima, SNIPPET |
| Guards are heated in a vise and bent inward (ため) | [14] |

**Dimensions: no primary source gives a Japanese sensu rib's width or thickness in millimetres.** The only figures found are for Chinese collector fans called 日式扇 ("Japanese-style"): 9 or 11 sticks, 31 to 32 cm long, main stick 10 to 12 mm at its widest and 7 mm at its narrowest [24]. They are a different, larger class. Rib widths therefore come from the photo (RS 4, RS 5) and thicknesses from the closed thickness of comparable fans (section 3).

### 2.4 The leaf and how it is mounted

**Paper (Kyoto).**
- The leaf is three sheets: a thin core paper (芯紙) between two skin papers (皮紙). Dance fans use 5 to 7 layers [9][11][15].
- The core is used because it splits easily. That lets the inner ribs be pushed between the layers [9].
- The damp leaf is folded between two templates cut for the rib count [9], one or two pleats at a time [11].
- A thin bamboo spill opens channels in the core [13][14][20]. Air is blown in to open them [11][13], and the glued, paper-thin ribs are slid in [13][19].
- The guards are glued on last and clamped with a ring (セメ) [13].

**Cloth (the reference type).**
- Cloth fans are almost always one-sided (片貼り): the ribs are glued to the back of the fabric, so they show from behind [6].
- Silk habotai runs 8 momme (sheer) to 16 momme (thick) [34]. One momme is about 4.34 g/m² [33], so 8 to 12 momme is **35 to 52 g/m²** (DERIVED).
- Thickness at 8 momme is about 0.05 mm (ESTIMATE; no source measures it).
- Many retail "silk" fans may be rayon or polyester. That is unverified, and it does not change the shape.

**Pleats.** Folds alternate mountain and valley, one pleat per rib gap [5][9]. On fan2 the rib folds are valleys and the mid-gap folds are mountains, seen from the front (RS 7). That fits ribs glued behind the fabric.

### 2.5 The rivet (kaname)

| Materials | Source |
|---|---|
| Metal, plastic, whale baleen, horn, tortoiseshell | [15][16] |
| Resin or metal, fitted as the last rib step (要打ち) | [8] |
| A metal fitting | [3] |

fan2 shows a polished metal eyelet with a hollow centre, 6.7 mm across (RS 6).

### 2.6 Tassel (房)

| Fact | Value | Source |
|---|---|---|
| How it attaches | The cord is threaded through the pivot | [5] |
| Sold fan tassel strap | 21 cm overall (10 cm tassel plus an 11 cm cord loop); tassel head 10 mm across | [31] |
| Tassel on a retail silk fan | 4.5 in (11.4 cm) | [28] |
| fan2 | Cord 0.19 L from the rivet to the knot, knot 0.047 L, skirt 0.373 L (71 mm), 0.63 L (120 mm) from the rivet to the tip; the cord runs through the hollow rivet | RS 8 |

### 2.7 Opening angle

- Sensu open between 90° and 180°. About 120° (a third of a circle) is "mainstream" [16][17][18].
- Retail listings give the open width. The DERIVED angle is 2·asin(W / 2R), with R = the closed length less a 20 mm butt. Results:
  - 139° for a 20.3 × 34.3 cm fan [28]
  - 144° for a 21 × 36.1 cm fan [25]
  - about 180° for 21 × 38 cm [27], 21.2 × 39 cm [29] and 22.5 × 41.5 cm [26]. The width there includes the guard edges.
- fan2 opens 163.2° guard axis to guard axis and 165.5° leaf corner to corner (RS 2). That is inside the real range, at its wide end.

### 2.8 Mass

| Fan | Mass | Source |
|---|---|---|
| 21 cm, paper, black bamboo | 20 g | [25] |
| 21.2 cm silk with tassel | under 24 g | [29] |
| 22.5 cm, 45 間, hardwood ribs | 35 g | [26] |

**Our build, DERIVED:**

| Part | Mass | Basis |
|---|---|---|
| Bamboo | 14.3 g | 22,000 mm³ at 0.65 g/cm³ (moso measures 0.65 to 0.71, madake 0.60 [35]). 24 inner sticks (bare part 6.7 × 0.85 × 102 mm, slip 2.3 × 0.38 × 100 mm), plus 2 guards (7.5 × 1.9 × 210 mm) |
| Silk | 1.6 to 2.3 g | 44,500 mm² at 35 to 52 g/m² |
| Rivet | about 0.3 g | ESTIMATE |
| Tassel | 2 to 4 g | ESTIMATE |
| **Total** | **18 to 21 g** | Matches the sourced 20 to 24 g |

**Build to 22 g** (physics mass 0.022 kg).

---

## 3. Build-to table

**Frame.**
- Origin at the rivet centre, on the mid-plane of the stick stack. Z is the rivet axis, +Z toward the viewer.
- Closed, the fan lies along +X, tip toward +X. This matches the kunai, and Blender +X arrives as Unreal +X [KUNAI_STUDY 5].
- The open pose sweeps through the XY plane.
- L = 190 mm, pivot to guard tip. That is DESIGNED in RS 0 and lands the common 21 cm size [4][27].

| Dimension | Build to | Basis | Status |
|---|---|---|---|
| Closed length, butt to tip | **210 mm** (1.106 L) | 7-sun silk fans are 21 cm [6][7][27][28][29] | SOURCED |
| Pivot above the butt | **20 mm** (0.106 L) | RS 4 butt lobe | DERIVED (pixels) |
| Stick count | **26 = 2 guards + 24 inner**, 25 gaps | RS 3 | DERIVED (pixels) |
| Opening, bind pose | **163.2°**, pitch **6.528°** | RS 2 | DERIVED (pixels) |
| Leaf inner radius | **82 mm** (0.431 L) | RS 7 | DERIVED (pixels) |
| Leaf outer radius | **190 mm**, flush with the guard tips | RS 7 | DERIVED (pixels) |
| Unfolded leaf angle Ψ | **173.6°**, so each of the 50 faces spans β = 3.472° | RS 7 | DERIVED |
| Pleat depth, open | **4.0 mm at the tip**, 1.7 mm at the leaf base | Rigid model: γ = acos(cos β / cos(α/2)) = 1.19°. Agrees with RS 7's 0.021 L | DERIVED |
| Face width at the tip | **11.5 mm**, the closed page width | 2·190·sin(β/2) | DERIVED |
| Inner rib, bare part | 7.8 mm wide at the leaf edge, tapering to 5.7 mm near the pivot; **0.85 mm** thick | RS 4 | DERIVED / ESTIMATE |
| Inner rib, inside the leaf | Not built as geometry. It shows only in the baked leaf maps (section 5.2) | This study | ESTIMATE |
| Guard | 6.5 to 8.9 mm wide (waisted, widest at the tip), **1.9 mm** thick | RS 5 | DERIVED / ESTIMATE |
| Stack at the rivet | 24 × 0.85 + 2 × 1.9 = **24.2 mm** | RS 4 | ESTIMATE |
| Closed thickness of comparable fans | 12.7 mm ("closed 8L × 0.5W in") | [28]; "8.3 × 1 × 0.5 in" folded, SNIPPET | SOURCED |
| Rivet | Eyelet 6.7 mm across, with a 3.2 mm hollow; a matching head on the back | RS 6 | DERIVED |
| Tassel | Section 2.6 | RS 8 | DERIVED |
| Mass | **22 g** | Section 2.8 | SOURCED range / DERIVED |

**Stack thickness disagrees.** RS's designed 24.2 mm stack is almost twice the 12.7 mm sourced for a comparable closed fan [28]. Inner ribs of 0.45 mm would match the source. Section 5.4 shows either value works for the fold, as long as every rib gap uses the same Z pitch. This is open question 2.

---

## 4. Pleat geometry (the part the rig must get right)

### 4.1 One rib gap, open

Take two neighbouring rib fold lines through the pivot, at ±α/2 about a middle direction m, with α the rib pitch. Each face is a flat sector of angle β. The mid-gap fold v is at angle β from both rib lines, so:

**v = cos γ · m + sin γ · n̂**, where **cos γ = cos β / cos(α/2)** and n̂ is the fan-plane normal.

- This needs α ≤ 2β. The leaf cannot open flatter than flat.
- The pleat depth at radius r is r·sin γ.
- At fan2's opening (α = 6.528°, β = 3.472°), γ = 1.19°. That gives **4.0 mm** of depth at the tip.
- Checked numerically: every face keeps its width to within 1e-12 mm at every angle (`fanstudy_kinematics.json`).

Faces are planar at every angle, because two lines through one point always share a plane. So:

- if every leaf vertex sits on a fold line,
- and each fold line moves rigidly with one bone,

then the leaf is **exactly isometric** under linear-blend skinning. No face stretches and nothing is interpolated.

### 4.2 Stacking and the two regimes

Real sticks are stacked on the rivet [23]. The rig must stack them too, or closed sticks would occupy the same space. So rib i lies in its own plane z_i, one pitch t behind the rib before it.

At radius r, the two ribs of a gap are then (rα, t) apart, measured along the arc and along Z. The mid-gap fold point lies at distance h = √((rβ)² − d²/4) from their midpoint, perpendicular to the line joining them (d = |(rα, t)|). As the fan closes:

1. **rα ≫ t.** The pleat points along ±Z, and its depth grows toward r·sin β (11.5 mm at the tip). The closing leaf becomes a stack of thin **fins**.
2. **rα ≲ t,** the last few degrees. The perpendicular turns toward the fan plane, so the pleats swing sideways and lie flat as **pages** between the ribs.

The closed leaf is therefore a stack of pages, each face r·β wide. At the tip that is **11.5 mm per side of the rib line**. The switch happens within the last 3 to 10° of total opening, depending on t and r (`fanstudy_kinematics.json`, `fanstudy_fold_xsec_spec.json`).

In the second regime the mid-gap fold is no longer an exactly straight line through the pivot:

- One rigid pleat bone per gap then carries a **residual of up to 0.25 mm** (worst at 4° open, with t = 0.45; `fanstudy_crease_line.json`).
- A **cone pitch** (Z spacing proportional to r) keeps it exact, but thickens the closed tip to 24 mm.
- Two pleat bones per gap (one inner, one outer) also remove it.

### 4.3 Real fans

Real fans get through the closing range by flexing:

- the ribs inside the leaf are paper-thin [8];
- silk and washi bend;
- the guards are heat-bent inward (ため) to press the bundle shut [5][14].

A rigid game rig must choose a fold direction per pleat that keeps the leaf out of the guards (section 5.4).

---

## 5. Rigging plan

### 5.1 Skeleton (52 bones, flat hierarchy)

| Bone | Count | Head, axis | Motion |
|---|---|---|---|
| `root` | 1 | Rivet centre, stack mid-plane. It is the armature object named `root` (the project's measured rule; any other object name adds a bone above it) [L1 §6.4, §7][54][55] | Static. Carries the rivet and head mesh |
| `stick_00` to `stick_25` | 26 | Pivot. The bone points along the stick. `stick_00` is the front guard (+Z side), `stick_25` the rear guard | Rotation about Z only. **In plane z_i at all times** (the rivet stack) |
| `pleat_00` to `pleat_24` | 25 | Pivot. The bone points along the mid-gap fold of gap i | A rigid transform per frame, computed by the build script (5.4). A small translation is allowed (the 0.25 mm residual fit) |

- All bones are direct children of `root`. There is no chain, so no error builds up.
- 52 bones is under the 75-per-section mobile cap and far under 65,536 elsewhere [40]. Every bone must keep Deform on, because `export_fbx` exports deform bones only [L2].
- There are no attach bones. Hand and tassel attach points are mesh sockets (5.9).

### 5.2 Skinning

Every vertex gets **one influence, weight 1.0**. That passes the pipeline's ≤ 4-influence and weight-sum gates [L1 §6.4].

| Vertices | Bone |
|---|---|
| Stick mesh (bare part and head) | Its `stick_NN` |
| Leaf vertices on rib fold i, including each guard's fold line | `stick_i` |
| Leaf vertices on mid-gap fold i | `pleat_i` |
| Rivet, both heads | `root` |

- **No leaf vertex may sit inside a face.** A vertex part-way across a face would need two bones, and blending two rigid transforms across a hinge that swings up to about 90° is wrong by millimetres. Radial rings only add vertices along the fold lines, plus the scalloped edge (RS 7).
- **Rib slips inside the leaf are not geometry.** A slip is a strip one face-width across, so it would need blending as above. Show them as a faint baked ridge in the leaf maps, front and back, as fan2 shows ribs through the silk.
- **The leaf's back** is a duplicate of the front faces with flipped normals, skinned identically. This avoids making `M_Fabric_Master` two-sided, which would change a frozen material.

### 5.3 Why not rib bones only, or morph targets

With rib bones only, the mid-gap fold vertices must be split 50/50 between the two rib bones. That blend:

- pulls the fold's radius in by cos(Δ/2), which is negligible;
- **keeps its Z depth fixed at the bind value.**

So a face that should be r·β wide when closed is only as wide as the open pleat depth.

| Ψ / Θ | Closed error | Error at half open |
|---|---|---|
| 1.10 | −58 % | −38 % |
| 1.20 | −45 % | −31 % |
| 1.30 | −36 % | −25 % |

At fan2's 1.064 the error is worse still (`fanstudy_kinematics.json`). The closed leaf would also sit as a single fin through the rib stack.

Corrective morph targets could patch this, but only badly:

- Unreal applies morphs before skinning, in the reference pose, with linear weights. The pleat path is non-linear and swings about 90° in the closing range, so it would need several in-between targets driven by curves.
- Morphs need Import Morph Targets, Apply Modifiers off in Blender [L1 §7], a "Used with Morph Targets" material usage flag, and remapping per LOD [41].
- Unreal's own morph docs call the effect "often subtle" [45]. They are built for small corrections, not a quarter-turn fold.

Pleat bones give an exact answer at 25 extra bones.

**Shipped game fans.** A sold game fan has 1.3k triangles, 806 vertices, and open and close animations [36]. **No source found says how any shipped game fan skins its pleats.**

### 5.4 Pleat bone path and fold direction

**The build script computes, for every keyed frame:**

1. The rib angles: φ_i = φ₀ + i·Θ/25. The held guard stays fixed (see 5.9); the rest spread from it.
2. The rib fold points at z_i. **Use one Z pitch for every gap, including the two guard gaps.** Unequal pitch makes neighbouring pleats swing between fins and pages at different moments, and they then cross. That was measured: an earlier test with half a pitch at the guard crossed 6 to 22 segments between 4° and 15°.
3. The mid-gap fold point for each gap at each ring radius, by the construction in 4.2, on the chosen side.
4. Each `pleat_i` transform as the least-squares rigid fit (Kabsch) from its bind fold points to these points. Log the residual; the gate is ≤ 0.1 mm.
5. If a gap exceeds the gate, split it into two pleat bones, or use the cone pitch.

**The side each pleat pops to** decides whether the leaf passes through a guard. It was measured in a cross-section test (`fanstudy_fold_hybrid.py`):

- inputs: RS values Θ = 163.2°, Ψ = 173.6°, rib 0.85 mm, guard 1.9 × 8.9 mm;
- 29 opening angles from 163.2° down to 0.02°, at radii 82, 110, 150 and 190 mm.

| Fold direction | Crossings / guard hits | Leaf beyond the stack faces | Open look vs fan2 |
|---|---|---|---|
| All mid-gap folds toward the viewer (fan2) | **60 failing cases**, from 100° open down: the pleats next to the front guard pass into it | 8.8 mm | Exact |
| As fan2, but the gap next to the front guard folds backward | 47 failing cases, from 60° down | 7.9 mm | 1 pleat differs |
| As fan2, the 2 gaps next to the front guard fold backward | 20 failing cases, from 25° down | 7.1 mm | 2 pleats differ |
| **As fan2, the 3 gaps next to the front guard fold backward** | **0** | 6.2 mm, at mid-closing angles, clear of the guards | 3 of 25 pleats differ, at the front-guard end |
| Front half backward, rear half toward the viewer ("converging") | **0** | **0** | 12 of 25 pleats differ |

**Recommendation.** Prototype "3 gaps backward" first. It is the smallest change from fan2 that passes, and its three reversed pleats sit beside the front guard, where the eye reads the guard.

**The builder must confirm by looking at it.** Compare the open render with fan2. If the reversed pleats read wrong, use "converging", or ask the user to accept a flex correction.

**The test is 2-D, at four radii.** The full 3-D gates in 5.10 decide.

**Fully closed.**
- Exactly 0° is singular: the side a pleat falls to is undefined there.
- Close to **0.05°**, or keep the last side by continuity.
- The closed leaf is **23 mm wide at the tip** (11.5 mm each side), 9.9 mm at the leaf base. That is wider than the 8.9 mm guard (section 9).

### 5.5 Morph targets

**None.** The rig is exact wherever each mid-gap fold stays a straight line (all of the opening except the pages regime), and within the 0.1 mm gate there. Reopen this only if the 3-D gates fail and more pleat bones cannot fix them.

### 5.6 Animation

| Asset | Content | Rate |
|---|---|---|
| `A_Fan_OpenPose` | One frame at 163.2°, equal to the bind pose. The static open pose | – |
| `A_Fan_OpenClose` | Closed (0.05°) to open to closed. Ease in and out, 0.5 s each way, 0.3 s hold (ESTIMATE; no source times a hand opening a fan) | 30 fps, keyed every frame |
| `A_Fan_Openness` | Linear in the opening angle, closed to open, so gameplay can scrub it with a Sequence Evaluator at explicit time = openness × length [48] | Import at 60 to 120 fps via Custom Sample Rate [38] |

- **Why the openness sequence needs dense keys.** Stick angles interpolate exactly between keys, because they are rotations about one axis. Pleat bones follow a non-linear path, so the rig is only exact on a key. Measure the error at half-key times; gate ≤ 0.1 mm and no intersections. Raise the rate until it passes.
- **Bind pose = open (163.2°).** Import with Use T0 As Ref Pose **off**, because the animations start closed [38]. The physics asset and bounds are then built on the open fan.
- **Compression.** ACL is the default codec since UE 5.3 [49][50]. Its default virtual-vertex distance of 3 cm suits characters, and its error threshold is 0.01 cm [49]. The fan reaches 19 cm, so give the fan's sequences their own compression settings with a virtual-vertex distance of about 19 cm. Check that pleat error after compression stays under the 0.85 mm Z pitch.
- **Blender 5.2** actions are layered: fcurves live under `action.layers[].strips[].channelbags[]` [L1 §8]. Export one action per animation FBX [L1 §7].

### 5.7 Physics asset (held prop)

- **The bounds come from the physics asset.** A skeletal mesh takes its bounds from the bodies marked Consider for Bounds [44][57]. A single body at the rivet would cull or shadow-pop the open fan. So:

| Body | Shape | Role |
|---|---|---|
| `root` | Box around the closed stack and head | Collision. **Kinematic** while held; the only body allowed to simulate when the fan is dropped |
| `stick_00`, `stick_25`, `stick_12` | Thin boxes | Consider for Bounds **on**, collision **off**, **Kinematic** |

  These give bounds for the open fan: both guards and the leaf top. The fallback is SkeletalMesh `positive_bounds_extension` [52].
- **Mass:** 0.022 kg on `root` [44].
- **Physics type:** Kinematic is "not affected by physics, but can interact with physically simulated bodies" [44].
- Do not keep the importer's auto physics asset. It builds spheres per bone around a root capsule [38], which here would mean 52 bodies. Write the physics asset from the build script. Fab requires one [L1 §7].

### 5.8 Tassel: a separate bone chain

**`SK_Fan_Tassel`** is its own skeletal mesh and skeleton:

- bones `tassel_root` (at the rivet, back face), `cord_01`, `cord_02`, `knot`, `skirt_01`, `skirt_02`;
- cord and skirt vertices on at most 2 influences;
- attached to the `Tassel` socket of `SK_Fan`.

**Why a chain.** It must **hang from the pivot under gravity** (RS 8 records that the photo is a flat-lay). A rigid static mesh points wherever the fan points, so it would stick out sideways whenever the fan tilts to fan the face.

**How it moves.** AnimDynamics in a small AnimBP is the light option: a Chain with Bound Bone and Chain End, and no physics asset [46]. The Rigid Body node with a capsule physics asset is the richer option [47].

**Optional.** `SK_Fan` has no tassel geometry, so leaving the tassel off leaves nothing behind. For the fan2 comparison render, pose it along −160° (RS 8).

### 5.9 Sockets and grip

Unreal sockets live on the Skeleton or on the mesh (Mesh Sockets) and hold a transform relative to their bone [42]. **The pipeline's socket sidecar is static-mesh only.** Create the fan's sockets from a sidecar through a **new** function, and verify them in a fresh process (the transient-socket trap [L1 §6.5]).

| Socket | Bone | Place | Use |
|---|---|---|---|
| `Grip` | `stick_00` (the held guard) | 40 mm above the butt on the guard's axis; +X along the stick, +Z out of the front | Hand attach (ESTIMATE; a sensu is held at the kaname end) |
| `Pivot` | `root` | Rivet | Spin and aim reference |
| `Tassel` | `root` | Back rivet head | Tassel attach |
| `Tip` | `stick_12` | Leaf edge, mid-fan | Trail or gust effects |

**Which guard the hand holds.** One guard stays fixed in the hand while the others sweep open. That puts the open fan to one side of the grip, not symmetric about +X. No source says which guard a user holds (open question 4).

### 5.10 Verification gates (on the shipped FBX, re-imported)

Every build re-imports the exported FBX into a fresh Blender and poses it from its own baked actions:

- at 0.05°, 0.1°, 0.2°, 0.5°, then 1° to 10° in steps of 1°, then 12° to 163.2° in steps of 2°;
- at every half-key time.

It measures:

| Gate | Test |
|---|---|
| G1 isometry | Every leaf edge length within 0.1 mm of its bind length |
| G2 intersections | No triangle overlap: leaf against itself (non-neighbouring faces), leaf against sticks, leaf against guards, stick against stick (BVH overlap) |
| G3 containment | Leaf never inside a guard's volume; the bulge beyond the stack faces is logged (6.2 mm expected) |
| G4 weights | One influence per vertex; 52 bones; `root` at the origin |
| G5 look | Render the open pose with RS 1's camera, compare side by side with fan2 and by silhouette, and check the RS rows. It must **look** the same |
| G6 Unreal, fresh process | Bone count; reference pose equal to Blender (≤ 1e-4 cm per bone, the garment check [L1 §6.5]); sequence lengths; sockets; bodies with Consider for Bounds; LOD count and screen sizes; slots bound. Offscreen renders at 0°, 10°, 30°, 90° and 163° |

### 5.11 LODs

**Every fold stays at every LOD.** The fold count is what folds the leaf:

- A face spanning a whole gap cannot fold. It shrinks to zero width as the ribs meet, while the true closed leaf is 23 mm wide. At a distance the closed silhouette would jump at each LOD switch.
- Do not use Bones to Remove. Unreal takes the listed bones out per LOD [41], and the builder must assume that a removed pleat bone's vertices fall back to `root` (unverified), which would freeze the leaf.

| LOD | Screen size | Triangles | What changes |
|---|---|---|---|
| LOD0 | 1.0 | 1,600 to 2,200 | Leaf: 50 faces × 5 rings × 2 sides; rounded stick edges; 16-sided rivet; butts rounded in 6 segments |
| LOD1 | **0.43** | 800 to 1,100 | Leaf 2 rings; sticks as boxes; 8-sided rivet |
| LOD2 | **0.15** | 350 to 500 | Leaf 1 ring (every fold kept, scallop dropped); inner sticks as two-sided quads; guards as boxes |

- **Screen sizes.** The pack's 1.0 / 0.10 / 0.035, scaled by the bounds radius: about 215 mm for the open box against 50 mm, through `props_lib.spec.scaled_lod_screen_sizes` (DERIVED). Apply them after import; FBX carries none [L2].
- **Budget.** The project's prop budget is 1,000 to 5,000 triangles [L1].
- **Importing the LODs.** Separate LOD FBX files through `SkeletalMeshEditorSubsystem.import_lod` [51]. Each must have the same root bone, or Unreal refuses it [39]. Whether an FBX LodGroup imports for skeletal meshes is untested here.

### 5.12 Materials (Integrate phase)

| Slot | Master | Instance | Default colour (= the part's mean colour, RS 9) |
|---|---|---|---|
| Leaf (front and back) | `M_Fabric_Master` | `MI_Fan_Leaf` (+ `_Base`) | `#272B30` |
| Sticks (ribs, guards, head) | `M_Fabric_Master` | `MI_Fan_Sticks` | `#212628` (the guards match the ribs within error, RS 9) |
| Rivet | `M_Steel_Master` | `MI_Fan_Rivet`, not tintable (like the shuriken) | Polished silver |
| Tassel | `M_Fabric_Master` | `MI_Fan_Tassel` | `#14181F`. This is at the pack's black floor (`#191919` lift), so check that the default is not lifted |

**Maps and constants.** Follow the pack's recolour chain [L3]:

- `Textures/Recolour/T_Fan_*_Detail16` (full-range, 16-bit, linear, G16);
- `recolour_maps.json` and `recolour_constants.json`;
- default = the shipped look to 1 to 3 levels;
- mip-safe mean through `MF_TintDetail`.

**Leaf texel density.** One 2048 map for about 445 cm² at roughly 70 % packing gives about 80 px/cm. That is below the 134 to 170 px/cm the small items reach [KUNAI_STUDY], deliberately: the leaf is large and plain, and its pleats are geometry. The front and back can share UVs.

**Usage flag (decision needed).** The masters have "Used With Instanced Static Meshes" but not "Used with Skeletal Mesh". That flag compiles the skeletal shader permutations [53]. Setting it edits the frozen masters, adding permutations but changing no parameter or default. **The user must approve it.** The alternative is a duplicate master for skeletal use, which splits the pack.

### 5.13 Unreal import (5.8)

| Setting | Value | Why |
|---|---|---|
| Importer | The measured skeletal path: Interchange with a duplicated `DefaultFBXOBJAssetsPipeline`, **Recompute Normals OFF** | Verified on garments; Recompute ON rewrites normals by about 7° and welds hard edges [L1 §6.5] |
| Skeleton | None: make `SK_Fan_Skeleton`. Animations then target it with Import Mesh off | [38][55] |
| Use T0 As Ref Pose / Update Skeleton Reference Pose | **Off / off** | The bind pose is the open pose [38] |
| Import Morph Targets | Off | There are no morphs |
| Create Physics Asset | Off; the build writes it | 5.7 |
| Normals | Import Normals, MikkTSpace tangents; Preserve Smoothing Groups on | [38][L1] |
| Convert Scene / Unit, Force Front X | On, on / off | [L1 §6.5] |
| Animation Length / sample rate | Exported Time; Use Default Sample Rate off, Custom Sample Rate = the file's rate (the default is 30 fps) | [38] |
| Blender side | Armature object `root`; Add Leaf Bones off; Deform-only on; primary / secondary bone axes Y / X | [L2][55] |

**Known pitfalls:**

1. **An extra root bone.** Unreal strips only an armature exactly named "armature" [54]. The project's rule is an object named `root`.
2. **One animation per FBX** [37].
3. **An LOD whose root bone differs is refused** [39].
4. **The bounds come from the physics asset** (5.7).
5. **A pleat bone dropped by Bones to Remove** freezes its fold (5.11).
6. **ACL tuned for characters** (5.6).
7. **Unsaved usage flags** (5.12).
8. **In-process reads prove nothing.** Assert saved state in a fresh commandlet [L1 §6.5].
9. **Interchange** ignores `destination_name` and creates extra assets [L1 §6.5].

**Pipeline.** `export_fbx(kind="skeletal")` and `kind="animation"` already exist with deform-only, no leaf bones and baked single actions [L2]. Add skeletal sockets, the physics asset writer and skeletal LOD import as **new** functions or a new module, and re-run `test_pipeline.py` and `test_qa_negative.py`.

---

## 6. fan1 vs fan2

This table is from RS 11. **fan2 is followed everywhere.**

| Feature | fan1 | fan2 (built) |
|---|---|---|
| Sticks | 30 (28 + 2) | 26 (24 + 2) |
| Opening | 143° | 163° |
| Leaf inner radius | 0.462 L | 0.431 L |
| Butt lobe | 0.08 to 0.09 L | 0.106 L |
| Rivet | Solid dome, 0.022 L | Eyelet, 0.035 L |
| Guard tip | Rounded | Square-cut, soft corners |
| Tassel | None | Cord, knot and skirt |
| Design (not modelled) | Sakura, cats, seal; pierced ribs | Willow, swirls, seal; openwork ribs |

This study's own quick count on the same pixels agreed: about 26 sticks in fan2 and about 33 in fan1 (the gorge periodicity in `fanstudy_period.py`, a rougher method than RS's four-way count). Openings came out 166° for fan2 and 145° for fan1, uncorrected for perspective. The pivot came out 20 mm above the butt.

---

## 7. Open questions

1. **Fold direction next to the front guard.** Which do we ship: "3 gaps backward" (3 of 25 pleats differ from fan2), "converging" (12 differ), or all folds as fan2 plus a flex correction the builder must bound? Decide on renders.
2. **Z pitch.** RS designs 0.85 mm inner ribs, a 24 mm stack. Comparable fans close at 12.7 mm [28], which means 0.45 mm ribs. Either works if every gap uses the same pitch.
3. **Closed width.** The closed leaf is 23 mm wide at the tip with the fold rule above, or 11.5 mm with all folds as fan2. The guard is 8.9 mm. Show the closed bundle wider than the guards, as rigid faces require, or change the unfolded leaf angle (which would change the open look)?
4. **Held guard** for the `Grip` socket, and a one-sided opening versus a symmetric one.
5. **Material usage flag** on the frozen masters (5.12).
6. **The real mass** of a fan2-class fan: 20 to 24 g is sourced for similar fans, not this one.
7. **Rib dimensions.** No source gives sensu rib widths or thicknesses in mm; they come from the photo and the closed thickness.

---

## 8. Verification of high-stakes claims

Checked 2026-09-26 by WebFetch and WebSearch. Nothing was downloaded.

| Claim | Status | Checked against |
|---|---|---|
| Size classes 6.5 / 7 / 7.5 / 8 / 8.5 / 9 sun = 19.5 / 21 / 22.5 / 24 / 25.5 / 27 cm | **Verified** | [1][2][3][4][7][10] |
| 間数 counts guards plus inner ribs; 8 to about 40; 20 to 35 everyday | **Verified** | [3][4][5][12][17] |
| Kyoto leaf is 3 layers with a splittable core; ribs are slid into air-opened channels | **Verified** | [9][11][13][14][19][20] |
| Cloth fans are one-sided, with the ribs visible behind | **Verified** | [6] |
| Rib leaf ends are shaved paper-thin; rivet of resin or metal | **Verified** | [8] |
| Guards heat-bent inward (ため) | **Verified** | [5][11][14] |
| Opening 90 to 180°, about 120° mainstream | **Verified** | [16][17][18] |
| 20 g (21 cm), under 24 g (21.2 cm silk), 35 g (22.5 cm) | **Verified** | [25][26][29] |
| Closed thickness 0.5 in | **Verified** for one listing [28]; the "8.3 × 1 × 0.5 in" figure is a SNIPPET | [28] |
| Tassel 10 to 11.4 cm; cord threaded through the pivot | **Verified** | [5][28][31] |
| Sensu rib width and thickness in mm | **Not found** | Only Chinese 日式扇 collector figures [24] |
| How shipped game fans skin their pleats | **Not found** | [36] lists only its triangle count and animations |
| Rib-only skinning compresses faces 36 to 58 % | **DERIVED** | `fanstudy_kinematics.py` |
| Fold direction and guard penetration | **DERIVED, 2-D test** | `fanstudy_fold_hybrid.py`. The builder's 3-D gates must confirm it |
| The skeletal mesh bounds come from the physics asset | **Verified** | [44] ("considered for the bounding box of the PhysicsAsset (and hence SkeletalMeshComponent)"); [57] SNIPPET |
| Bones per section: 65,536, mobile 75 | **Verified** | [40] |
| Removed-LOD-bone vertices fall back to the parent bone | **Unverified** | The builder must test it before any Bones to Remove use |
| Unreal strips only an "armature"-named extra root | **Verified** for UE4 [54]; the project's `root` rule is measured on 5.8 [L1] | |

---

## 9. Where this study disagrees with REFERENCE_SPEC

| RS row | RS says | This study | Consequence |
|---|---|---|---|
| RS 10, closed state | "The closed width is the guard width (0.047 L)" | Rigid faces fold into pages 11.5 mm wide at the tip, so the bundle is 11.5 to 23 mm wide against the 8.9 mm guard | The closed leaf shows beside the guards, as it does on real fans. It must still never pass **through** them (gate G3) |
| RS 7, "the two end faces are glued to the guards" | Full-face glue | A face glued along its width cannot keep its shape as the gap changes. Attach the leaf to each guard **along one fold line**, the guard's inner edge | Keeps both faces of the guard gaps rigid |
| RS 4, 0.85 mm inner rib | 24.2 mm stack | The sourced closed thickness of comparable fans is 12.7 mm [28] | Open question 2 |

---

## 10. Sources

**Makers and shops (Japan)**

- [1] Hakuchikudo, fan types and sizes: https://hakuchikudo.jp/pages/classification
- [2] Hakuchikudo FAQ, decorative sizes: https://www.hakuchikudo.co.jp/faq/110
- [3] SP no Oroshi, sizes and bones: https://www.spgoods-oroshi.com/communication/article/?p=420
- [4] Wa no Oroshi, sizes: https://www.sp-oroshi.com/sensu/other/size.html
- [5] Wa no Oroshi, part names: https://www.sp-oroshi.com/sensu/other/parts.html
- [6] Wa no Oroshi, cloth fans: https://www.sp-oroshi.com/sensu/cloth/
- [7] Ibasen, fan sizes: https://www.ibasen.co.jp/en/pages/fan-size
- [8] Maisendo, rib making: https://www.maisendo.co.jp/seizou01.html
- [9] Maisendo, leaf making: https://www.maisendo.co.jp/seizou02.html
- [10] Maisendo, paper fan sizes: https://www.maisendo.co.jp/original/sensu/kami/size/
- [11] Hakuchikudo, manufacturing flow: https://www.hakuchikudo.co.jp/about/flow
- [12] Hakuchikudo, parts and terms: https://hakuchikudo.jp/pages/parts-terms
- [13] Yonehara Yasuhito, Kyoto fan making part 2: https://kinsaisensu.com/blog/2297/
- [14] Aoyama Square, Kyo sensu: https://kougeihin.jp/en/craft/1411/
- [15] Matsui Hiroshi, Edo sensu structure: https://edo-sensu.com/spn/sensu_struct.html
- [16] Japanese Wikipedia, 扇子: https://ja.wikipedia.org/wiki/扇子
- [17] Novelty Lab, sensu basics: https://www.shop-stationery.com/labo/item/9999/
- [18] Sensu Daiko, basics: https://sensu-daiko.com/cont/basic.html
- [19] Inokuchi Shojudo, how Kyoto fans are made: https://www.kyosensu.com/kyosensugadekirumade
- [20] Taniguchi Matsuodo, fan process: https://www.taniguchi.co.jp/feature/2022/11/fan-process.html

**Fan glossaries and conservation**

- [21] The Fan Circle International, parts of a folding fan: https://fancircleinternational.org/parts-of-a-folding-fan/
- [22] Geri Walton, fan glossary: https://www.geriwalton.com/glossary-for-fans/
- [23] AIC Book and Paper Annual, "Design and Construction of a Support for a Folding Fan" (sticks stacked on the rivet at the head): https://cool.culturalheritage.org/coolaic/sg/bpg/annual/v05/bp05-04.html
- [24] cngold, rib classes (日式扇 figures): https://cang.cngold.org/sczs/c5471422.html

**Product listings**

- [25] BECOS, 21 cm black-bamboo fan, 20 g: https://en.thebecos.com/products/s0125-014
- [26] BECOS, 7.5-sun 45-ken fan, 35 g, 41.5 cm open: https://www.thebecos.com/products/s0125-030
- [27] Healing Sounds, 21 cm black silk fan, 38 cm open: https://healing-sounds.com/products/black-bamboo-leaf-21cm-folding-silk-fan
- [28] Wrapables, silk fan with tassel, closed 8 × 0.5 in, tassel 4.5 in: https://wrapables.com/products/wrapables-silk-handheld-folding-fan-with-tassel-and-protective-sleeve
- [29] Getmyfan, 21.2 cm silk fan, 39 cm, under 24 g: https://www.getmyfan.com/products/premium-silk-border-hand-fan-7-colours
- [31] Creema, fan tassel strap: https://www.creema.jp/item/12412696/detail
- [32] Oriental Artisan, 21 cm silk fan, 35 cm spread: https://oriental-artisan.com/products/handcrafted-high-end-silk-vein-leaf-folding-fan

**Materials**

- [33] George Weil, habotai (1 momme ≈ 4.34 g/m²): https://www.georgeweil.com/habotai-8mm-silk-fabric-undyed/
- [34] Wikipedia, Habutai: https://en.wikipedia.org/wiki/Habutai
- [35] "Densification of Bamboo: State of the Art" (natural densities): https://pmc.ncbi.nlm.nih.gov/articles/PMC7578950/

**Game assets**

- [36] Sketchfab, Handheld Foldable Fan Animated (1.3k tris): https://sketchfab.com/3d-models/handheld-foldable-fan-animated-43a3d5eeeb4145d5b80e39599de0e321

**Unreal Engine**

- [37] FBX Skeletal Mesh Pipeline: https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-skeletal-mesh-pipeline-in-unreal-engine
- [38] FBX Import Options Reference: https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-import-options-reference-in-unreal-engine
- [39] FBX Import Errors: https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-import-errors-in-unreal-engine
- [40] Skeletal Mesh Rendering Paths: https://dev.epicgames.com/documentation/en-us/unreal-engine/skeletal-mesh-rendering-paths-in-unreal-engine
- [41] Skeletal Mesh LODs: https://dev.epicgames.com/documentation/en-us/unreal-engine/skeletal-mesh-lods-in-unreal-engine
- [42] Skeletal Mesh Sockets: https://dev.epicgames.com/documentation/en-us/unreal-engine/skeletal-mesh-sockets-in-unreal-engine
- [43] Physics Asset Editor: https://dev.epicgames.com/documentation/en-us/unreal-engine/physics-asset-editor-in-unreal-engine
- [44] Physics Bodies Reference: https://dev.epicgames.com/documentation/en-us/unreal-engine/physics-bodies-reference-for-unreal-engine
- [45] FBX Morph Target Pipeline: https://dev.epicgames.com/documentation/unreal-engine/fbx-morph-target-pipeline-in-unreal-engine
- [46] AnimDynamics (SNIPPET): https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-blueprint-animdynamics-in-unreal-engine
- [47] Rigid Body node (SNIPPET): https://dev.epicgames.com/documentation/unreal-engine/animation-blueprint-rigid-body-in-unreal-engine
- [48] AnimNode_SequenceEvaluator, Python API (SNIPPET): https://docs.unrealengine.com/5.3/en-US/PythonAPI/class/AnimNode_SequenceEvaluator.html
- [49] Animation Compression Library: https://dev.epicgames.com/documentation/unreal-engine/animation-compression-library-in-unreal-engine?lang=en-US
- [50] N. Frechette, ACL in UE 5.3 (SNIPPET): https://nfrechette.github.io/2023/09/17/acl_in_ue/
- [51] SkeletalMeshEditorSubsystem, Python API (SNIPPET): https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/SkeletalMeshEditorSubsystem?application_version=5.5
- [52] SkeletalMesh, Python API, bounds extensions (SNIPPET): https://docs.unrealengine.com/5.3/en-US/PythonAPI/class/SkeletalMesh.html
- [53] UMaterial::bUsedWithSkeletalMesh (SNIPPET): https://docs.unrealengine.com/4.26/en-US/API/Runtime/Engine/Materials/UMaterial/bUsedWithSkeletalMesh/
- [54] Epic forum, extra root bone fix works only for "armature": https://forums.unrealengine.com/t/blender-specific-skeleton-extra-root-bone-fix-only-works-if-root-object-is-named-armature/393432
- [55] Cinevva, Blender-to-Unreal export checklist: https://app.cinevva.com/guides/blender-to-unreal-export-checklist
- [56] Send to Unreal, skeletal meshes: https://joshquake.github.io/BlenderTools/send2ue/asset-types/skeletal-mesh.html
- [57] Physics Asset Editor, UE 4.27 (SNIPPET: "will use the Physics Asset for calculating its bounds"): https://docs.unrealengine.com/4.26/en-US/InteractiveExperiences/Physics/PhysicsAssetEditor

**Local**

- [L1] `ASSET_GUIDELINES.md` §6.4, §6.5, §7, §8.
- [L2] `Scripts/pipeline/export_fbx.py`.
- [L3] `WorkFiles/materials/MATERIALS_REPORT.md`, with `Exports/SmokeBomb/Textures/Recolour/recolour_maps.json` as the format example.
- [KUNAI_STUDY] `References/Kunai/KUNAI_STUDY.md`.
- RS: `References/Fan/REFERENCE_SPEC.md`.

**Study arithmetic (`WorkFiles/fan/study/`)**

- `fanstudy_kinematics.py/.json`: pleat model, rib-only skinning error, mass.
- `fanstudy_fold_xsec*.py/.json` and `fanstudy_fold_hybrid.py/.json`: fold-direction test.
- `fanstudy_crease_line.py/.json`: straightness of the mid-gap fold.
- `fanstudy_period.py`, `fanstudy_polar.py`, `fanstudy_strip.py`: the quick stick count.
