# SR-01 hand-off to the gun chat (2026-10-16)

**What it is:** Sniper Rifle SR-01. It is a bolt-action precision rifle with an olive-drab chassis, a cheek riser, a
folding/extending/canting bipod, a 10-round magazine and a separate long-range scope (generic, no markings). It was
matched to the user's AI design sheet. It ships as a rigged `SK_SR01` (LOD0-3) with 8 weapon clips, a static twin
`SM_SR01`, `SM_SR01_Mag` and `SM_Att_Scope_LongRange`.

**State:** Unreal **37/37** on the shipped bytes (W5, round 2). Pack colours are built as **D1-a**: the OD is baked
and every blocking gate passed (`gates/pack_materials.json`), but recolour is not supported. All branches are merged
on main (`claude/sniper-sr01-realism`, `-pack`, `-k4`, `-judges`; the last merge is fea170de).

## Where things are

| What | Path |
|---|---|
| Exports | `Exports/Guns/SR01/` (FBX, `.sockets.json`, `.skeletal.json`, `Textures/`, `Physics/`, `README.md`, `MATERIALS_README.md`) |
| Blends | `Assets/Guns/SR01.blend`, `Assets/Guns/Att_Scope_LongRange.blend` |
| Build scripts | `Scripts/guns/sniper/` (`build_sniper.py`, `sniper_parts.py`, `sr_*.py`, `run_*.sh`) |
| Reports | `WorkFiles/guns/sniper/`: `SR01_REPORT.md`, `SR01_BUILD_PLAN.md`, `W0`-`W5_REPORT.md`, `REALISM_R2_REPORT.md`, `K4_NOTE.md`, `H1_REPORT.md`, `FINAL_JUDGES.md`; gates in `gates/` |
| Unreal check | `WorkFiles/guns/sniper/UnrealCheck/` (`run_w5_r2.sh`) |
| Pack colours | `WorkFiles/guns/sniper/pack/` (`PACK_REPORT.md`, `run_pack_build.sh`, build records in `build/`); spec entries in `Scripts/unreal/materials/material_spec.json` |
| Showcase | `showcase/SniperRifle_SR01/` (15 images); row in `showcase/ASSET_LIST.md` |
| Fab draft | `WorkFiles/fab/listing_drafts/SR01_fab_listing_draft.md` |

## Open items (source → next step)

**Realism** (`FINAL_JUDGES.md`): the judges still call all 5 views CG. They listed 19 tells.
- *Render rig, no re-export (tells 1, 3, 5, 7, 8, 11):* replace the cyc with an HDRI or cove, fix the stepped floor
  shadows, add contact occlusion, use more samples or denoise the defocus, and add a reticle sight picture and objective
  coating. → Do these first. They are about half of all mentions.
- *Material (tells 2, 6, 9, 14, 15, 19):* add edge wear, dust and roughness variation to the OD; dull the chrome bolt
  and bipod legs; mould the grip stipple; add more generic scope graduations. **Tell 6's maker text, serials and brands
  are not allowed** (IP). → Texture pass, then re-export.
- *Geometry (tells 4, 10, 12, 13, then 16-18):* fix the faceted, notched forend ridge and the chassis step, the boxy
  riser and buttpad, the bolt knob taper and the mag baseplate. Lower priority: bipod locks, muzzle crown and eyecup.
  → Generator change in `sniper_parts.py`.

**Form / close-up gates** (`REALISM_R2_REPORT.md`, `K4_NOTE.md`):
- GR **0.9571** (bar 0.958, K10 fails by 0.003), caused by the fillets and fairing. → Try smaller fillets on the long
  runs (rc = r + 0.1).
- K1 hard creases are at 0.58× (target ≤ 0.5×). K3 OD peel tilt is 0.436 and was not addressed. → Rework the
  crease and peel passes, then re-run `gates/closeup_r2.json`.

**Hands** (`H1_REPORT.md`; the proposals are measured but NOT applied):
- `SupportHand` (342.87, 0, 50.53) is 76.6 mm short in pose A. → Choose the stance: X ≤ 259.9 for a square stance,
  or keep X with a 23° bladed torso. Also set Z 40.90 (the socket is 9.6 mm inside the forend).
- `SupportHandBipod` (-179.13, 0, 4.13) is 38.1 mm inside the butt. → Set Z -33.99.
- Cheek riser: the face sits inside the riser, and full drop leaves it 1.6 mm short under the eye. → Lower the riser
  or extend its travel. Re-check with `sr_h1_full.py`.
- U11, the hand fit on the player MetaHuman in Unreal, has not run. → Run it after the sockets are settled. The
  engine pose needs its own thumb.

**Pack colours** (`pack/PACK_REPORT.md`, `Exports/Guns/SR01/MATERIALS_README.md`):
- D1-b, a real OD-only recolour, needs a master switch (a mask). → Take the PackMaterials lock, build it via
  `run_build.sh`, then re-run P3b. P3b (the pack's v3 recolour-quality gate, reported, not blocking) failed on 11 of 13 colours in the
  real build `sr01_1016`, and the build said the failure is NOT explained by the 8-bit near-black floor
  (`gates/pack_materials.json`): a recoloured OD loses wear detail. Do not advertise recolour until it passes.

**gunlib proposals P1-P9 + W1/W2 helpers** (`SR01_BUILD_PLAN.md` §10):
- P1 riser parent `body`, P2 motion axes, P3 sniper/optic budgets, P4 attachments block, P5 `dovetail_plain`,
  P6 `key_action`, P7 optional sockets, P8 `telescoping_leg`/`detent_disk`, P9 TOP shadow trace.
- The sniper-local helpers are `sr_scope`, `sr_silhouette`, the `Part` boolean steps, `sr_surface.CYL`,
  `sr_render.studio_rig` and the weld step.
- → The gun chat accepts or rejects each one. Promote from the sniper-local code under the `GunLib` lock.

**Fab pre-publishing** (draft §7, 19 items):
- **Blockers:**
  - The design is too close to a real gun: the blind test picked the copy 14/14. → Write and apply SR01's own
    original-design list, then re-run all gates and W5.
  - Record the markings exception (turret numerals, S/F).
  - Re-run the deny scan on the final bytes and text.
  - Decide whether to keep the AR-01 references.
  - The AI declaration is the user's call.
- **Fab rules:** ask Fab whether weapon-only clips meet the firearms rule, or add a Manny arms set.
- **Shared masters:** copy the shared masters into the pack (`Content/<Pack>/`).
- **Docs:** fix the stale and internal README text (round-1 triangle counts, "pending" banners, internal paths).
  Re-verify the hashes.
- **Unreal product (not built yet):** project, overview map, example BP, notifies, `PHYS_SR01`, migrate test, zip.
  Re-run the measurements on 5.8.3.
- **Media:** a 16:9 showcase, thumbnail, grid and trailer.
- **Listing decisions:** price, sources, formats, and the competitor gap (ammo, skins, BPs).

## Rules that bind any change
- Take the `SR01` lock (`Scripts/pipeline/lock.py`). Edit `Scripts/unreal/materials/` only under the PackMaterials
  lock, via `run_build.sh`. Run Blender headless only, and only one Unreal commandlet at a time.
- Re-export **only through `Scripts/pipeline/`**, and run `qa_check` before every export. No maker text or brands.
- On the new bytes, re-run W5 in a fresh process (the `UnrealCheck/run_w5_r2.sh` pattern; it must stay 37/37). Then
  re-run the pack build `pack/run_pack_build.sh`; its lit frames now land in `pack/build/frames/`. Then refresh the
  showcase and its `ASSET_LIST.md` row.
