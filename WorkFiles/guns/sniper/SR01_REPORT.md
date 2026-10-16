# Sniper Rifle SR-01: final report (W0-W6)

**Date:** 2026-10-14
**Branch:** `claude/sniper-sr01` (worktree); not merged, nothing pushed. W6 is uncommitted: the user reviews and
commits.
**Lock:** `SR01` is held by `claude` and kept, as instructed.

**What shipped.** `Exports/Guns/SR01/` holds:
- the rigged rifle `SK_SR01` (13 bones + root, LOD0-3, 8 clips, physics proxy);
- the static twin `SM_SR01` (bipod folded, magazine merged);
- the magazine `SM_SR01_Mag`;
- the long-range scope `SM_Att_Scope_LongRange`;
- 21 maps, the sidecars, `README.md` and `MATERIALS_README.md`.

The FBX, sidecar and texture bytes are the W5-verified ones (Unreal 5.8.3, 37 of 37). The showcase is in
`showcase/SniperRifle_SR01/` (15 images).

**What did not happen in W6, by instruction:**
- the shared pack-materials build (no `run_build.sh`, no `np_lock.py claim`, no edit under
  `Scripts/unreal/materials/`, no Unreal);
- an edit to `showcase/ASSET_LIST.md`.

The pack additions are written up as an unbuilt proposal (section 6). The row text for the asset list is in section 9.

## 1. The study in short (W0)

- **Source:** the user's AI design sheet (GR / GL / TOP / 3/4 panels), measured and traced (`SR01_STUDY.md`,
  `MEASUREMENT_NOTES.md`, `trace/`).
- **Rulings:** real-pattern rulings for every small part (`CRAFT_STUDY.md` RP1-RP15) and the plan
  (`SR01_BUILD_PLAN.md`).
- **Real scale:** 1,100 mm long with a 559 mm barrel, 5.9 kg without scope and magazine.
- **Spec:** S0 passed with 0 missing values and 0 of 33 checks failed.
- **Bipod (user requirement):** independent legs on 12-degree-splayed pins, 0..76 mm extension in 19 mm detents and
  +-15 degrees of cant, with deploy and stow clips.
- **Scope:** a separate attachment on the rail.

## 2. Build (W1-W3) and gates

| Stage | Gate file | Status |
|---|---|---|
| W1 blockout | `gates/blockout.json` | fail, not decisive: GR / GL pass, TOP under 0.95 raw and 0.90 or more with the declared conventions |
| W1 form | `gates/form.json` | **partial**. G5, B3, F1-F9 (bipod, bolt, release, riser, trigger), UD1 / UD2 and H1 early pass. **L2** fails: GR 0.9602 passes, but GL is 0.9426 raw / 0.9505 declared (bar 0.958), TOP 0.8375 / 0.9020 (bar 0.93) and per part 2 / 19 (bar 0.95 each). **L3** GR contour P95 3.0 px (bar 2). **L4** 13 / 14 (the grip bottom is 0.21 mm high, declared) |
| W1 magfit | `gates/form_magfit.json` | pass |
| W1b scope form | `gates/scope_form.json` | pass (A1-A4: Mount on a slot, lugs 0.1-0.4, 2 mm or more clear, Sight 57.6 mm and parallel) |
| W2 surface | `gates/uv_bake_paint.json` | **partial**. L5 12 / 12, UD4 pass. **B9** misses by a hair twice: Metal class C P5 31.3 vs 31.5, scope class C P5 40.9 vs 41.1 |
| W3 game / LODs | `gates/game.json`, `game_lod_sizes.json` | pass. LOD0 41,396 (twin), LOD-pop sizes on both bipod poses |
| W3 rig + export | `gates/rig_export.json` | pass (13 bones, 8 clips, B11 bounds over every clip frame and extreme pose, fresh-process verify) |
| W3 magazine | `gates/mag.json` | pass (M1-M10, straight path 67.8 mm) |
| W3 scope export | `gates/scope_export.json` | pass (A1-A5, Mount = Rail_Top + 20.02 mm) |

qa_check ran before every export. The meshes were re-exported last in W5 (half-texel UV1 fix), through
`Scripts/pipeline/`.

## 3. Review and close-up realism (W4, W4b)

- **W4** (`gates/review_fixes.json`):
  - W3 leftovers fixed; one review and one fix round; the chain rebuilt from nothing.
  - Blind test (reported, not blocking): the copy was picked in **14 / 14 pairs on design**. The tells were stock
    hardware, the open guard, the glossy scope, the flutes and the grip.
  - Realism judges: fake 5 / 5 and 5 / 5.
- **W4b** (`gates/closeup_r1.json`, **status fail**, 5 of 11):
  - Failed: K1 hard creases (15.9 m -> 14.9 m, target 0.5x), K2 bolt roughness P5, K3 OD peel tilt, K4 bare metal on
    small parts, K8 sparkle (6 hot pixels vs 5).
  - K2 / K4 / K5 here were measured with the bake ids and the ORM rows mirrored (fixed 2026-10-16, see `K4_NOTE.md`);
    round 1's bake ids are gone, so these round-1 values cannot be re-measured. On the shipped round-2 maps, K2 and K4
    pass (`REALISM_R2_REPORT.md` → "K-gate measurement fix").
  - Judges: **fake 8 / 8 (A) and fake 8 / 8 (B)**, mean confidence 88 / 89.
  - The round failed decisively and stopped there.
- **The judges' geometry list (still open):**
  - Judge A: torn slivers on the grip and grip base, jagged riser and pad edges, stepped stock seams, a wavy chassis
    underside, a crude trigger.
  - Judge B: a zig-zag at the forend nose, sawtooth or stepped forend edges, a wavy chassis edge near the well, a thin
    magazine release.
  - Both also asked for more wear and variation (fingerprints, dust, tone, a less clean bolt), real optics and a real
    backdrop.
  - W4b's note stands: the unclamped weighted round with exclusion boxes is a patchwork. The next round should change
    method (a per-vertex clamped bevel or authored round profiles) rather than add boxes.

## 4. Unreal (W5, UE 5.8.3, `UnrealCheck/verification_summary.json`)

**37 of 37 pass** on the re-exported bytes in fresh processes. The run folder was `/Game/GunCheck/SR01_1014b`.
Every Unreal process went through `sr_guard.ps1`.
- **Bytes:** identical before and after every pass (43 files).
- **Skeleton and clips:** U1 skeleton 14 bones; U2 bolt -8.8 cm and -60 degrees; U2b one ABP on the AR-01 skeleton
  drives both rifles.
- **Sockets (U3):** 20 / 20 / 5 / 5, worst 0.0 cm.
- **First person (U4):** FP / VSM and the scope pair (Mount + 20.02 mm, Sight 57.6 mm, parallel).
- **LODs and bounds (U5):** 4 / 4 / 4 / 3 LODs, triangles equal in Blender, the FBX and Unreal; bounds hold every
  vertex at every clip frame.
- **Magazine (U6):** SnapToTarget exact; only the catch nose touches on reload, 0.088 mm.
- **Physics (U7):** PHYS_SR01, 5.9 kg; drops rest without tunnelling.
- **Lightmap UVs (U8):** 0 px overlap at 64 / 128.
- **Clips at runtime (U9):** 0.0 mm against the raw clips.
- **Warnings (U10):** 0 asset warnings.
- **Texture streaming (U12):** top mip at the hip and at ADS.
- **Collision (C2):** 0 samples outside the hulls.
- Two W5 failures, U6 and C2, were measurement errors and were fixed in the analysis, not the asset (`W5_REPORT.md`).
- **Not covered:** U11 hand fit (no player MetaHuman in the project; the summary's `null` means not run), and the
  owner-only TP hiding (game side).

## 5. W6 docs and showcase (`gates/docs_showcase.json`, status pass)

- **`README.md`**, rewritten. Its "Measured in Unreal 5.8.3" section is kept word for word. It covers:
  - files, frames and units, import steps, the bounds extension, the notifies table;
  - bones and the angle table, and the AR-01-compatible ABP;
  - **bipod use:** deploy / stow clips, independent legs, the 12-degree splay, ground heights 266.7 / 285.3 / 303.9 /
    322.5 / 341.1 mm by extension detent, prone placement, cant, bounds, folding before physics;
  - **scope attachment:** Mount on Rail_Top + 2 slots, Sight / EyePoint, no built-in zero, 29.9 mm knob clearance;
  - the FP / TP pattern with the scope pair, the socket table, the straight reload path;
  - collision, CoM and masses, physics and the rebuild;
  - the materials table with the instances marked not built;
  - triangle counts and texture sizes;
  - the open items.
- **`MATERIALS_README.md`**, new: texture sets and slots, UV tiles, map settings (BC sRGB, ORM / Masks linear, N
  DirectX, Detail16 G16), the Masks channels (A = 1 only on the OD), the recolour plan, a clear "not built yet",
  and the D1 caution: do not switch off the baked colours on the Chassis.
- **Deny list:** gunlib's `qa_gun.deny_hits` (48 terms) plus a maker-word net found **0 hits** over 3,828 text lines
  and 145 names: every shipped text file, every file name, and every object, mesh, material, bone, socket and action
  name in every shipped FBX (`tools/w6_deny_scan.py`, `scratch/w6/deny_scan.json`).
- **Showcase** `showcase/SniperRifle_SR01/`, 15 images rendered headless from the shipped FBX and maps:
  - the studio views hero, front, side, back, top and hero_dark;
  - magazine hero / front / side;
  - **BipodDeployed** hero / front (SK_SR01 at the last frame of `A_SR01_BipodDeploy`, armature applied: legs at
    90 degrees, 12-degree splay, 38 mm extension, standing on its feet; the lowest point is 303.9 mm below the bore,
    equal to the sidecar's ext-38 ground height);
  - **Scoped** hero / front (scope Mount on Rail_Top + 20.02 mm);
  - **Scope** hero / front.

  How they were made:
  - Studio: `Scripts/showcase/studio.py` copied read-only from `claude/cardshop-build-integration-5227b4` to
    `scratch/w6/studio.py` (not added to `Scripts/showcase/`).
  - The composite scenes come from `tools/w6_showcase_prep.py`. The first prep run lost the scope when the FBX root
    empties were deleted; the parent transform is now kept and the composites were re-rendered.
  - I looked at every image. The framing is the studio's standard and consistent with the SMG's set; no reframing was
    needed.
  - Logs are in `showcase_logs/` (6 studio JSONs + the prep JSON / log).
  - No Unreal pack frame was made, because the pack is not built (the SMG had one).

## 6. Pack colours: proposal only (`pack_materials_proposal.md` + `.json`), **not built**

- **Spec additions.** 4 items (`SR01`, `SR01_Static`, `SR01_Mag`, `Att_Scope_LongRange`) and 10 instances
  (`MI_SR01_Metal`, `MI_Att_Scope_LongRange_Body` / `_Lens` on `M_Steel_Master`; `MI_SR01_Chassis`, `MI_SR01_Mag` on
  `M_Fabric_Master` with Metal From ORM ON; each with `_Base`). Also build-map entries, `changes_v11_sr01` and recolour
  group SR01.
  - Field shapes are copied from the SMG01 entries and there are no name clashes.
  - Slot names and order were read from the shipped FBX.
- **Recolour constants.** `materials/derive_constants_sr01_draft.py` is the proposed
  `maps/derive_constants_sr01.py` (the SMG's with group SR01 and one part).
  `materials/sr01_recolour_pack_draft.py` writes the pack-schema maps into `materials/draft_out/` and pre-checks them
  read-only through the pack's own `derive_constants.fabric_part`:
  - fabric_part gates, black floor, knee and the 13-colour stress all **pass**;
  - the default recolour path vs the BC on the OD: p50 0 / p99 1 / **p99.9 4 levels** (P1 bar 2), so the shipped
    Chassis instance keeps Use Original Baked Colours ON.
- **Findings for the builder:**
  1. **The magazine has no OD paint** (Masks A = 0 everywhere; 87 % phosphate, 13 % polymer). Recolour group SR01 has
     one member (Chassis), not the plan's grouping with the magazine.
  2. **D1: `M_Fabric_Master` has no mask input.** 28.4 % of the Chassis set's painted texels are anodize, polymer and
     rubber (painter counts: OD 8,165,957 of 11,406,727). A buyer recolour would tint the grip, butt pad and bipod.
     Options:
     - D1-a: ship baked-only first;
     - D1-b: add an additive, default-off "Masks A" switch on the master, under the lock.
     Moving parts to another slot would re-export the verified meshes, so it is not an option.
  3. **The shipped `Recolour/recolour_maps.json` is the W2 stub, not the pack schema.** The build writes the
     pack-schema map and the Detail16 (textures only, meshes untouched).
- **Gates the build must pass:** P1 (default capture = BC, 2 levels or less; BC7 fallback), P2, P3a (P3b reported),
  P4 (2 % or less), additions-only, every other entry unchanged, `run_build.sh` clean / build / verify, lit frames.

## 7. Shipped bytes (sha256)

`gates/shipped_sha256_w6.json` has all 44 files in full. Compared with W5's `UnrealCheck/SHA256_at_end.json`:
- **42 of 43 are identical**: every FBX, sidecar and map.
- `README.md` was rewritten in W6, and `MATERIALS_README.md` is new.

| File | sha256 (first 16) |
|---|---|
| `SK_SR01.fbx` | `1a007bb0dc1b0650` |
| `SK_SR01_LOD1.fbx` / `_LOD2` / `_LOD3` | `27c1241586c7ee18` / `047a0c6f00f381cd` / `79259dfb9f5bd078` |
| `SK_SR01.skeletal.json` | `26c75f451d2961a4` |
| `SM_SR01.fbx` / `.sockets.json` | `c4a407d90d919d20` / `aa48fb12ef07167f` |
| `SM_SR01_Mag.fbx` / `.sockets.json` | `9eb77b05f3b6d7b8` / `632775b0137f57bb` |
| `SM_Att_Scope_LongRange.fbx` / `.sockets.json` | `845e32da91765b70` / `6687c5ac318b5273` |
| `Physics/SK_SR01_PhysicsProxy.fbx` | `9bec832e39f4b806` |
| `A_SR01_Fire` / `BoltCycle` / `Reload` / `ReloadEmpty` | `c8821645c8fc39e2` / `055e95c43b626b17` / `77a9d2e04306f15f` / `73c8b7ce266fd9a2` |
| `A_SR01_Selector` / `BipodDeploy` / `BipodStow` / `CheekRiser` | `8d363d32c08f51ea` / `a598feb648b62d0d` / `d3080e33fdcd3763` / `7296aa8e78797927` |

## 8. What is left (honest)

1. **Close-up realism is not passed.** The judges called it fake 8 / 8 twice at W4b and listed the geometry problems
   in section 3. The next round needs a method change for edges (clamped per-vertex bevel or authored round
   profiles), not more exclusion boxes. The game views are the intended use until then.
2. **Form L2 / L3 / L4 are open:**
   - L2: GL 0.9426 / 0.9505 vs 0.958, TOP 0.8375 / 0.9020 vs 0.93, per part 2 / 19 (the per-part method is suspect);
   - L3: P95 3.0 vs 2 px;
   - L4: 13 / 14.

   The TOP conventions need the user's call.
3. **B9 near-misses:** Metal class C P5 31.3 vs 31.5, scope class C P5 40.9 vs 41.1. These are declared and not
   decisive.
4. **U11 hand fit was not run** (no player MetaHuman in the verification project). `Grip`, `SupportHand` and
   `SupportHandBipod` are provisional. H1 passed in Blender.
5. **Pack materials are unbuilt**, by instruction. Apply `pack_materials_proposal.*` after the merge, under
   `PackMaterials`, and decide D1 first.
6. **The blind test is reported, not blocking:** 14 / 14 picked on design at W4.
7. **Release the `SR01` lock** when the user is done with the item. It is held, as instructed.

## 9. `showcase/ASSET_LIST.md` row (for the main chat to add; not edited here)

```
| [SniperRifle_SR01](SniperRifle_SR01/) | Sniper Rifle SR-01: a bolt-action precision rifle in an olive-drab painted chassis with an adjustable cheek riser, a folding, extending and canting bipod (legs splayed 12 degrees), a detachable 10-round box magazine and a separate long-range scope (generic, no markings), matched to the user's design sheet; rigged skeletal mesh (bolt that turns and slides, trigger, safety, release, magazine, cheek riser, bipod legs and extensions) with 8 weapon clips incl. bipod deploy / stow, a static twin, the separate magazine and the scope attachment. | Built; Unreal 5.8 verified (37/37, no import gate open; hand fit not run); pack colours proposed, not built (branch not merged); close-up realism not yet passed by the judges | 4 | `Exports/Guns/SR01/`; `Assets/Guns/SR01.blend`, `Assets/Guns/Att_Scope_LongRange.blend` | 15 |
```

If the row is added, the totals line at the top of `ASSET_LIST.md` goes up by 1 asset, 4 meshes and 15 images.

## 10. API cost per stage (`C:/Users/Cody/api-projects/runs.log`)

| Stage | Logged run | Cost |
|---|---|---|
| W0 study, trace, plan, spec | 2026-10-12 21:15 | $10.37 |
| W1 form + scope form | 2026-10-13 08:18 | $29.18 |
| W1 follow-ups + W2 surface | 2026-10-13 11:27 | $24.54 |
| W3 rig, clips, bipod, LODs, twin, mag, scope | 2026-10-13 13:19 | $23.10 |
| W4 review + fix | 2026-10-13 15:59 | $24.53 |
| W4b close-up realism | 2026-10-13 21:01 | $16.74 |
| W5 first run (interrupted about 00:40 when the session restarted; WIP checkpoint 55100d54) | **not in the log: no cost was recorded for it** | unknown |
| W5 resume | 2026-10-14 11:47 | $4.09 |
| W6 finish (this run, cap $12) | 2026-10-14 12:35 | about $5 at the time of writing (the runner logs the final figure) |
| **Total logged, W0-W5** | | **$132.55**, plus W6 and the unlogged first W5 run |

The plan's estimate for W1-W6 was $145-245.
