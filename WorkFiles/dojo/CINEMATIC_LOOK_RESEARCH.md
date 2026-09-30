# Cinematic look for the DojoLab dojo (UE 5.8 + Ultra Dynamic Sky): research

Written 2026-09-29 by a research-only session: no Unreal project was opened, run or changed. Sources are the Epic docs
and release notes for 5.6-5.8, the UDS 9.7 readme and tooltips read as text from the UDS assets on disk (read-only), and
a few industry pages. The links are at the end. Every value below is a **starting point to measure in the level**,
not a measured result. Tags used:

- **[5.8?]**: the name or default could not be confirmed for 5.8. Check it in the console (autocomplete shows the
  current value) or in the Details panel before relying on it.
- **[exp]**: the feature is Experimental or Beta in 5.8.
- **[measure]**: the cost or result depends on this scene. Measure it (list in section 7).

Hardware assumed from `DemoGame_1/Docs/Scenery_Options.md`: RTX 4070 SUPER (12 GB), 32 GB RAM. The gameplay target is
60 fps at 1440p output.

---

## 0. Summary

1. **The flat look comes from our own overrides, not the engine.** The current unbound PPV (`look_r3.py` ENV) lifts
   the shadows in five ways at once:
   - film Toe 0.28 (the default is 0.55);
   - Local Exposure Shadow Contrast 0.5;
   - Lumen Diffuse Color Boost 3.0;
   - Lumen Skylight Leaking 0.1;
   - a sky light at 9.
   On top of these, the sun is 420 lux under manual exposure, the sky is an emissive painted dome (intensity 148), and
   extra fill lights are placed.
   A dusk reference with deep eave shadows needs:
   - the tone curve back at defaults;
   - local exposure at about 0.8-1.0;
   - Lumen boost 1 and leaking 0;
   - the contrast judged against the reference only (the round-6 lesson).
2. **Gameplay (60 fps):**
   - Lumen GI and reflections with hardware ray tracing in **Surface Cache** lighting mode;
   - virtual shadow maps at the scalability defaults;
   - TSR at about 67-75 % screen percentage for 1440p (or the NVIDIA DLSS plugin, which has a 5.8 build);
   - volumetric fog ON, for the dusk shafts under the eaves;
   - UDS in Game/Real-time mode, with Volumetric Clouds in "Fidelity + Performance" mode (Static Clouds as the fallback);
   - post effects kept subtle: no DOF, no chromatic aberration, no grain, light motion blur.
3. **Showcase and trailer:**
   - Movie Render Graph (Production Ready in 5.8) or MRQ;
   - UDS Project Mode "Cinematic / Offline" and cloud mode "Full Cinematic Quality";
   - Lumen Hit Lighting and Final Gather Quality 4;
   - scalability at Cinematic (4);
   - anti-aliasing override None with 8-32 samples, 64-120 warm-up frames, EXR output;
   - no high-res tiling (it breaks Lumen and other screen-space effects);
   - path tracer only for a few hero stills.
4. **UDS replaces all of these:** DirectionalLight, SkyLight, ExponentialHeightFog, SkyAtmosphere, VolumetricCloud,
   **and our painted sky dome**. Two more steps:
   - the exposure overrides in our PPV must be switched off, or UDS's "Apply Exposure Settings" disabled, so that one
     system owns exposure;
   - every emissive (ridges, shoji, lamps) must be recalibrated after the exposure changes.
5. **Capture:** UE's VolumetricCloud did not show in our SceneCapture2D stills. UDS's volumetric mode drives that same
   engine component, so expect the same. Judge and ship stills from a `-game` HighResShot or from MRQ/MRG, not from
   SceneCapture2D. SceneCapture also runs Lumen at a reduced surface-cache scale (0.5 by default), so it is not a
   faithful judge of the in-game look anyway.

---

## 1. Where the dojo stands (from DOJO_QUEUE rounds 5-7 and the scripts)

- `Scripts/dojo/unreal/dj_sc_level.py` currently builds:
  - a movable DirectionalLight (`look_r3`: elevation 13-14 deg, 5000-5600 K, **420 lux**, source angle 0.3, contact
    shadows 0.04);
  - SkyAtmosphere (luminance factor ~3.8/2.8/2.5, height-fog contribution 0);
  - an optional engine VolumetricCloud;
  - a real-time-capture SkyLight (intensity 9);
  - ExponentialHeightFog (density 0.014, falloff 0.18, explicit inscatter, directional lobe);
  - an emissive **painted sunset sky dome** on SM_SkySphere (intensity 148);
  - an unbound PPV with **manual exposure** and bias;
  - point lights at the lamps (candela x LAMP_SCALE), plus FILL_LIGHTS.
- PPV extras:
  - Lumen Final Gather / Scene Lighting / Scene Detail 2.0;
  - Diffuse Color Boost 3.0, Skylight Leaking 0.1;
  - Local Exposure Shadow Contrast 0.5;
  - film Toe 0.28;
  - vignette 0.42.
- Round 6 lesson (DOJO_QUEUE): the gates "no region >10 % near-black" and "sunlit tile R/B <= 1.2" pushed the look to
  a hazy flat afternoon. Ref 2 has 12.8 % of pixels under luma 40; ours had 1.9 %. Round 7 (running in its own
  workflow) judges against the reference. **Do not apply this report inside round 7's workflow.** A UDS switch is its
  own round, because it replaces every light and exposure value round 7 is tuning.
- DojoLab `Config/DefaultEngine.ini` already has:
  - Lumen GI and reflections (`r.DynamicGlobalIlluminationMethod=1`, `r.ReflectionMethod=1`);
  - VSM, mesh distance fields, `r.RayTracing=True`, Substrate (`r.Substrate.ProjectGBufferFormat=0`, the Blendable
    GBuffer), Nanite plus Nanite foliage, TSR (`r.AntiAliasingMethod=4`);
  - project motion blur off;
  - local exposure project defaults 0.8/0.8;
  - `r.SupportSkyAtmosphereAffectsHeightFog=True`, local fog volumes;
  - `r.Lumen.HeightFog=0`.
  `r.MSAACount=8` does nothing under TSR, because MSAA applies only to the forward renderer.
- Tom Looman's 5.8 notes list `r.Lumen.HeightFog` with a default of 1. DojoLab forces 0 (inherited from DemoGame_1).
  Check what it changes before keeping it **[5.8?][measure]**.

---

## 2. Real-time "cinematic realism" settings (UE 5.8)

Where each setting lives: **PS** = Project Settings (DefaultEngine.ini), **PPV** = PostProcessVolume (or camera post
settings), **CVar** = console / DefaultEngine `[SystemSettings]` / DefaultScalability.ini, **UDS** = a UDS actor
property.

### 2.1 Lumen (GI, reflections, translucency)

| Setting | Recommended | Why | Cost |
|---|---|---|---|
| GI / reflection scalability `sg.GlobalIlluminationQuality` / `sg.ReflectionQuality` (CVar) | 3 (Epic) for the 4070S at 67-75 % screen %; 2 (High) as the fallback | Epic's guide: **High = the 60 fps console budget (about 4 ms)**, **Epic = the 30 fps console budget (about 8 ms at 1080p)**. A 4070S at a reduced internal resolution usually sits between them **[measure]** | the largest single GPU item |
| Medium (1) = **Lumen Lite** [exp: Beta in 5.8] | only as the low preset | Irradiance-field final gather (`r.Lumen.FinalGatherMethod 0`), about 2x faster; reflections fall back to SSR. A 5.8 forum report shows black blocks under moving objects, a risk for a character game | about half of High |
| Use Hardware Ray Tracing when available (PS; `r.Lumen.HardwareRayTracing=1`) | ON (already on through `r.RayTracing=True`) | Traces real triangles and skinned meshes; better thin timber and kumiko than distance fields | Keep the RT scene under ~100 k instances after culling (Epic's console guidance). The dojo has 8.47 M tris and ~370 draws, so it is fine **[measure]** |
| Ray Lighting Mode (PS / PPV; `r.Lumen.HardwareRayTracing.LightingMode` [5.8?]) | **Surface Cache** for gameplay; **Hit Lighting for Reflections** for the showcase | Hit lighting evaluates real materials and lights at the hit point, for correct specular in reflections | Hit lighting in reflections costs about +0.5-1 ms (AMD GPUOpen / guides) **[measure]** |
| Screen traces (PPV Lumen GI / Reflections) | ON (default) | They hide mismatches between the Lumen scene and the triangles; the Lumen doc warns that screen traces make indirect-lighting art direction view-dependent | small |
| Final Gather Quality (PPV) | 1.0 gameplay; 2-4 showcase | Less GI noise and smoother bounce under eaves | "greatly increase GPU cost" (engine tooltip); about linear |
| Lumen Scene Lighting Quality / Scene Detail (PPV) | 1.0 / 1.0 gameplay; 2-4 showcase | Cleaner reflections; small props kept in the Lumen scene | moderate |
| Final Gather Lighting Update Speed (PPV) | 1 (fixed time of day); 2 only if the time of day animates | UDS readme: Lumen lags fast sky changes; UDS itself does not touch Lumen | more GPU |
| **Diffuse Color Boost** (PPV) | **1.0** (now 3.0) | Values above 1 add bounce from dark albedos: a flattening "fill" | none |
| **Skylight Leaking** (PPV) | **0** (now 0.1); at most 0.02-0.05 if the deepest crevices go black | Leaking is ambient added everywhere, which kills eave contrast | none |
| Max Trace Distance / Scene View Distance (PPV) | defaults (200 m view) | The courtyard is small; far ridges are impostors | more when raised |
| High Quality Translucency Reflections (PS, `r.Lumen.TranslucencyReflections.FrontLayer.EnableForProject`) | keep False | No water or glass in the dojo; UDS asks for it only for water | about a second reflection pass |
| Far Field (`r.LumenScene.FarField=1`) | off | Needs World Partition HLOD1; our far ring is impostors | - |

### 2.2 MegaLights [Production Ready in 5.8]

- **Not needed for the sun.** Epic's MegaLights doc: use Deferred lighting + VSM for a strong directional light.
  Directional support stays opt-in (`r.MegaLights.DirectionalLights 1`).
- Consider it once many lanterns, shoji rect lights and street lamps cast shadows. Its cost stays constant however many
  lights there are, it lights volumetric fog and translucency, and it needs HW RT (which we have). Enable in
  PS > Rendering > Direct Lighting (`r.MegaLights.EnableForProject` [5.8?]); switch off per scalability level with
  `r.MegaLights.Allow 0`.
- Watch for noise and ghosting when many lights overlap one pixel. Keep attenuation radii tight **[measure]**.

### 2.3 Shadows (virtual shadow maps, contact shadows, sun source angle)

| Setting | Recommended | Why / cost |
|---|---|---|
| VSM (PS `r.Shadow.Virtual.Enable=1`) | ON | Film-grade sharp contact detail; Nanite geometry is cheap in the shadow pass, non-Nanite is not (VSM doc) |
| `r.Shadow.Virtual.ResolutionLodBiasDirectional` | gameplay: the scalability default; showcase: -1 (twice the resolution) | Each -1 doubles resolution and cost; `...DirectionalMoving` applies while the sun moves (only with an animated time of day) |
| SMRT soft shadows `r.Shadow.Virtual.SMRT.RayCountDirectional` / `SamplesPerRayDirectional` | 8 / 8 (the Epic default); showcase 16 / 8 [5.8?] | Contact-hardening penumbrae; cost scales with rays |
| Sun **Source Angle** (the light, or UDS "Sun Source Angle Scale") | **0.53 deg** (real sun, the engine default 0.5357); **not 0.3** | Low sun = long shadows that should soften with distance; 0.3 reads CG-crisp. UDS derives the angle from its Sun Scale (it also widens it with cloud and fog) |
| Contact shadows (light Contact Shadow Length) | 0 to 0.02 | The VSM doc says VSM makes contact shadows unnecessary; keep only for tiny props that do not cast into the VSM. Cheap, but screen-space halos on characters |
| Shadow cache invalidation | keep the sun static (fixed time of day); set a **WPO Disable Distance** on future foliage | Sun movement invalidates all pages; WPO/PDO materials invalidate every frame. UDS "Lights Update" settings throttle updates when time animates |
| Distance-field shadows | not needed with VSM | - |

### 2.4 Anti-aliasing and upscaling

| Setting | Gameplay | Showcase | Notes |
|---|---|---|---|
| Method (PS `r.AntiAliasingMethod`) | 4 = TSR (keep) | TSR, or None under MRQ sample accumulation | - |
| Screen % (`r.ScreenPercentage`, or `sg.ResolutionQuality`) | 67-75 at 1440p output (about 1080p internal) | 100 (MRQ) or up to 150 for stills | TSR doc: about 0.43 ms at 50 %, 0.79 ms at 100 % (console figures). Below 50 % only for >4K outputs |
| `r.TSR.History.ScreenPercentage` | 100 (the High default); 200 if it fits (the Epic default) | 200 | 200 = a sharper history, more cost |
| `r.TSR.ShadingRejection.Flickering` | 1 (the Epic default) | 1 | Stops shimmer on tile rows and raked sand |
| NVIDIA DLSS plugin (optional) | DLSS Quality or DLAA; **Ray Reconstruction** can replace the Lumen denoise | - | NVIDIA lists a UE 5.8 plugin build; it is a third-party plugin (.uproject change, ask the user first) **[measure]** |

### 2.5 Tonemapper, exposure, grading

**Tonemapper (PPV > Film).** Epic defaults: Slope 0.88, **Toe 0.55**, Shoulder 0.26, Black Clip 0, White Clip 0.04.
- Restore the Toe to 0.55; ours is at 0.28, which lifts the blacks.
- For a punchier dusk, raise Slope to about 0.92-0.95 rather than lifting anything.
- Leave Black Clip alone (Epic advises against changing it).

**Auto exposure** (PPV > Exposure, or UDS > Exposure; **only one of them may own it**). A sunset is a fixed and very
high dynamic range: the sky is about 4-6 EV brighter than the shaded courtyard.
- Metering: **Auto Exposure Histogram**, with a **narrow range**: Max EV100 minus Min EV100 of about 1.5-2 EV. It
  follows the camera under the eaves a little but cannot "fix" the dusk into an afternoon.
- Alternative: **Manual** with an Exposure Compensation. That is deterministic and best for matching the reference;
  ours is manual now.
- Histogram Low / High percent 70-80 / 80-95 (Epic doc); Speed Up about 3, Speed Down about 1 f-stop/s.
- Exposure Compensation: set it on the ref-2 camera by the luma histogram, targeting about 12-13 % of pixels under luma
  40 as ref 2 has.
- Use Show > Visualize > HDR (Eye Adaptation) to see what it is doing (UDS readme tip).
- `r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange=True` is already on, so the range is in EV100.
- Real-world photographic EV100 values: sunset scene about 11-13, just after sunset about 9-10, open shade at dusk
  lower. These are rules of thumb, not Epic numbers. Our intensities are not physical (a 420 lux sun), so tune by the
  histogram, not by these values.

**Local exposure** (PPV > Local Exposure; project defaults 0.8/0.8 already):
- Highlight Contrast Scale 0.8 keeps the sky from clipping.
- **Shadow Contrast Scale 0.8-1.0, not 0.5.** Below 1 lifts the shadows, which is the anti-black rule in another form.
- Detail Strength 1, Method Bilateral.
- Tooltips (read in the UDS asset): "Value less than 1 will enable local exposure".

**White balance** (PPV > Temperature; Temperature Type = White Balance):
- Leave it neutral (6500) and let the sun and sky colours carry the warmth.
- In White Balance mode, Temp is the light colour being neutralised: **lower Temp gives a cooler image, higher Temp a
  warmer one** [verify on screen].
- Use Tint for a slight magenta/green correction only.

**Colour grading** (PPV > Color Grading). Keep it small and reference-driven:
- Global Saturation 1.0-1.05, Contrast 1.0-1.05.
- Shadows: gain slightly cool, e.g. (0.98, 0.99, 1.03), for the blue dusk shade.
- Highlights: gain slightly warm.
- No global Gain or Offset lift.
- Blue Correction default; Expand Gamut default.

**LUT:** Epic's doc prefers the grading controls, because a LUT works after the tonemapper in sRGB and does not carry to
HDR output. If a LUT is wanted:
- grade a neutral-LUT screenshot in Resolve;
- import it as a 256x16 texture in the ColorLookupTable group, no mips, sRGB;
- LUT Intensity 0.3-0.6.
Cost: effectively zero.

### 2.6 Lens and camera effects

| Effect (PPV) | Gameplay | Showcase | Why / cost |
|---|---|---|---|
| Bloom (Standard) | Intensity 0.4-0.675 (0.675 is the UE5 default [5.8?]), Threshold -1 | same, or **Convolution** for hero sun shots | Convolution is expensive and "not conservative" (it brightens); Epic keeps it for cinematics |
| Lens flare (image-based) | 0 (or 0.05-0.1) | 0.1-0.3 when the sun is in frame | Cheap; UDS has its own **Sun Lens Flare**, better for sun-in-frame trailer shots |
| Vignette | 0.3-0.45 (now 0.42; the default is 0.4) | 0.4-0.5 | free |
| Film grain (Film Grain Intensity, Texel Size, Shadows / Midtones / Highlights) | 0 | 0.08-0.2 (round 5 used 0.15) | Adds a "film" feel and hides banding in the dusk sky; almost free. Per-tone intensities exist (Python API PostProcessSettings) |
| Chromatic aberration (Scene Fringe Intensity, Start Offset) | 0 | 0.1-0.25 with Start Offset 0.5-0.7 (edges only) | Subtle only; strong CA reads as a cheap lens |
| Depth of field (Cinematic DOF, CineCamera) | OFF (a 1v1 needs clarity); a shallow DOF only in scripted finisher cameras | CineCamera 35-50 mm, f/2.8-5.6, manual focus; 5.8 adds **Accumulation DOF** in MRG for film-quality bokeh | Cinematic DOF costs about 1-2 ms at high quality **[measure]**; `r.DepthOfFieldQuality` 4 for MRQ |
| Motion blur (Amount, Max, Target FPS) | Amount 0.25-0.35, Max 2-3 %, per-object on (project default off now: `r.DefaultFeature.MotionBlur=False`, so set it in the PPV); give players an option | Amount 0.5 (a 180-degree shutter) with MRQ temporal samples | Cheap; strong blur hurts combat readability |
| Screen-space light shafts (light shaft bloom; UDS "Screen Space Light Shafts" category) | optional (cheap, only when facing the sun) | ON for sun-facing shots | Separate from volumetric fog |

### 2.7 Fog, atmosphere, clouds (the sunset haze and the god rays)

- **Sky Atmosphere:**
  - Rayleigh/Mie scattering sets the sunset colour; Mie gives the haze; Absorption (UDS: Sunset/Sunrise and Twilight
    values) makes stronger sunsets.
  - Aerial Perspective View Distance Scale thickens distance haze.
  - With `r.SupportSkyAtmosphereAffectsHeightFog=True`, fog colour comes from the atmosphere: set the fog inscatter
    colours black and use Height Fog Contribution (Epic).
  - Quality CVars: `r.SkyAtmosphere.SampleCountMax`, `r.SkyAtmosphere.FastSkyLUT` (keep FastSkyLUT on in gameplay).
    Cheap.
  - Keep the atmosphere "ground" below the lowest camera, or the sky can flicker black (UDS readme).
- **Exponential Height Fog:** UDS drives density, falloff and start distance from Cloud Coverage / Fog / Dust. Our
  hand-set values (0.014 / 0.18) become UDS Fog / Dust inputs.
- **Volumetric fog** (on the height fog; UDS "Volumetric Fog" category) is **the key element for the dusk shafts
  through the eaves and gate**:
  - sun Volumetric Scattering Intensity 1-2;
  - Scattering Distribution 0.6-0.8, forward-scattering toward the low sun;
  - Albedo about 0.9; Extinction Scale 1;
  - View Distance 3,000-6,000 cm (the courtyard only).
  - Quality comes from the **Shadow** scalability group: `r.VolumetricFog.GridPixelSize` (gameplay 16, showcase 4-8)
    and `r.VolumetricFog.GridSizeZ` (gameplay 64, showcase 128-256) [5.8?: read BaseScalability.ini].
  - Cost: Epic quotes about 1 ms on PS4 High and 3 ms on a GTX 970 at Epic, so it should be small on a 4070S
    **[measure]**.
  - Shadow-casting point and spot lights in fog cost about 3x. Keep lamp Cast Volumetric Shadow off except one or two
    hero lanterns.
- **Local Fog Volumes** (project support on) for ground haze in the yard and the alley. Cheap. Our ini has
  `r.LocalFogVolume.ApplyOnTranslucent=False`.
- **FSSS (Fog Screen Space Scattering)** [exp, 5.8]: approximates multiple scattering in fog. Not for clouds yet. Skip
  for gameplay; try it on a showcase shot.
- **Volumetric clouds (through UDS, section 3):** Epic's cloud CVars are `r.VolumetricCloud.ViewRaySampleCountMax`,
  `r.VolumetricCloud.Shadow.*` and `r.VolumetricCloud.ShadowMap.MaxResolution`. The screen-reconstruction mode is
  `r.VolumetricRenderTarget.Mode`, which UDS sets for you.

### 2.8 Materials (Substrate: plaster, timber, tile)

Substrate has been production-ready since 5.7. The project uses the Blendable GBuffer
(`r.Substrate.ProjectGBufferFormat=0`), which is cheaper and fine for these surfaces.
- **Plaster:** one Slab. Roughness 0.8-0.95, specular about 0.5 (F0 0.04). Albedo about 0.55-0.7 linear for white
  plaster, never 1.0 (the path tracer doc warns about near-1 albedo). A macro dirt / rain-streak layer through decals
  (already there).
- **Timber:** Slab. Roughness 0.55-0.8 (lacquered parts 0.3-0.45). Keep the real grain normal. **Remove the
  "FlattenToMean" / low AOStrength crutches** once the lighting is honest: they were added to fight the near-black
  gate.
- **Kawara tile:** Slab. Roughness 0.4-0.6 with some variation, so the low sun gives the glancing sheen seen in
  references. Albedo dark charcoal (R about G, slightly cool).
- **Shoji glow:** a thin translucent or two-sided subsurface (Substrate thin-surface) paper lit by a **rect light
  behind it**, with only modest emissive. Emissive alone gives little light and noisy Lumen GI.
- Glass and water are absent, so no translucency cost.

### 2.9 Nanite and foliage

- Everything static goes to Nanite (the VSM doc: even low-poly meshes benefit). Nanite foliage is on in the ini
  (`r.Nanite.Foliage=True`).
- For the pending vegetation pack:
  - set WPO Disable Distance (wind only near the camera);
  - check the VSM cache and invalidations (Show > Visualize > Virtual Shadow Map cache);
  - with Lumen HW RT, foliage uses the ray-tracing proxies (`r.RayTracing.RayTracingProxies.ProjectEnabled=True` is
    set).
  - Megaplants are extremely heavy: a few at the edge, not a forest.

### 2.10 Scalability groups and CVars

- Groups: `sg.ResolutionQuality`, `sg.ViewDistanceQuality`, `sg.AntiAliasingQuality`, `sg.ShadowQuality`,
  `sg.GlobalIlluminationQuality`, `sg.ReflectionQuality`, `sg.PostProcessQuality`, `sg.TextureQuality`,
  `sg.EffectsQuality`, `sg.FoliageQuality`, `sg.ShadingQuality`, `sg.LandscapeQuality`.
- Levels 0-3 = Low-Epic; 4 = Cinematic (the UDS tooltip also maps 4 = cinematic). Cinematic is for offline rendering.
- Put project overrides in `Config/DefaultScalability.ini` under sections such as `[ShadowQuality@3]`. Player choices
  go through GameUserSettings.
- Volumetric fog belongs to the Shadow group (Low and Medium disable it). UDS materials follow the material quality
  level, and UDS can switch its sky mode by Effects Quality ("Use Sky Mode Scalability Map").

---

## 3. Ultra Dynamic Sky (version 9.7 on disk, saved with UE 5.5)

Everything in this section comes from the in-content readme (`Blueprints/System/Editor_UI/UDS_Readme_Entries`), the
`UDS_VolRT_Mode` enum tooltips and the `Ultra_Dynamic_Sky` tooltips, read as text. The online copy is
<https://www.ultradynamicsky.com/Documentation/V9/9-7>. The version string (9.7) comes from `UDS_CurrentVersion`.

### 3.1 Getting it into DojoLab (never write under DemoGame_1)

- **Dependencies (scanned, all 848 assets):**
  - Content references only `/Game/UltraDynamicSky/...` and engine modules: Niagara, UMG, MetaSound,
    EditorScriptingUtilities (enabled in DojoLab), Blutility, MovieScene.
  - Two soft references to the **Water** plugin classes, used only for the water-level feature (optional, not needed).
  - No project settings are required. It works best with the defaults we already have:
    `Support Sky Atmosphere Affecting Height Fog` ON, mesh distance fields ON (for UDS ground fog, and weather
    particles on UDW).
- **How to copy it:**
  - Preferred: add UDS to DojoLab from the owner's Fab library, taking the newest build for 5.8 if Fab offers one.
  - Alternative: a plain **file copy** of `DemoGame_1/Content/UltraDynamicSky` to `DojoLab/Content/UltraDynamicSky`.
    It is self-contained, so the folder path must stay `/Game/UltraDynamicSky`.
  - Do not use Migrate from DemoGame_1: that opens DemoGame_1 in the editor.
  - The first load in 5.8 compiles many shaders.
- **Adding it** (readme, "Adding Ultra Dynamic Sky to Your Level"):
  1. Remove any DirectionalLight, SkyLight, ExponentialHeightFog, SkyAtmosphere and VolumetricCloud from the level.
  2. Drag `Blueprints/Ultra_Dynamic_Sky` into the level **at ground level** (Z about 0, the courtyard floor). Change
     cloud height with Bottom Altitude, never by moving the actor.
  3. Optionally add `Ultra_Dynamic_Weather` (not needed for a clear sunset).
  - UDS offers to convert an existing lighting setup if you leave the actors in. **Do not use that here.** Our
    lights are hand-tuned and non-physical; delete them in the level script instead (`dj_sc_level.py` would spawn the
    UDS class instead of the five actors).

### 3.2 What UDS drives, and what of ours conflicts

| Ours now | With UDS | Action |
|---|---|---|
| DirectionalLight (sun) | UDS **Sun** component: colour, intensity, cast shadows, source angle, cloud shadows (plus the Moon) | Delete ours. Edit other sun properties on UDS's Sun component; use "Custom Sun Light Actor" only if a plugin needs an actor (then copy Cloud Scattered Luminance Scale by hand) |
| SkyLight (real-time capture, 9) | UDS Sky Light (mode: Capture Based / Custom Cubemap / Cubemap with Dynamic Color Tinting) | Delete ours |
| SkyAtmosphere (luminance factor hack) | UDS Sky Atmosphere component (Color Mode = Sky Atmosphere) | Delete ours. Move UDS's Sky Atmosphere component below the lowest camera if the sky flickers black |
| ExponentialHeightFog (hand values, explicit inscatter) | UDS fog (Fog Density / Fog Color categories; Volumetric Fog category) | Delete ours. Our inscatter look moves to UDS Fog / Dust / Fog Color |
| Engine VolumetricCloud | UDS Sky Mode | Delete ours |
| **Painted sky dome** (SM_SkySphere, emissive 148) and the sunset sky texture | UDS sky material | **Delete it**: it would cover UDS's sky and double the sky light |
| Unbound PPV exposure overrides (manual + bias) | UDS "Apply Exposure Settings": exposure compensation curve, bias by time and weather, metering mode, Min/Max EV100 ("Exposure Brightness Range"), applied on a UDS post-process component | **Pick one owner.** Either untick the exposure overrides in our PPV (UDS readme: the usual cause of a black level), or untick UDS Apply Exposure and keep ours |
| PPV Lumen, local exposure, film, grade | UDS does not touch Lumen; it sets local-exposure contrast by EV100 only if its exposure is applied [verify] | Keep our PPV for these, but with the values from section 2 |
| Emissive ridges, shoji, lamps (candela x LAMP_SCALE), FILL_LIGHTS | unaffected, but the exposure changes | After exposure settles, multiply all emissive and candela values by 2^(ΔEV). Drop the fill lights that only existed to fight near-black |
| Lamp on/off | UDS "Light Day/Night Toggle" component (Blueprints/Utilities) | optional, for a later animated time of day |

### 3.3 A locked sunset

- Basic Controls:
  - **Time of Day**: 0-2400, or type "18:40" in Time of Day String.
  - **Dusk Time**: the time the sun crosses the horizon.
  - Set Time of Day about 20-40 in-game minutes before Dusk Time, for a sun elevation of about 10-14 deg (look_r3 uses
    12-14 deg) **[measure the elevation from the Sun component rotation]**.
- **Lock it:** Animate Time of Day OFF (the "Animate Time of Day" category). With it off, time does not move at
  runtime.
- **Aim it:** Sun category "Sun Yaw" (the path yaw) to put the sun behind-left of the hall as in round 5. Or, for
  exact art direction, enable **"Manually Position Sun Target"** and drag the Sun Target widget. Keep Simulate Real Sun
  OFF.
- **Multiplayer:** Time of Day replicates. For the 1v1, the server's fixed value is what everyone sees.
- **Brightness:** "Lighting Brightness" values for Day / Dawn-Dusk / Night art-direct the light relative to the sky
  colour. Sky Atmosphere Sunset/Sunrise and Twilight values control absorption, for a stronger coloured sunset.
  Saturation and Contrast are also in Basic Controls.

### 3.4 Clouds

- Sky Mode choices, in order of cost:
  - **Volumetric Clouds**: most realistic, most expensive.
  - **2D Dynamic Clouds**: much cheaper.
  - **Static Clouds**: cheaper still; a baked multi-angle texture made to look like the volumetrics.
  - No Clouds.
  - Cloud Wisps (a high static layer) render behind every mode.
- **Volumetric Cloud Rendering Mode** (it sets `r.VolumetricRenderTarget.Mode` and `r.VolumetricRenderTarget`); the
  enum tooltips give:
  - **Fidelity + Performance**: the default. Detailed, cheap, ghosts in fast motion, poor mesh intersections. **Right
    for gameplay**: our clouds are a slow background.
  - Mesh Intersections + Fast Movement + Performance: blurrier clouds. For cameras inside clouds.
  - Mesh Intersections + Fast Movement + Fidelity: "significantly more expensive", but "feasible" for high-end
    real-time.
  - **Full Cinematic Quality**: no optimisations. "NOT for realtime". **Use it for trailers and stills.**
- **Coverage:** Basic Controls > Cloud Coverage. For a dramatic lit sunset, broken-to-scattered cloud (low-to-mid
  values) so the sun can light cloud undersides [exact scale: read the tooltip]. Also Volumetric Clouds Scale, Bottom
  Altitude, and View / Shadow Sample Scale (noise versus cost).
- **Animation:** Cloud Speed can stay low. For repeatable trailers: Cloud Speed 0, "Randomize Cloud Formation on Run"
  OFF, "Clouds Move with Time of Day" OFF, and keyframe **Cloud Phase** in Sequencer.
- **Cloud shadows:** on by default, and correct in 3D for volumetric mode. Enable "Correct Specular Scale For Low
  Angle Cloud Shadows" if the sunset sun glints through cloud.
- **Volumetric Cloud Light Rays:** Niagara ray cards through gaps in the clouds. Cheap by default; "Individual Cloud
  Light Rays" costs more.

### 3.5 Exposure at sunset with UDS

- UDS applies histogram auto exposure by default. Its **Exposure Compensation Curve** pushes brightness by the scene
  EV100; a physical-values curve variant exists if Sun Light Intensity is very high. It also sets Exposure Bias per
  time and weather, and Min/Max EV100.
- For our look:
  - keep the time fixed;
  - either set UDS **Exposure Metering Mode = Manual** and tune the dusk bias (deterministic, closest to what the
    reference work needs), or keep auto with a **narrow Exposure Brightness Range** (about 1.5-2 EV) so the dusk
    stays dark;
  - check with Show > Visualize > HDR (Eye Adaptation).
- UDS also boosts the adaptation speed for the first half second after play (a tooltip), so the opening frame will
  not start mis-exposed.

### 3.6 Performance knobs specific to UDS

- **Project Mode = Game / Real-time** for play. Cinematic mode "will severely impact performance". Switch back after
  every movie render.
- Half Rate Tick ON (the default; UDS ticks every other frame above 45 fps).
- Sky Light Mode "Cubemap with Dynamic Color Tinting" removes the real-time capture cost. With a fixed time, a capture
  based light is fine.
- Color Mode "Simplified Color" is cheaper, but it drops the Sky Atmosphere; keep Sky Atmosphere for realism.
- Volumetric fog "has a very significant rendering cost"; UDS's Global Volumetric Material adds some more.
- CPU: UDS is a large Blueprint. Check `stat game` / Insights in `-game` **[measure]**.

### 3.7 Captures: SceneCapture2D versus the real frame

- Our finding: the engine VolumetricCloud does not appear in SceneCapture2D stills (`dj_sc_capture.py` uses
  SCS_FINAL_COLOR_LDR with Always Persist Rendering State). UDS volumetric mode is that same component with a UDS
  material, so **expect UDS volumetric clouds to be missing or wrong in SceneCapture2D as well** **[measure]**.
  Forum threads report cloud grid artifacts and cost in scene captures, with no confirmed fix.
- The UDS sky dome itself, Cloud Wisps and the Static or 2D cloud modes are sky-material effects. They **should**
  appear in a capture **[measure]**.
- SceneCapture also renders Lumen with a smaller surface cache (an engine tooltip: "Scale factor for Lumen Surface Cache
  resolution, for Scene Capture. Defaults to 0.5"). Judging look from SceneCapture is therefore biased.
- **Capture instead with one of these:**
  1. **Standalone `-game` screenshots** (`run_game_perf.ps1` already launches an offscreen `-game`): place the view on
     a CAM_* camera, let it settle 5-10 s (Lumen, clouds, exposure), then `HighResShot 3840x2160` or `HighResShot 2`.
     Add `bCaptureHDR=1` for EXR. Syntax:
     `HighResShot filename=PATH (XxY | Multiplier) CaptureX CaptureY CaptureW CaptureH bMaskUsingCustomDepth bDumpBufferVisualizationTargets bCaptureHDR bDateTimeAsFilename`.
     Temporal effects reset at the higher resolution. A settle delay (`r.HighResScreenshotDelay`, frames [5.8?]) or a
     plain `Shot` at the native window resolution avoids undersampled Lumen and clouds.
  2. **MRQ / Movie Render Graph** on a one-frame Level Sequence per camera: the most reliable, with warm-up frames
     (section 4).
- For the judge pipeline: switch the dojo stills to (1) or (2). If SceneCapture must stay for fast probes, set UDS
  Sky Mode = Static Clouds in probe runs and re-verify key shots through `-game`.

---

## 4. Showcase and trailer quality

### 4.1 Tool

- **Movie Render Graph** is Production Ready in 5.8, and new features are graph-only. Legacy MRQ presets still work.
- DojoLab's `.uproject` does not list the **Movie Render Queue** plugin (MovieRenderPipeline). Check the Plugins window;
  enabling it is a `.uproject` change, so ask the user first.
- Before each render:
  - UDS **Project Mode = Cinematic / Offline** (the UDS readme). Its "Cinematic / Offline Mode" category raises cloud
    view and shadow sample scales and the max sample count (the engine default is 768 in real time).
  - Cloud Rendering Mode = **Full Cinematic Quality**.
  - Afterwards, set both back.

### 4.2 Settings

| Item | Value | Source / why |
|---|---|---|
| Anti-aliasing | Override AA = **None**. Stills: Spatial 8-16, Temporal 1. Motion shots: Spatial 1, Temporal 8-16 (Epic's example: 1/64) | Epic MRQ docs: temporal samples are more efficient (static pixels get the same AA, moving ones get real blur); odd counts 9/15 are a common choice (industry guide) |
| Warm-up | Engine Warm Up 64-120, Render Warm Up 64-120 (Epic's example 120/120); "use camera cut for warm up" when the sequence has cuts | Lumen, VSM, volumetric-cloud history and exposure must settle |
| Scalability | Game Overrides > **Cinematic Quality Settings** ON (all sg.* = 4) | Epic MRQ docs |
| CVars (the MRQ Console Variables setting / MRG CVar node) | `r.MotionBlurQuality 4`, `r.MotionBlurSeparable 1`, `r.DepthOfFieldQuality 4`, `r.BloomQuality 5`, `r.Tonemapper.Quality 5` (Epic's list). Lumen through the PPV: Final Gather Quality 4, Scene Lighting Quality 2-4, Scene Detail 2-4, Reflections Quality 4, Ray Lighting Mode = Hit Lighting for Reflections. `r.Shadow.Virtual.ResolutionLodBiasDirectional -1`. `r.VolumetricFog.GridPixelSize 4`, `r.VolumetricFog.GridSizeZ 256` [5.8?] | Epic's MRQ page also lists `r.RayTracing.GlobalIllumination*` and `r.RayTracing.Reflections*`. Those drive the legacy ray-traced GI and reflections, not Lumen, and may be removed in 5.8 [5.8?]: **do not copy them** |
| Resolution | Native 3840x2160 (or up to 7680x4320 for key art) through Output Resolution, **without high-res tiling** | Tiling splits the frame; screen-space effects (Lumen screen traces, SSR, DOF, bloom, TSR, clouds' screen reconstruction) break at tile seams |
| Output | **EXR 16-bit** (linear, for grading) or ProRes / PNG for delivery. For a graded master, render with the tone curve and grade kept, or with the tone curve disabled plus OCIO for a colourist workflow | EXR keeps highlights for sky grading |
| DOF | CineCamera, Cinematic DOF; 5.8 **Accumulation DOF** in MRG for true multi-aperture bokeh | 5.8 release notes |
| Path tracer | Only for a few hero stills. Needs HW RT (on), UDS "**Adjust for Path Tracer**", and "Render Height Fog In Path Tracer Using Post Process" (on by default) | Path tracer: Sky Atmosphere needs a real-time-capture sky light or Reference Atmosphere; clouds only partial; height fog only approximate; bloom amplifies fireflies. Lumen plus MRQ usually wins for this stylised dusk |
| UDS extras | Sun Lens Flare ON for sun-facing shots; Screen Space Light Shafts ON; Volumetric Cloud Light Rays as they are | UDS readme |

### 4.3 A "capture-only" cinematic CVar preset (for the `-game` HighResShot path)

Apply these as a console batch in the `-game` capture run, never in the shipped config:

```
sg.ShadowQuality 4
sg.GlobalIlluminationQuality 4
sg.ReflectionQuality 4
sg.PostProcessQuality 4
sg.EffectsQuality 4
sg.TextureQuality 3
sg.ViewDistanceQuality 4
r.ScreenPercentage 100
r.TSR.History.ScreenPercentage 200
r.Shadow.Virtual.ResolutionLodBiasDirectional -1
r.VolumetricFog.GridPixelSize 4
r.VolumetricFog.GridSizeZ 256
r.DepthOfFieldQuality 4
r.MotionBlurQuality 4
r.BloomQuality 5
r.Tonemapper.Quality 5
```

Also set UDS Project Mode = Cinematic and the cloud mode to Full Cinematic Quality (through a capture-only Blueprint
call or a level variant), then wait about 10 s before the shot. Values marked [5.8?] in the tables above apply here too.

---

## 5. Recommended presets for the dojo

### 5.1 Gameplay (60 fps target, 1440p, RTX 4070 SUPER)

| Setting | Value | Where |
|---|---|---|
| Dynamic GI / Reflections | Lumen / Lumen (keep) | PS (`r.DynamicGlobalIlluminationMethod=1`, `r.ReflectionMethod=1`) |
| Use HW ray tracing when available | ON (keep) | PS (`r.RayTracing=True`, `r.Lumen.HardwareRayTracing=1`) |
| Ray Lighting Mode | Surface Cache | PS / PPV |
| High Quality Translucency Reflections | OFF (keep) | PS |
| GI / Reflection quality | Epic (3); fall back to High (2) if over budget | CVar `sg.GlobalIlluminationQuality`, `sg.ReflectionQuality` |
| Lumen Final Gather Quality / Scene Lighting Quality / Scene Detail | 1.0 / 1.0 / 1.0 (now 2 / 2 / 2) | PPV |
| Lumen Diffuse Color Boost / Skylight Leaking | **1.0 / 0** (now 3.0 / 0.1) | PPV |
| Final Gather Lighting Update Speed | 1 | PPV |
| Shadows | VSM ON; sg.ShadowQuality 3; SMRT defaults | PS / CVar |
| Sun source angle | 0.53 deg (UDS Sun Source Angle Scale 1) | UDS |
| Contact shadows | 0-0.02 | UDS Sun component |
| MegaLights | OFF for now (re-evaluate with the vegetation and more lamps) | PS |
| Anti-aliasing | TSR; screen % 67-75; `r.TSR.History.ScreenPercentage` 100 (200 if affordable) | PS / CVar (or the DLSS plugin, optional) |
| Exposure owner | ONE: UDS Apply Exposure ON with Metering **Manual** (or Histogram with a range of 1.5-2 EV), bias tuned on CAM_Ref2Match. Our PPV exposure overrides OFF | UDS / PPV |
| Film (tone curve) | Slope 0.88-0.95, **Toe 0.55**, Shoulder 0.26, Black Clip 0, White Clip 0.04 | PPV |
| Local exposure | Highlight 0.8, **Shadow 0.8-1.0** (now 0.5), Detail 1, Bilateral | PPV (project default 0.8 / 0.8) |
| White balance | 6500 neutral (fine-tune only) | PPV |
| Colour grading | Saturation 1.0-1.05, Contrast 1.0-1.05, a slightly cool shadow gain, no lifts; LUT optional at 0.3-0.6 | PPV |
| Bloom | Standard, 0.4-0.675, threshold -1 | PPV |
| Lens flare / UDS sun flare | 0 / OFF | PPV / UDS |
| Vignette | 0.35-0.42 | PPV |
| Film grain / chromatic aberration | 0 / 0 | PPV |
| Depth of field | OFF (finisher cameras only) | PPV / camera |
| Motion blur | Amount 0.25-0.35, Max 2-3 %; a player option | PPV |
| UDS Project Mode | Game / Real-time | UDS |
| UDS Sky Mode | Volumetric Clouds (Static Clouds on Low / Medium through the Sky Mode Scalability Map) | UDS |
| UDS Cloud Rendering Mode | Fidelity + Performance | UDS |
| UDS Color Mode | Sky Atmosphere | UDS |
| UDS Sky Light Mode | Capture Based (fixed time), or Cubemap with Dynamic Color Tinting if the capture cost shows | UDS |
| UDS time | Animate Time of Day OFF; Time of Day about Dusk Time minus 0:30 (sun about 10-14 deg); Sun Yaw or Manual Sun Target for the azimuth | UDS |
| UDS cloud coverage | scattered to broken (low to mid) | UDS |
| UDS cloud shadows | ON | UDS |
| Volumetric fog | ON: sun scattering 1-2, distribution 0.6-0.8, view distance 3,000-6,000 cm; lamps without volumetric shadows | UDS (Volumetric Fog) / lights |
| Volumetric fog quality | GridPixelSize 16, GridSizeZ 64 (the High/Epic scalability defaults [5.8?]) | CVar / scalability |
| Local fog volumes | 1-3 low volumes (yard, alley) | level actors |
| UDS Half Rate Tick | ON | UDS |
| Materials | Substrate slabs as in 2.8; remove the flatten crutches once the lighting is honest | MIs |
| Motion blur project default | leave `r.DefaultFeature.MotionBlur=False`, enable in the PPV | PS / PPV |

### 5.2 Showcase / trailer (Movie Render Graph or MRQ, or a `-game` HighResShot)

| Setting | Value | Where |
|---|---|---|
| Renderer | MRG (5.8, production), AA override None; stills: spatial 8-16; motion: temporal 8-16; warm-up 64-120 / 64-120 | MRG / MRQ |
| Scalability | Cinematic (4) through Game Overrides | MRQ / CVar |
| Resolution / output | native 4K (8K for key art), **no tiling**; EXR 16-bit plus a PNG / ProRes proxy | MRQ |
| Lumen | Ray Lighting Mode = Hit Lighting for Reflections; Final Gather 4; Scene Lighting 2-4; Scene Detail 2-4; Reflections Quality 4; Update Speed 1 | PPV (a showcase PPV or camera post settings, higher priority) |
| Shadows | `r.Shadow.Virtual.ResolutionLodBiasDirectional -1`; SMRT 16 rays [5.8?] | CVar |
| Volumetric fog | GridPixelSize 4, GridSizeZ 256 [5.8?] | CVar |
| UDS | Project Mode = Cinematic / Offline; Cloud Rendering Mode = Full Cinematic Quality; Sun Lens Flare ON for sun shots; Screen Space Light Shafts ON; Cloud Speed 0 + keyframed Cloud Phase for repeatable takes | UDS / Sequencer |
| Exposure | Manual with a keyframed bias per shot (no auto drift during a shot) | UDS or the camera / showcase PPV |
| Film / grading | the gameplay tone curve, plus optional small per-shot grading | PPV / camera |
| Bloom | Standard 0.675, or Convolution for hero sun shots | PPV |
| Film grain | 0.08-0.2 | PPV |
| Chromatic aberration | 0.1-0.25, start offset 0.5-0.7 | PPV |
| Vignette | 0.4-0.5 | PPV |
| DOF | CineCamera 35-50 mm, f/2.8-5.6, manual focus; Accumulation DOF in MRG for hero shots | CineCamera / MRG |
| Motion blur | Amount 0.5 (180 deg) with temporal samples | PPV / MRQ |
| MRQ CVars | `r.MotionBlurQuality 4`, `r.MotionBlurSeparable 1`, `r.DepthOfFieldQuality 4`, `r.BloomQuality 5`, `r.Tonemapper.Quality 5` | MRQ CVar setting |
| Path tracer (optional hero stills) | UDS Adjust for Path Tracer ON; PT fog through a post-process approximation; check the clouds | PPV / UDS |
| After rendering | UDS back to Game / Real-time and cloud mode back to Fidelity + Performance | UDS |

---

## 6. Experimental or version-uncertain items for 5.8

- **Lumen Lite** (Medium GI): Beta. There is a 5.8 forum report of black blocks under moving objects. Use it only as a
  low preset, and test it with the character.
- **FSSS fog scattering**: Experimental in 5.8.
- **Substrate NPR/Toon**: Experimental (not needed). Substrate itself is production.
- **MegaLights**: production in 5.8, but directional lights stay opt-in and are not recommended for the sun.
- **CVar names or defaults not confirmed for 5.8:**
  - `r.Lumen.HardwareRayTracing.LightingMode`
  - `r.MegaLights.EnableForProject`
  - the `r.VolumetricFog.GridPixelSize` / `GridSizeZ` scalability defaults
  - the SMRT ray counts above 8
  - `r.HighResScreenshotDelay`
  - the bloom default intensity
  - `r.Lumen.HeightFog` (the 5.8 default is 1 per Tom Looman; DojoLab forces 0)
- **Legacy `r.RayTracing.GlobalIllumination*` / `r.RayTracing.Reflections*`** on Epic's MRQ page: not the Lumen path.
  Do not use them.
- **UDS 9.7 was saved with 5.5.** Check Fab for a 5.8 build or a newer UDS, whose update notes may change exposure or
  cloud defaults (the online update-history page did not return content to the fetch).
- **The DLSS plugin** is third-party; a 5.8 build is listed by NVIDIA.

---

## 7. What must be measured in the level

1. **GPU frame time** in `-game` at 1440p (and 1080p / 4K) with `stat unit`, `stat gpu` and `ProfileGPU`, or the CSV
   from `run_game_perf.ps1`. Compare:
   - the current setup against UDS with Volumetric, Static and 2D clouds;
   - HW Lumen against software Lumen;
   - Surface Cache against Hit Lighting;
   - GI Epic against High;
   - volumetric fog on and off;
   - screen % 67 / 75 / 100.
   Budget: GPU at or under about 14 ms for headroom at 60 fps.
2. **CPU and game thread**: the UDS Blueprint tick, with Half Rate Tick on and off.
3. **VRAM** on 12 GB with Lumen HW RT, VSM and 4K textures.
4. **SceneCapture2D with UDS**: whether the volumetric clouds, the static or 2D clouds and the sky show, and whether a
   Lumen-quality difference appears against `-game`. Then move the judge captures to `-game` HighResShot or MRG.
5. **Exposure against the reference**: the luma histogram on CAM_Ref2Match. Target about 12.8 % of pixels under luma
   40 (ref 2), the roof R/B about 0.92-0.95 and deep eave shadows. Use Visualize > HDR (Eye Adaptation).
6. **Emissive and lamp recalibration** after the exposure change: ridges, shoji, lamps; multiply each by 2^ΔEV.
7. **Sun elevation and azimuth** from UDS's Sun component against round 5's placement (behind-left of the hall,
   12-14 deg).
8. **Volumetric fog shafts** under the eaves and the gate at gameplay grid settings: banding, noise, cost.
9. **VSM cache stability** once vegetation with WPO arrives.
10. **MRG test render**: 120 warm-up frames, AA None with 16 samples, UDS Cinematic mode. Look for cloud ghosting and
    Lumen noise; compare time per frame.
11. **`r.Lumen.HeightFog` 0 against 1**: what it changes in 5.8.

---

## Sources

Epic (Unreal Engine 5.6-5.8)
- UE 5.8 release notes: <https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes?lang=en-US>
- UE 5.8 announcement: <https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available>
- Lumen Performance Guide: <https://dev.epicgames.com/documentation/unreal-engine/lumen-performance-guide-for-unreal-engine>
- Lumen Technical Details: <https://dev.epicgames.com/documentation/unreal-engine/lumen-technical-details-in-unreal-engine>
- Hardware Ray Tracing: <https://dev.epicgames.com/documentation/en-us/unreal-engine/hardware-ray-tracing-in-unreal-engine>
- MegaLights: <https://dev.epicgames.com/documentation/en-us/unreal-engine/megalights-in-unreal-engine>
- Virtual Shadow Maps: <https://dev.epicgames.com/documentation/unreal-engine/virtual-shadow-maps-in-unreal-engine>
- Directional Lights: <https://dev.epicgames.com/documentation/en-us/unreal-engine/directional-lights-in-unreal-engine>
- Temporal Super Resolution: <https://dev.epicgames.com/documentation/unreal-engine/temporal-super-resolution-in-unreal-engine>
- Auto Exposure: <https://dev.epicgames.com/documentation/unreal-engine/auto-exposure-in-unreal-engine>
- Local Exposure: <https://dev.epicgames.com/documentation/en-us/unreal-engine/local-exposure-in-unreal-engine> (the
  page body did not load for the fetch; the parameter behaviour quoted here comes from the engine tooltips embedded in
  the UDS asset)
- Color Grading and the Filmic Tonemapper: <https://dev.epicgames.com/documentation/unreal-engine/color-grading-and-the-filmic-tonemapper-in-unreal-engine>
- Bloom: <https://dev.epicgames.com/documentation/en-us/unreal-engine/bloom-in-unreal-engine>
- Depth of Field: <https://dev.epicgames.com/documentation/en-us/unreal-engine/depth-of-field-in-unreal-engine>
- Post Process Effects: <https://dev.epicgames.com/documentation/en-us/unreal-engine/post-process-effects-in-unreal-engine>
- PostProcessSettings (Python API, film grain fields): <https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PostProcessSettings?application_version=5.1>
- Volumetric Fog: <https://dev.epicgames.com/documentation/en-us/unreal-engine/volumetric-fog-in-unreal-engine>
- Sky Atmosphere: <https://dev.epicgames.com/documentation/en-us/unreal-engine/sky-atmosphere-component-in-unreal-engine>
- Volumetric Cloud properties: <https://dev.epicgames.com/documentation/unreal-engine/volumetric-cloud-component-properties-in-unreal-engine>
- Scalability Reference: <https://dev.epicgames.com/documentation/en-us/unreal-engine/scalability-reference-for-unreal-engine>
- Taking Screenshots (HighResShot): <https://dev.epicgames.com/documentation/en-us/unreal-engine/taking-screenshots-in-unreal-engine>
- MRQ high-quality frames: <https://dev.epicgames.com/documentation/en-us/unreal-engine/rendering-high-quality-frames-with-movie-render-queue-in-unreal-engine>
- Cinematic rendering image quality: <https://dev.epicgames.com/documentation/unreal-engine/cinematic-rendering-image-quality-settings-in-unreal-engine>
- Path Tracer: <https://dev.epicgames.com/documentation/en-us/unreal-engine/path-tracer-in-unreal-engine>
- Lumen Lite roadmap card: <https://portal.productboard.com/epicgames/1-unreal-engine-public-roadmap/c/2296-lumen-medium-quality-beta->

Ultra Dynamic Sky
- UDS 9.7 documentation: <https://www.ultradynamicsky.com/Documentation/V9/9-7>
- In-content (read as text, read-only): `DemoGame_1/Content/UltraDynamicSky/Blueprints/System/Editor_UI/UDS_Readme_Entries.uasset`
  (sections: Adding UDS, Sky Mode, Project Mode, Volumetric Clouds, Lights, Sky Light Modes, Exposure, Fog, Sequencer,
  Movie Render Queue, Path Tracer, Performance, Common Issues), `Blueprints/Enum/UDS_VolRT_Mode.uasset` (the cloud
  rendering mode tooltips), `Blueprints/Ultra_Dynamic_Sky.uasset` (property tooltips), `UDS_CurrentVersion.uasset`
  (9.7).

Industry and community
- Tom Looman, UE 5.8 performance highlights: <https://tomlooman.com/unreal-engine-5-8-performance-highlights/>
- CG Channel, UE 5.7 (Substrate production-ready): <https://www.cgchannel.com/2025/11/unreal-engine-5-7-five-key-features-for-cg-artists/>
- CG Channel, UE 5.8: <https://www.cgchannel.com/2026/06/see-5-key-features-for-cg-artists-in-unreal-engine-5-8/>
- AMD GPUOpen UE performance guide: <https://gpuopen.com/learn/unreal-engine-performance-guide/>
- NVIDIA DLSS (UE plugin downloads incl. 5.8): <https://developer.nvidia.com/rtx/dlss> and
  <https://developer.nvidia.com/blog/whats-new-for-game-developers-in-nvidia-rtx-dlss-4-5-for-ue5-and-multilingual-ai-characters/>
- MRQ sampling guide (industry): <https://www.hyperrender.run/blog/ue5-mrq-settings-guide-2025>
- Forum, 5.8 Lumen Lite black blocks: <https://forums.unrealengine.com/t/ue5-8-medium-gi-lumen-lite-false-black-blocks-under-moving-objects-black-ring-on-mid-distance/2740008>
- Forum, volumetric clouds in SceneCapture2D: <https://forums.unrealengine.com/t/interesting-issue-with-volumetric-clouds-scenecapture2d/1252223>,
  <https://forums.unrealengine.com/t/scene-capture-component-2d-disable-capturing-volumetric-clouds-without-showflags/488982>
