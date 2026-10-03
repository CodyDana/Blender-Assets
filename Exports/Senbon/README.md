# Throwing Needles (senbon): Unreal Engine 5.8 static meshes

Two original throwing needles (hari-gata, the needle-type bo-shuriken) in the pack's blackened steel with bright
ground points. They are built at real size in Blender 5.2 (props_lib senbon 1.1.0) to the design in
`WorkFiles/senbon/senbon_spec.json` and its design sheet.

- **SM_Senbon_Needle** is 130 mm long, round and double-pointed. It swells from Ø 2.3 mm at the shoulders to Ø 2.8 mm
  at the middle and has two 15 mm cone points that end in a single sharp apex. It is thrown in volleys of three.
- **SM_Senbon_Heavy** is 170 mm long and round. It thickens from Ø 2.8 mm at the tail to Ø 4.5 mm behind a 22 mm point
  with three flat ground facets. The tail has a 45 mm twisted cotton thread wrap (Ø 4.2 mm) between two Ø 4.6 mm
  bindings, and the wrap colour can be changed.

The materials and the wrap colour are explained in `MATERIALS_README.md`.

## Files

| File | What it is |
|---|---|
| `SM_Senbon_Needle.fbx` | The volley needle: 3 LODs, 1 collision hull, 1 material slot (steel) |
| `SM_Senbon_Heavy.fbx` | The heavy needle: 3 LODs, 1 collision hull, 2 material slots (steel, wrap) |
| `*.sockets.json` | Sockets, LOD screen sizes, mass, embed and throw values for each mesh (see Import, step 2) |
| `Textures/T_Senbon_Needle_{BC,ORM,N}.png` | The needle's steel maps, 2048 x 256 |
| `Textures/T_Senbon_Heavy_{BC,ORM,N}.png` | The heavy needle's steel maps, 2048 x 256 |
| `Textures/T_Senbon_Heavy_Wrap_{BC,ORM,N}.png` | The thread wrap's maps, 1024 x 1024 at 18 px/mm (UV tile u 1..2, Wrap addressing) |
| `Textures/Recolour/T_Senbon_Heavy_Wrap_Detail16.png` | The wrap's lossless 16-bit linear detail map, used by the recolourable wrap material |
| `Textures/Recolour/recolour_maps.json`, `recolour_constants.json` | The wrap's recolour constants (written by the build and the pack's derive step; do not edit by hand) |

BC is sRGB. ORM is linear: R is ambient occlusion (a Cycles bake), G is roughness and B is metallic (1 on steel, 0 on
the wrap). N is a **DirectX** normal map (leave Flip Green OFF). All maps are power-of-two and get full mip chains
(checked in Unreal: 12 mips at 2048 wide, 11 at 1024). In Unreal the ten textures take about 8.3 MiB with mips.

The steel normal maps are nearly flat: the shapes are real geometry, and the maps carry only grind lines and fine
scratches. The wrap's normal map carries the thread: a right-hand, single-start helix with a 0.6 mm pitch, a 2-ply
twist, turns that vary slightly in height and shade, and square turns on the bindings.

## Size, triangles, LODs

| Mesh | Length | LOD0 / LOD1 / LOD2 triangles | Sides per LOD | LOD screen sizes | LOD switches (1080p, 90 deg) |
|---|---|---|---|---|---|
| `SM_Senbon_Needle` | 130 mm | 312 / 80 / 36 | 12 / 8 / 6 | 1.0 / 0.13 / 0.029 | 0.89 m, 3.99 m |
| `SM_Senbon_Heavy` | 170 mm | 618 / 198 / 78 | 12 / 9 / 6 | 1.0 / 0.17 / 0.0595 | 0.89 m, 2.54 m |

Every LOD is generated at its own side count, not decimated. Unreal 5.8.3 imports exactly these triangle counts with
the default build settings (Remove Degenerates ON): every triangle is at least 0.026 mm², far above Unreal's
degenerate threshold. Every LOD is closed.

- At each switch the shape changes by at most 0.17 px p99 (0.26 px max) at 1080p.
- The needle's LOD2 starts at about 4 m, later than the pack's usual 2.54 m: at 2.54 m the 6-sided LOD2 lost visibly
  more of a horizontal needle than LOD1 in Unreal's single frames. LOD1 is only 80 triangles.
- The heavy needle's LOD1 has 9 sides so that its three facets stay equal.
- Nanite is off.

**Seeing a needle at a distance.** A 2.8 mm needle is less than one pixel wide beyond about 2.5 m at 1080p and 90
degrees field of view (the heavy needle's 4.5 mm front beyond about 4 m). Measured in Unreal on single raw frames, a
needle lying across the view keeps at least 23 % of its shaft lit in the worst frame at 2.63 m and 58 % at 2.45 m;
beyond about 3.9 m some single frames show nothing. Averaged over 8 sub-pixel positions (what temporal anti-aliasing
does) it stays continuous to 5 m. So in flight, use a trail effect from the `Trail` socket and a small glint at `Tip`
to make a needle readable, and give embedded needles a cull distance of about 10-12 m. Do not make the mesh thicker.
Unreal's own TSR could not be measured in a headless check: test it in your level (see "Known limits").

## Pivot, sockets, physics

The pivot is the centre of mass. On the needle that is the middle. On the heavy needle it is 93.7 mm from the butt,
8.7 mm ahead of the middle, so the needle flies point-first. +X points toward the point on the mesh and on every
socket.

| Socket | Needle (cm from pivot) | Heavy (cm from pivot) | Use |
|---|---|---|---|
| `Grip` | 0 | -6.37 | Hand attach (use the inverse of the socket). The needle is held between the fingers at its middle |
| `Tip` | +6.5 | +7.63 | Impact effects, the embed calculation, the projectile root |
| `Trail` | -6.5 | -9.37 | Trail or ribbon effect (on the double-pointed needle this is the rear point) |
| `Throw` | 0 | 0 | Launch point (equals the pivot) |
| `Embed` | +5.0 | +6.13 | Put this socket on the surface hit point to bury the tip 15 mm |

- **Mass:** set Mass Override in kg to the sidecar `mass_kg` value: 0.00461 kg for the needle and 0.01193 kg for
  the heavy needle (steel at 7.85 g/cm³, plus the cotton wrap).
- **Collision:** each mesh has one convex hull that contains every LOD: on the needle an octagonal prism closing to a
  point at each tip (18 vertices), on the heavy needle an octagonal prism closing to the point (17 vertices).
  - Unreal takes the centre of mass from the hull. For the heavy needle the hull's centre is 1.23 cm behind the
    pivot, so set **Center Of Mass Offset** to (+1.23, 0, 0) cm if dropped needles should balance correctly. The
    needle's hull is centred on its pivot.
- **Dropped needles:** turn CCD on, and use Angular Damping 0.5-1.0 to stop a round needle rolling forever.
- **Needles in flight:** these never simulate physics. Use `ProjectileMovement` on a 0.5 cm sphere root placed at
  `Tip`, with Rotation Follows Velocity, and offset the mesh by -`Tip`. A fast needle (25 m/s moves 42 cm per frame
  at 60 fps) is swept by the projectile, so it does not tunnel.
- **Volleys:** three needles fanned about ±4 degrees. For many needles at once, a Niagara mesh renderer (Facing Mode
  Velocity, +X) with server traces for the hits is cheaper than actors; see "Known limits" for the material flag
  this needs.
- **Embedding:** the needle goes in along its incoming velocity (±2 degrees of jitter looks natural), not along the
  surface normal.
  - Suggested depths: 10-20 mm in wood, 25-40 mm in straw, 20-35 mm in a character (attach to the hit bone). Paper
    is passed through.
  - It does not stick in stone or metal, or when it hits more than 70 degrees off the surface normal.
  - Spent needles in a level: an Instanced Static Mesh (cap about 128), shadows on once they are embedded.

## Import (legacy FBX importer)

1. Import each FBX as a Static Mesh with the pack's standard settings:
   - **Convert Scene ON**, **Force Front XAxis OFF**, **Convert Scene Unit ON**, Import Uniform Scale 1.0 (the FBX
     is in metres);
   - **Import Mesh LODs ON**, Combine Meshes OFF;
   - Normal Import Method **Import Normals**, Normal Generation **MikkTSpace**;
   - Auto Generate Collision **OFF**, **One Convex Hull Per UCX ON**;
   - **Generate Lightmap UVs ON**, because the FBX carries only UV0;
   - Import Materials OFF, Import Textures OFF.
2. An FBX with LODs cannot carry sockets into Unreal. Run the pack's `ue_import_sockets.py` with each mesh's
   `.sockets.json`: it adds the five sockets at scale 1 and sets the LOD screen sizes above.
3. Assign the material instances (the pack's material build already does this on its copies of the meshes):
   - `SM_Senbon_Needle`: slot 0 `MI_Senbon_Needle_Steel` (on `M_Steel_Master`);
   - `SM_Senbon_Heavy`: slot 0 `MI_Senbon_Heavy_Steel` (on `M_Steel_Master`) and slot 1 `MI_Senbon_Heavy_Wrap` (on
     `M_Fabric_Master`, recolourable; the default is `#373532`, the kunai grip colour).

If you import the textures yourself:
- BC: sRGB ON, Default;
- ORM: sRGB OFF, Masks, **Compression No Alpha ON**;
- N: sRGB OFF, Normalmap, Flip Green OFF;
- Detail16: sRGB OFF, Grayscale (it builds as G16).

## Verified

- Blender build: 32 of 32 build gates pass; `qa_check` 72/72 (needle) and 84/84 (heavy). Silhouette within 0.004 mm of
  the design on both LOD0s; mass 4.61 g and 11.93 g, the heavy's balance 93.70 mm from the butt (design 93.695).
- Unreal 5.8.3, six fresh processes on these exact bytes (import, read-back, Unreal's own FBX round trip, lit renders
  and mip probes, distance visibility): triangle counts equal Blender's on every LOD, every LOD closed after the round
  trip, the hulls convex and equal to the shipped ones (within 0.000003 mm), every LOD inside its hull, sockets equal
  to the sidecars at scale 1, LOD screen sizes exact, every texture's flags and full mip chain as listed above.
- Pack materials: built from code with 0 compile failures; the wrap's default look equals the shipped colour map, and
  white, red and black picks match the material's reference maths within 1 level.

## Known limits

- **Thin at a distance** (see above). Readability in flight is a job for the trail and glint effects.
- **Unreal TSR** (temporal anti-aliasing) shimmer was not measured: a headless capture does not keep TSR history.
  Check a needle at 2.5 m and 4 m in your own level with the spike beside it.
- **Niagara mesh particles:** the pack's steel material does not yet have "Used with Niagara Mesh Particles" turned on.
  If you fire needles from a Niagara system, tick that flag on `M_Steel_Master` (and `M_Fabric_Master` for the heavy
  needle's wrap) and save, or the cooked game draws them with the default material.
- **The heavy needle's flat facets** reflect one direction of the world each, like any ground flat: under a bright
  studio light they can look darker than the black body. That is how polished flats behave; the round needle's cones
  always catch a highlight.
- **Blackened steel in sunlight** reads lighter and more neutral than indoors; it is the same finish as the pack's
  spike and kunai.

## Naming

The assets are named `SM_Senbon_*` inside the project. "Senbon" is a generic Japanese word for a needle, but as a name
for a throwing needle it is strongly tied to one anime franchise, so a store listing may prefer "Throwing Needles
(hari-gata)". The design is the pack's own: a generic historical needle form, with no marks or crests.
