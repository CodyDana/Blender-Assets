# SR-01 review render rig, rig2: proposal for gunlib (2026-10-16)

Scope: the render-rig tells in `FINAL_JUDGES.md` (#1 backdrop and light pools, #3 blocky floor patches, #5 contact,
#7 grain and defocus, #8/#11 dead black glass). Only the sniper's copy was changed:
`Scripts/guns/sniper/sr_review_job.py` and `Scripts/guns/sniper/sr_review_export.py` (`--rig2`). gunlib was not
touched. The gun chat can port this to `gunlib/realism_job.py` / `export_review_job.py`.

Render: `py -3 -B Scripts/guns/sniper/sr_review_export.py --tag rig2 --only realism --rig2` (5 shots, about 80 s on the
4070 SUPER). Sources are the shipped `Exports/Guns/SR01` bytes; nothing was re-exported.
Output: `review/rig2/realism/*.png`, `review/rig2/compare_rig.png` (r2 on the left, rig2 on the right).

## Causes found in the r2 code

| Tell | Cause in r2 |
|---|---|
| #1 seamless grey void, dark dome, hard seam | The camera sees the flat `bg_rgb` world beyond a 40 m flat plane, so there is a horizon line where the lit plane meets the unlit world colour. The "studio" HDRI is hidden from the camera but still lights the scene. |
| #1 blown elliptical pools | Strip and flank softboxes at 1.2-1.3 m hit the floor at grazing angles. The view transform is **Standard**, which clips the hot spots instead of rolling them off. |
| #3 blocky rectangular floor patches | The interior HDRI's window rectangles and the 0.1 m-wide strip lights reflect in a 0.55-rough, perfectly uniform floor. |
| #5 floats | `drop_mm` 0.3 leaves a gap. The light comes from many directions, so there is no dominant shadow. The deployed pose leaves the rifle level on its bipod with the butt in the air. |
| #7 even grain, too-even defocus | 512 spp with the **denoiser off** (an SMG W4b choice), and a round aperture. |
| #8/#11 empty black eyepiece | The ADS camera is 86 mm from the eyepiece but focused on the target 515 mm away at f/4, so the eyepiece is a blurred black disc. Nothing bright sits in the glass's mirror direction except one small light. |

## Changes (all opt-in per shot; shots without them render exactly as before)

1. **Lights `{"rig": "photo"}`** (`photo_lights`): no HDRI. The world is a dim neutral grey (`env` 0.12, never the
   visible backdrop). Four rectangular area lights are placed in the camera's horizontal axes around the shot target:
   - Key: 1.2 x 0.9 m, upper left front, 1.7 m, 260 W
   - Fill: 2.0 x 1.4 m, low right front, 2.2 m, 35 W
   - Rim strip: 0.35 x 1.6 m, behind and above, 1.6 m, 45 W, **spread 45°** (a grid, so it lights the gun and not a
     pool on the sweep)
   - Top: 1.6 x 0.6 m, overhead, 1.5 m, 70 W

   None of them is visible to the camera. Note: in Cycles a narrower spread **concentrates** the same power, so lower
   the energy when you narrow it. A 100° key overexposed by about 1 stop.
2. **Cyclorama floor `{"cyc": true, ...}`** (`cyclorama`): replaces the plane.
   - Shape: a floor running 10 m toward the camera, a 0.9 m-radius quarter-circle cove (48 smooth-shaded segments)
     and a 9 m wall, 20 m wide. The wall sits `wall_m` behind the target (1.3 m; 2.2 m for tp_3m) and is turned about
     Z to face the camera.
   - Placement: the floor is exactly at the lowest posed vertex (`drop_mm` 0), so the lowest point touches and nothing
     intersects (checked on the bipod feet at full resolution).
   - Material (`cyc_material`): sRGB 92 grey. Noise at 0.8/m varies the tone by -5/+4 %. Fine 900/m noise varies the
     roughness 0.62 ± 0.06 and adds a 0.04 bump. Specular 0.35.
3. **Render `shot["render"]`** (`photo_render`):
   - Colour: AgX view, "AgX - Medium High Contrast" look, exposure -1.1.
   - Sampling: `sample_clamp_indirect` 10, `blur_glossy` 0.5, caustics off, light tree on.
   - Denoising: OIDN on albedo + normal, ACCURATE prefilter, at 384 spp (`denoise: true`). At these distances the
     denoiser no longer reads as plastic, because the floor and textures are not flat.
   - Without the key, the shot keeps the calibration settings (Standard, no clamp).
4. **Lens**: `dof.blades` 7 (rotated 15°) and a 36 mm sensor. The f-stops are unchanged (f/4 close, f/8-11 hero).
   ads_eyepiece focuses on the eyepiece glass (`focus_M` X 271, CRAFT_STUDY) at f/8. The lens slot is unchanged (opaque
   glossy, Q6). It now shows the coated purple/green reflection and the soft boxes, not one highlight.
5. **Staging `shot["rest_on_butt"]`** (`rest_on_butt`): one rigid pitch of the whole assembly (armature + magazine +
   scope) about a Y line through the lowest point (a bipod foot), by the smallest angle that brings a rear point to the
   same height. The angle is solved, not guessed: 11.91° for deployed_34. No bone is re-posed. The pose is undone at the
   start of the next shot (`HOME`).
6. **Framing**: deployed_34 widened to 40° fov with the target 30 mm lower, because r2 cut the near bipod foot at the
   bottom edge.

## How to port to gunlib

- Copy `photo_lights`, `cyclorama` + `cyc_material`, `photo_render`, `world_verts` + `rest_on_butt`, the `floor(...,
  cam)` branch and the two `lens_dof` lines into `export_review_job.py` / `realism_job.py`. They are self-contained and
  use only gunlib `RD`/`LK`.
- In each gun's realism shot list, use `lights={"rig": "photo", "target_M": t}`, `floor={"cyc": true, "target_M": t,
  "rgb": [92, 92, 90], "rough": 0.62, "drop_mm": 0, "wall_m": 1.3, "radius_m": 0.9}`,
  `dof={"fstop": f, "blades": 7}`, `render={"view": "AgX", "look": "AgX - Medium High Contrast", "exposure": -1.1}`,
  `samples` 384, `denoise` true, and `rest_on_butt` for bipod-deployed views.
- Keep the L5 / studio rigs for colour calibration. AgX shifts the look of the pack colours, so judge colour accuracy on
  the calibration rig and realism on this one.

## Not done / left

- The tp_3m sweep still has a soft brighter area right of centre (the key's spill). It is a gradient, not a pool.
  Lower the key's spread with a matching energy cut if a judge flags it.
- No sensor grain, vignette or chromatic aberration in post. A real camera has them, and adding them is cheap if a
  judge still flags the noise.
- The asset tells in FINAL_JUDGES (geometry and material) are out of scope here.

## Judge verdict (rig2)

One fresh, strict, independent judge (Sonnet) saw the five new images at 1280 px, with no context.
File: `review/rig2/judges/realism_A.json`.

- **All 5 are still CG**, with confidence 0.95-0.97. "Rig better than a typical CG studio": no.
- Tells: 15 asset, 12 rig. The judge's top 5 ranking:
  1. flat, uniform matte materials with no wear or finish (asset)
  2. simplified, chunky geometry (asset)
  3. an empty gradient cyclorama with a soft light pool (rig)
  4. no sensor noise, grain or grading, so the image is "too clean" (rig)
  5. blank optics and a faceted lens rim (asset)
- The r2 rig tells are gone from the list: the hard seam, the blown elliptical pools, the blocky floor patches, the
  float or gap, and the path-tracer grain.
- Next rig steps, if the gun chat ports this:
  - a light post pass: sensor grain of about 1-2 % luminance, a gentle vignette and a touch of chromatic aberration
  - a non-empty set, i.e. a real surface such as a wooden bench or a mat instead of the bare sweep, which the user
    would have to approve as staging
- The main remaining gap is the asset (materials and geometry), as in FINAL_JUDGES.

## rig 2b: grain + grade

Answers the rig-2 judge's last render tell ("too clean, no grain or grading"). Code: `photo_finish()` in
`Scripts/guns/sniper/sr_review_job.py` (gunlib untouched). It is on for every rig2 shot (`shot["render"]`) by default;
turn it off with `sr_review_export.py --rig2 --no-finish` (or `render["finish"]: false`, or `--no-finish` on the job).
Non-rig2 and transparent shots render with no compositor. Renders: `review/rig2b/realism/` (5 shots, from the shipped
exports, 384 spp denoised as rig 2); side-by-side `review/rig2b/compare_grade.png` (rig2 left, rig2b right).

Blender 5.2 compositor: the node group goes on `scene.compositing_node_group` (a `CompositorNodeTree` with an `Image`
output socket and a `NodeGroupOutput`, because 5.x has no Composite node). Shader Math/Mix/Noise nodes run inside it.
It works in scene-linear, before AgX - Medium High Contrast (exposure -1.1). The chain:

| Step | Node | Settings |
|---|---|---|
| Lateral CA | `CompositorNodeLensdist` | Distortion 0.0, Dispersion **0.006**, Jitter off, Fit off |
| Black lift | `CompositorNodeColorBalance` | Type Offset/Power/Slope (ASC-CDL), Offset **+0.002**; Power/Slope 1; white balance untouched (neutral) |
| Mild S | `CompositorNodeCurveRGB` | combined curve, extrapolated, points (0,0) (0.05,0.045) (0.18,0.18) (0.6,0.63) (1,1): pivot at mid grey |
| Vignette | `CompositorNodeImageCoordinates`.Uniform → VectorMath LENGTH r → `1 − 0.07·r²` | corners ×0.89 at 16:9 |
| Grain | `ShaderNodeTexNoise` 4D, W 0.37, Scale **1.3** on `.Pixel` coords (~1 px at 1920), Detail 0 → `1 + 0.22·(n − 0.5)` | multiplicative = luminance-only (the same factor on R, G and B) |
| Apply | `ShaderNodeMix` RGBA MULTIPLY, factor 1: graded image × (vignette × grain) | |

Measured, rig2 → rig2b: flat backdrop patch std 0.55 → 1.63 (hero) and 0.77 → 2.04 (tp_3m) on 8-bit L (grain about 1.5/255),
corner mean −3.4/255, frame mean −0.6 to −0.9/255. Looked at the full frames and a 1:1 crop: the grain only shows
at 1:1, and the CA and vignette read as a lens, not a filter, so the settings were not dialled down. No judge run (out of scope).
For gunlib: port `photo_finish()` along with rig 2; the defaults live in the `FINISH` dict.
