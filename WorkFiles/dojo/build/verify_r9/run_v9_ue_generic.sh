#!/usr/bin/env bash
# VERIFY r8: ONE fresh read-only commandlet on DojoLab running the given script (arg 1, in verify_r9/), log to arg 2.
# Waits while ANY UnrealEditor-Cmd runs (house rule: one commandlet machine-wide); stops if a DojoLab editor is open.
set -u
export MSYS_NO_PATHCONV=1
VD="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/verify_r9"
UE="C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
PROJ="C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject"
S="$1"; LOG="$2"
guard() {
  hit=$(powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Where-Object { \$_.CommandLine -match 'DojoLab' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r\n ')
  if [ -n "$hit" ]; then echo "STOP: DojoLab editor open (pid $hit)"; exit 3; fi
}
free=0
while [ $free -lt 2 ]; do   # two consecutive free polls 10 s apart
  if tasklist 2>/dev/null | grep -qi "UnrealEditor-Cmd"; then free=0; sleep 20; else free=$((free + 1)); sleep 10; fi
done
guard
echo "start $S $(date '+%F %T') parts=${DJ_PARTS:-} out=${DJ_OUT:-}"
timeout 5400 "$UE" "$PROJ" -run=pythonscript -script="$VD/$S" -unattended -nop4 -nosplash -nullrhi -nosound \
  -stdout -FullStdOutLogOutput "-dpcvars=r.TextureStreaming=0,Editor.AsyncStaticMeshCompilation=0" > "$VD/$LOG" 2>&1
echo "exit $? $(date '+%F %T')"
grep -o "V8F?_[A-Z_]*DONE.*" "$VD/$LOG" | head -3
