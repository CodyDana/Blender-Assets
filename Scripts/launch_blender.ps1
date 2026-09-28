<#
Launch a GUI Blender bound to an MCP port for one AI agent, claiming the asset lock first.

  .\Scripts\launch_blender.ps1 -Blend Assets\Foo.blend -Port 9876 -Agent claude
  .\Scripts\launch_blender.ps1 -Port 9877 -Agent codex          # empty scratch file, no lock

Ports: claude = 9876, codex = 9877. Locks live in WorkFiles\locks (see Scripts\pipeline\lock.py).
#>
param(
    [string]$Blend = "",
    [int]$Port = 9876,
    [string]$Agent = "claude",
    [string]$Asset = "",
    [switch]$NoLock,
    [int]$WaitSeconds = 45
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
$autostart = Join-Path $PSScriptRoot 'mcp_autostart.py'
$lockPy = Join-Path $PSScriptRoot 'pipeline\lock.py'

if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $Port already has a listener: another Blender instance is bound to it."
}
$blendPath = ''
if ($Blend) {
    $blendPath = (Resolve-Path -LiteralPath $Blend).Path
    if (-not $Asset) { $Asset = [IO.Path]::GetFileNameWithoutExtension($blendPath) }
    if (-not $NoLock) {
        if (Test-Path $lockPy) {
            & py $lockPy claim $Asset --agent $Agent --blend $blendPath --port $Port
            if ($LASTEXITCODE -ne 0) { throw "Asset '$Asset' is locked by another agent (see $root\WorkFiles\locks). Not launching." }
        } else {
            Write-Warning "Scripts\pipeline\lock.py not found; launching without a lock."
        }
    }
}
$argLine = ''
if ($blendPath) { $argLine += "`"$blendPath`" " }
$argLine += "--python `"$autostart`" -- --port $Port --agent $Agent"
Start-Process -FilePath $blender -ArgumentList $argLine -WorkingDirectory $root | Out-Null
for ($i = 0; $i -lt $WaitSeconds; $i++) {
    Start-Sleep -Seconds 1
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        if ($blendPath) { Write-Host "Blender ($Agent) is listening on port $Port with $blendPath" }
        else { Write-Host "Blender ($Agent) is listening on port $Port (scratch file)" }
        exit 0
    }
}
Write-Warning "Blender started but port $Port is not listening after $WaitSeconds s; see $root\WorkFiles\mcp_autostart.log"
exit 1
