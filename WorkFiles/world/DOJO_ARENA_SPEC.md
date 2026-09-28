# Dojo Courtyard Arena: layout spec

**Date:** 2026-09-27. **Status:** PLAN ONLY. Nothing is built, and nothing in DemoGame_1 was changed. The grey-box
(section 8) waits for the user's go.
**The user's choice:** "Dojo courtyard for the 1v1, optional to go on top of dojo roofs and walls." The arena later
becomes a named location on the battle-royale (BR) map.
**Scope (2026-09-27):** this file is about the **layout**: the zones, how they connect, and the real dimensions. The
detailed asset list comes later, from the reference image made with `DOJO_ARENA_IMAGE_PROMPT.md`.
**Drawing:** `DOJO_ARENA_TOPDOWN.svg` / `.png` (drawn to scale by `make_topdown.py` from the numbers below).
**Look:** `STYLE_GUIDE.md`.

## 1. Summary

| Item | Value |
|---|---|
| Compound | 44 x 36 m inside a 1 m thick perimeter wall (46 x 38 m overall), inside the roadmap's "about 50 m across" |
| Fight floor | 28 x 17 m of raked sand in the middle, dead flat, nothing on it |
| Spawns | P1 at (14.5, 10.5) facing east, P2 at (29.5, 10.5) facing west: 15 m apart, as the roadmap asks |
| Dojo hall | 18 x 10 m on the north side, veranda (engawa) on three sides at +0.5, two-tier tiled roof: lower eave +3.0, upper eave +5.5, ridge +8.3 |
| Around it | Gatehouse in the south wall; storehouse (north-west) and residence (north-east) joined to the hall by covered corridors; a steel training shed (south-west); a drum pavilion (south-east); two trees; a well |
| High ground | Every wall top (+2.0) and the front-facing roofs are walkable. Every required climb is 2.0 m or less, using GASP's mantle |
| Boundary | An invisible wall on the outer edge of the wall top. The rear alley, the north wall top and every roof slope that faces away from the courtyard are closed in the 1v1 (they would be hiding places) |
| Time to the top | Ground to the hall's upper roof: 3 climbs, about 5 s (ESTIMATE, measured in the grey-box) |

**Frame used everywhere:** origin = the inside south-west corner of the compound at courtyard level; X east (0-44),
Y north (0-36), Z up, metres. The main gate is in the south wall at X 20-24. In Unreal: (x*100, -y*100, z*100), the
same mapping as the armory plan.

## 2. The layout at a glance

```
 Y 36  +--------------------------------------------+   north wall (1v1: out of bounds behind the hall)
       |SSSSSSSxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxRRRRRRR|   x = rear alley, closed in the 1v1
       |SSSSSSSxxxxeeHHHHHHHHHHHHHHHHHHeexxxxRRRRRRR|   S storehouse, R residence
       |SSSSSSSccccee  DOJO HALL 18x10 eeccccRRRRRRR|   c covered corridors
       |SSSSSSS    eeHHHHHHHHHHHHHHHHHHee    RRRRRRR|   e veranda (+0.5) under the lower roof
       |           eeHHHHHHHHHHHHHHHHHHee           |
       |           eeeeeeeeeeeeeeeeeeeeee        W  |   W well
 Y 20  |          T______________________T          |   T climb cisterns, _ stone step band
       |        .............::.............        |   . fight floor 28 x 17 m (raked sand)
       |   Y    .............::.............    Y   |   Y trees, : flush stone path
       |      m .............::............. m      |   m training posts
       |        .....1.......::.......2.....        |   1 / 2 spawns, 15 m apart
       |   rr   .............::.............   rr   |   r weapon racks
       |      m .............::............. m      |
       |ssssss  .............::.............   PPPP |   s steel training shed, P drum pavilion
 Y 0   |ssssss       V       ::                PPPP |   V vending machine
       +--------------------    --------------------+
      X 0                  main gate (GGG)           X 44
```
The SVG/PNG is the authoritative drawing; this sketch is for reading in a text editor.

## 3. The movement numbers, and the rules taken from them

GASP replaced our own movement on 2026-09-19 (`CLAUDE.md`), so `Movement_Study.md` is history: its jump numbers are
pre-GASP. Where a GASP number is not measured in this project, it says so, and the grey-box's first step measures it.

| Input | Value | Source |
|---|---|---|
| Capsule | radius 35 cm (70 cm wide), body height about 1.86 m | Radius: the armory's `walk_check.py` (Manny capsule, ARMORY_PLAN 3.3). Height: the MetaHuman head measured at 185.6 cm (`CLAUDE.md`) |
| Step-up | 45 cm | Engine default `MaxStepHeight`, also the armory's walk check |
| Walkable slope | 44.8 degrees | Engine default walkable floor angle. GASP's own value **not measured** |
| Vault / hurdle | obstacles about 0.5-1.25 m tall and thin | GASP's traversal system (`CLAUDE.md`: GASP vaults, mantles and hurdles over `LevelBlock_Traversable`-style geometry). Bands are GASP's shipped setup, **not measured here** |
| Mantle | ledges about 0.5-2.75 m above the feet | As above, **not measured here** |
| Jump | about 1.7 m apex (JumpZ 700, gravity 1.5), 1.95 m with the old asymmetric gravity | `Movement_Study.md` (pre-GASP). GASP's jump is not recorded. A second jump (front flip) exists: `MaxJumps` 2 |
| Speeds | run 575 cm/s (measured), crouch run 450 cm/s (measured) | `CLAUDE.md` free-look and stance tests |
| Prone | needs 70 cm ahead, 120 cm behind, 56 cm wide | `CLAUDE.md` (`HasRoomToLieDown`) |
| Lock-on | acquires within 20 m, lets go past 28 m, line of sight from the camera | `CLAUDE.md` (`LockOnRange` 2000, `LockOnBreakRange` 2800); traces use the Visibility channel (`Scenery_Options.md`) |
| Camera | spring arm 3.75 m, pivot +0.7 m, FOV 85; the roadmap's duel camera plans 4.5-7 m | `CLAUDE.md`; `MVP_Roadmap.md` 4.6 |
| Duel space | arena about 50 m across, spawns 15 m apart, knockback 3-5 m, chakra dash up to 10 m, Substitution reappears 2.5 m behind; low occluders, no hiding spots | `MVP_Roadmap.md` 4.6 and M4 "Arena check" |
| Future walls | Mud Wall 4 x 3 m placed 2.5 m ahead; Water Wall 3 x 2.5 m | `Loadout_System.md` |

**Rules derived from those numbers (these drive every height in this file):**

| Rule | Value | Why |
|---|---|---|
| R1 Required climbs | **2.0 m or less** from the surface you stand on | 0.75 m under GASP's ~2.75 m mantle ceiling, a margin for the unmeasured value. At 0.5 m or more a press of Space gives a traversal, not a step |
| R2 Steps | **0.25 m** risers (on the 25 cm height grid) | Under the 0.45 m step-up with margin; you walk up them without pressing anything |
| R3 Walk-on ledges | **at least 1.0 m deep** (wall tops, prop tops you land on, AC units) | Capsule 0.70 m plus 0.30 m; GASP needs room on top to land a mantle |
| R4 Walkable roofs | **25 degrees**, flat collision plane per slope | Well under 44.8 degrees; a real tiled-roof pitch (about 4.5-5 sun). Steeper decorative parts are marked unwalkable |
| R5 Headroom | **2.5 m or more** over anywhere a player walks | Body 1.86 m plus a jump start and camera room |
| R6 Jump gaps | none required. Gaps up to 2 m are single-jump shortcuts, 2-4 m double-jump shortcuts | The jump is not measured under GASP; nothing essential depends on it |
| R7 Fight floor | 28 x 17 m, 6.5 m behind each spawn to the yard edge, diagonal 32.8 m | Spawns 15 m apart; room behind for 3-5 m knockback plus a dodge; a 4 x 3 m wall fits anywhere; most of the floor sits inside the 28 m lock break |
| R8 Cover | nothing on the fight floor; in the yards only low cover (1.25 m or less) and thin uprights (0.4 m or narrower) | Roadmap: low occluders, no hiding spots. 1.25 m is the top of GASP's vault band, so low cover is vaultable |

## 4. The zones

### 4.1 Perimeter wall and main gate (the boundary)
- **Wall:** earthen plaster on a stone footing, tiled cap, **top +2.0**, 1.0 m thick, with a **flat 1.0 m walkable
  strip** on top (the tiles form a shallow cap 15 cm high visually; the collision is flat). Runs round the whole
  compound: X -1 to 45, Y -1 to 37.
- **Climbing it:** a single 2.0 m mantle from anywhere in the courtyard (route 1), or from the vending machine
  (route 8: machine top +1.75, then a 0.25 m step).
- **Main gate:** gatehouse straddling the south wall, roof 8 x 5 m (X 18-26, Y -2.5 to 2.5), opening **4.0 m wide x
  3.5 m high** (X 20-24), eave +3.25, ridge +4.4. Closed in the 1v1 (the gate leaves are the wall); the main
  entrance in the BR. Its roof is reached from the wall top (route 6, 1.25 m).
- **BR-only openings:** a rear wicket gate in the north wall (X 21.5-22.5) and a side wicket in the west and east
  walls (Y 14-15). In the 1v1 they are solid wall.

### 4.2 Fight floor (the courtyard)
- **28 x 17 m** at X 8-36, Y 2-19: raked sand over a dead-flat floor (the scenery rule: keep the fight area flat).
  Nothing stands on it. A flush stone path (X 21-23) runs from the gate to the hall steps; it is only a material
  change, 0 cm high.
- **Spawns:** P1 (14.5, 10.5) facing east, P2 (29.5, 10.5) facing west, 15 m apart. Both see the hall side-on and the
  compound is mirror-symmetric about X 22, so neither side has an advantage.
- **Why pale sand:** the players wear black at night; the floor is their backdrop (`STYLE_GUIDE.md` 2).

### 4.3 West and east yards (the bands round the floor)
- Gravel bands: 8 m wide on the west (X 0-8) and east (X 36-44), 2.5 m in front of the hall (Y 19-21.5), 2 m along
  the south wall.
- **Low cover and dressing only (rule R8):** weapon racks (2 m long, under 1.25 m), training posts (makiwara, 20 cm
  square), wooden training dummies, two stone lanterns in front of the hall (X 19 and 25), a well in the east yard
  (41, 22), crates at the shed and the pavilion (climb props, top +1.25).
- **Trees:** one each side at (3.5, 16) and (40.5, 16), canopy about 6.4 m across and starting above +4.0, so it
  never blocks a wall-top runner. Trunk collision only. More trees stand outside the walls as backdrop.

### 4.4 Dojo hall (north)
- **Hall body:** 18 x 10 m (X 13-31, Y 24-34), timber frame with plaster panels, floor **+0.5**, open truss interior
  to about +5.0.
- **Veranda (engawa):** 2 m wide on the front and both sides (X 11-33, Y 22-34), floor **+0.5**, reached everywhere
  by a continuous stone step band in front (Y 21.4-22.0): two 0.25 m risers, so you walk on without jumping.
- **Lower roof** (over the veranda, front and sides): 25 degrees, **eave +3.0** at the outer edge (front Y 21.5,
  sides X 10.5 / 33.5), rising to **+4.17 where it meets the hall wall** (2.5 m run). Headroom on the veranda: 2.5 m.
- **Upper roof** (hip-and-gable): 25 degrees, **eave +5.5**, overhanging the hall walls by 0.9 m (X 12.1-31.9, Y
  23.1-34.9), **ridge +8.3** along X at Y 29 (crest tiles to +8.7).
- **Doors:** three 2 m sliding-door bays on the front, one on each side, one at the back into the alley. **Closed in
  the 1v1** by default (see the open questions); open in the BR.

### 4.5 Outbuildings and corridors
| Building | Footprint (roof) | Heights | Role |
|---|---|---|---|
| Storehouse (NW) | X 0-7.6, Y 27.4-36; walls built into the perimeter wall | eave +3.25, ridge +5.25, ridge along X | Rooftop link from the west wall to the hall; BR loot |
| Residence / wash house (NE) | X 36.4-44, Y 27.4-36 | same | Mirror of the storehouse |
| Covered corridors | X 7.6-10.5 and 33.5-36.4, Y 29.5-32.5 | floor +0.5, roof +3.0 to +3.7; north side walled | Join outbuilding roofs to the hall's lower roof; open-sided at ground level |
| Training shed (SW) | X 0-6, Y 0-5, corrugated steel lean-to | +3.0 at the wall, +2.5 at the front edge | Modern touch; low roof reached from the wall or from crates |
| Drum pavilion (SE) | plinth X 39-43, Y 1-5 at +1.0; roof X 38.4-43.6, Y 0.4-5.6 | eave +3.25, pyramid apex +4.5 | The drum that can sound the round start; roof reached from the wall or crates |

### 4.6 Rear alley (closed in the 1v1)
The 2 m strip behind the hall (Y 34-36) and the two pockets behind the corridors are fenced off in the 1v1: from the
courtyard nobody could see a player there. In the BR the fences open and the rear wicket gate is the back way in.

## 5. Rooftop and wall-top play (optional high ground)

### 5.1 Routes up (numbers match the drawing)
| # | Route | Each climb |
|---|---|---|
| 1 | Courtyard to any wall top | 2.0 mantle |
| 2 | Wall top (+2.0) to storehouse or residence eave (+3.25) | 1.25 mantle |
| 3 | Outbuilding roof to corridor roof (+3.0) to the hall's lower roof side | walk (small step down) |
| 4 | Ground to cistern (+1.25, 1.2 x 1.2 m wooden tank at each front corner of the hall) to lower-roof eave (+3.0) | 1.25, then 1.75 mantle |
| 5 | Lower roof to AC unit top (+4.75) to upper-roof eave (+5.5) | about 1.5 (from the roof at +3.23), then 0.75 |
| 6 | South wall top to gatehouse eave (+3.25) | 1.25 mantle |
| 7 | Crates (+1.25) to shed front edge (+2.5) / pavilion eave (+3.25) | 1.25 / 2.0 mantle |
| 8 | Vending machine top (+1.75) to wall top (+2.0) | 1.75 mantle, 0.25 step |

- **The AC units** (1.2 x 2.0 m, two on the front lower roof at X 15-16.2 and 27.8-29) are the only way onto the
  upper roof without a jump. They stick 1.1 m out beyond the upper eave line, so there is room to stand on them
  (rule R3).
- **Why the cisterns and AC units:** from the veranda floor the lower eave is 2.5 m up, and from the lower roof the
  upper eave is about 2 m up at the nearest standing point (the eave overhang pushes the capsule out). Both are at
  or over rule R1, so each gets a step prop.
- **Shortcuts (jumps, never required):** lower roof to corridor roof corners, gatehouse roof to the wall, and a
  double jump from the lower roof straight to the upper eave. Confirm or drop them after the grey-box measures the
  GASP jump.

### 5.2 Walkable and blocking
| Walkable | Blocking or unwalkable |
|---|---|
| Courtyard, yards, veranda, step band | Hall walls, doors in the 1v1, shoji, lattice windows |
| Wall tops (flat 1.0 m strip) | Gable triangles, ridge-end ornaments, the drum and its stand |
| Hall lower roof (all three sides), upper roof front slope up to the ridge | Upper roof rear slope, outbuilding north slopes, corridor north slopes, north wall top (1v1 only) |
| Storehouse, residence, corridor, gatehouse, shed and pavilion front slopes | Anything steeper than 30 degrees (marked unwalkable per surface) |
| Tops of cisterns, crates, vending machine, AC units | Trees above the trunk, wires, lanterns' tops (too small to stand on) |

### 5.3 Collision rules
| Class | Players (Pawn) | Camera | Visibility (lock-on sight, hand and ground probes) | GASP traversal | Notes |
|---|---|---|---|---|---|
| Ground, floors, roofs, wall tops | block | block | block | block (ledges) | Roofs: one flat plane per slope; the tiles themselves have no collision |
| Walls and building bodies | block | block | block | block | Climbable edges must be set up the way GASP expects (below) |
| Eave overhangs beyond 1 m | block | ignore | block | block | Stops the camera snapping in when a player walks under an eave |
| Thin uprights (posts, lanterns, racks, dummies) | block | ignore | ignore | low items vault | Must not break lock-on or yank the camera |
| Climb props (cisterns, crates, vending machine, AC units) | block | ignore | block | block | Flat tops 1.0 m deep or more |
| Trees | trunk only | ignore | ignore | none | Canopies never collide |
| Grass, moss, gravel dressing | none | none | none | none | |
| 1v1 boundary and closed areas | block (invisible) | ignore | ignore | none | Pawn-only volumes |

**GASP traversal needs its own setup:** GASP climbs only over geometry built the way its traversal expects (its
`LevelBlock_Traversable` pattern and its Traversable collision channel). A plain wall mesh may simply block. The
grey-box tests this first; if it holds, every climbable kit edge (wall tops, eaves, prop tops) gets that setup.

### 5.4 Keeping players inside (1v1 only)
- **Outer ring:** an invisible Pawn-only wall on the outer edge of the wall top, from the wall top up to +20 m, all
  the way round. Players can run the wall top but cannot step off outside. The roadmap's "gentle push-back" can be a
  soft volume just inside it.
- **Ceiling:** an invisible Pawn-only plane at +20 m (the ridge is +8.7; a double jump from it cannot reach 20).
- **Hidden places:** Pawn-only blockers along the hall ridge (the rear slope), the outbuilding and corridor ridges,
  over the north wall top between the outbuildings, and fences at both ends of the rear alley.
- **Safety net:** a kill/reset volume 10 m below the courtyard.
- **All of these live in the duel level only**, never in the shared dojo building, so the BR copy has none of them.

## 6. Sight lines, camera and lock-on
| Check | From | To | Why |
|---|---|---|---|
| S1 | P1 spawn, eye height | P2 spawn | Clear (the floor is empty) |
| S2 | Either spawn | Both lower roofs, the upper front slope, every open wall top | A player on any legal high ground stays visible and lockable |
| S3 | Upper roof front slope | The whole fight floor | High ground sees everything, and everything sees it |
| S4 | Floor centre (22, 10.5) | Any legal surface | **The 1v1 rule:** a surface where a standing player's head cannot be seen from the floor centre and both spawns is out of bounds |

- High ground is a trade, not a win: getting to the upper roof costs about 5 s of climbing (the Great Fireball
  cooldown is 8 s), roofs have no cover, and a Great Fireball or thrown weapon reaches them.
- The 3.75 m camera boom: the yards give 2.5 m or more between the floor and any tall face, and posts and eaves
  ignore the camera, so the boom only shortens with your back to the hall or the storehouse.
- Corner to corner the compound is 57 m, past the 28 m lock break; the fight floor diagonal is 32.8 m. A player who
  runs to the far corner of the yard can drop the lock, as in any arena; the grey-box checks whether that needs a
  smaller compound (open question 7).

## 7. As a battle-royale location
- **Build the dojo once** as a Level Instance or Packed Level Actor (hall, outbuildings, walls, props). The duel
  level places it and adds its boundary volumes; the BR map places the same instance on a flat terrace, so both
  always match.
- **Setting:** on a terrace at the edge of a town, the main gate facing an approach road with street lamps and power
  lines. The outside ground stays within 0.5 m of the courtyard level along the walls, so the 2.0 m wall is
  climbable from outside too.
- **Ways in:** main gate (south), rear wicket (north), two side wickets (west and east), and over the wall anywhere.
- **Loot:** hall interior (weapon racks, the raised honour platform), storehouse (shelves and chests), residence
  (rooms), yard weapon racks. The high ground (hall ridge +8.3) overlooks the approach roads; trees outside the walls
  break the longest lines.
- **What changes from the 1v1:** doors open, fences and blockers gone, rear slopes and the alley playable.

## 8. Grey-box plan (in Unreal, before any art)
**Phase 0, measure GASP (half a day).** In a test map, a traversal strip: blocks at 0.40, 0.50, 0.75, 1.00, 1.25,
1.50, 1.75, 2.00, 2.25, 2.50, 2.75 and 3.00 m tall; top depths 0.3, 0.6 and 1.0 m; ramps from 15 to 45 degrees in 5
degree steps; one set of blocks as plain static meshes and one built the GASP traversable way. Record: which heights
vault, hurdle and mantle; walkable slope; capsule size; single and double jump height and distance at run speed;
whether plain meshes can be mantled. **If the mantle ceiling is lower than about 2.4 m, lower every height in this
file so rule R1 still holds; if higher, keep the heights (the margin is intentional).**

**Phase 1, block out (1 day).** Grey blocks on the 25 cm grid, from the coordinates in section 4, in a duel test
level (roadmap's `L_DuelArena`): walls, gatehouse, hall body, veranda and step band, both roof tiers as 25 degree
planes, outbuildings, corridors, cisterns, AC units, crates, vending-machine box, tree trunk cylinders, spawns, the
section 5.4 volumes. Use GASP-traversable blocks for every climbable edge. If GASP's level blocks were not among the
assets copied into DemoGame_1, copy them from the GameAnimationSample project the same way.

**Phase 2, play it (1 day), with the dummy and a second player.**

| Gate | Pass |
|---|---|
| G1 Routes | All 8 routes work with plain Space presses, 5 of 5 tries each |
| G2 Time to the top | Ground to the upper roof in 4-7 s; wall top in about 1.5 s |
| G3 Hiding | From the floor centre and both spawns, a standing player is visible on every legal surface (screenshot sweep) |
| G4 Lock-on | Tab acquires from spawn; the lock holds between floor and every roof |
| G5 Camera | No boom pop more than once per 360 degree turn on the floor, the veranda and each roof |
| G6 Boundary | Nobody leaves: wall-top run, double jump off every roof edge, knockback into the wall |
| G7 Fairness | P1 and P2 routes mirror; same times |
| G8 Frame time | 60 fps at 1080p with two players and effects (roadmap M4) |

**User gate:** the user walks it and says go before any art.

## 9. Provisional kit (short; the real list comes from the reference image)
Perimeter wall runs, corners and ends, tiled wall cap; gatehouse and gate leaves; hall frame (posts, wall bays with
plaster, lattice windows, sliding doors, shoji), veranda boards and edge beams, stone step band; lower and upper roof
tile fields, eaves, ridges, hips, gable panels, ridge-end ornaments; covered corridor; storehouse and residence (same
kit, plus a steel door); steel lean-to shed; drum pavilion and drum; stone lanterns; training posts, dummies, weapon
racks; cisterns, crates, vending machine, AC units, gutters and downpipes, electric lamps, power pole and wires; well;
gravel, sand and stone paving materials. Trees and grass are bought (`STYLE_GUIDE.md` 9).

## 10. Files
- `DOJO_ARENA_TOPDOWN.svg`: drawn by `py WorkFiles/world/make_topdown.py` (all numbers are in that script).
- `DOJO_ARENA_TOPDOWN.png`: 2000 x 1330, rasterized from the SVG with the installed Edge:
  `msedge --headless=new --disable-gpu --hide-scrollbars --window-size=2000,1330 --screenshot=<png> file:///<svg>`.
- `DOJO_ARENA_IMAGE_PROMPT.md`: prompts for the reference image.

## 11. Open questions for the user
1. **Time of day and season** for the duel: night like the test level, dusk, or day? Which season?
2. **Hall interior in the 1v1:** closed (default, no hiding and no camera trouble inside) or open to fight through?
3. **How modern:** 1970s-style infrastructure (poles, bulbs, vending machines), or today's (LED signs, screens,
   cars)?
4. **Rear roof slopes and the alley** in the 1v1: keep them closed (default), or allow them and accept hiding?
5. **Drum or bell** as the centrepiece, and should it sound the round start?
6. **Name and emblem** of the location for the BR map (the armory's planned original emblem could be reused)?
7. **Compound size:** 44 x 36 m inside, or try smaller in the grey-box if the lock drops too often?
8. **Trees:** OK to turn on the Experimental Megaplants setup for two hero trees (hinoki or ginkgo), or use lighter
   trees?

## 12. Roadmap lines now out of date (not edited)
`Docs/MVP_Roadmap.md` still describes the arena as the cleared field. These lines no longer match the dojo choice:
- **Line 42** (section 1, "What done means"): "the L_NinjaTest night courtyard with boundary walls added ... the arena
  will be an open grassland with a mountain backdrop; the boundary still has to be decided".
- **Line 304** (3.2, Maps): "`L_DuelArena` = a duplicate of `L_NinjaTest` plus bounds ... No new art pass".
- **Line 402** (4.4, World): "`L_DuelArena`: a duplicate of `L_NinjaTest` with boundary walls".
- **Line 483** (4.6, Arena): "Boundary about 50 m across in `L_NinjaTest` (now a flat field ...; walls or another
  boundary to fit the grassland)". The 50 m and 15 m spawn numbers still hold.
- **Line 611** (section 6, Content): "Map: `/Game/Maps/L_DuelArena`, duplicated from `L_NinjaTest`".
- **Lines 664-668** (M0a, `L_DuelArena`): "Duplicate `L_NinjaTest` / Add boundary walls / ... / No new art".
- **Lines 948-951** (M4, "Arena check (no art pass)"): the checks (push-back, low occluders, no hiding spots, 60 fps)
  still apply, but "no art pass" does not, and the dojo's buildings are tall occluders by design (handled by rule
  S4 and the 1v1 blockers).
- **Line 1094** (section 8): Ultra Dynamic Sky and Megaplants are kept out of the package "unless `L_DuelArena`
  references them"; a dojo with Megaplant trees and UDS will reference them, so their licence check becomes
  required.
- **Line 1099** (section 8, Arena): "Reuses `L_NinjaTest` and LevelPrototyping; CC0 textures only if anything new is
  needed". The dojo is a new kit.
- **Line 1221** (risk R5): mitigation "low-occluder arena"; the dojo needs the camera and sight-line rules in section 6
  instead.
- **Lines 1283-1286** (next sessions, "Arena"): "Create `L_DuelArena` by duplicating `L_NinjaTest` ... Add boundary
  walls".
- Related, in `CLAUDE.md` line 9: "Look: grounded / realistic, night feudal Japan" does not yet mention the modern
  mix.
