# How to play the AR-01 range (shooting prototype, step G7)

## Open it

1. Open `DemoGame_1` in Unreal Editor 5.8.
2. In the Content Browser open `/Game/Maps/L_GunRange` (Content > Maps > L_GunRange).
3. Press **Play** (PIE, or Standalone Game). The map's World Settings already use `GM_GunRange`, so you spawn as
   `BP_NinjaGasp_Gun` (the ninja with the gun holder) on the firing line, looking down range.

Nothing else in the game changed: `L_NinjaTest`, `BP_NinjaGasp` and its inputs are untouched. The gun lives only on this
map's pawn.

## Controls

| Key | Action |
|---|---|
| **X** | Holster / draw the rifle (it starts in your hands) |
| **Left mouse** | Fire (hold for full auto, one shot per press in semi) |
| **Right mouse, hold** | Shoulder aim: the camera comes in over the right shoulder (tighter spread) while held |
| **Right mouse, tap** | Aim down the sights; tap again (or press RMB) to leave. A sprint also leaves them |
| **R** | Reload (tactical with rounds left: 30+1; empty: the bolt is charged, 29+1) |
| **B** | Fire selector, in the real AK lever order: Safe -> Auto -> Semi -> Safe (the lever on the gun moves too) |
| **V** | First-person view toggle (experimental, step G9; not tested yet) |
| **Left Alt, hold + mouse** | Free look (G10e, like PUBG): the camera looks around while the body keeps facing and moving where it was and the gun stays on its aim (shots go there, the crosshair hides). Release = back to the aim. Works holstered and in V; ignored while aiming (RMB ends it) |
| WASD, mouse, Shift... | The normal ninja movement and camera |

While the rifle is out, LMB and RMB belong to the gun (no combo / block). Holster with X to get them back.

## What is on the range

- Training dummies at **10 m, 25 m and 50 m**: 34 damage per hit (3 hits kill), they get up again after 3 s.
- Four 1 m target boards at 15 m: **concrete, steel, wood, glass** (each has its own impact effect and bullet hole).
- A wall at 20 m (spread pattern), a low cover block 1.5 m in front of the line on the left (shoot over it with the
  muzzle behind it and the rounds hit the cover), a black panel with a white card at 25 m (sight picture), distance
  markers every 5 m.

## What is placeholder

- **Silent**: the sound slots are empty until real gun audio is supplied.
- **Hands**: the third-person hold / fire / reload poses are Epic's template rifle clips; in ADS the rifle shows without
  arms (step G8 adds first-person arms).
- **Infinite reserve** (30+1 in the gun, reserve never runs out).
- **Reload hands**: the magazine drops out and the new one seats (the gun's own clip), but the left hand does not carry
  the magazine (Epic's body reload clip is used and the hand IK is switched off for the reload).

## Things you will notice (found by the G7 play test, left for the tuning step G9)

- **Camera (fixed 2026-10-11):** with the gun out the camera sits over the right shoulder (DemoGame_1 commit 1670bc0, probe g9_camera_probe.py 9/9). From the hip the template hold pose still keeps most of the rifle in front of the chest; hold RMB to see it clearly.
  and the body turns to face the camera while the gun is out, so the hip-held rifle is behind the body (only its shadow,
  the flash and the tracers show). An over-the-shoulder camera offset fixes it; that is a tuning choice for G9.
- **Bloom never builds up in full auto** with the current numbers: each shot adds 0.25 deg but it fades at 4 deg/s, which
  is 0.4 deg between two shots at 600 rpm. If you want the cone to grow during a long burst, the fade needs a delay
  (like the recoil's) or a slower rate.

## Console helpers (press the ` key in PIE)

- `ninja.gun.debug 1` logs every shot / event / reload as `NGUN` lines; `2` also draws the traces.
- `ninja.gun.nospread 1` every round flies exactly along the aim.
- `ninja.gun.infiniteammo 1` the magazine never empties (`0` counts rounds, `-1` the gun's own rule).

## Test harness

The automated play test is `Tools/Claude/Guns/gun_playtest.py` (run with the editor closed):

```
Tools/Claude/Guns/run_guns.ps1 -Mode game -Script gun_playtest.py -Tag G7 -ReadOnly -ResX 1920 -ResY 1080
py -3 -B Tools/Claude/Guns/g7_analyse.py C:/Users/Cody/AppData/Local/Temp/ClaudeGuns/G7
```
