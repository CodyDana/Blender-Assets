# Armory Plan v2: the gallery (follows armory3)

**Date:** 2026-09-26 (v2). **Supersedes** the kura plan, kept as `ARMORY_PLAN_v1_kura.md`. Most of its
engineering still carries over (grid, slot system, material rules, gates, per-item seating). This version changes
the **look and the layout** to the user's references.
**Status:** PLAN ONLY. Nothing is modelled, rendered, imported or built. Under the stop-before-expensive-work rule,
phase P1 (the greybox) does not start until the user says go.
**Governing references (the user's own originals, 2026-09-26):**
- `reference/armory3_reference.png` sets the **layout**: the top-down plan, cases 1-10, windows, platform and steps.
- `reference/armory3_reference2.png` sets the **look**: the eye-level view from the door, with materials, light and
  casework.
- Where the two disagree, the top-down wins on position and the view wins on look (see 3.2).
- `armory1` and `armory2` in `reference/` are superseded and are not used.

**Companions (this folder):** `ITEM_INVENTORY.md` (sizes, sockets and needs for every item; unchanged);
`ARMORY_LAYOUT.svg` + `ARMORY_LAYOUT.txt`, both drawn by `armory_layout.py` from one table.
**Flags:** MEASURED, SOURCED, DERIVED and ESTIMATE, as in v1. Every day count is an ESTIMATE.

---

## 1. Summary

| Item | Value |
|---|---|
| Style | A **dark timber museum gallery**. Black-lacquer display plinths with gold trim and a warm under-glow, glass vitrines, and lit cream wall panels between dark posts. High lattice windows throw golden-hour sun shafts across a dark plank floor. A raised rear platform holds the hero sword in front of a painted panel |
| Shape | **One storey**, 8.0 x 12.0 m interior, as drawn in armory3. Flat coffered ceiling at +480 with downlights. One door in the south wall |
| Grid | 100 cm primary, 25 cm sub-grid, heights on 25 cm (steps on 15 cm). Walls 30 cm |
| Layout | Three glass cases on the centre axis (1, 2, 3). Three side cases on each long wall (4, 5 west; 6, 7, 8 east). Lit wall display panels (9) along both long walls. A rear platform at +60, reached by 4 steps, holding hero case 10 between two vases, with a long-weapon rack in each corner |
| Contrast rule (changed) | **Dark room, bright cases.** The room may be dark, but every surface an item touches or is seen against is pale, lit or red: linen decks, cream lit panels, red cloth. Black lacquer and gold stay on the outside of the plinths |
| Kit | **22 architecture pieces + a casework family** (5 plinths, 5 glass hoods) **+ 5 inner-mount families**, 7 dressing props |
| Light | Golden-hour sun through the high windows. Every case lit inside. Warm LED under-glow on plinths and steps. Downlights. Lanterns. Presets: **Gallery** (default), **Golden Hour** (the armory3 look), **Inspection**, **Night** |
| Cost | **49 engineering days** (ESTIMATE), **about 59 with 20 % contingency**. First walkable room with every finished item in its case lands at **day 31** (end of P3). Leaner path: about 25 days. The greybox gate is **3 days** |
| First step | P1 greybox in Unreal: blocks, every finished item at true scale in its case proxy, cameras, 11 pass/fail gates. **User gate** |

**What stays from v1:**
- the 8 x 12 m one-storey shell, the grid, 30 cm walls, the south door and high windows;
- the data-table slot system (`BP_DisplaySlot`, `DT_ArmoryItems`, "Reseat all");
- the per-item seating by socket, the never-mirror rule and the pack material rules;
- the new `ArmoryLab` project, the gates and the phase gating.

**What goes:**
- the white-plaster kura interior, the earth entry floor, step stone and central airing platform;
- the open roof trusses, the kannon doors and the modelled exterior door face (now optional P7);
- the target post (optional P7; its kunai-and-tag pairing moves into case 1).

---

## 2. Reading the references

### 2.1 What armory3 fixes

| From | Fixed for the plan |
|---|---|
| Top-down | 8.0 x 12.0 m, single storey, door 150 x 200 centred on the south wall, windows high on both long walls (sill +350), 1 m grid, the ten numbered displays and their places, the lanterns, the vases and the rear platform with its steps |
| View | Dark stained plank floor laid along the axis. Near-black timber posts and beams with cream infill panels. Black-lacquer plinths with a thin gold band, a gold emblem plate on the front and a warm LED line under the base. Glass vitrines on thin frames. Small label plates inside each case. Lit niches with red tassels. Shoji-style lattice windows with sun streaming in. A coffered ceiling with downlights. Red plum branches in black vases. Square paper floor lanterns. A painted pine panel behind the hero sword. Crest banners |

### 2.2 Where the two images disagree, and the call made here

| Point | Top-down | View | Plan follows |
|---|---|---|---|
| Kasa position | Right-mid case 6 | Right-mid, plus a second hat on the centre axis | Top-down: one kasa, case 6 |
| Items on the rear platform | One hero katana (10) | One katana on a low stand, plus sword racks at the back corners | Both: hero case 10 plus corner racks |
| Room proportion | 8 x 12 m | Reads wider (about 12 m) | Top-down, 8 m. The width is tested at G0 (D3) |
| Bay 7 | "Boots" | Black boots with red soles | Heels, the line's actual footwear (D5) |
| "Scrolls" in case 1 | Listed | Two rolled cream-and-red scrolls | The **paper tags**, shown flat face-out. The print is the product. A rolled scroll would be a new item |
| Tanto, extra katanas, wall weapons | Listed as "kunai, tanto, etc." | Many | Growth slots. Only the kunai exists today (section 12) |

### 2.3 What the references show that the plan must not build

| Shown | Why not | Instead |
|---|---|---|
| The **flower-in-a-ring crest** on every plinth front and on the banners | It reads as a real family crest (kamon) and would be an IP and cultural risk in a sold kit or a shipped game | An **original emblem**, designed for the game, with a similarity check against common kamon (D7), or blank gold plates |
| Black items on **black decks** (the smoke bombs and case 5's kunai) | They fail the contrast gate: near-black cloth on black lacquer | Pale linen decks and red cloth. Black stays on the outside of the plinth |
| A **specific painting** | Must not copy a known work | An original pine panel, made for this room, with no signature, seal or text |
| Legible label text | Text policy (SHOWCASE_PLAN 6.1) | Label plates carry only our own item names, or stay blank |

---

## 3. The room

**Updated 2026-09-27 (building stage, user decisions): 12.0 x 16.0 m interior (was 8 x 12), a 4.0 m wide entrance
(was a 150 x 200 door), the reference-2 dressing. Fix round f1 (same day): the entrance is 3.65 m tall, windows 1.45 m,
vestibule posts, dark top-lit niches, black lacquer decks, rear alcoves moved outboard (see BUILD_NOTES f1). Fix round f2:
wall bays over a dark dado with lit cream backs, 45 cm jamb posts, a thin matte sill beam, a low sun plus an interior
window fill (patches on both halves of the floor), long 20 cm floor boards, a sill vase in every bay, LED-ringed coffers
and lattice panels over the centre bays (see BUILD_NOTES f2). Everything below is the kit AS BUILT (`Scripts/armory/build_armory_kit.py`,
`build/layout.json`); the drawing is generated from layout.json by `armory_layout.py`. Build notes: `build/BUILD_NOTES.md`.
The 8 x 12 m v2 table is kept in `armory_layout_v2_8x12.py`.**

### 3.1 Frame and datums

Origin: interior south-west corner at floor level. X across (0-12.0 m), Y along the axis (0-16.0 m, north = +Y), Z up.
The entrance is in the south wall. Walls are 30 cm thick, with the pivot on the inner face (unchanged from v1).
Blender to UE: (x*100, -y*100, z*100), yaw = -rot_z.

| Datum | Z (cm) | Note |
|---|---|---|
| Floor | 0 | One level, dark walnut planks along Y, 20 cm wide x 4 m long with one staggered butt joint (f2), satin-gloss (4 m tile, four UV-offset 2 x 2 m variants) |
| Entry sill beam / threshold | +6 / +8 | Sill beam X 380-820 at Y 256-274 (f2: 18 cm deep, plain matte timber; was a 30 cm lacquer beam); threshold beam across the 4 m opening |
| Rear platform top | +60 | Y 1345-1600, full width |
| Steps | 4 risers x 15 | X 400-800, Y 1270-1345, LED nosings |
| Wall bays | Floor to +240 (hall; dado to +85, counter +85-+90); +60 to +250 (platform bays, 1.90 m, counter +100-+105, under the sill ledge underside +254.9) | f2: display bays over a dark dado: a black lacquer cabinet front (door panel, brass split line, toe kick), a projecting lacquer counter (29.4 cm deep) with a brass nosing, a cream back board (#A68D69, not emissive) lit by a warm downlight lens under the head 20 cm off the back, brass pegs at +135 / +170 (empty), both long walls |
| Sill ledge | +259 to +264 | 33.5 cm deep, under every side window; vases and caddies stand on it |
| Side windows | sill +265, head +410 | 150 W x 145 H clear, f2: 9 muntins and 3 rails (panes 14.2 x 34.3 cm; was 11 muntins, 1 rail), one per 2 m bay on both long walls (8 per side), all open; a black vase with a bushy plum spray (0.88 m wide, 0.72 m over the vase) on the sill of every bay |
| Ranma band | +421 to +443 | Dense lattice over each window, square-grid transom under the ceiling |
| Ceiling | +480 | 2 x 2 m dark timber coffers, each with a warm LED line round the inner lower edge of its ring (f2) and a round downlight can (f2: 18 cm brass trim, 14 cm body, 16 cm deep, lens at +463.5); 4 m cross beams every 2 m (40 cm deep) with warm LED edge lines; 30 cm ribs along the axis on X 2/4/6/8/10 (a coffer grid); six ornamental lattice panels (gold backlight) on the centre line X 400-800 at Y 800-1000, 1200-1400 (f2) and 1400-1600 (lattice coffers carry no downlight) |
| Eaves plate | +500 | Top of the upper wall |

### 3.2 Plan

| Feature | Extent (m) | Note |
|---|---|---|
| Entrance | X 4.0-8.0, 3.65 m tall, clear | Heavy 30 x 54 cm posts and a 40 cm lintel (+3.65-+4.05), lit ranma above (+4.10-+4.62); sliding lattice leaves (3.65 m) parked open on the inner face (X 2.05-3.95 and 8.05-9.95); runner mat X 5.2-6.8, Y 0.14-2.54; floor lanterns (f2: plain open top frame, a glow picture on each pane, hot core to amber rim) at (3.90, 2.25) and (8.10, 2.25); f2 jamb posts (45 x 30 cm, full height, black iron straps and studs) X 3.77-4.22 and 7.78-8.23 at Y 0.87-1.17: reference 2's door posts at the frame edges |
| Side windows | Y 0.25-1.75 + 2k (k = 0-7), both long walls | All open. f2: the sun, 18 deg up, heading 35 deg, lays patches over X 6.70-10.00 (16.5 % of the hall floor X 1.2-10.8, Y 2.6-12.7); an interior-only window fill, 30 deg up, heading 37 deg (linked to the room; Unreal: a second directional light on its own lighting channel), lays parallel patches over X 3.70-5.35 (11.1 %). Both stream from the WEST windows toward the entrance, as every patch in reference 2 does |
| Wall bays | West X 0-0.294, east X 11.706-12, Y 1-13 (12 bays per side, floor to +2.40, counter +0.85); one more per side on the platform (Y 14.07-14.93, 1.90 m, +0.60-+2.50, counter +1.00) | Empty (fixtures only). The north-wall corner niches are gone (the rear alcoves cover those corners) |
| Centre cases (X 6.0) | 1 (L 1.8 x 1.3, plinth 0.50, glass 0.95) at Y 3.70; 2 (M 1.8 x 1.2, 0.70 + 0.55) at Y 7.60; 3 (LN 1.6 x 1.0, 0.45 + 0.75) at Y 11.30 | Proportions fitted to reference 2 through the C1 camera |
| West cases (X 1.75, facing the aisle) | 5 (S) Y 4.10; 4 (Tall) Y 6.60; G1 (S) Y 9.10; G3 (Tall) Y 11.60 | G = EMPTY growth slot. f1: Tall = plinth 0.50 (25 cm emblem front and back) + glass 1.70; every deck is black lacquer (was oxblood cloth) |
| East cases (X 10.25) | 8 (S) Y 4.00; 7 (S) Y 6.30; 6 (Tall) Y 8.80; G2 (Tall) Y 11.40 | |
| Rear platform | Y 13.45-16.0 | Hero TABLE 10 (2.4 x 0.9, two tiers, top +0.52, no glass) at (6.0, 14.85); painting 2.4 x 2.3 at X 4.8-7.2, Z 1.5-3.8 (f2: warm beige paper #A88C66, near-black ink) with dark screens X 4.1-4.8 / 7.2-7.9; large plum vases at X 4.20 / 7.80 (Y 15.35; f2: two 0.90 m spray cards at 60 / 120 deg); platform lanterns (3.55, 15.10) / (8.45, 15.10); rear alcoves X 1.2-3.0 and 9.0-10.8 (f2: softly backlit cream panel with two warm spots under the head, EMPTY upright rack on a tansu, lattice screen above); banners (0.55 x 2.2 m cloth, +2.40-+4.60) hung from the ceiling at (0.78, 13.13) / (11.22, 13.13), facing the entrance; the user's emblem (11.6 cm) on the top riser at X 6.0; LED bay posts X 4.0 / 8.0; heavy posts X 3.30 / 8.70 at the platform front; lanterns on pedestals at (3.30, 13.0) / (8.70, 13.0) |

```
            NORTH (painting wall)     interior 12.0 x 16.0 m; one char = 25 cm across, one row = 50 cm
      X: 0m      2m      4m      6m      8m      10m     12m
         +------------------------------------------------+   Y 16.0
         w====rrrrrrrr===WWWppPPPPPPPPppWWW===rrrrrrrr==vvw
         wvv==rrrrrrrr=LLLWW=##########=WWLLL=rrrrrrrr==vvw
         wvv===========LLLWW=#####10###=WWLLL===========vvw
    14.0 wvv=================##########=================99w
         w============oo====================oo==========vvw
         wcvBBB=======LLL=ssssssseesssssss=LLL=======BBBvvw
         wvv          LLL ssssssssssssssss LLL          vvw
    12.0 wvv  ######                            ######  99w
         w99  ###G3#          ########          ######  vvw
         wvv  ######          ####3###          ###G2#  vvw
         wvv  ######          ########          ######  vvw
    10.0 wvv                                            99w
         w99  ######                            ######  vvw
         wvv  ###G1#                            ######  vvw
         wvv  ######                            ###6##  vcw
     8.0 wvv  ######          ########          ######  99w
         w99                  ####2###                  vvw
         wvv  ######          ########                  vvw
         wvv  ###4##                            ######  vvw
     6.0 wvv  ######                            ###7##  99w
         w99  ######                            ######  vvw
         wcv                                            vvw
         wvv  ######                            ######  vvw
     4.0 wvv  ###5##          ########          ###8##  99w
         w99  ######          ####1###          ######  vvw
         wvv  ######          ########          ######  vvw
         wvv             __________________             vvw
     2.0 wvv            LLL   ........   LLL            99w
         w99                  ........                  vvw
         wvv             oo   ........   oo             vvw
         wvv             oo   ........   oo             vcw
     0.0 wvv      dddddddd____........____dddddddd        w
         +----------------                ----------------+   Y 0.0  (entrance 4.0 m wide x 3.65 m, X 4.0-8.0)
                                  ^ C1 at Y -1.51, +3.42, 24.5 mm, looking north
```

Key: `#` case (label = display number, G = empty growth slot), `=` platform, `s` steps, `9` wall bays (dado, lit cream back), `r` rear alcoves,
`p` screens, `P` painting, `B` banners, `L` lanterns, `W`/`v` vases, `c` caddies, `o` posts, `.` runner, `_` beams,
`d` parked door leaves, `w` windows, `e` the emblem on the top riser. Full key and the SVG: `ARMORY_LAYOUT.txt` / `.svg`.

### 3.3 Circulation

- **Aisles** between the side cases (X 1.2-2.3 and 9.7-10.8) and the centre row (X 5.1-6.9) are **2.8 m** (DERIVED
  from the table). Behind the side cases, 0.906 m to the wall-bay counters (f2). Centre gaps: Y 4.35-7.0 and 8.2-10.8.
- The steps lead to the hero table; the walk continues across the platform front between the heavy posts, the hero
  table and the platform lanterns to both rear alcoves.
- From the runner to the aisles the walk passes between each jamb post (Y 0.87-1.17) and its floor lantern
  (Y 2.02-2.48), or along the post's inner side (f2: X 4.22 / 7.78) toward the runner.
- `Scripts/armory/walk_check.py` (Manny capsule r 35 cm vs the UCX hulls, 45 cm step-up) passes 17 routes (f2: both sides of the entry mat past the jamb posts), including
  the courtyard start along the path through the entrance and from outside the gate; both control routes (into case 1,
  into the stone lantern) are blocked (`build/walk_check.json`).
- The camera-boom note of v2 still applies in the 2.8 m aisles (shorter boom in an armory volume).

| Sightline | From | To | Proves |
|---|---|---|---|
| S1 axis | Eye +160 at Y 1.0 | Hero table top front (+1.12 at Y 14.55) | DERIVED: clears case 1 by 3.1 cm, case 2 by 9.5 cm, case 3 by 1.7 cm (the reference's tall glass on case 1 makes this marginal; lower G on case 1 if items need more margin) |
| S2 case reads | Each aisle | Every case front | Items read through glass at 1-2 m (G0-2, G0-10) |
| S3 walls | Centre aisle gaps | Wall niches | Lit niches read as a continuous gallery band |


### 3.4 Site: the courtyard garden and the scenery (exterior stage, 2026-09-27)

Built by `Scripts/armory/build_armory_exterior.py` (pieces `SM_AKX_*`, Blender collections `KitExterior` /
`AssemblyExterior`, same QA, export and layout.json as the room); textures by `Scripts/armory/make_exterior_textures.py`
(`T_AKX_*`). Drawing: `ARMORY_SITE.txt` / `.svg` (generated by `armory_layout.py` from layout.json).

| Feature | Extent (m) | Note |
|---|---|---|
| Courtyard | X -4..16, Y -13..-0.3 (20 x 12.7), ground Z 0 | Raked gravel (ridges 6.25 cm apart, running across the axis), walled on three sides |
| Enclosure | South wall Y -13 with the roofed gate X 4.55-7.45 (2.38 m clear, on the axis); side walls X -4 / 16 from Y -13 to +3 | Plaster on a stone base, dark timber cap, tiled coping, top +2.05; piers at the corners and ends |
| Approach | Landing X 3.7-8.3, Y -1.82..-0.42 (+0.06); ishidatami strip X 5.4-6.6, Y -4.9..-1.9; 11 stepping stones Y -5.45..-12.05 | Everything on the path is under 8 cm (walkable) |
| Garden | Stone lantern (8.35, -7.3); stone basin (3.35, -5.9); moss mounds with raked rings (1.9, -9.6), (11.4, -9.9); rocks; 10 clipped shrubs | |
| Trees | Black pines (1.2, -3.6), (9.5, -10.16) (f1: turned 90 deg, canopy clear of the south wall); red maples (11.9, -6.4), (13.8, -11.0); green maple (-1.9, -8.2) | Collision on the trunks only |
| The hall outside | Hipped tile roof, eaves 1.0 m out (X -1.3..13.3, Y -1.3..17.3), 26 deg, eave top +4.70, ridge +8.26; stone foundation band +0.46; timber posts every 2 m, plaster band under the eaves, window rails | f2 sun (18 deg up, heading 35 deg): the eave soffit edge (+4.52, 1.0 m out) shades the outer wall face down to +4.12, 2.3 cm above the clear window heads (+4.10), so the whole opening takes the sun; the interior window fill is linked to the room and ignores the roof |
| Scenery | Tree-line cards 24 x 14 m on X -10, X 22 and Y 26, 48 x 20 m on X -30, X 42 and Y 46, plus SW and SE on Y -48; hills ring r 170 m (10-34 m high), mountains ring r 720 m (70-250 m) | Emissive, cast no shadow; the gate opens south onto the meadow, hills and mountains |
| PlayerStart | (6.0, -10.4), facing the entrance (+Y) | layout.json `player_start`; the player walks in through the garden |

---

## 4. The look: materials and palette

**Contrast rule.** The line is near-black (`ITEM_INVENTORY.md` section 2).
- The room can be dark because the **case interiors and wall panels are the backdrops**, not the room.
- Every item-contact or item-backdrop surface is pale linen, cream lit panel, pale hinoki or red cloth.
- Black lacquer and gold appear only on plinth exteriors, frames and architecture.
- G0-1 measures item contrast against its **case interior**.

| Surface | Colour (ESTIMATE, tuned at G0-1) | Where |
|---|---|---|
| Plank floor, dark stained | `#3B2B20` | Floor, steps |
| Timber, near-black | `#221A15` | Posts, beams, nuki, window lattice, frames |
| Black lacquer | `#15120F`, clear-coat | Plinth exteriors, corner-rack carcasses |
| Gold / brass trim | `#B08A4A`, metallic | Plinth bands, emblem plates, glass-frame edges, lantern frames |
| Cream panel (lit) | `#DCCDAF` | Wall-panel backs, case back panels, ceiling coffers |
| Linen deck | `#D8CDB8` | Case decks under steel, bombs and the fan |
| Red cloth / tassel | `#8E1F1F` | Heel tiers, sword-kake cushions, tassel dressing (recolourable) |
| Pale hinoki | `#D8BE93` | Inner mounts: tray, kake arms, sanbo, fuda stand, form posts |
| LED / lantern light | 2700 K | Under-glow lines, lantern paper |

**Masters.** The v1 rules stand:
- New masters are added to `material_spec.json` under `environment` and built by the `np_*` builder.
- The frozen pack masters are never edited: dumps stay byte-identical and 63 of 63 frozen exports hold.
- Cloth and iron use MIs of the existing masters on unique UVs.

| Master | New or reused | Used for |
|---|---|---|
| `M_AK_Wood_Master` | NEW | Plank floor (tiling), timber trim sheet (4K), **black lacquer with clear coat**, pale hinoki for mounts |
| `M_AK_Plaster_Master` | NEW | Cream panels and coffers. Albedo capped at 0.80. Vertex-colour grime |
| `M_AK_Glass_Master` | NEW | Vitrine glass: Substrate thin translucent, low roughness, a faint edge tint. One switch to render the pane invisible for macro cameras (section 10) |
| `M_AK_Emissive_Master` | NEW | LED strips, lantern paper, lit panel glow. Intensity in nits, not a bright-emissive-as-light trick (the Lumen noise note from v1) |
| `M_AK_Decal_Master` | NEW (DBuffer) | Floor wear, soot above lanterns |
| `M_Steel_Master` | REUSED, MI | `MI_AK_Brass` (Steel Tint toward brass; confirm the tint range reaches brass, else a gold mode in `M_AK_Wood_Master`'s trim), iron hardware |
| `M_Fabric_Master` | REUSED, MI | Linen decks, red cloth, banner cloth, mannequin cover. Recolour constants per MI (about 0.25 day each) |
| `M_PaperInk_Master` | REUSED, MI | Label plates (blank or our own item names) |

---

## 5. The displays: one for every item

**Case family (F0, new).** One glass case = a black-lacquer **plinth** plus a separate **glass hood**. Hiding the
hood per camera is the reason they are separate meshes.

- Plinth: gold band, an emblem plate on the front, and an under-glow groove.
- Hood: five panes in a thin brass frame.
- Inside: pale decks and the v1 inner-mount families (F1 tray, F2 kake, F3 form post, F4 plinth and tiers, F5 wall
  inserts), unchanged in design and precedent. They were already on pale hinoki, linen and red cloth.

| Plinth / hood | Footprint (cm) | Plinth H | Glass H | Used by |
|---|---|---|---|---|
| `DSP_Case_L` | 200 x 140 | 75 | 45 | Case 1 (and 3 at 180 x 100 as a variant) |
| `DSP_Case_M` | 160 x 120 | 70 | 55 | Case 2 |
| `DSP_Case_S` | 110 x 140 | 90 | 45 | Cases 5, 7, 8 |
| `DSP_Case_Tall` | 110 x 150 | 20 | 200 | Cases 4, 6 (mannequins) |
| `DSP_Case_Hero` | 200 x 70 | 55 on the +60 platform | 45 | Case 10 |

| # | Case | Items (from `ITEM_INVENTORY.md`) | Inner mount and seating (sockets as in v1 section 8) |
|---|---|---|---|
| 1 | Front-centre, L | Smoke-bomb **trio** (shipped `#3F3A37`, indigo, undyed; the view shows about five bombs, three is the recolour story); paper tags; a plain kunai **with a tag tied to its ring**; four-point and eight-point stars | Four linen compartments. Bombs on `DSP_Sanbo` cradles (`Grip` at `Slot_1..3`, reference view to the front). Tags on `DSP_FudaStand`, print out (`Attach`, roll 180, 1 cm slack). Kunai flat on a two-notch rest by `Grip`, with a tag hanging: tag `Cord` = kunai `Ring`. This replaces the v1 target-post pairing. Stars in two tray wells |
| 2 | Mid-centre, M | Folding fan (skeletal, animated) | `DSP_FanStand` cradle: V-notch below the rivet, front +Z to the door. Closed at rest. `A_Fan_Openness` follows the player inside 2 m. **Clearance to the glass** (40 cm wide, 23 cm above the rivet, plus the tassel) proven at G0-7 |
| 3 | Rear-centre, L variant | **Snow Flower drawn** above the **empty sheath**, horizontal on a two-tier kake (the view shows it horizontal) | `DSP_Kake_Long`: sword by `Grip`, blade horizontal, edge up, -Y front (blossom relief) to the viewer. Held at the guard and at `BladeTip` minus 22 cm. Sheath below by `Holster`, front (blossoms) out. Interior length at least 145 (sword 125.6 + margin). Sheath is a box proxy until built |
| 4 | Left-front, Tall | Black cloak | Full mannequin / gusoku-kake form: stand `Root` = the cloak's ground origin. Front to the aisle (+X). **The lit wall panel behind it is its backdrop** (fixes the black-on-black risk). Torso sized after the cloak review |
| 5 | Left-mid, S | Plain kunai: shipped wrap and the **Undyed** preset. Growth: tanto and other small blades | `DSP_Kake_S` two-tier, plus two rail pegs on the case back panel, hung by `Ring`. Spare mounts are growth slots |
| 6 | Right-mid, Tall | Kasa **with attire** | Now: `DSP_FormPost` head top, hat by `HEAD`, brim at about 136, tails clear by at least 12 cm, knot side to the aisle. After the cloak review: a full mannequin wearing the kasa **and the cloak in a second preset** (Crimson or Navy, which ship), sized so `HEAD` meets the collar (D6) |
| 7 | Right-front, S | Snow Flower heels (the view shows boots, D5) | `DSP_Tiers_2`, red cloth. Left in profile, right at 3/4. **Two meshes, never mirrored.** 20 % margin until built |
| 8 | Right-front, S | **Shuriken assortment:** all six forms (four-point, eight-point, senban, six-point, hooked cross, spike) | `DSP_Tray_7`, linen-lined, tilted 15 degrees toward the aisle. Six wells plus the spike groove, as v1. The hooked cross is yaw only; negative scale is rejected |
| 9 | Wall panels, both sides | Growth. Extra kunai on pegs, tag hooks, colour variants (kunai wrap, smoke-bomb colours) | The v1 **universal rail**, now mounted inside each lit panel: sockets `Mount_00..07` every 25 cm at 90/120/160/200. Hooks and pegs are F5 inserts |
| 10 | Hero, on the platform | **Snow Flower sheathed** (the hero read, per the inventory's "drawn and sheathed" ask). Until the sheath is built: a second drawn sword copy, or empty with its light off | `DSP_Kake_Hero`, one tier, red cushion, sword horizontal, front to the axis. Sheathed seating waits on the sheath tip decision (SHEATH_REFERENCE_SPEC 9.4) |
| r | Corner racks | Growth: long weapons (the view shows katanas and spears) | Upright rack with a lit back, 6 slots each |

**Empty-slot rule.** The references show a full armory, and today there are 15 items. Unfilled growth mounts are
either hidden (not placed) or show colour variants of shipped items. They never show a placeholder that looks like
a missing asset.

---

## 6. The greybox (P1)

**Where:** a new `ArmoryLab` project, level `L_Armory`, DemoGame_1's render settings (Lumen HW RT, VSM, Substrate).
Pack items come in by a file copy of the imported `/Game/NinjaPack/`, with its recreated sockets (unchanged from v1).

**Blocks:**
- walls, windows with lattice bars (25 mm), door opening, floor;
- platform and steps; ceiling beams and coffers;
- case plinths as boxes, and glass hoods as **real glass-material boxes** (the glass is the thing to test);
- wall panels as emissive-backed boxes, corner racks and mannequin proxies;
- a **10 m wide variant** of the shell.

**Drops in:** the same items as v1 (real pack meshes, the real `SK_Fan`, the Snow Flower v4 with sidecar sockets;
the sheath, heels and a second mannequin as proxies), plus the player character.

| Gate | Test | Pass |
|---|---|---|
| G0-1 Contrast | Item silhouette against its **case interior** backdrop, from a luminance histogram per camera | At least 3:1 for every item |
| G0-2 Gameplay read | Smallest item (1.9 mm senban) through glass from the armory camera boom at the game FOV | At least 24 px across at 1080p |
| G0-3 Framing | Every camera in section 10 frames its subject with 5 % margin | All pass |
| G0-4 Leaks and stability | Lumen sweep at every junction; sun shafts and glass reflections watched over 60 frames | No leaks, no visible crawl |
| G0-5 Frame time | RTX 4070 SUPER, with all case lights, under-glow and glass on | Gameplay 16.7 ms or less at 1080p; showcase 33 ms or less at 1440p |
| G0-6 Sun | Golden Hour preset | Shafts fall on the floor aisles. **No sun glare on any case glass as seen from C1 or the aisles** |
| G0-7 Fan clearance | Real `SK_Fan` at the 41 sampled openings, against the stand **and the glass hood** | No contact |
| G0-8 Socket seat | Every item seated by its data row | Error under 1 mm; no negative scale |
| G0-9 Scale | Sword and cloak beside the player | The user confirms the sword length |
| **G0-10 Glass** (new) | Each case from its aisle at 1-2 m, and from C1: reflections of windows, lanterns and other cases | The item remains the brightest-contrast read in its case. Glass cost counted in G0-5 |
| **G0-11 Aisle camera** (new) | Walk every aisle and turn 360 degrees with the armory camera volume | The camera never enters a case and never pops more than once per turn. 8 m or 10 m width chosen here (D3) |

**Deliverable:**
- a walkable PIE level with both widths;
- camera stills with histograms;
- a one-page gate sheet.

**User gate:** P2 waits for the user's walk-through and go.

---

## 7. The modular kit (`/Game/ArmoryKit/`, prefix `SM_AK_`)

The piece rules are unchanged from v1 section 7:
- pivot on the inner face at the base, on the grid;
- LOD0-2 strictly descending; UV1; UCX keyed to the LOD0 node;
- `qa_check.py`, then `Scripts/pipeline` as the only export path;
- architecture at 5.12 px/cm, displays at 10.24 px/cm;
- Nanite on opaque pieces over about 2k triangles.

**Translucency is now in scope:** the glass hoods, and only those.

### 7.1 Architecture (22)

| # | Piece | Size (cm) | Tris LOD0 (ESTIMATE) | Notes |
|---|---|---|---|---|
| 1 | `SM_AK_WallLower_1` / `_2` | 100 / 200 x 30 x 250 | 300 / 400 | Timber frame, cream panel, wainscot |
| 2 | `SM_AK_WallUpper_2` | 200 x 30 x 250 | 300 | +250 to +500 |
| 3 | `SM_AK_WallUpper_Window_2` | 200 x 30 x 250, opening 150 x 90 | 900 | Sill 100 above the piece base (+350 world). Deep reveal |
| 4 | `SM_AK_Window_Lattice` | 150 x 5 x 90 | 800 | Shoji-style lattice, bars 25 mm (VSM-safe) |
| 5 | `SM_AK_WallLower_Door_2` | 200 x 30 x 250, opening 150 x 200 | 1,000 | |
| 6 | `SM_AK_Door_Leaf` | 75 x 6 x 200 | 800 | Timber leaf, placed open. Pair |
| 7 | `SM_AK_Corner_250` | 30 x 30 x 250 | 150 | |
| 8 | `SM_AK_Post_500` | 15 x 15 x 480 | 100 | Every 100 cm; defines the bays |
| 9 | `SM_AK_Nuki_1` / `_2` | 100 / 200 x 3 x 12 | 50 | +40 and +240 |
| 10 | `SM_AK_EavePlate_2` | 200 x 30 x 30 | 100 | |
| 11 | `SM_AK_Floor_Plank_2x2` | 200 x 200 x 5 | 50 | Two variants |
| 12 | `SM_AK_Ceiling_Beam_8` | 800 x 25 x 40 | 800 | Every 200 cm |
| 13 | `SM_AK_Ceiling_Coffer_2x2` | 200 x 200 x 20 | 600 | Recessed coffer, downlight cut-outs |
| 14 | `SM_AK_Downlight` | 12 dia x 10 | 200 | Emissive trim + a spot light in the level |
| 15 | `SM_AK_Platform_1x1` / `_Edge` | 100 x 100 x 60 | 300 / 500 | Edge has the gold band and LED groove |
| 16 | `SM_AK_Step_2` | 200 x 25 x 15 per tread, as a 4-riser run | 600 | LED line under each nosing (the view) |
| 17 | `SM_AK_WallPanel_Lit_1` | 100 x 25 x 200 | 800 | Cabinet with a cream lit back and a hidden LED strip. Carries the universal rail sockets. The main growth piece |
| 18 | `SM_AK_WallPanel_Plain_1` | 100 x 5 x 200 | 100 | Where nothing is shown |
| 19 | `SM_AK_CornerRack` | 120 x 85 x 220 | 2,000 | Long-weapon rack, lit back, 6 slots |
| 20 | `SM_AK_PaintingPanel` | 240 x 10 x 180 | 400 | Frame + an original pine painting texture (P2 art task) |
| 21 | `SM_AK_Threshold_2` | 200 x 20 x 10 | 150 | Door sill |
| 22 | `SM_AK_EntryMat` | 150 x 90 x 2 | 100 | Woven mat, unique UVs |

### 7.2 Casework and inner mounts

| Group | Pieces | Tris each (ESTIMATE) |
|---|---|---|
| F0 plinths | `DSP_Case_L`, `_M`, `_S`, `_Tall`, `_Hero` (5) | 1-3k |
| F0 glass hoods | 5 matching hoods (panes + brass frame; frame and glass as two material slots) | 300-800 |
| F1-F5 inner mounts | As v1 section 8: `DSP_Tray_7`, `DSP_Bundai`, `DSP_Kake_S`, `DSP_Kake_Long` (new, horizontal two-tier), `DSP_Kake_Hero` (new, one tier), `DSP_FormPost` (head top, torso top, full mannequin), `DSP_Sanbo`, `DSP_FudaStand`, `DSP_FanStand`, `DSP_Tiers_2`, rail inserts | 0.1-5k |
| Label plate | `DSP_LabelPlate` (8 x 0.5 x 5, black with gold edge, blank or our item name) | 50 |

### 7.3 Dressing (7)

| Prop | Size (cm) | Note |
|---|---|---|
| Floor lantern | 40 x 40 x 70 | Paper sides, emissive, a real light. x6 |
| Vase with plum branches | 30 dia x 90 | Black glaze, red blossom branches. Masked cards, one material. x2 |
| Banner | 60 x 2 x 180 | Cloth, **original emblem** or plain. x2-4 |
| Emblem plate | 12 x 1 x 12 | Gold. The same original emblem on every plinth front (D7) |
| Kiri box set | as v1 | Storage dressing in racks and under cases |
| Small shelf ornaments | 3 pieces | Growth-bay dressing, no text |
| Ceiling lantern (optional) | 30 x 30 x 50 | Only if the downlights read too modern at G0 |

### 7.4 Budgets

| Budget | Value (ESTIMATE) |
|---|---|
| Environment in view, LOD0 | About 110k triangles. Lower than v1: no trusses or roof undersides, but casework and lattice are added |
| Items in view, LOD0 | About 240k, as v1 (DERIVED) |
| Texture sets | 1 x 4K timber and lacquer trim; 4 x 2K tiling (planks, cream plaster, lacquer panel, woven mat); 1 x 2K casework atlas; 1 x 2K emissive and decal atlas; 1 x 2K painting; 1 x 1K brass trim. About 130 MB with mips |
| Lights | About 45 in the room: 10 case lights, 12 downlights, 6 lanterns, about 8 under-glow rects, sun, sky, and fill. **At most 12 shadow-casting**; under-glow and panel lights cast no shadows. Evaluate MegaLights if the 5.8 build supports it; otherwise stay within the shadow budget |

### 7.5 Content roots

| Root | Holds | Gate |
|---|---|---|
| `/Game/ArmoryKit/` | Architecture, casework, mounts, dressing, masters and textures (was `/Game/KuraKit/`) | Dependency gate: nothing here references `/Game/NinjaPack/`, `/Game/Armory/` or third-party assets. Keeps it sellable |
| `/Game/Armory/` | Level, `BP_DisplaySlot`, data tables, presets, item colour MICs | May reference both |

---

## 8. Lighting

The rules carry over from v1:
- Lumen GI and reflections; hardware RT in showcase mode, the software fallback checked in gameplay;
- VSM, low-density volumetric fog, manual exposure per camera;
- presets in `DT_LightingPresets`;
- practicals are real lights, and plaster albedo is capped at 0.80.

| Preset | Key | Fill | Accents | Use |
|---|---|---|---|---|
| **Gallery** (default) | Case lights: one soft rect per case, above the deck, raking the steel at about 45 degrees (Toukenza practice). Hero case 10 gets two | Downlights at low level, and a sky light at low intensity through the windows | Under-glow on plinths and steps; lit wall panels; lanterns | Walkthrough and gameplay |
| **Golden Hour** (the armory3 look) | Low sun, about 20-25 degrees, about 3800 K, through the lattice windows, making lattice patches across the aisles | Gallery lights at 60 % | Fog up for the shafts | C1, C9, trailer |
| **Inspection** | No sun. Neutral 5000 K case lights, glass hidden, fog off | Soft overhead | none | Honest material shots for Fab |
| **Night** | Lanterns and case lights only; windows dark | none | Under-glow | Gameplay mood; never in Fab media |

**Glass and light.**
- Case lights sit inside the hood, so the glass shows no hot reflection toward the aisle.
- Lanterns are placed so that their reflections in the case fronts fall off the item. Checked at G0-10.

---

## 9. Materials and the pack colour system

The v1 section 9 rules are unchanged: items keep their shipped MIs, and the armory adds only child MICs in
`/Game/Armory/` (the smoke-bomb trio, the kunai Undyed preset, the cloak's second preset in case 6, heel cloth).
The new environment masters are listed in section 4.

---

## 10. Showcase cameras (positions ESTIMATE until G0-3; 16:9 sensor 36 x 20.25 mm)

| Id | Position (X, Y, Z) and aim | Lens | Shows | Preset |
|---|---|---|---|---|
| C1 Entry reveal | AS BUILT (f1): Blender (6.0, -1.51, +3.42) m, level, looking +Y, vertical lens shift -0.303 (reference 2's verticals are vertical) | 24.5 mm | The armory3 view: every case, both wall bands, the platform and hero case | Golden Hour |
| C2 Case 1 overhead | (400, 130, 220), +Y, 45 degrees down onto case 1 | 35 mm | All four compartments, about 2 m frame width. Front pane hidden | Gallery or Inspection |
| C3 Sword + sheath | (400, 640, 130), +Y, about 1.5 m | 28 mm | The drawn sword over the sheath, full length (1.9 m frame) | Gallery |
| C4a-f Case macros | About 60 cm from each deck: case 1 (x2), 5, 8, 7, 10 | 100 mm | Within 0.89 m, so LOD0 without forcing. Front pane hidden | Gallery or Inspection |
| C5 Cloak | (220, 620, 120), aim (95, 295, 100), 3/4 from the north | 28 mm | Full 1.72 m cloak, lit panel behind. DERIVED: 3.45 m away, 2.5 m vertical frame. The 1.5 m aisle rules out a front-on full shot except at 18 mm | Gallery + front fill |
| C6 Fan fold | (400, 400, 120), +Y, 1.4 m | 85 mm | `A_Fan_OpenClose` live, front-on | Gallery |
| C7 Heels | (540, 400, 120), +X, 1.55 m | 85 mm | Left in profile, right at 3/4 | Gallery |
| C8 Kasa low 3/4 | (540, 560, 90), aim toward case 6 | 50 mm | Weave and brim | Gallery |
| C9 Dolly | C1 along the axis at +200 over the cases, rising over the steps, ends on C10 | 24 to 40 mm | Trailer and listing video | Golden Hour |
| C10 Hero case | (400, 930, 150), +Y, about 2 m | 40 mm | Hero case 10 against the painting, vases either side | Gallery |
| C11 Gameplay read | The armory camera volume boom | Game FOV | Runs G0-2 and G0-11 | Gallery |

**Hidden glass.** Macro and material cameras hide the front pane (a camera-preset flag on `BP_DisplaySlot`) and say
so in the still's metadata. This is standard museum photography practice, and it avoids a pane reflection being
mistaken for a material flaw.
**LOD in shots:** cameras beyond 0.89 m force LOD0 through the preset (v1 rule).
**Fab media rule:** unchanged. The caption reads "display environment not included", and there is no VFX in any
media.

---

## 11. The slot system

Unchanged from v1 section 12:
- one `BP_DisplaySlot` per slot, one `DT_ArmoryItems` row per item;
- slot world = display socket x inverse(item socket); "Reseat all" after every reimport;
- `AllowMirror` is always false.

**Two new columns:**

| Column | Meaning |
|---|---|
| `CaseId` | Which case or panel (1-10, W9-xx, R-xx) |
| `HideGlassInShowcase` | Front pane hidden for this row's showcase camera |

---

## 12. Growth

| Step | Where | Cost (ESTIMATE) |
|---|---|---|
| 1. A free mount in an existing case or panel | Case 5 spares, case 8 well 6, wall-panel rail mounts (about 60 mounts on 17 panels), corner racks (12 slots) | 0.25-0.5 day: a row, a seat check, a camera |
| 2. A new inner-mount variant | An item fits a case but not a mount | About 1 day with a blind round |
| 3. A new case on the floor | There is no free floor spot in the 8 m room. Swap a case, or the 10 m variant gains two positions | 1 day (plinth + hood are family pieces) |
| 4. A bespoke hero mount | Armour, spear, bow | 2-3 days |
| 5. Lengthen the room | +200 cm per ceiling bay: move the north wall, platform and steps; add a case pair | 1-2 days |
| 6. A second gallery | A new category | A new level from the same kit |

---

## 13. Phased build order

| Phase | Work | Days | Ends with (walkable) |
|---|---|---|---|
| **P0 Decisions** | The user answers section 15 | user | Approved scope |
| **P1 Greybox (G0)** | Section 6, both widths, real glass, proxy lights for all four presets, slot system v0 | **3** | The block room with every finished item in its case proxy. **USER GATE** |
| **P2 Shell** | 22 pieces 6 d; trim + tiling + emissive textures 4 d; 5 masters incl. glass and emissive, spec build, fresh-process verify, frozen proof 3.5 d; original emblem + pine painting 1.5 d; assembly + leak sweep 1 d | **16** | The finished empty gallery, Gallery light, lit panels |
| **P3 Casework + mounts + slots** | Slot system 2 d; 5 plinths + 5 hoods + under-glow 3 d; F1 tray, F2 kake S, F3 head form, F4 sanbo, fuda, tiers, F5 inserts 6.5 d; fabric MIs 0.5 d | **12** | Every finished small item in its case, from data rows (day 31) |
| **P4 Heroes** | `DSP_Kake_Long` + `DSP_Kake_Hero` 2 d (after v4 is final); fan cradle + proximity + glass clearance 2 d; cloak mannequin 1.5 d (after the review); kasa-with-attire form 1 d; heel tiers 0.5 d | **7** | Sword and sheath, the fan opening as you approach, the cloak and the kasa on forms |
| **P5 Light + cameras** | 4 presets against the gates, with glass and the shadow budget, 4 d; 11 cameras, dolly, MRQ 2 d | **6** | Presets switchable in PIE; shot set rendered |
| **P6 Dressing + perf** | Lanterns, vases, banners, emblem plates, labels, kiri boxes 4 d; perf and Lumen tuning 1 d | **5** | The finished gallery |
| **Total** | | **49** | **About 59 with 20 % contingency** |
| P7 Optional | Target post with embedded stars (1.5 d); exterior door face (3 d); animated doors (2 d); sword draw-on-interact (1.5 d); ArmoryKit Fab packaging (3 d) | | |

**Leaner path (D9):** P1 + a lean P2 (tiling only, no trim bake, a stock-free placeholder painting; about 10 d) + P3
gives a walkable gallery with every finished small item in **about 25 days**.

**Machine schedule** (unchanged):
- one Unreal commandlet at a time; asset locks per `.blend` and `.uasset`;
- P1 waits for the Snow Flower v4 Unreal check and never overlaps the MetaHuman spike;
- the fan and kunai reworks stay stopped unless the user authorises them.

---

## 14. Risks

| # | Risk | Mitigation | Check |
|---|---|---|---|
| 1 | **Black items in a dark room** | Dark room, bright cases: pale decks, lit panels behind the cloak and on the walls, case lights | G0-1 |
| 2 | **Glass**: reflections hide items; translucency cost; Lumen reflections on glass are limited in software mode | Case lights inside the hood; lantern placement; hidden panes for showcase; one glass master; HW RT in showcase | G0-10, G0-5 |
| 3 | **Tight aisles** (130-150 cm) against a 375 cm third-person boom | Armory camera volume (150-200 cm boom, glass collision); 10 m variant | G0-11 (D3) |
| 4 | **Many lights** (about 45) | At most 12 shadow casters; under-glow and panels unshadowed; MegaLights only if 5.8 supports it | G0-5 |
| 5 | **Crest and painting IP** | Original emblem with a kamon similarity check, or blank plates; an original painting; no text | P2 review (D7) |
| 6 | **The references show more items than exist** (tanto, katanas, spears, boots, scrolls) | Growth mounts hidden or showing colour variants; heels in bay 7; tags for "scrolls" | P3 review |
| 7 | **Snow Flower in flux**, sheath not built | Kakes built last in P4; box proxy; case 10 waits on the tip decision | G0-8, G0-9 |
| 8 | **Cloak unreviewed** (84.6k tris, own material) | Mannequins sized after the review; proxies until then | Review gate before P4 |
| 9 | **Fan inside a glass case** | Clearance to stand and hood at 41 openings | G0-7 |
| 10 | **Frozen pack masters** | New masters only; MIs of old; byte-identical dumps; 63 of 63 | Each material build |
| 11 | **Lacquer and gold read "luxury store" rather than "armory"** | Timber, lattice, lanterns and the painting carry the period; gold kept to thin bands | P2 blind review against armory3_reference2 |
| 12 | **Third-party contamination** of the kit | Dependency gate on `/Game/ArmoryKit/` | P2, P6 |
| 13 | **Scope** (49-59 days) | P1 hard stop; lean path; each P7 alone | User gates |
| 14 | **Shared machine** | Own project, one commandlet, locks | Every Unreal run |

---

## 15. Decisions for the user

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Style | **Decided 2026-09-26:** armory3 gallery | |
| D2 | Look reference | **Decided:** `armory3_reference2.png` (look) + `armory3_reference.png` (layout), the user's originals | |
| D3 | Room width | 8 m as drawn / 10 m | **Greybox both**; pick at G0-11. 8 m if the short camera boom feels right |
| D4 | Case 3 vs case 10 (one sword, two sword displays) | a) case 3 drawn + empty sheath, case 10 sheathed hero; b) Snow Flower only in case 10, case 3 held for the next long weapon | **a)**. It gives the "drawn and sheathed" ask its two reads. Until the sheath exists, case 10 shows a drawn copy |
| D5 | Bay 7 | Snow Flower heels / new boots item | **Heels.** Boots would be a new asset |
| D6 | Case 6 "kasa with attire" | Head form only / full mannequin with the kasa + the cloak in its Crimson or Navy preset | **Head form now**, full mannequin after the cloak review |
| D7 | Emblem on plinths and banners | Original emblem (0.5-1 d, similarity-checked) / blank gold plates | **Original emblem**. It can double as the game's house emblem |
| D8 | Glass | Real glass with per-camera hidden panes / open cases, no glass | **Real glass**, as the reference shows; the hidden pane covers showcase honesty |
| D9 | Scope | Full 49 d (about 59) / lean about 25 d | **Full, gated per phase**; lean if the item queue must restart sooner |
| D10 | Project | New `ArmoryLab` / DemoGame_1 / pack project | **New project** (unchanged) |
| D11 | Smoke bombs in case 1 | Trio in three colours / five in the shipped colour (as the view) | **Trio**: it shows the recolour system |
| D12 | Sword length | Keep 1.256 m / resize | Decide at G0-9 (unchanged) |
| D13 | Sell the kit on Fab | Plan for it / game-only | **Keep the option open** (own root, dependency gate) |
| D14 | When P1 starts | Now / after the current queue | **After the Snow Flower v4 Unreal check**, and only on the user's go |
