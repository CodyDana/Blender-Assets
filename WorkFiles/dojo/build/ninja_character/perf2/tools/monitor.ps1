# perf2 background-load monitor (one long-lived process; touches nothing): every 10 s until <Done> exists, one CSV row:
# CPU % (all cores), % processor performance (clock vs base: 100 = base, turbo > 100), GPU utilisation / memory, the count
# of blender.exe / UnrealEditor*.exe, and the top 5 processes by CPU (name:pct of one core) other than Idle / _Total.
param([Parameter(Mandatory = $true)][string]$Out, [Parameter(Mandatory = $true)][string]$Done)
if (-not (Test-Path $Out)) { 'time,cpu_pct,cpu_perf_pct,gpu_util_pct,gpu_mem_mb,blender_procs,unreal_procs,top5' | Out-File -FilePath $Out -Encoding utf8 }
while (-not (Test-Path $Done)) {
    try {
        $c = Get-Counter -Counter '\Processor(_Total)\% Processor Time', '\Processor Information(_Total)\% Processor Performance', '\Process(*)\% Processor Time' -ErrorAction SilentlyContinue
        $s = $c.CounterSamples
        $cpu = [math]::Round(($s | Where-Object { $_.Path -like '*\processor(_total)\% processor time' }).CookedValue, 1)
        $perf = [math]::Round(($s | Where-Object { $_.Path -like '*processor information(_total)*' }).CookedValue, 1)
        $top = ($s | Where-Object { $_.Path -like '*\process(*' -and $_.InstanceName -notin @('idle', '_total') } |
                Sort-Object CookedValue -Descending | Select-Object -First 5 |
                ForEach-Object { "$($_.InstanceName):$([math]::Round($_.CookedValue, 0))" }) -join ' '
        $g = (& nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits) -replace ' ', ''
        $b = @(Get-Process -Name 'blender' -ErrorAction SilentlyContinue).Count
        $u = @(Get-Process -Name 'UnrealEditor*' -ErrorAction SilentlyContinue).Count
        "$(Get-Date -Format HH:mm:ss),$cpu,$perf,$g,$b,$u,$top" | Out-File -FilePath $Out -Append -Encoding utf8
    } catch { "$(Get-Date -Format HH:mm:ss),ERR $($_.Exception.Message)" | Out-File -FilePath $Out -Append -Encoding utf8 }
    Start-Sleep -Seconds 8
}
