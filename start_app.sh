
VENV_DIR="venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtuelle Umgebung wird erstellt und Pakete installiert..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    
    pip install -r requirements.txt
else
    echo "Virtuelle Umgebung wird aktiviert..."
    source "$VENV_DIR/bin/activate"
fi


echo "Starte Streamlit-App..."


streamlit run source-code/streamlit_ui.py
-
deactivate
echo "Streamlit-App beendet."