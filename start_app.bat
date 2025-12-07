@echo off
set VENV_DIR=venv

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Virtuelle Umgebung wird erstellt und Pakete installiert...
    python -m venv %VENV_DIR%
    call "%VENV_DIR%\Scripts\activate.bat"
    pip install -r requirements.txt
) else (
    echo Virtuelle Umgebung wird aktiviert...
    call "%VENV_DIR%\Scripts\activate.bat"
)

echo Starte Streamlit-App...
streamlit run source-code/streamlit_ui.py

deactivate

pause