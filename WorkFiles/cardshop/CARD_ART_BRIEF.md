# Card Shop Kit: card art brief (for the user)

**Date:** 2026-09-28. **Decision D4:** the user draws the card illustrations; Claude builds everything around them
(card frames, names, tier colours, backs, pack and box layouts, slab labels) by script. See `CARDSHOP_KIT_SPEC.md` 4.1
for the atlas system these feed.

## What you make

**Only the pictures.** No borders, frames, card names, text or logos inside the image. Claude adds all of those, so
the card layout stays consistent and swappable.

| Line | Theme | How many |
|---|---|---|
| **Pyrecall** | Bold, fiery fantasy: warm palette, beasts, warriors, crests, volcanic places | **6** (up to 16 fit) |
| **Lumenfold** | Mystic, starlit fantasy: cool palette, spirits, sigils, night skies, glowing places | **6** (up to 16 fit) |
| **Rimvault** | The made-up sport: athletes vaulting at a raised hoop with a pole, arenas, action shots | **6** (up to 16 fit) |

18 pictures is enough for the shop to look stocked in screenshots. You can add more later up to 16 per line; the
atlas has room.

**Optional, one per line:** a larger **key art** piece for pack fronts, box art and a shop poster. If you skip it,
Claude crops from the card pictures.

## Size and format

| Item | Shape | Minimum size | Format |
|---|---|---|---|
| Card picture | Landscape, **4:3** (it fills a 55 × 41 mm window on a 63 × 88 mm card) | **1600 × 1200 px** | PNG or JPG, sRGB, under 3 MB |
| Key art (optional) | Portrait, **2:3** | **2000 × 3000 px** | PNG or JPG, sRGB, under 3 MB |

Keep the main subject inside the middle 80% of the picture. The frame may trim the outer edges slightly.

## Where to put it

```
References/CardShop/card_art/pyrecall/pyrecall_01.png ... pyrecall_06.png
References/CardShop/card_art/lumenfold/lumenfold_01.png ...
References/CardShop/card_art/rimvault/rimvault_01.png ...
References/CardShop/card_art/keyart/pyrecall_key.png (optional)
```

Optional: a `names.txt` next to each line's pictures with one card name per line (`01 Magma Warden`). Otherwise Claude
invents names, all original and screened against real card names.

## Rules (so the kit can be sold on Fab)

1. **Your own original work.** No existing characters, creatures, franchise look-alikes or traced art.
2. **Rimvault athletes are invented people.** No real athletes, real teams, team colour-and-logo combos or league marks.
3. **No text, logos or watermarks** in the pictures.
4. **Tell Claude if any AI tool was used** for any picture, even partly. Fab then requires the "Created with AI" tag on
   the whole listing, so it's logged per picture in `CARD_ART_LOG.md` when the art arrives.
5. Blood or gore would force a Mature rating on the whole listing. Keep it clean.

## What Claude does with it

1. Designs the card frame for each line: border, name bar, art window, tier colours (Common / Uncommon / Rare /
   Mythic), set symbol. Also the three card backs and the sleeve-back patterns.
2. Composes each picture into a finished card face and packs them into the `T_CSK_Cards` atlas.
3. Builds the pack and box art from the picture crops or key art plus the brand wordmarks.
4. Runs the IP checks (deny-list scan, barcode test, blind brand test; spec 6.3) and shows you an art sheet for
   approval (gate G2) before anything is baked.
