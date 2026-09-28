# SM_Flashbang: scale, game and pipeline plan

**Date:** 2026-09-27. **Role:** scale and game research. Nothing was downloaded. The numbers come from the reference
PNG and from files already on disk.
**Reference:** `References/Flashbang/flashbang_reference.png` (1254 x 1254, sha `64d1f560...`, checked).
**Scratch measurements:** the shared scratchpad `scale/` (`scale_silhouette.json`, `scale_profile.txt`, and crops).
Pixel figures below are top-row reference pixels.

This plan sets the frame, the sockets, the split into meshes, the collision, the budgets, the material slots and the
conventions. **The Study owns the part geometry.** Every dimension here marked *est.* is a starting value that the
Study's metrology replaces. The sockets are defined by **rules on the built parts**, so the build computes their
exact values from its own geometry and writes them to the sidecar.

---

## 0. Decisions at a glance

| Topic | Decision |
|---|---|
| Size | Painted sleeve diameter **44.0 mm** (the grip), which gives **about 170 mm overall** with the reference's proportions. Scale is **0.2529 mm per reference px**. |
| Frame | +Z is the canister axis, pointing to the fuze. **The origin is the centre of the base end face** (floor contact). +X runs through the lever centreline, so the lever lies on +X. The ring falls on -Y (the Blender front view is the reference's view 1). |
| Sockets | `Grip`, `Throw` (the centre of mass), `Pin`, `LeverHinge` and `Flash`, all Empties plus the sidecar (section 4). |
| Separate meshes | **Yes: four static meshes.** `SM_Flashbang` (assembled, the main asset), `SM_Flashbang_Body` (live body, and also the spent canister), `SM_Flashbang_PullRing` (ring and pin, pivot = the `Pin` frame) and `SM_Flashbang_Lever` (spoon, pivot = the `LeverHinge` frame). All four share one UV atlas and two material instances. |
| Collision | Three UCX hulls on the assembled mesh and the body: canister, fuze and lever arm. The ring has none. One hull on each part mesh. |
| Triangles | LOD0 target **5,500**, with a hard cap of **6,000**. LOD1 is about 2,600 and LOD2 about 1,100. |
| Textures | One **2048** atlas: BC, ORM and N (DirectX), plus a 2048 paint Detail and its Detail16. Section 8 gives the rule for moving BC and N to 4096. |
| Material slots | **2.** Slot 0 `Paint` uses `M_Fabric_Master` with **Metal From ORM ON**: the recolourable olive, while chips stay bare steel. Slot 1 `Steel` uses `M_Steel_Master` for the fuze, collar, base cap, lever, ring, pin and the brass inner tube. |
| User colour | The paint's `Colour` defaults to the reference olive, taken from the baked maps. Steel takes only the pack's optional `Steel Tint`. |
| Mass | Design mass 300 g, so the physics override is 0.30 kg. Lever 0.015 kg, ring and pin 0.008 kg. **CCD ON** when thrown. |

---

## 1. Real-world size

### 1.1 What the reference fixes (top row, view 2, centre column; base end face y = 716)

These pixel positions were measured by the scale role and are rounded. The Study refines them.

| Feature | px | mm at 0.2529 mm/px |
|---|---|---|
| Painted body width (rows 270-620) | 173.5 (x 381-554; view 1 gives 177, view 4 gives 178) | **44.0 (defining)** |
| Upper painted sleeve (wider, with a real step at its bottom edge) | about 185 | about 46.9 |
| Base cap | 190 (view 1 196, view 4 198: rim bulge) | about 48.0 to 49.5 |
| Fuze housing (square): face in view 1 about 90 px, diagonal in view 2 about 126 px | | face about 22.5, diagonal about 32 |
| Pull ring outer diameter (view 2, seen edge-on: y 60-250) | about 190 | about 48 (the reference ring is large, and it is the reference) |
| Lever width (view 4) | about 45 | about 11.4 |

The vertical stack, as Z from the base end face:

| Feature | y (px) | Z (mm) |
|---|---|---|
| Base end face | 716 | 0 |
| Base cap top / paint bottom edge | about 635 | 20.5 |
| Hole row 3 (centre) | 528-593 (560) | 31.1-47.5 (39.3) |
| Engraved line | about 501 | 54.4 |
| Hole row 2 (centre) | 408-473 (440) | 61.5-77.9 (69.7) |
| Engraved line | about 381 | 84.7 |
| Hole row 1 (centre) | 291-355 (323) | 91.3-107.5 (99.4) |
| Step at the bottom of the upper sleeve | about 260 | 115.6 |
| Top of the paint (chamfer) | about 181-190 | 133-135 |
| Collar tiers | about 120-178 | 136-151 |
| Square fuze housing | about 57-120 | 151-167 |
| Top of the fuze / lever top plate | 45 | **169.7** |
| Lever tip (views 1 and 4) | about 585-595 | about 31-33 |

- The hole pitch is 118.5 px, or 30.0 mm.
- The front hole is about 57 x 65 px, or **14.4 wide x 16.4 tall mm**.
- View 2 shows one centred hole and two at the limbs at about ±60°. That reads as **6 holes per row, 18 in all**,
  in vertically aligned columns. **The Study confirms the count and the alignment.**
- The lever stands **off** the sleeve. In view 1 the lever strip is at about x 270-297 and the sleeve edge at 246,
  so the lever arm sits roughly 6 mm outboard of the paint. This is to be confirmed once the Study has fixed the
  azimuths of views 1-4.

Proportions: overall height is **3.86 D**, the painted body 2.6 D, the base cap 0.47 D, and the fuze with its collar
0.78 D. This is more elongated than an M84-type stun grenade, which is about 133 x 44 mm, or 3.0 D.

### 1.2 Choice: D = 44.0 mm, overall height about 170 mm

- The brief asks for about 13-15 cm tall and 4.5-5 cm across. With the reference's 3.86 ratio, both cannot hold at
  once: 150 mm tall means D = 38.9 mm, and D = 45 mm means 174 mm tall.
- **The proportions are fixed ("to the T"). The only free number is the scale, and the grip should set it.**
  - 44 mm is the common real stun-grenade diameter (M84-class, 1.73 in).
  - It sits in the ergonomic power-grip optimum of about 38-50 mm.
  - A 44 mm cylinder is 138 mm around. A MetaHuman adult hand (palm about 85 mm, index finger about 72 mm) closes
    fully around it, fingers over the thumb, like the M84 in real hands. The female player's hand closes too.
- At 38.9 mm the canister would read as a thin tube in the hand, thinner than any real stun grenade. At 48-50 mm the
  overall height grows to 185-190 mm.
- The height, 170 mm (about 13 % over 15 cm), is a consequence of the reference's own long canister. It is not an
  error.
- The scale is **one constant in `flashbang_spec.py`** (`body_diameter_mm = 44.0`). If the user prefers a shorter
  item, D = 40 mm gives 154 mm, and it is changed before any bake.

**Mass.** The M84 weighs 236 g at 133 mm long. Scaled by length (170 / 133), that gives **about 300 g**, so the
physics override is **0.30 kg**. Part masses are 0.015 kg for the lever and 0.008 kg for the ring and pin (a 2.4 mm
steel wire ring 48 mm across, plus the pin).

---

## 2. Build frame and origin

- **Units:** metres, unit scale 1, transforms applied (qa_check).
- **Axes:** export Forward -Y, Up Z, the house pair.
- **The frame is defined by the parts, not by the camera:**
  - **+Z** is the canister axis, from the base to the fuze.
  - **Origin** is the centre of the base end face, Z = 0 on the floor-contact plane. This follows the guidelines'
    rule for props (floor contact): the item stands upright on a table or in the armory's glass cases with no
    offset, and the spent canister rests on its base.
  - **+X** runs through the lever's centreline plane, so the lever lies on +X.
  - **-Y** is then the ring side. From the lever side (view 4) the ring hangs to the viewer's left, which is -Y.
    The Blender front view, looking along +Y, is the reference's view 1 ("pull ring toward the viewer").
- **In Unreal:** X_ue = x, Y_ue = -y, Z_ue = z, in cm. So in Unreal the lever is on +X and the ring on +Y.
- The Study fits the true azimuths of views 1-4 around Z. The renders reproduce them. The views need not be 90°
  apart.

---

## 3. Grip and hand pose (right hand, overhand throw)

- **The hold** is a power grip on the painted body.
  - The palm and its heel press the **lever** against the canister. The lever is the part that must stay held down,
    and it lies on +X.
  - Fingers 2 to 5 wrap the 44 mm sleeve inside the **grip channel** between the base cap's top (Z 20.5) and the
    upper sleeve's step (Z 115.6). That channel is 95 mm long, and a four-finger span is about 83 mm.
  - The index finger sits snug under the step, so the step and the wider base cap act as finger stops.
  - The thumb lies over the lever's upper arm, below the fuze.
  - The ring is on the thumb's side (-Y), facing the off hand, so the left index finger can pull it. This is the
    standard right-hand technique.
- **Palm centre:** the midpoint of the 83 mm finger span below the step, **Z ≈ 74 mm** (115.6 − 41.6), on the axis. That is between
  hole row 2 (69.7) and the engraved line (84.7), and just below the centre of mass (about 82 mm, section 5). A
  hand holding a thrown object at its centre of mass is what a real throw does.
- **Left-handed holds:** mirror the character's hand pose, not the mesh. The mesh is not mirrored, because its UVs
  and lettering-free art would survive a mirror, but its sockets would not.
- **In Unreal:** put a skeleton socket such as `Grenade_R` on `hand_r` (the guidelines: weapon sockets on `hand_r`),
  posed in the editor with this grip. Attach the grenade with the component's relative transform =
  inverse(`Grip`). The item's frame then stays independent of the rig.

---

## 4. Sockets (Empties via `pipeline.helpers.make_socket`, shipped through the sidecar)

Every socket is created on `SM_Flashbang_LOD0` and on `SM_Flashbang_Body_LOD0` with the **same** values. The part
meshes carry no sockets: their origin is their pivot.

**Rotation convention.** `make_socket` takes "the orientation you want in Unreal, expressed in the parent's local
Blender space". It adds the 180° Y correction itself.

**The sidecar values below are exact outputs of `ue_socket_transform`.** They were run on these est. positions in
Blender 5.2 with the pipeline helper. A `view_layer.update()` is **needed before `socket_record`**, or the record
reads 0.

| Socket | Rule on the built parts (the build computes it) | Est. Blender (mm) | Blender rotation (deg) | Sidecar (Unreal) | Use |
|---|---|---|---|---|---|
| `Grip` | On the axis, at the palm centre: Z = step Z − 41.6 mm (half of 83 mm) | (0, 0, 74) | (0, 0, 0) | loc (0, 0, 7.4) cm, rot 0/0/0 | Hand attach (inverse of the socket) |
| `Throw` | The **centre of mass** of the assembled solids (5.1), rounded to 0.1 mm | (1.5, -0.7, 82) | (0, 0, 0) | loc (0.15, 0.07, 8.2), rot 0/0/0 | Launch point, spin centre, and the check against Unreal's centre of mass |
| `Pin` | On the pin axis, at the pin's head (the eye the ring passes through). **+X points along the pull**, out of the fuze. +Z is the component of world up normal to X. | (20, -6, 157) | (0, 0, -90), pull toward -Y | loc (2.0, 0.6, 15.7), **yaw 90** | Pull-ring attach and the pull animation |
| `LeverHinge` | On the lever's pivot axis, where its top hooks the fuze lugs, at the lever's mid-width. +X points radially out through the lever, +Y along the hinge axis, +Z up. | (24, 0, 165) | (0, 0, 0) (the lever defines +X) | loc (2.4, 0, 16.5), rot 0/0/0 | Lever attach and its fly-off |
| `Flash` | On the axis, at the centre of the perforated section (the row 2 hole centre) | (0, 0, 69.7) | (0, 0, 0) | loc (0, 0, 6.97), rot 0/0/0 | Flash, light and smoke FX spawn |

Notes:
- **The pin's axis direction** comes from the views: view 1 sees the pin boss end-on, and the ring lies on the -Y
  side, so the axis is along Y and the pull is toward -Y. **The Study confirms it.**
  - The rule above stays the same whatever the answer: +X of `Pin` is always the pull direction.
  - `pin_travel_mm` is the pin's length inside the fuze housing plus 2 mm. The build measures it from the modelled
    pin and writes it to the sidecar's `parts` block.
- **Lever opening.** The lever opens about `LeverHinge`'s **Y** axis, with the tip swinging outward (+X).
  - In **Unreal this is a positive pitch**: pitch takes X to Z, so it takes the tip (-Z) to +X.
  - In Blender it is a **negative** rotation about local +Y. This was checked: -90° takes (0, 0, -1) to (1, 0, 0).
  - The Unreal gate re-checks the sign on the imported asset (section 11).
- The `Throw` socket in the table is the est. centre of mass. The shipped value is the build's computed value.
- **Optional** (not required): `FuzeTop`, on the fuze housing's top face, for a small release spark. Add it only if
  the user asks.

**Sidecar extras** in `SM_Flashbang.sockets.json` and `SM_Flashbang_Body.sockets.json`:
- a `parts` block: `{PullRing: {mesh, attach_socket: "Pin", pin_travel_mm, mass_kg}, Lever: {mesh,
  attach_socket: "LeverHinge", open_axis: "socket Y", open_sign_ue: "+pitch", release_angle_deg: 100, mass_kg}}`;
- `mass_kg` 0.30;
- `use_ccd` true;
- `material` (the shading contract, as the smoke bomb has).

These keys are documentation for gameplay and the README. **Checked:** `ue_import_sockets.apply_sidecar` reads only
`payload.get("sockets")` and `payload.get("lod_screen_sizes")` (lines 48 and 176), so extra keys are ignored.

---

## 5. Separate meshes: recommended, with their gameplay

### 5.1 Why four meshes

| Mesh | Contents | Pivot | Used for |
|---|---|---|---|
| `SM_Flashbang` | Everything | Base centre (section 2) | World pickups, loot, the armory display, and any static placement. 2 sections, the cheapest draw. **The main Fab asset.** |
| `SM_Flashbang_Body` | Everything except the ring, pin and lever | Base centre | The live held body. After detonation, the **spent canister** (a flashbang body stays intact), left as a physics prop. Same 5 sockets. |
| `SM_Flashbang_PullRing` | Ring and pin | The **`Pin` frame** | Attached at the body's `Pin` with identity it reproduces the assembly. Pulled along its local +X. |
| `SM_Flashbang_Lever` | The spoon lever | The **`LeverHinge` frame** | Attached at `LeverHinge` with identity it reproduces the assembly. It swings (+pitch) and flies off. |

**Why it is worth it:**
- Pulling the pin and flinging the spoon are the moments a player *sees* a stun grenade being used. A single mesh
  cannot hide them: a static mesh cannot hide one section at runtime without a masked-material hack.
- The body doubles as the spent canister for free.
- The cost is small:
  - three more small FBX files from the **same** LOD geometry, split by a part tag (no new modelling);
  - no new textures, since all four share the atlas and the **same two MIs**;
  - 4 sections for the held grenade against 2. It matters only for the one grenade in hand. The battle royale's
    many grenades on the ground use `SM_Flashbang`.

### 5.2 How gameplay uses them (for the README)

1. **Equip.** Spawn `SM_Flashbang_Body` at the hand (section 3). Attach `SM_Flashbang_PullRing` at `Pin` and
   `SM_Flashbang_Lever` at `LeverHinge`, both with identity relative transforms. It looks exactly like
   `SM_Flashbang`.
2. **Pull the pin.**
   - Translate the ring component along its **local +X** by `pin_travel_mm`, about 0.15 s, driven by the off-hand
     animation.
   - Then attach it to `hand_l`'s index finger, or detach it with physics (0.008 kg).
   - The lever stays held.
3. **Throw.**
   - Detach the body with the throw velocity applied at `Throw`, **CCD on**. At 15-20 m/s it moves 25-33 cm per
     frame at 60 fps, over 5x its own 4.4 cm, so without CCD it tunnels through thin walls.
   - On release, rotate the lever about its socket Y to about **+100° pitch** over 0.05-0.08 s. Then detach it with
     physics (0.015 kg). Suggested impulse, tunable: 3 m/s along the socket's +X plus 0.5 m/s up, and about
     20 rad/s spin about the socket Y.
4. **Detonate.** After the fuze delay, spawn the flash FX at `Flash`. The body stays in the world as the spent
   canister.

### 5.3 How they are made (one geometry, split)

- Every part in the build carries a `part` tag: `paint_sleeve`, `inner_tube`, `base_cap`, `collar`, `fuze`, `hinge`,
  `pin_boss`, `lever`, `ring`, `pin`.
- For each LOD level, the assembled LOD is built once and then split:
  - **Body** = everything but `lever`, `ring` and `pin`;
  - **PullRing** = `ring` + `pin`;
  - **Lever** = `lever`.
- The part meshes are transformed by the inverse of their socket frame, meaning the *intended* frame, **before**
  `make_socket`'s 180° correction.
- UV0 is **identical**: the same islands in the same atlas.
- UV1 (lightmap) is generated per mesh.
- The PullRing and Lever get their own 3-LOD groups, built from the assembled LOD's subset at each level.

**The parts' screen sizes** use the pack rule on their own bounds radius, so every component switches at the same
physical distance (section 7.2).

---

## 6. Collision and physics

### 6.1 `SM_Flashbang` and `SM_Flashbang_Body`

Three UCX hulls, each ≤ 32 vertices, named `UCX_<node>_LOD0_00..02`:

| Hull | Shape | Why |
|---|---|---|
| `_00` canister | A **circumscribed** 16-gon prism from Z 0 to the top of the painted sleeve (about 135), radius = the base cap's maximum radius (about 24.0-24.8) | The body. It rolls like the real canister. |
| `_01` fuze | Hull of the collar tiers, square housing, hinge, pin boss and the lever's top plate (Z about 135-170) | The head. It stops the grenade standing on its fuze wrongly. |
| `_02` lever arm | An 8-vertex box around the lever's outboard arm (Z about 31-165) | The arm stands about 6 mm off the sleeve. Without it the lever sinks into the floor when the grenade lies on its lever side. |

- **The ring has no collision.** It is a 2.4 mm wire that would snag.
- The build reports the ring's largest protrusion outside the hull union. If it is over 3 mm, add a thin fourth hull
  for the ring and record why.
- **Gate:** the union of the hulls contains every LOD vertex except the ring and pin, worst vertex ≤ 0.5 mm outside.
  This replaces the smoke bomb's "one hull contains every LOD".
- The body has no lever, so it takes `_00` and `_01` only. `_01` still covers the hinge area.

### 6.2 Part meshes

- `SM_Flashbang_PullRing`: one hull, a flat 8-vertex box around the ring and pin. It only needs to land and settle
  when dropped.
- `SM_Flashbang_Lever`: one hull, the lever's convex hull, ≤ 16 vertices.

### 6.3 Mass and centre of mass

- **Mass override:** 0.30 kg for the assembled mesh and the body, 0.015 kg for the lever, 0.008 kg for the ring.
- **Centre of mass**, two estimates that agree:
  - **Weighted parts:** base cap about 60 g at Z 10, sleeve 70 g at 78, inner tube and charge 90 g at 78, fuze and
    collar 60 g at 150, lever 12 g at (30, 0, 110), ring 8 g at about (10, -25, 140). That gives **(+1.5, -0.7, 82)
    mm**.
  - **Hull-volume centroid:** what Unreal computes by default at uniform density. `_00` is about 244 cm³ at Z 67.6
    and `_01` about 50 cm³ at Z 152, which gives **Z ≈ 82 mm**.
- **Build rule:**
  - compute both, from the modelled solids with densities (steel 7.85, brass 8.5, the charge inside the tube 1.6
    g/cm³) and from the hulls;
  - `Throw` = the weighted centre of mass;
  - if the two differ by more than 5 mm, the README tells buyers to set the body's **Center Of Mass Offset** to the
    difference.

---

## 7. Triangle budget and LODs

### 7.1 LOD0 allocation (target 5,500; cap 6,000; Nanite off)

| Part | Triangles | How |
|---|---|---|
| Painted sleeve with 18 holes | 2,600 | Each hole has 16 sides: outer chamfer, wall and inner edge. Hole sagitta is 0.13 mm. |
| Inner brass tube, with its seam | 250 | 32 sides. The seam is a shallow groove or in the normal map. |
| Base cap with notched raised rim | 700 | 64 sides, crisp bevels, the notches as geometry |
| Collar tiers, square housing, hinge, spring/pin boss | 1,000 | Bevelled blocks; hinge knuckle and boss as cylinders |
| Lever (flanges, bends, bent tip) | 450 | Real bends, crisp bevels |
| Pull ring and pin | 500 | Torus 32 x 6 = 384, plus the pin and its eye |
| **Total** | **5,500** | |

- **Silhouette and close-up detail is geometry:** the holes, the step, the notches, the lever bends and the ring.
  Wear, grime, scratches and the engraved lines go in the maps, with the engraved lines in the normal map. This
  follows the lesson from the sword, sheath and heels: real forms are geometry.
- **LOD1 (about 2,600):** holes at 10 sides without an inner chamfer, rings at 24 x 4, a lighter base cap.
- **LOD2 (about 1,100):** holes at 6-8 sides (openings stay open), ring at 12 x 3, no notches.
  **Holes must never close.** A closed sleeve would show painted green where the brass shows, and the LOD would pop.
- **Budgets by mesh:** Body = assembled − 950 (about 4,550 at LOD0). PullRing 500 / 220 / 100. Lever 450 / 220 / 100.

### 7.2 Screen sizes and switch distances

- The pack rule (`props_lib.spec.scaled_lod_screen_sizes`): 1.0 / 0.10 / 0.035, times the bounds radius over 50 mm.
- With a bounds radius of about 97 mm (box X -24..+43 with the ring, Y about -35..+24, Z 0..170), that gives
  **about 1.0 / 0.19 / 0.068**. The build computes it from the real bounds.
- The pack rule keeps the switch distances constant across items: about **0.9 m and 2.5 m**, the smoke bomb's 0.89
  and 2.54 m.
  - A grenade in first person, at 0.35-0.6 m, is on LOD0.
  - A third-person camera at 2-3 m is on LOD1 or LOD2.
- **Gate (smoke bomb F-gate):** visible-surface deviation p99 < 1 px at each switch.

---

## 8. Textures

- **One atlas for all four meshes:**
  - `T_Flashbang_BC` (sRGB);
  - `T_Flashbang_ORM` (linear; R AO baked with Cycles, G roughness, B metallic exactly 0 or 1);
  - `T_Flashbang_N` (DirectX, green flipped on write);
  - `T_Flashbang_Paint_Detail` (sRGB 8-bit, reference only);
  - `Recolour/T_Flashbang_Paint_Detail16.png`.
- All maps are power of two with full mips. **All renders use the baked maps only.**
- **Texel density:**
  - Visible surface is about 38,000 mm², counting the inner tube at half density.
  - A 2048 atlas at 72 % packing gives about **8.9 texels per mm (89 px/cm)** on the paint, about 0.11 mm per
    texel. The inner tube gets about 45 px/cm.
- **Is 2048 enough?**
  - In game, at 90° hFOV:
    - 1080p at 0.4 m is 2.4 screen px/mm;
    - 4K at 0.4 m is 4.8 px/mm;
    - a 4K inspect at 0.2 m is 9.6 px/mm.
  - Close-ups 1-3 of the reference sheet are about 6-7 px/mm.
  - So **2048 covers every game view and three of the four close-ups.**
  - Close-up 4 (one hole) is a macro at about 14 px/mm.
- **Decision rule for 4096:** after the first shipped bake, render close-up 4's framing from the 2048 maps.
  - If the hole rim chip, the tube seam or the paint-edge wear measure visibly softer than the reference, raise
    **BC and N only** to 4096. ORM and Detail16 stay at 2048, for about +16 MiB.
  - Otherwise ship 2048.
- **Memory estimate at 2048 with mips.** The paint MI samples BC too, because Metal From ORM keeps the baked colour
  on metal texels.

| Map | Format | Size |
|---|---|---|
| BC | DXT1 | about 2.7 MiB |
| ORM | TC_Masks, no alpha | about 2.7 MiB |
| N | BC5 | about 5.3 MiB |
| Detail16 | G16 | about 11.2 MiB |
| **Total** | | **about 22 MiB** |

  The Steel MI shares BC, ORM and N. If memory matters, Detail16 can take Max Texture Size 1024, but only after the
  smoke bomb's mip-parity check (`final_pass/tools/fp_mips.py` pattern).
- **Wear:** chipped edges show bare steel (ORM.B = 1 inside chips, a thin transition), plus dark grime, scratches,
  and bright worn edges on the antiqued steel.
  - This is painted in texture space from curvature and AO **baked off the mid-poly**. The guidelines say there is
    no high-to-low bake for hard surface.
  - **No markings or text.**

---

## 9. Material slots and the pack colour system

Read from `WorkFiles/materials/MATERIALS_REPORT.md`, `Scripts/unreal/materials/np_masters.py` and
`material_spec.json`. Nothing there was edited.

### 9.1 Two slots, following the **Snow Flower sheath's shared-atlas pattern**

The sheath is the only item that already uses Metal From ORM.

| Index | Blender material / FBX slot | Unreal MI | Master | Recolourable | Covers |
|---|---|---|---|---|---|
| 0 | `M_Flashbang_Paint` | `MI_Flashbang_Paint` (+ `_Base`) | `M_Fabric_Master`: **Metal From ORM ON**, Cloth Sheen off, Use Lettering off, Specular Strength 0.5, Specular From ORM Alpha off | **Yes: `01 Colour > Colour`**, default the reference olive (from the generator) | The upper sleeve and body paint, their chipped edges and the hole walls |
| 1 | `M_Flashbang_Steel` | `MI_Flashbang_Steel` (+ `_Base`) | `M_Steel_Master` | No (optional `Steel Tint`; white = as shipped) | Collar, fuze housing, hinge, boss, base cap, lever, ring, pin, and the **brass inner tube** (a metal; its colour is in BC) |

- **Metal From ORM is already in the master.** It is a static switch, default OFF, added 2026-09-26/27. It does
  exactly what the flashbang needs, so **no master or graph change is needed**:
  - BaseColor = lerp(tinted paint, baked BC, max(ORM.B, saturate((lum(BC) − 0.2) × 5)));
  - Metallic = ORM.B.
  - The olive recolours; chips keep their bare steel colour and stay metallic.
- The part meshes: `SM_Flashbang_Body` has both slots in the same order. `SM_Flashbang_PullRing` and
  `SM_Flashbang_Lever` have one slot, index 0 = `M_Flashbang_Steel`.

### 9.2 Gates that protect the recolour (build, on the shipped maps)

- **Dielectric paint texels:** linear BC luminance < **0.18**. Above 0.2 the master's keep-luminance rule would
  freeze them at the baked colour. Pale dust or scuffs on the paint must stay under it, or be metallic chips.
- **ORM.B on paint islands** is bimodal: 0 on paint and 1 on chips, with ≤ 2 % of texels in between (the edge
  anti-aliasing). The guideline is no partial metallic on paint.
- **Detail16 covers paint texels only.** `derive_constants.fabric_part` counts "covered" texels as `d16 != fill`.
  - Chip texels and Steel islands are set to the fill value, so the default Colour is the **paint** mean.
  - The fill must also be mip-neutral near chips. Finalise checks how the sheath did this (its generator is under
    `maps/`) and gates that `Colour` is within 1 % of the paint-only mean.
- **Default look:** at the default Colour, Detail × tint equals BC at every mip (smoke bomb parity method).

### 9.3 Who writes what (shared-materials rule)

| Step | Who | Lock |
|---|---|---|
| Detail, Detail16 and `recolour_maps.json`, written by the build's `stage_recolour` exactly as `build_fan.py` does (`recolour_common` loaded read-only, v1 fields over every texel) | Build | Asset lock `Flashbang` only |
| `Scripts/unreal/materials/maps/derive_constants_flashbang.py`: a copy of the fan's wrapper; it imports `derive_constants`, which is **never edited**, since other items record its sha256 | **Finalise** | `np_lock.py claim flashbang-chat` |
| `material_spec.json`: items `Flashbang`, `Flashbang_Body`, `Flashbang_PullRing` and `Flashbang_Lever`; spec `build.recolour_maps` and `build.recolour_constants` entries for group `Flashbang` | **Finalise** | Same lock |
| Build: `NP_OWNER=flashbang-chat bash Scripts/unreal/materials/run_build.sh flashbang_0927 ...`, then verify (dependencies, slots, flags, recolour stress), then release the lock | **Finalise** | Same lock |

**Shared MIs across four meshes.** `np_spec.py` keys instances by name and stores one `slot` per leaf.
- Before building, Finalise runs `np_preflight.py` and a dry `np_spec` resolve with the four items all naming
  `MI_Flashbang_Paint` and `MI_Flashbang_Steel`.
- If that trips a check, make the smallest `np_spec` change (a leaf may be bound by several slots), under the lock
  and with preflight.
- **Do not fall back to one MI per mesh:** a buyer recolouring the grenade would then have to edit up to four
  instances.
- `verify_dependencies` allows each mesh the textures of its own slots. All four use `Textures/Flashbang/*`, so
  this passes.

`Exports/Flashbang/MATERIALS_README.md` follows `Exports/SmokeBomb/MATERIALS_README.md`: one recolourable part (Paint),
the shipped hex, Lightest Colour, the 3-step recolour, and the note that steel takes Steel Tint only.

---

## 10. How the smoke bomb was built and verified (the conventions to copy)

### 10.1 Build: `Scripts/props/build_smoke_bomb.py`

- Stages `mesh, textures, save, qa, export, render, report`. `--quick` and `--dev-dir` are for iteration; the
  shipped build runs with neither. Every report number is measured on what was built.
- **Pure-Python spec module** (`props_lib/smokebomb_spec.py`): a dataclass holding the size, mass, texture sizes,
  `SocketDef(name, position_mm, rotation_deg, use)` and `lod_screen_sizes()` via `props_lib.spec`. The Blender
  build, calculators and the Unreal verifier read the same object.
- `pipeline.helpers.make_lod_group` / `make_socket`, `pipeline.qa_check.qa_check` and `pipeline.export_fbx.export_fbx`
  (`kind="static"`, `lod_screen_sizes=` passed). The sidecar is written by the exporter and then given a `material`
  block (the shading contract).
- Frozen-asset hashes are checked at the start and the end.
- A deny-list of names, from `props_lib.spec`.
- **Renders only from the baked maps:** side_by_side, reference_view, crops, hero, raking, top, back, wire, lods,
  lod_switch, and a **1600 x 900 line sheet** (name, size, mass, LODs, maps).
- Report JSON in `WorkFiles/smokebomb/smokebomb_report.json`, and `SMOKEBOMB_REPORT.md`.

**Gates (30):**
- qa_check 66 / 66;
- LOD bands descending;
- UVs collapsed, mirrored, outside 0-1, and padding;
- hull contains every LOD;
- socket count;
- power of two and no colour chunks;
- Detail full range;
- frozen assets;
- no franchise strings;
- LOD deviation < 1 px at the switch;
- no triangle Unreal would drop;
- the fidelity gates.

### 10.2 Unreal: `WorkFiles/smokebomb/UnrealCheck_fp/run_unreal_checks.sh`

Eight steps, **each in a fresh process, one commandlet at a time.** The guard refuses only when an
`UnrealEditor-Cmd` is running; the user's DemoGame editors are left alone.

1. Blender FBX counts.
2. Pass 1: import with LODs ON and apply the sidecar.
3. Props texture import (`props_lib/ue_import_textures.py`, with the INTENT table).
4. Fresh texture verify.
5. Pass 2: reload and gates.
6. Pass 3: Unreal FBX export.
7. Blender round trip.
8. UV1 overlap.

19 gates:
- LOD triangle counts, with an exact round trip;
- collision hull count;
- sockets at scale 1, equal to the sidecar;
- screen sizes;
- UV1 with 0 overlap on every LOD;
- slot count;
- Nanite off;
- texture flags;
- byte hashes of the FBX and sidecar.

A new content path is used per run (`/Game/PropsCheck/SmokeBomb_FP_0925c`).

### 10.3 Regression, backup, materials

- `WorkFiles/smokebomb/regression/compare_post_smoke_bomb.py` and a `post_smoke_bomb/` snapshot (SHA256SUMS).
- `Backups/SmokeBomb_<date>/`.
- The pack MI (`MI_SmokeBomb_Cloth`) was built **afterwards** by the materials workflow through `run_build.sh`.

### 10.4 The flashbang equivalents

| Kind | Path |
|---|---|
| Build | `Scripts/props/build_flashbang.py` (same stages, plus a `parts` split before export) |
| Modules | `props_lib/flashbang_spec.py` (pure Python: dimensions from the Study, `SocketDef`s with the **rules** of section 4, budgets, masses, texture sizes), `flashbang_geom.py`, `flashbang_paint.py` (wear and bakes), `flashbang_look.py` (renders in the reference's style, the preview graph that mirrors the two masters), `flashbang_metrics.py` |
| Outputs | `Assets/Flashbang.blend` (packed); `Exports/Flashbang/` holds `SM_Flashbang.fbx`, `SM_Flashbang_Body.fbx`, `SM_Flashbang_PullRing.fbx`, `SM_Flashbang_Lever.fbx`, a `.sockets.json` for each, `Textures/` (+ `Recolour/`), `README.md` and `MATERIALS_README.md`; `Renders/Flashbang/` |
| Unreal harness | `WorkFiles/flashbang/UnrealCheck/`, a copy of `UnrealCheck_fp` with the prefix `fbu_`. Content path `/Game/PropsCheck/Flashbang_<run>`. |
| Regression | `WorkFiles/flashbang/regression/pre_flashbang/` and `post_flashbang/` |

---

## 11. Verification checklist (on top of the smoke bomb's gates)

1. **Scale:** the painted body diameter in the built LOD0 is 44.0 ± 0.1 mm. The overall height and every stack Z in
   section 1.1 are within the Study's tolerance after its refit. The scale constant is reported.
2. **Sockets:**
   - each is equal to its rule on the built parts (≤ 0.01 mm, ≤ 0.05°);
   - in Unreal, all 5 sockets are equal to the sidecar, at scale 1, on **both** the assembled mesh and the body;
   - `Pin` has yaw 90 if the pin pulls toward -Y.
3. **Assembly identity (new):** in Unreal, the body with PullRing at `Pin` and Lever at `LeverHinge` (identity) gives
   world-space LOD0 vertices equal to `SM_Flashbang` LOD0's ring, pin and lever vertices within 0.01 mm. Do it in
   Blender too, before export.
4. **Lever sign (new):** in Unreal, apply +100° pitch to the attached lever. The lever tip's X in the socket frame
   increases, and its bounds leave the body's `_02` hull outward.
5. **Collision:** 3 hulls on the assembled mesh, 2 on the body, 1 on each part. The union containment gate is from
   section 6.1. The ring's protrusion is reported.
6. **Centre of mass:** the build reports the weighted and hull centres of mass and their difference. `Throw` equals
   the weighted one.
7. **Budget:**
   - LOD0 ≤ 6,000 (target 5,500);
   - triangles strictly descend in all four meshes;
   - Body + PullRing + Lever triangles equal the assembled total at every LOD.
8. **Maps:**
   - 2048, power of two, full mips;
   - BC sRGB, ORM and N linear, N DirectX;
   - the section 9.2 recolour gates;
   - renders only from the baked maps.
9. **Materials** (Finalise): the MIs compile, 0 WorldGridMaterial, dependencies are own-item only, and the recolour
   stress passes (default plus 9 colours, including white, red, blue and black) with the pack's thresholds.
10. **Frozen assets.**
    - `WorkFiles/materials/survey/check_exports_frozen.sh` still reads the **older** baselines:
      - shuriken `post_kunai_plain`;
      - paper bomb `paused_2026-09-21`;
      - the 2026-09-26 survey.
    - The current baselines are:
      - `WorkFiles/shuriken/regression/post_blade_section/` (kunai, 2026-09-27);
      - `WorkFiles/paperbomb/regression/` (exact match);
      - `WorkFiles/fan/regression/post_fan/`.
      The fan and the black hat are not all covered by the script.
    - So at the **start** of the build, snapshot the SHA256 of every file under `Exports/{Shuriken,SmokeBomb,BlackHat,PaperBomb,Fan}`
      and `Scripts/unreal/materials/**` into `WorkFiles/flashbang/regression/pre_flashbang/SHA256SUMS.txt`.
    - Prove identity at the end, except the materials files Finalise changed under the lock.
    - Run `check_exports_frozen.sh` as well, and explain any DIFF against the current baselines.

---

## 12. Open points for the Study / user

1. **Study:**
   - the holes per row (6 read here) and their exact size;
   - the pin axis direction;
   - the azimuths of views 1-4;
   - the lever's stand-off from the sleeve;
   - the base cap's notch count;
   - the hinge location;
   - the ring's real diameter (about 48 mm here, larger than a real ring; follow the reference).
2. **User:**
   - The overall height comes out at about 170 mm for a real-world 44 mm grip. Say if a shorter item is preferred
     (D = 40 mm gives 154 mm). It is one constant, and it must be changed before the bake.
   - Whether 4096 BC/N is wanted is decided by the close-up 4 rule in section 8.
3. **Finalise:** whether `np_spec` needs its small shared-MI change (section 9.3). The sidecar's extra keys are
   already confirmed safe (section 4).
