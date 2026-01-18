#!/bin/bash
# ============================================================================
# EcoVision Labs - Streamlit App Starter (venv)
# Verwendet: Lokales venv mit Python 3.12 + Numba
# WICHTIG: Benötigt Python 3.12 (nicht 3.13 - Numba-Kompatibilität)
# ============================================================================

set -e  # Exit on error

echo "========================================"
echo "EcoVision Labs - Simulationssoftware"
echo "Mit Python venv"
echo "========================================"
echo

VENV_DIR="venv"

echo "[1/3] Prüfe Python 3.12..."
if ! python3 --version 2>/dev/null | grep -q "3.12"; then
    echo "[FEHLER] Python 3.12 nicht gefunden!"
    echo "Installieren:"
    echo "  Ubuntu/Debian: sudo apt install python3.12 python3.12-venv"
    echo "  macOS: brew install python@3.12"
    echo
    python3 --version 2>/dev/null || echo "Python3 nicht verfügbar"
    exit 1
fi

echo "[2/3] Prüfe/Erstelle venv..."
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "Erstelle venv..."
    python3 -m venv $VENV_DIR
fi

source $VENV_DIR/bin/activate

if ! python -c "import numba" 2>/dev/null; then
    echo "Installiere Pakete..."
    python -m pip install --upgrade pip -q
    pip install -r requirements.txt
fi

echo "[3/3] Starte Streamlit..."
echo
echo "Browser: http://localhost:8502"
echo "Beenden: Ctrl+C"
echo

streamlit run source-code/streamlit_ui.py

deactivate
