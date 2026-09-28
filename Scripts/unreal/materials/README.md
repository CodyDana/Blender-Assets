# Pack materials — shared by several chats

The pack's Unreal materials are built from code in this folder into the validation project
(`WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject`, `/Game/NinjaPack`). Several Claude chats use it,
so three guards stop one chat from breaking another's work (added 2026-09-27 after a collision deleted
`M_Fabric_Master` and orphaned 13 instances).

## Rules

1. **Take the materials lock before you EDIT anything here** (code or `material_spec.json`), and release it once your
   edits are built and verified. Use a name unique to your chat:

   ```
   py -3 -B Scripts/unreal/materials/np_lock.py claim snowflower-chat
   py -3 -B Scripts/unreal/materials/np_lock.py release snowflower-chat
   py -3 -B Scripts/unreal/materials/np_lock.py status
   ```

   If someone else holds it, wait. Never force a live holder (a holder whose process has died is taken over
   automatically).

2. **Build only through `run_build.sh`.** It enforces the rest:
   - it takes the lock for the whole run (owner `$NP_OWNER`, default `run_build:<tag>`; set `NP_OWNER` to your
     chat's lock name if you already hold the lock for editing) and refuses to start if another chat holds it;
   - whenever `clean` or `build` is requested it runs **`np_preflight.py` first**: every parameter each master graph
     asks for must exist in that master's spec table, and the spec must resolve. If not, it stops **before anything
     is deleted**;
   - it fingerprints the code and spec at preflight and stops if either changes mid-run.

3. **Add a spec entry in the same change as any new graph parameter.** `np_preflight.py` will tell you exactly
   which one is missing.

```
bash Scripts/unreal/materials/run_build.sh <tag>                          # maps_check import_meshes import_textures clean build assign verify
bash Scripts/unreal/materials/run_build.sh <tag> maps_check clean build assign verify
py -3 -B Scripts/unreal/materials/np_preflight.py                         # check without touching Unreal
```

One `UnrealEditor-Cmd` at a time across the machine (`run_build.sh` waits for others). Reports:
`WorkFiles/materials/MATERIALS_REPORT.md`; build logs and results: `WorkFiles/materials/build/`.
