# Folding Fan (sensu): SK_Fan

A black silk folding fan with 26 bamboo sticks (2 guards and 24 ribs), a pleated leaf that really folds, and an optional
tassel. It is plain black on purpose: no painted design and no pierced ribs. Every part except the metal rivet can be
recoloured.

## What is in this folder

| File | What it is |
|---|---|
| `SK_Fan.fbx` | The fan, skeletal mesh, LOD0 (78 bones in Unreal: `root`, `pivot`, `stick_00`..`stick_25`, `leaf_00`..`leaf_49`) |
| `SK_Fan_LOD1.fbx`, `SK_Fan_LOD2.fbx` | Its LOD1 and LOD2 (same skeleton; import them as LODs of `SK_Fan`) |
| `A_Fan_OpenClose.fbx` | Clip: flick open, hold, close (1.3 s, 60 fps) |
| `A_Fan_Openness.fbx` | Clip: closed at 0 s to fully open at 1.0 s, linear in angle. Drive it by time, do not play it |
| `A_Fan_OpenPose.fbx` | Clip: the static open pose |
| `SK_Fan_Tassel.fbx` (+ `_LOD1`, `_LOD2`) | The optional tassel: its own skeletal mesh, a 6-bone chain |
| `SK_Fan.skeletal.json`, `SK_Fan_Tassel.skeletal.json` | Sidecars: bones, sockets, LOD sizes, import settings, physics bodies, materials |
| `Physics/` | Proxy FBX files that rebuild the two physics assets exactly (see "Physics") |
| `Textures/` | BC, ORM, N and Detail maps per part; `Textures/Recolour/` holds the 16-bit Detail maps and the recolour data |

If you use the Ninja pack's Unreal content, all of this is already imported and set up under
`/Game/NinjaPack/Meshes/Fan/` with the material instances in `/Game/NinjaPack/MaterialInstances/`. The rest of this file
tells you how to use it, and what to keep if you import the FBX files yourself.

## Use it in Unreal (5.8)

1. **Put it in a hand.** Attach `SK_Fan` to your character's hand bone at the fan's **`Grip`** socket (on the front
   guard, 40 mm above the butt; +X runs along the guard, +Z comes out of the front). The grip position is an estimate:
   nudge the socket to fit your hand rig.
2. **Open and close it.**
   - For a gesture, play **`A_Fan_OpenClose`** once (for example as a montage slot on the fan's own Anim Blueprint).
     It starts and ends closed, so it also loops cleanly.
   - For gameplay control (half-open, fanning), use **`A_Fan_Openness`** in a *Sequence Evaluator* and set its
     **explicit time to the openness you want: 0 = closed, 1.0 = fully open** (163.2 degrees). Do not play it as a clip.
   - For a fan that simply stays open, loop **`A_Fan_OpenPose`**.
3. **Add the tassel (optional).** Attach `SK_Fan_Tassel` to `SK_Fan`'s **`Tassel`** socket (the back eyelet). Give the
   tassel an Anim Blueprint with an **AnimDynamics** node (Chain, Bound Bone `tassel_root`, Chain End `skirt_02`) or a
   **Rigid Body** node, so it hangs and swings under gravity. The cord's first few millimetres pass through the eyelet:
   that is the cord threaded through it, as on the real fan.
4. **Other sockets.** `Pivot` is on the rivet axis (spin or aim reference). `Tip` is at the leaf's outer edge at the
   middle of the fan (trails, gusts).

### Settings you must keep if you import the FBX files yourself

- **Animation compression: `/Engine/Animation/DefaultRecorderBoneCompression` on all three `A_Fan_*` clips.**
  Unreal's project default (ACL) moves the leaf by up to 0.6 mm and opens visible cracks and see-through dots along
  every fold of the leaf. If you ever re-compress the clips with the project default, the leaf will crack. (A custom ACL
  setting also works: error threshold 0.001 cm and a virtual-vertex distance of at least 20 cm.)
- Import the clips at their own rate (60 fps) onto `SK_Fan_Skeleton`, with *Use T0 As Ref Pose* off.
- Import LOD1 and LOD2 as LODs of `SK_Fan` and **do not remove bones** from any LOD (every fold is kept at every LOD).
- Set the mesh's **Positive / Negative Bounds Extension** to the values in the sidecar (`import.bounds_extension_cm`).
  The leaf swings up to 16 mm behind the rivet while it opens and closes; without the extension the fan can pop out of
  view or lose its shadow at some angles.
- The Loop flags: `A_Fan_OpenClose` and `A_Fan_OpenPose` on, `A_Fan_Openness` off.

## Physics

`PHYS_Fan` has **one body** on the `pivot` bone, which carries every stick and leaf face. Only a box around the closed
handle collides (22 g); the open leaf has no collision, so drop the fan closed or add bodies yourself. Make it Kinematic
while it is held and let it simulate when dropped. `PHYS_Fan_Tassel` has a kinematic anchor and one capsule per chain
bone. If you simulate the tassel as component physics instead of in its Anim Blueprint, make it ignore its parent fan
(for example *Ignore Component when moving* or a collision channel the fan ignores).

To rebuild the physics assets from this folder: import `Physics/SK_Fan_PhysicsProxy.fbx` onto `SK_Fan_Skeleton` with
*Create Physics Asset* on (it makes exactly the right bodies), set each body's shapes, collision and mass from the
sidecar's `physics_bodies`, then assign the asset to `SK_Fan` and delete the proxy mesh. Do the same for the tassel.

## Change the colours

The fan has three colour parts, each with one buyer-facing material instance:

| Part | Material instance | What it colours | Shipped colour |
|---|---|---|---|
| Leaf | `MI_Fan_Leaf` | The pleated silk leaf | near-black blue-grey `#272B30` |
| Ribs | `MI_Fan_Ribs` | All 26 sticks: both guards and the 24 ribs | near-black `#212628` |
| Tassel | `MI_Fan_Tassel` | Cord, knot and threads | blue-black `#14181F` |
| Rivet | `MI_Fan_Rivet` | The metal eyelet | polished metal, not tintable |

To recolour a part:

1. Open its instance (for example `MI_Fan_Leaf`). For a variant, **duplicate it first** and put the copy on the mesh
   slot or on a mesh component, so the shipped one stays as it is.
2. In the group **01 Colour**, change **Colour**. You can type a Hex sRGB value in the colour picker.
3. Save. The silk grain, the bamboo grain and the shading all stay; only the colour changes.

What the colour means: **Colour is the average colour of the whole part**, so the part reads as the colour you pick,
not darker or lighter. The default is the colour measured from the reference photo.

Good to know (these hold for every recolourable item in the pack):
- Very light picks are capped at the part's **Lightest Colour** (in 01 Colour) so the highlights keep their detail;
  raise it if you want a brighter result and can accept flatter highlights.
- Pure black is lifted slightly (to about `#191919`) so the grain stays visible.
- The colour holds at a distance: the material corrects for mip-mapping.
- To get back to the shipped look, reset **Colour** to its default (the arrow next to it), or tick
  **Use Original Baked Colours**.
- Leave the groups **08 Advanced** and **09 Textures** alone: they are matched to the maps.

## Good to know

- **Closed state.** When fully closed, the guards stay 1.6 degrees apart and the folded pages stick out about 2.7 mm past
  the front guard's edge near the tip. The pleats are wider than the guard (11.4 mm against 9.1 mm at the tip, both
  measured from the reference fan), so they cannot all sit inside it. It is a neat stack with nothing passing through
  anything, but it is not a perfectly flush stick.
- **Inner edge of the leaf.** A band of thin rib ends (about 6 mm) runs over the leaf's inner margin, as on a real fan,
  so no daylight shows through at the leaf's inner edge from the front or the back at any opening, or from 45 degrees
  or steeper across the leaf. The band shortens with its gap as the fan closes, so the closed fan stays compact. From
  a low angle across a partly open fan (about 25 - 30 degrees toward the pivot), a few small slits can still show.
- **Fold lines.** The leaf is 50 rigid pleat faces; their folds meet within 0.09 mm at every pose, so a coverage render
  can show a few single-pixel specks along a fold line. They are not visible in normal shading.
- **Back of the leaf.** The ribs do not run up behind the silk: the leaf is made of rigid pleat faces, and a rib there
  would be crushed when the fan closes. From behind, the leaf is plain black silk.
- Not tested: mobile rendering, Nanite (it is a skeletal mesh).
