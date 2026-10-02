# Ninja character port: DemoGame_1 -> DojoLab. Survey and port plan

Stage: SURVEY + PORT PLAN, 2026-10-02. Read-only everywhere. This stage wrote only this folder: `PORT_PLAN.md`, `closure.json` and `tools/`. Nothing was opened in an editor and no Unreal process was started. DemoGame_1 was read with `git --no-optional-locks` and plain file reads only.

Owner request (2026-10-02): bring the DemoGame_1 player into DojoLab, meaning its LOOK, its MOVEMENT and its JUTSU. These are not wanted now: the air-jump flips, lock-on, crouch-run and prone, free look, and the combat actions.

## 0. Pre-checks run in this stage

- **Armory-hall sync** (`py -3 -B WorkFiles/shared/armory_hall/tools/check_sync.py --side dojo`): **FAIL**, but none of it is owed by the dojo side.
  - The manifest is at rev 4. DojoLab is at rev 3, which is the revision it needs.
  - 25 `FAIL: sha` lines: `Exports/ArmoryKit/*.fbx` differ from the manifest or are missing. The tool's own note says the armory chat owes a bump or a re-export, and the git status shows these FBX files modified by the armory chat.
  - 1 STALE line: the armory's interior data, which the armory chat regenerates.
  - The port touches no shared file. The build stage must re-run the check and must not change shared files.
- **Unreal processes:** `UnrealEditor-Cmd.exe` PID 40256 is running ArmoryLab `-game` (ak_perf.py). It belongs to another chat; leave it alone.
  - Nothing has DojoLab.uproject open.
  - The build stage must wait until no Unreal process runs before its one commandlet, and before Build.bat.
- **Asset locks:** `WorkFiles/locks/mh_playerdefault.json` (CharacterLab source, since 09-25) and `blackcloak_mh_v2.json` (a v2 cloak in Blender, since 09-27) belong to other chats.
  - We copy only DemoGame_1's game copies and never touch those sources.
  - A later BlackCloak_MH_v2 would arrive through a re-sync (section 7).

## 1. Source: which DemoGame_1 state is ported (git commit hash)

- DemoGame_1 is on branch `metahuman-player`, **HEAD `7ea694afab7420f552879ce0f0a917901fbd07d7`** ("Catwalk: judging rounds 4-6 applied, final build r7").
- The working tree is dirty: BP_NinjaGasp, metahuman_base_skel, the uproject, two maps, CLAUDE.md, untracked mocap and catwalk content.
- **`Source/` is identical to HEAD** (`git diff HEAD -- Source` is empty).
- **The player in DemoGame_1 today is the FEMALE MetaHuman** (`setup_mh_visual.py BODY='female'`, commit 290dc79).
  - On disk, `BP_NinjaVisual` hard-imports `/Game/MetaHumans/MH_PlayerFemale/BP_MH_PlayerFemale` and `ABP_MH_NinjaBody_Female`.
  - Copying today's BP_NinjaVisual would drag MH_PlayerFemale in, and that is forbidden (private).
- **The male player is commit `43fd6ce242b48c282e089e802d6f0c113f821c21`** ("BlackCloak re-fitted to the MetaHuman player, worn with Chaos Cloth"). The plan takes two packages from that commit's git-LFS blobs, which are present locally in `.git/lfs/objects`:

| Package | Blob (sha256 = LFS oid) | Why |
|---|---|---|
| `/Game/Ninja/Blueprints/BP_NinjaVisual` | `5ea028e27eda24a366efd898d40ebb09b08ff23d0b12bd5d6fdd823a3d5a2f95` (58,969 B) | MetaHuman child actor = `BP_MH_PlayerDefault`, body ABP `ABP_MH_NinjaBody`, `CloakMH` tagged `NinjaMHGarment`. Its name map differs from today's file ONLY in those three female/male swaps. |
| `/Game/Ninja/Blueprints/BP_NinjaGasp` | `017e4018029f60d3c8099a0f23df67b7d97538432f79ea68f0d42b49aa15542b` (1,329,521 B) | Identical to f9e6292 (2026-09-21). Today's file adds only the female catwalk walk tier (`WalkAnimation`=A_Catwalk_Mocap, `WalkClipSpeed`, `WalkMinSpeed`, slowed WalkSpeeds). The catwalk was traced from another animator's reel, so it is private and not ported. |

Every other package comes from the working tree. The closure check is that none of them reaches a female, private or catwalk path: `private_blocked` is empty, and none of the 7 non-female files added by the female commit 93ea852 is in the closure.

C++: copy from the working tree (= HEAD 7ea694a).
- Between 43fd6ce and HEAD only `NinjaRunStyleComponent.h/.cpp` changed (+38/-3, the walk tier).
- That tier is inert while `WalkAnimation` is null, which it is in the 43fd6ce BP. So HEAD's source runs the male-era BP exactly.

## 2. C++: what to copy, and what the jutsu needs from the other components

The jutsu component (`NinjaJutsuComponent.cpp`) includes `NinjaFireball.h`, `NinjaHandEffect.h`, `NinjaJutsu.h`, `NinjaLockOnComponent.h`, `NinjaStanceComponent.h` and `NinjaVisual.h`. It uses other components only like this:

- **Stance:** `CanStartJutsu()` refuses while `UNinjaStanceComponent::IsProne()`. `UpdateClone()` copies the leader's `WantsProne()` / `SetProne()` to the clone. Both go through `FindComponentByClass` and are null-safe.
- **Lock-on:** `UpdateClone()` reads the leader's `UNinjaLockOnComponent::GetLockTarget()` so clones face the target. Also `FindComponentByClass` and null-safe.
- **Air jump:** not referenced. Clones copy jumps through `JumpCurrentCount`.
- **Combat:** not referenced by the jutsu. The run style references it (an attack gate, null-safe).
- **Also used:** GASP's hidden-mesh `DefaultSlot` (a traversal check), `CharacterInputState` (clones copy the gait), AIModule (clone controllers), Niagara, Enhanced Input.

**So the jutsu needs none of the unwanted components at run time.** The minimum is to compile and link their classes, because the code names them in `FindComponentByClass<T>`. **These components are not instanced in DojoLab**, so their behaviour is not ported.

| Files (Source/DemoGame_1 -> Source/DojoLab, byte-identical) | Role |
|---|---|
| NinjaJutsuComponent.h/.cpp, NinjaJutsu.h | the jutsu |
| NinjaVisual.h/.cpp, NinjaVisualBodyComponent.h/.cpp | jutsu helpers + LOOK (MetaHuman body, CloakMH) |
| NinjaFireball.h/.cpp, NinjaHandEffect.h/.cpp, NinjaGroundSeal.h/.cpp | parent classes of BP_GreatFireball, BP_ChidoriLightning, BP_SummoningSeal |
| NinjaTurnComponent.h/.cpp | MOVEMENT: finite turn rate, MaxAcceleration 3000, GroundFriction 20, BrakingDecelerationWalking 6000 |
| NinjaRunStyleComponent.h/.cpp | MOVEMENT: the ninja run and sprint clips (Bare Ninja move_run) |
| NinjaStanceComponent.h/.cpp, NinjaLockOnComponent.h/.cpp, NinjaLockOnCameraModifier.h/.cpp | **compile/link only** (jutsu dependency, see above) |
| NinjaCombatComponent.h/.cpp | **compile/link only** (run-style dependency) |
| NinjaAirJumpComponent.h/.cpp, NinjaFreeLookComponent.h/.cpp | **optional, load-cleanliness only**: BP_NinjaGasp has SCS nodes of these classes until step B4 removes them. Without the classes the BP loads with "invalid class" warnings, and removing the nodes is then less clean. Recommended: copy them (11 KB). They are never instanced. |
| NOT copied | `DemoGame_1.h/.cpp` and `.Build.cs` (replaced). `NinjaBlueprintTool.cpp`, `NinjaClothTool.cpp`, `NinjaLandscapeTool.cpp` (editor tools: the reliable flag and the cloth data are already baked into the assets). `NinjaDebugInput.cpp` and `NinjaDebugWorld.h` (dev tools; nothing else includes them). |

Per-file sha256 values are in `closure.json` -> `cpp`. Example: `NinjaJutsuComponent.cpp` = `bf18b174...54f`, `NinjaJutsuComponent.h` = `702ba628...7c3`, `NinjaVisual.h` = `30949dd5...62b`.

**Module, with zero edits to the copied files:**
- `Source/DojoLab/DojoLab.Build.cs`, new:
  - `PCHUsage = UseExplicitOrSharedPCHs`.
  - Public: `Core, CoreUObject, Engine, InputCore, EnhancedInput, Niagara`.
  - Private: `AIModule`.
  - `PublicDefinitions.Add("DEMOGAME_1_API=DOJOLAB_API");` keeps every `class DEMOGAME_1_API ...` line untouched.
  - DemoGame_1's editor-only modules (Landscape, BlueprintGraph, UnrealEd, Clothing*, SkeletalMeshEditor, ChaosCloth) are not needed, because the editor tools are not copied.
- New `DojoLab.h/.cpp` with `IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, DojoLab, "DojoLab")`.
- New `Source/DojoLab.Target.cs` and `Source/DojoLabEditor.Target.cs`: `BuildSettingsVersion.V7`, `EngineIncludeOrderVersion.Unreal5_8`, `ExtraModuleNames.Add("DojoLab")`, the same as DemoGame_1's.
- `DojoLab.uproject` gets `"Modules": [{"Name": "DojoLab", "Type": "Runtime", "LoadingPhase": "Default"}]`. Plugins stay as they are.
- The copied assets name their classes `/Script/DemoGame_1.<Class>`. DojoLab `Config/DefaultEngine.ini` gets:
  ```
  [CoreRedirects]
  +PackageRedirects=(OldName="/Script/DemoGame_1",NewName="/Script/DojoLab")
  ```
  This covers every class, struct and enum in the module, so no asset is resaved for it.
  - Note: inside packages the module name is the FName `/Script/DemoGame` with number 2. The redirect takes the plain string.
- Fallbacks, if UHT rejects the macro define:
  - Replace the one `DEMOGAME_1_API` token per file, a documented minimal change. 15 classes plus 7 `NinjaVisual.h` symbols.
  - Or name the module `DemoGame_1`, which needs no redirect or macro but is a confusing name.
- **Build:** `& 'C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat' DojoLabEditor Win64 Development "-Project=C:\Users\Cody\Documents\Unreal Projects\DojoLab\DojoLab.uproject" -WaitMutex -NoHotReloadFromIDE`.
  - Run it with no editor on DojoLab.
  - DemoGame_1's trap: Build.bat refuses with "Live Coding is active" whenever ANY editor of this engine install runs. `-NoHotReloadFromIDE` skips only that guard.
  - Never run UnrealBuildTool.exe directly; it wants .NET 10.
  - Toolchain: VS 2022 BT, MSVC 14.44, Win SDK 10.0.22621.
- **Consequence:** DojoLab stops being content-only.
  - Every DojoLab run (the showcase scripts' `UnrealEditor-Cmd ... -game`, the commandlets) then needs `Binaries/Win64/UnrealEditor-DojoLab.dll`. Without it the editor asks to rebuild and an unattended run fails.
  - Build first, and keep the DLL built after any re-sync.

## 3. Content closure

Method (tools in `tools/`):
- `uimports.py` reads each package header without an editor: the name map, the import table (HARD references) and the soft-package list (SOFT references), with FName numbers honoured.
- `closure2.py` walks from the roots and stops at packages DojoLab already has at the same path, whose references DojoLab already satisfies.
- Every package is compared by sha256.
- A first pass that only searched for strings missed numbered names (`combo01_1` is stored as `combo01` + number), so the header reader is the one to trust.

Roots: BP_NinjaGasp*, BP_NinjaVisual*, IMC_NinjaGasp, the four DA_Jutsu_*, ABP_MH_NinjaBody, RTG_Manny_to_MH, BP_MH_PlayerDefault, SKM_BlackCloak_MH, ABP_Cloak (* = the 43fd6ce blob).

| Set | Packages | Size | What |
|---|---|---|---|
| **core copy** (needed by look, movement or jutsu) | **473** | **949 MB** | /Game/MetaHumans/Common 143, BareNinja_AnimSet/demo 104, MetaHumans/MH_PlayerDefault 73, NiagaraExamples 75, Characters/Mannequins 23, Ninja 55 |
| of which hard-reachable | 332 | 460 MB | the rest (141, 489 MB) is reached only through soft references: the pack skeleton's preview meshes and CR rigs (103), DemoGame_1's template-mannequin preview meshes (22), and the MetaHuman gray/face preview assets (16). Copy them anyway, as DemoGame_1 itself has them, so DojoLab shows no missing-soft-ref warnings. |
| **feature_only copy** | 37 | 6 MB | 17 Bare Ninja combat clips, 3 throw clips, 3 prone clips, 2 evade (flip) clips + AN_FootPlant, 11 input actions (attack, block, dodge, kunai x2, shunshin, lock-on, free look, crouch, prone). They are hard-imported by BP_NinjaGasp's unwanted components and by the untrimmed IMC_NinjaGasp. Copy them so the BP loads clean; they become unreferenced after steps B4 and B5. Keep them for a later port of those features, or delete them then. |
| already in DojoLab, **identical** | 38 | none | GASP: AC_PreCMCTick, AC_TraversalLogic, SandboxCharacter_CMC_ABP, the Data enums and structs, the camera assets, IA_* x10, SKM_UEFN_Mannequin, SKM_Manny_Simple, IK_UE5_Mannequin_Retarget, RTG_UEFN_to_UE5_Mannequin, PA_Mannequin, the Foley assets |
| already in DojoLab, **DIFFERENT** | 13 | not copied | see the table below. Never overwritten without the decision below. |
| DojoLab-only soft refs | 5 | none | ABP_NinjaVisual's GASP retarget options (RTG_UEFN_to_Echo / TwinBlast / UE4 / Metahuman_nrw / _ovw): present in DojoLab, removed from DemoGame_1 |
| soft refs missing everywhere | 4 | none | Bare Ninja pack leftovers (`/Game/wmg_template/...CR_Mannequin_*`, `/Game/Characters/Heroes/Mannequin/...`), already missing in DemoGame_1, harmless |
| private | 0 | none | MH_PlayerFemale, Hiyuki, 2B, the catwalk and Mocap folders are never reached |

The `/Game/Ninja` part (55 core packages):
- **Animation:** ABP_NinjaVisual; the 10 seals (Snake, Ram, Tiger, Monkey, Boar, Horse, Dog, Bird, Ox, Hare); the jutsu clips A_Chidori_Charge, A_Summon_PalmSlam, A_Summon_ThumbBite; the run clips A_NinjaRun_InPlace and A_NinjaSprint_InPlace.
- **Audio:** SFX_HandSeal, SFX_JutsuRelease, SFX_Chidori, SFX_FireballLaunch, SFX_FireballImpact, and the two voice lines.
- **Blueprints:** BP_NinjaGasp, BP_NinjaVisual.
- **Character:** ABP_MH_NinjaBody, RTG_Manny_to_MH, IK_MH_PlayerDefault.
- **Cloak:** SKM_BlackCloak_MH (Chaos cloth data inside), ABP_Cloak, M_BlackCloak, M_BlackCloakSolid, MI_BlackCloak_Steel, MI_BlackCloak_Leather, 3 textures, and the hidden Manny-fit SKM_BlackCloak that BP_NinjaVisual still holds.
- **FX:** NS_CloneSmoke, MI_CloneSmoke, NS_ChidoriArcs, M_SummoningSeal, T_SummoningJutsu_D.
- **Input:** IA_Jutsu, IA_Jutsu_GreatFireball, IA_Jutsu_Summoning, IA_Jutsu_Chidori, IMC_NinjaGasp.
- **Jutsu:** the four DA_Jutsu_*, BP_GreatFireball, BP_ChidoriLightning, BP_SummoningSeal.

Not reached and not needed: Rat and Dragon seals, LS_HandSeals / LS_JutsuFinishers (authoring sequences), the dummy, ParagonKallari, NS_ChidoriLightning (an unused experiment).

**Do not copy the `.wav` / `.png` import sources** that sit next to the `Ninja/Audio` and `Ninja/FX/Summoning` uassets. The packages hold the data, and a loose source file in Content triggers the editor's auto-import on the next launch.

What the request asked about specifically:
- **Retargeter and IK rig:** RTG_Manny_to_MH + IK_MH_PlayerDefault (source rig = GASP's IK_UE5_Mannequin_Retarget, identical in DojoLab). ABP_NinjaVisual = GASP's RTG_UEFN_to_UE5_Mannequin (identical).
- **MetaHuman:** BP_MH_PlayerDefault + 73 MH_PlayerDefault packages + 143 Common packages.
- **Cloak:** the mesh, cloth data, materials and ABP_Cloak as listed.
- **Jutsu montages:** none exist as assets; `NinjaVisual::PlaySlotMontage` builds dynamic montages from the sequences listed.
- **Skeletons:**
  - The seals are on DemoGame_1's template skeleton `/Game/Characters/Mannequins/Meshes/SK_Mannequin`, copied, absent in DojoLab.
  - The run clips are on the Bare Ninja pack skeleton, copied. That skeleton already lists GASP's `/Game/Characters/UE5_Mannequins/Meshes/SK_Mannequin` as compatible.
  - In DemoGame_1 the seals played on GASP's Manny with no compatible-skeleton lists at all, so runtime montage play does not need them.
  - So DojoLab's GASP SK_Mannequin stays unedited. Gate C3 proves it.

### The 13 DIFFERENT packages (DojoLab version kept by default)

| Package | Difference (name-map and import comparison) | Default |
|---|---|---|
| /Game/Characters/UE5_Mannequins/Meshes/SK_Mannequin | DemoGame_1 added the Bare Ninja skeleton to `CompatibleSkeletons` | keep DojoLab's (see above) |
| /Game/Input/IMC_Sandbox | DemoGame_1 removed GASP's demo rows (IA_Takedown, Interact, TriggerRagdoll, TeleportToTarget, NextPawn, NextVisualOverride, Move_WorldSpace) | keep DojoLab's (the GASP setting; no jutsu key collides, see risk R9) |
| .../Common/Female/Medium/NormalWeight/Body/metahuman_base_skel | DojoLab = GASP's (230 KB, the CTRL_expressions curve metadata); DemoGame_1 = the MH Creator 5.8 one (76 KB) + a CompatibleSkeletons soft ref to /MetaHumanBodyTracker + preview mesh | keep DojoLab's (superset; the body mesh imports it by path) |
| .../Common/Face/Face_Archetype_Skeleton | DemoGame_1 adds a compat + preview to MH_PlayerDefault; DojoLab has AnimationCurves metadata | keep DojoLab's |
| .../Common/Common/MetaHuman_ControlRig, .../Face/Face_ControlBoard_CtrlRig, .../Controls/M_RigControlActor_Black | newer rig graphs (CRSL_MetaHuman_Gizmo vs MHGizmoLibrary); only SOFT references from the MH meshes (DefaultAnimatingRig = editor authoring) | keep DojoLab's |
| .../Common/Materials/MI_Hair, MI_Hair_Cards, MI_Hair_Helmet, MI_Facial_Hair, M_Eyelashes_Cards, T_Black_Linear | newer MetaHuman hair materials (e.g. MI_Facial_Hair has `hairMelanin`, `MelaninVariationFine/Rough`, `HairRoughness`; DojoLab's has `RIntensity`, `Roughness`, `RoughnessTRT`, `ScraggleMobile`) | **decision D1** |

**D1, the hair and eyelash materials (the one LOOK risk in the closure):**
- MH_PlayerDefault's groom material instances (`MI_WI_Hair_S_BrushCut_*`, `MI_WI_Eyebrows_*`, `MI_WI_Eyelashes_*`) are children of these Common parents. Under DojoLab's older parents some parameter overrides will not match by name, so hair, brow and lash colour and roughness may drift.
- **Option A (default, zero overwrite):** keep DojoLab's, then measure.
  - Compare the hair, brow and lash colour against DemoGame_1's own male reference shots (`DemoGame_1/Saved/Claude/Shots/metahuman_cloak/final/*.png` and `metahuman_player/*`, PIE 2026-09-26, read-only), framed the same.
  - If they differ by more than the agreed tolerance, go to B-hair.
- **Option B-hair:** overwrite only the hair chain, after backups. That is 19 DojoLab packages: MI_Hair, MI_Hair_Cards, MI_Hair_Helmet, MI_Facial_Hair, M_Eyelashes_Cards, M_Facial_Hair, M_hair_v4, 10 MF_* hair functions, and T_Black_Linear in Materials/ and Textures/. Also add 1 new package, T_TilingNoise_005. The list with both hashes is in `closure.json` -> `metahuman_common_option_B_overwrite_set`.
  - It changes GASP's Kellan MetaHuman, which only GASP's `GM_Sandbox` visual-override list references. DojoLab gameplay and the captures do not use it.
  - Verify with a Kellan load check.
- **Never overwrite** the skeletons or the control rigs (option B-full), because GASP's retargeters and Kellan depend on them.

## 4. Settings to merge

- **Collision channels** (Traversable / Mouse / Obstacle = GameTraceChannel1-3, the profiles), **gameplay tags** (39 rows), **the 27 GASP `DDCvar` declarations**, and the PoseSearch buffer (230) are **already identical**. Nothing to merge.
- **Plugins:** every script module the closure hard-imports is already on in DojoLab, explicitly or by default/dependency:
  - AnimationWarping, IKRig, FullBodyIK (PBIK), ControlRig (+Spline), RigLogic, HairStrands, LiveLink, MetaHumanSDK (EnabledByDefault), ChaosCloth (default), Niagara, PoseSearch, Chooser, MotionWarping, MovieSceneAnimMixer, GameplayCameras, EnhancedInput, Interchange.
  - **MetaHumanCharacter and MetaHumanBodyTracker (enabled in DemoGame_1) are NOT needed.** The MH assets name `/MetaHumanCharacter/...` only as metadata strings, not as imports. The body-tracker reference is a soft compat entry on DemoGame_1's skeleton, which is not copied.
  - Keep DojoLab's plugin list unchanged. ACLPlugin (EnabledByDefault) is used only by the feature-only evade clips.
- **CoreRedirects and uproject Modules:** see section 2.
- **Camera:** DemoGame_1 sets `DDCVar.NewGameplayCameraSystem.Enable=0` under `[ConsoleVariables]`.
  - `SandboxCharacter_CMC` and its copy BP_NinjaGasp read it in `SetupCamera`, which runs on `EventPossessed`.
  - At 1 the GASP rig wins (over-the-shoulder). At 0 BP_NinjaGasp's own SpringArm and Camera take the view (arm 375, pivot Z 70, socket 0, lag 12, FOV 85, carried inside the BP).
  - It is a project-wide cvar, and GASP's pawn needs 1 to keep its own camera.
  - **Recommended:** don't change the ini. Set it per mode before possession, from a new ~30-line file in the DojoLab module (a world subsystem bound to `FGameModeEvents::GameModePreLoginEvent`, or the game mode's `PreLogin`). It sets 0 when the game mode's default pawn class is BP_NinjaGasp and 1 otherwise.
  - Fallback: put the ini line in (DemoGame_1's way). This changes GASP's pawn camera only when someone plays it; DojoLab captures use placed cameras with the pawn hidden.
- **Game mode:**
  - DojoLab's `GM_Dojo` is a BP child of GASP's `GM_Sandbox` (PC_Sandbox, `PawnClasses_Soft` [Mover, CMC], `DDCvar.PawnClass` selects one) with DefaultPawnClass `SandboxCharacter_CMC`.
  - New **`/Game/Dojo/Blueprints/GM_DojoNinja`**, a child of GM_Dojo, with DefaultPawnClass `BP_NinjaGasp`.
  - Becomes `GlobalDefaultGameMode` and the L_Dojo world-settings override.
  - **Switch back to the reference pawn:**
    - `-game` with `L_Dojo?game=/Game/Dojo/Blueprints/GM_Dojo.GM_Dojo_C` (a URL `game=` beats the world override), or
    - `DDCvar.PawnClass <index of SandboxCharacter_CMC>` (GASP's own switch; measure the index), or
    - in the editor, set the world override back.
  - **DojoLab's own gates assert the old mode:** `dj_verify.py` gate 4 and `dj_sc_verify.py` gate 5 check `GlobalDefaultGameMode=GM_Dojo` and pawn `SandboxCharacter_CMC`. The build stage updates them (Scripts/dojo/unreal is this chat's pipeline) to accept GM_DojoNinja + BP_NinjaGasp and to keep checking that GM_Dojo still yields SandboxCharacter_CMC.
  - walk_check / climb_check are offline: they read the capsule from the SandboxCharacter_CMC CDO, untouched. BP_NinjaGasp is a copy with the same capsule; gate C6 checks it.
- **Input:** `DefaultInput.ini` F1 debug-binding removal is not needed (F1 = the aerial kunai, not ported). IMC changes are content (step B5).

## 5. Risks

- **R1, MetaHumans/Common path collision.** DojoLab's Common is GASP's (Kellan); DemoGame_1's is MH Creator 5.8.
  - 143 packages add cleanly. 10 differ: plan above, D1.
  - Two skeleton versions under one path: the MH_PlayerDefault meshes load against DojoLab's `metahuman_base_skel`. Same bone tree expected; check it with zero "missing bone" or "skeleton mismatch" lines in the load log (gate C2).
- **R2, `/Script/DemoGame_1` class paths** inside every copied BP, DA and ABP. Covered by the CoreRedirect. If it is missing, BP_NinjaGasp loses its components on the first resave. **Never resave a copied asset before the redirect and the built module are in place.**
- **R3, the C++ build.**
  - DojoLab becomes a C++ project (needs the DLL, section 2).
  - The Live Coding mutex while ArmoryLab or any editor runs: use `-NoHotReloadFromIDE`, and Build.bat only with no editor on DojoLab.
  - UHT and the `DEMOGAME_1_API` define: fallback in section 2.
- **R4, MetaHuman versions.** The assets are ue5 object version 1018 (MH Creator in 5.8). DojoLab's GASP Common is 1012/1013. Same engine (5.8) loads both.
  - DojoLab sets `r.SkinCache.DefaultBehavior=0` (skin cache only where a mesh asks for it); DemoGame_1 used the engine default.
  - The MetaHuman grooms and the face may need skin cache on their meshes to follow deformation.
  - Gate C4: measure, with a hair-root vs head-bone offset in a moving -game frame. If needed, set skin-cache usage on the MH_PlayerDefault meshes only, not the project cvar.
- **R5, GASP's own assets in DojoLab** (IMC_Sandbox, SK_Mannequin) differ from DemoGame_1's edited copies; they are kept. If the run clips refuse to play (gate C3), add the compat entry on DojoLab's SK_Mannequin. That is a documented edit of a DojoLab copy of a GASP asset; the GameAnimationSample project itself is never touched.
- **R6, an asset not loading by path.** The copy keeps each package's path; ensure no DojoLab redirector exists at these paths (none found). DojoLab has no `/Game/Ninja`, `/Game/BareNinja_AnimSet`, `/Game/NiagaraExamples`, `/Game/Characters/Mannequins` or `/Game/MetaHumans/MH_PlayerDefault` today.
- **R7, IP and licensing.**
  - The jutsu are Naruto techniques by name: DA_Jutsu_Chidori, ShadowClone ("Kage Bunshin"), GreatFireball ("Goukakyuu"), Summoning.
  - `SFX_HandSeal`, `SFX_JutsuRelease`, `SFX_Chidori` and both voice lines are third-party anime audio. DemoGame_1 notes: "fine for this personal project, replace before sharing".
  - **Keep this port out of anything sold or published.** No DojoLab video or still that is shared may carry these sounds or names.
  - Own-work replacements exist in DemoGame_1: `make_jutsu_sfx.py` originals, `SFX_ChidoriCharge`; the fireball SFX are own work.
  - The summoning seal texture is the owner's own design. The Bare Ninja AnimSet is the owner's Fab purchase; NiagaraExamples is Epic's free content.
- **R8, unwanted behaviour.** The 43fd6ce BP_NinjaGasp carries NinjaAirJump (sets JumpMaxCount 2 at BeginPlay), NinjaLockOn, NinjaStance, NinjaFreeLook and NinjaCombat as components. Unless removed (B4) they would all run. IMC_NinjaGasp as copied also maps and consumes LMB, RMB, E, Q, C, Z, Tab, LeftAlt, 1, 5 and F1. That would silently kill GASP's crouch (C) and aim (RMB) in DojoLab, hence B5.
- **R9, GASP demo inputs in DojoLab.** DojoLab's IMC_Sandbox still maps IA_NextPawn / IA_NextVisualOverride / Takedown and the rest. GM_Sandbox's `CyclePawn` could swap the ninja for a GASP pawn on that key. No collision with F/2/3/4 (IMC_NinjaGasp priority 1 consumes them). Record the keys in the gate run; leave them (GASP setting) unless the owner says otherwise.
- **R10, Chaos cloth or MetaHuman cost in the arena.** DemoGame_1 measured about 0.15 ms for the cloak and about 0.4 ms for the MetaHuman. DojoLab already runs at 8-14 ms GPU, so re-measure with `run_game_perf.ps1` and the ninja pawn.
- **R11, stale sources.** Another chat holds `mh_playerdefault` and `blackcloak_mh_v2` locks. Port today's DemoGame_1 copies, and record the hashes so a re-sync can tell what changed.
- **R12, known DemoGame_1 gaps that come along.** Hand effects use Manny's bones, a few cm off the MetaHuman's. The face does not animate. Small skin patches show through the cloak in deep poses. Seals, clones and jutsu are local only (no replication). Foot-lock IK in ABP_NinjaVisual is wired but inert.

## 6. Proposed build-stage order (for the next stage, not done here)

- **B0. Pre-checks:**
  - `check_sync.py --side dojo`.
  - No UnrealEditor* process with DojoLab.uproject, and none running at all before the commandlet and Build.bat.
  - Take the `WorkFiles/locks` lock for this port.
- **B1. Back up DojoLab:** `DojoLab.uproject`, `Config/`, `Content/Dojo/Maps/L_Dojo*`, `Content/Dojo/Blueprints/GM_Dojo.uasset`, and (only under D1-B) the 19 hair packages. Copy them to `WorkFiles/dojo/build/ninja_character/backup_<stamp>/` with sha256.
- **B2. C++ and config:**
  - Copy the files from section 2 byte-identical (verify sha256).
  - Write the new Build.cs, module files and targets, the uproject Modules entry and the CoreRedirect.
  - Build.bat DojoLabEditor (editor closed).
- **B3. Content:**
  - Copy core + feature_only (510 packages, about 955 MB; the list and per-file sha256 are in `closure.json`, `copy_class`).
  - BP_NinjaGasp and BP_NinjaVisual come from the 43fd6ce LFS blobs.
  - Skip `.wav` and `.png`, and never overwrite a DojoLab file (assert absent first).
  - Verify every copied file's sha256.
- **B4. One DojoLab commandlet (editor Python, after the module is built):**
  - Remove BP_NinjaGasp's SCS components `NinjaAirJump`, `NinjaLockOn`, `NinjaStance`, `NinjaFreeLook`, `NinjaCombat` (SubobjectDataSubsystem, like DemoGame_1's setup scripts), then compile and save.
  - Create GM_DojoNinja and set the project and L_Dojo game mode (D2).
- **B5. Same commandlet:**
  - Trim IMC_NinjaGasp to the 8 jutsu rows: IA_Jutsu F / pad Y, GreatFireball 2 / d-pad left, Summoning 3 / d-pad up, Chidori 4 / d-pad right. The name stays the same; documented.
  - Write the camera hook (section 4).
- **B6. Gates in a second, fresh process, measured** (`-game` only for stills and video, HighResShot or the showcase capture):
  - C1: the load log has no `Failed to load` / `Missing` / `invalid class` lines for the ported paths.
  - C2: no skeleton or bone mismatch.
  - C3: the run clip plays (`ninja.run.debug 1` -> `ninja run ON A_NinjaRun_InPlace`) and the turn component is active.
  - C4: MetaHuman visible, Manny hidden, the cloak attached as a Leader Pose follower with cloth simulating; hair follows (R4); hair, brow and lash colour vs the DemoGame_1 reference shots (D1).
  - C5: each jutsu key casts (`LogNinjaJutsu`): F clone spawns and dispels, 2 fireball spawns, 3 summoning seal decal at the hand, 4 Chidori effect on hand_r for the 4 s stance.
  - C6: the centred camera (socket offset 0, arm 375), the capsule equal to the GASP CDO, and the GM_Dojo route still giving SandboxCharacter_CMC.
  - C7: perf delta.
  - C8: DemoGame_1 untouched (no file mtime or sha changed, `git status` unchanged).
  - C9: check_sync dojo-side clean.
- **B7. Write the provenance and notes:**
  - `WorkFiles/dojo/build/ninja_character/PORT_PROVENANCE.md` with the commits, every file and package with its sha256 (from `closure.json` + the copy log), every change made (B4 / B5 / the camera hook / the redirect / the macro define), and the re-sync steps (section 7).
  - Append a dated NINJA CHARACTER section to `BUILD_NOTES.md`.
  - Update `DOJO_QUEUE.md`.
  - No git commit or push.

## 7. Re-syncing from DemoGame_1 later (for PORT_PROVENANCE.md)

- **C++:**
  - Diff `Source/DemoGame_1/<file>` sha256 against the provenance table.
  - Re-copy the changed files byte-identical; check them for new includes and new component classes. A newly referenced class means re-running the include analysis in section 2.
  - Rebuild with the editor closed.
- **Content:**
  - Re-run `tools/closure2.py <out.json>`: read-only, header-based, with the same roots.
  - If DemoGame_1 is still on the female body, keep using the male-era blobs or a newer male commit (`git log -- Content/Ninja/Blueprints/BP_NinjaVisual.uasset`). Never copy anything with `BP_MH_PlayerFemale` in its imports; `closure2.py` blocks private paths.
  - Copy new and changed `copy` packages over DojoLab's previous port copies, backed up first.
  - Re-apply B4 and B5 to the new BP_NinjaGasp and IMC_NinjaGasp, which are scripted and idempotent.
  - Re-run the gates.
- DojoLab packages marked `in_dojo_DIFFERENT` are never overwritten without D1-style sign-off.

## 8. Decisions for the owner / orchestrator

- **D1, MetaHuman hair materials:** A (keep DojoLab's, measure) by default; B-hair (overwrite 19 GASP-MetaHuman hair packages, affects Kellan only) if the measured look differs.
- **D2, default pawn:** GM_DojoNinja as the project and L_Dojo default. GASP's pawn stays reachable via `?game=GM_Dojo` or `DDCvar.PawnClass`. The DojoLab verify gates are updated to match.
- **D3, the camera cvar:** per-mode hook (recommended, keeps GASP's settings) vs the DemoGame_1 ini line.
- **D4:** copy the 37 feature-only packages (recommended, clean loads and a later port) or delete them after B4 and B5.
- **D5, the turn and run-style components:** DemoGame_1's movement feel (recommended, it is what "movement" means there). Without them it is GASP's stock acceleration and run clips.
- **D6, the anime audio and the Naruto jutsu names:** keep for the private lab now; replace before any DojoLab footage is shared (R7).
