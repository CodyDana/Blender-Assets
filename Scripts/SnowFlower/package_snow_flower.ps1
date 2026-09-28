$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$packagePath = Join-Path $projectRoot 'Exports\SnowFlower_DesignRevision3.zip'
if (Test-Path -LiteralPath $packagePath) { throw 'Revision 3 package already exists; preserve it before creating another archive.' }
$items = [System.Collections.Generic.List[object]]::new()
function Add-PackageFile([string]$relative, [string]$entryName = '') {
    $absolute = Join-Path $projectRoot $relative
    if (-not (Test-Path -LiteralPath $absolute -PathType Leaf)) { throw "Missing package source: $relative" }
    if (-not $entryName) { $entryName = $relative.Replace('\','/') }
    $items.Add([pscustomobject]@{ Source=$absolute; Entry=$entryName })
}
Add-PackageFile 'WorkFiles\SnowFlower\PACKAGE_README.md' 'README.md'
Add-PackageFile 'Assets\SnowFlower\SnowFlower_Master.blend'
Add-PackageFile 'Assets\SnowFlower\SnowFlower_Game.blend'
Add-PackageFile 'References\SnowFlower\SnowFlower_user_reference.png'
foreach ($relativeDir in @('Exports\SnowFlower','Renders\SnowFlower','Scripts\SnowFlower')) {
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $projectRoot $relativeDir) -Recurse -File) {
        if ($relativeDir -eq 'Scripts\SnowFlower' -and $file.Extension -notin @('.py','.ps1')) { continue }
        if ($file.Name -in @('SnowFlower_Pommel_ClipCheck.png','check_pommel_clip.py','write_reference_review.py')) { continue }
        Add-PackageFile $file.FullName.Substring($projectRoot.Length + 1)
    }
}
foreach ($name in @('QA_NOTES.md','REVIEW_PLAN.md','REFERENCE_REVIEW.md','REFERENCE_REVIEW.html','audit_report.json','lod_visual_report.json','build_report.json')) {
    Add-PackageFile ('WorkFiles\SnowFlower\' + $name)
}
Add-PackageFile 'WorkFiles\SnowFlower\Revision1\build_snow_flower.py'
foreach ($name in @('Front','Guard','BladeDetail','Pommel')) {
    Add-PackageFile ('WorkFiles\SnowFlower\Revision1\Renders\SnowFlower_' + $name + '.png')
}
$manifest = @($items | ForEach-Object {
    [pscustomobject]@{ path=$_.Entry; bytes=(Get-Item -LiteralPath $_.Source).Length; sha256=(Get-FileHash -LiteralPath $_.Source -Algorithm SHA256).Hash.ToLowerInvariant() }
})
$manifestJson = [pscustomobject]@{ format=1; revision=3; files=$manifest } | ConvertTo-Json -Depth 5
$zip = [System.IO.Compression.ZipFile]::Open($packagePath,[System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($item in $items) {
        [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip,$item.Source,$item.Entry,[System.IO.Compression.CompressionLevel]::Optimal)
    }
    $entry = $zip.CreateEntry('PACKAGE_MANIFEST.json')
    $writer = [System.IO.StreamWriter]::new($entry.Open(),[System.Text.UTF8Encoding]::new($false))
    try { $writer.Write($manifestJson) } finally { $writer.Dispose() }
} finally { $zip.Dispose() }
$zip = [System.IO.Compression.ZipFile]::OpenRead($packagePath)
try {
    if ($zip.Entries.Count -ne $items.Count + 1) { throw 'Unexpected package entry count' }
    foreach ($record in $manifest) {
        $entry = $zip.GetEntry($record.path)
        if ($null -eq $entry -or $entry.Length -ne $record.bytes) { throw "Missing or truncated entry: $($record.path)" }
        $stream = $entry.Open()
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try { $actual = [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-','').ToLowerInvariant() }
        finally { $sha.Dispose(); $stream.Dispose() }
        if ($actual -ne $record.sha256) { throw "Hash mismatch: $($record.path)" }
    }
} finally { $zip.Dispose() }
[pscustomobject]@{ status='verified'; path=$packagePath; entries=$items.Count+1; bytes=(Get-Item -LiteralPath $packagePath).Length; sha256=(Get-FileHash -LiteralPath $packagePath -Algorithm SHA256).Hash.ToLowerInvariant() } | ConvertTo-Json
