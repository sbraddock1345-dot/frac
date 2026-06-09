# Build a Windows executable for the Frac Pump Chart app.
# Usage: powershell -ExecutionPolicy Bypass -File .\build_exe.ps1

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

Write-Host "Installing PyInstaller if needed..."
python -m pip install --upgrade pip
python -m pip install pyinstaller

$exeName = "FracPumpChart"

Write-Host "Building executable..."
pyinstaller `
    --clean `
    --noconfirm `
    --onefile `
    --console `
    --name $exeName `
    --add-data "frac_pump_chart_program\app.py;frac_pump_chart_program" `
    --add-data "frac_pump_chart_program\sample_frac_pump_data.csv;frac_pump_chart_program" `
    --hidden-import streamlit.web.cli `
    --hidden-import streamlit.cli `
    --hidden-import streamlit.runtime.scriptrunner `
    --hidden-import streamlit.web.bootstrap `
    ".\frac_pump_chart_program\__main__.py"

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed."
    exit $LASTEXITCODE
}

Write-Host "Build complete. Find the executable in dist\$exeName.exe"