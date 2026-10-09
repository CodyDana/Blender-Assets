# Shooting prototype plan: AR-01 in DemoGame_1 (UE 5.8)

Status: PLAN ONLY (2026-10-09). Nothing in `DemoGame_1` has been changed. Every fact below marked [M] was read from
the files on this machine today; [P] marks an engine behaviour this plan does not assume and probes first (step G0).

Goal: the user can open a test map in their game, hold the finished Assault Rifle AR-01, and shoot it: hip fire,
aim down the sights, recoil, muzzle flash, ejected casings, impacts and decals, damage on the training dummy, reloads
with the magazine coming out, a fire-mode selector. Built so that every later gun (SMG01, carbine, sniper, long
rifle, pistol) adds **data and its exported assets only**, not code.

---

## 0. What exists today (the facts the plan is built on)

| Area | Fact [M] | Consequence for the plan |
|---|---|---|
| Game project | `C:\Users\Cody\Documents\Unreal Projects\DemoGame_1`, C++ module `DemoGame_1` (Core, Engine, EnhancedInput, Niagara), local git with LFS, no remote. **Another chat has uncommitted work there right now** (`BP_NinjaGasp`, `IMC_NinjaGasp`, `NinjaCombatComponent.*`, `NinjaSlashArc.*`, `CLAUDE.md`, slash-arc FX). | Touch none of those files. Add new folders only; commit only our own paths; build only when the tree compiles (section 9.4). |
| Rules of the game repo | `DemoGame_1/CLAUDE.md`: gameplay systems in C++, Blueprint subclasses assign assets and tunables; Enhanced Input only; content `/Game/<Feature>/{Blueprints,Materials,Meshes,...}`; prefixes `BP_ DA_ IA_ IMC_ ABP_ L_`; all gameplay server-authoritative from the start (roadmap D1); close the editor before building. | Follow them: `Source/DemoGame_1/Guns/*` in C++, `/Game/Guns/...` content, `DA_Gun_AR01`. |
| Player | `BP_NinjaGasp` (copy of GASP `SandboxCharacter_CMC`): hidden GASP mesh `SK_UEFN_Mannequin` drives animation; the VISIBLE body is the `VisualOverride` child actor `BP_NinjaVisual` whose `Manny` (GASP's `SKM_Manny`, skeleton `/Game/Characters/UE5_Mannequins/Meshes/SK_Mannequin`) runs `ABP_NinjaVisual` (slots `DefaultSlot` full body, `UpperBody` from `spine_01` weighted by `NinjaSealWeight`). Manny is what you see since 2026-10-04 (`USE_METAHUMAN = False`); the MetaHuman route still exists behind `ninja.visual.metahuman 1`. | Guns attach to the visible Manny. The MetaHuman (no `weapon_r`) is a later step (U11 / Q4 of the gun study). |
| Weapon socket | The UE5 Manny skeleton and `SKM_Manny` carry the names `weapon_r`, `weapon_l`, `ik_hand_gun` (string scan of the uassets); GASP's mesh has no `HandGrip_R` (Epic's template mesh does). | Attach `Grip` to `weapon_r` with the per-gun hand offset (study 6.2). Whether `weapon_r` is a bone or a socket is probed [P1]. |
| Camera | Centred spring arm (arm 375, pivot Z 70, socket offset 0, FOV 85), GASP's Gameplay Camera rig off. | Third-person hip fire from this camera; ADS goes to the sights (PUBG model, section 5). |
| Input in use | WASD, Shift, Ctrl, C, Z, Space, MMB, Tab, Alt, LMB (combo), RMB (block, consumes GASP's `IA_Aim`), E, F, G, Q, 1, 2, 3, 4, 5, 7, F1, double-tap A/D/S. Free: R, B, V, X, T, H, 6, 8, 9, 0 and others. Our IAs are Boolean, `bConsumeInput`, no triggers (Started = press, Completed = release). | Gun keys: LMB fire, RMB aim, R reload, B selector, X draw/holster, V view (later), all in our own contexts above `IMC_NinjaGasp` (section 7). |
| Damage | `UNinjaCombatComponent`: every fighter takes damage through its owner's `OnTakeAnyDamage` (Health 100, hit reaction, death, `ReviveDelay`); hostility through `UNinjaLockOnComponent::IsHostileTo` (player TeamId 0, dummy 1). The shuriken already deals damage with `UGameplayStatics::ApplyDamage`. | Guns use `ApplyPointDamage` (it also fires `OnTakeAnyDamage`) on the server: the dummy flinches, dies and revives with no new damage code. |
| Collision | `CharacterCapsule` profile ignores **Visibility** and Camera; trace channels 1-3 are taken (Traversable, Mouse, Obstacle). The visible MetaHuman/Manny child actor has collision turned off. | A plain Visibility trace would fly through characters. Add trace channel 4 `Weapon` (section 3.3). |
| Rendering | `r.AllowStaticLighting=False`, `r.Shadow.Virtual.Enable=1`, Lumen, Substrate on. | UE 5.8 First Person rendering works as-is (gun study Q5 is answered by the project). |
| Existing anims | `/Game/Characters/Mannequins/Anims/Rifle/` (Epic template content already in the project): `MF_Rifle_Idle_ADS`, `MM_Rifle_Fire`, `MM_Rifle_Reload`, `MM_Rifle_Equip`, `MM_Rifle_DryFire`, `AO_Rifle` (+ CC/CD/CU), rifle jog/walk/jump, 8 hit reacts; skeleton `/Game/Characters/Mannequins/Meshes/SK_Mannequin`, which today lists **no** compatible skeleton (the GASP skeleton lists the Bare Ninja and Muay Thai copies). | Placeholder third-person hold / fire / reload pose without authoring anything (section 8). Needs one Compatible Skeletons entry [P3]. |
| FX | `/Game/NiagaraExamples/FX_Weapons/`: `NS_MuzzleFlash` (emitters flash, smoke, sparks, **bullet shells** with `SM_BulletShell`; user params Flash/Shell/Smoke/Bullet/GlobalScale), `NS_Impact_Concrete/Metal/Wood/Glass` (incl. `NE_Impact_LightDecal`), `NS_BulletTracer`, `FX_NDC/NDC_Impacts` (data-channel impacts), `BP_ImpactProjectile`. | Copy (not reference) into `/Game/Guns/FX` and restyle (section 4). |
| Engine helpers | `NiagaraComponent` passes `IsFirstPerson()` to its proxy (Niagara honours `FirstPersonPrimitiveType`); `UGameplayStatics::TransformWorldToFirstPerson` / `TransformFirstPersonToWorld` exist; `WorldSpaceRepresentation` **forces `bOwnerNoSee = true`** internally (`PrimitiveComponent.h:159`). | FP muzzle flash can be a FirstPerson Niagara component; world tracers are mapped from the FP muzzle; the TP gun must NOT be WSR while the owner views it in third person (section 8.1). |
| Epic's shooter template | `Templates/TP_FirstPerson/Source/.../Variant_Shooter`: `AShooterWeapon` (FP + TP `USkeletalMeshComponent`s, `FirstPerson` / `WorldSpaceRepresentation`, `NoCollision`, projectile fire, `RefireRate`, `bFullAuto`, `AimVariance`, `FiringRecoil` as pitch input, ammo refill, HUD broadcast) + `IShooterWeaponHolder` (attach, recoil, target = camera trace `ECC_Visibility` 10 000 cm); FP character camera on `head` with `FirstPersonFieldOfView` 70, `FirstPersonScale` 0.6. | We keep its shape (weapon actor + holder interface + camera-target trace) and change: hit-scan, data asset, server authority, clips + notifies, mag components, ADS, TP view mode. |
| AR-01 exports | `Exports/Guns/AR01/`: `SK_AR01` (+LOD1-3), 5 clips (`Fire` 60 fps 8 f; `Charge`, `Reload` 60 f, `ReloadEmpty` 84 f, `Selector` 30 f at 30 fps), 17 sockets (`Grip` origin, `SupportHand`, `Muzzle` on `muzzle_device`, `Sight` on `sight_rear` pitch -0.4579, `Mag` on `magazine`, `MagRockStart`, `MagInsertStart`, `ShellEject` on body yaw 80 / pitch 20, `ChargingHandle`, `Selector`, `MagRelease`, `Trigger`, ...), notifies in the sidecar (Fire 1, ShellEject 3, TriggerReset 8; MagRelease 2, MagOut 15, MagDrop 20, MagIn 53; ChargeRear 74, BoltRelease 80), selector poses Safe 0 / Auto 8 / Semi 18 in `A_AR01_Selector`, clips hold the selector at Auto, `PHYS_AR01` 3.1 kg, bounds extension (0, 0.378, 0) cm, materials on the pack masters. Eye relief standard 0.25 m; gun study Q21 default FOVs 70 hip / 55 ADS. | Imported into the game with the stage-8 harness logic (`arA_import.py`), not by hand. |
| Harness style | `WorkFiles/guns/rifle/UnrealCheck` (`run_ue.sh`, `run_game_ue.ps1`, `arE_game.py`: fresh `UnrealEditor-Cmd -game -RenderOffscreen`, `-ExecCmds="py ..."`, a Slate post-tick state machine, `HighResShot`, JSON report, machine guard `wait_unreal_free.ps1`, kill only its own pid on its own timeout) and the dojo play test (`Scripts/dojo/unreal/run_ninja_playtest.ps1` + `dj_ninja_playtest.py`: real keys via `Input.+key`, **refuses to run while the project is open in any editor**, camera moved by plain attribute writes, never `set_editor_property` on the pawn). Headless ABP building precedent: `Scripts/SnowFlowerHeels/ue_hc_build_abp.py` (`editor_toolset...BlueprintTools`, `-EnablePlugins=EditorToolset`). | The prototype's harness is the same pattern (section 9). |

---

## 1. Where it lives

### 1.1 Game project (DemoGame_1)

| Path | What |
|---|---|
| `Source/DemoGame_1/Guns/` | C++: `NinjaGunTypes.h`, `NinjaGunData.*`, `NinjaGun.*`, `NinjaGunComponent.*`, `NinjaGunAnimInstance.*`, `AnimNotify_NinjaGun.*`, `NinjaGunImpactSet.*`, `NinjaDroppedMag.*` (section 2) |
| `/Game/Guns/Core/` | `BP_GunBase` (child of `ANinjaGun`, holds defaults only), `ABP_Gun_LongGun` (on `SK_AR01_Skeleton`, the long-gun class ABP of the study 5.2), `DA_ImpactSet_Default`, `PM_Concrete/Metal/Wood/Flesh/Glass` (physical materials) |
| `/Game/Guns/AR01/` | The imported AR-01 (`SK_AR01` + LODs, `PHYS_AR01`, clips with notifies, `SM_AR01`, `SM_AR01_Mag`, textures, materials) and `DA_Gun_AR01` |
| `/Game/Guns/Shared/` | `SM_Casing_762x39` (built in Blender, section 4.2), later the pistol / full-power casings |
| `/Game/Guns/FX/` | `NS_Gun_MuzzleFlash_Rifle`, `NS_Gun_CasingEject`, `NS_Gun_Tracer`, `NS_Gun_Impact_<Surface>`, `M_Gun_BulletHole` (decal) |
| `/Game/Guns/Audio/Placeholder/` | empty slots, filled by the user (section 6) |
| `/Game/Guns/Input/` | `IA_GunFire`, `IA_GunAim`, `IA_GunReload`, `IA_GunSelector`, `IA_GunEquip`, `IA_GunView`; `IMC_GunsBase`, `IMC_GunsEquipped` |
| `/Game/Guns/Character/` | `BP_NinjaGasp_Gun` (child of `BP_NinjaGasp`), `BP_NinjaVisual_Gun` (child of `BP_NinjaVisual`), `ABP_NinjaVisual_Gun` (duplicate of `ABP_NinjaVisual` + a gun layer), `GM_GunRange` |
| `/Game/Maps/L_GunRange` | **New test map.** No existing level changes. World Settings GameMode override = `GM_GunRange` |
| `Tools/Claude/Guns/` | Setup and test scripts (section 9), versioned with the content they create, like every other game tool |
| `Docs/Guns_Prototype.md` | The game-side doc (how to play, tune, add a gun); one pointer line added to `CLAUDE.md` at commit time |

**Why child Blueprints and not edits:** `BP_NinjaGasp`, `ABP_NinjaVisual` and `IMC_NinjaGasp` are the user's live character
and are being edited by another chat. `BP_NinjaGasp_Gun` changes only `VisualOverride`'s child actor class (to
`BP_NinjaVisual_Gun`) and adds `NinjaGun` (`UNinjaGunComponent`). When the user wants guns in the real game later,
the same component goes onto `BP_NinjaGasp` itself and the gun layer into `ABP_NinjaVisual` in one reviewed step.

### 1.2 This repo (Blender_Projects)

| Path | What |
|---|---|
| `WorkFiles/guns/shooting/SHOOTING_PROTOTYPE_PLAN.md` | This plan |
| `WorkFiles/guns/shooting/runs/<run>/` | Reports and gate JSON of each harness run (screens are PNG: gitignored by the repo rules) |
| `Scripts/guns/casings/` + `Exports/Guns/Shared/Casings/` | The casing mesh through `Scripts/pipeline` (section 4.2) |
| Locks | `py -3 -B Scripts/pipeline/lock.py claim GunProto --agent claude` (game-side work) and `Casing762` (Blender) |

### 1.3 The test map `L_GunRange`

Built by `Tools/Claude/Guns/build_gun_range.py` from `/Engine/Maps/Templates/Template_Default` (the house method: no
create-level tool), daylight so screenshots can be judged (`L_NinjaTest` is night):
- floor 120 x 30 m, `MI_NinjaTile` (1 m grid gives scale in every shot), `PlayerStart` at the firing line;
- `BP_TrainingDummy` at 10 / 25 / 50 m (TeamId 1, 100 HP, revives after 3 s; unchanged class);
- target boards 1 x 1 m with each physical material: concrete, steel plate, wood, glass (impact FX and decal check);
- one wall at 20 m (spread pattern), one low cover block 1.5 m in front of the line (muzzle-obstruction test);
- a black backdrop panel behind a white card at 25 m for the sight-picture gate;
- distance markers every 5 m; a spectator `CameraActor` side-on to the shooter (third-person checks).

---

## 2. Code: data-driven gun core (C++), every later gun adds data only

### 2.1 Classes

| Class | Role |
|---|---|
| `UNinjaGunData : UPrimaryDataAsset` (`DA_Gun_<Code>`) | Everything that differs per gun (2.2). No per-gun Blueprint needed: `BP_GunBase` reads the meshes, ABP and clips from the data asset |
| `ANinjaGun : AActor` (`BP_GunBase`) | Components `FP_Weapon` + `TP_Weapon` (`USkeletalMeshComponent`, same `SK_<Code>`), `FP_Mag` + `TP_Mag` (`UStaticMeshComponent`, `SM_<Code>_Mag` on each weapon's `Mag` socket, zero relative transform), both pairs `NoCollision`, `ForcedLodModel = 1` on FP. Owns ammo, fire mode, the fire timer, the reload state machine, the server RPCs and the cosmetic multicast. Replicated, owned by the pawn |
| `UNinjaGunComponent : UActorComponent` (on the character, `NinjaGun`) | Spawns / equips / holsters the gun, attaches it (`weapon_r` + hand offset), binds `IMC_GunsBase` / `IMC_GunsEquipped`, owns the camera side: aim trace, ADS blend, recoil on the control rotation, view mode, HUD (crosshair, ammo, hit marker via `AHUD::OnHUDPostRender`, like the lock-on marker), pushes the gun-hold weight and IK target to the visible mesh's ABP, sets GASP's aim/strafe flags while a gun is out |
| `UNinjaGunAnimInstance : UAnimInstance` | C++ base of `ABP_Gun_LongGun`: `TriggerPull` (0..1), `SelectorTime` (seconds into the gun's selector clip), `SelectorSequence`, `BoltOffsetCm` + `BoltLockAlpha` (procedural, for guns with a hold-open), later `StockFold`, `SightFlip` |
| `UAnimNotify_NinjaGun : UAnimNotify` | One notify class with an `EventName` (`GetNotifyName` returns it, so the U9 name checks keep working). `Notify()` finds the owning `ANinjaGun` and calls `OnGunEvent(EventName)`. Works with montages and single-node playback alike |
| `UNinjaGunImpactSet : UDataAsset` | `EPhysicalSurface` -> impact Niagara system, decal material + size + lifetime, sound; a default row |
| `ANinjaDroppedMag : AActor` | A simulating `SM_<Code>_Mag` (its UCX hulls, mass from data), spawned at `MagDrop`, despawns after 20 s, at most 8 alive |

The template's `IShooterWeaponHolder` idea is kept as `INinjaGunHolder` (implemented by `UNinjaGunComponent`'s owner
through the component), so a future non-GASP pawn (the dojo port, an AI shooter) can hold the same gun.

### 2.2 `DA_Gun_AR01` fields (defaults for the AR-01)

| Group | Fields (AR-01 value) |
|---|---|
| Identity | `Code` AR01, `DisplayName` "Assault Rifle AR-01", `Class` LongGun |
| Assets | `WeaponMesh` SK_AR01, `MagMesh` SM_AR01_Mag, `PickupMesh` SM_AR01, `AnimClass` ABP_Gun_LongGun, `CasingMesh` SM_Casing_762x39 |
| Clips | `Fire` A_AR01_Fire, `Reload`, `ReloadEmpty`, `Charge`, `Selector` A_AR01_Selector; `SelectorTimes` {Safe 0/30, Auto 8/30, Semi 18/30, Safe-via-Auto end 30/30} |
| Sockets | names from the sidecar standard (study 5.3): Grip, SupportHand, Muzzle, Sight, Mag, ShellEject (data only so an odd gun can rename) |
| Hand | `HandOffset` weapon_r -> Grip = identity (sidecar `hand_offset`, PROVISIONAL until U11/H1) |
| Fire | `FireModes` [Safe, Auto, Semi] in lever order (real AK lever: safe top, auto middle, semi bottom); `RPM` 600; `BurstCount` 0; `bChamber` true (tactical reload = 30 + 1); `MagSize` 30; `ReserveStart` 120 (prototype: infinite reserve toggle) |
| Damage | `Damage` 34; `HeadMultiplier` 2.0 (used once per-bone hits exist, 3.3); `FalloffStartM` 30, `FalloffEndM` 100, `FalloffMin` 0.6; `MaxRangeM` 300; `ImpulseOnPhysics` 600 |
| Spread (half-angle, deg) | `HipBase` 2.0, `HipMoving` +1.5, `HipAir` +3.0, `AdsBase` 0.15, `AdsMoving` +0.4, `PerShotBloom` 0.25 up to `BloomMax` 1.5, `BloomRecovery` 4 deg/s |
| Recoil (camera) | `PitchPerShot` 0.45-0.65 deg, `YawPerShot` -0.15..+0.30 deg (AK drifts up and right), `FirstShotMult` 1.3, `AdsMult` 0.75, `RecoveryDelay` 0.12 s, `RecoverySpeed` 7 deg/s (recovers only what recoil added, not the player's own mouse) |
| Recoil (weapon kick, FP) | `KickBackCm` 1.2, `KickPitchDeg` 1.4, `KickYawDeg` 0.3, spring `Stiffness` 350, `Damping` 28 |
| ADS | `EyeReliefCm` 25 (standard), `AdsFov` 55, `HipFovFP` 70, `AdsTime` 0.18 s, `bAdsHidesCrosshair` true |
| Clip timing | `FirePlayRate` = clip length / (60 / RPM) = 0.1333 / 0.1 = 1.333 (computed, not typed) |
| FX | `MuzzleFlash` NS_Gun_MuzzleFlash_Rifle, `CasingEject` NS_Gun_CasingEject (+ eject speed 350-500 cm/s, spin), `Tracer` NS_Gun_Tracer, `TracerEvery` 4 (0 = none), `ImpactSet` DA_ImpactSet_Default, `CameraShake` CS_Gun_Rifle |
| Sounds | slots (section 6) |
| Character | `HoldPose` MF_Rifle_Idle_ADS, `AimOffset` AO_Rifle, `FireAnim` MM_Rifle_Fire, `ReloadAnim` MM_Rifle_Reload, `EquipAnim` MM_Rifle_Equip (placeholders, section 8.3) |
| Projectile (later) | `bProjectile` false, `MuzzleVelocity`, `GravityScale`, `ProjectileClass` (kept for the sniper, 3.4) |
| Dropped mag | `MagMassKg` 0.33 (empty steel AK mag; not in the sidecar), `MagLifetime` 20 |

### 2.3 Gun state machine (in `ANinjaGun`, server-authoritative)

`Holstered -> Equipping (EquipTime) -> Idle <-> Firing`, `Idle -> Reloading -> Idle`, `Idle -> SelectorChange -> Idle`.
Fire is refused in Safe, while reloading, sprinting (GASP `WantsToSprint`), or with an empty chamber (dry-fire click
instead). The AR-01 pattern has **no last-round bolt hold-open**, so an empty gun looks the same as a loaded one and
`ReloadEmpty` (with the charge) is chosen by `AmmoInMag == 0 && !bChambered`. Reload is not cancellable in v1 (a
cancel after `MagDrop` would need the dropped mag's rounds rules; decided later).

---

## 3. Fire: hit-scan from the camera, muzzle as the visual origin

### 3.1 Per shot (local player)

1. **Aim ray.** From the active camera (spring-arm camera in third person, the eye in ADS) along its forward plus the
   spread cone (seeded `FRandomStream`: seed = shot counter, so the server reproduces the same direction).
   In third person the ray starts where it passes the pawn's head plane (skips the 3.75 m between camera and body, so
   nothing behind the ninja is hit).
2. **Obstruction check.** A second trace from the muzzle (`TP_Weapon`'s `Muzzle`, world space) to the aim hit: if it
   hits first (a wall in front of the barrel, the low cover block), that is the real impact. ADS needs none (the eye
   ray is the sight line).
3. **Prediction.** The owner plays cosmetics at once (flash, casing at the clip's `ShellEject` notify, sound, kick,
   recoil, its own impact FX) and sends `ServerFire(FNinjaShot{Origin, Dir, Seed, ShotIndex, ClientTime})`
   (reliable; 10 per second at 600 rpm).
4. **Server.** Validates (mode != Safe, ammo, interval >= 60/RPM - 5 ms, origin within 50 cm of the pawn's view point,
   direction within the spread cone + 2 deg of the control rotation), traces the same two rays on the `Weapon`
   channel, `ApplyPointDamage` (damage x range falloff) to hostile fighters only (`IsHostileTo`; a shadow clone of the
   enemy counts as hostile), `AddImpulseAtLocation` on simulating bodies (dropped mags, props), decrements ammo,
   multicasts `MulticastShotFX(ImpactPoint, Normal, Surface, ShotIndex)` unreliable, skip owner; `ClientConfirmHit`
   to the owner for the hit marker.
5. **No lag compensation in v1** (stated; the 1v1 is played with friends; rewinding capsules is a later step).

### 3.2 Fire timing

- Auto: a server-side and owner-side timer at 60 / RPM; the first shot fires on the press; release stops on the next
  tick. Semi: one shot per press, presses inside the cycle time are buffered for 0.08 s (like the combo buffer).
- The weapon clip `A_AR01_Fire` (8 frames at 60 fps = 0.133 s, bolt to the rear stop and back) plays at the
  computed `FirePlayRate` 1.333 so one cycle equals one shot interval; each shot restarts it.

### 3.3 Collision: a `Weapon` trace channel

- Add `ECC_GameTraceChannel4` `Weapon` (trace type, default Block) to `Config/DefaultEngine.ini` (the only config
  edit besides the physical surfaces). Characters block it with their **capsule** in v1 (capsule hits are enough for
  the 1v1 prototype; damage is per hit, not per bone).
- v2 (per-bone, headshots): the capsule ignores `Weapon` and the hidden GASP mesh's physics asset bodies block it
  (query only); the hit bone picks `HeadMultiplier`. Which component of the dummy can carry that is probed [P1].
- Physical surfaces in `DefaultEngine.ini`: SurfaceType1 Concrete, 2 Metal, 3 Wood, 4 Flesh, 5 Glass; `PM_*` assets
  set on the range targets; characters report Flesh by rule (no physical material on a capsule). Untagged = Concrete.

### 3.4 Projectile option (kept for the sniper)

`bProjectile` in the data spawns `ANinjaGunProjectile` (`UProjectileMovementComponent`, sweep on `Weapon`, gravity,
speed from data, tracer as its own Niagara) instead of the trace; same server validation and damage path. Not built
in the prototype, only the data fields and the branch in `Fire()`.

---

## 4. Visual effects

### 4.1 Muzzle flash, tracer, impacts, decals

| Effect | Source | Where / rule |
|---|---|---|
| Muzzle flash | `NS_MuzzleFlash` copied to `/Game/Guns/FX/NS_Gun_MuzzleFlash_Rifle`; its shells emitter switched off (casings come from our own system at the notify); flash scaled to an intermediate-rifle brake (the AR-01's brake vents sideways: side flash > forward); a 0.04 s point light (shadowless) | Spawned attached to the **active view's** weapon component at `Muzzle`: `FP_Weapon` in ADS with the Niagara component set to `FirstPerson`, `TP_Weapon` otherwise; others always see the TP flash (multicast) |
| Smoke wisp | the same system's smoke emitter, lower rate | after the last shot of a burst |
| Tracer | `NS_BulletTracer` copied to `NS_Gun_Tracer`; every 4th round (`TracerEvery`) | from the TP muzzle for others; from `TransformFirstPersonToWorld(FP muzzle)` for the owner in ADS so it leaves the barrel on screen |
| Impact | `NS_Impact_Concrete/Metal/Wood/Glass` copied to `NS_Gun_Impact_<Surface>`; Flesh = a small dust/cloth puff (no gore; question O4) | by the hit's physical surface via `DA_ImpactSet_Default`, oriented to the normal |
| Bullet hole | `M_Gun_BulletHole`: a material-only deferred decal (radial dark core + soft scorch, noise breakup; no textures), 1.6 cm (wood/concrete), 1.2 cm steel with a bright ring | `SpawnDecalAttached` on the hit component (so holes ride moving props), 15 s then 2 s fade, oldest-first pool of 64 |
| Camera shake | `CS_Gun_Rifle` (wave oscillator, 0.12 s) | owner only, scaled down x0.4 in ADS |

The NDC route (`NDC_Impacts`, one pooled system fed by a data channel) is the battle-royale optimisation; v1 spawns
pooled components (`ENCPoolMethod::AutoRelease`).

### 4.2 Shell casing (built in Blender through the pipeline)

- **Mesh:** `SM_Casing_762x39` built by `Scripts/guns/casings/build_casing.py` (headless Blender 5.2, `--factory-startup`),
  exported only through `Scripts/pipeline` (`qa_check` first) to `Exports/Guns/Shared/Casings/` with a
  `.sockets.json` (socket `Base` at the head centre). Real 7.62x39 dimensions: case length 38.7 mm, rim and base
  11.35 mm, shoulder 10.07 mm, neck 8.6 mm, extractor groove, bottle-neck taper; **spent**: open mouth with wall
  thickness, struck primer dimple; **no headstamp** (study 6.2: generic casings, no markings). LOD0 ~400 tris
  (24 segments), LOD1 ~120, LOD2 ~40; no UCX (Niagara collides by scene depth / distance fields).
- **Finish:** lacquered steel case (the common finish for this calibre) as material values, no texture set:
  a `MI_Casing_Steel` on the pack's `M_Steel_Master` if the pack materials are copied in (O2), else a 3-parameter
  material. A brass variant is one colour change.
- **Ejection:** `NS_Gun_CasingEject`, built from the examples' `NE_BulletShells` with our mesh, spawned at the
  `ShellEject` notify (frame 3, the carrier at the rear stop) at the `ShellEject` socket; initial velocity along the
  socket's +X (right, slightly forward and up) 350-500 cm/s plus the gun's velocity, tumble 900-1800 deg/s, scene
  collision with 2 bounces, a tink sound slot on first bounce, 4 s life, 40 alive max. In ADS the owner's casing
  spawns at the FP socket through `TransformFirstPersonToWorld` so it leaves the port on screen.
- House rules: lock `Casing762`, a row in `showcase/ASSET_LIST.md` + `showcase/Casing_762x39/` (memory: showcase
  folder rule), README in the export folder.

---

## 5. Recoil, ADS and the cameras (the PUBG model)

### 5.1 View modes

| Mode | Camera | What the owner sees |
|---|---|---|
| Third person, hip (default) | the existing spring arm (375 cm, FOV 85), crosshair at screen centre with the current spread drawn as a gap | the visible body + `TP_Weapon` + `TP_Mag` (primitive type **None**, owner can see them); FP components hidden |
| ADS (RMB held) | the eye: the camera moves onto the `Sight` line, `EyeReliefCm` 25 behind the notch, looking along `Sight` +X; world FOV and FP FOV both 55 (equal, so the gun is not distorted against the world); blend `AdsTime` 0.18 s | `FP_Weapon` + `FP_Mag` (`FirstPerson`, LOD0); TP components switched to `WorldSpaceRepresentation` (others and shadows still see them); the body WSR too (no body in the face) |
| First person (V, later step G9) | the eye at the head with FP FOV 70, `FirstPersonScale` 0.6 (template value) | FP weapon at a hip offset from data + FP arms |

`UNinjaGunComponent::SetGunView(Mode)` sets every component's visibility and `FirstPersonPrimitiveType` explicitly in
each switch; nothing relies on engine defaults [P6: `WorldSpaceRepresentation` forces owner-no-see; the visible body
is a child actor, so whether owner-no-see reaches it "indirectly" is probed].

### 5.2 ADS alignment (sight picture gate B4 in the engine)

In ADS the FP gun is placed relative to the camera, not to the hand: `FP_Weapon` world = Camera x
inverse(`Sight` socket in component space) x (EyeRelief along -X). The camera axis is then exactly the sight line, so
the front post tip sits at screen centre on the notch top (the sidecar's B4 definition) and the hit-scan ray goes
where the post points, at every range (the `Sight` pitch of -0.4579 deg is honoured: the gun tilts, not the view).
Weapon kick and idle sway are added on top of that placement as a spring offset that always returns to zero.

### 5.3 Recoil

- **Camera:** per shot, add pitch/yaw from the data ranges to a tracked `RecoilOffset` applied to the control rotation
  (owner only; the server only validates). After `RecoveryDelay` without a shot, recover `RecoveryOffset` toward zero
  at `RecoverySpeed`, minus whatever the player pulled down himself (track mouse pitch input during the burst so a
  player who compensates does not get pulled further down).
- **Weapon:** FP: the spring kick (2.2). TP: `MM_Rifle_Fire` as a 0.1 s upper-body slot play on the visible mesh
  (placeholder) + the gun's own bolt clip.
- **Spread bloom** grows per shot and decays (2.2); the crosshair gap shows it.

---

## 6. Sounds: placeholder slots only

`UNinjaGunData` slots (all `USoundBase`, may be empty = silent): `FireSingle`, `FireTailOutdoor`, `FireTailIndoor`
(later), `DryFire`, `SelectorClick`, `MagRelease`, `MagOut`, `MagIn`, `ChargeRear`, `BoltRelease`, `CasingBounce`
(by surface), `Equip`, `Holster`; the impact set has per-surface `ImpactSound`; `HitMarker` (owner UI).
A `SC_Gun` concurrency (max 8 fire voices per gun, stop oldest) and `SA_Gun_Rifle` attenuation (audible far,
low-pass beyond 50 m) are created empty-ready. Reload sounds play from the weapon clip's notifies (`MagRelease`,
`MagOut`, `MagIn`, `ChargeRear`, `BoltRelease`), so their timing is the clip's. **The user sources the real gun audio**;
until then the prototype is silent (default, O5), or uses Epic's template `FirstPersonTemplateWeaponFire02` as a
stand-in for the fire slot only if the user prefers.

---

## 7. Input (Enhanced Input)

| Action | Key | Context | Behaviour |
|---|---|---|---|
| `IA_GunEquip` | X | `IMC_GunsBase` (priority 1, added by the component at possession, always on) | draw / holster |
| `IA_GunFire` | LMB | `IMC_GunsEquipped` (priority 2, added while a gun is out, removed on holster) | press = fire / start auto, release = stop; consumes LMB so the melee combo does not fire |
| `IA_GunAim` | RMB | `IMC_GunsEquipped` | hold to ADS (O7: hold vs toggle); consumes RMB so Block does not fire |
| `IA_GunReload` | R | `IMC_GunsEquipped` | reload (tactical or empty chosen by state) |
| `IA_GunSelector` | B | `IMC_GunsEquipped` | next fire mode in lever order (AK: Safe -> Auto -> Semi -> Safe) |
| `IA_GunView` | V | `IMC_GunsEquipped` | third / first person (step G9) |

Same style as the house IAs: Boolean, `bConsumeInput` on, no triggers. All new keys are free today. While the gun is
out the component sets GASP's `WantsToStrafe` + `WantsToAim` (as the lock-on does) so the body faces the camera while
shooting; it restores the player's own values on holster. The lock-on component writes the same two flags, so both
go through one small shared helper with an owner count (otherwise holstering while locked on would turn strafe off).

---

## 8. Character side: attach, poses, first person

### 8.1 Third-person attach

- `TP_Weapon` attaches to the visible Manny (`NinjaVisual::FindVisualMesh`) at `weapon_r` with `HandOffset`
  (identity, provisional). `TP_Mag` rides `TP_Weapon`'s `Mag` socket.
- **Left hand:** two-bone IK (`hand_l`, joint target from the elbow) to the `SupportHand` socket world transform,
  pushed each tick into `ABP_NinjaVisual_Gun` (`GunSupportHandWS`, alpha `GunIKAlpha`: 1 when idle / firing, 0 during
  reload and equip). The sidecar marks `SupportHand` PROVISIONAL (it sits on the handguard underside); the measured
  H1 pose replaces it later.
- **Gun layer** in `ABP_NinjaVisual_Gun` (a duplicate of `ABP_NinjaVisual`, built headlessly with BlueprintTools):
  after the existing chain, `Layered blend per bone` from `spine_01` (mesh-space rotation) with the data's `HoldPose`
  (`MF_Rifle_Idle_ADS`) + `AO_Rifle` driven by the control pitch, weight `GunHoldWeight`; then a `Slot 'GunUpper'`
  for fire / reload / equip one-shots; then the left-hand IK. Its source is the retargeted body, so an empty slot never
  shows the reference pose (the house's known trap).
- **Compatible skeletons [P3]:** the template rifle clips sit on `/Game/Characters/Mannequins/Meshes/SK_Mannequin`.
  Add the visible Manny's skeleton to that template skeleton's `CompatibleSkeletons` (it is not a GASP asset); only
  if the engine needs the reverse entry too, add it to the GASP skeleton (precedent: the Bare Ninja and Muay Thai
  entries).

### 8.2 First-person setup (UE 5.8 First Person rendering)

- `FP_Weapon` / `FP_Mag`: `FirstPersonPrimitiveType = FirstPerson`, `ForcedLodModel = 1`, cast no shadow (engine
  rule), visible only in ADS / FP view. `TP_Weapon` / `TP_Mag`: `None` in third person, `WorldSpaceRepresentation` in
  ADS / FP.
- The view camera: `bEnableFirstPersonFieldOfView` and `bEnableFirstPersonScale` on only in ADS / FP.
- **FP arms (step G8):** a `FP_Arms` component on the pawn: `SKM_Manny` (the same skeleton as the visible body),
  `FirstPerson`, owner-only, head and neck hidden (`HideBoneByName neck_01`), pose = `HoldPose` + two-bone IK of both
  hands to `FP_Weapon`'s `Grip` (through `HandOffset`) and `SupportHand`. Until G8 the ADS view shows the gun without
  hands (an honest placeholder, the user is told).

### 8.3 What is placeholder, and what is ours to make later

| Need | Placeholder now | Ours later (the gun study Q1: "our own", procedural in the game) |
|---|---|---|
| Hold / aim pose | `MF_Rifle_Idle_ADS` + `AO_Rifle` (Epic template, made for Epic's rifle) | a hold pose fitted to the AR-01 on the player (`H1` / U11) |
| Fire body motion | `MM_Rifle_Fire` on `GunUpper` | procedural kick from the gun's recoil + a short shoulder clip |
| Reload | weapon clip carries the mag (pattern 1); body plays `MM_Rifle_Reload` with left-hand IK off | a character reload montage with the mag on `hand_l` (pattern 2, the game default in the study), notifies copied from the weapon clip |
| Equip / holster | `MM_Rifle_Equip`; holster = hide | holster on the back (`SlingRear` / `Holster` sockets) |
| Sprint / jump with a gun | GASP's locomotion under the upper-body hold | gun-down sprint pose |
| MetaHuman body | not supported in v1 (gun follows Manny's hand) | `weapon_r` socket on the MetaHuman `hand_r` (gun study Q4) |

The template clips are Epic's: fine inside this game, never shipped on Fab.

---

## 8b. Weapon-side animation (the gun's own bones)

- `ABP_Gun_LongGun` (target `SK_AR01_Skeleton`, parent class `UNinjaGunAnimInstance`), graph:
  `Slot 'Weapon'` (clips as dynamic montages) -> `Layered blend per bone` (branch `selector`, alpha 1) with a
  `Sequence Evaluator` (Sequence = `SelectorSequence` pin, Explicit Time = `SelectorTime`) -> `Transform (Modify) Bone`
  `trigger` (rotation, alpha = `TriggerPull` while LMB is held in Auto, so the trigger does not flutter between shots)
  -> `Transform (Modify) Bone` `bolt` (-X `BoltOffsetCm`, alpha `BoltLockAlpha`; unused by the AR-01) -> Output.
  Built headlessly by `Tools/Claude/Guns/build_gun_abp.py` with `editor_toolset...BlueprintTools`
  (`-EnablePlugins=EditorToolset`), the heels check's proven method.
- **Selector shows the real mode at all times**, including during the fire and reload clips (they hold Auto): the
  selector branch always comes from the selector pose. A mode change tweens `SelectorTime` between the data's times
  (Safe 0 -> Auto 8/30 -> Semi 18/30 -> Safe through 22/30 to 30/30, i.e. the lever passes Auto on its way up, as
  on the real rifle) in the clip's own duration; `SelectorClick` plays at the end.
- **Shared ABP:** the SMG and later long guns list `SK_AR01_Skeleton` as compatible and use the same ABP (gun study
  5.2, gate U2b); bones a gun lacks are ignored.
- **Magazine (pattern 1):** `FP_Mag` / `TP_Mag` ride the `magazine` bone through the `Mag` socket, so the reload clip
  moves them. `MagDrop` (frame 20): hide both seated mags and spawn `ANinjaDroppedMag` at the socket's world
  transform with the bone's velocity (finite difference over the last frame); show the seated mags again on the next
  frame (the clip then carries the new mag in along `MagInsertStart -> MagRockStart -> Mag`); `MagIn` (53): ammo
  becomes `MagSize` (+1 when chambered). Exact frame of re-show is checked from frames in G7.
- Notify -> gun events: `Fire` (cosmetic sync only; the shot itself is input-timed), `ShellEject` (casing),
  `TriggerReset`, `MagRelease`, `MagOut`, `MagDrop`, `MagIn`, `ChargeRear`, `BoltRelease`, `Selector*` (sounds).
  The import step adds them as `UAnimNotify_NinjaGun` events at the sidecar frames (not as one Blueprint class per
  name as the validation check did).

---

## 9. Verification harness

### 9.1 Runner and guards (`Tools/Claude/Guns/run_guns.ps1`)

Modes: `-Mode commandlet` (`UnrealEditor-Cmd <DemoGame_1.uproject> -run=pythonscript -script=...`, writes content),
`-Mode game` (`UnrealEditor-Cmd <uproject> /Game/Maps/L_GunRange -game -RenderOffscreen -dx12 -ResX=1920 -ResY=1080
-windowed -unattended -nosplash -nop4 -NoSound -NoLiveCoding -NoVSync -ExecCmds="py gun_playtest.py" -abslog=...`,
read-only). Before launching, in this order, each check logged to `<log>.guard.txt`:

1. **Is DemoGame_1 open in an editor?** `Get-CimInstance Win32_Process` for any `UnrealEditor*.exe` whose
   `CommandLine` contains `DemoGame_1` (the dojo runner's test), plus a 2 s probe of the MCP server on
   `127.0.0.1:8000` asking `AssetTools.exists('/Game/Maps/L_Main')` (an editor launched from the Epic launcher or the
   project browser is caught this way too; MyProject6 can also hold port 8000, so only a `true` counts).
   **If open: do nothing, exit 3, and the session tells the user:** "DemoGame_1 is open in the editor (pid N). Please
   save, close it, and say go." Never wait silently, never kill it, never touch its assets (commandlets on an open
   project can overwrite or be overwritten by the editor's in-memory packages; autosave-restore prompts follow).
2. **Machine guard:** `WorkFiles/shuriken/UnrealCheck6/wait_unreal_free.ps1` (no `UnrealEditor-Cmd` and no headless
   editor anywhere; waits up to 90 min in 60 s polls, logs every check). One Unreal process on the machine at a time.
3. **Binaries fresh:** `Binaries/Win64/UnrealEditor-DemoGame_1.dll` newer than every file in `Source/` (else build
   first, 9.4).
4. **Repo snapshot:** `git status --porcelain` and sha256 of `Content/Guns/**` + `L_GunRange.umap` recorded before;
   after a `game` run they must be identical (gate F15); after a `commandlet` run only `/Game/Guns/**`,
   `/Game/Maps/L_GunRange` and the two config lines may differ.
5. Launch hidden with a timeout (game 20 min, commandlet 30 min); on timeout kill **only its own pid**; after exit, stop
   any leftover `UnrealEditor*` whose command line names our script. Nothing is left running.

### 9.2 The play test (`gun_playtest.py`, one `-game` process, Slate post-tick state machine)

Pattern of `arE_game.py` + `dj_ninja_playtest.py`: find the PlayerController, real keys via `Input.+key / -key`,
camera aims by setting the control rotation (computed toward a target point), no `set_editor_property` on the pawn,
`HighResShot` for frames, every event in a JSON report, `quit` at the end. The gun exposes test hooks
(`ninja.gun.debug 1` logs `NGUN` lines; `ninja.gun.nospread 1`; `ninja.gun.infiniteammo 0/1`; delegates
`OnShotFired`, `OnGunEvent`, `OnAmmoChanged`, `OnHitConfirmed` that the script binds).

| # | Scenario | Gate (numbers) |
|---|---|---|
| F0 | world ready, pawn is `BP_NinjaGasp_Gun`, press X | gun equipped within EquipTime + 0.2 s; ammo 30+1 (spawned chambered); IMC_GunsEquipped active |
| F1 | Semi, 5 presses at 0.3 s on the 10 m dummy (nospread) | 5 shots, ammo -5, every shot interval >= 0.1 s |
| F2 | Auto, hold LMB 2.0 s | 20 +- 1 shots; last shot <= 1 frame after release; ammo exact |
| F3 | hits | dummy Health drops by `Damage` x shots (it revives at 0: counted through the hit delegate); impact point within 1 cm of the camera-ray hit at 10 m with nospread; 0 hits on the shooter, its visual or its gun |
| F4 | ADS sight picture | camera axis vs `Sight` +X <= 0.02 deg; camera on the sight line <= 0.05 cm at EyeRelief; screenshot on the black/white card: front post tip at screen centre +-1 px (B4 in the engine) |
| F5 | spread | 100 hip and 100 ADS shots on the 20 m wall: 95th-percentile radius = tan(cone) x 20 m +-15 %; bloom grows and decays per data |
| F6 | recoil | control pitch rise per shot within the data range; recovery to <= 10 % of the added offset within RecoveryDelay + offset/speed + 0.2 s; a script that pulls the mouse down is not over-recovered |
| F7 | reloads | tactical (10 left): `Reload` clip, notifies in order at frame/fps / play rate +-1 frame, ammo 30+1 exactly at `MagIn`; empty: `ReloadEmpty` with `ChargeRear` / `BoltRelease`; dropped mag spawns at `MagDrop` on the `Mag` socket transform +-0.1 cm, rests within 3 s, never below the floor (the U7 method); seated mag visible again before `MagIn` (frames) |
| F8 | selector | Safe: LMB gives 0 shots and no ammo change; B cycles Safe -> Auto -> Semi -> Safe; the `selector` bone is at 0 / 16 / 32 deg +-0.1 at rest **and during the fire clip** (proves the layer) |
| F9 | bolt / trigger | during a shot the `bolt` reaches -103.25 mm +-0.5 at the rear-stop frame and returns to rest; in Auto the trigger stays pulled while LMB is held |
| F10 | FX | muzzle Niagara active <= 1 frame after each shot, at `Muzzle` of the view's component (FP in ADS, TP otherwise); casing spawned at `ShellEject` at the notify time +-1 frame, initial direction within 15 deg of socket +X; one impact system per hit, chosen by surface on the four boards + Flesh on the dummy; decals spawned and capped at 64 |
| F11 | visibility | third person: owner sees TP gun + mag (component flags + frame), FP hidden; ADS: owner sees FP only, TP still casts the shadow (frame vs a frame with the TP gun hidden), the body is not in the view |
| F12 | attach and IK | `TP_Weapon` `Grip` = `weapon_r` x HandOffset +-0.01 cm; `hand_l` to `SupportHand` <= 1.0 cm with IK alpha 1 (idle, walking, firing) |
| F13 | obstruction | aiming over the low cover with the muzzle behind it: impacts on the cover, not the target |
| F14 | performance (reported) | 3 s auto burst after a warm-up burst: game-thread frame time +<= 1.0 ms vs idle, 0 hitches > 50 ms |
| F15 | clean | 0 warnings / errors from `/Game/Guns` assets or `LogNinjaGun`; 0 "Accessed None"; the project's tracked files unchanged by the play test (9.1 check 4) |
| F16 | network (step G10, not in v1) | listen server + 1 client: the client's hits damage the dummy on the server; ammo and selector agree; the other player sees the TP flash, tracer and impact |

Frames for the user (1920x1080, `WorkFiles/guns/shooting/runs/<run>/shots/`): hip third person, firing (flash) frame,
ADS sight picture, casing in flight under `slomo 0.1`, impacts + holes on each board, reload at `MagDrop` and at
`MagIn`, dropped mag on the floor, spectator side view while firing, contact sheet.

### 9.3 Fresh-process rule

Content-writing steps and the play test are always separate processes; the play test only ever reads. Import results
are re-read in a second fresh process (gates U1, U3, U5, U9 of the gun study) before anything is built on them, as
the rifle's stage 8 did; sha256 of `Exports/Guns/AR01/*` recorded at import and checked unchanged.

### 9.4 Building the C++

Only with DemoGame_1's editor closed (guard check 1): `Build.bat DemoGame_1Editor Win64 Development
-Project=... -WaitMutex -NoHotReloadFromIDE` (the house note: Live Coding's mutex blocks builds whenever any editor of
this engine runs). The module also compiles the other chat's uncommitted C++: if their files do not compile, stop and
ask (never edit their files). `Build.cs`: add `PhysicsCore` (physical surfaces) and nothing else.

---

## 10. Work split: small buildable steps

Each step ends with its gates passing and a commit of our own paths only (`git add` by path) in the game repo; the
Blender repo side commits to the gun branch. Times are focused Claude time on the user's PC; Unreal waits not counted.

| Step | What | Needs | Gates | Est. |
|---|---|---|---|---|
| **G0** | Probes (read-only): P1 the dummy's and player's collision (capsule / hidden mesh / visual) per channel; P2 `weapon_r` is a bone or a socket on `SKM_Manny` and its frame vs `hand_r`; P3 does a `/Game/Characters/Mannequins` rifle clip play on the visible Manny with one compatible entry; P4 what GASP's aim flag changes in our setup (camera is the spring arm); P5 FirstPerson Niagara renders with FP FOV; P6 owner-no-see reaches the child-actor body; P7 BlueprintTools in a DemoGame_1 commandlet. One commandlet + one `-game` run | editor closed | report only | 1 h |
| **G1** | Casing `SM_Casing_762x39` in Blender, pipeline export, showcase row | Blender only (can run any time, also in parallel) | `qa_check`; real dims within 0.05 mm; tri budget | 2 h |
| **G2** | Import AR-01 into `/Game/Guns/AR01` (`import_ar01.py`, from `arA_import.py`): LODs, sockets, clips with `UAnimNotify_NinjaGun` events, `PHYS_AR01`, bounds extension, texture groups; materials (O2); read-back in a fresh process | G3's notify class compiled first, or the import adds notifies in a second pass | U1, U3, U5 (counts, bounds), U9, materials compile 0 errors under Substrate | 2 h |
| **G3** | C++ core (classes of 2.1, the state machine, server RPCs, trace, damage, ammo, recoil, ADS math, view modes, HUD, debug cvars) + `Build.cs` + build | editor closed for the build | compiles clean, 0 new warnings | 6 h |
| **G4** | Content: `DA_Gun_AR01`, `BP_GunBase`, inputs + contexts, physical materials + config lines, FX copies and restyle, decal material, impact set, `ABP_Gun_LongGun` (headless) | G2, G3 | assets load in a fresh process; ABP compiles; U2-style check: selector layer + trigger + bolt nodes move the bones by the commanded amount | 3 h |
| **G5** | Character: `BP_NinjaVisual_Gun`, `ABP_NinjaVisual_Gun` (gun layer, IK), `BP_NinjaGasp_Gun`, `GM_GunRange`, compatible skeleton entry | G0 P2/P3/P6 answers | ABP compiles; F12 numbers in a quick `-game` probe | 3 h |
| **G6** | `L_GunRange` | none | loads, dummies placed, surfaces tagged | 1 h |
| **G7** | Play test `gun_playtest.py` F0-F15, first full run, fixes, frames to the user | G1-G6 | F0-F15 (F14 reported) | 4 h + fix rounds |
| **G8** | ADS polish + FP arms (8.2) | G7 | F4, F11 with arms; hands on Grip / SupportHand <= 1 cm | 3 h |
| **G9** | Tuning pass with the user (recoil, spread, FOV, timings), optional first-person mode (V) | user plays it | user's call | 2 h |
| **G10** | Network test (listen server + client) | O8 (two game processes) | F16 | 3 h |
| **G11** | Docs: `Docs/Guns_Prototype.md` (play, tune, add a gun: export -> import script -> one `DA_Gun_<Code>`), pointer in the game's `CLAUDE.md`, this repo's memory note | end | doc review | 1 h |

**Total about 28-31 h** of work (4-5 sessions), plus fix rounds after G7. A playable first version (hip fire, ADS
without arms, reload, selector, FX, damage) exists after **G7**, about 22 h in. Recommended order: G0 and G1 first
(G1 needs no Unreal), then G3 -> G2 -> G4 -> G5 -> G6 -> G7.

**Adding the SMG later** = export `SMG01` with the same standards -> `import_gun.py SMG01` (the G2 script with the
code as an argument) -> `DA_Gun_SMG01` (values) -> mark `SK_SMG01_Skeleton` compatible with `SK_AR01_Skeleton`
(U2b). No new code, Blueprint or ABP. The side-folding stock is one more ABP variable (`StockFold`) on the shared ABP.

---

## 11. Open questions (each has the default this plan uses)

| # | Question | Default |
|---|---|---|
| O1 | Third-person shooting with ADS into the sights (PUBG model), or a first-person game mode first | Third person + sight ADS; first-person mode as G9 option |
| O2 | AR-01 materials in the game: copy the pack's `/Game/NinjaPack` closure (masters + `MI_AR01_*` + maps) from the validation project (built without Substrate; the game has Substrate on), or a simple BC/ORM/N material | Copy the pack closure (look parity, recolour kept); if it does not compile cleanly or looks different under Substrate, fall back to the simple material and report |
| O3 | Damage numbers (34 per hit, 100 HP dummy = 3 hits) and whether guns may hit only hostile fighters | 34, hostile only (same rule as the combo and shuriken) |
| O4 | Hit effect on characters: dust/cloth puff, or blood | Puff, no blood |
| O5 | Placeholder sounds: silent until the user supplies audio, or Epic's template fire sound as a stand-in | Silent; slots ready |
| O6 | Ammo rules: 30+1 chambered, reserve 120 vs infinite for the prototype | 30+1, infinite reserve toggle on in the range |
| O7 | ADS on RMB: hold or toggle | Hold |
| O8 | Network test needs a listen server and a client = two Unreal game processes at once (the machine rule says one process) or PIE multi-player in the user's open editor via MCP | Defer to G10; then ask: PIE with the user's editor open |
| O9 | Where the gun harness reports live: game repo `Saved/Claude/Guns` or this repo's `WorkFiles/guns/shooting/runs` | Scripts in the game's `Tools/Claude/Guns`, reports copied to `WorkFiles/guns/shooting/runs` |
| O10 | Commit in DemoGame_1 while another chat has uncommitted work there | Commit only our own paths after each green step; never stage theirs; the `CLAUDE.md` pointer line waits until their `CLAUDE.md` edits are committed |
| O11 | When guns move from the test map into the real character (`BP_NinjaGasp`, `ABP_NinjaVisual`, LMB/RMB conflicts with combo and block) | Not in this prototype; a separate reviewed step after the user has played the range |

## 12. Risks

- `weapon_r` frame, the template hold pose (made for Epic's rifle) and the provisional `SupportHand` will not fit the
  AR-01 exactly: the left hand may float or clip until H1 / U11 are done. IK hides most of it; the user sees it in G7.
- `WorldSpaceRepresentation` forces owner-no-see; if runtime switching of `FirstPersonPrimitiveType` does not reset
  it, the view-mode switch must keep two TP component sets or toggle visibility instead [P6 / F11 catch it].
- The headless ABP build via BlueprintTools is proven on a simple graph only; `Layered blend per bone` branch filters
  and `Transform (Modify) Bone` pins may need the house's MCP graph route with the editor open (asks the user).
- The pack masters were built in a non-Substrate project; under Substrate they may compile with a different look (O2).
- The other chat's uncommitted C++ in DemoGame_1 may not compile at the time of our build (9.4): we stop and ask.
- GASP's aim/strafe flags are shared with the lock-on: without the shared owner count, holstering can switch strafe
  off while locked on (section 7).
- The import drops the known sub-0.005 mm2 triangles on the statics and logs tangent warnings (the AR-01's open U5/U10
  items); F15 must whitelist those exact known lines, nothing else.
- Perf numbers (F14) are noisy while another GUI editor (DojoLab, etc.) runs on the GPU: reported, not gating.
