# Builds the review contact sheet from EXISTING renders only (no new 3D renders).
# Output: WorkFiles/BlackCloak_Review/BLACK_CLOAK_contact_sheet.png
Add-Type -AssemblyName System.Drawing
$root = 'C:\Users\Cody\Desktop\Blender_Projects'
$rv   = "$root\WorkFiles\BlackCloak_Review"
$out  = "$rv\BLACK_CLOAK_contact_sheet.png"

$W = 1360; $gap = 16; $lab = 44
$row1 = @(
  @{f="$root\References\BlackCloak\blackcloak.png"; t="1. Reference (blackcloak.png)"},
  @{f="$rv\fidelity\ours_lod0_front_refframe.png"; t="2. Shipped LOD0 (BlackCloak.fbx), 84,612 tris"},
  @{f="$rv\fidelity\ours_mhfit_refframe.png";       t="3. MetaHuman fit (BlackCloak_MH_fit.blend)"}
)
$pairs = @(
  @{f="$rv\blind\pair_03.png"; t="Blind pair 03 - collar (reference = RIGHT)"},
  @{f="$rv\blind\pair_04.png"; t="Blind pair 04 - clasp (reference = LEFT)"},
  @{f="$rv\blind\pair_15.png"; t="Blind pair 15 - fabric grain (reference = RIGHT)"},
  @{f="$rv\blind\pair_20.png"; t="Blind pair 20 - hem (reference = RIGHT)"}
)
$h1 = 674; $pw = [int](($W - 3*$gap)/2)
$ph = @(); foreach($p in $pairs){ $i=[System.Drawing.Image]::FromFile($p.f); $ph += [int]($i.Height * $pw / $i.Width); $i.Dispose() }
$r2 = [Math]::Max($ph[0],$ph[1]); $r3 = [Math]::Max($ph[2],$ph[3])
$head = 70; $foot = 40
$H = $head + $lab + $h1 + $gap + $lab + $r2 + $gap + $lab + $r3 + $foot
$bmp = New-Object System.Drawing.Bitmap $W, $H
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAlias
$g.Clear([System.Drawing.Color]::FromArgb(238,238,238))
$fT = New-Object System.Drawing.Font 'Segoe UI', 20, ([System.Drawing.FontStyle]::Bold)
$fL = New-Object System.Drawing.Font 'Segoe UI', 13
$fS = New-Object System.Drawing.Font 'Segoe UI', 11
$ink = [System.Drawing.Brushes]::Black
$g.DrawString("Black Cloak review 2026-09-26 - existing renders only", $fT, $ink, 16, 14)
$g.DrawString("Blind test: 20 of 20 pairs picked correctly (pass mark: 13 or fewer). Silhouette IoU 0.934.", $fS, $ink, 18, 46)

$y = $head
$x0 = [int](($W - (3*417 + 2*$gap))/2); $x = $x0
foreach($p in $row1){
  $i=[System.Drawing.Image]::FromFile($p.f)
  $g.DrawString($p.t, $fL, $ink, $x, $y + 12)
  $g.DrawImage($i, $x, $y + $lab, 417, $h1); $i.Dispose(); $x += 417 + $gap
}
$y += $lab + $h1 + $gap
for($k=0; $k -lt 4; $k++){
  if($k -eq 2){ $y += $lab + $r2 + $gap }
  $col = $k % 2; $x = $gap + $col*($pw + $gap)
  $i=[System.Drawing.Image]::FromFile($pairs[$k].f)
  $g.DrawString($pairs[$k].t, $fL, $ink, $x, $y + 12)
  $g.DrawImage($i, $x, $y + $lab, $pw, $ph[$k]); $i.Dispose()
}
$g.DrawString("Sources: References/BlackCloak/blackcloak.png; WorkFiles/BlackCloak_Review/fidelity/ours_*_refframe.png; WorkFiles/BlackCloak_Review/blind/pair_*.png. Blind sides identified by eye after scoring.", $fS, $ink, 16, $H - 30)
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
"wrote $out ($W x $H)"
