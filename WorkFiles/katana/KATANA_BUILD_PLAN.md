# Katana + saya: game and tech build plan

**Date:** 2026-10-03. **Role:** game + tech study (planning only; nothing built, no lock taken, no Unreal or Blender run).
**Scope:** `SM_Katana` (a basic, plain, standard katana) and `SM_Katana_Saya` (its scabbard), for the UE 5.8 ninja game
(1v1 duel MVP, battle royale later) and the Fab pack. No user reference exists: the Study phase's dimensioned design
sheet is the reference. Every dimension below marked *nominal* is a placeholder that the design sheet overrides; the
builder derives the final socket and fit numbers from the sheet's numbers, never from this file.

**Read for this plan:** `CLAUDE.md`, `ASSET_GUIDELINES.md` (all), `FAB_ASSET_STUDY.md` (3.2, 3.5, 4.3-4.4, 6),
`WorkFiles/materials/MATERIALS_REPORT.md` (A1-A8, Part B 2-3, heels), `Scripts/unreal/materials/README.md` and
`material_spec.json` (masters, the Snow Flower / kunai / flashbang items, `changes_v4_snowflower`),
`np_masters.py` (`mip_level`), the Snow Flower `SWORD_V4_REPORT.md`, `SHEATH_REPORT.md`, `Exports/SnowFlower/v4/README.md`
and both sidecars, `Scripts/SnowFlower/v4/shv4_fit.py` and `shv4_verify.py`, the kunai report (wrap and UV-tile notes),
`Scripts/pipeline/` (`export_fbx.py`, `qa_check.py`, `helpers.py` arguments), `showcase/ASSET_LIST.md`, and the
player body's skeleton record (`References/Characters/MH_PlayerDefault/base_lock.json`: pelvis at 1.032 m, so a
character of roughly 1.75-1.80 m).

---

## 0. The plan in one screen

| Item | Katana `SM_Katana` | Saya `SM_Katana_Saya` |
|---|---|---|
| LOD0 / LOD1 / LOD2 triangles | **target 16-20k** (ceiling 25k) / ~6.7k (≈40 %) / ~1.8k (≈10 %) | **target 6-8k** (ceiling 12k) / ~2.5k / ~0.85k |
| LOD screen sizes | proposed 1.0 / 0.35 / 0.15, **set by an LOD-pop measurement** (section 2.3) | same |
| Material slots | 3: `M_Katana_Blade`, `M_Katana_Fittings` (both `M_Steel_Master`), `M_Katana_Grip` (`M_Fabric_Master`, recolourable, **Metal From ORM on**) | 2: `M_Katana_Saya_Lacquer` (`M_Fabric_Master`, recolourable), `M_Katana_Saya_Fittings` (`M_Steel_Master`) |
| Textures | Steel atlas **4096 x 1024** (same memory as 2048²; fallback 2048²) BC/ORM/N; Grip atlas 2048² BC/ORM/N + `Detail16` 1024² | Saya atlas 2048² BC/ORM/N + lacquer `Detail16` 1024² |
| User colours | Blade: `Steel Tint`. Fittings: `Steel Tint`. Ito cord: `Colour` (the same windows keep their baked colour) | Lacquer: `Colour`. Horn fittings: `Steel Tint` |
| Collision | 6 hulls `UCX_SM_Katana_LOD0_00..05`: 4 blade segments (habaki in the first), tsuba + seppa, tsuka | 5 hulls `UCX_SM_Katana_Saya_LOD0_00..04`: 4 body segments along the arc, kurikata |
| Sockets (sidecar) | `Grip` (pivot), `OffHand`, `BladeBase`, `BladeMid`, `BladeTip`, `TrailStart`, `TrailEnd`, `CenterOfMass` | `BeltMount` (pivot), `Holster`, `Mouth`, `DrawPivot` |
| Pivot / frame | Grip = right-hand centre on the tsuka axis; +Z to the tip along the tsuka axis; **+X = mune (back)**, -X = ha (edge); -Y = omote | BeltMount = obi station on the saya centre line; axes = the sheathed katana's axes, so `Holster` has **zero rotation** |
| Fit | Copy of the Snow Flower method, with the draw as an **arc** about `DrawPivot`: 0 intersections in all 9 LOD pairs, clearance, enclosure, arc draw clean at every 10 mm, flush seat (≤ 1 mm), exported bytes only, Holster gate in Unreal | |
| Tsuka-ito | **Real geometry**: parametric hira-ito ribbons on the core surface, crowned 7-vertex section, raised over/under crossings, hineri twists on the edges; same visible in the diamond windows; LOD2 = a baked shell | |

---

## 1. Lessons carried over (what worked, what failed)

From the Snow Flower sword and sheath, which passed every engineering gate and failed every blind look test:

| Keep (worked) | Avoid (failed or cost time) |
|---|---|
| Parametric generator per part; LOD1/LOD2 from the **same generator at lower resolution** with the same UV islands (no Decimate, no UV transfer, no seams between LODs) | The grip wrap was a **smooth spiral** with the diamonds only implied: judge's first tell. The katana's ito must be real crossing geometry (section 4) |
| `Grip` socket = pivot = primary hand; sockets only through the sidecar | Ornament baked onto flat solids (throat plates) read flat at grazing angles. "Basic" removes ornament; whatever relief remains is geometry |
| Saya cavity = the **shipped** sword's vertices (every LOD, plus edge samples every 0.5 mm) swept along the draw path + clearance, so the draw is clean by construction | The sheath had to be tilted 0.65° because it was fitted to a fixed outline. Here both are designed together: **zero Holster rotation** |
| Verification on the **exported FBX bytes** of both assets, with the sword placed from the **exported sidecar's** Holster socket | A visible seat gap of ~20 mm went unmeasured until the final pass: the seat-gap check is a gate from day one |
| Unreal harness: fresh processes, sha256 of the bytes, hull round trip, in-engine Holster composition (0.0001 cm) | Writing outside the project (`C:\WorkFiles`, `C:\dev`) from relative paths: all scripts use absolute paths from a `ROOT` constant |
| `Recolour/*_Detail16.png` (G16) imported instead of an 8-bit sRGB detail (which builds as BGRA8) | 4096 maps by default (85 MiB BGRA8 detail): 2048 default here, one measured exception (section 5.3) |
| Detail normalised over the **recolourable texels only** (sheath marble) so the constants pass their knee and mip gates | Tassels and cords: none on either asset (a static cord freezes in one pose). The saya's kurikata keeps its empty cord hole; no sageo |

From the kunai: wrap in **UV tile u 1..2** so the two slots never overlap in UV0 (Unreal's lightmap packer then stays
overlap-free); thin blade lands unfolded onto a neighbouring island (the 0.15 mm land made a sub-texel chart that
broke the lightmap packer); LOD screen sizes measured, not defaulted (kunai 1.0 / 0.28 / 0.098).

---

## 2. Frames, pivots, dimensions, LOD switching

### 2.1 Katana frame (Blender metres, model in mm; Unreal cm after export)

- **Origin = `Grip`** = centre of the right hand on the tsuka axis, about 45 mm behind the tsuba (a hand is ~85-90 mm
  wide, index finger against the tsuba). This is the house rule (pivot at the grip point) and the Snow Flower's.
- **+Z** = the tsuka axis toward the tip. **+X** = the mune (back) side; the tip curves toward +X (the edge is on the
  convex side). **-X** = the ha (cutting edge). **-Y** = omote (the face that looks away from the body when worn
  edge-up on the left hip). Same convention as the Snow Flower, so the README and the game code read alike.
- **Curvature model (the fit depends on it):** the habaki and tsuka are straight and coaxial with Z. The blade's mune
  line is **one circular arc of radius R**, tangent to +Z at the munemachi. One constant-curvature arc means a draw is a
  pure rotation about a fixed centre (`DrawPivot`), which makes the saya cavity and the draw path exact. If the design
  sheet wants koshi-zori (curvature concentrated near the habaki), it must be approximated by one arc within 0.3 mm on
  the mune line, or the fit stage must switch to a general sweep (section 7.2). **Decision for the Study phase.**
- **Cross-sections must not grow toward the tip** (width, thickness and kasane non-increasing from the machi to the
  yokote). Then the arc-swept cavity equals the sheathed blade plus clearance, with no slop.
- If the design gives the tsuka its own small angle to the blade (tsuka-zori), the frame stays on the tsuka axis and the
  arc's start tangent tilts by that angle; sockets and `DrawPivot` are derived from the spec either way.

### 2.2 Nominal layout (the design sheet replaces these numbers)

Generic historical proportions for a character of ~1.78 m; nothing here is a specific named blade.

| Along Z (mm, katana frame) | Nominal |
|---|---|
| Kashira end | -220 |
| Tsuka (kashira + ito + fuchi) | -220 .. +45 (265 mm; section ~33 x 25 mm at the fuchi, a slight waist mid-tsuka) |
| Seppa / tsuba / seppa | +45..47 / 47..53 (Ø ~76 mm, plate 5 mm, rim 6 mm) / 53..55 |
| Habaki | 55..88 (33 mm); munemachi at z 88 |
| Blade | nagasa 710 mm (chord), sori 17 mm (torii-zori), motohaba 31 mm, sakihaba ~21 mm, kasane ~7 -> 5 mm, chu-kissaki |
| Derived | R = 3,715 mm; arc length 711.1 mm; arc angle 10.97°; tip ≈ (+83, 0, +795) mm (68 mm off the tsuka axis); overall ≈ 1,015 mm |
| Saya | mouth (koiguchi top) at katana z 55.3 (0.3 mm seat gap); obi station / pivot ~110 mm further in; kojiri end ≈ katana z 815; length ≈ 760 mm |
| Mass (nominal, for physics) | katana ≈ 1.15 kg, point of balance ≈ 120 mm in front of the tsuba; saya ≈ 0.40 kg. The builder computes both from part volumes x densities (steel/iron 7.85, brass 8.5, ho wood 0.45, ray skin 1.1, silk cord ~0.7 effective, horn 1.3) |

### 2.3 LOD switching for a long, thin object

Unreal's screen size uses the **bounding sphere** (radius ~0.51 m here), so a katana stays on high LODs much longer
than a compact prop. Roughly, screen size ≈ r / d at 90° FOV: with the house 1.0 / 0.5 / 0.25 the switches fall at
~1.0 m and ~2.0 m, so in a third-person duel (camera 2.5-4 m) the opponent's sword would sit on LOD2 most of the time.
**Proposal: 1.0 / 0.35 / 0.15** (LOD1 beyond ~1.5 m, LOD2 beyond ~3.4 m), then **measure** like the kunai: render each
switch at its distance at 2560 x 1440, 90° FOV, and require a mean silhouette difference ≤ 1 px and the tsuka
diamonds still legible at the LOD1 -> LOD2 switch. The sidecar carries the chosen sizes (an FBX LodGroup carries none:
Unreal would compute 2.0 / 0.75 / 0.56 by itself).

A LOD3 (~600-900 triangles, screen size ~0.05) is worth adding for the battle royale; not in this MVP build. Nanite
**off** on both (small, held, moving; pack convention; Fab's "dense meshes only" rule).

---

## 3. Triangle budgets

### 3.1 Why these numbers

- The house range for a hero weapon is 20-50k. The job's band is 10-25k for the katana and 5-12k for the saya, and
  this design sits low in it on purpose: a **basic** katana is plain surfaces (blade, discs, collars) where extra
  triangles buy nothing once bevels are crisp. The one place geometry earns its keep is the **tsuka-ito**, which
  takes ~45 % of LOD0.
- In the 1v1 duel at most 2 katana and 2 saya are drawn; LOD0 cost there is negligible. In the battle royale up to
  ~100 can be relevant, so the LOD chain carries the cost (LOD2 under 2k, LOD3 later).
- Comparison: the Snow Flower ships 21,310 / 8,850 / 2,778 with heavy ornament; its sheath 11,424 / 5,600 / 3,292.
- The 25k ceiling is headroom for the ito only (more crown segments if the first look round shows faceting).

### 3.2 Katana, per part

| Part | LOD0 | LOD1 | LOD2 | Notes |
|---|---|---|---|---|
| Blade (shinogi-zukuri: ha land, ji, shinogi-ji, iori mune, yokote, kissaki with fukura) | 3,000 | 1,300 | 500 | ~14 section vertices incl. 0.15-0.2 mm lands so the shinogi and yokote catch a crisp highlight; dense stations only in the kissaki. A bo-hi groove, if the sheet has one, +800 |
| Habaki | 600 | 250 | 80 | |
| Seppa x2 | 400 | 160 | 0 | LOD2: folded into the tsuba disc |
| Tsuba (plain; rim; nakago-ana hidden) | 1,800 | 700 | 250 | 64 / 32 / 20 segments. Hitsu-ana openings only if the sheet draws them |
| Fuchi | 600 | 250 | 80 | |
| Kashira (+ ito laced over it if the sheet shows kake-maki) | 1,000 | 400 | 120 | |
| Tsuka core (same visible in the windows) | 1,000 | 500 | - | Ray-skin nodules are normal + colour, not geometry |
| **Tsuka-ito** (ribbons, crossings, twists, ends) | **7,000** | **2,800** | - | Section 4 |
| LOD2 tsuka shell (baked from LOD0) | - | - | 700 | Own island in the Grip atlas |
| Menuki x2 (only if the sheet has them; plain forms) | 800 | 300 | 0 | LOD2: baked into the shell |
| Mekugi ends | 100 | 40 | 0 | |
| **Total** | **≈16,300** | **≈6,700** | **≈1,730** | strictly descending; qa budget flag `--budget 25000` |

### 3.3 Saya, per part

| Part | LOD0 | LOD1 | LOD2 |
|---|---|---|---|
| Outer body (oval / egg section, 32 / 16 / 10 sides, curved along the arc) | 3,800 | 960 | 280 |
| Cavity (swept support polygon, mouth to the kojiri end) | 1,600 | 800 | 300 |
| Mouth annulus + koiguchi (horn) | 700 | 300 | 120 |
| Kurikata (knob with its empty cord hole) | 500 | 200 | 60 |
| Kojiri (horn end cap; plain) | 500 | 200 | 80 |
| **Total** | **≈7,100** | **≈2,460** | **≈840** |

The cavity exists at **every** LOD (coarser polygons), because the fit gate covers all 9 LOD pairs. qa flag
`--budget 12000`.

---

## 4. Tsuka-ito: real geometry that reads at first-person distance

**What has to read** (in priority order): (1) the row of **diamonds** (hishigami) down each flat face with the pale same
showing through, (2) the **scalloped edge silhouette** where the cords twist round the ha and mune edges (hineri-maki),
(3) the **over/under lift** at each crossing, (4) the flat braided silk texture. At first person the tsuka is ~40-60 cm
from the camera; a 23 mm diamond then spans ~80 px at 1440p, so 1-3 are geometry and 4 is the normal map.

**Construction (parametric, no sculpt, no boolean):**

1. **Core** `C(s, t)`: the tsuka surface, s along Z, t around the oval section (33 x 25 mm nominal, a slight waist).
   The diamond windows are this surface with the same's nodule normal map and light colour.
2. **Cord paths in (s, t):** per crossing k (N per face, nominal 8-9 over ~200 mm, pitch ≈ 23 mm) two cords cross
   at the face centre line. Each cord centre path is a straight diagonal in (s, t) across the face, then a
   **twist segment** over the edge, then the next face. Spacing, N and the cord width (10-11 mm hira-ito) come from the
   design sheet.
3. **Ribbon:** each cord is a band of width w swept along its path on the core, offset along the core normal:
   - section of 7 vertices across: edge bevel, crowned top (cord thickness ~1.0-1.2 mm), edge bevel, and two short
     side walls that **sink 0.3 mm into the core** (no light leaks, no gaps; open bottom = legitimate boundary edges,
     reported, not failed by qa);
   - **lift** h(s, t): the upper cord rises ~1.0 mm over each crossing (the hishigami paper triangles are implied by
     this lift and never modelled); the lower cord stays at the base offset and is hidden under the upper one there;
   - steps along the path: ~6 mm on the flat faces, ~3 mm over the curved shoulders and through the twists.
4. **Twists (hineri)** at the edges: the band rotates 180° about its own path over ~12-15 mm while wrapping the edge;
   this makes the zig-zag edge silhouette. It is the biggest single read after the diamonds.
5. **Ends:** under the fuchi and under (or over, for kake-maki) the kashira, as the design sheet shows.
6. **Each ribbon carries its own parametric UV** (along, across) in mm. The braid weave is painted in that space,
   so it follows every cord with no distortion. Every ribbon still gets a **unique** island in UV0 (no stacked
   islands; qa and the lightmap forbid overlaps).

**Counts:** ~2 m of cord path in total, at ~12 triangles per step: ≈5.4k for the ribbons, ≈1.0k for the twists,
≈0.5k for the ends: **≈7k at LOD0**. **LOD1:** 5-vertex section, 8 mm steps, simpler twists: ≈2.8k (same paths, same
islands, so no LOD pop in pattern). **LOD2:** no ribbons; a 16-sided tsuka shell whose own island is **baked
selected-to-active from LOD0** (ito + core, cage ~2 mm), so the diamonds are a texture at LOD2.

**Gates for the wrap:** diamond count, pitch and width equal to the sheet; edge scallop amplitude ≥ 1 mm in the
side silhouette; diamond-window contrast (same vs ito luminance) ≥ the sheet's; no cord-to-cord gaps where the core
shows between cords (ray test from outside, 0 hits on the core except inside the windows); a first-person 3/4 crop at
50 cm and a third-person crop at 3 m in the review set; LOD0/LOD1/LOD2 switch renders.

---

## 5. Materials, slots, textures and the pack colour system

### 5.1 How the pack system constrains the choices (measured in the code)

- `M_Steel_Master`: BaseColor = saturate(BC x `Steel Tint`), Metallic = ORM.B. **Steel Tint is a clamped multiplier:**
  it re-tints bright metal (silver -> gold) but cannot lighten, and it barely changes a dark part. So the fittings
  that should change colour must be baked as **bright metal** (linear albedo ≥ ~0.5).
- `M_Fabric_Master`: BaseColor = the recolour `Colour` over a normalised `Detail Map`; with the static switch
  **Metal From ORM** on, texels with ORM.B metallic **or** baked BC luminance ramping 0.2 -> 0.4 keep their baked colour
  (and Metallic = ORM.B). Used on the Snow Flower sheath lacquer and the flashbang paint.
- `mip_level()` in `np_masters.py` uses one scalar `Detail Map Size` for both axes: **every Detail16 map must be
  square.** Non-square maps are only safe on `M_Steel_Master` slots (no detail map).
- Instance chain: master -> `MI_<Item>_<Part>_Base` (all textures + generated constants) -> `MI_<Item>_<Part>` on the
  mesh (overrides only its colour). Reset returns to the shipped look.

### 5.2 Slots

**Rule for assigning parts: by finish, not by name.** Forged iron/steel parts (blade, an iron tsuba) go in the Blade
slot; bright soft-metal parts that should tint as a set (habaki, seppa, fuchi, kashira, menuki; a brass tsuba if the
sheet has one) go in Fittings.

| Asset | Slot (index) | Instance | Master | Parts | Buyer control |
|---|---|---|---|---|---|
| Katana | `M_Katana_Blade` (0) | `MI_Katana_Blade` | `M_Steel_Master` | blade, iron tsuba | `Steel Tint` (white = shipped; blued/bronze shifts). The hamon lives in BC + roughness, so a tint keeps it |
| Katana | `M_Katana_Fittings` (1) | `MI_Katana_Fittings` | `M_Steel_Master` | habaki, seppa, fuchi, kashira, menuki | `Steel Tint`: gold / silver / copper / dark |
| Katana | `M_Katana_Grip` (2) | `MI_Katana_Grip` | `M_Fabric_Master`, **Metal From ORM on** | ito, core (same), mekugi | `Colour` = the ito colour. The same windows keep their baked colour |
| Saya | `M_Katana_Saya_Lacquer` (0) | `MI_Katana_Saya_Lacquer` | `M_Fabric_Master` (Metal From ORM off unless metal sits in this slot) | lacquered body, cavity | `Colour` = lacquer colour (black, red, brown, blue...) |
| Saya | `M_Katana_Saya_Fittings` (1) | `MI_Katana_Saya_Fittings` | `M_Steel_Master` | koiguchi, kurikata, kojiri (horn: dielectric, ORM.B = 0) | `Steel Tint` |

Each instance gets its `_Base`: **10 new instances**, **no master change expected** (Metal From ORM exists).

**Conditions the design must meet for the Grip slot to work with 3 slots:**
- the shipped ito is **dark** (baked linear luminance ≤ 0.15 everywhere on the cord, AO kept out of BC) and the same is
  **light** (≥ 0.45), with nothing in between except mip blending at the window borders;
- the `Detail` map is normalised over the **ito texels only** (by island mask, not by luminance), like the Snow Flower
  sheath's marble;
- if the sheet wants **black (lacquered) same**, the keep-weight cannot separate it from a dark ito: that needs a 4th
  slot `M_Katana_Same` (one more draw call). Flagged as an open question.

### 5.3 Texture sizes

| Atlas | Size | Content | Reason |
|---|---|---|---|
| `T_Katana_Steel_{BC,ORM,N}` | **4096 x 1024** (fallback 2048²) | blade (both faces, mune, ha lands), habaki, seppa, tsuba, fuchi, kashira, menuki | A blade face is a 711 mm island that should not be cut (a seam through a polished blade and its hamon shows). At 2048² it maxes at **28 px/cm** along the blade; at 4096 wide it gets **56 px/cm**, at the **same memory as 2048²**. Measured need: blade on screen ≈ 18 px/cm in first person at 1440p, ≈ 43 px/cm in an inspect / armory close-up at ~30 cm; the hamon's nioi band (1-3 mm) and ashi need ≥ ~5 px/mm. qa_check tests power-of-two per dimension (read in `qa_check.py`), the Steel master has no Detail map, and N + ORM share one size for the ORM composite; Unreal's handling of the non-square chain is a gate (section 9). |
| `T_Katana_Grip_{BC,ORM,N}` | 2048² | ito ribbons (unique islands), core + same, mekugi, LOD2 tsuka shell island; **UV tile u 1..2** | ~250 cm² of visible wrap at ~80-100 px/cm (Snow Flower wrap 102 px/cm) |
| `Recolour/T_Katana_Grip_Detail16` | 1024² G16 | ito detail | square (5.1); Snow Flower precedent: wrap Detail at 1024 |
| `T_Katana_Saya_{BC,ORM,N}` | 2048² | lacquer body in **two lengths** (one ring seam near mid-length), horn fittings, cavity (hidden, ~6 % density), kurikata | ~760 mm long: two ~380 mm strips give ~50 px/cm along and across. The lacquer is smooth with a flat normal, so the ring seam is invisible if the variation is painted in continuous arc-length coordinates (gate: seam step ≤ 1 BC level and ≤ 0.01 roughness in a raking render) |
| `Recolour/T_Katana_Saya_Lacquer_Detail16` | 1024² G16 | lacquer detail | square |

Approximate memory: steel ≈ 11 MB, grip ≈ 11 + 2.8 MB, saya ≈ 11 + 2.8 MB: **≈ 39 MB** for both (the Snow Flower
pair is several times that). Only 8-bit sRGB reference copies of the Detail maps ship beside them, never imported.

Maps: BC sRGB (TC_Default), ORM linear (TC_Masks; R = **baked AO**, G roughness, B metallic; composite texture = its
own N, CTM_NormalRoughnessToGreen, as the pack does), N DirectX (green flipped on write; Flip Green **off** in
Unreal). Power of two, full mips. Renders only from the baked maps.

### 5.4 Finish recipe (what the maps carry)

- **Blade:** metallic 1. Shinogi-ji burnished (roughness ~0.08-0.12, slightly darker); ji polished-hazy (~0.18-0.25);
  hamon band lighter and rougher (~0.35-0.45, the frosted nioi), boshi in the kissaki following the sheet; a thin
  bright ha line. Pattern (suguha / notare / gentle gunome) from the sheet; generic, no named smith's style.
- **Fittings:** bright metal in the Fittings slot; tsuba iron (dark, low roughness variation, slight hammer texture in
  N) in the Blade slot.
- **Grip:** silk braid weave in each ribbon's parametric space; ray-skin nodules (normal + albedo) in the windows.
- **Saya:** glossy lacquer (roughness ~0.08-0.15, very low-frequency variation), horn with a fine lengthwise grain.

---

## 6. Sockets (sidecar; nominal values in Unreal cm)

All sockets are Empties named `SOCKET_<LOD0 node>_<name>`, written to `<name>.sockets.json` by `export_fbx` and
applied by `ue_import_sockets.py` (a LodGroup FBX loses FBX sockets; FBX sockets also arrive at scale 100). Rotation 0
unless stated; the builder computes final positions from the spec.

### 6.1 Katana

| Socket | Nominal location | Use |
|---|---|---|
| `Grip` | (0, 0, 0) | Pivot; right hand. Attach to the character's `hand_r` weapon socket |
| `OffHand` | (0, 0, -17.0) | Left-hand target on the tsuka (two-hand IK) |
| `BladeBase` | (0, 0, 8.8) | Blade centre line at the munemachi: hit-trace start |
| `BladeMid` | ≈ (1.9, 0, 44.3) | Centre line at half the arc: a two-segment trace Base -> Mid -> Tip follows the curve within ~4 mm (a single straight trace is up to 17 mm off) |
| `BladeTip` | ≈ (8.1, 0, 79.5) | The kissaki point. **Rotation = the blade tangent at the tip** (pitch ≈ 11°, sign through `ue_socket_transform`) so thrust FX point along the blade |
| `TrailStart` | ≈ (0.0, 0, 13.8) | Swing-trail ribbon start (~5 cm above the machi) |
| `TrailEnd` | ≈ (7.6, 0, 78.0) | Swing-trail ribbon end (~1.5 cm short of the tip, so the ribbon does not overshoot) |
| `CenterOfMass` | ≈ (0.3, 0, 17.0) | Computed from part volumes x densities. Unreal computes CoM from the hulls at uniform density (the tsuka hull would pull it far back): the README tells buyers to set the body's Center Of Mass offset to this socket for dropped-weapon physics |

### 6.2 Saya

| Socket | Nominal location | Use |
|---|---|---|
| `BeltMount` | (0, 0, 0) | Pivot: the obi station on the saya centre line (~110 mm below the mouth, mouth side of the kurikata). Attach to the hip socket. Rotation 0 (the local tangent there is only ~1.2° off; kept 0 to avoid a sign trap) |
| `Holster` | ≈ (-0.08, 0, -16.5), **rotation 0** | Where the katana's `Grip` sits when sheathed (SnapToTarget, zero relative transform) |
| `Mouth` | ≈ (0, 0, -11.0) | Koiguchi plane on the blade centre line. The draw starts along its -Z (within 0.5°) |
| `DrawPivot` | ≈ (373.0, 0, -7.7) | Centre of the blade arc (R ≈ 3.7 m). A clean draw = rotate the katana about this point (about the socket's Y axis) by arc-length / R until ≈ 11.5° (blade + habaki out). Far from the mesh by design; sockets do not affect bounds |

---

## 7. Collision

### 7.1 Hulls

`UCX_<LOD0 node>_NN` (the pipeline renames with the LodGroup), ≤ 32 vertices each, **built by the builder's own
code** (convex hull of the part's vertices dilated by 0.2 mm, reduced by keeping the hull of a support polygon, so
every LOD0 vertex stays inside), not by `make_ucx_hull`'s whole-object collapse decimate.

| Katana hull | Covers | Why split |
|---|---|---|
| 00 | habaki + blade arc 0-25 % | a curved blade in one hull would fill the 17 mm sagitta on the mune side; in four chords the phantom is ≈ 1.1 mm |
| 01, 02 | blade 25-50 %, 50-80 % | |
| 03 | blade 80 % - tip (kissaki) | |
| 04 | seppa + tsuba | a disc; merged with the habaki it would make a cone of phantom volume |
| 05 | tsuka (fuchi .. kashira) | |

| Saya hull | Covers |
|---|---|
| 00..03 | body in four chords along the arc (koiguchi in 00, kojiri in 03); phantom ≈ 1.2 mm per chord |
| 04 | kurikata |

Gates: every LOD0 vertex inside a hull (engine round trip: worst vertex inside, as on the Snow Flower), hull geometry
round-trips through Unreal's own FBX export.

### 7.2 While sheathed

The sheathed blade lies inside the saya hulls (hulls are solid). As on the Snow Flower: set the katana to
**NoCollision or QueryOnly while sheathed**, restore on draw. Stated in both READMEs.

---

## 8. Sheathed fit and its verification (the Snow Flower method, adapted to an arc)

### 8.1 Construction (saya build, `fit` stage)

1. **Read the shipped katana FBX** (exact bytes; record its sha256 and refuse to continue if the katana is re-exported
   later; the saya then rebuilds). Import all three LODs; add edge samples every 0.5 mm (the Snow Flower lesson: with vertex
   support alone a long LOD2 edge came within 0.24 mm of the cavity wall against a 0.6 mm design clearance).
2. **Unbend:** map every point to arc coordinates about the draw centre C: s = R·angle, ρ = |p_xz - C| - R, y. In that
   frame the arc draw is a straight translation in s, so the Snow Flower's straight-sweep support code
   (`suffix_extremes`, `swept_support`, `support_polygon` in `shv4_fit.py`) applies as is. Copy those functions into
   `Scripts/Katana/` (never import or edit the Snow Flower files).
3. **Cavity** = the swept support of all LODs below the mouth + clearance (design 0.6 mm on the blade; the habaki
   section **0.15 mm**, the friction fit that holds a real katana in its saya), 16-sided support polygon per station,
   mapped back to the arc. With non-increasing sections the cavity hugs the blade.
4. **Outer body** = cavity + walls (design: ≥ 3 mm on the flats, ≥ 3.5 mm at the ha and mune), smoothed into the
   sheet's outer section; the kojiri closes ≥ 3 mm past the tip.
5. **Seat:** the koiguchi top face sits **0.3 mm** below the lower seppa; the habaki is entirely inside the koiguchi.
   `Holster` = the katana frame expressed in the saya frame; zero rotation by construction.

### 8.2 Gates (on the exported FBX bytes of both, katana placed from the exported sidecar's `Holster`)

| # | Gate | Threshold |
|---|---|---|
| F1 | Intersecting triangles, every saya LOD x katana LOD (9 pairs) | **0** |
| F2 | Blade clearance (vertex to saya surface) | ≥ 0.3 mm |
| F3 | Habaki in the koiguchi | 0 intersections, clearance 0.1-0.5 mm |
| F4 | Hilt (seppa / tsuba) clearance to the saya | ≥ 0.2 mm |
| F5 | Enclosure: rays ±X, ±Y from every blade vertex hit a cavity wall facing them | 0 failures |
| F6 | **Arc draw**: rotate about the **exported** `DrawPivot` in 10 mm arc steps (and a final 1 cm pass) until the tip clears | 0 intersections at every step, all 9 pairs |
| F7 | Visible seat gap (front and edge-on silhouettes of the Fittings slot over the koiguchi; Snow Flower check 6) | front max ≤ **1.0 mm**, side max ≤ 1.0 mm (flush seat; the Snow Flower's 5 / 10 mm limits were for a forced design) |
| F8 | Minimum wall | ≥ 2.0 mm in the visible body, ≥ 1.5 mm anywhere, every LOD |
| F9 | Holster and DrawPivot from the exported sidecar vs the fit | ≤ 0.001 mm |
| F10 | Katana bytes = the shipped katana's sha256 | equal |
| F11 | Tip to cavity end | ≥ 3 mm |
| F12 (info) | A **straight** draw | reported (expected to collide: proves the arc is needed and documents it) |
| F13 (Unreal) | In-engine: katana attached at `Holster`; its sockets land where Blender put them | ≤ 0.001 cm |

Outputs: `fit_verify.json`, X-ray section sheet at 7+ stations, cutaway renders (mouth, mid, tip), the arc-draw strip.

---

## 9. Export, QA and Unreal verification

### 9.1 Export (pipeline only)

```
py Scripts/pipeline/lock.py claim Katana --agent claude --blend Assets/Katana/Katana.blend
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b Assets/Katana/Katana.blend --factory-startup --python Scripts/pipeline/qa_check.py -- --objects SM_Katana_LOD0,SM_Katana_LOD1,SM_Katana_LOD2 --budget 25000 --texel <measured aggregate> --require-uv1 --json WorkFiles/katana/qa_katana.json
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b Assets/Katana/Katana.blend --factory-startup --python Scripts/pipeline/export_fbx.py -- --objects SM_Katana_LodGroup --out Exports/Katana/SM_Katana.fbx --kind static
```
Same for `Assets/Katana/Saya.blend` -> `Exports/Katana/SM_Katana_Saya.fbx` with `--budget 12000`. Texel target: each
build reports per-atlas density (steel ≈ 56, grip ≈ 80-100, saya ≈ 50 px/cm; hidden islands 0.06-0.25x) and sets
qa's aggregate target to the measured value ±25 %, as the Snow Flower did. UV0: steel u 0..1, grip u 1..2; UV1 a
separate authored non-overlapping pack (Unreal regenerates channel 1 on import, pack setting kept).

### 9.2 Unreal (UE 5.8.3, `ShurikenValidation.uproject`, new content path per run)

Adapted **copies** of `WorkFiles/SnowFlower/v4/UnrealCheck/` and `UnrealCheck_Sheath/` in `WorkFiles/katana/UnrealCheck/`
(the Snow Flower harness stays untouched), one commandlet at a time behind the machine guard
(`WorkFiles/shuriken/UnrealCheck6/wait_unreal_free.ps1`), none left running, the user's editors never touched.
Pass 1 imports both FBX + sidecars (one save); pass 2 is a fresh reload. Gates:

LOD count 3 and triangles equal in Blender / FBX / Unreal · hull counts 6 and 5 · sockets 8 and 4 at scale 1,
outered to the asset (fresh process) · bounds · screen sizes from the sidecar · lightmap index 1 on every LOD · slot
names · Nanite off · texture flags persisted (BC sRGB, ORM TC_Masks + composite, N TC_Normalmap flip-green off, full
mips) **including the 4096 x 1024 steel maps' built size and mip count** (fallback to 2048² if they fail) · every LOD0
vertex inside the engine's hulls · Unreal's own FBX export round-trips triangles, positions and hulls · UV1 overlap 0 ·
same sha256 bytes everywhere · Holster gate F13 · 0 warning/error lines.

---

## 10. Pack materials integration (Finalise phase)

1. `py -3 -B Scripts/unreal/materials/np_lock.py claim katana-wf` (wait if held; never force a live holder).
2. Recolour maps: `maps/make_katana_recolour_maps.py` (new; Grip Detail over ito texels only, Saya lacquer Detail over
   lacquer texels only, writes `Exports/Katana/Textures/Recolour/*_Detail16.png` + `recolour_maps.json`), then
   `maps/derive_constants_katana.py` (a copy of the flashbang/heels script with this group's paths) ->
   `recolour_constants.json`.
3. `material_spec.json`: add items `Katana` and `Katana_Saya` (slots of 5.2, `texture_kinds`, `orm_texture_settings`,
   `Metal From ORM` true on `MI_Katana_Grip`), 10 instances, and a `changes_v7_katana` note. Additions only.
4. `NP_OWNER=katana-wf bash Scripts/unreal/materials/run_build.sh katana_<mmdd>` (preflight, maps_check, import,
   clean, build, assign, verify). Then `render` for the UV-plane captures of the two recolourable parts.
5. Gates (pack's own): default capture = shipped BC (p99.9 ≤ 1-2 levels); recolour stress 10 colours incl.
   `FFFFFF FF0000 0000FF F2E8D5 000000` on the ito and the lacquer; plateau, mip drift ≤ 1 %; **new for the Grip:
   the same windows keep their baked colour within 2 levels under every stress colour**; dump comparison shows every
   other instance, master, function, mesh and texture unchanged; dependencies = own textures + Default.
6. Release the lock. Write `Exports/Katana/MATERIALS_README.md` (how to change each colour, what Steel Tint can and
   cannot do, reset, Detail16 note).

---

## 11. Attaching to the character (game side; needs the user's go)

The asset frames never change; the character side absorbs orientation, once:

- Skeleton sockets on the player skeleton (authored in the game project, not by this build): `Katana_R` on `hand_r`
  (the katana's `Grip` snaps here), `Saya_L` on **`pelvis`** for the hip carry (the obi moves with the pelvis, not the
  thigh). The socket rotations are tuned once in Unreal on the MetaHuman with a grip preview: the `hand_r` rest frame
  is measured there, not assumed. `OffHand` is the left-hand IK target.
- Default carry: **left hip, edge up, through the obi** (the kurikata sits on the outer, omote side). A back carry
  only needs another skeleton socket (`Saya_Back` on `spine_05`) using the same `BeltMount`.
- Sheathe: collision off/QueryOnly, attach the katana at the saya's `Holster` (SnapToTarget). Draw: detach, follow the
  arc about `DrawPivot` (or simply hand-attach on the montage notify), attach `Grip` to `Katana_R`, restore collision.
- Character QA (guidelines 12.8, later): katana draw, scabbard vs cloak, seiza, LOD transitions, many characters.

---

## 12. Look acceptance (the design sheet is the reference)

- Orthographic front / side / top renders of the **shipped FBX with the shipped PNGs** vs the sheet's views at the
  sheet's scale: silhouette IoU ≥ 0.97 per view; mean width error per band (kashira, tsuka, tsuba, habaki, blade
  thirds, kissaki; saya mouth, body, kojiri) ≤ 0.5 mm. Same numbers drive both, so anything larger is a bug.
- Diamond count / pitch / window size equal to the sheet; hamon pattern and boshi as drawn.
- **Blind tests** (the CLAUDE.md bar): (a) image pairs sheet vs ours: the judge must not pick ours on design; (b) a
  "real or game asset" judge with crops of real public katana photos at matched framing (read-only research, no
  downloads into the repo) for the reads the sheet cannot judge: wrap, hamon, polish, lacquer. Stop early and show the
  user if a round fails decisively.
- Review set: hero 3/4, first-person 3/4 crop at 50 cm, third-person at 3 m, the tsuka at 3x, kissaki + hamon raking,
  sheathed pair, cutaways, LOD strip and switch frames, wireframe.

---

## 13. Build order, files and locks

| Phase | Output | Notes |
|---|---|---|
| 1 Study (other role) | design sheet + `katana_spec.json` (every dimension, pattern, palette) | the reference for everything |
| 2 Katana build | `Scripts/Katana/build_katana.py` (stages geo, uv, maps, bake, game, export) + `katana_*.py` modules; `Assets/Katana/Katana.blend` | takes asset lock `Katana` (agent claude) |
| 3 Saya build | `Scripts/Katana/build_saya.py` (stages fit, geo, uv, maps, bake, game, export, verify) + `saya_*.py`; `Assets/Katana/Saya.blend` | reads only the **exported** katana; refuses on a sha mismatch |
| 4 Unreal check | `WorkFiles/katana/UnrealCheck/` copies; `verification_summary.json` | |
| 5 Materials | section 10 | lock `katana-wf` |
| 6 Docs + renders | `Exports/Katana/README.md`, `MATERIALS_README.md`; `Renders/Katana/` | |
| 7 Review + finalise | blind tests; `showcase/Katana/` via the read-only `studio.py` in the cardshop worktree; one row under **"Throwables and weapons"** in `showcase/ASSET_LIST.md` (re-read just before editing) | finaliser releases lock `Katana`; `check_exports_frozen.sh` compared against its output at the start |

Rebuild-from-nothing scripts (`run_all_katana.sh`, `run_all_saya.sh`) as on the Snow Flower. Scratch (bakes,
caches) stays under `WorkFiles/katana/` and out of git. Every script uses absolute paths from a `ROOT` constant.

---

## 14. Risks

| Risk | Mitigation |
|---|---|
| The ito still reads as a flat pattern | Geometry crossings, twists and lift are required (section 4); an early look gate on the tsuka alone, before the blade is finished; stop and show the user if it fails |
| Non-square steel maps trip a tool | qa and the Steel master checked in code; Unreal gate on built size and mips; fallback 2048² (blade at 28 px/cm) |
| Keep-weight leaks (ito colour onto the same, or the same left untinted where it should tint) | luminance separation required (5.2); the "windows unchanged under stress" gate |
| Curvature not a single arc in the sheet | approximate within 0.3 mm or switch the fit to a general sweep along the sampled path |
| Katana re-exported after the saya | sha guard in the saya fit stage; rebuild the saya |
| LOD2 too early in third person | measured screen sizes (2.3) |
| Another chat holds Unreal or the materials lock | wait and retry; never force a live holder |
