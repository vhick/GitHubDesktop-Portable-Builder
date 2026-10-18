param(
  [Parameter(Mandatory=$true)][string]$Version,
  [Parameter(Mandatory=$true)][ValidateSet('x64','arm64')][string]$Architecture
)
$ErrorActionPreference = 'Stop'
python ./builder/build_portable.py --version $Version --architecture $Architecture --output 'stage/GitHubDesktopPortable'
if ($LASTEXITCODE -ne 0) { throw 'Portable staging failed' }
$root = (Resolve-Path 'stage/GitHubDesktopPortable').Path
$appExe = Join-Path $root 'App/GitHubDesktop/GitHubDesktop.exe'
$icon = Join-Path $root 'App/AppInfo/appicon.ico'
New-Item -ItemType Directory -Path (Split-Path $icon) -Force | Out-Null
Add-Type -AssemblyName System.Drawing
$officialIcon = [System.Drawing.Icon]::ExtractAssociatedIcon($appExe)
if (-not $officialIcon) { throw 'Unable to extract original GitHub Desktop icon from official executable' }
try {
  $iconFile = [System.IO.File]::Create($icon)
  try { $officialIcon.Save($iconFile) } finally { $iconFile.Dispose() }
} finally { $officialIcon.Dispose() }
$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework/v4.0.30319/csc.exe'
if (-not (Test-Path $compiler)) { throw 'Windows .NET Framework C# compiler missing' }
$launcher = Join-Path $root 'GitHubDesktopPortable.exe'
& $compiler /nologo /target:winexe "/out:$launcher" "/win32icon:$icon" /reference:System.Windows.Forms.dll 'builder/GitHubDesktopPortable.cs'
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $launcher)) { throw 'Portable launcher compilation failed' }
$appInfo = @"
[Format]
Type=PortableApps.comFormat
Version=3.9

[Details]
Name=GitHub Desktop Portable (Community)
AppID=GitHubDesktopPortableCommunity
Publisher=GitHub, Inc. (original application); Community repack
Homepage=https://github.com/desktop/desktop
Category=Development
Description=Unofficial portable repack of GitHub Desktop
Language=English

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true

[Version]
PackageVersion=$Version.0
DisplayVersion=$Version

[Control]
Icons=1
Start=GitHubDesktopPortable.exe
"@
Set-Content -Path (Join-Path $root 'App/AppInfo/appinfo.ini') -Value $appInfo -Encoding ascii
# No empty Data included in the updated executable download. GitHubDesktopPortable
# must create Data on first use. Data/README is documentation only, not overwrite state.
$zipName = "GitHubDesktop-v$Version-$Architecture-Portable.zip"
$dest = Join-Path (Resolve-Path '.').Path "artifacts/$zipName"
New-Item -ItemType Directory -Path 'artifacts' -Force | Out-Null
if (Test-Path $dest) { throw "Output already exists: $dest" }
Compress-Archive -Path $root -DestinationPath $dest -CompressionLevel Optimal
if (-not (Test-Path $dest)) { throw 'Unable to create ZIP artifact' }
python ./builder/verify_zip.py $dest
if ($LASTEXITCODE -ne 0) { throw 'ZIP verification failed' }
Write-Host "SUCCESS $dest"
