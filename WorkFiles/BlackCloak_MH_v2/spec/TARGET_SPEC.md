# BlackCloak_MH_v2: target spec

Date: 2026-09-27. Author: the target-spec agent of the v2 build workflow. The machine copy is `target_spec.json`, next to this file. It holds the same numbers.

**Frame used throughout:** the locked fitting body's world.
- Units are metres, with Z up.
- The male faces -Y. **His right is -X**, which is viewer-left in a front view.

All paths are relative to `C:/Users/Cody/Desktop/Blender_Projects/` unless they are absolute.

## 0. In short

- **What we build.** One heavy wool mantle, fastened by a round glossy dark button high on his right shoulder.
  - It wraps across his front to his left side and continues around the back.
  - Long folds fan out from the button, down and across the front.
  - The open edge falls from the button down his right front.
  - A dark lining sits behind that edge, so his legs never show.
  - On top is a smooth, tall funnel collar. Its front rim sits just under his nose tip, so the mouth is covered and the eyes are free. It is open at the top, with a dark inside.
- **What comes from where.**
  - Fabric, edges, hem, length and outline come from the user's photo.
  - Shape and how the cloak sits on him come from Jin_Cloak.
- **One structural finding changes how the photo is scored.** The photo is a ghost-mannequin shot, and the mannequin holds its arms out under the cloak.
  - Mapped onto the male, the photo's two wing points land where his A-pose hands are.
  - So the photo outline is scored on a re-drape in his A-pose (the "product-form drape").
  - The shipped mesh is the arms-down drape, and it is judged against Jin's look (sections 5 and 6).
- **Pose decision.** Drape arms-down (`ARMS_DOWN_V2`). That drape is the bind mesh, unchanged.
  - The cloak is weighted to spine, neck and head bones only.
  - Those bones do not move between `ARMS_DOWN_V2` and the rest A-pose.
  - So the arms-down drape is already valid as the rest-pose mesh. There is no inverse-skinning step.
- **Measurement tools.** They are ready in `spec/scripts/`, and `v2m_run_all.sh` runs a whole round.
  - They were checked on the current in-game cloak and reproduce the review's numbers (section 9).

## 1. Sources and what each one decides

| Topic | Decided by | Notes |
|---|---|---|
| Overall shape, how it sits, wrap direction | **Jin_Cloak** (look only, never traced or textured) | One mantle. Clasp high on his right shoulder. Fold fan. Open edge down his right side. |
| Collar | **Jin_Cloak** | Smooth, tall funnel over the mouth, open top with dark inside. The photo's wrapped cowl is not used. |
| Clasp | **Jin_Cloak** | Solid round glossy dark domed button. No ring, no strap, no pin. The photo's ring and strap are not used. |
| Fabric (slub, value, warmth, sheen) | **Photo** | Matte, slubby linen/wool. Charcoal-black, slightly warm. |
| Edges | **Photo** | Frayed ragged edges, a few loose threads, soft rolled thickness. |
| Hem | **Photo** | Continuous and staggered. Flares and pools slightly on the floor. The front is raised about 8 cm. |
| Length and outline width | **Photo** | Scored on the product-form drape (section 5). Arms-down is held to a lower bar. |
| Back | No reference | Mantle and funnel continue around as one plain piece. Nothing invented. |
| Front opening | User decision | A dark lining or under-layer behind it. No trousers. |
| Not added | User decision | No hood, no extra straps, no decorations. |

## 2. Measurements

### 2.1 Photo (`References/BlackCloak/blackcloak.png`, 417 x 674)

Tool: `v2m_ref_measure.py`. Outputs: `spec/out/ref_photo_measure.json`, `ref_photo_contour.json` (outline normalised to garment height, one row per 1 %), `ref_photo_mask.npy`, and `ref_photo_measure_overlay_2x.png`.

**Mask and outline.**
- The mask is luma < 115 (0.45), the review's threshold.
- Garment bbox is (10, 7)-(402, 660). Height over width is 1.664.
- Widths in px:
  - 100 at the collar (top + 15)
  - 269 at row 150
  - 375 at most, at row 337
  - 327 at row 447
  - 365 at row 627
- Bands follow the review: collar 0-120, shoulders 120-260, wings 260-480, lower 480-600, hem 600-674.

**Hem.**
- 4 jumps of 8 px or more, at x = 39, 272, 381 and 391.
- Range 34 px and std 10.5 px, over x 40-380.
- Both outer corners flare down to y 628-629. The lowest points are y 659-660 at x 70-90.
- The centre front, x 140-260, is raised to y 626-631. That is about 30 px, or 8 cm on him.
- Floor contact is 7.9 % of the columns.

**Fray.**
- At this resolution it is subtle but measurable.
- Hem outline high-frequency RMS is 1.03 px.
- There are 63 spikes over 1 px and 24 over 2 px along x 40-380.
- Thin-residue is 1.26 px per 100 px of hem outline.

**Tone.**
- Garment luma p10/p50/p90 = 8 / 31 / 40 sRGB. The linear median is 0.0137.
- Mean RGB is 27.7 / 27.4 / 27.1, which is slightly warm.
- The backdrop is 254.

**Grain.** Measured on the 6 flattest 32 x 32 patches.
- High-pass relative std: 0.055.
- Band energy by period is shown below. 1 px is 2.74 mm on him.

  | Period band | On him | Energy |
  |---|---|---|
  | 2-3 px | 5.5-8 mm | 0.31 |
  | 3-5 px | 0.8-1.4 cm | 0.26 |
  | 5-10 px | 1.4-2.7 cm | 0.20 |
  | 10-16 px | 2.7-4.4 cm | 0.07 |

- Anisotropy (max over min energy across 8 orientation sectors): mean 2.8, range 1.6-4.0.
- Vertical over horizontal frequency: 0.9 (range 0.5-1.3).
- ACF half-width: 1 px.
- Reading: the slub is isotropic, with energy from 5 mm up to about 4 cm. There is no direction.

**Mapping the photo onto him** (`spec/out/spec_photo_on_male_rows.json`, `spec_target_overlay.png`):
- 365 reference px per metre (1 px = 2.74 mm).
- The floor is at photo row 662. His midline is column 200.
- The bracket comes from three independent mappings:

  | Mapping | px/m |
  |---|---|
  | The old traced cloak's own fit on him | 353 |
  | The reviewers' "collar at eye level" | 368 |
  | Collar top at the v2 funnel's back rim | 374 |

- Allowed band: 350-380 px/m.
- At 365 px/m the photo outline is:
  - 0.75 m wide at z 1.40
  - 0.97 m at z 1.00
  - 1.03 m at z 0.91 (the wing points)
  - 1.02 m at z 0.10

**Why this means the photo form had its arms out.**
- The photo's wing points land at (-0.52, 0.91) and (+0.56, 0.76).
- His A-pose right hand is at (-0.518, 1.081), with fingertips around z 0.9.
- The straight slopes from shoulder to point are fabric carried over outstretched arms.
- The old cloak was sculpted around an A-pose and traced from the photo. It matches the photo at IoU 0.962 (rows 120 and below), but its hands come through the wings when the arms go down. That fits the same explanation.

### 2.2 Jin_Cloak (2420 x 3632)

Tools: `spec_jin_measure.py` and the manual grid readings, both in `spec/out/spec_jin_measure.json`. The grid images are `spec_jin_face_grid20.png` and `spec_jin_quarter_grid100.png`.

**Scale.**
- The eye (iris) distance is 207 px, which equals his 7.2 cm eye-front distance. So 0.0348 cm per px.
- This scale checks out on the body: the viewer-right shoulder peak maps to z 1.564, which is his clothed shoulder line.
- The illustrated nose is long. Eye-to-nose is 163 px, while his is 4.0 cm. So face heights are read against the face landmarks, not the px scale.

**Funnel collar.**
- The front rim at the face centre is at y 755. That is 57 px under the nose tip, or 0.35 of the eye-to-nose distance. On him that is 1.688 m by the face landmarks, or 1.666 m by the px scale.
- The rim rises to about 1.70-1.71 m at the cheeks (about 4.5 cm off the midline). Behind the head it reaches about eye level.
- The outer width is 760 px, which is 26.4 cm on him (1.35 x his head width).
- It meets the mantle about 10 cm below the rim.
- It is smooth, with a dark gap between collar and face (pure black at the viewer-left).

**Clasp.**
- Centre (563, 1320), radius 78 px. Diameter 5.4 cm on him.
- 20 cm to his right of the face centre. 27 cm under the eye line, so z about 1.47.
- 5-10 cm under his shoulder line and 5 cm inside the cloak's outer edge.
- A glossy dome with a rim highlight.

**Fold fan.** Arc crossings around the clasp. 0 deg points toward his left (image right) and 90 deg points straight down.

| Arc radius | Ink lines, across chest (-50..10 deg) | Ink lines, down and across (15..120 deg) | Detector (`v2m_jin_score --selftest`) |
|---|---|---|---|
| 0.35 m | 8 | 9 | 5 across, 8 fan, spread 76 deg |
| 0.55 m | - | 10 | 8 fan, spread 77 deg |

**Wrap and opening.**
- The mantle crosses from the clasp over his front to his left, and around.
- The dark opening, where the sword shows, is at x -0.26..-0.21 at hip and thigh level. That is in front of his hanging right hand.
- Length cannot be read from Jin: the frame ends at mid-thigh.

### 2.3 The male (`spec/out/male_landmarks.json`, tool `v2m_body_landmarks.py`)

Heights (m):

| Landmark | z |
|---|---|
| Stature | 1.863 |
| Hair-proxy top | 1.878 |
| Eye line | 1.743 |
| Nose tip | 1.7025 (y -0.133) |
| Subnasale | 1.6875 |
| Upper lip | 1.6725 |
| Mouth line | 1.6525 |
| Chin point | 1.6325 |
| neck_01 / neck_02 / head bones | 1.566 / 1.622 / 1.680 |

Head width:
- At the eye line: ±0.098
- At the mouth: ±0.063, with y from -0.119 to +0.063

Shoulders:
- Acromion proxy at x ±0.205, z 1.535
- Shoulder line z: 1.505 at |x| = 0.08, 1.521 at 0.12, 1.535 at 0.18
- Biacromial width: 0.41 m

Arms:
- A-pose upper arms are 37.4 deg from vertical, with hands at (±0.518, -0.146, 1.081).
- In `ARMS_DOWN_V2` the upper arms hang about 9 deg off vertical and the forearms about 14 deg forward. The hands sit beside the thighs.

### 2.4 Target sheet

`spec/out/spec_target_overlay.png` shows the photo outline (red) mapped onto him arms-down. It marks the funnel-rim targets (blue lines), the clasp (dark square) and the opening band at the hand (green).

## 3. The target on him

**Funnel collar**

| Measure | Target |
|---|---|
| Front rim at the centre | z **1.690** (accept 1.680-1.702): under the nose tip, over the upper lip |
| Rim at the cheeks (\|x\| 3.5-6.5 cm) | 1.695-1.725 |
| Rim at the back | 1.725-1.765 |
| Rim in front of the nose tip | 1.0-3.5 cm |
| Clearance to the head | at least 1.0 cm everywhere |
| Outer width at the mouth line | 0.24-0.29 m |
| Width at the base (z 1.56) | 0.30-0.40 m |

- From the Jin and front cameras, the eyes are visible, and the mouth line, upper lip and chin are hidden by the garment.
- Smooth, with no wraps and no rings.
- The top edge is a soft fold. The dark inside shows in the gap in front of the face.
- It continues all around the back as one surface.

**Clasp**

| Measure | Target |
|---|---|
| Centre x | **-0.185** (accept -0.205..-0.165) |
| Centre z | **1.48** (accept 1.46-1.50) |
| Position | On the mantle's outer surface |
| Diameter | 5.0-6.0 cm |
| Dome height | 1.0-1.8 cm |

- A thin raised bezel.
- Glossy dark dielectric: base colour 0.02-0.03 linear, roughness 0.2-0.35.
- Slot `M_BlackCloakV2_Clasp`, with `garment_hard = True`.

**Fold fan**, measured on the Jin-framing render with `v2m_jin_score.py`:
- At least 7 folds in the 15-120 deg sector at 0.35 m.
- At least 4 in the -50..10 deg sector at 0.35 m.
- At least 6 in the fan sector at 0.55 m.
- Fan spread of at least 70 deg at 0.35 m.
- Roughly 3/4 of the illustration's counts.

**Mantle and opening**
- The edge falls from the clasp down his right front.
- At hip and thigh height the opening sits in x -0.28..-0.18.
- The lining is behind it.
- Zero torso, neck or leg pixels (above 10 cm over the floor) in the photo, front, 3/4, side and Jin views.

**Hem**
- Lowest z is 1 cm or less.
- At least 0.5 m of hem lies on the floor: it pools 2-5 cm at the sides and back.
- It rises 5-9 cm across the front at the opening.
- It is continuous, with no square strips and no slits.

**Air**
- Torso and neck: p5 at least 0.8 cm, counted over vertices within 5 cm of the skin. The p50 is reported; the 1-1.5 cm house rule applies to the contact zone.
- Cloth panels start 1.5 cm off the skin.

**Fabric** (for the stage-1 surface kit; the render tone decides)
- Base colour: start at 0.013-0.019 linear (a texture median of 30-38 sRGB).
- Warmth: R/B 1.02-1.08 in linear.
- Roughness: 0.85-0.95.
- Sheen: Blender weight 0.3-0.6, or UE Cloth fuzz 0.03-0.05.
- Slub: isotropic thick-thin mottling at 0.5-4 cm, plus fine fibre noise.
  - No directional weave.
  - The tile is at least 50 cm, mapped with true-scale UVs.

**Edges**
- Soft rolled thickness of 3-5 mm.
- A frayed fringe of 1-2 cm.
- 6-12 loose threads on the hem and wing points.

## 4. Pattern plan (stage 2)

Model the garment the way a real one is made. The pilot's recipe carries over: flat pieces, sewing springs, Blender 5.2 cloth, self-collision on.

### 4.1 Pieces

| Piece | Cut | Rough size | In game |
|---|---|---|---|
| **Mantle** | One asymmetric circle cut of about 330 deg. The opening is off-centre at azimuth about -50 deg (his right front). A **wrap extension** of 30-40 deg on the wrap side lets the left-front portion cross his chest to the right shoulder. | Radius measured from the neck edge: back 158-165 cm, sides over the arms 164-172 cm, front wrap into a curved cutaway 145-150 cm (makes the raised front hem). The neck edge is about 100 cm, so it sews to the funnel base. | Sim below the pin line. Skinned above it (the yoke). |
| **Wrap gather** | The top 20-30 cm of the wrap edge, from the neckline to the wrap corner, is sewn (gathered 4-6 x) into the 5.4 cm clasp footprint at (-0.185, surface, 1.48), on top of the under-side at the right shoulder front. | - | Skinned (part of the yoke). This makes the fold fan. |
| **Funnel collar** | A curved conical band, cut double height and **folded at the top edge**. The fold gives a soft rolled rim, and the two layers give thickness and a dark inside. Centre-back seam. The base sews to the mantle neckline. | Top edge 83-90 cm. Base 95-108 cm. Finished height: front 14-16 cm, back 17-19 cm (taller at the back). | Skinned (the build's height blend puts the upper funnel on `head`, so it turns with the head). |
| **Funnel stiffener** | An invisible helper surface in `GARMENT_HELPERS` (the interfacing). It stops 1-2 cm under the fold. It is never exported. | - | - |
| **Lining** | A front under-drape of about 200 deg, hung from the neckline seam in front of the legs. The hem sits 3-6 cm above the floor, so it never shows at the hem. | Radius 140-146 cm. Coarse edges of 8-9 cm (it is hidden). | Sim: the legs must collide with it. |
| **Clasp** | Hard mesh: domed disc 5.4 cm across, bezel 3-4 mm. | - | Skinned, `garment_hard`. |

- **Back.** The mantle and funnel run continuously around the back.
  - The only seams are the funnel centre-back seam and the neckline.
  - For packing, UV islands may split the mantle along the centre back and the sides.
  - Nothing is visible there: no yokes, no panels.

### 4.2 Drape (Blender 5.2, headless)

**Collision**
- Bake the fitting body (body, head and hair proxy) in `ARMS_DOWN_V2`: `v2m_common.ARMS_DOWN_V2` applied with `garment_qa.apply_pose`.
- Outer thickness 6-8 mm, friction 5.
- A collision floor at z = 0, for pooling.

**Placement**
- Pieces start at least 1.5-2 cm off the body. Use a shoulder-cone pre-shape, as in the pilot.
- Seams close with sewing springs.
- The funnel settles on the stiffener.

**Solver**

| Setting | Value |
|---|---|
| Quality | 6-8 |
| Self-collision | On, distance 4 mm |
| Wool mass | about 0.5-0.7 kg/m², converted to Blender's per-vertex mass |
| Tension / compression | 40-80 |
| Shear | 20-40 |
| Bending | 1-5 (heavy wool; higher in the funnel through a bending vertex group) |
| Air damping | 1 |
| Frames | 150-300 |
| Working mesh | 1.5-2.5 cm edges (the pilot used 2.8 cm and took 36 s) |

**After settling**
- Re-topologise to the budget below, keeping the boundaries.
- Bake the hi-res drape's normals onto the budget mesh.
- Check with `v2m_geom_check.py`: 0 vertices inside with the arms down, 0 self-intersections, fold-over of 0.20 or more.

### 4.3 Split into skinned and simulated pieces, and the pins

**Pin line.** Rule: every area an arm can touch in any pose is sim. Skinned pieces have no collision.

| Region | Pin line z |
|---|---|
| Front, under the clasp gather | 1.30-1.35 |
| Sides, above the upper arm | 1.42-1.46 |
| Back | 1.35-1.40 |

**Collections.**
- `GARMENT`: funnel, yoke and gather, clasp.
- `GARMENT_SIM`: mantle below the pin line, and the lining.
- The seam vertices between the two must be coincident.

**`CLOTH_Pin`** on the sim pieces:
- 1.0 on the top 2 rows along the yoke seam and at the lining attachment (8-12 cm).
- A linear ramp from 1 to 0 over the next 25-35 cm.
- 0 below that.
- The build bakes this into the red `PinMask`. Unreal builds the MaxDistance ramp from it (trap 9).

**Skinning** is automatic (`skin_cloak`):
- Sim pieces are rigid on one bone. With their tops near z 1.30-1.46, that is `spine_05`.
- Skinned pieces are height-blended on the spine chain.
- Custom weights are overwritten by the build (see proposal 1 in section 8).

### 4.4 Budget (triangles)

| Part | Target |
|---|---|
| Sim: mantle below the pin line | about 4,200 |
| Sim: lining | about 900 |
| Sim: fray fringe row on the visible edges | about 500 |
| Sim: optional turned-under edge strip | about 300 |
| **Sim total (gate)** | **≤ 6,000** |
| Skinned: funnel (2 layers + fold) | about 4,000 |
| Skinned: yoke + clasp gather (1.5-2 cm edges at the gather) | about 7,000 |
| Skinned: edge rolls and fringe | about 1,000 |
| Clasp | about 800 |
| Loose-thread cards | about 50 |
| **Cloak total** | **about 22,000 target, ≤ 30,000 gate** (character 121,892 + cloak ≤ 160,000) |

- Deliver the sim pieces already under 6,000 triangles, with good triangles: edges 4-7 cm, and under 2 % with an angle below 10 deg. Then the build's collapse-decimate does nothing. That decimate made the old cloak's 29 % slivers.

### 4.5 Thickness, edges, fray

- **The build strips SOLIDIFY and SUBSURF.** Thickness must be real geometry.
- **Funnel rim.** The fold is the rim.
- **Visible cut edges** (the mantle hem, the opening edge, the wing points):
  - A 3-5 mm turned-under strip, where the budget allows. It reads as thickness.
  - An outward **fray fringe row** of 1-2 cm, using UV1: U runs along the edge; V is 0 at the cut line and 1 at the fringe tip.
  - The row samples the stage-1 fray alpha in the **same** wool material, set to Masked. The sim section must keep one material, so the fray cannot live in a separate slot.
  - 6-12 thin alpha loose-thread cards on the hem and wing points.
- **The lining** gets no fringe.

### 4.6 UVs and materials

**UV0: true scale.**
- Take the flat-pattern coordinates and divide by S, a single number of metres per UV unit shared by every wool piece. S is 5-8 m, which gives 8.2-5.1 px/cm at 4K.
- UV0 is unique and non-overlapping. Set the scene property `garment_unique_uvs = True`, because the fold normal map is baked.
- The material tiles the slub at UV0 x (S / tile_m).
- The UV-to-3D scale must be uniform: CV ≤ 0.12 (checked by `v2m_geom_check`).

**Material slots** (4 at most):
1. `M_BlackCloakV2_Wool`
2. `M_BlackCloakV2_Wool_Sim` (the build makes it)
3. `M_BlackCloakV2_Clasp`
4. Spare

**Contract with the measurer.** Write `Exports/Garments/BlackCloak_MH_v2/SK_BlackCloak_MH_v2.material_params.json`:

```
{"slots": {"M_BlackCloakV2_Wool": {"base_color_tex":..., "orm_tex":..., "normal_tex": "<DirectX>", "opacity_tex":...,
 "uv_map":..., "uv_scale":..., "base_tint_linear":[r,g,b], "roughness_mult":..., "specular":..., "sheen_weight":...,
 "sheen_tint":[..], "sheen_roughness":..., "normal_strength":...}, "M_BlackCloakV2_Clasp": {...}}}
```

`v2m_render.py` builds its Blender copy of the shipped material from this file and the exported `Textures/`.

## 5. Pose plan

**Decision: drape in `ARMS_DOWN_V2` and ship that drape as the bind mesh.**

**Why the bind is valid.**
- `build_garment.py` binds at the fitting body's rest (A-pose).
- The cloak's weights are only on the spine chain. The gate enforces this, and the sim pieces are rigid on `spine_03..05`.
- Those bones have the same rest transforms in `ARMS_DOWN_V2`, where only the upper and lower arms rotate.
- So the vertices of the arms-down drape are exactly the rest-pose vertices. There is no bind-shape derivation, and no inverse skinning.
- The rest gate (0 vertices more than 1 mm inside, arms ignored) sees the same torso, neck and head as the drape.
  - If the drape has 0 vertices inside, so does the bind.
  - The A-pose arms passing through the wings in the editor's reference pose are expected and harmless.

**Why it is right for the game.**
- In game the idle is arms-down.
- The skinned target that Chaos is driven toward (AnimDrive, MaxDistance) is then the correct hanging shape.
- The old cloak's in-game failures came from the opposite:
  - an A-pose tent as the target
  - AnimDrive 0
  - a column at idle, and boards or ribbons in motion
- Renders of the shipped mesh with the arms down show the look directly.

**How the photo is still scored fairly.** The photo's mannequin holds its arms out (section 2.1).
- `v2m_posed_resim.py --poses apose` re-simulates the shipped cloth section from the bind drape into the rest A-pose. The arms lift the wings just as the mannequin's did.
- The photo outline is scored on that product-form drape.
- The arms-down outline is also scored, with a lower bar.

**Robustness.**
- **Idle settle.** Hold `ARMS_DOWN_V2`. The drape must stay put: this catches pin errors and a column collapse.
- **The four gate poses.** Long stride, arms forward, deep crouch and arms up, re-simulated from the bind drape.
  - Blender cloth, self-collision on.
  - Colliding with the posed body with arms included, and with the floor.
  - Pinned by the shipped `PinMask`.

**Rejected alternatives.**
- **Drape in A-pose and ship it.** The anim target becomes a tent, which gives the old board-and-column behaviour, and the shipped renders would not show the look.
- **Inverse-skin an arms-down drape into A-pose.** This does nothing with spine-only weights. It only becomes relevant if clavicle weights are ever approved (proposal 1).

## 6. Acceptance: what passes and how it is measured

### 6.1 Rules for every measure

- **Measure only the shipped FBX.** That is `Exports/Garments/BlackCloak_MH_v2/SK_BlackCloak_MH_v2.fbx` with its exported `Textures/` and `material_params.json`.
  - It is re-bound to the locked fitting body.
  - Never the builder's scene, an internal layer or the builder's own report.
- **Renders.**
  - Cycles, OptiX, 256 spp, OIDN denoising.
  - View transform **Standard**, look None, exposure 0.
  - 16-bit PNG, transparent film.
- **Lighting.** The male review's product rig (`v2m_common.lights`):
  - key: 3 x 3 m area, 1000 W, at centre + (-1.6, -3.0, 1.4), turning with the camera yaw
  - fill: 3 x 3 m, 350 W, at (1.9, -2.8, 0.5)
  - top: 2.5 m, 400 W, 3 m up
  - white world at strength 4
  - Everything is scaled so an albedo-1 Lambertian card at (0, -0.25, 1.30), facing the camera, reads **0.90 linear**.
  - Tone targets are absolute under this rig, with no exposure matching. Only the blind pairs match exposure (fairness).
- **Round outputs.** Put renders in `Renders/BlackCloak_MH_v2/<round>/`.

### 6.2 Cameras

All use the fidelity-style camera: vertical sensor fit, 24 mm sensor. Yaw above 0 moves the camera toward his left.

| View | Lens | Yaw / pitch | Framing | Resolution |
|---|---|---|---|---|
| **photo** | 100 mm | 0 / 0 | Target = garment bbox centre, distance = height x 1.08 / (24 / f) | 1251 x 2022, then box-down in linear to 417 x 674 |
| **jin** | 85 mm | +12 / +3 | Target (0, 0, 1.358), vertical span 1.10 m (head top to mid-thigh, like the illustration) | 605 x 908 |
| front, q34 (-40), q34_other (+40), side_r, side_l, back | 85 mm | - | Target (0, 0, 0.95), span 2.02 m | 600 x 900 |
| face | 85 mm | +12 / +3 | Target (0, -0.05, 1.66), span 0.42 m | - |
| hem | 85 mm | 0 / +8 | Target (0, -0.1, 0.12), span 0.45 m | - |

Notes on the photo camera:
- It refits `camfit_lod0.json`.
- Yaw is held at 0, because the review showed the -10 and -18 deg yaws were fit artefacts.
- Only scale and shift are fitted, by best IoU on rows 120 and below.
- Two physical checks: 350-380 px/m, and the floor within 6 px of row 662.

### 6.3 Thresholds

| # | Check | Tool / render | Pass |
|---|---|---|---|
| A | Pipeline gates | `build_garment.py --gate-only` / `SK_BlackCloak_MH_v2.qa.json` | Every gate passes, no waiver. Rest: 0 vertices more than 1 mm inside (arms ignored). Poses: ≤ 1 % more than 5 mm (skinned vertices). Spine chain only, ≤ 2 influences, sim rigid on spine_03..05, ≤ 4 slots, one `*_Sim`, `PinMask` active, cloth ≤ 6,000, cloak ≤ 30,000, character ≤ 160,000 |
| B1 | Clearance, arms-down | `v2m_geom_check.py` | **0** vertices more than 1 mm inside the skin in `ARMS_DOWN_V2`, every region **including arms** |
| B2 | Cloth quality | same | 0 self-intersecting face pairs. Front fold-over ≥ 0.20 (the pilot got 0.35, the old cloak 0.000). Sim slivers under 10 deg ≤ 2 %. All slivers under 5 deg ≤ 1 %. UV0 scale CV ≤ 0.12 |
| B3 | Funnel, clasp, hem, air | same | The section 3 ranges |
| C1 | **Photo outline, product-form drape** | `v2m_posed_resim.py` pose apose, then `v2m_silhouette_score.py <resim> apose_photo` | IoU on rows 120+ (aligned) **≥ 0.95**. Bands: shoulders ≥ 0.92, wings ≥ 0.94, lower ≥ 0.94, **hem ≥ 0.90**. Hem jumps (8 px or more) **≤ 4**. Floor within 6 px. 350-380 px/m |
| C2 | Photo outline, shipped mesh arms-down | `v2m_render.py --view photo --body 0` + `v2m_silhouette_score.py` | IoU on rows 120+ ≥ 0.90. Hem band ≥ 0.88. Hem jumps ≤ 4. Floor within 6 px. 350-380 px/m |
| C3 | Collar band, rows 0-120 | same | Reported only. The v2 funnel is not scored against the photo cowl |
| D | Tone, grain, fray | `v2m_fabric_score.py` (cloak-only photo render) | Luma p50 28-36, p10 4-13, p90 35-46 sRGB. R/B (linear) 1.00-1.10. Grain high-pass relative 0.040-0.075. Each band energy within 0.08 of the photo. Sector anisotropy ≤ 3.5. Vertical/horizontal 0.6-1.6. Hem outline high-frequency RMS 0.7-1.6 px. Spikes over 2 px: 12-40 |
| E | **Blind judge** | `v2m_make_blind.py` (20 pairs: 6 fabric, 5 hem, 5 edge/fray, 2 outline below the cowl, 2 lower quadrants; no collar, clasp or front-layering crops) | The judge picks the photo in **13 or fewer** of 20 |
| F1 | **Look judge vs Jin_Cloak** | Renders with body, arms down: jin, face, front, q34, q34_other, side_r, side_l, back, shown beside Jin_Cloak | **Every aspect ≥ 4/5** (aspects below) |
| F2 | Fold fan | `v2m_jin_score.py` on the jin render | At 0.35 m: fan ≥ 7, across ≥ 4, spread ≥ 70 deg. At 0.55 m: fan ≥ 6 |
| F3 | Face | `face_landmark_visibility` in the render json (jin, face, front) | Eyes visible. Mouth line, upper lip and chin hidden by the garment |
| G | Cloth in poses | `v2m_posed_resim.py` (idle, apose, long_stride, arms_forward, deep_crouch, arms_up) | Sim vertices more than 5 mm inside (all regions) ≤ 0.5 %. Sim self-intersections 0. Idle displacement from the bind: mean ≤ 2 cm, p95 ≤ 6 cm. Settled idle IoU (fixed rest alignment) ≥ the bind IoU - 0.02. Skinned vertices inside torso, legs, neck or head = 0 (arms in raised poses reported only) |
| H | No body through the front | `v2m_render.py --body 1` ID renders (photo, jin, front, q34, sides, back) → `visible_body` | 0 torso or neck px, and 0 leg px above 10 cm over the floor. Allowed: head above the rim, hand or forearm at the opening, toes under the hem if the look judge agrees |

**Look aspects for F1:**
1. One heavy mantle wrapping from a clasp high on his right shoulder across the body.
2. Long folds fanning or radiating from the clasp, down and across the front.
3. An open edge down his right side (viewer-left), dark lining behind it, room for the arm or sword.
4. A smooth, tall funnel collar over the mouth: face visible from about the nose up, open top, dark inside.
5. A round glossy dark button (no ring, strap or pin).
6. Heavy, long, matte charcoal wool (not flat black), with rolled, frayed edges.
7. A plain, continuous back (mantle and funnel, nothing invented).

**Judge by looking and confirm by measuring.** A number that passes while the render looks wrong is a failure. Each round's report puts the renders beside the numbers.

**Unreal (for the Unreal-check agent, proposals only, not Blender gates).**
- Self-collision on (the drape is intersection-free).
- Per-vertex MaxDistance from the `PinMask` ramp: 0 at the pin line, 40-60 cm at the hem.
- AnimDrive ramp: about 0.3-0.5 near the top, down to 0.05-0.1 at the hem. The bind is the arms-down drape, so the target is the right shape.
- CollisionThickness 1.0-1.5 cm.
- Density 0.5-0.7 kg/m².
- Accept when the settled PIE idle IoU (fixed framing) is within 0.03 of the rest IoU, and no legs show in the PIE poses.

## 7. Measurement tools and runbook

**Where.** `C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/spec/scripts/`. All run in Blender 5.2 headless; start them with `"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python <script> -- <args>`.

| Script | What it does |
|---|---|
| `v2m_common.py` | Appends the locked fitting body (read-only, hash-checked). Imports and re-binds the shipped FBX. Holds `ARMS_DOWN_V2`, the views, the product rig, the white-card calibration, the material copy from `material_params.json`, and the region-ID body. |
| `v2m_render.py` | `--view photo\|jin\|front\|q34\|q34_other\|side_r\|side_l\|back\|face\|hem --body 0\|1 --pose down\|rest --mult --samples --out --tag [--no-beauty] [--clasp-keys]`. Writes `<tag>.png`, `<tag>_alpha.png`, `<tag>_id.png` and `<tag>.json` (camera, calibration, projected landmarks, face-landmark visibility). |
| `v2m_silhouette_score.py` | `<dir> <tag> [out.json\|-] [rest_silhouette.json for a fixed fit]`. Gives IoU, bands, hem, contour distances, the scale check, visible body, and an overlay. |
| `v2m_fabric_score.py` | `<dir> <tag>`. Tone, warmth, grain spectrum and anisotropy, fray, all against the photo. Also writes `<tag>_refframe.npy` for the blind pairs. |
| `v2m_geom_check.py` | `--fbx --out`. The 3D checks: budgets, slivers, weights, clearance, funnel, clasp, hem, fold-over, self-intersections, sim edges, `PinMask`, true-scale UVs. |
| `v2m_jin_score.py` | `<dir> jin`. Fold-fan crossings. `--selftest` calibrates it on the illustration. |
| `v2m_posed_resim.py` | `--fbx --out --poses idle,apose,long_stride,arms_forward,deep_crouch,arms_up`. Writes `<pose>_front/side_r/back.png`, `<pose>_photo_alpha.png` + `.json`, and `posed_resim.json`. |
| `v2m_make_blind.py` | `<dir> photo <pairs_dir> <scratchpad_keyfile>`. The key never goes next to the pairs. |
| `v2m_run_all.sh` | `bash v2m_run_all.sh <out_dir> [<fbx>] [geom photo photo_body jin views resim settled blind]`. Set `V2M_BLIND_KEY` for `blind`. Each step stays under 8 minutes. |
| `v2m_ref_measure.py`, `v2m_body_landmarks.py`, `spec_jin_measure.py`, `spec_target_overlay.py`, `v2m_contact.py`, `v2m_lib.py` | Spec-time measurements, the contact-strip helper, and the shared image library (a copy of the review's `gap_lib.py` plus additions). |

**A typical round:**

```
V2M_BLIND_KEY=<scratchpad>/v2_r1_key.json bash v2m_run_all.sh C:/Users/Cody/Desktop/Blender_Projects/Renders/BlackCloak_MH_v2/r1
```

Then the blind judge reads `r1/blind/pair_*.png`, and the look judge reads `r1/{jin,face,front,q34,q34_other,side_r,side_l,back}.png` next to Jin_Cloak.

**Performance.**
- A photo render at 1251 x 2022 and 256 spp takes seconds on the 4070 SUPER.
- A posed re-sim pose takes about 40-50 s for a section of about 3.4k vertices.
- Each script holds one Blender process at about 1-2 GB.

## 8. Proposals for the user (not in the gates) and open questions

**Proposals**
1. **Clavicle weights for the shoulder yoke and clasp zone.** With spine-only weights, the deltoids come through the yoke when the arms rise.
   - `skin_cloak` overwrites custom weights, so this needs a helper change.
   - It is recorded here as a proposal only.
2. **Hem fidelity versus the cloth budget.** If a 6,000-triangle sim section cannot hold the photo's hem in the blind hem crops, there are two options:
   - raise the cloth budget to about 10-12k triangles (Chaos cost at 3.4k particles was below the noise), or
   - use Unreal's LOD1 → LOD0 clothing proxy.
   Both are pipeline decisions.

**Open questions (the spec's default is in brackets)**
1. **Rim height.** "Covers mouth and nose" and "face visible from about the nose up" conflict slightly. [Front rim at 1.690 m: under the nose tip, over the upper lip, as in Jin. Accept 1.680-1.702.]
2. **Silhouette width arms-down.** The photo's width comes from a mannequin with its arms out. Arms down, heavy wool hangs narrower at the wings. [The photo outline is scored on the A-pose product-form drape; arms-down must reach IoU 0.90 or more. Matching the full photo width arms-down would need the cloak to stand off stiffly.]
3. **Clasp x.** Jin puts the button at about -0.20, on the front of the shoulder joint. [Aim -0.185, accept -0.205..-0.165, to keep it off the deltoid with spine-only weights.]

## 9. Were the tools checked?

All tools were run on the current in-game cloak (the review's copy of `SKM_BlackCloak_MH.fbx`). Outputs are in `spec/out/smoke/` and logs in `spec/logs/`. They reproduce the review's findings:

| Measure | Our tools | Review |
|---|---|---|
| Triangles | 28,378 | 28,378 |
| Sim triangles | 5,991 | 5,991 |
| Sim self-intersecting pairs | 707 | 707 |
| Vertices inside with arms down | 27 | 27 |
| Front fold-over | 0.0001 | 0.000 |
| Hem jumps | 10-11 | 7 (Blender) / 12 (UE) |
| Hem band IoU | 0.78 | 0.69-0.73 |
| Settled idle IoU (fixed framing, raw rows 120+) | 0.818 | 0.797-0.813 |
| Cowl front rim | 1.738 m | 1.738 |
| Grain anisotropy | 72 (the wormy streaks) | - |

- The old cloak still scores IoU 0.962 on rows 120+ at rest. It was traced from the photo on an A-pose form, which is why the product-form drape is the fair place to score the photo outline.
- The fan detector finds 5 across / 5 fan on the old cloak and 5 / 8 on the illustration. That matches the review's "about half the radial folds".
- The Jin view shows the old cowl covering the mouth and nose with the eyes free, which the visibility check reports correctly.
