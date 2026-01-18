@echo off
REM ============================================================================
REM EcoVision Labs - Streamlit App Starter (Conda)
REM Verwendet: Conda-Umgebung 'ecovision' mit Python 3.12 + Numba
REM ============================================================================

title EcoVision Labs - Simulationssoftware

echo ========================================
echo EcoVision Labs - Simulationssoftware  
echo Mit Conda-Umgebung (ecovision)
echo ========================================
echo.

set ENV_NAME=ecovision
set CONDA_PATH=%USERPROFILE%\miniconda3
set CONDA_EXE=%CONDA_PATH%\Scripts\conda.exe

REM Suche Conda (Miniconda oder Anaconda)
if not exist "%CONDA_EXE%" (
    set CONDA_PATH=%USERPROFILE%\anaconda3
    set CONDA_EXE=%CONDA_PATH%\Scripts\conda.exe
)

if not exist "%CONDA_EXE%" (
    echo [FEHLER] Conda nicht gefunden!
    echo Bitte installieren Sie Miniconda: https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)

echo [1/3] Pruefe Umgebung '%ENV_NAME%'...
"%CONDA_EXE%" env list | findstr /C:"%ENV_NAME%" >nul 2>&1
if errorlevel 1 (
    echo Umgebung nicht gefunden - erstelle neu mit Python 3.12...
    call "%CONDA_EXE%" create -n %ENV_NAME% python=3.12 -y
    if errorlevel 1 (
        echo [FEHLER] Konnte Umgebung nicht erstellen!
        pause
        exit /b 1
    )
)

echo [2/3] Pruefe Pakete (Numba, Streamlit, etc.)...
call "%CONDA_EXE%" run -n %ENV_NAME% python -c "import numba" 2>nul
if errorlevel 1 (
    echo Installiere Pakete aus requirements.txt...
    call "%CONDA_EXE%" run -n %ENV_NAME% pip install -r requirements.txt
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

call "%CONDA_EXE%" run -n %ENV_NAME% streamlit run source-code/streamlit_ui.py
pause
