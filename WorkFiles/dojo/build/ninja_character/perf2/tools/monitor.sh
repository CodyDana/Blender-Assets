#!/usr/bin/env bash
# perf2 background-load monitor: every 10 s until <donefile> exists: CPU %, GPU util / memory, blender.exe count,
# UnrealEditor*.exe count (incl. this stage's own one), the names of other Unreal / Blender processes. Touches nothing.
OUT="$1"; DONE="$2"
[ -f "$OUT" ] || echo "time,cpu_pct,gpu_util_pct,gpu_mem_mb,blender_procs,unreal_procs,unreal_cmd_procs" > "$OUT"
while [ ! -f "$DONE" ]; do
  g=$(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits | tr -d ' ')
  c=$(powershell -NoProfile -Command "[math]::Round((Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average,0)" | tr -d '\r')
  tl=$(tasklist)
  echo "$(date +%T),$c,$g,$(echo "$tl" | grep -ci '^blender.exe'),$(echo "$tl" | grep -ci '^UnrealEditor'),$(echo "$tl" | grep -ci '^UnrealEditor-Cmd')" >> "$OUT"
  sleep 10
done
