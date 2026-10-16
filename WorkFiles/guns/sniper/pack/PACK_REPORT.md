# SR-01 pack colours: preparation report (2026-10-16, session `sr01-pack`)

**Status:** everything that needs no Unreal is done and checked. **The Unreal build has NOT run.** The main chat runs
`WorkFiles/guns/sniper/pack/run_pack_build.sh`. Nothing is committed.

## Lock

`PackMaterials` is **HELD by `sr01-pack`**, with pid 5584 (this session's `claude.exe`).
- When this session ends, that pid dies. The lock then reads as dead, and any chat's `claim` takes it over
  automatically.
- **Main chat: re-claim it first:** `py -3 -B Scripts/unreal/materials/np_lock.py claim sr01-pack --pid <your pid>`.
- Run the build with `LOCK_PID=<your pid>` so the lock stays live after the script.
- Release it after the commit.

## What was done

| Step | Result |
|---|---|
| Spec (`material_spec.json`, additions only) | +4 items, +10 instances, recolour group SR01, 5 Masks not imported, `changes_v11_sr01`. `materials/add_sr01_to_spec.py` proves that removing the SR01 keys gives back `materials/material_spec_before_sr01.json` (= main's spec at 48210363) |
| One change from the proposal | `MI_SR01_Mag` is on **`M_Steel_Master`**, not `M_Fabric_Master`. The pack's chain requires every Fabric leaf to override `Colour` (`build.instance_chain.leaf_overrides`), and the baked-only magazine has no value for it: `np_spec` refused it. The proposal named the steel master as the equal alternative; it is the AR-01 magazine's master. The look is BC × white Steel Tint, i.e. exactly the BC |
| BC kinds | Chassis and Mag BC are `BC_BC7` (the SMG lesson). The capture measures BC1 beside BC7, so the main chat can choose BC1 if it fits (`add_sr01_to_spec.py --bc-kind BC --mag-bc-kind BC`, then re-run) |
| Recolour maps | `materials/sr01_recolour_maps.py` (the W6 draft, made final) wrote `Exports/Guns/SR01/Textures/Recolour/T_SR01_Chassis_Detail16.png` + `recolour_maps.json` (schema `ninjapack.recolour_maps/1`), replacing the W2 stub. Texture/JSON only. Pre-check `gates/recolour_precheck.json`: PNG round trip exact, fabric_part PASS, 13-colour stress PASS, black floor / knee PASS. Default path vs BC on the OD: p50 0 / p99 1 / p99.9 3 levels (reported; the reason the OD ships baked) |
| Constants | `Scripts/unreal/materials/maps/derive_constants_sr01.py` (CRLF, as checkouts produce). Run in headless Blender **from the mirror** on main's LF bytes. Every gate PASS (v1 contract at mip 0 and every mip, guards inactive, mip drift within 2 %). It records twin sha 738545ec… = main's. Output: `Exports/.../Recolour/recolour_constants.json` + `materials/recolour_constants_SR01.json`. Log: `pack/derive_sr01.log` |
| Checks with no Unreal | **In the mirror:** `maps_check` (np_spec.py) OK and `np_preflight.py` OK. **In the worktree:** maps_check fails for every item, because this worktree's pack code is CRLF and some exports are LFS pointers (the SMG's known lesson); the mirror is what the build uses. **Dry run of run_pack_build.sh (`DRY_RUN=1`, steps 0-3):** passes |
| Mirror | `pack/make_mirror.py`, the SMG way. Copies of main's pack code + pipeline, with this branch's spec and derive script. Junctions to main's Exports and `WorkFiles/shuriken`, and to this worktree's `Exports/Guns/SR01` and `WorkFiles/guns`. Checks: M1 main's pack code clean; M2 main's spec = before-file (or = the branch spec once merged); M3 the branch's code differs only by the two files; M4 143 other-item textures and FBXs match the last import records. AR01 and SMG01 come from main, because this worktree's AR01 FBXs are LFS pointers. Removal tested: it unlinks the junctions and leaves the targets intact. The mirror is currently removed |
| Docs | `Exports/Guns/SR01/MATERIALS_README.md` and `README.md` updated for D1-a: instances built by the pack; OD baked; recolour = OD paint only after a future master switch; do not switch the baked colours off; BC7 on Chassis/Mag. The status says the Unreal build is pending |

## For the main chat: run it

```
LOCK_PID=<your claude.exe pid> bash WorkFiles/guns/sniper/pack/run_pack_build.sh sr01_1016
```

The script runs these steps and stops at the first failure:
1. lock;
2. spec re-check;
3. no pack build newer than `dump_smg01_1013b`;
4. mirror + maps_check + preflight;
5. `NP_OWNER=sr01-pack run_build.sh sr01_1016 maps_check import_meshes import_textures clean build assign verify render`;
6. capture (`sr01_ue_capture.py`);
7. analysis (`sr01_pack_analyse.py`, Blender);
8. gates (`sr01_pack_gates.py` → `gates/pack_materials.json`: S1-S7, P1-P4, the dump comparison against `dump_smg01_1013b`; expected additions 10 instances / 4 meshes / 16 textures);
9. cleanup.

Build records go to `pack/build/`.

## What is left / risks

- Steps 4-8 have never run. The capture, analysis and gates scripts are adapted from the SMG's working ones and they compile, but they are untested. Likely first-run fixes would be small key or path mismatches.
- After the build, look at the R3 lit frames (render step) before merging.
- If P1 fails with BC7: stop and report. BC7 is already the fallback.
- If P3b fails at near black, the gates file checks whether the 8-bit floor explains it, as on the SMG.
- The W5 Unreal summary's sha256 for `Textures/Recolour/*` no longer match: those two files were replaced on purpose. The meshes are unchanged.
- D1-b (a real OD-only recolour) needs a master change. It is not done.
