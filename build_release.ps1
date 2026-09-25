$ErrorActionPreference='Stop'
$Root='D:\code\phongthan_proxy_manager'
Set-Location $Root
$Name='PhongThanProxyManager'
$Version='1.0.0'

& "$Root\.venv\Scripts\pyinstaller.exe" --noconfirm --clean --onedir --windowed --name $Name --icon "$Root\assets\app.ico" --version-file "$Root\version_info.txt" "$Root\app.py"
if($LASTEXITCODE -ne 0){ throw "PyInstaller failed: $LASTEXITCODE" }

$Out="$Root\dist\$Name"
New-Item -ItemType Directory -Path "$Out\data","$Out\logs","$Out\tools" -Force | Out-Null
if(Test-Path "$Root\tools\ProxifierStandard"){ Copy-Item "$Root\tools\ProxifierStandard" "$Out\tools\ProxifierStandard" -Recurse -Force }
if(Test-Path "$Root\tools\ProxifierSetup.exe"){ Copy-Item "$Root\tools\ProxifierSetup.exe" "$Out\tools\ProxifierSetup.exe" -Force }
Copy-Item "$Root\PLAN.md" "$Out\PLAN.md" -Force
if(Test-Path "$Root\TEST_REPORT.md"){ Copy-Item "$Root\TEST_REPORT.md" "$Out\TEST_REPORT.md" -Force }
Copy-Item "$Root\requirements.txt" "$Out\requirements.txt" -Force

$readme=@'
Phong Than Proxy Manager v1.0.0

- Chay PhongThanProxyManager.exe.
- Data, log va config duoc tao canh file EXE.
- Routing dung Proxifier Standard trong thu muc tools.
- Neu Proxifier driver chua duoc cai, Apply Routing se de nghi mo installer bang quyen Administrator.
- Proxy credentials duoc ma hoa bang Windows DPAPI; khong copy secrets.json sang Windows user/may khac.
- Ban portable khong can cai Python.
'@
[System.IO.File]::WriteAllText("$Out\README.txt",$readme,[System.Text.UTF8Encoding]::new($false))

$ReleaseDir="$Root\release"
New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null
$Zip="$ReleaseDir\${Name}_v${Version}_portable.zip"
if(Test-Path $Zip){Remove-Item $Zip -Force}
Compress-Archive -Path "$Out\*" -DestinationPath $Zip -CompressionLevel Optimal

Write-Output "RELEASE=$Zip"
Get-Item "$Out\$Name.exe",$Zip | Select FullName,Length,LastWriteTime
