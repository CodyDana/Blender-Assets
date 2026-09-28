# Review: ChatGPT's character and clothing pipeline, checked against your folder and your goals

Reviewed 2026-09-25 against UE 5.8.3 and Blender 5.2. I only read files. I changed nothing in the project and did not launch Blender or Unreal.
Tags: **[V]** means I saw it in a file or a dated source. **[I]** is my reasoning. **[U]** means it is unconfirmed, or the sources disagree.

## 1. Bottom line

ChatGPT's core rule is right: lock the body and skeleton first, then build clothes on it. Its MetaHuman steps also fit UE 5.8 reasonably well. In 5.8, "From Custom Mesh" fits a custom sculpt to MetaHuman topology inside Unreal, and Marvelous Designer 2025.2 imports a MetaHuman body directly [V]. What the plan misses is most of what you asked for:
- **Face swap.** In a shipped game this means choosing among heads you built in advance. The MetaHuman face editor can't ship inside a game [V/I].
- **Runtime skin and nail color.** MetaHuman bakes both into its textures when it assembles a character, so you need your own material setup [V/I].
- **A cosmetic system** for the skins, weapons and clothing the game will hand out. It needs part assembly, body hiding and saved choices [I].
- **IP.** Jin Mu-Won belongs to someone else, and both of your character tracks currently aim at his likeness [V].

**What to do instead:** before you commit to MetaHuman, run a gated MetaHuman trial. I'll call it a "spike": a throwaway test build. It will take several days, and each step waits for your go-ahead (§5). If it passes, build the cosmetic system, then one pilot garment and one pilot weapon, and freeze the reusable template from those pilots.

## 2. What's in the folder today

**Study and house rules** (FAB_ASSET_STUDY.md and ASSET_GUIDELINES.md, both dated 2026-09-17)
- Strong on static meshes and Fab rules. Budgets: a dressed character is 80–120k triangles at LOD0 with hair cards only; a hero weapon is 20–50k. Skeleton rules: at most 4 bone influences per vertex, no "." in bone names, one root bone at the origin [V].
- MetaHuman appears only as an allowed skeleton. There's nothing on customization, cosmetics, Mutable, cloth, Marvelous/CLO, Leader Pose, body hiding or multiplayer [V].
- Stale: everything was measured on 5.8.2, and study §3.11 says to re-run its four tests after an upgrade. The MCP section (5.1) is out of date. The IP audit predates BlackCloak, BlackNunchucks, SnowFlower and the props [V].
- Two house rules clash with any MetaHuman or clothing plan and need written amendments:
  - §7 says "Only Deform Bones ON". That setting drops IK bones, and Fab's Epic-skeleton route needs them "unweighted and in place" (study §3.6) [V].
  - §9 says every asset must be "regenerable end to end from Scripts/". MetaHuman Creator (a GUI plus Epic's cloud) and Marvelous/CLO (GUI only) can't meet that [V/I].

**Scripts/pipeline** was built for static meshes. It has a skeletal export mode and weight checks [V], but:
- No test exercises an armature.
- Deform-only bones is the default.
- Nothing compares a garment's skeleton with the locked base.
- There are no skeletal LODs, no skeleton sockets and no high-to-low bake [V].

**Track 1: JinMuWon_v2 (custom)**
- **Setup.** A CC0 MPFB body on a custom 152-bone skeleton. Hair and Clothing share that skeleton and are meant to follow the body through **Leader Pose** (one mesh drives the others' animation). A "Human_Clothed" body has its covered polygons deleted [V]. The Leader Pose assembly exists only as README instructions: UnrealDemo has no Blueprint or AnimBP, so it has never run in Unreal [V].
- **What works.** Skin-tone and nail controls work in Blender and in Unreal 5.8.2. They use one **dynamic material instance** (a per-character copy of the material) plus UV masks, and the renders back this up [V].
- **Budget.** Dressed, it's 635,371 triangles at LOD0, 5–8× the budget, with 20 material sections [V]. The body isn't the problem: Human_Clothed is 87,691 and fits. Hair is 221,056 triangles, 174,456 of them geometric flyaway strands, which breaks the cards-only rule. Clothing is 326,624 [V].
- **Skeleton.** 114 bone names contain "." [V]. There's no `hand_r` and no IK bones, and `robe_*` bones sit inside the "base" skeleton. Only 3 of 26 Manny bone names match [V].
- **Animation is unverified in Unreal, not shown broken.** The walk/run capture harness itself crashed: `AttributeError: 'SkeletalMeshComponent' has no attribute 'set_playing'`. The later diagnostic PNGs contain no character. The commandlet's JMW_Walk/Run motion checks passed on 5.8.2 [V].
- **Look in Unreal.** A hard seam down the face and near-black blotches on the body. The docs call these "dark patches". The cause was never found, because the Sep 17 diagnostics captured no character [V]. The eyes also render black, but the Kelvin MetaHuman preview shows the same dark, iris-less eyes. That suggests a problem with the capture setup rather than the asset [I]. Check the eyes in PIE (Play In Editor) or the viewport before counting them as a defect.
- **Open review items** (REVIEW_PLAN.md, PAUSED.md) [V]:
  - Hair review is 0/7 and Clothing review 0/11. "No new severe pinching" is unchecked.
  - Overhead neck/shoulder contacts rose from 6 to 14.
  - `Hair_Structure_Candidate.blend` is uncommitted. The rejected Hair_Candidate ponytail remap must not be applied.
  - The clothing LOD renders are unfinished.
  - The scalp reimport waits until the shading problem is diagnosed.
- **Overclaims** [V]:
  - The README's "45 of 45 checks" is stale: Hair and the combined FBX were re-exported after the import.
  - "TwoPlayers" is two material copies in one editor, not a networking test.
  - Every Unreal check ran on 5.8.2.
- **Color quality.** The deep skin tone is a plain multiply and skews red-orange [I]. The nail masks are small: fingernails are about 12–17 px across on the 2048 mask, thumbs about 8–10 px. CUSTOMIZATION.md says the "borders remain visible at extreme close-up" [V].
- **Face swap.** You already approved "interchangeable heads that replace the original head", with skin-tone, iris and nail controls (REVIEW_PLAN.md line 22). So far it's only a spec: there's no head/body split, no neck seam and no blendshapes [V].
- **IP.** The design brief uses the official Northern Blade cover as its identity reference. `realistic_design_reference.png` is AI-generated. qa_check rejects the name "jinmuwon" [V].
- **Backup gap.** The BeforeMetaHuman backup (Sep 24, 18:50Z) includes the nail work. It does not include the skin-tone pass (committed 14:53 CDT Sep 24) or the later doc and report edits, and 9 of its 12 files have changed since. The current skin-tone state exists only in the live files [V].

**Track 2: CharacterLab / MH_MaleBase (MetaHuman, owned by Codex)**
- **State.** An editable copy of Epic's Kelvin preset in a 5.8.3 project. There's no rig, no high-res textures, and no assembled Blueprint, AnimBP, pawn or map [V]. Its README calls it "a starting preset, not the final Jin Mu-Won likeness", so this track aims at the third-party likeness too [V].
- **Blocker: a sign-in nobody finished, not a technical fault.** Auto-rigging and the high-res texture download need a signed-in Epic account. Preview-resolution textures were generated locally with no sign-in [V]. The browser sign-in opened, but nobody entered the code within about 10 minutes, so it failed (`EOS_Auth_PinGrantExpired`, then `EOS_InvalidAuth`). The headless runs use flags that block the browser login [V]. Epic's docs say assembly also needs the downloaded source textures [V]. That hasn't been confirmed locally [U].
- **Stale status.** `setup_status.json` still says an editor is waiting for sign-in, but none was running at 00:55 CDT. The README leaves out the second attempt [V].
- **The lock** names Codex with a dead process (PID 46768). It won't count as stale until about 07:19 CDT [V].
- **Script issues.** `create_male_preview.py` throws an IndexError on every run, so far without harm [V]. `assemble_male.py` hard-codes a "Joints Only" face rig and Optimized **High** quality [V], and a re-run may skip the texture download [I].
- **Images.** The previews use low-res textures, so don't judge the art from them. The blue skin in PresetSheet.png is a red/blue swap bug in `extract_preset_thumbnails.py`: swapping the two channels back restores natural skin on every preset [V].

**Clothing and weapon precedents**
- **BlackCloak.**
  - The skeletal version is rigidly weighted to the JinMuWon skeleton, and Unreal gave it a separate skeleton asset of its own [V].
  - It's 84,612 triangles, with no cloth sim and no Physics Asset [V].
  - Its recolor works (verified on 5.8.2) [V].
- **BlackNunchucks** is the best template for game "skins": 16 mask regions, texture reskins and a JSON manifest. It is a skeletal mesh with a skeleton of its own [V].
- **SnowFlower.** LOD0 is 456,024 triangles and even LOD2 is 118,428, against the 20–50k weapon budget. It was built from an unattributed `SnowFlower_user_reference.png` whose IP hasn't been audited [V].
- **Shuriken/kunai, paper bomb, smoke bomb.** None is tied to the character plan: no hand sockets and no hold animations [I].

**Housekeeping**
- Between 01:16 and 01:27 CDT, two Blender processes (PIDs 59324 and 61388) and the Epic Games Launcher were running. The Blender processes were almost certainly Claude's smoke-bomb rebuild, running in another session: it kept writing files under `WorkFiles/smokebomb/rewind/build/` until 01:35 [V]. No Unreal editor was running, and no JinMuWon lock was held [V].
- Claude's locks: **SmokeBomb is live.** Don't clear it while that build is running. Shuriken (Sep 17) and PaperBomb (Sep 19) are old but belong to paused Claude work (the paper bomb's exact pass is still queued), so leave them alone too [V].
- The lock system is real for Blender. `launch_blender.ps1` claims a lock before GUI Blender starts, and about 20 scripts call `assert_owner`. Codex's lock covers a `.uasset`. The MetaHuman/Unreal scripts never check locks [V].
- `LauncherInstalled.dat` still says 5.8.2, while Build.version and the logs say 5.8.3. That doesn't block anything, but check it if the Launcher acts oddly [V].

## 3. ChatGPT's pipeline, step by step

**Character pipeline**

| # | Step | Verdict | Why |
|---|---|---|---|
| 1 | Design | Keep, add | Add an IP gate covering both tracks: original name, face, hair and outfit [V, study §1/4.3]. The lock sheet should list the skin-tone range, nail and eye colors, the head list and the budgets. AI-generated references matter for Fab's AI disclosure if a design derived from them is sold [I]. |
| 2 | Blender base mesh | Change (optional) | Only needed for a custom likeness; otherwise start from a preset [V]. A-pose gives the best results, though 5.7+ accepts any pose from A to T. Clean and hole-free, with no loose clothing. Head and body can be one mesh or separate ("Head And Body" mode) [V]. If you sculpt, start from the CC0 MPFB generator, not the Jin Mu-Won body [I]. |
| 3 | Convert/fit | Keep, with caveats | 5.8 "From Custom Mesh" converts a mesh of any topology inside Unreal, and the output is always MetaHuman topology [V]. Epic's docs say stylized features "solve with varying quality", and extreme proportions can cause "volume loss or pinching" [V]. For the closest match, wrap Epic's free Conform Topology pack onto your sculpt and use "From Template" [V]. The output is "fully rigged", and rigging runs on Epic's cloud, so expect to need the sign-in [I]. Your UV masks won't carry over [I]. |
| 4 | Finalize | Change | Skin tone and nail tint are baked in at assembly. The baked materials keep only global hue/value controls and have no nail color [V: names from a file scan; runtime use is I]. Add a runtime material contract (§4). Use card hair [V]. |
| 5 | Rig + animation | Change | Epic plays Manny and Game Animation Sample (GASP) animation on MetaHumans through retargeters such as `RTG_UEFN_to_MetaHuman_nrw` [V]. Community sources say the skeleton uses Manny's names and hierarchy with extra joints, probably without `ik_*` bones [U]. **Risk to test:** a May 5, 2026 forum post reports deformed retargets on a 5.7-made body. The next day the poster said a manual two-stage retarget "minimized" the deformation. Epic hasn't replied [V]. The face is a separate RigLogic mesh, so test every head. |
| 6 | Unreal integration | Keep, add | Assemble as UE Optimized (typically under 100 MB), not Cine (about 1–2 GB). Use card hair and LODSync [V]. Epic gives no character-count or multiplayer guidance for Optimized [I]. For large crowds, 5.8 adds an Experimental Crowds pipeline [V]. Missing: how cosmetics are assembled and saved. |
| 7 | Lock the base | Change | Lock the skeleton, body topology and UVs, neck boundary and material parameter names, **but not the face** [I]. Outfit Assets refit across MetaHuman bodies at build time. Epic recommends "at least 2 source bodies (masculine, feminine)" [V]. Enforce the lock with skeleton and rest-pose hashes. Today that code exists only in JinMuWon's own script [V]. |
| — | Head library | **Missing** | This is your face-swap requirement (§4). |

**Clothing pipeline**

| # | Step | Verdict | Why |
|---|---|---|---|
| 1 | Concept | Keep, add | Add an IP check. Decide each piece's recolor regions and physics tier here. |
| 2 | Export body | Change | Marvelous Designer (MD) 2025.2 imports MetaHuman DNA directly. The alternative is Geometry Export → FBX [V]. |
| 3 | Build in CLO | Change | CLO ($450/yr) targets fashion production; MD targets games [V]. Use MD for draped pieces: hakama, haori, sleeves, cloak. Use Blender for armor, belts, bracers, tabi and tight suits [I]. Keep MD files as versioned sources under an amended §9 [I]. |
| 4 | Export to Blender | Optional | USD goes from MD straight into a UE Cloth Asset [V]. Use Blender only for retopology, UVs or bakes. |
| 5 | Blender cleanup | Keep, add | Add texturing, LODs, a separate low-poly simulation mesh, and body hiding. There's no high-to-low bake tool yet [V]. |
| 6 | Rig clothing | Keep | Fixed-size clothing: Data Transfer, then the free Robust Weight Transfer add-on, then hand fixes [V]. Resizable clothing: Unreal's Dataflow transfers the weights [V]. Whether to keep the 4-influence limit is open [U]. |
| 7 | Cloth physics | Change | Use three tiers: skin weights, then bone chains, then Chaos Cloth for hero pieces only [I]. The Chaos Cloth editor is Production-Ready in 5.8; the Outfit Asset is still Beta [V]. Epic's 5.8 table marks Leader Pose followers "Physics: No" ("cannot … simulate physics independently") and says nothing about cloth, so test cloth on a follower [V/U]. One undated third-party guide puts unoptimized cloth at 1–3 ms per character [U]. Call `ForceClothNextUpdateTeleportAndReset` on respawn (UE 5.8 API doc, seen via search snippet) [V]. |
| 8 | Unreal import | Keep | Import onto the same skeleton; BlackCloak shows why [V]. A July 2026 user report says 5.8 loses the cloth sim when an outfit is converted to a parametric wardrobe asset. There's been no Epic response as of 2026-09-15; one community workaround using a third-party Fab asset was tested on one garment [V]. |
| 9 | QA | Keep, expand | Add: seiza, crouch-walk, ledge hang, wall-run, roll, flips, ragdoll, katana draw, scabbard vs cloak, hood vs every head, LOD transitions, 8+ characters on screen. Do QA in Unreal, not in Blender renders [V]. |
| 10 | Template | Move earlier | Freeze the template from pilot pieces [I]. It needs a skeletal version of Scripts/pipeline and a Fab check. |
| — | Body hiding, recolor layout, texturing, weapons | **Missing** | See §4. |

Add one line to ChatGPT's closing "Claude command": *"Do not rename material parameters or change the neck boundary."*

## 4. What ChatGPT left out

**Face swap** (interchangeable heads are already approved)
- Ways to swap heads at runtime:
  - **(a) Pre-assembled heads.** Swap the face mesh, its DNA and its animation class on one body [I].
  - **(b) 5.8 MetaHuman Instances and Collections.** They're Experimental and "can be assembled at runtime in cooked builds". Epic's doc lists "character customization" (players picking hair, clothing and accessories) and "dynamic outfit changes", and they have runtime hair-color and material-tint parameters [V]. In March 2026 Epic staff said 5.6/5.7 didn't support runtime assembly and that this code would later be exposed as Experimental; 5.8 did that [V]. Choosing heads, skin tone, nails and multiplayer aren't documented [U]. The spike should test this as your cosmetic path.
  - **(c) Mutable.** Animated faces need a "RigLogic Extensions for Mutable" plugin. It's missing from your 5.8.3 install and from the 5.8 Plugin Index, and the 5.8 page didn't load. Whether this works in 5.8 is [U].
- Use preset heads, not sliders. Baldur's Gate 3 made the same choice [V].
- The seams are the weak spot. 5.8 has a known issue with texture seams at the head/body line, the back of the shoulders and the waist, and no workaround [V].

**Runtime skin tone and nails**
- Give each character its own material instance for every slot. Push the same values to every face LOD material and the body [V/I].
- On a baked MetaHuman, a runtime change is only a global color grade, and it shifts the lips and nails too [I].
- Two ways around that:
  - An override material with a nail mask. Overrides derived from Epic's materials still get baked [V].
  - 5.8's unbaked assembly, whose cost hasn't been measured [V/U].
- Also fix JinMuWon's weak spots: clamp the output, use hand-authored deep tones and make the nail masks bigger [I].

**Assembling cosmetics** (Epic's modular-characters page [V])
- **Leader Pose:** cheap on the game thread, heavy on the render thread, keeps morphs, no independent physics.
- **Mesh Merge:** cheapest to render, but loses morphs.
- **Mutable:** merges parts. The 5.8 notes say it has reached "production readiness", but your plugin file still says Beta [U].
- Start with Leader Pose [I].

**Hiding the body under clothes**
- Options:
  - Trimmed bodies per outfit, like Human_Clothed.
  - MetaHuman hidden-face maps (local `MetaHumanOutfitPipeline.cpp`) [V].
  - Opacity masks.
  - Mutable clipping.
- Keep trimmed edges away from the known seam lines [I].

**Fitting outfits to bodies**
- Your 5.8.3 runtime code only picks outfits that were fitted at build time [V].
- On Sep 12, 2025 (the 5.6 era), Epic's Kriss Gossart said resizing can't run at runtime because it recreates a Cloth Asset that must be cooked in the editor. Nothing from Epic confirms that for 5.8 [V/U].
- A custom body needs matching morphs on every garment [V]. If body shape is fixed, none of this applies.

**Weapons**
- Retarget Manny and Fab animation packs. Put sockets on `hand_r` (JinMuWon only has `wrist.R`).
- Per-weapon animation layers follow Lyra's pattern (`ALI_ItemAnimLayers`, Lyra animation doc 5.7) [V].
- Your existing weapons are over budget or unaudited (§2).
- If the MetaHuman skeleton lacks `ik_*` bones, Fab's Epic-skeleton route (study §3.6) needs them added to anything sold outside the `.mhpkg` route [I].

**Performance**
- Your GPU is an RTX 4070 SUPER [V].
- Eight JinMuWons at LOD0 would be about 5.1M triangles [I].
- Proposed target: **60 FPS at 1440p, High scalability, 8 characters on screen, with cloth** [I, adjust to taste].
- Compare Optimized High against Medium in that test.

**Save and network data**
- Store cosmetics as Primary Data Assets with soft references, loaded asynchronously by the Asset Manager (Epic docs) [V mechanism; the choice is I]. Save only the IDs and colors [I].
- If multiplayer: the server picks the parts and replicates only IDs and colors (RepNotify). Dedicated servers never spawn cosmetics, as in Lyra (community notes) [V].
- Launcher engine builds have historically been unable to package dedicated servers without a source build [U for 5.8]. For testing, use PIE's "Play As Client" mode instead.

**IP and licensing** (not legal advice)
- **MetaHuman** falls under the standard UE EULA [V]. For a UE game, the usual royalty applies: 5% of gross revenue above $1M per product [V, UE EULA]. The $1M seat-license threshold is for rendering MetaHumans *outside* Unreal [V]. Training or testing AI on MetaHumans is banned [V].
- **Fab** accepts MetaHumans and clothing made in 5.6+ [V]. Conditions:
  - Package as `.mhpkg`; the NoAI tag is applied automatically, and CC BY is not allowed.
  - Build clothing on the MetaHuman base skeleton without reparenting any bones.
  - Include a matching body for each outfit size.
- **Known 5.8 issue:** packaged outfits can lose their materials [V].
- **Presets:** whether a lightly edited preset like Kelvin can be sold is [U].
- **Jin Mu-Won** can't go on Fab, and using him in your game is an infringement risk. This applies to both tracks [V/I].
- **MPFB:** keep its GPL code out of the shipped game [V].

**Tool costs** [V unless marked]
- MetaHuman: no upfront fee.
- MD:
  - Personal is $39/mo or $280/yr, for "solo freelancers, hobbyists and sole proprietors". Whether a one-person LLC qualifies is [U].
  - Indie requires 2+ employees, so it doesn't fit a one-person LLC.
  - Enterprise is $199/mo.
  - The 14-day trial's commercial-use and export terms are unknown [U].
- CLO: $450/yr.
- Simply Cloth: $36–66.
- Robust Weight Transfer and the Character DNA add-on (base edition): free.

## 5. Recommended pipeline

**Every stage waits for your explicit go-ahead.** Hours are rough estimates for one agent [I].

**0. Housekeeping** (~1–2 h, plus you relaying messages to Codex)
- Back up the current JinMuWon state.
- Leave every lock alone. The Blender activity was the smoke-bomb build, still running in another session.
- Re-run the study §3.11 tests and the skin/nail checks on 5.8.3.
- Ask Codex to fix its status file and README. I can't message Codex, so you'd relay this.

*Gate:* the backup exists, the 5.8.3 results are recorded, and the owner of each track is written down.

**1. Design lock** (mostly your time; ~1–2 h for an agent to draft the sheet)
- Original front, side and back sheets.
- The skin-tone range, nail and eye colors, and the head list.
- Budgets: 80–120k triangles dressed, weapons 20–50k, card hair.
- Amend guidelines §7 (keep IK bones for Epic-skeleton exports) and §9 (GUI and cloud sources are allowed if versioned and documented).

*Gate:* the IP check passes on both tracks, AI-generated references are noted, and you sign off.

**2. MetaHuman spike** (Unreal, throwaway map; roughly 2–4 working days; one agent, since only one editor may have the project open; never run it alongside another Unreal job, because RAM is tight)

Each sub-step needs its own go:
- **2a. Sign-in, rig and assemble** (~1–2 h, scheduled while you're at the PC). You type your own Epic credentials; no agent enters them.
  - Use a normal (non-admin) editor with Chrome or Edge as the default browser, and finish within about 10 minutes. The editor looks frozen while it waits [V].
  - The log says "No existing persistent auth credentials were found", so one successful login might be reused by later headless runs [I, unverified].
- **2b. Locomotion** (~4–6 h). Manny/GASP locomotion plays through Epic's retargeter, with a katana on `hand_r`. Record the bone list (including `ik_*`) and the influence counts.
- **2c. Runtime color** (~4–8 h). Skin and nail color change at runtime and match across every face LOD at the neck, back of the shoulders and waist.
- **2d. Head swap** (~1 day; the second head needs its own rig, so another sign-in). Two heads swap in a **packaged** build. Try both pre-assembled heads and 5.8 Instances.
- **2e. Performance** (~2–4 h). Eight characters hit the proposed target, and cloth works on a Leader Pose follower.

*Gate:* if all pass, MetaHuman becomes the base. If not, fall back to the study's route: re-skin the CC0 MPFB body onto Manny's skeleton and reuse your skin/nail system. That fallback is also several days of work, because JinMuWon shares only 3 of 26 Manny bone names [V, study line 34].

**3. Base body + head library** (~2–4 days, plus your art reviews)
- Use MetaHuman Creator in Unreal; Blender only for a custom sculpt.
- One body per sex, and 2 heads to start.

*Gate:* the 11-pose deformation audit passes against thresholds you set in advance (JinMuWon never passed it), and the seams are clean at every LOD.

**4. Customization contract** (~1–2 days; Unreal materials, masks painted in Blender)
- Keep `SkinToneColor`, `SkinToneAmount`, `NailColor`, `NailPolishAmount` and `NailRoughness`.
- Add `IrisColor`.
- Redraw the masks in MetaHuman UV space.

*Gate:* the fresh-process capture harness passes on 5.8.3.

**5. Lock enforced by tooling** (~1 day; Scripts/pipeline)
- A skeleton and rest-pose hash check.
- Keep IK bones in exports.
- A skeletal test case.
- A triangle budget for the whole character.
- Skeleton sockets.

*Gate:* a deliberately broken garment export fails the check.

**6. Cosmetic framework** (~3–5 days, in Unreal)
- Data assets for outfits, skins and weapons.
- Leader Pose and body hiding.
- Weapon equipping with animation layers.
- Saved IDs.

*Gate:* any item can be swapped at runtime, and a saved game restores it. If you choose multiplayer, two "Play As Client" PIE clients also pass late-join and mid-match-change tests.

**7. Pilots** (~2–4 days each)
- **Pilot A:** a fitted inner suit made in Blender and skin-weighted, with BlackNunchucks-style recolor and body hiding.
- **Pilot B:** the cloak rebuilt as MD → USD → Cloth/Outfit Asset → Chaos Cloth. Check the trial's terms before shipping anything made with it.
- **Pilot C:** one weapon rebuilt to 20–50k triangles, with a socket and an animation layer.

*Gate:* the full QA list, the head × outfit matrix and the budgets all pass. Then freeze the template: naming, export settings, LOD rules and the QA checklist.

**8. Production and Fab**
- Every asset goes through the template.
- For Fab:
  - Verify with MetaHuman Manager and package as `.mhpkg`.
  - Test for the missing-material issue.
  - Use original designs only.
  - Re-check the Fab rules, since the study's sources are from Feb/Mar 2026.

## 6. What to do with what you already have

- **JinMuWon_v2**
  - Back it up, freeze it as the customization testbed, and rename and redesign it before anything goes public.
  - Keep for reuse: the parameter names, the per-character material pattern, the installer, the capture harness (after fixing its `set_playing` bug), the deformation metrics and the Human_Clothed idea.
  - The Leader Pose layout is a plan still to test, not a proven asset.
  - Don't apply the rejected ponytail remap. Commit or discard `Hair_Structure_Candidate.blend`.
  - Fix it only if you need a temporary playable character. That means:
    - cutting Hair and Clothing to budget
    - re-running the diagnostics with a working camera
    - checking the eyes in PIE
    - reimporting Hair and the combined FBX
    - retargeting animations
    - re-verifying on 5.8.3
- **MH_MaleBase**
  - It's Codex's, so you'd relay these requests:
    - fix the status file and README
    - fix the preview IndexError and the texture-request branch
    - make the rig type and quality level settings
    - fix the channel swap in `extract_preset_thumbnails.py`
    - change the README's Jin Mu-Won goal to an original design
  - A Kelvin copy is fine for the spike, but not as your final character.
- **BlackCloak.** Keep it as a design and recolor reference, and rebuild it as Pilot B.
- **BlackNunchucks.** Use it as the model for one shared clothing master material. Its separate skeleton needs a plan before it can be equipped.
- **SnowFlower and props.**
  - Audit the source of SnowFlower's reference image, and rebuild it to budget.
  - Add grip sockets and hold poses for the shuriken, kunai and bombs.
- **Scripts/pipeline.** Add the stage-5 gates and a high-to-low bake.
- **Customization masks.** They're in MPFB's UV layout and won't carry over; the parameter names and the harness will.
- **The study.**
  - Add MetaHuman, customization and clothing chapters.
  - Update the stale sections.
  - Record the §7 and §9 amendments.
- **Codex.** Only one editor per project at a time. Either add `assert_owner` to the MetaHuman/Unreal scripts or keep a written owner table.

## 7. Decisions only you can make

The face-swap style is already settled: you approved interchangeable preset heads (REVIEW_PLAN.md line 22). Start with 2.

1. **Base track.** *Default: MetaHuman if the spike passes; otherwise the MPFB body on Manny.* JinMuWon stays a testbed either way.
2. **Single-player or multiplayer?** You haven't said, and only ChatGPT mentioned it. *Default: single-player first, with ID-based cosmetics so replication can be added later.* Skip dedicated-server work until you decide.
3. **Body shape.** *Default: players can't change it.* One body per sex means no outfit resizing and no morphs on every garment.
4. **Face rig.** *Default: Joints Only (already scripted).* It's lighter, and ninja faces are often masked [I]. Choose Full Rig if you want expressive cutscenes.
5. **Marvelous Designer.** *Default: not yet.*
   - Ask the vendor whether your one-person LLC qualifies for Personal. Indie is ruled out, and Enterprise costs $199/mo.
   - Use the trial for Pilot B only if its terms allow commercial export.

## 8. Sources

Web (accessed 2026-09-25 unless noted; "date unconfirmed" means a later check couldn't open the page):
- MetaHuman 5.8 release notes and known issues: dev.epicgames.com/documentation/metahuman/metahuman-5-8-release-notes-in-unreal-engine ; …/metahuman-known-issues-5-8-in-unreal-engine
- MetaHuman 5.8 announcement (Epic forum, 2026-06-17): forums.unrealengine.com/t/metahuman-5-8-released/2729288 ; metahuman.com/news/metahuman-5-8-is-now-available (date unconfirmed) ; 5.6 launch (2025-06-03)
- Epic MetaHuman docs (dev.epicgames.com/documentation/metahuman/…): from-custom-mesh, from-template, assembly, LODs, runtime-retargeting, metahuman-instances-in-unreal-engine, materials-and-textures, material-overrides, selling-metahumans-on-fab, creating-your-metahuman-characters (undated; "at least 2 source bodies" quote confirmed 2026-09-25)
- Modular characters (5.8): dev.epicgames.com/documentation/en-us/unreal-engine/working-with-modular-characters-in-unreal-engine ; Mutable + MetaHumans (5.7): …/using-mutable-and-metahumans-in-unreal-engine
- Epic staff on runtime assembly (2026-03-11 to 03-16): forums.unrealengine.com/t/metahuman-collections-and-character-instances/2715460
- Retarget report (2026-05-05/06): forums.unrealengine.com/t/animation-retargeting-broken-on-new-skm-mhc-metahuman-skeletal-mesh-ue-5-7/2720169
- Outfit resizing addendum (2025-08-19; Epic reply 2025-09-12): forums.unrealengine.com/t/tutorial-chaos-cloth-outfit-asset-resizing-addendum/2647376
- Wardrobe cloth loss (2026-07-19; last reply 2026-09-15): forums.unrealengine.com/t/metahuman-parametric-wardrobe-asset-missing-cloth-simulation-5-8/2736828
- Chaos Cloth 5.8 (2026-06-17): forums.unrealengine.com/t/tutorial-chaos-cloth-updates-5-8/2729420 ; Login fixes (Jun–Jul 2025): …/error-not-logged-in-5-6/2542895
- License: metahuman.com/license ; unrealengine.com/eula/unreal ; Fab MetaHuman sales: support.fab.com/s/article/Can-I-sell-characters-created-with-MetaHuman-Creator-on-Fab (2025-10-17, date unconfirmed)
- MD DNA importer: support.marvelousdesigner.com/hc/en-us/articles/51752244831897 (2025-10-30, date unconfirmed; MD 2025.2 shipped mid-Nov 2025) ; MD pricing and CLO vs MD (2026-09-18): marvelousdesigner.com/explore/guide/3d-clothing-software-pricing-licensing-models-compared ; clo3d.com/explore/clo-vs-marvelous-designer-software-compared ; MD 2026.0 and Enterprise price: cgchannel.com/2026/04/clo-virtual-fashion-releases-marvelous-designer-2026-0/
- Robust Weight Transfer: github.com/sentfromspacevr/robust-weight-transfer ; Character DNA free (2026-07-17): cgchannel.com/2026/07/the-character-dna-metahuman-add-on-for-blender-is-now-free/ ; Cloth cost (undated, third-party): getperfguard.com/tutorials/chaos-physics ; BG3 presets (2023-07-19): 80.lv/articles/larian-explained-why-there-are-no-face-sliders-in-baldur-s-gate-3

Local (C:/Users/Cody/Desktop/Blender_Projects/):
- FAB_ASSET_STUDY.md, ASSET_GUIDELINES.md, Scripts/pipeline/{export_fbx,qa_check,textures,helpers,lock}.py, Scripts/launch_blender.ps1
- Exports/JinMuWon_v2/{README, CUSTOMIZATION, REVIEW_PLAN}.md, {module_report, asset_report}.json, UnrealDemo/Validation/*.json ; WorkFiles/JinMuWon/checklist_round2/{PAUSED.md, unreal/}
- Exports/CharacterLab/{README.md, Unreal/Validation/male_assembly.json} ; WorkFiles/MetaHuman/{setup_status.json, *.log, male_preview/, preset_thumbnails/} ; WorkFiles/locks/*.json ; Scripts/MetaHuman/*.py
- Exports/{BlackCloak, BlackNunchucks, SnowFlower}/README.md ; References/JinMuWon/design_brief.md ; Backups/BeforeMetaHuman_20260924T185019Z/manifest.json
- C:/Program Files/Epic Games/UE_5.8/Engine/{Build/Build.version, Plugins/(Mutable, ChaosOutfitAsset, MetaHuman/…)/*.uplugin, MetaHumanOutfitPipeline.cpp, MetaHumanInstance.h}

## Review notes

What the verifiers changed:
- Removed "describes MetaHuman as before 5.6". ChatGPT's steps 2–3 match 5.8, and the real gaps are the three things you asked for plus IP.
- Retarget report: added the poster's two-stage workaround and made it a risk to test.
- MetaHuman Instances: now described as Epic documents them in 5.8, including player customization. Heads, skin and nails are marked undocumented.
- Resizing: the runtime answer is dated Sep 12, 2025 (5.6 era), with no 5.8 confirmation.
- Performance: the "Medium for 3–4 characters" advice was moved to its real home (UEFN Export), and Crowds was added.
- Cloud: only auto-rigging and the high-res download need sign-in, and preview textures run locally.
- Backup: it includes the nails but not the skin-tone pass.
- Spike: now multi-day, with per-stage hours and a hold before each step. The fallback is also large.
- Row 2 now allows separate head and body meshes. Row 3 quotes Epic's wording, and the sign-in need for the rig is now [I].
- Leader Pose "Physics: No" is flagged, with a cloth-on-follower test added to the gates.
- Skeleton and Fab IK-bone link added. Seams extended to the shoulders and waist.
- EULA royalty clarified (5% above $1M for UE games). MD Indie, LLC and trial caveats added.
- Tags fixed on items that had no source or only third-party sources. The blue skin in PresetSheet.png is now confirmed as a script bug.
- The wardrobe cloth-loss bug is now "no Epic response as of 2026-09-15".
- Citation dates corrected.
- Added: the sign-in must be done by you, multiplayer as a decision, a concrete FPS target, the prior head-swap approval, the IP gate on both tracks, and the AI-generated reference.
- Animation reframed as unverified (the harness broke). Black eyes are now a possible capture problem. Leader Pose is untested.
- Lock statement corrected. After the run I checked myself: the Blender processes were the smoke-bomb build (files written until 01:35), so its lock is live. The draft's "clear Claude's stale locks" step was removed.
- §7/§9 amendments, triangle breakdown, open review items, weapons (SnowFlower budget and IP, props), the Codex relay, and the LauncherInstalled.dat mismatch added.
- Nail figures are now measured, and "halos" was replaced with the doc's own wording.

Where I departed from the verifiers:
- Kept "at least 2 source bodies" as [V]. I fetched Epic's "Creating Your MetaHuman Characters" page, which says it verbatim.
- Did not tell Codex to switch assembly to Medium. That advice rested on the misattributed UEFN guidance, so the quality level becomes a setting for the performance test to decide.
- Dropped the "5 spine bones vs 3" detail, which the dossier doesn't support.

Still unconfirmed:
- Whether assembly needs the downloaded source textures, and whether a login persists across runs.
- `ik_*` bones on the MetaHuman skeleton.
- Mutable plus animated faces in 5.8, and Mutable's Beta vs production status.
- Runtime resizing in 5.8.
- Head swap through Instances.
- Cloth on Leader Pose followers.
- Selling a lightly edited preset.
- MD eligibility and trial terms.
- Packaging a dedicated server from a Launcher build.
- The hour estimates.