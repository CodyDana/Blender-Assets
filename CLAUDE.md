# Blender_Projects: ninja asset line for a UE 5.8 game and Fab

A solo developer's game assets, built in Blender 5.2 for their Unreal Engine 5.8 ninja game (a 1v1 duel MVP; a battle
royale later) and for sale on Epic's Fab. Almost everything is built by Claude sessions through Python scripts run in
headless Blender, then verified in Unreal. This file is for any session, local or cloud, that opens this repo.

## Layout

| Folder | What |
|---|---|
| `Scripts/` | All build code. `pipeline/` = the ONLY export path (export_fbx, qa_check, helpers, textures, lock, garments, sockets). `props/` = per-item builders (`build_<item>.py` + `props_lib/<item>_*.py`). `unreal/materials/` = the pack's recolourable materials as code. `garments/`, `SnowFlower/`, `SnowFlowerHeels/`, `dojo/`, `armory/`... |
| `Assets/` | Source `.blend` files (LFS). |
| `Exports/<Item>/` | Shipped game files: FBX + `.sockets.json` sidecar + `Textures/` + `README.md` / `MATERIALS_README.md` (LFS for binaries). |
| `Renders/<Item>/` | Final renders and reference side-by-sides (LFS). |
| `References/<Item>/` | The user's reference images and measured specs (plain git, so they're available without LFS). |
| `WorkFiles/<item>/` | Reports, specs, study notes, check scripts. Heavy scratch (bakes, caches, test builds, images) is NOT in git. |
| `Backups/` | Local safety copies; only two verified baselines are in git. |
| `ASSET_GUIDELINES.md`, `FAB_ASSET_STUDY.md`, `TREE_BUILDING_STUDY.md`, `STONE_BUILDING_STUDY.md` | The standards: read before building anything. `TREE_BUILDING_STUDY.md` is the reference for any tree, plant or vegetation build (build or buy, pipeline, Unreal setup, gates). `STONE_BUILDING_STUDY.md` is the reference for any stone, masonry or rock build (walls, steps, paving, lanterns and carved stone, boulders; build or buy, pipeline, Unreal setup, gates). |

## Rules that matter

- **Export only through `Scripts/pipeline/`** and run `qa_check` before every export. Measured Unreal 5.8 rules:
  collision is `UCX_<render mesh NODE name>_NN` (with LODs: `UCX_<base>_LOD0_NN`); sockets are Empties plus the
  `.sockets.json` sidecar applied by `ue_import_sockets.py` (the FBX socket arrives at scale 100); Import Mesh LODs ON;
  BaseColor sRGB, ORM linear, Normal DirectX; power-of-two maps with full mips; garments export in centimetres
  (pipeline 1.2.0). Verify Unreal results in a second, fresh process on the exact exported bytes.
- **Shared materials:** before editing anything in `Scripts/unreal/materials/`, take the lock
  (`py -3 -B Scripts/unreal/materials/np_lock.py claim <name>`) and build only via `run_build.sh` (see its README).
- **Asset locks** live in `WorkFiles/locks/` (`Scripts/pipeline/lock.py`). Several Claude chats work in this folder at
  once: never edit another chat's asset, lock or in-progress folder.
- **Blender headless only:** `blender.exe -b --factory-startup --python script.py -- args`. One Unreal commandlet at a
  time on the machine; never leave one running.
- **Matching references "to the T"** is the user's bar. Match by looking, confirm by measuring, and blind-test: a judge
  who sees only image pairs must not be able to pick the copy on design. Invent nothing the reference doesn't show.
  Model real forms as real geometry with crisp bevels. Height-field relief and baked outlines on flat shapes have failed
  on ornate 3D items (Snow Flower sword, sheath, heels); tracing works as the 2D outline authority. If a construction
  does not converge, change the method rather than patch. Stop early and show the user when a round fails decisively.
- **IP:** everything sold must be the user's own design; no franchise symbols or names; private items stay out of git.

## Machine-specific paths (Windows)

Scripts assume the user's Windows PC: Blender `C:/Program Files/Blender Foundation/Blender 5.2/blender.exe`, Unreal
`C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe`, project root
`C:/Users/Cody/Desktop/Blender_Projects`. Unreal work (and final bakes and renders on the GPU) can only run there.

## Cloud sessions

A cloud session is a Linux VM with no GPU and no Unreal. Use it for planning, reference measurement, specs, script
work and reviews. Clone without LFS (`GIT_LFS_SKIP_SMUDGE=1`) and pull only the files a task needs
(`git lfs pull --include="<path>"`): the free LFS download allowance is 10 GB a month and the repo holds about 3.5 GB of
LFS. Push to a branch; the user's PC does the final bakes, renders and Unreal checks.
