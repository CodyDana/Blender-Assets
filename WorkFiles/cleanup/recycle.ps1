# Move every path in recycle_list.json to the Recycle Bin (never a permanent delete).
# Largest first; after the first item it checks that the item really reached the bin, and stops if not.
Add-Type -AssemblyName Microsoft.VisualBasic
$root = 'C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\cleanup'
$list = Get-Content "$root\recycle_list.json" -Raw | ConvertFrom-Json | Sort-Object -Property bytes -Descending
$log = "$root\recycled_$(Get-Date -Format yyyyMMdd_HHmm).log"
$shell = New-Object -ComObject Shell.Application
$bin = $shell.Namespace(10)
$capBytes = 97394MB
$total = 0; $n = 0; $fail = 0
foreach ($e in $list) {
    $p = $e.path
    if (-not (Test-Path -LiteralPath $p)) { Add-Content $log "MISSING  $p"; continue }
    if (($total + [int64]$e.bytes) -gt [int64]($capBytes * 0.9)) { Add-Content $log "STOP: would exceed 90% of the bin before $p"; break }
    $before = $bin.Items().Count
    try {
        if (Test-Path -LiteralPath $p -PathType Container) {
            [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($p, 'OnlyErrorDialogs', 'SendToRecycleBin')
        } else {
            [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($p, 'OnlyErrorDialogs', 'SendToRecycleBin')
        }
    } catch { Add-Content $log "ERROR    $p  $($_.Exception.Message)"; $fail++; continue }
    $n++; $total += [int64]$e.bytes
    Add-Content $log ("RECYCLED {0,12:N0} {1}" -f $e.bytes, $p)
    if ($n -eq 1) {
        $after = $bin.Items().Count
        if ($after -le $before) { Add-Content $log "STOP: first item did not appear in the Recycle Bin (before $before, after $after)"; Write-Output "STOPPED: bin check failed"; break }
        Write-Output "bin check ok: $before -> $after items"
    }
}
Write-Output ("done: {0} items, {1:N2} GiB to the Recycle Bin, {2} errors, log {3}" -f $n, ($total / 1GB), $fail, $log)
