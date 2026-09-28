# Armory Plan: the airing-day kura

**Date:** 2026-09-26
**Status:** PLAN ONLY. Nothing is modelled, rendered, imported or built. The user approves the scope and answers
section 16 before any build. Under the stop-before-expensive-work rule, phase P1 (the greybox) does not start until
the user says go.
**Purpose.** One executable plan for an in-engine armory: a room that holds every item in the line, grows as the
line grows, and gives the in-engine showcase shots that `WorkFiles/showcase/SHOWCASE_PLAN.md` could not make.
**Companions (this folder):** `ITEM_INVENTORY.md` (sizes, sockets and needs for every item: the source for every
item number here); `ARMORY_LAYOUT.svg` and `ARMORY_LAYOUT.txt` (top-down plan); `armory_layout.py` (draws both
from one table, so the two cannot disagree).
**Flags.** MEASURED = measured on a shipped mesh by its build (numbers from the item reports and sidecars).
SOURCED = from a cited reference. DERIVED = computed here from the numbers above. ESTIMATE = a design choice or
guess, to be checked at the greybox. Every day count is an ESTIMATE.

---

## 1. Summary

| Item | Value |
|---|---|
| Style | A **kura**: a thick-walled Japanese earthen storehouse, shown on **mushiboshi**, the one day a year its owner airs the treasures |
| Why | The line is almost all black and silver. A kura is white lime plaster and pale wood, the palest Japanese interior, so every item reads. It is also the real building type for keeping valuables, so every display has a real ancestor |
| Shape | **One storey**, 8.0 x 12.0 m interior, 5.0 m to the eaves and 7.0 m to the ridge. No loft, no stairs (cut for cost; section 13 P7 keeps them optional) |
| Grid | 100 cm primary, 25 cm sub-grid, heights on 25 cm. Walls 30 cm thick |
| Kit | **28 architecture pieces + 5 rail inserts + 6 dressing props**, one 4K timber trim sheet, 5 tiling sets |
| Displays | **5 stand families + 3 hero stands** cover all 15 items. Placement comes from a data-table row per item: slot = display socket x inverse(item socket) |
| Light | Sun through four high barred windows onto a central airing platform; sky fill through the open door; white plaster bounce. Four presets: Airing Day, Afternoon Rim, **Inspection** (neutral, for honest material shots), Night |
| Cost | **47 engineering days** (ESTIMATE), **about 56 with 20 % contingency**. The first walkable room with every finished item on its real display lands at **day 30** (end of P3). The greybox gate is **3 days** |
| First step | P1 greybox in Unreal: blocks, all finished items at true scale, every camera, 9 pass/fail gates. **User gate** |

Three facts shape the plan. The two judges disagreed: the cost judge ranked the dojo first (7/10) and the game judge
ranked the kura first (8/10). This plan takes the kura's look and contrast rule, but cuts it down to the dojo's cost
profile: one level, static doors, one alcove, and the dojo's wall-rail growth system. Second, the Snow Flower v4
export is **19,386 LOD0 triangles**, not the 456,024 of rev 3 that all three directions budgeted, so no piece needs
Nanite just to carry the sword. Third, every pack prop drops to LOD1 at about **0.89 m** (MEASURED,
`ITEM_INVENTORY.md`). A visitor at 1-2 m sees LOD1, which is honest. Showcase shots either sit inside 0.9 m or force
LOD0 through the camera preset (section 11).

---

## 2. The recommended style, and the runners-up

### 2.1 Kura on airing day (recommended)

| Reason | What it gives the armory |
|---|---|
| **Contrast** | The items are black-coated stars, a black kunai wrap, a black kasa, a blue-black fan, a black cloak, black-and-silver heels and a dark-steel sword with a black grip and sheath. A kura interior is lime plaster (shikkui) over clay plus pale sugi, hinoki and kiri wood. Every black silhouette reads at every distance. A dark dojo or stone vault would swallow the line |
| **A real ancestor for every display** | Kura held a household's valuables in kiri boxes, tansu and chests. So the displays borrow real forms: the compartment tray, the kake sword stand, the sanbo offering stand, the ofuda holder, the kabuto-kake head stand, the gusoku-kake armour stand and the red-cloth hina-dan tiers. None of them belongs to a franchise |
| **One controllable light** | A few small high barred windows and one door give one key (sun shafts) and one fill (the open door). 30 cm walls are three times Epic's 10 cm light-leak floor |
| **A story that explains the layout** | Mushiboshi is a real custom: temples such as Daitokuji air their treasures once a year. It explains why the items are out of their boxes, laid on cloth, lit by open shutters. New items "arrive in kiri boxes" |
| **Cheap growth** | Posts every 100 cm make every wall bay a slot. Trusses repeat every 200 cm, so the building lengthens by whole bays with no new kit |

The mood is quiet, dim and reverent: a treasury, not a weapon wall. Stated liberties: the interior is larger than a
household kura (a merchant kura, about 4.4 x 6.6 ken), and a real kura has a second floor, which this plan omits.
It is not a historical reconstruction.

### 2.2 Runners-up, and what was grafted from them

| Direction | Cost judge | Game judge | Why it lost | Grafted into this plan |
|---|---|---|---|---|
| **Mountain dojo** (timber training hall, weapons on the walls around an open floor) | 7/10, first | 6/10 | It puts black items on black lacquer (sword kake, shoe board, bon tray). Its whole look rests on shoji paper, which Lumen handles worst (about 30 rect lights). The heels sat on the floor by the door. Its target placed shuriken by the Trail socket, which is the disc's centre | The **universal wall rail** (sockets every 25 cm at four heights) as the growth system. The **target** with the stuck-in-wood shot, fixed to embed by a point. The **Ring-socket kunai pegs** and **Cord-socket tag hooks**. The **dependency gate** on the kit root. The **Fab media rule** ("display environment not included") |
| **Yagura** (four-storey castle tower around a 16 m well) | 3/10 | 5/10 | 55-61 days. 56-degree stairs. Floor undersides modelled everywhere. Growth means a new storey. No frame shows the whole line. It pinned stars through their centre (the hooked cross has no hole) and put the dark smoke bombs in the darkest floor | The **Inspection** lighting profile. The **three-colour smoke-bomb trio** (it shows the recolour system that ships). The **kasa seen from below**. The **vertical star board** as a fallback if the tray fails the read test (section 16, D6) |

---

## 3. The one mood image

The mood image sets the palette, the light and the material hierarchy. It is not a blueprint to copy piece by piece.
**The user supplies or approves it** (section 16, D2).

**What it must show.** An interior view from just inside a thick kura doorway, looking down the long axis, at eye
height. Near the edge of the frame: the stepped (jabara) door reveal and part of one heavy plastered door leaf. White
lime-plaster walls with close-set dark timber posts and a board wainscot. One small, high, barred window throwing a
sharp sun shaft with bar shadows onto a low pale wooden platform, where a few dark objects lie on cloth. A heavy dark
beam in the middle distance, framing a warm lantern glow at the far end. Dust in the air. No people, no legible text,
no family crests, nothing from a game or anime.

**Candidates** (links only; nothing downloaded):

| # | Source | Carries | Licence |
|---|---|---|---|
| M1 | Ishitani House kura interior, Chizu, Tottori (Important Cultural Property), Asturio Cantabrio, Dec 2023: https://commons.wikimedia.org/wiki/File:Ishitani_House_kura_ac_(1).jpg (and (2)-(4) in the series) | Real kura interior: plaster, timber, scale. Checked: the file exists and is an interior | CC BY-SA 4.0 |
| M2 | E. S. Morse, "Room in kura fitted up as a library, Tokio", *Japanese Homes and Their Surroundings*, 1885: https://commons.wikimedia.org/wiki/File:JapanHomes137_ROOM_IN_KURA_FITTED_UP_AS_A_LIBRARY,_TOKIO.jpg | The exact premise: an antiquarian's kura full of collections, more stored in the loft. Checked: exists | Public domain |
| M3 | Wikimedia Commons, Category Kura (storehouse): https://commons.wikimedia.org/wiki/Category:Kura_(storehouse) | Browse for an interior with a window shaft | Per file |
| M4 | Mushiboshi at Daitokuji, the narrative frame: https://www.nippon.com/en/guide-to-japan/gu900056/ | The airing-day event | Reference only |

**Recommendation.** Use M1 as the mood image. If no single photo carries the sun shaft and the dark objects, make the
mood image a **paint-over of the greybox C1 frame** (after P1), using M1 and M2 as sources. If an AI tool makes or
paints any part of it, record that for Fab's AI disclosure (ASSET_GUIDELINES 11).

---

## 4. Detail references

| Subject | Reference | Used for |
|---|---|---|
| Kura construction | Wikipedia, Kura (storehouse): plaster-finished interior, double roof, thick plaster outer door plus thin inner leaf, high windows with iron bar grilles: https://en.wikipedia.org/wiki/Kura_(storehouse) | Wall build-up, windows |
| Wall thickness | ja.wikipedia, 土蔵 (dozo): walls about 300 mm or more, clay over bamboo lath, shikkui finish: https://ja.wikipedia.org/wiki/土蔵 | 30 cm walls (SOURCED) |
| Doors | JAANUS, kannonbiraki tobira: paired swing doors, finished fireproof leaf about 18 cm, interlocking stepped reveals: https://projects.mcah.columbia.edu/jaanus/record/kannonbirakitobira ; Kura door, Tsuyama (CC BY-SA 3.0): https://commons.wikimedia.org/wiki/File:Kura_door.JPG | Door leaf 75 x 18 x 200, jabara reveal |
| Windows | Kura window with stepped shutters, Kitakata (CC BY-SA 3.0): https://commons.wikimedia.org/wiki/File:Kura_window.JPG | Shutter and bar pieces |
| Exterior door face | Kawagoe kurazukuri, Osawa House (1792): https://www.japan-guide.com/e/e6501.html | The one exterior face (C1) |
| Kura as a finished room | Kitakata kura-zashiki: https://fukushima.travel/destination/the-warehouses-of-kitakata/145 ; Morse, framework for draping a kura room: https://commons.wikimedia.org/wiki/File:JapanHomes138_FRAMEWORK_FOR_DRAPING_ROOM_IN_KURA.jpg | Interior finish level |
| Treasure storage | Shosoin repository: https://smarthistory.org/the-shosoin-repository/ ; kiri-bako boxes: https://www.japan-suite.com/blog/2026/1/10/kiribako-practical-beauty-in-japanese-craft-and-preservation | Kiri boxes, chests (blank, no labels) |
| Sword stands | Met Museum sword stands (katana-kake, about 38.7 x 59.2 x 18.2 cm): https://www.metmuseum.org/art/collection/search/26750 and https://www.metmuseum.org/art/collection/search/24413 | Kunai kake and sword stand proportions |
| Sword display practice | Toukenza, sword display (tokonoma, light at about 45 degrees to show the steel): https://toukenza.jp/en/column/sword-display ; Japanese Sword Museum: https://www.japan.travel/en/spot/1669/ ; Tokyo National Museum cases by Goppion (supports hidden under silk): https://www.goppion.com/projects/tokyo-national-museum | Sword key light, restraint |
| Garment and armour stands | Met Museum kimono rack (iko): https://www.metmuseum.org/art/collection/search/50801 ; armour and helmet stands (gusoku-kake, kabuto-kake): https://sengokudaimyo.com/katchu-katchu18 | Form post family |
| Kit practice | Joel Burgess, Skyrim's modular level design (GDC 2013): http://blog.joelburgess.com/2013/04/skyrims-modular-level-design-gdc-2013.html ; The Level Design Book, modular metrics: https://book.leveldesignbook.com/process/blockout/metrics/modular | Grid, pivots, piece count |
| Trim sheets in UE5 | https://80.lv/articles/building-a-modular-snowy-church-environment-in-unreal-engine-5 | 4K trim, texel density |
| Lumen limits | Epic, Lumen technical details (walls no thinner than 10 cm; distance fields miss thin meshes): https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-technical-details-in-unreal-engine | Wall thickness, bar size |

**Never shown in the room:** the Snow Flower reference sheet (it carries third-party name text), any real family
crest (kamon), temple names, or legible calligraphy (SHOWCASE_PLAN 6.1 text policy).

---

## 5. The room

### 5.1 Grid and frame

| Rule | Value |
|---|---|
| Origin | Interior south-west corner, at grade (the doma floor) |
| Axes | X across (0-800 cm), Y along the axis (0-1200 cm, north = +Y, the sword end), Z up. The door is in the south wall |
| Grid | 100 cm primary, 25 cm sub-grid, heights on 25 cm. Kit snap 25 cm |
| Walls | 30 cm. The pivot sits on the **inner face** at the piece's base, so the interior snaps to whole metres and thickness grows outward (ASSET_GUIDELINES 1: whole-metre modules, pivot where the next piece meets) |
| Units | Blender metres, Unreal cm (1 m = 100 UU) |

### 5.2 Dimensions

| Datum | World Z (cm) | Note |
|---|---|---|
| Doma (earth entry floor) | 0 | Grade |
| Raised plank floor, top | +50 | Everything north of Y 200 |
| Airing platform, top | +80 | 30 cm above the plank floor |
| Sanctum dais, top | +75 | 25 cm above the plank floor |
| Wainscot cap (nuki) | +150 | 100 above the plank floor |
| Hanging rail line (nuki) | +250 | 200 above the plank floor; top of the lower wall piece |
| Lintel beam underside | +300 | Frames the sanctum at Y 900 |
| High windows | sill +350, head +440 | 90 x 90, on both long walls |
| Eaves plate | +500 | Top of the upper wall piece |
| Ridge | +700 | 200 rise over a 400 half-span, 26.6 degrees (ESTIMATE, a typical kura pitch) |

| Plan | Size | Note |
|---|---|---|
| Interior clear | 8.0 x 12.0 m (96 m2) | 3-5 m of camera stand-off everywhere |
| Exterior | about 8.6 x 12.6 m | Only the south door face is modelled |
| Door | 150 W x 200 H, centred at X 400 | One entrance, as in a real kura. No second exit |

### 5.3 Zones

| Zone | Extent | Contents |
|---|---|---|
| **Z0 Doma threshold** | Y 0-200, at grade | Arrival. Step stone and a 50 cm step-up beam. The **target post** (kunai stuck tip-first, paper tag tied to its ring, stars embedded) stands at X 120, Y 100: the first thing you see, off the axis |
| **Z1 Airing hall** | Y 200-900, plank floor, open to the trusses | The central **airing platform** (100 W x 400 L x 30 H, X 350-450, Y 300-700) carries the small items, all facing the door. West wall: cloak (Y 300-400), kasa (Y 500-600), kunai peg rail (Y 700-900). East wall: fan (Y 300-400), heels (Y 500-600), tag and growth rail (Y 700-900). Six free bays |
| **Z2 Sanctum** | Y 900-1200, behind the lintel beam | Dais 300 W x 100 D x 25 H on the north wall (X 250-550, Y 1100-1200). The Snow Flower sword and sheath stand upright against bare white plaster, at the end of the axis. Tansu on the side walls, an andon lantern. Two free bays |

### 5.4 Top-down layout

Full drawing: `ARMORY_LAYOUT.svg` (1 m grid, sun shafts, cameras). The same data as text:

```
            NORTH (gable wall)            one char = 25 cm across, one row = 50 cm along Y
      X: 0m      2m      4m      6m      8m
         +--------------------------------+   Y 12.0
         |          ###W####S###          |
         |          ############          |  sanctum: W sword, S sheath, # dais
         |g       a                      g|
    10.0 |                                |
         |tt                            tt|
         |tt============================tt|  = lintel beam (underside +300)
         |R                              R|
     8.0 |R                              R|
         |R                              R|
         wR                              Rw
         wg             ::3:             gw  w high windows (sill +350)
     6.0 |              ::::              |
         |  K           ::::          _H_ |
         |              ::2:          ___ |
         |g             ::::             g|
     4.0 w              ::1:              w
         w__C_          ::::          _F_ w
         |____          ::4:          ___ |
         |g                              g|
     2.0 |--------------------------------|  - step-up to the plank floor (+50)
         |              oooo              |
         |    T         oooo              |
         |                                |
     0.0 |                                |  doma, earth floor at grade
         +-------------      -------------+   Y 0.0  (door 1.5 m wide, X 3.25-4.75)
                          ^ C1 at Y -2.5, looking north

Key: 1 shuriken tray, 2 kunai kake, 3 smoke-bomb sanbo, 4 tag fuda stand (all on the
:: airing platform); C cloak, K kasa, F fan, H heels, T target post, W sword, S sheath,
a andon, t tansu, R wall rail, g free growth bay, _ dais or plinth, o step stone.
```

### 5.5 Circulation and sightlines

**Route.** Enter on the axis, pass the target post, step up. Walk either 3.5 m aisle around the platform
(X 0-350 or 450-800). Side displays stand within 1 m of their wall, leaving about 2.5 m clear, enough for a
375 cm third-person boom. Pass under the lintel to the sword, and return down the other aisle. Nothing taller than
80 cm stands between X 300 and 500 south of the sanctum, so the axis stays open.

| Sightline | From | To | What it proves |
|---|---|---|---|
| S1 main axis | Outside the door (Y -250, eye +160) | Sword on the sanctum dais, 14 m away | The sword reads as a black upright against white plaster, framed by the door reveal and the lintel |
| S2 platform | Any aisle | Platform items at 55-70 cm above the floor | Walk-up readability, 360-degree access |
| S3 cross-axis | East aisle | Cloak and kasa on the west wall | Black garments on plaster, rim-lit in the Afternoon Rim preset |
| S4 sanctum | Under the lintel | Sword and sheath, andon side light | The close hero read |

---

## 6. The greybox (P1): what blocks, what drops in, what it must prove

**Where.** A new Unreal 5.8 project for the armory (working name `ArmoryLab`), level `L_Armory`, no World Partition.
Never the pack validation project, never mid-run. The finished pack items come in by a file-level copy of the
already-imported `/Game/NinjaPack/` folder, made while no editor holds it. It must be the imported pack assets:
Unreal 5.8.2 drops FBX sockets from LodGroup files, and the pack recreated them from the sidecars. Project settings
match DemoGame_1 (Lumen HW RT, Virtual Shadow Maps, Substrate), so what passes here passes in the game (section 16, D10).

**What blocks.** Engine cube meshes scaled and snapped on the 25 cm grid. No new art.

| Block | Size (cm) | Count |
|---|---|---|
| Wall slabs (lower, upper, gable) | 30 thick, on the heights in 5.2 | Shell of 8 x 12 m |
| Door opening + two leaf slabs (open) | 150 x 200; leaves 75 x 18 x 200 | 1 + 2 |
| Window openings with 5 bar blocks each | 90 x 90, bars 2.5 x 2.5 | 4 |
| Plank floor, doma, step beam | as 5.2 | 3 |
| Truss proxies (a tie beam + ridge) | 800 x 30 x 45, every 200 | 5 |
| Lintel beam | 800 x 30 x 45 at +300 | 1 |
| Airing platform | 100 x 400 x 30 | 1 |
| Stand proxies at their section-8 sizes | per display | 12 |
| Wall rail proxies | 200 x 4 x 12 at 90/120/160/200 above the floor | 2 |

**What drops in (true scale, placed by data-table row from the start).**

| Item | Asset | Status in G0 |
|---|---|---|
| Five shuriken discs, spike, plain kunai, smoke bomb, black hat, paper tag | Pack static meshes with recreated sockets | Real |
| Folding fan | `SK_Fan` + `SK_Fan_Tassel` with the sidecar's DefaultRecorderBoneCompression and `bounds_extension_cm` | Real, animated |
| Snow Flower sword | v4 export (`Exports/SnowFlower/v4/`), sockets recreated from `SM_SnowFlower.sockets.json` (they are not in the FBX) | Real, in flux |
| Snow Flower sheath | Box proxy per `SHEATH_REFERENCE_SPEC.md`: 100.8 long, 6.66 wide tapering to 4.95, 10.1 at the throat, 2.2 deep | Proxy |
| Heels | Two boxes 26 L x 10 W x 17 H (ESTIMATE + 20 % margin), left and right as separate actors | Proxy |
| Black cloak | `SM_BlackCloak` static, as exported (review still queued) | Real, for scale only |
| Player | The game's third-person character or the UE mannequin, for eye height and boom distance | Real |

**What it must prove: the nine G0 gates.**

| Gate | Test | Pass |
|---|---|---|
| G0-1 Contrast | Per camera, item-silhouette luminance against its local backdrop, from a luminance histogram of the still | At least **3:1** for every item |
| G0-2 Gameplay read | The smallest item (the 1.9 mm senban) captured from the real third-person boom (about 375 cm) at the game's FOV, walking the aisle | Reads as its shape: at least **24 px across at 1080p** (ESTIMATE threshold; DERIVED about 30-45 px at 3 m) |
| G0-3 Framing | Each camera in section 11: subject inside the frustum with at least 5 % margin | All pass. The judges already caught two failures in the kura draft (C3, C7); both are fixed in section 11 |
| G0-4 Leaks and stability | Lumen sweep at every wall and roof junction; sun shafts watched over 60 frames | No leaks, no visible crawl |
| G0-5 Frame time | RTX 4070 SUPER | Gameplay at most 16.7 ms at 1080p; showcase mode at most 33 ms at 1440p (ESTIMATE targets; the directions set none) |
| G0-6 Sun geometry | Airing Day preset | The two east-window patches land on the shuriken tray (Y 355-445) and the smoke-bomb sanbo (Y 655-745) |
| G0-7 Fan clearance | The real `SK_Fan` on the stand proxy at the fan job's 41 sampled openings, against the sidecar's posed-bounds envelope | No leaf or tassel contact at any opening |
| G0-8 Socket seat | Each item seated by its data-table row; item socket world position against the display socket | Error under 1 mm; no negative scale anywhere (the hooked cross must never mirror) |
| G0-9 Scale | Sword (1.256 m) and cloak (1.72 m) next to the player | The user confirms the sword length against player height (open in `ITEM_INVENTORY.md`) |

**Deliverable.** A walkable PIE level, the 11 camera stills with histograms, and a one-page gate sheet. **User gate:**
nothing in P2 starts until the user has walked it and said go.

---

## 7. The modular kit

Rules for every piece: pivot on the inner face at the base, on the grid. LOD0-LOD2 with strictly descending
triangles, UV1 lightmap channel (Fab rule, even though Lumen ignores it), UCX collision keyed to the LOD0 node
name, `qa_check.py` before export, `Scripts/pipeline` as the only export path. Triangle bands follow
ASSET_GUIDELINES: background piece 0.5-2k, prop 1-5k. Architecture is textured at **5.12 px/cm** (the house
third-person rate). Display pieces use 10.24 px/cm. Opaque kit pieces over about 2k triangles use Nanite. There is no
translucency, because the plan uses no display glass.

### 7.1 Architecture (28 pieces)

| # | Piece | Size (cm, W x T x H) | Tris LOD0 (ESTIMATE) | Material | Notes |
|---|---|---|---|---|---|
| 1 | `SM_Kura_WallLower_1` | 100 x 30 x 250 | 300 | Plaster + wood trim | Grade to +250. Board wainscot +50 to +150 |
| 2 | `SM_Kura_WallLower_2` | 200 x 30 x 250 | 400 | Plaster + wood trim | Most of the shell |
| 3 | `SM_Kura_WallUpper_2` | 200 x 30 x 250 | 200 | Plaster | +250 to +500 |
| 4 | `SM_Kura_WallUpper_Window_2` | 200 x 30 x 250, opening 90 x 90, sill 100 above the piece base | 800 | Plaster + trim | Deep stepped reveal, splayed inner sill |
| 5 | `SM_Kura_WallLower_Door_2` | 200 x 30 x 250, opening 150 x 200 | 1,200 | Plaster + trim | Jabara reveal, 3 steps of 30 mm |
| 6 | `SM_Kura_Door_KannonLeaf` | 75 x 18 x 200 | 2,500 | Plaster + trim + iron | Placed as a mirrored pair, **static open** in P2 (animation is optional P7) |
| 7 | `SM_Kura_Window_Bars` | 90 x 5 x 90 | 300 | Iron | Five 25 mm square bars (25 mm keeps Virtual Shadow Maps clean) |
| 8 | `SM_Kura_Window_Shutter` | 45 x 12 x 90 | 1,000 | Plaster + trim | Placed open (day) or closed (night) by rotation; no Blueprint |
| 9 | `SM_Kura_Corner_250` | 30 x 30 x 250 | 150 | Plaster | Inside corner return, stacked twice |
| 10 | `SM_Kura_Post_500` | 15 x 15 x 500 | 100 | Wood trim | Exposed post at every 100 cm bay line, 5 cm proud. Defines the display slots |
| 11 | `SM_Kura_Nuki_1` / `_2` | 100 or 200 x 3 x 12 | 50 | Wood trim | At +150 and +250 |
| 12 | `SM_Kura_EavePlate_2` | 200 x 30 x 30 | 100 | Wood trim | Wall top at +500 |
| 13 | `SM_Kura_Gable_Half_4` | 400 x 30 x 200 (triangle) | 200 | Plaster | Both gable ends, mirrored halves |
| 14 | `SM_Kura_Floor_Plank_2x2` | 200 x 200 x 5 | 50 | Tiling sugi | Top at +50. Two variants so seams do not repeat |
| 15 | `SM_Kura_Floor_Doma_2x2` | 200 x 200 x 5 | 50 | Tiling earth | Top at grade |
| 16 | `SM_Kura_StepBeam_2` | 200 x 25 x 50 | 200 | Wood trim (keyaki) | Step-up at Y 200 |
| 17 | `SM_Kura_StepStone` | 75 x 50 x 25 | 600 | Tiling stone | Kutsunugi stone |
| 18 | `SM_Kura_Truss_8` | 800 x 30 x 200 | 6,000 | Wood trim | Curved tie beam, struts, bearing blocks. Every 200 cm. Nanite |
| 19 | `SM_Kura_Purlin_2` | 200 x 12 x 12 | 50 | Wood trim | Between trusses |
| 20 | `SM_Kura_Ridge_2` | 200 x 20 x 25 | 80 | Wood trim | |
| 21 | `SM_Kura_RoofUnder_2` | 200 x 447 (sloped) x 15 | 1,000 | Wood trim + plaster | Rafters at 45 cm, plaster between. Closed, 15 cm |
| 22 | `SM_Kura_LintelBeam_8` | 800 x 30 x 45 | 3,000 | Wood trim (keyaki) | Adze-faceted log; frames the sanctum at Y 900. Nanite |
| 23 | `SM_Kura_Platform_1x1` / `_End` | 100 x 100 x 30 | 300 | Wood (hinoki) + fabric runner | Grows in 1 m steps |
| 24 | `SM_Kura_Dais_1x1` | 100 x 100 x 25 | 300 | Wood + vermilion edge | Sanctum dais (x3), cloak dais |
| 25 | `SM_Kura_WallRail_2` | 200 x 4 x 12 | 100 | Wood trim (hinoki) | The universal rail: sockets `Mount_00..07` every 25 cm, fixed to posts at 90/120/160/200 above the floor. Every insert docks here |
| 26 | `SM_Kura_Ext_DoorFace` | 400 x 60 x 500 | 5,000 | Plaster, namako tile, trim, roof tile | The one exterior face: namako skirt, outer jabara reveal, small door hood. **Phase 1**, because C1 and the dolly need it |
| 27 | `SM_Kura_Ext_Apron_4x3` | 400 x 300 x 5 | 50 | Tiling earth | Ground outside the door |
| 28 | `SM_Kura_InnerFrame_2` | 200 x 12 x 250 | 400 | Wood trim | Timber frame and bar lattice of the inner sliding door, placed open |

**Rail inserts (5):** `SM_Kura_Rail_Peg` (3 x 12 x 3), `SM_Kura_Rail_Hook` (tags), `SM_Kura_Rail_BracketPair`
(long weapons, 8 x 18 x 12), `SM_Kura_Rail_Shelf` (100 x 35 x 4 + brackets), `SM_Kura_Rail_Board` (100 x 3 x 60
backing board). 100-600 triangles each.

**Dressing (6 props, 0.5-2k each):** tansu 90 x 45 x 100; kiri box set (30 x 20 x 10, 80 x 15 x 15, 50 x 50 x 30,
blank, no labels); andon lantern 30 x 30 x 80 (emissive paper, no visible flame); karabitsu chest 90 x 60 x 70;
zabuton 55 x 60 x 8; fire bucket 30 dia x 30.

**Cut from the kura direction** (cost judge): the loft, joists, loft floor, balustrade, stair chest, the gable
window (it would backlight and silhouette the sword's front relief), the three door and shutter Blueprints, and
the separate facade kit. The loft and stair return as optional P7.

### 7.2 Budgets

| Budget | Value | Note |
|---|---|---|
| Environment in view, LOD0 | about 150k triangles (ESTIMATE) | Shell about 25k, 5 trusses 30k, roof undersides 12k, lintel 3k, door face 5k, dressing about 30k with instances, displays about 30k |
| Items in view, LOD0 | about 240k (DERIVED) | Stars and spike about 9k, kunai x4, tags x5 about 6k, smoke bombs 3 x 16.1k, hat 16.5k, fan, **sword 19,386 (v4)**, sheath budget 20k, cloak 84.6k, heels budget 2 x 10k |
| Texture sets | 1 x 4K timber trim; 5 x 2K tiling (plaster, sugi planks, tataki earth, stone, roof and namako tile); 4 x 2K display-family atlases; 1 x 2K decal atlas; 1 x 1K iron trim | 12 sets |
| Texture memory | about 150 MB with mips (ESTIMATE) | 4K set about 43 MB (BC1 10.7 + BC5 21.3 + ORM 10.7), each 2K about 10.7 MB, 1K about 2.7 MB. Item textures are extra and already counted by their packs |

### 7.3 Content roots

| Root | Holds | Gate |
|---|---|---|
| `/Game/KuraKit/` | Architecture, dressing, rail inserts, environment masters and textures | **Dependency gate:** nothing here may reference `/Game/NinjaPack/`, `/Game/Armory/` or any third-party asset from DemoGame_1 (Ultra Dynamic Sky, Megaplant, the fisherman's cabin). Keeps the kit sellable |
| `/Game/Armory/` | The level, the display pieces, `BP_DisplaySlot`, the data tables, camera and light presets, item colour MICs | May reference NinjaPack and KuraKit. Never shipped as a kit |

---

## 8. Display pieces: one for every item

**Families.** Five reusable stand families plus three hero stands cover all 15 items. A new item uses a family
variant unless it is a true hero (section 14).

| Family | Variants | Items now |
|---|---|---|
| F1 Tray | 1 / 3 / 7 slot, on a `DSP_Bundai` low desk | Five discs, spike |
| F2 Kake (sword-stand arms) | small 2-tier (kunai); tall upright (sword + sheath, hero) | Kunai, sword, sheath |
| F3 Form post | head-form top (headwear); torso-and-yoke top (garments) | Kasa, cloak |
| F4 Plinth and tiers | plinth S/M/L; sanbo; fuda stand; 2-step cloth tiers | Smoke bomb, paper tag, heels, fan base |
| F5 Wall rail inserts | peg, hook, bracket pair, shelf, board | Kunai (extra), tags (extra), future weapons |
| Hero | `DSP_TachiKake`, `DSP_FanStand`, `DSP_TargetPost` | Sword and sheath, fan, the kunai-and-tag pairing |

**Palette rule for every display:** no black lacquer and no dark wood on any surface an item touches. Surfaces are
pale hinoki or kiri, vermilion lacquer, undyed or indigo or red cloth. Every display is measured against its item's
sidecar or report, then blind-judged against its real precedent, as the props were.

| Item (from `ITEM_INVENTORY.md`) | Display | How it uses the item's sockets | Place |
|---|---|---|---|
| **Shuriken four-point, eight-point, senban, six-point, hooked cross** (7.62-10.78 cm across, 1.9-3.0 mm thick) | `DSP_Tray_7` (F1): kiri tray 50 x 40 x 4, indigo cloth lining, **six 115 mm wells** at 140 mm pitch (3 x 2) plus one 170 x 30 mm spike slot. Tilted 15 degrees toward the door on a `DSP_Bundai` desk 60 x 36 x 25. Well 6 is a growth slot. Precedent: collectors' cloth-lined compartment boxes | Display sockets `Slot_01..07` at the well centres. Each disc seats by its origin (the `Trail` socket, 0,0,0) with the flat face +Z up, and the well's yaw set from the item's `Grip` yaw so the grips align. The largest form (senban, 107.8 mm) has 3.6 mm clearance. **Hooked cross: yaw only; the slot validator rejects any negative scale** | Platform, Y 400: in the east-window sun patch so the grind rakes |
| **Spike / bo-shuriken** (15.0 x 0.6 cm) | Slot 7 of the same tray, a fitted groove | Seats by its origin (the centre of mass), point +X toward the viewer's right | Platform, Y 400 |
| **Plain kunai** (28.0 cm; Tip, Grip, Ring, Trail) | `DSP_Kake_S` (F2): vermilion two-tier stand 36 W x 22 H x 12 D (Met katana-kake proportions). Top tier: shipped wrap. Lower tier: the **Undyed** wrap preset, which ships, so showing it is honest | Seats by `Grip` in the arm notch, tip to the viewer's left (yaw 180), lettering face +Z up, `Ring` hanging free | Platform, Y 540 |
| **Plain kunai, extra** | Rail pegs (F5) on the west rail | Hangs **by its own `Ring` socket**, tip down. The peg socket sits 0.5 cm below the top of the ring's 2.0 cm inner hole (DERIVED), so the fit is exact by construction | West wall, Y 700-900, rail at 120 |
| **Smoke bomb** (7.0 cm ball) | `DSP_Sanbo` (F4): hinoki offering stand, 21 x 21 cm tray, 18 cm tall, a folded blank paper sheet. **Three bombs in a triangle, in three colours** (shipped `#3F3A37`, indigo, undyed) through the documented `Colour` parameter, as child MICs in `/Game/Armory/` | Seats by `Grip` (the ball centre) at `Slot_1..3`. Each is rotated so its -Y reference view faces the door and the crumpled pocket faces away. `Burst` unused (no smoke VFX) | Platform, Y 670, in the second sun patch: gives the weakest tile a silhouette |
| **Paper bomb / tag** (16.2 x 7.0 cm) | `DSP_FudaStand` (F4): hinoki holder 30 W x 24 H x 10 D, three slots leaning back 8 degrees, print facing the door, square-on to the door's sky light. No glass | Seats by `Attach` (roll 180) on the slot's back face, so `Face` points out. The slot width is a parameter (allow 1 cm slack: the tag's exact pass is still queued) | Platform, Y 320, nearest the door |
| **Paper tag + kunai pairing** (the pairing the inventory calls strongest) | `DSP_TargetPost` (hero): hinoki log post 20 cm diameter x 150 cm on a cross foot, bark on, cut marks | Kunai embedded tip-first **by its `Tip` socket**, 4 cm deep. A tag hangs from it: tag `Cord` socket = kunai `Ring` socket, tag long axis rotated to hang down. Stars embed **by a point, never by `Trail`**: display-side sockets `Embed_<Form>` at the tip radius minus 1.2 cm depth (tip radius DERIVED: four-point 4.85, eight-point 5.0, six-point 4.90, hooked cross 5.0, senban corner 5.39 cm). Spike embeds by its point (about +7.9 cm from its origin, ESTIMATE: measure on the mesh). A static placement, never described as a gameplay feature | Doma, X 120, Y 100 |
| **Black hat / kasa** (60.3 x 61.7 x 23.9) | `DSP_FormPost` with the head-form top (F3): turned post on a cross foot 60 x 60 x 8, a cloth-wrapped head form sized to a 57 cm head, undyed | Hat `HEAD` socket snaps to the stand's `Head` socket, placed at 150 above the floor (ESTIMATE) so the brim is at about 136 and the tails clear by 12 cm or more. Knot side (+Y) and front toward the aisle. 70-80 cm wide bay | West wall bay Y 500-600, 60 cm off the wall |
| **Folding fan** (skeletal; open 37.3 x 21.0, closed 21.0) | `DSP_FanStand` (hero): vermilion cradle easel 30 W x 18 D x 22 H on an F4 plinth 60 x 60 x 90. A V-notch holds only the handle below the rivet | Pivot at the rivet (`Pivot` socket). Front (+Z) toward the aisle, turned 20 degrees toward the door. **Closed at rest**; `A_Fan_Openness` (Sequence Evaluator, 0-1) follows the player's distance inside 2 m; C6 plays `A_Fan_OpenClose`. Tassel AnimDynamics `tassel_root` to `skirt_02`, ignoring fan collision. Ticks only within 6 m. Clearance proven at G0-7 | East wall bay Y 300-400 |
| **Snow Flower sword v4** (125.6 tall; Grip at 0, BladeBase 12.85, BladeTip 104.0) | `DSP_TachiKake` (hero, F2 tall): upright stand, pale hinoki post and vermilion base 60 W x 35 D, about 150 tall, two arms (sword and sheath 30 cm apart). Precedent: tachi-kake | Seats by `Grip`, blade +Z up. The item's -Y front (blossom relief), guard and pommel medallion face world -Y, down the axis: **identity yaw**. A pommel cup at dais + 22 puts `Grip` at dais + 43.6 and the tip at about +223 world (DERIVED from the v4 bbox, z -21.6 to 104.0). The upper arm holds the blade 22 cm below `BladeTip`, never at the tip. Recompute from the final v4 sidecar | Sanctum dais, X 340, Y 1150 |
| **Snow Flower sheath** (100.8 long DESIGNED; not built) | Second arm of `DSP_TachiKake`, upright, mouth up, front (blossoms and vine) toward the axis | `Slot_Sheath` binds to the sheath's `Holster` socket when v4 ships it. Until then, the box proxy from the spec. **Sheathed** state waits on the tip decision (section 16, D5). A draw-on-interact Blueprint (sword slides out along the sheath's -Z from `Holster`) is optional P7 | Sanctum dais, X 460, Y 1150 |
| **Snow Flower heels** (pair; about 24-26 long, ESTIMATE; not built) | `DSP_Tiers_2` (F4): two 12 cm steps with red wool cloth (hina-dan convention, `Colour` recolourable) on a plinth 60 x 50 x 75. Soles at 87 and 99 cm above the floor (inventory asks for 90-110) | Display sockets `Slot_L` (top step, left shoe in profile, heel and silver vine toward the aisle) and `Slot_R` (lower step, 3/4 front, toe cap). **Two distinct meshes, never a mirrored copy.** Seat at sole contact. 20 % margin until the mesh exists; confirm a heel-pose static copy stands on its own | East wall bay Y 500-600 |
| **Black cloak** (103.2 x 67.8 x 172.1, ground origin; review queued) | `DSP_FormPost` with the torso-and-yoke top (F3), gusoku-kake style: a hidden post, 45 cm shoulder bar and a padded torso block (about 36 x 22 x 55, ESTIMATE) filling the hollow neck and chest, on a 1 x 1 dais. Undyed cloth | Stand `Root` socket at the dais top = the cloak's ground origin (static mesh, no cloth sim). Front to the aisle, back to the wall until the interpreted back is reviewed. **Torso block sized from the final mesh after review** | West wall bay Y 300-400 |

---

## 9. Materials, and how they join the pack colour system

| Rule | Detail |
|---|---|
| Items never change | Every item keeps its shipped `MI_<Item>_<Part>`. The armory only adds **child MICs** of them in `/Game/Armory/` through the documented `Colour` parameter (the smoke-bomb trio, heel cloth). What is shown is what ships |
| New masters are new, never edits | Four environment masters are added to `material_spec.json` under a new `environment` section and built by the same `np_*` builder (`Scripts/unreal/materials/`). Never rebuilt in place (MATERIALS_REPORT section 3, the UE 5.8.3 finding). Verified in a fresh process. The existing masters' dumps stay byte-identical and `check_exports_frozen.sh` stays 63 of 63 |
| No tiling group on the frozen masters | The kura draft added a tiling group to `M_Fabric_Master` and `M_Steel_Master`. Cut: both judges flagged the risk. Instead, every cloth and iron surface on the displays gets **unique UVs** (a 1 x 1 m runner at 2K is 20 px/cm), so plain MIs of the existing masters work with no graph change |
| One colour behaviour | Every new master uses `MF_TintDetail` and `MF_NormalStrength`, so plaster and wood recolour with the same `Colour` and `Lightest Colour` sliders buyers already know, including the highlight cap and mip compensation. Groups follow the pack scheme: 01 Colour, 02 Detail, 03 Surface, 06 Blend (new), 07 Trim (new), 09 Textures |
| Substrate | DemoGame_1 runs Substrate; the pack project does not. The new masters pass verification in both |

| Master | New or reused | Used for |
|---|---|---|
| `M_Kura_Plaster_Master` | NEW | Tiling shikkui, warm white, **albedo capped at 0.80**. Vertex colour R blends to exposed clay, G to grime and soot, B to water streaks. Trowel-mark normals |
| `M_Kura_Wood_Master` | NEW | Tiling planks, plus a 4K timber trim-sheet mode (posts, beams, nuki, jabara steps, stand parts). Species as MIs: sugi aged (floor), keyaki dark (**overhead only**), hinoki pale (platform, stands), kiri pale (tray, boxes), vermilion shu lacquer with a clear-coat switch |
| `M_Kura_Surface_Master` | NEW | Tataki earth, step stone, namako and roof tile on the door face |
| `M_Kura_Decal_Master` | NEW (DBuffer) | Soot above the andon, drip streaks under the windows, trowel repairs, footpath polish. One 2K atlas |
| `M_Steel_Master` | REUSED, MI only | `MI_Kura_Iron` (Steel Tint to blackened iron) with a new 1K iron trim: bars, hinges, pull rings, chest corners, pegs |
| `M_Fabric_Master` | REUSED, MI only | Tray lining (indigo), platform runner (undyed), heel tiers (red), head and torso forms (undyed). Each new fabric MI needs its recolour constants derived by the existing maps tool (about 0.25 day each) |
| `M_PaperInk_Master` | REUSED, MI only | Blank paper under the smoke bombs. No inked text anywhere |

**Room palette** (ESTIMATE; tuned at the G0-1 contrast gate). The black-and-silver items are the darkest things in
the room by design.

| Surface | Colour | Note |
|---|---|---|
| Plaster | `#E6E0D3` | Warm white, under the 0.80 cap |
| Hinoki (platform, stands) | `#D8BE93` | |
| Kiri (tray, boxes) | `#CFBBA0` | |
| Sugi floor, aged | `#8E765B` | Mid value, never under an item |
| Keyaki (beams, step) | `#4B3727` | Overhead and structural only |
| Vermilion lacquer (accent) | `#B8412A` | Stand accents, dais edge |
| Indigo lining (cool) | `#2E3B56` | Under the steel stars: dark, but the stars are black-coated steel with bright edges; checked at G0-1 |
| Red wool (heel tiers) | `#9E2A23` | Recolourable |

---

## 10. Lighting

Lumen GI and reflections, hardware ray tracing in showcase mode (RTX 4070 SUPER), software fallback checked in
gameplay. Virtual Shadow Maps for the bar shadows. Low-density volumetric fog so the shafts read. **Manual exposure
per camera** (no pumping when the doors open). Presets live in `DT_LightingPresets`, selected by the camera preset.

| Preset | Key | Fill | Accent | Use |
|---|---|---|---|---|
| **Airing Day** (default) | Sun from due east through the two east windows, **38 degrees** elevation, about 5200 K. DERIVED: window centre +395 to platform top +80 is 315 cm of drop over 400 cm, so both barred patches land on the platform (X 343-457) at the tray and the sanbo | The open door: sky light plus a large soft sky rect through the 150 x 200 opening, about 7500 K, a long low fill down the axis. White plaster does the bounce | Sanctum: andon (2400 K point, 15 cm source radius) beside the dais, plus a hidden soft rect in the lintel soffit, raking the sword at about 45 degrees from the front (Toukenza). **No backlight on the sword**: it would silhouette the -Y relief | Walkthrough, trailer, C1-C4, C10 |
| **Afternoon Rim** | Sun from the west at about 20 degrees through the west windows onto the east wall | Door | Rim light on the cloak and kasa from the opposite shafts | C5, C8 |
| **Inspection** (from the yagura direction) | None. Neutral 5000 K sky light | A soft overhead rect per display, fog off | none | Honest in-engine material shots for Fab. Every showcase still names its preset |
| **Night** | Shutters closed (rotated instances), doors shut | Thin moon slit through one window | Andon practicals, emissive paper, no visible flame | Gameplay mood only; **never in Fab media** |

Showcase cheat lights (the lintel soffit rect, small card lights per macro camera) exist only in showcase mode and
are never visible. Plaster albedo is capped at 0.80 and wood at 0.35-0.55 so Lumen does not bloom. Andon practicals
are real lights, not tiny bright emissives (Epic notes those cause Lumen noise).

---

## 11. Showcase cameras

Frame check (G0-3) uses a 36 x 20.25 mm (16:9) sensor. Positions are world cm. All are ESTIMATES until G0.

| Id | Position (X, Y, Z) and aim | Lens | Shows | Preset | Fix vs the kura draft |
|---|---|---|---|---|---|
| C1 Doors-open reveal | (400, -250, 160), +Y | 35 mm | The door reveal, the shafts, the platform, the sword 14 m away | Airing Day | Needs the door face: moved into phase 1 (`SM_Kura_Ext_DoorFace`) |
| C2 Kit overhead | (400, 850, 420), -Y, 41 degrees down | 35 mm | Every platform item in one frame, 4.7 m away. A Sequencer camera: no balcony needed | Airing Day or Inspection | Was 50 mm from a loft balcony; 50 mm covers only about 1.9 m and cannot hold the 4 m platform (DERIVED); 35 mm covers about 2.7 m |
| C3 Sword and sheath | (400, 710, 150), +Y, 4.4 m | 50 mm, landscape (or 85 mm portrait crop) | The full upright sword beside the sheath, black on white plaster | Airing Day | Was 85 mm at 2.9 m, which sees only about 0.8 m vertically and cannot frame a 1.5 m subject. 50 mm at 4.4 m covers 1.8 m (DERIVED) |
| C4a-d Platform macros | One per stand, about 60 cm away, square to the tray tilt or the fuda face | 100 mm | Tray, kunai kake, sanbo, fuda stand (the tag square-on: "the print is the product", SHOWCASE_PLAN 5.1) | Airing Day or Inspection | Within 0.89 m, so LOD0 without forcing |
| C5 Cloak | (560, 350, 150), -X, about 5 m | 50 mm | The full 1.72 m cloak and its stand | Afternoon Rim + a 3/4 front fill | The dojo lit the cloak from behind only; this adds a front key |
| C6 Fan fold | (630, 350, 155), +X, 1.1 m (the rivet sits at about +152: plinth 90 on the +50 floor plus the stand, ESTIMATE) | 85 mm | `A_Fan_OpenClose` played live: the selling fact is that it folds (SHOWCASE_PLAN 5.2). Front-on or 45 degrees or more, never a low 25-30 degree oblique (the slits show) | Airing Day | Fan is closed at rest (the kura draft said open) |
| C7 Heels | (630, 550, 145), +X, 1.2 m | 85 mm | The pair: left in profile, right at 3/4 | Airing Day | Was z 45, inside the +50 floor. Now at shoe height on the raised tiers |
| C8 Kasa, low 3/4 | (170, 520, 90), looking up at the hat | 50 mm | The woven outer and the brim edge. The underside is plain inner weave with a seat disc (BLACKHAT_REPORT): shown honestly, not featured | Afternoon Rim | |
| C9 Dolly | C1, through the door, along the axis at +150, ends on C3 | 35 to 50 mm | Listing and trailer video | Airing Day | |
| C10 Target macro | (200, 160, 130), toward the post, about 1.0 m (a 36 cm wide frame at 100 mm) | 100 mm | Kunai stuck in wood with the tag tied on, stars embedded (the shot SHOWCASE_PLAN 8 left for later) | Airing Day | New (grafted from the dojo) |
| C11 Gameplay read | The player's third-person boom, walking the aisles | Game FOV | The in-game read of every bay | Airing Day | New: runs the G0-2 gate |

**LOD in shots.** Cameras beyond 0.89 m (C1, C2, C3, C5, C9) switch the item components to forced LOD0 through the
camera preset, and the still says so. Gameplay keeps normal LOD switching.
**Fab media rule** (from the dojo). Armory shots appear in item listings only with the caption "display
environment not included", or in a listing for the kit itself. White-background gallery tiles still come from the
Blender showcase rig; the armory adds in-context shots and does not replace the rig. No smoke, burn or fire VFX in
any media.

---

## 12. Adding new items later

**The slot system.** One `BP_DisplaySlot` actor per display slot. One row per item in `DT_ArmoryItems`. A rebuilt
item (such as Snow Flower v4) re-seats itself on reimport; a new item needs a row, not new level geometry.

| Column | Example (kunai on the rail) |
|---|---|
| `RowName` | `Kunai_Plain_Rail_01` |
| `ItemAsset` (soft reference, static or skeletal) | `/Game/NinjaPack/.../SM_Kunai_Plain` |
| `ItemSocket` | `Ring` |
| `DisplayFamily`, `Variant` | `F5_Rail`, `Peg` |
| `SlotId`, `DisplaySocket` | `W_Rail_120`, `Mount_03` |
| `ColourMIC` (optional) | none (shipped MI) |
| `CameraPreset`, `LightPreset` | `C4_Macro`, `AiringDay` |
| `ForceLOD0InShowcase` | true |
| `AllowMirror` | always false. The validator rejects negative scale on every row (the hooked cross must never mirror) |

Slot world transform = display socket x inverse(item socket). An editor utility, "Reseat all", runs after any item
reimport and reports every seat error over 1 mm.

**Growth order.**

| Step | When | Cost (ESTIMATE) |
|---|---|---|
| 1. A free slot in an existing variant (a new star, a new tag, a new kunai) | Tray well 6, rail mounts, spare fuda slots | **0.25-0.5 day**: a row, a seat check, a camera preset |
| 2. A new variant of a family (a 3-slot tray, a taller form post, a 3-step tier) | The item fits a family but not a variant | **about 1 day** with a blind round |
| 3. A bespoke stand (a spear, a bow, armour) | Only for true heroes | **2-3 days** with blind rounds |
| 4. Use the free bays | 8 marked bays now (6 in the hall, 2 in the sanctum) plus rail mounts | Included in steps 1-3 |
| 5. Lengthen the platform | +1 m per `SM_Kura_Platform_1x1` | 0.25 day |
| 6. Lengthen the building | +200 cm per truss bay: move the north wall, sanctum and lintel 200 cm north. No new kit | **1-2 days** |
| 7. A second kura | When a whole new category arrives (armour, costumes) | A new level from the same kit |

---

## 13. Phased build order

Every phase ends with something the user can walk through in PIE. Day counts are ESTIMATES scaled from the prop
builds, where a hero prop took 2-4 sessions with its blind rounds. Render and verify effort is listed separately
because it uses the shared machine.

| Phase | Work | Days | Ends with (walkable) | Render and verify effort (ESTIMATE) |
|---|---|---|---|---|
| **P0 Decisions** | The user answers section 16 and supplies or approves the mood image | user | An approved scope | none |
| **P1 Greybox (G0)** | Section 6: block the room, drop in every finished item, place all 11 cameras, 4 light presets as proxies, slot system v0 | **3** | The cube room with every finished item at true scale, on proxy stands, seated from data rows. **USER GATE** | One editor session of about 3 h; 11 stills + histograms; no commandlet |
| **P2 Shell** | 28 architecture pieces (modelling, UV to trim, UV1, UCX, `qa_check`) 7 d; 4K trim, 5 tiling sets and decal atlas as Blender bakes with real AO 5 d; the 4 environment masters in the spec build + fresh-process verify + frozen-exports proof 3 d; assembly and leak sweep 1 d | **16** | The finished empty kura with the Airing Day light, the door face and the doors open | 28 x `qa_check` (about 1 min each); 1 material-build commandlet + 1 fresh-process dump + `check_exports_frozen.sh`; 2 editor sessions for assembly and the leak sweep |
| **P3 Families + slots** | `BP_DisplaySlot`, data tables, Reseat utility 2 d; F1 tray 1.5 d; F2 kunai kake 1.5 d; F3 form post (head top) 1.5 d; F4 sanbo, fuda stand, plinths, tiers 3 d; F5 rail and inserts 1 d; fabric MI constants 0.5 d | **11** | Every finished small item (discs, spike, kunai, smoke bombs, tags, kasa) on its real display, placed from data rows | Each display: 2-4 blind rounds of about 6 Blender renders (about 10 min render per display) + a UE import check; 1 editor session for placement |
| **P4 Heroes** | `DSP_TachiKake` 2.5 d (built last, after v4 is final); `DSP_FanStand` + proximity Blueprint + the 41-opening proof 2 d; `DSP_TargetPost` + embed sockets + tag pairing 1.5 d; cloak torso top after the review 1.5 d; heel tiers re-fit when the heels exist 0.5 d | **8** | Sword and sheath (sheath as proxy until built), the fan opening as you approach, the target post, the cloak on its form | As P3, plus a fan animation capture at 41 openings |
| **P5 Light + cameras** | 4 presets tuned against the G0 gates 3 d; 11 cameras, Sequencer dolly, Movie Render Queue settings 2 d | **5** | Switch Airing Day, Afternoon Rim, Inspection and Night in PIE; the shot set rendered | 11 MRQ stills per preset used (about 2-5 min each with HW RT, ESTIMATE); dolly 2 x 20 s at 30 fps (about 2-4 h, overnight when the machine is free) |
| **P6 Dressing + perf** | 6 dressing props 3 d; decals, frame-time and Lumen tuning, final verify 1 d | **4** | The finished room | 1 perf capture per camera; a final fresh-process material verify |
| **Total** | | **47** | | **About 56 with 20 % contingency** |
| P7 Optional, each approved on its own | Animated kannon doors and shutters (2 d); sword draw-on-interact Blueprint (1.5 d); loft, balcony and stair chest (6 d); KuraKit Fab packaging (3 d) | | | |

**Leaner path** (section 16, D9). P1 + a lean P2 (about 20 pieces, tiling materials only, no trim bake: about 10 d)
+ P3 gives a walkable room with every finished small item in **about 24 days**, closer to the cost judge's 20-25 day
minimum room, at the price of flatter timber detail until the trim sheet lands.

**Machine schedule.** One Unreal commandlet at a time; claim the asset lock per `.blend` and per `.uasset`. P1 waits
until the Snow Flower v4 Unreal check is finished and must never overlap the MetaHuman spike (about 11 GB editor). The
fan and kunai reworks stay stopped unless the user authorises them; the armory does not unblock them. Sessions that
only plan, read and write Markdown (like this one) can run in parallel with builds.

---

## 14. Risks

| # | Risk | Mitigation | Check |
|---|---|---|---|
| 1 | **Dimness vs product clarity.** Small windows make a dim room, and Lumen is noisy in dim interiors | White plaster bounce, the open door, per-camera cheat lights, manual exposure, the Inspection preset | G0-1 contrast and G0-4 stability |
| 2 | **Black items on dark surfaces** if the palette slips | The palette rule in section 8; no black lacquer anywhere an item touches | G0-1, re-run at P5 |
| 3 | **Small items unreadable at play distance** (a 10 cm star from a 375 cm boom) | Items raised on the platform in 3.5 m aisles; a close camera per stand | G0-2; fallback: the vertical star board (D6) |
| 4 | **Snow Flower in flux**: v4 is exported and in its Unreal check; its sockets are not in the FBX; the length is unconfirmed | The stand binds by data row and is built last in P4; sockets recreated from the sidecar | G0-8, G0-9; Reseat after every reimport |
| 5 | **Sheath not built**; sheathed state blocked on the tip decision (SHEATH_REFERENCE_SPEC 9.4) | Box proxy from the spec; drawn sword and empty sheath side by side until then | Re-fit at P4 |
| 6 | **Heels not built**; no female foot form; the reference image's provenance and AI-disclosure status is unaudited | Tiers with 20 % margin; bay reserved with a proxy; audit the reference before any Fab use | Re-measure when the mesh exists |
| 7 | **Cloak unreviewed**: 84.6k LOD0 against the 30k garment budget, no ORM, own recolour material outside the pack system, fit untested | Display the static mesh; size the torso block only after the review; its bay holds a proxy if it is rebuilt | Review gate before P4's cloak task |
| 8 | **Fan on a stand**: the leaf or tassel could touch the cradle; ACL compression cracks the leaf | Handle-only V-notch; keep DefaultRecorderBoneCompression and `bounds_extension_cm` | G0-7 at 41 openings |
| 9 | **Frozen pack masters**: any edit could change shipped instances | New environment masters only; MIs of the old ones; no tiling group | Byte-identical dumps and 63 of 63 frozen exports each material build |
| 10 | **Lumen and shadow artefacts**: bars aliasing in VSM, shaft cost, thin trims leaking | Bars 25 mm or more, walls 30 cm, roof 15 cm closed | G0-4, G0-5 in the real Unreal build, not in Blender |
| 11 | **IP and cultural drift**: crests, temple names, inked text, franchise props | All boxes and labels blank; no crest on the door face; generic vernacular kura; `qa_check` deny list on kit names | Review at P2 and P6 |
| 12 | **Third-party contamination** of the kit | Dependency gate on `/Game/KuraKit/` | Reference viewer check at P2 and P6 |
| 13 | **Scope**: 47-56 days is larger than any item so far and competes with the item queue | P1 is a real stop; each P7 extra is approved alone; the leaner path exists | User gates |
| 14 | **Shared machine**: collisions with other sessions and the pack project | Own project, one commandlet at a time, locks | Before every Unreal run |
| 15 | **Paper tag size may shift** (exact pass queued) | Parametric fuda slots with 1 cm slack | Reseat after the tag's final export |

**What this plan gives up.** No grand hall, no "wall of a hundred weapons", no combat floor, no garden or sky shots,
and a limited palette (white, pale wood, one vermilion accent, one indigo) that risks sameness over many shots.
Long items over about 2.5 m fit only upright in the hall. It spends real effort on a room that is mostly for
looking, not playing.

---

## 15. Doing this planning in parallel

The user asked whether to run the armory planning in another chat. Yes: planning is read-only research and writing
under `WorkFiles/armory/`, so it can run beside the build sessions without conflict. The limits: the planning chat
must not open Unreal or Blender, claim asset locks, or start P1. The greybox and everything after it wait for the
user's explicit go and for Unreal to be free (one commandlet at a time). When the Snow Flower v4 check, the sheath
build or the heels change an item, re-read `ITEM_INVENTORY.md` and update the affected rows here before P1.

---

## 16. Decisions for the user

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Style | Kura / dojo / yagura | **Kura, one storey** (sections 1-2). It is the only room built around a black-and-silver line; the cuts bring it close to the dojo's cost |
| D2 | Mood image | A CC photo; a paint-over of the greybox C1 frame; an AI image | **M1 (Ishitani House kura, CC BY-SA 4.0)** now; if it lacks the shaft, a paint-over of the G0 C1 frame after P1. Record any AI use for Fab disclosure |
| D3 | Loft and double-height well | Build now / later / never | **Later (P7)**. C2 works from a free camera, and the loft costs about 6 days |
| D4 | Doors | Static open / animated kannon doors and shutters | **Static open** in P2; animation in P7 only if a trailer is planned |
| D5 | Sword and sheath | Upright side by side / horizontal kake (edge up, hilt left) / sheathed | **Upright side by side**, drawn sword and empty sheath, because it reads down the 14 m axis. Sheathed waits on the sheath tip decision (straight back edge, 8 mm bow or hidden blade, SHEATH_REFERENCE_SPEC 9.4); a draw-on-interact Blueprint is P7 |
| D6 | Shuriken display | Tilted tray on the platform / vertical wall board | **Tray**. Build the board only if the tray fails the G0-2 read test |
| D7 | Smoke bombs | One colour / three-colour trio | **Trio** (shipped, indigo, undyed): it shows a recolour system that really ships |
| D8 | VFX | Smoke wisp from `Burst`, burn from `Fuse` | **None in any media.** Optional in gameplay only, later |
| D9 | Scope path | Full (47 d, about 56 with contingency) / leaner (about 24 d to the first walkable room) | **Full, gated per phase**, with P1 as the hard stop. Choose the leaner path if the item queue must restart sooner |
| D10 | Project | A new `ArmoryLab` project / inside DemoGame_1 / the pack project | **A new project** with DemoGame_1's render settings (Substrate, Lumen HW RT). Migrate to the game when it is finished. Never the pack project |
| D11 | Wearable bays (heels, cloak) | Build their stands now / reserve with proxies | **Reserve with proxies.** Build the heel tiers when the heels exist and the cloak form after its review |
| D12 | Sword length | Keep 1.256 m / resize for the player | Decide at G0-9, standing next to the player character |
| D13 | Sell the kit on Fab | Plan for it / game-only | **Keep the option open** (own root, dependency gate, UV1, LODs); decide after P3. Modular kits sit in the $49.99-129.99 band (FAB_ASSET_STUDY section 6) |
| D14 | When P1 starts | Now / after the current queue | **After the Snow Flower v4 Unreal check finishes**, and only when you say go |
