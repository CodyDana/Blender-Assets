# Dojo dressing track: emblem plaques + weathering / moss decals

Spec: `WorkFiles/world/DOJO_ARENA_SPEC.md`; look: `WorkFiles/world/STYLE_GUIDE.md`; references: `References/Dojo/`
(AI-generated modelling references, `REFERENCE_LOG.md`). Lock: `DojoDressing` (claude, `Assets/Dojo/DojoDressing.blend`).
Owned here: `Scripts/dojo/dressing/`, `Assets/Dojo/DojoDressing.blend`, `Exports/DojoKit/Dressing/` (SM_DKD_*, T_DKD_*),
`WorkFiles/dojo/build/dressing/`.

## 2026-09-29 - ROUND 5 (final look pass, no vegetation): emblem plaques + the decal plan (Blender only)

### Commands (headless, --factory-startup; no MCP, no Unreal in this track)
```
"C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/dojo/dressing/make_decal_textures.py   # 14 s
blender -b --factory-startup --python Scripts/dojo/dressing/build_dressing.py                                    # 45 s
bash WorkFiles/dojo/build/dressing/checks/run_checks.sh                                                           # walk / climb / roof walks
blender -b --factory-startup Assets/Dojo/DojoDressing.blend --python Scripts/dojo/dressing/render_dressing.py -- --tag r3 --samples 96 [--no-decals --only ...]
py -3 Scripts/dojo/dressing/compose_sheets.py r3
```
`build_dressing.py` appends the composed compound read-only from `Assets/Dojo/DojoShowcase.blend` (Kit + Assembly), builds
the plaques, measures every decal placement by ray casts, QAs and exports, and saves `DojoDressing.blend` (the showcase
context + the plaques + the `DecalPreview` collection; the preview meshes are never exported).

### 1. Emblem (the user's own armory emblem; no other crest, no text, no cloth)
- **Textures**: `T_AK_Emblem{,_BC,_N,_ORM}.png` copied BYTE FOR BYTE to `Exports/DojoKit/Dressing/Textures/T_DKD_Emblem_{M,BC,N,ORM}.png`
  (sha256 identical, checked every build; `layout_dressing.json` 'emblem_textures'). Pixels unchanged.
- **Construction**: a round black-lacquered timber board (45 deg front chamfer) with the emblem RAISED on it as real geometry:
  the emblem mask traced by marching squares at 512 px (8 loops: ring outer + inner, 5 petals, the heart), simplified
  (RDP 0.35 px), a 2D filled curve extruded with a small round bevel. UV0 = the emblem texture 0-1 across the board face;
  the relief's walls are pulled onto gilt texels, the edge and back onto black corner texels. One material slot
  `M_DKD_EmblemPlaque` (recipe: M_DJ_Lib_Opaque, BC/ORM/N = T_DKD_Emblem_*, **RoughMult 2.0**, UseWear off).
  - RoughMult 2 (r1 finding): at the armory's roughness (gilt 0.30, lacquer 0.20) the gilt mirrored the dark eave and
    gable surroundings and read BLACK in shade (renders r0 / r1); at 0.60 / 0.40 it reads as weathered gilt on lacquer.
- **Pieces** (Nanite, 3307 tris each, 1 LOD, one UCX hull each, class thin):

  | Piece | Board | Relief (measured) | Placed (grey-box m) | rot_z |
  |---|---|---|---|---|
  | SM_DKD_EmblemPlaque_Hall | 0.90 m, 50 mm | 9.5 mm | (14.545, 29.0, 7.93) west gable | -90 |
  | SM_DKD_EmblemPlaque_Hall | same mesh | | (29.455, 29.0, 7.93) east gable | +90 |
  | SM_DKD_EmblemPlaque_Gate | 0.46 m, 35 mm | 6.2 mm | (22.0, -1.945, 2.975) street face | 0 |

  Pivot = the disc centre on its back plane; the face looks along local -Y.
- **FLAGGED deviation from the brief: the hall has NO front-facing gable.** Its upper roof is a hip-and-gable whose gables
  (tsuma triangles) face WEST and EAST (hall sheet side view; `layout_hall.json` gable_face_x 14.6 / 29.4). The plaque sits
  where a house crest sits on an irimoya: centred on the gable's king post over the collar beam, on BOTH gables (the
  compound is mirror-symmetric for P1 / P2). Measured fit (probe of DojoShowcase.blend): plaster face X 14.600, king post
  face 14.550, collar beam face 14.555 (z 7.842-7.992), a block on the tie beam at 14.510 (z 7.233-7.453, under the plaque:
  r0 at z 7.90 clipped it by 3 mm, so +7.93); apex +8.729; clearance from the rakes 0.20 m. Seen from the side yards and
  obliquely from the courtyard (renders CU_HallGableW, EastYard); the establishing view from the gate does not show them.
  If the user wants the emblem on the FRONT, the only front candidate is the clerestory frieze centre (X 22, +5.1..5.6),
  which would cover lattice: the user's call.
- **Gate: the street face.** Measured: the front eave beams (upper y -1.890, z 3.20-3.36; lower y -1.840, z 3.06-3.20) carry
  11 x 10 cm pegs every 0.4 m reaching y -1.940, one at X 22; above them the gate roof's rafters (X 21.73-21.82 / 22.18-22.27)
  and soffit boards come down to about +3.22 in the plaque's plane. The lintel / tie beams further in are hidden behind the
  eave beam from any street viewpoint (sight lines computed) and sit under the rafters. So the plaque hangs on the centre
  peg: top +3.205, bottom +2.745 (clear height over the apron 2.75 m > R5's 2.5). From the courtyard only its black back shows
  through the opening (CU_GateCourtyard). Candidate tests: scratch renders of 5 positions (street eave beam, street tie beam,
  courtyard lintel, courtyard eave beam, hall gable).
- **Clearance** (`clearance.json`, BVH of each neighbour within 0.6 m): no intersection; min gap 5.0 mm (hall, to the king
  post / RoofUpper_End), 5.1 mm (gate, to the Gate_Frame peg). The export is gated on it.
- **QA**: 0 hard fails; waived `uv_no_overlap` (the relief sits over the board face in UV0 by design; the kits waive it too);
  texel density not checked (a unique crest texture: 2048 px over 0.90 m = 22.8 px/cm, over 0.46 m = 44.5 px/cm). FBX audit
  (re-import): 1 mesh + 1 UCX each, UV0 'UVMap' in 0.004-0.99 + UV1, scale 1, one slot.
  - Bug found and fixed (r1 -> r2): the curve conversion brought its own UV layer, which stayed channel 0 (ours became
    'UVMap.001'); the r0 / r1 exports and renders had the wrong UVs. Removed before our UVs are written.

### 2. Weathering + moss decals (Unreal deferred decals; Blender shows ray-projected previews)
Textures (`make_decal_textures.py`, our own procedural numpy work on the library's helpers, power of two):
`T_DKD_Decal_<Name>_{BC,N,ORM,M}` (BC sRGB, N DirectX, ORM linear, M = the opacity mask, linear grey). Image top = the
decal's up. Report `decal_textures.json`; sheet `renders/decal_textures_sheet.png`.

| Decal | px | nominal m | placements | where (all measured by ray casts, `decals.json` 'source') |
|---|---|---|---|---|
| MossFoot | 2048 x 512 | 4 x 1 | 14 | wall-foot rubble: south wall courtyard face x4 (faces north, shaded), west x3, east x3, street face x4 (reference 1 shows moss there) |
| RainStreak | 1024 x 512 | 2 x 1 | 14 | plaster under the wall-cap drip (courtyard x6, street x4), under the storehouse / residence eave corners x4 |
| Grime | 1024 x 1024 | 1 x 1 | 37 | post bases (posts found as loose parts of the frames: gate 10, hall veranda front 12, corridor 4, pavilion 4, shed 2) + thresholds (gate street / courtyard, hall main doors, storehouse, residence) |
| Lichen | 1024 x 1024 | 1 x 1 | 19 | hall lower roof x4, gate roof x2, wall caps x6, outbuilding roofs x2, pavilion roof x1, the two tall lanterns (cap + base) x4 |
| WaterStain | 1024 x 1024 | 1 x 1 | 10 | under every downpipe shoe (hall 4, outbuildings 4, corridors 2): outlet + outflow measured from each instance's lowest vertices |
| WornPath | 1024 x 1024 | 1.5 x 1.5 | 7 | beside the hall stair x2, along the hall front x2, beside the gate apron x2, the street in front of the gate x1 (lands on whatever the outside track's ground is) |

- **decals.json** (101 placements, 0 skipped): per placement the centre ON the surface, the outward normal, up / right, size,
  box depth, a flip flag, and the Unreal transform: location (x, -y, z) * 100, rotator for local +X = projection (-normal)
  and +Z = up (self-checked by rebuilding the matrix), DecalSize = HALF extents in cm, scale Y -1 for flipped ones. One master
  `M_DKD_Decal_Master` (DeferredDecal, DBuffer translucent colour + normal + roughness) and six instances, recipes in the file.
- **Not measured here (for the Unreal stage):** which of the decal's local Y / Z carries the image's U / V. Check MossFoot_01
  (south wall courtyard face at X 10: the moss must sit at the wall FOOT) in the first capture and flip up / right globally
  if needed. Set bReceivesDecals off on the player character's meshes. Wall-foot boxes stop 2 cm above the ground so the
  gravel does not take stretched texels; faces parallel to a projection axis (post sides, footing tops) do stretch: keep the
  depths as given.
- Iterations (renders r0-r3): rain streaks r1 read as a comb (46 thin lines) -> 30 softer smudges; moss r1 a green wash,
  r2 dots, r3 a continuous band -> patchy cushion clumps at the foot (15-40 cm clumps of 3.5 cm cushions); lichen r1 star
  rosettes / paint chips -> irregular crusts a step darker, opacity 0.8; worn path r1 a dark wet-looking oval -> packed fines
  a touch lighter than the loose gravel with small stones left in it; water-stain tide rings softened. Wall decals r0 took
  the rubble pillows' tilted hit normals and a bench top as "ground": the wall normal is now the ray's axis and the ground ray
  skips props.
- Restraint: at the establishing distance (SHEET_ref2) the decals are barely visible, as in reference 2 (well kept but
  lived in); they read at 3-8 m (SHEET_AB_*).

### Checks (fresh processes on DojoDressing.blend with `layout_dressing_checks.json` = showcase + the 3 plaques) - ALL PASS, identical to verify_r4
- walk_check: 20 / 20 routes clear, 11 / 11 controls blocked (also at r 0.35), 945 Pawn hulls (942 + 3 plaques); route JSON
  identical to verify_r4.
- climb_check (--hover 0.019): routes 1-8 true, same verdicts as verify_r4.
- roof_walk_check, hall_roof_walk, ob_roof_walk: passed (as r4). The 1v1 boundary and the closed rear alley are untouched
  (no dressing piece is in them; decals have no collision).

### Renders (`renders/r3/`, Cycles 96 spp, denoised, the round-4 sunset rig; textured kit meshes)
EstablishingRef2 (+ _nodecals), Overview, GateFromStreet, CU_GatePlaque, CU_HallGableW, CU_HallGablePlaque, EastYard,
CU_WallFooting, CU_WestWall, CU_StreetWall, CU_PathStepBand, CU_Lantern, CU_Downpipe, CU_RoofLichen, CU_Storehouse,
CU_GateCourtyard; sheets SHEET_ref2 / SHEET_ref1 (beside the references), SHEET_emblem_hall / _gate, SHEET_AB_* (decals
off / on).

### For the Unreal stage (not done here: one Unreal commandlet at a time, the integration owns DojoLab)
- Import `Exports/DojoKit/Dressing/SM_DKD_EmblemPlaque_{Hall,Gate}.fbx` (Nanite, fallback full) + the T_DKD_* textures
  (kinds in layout_dressing.json 'textures' / decals.json 'textures': BC sRGB, ORM / M TC_Masks, N TC_Normalmap no flip),
  the plaque MI per `layout_dressing.json` 'materials', the 3 instances in 'instances' (yaw = -rot_z), class thin.
- Build M_DKD_Decal_Master + 6 MIs and place the 101 decal actors from `decals.json`.

### Open / for the user
- The hall's crest is on the side gables, not a front gable (there is none): confirm, or choose the frieze centre.
- The gate crest is on the street face only (sparing); a courtyard-side twin would sit behind the tie beam and the eave
  beam from most courtyard viewpoints.
- The gilt reads bright in low sun on the hall gables; if the judges want it older, lower the MI Tint (not the pixels).
- Decal orientation / DecalSize convention to be confirmed on the first Unreal capture (see above).

### Scripts (new, not committed)
`Scripts/dojo/dressing/{dkd_common.py, make_decal_textures.py, build_dressing.py, render_dressing.py, compose_sheets.py}`,
`WorkFiles/dojo/build/dressing/checks/run_checks.sh`.
