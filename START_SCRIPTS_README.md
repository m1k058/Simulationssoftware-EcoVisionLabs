# 🚀 EcoVision Labs - Startskripte

Verwenden Sie diese Skripte, um die Simulationssoftware einfach zu starten.

## 📋 Verfügbare Skripte

### Windows

| Skript | Beschreibung | Voraussetzung |
|--------|--------------|---------------|
| `start_app_ecovision.bat` | **Empfohlen**: Verwendet Conda-Umgebung | Miniconda/Anaconda |
| `start_app_venv.bat` | Verwendet lokales venv | Python 3.12 |
| `start_app.bat` | Legacy (nicht empfohlen) | Python |

### Linux/Mac

| Skript | Beschreibung | Voraussetzung |
|--------|--------------|---------------|
| `start_app_ecovision.sh` | **Empfohlen**: Verwendet Conda-Umgebung | Miniconda/Anaconda |
| `start_app_venv.sh` | Verwendet lokales venv | Python 3.12 |
| `start_app.sh` | Legacy (nicht empfohlen) | Python |

## 🎯 Empfohlene Verwendung

### Option 1: Mit Conda (Empfohlen)

**Vorteile:**
- ✅ Automatische Python 3.12 Installation
- ✅ Isolierte Umgebung
- ✅ Einfachste Verwaltung

**Windows:**
```cmd
start_app_ecovision.bat
```

**Linux/Mac:**
```bash
chmod +x start_app_ecovision.sh
./start_app_ecovision.sh
```

**Installation Miniconda:**
- Windows: https://docs.conda.io/en/latest/miniconda.html
- Linux: `wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && bash Miniconda3-latest-Linux-x86_64.sh`
- Mac: `brew install miniconda`

### Option 2: Mit venv

**Voraussetzung:** Python 3.12 muss installiert sein!

**Windows:**
```cmd
start_app_venv.bat
```

**Linux/Mac:**
```bash
chmod +x start_app_venv.sh
./start_app_venv.sh
```

**Python 3.12 Installation:**
- Windows: https://www.python.org/downloads/release/python-31212/
- Ubuntu/Debian: `sudo apt install python3.12 python3.12-venv`
- Mac: `brew install python@3.12`

## ⚠️ Wichtige Hinweise

### Warum Python 3.12?

**Numba (Performance-Optimierung) unterstützt aktuell kein Python 3.13!**

Die Wärmepumpen-Simulation benötigt Numba für CPU-beschleunigte Berechnungen. Ohne Numba läuft die Simulation im langsameren "Normal"-Modus.

### Was machen die Skripte?

1. ✅ Prüfen Python/Conda Installation
2. ✅ Erstellen/Aktivieren der Umgebung
3. ✅ Installieren aller Pakete (bei Bedarf)
4. ✅ Starten der Streamlit-App
5. ✅ Öffnen des Browsers auf http://localhost:8502

### Fehlerbehebung

**"Python 3.12 nicht gefunden"**
→ Installieren Sie Python 3.12 oder verwenden Sie die Conda-Version

**"Conda nicht gefunden"**
→ Installieren Sie Miniconda oder verwenden Sie die venv-Version

**"Numba ist nicht installiert"**
→ Das Skript installiert Numba automatisch. Falls es fehlschlägt:
- Conda: `conda activate ecovision && pip install -r requirements.txt`
- venv: `venv\Scripts\activate && pip install -r requirements.txt` (Windows)
- venv: `source venv/bin/activate && pip install -r requirements.txt` (Linux/Mac)

## 📊 Performance

| Modus | Wärmepumpen-Berechnung | Geschwindigkeit |
|-------|------------------------|-----------------|
| **CPU-Beschleunigt (Numba)** | ✅ Optimiert | ~10x schneller |
| Normal | ⚠️ Langsam | Baseline |

→ **Empfehlung:** Verwenden Sie die Conda/venv-Skripte für optimale Performance!

## 🔧 Manuelle Ausführung

Falls Sie die Umgebung manuell verwalten möchten:

**Conda:**
```bash
conda activate ecovision
streamlit run source-code/streamlit_ui.py
```

**venv (Windows):**
```cmd
venv\Scripts\activate
streamlit run source-code/streamlit_ui.py
```

**venv (Linux/Mac):**
```bash
source venv/bin/activate
streamlit run source-code/streamlit_ui.py
```

## 📝 Lizenz

Siehe [LICENSE](LICENSE)
