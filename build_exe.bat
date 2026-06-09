@echo off
REM Build a Windows executable for the Frac Pump Chart app.
REM Usage: build_exe.bat

python -m pip install --upgrade pip
if errorlevel 1 goto error
python -m pip install pyinstaller
if errorlevel 1 goto error

pyinstaller --clean --noconfirm --onefile --console --name FracPumpChart ^
    --add-data "frac_pump_chart_program\app.py;frac_pump_chart_program" ^
    --add-data "frac_pump_chart_program\sample_frac_pump_data.csv;frac_pump_chart_program" ^
    --hidden-import streamlit.web.cli ^
    --hidden-import streamlit.cli ^
    --hidden-import streamlit.runtime.scriptrunner ^
    --hidden-import streamlit.web.bootstrap ^
    ".\frac_pump_chart_program\__main__.py"

if errorlevel 1 goto error

echo Build complete: dist\FracPumpChart.exe
exit /b 0

:error
echo Build failed.
exit /b 1
