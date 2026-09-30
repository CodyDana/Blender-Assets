# Stone kit track 8: terrace retaining wall (ishigaki)

**Date:** 2026-09-29. **Builder:** `Scripts/dojo/stonekit/build_wall.py`, plus `render_wall.py`, `compose_wall.py` and
`measure_wall.py`. It shares `sk_shared.py` with track 9 and does not edit it. **Lock:** DojoStoneKit.
**Out:** 41 `Exports/DojoKit/StoneKit/SM_DKT_Wall*.fbx`, the `StoneKit_Wall` collection in
`Assets/Dojo/DojoStoneKit.blend`, `wall/DojoStoneKit_wall.blend` (this track only) and `kit_catalog.json`
(`tracks.wall` plus every `SM_DKT_Wall*` piece). No Unreal work was done in this run (DojoLab belongs to the round 8
sky workflow).

## Reference and the style anchor

The reference is `References/Dojo/dojo_landscape_ref.png`. The gridded crops are `renders/wall/refcrops/grid_*.png`.

The scale was measured two ways:
- at the gate steps, 47-50 px/m, from a 0.16 m riser;
- at the terrace, 17-25 px/m, from the compound wall's plaster band.

What the crops show:
- **Body stones:** rounded-rectangle pillow stones, 0.28-0.55 m wide and 0.28-0.47 m tall, many of them upright, in
  rough courses.
- **Top blocks:** squarer, about 0.34 x 0.24-0.28 m, with flat tops.
- **Joints:** dark, 2-4 cm, with moss low down.
- **Compound wall:** stands right on the terrace wall.

Nothing is invented beyond this, except the parts the brief asks for: the sangi-zumi corners, the upswept arris, the
skirts and the stair bastion.

The style anchor is kit 1's footing. The kit **imports** it rather than copying it:
- `kit1_geo.pillow_face` / `rough_block` / `rounded_stone`;
- kit 1's `M_DK_FootingStone` recipe (moss by Wear.A), rebuilt through `sk_shared.granite_moss_variant` with kit 1's own
  numbers;
- `M_DK_JointEarth` (via `build_kit1.build_material`, the module is loaded without its `main()`);
- the library `bake_wear`.

The stair opening's steps are track 9's own `worn_block` in `M_DKT_StepGranite`, imported the same way from
`build_stairs.py`.

## Grid (measured on the built meshes: `wall/measure_wall.json`)

- **Pivot:** Z 0 is the terrace grade, which is the coping's flat top. The pivot sits on the face line at the module
  start. The face looks to local -Y. Plan grid 1 m.
- **Heights:** H 2 / 3 / 4 / 6 m, measured from grade to the nominal foot. Every piece also carries **0.40 m of buried
  stones** below that.
- **Batter:** one profile for every piece, d(s) = 0.10 s + 0.035 s². The face angle runs from 6 deg off vertical at the
  top to 27.5 deg at 6 m. The foot set-back is 0.34 / 0.62 / 0.96 / 1.86 m.
  - Measured: the stone rims stand a median 0.042-0.049 m proud of d(s) at every depth.
  - Largest deviation, stone crowns included: 0.073 m.
- **Courses:** one global table (`COURSE_S`) under the 0.26 m coping.
- **Module ends interlock with teeth:** course k runs 0.18 m past the grid line (even k) or stops 0.18 m short (odd k).
  - Measured on a 4m_H3 + 4m_H4 pair: the seam band is 95.2 % stone faces, against 89.1 / 92.1 % in the module interiors.
  - So no straight joint runs through the courses at a seam.
- **Coping:** the tops measure +0.0004 to +0.0012 m at their highest (flat). The lowest top-band vertices, -0.04, are
  the rounded arrises.
  - The walkable UCX top is exactly Z 0 on every wall piece.
  - The foot plinths top out at +0.14.
- **Corners:**
  - **CornerOut** takes 1 m of each face; the next pivot is (1, 1, 0), yaw +90.
  - **CornerIn** takes **2 m** of each face; the next pivot is (2, -2, 0), yaw -90. The batter pulls the inside corner
    line in by d(s), and a 1 m arm would vanish below about 2.6 m.
  - **Sangi-zumi:** dressed rough_block corner stones, 0.80-0.95 x 0.40-0.50 m, long face alternating between the two
    faces course by course.
  - **Upswept arris:** +0.008 s² outward, fading over 1 m along each face.
- **Stair opening:** built on track 9's grid.
  - Riser 1/6, tread 1/3, 1.8 m clear, which is track 9's W180. Measured: risers 0.1587-0.1716 (median 0.1667, the
    spread is track 9's per-stone wear), treads 0.33-0.34 at 1 cm sampling.
  - Curbs (sode-ishi) stand 0.117 m above the nosing line (0.12 by design).
  - 12 / 18 / 24 risers for H 2 / 3 / 4.
  - `stair_foot` snap: a track-9 Flight's `out` or a Landing's N edge.
  - `rail_L` / `rail_R` snaps: track-9 Rail_Slope pivots.
  - The assembly test uses all three snaps.
- **Kit 1's wall on the terrace:** its outer footing face sits 0.10 m behind the coping arris, which is kit 1's
  SE-corner rule shifted. Its Z 0 equals the terrace Z 0. The apron meets the coping top flush behind y = 0.55.

## Pieces, budgets and collision

- **32 Nanite pieces**, 22.5k-389k triangles each:
  - straight modules 40k (2m_H2) to 207k (4m_H6);
  - corners 30k-131k;
  - ends 33k-139k;
  - stair openings 155k / 263k / 389k.
- **9 LOD0-2 pieces** (coping pieces, small feet): LOD0 2.5k-14.8k, then 1/2 and 1/4, strictly descending.
- **Total LOD0:** 3.15 M triangles over the 41 pieces.
- **No UV1 on Nanite pieces.** This assumes Lumen, which bakes no lightmaps; switch on UE's Generate Lightmap UVs if
  static lighting is ever used. qa_check passes them with `require_uv1` off; the LOD pieces carry kit 1's checked UV1.
- **QA:** `qa_check` finds 0 hard fails on all 41 pieces. `uv0_tile_range` / `uv_no_overlap` are waived, as for kit 1
  (the UVs are in library tile units).
- **UCX:** every piece has one.
  - **Walls:** sloped band hulls follow the batter (1 m bands). The coping band and a top box are flat at Z 0.
  - **Stair:** one ramp hull through the nosings (26.57 deg, walkable up to 44.77). Sloped hulls cover the curbs and
    bastions; boxes cover the landing and coping.
  - **Feet:** a plinth box plus a skirt ramp.

## Renders (Cycles, headless, denoised; `renders/wall/`)

**Kit sheets:** `KIT_SHEET_{straight,corners,ends,stairs,topfoot}.png` and the contact page `KIT_SHEET_all.png`. Each
sheet shows:
- ortho front / side / top and a 3/4 view;
- the reference grey #A0A0A0;
- a 1.8 m silhouette at each row's own measured scale (from `views.json`).

**Sunset assembly:** the layout's sun, 7 deg elevation and 160 deg azimuth. The test run stands as the dojo's **west**
terrace wall, so its azimuth is turned +90 into the scene frame. The run:
- EndL_H3, 4m_H3, StairOpening_H3, 4m_H3, then 2m_H4 (a step down) and CornerOut_H4, turning to 4m_H4;
- feet at the `foot` snaps;
- kit 1's real footing, body and cap pieces standing on the coping, round the corner;
- track 9's LandingL, Flights, Landing, Rail_Slope, EndPosts and Lantern_Timber, continuing from `stair_foot` down a
  stand-in slope.

The views are `asm_overview`, `asm_corner`, `asm_terrace_wall`, `asm_stair_head` and `asm_stair_path`.

**Close-ups:** `close_stone_faces`, `close_sangi_zumi`, `close_step_nosing`, `close_rail_joints`, `close_coping_top`.

**Reference | ours pairs:** `sbs_asm_terrace_wall`, `sbs_asm_stair_head`, `sbs_asm_stair_path`, `sbs_asm_overview`,
`sbs_close_stone_faces`, `sbs_close_step_nosing`.

## Open points (honest)

- **Tone:** under the sunset rig our stones read darker and browner than the reference's daylight grey-beige, because
  kit 1's FootingStone tint is 0.55. That was kept on purpose so the terrace matches the dojo footing. The Unreal look
  pass decides.
- **Joint core:** kit 1's `M_DK_JointEarth` shows small pale pebble specks in the widest joints (`close_stone_faces`).
  They are kit 1's texture; changing them is the kit 1 owner's call.
- **Height changes:** a taller module's end below its shorter neighbour's foot shows the core end cap and the stone
  teeth. Terrain or a foot skirt should cover it. No dedicated step-down piece.
- **FootCornerIn_H6 is tiny** (0.79 x 0.71 m). At 6 m the inside corner line sits 0.14 m from the arm end at the foot.
  Use straight WallFoot pieces overlapping there.
- **H6 geometry:** the outside-corner flare at H6 (0.29 m at the foot) stretches the lowest corner stones visibly on
  the sheets.
- **Stair openings stop at H4.** For taller walls, split the climb.
- **Stand-ins only:** the stand-in terrain, boulders and terrace plane in the assembly are not kit pieces. The user's
  landscape replaces them.
- **Track 9 drift:** `build_stairs.py` was still changing (23:38). The opening's steps use its `worn_block` as it stood
  at build time (about 23:20). Re-run `build_wall.py` after track 9 settles to pick up changes.
- **Not verified in Unreal** (no Unreal in this run): import, Nanite, the UCX responses and the material binding of
  `M_DK_FootingStone` / `M_DKT_StepGranite` to the existing instances.
