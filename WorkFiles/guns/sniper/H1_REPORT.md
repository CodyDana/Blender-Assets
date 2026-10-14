# SR01 H1 full: the player's hands on the shipped SK_SR01 (Blender, 2026-10-14)

Script: `Scripts/guns/sniper/sr_h1_full.py`, a port of `smg_h1_full.py`. Run it with:

    blender -b References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend --factory-startup --python Scripts/guns/sniper/sr_h1_full.py

Gate file: `gates/h1_full.json`. It also records the sha256 of the fit body (matches `base_lock.json`) and of the
gun bytes. Renders: `Renders/Guns/SR01/h1_{A,B}_{side,fp,grip_right,support_left}.png`.

The fit body was already in the worktree, so no LFS pull was needed. The gun is the **shipped** set:
- `Exports/Guns/SR01/SK_SR01.fbx` (LOD0). The import is in frame B; the trigger bone head matches the sidecar to
  0.0 mm. Each part is the set of vertices weighted to its bone.
- The clip extremes come from the shipped clip FBX files.
- `SM_SR01_Mag.fbx` sits on the `magazine` bone.
- `SM_Att_Scope_LongRange.fbx` sits on `Rail_Top` + 2 slots.

Nothing in `Exports/` was written apart from the README note.

## Result: 9 of 10 gate rows pass; `ik_left_A` fails (a reach problem, not an intersection)

| Row | Value | Bar | Pass |
|---|---|---|---|
| Right palm penetration | 0.0 mm | <= 1 mm | yes |
| Index pad to trigger face (rest curl, finger clear of the frame by 0.21 mm) | 0.715 mm | 0..3 mm | yes |
| Left palm, pose A (`SupportHand`) / pose B (`SupportHandBipod`) | 0.0 / 0.0 mm | <= 1 mm | yes |
| Hand-gun triangle pairs / penetrations: right hand at 10 states, left A at 9, left B at 7 | 0 everywhere (right-hand min gap 0.21 mm) | 0 | yes |
| Right-arm two-bone IK to the held grip (EyePoint on the right eye) | 0.0 mm, elbow 120.3 deg | < 0.5 mm, 0..150 deg | yes |
| Left-arm IK, pose A (`SupportHand`) | **76.6 mm short**, arm straight | < 0.5 mm | **no** |
| Left-arm IK, pose B (`SupportHandBipod`) | 0.0 mm, elbow 135.2 deg | < 0.5 mm, 0..150 deg | yes |
| Grip girth at 46 mm below the web point | 165.9 mm (25 mm: 235.2, where the section takes in more than the grip; 70 mm: 171.2) | <= 167 mm | yes |
| Trigger reach (spec web point to the blade face) | 44.7 mm (same as the W1 early H1) | <= 80 mm | yes |

The 10 states are: rest, bolt unlocked, bolt back (88.0 mm measured), trigger pulled, SAFE, paddle pressed, magazine
out, riser up, riser down, bipod deployed. Each comes from the shipped clips: BoltCycle f6 / f14, Fire f2,
Selector f10, Reload f3, CheekRiser f8 / f18, BipodDeploy f36.

## Reported numbers

- **Length of pull:** 358.2 mm, from the trigger blade face (B X 61.07) to the butt-pad rear (B X -297.13). The
  real-world range is 330-370 mm.
- **Eye relief:** 95.0 mm by design (EyePoint to Sight). Measured from the EyePoint to the scope's rearmost vertex,
  it is 95.02 mm.
- **Upright body, eye on EyePoint:** the butt pad sits 154.1 mm above, 76.2 mm left of and 144.5 mm behind the
  shoulder-pocket skin. The shooter closes this gap by dropping and canting the head onto the comb and raising the
  shoulder. If the gun instead slid forward until the butt met the pocket, eye relief would be 239.5 mm.
- **Cheek riser:**
  - At rest the eye sits 25.5 mm above the riser top.
  - With the fit body's upright face on EyePoint, the face sits inside the rest riser: 14.5 mm under the eye,
    growing to 41.1 mm at the riser's rear end (105 mm behind the eye). Only the riser front, 23 mm ahead of the eye,
    clears (-0.4 mm).
  - The riser drops at most 12.9 mm, which leaves the eye 38.4 mm above the comb: **1.6 mm short** under the eye,
    and the rear portion stays in the jaw.
  - I searched head poses (cant and nod about `neck_01`, 0-40 deg) for one that puts the face on the comb within
    the riser travel. None does: nodding sinks the jaw further, and the best gap is -40.8 mm at 5 deg cant.
- **Grip seat:** the palm centre sits on `Grip` (0 offset). The `Grip` frame in `hand_r` is location
  (-44.16, -53.36, 6.41) mm, quaternion wxyz (0.0290, 0.1311, 0.0861, 0.9872). The finger rotations are in the JSON
  (`hand_offset`).

## Socket proposals (measured; NOT applied; the exports stay as Unreal verified them at W5)

| Socket | Now (B mm) | Proposal | Why |
|---|---|---|---|
| `SupportHand` | (342.87, 0, 50.53) | X <= **259.9** for a square stance, or keep X with a 23 deg bladed torso; Z **40.90** | In the square stance the left arm (562.6 mm) falls 83 mm short of the seated hold. The socket also sits 9.6 mm inside the forend, above the band face the palm rests on. |
| `SupportHandBipod` | (-179.13, 0, 4.13) | Z **-33.99** | The socket is 38.1 mm inside the butt; the palm rests on the underside at Z -33.99. |
| `Grip` | (0, 0, 0) | keep | The hand seats with the palm centre on it (0 offsets). |
| `Shoulder` | (-297.13, 0, 27.53) | keep | It is the butt-pad rear centre. The pocket offset is a posture matter, not a socket error. |

Which `SupportHand` X to use depends on the game's stance. The SMG passed with a square-stance assumption. A sniper
standing hold normally blades the torso, and 23 deg of shoulder yaw closes the gap (elbow 5.7 deg, nearly straight).

## Method changes from the SMG (and why)

1. **Right-hand seat.** The SMG's rules (thenar 0.3 mm off the back strap, or the web in the hollow) can't be met with
   this body and grip:
   - The rest thumb lies across the grip's left side: run 1 found the thenar 9.5 mm inside at both ends of the push.
   - The web stays in the palm plane, beside the back strap: in runs 4-5 it was never within 2.4 mm over a 60 mm
     sweep.

   A 2-D Newton solve diverged, because signed gaps deep inside the mesh have no usable gradient. The seat now follows
   the SMG's stated rule, the **palm centre on the Grip origin**. Offsets of 0 / ±4 / ±8 mm axially and fore-aft are
   tried, the gun is pushed to 0.3 mm palm-side contact, and the nearest clear seat is used: 0 / 0. The
   web-on-hollow seats stay in the JSON as alternatives.
2. **Thumb.** The SMG's smallest-rotation thumb pointed forward under the trigger guard. I now aim it at the grip's
   left face, and tried every clear seat plus the hand turned ±15/30/45 deg about the grip axis. **No clear pose
   lets the thumb wrap the left side**: the tip ends 13-68 mm out on the gun's right. This is a limit of
   MH_PlayerDefault's rest thumb in this method (`thumb_01` grid ±70 deg), so I stopped there. The engine hand pose
   (U11) needs its own thumb-over or thumb-wrap.
3. **Left hands.** The SMG checked only the IK reach to `SupportHand`. Here both supports also get a palm-up seat:
   knuckle line along the bore, fingers round the gun's right side, socket over the palm centre, push to 0.3 mm, all
   fingers and the thumb curled to 0.5 mm, and the same intersection checks.
4. **Eye.** The eye is the cornea of the right eyeball mesh in `FIT_..._HeadParts` (world -33.3, -103.3, 1744.9).
   The SMG used a fixed offset from the head joint.

## Limits / what is left

- Pose B uses the standing upper body as a stand-in for prone: the hand-to-gun and gun-to-eye relations are what's
  gated, and the torso and legs aren't posed prone. In the renders the arms are posed analytically (two-bone, elbow
  pole down and out). In pose A the left hand stops 76.6 mm short of `SupportHand`, so the close-up shows it on the
  forend just ahead of the magazine.
- The renders keep the head upright (no cheek-weld pose was found), so the stock visibly passes through the jaw. That
  is the riser finding above, not a render fault.
- U11 in Unreal (the hand fit on the player MetaHuman in-engine) is still not run.
- Scratch from this round (logs of runs 1-14, debug hold views) is in `WorkFiles/guns/sniper/scratch/h1/` (not in git).
