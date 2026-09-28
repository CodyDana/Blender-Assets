# Snow Flower heels: MH_PlayerFemale's feet, the heel, and the foot-pose correction

2026-09-27, role "female fitting body + heel pose". Every number below is in `heel_pose.json` (same folder), written by
`Scripts/SnowFlowerHeels/heel_pose.py` and checked with Unreal's own math by `Scripts/SnowFlowerHeels/ue_verify_heel_pose.py`
(`ue_verify_heel_pose.json`: PASS, worst position error 0.028 mm, rotators identical to 1e-4 deg).

Conventions: Blender = metres, Z up, she faces -Y, +X is HER LEFT. "UE cm" = Unreal component space (cm, Y mirrored:
`ue = (x, -y, z) * 100`). Bone-local points are in the Unreal bone's own frame (cm), usable directly in a Control Rig.

---

## 1. The locked female fitting body (built)

`References/Characters/MH_PlayerFemale/`, same layout as the male base:

| Item | Value |
|---|---|
| `MH_PlayerFemale_FitBody.blend` | sha256 `b35c9247e248aded77b1e80d3482b8fe4f6114f4e12b05d98f807ac4937b6bec`, collection `FITBODY_MH_PlayerFemale` (root, Body, Head, HeadParts, HairProxy, HairCards; all unselectable) |
| `base_lock.json` | skeleton hash `9c994c38cfadb8b4fedacf996fcb5f5d09fd9c2c33e5daabdf99890871dc47c5` (the male's is `b6e1cbf5...`: same bone names, different rest, so a garment is gated per base) |
| Skeleton | `/Game/MetaHumans/Common/Female/Medium/NormalWeight/Body/metahuman_base_skel`, 342 bones incl. root, no `ik_*`; matches Unreal's reference skeleton to 0.00035 mm |
| Physics asset | `/Game/MetaHumans/MH_PlayerFemale/Body/PHYS_MH_PlayerFemale` |
| LOD0 triangles | body 60,816 + face 34,514 + hair cards 34,790 (two groups, 11,830 + 22,980) = **130,120** (budget 160k leaves 29,880 for her whole loadout; the heels at 2 x 8-14k fit) |
| Hair proxy | `Hair_L_Straight_Helmet_LOD5`, rim closed, pushed out 12.2 mm: holds 89.3 % of the LOD0 card vertices (long hair hangs outside the helmet; the male's BrushCut was 99.4 %). Only matters for hats. |
| `source/` | body/face FBX exported from CharacterLab 2026-09-27 (`SKM_MH_PlayerFemale_BodyMesh.fbx` sha `503d78f0...`, `..._FaceMesh.fbx` sha `12224a50...`, pinned in `build_fitbody.py`), groom FBX x3, `ue_reference.json`, `bones.json` |

Her MetaHuman assets were only read: the CharacterLab wrapper hashed all 342 files of `Content/MetaHumans` before and after
each run (0 changed, 0 new files) for the export and both verify runs.

Script changes that made this possible (male path unchanged):
- `Scripts/garments/ue_export_fitbody.py`: `FITBODY_BASE` env var + a `BASES` table; for the female it also writes the
  body/face FBX (the male's came from DemoGame_1's exporter).
- `Scripts/garments/build_fitbody.py`: `BASES` table (sources, bones.json, groom files; several card groups are joined).
- `Scripts/garments/run_ue_characterlab.ps1`: new `-Render` switch (offscreen RHI). **Trap:** a skeletal-mesh FBX export
  under `-nullrhi` dies on `Assertion failed: MeshObject` (SkinnedMeshComponent.cpp:4987, via MeshMergeUtilities).

Rebuild: `$env:FITBODY_BASE="MH_PlayerFemale"; run_ue_characterlab.ps1 -Script Scripts/garments/ue_export_fitbody.py -Tag fitbody_export_female_r -Render`,
then `blender -b --factory-startup --python Scripts/garments/build_fitbody.py -- --base MH_PlayerFemale --force`.

---

## 2. Her feet (rest, barefoot) - measured on the skinned LOD0 body

Left and right agree to 0.05 mm; left values:

| Measure | Value |
|---|---|
| Foot length (heel back to toe tip, along the foot axis) | **242.4 mm** (EU ~38 / US W 7.5) |
| Foot width (widest, below 45 mm) | **85.6 mm** |
| Toe-out (foot axis vs straight ahead) | 9.86 deg |
| Ankle height (`foot_l` head above the lowest sole skin) | **75.35 mm** |
| Ball joint height (`ball_l` head) | 11.96 mm |
| Ball joint from heel back / ankle from heel back | 178.4 mm / 45.8 mm |
| Heel contact centroid to ball contact centroid (horizontal) | 150.0 mm |
| Lowest sole skin | -3.1 mm (the rest mesh sinks 3 mm into z = 0; the floor stays z = 0) |
| `foot_l` head | (0.13362, -0.00209, 0.07223) m |
| `ball_l` head | (0.15634, -0.13275, 0.00884) m |
| Heel contact centroid (rest) | (0.14744, 0.01086, 0.0) m = UE (14.744, -1.087, -0.001) cm |
| Ball contact centroid (rest, = the pivot) | (0.18910, -0.13321, -0.00056) m = UE (18.910, 13.322, -0.056) cm |
| Unreal local rest of `foot_l` / `ball_l` | rotator (roll 0, pitch -2.823, yaw 0) / (0, 0, 90); full transforms in `heel_pose.json` `ue_bones.*.local_rest` |

Right foot = mirror (heel contact UE (-14.740, -1.086, -0.002), ball (-18.908, 13.326, -0.055)). All four bone matrices
(`pelvis`, `thigh`, `calf`, `foot`, `ball` x2) are in `bones_rest`.

---

## 3. The heel, derived from the reference

The reference is the only source: black pointed-toe stiletto pumps, 3/4 views. Measured on the rear (right-hand) shoe,
original pixels: heel top-lift bottom y = 790, heel-to-counter junction y ~480 (vertical heel ~310-315 px), heel tip to toe
tip on the ground (605, 232) px. The ground line is foreshortened, so the height depends on the camera elevation e:

| Elevation assumed | Heel height for her foot |
|---|---|
| 14.5 deg (from the ankle-strap loop read as a level circle; the strap is probably tilted, so a floor) | ~73 mm |
| 20 deg (fits how far we see into the shoe and the ~48 deg yaw of the shoe to the image plane) | **~88-90 mm** |
| 25 deg | ~100 mm |

The model for the conversion: heel tip to toe tip on the ground = heel-to-ball run in the shoe + ball to pointed tip
(~100 mm: toes ~65 mm past the ball plus a ~35 mm pointed toe). DemoGame_1's catwalk clip (copied from a real heeled walk)
plants the heel at ~34 deg "about a 9 cm heel" - the same answer from an independent source. **Design value: 90 mm heel
height** (standard: ground to the heel seat at the back). Plausible range 80-100 mm; if the builder's side-by-side with the
reference argues otherwise, re-run `heel_pose.py --heel-mm N` (everything below follows).

Design constants (all in `heel_pose.json` `design`):

| Constant | Value | Why |
|---|---|---|
| Heel height | 90 mm | above |
| Seat drop to the heel's weight-bearing point | 2 mm | the seat under the heel pad sits a little below its rear edge |
| Insole over the seat | 2 mm | |
| => heel contact target | **90.0 mm** above the floor | tracked point = centroid of the rest heel contact patch |
| Forefoot outsole + insole | 4 + 2 = **6 mm** | thin pump sole seen in the reference; the lowest forefoot skin sits on it |
| Toe spring (outsole tip above ground) | 8 mm | the reference's toe tips just clear the ground |
| Toes inside the shoe | 3 deg up from level | they ride the first ~5 cm of that rise |

Results of the solve (on the skinned mesh, both feet; left shown, right within 0.02 deg / 0.03 mm):

| Result | Value |
|---|---|
| **Foot pitch** (`foot_*` rotation about the lateral axis, toes down, pivot = ball contact) | **33.67 deg** |
| Foot lift after the pitch (`dz`) | 7.45 mm |
| Heel-contact to ball-contact incline (skin) | 31.56 deg; run 129.7 mm |
| Ball bend (`ball_*` vs `foot_*`) | **36.67 deg** dorsiflexion (33.67 back to level + 3 toe spring) |
| Heel contact / lowest forefoot skin / ball contact centroid / lowest toe | 90.00 / 6.00 / 10.29 / 6.19 mm |
| Heel pad lowest point | 72.0 mm (the pad's front edge rests on the inclined shank, not on the seat) |
| Ankle (`foot_*` head) | rises 72.1 mm (to 144.4 mm) and moves 63.6 mm forward |
| **Pelvis lift** | **71.00 mm** (reach-preserving; both legs keep their rest hip-ankle distance) |
| Legs | thigh and calf each swing 4.46 deg forward about the lateral axis (knee moves 79 mm); knee bend 1.03 -> 1.09 deg |
| Posed foot box (left) | x 0.115..0.209, y -0.205..0.007, z 0.006..0.153 m |

Her eyes end up 71 mm higher; the capsule and root do not move.

---

## 4. The foot-pose correction (what ships)

### 4.1 Unreal numbers for the standing pose

Component-space deltas (UE axes; right = mirror):

| Bone | Delta |
|---|---|
| `pelvis` | translate Z **+7.0996 cm**, no rotation |
| `thigh_l` | 4.46 deg about (0.9838, -0.1718, 0.0508) |
| `calf_l` | 4.41 deg about the same axis; head moves (0.570, 3.287, 7.189) cm |
| `foot_l` | **33.669 deg** about **(-0.98522, 0.17130, 0)** (the lateral axis, sign = toes down), pivot UE (18.910, 13.322, -0.056) cm, then +0.745 cm Z |
| `ball_l` | 3.0 deg toes-up in component space (= level + toe spring); local delta vs foot 36.67 deg |

Local (parent-relative) posed rotators, UE FRotator (roll, pitch, yaw):
`thigh_l` (8.2346, 3.4406, -5.2717) [rest (8.4751, 2.6782, -0.8690)], `calf_l` (0, 0, 1.0849) [rest (0, 0, 1.0332)],
`foot_l` (-1.8816, -3.1829, 38.1268) [rest (0, -2.823, 0)], `ball_l` (0.8122, 0.2400, 53.3418) [rest (0, 0, 90)];
right: `thigh_r` (8.2360, 3.4364, 174.7517), `calf_r` (0, 0, 1.0339), `foot_r` (-1.8793, -3.1765, 38.1555),
`ball_r` (0.8059, 0.2381, 53.3402). Quaternions and locations: `heel_pose.json` `ue_bones.*.local_posed`.

### 4.2 Bone-local constants the runtime needs (UE cm, left; right = negated, see json)

| Constant | In bone | Value |
|---|---|---|
| Barefoot heel contact | `foot_l` | (-7.2543, -0.8482, -1.5585) |
| Barefoot ball contact (the pivot) | `foot_l` | (-6.8394, 14.0122, -3.5443) |
| Barefoot ball contact | `ball_l` | (0.5603, 0.9219, -3.2328) |
| Shoe heel tip on the floor (under the heel contact) | `foot_l` | (-14.5832, 4.3744, -1.6755) |
| Shoe ball sole on the floor | `ball_l` | (0.3642, 1.8196, -3.2276) |
| Rest incline of the rigid heel->ball contact line | - | +0.207 deg |
| HeelPitchDeg / BallLiftCm / ToeSpringDeg | - | 33.67 / 0.745 / 3.0 |

Unreal check (fresh commandlet): with the posed locals, the shoe heel tip and ball sole land at z = 0.0000 / -0.0003 cm
and the ankle within 0.028 mm of Blender's.

### 4.3 The per-frame algorithm (component space, after the retarget)

Per foot, with `HeelAlpha` (0 barefoot, 1 in these heels):

1. `H` = foot cs * barefoot heel contact, `B` = foot cs * barefoot ball contact (rigid points), `f` = horizontal(B - H),
   `a` = normalize(up x f).
2. `phi` = atan2(H.z - B.z, |B - H|horizontal) - 0.207 deg (the animation's own heel lift).
3. `delta` = HeelAlpha * softmax0(HeelPitchDeg - phi) (soft clamp at 0 over ~4 deg, so a heel-raised clip - the catwalk,
   planted at ~34 deg - gets ~0 and is left alone).
4. foot' = Translate(0, 0, HeelAlpha * BallLiftCm) * RotateAbout(B, a, delta) * foot.
5. ball keeps its animated component rotation, plus ToeSpringDeg toes-up about `a` (so the toes never go through the insole).
6. **Floor clamp** (only while the barefoot foot is grounded: lowest of H, B within 2 cm of the floor, fading out by 4 cm):
   drop/raise foot' so the lower of {shoe heel tip, shoe ball sole} (bone-local constants above) is at the animation's
   contact height. This keeps the heel tip on the floor at heel strike (the heel rocker, where the ball is in the air).
7. Pelvis lift = min over GROUNDED feet of the reach-preserving lift `A'.z - hip.z + sqrt(L^2 - horiz(hip, A')^2)`
   (L = animated hip->ankle distance, A' = corrected ankle, hip = thigh head), clamped to [0, 7.10 cm], smoothed by a
   critically damped spring (~0.1 s); with no grounded foot hold the last value. Standing flat gives exactly 7.10 cm.
8. Two-bone IK thigh/calf per leg to foot' (pole = the animated knee), then set foot' and ball.

Expected: the animation's ball contacts stay where the clip put them (no ball slide); the heel tip stands 2.5 cm forward
of the barefoot heel contact (UE y 1.40 vs -1.09 cm, standing); a barefoot walk gets a pelvis bob up to the lift (the leading leg bends more in double
support). Tuning knobs, default off: `PelvisForwardFollow` (0..1, move the pelvis forward by that share of the mean ankle
shift, 63.6 mm when standing, to keep the legs vertical) and `TrailingToeRollDeg` (let a trailing foot pitch further about
its ball before the pelvis drops).

### 4.4 How it ships in DemoGame_1 (read-only look; the user does it, or a later chat with permission)

Her body: `BP_MH_PlayerFemale` `Body` runs `/Game/Ninja/Character/ABP_MH_NinjaBody_Female` (one Retarget Pose From Mesh node,
`RTG_Manny_to_MHFemale`, Manny is the hidden animation host); the body mesh's own post-process ABP is
`/Game/MetaHumans/Common/Body/ABP_Body_PostProcess` (correctives, twist, ankle_fwd/bck).

| Option | Setup | Keeps every animation grounded? | Verdict |
|---|---|---|---|
| **Control Rig node** (`CR_HeelPose`, section 4.3) right after the Retarget node in `ABP_MH_NinjaBody_Female`, pins HeelAlpha + the constants | 1 Control Rig asset, 1 node, 1 float set on equip | yes: adapts per frame to the clip's own foot pitch, floor clamp, reach-safe pelvis | **chosen** |
| Linked Anim Layer (an ALI "Footwear" interface, a heels ABP implementing it, LinkAnimClassLayers on equip) | interface + 2 ABPs + equip code, and the layer still needs the same CR/IK inside | yes (same maths) | more setup for no gain until several footwear rigs differ in more than numbers |
| Pose offset (a one-frame additive: foot pitch + pelvis Z) or static IK-goal offsets in a retarget profile | 1 asset | **no**: ignores the clip's own foot angle (the catwalk would be pitched 34 + 34 deg), toes dig in at push-off, feet float at heel strike | rejected |

Order matters: the CR runs in the main ABP, BEFORE `ABP_Body_PostProcess`, so the MetaHuman correctives see the corrected
ankle. The face follows the body (leader/copy pose), the grooms follow the head, and the heels mesh (a skeletal garment on
`metahuman_base_skel`, skinned to foot_*/ball_*) follows the corrected body via Leader Pose / Copy Pose, so nothing else
changes. Manny's GASP foot placement is untouched (it runs on the host before the retarget).

---

## 5. Files for the shoe builder

- `foot_posed.blend` (sha `d869fc15...` in json): a COPY of the fitting body with the armature in the heel pose (only
  pelvis, thigh/calf/foot/ball l+r posed), plus collection `HEEL_POSE_REF`: `HEEL_FootPosed_L/R` (the posed skin below
  mid-shin, applied, 7,028 triangles each), empties `HEEL_HeelContact_*` (heel seat point, z 90 mm), `HEEL_BallContact_*`,
  `HEEL_ToeLowest_*`, `HEEL_Pivot_*`, `HEEL_HeelTipFloor_*` (floor point under the heel contact), `HEEL_Floor` (z = 0 top).
  It is a reference, not the garment's fitting body: the garment work file still appends the LOCKED body from
  `References/Characters/MH_PlayerFemale/` (the gates hash it).
- Model the shoe around the posed foot, then map it back to the bind (rest) pose before skinning/export:
  `from SnowFlowerHeels.heel_pose import load_pose, apply_heel_pose, clear_heel_pose, unpose_points`
  (`load_pose()` + `apply_heel_pose(arm, feet, params)` reproduces this pose to 0.0005 mm; `unpose_points(points, weights, arm)`
  inverts the skinning for given foot_*/ball_* weights). The exported garment is in the REST pose, like every garment;
  it only looks right on her once the correction runs (in a Persona preview without it, the shoe sits on a flat foot).
- Skin: back part and heel on `foot_*`, forefoot/toe box on `ball_*`, a short blend at the ball flex line; the ankle strap
  on `foot_*` (plus a little `calf_*` if it must follow the shin). Check clearance against the POSED foot (the gates'
  rest-pose test sees a flat foot inside a pitched shoe); the shoe-specific gate settings are for the builder to agree.
- Renders of the pose: `heel_pose_renders/heelpose_MH_PlayerFemale_{side_L,front,threequarter_L}.png`.
