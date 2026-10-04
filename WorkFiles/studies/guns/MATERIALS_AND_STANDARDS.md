# Gun study: materials, realism data and cross-gun standards

**Written:** 2026-10-04, research only (web, the repo's files and pixel measurements of the six reference sheets; no
Blender, no Unreal, no shared-material edits). **Role:** one of several research notes for the gun-line study
(`WorkFiles/studies/guns/`). **Clients:** the AR-01 rifle (now), the SMG (next), then the carbine, long rifle, sniper
and pistol, and the attachments kit from the backlog (`WorkFiles/guns/GUN_REFERENCE_PROMPTS.md`).

Tags: **[E]** external source (numbered, list at the end), **[M]** measured or read in this repo, **[J]** judgement.
**[SECONDARY]** = a search-engine summary, a forum or a blocked (403) page, not a primary document.
**[UNVERIFIED 5.8]** = not tested on this machine's Unreal 5.8.

Measurement scripts (scratch, not in git): `<scratchpad>/matstd/sample.py` (colour patches) and `extent.py`
(gun length against each sheet's ruler).

---

## 0. The twelve rules (read this if nothing else)

1. **A gun finish is a coating over a substrate.** Every finish except bare stainless and raw polymer is a thin layer
   (oxide, phosphate, anodic oxide, ceramic paint, lacquer) over steel, aluminium or wood. So wear never "lightens the
   paint"; it **reveals the layer underneath**. Bake one mask that says where the coating has gone, and shade both
   layers from it [J, after 11, 12, 13].
2. **Most gun coatings are dielectrics, not metals.** Parkerizing is a non-metallic crystalline phosphate [E 6]. Hard
   anodizing is a transparent oxide with dye or a dark colour [E 7]. Cerakote is a ceramic-filled polymer paint
   [E 8]. All three are metallic 0 with a dark base colour. Metallic 1 is only for the bare metal that wear reveals,
   stainless, and polished moving parts.
3. **Bluing (black oxide) is the one in-between finish.** It is a thin magnetite layer, and magnetite reflects about
   20-22 % across the visible range [E 5]. Shade it as metallic 1 with a dark neutral base colour of about 0.20
   linear, or as dark lacquer over steel when the reference reads that dark. The AR-01 sheet reads that dark (rule 4).
4. **The rifle reference's "blued" steel reads as a dark dielectric.** Measured [M]: receiver and magazine median
   luminance is **0.17-0.21 x the grey background**. A 20 %-reflective metal would render near 1 x the background
   under that soft studio light. So AR-01's metal is **black lacquer or paint over steel** (base colour linear about
   0.03-0.04, sRGB about 50-55, metallic 0), with wear down to bare steel. Real AKMs were phosphated and lacquered,
   so this matches.
5. **Polymer, rubber and wood wear differently.** Polymer does not reveal another colour: it **polishes** (roughness
   goes down) and scuffs slightly lighter. Rubber barely wears at all. Wood loses its finish where hands rest, which
   makes it lighter, rougher and less saturated, and hand oil darkens the grain around those patches [J, after 11, 12].
6. **Wear has a cause, so place it by cause.** The causes are: hard edges hitting things, hands, magazine insertion,
   holstering, grounding the butt, thumb travel on controls, sliding parts and muzzle heat and soot (section 3). Do
   not spread a uniform curvature mask everywhere [E 12, J].
7. **Join the pack the way the katana did: additions only, masters unchanged** [M: `changes_v8_katana`]. Steel that
   keeps its baked look goes on `M_Steel_Master`. Recolourable furniture and coatings go on `M_Fabric_Master`, with
   **Metal From ORM** on wherever bare-metal wear has to keep its baked colour. Watch one trap: that switch also
   keeps any texel whose baked colour is brighter than linear luminance 0.2-0.4, which it treats as "pearl ornament"
   [M: spec text]. A light finish such as raw birch or FDE tan would then refuse to recolour (section 4.3).
8. **Plan one `M_Weapon_Master` before the Fab gun pack and battle-royale skins.** It needs coating recolour, a
   **Wear Amount** slider, a **tileable camo** layer and grime. It is a new master, so it takes the PackMaterials lock
   and needs preflight. Ship every gun's **masks texture** from the first build (section 4.4) so this costs no re-bake.
9. **Make skins as material instances over shared textures, not as texture sets.** A camo skin is one MIC plus one
   tileable pattern that every gun shares. This is the APB and CS:GO model [E 13, 15]. The camo lines up across guns
   because all guns share one texel density, which the sidecar records. Unique hand-painted skins are the expensive
   exception.
10. **Use real dimensions for scale.** Each gun's overall length, barrel and mass come from section 5, not from the
    sheet rulers. Measured [M]: by their own rulers the sheets make every gun **8-26 % too long**.
11. **One interface standard across the line.** Rails use the MIL-STD-1913 profile and the 10.01 mm slot pitch. One
    socket set with fixed names (`GRIP_R`, `GRIP_L`, `AIM`, `MUZZLE`, `MAG`, `EJECT`, `RAIL_*`). The pivot is at the
    firing-hand grip point. The muzzle device is a separate part so a suppressor can replace it. One magazine origin
    convention. With these, one attachments kit and one animation set per class (long gun, pistol) fit every gun
    (section 6).
12. **Build shared parts once, as code modules.** The carbine and long rifle share their lower receiver, magazine,
    grip and controls. The rail, sight posts, screws, pins and sling swivels are shared across the whole line. Write
    them once in `Scripts/guns/parts/` (proposed) and call them from each `build_<gun>.py`.

---

## 1. Scope and how to use this note

- **Section 2** gives PBR values per finish: what to type into base colour, metallic and roughness for a gun part.
- **Section 3** is the wear logic: where wear goes on each gun type, and why.
- **Section 4** is how guns join `Scripts/unreal/materials/`, the `M_Weapon_Master` proposal, the masks texture and
  battle-royale skins.
- **Section 5** gives real dimensions and masses for scale and physics.
- **Section 6** is the cross-gun standards: hand frame, sockets, rail, muzzle, magazine families and code modules.
- **Section 7** is what the AR-01 plan and the SMG must change. **Section 8** is the decisions only the user can make.

Values are **Unreal metal/roughness**: base colour as linear float with sRGB 0-255 in brackets, Specular left at 0.5
(4 % F0) for every dielectric [E 1]. Ranges are where to start. A sheet-match round sets the final value.

---

## 2. PBR values per gun finish

### 2.1 Anchors

- Non-metal base colour must stay within **sRGB 50-243** [E 3]. CS:GO's finish guide allows 55-220 for non-metals
  [E 13]. Charcoal is about 0.02 linear, fresh snow 0.81 [E 1].
- Metal base colour sits at **sRGB 186-255** for pure metals [E 3]. CS:GO allows "180-250, acceptable as low as
  90" [E 13], and oxide coatings are the reason for that low end.
- Measured metal base colours, linear: iron (0.560, 0.570, 0.580) per Epic, (0.530, 0.513, 0.494) per Physically
  Based; stainless (0.669, 0.639, 0.598); aluminium (0.913, 0.921, 0.925) per Epic, (0.916, 0.923, 0.924) per PB;
  titanium (0.542, 0.497, 0.449) per Epic; brass (0.910, 0.778, 0.423) per PB [E 1, 2].
- Treat Metallic as binary. Use intermediate values only for corroded, dusty or rusty blends [E 1]. The house rule
  agrees: "No partial metallic on painted colour" [M: ASSET_GUIDELINES 3].
- Gloss units to roughness: paint sheen bands are matte < 10 GU, eggshell 10-15, sheen 15-25, satin 26-40,
  semi-gloss 41-69, full gloss 70-90, at 60° [E 9]. No published conversion from GU to GGX roughness was found. The
  roughness numbers below are **[J]**, mapped by band and checked against how the sheets read.

### 2.2 The table

| Finish (where on the line) | Metallic | Base colour, linear (sRGB) | Roughness | Wears to | Notes |
|---|---|---|---|---|---|
| **Bare / machined carbon steel** (worn edges, bolt, bore, pins) | 1 | 0.53-0.56 neutral (190-196) [E 1, 2] | 0.25-0.40 machined, 0.15-0.25 polished by sliding | — | Moving parts that rub (bolt, carrier, charging-handle face, trigger face) sit at the low end. |
| **Black lacquer / paint over steel** (AR-01 receiver, magazine) | 0 | 0.025-0.04 (45-55) [M rule 4] | 0.40-0.55 satin; 0.55-0.70 matte | bare steel | What the rifle sheet shows. Wear to bare steel is sharp-edged (paint chips), never a soft fade. |
| **Bluing / black oxide** (classic sniper variant, small parts) | 1 | 0.16-0.22, faint blue or neutral (110-130) [E 5, J] | 0.25-0.40 polished bluing; 0.45-0.60 matte | bare steel, worn bluing goes grey-brown first | Below the 186 sRGB metal floor on purpose: magnetite is about 20 % reflective [E 5]. |
| **Manganese phosphate (parkerized)** (barrels, SMG and carbine small steel parts) | 0 | 0.03-0.06 dark grey-black (50-70) [E 6, J] | 0.65-0.85; oiled 0.55-0.70 | bare steel | Rough, porous crystals that hold oil [E 6]. The oil darkens it and lowers its roughness. |
| **Zinc phosphate** (optional lighter-grey variant) | 0 | 0.08-0.15 (80-108) [E 6, J] | 0.60-0.80 | bare steel | "Light to medium grey" [E 6]. |
| **Type III hard anodized aluminium** (carbine and long-rifle receivers, rails, handguards, scope tube) | 0 | 0.025-0.05 (45-62) [E 7, J] | 0.45-0.65 | bare aluminium: metallic 1, 0.91 (245), roughness 0.30-0.45 | Type III comes only in black, dark grey, dark bronze or natural [E 7]. Wear shows as **bright silver**, high contrast. |
| **Cerakote-type ceramic paint** (sniper chassis OD green, colour variants) | 0 | per colour; the sniper sheet's OD reads about 0.05 (sRGB rendered 89, 89, 78; hue 59°, sat 0.12) [M] | matte 0.60-0.75; satin 0.45-0.55 [E 8, 9, J] | substrate (Al or steel) | H-series comes in matte, eggshell and satin [E 8]. A hard, thin coat: it chips at corners, there is no primer layer to show, and edges show a dark rim before the metal. |
| **Glass-filled polymer** (SMG body, carbine and long-rifle furniture, grips) | 0 | 0.02-0.04 (40-55) [M] | 0.50-0.70 smooth moulding; 0.75-0.90 stippled grip panels | itself: polished (-0.10 to -0.20 roughness), slightly lighter | Measured [M]: SMG body, grip and magazine 0.12-0.15 x background; long-rifle stock 0.14 x, handguard 0.24 x. |
| **Brushed stainless** (pistol slide and barrel) | 1 | (0.67, 0.64, 0.60) (214, 209, 203) [E 2] | 0.25-0.40 along the brushing, about 0.15 higher across it | itself (scratches) | Anisotropy needs the project setting "Use anisotropic BRDF (Beta)" [E 10], which a Fab buyer may not have on. Default to a brushed micro-normal plus roughness, with anisotropy as an optional static switch [J]. The pistol sheet slide reads 1.09 x background [M]. |
| **Walnut / dark stained wood, shellac or varnish** (AR-01 stock and handguards) | 0 | 0.04-0.07, hue 18-22°, sat 0.45-0.65 [M] | 0.35-0.55 satin varnish; 0.50-0.70 oil finish [J, after 33] | raw wood: lighter, rougher, less saturated | Measured [M]: stock sRGB (103, 65, 47), lower handguard (110, 65, 40), grip (99, 68, 54). Soviet stocks were finished with shellac or varnish, sometimes tinted [E 33, SECONDARY]. |
| **Birch / beech, light** (variant) | 0 | 0.30-0.42 (150-175) [E 4, SECONDARY] | 0.40-0.60 | raw: rougher | Fresh wood 0.35-0.42, weathered 0.12-0.16, varnished 0.13 [E 4]. **Above the Fabric master's ornament threshold** (section 4.3). |
| **Laminate wood** (variant) | 0 | per ply: alternating dark and light veneer bands on end grain and edges | 0.40-0.55 | as walnut | The ply lines on cut edges are the cue; flat faces look like ordinary grain [J]. |
| **Rubber** (butt pad, pistol grip, scope eyecup) | 0 | 0.02-0.03 (tyre 0.023, rubber 0.05) [E 2] | 0.70-0.90 | barely wears; dust in the texture | Measured [M]: sniper butt pad 0.09 x background, pistol grip 0.27 x (its pebbling catches the light). |
| **Soot / carbon fouling** (muzzle, gas port, ejection port) | 0 | 0.02-0.03 | 0.80-0.95 | — | A gradient from the vent or port outward [E 12]. |
| **Grime / oil in cavities** | 0 | darken base colour 10-30 % | oil -0.15 roughness; dust +0.10 | — | Driven by the cavity channel of the masks texture (section 4.4). |

**Reading the [M] colour samples.** The sheets are AI-generated and lit, so the ratios are not albedo. If the
seamless backdrop is about 18 % grey, then a diffuse part's albedo is roughly 0.18 x its ratio. That gives wood about
0.05, polymer 0.02-0.04 and rubber about 0.016, all inside the published ranges [E 1, 2]. Use the samples for hue,
relative value and wear contrast. Use [E] for absolute values.

### 2.3 Shared micro-detail textures [J]

One set of tileable detail normals, shared by every gun, keeps the line consistent and saves memory. Proposed set:
cast (rough cast steel), bead-blast, machined swirl, brushed (stainless), polymer moulding grain, stippled grip,
pebbled rubber, wood pores. The house rule "model real forms as real geometry" is about forms you can see. Sub-mm
surface texture is what a normal map is for. Checkering and serrations of 1 mm and up stay real geometry (the AR-01
grip checkering, the pistol slide serrations).

---

## 3. Wear logic: where it goes and why

Work through the weapon's life in order: factory finish, then wear-resistant coating, then scratches, dust and oil,
then hand marks [E 12, SECONDARY]. Keep surface wear subtle and edge wear hard [E 12]. The heaviest wear and heat sit
at the pistol grip, magazine, the handguard where the support hand holds it, and the muzzle [E 12]. Hand-painted rust,
grease and subtractive paint-wear layers sold the 80.lv AK-74 [E 11].

| Cause | Where (gun types) | What it does | Mask channel |
|---|---|---|---|
| Edge abrasion (bumping, carrying, setting down) | every convex hard edge: receiver corners, dust-cover ribs, sight wings and protectors, muzzle crown, trigger guard, rail top edges, stock edges | coating chipped to bare substrate in a 0.5-3 mm band | R (edge-wear propensity, from curvature x exposure) |
| Firing hand | pistol-grip front and back strap, palm swell, thumb rest, beavertail (pistol) | polymer polished; wood finish worn, then darkened by oil; stipple tips flattened | G (handling) |
| Support hand | handguard underside and sides at the hold point, AK lower-handguard belly, SMG magwell (SMG hold), pistol trigger-guard front | as above, plus wood polish; anodizing rubbed to grey | G |
| Cheek weld | stock comb (AR-01 wood, long-rifle polymer, sniper cheek riser) | polished; wood darkened | G |
| Thumb travel | selector lever and the arc it sweeps on the receiver (AK: the long lever's path scrapes the receiver side) | bright arc of scratches following the travel | G (painted as an arc) |
| Magazine insertion | magwell rim (a fan of scratches pointing into the well), magazine spine front and back, feed lips | bright streaks along the insertion axis | R + G |
| Magazine drops | magazine baseplate edges and corners, the bottom of the curved spine | dents and bare corners | R |
| Grounding the gun | butt plate bottom edge and toe, stock heel, bipod feet, pistol magazine base | heavy abrasion, small dents (wood) | R |
| Holster (pistol) | slide front and muzzle face, front-sight base, slide flats, frame dust-cover edge | finish worn to bright steel; on stainless, a polished patch | R + G |
| Sliding parts | bolt carrier flank, charging-handle face, pistol slide rails, dust-cover edges | polished bright metal (machined steel, low roughness) | R (forced) |
| Heat and gas | muzzle device and vents, gas block and port, ejection port surround | soot gradient and carbon smudge; bluing can heat-tint only if overheated (rare, do not overuse) | B-side soot can live in G's unused range or its own channel [J] |
| Cavity grime | rail slots, screw heads, receiver seams, the trigger-guard inside corner, grip texture troughs | darker base colour, dust (rougher) or oil (shinier) | B (cavity / AO gate) |
| Sling | swivel bases, stock side beside the rear swivel | rub marks | G |

**Scale check [J].** An edge-wear band of about 1.5 mm needs 2 px or more to survive the first mip, so at least
13 px/cm on surfaces seen up close. Estimate: a rifle's surface is about 0.2-0.3 m². A 2048 atlas packed to 70 %
gives about 30 px/cm, a 4096 about 65 px/cm. For comparison, the katana blade measured 54.8 px/cm on a 2048 [M:
KATANA_REPORT]. The house 10.24 px/cm (first-person hero) is too low for gun wear seen in first person. Another role
owns the final texel-density number.

**Method in this repo [J].** There is no Substance. Bake curvature and AO from the bevelled mid-poly in Cycles.
Compute edge propensity as convexity x (1 - AO) x a per-part exposure weight. Store the handling zones as named
polygons or volumes in the gun's spec JSON ("firing_grip", "support_hold", "cheek", "mag_spine", "selector_arc"),
rasterised in the bake. Pick shipped-look thresholds per gun and record them in the spec. That keeps wear placement
reviewable as code, like the katana's per-face parametric maps [M: KATANA_REPORT].

---

## 4. Joining the pack's material system

### 4.1 What exists [M]

`Scripts/unreal/materials/material_spec.json`, schema `ninjapack.material_spec/2`, built into `/Game/NinjaPack` by
`run_build.sh` under the PackMaterials lock:

- **`M_Steel_Master`**, Default Lit: `BaseColor = saturate(BaseColourMap * SteelTint)`, Metallic = ORM.B, Roughness =
  ORM.G + Roughness Adjust (±0.25), Normal Strength. One colour parameter, **Steel Tint**, a multiply whose tooltip
  already suggests "cool (0.8, 0.9, 1.0) for blued steel". Skeletal and instanced use: on.
- **`M_Fabric_Master`**, attributes-based: the recolour system. `MF_TintDetail` turns a **16-bit linear detail map
  (Detail16)** plus per-map constants (Detail Bias, Scale, Mean, Moments, Mip Compensation, written by a GENERATOR
  from `recolour_maps.json`) into an albedo for any picked **Colour**. **Lightest Colour** and Albedo Ceiling guards,
  a Use Original Baked Colours switch, and **Metal From ORM**: texels the ORM marks as metal keep their baked colour.
  Skeletal and instanced use: on. Used on the katana grip (Metal From ORM on) and the saya lacquer.
- **`M_PaperInk_Master`**: paper-bomb only.
- Texture kinds: BC sRGB; ORM_rgb or ORM_rgba linear (TC_MASKS, BC3); N DirectX; **Detail16 = G16 linear, sRGB off**.
- Adding an item = additions only. Copy `maps/derive_constants_<item>.py`, write the item's recolour maps script, add
  item and instance entries. The katana did exactly this with "masters: unchanged" [M: `changes_v8_katana`].

### 4.2 How each gun part maps onto today's masters

| Gun part | Master | Why |
|---|---|---|
| Bare or blued steel that keeps its baked look (bolt, small parts, pistol stainless) | `M_Steel_Master` | Steel Tint covers blued, stainless and bronze variation; nothing to recolour. |
| Dark coated metal with bare-metal wear (AR-01 receiver, anodized receivers, OD chassis) | `M_Fabric_Master` + **Metal From ORM** | The coating recolours through Detail16; the worn metal texels keep their baked colour. This is "coating over substrate" in today's system. |
| Dark wood, polymer, rubber | `M_Fabric_Master` (Metal From ORM off unless metal shares the slot) | Recolourable furniture: wood tone, polymer colours (black, FDE, OD, grey). |
| Glass / lens | none of these | A future opaque lens material with a tinted coating and fake reflection; avoid translucency on a gun seen in first person [J]. |

### 4.3 The trap: the "pearl ornament" luminance rule [M]

With Metal From ORM on, the Fabric master keeps the baked colour wherever
`max(ORM.B, saturate((lum(BaseColourMap) - 0.2) x 5))` is high. That is, any texel whose baked colour is above
**linear luminance 0.2-0.4** stays fixed, because the rule was written for pearl ornaments on the fan.
- Raw birch (0.30-0.42), zinc phosphate at the light end, FDE or tan Cerakote (about 0.25-0.35) and light polymer
  colours all cross it. **They would not recolour, or would recolour only partly.**
- Dark finishes are safe: walnut 0.05, black lacquer 0.03, polymer 0.02-0.04, OD about 0.05.
- So AR-01 and the SMG (dark walnut, black lacquer, black polymer) can use today's masters. A light variant (birch
  stock, tan SMG) needs either Metal From ORM off on that slot, with the metal moved to its own slot, or the new
  master.

### 4.4 Proposal: `M_Weapon_Master` (new, additive; before the Fab gun pack and battle-royale skins)

Built through the shared-materials process: PackMaterials lock, a spec entry for every parameter, `np_preflight.py`,
`run_build.sh`. **No edit to the three existing masters.** Graph sketch [J]:

```
Coating   = MF_TintDetail(Detail16, CoatingColour, ...)        # reuse the pack's recolour function
CoatingWorn = 1 - smoothstep(T(WearAmount), T(WearAmount)+e, Masks.R*EdgeW + Masks.G*HandW)  (only where Masks.A=1)
Substrate = SubstrateMap from BC (baked bare steel or aluminium), metallic 1
Camo      = UseCamo ? pattern(UV0 * CamoScale / TexelDensity) or PreSkinnedLocalPosition triplanar : none
BaseColor = lerp(Substrate, lerp(Coating, Camo, CamoMask), CoatingWorn) * lerp(1, GrimeTint, Masks.B*GrimeAmount)
Metallic  = lerp(1, 0, CoatingWorn) on Masks.A texels; ORM.B elsewhere
Roughness = ORM.G + RoughnessAdjust, polished by Masks.G on polymer/wood regions
```

- **Wear Amount 0-1** thresholds the propensity masks, like CS:GO's float, whose condition bands run Factory New
  0.00-0.07, Minimal 0.07-0.15, Field-Tested 0.15-0.37, Well-Worn 0.37-0.44 and Battle-Scarred 0.44-1.0 [E 13].
  Default = the shipped look.
- **Camo:** CS:GO tiles over the weapon's UVs for hydrographic, patina and custom paint, and uses triplanar
  projection for spray paint and airbrush. Pattern scale is set per weapon size [E 13]. UV camo works across guns
  only if texel density and UV orientation are consistent (UV-up = gun-up, the standard in 6.1). Triplanar avoids
  the UV dependency. On a skeletal gun it needs the pre-skinned local position so it does not swim on moving parts
  [J, UNVERIFIED 5.8].
- **Refinishable region** (Masks.A) is CS:GO's idea: only some parts take a finish, and an alpha mask sets each part's
  durability [E 13, 14 SECONDARY]. Rubber pads, lenses, sights and the bore stay unpainted.

**The masks texture, per gun (ship from the first build).** `T_<Gun>_Masks.png`, linear RGBA, ORM_rgba import
settings (TC_MASKS):

| Channel | Content |
|---|---|
| R | edge-wear propensity (convexity x exposure, 0-1) |
| G | handling and contact propensity (the painted zones in section 3, plus sliding parts) |
| B | cavity / grime (AO-gated concavity) |
| A | refinishable coating region (1 = coated metal or paintable furniture, 0 = bare metal, rubber, glass, sights) |

The shipped BC and ORM are the baked look at the default Wear Amount, so the gun renders correctly on today's
masters. The masks only start working once `M_Weapon_Master` exists, and no re-bake is needed then.

### 4.5 Skins for the battle royale [J, E]

- **Tier 1, colour variants:** one MIC per variant (Coating Colour, Wood Tone). Zero new textures. Works on today's
  Fabric master for dark colours.
- **Tier 2, camo patterns:** one MIC per pattern, plus one tileable pattern texture (1024², shared by every gun).
  APB built "new weapon skins without having to create custom textures for each weapon" from a super-shader plus
  per-weapon masks [E 15]. Fab packs ship this model: one master plus instances with albedo, normal and a packed mask
  [E 17], 12 tileable skin textures [E 17], and runtime-switchable, replicated skins [E 17].
- **Tier 3, unique painted skins:** a full BC+ORM override on the same UVs. Memory cost equals a new gun texture set,
  so keep it rare.
- **Data:** skins are Primary Data Assets with soft references, and only the skin ID is replicated [M:
  ASSET_GUIDELINES 12.x]. Custom Primitive Data can carry per-instance colour without new MICs and cuts draw calls
  for repeated meshes [E 16]. That suits ground loot. Material Layers give a UI to swap layers in a MIC [E 16]. Not
  needed for v1.
- **Draw calls [J]:** keep at most 3 material slots per gun (Metal/Coating, Furniture, Optics). Ground loot in a
  battle royale multiplies them, and the magazine shares the gun's atlas.

---

## 5. Real-world dimensions (scale and physics sanity)

Published figures for the real guns each design is "in the style of". Our designs are original, but overall length,
barrel and mass set the scale. Unreal mass in kg goes on the physics body.

| Our gun | Style reference | Overall length | Barrel | Mass empty | Magazine | Other |
|---|---|---|---|---|---|---|
| **Rifle AR-01** | AKM [E 18] | **880 mm** (fixed stock) | **415 mm** | **3.3 kg** | 30-rd curved, **0.33 kg** loaded; AKM ribbed steel about 223 mm long (1 in shorter than the 248 mm early mag) [E 30, SECONDARY]; polymer 30-rd 232 x 64 x 32 mm (height x depth x width) [E 30] | sight radius 378 mm; muzzle **14x1 LH** [E 18, 28] |
| **SMG** | UMP45 [E 19] | **690 mm** stock extended, **450 mm** folded | **200 mm** | **2.5 kg** | 25-rd straight; magwell about 30 x 42.5 mm [E 31, SECONDARY]; about 245 mm long (airsoft copy) [SECONDARY] | — |
| **Carbine** | M4 [E 20] | **838 mm** extended, 756 mm retracted | **368 mm** | **2.92 kg** (3.52 loaded with sling) | 30-rd STANAG: one polymer product 223 x 57 x 29 mm (8.79 x 2.25 x 1.125 in) [E 29]; about 0.11 kg empty [SECONDARY] | muzzle 1/2-28 |
| **Long rifle** | M16A2/A4 [E 21] | **1,007 / 1,000 mm** | **508 mm** | **3.40 kg** (4.00 loaded with sling) | same as carbine | sight radius 502 mm; muzzle **1/2-28** [E 21] |
| **Sniper** | AWM-class chassis bolt gun [E 23] | **1,270 mm** (the prompt asked for about 1.2 m) | **686 mm** | **6.9 kg** | 5-rd box | muzzle 5/8-24 class for .30 [E 28] |
| **Pistol** | Desert Eagle Mk XIX, 6 in [E 22] | **273 mm** | 152 mm | **2.0 kg** | 7-rd (.50) | height 159 mm, width 32 mm |

**The sheet rulers are wrong, and by how much [M]** (`extent.py`: gun extent in the LEFT panel against that panel's
ruler):

| Sheet | Length by its own ruler | Real reference | Over | Length / height |
|---|---|---|---|---|
| Rifle | about 97-99 cm | 88.0 cm | +11-13 % | 3.84 |
| SMG | 86.7 cm | 69.0 cm | +26 % | 2.04 |
| Carbine | 97.3 cm | 83.8 cm | +16 % | 3.06 |
| Long rifle | 117.0 cm | 100-100.7 cm | +16-17 % | 3.39 |
| Pistol | 29.7 cm | 27.3 cm | +9 % | 1.55 |

So: scale each gun so its overall length matches the table above, then check proportions with the sheet's
length/height ratio, which does not depend on the ruler. The prompts file already says the rulers are unreliable
[M].

---

## 6. Cross-gun standards

### 6.1 Axes, pivot and the hand frame (one animation set per class)

- **Bore axis** on the mesh forward axis that lands on **Unreal +X**, up = +Z, the gun's right side = +Y in Unreal.
  Use the pipeline's axis convention from the sidecar (`axis` block; the katana's is forward -Y, up Z in Blender
  [M]). Verify on the first gun import.
- **Pivot = `GRIP_R`, the firing-hand grip point:** on the grip's centre plane, on the grip axis, at the height where
  the web of the hand meets the backstrap or tang. The house rule is "pivot placement: grip point for weapons" [M:
  ASSET_GUIDELINES 1]. The socket's +X runs **up the grip axis**, so the grip angle (AR about 25°, AK steeper,
  pistols vary) is absorbed by the socket rather than the animation [J].
- **Why one animation set fits:** shooter rigs animate a dedicated `ik_hand_gun` bone (under `ik_hand_root`) and
  attach every weapon to it, with `ik_hand_l` / `ik_hand_r` carrying the hand targets [E 32]. Kinemation's pack
  attaches all weapons to one virtual pivot bone and applies **per-weapon transform offsets** to the IK bones, so one
  animation works across weapons [E 32]. Every gun needs a left-hand socket **with the same name**: on the root for
  rigid guns, on the pump bone for a pump shotgun [E 32]. Hand-reference systems do the same through a reference
  mesh with fixed hand bones [E 32].
- **Classes:** long gun (rifle, SMG, carbine, long rifle, sniper, later the shotgun, DMR and LMG) and pistol. Each
  class shares one animation set. Per gun, only socket transforms change [J].
- **Grip envelope [J, verify on the Manny or MetaHuman hand]:** grip cross-section about 28-35 mm wide and 45-55 mm
  front-to-back at mid-height; trigger reach (backstrap to trigger face) about 65-75 mm. Guns outside this envelope
  (the large pistol) need a hand-pose variant, not a new animation set.
- Weapon sockets on `hand_r` / `hand_l` remain the house plan for the character [M: ASSET_GUIDELINES 7]. The
  `GRIP_R` socket is what lines up with them.

### 6.2 Socket set (fixed names, sidecar-applied as today)

Static or skeletal, the names are the same. They are Empties plus `.sockets.json`, applied by `ue_import_sockets.py`
[M: pipeline]. For a skeletal gun, `skeletal_prop.py` writes sockets on bones [M].

| Socket | Where | Axes |
|---|---|---|
| `GRIP_R` | firing-hand grip point (= pivot) | +X up the grip axis, +Z toward the bore |
| `GRIP_L` | support-hand hold point: handguard (long guns), magwell (SMG hold), trigger guard or firing hand (pistol) | +X along the bore |
| `AIM` | on the sight line at the rear aperture or notch | +X through the front sight; an optic attached to a rail overrides it with its own `AIM` |
| `MUZZLE` | centre of the muzzle face, on the bore axis | +X forward |
| `MUZZLE_SEAT` | the barrel shoulder where devices seat (front of the threads) | +X forward |
| `MAG` | where the magazine's origin lands when seated (6.6) | +Z = insertion direction, reversed |
| `EJECT` | ejection port centre | +X = ejection direction |
| `RAIL_TOP` / `RAIL_BOTTOM` / `RAIL_L` / `RAIL_R` | rear end of each rail's top centreline, in the rail-top plane | +X forward along the slots, +Z out of the rail |
| `SLING_F` / `SLING_R` | sling swivel or QD centres | — |
| `CenterOfMass` | as on the katana [M] | — |

The sidecar adds a few fields per gun: `rail_slots` per rail, `muzzle_class`, `mag_family`, `texel_density_px_cm`
and `class` (longgun or pistol).

### 6.3 Accessory rail: MIL-STD-1913 profile, one code module

| Dimension | Value |
|---|---|
| Width across the dovetail | **21.2 mm** (0.835 in, tolerance 0.835-0.830) [E 24, 25, 26] |
| Top flat width | about 15.7 mm (0.617 in) [E 26, SECONDARY] |
| Dovetail flank angle | **45°** [E 25] |
| Slot (recoil groove) width | **5.23-5.26 mm** (0.206 in) [E 24, 25] |
| Slot centre spacing | **10.01 mm** (0.394 in) [E 24, 25] |
| Slot depth | **3.00 mm** (0.118 in) [E 24]; picatinny.se's "0.180 in" is a conversion slip |
| Rail height | not set by the standard [E 25]; about 9.5 mm (0.375 in) is common [E 26, SECONDARY] |
| Slot bottoms | square [E 24] |

- Module: `rail_1913(n_slots, length_pad)` produces the exact cross-section with crisp 0.3-0.5 mm bevels [J].
  Every gun calls it, so every attachment fits every rail by construction.
- **Attachment snap:** each attachment's `MOUNT` Empty sits at its cross-bolt centre in the rail-top plane. Its
  position on a gun = `RAIL_x + (k + 0.5) x 10.01 mm` along +X, for slot index k from the rear. Only integer slots
  are allowed, as on a real gun.
- The 1913 standard is a public military specification, so its dimensions are fine to use. In listings, say
  "1913-profile accessory rail" [J].
- **Slotted handguard (carbine):** M-LOK-style slots are about 32 x 7 mm with 8 mm between slots (40 mm pitch), with
  mounting positions every 20 mm [E 27]. M-LOK is a Magpul trademark, so name it "slotted handguard" and give our
  slots an original pattern, as the carbine prompt asks [M]. The kit then mounts short 1913 sections on the slots.

### 6.4 Muzzle and suppressor interface

- Real threads differ by calibre: 1/2-28 (5.56 and most 9 mm), 5/8-24 (.30 calibre), 14x1 LH (AKM) [E 28].
- **Game standard [J]:** the muzzle device (AR-01 slant brake, SMG and carbine flash hiders, long-rifle slotted
  hider) is a **separate part**: its own mesh section, bone or static mesh. A suppressor *replaces* it, never sits
  over it. Every gun has `MUZZLE_SEAT`. One suppressor mesh with a rear collar about 35-45 mm across hides the
  differences between barrels, so **one suppressor fits all guns**. The sidecar's `muzzle_class` (T12.7, T15.9,
  T14L) is kept for realism, for a later "adapter" cosmetic.
- `MUZZLE` drives the muzzle flash and tracer origin; the suppressor carries its own `MUZZLE` that overrides it.

### 6.5 Shared receiver families and parts as code modules

| Family | Members | Shared modules (proposed `Scripts/guns/parts/`) |
|---|---|---|
| AR family | Carbine, Long rifle (later an LMG may take the same magazine) | `ar_lower` (magwell, controls, trigger guard, grip mount), `ar_upper(top = flat_rail or carry_handle)`, `ar_barrel(length_mm = 368 or 508, profile)`, `ar_stock(collapsible or fixed)`, `mag_ar(rounds = 30 or 20)` |
| AK family | Rifle AR-01 (later a DMR variant) | `ak_receiver`, `ak_dustcover(rail = False or True)`, `mag_ak(30)`, wood furniture modules |
| SMG family | SMG (later a second SMG may reuse the stick-magazine module) | `smg_receiver`, `fold_stock`, `mag_stick(rounds)` |
| Pistol | Pistol | `pistol_frame`, `pistol_slide`, `mag_pistol` |
| Line-wide | every gun | `rail_1913`, `sight_post`, `sight_aperture`, `screw(head, d)`, `pin(d = 4 or 5 mm)`, `sling_swivel`, `qd_socket`, `selector_lever`, `trigger`, `muzzle_device(kind)` |

Same pattern as `props_lib/<item>_*.py`. Each module returns geometry plus its sockets, so the build script places
parts by their sockets, not by hand-typed coordinates [J].

### 6.6 Magazine interface

- **Magazine origin:** centre of the feed-lip opening, in the plane of the magwell entry, with +Z = the reverse of
  the insertion direction. The gun's `MAG` socket has the same frame. Any magazine of the family then snaps, and the
  reload animation's insertion path is the socket's -Z [J].
- Magazines are separate meshes, or bones on a skeletal gun, sharing the gun's atlas. A family magazine shared
  across guns (the AR magazine) gets its own small atlas so it does not tie two guns' textures together [J].
- Extended magazines (attachments kit) keep the same origin and frame and only grow downward.

### 6.7 If guns are skeletal (the rig role decides): bone names across the line [J]

The house convention applies: the armature object is named `root` and the moving bones are top-level [M:
skeletal_prop.py]. Use the same names on every gun so one AnimBP layer can drive them: `Mag`, `Bolt` (or `Slide` on
the pistol, `BoltHandle` on the sniper), `ChargingHandle`, `Trigger`, `Selector`, `MagRelease`, `DustCover`,
`Hammer`, `Stock` (SMG fold), `SightRear`, `SightFront`, `Bipod_L` / `Bipod_R`, `MuzzleDevice`. A static build
(`SM_` plus a separate magazine) keeps the same socket names, so the standards hold either way.

---

## 7. What the AR-01 plan and the SMG must change

**AR-01 (rifle), now:**
1. **Pivot at `GRIP_R`**, with `GRIP_L` on the lower-handguard hold point, `AIM` on the rear-sight notch line, plus
   `MUZZLE`, `MUZZLE_SEAT`, `MAG`, `EJECT`, `SLING_F` / `SLING_R` and `CenterOfMass`, using the names in 6.2.
2. **Slant brake as a separate part**, so a suppressor can replace it (`muzzle_class` T14L).
3. **Scale to 880 mm overall, 415 mm barrel**; 3.3 kg body and 0.33 kg loaded magazine for physics. Ignore the
   sheet ruler (+11-13 % measured).
4. **Materials:**
   - Metal is **black lacquer over steel**: dielectric, base colour about 0.03-0.04 (sRGB 45-55), roughness
     0.45-0.6, wearing to **bare steel** (metallic 1, 0.53-0.56, roughness 0.25-0.4).
   - Wood is **walnut-tone shellac**: hue about 19-21°, sat 0.45-0.65, about 0.05 linear, roughness 0.35-0.55, worn
     to lighter raw wood at the handguard belly, grip palm swell and comb.
   - On today's masters: coated metal → `M_Fabric_Master` + Metal From ORM (dark, so the 4.3 trap is not hit); wood
     → `M_Fabric_Master`; polished small steel → `M_Steel_Master`. Additions only, katana precedent.
5. **Bake and ship `T_AR01_Masks`** (R edge, G handling, B cavity, A refinishable) and a Detail16 for each
   recolourable slot, so `M_Weapon_Master` and camo skins later need no re-bake.
6. **Wear placement for this design:** receiver and dust-cover edges and ribs; the selector lever and the arc it
   sweeps on the receiver; a polished charging handle; magazine spine, feed lips and baseplate corners; front-sight
   ears; muzzle crown with soot; butt-plate bottom edge and toe; stock heel dents.
7. **Rail decision (8.4):** the sheet shows no rail. If the attachments kit must fit AR-01, add an original
   `ak_dustcover(rail=True)` or handguard rail module. It is also a useful original design change for IP distance.
8. If AR-01 ships a light birch or laminate variant, keep metal out of the wood slot (or wait for
   `M_Weapon_Master`). See 4.3.

**SMG, next:** black glass-filled polymer (0.02-0.04, roughness 0.5-0.7, stippled grip 0.75-0.9) that wears by
**polishing**, not by revealing metal. Phosphated steel barrel and small parts (0.03-0.06, roughness 0.65-0.85).
Top and bottom rails from `rail_1913`. `GRIP_L` at the magwell or lower rail. The folding stock is a `Stock` bone or
part. 690 / 450 mm, 200 mm barrel, 2.5 kg. A tan or FDE variant hits the 4.3 trap.

---

## 8. Open questions (the user's decisions)

1. **`M_Weapon_Master`:** add one shared weapon master (coating recolour, Wear Amount, camo, grime) before the Fab
   gun pack and battle-royale skins? It costs a PackMaterials-lock session. The alternative is keeping guns on
   today's masters, which gives no camo and dark colours only.
2. **Battle-royale skin tiers:** colour variants only, camo patterns (cheap, shared textures), or also unique painted
   skins (a full texture set each)?
3. **One universal suppressor/muzzle standard (game-friendly) or calibre-faithful thread classes?** Recommended:
   universal, with the class kept as data.
4. **A rail on the AK-style rifle?** A dust-cover or handguard rail as an original design change, so the attachments
   kit fits it.
5. **Wood variants for AR-01:** walnut only, or birch, laminate and blonde too? Light woods need 4.3's workaround or
   the new master.
6. **Real scale or "game-prop" scale for the fictional sniper, pistol and long rifle?** The prompts said about 1.2 m,
   27 cm and 100 cm; real references give 1.27 m, 27.3 cm and 1.00 m. Recommended: the real figures within ±5 %.
7. **First-person texture budget per gun:** 2048 atlas (about 30 px/cm) or 4096 (about 65 px/cm)? This sets how fine
   the wear can be.

---

## 9. Sources

1. Epic, *Physically Based Materials in Unreal Engine* (base colour tables, Specular 0.5 = 4 %, metallic binary):
   https://dev.epicgames.com/documentation/unreal-engine/physically-based-materials-in-unreal-engine
2. Physically Based database (A. Palmqvist), API: https://api.physicallybased.info/materials ; overview:
   https://www.cgchannel.com/2022/08/physically-based-is-an-amazing-database-of-pbr-material-values/
3. S. Lagarde, *DONTNOD physically based rendering chart for Unreal Engine 4* (dielectric sRGB 50-243, metal
   186-255): https://seblagarde.wordpress.com/2014/04/14/dontnod-physically-based-rendering-chart-for-unreal-engine-4/
4. Albedo chart values for wood (fresh 0.35-0.42, weathered 0.12-0.16, varnished 0.13) [SECONDARY, via search
   summary]: https://shinsoj.artstation.com/blog/Q9j6/pbr-color-space-conversion-and-albedo-chart ; see also
   http://wiki.polycount.com/wiki/PBR
5. Magnetite reflectance about 20-22 % across the visible [SECONDARY summary]:
   https://www.sciencedirect.com/science/article/abs/pii/S0019103518302252 ; https://www.mindat.org/min-2538.html
6. Phosphate and black-oxide coatings guide (manganese phosphate dark grey to black, matte, porous; zinc phosphate
   light to medium grey): https://www.trojansf.co.uk/phosphating
7. Type III hard anodizing colours (black, dark grey, dark bronze, natural):
   https://www.rivcut.com/blog/anodizing-type-comparison ; https://caswellplating.com/hardcoat-type-iii-anodizing-system.html
8. Cerakote H-series gloss guide and TDS (matte, eggshell, satin; measured at 60°):
   https://www.cerakoteeu.com/knowledge-base/gloss-guide-h-series-coatings/ ;
   https://images.nicindustries.com/cerakote/documents/175/h-series-all-in-one-tds-dt20200115005900675.pdf
9. Paint sheen gloss-unit bands: https://en.wikipedia.org/wiki/Paint_sheen
10. Epic, material inputs (Anisotropy, Tangent; "Use anisotropic BRDF (Beta)"):
    https://dev.epicgames.com/documentation/en-us/unreal-engine/material-inputs-in-unreal-engine ;
    https://www.unrealengine.com/en-US/tech-blog/improved-shading-models-in-unreal-engine-4-25-and-beyond
11. 80.lv, AK-74 modelling and texturing (rust, paint and grease layers, hand-painted wear, 5+ texture sets):
    https://80.lv/articles/how-to-model-and-texture-a-realistic-ak-74-using-3ds-max-zbrush-and-substance-3d
12. 80.lv weapon breakdowns (wear and heat zones, lifecycle order, edge vs surface wear) [SECONDARY summary]:
    https://80.lv/articles/weapon-art-plasma-akm-production-breakdown ;
    https://80.lv/articles/breakdown-how-to-make-a-weapon-look-realistic-and-eye-catching ;
    https://80.lv/articles/sks-hard-surface-texturing-in-weapons-art
13. Valve, CS:GO Workshop finishes (wear bands, UV vs triplanar styles, pattern scale, albedo ranges, durability
    alpha): https://www.counter-strike.net/workshop/workshopfinishes
14. Valve Developer Community, CS2 weapon finishes (wearness, patina and gunsmith masks) [SECONDARY, 403, via search
    summary]: https://developer.valvesoftware.com/wiki/Counter-Strike_2_Workshop_Tools/Weapon_Finishes
15. APB Reloaded weapon pipeline (super-shader instances, per-weapon masks, skins without per-weapon textures):
    https://apbreloaded.blogspot.com/2016/06/apb-reloaded-weapon-pipeline-overview.html
16. Epic, Material Layers and Custom Primitive Data:
    https://dev.epicgames.com/documentation/en-us/unreal-engine/using-material-layers-in-unreal-engine ;
    https://dev.epicgames.com/documentation/en-us/unreal-engine/storing-custom-data-in-unreal-engine-materials-per-primitive
17. Fab and Marketplace weapon packs [SECONDARY, listing summaries]: FPS Weapon Pack
    https://www.unrealengine.com/marketplace/en-US/item-detail/40d1f3ab15944a6db997e7e528bb4805 ; Weapon Kit
    https://www.fab.com/listings/38ecb3f5-fc80-4f58-b579-2dfa0656617f ; Ultimate Weapon Pack
    https://www.fab.com/listings/40dbe4dc-bfc2-4854-b960-6335bae64e3d ; Modern Weapon Camouflage Pack
    https://www.fab.com/listings/35c10cd7-892e-456c-b7bb-6aa5e701a983
18. AKM: https://en.wikipedia.org/wiki/AKM
19. UMP: https://en.wikipedia.org/wiki/Heckler_%26_Koch_UMP
20. M4 carbine: https://en.wikipedia.org/wiki/M4_carbine
21. M16 rifle: https://en.wikipedia.org/wiki/M16_rifle
22. Desert Eagle: https://en.wikipedia.org/wiki/Desert_Eagle
23. AWM: https://en.wikipedia.org/wiki/Accuracy_International_AWM
24. Picatinny rail: https://en.wikipedia.org/wiki/Picatinny_rail
25. Picatinny rail dimensions: https://www.picatinny.se/en/blogs/videnscenter/picatinny-skinne-maal-dimensioner
26. Picatinny and NATO rail GD&T (0.835-0.830 width, 0.617 flat) [SECONDARY summary]:
    https://www.thomasmechanicaldesign.com/the-mitch-blog/picatinny-and-nato-rails-gdt
27. M-LOK: https://en.wikipedia.org/wiki/M-LOK ;
    https://www.at3tactical.com/blogs/news/the-complete-guide-to-the-m-lok-attachment-system
28. Suppressor thread pitches by calibre: https://blog.primaryarms.com/guide/most-common-thread-for-suppressor-guide/ ;
    https://www.capitolarmory.com/articles/suppressor-thread-pitch-guide
29. 30-round AR magazine product dimensions: https://missionfirsttactical.com/SCPM556BAG
30. AK 30-round polymer magazine dimensions: https://www.leapers.com/products-utg-rbt-akm30.html ; steel magazine
    lengths [SECONDARY]: https://en.wikipedia.org/wiki/7.62%C3%9739mm
31. UMP magwell dimensions [SECONDARY, forum]: https://www.hkpro.com/threads/ump-mag-well-dimensions.194009/
32. Weapon hand IK and pivot practice: https://zaggoth.wordpress.com/2019/01/26/ue4-tutorial-the-right-way-to-do-left-hand-weapon-ik/ ;
    https://kinemation.gitbook.io/tactical-shooter-pack-unreal/animations/character ;
    https://neilgilbertg.ca/2024/04/18/ue5-hand-reference-based-weapon-animation-system-2-0/
33. Soviet AK stock finish (shellac or varnish) [SECONDARY, forum]:
    https://www.theakforum.net/threads/how-were-original-russian-akm-stocks-finished.50554/
