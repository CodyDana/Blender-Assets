# Asset list

Every asset we have built in this project, with its showcase pictures. Each folder in `showcase/` holds only the
pictures for one asset. Made on 2026-10-02 from the inventory in `WorkFiles/showcase/inventory.json`.

**Totals: 25 assets, 748 meshes, 1,100 showcase images.**

- 24 are our own designs. SummoningJutsu is older fan art the user chose to keep in the showcase (local only, not for sale). The other fan-art pieces are under "Not included".
- Mesh counts are the shipped LOD0 meshes. LOD1/LOD2, collision and physics proxies are not counted.
- Each folder has most or all of the following:
  - Studio renders: hero (3/4 view), front, side, back, top, and usually a hero on a dark background.
  - For kits: one hero per mesh (`SM_*_hero.png`) and labelled contact sheets of 20 (`*_Sheet_NN.png`).
  - Assembled group shots where they make sense.
  - Copies of the best existing renders and Unreal captures, named `*_Scene_*`.

## Throwables and weapons

| Asset | What it is | Status | Meshes | Where it lives | Images |
|---|---|---|---|---|---|
| [Shuriken](Shuriken/) | Six original steel throwing stars: four-point, eight-point, square plate, six-point, spike and hooked cross. | Finished, Unreal-verified | 6 | `Exports/Shuriken/SM_Shuriken_*.fbx`; `Assets/Shuriken.blend` | 40 |
| [Kunai](Kunai/) | 280 mm kunai with a full-diamond blade, ring pommel and tape-wrapped grip; dark and undyed wraps. | Finished, Unreal-verified (blade rework 2026-09-27) | 1 | `Exports/Shuriken/SM_Kunai_Plain.fbx`; `Assets/Shuriken.blend` | 9 |
| [PaperBomb](PaperBomb/) | Explosive paper tag with the user's own calligraphy and flame emblem. | Finished, Unreal PASS (2026-09-26) | 1 | `Exports/PaperBomb/`; `Assets/PaperBomb.blend` | 10 |
| [SmokeBomb](SmokeBomb/) | Cloth-wrapped smoke bomb ball. | Finished | 1 | `Exports/SmokeBomb/`; `Assets/SmokeBomb.blend` | 9 |
| [Flashbang](Flashbang/) | Stun grenade with a perforated olive body, spoon lever and pull ring, plus split parts for the pin-pull mechanic. | Finished (2026-09-27) | 1 | `Exports/Flashbang/`; `Assets/Flashbang.blend` | 13 |
| [BlackNunchucks](BlackNunchucks/) | Black textured nunchaku with silver caps and a seven-link chain; recolourable. | Finished (built by the Codex agent) | 1 | `Exports/BlackNunchucks/`; `Assets/BlackNunchucks.blend` | 11 |
| [Fan](Fan/) | Black silk folding fan with 26 bamboo sticks, a leaf that really folds, and an optional tassel. Rigged and animated. | Finished | 2 | `Exports/Fan/`; `Assets/Fan.blend` | 12 |
| [SnowFlower](SnowFlower/) | Ornate straight sword with a floral silver guard, and its black-lacquer sheath. | Finished in Unreal (v4); look-match to the reference not reached | 2 | `Exports/SnowFlower/v4/`; `Assets/SnowFlower/SnowFlower_Game_v4.blend` | 14 |
| [Senbon](Senbon/) | Two original throwing needles: a 130 mm double-pointed volley needle and a 170 mm heavy needle with a three-facet point and a recolourable cotton-wrapped tail. | Finished, Unreal-verified (2026-10-03) | 2 | `Exports/Senbon/`; `Assets/Senbon.blend` | 17 |

## Clothing

| Asset | What it is | Status | Meshes | Where it lives | Images |
|---|---|---|---|---|---|
| [BlackHat](BlackHat/) | Black conical woven kasa hat with ribs, a cloth band and two hanging ties; straw and cloth recolourable separately. | Finished, Unreal-verified (tie cut removed, recolour re-verified 2026-10-02) | 1 | `Exports/BlackHat/`; `Assets/BlackHat.blend` | 9 |
| [BlackCloak](BlackCloak/) | Long black wrap cloak with scarf collar and clasp, plus the MetaHuman wearable version (v2). | Static cloak finished (Codex agent); MetaHuman v2 in progress | 2 | `Exports/BlackCloak/`, `Exports/Garments/BlackCloak_MH_v2/`; `Assets/BlackCloak.blend`, `Assets/Garments/BlackCloak_MH_v2.blend` | 17 |
| [SnowFlowerHeels](SnowFlowerHeels/) | Black pointed-toe ankle-strap pumps with silver vine ornament, skinned for MH_PlayerFemale. | Finished in Unreal (walk/run verified); look-match not reached | 1 | `Exports/SnowFlowerHeels/`; `Assets/SnowFlowerHeels/` | 11 |

## Interior kits

| Asset | What it is | Status | Meshes | Where it lives | Images |
|---|---|---|---|---|---|
| [CardShopKit](CardShopKit/) | Collectibles card shop: cards, slabs, booster boxes and packs, binders, display cases, shelving, counter and fixtures. **Private for now.** | In progress (all meshes pass the G1 Unreal run; design review open) | 179 | `Exports/CardShopKit/G1/` | 204 |
| [ArmoryKit](ArmoryKit/) | Dark-timber museum armory: glass display cases, walls, lattice windows, ceiling, lanterns, platform, plus an exterior garden and building set. | In progress (round r20, about 6/10; interior now shared with the dojo main hall) | 117 | `Exports/ArmoryKit/` | 135 |

## Dojo arena kit

| Asset | What it is | Status | Meshes | Where it lives | Images |
|---|---|---|---|---|---|
| [DojoKit_Buildings](DojoKit_Buildings/) | Main dojo hall, covered corridors, storehouse, residence, drum pavilion and training shed. | In progress (about 5.5 to 6.5/10) | 81 | `Exports/DojoKit/{Hall,Corridors,Outbuildings,Pavilion,Shed}/`; `Assets/Dojo/` | 101 |
| [DojoKit_WallGate](DojoKit_WallGate/) | Plaster-and-tile perimeter wall (1/2/4 m, three thicknesses) and the roofed gatehouse. | In progress (about 5.5 to 6/10) | 28 | `Exports/DojoKit/Kit1/` | 43 |
| [DojoKit_StoneKit](DojoKit_StoneKit/) | Granite retaining walls, corners, copings, stair flights, landings, kerbs, rails and stair lanterns. | In progress (round f2) | 104 | `Exports/DojoKit/StoneKit/` | 116 |
| [DojoKit_Ground](DojoKit_Ground/) | Courtyard ground: raked sand, gravel tiles, paving, kerbs, planting beds, pebbles and grass/moss tufts. | In progress (Blender done, about 5.5/10) | 72 | `Exports/DojoKit/Ground/`; `Assets/Dojo/DojoGround.blend` | 82 |
| [DojoKit_Outside](DojoKit_Outside/) | Approach street and backdrop: roads, kerbs, canal, fences, background houses, far town, ridges and 1v1 blockers. | In progress (round r5) | 48 | `Exports/DojoKit/Outside/` | 62 |
| [DojoKit_Props](DojoKit_Props/) | Stone lanterns, well, cistern and crates; training gear; vending machine, AC units, utility pole and lamps; emblem plaques. | In progress (Blender done, about 6.5/10) | 35 | `Exports/DojoKit/Props/`, `Exports/DojoKit/Dressing/` | 41 |
| [DojoKit_Taiko](DojoKit_Taiko/) | Large taiko drum on a timber stand with two drumsticks. | Finished in Blender (about 6.5/10) | 3 | `Exports/DojoKit/Props/taiko/`; `Assets/Dojo/Taiko.blend` | 13 |
| [DojoKit_Pines](DojoKit_Pines/) | Eight cloud-pruned garden pines (4 designs x 2) with trunks, foliage, base mounds and rocks. | Pilot (about 4/10; method to be revised) | 22 | `Exports/DojoKit/Pines/` | 80 |
| [DojoKit_FX](DojoKit_FX/) | Falling cherry petals, drift clusters, petal decals, and mist/spray flipbooks. | First pass finished | 10 | `Exports/DojoKit/FX/` | 33 |
| [Rocks_Pilot](Rocks_Pilot/) | Granite river boulders (round and long) and a jointed cliff chunk with moss and lichen. | Pilot (about 5/10, below the 7/10 gate; the user decides retry or source) | 3 | `Exports/DojoKit/Rocks/`; `Assets/Dojo/DojoRocks.blend` | 22 |

## Characters

| Asset | What it is | Status | Meshes | Where it lives | Images |
|---|---|---|---|---|---|
| [Ninja](Ninja/) | Stylized ninja built from a Skin-modifier body: black suit, red headband, sash, wraps, pouch and katana. | Early study (2026-07-31); not exported, not rigged | 26 | `Assets/Ninja.blend`; `Scripts/build_ninja.py` | 8 |

## Legacy (local only, not for sale)

| Asset | What it is | Status | Meshes | Where it lives | Images |
|---|---|---|---|---|---|
| [SummoningJutsu](SummoningJutsu/) | Ink summoning-seal circle as a 4 m game decal. Naruto fan art: kept in the showcase by the user, never for sale. | Legacy decal | 1 | `Exports/SM_SummoningJutsu.fbx`, `Exports/T_SummoningJutsu_D.png` | 5 |

## Not included

| Item | Why it has no folder |
|---|---|
| Hiyuki private MetaHuman test | Private, do not ship. It lived only in Unreal, and CharacterLab was removed. |
| 2B private base body | Private, do not ship. The source is a downloaded Sketchfab/DAZ model, not built by us. |
| DemoGame_1_private2b | Private Unreal project for the 2B test, not an asset. |
| JinMuWon character | Removed by the user on 2026-09-28; the name comes from a third-party manhwa. Only old renders and scripts remain. Ask before showing it. |
| MetaHuman player characters | MetaHuman assets that live in Unreal, not Blender builds. They appear only as fitting bodies under the garments. |
| Dojo grey-box blockout (`SM_DGB_*`) | Layout and climb-test blocks, replaced by the real kit pieces. |
| Superseded Dojo rounds (`_superseded_*`) | Older rounds replaced by the current kit. |
| Snow Flower rev 3 | Replaced by v4. Rev 3 was built by another AI agent. |
| Black cloak MetaHuman fit v1 | Replaced by v2; work files only. |
| Package zips (cloak, nunchucks) | Copies of assets already listed. |
| LOD1/LOD2, previews, physics proxies, Unreal demo projects | Parts or by-products of listed assets. |
| Dojo landscape, mountains, river, sourced trees | Sourced scenery (user rule), Unreal only, nothing built in Blender. |
| DojoWheat | A lock exists, but no blend or export is on disk yet. |
| Cafe Kit | Study and plan only, nothing built. Only on the unmerged branch `claude/cardshop-build-integration-5227b4`. |
| Retail Packaging System | Plan only, nothing built. Only on the same unmerged branch. |
| Three-point shuriken, Negishi dart | Planned in the shuriken study, never built. |
| Backups and References | Safety copies and reference images, not assets. |
| Fan art: Ea_Sword (Fate), Kamish_Daggers (Solo Leveling), AWM_Sniper (real rifle name) | Built by us in August 2026 from other people's designs. Not ours to sell; removed from the showcase by the user on 2026-10-02. The source files stay in `Assets/` and `Exports/`. |

## Known issues

These are the showcase renders that are not perfect. Most come from the studio render tool, not from the assets.
The Unreal look will differ from these Blender renders.

**Placeholder art or materials the asset really has**
- **CardShopKit:** cards, packs, boxes, posters and signs show the kit's G1 placeholder art ("PYRECALL F", FRONT/LID/BOTTOM labels, corner markers); the Box_Collector front shows "BOTTOM". Some curved glass and acrylic pieces (CardTable_Lid, Case_Counter_Lid, Showcase_Half_Glass, Stand_Card_1) show a bright reflection patch. There are no BoosterBox or CardTable group shots, because their lids export at the origin.
- **ArmoryKit:** the Hills and Mountains rings render as pale glowing bands, because their texture is wired as emission. Facade plaster and the white `SM_AK_H_*` pieces are plain white because they have no textures. Court_Gravel and Ground_Field look plain.
- **DojoKit_Outside:** the 1v1 blockers are flat red (their real material). Long thin pieces (roads, verges, water) read as a line. Ground pieces look flat brown (Unreal uses world projection). FarGround renders mid-grey instead of dark olive. Far town and ridge rings are tiny in frame. Two copied captures (alley_E, junction_E) are weak.

**Approximate materials (Blender stand-ins for Unreal materials)**
- **DojoKit_WallGate:** plaster is UV-mapped, not world-projected. FootingStone, TimberPale and JointEarth are approximations without moss. Gate timber reads darker than in the dojo chat's renders.
- **DojoKit_StoneKit:** no vertex-colour wear or moss blend. Timber uses the plain dark set. The stone lantern granite looks speckled. Dark joint cores show as black slabs on the backs of walls (real geometry).
- **DojoKit_Ground:** raked sand and texture variation can't be seen at hero distance. Kerb granite looks coarse close up. The courtyard shots are flat.
- **DojoKit_Pines:** D-rock moss is too yellow, and the needles have no canopy shading. Some trunk and roots show below the mound edge, and a PineB1 root sticks out. BaseMound_D alone looks like a ring. The trees fill only about half the frame, and there is no group shot.
- **DojoKit_Props:** thin wires and the pole guy read faintly. There is no assembled well shot. The emblem plaque rim renders near-black (not checked against the design). Wood is darker than in the dojo's own renders.

**Framing and pose**
- **DojoKit_Buildings:** some modular pieces look sparse alone (for example Bay_DoorOpen and the thin roof strips). The storehouse roof notch is modelled. There are no dark-background shots.
- **DojoKit_WallGate:** the WallRun shots are small in frame.
- **DojoKit_FX:** the drift-cluster heroes look sparse; the top views read better. Mist and spray appear only in the copied scene renders.
- **PaperBomb:** all studio views are from above, so "back" shows the art face from the far end and "top" lies sideways. The copied `paperbomb_back` scene shows the underside.
- **SmokeBomb:** the copied `smokebomb_back` scene has a white transparent background.
- **BlackNunchucks:** the grips look grey in the top view (reflection).
- **Fan:** the top view shows the upright fan edge-on.
- **BlackCloak:** the dark-background hero has low contrast. The MetaHuman v2 garment is still in a wide rest pose.
- **SnowFlower:** tall, thin, so it fills only a narrow strip of the 4:3 frame.
- **SnowFlowerHeels and Flashbang:** recolours are material settings or detail maps, so they have no separate renders. Flashbang's copied swatch image shows its recolours.
- **DojoKit_Taiko:** the sticks lean against the stand, as laid out in the source file.

**Render tool (`Scripts/showcase/studio.py`)**
Several batches needed wrappers for the same gaps. They are worth fixing in `studio.py` itself:
- texture-set matching: prefer an exact name match, add aliases, and support explicit maps;
- alpha cut-out for leaves;
- clear glass;
- drop the floor slightly below flat tiles and decals;
- convert curves to meshes;
- hide the studio lights from the camera;
- render on the GPU only, which lowers CPU load.
