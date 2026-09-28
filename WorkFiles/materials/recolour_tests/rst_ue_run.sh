#!/usr/bin/env bash
# One UnrealEditor-Cmd (validation project only), real RHI, offscreen. Waits while any UnrealEditor-Cmd runs.
export MSYS_NO_PATHCONV=1
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"
SCRIPT="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/materials/recolour_tests/rst_ue_capture.py"
LOG="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/materials/recolour_tests/ue/rst_ue_capture.log"
mkdir -p "$(dirname "$LOG")"
while tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; do echo "waiting: an UnrealEditor-Cmd is running"; sleep 15; done
timeout 1500 "$UE" "$PROJ" -run=pythonscript -script="$SCRIPT" -unattended -nop4 -nosplash -nosound -stdout -FullStdOutLogOutput \
  -AllowCommandletRendering -RenderOffscreen \
  -dpcvars=r.TextureStreaming=0,Editor.AsyncTextureCompilation=0,Editor.AsyncStaticMeshCompilation=0 > "$LOG" 2>&1
echo "exit $?"
grep -o "RST_UE_DONE.*" "$LOG" | head -1
grep -c "RST_JOB" "$LOG"
tasklist 2>/dev/null | grep -i "UnrealEditor-Cmd" && echo "WARNING: UnrealEditor-Cmd still running" || echo "no UnrealEditor-Cmd running"
