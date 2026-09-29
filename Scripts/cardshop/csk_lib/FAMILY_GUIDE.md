# Card Shop Kit: building a family (P3-P5)

A guide for a session that builds one family of `WorkFiles/cardshop/CARDSHOP_KIT_SPEC.md` section 3. The G1 items in
`geom.py` are the worked examples. Read them before writing anything; they are the house style.

## Where your code goes (parallel-safe)

- **Your family module:** `Scripts/cardshop/csk_lib/fam_<family>.py`, and nothing else in `Scripts/`. It defines:
  - `ITEMS = {"<family>_<item>": item_function, ...}`: keys prefixed with your family, e.g. `a_cases_tower`.
  - Optionally `CLASSES = {code: spec.ItemClass(code, footprint, pitch)}` for new placement classes (the spec's `class`
    column), used by fixture level grids.
  - Your numbers: a dict per item at the top of the module, with the spec's flags (M / D / E / E*) and the reference sheet
    in comments, exactly like `spec.py`. `geom.py` picks the module up by itself (`_load_families`).
- **Never edit** `geom.py`, `spec.py`, `shapes.py`, `mesh.py`, `build_csk.py`, the Unreal scripts, or another family's
  module. If you need a helper that lives there, import it (`from .geom import _prism_y, _face_out, _planar, ...`) or
  copy it into your module.
- **No git.** Don't commit, push, stash or switch branches: the lead session integrates and commits.
- **Report:** `WorkFiles/cardshop/families/<family>.md`. Renders go in `WorkFiles/cardshop/families/<family>/`
  (PNG in WorkFiles is git-ignored; the user views them in the app).

## Frames, units, pivots (spec 4.2)

- Millimetres everywhere. Builder coordinates are in mm; `mesh.to_object` converts.
- The pivot is the item's `Seat`: the centre of the face it rests on. **+X to the viewer's right, +Y away from the
  customer (the back), +Z up.** Cards, slabs and packs lie on their back; boxes and fixtures stand upright.
- Moving parts (lids, doors) are separate meshes with their pivot on the hinge or slide axis. They are wired through
  `data["parts"]`, as in `item_box_booster` (hinge: axis, `range_deg`, `open_rot_deg`) and `item_showcase` (slide:
  axis, `range_mm`).

## The item recipe

```python
from . import spec as S
from .geom import Item, Lod, Socket, _planar, R_FRONT, R_BACK, R_LABEL, solve_grid
from .shapes import Builder, rect, rounded_rect, circle, chamfer_rect

def item_thing() -> Item:
    b = Builder()
    b.box((x0, y0, z0), (x1, y1, z1), mat=0)                 # axis-aligned closed box (mats/regions per side)
    b.prism(outline_ccw_xy, z0, z1, mat=0)                   # extrude a CCW outline along +Z
    return Item(name="SM_CSK_Thing", lods=[Lod(b0, bevel_mm=0.5), Lod(b1), Lod(b2)],
                materials=["M_CSK_Frame", ...], projections={}, sockets=[Socket("Seat", (0, 0, 0)), ...],
                hulls=[((x0, y0, z0), (x1, y1, z1))], cls="ClassCode", budget=600,
                data={"footprint_mm": [w, d, h], "reference": "sheet NN", "notes": [...]})
```

**Builder API** (`shapes.py`):
- `v(x, y, z)`
- `face(ids, mat, region)`: the ids are counter-clockwise seen from outside.
- `fill(loops, mat, region, normal)`: a planar face with holes.
- `loop(outline, z)`
- `box(mn, mx, mat, region, inward, regions={"px"...}, mats={...}, skip=[...])`
- `prism(outline, z0, z1, mat, top, bottom, side, top_mat, bottom_mat)`: a region of `None` leaves that cap open.
- Outlines: `rect`, `rounded_rect(w, h, r, segs)`, `circle(r, segs, cx, cy)`, `chamfer_rect`.

**Geom helpers:**
- `_prism_y(b, outline_xz, y0, y1, mat)`: a prism along Y.
- `_face_out(b, ids, outward, mat)`: winds a planar face to face `outward`, so you don't have to work out the order.
- `_shift_z(b, dz)`
- `_planar(x0, y0, w, h, tile_u, tile_v, mirror_x)`: a print projection.
- `solve_grid(width, depth, clear_h, cls)`: fixture grids.
- Showcase building blocks: `_showcase_dims`, `_slotted_standard`.

**Lod options:**
- `bevel_mm` (plus `bevel_segments`, `bevel_first`) rounds edges sharper than 60 degrees. Use a small bevel on LOD0 for
  hard-surface highlights: 0.3-1 mm, by size.
- `ops=[("DIFFERENCE" | "UNION", builder)]` are exact booleans. **Use them only when the base builder is ONE closed,
  non-self-intersecting shell** (e.g. a prism). A "soup" of overlapping boxes breaks the exact solver.
- `extra=builder` appends parts after the bevel and booleans (small crisp parts, no cuts).

Overlapping closed boxes in one mesh are fine without booleans: posts in a base, for example. Coincident but separate
vertices are not: qa fails them. Sink one part 0.5-1 mm into the other instead of letting faces touch.

**Materials:** slot names `M_CSK_<Name>`. Reuse the existing names where they fit:
- `M_CSK_Frame` (aluminium), `M_CSK_Base` (black), `M_CSK_LED` (emissive);
- `M_CSK_Oak`, `M_CSK_Deck` (cream);
- `M_CSK_Glass`, `M_CSK_PVC`, `M_CSK_Film`;
- `M_CSK_Board` (grey/kraft board), `M_CSK_BoxPrint` (printed dieline);
- `M_CSK_Card`, `M_CSK_Pack`, `M_CSK_SlabBody`, `M_CSK_SlabWindow`.

New names are fine (e.g. `M_CSK_Steel`, `M_CSK_Laminate`, `M_CSK_Rubber`, `M_CSK_Acrylic`). List every new one in
your report: the lead adds their Unreal instances.

**Print UVs** (spec 4.1):
- A face region > 0 gets a planar projection from `projections`, and everything else is auto-unwrapped.
- Tiles: front (0,0), back (1,0), label (0,1). Boxes use dieline regions 10+ inside tile (0,0), as in `_dieline`.
- Use prints only where the item carries printed art (packs, boxes, signs, posters, playmat, labels); plain materials
  elsewhere.

**Sockets:** use the spec row's socket column (names exactly), plus `Seat`. Fixtures keep 40 sockets or fewer; use
`Level_*` + `Compartment_*` + `PriceTag_*` and a `levels` data list like `item_showcase`, and let `solve_grid` pick
the class grids. Rotations are XYZ degrees, the orientation wanted in Unreal.

**LODs and budget:**
- The budget is the spec's "Tris" column.
- An item of 150 tris or fewer ships LOD0 only (automatic).
- Otherwise give 3 LODs: LOD1 about 25-50% of LOD0, LOD2 about 5-20%, and the silhouette must hold.
- If the reference needs more than the budget, raise it in your module and log why (the pack went 300 -> 1500 for its
  27 ribbed teeth). Don't blow it casually.

**Hulls:** 1-6 boxes (`hulls`) that cover the shape; they become UCX collision. Handheld items get one box, at least
2 mm thick.

## Build, check, look

Commands (cloud: the pip `bpy` module; `$PY` is `/tmp/claude-0/-home-user-Blender-Assets/fe6ca5be-210d-5d38-a7b5-fcee2dacd66b/scratchpad/bpyenv/bin/python`):

```
$PY Scripts/cardshop/cloud/bpy_run.py Scripts/cardshop/build_csk.py -- --no-save --items <key1>,<key2> \
    --out <scratch>/<family> --report <scratch>/<family>/r.json
$PY Scripts/cardshop/cloud/bpy_run.py Scripts/cardshop/tools/csk_shot.py -- OUT.png <scratch>/<family>/<Mesh>.fbx \
    [more.fbx@x,y,z,rx,ry,rz] --view front|back|left|right|top|34|34back --samples 16 --res 1000x700
```

- The build must end `CSK_BUILD PASSED`: house `qa_check` on every LOD, plus kit checks (contain fits, level grids,
  stacks, hashes, deny scan). Fix every failure at its cause: no disabled checks, no skipped items.
- Use your own scratch folder under the scratchpad above (e.g. `.../scratchpad/fam_<family>/`).
- This machine has 4 CPUs shared with another builder: keep renders at 16 samples and 1000 px or less.
- Flat-lying items (cards, sleeves, mats, signs lying down) need `--view top`.
- The shot tool guesses materials from slot names; it is a shape check.

**Look at every item.** Render it, and compare it with the reference notes (`References/CardShop/REFERENCE_LOG.md`,
your sheets) and the prompt (`WorkFiles/cardshop/CARDSHOP_REFERENCE_PROMPTS.md`). The user's bar is "match the
reference to the T":
- real forms as real geometry, crisp bevels;
- nothing invented that the reference doesn't show;
- dimensions from the spec (M wins; the picture wins over an E value, and you log it).

Sheets 0-7 are on disk in `References/CardShop/` (the style anchor `csk_style_anchor.png` sets the kit's palette and
materials). Sheets 8-36 are not on disk yet: work from their notes in the log.

## Report (`WorkFiles/cardshop/families/<family>.md`)

Keep it short and factual:
- a table of each mesh: key, LOD tris, budget, qa result, sockets;
- deviations from the spec, and why;
- new material slot names;
- anything not built and why;
- open questions for the user;
- the render file names.
