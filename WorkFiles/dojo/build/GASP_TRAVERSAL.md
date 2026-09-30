# GASP traversal: what it climbs, how geometry must be marked, measured ranges

**Date:** 2026-09-27. **Source:** the Game Animation Sample assets as copied into `Documents/Unreal Projects/DojoLab`
(UE 5.8, the sample itself was never opened). Every number below was read headless by
`Scripts/dojo/unreal/dj_gasp_inspect.py` (commandlet, read-only) into `WorkFiles/dojo/build/unreal/gasp_inspect.json`
plus T3D text exports in `WorkFiles/dojo/build/unreal/gasp_t3d/`. Blueprint graphs were read with
`Scripts/dojo/unreal/gasp_graph_dump.py` (pin defaults and links). Nothing here is from memory or Epic's docs.

## 1. How geometry must be marked

| Rule | Value | Where it comes from |
|---|---|---|
| The forward trace only sees the **Traversable** trace channel | `CapsuleTraceSingle(TraceChannel = TraceTypeQuery3)`; TraceTypeQuery3 = `ECC_GameTraceChannel1` "Traversable", default response **Ignore** | `AC_TraversalLogic.TryTraversalAction` step 2.1; `Config/DefaultEngine.ini` `+DefaultChannelResponses=(Channel=ECC_GameTraceChannel1, DefaultResponse=ECR_Ignore, bTraceType=True, Name="Traversable")` |
| The hit actor must **be a `LevelBlock_Traversable`** | `K2Node_DynamicCast AsLevelBlockTraversable`; a plain static mesh is never traversed, whatever its channel | `AC_TraversalLogic` step 2.2 |
| Ledges are the block's **four spline components** | `Ledge_1..4` on the top edges of the 100 cm cube (`SM_Cube`, pivot at a corner): Ledge_1 on local y 0 (normal -Y), Ledge_2 y 100 (+Y), Ledge_3 x 0 (-X), Ledge_4 x 100 (+X), all at z 100; the ledge normal is the spline's **up vector**, pointing outward. They scale with the actor | Blueprint SCS, spawn tests at scales (1,1,1), (2,1,1), (1,3,1), (1,1,2), (4,1,2.5) in `gasp_inspect.json` |
| Opposite ledges | 1 <-> 2, 3 <-> 4 (set in its construction script) | `LevelBlock_Traversable.UserConstructionScript` |
| Front ledge | the ledge closest to the actor; valid only if **>= MinLedgeWidth 60 cm** long; the contact point is the point closest to the trace hit, **clamped 30 cm** from the ledge ends | `GetLedgeTransforms`, `FindLedgeClosestToActor`, CDO `MinLedgeWidth = 60` |
| Block collision in GASP's own level | profile `TraversalObjectPreset` (WorldDynamic, blocks everything incl. Traversable) | spawn test responses |
| Room checks use the **Visibility** channel | `TraceTypeQuery1` | `TryTraversalAction` steps 3.2, 3.4, 3.6 |

**How the dojo marks it:** one `LevelBlock_Traversable` (GASP's Blueprint, unedited) per climbable volume, scaled so its cube
fills the volume (its ledges then sit on the volume's top edges), hidden in game, collision set to **Traversable only,
query only** (Pawn / Camera / Visibility ignore), so the grey-box meshes alone decide blocking, sight and the room checks.
28 markers, Outliner folder `Dojo/Traversal`, labels `TRV_*`, tags `DJ_Traversal` + `route_<n>`
(`Scripts/dojo/unreal/dj_level.py`; `dj_verify.py` re-reads the saved ledges, normals and responses in a fresh process).

## 2. The check GASP runs (AC_TraversalLogic.TryTraversalAction)

| Step | What | Numbers |
|---|---|---|
| Inputs (on the ground) | capsule trace from the capsule centre along the actor's forward vector | distance = MapRangeClamped(forward speed, 0..500 -> **75..350 cm**), radius **30**, half height **60** (`SandboxCharacter_CMC.GetTraversalCheckInputs`) |
| Inputs (in the air, falling / flying) | same | distance **75**, radius 30, half height **86**, end offset **+50 cm z** |
| Band the ground trace sees | capsule centre (+86 above the feet) +- 60 | a block is found if it reaches above **feet + 26 cm** (and starts below feet + 146 cm) |
| 3.2 room to reach the ledge | capsule sweep (Visibility) actor -> front ledge + normal x (radius + 2) + (0, 0, half height + 2) | must be clear |
| 3.3 obstacle height | front ledge z - (actor z - half height) | = ledge height above the feet |
| 3.4 top sweep | capsule 2 cm above the ledge, front room point -> back room point (Visibility) | a hit **invalidates the back ledge** and depth = XY distance front ledge -> impact |
| 3.5 depth | otherwise XY distance front -> back ledge | |
| 3.6 back floor | sweep down from the back room point to back ledge + normal x 32 - (0, 0, 50) | reaches about **136 cm** below the back ledge; hit = back floor, back ledge height = back ledge z - floor z |
| 4.2 choose | `CHT_TraversalMontages_CMC` (below) | no matching row = no traversal |

## 3. The ranges (CHT_TraversalMontages_CMC, CMC character)

**Root table (row order):**

| Row | Needs | Action |
|---|---|---|
| 0 | front + back ledge, back floor, depth <= 59 cm, back ledge height >= 50 cm | **Hurdle** |
| 1 | front + back ledge, back floor, depth <= 59 cm, back ledge height <= 10 cm | **Mantle** |
| 2 | front + back ledge, **no** back floor (drop > ~1.36 m behind), depth <= 59 cm | **Vault** |
| 3 | front ledge, depth >= 59 cm | **Mantle** |

**Nested tables (obstacle height = ledge above the feet):**

| Action | On the ground (MovementMode OnGround) | In the air (InAir / Traversing "catch" rows) |
|---|---|---|
| Hurdle | height **0-125 cm**, depth **<= 25** (V1 clips) or **25-60** (V2 clips); stand <= 100, walk 100-250, run >= 250 cm/s | height <= 50 / 50-100 / 100-200, depth <= 60 |
| Vault | height **0-125 cm**, depth **<= 60**; stand / walk / run rows | height <= 50 / 50-80 / 80-200, depth <= 60 |
| Mantle | height **0-150 cm** (1 m clips), **150-275 cm** (2.5 m climb clips); stand / walk / run rows | height <= 50 / 50-100 / 100-200 |

So, measured: **mantle ceiling 275 cm** above the feet (the spec's "about 2.75 m" holds), **hurdle and vault ceiling
125 cm** over a thin (<= 59-60 cm) obstacle. A thin obstacle becomes a hurdle only with **>= 50 cm** between its top and
the floor behind it, a vault only when the far side drops away (no floor within ~1.36 m), a mantle when its top is
level with the floor behind (<= 10 cm) or it is >= 59 cm deep. **A thin obstacle whose top is 10-50 cm above the floor
behind matches no row** (nothing happens). There is no minimum height in the tables; the forward trace finds anything
reaching above feet + 26 cm.

**The character (SandboxCharacter_CMC CDO):** capsule radius **30 cm**, half height **86 cm** (1.72 m); MaxStepHeight **45 cm**;
walkable floor **44.77 deg**; JumpZVelocity **500 cm/s**, GravityScale **1.0** (apex 500^2 / (2 x 980) = **127.6 cm**);
JumpMaxCount **1** (the game adds its double jump on top); MaxWalkSpeed 500 (GASP rewrites speeds per gait at run time).
Components include `AC_TraversalLogic`, `MotionWarping`, `AC_PreCMCTick`.
**GASP's own test level** (`/Game/Levels/DefaultLevel`) has 28 `LevelBlock_Traversable`: ground blocks 100 to 250 cm tall,
20-50 cm thin walls and floating 20 cm ledges (air catches). Game mode: `GM_Sandbox`, whose own DefaultPawnClass is
**SandboxCharacter_Mover** (not CMC); it picks `PawnClasses[DDCvar.PawnClass]` when the cvar is set (default -1 = the
DefaultPawnClass). DojoLab therefore uses `GM_Dojo`, a child of GM_Sandbox with DefaultPawnClass SandboxCharacter_CMC.

## 4. Consequences for the dojo (the numbers that change, flagged)

| Spec item | Spec | Measured | Change |
|---|---|---|---|
| Capsule | r 35 cm, 1.86 m | r **30**, **1.72 m** | walk check uses 0.30 (0.35 kept as a margin run) |
| Mantle ceiling (R1) | ~2.75 m, unmeasured | **2.75 m** | keep every height (spec section 8 rule: above 2.4 m, keep) |
| Vault / hurdle band (R8) | 0.5-1.25 m | hurdle 0.5-1.25 m over <= 0.6 m thick cover with floor behind; 0.10-0.50 m cover is **not traversable** | low cover should be >= 0.5 m (or <= 0.45 to be stepped) |
| Jump | ~1.7 m apex, unmeasured | **1.28 m** single jump | no route relies on a jump (unchanged R6) |
| **Mantle onto a sloped roof edge** | assumed to work | **fails for any slope over ~2 deg**: the top sweep (capsule 2 cm above the ledge) hits a 25 deg roof about **10.6 cm** in (5.7 deg lean-to: about 22 cm), depth < 59 cm, back ledge invalidated, no row matches | every eave a route arrives at needs a **flat landing >= 0.49 m deep** (0.75 m used): wall piers +3.25 (routes 2, 6), eave pads (routes 4, 7), a flat front band on the shed (route 7) |
| Route 5 AC unit | top +4.75, 0.75 to the upper eave | a 0.75 m rise can be neither walked (step 0.45) nor mantled (slope) | AC top **+5.10**, the last rise is a 0.40 m walk-up step |
| Route 6 gatehouse | eave reachable from the wall top | the sheet's gable puts the verge 2.2-2.4 m above the wall top | grey-box gatehouse roof **hipped** (eaves all round at +3.25) |

Verified on the grey-box by `Scripts/dojo/climb_check.py` (GASP's steps 1-6 and the chooser replayed against the UCX hulls):
see `WorkFiles/dojo/build/climb_check.json` and `BUILD_NOTES.md`.
