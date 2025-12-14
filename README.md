# Simulationssoftware-EcoVisionLabs

Ein Projekt von **EcoVision Labs** :) 

> [!NOTE]
> **Alpha Version:** Diese Software ist noch stark in Entwicklung.

### Shortcuts 
[![Run Software](https://img.shields.io/badge/Web_App-Start-green.svg)](https://simu-ecovisionlabs.streamlit.app/)  
[![Technische Planung](https://img.shields.io/badge/Technische_Planung-docs-blue.svg)](docs/technische_planung.md)   
[![raw-input doku](https://img.shields.io/badge/RAW_INPUT_Tabelle-docs-blue.svg)](raw-data/raw-data.md) 
   
## 1. Funktionen

Die Software dient zur **Simulation und Analyse der Energieerzeugung in Deutschland**,  
mit Fokus auf erneuerbare Energien und das Erreichen der Klimaziele 2030/2045.  

### Hauptfunktionen
- **Simulation verschiedener Energiequellen**
  - Windenergie  
  - Solarenergie
  - und mehr
- **Visualisierung**
  - Diagramme und Statistiken zur Stromerzeugung, -nachfrage und zum Anteil erneuerbarer Energien  



## 2. Schnellstart

### Software starten (gehostete WebApp):
[![Run Software](https://img.shields.io/badge/Klicke_hier:-Start-green.svg)](https://simu-ecovisionlabs.streamlit.app/)

### Software starten (lokal):

**Voraussetzungen :** 
- Python 3.9 oder höher


Die Software kann **direkt** gestartet werden, ohne Installation:

**Linux/macOS :**  
1.  **Öffne das Terminal** und navigiere in das Hauptverzeichnis des Projekts:
    ```bash
    cd /Pfad_zu/Simulationssoftware-EcoVisionLabs
    ```

2.  **Mache das Skript ausführbar** (nur einmalig nötig):
    ```bash
    chmod +x start_app.sh
    ```

3.  **Starte die Anwendung:**
    ```bash
    ./start_app.sh
    ```

**Windows :**
1.  **Öffne den Projektordner** (diesen Ordner, der das Skript `start_app.bat` enthält).
2.  Mache einen **Doppelklick** auf die Datei **`start_app.bat`**.

---


### Tests ausführen (nach editable install)

```bash
# Alle Tests
python -m unittest discover tests -v

# Einzelne Test-Datei
python -m unittest tests.test_config_manager -v
```

## 3. Das EcoVision-Team

![Teamfoto](assets/team1.png)  
*Team EcoVision Labs – Gründung Oktober 2025*
