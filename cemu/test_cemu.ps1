# Launch Mario Kart 8 in Cemu, wait, report whether it crashed (reads Cemu's log.txt) and save a screenshot.
#   powershell -File test_cemu.ps1 -Cemu C:\Cemu\Cemu.exe -Game "D:\Games\MARIO KART 8\code\Turbo.rpx" [-Seconds 45]
param([Parameter(Mandatory)][string]$Cemu, [Parameter(Mandatory)][string]$Game, [int]$Seconds = 45, [string]$Log = "$env:APPDATA\Cemu\log.txt", [string]$Shot = "$PSScriptRoot\shot.png")
$name = [IO.Path]::GetFileNameWithoutExtension($Cemu)
Get-Process $name -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }; Start-Sleep 3
Get-Process $name -ErrorAction SilentlyContinue | Stop-Process -Force
Remove-Item $Log -ErrorAction SilentlyContinue
$p = Start-Process -FilePath $Cemu -WorkingDirectory (Split-Path $Cemu) -ArgumentList '-g', "`"$Game`"" -PassThru
Start-Sleep -Seconds $Seconds
$crashed = [bool](Get-Content $Log -ErrorAction SilentlyContinue | Select-String 'Crashlog')
"alive=$(-not $p.HasExited) crashed=$crashed"
Get-Content $Log -ErrorAction SilentlyContinue | Select-String 'IP 0x|RPX hash|TitleVersion' | Select-Object -First 5 | ForEach-Object { $_.Line }
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
[System.Drawing.Graphics]::FromImage($bmp).CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$bmp.Save($Shot, [System.Drawing.Imaging.ImageFormat]::Png)
