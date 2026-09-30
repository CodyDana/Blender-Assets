#!/usr/bin/env bash
# VERIFY r2: one fresh read-only commandlet on DojoLab. Waits while ANY UnrealEditor-Cmd runs (house rule); stops if a
# DojoLab editor is open. Log + JSON in WorkFiles/dojo/build/verify_r2/.
set -u
export MSYS_NO_PATHCONV=1
VD="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/verify_r2"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject"
guard() {
  hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Where-Object { \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r\n ')
  if [ -n "$hit" ]; then echo "STOP: DojoLab editor open (pid $hit)"; exit 3; fi
}
free=0
while [ $free -lt 2 ]; do   # two consecutive free polls 10 s apart
  if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then free=0; sleep 20; else free=$((free + 1)); sleep 10; fi
done
guard
echo "start $(date '+%F %T')"
timeout 5400 "$UE" "$PROJ" -run=pythonscript -script="$VD/v2_ue_ledges.py" -unattended -nop4 -nosplash -nullrhi -nosound \
  -stdout -FullStdOutLogOutput "-dpcvars=r.TextureStreaming=0,Editor.AsyncStaticMeshCompilation=0" > "$VD/ue_ledges.log" 2>&1
echo "exit $? $(date '+%F %T')"
grep -o "V2_LEDGES_DONE.*" "$VD/ue_ledges.log" | head -1
