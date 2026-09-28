#!/usr/bin/env bash
# UE_CMD wrapper for Scripts/unreal/materials/run_build.sh (kunai blade-section materials step, 2026-09-27).
# run_build.sh only waits for UnrealEditor-Cmd; the machine rule also forbids launching while an UnrealEditor.exe carries
# -run= / -ExecutePythonScript / -unattended / -nullrhi. So every launch first runs the shared guard
# (WorkFiles/shuriken/UnrealCheck6/wait_unreal_free.ps1: Win32_Process check, Start-Sleep 60 loop, up to 90 min),
# logging to GUARD_LOG, then execs the real UnrealEditor-Cmd with the arguments run_build.sh passed. GUI editors are
# never touched.
GUARD_LOG="${GUARD_LOG:-C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/kunai/blade_section/materials/guard.log}"
powershell -NoProfile -ExecutionPolicy Bypass -File "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/UnrealCheck6/wait_unreal_free.ps1" \
  -GuardLog "$GUARD_LOG" -Label "materials ${NP_MODE:-?} ${NP_TAG:-?}" >&2 || { echo "ABORT: Unreal busy for 90 min" >&2; exit 97; }
echo "$(date -Iseconds) LAUNCH materials ${NP_MODE:-?} ${NP_TAG:-?}" >> "$GUARD_LOG"
exec "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$@"
