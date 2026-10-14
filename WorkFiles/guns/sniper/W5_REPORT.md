# SR-01 W5: Unreal 5.8 verification (2026-10-14)

**Result: 37 of 37 gates pass** on the re-exported bytes in fresh UE 5.8.3 processes
(`UnrealCheck/verification_summary.json`, status `pass`, `engine_verified: true`). Run folder:
`/Game/GunCheck/SR01_1014b` in `WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject` (main checkout). Nothing
else in that project was touched. Every Unreal process went through `sr_guard.ps1` (one Unreal on the machine; it
waited behind other chats' processes and never stopped one).

## What happened
1. **First run (before the restart, on the W4b bytes): 3 failures.** U6 (catch touches the magazine on reload frame
   2), U8 (1 px of stored-UV1 overlap at 128 px), C2 (9,498 of 320,744 samples "outside" the hulls).
2. **Source fixes (previous session, checkpoint 55100d54):** `sr_lodlib.half_uv1` (UV1 snapped to the float16 grid
   after each static join: twin, magazine, scope); `sr_lodlib.fix_uv_overlaps` shrinks to a speck instead of a point
   (this removed the "nearly zero bi-normals" warnings).
3. **This session:** reran the whole re-export chain `run_rig_mag.sh --from game`. Every step passed: game, view
   (game_lod_sizes), rig, rig_verify (rig_export), mag, scope, scope_verify (scope_export), fit (M1-M10 on the shipped
   bytes, mag.json), look, gates. qa_check passed before every export. Then I recorded the start sha256 (43 files) and
   ran passes A, A3, A2, B, C, E in fresh processes, then D (Blender) and F.
4. **C2** turned out to be the analysis, not the asset: Unreal stores the shipped hull points (hull 02 identical; hull
   05 keeps 22 of 23 points, worst 0.007 mm). The plane builder made a flipped sliver plane on hull 02's near-coplanar
   points. Fixed in `srD_analyse.planes()` (supporting planes only): **0 outside**.
5. **U6** was a measurement error too: the depth test used the nearest-face normal sign, which calls points past the
   notch's edges "inside". It now uses gunlib's ray-parity `depth_inside`, the same method as Blender's F5:
   **0.088 mm, within F5's 0.124 mm**. Only the catch nose touches, on frame 2 of both reload clips, and Blender's M8
   reports the same frame.
6. **Renders:** the deployed bipod now shows deployed (fresh actor per pose). The scope-view board was changed from
   the chassis atlas, which read as noise, to the engine's plain material. The 3/4 hero camera was reframed. These
   are harness-only changes and were rerun in fresh pass-C processes on the same bytes.

## Gates (numbers)
- Bytes: 43 files, identical before and after every pass (A, A2, A3, B, C); equal to the rig_export / mag M7 /
  scope_export records.
- U1 skeleton: 14 bones, head error 5.8e-6 cm. U2 bolt -8.8 cm straight back, -60 deg roll about X. U2b one ABP on
  `SK_AR01_Skeleton` drives SK_SR01 (compatible skeleton) and SK_AR01 within 0.01 cm / 0.01 deg.
- U3 / sockets: SK 20, SM 20, Mag 5, Scope 5, worst 0.0 cm / 3.3e-6 deg.
- U4 FP/VSM: TP ground shadow 60,158 px, FP 3 px. **Scope pair:** Mount = Rail_Top + 20.02 mm (error 1e-14 cm),
  Sight 57.6 mm above the bore, muzzle axis . sight axis = 1.0, bore 5.76 cm under the cross at 10 m.
- Bipod poses read back: legs 90.0 deg, splay 12.0 deg, lean out, extension 3.8 cm, rotation 2e-5 deg vs the build.
- U5: LODs 4 / 4 / 4 / 3. Triangles equal in Blender, the FBX and Unreal on every LOD. Screen sizes = sidecars. Sphere
  radii = the build's (SK 60.94 cm). Bounds hold every vertex at every frame of every clip (0 outside).
- U6 / M9: SnapToTarget error 1.6e-14 cm. Seated pairs 0 at LOD0-1. Straight path 67.8 mm, 0 released-catch
  intersections. Reload clips: catch only, 0.088 mm.
- U7: PHYS_SR01 7 boxes + capsule + no-collision envelope, 5.9 kg. All 5 dropped actors rest, no tunnelling. Component
  bounds hold every vertex at every sample.
- U8: lightmap index 1, generate off, 2 UV channels. Stored UV1 0 px overlap at 64 / 128 on every LOD (1024 px,
  reported only: 4 / 19 / 1 / 0).
- Textures: 21, flags persisted, full mips. U9 clips: runtime vs raw 0.0 mm. U10: 0 asset warning lines in every log.
  U12: Metal / Chassis BC / N at the top mip at the hip and at ADS.
- C2: 0 of 320,744 (SM_SR01), 0 of 300,443 (Mag), 0 of 305,003 (Scope). Hulls 10 + 1 + 3, 32 vertices or fewer.

## Not covered
- **U11 hand fit: not run.** There is no player MetaHuman in the verification project. The summary lists it as a pass
  with value `null`; treat it as not run. H1 passed in Blender.
- U4 "owner sees no TP component" needs the weapon Blueprint on a possessed pawn (game side), as on the AR-01.
- U2b: the ABP's nodes for sniper-only bones (cheek_riser, bipod) warn "bone not found" when compiled on the AR-01
  skeleton. This is expected and has no runtime effect.

## Renders to look at (`UnrealCheck/renders/`)
`look_hero34.png`, `look_right_side.png`, `look_left_side.png`, `look_deployed_hero34.png`,
`look_deployed_right.png`, `look_deployed_front.png`, `look_scope_view_reticle.png` (generic duplex + mil dots drawn
afterwards; the black square under the cross is the bore's 10 m point), `look_bolt_open_port.png`,
`look_receiver_right_close.png`, `look_lod0..3_right.png`, `e_u12_hip.png`, `e_u12_ads.png`. The look renders are
dark (simple offscreen lighting); they show form, pose and framing, not final lighting.

## Files changed in this run (not committed)
- Re-exported (chain): `Exports/Guns/SR01/*.fbx`, `Assets/Guns/SR01.blend`, `Assets/Guns/Att_Scope_LongRange.blend`,
  `WorkFiles/guns/sniper/gates/{game,game_lod_sizes,rig_export,mag,scope_export}.json` + contact sheets.
- Harness: `UnrealCheck/srD_analyse.py` (U6 depth method), `UnrealCheck/srC_render.py` (scope board material, hero
  framing), all pass JSON / logs / renders, `SHA256_at_start.json`, `SHA256_at_end.json`, `content_path.txt`
  (`/Game/GunCheck/SR01_1014b`), `verification_summary.json`, `w5_findings.json`.
- `Exports/Guns/SR01/README.md`: status + "Measured in Unreal 5.8.3". It was written after the last Unreal pass, so it
  is the only file in `Exports/Guns/SR01/` whose hash differs from `SHA256_at_end.json`.
- Scratch (not in git): `scratch/w5/` (logs `rig_mag_chain3.log`, `srD2-5.log`, the C2 diagnosis, contact sheets).
