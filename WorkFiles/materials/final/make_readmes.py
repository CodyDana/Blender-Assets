"""Write the buyer-facing MATERIALS_README.md of every item (NEW files beside the frozen exports). System Python.

    py -3 WorkFiles/materials/final/make_readmes.py

The text is shared where the items share behaviour, so the four files never contradict each other. Numbers come from
the final build (build/dump_f2.json) and the final stress tests (final/recolour/).
"""
import json
from pathlib import Path

P = Path("C:/Users/Cody/Desktop/Blender_Projects")
SUPPORT = (P / "WorkFiles/materials/final/compat/support_text.md").read_text(encoding="utf-8").strip()

HEADER = """# {title}: materials and colours (Unreal Engine 5.8)

This file explains the item's Unreal materials: where they are, how to change a colour, and what to leave alone.
The pack's content folder is `/Game/NinjaPack/` (a working name: the folder can be renamed, no asset name contains it).
"""

LAYOUT = """## Where things are

| Folder | What is in it |
|---|---|
| `/Game/NinjaPack/Meshes/` | The static meshes, with their material slots already assigned |
| `/Game/NinjaPack/MaterialInstances/` | **The instances you edit**: one per material slot, named `MI_<Item>_<Part>` |
| `/Game/NinjaPack/MaterialInstances/Base/` | `MI_<Item>_<Part>_Base`: holds the textures and the settings matched to them. Leave these alone |
| `/Game/NinjaPack/MaterialInstances/Presets/` | Ready-made alternatives (for example the kunai's undyed grip) |
| `/Game/NinjaPack/Materials/` | The three master materials (`M_Steel_Master`, `M_Fabric_Master`, `M_PaperInk_Master`) and `Functions/`. You never need to open these |
| `/Game/NinjaPack/Textures/` | The textures, one folder per item, plus `Default/` (tiny neutral textures the masters use as placeholders) |

Every item only references its own textures, so you can migrate a single item to another project without dragging
the others along.
"""

STEPS = """## Change a colour in three steps

1. In the Content Browser, open `/Game/NinjaPack/MaterialInstances/{mi}` (double-click).
2. At the top of the Details panel, in the group **01 Colour**, the **{param}** box is already ticked. Click its colour swatch.
3. Pick a colour, or type a web colour into the picker's **Hex sRGB** field (for example `8B1A1A`). Click OK. The change is live in every level.

**Want a variant and keep the original?** Editing `{mi}` recolours every copy of the item in your project. For a
second colour, right-click `{mi}` > **Create Material Instance** (or Duplicate), give it a name, change its colour, and
assign it to the mesh's material slot on the placed actor (Details panel > Materials).

**What the colour means.** It is the part's *average* colour. The {detail} are built into the material and follow
the new colour automatically, so you do not need to edit any texture. The picker's R/G/B numbers are linear values;
the Hex sRGB field is the one that matches colours from the web or from an image editor.
"""

GOOD_TO_KNOW_FABRIC = """## Good to know

- **Very light colours are capped** at the part's **Lightest Colour** (group 01 Colour, {lightest_hex} for this
  part). A pick lighter than that keeps its hue but is scaled down to it, so the bright {highlights} keep their detail
  instead of turning into flat white. Want it brighter and accept softer highlights? Tick **Lightest Colour** and
  raise it (0.9 = no cap).
- **Pure black is lifted** to about `#191919`, so the {detail} stay visible. Any colour with a channel above that is
  used as picked.
- **Distance:** the part keeps the same average colour close up and far away (the material compensates for texture
  filtering at a distance).
- **Detail Strength** (02 Detail): 1 = as shipped, 0 = flat colour. On very light colours the highlight detail is
  limited automatically, so values above 1 mainly deepen the darker weave.
"""

BACK = """## Get the original look back

- Click the **reset arrow** next to a parameter (or untick it): it goes back to the value the item shipped with.
- Tick the box of **Use Original Baked Colours** (01 Colour) and switch it on to show the original baked colour map exactly as shipped,
  ignoring the colour settings.
"""

LEAVE = """## Leave these alone

- The `_Base` instances in `MaterialInstances/Base/`: they hold the textures and the settings matched to them.
- The group **08 Advanced (matched to ... - do not change)**: these numbers are computed from the item's textures.
  Changing them shifts the average colour and the detail.
- The textures in **09 Textures**: swap a detail map only together with its matched 08 Advanced settings.
"""

SUPPORTED = """## Supported setups

""" + SUPPORT + "\n"

FABRIC_PARTS_TABLE = """## The colours you can change

| Part | Instance to edit | Parameter | Shipped colour (Hex sRGB) | Lightest Colour |
|---|---|---|---|---|
{rows}
"""


def fabric_rows(parts):
    return "\n".join(f"| {p} | `{mi}` | 01 Colour > Colour | `#{hx}` | {lh} |" for p, mi, hx, lh in parts)


def write(path, text):
    path = Path(path)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.write_text(text, encoding="utf-8")
    print("wrote", path)


# ------------------------------------------------------------------------------------------------ shuriken + kunai
shuriken = HEADER.format(title="Shuriken pack (six stars and the plain kunai)") + "\n" + LAYOUT + """
## Instances

| Mesh | Slot | Instance | Recolourable |
|---|---|---|---|
| `SM_Shuriken_FourPoint`, `_EightPoint`, `_SquarePlate`, `_SixPoint`, `_Spike`, `_HookedCross` | steel | `MI_Shuriken_<Form>_Steel` | Steel tint only (optional) |
| `SM_Kunai_Plain` | 0, blade and ring | `MI_Kunai_Plain_Steel` | Steel tint only (optional) |
| `SM_Kunai_Plain` | 1, grip wrap | `MI_Kunai_Plain_Wrap` | **Yes**: 01 Colour > Colour (shipped `#373532`, Lightest Colour `#CBCBCB`) |
| (preset) | grip wrap | `Presets/MI_Kunai_Plain_Wrap_Undyed` | The natural, undyed grip as a fixed colour |

## The steel

The steel keeps its metal look. **Steel Tint** (01 Colour) multiplies the steel's colour: white = exactly as shipped,
warm `(1.0, 0.8, 0.6)` for a bronze tone, cool `(0.8, 0.9, 1.0)` for blued steel. **Roughness Adjust** (03 Surface)
makes it more polished (negative) or duller (positive). Steel Tint is a multiplier, while a fabric's Colour is the
colour itself: the steel's colour comes from the metal's reflection, so it can only be tinted.

""" + STEPS.format(mi="MI_Kunai_Plain_Wrap", param="Colour", detail="weave, fibre and wear detail of the grip tape") + "\n" + \
    GOOD_TO_KNOW_FABRIC.format(lightest_hex="`#CBCBCB`", highlights="tape ridges", detail="tape and weave") + "\n" + BACK + """- For the natural, undyed grip use `Presets/MI_Kunai_Plain_Wrap_Undyed` (assign it to the kunai's slot 1).

""" + LEAVE.replace("matched to ...", "matched to the detail map") + """
## Kunai: sheen

The grip ships without Unreal's Cloth sheen (**04 Sheen > Cloth Sheen** off), because plain shading matched the
original look more closely in a measured comparison. The original preview had a faint glint on the tape at grazing
angles that neither Unreal option reproduces; you will notice it only in extreme close-ups. Tick **Cloth Sheen** for
a softer, dusty read (the Sheen Colour and Amount are preset to calibrated values).

## Kunai: lettering

The grip has a blank band for your own text. To letter it:

1. Paint white text on a black **1536 x 256** greyscale image (white = ink). Look at the band face-on with the tip to
   your right: the image reads left to right from the ring end towards the tip. For extreme close-ups use 3072 x 512.
2. Import it with sRGB **off**, Compression **Grayscale**, Address X and Y **Clamp**, Power Of Two Mode **Stretch to
   power of two**, and Mip Gen Settings **From Texture Group** (a 1536-wide image otherwise imports without mips and
   shimmers at a distance).
3. In `MI_Kunai_Plain_Wrap`: tick **05 Lettering > Use Lettering**, set **Lettering Mask** to your image, and pick
   **Lettering Colour** (a light worn paint `(0.62, 0.56, 0.44)` suits the dark grip) and **Lettering Roughness**.

Leave **Lettering Band UV** as it is: it is where the band sits on the kunai's UVs. The lettering options show on the
other fabric items too but do nothing there.

""" + SUPPORTED

# ------------------------------------------------------------------------------------------------ smoke bomb
smoke = HEADER.format(title="Smoke bomb") + "\n" + LAYOUT + "\n" + FABRIC_PARTS_TABLE.format(rows=fabric_rows(
    [("Cloth wrap", "MI_SmokeBomb_Cloth", "3F3A37", "`#C5C5C5`")])) + "\n" + \
    STEPS.format(mi="MI_SmokeBomb_Cloth", param="Colour", detail="threads, weave and wear") + "\n" + \
    GOOD_TO_KNOW_FABRIC.format(lightest_hex="`#C5C5C5`", highlights="threads", detail="threads and weave") + """- The smoke bomb's cloth has very bright single threads on a dark weave. On light colours the brightest threads
  are softened towards a gentle ceiling rather than cut off, so no flat white areas appear.
- The material shows the item's texture maps exactly. The original Blender preview renders reported the cloth a little
  darker (about 7 %) than its own maps, because of how Cycles filters 8-bit textures; Unreal shows the maps' true
  colour. If you prefer the darker preview tone, set the Colour about 7 % darker.

""" + BACK + "\n" + LEAVE.replace("matched to ...", "matched to the detail map") + "\n" + SUPPORTED

# ------------------------------------------------------------------------------------------------ black hat
hat = HEADER.format(title="Black hat (straw hat with cloth band)") + "\n" + LAYOUT + "\n" + FABRIC_PARTS_TABLE.format(
    rows=fabric_rows([("Straw", "MI_BlackHat_Straw", "3F3C3B", "`#CBCBCB`"),
                      ("Cloth band and ties", "MI_BlackHat_Cloth", "383737", "`#CBCBCB`")])) + """
The straw and the cloth band are separate: change one, the other, or both.

""" + STEPS.format(mi="MI_BlackHat_Straw", param="Colour", detail="straw strands, stitching and wear") + \
    "\nFor the band, do the same in `MI_BlackHat_Cloth`.\n\n" + \
    GOOD_TO_KNOW_FABRIC.format(lightest_hex="`#CBCBCB`", highlights="straw strands", detail="strands and weave") + \
    "\n" + BACK + "\n" + LEAVE.replace("matched to ...", "matched to the detail map") + "\n" + SUPPORTED

# ------------------------------------------------------------------------------------------------ paper bomb
paper = HEADER.format(title="Paper bomb (explosive tag)") + "\n" + LAYOUT + """
## The colours you can change

All three are in the one instance `MI_PaperBomb_Tag`, group **01 Colour**, and all three are already ticked.

| Colour | What it changes | Shipped (Hex sRGB) |
|---|---|---|
| **Paper Colour** | The paper, with its grain, ageing, stains and the show-through on the back | `#F5E1BB` |
| **Black Ink Colour** | The brushed text and emblem; the dry-brush strokes follow it | `#080907` |
| **Red Ink Colour** | The border, ring and seals; the dry-brush strokes and the dark knob follow it | `#CA170C` |

""" + STEPS.format(mi="MI_PaperBomb_Tag", param="Paper Colour (or Black Ink Colour, Red Ink Colour)",
                   detail="paper grain, ink edges and dry-brush strokes").replace(
    "the **Paper Colour (or Black Ink Colour, Red Ink Colour)** box is already ticked",
    "the **Paper Colour**, **Black Ink Colour** and **Red Ink Colour** boxes are already ticked").replace(
    "ticked. Click its colour swatch.", "ticked. Click the swatch of the one you want to change.") + """
## Good to know

- **The lightest paper is about `#F4F4F4`.** A lighter Paper Colour keeps its hue but is scaled down to it, so the
  grain never turns into flat white. **Pure black paper is lifted** to about `#191919` so the grain stays visible;
  very dark papers show the grain only faintly (that is the limit of 8-bit colour, not a fault).
- **Inks are flat colour inside solid strokes**, as painted ink is; their edges, dry-brush strokes and pools carry the
  texture. A white or very light ink therefore reads as a flat light shape inside the strokes.
- **Pooled red ink is always darker** than the Red Ink Colour (ink pools dry dark). A neutral red-ink colour (grey,
  white, black) pools neutral.
- **Baked AO In Colour** (03 Surface): 1 = the original look, where the baked shading also darkens the colour; 0 = none.

""" + BACK + "\n" + LEAVE.replace("matched to ...", "matched to the paper maps") + """
""" + SUPPORTED

write(P / "Exports/Shuriken/MATERIALS_README.md", shuriken)
write(P / "Exports/SmokeBomb/MATERIALS_README.md", smoke)
write(P / "Exports/BlackHat/MATERIALS_README.md", hat)
write(P / "Exports/PaperBomb/MATERIALS_README.md", paper)
