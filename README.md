# Simulationssoftware-EcoVisionLabs

Ein Projekt von **EcoVision Labs** 🌱

> [!NOTE]
> **Alpha Version:** Diese Software befindet sich noch in aktiver Entwicklung.

[![Web App](https://img.shields.io/badge/Web_App-Live_Demo-green.svg)](https://ecovisionlabs.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Über das Projekt

Software zur **Simulation und Analyse der Energieerzeugung in Deutschland** mit Fokus auf erneuerbare Energien und die Erreichung der Klimaziele 2030/2045.

### Hauptfunktionen
- **Energiequellen-Simulation**: Wind, Solar, Biomasse, Wasserkraft, Speichersysteme
- **Nachfrage-Modellierung**: Verbrauchsprofile, E-Mobilität, Wärmepumpen
- **Szenario-Vergleich**: Vordefinierte und eigene Szenarien
- **Visualisierung**: Interaktive Diagramme, Zeitreihen, Kennzahlen
- **Wirtschaftlichkeit**: Kosten- und Emissionsanalyse

[Rohdaten-Dokumentation](raw-data/raw-data.md)

---

## Installation & Start

### Voraussetzungen
- **Python 3.12** (erforderlich für Numba)
  - Download: https://www.python.org/downloads/release/python-31210/

### 1. Repository klonen
```bash
git clone https://github.com/m1k058/Simulationssoftware-EcoVisionLabs.git
cd Simulationssoftware-EcoVisionLabs
```

### 2. Virtual Environment erstellen (empfohlen)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3.12 -m venv venv
source venv/bin/activate
```

### 3. Dependencies installieren
```bash
pip install -r requirements.txt
```

### 4. Anwendung starten
```bash
streamlit run source-code/streamlit_ui.py
```

Die Anwendung öffnet sich automatisch im Browser unter `http://localhost:8501`



## Alternative: Gehostete Web-App

**Ohne lokale Installation direkt nutzen:**  
👉 [ecovisionlabs.streamlit.app](ecovisionlabs.streamlit.app)


---

## 📁 Projektstruktur

```
├── source-code/          # Hauptanwendung
│   ├── streamlit_ui.py   # Streamlit-Interface
│   ├── data_processing/  # Simulationsengine
│   ├── plotting/         # Visualisierungen
│   └── ui/               # UI-Komponenten
├── scenarios/            # Szenario-Definitionen
│   ├── EVL_own/          # Eigene Szenarien
│   └── Studien_rebuild/  # Studien-basierte Szenarien
├── raw-data/             # Eingangsdaten (CSV)
├── tests/                # Integration Tests
└── requirements.txt      # Python Dependencies
```


---

## Das EcoVision-Team

![Teamfoto](assets/team1.png)  
*Team EcoVision Labs – Gegründet Oktober 2025*

---

## Lizenz

Dieses Projekt ist unter der [MIT-Lizenz](LICENSE) veröffentlicht.
