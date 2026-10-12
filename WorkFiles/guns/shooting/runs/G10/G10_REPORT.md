# G10 report: card-shop movement, a real grip, reloads with hands, free look (2026-10-11)

**Result: all four requests are in and pass on the final binaries.** The final check is `finish.json`, 15/15 gates.
Everything below was run fresh on DemoGame_1 `f1a9c29`, in 8 read-only `-game` runs on `L_GunRange`:

- `gun_playtest` F0-F15: 15/15 in each of 3 runs.
- `g9_camera_probe`: 9/9.
- The grip, reload, first-person and free-look probes: all gates pass.
- No warnings or errors from our code in any of the 8 logs, and the repo snapshot was unchanged after every run.

The contact sheet is `finish/contact_sheet_G10_finish.png`. It shows the idle grip, firing, shoulder aim, ADS, the
third-person reload, the first-person reload and free look. The six best frames are in `finish/frames/`. The play guide is
`../G7/HOW_TO_PLAY.md`, rewritten for the new pawn and controls, including Left Alt.

## What the user asked, and what is there now

| Request (2026-10-11) | Now | Key numbers (final runs) |
|---|---|---|
| 1. No ninja movement; move like the card shop's character | The pawn is `BP_GunCharacter`, a child of Epic's `SandboxCharacter_CMC` (UEFN mannequin, GASP motion matching, card-shop camera and keys). It adds only the gun component and the first-person body. The gun layer is a post-process ABP (`ABP_GunCharacter`). | Pawn class checked in every run. Run 500 cm/s and sprint 700 cm/s with the gun out. G10a: holstered pose vs the stock pawn 0.0 cm, gait speeds 0 % off. |
| 2. Grip the gun at idle and when shooting; the left hand was not gripping fully. Keep the hip hold. | Solved finger poses on the AR-01. The left hand wraps the handguard (fingers side by side, thumb under it). The right hand wraps the pistol grip, with the middle finger under the trigger guard and the index pad on the trigger. The right hand slides 1.8 cm down the grip by IK; the gun does not move. | Left fingertips: skin gap <= 0.40 cm (p95), palm on target <= 0.05 cm. Right middle finger top 0.62 cm (the guard bar is at 1.0). Index pad 0.19 cm from the trigger face. Hold vs the baseline 0.016 cm / 0.008 deg. |
| 3. The third-person reload grabbed nothing; check the first-person reload too | The left hand pulls the magazine, drops it, takes a new one from a visible belly pouch and seats it. The empty reload also pulls the charging handle and lets it go. First person (V) has real arms and legs, and shows the same reload. | 3P: hand on the magazine <= 0.70 cm in every carried frame, 0 floating frames, seated 0.0 cm at MagIn. Pouch grab 0.01-0.02 cm. Hand on the charging handle <= 0.23 cm. FP: <= 1.02 cm, reach 0.92, eye to upper arm >= 36 cm. |
| 4. Look around with Alt + mouse without turning the character, like PUBG | Hold Left Alt: the camera orbits (3P) or turns at the eye (V). The body, the movement and the aim stay put, and shots still go to the aim. Release snaps back. Ignored while aiming; RMB ends it. | Control and actor yaw change 0.000 deg; camera +90 deg. Shot 0.00004 deg off the aim. Run / sprint heading drift 0 deg. The wall stops the camera. Back on the aim 2 frames after the release. |

Still working as before: the gun is drawn at spawn, the over-the-shoulder camera, hold RMB for shoulder aim, tap RMB to
toggle ADS, X holster / draw, LMB fire, R reload, B selector, V first person. All of these are covered by the play test
F0-F13 and by g9.

## Stages and commits

| Stage | DemoGame_1 commit | Gates | Results |
|---|---|---|---|
| Plan, read-only probes | `de3d75b` | - | `g10_probe_*`, `G10_PLAN.md` |
| G10a pawn (card-shop child, post-process gun layer, retargeted rifle clips) | `58da578` | 17/18 (barrel yaw 5.95 deg vs a 3 deg target; hold kept as asked) | `pawn.json`, `pawn/` |
| G10b grip, rounds 1-3 | `500d840`, `5ea0de6`, `9c61ad1` | 11/11, 17/17, 14/15 (F7 dropped-magazine physics flake, fixed in G10c) | `grip*.json`, `grip*/` |
| G10c reload with hands + FP arms; fix rounds 1-2 | `d1b4add`, `052dcbb`, `319a927` | 13/14, 17/17, 16/16 | `reload*.json`, `reload*/` |
| G10e free look | `f1a9c29` | 19/19 | `freelook.json`, `freelook/` |
| Fire sound (separate) | `dbb3504` | - | CC0 AK single shot |
| **G10 finish** (this report) | none (nothing changed) | **15/15** | `finish.json`, `finish/` |

The G10 commits touch only `Content/Guns`, `Source/DemoGame_1/Guns` and `Tools/Claude/Guns` (61 files). The other chat's
uncommitted DemoGame_1 work (BP_NinjaGasp, IMC_NinjaGasp, combat, slash arc, Mimic) was not touched.

## Final regression (finish.json)

| Gate | Value | Bar |
|---|---|---|
| gun_playtest F0-F15, 3 runs | 15/15, 15/15, 15/15 | 15/15 each |
| g9_camera_probe | 9/9 | 9/9 |
| Grip, left hand (all phases) | tip gap median <= 0.352, p95 <= 0.395 cm; palm <= 0.049 cm; penetration <= 0.22 cm | <= 0.5 / 0.5 / 1.0 / 0.5 |
| Grip, right hand | middle finger top 0.617 cm; index pad 0.188 cm; index tip y -0.626 | <= 1.0 / 0.25 / -0.5 |
| Hip hold unchanged | 0.016 cm / 0.008 deg vs G10b base; root error 0 | <= 0.2 / 0.2 |
| 3P reload (tactical / empty) | hand on magazine max 0.696 / 0.567 cm; 0 floating; seated 0.0 cm; pouch 0.009 / 0.017 cm; charge 0.228 cm; release 0.67 cm with the handle 10.9 cm away | <= 2.0; 0; <= 0.05; <= 1.0; <= 2.0 |
| FP reload | hand on magazine max 1.019 cm; 0 floating; seated 0.0; reach 0.92; root error 0 | <= 2.0; 0; <= 0.05; <= 0.97; <= 0.5 |
| FP views | palm 0.30 cm; reach <= 0.93; eye to upper arm >= 36.4 cm; legs 7/7 in V, hidden in 3P | <= 1.0; 0.97; >= 30 |
| Free look | control 0, actor 0, camera 90 deg, radius 0 cm; shot 0.00004 deg / 0.001 cm; run / sprint drift 0; V at the eye 0 cm; holstered same; ignored in aim; wall clear; release in 2 frames | as in G10e |
| Logs (8 runs) | 0 from our code, 0 Accessed None | 0 |
| Repo guard (8 runs) | 0 snapshot differences | 0 |
| Frames looked at | contact sheet | the four requests visible |

The remaining warnings in the logs are all stock and the same in every run (108-109 lines per log):

- Python init tracebacks from Epic's experimental Toolsets plugins at startup;
- LogEditorDataStorageUI;
- LogPoseSearch "databases still building" in GASP's first seconds;
- LogConsoleManager GASP cvars;
- one LogTextureGraph line.

## Honest notes and open items

- **Plan gap: F16-F20 are not in `gun_playtest.py`.** These are the plan's grip, reload hands, FP arms, free look and
  card-shop parity gates. The dedicated probes re-run here cover them. Card-shop parity was not re-measured here; the
  0.0 cm figure is from G10a.
- **F14 performance is reported only.** A burst costs 1.4-1.6 ms per frame more than idle: mean 6.5 ms, max 16-19 ms,
  no hitches.
- **The play-test script logs one Python DeprecationWarning of its own** (`TraceTypeQuery1`). It comes from the test
  script, not the game.
- **The hip hold was not changed, as asked.** The barrel points 5.95 deg left of the aim at the hip, and the shoulder
  camera sees most of the rifle behind the body from the hip.
- **Placeholders:**
  - only the fire sound is in: no magazine, bolt or selector foley;
  - the reserve is infinite;
  - the poses are solved for the AR-01 only;
  - in V, free look turns the gun out of the view, and at about 30 deg off the aim it looks a little large.
- **Multiplayer is not exercised.** Shots are built on the client from the aim view.
- **Nothing was merged or pushed.** That waits for the user's go.

## How the finish was run

- `run_guns.ps1 -Mode game -ReadOnly -ResX 1920 -ResY 1080`, with these tags:
  - `G10f_pt1`, `G10f_pt2`, `G10f_pt3`: gun_playtest + g7_analyse;
  - `G10f_g9`;
  - `G10f_grip`, measured with `g10b_grip_solve_r3.py measure` against pose r3, base G10b_base;
  - `G10f_reload`;
  - `G10f_freelook`;
  - `G10f_views`.
- The log scan writes `finish/logscan.json`.
- `finish/make_finish_sheet.py` draws the contact sheet.
- Each run's guard log is in `finish/*.guard.txt`.
