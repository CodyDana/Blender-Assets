# Collectibles & Card Shop Kit: product and build spec

**Date:** 2026-09-28 (revision 2: the buyer and pipeline-IP reviews are applied; see the Review log at the end).
**Status:** PLAN ONLY, nothing built. Nothing is locked or exported. Building starts only after the user answers section 2 (gate G0).
**Role:** the spec for GENRE_SCAN item #1. It is a 3D asset pack for Fab (UE 5.8 project + FBX + GLB), made for developers
of card-shop simulator games (TCG Card Shop Simulator, Sports Card Shop Simulator, Card Shop Simulator Multiplayer and
their clones). Those game titles appear only in this internal file, never in the listing (6.2).
**Scope:** dressing and interactable props: shop fixtures, collector hardware, sealed product, retail accessories and an
art system of original fictional brands. It is **not** game logic, and it contains **no real cards, brands or grader labels**.
**The user's question, "Slabs and empty cases?":** yes, both are the core, but they are not enough alone.
- Slabs, top-loaders and magnetic holders ship as **empty shells**. The card is a separate mesh that snaps in through a
  `Card` socket. Each also ships as a fully opaque `_Filled` dressing variant with the card already inside (cheap in bulk).
- Every display case, shelf and table ships **empty**, with a level origin socket plus a slot grid in data, so the buyer's
  game (or the Fab TCG template) fills it at runtime.
- The card art is **original**: a card-face atlas of fictional sets, plus a plain-texture path and a tool so buyers can
  drop in their own card images (4.1).
- The rest of what every card-shop game uses is also in v1: packs, boxes, retail accessories, shelves, card tables, a
  register, play tables, and the stocking loop's cartons and hand truck (section 3).

**Sources read:**
- Research relayed to this writer on 2026-09-28: *dimensions*, *gameneeds*, *market-ip* and *pipeline*. Two reviews relayed
  the same day: *buyer* and *pipeline-ip*. All of their web numbers come from search snippets; **no source page was opened
  in full**, because WebFetch was blocked on every site.
- Repo: `CLAUDE.md`, `ASSET_GUIDELINES.md` (§3 lines 44-62: ORM.R is baked AO, 2048 for props, padding), `WorkFiles/asset_research/GENRE_SCAN.md` (item #1),
  `FAB_ASSET_STUDY.md` (line 17; line 191 packaging self-tests; line 308 sample content; line 327 minimum counts [unverified];
  lines 335 and 341 media; line 345 rejections; line 448 price bands; line 467 thumbnail), `WorkFiles/world/DOJO_ARENA_SPEC.md` (header format),
  `WorkFiles/armory/ITEM_INVENTORY.md` (the pack LOD rule, lines 53-55) and `Scripts/props/props_lib/spec.py`
  (`PACK_LOD_SCREEN_SIZES`, `PROP_TRIANGLE_BUDGET`, `deny_hits` line 386).
- Checked for this revision: `Scripts/pipeline/export_fbx.py` (`RESERVED_OVERRIDES` line 84, `write_socket_sidecar` line
  280, the unknown-override `ValueError` line 395), `Scripts/pipeline/qa_check.py` (UV0 tile range and overlap checks, `--texel`
  is whole-mesh, `DENY_WORDS = ("ea",)` line 69), `Scripts/unreal/materials/run_build.sh` (line 17: the project is hard-wired)
  and `np_spec.py` (lines 27-31: `NP_SPEC_PATH`, `NP_ROOT`).
- The source keys `[D..]`, `[G..]`, `[M..]`, `[T..]`, `[U..]` and `[R]` are listed in section 11.

**Status labels.**

| Flag | Meaning |
|---|---|
| **M** = MEASURED | The number appears in the cited source. For web sources that means a search snippet, not a checked full page. |
| **D** = DERIVED | Computed from M numbers, or from M and E numbers. The inputs are named. |
| **E** = ESTIMATE | A design choice or a judgement, with no source. |
| **E\*** | The research relayed the value as measured but recorded no source key. It is treated as E until it is re-sourced. |
| **HOUSE** | A rule the repo states (cited). |

**Units and frame.** All sizes are in **mm** unless marked. Blender: metres, Z up, scale 1.0 (HOUSE, `ASSET_GUIDELINES.md` §1).
Unreal mapping: (x*100, -y*100, z*100) cm, the same as the dojo and armory specs. Kit poses and pivots (E):

| Kind | Modelled pose | Pivot | Size column order |
|---|---|---|---|
| **Flat items** (card, sleeves, holders, slab, pack, playmat, mailer, tag) | Lying face-up. The printed face is +Z and the top edge points +Y. | = `Seat`: centre of the back face | W × H × T |
| **Volumetric items and stand-alone fixtures** | Upright. The customer / front side is **−Y**, so it becomes +Y in Unreal. | = `Seat`: bottom centre at floor contact | W × D × H |
| **Modular run pieces** (slatwall, gondola, shell walls, floor, ceiling) | Upright, as above | **End corner**: the −X end, back-bottom, on the wall plane or back face, where the next piece meets (HOUSE wall rule, `ASSET_GUIDELINES.md` §1). `Snap_L` sits on the pivot and `Snap_R` at +W | W × D × H |
| **Moving parts** (every `_Lid`, `_Door`, `_Cover`, `_Plate`, `_Tray`, `_Front`/`_Back` half, laptop lid, track head) | In the closed pose | **On the hinge axis** (rotating parts), or at the closed position (sliding and lift-off parts). The parent's `Lid`/`Door_*`/`Tray` socket sits on the same axis, so a plain Timeline → `SetRelativeRotation` works without any kit Blueprint. The README says this | as the parent |

Run fixtures that are not modular (showcases, box tier, wire rack, counter, warehouse rack) keep the bottom-centre pivot and
also get `Snap_L`/`Snap_R` sockets at their end faces.

---

## 1. Summary

| Item | Value |
|---|---|
| Product | **Collectibles & Card Shop Kit**: a furnished card shop's fixtures, collector hardware, sealed product and retail accessories, with every piece socketed for gameplay |
| Buyer | Small teams making card-shop sims in UE 5.8 (FBX/GLB for other engines); buyers of the Fab "Shop Simulator – TCG Card Store Template", which ships only 10 demo cards and no art kit [G5] |
| Gap | No dedicated card-shop 3D kit was found on Fab, Unity, CGTrader, Sketchfab or itch.io across 19 queries [M10]. The nearest single item is one CGTrader empty slab [M9] |
| Style (recommended) | **Clean realistic PBR** (real proportions, crisp bevels, low texture noise, one recolourable master per surface family). Tagged Realistic + PBR. A stylized skin is a **separate later listing** (D1) |
| Asset count v1 | **69 items / 171 static meshes** (D): 118 stand-alone pieces + 53 moving parts, fixed-glass panes and state variants, in 10 groups (table 3.0). About 40 more are planned for v1.1 or later (3.11) |
| Textures | 7 shared print atlases (about 85 MiB, D, 4.1) + per-mesh ORM on UV1 + about 15 tileable surface sets |
| Formats | UE 5.8 project (`/Game/CardShopKit/`), FBX + `.sockets.json` + `.csk.json` per mesh, GLB (Fab auto-conversion: D6), `.blend` sources, buyer tools (`csk_pack_cards.py`, `csk_import_sockets.py`) |
| Unreal extras | 5 master materials + MIs, a furnished demo shop map, an overview map, 6 light Blueprints, a slot function library, 2 DataTables. **No game logic** (section 5) |
| Price | **$29.99 Personal / $59.99 Professional** (E). It sits **between** the M bands: $9.99-$19.99 for stylized prop packs and $49.99-$129.99 for modular kits; Professional at 1-3.3× Personal [M1] |
| Effort | **M-L: about 36 Claude sessions plus about 6 PC days** for bakes, Unreal checks and media (E, 7.1). After gate G1, families can be built in parallel by a workflow inside one VM or on the PC (7.1) |
| Fab minimum | Realistic packs need 1 asset (5 recommended); stylized packs need about 25 [M3, unverified in the study]. 171 clears both |

---

## 2. Decisions the user must make (gate G0)

| # | Decision | Options | Recommendation (why) |
|---|---|---|---|
| D1 | **Style** | a) clean realistic PBR · b) stylized · c) both in one listing | **a now, b as a second listing later.** The genre leader reads as "simple, Sims-like" clean realism, and players complain about blur, noise and cheap-looking worlds, not about realism [G6][G7]. Hard-surface realism is our strength and can be checked by measurement. Fab advice is to tag one rendering style per product [M1], so a "Stylized Skin" listing later is mostly new MIs and textures on the same meshes. The masters get a `Use Flat Colour` switch now so the skin is cheap later (E) |
| D2 | **v1 scope** | a) full v1, 171 meshes · b) lean v1, about 115 (3.11) | **a.** Extra lengths and variants are parameters of the same builders, so they cost QA time, not modelling. The real risk is gate G1, not the count: if the card/slab/showcase spike fails, stop before any fan-out |
| D3 | **Brand names** (all fictional) | Claude proposes a shortlist and the user picks; or the user names them | **Claude proposes 3 names per slot, the user picks, and the user screens each pick in USPTO search (a manual step; Claude prepares the query list) and logs the date before any art.** Slots: 3 card lines (2 fantasy TCG + **1 sports-style line with a fictional sport, in v1**, no leagues or teams), 2 graders, 1 accessory brand, 1 distributor (carton labels), 1 demo shop name = **8 names** |
| D4 | **Card art method** | a) script-made original art (emblems, patterns, landscapes, renders of the user's own 3D props) · b) AI-generated images · c) commission | **a.** It is original, reproducible from `Scripts/`, and avoids the mandatory CreatedWithAI tag (FAB_ASSET_STUDY line 314). Buyers bring their own card art anyway through the plain-texture path and `csk_pack_cards.py` (4.1) |
| D5 | **Material home** | a) kit masters built by the existing materials builder in the kit's own project · b) a new separate builder | **a, with three small changes (all under `np_lock`):** add an `NP_PROJECT` env override to `run_build.sh` (line 17 is hard-wired to ShurikenValidation); give the kit its own spec file through `NP_SPEC_PATH`; set `NP_ROOT=/Game/CardShopKit`. `MF_*` functions the kit needs (the `MF_LetteringBand` technique) are **copied** under the CSK root, never referenced from `/Game/NinjaPack/` (precedent `ARMORY_PLAN.md` §7.5) |
| D6 | **GLB** | a) rely on Fab auto-converting FBX · b) write a GLB exporter in `Scripts/pipeline/` with self-tests | **a for v1.** Fab auto-converts FBX listings to GLB/glTF/USDZ (`FAB_ASSET_STUDY.md` line 327). A real exporter is v1.1 if buyers of other engines ask |
| D7 | **Exchange texture names** | `T_CSK_*_BC/_ORM/_N` (house) vs Fab's lowercase `modelname_suffix` | **House names in the UE project. In the FBX zip, per-mesh maps are renamed `modelname_suffix`; the shared atlases go in `Textures/Shared/` under a `csk_atlas_` prefix with a README table**, because a shared atlas cannot follow per-model auto-mapping. Test on one upload draft |
| D8 | **Validation project** | a new `CardShopKit.uproject` (UE 5.8, Substrate off) · the ShurikenValidation project | **New project**, reached by `run_build.sh` through `NP_PROJECT` (D5). It keeps the content root clean and makes Fab packaging and the dependency check trivial |
| D9 | **Publisher name** | the user's current seller name, or a second brand for the sim/horror line | GENRE_SCAN advises a second brand for sim content (niche consistency). **User's call.** |

**Decided by the user, 2026-09-28:** D1 = **a** (clean realistic PBR); D2 = **a** (full v1, 171 meshes); D3 = Pyrecall,
Lumenfold, Rimvault (fictional sport), Clearmark Grading, Halcyon Grading, Sleevesmith, Longhaul Hobby Distribution,
Corner Pocket Cards (`BRAND_NAMES.md`); the user's USPTO screen is still pending. D4-D9 are
still open.

---

## 3. Asset list

### 3.0 Counts by group

| Group | Families | v1 meshes | Notes |
|---|---|---|---|
| A. Shop fixtures | 16 | 50 | Showcases (+ `_Glass` panes), wall cases, slatwall, gondola, racks, card tables, easels, risers |
| B. Sealed product & retail | 8 | 30 | Std pack (3 states + strip), boxes, carton (3 states), shipping boxes, blister, tuck deck, 8 retail accessories |
| C. Singles & protection | 7 | 16 | Card, card stack proxy, sleeves, top-loaders, semi-rigid holder, magnetic holder |
| D. Graded slabs | 3 | 5 | Standard, thick, filled, grading-return box + lid |
| E. Storage & binders | 6 | 21 | Row boxes, monster boxes, binder system, deck box, playmat, dice |
| F. Play area | 2 | 4 | Play tables 2/4/6 seats, folding chair |
| G. Counter & POS | 11 | 15 | Counter, cash drawer, terminal, printer, screen, scanner, price gun, money, phone, laptop, paper bag |
| H. Back room & shipping | 7 | 9 | Warehouse rack, workbench, mailers, tape gun, trash can, bag, hand truck |
| I. Signage & decor | 5 | 9 | Open/closed sign, price tags, posters, storefront and hanging signs |
| J. Shell, lighting & utilities | 4 | 12 | 2 m modular shell, entry door, 4 ceiling lights, scale figure |
| **Total** | **69** | **171** | Moving parts ship as separate meshes (HOUSE pattern: static parts + socket, `Exports/Flashbang/README.md`) |

**Common to every row (not repeated in the tables):**
- Every mesh has LOD0-LOD2, except meshes of 150 triangles or fewer, which ship LOD0 only (4.6).
- Every mesh has at least one `UCX_<name>_LOD0_NN` hull and the UV layout of 4.1 (UV0 print/detail, UV1 unique 0-1 = lightmap
  and per-mesh ORM, UV2 metre-scale tiling where a tileable surface is used).
- Every mesh has a `Seat` socket, a `.sockets.json` (pipeline) and a `.csk.json` (kit data, 4.2).
- Material slot names are `M_CSK_<Part>`, leaf MIs are `MI_CSK_<Part>`. Params come from the masters in section 5.1.
- Fixed glass panes live in their own `_Glass` mesh (4.5). Moving glass (doors, lids) keeps its pane in the moving mesh.
- "Tris" is the LOD0 budget (E), enforced with `qa_check --budget`.
- Ver: **v1**, or **v1.1** (free update) / **later** (add-on or second listing).
- Collision: "1 box" means one UCX box hull; handheld hulls are at least 2 mm thick (4.6).
- Sockets named `Level_*`, `Compartment_*` and `Slot_*` are DISPLAY sockets. `Card`, `Pack_NN`, `Box_NN`, `Slab_NN`, `Row_NN`,
  `Pocket_*`, `Contents`, `Cards_Start`, `Hang_Start` and `Nose` are CONTAIN sockets (4.2).
- Socket counts are about 20-40 per fixture (D, from the tables), not hundreds.

### 3.A Shop fixtures

| # | Asset | What | Size mm W×D×H | Variants | Parts / moving | Sockets | Slots · params | Tris | UCX | Ver |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | `SM_CSK_Showcase_Full_{1219,1778}` + `_Door_{…}` + `_Glass_{…}` | Full-vision glass counter: aluminium profile, glass on 4 sides and the top | L × 508 × 965 (M [D22]); lengths 914/1219/1524/1778 exist (M [D23]), v1 ships 1219 and 1778 (E) | 2 lengths | `_Glass`: 4 panes, top and 2 glass shelves 305 and 356 deep (E\*), glass 6.35 (M [D24]); 152 black kick base (E\*); rear sliding doors, W = L/2 + 25 overlap, travel L/2 − 50 (E), pivot at the closed position | `Level_{Deck,S1,S2}`, `Compartment_<Lvl>_01..04`, `PriceTag_<Lvl>_01..04`, `Door_L`, `Door_R`, `LED`, `Snap_L`, `Snap_R` | Frame (tint), Base, LED (emissive); `_Glass`: Glass | 3,000; glass 600; door 150 | body 2, glass 7, door 1 | v1 (6) |
| A2 | `SM_CSK_Showcase_Half_{1219,1778}` + `_Door_{…}` + `_Glass_{…}` | Half-vision showcase: melamine carcass, glass front and top, storage bay below | L × 457 × 965 (M [D23]) | 2 lengths | Glass front 470 H, storage bay 184 H, 19 carcass, 2 glass shelves 254 D × 6.35 (all E\*); rear doors as A1 | as A1 + `Bay_01..02` | Carcass, Frame, LED; Glass | 2,500; glass 500; door 150 | body 3, glass 4, door 1 | v1 (6) |
| A3 | `SM_CSK_Showcase_Tower` + `_Door` + `_Glass` | Frameless glass tower | 457 × 457 × 1829 (M [D25]) | 1 | 4 glass shelves at 317.5 pitch (E\*), 152 base (E\*); hinged door, pivot on the hinge axis (left, 0-100°, E) | `Level_L1..L5`, `Compartment_<Lvl>_01..02`, `Door`, `Lock`, `LED` | Base, Metal (hinges), LED; Glass | 1,500; glass 400; door 150 | body 2, glass 7, door 1 | v1 (3) |
| A4 | `SM_CSK_Showcase_Wall_1016` + `_Door` + `_Glass` | Lit framed wall/tower case | 1016 × 457 × 1848 (M [D26]) | 1 | Base 203 (E\*), 4 glass shelves × 6.35 (count E); 2 sliding doors of one mesh (533 W, E) | as A3 with `Compartment_<Lvl>_01..03` + `Door_L`, `Door_R`, `Snap_L`, `Snap_R` | Frame, Base, LED; Glass | 2,500; glass 500; door 150 | body 3, glass 6, door 1 | v1 (3) |
| A5 | `SM_CSK_Case_Counter_900` + `_Lid` + `_Glass` | Countertop glass case for singles and slabs | 900 × 450 × 300 (E; fits the 610-deep counter, G1) | 1 | Glass lid, pivot on the hinge axis at the rear top edge, 0-80° (E) | `Level_Deck`, `Compartment_Deck_01..03`, `PriceTag_Deck_01..03`, `Lid`, `Lock` | Frame, Felt; Glass | 1,200; glass 200; lid 150 | body 1, glass 4, lid 1 | v1 (3) |
| A6 | `SM_CSK_Case_WallSlab` + `_Door` | Shallow wall case for graded cards, 4 ledges | 1000 × 90 × 700 (E); 10 × 4 = 40 slab slots (D: 94 pitch × 10 = 940 ≤ 1000; 144 pitch × 4 = 576 ≤ 700; a leaning slab needs about 30 of the 90 depth) | 1 | Glass front, pivot on the hinge axis at the top, lifts 0-85° (E) | `Slot_R<r>_01..10` (fixed count; slab leans 10° back, E), `Door`, `Lock`, `LED`, `Snap_L`, `Snap_R` | Frame, Back (felt), LED; door: Glass | 1,500; door 200 | 5 + 1 | v1 (2) |
| A7 | `SM_CSK_Slatwall_{1000,2000}x2400` | MDF slatwall panel, metric to match the 2 m shell | {1000, 2000} × 19 × 2400 (E); grooves 76.2 on centre (M [D27]), 31 grooves (D: floor(2400/76.2)) | 2 widths | none; end-corner pivot | `Groove_01..31` (left end of each groove; items slide along X), `Snap_L`, `Snap_R` | Slatwall (tint), Insert (aluminium) | 3,000 (E; about 1,400 before bevels, D) | 1 | v1 (2) |
| A8 | `SM_CSK_Hook_Slat_{102,203,305}` | Slatwall hook with a scan-plate tip | Wire Ø 4.76 (M [D28]); lengths within 25-305 (E\*), v1 picks 102/203/305 (E) | 3 lengths | none | `Mount`, `Hang_Start` (the hang grid runs to the tip; pitch per class in `.csk.json`, class Hang = item T + 2, E), `Label` | Metal (chrome/black MI) | 400 | 1 | v1 (3) |
| A9 | `SM_CSK_Shelf_Slat_1000` | Slatwall shelf on brackets | 1000 × 305 × 19 board (E); two per 2000 panel | 1 | none | `Level_S1`, `Compartment_S1_01..03`, `PriceTag_S1_01..03`, `Mount_L`, `Mount_R` | Board, Metal | 600 | 1 | v1 |
| A10 | `SM_CSK_Gondola_{Single,Double,EndCap}_1372` | Gondola shelving section with a **slatwall back**, so A8 hooks fit | 1219 section × 1372 H (M [D30]); base deck 406 D (E\*, range 406-559); kick 100 (E); back grooves 76.2 (M [D27]), 16 per side (D: floor((1372 − 100)/76.2)) | 3 kinds | Uprights slotted on 25.4 pitch (E\*); shelves are separate (A11); end-corner pivot | `Mount_<Side>_NN` every 101.6 (E: every 4th slot), `Groove_<Side>_01..16`, `Level_Deck`, `Compartment_Deck_01..03`, `PriceTag_Deck_01..03`, `Snap_L`, `Snap_R` | Metal (powder coat), Slat back (tint) | 4,000 (Single, EndCap) / 6,000 (Double) | 4 | v1 (3) |
| A11 | `SM_CSK_Gondola_Shelf_{305,406}` + `SM_CSK_Gondola_Corner_1372` | Gondola shelf with a price channel; inside-corner unit | 1219 × {305, 406} (E\*, range 305-457); price lip 38 H (E); corner 610 × 610 (E) | 2 depths + corner | none | `Level_S1`, `Compartment_S1_01..03`, `PriceTag_S1_01..03`, `Mount_L`, `Mount_R`; corner also `Snap_L`, `Snap_R` | Metal | 500 / 2,000 | 1 / 4 | v1 (3) |
| A12 | `SM_CSK_Rack_Wire_914` | Chrome wire "metal rack" (the TCGCSS shelf type, M [G1]) | 914 × 457 × 1829 (E) | 1 | 4 wire decks in real geometry | `Level_L1..L4`, `Compartment_<Lvl>_01..02`, `PriceTag_<Lvl>_01..02`, `Snap_L`, `Snap_R` | Metal | 7,000 (E; fallback: opacity-masked decks at about 3,000) | 5 | v1 |
| A13 | `SM_CSK_Shelf_BoxTier_1219` | Stepped booster-box display shelf ("box shelf", M [G1]) | 1219 × 457 × 1372 (E), 4 tiers tilted 10° (E) | 1 | none | `Level_T1..T4`, `Compartment_<T>_01..03`, `PriceTag_<T>_01..03`, `Snap_L`, `Snap_R` (classes BoxS, BoxL, BoxC, Retail) | Wood (MI), Metal | 1,200 | 5 | v1 |
| A14 | `SM_CSK_CardTable_{08,10,12}` + `_Lid_{…}` | Glass-top card display/sell table (TCGCSS card tables use 8/10/12 slots, M [G1]) | {640, 760, 880} × 460 × 914 (E: cols × 120 + 160, and 2 × 150 + 160; H chosen within the counter range, see G1) | 3 slot counts | Glass lid, pivot on the hinge axis at the rear, 0-80° (E) | `Slot_01..NN` (fixed count; classes Card, CardProt, Slab; 2 rows), `PriceTag_01..NN` in front of each, `Lid` | Frame, Felt (tint); lid: Glass; "vintage" is a wood MI (M concept [G1]) | 1,500; lid 200 | 5 + 1 | v1 (6) |
| A15 | `SM_CSK_Easel_{Slab,Card,Small}` | Bent clear acrylic easel | Slab 66 × 57 × 64; Card 76 × 60 × 57, lip 25; Small 54 × 54 × 51, lip 19 (all M [D31]); acrylic 3 (E) | 3 | none | `Item` (lip, pitched 15° back, E, matching the M 15° riser) | Acrylic | 150 (LOD0 only) | 1 | v1 (3) |
| A16 | `SM_CSK_Riser_Slab_{1,3}` + `SM_CSK_Stand_Card_{3,9}` | Slab riser module and 3-tier riser; acrylic block card stand | Riser 200 × 80 × 25 with 15° slots (M [D32]), 2 slots (D: 2 × 94 ≤ 200); 3-tier 200 × 150 × 75 (E), 6 slots; stand 70 × 40 × 25 (E), slot 3 or 9 (E) | 2 + 2 | none | `Slot_NN` / `Item` | Riser plastic (tint), Acrylic | 300 / 150 | 1-3 | v1 (4) |

**Slot-grid example (D, from E pitches).** `SM_CSK_Showcase_Full_1778`, level `S1` (356-deep glass shelf, interior 1740 wide:
the half-vision glass-front width, M [D23], applied to the full-vision case, E). The `.csk.json` holds one grid per class under
the one `Level_S1` socket: Slab at 94 × 144 → cols floor((1740 − 20)/94) = 18, rows floor((356 − 20)/144) = 2 = 36 slots;
Card at 77 × 102 → 22 × 3 = 66 slots. The builder computes every grid from the interior size, the class footprint and the
clearance (4.2); these numbers are not typed by hand. The fixture carries 3 levels × (1 `Level` + 4 `Compartment` + 4
`PriceTag`) + 2 doors + `LED` + 2 snaps = 32 sockets (D), instead of about 700 per-slot sockets.

### 3.B Sealed product & retail

| # | Asset | What | Size mm | Variants | Parts / moving | Sockets | Slots · params | Tris | UCX | Ver |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | `SM_CSK_Pack_Std_{Sealed,Open,Wrapper}` + `SM_CSK_Pack_Std_Strip` | Foil booster pack: a soft pillow with serrated crimps at both short ends and a back fin seal | 67 × 117 (M [D2][D9]) × 4 (E); crimp 9 deep (E) | 3 states; tier colour (4 tiers; names and colours are buyer params, 4.1) and design are params, not meshes | Open = top crimp removed; the tear strip is a separate mesh (67 × 12, E); Wrapper = flattened, crumpled, for trash | `Seat`, `Grip`, `Face`, `CardsOut` (top opening, +Y out), `Stack` | 1 slot `M_CSK_Pack` (Print master; UV0 front and back tiles, 4.1): Art Index, Tier, Foil Amount | 300 (sealed) / 250 / 200; strip 40 (LOD0 only) | 1 box | v1 (4) |
| B2 | `SM_CSK_Box_Booster_{S,L}` + `_Lid` | Printed display box of packs; the top tears away and folds back into a display tray | S 140 × 80 × 125 (E; a real box measures 133 × 75 × 121, M [D9], but ours is sized so the packs fit: 3.B map); L 190 × 76 × 140 (E, the M "typical" size [D9]); board 2 (E) | 2 sizes | Lid, pivot on the hinge axis at the rear top edge, 0-200° folded back (E); sealed = lid closed + `Shrink Film` param | `Pack_01..36` (S: 2 × 18 standing at 4 pitch), `Pack_01..24` (L: 2 × 12 at 5 pitch), `Lid`, `Grip`, `Face`, `Stack` | Print (Boxes / BoxesL atlas), Board (plain inside) | 400 + lid 150 | 1 + 1 | v1 (4) |
| B3 | `SM_CSK_Box_Collector` + `_Lid` | Two-piece telescoping collector box (generic) | 190 × 89 × 165 (E); inner 186 × 85 × 161 (D, board 2); lid depth 30 (E) | 1 | Lid lifts off (pivot at the closed position) | `Pack_01..08` (2 × 4 **standing on edge** at the back, D), `Dice`, `Cards`, `Sleeves` (in the remaining 69 depth, D), `Lid` | Print (BoxesL atlas), Board | 600 + 300 | 1 + 1 | v1 (2) |
| B4 | `SM_CSK_Carton_Box6_{Closed,Open,Flat}` | Brown corrugated case of 6 S boxes, taped, with a distributor label; Flat = knocked down for trash | Outer 492 × 152 × 137 (D: inner 484 × 144 × 129 = 6 × 80 + 4, 140 + 4, 125 + 4; board 4, E); Flat 644 × 289 × 8 (D: (L + W) × (H + W)) | 3 states | State swap (5.3) | `Box_01..06` (BoxS), `Label`, `Grip_L`, `Grip_R`, `Stack` | Cardboard, Tape, Label (Labels atlas) | 500 / 800 / 100 | 1 / 5 (floor + 4 walls) / 1 | v1 (3) |
| B5 | `SM_CSK_Box_Ship_{S,M,L}_{Closed,Open}` + `SM_CSK_Box_Ship_Flat` | Delivery box for orders **and** grading returns (both M in TCGCSS [G4]); flat = knocked down for trash | S 305 × 229 × 102 (E); M 406 × 305 × 254 (E); L 610 × 406 × 406 (E); inner = outer − 8 (E); Flat 700 × 450 × 8 (E) | 3 sizes × 2 states + flat | State swap | `Contents` (floor origin; the `.csk.json` holds per-class grids for Pack, BoxS, Retail and Slab, computed by the solver), `Label`, `Tape`, `Grip`, `Stack` | Cardboard, Tape, Label | 300-700 | 1 / 5 | v1 (7) |
| B6 | `SM_CSK_Blister_Pack` | Hanging blister: printed card back, clear PET bubble with 2 packs inside | 180 × 250 × 20 (E, no source found); bubble 150 × 130 × 14 (E); euro slot 30 × 10 (E) | 1 | none | class **Hang** (T 20, hook pitch 22): `Hang` (euro slot), `Pack_01..02`, `Face`, `Stack` | Print (Boxes atlas), Film | 300 | 1 | v1 |
| B7 | `SM_CSK_Deck_Tuck` | Sealed starter-deck tuck box | 70 × 30 × 95 (E, no source) | 1 | none | `Grip`, `Face`, `Stack` | Print (Boxes atlas) | 150 (LOD0 only) | 1 | v1 |
| B8 | `SM_CSK_Retail_*` (8 meshes, table below) | Accessories a shop sells: TCGCSS stocks sleeves, deck boxes, dice, collection books, playmats and cleaner (M [G8]) | per row | 8 | none | per row | Print (Boxes atlas cell), Film, Plastic | per row | 1 each | v1 (8) |

**B8 retail accessories (all sizes E).** Items with a hang tab are class Hang (pitch T + 2 on A8 hooks).

| Mesh | What | Size W × D × H | Class | Sockets | Tris |
|---|---|---|---|---|---|
| `SM_CSK_Retail_SleeveBox100` | Box of 100 deck sleeves with a hang tab | 72 × 42 × 98 + 40 tab (inner 68 × 38 × 94 holds a 66 × 91 sleeve, D) | Hang (T 42) | `Hang`, `Stack`, `Face`, `Grip` | 200 |
| `SM_CSK_Retail_TopLoaderPack25` | 25 top-loaders in a bag with a header card | 82 × 35 × 108 + 30 header (holds 76.2 × 101.6, D) | Hang (T 35) | as above | 300 |
| `SM_CSK_Retail_PennyPack100` | 100 penny sleeves in a bag with a header | 72 × 12 × 97 + 25 header | Hang (T 12) | as above | 150 |
| `SM_CSK_Retail_DiceClam` | Clamshell of 7 dice (dice as baked detail) | 60 × 25 × 130 incl. tab | Hang (T 25) | as above | 400 |
| `SM_CSK_Retail_BinderWrapped` | E3 binder in shrink film with a sticker | 250 × 55 × 295 | Binder | `Stack`, `Face`, `Grip` | 500 |
| `SM_CSK_Retail_PlaymatTube` | Tube holding a rolled playmat (E5 Rolled Ø 45 × 356) | Ø 70 × 380 | Retail | `Stack`, `Face`, `Grip` | 300 |
| `SM_CSK_Retail_DeckBoxPack` | E4 deck box in a window box | 82 × 86 × 116 | Deck | `Stack`, `Face`, `Grip` | 300 |
| `SM_CSK_Retail_CleanerBottle` | 60 ml card-cleaner spray bottle | Ø 40 × 140 | Retail | `Stack`, `Face`, `Grip` | 400 |

Hook capacity (D: floor((L − 20)/(T + 2))) on the 102/203/305 hooks: blister 3/8/12, penny pack 5/13/20, sleeve box 1/3/6.

**Pack → box map (D; the table lives in `csk_lib/spec.py` and the fit test is zero-tolerance on render bounds).** These are
fictional products, so the sizes are chosen to fit together rather than copied from franchise boxes.

| Container | Inner W × D × H | Holds | Arrangement | Check |
|---|---|---|---|---|
| `Box_Booster_S` | 136 × 76 × 121 | 36 `Pack_Std` | 2 across × 18 deep, standing, 4 pitch | 2 × 67 = 134 ≤ 136; 18 × 4 = 72 ≤ 76; 117 ≤ 121 |
| `Box_Booster_L` | 186 × 72 × 136 | 24 `Pack_Std` | 2 × 12 at 5 pitch, standing | 134 ≤ 186; 60 ≤ 72; 117 ≤ 136 |
| `Box_Collector` | 186 × 85 × 161 | 8 `Pack_Std` + dice + sleeves + cards | 2 × 4 standing on edge | 134 ≤ 186; 16 ≤ 85; 117 ≤ 161 |
| `Carton_Box6` | 484 × 144 × 129 | 6 `Box_Booster_S` | in a row, standing | 6 × 80 = 480 ≤ 484; 140 ≤ 144; 125 ≤ 129 |
| `Blister_Pack` | bubble 150 × 130 × 14 | 2 `Pack_Std` | side by side, lying | 134 ≤ 150; 117 ≤ 130; 4 ≤ 14 |
| `Box_GradeReturn` | 142 × 117 × 162 | 8 `Slab_Std` | on edge, 14 pitch | 8 × 14 = 112 ≤ 142; 84 ≤ 117; 134 ≤ 162 |

The Tall pack is dropped from v1; it returns in v1.1 with its own box (3.11).

### 3.C Singles & protection

| # | Asset | What | Size mm W×H×T | Variants | Parts | Sockets | Slots · params | Tris | UCX | Ver |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | `SM_CSK_Card_{Std,Small}` | Blank trading card, rounded corners, no bend | Std 63 × 88 (M [D1]) × 0.30 (E; real range 0.25-0.76 M [D2]); Small 59 × 86 (M [D1]); corner R 3 (E) | 2 | none | `Seat`, `Face`, `Grip` (bottom-edge centre) | **1 slot** `M_CSK_Card` (UV0 tiles: front, back, edge, 4.1), so one draw call: Art Index, Back Index, Tier, Foil, condition params | **96** / 28 / 12 | 1 box, 2 mm thick, centred | v1 (2) |
| C2 | `SM_CSK_CardStack_{10,30,90}` | Solid card-block proxy with an edge-stripe texture, for storage-box fill levels and thick stacks | 63 × 88 × {10, 30, 90} (10 = 33 cards at 0.30, D) | 3 | none | `Seat`, `Top` | `M_CSK_Card` (front, back, edge-stripe tiles) | 60 (LOD0 only) | 1 box | v1 (3) |
| C3 | `SM_CSK_Sleeve_Penny` | Thin clear polypropylene pouch, open on one short edge | 66.7 × 92.1 (M in inches [D3]; mm D) × 0.5 overall (D: 2 skins 0.4 apart + 2 × 0.05 film, E) | 1 | none | `Card` (inside, card `Seat` lands here) | `M_CSK_Film` | 60 (LOD0 only) | 1 box, 2 mm | v1 |
| C4 | `SM_CSK_Sleeve_Deck_{Std,Small}` | Deck sleeve: clear front, matte coloured back with our own back art | 66 × 91 / 62 × 89 (M [D1]) | 2 | none | `Card` | Film (front), `M_CSK_SleeveBack` (Cards atlas cell + tint) | 80 (LOD0 only) | 1 box, 2 mm | v1 (2) |
| C5 | `SM_CSK_TopLoader_{35pt,130pt}` + `SM_CSK_TopLoader_35pt_Filled` | Rigid PVC top-loader with a thumb notch | Outer 76.2 × 101.6 (M [D4]); inner 69 × 97 (E\*; another source gives 69.9 × 98.4); card gap 0.89 / 3.30 (D from pt [D4]); overall T 2.0 / 4.8 (E); notch 20 W (E) | 2 thicknesses + filled | none | `Card`, `Face`, `Grip`, `Stack` | `M_CSK_PVC` (translucent); Filled: 1 opaque Clear Coat section with the card art (4.5) | 300 (+ 96) | 1 box | v1 (3) |
| C6 | `SM_CSK_Holder_SemiRigid` | Semi-rigid holder with a pull tab | 84.1 × 123.8 (M in inches [D5]) × 1.0 (E); tab 30 × 12 (E) | 1 | none | `Card` | PVC | 150 (LOD0 only) | 1 box, 2 mm | v1 |
| C7 | `SM_CSK_Holder_Magnetic` + `_Front` + `_Back` + `_Filled` | Magnetic card holder: two clear halves, 4 magnets in the border | Outer 74.3 × 110.4 (M [D6]) × 6 (E); inner well 67.6 × 94.7 (E\*); magnets Ø 6 (E) | closed / 2 halves (opening) / filled | The halves pull apart along Z; each half's pivot is at the closed position | `Card`, `Face`, `Grip`, `Stack`, `Half` (on the back half) | Body (opaque border and magnets, Clear Coat), Window (translucent); Filled: opaque only | 800 | 1 box | v1 (4) |

### 3.D Graded slabs

**Design (E, original):** 84 × 134 × 7.0 overall, inside every measured range (W 81-86, H 130-139, T 5-8, M [D7]; the
sources conflict on thickness). The original details are ours, not traced from any grader:
- a 3.5 mm perimeter frame with **4 mm corner chamfers** (not radii);
- a 24 mm label band (E) on the top;
- an inner card well of 65 × 90 × 1.0 (E: card + 1 mm each side; depth ≥ the 0.76 M max card thickness) held by our own
  gasket frame;
- 0.6 mm stacking ridges on the back edges, **included in the 7.0**, and a matching 0.6 recess band on the front, so
  stacked slabs nest and the stack pitch is 7.0 (D);
- a weld-seam line.

The empty shell alone goes through the blind brand test (6.3). If a judge reads it as the leading grader, the label band
(height and position) changes before P3 (risk R14).

The slab ships **empty**; the card is C1 in the `Card` socket. Sections: `M_CSK_SlabBody` is **opaque** (label, gasket and
frame, with Clear Coat for the acrylic look) and `M_CSK_SlabWindow` is the **only translucent section** (the window skins).

| # | Asset | What | Size mm W×H×T | Variants | Parts | Sockets | Slots · params | Tris | UCX | Ver |
|---|---|---|---|---|---|---|---|---|---|---|
| D1 | `SM_CSK_Slab_Std` | Empty graded slab, label insert included | 84 × 134 × 7 (E, inside the M range) | the label is a param: grader (2), style (2), blank (buyer text), `Grade` 1-10 | none | `Card` (well floor centre), `Label`, `Face`, `Grip`, `Stack` (7.0 pitch) | `M_CSK_SlabBody` (Labels atlas cell by `Label Index`/CD5 + Grade digits), `M_CSK_SlabWindow` (Glass master, acrylic MI) | 1,200 / 400 / 60 | 1 box | v1 |
| D2 | `SM_CSK_Slab_Thick` | For thick cards | 84 × 134 × 8 (E, top of the M range); well depth 3.4 (E ≥ 3.30 D) | as D1 | none | as D1 (8.0 pitch) | as D1 | 1,200 | 1 box | v1 |
| D3 | `SM_CSK_Slab_Std_Filled` | D1 with the card inside, fully opaque: the window is a Clear Coat over the card art | as D1 | as D1 + the card's params (CD0 art, CD5 label) | none | as D1 minus `Card` | **1 opaque section** (Print master, `Clear Coat Window` switch) → 1 draw, HISM-friendly | 1,300 | 1 box | v1 |
| D4 | `SM_CSK_Box_GradeReturn` + `_Lid` | Grading-return box with a foam insert for 8 slabs on edge (8 cards per submission, M [G4]) | 150 × 125 × 170 (E; inner 142 × 117 × 162, board 4; 8 × 14 pitch = 112, D) | 1 | Lid lifts off (pivot at the closed position) | `Slab_01..08` (fixed), `Lid`, `Label` | Cardboard, Foam, Label | 500 + 150 | 1 + 1 | v1 (2) |

### 3.E Storage & binders

| # | Asset | What | Size mm W×D×H | Variants | Parts | Sockets | Slots · params | Tris | UCX | Ver |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | `SM_CSK_Box_Row_{100,400,800}` + `_Lid` | White corrugated row box with a fold-over lid; also the TCGCSS "bulk box" and a slab shipper (M [D39]) | Outer 85.7 / 200.0 / 381.0 × 104.8 × 76.2; inner 63.5 / 177.8 / 358.8 × 95.3 × 69.9 (M [D16]); board 3 (E) | 3 | Lid, pivot on the hinge axis at the back edge, 0-180° (E) | `Cards_Start` (row origin; cards stand on their long edge; pitch 0.3 raw, 0.5 penny-sleeved), `Lid`, `Label`, `Stack` (76.2 pitch, D = H) | `M_CSK_BoardWhite`, Label | 300 + 150 | 5 + 1 | v1 (6) |
| E2 | `SM_CSK_Box_Monster_{3200,5000}` + `_Lid` | Monster box: fold-up row dividers, telescoping lid, hand holes | 336.6 × 406.4 × 103.2, 4 rows; 419.1 × 495.3 × 104.8, 5 rows (M [D16]; rows D); lid depth 40, hand hole 90 × 30 (E) | 2 | Lid lifts off (pivot at the closed position) | `Row_01..05`, `Lid`, `Stack` | BoardWhite, Label | 600 + 200 | 6 + 1 | v1 (4) |
| E3 | `SM_CSK_Binder_{Body,Cover,Page,Closed}` | 3-ring binder: back cover, spine and D-rings; hinged front cover; 9-pocket page; merged closed binder for shelves | Cover 247.7 × 292.1 (M [D17]); spine 51 (E, range 25-76 E); page 220.7 × 293.7, pockets 65.1 × 90.5, 3 holes at 108 (M [D17]) | spine width is a param | Cover and pages pivot on their hinge axes (spine; ring axis), 0-180° | Body: `Ring_01..20` (page stations on the arc, E), `Cover`; Page: `Pocket_F01..09`, `Pocket_B01..09`; Closed: `Stack`, `Face` | `M_CSK_BinderCover` (PU tint + spine label cell), Metal, Film | 1,500 / 300 / 400 / 800 | 3 / 1 / 1 / 1 | v1 (4) |
| E4 | `SM_CSK_DeckBox` + `_Lid` | Flip-top deck box for 100 sleeved cards | Outer 76 × 80 × 108 (E); inside 68 × 71 × 100 (M [D18]) | 1 | Lid, pivot on the hinge axis at the rear top edge, 0-110° (E) | `Cards`, `Lid`, `Grip`, `Stack` | Plastic (tint), Print (emblem) | 600 + 300 | 1 + 1 | v1 (2) |
| E5 | `SM_CSK_Playmat_{Flat,Rolled}` | Cloth-top rubber playmat | Flat 609.6 × 355.6 × 2 (M [D19]); rolled Ø 45 × 356 (D: √(20² + 4·609.6·2/π) with a 20 core, E); stitched edge 2 (E) | 2 states | State swap | Flat: `Zone_Deck`, `Zone_Play`, `Zone_Discard` (E); Rolled: `Grip` | Print (Playmats atlas), Rubber | 200 / 600 | 1 box | v1 (2) |
| E6 | `SM_CSK_Die_{D6,D20}` + `SM_CSK_Token_22` | Resin dice and a counter token | d6 16 (M [D20]); d20 22 (E); token Ø 22 × 2 (E) | 3 | none | `Grip` | `M_CSK_Resin` (tint, pip-ink mask) | 300 / 500 / 100 (LOD0 only) | 1 | v1 (3) |

### 3.F Play area

| # | Asset | What | Size mm W×D×H | Variants | Parts | Sockets | Slots · params | Tris | UCX | Ver |
|---|---|---|---|---|---|---|---|---|---|---|
| F1 | `SM_CSK_Table_Play_{2,4,6}` | Folding tournament table; one match = 2 facing mats | {914, 1524, 1829} × 762 × 737 (H M [D33]; 1829 × 762 E; 3 matches on 1829: 3 × 609.6 = 1828.8, D; 2 × 356 = 712 ≤ 762, D) | 3 seat counts; black/white/wood are MIs (M concept, TCGCSS 0.60 [G1]) | none | `Mat_<m>A`, `Mat_<m>B`, `Deck_<m>A/B`, `Chair_01..06` (chair `Seat` target, facing the table), `Zone_<m>` | Top (tint), Metal | 1,000 | 3 | v1 (3) |
| F2 | `SM_CSK_Chair_Folding` | Steel folding chair | 450 × 520 × 800, seat 445 (E) | 1 | none | `Sit` (seat-top centre, NPC sit), `Grip` | Metal, Seat (tint) | 1,200 | 3 | v1 |

### 3.G Counter & POS

Every screen (G3, G5, G9, G10) has its own `M_CSK_Screen` slot with a 0-1 UV0 island, so a buyer can put a render target or
widget material on it. Every POS shape is an **original design** (E); only the sizes below come from research.

| # | Asset | What | Size mm W×D×H | Variants | Parts | Sockets | Slots · params | Tris | UCX | Ver |
|---|---|---|---|---|---|---|---|---|---|---|
| G1 | `SM_CSK_Counter_1397` | Cash wrap: laminated carcass, worktop, bag shelf | 1397 (M [D34]) × 610 (E\*, bottom of a 610-914 range) × 965 (E, inside a 914-1067 range, E\*; chosen to line up with the 965 showcases) | 1 | none | `POS`, `Drawer`, `Terminal` (customer side), `Printer`, `Scanner`, `Drop` (customer item drop), `PriceGun`, `Bag`, `Phone`, `Staff`, `Snap_L`, `Snap_R` | Carcass, Top, Trim | 2,000 | 3 | v1 |
| G2 | `SM_CSK_CashDrawer` + `_Tray` | Steel cash drawer with a 5-bill / 8-coin tray | 409 × 417 × 112 (M [D35]); counts 5 / 8 (E\*) | 1 | The tray slides toward the staff side (+Y), travel 280 (E); pivot at the closed position | `Tray`, `Bill_01..05`, `Coin_01..08` | Metal, Plastic | 800 + 400 | 1 + 1 | v1 (2) |
| G3 | `SM_CSK_Terminal_Card` | Generic countertop card terminal with a keypad; original shape | 168 × 81 × 56 (E\*: near common countertop terminals [D36], source of the numbers not recorded) | 1 | none | `CardSlot`, `Tap`, `Grip` | Plastic, `M_CSK_Screen` | 800 | 1 | v1 |
| G4 | `SM_CSK_Printer_Receipt` | Clamshell receipt printer; original shape | 179 × 152 × 118 (E); paper 80 nominal (M [D37]) | 1 | none | `PaperOut` | Plastic | 700 | 1 | v1 |
| G5 | `SM_CSK_POS_Screen` | Generic POS screen on a stand | Screen 360 × 230 on a 200 × 200 base (E) | 1 | none | `Screen` | Plastic, `M_CSK_Screen` | 800 | 1 | v1 |
| G6 | `SM_CSK_Scanner` + `_Cradle` | Handheld barcode scanner and its cradle | 160 × 70 × 95 (E) | 1 | Picked up from the cradle | `Grip`, `Beam`; cradle: `Scanner` | Plastic, Emissive (beam window) | 600 + 200 | 1 + 1 | v1 (2) |
| G7 | `SM_CSK_PriceGun` | Pistol-grip price labeller; original body shape | Body 190 × 45 × 125 (E); label 19.8 × 11.2 (M [D38]) | 1 | none | `Grip`, `LabelOut` | Plastic | 1,200 | 1 | v1 |
| G8 | `SM_CSK_Bills_Stack` + `SM_CSK_Coin` | Generic money: plain notes and a coin, **no real currency design** | 150 × 70 × 10 (E); Ø 24 × 2 (E) | 2 | none | `Grip`, `Stack` | Paper (Signs atlas, generic), Metal | 100 / 120 (LOD0 only) | 1 | v1 (2) |
| G9 | `SM_CSK_Phone` | Generic smartphone, the ordering device (TCGCSS orders on a phone, M [G9]) | 72 × 150 × 8 (E) | 1 | none | `Grip`, `Screen` | Plastic, `M_CSK_Screen` | 300 | 1 box | v1 |
| G10 | `SM_CSK_Laptop` + `_Lid` | Generic laptop for back-office ordering | 320 × 220 × 16 closed (E) | 1 | Lid, pivot on the hinge axis, 0-130° (E) | `Lid`, `Grip`, `Screen` (on the lid) | Plastic, Metal, `M_CSK_Screen` | 500 + 300 | 1 + 1 | v1 (2) |
| G11 | `SM_CSK_Bag_Paper` | Kraft paper shopping bag with twisted handles | 250 × 130 × 300 (E) | 1 | none | `Contents`, `Grip` | Kraft (tint), Print (shop-logo cell, Signs atlas) | 400 | 1 | v1 |

### 3.H Back room & shipping

The stocking loop is "order, it arrives outside, bring it in, unbox, shelve, throw out the box, set the price" (M [G10]).
The kit covers it with B4/B5 (contents grids and Flat states), H7 and the trash items.

| # | Asset | What | Size mm W×D×H | Variants | Parts | Sockets | Slots · params | Tris | UCX | Ver |
|---|---|---|---|---|---|---|---|---|---|---|
| H1 | `SM_CSK_Rack_Warehouse_1829` | Boltless steel warehouse rack, 4 levels | 1829 × 610 × 2134 (E) | 1 | none | `Level_L1..L4`, `Compartment_<Lvl>_01..03` (classes Carton, BoxShip, Retail), `Snap_L`, `Snap_R` | Metal (tint), Deck (board) | 1,500 | 6 | v1 |
| H2 | `SM_CSK_Workbench_1524` | Workbench with a cutting-mat top | 1524 × 762 × 914 (E) | 1 | none | `BulkOut`, `Work`, `Tool_01..04`, `Lamp` | Wood, Metal, Mat (Print) | 1,500 | 3 | v1 |
| H3 | `SM_CSK_Mailer_{S,L}` | Kraft bubble mailer | 100 × 200 × 5 / 150 × 250 × 6 (E) | 2 | none | `Contents`, `Label`, `Grip` | Kraft, Label | 150 (LOD0 only) | 1 | v1 (2) |
| H4 | `SM_CSK_TapeGun` | Tape dispenser gun | 250 × 75 × 180 (E) | 1 | none | `Grip` | Plastic, Tape | 800 | 1 | v1 |
| H5 | `SM_CSK_TrashCan` + `_Lid` | Swing-lid shop bin | Ø 400 × 700 (E) | 1 | Swing lid, pivot on its swing axis | `Lid`, `Drop`, `Bag` | Plastic (tint) | 800 + 200 | 2 + 1 | v1 (2) |
| H6 | `SM_CSK_TrashBag_Full` | Full tied bag | Ø 450 × 600 (E) | 1 | none | `Grip` | Plastic film | 600 | 1 | v1 |
| H7 | `SM_CSK_HandTruck` | Two-wheel hand truck (dolly) for bringing deliveries in | 450 × 500 × 1200 (E); nose plate 350 × 200 (E); wheels Ø 250 (E) | 1 | none | `Nose` (stack origin for cartons and ship boxes), `Grip`, `Axle` (tilt axis) | Metal (tint), Rubber | 2,500 | 3 | v1 |

Litter reuses `SM_CSK_Pack_Std_Wrapper` and `_Strip`, `SM_CSK_Box_Ship_Flat`, `SM_CSK_Carton_Box6_Flat` and `SM_CSK_Card_Std`.

### 3.I Signage & decor

| # | Asset | What | Size mm | Variants | Parts | Sockets | Slots · params | Tris | UCX | Ver |
|---|---|---|---|---|---|---|---|---|---|---|
| I1 | `SM_CSK_Sign_OpenClosed` + `_Plate` | Hanging open/closed sign; the plate flips 180° about Z | Plate 300 × 150 × 5 (E) | 1 | Plate on a hanger (chain + suction hook), pivot on the flip axis | `Plate`, `Mount` | Print (Signs atlas, 2 faces), Metal | 300 + 60 | 1 + 1 | v1 (2) |
| I2 | `SM_CSK_PriceTag_{Shelf,Tent,Hook}` | Price tags: shelf-edge strip clip, folded tent card, hook scan plate | 76 × 32 × 2 (E, clips into the 38 lip, E); 60 × 40 tent (E); 76 × 38 (E) | 3 | none | `Mount`, `Face`, `Text` | `M_CSK_PriceTag` (Price digits, 4.4) | 40-80 (LOD0 only) | 1 | v1 (3) |
| I3 | `SM_CSK_Poster_{A2,A1}` | Framed poster of original set art | 420 × 594 / 594 × 841 (ISO 216 sizes, common knowledge, not from the research: E) | 2 | none | `Mount` | Print (Signs atlas), Frame | 200 | 1 | v1 (2) |
| I4 | `SM_CSK_Sign_Storefront` | Lightbox shop sign | 1829 × 100 × 457 (E) | 1 | none | `Mount` | Print + Emissive | 400 | 1 | v1 |
| I5 | `SM_CSK_Sign_Hanging` | Ceiling-hung category sign ("Singles", "Sealed", "Play Area") | 600 × 10 × 200 (E) | the text is an atlas cell | none | `Mount_L`, `Mount_R` | Print | 100 (LOD0 only) | 1 | v1 |

### 3.J Shell, lighting & utilities

| # | Asset | Size mm | Notes | Ver |
|---|---|---|---|---|
| J1 | `SM_CSK_Shell_{Wall,Wall_Window,Wall_Door,Floor,Ceiling}_2000` | Walls 2000 × 150 × 3000; floor and ceiling 2000 × 2000 × 20 (E) | Whole-metre modules; end-corner pivot and `Snap_L`/`Snap_R` (HOUSE, `ASSET_GUIDELINES.md` §1). Materials: plaster, vinyl floor, ceiling tile (tint MIs). 100-600 tris each | v1 (5) |
| J2 | `SM_CSK_Door_Entry` + `_Frame` | Leaf 900 × 45 × 2100 (E); frame 1000 × 150 × 2200 (E), fits the `Shell_Wall_Door_2000` opening | Glass shop door. The leaf pivots on the hinge axis, 0-100° (E), and keeps its pane (a moving pane). Sockets: `Door`, `Handle`, `Bell`, `Sign` (for I1). 800 + 400 tris | v1 (2) |
| J3 | `SM_CSK_Light_{Panel600,Track2000,TrackHead,Pendant}` | Panel 600 × 600 × 12; track rail 2000 × 35 × 20; head Ø 70 × 150; pendant shade Ø 300 × 250 on a 1000 cord (all E) | The showcases have `LED` sockets, and these are the kit's lamps. Each has a `Light` socket where a light component goes (aimed along the socket's +X), and `Mount`. The track has `Head_01..06` (fixed) and the head pivots on its tilt axis. Metal (tint), Emissive. 200 / 300 / 400 / 600 tris | v1 (4) |
| J4 | `SM_CSK_ScaleFigure` | 1800 tall (E) | An **original** neutral scale figure for `L_CSK_Overview`; the UE mannequin may appear in media only (5.2). 2,000 tris | v1 |

### 3.11 v1.1 and later (not in the 171)

| Item | Why deferred | Ver |
|---|---|---|
| Pack-opener machine S/M/L (M in TCGCSS [G1]) and pack vending machine (E\*: reported in Card Shop Simulator Multiplayer) | Bigger original industrial designs; "nice" in the game research | v1.1 |
| Tall pack (75 × 145 × 6, E) with **its own** box | No v1 box fits it (145 > the L box's 136 inner, D) | v1.1 |
| Grading station (magnifier lamp, inspection light) and streaming desk (camera, ring light, mic) | M in Sports Card Shop Sim and Sports Card Collector Sim [G6] | v1.1 |
| Card drawer cabinet (TCGCSS card storage shelf, 1,000 cards, M [G1]) | Drawer rig | v1.1 |
| Tins: rectangular 178 × 133 × 51 (M [D13]); an **original** hex tin instead of the sphere | A sphere with a band reads as a franchise ball (IP, 6.2) | v1.1 |
| Starter window box, team bag, slab sleeve, zip binder, 10-cell sorting box, sorting tray, pegboard + hooks, pallets, 1829 × 1219 gaming table, stacking chair, folded chair | Low demand signal | v1.1 |
| More fixture lengths (914/1524 showcases, other gondola heights), second counter length | Parameters only | v1.1 |
| Pre-filled Packed Level Actors (a filled showcase, a filled shelf) | Dressing convenience | v1.1 |
| Tournament bracket board, banners, standee, statue plinth, dirt decals | Decor | later |
| Figure / plush / board-game boxes | They overlap GENRE_SCAN #5 (Retail Packaging System) and belong there | later |
| Sports add-on: memorabilia case, ball cube, jersey frame, 12-box hobby case | A separate add-on | later |
| Stylized Skin listing (D1) | A separate listing | later |
| GLB exporter (D6) | Pipeline work | v1.1 |

**Cut from v1 in revision 2:** `Pack_Slim_*` (4 meshes; indistinguishable from Std at shelf distance), `Tray_Sort_24`
(niche at 3,000 tris), `Counter_1829`, and `L_CSK_Stress` from the shipped package (it stays in the repo).

**Lean v1 (D2 option b, about 115 meshes):**
- Listed cuts, 31 meshes, giving 140:
  - the second showcase length (−6);
  - the `_Filled` variants (−3);
  - `Slatwall_1000` (−1);
  - hook 203 (−1);
  - the ship-box M size (−2);
  - `Box_Row_800` and `Monster_5000` with their lids (−4);
  - `CardStack_30` (−1);
  - the demo shell (−5; the map uses BSP);
  - `Poster_A1` (−1);
  - 4 of the 8 retail items (−4);
  - the laptop (−2);
  - the pendant (−1).
- About 25 more come from the lowest-demand rows at G0.
- `Case_WallSlab` **stays**, because thumbnail shot 1 is built around it.

---

## 4. Systems shared across assets

### 4.1 Art system: UVs, atlases, buyer art (all E unless flagged)

**UV layout (every mesh).**

| Channel | Content | Graded by |
|---|---|---|
| UV0 | Print and detail. Each print face spans a full 0-1 tile: front (0,0), back (1,0), label (0,1); non-print islands (edges, inside board, frame) go in the U −1..0 tile. Everything stays inside −1..2 and does not overlap | `qa_check` (tile range, overlap) + `qa_csk` (print px/mm) |
| UV1 | Unique 0-1 layout: the lightmap **and** the per-mesh ORM bake (R = baked AO, G = roughness, B = metal), 256-1K per mesh | `qa_check --require-uv1` |
| UV2 | Metre-scale tiling for `M_CSK_Surface_Master` (1 UV unit = 1 m), only on meshes that use a tileable set | `qa_csk` (scale check; `qa_check` does not grade UV2) |

Because every print face is 0-1 in UV0, a buyer who drops a plain one-texture material on `SM_CSK_Card_Std` sees the whole
image on both faces, and the FBX/GLB downloads show each mesh's default texture instead of a 1/64 corner.

**Three art paths in `M_CSK_Print_Master` (static switches):**

| Path | How | For |
|---|---|---|
| `Use Atlas` (default) | The material maps each tile into the chosen cell: offset = (i mod cols, floor(i/cols)) / (cols, rows), or a `Cell Rect` for cells that span several grid cells. The V flip follows the `MF_LetteringBand` technique (HOUSE), in a CSK copy | The kit's own art, HISM with per-instance data |
| Plain textures | `Front Texture`, `Back Texture` (and `Label Texture`), sampled straight on the 0-1 tiles | Hero close-ups (pack reveal) and buyers' own single images |
| `Use Texture Array` | A Texture2DArray indexed by `Art Index` or CD0 | Buyers with hundreds of cards, one draw per material |

**Buyer tools (shipped):**
- `csk_pack_cards.py` (standalone Python 3 + Pillow) packs a folder of PNGs into the kit's atlas format: cell grid,
  16 px dilated padding, power of two, plus a JSON index. It is not UE Python, because UE's embedded Python has no image library.
- `csk_make_card_array.py` (UE Python editor script) builds a Texture2DArray from imported textures. Creating the array
  from Python is to be verified at G1 (risk R15).
- Blank templates ship as separate PNGs with a UV-layout overlay, one per print mesh (card front and back at 10 px/mm, pack,
  box dielines, slab label, playmat).
- The same rule covers packs, boxes, slab labels and playmats. A **blank slab-label cell** lets buyers print their own card
  name (through the `Label` socket's text component or a packed PNG) and use the `Grade` digits.

**Atlases.** A pixel-grid atlas, as `Scripts/props/props_lib/atlas.py` does it: an integer px/mm, art blitted at integer
offsets, 16 px padding, identical UVs on every LOD (HOUSE precedent). Cells are power-of-two sizes. Atlases carry BaseColor
and a mask `_M` (R = tier-tint region, G = foil region, B = holo pattern, A = roughness); AO lives in the per-mesh ORM on UV1.

| Atlas | BC / M size | Cells | Density | Contents (v1) |
|---|---|---|---|---|
| `T_CSK_Cards` | 4096² / 2048² | 8 × 8 of 512² | 5 px/mm (card = 315 × 440 px) | 48 fronts (3 lines × 16 arts), 4 backs, 4 sleeve-back patterns, 2 blank frames, 6 spare |
| `T_CSK_Packs` | 2048² / 2048² | 2 × 4 of 1024 × 512 (front and back side by side) | 3 px/mm (front + back = 402 × 351 px) | 3 lines × 2 designs = 6, 2 spare |
| `T_CSK_Boxes` | 4096² / 2048² | 4 × 4 of 1024² | 2 px/mm (S dieline 2 × (140 + 80) × (125 + 2 × 80) = 440 × 285 mm = 880 × 570 px, D) | 3 S boxes, 3 tuck boxes, 1 blister back, 8 retail items, 1 spare |
| `T_CSK_BoxesL` | 4096² / 2048² | 2 × 4 of 2048 × 1024 | 2 px/mm (L wrap 532 × 292 mm = 1064 × 584 px; Collector base wrap 558 × 165 + lid 250 × 149 mm = 1116 × 628 px, D) | 3 L boxes, 3 collector boxes, 2 spare |
| `T_CSK_Labels` | 2048² / none | 4 × 16 of 512 × 128; larger labels span cells | 4 px/mm (slab label 76 × 24 mm = 304 × 96 px) | 2 graders × 2 styles, 1 **blank slab label**, grade-word strip, price-glyph strip, 2 shelf/category labels, carton label, shipping label, 3 binder-spine labels |
| `T_CSK_Playmats` | 4096² / none | 2 × 4 of 2048 × 1024 | 2 px/mm (mat = 1220 × 712 px) | 8 playmats (19 exist in TCGCSS, M [G3]; 8 is E) |
| `T_CSK_Signs` | 4096² / 2048² | 2048² quadrants, subdivided | 1-3.45 px/mm | 2 posters, storefront sign, open/closed faces, 3 category signs, 3 default screen UIs (POS, phone, laptop), shop-bag logo, generic money print |

**Texture budget (D, from the E sizes; DXT1 BaseColor, BC7 mask, full mips at 4/3).** 4K DXT1 = 10.7 MiB, 2K DXT1 = 2.7 MiB,
2K BC7 = 5.3 MiB.
- Atlases: about 85 MiB.
- Per-mesh ORMs: about 45 MiB (512² handheld and medium, 1K fixtures, E).
- About 15 tileable 1K sets: about 40 MiB.
- Total: **about 170 MiB**, against 400-500 MiB for the revision 1 plan.

**Texture-size waiver (dated 2026-09-28, E).** `ASSET_GUIDELINES.md` §3 says "2048 for props". The five 4096 BaseColor atlases
each serve 20-100 meshes, so they are logged here as an explicit waiver. Masks, per-mesh maps and tileables stay at 2048 or
smaller, and nothing goes above 4K in the exchange upload.

**Tier:** 4 colour params (`Tier 0..3 Colour`) and 4 name strings, all buyer-editable. The kit's defaults are **our own**
(E): grey, teal, amber and magenta, named Common / Uncommon / Rare / Mythic. The media never shows a blue/gold/purple/red
"Basic-Rare-Epic-Legendary" ladder as the pack's identity (the generic ladder is M [G2]). One art cell serves all four tiers.

**Card condition look (shader only, 5.1):**
- `Centering Offset` shifts the art UV inside the border.
- `Corner Wear`, `Edge Whitening` and `Surface Scratch` are masks from a shared 1K `T_CSK_Wear_M`.
- `Crease` is a normal-mask blend.
- All of these are per-instance capable (4.6).

**Fictional brands (D3):** 3 card lines (one sports-style), 1 set each in v1, 16 arts per line, 2 graders, 1 accessory
brand, 1 distributor, 1 demo shop. That is 8 names, logged in `WorkFiles/cardshop/BRAND_NAMES.md` with the USPTO search date.

**Texel-density check:**
- Print meshes get **no** `qa_check --texel` target, because `--texel` grades the whole mesh.
- `qa_csk.py` grades each print tile's exact px/mm and the non-print islands' density separately.
- Fixtures without print use `qa_check --texel 10.24` as usual.

**Close-up limit:** a card at 5 px/mm is 440 px tall. That is enough on shelves, but soft in a full-screen pack reveal, so the
reveal uses the plain-texture path with a 1024² image (risk R1). Readability is checked at **1.25× game scale** at G1 (E),
because genre games often enlarge handheld stock.

### 4.2 Slot and socket standard ("any product fits any case or shelf")

**Item classes.** Every item's `.csk.json` declares one class; every display surface declares which classes it accepts. Class
codes are CamelCase with no underscores, so socket names split cleanly on `_`. The slot pitch is the footprint plus 10 mm
clearance (E) unless stated.

| Class | Items | Footprint W×D×H mm (lying or standing as stored) | Pitch |
|---|---|---|---|
| Card | C1 raw or penny-sleeved | ≤ 66.7 × 92.1 × 0.5 | 77 × 102 |
| CardProt | C4-C7 | ≤ 84.1 × 123.8 × 6 | 94 × 134 |
| Slab | D1-D3 | 84 × 134 × 7 (8) | 94 × 144 |
| Pack | B1 | 67 × 117 × 4 | 77 × 127 lying; 4 standing in boxes |
| Hang | B6 and hang-tab retail items | per item, T = depth off the hook | T + 2 along the hook (E) |
| BoxS / BoxL / BoxC | B2, B3 | 140 × 80 × 125 / 190 × 76 × 140 / 190 × 89 × 165 | + 10 |
| Retail | B8 (non-hanging) | per item | + 10 |
| Deck | B7, E4, `Retail_DeckBoxPack` | ≤ 82 × 86 × 116 | 92 × 96 |
| Storage | E1, E2 | per size | + 10 |
| Binder | E3 Closed, `Retail_BinderWrapped` | 250 × (spine) × 295, standing | spine + 2 |
| Carton / BoxShip | B4, B5 | per size | + 20 |

**Socket kinds:**

| Kind | Names | Rule |
|---|---|---|
| DISPLAY, grid | `Level_<Lvl>` (one origin per level, at the level's floor centre), `Compartment_<Lvl>_NN` (2-4 per level, at compartment centres), `PriceTag_<Lvl>_NN` (one per compartment) | The per-class grids (cols, rows, pitch, first-slot offset) live in `.csk.json` and `DT_CSK_Slots`. `BPFL_CSK_Slots::CSK_GetSlotTransform(Fixture, Level, Class, Index)` expands them at runtime or in the editor. The hull test applies |
| DISPLAY, fixed | `Slot_NN` / `Slot_R<r>_NN` / `Item` | Only where the count is fixed: card tables 8/10/12, easels, risers, card stands, the wall slab case. The hull test applies |
| CONTAIN | `Card`, `Pack_NN`, `Box_NN`, `Slab_NN`, `Row_NN`, `Pocket_*`, `Contents`, `Cards_Start`, `Hang_Start`, `Nose` | Attached items are NoCollision and must not simulate physics (README). They are exempt from the hull test; the fit test (render bounds) still applies |
| UTILITY | `Seat`, `Grip`, `Face`, `Stack`, `Mount*`, `Snap_L/R`, `Groove_NN`, hinge sockets (`Lid`, `Door*`, `Tray`, `Cover`, `Plate`, `Half`), `Label`, `Text`, `Screen`, `Light`, `LED` | Hinge sockets sit on the part's pivot axis |

**Seating and authoring:**
- Every slot uses the item-`Seat` frame: origin at the slot's floor centre, +X to the viewer's right, +Y away from the
  customer, +Z up. Leaning slots (easels, risers, wall slab case) are pitched in the socket's rotation.
- Seating (HOUSE, armory §8): item world = slot transform × inverse(item `Seat`). `AllowMirror` is false.
- The **fit test is zero-tolerance on render bounds**. Each item's render AABB, in the slot frame, must lie inside the slot's
  clear volume and must not overlap its neighbours at the grid pitch. The seat error must be ≤ 1 mm.
- Socket names contain no dots or spaces (HOUSE, `make_socket`). Sockets are made with `helpers.make_socket` (it applies the
  180° Y correction) and exported only through `export_fbx`, which writes `.sockets.json` (HOUSE; never hand-written).

**Kit data file (`<name>.csk.json`).** `export_fbx.write_socket_sidecar` writes only `fbx`, `axis`, `note`, `sockets` and
`lod_screen_sizes`, and any unknown keyword raises `ValueError` (`export_fbx.py` lines 84, 280, 395). So the kit data does
**not** go in the pipeline sidecar. `csk_lib/slots.py` writes a separate `<name>.csk.json` next to the FBX after export,
recording the SHA-256 of the FBX and of the `.sockets.json` it belongs to. `qa_csk` fails on a hash mismatch. The pipeline
stays unedited.
```json
{
  "fbx": "SM_CSK_Showcase_Full_1778.fbx", "fbx_sha256": "…", "sockets_sha256": "…",
  "class": null, "pose": "upright", "pivot": "bottom-centre", "accepts": ["Card", "CardProt", "Slab", "Pack", "BoxS", "Deck", "Retail"],
  "levels": [{"socket": "Level_S1", "interior_mm": [1740, 356], "clear_h_mm": 180, "compartments": 4,
              "grids": [{"class": "Slab", "cols": 18, "rows": 2, "pitch_mm": [94, 144], "first_mm": [-799, -72]},
                        {"class": "Card", "cols": 22, "rows": 3, "pitch_mm": [77, 102], "first_mm": [-808.5, -102]}]}],
  "parts": {"Door_L": {"mesh": "SM_CSK_Showcase_Full_Door_1778", "type": "slide", "axis": "X", "range_mm": [0, 839]}},
  "glass": "SM_CSK_Showcase_Full_Glass_1778",
  "ip_review": "2026-..-.. pass"
}
```
The numbers in this example are E, except the D grid counts and travel (L/2 − 50 = 839). An item file carries `class`,
`footprint_mm`, `stack` (`socket`, `pitch_mm`, `max`), `states` and `contain` grids instead of `levels`.
`csk_make_datatable.py` turns all the files into `DT_CSK_Items` and `DT_CSK_Slots` in Unreal (5.4).

### 4.3 Stacking rules (E)

| Class | Stacks on | Pitch | Max per slot |
|---|---|---|---|
| Pack (lying) | Pack only | 4 | min(10, floor((clear_h − 5)/4)) |
| BoxS / L / C | same class | 125 / 140 / 165 standing, or 80 / 76 / 89 lying | floor((clear_h − 10)/pitch), at most 4 |
| Slab | Slab (ridges nest in the front recess) | 7.0 (8.0 thick); T includes the ridges (3.D) | 10 |
| CardProt | same item | its T | 20 |
| Card | beyond 5 cards, switch to `CardStack_*` (a performance rule) | 0.3 raw, 0.5 penny-sleeved | 5 |
| Retail | same item | its H | 4 |
| Storage row boxes | same size | 76.2 (D: = the box H, M [D16]) | 5 |
| Carton, BoxShip | same size | its H | 4 on the floor or the hand truck; per rack level by clear height |

- Mixed-class stacking is not supported.
- Each stackable item has a `Stack` socket (top centre) equal to the next item's `Seat`.
- The stack test builds every stack to max in every accepting slot and checks it with the render-bounds fit test (4.2).

### 4.4 Price-tag system

- **Tags:** 3 meshes (I2). Shelves and cases expose one `PriceTag_<Lvl>_NN` per compartment; card tables expose one per slot.
- **Digits:** `MF_CSK_Digits` (a CSK-root function, built with the `MF_LetteringBand` technique, not referencing it) renders
  the `Price` value (a scalar param, or per-instance CD4) from the glyph strip in `T_CSK_Labels`. It shows up to 5 digits
  + a decimal point + `Currency Glyph` (none, $, €, £, ¥), masked to a rect.
- **Fallback:** a `Text` socket on each tag for a TextRender or widget component.
- **No barcode** that scans: a decorative line pattern only (6.2).

### 4.5 Glass, clear plastics and draw calls

| MI | Used on | Look (E) |
|---|---|---|
| `MI_CSK_Glass_Tempered` | Case `_Glass` meshes and glass doors/lids (6.35, M [D24]) | Clear, faint green edge via fresnel, roughness 0.02 |
| `MI_CSK_Acrylic` | Slab window, easels, stands | Clear, no tint, roughness 0.03 |
| `MI_CSK_PVC` | Top-loader, semi-rigid | Faint blue haze, roughness 0.08 |
| `MI_CSK_Film` | Penny sleeve, sleeve fronts, blister, retail bags | Low opacity, roughness 0.15 |
| `MI_CSK_Glass_Cheap` (opaque) | The LOD2 of **case glass only** | A dark reflective opaque stand-in |

- Master `M_CSK_Glass_Master`: Translucent, Surface ForwardShading, with params `Tint`, `Edge Tint`, `Opacity`,
  `Roughness`, `Specular`, `Fresnel Power`. A **Thin Translucent** shading-model variant is tried for slab and holder windows
  at G1 and kept if it is cheaper and sorts better.
- **Sections:** a card is 1 section. An empty slab is 2 (opaque body + translucent window). Every `_Filled` variant is 1
  opaque section with Clear Coat, so there is no translucency at all.
- **Holder and slab LODs:** LOD1 keeps a single front skin (no back skin); LOD2 has no skin and shows the opaque card, label
  and frame. Distant slab walls never show blank rectangles.
- **Sort priority:** case glass is **+1 over** slab and holder windows, so glass in front draws after the items behind it,
  seen from the customer side (E, from sort-priority semantics). Instances inside one HISM are not depth-sorted against each
  other. So bulk dressing uses `_Filled` (opaque) in HISM, and translucent shells stay socket-attached components; this is a G1
  check.
- **Draw calls (D):**
  - 200 socket-attached empty slabs with cards = 200 × (2 + 1) = 600 draws, 200 of them translucent.
  - 200 `_Filled` slabs in one HISM = about 1 draw per LOD.
- **Glass meshes:** `_Glass` meshes let buyers put glass on its own trace channel, so clicks reach the items inside. They also
  leave the case bodies fully opaque, so the bodies are Nanite-eligible.
- Substrate off (as the validation project, HOUSE).

### 4.6 LODs, collision, performance

**LOD screen sizes.** The kit rule (E) is S = 1.778 R / d, the repo formula from `ITEM_INVENTORY.md` (16:9, 90° HFOV):

| Class | Bounds R | LOD1 at | LOD2 at | Why not the pack rule |
|---|---|---|---|---|
| Handheld (cards, holders, slabs, packs, dice) | < 100 mm | 1.5 m | 4 m | The pack rule switches at 0.89 m; shop sims hold cards at arm's length and scan shelves from 1-2 m (E) |
| Medium (boxes, POS, easels) | 100-500 | 4 m | 10 m | The pack rule's switch distance does not grow with size |
| Fixtures and shell | > 500 | 8 m | 20 m | The pack rule is invalid above R = 500 (D, pipeline gap 5) |

- The sizes are written with `export_fbx(..., lod_screen_sizes=[...])` and re-applied by `ue_import_sockets.py` (HOUSE).
- Triangles must strictly descend (HOUSE). Meshes of **150 triangles or fewer** ship LOD0 only (marked "LOD0 only" in section 3),
  and the listing's LOD statement says so.
- LODs are built from the parts, not blind-decimated, where a silhouette matters (HOUSE).

**Collision:**
- Every mesh has UCX hulls (`helpers.make_ucx_hull`, closed and convex). Cases get one hull per panel (on the body and the
  `_Glass` mesh), so items can sit inside.
- **Handheld items get a box hull at least 2 mm thick (E), centred on the item.** The card (0.3), sleeves (0.5) and the
  semi-rigid (1.0) are padded to 2 mm, because Chaos drops small thin bodies through floors even with CCD (M [U1]).
- The README recommends a preset: CCD on for thrown stock, query-only for cards on display, and NoCollision for anything
  attached to a CONTAIN socket.

**Nanite.** Off by default (E). The opaque bodies are Nanite-eligible now that glass is split out, and the README says how to
turn it on.

**Instancing.**
- All masters have Used With Instanced Static Meshes (HOUSE setting).
- Per-instance custom data layout (E):

  | CD | Meaning |
  |---|---|
  | CD0 | Art Index (also the array slice) |
  | CD1 | Back / Alt Index |
  | CD2 | Tier 0-3 |
  | CD3 | Foil 0-1 |
  | CD4 | Grade or Price |
  | CD5 | Label / grader index |
  | CD6 | Wear 0-1 (drives corner wear, edge whitening and scratch) |
  | CD7, CD8 | Centering X, Y |
  | CD9 | Crease (0 = none, else a seed) |

- A static switch `Use Per-Instance Data` is on for ISM/HISM and off for socket-attached components, which use MI params.

**Performance target (E).** An internal stress level (3,000 packs, 1,000 cards, 200 slabs in cases, with both the attached
and the HISM `_Filled` paths) runs at ≥ 60 FPS at 1440p High on the user's PC. It is measured at G1 and G4 and is not shipped.

---

## 5. Unreal deliverables

### 5.1 Master materials (`/Game/CardShopKit/Materials`, built by code under the materials lock, D5)

| Master | Used for | Key params (group-numbered, each with a buyer tooltip, HOUSE convention) |
|---|---|---|
| `M_CSK_Print_Master` | Cards, packs, boxes, labels, playmats, posters, signs, `_Filled` holders and slabs | `Use Atlas`, `Atlas Grid`, `Cell Rect`, `Art Index`, `Back Index`, `Label Index`, `Front Texture`, `Back Texture`, `Label Texture`, `Use Texture Array`, `Art Array`, `Edge Colour`, `Tier 0..3 Colour`, `Tier`, `Foil Amount`, `Foil Colour Shift`, `Shrink Film`, `Clear Coat Window`, `Use Per-Instance Data`, `Grade` (digits MF), `Price` + `Currency Glyph`, `Centering Offset`, `Corner Wear`, `Edge Whitening`, `Surface Scratch`, `Crease`, `Roughness Adjust`, `Use Flat Colour` |
| `M_CSK_Surface_Master` | Fixtures, cardboard, metal, plastic, wood, felt, resin, shell | `Colour`, `Lightest Colour` (the Fabric-master tint model, HOUSE), `Roughness Adjust`, `Metal From ORM`, `Tile Scale` (UV2, per metre), `Surface Set` textures (tileable 1K/2K: melamine, anodised aluminium, powder-coat, chrome, ABS, corrugated, white board, kraft, MDF slat, wood, felt, rubber, resin, plaster, vinyl floor), per-mesh `ORM` (UV1), `Use Flat Colour` |
| `M_CSK_Glass_Master` | 4.5 | 4.5, plus a Thin Translucent variant after G1 |
| `M_CSK_GlassCheap_Master` | LOD2 of case glass | `Tint`, `Roughness` |
| `M_CSK_Emissive_Master` | LED strips, lamps, screens, lightbox signs | `Emissive Colour`, `Intensity`, `Use Atlas`, `Art Index`, `Screen Texture` (accepts a render target) |

- MIs follow the `MI_CSK_<Part>_Base` → `MI_CSK_<Part>` chain (HOUSE): the base holds the textures, the leaf holds colours.
- About 60 leaf MIs (E). `MATERIALS_README.md` lists every recolour param with hex defaults.
- The kit spec file (`Scripts/cardshop/unreal/csk_material_spec.json`) goes through the preflight like any other spec entry.

### 5.2 Maps

| Map | Content |
|---|---|
| `L_CSK_Shop` | A furnished shop from the J1 shell, 14 × 8 × 3 m (E): sales floor 10 × 8 (showcases, gondolas, slatwall, box tier, wall slab case, counter + POS, 2 play tables, ceiling lights, entry door) and back room 4 × 8 (warehouse racks, workbench, trash, cartons, hand truck). Every case and shelf is **filled** by `BP_CSK_SlotFiller`. Lumen only, with World Settings **Force No Precomputed Lighting** on, so there is no unbuilt-lighting warning (FAB_ASSET_STUDY line 345) |
| `L_CSK_Overview` | Every mesh on a labelled grid, plus an empty-vs-filled pair of each case, a socket-visualiser toggle and the original `SM_CSK_ScaleFigure` for scale. Everything referenced is inside `Content/CardShopKit/` (FAB_ASSET_STUDY lines 191 and 308) |
| `L_CSK_Stress` | The internal performance scene for 4.6. It stays in the repo, not in the Fab package |

### 5.3 Light Blueprints and tools (optional, no gameplay)

| Asset | Does |
|---|---|
| `BP_CSK_HingedPart` | Rotates a child mesh about its own pivot (already on the hinge axis) between the `range_deg` values; an `Open` float 0-1 is exposed. Optional: a buyer's own Timeline works the same |
| `BP_CSK_SlidingPart` | The same, for sliding doors and the cash-drawer tray (translation) |
| `BP_CSK_StateSwap` | Swaps Sealed → Open → Wrapper / Closed → Open → Flat meshes (packs, cartons, ship boxes, playmat) and spawns the tear strip |
| `BP_CSK_SlotFiller` | Editor/construction-time helper: fills a fixture's grids with chosen items as HISM (`_Filled` for holders and slabs), using the CD layout (4.6). Dressing only |
| `BP_CSK_OpenSign` | Flips the plate 180° |
| `BP_CSK_Holder` | Attaches a card (or card index) to a holder's `Card` socket |
| `BPFL_CSK_Slots` | Blueprint function library: `CSK_GetSlotTransform(Fixture, Level, Class, Index)`, `CSK_GetSlotCount(...)`, reading `DT_CSK_Slots` |
| `EUW_CSK_Tools` + `csk_import_sockets.py`, `csk_make_card_array.py` | Editor Utility Widget for FBX-route users: re-applies sockets from `.sockets.json` (a renamed copy of `ue_import_sockets.py`, so sockets do not arrive at scale 100), builds a card Texture2DArray. Where the Python files live in the package is risk R13 |

### 5.4 Data

`DT_CSK_Items` (mesh, class, footprint, stack pitch/max, sockets) and `DT_CSK_Slots` (fixture, level, class, grid) are filled
from the `.csk.json` files by `csk_make_datatable.py`. Their row structs `S_CSK_Item` and `S_CSK_Slot` are **authored in the
editor on the PC** (or through Unreal MCP), because adding members to a UserDefinedStruct is not exposed to UE Python and an
asset pack cannot ship C++ (R7). Only the JSON fill is scripted.

### 5.5 Explicitly NOT included

Economy, prices and pricing AI; customers and NPC AI or animation; ordering, stock or inventory; pack RNG or card rarity
logic; a card database or card stats; grading logic; register or payment logic; UI; save; multiplayer; real brands,
cards or graders. The listing says this in its first paragraph.

---

## 6. IP rules for this product

### 6.1 Do

| # | Rule |
|---|---|
| 1 | Invent every brand, grader, card line and set. The user screens each name in USPTO search and logs it with the date in `WorkFiles/cardshop/BRAND_NAMES.md` before any art is drawn |
| 2 | Design our own slab: the chamfered frame, gasket, ridges and label proportions (3.D). Our own label layout, wordmark, grade wording and colours; a **decorative, non-functional** barcode/cert pattern. The empty shell passes the blind test on its own |
| 3 | Make every card face, back, label and pack face a swappable cell **and** a plain-texture slot, and ship blank templates and `csk_pack_cards.py`, so buyers use their own game's art |
| 4 | Use generic names in files, listings and tags: "graded card slab", "top-loader" (pending the screen in 6.3), "booster pack", "magnetic card holder", "semi-rigid holder", "deck sleeve", "collector box" |
| 5 | Use only fonts we may embed in textures (OFL or similar). Log each font and its licence in `WorkFiles/cardshop/FONTS.md` |
| 6 | Make the sports-style line a **fictional sport** with fictional teams: no leagues, team names, logos, real athletes or likenesses |
| 7 | Keep a per-product AI decision log (FAB_ASSET_STUDY line 314). With D4 = a, nothing is AI-generated |
| 8 | Keep tier names and colours as buyer-editable parameters, with our own defaults (4.1) |
| 9 | Design every POS item (terminal, printer, price gun, scanner, phone, laptop) as an original shape; only sizes come from research |

### 6.2 Don't

| # | Rule |
|---|---|
| 1 | No real names, logos or wordmarks in meshes, textures, file names, listing text or tags: Pokemon, Magic: The Gathering, Yu-Gi-Oh, Lorcana, One Piece, Topps, Panini, Upper Deck, PSA, BGS/Beckett, CGC, SGC, TAG, Ultra PRO, BCW, Dragon Shield, KMC, Ultimate Guard [M4][M5] |
| 2 | No trademarked product names used as generic terms: ONE-TOUCH (Ultra PRO, Reg. 3289899 [T1]), Card Saver (Cardboard Gold, Reg. 6309079 [T2]), Deck Protector (Ultra PRO filing, status unconfirmed [T3]), "Elite Trainer Box" (a Pokémon product name [T4]). The registration numbers are from search results only; the user confirms them on USPTO |
| 3 | No competitor game titles in the listing, tags or file names (TCG Card Shop Simulator, Sports Card Shop Simulator, Card Shop Simulator Multiplayer, Tetramon). Say "card-shop sim" instead |
| 4 | No grader trade dress: no white label with a red frame and a big grade block on the right; no subgrade table; no hologram sticker copy; no grader wording such as "GEM MT"; no combination that reads as one grader even without its name [M7] |
| 5 | No famous card backs (red-and-white ball, brown-blue five-pip swirl, brown vortex). No famous frame layout (name bar + cost pips top-right + art box + type line + text box + P/T box). No set-symbol placement or rarity symbols copied [M5][M6] |
| 6 | No brand-evoking colour **plus** layout **plus** logo-shape combinations on packs, for example yellow lettering with a blue outline over a creature panel (E judgement) |
| 7 | No mascot-like creatures or ball-shaped tins that echo franchises (the sphere tin is replaced by an original hex tin, 3.11) |
| 8 | Nothing usable for counterfeits: no scannable barcodes or QR codes, no real-format cert numbers, no hologram replica. Labels are drawn at 4 px/mm, **half** the 8 px/mm (about 203 dpi, D) of common thermal label printers, so they are not print-ready at 1:1 [M7] |
| 9 | No real currency design on money props; no real payment-brand shapes or logos on the terminal; no copied silhouette of a specific terminal, printer or labeller |
| 10 | Nothing "PSA-style" or "Pokemon-style" in text anywhere, including tags |

### 6.3 IP gates (part of G2 and G5)

1. **Deny scan** (`qa_csk.py`, rules in `csk_lib/spec.py`; `qa_check.py` is not edited):
   - It runs on every object, material, texture and socket name, on the strings table the atlas art is drawn from, and on the
     listing text.
   - `CSK_DENY_TERMS` holds long terms matched as substrings: franchise names, brands, game titles, trademarked product names
     and grader wording.
   - `CSK_DENY_WORDS` holds short terms (TAG, PSA, BGS, CGC, SGC, KMC, BCW) matched as **whole tokens**, split on
     non-alphanumerics and `_` but not on CamelCase. So `PriceTag`, "Vintage", "Stage" and "tags" pass, the same way
     `qa_check` treats "ea".
   - An allow-list removes "price tag" and "hang tag" before matching.
2. **Barcode decode test:** pyzbar/zxing run on every Labels/Boxes/Cards texture at 1×, 2× and 4×, **under system Python**
   (they need native libraries Blender's Python lacks). Pass = nothing decodes.
3. **Blind brand test:** a judge (a fresh subagent plus the user) sees each pack, box, card back, slab label **and the empty
   slab shell** next to nothing but the question "which real brand is this?". Pass = no confident match. This is the
   CLAUDE.md blind-test rule turned around.
4. **Trademark screen (manual, the user):** the 8 names, plus "top-loader"/"toploader". No registration was found for
   "toploader" in the research, but it has not been screened. If it is registered, rename to `RigidHolder`.

---

## 7. Build plan

### 7.1 Phases (effort is E; one session ≈ one Claude working session)

| Phase | Work | Sessions | Gate at the end |
|---|---|---|---|
| P0 | User decisions (section 2); brand shortlist and the USPTO query list (the user screens); claim the `CardShopKit` lock; create `CardShopKit.uproject`; the `NP_PROJECT` edit to `run_build.sh` and the kit spec file, under `np_lock`; the row structs authored on the PC | 1 | **G0** decisions signed |
| P1 | **Standards spike**, end to end: `Card_Std`, `TopLoader_35pt`, `Slab_Std` + `_Filled`, `Pack_Std_*`, `Box_Booster_S`, `Showcase_Full_1778` + `_Glass` + a placeholder atlas + first masters + `BPFL_CSK_Slots` + `csk_pack_cards.py`. Export, fresh-process Unreal import, sidecar sockets, the `.csk.json` hashes, the seat test and the stress test | 4 | **G1 — stop and show the user if any of these fail:** (1) buyer art: a plain one-texture material and a `csk_pack_cards.py` atlas both show correctly on card, pack and slab label; (2) sockets: `CSK_GetSlotTransform` seats 3 classes at ≤ 1 mm with ≤ 40 sockets on the showcase; (3) draws: 200 slabs in the glass case, attached and HISM `_Filled`, sort correctly from the customer side, with the HISM translucent-stack check, the Thin Translucent trial and ≥ 60 FPS. Also: LODs and hulls correct in UE, readability at 1.25× scale, a Texture2DArray made from Python |
| P2 | Brand art: the 7 atlases, fonts, blank templates, the wear mask, the IP gates | 5 | **G2**: IP gates pass; the user approves the art sheet |
| P3 | Groups B, C, D, E (small items and retail; parallel families possible) | 7 | **G3** per family |
| P4 | Group A, F (fixtures, tables) | 6 | G3 per family |
| P5 | Groups G, H, I, J | 4 | G3 per family |
| P6 | Final masters + about 60 MIs, texture import, DataTables, BPs, BPFL, Editor Utility | 5 | **G4**: full-kit import in a fresh process; no `/Game/NinjaPack` references (Reference Viewer / asset audit); the BPs and tools work |
| P7 | Demo and overview maps, dressing, video | 2 | G4 re-run in the maps |
| P8 | Media at 3840 × 2160, README / MATERIALS_README, listing text, Fab package | 2 | **G5**: the Fab checklist (8.4) passes |
| | **Total** | **36** + about 6 PC days | |

**Workflow parallelism:**
- After G1, P3-P5 fan out: one agent per family, each holding its own asset lock (`CSK_<Family>`, via
  `Scripts/pipeline/lock.py`).
- Lock files live in `WorkFiles/locks/` (or `PIPELINE_LOCK_DIR`) on one filesystem, so **the fan-out runs inside one VM or
  on the PC**, never across separate cloud VMs.
- Each family has its own `.blend` and export folder. `.blend` files are LFS binaries and cannot be merged, so families
  merge serially.
- One Unreal commandlet at a time on the PC (HOUSE), so the Unreal checks run in one serial queue.

### 7.2 Script modules (planned)

| Path | Role |
|---|---|
| `Scripts/cardshop/build_csk.py` | Entry point: `blender -b --factory-startup --python build_csk.py -- --family <F> --variant <V> --out Exports/CardShopKit/<Group>/` |
| `Scripts/cardshop/csk_lib/spec.py` | Every dimension in section 3 with its flag and source key; classes, pitches, the pack → box map, budgets, the LOD class table, `CSK_DENY_TERMS`, `CSK_DENY_WORDS`, the allow-list |
| `csk_lib/geom_{cards,holders,slab,packs,boxes,retail,storage,binder,showcase,shelving,tables,pos,backroom,signs,shell,lights}.py` | Parametric geometry, one module per family group; bevel + weighted normals (HOUSE hard-surface method) |
| `csk_lib/slots.py` | Slot-grid solver, socket authoring, stacking, and the `.csk.json` writer (after `export_fbx`, with hashes) |
| `csk_lib/atlas_layout.py`, `art_{cards,packs,boxes,labels,playmats,signs}.py`, `fonts.py` | Atlas cell math (following `props_lib/atlas.py`) and script-drawn original art |
| `csk_lib/lods.py`, `collision.py`, `uv.py` | LODs from parts, UCX hulls (2 mm handheld minimum), UV0 tiles + UV1 unique + UV2 tiling |
| `csk_lib/qa_csk.py` | Fit (render bounds, zero tolerance), stack and hull tests (DISPLAY only); `.csk.json` hash check; print px/mm and non-print texel; UV2 scale; deny scan; triangle and LOD checks per class |
| `Scripts/cardshop/barcode_test.py` | The decode test, run under system Python |
| `Scripts/cardshop/test_csk.py` | Self-tests, including negative cases (a slot that is too small, a pack that overhangs a box by 0.1 mm, a deny hit, a false deny on `PriceTag`, a decodable barcode, a stale `.csk.json` hash) |
| `Scripts/cardshop/tools/csk_pack_cards.py` | Buyer tool, standalone Python 3 + Pillow (4.1) |
| `Scripts/cardshop/unreal/csk_import.py`, `csk_make_datatable.py`, `csk_demo_map.py`, `csk_stress.py`, `csk_make_card_array.py`, `csk_import_sockets.py` | Import with the house settings + socket re-apply, DataTables, maps, the Texture2DArray tool, the buyer socket tool (kept byte-identical to `ue_import_sockets.py` apart from the name, checked by a hash test) |
| `Scripts/unreal/materials/run_build.sh` (`NP_PROJECT`), `Scripts/cardshop/unreal/csk_material_spec.json` | The kit masters (D5), under `np_lock` |

### 7.3 QA per mesh (gate G3)

1. `qa_check` with `--budget <class tris>`, `--require-uv1`, UCX present, transforms applied, Non-Color data maps (HOUSE).
   `--texel 10.24` only on meshes without print.
2. `qa_csk`:
   - every item seats into every accepting slot class (≤ 1 mm), and its render bounds fit with zero tolerance;
   - the hull test on DISPLAY sockets only;
   - stacks to max;
   - the pack → box map;
   - the print px/mm is exact and UV2 is at metre scale;
   - the `.csk.json` hashes match the exported bytes;
   - the deny scan passes, and the barcode test passes (system Python).
3. LOD triangles strictly descend (or LOD0 only at ≤ 150 tris); the screen sizes match the class table.
4. Export via `export_fbx` only; record SHA-256 of the FBX, `.sockets.json` and `.csk.json`.
5. On the PC, a second fresh Unreal process imports the exact bytes: sockets present, hull count, LOD count and screen
   sizes, material slots and section counts (HOUSE).
6. Per-group `README.md` rows: size, tris, LODs, sockets, collision, markings/IP statement, check counts.

### 7.4 Showcase shots (rendered in UE from `L_CSK_Shop` / `L_CSK_Overview`)

Listed in 8.3.

---

## 8. Fab listing plan

### 8.1 Text

| Field | Value |
|---|---|
| Title | **Collectibles & Card Shop Kit** (28 characters, D; the ≤ 30 rule is from FAB_ASSET_STUDY line 341) |
| Category | 3D model → Props (E; confirm in the uploader, not measured) |
| Style tags | Realistic, PBR (one style only, [M1]) |
| Tags | card shop, trading card, collectibles, shop simulator, store, retail, display case, showcase, graded card slab, booster pack, top loader (after the screen, 6.3), binder, shelves, interior, game ready, modular, low poly friendly (E; fill every slot, FAB_ASSET_STUDY line 341) |
| Price | $29.99 Personal / $59.99 Professional (E, between the stylized-prop and modular-kit bands [M1]; Fab prices end in .99 on a $1 grid, M [M2]) |
| First paragraph | What it is, "no game logic", "original fictional brands only", **69 items / 171 meshes**, the formats, the LOD and collision statement (Fab wants it even when zero, HOUSE) |
| Exchange-format note | "The FBX/GLB files and the 3D preview show each mesh's default art. The atlas index, per-instance data, card-condition and texture-array features work in the Unreal project. Sockets for FBX users: run the included `csk_import_sockets.py`." |
| Technical fields | Mesh count 171; LODs 3 per mesh (LOD0 only on meshes ≤ 150 tris); UCX on every mesh; sockets from sidecars; texture sizes (4K BaseColor atlases, 2K and below otherwise); Nanite off (opaque bodies eligible); Lumen demo map |

### 8.2 Minimum-count check

Realistic packs need ≥ 1 asset (5 recommended); stylized packs need about 25 [M3, unverified in the study]. v1 has 171
meshes (lean option about 115). **Pass.**

### 8.3 Gallery (3840 × 2160 JPEG, < 3 MB each, < 25 MB total, 16:9 thumbnail, no UE logos: FAB_ASSET_STUDY lines 335, 341, 467)

**10 images at ≤ 2.3 MB each** (D: 25/10 = 2.5, with margin), so the set stays under 25 MB.

| # | Shot |
|---|---|
| 1 | Thumbnail: the lit shop from the counter, the slab wall case and a showcase in front. It is framed so **no legible text or logo** shows (the storefront lightbox is out of frame; the labels are too small to read) |
| 2 | Grid overview of all 171 meshes (the house pack-overview rule) |
| 3 | Slabs and protection: empty and filled slabs, thick, the two fictional graders, grades; penny sleeve, deck sleeve, top-loaders, semi-rigid, magnetic holder (open/closed) |
| 4 | Sealed and retail: pack states × our 4 tiers, S/L/collector boxes, carton states, the blister and 8 retail items on slatwall hooks |
| 5 | Empty vs filled: the same showcase in a split frame, with the level sockets and slot grids drawn |
| 6 | Recolour and condition sheet: one fixture in 6 MIs, one card mint → worn (centering, corners, edges, crease) |
| 7 | Play area + counter/POS close-up (drawer open, screens lit) |
| 8 | Stocking loop: hand truck with cartons, open carton, ship boxes with contents, flat boxes at the trash |
| 9 | Art proof + buyer path: the atlas sheets (original art) beside a card using a buyer PNG through the plain-texture path |
| 10 | Tech sheet: LOD0-2 + UCX + tri counts for 6 hero items, and the original scale figure |
| Video | 60-90 s: a flythrough + door, drawer, lid and pack-open state swaps (1920 × 1080 MP4, ≤ 300 MB) |

### 8.4 Fab checklist (gate G5)

| # | Check | Source |
|---|---|---|
| 1 | Only `Content/CardShopKit/`; no `/Engine/`, Starter Content or `/Game/NinjaPack` references; no Epic sample content in the package | FAB_ASSET_STUDY lines 188, 308 |
| 2 | Migrate `Content/CardShopKit` alone into a blank 5.8 project, delete `Config/`, reopen both maps | line 191 |
| 3 | Force No Precomputed Lighting on every shipped map; no unbuilt-lighting warning | line 345 |
| 4 | 16:9 thumbnail with no text or logos; 10 images < 3 MB each and < 25 MB in total | lines 335, 341, 467 |
| 5 | Title ≤ 30 characters; every tag slot and technical field filled; LOD, collision and exchange-format statements | line 341, HOUSE |
| 6 | The deny scan passes on the listing text and tags (no competitor game titles, no trademarked terms) | 6.3 |
| 7 | One upload draft tests the Python-tools packaging (R13) and the exchange texture auto-mapping (D7) | E |

---

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **Card art quality** is what reviewers judge [G6][G7]; script-made art can look cheap, and 5 px/mm is soft in a full-screen reveal | The buyer-art paths, a plain-texture hero path, the user approves the art sheet at G2; our art is demo quality and the listing says so |
| R2 | **Translucency cost and sorting** with hundreds of slabs and sleeves inside glass cases | Opaque slab bodies, one translucent section, opaque `_Filled` for bulk, skins dropped at LOD1/LOD2, glass +1 sort priority, Thin Translucent trial; all checked at G1 (stop rule) |
| R3 | **Per-instance data works only on ISM/HISM**; runtime socket attachment makes plain components | Both paths in the master (static switch); `BP_CSK_SlotFiller` uses HISM; documented |
| R4 | **Weak or conflicting sizes** (slab thickness, blister, tuck box, retail items, price-gun body, play-table depth, the E\* fixture values) | Box and pack sizes are now our own and fit by design (3.B map); the rest is flagged E/E\*; measure any real items the user owns before P3 |
| R5 | **IP / trade dress** on labels, packs and the slab shell; name collisions | Section 6 gates; USPTO log; blind test including the empty shell |
| R6 | **Scope:** 171 meshes | Parametric families, workflow fan-out after G1, the lean option in 3.11, the G1 stop rule |
| R7 | **Blueprint graphs and structs by script** are limited in UE Python (timelines, event graphs, UserDefinedStruct members) | Keep the BPs minimal; author the structs and any graphs on the PC or through Unreal MCP |
| R8 | **All FBX users** (Unreal and other engines) get sockets at scale 100, or not at all, without tooling | Ship `csk_import_sockets.py` + `EUW_CSK_Tools`; the README documents `.sockets.json` and `.csk.json`; GLB with sockets as nodes in v1.1 |
| R9 | **Materials-lock contention** with ninja-pack sessions; the `run_build.sh` edit touches shared code | A short claim window per build; the `NP_PROJECT` edit is one env override with a default that keeps today's behaviour; kit masters sit under their own root |
| R10 | A dedicated competitor appears, or the Fab TCG template adds its own art | Ship v1 first with the core; v1.1 free updates keep the listing fresh |
| R11 | **Price sensitivity** (GENRE_SCAN) | $29.99 with launch-sale headroom; the lean option could list at $24.99 |
| R12 | **Card z-fighting** (0.3 mm cards in 0.89 mm gaps) at distance | A minimum 0.2 mm gap per side in the fit test; `_Filled` variants; LOD1 card = chamfered box |
| R13 | **Python tools inside the package:** Fab accepts only `Content/<Pack>`, and `.py` files there may be flagged or ignored | Test on one upload draft; fallback: the tools ship in the FBX zip's `Tools/` and the README, and `EUW_CSK_Tools` points to them |
| R14 | **The empty slab shell's proportions** (84 × 134 with a top label band) sit close to the leading grader's | Blind test on the shell alone at G2; change the label band if it fails |
| R15 | **Texture2DArray creation from UE Python** is unverified | G1 check; fallback: document the editor's "Create Texture Array" action |
| R16 | **Locks across machines:** file locks do not cross VMs | Fan out inside one VM or on the PC (7.1) |

---

## 10. Open questions for the user

1. D1-D9 (section 2): the style, the v1 scope, who names the brands, the art method, the material home, GLB, texture names,
   the validation project, the publisher name.
2. Do you own any real slabs, top-loaders, magnetic holders, packs or booster boxes to measure? (That settles the E\* values
   in R4.)
3. Is $29.99 / $59.99 right, or do you want $24.99 for the launch?
4. Will you run the USPTO screens for the 8 names and "toploader" (Claude prepares the query list), and confirm the four
   trademark registrations in 6.2 rule 2?

---

## 11. Sources (keys used above)

All web sources are search-result snippets relayed by the research and review agents on 2026-09-28; **not measured here**
and not opened in full.

| Key | Source |
|---|---|
| D1 | cardfitlab.com/guides/japanese-size-sleeves-vs-standard; safelysleeved.com/guides/card-sleeve-sizes |
| D2 | wargamer.com/pokemon-card-size |
| D3 | bcwsupplies.com/card-sleeves; thecardshopfinder.com/guides/card-supplies/penny-sleeves-vs-perfect-fit/ |
| D4 | bcwsupplies.com/3x4-topload-card-holder; ultrapro.com (3x4 regular toploaders); cardfitlab.com/guides/what-does-35pt-mean |
| D5 | cardboardgold.com/card-saver-1.html; acecards.com (Card Saver 1) |
| D6 | bcwsupplies.com/magnetic-card-holder-35-pt |
| D7 | wetopacrylic.com/guide/psa-slab-dimensions/; slabguardtcg.com (two posts); pregradecards.com slab-quality comparison; accio.com card-slab-dimensions |
| D9 | pokecompare.com/blog/pokemon-booster-box-dimensions-weight; elitefourum.com booster-pack dimensions |
| D11 | lunafabrication.com (6-box display); steelcitycollectibles.com (acrylic 6-box case). No longer used for sizes (the carton is D from our box) |
| D12 | aliexpress.com wiki; evoretro.ca (collector-box dimensions), weak. No longer used (B3 is E) |
| D13 | ebay.com/itm/157205386785 |
| D16 | bcwsupplies.com 100/400/800/3200/5000 storage box pages |
| D17 | bcwsupplies.com/vinyl-9-pocket-page; printmag.com/design-resources/binder-sizes/ |
| D18 | decksmith.shop/en/blog/deck-box-dimensions-guide |
| D19 | playmatspro.com standard TCG playmat; answers.custommousepad.com |
| D20 | dicegamedepot.com 16 mm dice; litko.net Chessex 16 mm d6 |
| D21 | amazon.com BCW card sorting tray B0F4LCRF13 (the tray is now v1.1) |
| D22 | storefixtureshowcase.com/products/display-case; shoppopdisplays.com (70 × 20 × 38); kc-store-fixtures.com full-vision 70 |
| D23 | kc-store-fixtures.com half-vision 70 with light |
| D24 | cosmoglasshardware.com 72 in tempered glass case |
| D25 | amazon.com frameless tower B01FXK9296; antdisplay.com 18 × 18 × 72 tower |
| D26 | amazon.com lighted display B00RE3VUJ6; cosmoglasshardware.com |
| D27 | kc-store-fixtures.com slatwall panel 4 × 8; plywoodcompany.com displawall |
| D28 | barrdisplay.com slatwall hooks; kc-store-fixtures.com slatwall hook |
| D30 | gondola-shelving.com size guide; rackleaders.com gondola dimensions |
| D31 | etsy.com/listing/962413366; jpscorner.com small display easels |
| D32 | etsy.com/listing/4390084055 (modular graded-card riser) |
| D33 | peccadille.net folding tables; warzonestudio.com folding table |
| D34 | koronapos.com/blog/cash-wrap/; econoco.com 55 in wrap counters; kaguyasu.com cashier counter guide |
| D35 | officedepot.com Adesso 16 in cash drawer |
| D36 | chase.com countertop terminal; stripe.com/terminal (WisePOS E). Which of them gave 168 × 81 × 56 was not recorded, so G3 is E\* |
| D37 | hprt.com 58/80/112 mm receipt paper. It supports the paper width only, not a printer body size |
| D38 | pricegun.com Monarch 1131; amazon.com Monarch 1131-01 (label size only; the body is our own shape) |
| D39 | wizardcoinsupply.com BCW 400-count slab storage/shipping box |
| G1 | tcgcardshopsimulator.wiki.gg (Card Displays, Grading); tcg-card-shop.fandom.com (Card Display Table, Small Card Display, Workbench); steamdb 0.60 patch notes; tcgcardshopsimulator.site; tcg-card-shop-simulator.wiki (fan sites; re-check before relying on them) |
| G2 | gamerant.com/tcg-card-shop-simulator-all-card-rarities/ |
| G3 | steamcommunity.com/app/3070070/discussions/0/4700162167909935419/ (product counts) |
| G4 | tcgcardshopsimulator.wiki.gg/wiki/Grading; neoseeker.com Card_Grading |
| G5 | fab.com/listings/91ec2c00-e360-418a-ba83-a4c04dc478c1 (Shop Simulator – TCG Card Store Template) |
| G6 | store.steampowered.com/app/4157170; mkaugaming.com Sports Card Shop Simulator review; store.steampowered.com/app/4408450; gosugamers.net TCGCSS review |
| G7 | steamcommunity.com/app/3569500/discussions/0/599659929547088948/ (CSSM "blurry graphics"); steamcommunity.com/app/3070070/discussions/0/4852155320354644196/ |
| G8 | tcgcardshopsimulator.wiki.gg/wiki/Accessories; tcgcardshopsimulator.wiki.gg/wiki/Card_Sleeves ("40 in a box") |
| G9 | tcgcardshopsimulator.wiki.gg/wiki/Stock_Order (ordering on a phone) |
| G10 | cgmagonline.com/review/game/tcg-card-shop-simulator-pc/ (the stocking loop) |
| U1 | forums.unrealengine.com/t/small-physics-objects-passing-through-walls/1797112; forums.unrealengine.com/t/how-to-stop-tiny-physics-objects-from-falling-through-the-floor/658508 |
| T1 | trademarks.justia.com/770/56/one-77056502.html (ONE-TOUCH, Reg. 3289899) |
| T2 | trademarks.justia.com/902/90/card-90290791.html (CARD SAVER, Reg. 6309079) |
| T3 | uspto.report/TM/98038084 (Deck Protector, serial 75086783; status not confirmed) |
| T4 | pokemoncenter.com/category/elite-trainer-box |
| M1 | `FAB_ASSET_STUDY.md` line 448, ref [58] (price bands, one style per product) |
| M2 | `FAB_ASSET_STUDY.md` lines 298-306 (price grid), line 341 (title, media) |
| M3 | dev.epicgames.com Fab "Asset File Format and Structure Requirements" (snippet), ref [15] in the study; the study's line 327 tags the minimum counts [unverified] |
| M4 | epicgames.com/site/en-US/content-guidelines; legal.epicgames.com IP FAQ |
| M5 | uspto.report/TM/88049038; uspto.report/TM/75979185; mtg.fandom.com/wiki/Card_back |
| M6 | gamedeveloper.com (WotC v. Cryptozoic filing); hipstersofthecoast.com 2014/05 |
| M7 | pregradecards.com fake-slab guide; cardsmania.fun forged-label case; en.wikipedia.org/wiki/Coin_slab |
| M9 | cgtrader.com empty graded card slab holder; turbosquid.com 2106609 |
| M10 | `WorkFiles/asset_research/GENRE_SCAN.md` item #1; `genre_scan_results.json` |
| R | `CLAUDE.md`, `ASSET_GUIDELINES.md` §1-6, §10, `Scripts/pipeline/*.py` (export_fbx, qa_check), `Scripts/props/props_lib/spec.py` and `atlas.py`, `Scripts/unreal/materials/run_build.sh`, `np_spec.py`, `material_spec.json` and README, `WorkFiles/armory/ARMORY_PLAN.md` §7-§11, `ITEM_INVENTORY.md`, `Exports/Flashbang/README.md`, `Exports/PaperBomb/README.txt` |

## Files

| Path | Status |
|---|---|
| `WorkFiles/cardshop/CARDSHOP_KIT_SPEC.md` | this file |
| `WorkFiles/cardshop/BRAND_NAMES.md`, `FONTS.md`, `IP_REVIEW.md` | planned (P0 / P2) |
| `Scripts/cardshop/…` | planned (7.2) |
| `Assets/CardShopKit/<Family>.blend` (LFS, one per family), `Exports/CardShopKit/<Group>/` (FBX + `.sockets.json` + `.csk.json` + `Textures/` + `README.md` + `MATERIALS_README.md`), `Renders/CardShopKit/` | planned |
| `WorkFiles/locks/cardshopkit.json` + `csk_<family>.json` | claimed at P0 / per family, never before G0 |

Note: the market research suggested `WorkFiles/card_shop/` for the name list. This spec uses `WorkFiles/cardshop/`, one
folder for the whole kit.

---

## Review log

Revision 2 (2026-09-28) applied the *buyer* review (14 points) and the *pipeline-ip* review (22 points). Every point was
applied, except the ones below, which were rejected or changed.

| Review · point | Decision | Why |
|---|---|---|
| buyer 1 | Applied, with one change: `csk_pack_cards.py` is standalone Python 3 + Pillow, not a UE Python utility; the UE side is `csk_make_card_array.py` (Texture2DArray) | UE's embedded Python ships no image library, so pixel packing inside the editor is not practical |
| buyer 2 + pipeline-ip 5 | Merged. One `Level_<Lvl>` origin per level + 2-4 `Compartment_` sockets (buyer); per-class grids live in data under that origin. **Rejected:** pipeline-ip's one origin socket per level *and class* | Class grids differ only in data, so one origin per level is enough and keeps the count at about 32 per showcase |
| buyer 3 | Applied, but `Hang` only on items with a hang tab (4 of 8, + the blister) | A bottle, a tube and a wrapped binder have nothing to hang by |
| buyer 5 | **Rejected:** "Std pack 64 W". Took the other option: Box S widened to 140 (and deepened to 80, raised to 125) | A 64 pack leaves 0.5 mm per side around a 63 mm card; 67 is the M pack width [D2][D9] |
| buyer 8 | Applied, but the card's front and back are picked by **UV tile** (floor(U)), not by vertex colour | Same single draw, with no vertex-colour channel, and UV0 stays non-overlapping for `qa_check` |
| buyer 8 + pipeline-ip 4 | Slab/holder LOD1 keeps a single front skin; LOD2 drops it (pipeline-ip asked for both LODs to drop it) | Handheld LOD1 starts at 1.5 m, which is still case-viewing distance (buyer 8), so one reflective skin is kept there |
| buyer 9 vs pipeline-ip 3 | Minimum handheld hull 2 mm (buyer's 2-3 mm), not 1 mm | Chaos's trouble with thin bodies (M [U1]) argues for the thicker hull; the fit test no longer uses hulls, so padding costs nothing |
| buyer 10 | Applied slatwall 1000/2000, end-corner pivots and snaps. **Rejected:** "make the shell module 1219" | The metric shell matches UE's 10 cm grid and the house whole-metre wall rule; gondolas are freestanding and can stay imperial |
| buyer 12 (gondola back) | Chose the slatwall back, not a pegboard hook variant | One hook family (A8) fits both walls and gondolas |
| buyer 12 (second counter) | Cut the 1829 counter (E), kept the 1397 (M [D34]) | Keep the measured size |
| pipeline-ip 1 | Chose option (a), a separate `.csk.json` with hashes. **Rejected:** (b) the `sidecar_extra` keyword | (a) leaves the pipeline and its self-tests untouched |
| pipeline-ip 6 | Applied with a different channel plan: UV0 = print/detail tiles, UV1 = unique 0-1 (lightmap + baked-AO ORM), UV2 = tiling | Buyer 1 needs print faces at 0-1 in UV0; baking AO on UV1 still meets "ORM.R is baked AO" |
| pipeline-ip 10 | Chose a second atlas `T_CSK_BoxesL` with 2048 × 1024 cells. **Rejected:** "about 1.8 px/mm" | The house atlas method uses integer px/mm (`props_lib/atlas.py`) |
| pipeline-ip 21 | Values with no recorded source key were downgraded to a new flag, E\*, not re-sourced | No source was invented; the user's own measurements (open question 2) or a later research pass can promote them |
