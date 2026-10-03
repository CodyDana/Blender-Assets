# Throwing Needles (senbon): Unreal Engine 5.8 static meshes

Two original throwing needles (hari-gata, the needle-type bo-shuriken) in the pack's blackened steel with bright
ground points. They are built at real size in Blender 5.2 to the design in `WorkFiles/senbon/senbon_spec.json` and its
design sheet.

- **SM_Senbon_Needle** is 130 mm long, round and double-pointed. It swells from Ø 2.3 mm at the shoulders to Ø 2.8 mm
  at the middle and has two 15 mm cone points. It is thrown in volleys of three.
- **SM_Senbon_Heavy** is 170 mm long and round. It thickens from Ø 2.8 mm at the tail to Ø 4.5 mm behind a 22 mm point
  with three flat ground facets. The tail has a 45 mm cotton thread wrap (Ø 4.2 mm) between two Ø 4.6 mm bindings, and
  the wrap colour can be changed.

## Files

| File | What it is |
|---|---|
| `SM_Senbon_Needle.fbx` | The volley needle: 3 LODs, 1 collision hull, 1 material slot (steel) |
| `SM_Senbon_Heavy.fbx` | The heavy needle: 3 LODs, 1 collision hull, 2 material slots (steel, wrap) |
| `*.sockets.json` | Sockets, LOD screen sizes, mass, embed and throw values for each mesh (see Import, step 2) |
| `Textures/T_Senbon_Needle_{BC,ORM,N}.png` | The needle's steel maps, 2048 x 256 |
| `Textures/T_Senbon_Heavy_{BC,ORM,N}.png` | The heavy needle's steel maps, 2048 x 256 |
| `Textures/T_Senbon_Heavy_Wrap_{BC,ORM,N}.png` | The thread wrap's maps, 1024 x 256 (UV tile u 1..2, Wrap addressing) |
| `Textures/Recolour/T_Senbon_Heavy_Wrap_Detail16.png`, `recolour_maps.json` | The wrap's 16-bit linear recolour detail and its constants, used by the pack's material build |

BC is sRGB. ORM is linear: R is ambient occlusion (a Cycles bake), G is roughness and B is metallic (1 on steel, 0 on
the wrap). N is a **DirectX** normal map (leave Flip Green OFF). All maps are power-of-two and get full mip chains.
The steel normal maps are nearly flat: the shapes are real geometry, and the maps carry only grind lines and fine
scratches. The wrap's normal map carries the thread: a right-hand, single-start helix with a 0.6 mm pitch, and square
turns on the bindings.

## Size, triangles, LODs

| Mesh | Length | LOD0 / LOD1 / LOD2 triangles | Sides per LOD | LOD screen sizes |
|---|---|---|---|---|
| `SM_Senbon_Needle` | 130 mm | 360 / 80 / 36 | 12 / 8 / 6 | 1.0 / 0.13 / 0.0455 |
| `SM_Senbon_Heavy` | 170 mm | 618 / 198 / 78 | 12 / 9 / 6 | 1.0 / 0.17 / 0.0595 |

Every LOD is generated at its own side count, not decimated. Both meshes switch LOD at about 0.89 m and 2.54 m at 90
degrees horizontal field of view, the same distances as the rest of the pack.

- At each switch the shape changes by at most 0.17 px p99 at 1080p.
- The heavy needle's LOD1 has 9 sides so that its three facets stay equal.
- Nanite is off.

A needle 2.8 mm thick is less than 1 pixel wide beyond about 2.7 m at 1080p. In flight, use a trail effect from the
`Trail` socket and a small glint at `Tip` to make it readable. Do not make the mesh thicker.

## Pivot, sockets, physics

The pivot is the centre of mass. On the needle that is the middle. On the heavy needle it is 93.7 mm from the butt,
8.7 mm ahead of the middle, so the needle flies point-first. +X points toward the point on the mesh and on every
socket.

| Socket | Needle (cm from pivot) | Heavy (cm from pivot) | Use |
|---|---|---|---|
| `Grip` | 0 | -6.37 | Hand attach (use the inverse of the socket). The needle is held across the fingers at its middle |
| `Tip` | +6.5 | +7.63 | Impact effects, the embed calculation, the projectile root |
| `Trail` | -6.5 | -9.37 | Trail or ribbon effect |
| `Throw` | 0 | 0 | Launch point (equals the pivot) |
| `Embed` | +5.0 | +6.13 | Put this socket on the surface hit point to bury the tip 15 mm |

- **Mass:** set Mass Override in kg to the sidecar `mass_kg` value: 0.00462 kg for the needle and 0.01193 kg for
  the heavy needle (steel at 7.85 g/cm³, plus the cotton wrap).
- **Collision:** each mesh has one convex hull, an octagonal prism closing to the point, with 24 and 17 vertices.
  - Unreal takes the centre of mass from the hull. For the heavy needle the hull's centre is 1.23 cm behind the
    pivot, so set **Center Of Mass Offset** to (+1.23, 0, 0) cm if dropped needles should balance correctly.
- **Dropped needles:** turn CCD on, and use Angular Damping 0.5-1.0 to stop a round needle rolling forever.
- **Needles in flight:** these never simulate physics. Use `ProjectileMovement` on a 0.5 cm sphere root placed at
  `Tip`, with Rotation Follows Velocity, and offset the mesh by -`Tip`.
- **Embedding:** the needle goes in along its incoming velocity, not the surface normal.
  - Suggested depths: 10-20 mm in wood, 25-40 mm in straw, 20-35 mm in a character (attach to the hit bone).
  - It does not stick in stone or metal, or when it hits more than 70 degrees off the surface normal.

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
3. Assign the material instances:
   - `SM_Senbon_Needle`: slot 0 `MI_Senbon_Needle_Steel` (on `M_Steel_Master`);
   - `SM_Senbon_Heavy`: slot 0 `MI_Senbon_Heavy_Steel` (on `M_Steel_Master`) and slot 1 `MI_Senbon_Heavy_Wrap` (on
     `M_Fabric_Master`, recolourable; the default is #373532, the kunai grip colour).

If you import the textures yourself:
- BC: sRGB ON, Default;
- ORM: sRGB OFF, Masks;
- N: sRGB OFF, Normalmap, Flip Green OFF;
- Detail16: sRGB OFF, Grayscale.

## Naming

The assets are named `SM_Senbon_*` inside the project. "Senbon" is a generic Japanese word for a needle. The design is
the pack's own: a generic historical needle form, with no marks or crests.
