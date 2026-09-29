# Any-genre Fab product list: competitor scan (2026-09-28)

**Role:** research only. Nothing was built. This list is **not tied to the ninja line** (that list is `PRODUCT_LIST.md`).
It covers medieval/Viking, cyberpunk/sci-fi, modern military/post-apocalyptic, horror, historical, cozy/simulator and
genre-agnostic products.

**How it was made:** a multi-agent workflow. Seven genre scouts each ran 25-50 web searches, proposed 6-8 products and
listed real competing Fab listings. The 16 best-rated non-crowded ideas then went to two skeptics, whose only job was to
find competitors the scouts missed and to refute the demand claims. Full per-idea detail and every competitor link are
in `GENRE_SCAN_ALL_CANDIDATES.md`; the raw data is in `genre_scan_results.json`.

**Limits (read before trusting a number):**

- fab.com cannot be opened from the cloud session. All Fab evidence comes from search-result titles and snippets.
  **No Fab prices, review counts or sales were seen.** The prices below are the scouts' estimates from the study's bands.
- The first run used up the session's search budget, so 3 genre groups and both skeptics came back with no evidence. Those
  groups and the skeptic pass were re-run with a search cap; every result below has real searches behind it.
- "Holds" means the skeptic's own 3-5 searches found no close competitor. It does not mean none exists. Check each pick
  on fab.com from the PC before building (see the end of this file).

---

## 1. What the scan says about the market

1. **Environments are saturated in every genre.** Castles (945-mesh kits), Viking villages (7+ megapacks), cyberpunk
   cities (1,003-asset kits), asylums, backrooms (7+), Wild West towns, Egyptian and Mesoamerican temples, supermarkets
   and cozy rooms all have many large kits. Epic also gives large historical kits away free (200+ Chinese pieces Aug
   2025, 80 temple pieces Jan 2026). **A solo seller should not build another environment megapack.**
2. **The openings are "function layers" and "part-heavy kits"**:
   - *function layers*: working mechanisms, interactables and systems that plug into the environment kits buyers
     already own (gates that open, boards that break, containers with loot sockets);
   - *part-heavy kits*: many small interchangeable hard-surface parts with sockets (engine parts, PC parts, retail SKUs,
     card-shop stock).
   Both are exactly what our pipeline makes well: rigid-part rigs, sockets plus the `.sockets.json` sidecar, UCX,
   LODs and recolourable master materials.
3. **Three demand waves stood out on Steam in 2025-2026:**
   - **simulator games** (card shop, mechanic, supermarket, PC builder). *TCG Card Shop Simulator* shows 96% of 33,885
     Steam reviews in a snippet, and a wave of card-shop clones followed. *Car Mechanic Simulator 2026* and several
     co-op mechanic sims are live;
   - **co-op extraction horror** (R.E.P.O., Lethal Company; "friendslop" is now a named genre with its own Fab templates);
   - **extraction shooters and survival crafting** (ARC Raiders, Marathon; survival craft was 2025's "easiest hit genre"
     per howtomarketagame, via the scout).
4. **Templates create content demand.** Fab now sells store-sim, TCG-shop, co-op-horror and extraction templates. Their
   buyers need content that plugs into them, and that content is what we'd sell.
5. **Niche themes are niche.** Dieselpunk, atompunk, solarpunk, Roman-accurate siege and feudal-Japan mechanisms have
   gaps, but the skeptics found little buyer demand. Cheap and fast ones are fine as side products; don't lead with them.

## 2. The list

Scores: **Demand** and **Gap** after the skeptic pass where one ran (1-5, 5 = strong demand / wide-open gap). **Fit** =
fit to our pipeline. **Effort**: S = days, M = 1-3 weeks, L = month+ (estimate). Verdict: HOLDS / WEAKENED / REFUTED /
*not verified*.

### Tier A: build first (survived the skeptics)

| # | Product | Genre | What ships | Demand | Gap | Fit | Effort | Price est. | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Collectibles & Card Shop Kit** | Simulator | Display counters and wall cases with slot sockets; booster packs, boxes and cartons in parametric sizes on a label atlas of original fictional brands; sleeves, top-loaders, graded slabs, binders, deck boxes, playmats, play tables, register, figure boxes | 4 | Open | Strong | M | $24.99-$34.99 | **HOLDS** |
| 2 | **Engine & Machinery Teardown Kit** | Simulator / any | 3 original engines (inline-4, V-type, small single-cylinder), each 30-60 removable parts, a socket on every attach point, UCX per part, dependency order and condition data for a mechanic-sim teardown loop | 4 | Thin | Strong | L | $49.99-$69.99 | **HOLDS** |

Why these two: both sit on a live Steam simulator wave, both are pure hard-surface plus sockets, and neither skeptic found
a Fab kit that does the same. Risks: card-shop buyers are price-sensitive and many use Unity, so ship FBX as well as UE
and keep it mid-priced; engine buyers judge mechanical accuracy harshly, so keep the engines original but believable.

### Tier B: strong demand, needs a sharp angle (weakened, but demand 4)

| # | Product | Genre | What ships / the angle that still wins | Demand | Gap | Fit | Effort | Price est. | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 3 | **Physics Valuables Kit** (co-op extraction horror) | Horror | 40-60 clean hard-surface valuables (clocks, gramophone, typewriter, globe, trophies, radios, porcelain) with mass, grab sockets, pre-fractured variants and a value/fragility DataTable. **Sell as content for the existing co-op horror templates**, priced as a prop pack. Merge the "Scrap Haul" idea in as a sci-fi theme expansion | 4 | Thin | Strong | M | $29.99-$39.99 | WEAKENED |
| 4 | **Extraction Raid Interactables** | Military / shooter | Lead with what nobody sells: an **exfil set** (flare, radio beacon, antenna mast with countdown, conditional exfils) plus keycard doors and civilian/industrial searchable containers behind one loot interface. Skip ammo crates; they are crowded | 4 | Thin | Strong | M | $39.99-$59.99 | WEAKENED |
| 5 | **Procedural Retail Packaging System** | Simulator | Box, can, bottle, jar, carton families in 3-5 sizes on one master material with a 64+ original-brand label atlas: 500+ SKUs from ~40 meshes, plus a SKU DataTable for the store-sim templates. Hidden cost: designing 64 original fake brands (no AI imitations of real ones) | 4 | Thin | Strong | M | $29.99-$49.99 | WEAKENED |

### Tier C: good fit, moderate demand (weakened, demand 3)

| # | Product | Genre | The angle that still wins | Demand | Gap | Fit | Effort | Price est. | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 6 | **Board-Up: Barricade System** | Horror / zombie / post-apoc | Boards auto-fit any opening, break in stages, rebuild; **a PCG pass boards up a whole building**. No dedicated Fab product found (itch/Unity equivalents exist) | 3 | Thin | Strong | M | $19.99-$34.99 | WEAKENED |
| 7 | **CQB Breach Door Library** | Tactical shooter | Door logic exists inside templates; the gap is the **art**: 8 door types x intact/kicked/hinge-shot/ram/explosive pre-cut states. Start with 3 types to test | 3 | Thin | Strong | M | $29.99-$44.99 | WEAKENED |
| 8 | **Castle Gatehouse Controller** | Medieval | Two animated gate listings exist; sell the **replicated siege controller** (winch-linked portcullis, drawbridge, destroyed state, nav update) with adapter frames for the top castle kits | 3 | Thin | Strong | M | $24.99-$29.99 | WEAKENED |
| 9 | **Wasteland Vehicle Upfit Kit** | Post-apoc | 100+ bolt-on armour/cage/rack parts; must ship pre-fitted to 3 sample car shells plus width-adjustable versions, or "fits any vehicle" fails | 3 | Thin | Strong | M | $34.99-$49.99 | WEAKENED |
| 10 | **Modern Frontline Kit** | Modern military | Trenches are well supplied (incl. a free Megascans sample); lead with **anti-drone netting and FPV-era dressing**, which nobody sells. Keep it generic, since it depicts a real ongoing war | 3 | Thin | Strong | M | $39.99-$59.99 | WEAKENED |
| 11 | **Retro Raygun Arsenal** | Retro sci-fi | 10 original 1950s-style ray guns with sockets, a chrome/enamel/bakelite recolour material and optional beam VFX. Small and fast; avoid famous franchise silhouettes | 3 | Thin | Strong | S | $24.99-$29.99 | WEAKENED |

### Tier D: deprioritise

| Product | Why |
|---|---|
| PCG Industrial Racking & Stock-Fill | **REFUTED**: auto-fill rack blueprints and PCG shelf fillers already exist; meshes are crowded |
| Dieselpunk Industrial Kit | A game-ready dieselpunk kit already exists (Floor 5), KitBash3D gave one away free, and demand is niche (demand 2) |
| Roman Torsion Siege Engines | 5+ siege packs exist; Roman-exact accuracy is a small niche (demand 2). Maybe later as part of a wider Roman camp set |
| Shinobi Castle Mechanisms (karakuri) | Gap is wide open, but demand is 2. Worth building **for our own ninja game** and listing cheaply, not as a lead product |
| Any environment megapack, generic loot crates, spline fence/pipe tools, fast-food kitchens, cozy interiors | Crowded, and free alternatives exist |

### Tier E: promising but not verified (scouts' ratings only; verify before building)

| Product | Genre | Pitch | Scout gap | Effort | Price est. |
|---|---|---|---|---|---|
| **Modular PC Hardware Kit** | Simulator | 60-80 parts on one socket standard (any GPU fits any board) for PC-builder, repair-shop and internet-cafe sims | Thin | M | $29.99-$39.99 |
| **Safe & Vault Cracking Kit** | Any (heist, horror, RPG) | 8 safes and vaults incl. a walk-in vault door and deposit-box wall, real boltwork rigs, 3 lock BPs (dial, keypad, key) | Thin | M | $29.99-$39.99 |
| **Frontier Wagons & Stagecoach Family** | Wild West | Buckboard, farm wagon, chuckwagon, schooner, stagecoach, ore cart, handcar: steering/wheel/door rigs, hitch and seat sockets | Thin | M | $29.99-$39.99 |
| **Forged: Medieval Iron Hardware Kitbash** | Medieval / fantasy | ~150 hinges, studs, locks, pulls, brackets, chains as meshes, mesh decals and a trim sheet. Cheap, fast, and speeds up our other medieval work | Open | S | $14.99-$19.99 |
| **Trap & Puzzle Mechanisms (ancient stone)** | Egypt / Mesoamerica / classical | Pressure plates, sliding doors, statue-alignment puzzles, dart walls, rolling boulder, swappable style trims | Thin | M | $29.99-$44.99 |
| **Mechanical Puzzle Mechanisms** | Any | Ring locks, gear-train, mirror-beam relay, balance scales, lever panels in fantasy/horror/sci-fi trims | Thin | M | $34.99-$49.99 |
| **Gothic Level-Mechanics Kit** | Soulslike | One-way shortcut doors, counterweight lifts, lever gates, kick-down ladders, mist-gate VFX for existing soulslike frameworks | Thin | M | $29.99-$49.99 |
| **Searchable Storage Kit** | Horror / survival | ~20 lockers, filing cabinets, desks with real drawers, loot sockets inside and a search component | Thin | M | $24.99-$34.99 |
| **Animated Industrial Machinery** | Industrial / any | 15-20 machines with on/off/fault states and a spline conveyor that moves items; rust switch for abandoned sets | Thin | M | $29.99-$49.99 |
| **Crew-Served Weapon Emplacements** | Military | Original-design mountable HMG, mortar, recoilless rifle, AA mount with yaw/pitch rigs and a mount BP | Thin | M | $29.99-$49.99 |
| **Cassette-Futurism Consoles** | Retro sci-fi | ~40 modular 70s/80s consoles, CRT shader, switches as separate parts with interact BPs | Thin | M | $29.99-$44.99 |
| **Norse Longship Kit** | Viking | Procedural clinker hulls in 3 sizes, row/sail BP, crew seat sockets, buoyancy | Thin | L | $39.99 |

## 3. Recommended order

1. **Card Shop Kit (#1).** The best evidence of any idea, medium effort, and built entirely from our strengths.
2. **Retail Packaging System (#5)** next, sharing the label-atlas material with #1. Together they make a "sim store
   content" line that can be bundled.
3. **Physics Valuables Kit (#3)** for the co-op horror wave; it is prop work plus a small DataTable.
4. **Engine Teardown Kit (#2).** Strong, but L effort; start it once the socket/sidecar workflow is routine on #1.
5. **Forged Iron Hardware (Tier E)** as a quick side product between big ones, if its gap checks out.
6. Then pick from Tier C by what the first sales show (horror/zombie → Board-Up; shooter → Extraction Raid / Breach Doors).

This line sits well beside the ninja pack: the same scripts, materials, socket sidecars and showcase rig serve both.
Buyers follow a seller's niche, so consider a second publisher brand name for the sim/horror content (the Fab study's
advice on niche consistency, `MARKET_FINDINGS.md` section 1).

## 4. Before building any of these

On the PC (fab.com is reachable there), for the chosen product:

- Search fab.com with 5+ phrasings; note the top 5 competitors' **price, rating, review count** and whether they ship
  sockets, rigs, Blueprints or VFX. Save as `<product>_COMPETITION.md` in this folder.
- Check the Unity Asset Store for the same idea (sim buyers often use Unity; FBX/GLB ships to them too).
- Confirm every brand, label, logo and silhouette is original (Fab bars trademarked content; `FAB_ASSET_STUDY.md` 4.3).
- Check the Fab minimum count for its category (`FAB_ASSET_STUDY.md` 4.4).
