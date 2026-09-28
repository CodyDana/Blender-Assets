# What to build and sell on Fab: product list (2026-09-28)

**Role:** planning only. Nothing was built. The evidence is in `MARKET_FINDINGS.md`; fees, price rungs and listing rules
are in `FAB_ASSET_STUDY.md` section 4. Prices are **ESTIMATES** from the study's bands (weapon packs $9.99-$59.99,
stylized props $9.99-$19.99, modular kits $49.99-$129.99, MetaHuman outfits $39.99-$49.99), not measured.

## How the list is scored

| Column | Meaning |
|---|---|
| Demand | Fab's 2025/2026 demand signal: High = environments, characters, tools/BP, procedural, VFX; Med = themed props/weapons; Low = niche |
| Gap | How thin the competition looked in search: Open / Thin / Crowded |
| Fit | How well our scripted, headless, hard-surface pipeline builds it: Strong / OK / Weak (organic, sculpted, ornate) |
| Game | Does the ninja duel / battle royale need it anyway? Yes / Later / No |
| Effort | S = days, M = 1-3 weeks, L = a month or more (INFERENCE; no timing data exists yet) |

## Principles behind the order

1. **Build for the game, ship to Fab.** Almost everything below is something the 1v1 duel or the battle royale needs.
2. **Sell the function layer.** Competing ninja listings describe static meshes. Ours carry sockets, separable parts,
   rigs, LODs, collision and recolour materials; add Niagara and Blueprints where it's cheap.
3. **One coherent line under one publisher name.** Buyers follow a seller who stays in a niche and style.
4. **Avoid leading with feudal-Japan environments.** The demand is highest there, but so is the competition and the cost.
5. **No franchise anything.** Original glyphs and crests only; audit every item before listing (`FAB_ASSET_STUDY.md` 4.3).

---

## Tier 1: package what already exists (fastest path to a first listing)

| # | Product | Contents | Demand | Gap | Fit | Game | Effort | Price (Personal / Pro) |
|---|---|---|---|---|---|---|---|---|
| 1 | **Shinobi Arsenal Vol. 1** | 6 shuriken, plain kunai, smoke bomb, paper bomb (after glyph IP audit), sensu fan (rigged + 3 clips), nunchucks (10-bone rig); add **caltrops** (makibishi, new, easy) | Med | Thin | Strong | Yes | S-M | $19.99 / $39.99 |
| 2 | **Stun Grenade** (standalone) | The flashbang: separable ring, pin and lever with sockets. Modern, so it does not fit the ninja line; seed of a later "tactical" line or a $4.99 single | Med | Crowded | Strong | Maybe | S | $4.99 / $9.99 |
| 3 | **Japanese Armory & Display Kit** | The ArmoryKit: display cases (5 sizes, glass + plinth), racks, banners, ceiling/wall modules, facades, gate, garden set (maples, pines, rocks, stone lantern, tsukubai, raked gravel) | High | Thin (display/museum angle) | Strong | Yes | M | $39.99 / $79.99 |
| 4 | **Recolourable Lacquer, Silk & Steel Materials** | The pack's master materials from `Scripts/unreal/materials/` as a standalone Materials listing | Med | Crowded | Strong | Yes | S | $9.99 / $19.99 |

**Blockers before any Tier 1 listing:** (a) the showcase renders: 0 of 49 current PNGs meet Fab's 1920x1080 / 3 MB rules
(`WorkFiles/showcase/SHOWCASE_PLAN.md`); (b) the IP re-audit of items added after 2026-09-17; (c) seller account setup,
since Trader verification is reported to take 5-9 weeks, so start it now.

## Tier 2: new hard-surface weapon and gear packs (our pipeline's sweet spot)

| # | Product | Contents | Demand | Gap | Fit | Game | Effort | Price |
|---|---|---|---|---|---|---|---|---|
| 5 | **Modular Japanese Blades** | Katana, wakizashi, tanto, ninjato + saya. Fittings (tsuba, habaki, tsuka wrap, kashira) as swappable parts on sockets, so buyers "build" swords. Hamon steel material | Med | Thin (modular is rare) | Strong (keep ornament restrained) | Yes | M | $24.99 / $49.99 |
| 6 | **Polearms & Staffs** | Naginata, yari (2 heads), bo, jo, hanbo, kanabo | Med | Thin | Strong | Yes | M | $19.99 / $39.99 |
| 7 | **Chain & Rope Weapons** | Kusarigama, manriki-gusari, meteor hammer, rope dart. Rigged chains reusing the nunchucks rig approach | Med | **Open** (few rigged chains seen) | Strong | Yes | M | $24.99 / $49.99 |
| 8 | **Hidden & Close-Quarters Weapons** | Sai, tonfa, kama, tessen (iron fan, reuses the fan rig), kakute rings, neko-te, blowgun + darts | Med | Thin | Strong | Yes | M | $19.99 / $39.99 |
| 9 | **Shinobi Traversal Gear** | Kaginawa grappling hook + rope segments, shuko/ashiko climbing claws, rope ladder, bamboo snorkel, mizugumo water shoes. Sockets that plug into existing Fab grapple Blueprints | Med | **Open** (mechanics exist, themed gear doesn't) | Strong | Yes | S-M | $14.99 / $29.99 |
| 10 | **Stealth Consumables** | Poison vials, pill case (inro), metsubushi blinding-powder egg, fire starter, gando lantern, scroll cases, pouches, rope coils | Med | Thin | Strong | Yes | S-M | $14.99 / $29.99 |
| 11 | **Japanese Bows** | Yumi (rigged string), arrows (standard, fire, whistling), yebira quiver. Check Fab's ranged-weapon rules first (firearms need rigs + animations) | Med | Thin | OK | Yes | M | $19.99 / $39.99 |
| 12 | **Masks of the Shinobi** | Cloth ninja masks, menpo, and original oni / kitsune / tengu masks (folklore types, our own designs). Static display + MetaHuman-wearable | Med-High (cosmetics) | Thin | OK | Yes (skins) | M | $19.99 / $39.99 |
| 13 | **Travel Hats** | Sugegasa, jingasa, amigasa, hachimaki; builds on BlackHat | Med | Thin | Strong | Yes | S | $9.99 / $19.99 |
| 14 | **Samurai Armour Display** | Kabuto, menpo, do, sode on an armour stand; static first, wearable later | Med | Crowded-ish | **Weak** (ornate; SnowFlower lesson) | Later | L | $39.99 / $79.99 |

## Tier 3: the function layer (needs the Windows PC and Unreal)

| # | Product | Contents | Demand | Gap | Fit | Game | Effort | Price |
|---|---|---|---|---|---|---|---|---|
| 15 | **Ninja Gadget VFX** (Niagara) | Smoke-bomb burst, flash, paper-tag burn + blast, shuriken trail, substitution "poof", caltrop scatter, ink slash | **High** | **Open** (generic smoke is crowded; ninja-specific isn't seen) | OK (authored in Unreal) | Yes | M | $19.99 / $39.99 |
| 16 | **Throwables Gameplay Kit** (Blueprint) | Throw arc preview, stick-in-surface via the existing tip sockets, retrieve/pickup, bomb fuse timers, hit events. Ships as a "Gameplay Edition" of #1 | **High** | Open | OK | Yes | M | $29.99 / $59.99 (with #1) |
| 17 | **Melee Weapon Attach & Trace Kit** | Hand/back/hip sockets for Manny and MetaHuman, blade trace sockets for hit detection, holster swaps; generated from our `.sockets.json` sidecars | High | Crowded (generic) / Open (themed) | Strong | Yes | S-M | bundle bonus |

## Tier 4: outfits and wearables (MetaHuman; higher risk)

Risks: Chaos Outfit is still Beta in 5.8.3; packaged outfits can lose their materials (`FAB_ASSET_STUDY.md` 4.7); the heels
look failed its blind test. Start small.

| # | Product | Contents | Demand | Gap | Fit | Game | Effort | Price |
|---|---|---|---|---|---|---|---|---|
| 18 | **Japanese Footwear** | Tabi, jika-tabi, waraji, geta, zori, M + F. Proves the garment route on small parts, as the heels did | High (characters) | **Open** (no feudal-Japan MH items surfaced) | OK | Yes | M | $19.99 / $39.99 |
| 19 | **Shinobi Outfit** (MetaHuman) | Shozoku jacket, hakama/trousers, hood, mask, gloves, belt, M + F | High | **Open** | Weak-OK | Yes (hero) | L | $39.99 / $79.99 |
| 20 | **Dojo Gi & Hakama** | Training gi, obi (belt colours), hakama | High | Open | OK | Yes | L | $34.99 / $69.99 |
| 21 | **Kimono & Yukata** | Formal kimono, yukata, haori, M + F | High | Open | Weak (long drape) | Later | L | $39.99 / $79.99 |
| 22 | **Cloaks & Capes** | BlackCloak variants: hooded, travel, tattered; recolourable | Med | Thin | OK | Yes | M | $24.99 / $49.99 |

## Tier 5: environments, props and diversification (after the line is established)

| # | Product | Contents | Demand | Gap | Fit | Game | Effort | Price |
|---|---|---|---|---|---|---|---|---|
| 23 | **Dojo Duel Arena** | The MVP courtyard as a playable level kit: full collision, climbable roofs and walls, spawn points, demo map. Pitched as a multiplayer arena, not a set | High | Crowded (sets) / Open (arenas) | OK | **Yes (MVP)** | L | $49.99 / $99.99 |
| 24 | **Training Yard Props** | Makiwara, wooden dummy, target boards, weapon racks, bokken, balance posts, sandbags | Med | Thin | Strong | Yes | S-M | $14.99 / $29.99 |
| 25 | **Shinobi Hideout Dressing** | Scrolls, ink-stone sets, low tables, candles, chests, rice sacks, barrels, straw mats, maps | Med | Crowded | Strong | Yes | M | $19.99 / $39.99 |
| 26 | **Bamboo Forest Kit + PCG scatter** | Scripted bamboo (stalks, clumps, fallen canes, shoots) with a PCG graph | **High** (procedural) | Thin | **Strong** (bamboo is algorithmic geometry) | Yes (BR map) | M | $29.99 / $59.99 |
| 27 | **Zen Garden Tool** | Raked-gravel generator (from the armory's RakeRing), stepping stones, moss, rocks | High (procedural) | Open | Strong | Yes | M | $19.99 / $39.99 |
| 28 | **Battle Royale Loot Kit** | Lootable chests and crates (lids on sockets), supply drops, zone markers, respawn shrines | Med | Crowded (generic) / Thin (themed) | Strong | **Yes (BR)** | M | $19.99 / $39.99 |
| 29 | **Yokai Shrine (Japanese horror)** | Original ofuda talismans, torii, jizo statues, cursed dolls, broken lanterns, shrine gates | High (horror is a top theme) | Thin | OK | Maybe | M | $24.99 / $49.99 |
| 30 | **Original Clan Crests & Sigils** (decals) | 10+ original mon and seal decals + reveal master material (the study's product 3) | Med | Thin | Strong | Yes | S | $9.99 / $14.99 |
| 31 | **Japanese Food & Tea** (realistic) | Tea set, rice bowls, onigiri, dango, sake set | Low-Med | Crowded (stylized) | OK | Maybe | S-M | $9.99 / $19.99 |
| 32 | **Medieval European Melee Pack** | Longsword, arming sword, mace, axe, spear, shields: same pipeline, bigger market (medieval is a top theme) | Med-High | Crowded | Strong | No | M | $19.99 / $39.99 |

---

## Recommended order

1. **Now (cloud + PC, in parallel):** start seller setup (Trader verification is slow); run the IP re-audit; fix the
   showcase renders.
2. **First listing: #1 Shinobi Arsenal Vol. 1.** Everything is built except caltrops. It exercises the listing, review
   and showcase path end to end on something cheap, and teaches us the real review time.
3. **Second: #5 Modular Japanese Blades.** The duel needs swords, the modular angle is rare, and the study already chose a
   melee pack as product 1.
4. **Third: #15 + #16 VFX and Throwables kit**, released as a "Gameplay Edition" upgrade of #1. This is where the 2026
   demand points (Blueprints, VFX).
5. **Then:** #9 Traversal, #7 Chain Weapons, #3 Armory Kit, #18 Footwear (the first MetaHuman product), #26 Bamboo PCG.
6. **Hold:** #14 Armour and #21 Kimono (ornate or long drape; our worst fit) until the method is proven on simpler
   pieces.

## Before building any item

- Verify its gap on fab.com from the PC (the cloud session cannot reach it): search 3-5 terms, note the top 5 competitors'
  price, reviews and whether they ship sockets, rigs or Blueprints. Write it in this folder as `<item>_COMPETITION.md`.
- Check the Fab minimum count for its category (`FAB_ASSET_STUDY.md` 4.4): realistic packs 1 (5 recommended), stylized
  about 25, animations 10+.
