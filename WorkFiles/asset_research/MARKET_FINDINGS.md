# Fab market findings (2026-09-28)

**Role:** research notes only. Nothing was built, and no file outside `WorkFiles/asset_research/` was changed.
**Method:** web search from a cloud session. `fab.com` and `unrealengine.com` are blocked by this environment's network
policy, so listing pages could not be opened. Everything about individual listings comes from search-result snippets:
prices, ratings and review counts are **not measured**. It builds on `FAB_ASSET_STUDY.md` section 6 (2026-09-17), which
remains the source for fees, price rungs, minimum counts and listing rules.

**Flags:** **SOURCED** = stated by a source below. **SNIPPET** = seen only in a search snippet. **INFERENCE** = our
reading, not a source's claim.

## 1. What the market rewards

| Finding | Flag | Source |
|---|---|---|
| Fab's first full year (2025): library tripled to 420,000+ live listings; publishers doubled to 20,000+; creators earned $24M+ | SOURCED | [1] |
| Top categories 2025: environments, characters, engine tools, procedural systems, gameplay features | SOURCED | [1] |
| Top themes 2025: realistic, fantasy, stylized, medieval, horror | SOURCED | [1] |
| Strong demand for realistic styles, ready-to-use RPG frameworks, Blueprint-driven products and dynamic VFX | SOURCED | [1][2] |
| 2026 outlook: high-quality environments, game-mechanics tools/plugins, procedural game systems | SOURCED | [2] |
| Event sales (Fab Friday, Spring, Summer) brought up to 50% of a month's revenue; flash sales about 25% | SOURCED | [1][2] |
| Buyers expect a seller to stay in one niche/style ("if you specialize in low poly stylized... buyers expect similar content") | SOURCED | [2] |
| Limited-Time Free runs in two-week rotations; used as a reach/revenue lever | SOURCED | [3] |
| New sellers: 60-day hold on the first three months of revenue; payouts on the 15th | SNIPPET | [4] |

**INFERENCE:** with 420k listings, a plain static-mesh pack is a commodity. The products that stand out carry
*function* (Blueprints, VFX, sockets, rigs, recolour materials) or *coverage* (a coherent kit that builds a whole scene).
Our pipeline already produces the function layer (socket sidecars, rigged fan/nunchucks, separable flashbang parts,
recolourable master materials), which most competing ninja listings do not advertise.

## 2. Competition in our niche (feudal Japan / ninja)

| Area | What already exists on Fab (snippets) | Read |
|---|---|---|
| Feudal Japan environments | Feudal Japan Megapack, Feudal Japanese Village (409 meshes), Feudal Japanese Castle, Warroom, Synty POLYGON Samurai [5] | **Crowded** at the top end. Do not lead with a generic village. |
| Japanese interiors / dojo | Japanese Dojo and Rooms (62 assets, 6 BPs), Japanese Room Props, MJH Modular Town House, Modular Japanese Architecture [6] | **Crowded.** Our dojo only sells if it is a *gameplay arena* (duel layout, climbable roofs, collision), not another set. |
| Chinese / wuxia environments | Silent City, Ancient Chinese City (with PCG), Chinese Alley, Asian Temple; a free 200+ piece Chinese park pack in 2025 [7] | **Crowded**, and a free pack undercuts it. |
| Ninja weapons | Real Ninja Weapons (katana, tanto, kunai, shuriken, sai, grappling hook), Katana Ninja, Ninja Weapons Throwing Stars and Kunai, HB Ninja [8] | **Present but thin**: descriptions are static meshes + PBR. No snippet mentions sockets, separable parts, recolour, rigs or gameplay BPs. **Our opening.** |
| Grappling hook systems | At least 8 Blueprint grapple systems (physics, multiplayer, FP/TP) [9] | Mechanics covered; a *themed kaginawa mesh + rope* that plugs into them is not. |
| Smoke / stylized VFX | Many generic smoke packs; anime slash/projectile packs (Vefects, 67 effects + 6 BPs) [10][11] | Generic VFX is covered. **Ninja-specific** gadget VFX (smoke-bomb burst, substitution, ink/paper-tag burn) is not seen. |
| MetaHuman clothing | Workwear, dresswear, medical, cyber, fitness, western, medieval; $39.99-$49.99 [12] | **No feudal-Japanese MetaHuman outfit surfaced in search.** Possible gap; verify on Fab from the PC. |
| Japanese food props | Low Poly Japanese Food (70+), Japanese Food Pack01 (70+), Ramen Restaurant [13] | Covered in stylized; small realistic gap only. |

## 3. What this means for us (INFERENCE)

1. **Lead with what our pipeline does that others don't:** gameplay-ready ninja items (sockets, separable parts,
   rigs, recolour materials, LODs, collision) sold as a coherent line under one publisher name.
2. **Every item should serve the game first.** The 1v1 dojo duel and later the battle royale need weapons, throwables,
   outfits and an arena anyway; building to Fab standard costs little extra and each sale subsidises the game.
3. **Avoid leading with environments** in feudal Japan: highest demand, but the most crowded and the most expensive to
   make well. Sell the dojo arena only as a *playable* level kit, later.
4. **Add a function layer per pack** (Blueprint or Niagara) where possible: that is what the 2025/2026 demand data
   points to. It needs the Windows PC (Unreal), so plan it as the second step of each pack.
5. **Price for events:** list at a price that still pays at 50% off, since event sales are half of revenue.
6. **Diversify later along the same pipeline:** medieval and horror are top themes; a medieval melee pack or a
   Japanese-horror (yokai shrine) prop pack reuses the same scripts.

## 4. Open questions to check on the PC (fab.com is reachable there)

- Real prices, ratings and review counts of the 4 ninja-weapon listings in [8].
- Whether any feudal-Japanese MetaHuman outfit exists (search "kimono MetaHuman", "samurai MetaHuman", "ninja
  MetaHuman").
- Whether a ninja-gadget VFX pack exists (search "ninja VFX", "shinobi Niagara").
- The IP audit of the post-2026-09-17 items (`FAB_ASSET_STUDY.md` section 2 lists them as not re-audited), especially
  the paper bomb's glyphs and SnowFlower's unattributed reference.

## 5. Sources

1. Epic, "Take a look back at Fab's first full year": https://www.unrealengine.com/news/fab-2025-year-in-review (SNIPPET: page blocked here; quoted via search)
2. Search summary of [1] and StraySpark, "Fab Marketplace: A 12-Month Retrospective from a Seller": https://www.strayspark.studio/blog/fab-marketplace-12-month-retrospective-seller-2026 (page blocked here)
3. Fab forum, "New Limited-Time Free Content Program on Fab!": https://forums.unrealengine.com/t/new-limited-time-free-content-program-on-fab/2092736
4. StraySpark retrospective (above), search snippet only
5. https://www.fab.com/listings/80c4ae6f-b612-4d5b-86b4-d8fec433d469 (Feudal Japan Megapack); https://www.fab.com/listings/64e34d42-ef01-4a3c-a20c-4892cf3fafd1 (Village); https://www.fab.com/listings/041f2237-8123-4643-8c02-c5a6f3159da7 (Castle); https://syntystore.com/products/polygon-samurai-pack
6. https://www.fab.com/listings/07b9dedf-c42d-4d1b-ae8c-a6756bcd1643 (Japanese Dojo and Rooms); https://www.fab.com/listings/5d7f0073-f857-44cc-aa5a-a6476ffe7245 (Japanese Room Props); https://www.fab.com/listings/ce2f58c7-2d54-4756-8cea-3597b1c8329c
7. https://www.fab.com/listings/cf760130-1048-4208-9f8d-cdb91e19726f (Ancient Chinese City); https://www.fab.com/listings/9a2857f1-b346-4e23-a51a-178e7163e085 (Chinese Alley); https://www.cgchannel.com/2025/08/get-200-modular-assets-for-creating-traditional-chinese-buildings-in-ue5/
8. https://www.fab.com/listings/e3e84b9b-100e-4812-a156-da0665501a22 (Real Ninja Weapons); https://www.fab.com/listings/b0345480-84b4-4a78-a803-0fe68d84bf60 (Katana Ninja); https://www.fab.com/listings/5be3af07-b2b8-4b0d-a3b8-b2f8fe434cfa (Throwing Stars and Kunai); https://www.fab.com/listings/2f73bf33-9f77-4067-aec0-cb2a14355ba5 (HB Ninja)
9. https://www.fab.com/listings/b761ed67-a470-4f41-b9b3-c312b92f56b0; https://www.fab.com/listings/d50097ec-9c33-44f1-bce6-6ac039ae6d7f; https://www.fab.com/listings/12ae72f7-d885-4227-b1ad-45d26d3e4202
10. https://www.fab.com/listings/67168714-1a42-4a5d-bbf4-51fbabb92d38; https://www.fab.com/listings/2d354f78-a836-4c27-82df-be7c9184883c
11. https://www.fab.com/listings/a4660915-e001-4b6b-b3ca-cec7c66740ce (Stylized VFX); https://vefects.com/product/anime-stylized-vfx-unreal-engine-asset-pack/
12. https://www.fab.com/listings/709a5877-3cfe-4af8-819f-94983d26c53d; https://www.fab.com/listings/2f376410-f954-4e48-bcd3-d0fe8290e8ee; https://www.fab.com/listings/1d2573a8-ea2b-41b1-8908-95b98a4526da
13. https://unrealengine.com/marketplace/en-US/product/food-pack-low-poly-japanese-food; https://www.fab.com/listings/9b8170a6-c79b-4c98-a382-37e872dbd973; https://www.fab.com/listings/4c5b5ba7-e702-48a2-a5e4-975cd6728ace
