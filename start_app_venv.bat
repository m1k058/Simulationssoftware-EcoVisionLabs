@echo off
REM ============================================================================
REM EcoVision Labs - Streamlit App Starter (venv)
REM Verwendet: Lokales venv mit Python 3.12 + Numba
REM WICHTIG: Benoetigt Python 3.12 (nicht 3.13 - Numba-Kompatibilitaet)
REM ============================================================================

title EcoVision Labs - Simulationssoftware

echo ========================================
echo EcoVision Labs - Simulationssoftware
echo Mit Python venv
echo ========================================
echo.

set VENV_DIR=venv

echo [1/3] Pruefe Python 3.12...
python --version 2>nul | findstr /C:"3.12" >nul
if errorlevel 1 (
    echo [FEHLER] Python 3.12 nicht gefunden!
    echo Download: https://www.python.org/downloads/release/python-31212/
    echo.
    python --version 2>nul
    pause
    exit /b 1
)

echo [2/3] Pruefe/Erstelle venv...
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Erstelle venv...
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [FEHLER] venv-Erstellung fehlgeschlagen!
        pause
        exit /b 1
    )
)

call %VENV_DIR%\Scripts\activate.bat

python -c "import numba" 2>nul
if errorlevel 1 (
    echo Installiere Pakete...
    python -m pip install --upgrade pip -q
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [FEHLER] Installation fehlgeschlagen!
        pause
        exit /b 1
    )
)

echo [3/3] Starte Streamlit...
echo.
echo Browser: http://localhost:8502
echo Beenden: Ctrl+C
echo.

streamlit run source-code/streamlit_ui.py

deactivate
pause
