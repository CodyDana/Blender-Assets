#!/usr/bin/env bash
# perf re-run only on an idle machine: no blender.exe for 60 s and GPU utilisation < 40 % (the desktop idles at ~25 %) and no UnrealEditor-Cmd (max wait 90 min); the
# background load is sampled every 10 s into perf/background_load.csv during the runs.
T="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/ninja_character/test"
L="$T/perf/background_load.csv"
quiet=0; t0=$(date +%s)
while [ $quiet -lt 6 ]; do
  b=$(tasklist | grep -ci '^blender.exe'); g=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | tr -d ' ')
  if [ "$b" -eq 0 ] && [ "$g" -lt 40 ] && ! tasklist | grep -qi UnrealEditor-Cmd; then quiet=$((quiet + 1)); else quiet=0; fi
  [ $(( $(date +%s) - t0 )) -gt 5400 ] && { echo "IDLE_WAIT_TIMEOUT"; exit 3; }
  sleep 10
done
echo "idle at $(date +%T) after $(( $(date +%s) - t0 )) s"
echo "time,cpu_pct,gpu_util_pct,gpu_mem_mb,blender_procs,unreal_cmd_procs" > "$L"
( while [ ! -f "$T/perf/.done" ]; do g=$(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits | tr -d ' ');
    c=$(powershell -NoProfile -Command "[math]::Round((Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average,0)" | tr -d '\r');
    echo "$(date +%T),$c,$g,$(tasklist | grep -ci '^blender.exe'),$(tasklist | grep -ci UnrealEditor-Cmd)" >> "$L"; sleep 10; done ) &
rm -f "$T/perf/.done"
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$T/run_perf.ps1")" | tail -2
touch "$T/perf/.done"; sleep 12
echo PERF_IDLE_DONE
