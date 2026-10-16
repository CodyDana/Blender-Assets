# Bake-vs-PNG row-order scan (2026-10-16, branch claude/bake-png-roworder-scan, read-only)

This follows K4_NOTE.md and fade7ed2. Bake arrays from `img.pixels` / `np.save(<Set>_{ids,pos,nrm,edge,ao}.npy)` are
**bottom-up** (Blender row 0 = V 0). PNGs read by PIL / `rc.png_read` are **top-down**. The gun writers
`gunlib/paint.py write_png / write_png16` flip on write (`[::-1]`, line 259 comment). Any compare of a bake array with a
PNG therefore needs exactly one `[::-1]` on one side. The scan used grep for `np.load(`, `.pixels`, `Image.open(`,
`png_read`, `[::-1]` and `flipud` over all of `Scripts/`, then read only the functions that mix the two sources.

## Places that mix bake/raster arrays with PNGs

| file:function | compares | aligned? | evidence | gate / metric fed | owner |
|---|---|---|---|---|---|
| guns/sniper/sr_closeup.py:maps_metrics | Metal/Scope ids+pos .npy vs T_SR01_Metal_ORM, Scope_Body_ORM, Scope_Lens_BC PNG | **yes (fixed)** | fade7ed2 flips the arrays `[::-1]`, plus the registration guard (bolt metal > 0.5, receiver < 0.05) | K2, K4, K5 close-up gates | sniper |
| guns/sniper/sr_recolour.py:main | BC PNG vs Masks PNG only | yes (n/a) | no bake array; both are PIL top-down | recolour Detail16 + recon gate | sniper |
| guns/sniper/sr_paint.py (paint + `masks_A_on_non_od_texels`) | bake .npy vs arrays painted in bake order | yes | all in bake order; PNGs written via PT.write_png (flip once) | paint_report, sr_recolour non-OD check | sniper |
| guns/smg/smg_recolour.py:member | `<Set>_ids.npy` vs T_SMG01_*_BC PNG | yes | line 102: `np.load(...ids.npy)[...,0][::-1]` | recolour cover / Colour / Detail16 | gun chat (smg) |
| guns/smg/smg_paint.py | bake .npy vs painted arrays | yes | bake order throughout; PT.write_png flips | SMG textures | gun chat (smg) |
| guns/smg/smg_maps_vs_clay.py:consts | whole-texture medians of BC/ORM PNG | yes (n/a) | no bake array; medians don't depend on row order | maps-vs-clay constants | gun chat (smg) |
| guns/rifle/rifle_recolour.py | Furniture_ids.npy vs T_AR01 BC PNG | yes | line 108: ids `[::-1]` ("paint writes [::-1]") | rifle recolour | gun chat (rifle) |
| guns/rifle/rifle_stage34_gates.py (realism-tex gate) | Metal_ids/nrm/pos .npy vs T_AR01_Metal_ORM + BC PNG | yes | lines 49-50 flip the PNGs `[::-1]` to bake order; ids/nrm/pos stay bake order | "realism-tex: no blown wear masks", dust-cover crown check | gun chat (rifle) |
| guns/rifle/rifle_look_polish.py:load | ids/pos/nrm .npy vs T_AR01 BC + ORM PNG | yes | lines 41-42 flip the PNGs `[::-1]` before the `[v]` mask | look-polish zone medians | gun chat (rifle) |
| guns/rifle/rifle_paint.py (+ rifle_bake Furniture_ckn/ckm) | bake .npy (ckn/ckm via BK.read_image) vs painted arrays | yes | all bake order; PT.write_png flips | AR-01 textures | gun chat (rifle) |
| guns/rifle/rifle_texrender.py | `im.pixels` readback / write | yes | line 150 `[::-1]` "top-down rows"; line 221 flips back before `img.pixels[:] =` | texture renders | gun chat (rifle) |
| unreal/materials/maps/recolour_common.py:png_read / load_png_bpy | helpers | yes | png_read is top-down; load_png_bpy flips `img.pixels` `[::-1]` (doc: row 0 at the top) | all recolour builders | materials |
| unreal/materials/maps/make_kunai_wrap_detail.py:bake_wrap | bake image_pixels vs Detail16 PNG read-back | yes | line 83-84 flip every bake array `[::-1]`; read-back via rc.png_read | kunai wrap Detail16 round-trip | materials |
| Katana/katana_recolour.py (read_bc, saya_lacquer_mask, gcov) | rasterised masks + paint_grip_cov.npy vs BC PNG | yes | line 87 `m[::-1]`, line 185 `cov[::-1]`; katana_tex/saya_tex write PNGs with `flip` | katana/saya recolour | other (katana) |
| props/props_lib/bake.py (read, write, verify_transfer) | bake pixels vs written PNG / transfer check | yes | 268 `px[::-1]` to top-down before own write_png; 355 flips back for foreach_set; 446 flips before compare | props bake + transfer verify | other (props) |
| pipeline/textures.py:image_pixels / write_png | bpy in, bpy out | yes | both sides are bpy `pixels` (bottom-up); no PIL | pipeline texture writes | other (pipeline) |

## Result

There are no confirmed row-order bugs outside the one already fixed in `sr_closeup.maps_metrics`, and nothing is unsure.
The rifle uses the opposite convention (it flips the PNG into bake order rather than the bake into PNG order). That is
equally correct. Files outside the guns/materials/props/pipeline scope matched the grep, but they compare only
renders or reference masks with PNGs (no bake arrays): SnowFlower, dojo, MetaHuman, Characters, rocks, armory. I did
not read them function by function.

Suggested hardening (not applied, owners decide): add a registration guard like sr_closeup's to any future gate that
reads per-part texels. For example, the share of metal texels on a known bare part compared with a known painted part.
A mirrored read then fails loudly instead of passing silently.
