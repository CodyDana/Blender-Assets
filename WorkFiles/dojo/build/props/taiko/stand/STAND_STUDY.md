# Taiko stand study: how a real stand cradles a nagado-daiko, and what ours should change

Intended location: `WorkFiles/dojo/build/props/taiko/stand/STAND_STUDY.md`. The worktree guard blocked writing to the
main checkout, so this copy is in the session scratchpad.

User question (2026-10-02): "review what an actual Taiko Stand should look like... for ours, shouldn't there be a
circular groove where the taiko sits on the wood?"

**Short answer.** Yes. A real horizontal stand carries the drum on two cross boards (saddles). Each saddle has a
circular-arc cut that matches the barrel, usually lined with felt. Ours already has two arc-cut saddle beams, but they
fail in three ways:

- The drum never touches them. The gap is 3 to 18 mm, because the arc is a single-radius cut on a barrel that narrows.
- The saddles can't be seen once the drum is on. The posts hide them from the side and the drum head hides them from
  the end.
- Instead, the drum reads as resting on four flat post tops, which stop 4 mm under it.

The change list below makes the seat real (felt-lined, barrel-matched, 0-2 mm) and visible (horns standing proud of the
posts). It keeps the reference sheet's frame.

Research only: no Blender was run, and no asset file was edited. All web sources were read on 2026-10-02.

---

## 1. How real stands carry a nagado-daiko lying on its side

### 1.1 Stand families (horizontal axis, heads facing sideways)

| Family | How the drum is held | Examples read |
|---|---|---|
| **Saddle stand** (yagura-dai, four-pillar, butoku dojo, odaiko box, yatai) | Two cross boards or beams run **perpendicular to the drum axis**, under the lacquered body near each end. Each has a **concave circular-arc cut** that matches the body there, with raised "horns" either side. | Asano 武徳道場型台 (dojo), Asano 四本柱台, Asano 大太鼓用四本柱台; Miyamoto やぐら台 (dojo), Miyamoto 四本柱台; MOKU odaiko box stand and yatai stand |
| **Miya-dai** (shrine stand) | Two upright end frames. Each frame's top is a **carved "wing" cradle** cut to the body curve. | Miyamoto 宮台 本欅製 (photo); taikos.com (search snippet): "two main vertical supports and decoratively carved 'wings' which cradle the taiko" |
| **X-stand** | The drum lies in the crotch of two crossed leg pairs, so it touches along 2 lines per end. | MOKU Odaiko X-Stand |
| Beta-dai / hira-dai / naname | The drum stands upright or slanted. Not relevant to ours. | Taiko Center square stand, Tengu |

The dojo stand is the saddle family. Asano says its 武徳道場型台 is "mainly used in judo and kendo dojo", and
Miyamoto says the same of its やぐら台 (Butoku dojo). That is the family for our dojo kit, and our build is already
that family.

### 1.2 Where the drum touches (from the photos)

- **Two saddles per drum**, one near each end, **under the lacquered body just inboard of the hide collar**. A saddle
  never sits under the tacks, the collar hide or the head. The ring handles are high on the sides and touch nothing.
  - Saddle spacing is about 0.6-0.7 of the drum length (estimated from the Asano, Miyamoto and MOKU photos).
- **The cut is a circular arc matching the body radius at that station**, plus the padding. The arc covers about
  80-120 deg of the circumference.
  - The horns rise about 0.15-0.35 x the drum diameter above the lowest contact. MOKU's yatai and box-stand boards are
    at the deep end; the Miyamoto yagura notch is shallower. These are estimates from the photos.
- **Padding is standard at every contact:**
  - Tengu Taiko: every stand is "pine with felt contact points".
  - taikos.com (search snippet): "felt at the points of contact with the drum".
  - The MOKU photos show the saddle arc lined with a grey felt strip about 3-6 mm thick, flush with the board faces,
    running horn to horn.
  - Asano's ceremonial dojo and odaiko stands have an **orange-red padded cushion cord** along the saddle tops, tied
    off with white cords at the posts (visible in the 武徳道場型台 and 大太鼓用四本柱台 photos).
- **The drum sits by gravity in the two arcs.** No straps or retaining blocks hold it; the horns stop it rolling.

### 1.3 Timber, joinery, iron

- **Timber.** Keyaki (zelkova, 欅) is the premium choice (Miyamoto 本欅製). The cheaper option is 木目材 ("grain
  wood"). Taiko Center uses beech and Tengu uses pine.
  - Finishes are black, tonoko or mahogany (Asano options).
- **Saddle size (photo estimates).** A saddle board is roughly 4-6 cm thick along the axis on small drums (MOKU), and
  a heavier beam of about 8-12 cm on dojo yagura stands.
- **Joinery.** Through-tenons with wedges (kusabi) at the stretchers: the MOKU yatai shows wedged through-tenons proud
  of the boards, and the Asano and Miyamoto yagura stands show through-tenon ends.
  - The saddle beams sit on top of the posts or are housed into them. The saddle is always the **topmost** member
    under the drum, so its horns show.
  - A DIY odaiko (Make:) used shaped 2x12 cradle boards, 4x4 legs, 2x6 braces and 1/2 in carriage bolts.
- **Iron.** None at the saddle on any stand read. Modern stage stands have casters (Asano options). Our iron strap
  plates come from the reference sheet's joint close-up and stay.

### 1.4 Heights and proportions

| Stand | Drum head | Drum centre above floor |
|---|---|---|
| Asano 武徳道場型台 (dojo) | 2 shaku (60 cm) | 140 cm |
| Asano 四本柱台 | 1.6 and 2 shaku | 170 cm |
| Asano 大太鼓用四本柱台 (odaiko) | 3 shaku (90 cm) | 170 cm |
| **Ours** | 1.01 m face (about 3.3 shaku), 1.20 m belly | **1.25 m above the stand base** (set by the sheet, on the +1.0 m plinth) |

- Nagado body length is 1.25-1.3 x the head diameter (Taiko Center). Ours is 1.554 m, which is 1.29 x the belly.
- Ours is a low stand by Japanese standards. The height comes from the sheet and the pavilion eave, so it does not
  change.

---

## 2. What our stand does now where the drum sits

Source: `Scripts/dojo/props/taiko/build_taiko.py`: `cradle_profile()` (l. 634), `stand()` (l. 691), the constants at
l. 72-79, and `measure.json`.

- **Two cradle crossbeams** run along Y (perpendicular to the drum axis):
  - at x = +-0.46..0.58 (12 cm along the axis, centres +-0.52, so the spacing is 1.04 m = 0.67 L);
  - bottom at z 0.52;
  - the ends pass through the posts, with tapered kusabi wedge blocks outside them (y +-0.566..0.69).
  - **Position is right:** the beams are under the lacquered body, and the outer face (0.58) is 18 mm inboard of the
    collar's torn edge (x 0.5976-0.6323).
- **The saddle is a concave polyline arc, so a groove exists:**
  - 10 chords, single radius Rs = body_r(0.46) + 3 mm = 0.5805 m;
  - half-angle 43.6 deg (y +-0.40), so 87 deg of arc;
  - arc bottom z 0.6695; flat "horn" shoulders at z 0.829 out to y +-0.56.
- **The drum touches nothing.**
  - The cut is one radius across the beam's width, but the barrel narrows: body_r is 0.5775 at x 0.46 and 0.5643 at
    x 0.58.
  - The gap is 3 mm at the inner edge and 16-18 mm at the outer edge (`measure.json` `saddle_gap_min_max_m`
    [0.003, 0.0179]).
  - The 10-chord polyline adds up to 2.6 mm of sagitta.
- **No padding.** The bare timber faces the lacquer.
- **The groove is hidden in every view with the drum on:**
  - **Side view (along Y):** the posts (x 0.47..0.65, y +-0.39..0.57) stand in front of the beam (x 0.46..0.58).
    Only a 10 mm sliver of beam shows inboard of the post.
  - **End view (along X):** the head (lip r 0.547) covers the arc. The horns sit where the posts are, and stand only
    **8 mm** above the post tops (0.829 vs 0.821). In `DojoKit_Taiko_front.png` the beam reads as a flat-topped
    block under the head.
  - **What reads instead:** the four **flat post tops, 4 mm under the drum** (`post_top()`, "post_top_below_drum_surface
    0.004"). The drum looks as if it rests on four flat blocks.
  - In `DojoKit_Taiko_side.png` and `Scene_Set_front.png` a light line shows under the belly. That is the floating
    gap.
  - Only `DojoKit_Taiko_Stand_hero.png` (stand alone) shows the U-saddles.
- **UCX.** Three hulls per beam:
  - a centre hull over |y| <= 0.18 (+-18 deg), whose chord top sits about 28 mm above the arc, inside the drum's space;
  - two shoulder hulls, each also chording the arc and taking in the wedge block.
  - This is harmless for gameplay but not exact.
- **Reference sheet** (`References/Dojo/dojo_drum_pavilion_ref.png`, taiko panels). The posts rise beside the drum,
  with a block at the post top at about the drum-bottom level. The saddle itself is hidden in every panel, so **the sheet
  neither shows nor rules out the seat**. It shows no felt.

---

## 3. Recommended stand design for our drum

Keep the sheet's frame: the sills with stop blocks, the 4 posts, the rails with iron strap plates, the wedge blocks,
the cradle beams' X position and the drum centre at 1.25 m. Change only the seat and the post tops. This is a saddle
stand, matching the dojo yagura stands.

| Item | Now | Recommended |
|---|---|---|
| Saddles | 2 beams, x +-0.46..0.58 | **unchanged** (2 beams, same x, 12 cm thick along the axis) |
| Saddle surface | single radius 0.5805, 10 chords | **barrel-matched (doubly curved):** at each x, radius Rw(x) = body_r(x) + FELT_T + GAP. Built at 3 x-stations (xa, mid, xb; linear ruling alone would cut 0.38 mm in) with 24 arc segments (sagitta 0.44 mm); vertices pushed out by 1/cos(half-step) so every chord stays outside |
| Felt liner | none | **FELT_T = 5 mm** pad on the arc, horn to horn, flush with the beam's x faces (never past x 0.585). Inner surface = body_r(x) + GAP. Dark charcoal wool felt, roughness about 0.95, a fibrous normal. **User decision D1** (the sheet shows none; every real maker uses felt) |
| Contact gap | 3-18 mm | **GAP = 1 mm** nominal. Measured drum-to-felt 0-2 mm over the whole contact patch |
| Arc extent | +-43.6 deg (y +-0.40), horn top z 0.829 | **The arc runs up to a flat horn top at z_h = 0.90**, which it meets at y of about +-0.45..0.47 (half-angle about 50-54 deg, about 104 deg of arc). The horn rises 0.22-0.23 m above the arc bottom (0.19 D, inside the real 0.15-0.35 D range). Horn ends chamfered 15 mm |
| Saddle bottom / wood radius | arc bottom z 0.6695 | wood arc bottom z 0.6665 (x 0.46) to 0.6797 (x 0.58); the felt fills 1-6 mm above it |
| Post tops | flat at 0.821, 4 mm under the drum | **PT = 0.800 flat.** That is 25 mm clear of the drum at the post's inner top corner (drum there z 0.8254). The posts no longer touch the drum. The beam's horns stand **100 mm proud** of the post tops, so the curved seat shows in the end, side and 3/4 views |
| Joint | beam through a mortise in the post | the same through-tenon, now read as the beam housed in the post top with the horn above it (a watari-ago-style housing). Wedge blocks unchanged |
| Rings / tacks / collar | clear | unchanged: nothing touches the rings, the tacks (x 0.68-0.72) or the collar (x >= 0.5976) |
| UCX | 3 hulls per beam (centre chord about 28 mm into the drum) | **6 arc hulls per beam** (about 17 deg each, chord at most 7 mm above the arc) + 2 horn/wedge hulls per beam. Stand total 20 -> **30** hulls |

Alternative (bigger change, flag only). Make the saddle beams the topmost member: the posts end under them and the
beams overhang the posts, as in the Miyamoto 四本柱台 and MOKU box stand. This is more "catalogue", but it drops the
sheet's posts rising beside the drum, so it is not recommended unless the user prefers it.

**Option D1b (dojo-authentic, more ornate).** Use Asano-style crimson cushion cords along the two saddle tops, tied off
with white cords at the horns, in place of plain felt. This is the user's call; the sheet shows neither.

---

## 4. Change list for `build_taiko.py` (numbered), with acceptance checks

1. **Constants.**
   - Add `FELT_T = 0.005`, `SADDLE_GAP = 0.001` (was 0.003), `HORN_Z = 0.90`, `SADDLE_SEG = 24`,
     `SADDLE_XST = (CRADLE_X0, 0.5*(CRADLE_X0+CRADLE_X1), CRADLE_X1)`.
   - Retire `CRADLE_FLAT_Y`, since the arc end is now derived from HORN_Z per station.
2. **`cradle_profile(x, yend, r_off)`.** Take the station x and a radial offset (felt surface: GAP; wood: GAP + FELT_T).
   - R(x) = body_r(x) + r_off.
   - a_max(x) = acos((DRUM_Z - HORN_Z) / R(x)).
   - SADDLE_SEG segments, vertices at R/cos(step/2), end vertices exactly at R so they meet the horn flat at HORN_Z.
   - Flat horn out to yend; horn tip chamfer 15 mm.
3. **Saddle solid.** Replace `extrude_heightfield(xa, xb, ...)` with a 3-station loft:
   - wood profile at x = xa, mid, xb, joined by quads; bottom at CRADLE_BOTTOM; same UV rule (grain along Y);
   - all three profiles must keep the same vertex count. Use a fixed SADDLE_SEG and reparametrise by angle, so the
     arc-end y differs per station but the topology does not.
4. **Felt liner (if D1 = yes).**
   - A new part on the stand: a shell between r_off = GAP (inner, facing the drum) and GAP + FELT_T (on the wood), over
     the same angles and 3 stations, plus end caps at the horn ends.
   - New material slot `M_DKP_Taiko_Felt` built like the other taiko-own surfaces (`build_material` path; `OWN` +
     `MATERIALS` entries), with maps from `make_taiko_textures.py`: a new `T_DKP_Taiko_Felt_{BC,ORM,N}` at 512 x 512
     (power of two, full mips; BaseColor sRGB, ORM linear, Normal DirectX).
   - Add the felt to the timber band / `pin_band_v` exclusion (it is not timber).
5. **Post tops.**
   - `post_top()` returns `min(drum_z_at_inner_corner - 0.025, HORN_Z - 0.10)`, which gives 0.800.
   - Keep the post section, chamfer and UVs.
   - Re-check the upper rail (RAIL_HI top 0.62) and the strap plates. They are unaffected; the posts stay 18 cm above
     the rail.
6. **Wedge blocks.** Unchanged (z 0.495..0.715, y 0.566..0.69). Confirm that they still overlap the beam ends after the
   horn change.
7. **UCX.** In the collision block, replace the 3 cradle hulls per beam:
   - 6 hulls tile the arc between -a_max and +a_max. Each hull = that segment's arc vertices (from the felt surface if
     the felt is on), at x = xa-0.002 and xb+0.002, + the same points dropped to CRADLE_BOTTOM;
   - 2 horn hulls per beam (horn flat + wedge block, as the current shoulder hulls).
   - Post hulls follow the new PT.
   - Update the `ucx` description in the collision table (20 -> 30 hulls).
8. **Stick solver.** Re-run `stick_poses()` unchanged. The sticks lean on the rail-end iron at the +X/-Y corner, which
   does not move. The post top only drops 21 mm, so check that the stick's lean contact is still the rail iron and not
   the post.
9. **`measure()`.** Replace the saddle-gap sampler, which now only checks vertices with |y| < CRADLE_FLAT_Y and z > 0.6.
   - Use a two-way BVH sample: the drum lacquer surface against the felt (or wood) top surface, on a 2 mm grid over the
     arc patch at all x in [xa, xb].
   - Report: `saddle_gap_min_max_m`, `saddle_contact_arc_deg` (where gap <= 2 mm), `saddle_contact_width_x_m`,
     `post_top_clearance_m`, `horn_above_post_m`, `drum_stand_interpenetration_max_m`.
10. **Renders.** Add an end-on stand+drum close-up (`closeup_saddle.png`, camera at x = 1.6, z = 0.85, looking along -X,
    low and slightly off-axis) and an orthographic X-section through x = 0.52 (`section_saddle.png`, the drum + stand
    cut). Keep `Stand_hero`.
11. **Notes.** Update `WorkFiles/dojo/build/props/taiko/BUILD_NOTES.md`: the stand row, saddle gap, post-top row and
    UCX count. Point the "Known gaps / tall U-saddle board" line at this study.

### Acceptance checks (all measured, in `measure.json`, `qa_report.json` and the renders)

| # | Check | Pass |
|---|---|---|
| A1 | Drum-to-saddle gap over the contact patch (felt surface, or wood if D1 = no) | **0 <= gap <= 2 mm** everywhere the arc is under the drum, at all x in [0.46, 0.58]; no negative samples |
| A2 | Contact arc | gap <= 2 mm over **>= 90 deg** of arc, on **>= 110 mm** of the 120 mm beam width, at both saddles |
| A3 | No interpenetration | 0 drum vertices inside any stand mesh, and 0 stand vertices inside the drum (BVH parity or ray test); max penetration 0.0 mm |
| A4 | Posts clear | post top >= 20 mm below the drum surface everywhere over the post; no stand part except the saddles within 10 mm of the drum |
| A5 | Collar, tacks, rings clear | nearest stand-to-collar-hide >= 15 mm; tacks and rings >= 50 mm |
| A6 | Seat visible | in `DojoKit_Taiko_front.png` (end view) and the new `closeup_saddle.png`, the horns and the arc rim show on both sides of the head; in the side ortho the horns show above the posts (100 mm); in `Stand_hero` the felt-lined arcs show |
| A7 | No light line | no lit gap under the belly in `DojoKit_Taiko_side.png` / `Scene_Set_front.png` at the saddle stations |
| A8 | UCX | 30 stand hulls named `UCX_SM_DKP_Taiko_Stand_LOD0_NN`; `check_ucx_cover.py` 0 stand vertices outside the hulls by > 1 mm; each arc hull's top within 7 mm of the arc |
| A9 | QA / export | `qa_check(require_uv1=True)` 0 hard fails on the stand and every LOD; LODs strictly descending (stand LOD0 expected about 2.1-2.4k tris, from 1,712); felt textures power of two with full mips; exported only through `Scripts/pipeline` |
| A10 | Unreal (main session, one process) | the stand imports with 30 simple hulls and no extra shapes; the felt material is assigned; no engine-default material |

---

## 5. Sources (all read 2026-10-02)

- Asano Taiko, 台 product list (20 stand types): https://www.asano.jp/product/category/6
- Asano Taiko, 武徳道場型台 (dojo stand; for judo and kendo dojos; drum centre 140 cm for a 2-shaku drum; photo shows
  two concave top beams and the orange cushion cord): https://www.asano.jp/product/126
  - photo: https://www.asano.jp/uploads/736074976b4bb545e77bb8af6829535ddc8383c1.png
- Asano Taiko, 四本柱台 (drum centre 170 cm for 1.6 / 2 shaku): https://www.asano.jp/product/124
  - photo: https://www.asano.jp/uploads/36e13c6a890d61bff15cb6e2511cbaf68dd204b0.png
- Asano Taiko, 大太鼓用四本柱台 目有 (odaiko, 3 shaku -> centre 170 cm; casters; cushion cords tied with white cord):
  https://www.asano.jp/product/128
  - photo: https://www.asano.jp/uploads/077ad043168506a9f63d10abefa382d9381ef95a.png
- Miyamoto Unosuke, 太鼓台 list: https://www.miyamoto-unosuke.co.jp/collections/drumstand
- Miyamoto Unosuke, 宮台 本欅製 (shrine and temple use; keyaki; carved wing cradles on two end frames):
  https://www.miyamoto-unosuke.co.jp/collections/drumstand/products/13110101010000
- Miyamoto Unosuke, やぐら台 本欅製 (for Butoku dojos, judo and kendo; keyaki; two notched top crossbeams on splayed legs):
  https://www.miyamoto-unosuke.co.jp/collections/drumstand/products/13110301014000
- Miyamoto Unosuke, 四本柱台 木目材製 (bon odori and general use; two notched top beams between posts):
  https://www.miyamoto-unosuke.co.jp/collections/drumstand/products/13110202010000
- MOKU Studio stands (photos: Odaiko/Ojime box stand with two deep arc-cut, felt-lined saddle boards; Yatai stand with
  thick felt in the arc and wedged through-tenons; Odaiko X-stand): https://www.mokustudio.ca/taiko-2
- Tengu School of Taiko, drum stands ("pine with felt contact points" on each stand):
  https://www.tengutaiko.com/taiko-drum-stands.html
- taikos.com, nagado daiko stands (search-result snippet only; the page body did not load): felt at the contact points;
  miya-dai "wings" cradle: https://taikos.com/shop/taiko-accessories/taiko-drum-stands/nagado-daiko-stands/
- Taiko Center, size of taiko (nagado length = 1.25-1.3 x head diameter): https://taiko-shop.com/blogs/learn/size-of-taiko
- Taiko Center, yagura stand for ohira daiko (beech; horizontal on top): https://taiko-shop.com/products/yagura-stand-for-ohira-daiko
- Make:, odaiko on a budget (cradle of shaped 2x12s, 4x4 legs, 2x6 braces, 1/2 in carriage bolts):
  https://makezine.com/article/workshop/woodworking/making-the-25k-odaiko-drum-on-a-budget/

The photo-based numbers (arc 80-120 deg, horn rise 0.15-0.35 D, board thickness, felt 3-6 mm, saddle spacing
0.6-0.7 L) are estimates by eye from the product photos above, not maker specifications. No maker page read gives
saddle dimensions.
