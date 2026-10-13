# Sniper Rifle SR-01 (SR01): craft study (2026-10-12)

How each part is made, bevelled, finished and worn, and the real-pattern rulings for the small parts. Data twin:
`craft_parts.json` (read by `tools/make_spec.py`; the spec's `parts` carry these fields with the measured numbers).

**Real pattern.** A modern .308-class bolt-action rifle in a one-piece aluminium chassis: a short action with a
3-lug, 60 deg bolt, a detachable double-stack box, a fixed chassis butt with an adjustable riser, and a tension-swivel
folding bipod on a forend dovetail. The look is the sheet's; construction follows how such parts are made. No
maker's part is copied, and no real product name appears in any shipped text.

**Sources.** The sheet (the 4-8x zooms in `scratch/zoom/`, local only); GUN_BUILDING_STUDY 3.1-3.7;
`WorkFiles/studies/guns/HARD_SURFACE_CRAFT.md` and `MATERIALS_AND_STANDARDS.md` (Cerakote, anodizing, phosphate, rubber
values; the sheet's OD measured there as 89, 89, 78 rendered). **No real photos were downloaded** in this run (no user
go, unattended). The rulings below rest on general engineering knowledge of the pattern, so W1 should start with a
short real-photo pass into `scratch/realref/` (local only, never committed) to confirm RP1, RP5, RP10 and RP15
before the form build.

**`References/AWP.webp`** was used for one thing only: to confirm that the legs of such a bipod fold forward along
the barrel. Nothing of its look is used: not its livery, panels, thumbhole stock or anything else.

## 1. Process classes and bevels (study 3.1)

| Part | Process class | Edge (LOD0) | Finish |
|---|---|---|---|
| Chassis (centre + forend + guard + well + dovetail) | M-chamfer, machined aluminium | 0.6 x 45 outer; pocket corners keep a 3.0 cutter radius; slot edges 0.4 | OD ceramic paint over aluminium |
| Butt, pad plate | M-chamfer | 0.6; cut-out inside corners R 2.5 | OD paint |
| Cheek riser plate | M-chamfer | 0.6; the drawn 6 x 45 lower-front chamfer | OD paint; posts phosphate steel |
| Butt pad | P-round, moulded rubber | R 3-4 outer, R 1.5 grooves, 1.5 deg draft | rubber |
| Grip | P-round, glass-filled polymer | R 1.5-2.5, 1.5 deg draft, parting line on the mid-plane | polymer, moulded texture panels |
| Receiver | M-chamfer, machined steel | 0.4 | phosphate |
| Rail | gunlib `rail_1913` | 0.3-0.5 | black anodized |
| Bolt | M-chamfer lugs 0.3; M-round shroud 0.8 | | polished bare steel body, phosphate shroud |
| Bolt handle and knob | M-round stem 0.8; the knob is a revolve | | phosphate |
| Safety, trigger, mag release | M-chamfer 0.3-0.4 / C-fillet 1.0 (trigger) | | phosphate |
| Barrel | M-chamfer 0.3 at the flute edges; crown 1.0 x 45 | 48 sides | phosphate (matte black) |
| Compensator | M-chamfer; the drawn 2.0 front chamfer | 48 sides | phosphate + soot |
| Magazine | S-bend (stamped steel, R 1.0 inside), S-cut 0.25; polymer floorplate R 1.0 | | phosphate / polymer |
| Bipod clamp and body | M-chamfer 0.5 | | black anodized |
| Bipod legs | M-round (drawn tube; ends 0.8) | | black anodized outer tubes, polished steel inner legs, rubber feet |
| Scope (attachment) | M-round (machined aluminium revolves) 0.4-0.8 | knurl as geometry on the turret skirts | black anodized; rubber eyecup |

Visibility minimum (study 3.1): >= 0.4 mm at the rear (comb, riser, action), 0.5-0.7 mid, 0.7-0.9 front. Every
chamfer above meets it, and the classes differ (G1: CV > 0.3).

## 2. Part by part

**Chassis.** One machined part from the butt joint (X ~244) to the forend front (X 836.8). No seam is drawn between
the centre and the forend, so it is built as one part. Inside it are modelled the real features the bolt and the
magazine meet:
- the **bolt raceway**: radius 12.5 on the bore axis, open on top from the shroud's rear to the receiver front, so
  the bolt can run 88 mm back;
- the inletted receiver pocket;
- the **mag well**: walls 3.0, 0.3 clearance, a top shelf, and a catch window in the rear wall for the release hook;
- the trigger-housing pocket.

The forend is a U-tube that floats around the barrel with >= 3.0 radial clearance. The drawn side panel on the
action is a 0.8 mm pocket with R 3 corners. The three side slots per side are cut through with wall reveals. They are
an original pattern and are never named after a trade standard. The drawn lower band is an integral **plain
dovetail** (38 across, 45 deg flanks, no teeth drawn, so none are cut). It is the bipod clamp's seat.

**Butt.** Fixed. The brief calls the butt "skeleton/folding-style", but no hinge knuckle, fold seam or latch is
resolvable on GR, GL or TOP, so it folds in nothing: no `stock` bone (open Q4). The traced profile has a flat comb (the
riser seat) at Z -16.7, a stepped heel and the lower cut-out rising to the grip. The two drawn round heads on the
right are length-of-pull / height clamp knobs (knurled caps). GL draws a rectangular recess on the left: a QD sling
cup (`SlingRear`).

**Butt pad.** A thick rubber pad (52.9 incl. the spacer plate) with the drawn grooves. The spacer plate carries three
drawn socket heads (the middle head spans 4.4 px, so its size comes from the sheet; the outer two from norms).

**Cheek riser.** An aluminium plate on two steel posts (dia 10) in bores in the butt top, with a clamp lever on the
left (GL). The posts are exposed 13.2 mm in the sheet pose, and that pose is the rest. Travel is -12.9 (plate 0.3
above the comb) to +12.0. The ADS eye point (95 mm behind the eyepiece, X 176.1) sits over the riser, 25.6 mm above its
top. This is the cheek-weld geometry a real riser exists for.

**Receiver, bolt, bolt handle.**
- **Receiver:** round, dia 34.3, X 382-567. The port is opened from the drawn 422.5-507.1 to the full bolt stroke,
  with wall reveals.
- **Bolt:** dia 17.8 with three lugs (OD 25.4) that lock into three 60 deg recesses in the front ring (modelled).
  The bolt face is recessed with an extractor hook and an ejector hole.
- **Handle:** swept 15 mm rearward to a spherical knob dia 24.8. The knob's X and Z come from GR; its outboard reach
  comes from TOP (Y -67.6).
- **Cycle:** rotate 60 deg (the knob goes from 26.4 deg below horizontal to 33.5 above), then slide back 88 mm. The
  knob clears the mounted scope by 29.9 mm over the whole cycle. The open bolt's rear (X 257.4) stays 77 mm ahead of
  the riser.

**Safety.** Not resolved on the sheet. Real 2-position tang rocker on the right behind the bolt handle, pivot
(360, -17.5, -16), FIRE forward = bind, SAFE -12 deg. Serrated thumb face as geometry.

**Trigger.** The traced curved blade; pivot above it inside the housing (368, -57); 6 deg pull = 2.4 mm at the
face. The tip keeps 1.3+ mm to the guard at full pull. The guard is part of the chassis (no seam drawn).

**Mag release.** The sheet draws a thin lever directly behind the magazine with a 1 px gap. A real forward-push
paddle needs room to move, so it is built as follows:
- pivot (408.6, -74) in a clevis in the guard's front leg;
- a hook 24 mm above the pivot, engaging a notch in the magazine's rear wall at Z -50 by 1.4 mm;
- a pad 40 mm below the pivot;
- press -4.5 deg: the pad moves 3.14 mm forward, the hook 1.88 mm back (it clears the notch by 0.48), and the pad
  keeps 0.36 mm to the magazine;
- the front face is built 3.4 mm behind the drawn edge (1.8 sheet px, under the 2 px L3 tolerance; declared).

**Magazine.** A straight 10-round double-stack steel box, vertical:
- fore-aft 89.3 (sheet), thickness 26.5 (unseen except the 3/4; real class);
- top at Z -11.0 under the bolt, with feed lips, follower and top round modelled;
- two pressed ribs per side (the 3/4);
- polymer floorplate, rear catch notch.

Its AO is baked alone (rifle lesson).

**Barrel and compensator.**
- **Barrel:** heavy contour, 35.2 tapering to 31.8. Six straight flutes, 6.0 wide x 2.0 deep with radius bottoms,
  over the drawn span; the run-outs are ball-end cutter exits (no knife edges, so no UD2 needles). 22 in from breech
  to crown; bore 7.8, darkened >= 2 calibres deep.
- **Compensator:** a closed linear-compensator sleeve (no ports drawn; the brief says "simple cylindrical muzzle
  cap"). Exit bore 12 mm (3/4 view), with an internal baffle visible only down the exit.

**Bipod.** A tension-swivel folding pattern, and every drawn piece has its real part:
- **Clamp:** on the dovetail. A swivel body runs back to the leg yoke around the drawn hub. The drawn knob under the
  hub is the swivel-tension knob.
- **Legs:** each leg pivots independently on a transverse pin at the hub (X 719.6, Z -62.3), at Y +-19.5. A
  spring ball in a notched hub disk gives detents at 0 deg (folded forward, the sheet pose) and +90 deg (straight
  down).
- **Extension:** outer tubes OD 19.4 to the lock collar; inner legs dia 12.7 telescope 0..76 mm in five 19 mm notches,
  locked by the collar's button.
- **Feet:** spool-shaped rubber, dia 37 x 29 (side-view size).
- **Clearances:**
  - folded, the legs sit 0.2 under the clamp (hinge row) and the feet 4.2 under the forend band, with 2.0 between
    the feet;
  - over the deploy sweep the minimum distances are: clamp 0.2, forend 13.0, barrel 29.8, tension knob 2.8 (Y),
    magazine 206.7;
  - cant +-15 deg: folded worst 7.7, deployed 32.4.
- **Deployed:** the bore stands 268 mm (ext 0) to 344 mm (ext 76) above the ground.

**Scope (attachment `SM_Att_Scope_LongRange`).**
- 34 mm tube, 45.1 eyepiece, 62.1 bell.
- Elevation turret on top, windage on the right, side-focus knob on the left (the TOP view shows the left knob
  bigger than the right turret).
- Magnification ring with a throw lever; rubber eyecup ring.
- Two-piece medium 34 mm rings, each with a recoil lug in a rail slot (slots 2 and 12), two cross-bolt nuts on the
  left and four cap screws.
- No text and no reticle markings. Its lenses are their own slot (opaque glossy, study Q19).

## 3. Materials, texture and wear

| Finish | Values (Unreal metal/roughness) |
|---|---|
| OD ceramic paint over aluminium (chassis, butt, riser, plate) | metallic 0, sheet 89/89/78 rendered (target ~0.05 linear, hue 59, sat 0.12), roughness 0.55-0.70, orange-peel micro 0.2-0.5 mm (Detail16 normal); wears to a dark rim first, then bare aluminium (metallic 1, 0.91, rough 0.30-0.45) only on the highest corners ("light edge wear to dark grey") |
| Black anodized aluminium (rail, bipod body/tubes, scope) | metallic 0, sRGB 45-62, rough 0.45-0.65; bright silver at rare edges |
| Manganese phosphate steel (barrel, receiver, compensator, handle, small parts, mag body) | metallic 0, sRGB 50-66, rough 0.65-0.80 (oiled 0.55-0.70); wears to bare steel 0.53-0.56 linear |
| Polished steel (bolt body, lugs, inner legs) | metallic 1, 0.53-0.56, rough 0.15-0.30 |
| Black polymer (grip, floorplate) | metallic 0, sRGB 42-50, rough 0.55-0.70; polish only |
| Rubber (pad, feet, eyecup) | metallic 0, 0.02-0.03 linear, rough 0.75-0.90 (the sheet's pad reads 0.09 x the backdrop) |
| Soot (compensator exit, port) | 0.02-0.03, rough 0.85-0.95 |

**Wear by cause (study 3.4).** Paint chips at corners (R): butt toe and heel, forend front, slot edges, riser
edges. Hands polish the paint (G): grip top, the riser's left top (cheek weld), the forend belly, the knob, the
safety's arc. The bolt body is polished bare by sliding. The feet, the floorplate corners and the butt toe are
abraded (R). Dust sits in the rail slots, forend slots and pocket corners (B). Soot is at the exit and the port.
Left and right wear differ (G9).

**Lessons planned in.** Rough-real finishes and a physical light rig from the first look (the SMG's "flat clay"
cause was near-uniform paint under flat grey light). L5 calibrates against sheet crops before the first look. With
Metal From ORM on, the OD paint is dark enough (the study 5.9 brightness trap does not bite).

## 4. Real-pattern rulings (the builder follows these)

| # | Part | Ruling |
|---|---|---|
| RP1 | bolt | 3-lug, 60 deg throw, 88 mm stroke, face X 505 at rest |
| RP2 | handle and knob | swept stem, spherical knob dia 24.8, screw-on with a thread-relief groove |
| RP3 | trigger and guard | single-stage precision trigger, pivot above the blade, 6 deg; guard integral with the chassis |
| RP4 | safety | 2-position tang rocker, right, behind the handle; FIRE forward (bind), SAFE -12 |
| RP5 | mag release | forward-push paddle in front of the guard; hook 24 above the pivot, pad 40 below (the spec's leverage) |
| RP6 | magazine | straight 10-round double stack, vertical, 26.5 thick, 2 pressed ribs per side, polymer floorplate |
| RP7 | rail and rings | 1913 base, 15 slots, flat; medium 34 mm two-piece rings with recoil lugs on slots 2 and 12 |
| RP8 | riser hardware | two dia 10 posts, left clamp lever, travel -12.9..+12.0 |
| RP9 | butt adjustment | fixed; length of pull by spacer (no bone); two clamp knobs as drawn |
| RP10 | bipod and mount | tension-swivel folding pattern: independent legs at the hub, detents 0/+90, ext 0..76 in 19 mm notches, cant +-15, the drawn rear knob = tension knob |
| RP11 | bolt stop | internal, not animated, no bone |
| RP12 | muzzle device | linear compensator, closed sleeve, 12 mm exit |
| RP13 | flutes | 6 straight, 6.0 x 2.0, radius bottoms, ball-end run-outs |
| RP14 | forend slots and band | slots cut through (original pattern); band = plain dovetail, no teeth |
| RP15 | scope | 34 mm, 56 mm-class bell, elevation top, windage right, side focus left, magnification lever, rubber eyecup |

## 5. Unseen surfaces (plain)

The chassis underside except the well and the dovetail; the bolt's left side; the trigger housing; the scope
underside; the butt's QD cup interior; the clamp's left screw head; the magazine top (real pattern, plain).

## 6. Inconsistencies between views

I1 knob X (TOP 32 mm further back: GR wins). I2 TOP right-edge shadow bias (left half x 2). I3 TOP inflates rounds
(side views win). I4 TOP folded feet only ~60 wide (legs at +-19.5 with 37 feet: 76, declared). I5 magazine edges
-0.9/+1.3 deg (built vertical). I6 the drawn paddle touches the magazine (moved 3.4 back, declared). I7 rail pitch
10.6 (built 10.01). I8 the 3/4 bipod is folded (the deployed pose comes from the real pattern).

## 7. Fab-original changes (not applied; the user decides)

Two stepped side pockets instead of one; tapered lozenge forend slots of three lengths; a scalloped riser front; a
reversed-curve butt cut-out with a thumb notch; a hex grip texture with a thumb ledge; a 4-slot compensator; cleated
disc feet. Any four of these move the read away from any real chassis.

## 8. Open questions (craft side; defaults the build follows)

Merged into `SR01_STUDY.md` section 9 (Q2 bipod splay, Q3 barrel thickness, Q4 fixed butt).
