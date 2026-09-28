"""Finalise step 6: append the final list and the note to the main chat to LIVE_CHANGES.md.
    py -3 append_final_live_changes.py <Get-Date -Format o timestamp>"""
import json, sys
from pathlib import Path

P = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = P / "WorkFiles/kunai/blade_section/finalise"
LOG = P / "WorkFiles/kunai/blade_section/LIVE_CHANGES.md"
ts = sys.argv[1]
res = json.loads((HERE / "final_change_list.json").read_text(encoding="utf-8"))
table = (HERE / "final_change_list.md").read_text(encoding="utf-8").rstrip("\n")
n_changed = len(res["changed"])
fs = res["frozen_six"]
text = f"""| {ts} | (this file) | FINALISE 6: final list and note to the main chat appended below (`finalise/final_change_list.py` -> `final_change_list.json` / `.md`). No other live file written in this step. |

## Final list of live changes (finalise, {ts})

Every live file the blade-section rework changed, from the pre-rework copies (`regression/pre_blade_section` + `extras/`,
`script_backups/`, `UnrealCheck6/*.before_blade_section.py`) to the shipped bytes. {n_changed} files changed.
Machine-readable: `WorkFiles/kunai/blade_section/finalise/final_change_list.json`.

{table}

**Changed, without a single old/new hash:**
- `WorkFiles/shuriken/diag/kunai_plain_*` (11 files: masks, the knife-coat-rule `*_orient.png` / `*_refcoat.png` passes,
  LOD close-ups) - build diagnostics, promoted with the kunai.
- `Scripts/shuriken/__pycache__/`, `Scripts/shuriken/shuriken_lib/__pycache__/` - bytecode caches refreshed by the
  headless builds (no source effect).
- `WorkFiles/kunai/lettering_test/lettering_*.png`, `lettering_test_sheet.png`, `lettering_test_render.{{json,log}}` -
  the lettering proof, re-rendered (Sep 19 copies in `finalise/lettering_pre/`).
- `WorkFiles/materials/`: `build/*_kblade_0927.*`, `maps/gates_kunai_wrap.json`,
  `final/constants/recolour_constants_Shuriken.json`, `ue_renders/` kunai entries (see the materials rows above).
- Unreal `WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject`: new check paths
  `/Game/ShurikenCheck9/KunaiBladeC1`, `KunaiBladeC2`, `KunaiBladeC3`; `/Game/NinjaPack` rebuilt (`kblade_0927`: only
  `MI_Kunai_Plain_Wrap`, `_Base`, `_Undyed` changed, in their derived constants; kunai mesh and maps re-imported).
- New: `WorkFiles/shuriken/regression/post_blade_section/` (the new baseline) and
  `Backups/Shuriken_after_kunai_blade_section_2026-09-26/` (129 files, hash-verified).

**Checked unchanged:** `Exports/Shuriken/Textures/T_Kunai_Lettering.png`, `Exports/Shuriken/MATERIALS_README.md`,
`References/Kunai/LETTERING_HOWTO.md`, `Scripts/shuriken/build_pack.py`, `line_sheet.py`, `ue_import_textures.py`,
`Scripts/pipeline/`, and every other `shuriken_lib` module ({len(res['unchanged_listed'])} listed files unchanged).
**The six other forms:** {fs['identical']}/{fs['files']} live files (FBX, sidecar, BC/ORM/N, five renders, report per form)
byte-identical to `prep/frozen_six_sha256.json`, re-checked at the end of this step.

## Note to the main chat

The kunai change is expected. `SM_Kunai_Plain` was reworked to the user's option C: a 7 mm full-diamond blade over a
0.3 mm edge, the knife-only hero coat rule and the 3/4 diagonal hero. It shipped as shuriken_lib 3.11.1, with FBX
`a2d464722c30...` and blend `abb558fef12a...`. The kunai's files, the pack-level reports and sheets, the Recolour
files and the kunai's `/Game/NinjaPack` wrap instances changed, as listed above. It passed every gate and two review
rounds, and it is verified in Unreal 5.8.3 on those exact bytes (independently, in `/Game/ShurikenCheck9/KunaiBladeC3`).
The other six forms (four_point, eight_point, square_plate, six_point, spike, hooked_cross) are byte-identical: their
FBX, sidecars, textures, renders and report figures did not change, and compare_frozen passes. Their
`M_Shuriken_Master` and `/Game/NinjaPack` instances are unchanged too (a CPU bake proves bitwise no-op). The new
regression baseline is `WorkFiles/shuriken/regression/post_blade_section/` (seven forms, self-check identical). The
next pack job should run `compare_frozen.py --snapshot post_blade_section` and build with
`--frozen-maps WorkFiles/shuriken/regression/post_blade_section/textures`. The backup is
`Backups/Shuriken_after_kunai_blade_section_2026-09-26/`. No lock was taken or changed: `WorkFiles/locks/shuriken.json`
is untouched, and the materials lock was released by the materials step.
"""
with open(LOG, "a", encoding="utf-8", newline="\r\n") as fh:
    fh.write(text)
print("appended", len(text))
