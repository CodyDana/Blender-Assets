# Gun Building Study

Best practice for building game-ready firearms in this repo: the six sheets in `References/Guns/` (Rifle, SMG,
Carbine, LongRifle, Sniper, Pistol), the backlog in `WorkFiles/guns/GUN_REFERENCE_PROMPTS.md` (pump shotgun, DMR,
second SMG, LMG, crossbow) and the attachments kit on one shared rail. Built in Blender 5.2 (headless Python),
exported through `Scripts/pipeline/`, run in Unreal Engine 5.8, for the ninja game (1v1 duel MVP, battle royale
later, first and third person) and for Fab.

**Written:** 2026-10-04. **Versions:** Blender 5.2.0 LTS, Unreal Engine 5.8 (5.8.3 measured on the fan).
**Research notes behind it** (go there for the long form; this file is the working rulebook):
- `WorkFiles/studies/guns/UNREAL_WEAPON_TECH.md`: engine side (static vs skeletal, bones, sockets, first person,
  LODs, attachments, physics, hand attach, Fab listings).
- `WorkFiles/studies/guns/HARD_SURFACE_CRAFT.md`: modelling craft (mid-poly method, bevels, texel classes, the
  fake-gun checklist, sheet self-consistency).
- `WorkFiles/studies/guns/MATERIALS_AND_STANDARDS.md`: finishes, wear, the pack's materials, real dimensions, rail,
  muzzle and magazine standards.
- `WorkFiles/studies/guns/REPO_AUDIT.md` (+ `repo_audit/*.py`): what the pipeline supports, traps, shared parts,
  layout, names, locks.

**Evidence tags.** **[M]** measured in this repo or on this PC (engine headers, Epic's 5.8 template assets, our
code, sheet pixels). **[E]** external, numbered sources in section 13. **[J]** judgement. A claim carries the tag of
the role note it came from; where this study overrules a note, the row in 1.4 says so.

**Revision history.**
- 2026-10-04: first version, from the four role notes and the rifle plan `WorkFiles/guns/rifle/RIFLE_BUILD_PLAN.md`
  (read only).
- 2026-10-04 (rev 2): independent review applied (14 findings, all verified against the code, the UE 5.8 headers or
  Epic's docs; table in section 12). Main changes: static twin slots on separate UV0 tiles (qa_check overlap gate);
  coincident-vertex rule for butted parts; tokenised gun deny list; hand-fit gate H1 on `MH_PlayerDefault`; one
  clearance table; texel classes A/B re-derived from ADS; full FP/TP component set incl. the mag; notifies in the
  sidecar; Compatible Skeletons per class; generated lightmap UV; weapon texture groups; Fab static-lighting and
  "full set of animations" risks.

---

## 1. Purpose, scope and how to use it

### 1.1 The decisions on one screen

| # | Decision | One-line reason |
|---|---|---|
| 1 | **Every gun ships three assets from one build:** `SK_<Code>` (rigid skeletal, the held gun), `SM_<Code>` (static twin: loot, armory, scene dressing) and `SM_<Code>_Mag` (the magazine) | Epic's own 5.8 FP template ships every weapon as `SKM_` + `SK_` + `PA_` + `SM_` [M]; Fab's Firearms category requires moving parts rigged and animated [E5]; the user's reload rule needs a moving mag [M memory] |
| 2 | **Parts are built as separate closed solids with pivots; the rig and the static merge happen only at export** | Static vs skeletal then never touches modelling (flashbang precedent ships both [M]) |
| 3 | **AR-01 is the rig pilot.** No static-only gun ships | Rigging later is cheap only if parts stay separate; doing it on the first gun proves the harness for the line [J] |
| 4 | **Method: generator mid-poly.** The shipped mesh is its own high: real crisp bevels sized by manufacturing process, hardened/custom normals, a normal map carrying only micro relief painted from height functions; Cycles bakes AO only | The katana proved this chain to Unreal [M]; mid-poly + weighted normals is shipped practice [E30] |
| 5 | **One weapon asset, two components** in first person (`FirstPerson` + `WorldSpaceRepresentation`), FP forced to LOD0; **the mag and every attachment get the same FP + TP pair** (the setting is per primitive) | Exactly Epic's 5.8 `BP_ShooterWeaponBase` (`FP_Weapon` + `TP_Weapon`, same `SKM_`) [M]; `FirstPersonPrimitiveType` is not passed to attached children [M `PrimitiveComponent.cpp`] |
| 6 | **Classic LODs, Nanite off** on the skeletal guns; LOD0-LOD3 from the same generator, screen sizes measured | FP is pinned to LOD0; Fab buyers on forward/mobile need LODs [J]; Decimate breaks UVs [M katana] |
| 7 | **One standard for the line:** Blender +X = muzzle, +Z up, -Y = gun's right; origin = `Grip`; lowercase bone table; PascalCase socket table; 1913-profile rail module; one magazine-frame rule; one universal muzzle seat; **checked in the player's hand (gate H1) on the first gun before the SMG inherits it** | One AnimBP per class (Compatible Skeletons), one attachments kit and one animation set per class (long gun, pistol) fit every gun [E20][E52][J] |
| 8 | **Finishes are coatings over a substrate:** parkerizing, anodizing, Cerakote, lacquer are metallic 0; bluing is metallic 1 at ~0.20 linear; wear reveals the substrate | Measured on the sheets and published reflectances [M][E35-38] |
| 9 | **2-3 texture sets per gun** (Metal, Furniture, + the mag's own) with texel density by visibility class (A 80-100 ... E 8-15 px/cm, A and B derived from the ADS view); each set is the smallest power of two that reaches its classes at the fill target (2048 expected, 4096 if the packer says so); no UDIM, no trim sheets; masks texture shipped from the first build | Screen math at 1440p hip and ADS (5.8); UDIM needs virtual texturing [J]; masks make camo and wear sliders free later [J] |
| 10 | **Scale from real published dimensions,** never the sheet rulers | The rulers read 8-26 % long [M] |
| 11 | **Each part has an authority view chosen before tracing** | The rifle sheet's left vs mirrored right views agree to only ~0.89 IoU [M] |
| 12 | **Shared code in `Scripts/guns/gunlib/`;** no change to `Scripts/pipeline/` is needed for the first gun | `skeletal_prop.py` + `np_skeletal.py` already passed a two-process Unreal check on the fan [M] |

### 1.2 Was the study worth doing before the rifle? Yes

The two highest-risk calls apply to all six guns plus the backlog, so they are made once here: **(1)** skeletal guns
with separate parts (the rifle plan assumed two static meshes, which cannot move a bolt, trigger, selector or folding
stock, and which Fab will not accept as a firearm), and **(2)** a rule for AI sheets that disagree with themselves.
A third gain is the shared standard (frame, bones, sockets, rail, mag, slots), which the SMG inherits unchanged.
Getting any of them wrong on the rifle would be paid again on every gun after it [J].

### 1.3 How to use it

1. **Section 2** decides what assets the gun needs (static vs skeletal per use, FP/TP, what to share).
2. **Section 3** is how a gun reads as real. Walk the fake-gun checklist (3.6) before every judge round.
3. **Section 4** is the staged pipeline. Copy the stage table into the gun's plan.
4. **Section 5** is the line standard. Every name, frame and budget comes from there.
5. **Sections 6 and 7** are the Unreal setup and the gates with numbers; copy the gates into the gun's spec.
6. **Section 8** applies it to each sheet; **section 11** lists what the running rifle plan must change.

**The twelve rules.**
1. **A gun reads by its edges.** Each hard edge carries a thin highlight whose width and profile say machined,
   stamped, cast, moulded or wood. One radius everywhere reads CG first.
2. **Classify every part by process before geometry** and let the process set bevel, surface marks, finish and wear.
3. **Silhouette, openings and seams are geometry; texture is micro** (under ~0.5 mm). Never fake a receiver cut,
   rib, rivet or serration with a normal map (CLAUDE.md: height-field relief failed on ornate items).
4. **Bevels are sized for the screen:** max(process radius, 2 px at the nearest view distance).
5. **Parts are parts:** closed solids with real contact or real gaps; no floating, buried or zero-thickness parts.
6. **Model what moves and what moving reveals** (bolt face, port interior, mag feed lips and top round).
7. **Wear tells one story of use** (hands, holster, insertion, sliding, heat), never curvature alone.
8. **A finish is a coating over a substrate;** wear reveals the substrate. Metallic is exactly 0 or 1.
9. **Real scale, generic names, no text, no logos, no invented marks.**
10. **The sheet is the outline authority, per part.** Measure, then blind-test; when a judge and a measurement
    disagree, the measurement wins (stone rule 11).
11. **Same generator, every LOD.** No Decimate, no UV transfer.
12. **If a construction does not converge, change the method** (CLAUDE.md). Stop early and show the user.

### 1.4 Where the role notes disagreed, and what this study decides

| Topic | Positions | Decision and why |
|---|---|---|
| Static or skeletal | Rifle plan: static `SM_AR01` + `SM_AR01_Mag` (skeletal as open Q1). All four notes: skeletal | **Skeletal `SK_` + static twin + mag** (1.1 #1) |
| Socket names | Unreal: PascalCase `Grip/LeftHand/Muzzle/ShellEject/Sight`. Materials: `GRIP_R/GRIP_L/AIM/MUZZLE/EJECT`. Audit: `Grip/SupportHand/Eject/AimPoint`. Rifle plan: `Grip/OffHand/EjectPort/ADS/MagWell` | **PascalCase** (house `Grip`/`Pivot`/`BladeBase`, Epic `Muzzle`/`ShellEject` [M]): `Grip`, `SupportHand` (handedness-neutral), `Muzzle`, `MuzzleSeat`, `ShellEject` (Epic's name), `Sight`, `Mag`, `Rail_*`... full table 5.3 |
| Bone names | Unreal + audit: lowercase snake. Materials: PascalCase `Mag`, `Bolt` | **Lowercase snake** (Manny `hand_r`, fan `stick_00` [M]); table 5.2 |
| `Grip` axes | Unreal: weapon axes. Materials: +X up the grip axis | **Weapon axes (identity at the origin).** The grip angle goes in the sidecar (`grip_axis_deg`) and the per-gun hand offset lives in the game's weapon data, the per-weapon-offset pattern [E20] |
| Mag origin | Unreal: top of feed lips. Materials: centre of the well-entry opening. Rifle plan: AK front-lug hook (rock pivot) | **Origin = the seating pivot:** the well-entry centre for straight-insert mags, the front-lug hook for rock-in mags (AK family), with the rifle plan's `MagRockStart`/`MagInsertStart` path sockets kept (5.6) |
| Rail sockets | Unreal: `Rail_Top` at the first slot. Materials: rail rear end, `(k+0.5)` pitch. Audit: one socket per slot | **One socket per rail at the centre of slot 0;** slot k = socket + k x 10.01 mm along +X; attachments carry a `Mount` socket at their recoil lug (5.4) |
| Coated-metal shading | Craft: blued/parkerized/anodized = metallic 1 dark. Materials: coatings dielectric. Rifle plan: steel metallic 1 at sRGB 40-55 | **Materials wins** (measured sheet ratios + published reflectances): coatings metallic 0; only bluing is a dark metal (~0.20 linear). Metallic 1 below sRGB ~110 is non-physical (3.3) |
| Coated-metal master | Rifle plan: `M_Steel_Master` + Steel Tint. Materials: `M_Fabric_Master` + Metal From ORM | **`M_Fabric_Master` + Metal From ORM** (recolourable coating, bare wear keeps its colour; safe for dark finishes) (5.9) |
| Texture size | Rifle plan: steel 4096 (~90 px/cm). Craft: three 2048 sets by class. Materials: 2048 (~30) or 4096 open | **Sets with visibility classes, A and B derived from the ADS view** (A 80-100, B 60-80 ... E 8-15 px/cm, 5.8). Rev 1 said "90 px/cm exceeds the 1440p need (~55)": that was the hip view only; at a 55 deg ADS FOV with the rear sight 0.25 m from the eye the need is ~98 px/cm [J, review R6]. Set size = smallest power of two that reaches the classes (2048 likely, 4096 allowed: the rifle plan's figure may stand for Metal). Fab: 4096 option for 4K buyers (Q13) |
| UV tiles | Craft + rifle plan: second slot in UV0 tile u 1..2 (katana). Audit: `qa_skeletal` requires UV0 inside 0..1 | **SK: every slot in 0..1** (slots overlap across materials; `qa_skeletal` has no overlap test). **SM twin: slot k on U tile k, always** (Metal 0, Furniture 1, merged mag -1), because `qa_check`'s `uv_no_overlap` tests every UV0 triangle whatever the material [M]. Within a slot, no stacked or mirrored islands anywhere (5.8; review R1) |
| Triangles | Craft: rifle 30-45k, ceiling 50k, + LOD3. Rifle plan: 26-32k, ceiling 45k, LOD3 open | **Target 30-45k, ceiling 50k (house hero range), LOD3 now** (adding it later repeats every verification, the rifle plan's own argument). The rifle plan's per-part table (~27.5k) is a valid low start |
| Mag texture | Materials: mag shares the gun atlas. Craft: own set | **Own 2048 set and MI** (separate mesh, shown up close in reloads, reused by variants); a family mag shared by two guns lives in `Shared/` |
| Skeletal LOD bones | Unreal: drop small bones at LOD2+. Audit: same bones every LOD (fan) | **Same bones every LOD in v1** (fan-measured path; ~10 bones cost nothing) |
| Wear masks | Materials: curvature bake. Craft: analytic bevel parameter | **Analytic** (exposure from the generator's bevel parameter, handling zones from the spec, cavity from the AO bake) |
| Exports, scripts | Rifle plan: `Exports/AR01/`, `Scripts/Guns/AR01/`. Audit: `Exports/Guns/AR01/`, `Scripts/guns/rifle/` | **`Exports/Guns/<Code>/` + `Exports/Guns/Shared/`; `Scripts/guns/gunlib/` + `Scripts/guns/<role>/`** (lowercase like `WorkFiles/guns/`; never mix `Guns`/`guns` in git) |
| Physics asset name | Unreal: `PA_<Gun>` (Epic). Audit: `PHYS_<Code>` | **`PHYS_<Code>`** (house precedent `PHYS_Fan`) |
| Blind test size | Craft: 20 pairs, <= 12/20. Rifle plan: 12 pairs, <= 8/12 | **At least 12 pairs; pass at <= 8/12 or <= 12/20** (both near chance at p ~0.1-0.25) |

---

## 2. Decision guide

### 2.1 Static or skeletal, by use

| Use | Asset | Why |
|---|---|---|
| Gun in hand (owner FP + world TP) | `SK_<Code>` in two components | Bolt, trigger, selector, slide, stock and bipod move; Epic's template does this [M] |
| Gun dropped by a duelist (keeps mag, skin, attachments) | the same `SK_<Code>`, `PHYS_<Code>` set to simulate | Fan pattern: one body, kinematic while held [M] |
| Battle-royale ground loot (many instances) | `SM_<Code>` with UCX hulls | Epic's pickup is a static mesh with a physics body; `SM_Pistol` carries convex hulls [M] |
| Armory glass cases, set dressing, Fab static buyers | `SM_<Code>` | One mesh, one hull set, Nanite-capable later |
| Magazine (seated, in hand, dropped) | `SM_<Code>_Mag` on the `magazine` bone's `Mag` socket, in **two components** (FP + WSR) like the gun | Supports both reload patterns (6.2) and drum/extended mags [E9]; the FP setting is per primitive (2.3) |
| Attachments (optic, suppressor, grip, laser, light) | static `SM_Att_<Type>_<Name>` | Fab modular packs work this way [E10-E16]; each also needs FP + WSR components, so keep them few |
| Bipod, folding sights | bones on the gun (sniper bipod is drawn fixed to the gun) | A separate rigged attachment only if the kit sells a bipod |

**Why not "static parts moved in Blueprint":** many components per gun, each doubled for FP and TP, and no
authored clips. Every listing read and Epic's template use bones [M][E].

### 2.2 What animates, per gun (only parts visible from outside; internals are not modelled)

| Part | Rifle AR01 | SMG01 | Carbine CB01 | LongRifle LR01 | Sniper SR01 | Pistol HP01 |
|---|---|---|---|---|---|---|
| Bolt / carrier | `bolt` (carrier + charging handle, one part) | `bolt` (if visible in the port) | `bolt` | `bolt` | `bolt` (rotate, then slide) | - |
| Charging handle | - | `charging_handle` (front, non-reciprocating) | `charging_handle` (T-handle) | `charging_handle` | - | - |
| Slide / barrel | - | - | - | - | - | `slide` (barrel fixed: gas design) |
| Trigger, selector, mag release | yes | yes | yes | yes | yes (safety) | yes (safety on the slide: child of `slide`) |
| Hammer | not visible | - | - | - | - | `hammer` |
| Bolt catch / slide stop | - | optional | `bolt_catch` | `bolt_catch` | - | `slide_stop` |
| Dust cover | removable only, no bone | - | `dust_cover` (port door) | `dust_cover` | - | - |
| Stock | fixed | `stock` (side fold) | `stock` (collapse) | fixed | `cheek_riser` (optional) | - |
| Sights | `sight_rear` (leaf) | flip if drawn | `sight_front`, `sight_rear` (flip) | fixed in carry handle | - (scope) | - |
| Bipod | - | - | - | - | `bipod`, `bipod_leg_l/_r` | - |
| Muzzle device | `muzzle_device` (hide when suppressed) | yes | yes | yes | yes (cap) | - |

Backlog: shotgun `pump`; LMG `feed_cover`, `bipod*`; crossbow `string`, `limb_l/_r`.

### 2.3 First- and third-person strategy

- **One mesh asset in two components** (Epic 5.8 pattern [M][E1]): `FirstPersonPrimitiveType = FirstPerson` for the
  owner (FP FOV and scale, casts no scene shadow) and `= WorldSpaceRepresentation` for everyone else (owner-no-see,
  casts the shadow, shows in reflections) [M `PrimitiveComponent.h`].
- **The setting is per primitive.** `FirstPersonPrimitiveType` is a property of each `UPrimitiveComponent`
  (`PrimitiveComponent.h:730`, `SetFirstPersonPrimitiveType` only marks its own render state dirty); nothing in the
  5.8 source passes it to attached children [M `PrimitiveComponent.cpp`, `PrimitiveSceneProxyDesc.cpp`]. So the
  **full component set per held gun** is: `FP_Weapon` + `TP_Weapon` (`SK_<Code>`), `FP_Mag` + `TP_Mag`
  (`SM_<Code>_Mag` on `Mag` of the matching weapon component), and `FP_<Att>` + `TP_<Att>` per attachment. Every FP
  component: `FirstPerson`, **`ForcedLodModel = 1`** (= LOD0); every TP component: `WorldSpaceRepresentation`
  (owner-no-see is set by the engine).
- **Draw calls per held gun** = sum over components of material sections: rifle = 2 x 2 (gun, Metal + Furniture) +
  2 x 1 (mag) = **6**, + 2 x slots per attachment (a red dot with body + lens = 4 more). The "at most 3 slots" rule
  (5.9) is per mesh; budget the held total too: <= 10 for a gun with two attachments [J].
- **FP components forced to LOD0**, so LOD0 and the textures must hold 15-60 cm from the eye, ADS included (5.7, 5.8).
- A separate richer viewmodel is not needed at our budgets; revisit only if an ADS close-up shows something the
  world mesh does not need [J].
- Project requirements: deferred renderer, Virtual Shadow Maps (or ray-traced shadows), Allow Static Lighting off
  [E1]. Stated in every gun README; open decision for `DemoGame_1` (Q5). **Fab example content must not depend on
  them:** the example Blueprint and overview map load and render with static lighting allowed and no `Config/`
  (ASSET_GUIDELINES 11 self-test; Epic says FP features fall back when the requirements are missing [E1]); the
  project-setting instructions live in the README only (9).

### 2.4 Build once, share, or attach

| Thing | Rule |
|---|---|
| Rail, sight posts and apertures, pins, screws, rivets, sling swivels, QD sockets, selector levers, triggers | **gunlib modules**, built once, every gun calls them |
| Black-rifle lower, upper core, trigger group, curved 30 mag, birdcage hider | **shared by Carbine and LongRifle** from one spec (the two sheets disagree on scale by ~13 % [M]) |
| Magazines | two generators (curved box, straight box) + per-gun parameters; a family mag is one asset in `Shared/` |
| Flip sights | one design for SMG + Carbine |
| Muzzle devices | always a separate part with its own bone; one universal suppressor replaces any of them |
| Scope | **attachment no. 1** on the rail, not baked into the sniper |
| Bipod | sniper bones (the sheet draws it fixed) |
| Wood/polymer furniture, receivers, handguards, stocks | per gun |

### 2.5 Build or buy

The user chose to build (memory `realistic-guns`). Common guns could be bought for the game only, never sold
(Fab Standard License content may not be redistributed standalone [M FAB_ASSET_STUDY]). This study assumes we build.

---

## 3. Principles of believable guns

### 3.1 Form by manufacturing process (put the class in the spec for every part)

| Class | Process / parts | Edge (LOD0 width, segments LOD0/1/2) | Surface marks | Finish and wear |
|---|---|---|---|---|
| M-chamfer | machined broken edge: barrel, blocks, bolt, rails, slide | 0.2-0.6 mm 45 deg chamfer, but >= the visibility minimum; 1/1/0 | lathe rings, milling passes (roughness only); inside corners keep the cutter radius 2-6 mm | dark finish; bright steel on high edges, polish along sliding axes |
| M-round | machined radius: sight ears, slide top | 0.8-1.5 mm; 3/2/1 | as above | as above |
| S-bend | stamped sheet bend: AK receiver, dust cover, mag body | inside radius >= sheet thickness (~1 mm); 3/2/1 | ribs with soft radii, dimples, rivet heads both faces, faint oil-canning | paint/lacquer; wear on rib crests and bend apexes, never on the flat between |
| S-cut | stamped cut edge | 0.2-0.3 mm land; **the sheet thickness shows**; 1/0/0 | | |
| C-fillet | cast / forged: hammers, triggers, pistol frame | 1-3 mm; 3/2/1 | casting grain, parting line | less polished |
| P-round | moulded polymer: SMG body, grips, stocks | 0.6-2 mm; 2-3/2/1; **1-2 deg draft** on walls | parting line, sink at thick ribs, ejector circles on hidden faces, stipple zones | matte; wear **polishes** (roughness down), never shows metal |
| W-round | wood: AK stock, handguards, grip | 1.5-4 mm, larger where handled; 3-4/2/1 | 3D grain along the blank, end grain on cut ends, pores | finish worn to raw wood at hand zones; dents on toe and heel |

**Visibility minimum** (a highlight under ~2 px vanishes under TAA/TSR; 1440p, 70 deg FP FOV) [J, craft 3.3]:
on-screen px/mm = W / (2 d tan(HFOV/2)); about **0.4 mm** at the rear of the gun (d 0.30-0.35 m, ~5.2 px/mm),
**0.5-0.7 mm** mid (mag, handguard), **0.7-0.9 mm** front (gas block, brake). Weapon artists exaggerate bevels for the
same reason [E24].

### 3.2 Geometry or texture

| Geometry (LOD0) | Texture only |
|---|---|
| Protruding rivet and screw heads (random slot clocking, +-0.1 mm dome variation); flush pins as an inset ring | Threads, tiny set screws |
| Magazine ribs, slide serrations (1.5-3 mm pitch), cocking grooves, flutes | Checkering (18-24 lpi [E50]), knurl, stipple, pebbling |
| Every opening the sheet shows, with wall thickness; brake ports cut through | Wood grain and pores, tool marks, lathe and milling marks |
| The bore: >= 2 calibres deep, chamfered crown | Rifling (close renders only), carbon |
| Checkered-panel borders, turret scallops on a silhouette | |

Fastener **count and position** come from the sheet only; **size** from the sheet when the head spans >= 4 sheet px,
otherwise from engineering norms (rivets 4-7 mm domed 0.6-1.5 mm proud; pins 3-5 mm; screws of 3-5 mm metric
thread with 5.5-8.5 mm heads; never write fastener sizes as "M" + number, which reads as a gun name) recorded with their source. Sub-pixel sizes from norms are manufacturing truth below the sheet's resolution,
not invention [J]. **No text, ever:** no proof marks, numerals, logos or fake scribbles; the AK sight leaf gets plain
ticks only if the sheet shows ticks (default: none).

### 3.3 Material values (Unreal metal/roughness; Specular 0.5 on dielectrics)

| Finish (where) | Metallic | Base colour, linear (sRGB) | Roughness | Wears to |
|---|---|---|---|---|
| Bare / machined steel (worn edges, bolt, bore, pins) | 1 | 0.53-0.56 (190-196) [E4][E34] | 0.25-0.40; sliding-polished 0.15-0.25 | - |
| **Black lacquer / paint over steel** (AR-01 receiver, mag) | 0 | 0.025-0.04 (45-55) [M] | 0.40-0.55 satin | bare steel, sharp-edged chips |
| Bluing / black oxide (variants, small parts) | 1 | 0.16-0.22 (110-130) [E38] | 0.25-0.60 | grey-brown, then bare steel |
| Manganese phosphate (barrels, SMG/carbine steel) | 0 | 0.03-0.06 (50-70) [E35] | 0.65-0.85 (oiled 0.55-0.70) | bare steel |
| Type III anodized aluminium (carbine/long-rifle receivers, rails, scope) | 0 | 0.025-0.05 (45-62) [E36] | 0.45-0.65 | bare aluminium: metallic 1, 0.91, rough 0.30-0.45 (bright silver) |
| Cerakote-type paint (sniper OD) | 0 | sheet OD ~0.05 (89, 89, 78 rendered) [M] | 0.45-0.75 [E37] | substrate, dark rim first |
| Glass-filled polymer (SMG, black-rifle furniture) | 0 | 0.02-0.04 (40-55) [M] | 0.50-0.70; stipple 0.75-0.90 | itself, polished -0.10 to -0.20 |
| Brushed stainless (pistol) | 1 | (0.67, 0.64, 0.60) [E34] | 0.25-0.40 along, +0.15 across | scratches |
| Walnut-tone shellac (AR-01 wood) | 0 | 0.04-0.07, hue 18-22 deg, sat 0.45-0.65 [M] | 0.35-0.55 | raw wood: lighter, rougher, oil-darkened around |
| Rubber (pads, grips, eye cup) | 0 | 0.02-0.03 | 0.70-0.90 | barely; dust |
| Soot (muzzle, gas, port) | 0 | 0.02-0.03 | 0.80-0.95 | gradient from the vent |

Measured sheet ratios are lit, not albedo: use them for hue, relative value and wear contrast; use [E] for absolute
values. The AR-01 receiver reads 0.17-0.21 x the backdrop, far darker than any metal would render, which is why it is
lacquer, not bluing [M]. Calibrate every finish against a sheet crop under matched light before the first look
review (the katana's first blade was far too dark [M]). Anisotropy needs a project setting buyers may not have:
default to brushed micro-normal + roughness, anisotropy as an optional switch [E51].

### 3.4 Wear: place it by cause

| Cause | Where | What it does | Masks channel |
|---|---|---|---|
| Edge abrasion | convex hard edges: receiver corners, ribs, sight ears, crown, rail edges, stock edges | coating chipped to substrate in a 0.5-3 mm band | R |
| Firing hand | grip front/back strap, palm swell, thumb rest | polymer polished; wood finish worn then oil-darkened | G |
| Support hand | handguard belly and left side (right-handed), SMG magwell | as above | G |
| Cheek weld | left side of the comb | polished, darkened | G |
| Thumb travel | selector lever and the arc it sweeps on the receiver | bright scratch arc | G |
| Mag insertion | magwell rim (scratch fan into the well), mag spine, feed lips | streaks along the insertion axis | R + G |
| Drops and grounding | mag baseplate corners, butt toe and heel, bipod feet | dents, bare corners | R |
| Holster (pistol) | slide front, front-sight base, slide flats | worn bright | R + G |
| Sliding parts | carrier flank, charging-handle face, slide rails | polished bare metal | R (forced) |
| Heat and gas | muzzle device, gas block, ejection port | soot gradient (heat tint rare) | own range |
| Cavity grime | rail slots, screw heads, seams, grip troughs | darker, dusty or oily | B |

Wear follows a life story (finish, coating, scratches, dust, oil, hand marks [E26][E27]); keep surface wear subtle
and edge wear hard; scratches vanish by 3-5 m [E27]. Target the sheet's own wear level ("moderate" in the prompts
[M]). No mirrored or stacked UV islands on guns at all (5.8: unique texels; the static twin's tile scheme has no
room for the +1 U mirror tile).

### 3.5 Scale: real figures, not the rulers

| Code | Style reference | Overall | Barrel | Mass | Ruler error on the sheet [M] |
|---|---|---|---|---|---|
| AR01 | AKM [E44] | **880 mm** | 415 mm | 3.1 kg without mag (3.3 with empty mag); loaded 30-rd mag ~0.82 kg | +11-13 % (ruler mislabelled: "90" twice) |
| SMG01 | UMP45 [E45] | **690 mm** (450 folded) | 200 mm | 2.5 kg | +26 % |
| CB01 | M4 [E46] | **838 mm** (756 collapsed) | 368 mm | 2.92 kg | +16 % |
| LR01 | M16A2/A4 [E47] | **~1000 mm** | 508 mm | 3.40 kg | +16-17 % |
| SR01 | AWM-class [E48] | **1270 mm** | 686 mm | 6.9 kg | no ruler |
| HP01 | Desert Eagle 6 in [E49] | **273 mm** | 152 mm | 2.0 kg | +9 % |

Scale each gun to its overall length, then check proportions with the sheet's length/height ratio, which does not
depend on the ruler. Real figures within +-5 % (Q15). Mass goes on the physics body; the builder computes the centre
of mass from part volumes and scales to these totals (hollow internals are not modelled).

### 3.6 The fake-gun checklist (walk it before every judge round)

| # | Tell | Measurable check |
|---|---|---|
| G1 | Soft, blobby bevels | bevel width per class = spec +-0.05 mm; widths differ across classes (CV > 0.3) |
| G2 | Missing chamfers | every hard edge >= its visibility minimum; raking-light render shows a continuous highlight |
| G3 | Faceted rounds | facet angle <= 7.5 deg at LOD0 (48 sides on a barrel); analytic custom normals on rounds |
| G4 | Gradients on flats | flat-face normal deviation < 1 deg |
| G5 | Floating or buried parts | every joint sits in its row of the clearance table (3.7): butt joints 0.01-0.05 mm (never exact: no two vertices of different parts within 1 micron), moving joints in their row, visible seams 0.2-0.8 mm with depth; 0 intersections at LOD0-LOD1 |
| G6 | Wrong screw/pin/rivet scale | every size listed with its source (sheet px or norm); error against that source <= 0.1 mm or <= 1 sheet px, whichever is larger |
| G7 | Plastic-looking metal | metallic exactly 0/1; bare steel near Epic iron; metal roughness histogram has >= 2 modes |
| G8 | Metal-looking plastic | no polymer texel with metallic 1; polymer wear lightens/glosses only |
| G9 | Uniform, mirrored or repeated wear | wear = exposure x handling x motion; no mirrored or stacked UV islands (5.8); left/right wear differs |
| G10 | Everything mirrored | handed features (selector, port, charging handle, bolt handle, catch) only on the side the sheet shows |
| G11 | Too-clean bore | bore >= 2 calibres deep, crown chamfer, darkening with depth, carbon at the crown |
| G12 | Holes without walls | every opening cut in geometry with visible wall thickness |
| G13 | Zero-thickness sheet metal | ~1 mm sheet thickness visible at cut edges and openings |
| G14 | Stretched wood grain | 3D grain in a virtual blank per part, continuous across bevels, end grain on cuts |
| G15 | Too new, or uniformly dirty | dust only in cavities away from hands; scratches gone at 5 m |
| G16 | Fake markings, invented details | nothing the sheet does not show; text-free |
| G17 | Silhouette drift | traced authority, IoU gates (7.3) |
| G18 | LOD pops | same-generator LODs; switch difference <= 1 px mean at 1440p |
| G19 | Polymer without draft or parting lines | 1-2 deg draft, parting line on the mould split |
| G20 | Colour off under the scene light | crop-matched hue, R/B and median luma vs the sheet (stone S16 method) |

### 3.7 Clearance table (the one source for G5, B3, M2, M3)

| Joint type | Examples | Clearance per side (LOD0) | Checked by |
|---|---|---|---|
| Butt / fixed contact | stock or grip to receiver, rail on a receiver top, handguard to cap, flush pins, rivet heads on sheet | **0.01-0.05 mm** modelled gap (or contact faces built so no vertex of one part lies within 1 micron of another's) | G5, B6a |
| Sliding | carrier in the receiver, charging handle in its slot, slide on the frame, stock on its tube, mag release | **0.15-0.40 mm** at rest and over the whole travel | B3 |
| Hinge / rotating | trigger, hammer, selector, sight leaf, dust cover, folding stock, bipod legs | **0.10-0.30 mm** radial and axial; swept minimum >= 0.10 mm | B3 |
| Seated mag | mag body in the well | lateral **0.20-0.60 mm**, top-stop 0.1-0.5 mm, lug in recess 0.1-0.4 mm | M2, M3 |
| Visible design seam | panel and assembly seams the sheet shows | **0.2-0.8 mm** with modelled depth | G5 |

Why a butt joint is never exact [M]: the static twin joins every part into one mesh and `qa_check`'s
`no_coincident_vertices` fails any vertex pair within 1e-6 m across the mesh (`COINCIDENT_DISTANCE`). Parts built from
the same traced outline or loft rings share positions where they meet. 0.01 mm is 10x that tolerance, far below 1 px
at any view distance, and 50x Unreal's `UE_THRESH_POINTS_ARE_SAME` (0.00002 cm) [M `UnrealMathUtility.h`]. `qa_skeletal` has no such test, so without this rule
the failure would surface only at the twin export (stage 6).

---

## 4. The pipeline in this repo

### 4.1 Staged build (copy into each gun's plan)

| Stage | Output | Gate before the next stage |
|---|---|---|
| 0 Sheet + trace | side assignment by handed features; scale from 3.5; traced outlines per view (`props_lib/trace.py`, the rifle study's `refimg.py`); the sheet's self-consistency map | sides and authority views recorded; the user asked if two views disagree on design (not drawing error) |
| 1 Spec | `WorkFiles/guns/<role>/<role>_spec.json` against `gun_standard.json` (4.3) | S0 (7.1) |
| 2 Blockout | primary volumes from the traces | L1; **below 0.90 IoU = change the method** |
| 3 Form | every part as a closed solid with process bevels, pivots and motion limits; revealed geometry | L2-L4, B3 (rest + extremes), B7, **B6a (`qa_check` topology on the joined twin, from now on every build)**, H1 grip girth and trigger reach (early); early image-pair look on two crops (stop on a decisive fail) |
| 4 UV + paint | sets per 5.8, AO bake, per-texel paint (BC/ORM/N + `T_<Code>_Masks` + Detail16) | B9; renders from the baked maps only |
| 5 Game | LOD1-3 from the generators, rig (`root` + bone table, rigid bind, triangulate), sockets, UCX for the static twin, physics proxy, clips + notifies | B1-B6, B8, **H1 (full, in `MH_PlayerDefault`'s hands)**, LOD-pop gate fixes the screen sizes |
| 6 Export | SK set + SM twin + SM mag + sidecars; sha256 recorded | B10; export warnings reviewed |
| 7 Mag fit | mag top fitted to the exported well (saya method), seat and insertion path | M1-M6 (7.2) on exported bytes |
| 8 Look review | blind design judge + realism judge; G1-G20 with evidence | L6, L7; fixes loop to 3-7 |
| 9 Unreal | two-process harness on the exact bytes | U1-U11 (7.4) |
| 10 Colour system | recolour maps, `material_spec.json` items + instances, under the PackMaterials lock via `run_build.sh` | P1-P4 (7.5) |
| 11 Docs + showcase | `README.md`, `MATERIALS_README.md` (frames, sockets, reload path, FP requirements, tri counts, texture sizes), `showcase/<Product>/` via `studio.py`, one `ASSET_LIST.md` row | lock released; only this gun's exports changed |

### 4.2 Reading AI sheets

- **Resolution** [M]: rifle side views ~0.8 px/mm (Sheet B close-ups 2-3 px/mm); SMG ~0.85; carbine ~0.7; long rifle
  ~0.6; sniper ~0.5; pistol ~2.1 px/mm. Chamfers and most pins are sub-pixel everywhere except the pistol.
- **Sides by handed features, never by label:** the rifle and sniper sheets have LEFT/RIGHT swapped [M].
- **Authority view per part**, recorded in the spec before tracing (rifle: selector and charging handle from the
  right; dust cover and rear sight from top + Sheet B; mag and grip from the view that agrees with top and 3/4).
- **Gate each view on its authority parts**, and the rest of the view against the sheet's own disagreement.
- **Shared parts come from one spec;** each gun's proportions are fitted around them.
- If two views disagree on design, stop and ask (Q11): pick per part or regenerate the sheet.

### 4.3 The spec (one JSON per gun, like `katana_spec.json`)

Per part: process class (3.1), bevel class per edge set, material family and texture set, texel class (5.8),
authority view, traced outline id, pivot frame and motion (axis, travel or angle, limits), bone, contact parent,
fastener list (position, type, size, source), handling zones, revealed geometry. Per gun: code, real dimensions and
mass, frame, sockets, LOD budgets and screen sizes, gates with numbers. Everything else (builder, painter, measurer,
fit, export) reads it. Shared values (bone table, sockets, rail profile, mag families, density classes) live in
`WorkFiles/guns/gunlib/gun_standard.json`.

### 4.4 Geometry method (headless Blender 5.2)

| Primitive | For | Note |
|---|---|---|
| Bevelled extrusion of a traced outline | receiver sides, trigger guard, stock/grip blanks, slide, sight ears | own builder (katana `MB` style); offsetting is our own code (no shapely/scipy in Blender [M]); the curve route works once welded (24 non-manifold edges before, 0 after [M probe]) |
| Lofted sections | barrel, gas tube, handguards, mag body on its curve, stocks, rails | katana loft with explicit bevel lands, analytic normals per ring |
| Revolves | brake body, pins, rivets, sight drum, scope tube, turrets | 32-48 sides at LOD0 |
| Boolean cuts | ejection port, magwell, slots, brake ports | MANIFOLD/EXACT solvers exist [M probe]; prefer cuts built into the outline/loft for clean topology and exact UVs |
| Bevel (Harden Normals) + Weighted Normal (Keep Sharp) | box-plus-cut parts | house rule; `face_strength_mode`, `use_face_influence` exist in 5.2 [M probe] |
| Analytic custom normals | rounds, curved furniture | `normals_split_custom_set` (no auto-smooth flag in 5.x) [M] |

Avoid: SDF/remesh hulls (round everything, G1), subdivision on the shipped mesh, Decimate for LODs. Quads on flats,
triangulated before skeletal QA; UV seams and sharp edges on bevel boundaries; no hidden faces unless an animation
reveals them; never unfold sub-texel bevel lands into their own UV charts (kunai lightmap lesson [M]).

### 4.5 UV and paint

- Parametric per-corner UVs in mm, packed per set by the katana skyline packer with per-island scale by texel class;
  LOD1-3 reuse the islands. Straight, axis-aligned islands; UV-up = gun-up (camo).
- **Painter (katana `katana_tex.py`, extended):** edge exposure from the analytic bevel parameter; 3D wood grain in a
  virtual blank per wooden part; process marks; checkering, knurl, stipple and serration height functions in each
  part's frame; the spec's handling zones and motion paths with per-instance seeds; normal map from painted height
  only (DirectX); AO from a Cycles bake of the assembled LOD0 at rest (contact shadows), with mild cavity darkening in
  BC on metals.
- Outputs per set: `T_<Code>_<Set>_BC` (sRGB), `_ORM` (linear), `_N` (DirectX); per gun `T_<Code>_Masks` (linear RGBA,
  5.10); `Detail16` (G16 linear, square) for each recolourable slot.

### 4.6 Rig and export

- Armature object `root` at the origin, identity; bones from 5.2, rest rotation = root's; each part object gets one
  vertex group at weight 1.0, parts of one LOD joined, triangulated; `qa_skeletal(max_influences=1)` (an existing
  argument: no pipeline change [M]).
- `skeletal_prop.export_skeletal_set`: `SK_<Code>.fbx` (LOD0 + armature), `SK_<Code>_LOD1..3.fbx`, one `A_<Code>_*.fbx`
  per clip, all from the centimetre copy; `SK_<Code>.skeletal.json` with bones, sockets on bones, LOD files and screen
  sizes, `bounds_extension_cm` (posed envelope over every clip), physics bodies, import settings, mass, plus gun fields
  (`class`, `grip_axis_deg`, `rail_slots`, `muzzle_class`, `mag_family`, `texel_classes`). Physics proxy FBX in
  `Physics/` (fan method).
- `SM_<Code>` and `SM_<Code>_Mag` through `export_fbx(kind="static")` with UCX + `.sockets.json`; LOD screen sizes
  passed from the build script (the CLI has no flag). **On the SM copy only, `export_gun` moves slot k's UV0 islands
  to U tile k** (Metal 0, Furniture 1, merged mag -1) before `qa_check` (5.8).
- Clips (Fab needs a set; the game may drive some procedurally): `A_<Code>_Fire`, `_Charge`, `_Reload`,
  `_ReloadEmpty`, `_Selector`, plus `_StockFold`, `_BoltCycle`, `_BipodDeploy`, `_SightFlip`, `_SlideLock` per gun.
- **Notifies do not travel through FBX** (ASSET_GUIDELINES 8 says the same for material animation; neither the fan
  harness nor `np_skeletal` adds any [M]). The skeletal sidecar carries them:
  `"notifies": [{"clip": "A_AR01_Reload", "name": "MagDrop", "frame": 14}, ...]`, names from the standard
  (`MagRelease`, `MagOut`, `MagDrop`, `MagIn`, `BoltRelease`, `ShellEject`, `Fire`, `SlideLock`), frames from the
  clip keys. The Unreal harness adds them (`unreal.AnimationLibrary` notify-track and notify-event functions; the
  exact call and whether a named skeleton notify or an `AnimNotify` class per name is used is probed on the first
  gun [J]). Notifies the character's montage owns in reload pattern 2 (`MagOut`, `MagIn` on the hand) are the
  buyer's; the README lists the names and the weapon-clip frames to copy.

### 4.7 gunlib modules and layout

```
Scripts/guns/gunlib/                 lock GunLib; LIB_VERSION; ROOT from __file__ (never a literal path)
  standard.py                        loads WorkFiles/guns/gunlib/gun_standard.json
  mesh.py                            generalized katana_mesh (MB, loft, revolve, sweep, caps, UV helpers)
  parts/                             rail_1913.py, barrel.py, muzzle.py, mag_curved.py, mag_box.py, trigger_group.py,
                                     sights_flip.py, sight_post.py, hardware.py (pins, screws, rivets, swivels), hinge.py
  rig.py                             armature from the table, rigid bind, triangulate, key actions (from fan_look.py)
  sockets.py                         socket records on bones -> sidecar (skeletal_prop.ue_component_transform)
  qa_gun.py                          gun gates on top of qa_skeletal / qa_check, gun deny list
  export_gun.py                      SK set + SM twin + SM mag + physics proxy + sidecars
  fit.py                             motion sweep, mag seat and insertion path (from saya_fit / the rifle mag_fit)
  paint.py, uvpack.py                painter and packer generalized from the katana
  render.py, compare.py, refimg.py   sheet-matched ortho renders, side-by-sides, sheet panel finder (refimg promoted
                                     from WorkFiles/guns/rifle/tools/ once the rifle study is done with it)
Scripts/guns/<role>/                 rifle/ smg/ carbine/ longrifle/ sniper/ pistol/: build_<role>.py (staged,
                                     lock asserted at the top), <role>_parts.py, run_<role>.sh
WorkFiles/guns/gunlib/gun_standard.json
WorkFiles/guns/<role>/               plan, <role>_spec.json, reports, UnrealCheck/, check scripts (scratch not in git)
Assets/Guns/<Code>.blend             (LFS)
Exports/Guns/<Code>/                 SK_<Code>*.fbx, SK_<Code>.skeletal.json, A_<Code>_*.fbx, SM_<Code>.fbx + .sockets.json,
                                     SM_<Code>_Mag.fbx + .sockets.json, Physics/, Textures/ (+ Recolour/), README.md,
                                     MATERIALS_README.md
Exports/Guns/Shared/                 family mags, flip sights; later Attachments/        (lock GunShared)
Renders/Guns/<Code>/, showcase/<Product_Name>/ + ASSET_LIST.md row
```

**Rule of extraction:** write the rifle's code in `Scripts/guns/rifle/`, move a module to gunlib only when the SMG
needs it, bump `LIB_VERSION`, and re-run the earlier guns' QA (fan/katana hash pattern) [J].

### 4.8 Names, codes and locks

| Role | Product name (generic) | Code | Lock |
|---|---|---|---|
| Rifle (AK style) | Assault Rifle AR-01 | `AR01` | `AR01` |
| SMG | Compact SMG SM-01 | `SMG01` (avoids `SM_SM01`) | `SMG01` |
| Carbine | Carbine CB-01 | `CB01` | `CB01` |
| Long rifle | Long Rifle LR-01 | `LR01` | `LR01` |
| Sniper | Sniper Rifle SR-01 | `SR01` | `SR01` |
| Pistol | Heavy Pistol HP-01 | `HP01` | `HP01` |
| Library / shared exports / materials | - | - | `GunLib` / `GunShared` / `PackMaterials` |

Unreal: `SK_<Code>`, `SK_<Code>_Skeleton` (one per gun), `PHYS_<Code>`, `SM_<Code>`, `SM_<Code>_Mag`, `A_<Code>_*`,
`M_`/`MI_<Code>_<Slot>`, `T_<Code>_<Set>_<Map>`, attachments `SM_Att_<Type>_<Name>`; checks under
`/Game/GunCheck/<Code>_<run>`. Never join words into a deny-list hit (`DrawMag` contains `awm`: use `MagDraw`).

### 4.9 Pipeline additions, in order

| When | Addition | Built from |
|---|---|---|
| Before the AR-01 rig stage | `gun_standard.json` + `standard.py`; `rig.py` (rigid bind); `qa_gun.py` = `qa_skeletal(max_influences=1)` + bone/socket table + **tokenised gun deny list** (below) + frame check + "unweighted `magazine` bone survives the FBX" check; `export_gun.py` (SM-copy UV tile offset, 5.8) | `fan_look.py`, `skeletal_prop`, `export_fbx`, `build_fan.py` |
| During AR-01 | `fit.py` (motion sweep B3, mag seat and path M1-M6), sight-picture gate, LOD-pop measurer, gun Unreal harness | `saya_fit.py`/`saya_verify.py`, rifle plan's `mag_fit`, kunai/flashbang LOD method, `WorkFiles/fan/UnrealCheck/`, `WorkFiles/katana/UnrealVerify_*` |
| Before the SMG | extract `mesh.py`, `paint.py`, `uvpack.py`, `rail_1913`, `mag_box`, `hinge`, `sights_flip`, `hardware`; promote `refimg.py` | the rifle's code |
| Before the Carbine | `ar_lower`, `ar_upper(top=rail|carry_handle)`, `ar_barrel`, `ar_stock`, `mag_ar` | |
| Before the Fab gun pack / BR skins | `M_Weapon_Master` (PackMaterials lock, preflight, `run_build.sh`); lens material decision; `studio.py` landed in main | `material_spec.json` process |
| Never needed for v1 | edits to `Scripts/pipeline/` (optional later: a UV tile-range argument for `qa_skeletal`, with its self-test) | |

**The gun deny list is matched on tokens, not with `\b`** [M]. In Python regex `_` and digits are word characters, so
`\bak\b` misses `SM_AK47`, `T_UMP45_BC` and `MI_M4A1_Metal`. Names are split on `_`, `-`, spaces, case changes and
letter/digit changes (`[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+`); each deny term is tokenised the same way
(`m4` -> `m`,`4`; `desert eagle` -> `desert`,`eagle`) and hits only as a run of whole consecutive tokens. Prototype
and negative tests: `WorkFiles/studies/guns/repo_audit/deny_tokens_test.py` (run, exit 0): `SM_AK47`, `T_UMP45_BC`,
`SK_M4A1`, `SM_AR15`, `SM_AR-15`, `SK_Glock17`, `T_DesertEagle_BC`, `SM_AWM01` hit; `Bump`, `Pump`, `SM_Mag_Break`,
`SupportHand`, `MagDraw`, `Sigil` and every line code (`SM_AR01`, `SK_SMG01`, `SM_HP01`...) pass. **Scope: asset,
object, material, texture, bone and socket names, plus the shipped README and listing text through the same
tokeniser**; studies and plans are not scanned (they name the style references on purpose), and fastener sizes are
written "4 mm thread", never "M4". The list covers the six sheets and the backlog: `ak akm ak47 ak74 kalashnikov rpk
pkm svd dragunov m4 m4a1 m16 ar15 armalite colt m249 minimi m60 ump mp5 mp7 hk heckler koch fn scar p90 uzi galil
famas steyr aug glock beretta sig sauer desert eagle deagle magnum research mossberg remington benelli barrett awm
accuracy international magpul mlok` (common words such as "saw" are left out: they would hit real part names).

### 4.10 Traps found in the repo [M]

1. `qa_skeletal` requires UV0 strictly inside 0..1 (kills the katana's u 1..2 slot trick on the SK).
2. `qa_skeletal` wants triangles before QA (the static path triangulates at export).
3. The `export_fbx` CLI with `--kind skeletal` writes metres (root scale 100 in Unreal). Guns always use
   `export_skeletal_set`.
4. The `qa_check` deny list matches `awm` as a substring and holds no gun trademarks; gunlib carries its own list.
5. `katana_spec.py` and several pipeline tests hardcode the main-checkout root; a copied script would write into the
   main checkout from a worktree. Derive the root from `__file__`.
6. `Scripts/showcase/studio.py` and `FAB_PUBLISHING_STUDY.md` exist only in the cardshop worktree.
7. The Unreal project `ShurikenValidation` is untracked and only in the main checkout (Q17).
8. `np_skeletal` is reachable only through the pack build; its functions are reusable from a gun harness.
9. The fan's clips needed `DefaultRecorderBoneCompression` (ACL cracked rigid parts by ~1.1 mm).
10. **`qa_check` tests UV0 overlap across the whole mesh, whatever the material** (`_uv_checks` always runs
    `_overlap_checks` -> `uv_no_overlap`), and its default tile range is -1..2 (three U tiles). A static twin with
    two or three slots stacked in 0..1 fails. Hence slot k on tile k on the SM copy, at most 3 slots on `SM_<Code>`,
    and no mirrored or stacked islands (the +1 U mirrored-shell convention would compete for the same tiles). The SK
    keeps 0..1 (`qa_skeletal` checks containment, not overlap). The katana put its grip atlas on u 1..2 so that "the two never overlap in UV0" (`katana_uvpack.py`).
11. **`qa_check` fails coincident vertices across the joined mesh** (`no_coincident_vertices`, 1e-6 m). Butted parts
    from shared outlines trip it on the twin only; `qa_skeletal` has no such test. Rule in 3.7; run B6a from stage 3.
12. **Unreal's Generate Lightmap UVs overwrites the authored UV1** (source index 0, destination 1: the katana import
    set exactly this, `kuc_pass1_import.py`). The gate is on the generated channel (5.8, U8).
13. **`qa_check`'s `ea` rule does not do what its comment says:** `(?<![A-Za-z0-9])ea(?![a-z])` is compiled with
    `re.IGNORECASE`, so the lookahead also rejects capitals and `SM_EaBlade` does not hit (`deny_tokens_test.py`
    prints it). Pipeline is out of this study's scope: flag for the pipeline owner; do not copy that pattern.

---

## 5. Standards shared by the whole line

### 5.1 Frame, axes, origin

- Blender metres, modelled in mm, unit scale 1. **+X = muzzle (bore exactly parallel to X, at Y = 0), +Z = up,
  -Y = the gun's right side.** Through the house FBX axes and `ue_component_transform` (Unreal = x, -y, z) it lands as
  **Unreal +X forward, +Y right, +Z up** [M mapping, J choice; first-gun round trip in U1].
- **Origin = `Grip`:** on the grip's centre axis in the Y = 0 plane, 40 mm down that axis from the grip/receiver
  junction (the web line; pistols: from the tang), axes = weapon axes. One hand pose then fits a class [J].
  **The 40 mm is provisional:** gate H1 (7.2) puts the AR-01 in `MH_PlayerDefault`'s hands and the measured palm
  centre replaces it in `gun_standard.json` before the SMG inherits it. The resulting per-gun hand offset (the
  `weapon_r` -> `Grip` transform) is recorded in the sidecar (`hand_offset`) for the game's weapon data. The pistol's
  grip angle differs; its class gets its own H1 pose.
- Blender front view (from -Y) shows the right side, muzzle to screen right.

### 5.2 Bone table (lowercase snake, no dots, every bone deforms; missing bones omitted, never dummies)

```
root                         armature OBJECT = Unreal root bone, identity, at Grip (no bone is called root)
  body                       every fixed part; the physics body
    trigger  hammer  selector  mag_release  bolt_catch  slide_stop
    bolt                     carrier / bolt group (AK: with its charging handle)
    charging_handle          AR / SMG separate handle
    slide                    pistol
      barrel                 tilting-barrel pistols only
      selector               (re-parented here when the safety rides the slide)
    dust_cover               hinged port door
    magazine                 attach bone for SM_<Code>_Mag; no weighted vertices
    muzzle_device            the brake / hider; hidden when a suppressor mounts
    stock                    fold or collapse
      stock_ext  cheek_riser
    sight_front  sight_rear  folding / leaf sights
    bipod
      bipod_leg_l  bipod_leg_r  (+ _ext)
    pump                     shotgun
```

- A bone's parent is the part it physically rides on. **Rest rotation = root's**, so "bolt back" is -X and a selector
  turns about X on every gun; hinge bones put their head on the hinge axis; the `magazine` bone's head is the mag's
  seating pivot (5.6).
- One skeleton asset per gun (bolt travel and hinges differ) [E9][J]. **Common bone names alone do not share an
  Animation Blueprint:** an AnimBP targets one skeleton, and weapon clips `A_<Code>_*` stay per gun. Mechanism chosen:
  **Compatible Skeletons per class** (Epic: compatible skeletons share sequences, montages and Animation Blueprints
  [E52]). One procedural `ABP_Gun_<Class>` is authored on the class pilot's skeleton (long guns: `SK_AR01_Skeleton`;
  pistols: `SK_HP01_Skeleton`) and every later gun of that class lists the pilot as compatible; a node naming a bone
  the gun lacks is expected to do nothing [J, checked in U2b]. Rejected as the main path: a Template Animation Blueprint, because bone-reference nodes
  (Transform Modify Bone on `bolt`) do not belong in a skeleton-agnostic template [E53]; it may still hold
  bone-free logic with per-class linked layers. Proven by U2b (7.4).
- Typical counts: rifle 8, SMG 10-11, carbine 12, pistol 8-9, sniper 10-12.
- If the user adopts a bought animation pack (Q1), map its bone names in a retarget table rather than renaming ours.

### 5.3 Socket table (PascalCase; on bones in the skeletal sidecar, Empties + `.sockets.json` on the statics)

| Socket | Bone | Place and axes | Used by |
|---|---|---|---|
| `Grip` | body | the origin, weapon axes | attach to the character's `weapon_r` |
| `SupportHand` | body (foregrip: overridden) | off-hand palm centre: handguard (long guns), magwell (SMG), support wrap (pistol); +X along the bore | two-bone IK target for `hand_l` |
| `Muzzle` | muzzle_device (pistol: slide) | bore exit, +X out of the bore | flash, smoke, tracer visual |
| `MuzzleSeat` | body | barrel shoulder where devices seat, +X forward | suppressor / device mount |
| `ShellEject` | bolt or body (pistol: slide) | port centre, +X = throw direction | casing spawn |
| `Sight` | sight_rear or body | on the sight line at the rear notch/aperture, +X toward the front sight | ADS alignment; the eye point is game data (eye relief along -X); an optic's own `Sight` overrides |
| `Mag` | magazine | the mag's origin frame when seated (5.6) | attach `SM_<Code>_Mag` with zero relative transform |
| `MagInsertStart`, `MagRockStart` | body | reload path frames (rock-in mags: both; straight mags: `MagInsertStart` only) | lerp/slerp insertion |
| `Rail_Top`, `Rail_Bottom`, `Rail_Left`, `Rail_Right` | body | centre of slot 0 (rearmost) on the rail-top plane, +X along the slots, +Z out of the rail | attachments (5.4) |
| `Stock` | body | stock interface (tube end or hinge face) | modular stocks |
| `SlingFront`, `SlingRear` | body | swivel / QD centres | sling, back carry |
| `Holster` | body | point the gun hangs from when stowed | stowed weapon |
| `Shoulder` | body / stock | butt-plate centre, +X = plate normal reversed | TP aim offsets |
| `CenterOfMass` | body | computed | physics CoM offset (README tells buyers) |
| optional `Trigger`, `Selector`, `MagRelease`, `ChargingHandle`, `Laser`, `Light` | their bones | finger / hand targets, fixed mounts | procedural hand IK |

On `SM_<Code>_Mag`: `Mag` (= origin), `HandReload` (left palm on the body), `Feed` (top of the lips), `Base`
(floor plate, impact FX), `CenterOfMass`. On attachments: `Mount` plus overrides (`Sight`, `Muzzle`, `SupportHand`).

### 5.4 Rail and attachment interface

| Dimension (MIL-STD-1913 profile) [E41] | Value |
|---|---|
| Width across the dovetail | 21.2 mm |
| Flank angle | 45 deg |
| Slot width | 5.23-5.26 mm, square bottoms |
| Slot pitch | **10.01 mm** |
| Slot depth | 3.00 mm |
| Rail height (not standardised) | ~9.5 mm |

- `rail_1913(n_slots, pad)` in gunlib, crisp 0.3-0.5 mm bevels; every rail on every gun comes from it, so every
  attachment fits every rail by construction. The sidecar records `rail_slots` per rail.
- **Attachment snap:** the attachment's `Mount` sits at its recoil-lug centre on the rail-top plane; on a gun it goes
  to `Rail_X + k x 10.01 mm` along +X, integer k only.
- Slotted handguards (carbine): an original slot pattern, short 1913 sections mount on it; never call it M-LOK
  (Magpul trademark [E42]).
- Attachments use the same masters and instances so one skin covers the assembly; scope glass is its own slot
  (opaque glossy lens until a lens material exists, Q19; Nanite allows only opaque/masked [E3]).

### 5.5 Muzzle interface

Every muzzle device is a separate part on `muzzle_device`. **One universal suppressor** with a 35-45 mm rear collar
replaces any device at `MuzzleSeat` (hide the device bone), carrying its own `Muzzle`. Real thread classes (14x1 LH,
1/2-28, 5/8-24 [E43]) are kept only as `muzzle_class` data (Q10).

### 5.6 Magazine interface

- **Origin = the seating pivot; +X forward, +Z = out of the well along the final insertion direction.** Straight-insert
  mags (AR, SMG, pistol, sniper): the centre of the well-entry opening; insertion along -Z from `MagInsertStart`.
  Rock-in mags (AK family): the front-lug hook point; path `MagInsertStart` -> (lerp) -> `MagRockStart` -> (slerp,
  pure rotation about the lug) -> `Mag` (rifle plan 2.3, adopted).
- `SM_<Code>_Mag`: LOD0-3, one UCX hull per straight mag (two for a curved mag: one hull fills the curve's sagitta),
  top round modelled if the sheet shows it; optional `Round_NN` sockets.
- Extended and drum mags keep the origin and frame and grow downward.
- Mag LOD screen sizes are **derived** from the gun's: size_mag = size_gun x r_mag / r_gun (measured bounds), so both
  switch at the same distance.

### 5.7 Budgets

| Gun | LOD0 target (ceiling) | LOD1 | LOD2 | LOD3 (BR) | Mag LOD0 |
|---|---|---|---|---|---|
| Rifle, carbine, long rifle | 30-45k (50k) | ~45 % | ~15 % | 1.5-2.5k | 2-5k (7k) |
| SMG | 25-40k (50k) | ~45 % | ~15 % | 1.2-2k | 2-4k |
| Sniper without scope (scope is an attachment) | 35-45k (50k) | ~45 % | ~15 % | 2-3k | 2-3k |
| Pistol | 15-25k (30k) | ~45 % | ~15 % | 0.8-1.2k | 1-2k |
| Attachment (optic, suppressor) | 3-10k | ~45 % | ~15 % | - | - |

LOD0 cost is bevel rings first (~10-15k on a rifle), then rounds (32-48 sides), then fasteners. LOD1 halves segments;
LOD2 drops bevels under ~2 px at its switch distance and replaces fastener groups and checkered panels by ray-cast
shells; LOD3 is the silhouette hull per part group. **Screen sizes are measured** (start: 1.0 / 0.30 / 0.12 / 0.04 for
a ~0.45 m bounding radius; house default 1.0 / 0.5 / 0.25 would put your own TP rifle on LOD2 at 3 m [M rifle plan]).

### 5.8 Texel density and texture sets

**Derivation.** On-screen px per cm of surface = W / (2 d tan(HFOV/2)) for a surface d cm from the eye. The camera
standard lives in `gun_standard.json` (`camera`: target 2560 x 1440, hip FP HFOV 70 deg, ADS FP HFOV 55 deg, eye
relief 0.25 m behind `Sight` in ADS, eye-to-part distances per class) and the class targets are computed from it, so
a game FOV change re-derives them [J defaults; the game sets the real FOVs]. A and B are governed by the ADS view,
where the FOV narrows and the rear of the gun sits 0.15-0.35 m from the eye (rev 1 used the hip view only and came
out up to 2x short; review R6). 4K buyers need x1.5 (Fab 4096 option, Q13).

| Class | Surfaces | Governing case | Target px/cm |
|---|---|---|---|
| A, ADS | rear sight leaf and notch, optic eyepiece, front post and hood | ADS 55 deg at 0.20-0.25 m (~98 at 0.25 m) | **80-100** |
| B, FP rear | rear receiver, dust cover, selector, charging handle, grip top, comb | ADS 55 deg at 0.30-0.35 m (70-82); hip 70 deg at 0.30 m (61) | **60-80** |
| C, FP mid | mag, magwell, trigger guard, handguards, front receiver | hip 70 deg at 0.45-0.60 m (41-30) | 30-40 |
| D, front | gas block, front sight base, barrel, brake | hip 70 deg at 0.60-0.75 m (30-24) | 25-30 |
| E, hidden | undersides, insides, contact faces (reload-visible insides at the low end, never-visible deleted) | - | 8-15 |

- The house 10.24 px/cm is a floor, not a target, for FP guns [M ASSET_GUIDELINES, katana shipped 54.8].
- **Sets:** Metal and Furniture on the gun, one on the mag; a pistol may need only one or two; attachments own their
  sets. Fill >= 70 % (metal) / 65 %. **Each set is the smallest power of two that reaches its classes at that fill**
  (the packer reports it). Rough AR01 estimate: Metal needs ~1.9 M texels (class A ~30 cm2, B ~200 cm2, C ~200 cm2,
  D ~400 cm2) against ~2.9 M usable at 2048 and 70 % fill, so 2048 probably holds; if it does not, Metal goes to 4096
  (the rifle plan's figure) [J, rough areas]. The painter is procedural, so 4096 costs bake time and memory, not
  labour. ASSET_GUIDELINES 3 says "4096 for hero": a 2048 hero set that meets the derived classes is a recorded
  deviation (proposed dated amendment, section 12).
- **UV0, skeletal vs static** [M qa code, review R1]: the SK keeps every slot's islands in 0..1 (`qa_skeletal`
  requires containment and has no overlap test; slots overlap across materials). **The SM copy always moves slot k
  to U tile k** (Metal 0, Furniture 1, merged mag or third slot -1), because `qa_check` tests UV0 overlap over the
  whole mesh whatever the material; wrap sampling makes the textures read the same. `qa_check`'s default tile range
  -1..2 holds three tiles, so **at most 3 slots on `SM_<Code>`** including a merged mag. **No stacked or mirrored
  islands within a slot, anywhere** (unique texels: AO and wear differ left to right anyway), so the +1 U
  mirrored-shell convention is unused on guns. This is an exception to ASSET_GUIDELINES 4 ("UV0: non-overlapping
  islands") for skeletal meshes only (proposed amendment, section 12).
- **UV1 (lightmap), one method** [M]: Unreal generates it at import (Generate Lightmap UVs on, source 0, destination
  1, the house practice on the shuriken and katana; it overwrites any authored UV1) and **U8 gates the generated
  channel** (inside 0..1, 0 overlap, lightmap index 1). The packer still writes a UV1 so `qa_check --require-uv1`
  passes and a buyer who turns generation off has a valid channel; it is a fallback, not the gate. With Allow Static
  Lighting off (Q5) the game never uses lightmaps; UV1 exists for Fab's static-mesh rule.
- No UDIM (virtual texturing dependency), no trim sheets (our painter makes unique texels free; reuse is at module
  level). Power-of-two, full mips; ~35 MB for three sets, ~60 MB with masks and two Detail16, streamed [J].
- `qa_check --texel` grades an average; the builder reports per class and the qa target is the measured aggregate
  +-25 % (katana precedent).

### 5.9 Material slots and masters (additions only; masters unchanged)

| Slot | Master | Carries |
|---|---|---|
| `M_<Code>_Metal` | `M_Fabric_Master`, **Metal From ORM on** | coated metal (recolourable) with bare wear and small bare parts keeping their baked colour |
| `M_<Code>_Furniture` | `M_Fabric_Master`, Metal From ORM off (no metal in this slot) | wood, polymer, rubber |
| `M_<Code>_Mag` (on the mag mesh) | as the mag's finish (coated: Fabric + MFO; polymer: Fabric) | the magazine |
| `M_<Code>_Steel` (only when a slot is all bare metal, e.g. pistol stainless) | `M_Steel_Master` (Steel Tint) | bare/blued/stainless |

- At most 3 slots per mesh (draw calls multiply in BR loot; also the `qa_check` tile limit on the twin, 5.8). The
  held gun costs 2 components per mesh (2.3): rifle 6 draws, <= 10 with two attachments.
- **The brightness trap:** with Metal From ORM on, `M_Fabric_Master` freezes texels brighter than linear luminance
  ~0.2-0.4 (the fan's pearl rule). Dark finishes (walnut, black lacquer, black polymer, OD) are safe. Light birch, tan
  or FDE need metal out of that slot or `M_Weapon_Master` [M].
- Pack integration copies the katana's `changes_v8_katana` pattern: `maps/derive_constants_<code>.py`, recolour maps,
  item + instance entries, PackMaterials lock, `run_build.sh`.

### 5.10 Colour and skin system

- **Ship `T_<Code>_Masks` from the first build** (linear RGBA, TC_MASKS): R edge-wear propensity, G handling and
  contact, B cavity grime, A refinishable region (1 = coating or paintable furniture; 0 = bare metal, rubber, glass,
  sights). The shipped BC/ORM are the default-wear look, correct on today's masters.
- **`M_Weapon_Master` later** (new master, Q8): coating recolour via the pack's `MF_TintDetail`, a **Wear Amount**
  slider thresholding R+G (CS:GO wear bands [E39]), tileable camo, grime from B. Camo by triplanar on the pre-skinned
  local position (density classes make UV camo misalign; [J, unverified 5.8]).
- **Skin tiers** (Q9): colour variants = one MIC each, no textures; camo = one MIC + one shared 1024 tileable pattern;
  unique painted skins = a full BC/ORM set each, rare. Skins are Primary Data Assets with soft references; only the
  skin ID replicates [M ASSET_GUIDELINES]. APB and Fab packs ship this model [E40][E10].

---

## 6. Unreal setup and verification

### 6.1 Import

- **`SK_<Code>`**: the fan path, `np_skeletal` functions called from the gun harness. Legacy `FbxFactory`, import
  normals, convert scene and unit, Force Front X off, `use_t0_as_ref_pose` off, no morphs, no auto physics; LOD1+ via
  `SkeletalMeshEditorSubsystem.import_lod`; LOD screen sizes through a `SkeletalMeshLODSettings` asset; bounds
  extension from the sidecar; sockets made relative to each bone's ref pose (`SkeletalMeshSocket`, outer = mesh, scale
  1); `PHYS_<Code>` from the proxy FBX then rewritten from the sidecar; clips at their own rate with
  `DefaultRecorderBoneCompression`; Nanite off [M].
- **`SM_<Code>`, `SM_<Code>_Mag`**: legacy importer, Convert Scene on, Force Front X off, Import Normals + MikkTSpace,
  Auto Generate Collision off, One Convex Hull per UCX on, Import Mesh LODs on, Generate Lightmap UVs on (source 0,
  destination 1: replaces the authored UV1, which is only the fallback, 5.8), Nanite off; then `ue_import_sockets.py`
  with the sidecar (FBX sockets arrive at scale 100) [M rifle plan 10.2].
- Textures: BC sRGB, ORM linear TC_Masks, N TC_Normalmap (flip green off, DirectX on disk), Masks TC_Masks, Detail16
  G16 linear; full mip chains.
- **Texture LOD groups:** the gun's and mag's BC, ORM and Masks in `TEXTUREGROUP_Weapon`, N in
  `TEXTUREGROUP_WeaponNormalMap` (5.8 `TextureDefines.h:36-37`), so buyers' scalability and device profiles can treat
  weapon maps on their own; on Windows the engine defaults equal World's (`BaseDeviceProfiles.ini`: MaxLODSize 16384,
  LODBias 0) so nothing changes by default [M]. Shared Detail16 maps stay World. The streamer sizes mips from
  bounds and distance, which the FP scale changes, so U12 checks the resident mip in the FP pawn.
- Pack integration (material instances, recolour) only through the shared materials build under the lock.

### 6.2 Game-side pattern (documented in the README; built in the game project only on the user's go)

- **Weapon Blueprint:** `FP_Weapon` + `TP_Weapon` skeletal components on the same `SK_<Code>`, plus `FP_Mag` +
  `TP_Mag` (`SM_<Code>_Mag` on each weapon component's `Mag` socket) and `FP_<Att>` + `TP_<Att>` per attachment; every
  FP component `FirstPerson` with `ForcedLodModel = 1`, every TP component `WorldSpaceRepresentation` (2.3); muzzle
  visuals from the matching component; gameplay traces from the camera; `Transform World to First Person` when a
  visual must line up [E1][E2].
- **Hand attach:** a `weapon_r` socket on the MetaHuman `hand_r` (Lyra's name [E7]); `Grip` snaps to it with the
  per-gun offset from the weapon data asset; the off hand solves two-bone IK to `SupportHand` expressed in `hand_r`
  space [E19]. Our MetaHuman has no `ik_*` bones [M], so `ik_hand_gun` style rigs are a character decision (Q4).
- **Physics:** `PHYS_<Code>` one body on `body`, kinematic/query-only while held, simulate when dropped; ground loot is
  `SM_<Code>` on its hulls; a seated mag has collision off; a dropped mag uses its hull and mass.
- **Reload patterns (both supported by the asset):** (1) the `magazine` bone rides a weapon clip, a physics copy spawns
  at the `MagDrop` notify; (2) hand swap: detach to a `Mag_L` socket on `hand_l` at the `MagOut` notify, re-attach
  along the path at `MagIn` [E9][J]. Notify names, clips and frames come from the skeletal sidecar (4.6); pattern 2's
  notifies sit on the character montage. Pattern 2 is the game default (works with any character montage); pattern 1
  clips ship for Fab.
- **Procedural parts:** Transform Modify Bone on `bolt` (-X) for recoil kick, selector about X, trigger pull, in one
  `ABP_Gun_<Class>` shared through Compatible Skeletons (5.2).
- **Casings:** generic meshes per calibre class (intermediate rifle, full-power rifle, pistol), no headstamps.

### 6.3 Verification harness

`WorkFiles/guns/<role>/UnrealCheck/`, adapted from `WorkFiles/fan/UnrealCheck/` (run guard: refuse to start when
another `UnrealEditor-Cmd` runs, kill only its own leftover) and the katana's independent verify. Pass 1 imports
everything in one process; pass 2 reloads in a **fresh process** with a real RHI and asserts; sha256 of the bytes at
start and end. One commandlet on the machine at a time; never left running. Content path `/Game/GunCheck/<Code>_<run>`
in `ShurikenValidation` until Q17 decides otherwise.

---

## 7. Gates with numbers (copy into each gun's spec)

### 7.1 Spec

| # | Gate |
|---|---|
| S0 | the spec validator (`standard.py`) reports **0 missing or null fields**: every part has process, bevel class, texel class, set, authority view, pivot/motion/limits, bone, parent, joint type (3.7), fastener sources; 0 unresolved nominal numbers; real dimensions from 3.5 within +-5 %; camera block present (5.8) |

### 7.2 Blender, on built and exported bytes

| # | Gate | Threshold |
|---|---|---|
| B1 | Skeleton | object `root` at identity; names only from 5.2; every bone deforms; unweighted `magazine` survives the FBX; rest rotations = root's |
| B2 | Rigid skin | `qa_skeletal(max_influences=1)` passes: exactly one influence at 1.0 |
| B3 | Motion clearance | sweep every bone through its range; translation step <= half the joint's minimum clearance (and <= 1 mm), rotation step **min(1 deg, c_min / r_max)** (c_min = the row's lower bound, r_max = the part's largest radius from the pivot; 0.1 mm at 50 mm = 0.11 deg). LOD0-LOD1: **0 intersections** and every joint inside its 3.7 row at rest and over the sweep. LOD2-LOD3: penetration depth, projected at that LOD's switch distance, < 1 px at 1440p |
| B4 | Sockets | all 5.3 sockets the gun needs present on the right bones; `Muzzle` on the bore axis <= 0.5 mm and <= 0.05 deg; sight picture: camera at the `gun_standard` ADS FOV (55 deg) and eye relief (0.25 m behind `Sight` along -X), 2560 x 1440, front post centred in the rear notch/aperture within 0.5 px |
| B5 | Sidecar | exported socket transforms = build values within 0.001 mm / 0.001 deg |
| B6 | Static twin | `qa_check` passes on the exported SM bytes: UCX keyed to the node name, UV0 tile range -1..2 with slot k on tile k and `uv_no_overlap` 0, `no_coincident_vertices` 0, UV1, LOD triangles strictly descending, `--budget` = the 5.7 ceiling |
| B6a | Twin topology, early | from stage 3 on, every build joins the parts as the twin would and runs `qa_check` topology + UV checks on it (0 coincident vertices, 0 non-manifold, 0 UV0 overlaps once UVs exist), so 3.7 violations surface at form, not at export |
| B7 | Geometry | closed manifold parts; flat-face normal deviation < 1 deg; facet angle <= 7.5 deg at LOD0; bevel widths = spec +-0.05 mm and >= the visibility minimum |
| B8 | Budgets / LOD | LOD0 within target and <= ceiling; LOD1-3 per 5.7; LOD-pop: mean silhouette difference <= 1 px, max <= 3 px at each switch (2560 x 1440, 4 headings) |
| B9 | Textures | power-of-two, full mips; each texel class within +-15 % of target; fill >= 70 / 65 %; metallic exactly 0/1; dielectric BC sRGB 30-243 (below 50 only for the declared black finishes); metal BC >= sRGB 110 (bluing) / >= 186 (bare) |
| B10 | Names | tokenised gun deny list (4.9; its negative tests pass) and `qa_check` deny list clean on every name and on the shipped README/listing text; no text in any map |
| H1 | Hand fit (first gun of each class; re-run when the grip, trigger or `SupportHand` moves) | In Blender, on the locked `References/Characters/MH_PlayerDefault/` fit body and its `metahuman_base_skel` (confirmed in Unreal by U11): `SK_<Code>` attached at a `weapon_r` frame on `hand_r` with the class grip pose (finger rotations stored in `gun_standard.json`). Palm-to-grip penetration **<= 1 mm**; index fingertip reaches the trigger face within **+-3 mm** of the rest curl; two-bone IK of `hand_l` to `SupportHand` converges (< 0.5 mm residual) with the elbow and wrist inside the skeleton's limits; **0 hand-gun intersections** at rest and at every clip's extremes (bolt back, stock folded/collapsed, mag out). Records `hand_offset` in the sidecar; the AR-01 result replaces the provisional 40 mm (5.1) |
| M1 | Mag seated | 0 intersecting triangles for the gun/mag LOD pairs that appear together (mag sizes are derived to switch with the gun's: pairs (k, k), plus (k, k+-1) for rounding at the switch); LOD0-LOD1 pairs 0 intersections, LOD2-LOD3 pairs under the B3 1 px rule |
| M2 | Seat | top-stop gap 0.1-0.5 mm (3.7 seated-mag row); visible seam <= 0.6 mm |
| M3 | Clearances | 3.7 seated-mag row: lateral 0.2-0.6 mm per side; lug in recess 0.1-0.4 mm |
| M4 | Insertion and removal paths | 0 intersections in 0.5 mm / 0.25 deg steps; rock-in only: declared catch allowance <= 3.0 mm in the last <= 6 deg |
| M5 | Fit inputs | gun bytes = the shipped sha256; sockets from the exported sidecar |

### 7.3 Look

| # | Gate | Threshold |
|---|---|---|
| L1 | Blockout IoU (authority view) | >= 0.95 sides, >= 0.92 top; **< 0.90 = stop and change the method** |
| L2 | Form IoU | authority view >= 0.96 sides, >= 0.93 top; each part on its authority view >= 0.95; non-authority whole view >= the sheet's own self-IoU there - 0.01 (rifle ~0.88) |
| L3 | Contour and features | P95 contour distance <= 2 sheet px; feature positions <= 2 sheet px (side views) or 1 mm on close-ups; angles <= 1 deg |
| L4 | Dimensions | measured vs spec <= 0.05 mm (same numbers drive both; larger = a bug) |
| L5 | Colour | crop-matched hue, R/B and median luma within the stone S16 tolerances (STONE_BUILDING_STUDY section 6) |
| L6 | Fake checklist | G1-G20 reviewed with evidence images; 0 major |
| L7 | Blind tests | design judge on >= 12 image pairs (sheet crop vs our render, matched camera, light, scale): correct picks <= 8/12 (or <= 12/20), and no confident design tell; realism judge (2 independent judges) on 4 views (FP crop at 35 cm, ADS, TP at 3 m, hero 3/4): at most 1 of 4 views called fake, by at most 1 judge, and that call gets a fix or a written justification; any view both judges call fake fails. Stop and show the user if the first 4 pairs are all picked for a design reason |

### 7.4 Unreal (fresh process, exact bytes)

| # | Gate |
|---|---|
| U1 | Skeleton dump: names, parents, ref poses; muzzle +X, up +Z, right +Y; root scale 1 |
| U2 | Procedural: Transform Modify Bone `bolt` -X moves straight back; selector turns about X |
| U2b | Shared AnimBP: the same `ABP_Gun_<Class>` drives the bolts of two different guns of the class (from the second gun of a class on; the SMG for long guns) through Compatible Skeletons; each bolt moves straight back by the commanded amount within 0.01 cm; a bone missing on one gun raises no error |
| U3 | Sockets from the sidecar on the right bones at scale 1, within 0.001 cm / 0.001 deg; no extras |
| U4 | FP + WSR test pawn with VSM, full component set (gun, mag, one attachment, each FP + TP): FP components cast no ground shadow and render at LOD0 (`ForcedLodModel = 1`), TP components cast it, owner sees no TP component; the mag and the attachment follow the same rules as the gun |
| U5 | LOD count and triangles equal Blender/FBX/Unreal; screen sizes and bounds extension applied; the stored bounds contain **every vertex at every frame of every clip** (0 outside, sampled at clip rate) |
| U6 | Mag composition: `SM_<Code>_Mag` at `Mag` lands on the sidecar transform within 0.001 cm, at rest and at sampled reload frames; seated fit on read-back geometry |
| U7 | Physics: `PHYS_<Code>` simulates and rests; `SM_<Code>` dropped from 1 m rests on its hulls, no tunnelling; 0 of 300k LOD0 samples outside the stored hulls |
| U8 | Statics: lightmap index 1 on every LOD; the **generated** UV1 inside 0..1 with overlap 0 (shuriken method); texture flags and LOD groups persisted; full mips (13 levels at 4096, 12 at 2048) |
| U9 | Clips: lengths, engine-evaluated end poses equal rest; rigid-part compression error <= 0.1 mm; **every sidecar notify present on its clip at its frame** (+-0.5 frame), no extra notifies |
| U10 | 0 warnings or errors from the assets; same sha256 everywhere; report promoted to "engine-verified" only on matching bytes |
| U11 | Hand fit in engine: `SK_<Code>` on a `weapon_r` socket of `MH_PlayerDefault`'s `hand_r` with the sidecar `hand_offset`, class grip pose: H1's penetration, trigger-reach and IK numbers reproduce within 1 mm |
| U12 | Texture residency: in the FP test pawn at hip and at ADS, the resident mip of the gun's BC and N is the top mip (mip 0) after streaming settles |

### 7.5 Pack materials (under the lock)

| # | Gate |
|---|---|
| P1 | default capture = shipped BC (p99.9 <= 2 levels) |
| P2 | 10-colour stress per recolourable slot incl. `FFFFFF FF0000 0000FF F2E8D5 000000` |
| P3 | mip drift <= 2 % |
| P4 | dump comparison: every other pack entry unchanged (additions only) |

---

## 8. Per-gun notes

| Code | Sheet facts [M] | Bones | Special parts | Shares | Finishes |
|---|---|---|---|---|---|
| AR01 | L, R, top, 3/4 + 7 close-ups; LEFT/RIGHT labels swapped; ruler mislabelled; self-IoU ~0.89 (grip angle, mag rake) | body, bolt, trigger, selector, mag_release, magazine, sight_rear, muzzle_device | rock-in curved mag; 1 mm stamped receiver; slant brake with cut port; checkered grip panels (class B); cleaning rod | curved-box mag generator; hardware | black lacquer over steel; walnut shellac |
| SMG01 | Sheet A only (Sheet B refused: keep unseen details plain); labels consistent; ruler +26 % | body, bolt (if visible), charging_handle, trigger, selector, mag_release, magazine, stock, sight_front/rear (if flip), muzzle_device | side-folding skeleton stock (hinge part, revealed hinge inside, bounds extension for both states); top + bottom 1913 rails; straight stick mag | rail, flip sights (with CB01), mag_box generator | black polymer (polishes, stipple 0.75-0.90); phosphated steel |
| CB01 | no labels; ruler +16 %; flip sights up; stock half out | body, bolt, charging_handle, dust_cover, bolt_catch, trigger, selector, mag_release, magazine, stock, sight_front, sight_rear, muzzle_device | collapsible stock (`stock` translate, positions as data); original slotted handguard; flat-top rail | **defines** black-rifle parts A-D (lower, upper core, trigger group, curved 30 mag) with LR01 | anodized aluminium (bright silver wear); polymer |
| LR01 | ruler +16-17 %; magazine scale disagrees with CB01's by ~13 % | as CB01 minus stock and flip sights | carry handle as a separate part on the shared upper core; round ribbed handguard (ribs geometry); triangle front sight tower; fixed stock; sling loops | ~half its parts from CB01 | as CB01 |
| SR01 | no ruler; labels swapped (bolt handle in LEFT); bipod folded in the side views, deployed in the 3/4 | body, bolt (rotate then slide), trigger, selector, mag_release, magazine, bipod, bipod_leg_l/_r (+_ext), cheek_riser (opt.), muzzle_device | fluted barrel (flutes geometry); detachable box mag; **scope = `SM_Att_Scope_*` on the top rail** with its own `Sight` and lens slot; folded pose authority = side views, deployed pose checked against the 3/4 | rail, mag_box generator | OD Cerakote over aluminium; rubber pad |
| HP01 | views consistent; ~2.1 px/mm (tighter: 2 px = ~1 mm); ruler +9 % | body, slide, hammer, trigger, selector (on `slide`), slide_stop, mag_release, magazine | slide serrations geometry; short top rail on the barrel; flush grip mag (base plate visible); grip envelope outside the long-gun hand pose (pistol class anim set) | rail, mag_box generator | brushed stainless (`M_Steel_Master`); pebbled rubber grip |

**Build order** [J]: AR01 (rig pilot) -> SMG01 (automatic after the rifle, user 2026-10-04) -> CB01 (defines the
black-rifle shared parts) -> LR01 -> HP01 -> SR01. The pistol may move earlier if the duel MVP wants a sidearm; every
gun after the SMG waits for the user's say (memory `stop-before-expensive-work`).

**Backlog fit:** pump shotgun (`pump`, `SupportHand` on the pump bone), DMR (AK family modules), second SMG
(`mag_box`, rail), LMG (curved/box mags or belt, `feed_cover`, bipod), crossbow (`string`, limbs; not a firearm on
Fab), attachments kit (red dot, 4x, suppressor, grip, extended mag) all on 5.3-5.6.

---

## 9. IP and Fab notes

- **Names:** generic product names and codes only (4.8). Never AK, AKM, Kalashnikov, M4, M4A1, M16, AR-15, ArmaLite,
  Colt, UMP, Heckler & Koch, Desert Eagle, Magnum Research, AWM, Accuracy International, Glock, Barrett, Remington,
  M-LOK or Magpul (nor the backlog's MP5, SCAR, P90, Beretta, SIG, Mossberg, Benelli and the rest of the 4.9 list)
  in any asset name, shipped README, showcase or listing; the tokenised gun deny list (4.9) enforces it on names and
  shipped text. "1913-profile accessory
  rail" is fine (public military specification) [J].
- **No markings:** no logos, stamps, serials, proof marks or numerals; nothing a "removable logo" would cover.
- **Design distance:** the rifle and long-rifle sheets are near-replicas of real designs [M memory]. The game may use
  them as drawn; **Fab versions get original design deltas** applied in the spec (rifle plan 13 lists seven for AR01:
  receiver dimple/rivet layout, sight-leaf profile, ported brake, stock profile, handguard grooves, grip panel
  pattern, mag ribs; an original dust-cover rail is an eighth). The shared-parts spec makes the black-rifle deltas
  cost once for both.
- **Fab's Firearms rule:** at least one asset "with all expected moving parts rigged and a full set of animations"
  [E5]. So the Fab gun pack ships `SK_` + weapon clips, and states poly counts and texture sizes (rarely stated by
  competitors [E10-E17]), the FP project requirements, Blender sources if offered, example Blueprints using the
  sockets, and a compatible skeleton only if we tested it (UE5 Manny is the selling name; UE4-only packs carry
  warnings [E11]). **Open risk:** Epic does not define "a full set of animations" (the Smart Assets wording is only
  "rigged and animated" [E5]), and the listings we cite sell FP arms and character animations with the guns. A
  reviewer may not accept weapon-only clips. Before promising the Firearms category: ask Fab support, or plan a
  minimal arms set (idle, fire, reload, reload empty, equip on the UE5 Manny) for one gun (Q6).
- **Fab release checklist additions:** the example Blueprint and overview map load and render correctly with static
  lighting allowed and with `Config/` deleted (ASSET_GUIDELINES 11 self-test; FP features fall back: shadows and
  reflections simply absent [E1]); the FP project settings (deferred, VSM, Allow Static Lighting off) appear only as
  README instructions, never as a dependency of the example content; "Build lighting" is run on the overview map as
  usual.
- **What top listings sell** [E10-E17]: rigged skeletal guns plus static parts and mags, weapon-side clips (fire,
  reload, safety, bolt), modular parts with counts, several material skins or wear sliders, 4K PBR, sockets with
  example Blueprints, ammo and casings.
- Release process: `FAB_PUBLISHING_STUDY.md` (R0-R8; currently only in the cardshop worktree) and
  `FAB_ASSET_STUDY.md`.

---

## 10. Open decisions for the user

Defaults let the rifle and SMG proceed; the starred ones change the build if answered differently.

| # | Decision | Default (recommended) |
|---|---|---|
| Q1* | Where the character fire/reload/ADS animations come from: bought pack (its bone names), our own, or procedural | our bone standard; procedural in the game; weapon-side clips authored for Fab; a bought pack is mapped by a retarget table |
| Q2* | Rig from AR-01 on, or static first | rig pilot on AR-01 |
| Q3 | Static twin with the mag merged in, or always attached | merged (one mesh for loot and set dressing); `SM_<Code>_Mag` still ships |
| Q4 | Player hand attach: `weapon_r` + two-bone IK, or add `ik_hand_*` bones to the player rig | `weapon_r` + two-bone IK |
| Q5* | Use UE 5.8 First Person rendering (deferred, VSM, Allow Static Lighting off): can `DemoGame_1` drop static lighting? | yes, if the project allows |
| Q6* | Fab: fully animated (required for the Firearms category) or "rigged, animation-ready" in another category; and whether weapon-only clips count as Fab's "full set of animations" (undefined by Epic) | fully animated weapon clips; **ask Fab support before listing**; if the answer is no, add a minimal FP arms set on the UE5 Manny for one gun, or list under Smart Assets ("rigged and animated") |
| Q7* | One shared 1913 rail standard across the line, including a rail on the AK-style rifle | yes; AK rail on the Fab version (dust cover), game version as drawn |
| Q8 | Build `M_Weapon_Master` (wear slider, camo, grime) before the Fab pack and BR skins | yes, after the SMG; masks ship from the first build either way |
| Q9 | Battle-royale skin tiers: colours, camo, unique painted | colours + camo |
| Q10 | One universal suppressor, or per-calibre threads | universal, class kept as data |
| Q11* | When a sheet's views disagree: authority view per part, or regenerate the sheet | per part; ask only for design-level conflicts |
| Q12 | AK left side: real pattern (plain), or the sheet's mirrored selector | real pattern (rifle plan Q2) |
| Q13 | Texture size: classes A/B are now derived from ADS (A 80-100, B 60-80 px/cm), set size = smallest power of two that reaches them; accept, or keep every game set at 2048 with softer ADS detail; and ship 4096 in the Fab pack for 4K buyers | derived classes (2048 where it holds, 4096 where the packer needs it; record a dated amendment to ASSET_GUIDELINES 3 either way); offer 4096 in the Fab pack (compute only) |
| Q14 | Sniper ceiling: the scope is now an attachment; is 50k enough, or a recorded waiver to ~60k | 50k without the scope |
| Q15 | Real scale within +-5 % for every gun (sniper 1.27 m, pistol 27.3 cm, long rifle 1.00 m) | yes |
| Q16 | Wood variants (birch, laminate) and a clean factory wear variant | walnut only for v1; variants after `M_Weapon_Master` |
| Q17 | Unreal checks in the main checkout's untracked `ShurikenValidation`, or a dedicated gun validation project | keep the house practice, new content path per run |
| Q18 | Fab packaging: one gun pack (shared rail, mags) or one product per gun; game guns closer to the real designs than the Fab versions | one pack; game as drawn, Fab with deltas |
| Q19 | Scope lens: opaque glossy on an existing master, or a new glass master | opaque glossy for v1 |
| Q20 | Exports `Exports/Guns/<Code>/`, SMG code `SMG01`, sight-leaf graduations omitted | as proposed |
| Q21 | Game camera for the texel and sight gates: hip FP FOV, ADS FOV, target resolution | 70 deg hip, 55 deg ADS, 2560 x 1440 (in `gun_standard.json`; changing them re-derives classes A/B and B4) |
| Q22 | Approve the two house-document amendments this study needs (section 12): ASSET_GUIDELINES 4 (skeletal UV0 may overlap across slots; SM twins use one U tile per slot) and ASSET_GUIDELINES 3 (gun set size by derived texel class) | approve; the main chat edits ASSET_GUIDELINES |

---

## 11. Impact on the AR-01 rifle build (`WorkFiles/guns/rifle/`)

The rifle plan stays largely valid (frames, the rock-in reload path, hull method, fit gates, LOD-pop gate, Fab deltas).
It must change these items:

1. **Assets:** add `SK_AR01` (+ `_LOD1..3`, `SK_AR01_Skeleton`, `PHYS_AR01`, clips `A_AR01_Fire/_Charge/_Reload/
   _ReloadEmpty/_Selector`) with bones `body, bolt, trigger, selector, mag_release, magazine, sight_rear,
   muzzle_device`. Keep `SM_AR01` as the static twin (mag merged by default, Q3) and `SM_AR01_Mag`. Resolves plan Q1
   as option (c).
2. **Modelling:** every moving part a separate closed solid with pivot, axis and limits in the spec (carrier with
   charging handle, trigger, selector, mag catch, rear sight leaf, brake as `muzzle_device`); the charging-handle slot
   and ejection port cut the full bolt travel; the selector clears its arc; the port interior and bolt face exist.
   Add B3 (motion sweep, LOD0-LOD1 zero intersections, LOD2-LOD3 under 1 px) at stages 3 and 5. **Every joint gets a
   type from the 3.7 clearance table** (the plan's 0.3 mm lateral / 0.2 mm lug mag numbers already sit inside it);
   **butted parts (stock and grip to receiver, handguard to cap, rivets, flush pins) get a 0.01-0.05 mm modelled
   gap**, never shared vertex positions, and B6a (`qa_check` on the joined twin) runs from the form stage.
3. **Rig stage** after the game stage: `root` at `Grip`, rigid bind, triangulate, `qa_skeletal(max_influences=1)`,
   `skeletal_prop.export_skeletal_set`; no welding of parts at build time.
4. **Sockets renamed to 5.3:** `OffHand` -> `SupportHand`, `EjectPort` -> `ShellEject`, `MagWell` -> `Mag` (on the
   `magazine` bone), `ADS` -> `Sight` (on the notch; eye relief becomes game data), `SightFront` dropped (the `Sight`
   X axis carries the line), `SlingFront/SlingRear` kept; add `MuzzleSeat`, `Holster`; keep `MagRockStart`,
   `MagInsertStart`, `Trigger`, `Selector`, `MagRelease`, `ChargingHandle`, `Shoulder`, `CenterOfMass`. Mag sockets:
   `Attach` -> `Mag`.
5. **Materials:** the receiver, dust cover and mag are **black lacquer over steel** (metallic 0, sRGB 45-55, rough
   0.40-0.55) wearing in sharp chips to bare steel (metallic 1, 0.53-0.56, rough 0.25-0.40), not metallic-1 blued
   steel at sRGB 40-55. Slots: `M_AR01_Metal` (`M_Fabric_Master` + Metal From ORM), `M_AR01_Furniture` (Fabric, MFO
   off; was `M_AR01_Wood`), `M_AR01_Mag` (Fabric + MFO). This replaces the `Steel Tint` colour story.
6. **Textures:** steel 4096 -> **Metal set sized by texel class** (A 80-100 for the sight-picture faces, B 60-80 rear
   receiver and dust cover, C-E as 5.8): the packer picks 2048 if it reaches the classes at >= 70 % fill, otherwise
   the plan's 4096 stands (rev 1's "90 px/cm exceeds the need" is withdrawn: the ADS view needs ~98 at the notch;
   the plan's 2x on sight faces was right in spirit). Furniture 2048 and Mag 2048 kept. **UV0: the SK keeps every
   slot in 0..1; the SM copy keeps the plan's tile scheme** (Metal u 0..1, Furniture u 1..2, merged mag u -1..0),
   written by `export_gun`, because `qa_check` tests overlap across materials. No mirrored or stacked islands.
   **UV1:** keep the authored pack as a fallback, but gate on Unreal's generated channel (the plan's own 6.1 import
   regenerates it). Add `T_AR01_Masks` and a Detail16 for the Metal slot as well as the wood. Maps in
   `TEXTUREGROUP_Weapon` / `WeaponNormalMap`.
7. **Budget:** target 30-45k (ceiling 50k; the per-part ~27.5k table is a fine start), mag ceiling 7k kept, and
   **LOD3 now** (~1.5-2.5k rifle, ~200-300 mag) with measured screen sizes.
8. **Layout:** `Scripts/Guns/AR01/` -> `Scripts/guns/rifle/` (root from `__file__`, `parents[3]` still holds),
   `Exports/AR01/` -> `Exports/Guns/AR01/`, `Assets/AR01/` -> `Assets/Guns/AR01.blend`, shared code to
   `Scripts/guns/gunlib/` (not `Scripts/Guns/common/`); materials lock `PackMaterials` via `np_lock.py` for stage 9.
9. **Gates:** add B1-B4 (skeleton, rigid skin, motion sweep, sockets on bones; B4's sight picture at 55 deg ADS FOV
   and 0.25 m eye relief), B6a, **H1** (hand fit on `MH_PlayerDefault`) and U1-U6, U9, U11, U12 (skeleton dump,
   procedural bolt, sockets on bones, FP/WSR with the mag as its own FP + TP pair, bounds containing every clip
   vertex, mag composition, clip compression and notifies, engine hand fit, top-mip residency); M1 only on co-visible
   gun/mag LOD pairs (not all 9); keep the plan's L-gates but set L2's non-authority side to the sheet's self-IoU -
   0.01 (~0.88), not 0.97; blind test pass at <= 8/12 kept; realism judge = 2 judges, at most 1 single-judge fake
   call over 4 views.
10. **Sheet:** treat the panel labelled LEFT as the right side (as the plan does); record an authority view per part
    before tracing; scale 880 mm with mass 3.1 kg without mag (consistent with the plan).
11. **Rail:** none on the game rifle; the Fab version's dust-cover rail (from `rail_1913`) joins the plan's design
    deltas if Q7 is yes.
12. **Hand fit before the SMG:** the `Grip` origin's 40 mm is provisional; H1 on `MH_PlayerDefault` fixes it from the
    AR-01 and records `hand_offset` in `SK_AR01.skeletal.json`; the long-gun grip pose goes into `gun_standard.json`.
13. **Names:** `qa_gun` uses the tokenised deny list (4.9, `deny_tokens_test.py`), not `\b`; the plan's "no real
    pattern names anywhere" is scoped to asset names and shipped text; fastener sizes written in mm.
14. **Notifies and AnimBP:** the plan's `MagOut`/`MagIn` montage notifies stay (character side); the weapon clips'
    notifies (`MagRelease`, `MagDrop`, `MagIn`, `BoltRelease`...) go in the skeletal sidecar with frames and are added
    by the harness (U9). `SK_AR01_Skeleton` is the long-gun pilot skeleton for `ABP_Gun_LongGun` (Compatible
    Skeletons); the SMG proves sharing (U2b).
15. **README game pattern:** six components for the held rifle (`FP_/TP_Weapon`, `FP_/TP_Mag`, + 2 per attachment),
    `ForcedLodModel = 1` on every FP component; the Fab example content must work with static lighting allowed and no
    `Config/`.

---

## 12. Review findings and resolutions

Independent review of rev 1, 2026-10-04. Every finding was checked against the code, the UE 5.8 source on this PC
or Epic's pages before it was applied. None was rejected outright; four were applied with a different mechanism or
number than the reviewer proposed (noted).

| # | Sev. | Finding (short) | Verified by | Resolution |
|---|---|---|---|---|
| R1 | major | Twin's slots stacked in UV0 0..1 fail `qa_check` `uv_no_overlap` (tests all triangles, any material) | [M] `qa_check._uv_checks` -> `_overlap_checks` always on UV0; `DEFAULT_TILE_RANGE = (-1, 2)`; `qa_skeletal.uv_material_checks` has containment only; katana packer comment | **Fixed:** slot k on U tile k on every SM copy, at most 3 slots on `SM_<Code>`, no mirrored/stacked islands; SK stays 0..1; ASSET_GUIDELINES 4 exception proposed (Q22); trap 10 (5.8, 1.4, 4.6, B6) |
| R2 | major | Butted parts share vertices; `no_coincident_vertices` (1 micron) fails the joined twin late | [M] `qa_check._topology_checks` -> `_degenerate_checks`, `COINCIDENT_DISTANCE = 1e-6`; `skeletal_prop.geometry_checks` has no such test | **Fixed:** butt joints = 0.01-0.05 mm modelled gap (3.7); B6a runs `qa_check` on the joined twin from stage 3; trap 11 |
| R3 | major | `\b` deny matching misses `SM_AK47`, `T_UMP45_BC`, `MI_M4A1_Metal`; prose "M4" screws; list too short | [M] Python regex word chars; prototype `deny_tokens_test.py` (11 must-hit, 19 must-pass, exit 0) | **Fixed, different mechanism:** tokenise and match whole consecutive token runs (not qa_check's lookaround rule, which has its own IGNORECASE quirk: trap 13); scope = names + shipped text; sizes in mm; list extended to the backlog (4.9, 9, B10) |
| R4 | major | Line standard never checked against the player's hand | [M] no gate did; `MH_PlayerDefault` fit body + `metahuman_base_skel` exist in `References/Characters/` | **Fixed:** H1 (Blender, stage 3 early + stage 5 full) and U11 (Unreal) with the reviewer's thresholds plus an IK residual; 40 mm marked provisional; `hand_offset` in the sidecar (5.1, 7.2, 7.4) |
| R5 | minor | Clearance numbers contradict (B3/G5/M3); 1 deg steps too coarse; LOD3 hulls and all LOD pairs intersect by design | [J] arithmetic: 50 mm x 1 deg = 0.87 mm | **Fixed:** one clearance table (3.7); rotation step min(1 deg, c/r); 0 intersections LOD0-LOD1, < 1 px at LOD2-3; M1 on co-visible pairs only |
| R6 | minor | 2048 / 55 px/cm came from the hip view only; ADS needs ~98 px/cm | [J] recomputed: 2560 / (2 x 25 x tan 27.5) = 98; 2560 / (2 x 25 x tan 35) = 73 | **Fixed, different decision:** camera block in `gun_standard.json`; A 80-100, B 60-80; set size = smallest power of two that reaches them (2048 likely, 4096 allowed); amendment to ASSET_GUIDELINES 3 proposed (Q13, Q21, Q22) |
| R7 | minor | Mag and attachments need their own FP + TP components; draw calls uncounted | [M] `PrimitiveComponent.h:730`, setter only marks own render state, `PrimitiveSceneProxyDesc.cpp` reads it per component; no propagation found | **Fixed:** full component set and `ForcedLodModel = 1` (2.1, 2.3, 6.2); draw-call count; U4 extended |
| R8 | minor | `MagOut/MagIn/MagDrop` undefined; notifies do not cross FBX; wrong cross-reference | [M] no notify code in `np_skeletal` or the fan harness; ASSET_GUIDELINES 8; 2.1 pointed at 6.3 | **Fixed:** names + `notifies` block in the sidecar, added by the harness (exact API probed first [J]); U9 checks frames; cross-reference fixed (4.6, 6.2) |
| R9 | minor | Common bone names do not share an AnimBP | [E52][E53] | **Fixed, one of the two offered:** Compatible Skeletons per class with one `ABP_Gun_<Class>`; Template ABP rejected for bone nodes; U2b (5.2, 7.4) |
| R10 | minor | FP requirement (Allow Static Lighting off) vs Fab's build-lighting and no-Config self-test | [M] ASSET_GUIDELINES 11; [E1] graceful fallback quoted | **Fixed:** example content must work with static lighting allowed and no Config; settings only in the README; Fab checklist (2.3, 9) |
| R11 | minor | No weapon texture LOD group; FP streaming risk | [M] `TextureDefines.h:36-38`; `BaseDeviceProfiles.ini` Weapon = World defaults | **Fixed:** `TEXTUREGROUP_Weapon` / `WeaponNormalMap`; U12 top-mip residency at hip and ADS (6.1, 7.4) |
| R12 | minor | Authored UV1 vs Generate Lightmap UVs (overwrites it) | [M] katana `kuc_pass1_import.py` sets generate on, src 0, dst 1 | **Fixed, option (b):** gate on the generated UV1 (U8, shuriken method); authored UV1 kept only as fallback for `--require-uv1` and buyers (5.8, 6.1); trap 12 |
| R13 | minor | Gates without numbers (B4, G6, S0, L7, U5) | read | **Fixed:** B4 at 55 deg / 0.25 m; G6 <= 0.1 mm or 1 sheet px; S0 = 0 missing fields from the validator; L7 = 2 judges, <= 1 single-judge call in 4 views; U5 bounds contain every clip vertex |
| R14 | minor | Fab "full set of animations" may need arms/character clips | [E5] fetched: Props wording "full set of animations", Smart Assets "rigged and animated"; neither defines the set | **Fixed as an open risk:** Q6 starred; ask Fab support or plan a minimal Manny arms set for one gun (9) |

**Proposed amendments to house documents** (not edited by this study; Q22): ASSET_GUIDELINES 4, "UV0:
non-overlapping islands", gains "skeletal meshes may overlap UV0 across material slots (`qa_skeletal` checks
containment only); their static twins place slot k on U tile k". ASSET_GUIDELINES 3, "4096 for hero", gains "guns:
each set is the smallest power of two that meets the derived texel classes of GUN_BUILDING_STUDY 5.8 (dated
2026-10-04)". Pipeline owner: the `qa_check` `ea` rule (trap 13).

---

## 13. Sources

1. Epic, First Person Rendering (UE 5.6+/5.8). https://dev.epicgames.com/documentation/en-us/unreal-engine/first-person-rendering
2. Epic, Blueprint API: Transform World to First Person. https://dev.epicgames.com/documentation/unreal-engine/BlueprintAPI/Camera/TransformWorldtoFirstPerson?lang=en-US
3. Epic, Nanite Virtualized Geometry (5.8, skeletal section). https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine
4. Epic, Physically Based Materials. https://dev.epicgames.com/documentation/en-us/unreal-engine/physically-based-materials-in-unreal-engine
5. Epic, Asset File Format and Structure Requirements in Fab (Firearms). https://dev.epicgames.com/documentation/en-us/fab/asset-file-format-and-structure-requirements-in-fab
6. Epic, Skeletal Mesh Sockets. https://dev.epicgames.com/documentation/en-us/unreal-engine/skeletal-mesh-sockets-in-unreal-engine
7. Epic, Animation in Lyra; forum on Lyra's `weapon_r`. https://dev.epicgames.com/documentation/en-us/unreal-engine/animation-in-lyra-sample-game-in-unreal-engine ; https://forums.unrealengine.com/t/problem-with-weapon-rotation-on-custom-animation-with-lyra/1841283
8. Epic, Material Layers; Custom Primitive Data. https://dev.epicgames.com/documentation/en-us/unreal-engine/using-material-layers-in-unreal-engine ; https://dev.epicgames.com/documentation/en-us/unreal-engine/storing-custom-data-in-unreal-engine-materials-per-primitive
9. Infima Games, replacing the weapon with a custom model (Blender to UE5). https://docs.infimagames.com/product/tactical-fps-animation-packs/guides-and-tutorials/editor/how-to-replace-the-weapon-with-a-custom-model-in-unreal-engine-5-blender-to-ue5
10. Fab, Infima Modern Guns Bundle. https://www.fab.com/listings/eb4258b3-cec4-4995-85fe-ace8c9b5d45f
11. Fab, Infima Low Poly Animated Modern Guns. https://www.fab.com/listings/6914a185-4b14-475c-8f4f-cc0a6a3c589f
12. Fab, Infima Modern Sniper Rifle. https://www.fab.com/listings/6d872a60-fbd2-48f0-9df6-16a385519dbb
13. Fab, Nando Studio Developer Weapon Kit. https://www.fab.com/listings/6e9c4979-d31c-492f-b76c-f3b2b889a52c
14. Fab, Deadghost FPS Weapon Bundle. https://www.fab.com/listings/8aeb9c48-b404-4dcd-9e56-1d0ecedba7f5
15. Fab, Tactical Gun Pack (Manifold). https://www.fab.com/listings/5eacefd6-79cf-40a5-924a-7cce66e99838
16. Fab, FPS AK Modular Weapons Pack. https://www.fab.com/listings/98e6e4cd-4589-4cff-a392-ce0c4fda3c34
17. Fab, Modular Weapon Pack: Assault Rifles. https://www.fab.com/listings/38ff34af-76cc-42fc-bde5-e975ac2631c6
18. nanos world, Weapons Meshes (+X, muzzle and shell sockets). https://docs.nanos-world.com/docs/assets-modding/creating-assets/skeletal-meshes/weapons-meshes
19. Zaggoth, The Right Way to Do Left-Hand Weapon IK. https://zaggoth.wordpress.com/2019/01/26/ue4-tutorial-the-right-way-to-do-left-hand-weapon-ik/
20. Kinemation, Tactical Shooter Pack (one pivot, per-weapon offsets). https://kinemation.gitbook.io/tactical-shooter-pack-unreal/animations/character
21. Dev_Unallocated, Procedural Weapon Animations Condensed. https://www.devunallocated.com/projects/project-killhouse/procedural-weapon-animations-condensed
22. TPS-Docs, custom weapons on Lyra's skeletons. https://docs.page/soriox/TPS-Docs/tutorials/custom-weapon
23. T. Andrushkiv, Gun Production From Start to Finish, 80.lv. https://80.lv/articles/gun-production-from-start-to-finish
24. M. Rosenberger-Loosmann (Rocksteady), Modeling a Revolver, 80.lv. https://80.lv/articles/002mrs-004adk-modeling-a-revoler-high-low-poly-uvs-baking
25. E. Hiley (Treyarch), Production of 3D Weapons for Video Games, 80.lv. https://80.lv/articles/production-of-3d-weapons-for-video-games
26. S. Mercuzot, SKS: Hard-Surface Texturing in Weapons Art, 80.lv. https://80.lv/articles/sks-hard-surface-texturing-in-weapons-art
27. A. Stokaliuk, How to Make a Weapon Look Realistic, 80.lv. https://80.lv/articles/breakdown-how-to-make-a-weapon-look-realistic-and-eye-catching
28. Room 8 Studio, FPS Weapon Creation: AAA Standards. https://room8studio.com/news/fps-weapon-creation-how-to-match-aaa-standards/
29. D. Bekishev, Weapon Production: Modeling and Rendering Tips, 80.lv. https://80.lv/articles/001agt-002mrs-003qxl-004adk-weapon-production-modeling-and-rendering-tips
30. Polycount, Weighted Normals (Mid Poly) Workflow [secondary]. https://polycount.com/discussion/238054/weighted-normals-mid-poly-workflow-clarification
31. Radiator Blog, Bevels in video games. https://www.blog.radiator.debacle.us/2017/07/bevels-in-video-games.html
32. Texel density norms [secondary]. https://www.beyondextent.com/deep-dives/deepdive-texeldensity
33. S. Lagarde, DONTNOD PBR chart for UE4. https://seblagarde.wordpress.com/2014/04/14/dontnod-physically-based-rendering-chart-for-unreal-engine-4/
34. Physically Based database. https://api.physicallybased.info/materials
35. Phosphating guide. https://www.trojansf.co.uk/phosphating
36. Type III anodizing colours. https://www.rivcut.com/blog/anodizing-type-comparison
37. Cerakote H-series gloss guide. https://www.cerakoteeu.com/knowledge-base/gloss-guide-h-series-coatings/
38. Magnetite reflectance [secondary]. https://www.mindat.org/min-2538.html
39. Valve, CS:GO Workshop finishes (wear bands, UV vs triplanar). https://www.counter-strike.net/workshop/workshopfinishes
40. APB Reloaded weapon pipeline (super-shader skins). https://apbreloaded.blogspot.com/2016/06/apb-reloaded-weapon-pipeline-overview.html
41. Picatinny rail dimensions. https://en.wikipedia.org/wiki/Picatinny_rail ; https://www.picatinny.se/en/blogs/videnscenter/picatinny-skinne-maal-dimensioner
42. M-LOK. https://en.wikipedia.org/wiki/M-LOK
43. Suppressor thread pitches. https://blog.primaryarms.com/guide/most-common-thread-for-suppressor-guide/
44. AKM. https://en.wikipedia.org/wiki/AKM
45. UMP. https://en.wikipedia.org/wiki/Heckler_%26_Koch_UMP
46. M4 carbine. https://en.wikipedia.org/wiki/M4_carbine
47. M16 rifle. https://en.wikipedia.org/wiki/M16_rifle
48. AWM. https://en.wikipedia.org/wiki/Accuracy_International_AWM
49. Desert Eagle. https://en.wikipedia.org/wiki/Desert_Eagle
50. Shooting Sportsman, Considering Checkering. https://shootingsportsman.com/considering-checkering/
51. Epic, Material inputs (anisotropy). https://dev.epicgames.com/documentation/en-us/unreal-engine/material-inputs-in-unreal-engine
52. Epic, Skeletons in Unreal Engine (Compatible Skeletons share sequences, montages and Animation Blueprints). https://dev.epicgames.com/documentation/en-us/unreal-engine/skeletons-in-unreal-engine
53. Epic forum, Layered Blend per Bone in a skeleton-agnostic template ABP (bone-reference nodes do not belong in templates; use linked layers) [secondary]. https://forums.unrealengine.com/t/layered-blend-per-bone-in-a-skeletal-mesh-agnostic-base-animation-blueprint-template/765488

**Measured in this repo / on this PC [M]** (details in the role notes): UE 5.8 `PrimitiveComponent.h`,
`CameraComponent.h`, `NaniteResources.cpp`, `NaniteCullingCommon.ush`; Epic's 5.8 template weapons and
`BP_ShooterWeaponBase` (name tables); GASP `SK_Mannequin`; `Scripts/pipeline/skeletal_prop.py`, `qa_check.py`,
`export_fbx.py`; `Scripts/unreal/materials/np_skeletal.py`, `material_spec.json`; `Exports/Fan/SK_Fan.skeletal.json`;
`WorkFiles/fan/`, `WorkFiles/katana/`; `ASSET_GUIDELINES.md` sections 1, 2, 3, 4, 7, 8, 11; the six sheets in
`References/Guns/` (`WorkFiles/studies/guns/repo_audit/sheet_silhouettes.py`, `sheet_rulers.py`). Review round
(rev 2): `PrimitiveComponent.cpp`, `PrimitiveSceneProxyDesc.cpp`, `TextureDefines.h`, `UnrealMathUtility.h`,
`Config/BaseDeviceProfiles.ini`; `qa_check.py` (`_uv_checks`, `_degenerate_checks`, `DENY_RE`),
`skeletal_prop.uv_material_checks` / `geometry_checks`; `Scripts/Katana/katana_uvpack.py`;
`WorkFiles/katana/UnrealCheck/kuc_pass1_import.py`; `WorkFiles/studies/guns/repo_audit/deny_tokens_test.py`.
