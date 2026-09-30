

## 2026-09-29 - ROUND 5 FIX f1: the two round-5 Unreal judges (whole 6.5 / detail 6.5), lighting + colour first, Blender assets + Unreal

User: "start with everything else and leave the vegetation for later" (trees stay grey-box). No DojoLab editor was
open at any step (the runner's guard); one Unreal process at a time, none left running. Headless Blender only (no MCP).
Nothing committed. The armory emblem files were read only (the plaque textures are the dressing track's byte copies).
- **Folders:** `unreal/round5/f1_work/`:
  - `start_backup/` (every showcase, Unreal, outside and dressing script, their layouts, the three .blend files and the
    r5 sky PNG as they were);
  - `it1`..`it8` (iterations); `probe_fog/` (the fog probe);
  - `calib_it1.json` + `fit_sky_calib.py` (the dome response);
  - `sky_preview.py`, `contact.py`, `m.py`, `cores.py` (helpers);
  - `patch_outside.py` (the outside builder patch, for the record);
  - `retired_fbx/` (SM_DKX_Mountains_Near / _Far);
  - `checks/run_checks_f1.sh`;
  - logs.
- `unreal/round5/f1/`: the FINAL 36 stills, `SHOWCASE_SHEET_R5_f1.png` (with CAM_Ref2Match), `measure_f1.txt`,
  `health_f1.txt`, `regions_r5_f1.json`, `json/` (import, materials, level, verify, perf, capture, compose) and
  `json/checks/` (every Blender check).

### Commands
```
py -3 Scripts/dojo/showcase/make_sky_sunset.py --calib WorkFiles/dojo/build/unreal/round5/f1_work/calib_it1.json
blender -b --factory-startup --python Scripts/dojo/outside/build_outside.py          (QA 34 pieces, 0 hard fails, 34 FBX)
blender -b --factory-startup --python Scripts/dojo/dressing/build_dressing.py -- --no-preview   (QA 2, 0 hard fails)
blender -b --factory-startup --python Scripts/dojo/showcase/compose_showcase.py      (242 pieces, 1099 instances, 86 decals)
bash WorkFiles/dojo/build/unreal/round5/f1_work/checks/run_checks_f1.sh
DJ_CAPTURE_DIR=<abs>/unreal/round5/f1 bash Scripts/dojo/unreal/run_showcase_unreal.sh prep import materials level verify perf capture
py -3 WorkFiles/dojo/build/unreal/round5/f1_work/make_sheet_r5_f1.py <abs>/unreal/round5/f1 f1
```

### 1. Sky and sun (both judges' first blocker)
- **Sun:** 12 deg / az 160 (west, side-lit) -> **14 deg / az 125** (north-west, behind the hall's left shoulder seen
  from the gate), 5600 K.
  - it1 tried 10 deg / 108: every 5 m building threw a 30 m shadow, so the whole courtyard sat in flat shade.
  - At 14 / 125: the hall front and the gable fronts are backlit (shade), the ridges and roof edges take rim light, and
    the sun rakes across the west sand field while the hall's shadow runs diagonally over the east field.
- **Sky:** `Scripts/dojo/showcase/make_sky_sunset.py` (new). T_DJS_SunsetSky is a FULL opaque painted sky, 8192 x 2048
  (1:1 with the 1920 captures; the r5 layer was 4096 x 1024, magnified 2.4x), BC7.
  - It replaces the translucent cloud layer over the SkyAtmosphere. The atmosphere stays for the sun's transmittance,
    the aerial perspective and the real-time sky light.
  - Gradient: ref 2's measured colours by elevation and angle to the sun (warm horizon band behind the hall -> dusty
    violet).
  - Clouds: band-limited noise projected on a flat deck (they shrink into banks toward the horizon), octaves faded
    under their texel footprint (no aliasing), lit undersides and sun-facing rims, thin edges glowing near the sun.
  - **Calibrated:** `fit_sky_calib.py` traces capture pixels back to dome texels and fits the tonemapper response, so
    the painting targets output colours. Dome Intensity 90 -> 148.
  - `dj_sc_level.sky_dome` takes `cfg["png"]`.
- **Measured (CAM_EstablishingRef2):** horizon left of the hall (238, 161, 107) s 0.55; judge target (240, 150, 90),
  ref 2 (249, 183, 126). Clouds (197, 144, 119).
- **Fog / haze:** explicit inscattering (1.2, 1.1, 1.45), warm directional lobe (2.0, 1.1, 0.5) exp 6 from 150 m,
  density 0.014, the SkyAtmosphere's height_fog_contribution 0. The fog probe (probe_fog) measured 6x that washing the
  ranges to (224, 195, 174).
- **Sky light:** 7.5 -> 9. Sky factor (4.2, 2.8, 2.1) -> (3.8, 2.8, 2.5).
- **Vignette:** 0.15 -> 0.42.

### 2. Far background (both judges' second blocker)
`Scripts/dojo/outside/build_outside.py` + `ox_common.py`.
- **Root cause, found:** SM_DKX_FarGround and both mountain shells were wound with their normals DOWN. Unreal culled the
  plain from above and every front slope of the rings. The judges' 'flat lavender plane with a hard edge' was the sky
  dome's horizon row seen through the culled plain, and the 'sine shells' were the back slopes' undersides. The
  winding is fixed (normals up: checked in Blender).
- **Four ridge rings SM_DKX_Ridge1..4** (0.45-2.25 km, heights 14-215 m, broader, gentler peaks), each ring's back
  falling to the next ring's foot, so no gap shows the sky.
  - Own flat emissive colours on M_DJ_EmissiveFlat_Master (M_DKX_Ridge1..4), so the backlit sun cannot light them
    unevenly. Their colours go (58, 64, 82) -> (128, 124, 148) before the fog.
  - Measured (probe V2): (93, 79, 81) ring 1 -> (157, 134, 128) ring 4, warm toward the sun.
- **SM_DKX_FarTown (new):** about 1,750 low-poly houses (gable, hip, gable-front, kura, two-storey; 38.4k tris, Nanite,
  token UCX) in rotated districts from the town rectangle to 430 m, so no ground reaches the horizon. Flat colour sets
  M_DKX_FarRoofA/B and M_DKX_FarWallPlaster/Wood. FarGround now ends at 470 m under ring 1 (Specular 0).
- **Local town:**
  - every house has its own frontage (x0.82-1.22) and height (x0.86-1.16) scale;
  - 35 % random types break the cycle, and single-storey and kura are mixed into the north rows (`place()` and
    `link_instances` take a scale);
  - the plots use M_DJS_TownYard (fine grey gravel) and the lanes the road cobble (actor overrides on Ground_W/E/N).
- **Power line:** the lower crossarm's four conductors (E-H) are dropped: 28 conductor spans, was 56.
  - `modern_instances()` now reads the modern kit's original rows from the pre-round-5 showcase backup (the live
    layout already carried the moved rows).
  - `compose_checks` no longer appends a second copy of the route-O climbs on every rebuild (they had grown to 25;
    deduped to 5).
- Retired: SM_DKX_Mountains_Near / _Far (RETIRED_MESHES; FBX in f1_work/retired_fbx).

### 3. Assets and look deltas
- **Hall gable emblem:** board 0.90 -> 0.64 m (`build_dressing.py` PLAQUES), clear of the bargeboard and the tie-beam
  block. Its own aged-gilt instance M_DJS_EmblemPlaque_Aged (Tint (1, 0.82, 0.6), VM 0.62, Rough x1.5) on the user's
  unchanged emblem textures.
- **Gate emblem back:** both plaques' back face is now a timber cap (slot M_DJ_TimberDark). It no longer reads as a black
  disc from the courtyard.
  - `dkd_common.load_showcase` leaves the track's own plaques out of the context (the rebuild had made '.001' nodes).
  - decals.json is the track's original: the rebuild's re-planned decals were discarded
    (`f1_work/decals_rebuild_discarded.json`).
- **Decals:** 15 lichen on the tiled roofs and wall caps are dropped (`round5.DROP_DECALS`: the white scribbles, and
  the gate-roof one's box printed black splatter on the soffit). 86 decals remain.
  - A new EdgeFeather in M_DKD_Decal_Master (a UV border fade: moss 0.16, grime / rain 0.1) ends the hard diagonal
    cuts.
  - Moss is subtler: Sat 0.5, Opacity 0.75. The lantern lichen is darkened.
- **Shoji / window glow:** cores (227, 182, 125) s 0.45 (hall) and (229, 194, 118) s 0.48 (residence), clip 0 %.
  Round 5 had s 0.77-0.81 and residence clip 12.9 %.
- **Roof tiles:** neutral warm charcoal (Tint (1, 0.98, 0.95), flatten target (0.058, 0.056, 0.054), not the blue
  texture mean). Hall upper roof (61, 57, 59) R/B 1.03: r5 0.72, ref 2 0.88.
- **Gate timber:** its own grey-brown instances M_DJS_GateTimber / End on the gate frame, roof and leaves; gate lamps
  3300 K x0.7.
- **Street lamps:** x5, 2900 K (pools on the road). The road cobble: tile 4 -> 2.4 m, macro tint / dirt 0.3 / 0.28,
  Sat 0.7, warmer.
- **Sand:** (187, 154, 131) s 0.30 lit, (179, 151, 136) mid. Ref 2: (185, 146, 120) / (179, 149, 131).
- **Training props:** darker walnut (M_DJS_TimberMid VM 3.4 -> 1.9).
- **Gravel:** tile 2 m, Sat 0.5. **Plaster:** normal x1.7.
- **Fill lights:** five shadowless 6000 K fill point lights (Light_Fill_*: pavilion ceiling, both alley fences, both
  corridors). They are layout lights, so verify counts them.
  - Alley fence black tiles 43 -> 0, near-black 21.8 -> 6.1 %; corridor 55 -> 2 tiles, 16.6 -> 8.6 %.
  - Pavilion ceiling (15, 3, 1) -> (34, 17, 9).
- **New camera CAM_Ref2Match** (22, -0.9, 2.1): ref 2's framing from the gate threshold (the paving across the bottom,
  the gate's leaves and posts at both edges).

### Checks (final compose; GASP capsule r 0.30, 1.72 m, step 0.45) - ALL PASS
- **QA:** outside 34 and dressing 2 pieces, 0 hard fails, a UCX on every SM_, all through Scripts/pipeline.
- **walk:** 41 routes + CONTROLs, PASS at r 0.30 and 0.35. The 1v1 rear alley is still closed (the alley-fence CONTROLs
  are blocked).
- **climb:** every route, numbers unchanged:

  | Obstacle | Height (cm) |
  |---|---|
  | Wall | 198.1 / 193.7 |
  | Pier | 123.1 (+0.233 step) |
  | Cistern | 122.3 |
  | Eave pad | 172.9 |
  | AC | 197.4 + 0.40 |
  | Shed crate -> band | 123.1 -> 122.9 |
  | Pavilion crate -> pad | 122.3 -> 197.9 |
  | Vending | 173.1 + 0.25 |
  | Plinth | 98.1 |
  | Veranda | 48.1 |
  | Hurdle | 111.8 |
  | Outside wall climbs (BR) | 197.8-198.7 |

  Route 3: -0.109 / -0.513.
- **Roof walks:** gate, hall, outbuildings, corridors, shed, pavilion: all PASS.
- **Clearance / ground holes:** identical to r5 (46 contacts; the same 136 closed-interior clusters).
- **Unreal verify (fresh process): 8 / 8 gates.** 240 meshes, 134 textures, 1099 / 1099 actors, 86 decals, 24 markers.
- **Perf:** 8.47 M placed triangles (+0.02 M), 2.0 M unique.

### Open (for the judges / user)
- Not done:
  - wall footing stones are still the pillow rubble (a kit-1 geometry rebuild);
  - the wooden dummy's square trunk;
  - the shed roof corrugation silhouette;
  - curb damp and the full-frontage flagstone apron (outside geometry);
  - the player's bReceivesDecals (user's call, as r5).
- The hall facade in shade is darker than ref 2 (veranda band (47, 28, 19) against (72, 49, 32)); the drum top and
  the gate soffit stay deep red-brown in shade.
- The fill lights are an authored bounce stand-in (the judge's ask); the sun's GI x4 stays.
- The far town is flat-colour low-poly (reads at 100 m+); the vegetation pass should add trees among it.
- The hall plaque is still on the side gables (user's call); the sun at az 125 is a look choice (ref 2), not a real
  bearing.
- Lock DojoKit is still held.

### Scripts changed (not committed)
- **Showcase:** `Scripts/dojo/showcase/look_r3.py` (ROUND 5 FIX f1 section), `make_sky_sunset.py` (new),
  `apply_look_r3.py` (fill lights, camera idempotence), `round5.py` (DROP_DECALS).
- **Unreal:** `Scripts/dojo/unreal/dj_sc_level.py` (sky png), `dj_sc_materials.py` (decal EdgeFeather).
- **Outside:** `Scripts/dojo/outside/build_outside.py`, `ox_common.py`.
- **Dressing:** `Scripts/dojo/dressing/build_dressing.py`, `dkd_common.py`.
- **Work files:** `WorkFiles/dojo/build/outside/layout_outside_checks.json` (route-O dedupe).
