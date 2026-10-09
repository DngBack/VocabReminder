$ErrorActionPreference = 'Stop'
$venv = Join-Path $env:SystemDrive 'vrp-venv'
$python = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { python -m venv $venv }
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name VocalReminderPoke --icon assets/app_icon.ico --add-data "assets:assets" main.py
if ($LASTEXITCODE -ne 0) { throw 'EXE build failed.' }
Write-Host "EXE: dist/VocalReminderPoke.exe"
