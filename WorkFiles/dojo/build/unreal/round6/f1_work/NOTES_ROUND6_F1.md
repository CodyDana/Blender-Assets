

## 2026-09-30 - ROUND 6 FIX f1: the round-6 judge (7 / 10) and verifier (gravel), Blender outside + Unreal

User: "yes start first round. keep emblem for now". The emblem plaques are untouched, and there is no vegetation
(trees stay grey-box).

House rules kept:
- headless Blender only (no MCP);
- one Unreal process at a time, none left running;
- no DojoLab editor open at any step;
- DemoGame_1*, the GASP sample and ArmoryLab untouched;
- locks DojoKit and DojoOutside (claude) refreshed and kept;
- nothing committed.

Folders:
- **Work:** `unreal/round6/f1_work/`:
  - `start_backup/`: scripts, layouts, both blends, L_Dojo.umap;
  - `it1`-`it3`, `probe_a`/`probe_b`, `wb/`.
- **Final:** `unreal/round6/f1/`: 42 stills, SHOWCASE_SHEET_R6_f1.png, measure_f1.json, `json/`.

### The alley first
The round-6 seal still holds on the final level (fresh processes):
- **UE:**
  - replay: 32 / 32 CONTROL blocked, 10 / 10 POSITIVE clear, BR 30 / 30 open;
  - flood: 0 alley cells;
  - pocket probes: 0 clear.
- **Blender:** the flood, walk, climb, roof walks, clearance and ground holes are **identical** to round 6
  (`f1/json/checks/`, `round6/build/checks_f1/`).

### Fixes
All in look_r3.py "ROUND 6 FIX f1". Every value was measured with `f1_work/measure_f1.py`.

**Blocker 1: empty sky behind the hall in CAM_Ref2Match**
- Change:
  - CAM_Ref2Match raised to 7.3 m over the gate ridge, hfov 84;
  - CAM_EstablishingRef2 raised to 6.8 m inside the gate, hfov 80;
  - the ridges are 40 % lower (outside notes).
- Why the cameras moved: the Workbench studies show the town is hidden from any eye at 3.1 m or lower.
- Result:

  | | r6 | f1 | Ref 2 |
  |---|---|---|---|
  | Hall share of frame width | 60 % | about 56 % | about 50 % |
  | Behind the hall | sky | town roofs + ridges between the hips and the gables | |

  Both training yards are now in frame.

**Blocker 2: pale town ground**
- Change: M_DJS_TownYard now uses the cobble maps (tile 3.3 m, macro dirt 0.45) at VM 0.74; RoadCobble VM 0.7.
- Result:

  | Region | r6 | f1 | Ref 1 street |
  |---|---|---|---|
  | FarBackground sunlit lot E | (130, 111, 106) L 0.46 | (100, 87, 90) L 0.37 | |
  | FarBackground lot W | (134, 124, 131) L 0.51 | (76, 74, 87) L 0.32 | (77, 75, 87) |
  | Overview lot | | (65, 56, 60) | |
  | Overview street | | (69, 61, 72) | |

**Delta 1: blue slate tiles**
- Change:
  - flatten target with R = G: (0.046, 0.045, 0.059);
  - tint (0.95, 0.94, 1.0), VM 1.4, AO 0.2.
- Result:

  | Where | r6 | f1 | Ref 1 |
  |---|---|---|---|
  | Overview hall | hue 226, HLS s 0.20 | hue 238, s 0.19 | hue 245, s 0.09, L 0.24 |
  | Ref2Match | | hue 240-243, s 0.15-0.16, L 0.28-0.33 | |

- The gate kept (sunlit tile R/B <= 1.2): r6 1.10-1.19; now gate 1.12-1.15, pavilion 1.08, E wall cap 1.19.

**Delta 2: ridges, glow step and an evenly lit town**
- Ridge change:
  - the ring emissive ladder is compressed, with ring 1 lifted most;
  - fog sun lobe exponent 6 -> 3, luminance (1.5, 0.9, 0.45).
- Ridge result: lower, softer layers instead of 4 hard ones (CU_R6_RidgesNorth, CU_R5_FarBackground). Ref 2 shows
  hazy low hills.
- Town: the far town is in distance bands (outside notes). Far rows L 0.25 -> 0.23.

**Delta 3: sand**
- Rake lines:
  - UV Scale 2 halves the spacing;
  - the normal is about 65 % at the feet, falling to 35 % from 25 m (NormalFade -30 / 25 m);
  - Sat 0.9;
  - result: fine, soft lines instead of coarse corrugations (CU_SandEye).
- Ref2Match chroma (camera + material):

  | | r6 | f1 | Ref 2 |
  |---|---|---|---|
  | Ref2Match sand | s 0.43, L 0.67 | HLS s 0.27-0.28, L 0.63-0.64 | s 0.32, L 0.61 |

  The Overview sand stays (211, 175, 150), the same as r6 and ref 1.

**Verifier + delta 4: gravel**
- Change:
  - Sat 0.9, tint (1.12, 0.95, 0.76);
  - VM 0.74 / 0.94;
  - tile 2.8 m (bigger stones).
- Result:

  | Region | r6 | f1 | References |
  |---|---|---|---|
  | Shaded Overview | hue 16.6-24 | (145-148, 122-125, 109-113), hue 20-22, R/B 1.29-1.33 | hue 13-18; ref 1 hall front (148, 120, 109) R/B 1.36 |
  | CU_Training | (176, 144, 122) | (170, 139, 121), hue 22 | ref 2 (150, 119, 107) |

**Delta 5: soft shadows**
- Change: sun disc 0.53 -> 0.3 deg; contact shadows 0.04.
- Result: slightly crisper. The sky light stays at 9.

### The gravel band
The verifier's 25-40 deg band contradicts both references (13-18 deg). Option A, the verifier's own recommendation, is
applied: the gravel is judged against the references, with the band **13-30 deg, R/B >= 1.2, HSV s >= 0.15**.
- 9 / 11 boxes pass it.
- The two misses are eye-level foreground boxes seen at a grazing angle:
  - CAM_PlayerEyeSand W: hue 12.5, R/B 1.20;
  - CAM_EastYard front: hue 15.7, R/B 1.17.
- Against the old 25-40 band, only the sunlit W yard passes (as in r6).
- The final call on the band is the orchestrator's or the user's.

### Tried and rejected
From probe_a / probe_b (one offscreen editor each):

| Variant | Result | Why rejected |
|---|---|---|
| Warm sky-light tint (255, 238, 222) / (255, 228, 208) | shaded tiles neutral (R/B 0.68 -> 0.89 / 1.00) | the backlit scene is sky-lit almost everywhere, so every "sunlit" tile box rose over 1.2 (1.35-1.57); the gravel and sand went orange |
| Lumen colour boost 2.0 | | added a near-black corridor cell; the alley bounce stayed red |
| Sky light 8 / 7 | | E wall cap R/B 1.25 / 1.29; CU_Taiko crease cell 16 / 18 % near-black |

### Checks on the final level (fresh processes)
- **Unreal verify: 8 / 8 gates** (7_gasp_trace; 8_decals 86 / 86):
  - 251 meshes, 137 textures;
  - 1,110 actors, bounds max error 0.024 cm;
  - 24 markers;
  - import, materials (92 instances) and level: 0 errors.
- **Perf:** 219 unique meshes, 2.0 M unique tris, about 395 MB of textures at full mips (r6: 2.0 M / 395 MB).
- **Captures:** 42 / 42.
  - Near-black 4 x 4 cells: the same 2 stills as r6:
    - CU_Lantern 13.2 %: the void under the veranda deck;
    - CU_Taiko 13.0 % (r6: 11.1 %): the shaded wall-cap tile creases, after the darker tile.
  - Drum hotspot: 0 px.
  - The capture-health scan (`f1/json/capture_health.json`): 0 black, blown or grey tiles.
- **Blender:** walk 47 routes PASS, climb PASS. Every roof walk, clearance and ground holes are identical to r6. The
  numbers are kept:

  | Obstacle | Height (cm) |
  |---|---|
  | Wall | 198.1 / 193.7 |
  | Pier | 123.1 |
  | Cistern | 122.3 |
  | Eave pad | 172.9 |
  | AC | 197.4 |
  | Shed | 123.1 -> 122.9 |
  | Pavilion | 122.3 -> 197.9 |
  | Vending | 173.1 |
  | Plinth | 98.1 |
  | Veranda | 48.1 |
  | Hurdle | 111.8 |

### Open
- **Shaded tiles still read cool slate:** R/B 0.68-0.74, HLS s 0.15-0.19, against ref 1 / 2 at 0.84-0.94 and
  s 0.06-0.09. Under this sky light, the sunlit R/B <= 1.2 gate and the reference's neutral shade cannot both hold (see
  the rejected tint). The user or the judges should choose which wins.
- **The rear-alley strip** reads a saturated red-brown in deep shade (96, 56, 44). The cause is the warm bounce off the
  sunlit hall rear and the Lumen colour boost 3.0. It is not the gravel's albedo: the strip uses the same material as
  the yard.
- **CAM_Ref2Match** can no longer show the gate posts or sill, because the camera sits over the gate roof. From this
  height, the corridor lattice stays hidden behind the hall's lower roof.
- Still open:
  - the pavilion ceiling is still a saturated red-brown (94, 48, 27);
  - vegetation is pending;
  - bReceivesDecals is the user's call.

### Scripts changed (not committed)
- `Scripts/dojo/showcase/look_r3.py` (the ROUND 6 FIX f1 section).
- `Scripts/dojo/outside/build_outside.py`.
- `Scripts/dojo/outside/ox_common.py`.

Tools (in `f1_work/` only):
- `measure_f1.py`, `ref2match_boxes.json`;
- `wb_cams.py`, `gridov.py`, `pairs.py`;
- `make_sheet_r6_f1.py`, `v6_capture_health_f1.py`;
- `checks/run_checks_f1.sh`, `checks/run_outside_checks_f1.sh`;
- `checks/ue/run_f1_ue.sh`, plus the r6 UE check copies (they now write to f1_work).
