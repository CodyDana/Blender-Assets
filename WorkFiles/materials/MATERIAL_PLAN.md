# Pack materials and recolour: survey and design

**Date:** 2026-09-26. **Role:** survey and design, the first phase of workflow `pack-materials-recolour`.
**Companion:** `WorkFiles/materials/material_spec.json` holds every item, slot, texture, default, parameter and gate in machine-readable form. The build copies it to `Scripts/unreal/materials/material_spec.json` and uses that copy as the source of truth.
**Survey evidence:** `WorkFiles/materials/survey/`. It holds `map_stats.json`, `recolour_headroom.json`, `twin_prototype_f050.json`, the Unreal probe (`probe/`), `exports_sha256_at_survey_2026-09-26.txt` and `check_exports_frozen.sh`.

The user's requirement: *"i want to provide the option for the user to easily change the color if they'd like"*, and *"its fine to have a default color"*. So:

- Every item looks exactly like its Blender look out of the box.
- Each recolourable part has ONE obvious colour parameter on its Material Instance.
- A light or saturated colour recolours cleanly.

---

## 0. Decisions in one screen

| # | Decision | Why |
|---|---|---|
| D1 | **Three masters:** `M_Steel_Master` (7 steel slots), `M_Fabric_Master` (kunai wrap, smoke bomb cloth, hat straw, hat cloth), `M_PaperInk_Master` (paper bomb). **Five functions:** `MF_TintDetail`, `MF_AlbedoRollOff`, `MF_NormalStrength`, `MF_LetteringBand`, `MF_InkDerive`. **Twelve instances** `MI_<Item>_<Part>`, plus one optional preset. | This is the smallest set that covers metal, woven fibre and printed paper. Straw is a woven fibre with a detail map and a specular mask, so it shares the fabric master. |
| D2 | **The colour parameter is the part's MEAN colour** (`Colour`, `Paper Colour`, `Black Ink Colour`, `Red Ink Colour`). The steel gets an optional `Steel Tint` multiplier (white = as shipped). | This is the black hat's proven semantic ("Tint = the part's MEAN colour"). Whatever colour the buyer picks is what the part reads as. |
| D3 | **Fabric detail is sampled from NEW 16-bit linear greyscale maps** (`*_Detail16.png`, TC_Grayscale, sRGB OFF, G16). For the smoke bomb and the hat these are lossless re-encodings of the shipped sRGB Detail. For the kunai wrap the map comes from a float bake. | Engine source (`Texture.cpp`, "GrayscaleSRGB is off on all targetplatforms") and the probe show that a G8 + sRGB texture is rebuilt as **BGRA8, 4 bytes per texel**. The shipped 4096 smoke-bomb Detail would cost about **85 MiB** with mips; the smoke-bomb report's "~21 MiB" is wrong. G16 costs 2 bytes, decodes exactly and builds its mips in linear light. One sampler type (LinearGrayscale) then serves all four parts. |
| D4 | **Light colours soften the detail automatically**, with an exponent derived from the colour's headroom. At the default colour this is provably the identity. A hue-preserving roll-off above 0.85 follows. | The dark parts' detail spans **up to 13.8 times** the mean (smoke bomb). At a plain multiply with white 0.75, **20 % of the smoke-bomb texels exceed 1.0** (`recolour_headroom.json`). The softening removes that clipping and keeps the detail. |
| D5 | **Paper bomb = a linear layer decomposition**, not a tint. Two new maps (`T_PaperBomb_PaperDetail`, `T_PaperBomb_InkWeights`) hold the per-texel weight of the paper, wet/dry black ink and wet/dry/pooled red ink. Dry and pooled colours are derived from the ink colour. The decomposition is exact at the defaults. | The shipped `_M.B` is `max(red, black)`: one channel for two inks, and no paper detail. A luminance-only tint fits the paper and the black ink, but fails the red at the pools (dE76 p99 **17.4**). |
| D6 | **New maps go in `Exports/<Item>/Textures/Recolour/`**, a new subfolder with a `recolour_maps.json`. No existing file moves. | The props texture importer **fails** on any unknown suffix in the folder it scans (`glob("*.png")`, non-recursive). A new PNG in `Exports/PaperBomb/Textures/` would break the paused paper bomb's own Unreal check when it resumes. |
| D7 | **Content root `/Game/NinjaPack/`** is a working name. No asset name contains it, so the user's final pack name is a folder rename. | The pack name is the user's call. |

---

## 1. Scope and frozen state (verified 2026-09-26, before any work)

`bash WorkFiles/materials/survey/check_exports_frozen.sh` prints `baseline files identical=63 differing_or_missing=0` and exits 0. It compares against:

- **Shuriken:** `WorkFiles/shuriken/regression/post_kunai_plain/SHA256SUMS.txt`. Its `export/` and `textures/` entries map to `Exports/Shuriken/` and `Exports/Shuriken/Textures/`.
- **Smoke bomb:** `WorkFiles/smokebomb/regression/post_smoke_bomb/SHA256SUMS.txt`.
- **Black hat:** `WorkFiles/blackhat/regression/post_black_hat/SHA256SUMS.txt`.
- **Paper bomb:** `WorkFiles/paperbomb/paused_2026-09-21/SHA256SUMS_exports.txt`.
- **Survey snapshot:** `WorkFiles/materials/survey/exports_sha256_at_survey_2026-09-26.txt`, which also covers `Exports/PaperBomb/README.txt`. No older baseline lists that file.

The SUMS files are CRLF; strip `\r` before you parse them. The script also lists every NEW file under the four export folders. The final phase re-runs it and must exit 0.

Also unchanged:

- `Assets/Shuriken.blend` (sha256 `f712b421…`, equal to the post_kunai_plain baseline).
- The paper-bomb art modules: `paperbomb_art.py`, `bake.py`, `atlas.py`, `spec.py`, `paper_material.py` and `build_paper_bomb.py` are byte-identical to `WorkFiles/paperbomb/paused_2026-09-21/Scripts_props/`. Only `ue_import_textures.py` differs, by the Detail intent.

Untouched and out of scope: `Exports/BlackCloak/`, anything JinMuWon, MetaHuman/MH_*, BlackNunchucks (Codex's; I read its recolour script for API lessons only). No lock was claimed or released.

Found running during the survey and left alone: one `blender.exe` (pid 32016, started 03:50, not mine) and the other session's two `UnrealEditor.exe`.

---

## 2. Survey per item

Every number below was measured on the shipped PNGs with Blender 5.2 numpy (`survey/map_stats.json`). "Linear" means sRGB-decoded.

### 2.1 Shuriken steel: 6 stars and the kunai blade (slot 0 `M_Shuriken_Master`)

| Map | Size | Unreal import | Content |
|---|---|---|---|
| `T_Shuriken_<Form>_BC`, `T_Kunai_Plain_BC` | 2048² (spike 2048×512) | sRGB ON, TC_Default (BC1) | metal F0 colour: coat linear ≈0.097 faintly violet; polished band 0.42; satin 0.10 |
| `..._ORM` | same | sRGB OFF, TC_Masks, no alpha | R AO, G roughness (coat 0.34, polish 0.22, satin 0.47), B metallic (1, rust specks 0) |
| `..._N` | same | TC_Normalmap, flip green OFF | DirectX; dish + scratches + pits |

- **Contract.** From `shuriken_lib/bake.py` `preview_material`, which the gallery renders through: *"BC (sRGB) -> Base Color, ORM G -> Roughness, ORM B -> Metallic, N (DirectX) -> green flipped back to OpenGL -> Normal Map… AO is not used: Cycles computes occlusion itself; Unreal uses the R channel for indirect light only."* Specular is the Principled default (IOR level 0.5), which only matters on the rust specks.
- **Not recolourable** (the pack's look). Optional `Steel Tint` (white = exact) and `Roughness Adjust` (0 = exact).
- **Quirk (shipped, frozen).** The six stars' unused atlas texels are 0 in BC and ORM (`fill_unused` is off; only the spike and kunai fill). Far mips blend roughness 0 and AO 0 into island borders. The Blender gallery shares this, so there is nothing to do except watch for edge glints at distance in V4.

### 2.2 Kunai wrap (slot 1 `M_Kunai_Wrap`): recolourable, NOT tint-ready

- **Maps.**
  - `T_Kunai_Wrap_BC/_ORM/_N` are 1024² in **UV tile u 1..2**. Wrap addressing reads the same texels.
  - `T_Kunai_Wrap_Natural_BC` is the undyed option.
  - `T_Kunai_Lettering` is 1536×256 greyscale and blank.
- **BC.** Mean linear (0.0374, 0.0348, 0.0321). Luminance p0.1 0.0155, p99.9 0.089, max 0.15 (fibre flecks). Only **79 distinct stored levels**, so dividing this BC would band. A float bake is required.
- **ORM.** G 0.74–0.98 (mean 0.859), B 0, no alpha.
- **Contract.** `kunai_wrap.py` bakes `M_Kunai_Wrap` with `Dye = 0`: DARK (0.042, 0.039, 0.036) × a value recipe (crest burnish, crevice, fade, patches, grime, weave), mixed toward FIBRE (0.150, 0.142, 0.126) at flecks and fray.
- **The luminance-only tint model fits it.** On the shipped BC, `mean × Y/Ymean` gives dE76 mean 0.19, p99 0.77. One greyscale detail map is therefore enough.
- **Shading the Blender look depends on that a stock Unreal material would not reproduce.**
  - `wrap_preview_material`: **Sheen Weight 0.35, Sheen Roughness 0.35, Sheen Tint (0.62, 0.60, 0.56)**. The docstring says *"cloth catches a grazing sheen … use Unreal's CLOTH shading model (fuzz) for the same read."*
  - Specular is the Principled default, 0.5 constant, with no mask.
  - The lettering composite, verbatim from `References/Kunai/LETTERING_HOWTO.md` §5:
    ```
    LettUV = (UV - Rect.min) / (Rect.max - Rect.min)   // Rect in UNREAL UV0: u 1.1328125–1.8359375, v 0.61898509–0.73617259
    Ink = T_Kunai_Lettering(LettUV).R * Inside          // sampler Clamp
    BaseColor = lerp(Wrap BC, InkColour, Ink); Roughness = lerp(ORM.G, InkRoughness, Ink)
    ```
    InkColour is (0.62, 0.56, 0.44) and InkRoughness is `INK_ROUGHNESS` = 0.62 in code (the how-to rounds it to 0.6). The shipped mask is blank, so Ink = 0 and nothing changes.
- **Undyed option.** It is **not** a recolour of the dark wrap: natural/dark luminance ratio is 6.2–9.2 (p1–p99), correlation 0.86. It ships as an optional baked-colour preset, `MI_Kunai_Plain_Wrap_Undyed`.

### 2.3 Smoke bomb (slot `M_SmokeBomb`): recolourable, tint-ready

- **Maps.** BC 4096 (sRGB), Detail 4096 (8-bit grey, sRGB-encoded linear detail, 253 levels), ORM 2048 **RGBA**, N 2048.
- **Contract, verbatim from the sidecar.**
  - `"BaseColor": "T_SmokeBomb_Detail.R x Tint (Tint default = tint_linear; equals T_SmokeBomb_BC at the default Tint, at every mip)"`, with Tint default linear **(0.630803, 0.532934, 0.481121)**.
  - `"Specular": "0.5 x T_SmokeBomb_ORM.A"`, with *"Do NOT use a constant Specular: 0.5 greys the cloth (p50 +53 %, p10 +111 %) … the look depends on this pin"*.
  - Roughness ORM.G, Metallic 0, AO ORM.R, Sheen 0, *"Default Lit … no Cloth/Fuzz layer"*.
- **Survey check.** Detail × Tint reproduces the BC with **0 stored-level difference on all 16.8 M texels**.
- **Parameters in the mean-colour form.** mean(d) = 0.072262, so `Colour` = Tint × mean = **(0.045583, 0.038511, 0.034767)**, Bias 0, Scale = 1/mean = **13.838558**. Colour × Scale = Tint, so this is the same contract.
- **Hard part.** d/mean reaches p99 6.6, p99.9 11.4, max 13.8, so the recolour needs D4.
- **Dependencies to reproduce:** the specular mask pin (ORM.A, keep alpha → DXT5), Default Lit, no sheen.

### 2.4 Black hat (slots `M_BlackHat_Straw`, `M_BlackHat_Cloth`): recolourable, tint-ready

- **Maps.** Per part: BC, Detail (8-bit sRGB-encoded), ORM **RGBA**, N, all 2048. The cloth's UV0 is in tile U+1 (keep Wrap).
- **Contract, verbatim from the sidecar.** `"saturate(Tint x (DetailBias + DetailScale x T_BlackHat_<Part>_Detail.R)); at the default Tint / Bias / Scale it equals T_BlackHat_<Part>_BC at every mip"`, with Tint = *"the part's MEAN colour"*.

  | Part | Tint (Colour) | Bias | Scale | Specular | mean n | p99.9 n |
  |---|---|---|---|---|---|---|
  | Straw | (0.049758, 0.045438, 0.044183) | 0.058461 | 6.879606 | 0.65 × ORM.A | 0.960 | 6.34 |
  | Cloth | (0.039551, 0.038501, 0.038618) | 0.239278 | 3.800177 | 0.5 × ORM.A | 0.965 | 3.58 |

- **Survey check.** 0 stored-level difference on both parts.
- **Dependencies to reproduce.**
  - The specular masks.
  - The **ORM texture setting** Composite Texture = the part's `_N`, `CTM_NORMAL_ROUGHNESS_TO_GREEN`, power 1. This is per-mip Toksvig roughness, set on the texture asset, not in the graph.
  - Default Lit, no cloth sheen (unlike the kunai wrap).
- **Discrepancy.** The `BLACKHAT_REPORT.md` table lists Bias/Scale straw 0.05858/6.853311 and cloth 0.199741/3.847832, "mean 1.000005". Only the **sidecar** values reproduce the shipped BC, so the report table is stale. Use the sidecar.

### 2.5 Paper bomb (slot `M_PaperBomb`): recolourable (black ink, red ink, paper), NOT tint-ready, PAUSED

- **Maps.** BC, ORM (RGB), N, M, all 2048.
- **`_M` channels (README §4).**
  - **R** is the fibre-fringe alpha, all 0 on this card.
  - **G** is burn *order*: threshold it, never lerp with it.
  - **B** is the ink mask = `max(red, black)` opacity.
  - It is NOT an opacity mask and the shipped master does **not** wire M.
- **Contract (`paper_material.gallery_material`).** Base Color = BC × **ORM.R** (*"AO into base colour, as a UE master does"*); Specular IOR Level 0.5 at IOR 1.5; Roughness ORM.G (paper 0.86, ink 0.72); Metallic 0; N DirectX; opaque.
- **How the BC is made (`paperbomb_art._composite`).**
  - Paper first, red over it, black over red.
  - Colour = lerp(dry, wet, load), with red pooling to `red_pool`.
  - The composite is multiplied by `1 - 0.13 · dirt · thin` and clipped to [0.0016, 0.962].
  - All of this happens at **2× supersample**, then a 2:1 box downsample (`_downsample` averages `a`, `d` and `p` separately, so a 1× recomposition from those layers is NOT exact).
  - `bake.transfer` then blits it 1:1 into the atlas: front island, back island (blank paper plus a show-through ghost), rim gradient.
- **Measured (ink-free texels are the paper; solid ink is split by redness).**

  | Region | Texels | Mean linear | Luminance-only model dE76 p99 |
  |---|---|---|---|
  | Paper | 2.29 M | (0.8809, 0.7527, 0.5325) | 0.89 (fits) |
  | Black ink | 0.30 M | (0.0060, 0.0058, 0.0053) | 2.96 (dry warmer) |
  | Red ink | 0.18 M | (0.557, 0.0093, 0.0040) | **17.4** (pools: (0.024, 0.011, 0.0082)) |

  So `_M` is not enough and D5 applies. 30 % of texels have partial ink coverage: dry brush, bleed, the ghost on the back.
- **Re-pointing after the exact pass.** Rerun `make_paperbomb_recolour_maps.py`, then `build_pack_materials.py`. Asset names stay the same.

---

## 3. The masters (parameter names, groups, ranges)

Groups are numbered so the MI editor orders them. "Advanced" parameters are written by the build from `recolour_maps.json`, and their group name says "do not edit".

### 3.1 `M_Steel_Master`: Default Lit, opaque

BaseColor = `Base Colour Map` × **Steel Tint**; Metallic = ORM.B; Roughness = saturate(ORM.G + **Roughness Adjust**); Specular 0.5; AO = ORM.R; Normal = MF_NormalStrength(N, **Normal Strength**).

| Parameter | Group | Default | Range |
|---|---|---|---|
| Steel Tint | 01 Colour | (1, 1, 1) | colour |
| Roughness Adjust | 02 Surface | 0 | −0.25..0.25 |
| Normal Strength | 02 Surface | 1 | 0..2 |
| Base Colour Map, ORM Map, Normal Map | 09 Textures | — | — |

### 3.2 `M_Fabric_Master`: material attributes, shading model from expression

| Parameter | Group | Default | Range / note |
|---|---|---|---|
| **Colour** | 01 Colour | per part (the mean colour) | colour picker (linear) |
| Detail Strength | 02 Detail | 1 | 0..1.5 |
| Roughness Adjust | 03 Surface | 0 | −0.25..0.25 |
| Specular Strength | 03 Surface | 0.5 / 0.65 / 0.5 / 0.5 | 0..1 (× ORM.A when the switch is on) |
| Normal Strength | 03 Surface | 1 | 0..2 |
| Cloth Sheen (static switch) | 04 Sheen | off (wrap: on) | Default Lit ↔ Cloth |
| Sheen Colour / Sheen Amount | 04 Sheen | (0.62, 0.60, 0.56) / 0.35 | colour / 0..1 |
| Use Lettering (static switch) | 05 Lettering | off (wrap: on) | |
| Lettering Colour / Lettering Roughness / Lettering Mask / Lettering Band UV | 05 Lettering | (0.62, 0.56, 0.44) / 0.62 / T_Kunai_Lettering / (1.1328125, 0.61898509, 1.8359375, 0.73617259) | |
| Detail Bias, Detail Scale, Detail Mean, Detail Highlight Ratio, Detail Moments Low/High (vec4), Dark Detail Follow (0.5), Albedo Ceiling (0.9) | 08 Advanced (set by build, do not edit) | per part | |
| Use Baked Colour Map (switch), Specular From ORM Alpha (switch), Detail Map, Base Colour Map, ORM Map, Normal Map | 09 Textures | off / on | |

Graph:

- **BaseColor** = UseBakedColourMap ? BC : MF_AlbedoRollOff(MF_TintDetail(Detail, Colour, …), knee 0.85, limit 0.95), then MF_LetteringBand when Use Lettering is on.
- **Roughness** = saturate(ORM.G + adjust).
- **Specular** = Strength × (switch ? ORM.A : 1).
- **AO** = ORM.R. **Normal** = MF_NormalStrength. **Metallic** = 0.
- **Shading model** = the switch picks MSM_DefaultLit or MSM_Cloth.
- **Fuzz Colour** (MMA `SubsurfaceColor`) = Sheen Colour.
- **Cloth amount** (MMA `ClearCoat` input = CustomData0) = Sheen Amount. Confirm the mapping with a V4 render. If the pin does not respond, fall back to Cloth unconnected (default 1) and scale Fuzz Colour by Sheen Amount.

Mapping the Blender sheen (weight 0.35, tint 0.62/0.60/0.56, roughness 0.35) to Unreal's Cloth lobe is an **approximation to calibrate in V4**, against `Renders/Shuriken/kunai_plain_grip_closeup.png`-style views.

### 3.3 `M_PaperInk_Master`: Default Lit, opaque, M not wired

Without the baked-colour path:

```
BaseColor = min( PaperColour ⊙ PaperDetail.rgb·PaperWeightScale
               + BlackInk·Ink.r + BlackDry·Ink.g
               + RedInk·Ink.b  + RedDry·Ink.a + RedPool·PaperDetail.a , AlbedoCeiling 0.962 )
            × lerp(1, ORM.R, Baked AO In Colour)
```

With MF_InkDerive:

- **BlackDry** = lerp(BlackInk, PaperColour, t) ⊙ g.
- **RedDry** = sRGBdecode(0.82 · sRGBencode(RedInk)). This is the palette's own definition: *"red_wet scaled by 0.82 in STORED space"*.
- **RedPool** = lerp(Y(RedInk), RedInk, s) ⊙ g_p.

Survey constants from the current palette: t = **0.00624**, g = (0.974, 1.003, 1.052); s = **0.30**, g_p = (0.0791, 0.1032, 0.0782). RedDry via 0.82 matches `red_dry` to 4e-4 linear.

The derivations depend on parameters only, so Unreal can evaluate them as preshaders, and they stay in [0,1] for any ink colour. One caveat: a light red-ink colour still pools DARK (the pool gain ≈0.09). That matches how pooled vermilion reads; document it for buyers.

| Parameter | Group | Default |
|---|---|---|
| Paper Colour / Black Ink Colour / Red Ink Colour | 01 Colours | mean paper / `black_wet` (0.0048, 0.0047, 0.0045) / `red_wet` (0.6649, 0.00926, 0.00350) |
| Roughness Adjust, Specular Strength (0.5), Normal Strength, Baked AO In Colour (1) | 03 Surface | |
| Paper Weight Scale, Black Ink Dry Paper Mix, Black Ink Dry Gain, Red Ink Dry Value Scale (0.82), Red Ink Pool Saturation, Red Ink Pool Gain, Albedo Ceiling (0.962) | 08 Advanced (set by build, do not edit) | |
| Use Baked Colour Map, Base Colour Map, ORM Map, Normal Map, Paper Detail Map, Ink Weights Map | 09 Textures | |

---

## 4. The recolour model (`MF_TintDetail` + `MF_AlbedoRollOff`)

```
n      = DetailBias + DetailScale·Detail                     multiple of the mean colour (mean ≈ 1)
H      = ln(AlbedoCeiling / max(Colour.rgb)) / ln(HighlightRatio)       HighlightRatio = p99.9 of n
C_hi   = min(DetailStrength, max(H, 0))                       highlights (n > 1)
C_lo   = lerp(DetailStrength, C_hi, DarkFollow)               dark weave (n ≤ 1)
n'     = n ≤ 1 ? n^C_lo : n^C_hi
E      = El(C_lo) + Eh(C_hi)        El(c) = E[n^c; n≤1], Eh(c) = E[n^c; n>1], cubics fitted exactly through c = 0, .5, 1, 1.5
Albedo = Colour · n' · DetailMean / E    →   roll-off: if max channel m > 0.85, scale rgb by (0.85 + 0.10·(1 − e^{−(m−0.85)/0.10}))/m
```

**Exact at the default.** H(default) is ≥ 1 for every part: smoke 1.23, straw 1.57, hat cloth 2.45, wrap ≈ 3. So C = 1, n' = n and E = DetailMean, which gives the item's own contract. The prototype twin (`survey/survey_twin_prototype.py` on the shipped maps) measures the default error at **≤ 2·10⁻¹⁶ linear**. The largest default albedo (smoke 0.63) is below the 0.85 knee, so the roll-off is the identity there too. Gate **G-H1**: the build asserts H(default) ≥ 1 and the maximum default albedo ≤ 0.85 for every part.

**Recolour** (prototype, Dark Detail Follow 0.5, `twin_prototype_f050.json`):

- Zero clipped texels for white, cream, pastel pink, saturated red, saturated blue, yellow, mid grey and near black.
- White keeps 34–40 % of the log-contrast. Near black keeps 100 %.
- The largest 8-bit output gap is 3 levels (smoke bomb, from the source's own 11 % steps at its darkest levels), 2 (straw), 1 (hat cloth).
- The mean albedo for white 0.8 is 0.754 / 0.766 / 0.772.

Dark Detail Follow is provisional. The stress test (V3) tunes it once for the whole pack; a lower value keeps more dark weave on light colours.

**Why not a plain multiply?** The dark cloth's albedo detail spans 7–14× its mean. A white cloth cannot have that range, so something must give. A soft clip alone would flatten 20 % of the smoke bomb into a plateau. Scaling the log-contrast with the colour's headroom keeps every texel's rank, so the detail survives, while nothing clips.

---

## 5. New maps: how to make each one from the build data

Every generator:

- runs headless: `"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b [file] --factory-startup --python <script> -- …`
- **never saves a .blend**
- writes only to `Exports/<Item>/Textures/Recolour/` (new files) and `WorkFiles/materials/`
- records sha256 of its inputs and outputs, and the default parameters, in `recolour_maps.json`

Scripts live in `Scripts/unreal/materials/maps/`.

### 5.1 `T_Kunai_Wrap_Detail16.png`: 1024², 16-bit linear grey (`make_kunai_wrap_detail.py`)

1. Open `Assets/Shuriken.blend` read-only. The survey confirmed `SM_Kunai_Plain_LOD0` has slots `M_Shuriken_Master` + `M_Kunai_Wrap`, the procedural wrap material (175 nodes) with its `Dye` node, and `kunai_shift_m` = −0.0205193.
2. Reproduce the wrap half of `kunai_wrap.bake_kunai` into a **float** image: `B._alone(lod0)`, `_absorber(steel)`, `_wrap_uv(lod0)`, `B._bake_channel(lod0, wrap_mat, "Base Color", float_image)` at `spec.wrap_px` (1024), then `B._fill(..., B._coverage(...))`. The Dye must be 0. Bake on the same device (OPTIX) and with the same samples as the pack.
3. Take Y = luminance of the linear rgb. Ymean is the covered-texel mean (the fill texels carry it), Ylo = min, Yhi = max. d = (Y − Ylo)/(Yhi − Ylo), written with a 16-bit grey writer.
4. Defaults: Colour = mean linear rgb, Bias = Ylo/Ymean, Scale = (Yhi − Ylo)/Ymean, Detail Mean = mean(n) (≈1), HighlightRatio = p99.9(n), cubic moments.
5. Gates:
   - **G-K1:** sRGB8(float bake) vs the shipped `T_Kunai_Wrap_BC.png`: max |Δ| ≤ 1 level, mean ≤ 0.2. This is the bake-noise tolerance the kunai freeze already uses.
   - **G-K2:** the default model vs the shipped BC: dE00 mean ≤ 0.5, p99 ≤ 1.5 (survey estimate: dE76 mean 0.19, p99 0.77).
   - **G-K3:** `Assets/Shuriken.blend` sha unchanged.
   - **G-H1.**

### 5.2 `T_SmokeBomb_Detail16`, `T_BlackHat_Straw_Detail16`, `T_BlackHat_Cloth_Detail16` (`make_detail16.py`)

d16 = round(65535 · sRGBdecode(Detail8/255)). This is lossless: every 8-bit level maps to a distinct 16-bit code. The defaults come from the sidecars (§2.3, §2.4); Mean, HighlightRatio and the moments are computed from the written file.

Gates: the decode round-trips within half a 16-bit step, and model(Detail16) vs BC gives 0 stored levels, as the shipped Detail does.

### 5.3 `T_PaperBomb_PaperDetail.png` + `T_PaperBomb_InkWeights.png`: 2048² RGBA8 linear (`make_paperbomb_recolour_maps.py`)

`props_lib.bake.write_png` cannot write alpha. Use a local colour-type-6 writer.

1. `plan = atlas.plan_for(spec)`, where `spec` is the build's paper-bomb spec, as in `build_paper_bomb.stage_art`. Call `bake.draw_art(spec, plan, seed=20260919, supersample=2)` (≈2–3 min). While it runs, wrap `paperbomb_art._composite` and `paperbomb_art._downsample` **in memory** (the files are untouched) to capture the 2× `paper` dict, the `red` and `black` Ink layers and `cfg` for the front.
2. At 2×, with K = 1 − 0.13·clip(grime·0.5 + edge_band·0.6)·max(a_r(1−d_r), a_b(1−d_b)) (the formula in `_composite`):
   ```
   W_bw = a_b·d_b·K            W_bd = a_b·(1−d_b)·K
   W_rw = (1−a_b)·a_r·d_r·(1−p_r)·K    W_rd = (1−a_b)·a_r·(1−d_r)·(1−p_r)·K    W_rp = (1−a_b)·a_r·p_r·K
   W_P,c = (clip(total)_c − Σ ink terms_c) / PaperColour_c      per channel: absorbs paper grain, foxing, edge band, the dirt and the clip exactly
   ```
3. Box-downsample 2:1 with `paperbomb_art._down`. Apply `bake._fit_raster`'s far-edge extension to the weight rasters as well. Compose into the atlas with `atlas.compose(plan, front, back, fill)`. On the back face, W_P = back.base_colour / PaperColour and the inks are 0 (the ghost belongs to the paper). On the rim, W_P = rim_gradient / PaperColour.
4. Choose PaperColour = the mean of the paper-only front texels and PaperWeightScale = max(W_P)·1.001. Write PaperDetail RGB = W_P/scale with A = W_rp, and InkWeights = (W_bw, W_bd, W_rw, W_rd).
5. Gates:
   - **G-P1:** Σ weights × default colours vs the shipped `T_PaperBomb_BC.png`: max |Δ| ≤ 1 stored level everywhere, dE00 mean ≤ 0.3.
   - **G-P2:** derived colours within 0.25 stored levels of `black_dry` / `red_dry` / `red_pool`.
   - **G-P3:** derived colours in [0,1] for the stress set.
   - **G-P4:** art modules byte-identical to the paused snapshot. If the exact pass later changes `_composite`, G-P1 fails loudly and the generator is updated with it.
6. Compression: TC_BC7 with sRGB OFF by default. Switch to TC_VectorDisplacementmap (uncompressed BGRA8, 21 MiB each) if the V2 default gate fails with BC7.

---

## 6. Unreal build (materials as code)

### 6.1 Layout

| Path | Content |
|---|---|
| `/Game/NinjaPack/Textures/<Item>/` | T_ assets |
| `/Game/NinjaPack/Meshes/` | SM_ assets |
| `/Game/NinjaPack/Materials/` | 3 masters |
| `/Game/NinjaPack/Materials/Functions/` | 5 MFs |
| `/Game/NinjaPack/MaterialInstances/` | 12 MIs |
| `/Game/NinjaPack/MaterialInstances/Presets/` | `MI_Kunai_Plain_Wrap_Undyed` (optional) |

### 6.2 Code in `Scripts/unreal/materials/`

- **`build_pack_materials.py`** is the entry point. One mode per process: `clean` | `import` | `build` | `assign` | `dump` | `verify`.
- **Modules:**
  - `np_spec.py` loads `material_spec.json` and the `recolour_maps.json` files.
  - `np_graph.py` holds the node/link/param helpers (group, sort_priority, desc, slider_min/max).
  - `np_functions.py`, `np_masters.py`.
  - `np_textures.py` sets the import flags from `texture_import`, the hat ORM composite and G16 checks.
  - `np_meshes.py` does the legacy FBX import, as in `WorkFiles/smokebomb/UnrealCheck_fp/sbu_pass1_import.py`: LODs ON, normals imported, one convex per UCX, no materials, Interchange FBX off. `pipeline.ue_import_sockets.apply_sidecar` does the only save and applies the sockets and LOD screen sizes. Slots are assigned with `StaticMesh.set_material(index, mi)`.
- **Generators:** `maps/`.
- **Verification:** `verify/`. `twin.py` is the numpy twin, run in Blender; there are UE capture scripts and an EXR reader.

The `material_spec.json` field `texture_kinds` says which import intent each texture gets.

**Slot names in the FBX** (from earlier Unreal checks):

| Mesh | Slots |
|---|---|
| Stars | `M_Shuriken_Master` |
| Kunai | `M_Shuriken_Master`, `M_Kunai_Wrap` |
| Smoke bomb | `M_SmokeBomb` |
| Hat | `M_BlackHat_Straw`, `M_BlackHat_Cloth` |
| Paper | `M_PaperBomb` |

**Instances:**

- MI_Shuriken_FourPoint_Steel, MI_Shuriken_EightPoint_Steel, MI_Shuriken_SquarePlate_Steel, MI_Shuriken_SixPoint_Steel, MI_Shuriken_Spike_Steel, MI_Shuriken_HookedCross_Steel
- MI_Kunai_Plain_Steel, MI_Kunai_Plain_Wrap
- MI_SmokeBomb_Cloth
- MI_BlackHat_Straw, MI_BlackHat_Cloth
- MI_PaperBomb_Tag
- (optional preset) MI_Kunai_Plain_Wrap_Undyed

**Determinism:**

- `clean` deletes `Materials/` and `MaterialInstances/` in its own process. Deleting and recreating in one process logs reference-gathering warnings.
- `build` then recreates everything from nothing.
- `dump` writes a JSON of every expression (class, properties, links) and every MI parameter. Two clean builds must dump identically; the asset bytes carry GUIDs, so compare the dumps instead.

### 6.3 Commandlet invocation

- **Authoring and data:**
  ```
  UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<py> -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput
  ```
- **Render:** replace `-nullrhi` with `-AllowCommandletRendering -RenderOffscreen "-dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0"`.
- **Guards:** check `tasklist | grep -i UnrealEditor-Cmd` before each run, run one process at a time, set `MSYS_NO_PATHCONV=1` in Git Bash, and never touch UnrealEditor.exe.

---

## 7. What this Unreal build can do in a commandlet (probe, 2026-09-26, UE 5.8.3)

`survey/ue_probe_materials.py` authored into `/Game/_Probe_NPMat_0926`. A fresh process then reloaded the assets and deleted them; the folder is gone from `Content/`. Results are in `survey/probe/ue_probe_{author,reload}.json`.

**Worked:**

1. **PNG import through `AssetImportTask`** (goes through Interchange for PNG), with `srgb`, `compression_settings` (TC_GRAYSCALE, TC_BC7, TC_EDITOR_ICON) and `mip_gen_settings` set after import, then saved. The flags persisted in a fresh process.
2. **MaterialFunction creation.** `MaterialFunctionFactoryNew`; FunctionInput (vector3 and scalar, `input_name`, `sort_priority`) and FunctionOutput via `create_material_expression_in_function`; `MEL.update_material_function`.
3. **Material creation.** `MaterialFactoryNew`, with Vector/Scalar/TextureSampleParameter2D/StaticSwitchParameter nodes. `group`, `sort_priority`, `desc`, `slider_min/max` and `sampler_type` all set without error. MaterialFunctionCall worked, and so did `connect_material_expressions` / `connect_material_property`.
4. **Compile and stats.** `MEL.recompile_material` returned `[]`. `MEL.get_statistics` → 150 pixel-shader instructions, 2 samplers.
5. **Material attributes.** Shading model **Cloth** plus `use_material_attributes` + **MakeMaterialAttributes** compiled. Its inputs include `ShadingModel`, `SubsurfaceColor` and `ClearCoat`. A **static switch between two `MaterialExpressionShadingModel` nodes** (Default Lit / Cloth) feeding MMA.ShadingModel compiled, and so did its MIC permutation.
6. **MICs.** `MaterialInstanceConstantFactoryNew`, `set_material_instance_parent`, vector and static-switch overrides. They persisted and read back in a fresh process.
7. **Offline render in a commandlet.**
   - Setup: D3D12 on the RTX 4070 SUPER. The transient editor world is `/Temp/Untitled_0` (never saved). Actors were spawned with EditorActorSubsystem.
   - Capture: SceneCapture2D, orthographic, `SCS_BASE_COLOR` into an `RTF_RGBA32F` target from `create_render_target2d`. `capture_scene()` is synchronous. Read back with `read_render_target_raw_pixel(_area)`; `export_render_target` writes **OpenEXR**, with the filename taken exactly as given.
   - **G8 + sRGB decode is correct in the render:** G8 128 → **0.21582** (expected 0.21586). BC7 sRGB (200, 100, 50) → (0.5781, 0.1270, 0.0320), expected (0.5776, 0.1274, 0.0319).
   - The base-colour capture is the **8-bit sRGB GBuffer** value. For example 0.1079 comes back as 0.1069, level 93. So compare at stored-level precision.
   - A lit `SCS_FINAL_COLOR_HDR` capture with a DirectionalLight worked and exported as EXR.
8. **Cleanup.** `EditorAssetLibrary.delete_directory` worked.

**Did not work, or needs care:**

- `unreal.MaterialProperty` has **no `MP_CUSTOM_DATA0` and no `MP_SHADING_MODEL`**. Use MakeMaterialAttributes instead.
- `-ini:Engine:[DevOptions.Shaders]:bAllowAsynchronousShaderCompiling=False` **crashes at startup**: `Assertion failed: AllJobs.GetNumPendingJobs() == 0`, ShaderCompiler.cpp:1940. **To block until shaders exist, call `MEL.get_statistics(material_or_mic)`.** It runs `FMaterialResource::FinishCompilation()`: 2 s for two MIC permutations.
- `set_material_instance_*_parameter_value` returns **False even on success** in 5.8. Read back instead.
- Wiring a graph logs transient `Failed to compile Material … (Node StaticSwitchParameter) Missing B input`. Judge by the final `recompile_material()` and `get_statistics`, not by grepping `Warning:`. Engine debug materials also log Niagara X3507 diagnostics; that is engine noise, not ours.
- `blueprint_get_memory_size()` returns 0 under `-nullrhi`. It needs the RHI process.
- SceneCapture: set `capture_every_frame = False` before `capture_scene()`, or the log gets a "major inefficiency" warning.
- Timing: first compile of a new material ≈ 30–60 s. The whole probe author process (3 materials, 3 MICs, 2 captures) took 128 s.

---

## 8. Verification method (the gates the later phases run)

| Gate | Method | Pass |
|---|---|---|
| **V0 frozen** | `survey/check_exports_frozen.sh` | exit 0; only NEW files under `Recolour/` |
| **G-H1 / G-K* / G-P*** | generators (§5) | as stated |
| **V1 source twin** | numpy twin of every graph on the source PNGs (Blender python) | per recolourable part, covered texels: dE00 mean ≤ 0.5, p99 ≤ 1.5 vs the BC PNG (smoke/hat expected 0 levels) |
| **V2 UE base colour** | engine Plane, ortho SceneCapture at the texture's resolution, SCS_BASE_COLOR, RGBA32F → EXR, analysed in Blender. First calibrate UV orientation by cross-correlating the BC-direct instance with its PNG. | default MI vs twin: \|Δ\| ≤ 1 sRGB level at p99.9, mean ≤ 0.3. The BC-direct vs PNG figure (BC1 error) is reported, not gated. |
| **V3 recolour stress** | the twin for 8 colours on every part (paper: each colour alone), plus UE V2 for white, saturated red and near black | clip ≤ 0.1 %; banding: max gap ≤ 3 levels and occupied ≥ 0.5 × span; detail: std(log L) ≥ 0.25 × default, Spearman ≥ 0.98 on UE captures; mean dE00 ≤ 3 for colours with max channel ≤ 0.85 |
| **V4 lit look** | SCS_FINAL_COLOR_HDR, fixed rig, EXR. Default MI vs BC-direct MI; wrap sheen on/off; smoke bomb ORM.A vs constant 0.5; side-by-side with the Blender gallery for the look judge | dE00 mean ≤ 1.0 for default vs BC-direct; the +53 % shows for the constant-specular control |
| **V5 persistence** | fresh process: parent, every parameter, textures, slots on every LOD, `recompile_material()==[]`, `get_statistics` (samplers ≤ 16), texture flags incl. hat ORM composite and G16 format, memory via `blueprint_get_memory_size` (RHI run) | all equal to the spec |
| **V6 determinism** | two clean builds → identical dump JSON | identical |
| **V7 buyer review** | an independent reader goes through the MI parameter dump (names, groups, descriptions, ranges) | clear without the docs |

---

## 9. Risks and questions for the user

1. **Pack name.** `/Game/NinjaPack` is a working name. The final name is the user's call; renaming the root folder is all it takes.
2. **Texture memory, factual correction.** The shipped sRGB Detail maps build as BGRA8 on PC (4 bytes per texel): smoke bomb ≈ 85 MiB, hat 21 MiB per part. The masters use the G16 twins (half that). The smoke bomb's Detail is still 42.7 MiB at 4096. A game build may want Maximum Texture Size 2048 on it; that is the user's call, because the item's report found 2048 loses sparkle at its reference view.
3. **The kunai sheen is an approximation** of Blender's sheen with Unreal's Cloth lobe. It is calibrated by eye plus the V4 on/off pair. The Cloth-amount pin mapping (MMA ClearCoat = CustomData0) needs the V4 render to confirm.
4. **Substrate is untested.** It is off in this project; the legacy masters auto-convert in a Substrate project. A Substrate compile check would recompile every global shader (tens of minutes), so it is not planned.
5. **The paper bomb will change.** Its exact pass rewrites the maps and maybe the palette and `_composite`. The generator's G-P1 recomposition gate detects any drift. Re-pointing is two commands.
6. **Light colours flatten on purpose.** White keeps about a third of the dark cloth's log-contrast. Physically, light fabric does not carry 10:1 albedo variation. Detail Strength and Dark Detail Follow tune this, and V3 records it.
7. **Pooled red ink stays dark for any red-ink colour.** This is a property of the reference's pooled vermilion. Document it.
8. **Stale numbers in two reports** (not fixed, since they are frozen files): BLACKHAT_REPORT's Bias/Scale table, and SMOKEBOMB_REPORT's "Detail G8 ~21.3 MiB".
9. **Importer default output path.** Both texture importers write their JSON into the export folder's parent unless `*_TEXTURE_OUT` is set. Always set it, or a new file appears in `Exports/`.
