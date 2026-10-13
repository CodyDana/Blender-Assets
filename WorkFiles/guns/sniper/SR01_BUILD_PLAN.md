# Sniper Rifle SR-01 (SR01): game and tech build plan

**Date:** 2026-10-12 (W0). **Role:** game and tech plan. Nothing was built, and neither Blender nor Unreal was run.
Lock `SR01` is held (agent `claude`). The machine-readable twin of this plan is `sr01_interface.json`.
**`sr01_spec.json` wins** over every number here (written by `tools/make_spec.py`, S0 PASS).

**Scope.** The sixth gun of the line (queue item 6). One build ships four assets:
- `SK_SR01`: the rigged rifle without the scope (+ `_LOD1..3`, `SK_SR01_Skeleton`, `PHYS_SR01`, 7 clips + 1 optional);
- `SM_SR01`: the static twin (bipod folded as drawn, riser at the sheet pose, magazine merged; no scope);
- `SM_SR01_Mag`: the 10-round box;
- `SM_Att_Scope_LongRange`: the scope with its rings, a static attachment on `Rail_Top` (study row 8: attachment no. 1
  of the kit).

**Reference:** `References/Guns/Sniper/sniper_sheetA.webp`. The labels are swapped (the panel labelled LEFT is the
gun's right). There is no ruler. The bipod is folded in every view, the 3/4 included. `References/AWP.webp` is never
a look source.

---

## 0. The plan on one screen

| Item | `SK_SR01` / `SM_SR01` | `SM_SR01_Mag` | `SM_Att_Scope_LongRange` |
|---|---|---|---|
| Real scale | **1100 mm**, barrel **559 (22 in)**, **5.9 kg** without scope and mag (bipod incl.), ready 7.5 kg | empty 0.20 kg, 10 x 25.4 g | 1.15 kg with rings, 419 long |
| Triangles LOD0 / 1 / 2 / 3 | **35-45k (ceiling 50k, scope excluded)** / ~45 % / ~15 % / 2-3k | 2-3k (5k) | 6-10k (12k), 3 LODs |
| Slots | 2: `M_SR01_Metal` (`M_Steel_Master`), `M_SR01_Chassis` (`M_Fabric_Master`, Metal From ORM on; OD paint is the user colour; rubber/polymer/anodized at Masks A 0) | `M_SR01_Mag` (Fabric + MFO) | `M_Att_Scope_Body` (Steel), `M_Att_Scope_Lens` (opaque glossy) |
| Twin UV tiles | Metal 0, Chassis 1, merged mag -1 (the qa_check 3-tile limit) | 0 | 0, 1 |
| Held draw calls | gun 2 x 2 + mag 2 x 1 + scope 2 x 2 = **10** (the study's ceiling with an attachment) | | |
| Texture sets | Metal 2048 likely, Chassis 4096 likely (largest painted area), Masks, Detail16; the packer decides with the x2.3 factor | 1024 | Body 2048 (class A eyepiece), Lens 256 |
| Bones (13) | `body`, `bolt`, `trigger`, `selector`, `mag_release`, `magazine`, `muzzle_device`, `cheek_riser`, `bipod`, `bipod_leg_l`, `bipod_leg_r`, `bipod_leg_l_ext`, `bipod_leg_r_ext` | - | - |
| Clips | `A_SR01_Fire`, `_BoltCycle`, `_Reload`, `_ReloadEmpty`, `_Selector`, **`_BipodDeploy`**, **`_BipodStow`** (+ optional `_CheekRiser`) | - | - |
| Sockets | 20 (no `Sight` on the gun: no iron sights; the scope's overrides) | 5 | 5: `Mount`, `Sight`, `EyePoint`, `Lens_Front`, `CenterOfMass` |
| Collision | 10 hulls `UCX_SM_SR01_LOD0_00..09` | 1 | 3 |
| Physics | `PHYS_SR01`: one body on `body` (folded-pose hulls); deployed legs are kinematic when held | mass + CoM | mass |
| Reload | straight, `MagInsertStart` -> `Mag` along +Z | | |
| Nanite | off | off | off |

**Stages:** W1 form -> W2 surface -> W3 rig + mag + bipod -> W4 review + fix -> W4b close-up realism -> W5 Unreal ->
W6 finish. Each stage is a fresh workflow from a commit and ends in a commit with its gate file passing.

## 1. Lessons from the AR-01 and the SMG, and where this plan applies them

| Lesson | Applied here |
|---|---|
| Internals the mag and bolt meet came late | **Form stage builds** the bolt raceway (full 88 mm stroke), lug recesses, port opened to the stroke, mag well (walls, shelf, catch window), the release clevis and hook notch, the riser post bores, the bipod hub yoke, detent disks, telescoping tube bores |
| Small parts drifted toward close-ups; rulings came late | **Rulings up front** (`CRAFT_STUDY.md` RP1-RP15; spec `real_pattern_rulings`); a short real-photo pass opens W1 (local only) |
| "Flat clay" early looks (SMG W4) | **Rough-real finishes in the first look**: OD paint orange-peel + edge rim, phosphate roughness split, polished bolt, rubber; studio-HDRI realism rig from W1 (gunlib `realism_job`) |
| Micro strips dropped by Unreal (AR-01 U5/U10) | UD1-UD4 from form; flute run-outs as ball-end exits; no export patching |
| Bake margin, mag AO, edge masks | margin 0, the mag's AO alone, same-side edge masks (W2) |
| Bounds over LOD0 only | **B11 over LOD0-3 x every clip frame x bipod folded/deployed x ext 0..76 x cant +-15 x riser range x bolt open/back** |
| Clips moving the bolt left the selector on safe | Fire, BoltCycle, ReloadEmpty hold the safety at FIRE |
| FBX writes a clip's first frame as node defaults | review tools pose from absolute matrices; ReloadEmpty and BipodStow are `starts_at_rest: false` |
| Per-stage commits so a pause loses nothing | every stage (and W1a/W1b/W3a/W3b sub-steps) ends in a commit with its gate JSON |
| U8 lightmap UV overlaps | authored UV1 gated in Blender at 64 and 128 px (SMG default) |

## 2. Frames and skeleton

### 2.1 Frame (study 5.1)

- +X muzzle, +Z up, -Y = the gun's right (bolt-handle side). **Grip = M (297.13, 0, -96.13)**: 46 mm down the
  traced grip axis (27.15 deg) from the web line Z -55.2. B = M - Grip; the bore is at B Z +96.13. Grip is
  provisional until H1.
- The Blender front view (from -Y) shows the right side = the sheet's panel labelled LEFT.

### 2.2 Bones

| Bone | Parent | Head (M) | Motion | Joint row |
|---|---|---|---|---|
| `body` | root object | Grip | fixed; the physics body | - |
| `bolt` | body | bolt face (505, 0, 0) | **rotate about X 0..-60 deg, then translate -X 0..88** (translation only at -60; rotation only at 0) | sliding 0.15-0.40; lugs hinge 0.10-0.30 while turning |
| `trigger` | body | pivot (368, 0, -57) | rotate about Y 0..+6 | hinge |
| `selector` | body | safety pin (360, -17.5, -16) | rotate about Y, FIRE 0 (bind) / SAFE -12 | hinge |
| `mag_release` | body | paddle pin (408.6, 0, -74) | rotate about Y 0..-4.5 (pad forward, hook back) | hinge |
| `magazine` | body | well entry (458.7, 0, -68.8) = `Mag` | attach only, unweighted | seated mag |
| `muzzle_device` | body | seat (1049.7, 0, 0) | none (hidden when suppressed) | - |
| `cheek_riser` | body (**proposal P1**) | plate bottom (124.4, 0, -3.5) | translate Z -12.9..+12.0 | sliding |
| `bipod` | body | swivel point (780.2, 0, -46.0) | rotate about X -15..+15 (cant); 0 in every clip | hinge |
| `bipod_leg_l` / `_r` | bipod | hub axis (719.6, +-19.5, -62.3) | rotate about Y **0 (folded forward, sheet) .. +90 (deployed down)**, detents 0/+90 | hinge |
| `bipod_leg_l_ext` / `_r_ext` | the leg | collar (896.4, +-19.5, -62.3) | translate +X in the leg's rest frame 0..76, detents every 19 | sliding |

- 13 bones, the same on every LOD. The AR-01 pilot's bones keep their names, parent and axes, so
  `SK_SR01_Skeleton` lists `SK_AR01_Skeleton` as compatible. The bolt's extra rotation and the bipod and riser bones
  are driven by the sniper's own clips (or ABP nodes that do nothing on other guns; U2b).
- `abp_angle_table` in the sidecar: bolt_rotate 0..-60, bolt 0..88, trigger 0..6, selector [0, -12], release
  0..-4.5, bipod_legs 0..90, ext 0..76, cant +-15, riser -12.9..12.

## 3. The bipod: mechanism, poses and gates (user requirement)

**Sheet facts:** folded in GR, GL **and the 3/4** (the study's "deployed in the 3/4" is corrected, spec R5). Folded
authority = GR/GL, checked again by the camera-solved 3/4 gate. Deployed = the real pattern.

**Mechanism (real tension-swivel pattern, every drawn piece accounted for):**
- **Clamp:** the drawn mount, on the forend's plain dovetail. The swivel body runs back to the yoke at the drawn
  hub, and the drawn knob under the hub is the swivel-tension knob.
- **Legs:** each leg on its own transverse pin at X 719.6, Z -62.3, Y +-19.5. They move independently, with a
  spring-ball detent in a two-notch hub disk at 0 and +90 deg. Rotation sign: Blender +R_y swings the forward-pointing
  leg down.
- **Extension:** 0..76 mm in five 19 mm notches (the collar button). Spool rubber feet dia 37.
- **Cant:** +-15 deg about X at Z -46.0. Allowed folded and deployed (worst clearances 7.7 / 32.4 mm).

**Clearances (computed in the spec, 0.5 deg sweep, ext 0 and 76):**

| Pair | Value | Row |
|---|---|---|
| Folded leg top to clamp | 0.20 | hinge 0.10-0.30 |
| Folded feet to forend band | 4.2 | - |
| Feet to each other | 2.0 | - |
| Legs to tension knob (Y) | 2.8 | - |
| Sweep min: forend / barrel / magazine | 13.0 / 29.8 / 206.7 | >= 0.10 |
| Deployed ground (bore height) | ext 0: 268; 19: 287; 38: 306; 57: 325; 76: 344 mm | - |

**Clips:**
- `A_SR01_BipodDeploy` (30 fps, 0-36): the legs 0 -> +90 with the left leading by 2 frames (independent legs), the
  detent click, then ext 0 -> 38 with the button pressed; notifies `BipodLegOut_L`, `BipodLegOut_R`, `BipodLocked`.
- `A_SR01_BipodStow` (0-36, starts deployed at ext 38): ext 38 -> 0, then the legs +90 -> 0; it ends at the bind pose;
  notifies `BipodRetracted`, `BipodStowed`.

**Bounds extension:** Z down to **-344.3** (deployed, ext 76), |Y| up to **113.9** (cant 15 with legs deployed),
folded ext 76 foot front X 1001.6, knob open Z +41.7, open bolt rear X 257.4, riser up Z +44.0. Taken over every LOD.

**Gates F1-F5** (spec `gates.craft_bipod_bolt`): F1 folded (0 intersections, rows above); F2 deploy sweep at ext 0
and 76; F3 deployed feet coplanar +-0.1, legs splayed 12 +-0.05 deg outward (user 2026-10-13), ground by detent; F4 extension sweep in both
poses (sliding row, notches at 19.0); F5 cant +-15 deployed and folded. B3's rotation step for a 296 mm leg radius
is 0.019 deg, so use the coarse-step-with-proof method (`gunlib.fit.sweep`, as the SMG stock fold).

**Physics and game:** `PHYS_SR01` uses folded-pose hulls on `body`. When the gun is dropped, the legs fold first
(BipodStow or snap to 0). Prone use: the game sets the legs to 90 and the extension so that `BipodFoot_L/R` reach
the ground (two-bone-free IK: the extension is a scalar). The README documents it.

## 4. Bolt, safety, trigger, release, riser

- **Bolt:** 3-lug, 60 deg, 88 mm. The knob rest (367.9, -67.6, -33.6) lifts to Z +41.7. It clears the mounted
  scope by **29.9 mm** over rotate + slide (F6: >= 20). The port is opened to the stroke. `A_SR01_BoltCycle` (30 fps,
  0-30): rotate f0-6, back f6-14, hold, forward f16-24, rotate down f24-30; notifies `BoltUnlock`, `ShellEject` (f13),
  `BoltForward`, `BoltLock`.
- **Fire:** the trigger 0 -> 6 -> 0 (60 fps, 0-8); the bolt does not move (bolt action). The cycle is a separate
  clip so the game can chain or skip it.
- **Reload / ReloadEmpty:** paddle press (-4.5), the magazine straight down 67.8 mm to `MagInsertStart`, drop, a new
  magazine up, release, and the hook snaps in. ReloadEmpty starts with the bolt open and ends with it closed.
- **Selector:** FIRE -> SAFE -> FIRE.
- **Riser:** optional clip `A_SR01_CheekRiser` (rest -> +12 -> -12.9 -> rest).
- **F6-F9:** knob/scope >= 20, lugs clear while turning; hook travel 1.88 >= 1.4 + 0.3, the pad keeps 0.36 at full
  press; riser low-stop 0.3; trigger tip 1.3+ from the guard.

## 5. The scope attachment `SM_Att_Scope_LongRange`

- **Frame:** origin `Mount` = the rear ring's recoil lug on the rail-top plane. It mounts at `Rail_Top` + 2 slots
  (M 416.15, 0, 30.0); the front ring sits on slot 12 (ring shifts +2.6 / -1.65 mm from the drawn centres: integer
  slots, declared).
- **Sockets:**
  - `Sight`: scope axis at the eyepiece face, local (-145.05, 0, 27.6);
  - `EyePoint`: 95 mm eye relief behind it, local (-240.05, 0, 27.6). In gun M this is X 176.1, over the cheek riser;
  - `Lens_Front`, `CenterOfMass`.
- **Build:** revolves at 48 sides, with turret knurl and scallops as geometry; slots body + lens; LOD0 6-10k, 3 LODs,
  3 UCX hulls. Through `export_fbx(kind="static")` + `qa_check` like every static.
- **Gates A1-A5:**
  - A1: Mount exactly on a slot;
  - A2: lugs in slots 0.1-0.4;
  - A3: scope >= 2 mm from every gun part at rest and over the bolt cycle and the riser travel;
  - A4: `Sight` Z 57.6 +-0.2 and parallel to the bore <= 0.05 deg (this replaces B4's iron-sight picture);
  - A5: budgets / qa_check.
- **FP/TP:** the attachment gets its own FP + TP component pair (study 2.3); U4 includes it.
- **Exports:** `Exports/Guns/SR01/SM_Att_Scope_LongRange.fbx` for now, moved to
  `Exports/Guns/Shared/Attachments/` when the kit and the `GunShared` lock exist (gun chat's call).

## 6. Budgets (LOD0 floor allocation, gun without the scope)

| Group | LOD0 |
|---|---|
| Chassis incl. slots, pockets, well, dovetail | 9-11k |
| Butt, pad plate, pad, riser + posts | 4-5k |
| Receiver, rail (15 slots), bolt + handle + knob | 6-7k |
| Barrel (48 sides, 6 flutes) + compensator | 4-5k |
| Grip, trigger, guard detail, safety, release | 3-4k |
| Bipod (clamp, body, knob, 2 legs, collars, 2 inner legs, 2 feet) | 5-6k |
| Fasteners | 1-2k |
| **Total** | **32-40k** (target 35-45k, ceiling 50k) |

## 7. Materials and textures

Finishes and values: `CRAFT_STUDY.md` section 3 (spec `materials`). Texel classes:
- **A:** the scope eyepiece;
- **B:** comb, riser top, action bed, receiver, bolt, knob, safety, grip top, rail;
- **C:** forend, well, guard, mag, release, bipod;
- **D:** barrel, compensator;
- **E:** hidden faces.

Sets per the packer (Metal 2048 likely, Chassis 4096 likely). `T_SR01_Masks` from the first build (A = 1 only on the
OD paint, so the user colour never tints rubber or polymer). L5 calibrates against sheet crops (OD 89/89/78
rendered).

## 8. Gate list (numbers in the spec `gates`)

- **S0:** PASS (0 missing, 0 of 33 checks failed).
- **L1-L8:**
  - L1 blockout: GR >= 0.95, GL >= 0.95, TOP >= 0.92 (< 0.90 = stop);
  - L2 form: GR >= 0.96, GL >= 0.958 (the sheet's self-IoU 0.968 - 0.01), TOP >= 0.93, each part >= 0.95; the 3/4
    camera-solved >= 0.93, P95 <= 3 px with the bipod folded;
  - L3 P95 <= 2 px with the declared items;
  - L5 colour; L6 G1-G20;
  - **L7: the blind test is run and REPORTED, not blocking; two realism judges decide the look** (FP 35 cm, scope
    view, TP 3 m, hero 3/4, plus a deployed-bipod hero);
  - L8: early realism per part group at form (chassis, bolt group, bipod, scope).
- **Blender:** B1-B11, UD1-UD4, H1 early (grip girth, reach) and full; B4 replaced by A4 (no iron sights).
- **Craft:** F1-F9 (bipod, bolt, release, riser, trigger). **Scope:** A1-A5. **Magazine:** M1-M10 (straight path).
- **Unreal:** U1-U12 incl. U2b and U5 bounds over every clip frame incl. BipodDeploy; U4 with the scope pair.
- **Pack:** P1-P4.

## 9. Staged build and rough cost

Every workflow: starts from a named commit on the gun branch; holds `SR01` (and `GunLib` only if the gun chat has
accepted a proposal and handed the change over); one Blender process per step, headless; writes
`WorkFiles/guns/sniper/gates/<stage>.json`; ends with a commit. Stop and show the user on a decisive fail (L1 < 0.90,
a both-judges fake call at L8, a design conflict).

| Stage | Does | Gate files | Rough cost (Opus, at the SMG's observed rates) |
|---|---|---|---|
| **W0** (this run) | measurement, trace, craft study, plan, spec, design sheet | spec S0 | ~$10 |
| **W1 form** | W1a: real-photo pass (local), `Scripts/guns/sniper/` (build_sniper.py staged, lock asserted; sniper_parts.py; run_sniper.sh on the SMG chain); blockout (L1) -> form with every internal, both bipod poses, bolt open/back, riser range, release pressed -> L2-L4, B3 + F1-F9, B6a, B7, B8, UD1-UD2, H1 early, form magfit, grey + rough-real renders, L8 per group. W1b: the scope attachment form (A1-A4) | `gates/form.json`, `gates/form_magfit.json`, `gates/scope_form.json` | $35-55 (2-3 sessions; the bipod sweep and the scope add ~30 % over the SMG's W1) |
| **W2 surface** | UV by class, slot tiles, bakes (margin 0, mag AO alone), paint (OD paint chips, phosphate, polished bolt, rubber), Masks, Detail16, L5; scope UV + paint | `gates/uv_bake_paint.json` | $20-35 |
| **W3 rig + mag + bipod** | LOD1-3, twin (10 hulls, tiles), LOD-pop on both bipod poses -> screen sizes on engine radii incl. the bounds extension; rig (13 bones), 7+1 clips, notifies, B11; `export_skeletal_set` + twin + mag + scope exports; fresh-process verify; M1-M10; H1 full | `gates/game.json`, `gates/rig_export.json`, `gates/mag.json`, `gates/scope_export.json` | $25-40 |
| **W4 review + fix** | review sets from exported bytes: L6, L7 blind (reported), 2 realism judges incl. the deployed hero; tech review; fixes in the generators; full chain from nothing | `gates/review_fixes.json` | $25-40 |
| **W4b close-up realism** | FP 35 cm, scope view, hero 3/4, 3x crops; paint orange-peel, chips, phosphate, rubber, lens; target: both realism judges pass the close views | `gates/closeup_r1.json` | $15-30 |
| **W5 Unreal** | harness copied from the SMG's `UnrealCheck/`; U1-U12, U2b, scope FP/TP; one commandlet at a time; sha256 at start and end | `UnrealCheck/verification_summary.json` | $15-25 |
| **W6 finish** | pack materials under `PackMaterials` (`run_build.sh`, short-path mirror root), READMEs (frames, sockets, bipod use, scope attach, bounds, FP pattern), showcase via `studio.py`, `ASSET_LIST.md` row; release `SR01` | `gates/pack_materials.json`, `gates/docs_showcase.json` | $10-20 |
| **Total W1-W6** | | | **~$145-245** |

Costs are rough, from the SMG's stage logs and this run (W0 ~$10). The bipod (a sweep with 296 mm radii) and the
scope attachment are the two items without an SMG precedent.

## 10. Proposed gunlib changes (for the gun chat; not made here, `GunLib` is theirs)

| # | Change | Why |
|---|---|---|
| P1 | `gun_standard.json` `bones.parents.cheek_riser`: add `"body"` (now `["stock"]` only); mirror in `rig.STANDARD_BONES` | SR01 has a fixed butt and no `stock` bone; "never dummies" forbids adding one |
| P2 | `bones.motion_axes`: add `bipod (cant): rotate about X`, `bipod_leg_l/_r: rotate about Y (0 folded forward, +90 down)`, `bipod_leg_*_ext: translate +X in the leg's rest frame`, `cheek_riser: translate Z`, `bolt (bolt action): rotate about X then translate -X` | the line's axis table covers only the AR/SMG motions |
| P3 | `budgets_triangles.sniper`: `{"lod0": [35000, 45000], "ceiling": 50000, "lod3": [2000, 3000]}`; `attachment_optic`: `{"lod0": [6000, 10000], "ceiling": 12000}` | study 5.7 rows missing from the JSON |
| P4 | an `attachments` block: sockets `Mount`, `Sight`, `EyePoint`, `Lens_Front`, `CenterOfMass`; the Mount rule (rear recoil lug on the rail-top plane, integer slot k); the lens slot rule (Q19) | first attachment of the kit; the next ones should inherit it |
| P5 | `parts/dovetail_plain.py`: a plain dovetail band (width, flank, length, chamfers) with LOD rules like `rail_1913` | forend bottom band (R18); common on chassis guns |
| P6 | `rig.key_action` helper for sequenced compound motion (rotate then translate on one bone) + a B3 driver mode for it | the bolt; the pump shotgun later |
| P7 | optional sockets `BoltHandle`, `BipodFoot_L`, `BipodFoot_R`, `SupportHandBipod` in `sockets.optional_gun` | hand target for the bolt cycle; ground IK for the bipod |
| P8 | `parts/hinge.py`: a `telescoping_leg(outer, inner, notches)` generator and a two-notch `detent_disk` | bipod legs here; the LMG bipod later |
| P9 | the TOP-view shadow method (`top_silhouette` in `tools/trace_reference.py`) promoted to the shared trace helpers if the next sheets need it | sheets with a floor shadow under the TOP view |

**W1 status of the proposals (2026-10-13, nothing in gunlib touched; sniper-local code the gun chat can promote):**

| # | Sniper-local implementation | Notes for promotion |
|---|---|---|
| P2 / P6 | `Scripts/guns/sniper/sr_motion.py`: bolt rotate-then-slide (`bolt`, `bolt_cycle_param`), bipod `cant` / `leg` / `leg_ext` (leg ext in the leg's rest frame), riser, release, trigger, selector as 4x4 in frame M | the B3 driver mode for a compound path = sweep the two legs separately (rotate with proof, then slide at -60) as `sr_fgates.py` does |
| P5 | `sniper_parts.chassis()`: the dovetail band as two 45 deg flank cutters under Z -25.1 + a flat clamp seat | a `dovetail_plain` part would take (X range, top Z, half-width, flank, depth) |
| P8 | `sniper_parts.bipod_leg / bipod_ext / bipod_foot / bipod_swivel`: tube + collar + button + notched hub disk, telescoping bore (sliding 0.25), 5 notch rings, spool foot with tread rings, a yoke (rear web + outboard pivot cheeks) clear of the +-15 cant | `telescoping_leg(outer, inner, notches)` and `detent_disk` generators; the cant-clearance rule (wide parts only below Z -54 here) |
| new | `sniper_parts.Part`: ordered boolean steps (U / I / D), loose-edge cleanup, `ud.repair` only when UD fails and only kept when not worse, `weighted_normals(clear_custom=True, weight=100)` | the last two are the SMG 0.2.1 lessons applied by default |
| new | `sr_silhouette.py`: mm -> px mapping fitted from the trace's own px / mm ring pairs; TOP raw + a bounded Y-only fit (shadow bias) + a declared knob window; `--with-npz` stand-in parts (the blockout scope until W1b) | for sheets whose trace JSONs carry px + mm pairs but no origin |
| new | `sr_scope.py`: the first attachment generator (34 mm tube revolve-loop with lens recesses, toothed-prism knurled turrets, rings with recoil lugs keyed to rail slots) | P4's attachment block; the ring / lug rule measured by A1-A2 |


**W2 sniper-side helpers (2026-10-13), candidates for gunlib (not changed here):** per-part cylinder UV frames
(`sr_surface.CYL`: origin / axis / seam per round part, incl. the splayed legs); visibility configurations straight
from the motion module (`sr_uv.configs` on `sr_motion`); the studio-HDRI product rig as a render function
(`sr_render.studio_rig`); a panel-matched L5 render driven by the trace JSON (`sr_render.l5_render` + `sr_l5.py`);
z-buffer per-part silhouette labels with trace-label fixes (`sr_silhouette.raster_zbuffer`); the generator-side weld
step (`sniper_parts.Part(weld_mm=...)`).

## 11. Risks

| Risk | Mitigation |
|---|---|
| Scale ruling 1100 vs the study's 1270 | evidence in MEASUREMENT_NOTES; Q1 asks the user; at the default nothing else changes |
| The deployed bipod has no drawn reference | real-pattern ruling + realism judges on a deployed hero; Q2 (splay) |
| Bipod B3 sweeps are slow (296 mm radius) | coarse-step-with-proof (`fit.sweep`); analytic checks already in the spec |
| The paddle is built 3.4 mm behind the drawn lever | declared (< 2 px); L8 judges the read |
| The TOP feet width (76 built vs ~60 drawn) | declared, TOP is non-authority for the bipod |
| The scope pushes the held draw calls to 10 | at the study's ceiling; no second attachment while the scope is on (README) |
| Real photos not yet gathered (unattended run) | W1 opens with the photo pass; rulings RP1, RP5, RP10, RP15 confirmed or adjusted there |
| gunlib proposals not accepted | P1 fallback: the riser goes static (no bone) rather than a dummy `stock` bone; P2-P8 are conveniences |

## 12. Open questions

See `SR01_STUDY.md` section 9 (Q1-Q6, each with the default the build follows).
