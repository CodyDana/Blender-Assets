SM_PaperBomb - import notes for Unreal Engine 5.8
=================================================

Everything in this folder was measured in UE 5.8.2 before it shipped.  Two of the four
maps import WRONG by default, and the mesh loses its sockets and its LOD screen sizes,
so this page exists.  Five minutes, once.


1.  THE MESH
------------
SM_PaperBomb.fbx holds three LODs in a LodGroup, one convex collision hull and one
material slot.

  * Import Mesh LODs   ON.  Off, you get LOD0 only.
  * Import Normals     ON (not "Compute Normals").  The 170 sharp edges between the
    card's faces and its 0.15 mm rim exist only as explicit split normals; the FBX
    smoothing layer says every face is smooth, so Compute Normals rounds the rim over
    and the silhouette softens.
  * Collision comes in as UCX_SM_PaperBomb_LOD0_00 -> one convex hull, 16 vertices.
    Do not rename the render mesh: the UCX prefix has to keep matching the node name
    exactly or the hull is dropped and the asset imports with NO collision, silently.
  * Nanite: off.  1,380 triangles with hand-authored LODs.


2.  THE SIDECAR - SOCKETS AND LOD SCREEN SIZES
----------------------------------------------
UE 5.8.2 drops FBX sockets from any file that carries a LodGroup, and an FBX LodGroup
carries no screen sizes at all.  Both live in SM_PaperBomb.sockets.json.  After
importing the mesh, run

    Scripts/pipeline/ue_import_sockets.py

against it (or read the JSON and set them by hand).  It recreates the four sockets and
applies the screen sizes, and it works around the FBX socket scale-100 bug.

--- BUILD DATA (written by Scripts/props/build_paper_bomb.py; do not edit by hand) ---

  socket positions, in centimetres, relative to the asset origin:
  Face    (  0.0008,  0.0000,   0.0075) cm   decal, glow and VFX anchor on the printed face (the tag rests on its curl, not on this point)
  Attach  ( -0.0008,  0.0000,  -0.0075) cm   stick to a wall, glue to a crate, parent to a kunai
  Fuse    (  4.9158, -0.0000,  -0.3297) cm   spark and burn VFX start; the _M green scorch gradient radiates from here
  Cord    (  8.0961,  0.0000,  -0.3971) cm   ties to the kunai's Ring socket at (-103.5, 0, 0) mm; also a fuse cord

  LOD screen sizes  1.0 / 0.1768 / 0.0619
  LOD triangles     1132 / 428 / 172
  bounds            16.1987 x 6.9825 x 1.2407 cm
  mass              0.900 g (Mass in KG override 0.001)
  SM_PaperBomb.fbx  sha256 a05cb011af52ab742f0ff122ec8727540eca1da0bb7afce634558d7156cfdae5

  T_PaperBomb_BC.png sha256 fe0041f73784b51cd5ada9d2e0aae043b51e205aaf340c026d62b93d9ee7cb64
  T_PaperBomb_M.png  sha256 ae485c210b63c87d665ddb874a44c52471fbdba8c16b645897b212ed7dcfe421
  T_PaperBomb_N.png  sha256 a02f26f68537e00011dd3a45f93d4dfa2205d6415158ace2066ba98420c75013
  T_PaperBomb_ORM.png sha256 b6a2748f0a375a92abd9ed855cc2850c7e83d3fe9ad140a6a2bcd40ba008e3e4

--- END BUILD DATA ---


3.  THE TEXTURES - TWO OF THE FOUR NEED A CHANGE
------------------------------------------------
Dragged in by hand, Unreal gives every PNG sRGB ON and TC_Default.  That is right for
the base colour and it auto-detects the _N suffix, but it has no mask detection:

  T_PaperBomb_BC    leave as imported            sRGB ON,  Default
  T_PaperBomb_N     leave as imported            sRGB OFF, Normalmap,
                                                 Flip Green Channel OFF
                                                 (the map on disk is DirectX green -
                                                  measured, not assumed)
  T_PaperBomb_ORM   UNTICK sRGB, set Compression to "Masks (no sRGB)"
  T_PaperBomb_M     UNTICK sRGB, set Compression to "Masks (no sRGB)"

Left as imported, roughness stored at 0.86 decodes to 0.709 and the ambient occlusion
goes with it, and the masks stop being linear.

All four are 2048 x 2048, so Mip Gen Settings is already "From Texture Group".  Check it
anyway if you ever resize one: a non-power-of-two texture imports with NO mipmaps in UE
5.8.2, silently, and does not texture-stream at all.


4.  WHAT THE CHANNELS MEAN
--------------------------
  BC   R G B   base colour: paper, sumi, vermilion, wear.  sRGB.
  ORM  R       ambient occlusion.  Near 1.0 over most of the card and that is honest -
               a 0.15 mm sheet has almost nothing to occlude.  The signal is in the
               crease valleys and where the curl turns under.
       G       roughness.  Paper ~0.86, ink ~0.72.
       B       metallic.  Exactly 0 everywhere.
  N    R G B   tangent-space normal, DIRECTX green.  Fibre grain, cockling along the
               heavy strokes, thumb dents, the fold grooves.  The curl and the two
               creases are GEOMETRY, not in here.
  M    R       fibre-fringe alpha.  ZERO everywhere on this card, and deliberately
               so: the tag's outline is a clean cut octagon - four straight sides and
               four straight 45 degree chamfers - with no tear, no nick and no folded
               corner, so there is no broken edge for loose fibre to stand out of.  The
               channel ships wired and empty rather than dropped, so a torn variant in
               this family needs no material change.  It is NOT a card-shaped opacity
               mask; wiring it straight into Opacity Mask erases the tag.
       G       burn ORDER, not scorch amount.  0 at the Fuse socket, rising to 1 at the
               far end of the card.  Threshold it - "burnt where G < BurnAmount" - so
               the burn starts at the fuse and eats down the tag.  Lerping toward char
               WITH G gives you a tag charred at the bottom and pristine at the fuse,
               which is backwards.
       B       ink mask (black or red ink present), for recolouring the print.

The shipped master material is OPAQUE.  M is included but not wired, on purpose: an
opaque material keeps early-Z, costs nothing on mobile and cannot shimmer.


5.  PHYSICS
-----------
The real sheet weighs 0.86 g.  That is at the light end of what Chaos is comfortable
with, so the asset ships with Mass in KG overridden to 0.001.  If it jitters, raise the
override to 0.005 - do not thicken the card.  If it tunnels, enable CCD on whatever is
hitting it.


6.  AI DISCLOSURE
-----------------
Nothing in this product is generated by a generative AI program.  The blend is rebuilt
from scratch by a deterministic build script, the FBX is exported from it, all four maps
are baked from that script's own procedural node graph and its own curve geometry, and
every character is typeset by Blender from a licensed SIL OFL 1.1 font.  No Fab
"Created with AI" flag is required.  (The fonts themselves are not redistributed in this
package, as their licence requires.)
