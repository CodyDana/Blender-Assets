# Snow Flower Sheath Study

**Date:** 2026-09-26
**Status:** reference for modelling. No asset was built for this study.

**Purpose.** This study gives build-to numbers, construction and game setup for a new scabbard that matches the Snow Flower sword. The design follows `SnowFlower_sheath_reference.png`: a straight black-grey marbled lacquer body, a raised silver vine with five-petal blossoms, a leaf-plate throat, one mid band and a pointed chape. It has **no tassel and no cord**. The same decision applies to the sword: its revision-3 tassel is removed (section 6).

**Flags.** Same as `KUNAI_STUDY.md`:
- **SOURCED:** measured, with a URL [n] or a project file [Pn].
- **DERIVED:** computed from sourced figures.
- **ESTIMATE:** a design choice.
- **SNIPPET:** a search-engine summary only; the page itself could not be read.

**Companion arithmetic.** `WorkFiles/SnowFlower/v4/study_calc/`:
- `measure_r3_blade_profile.py`: headless and read-only on the master.
- `measure_sheath_reference_rows.py`
- `sheath_fit_calc.py` and its output `.txt`: section 4. Uses system Python and the standard library only.

---

## 1. Summary

| Item | Value |
|---|---|
| Asset | `SM_SnowFlower_Sheath`, a separate static mesh from `SM_SnowFlower` |
| Form | Straight scabbard: throat of pointed leaf plates around a blossom, one belt band with a blossom, raised silver vine with blossom clusters, pointed chape with a blossom and leaf plates |
| Build-to headline | **1,015 mm** from mouth to point, body **66.5 mm** wide under the throat tapering to **about 53 mm**, **24 to 20 mm** thick, throat **102 mm** at its widest, **0.5 to 0.9 kg** (0.7 kg for physics) |
| Scale basis | 0.70 mm per reference pixel. At this scale the r3 blade tip sits inside the chape's widest point (section 4) |
| Main conflict | The reference body tapers 27%. The r3 blade stays 44 to 46 mm wide until 85% of its length, then its spine sweeps out to +30.5 mm. **No straight, symmetric outline at the reference taper can hold that blade coaxially.** Recommended fix: widen the lower body by up to 2 mm per side and sit the blade 6.2 mm off the sheath axis. Re-run the fit on the v4 blade |
| Game setup | Sheath actor snapped to a hip socket on the character. Sword actor snapped to the sheath's `Holster` socket. Blade stays inside the sheath, not hidden, and a containment gate proves it never shows |
| Budget | LOD0 10 to 16k triangles; one 4096 BC/ORM/N set; two slots (`Lacquer`, `Silver`) |
| Tassel | None on the sheath. Remove it from the sword (section 6 confirms, with caveats) |
| IP | The sword sheet is titled after a webtoon protagonist. The user decides before any Fab use (section 7) |

The build rests on three facts:
1. The sheath is sized by the blade it must hide, not by the picture alone. The picture sets the look; the blade sets the minimum widths.
2. The sheath reference shows only the front. The back face, the thickness and the section are estimates.
3. Real scabbards are wood cores with metal fittings. That fixes the construction logic, but the game only needs a closed shell that the blade never pierces.

---

## 2. Real scabbards, briefly

### 2.1 Japanese saya

- **Wood.** The saya is two halves of honoki (*Magnolia obovata*), hollowed to the blade's exact shape and glued back together with rice-paste glue (sokui) [1][2]. The wood is dried for 1 to 10 years, and at least 1 year [4].
- **Density.** Honoki air-dry density is **0.40 to 0.49 to 0.61** (low, mean, high), light and soft. It is listed for use in blade scabbards [3][35].
- **Fit.** The cavity is fitted by repeated trials. Too much gap lets the blade move; too little stops it from drawing [1]. The edge must never touch the inside, and the koiguchi grips the habaki so the blade does not rattle [1][2].
- **Fittings** [2]:
  - The **koiguchi** (mouth) is traditionally buffalo horn, glued into the rim.
  - The **kurikata** is a knob for the sageo cord.
  - The **kojiri** (end) is horn or metal.
- **Size.** A saya is about **2.5 to 5 cm** longer than the blade, to protect the tip [7] (SNIPPET).
- **Horn koiguchi dimensions:**
  - About **40 x 24 x 10 mm** [5] (SOURCED).
  - A kit piece of **44 x 26 x 8 mm** with a **36 x 16 mm** slot [6] (SNIPPET).
  - The kit implies walls of about **4 mm** across the width and **5 mm** across the thickness at the mouth (DERIVED).
- **How it is worn:**
  - The katana goes through the obi, edge up [2], on the left hip, at about **45°** [18] (a weak retail source).
  - The tachi hangs edge down from two hangers (ashi), "in a horizontal position" [17].

### 2.2 Chinese dao scabbards

This is the closer relative. The r3 blade is straight until about 85% of its length and then sweeps up to the point. That is the **yanmaodao** profile: "a straight or very nearly straight blade that sweeps up gently from around the last quarter of the blade length" [10]. The scabbard:
- **Core:** two wooden halves covered with leather, ray skin or lacquer; lacquer is usually solid black or chestnut-brown [8][9].
- **Fittings:** a mouthpiece, two suspension bands, a suspension bar joining them, and a chape [8]. The sources read do not say how the fittings attach. Slide-on sleeves, glued or pinned, is the usual reading (ESTIMATE, unsourced).
- **Fitting metals:** usually brass or bronze, less often German silver, matched to the hilt [9] (SNIPPET via search).
- **Qing carry:**
  - Hung from the belt with the hilt to the rear, so it does not foul the bow.
  - To draw, the left hand swings the scabbard end rearward, bringing the hilt forward, and the blade comes out "edge-up" [9].
  - Hilts could carry a lanyard, shown on a 1760 bodyguard portrait. Modern performance swords carry tassels instead [11].

| Real-world reference | Value | Source | Status |
|---|---|---|---|
| Qing blade lengths | 68.3 to 83.2 cm | [9][12][13] | SOURCED |
| Sabre mass without scabbard | 628 g (71 cm blade), 673 g (68.3 cm) | [12][13] | SOURCED |
| Scabbard mass, Met Chinese and Indo-Chinese swords | 113.4, 144.6, 167.3, 215.5, 428.1 g | [14] | SNIPPET (Met pages rate-limited) |
| Katana saya mass | about 200 to 320 g; 500 g or more when heavily decorated | [19] | SNIPPET, weak |

### 2.3 What carries over to the build

- Wood core plus separate metal fittings at mouth, band and tip. The reference shows exactly that set, with one band instead of two and no suspension bar.
- The mouth grips a collar (habaki or throat). On this sword the collar role falls to the guard's **central pendant** (23.2 x 18.4 mm, bottom at Z 170.8) [P2]. The sheath mouth sits just under it.
- The walls are thin (about 4 to 5 mm at the mouth). The outside follows the blade envelope plus a small margin.

---

## 3. The reference sheath

Measured on `SnowFlower_sheath_reference.png` (1024 x 1536), row 0 at the top, silhouette with luminance below 0.85 [P3]. The axis is at column 505.5 ± 1 over the full height: the outline is straight and symmetric.

| Feature | Rows (px) | Width (px) | At 0.70 mm/px |
|---|---|---|---|
| Throat flower tip, proud of the rim | 31 to 45 | 14 | about 10 mm high |
| Mouth rim | 47 | 111 | 78 mm |
| Throat, widest (leaf-plate tips) | 91 | 145 | 102 mm |
| Throat bottom, back to the body | about 165 | 97 | 83 mm tall |
| Body under the throat | 171 to 271 | 97 | 67.9 mm |
| Belt band | 283 to 322 | 109 | 76 mm wide, 27 mm tall, centre 178.5 mm below the mouth |
| Body at mid-length (row 791) | | 85 | 59.5 mm |
| Body before the chape (row 1291) | | 71 | 49.7 mm |
| Chape | 1295 to 1497 | 80 at row 1351 | 141 mm long, 56 mm widest |
| Point | 1497 | 1 | |

**What the reference shows:**
- Front face only.
- Marbled black-grey lacquer, with faint lengthwise highlight lines near both edges. These suggest flat faces with chamfered or rounded edges.
- One vine starting under the throat, crossing the band, and running with three main blossom clusters (around rows 470 to 590, 680 to 720 and 1020 to 1130) plus buds and single blossoms, down to the chape.
- Blossoms on the throat, the band and the chape.

**What it does not show:** the back, the thickness, the section, the mouth opening, any ring, cord or suspension bar. None of these is invented beyond section 4's estimates. The vine and blossom positions go to the metrology in `WorkFiles/SnowFlower/v4/sheath_metrology/`.

---

## 4. Build-to table

**Frame.** The sheath is built in the **sword's frame**, so the fit can be checked in place and the holster socket needs no rotation:
- **Z** along the axis, **+Z toward the point**, the same direction as the sword's blade.
- **X** across, **+X = the sword's spine side**, -X = its edge side.
- **Y** through the thickness.

In sword coordinates the mouth rim is at Z = 171.5, 0.7 mm under the pendant. After building, move the origin to the band centre (below).

**The fit (the load-bearing arithmetic).** Revision-3 `SF_Blade` sections, measured on the master [P2]:

| Blade Z | 142 to 800 | 860 | 920 | 975 | 1020 | 1051 | 1085 (tip) |
|---|---|---|---|---|---|---|---|
| X range, mm | -23.0..23.0 tapering to -21.4..22.2 | -19.3..23.2 | -13.2..25.3 | -3.3..27.4 | 8.1..29.0 | 17.9..29.9 | 30.5 |

- The blade is 46 mm wide, 6 mm thick at the base and 1 mm at the tip.
- The raised relief on both faces makes it **13 mm** thick (Y -6.5..6.4) from Z 143 to 1008 [P1].
- The tip is at +X 30.5, so the point lies 30.5 mm to the spine side of the blade axis.

Checking every blade section against the reference outline at scale k (mm/px), with margin m per side and the sheath axis at blade X = c [P4]:

| k (mm/px) | Mouth to point | Best c | Slack, m = 2 | Slack, m = 3 |
|---|---|---|---|---|
| 0.68 | 986 mm | +6.7 | -3.7 mm | -4.7 mm |
| **0.70** | **1,015 mm** | **+6.2** | **-2.0 mm** | -3.0 mm |
| 0.75 | 1,088 mm | +7.0 | 0.0 mm | -1.0 mm |
| 0.80 | 1,160 mm | +6.8 | +2.7 mm | +1.7 mm |

What the numbers say:
- The reference outline holds the blade only at **k ≥ 0.75 to 0.80**. At that scale the sheath is 175 to 250 mm longer than the blade and the tip ends far above the chape. It would look wrong.
- Tilting the blade in the sheath instead needs **1.2°** of tilt and a **9 to 10 mm** hilt offset. That is a visibly crooked hilt; rejected.
- The binding sections are **Z 700 to 860**, where the blade is still 44 mm wide but the reference has tapered, and **Z 1020 to 1085**, where the spine sweeps out.

**Recommended build (option B).** Use k = 0.70 and c = +6.2 mm: the sheath axis sits 6.2 mm to the spine side of the blade axis. Keep the reference outline wherever it already clears. Widen the body only where the blade needs it:
- **+2 mm per side at most** for the final pose, with a 2 mm game margin.
- Hold a floor of **52.6 mm** full width down to the chape, so the tip's spine sweep never shows during the draw [P4].

The lower body ends about 5 mm (10%) wider than the picture. The user should see this in the blockout (section 8).

| Dimension | Build to | Basis | Status |
|---|---|---|---|
| Scale | **0.70 mm/px** | Blade tip lands at row 1352, inside the chape's widest band. The chape covers the point, as a kojiri does | DERIVED [P4] |
| Mouth rim position | Sword Z **171.5** | 0.7 mm under the pendant (Z 170.8). 8 mm under the leaf rims (Z 163.3) | DERIVED [P2] |
| Mouth to point | **1,015 mm** (Z 171.5 to 1186.5) | 1450 px x 0.70 | DERIVED |
| Sheathed overall, pommel to point | **1,358 mm** | 171.3 + 171.5 + 1,015 | DERIVED |
| Cavity end | Sword Z **1,093**, 8 mm past the tip | Saya 2.5 to 5 cm longer than the blade [7]; here the point carries the extra 94 mm | ESTIMATE |
| Throat height | **83 mm** | Rows 47 to 165 | DERIVED |
| Throat width | **78 mm** at the rim, **102 mm** at the leaf tips (31 mm below the rim), 68 mm at its foot | Reference rows | DERIVED |
| Throat flower | Centre about 20 mm below the rim; petal tip about 10 mm proud of the rim | Rows 31 to 110 | DERIVED; size from the metrology |
| Body width | **66.5** (Z 300), **63.3** (500), **61.3** (600), **59.8** (700, reference 57.9), **59.2** (800, reference 55.2), **55.0** (860, reference 53.3), then a **52.6** floor to the chape top at Z 1045 (reference 51.8 to 47.8) | max(reference, final fit, draw path), m = 2 | DERIVED [P4] |
| Body taper ratio | 0.79 built, against 0.73 in the picture | Lower body widened | DERIVED |
| Sheath axis vs blade axis | **c = +6.2 mm** (toward the spine) | Best offset, both margins | DERIVED [P4] |
| Body thickness | **24 mm** under the throat to **20 mm** at the chape | Koiguchi 24 to 26 mm thick [5][6]; cavity 15 mm plus a 2.5 to 4.5 mm wall | ESTIMATE, anchored |
| Cavity thickness | **15 mm** (Y ±7.5) under relief; 8 mm below Z 1008 | Relief ±6.5 [P1] + 0.5 to 1 mm clearance | DERIVED |
| Cavity width at the mouth | X **-29.7..+24.8** in sheath X (blade -23..+30.5, minus c, ±0.5) | Draw path: every section passes the mouth | DERIVED |
| Mouth recess | Dark slot of that shape, **40 mm** deep, then closed | Only visible with the sword drawn | ESTIMATE |
| Section | Flat faces with rounded chamfered edges, about 1/6 of the width each side | Highlight lines in the reference | ESTIMATE |
| Belt band | **76 x 27 mm**, 4.2 mm proud of the body each side, centre **178.5 mm** below the rim (sword Z 350.0) | Rows 283 to 322 | DERIVED |
| Chape | **141 mm**, top 874 mm below the rim, widest **56 mm** at 913 mm (the blade tip), point at 1,015 mm | Rows 1295 to 1497 | DERIVED |
| Vine | Raised silver branch, about **3 to 4 mm** wide, **1.5 to 2 mm** proud; front face; three clusters (section 3) | Reference; heights assumed | ESTIMATE; routing from the metrology |
| Blossoms | Five petals, about **20 to 28 mm** across on the body; larger on the throat, band and chape | Reference, about 30 to 40 px | ESTIMATE |
| Back face | Mirror the front vine, as the sword sheet's back view mirrors its front | Design-language analogy, not shown | ESTIMATE, user to confirm |
| Wall (real-world logic) | 4 mm across the width, 5 mm across the thickness at the mouth | Koiguchi kit [6] | DERIVED from a SNIPPET |
| Mass | **0.5 to 0.9 kg**; set **0.7 kg** in Unreal | See the cross-check below | ESTIMATE |

**Mass cross-check.** Rough volumes, not a metrology [3][34]:
- **Wood wall:** about 610 mm² (mean section 62 x 22 mm outer, less the cavity) x 791 mm, plus the ends ≈ 500 to 600 cm³. At honoki 0.49 g/cm³ that is **245 to 295 g**.
- **Silver or German-silver fittings, 0.8 to 1.0 mm sheet:**

| Part | Volume | Mass |
|---|---|---|
| Throat | about 20 to 25 cm³ | 170 to 260 g |
| Band | about 5 cm³ | about 50 g |
| Chape | about 14 cm³ | 120 to 150 g |
| Vine and blossoms, both faces | 8 to 15 cm³ | 70 to 155 g |

- **Total: 0.65 to 0.9 kg.** That is above the Met's 113 to 428 g Chinese scabbards [14] because the whole length is clad in silver ornament. Thinner fittings or a front-only vine bring it to about 0.5 kg.
- For game physics, use **0.7 kg**.

---

## 5. Modelling and game notes

### 5.1 Where the detail goes (high-poly bake source to low-poly)

- The new high-poly sheath is the bake source, kept in `Assets/SnowFlower/SnowFlower_Sheath.blend` beside the game low-poly. This is the same pattern as the sword: its r3 master stays the bake source.
- **Modelled at LOD0**, because they carry the silhouette:
  - the throat leaf plates and flower;
  - the band;
  - the chape plates, flower and point;
  - the body's chamfers;
  - the vine as a low raised strip, visible at grazing angles.
- **Baked into the normal and AO maps:** petal engraving, bark texture on the vine, buds and small twigs, and the lacquer marbling (in base colour).
- **Throat design.** It should reuse the sword's leaf-plate language: r3 `SF_Guard_MainLeaf`/`UpperLeaf` with inset and lip [P2]. The reference draws the throat as an echo of the guard.

### 5.2 Pivot and sockets

Sockets are Empties via `pipeline.make_socket`. They arrive in Unreal through the `.sockets.json` sidecar and `ue_import_sockets.py`, because FBX with LODs drops sockets on 5.8 [P5]. Positions below are in the sheath's local frame, in millimetres, after the origin is moved to the band centre on the sheath axis (sword Z 350.0, X +6.2).

| Mesh | Socket | Position (local, mm) | Rotation | Use |
|---|---|---|---|---|
| Sheath | *(pivot)* | Band centre on the axis | Axes as the sword's | The sheath's root snaps to the character's hip socket |
| Sheath | `Holster` | **(-6.2, 0, -350.0)** | **None** | The sword actor snaps here. That position is the sword's pivot (grip centre) when fully sheathed |
| Sheath | `Mouth` | (0, 0, -178.5) | +Z into the sheath | Draw and sheathe VFX, draw-path trace |
| Sheath | `Tip`, optional | (0, 0, +836.5) | | Ground-drag or impact effects |
| Sword | `Grip` | (0, 0, 0), grip centre | +Z to the tip | Hand attach. r3 `Socket_MainHand` [P2] |
| Sword | `OffHand` | (0, 0, -70) | | Two-hand pose. r3 `Socket_OffHand` |
| Sword | `Tip` | (30.5, 0, 1085) | | Trail and hit trace. r3 `Socket_BladeTip` |
| Sword | ~~`TasselRoot`~~ | | | **Delete** with the tassel |

Two points to note:
- The sword's pivot must stay the grip centre. `Holster` assumes it.
- If the v4 sword review moves the blade, the guard or the pivot, recompute the mouth position, c and `Holster` from the v4 mesh with `sheath_fit_calc.py`, not from this table.

### 5.3 Containment gate (replaces hiding the blade)

**Shipped practice.** Shipped games keep the blade physically inside the sheath rather than hiding it:
- Skyrim's weapon NIF carries its own scabbard node `Scb`, which stays at the hip when the weapon is drawn [28].
- Generic equip systems use one holstered object and one held object, toggled by animation events [29].
- Unreal users are told to make the sword and the sheath two separate actors [26].

The blade inside the sheath is hidden by depth testing and costs little. Its hilt has to draw anyway.

**The gate.** Put the sword at `Holster` and check:
- **Final pose:** every sword vertex below the mouth plane lies inside the sheath shell by at least **1 mm**. Test every LOD pairing, because the two meshes switch LOD independently. The worst case is **sheath LOD2 against sword LOD0**: a decimated sheath shrinks and the sharp blade does not.
- **Draw path:** slide the sword out along +Z (sheath frame -Z) in 10 mm steps for the whole blade length. No vertex may cross the shell below the mouth. Warn only, if the user accepts a flicker during a fast draw.
- **Clash:** no guard vertex below Z 171.5. The pendant bottom stays above the mouth rim, with a gap of 0.5 to 1.0 mm.

### 5.4 Collision

- **Sheath:**
  - Hulls `UCX_SM_SnowFlower_Sheath_LOD0_00` (throat and upper body down to the band), `_01` (body) and `_02` (chape), 12 to 24 vertices each [P5][23].
  - One hull over the whole length would be a fat box.
  - Set Mass to **0.7 kg**.
- **Sword:** the r3 hulls `UCX_SM_SnowFlower_00/01/02` do not import on a LOD group in 5.8. They must be keyed `UCX_SM_SnowFlower_LOD0_NN` [P5].
- **While attached,** both components should use NoCollision, or a query-only profile for hit traces, so they do not fight the character capsule. Simulate physics only when the item is dropped. The attach call's weld flag [22] matters only if physics is on.

### 5.5 LODs

The pack's prop rule scales screen sizes by radius / 50 mm (`spec.scaled_lod_screen_sizes`). That is built for 50 mm props: on a 1 m sheath the factor is about 10, which pushes LOD1's threshold above 1.0. **Do not use it here.** Use the character rule, **1.0 / 0.5 / 0.25** [P5], so the weapon switches with the wearer.

| Mesh | Bounds radius | LOD1 at | LOD2 at | Source |
|---|---|---|---|---|
| Sheath | about 0.52 m | 1.85 m | 3.7 m | DERIVED: d = r / (s x 0.5625), 90° hfov at 16:9 (pack convention) |
| Sword | about 0.64 m | 2.3 m | 4.5 m | DERIVED |

| Sheath LOD | Screen size | Triangles | What changes |
|---|---|---|---|
| LOD0 | 1.0 | **10,000 to 16,000** | Everything in 5.1. 24 to 32 sides on the body section |
| LOD1 | 0.5 | 45 to 55% of LOD0 | Vine flattened into the normal map; blossoms as low domes; half the body sides |
| LOD2 | 0.25 | 20 to 25% of LOD0 | Fittings as simple shells; the point kept. **Must still pass 5.3** |

**Budget comparisons.** Shipped and sold pairs, all non-hero:
- katana 14,526 + saya 4,276 [30];
- sword 2,864 + sheath 3,858 [31] (SNIPPET).

The project's hero weapon budget is 20 to 50k [P5]. Sword LOD0 at 25 to 40k plus sheath at 10 to 16k keeps the pair in the tens of thousands.

**Nanite** stays off: authored LODs are this project's measured path.

### 5.6 Texel density and materials

- **Area:** body about 1,530 cm² (mean perimeter about 150 mm x 1,015 mm) plus fittings about 400 cm² ≈ 1,900 cm².
- **Density:** one **4096** set at 70% packing gives about **78 px/cm** (DERIVED). The house floor is 10.24 px/cm [P5]. Wear must be unique, so do not mirror UVs; mirror only the back-face vine *geometry* if the user approves it.

| Slot | Recipe | Status |
|---|---|---|
| `Lacquer` | Marbled black-grey from the reference, dielectric (metallic 0), roughness about 0.2 to 0.35 (polished lacquer), faint scuffs at the band and the mouth | ESTIMATE |
| `Silver` | Metallic 1.0, base colour near white (silver ≈ 0.99 [34]), roughness 0.25 to 0.4 with darker recesses from AO. Match the sword's silver so the set reads as one | SOURCED base, ESTIMATE finish |

- Both slots can share the one texture set.
- The two slots exist for the pack's recolour instances [P6]: `M_Steel_Master` for silver. Whether lacquer fits `M_Steel_Master` or needs a new dielectric master is an open question (section 8).
- DirectX normals, ORM with baked AO in R, UV1 lightmap channel [P5].

### 5.7 Unreal setup

1. **Import.** Sheath and sword FBX with **Import Mesh LODs ON** [24][P5], UCX keyed to the LOD0 node, then `ue_import_sockets.py` from each sidecar. Verify in a second, fresh process.
2. **Character socket** (owned by the character workstream, not this job). Add a skeleton socket on the pelvis, left side, for a right-hand draw [20]. Its rotation sets the carry: hilt forward and up, sheath about **30 to 45°** below horizontal, edge up (ESTIMATE). This is the katana-style carry [2][18] and the Qing edge-up draw [9]. Keep the angle in the **character's socket**, not in the mesh, so the carry can change without re-exporting.
3. **Equip actor.** Spawn two actors, `BP_SnowFlowerSheath` and `BP_SnowFlowerSword` [26]:
   - Attach the sheath: `AttachToComponent(character mesh, SnapToTarget, "Sheath_L")`.
   - Attach the sword: `AttachToComponent(sheath static mesh component, SnapToTarget, "Holster")`. Static-mesh sockets accept attached actors [21]; snap-to-target takes the socket's transform [20][22].
4. **Draw and sheathe.**
   - An AnimNotify in the draw montage re-attaches the sword to the hand socket at the frame the hand closes on the grip [32][20].
   - Sheathing reverses it, snapping back to `Holster` at the frame the guard meets the mouth.
   - The sheath never moves.

---

## 6. The tassel question

**Answer: remove it. The user's call is right for a game weapon, with two caveats.**

| For a tassel | Against a tassel |
|---|---|
| It is in the design sheet. The pommel crop even shows the cord through the pommel [P7] | **A static mesh cannot hang.** A static tassel is frozen in the design-sheet pose. Held level, raised overhead or worn at 45°, it points sideways or up, and it stays that way through every swing. It looks wrong in almost every frame of play |
| Chinese sword tassels are a real tradition. Historically they were probably wrist lanyards; today they are mostly decorative [11][33] (SNIPPET) | **Moving it costs a rig.** Motion means turning the sword into a skeletal mesh with a bone chain. AnimDynamics chains are "much more resource intensive" than single bodies [25], and physics on a fast weapon needs tuning ("swinging a noodle" [27]). The pack's tiers put that cost on hero cloth only [P5] |
| Secondary motion trailing a swing reads well in animation [37] (SNIPPET) | **Clipping.** The r3 bundle hangs to guard height, **107 mm** off the axis [P1]. It would cross the forearm on most grips, and the hip and sheath when holstered |
| | **Budget.** The r3 tassel is **71,880 triangles**, **15.8%** of the r3 mesh [P1]. That is more than the whole sheath budget |
| | **Readability.** A dark cord and bundle against a dark grip and dark clothes is a thin, aliasing sliver at play distance. It adds noise, not shape |

**Caveats:**
1. **Clean up the pommel.** Removing the cord leaves the design sheet's cord hole. Close it, or keep it only if it reads as pommel ornament, per the brief. The r3 `SF_Tassel_AttachmentKnots` sit at X -25..-35, Z -121..-139, on the pommel collar [P1].
2. **Keep the door open, off by default.** The character plan wants swappable cosmetics [P8]. If the user ever wants a charm, it should be a separate skeletal-mesh cosmetic on an optional `Charm` socket at the pommel, simulated with AnimDynamics, not geometry welded into `SM_SnowFlower`. Adding that socket now is the user's choice (section 8). The default build has no tassel and no `TasselRoot`.

The sheath gets **no tassel and no cord**. The reference shows none, and the band-only mount means the belt belongs to the character's garment.

---

## 7. IP note (for the user's decision; nothing acted on)

- The sword reference sheet is titled **"JIN MUWON - SNOW FLOWER BLADE"** [P7]. Jin Mu-won is the protagonist of the Korean webtoon *The Legend of the Northern Blade*.
- The project's own deny list already names "jinmuwon", "jin mu-won" and "northern blade" [P5].
- If the design derives from that franchise, it is fine for the user's personal game. It **must not be sold on Fab** under that name, and probably not with that design, as with the kunai's licensed silhouette.
- The sheath reference carries no title, but it is drawn to match.
- No asset, file, material or socket name may use the franchise words. `SnowFlower` is generic and stays.
- **The user decides at release.**

---

## 8. Open questions

1. **Widen the lower body** by up to 2 mm per side (about 10% at the bottom), or accept a longer sheath (k ≥ 0.75, 1,088 mm or more) with the tip well above the chape? Recommended: widen. Show the blockout beside the reference.
2. **Does the v4 sword review change the blade?** Narrowing the spine sweep would let c go toward 0 and the reference taper hold. Re-run `sheath_fit_calc.py` on the v4 blade before modelling.
3. **Back face:** mirror the front vine (recommended, by analogy with the sword sheet) or plain lacquer?
4. **Carry:** edge up, hilt forward (katana-like), or hilt to the rear (Qing)? This depends on the draw animation set.
5. **Lacquer master:** does `M_Steel_Master` handle a dielectric through ORM.B, or does the pack need `M_Lacquer_Master`?
6. **Optional `Charm` socket** on the sword pommel for a future cosmetic: yes or no?
7. Sheath thickness (24 to 20 mm) and section are estimates. No view shows them.
8. **Mass:** 0.7 kg is a mid estimate from rough volumes. The sword's own mass is not studied here.

---

## 9. Verification of high-stakes claims

Checked 2026-09-26 by WebFetch and WebSearch; local numbers by headless Blender and system Python. Nothing was downloaded; no asset was written.

| Claim | Status | Checked against |
|---|---|---|
| Saya is two honoki halves, rice glue, fitted cavity; gap neither loose nor tight | **Verified** | [1]; [2] for the fitting names |
| Honoki density 0.40 to 0.49 to 0.61; used for scabbards | **Verified** | [3]; [35] for the use |
| Koiguchi horn 40 x 24 x 10 mm | **Verified** | [5] |
| Koiguchi 44 x 26 x 8 mm, slot 36 x 16 mm | **SNIPPET** | [6]; pages returned 403 |
| Saya 2.5 to 5 cm longer than the blade | **SNIPPET** | [7] |
| Dao scabbard: wood halves, leather, ray skin or lacquer; mouthpiece, two bands, bar, chape | **Verified** | [8][9] |
| Qing carry hilt to the rear; draw edge-up | **Verified** | [9] |
| Yanmaodao sweeps up in the last quarter; r3 blade matches (sweep from Z 800 of 142..1085, 70%) | **Verified**, profile measured | [10], [P2] |
| Met scabbard weights 113 to 428 g | **SNIPPET** | [14]; pages rate-limited (429) |
| Katana at 45° in the obi | **Weak** | [18], a retail blog |
| Tachi hung edge down, horizontal, on two ashi | **Verified** | [17] |
| Skyrim `Scb` node keeps the scabbard at the hip | **Verified** | [28] |
| Sword and sheath as two actors in Unreal | **Verified**, forum | [26] |
| SnapToTarget attach to a named socket | **Verified** | [20][22] |
| Static-mesh sockets accept attached actors | **Verified**, 4.27 page | [21] |
| AnimDynamics chain costs more than a single body | **Verified**, search summary of the 5.8 page | [25] |
| UCX must key to the LOD0 node; FBX LOD files drop sockets | **Verified locally** on UE 5.8.2 | [P5], not by Epic's page |
| r3 blade profile, relief thickness, guard lowest points, sockets | **Measured** | [P1][P2] |
| r3 tassel 71,880 triangles | **Measured** | [P1] audit sum |
| Reference outline rows and widths | **Measured** | [P3] |
| Straight reference outline cannot hold the r3 blade coaxially at k ≤ 0.72 | **Computed** | [P4] |
| Fab sword 2,864 and sheath 3,858 triangles | **SNIPPET** | [31]; page 403 |
| Katana 14,526 and saya 4,276 triangles | **Verified** | [30] |

---

## 10. Sources

**Web**

1. Toukenza, *The Sayashi's Craft*: https://toukenza.jp/en/column/sayashi-scabbard-craftsman-shirasaya-koshirae-wood
2. Wikipedia, *Japanese sword mountings*: https://en.wikipedia.org/wiki/Japanese_sword_mountings
3. JAWIC wood database, ホオノキ (honoki): https://www.jawic.or.jp/woods/sch.php?nam0=hoonoki
4. Nagoya Touken Museum, 鞘師の仕事 (the scabbard maker's work): https://www.meihaku.jp/sword-basic/sayashi-jobs/
5. samuraischwert.kaufen, koiguchi horn reinforcement: https://samuraischwert.kaufen/en/product-2/koiguchi-horn-reinforcement-for-opening-a-centreboard-sheath/
6. Koiguchi kit listings (SNIPPET): https://www.worthpoint.com/worthopedia/buffalo-horn-koi-guchi-koiguchi-172664658 and https://www.ebay.com/itm/323679022057
7. Saya length versus blade (SNIPPET): https://www.hanbonforge.com/Replacement-Saya-for-Japanese-Samurai-Sword-KATANA-WAKIZASHI-TANTO and https://romanceofmen.com/blogs/katana-info/how-long-is-a-katana
8. Mandarin Mansion, *Dāoqiào*: https://www.mandarinmansion.com/glossary/daoqiao
9. Mandarin Mansion, *Military sabers of the Qing dynasty*: https://www.mandarinmansion.com/article/military-sabers-qing-dynasty (fitting metals: https://northernwu.com/index.php/research/50-an-introduction-to-antique-chinese-swords-of-the-qing-dynasty-period, SNIPPET)
10. Mandarin Mansion, *Yànmáodāo*: https://www.mandarinmansion.com/glossary/yanmaodao
11. Wikipedia, *Dao (Chinese sword)*: https://en.wikipedia.org/wiki/Dao_(Chinese_sword)
12. Mandarin Mansion, *Peidao in iron fangshi mounts*: https://www.mandarinmansion.com/18th-century-peidao-iron-fangshi-mounts
13. Mandarin Mansion, *18th century Chinese saber*: https://www.mandarinmansion.com/18th-century-chinese-saber
14. The Met, scabbard weights (SNIPPET): https://www.metmuseum.org/art/collection/search/31096, /31111, /26740, /32236, /31106
15. Wikipedia, *Scabbard*: https://en.wikipedia.org/wiki/Scabbard
16. Wikipedia, *Chape*: https://en.wikipedia.org/wiki/Chape
17. Wikipedia, *Tachi*: https://en.wikipedia.org/wiki/Tachi
18. Musashi Swords, *How to wear a katana* (weak): https://musashiswords.com/blogs/news/how-to-wear-a-katana
19. Romance of Men, saya guide (SNIPPET, weak): https://romanceofmen.com/blogs/katana-info/katana-saya-complete-guide-to-understand-the-sheath-of-the-legendary-samurai-sword
20. Epic, *Skeletal Mesh Sockets* (UE 5.8): https://dev.epicgames.com/documentation/unreal-engine/skeletal-mesh-sockets-in-unreal-engine?lang=en-US
21. Epic, *Setting Up and Using Sockets With Static Meshes* (4.27): https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-and-using-sockets-with-static-meshes?application_version=4.27
22. Epic, *Equip Your Character With C++ Tools* (5.8): https://dev.epicgames.com/documentation/unreal-engine/coder-07-equip-your-character-with-cplusplus-tools?lang=en-US
23. Epic, *FBX Static Mesh Pipeline* (5.8): https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine
24. Epic, `FbxStaticMeshImportData` (Import Mesh LODs): https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/FbxStaticMeshImportData?application_version=5.0
25. Epic, *Animation Blueprint AnimDynamics* (5.8): https://dev.epicgames.com/documentation/unreal-engine/animation-blueprint-animdynamics-in-unreal-engine
26. Unreal forums, sword to hand and sheath to hip: https://forums.unrealengine.com/t/how-do-i-attach-sword-to-hand-and-sheath-to-hip-using-actor-bp/400834
27. Unreal forums, static versus skeletal mesh for equippables: https://forums.unrealengine.com/t/static-mesh-vs-skeletal-mesh-for-equip-able-items-pros-cons-tradeoffs/146094
28. Beyond Skyrim wiki, *Nifskope Weapons Setup*: https://wiki.beyondskyrim.org/wiki/Arcane_University:Nifskope_Weapons_Setup
29. Emerald AI wiki, equippable weapon: https://github.com/Black-Horizon-Studios/Emerald-AI/wiki/Setting-up-an-Equippable-and-Unequippable-Weapon
30. Blender Artists, *Katana (real time game ready)*: https://blenderartists.org/t/katana-real-time-game-ready/1464651
31. Fab, *Sword animations* (SNIPPET): https://www.fab.com/listings/101c78f8-81b6-46a1-b908-b7db4e1b2cc3
32. Crow's Keep Studios, equip and unequip sword (SNIPPET): https://www.crowskeepstudios.com/post/unreal-engine-interactable-sword-item-equipping-and-unequipping-and-animation-changes
33. Chinese sword tassel as lanyard (SNIPPET): https://swordis.com/blog/parts-of-a-chinese-sword/ and https://www.martialtalk.com/threads/sword-tassel.1068/
34. Physically Based, silver base colour: https://physicallybased.info/
35. Wikipedia (de), *Honoki-Magnolie*: https://de.wikipedia.org/wiki/Honoki-Magnolie
36. Wikipedia, *Uchigatana* (general context): https://en.wikipedia.org/wiki/Uchigatana
37. MoCap Online, sword animation guide, secondary motion (SNIPPET): https://mocaponline.com/blogs/mocap-news/sword-melee-animation-guide

**Project**

- P1. `WorkFiles/SnowFlower/audit_report.json`: r3 per-object bounds and triangles
- P2. `Assets/SnowFlower/SnowFlower_Master.blend`: read-only headless measurement (`study_calc/measure_r3_blade_profile.py`)
- P3. `References/SnowFlower/SnowFlower_sheath_reference.png` (`study_calc/measure_sheath_reference_rows.py`)
- P4. `WorkFiles/SnowFlower/v4/study_calc/sheath_fit_calc.py` and `.txt`
- P5. `ASSET_GUIDELINES.md`, sections 2, 3, 4, 5, 6.2 and the physics tiers
- P6. `WorkFiles/materials/MATERIALS_REPORT.md`
- P7. `References/SnowFlower/SnowFlower_user_reference.png`
- P8. `CHARACTER_PIPELINE_REVIEW.md` / character customization plan
