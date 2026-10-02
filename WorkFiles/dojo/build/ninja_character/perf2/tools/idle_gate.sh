#!/usr/bin/env bash
# perf2 idle gate: wait until no blender.exe, no UnrealEditor*.exe and GPU utilisation < 40 % for 60 s (6 polls), max
# MAXS seconds; log what else runs each minute. Exit 0 idle, 3 timeout (the caller measures anyway and says so).
LOG="$1"; MAXS="${2:-2700}"
quiet=0; t0=$(date +%s); last=0
while [ $quiet -lt 6 ]; do
  tl=$(tasklist); b=$(echo "$tl" | grep -ci '^blender.exe'); u=$(echo "$tl" | grep -ci '^UnrealEditor')
  g=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | tr -d ' ')
  if [ "$b" -eq 0 ] && [ "$u" -eq 0 ] && [ "$g" -lt 40 ]; then quiet=$((quiet + 1)); else quiet=0; fi
  now=$(date +%s)
  if [ $((now - last)) -ge 60 ]; then
    echo "$(date +%T) blender=$b unreal=$u gpu=$g% others: $(echo "$tl" | grep -i '^blender.exe\|^UnrealEditor' | awk '{print $1":"$2}' | tr '\n' ' ')" >> "$LOG"; last=$now
  fi
  if [ $((now - t0)) -gt "$MAXS" ]; then echo "$(date +%T) IDLE_WAIT_TIMEOUT after $((now - t0)) s" >> "$LOG"; exit 3; fi
  sleep 10
done
echo "$(date +%T) idle after $(( $(date +%s) - t0 )) s" >> "$LOG"
exit 0
