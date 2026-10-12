# How to play the AR-01 range (shooting prototype, updated for G10, 2026-10-11)

## Open it

1. Open `DemoGame_1` in Unreal Editor 5.8.
2. In the Content Browser, open `/Game/Maps/L_GunRange` (Content > Maps > L_GunRange).
3. Press **Play** (PIE or Standalone Game). The map's World Settings use `GM_GunRange`, so you spawn on the firing line,
   looking down range, as **`BP_GunCharacter`**, with the rifle already in your hands.

`BP_GunCharacter` (G10) is the card-shop character: a child of Epic's Game Animation Sample pawn `SandboxCharacter_CMC`.
It uses the same mannequin, motion-matched movement, camera and keys as the card shop. Nothing comes from the ninja: no
jutsu, combat, stances or ninja animations. The only things added are the gun component and its first-person arms.

Nothing else in the game changed. `L_NinjaTest`, `BP_NinjaGasp` and its inputs are untouched. The older ninja gun pawn
`BP_NinjaGasp_Gun` is still in the project but is no longer used by this map.

## Controls

**Moving (the card shop's keys)**

| Key | Action |
|---|---|
| **W A S D** | Move (the default pace is a run) |
| **Left Shift, hold** | Sprint (it also takes you out of the sights) |
| **Left Ctrl, hold** | Walk |
| **C** | Crouch |
| **Space** | Jump, or vault / climb over obstacles (GASP traversal) |
| **Mouse** | Look. With the gun out, the body turns to face where you aim |

**Using the gun**

| Key | Action |
|---|---|
| **X** | Holster or draw the rifle (you start with it drawn) |
| **Left mouse** | Fire. Hold for full auto; in semi, one shot per press |
| **Right mouse, hold** | Shoulder aim: the camera moves in over the right shoulder and the spread tightens, for as long as you hold |
| **Right mouse, tap** | Aim down the sights. Tap again to leave; a sprint also leaves them |
| **R** | Reload. With rounds left (tactical): 30+1. When empty, the left hand also pulls the charging handle: 29+1 |
| **B** | Fire selector, in the real AK lever order: Safe -> Auto -> Semi -> Safe (the lever on the gun moves too) |
| **V** | First-person view on or off. You see your own arms holding the gun, your legs when you look down, and the reload |
| **Left Alt, hold + mouse** | **Free look, as in PUBG.** The camera looks around (up to 170 deg to either side, 60 deg up or down) while the body keeps facing and moving where it was. The gun stays on its aim, so shots still go there, and the crosshair hides. Let go of Alt and the view snaps back to the aim. Works while running and sprinting, holstered, and in V. It is ignored while you aim, and pressing RMB ends it |

While the rifle is out, LMB and RMB belong to the gun. Holster with X to give them back to the character.

## What you will see (G10)

- **Grip:** the left hand wraps the handguard with all four fingers side by side and the thumb underneath. The right
  hand wraps the pistol grip, and only the index finger is inside the trigger guard. The grip is the same at idle,
  walking, firing and in shoulder aim. The hip hold position itself was not changed.
- **Reload, third person:** the left hand takes the old magazine out and drops it. It then fetches a fresh magazine from
  the pouch on the belly (the pouch shows one magazine fewer while you carry it) and seats it. On an empty reload the hand
  then pulls the charging handle and lets it go.
- **Reload, first person (V):** the gun tilts, and you see the left hand pull the old magazine and bring the new one in.

## What is on the range

- Training dummies at **10 m, 25 m and 50 m**. Each hit does 34 damage (3 hits kill), and they get up again after 3 s.
- Four 1 m target boards at 15 m: **concrete, steel, wood and glass**. Each has its own impact effect and bullet hole.
- A wall at 20 m for the spread pattern.
- A low cover block 1.5 m in front of the line, on the left. Shoot over it with the muzzle behind it and the rounds hit
  the cover.
- A black panel with a white card at 25 m for the sight picture, and distance markers every 5 m.

## What is still placeholder

- **Sound:** only the fire sound is in: a CC0 AK single shot (DemoGame_1 commit dbb3504). There is no magazine, bolt,
  charging-handle or selector sound yet, and no footstep or handling sound tied to the gun.
- **Infinite reserve:** 30+1 in the gun, and the reserve never runs out.
- **The hip hold** is still the template rifle's hold, left as asked. The barrel points about 6 deg left of the aim at
  the hip, and the over-the-shoulder camera sees most of the rifle behind the body. Hold RMB to see it clearly.
- **The grip and reload hand poses are solved for the AR-01 only.** Another gun will need its own solve.
- **Free look in first person:** when you turn far to the side, the gun and arms leave the view, because they stay on
  the aim. At about 30 deg off the aim the first-person gun looks a little large.
- **The bloom never builds up in full auto** with the current numbers. Each shot adds 0.25 deg, but the bloom fades at
  4 deg/s, which removes 0.4 deg between two shots at 600 rpm. A fade delay or a slower fade rate would fix it.

## Console helpers (press the ` key in PIE)

- `ninja.gun.debug 1` logs every shot, event and reload as `NGUN` lines; `2` also draws the traces.
- `ninja.gun.nospread 1` sends every round exactly along the aim.
- `ninja.gun.infiniteammo 1` stops the magazine from emptying (`0` counts rounds, `-1` uses the gun's own rule).

## Test harness (close the editor first)

```
Tools/Claude/Guns/run_guns.ps1 -Mode game -Script gun_playtest.py        -Tag G10f_pt1      -ReadOnly -ResX 1920 -ResY 1080
py -3 -B Tools/Claude/Guns/g7_analyse.py C:/Users/Cody/AppData/Local/Temp/ClaudeGuns/G10f_pt1
Tools/Claude/Guns/run_guns.ps1 -Mode game -Script g9_camera_probe.py     -Tag G10f_g9       -ReadOnly -ResX 1920 -ResY 1080
Tools/Claude/Guns/run_guns.ps1 -Mode game -Script g10b_grip_probe_game.py   -Tag G10f_grip  -ReadOnly -ResX 1920 -ResY 1080
Tools/Claude/Guns/run_guns.ps1 -Mode game -Script g10e_reload_probe_game.py -Tag G10f_reload -ReadOnly -ResX 1920 -ResY 1080
Tools/Claude/Guns/run_guns.ps1 -Mode game -Script g10_freelook_probe.py  -Tag G10f_freelook -ReadOnly -ResX 1920 -ResY 1080
```

The latest results are in `WorkFiles/guns/shooting/runs/G10/G10_REPORT.md`: play test 15/15 three times, g9 9/9, and
grip, reload and free look all passing.
