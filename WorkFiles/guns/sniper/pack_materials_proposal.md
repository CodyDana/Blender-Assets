# SR-01 pack materials: proposal (UNBUILT)

**Status: proposal only. Nothing is built.** This W6 run did not edit `Scripts/unreal/materials/` or
`material_spec.json`, did not run `run_build.sh` or `np_lock.py claim`, and ran no Unreal. The reason: this branch
(`claude/sniper-sr01`) is not merged. If SR01 were built into the shared validation project's `/Game/NinjaPack`,
every other chat's pack build would stop at "clean" until the branch merged (this happened with the AR-01). The gun
chat, or a later session holding the `PackMaterials` lock, can apply this after the merge.

Files:
- `pack_materials_proposal.json`: the exact additions, written by `materials/make_pack_proposal.py`. It has
  `items[]` (4), `instances[]` (10), `build_map_entries` (recolour_maps, recolour_constants, not_imported),
  `changes_v11_sr01`, `recolour_group`. The field shapes are copied from this branch's SMG01 entries: the same keys,
  checked by the script's run, and no name clashes with existing items or instances.
- `materials/derive_constants_sr01_draft.py`: the proposed `maps/derive_constants_sr01.py`. It is
  `derive_constants_smg01.py` with group SR01, one part (`SR01/Chassis`) and the SR01 paths. It imports
  `derive_constants.fabric_part` unchanged.
- `materials/sr01_recolour_pack_draft.py`: a draft of the pack-schema maps writer, with a pre-check run read-only
  through the pack's own `derive_constants.fabric_part`. Its outputs are in `materials/draft_out/` (the detail map,
  `recolour_maps.json` in schema `ninjapack.recolour_maps/1`, the draft constants, `precheck.json`).

## 1. Items, slots, instances (plan section 0)

| Item | Mesh | Slots (index: slot -> instance, master) |
|---|---|---|
| `SR01` (skeletal, `Meshes/SR01`) | `SK_SR01` + LOD1-3, sidecar `SK_SR01.skeletal.json` | 0 `M_SR01_Metal` -> `MI_SR01_Metal` (`M_Steel_Master`); 1 `M_SR01_Chassis` -> `MI_SR01_Chassis` (`M_Fabric_Master`, Metal From ORM ON) |
| `SR01_Static` | `SM_SR01` (UV0 tiles: Metal 0, Chassis 1, merged mag -1; Wrap addressing) | 0 Metal, 1 Chassis, 2 `M_SR01_Mag` -> `MI_SR01_Mag` (`M_Fabric_Master`, MFO ON) |
| `SR01_Mag` | `SM_SR01_Mag` | 0 `M_SR01_Mag` -> `MI_SR01_Mag` |
| `Att_Scope_LongRange` (`Meshes/SR01`) | `SM_Att_Scope_LongRange` (Body tile 0, Lens tile 1) | 0 `M_Att_Scope_Body` -> `MI_Att_Scope_LongRange_Body` (`M_Steel_Master`); 1 `M_Att_Scope_Lens` -> `MI_Att_Scope_LongRange_Lens` (`M_Steel_Master`, opaque glossy) |

- The slot names and order were read from the shipped FBX (headless probe, `scratch/w6/slots_probe.py`).
- Every instance has its `_Base` (textures and matched settings); the buyer-facing instance overrides only colours.
- **Texture kinds.** BC sRGB, ORM `ORM_rgb` with the N-roughness composite as on the SMG, N DirectX, Detail16
  linear.
  - Chassis and Mag BC are proposed as `BC_BC7`. The SMG's polymer needed BC7 to meet P1 (BC1 was 5 to 8 levels off).
    Measure BC1 first and keep it if it is within 2 levels.
  - Metal and Scope BC use BC1.
- The five `*_Masks.png` maps are `not_imported`. They are shipped for a buyer's own wear material; no pack master
  samples them.

## 2. Recolour group SR01 (the OD paint is the user colour)

- **One member, `M_SR01_Chassis`.** The magazine set has no OD paint: Masks A = 0 on every texel, and it is 87 %
  phosphated steel and 13 % polymer. So `MI_SR01_Mag` is baked-only. Plan 0 grouped it with the chassis materials;
  that does not hold for the shipped maps.
- **The shipped `Recolour/recolour_maps.json` is the W2 stub** (`sr_recolour.py`, not the pack schema). The build
  needs a pack-schema map. The draft writer produces it: detail = normalised luminance over the OD texels
  (Masks A = 1) at 2048, using the same `detail()` as the SMG. Its pack-step version would replace the stub and
  `T_SR01_Chassis_Detail16.png`. That is a texture-only change; the meshes are not touched.
- **Draft pre-check** (`materials/draft_out/precheck.json`, through the pack's own code, read-only):

| Check | Result |
|---|---|
| `derive_constants.fabric_part` gates (v1 contract at mip 0 and every mip, guards inactive, mip drift within 2 %) | PASS |
| Black floor / knee | PASS (Colour max 0.0807 > 0.01; default albedo max 0.12 < 0.85) |
| 13-colour stress (10 + tan / OD / FDE) on the OD texels | PASS on all 13 |
| PNG round trip of the 16-bit map | exact |
| Default recolour path vs the shipped BC on the OD (P1 bar p99.9 <= 2 levels) | **FAIL: p50 0 / p99 1 / p99.9 4 levels** (chip and rub hue that one Colour flattens) |
| Draft constants | Colour (linear) 0.0788 / 0.0807 / 0.0576; Detail Bias 0.634, Scale 0.884, Mean 1.0, Lightest 0.6 |

  Because of the 4-level miss, the shipped `MI_SR01_Chassis_Base` has **Use Original Baked Colours ON**, as on the
  SMG: the default look is the BC itself, and P1 is then a BC-compression check.

### D1: a decision the builder must make first (the master has no mask input)

The plan wants the user colour on the OD paint only. Masks A marks exactly that: 8,165,957 of the set's 11,406,727
painted texels (71.6 %). The other 28.4 % of the Chassis set is black anodize (bipod, hardware), polymer (grip) and
rubber (butt pad). `M_Fabric_Master` has no mask input. When a buyer switches Use Original Baked Colours off, the
recolour path tints the whole set. Metal From ORM lerps back to the BC only on metallic or bright texels
(`max(ORM.B, saturate((lum(BC) - 0.2) x 5))`), and the dark anodize, polymer and rubber are neither. So a recolour
would also paint the grip, the pad and the bipod.

- **D1-a (no master change; recommended for the first build):** ship the OD as baked (Use Original Baked Colours
  ON). Document recolour as "OD paint only, after D1-b". The buyer-facing `MI_SR01_Chassis` still has Colour, but
  the README says the switch is not yet safe on this item.
- **D1-b (real recolour):** add one static switch to `M_Fabric_Master`, for example `Recolour Mask From Masks A`
  (default OFF, so every other item compiles to the same instructions). When ON, it samples a Masks map and returns
  `lerp(BC, tinted, Masks.A)`. This is a masters change, so it needs the `PackMaterials` lock, the "every other entry
  unchanged" dump comparison, and the Masks map moving from `not_imported` to imported (linear) for SR01 only.
- **Not acceptable:** moving the rubber, polymer and anodize to another slot. That re-exports the W5-verified meshes.

## 3. Gates the build must pass (P1-P4, as the SMG measured them)

| Gate | Bar | Notes for SR01 |
|---|---|---|
| **P1** default capture = shipped BC (UV-plane capture, the pack's twin) | p99.9 <= 2 levels | per set: Chassis (4096), Mag (1024), Metal and Scope reported. BC7 fallback for Chassis and Mag |
| **P2** recolour path at the default vs the twin | p99.9 <= 1, mean <= 0.3 | the OD member only |
| **P3a** 13-colour stress vs the twin | p99.9 <= 1 level per colour | 13 captures. **P3b** (the pack's v3 Spearman gate) is reported; the SMG missed it at near-black only |
| **P4** mip drift (mip 4 vs box-filtered mip 0) | <= 2 % | Chassis Detail16 2048 |
| Additions only | removing the SR01 keys gives back the spec before | `add_sr01_to_spec.py`, as on the SMG |
| Every other entry unchanged | dump vs the last main build | instances +10, meshes +4, textures +21 (+1 Detail16); nothing removed |
| Build | `run_build.sh sr01_<date>`: preflight, maps_check, import_meshes, import_textures, clean, build, assign, verify, render | 0 compile failures; every SR01 LOD section resolves to the pack instances; SK_SR01 arrives with 4 LODs, 20 sockets, 8 clips, PHYS_SR01, bounds extension |
| Lit frames looked at | the twin's three UV tiles resolve; scope on the rail | |

Rough cost when it runs: $10-20 (plan section 9's W6 row; the SMG's pack stage was in that range).
