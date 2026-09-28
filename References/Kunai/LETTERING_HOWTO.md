# Kunai lettering: how to put your own text on the grip

**Asset:** `SM_Kunai_Plain` (shuriken pack, library 3.10.1). **Date:** 2026-09-19.

The kunai ships with **no lettering anywhere**. Its grip has a blank band reserved for your own text, and the text lives in one small greyscale texture, `T_Kunai_Lettering`. It ships blank (all black, no ink). To letter the kunai you replace that one texture. The mesh, the UVs and the other maps stay as they are.

Everything below is measured from the build (`WorkFiles/shuriken/kunai_plain_report.json`, keys `lettering` and `uv_layout.lettering`).

---

## 1. Where the band is on the model

| Item | Value |
|---|---|
| Face | The grip's **+Z face**: the face that is up when the kunai lies flat as built (blade in the XY plane) |
| Length | **72 mm**, from X = -90 to X = -18 mm, measured from the shoulder (the blade base). That leaves 12 mm clear of each end of the wrap |
| Width | **12 mm** of arc on the 20 mm grip, ±34.4° either side of +Z |
| Surface | The tape of the wrap, at its full relief: the wound tape's overlap ridges are modelled, and ink applied through the mask follows them like paint on a real wrap. The band is only a little cleaner than the rest of the grip, feathered over ~4 mm so there is no panel edge |
| Other side | The -Z face has no band. |

## 2. Orientation

**Look at the band face-on with the tip pointing to your right. Your image then reads upright and left to right.**

- The image's **left edge** is the ring end (X = -90). Its **right edge** faces the blade (X = -18). U runs from the ring end toward the tip.
- The image's **top edge** is the band's **+Y** side in Blender's frame. That is the upper edge when you look down at the +Z face with the tip to your right. V runs toward +Y.

The test render in section 7 proves this: the words `RING END` sit at the ring end, `TIP` and its arrow point at the blade, and `+Y` is at the top.

## 3. The texture

| Item | Value |
|---|---|
| File | `Exports/Shuriken/Textures/T_Kunai_Lettering.png` |
| Format | 8-bit **greyscale** PNG. **White = ink, black = no ink**, and grey gives partial ink (antialiasing, worn paint) |
| Shipped size | **1536 x 256 px**: the band's 6:1 at square texels, **21.3 px/mm**. Text 8 mm tall is about 170 px |
| Suggested size | 1536 x 256 for normal use; **3072 x 512** (42.7 px/mm) for extreme close-ups. Keep it 6:1 or the text stretches |
| Mapping | The whole image covers the whole band: the image's (0, 0) to (1, 1) is the band's rectangle |

**Unreal import:** sRGB **off**, Compression Settings **Grayscale**, Address X and Y **Clamp**, Power Of Two Mode **Stretch to power of two**, and **Mip Gen Settings "From Texture Group"**.

1536 is not a power of two. Unreal's texture factory imports a non-power-of-two PNG with **Mip Gen Settings = NoMipmaps**, and setting Power Of Two Mode to Stretch afterwards does **not** reset it — measured twice in fresh UE 5.8.2 processes during the build's review. Without the mip setting the mask ships with a single mip, and lettering painted into it aliases and shimmers as soon as the kunai is more than a metre away (the 72 mm band is about 78 px wide at the LOD1 switch and 27 px at 2.5 m). `Scripts/shuriken/ue_import_textures.py` sets all five and its `verify` mode fails on NoMipmaps.

## 4. The band's UV rectangle

The kunai has two material slots. The steel (slot 0, `M_Shuriken_Master`) keeps its islands in UV tile u 0..1. The wrap (slot 1, `M_Kunai_Wrap`) keeps its islands in **UV tile u 1..2**, so the two layouts never overlap. Its maps (`T_Kunai_Wrap_BC / _ORM / _N`, 1024 px) are sampled with **Wrap** addressing, which is Unreal's default and reads u 1..2 from the same texels as u 0..1.

The whole grip is unrolled as **one straight island** (u along the axis, v around it, seam on -Z), and the band is a **rectangle inside that island** — since 3.10.1, when the review found that giving the band its own island drew a seam round it that read as an outlined panel on the grip.

| Convention | u min | u max | v min | v max |
|---|---|---|---|---|
| **UV0 in Blender** (v up from the image bottom) | 1.13281250 | 1.83593750 | 0.26382741 | 0.38101491 |
| **UV0 in Unreal** (the FBX importer flips V: v' = 1 - v) | 1.13281250 | 1.83593750 | 0.61898509 | 0.73617259 |
| The wrap maps' own 0..1 (Blender convention) | 0.13281250 | 0.83593750 | 0.26382741 | 0.38101491 |

| Wrap-map pixels (1024 x 1024 PNG, origin top-left) | x | rows |
|---|---|---|
| Band rectangle | 136.0 to 856.0 (720 px) | 633.84 to 753.84 (120 px) |

Every LOD carries the same analytic mapping — u = (X + 102 mm) at 10 px/mm, v = the arc from the -Z seam — so that rectangle is the same 72 x 12 mm of cloth on LOD0, LOD1 and LOD2. The build gates it (`lettering.gate`: the mapping on every LOD to 0.01 px, and the rectangle against the band's own region).

## 5. The wrap material's lettering graph

Build this in the wrap material (Unreal: `M_Kunai_Wrap`, with instances `MI_Kunai_Wrap_Dark` and `_Natural`). Blender's gallery preview, `shuriken_lib.kunai_wrap.wrap_preview_material`, builds the same graph.

```
UV        = TexCoord[0]
LettUV    = (UV - Rect.min) / (Rect.max - Rect.min)          // Unreal: Rect = the "UV0 in Unreal" row above
Inside    = (LettUV.x > 0) * (LettUV.x < 1) * (LettUV.y > 0) * (LettUV.y < 1)
Ink       = TextureSample(T_Kunai_Lettering, LettUV).R * Inside   // sampler Clamp
BaseColor = lerp(T_Kunai_Wrap_BC, InkColour, Ink)
Roughness = lerp(T_Kunai_Wrap_ORM.G, InkRoughness, Ink)
Normal    = T_Kunai_Wrap_N                                   // the ink follows the tape relief
```

Suggested parameters: `InkColour` light worn paint (linear 0.62, 0.56, 0.44) on the dark wrap, or near-black on the undyed wrap (`T_Kunai_Wrap_Natural_BC`); `InkRoughness` 0.6. With the shipped blank mask `Ink` is 0 everywhere and the graph changes nothing.

**Status:** the pack has no Unreal materials yet. The validation import runs with `import_materials=False` and both slots bind to WorldGridMaterial. This graph is the specification for the pack's material pass.

## 6. Swapping your lettering in

1. Draw your text white on black in a **1536 x 256** greyscale image. It must be upright, left to right, and have a margin of about 10 px. Keep your own artwork: no traced or franchise text if the kunai goes to Fab (see the Fab note below).
2. Save it over `Exports/Shuriken/Textures/T_Kunai_Lettering.png` with the same name, or save it as a new texture and point the material's `T_Kunai_Lettering` parameter at it.
3. Unreal: reimport the texture, or import it with `ue_import_textures.py`. Check the five flags in section 3 — **Mip Gen Settings included**, or the text will shimmer at a distance.
4. Check it in Blender before Unreal:

   ```
   "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b Assets/Shuriken.blend --factory-startup ^
       --python WorkFiles/kunai/lettering_test/lettering_test_render.py
   ```

   That script renders the grip from above and at 3/4 with the shipped blank mask and with `WorkFiles/kunai/lettering_test/T_Kunai_Lettering_TEST.png`. Point its test path at your file, or copy your file over the test PNG. It never saves the .blend.

**Alternative: no material change.** Paint the text straight into `T_Kunai_Wrap_BC` inside the pixel rectangle in section 4 (x 136 to 856, rows 633.84 to 753.84), with the same orientation (the rectangle's top row is the band's +Y edge). You get only 10 px/mm there, against 21 px/mm in the mask, and the dark and undyed BC maps each need their own copy.

## 7. Test pattern (not shipped)

`WorkFiles/kunai/lettering_test/T_Kunai_Lettering_TEST.png` is a neutral pattern: a frame, a 128 px grid, `RING END`, `ABC 123`, `TIP` with an arrow, `+Y` with an arrow, and corner tags. It was made by `make_test_pattern.py` in the same folder. `lettering_test_sheet.png` puts four renders side by side: the test mask and the shipped blank mask, each from +Z and at 3/4 (`lettering_{test,blank}_{top,34}.png`, rendered by `lettering_test_render.py`). With the test mask, the frame sits on the band's edges, the text reads upright from the +Z face with the tip to the right, and it wraps with the grip's curvature at the 3/4 view. With the shipped mask the band is plain tape.

## 8. Fab note

The kunai itself is generic and Fab-safe: a plain leaf blade, a wrapped grip and a ring pommel, with no franchise feature. If you write franchise text into the mask, the asset carries franchise text again. That is your call for your own game, and a blocker for a Fab listing (`KUNAI_STUDY.md` section 6).
