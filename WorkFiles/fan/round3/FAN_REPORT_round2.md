# SK_Fan: build report (folding fan / sensu, skeletal prop), round 2

**Date:** 2026-09-26. **Library:** props_lib fan (`fan_spec`, `fan_fold`, `fan_geom`, `fan_tassel`, `fan_paint`,
`fan_look`, `fan_refview`, `fan_gallery`). **Build:** `Scripts/props/build_fan.py`, run from scratch with no arguments
(Blender 5.2.0 LTS, headless, `--factory-startup`, 164 s, fold bind offsets from the cache `8728ffefcd880b74`, which
`WorkFiles/fan/run_fold_optimisation.py` regenerates in about 12 min). It rebuilt `Assets/Fan.blend`,
`Exports/Fan/` and `Renders/Fan/`. Log: `WorkFiles/fan/final_build.log`. Report: `WorkFiles/fan/fan_report.json`.

This round covers shape and mechanism only. The leaf and ribs are plain black, with no painted design (no willow,
flowers or seal) and no rib piercing. The round-1 sources are kept for comparison, not shipped.

## Status

- **Build gates: 24 of 24 pass** (`fan_report.json`, `gates`). They cover:
  - fold cracks, intersections, half keys and the closed stack;
  - the new G2b gate: neighbouring faces never cross at bind;
  - skeletal QA and LOD bands;
  - maps, recolour, mip parity, tint and Detail16;
  - UV overlaps and the minimum triangle area;
  - frozen assets, the deny list, the reference camera and the fidelity gates.
- **qa_skeletal:** fan 138 of 138, tassel 57 of 57.
- **Blender re-import verify: V1-V6 pass** (`Scripts/props/verify_fan.py`, full quality). It re-imports the shipped
  FBX files and replays every key and half key of every clip.
- **Unreal 5.8.3: VERIFIED, U1-U9 pass** on these exact bytes (pass 1 checked the SHA-256 of all 7 FBX files it
  imported). It ran in two separate processes under `/Game/FanCheck/Final_0926r2b`:
  - pass 1 imports and saves (`-nullrhi`);
  - pass 2 is a fresh process with a real RHI that only measures and renders.

  The only Warning/Error lines are the usual 4 missing profiler DLLs per process. No UnrealEditor-Cmd was running
  before or after either pass.
- **Pipeline:** not touched this round. `Scripts/pipeline/skeletal_prop.py` is unchanged since round 1's passing
  `test_pipeline.py` and `test_qa_negative.py` runs.
- **Frozen assets unchanged.** All 60 frozen hash entries are identical to round 1's (`frozen.after`) and equal
  before and after this build. They cover:
  - the shuriken, smoke bomb, black hat and paper bomb blends, Exports and Renders;
  - `Scripts/shuriken`, `Scripts/unreal/materials`, the static pipeline, and the other props' builders and
    libraries.

  The newest file in `WorkFiles/materials` and in every other frozen tree dates from 07:57 or earlier, before any
  fan work.

**Bytes (shipped):**

| File | SHA-256 (prefix) |
|---|---|
| `SK_Fan.fbx` | `4886544b80fb` |
| `SK_Fan_LOD1` | `38f23e37bbcf` |
| `SK_Fan_LOD2` | `e9e26d09ef9f` |
| `A_Fan_OpenClose` | `787d8e705edb` |
| `A_Fan_Openness` | `d12d6e27d9df` |
| `A_Fan_OpenPose` | `3d20b438d58d` |
| `SK_Fan_Tassel` | `713dfe4bec4f` |
| `SK_Fan.skeletal.json` | `3383b2a789d8` |
| `Fan.blend` | `51c68c1eca8e` |

Full hashes are in `fan_report.json` under `export.files`.

---

## 0. What round 2 changed, and why

The blind judge picked the copy in 15 of 16 pairs. The measurer found the fold sound but several shape and look
differences. Each fix is listed with what it answers and how it was checked.

| # | Finding (round 1) | Fix | Check |
|---|---|---|---|
| R1 | Fold: neighbouring faces crossed by ~4 µm at bind (the back layers were offset along two different normals at each fold) | Each face's back layer now **tapers to the front layer on both fold lines** (0 → 0.02 mm over 1 mm), so two faces' layers meet exactly on every fold. They stay apart for any dihedral above 2.3° (the closed pleats' minimum is 3.44°) | G2b: **0 neighbouring crossings at bind**; verify shows 0 in the open pose |
| R2 | **Pleat phase about half a pitch off fan2**: shading anti-correlated, edge notches 3.2° off | **The fold alternation is flipped.** The leaf lines on the ribs are now the MOUNTAINS (soft rounded ridges) and the mid-gap folds are the VALLEYS (sharp creases, -Z behind the leaf lines). The leaf-line offsets are **fitted to fan2's 24 visible edge notches**: +1.27° at the front guard to -0.30° at the rear | Notches: **mean +0.14°, rms 0.52°, range -0.75 to +1.15°** (round 1: 2.2-3.2° off). Shading correlation at zero shift is now **+0.46 to +0.75** over φ 20-140° (round 1: -0.22 to -0.85) |
| R3 | Edge ripple 1.5x too deep, a crisp zigzag | The outer edge is a **sinusoid** along each face (5 segments at LOD0), with the bump at the mountain and the notch at the valley. The in-plane scallop is 0.19 mm, because the valleys' 3.9 mm fall already gives most of what the camera sees | Ripple p95-p5 **3.08 px vs fan2's 2.96** (round 1: 4.1 vs 2.8) |
| R4 | Flat two-tone facets with hard mountain creases | Each face is cut into strips with **normals sweeping across it**: the ridge bisector at the rib, then past the face normal to twice the face's tilt at the valley. The result is a convex silk face with a soft ridge and a sharp crease, and a mean normal equal to the face normal. The leaf's normal map adds silk cockling (3-12 mm, 0.06 mm) and the weave's ripple | Leaf tone p10/50/90 **0.0052 / 0.0151 / 0.0273** (fan2 0.0076 / 0.0156 / 0.0287). See the crops and side-by-side |
| R5 | "White dots" along the leaf's inner edge (rib shoulders letting light through) | The rib slips are gone (they would sit where the valleys now fall). Ribs are **0.056 L wide at the leaf edge, so neighbours overlap about 1 mm**, with near-square shoulders (0.12 mm, one cut) and the tip 0.10 mm inside the leaf (the fold proof's minimum, below) | The dots at the rib junctions are gone. A 0.10 mm ring and small valley slits remain (known gap 1) |
| R6 | See-through eyelet | Each eyelet head's hollow is a **blind recess** with a dark floor 0.5 mm below the stack face (dark, dull map), which is fan2's dark centre. The ring is polished (roughness 0.08-0.35) | Crops row 1 |
| R7 | Tassel: smooth cone, perfect-sphere bead | The knot is a ball with **raised crossing cord turns**. The skirt is **16 thread locks** (LOD0) around a hidden core. Each lock has its own wander, a ragged length (RS 8's 0.015 L) and a splay at the tip, and the maps add single threads | Rivet-to-tip **0.624 L vs fan2's 0.629 L** (round 1: 0.648). Width profile follows RS 8's measured stations |
| R8 | Bare ribs read as one flat plate | Each stick has its own tone (±8 %), roughness and twist (±4° across it, in the normal map), and glossier lacquer (roughness 0.25-0.36). The overlapping ribs' step edges now show | Lobe p10/50/90 **0.0028 / 0.0055 / 0.0074** (fan2 0.0025 / 0.0049 / 0.0089). The bare ribs' contrast is still low (known gap 2) |
| R9 | Stair-stepped silhouettes | Reference render pixel filter 1.0 → 1.5 (Blender's default) | Visual |
| R10 | Closed leaf 11.45 mm beside the guard, stack 23.7 mm | Follows from R2: the guards now sit near the pages when closed | **Closed 210.2 x 17.2 x 15.5 mm** (round 1: 23.97 mm wide) |

Unchanged from round 1: opening 163.2°, 26 sticks, L = 190 mm, the leaf radii, guard widths, the rear guard's
measured outer line, colours, the bone scheme, clips, sockets, physics and the export route.

## 1. Decisions (defaults the builder chose; change any of these)

| # | Decision | Why |
|---|---|---|
| D1 | Opening **163.2°** guard axis to guard axis. 26 sticks (2 guards + 24 ribs), L = 190 mm | fan2 metrology |
| D2 | Leaf: **25 pleats = 50 rigid faces. Leaf lines on the ribs = mountains, mid-gap folds = valleys** (round 2, MEASURED). The REFERENCE_SPEC row "rib folds are valleys" was INFERRED. The round-1 build that followed it came out anti-phase against fan2 in shading and in silhouette. `References/Fan/REFERENCE_SPEC.md` now carries the correction row | fan2 notch fit (R2) |
| D3 | **One bone per leaf face** (leaf_00..49), each a CHILD of the stick it hinges on | Unreal slerps each bone's LOCAL rotation; parented to their sticks the cracks stay ≤ 0.079 mm at half keys |
| D4 | **Bones: pivot + 26 sticks + 50 leaf = 77** in Blender and **78 in Unreal** (the armature object `root` becomes the root bone) | pack convention |
| D5 | Rib **0.37 mm** thick, 5 µm stack clearance. The stack is **13.235 mm**, including a **0.435 mm gap under the front guard**: leaf line 0 lies one leaf pitch above rib 1's, 0.03 mm under the guard, where the leaf's first panel is glued. A spacer on the guard's bone fills the gap in the bare zone | the stacked leaf lines step one pitch per stick |
| D6 | Leaf-line offsets **+1.27° (front) → -0.30° (rear)**, linear. Leaf pitch 6.465°, stick pitch 6.528° | Least-squares fit to fan2's notches. fan2 alone puts the rear 0.75° outside the rear axis, but the last face falls toward the rear guard, so the rear leaf line must lie on the guard's inner edge. In the leaf zone that edge is brought to it; it is hidden under the glued flap from the front |
| D7 | Closed: the pages lie on the **front guard's outer side** of the common leaf line: 11.4 mm at the tip, 4.9 mm at the base, mostly behind the front guard (lateral -8.8 to +0.3 mm at the tip). The closed stack is 17.2 mm wide | physical for 50 faces of silk. The page side is set by the valley direction (the mechanism) |
| D8 | Rear guard's outer outline **measured** from fan2's silhouette line | `WorkFiles/fan/measure/fan_edge_lines.py` |
| D9 | Tassel is a separate SK_Fan_Tassel with a 6-bone chain, attached at the fan's `Tassel` socket (back eyelet) | optional piece; it must hang under gravity whatever the fan does |
| D10 | Clips: **A_Fan_OpenClose** (60 fps: 0.5 s eased open, 0.3 s hold, 0.5 s close), **A_Fan_Openness** (60 fps, linear in angle over 1 s; drive openness by time), **A_Fan_OpenPose** (static open). Bind pose = open. Closed = 1.57° guard to guard (s = 0) | |
| D11 | Physics: **one** body for a held prop | section 5 |
| D12 | **Unreal animation compression = `/Engine/Animation/DefaultRecorderBoneCompression`** | MEASURED in round 1: the default ACL setting moves the leaf up to 0.6 mm and cracks the fold |
| D13 | Rib tip **0.10 mm** inside the leaf's inner edge | Fold proof: at 0.08 mm the closing pleats' valley corners touch the rib tips at 5-8° open (30 hits); at 0.06 mm there are 1,640 hits; at 0.10 mm there are none |

## 2. Mechanism and fold proof

Frame: rivet at the origin, rivet axis +Z (front), stick_00 (the held front guard) along +X, opening
counter-clockwise. Openness s runs from 0 (closed, 1.57°) to 1 (bind/open, 163.2°).

- **Numpy mechanism (G1-G3) at 87 openness samples:** worst crack **0.0784 mm**, **0 triangle intersections**
  (leaf/leaf non-neighbours, leaf/sticks, stick/stick, rivet). Minimum dihedrals are 3.44° at the mid folds and
  3.61° at the rib folds, so no face flips.
- **Neighbouring faces:**
  - **0 crossings at bind** (G2b; round 1 had 75 pairs).
  - Posed, up to 592 triangle pairs of neighbouring faces cross along their shared fold. There, the two rigid copies
    of a fold line are up to the crack (≤ 0.079 mm) apart and meet at a few degrees near closed.
  - This is the crack gated at 0.1 mm, seen another way. It stays between faces sharing a fold, never with a
    non-neighbour, a stick or a guard.
  - It would disappear only with more bones per pleat or with morph targets (see known gaps).
- **Half keys (Unreal-style local slerp between keys):** OpenClose 0.0775 mm, Openness 0.0781 mm, 0 hits.
- **From the exported files (verify_fan, Blender importer, 121 + 157 evaluations):** worst crack 0.0788 mm, worst
  stretch 0.00013 mm, 0 intersections, 0 front-guard hits. Neighbouring crossings: 0 in the open pose, at most 588
  posed (as above).
- **Unreal, raw clip poses** (every key and half key): crack **0.0079 cm**, opening error 8.3e-5°.
- **Unreal, runtime component poses** (compressed clip): crack **0.0078 cm**, opening error 2.6e-5°.
- **Sheets:**
  - `Renders/Fan/fan_fold_sheet.png`: 0, 15, 30, 60, 90, 120, 150 and 163.2°, a front row and a row from above the
    tip, from the re-imported FBX.
  - `Renders/Fan/fan_closed_stack.png`: end-on and from above.
  - `Renders/Fan/fan_unreal_fold_sheet.png`: Unreal offscreen captures.

  The pleats fold into an even zigzag and lie down as one neat stack of 25 pages.

## 3. Geometry, LODs, skin

| | LOD0 | LOD1 | LOD2 | screen size |
|---|---|---|---|---|
| SK_Fan | 4656 | 2220 | 1020 | 1.0 / 0.413 / 0.1446 |
| SK_Fan_Tassel | 1384 | 384 | 76 | 1.0 / 0.1207 / 0.0423 |

- Every fold is kept at every LOD, and all 77 bones are kept (no Bones to Remove). The leaf's strips per face are
  5 / 3 / 2 at LOD0 / 1 / 2 (front) and 3 on the tapered back layer.
- The LOD bands are now 3000-6000, 1500-3000 and 500-1500. The strips cost the leaf 800 / 600 / 500 triangles
  (round 1: 200).
- **Skin:** one influence per vertex on the fan; at most 2 on the tassel. Weights are normalised, with no unweighted
  vertices and no triangle under 0.001 mm². The closed parts (sticks, spacer, eyelet) are manifold.
- **Size:**
  - Open 372.9 x 210.1 x 16.2 mm. Closed 210.2 x 17.2 x 15.5 mm.
  - Leaf radii 81.9-190 mm. The valleys fall 3.94 mm (edge) / 1.67 mm (base) behind the leaf lines.
  - In-plane scallop 0.19 mm. Tassel rivet to tip 119.2 mm. Mass 22 g.
- **Sockets:**
  - `Grip` on stick_00, 40 mm above the butt. **This is an estimate: set it against your hand rig.**
  - `Pivot` on the rivet axis.
  - `Tassel` at the back eyelet.
  - `Tip` on stick_12 at the leaf edge.

## 4. Textures and recolour

Tint-ready maps follow the MATERIALS_REPORT conventions for the leaf, sticks and tassel:
- BC, ORM, N, and a full-range Detail (8-bit, plus a lossless Detail16 in `Textures/Recolour/` with
  `recolour_maps.json`).
- Colour = the part's mean colour = the reference colour by default.
- Mip parity is within 1 % or half a level.

The rivet is metal and not tintable; its recess is dark in its own maps. All renders are from the BAKED maps.

## 5. Physics (PHYS_Fan, PHYS_Fan_Tassel)

- **SK_Fan:** ONE body with the fan's full 22 g mass. It has two boxes:
  - a handle box (21.2 x 1.4 x 1.65 cm), the only colliding shape;
  - a bounds envelope (37.6 x 21.2 x 2.6 cm; no collision, no mass), the AABB of LOD0 posed at 41 openings.

  U7 found the posed leaf inside the bounds at every checked opening (worst corner 0.10 cm inside).
- **SK_Fan_Tassel:** a Kinematic anchor sphere and one capsule per chain bone, joined by 5 constraints.
- **Build route:** unchanged. Proxy meshes in `WorkFiles/fan/build/physics_proxy/` make the builder create exactly
  these bodies, which the import script then rewrites from the sidecar.

## 6. Unreal verification (UE 5.8.3, `/Game/FanCheck/Final_0926r2b` in ShurikenValidation)

Scripts are in `WorkFiles/fan/UnrealCheck/`, outputs in `final_r2/`. **`run_ue.sh` changed in round 2:** after
its run it stops only a leftover process whose command line carries its own script. Round 1's version killed
every UnrealEditor-Cmd, which could have hit another session's editor. It still refuses to start while any
UnrealEditor-Cmd is running.

| Gate | Result |
|---|---|
| U1 bones 78, hierarchy, reference-pose heads | max head error 2.1e-6 cm |
| U2 no bone scale | max 2.4e-7, root scale 1 |
| U3 sockets | 0.0 cm / 0.0° |
| U4 LODs | 3 LODs, 1.0 / 0.413 / 0.1446 |
| U5 clips play, fold holds (raw poses, all keys and half keys) | crack 0.0079 cm, opening error 8.3e-5° |
| U6 physics assets | as the sidecar |
| U7 bounds hold the leaf | worst corner 0.10 cm inside |
| U8 posed offscreen renders, tassel on its socket | 10 shots, attach error 0 |
| U9 runtime (compressed) fold | crack 0.0078 cm |

The Unreal check uses check materials made from the exported maps (M_FanCheck_*), as in round 1 (known gap 5).

## 7. Renders (`Renders/Fan/`, all from baked maps)

The renders are:
- `fan_reference_view.png`, `fan_side_by_side.png` (fan2 | ours) and `fan_crops_3x.png`;
- `fan_hero.png`, `fan_front.png`, `fan_back.png`, `fan_top.png`, `fan_underside.png`, `fan_raking.png`;
- `fan_wire.png`, `fan_lods.png`, `fan_linesheet.png`;
- `fan_fold_sheet.png`, `fan_closed_stack.png`, `fan_unreal_fold_sheet.png`.

**Fidelity against fan2** (RS 1 camera):
- Mask IoU **0.978** (0.969 with the tassel against the photo's tassel). Boundary mean 1.68 / 1.62 px.
- Pleat notches within 0.52° rms; ripple 3.08 vs 2.96 px.
- Leaf, lobe and tassel reach as in section 0.

## 8. Known gaps (for the user)

1. **Rib-tip ring and valley slits.** The leaf starts 0.10 mm beyond the rib tips (the fold proof's minimum, D13).
   Behind the leaf's inner edge the valleys fall 1.7 mm, so:
   - straight on, a 0.10 mm ring can show daylight;
   - in oblique views, a short slit can show under each valley.

   Both are about 0.2 px in the reference view and a faint line in close-ups. A real fan hides this because its silk
   is glued flat to the rib tops at the inner edge. A rigid-face leaf cannot flatten there:
   - a silk tuck under the rib tips was tried, and it hits the ribs below 25° open;
   - slips under the ridges would sit where the faces fall.

   Hiding it would need two bones per face near the inner edge, or morph targets.
2. **Bare ribs still read flatter than fan2** (bare-zone p10-p90 0.0084-0.0107 vs 0.0048-0.0252). fan2's bare zone
   is mostly openwork (pierced), which the brief keeps out. Per-rib tone, twist and gloss helped the lobe but not the
   bare zone's spread under this soft key light.
3. **Left end of the leaf:** the pleat pattern drifts up to about 1-2° from fan2's over φ 140-165°. fan2's rear leaf
   line lies outside its rear guard's axis, which the rigid mechanism cannot follow (D6).
4. **Neighbouring faces cross along their shared fold by the crack while posed** (section 2). It is invisible
   (≤ 0.079 mm) and absent at bind.
5. **Pack materials on a skeletal mesh.** M_Fabric_Master and M_Steel_Master lack "Used with Skeletal Mesh".
   `Scripts/unreal/materials` is left for the Integrate phase (your decision); Unreal verified the fan with check
   materials.
6. **Tassel physics:** the asset and constraints are verified, but no gravity simulation was run in-engine (a
   commandlet does not tick).
7. **Grip socket** position is an estimate.
8. **Excluded from the reference on purpose:** the painted design and the rib openwork.
9. **The eyelet ring renders greyer than fan2's** under the reference lighting (a near-black studio). fan2's bright
   ring reflects its white studio. This is lighting, not the asset.
10. **Photo character:** fan2's JPEG noise and colour cast are not added to renders; the blind test lists them as
    tells. They belong to the photo, not to the asset.

## 9. Files

- **Build:**
  - `Scripts/props/build_fan.py`
  - `Scripts/props/props_lib/fan_*.py`
  - `Scripts/pipeline/skeletal_prop.py` (round 1; unchanged)
- **Verify:**
  - `Scripts/props/verify_fan.py`
  - `WorkFiles/fan/UnrealCheck/`: `fan_ue_common.py`, `fan_ue_pass1_import.py`, `fan_ue_pass2_verify.py`,
    `fan_ue_sheet.py` and `run_ue.sh`
- **Outputs:**
  - `Assets/Fan.blend`
  - `Exports/Fan/` (11 FBX + sidecars, `Textures/`)
  - `Renders/Fan/`
  - `WorkFiles/fan/fan_report.json`
  - `WorkFiles/fan/verify/verify_report.json`
  - `WorkFiles/fan/UnrealCheck/final_r2/pass1.json`, `pass2.json`, `ue_sheet.json`
- **Fold cache:** `WorkFiles/fan/fold_bind_cache.json` (key `8728ffefcd880b74`; optimisation log
  `WorkFiles/fan/fold_optimisation_r2.log`).
