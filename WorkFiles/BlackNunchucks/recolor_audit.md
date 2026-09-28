# Recolor implementation audit

Read-only review of the shipped asset pipeline, 2026-09-22. This document records design findings and proposed gates; it is not an engine verification report.

## Findings

- The saved asset has 16 logical mesh parts at each of three LODs. UV0 is a unique atlas; geometry can retain a single material while masks select individual parts.
- `build.py` packs analytic charts once and reuses their rectangles across all LODs. `resolve_chain.py` explicitly hashes topology and both UV layers before and after chain changes, so the resolution pass does not invalidate those rectangles.
- **Eye end caps use different rectangles at different LODs:** `_end56` for LOD0, `_end40` for LOD1, and `_end28` for LOD2. `_end0` is shared. All charts are present in `build_report.json`. Rasterizing only LOD0 leaves later LOD end caps without masks. Associate every chart by part prefix or rasterize the union of all LOD UVs.
- Chart padding is 32 pixels per side at 4K, normally 64 pixels between neighbors. Weld strips are only about 174 × 8 pixels before padding. Mask generation must preserve padding and test mip behavior, especially for welds.
- Four RGBA masks provide 16 channels without introducing extra mesh material slots. Preserve alpha, disable sRGB, use mask/data compression, and keep samplers linear rather than color samplers in Unreal.
- Fill chart rectangles plus padding with exclusive labels, or use a nearest-label dilation. Independent overlapping binary dilations can produce mask sums greater than one. A summed weighted tint shader should never double-count overlapping part labels.
- Source grip albedo averages about RGB 27/30/31 in 8-bit sRGB; direct multiplication cannot make a bright grip. A neutral detail image should derive variation in linear space, not simply multiply or normalize sRGB bytes. Normal and roughness already contain much of the grip grain and must remain connected.
- Keep the original baked base image and a tint amount default of zero for every part. Then the untouched appearance can be reproduced exactly without depending on a reconstructed black tint. Bright tint should replace pigment using neutral detail; it should not multiply the near-black original pigment.
- Unchanged ORM means a colored metal cap stays metallic and a colored grip stays dielectric. This is appropriate for recoloring; replacement ORM and normal texture parameters support reskins that change finish.
- The existing GLB validator expects a directly exportable Principled PBR texture graph. Blender/Unreal recolor arithmetic is not an exchange-format shader. Preserve a portable baked material for FBX/GLB or temporarily swap it only during export, and label the dynamic master material as Unreal-specific.
- `package.py` currently requires chain clearance reports to match the entire blend SHA. Editing only material data changes that SHA. Do not silently certify a changed asset with stale provenance; record exact geometry/UV/skin/skeleton invariants and a new source hash, or rerun the dependent checks.

## Required validation gates

1. Record before/after hashes per object covering local/world vertex coordinates, polygon indices, every UV loop, object transforms, skin weights/group names, armature modifier target, and bone hierarchy/rest matrices. Geometry/rig invariants must remain byte-identical for all 48 meshes.
2. For all 16 parts at every LOD, sample mask bilinearly at triangle vertices, edge midpoints, and interior barycentric locations. Intended channel should be 1 and every other channel 0 at full resolution, allowing only numeric/quantization tolerance. Include every eye end cap and weld. Report minimum intended value and maximum unintended value per part/LOD.
3. Verify source mask pixels are exclusive (sum of the 16 channels is 0 or 1), maps are power-of-two, and RGBA channel routing agrees with a written manifest. Inspect representative downsampled mip levels for unintended part influence.
4. Check the tint algebra on image samples: all amounts 0 returns original BaseColor exactly; changing only part P changes no samples assigned to Q; amount 1 uses neutral-detail × requested linear color for P. Include bright red/white on each grip and independent colors on adjacent chain links.
5. In Unreal, import the exact hashed FBX/textures, inspect texture sRGB/compression/alpha settings, create and compile the master, save the MI examples and mesh assignments, and verify the material has no compile errors. Confirm the same material works on all three imported LODs.
6. Create a Dynamic Material Instance and set/read individual color and amount parameters. Capture a rendered example with visibly different left/right grips and chain colors. A parameter readback alone cannot prove mask isolation; pair it with the UV/mask test and a rendered result.
7. Reopen the Unreal project in a fresh process and verify saved parent/texture parameters, static or skeletal mesh assignments, LOD counts, and default appearance. Record runtime parameter mutation separately from editor save/reload.
8. Package the Unreal Content assets plus project/config or clear migration instructions, recolor masks/detail map, parameter mapping, updated Blender preview, and reports. Hash-check archive contents; retain the default black appearance and an explicit per-part customization example.

## Scope of evidence

These checks can establish working material recoloring and unchanged authored mesh/rig. They do not establish game-specific inventory, network replication, animation, or physical chain behavior.
