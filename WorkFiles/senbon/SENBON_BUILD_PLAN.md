# SM_Senbon: game and tech build plan

**Date:** 2026-10-03. **Role:** game and tech study (workflow `senbon`). Nothing was downloaded and no asset was opened
for writing. The numbers come from files already on disk and from one stdlib calculator written for this plan:
`WorkFiles/senbon/tech/senbon_tech_calc.py`, which writes `senbon_tech_calc.json` beside itself. Run it with
`py -3 -B WorkFiles/senbon/tech/senbon_tech_calc.py`.

**Read first:**
- `CLAUDE.md`, `ASSET_GUIDELINES.md` and `FAB_ASSET_STUDY.md`, sections 3.2-3.5;
- `References/Shuriken/SHURIKEN_STUDY.md`, sections 2.5, 4 and 5;
- `WorkFiles/shuriken/spike_report.json` (the bo-shuriken, library 3.10.1);
- `WorkFiles/kunai/KUNAI_PLAIN_REPORT.md`;
- `WorkFiles/flashbang/FLASHBANG_BUILD_PLAN.md` and `FLASHBANG_REPORT.md`;
- `WorkFiles/materials/MATERIALS_REPORT.md`, `Scripts/unreal/materials/README.md` and `material_spec.json`;
- `Scripts/props/props_lib/spec.py` and `ue_import_textures.py`;
- `Scripts/pipeline/helpers.py` and `ue_import_sockets.py`.

**Who owns what.** The Study owns the design: section, diameter, length, the point and any tail feature. Its
dimensioned design sheet is the reference. This plan sets the frame, sockets, collision, budgets, LOD and
distance behaviour, maps, material slots, projectile and embed conventions, and the gates. Where a number here
depends on the design, it is given as a **rule**, with worked values for a typical needle (round, about 2.5 mm,
150 mm). The build computes the real values from its own geometry and writes them to the report and the sidecar.

---

## 0. Decisions at a glance

| Topic | Decision |
|---|---|
| Frame | Metres, unit scale 1, transforms applied. **Long axis X, +X toward the point** (the spike's and kunai's convention, so one Blueprint drives the pack). The UV seam and any asymmetric feature sit on -Z. Export -Y forward / Z up (the house pair). |
| Pivot | **The centre of mass** of the finished LOD0 (steel, uniform density). It is the pack rule for the spike and the kunai. The other frames are sockets. |
| Sockets | `Grip`, `Tip`, `Trail` (the tail; the pack's name for it), `Throw` (= the pivot) and `Embed` (the tip minus the default embed depth). All are Empties plus the sidecar (section 3). |
| Collision | **One** UCX convex hull, `UCX_SM_Senbon_LOD0_00`: a circumscribed octagonal "capsule" (prism plus point cone), at most 32 vertices, containing every LOD with 0.0 mm outside (section 4). |
| Triangles | Analytic LODs, nothing decimated and nothing padded. LOD0 target **≤ 400** (cap 1,000, used only if the Study adds a tail feature), LOD1 about 80-100, LOD2 about 30-40. For a plain round needle: 12 / 8 / 6 sides gives **238 / 94 / 34** (section 5). |
| Screen sizes | The pack rule: 1.0 / 0.10 / 0.035 × (Unreal bounds radius / 50 mm). A 150 mm needle gets **1.0 / 0.15 / 0.0525**, switching at **0.89 m and 2.54 m** like every other pack item. |
| Distance | The shaft drops under 1 px at about 0.96 × D(mm) metres at 1080p, so **2.4 m for a 2.5 mm needle**. Beyond that, the mesh is not what makes the needle visible: the `Trail` VFX and a tip glint are. Do not fatten the geometry and do not add a minimum-width hack to the shared master (section 6). |
| Normal map | **Not needed for the form.** The round form is geometry with analytic normals. Ship a small N anyway, carrying only the surface marks the Study specifies, for the pack's three-map contract (section 7). |
| Textures | **2048 × 256** BC / ORM / N (about 1.4 MiB with mips). That is the spike's bar density (about 135 px/cm) on an analytic unroll. Power of two, full mips, renders from the baked maps only. Variants stack in V, up to 2048 × 512. |
| Material | **One slot**: `M_Senbon_Steel` → `MI_Senbon_Steel` (+ `_Base`) on **`M_Steel_Master`**. Not recolourable; the only buyer control is `Steel Tint`. A fabric slot is added only if the Study's design has a cord, flight or wrap. |
| Master change | **Recommended (finalise, under the lock):** add *Used with Niagara Mesh Particles* to `M_Steel_Master`. A cooked game would otherwise draw Niagara-spawned needles with the default material. The fan's skeletal-mesh flag is the precedent (section 8.3). |
| Projectile | `ProjectileMovement` on a small sphere root **at the tip**, with Rotation Follows Velocity and the mesh offset by -`Tip`. Volleys use Niagara mesh particles (Facing Mode Velocity, +X), with gameplay hits from traces. Spent needles become HISM instances (section 9). |
| Embed | Along the **incoming velocity**, not the surface normal. Depth by surface, 15 mm default. No stick on stone or metal, or above 70° incidence. Attach to the hit bone on characters (section 9.4). |
| Mass | The finished LOD0 volume × 7.85 g/cm³ (a 150 mm × 2.5 mm needle is about 5 g). It goes in the sidecar and README as a Mass override. CCD and damping apply only to dropped needles that simulate physics. |
| Verification | The spike, kunai and flashbang chain, plus four senbon gates: the Tip socket equals the apex, Unreal bounds equal the computed bounds, cross-LOD UVs are analytic, and a thin-geometry distance render (section 11). |

---

## 1. What the senbon has to be, technically (inputs for the Study)

### 1.1 Distinct from the spike, in the same family

The pack's spike (`SM_Shuriken_Spike`) is a **150 mm × 6 mm square** bar with a 25 mm four-facet point and a 20 mm
tail taper. It weighs 35.3 g, has 92 / 60 / 28 triangles and uses 2048 × 512 maps. To read as a different object at
game distance, the senbon has to differ in what survives on screen:

| Property | Spike | Senbon: technical guidance |
|---|---|---|
| Section | Square, with 0.3 mm arris rounds | **Round** (or octagonal, if the Study's history supports it). Unlike a square, a round section shows one continuous highlight line along its length. |
| Width | 6 mm | **About 2-3.5 mm**: at most 0.6 × the spike, so the difference reads even where both are only a few px wide. |
| Point | 25 mm four-facet pyramid | A long conical or ogive taper. Its length is the Study's call; 25-40 mm is typical of needle forms. |
| Mass | 35 g | About 3-9 g (table 1.3). |
| Finish | Pack blackened coat, bright ground point | **The same recipe**: satin blackened coat, metallic 1.0, roughness about 0.34, with the point ground bright over its last 10 mm (the spike's `style_on_a_bar`). This is what makes it part of the family. |

### 1.2 Readability limits the Study should know (from `senbon_tech_calc.json`)

The shaft's on-screen width in px is about 960 × D(mm) / d(mm) at 1080p and 90° horizontal FOV. It doubles at 4K
and is about 1.43 × at 70° FOV.

| Shaft D | 0.3 m (first person) | 0.89 m (LOD1 switch) | 2.54 m (LOD2 switch) | 5 m | 10 m | Under 1 px from (1080p / 4K) |
|---|---|---|---|---|---|---|
| 1.5 mm | 4.8 px | 1.6 | 0.57 | 0.29 | 0.14 | 1.44 m / 2.88 m |
| 2.0 mm | 6.4 | 2.2 | 0.76 | 0.38 | 0.19 | 1.92 / 3.84 |
| 2.5 mm | 8.0 | 2.7 | 0.94 | 0.48 | 0.24 | 2.40 / 4.80 |
| 3.0 mm | 9.6 | 3.2 | 1.13 | 0.58 | 0.29 | 2.88 / 5.76 |
| 4.0 mm | 12.8 | 4.3 | 1.51 | 0.77 | 0.38 | 3.84 / 7.68 |

- **Under about 2 mm**, a held needle in first person is a 4-6 px line, and in third person (2-3 m) it is gone.
  That is acceptable if it is the design, but the Study should know it.
- **At any diameter**, a needle thrown in a 5-15 m duel is sub-pixel. The design cannot fix that; section 6 does.

### 1.3 Mass and balance (steel 7.85 g/cm³, cylinder plus conical point)

| Length × D | 25 mm point | 40 mm point | Centre of mass behind the middle |
|---|---|---|---|
| 150 × 2.0 mm | 3.3 g | 3.0 g | 8.2 / 13.0 mm |
| 150 × 2.5 mm | 5.1 g | 4.8 g | 8.2 / 13.0 mm |
| 150 × 3.0 mm | 7.4 g | 6.8 g | 8.2 / 13.0 mm |
| 180 × 2.5 mm | 6.3 g | 5.9 g | 8.2 / 13.0 mm |
| 180 × 3.0 mm | 9.1 g | 8.5 g | 8.2 / 13.0 mm |

- A plain needle is **tail-heavy**: the point removes steel ahead of the middle.
- That suits the direct throw (jiki-daho, point first, no spin), which the shuriken study records for bar types
  (`SHURIKEN_STUDY.md` 4, Throwing).
- If the Study's design has a heavier tail feature, the centre of mass moves further back. The pivot follows it
  (section 2).

---

## 2. Frame and pivot

- **Units and axes:** metres, unit scale 1, transforms applied (a `qa_check` gate). Long axis X, +X toward the
  point.
  - A round needle has no up. +Z is defined as the side facing away from the UV seam: the seam lies on -Z, and so
    does any asymmetric feature (a hole, a flat or a mark), unless the Study places it elsewhere.
  - In Unreal: X_ue = x, Y_ue = -y, Z_ue = z, in cm.
- **Pivot = the centre of mass by volume of the finished LOD0.** Build it like the spike's bar generator: author
  the needle shifted by its own measured centroid, so the object origin **is** the centre of mass to 1e-6 mm.
  Report the centroid of each LOD; LOD1 and LOD2 may differ by a few µm.
  - **Why not the tip?** A tip pivot would make placing an embedded needle a one-liner. But Rotation Follows
    Velocity, Niagara's velocity alignment and physics all rotate about the pivot, and a tip pivot makes a dropped
    or ricocheting needle swing about its point.
  - The pack has one convention for bars: the pivot is the centre of mass, and every other frame is a socket.
    `Tip` and `Embed` give the tip frame exactly (section 9).
- **Unreal's bounds sphere is centred on the bounding-box centre, not the pivot.** Its radius is about half the
  length: sqrt((L/2)² + r²). The screen sizes use that radius, the spike's `unreal_bounds_sphere_radius_mm` lesson.
  The radius measured from the origin is about 8-13 mm larger and is **not** the one to use.

---

## 3. Sockets (Empties via `pipeline.helpers.make_socket`, shipped through the sidecar)

All sockets go on `SM_Senbon_LOD0`. **+X points toward the tip on every socket**, and +Z is the mesh's +Z.
`make_socket` takes the orientation wanted in Unreal, in the parent's Blender space, and adds the 180° Y correction
itself. Call `view_layer.update()` before `socket_record`; this was a lesson from the flashbang.

| Socket | Rule on the built LOD0 (the build computes it) | Worked value (150 × 2.5 mm, 25 mm point, centre of mass 8.2 mm behind the middle) | Use |
|---|---|---|---|
| `Grip` | On the axis, **40 mm from the butt** (ESTIMATE, the spike's grip distance) | x = -26.8 mm → (-2.68, 0, 0) cm | Hand attach (inverse of the socket). One needle **between the index and middle fingers**, butt in the palm and point past the fingertips, crosses the fingers at about 30-50 mm from the butt. The palm-laid bar grip (`SHURIKEN_STUDY.md` 4) lands at the same place. If the Study's grip differs, it changes this one number in the spec. |
| `Tip` | At the apex: the LOD0 vertex with the largest x, or the centre of the tip flat | x = +83.2 mm | Impact FX, the embed computation, and the projectile root (section 9.1) |
| `Trail` | On the axis at the butt face, its smallest x | x = -66.8 mm | Ribbon or streak VFX, a thread or cord attach. **The pack's name for the tail socket** (the spike and kunai both ship `Trail`; the brief's "Tail" is this socket). One shared name lets one trail Blueprint serve every form. |
| `Throw` | At the origin, identity | (0, 0, 0) | Launch point and spin centre. It equals the pivot, and ships so that Blueprints written against the flashbang's `Throw` work unchanged. |
| `Embed` | On the axis at `Tip` minus the default embed depth (15 mm) | x = +68.2 mm | Attach so that `Embed` sits on the surface hit point (section 9.4). The depth by surface type lives in the sidecar's `embed` block. |

- Every socket is at relative scale 1, imported from the sidecar by `ue_import_sockets.py` (the LodGroup FBX drops
  FBX sockets).
- **Sidecar extra keys**, which are documentation only: `ue_import_sockets.apply_sidecar` reads only `sockets` and
  `lod_screen_sizes` (checked in the flashbang plan, section 4).
  - `mass_kg`;
  - `centre_of_mass_mm` (0, 0, 0);
  - `hull_com_offset_cm` (section 4.2);
  - `embed`: `{default_depth_mm: 15, by_surface_mm: {...}, max_incidence_deg: 70}`;
  - `throw`: `{method: "direct, point first", rotation_follows_velocity: true}`;
  - `material`: the shading contract, as the smoke bomb and flashbang have.
- **Hand sockets are the character's, not the mesh's.** For a fan of needles between the fingers, add skeleton
  sockets on `hand_r`, for example `Needle_R_1..3` between each finger pair at about 18-20 mm pitch, and attach each
  needle with the inverse of its `Grip`. These are for the README, not this build.

---

## 4. Collision and physics

### 4.1 One convex hull, capsule-like

- **Shape.** An octagonal prism **circumscribed** about the shaft, with r_hull = r_max / cos(22.5°) = 1.0824 × r_max.
  It runs from the butt face to the start of the point taper, then closes to a single apex at the tip (or a 4-vertex
  flat if the tip has a flat).
  - That is 8 + 8 + 1 = **17 vertices and 30 triangles**, within `make_ucx_hull`'s cap of 32 vertices.
  - If the Study's needle has a wider tail feature, size the octagon to the largest radius over the shaft, or add
    one more ring of 8 (25 vertices).
- **Author it analytically**, as the spike's `author_bar_hull` did. Do not take a hull of the LOD0: a hull of a
  12-gon would give 25+ vertices for no benefit.
- **Name:** `UCX_SM_Senbon_LOD0_00`. `make_lod_group` renames LOD0 together with its UCX child, so the name keys to
  the LOD0 node.
- **Gates** (the spike's):
  - every vertex of every LOD is inside, with the worst at ≤ 0.0 mm outside;
  - hull volume / LOD0 volume is reported (about 1.06 for a circumscribed octagon over a round shaft:
    8 tan(22.5°) / π = 1.055);
  - in Unreal, exactly one convex element;
  - the Unreal FBX round trip gives the same hull vertex and face counts as the shipped one.
- **Why not `UCP_`, a true capsule primitive?** `ASSET_GUIDELINES.md` lists it but the pipeline has never measured
  it. `qa_check` requires a `UCX_` on every `SM_`, and the guidelines require any unmeasured helper claim to be
  re-run against a matched control before use. A 17-vertex convex is cheap. Revisit only if dropped needles jitter
  in Chaos (4.3).
- **Never** set Use Complex As Simple on a simulating needle.

### 4.2 Mass and centre of mass

- **Mass override:** the finished LOD0 volume × 7.85 g/cm³, stated to 0.1 g. This is the pack rule since the
  spike's knife-grind pass: the override is the finished mass, while the mass *gate* is evaluated on the un-ground
  outline against the Study's target, ±2 g or ±10 %, whichever is smaller for a needle this light.
  - It is not carried by the FBX. Set it on the component's Body Instance, and state it in the sidecar `mass_kg`
    and the README.
- **The hull's centre differs from the mesh's.**
  - Unreal derives the centre of mass from the hull at uniform density.
  - The hull is the needle's own profile with a scaled section (octagon over circle), so on a plain needle the
    hull centroid lands within about 0.1 mm of the mesh centroid. A tail feature or an ogive point moves it
    further.
  - The build reports the difference as `hull_com_offset_cm`. If it is over 1 mm, the README tells buyers to set
    **Center Of Mass Offset** to it, as the kunai README does with (+3.06, 0, 0) cm.

### 4.3 When the needle simulates (drops, ricochets, pickups only)

- A 3-9 g, 2-3 mm body is near the small end of what a physics engine handles well. It rolls on any slope, and at
  ricochet speeds it crosses its own diameter many times per frame.
- Use **CCD on**, **Angular Damping about 0.5-1.0** (it stops the endless roll on a round section; tune in game)
  and a small Linear Damping.
- **In flight a needle never simulates.** `ProjectileMovement` sweeps its root (section 9.1), so tunnelling is
  impossible however thin the needle is.

---

## 5. Triangle budget and LODs (a thin object)

### 5.1 Where the triangles go

- On a needle, the silhouette is two parallel lines and a point. As on the spike ("at 1:25 the silhouette is nearly
  all straight line, so the triangles belong at the point"):
  - **the shaft is single planar strips** from the butt ring to the taper start;
  - the rings sit only where the profile changes: the butt edge, the taper start, the stations of a curved (ogive)
    taper, and the tip.
- **Facet count from the silhouette error.** An n-gon's worst deviation from the circle is r (1 - cos(π/n)). In px,
  for r = 1.25 mm (D 2.5):

| Sides | Inspect 4K at 0.2 m | First person 1080p at 0.3 m | First person 4K at 0.3 m | LOD1 switch, 4K | LOD2 switch, 4K |
|---|---|---|---|---|---|
| 6 | 1.61 px | 0.54 | 1.07 | 0.36 | **0.13** |
| 8 | 0.91 | 0.30 | 0.61 | **0.21** | 0.07 |
| 12 | **0.41** | 0.14 | 0.27 | 0.09 | 0.03 |
| 16 | 0.23 | 0.08 | 0.15 | 0.05 | 0.02 |

  - LOD0 at **12 sides** is sub-pixel even in a 4K inspect at 0.2 m.
  - 16 sides is the ceiling and is used only if the Study's diameter is 3 mm or more and a 4K inspect view
    matters: r = 1.5 mm with 12 sides gives 0.49 px.
  - LOD1 at **8 sides** and LOD2 at **6 sides** stay within 0.21 px at their switches, even at 4K.
  - A 4-sided LOD2 would still pass (0.28 px at 4K), but it saves 12 triangles and makes the width flicker
    ×1.41 as the needle rolls. **Use 6.**

### 5.2 Budgets (closed mesh: shaft quads, a fan to the apex, an n-gon butt cap)

| LOD | Sides | Stations | Triangles (plain needle) | What changes |
|---|---|---|---|---|
| LOD0 | 12 | about 10 (butt chamfer 2, shaft 1, taper 4-6, tip) | **238** (308 with a 0.15 mm tip flat) | The full profile: butt edge chamfer, taper stations, tip. Analytic radial normals. |
| LOD1 | 8 | about 6 (taper 2-3) | **94** | Half the taper stations, no butt chamfer |
| LOD2 | 6 | 3 (butt, taper start, tip) | **34** | A straight cone point |

- **Target ≤ 400 at LOD0 and cap 1,000.** Pass `--budget 1000` to `qa_check`. Of the house prop band (1,000-5,000),
  the spike uses 92 triangles and the senbon should be similar: **nothing is padded**, the spike's `why_so_few`
  rule.
  - A tail feature, if the Study adds one (a ring, an eye, a thread wrap modelled as geometry, a flight), takes
    its triangles from the cap and is reported per part.
- **LODs strictly descend** in Blender and in Unreal, and the counts must match exactly in the engine.
- **Topology quality.** Long sliver strips are legitimate (the spike's are at aspect ratio up to about 920).
  Report the smallest triangle angle and aspect ratio; no edge may be under `qa_check`'s 1 µm, and no area under
  1e-12 m².
  - **Unreal keeps every triangle** with Remove Degenerates on, verified by the exact triangle-count gate.
  - A 0.15 mm tip flat on 12 sides has 0.04 mm edges, which is about 200 times Unreal's same-point threshold.
- **Normals:**
  - analytic radial custom normals on the shaft;
  - normals tilted by the cone half-angle on the taper;
  - a hard edge at the butt face.
  - **The apex** must not pinch: either use per-corner normals of the cone at a single apex vertex, or use the
    pack's 0.15 mm tip flat (tip radius 0.075 mm, the stars' and the spike's). Gate it with the spike's shading
    check: max deviation of the shaded normal from the analytic normal, reported in degrees.
- **Screen sizes** use the pack rule, scaled by Unreal's bounds radius:

| Length | Bounds radius | Screen sizes | Switch |
|---|---|---|---|
| 120 mm | 60.0 mm | 1.0 / 0.12 / 0.042 | 0.89 / 2.54 m |
| 150 mm | 75.0 mm | 1.0 / 0.15 / 0.0525 | 0.89 / 2.54 m |
| 180 mm | 90.0 mm | 1.0 / 0.18 / 0.063 | 0.89 / 2.54 m |

  - Use `props_lib.spec.scaled_lod_screen_sizes(R)`; they travel in the sidecar.
  - **Why keep the pack rule, when the needle's width alone would allow switching closer?** Bounds-sphere screen
    size is driven by the *length*, so it overstates a needle's on-screen weight. But the LODs are already tiny,
    so switching earlier saves nothing measurable. Keeping the pack's distances keeps one rule for the README and
    one gate set.
  - **Gate** (the smoke bomb's F-gate): two-sided surface deviation p99 < 1 px at each switch. Expect about 0.1 px.
- **Nanite off.** The mesh is far too simple, Fab refuses "simplistic" meshes tagged Nanite, and the pack is
  classic-LOD throughout.
- **No LOD3.** At 34 triangles, LOD2 costs nothing more to draw. Distant cost is per *instance* (draws and quad
  overdraw on sub-pixel triangles), and it is controlled by cull distance (6.3), not by more LODs.

---

## 6. Thin geometry at distance: minimum width, flicker, what to do

### 6.1 What happens

- Past the 1-px distance (1.2 above: about 2.4 m at 1080p for a 2.5 mm shaft), the shaft covers only part of each
  pixel. The rasteriser then keeps or drops whole pixels per frame, and the needle **breaks into dashes and
  shimmers**, worse while it moves or the camera jitters.
  - TSR (UE 5.8's default) reconstructs thin static lines well over several frames.
  - TSR does less for a fast-moving needle, because there is no stable history.
- A round polished shaft also concentrates its specular highlight into a line narrower than the shaft. When the
  shaft is sub-pixel, that line sparkles: **specular aliasing**.

### 6.2 What we do and do not do

| Option | Decision | Why |
|---|---|---|
| Fatten the geometry, or a vertex-shader "minimum pixel width" (WPO by distance) | **No** | The first invents a thicker needle than the design sheet (the user's to-the-T bar). The second needs a graph change to the shared `M_Steel_Master` and moves every pack item's material onto a WPO path. |
| Rely on TSR for static and slow needles (held, embedded, on a table) | **Yes** | Measured in the distance render gate (11.3). |
| **VFX carries in-flight readability:** a thin streak or ribbon from `Trail` and a small glint at `Tip`, sized in screen space | **Yes, as game guidance** | Bullet tracers solve the same problem the same way. The asset ships the sockets, the README describes the setup, and the VFX itself is not part of this build (open point 13.2). |
| Cull distance on embedded and dropped needles (6.3) | **Yes** | Once sub-pixel, a needle adds only shimmer and draw cost. |
| Specular-aliasing controls: the material's *Normal Curvature to Roughness*, or a composite texture | **Not now; measure first** | The composite (Toksvig) path works from normal-map variance, which an almost flat N does not have. *Normal Curvature to Roughness* is a master-level property; its effect in the deferred path is to be tested, and turning it on changes every steel item. **Only if** the distance render shows the senbon sparkling clearly more than the spike at equal on-screen width: in a throwaway project copy, test it, or a +0.05 roughness bias baked into the senbon's own ORM.G (no master change), and bring the result to the user. |
| Shadows | Cast Shadow **off** on in-flight needles (a few frames, invisible), **on** for held and embedded ones | The contact shadow is the main cue that a needle is stuck in a surface. |
| Distance fields / Lumen | Leave the project defaults. Optionally turn Affect Distance Field Lighting off on needle components | A 2-3 mm object is below any distance-field voxel and contributes nothing. |

### 6.3 Cull distances (README guidance, with defaults computed for the shipped D)

- **Embedded and dropped needles** in HISM: InstanceStartCullDistance / InstanceEndCullDistance about **10 / 12 m**.
  At 10 m, a 2.5 mm shaft is 0.24 px at 1080p and 0.48 px at 4K. The opaque pop is invisible below half a pixel.
  - Single actors: Max Draw Distance 1,200 cm, or a Cull Distance Volume entry for the needle's size bucket.
- **In-flight needles:** no cull. The trail VFX is the visible part.

---

## 7. Normal map, textures and UVs

### 7.1 Does a needle need a normal map?

**Not for its form.** At 0.3 m in first person a 2.5 mm shaft is 8 px wide at 1080p. Its roundness, taper and point
are geometry, shaded by analytic normals, so a normal map would add nothing there. The places an N **does** show:

- **fine axial grinding or polish lines** along the shaft, which catch the light as the needle turns in an inspect
  view;
- **the relief of a tail feature**, if the Study draws one: a thread wrap, a knurl or stamped marks.

**Decision: ship `T_Senbon_N`, small and nearly flat**, holding only what the Study's sheet shows.
- Reasons:
  1. The pack contract is BC / ORM / N for every steel item. `np_spec` texture kinds, `ue_import_textures` and the
     buyer README all expect three maps.
  2. Falling back to `Textures/Default`'s 8x8 flat normal works, but would make this the only shipped item whose
     MI depends on a default map.
  3. The cost at 2048 × 256 is about 0.7 MiB (BC5).
- **Gates:**
  - N carries no geometry: no baked bevels, no fake taper, no tip shading;
  - mean tilt is reported;
  - its mips are generated normally, so the 1.25 mm-radius surface cannot alias through the N at distance.
- The build also renders the first-person view with and without N and reports the difference. If it is under 1
  level p99, the README says the N is optional and `Normal Strength 0` is free.

### 7.2 Size, layout, density

- **Size: 2048 × 256** for one needle: BC (DXT1), ORM (Masks), N (BC5), about 1.4 MiB with mips in total.
  - The spike's maps are 2048 × 512, for four flat strips.
  - Non-square power-of-two maps import, mip and stream normally; the spike's are measured.
  - **No 4096**: the needle is 2048 texels long at 13.5 px/mm. For a length L the density is 2032 / L px/mm, so
    11.3 px/mm at 180 mm and 9.7 at 210 mm. That is still about ten times the guideline's first-person
    10.24 px/cm.
- **Layout (analytic, no packer, the spike and kunai rule):**
  - **One unrolled island** per needle: u along the axis, v the arc length around it (v ∝ angle × r(x)), with the
    seam on -Z.
    - The island narrows into the point, so texel density is the **same everywhere**, including the taper. The
      point gets no stretched texels.
    - Width at the shaft: π D × 13.5 px/mm, which is about 106 px for D 2.5.
  - The **butt cap** is its own small disc island beside the strip.
  - Borders 8 px and gaps 16 px (the 2K padding). Texels outside the islands and margin take the covered mean for
    BC and ORM, and a flat value for N (the spike's `unused_texel_fill`), so mips never pull black into the edge.
  - **The same UV function on every LOD**, so cross-LOD UV consistency is exact by construction (the kunai's
    `lod_uv` hook). Report the cross-LOD UV deviation in px; expect 0.
  - UV1 (lightmap) is generated at import (Generate Lightmap UVs ON, LightMapCoordinateIndex 1), with the spike's
    known gap stated in the README. A movable needle never uses it, but Fab requires it.
- **Variants** (if the Study defines more than one needle): one strip per variant stacked in V, sharing one atlas
  and one MI. 2048 × 512 holds up to three.
- **ORM:**
  - R is the **baked** Cycles AO. It will be about 1.0 on a bare needle; a constant is still forbidden.
  - G is roughness: the coat about 0.34, the ground point about 0.2-0.25, and the polished band.
  - B is metallic 1.0 everywhere (all steel).
  - PNG colour chunks are stripped from ORM and N; N is DirectX, with green flipped on write.
- **Unreal flags**, through `Scripts/props/props_lib/ue_import_textures.py` with no edit (it picks the kind from the
  `_BC` / `_ORM` / `_N` suffix; set `PROPS_TEXTURE_DIR=Exports/Senbon/Textures` and a new `PROPS_TEXTURE_DEST`):
  - BC: sRGB, Default;
  - ORM: sRGB **OFF**, **Masks** (a plain import decodes roughness 0.32 as 0.08 and the needle renders as a
    mirror);
  - N: Normalmap, Flip Green **OFF**.

---

## 8. Material slots and the pack colour system

### 8.1 One slot (plain needle)

| Index | Blender material / FBX slot | Unreal MI on the mesh | Base | Master | Recolourable |
|---|---|---|---|---|---|
| 0 | `M_Senbon_Steel` | `MI_Senbon_Steel` | `MaterialInstances/Base/MI_Senbon_Steel_Base` (every texture) | `M_Steel_Master` | **No.** `Steel Tint` only: white = as shipped, warm = bronze, cool = blued. Plus `Roughness Adjust` and `Normal Strength`. |

- `M_Steel_Master` is BaseColor = saturate(BC × Steel Tint), Metallic = ORM.B, Roughness = ORM.G + adjust,
  AO = ORM.R, Normal = MF_NormalStrength(N). It needs **no graph change** for a needle. It already has *Used with
  Instanced Static Meshes*, which HISM and ISM need.
- **A second slot only if the Study's design has a non-steel part** (a cord, flight or wrap): slot 1
  `M_Senbon_Wrap` on `M_Fabric_Master`, recolourable.
  - It follows the flashbang's chain exactly: the build's `stage_recolour` writes Detail16 and
    `recolour_maps.json`; the finaliser adds `maps/derive_constants_senbon.py`, a copy of the flashbang's wrapper
    (`derive_constants.py` itself is **never** edited); the recolour stress uses the default plus 9 colours.
  - Its UV island goes in **u 1..2**, as the kunai's wrap does, so no UV0 triangle overlaps another slot's and the
    generated UV1 stays clean.
- **Blender side.** A props build bakes its own procedural steel and renders from the baked maps, as
  `flashbang_look.py` mirrors the masters. **Do not import `Scripts/shuriken/shuriken_lib`**:
  - it is frozen;
  - other items' regressions hash it;
  - importing it writes `__pycache__` into a frozen folder.
  Copy the recipe values (coat, point polish, wear along the axis, specks damped on side views; the spike's
  `style_on_a_bar`), not the code.

### 8.2 `material_spec.json` entry (finalise, under the lock)

Item `Senbon`:
- mesh `SM_Senbon`, fbx `Exports/Senbon/SM_Senbon.fbx`, sidecar `Exports/Senbon/SM_Senbon.sockets.json`;
- one slot: `{index 0, slot_name M_Senbon_Steel, part Steel, instance MI_Senbon_Steel, master M_Steel_Master,
  recolourable false, textures {Base Colour Map, ORM Map, Normal Map → Exports/Senbon/Textures/T_Senbon_*},
  texture_kinds {BC, ORM_rgb, N}, size [2048, 256], params {}, base_instance MI_Senbon_Steel_Base}`. This is
  exactly the spike's entry shape;
- a `changes_v7_senbon` note.

`verify_dependencies` then allows the mesh only `Textures/Senbon/*` and the Default maps.

### 8.3 Recommended master addition: *Used with Niagara Mesh Particles*

- **Why.** Volleys of needles are the natural Niagara mesh-particle case (9.2). A material without the usage flag
  draws the **default material** on Niagara meshes in a cooked build. In the editor, it silently sets the flag
  itself, dirtying `M_Steel_Master`. The fan hit the same issue with *Used with Skeletal Mesh*.
- **How**, following the fan precedent:
  1. Take the lock: `py -3 -B Scripts/unreal/materials/np_lock.py claim senbon-wf`.
  2. Add `settings.used_with_niagara_mesh_particles: true` to `M_Steel_Master`, and teach `np_masters.py` and
     `np_dump.py` the key, as they learned `used_with_skeletal_mesh`.
     - First confirm the Python property name on a scratch material in a commandlet (`get_editor_property`).
  3. Run preflight, then `NP_OWNER=senbon-wf bash Scripts/unreal/materials/run_build.sh senbon_<date> ...`.
  4. **Prove the dump unchanged except the flag and the new Senbon instances.** Every other instance, function,
     mesh slot and texture flag must be identical, using the fan's `post_fan` comparison method.
  5. Release the lock.
- It adds a shader permutation only.
- If another owner holds the lock, wait. If the orchestrator prefers no master change in this run, ship without it
  and put the one-line fix in the README. It is the user's call.

---

## 9. Projectiles, volleys, instancing, embedding (README guidance and the frames the asset must provide)

### 9.1 One thrown needle (the 1v1 case)

- **Actor:**
  - **Root:** a `SphereComponent`, radius 0.5 cm, profile *Projectile*, placed **at the needle's tip**.
  - **Child:** `StaticMeshComponent` `SM_Senbon`, NoCollision, relative location = **-`Tip`**, so the mesh's
    tip sits on the root.
  - A Niagara trail attached at `Trail`.
- **`ProjectileMovement`:**
  - Rotation Follows Velocity ON, which rotates about the root, so the point leads;
  - no spin;
  - Initial Speed about 20-30 m/s (game tune; real throws are slower);
  - Gravity Scale tuned for game feel.
  - It **sweeps** the root every tick: at 25 m/s a needle moves 42 cm per frame at 60 fps, about 170 times its own
    width, and still cannot tunnel.
- **Why the root is at the tip.** The sweep's hit point is then the tip's contact point, which is exactly what
  embedding needs. Putting the root at the pivot would report a hit with the point already 8 cm inside the target.
  The mesh's own pivot stays at the centre of mass for everything else.
- **Throw:** spawn at the hand socket with the needle's `Throw` (= origin), velocity along socket +X.
- **Multiplayer (1v1):** replicate the throw event (origin, direction, speed, seed), not a per-tick transform. The
  server decides hits by its own sweep.

### 9.2 Volleys (many needles at once)

- **Visual:** a Niagara system with a **Mesh Renderer**, mesh `SM_Senbon`, **Facing Mode = Velocity**. It aligns
  the mesh's **+X** with the velocity, which is our point-forward axis, so no rotation offset is needed.
  - Pivot Offset is (0, 0, 0) for the centre-of-mass convention, or the `Tip` x in mesh space if the particle
    position should be the tip.
  - Material usage: section 8.3.
- **Gameplay:** hits come from server line or sphere traces per needle (or one replicated volley actor tracing N
  rays), **never** from Niagara collision. Niagara collision events can still drive cosmetic sparks.
- **Draw cost:** UE5 dynamic instancing merges identical mesh-plus-MI draws, so tens of separate needle actors are
  fine for the duel. For battle-royale volume, use Niagara for flight and HISM for the remains.

### 9.3 Instancing spent needles

- After a needle embeds or comes to rest, swap the actor for an instance in one **HISM per level or target type**:
  instance transform = the mesh's world transform (pivot = centre of mass, so no offset).
- Cap it (for example 128, FIFO), with the cull distances of 6.3.
- Retrieval or pickup, if wanted: a query-only overlap on the actor before the swap, or a trace against the HISM.

### 9.4 How an embedded needle sits

- **Direction: along the incoming velocity, not the surface normal.** A thrown needle keeps its angle of entry.
  Snapping to the normal makes every needle stand perpendicular, the tell of a fake.
  - Add ±2° random jitter so clusters do not look stamped.
  - **No stick** when the incidence from the normal is over **70°**: it glances and drops.
- **Depth:** set the needle so `Embed` lands on the hit point. `Embed` is at `Tip` - 15 mm, so the tip is 15 mm
  inside. For other depths, move along -velocity by depth − 15 mm. Defaults for the sidecar `embed.by_surface_mm`
  (game tune, not measured):

| Surface | Depth | Behaviour |
|---|---|---|
| Wood post, target | 10-20 mm | Stick |
| Straw or tatami target | 25-40 mm | Stick |
| Paper screen | Passes through | Spawn a hole decal, keep flying (a damped speed) |
| Cloth or flesh (character) | 20-35 mm | Stick. Attach to the **hit bone** (`AttachToComponent` with the hit's BoneName, KeepWorld), so the needle follows the animation |
| Stone, metal, armour | 0 | **No stick:** ricochet (bounce on, speed × 0.3) or drop, with a spark at `Tip` |

- **Visible length.** With a 150 mm needle and 15 mm of depth, 90 % shows, so the needle reads as stuck, not
  buried. The opaque surface hides the buried part, and the depth is chosen so the tip never pokes out of a thick
  surface. Thin surfaces (paper, cloth) let it through, which is correct.
- **After embedding:**
  - collision NoCollision, or query-only for pickup;
  - Cast Shadow ON;
  - movement stopped;
  - after a few seconds, the instance swap of 9.3 (not for needles on characters).

---

## 10. How the spike and kunai were built and verified: the conventions to copy

| Convention | Spike / kunai (shuriken_lib 3.10-3.11) | Senbon (props build, flashbang pattern) |
|---|---|---|
| Generator | Parametric and analytic: every LOD authored by the generator at its own segment count, never decimated (`lod_strategy`) | `senbon_geom.py`: one profile function r(x), the side count and stations per LOD, the same UV function on every LOD |
| Spec | `spec.py` / `bar_spec.py` dataclasses: build-to numbers with SOURCED / ESTIMATE status | `props_lib/senbon_spec.py`: a pure-Python dataclass of the Study's design-sheet numbers with their status, `SocketDef`s as **rules**, budgets, masses and texture sizes. Read by Blender, the calculators and the Unreal verifier. |
| Stages | `build_pack.py` per form, with `--frozen-maps` | `Scripts/props/build_senbon.py`: `mesh, textures, save, qa, export, render, report` (the flashbang's `ALL_STAGES`), plus `--quick` / `--dev-dir` for iteration only |
| Pivot | The centre of mass (the spike's by volume; the kunai's mass-weighted with the wrap) | By volume (all steel), authored shifted by the measured centroid |
| Mass gate | The un-ground outline within ±2 g of the sourced target; the finished mass is reported and is the override | The same, against the Study's design mass |
| Hull | Authored analytically (the bar prism), checked against every LOD | An analytic octagonal capsule (4.1) |
| Sockets | `Grip`, `Trail` (plus `Tip` and `Ring` on the kunai); Empties plus the sidecar; identical names across forms | `Grip`, `Tip`, `Trail`, `Throw`, `Embed` |
| Screen sizes | 1.0 / 0.10 / 0.035 × R / 50 mm, R = Unreal's bounds radius from the **bbox centre** | The same, via `props_lib.spec.scaled_lod_screen_sizes` |
| LOD gates | Strictly descending; two-sided surface deviation; `lod1_is_distinct` reported (on the spike, LOD1 is visually equal to LOD2, kept for chain uniformity) | The same. Report each LOD's value honestly. |
| UVs | Deterministic layout, no packer; cross-LOD UV deviation in px; unused-texel fill | The same (7.2) |
| Normals | Analytic arc normals; `knife_shading_max_dev_deg` | Analytic radial normals; apex shading gate |
| Symmetry | C4 about X: quarter-turn and mirror deviation exactly 0 on 1 nm-snapped positions | C_n about X for the n-gon, exactly 0, same method |
| Maps | Cycles bake on the GPU (OptiX), EXTEND margin 16 px, colour chunks stripped from ORM and N, DirectX N, SHA-256 in the report | The same, 2048 × 256 |
| Renders | Baked maps only: hero, top, LOD strip with end-on section insets, wire, line sheet; pack-consistency gates on coat pixels against the anchor forms | The same set, plus a **distance strip** (1.0, 2.5, 5, 10 m) and a hand-scale image beside the spike |
| Report | `<form>_report.json` + `.md`; every number measured on the built mesh; `known_gaps` stated plainly | `WorkFiles/senbon/senbon_report.json` + `SENBON_REPORT.md` |
| Unreal | `UnrealCheck6`: pass 1 import plus sidecar, pass 2 fresh-process gates, pass 3 the engine's FBX export plus a Blender round trip. The report is written "pending" with SHA-256s, and `attach_engine_check.py` promotes it only when the imported bytes equal the shipped ones. | `WorkFiles/senbon/UnrealCheck/`: a copy of `WorkFiles/flashbang/UnrealCheck_fin2/` with prefix `sbu_`, plus the pass-3 round trip from `UnrealCheck6`. New content path per run, `/Game/PropsCheck/Senbon_<run>`. |
| Regression | Frozen forms byte-identical (`post_blade_section`) | Snapshot SHA-256 of `Exports/{Shuriken,SmokeBomb,BlackHat,PaperBomb,Fan,Flashbang}` and `Scripts/unreal/materials/**` at the start, prove them at the end; run `check_exports_frozen.sh` at the start and end, and explain only DIFFs that are new |

---

## 11. Verification checklist

### 11.1 Blender (build gates)

1. `qa_check` passes on every LOD: budget 1,000, `--require-uv1` off (generated at import, as the pack does), no
   franchise strings.
2. **Dimensions equal the Study's design sheet** within its tolerances (length, D, point length and profile,
   tail feature). Silhouette overlay against the sheet's orthographic drawing: match by looking, then measure IoU
   and the profile r(x) error.
3. The pivot is the centre of mass to 1e-6 mm. The mass gate is on the outline. The finished mass is reported, and
   `hull_com_offset_cm` is reported.
4. Sockets equal their rules: ≤ 0.01 mm and ≤ 0.05°. `Tip` is the apex vertex or tip-flat centre; `Trail` is on
   the butt face.
5. The hull contains every LOD, with 0.0 mm outside; vertex count ≤ 32; volume ratio reported.
6. LODs: 238 / 94 / 34 or the design's equivalent, strictly descending, two-sided deviation p99 < 1 px at each
   switch, C_n symmetry 0.
7. UVs: no overlap, texel density uniform (taper included), cross-LOD deviation 0 px, fill outside the islands.
8. Maps: 2048 × 256, power of two, full mips, AO baked, no colour chunks in ORM / N, DirectX N; renders from the
   baked maps only.
9. Pack look: coat and point pixels against the spike's (`PACK_COAT_ANCHOR` method, like with like). The hero must
   read as the same steel.

### 11.2 Unreal 5.8.3 (fresh processes, one commandlet at a time, the guard first)

**Pass A** imports with the README's settings:
- legacy importer, Convert Scene ON, Convert Scene Unit ON, Force Front XAxis OFF;
- Import Mesh LODs ON, One Convex Hull per UCX, Import Normals + MikkTSpace, Generate Lightmap UVs ON,
  Do Not Create Material;
- then the sidecar, then the textures through `props_lib/ue_import_textures.py`.

**Pass B** runs in a second fresh process on the reloaded assets:
- LOD triangles equal Blender's exactly;
- exactly 1 convex element;
- 5 sockets equal the sidecar at relative scale 1;
- screen sizes read back;
- LightMapCoordinateIndex 1 with UV1 overlap 0 on every LOD;
- 1 slot; Nanite off;
- texture flags 3 of 3;
- FBX and sidecar SHA-256 equal the build report;
- zero Warning or Error lines (beyond the known profiler DLL probes);
- **senbon-specific:**
  - the `Tip` socket equals the render data's max-X vertex within 0.01 mm;
  - the bounds sphere radius equals the computed R within 0.01 mm;
  - the hull-derived centre of mass is reported against `hull_com_offset_cm`.

**Pass C:** Unreal's own FBX export of the saved asset, then a Blender round trip. The hull and positions must equal
the shipped FBX (within 1e-6 cm).

### 11.3 Distance and flicker render (real RHI offscreen, report-only on first run)

- **Setup.** The needle and the **spike as a matched control**, lying on a neutral floor, at 1.0, 2.5, 5 and 10 m,
  with a slow camera drift of 0.25 px per frame over 32 frames. TSR is on, if the capture path keeps temporal
  history (SceneCapture with persistent rendering state).
- **Report:**
  - per distance, the coverage of the expected footprint;
  - the temporal standard deviation of luminance inside it;
  - the share of frames where the needle's coverage drops under 30 % of its median.
- **Pass:** the senbon is no worse than the spike scaled to equal on-screen width. **Above that:** the section 6.2
  specular option goes to the user, with images.
- If a commandlet capture cannot keep temporal history, write "not measured", with the reason. **Never** use the
  user's open editor.

### 11.4 Materials (finalise)

- The MIs compile with 0 failures, and none are WorldGridMaterial.
- Dependencies are own-item only.
- The Base / leaf chain is correct.
- The default steel BC capture equals the shipped BC to within DXT1 block error.
- If 8.3 was done, the dump comparison proves only the flag and the Senbon instances changed.
- `Exports/Senbon/MATERIALS_README.md` follows `Exports/Shuriken/MATERIALS_README.md`'s steel section.

### 11.5 Housekeeping

- The asset lock `Senbon` (agent claude) is taken by the builder and released by the finaliser.
- No Blender or UnrealEditor-Cmd process is left running.
- The frozen-exports proof is done.
- Showcase: `showcase/Senbon/` via the read-only `studio.py`, plus one `ASSET_LIST.md` row.

---

## 12. Deliverables

| Path | Contents |
|---|---|
| `Scripts/props/build_senbon.py`, `Scripts/props/props_lib/senbon_{spec,geom,paint,look,gallery,metrics}.py` | The build (the flashbang's module split). Its own calculators read `senbon_spec`. |
| `Assets/Senbon.blend` | Textures packed |
| `Exports/Senbon/` | `SM_Senbon.fbx` (LodGroup: LOD0-2 + UCX), `SM_Senbon.sockets.json` (5 sockets, screen sizes, plus `mass_kg`, `embed`, `throw`, `material`), `Textures/T_Senbon_{BC,ORM,N}.png`, `README.md` (sizes, mass, import settings, sockets, the projectile / Niagara / HISM / embed recipes of section 9, the cull distances, the UV1 note, the Center Of Mass Offset), `MATERIALS_README.md` |
| `Renders/Senbon/` | Hero, top, LOD strip with section insets, wire, distance strip, hand-scale image with the spike, line sheet |
| `WorkFiles/senbon/` | This plan, `tech/` (calculator plus JSON), the Study's design sheet, the build report, `UnrealCheck/`, `regression/` |

---

## 13. Open points

### 13.1 For the Study

1. Section (round or octagonal), D, length, the point profile (conical or ogive, and its length), and any tail
   feature. These numbers fix the worked values above.
   - Keeping D at about 2-3.5 mm keeps it distinct from the 6 mm spike and visible to about 2-3 m at 1080p
     (table 1.2).
   - Under 2 mm is allowed but is invisible in third person.
2. Single-pointed or double-pointed. A double point puts the centre of mass at the middle, `Trail` becomes a
   second tip, and the throw can lead with either end. The sockets keep their names.
3. The grip the design implies, if it is not about 40 mm from the butt.

### 13.2 For the user

1. **The name.** "Senbon" as the name of a throwing needle is widely associated with one anime franchise. The
   shuriken study already flags `Senbon.svg` on Wikimedia as franchise-derived fan art (`SHURIKEN_STUDY.md` 5).
   - It is a generic Japanese word, not a trademark, and it is not on `qa_check`'s deny list.
   - Suggestion: keep `SM_Senbon` internally if you like, but title the Fab listing "Throwing Needles", with the
     historical term hari-gata shuriken (needle-type shuriken) in the body.
   - Renaming the files before shipping is a one-constant change in `senbon_spec`.
2. **A bundle mesh** (for example 5 needles tied together, for loot, display or the armory) is not planned. It
   would be a separate small mesh reusing the same atlas. Say if wanted.
3. **In-flight VFX** (a streak or ribbon from `Trail` and a tip glint) is what makes thrown needles readable past
   about 2.5 m. The asset provides the sockets and the README recipe; a VFX asset is a separate job.
4. **The `M_Steel_Master` Niagara usage flag** (8.3): recommended for the game; a shared-master change done under
   the lock.

### 13.3 For the finaliser

- 8.2 and 8.3 under `np_lock` owner `senbon-wf`.
- The flicker-render result (11.3) and, only if it fails, the specular option, with images for the user.
