#!/bin/bash
# ============================================================================
# EcoVision Labs - Streamlit App Starter (Conda)
# Verwendet: Conda-Umgebung 'ecovision' mit Python 3.12 + Numba
# ============================================================================

set -e  # Exit on error

echo "========================================"
echo "EcoVision Labs - Simulationssoftware"
echo "Mit Conda-Umgebung (ecovision)"
echo "========================================"
echo

ENV_NAME="ecovision"

# Finde Conda
if command -v conda &> /dev/null; then
    CONDA_EXE="conda"
elif [ -f "$HOME/miniconda3/bin/conda" ]; then
    CONDA_EXE="$HOME/miniconda3/bin/conda"
elif [ -f "$HOME/anaconda3/bin/conda" ]; then
    CONDA_EXE="$HOME/anaconda3/bin/conda"
else
    echo "[FEHLER] Conda nicht gefunden!"
    echo "Installieren Sie Miniconda: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo "[1/3] Prüfe Umgebung '$ENV_NAME'..."
if ! $CONDA_EXE env list | grep -q "^$ENV_NAME "; then
    echo "Umgebung nicht gefunden - erstelle neu mit Python 3.12..."
    $CONDA_EXE create -n $ENV_NAME python=3.12 -y
fi

echo "[2/3] Prüfe Pakete (Numba, Streamlit, etc.)..."
if ! $CONDA_EXE run -n $ENV_NAME python -c "import numba" 2>/dev/null; then
    echo "Installiere Pakete aus requirements.txt..."
    $CONDA_EXE run -n $ENV_NAME pip install -r requirements.txt
fi

echo "[3/3] Starte Streamlit..."
echo
echo "Browser: http://localhost:8502"
echo "Beenden: Ctrl+C"
echo

$CONDA_EXE run -n $ENV_NAME streamlit run source-code/streamlit_ui.py
